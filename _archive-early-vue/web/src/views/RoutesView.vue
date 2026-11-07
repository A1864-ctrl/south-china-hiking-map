<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { routes, terrains, provinces } from '../data/routes.js'
import HikeMap from '../components/HikeMap.vue'
import ElevationChart from '../components/ElevationChart.vue'
import { buildGpx, downloadText } from '../data/geo.js'

const route = useRoute()
const router = useRouter()

const levelColor = { easy: '#27ae60', mid: '#2980b9', hard: '#c0392b' }
const levelBg = { easy: 'badge-easy', mid: 'badge-mid', hard: 'badge-hard' }

const levelFilter = ref('all')
const terrainFilter = ref('')
const provinceFilter = ref('')
const sortBy = ref('heat')
const keyword = ref('')
const selectedId = ref(routes.slice().sort((a, b) => b.heat - a.heat)[0].id)

const list = computed(() => {
  let l = routes.filter((r) => {
    if (levelFilter.value !== 'all' && r.level !== levelFilter.value) return false
    if (terrainFilter.value && r.terrain !== terrainFilter.value) return false
    if (provinceFilter.value && r.province !== provinceFilter.value) return false
    if (keyword.value.trim()) {
      const kw = keyword.value.trim()
      if (!(r.name.includes(kw) || r.city.includes(kw) || r.terrain.includes(kw) || r.province.includes(kw))) return false
    }
    return true
  })
  if (sortBy.value === 'heat') l = l.sort((a, b) => b.heat - a.heat)
  else if (sortBy.value === 'distance') l = l.sort((a, b) => b.distance - a.distance)
  else l = l.sort((a, b) => b.climb - a.climb)
  return l
})

const current = computed(() => routes.find((r) => r.id === selectedId.value) || list.value[0] || routes[0])

// 每段行程：距上一点的距离
const legs = computed(() =>
  current.value.waypoints.map((w, i) => ({
    ...w,
    gap: i === 0 ? 0 : +(w.km - current.value.waypoints[i - 1].km).toFixed(1),
    sup: w.sup || '',
    photo: w.photo || ''
  }))
)

const supplyPoints = computed(() => legs.value.filter((w) => w.sup))
const photoPoints = computed(() => legs.value.filter((w) => w.photo))

const counts = computed(() => ({
  all: routes.length,
  easy: routes.filter((r) => r.level === 'easy').length,
  mid: routes.filter((r) => r.level === 'mid').length,
  hard: routes.filter((r) => r.level === 'hard').length
}))

function pick(r) {
  selectedId.value = r.id
  router.replace({ query: { id: r.id } })
}

function exportGpx() {
  const r = current.value
  downloadText(`${r.name.replace(/[·/\\s]/g, '_')}.gpx`, buildGpx(r))
}

watch(
  () => route.query.id,
  (v) => {
    if (v && routes.some((r) => r.id === Number(v))) selectedId.value = Number(v)
  }
)

onMounted(() => {
  const id = Number(route.query.id)
  if (id && routes.some((r) => r.id === id)) selectedId.value = id
})
</script>

<template>
  <div class="page">
    <div class="container">
      <div class="page-head">
        <div>
          <h1 class="page-title"><span>🥾</span>徒步轨迹</h1>
          <p class="page-desc">
            共 {{ routes.length }} 条路线：湖南、广东全覆盖 + 全国热门，按热度排序。左侧选路线，右侧看轨迹、分段路书、补给点、交通接驳与装备清单，可直接导出 GPX。
          </p>
        </div>
        <div class="head-stats">
          <div class="hs"><b class="mono">{{ counts.hard }}</b><em>难线</em></div>
          <div class="hs"><b class="mono">{{ counts.mid }}</b><em>进阶</em></div>
          <div class="hs"><b class="mono">{{ counts.easy }}</b><em>入门</em></div>
        </div>
      </div>

      <!-- 筛选条 -->
      <div class="filters card">
        <div class="f-left">
          <button class="chip" :class="{ active: levelFilter === 'all' }" @click="levelFilter = 'all'">
            全部 <em class="mono">{{ counts.all }}</em>
          </button>
          <button class="chip" :class="{ active: levelFilter === 'easy' }" @click="levelFilter = 'easy'">
            入门休闲 <em class="mono">{{ counts.easy }}</em>
          </button>
          <button class="chip" :class="{ active: levelFilter === 'mid' }" @click="levelFilter = 'mid'">
            进阶挑战 <em class="mono">{{ counts.mid }}</em>
          </button>
          <button class="chip" :class="{ active: levelFilter === 'hard' }" @click="levelFilter = 'hard'">
            顶级毕业 <em class="mono">{{ counts.hard }}</em>
          </button>
        </div>
        <div class="f-right">
          <div class="search-mini">
            <span>⌕</span>
            <input v-model="keyword" placeholder="搜索路线 / 城市" />
          </div>
          <select v-model="provinceFilter" class="select">
            <option value="">全部省份</option>
            <option v-for="p in provinces" :key="p" :value="p">{{ p }}</option>
          </select>
          <select v-model="terrainFilter" class="select">
            <option value="">全部地形</option>
            <option v-for="t in terrains" :key="t" :value="t">{{ t }}</option>
          </select>
          <select v-model="sortBy" class="select">
            <option value="heat">按热度</option>
            <option value="distance">按里程</option>
            <option value="climb">按爬升</option>
          </select>
        </div>
      </div>

      <div class="split">
        <!-- 路线列表 -->
        <div class="list-col card">
          <div class="list-head">
            <span>路线列表</span>
            <span class="mono">{{ list.length }} 条</span>
          </div>
          <div class="list-body scroll-area">
            <button
              v-for="r in list"
              :key="r.id"
              class="route-item"
              :class="{ active: r.id === selectedId }"
              @click="pick(r)"
            >
              <div class="ri-top">
                <span class="ri-name">{{ r.name }}</span>
                <span class="badge" :class="levelBg[r.level]">{{ r.levelText }}</span>
              </div>
              <div class="ri-meta">
                {{ r.city }} · {{ r.terrain }} · {{ r.days }}
              </div>
              <div class="ri-bottom">
                <span class="mono">{{ r.distance }}km</span>
                <span class="ri-sep"></span>
                <span class="mono">↑{{ r.climb }}m</span>
                <span class="ri-heat mono">🔥{{ r.heat }}</span>
              </div>
            </button>

            <div v-if="!list.length" class="list-empty">
              没有匹配的路线，试试放宽筛选条件。
            </div>
          </div>
        </div>

        <!-- 详情 -->
        <div class="detail-col">
          <div class="detail card">
            <div class="d-head">
              <div class="d-title-row">
                <h2>{{ current.name }}</h2>
                <div class="d-actions">
                  <button class="btn btn-ghost d-btn" @click="exportGpx">⬇ 导出 GPX</button>
                </div>
              </div>
              <div class="d-meta">
                <span>{{ current.province }} · {{ current.city }}</span>
                <span class="sep">|</span>
                <span>{{ current.terrain }}</span>
                <span class="sep">|</span>
                <span>{{ current.days }}</span>
                <span class="sep">|</span>
                <span>最佳季节 {{ current.season }}</span>
              </div>
              <div class="d-badges">
                <span class="badge" :class="levelBg[current.level]">难度 {{ current.levelText }}</span>
                <span class="badge badge-ghost">{{ current.loop ? '环线' : '穿越线' }}</span>
                <span class="badge badge-ghost">途经 {{ current.waypoints.length }} 个节点</span>
                <span class="heat-wrap">
                  <span class="heat-label">热度</span>
                  <span class="heat-track"
                    ><i :style="{ width: current.heat + '%', background: levelColor[current.level] }"></i
                  ></span>
                  <b class="mono">{{ current.heat }}/100</b>
                </span>
              </div>
            </div>

            <p class="d-desc">{{ current.desc }}</p>

            <div class="d-grid">
              <div class="d-map">
                <HikeMap
                  :track="current.track"
                  :waypoints="current.waypoints"
                  :center="current.center"
                  :color="levelColor[current.level]"
                  height="400px"
                  :label="current.loop ? '环线轨迹' : '穿越轨迹'"
                />
              </div>
              <div class="d-side">
                <div class="stat-grid">
                  <div class="stat">
                    <em>里程</em>
                    <b class="mono">{{ current.distance }}<i>km</i></b>
                  </div>
                  <div class="stat">
                    <em>累计爬升</em>
                    <b class="mono">{{ current.climb }}<i>m</i></b>
                  </div>
                  <div class="stat">
                    <em>最高海拔</em>
                    <b class="mono">{{ current.maxEle }}<i>m</i></b>
                  </div>
                  <div class="stat">
                    <em>建议时长</em>
                    <b class="mono small">{{ current.hours }}</b>
                  </div>
                </div>
                <div class="wp-box">
                  <div class="wp-title">途经点与间距</div>
                  <ul class="wp-list">
                    <li v-for="(w, i) in legs" :key="w.name">
                      <span class="wp-idx" :class="{ s: i === 0, e: i === legs.length - 1 }">
                        {{ i + 1 }}
                      </span>
                      <span class="wp-name">{{ w.name }}</span>
                      <span class="wp-km mono">{{ w.km }}km</span>
                      <span v-if="i" class="wp-gap mono">+{{ w.gap }}</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            <ElevationChart
              :profile="current.profile"
              :distance="current.distance"
              :color="levelColor[current.level]"
            />

            <!-- 路书 -->
            <div class="rb">
              <section class="rb-block">
                <h3 class="rb-title"><span>🧭</span>分段路书<span class="rb-sub">共 {{ legs.length }} 个节点 · 累计 {{ current.distance }} km · 爬升 {{ current.climb }} m</span></h3>
                <div class="rb-table-wrap">
                  <table class="rb-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>地点</th>
                        <th>累计里程</th>
                        <th>海拔</th>
                        <th>路况与说明</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(w, i) in legs" :key="w.name">
                        <td class="mono idx">{{ i + 1 }}</td>
                        <td class="place">
                          <b>{{ w.name }}</b>
                          <span v-if="i === 0" class="tag tag-start">起点</span>
                          <span v-if="i === legs.length - 1" class="tag tag-end">终点</span>
                          <span v-if="w.sup" class="tag tag-sup">可补给</span>
                          <span v-if="w.camp" class="tag tag-camp">营地</span>
                          <span v-if="w.photo" class="tag tag-photo">机位</span>
                        </td>
                        <td class="mono nowrap">
                          {{ w.km }} km
                          <em v-if="i" class="gap">+{{ w.gap }}</em>
                        </td>
                        <td class="mono nowrap">{{ w.ele }} m</td>
                        <td class="note">{{ w.note }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>

              <div class="rb-cols">
                <section class="rb-block">
                  <h3 class="rb-title"><span>🚄</span>怎么到起点</h3>
                  <ul class="acc-list">
                    <li><b>高铁</b><span>{{ current.access.hsr }}</span></li>
                    <li><b>火车站</b><span>{{ current.access.rail }}</span></li>
                    <li><b>公交 / 班车</b><span>{{ current.access.bus }}</span></li>
                    <li><b>自驾</b><span>{{ current.access.car }}</span></li>
                  </ul>
                </section>

                <section class="rb-block">
                  <h3 class="rb-title"><span>🥤</span>补给与撤离</h3>
                  <ul class="sup-list">
                    <li v-for="w in supplyPoints" :key="w.name">
                      <b class="mono">{{ w.km }}km</b>
                      <div>
                        <strong>{{ w.name }}</strong>
                        <p>{{ w.sup }}</p>
                      </div>
                    </li>
                    <li v-if="!supplyPoints.length" class="muted">全程无补给，需自带水与食物。</li>
                  </ul>
                  <div class="sup-note">撤离原则：任一节点沿原路或机耕道下撤，天黑前 1 小时未到下一节点即应折返。</div>
                </section>
              </div>

              <div class="rb-cols">
                <section class="rb-block">
                  <h3 class="rb-title"><span>🎒</span>装备清单</h3>
                  <div class="chips-wrap">
                    <span v-for="g in current.gear" :key="g" class="gear-chip">{{ g }}</span>
                  </div>
                  <div class="gear-extra">另备：{{ current.loop ? '无' : '接驳车辆联系方式' }}、身份证、现金 200 元、离线地图。</div>
                </section>

                <section class="rb-block">
                  <h3 class="rb-title"><span>📷</span>出片机位</h3>
                  <ul class="photo-list">
                    <li v-for="w in photoPoints" :key="w.name">
                      <b class="mono">{{ w.km }}km</b>
                      <div><strong>{{ w.name }}</strong><p>{{ w.photo }}</p></div>
                    </li>
                    <li v-if="!photoPoints.length" class="muted">沿途以自然景观为主，无固定机位。</li>
                  </ul>
                </section>
              </div>

              <section class="rb-block">
                <h3 class="rb-title"><span>⚠️</span>风险提示</h3>
                <div class="chips-wrap">
                  <span v-for="k in current.risk" :key="k" class="risk-chip">{{ k }}</span>
                </div>
              </section>
            </div>

            <div class="d-tip">
              <span class="tip-label">安全提示</span>
              <p>{{ current.tips }}</p>
            </div>

            <div class="d-foot">
              <span class="muted">轨迹为示例生成，用于演示交互；接入真实数据后可直接替换为 GPX 轨迹。</span>
              <router-link
                :to="{ path: '/spots', query: { city: current.city } }"
                class="link-more"
              >
                看 {{ current.city }} 的景点 →
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.head-stats {
  display: flex;
  gap: 26px;
}

.hs {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.hs b {
  font-size: 1.4rem;
  color: var(--forest);
  line-height: 1.2;
}

.hs em {
  font-style: normal;
  font-size: 0.72rem;
  color: var(--gray-light);
}

/* 筛选 */
.filters {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 16px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.f-left {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.f-left .chip em {
  font-style: normal;
  opacity: 0.68;
  font-size: 0.76rem;
}

.f-right {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.search-mini {
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 0 10px;
  background: var(--cream);
}

.search-mini span {
  color: var(--gray);
}

.search-mini input {
  border: none;
  outline: none;
  background: transparent;
  padding: 7px 0;
  font-size: 0.82rem;
  width: 130px;
}

.select {
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 7px 10px;
  font-size: 0.8rem;
  color: var(--ink-soft);
  background: #fff;
  outline: none;
  cursor: pointer;
}

/* 分栏 */
.split {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  min-width: 0;
  gap: 18px;
  align-items: start;
}

.list-col {
  position: sticky;
  top: calc(var(--nav-h) + 20px);
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - var(--nav-h) - 40px);
  overflow: hidden;
}

.list-head {
  display: flex;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--forest-dark);
  background: #fff;
  border-radius: var(--radius) var(--radius) 0 0;
}

.list-head .mono {
  color: var(--gray);
  font-weight: 400;
}

.list-body {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.route-item {
  text-align: left;
  padding: 11px 12px;
  border-radius: 9px;
  border: 1px solid transparent;
  transition: all 0.16s;
  width: 100%;
}

.route-item:hover {
  background: var(--cream);
}

.route-item.active {
  background: var(--forest-soft);
  border-color: rgba(45, 90, 61, 0.28);
}

.ri-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.ri-name {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.route-item.active .ri-name {
  color: var(--forest-dark);
}

.ri-meta {
  font-size: 0.72rem;
  color: var(--gray-light);
  margin: 3px 0 5px;
}

.ri-bottom {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 0.72rem;
  color: var(--gray);
}

.ri-sep {
  width: 1px;
  height: 9px;
  background: var(--line);
}

.ri-heat {
  margin-left: auto;
  color: var(--earth);
  font-size: 0.7rem;
}

.list-empty {
  padding: 30px 12px;
  text-align: center;
  font-size: 0.82rem;
  color: var(--gray);
}

/* 详情 */
.detail {
  padding: 24px 26px 20px;
  min-width: 0;
}

.d-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.d-title-row h2 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--forest-dark);
  letter-spacing: -0.01em;
  line-height: 1.35;
}

.d-btn {
  padding: 7px 14px;
  font-size: 0.8rem;
  white-space: nowrap;
}

.d-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 0.8rem;
  color: var(--gray);
  margin-top: 6px;
}

.sep {
  opacity: 0.45;
}

.d-badges {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.heat-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 4px;
}

.heat-label {
  font-size: 0.74rem;
  color: var(--gray-light);
}

.heat-track {
  width: 88px;
  height: 5px;
  border-radius: 4px;
  background: var(--cream-dark);
  overflow: hidden;
}

.heat-track i {
  display: block;
  height: 100%;
  border-radius: 4px;
}

.heat-wrap b {
  font-size: 0.76rem;
  color: var(--ink-soft);
}

.d-desc {
  font-size: 0.9rem;
  color: var(--ink-soft);
  line-height: 1.85;
  margin: 16px 0 18px;
  padding-left: 12px;
  border-left: 3px solid var(--cream-dark);
}

.d-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 268px;
  gap: 14px;
  margin-bottom: 14px;
}

.d-side {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.stat {
  background: var(--cream);
  border-radius: 10px;
  padding: 9px 11px;
  display: flex;
  flex-direction: column;
}

.stat em {
  font-style: normal;
  font-size: 0.68rem;
  color: var(--gray-light);
}

.stat b {
  font-size: 1.08rem;
  color: var(--forest-dark);
  line-height: 1.4;
  font-weight: 700;
}

.stat b i {
  font-style: normal;
  font-size: 0.66rem;
  color: var(--gray);
  margin-left: 2px;
  font-weight: 400;
}

.stat b.small {
  font-size: 0.86rem;
}

.wp-box {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px 12px;
  flex: 1;
}

.wp-title {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--forest-dark);
  margin-bottom: 6px;
}

.wp-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.wp-list li {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 0.76rem;
}

.wp-idx {
  width: 17px;
  height: 17px;
  border-radius: 50%;
  background: var(--earth);
  color: #fff;
  font-size: 0.62rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-weight: 700;
}

.wp-idx.s {
  background: var(--green);
}

.wp-idx.e {
  background: var(--red);
}

.wp-name {
  flex: 1;
  color: var(--ink-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wp-km {
  font-size: 0.68rem;
  color: var(--gray-light);
}

.d-tip {
  display: flex;
  gap: 12px;
  margin-top: 14px;
  background: rgba(139, 105, 20, 0.06);
  border: 1px solid rgba(139, 105, 20, 0.16);
  border-radius: 10px;
  padding: 11px 14px;
}

.tip-label {
  font-size: 0.74rem;
  font-weight: 700;
  color: var(--earth);
  white-space: nowrap;
  padding-top: 1px;
}

.d-tip p {
  font-size: 0.8rem;
  color: var(--ink-soft);
  line-height: 1.7;
}

.d-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed var(--line);
  flex-wrap: wrap;
}

.d-foot .muted {
  font-size: 0.72rem;
}

.link-more {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--forest);
}

.link-more:hover {
  color: var(--forest-dark);
}

.wp-gap {
  font-size: 0.66rem;
  color: var(--earth);
  background: rgba(139, 105, 20, 0.09);
  padding: 1px 5px;
  border-radius: 5px;
}

/* ─── 路书 ─── */
.rb {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rb-block {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px 16px 16px;
  background: #fff;
}

.rb-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 0.92rem;
  font-weight: 700;
  color: var(--forest-dark);
  margin-bottom: 12px;
}

.rb-title span:first-child {
  font-size: 1rem;
}

.rb-sub {
  font-size: 0.72rem;
  font-weight: 400;
  color: var(--gray-light);
  margin-left: 6px;
}

.rb-table-wrap {
  overflow-x: auto;
  max-width: 100%;
  -webkit-overflow-scrolling: touch;
}

.detail,
.d-grid,
.rb,
.rb-block {
  min-width: 0;
}

.rb-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.79rem;
}

.rb-table th {
  text-align: left;
  font-weight: 600;
  color: var(--gray);
  font-size: 0.7rem;
  padding: 6px 8px;
  border-bottom: 1px solid var(--line);
  white-space: nowrap;
}

.rb-table td {
  padding: 9px 8px;
  border-bottom: 1px solid #f2f0ea;
  vertical-align: top;
  color: var(--ink-soft);
}

.rb-table tr:last-child td {
  border-bottom: none;
}

.rb-table .idx {
  color: var(--gray-light);
  font-size: 0.72rem;
  width: 22px;
}

.rb-table .place b {
  color: var(--ink);
  font-size: 0.82rem;
  display: inline-block;
  margin-right: 4px;
}

.rb-table .nowrap {
  white-space: nowrap;
}

.rb-table .gap {
  font-style: normal;
  color: var(--earth);
  font-size: 0.68rem;
  margin-left: 3px;
}

.rb-table .note {
  line-height: 1.65;
  font-size: 0.77rem;
  min-width: 220px;
}

.tag {
  display: inline-block;
  font-size: 0.62rem;
  padding: 1px 5px;
  border-radius: 4px;
  margin: 2px 2px 0 0;
  vertical-align: middle;
  background: var(--cream-dark);
  color: var(--gray);
}

.tag-start {
  background: rgba(39, 174, 96, 0.12);
  color: #1e8449;
}

.tag-end {
  background: rgba(192, 57, 43, 0.1);
  color: #a93226;
}

.tag-sup {
  background: rgba(41, 128, 185, 0.1);
  color: #2471a3;
}

.tag-camp {
  background: rgba(139, 105, 20, 0.12);
  color: #8b6914;
}

.tag-photo {
  background: rgba(142, 68, 173, 0.1);
  color: #7d3c98;
}

.rb-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.acc-list {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.acc-list li {
  display: flex;
  gap: 10px;
  font-size: 0.78rem;
  line-height: 1.65;
}

.acc-list b {
  flex-shrink: 0;
  width: 66px;
  color: var(--forest);
  font-size: 0.74rem;
  background: var(--forest-soft);
  height: 20px;
  line-height: 20px;
  text-align: center;
  border-radius: 5px;
  font-weight: 600;
}

.acc-list span {
  color: var(--ink-soft);
}

.sup-list,
.photo-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sup-list li,
.photo-list li {
  display: flex;
  gap: 10px;
  font-size: 0.78rem;
}

.sup-list b,
.photo-list b {
  flex-shrink: 0;
  color: var(--earth);
  font-size: 0.7rem;
  padding-top: 2px;
  width: 44px;
}

.sup-list strong,
.photo-list strong {
  font-size: 0.8rem;
  color: var(--ink);
}

.sup-list p,
.photo-list p {
  color: var(--gray);
  font-size: 0.75rem;
  line-height: 1.6;
  margin-top: 1px;
}

.sup-note {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--line);
  font-size: 0.72rem;
  color: var(--gray);
  line-height: 1.7;
}

.chips-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.gear-chip {
  font-size: 0.74rem;
  padding: 4px 10px;
  border-radius: 20px;
  background: var(--forest-soft);
  color: var(--forest-dark);
  border: 1px solid rgba(45, 90, 61, 0.15);
}

.risk-chip {
  font-size: 0.74rem;
  padding: 4px 10px;
  border-radius: 20px;
  background: rgba(192, 57, 43, 0.07);
  color: #a93226;
  border: 1px solid rgba(192, 57, 43, 0.14);
}

.gear-extra {
  margin-top: 10px;
  font-size: 0.72rem;
  color: var(--gray-light);
}

.muted {
  color: var(--gray-light);
  font-size: 0.76rem;
}

@media (max-width: 1180px) {
  .split {
    grid-template-columns: minmax(0, 1fr);
  }

  .list-col {
    position: static;
    max-height: 340px;
  }

  .d-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .d-side {
    flex-direction: row;
  }

  .stat-grid {
    flex: 1;
    grid-template-columns: 1fr 1fr;
  }

  .wp-box {
    flex: 1;
  }
}

@media (max-width: 760px) {
  .head-stats {
    display: none;
  }

  .detail {
    padding: 18px 16px;
  }

  .d-title-row {
    flex-direction: column;
  }

  .d-side {
    flex-direction: column;
  }

  .search-mini input {
    width: 90px;
  }

  .rb-cols {
    grid-template-columns: minmax(0, 1fr);
  }

  .rb-table .note {
    min-width: 180px;
  }
}
</style>
