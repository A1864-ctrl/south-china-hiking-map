<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { spots } from '../data/spots.js'
import { cityMeta } from '../data/cities.js'
import { spotPhotos } from '../data/photos.js'
import { matchLoose, haystack } from '../utils/search.js'
import HikeMap from '../components/HikeMap.vue'
import LightBox from '../components/LightBox.vue'
import { loadView, saveView } from '../utils/viewState.js'

const route = useRoute()
const router = useRouter()

const cityColors = {
  桂林: '#2d5a3d', 广州: '#b93a2c', 深圳: '#2471a3', 长沙: '#8b6914',
  湘西: '#6c3483', 张家界: '#148f77', 惠州: '#ca6f1e', 郴州: '#2c3e50'
}

const cities = Object.keys(cityMeta).filter((c) => spots.some((s) => s.city === c))
const keyword = ref('')
const activeCity = ref('')
const activeType = ref('')
const sortBy = ref('heat')
const mapRef = ref(null)

/* 列表状态记忆：从详情返回时回到刚才那屏（筛选 + 滚动位置都还原） */
const VIEW_KEY = 'spots'
let lastScroll = 0
function trackScroll() {
  lastScroll = window.scrollY || document.documentElement.scrollTop || 0
}
function persist() {
  saveView(VIEW_KEY, {
    keyword: keyword.value,
    city: activeCity.value,
    type: activeType.value,
    sort: sortBy.value,
    scroll: lastScroll
  })
}

const totalByCity = computed(() => {
  const m = {}
  spots.forEach((s) => (m[s.city] = (m[s.city] || 0) + 1))
  return m
})

/* ── 搜索：只认地名（城市 / 省份 / 区县） ── */
const PLACES = computed(() => {
  const set = new Set()
  spots.forEach((s) => {
    set.add(s.city)
    set.add(s.district)
  })
  Object.values(cityMeta).forEach((c) => set.add(c.province))
  return set
})

const placeMode = computed(() => {
  const q = keyword.value.trim()
  if (!q) return 'all'
  if (PLACES.value.has(q)) return 'place'
  const head = q.split(/\s+/)[0]
  if (PLACES.value.has(head)) return 'place'
  return 'unknown'
})

const placeTip = computed(() => {
  const q = keyword.value.trim()
  if (!q) return ''
  if (placeMode.value === 'place') return `按地名筛：${q}`
  return '这个搜索框只认地名（城市 / 省份 / 区县），例如 韶关、湘西、阳朔。找路线请去「徒步轨迹」。'
})

const cityScoped = computed(() => (activeCity.value ? spots.filter((s) => s.city === activeCity.value) : spots))

const typeCounts = computed(() => {
  const m = new Map()
  cityScoped.value.forEach((s) => m.set(s.type, (m.get(s.type) || 0) + 1))
  return [...m.entries()].map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count)
})

const showAllTypes = ref(false)
const typeOptions = computed(() => {
  const list = typeCounts.value
  if (showAllTypes.value || list.length <= 10) return list
  return list.slice(0, 10)
})

const filtered = computed(() => {
  const q = keyword.value.trim()
  const list = spots.filter((s) => {
    if (activeCity.value && s.city !== activeCity.value) return false
    if (activeType.value && s.type !== activeType.value) return false
    if (!q) return true
    if (placeMode.value === 'unknown') return false
    const parts = q.split(/\s+/)
    const place = parts[0]
    const rest = parts.slice(1).join('')
    if (!matchLoose(haystack(s.city, s.district), place)) return false
    if (rest) return matchLoose(haystack(s.name, s.type, s.reason, s.tags), rest)
    return true
  })
  return list.slice().sort((a, b) =>
    sortBy.value === 'heat' ? b.heat - a.heat : a.name.localeCompare(b.name, 'zh')
  )
})

const mapPoints = computed(() =>
  filtered.value.map((s) => ({
    id: s.id, lat: s.lat, lng: s.lng, name: s.name,
    sub: `${s.city} · ${s.type}`, color: cityColors[s.city] || '#2d5a3d'
  }))
)
const mapCenter = computed(() => (activeCity.value ? cityMeta[activeCity.value].center : [24.4, 112.4]))

function cover(s) {
  const p = spotPhotos(s.name)
  return p.length ? p[0].src : ''
}
function open(s) {
  router.push(`/spot/${encodeURIComponent(s.name)}`)
}

/* 双击图片看大图：把当前筛选出来的所有点位封面串成画廊 */
const gallery = computed(() =>
  filtered.value.map((s) => ({
    src: cover(s),
    title: s.name,
    caption: `${s.city} · ${s.type} · 热度 ${s.heat}`
  }))
)
const lbOpen = ref(false)
const lbIndex = ref(0)
const selectedId = ref(null)

/** 单击卡片：选中并把地图定位到这个点位 */
function select(s) {
  selectedId.value = s.id
  if (mapRef.value) mapRef.value.focusPoint(s.id, 12)
}
function openAt(i) {
  if (!gallery.value[i]) return
  lbIndex.value = i
  lbOpen.value = true
}

/** 整卡双击分发：封面 → 看大图，文字区 → 进路书 */
function onDbl(e, i, s) {
  const t = e.target
  if (t && t.closest && t.closest('.cover')) openAt(i)
  else open(s)
}

/* 双击图片看大图：把当前筛选出来的所有点位封面串成画廊 */
function selectCity(c) {
  activeCity.value = activeCity.value === c ? '' : c
  activeType.value = ''
}
function pickType(t) {
  activeType.value = activeType.value === t ? '' : t
}
function clearAll() {
  keyword.value = ''
  activeCity.value = ''
  activeType.value = ''
}

onMounted(async () => {
  window.addEventListener('scroll', trackScroll, { passive: true })

  if (route.query.open) {
    router.replace(`/spot/${encodeURIComponent(String(route.query.open))}`)
    return
  }

  const fromLink = Boolean(route.query.city || route.query.q)
  if (route.query.city && cityMeta[route.query.city]) activeCity.value = String(route.query.city)
  if (route.query.q) keyword.value = String(route.query.q)

  // 从详情页返回时，恢复上一次的筛选与滚动位置
  const st = fromLink ? null : loadView(VIEW_KEY)
  if (st) {
    keyword.value = st.keyword || ''
    activeCity.value = st.city || ''
    activeType.value = st.type || ''
    sortBy.value = st.sort || 'heat'
  }

  await nextTick()
  setTimeout(() => {
    if (mapRef.value && filtered.value.length) {
      mapRef.value.fitBounds(filtered.value.map((s) => [s.lat, s.lng]))
    }
  }, 300)

  if (st && st.scroll > 0) {
    // 等图片与地图把高度撑开再跳，避免滚到一半被拉回
    setTimeout(() => {
      window.scrollTo({ top: st.scroll, behavior: 'auto' })
      lastScroll = st.scroll
    }, 460)
  }
})

onUnmounted(() => {
  window.removeEventListener('scroll', trackScroll)
  persist()
})
</script>

<template>
  <div class="page">
    <!-- 常驻搜索条 -->
    <div class="sticky-bar">
      <div class="bar-inner">
        <label class="search">
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" stroke-width="1.8" />
            <path d="M16 16l4.5 4.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
          </svg>
          <input v-model="keyword" type="search" placeholder="只搜地名：城市 / 省份 / 区县（例：韶关、阳朔）" />
          <button v-if="keyword" class="clear" @click="keyword = ''">×</button>
        </label>
        <span class="hit">共 <b>{{ filtered.length }}</b> 个点位</span>
      </div>
      <div class="bar-tip">
        <span class="tip" :class="{ warn: placeMode === 'unknown' }">
          {{ placeTip || '这个搜索框只支持地名：城市（韶关）、省份（湖南）、区县（阳朔）。找徒步路线请去「徒步轨迹」。' }}
        </span>
      </div>
    </div>

    <div class="container">
      <header class="head">
        <p class="eyebrow">SPOT GUIDE</p>
        <h1>去哪儿，什么时候去，去了拍什么</h1>
        <p class="lead">
          {{ spots.length }} 个点位，每个都写了四季表现、日落和夜景的时间位置、机位怎么找、饿了吃什么。
          单击卡片在地图上定位，<b>双击图片看大图</b>，<b>双击文字进路书</b>。
        </p>
      </header>

      <section class="panel">
        <div class="facet">
          <span class="fl">城市</span>
          <div class="chips">
            <button class="chip" :class="{ active: activeCity === '' }" @click="activeCity = ''; activeType = ''">
              全部<em>{{ spots.length }}</em>
            </button>
            <button
              v-for="c in cities"
              :key="c"
              class="chip"
              :class="{ active: activeCity === c }"
              @click="selectCity(c)"
            >
              <i class="dot" :style="{ background: cityColors[c] }"></i>{{ c }}<em>{{ totalByCity[c] }}</em>
            </button>
          </div>
        </div>
        <div class="facet">
          <span class="fl">类型</span>
          <div class="chips">
            <button class="chip" :class="{ active: activeType === '' }" @click="activeType = ''">全部类型</button>
            <button
              v-for="t in typeOptions"
              :key="t.name"
              class="chip"
              :class="{ active: activeType === t.name }"
              @click="pickType(t.name)"
            >
              {{ t.name }}<em>{{ t.count }}</em>
            </button>
            <button v-if="typeCounts.length > 10" class="chip more" @click="showAllTypes = !showAllTypes">
              {{ showAllTypes ? '收起' : `还有 ${typeCounts.length - 10} 类` }}
            </button>
          </div>
        </div>
      </section>

      <div class="layout">
        <div class="list-col">
          <p class="count-line">
            全部点位 <b>{{ filtered.length }}</b> 个
            <button v-if="keyword || activeCity || activeType" class="reset" @click="clearAll">清空筛选</button>
            <span class="sort">
              <button :class="{ on: sortBy === 'heat' }" @click="sortBy = 'heat'">热度</button>
              <button :class="{ on: sortBy === 'name' }" @click="sortBy = 'name'">名称</button>
            </span>
          </p>

          <div v-if="filtered.length" class="grid">
            <article
              v-for="(s, i) in filtered"
              :key="s.id"
              class="card"
              :class="{ active: selectedId === s.id }"
              @click="select(s)"
              @dblclick="onDbl($event, i, s)"
            >
              <figure class="cover" title="双击看大图">
                <img v-if="cover(s)" :src="cover(s)" :alt="s.name" loading="lazy" />
                <div v-else class="cover-empty"></div>
                <span class="city" :style="{ background: cityColors[s.city] || '#2d5a3d' }">{{ s.city }}</span>
                <span class="heat mono">{{ s.heat }}</span>
                <span class="dbl-hint">双击看大图</span>
              </figure>
              <div class="body" :title="`双击进入「${s.name}」路书`">
                <h3>{{ s.name }}<em>{{ s.district }}</em></h3>
                <p class="reason">{{ s.reason }}</p>
                <div class="metas">
                  <span>{{ s.ticket }}</span>
                  <span>·</span>
                  <span>{{ s.hours }}</span>
                  <button class="go" @click.stop="open(s)" @dblclick.stop="open(s)">看路书 →</button>
                </div>
              </div>
            </article>
          </div>
          <p v-else class="empty">
            {{ placeMode === 'unknown' ? '这个关键词不是地名：试试城市（韶关）、省份（湖南）或区县（阳朔）' : '没有匹配的点位' }}
          </p>
        </div>

        <aside class="map-col">
          <HikeMap
            ref="mapRef"
            :points="mapPoints"
            :center="mapCenter"
            :zoom="activeCity ? 9 : 7"
            height="520px"
            label="点位分布"
          />
          <p class="map-note">
            地图右上角可切「高德矢量 / 天地卫星」。点地图上的点会弹出名称，左侧卡片同步筛选。
          </p>
        </aside>
      </div>
    </div>

    <LightBox
      :images="gallery"
      :index="lbIndex"
      :open="lbOpen"
      @close="lbOpen = false"
      @update:index="lbIndex = $event"
    >
      <template #actions="{ image }">
        <button class="lb-enter" @click="open({ name: image.title })">查看这个点位的路书 →</button>
      </template>
    </LightBox>
  </div>
</template>

<style scoped>
.page {
  padding-top: var(--nav-h);
  min-height: 100vh;
}

.sticky-bar {
  position: sticky;
  top: var(--nav-h);
  z-index: 40;
  background: rgba(250, 248, 242, 0.97);
  backdrop-filter: saturate(180%) blur(12px);
  border-bottom: 1px solid var(--line);
}

.bar-inner {
  max-width: 1320px;
  margin: 0 auto;
  padding: 11px 28px 6px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.bar-tip {
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 28px 10px;
}

.tip {
  font-size: 0.72rem;
  color: var(--gray);
}

.tip.warn {
  color: #9a5a25;
}

.search {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 38px;
  padding: 0 12px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 10px;
  color: var(--gray-light);
}

.search input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.84rem;
  color: var(--ink);
}

.clear {
  border: none;
  background: transparent;
  font-size: 1.1rem;
  color: var(--gray-light);
  cursor: pointer;
  line-height: 1;
}

.hit {
  font-size: 0.76rem;
  color: var(--gray);
  white-space: nowrap;
}

.hit b {
  color: var(--forest-dark);
}

.container {
  max-width: 1320px;
  margin: 0 auto;
  padding: 24px 28px 70px;
}

.eyebrow {
  font-family: var(--serif);
  font-size: 0.68rem;
  letter-spacing: 0.26em;
  color: var(--earth);
}

.head h1 {
  font-family: var(--serif);
  font-size: 1.7rem;
  margin: 8px 0 10px;
  color: var(--forest-dark);
}

.lead {
  font-size: 0.85rem;
  line-height: 1.9;
  color: var(--gray);
  max-width: 780px;
}

.panel {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px 16px 12px;
  margin: 18px 0 14px;
}

.facet {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 5px 0;
}

.fl {
  width: 34px;
  flex-shrink: 0;
  font-size: 0.72rem;
  color: var(--gray-light);
  padding-top: 6px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  border: 1px solid var(--line);
  background: #fcfbf7;
  border-radius: 999px;
  padding: 5px 11px;
  font-size: 0.75rem;
  color: var(--ink-soft);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.chip em {
  font-style: normal;
  font-size: 0.66rem;
  color: var(--gray-light);
}

.chip.active {
  background: var(--forest);
  border-color: var(--forest);
  color: #fff;
}

.chip.active em {
  color: rgba(255, 255, 255, 0.7);
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1.75fr) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.count-line {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.78rem;
  color: var(--gray);
  margin-bottom: 10px;
}

.count-line b {
  color: var(--forest-dark);
}

.reset {
  border: none;
  background: transparent;
  color: var(--forest);
  font-size: 0.74rem;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.sort {
  margin-left: auto;
  display: flex;
  gap: 4px;
}

.sort button {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--gray);
  font-size: 0.72rem;
  padding: 3px 9px;
  border-radius: 6px;
  cursor: pointer;
}

.sort button.on {
  background: var(--forest-soft);
  border-color: var(--forest-light);
  color: var(--forest-dark);
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 13px;
  overflow: hidden;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.cover {
  position: relative;
  margin: 0;
  aspect-ratio: 16 / 10;
  background: #e4ebe3;
  overflow: hidden;
}

.cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.4s ease;
}

.card:hover .cover img {
  transform: scale(1.04);
}

.cover-empty {
  width: 100%;
  height: 100%;
  background: linear-gradient(140deg, #dfe7dd, #c7d5c6);
}

.city {
  position: absolute;
  left: 9px;
  top: 9px;
  font-size: 0.66rem;
  padding: 2px 8px;
  border-radius: 999px;
  color: #fff;
}

.heat {
  position: absolute;
  right: 9px;
  top: 9px;
  font-size: 0.68rem;
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--forest-dark);
}

.dbl-hint {
  position: absolute;
  right: 9px;
  bottom: 9px;
  font-size: 0.63rem;
  color: #fff;
  background: rgba(12, 22, 16, 0.5);
  padding: 2px 8px;
  border-radius: 999px;
  opacity: 0;
  transition: opacity 0.16s;
  pointer-events: none;
}

.cover:hover .dbl-hint {
  opacity: 1;
}

.body {
  padding: 11px 13px 12px;
  cursor: pointer;
}

.body h3 {
  font-size: 0.94rem;
  color: var(--forest-dark);
  display: flex;
  align-items: baseline;
  gap: 7px;
}

.body h3 em {
  font-style: normal;
  font-size: 0.66rem;
  color: var(--gray-light);
}

.reason {
  margin-top: 5px;
  font-size: 0.74rem;
  line-height: 1.65;
  color: var(--gray);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.metas {
  margin-top: 9px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.7rem;
  color: var(--gray-light);
}

.go {
  margin-left: auto;
  color: var(--forest);
  font-weight: 500;
  font-size: 0.72rem;
  border: 1px solid rgba(45, 90, 61, 0.24);
  background: var(--forest-soft);
  padding: 3px 10px;
  border-radius: 999px;
  cursor: pointer;
}

.go:hover {
  background: var(--forest);
  color: #fff;
}

.card.active {
  border-color: var(--forest-light);
  box-shadow: 0 0 0 2px rgba(45, 90, 61, 0.14), var(--shadow);
}

.map-col {
  position: sticky;
  top: calc(var(--nav-h) + 78px);
}

.map-note {
  margin-top: 8px;
  font-size: 0.7rem;
  line-height: 1.7;
  color: var(--gray);
}

.lb-enter {
  border: none;
  background: var(--forest);
  color: #fff;
  font-size: 0.78rem;
  padding: 7px 14px;
  border-radius: 999px;
  cursor: pointer;
}

.lb-enter {
  border: none;
  background: var(--forest);
  color: #fff;
  font-size: 0.78rem;
  padding: 7px 14px;
  border-radius: 999px;
  cursor: pointer;
}

.empty {
  padding: 50px 0;
  text-align: center;
  color: var(--gray-light);
  font-size: 0.84rem;
}

@media (max-width: 1080px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }
  .map-col {
    position: static;
  }
}

@media (max-width: 680px) {
  .grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .bar-inner,
  .bar-tip,
  .container {
    padding-left: 16px;
    padding-right: 16px;
  }
  .head h1 {
    font-size: 1.35rem;
  }
  .facet {
    flex-direction: column;
    gap: 6px;
  }
}
</style>
