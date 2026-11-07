// 外部跳转链接：两步路 / 小红书 / 抖音 / 高德导航
const enc = encodeURIComponent

/** 两步路「搜索全部」——用户给的格式，换关键词即可定位到该路线的轨迹 */
export const twobulu = (kw) =>
  `https://www.2bulu.com/search/search_all.htm?searchRange=all&keyword=${enc(kw)}`

/** 两步路轨迹库（只看轨迹） */
export const twobuluTrack = (kw) =>
  `https://www.2bulu.com/search/search_all.htm?searchRange=track&keyword=${enc(kw)}`

export const xhs = (kw) => `https://www.xiaohongshu.com/search_result?keyword=${enc(kw)}`
export const dy = (kw) => `https://www.douyin.com/search/${enc(kw)}`

/** 高德网页导航：终点用「名称 + 经纬度」，微信/浏览器都能打开 */
export const amapNav = (lat, lng, name) =>
  `https://uri.amap.com/marker?position=${lng},${lat}&name=${enc(name)}&src=yejing&coordinate=wgs84&callnative=0`

/** 天地图网页版（卫星） */
export const tdtWeb = (lat, lng, zoom = 13) =>
  `https://map.tianditu.gov.cn/?lnglat=${lng},${lat}&zoom=${zoom}`
