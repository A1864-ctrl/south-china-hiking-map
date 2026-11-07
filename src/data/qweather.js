/**
 * 和风天气接入层
 * ─ 新版接口：/weather/v1/current|daily/{纬度}/{经度}（注意：路径里纬度在前）
 * ─ 旧版接口：/v7/weather/now|7d、/v7/warning/now（location=经度,纬度）——API Host 为 devapi 时使用
 * ─ 鉴权：?key=（也支持 Header X-QW-Api-Key），API Key 只存在本机浏览器
 * ─ 缓存：按坐标取两位小数 + 30 分钟，避免刷新一次打一次接口
 */
const CFG_KEY = 'yejing:weather:cfg'
const CACHE_KEY = 'yejing:weather:cache'
const TTL = 30 * 60 * 1000

/**
 * 【已下线】和风接入代码保留备用：再次启用时恢复默认 Key 常量或由面板填入。
 * 2026-11-07：应用户要求改用 Open-Meteo 免 Key 数据源，和风相关的 Key 已从代码中移除。
 */
/** 旧版默认域名是 devapi.qweather.com；新版项目请填控制台分配的 API Host */
export const DEFAULT_HOST = ''

export function readConfig() {
  try {
    const o = JSON.parse(localStorage.getItem(CFG_KEY) || '{}') || {}
    // key 未设置过时用内置 Key；用户显式清除（存了空串）则尊重其选择
    return { host: o.host || DEFAULT_HOST, key: o.key || '' }
  } catch {
    return { host: DEFAULT_HOST, key: '' }
  }
}

export function saveConfig({ host, key }) {
  const cfg = { host: String(host || '').trim().replace(/^https?:\/\//, '').replace(/\/+$/, '') || DEFAULT_HOST, key: String(key || '').trim() }
  localStorage.setItem(CFG_KEY, JSON.stringify(cfg))
  return cfg
}

export function hasKey() {
  const c = readConfig()
  return !!(c.host && c.key)
}

/* ── 缓存 ── */
function readCache() {
  try {
    return JSON.parse(localStorage.getItem(CACHE_KEY) || '{}') || {}
  } catch {
    return {}
  }
}
function cacheGet(id) {
  const c = readCache()[id]
  if (!c || Date.now() - c.at > TTL) return null
  return c.data
}
function cacheSet(id, data) {
  const all = readCache()
  all[id] = { at: Date.now(), data }
  // 只留最近 40 个点位，避免 localStorage 膨胀
  const keys = Object.keys(all)
  if (keys.length > 40) {
    keys.sort((a, b) => all[a].at - all[b].at)
    for (const k of keys.slice(0, keys.length - 40)) delete all[k]
  }
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(all))
  } catch {
    /* 空间不足就算了 */
  }
}

/* ── 天气代码 → 站内图标 ── */
export function condOfCode(code) {
  const c = Number(code)
  if (c === 100 || c === 150) return 'sun'
  if (c === 104 || c === 154) return 'over'
  if (c >= 302 && c <= 304) return 'storm'
  if (c >= 300 && c < 400) return 'rain'
  if (c >= 400 && c < 500) return 'snow'
  if (c >= 500 && c < 600) return 'fog'
  return 'cloud'
}

const COND_NAME = {
  sun: '晴', cloud: '多云', over: '阴', rain: '雨', storm: '雷阵雨', snow: '雪', fog: '雾'
}

function beaufort(ms) {
  const t = [0.3, 1.6, 3.4, 5.5, 8.0, 10.8, 13.9, 17.2, 20.8, 24.5, 28.5, 32.7]
  const n = Number(ms) || 0
  let scale = 0
  for (let i = 0; i < t.length; i++) if (n >= t[i]) scale = i + 1
  return Math.min(12, scale)
}

function toNum(v, fallback = 0) {
  const n = typeof v === 'object' && v !== null ? v.value : v
  const x = Number(n)
  return Number.isFinite(x) ? x : fallback
}

function warnTone(sev) {
  const s = String(sev || '').toLowerCase()
  if (s.includes('extreme') || s.includes('红')) return '#a12b1f'
  if (s.includes('severe') || s.includes('橙')) return '#a9462f'
  if (s.includes('moderate') || s.includes('黄')) return '#a97a17'
  return '#2f6f9e'
}

function pickDate(iso) {
  const s = String(iso || '')
  return s.length >= 10 ? s.slice(0, 10) : ''
}

/**
 * 拉取并归一化成和本站模型一致的结构
 * @returns {Promise<{source:'qweather', days:Array, today:Object, warnings:Array, now:Object, updated:string, attributions:string[]}>}
 */
export async function fetchWeather(lat, lng, opt = {}) {
  const cfg = readConfig()
  if (!cfg.host || !cfg.key) {
    const e = new Error(!cfg.host ? '尚未填写 API Host' : '尚未配置和风天气 Key')
    e.code = !cfg.host ? 'NO_HOST' : 'NO_KEY'
    throw e
  }
  const days = opt.days || 7
  const la = Number(lat).toFixed(2)
  const lo = Number(lng).toFixed(2)
  const legacy = /devapi|api\.qweather\.com/.test(cfg.host)
  const base = `https://${cfg.host}`
  const id = `${la},${lo},${days},${cfg.host}`
  const hit = cacheGet(id)
  if (hit) return { ...hit, cached: true }

  const url = (path) => `${base}${path}${path.includes('?') ? '&' : '?'}key=${encodeURIComponent(cfg.key)}`

  const get = async (path) => {
    const ctl = new AbortController()
    const timer = setTimeout(() => ctl.abort(), 8000)
    try {
      const res = await fetch(url(path), { signal: ctl.signal })
      let body = null
      try {
        body = await res.json()
      } catch {
        /* 非 JSON */
      }
      return { ok: res.ok, status: res.status, body }
    } catch (err) {
      // 域名写错 / 断网 / 被拦截，都会走到这里；给一句能照着改的提示
      if (err && err.name === 'AbortError') {
        const e = new Error('请求超时（8 秒），检查网络或 API Host')
        e.code = 'TIMEOUT'
        throw e
      }
      const e = new Error('网络不可达：检查 API Host 是否填对（形如 abcxyz.qweatherapi.com）')
      e.code = 'NET'
      throw e
    } finally {
      clearTimeout(timer)
    }
  }

  const fail = (code, msg) => {
    const e = new Error(msg)
    e.code = code
    return e
  }
  const checkCode = (r, label) => {
    if (!r.ok) {
      if (r.status === 401) throw fail('AUTH', `${label}：鉴权失败（401），检查 Key 是否正确`)
      if (r.status === 403) throw fail('DENY', `${label}：没有权限（403），检查项目是否开通该接口`)
      if (r.status === 429) throw fail('QUOTA', `${label}：请求过于频繁（429）`)
      if (r.status === 404) throw fail('NOTFOUND', `${label}：接口或地点不存在（404）`)
      throw fail('HTTP', `${label}：HTTP ${r.status}`)
    }
    // 旧版把错误码放在 body.code
    if (r.body && r.body.code && String(r.body.code) !== '200') {
      const c = String(r.body.code)
      if (c === '401') throw fail('AUTH', `${label}：鉴权失败（code 401）`)
      if (c === '402') throw fail('QUOTA', `${label}：额度用尽（code 402）`)
      if (c === '403') throw fail('DENY', `${label}：无权限（code 403）`)
      if (c === '404') throw fail('NOTFOUND', `${label}：地点无效（code 404）`)
      throw fail('CODE', `${label}：返回 code ${c}`)
    }
  }

  /* 1) 实况 */
  const curPath = legacy
    ? `/v7/weather/now?location=${lo},${la}`
    : `/weather/v1/current/${la}/${lo}`
  const curR = await get(curPath)
  checkCode(curR, '实况')

  /* 2) 逐日 */
  const dayPath = legacy
    ? `/v7/weather/7d?location=${lo},${la}`
    : `/weather/v1/daily/${la}/${lo}?days=${days}&localTime=true`
  const dayR = await get(dayPath)
  checkCode(dayR, '逐日预报')

  /* 3) 预警：新版路径不确定，按候选依次尝试，失败不影响主体 */
  let alerts = []
  const warnPaths = legacy
    ? [`/v7/warning/now?location=${lo},${la}`]
    : [
        `/alert/v1/current/${la}/${lo}`,
        `/warning/v1/current/${la}/${lo}`,
        `/v7/warning/now?location=${lo},${la}`
      ]
  for (const p of warnPaths) {
    try {
      const r = await get(p)
      if (!r.ok) continue
      const arr = (r.body && (r.body.alerts || r.body.warning || r.body.warnings)) || []
      if (Array.isArray(arr)) {
        alerts = arr
        break
      }
    } catch {
      /* 换下一个候选 */
    }
  }

  /* 4) 归一化 */
  const now = (() => {
    if (legacy && curR.body.now) {
      const n = curR.body.now
      return {
        temp: Math.round(toNum(n.temp)),
        feels: Math.round(toNum(n.feelsLike)),
        text: n.text || '',
        cond: condOfCode(n.icon),
        humidity: Math.round(toNum(n.humidity)),
        wind: toNum(n.windScale),
        windDir: n.windDir || '',
        precip: toNum(n.precip),
        pressure: Math.round(toNum(n.pressure)),
        vis: Math.round(toNum(n.vis))
      }
    }
    const b = curR.body || {}
    return {
      temp: Math.round(toNum(b.temperature)),
      feels: Math.round(toNum(b.feelsLike)),
      text: b.condition?.text || '',
      cond: condOfCode(b.condition?.code),
      humidity: Math.round(toNum(b.humidity) * 100),
      wind: toNum(b.wind?.scale),
      windDir: b.wind?.direction?.compass || '',
      precip: toNum(b.precipitation?.amount),
      pressure: Math.round(toNum(b.pressure)),
      vis: Math.round(toNum(b.visibility) / 1000)
    }
  })()

  const rawDays = legacy ? dayR.body.daily || [] : dayR.body.days || []
  const baseDate = new Date()
  const outDays = rawDays.slice(0, days).map((d, i) => {
    if (legacy) {
      const code = Number(d.iconDay)
      const date = d.fxDate
      return {
        date: date ? `${Number(date.slice(5, 7))}/${Number(date.slice(8, 10))}` : '',
        wd: i === 0 ? '今天' : i === 1 ? '明天' : '周' + '日一二三四五六'[new Date(date).getDay()],
        iso: date,
        high: Math.round(toNum(d.tempMax)),
        low: Math.round(toNum(d.tempMin)),
        cond: condOfCode(code),
        name: d.textDay || COND_NAME[condOfCode(code)],
        icon: '',
        precip: toNum(d.precip),
        prob: Math.round(toNum(d.pop)),
        wind: toNum(d.windScaleDay),
        gust: toNum(d.windScaleDay) + 2,
        warn: []
      }
    }
    const date = pickDate(d.forecastStartTime)
    const cond = condOfCode(d.daytime?.condition?.code)
    return {
      date: date ? `${Number(date.slice(5, 7))}/${Number(date.slice(8, 10))}` : '',
      wd: i === 0 ? '今天' : i === 1 ? '明天' : '周' + '日一二三四五六'[new Date(date).getDay()],
      iso: date,
      high: Math.round(toNum(d.temperatureMax)),
      low: Math.round(toNum(d.temperatureMin)),
      cond,
      name: d.daytime?.condition?.text || COND_NAME[cond],
      icon: '',
      precip: +toNum(d.daytime?.precipitation?.amount).toFixed(1),
      prob: Math.round(toNum(d.daytime?.precipitation?.probability) * 100),
      wind: toNum(d.daytime?.wind?.scale),
      gust: Math.max(toNum(d.daytime?.wind?.scale), beaufort(toNum(d.daytime?.windGustMax))),
      warn: []
    }
  })

  // 预警归一化（新旧字段兼容）
  const warnings = alerts.map((a) => {
    const sev = a.severity || a.level || ''
    const name = a.typeName || a.title || '气象预警'
    return {
      k: 'qweather',
      text: a.title || `${name}预警`,
      tone: warnTone(sev),
      detail: a.text || '',
      kind: name,
      time: a.pubTime || a.startTime || '',
      severity: sev
    }
  })

  const today = outDays[0] || null
  // 用实况温度修正今天的高低温展示（预报的日高温常与当前实况不同）
  if (today) {
    today.name = now.text || today.name
    today.cond = now.cond || today.cond
  }

  const data = {
    source: 'qweather',
    days: outDays,
    today,
    warnings,
    now,
    updated: new Date().toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit' }),
    attributions: curR.body?.metadata?.attributions || dayR.body?.metadata?.attributions || ['https://developer.qweather.com/attribution.html'],
    cached: false,
    days7: outDays.length
  }
  cacheSet(id, data)
  return data
}

/** 把和风的天气代码映射成站内图标字符 */
export function iconOf(cond) {
  return { sun: '☀', cloud: '☁', over: '☁', rain: '🌧', storm: '⛈', snow: '❄', fog: '🌫' }[cond] || '☁'
}
