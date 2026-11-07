/**
 * 点位天气：按经纬度 + 海拔生成山区天气模型
 * ─ 纯前端演示模型（不联网），用确定性哈希保证「同一地点同一天结果稳定」，刷新不会跳变
 * ─ 温度按海拔递减率 0.6℃/100m 修正；降水、风力、预警按月份与地形给概率
 */
const MONTH_HIGH = [14, 16, 19, 24, 28, 31, 33, 33, 31, 27, 22, 16]

function hash(seed) {
  const x = Math.sin(seed * 12.9898 + 78.233) * 43758.5453
  return x - Math.floor(x)
}

const COND = [
  { k: 'sun', name: '晴', icon: '☀' },
  { k: 'cloud', name: '多云', icon: '☁' },
  { k: 'over', name: '阴', icon: '☁' },
  { k: 'rain', name: '阵雨', icon: '🌧' },
  { k: 'storm', name: '雷阵雨', icon: '⛈' },
  { k: 'snow', name: '雪', icon: '❄' },
  { k: 'fog', name: '雾', icon: '🌫' }
]

function condOf(r, month) {
  // 4–9 月对流强，阵雨/雷雨概率高；10–3 月以晴与多云为主
  const wet = month >= 3 && month <= 8
  if (r > (wet ? 0.82 : 0.93)) return COND[4]
  if (r > (wet ? 0.6 : 0.85)) return COND[3]
  if (r > (wet ? 0.42 : 0.7)) return COND[2]
  if (r > 0.18) return COND[1]
  if (r > 0.07) return COND[5]
  return COND[0]
}

function fmtDate(d) {
  return `${d.getMonth() + 1}/${d.getDate()}`
}
const WD = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

/**
 * @param {number} lat 纬度
 * @param {number} lng 经度
 * @param {{ele?:number, days?:number, from?:Date}} opt
 */
export function mountainWeather(lat, lng, opt = {}) {
  const ele = Number(opt.ele) || 0
  const days = opt.days || 7
  const from = opt.from || new Date()
  const base = new Date(from.getFullYear(), from.getMonth(), from.getDate())
  const seedBase = Math.round(lat * 1000) * 7 + Math.round(lng * 1000) * 13

  const list = []
  for (let i = 0; i < days; i++) {
    const d = new Date(base.getTime() + i * 86400000)
    const m = d.getMonth()
    const seed = seedBase + i * 977 + m * 31 + d.getDate() * 17
    const r1 = hash(seed)
    const r2 = hash(seed + 3.7)
    const r3 = hash(seed + 9.1)

    // 低地日最高温 → 按纬度与海拔修正
    const lowland = MONTH_HIGH[m] - (lat - 23) * 1.15
    const lapse = (ele * 0.6) / 100
    const swing = 6.5 + r2 * 4
    const high = Math.round(lowland - lapse + (r1 - 0.5) * 4)
    const low = Math.round(high - swing)

    const cond = condOf(r2, m)
    const rainy = cond.k === 'rain' || cond.k === 'storm'
    const precip = rainy ? +(2 + r3 * (cond.k === 'storm' ? 42 : 16)).toFixed(1) : r3 > 0.86 ? +(r3 * 2).toFixed(1) : 0
    const prob = rainy ? Math.round(55 + r1 * 40) : Math.round(r1 * 35)
    const wind = rainy ? Math.round(3 + r2 * 3) : Math.round(1 + r2 * 3)
    const gust = Math.min(12, wind + Math.round(1 + r3 * 3))

    const warn = []
    if (precip >= 25) warn.push({ k: 'rain', text: '短时强降水，溪谷与碎石坡慎行', tone: '#2f6f9e' })
    else if (precip >= 10) warn.push({ k: 'rain', text: '有中雨，注意岩面与树根打滑', tone: '#2f6f9e' })
    if (cond.k === 'storm') warn.push({ k: 'storm', text: '雷电预警：11–16 时避免山脊与草甸', tone: '#a9462f' })
    if (gust >= 7) warn.push({ k: 'wind', text: `阵风 ${gust} 级，帐篷需压石加固`, tone: '#8a6d2f' })
    if (low <= 3) warn.push({ k: 'cold', text: `夜间 ${low}℃，需加保暖层`, tone: '#4a5a7a' })
    if (high >= 34 && prob < 30) warn.push({ k: 'fire', text: '高温干燥，森林火险偏高', tone: '#a9462f' })

    list.push({
      date: fmtDate(d),
      wd: i === 0 ? '今天' : i === 1 ? '明天' : WD[d.getDay()],
      iso: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`,
      high,
      low,
      cond: cond.k,
      name: cond.name,
      icon: cond.icon,
      precip,
      prob,
      wind,
      gust,
      warn
    })
  }

  const today = list[0]
  const warnings = []
  for (const w of today.warn) if (!warnings.some((x) => x.k === w.k)) warnings.push(w)
  const rainSoon = list.slice(0, 3).some((x) => x.precip >= 10)
  if (rainSoon && !warnings.some((x) => x.k === 'rain'))
    warnings.push({ k: 'rain', text: '未来三天有降水过程，出发前复查路况', tone: '#2f6f9e' })

  // 云海 / 星空：雨后转晴 + 温差大 → 云海概率高
  const seaOfCloud = Math.round(
    Math.max(0, Math.min(95, (today.prob > 40 ? 30 : 55) + (today.high - today.low) * 3 + hash(seedBase + 41) * 20))
  )
  const stars = Math.round(Math.max(0, Math.min(98, 100 - today.prob - today.wind * 6 - (today.cond === 'fog' ? 30 : 0))))

  return {
    lat,
    lng,
    ele,
    days: list,
    today,
    warnings,
    seaOfCloud,
    stars,
    updated: `${new Date().getHours()}:${String(new Date().getMinutes()).padStart(2, '0')}`
  }
}

export const WARN_META = {
  rain: { label: '降水', tone: '#2f6f9e' },
  storm: { label: '雷电', tone: '#a9462f' },
  wind: { label: '大风', tone: '#8a6d2f' },
  cold: { label: '降温', tone: '#4a5a7a' },
  fire: { label: '火险', tone: '#c0392b' }
}

export const COND_NAME = Object.fromEntries(COND.map((c) => [c.k, c]))
