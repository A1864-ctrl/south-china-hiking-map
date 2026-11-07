// 按每条徒步路线的天数、里程、爬升、地形、补给点，推导出专属装备清单
import { GEAR, GEAR_GROUPS, GROUP_DESC } from './gear.js'

const num = (v) => (typeof v === 'number' ? v : parseFloat(v) || 0)

/** 导出后的路线只有 waypoints（含 km 与 sup），没有原始 pts */
const ptsOf = (r) => r.waypoints || r.pts || []

/** 天数：'1天' / '2天' / '3-4天' 都转成数字 */
export function daysOf(r) {
  const m = String(r.days || '').match(/(\d+)/)
  return m ? Number(m[1]) : 1
}

/**
 * 这条路线属于哪种场景：天数决定要不要背帐篷，难度只影响额外提醒。
 * 不能因为「单日 30km 且难」就让人带帐篷。
 */
export function routeScene(r) {
  const d = daysOf(r)
  if (d >= 3) return '长线高难度'
  if (d === 2 || ptsOf(r).some((p) => p.camp)) return '重装露营'
  return '单日徒步'
}

/** 粗略耗时：平路 3.2km/h，每 500m 爬升折 1 小时 */
export function hoursOf(r) {
  const h = num(r.distance) / 3.2 + num(r.climb) / 500
  return Math.round(h * 10) / 10
}

/* ── 地貌族 ── */
const FAMILY = {
  海岸礁石: 'coast', 海岸: 'coast', 海岛: 'coast', 海滩: 'coast',
  溪谷石阶: 'creek', 溪谷瀑布: 'creek', 峰林溪谷: 'creek', 峡谷: 'creek', 峡谷山峰: 'creek',
  高山草甸: 'alpine', 山峰草甸: 'alpine', 高原雪山: 'alpine', 高山石海: 'alpine', 山脊岩壁: 'alpine',
  森林古道: 'forest', 森林山峰: 'forest', 原始森林: 'forest', 茶山: 'forest',
  丹霞地貌: 'danxia', 丹霞: 'danxia',
  喀斯特田园: 'karst', 峰林: 'karst',
  城市山: 'city', 石阶古道: 'stone', 古道: 'stone',
  花岗岩峰林: 'granite', 花岗岩: 'granite', 山峰野线: 'granite', 山峰: 'granite', 山峰栈道: 'granite'
}
const fam = (r) => FAMILY[r.terrain] || 'granite'

/* ── 该地貌额外要带的东西（不在这 74 项里，属于路线专属） ── */
const EXTRA = {
  coast: [
    { name: '防滑礁石手套', why: '海岸线要手脚并用翻礁石，手套防割伤也防滑', req: true },
    { name: '手机防水袋', why: '浪打上来、手是湿的，手机放兜里最容易进水', req: true },
    { name: '快干短裤', why: '贴着水线走，裤脚一定会湿，快干比防水更实用', req: false }
  ],
  creek: [
    { name: '溯溪鞋或旧运动鞋', why: '溪谷段石面长苔，徒步鞋底反而更滑', req: true },
    { name: '一套干爽替换衣物（车内存放）', why: '出溪谷基本全身湿透，回到车上必须换', req: true }
  ],
  alpine: [
    { name: '薄羽绒或抓绒（即使夏天）', why: '山顶比山下低 6-8℃，风一起来体感骤降', req: true },
    { name: '防风帽 + 手套', why: '草甸与山脊没有遮挡，风是主要失温原因', req: false }
  ],
  forest: [
    { name: '长袖长裤（不穿短裤）', why: '林下蚊虫、茅草、树枝都会刮伤', req: true },
    { name: '驱蚊液（含避蚊胺）', why: '南方山林 4-10 月蚊虫密集', req: true }
  ],
  danxia: [
    { name: '攀爬手套', why: '红色砂岩表面粗糙，扶一把就磨破手', req: false }
  ],
  karst: [
    { name: '防晒（帽子+袖套）', why: '峰林一带没有树荫，正午暴晒', req: true }
  ],
  city: [
    { name: '轻便腰包', why: '路线短、补给方便，不需要大包', req: false }
  ],
  stone: [
    { name: '护膝 + 登山杖', why: '连续石阶下坡对膝盖冲击最大，这两样是硬需求', req: true }
  ],
  granite: [
    { name: '手套（碎石段）', why: '花岗岩碎石松动，下撤时手撑地很常见', req: false }
  ]
}

/* ── 单条装备的「为什么带」，按路线数字给理由 ── */
function whyOf(it, r, ctx) {
  const d = num(r.distance)
  const up = num(r.climb)
  const f = fam(r)
  const map = {
    1: `全程 ${d}km，贴身层湿了会一路发冷，速干是底线`,
    2: `${f === 'forest' ? '林下树枝多' : '防晒与防刮'}，长裤比短裤更省事`,
    5: `${d}km 走下来脚会胀，厚袜能少起一半水泡`,
    7: ctx.cold ? `夜间营地约 ${ctx.nightLow}℃ 上下，薄抓绒是性价比最高的一层` : '',
    10: ctx.rain ? `${r.season} 是这条线的主要窗口，山区阵雨来得快，硬壳不能省` : '山区天气说变就变，防风层是保命层',
    14: up > 1200 ? `累计爬升 ${up}m，中高帮能明显减少崴脚` : '碎石与土路混合，中帮更稳',
    23: `装 ${ctx.pack}，${ctx.days} 天${ctx.days > 1 ? '重装' : '轻装'}刚好`,
    28: ctx.camp ? `沿途有营地（${ctx.campNames}），需要过夜` : '',
    30: ctx.camp ? `营地夜间约 ${ctx.nightLow}℃，睡袋温标按这个再留 5℃ 余量` : '',
    31: ctx.camp ? '山地地面凉，防潮垫比睡袋更影响睡眠' : '',
    35: up > 1000 ? `爬升 ${up}m、下降同样多，双杖能省 20% 腿力` : '碎石与湿滑路段用得上',
    36: d >= 15 ? `${d}km 且下坡长，护膝是膝盖的保险` : '',
    40: `按 ${ctx.water}L 备水（${ctx.hours}h 行程估算）`,
    41: ctx.hours >= 5 ? `行程 ${ctx.hours}h，水袋边走边喝比停下来掏水壶实际` : '',
    42: ctx.hasWater ? '沿途有溪水但不确定水质，过滤器可以少背 1L 水' : '全程无可靠水源，只能背',
    44: ctx.camp ? '露营要煮水做饭，注意林区防火规定' : '',
    49: `备 ${ctx.snacks} 份路餐，每 2-3 小时补一次`,
    50: `${ctx.hours}h 大量出汗，电解质比纯水更能防抽筋`,
    53: ctx.night ? '行程含夜爬或可能摸黑下撤，头灯必须带备用电池' : '天黑前下不了山是常态，头灯是兜底',
    55: '这条线岔路多，提前在两步路下好离线轨迹',
    62: ctx.remote ? '中段没有手机信号，急救包必须自己带全' : '常规急救耗材',
    68: f === 'coast' || f === 'karst' ? '海边与峰林都没有遮阴，SPF50 起步' : '高海拔与草甸紫外线强'
  }
  return map[it.id] || ''
}

/**
 * 生成一条路线的装备清单。
 * 返回 { scene, groups, extras, stats, warnings }
 */
export function routeGear(r) {
  const scene = routeScene(r)
  const days = daysOf(r)
  const hours = hoursOf(r)
  const up = num(r.climb)
  const pts = ptsOf(r)
  const camp = pts.some((p) => p.camp)
  const campNames = pts.filter((p) => p.camp).map((p) => p.name).join('、') || '无固定营地'
  const hasWater = pts.some((p) => /溪|水|泉|井/.test(p.sup || ''))
  const remote = /无补给|无信号|无人区/.test(`${r.tips || ''}${r.desc || ''}`) || days >= 2
  const night = /夜|日出|摸黑|头灯/.test(`${r.tips || ''}${r.desc || ''}`)
  const rain = /雨|暴雨|雨季|雷/.test(`${r.tips || ''}`)
  const cold = days >= 2 || /雪|冰|低温|0℃|严寒/.test(`${r.tips || ''}`)
  const nightLow = days >= 2 ? '5-10' : '12-15'
  const pack = days >= 3 ? '60-70L' : days === 2 ? '40-55L' : '20-30L'
  // 沿途能补水就少背：按每公里 0.1L 估，有水源打 6 折
  const waterRaw = hours * 0.45 * (hasWater ? 0.62 : 1)
  const water = Math.min(4.5, Math.max(0.5, Math.round(waterRaw * 2) / 2))
  const snacks = Math.max(1, Math.ceil(hours / 3))
  const ctx = { days, hours, up, camp, campNames, hasWater, remote, night, rain, cold, nightLow, pack, water, snacks }

  // 该场景下要带的 74 项里的装备
  const base = GEAR.filter((it) => it.scenes.includes(scene))

  // 按地貌额外补充的项（把上面 EXTRA 里的也并进对应分组）
  const groups = GEAR_GROUPS.map((g) => {
    const items = base
      .filter((it) => it.group === g)
      .map((it) => ({ ...it, why: whyOf(it, r, ctx) }))
    return { group: g, desc: GROUP_DESC[g], items }
  }).filter((g) => g.items.length)

  // 路线专属加项，挂在「行进辅助装备」后面单独一组
  const extras = (EXTRA[fam(r)] || []).map((x) => ({ ...x }))

  const warnings = []
  if (remote) warnings.push(`中段无补给无信号：水与路餐按全程自带，别指望中途补`)
  if (camp) warnings.push(`营地 ${campNames}：夜间温差大，睡袋与防潮垫按 ${nightLow}℃ 准备`)
  if (rain) warnings.push(`${r.season} 山区多阵雨，硬壳与背包防雨罩都要带`)
  if (night) warnings.push('行程含夜段或日出机位，头灯 + 备用电池必带')
  if (!hasWater) warnings.push('沿途没有可靠水源，按上面水量一次性背足')

  return {
    scene,
    stats: { days, hours, distance: num(r.distance), climb: up, water, snacks, pack },
    groups,
    extras,
    warnings
  }
}
