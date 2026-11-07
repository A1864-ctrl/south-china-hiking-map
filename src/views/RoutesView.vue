<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { routes, terrains, provinces } from '../data/routes.js'
import { spotCity } from '../data/gallery.js'
import { routePhotoOf } from '../data/photos.js'
import { matchLoose, haystack } from '../utils/search.js'
import { useMineStore } from '../stores/mine.js'
import LightBox from '../components/LightBox.vue'
import { loadView, saveView } from '../utils/viewState.js'

const router = useRouter()
const mine = useMineStore()

const levelColor = { easy: '#27ae60', mid: '#2980b9', hard: '#c0392b' }
const levelLabel = { easy: '入门', mid: '进阶', hard: '顶级' }
const CORE = ['广东', '广西', '湖南', '江西']

const terrainTheme = {
  高山草甸: 'grass', 森林古道: 'forest', 海岸礁石: 'sea', 山峰野线: 'mountain', 溪谷石阶: 'river',
  溪谷瀑布: 'river', 山脊岩壁: 'mountain', 喀斯特田园: 'terrace', 丹霞地貌: 'danxia', 峡谷: 'peak',
  森林山峰: 'forest', 山峰草甸: 'grass', 原始森林: 'forest', 城市山: 'city', 石阶古道: 'mountain',
  古道: 'town', 峰林溪谷: 'peak', 峰林: 'peak', 山峰栈道: 'peak', 丹霞: 'danxia', 峡谷山峰: 'peak',
  山峰: 'mountain', 茶山: 'terrace', 花岗岩峰林: 'peak', 花岗岩: 'mountain', 高山石海: 'mountain',
  高原雪山: 'mountain'
}

/* ── 搜索：只认两种写法 ──
   1) 地名：城市 / 省份 / 区县
   2) 徒步名称 + 路线：「武功山徒步」「船底顶 罗新线」这种，名字后面跟 徒步/路线/穿越… */
const keyword = ref('')
const ROUTE_WORDS = /(徒步|路线|穿越|环线|登顶|古道|海岸线|线)$/
const CITY_NAMES = new Set(routes.map((r) => r.city))
const PROV_NAMES = new Set(routes.map((r) => r.province))

const mode = computed(() => {
  const q = keyword.value.trim()
  if (!q) return 'all'
  if (ROUTE_WORDS.test(q) || /[·]/.test(q) || /\s/.test(q)) return 'route'
  if (CITY_NAMES.has(q) || PROV_NAMES.has(q)) return 'place'
  // 没带「徒步/路线」但能整串命中路线名，也按路线处理
  if (routes.some((r) => r.name.includes(q))) return 'route'
  return 'unknown'
})

const modeTip = computed(() => {
  if (mode.value === 'all') return ''
  if (mode.value === 'place') return `按地名筛：${keyword.value.trim()}`
  if (mode.value === 'route') return `按路线名筛：${keyword.value.replace(ROUTE_WORDS, '').trim() || keyword.value.trim()}`
  return '没匹配到。搜索只支持「地名」（如 韶关）或「徒步名称 + 路线」（如 武功山徒步、船底顶 罗新线）'
})

function stripRouteWord(q) {
  return q.replace(/徒步|路线|穿越|环线|登顶|古道$/g, '').trim()
}

const levelFilter = ref('all')
const provinceFilter = ref('')
const terrainFilter = ref('')
const sortBy = ref('heat')

const counts = computed(() => ({
  all: routes.length,
  easy: routes.filter((r) => r.level === 'easy').length,
  mid: routes.filter((r) => r.level === 'mid').length,
  hard: routes.filter((r) => r.level === 'hard').length
}))

const list = computed(() => {
  const q = keyword.value.trim()
  let l = routes.filter((r) => {
    if (levelFilter.value !== 'all' && r.level !== levelFilter.value) return false
    if (terrainFilter.value && r.terrain !== terrainFilter.value) return false
    if (provinceFilter.value && r.province !== provinceFilter.value) return false
    if (!q) return true
    if (mode.value === 'place') {
      return matchLoose(haystack(r.city, r.province), q)
    }
    if (mode.value === 'route') {
      const name = stripRouteWord(q)
      return matchLoose(haystack(r.name, r.city), name || q)
    }
    return false
  })
  if (sortBy.value === 'heat') l = l.sort((a, b) => b.heat - a.heat)
  else if (sortBy.value === 'distance') l = l.sort((a, b) => b.distance - a.distance)
  else l = l.sort((a, b) => b.climb - a.climb)
  return l
})

function photo(r) {
  return routePhotoOf(r, terrainTheme)
}

/* ── 灯箱：双击任意位置放大，可左右切换 ── */
const gallery = computed(() =>
  list.value.map((r) => {
    const p = photo(r)
    return {
      src: p ? p.src : '',
      title: r.name,
      caption: `${r.city} · ${r.terrain} · ${r.distance}km · ↑${r.climb}m`,
      id: r.id
    }
  })
)
const lbOpen = ref(false)
const lbIndex = ref(0)
const activeId = ref(null)

/* ── 双击：封面看大图 / 文字进详情 ── */
function openAt(i) {
  if (!gallery.value[i] || !gallery.value[i].src) return
  lbIndex.value = i
  lbOpen.value = true
}

function gotoDetail(id) {
  lbOpen.value = false
  router.push(`/route/${id}`)
}

/**
 * 整卡双击分发：落在封面图 → 看大图；落在文字区 → 进详情。
 * 挂在 <article> 上而不是内层元素，避免 <img> 拖动 / 子元素拦截导致「双击没反应」。
 */
function onDbl(e, i, id) {
  const t = e.target
  if (t && t.closest && t.closest('.cover')) openAt(i)
  else gotoDetail(id)
}

function clearAll() {
  keyword.value = ''
  levelFilter.value = 'all'
  provinceFilter.value = ''
  terrainFilter.value = ''
}

/* 示例词，点一下就填进搜索框 */
const examples = [
  { label: '韶关', text: '韶关' },
  { label: '武功山徒步', text: '武功山徒步' },
  { label: '船底顶 罗新线', text: '船底顶 罗新线' }
]

/* 列表状态记忆：从详情返回时回到刚才那屏 */
const VIEW_KEY = 'routes'
let lastScroll = 0
function trackScroll() {
  lastScroll = window.scrollY || document.documentElement.scrollTop || 0
}
function persist() {
  saveView(VIEW_KEY, {
    keyword: keyword.value,
    level: levelFilter.value,
    province: provinceFilter.value,
    terrain: terrainFilter.value,
    sort: sortBy.value,
    scroll: lastScroll
  })
}

onMounted(async () => {
  window.addEventListener('scroll', trackScroll, { passive: true })
  const st = loadView(VIEW_KEY)
  if (st) {
    keyword.value = st.keyword || ''
    levelFilter.value = st.level || 'all'
    provinceFilter.value = st.province || ''
    terrainFilter.value = st.terrain || ''
    sortBy.value = st.sort || 'heat'
    await nextTick()
    if (st.scroll > 0) {
      setTimeout(() => {
        window.scrollTo({ top: st.scroll, behavior: 'auto' })
        lastScroll = st.scroll
      }, 260)
    }
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
          <input v-model="keyword" type="search" placeholder="输入地名（韶关），或「徒步名称+路线」（武功山徒步）" />
          <button v-if="keyword" class="clear" @click="keyword = ''">×</button>
        </label>
        <div class="quick">
          <button :class="{ on: levelFilter === 'all' }" @click="levelFilter = 'all'">
            全部 <i>{{ counts.all }}</i>
          </button>
          <button :class="{ on: levelFilter === 'easy' }" @click="levelFilter = 'easy'">
            入门 <i>{{ counts.easy }}</i>
          </button>
          <button :class="{ on: levelFilter === 'mid' }" @click="levelFilter = 'mid'">
            进阶 <i>{{ counts.mid }}</i>
          </button>
          <button :class="{ on: levelFilter === 'hard' }" @click="levelFilter = 'hard'">
            顶级 <i>{{ counts.hard }}</i>
          </button>
        </div>
        <select v-model="provinceFilter" class="sel">
          <option value="">全部省份</option>
          <option v-for="p in provinces" :key="p" :value="p">{{ p }}</option>
        </select>
        <select v-model="terrainFilter" class="sel">
          <option value="">全部地形</option>
          <option v-for="t in terrains" :key="t" :value="t">{{ t }}</option>
        </select>
        <select v-model="sortBy" class="sel">
          <option value="heat">按热度</option>
          <option value="distance">按里程</option>
          <option value="climb">按爬升</option>
        </select>
      </div>
      <div class="bar-tip">
        <span v-if="modeTip" class="tip" :class="{ warn: mode === 'unknown' }">{{ modeTip }}</span>
        <span v-else class="tip">搜索只认两种写法：<b>地名</b>（韶关 / 湖南）或 <b>徒步名称 + 路线</b>（武功山徒步）。</span>
        <button v-for="e in examples" :key="e.label" class="eg" @click="keyword = e.text">{{ e.label }}</button>
      </div>
    </div>

    <div class="container">
      <header class="head">
        <p class="eyebrow">TRAILS</p>
        <h1>{{ routes.length }} 条线路，双击图片看大图</h1>
        <p class="lead">
          卡片只放风景实拍，轨迹线不压在图上。<b>单击选中</b>；<b>双击图片看大图</b>（可左右翻看全部路线），
          <b>双击文字区进详情</b>，也可以点「进入详情 →」。
        </p>
      </header>

      <p class="count-line">
        共 <b>{{ list.length }}</b> 条
        <button v-if="keyword || levelFilter !== 'all' || provinceFilter || terrainFilter" class="reset" @click="clearAll">
          清空筛选
        </button>
      </p>

      <div v-if="list.length" class="grid">
        <article
          v-for="(r, i) in list"
          :key="r.id"
          class="card"
          :style="{ '--accent': levelColor[r.level] }"
          :class="{ active: activeId === r.id }"
          @click="activeId = r.id"
          @dblclick="onDbl($event, i, r.id)"
        >
          <figure class="cover" title="双击看大图">
            <img v-if="photo(r)" :src="photo(r).src" :alt="r.name" loading="lazy" />
            <div v-else class="cover-empty"></div>
            <span class="lv">{{ levelLabel[r.level] }}</span>
            <span v-if="!CORE.includes(r.province)" class="out">域外</span>
            <span class="dbl-hint">双击看大图</span>
          </figure>

          <div class="body" :title="`双击进入「${r.name}」详情`">
            <div class="row1">
              <h3>{{ r.name }}</h3>
              <span v-if="mine.countOf(r.id)" class="mine" :title="`我的记录 ${mine.countOf(r.id)} 条`">
                {{ mine.countOf(r.id) }}
              </span>
            </div>
            <p class="meta">{{ r.city }} · {{ r.terrain }} · {{ r.days }}</p>
            <div class="nums">
              <span><b class="mono">{{ r.distance }}</b> km</span>
              <span><b class="mono">↑{{ r.climb }}</b> m</span>
              <span class="season">{{ r.season }}</span>
            </div>
            <button class="enter" @click.stop="gotoDetail(r.id)">进入详情 →</button>
          </div>
        </article>
      </div>

      <p v-else class="empty">
        {{ mode === 'unknown' ? '这个关键词不在支持范围内：试试地名，或「徒步名称 + 路线」' : '没有匹配的路线' }}
      </p>
    </div>

    <LightBox
      :images="gallery"
      :index="lbIndex"
      :open="lbOpen"
      @close="lbOpen = false"
      @update:index="lbIndex = $event"
    >
      <template #actions="{ image }">
        <button class="lb-enter" @click="gotoDetail(image.id)">查看这条路线 →</button>
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
  gap: 10px;
  flex-wrap: wrap;
}

.bar-tip {
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 28px 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.tip {
  font-size: 0.72rem;
  color: var(--gray);
}

.tip b {
  color: var(--forest-dark);
}

.tip.warn {
  color: #9a5a25;
}

.eg {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--forest);
  font-size: 0.7rem;
  padding: 2px 9px;
  border-radius: 999px;
  cursor: pointer;
}

.eg:hover {
  background: var(--forest-soft);
}

.search {
  flex: 1 1 300px;
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

.quick {
  display: flex;
  gap: 2px;
  background: #ece7d9;
  border-radius: 9px;
  padding: 3px;
}

.quick button {
  border: none;
  background: transparent;
  font-size: 0.76rem;
  color: var(--ink-soft);
  padding: 6px 10px;
  border-radius: 7px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.quick button i {
  font-style: normal;
  font-size: 0.66rem;
  color: var(--gray-light);
}

.quick button.on {
  background: #fff;
  color: var(--forest-dark);
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}

.sel {
  height: 34px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  color: var(--ink-soft);
  font-size: 0.76rem;
  padding: 0 8px;
}

.container {
  max-width: 1320px;
  margin: 0 auto;
  padding: 26px 28px 70px;
}

.eyebrow {
  font-family: var(--serif);
  font-size: 0.68rem;
  letter-spacing: 0.26em;
  color: var(--earth);
}

.head h1 {
  font-family: var(--serif);
  font-size: 1.72rem;
  margin: 8px 0 10px;
  color: var(--forest-dark);
}

.lead {
  font-size: 0.85rem;
  line-height: 1.9;
  color: var(--gray);
  max-width: 820px;
}

.count-line {
  margin: 18px 0 12px;
  font-size: 0.78rem;
  color: var(--gray);
  display: flex;
  align-items: center;
  gap: 10px;
}

.count-line b {
  color: var(--forest-dark);
}

.reset {
  border: none;
  background: transparent;
  color: var(--forest);
  font-size: 0.76rem;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: var(--shadow-sm);
  user-select: none;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.card.active {
  border-color: var(--forest-light);
  box-shadow: 0 0 0 2px rgba(45, 90, 61, 0.14), var(--shadow);
}

.card.active {
  border-color: var(--forest-light);
  box-shadow: 0 0 0 2px rgba(45, 90, 61, 0.14), var(--shadow);
}

.cover {
  position: relative;
  margin: 0;
  aspect-ratio: 3 / 2;
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

.lv {
  position: absolute;
  left: 9px;
  top: 9px;
  font-size: 0.66rem;
  padding: 2px 7px;
  border-radius: 5px;
  color: #fff;
  background: var(--accent);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
}

.out {
  position: absolute;
  right: 9px;
  top: 9px;
  font-size: 0.62rem;
  padding: 2px 6px;
  border-radius: 4px;
  color: #5c4410;
  background: rgba(255, 245, 214, 0.94);
}

.dbl-hint {
  position: absolute;
  right: 9px;
  bottom: 9px;
  font-size: 0.66rem;
  padding: 3px 8px;
  border-radius: 999px;
  color: #fff;
  background: rgba(12, 22, 16, 0.5);
  opacity: 0;
  transition: opacity 0.18s;
}

.card:hover .dbl-hint {
  opacity: 1;
}

.body {
  padding: 12px 14px 13px;
}

.row1 {
  display: flex;
  align-items: center;
  gap: 8px;
}

.row1 h3 {
  font-size: 0.95rem;
  color: var(--forest-dark);
  font-weight: 700;
  letter-spacing: -0.01em;
}

.mine {
  margin-left: auto;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--forest-soft);
  color: var(--forest);
  font-size: 0.66rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.meta {
  margin-top: 3px;
  font-size: 0.74rem;
  color: var(--gray);
}

.nums {
  margin-top: 9px;
  display: flex;
  align-items: baseline;
  gap: 12px;
  font-size: 0.7rem;
  color: var(--gray);
}

.nums b {
  font-size: 0.86rem;
  color: var(--ink);
}

.season {
  margin-left: auto;
  color: var(--gray-light);
}

.enter {
  margin-top: 11px;
  width: 100%;
  border: 1px solid var(--line);
  background: #fbf9f3;
  color: var(--forest);
  font-size: 0.76rem;
  padding: 7px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
}

.enter:hover {
  background: var(--forest);
  border-color: var(--forest);
  color: #fff;
}

.empty {
  padding: 60px 0;
  text-align: center;
  color: var(--gray-light);
  font-size: 0.86rem;
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

@media (max-width: 1080px) {
  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
}
</style>
