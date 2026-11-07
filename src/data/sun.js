// 本地太阳位置计算（NOAA 简化算法），用于「日落与晚霞」给出当天真实时刻与太阳落点方位
const RAD = Math.PI / 180

function params(date) {
  const start = Date.UTC(date.getFullYear(), 0, 0)
  const doy = Math.floor((Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) - start) / 86400000)
  const g = (2 * Math.PI / 365) * (doy - 1 + 0.5)
  const eqtime =
    229.18 *
    (0.000075 +
      0.001868 * Math.cos(g) -
      0.032077 * Math.sin(g) -
      0.014615 * Math.cos(2 * g) -
      0.040849 * Math.sin(2 * g))
  const decl =
    0.006918 -
    0.399912 * Math.cos(g) +
    0.070257 * Math.sin(g) -
    0.006758 * Math.cos(2 * g) +
    0.000907 * Math.sin(2 * g) -
    0.002697 * Math.cos(3 * g) +
    0.00148 * Math.sin(3 * g)
  return { eqtime, decl }
}

/** 太阳高度角为 h 度的时刻（分钟，本地时间 UTC+8）；不存在时返回 null */
function minuteAt(lat, lng, decl, eqtime, h) {
  const cosH =
    (Math.sin(h * RAD) - Math.sin(lat * RAD) * Math.sin(decl)) /
    (Math.cos(lat * RAD) * Math.cos(decl))
  if (cosH > 1 || cosH < -1) return null
  const H = Math.acos(cosH) / RAD
  // 日落用减号（NOAA：sunset = 720 - 4*(longitude - HA) - eqtime）
  const utc = 720 - 4 * (lng - H) - eqtime
  return utc + 8 * 60
}

/**
 * 太阳高度角为 h 度时的「日出」时刻（分钟，本地时间 UTC+8）。
 * 与 minuteAt 同一套 NOAA 公式，只是取 +H 的解，用于天气页给出日出时间。
 */
function minuteRise(lat, lng, decl, eqtime, h) {
  const cosH =
    (Math.sin(h * RAD) - Math.sin(lat * RAD) * Math.sin(decl)) /
    (Math.cos(lat * RAD) * Math.cos(decl))
  if (cosH > 1 || cosH < -1) return null
  const H = Math.acos(cosH) / RAD
  const utc = 720 - 4 * (lng + H) - eqtime
  return utc + 8 * 60
}

const pad = (n) => String(n).padStart(2, '0')
function fmt(min) {
  if (min == null) return '--:--'
  const m = Math.round(min)
  return `${pad(Math.floor(((m % 1440) + 1440) % 1440 / 60))}:${pad(((m % 60) + 60) % 60)}`
}

/** 方位角数字 → 中文描述 */
function azText(az) {
  const names = [
    [0, '正北'], [22.5, '北偏东'], [45, '东北'], [67.5, '东偏北'],
    [90, '正东'], [112.5, '东偏南'], [135, '东南'], [157.5, '南偏东'],
    [180, '正南'], [202.5, '南偏西'], [225, '西南'], [247.5, '西偏南'],
    [270, '正西'], [292.5, '西偏北'], [315, '西北'], [337.5, '北偏西'], [360, '正北']
  ]
  let best = names[0]
  let diff = 999
  for (const [deg, label] of names) {
    const d = Math.abs(((az - deg + 540) % 360) - 180)
    if (d < diff) {
      diff = d
      best = [deg, label]
    }
  }
  const off = Math.round(Math.abs(((az - best[0] + 540) % 360) - 180))
  // 正北/正东/正南/正西 这类直接用名字；其余补上偏差度数
  const exact = ['正北', '正东', '正南', '正西'].includes(best[1])
  return { label: best[1], deg: Math.round(az), off, exact }
}

/**
 * 当天该点位的日落信息。
 * 返回 { sunset, golden, blue, az, goldenStart }，单位均为「本地时间」字符串。
 */
export function sunInfo(lat, lng, date = new Date()) {
  if (typeof lat !== 'number' || typeof lng !== 'number') return null
  const { eqtime, decl } = params(date)
  const sunsetMin = minuteAt(lat, lng, decl, eqtime, -0.833)
  const sunriseMin = minuteRise(lat, lng, decl, eqtime, -0.833)
  if (sunsetMin == null) return null
  const goldenMin = minuteAt(lat, lng, decl, eqtime, 6)
  const blueMin = minuteAt(lat, lng, decl, eqtime, -6)
  const az = (Math.acos(Math.max(-1, Math.min(1, Math.sin(decl) / Math.cos(lat * RAD)))) / RAD)
  return {
    sunrise: fmt(sunriseMin),
    sunset: fmt(sunsetMin),
    goldenStart: fmt(goldenMin),
    goldenEnd: fmt(sunsetMin - 8),
    blue: `${fmt(sunsetMin + 10)}–${fmt(blueMin)}`,
    az: azText(360 - az),
    minutesToSunset: sunsetMin
  }
}

/** 按地貌给出「光线怎么走」与「参数怎么给」 */
export const LIGHT_TIP = {
  sea: {
    light: '太阳贴海平面时，浪花会被打成一片金色噪点；落海后 10–25 分钟的粉紫色才是海边的重头戏，很多人拍完就收机器，正好错过。',
    gear: 'f/11 · ISO 100 · 2–8 秒慢门（三脚架+ND8）· 前景留 1/3 礁石或沙滩'
  },
  mountain: {
    light: '山上的日落比山下早 20–30 分钟，最好日落前 60 分钟登顶；太阳一落体感骤降 5℃，收工前把外套穿上。',
    gear: 'f/8 · ISO 100 · 包围曝光 ±1.5EV · 长焦压缩山脊层叠'
  },
  peak: {
    light: '峰林靠侧逆光才有层次：太阳压低后山体正面发暗、边缘发亮，这 15 分钟是唯一能拍出「峰墙」质感的时间。',
    gear: 'f/9 · ISO 200 · 70–200mm 长焦 · 带渐变灰压天空'
  },
  river: {
    light: '水面是最好的反光板：太阳落到对岸山脊线后，水面会把天光翻倍反射回来，比天空本身更亮，注意别过曝。',
    gear: 'f/8 · ISO 100 · 偏振镜压反光 · 1/60 以上防止船影糊'
  },
  lake: {
    light: '湖面平静时用长曝把波纹抹平，倒影会变成一整块颜色；起风就改拍逆光的水面碎金。',
    gear: 'f/11 · ISO 100 · 4–15 秒长曝 · 偏振镜按需旋到 70%'
  },
  town: {
    light: '古镇日落的看点是「灯亮起来但天还没黑」的那 20 分钟：天空是深蓝、灯笼是暖橘，一冷一暖最好看。',
    gear: 'f/8 · ISO 400 · 1/15 手持或 1 秒上架 · 白平衡 4000K 保留蓝调'
  },
  city: {
    light: '城市日落要抢「蓝调时刻」：天空还有颜色、楼体灯已经亮，这段只有 20 分钟左右，比全黑的夜景更有层次。',
    gear: 'f/8 · ISO 200 · 三脚架 2 秒 · 包围曝光保住霓虹高光'
  },
  danxia: {
    light: '丹霞的红色在低角度光线下最饱和，太阳一升高就发灰；日落前 30 分钟是全天红度最高的一段。',
    gear: 'f/9 · ISO 100 · 偏振镜增强红色 · 避免直射阳光打进镜头'
  },
  terrace: {
    light: '梯田灌水期是「天空复印机」：太阳落山后天空变色，田埂上每一格水面都会跟着变，比日落本身更好看。',
    gear: 'f/11 · ISO 100 · 2–6 秒 · 站高一级俯拍保留曲线'
  },
  forest: {
    light: '林子里看不到太阳本身，看的是穿林光：太阳高度降到 15° 以下，光柱会斜穿过树冠，雾天效果翻倍。',
    gear: 'f/5.6 · ISO 400 · 点测光对准亮部 · 收一档曝光保住暗部细节'
  },
  grass: {
    light: '草甸日落是「整片发光」：太阳贴地时草尖全部镶金边，逆光蹲低拍能拍到一层毛茸茸的光。',
    gear: 'f/8 · ISO 100 · 逆光 +2/3EV · 用草穗做前景虚化'
  },
  cave: {
    light: '溶洞没有日落，出洞那一刻的强反差才是重点：让眼睛适应 30 秒再按快门，别一出来就拍。',
    gear: 'f/4 · ISO 1600 · 手持 1/30 · 别开闪光灯'
  }
}
