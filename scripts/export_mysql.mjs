/**
 * 把站点里的静态数据导出成 MySQL 种子文件：sql/02_seed.sql
 *
 *   node scripts/export_mysql.mjs
 *
 * 数据来源就是前端自己在用的那几个模块，改完 routes.js / spots.js / gear.js
 * 重新跑一次即可，不用手抄 SQL。
 */
import { createHash, randomBytes } from 'node:crypto'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { spots } from '../src/data/spots.js'
import { routes } from '../src/data/routes.js'
import { GEAR } from '../src/data/gear.js'
import { cityMeta } from '../src/data/cities.js'
import { versions } from '../src/data/versions.js'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const OUT = resolve(ROOT, 'sql/02_seed.sql')

/** SQL 字符串字面量：转义反斜杠与单引号，控制字符清掉 */
const q = (v) => {
  if (v === null || v === undefined) return 'NULL'
  const s = String(v)
    .replace(/\\/g, '\\\\')
    .replace(/\r/g, '')
    .replace(/\n/g, '\\n')
    .replace(/'/g, "''")
  return `'${s}'`
}
const n = (v) => (v === null || v === undefined || Number.isNaN(Number(v)) ? 'NULL' : String(Number(v)))
const b = (v) => (v ? 1 : 0)
const j = (v) => q(JSON.stringify(v))

const chunks = (arr, size) => {
  const out = []
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size))
  return out
}

const out = []
const say = (s) => out.push(s)

// ── 1. 城市：先放有内容页的 11 座，再放只在路线里出现的城市 ─────────────────
const cityRows = []
const cityId = new Map()
for (const [name, meta] of Object.entries(cityMeta)) {
  cityRows.push(`(${q(name)}, ${q(meta.province)}, ${n(meta.center?.[0])}, ${n(meta.center?.[1])}, ${q(meta.tagline)}, ${q(meta.season)})`)
  cityId.set(name, cityRows.length)
}
const extraCities = [...new Set(routes.map((r) => r.city))].filter((c) => !cityId.has(c))
for (const name of extraCities) {
  const province = routes.find((r) => r.city === name)?.province ?? null
  cityRows.push(`(${q(name)}, ${q(province)}, NULL, NULL, NULL, NULL)`)
  cityId.set(name, cityRows.length)
}

// 城市没覆盖全就直接报错，别让 NULL 混进 city_id 这种 NOT NULL 列
for (const s of spots) {
  if (!cityId.has(s.city)) throw new Error(`景点「${s.name}」的城市「${s.city}」没有建城市行`)
}
for (const r of routes) {
  if (!cityId.has(r.city)) throw new Error(`路线「${r.name}」的城市「${r.city}」没有建城市行`)
}

// ── 2. 景点 + 标签 ─────────────────────────────────────────────────────────
const spotRows = spots.map(
  (s) =>
    `(${s.id}, ${q(s.name)}, ${cityId.get(s.city)}, ${q(s.district)}, ${q(s.type)}, ${n(s.heat)}, ${q(s.ticket)}, ${q(s.hours)}, ${q(s.reason)}, ${n(s.lat)}, ${n(s.lng)})`
)
const tagRows = []
for (const s of spots) {
  ;(s.tags || []).forEach((t, i) => tagRows.push(`(${s.id}, ${i}, ${q(t)})`))
}

// ── 3. 路线 ────────────────────────────────────────────────────────────────
const routeRows = routes.map((r) => {
  const a = r.access || {}
  return `(${r.id}, ${q(r.name)}, ${q(r.province)}, ${cityId.get(r.city)}, ${q(r.terrain)}, ${q(r.level)}, ${q(r.levelText)}, ${n(r.distance)}, ${n(r.climb)}, ${q(r.days)}, ${q(r.season)}, ${n(r.heat)}, ${b(r.loop)}, ${q(r.hours)}, ${n(r.realKm)}, ${n(r.maxEle)}, ${n(r.minEle)}, ${q(r.desc)}, ${q(r.tips)}, ${q(a.hsr)}, ${q(a.rail)}, ${q(a.bus)}, ${q(a.car)}, ${r.naming ? j(r.naming) : 'NULL'})`
})

const wpRows = []
const trackRows = []
const riskRows = []
const rgRows = []
for (const r of routes) {
  r.waypoints.forEach((w, i) => {
    wpRows.push(
      `(${r.id}, ${i}, ${q(w.name)}, ${n(w.lat)}, ${n(w.lng)}, ${n(w.ele)}, ${q(w.sup)}, ${q(w.note)}, ${q(w.photo)}, ${b(w.camp)})`
    )
  })
  r.track.forEach(([lat, lng], i) => trackRows.push(`(${r.id}, ${i}, ${n(lat)}, ${n(lng)})`))
  ;(r.risk || []).forEach((k, i) => riskRows.push(`(${r.id}, ${i}, ${q(k)})`))
  ;(r.gear || []).forEach((g, i) => rgRows.push(`(${r.id}, ${i}, ${q(g)})`))
}

// ── 4. 装备 ────────────────────────────────────────────────────────────────
const gearRows = GEAR.map(
  (g) => `(${g.id}, ${q(g.group)}, ${q(g.sub)}, ${q(g.name)}, ${b(g.req)}, ${q(g.note)})`
)
const sceneRows = []
for (const g of GEAR) (g.scenes || []).forEach((s) => sceneRows.push(`(${g.id}, ${q(s)})`))

// ── 5. 版本记录 ────────────────────────────────────────────────────────────
const verRows = [...versions]
  .reverse()
  .map(
    (v, i) =>
      `(${q(v.id)}, ${q(v.date)}, ${q(v.tag)}, ${q(v.title)}, ${q(v.summary)}, ${q(v.snapshot)}, ${q(v.live)}, ${j(v.metrics)})`
  )

// ── 6. 演示账号（密码 yejing2026，哈希算法与前端一致） ─────────────────────
const demoName = '阿野'
const demoPhone = '13800000000'
const demoSalt = randomBytes(8).toString('hex')
const demoHash = createHash('sha256').update(`${demoSalt}::yejing2026`).digest('hex')

// ── 输出 ───────────────────────────────────────────────────────────────────
say('-- ============================================================================')
say('-- 野径 · 华南徒步图鉴 —— 种子数据')
const now = new Date()
const pad = (x) => String(x).padStart(2, '0')
const stamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
say(`-- 生成时间：${stamp}（本机时间）`)
say(`-- 统计：${cityRows.length} 城 / ${spots.length} 点位 / ${routes.length} 条路线 / ${GEAR.length} 件装备`)
say(`--       关键点 ${wpRows.length} 个，轨迹点 ${trackRows.length} 个，标签 ${tagRows.length} 个`)
say('-- 由 scripts/export_mysql.mjs 从 src/data/*.js 自动生成，改数据后重跑即可')
say('-- 前置：先执行 sql/01_schema.sql 建库建表')
say('-- ============================================================================')
say('')
say('USE yejing_content;')
say('SET NAMES utf8mb4;')
say('SET FOREIGN_KEY_CHECKS = 0;')
for (const t of [
  'favorites', 'auth_sessions', 'users', 'gear_scenes', 'gear_items',
  'route_risks', 'route_gear', 'route_track', 'route_waypoints', 'routes',
  'spot_tags', 'spots', 'app_versions', 'cities'
]) {
  say(`TRUNCATE TABLE ${t};`)
}
say('SET FOREIGN_KEY_CHECKS = 1;')
say('')

const insert = (title, head, rows, per = 200) => {
  say(`-- ${title}（${rows.length} 行）`)
  for (const part of chunks(rows, per)) {
    say(head)
    say(part.join(',\n') + ';')
  }
  say('')
}

insert('城市', 'INSERT INTO cities (name, province, center_lat, center_lng, tagline, best_season) VALUES', cityRows, 50)
insert('景点', 'INSERT INTO spots (id, name, city_id, district, type, heat, ticket, hours, reason, lat, lng) VALUES', spotRows, 50)
insert('景点标签', 'INSERT INTO spot_tags (spot_id, seq, tag) VALUES', tagRows, 200)
insert(
  '路线',
  'INSERT INTO routes (id, name, province, city_id, terrain, level, level_text, distance_km, climb_m, days, season, heat, is_loop, hours_text, real_km, max_ele, min_ele, `desc`, tips, access_hsr, access_rail, access_bus, access_car, naming_json) VALUES',
  routeRows,
  20
)
insert(
  '关键点',
  'INSERT INTO route_waypoints (route_id, seq, name, lat, lng, ele, supply, note, photo, is_camp) VALUES',
  wpRows,
  100
)
insert('轨迹点', 'INSERT INTO route_track (route_id, seq, lat, lng) VALUES', trackRows, 500)
insert('路线专属装备', 'INSERT INTO route_gear (route_id, seq, item) VALUES', rgRows, 200)
insert('路线风险', 'INSERT INTO route_risks (route_id, seq, risk) VALUES', riskRows, 200)
insert('装备', 'INSERT INTO gear_items (id, group_name, sub_group, name, is_required, note) VALUES', gearRows, 50)
insert('装备场景', 'INSERT INTO gear_scenes (gear_id, scene) VALUES', sceneRows, 200)
insert('版本记录', 'INSERT INTO app_versions (code, released_at, tag, title, summary, snapshot, live_url, metrics) VALUES', verRows, 20)

say('-- 演示账号：手机号 13800000000 / 密码 yejing2026（哈希与前端 digest() 同算法）')
say(
  `INSERT INTO users (nickname, phone, email, salt, password_hash) VALUES (${q(demoName)}, ${q(demoPhone)}, NULL, ${q(demoSalt)}, ${q(demoHash)});`
)
say('')
say('-- 顺手给演示账号加两条收藏：一个景点（按名称）、一条路线（按 id）')
say(`INSERT INTO favorites (user_id, kind, target_id, target_name) VALUES
  (1, 'spot', NULL, ${q('漓江·杨堤至兴坪')}),
  (1, 'route', 1, NULL);`)
say('')
say('-- 自检：三张主表行数应当与站点封面数字一致（76 / 53 / 74）')
say('SELECT (SELECT COUNT(*) FROM spots) AS spots,')
say('       (SELECT COUNT(*) FROM routes) AS routes,')
say('       (SELECT COUNT(*) FROM gear_items) AS gear,')
say('       (SELECT COUNT(*) FROM route_track) AS track_points;')

mkdirSync(dirname(OUT), { recursive: true })
writeFileSync(OUT, out.join('\n') + '\n', 'utf8')

console.log('已生成', OUT)
console.log(`城市 ${cityRows.length}（含仅路线提及 ${extraCities.length}）｜点位 ${spots.length}｜路线 ${routes.length}｜装备 ${GEAR.length}`)
console.log(`关键点 ${wpRows.length}｜轨迹点 ${trackRows.length}｜标签 ${tagRows.length}｜演示账号盐值 ${demoSalt}`)
