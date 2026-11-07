/**
 * Open-Meteo 真实天气（免费、无需 Key、支持 CORS 直连）
 * ─ https://api.open-meteo.com/v1/forecast?latitude=&longitude=&current=...&daily=...&timezone=auto
 * ─ 归一化成与本地模型一致的结构，接口失败/离线时上层自动回退模型
 * ─ 缓存：坐标取两位小数 + 30 分钟
 */
const CACHE_KEY = 'yejing:weather:om'
const TTL = 30 * 60 * 1000

/* WMO 天气代码 → 站内条件 */
function condOfCode(code) {
  const c = Number(code)
  if (c === 0) return 'sun'
  if (c === 1 || c === 2) return 'cloud'
  if (c === 3) return 'over'
  if (c === 45 || c === 48) return 'fog'
  if (c >= 71 && c <= 77) return 'snow'
  if (c === 85 || c === 86) return 'snow'
  if (c >= 95) return 'storm'
  if (c >= 51) return 'rain'
  return 'cloud'
}

const COND_NAME = {
  sun: '晴', cloud: '多云', over: '阴', rain: '雨', storm: '雷阵雨', snow: '雪', fog: '雾'
}

export function iconOf(cond) {
  return { sun: '☀', cloud: '☁', over: '☁', rain: '🌧', storm: '⛈', snow: '❄', fog: '🌫' }[cond] || '☁'
}

/* m/s → 蒲福风级 */
function beaufort(ms) {
  const t = [0.3, 1.6, 3.4, 5.5, 8.0, 10.8, 13.9, 17.2, 20.8, 24.5, 28.5, 32.7]
  const n = Number(ms) || 0
  let scale = 0
  for (let i = 0; i < t.length; i++) if (n >= t[i]) scale = i + 1
  return Math.min(12, scale)
}

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
  const keys = Object.keys(all)
  if (keys.length > 40) {
    keys.sort((a, b) => all[a].at - all[b].at)
    for (const k of keys.slice(0, keys.length - 40)) delete all[k]
  }
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(all))
  } catch {
    /* 忽略 */
  }
}

/**
 * 拉取真实天气并归一化
 * @returns {Promise<{source:'openmeteo', days:Array, today:Object, warnings:Array, now:Object, updated:string}>}
 */
export async function fetchWeather(lat, lng, opt = {}) {
  const days = opt.days || 7
  const la = Number(lat).toFixed(2)
  const lo = Number(lng).toFixed(2)
  const id = `om:${la},${lo},${days}`
  const hit = cacheGet(id)
  if (hit) return { ...hit, cached: true }

  const params = new URLSearchParams({
    latitude: la,
    longitude: lo,
    current: 'temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_gusts_10m',
    daily: 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max',
    timezone: 'auto',
    forecast_days: String(days)
  })
  const ctl = new AbortController()
  const timer = setTimeout(() => ctl.abort(), 8000)
  let body
  try {
    const res = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`, { signal: ctl.signal })
    if (!res.ok) {
      const e = new Error(`Open-Meteo 返回 HTTP ${res.status}`)
      e.code = 'HTTP'
      throw e
    }
    body = await res.json()
  } catch (err) {
    if (err && err.name === 'AbortError') {
      const e = new Error('请求超时（8 秒）')
      e.code = 'TIMEOUT'
      throw e
    }
    if (err && err.code) throw err
    const e = new Error('网络不可达，无法获取真实天气')
    e.code = 'NET'
    throw e
  } finally {
    clearTimeout(timer)
  }

  const cur = body.current || {}
  const d = body.daily || {}
  const times = d.time || []

  const outDays = times.map((date, i) => {
    const cond = condOfCode(d.weather_code?.[i])
    const wd = i === 0 ? '今天' : i === 1 ? '明天' : '周' + '日一二三四五六'[new Date(date).getDay()]
    const high = Math.round(d.temperature_2m_max?.[i])
    const low = Math.round(d.temperature_2m_min?.[i])
    const precip = +(d.precipitation_sum?.[i] || 0).toFixed(1)
    const prob = Math.round(d.precipitation_probability_max?.[i] || 0)
    const wind = beaufort((d.wind_speed_10m_max?.[i] || 0) / 3.6)
    const gust = beaufort((d.wind_gusts_10m_max?.[i] || 0) / 3.6)
    const warn = []
    if (precip >= 25) warn.push({ k: 'rain', text: '预报有强降水，溪谷与碎石坡慎行', tone: '#2f6f9e' })
    else if (precip >= 10) warn.push({ k: 'rain', text: '有中雨，岩面与树根打滑', tone: '#2f6f9e' })
    if (cond === 'storm') warn.push({ k: 'storm', text: '有雷阵雨，避开山脊与草甸', tone: '#a9462f' })
    if (gust >= 7) warn.push({ k: 'wind', text: `阵风约 ${gust} 级，帐篷需压石`, tone: '#8a6d2f' })
    if (low <= 3) warn.push({ k: 'cold', text: `夜间约 ${low}℃，加保暖层`, tone: '#4a5a7a' })
    return {
      date: date ? `${Number(date.slice(5, 7))}/${Number(date.slice(8, 10))}` : '',
      wd,
      iso: date,
      high,
      low,
      cond,
      name: COND_NAME[cond],
      icon: '',
      precip,
      prob,
      wind,
      gust,
      warn
    }
  })

  const nowCond = condOfCode(cur.weather_code)
  const now = {
    temp: Math.round(cur.temperature_2m),
    feels: Math.round(cur.apparent_temperature),
    text: COND_NAME[nowCond],
    cond: nowCond,
    humidity: Math.round(cur.relative_humidity_2m),
    wind: beaufort((cur.wind_speed_10m || 0) / 3.6),
    windDir: '',
    precip: +(cur.precipitation || 0).toFixed(1),
    pressure: 0,
    vis: 0
  }

  /* 按真实预报推算的提示（不是官方预警信号） */
  const warnings = []
  const today = outDays[0]
  if (today) for (const w of today.warn) if (!warnings.some((x) => x.k === w.k)) warnings.push(w)
  const rainSoon = outDays.slice(0, 3).some((x) => x.precip >= 10)
  if (rainSoon && !warnings.some((x) => x.k === 'rain'))
    warnings.push({ k: 'rain', text: '未来三天有降水过程，出发前复查路况', tone: '#2f6f9e' })

  const data = {
    source: 'openmeteo',
    days: outDays,
    today,
    warnings,
    now,
    updated: new Date().toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit' }),
    cached: false,
    days7: outDays.length
  }
  cacheSet(id, data)
  return data
}
