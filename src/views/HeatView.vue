<script setup>
import { computed, ref } from 'vue'
import { cityStats, overview } from '../data/cities.js'

const hovered = ref(null)

const top15 = computed(() => cityStats.slice(0, 15))
const maxIndex = computed(() => Math.max(...cityStats.map((c) => c.index)))

const avgIndex = computed(() =>
  Math.round(cityStats.reduce((a, c) => a + c.index, 0) / cityStats.length)
)

const metrics = computed(() => [
  { label: '覆盖城市', value: overview.cityCount, unit: '座', sub: `广东 / 湖南 / 江西 / 广西`, icon: '城' },
  { label: '收录景点', value: overview.spotCount, unit: '个', sub: `平均热度 ${Math.round(cityStats.reduce((a, c) => a + c.spotAvg * c.spotCount, 0) / overview.spotCount)}`, icon: '点' },
  { label: '徒步路线', value: overview.routeCount, unit: '条', sub: `共 ${overview.totalKm} 公里轨迹`, icon: '线' },
  { label: '最热城市', value: cityStats[0].name, unit: '', sub: `综合热度 ${cityStats[0].index} / 100`, icon: '热' }
])

// ── 散点图 ──
const W = 660
const H = 400
const PAD = { l: 54, r: 28, t: 26, b: 48 }

const xMax = computed(() => Math.max(...cityStats.map((c) => c.spotCount)) + 2)
const yMax = computed(() => Math.max(...cityStats.map((c) => c.routeCount)) + 1.5)
const xMid = computed(() => cityStats.reduce((a, c) => a + c.spotCount, 0) / cityStats.length)
const yMid = computed(() => cityStats.reduce((a, c) => a + c.routeCount, 0) / cityStats.length)

const px = (v) => PAD.l + ((W - PAD.l - PAD.r) * v) / xMax.value
const py = (v) => H - PAD.b - ((H - PAD.t - PAD.b) * v) / yMax.value
const pr = (v) => 6 + (v / 100) * 8

const FS = 11 // 标签字号
const dots = computed(() => {
  const base = cityStats.map((c) => ({
    ...c,
    cx: px(c.spotCount),
    cy: py(c.routeCount),
    r: pr(c.index)
  }))

  // 象限说明文字也是「障碍物」，先占位，城市名会自己绕开
  const placed = [
    { x1: PAD.l + 4, y1: PAD.t + 4, x2: PAD.l + 52, y2: PAD.t + 22 },
    { x1: W - PAD.r - 152, y1: PAD.t + 4, x2: W - PAD.r, y2: PAD.t + 22 },
    { x1: W - PAD.r - 50, y1: H - PAD.b - 46, x2: W - PAD.r, y2: H - PAD.b - 24 }
  ]
  const hitBox = (a, b) => !(a.x2 < b.x1 || a.x1 > b.x2 || a.y2 < b.y1 || a.y1 > b.y2)

  return base.map((d) => {
    const w = d.name.length * FS * 1.05
    const h = FS * 1.1
    const xa = PAD.l + 2
    const xb = W - PAD.r - 2 - w

    const cands = [
      { x: d.cx + d.r + 6, y: d.cy - h / 2 },
      { x: d.cx - d.r - 6 - w, y: d.cy - h / 2 },
      { x: d.cx - w / 2, y: d.cy - d.r - 8 - h },
      { x: d.cx - w / 2, y: d.cy + d.r + 8 }
    ].map((c) => ({ ...c, x: Math.min(Math.max(c.x, xa), xb) }))

    let pick = null
    for (const c of cands) {
      const box = { x1: c.x - 3, y1: c.y - 2, x2: c.x + w + 3, y2: c.y + h + 2 }
      const clashLabel = placed.some((p) => hitBox(box, p))
      const clashDot = base.some(
        (o) =>
          o !== d &&
          !(
            box.x2 < o.cx - o.r ||
            box.x1 > o.cx + o.r ||
            box.y2 < o.cy - o.r ||
            box.y1 > o.cy + o.r
          )
      )
      if (!clashLabel && !clashDot) {
        pick = c
        break
      }
    }
    if (!pick) pick = cands[3]

    placed.push({ x1: pick.x - 3, y1: pick.y - 2, x2: pick.x + w + 3, y2: pick.y + h + 2 })
    return { ...d, labelX: pick.x, labelY: pick.y + FS * 0.94 }
  })
})

const xTicks = computed(() => {
  const step = Math.ceil(xMax.value / 5)
  const arr = []
  for (let v = 0; v <= xMax.value; v += step) arr.push(v)
  return arr
})

const yTicks = computed(() => {
  const step = Math.ceil(yMax.value / 4)
  const arr = []
  for (let v = 0; v <= yMax.value; v += step) arr.push(v)
  return arr
})
</script>

<template>
  <div class="page">
    <div class="container">
      <header class="head">
        <div>
          <p class="eyebrow">CITIES</p>
          <h1>哪座城值得排进这个周末</h1>
          <p class="lead">
            把景点和路线按城市汇总。综合热度 = 景点热度 40% + 路线热度 30% + 点位规模 30%，
            分数高不代表适合你，点城市名可以直接跳到那张城市的路书。
          </p>
        </div>
        <div class="head-nums">
          <div><b>{{ cityStats.length }}</b><span>城市</span></div>
          <div><b>{{ overview.spotCount }}</b><span>点位</span></div>
          <div><b>{{ overview.routeCount }}</b><span>路线</span></div>
        </div>
      </header>

      <!-- 指标卡 -->
      <div class="metric-grid">
        <div v-for="m in metrics" :key="m.label" class="metric-card card">
          <div class="mc-icon">{{ m.icon }}</div>
          <div class="mc-label">{{ m.label }}</div>
          <div class="mc-value">
            <b>{{ m.value }}</b><em v-if="m.unit">{{ m.unit }}</em>
          </div>
          <div class="mc-sub">{{ m.sub }}</div>
        </div>
      </div>

      <div class="heat-layout">
        <!-- 排行 -->
        <div class="rank-card card">
          <div class="rc-head">
            <h3>综合热度 Top {{ top15.length }}</h3>
            <span class="rc-note">平均 {{ avgIndex }}</span>
          </div>
          <div class="rank-list">
            <div
              v-for="(c, i) in top15"
              :key="c.name"
              class="rank-row"
              @mouseenter="hovered = c.name"
              @mouseleave="hovered = null"
            >
              <span class="rk-no mono" :class="{ gold: i === 0, silver: i === 1, bronze: i === 2 }">
                {{ String(i + 1).padStart(2, '0') }}
              </span>
              <span class="rk-name">{{ c.name }}</span>
              <div class="rk-bar">
                <i :style="{ width: (c.index / maxIndex) * 100 + '%' }"></i>
              </div>
              <span class="rk-count">{{ c.spotCount }}景点 / {{ c.routeCount }}路线</span>
              <span class="rk-val mono">{{ c.index }}</span>
            </div>
          </div>
          <div class="rc-foot">
            指数越高，说明这个城市既有得玩、也有得走；单看景点多但路线少的城市，适合观光型行程。
          </div>
        </div>

        <!-- 玩法对比 -->
        <div class="scatter-card card">
          <div class="rc-head">
            <h3>玩法对比：观光 vs 徒步</h3>
            <span class="rc-note">气泡大小 = 综合热度</span>
          </div>
          <div class="scatter-wrap">
            <svg :viewBox="`0 0 ${W} ${H}`" class="scatter">
              <!-- 象限底色 -->
              <rect
                :x="PAD.l"
                :y="PAD.t"
                :width="W - PAD.l - PAD.r"
                :height="H - PAD.t - PAD.b"
                fill="#fbfaf6"
                rx="6"
              />
              <rect
                :x="px(xMid)"
                :y="PAD.t"
                :width="W - PAD.r - px(xMid)"
                :height="py(yMid) - PAD.t"
                fill="rgba(45,90,61,0.05)"
              />

              <!-- 网格 -->
              <g v-for="t in xTicks" :key="'x' + t">
                <line
                  :x1="px(t)"
                  :x2="px(t)"
                  :y1="PAD.t"
                  :y2="H - PAD.b"
                  stroke="#ece7dc"
                  stroke-width="1"
                />
                <text :x="px(t)" :y="H - PAD.b + 16" text-anchor="middle" font-size="10" fill="#9ca3af">
                  {{ t }}
                </text>
              </g>
              <g v-for="t in yTicks" :key="'y' + t">
                <line
                  :x1="PAD.l"
                  :x2="W - PAD.r"
                  :y1="py(t)"
                  :y2="py(t)"
                  stroke="#ece7dc"
                  stroke-width="1"
                />
                <text :x="PAD.l - 10" :y="py(t) + 3.5" text-anchor="end" font-size="10" fill="#9ca3af">
                  {{ t }}
                </text>
              </g>

              <!-- 均值线 -->
              <line
                :x1="px(xMid)"
                :x2="px(xMid)"
                :y1="PAD.t"
                :y2="H - PAD.b"
                stroke="#d8cfbc"
                stroke-dasharray="4 4"
              />
              <line
                :x1="PAD.l"
                :x2="W - PAD.r"
                :y1="py(yMid)"
                :y2="py(yMid)"
                stroke="#d8cfbc"
                stroke-dasharray="4 4"
              />

              <!-- 象限说明 -->
              <text :x="W - PAD.r - 10" :y="PAD.t + 16" text-anchor="end" font-size="10" fill="#a99e88">
                全能城市：景点多 · 路线多
              </text>
              <text :x="PAD.l + 10" :y="PAD.t + 16" font-size="10" fill="#a99e88">徒步为主</text>
              <text :x="W - PAD.r - 10" :y="H - PAD.b - 34" text-anchor="end" font-size="10" fill="#a99e88">
                观光为主
              </text>

              <!-- 气泡 -->
              <g
                v-for="d in dots"
                :key="d.name"
                class="dot-g"
                :class="{ dim: hovered && hovered !== d.name }"
                @mouseenter="hovered = d.name"
                @mouseleave="hovered = null"
              >
                <circle :cx="d.cx" :cy="d.cy" :r="d.r" fill="rgba(45,90,61,0.13)" />
                <circle :cx="d.cx" :cy="d.cy" :r="d.r * 0.56" fill="#2d5a3d" opacity="0.88" />
                <text
                  :x="d.labelX"
                  :y="d.labelY"
                  font-size="11"
                  font-weight="600"
                  fill="#1e3d29"
                  stroke="#fbfaf6"
                  stroke-width="3"
                  paint-order="stroke"
                  stroke-linejoin="round"
                >
                  {{ d.name }}
                </text>
              </g>

              <text :x="(W + PAD.l) / 2" :y="H - 8" text-anchor="middle" font-size="11" fill="#6b7280">
                景点数量（个）
              </text>
              <text
                :x="14"
                :y="(H - PAD.b + PAD.t) / 2"
                text-anchor="middle"
                font-size="11"
                fill="#6b7280"
                :transform="`rotate(-90 14 ${(H - PAD.b + PAD.t) / 2})`"
              >
                徒步路线（条）
              </text>
            </svg>
          </div>
          <div v-if="hovered" class="sc-hover">
            <template v-for="c in cityStats.filter((x) => x.name === hovered)" :key="c.name">
              <b>{{ c.name }}</b>
              <span>{{ c.province }} · {{ c.spotCount }} 景点 · {{ c.routeCount }} 路线 · 综合 {{ c.index }}</span>
              <span class="muted">{{ c.tagline }}</span>
            </template>
          </div>
          <div v-else class="sc-hover placeholder">
            把指针放到气泡上（手机上点一下）看城市详情 · 右上角是既能观光又能徒步的城市，贴着横轴说明可走的路线偏少。
          </div>
          <span class="scatter-hint">左右滑动可查看完整图表</span>
        </div>
      </div>

      <!-- 明细表 -->
      <div class="table-card card">
        <div class="rc-head">
          <h3>城市明细</h3>
          <span class="rc-note">按综合热度排序</span>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>城市</th>
                <th>省份</th>
                <th>景点</th>
                <th>路线</th>
                <th>路线总里程</th>
                <th>景点均热度</th>
                <th>路线均热度</th>
                <th>综合指数</th>
                <th>代表景点</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(c, i) in cityStats" :key="c.name">
                <td class="mono idx">{{ i + 1 }}</td>
                <td class="city-cell">
                  <router-link :to="{ path: '/spots', query: { city: c.name } }">{{ c.name }}</router-link>
                </td>
                <td class="muted">{{ c.province }}</td>
                <td class="mono">{{ c.spotCount }}</td>
                <td class="mono">{{ c.routeCount }}</td>
                <td class="mono">{{ c.totalKm }} km</td>
                <td class="mono">{{ c.spotAvg }}</td>
                <td class="mono">{{ c.routeAvg }}</td>
                <td>
                  <span class="idx-pill mono">{{ c.index }}</span>
                </td>
                <td class="muted small">{{ c.topSpot ? c.topSpot.name : '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 26px;
  padding-bottom: 20px;
}

.eyebrow {
  font-size: 0.66rem;
  letter-spacing: 0.22em;
  color: var(--earth);
  margin-bottom: 5px;
}

.head h1 {
  font-size: 1.66rem;
  font-weight: 800;
  color: var(--forest-dark);
  letter-spacing: -0.01em;
}

.lead {
  margin-top: 8px;
  font-size: 0.85rem;
  color: var(--ink-soft);
  max-width: 640px;
}

.head-nums {
  display: flex;
  gap: 26px;
  flex-shrink: 0;
}

.head-nums div {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.head-nums b {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 1.45rem;
  color: var(--forest);
  line-height: 1.1;
}

.head-nums span {
  font-size: 0.68rem;
  color: var(--gray-light);
}

.head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 26px;
  padding-bottom: 20px;
}

.eyebrow {
  font-size: 0.66rem;
  letter-spacing: 0.22em;
  color: var(--earth);
  margin-bottom: 5px;
}

.head h1 {
  font-size: 1.66rem;
  font-weight: 800;
  color: var(--forest-dark);
  letter-spacing: -0.01em;
}

.lead {
  margin-top: 8px;
  font-size: 0.85rem;
  color: var(--ink-soft);
  max-width: 640px;
}

.head-nums {
  display: flex;
  gap: 26px;
  flex-shrink: 0;
}

.head-nums div {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.head-nums b {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 1.45rem;
  color: var(--forest);
  line-height: 1.1;
}

.head-nums span {
  font-size: 0.68rem;
  color: var(--gray-light);
}

.head-note {
  font-size: 0.8rem;
  color: var(--gray);
}

.head-note .mono {
  color: var(--forest);
  font-weight: 700;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 18px;
}

.metric-card {
  padding: 16px 18px;
  position: relative;
  overflow: hidden;
}

.mc-icon {
  position: absolute;
  right: 14px;
  top: 8px;
  font-family: var(--serif);
  font-size: 1.9rem;
  line-height: 1;
  color: var(--forest);
  opacity: 0.13;
  user-select: none;
}

.mc-label {
  font-size: 0.76rem;
  color: var(--gray);
  letter-spacing: 0.06em;
}

.mc-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin: 4px 0 2px;
}

.mc-value b {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--forest-dark);
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.mc-value em {
  font-style: normal;
  font-size: 0.78rem;
  color: var(--gray);
}

.mc-sub {
  font-size: 0.72rem;
  color: var(--gray-light);
}

.heat-layout {
  display: grid;
  grid-template-columns: 1.02fr 1fr;
  gap: 18px;
  margin-bottom: 18px;
}

.rank-card,
.scatter-card,
.table-card {
  padding: 18px 20px;
}

.rank-card {
  display: flex;
  flex-direction: column;
}

.rc-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 14px;
}

.rc-head h3 {
  font-size: 1.02rem;
  font-weight: 700;
  color: var(--forest-dark);
}

.rc-note {
  font-size: 0.72rem;
  color: var(--gray-light);
}

.rank-list {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 2px;
  flex: 1;
  padding-bottom: 10px;
}

.rank-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 4px;
  border-radius: 7px;
  transition: background 0.15s;
}

.rank-row:hover {
  background: var(--forest-soft);
}

.rk-no {
  width: 22px;
  font-size: 0.72rem;
  color: var(--gray-light);
  font-weight: 700;
}

.rk-no.gold {
  color: #c9a227;
}

.rk-no.silver {
  color: #8d99a6;
}

.rk-no.bronze {
  color: #b07d4a;
}

.rk-name {
  width: 58px;
  font-size: 0.84rem;
  font-weight: 600;
  color: var(--ink);
}

.rk-bar {
  flex: 1;
  height: 7px;
  background: var(--cream);
  border-radius: 6px;
  overflow: hidden;
}

.rk-bar i {
  display: block;
  height: 100%;
  border-radius: 6px;
  background: linear-gradient(90deg, var(--forest-light), var(--forest));
  transition: width 0.5s ease;
}

.rk-count {
  width: 104px;
  font-size: 0.68rem;
  color: var(--gray-light);
  text-align: right;
}

.rk-val {
  width: 30px;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--forest);
  text-align: right;
}

.rc-foot {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px dashed var(--line);
  font-size: 0.72rem;
  color: var(--gray);
  line-height: 1.7;
}

/* 散点 */
.scatter-wrap {
  width: 100%;
}

.scatter {
  width: 100%;
  height: auto;
  display: block;
}

.dot-g {
  cursor: pointer;
  transition: opacity 0.15s;
}

.dot-g.dim {
  opacity: 0.28;
}

.sc-hover {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 6px;
  padding: 8px 12px;
  background: var(--forest-soft);
  border-radius: 8px;
  font-size: 0.75rem;
  min-height: 36px;
}

.sc-hover b {
  color: var(--forest-dark);
  font-size: 0.84rem;
}

.sc-hover span {
  color: var(--ink-soft);
}

.sc-hover.placeholder {
  background: var(--cream);
  color: var(--gray);
  font-size: 0.72rem;
  align-items: center;
  line-height: 1.6;
}

/* 表格 */
.table-scroll {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}

th {
  text-align: left;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--gray-light);
  padding: 8px 10px;
  border-bottom: 1px solid var(--line);
  white-space: nowrap;
}

td {
  padding: 9px 10px;
  border-bottom: 1px solid #f4f1e9;
  color: var(--ink-soft);
}

tbody tr:hover {
  background: #fcfbf7;
}

.idx {
  color: var(--gray-light);
  width: 30px;
}

.city-cell a {
  font-weight: 600;
  color: var(--forest-dark);
}

.city-cell a:hover {
  color: var(--forest-light);
  text-decoration: underline;
}

.idx-pill {
  display: inline-block;
  padding: 1px 9px;
  border-radius: 6px;
  background: var(--forest-soft);
  color: var(--forest);
  font-weight: 700;
  font-size: 0.78rem;
}

.small {
  font-size: 0.78rem;
}

@media (max-width: 1080px) {
  .metric-grid {
    grid-template-columns: 1fr 1fr;
  }

  .heat-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 640px) {
  .metric-grid {
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .mc-value b {
    font-size: 1.4rem;
  }

  .rk-count {
    display: none;
  }

  /* 明细表：列多，小屏给横向滚动，别把城市名压成竖排 */
  .table-scroll table {
    min-width: 660px;
  }

  .table-scroll th,
  .table-scroll td {
    white-space: nowrap;
  }

  /* 散点图：等比例缩到 330 宽时字只有 5px，改成可横向滑动 */
  .scatter-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .scatter {
    min-width: 470px;
  }

  .scatter-hint {
    display: block;
  }
}

.scatter-hint {
  display: none;
  margin-top: 6px;
  font-size: 0.68rem;
  color: var(--gray-light);
  letter-spacing: 0.02em;
}
</style>
