import { spotPhotoFiles } from './spotWiki.js'
import { spotPhotoNet } from './spotPhotoNet.js'
import { routePhotoFiles } from './routeWiki.js'
import { moodPhotos } from './moodPhotos.js'
import { spotGallery, routeGallery, spotCity, galTone, galWebFiles } from './gallery.js'
import { lightPhoto, lightCity } from './lightPhoto.js'
import { seasonPhoto } from './seasonPhoto.js'

/**
 * 图片优先级（景点）：
 * 1. 《户外出片图集》—— 用户提供的成套实拍，风格统一，覆盖全部 76 个点位
 * 2. 网络检索图（博主分享）
 * 3. 开放版权图（维基 / Commons，附署名）
 */
const merged = { ...spotPhotoFiles, ...spotPhotoNet }

const GAL_DIR = 'photos/gal/'
const galCredit = { credit: '户外出片图集', license: '网络图源 · 仅作演示' }
const WEB_CREDIT = { credit: '网络公开图源', license: '仅作演示 · 非商业使用' }

/** 按具体文件挑署名口径：图集原图 / 后续替换的高清网络图 */
function creditOf(file) {
  return galWebFiles.includes(file) ? WEB_CREDIT : galCredit
}

/** 某个景点的实景图（图集优先，单图） */
export function spotPhotos(name) {
  const g = spotGallery[name]
  if (g) {
    const c = creditOf(g)
    return [{ src: GAL_DIR + g, title: name, author: c.credit, license: c.license, page: '' }]
  }
  const p = merged[name]
  if (!p) return []
  return (p.all && p.all.length ? p.all : [p.src]).map((src) => ({
    src,
    title: p.title,
    author: p.credit,
    license: p.license,
    page: p.page
  }))
}

export function coverOf(name) {
  const g = spotGallery[name]
  if (g) return GAL_DIR + g
  const p = merged[name]
  return p ? p.src : ''
}

/** 徒步路线封面：图集优先，其次同名山头景点图，最后按地貌取氛围图 */
export function routePhotoOf(r, terrainTheme) {
  const g = routeGallery[r.name]
  if (g) return { src: GAL_DIR + g, title: r.name, ...creditOf(g), page: '' }
  const b = r.name.split('·')[0]
  const rp = routePhotoFiles[b]
  if (rp && rp.src) return rp
  const sg = spotGallery[b]
  const sp = sg ? { src: GAL_DIR + sg } : merged[b]
  if (sp && sp.src) return { src: sp.src, ...creditOf(g), page: '' }
  const m = moodPhoto((terrainTheme && terrainTheme[r.terrain]) || 'mountain', 'sunset')
  return m ? { src: m.src, credit: m.credit, page: m.page, title: '同类地貌参考' } : null
}

/**
 * 日落 / 夜景：不再用一套全国通用的氛围图（每个景点都长得一样），
 * 改成从同一座城市里挑别的点位实拍，按 id 轮换，同一个景点两张也不重复。
 * 这里的名单是逐张看过画面挑的「黄昏感 / 夜灯感」照片。
 */
const CITY_MOOD = {
  桂林: {
    sunset: ['漓江·杨堤至兴坪', '全州天湖', '相公山观景台', '兴坪古镇'],
    night: ['兴坪古镇', '漓江·杨堤至兴坪', '全州天湖']
  },
  广州: {
    sunset: ['海珠湖', '莲花山', '白云山', '广州塔'],
    night: ['广州塔', '永庆坊', '海珠湖']
  },
  深圳: {
    sunset: ['深圳湾公园', '人才公园', '大梅沙', '杨梅坑'],
    night: ['人才公园', '深圳湾公园']
  },
  长沙: {
    sunset: ['橘子洲', '岳麓山', '洋湖湿地'],
    night: ['太平老街', '铜官窑古镇', '橘子洲']
  },
  湘西: {
    sunset: ['矮寨大桥', '边城茶峒', '凤凰古城', '猛洞河漂流'],
    night: ['凤凰古城', '芙蓉镇', '矮寨大桥']
  },
  张家界: {
    sunset: ['七星山', '天门山', '宝峰湖', '天子山'],
    night: ['天门山', '七星山', '张家界国家森林公园']
  },
  惠州: {
    sunset: ['双月湾', '巽寮湾', '大亚湾', '惠州西湖'],
    night: ['巽寮湾', '双月湾']
  },
  郴州: {
    sunset: ['高椅岭', '飞天山', '仰天湖草原', '便江'],
    night: ['仰天湖草原', '高椅岭', '苏仙岭']
  }
}

/**
 * 同城实拍：给我一个景点，返回该城市另一处点位的照片（用于日落 / 夜景格）。
 * 只在「画面色调真的像那个时段」的图里挑：夜景要求很暗，黄昏要求偏暖、
 * 且不能是大白天的亮图——否则会出现「日落与晚霞」配一张正午绿树的情况。
 */
export function nearbyMood(spot, slot, exclude = []) {
  if (!spot) return null
  const city = spot.city || spotCity[spot.name]
  const citySpots = Object.keys(spotGallery).filter((n) => spotCity[n] === city)
  const curated = ((CITY_MOOD[city] || {})[slot] || []).filter(
    (n) => n !== spot.name && spotGallery[n] && !exclude.includes(n)
  )
  const base = curated.length ? curated : citySpots.filter((n) => n !== spot.name && !exclude.includes(n))
  const pool = base.filter((n) => toneFits(n, slot))
  if (!pool.length) return null
  const pick = pickByTone(pool, slot, spot.id)
  return { src: GAL_DIR + spotGallery[pick], name: pick, city, own: false }
}

/** 画面色调是否像这个时段 */
function toneFits(name, slot) {
  const t = galTone[spotGallery[name]]
  if (!t) return false
  if (slot === 'night') return t.l <= 88
  return t.w >= 8 && t.l >= 45 && t.l <= 175
}

/** 该点位自己的黄昏 / 夜景实拍；没有就退到同城最贴合那个时段的一张 */
export function lightPhotoOf(name, slot, city) {
  const p = lightPhoto[name]
  if (p && p[slot]) return { src: p[slot], name, own: true, city: '' }
  const c = lightCity[city]
  if (c && c[slot]) return { src: c[slot].src, name: c[slot].from, own: false, city }
  return null
}

/** 某个点位的四季实拍（春 / 夏 / 秋 / 冬，缺季不补假图） */
export function seasonPhotosOf(name) {
  const s = seasonPhoto[name]
  if (!s) return []
  return ['春', '夏', '秋', '冬'].filter((k) => s[k]).map((k) => ({ k, src: s[k] }))
}

/**
 * 同城候选里挑更贴合时段的一张：
 * 夜景挑最暗的、黄昏挑最暖（R-B 最大）的，但只取前 3 名再按景点 id 轮换，
 * 避免同城所有景点都落到同一张图。
 */
function pickByTone(pool, slot, seed = 0) {
  const tone = (n) => galTone[spotGallery[n]] || { l: 128, w: 0 }
  const ranked = [...pool].sort((a, b) =>
    slot === 'night' ? tone(a).l - tone(b).l : tone(b).w - tone(a).w
  )
  const top = ranked.slice(0, Math.min(3, ranked.length))
  return top[Math.abs(seed || 0) % top.length]
}

// 主题图片不全时的兜底顺序
const THEME_FALLBACK = {
  peak: ['mountain', 'grass', 'sea'],
  lake: ['river', 'sea', 'terrace'],
  river: ['lake', 'sea'],
  forest: ['mountain', 'grass'],
  danxia: ['mountain', 'grass'],
  cave: ['town', 'city'],
  terrace: ['grass', 'lake'],
  grass: ['mountain'],
  town: ['city'],
  sea: ['lake', 'river'],
  city: ['town'],
  mountain: ['grass', 'peak']
}

/** 日落 / 夜景 氛围参考图（按地貌主题，缺图时按相近地貌兜底） */
export function moodPhoto(theme, slot) {
  const direct = moodPhotos[`${theme}-${slot}`]
  if (direct) return direct
  for (const t of THEME_FALLBACK[theme] || []) {
    const p = moodPhotos[`${t}-${slot}`]
    if (p) return p
  }
  const alt = slot === 'sunset' ? 'night' : 'sunset'
  return moodPhotos[`${theme}-${alt}`] || moodPhotos[`mountain-${alt}`] || null
}
