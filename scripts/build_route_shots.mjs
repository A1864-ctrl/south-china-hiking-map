// 生成 src/data/routeShots.js：每条路线 封面 + 最近点位的四季/晚霞/夜景
import { writeFileSync } from 'node:fs'
import { routes } from '../src/data/routes.js'
import { spots } from '../src/data/spots.js'
import { seasonPhoto } from '../src/data/seasonPhoto.js'
import { lightPhoto } from '../src/data/lightPhoto.js'
import { routeGallery } from '../src/data/gallery.js'

const hav = (a, b) => {
  const R = 6371
  const r = Math.PI / 180
  const d1 = (b[0] - a[0]) * r
  const d2 = (b[1] - a[1]) * r
  const x = Math.sin(d1 / 2) ** 2 + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(d2 / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(x))
}

const SEASON_LABEL = { 春: '春 · 3-5月', 夏: '夏 · 6-9月', 秋: '秋 · 10-11月', 冬: '冬 · 12-2月' }

const out = {}
for (const r of routes) {
  const shots = []
  const g = routeGallery[r.name]
  if (g) {
    shots.push({
      k: '本线',
      src: 'photos/gal/' + g,
      label: '本线实拍 · 图集原图',
      title: r.name,
      note: `${r.city} · ${r.terrain}`
    })
  }

  let best = null
  let bd = 1e9
  for (const s of spots) {
    if (!seasonPhoto[s.name]) continue
    const d = hav([r.center[0], r.center[1]], [s.lat, s.lng])
    if (d < bd) {
      bd = d
      best = s.name
    }
  }

  if (best && bd <= 160) {
    const base = r.name.split('·')[0]
    const same = best === r.name || best.includes(base) || base.includes(best)
    const tag = same ? '同名点位' : `附近实拍 · ${best}（${Math.round(bd)}km）`
    const sp = seasonPhoto[best] || {}
    for (const k of ['春', '夏', '秋', '冬']) {
      if (sp[k]) {
        shots.push({ k, src: sp[k], label: `${SEASON_LABEL[k]} · ${tag}`, title: `${r.name} · ${k}`, note: `取景自 ${best}` })
      }
    }
    const lp = lightPhoto[best] || {}
    if (lp.sunset) {
      shots.push({ k: '晚霞', src: lp.sunset, label: `晚霞 · 日落前 40 分钟 · ${tag}`, title: `${r.name} · 晚霞`, note: `取景自 ${best}` })
    }
    if (lp.night) {
      shots.push({ k: '夜色', src: lp.night, label: `夜色 · 亮灯后 · ${tag}`, title: `${r.name} · 夜色`, note: `取景自 ${best}` })
    }
  }
  out[r.name] = shots
}

const lines = ['// 每条路线的影像集：本线封面 + 最近点位的四季 / 晚霞 / 夜色（附来源标注）',
  '// 由 scripts/build_route_shots.mjs 生成，图片全部来自已核验的本地图库',
  'export const routeShots = {']
for (const [name, shots] of Object.entries(out)) {
  const items = shots
    .map((s) => `{ k: ${JSON.stringify(s.k)}, src: ${JSON.stringify(s.src)}, label: ${JSON.stringify(s.label)}, title: ${JSON.stringify(s.title)}, note: ${JSON.stringify(s.note)} }`)
    .join(', ')
  lines.push(`  ${JSON.stringify(name)}: [${items}],`)
}
lines.push('}')
lines.push('')

writeFileSync(new URL('../src/data/routeShots.js', import.meta.url), lines.join('\n'), 'utf8')
const counts = Object.values(out).map((v) => v.length)
console.log('路线', counts.length, '影像', counts.reduce((a, b) => a + b, 0), '每线', Math.min(...counts), '-', Math.max(...counts))
console.log('只有封面的', Object.entries(out).filter(([, v]) => v.length <= 1).map(([k]) => k).join(' / '))
