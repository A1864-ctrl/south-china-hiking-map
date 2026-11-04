<script setup>
import { computed, onMounted, ref, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { spots } from '../data/spots.js'
import { cityMeta } from '../data/cities.js'
import { getGuide } from '../data/spotGuide.js'
import HikeMap from '../components/HikeMap.vue'

const route = useRoute()
const router = useRouter()

const cityColors = {
  桂林: '#2d5a3d',
  广州: '#c0392b',
  深圳: '#2980b9',
  长沙: '#8b6914',
  湘西: '#7d3c98',
  张家界: '#16a085',
  惠州: '#d35400',
  郴州: '#2c3e50'
}

const cities = Object.keys(cityMeta).filter((c) => spots.some((s) => s.city === c))
const keyword = ref('')
const activeCity = ref('')
const activeType = ref('')
const sortBy = ref('heat')
const selectedId = ref(null)
const mapRef = ref(null)
const guideSpot = ref(null)
const guideData = computed(() => (guideSpot.value ? getGuide(guideSpot.value.name, guideSpot.value.city) : null))

function openGuide(s) {
  guideSpot.value = s
  document.body.style.overflow = 'hidden'
}

function closeGuide() {
  guideSpot.value = null
  document.body.style.overflow = ''
}

const types = computed(() => {
  const m = new Map()
  spots.forEach((s) => m.set(s.type, (m.get(s.type) || 0) + 1))
  return [...m.entries()].sort((a, b) => b[1] - a[1]).map(([name]) => name)
})

const typeCounts = computed(() => {
  const m = new Map()
  spots.forEach((s) => m.set(s.type, (m.get(s.type) || 0) + 1))
  return [...m.entries()].map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count)
})

const showAllTypes = ref(false)
const typeOptions = computed(() => {
  if (showAllTypes.value) return typeCounts.value
  const top = typeCounts.value.slice(0, 10)
  if (activeType.value && !top.some((t) => t.name === activeType.value)) {
    top.push(typeCounts.value.find((t) => t.name === activeType.value))
  }
  return top
})

const filtered = computed(() => {
  const kw = keyword.value.trim()
  let list = spots.filter((s) => {
    if (activeCity.value && s.city !== activeCity.value) return false
    if (activeType.value && s.type !== activeType.value) return false
    if (!kw) return true
    return (
      s.name.includes(kw) ||
      s.city.includes(kw) ||
      s.district.includes(kw) ||
      s.type.includes(kw) ||
      s.reason.includes(kw) ||
      s.tags.some((t) => t.includes(kw))
    )
  })
  list = list.slice().sort((a, b) =>
    sortBy.value === 'heat' ? b.heat - a.heat : a.name.localeCompare(b.name, 'zh')
  )
  return list
})

const mapPoints = computed(() =>
  filtered.value.map((s) => ({
    id: s.id,
    lat: s.lat,
    lng: s.lng,
    name: s.name,
    sub: `${s.city} · ${s.type} · 热度 ${s.heat}`,
    color: cityColors[s.city] || '#2d5a3d'
  }))
)

const mapCenter = computed(() => {
  if (activeCity.value) return cityMeta[activeCity.value].center
  return [24.4, 112.4]
})

const mapZoom = computed(() => (activeCity.value ? 9 : 7))

const activeCityStats = computed(() => {
  if (!activeCity.value) return null
  const list = filtered.value
  const avg = list.length ? Math.round(list.reduce((a, s) => a + s.heat, 0) / list.length) : 0
  return { count: list.length, avg }
})

function selectCity(name) {
  activeCity.value = activeCity.value === name ? '' : name
  activeType.value = ''
  selectedId.value = null
  if (activeCity.value) {
    router.replace({ query: { ...route.query, city: activeCity.value } })
  } else {
    const q = { ...route.query }
    delete q.city
    router.replace({ query: q })
  }
}

function resetAll() {
  keyword.value = ''
  activeCity.value = ''
  activeType.value = ''
  selectedId.value = null
  router.replace({ query: {} })
}

function selectSpot(s) {
  selectedId.value = s.id
  if (mapRef.value) {
    mapRef.value.focus(s.lat, s.lng, 12)
  }
}

function onPinClick(id) {
  selectedId.value = id
  const el = document.getElementById('spot-' + id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

watch(
  [filtered],
  () => {
    nextTick(() => {
      setTimeout(() => {
        if (mapRef.value && filtered.value.length) {
          mapRef.value.fitBounds(filtered.value.map((s) => [s.lat, s.lng]))
        }
      }, 120)
    })
  },
  { immediate: true }
)

onMounted(() => {
  const q = route.query
  if (q.city && cityMeta[q.city]) activeCity.value = String(q.city)
  if (q.q) keyword.value = String(q.q)
  if (q.type) activeType.value = String(q.type)

  // 首屏（地图刚挂载）补一次自适应，否则会停在默认的华南全景
  nextTick(() => {
    setTimeout(() => {
      if (mapRef.value && filtered.value.length) {
        mapRef.value.fitBounds(filtered.value.map((s) => [s.lat, s.lng]))
      }
    }, 260)
  })
})
</script>

<template>
  <div class="page">
    <div class="container">
      <div class="page-head">
        <div>
          <h1 class="page-title"><span>🔍</span>景点搜索</h1>
          <p class="page-desc">
            输入地名（城市、区县、景点名或类型），看这个片区值得去哪些地方、为什么值得去。左侧筛选，右侧地图同步联动。
          </p>
        </div>
        <div class="head-stats">
          <div class="hs"><b class="mono">{{ spots.length }}</b><em>收录景点</em></div>
          <div class="hs"><b class="mono">{{ cities.length }}</b><em>覆盖城市</em></div>
          <div class="hs"><b class="mono">{{ types.length }}</b><em>景点类型</em></div>
        </div>
      </div>

      <!-- 搜索区 -->
      <div class="search-panel card">
        <div class="search-row">
          <div class="search-box">
            <span class="s-icon">⌕</span>
            <input
              v-model="keyword"
              type="text"
              placeholder="输入城市、区县、景点名或类型，例如：桂林 / 丹霞 / 海岸 / 古镇"
            />
            <button v-if="keyword" class="s-clear" @click="keyword = ''">✕</button>
          </div>
          <button class="btn btn-ghost" @click="resetAll">看全部</button>
        </div>

        <div class="chip-group">
          <span class="cg-label">热门城市</span>
          <div class="cg-chips">
            <button
              class="chip"
              :class="{ active: activeCity === '' }"
              @click="selectCity('')"
            >
              全部
            </button>
            <button
              v-for="c in cities"
              :key="c"
              class="chip"
              :class="{ active: activeCity === c }"
              @click="selectCity(c)"
            >
              <i class="dot" :style="{ background: cityColors[c] }"></i>{{ c }}
            </button>
          </div>
        </div>

        <div class="chip-group">
          <span class="cg-label">景点类型</span>
          <div class="cg-chips">
            <button class="chip sm" :class="{ active: activeType === '' }" @click="activeType = ''">
              全部类型
            </button>
            <button
              v-for="t in typeOptions"
              :key="t.name"
              class="chip sm"
              :class="{ active: activeType === t.name }"
              @click="activeType = activeType === t.name ? '' : t.name"
            >
              {{ t.name }}<em>{{ t.count }}</em>
            </button>
            <button class="chip sm more" @click="showAllTypes = !showAllTypes">
              {{ showAllTypes ? '收起 ∧' : `全部 ${types.length} 类 ∨` }}
            </button>
          </div>
        </div>
      </div>

      <!-- 结果头 -->
      <div class="result-bar">
        <div class="rb-left">
          <h2 class="rb-title">
            {{ activeCity || '全部' }}
            <span class="rb-sub">找到 <b class="mono">{{ filtered.length }}</b> 个景点</span>
          </h2>
          <span v-if="keyword" class="rb-kw">关键词「{{ keyword }}」</span>
          <span v-if="activeType" class="rb-kw">类型「{{ activeType }}」</span>
          <span v-if="activeCityStats" class="rb-kw">
            平均热度 {{ activeCityStats.avg }} / 100
          </span>
        </div>
        <div class="rb-sort">
          <button class="sort-btn" :class="{ on: sortBy === 'heat' }" @click="sortBy = 'heat'">按热度</button>
          <button class="sort-btn" :class="{ on: sortBy === 'name' }" @click="sortBy = 'name'">按名称</button>
        </div>
      </div>

      <!-- 主体 -->
      <div class="split">
        <div class="list-col">
          <div v-if="filtered.length" class="spot-grid">
            <article
              v-for="s in filtered"
              :id="'spot-' + s.id"
              :key="s.id"
              class="spot-card"
              :class="{ selected: selectedId === s.id }"
              @click="selectSpot(s)"
            >
              <div class="sc-top">
                <div class="sc-title">
                  <span class="sc-dot" :style="{ background: cityColors[s.city] }"></span>
                  <h3>{{ s.name }}</h3>
                </div>
                <span class="badge badge-ghost">{{ s.type }}</span>
              </div>
              <div class="sc-meta">
                <span>{{ s.city }} · {{ s.district }}</span>
                <span class="sep">|</span>
                <span>{{ s.ticket }}</span>
                <span class="sep">|</span>
                <span>{{ s.hours }}</span>
              </div>
              <p class="sc-reason">{{ s.reason }}</p>
              <button class="sc-guide" @click.stop="openGuide(s)">查看路书 · 打卡 / 美食 / 交通</button>
              <div class="sc-bottom">
                <div class="sc-tags">
                  <span v-for="t in s.tags" :key="t" class="tag">{{ t }}</span>
                </div>
                <div class="sc-heat">
                  <div class="heat-bar"><i :style="{ width: s.heat + '%' }"></i></div>
                  <span class="mono">{{ s.heat }}</span>
                </div>
              </div>
            </article>
          </div>

          <div v-else class="empty card">
            <div class="empty-icon">🧭</div>
            <h3>这个片区暂时没有匹配的景点</h3>
            <p>试试换个关键词，或点「看全部」回到完整列表。</p>
            <button class="btn btn-primary" @click="resetAll">看全部景点</button>
          </div>
        </div>

        <aside class="map-col">
          <div class="map-card">
            <div class="map-head">
              <div>
                <h4>点位分布</h4>
                <p>{{ filtered.length }} 个点位 · {{ activeCity || '华南片区' }}</p>
              </div>
              <span class="map-badge">高德底图</span>
            </div>
            <HikeMap
              ref="mapRef"
              :points="mapPoints"
              :center="mapCenter"
              :zoom="mapZoom"
              height="min(66vh, 620px)"
              label=""
              :fit-track="false"
              @pin-click="onPinClick"
            />
            <div class="legend">
              <span v-for="c in cities" :key="c" class="lg">
                <i :style="{ background: cityColors[c] }"></i>{{ c }}
              </span>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <!-- 景点路书弹层 -->
    <div v-if="guideSpot" class="modal-mask" @click.self="closeGuide">
      <div class="modal">
        <header class="m-head">
          <div>
            <h3>{{ guideSpot.name }}</h3>
            <p>{{ guideSpot.city }} · {{ guideSpot.district }} · {{ guideSpot.type }} · {{ guideSpot.ticket }} · {{ guideSpot.hours }}</p>
          </div>
          <button class="m-close" @click="closeGuide">✕</button>
        </header>

        <div class="m-body">
          <p class="m-reason">{{ guideSpot.reason }}</p>

          <section class="m-block">
            <h4>📷 打卡机位</h4>
            <ol class="m-list">
              <li v-for="(x, i) in guideData.photo" :key="x">
                <span class="m-idx">{{ i + 1 }}</span><span>{{ x }}</span>
              </li>
            </ol>
            <p v-if="!guideData.photo.length" class="m-muted">以自然景观为主，沿途皆可取景。</p>
          </section>

          <section class="m-block" v-if="guideData.route">
            <h4>🧭 推荐走法</h4>
            <p class="m-text">{{ guideData.route }}</p>
          </section>

          <section class="m-block" v-if="guideData.access">
            <h4>🚄 怎么去</h4>
            <p class="m-text">{{ guideData.access }}</p>
          </section>

          <section class="m-block">
            <h4>🍜 当地吃什么</h4>
            <div class="m-chips">
              <span v-for="f in guideData.food" :key="f" class="m-chip">{{ f }}</span>
            </div>
          </section>

          <section class="m-block m-tip">
            <h4>💡 实用提示</h4>
            <p class="m-text">{{ guideSpot.tags.join(' · ') }}｜门票 {{ guideSpot.ticket }}，建议 {{ guideSpot.hours }}。旺季提前在官方公众号预约，雨天备选室内展馆。</p>
          </section>
        </div>

        <footer class="m-foot">
          <button class="btn btn-primary" @click="closeGuide">知道了</button>
        </footer>
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

/* 搜索面板 */
.search-panel {
  padding: 18px 20px 14px;
  margin-bottom: 20px;
}

.search-row {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
}

.search-row .btn {
  flex-shrink: 0;
  white-space: nowrap;
}

.search-box {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--cream);
  border: 1.5px solid transparent;
  border-radius: 11px;
  padding: 0 14px;
  transition: all 0.18s;
}

.search-box:focus-within {
  background: #fff;
  border-color: var(--forest-light);
  box-shadow: 0 0 0 4px rgba(74, 124, 89, 0.1);
}

.s-icon {
  font-size: 1.1rem;
  color: var(--gray);
}

.search-box input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  padding: 12px 0;
  font-size: 0.92rem;
  color: var(--ink);
}

.search-box input::placeholder {
  color: var(--gray-light);
}

.s-clear {
  color: var(--gray-light);
  font-size: 0.8rem;
  padding: 4px;
}

.s-clear:hover {
  color: var(--red);
}

.chip-group {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding-top: 10px;
}

.chip-group + .chip-group {
  border-top: 1px dashed var(--line);
  margin-top: 10px;
}

.cg-label {
  flex-shrink: 0;
  font-size: 0.76rem;
  color: var(--gray-light);
  padding-top: 9px;
  width: 60px;
}

.cg-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}

.chip em {
  font-style: normal;
  font-size: 0.68rem;
  opacity: 0.55;
  margin-left: 3px;
}

.chip.active em {
  opacity: 0.8;
}

.chip.more {
  color: var(--gray);
  border-style: dashed;
}

/* 结果头 */
.result-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.rb-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}

.rb-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--forest-dark);
}

.rb-sub {
  font-size: 0.84rem;
  font-weight: 400;
  color: var(--gray);
  margin-left: 6px;
}

.rb-sub b {
  color: var(--earth);
  font-size: 1rem;
}

.rb-kw {
  font-size: 0.76rem;
  color: var(--gray);
  background: var(--white);
  border: 1px solid var(--line);
  padding: 2px 9px;
  border-radius: 6px;
}

.rb-sort {
  display: flex;
  gap: 4px;
  background: var(--white);
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 3px;
}

.sort-btn {
  font-size: 0.78rem;
  color: var(--gray);
  padding: 4px 12px;
  border-radius: 6px;
}

.sort-btn.on {
  background: var(--forest-soft);
  color: var(--forest);
  font-weight: 600;
}

/* 分栏 */
.split {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 460px;
  gap: 20px;
  align-items: start;
}

.spot-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.spot-card {
  background: #fff;
  border: 1.5px solid var(--line);
  border-radius: 13px;
  padding: 16px 16px 12px;
  cursor: pointer;
  transition: all 0.18s ease;
  display: flex;
  flex-direction: column;
}

.spot-card:hover {
  border-color: var(--forest-light);
  box-shadow: var(--shadow);
  transform: translateY(-2px);
}

.spot-card.selected {
  border-color: var(--forest);
  box-shadow: 0 6px 20px rgba(45, 90, 61, 0.16);
  background: #fcfdfb;
}

.sc-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.sc-title {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.sc-title h3 {
  font-size: 0.98rem;
  font-weight: 700;
  color: var(--forest-dark);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sc-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.sc-meta {
  font-size: 0.74rem;
  color: var(--gray-light);
  margin: 5px 0 8px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.sep {
  opacity: 0.5;
}

.sc-reason {
  font-size: 0.83rem;
  color: var(--ink-soft);
  line-height: 1.65;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 12px;
  flex: 1;
}

.sc-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.sc-tags {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.tag {
  font-size: 0.68rem;
  color: var(--forest-light);
  background: var(--forest-soft);
  padding: 1px 7px;
  border-radius: 5px;
}

.sc-heat {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.heat-bar {
  width: 46px;
  height: 4px;
  border-radius: 4px;
  background: var(--cream-dark);
  overflow: hidden;
}

.heat-bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--earth-light), var(--earth));
  border-radius: 4px;
}

.sc-heat span {
  font-size: 0.72rem;
  color: var(--earth);
  font-weight: 600;
}

/* 地图列 */
.map-col {
  position: sticky;
  top: calc(var(--nav-h) + 20px);
}

.map-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 14px;
  box-shadow: var(--shadow-sm);
}

.map-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 10px;
}

.map-head h4 {
  font-size: 0.9rem;
  color: var(--forest-dark);
}

.map-head p {
  font-size: 0.74rem;
  color: var(--gray);
}

.map-badge {
  font-size: 0.68rem;
  color: var(--gray);
  border: 1px solid var(--line);
  padding: 2px 8px;
  border-radius: 6px;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  margin-top: 10px;
}

.lg {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.72rem;
  color: var(--gray);
}

.lg i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

/* 空状态 */
.empty {
  padding: 60px 24px;
  text-align: center;
}

.empty-icon {
  font-size: 2.2rem;
  margin-bottom: 10px;
}

.empty h3 {
  font-size: 1.05rem;
  color: var(--forest-dark);
  margin-bottom: 6px;
}

.empty p {
  font-size: 0.85rem;
  color: var(--gray);
  margin-bottom: 18px;
}

@media (max-width: 1180px) {
  .split {
    grid-template-columns: 1fr;
  }

  .map-col {
    position: static;
    order: -1;
  }

  .spot-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .spot-grid {
    grid-template-columns: 1fr;
  }

  .head-stats {
    display: none;
  }

  .cg-label {
    display: none;
  }
}

/* 路书按钮 */
.sc-guide {
  margin-top: 8px;
  font-size: 0.72rem;
  color: var(--forest);
  background: var(--forest-soft);
  border: 1px solid rgba(45, 90, 61, 0.16);
  border-radius: 7px;
  padding: 4px 10px;
  cursor: pointer;
  width: fit-content;
}

.sc-guide:hover {
  background: rgba(45, 90, 61, 0.14);
}

/* 弹层 */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(24, 32, 27, 0.45);
  backdrop-filter: blur(3px);
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.modal {
  background: #fff;
  width: min(680px, 100%);
  max-height: 86vh;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.22);
}

.m-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 22px 14px;
  border-bottom: 1px solid var(--line);
}

.m-head h3 {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--forest-dark);
}

.m-head p {
  font-size: 0.76rem;
  color: var(--gray);
  margin-top: 4px;
}

.m-close {
  border: none;
  background: var(--cream);
  width: 30px;
  height: 30px;
  border-radius: 50%;
  color: var(--gray);
  cursor: pointer;
  flex-shrink: 0;
}

.m-body {
  padding: 16px 22px 6px;
  overflow-y: auto;
}

.m-reason {
  font-size: 0.84rem;
  color: var(--ink-soft);
  line-height: 1.8;
  background: var(--cream);
  border-radius: 10px;
  padding: 10px 12px;
}

.m-block {
  margin-top: 16px;
}

.m-block h4 {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--forest-dark);
  margin-bottom: 8px;
}

.m-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.m-list li {
  display: flex;
  gap: 8px;
  font-size: 0.8rem;
  color: var(--ink-soft);
  line-height: 1.6;
}

.m-idx {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--earth);
  color: #fff;
  font-size: 0.66rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
}

.m-text {
  font-size: 0.8rem;
  color: var(--ink-soft);
  line-height: 1.8;
}

.m-muted {
  font-size: 0.76rem;
  color: var(--gray-light);
}

.m-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.m-chip {
  font-size: 0.74rem;
  padding: 4px 10px;
  border-radius: 20px;
  background: rgba(139, 105, 20, 0.08);
  color: var(--earth);
  border: 1px solid rgba(139, 105, 20, 0.16);
}

.m-tip {
  border-top: 1px dashed var(--line);
  padding-top: 12px;
  margin-bottom: 8px;
}

.m-foot {
  padding: 12px 22px 18px;
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--line);
}
</style>
