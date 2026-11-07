// 地理与轨迹工具：坐标转换、伪随机轨迹生成、高程剖面生成、GPX 导出

export function mulberry32(a) {
  return function () {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// WGS84 -> GCJ-02，让点位在高德底图上不至于偏移几百米
const PI = Math.PI
const A = 6378245.0
const EE = 0.00669342162296594323

function outOfChina(lat, lng) {
  return lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271
}

function transformLat(x, y) {
  let ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x))
  ret += ((20.0 * Math.sin(6.0 * x * PI) + 20.0 * Math.sin(2.0 * x * PI)) * 2.0) / 3.0
  ret += ((20.0 * Math.sin(y * PI) + 40.0 * Math.sin((y / 3.0) * PI)) * 2.0) / 3.0
  ret += ((160.0 * Math.sin((y / 12.0) * PI) + 320 * Math.sin((y * PI) / 30.0)) * 2.0) / 3.0
  return ret
}

function transformLng(x, y) {
  let ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x))
  ret += ((20.0 * Math.sin(6.0 * x * PI) + 20.0 * Math.sin(2.0 * x * PI)) * 2.0) / 3.0
  ret += ((20.0 * Math.sin(x * PI) + 40.0 * Math.sin((x / 3.0) * PI)) * 2.0) / 3.0
  ret += ((150.0 * Math.sin((x / 12.0) * PI) + 300.0 * Math.sin((x / 30.0) * PI)) * 2.0) / 3.0
  return ret
}

export function wgs84ToGcj02(lat, lng) {
  if (outOfChina(lat, lng)) return [lat, lng]
  let dLat = transformLat(lng - 105.0, lat - 35.0)
  let dLng = transformLng(lng - 105.0, lat - 35.0)
  const radLat = (lat / 180.0) * PI
  let magic = Math.sin(radLat)
  magic = 1 - EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  dLat = (dLat * 180.0) / (((A * (1 - EE)) / (magic * sqrtMagic)) * PI)
  dLng = (dLng * 180.0) / ((A / sqrtMagic) * Math.cos(radLat) * PI)
  return [lat + dLat, lng + dLng]
}

/**
 * 由「已经落到陆地上的折线」生成轨迹。
 * routes.js 里带 path 的路线走这条：不再凭空摆动，线的走向就是路径本身。
 */
// Chaikin 圆角：把折线拐角抹圆，看起来像人走出来的线而不是 CAD 折线
function chaikin(arr, iter = 2) {
  let a = arr
  for (let k = 0; k < iter; k++) {
    const out = [a[0]]
    for (let i = 0; i < a.length - 1; i++) {
      const p = a[i]
      const q = a[i + 1]
      out.push([p[0] * 0.75 + q[0] * 0.25, p[1] * 0.75 + q[1] * 0.25])
      out.push([p[0] * 0.25 + q[0] * 0.75, p[1] * 0.25 + q[1] * 0.75])
    }
    out.push(a[a.length - 1])
    a = out
  }
  return a
}

export function buildTrackFromPath(pathIn, pts, stepKm = 0.04) {
  const path = chaikin(pathIn, 2)
  const base = []
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i]
    const b = path[i + 1]
    const d = distKm(a, b)
    const n = Math.max(2, Math.min(240, Math.round(d / stepKm)))
    for (let j = 0; j < n; j++) {
      const t = j / n
      base.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t])
    }
  }
  base.push([path[path.length - 1][0], path[path.length - 1][1]])

  const cum = [0]
  for (let i = 1; i < base.length; i++) cum.push(cum[i - 1] + distKm(base[i - 1], base[i]))
  const total = cum[cum.length - 1] || 1
  const kmAt = (i) => cum[Math.min(i, cum.length - 1)] / total

  // 关键点映射到最近的轨迹样本，并保证里程单调递增
  const ptIndex = pts.map((p) => {
    let bi = 0
    let bd = Infinity
    for (let i = 0; i < base.length; i++) {
      const d = distKm([p.lat, p.lng], base[i])
      if (d < bd) {
        bd = d
        bi = i
      }
    }
    return bi
  })
  for (let i = 1; i < ptIndex.length; i++) if (ptIndex[i] < ptIndex[i - 1]) ptIndex[i] = ptIndex[i - 1]

  return { track: base, kmAt, ptIndex, ratio: 1 }
}

// ── 由显式关键点生成轨迹（Catmull-Rom 平滑 + 轻微摆动，贴合真实走线）──
function distKm(a, b) {
  const dy = (b[0] - a[0]) * 111.32
  const dx = (b[1] - a[1]) * 111.32 * Math.cos(((a[0] + b[0]) / 2 * PI) / 180)
  return Math.sqrt(dx * dx + dy * dy)
}

function catmullRom(p0, p1, p2, p3, t) {
  const t2 = t * t
  const t3 = t2 * t
  const f = (a, b, c, d) =>
    0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
  return [f(p0[0], p1[0], p2[0], p3[0]), f(p0[1], p1[1], p2[1], p3[1])]
}

/**
 * pts: [{ lat, lng, ele, km }] 按顺序排列的关键点
 * 返回 { track, cumKm, ptIndex, profile }
 */
export function buildTrackFromPts(pts, seed = 1, targetKm = 0, stepKm = 0.08) {
  const rnd = mulberry32(seed + 977)
  const ctrl = pts.map((p) => [p.lat, p.lng])

  // 1) 控制点之间做 Catmull-Rom 平滑，并记录每个点属于哪一段、段内进度
  const base = []
  const meta = []
  const ptIndex = []
  for (let i = 0; i < ctrl.length - 1; i++) {
    const p0 = ctrl[Math.max(0, i - 1)]
    const p1 = ctrl[i]
    const p2 = ctrl[i + 1]
    const p3 = ctrl[Math.min(ctrl.length - 1, i + 2)]
    const segKm = distKm(p1, p2)
    const n = Math.max(10, Math.min(600, Math.round(segKm / stepKm)))
    ptIndex.push(base.length)
    for (let j = 0; j < n; j++) {
      const t = j / n
      const [la, ln] = catmullRom(p0, p1, p2, p3, t)
      base.push([la, ln])
      meta.push({ seg: i, t })
    }
  }
  ptIndex.push(base.length)
  base.push(ctrl[ctrl.length - 1])
  meta.push({ seg: ctrl.length - 2, t: 1 })

  // 2) 自适应“盘山”摆动：让画出来的线长度接近标称里程（山径比直线长 15-80%）
  const baseKm = polylineKm(base)
  const wanted = targetKm > 0 ? Math.min(Math.max(targetKm / (baseKm || 1), 1), 2.8) : 1
  let amp = Math.max(0.01, (baseKm / Math.max(1, ctrl.length - 1)) * 0.25)
  let track = base
  let guard = 0
  while (wanted > 1.03 && guard < 10) {
    track = offsetTrack(base, meta, amp)
    const cur = polylineKm(track) / (baseKm || 1)
    if (Math.abs(cur - wanted) < 0.03) break
    // 长度增量与振幅平方成正比，用固定点迭代快速收敛
    const ratio = (wanted - 1) / Math.max(cur - 1, 1e-4)
    amp = Math.min(amp * Math.sqrt(Math.max(ratio, 0.05)), baseKm * 0.3)
    guard++
  }
  // 小尺度自然抖动（15~30 m），让线条不像 CAD
  const jitter = 0.00012 + rnd() * 0.0001
  track = track.map(([la, ln], i) => {
    const ph = i * 0.7 + seed
    return [la + Math.sin(ph) * jitter * 0.6, ln + Math.cos(ph * 1.3) * jitter * 0.6]
  })

  // 3) 弧长表：用于把关键点映射到 0-1 的里程比例
  const cum = [0]
  for (let i = 1; i < track.length; i++) cum.push(cum[i - 1] + distKm(track[i - 1], track[i]))
  const total = cum[cum.length - 1] || 1
  const kmAt = (idx) => cum[Math.min(idx, cum.length - 1)] / total

  return { track, kmAt, ptIndex, ratio: total / (baseKm || 1) }
}

function polylineKm(arr) {
  let d = 0
  for (let i = 1; i < arr.length; i++) d += distKm(arr[i - 1], arr[i])
  return d
}

// 沿每一段做多次正弦摆动（段两端归零，保证穿过关键点）
function offsetTrack(base, meta, ampKm) {
  const out = []
  for (let i = 0; i < base.length; i++) {
    const [la, ln] = base[i]
    const { seg, t } = meta[i] || { seg: 0, t: 0 }
    const prev = base[Math.max(0, i - 1)]
    const next = base[Math.min(base.length - 1, i + 1)]
    const dy = next[0] - prev[0]
    const dx = (next[1] - prev[1]) * Math.cos((la * PI) / 180)
    const len = Math.hypot(dx, dy) || 1
    // 每段内 2-5 个弯，模拟山径的连续转折
    const bends = 3 + (seg % 3)
    const env = Math.sin(PI * Math.min(1, Math.max(0, t)))
    const off = ampKm * env * Math.sin(bends * PI * t + seg)
    out.push([
      la + (-dx / len) * off / 111.32,
      ln + (dy / len) * off / (111.32 * Math.cos((la * PI) / 180))
    ])
  }
  return out
}

export function buildProfileFromPts(pts, trackInfo, seed = 1, samples = 72) {
  const rnd = mulberry32(seed * 13 + 7)
  const { kmAt, ptIndex } = trackInfo
  const anchors = pts.map((p, i) => ({ f: kmAt(ptIndex[i]), ele: p.ele }))
  if (anchors.length && anchors[anchors.length - 1].f < 1) anchors[anchors.length - 1].f = 1

  const profile = []
  for (let i = 0; i <= samples; i++) {
    const f = i / samples
    let a = anchors[0]
    let b = anchors[anchors.length - 1]
    for (let k = 1; k < anchors.length; k++) {
      if (anchors[k].f >= f) {
        a = anchors[k - 1]
        b = anchors[k]
        break
      }
    }
    const span = b.f - a.f || 1
    const t = Math.max(0, Math.min(1, (f - a.f) / span))
    const smooth = t * t * (3 - 2 * t)
    const base = a.ele + (b.ele - a.ele) * smooth
    profile.push(Math.max(0, Math.round(base + (rnd() - 0.5) * 6)))
  }
  return profile
}

// 由关键点生成：轨迹 + 各地里程 + 高程剖面
export function assembleRoute(pts, hintKm, seed, path) {
  // 关键点直线距离 → 按“山径曲折系数”放大成真实步程
  let straight = 0
  for (let i = 1; i < pts.length; i++) {
    straight += distKm([pts[i - 1].lat, pts[i - 1].lng], [pts[i].lat, pts[i].lng])
  }
  const factor = Math.min(1.42, Math.max(1.1, hintKm / (straight || 1)))
  const info = (path && path.length > 2)
    ? buildTrackFromPath(path, pts)
    : buildTrackFromPts(pts, seed, straight * factor)
  const distance = +(hintKm || polylineKm(info.track)).toFixed(1)
  const waypoints = pts.map((p, i) => ({
    ...p,
    km: +(info.kmAt(info.ptIndex[i]) * distance).toFixed(1)
  }))
  const track = info.track
  const profile = buildProfileFromPts(pts, info, seed)
  // 爬升由剖面累加得出（乘 1.12 补偿平滑损失）
  let gain = 0
  for (let i = 1; i < profile.length; i++) if (profile[i] > profile[i - 1]) gain += profile[i] - profile[i - 1]
  return {
    track,
    waypoints,
    profile,
    distance,
    climb: Math.round((gain * 1.12) / 10) * 10,
    realKm: +trackLengthKm(track).toFixed(1)
  }
}

// 生成一条“像轨迹”的线路：环线为带噪声的闭合环，穿越线为折返漫步
export function buildTrack(seed, center, distanceKm, loop = true, n = 88) {
  const rnd = mulberry32(seed)
  const [lat, lng] = center
  const kmPerLat = 111.32
  const kmPerLng = 111.32 * Math.cos((lat * PI) / 180)

  const pts = []
  if (loop) {
    const radius = distanceKm / (2 * PI) * 0.92
    const wobble = 1 + rnd() * 0.5
    let prevR = radius
    for (let i = 0; i <= n; i++) {
      const t = i / n
      const ang = t * PI * 2
      const r = radius * (0.62 + 0.38 * Math.sin(ang * (2 + wobble) + rnd() * 0.1)) + (rnd() - 0.5) * radius * 0.22
      const rr = (r + prevR) / 2
      prevR = r
      pts.push([Math.cos(ang) * rr, Math.sin(ang) * rr * 0.86])
    }
    // 收敛首尾，避免明显断口
    const [x0, y0] = pts[0]
    const [x1, y1] = pts[pts.length - 1]
    for (let i = 0; i < pts.length; i++) {
      const t = i / (pts.length - 1)
      pts[i][0] += (x0 - x1) * t
      pts[i][1] += (y0 - y1) * t
    }
  } else {
    // 折返：先向北侧绕行，再沿脊线南下
    let dir = -PI / 2 + (rnd() - 0.5) * 0.4
    let x = 0
    let y = 0
    const step = distanceKm / n / 2
    for (let i = 0; i <= n; i++) {
      const t = i / n
      dir += (rnd() - 0.5) * 0.55 + Math.sin(t * PI * 2.2) * 0.09
      x += Math.cos(dir) * step
      y += Math.sin(dir) * step
      pts.push([x, y])
    }
  }

  return pts.map(([x, y]) => [lat + y / kmPerLat, lng + x / kmPerLng])
}

export function buildProfile(seed, climb, n = 56) {
  const rnd = mulberry32(seed * 7 + 19)
  const base = 60 + Math.round(rnd() * 160)
  const peak = base + climb / 2.4
  const raw = []
  for (let i = 0; i <= n; i++) {
    const t = i / n
    const shape = Math.sin(PI * Math.pow(t, 0.82))
    const noise = (rnd() - 0.5) * climb * 0.1
    raw.push(Math.max(base * 0.85, base + (peak - base) * shape + noise))
  }
  let gain = 0
  for (let i = 1; i < raw.length; i++) if (raw[i] > raw[i - 1]) gain += raw[i] - raw[i - 1]
  const k = gain > 0 ? Math.min(climb / gain, 2.2) : 1
  return raw.map((v) => Math.round(base + (v - base) * k))
}

export function trackLengthKm(track) {
  let d = 0
  for (let i = 1; i < track.length; i++) {
    const [la1, ln1] = track[i - 1]
    const [la2, ln2] = track[i]
    const dy = (la2 - la1) * 111.32
    const dx = (ln2 - ln1) * 111.32 * Math.cos((la1 * PI) / 180)
    d += Math.sqrt(dx * dx + dy * dy)
  }
  return d
}

export function buildGpx(route) {
  const date = new Date().toISOString()
  const pts = route.track
    .map(([lat, lng], i) => {
      const ele = route.profile[Math.min(route.profile.length - 1, Math.round((i / (route.track.length - 1)) * (route.profile.length - 1)))]
      return `      <trkpt lat="${lat.toFixed(6)}" lon="${lng.toFixed(6)}"><ele>${ele}</ele></trkpt>`
    })
    .join('\n')
  const wpts = route.waypoints
    .map((w) => `  <wpt lat="${w.lat.toFixed(6)}" lon="${w.lng.toFixed(6)}"><name>${w.name}</name></wpt>`)
    .join('\n')
  return `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="野径 · 华南徒步图鉴" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata><name>${route.name}</name><time>${date}</time></metadata>
${wpts}
  <trk>
    <name>${route.name}</name>
    <trkseg>
${pts}
    </trkseg>
  </trk>
</gpx>
`
}

export function downloadText(filename, text) {
  const blob = new Blob([text], { type: 'application/gpx+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
