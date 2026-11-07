<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { routes } from '../data/routes.js'
import { spots } from '../data/spots.js'
import HikeMap from '../components/HikeMap.vue'
import ElevationChart from '../components/ElevationChart.vue'
import RouteGear from '../components/RouteGear.vue'
import TrailConditions from '../components/TrailConditions.vue'
import RouteEcology from '../components/RouteEcology.vue'
import { buildGpx, downloadText } from '../data/geo.js'
import { routePhotoOf } from '../data/photos.js'
import { twobulu, twobuluTrack, xhs, dy, amapNav, tdtWeb } from '../utils/links.js'
import { useMineStore } from '../stores/mine.js'
import { routeGear } from '../data/routeGear.js'
import { routeShots } from '../data/routeShots.js'
import { supplyPlan } from '../data/supply.js'
import LightBox from '../components/LightBox.vue'
import { useAuthStore } from '../stores/auth.js'
import { useFavStore } from '../stores/fav.js'
import { useUiStore } from '../stores/ui.js'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const fav = useFavStore()
const ui = useUiStore()

/**
 * 返回逻辑：不要假设上一页一定是路线列表。
 * 营地库、个人主页、路况页、天气页都能点进路线详情，标签与目标都要跟着来源变。
 * 优先用 history.state.back（能保留筛选与滚动位置），只有拿不到时按 ?from= 兜底。
 */
const FROM_ROUTES = {
  '/': '返回首页',
  '/routes': '返回路线列表',
  '/camps': '返回营地库',
  '/me': '返回个人主页',
  '/reports': '返回路况上报',
  '/safety': '返回安全报备',
  '/weather': '返回点位天气',
  '/community': '返回山友社区',
  '/learn': '返回山野知识库',
  '/spots': '返回景点路书',
  '/gear': '返回装备清单',
  '/gear-lab': '返回我的装备库',
  '/heat': '返回城市热度'
}

const backInfo = computed(() => {
  // 依赖 fullPath：换一条路线时重新判定
  void route.fullPath
  const back = window.history.state && window.history.state.back
  if (typeof back === 'string' && back) {
    const path = back.split('?')[0].split('#')[0]
    if (FROM_ROUTES[path]) return { label: FROM_ROUTES[path], to: path, useHistory: true }
    if (path.startsWith('/route/')) return { label: '返回上一条路线', to: '/routes', useHistory: true }
  }
  const from = String(route.query.from || '').replace(/^\//, '')
  if (from && FROM_ROUTES['/' + from]) {
    return { label: FROM_ROUTES['/' + from], to: '/' + from, useHistory: false }
  }
  return { label: '返回路线列表', to: '/routes', useHistory: false }
})

function goBack() {
  if (backInfo.value.useHistory) router.back()
  else router.push(backInfo.value.to)
}
const mine = useMineStore()

const levelColor = { easy: '#27ae60', mid: '#2980b9', hard: '#c0392b' }

const terrainTheme = {
  高山草甸: 'grass', 森林古道: 'forest', 海岸礁石: 'sea', 山峰野线: 'mountain', 溪谷石阶: 'river',
  溪谷瀑布: 'river', 山脊岩壁: 'mountain', 喀斯特田园: 'terrace', 丹霞地貌: 'danxia', 峡谷: 'peak',
  森林山峰: 'forest', 山峰草甸: 'grass', 原始森林: 'forest', 城市山: 'city', 石阶古道: 'mountain',
  古道: 'town', 峰林溪谷: 'peak', 峰林: 'peak', 山峰栈道: 'peak', 丹霞: 'danxia', 峡谷山峰: 'peak',
  山峰: 'mountain', 茶山: 'terrace', 花岗岩峰林: 'peak', 花岗岩: 'mountain', 高山石海: 'mountain',
  高原雪山: 'mountain'
}

const current = computed(() => routes.find((r) => r.id === Number(route.params.id)))

const isFav = computed(() => (current.value ? fav.has('route', current.value.id) : false))

function toggleFav() {
  if (!current.value) return
  if (!auth.isLogged) {
    auth.openDialog('login')
    ui.toast('登录后就能收藏')
    return
  }
  const on = fav.toggle('route', current.value.id)
  ui.toast(on ? '已收藏，去「我的」看看' : '已取消收藏')
}

const tab = computed(() => String(route.query.tab || 'overview'))
const tabs = [
  { k: 'overview', label: '概览与轨迹' },
  { k: 'shots', label: '四季与光' },
  { k: 'guide', label: '分段路书' },
  { k: 'gear', label: '装备清单' },
  { k: 'supply', label: '补给与风险' },
  { k: 'live', label: '路况与天气' },
  { k: 'eco', label: '山野科普' },
  { k: 'more', label: '更多跳转' }
]
function go(k) {
  router.replace({ path: `/route/${current.value.id}`, query: { tab: k } })
}

const legs = computed(() => {
  const w = current.value.waypoints
  return w.map((p, i) => ({
    ...p,
    gap: i === 0 ? 0 : +(p.km - w[i - 1].km).toFixed(1)
  }))
})
const supplyPoints = computed(() => legs.value.filter((w) => w.sup))
const photoPoints = computed(() => legs.value.filter((w) => w.photo))

/** 搜索词：把「·」换成空格，两步路/小红书按词分词更容易命中 */
const kw = computed(() => (current.value ? current.value.name.replace(/·/g, ' ') : ''))

/** 搜索词：把「·」换成空格，两步路/小红书按词分词更容易命中 */


const photo = computed(() => (current.value ? routePhotoOf(current.value, terrainTheme) : null))
const gearInfo = computed(() => (current.value ? routeGear(current.value) : null))
const plan = computed(() => (current.value ? supplyPlan(current.value) : null))

/* 四季与光：本线封面 + 最近点位的四季 / 晚霞 / 夜色 */
const shots = computed(() => (current.value ? routeShots[current.value.name] || [] : []))
const lbOpen = ref(false)
const lbIndex = ref(0)
function openShot(i) {
  lbIndex.value = i
  lbOpen.value = true
}
const gallery = computed(() => {
  const list = shots.value.map((s) => ({ src: s.src, title: s.title, caption: s.label, note: s.note }))
  if (!list.length && photo.value) {
    list.push({ src: photo.value.src, title: current.value.name, caption: '本线实拍', note: current.value.city })
  }
  return list
})

const spotCities = new Set(spots.map((s) => s.city))
const startPoint = computed(() => current.value.waypoints[0])

function exportGpx() {
  const r = current.value
  downloadText(`${r.name.replace(/[·/\s]/g, '_')}.gpx`, buildGpx(r))
}

/* 我的记录 */
const draftText = ref('')
const draftUrl = ref('')
function addNote() {
  if (!draftText.value.trim() && !draftUrl.value.trim()) return
  mine.add(current.value.id, { text: draftText.value.trim(), url: draftUrl.value.trim() })
  draftText.value = ''
  draftUrl.value = ''
}

watch(
  () => route.params.id,
  () => {
    draftText.value = ''
    draftUrl.value = ''
  }
)
</script>

<template>
  <div v-if="current" class="page">
    <!-- 顶部：图片 + 标题 -->
    <header class="hero" :style="{ '--accent': levelColor[current.level] }" @dblclick="openShot(0)">
      <img v-if="photo" class="hero-img" :src="photo.src" :alt="current.name" />
      <span class="hero-zoom">双击看大图</span>
      <div class="hero-shade"></div>
      <button class="back" @click="goBack" @dblclick.stop>
        <svg viewBox="0 0 24 24" width="14" height="14"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
        {{ backInfo.label }}
      </button>
      <button class="fav" :class="{ on: isFav }" @click.stop="toggleFav" @dblclick.stop>
        <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
          <path
            d="M12 20.3l-1.5-1.4C5.6 14.4 2.8 11.9 2.8 8.8A4.6 4.6 0 017.4 4.2c1.8 0 3.2.9 4.6 2.4 1.4-1.5 2.8-2.4 4.6-2.4a4.6 4.6 0 014.6 4.6c0 3.1-2.8 5.6-7.7 10.1L12 20.3z"
            :fill="isFav ? 'currentColor' : 'none'"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linejoin="round"
          />
        </svg>
        {{ isFav ? '已收藏' : '收藏' }}
      </button>
      <div class="hero-inner">
        <h1>{{ current.name }}</h1>
        <p class="hero-meta">
          {{ current.province }} · {{ current.city }} · {{ current.terrain }} · {{ current.days }} ·
          最佳 {{ current.season }}
        </p>
        <p class="hero-line">
          <span>起</span>{{ current.waypoints[0].name }}
          <i>→</i>
          <span>终</span>{{ current.waypoints[current.waypoints.length - 1].name }}
        </p>
        <div class="hero-nums">
          <div><b class="mono">{{ current.distance }}</b><span>公里</span></div>
          <div><b class="mono">↑{{ current.climb }}</b><span>累计爬升</span></div>
          <div><b class="mono">{{ current.maxEle }}</b><span>最高海拔</span></div>
          <div><b class="mono">{{ current.hours }}</b><span>建议时长</span></div>
        </div>
      </div>
    </header>

    <!-- 常驻分页 + 快捷跳转 -->
    <div class="sticky">
      <div class="sticky-inner">
        <nav class="tabs">
          <button v-for="t in tabs" :key="t.k" :class="{ on: tab === t.k }" @click="go(t.k)">
            {{ t.label }}
          </button>
        </nav>
        <div class="quick-links">
          <a :href="twobulu(kw)" target="_blank" rel="noreferrer" class="q primary">
            两步路轨迹
          </a>
          <a :href="xhs(kw + ' 徒步')" target="_blank" rel="noreferrer" class="q">小红书</a>
          <button class="q" @click="exportGpx">导出 GPX</button>
        </div>
      </div>
    </div>

    <main class="wrap">
      <!-- 概览 -->
      <section v-if="tab === 'overview'" class="pane">
        <div v-if="current.naming" class="naming">
          <div class="naming-head">
            <span class="naming-tag">命名说明</span>
            <b>{{ current.naming.lead }}</b>
          </div>
          <p class="naming-actual">{{ current.naming.actual }}</p>
          <dl class="naming-rows">
            <div v-for="row in current.naming.rows" :key="row[0]">
              <dt>{{ row[0] }}</dt>
              <dd>{{ row[1] }}</dd>
            </div>
          </dl>
          <p class="naming-why">{{ current.naming.why }}</p>
        </div>

        <div class="desc-card">
          <p>{{ current.desc }}</p>
          <div class="badges">
            <span class="badge" :style="{ background: levelColor[current.level] }">难度 {{ current.levelText }}</span>
            <span class="badge ghost">{{ current.loop ? '环线' : '穿越线' }}</span>
            <span class="badge ghost">途经 {{ current.waypoints.length }} 个节点</span>
            <span class="badge ghost">热度 {{ current.heat }}/100</span>
          </div>
        </div>

        <div class="map-row">
          <div class="map-cell">
            <HikeMap
              :track="current.track"
              :waypoints="current.waypoints"
              :center="current.center"
              :color="levelColor[current.level]"
              height="440px"
              :label="current.loop ? '环线轨迹' : '穿越轨迹'"
            />
            <div class="map-act">
              <a class="to-bulu" :href="twobulu(kw)" target="_blank" rel="noreferrer">
                在两步路看「{{ current.name }}」的真实轨迹 →
              </a>
              <span>本页红线是按可见步道追踪的走向示意，不是实测 GPS</span>
            </div>
          </div>
          <aside class="wp-cell">
            <h3>途经点与间距</h3>
            <ul class="wp-list">
              <li v-for="(w, i) in legs" :key="w.name">
                <span class="idx" :class="{ s: i === 0, e: i === legs.length - 1 }">{{ i + 1 }}</span>
                <span class="nm">{{ w.name }}</span>
                <span class="km mono">{{ w.km }}km</span>
                <span v-if="i" class="gap mono">+{{ w.gap }}</span>
              </li>
            </ul>
          </aside>
        </div>

        <ElevationChart :profile="current.profile" :distance="current.distance" :color="levelColor[current.level]" />
      </section>

      <!-- 四季与光 -->
      <section v-else-if="tab === 'shots'" class="pane">
        <div class="block">
          <h2>
            四季与光
            <span class="sub">{{ shots.length }} 张 · 点任意一张看大图，可左右翻</span>
          </h2>
          <p class="shots-note">
            第一张是本线实拍；其余按季节与时段排列，来自同一条山系里最近的覆盖点位（每张都标了来源），
            用来看这条路在春夏秋冬、日落与亮灯之后分别长什么样。
          </p>
          <div class="shots">
            <figure
              v-for="(s, i) in shots"
              :key="s.src"
              class="shot"
              @click="openShot(i)"
            >
              <img :src="s.src" :alt="s.title" loading="lazy" />
              <figcaption>
                <b>{{ s.k }}</b>
                <span>{{ s.label }}</span>
              </figcaption>
            </figure>
          </div>
        </div>
      </section>

      <!-- 路书 -->
      <section v-else-if="tab === 'guide'" class="pane">
        <div class="block">
          <h2>分段路书<span class="sub">共 {{ legs.length }} 个节点 · {{ current.distance }} km · 爬升 {{ current.climb }} m</span></h2>
          <div class="table-wrap">
            <table>
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
                  <td class="mono idx-cell">{{ i + 1 }}</td>
                  <td class="place">
                    {{ w.name }}
                    <em v-if="w.photo" class="tag-photo">机位</em>
                    <em v-if="w.sup" class="tag-sup">可补给</em>
                  </td>
                  <td class="mono">{{ w.km }} km<span v-if="i" class="gap">+{{ w.gap }}</span></td>
                  <td class="mono">{{ w.ele }} m</td>
                  <td class="note">{{ w.note }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="block">
          <h2>怎么到起点</h2>
          <ul class="acc">
            <li><b>高铁</b><span>{{ current.access.hsr }}</span></li>
            <li><b>火车站</b><span>{{ current.access.rail }}</span></li>
            <li><b>公交 / 班车</b><span>{{ current.access.bus }}</span></li>
            <li><b>自驾</b><span>{{ current.access.car }}</span></li>
          </ul>
          <div class="jump-row">
            <a :href="amapNav(startPoint.lat, startPoint.lng, startPoint.name)" target="_blank" rel="noreferrer">
              高德导航到「{{ startPoint.name }}」
            </a>
          </div>
        </div>

        <div class="block">
          <h2>出片机位</h2>
          <ul class="pts">
            <li v-for="w in photoPoints" :key="w.name">
              <b class="mono">{{ w.km }}km</b>
              <div><strong>{{ w.name }}</strong><p>{{ w.photo }}</p></div>
            </li>
            <li v-if="!photoPoints.length" class="muted">沿途以自然景观为主，无固定机位。</li>
          </ul>
        </div>
      </section>

      <!-- 装备 -->
      <section v-else-if="tab === 'gear'" class="pane">
        <div class="block">
          <h2>
            这条线要带什么
            <span class="sub">
              按 {{ current.distance }}km / ↑{{ current.climb }}m / {{ current.days }} 自动配的 ·
              判定为「{{ gearInfo.scene }}」
            </span>
          </h2>
          <RouteGear :route="current" />
        </div>
      </section>

      <!-- 补给与风险 -->
      <section v-else-if="tab === 'supply'" class="pane">
        <!-- 三个关键结论 -->
        <div class="sup-sum">
          <div class="cell">
            <em>可补给点</em>
            <b>{{ plan.waterPoints.length }}<i>处能补水</i></b>
            <span>共 {{ plan.items.filter((x) => x.hasSup).length }} 个点有补给</span>
          </div>
          <div class="cell">
            <em>最后补给点</em>
            <b>{{ plan.lastSup ? plan.lastSup.name : '无' }}</b>
            <span v-if="plan.lastSup">在 {{ plan.lastSup.km }}km 处，之后 {{ plan.gapToEnd }}km 无补给</span>
            <span v-else>全程自带水与食物</span>
          </div>
          <div class="cell">
            <em>起步要背的水</em>
            <b>{{ plan.water.carry }}<i>L</i></b>
            <span>全程约需 {{ plan.water.total }}L · 首次可补水 {{ plan.water.firstAt }}</span>
          </div>
        </div>

        <!-- 补给点明细表 -->
        <div class="block">
          <h2>
            补给点明细
            <span class="sub">水 / 食物 / 住宿 / 信号逐项标出来，别到山上才发现没得买</span>
          </h2>
          <div class="table-wrap">
            <table class="sup-table">
              <thead>
                <tr>
                  <th>地点</th>
                  <th>里程</th>
                  <th>海拔</th>
                  <th>补水</th>
                  <th>食物</th>
                  <th>住宿</th>
                  <th>信号</th>
                  <th>实际情况</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="x in plan.items" :key="x.name">
                  <td class="place">
                    {{ x.name }}
                    <em v-if="x.camp" class="tag-camp">营地</em>
                  </td>
                  <td class="mono">{{ x.km }}km</td>
                  <td class="mono">{{ x.ele }}m</td>
                  <td><span class="ok" :class="{ no: !x.water }">{{ x.water ? '可以' : '没有' }}</span></td>
                  <td><span class="ok" :class="{ no: !x.food }">{{ x.food ? '可以' : '没有' }}</span></td>
                  <td><span class="ok" :class="{ no: !x.bed }">{{ x.bed ? '有' : '没有' }}</span></td>
                  <td class="sig">{{ x.signal }}</td>
                  <td class="note">{{ x.note }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="note-line">
            表里「可以」是按途经点说明推断的，实际营业随季节与天气变化；节假日之外的小卖部常常关着，
            把「可能买到」当成「买不到」来准备更稳。
          </p>
        </div>

        <!-- 水计划 -->
        <div class="block">
          <h2>水怎么带<span class="sub">按 {{ current.hours }} 行程估算，出汗多再加 0.5L</span></h2>
          <div class="water-row">
            <div class="w-item">
              <b>{{ plan.water.total }}L</b>
              <span>全程需要</span>
            </div>
            <div class="w-item">
              <b>{{ plan.water.carry }}L</b>
              <span>起步先背</span>
            </div>
            <div class="w-item">
              <b>{{ plan.waterPoints.length }}</b>
              <span>可补水点</span>
            </div>
            <p class="w-note">
              {{ plan.water.firstAt === '全程无可靠水源'
                ? '这条线没有可靠水源，按全程带走，别指望溪水。'
                : `第一个能补水的点是 ${plan.water.firstAt}；到那里之前按 ${plan.water.carry}L 背，之后每次补满。` }}
              溪水、山泉取用前先看上游有没有村落与农田，最好过滤或煮沸。
            </p>
          </div>
        </div>

        <!-- 撤离方案 -->
        <div class="block">
          <h2>从哪撤、撤多久<span class="sub">里程按回到起点算，含 15% 绕行，速度按 3km/h</span></h2>
          <ul class="exit-list">
            <li v-for="e in plan.exits" :key="e.name">
              <div class="ex-head">
                <b>{{ e.name }}</b>
                <span class="mono">{{ e.km }}km</span>
                <em class="mono">{{ e.back }}km / {{ e.hours }}</em>
              </div>
              <p>{{ e.way }}</p>
              <p class="ex-trans">{{ e.transport }}</p>
            </li>
          </ul>
          <p class="note-line">
            撤离原则：任一节点沿原路或机耕道下撤；<b>天黑前 1 小时还没到下一节点就折返</b>，
            不要赌「再走半小时就到了」。队伍里至少留一个人知道你的路线和预计下撤时间。
          </p>
        </div>

        <!-- 应急信息 -->
        <div class="block">
          <h2>出事怎么办</h2>
          <div class="emerg">
            <div class="em-item">
              <b>报警 / 急救</b>
              <p>110 · 120 · 119（森林火警）。接通后先说「在哪个山、哪个方向、几个人、有没有伤」，再说细节。</p>
            </div>
            <div class="em-item">
              <b>求救信号</b>
              <p>哨子三短三长三短（SOS）；夜间用手电同样节奏。声音与光比喊叫省力，也传得更远。</p>
            </div>
            <div class="em-item">
              <b>失温 / 中暑</b>
              <p>失温先换干衣、加保温毯、喝热的，别搓手脚；中暑移到阴凉处、解开衣物、补电解质，意识不清立即求救。</p>
            </div>
            <div class="em-item">
              <b>就近就医</b>
              <p>{{ current.city }}人民医院 / 沿途镇卫生院；山区到县城通常 1–2 小时车程，别把小伤拖成大伤。</p>
            </div>
          </div>
          <p class="note-line">
            信号情况：{{ plan.signalNote }}。景区值班与救援电话以入口公告牌为准，出发前拍一张存手机里。
          </p>
        </div>

        <div class="block">
          <h2>风险提示</h2>
          <div class="chips">
            <span v-for="k in current.risk" :key="k">{{ k }}</span>
          </div>
          <p class="tip">{{ current.tips }}</p>
          <p class="note-line">
            本页轨迹、里程、用时、补给与撤离时间为整理估算，出行前请以景区公告、当日天气与实地路况为准；
            山区无信号路段建议带卫星通讯设备。
          </p>
        </div>
      </section>

      <!-- 路况与天气 -->
      <section v-else-if="tab === 'live'" class="pane">
        <div class="block">
          <h2>
            路上现在什么样
            <span class="sub">山友上报的路况 + 起点天气，出发前 1 分钟就能看完</span>
          </h2>
          <TrailConditions :route="current" />
        </div>
      </section>

      <!-- 山野科普 -->
      <section v-else-if="tab === 'eco'" class="pane">
        <div class="block">
          <h2>
            这条线上有什么
            <span class="sub">地形 · 植被 · 动物 · 注意事项，按当地实际情况整理</span>
          </h2>
          <RouteEcology :route="current" />
        </div>
      </section>

      <!-- 更多跳转 + 我的记录 -->
      <section v-else class="pane">
        <div class="block">
          <h2>去别的地方看这条线</h2>
          <div class="link-grid">
            <a class="link-card" :href="twobulu(kw)" target="_blank" rel="noreferrer">
              <b>两步路 · 搜索全部</b>
              <span>搜「{{ current.name }}」，能看到别人上传的 GPX 轨迹、海拔与用时</span>
            </a>
            <a class="link-card" :href="twobuluTrack(kw)" target="_blank" rel="noreferrer">
              <b>两步路 · 只看轨迹</b>
              <span>直接进轨迹库，筛选同线路的轨迹文件与卫星叠加</span>
            </a>
            <a class="link-card" :href="xhs(kw + ' 徒步')" target="_blank" rel="noreferrer">
              <b>小红书 · 实拍与路况</b>
              <span>近期的路况、封山、蚂蟥、草况，看笔记比看攻略准</span>
            </a>
            <a class="link-card" :href="dy(kw + ' 徒步')" target="_blank" rel="noreferrer">
              <b>抖音 · 视频</b>
              <span>视频能看出碎石坡有多陡、灌木有多密</span>
            </a>
            <a class="link-card" :href="tdtWeb(startPoint.lat, startPoint.lng)" target="_blank" rel="noreferrer">
              <b>天地图 · 卫星看地形</b>
              <span>在网页版卫星图上量一下山脊走向和沟谷位置</span>
            </a>
            <a class="link-card" :href="amapNav(startPoint.lat, startPoint.lng, startPoint.name)" target="_blank" rel="noreferrer">
              <b>高德 · 导航到起点</b>
              <span>{{ startPoint.name }}（{{ startPoint.lat }}, {{ startPoint.lng }}）</span>
            </a>
            <button class="link-card as-btn" @click="exportGpx">
              <b>导出 GPX</b>
              <span>导到手表 / 两步路 / OruxMaps，本页轨迹为示意线</span>
            </button>
            <router-link
              v-if="spotCities.has(current.city)"
              class="link-card"
              :to="{ path: '/spots', query: { city: current.city } }"
            >
              <b>{{ current.city }} 的景点路书</b>
              <span>同城的日落、四季、机位与吃什么</span>
            </router-link>
          </div>
        </div>

        <div class="block">
          <h2>
            我的这条线
            <span class="sub">自己记的笔记与链接，只存在本机浏览器</span>
          </h2>
          <div class="note-form">
            <input v-model="draftText" placeholder="写点什么：几点出发、在哪停车、谁去过、下次注意什么" />
            <input v-model="draftUrl" placeholder="附一个链接（可选）：轨迹、相册、笔记都行" />
            <button @click="addNote">添加</button>
          </div>
          <ul v-if="mine.of(current.id).length" class="note-list">
            <li v-for="n in mine.of(current.id)" :key="n.id">
              <div>
                <p>{{ n.text || '（只有链接）' }}</p>
                <a v-if="n.url" :href="n.url" target="_blank" rel="noreferrer">{{ n.url }}</a>
              </div>
              <span class="at mono">{{ n.at }}</span>
              <button class="del" @click="mine.remove(current.id, n.id)">删除</button>
            </li>
          </ul>
          <p v-else class="muted">还没有记录。出发前写一句，回来补一条，比收藏夹靠谱。</p>
        </div>
      </section>
    </main>
  </div>

  <div v-else class="missing">
    <p>没有这条路线</p>
    <button @click="router.push('/routes')">回到路线列表</button>
  </div>

  <LightBox
    :images="gallery"
    :index="lbIndex"
    :open="lbOpen"
    @close="lbOpen = false"
    @update:index="lbIndex = $event"
  >
    <template #actions="{ image }">
      <a class="lb-link" :href="twobulu(kw)" target="_blank" rel="noreferrer">去两步路看真实轨迹</a>
      <span class="lb-src">{{ image.note }}</span>
    </template>
  </LightBox>
</template>

<style scoped>
.page {
  padding-top: var(--nav-h);
  padding-bottom: 70px;
}

/* hero */
.hero {
  position: relative;
  height: clamp(240px, 34vh, 380px);
  overflow: hidden;
  background: #22392c;
}

.hero-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.hero-shade {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(to top, rgba(10, 18, 13, 0.85) 0%, rgba(10, 18, 13, 0.25) 55%, rgba(10, 18, 13, 0.35) 100%);
}

/* 大图可双击：指示只在鼠标移到图上时出现，平时不挡画面 */
.hero-img {
  cursor: zoom-in;
}

.hero-inner {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 28px 22px;
  color: #fff;
}

.back {
  position: absolute;
  left: 22px;
  top: 18px;
  z-index: 3;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.92);
  color: #24352a;
  border: none;
  font-size: 0.75rem;
  padding: 7px 13px;
  border-radius: 999px;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
}

.back:hover {
  background: #fff;
}

/* 收藏：与返回按钮同层，右侧对齐 */
.fav {
  position: absolute;
  right: 22px;
  top: 18px;
  z-index: 3;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 32px;
  padding: 0 13px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #24352a;
  font-size: 0.75rem;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
  transition: background 0.18s, color 0.18s, transform 0.18s;
}

.fav:hover {
  background: #fff;
  transform: translateY(-1px);
}

.fav.on {
  background: #c0392b;
  color: #fff;
}

.hero h1 {
  font-family: var(--serif);
  font-size: 1.9rem;
  letter-spacing: -0.01em;
}

.hero-meta {
  margin-top: 6px;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.78);
}

/* 实际起终点：写死在标题下，避免只看名字误解 */
.hero-line {
  margin-top: 7px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.92);
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  padding: 3px 12px;
}

.hero-line span {
  font-size: 0.66rem;
  font-weight: 700;
  color: #e9dcc0;
  letter-spacing: 0.06em;
}

.hero-line i {
  font-style: normal;
  color: rgba(255, 255, 255, 0.5);
}

.hero-zoom {
  position: absolute;
  right: 22px;
  bottom: 22px;
  z-index: 2;
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.9);
  background: rgba(12, 22, 16, 0.45);
  padding: 3px 9px;
  border-radius: 999px;
  pointer-events: none;
  opacity: 0;
  transform: translateY(4px);
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.hero:hover .hero-zoom {
  opacity: 1;
  transform: none;
}

.hero-nums {
  display: flex;
  gap: 26px;
  margin-top: 14px;
}

.hero-nums div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.hero-nums b {
  font-size: 1.18rem;
  font-weight: 700;
}

.hero-nums span {
  font-size: 0.66rem;
  color: rgba(255, 255, 255, 0.66);
}

/* sticky tabs */
.sticky {
  position: sticky;
  top: var(--nav-h);
  z-index: 40;
  background: rgba(250, 248, 242, 0.97);
  backdrop-filter: saturate(180%) blur(12px);
  border-bottom: 1px solid var(--line);
}

.sticky-inner {
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 28px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.tabs {
  display: flex;
  gap: 2px;
  overflow-x: auto;
}

.tabs button {
  border: none;
  background: transparent;
  padding: 13px 10px;
  font-size: 0.8rem;
  color: var(--gray);
  border-bottom: 2px solid transparent;
  cursor: pointer;
  white-space: nowrap;
}

.tabs button.on {
  color: var(--forest);
  border-bottom-color: var(--forest);
  font-weight: 600;
}

.quick-links {
  margin-left: auto;
  display: flex;
  gap: 7px;
}

.q {
  font-size: 0.74rem;
  padding: 6px 12px;
  border-radius: 7px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink-soft);
  cursor: pointer;
  text-decoration: none;
}

.q.primary {
  background: var(--forest);
  border-color: var(--forest);
  color: #fff;
}

.wrap {
  max-width: 1320px;
  margin: 0 auto;
  padding: 20px 28px 0;
}

.pane {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── 命名说明：名字与实际起终点不一致时的勘误卡 ── */
.naming {
  background: #fdf8ec;
  border: 1px solid #ecdcb6;
  border-left: 3px solid #c99a2e;
  border-radius: 12px;
  padding: 14px 18px 15px;
}

.naming-head {
  display: flex;
  align-items: baseline;
  gap: 9px;
  flex-wrap: wrap;
}

.naming-tag {
  font-size: 0.66rem;
  font-weight: 700;
  color: #7a5b12;
  background: #f2e3b8;
  border-radius: 999px;
  padding: 2px 9px;
  letter-spacing: 0.04em;
}

.naming-head b {
  font-size: 0.9rem;
  color: #4a3a12;
  font-weight: 700;
}

.naming-actual {
  margin-top: 9px;
  font-size: 0.84rem;
  font-weight: 600;
  color: var(--forest-dark);
}

.naming-rows {
  margin-top: 10px;
  display: grid;
  gap: 6px;
}

.naming-rows > div {
  display: grid;
  grid-template-columns: 148px minmax(0, 1fr);
  gap: 10px;
  font-size: 0.79rem;
  line-height: 1.7;
}

.naming-rows dt {
  color: #7a5b12;
  font-weight: 600;
}

.naming-rows dd {
  margin: 0;
  color: var(--ink-soft);
}

.naming-why {
  margin-top: 11px;
  padding-top: 10px;
  border-top: 1px dashed #e3d2a8;
  font-size: 0.78rem;
  line-height: 1.8;
  color: #6b5a33;
}

@media (max-width: 680px) {
  .naming-rows > div {
    grid-template-columns: minmax(0, 1fr);
    gap: 2px;
  }
}

.desc-card,
.block {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 13px;
  padding: 16px 18px;
  box-shadow: var(--shadow-sm);
}

.desc-card p {
  font-size: 0.87rem;
  line-height: 1.95;
  color: var(--ink-soft);
}

.badges {
  display: flex;
  gap: 7px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.badge {
  font-size: 0.7rem;
  padding: 3px 9px;
  border-radius: 5px;
  color: #fff;
}

.badge.ghost {
  background: #f2efe6;
  color: var(--ink-soft);
}

.map-row {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(0, 1fr);
  gap: 16px;
}

.map-act {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 9px;
  flex-wrap: wrap;
}

.to-bulu {
  font-size: 0.76rem;
  padding: 7px 13px;
  border-radius: 8px;
  background: var(--forest);
  color: #fff;
  text-decoration: none;
}

.to-bulu:hover {
  background: var(--forest-dark);
}

.map-act span {
  font-size: 0.71rem;
  color: var(--gray);
}

.wp-cell {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 13px;
  padding: 14px 16px;
  box-shadow: var(--shadow-sm);
}

.wp-cell h3 {
  font-size: 0.82rem;
  color: var(--forest-dark);
  margin-bottom: 8px;
}

.wp-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.wp-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.76rem;
  padding: 5px 0;
  border-top: 1px dashed #f0ece1;
}

.wp-list li:first-child {
  border-top: none;
}

.idx {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #eef2ee;
  color: var(--forest);
  font-size: 0.66rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.idx.s {
  background: var(--forest);
  color: #fff;
}

.idx.e {
  background: var(--earth-light);
  color: #fff;
}

.nm {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.km {
  color: var(--gray);
  font-size: 0.7rem;
}

.gap {
  color: var(--earth);
  font-size: 0.66rem;
  margin-left: 4px;
}

/* blocks */
.block h2 {
  font-family: var(--serif);
  font-size: 1.02rem;
  color: var(--forest-dark);
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.block h2 .sub {
  font-family: inherit;
  font-size: 0.72rem;
  font-weight: 400;
  color: var(--gray);
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
}

th {
  text-align: left;
  font-weight: 600;
  color: var(--gray);
  font-size: 0.7rem;
  padding: 8px 10px;
  border-bottom: 1px solid var(--line);
  white-space: nowrap;
}

td {
  padding: 9px 10px;
  border-bottom: 1px solid #f4f1e8;
  vertical-align: top;
  color: var(--ink-soft);
}

.idx-cell {
  color: var(--gray-light);
}

.place {
  color: var(--ink);
  font-weight: 500;
  white-space: nowrap;
}

.tag-photo,
.tag-sup {
  font-style: normal;
  font-size: 0.6rem;
  padding: 1px 5px;
  border-radius: 3px;
  margin-left: 5px;
}

.tag-photo {
  color: var(--earth);
  background: #fbf3e0;
}

.tag-sup {
  color: var(--forest);
  background: var(--forest-soft);
}

.note {
  line-height: 1.7;
  min-width: 260px;
}

.acc,
.sup,
.pts {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.acc li,
.sup li,
.pts li {
  display: flex;
  gap: 12px;
  font-size: 0.79rem;
  line-height: 1.7;
  color: var(--ink-soft);
}

.acc b {
  width: 84px;
  flex-shrink: 0;
  color: var(--forest);
  font-size: 0.74rem;
}

.sup b,
.pts b {
  width: 58px;
  flex-shrink: 0;
  color: var(--gray);
  font-size: 0.72rem;
}

.sup strong,
.pts strong {
  color: var(--ink);
  font-size: 0.8rem;
}

.sup p,
.pts p {
  margin-top: 2px;
}

.jump-row {
  margin-top: 12px;
}

.jump-row a {
  font-size: 0.76rem;
  color: var(--forest);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chips span {
  font-size: 0.72rem;
  padding: 4px 10px;
  border-radius: 6px;
  background: #fdf3ee;
  color: #8a4a2a;
  border: 1px solid #f0dbd0;
}

.tip {
  margin-top: 12px;
  font-size: 0.8rem;
  line-height: 1.85;
  color: var(--ink-soft);
  background: #f8f5ec;
  border-radius: 9px;
  padding: 12px 14px;
}

.note-line {
  margin-top: 10px;
  font-size: 0.72rem;
  line-height: 1.75;
  color: var(--gray);
}

/* 更多跳转 */
.link-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.link-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fcfbf6;
  text-decoration: none;
  transition: all 0.15s;
  text-align: left;
  cursor: pointer;
}

.link-card:hover {
  border-color: var(--forest-light);
  background: var(--forest-soft);
}

.link-card b {
  font-size: 0.82rem;
  color: var(--forest-dark);
}

.link-card span {
  font-size: 0.72rem;
  line-height: 1.65;
  color: var(--gray);
}

.link-card.as-btn {
  font: inherit;
}

/* 我的记录 */
.note-form {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr) auto;
  gap: 8px;
}

.note-form input {
  height: 36px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0 11px;
  font-size: 0.78rem;
  outline: none;
  background: #fcfbf7;
}

.note-form input:focus {
  border-color: var(--forest-light);
  background: #fff;
}

.note-form button {
  padding: 0 16px;
  border-radius: 8px;
  border: 1px solid var(--forest);
  background: var(--forest);
  color: #fff;
  font-size: 0.78rem;
  cursor: pointer;
}

.note-list {
  list-style: none;
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.note-list li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: #fbf9f2;
  border-radius: 9px;
  font-size: 0.78rem;
}

.note-list p {
  color: var(--ink-soft);
  line-height: 1.65;
}

.note-list a {
  color: var(--forest);
  font-size: 0.72rem;
  word-break: break-all;
}

.at {
  margin-left: auto;
  font-size: 0.68rem;
  color: var(--gray-light);
  flex-shrink: 0;
}

.del {
  border: none;
  background: transparent;
  color: var(--gray-light);
  font-size: 0.7rem;
  cursor: pointer;
}

.muted {
  color: var(--gray-light);
  font-size: 0.78rem;
  margin-top: 8px;
}

/* 补给与撤离 */
.sup-sum {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
}

.sup-sum .cell {
  background: #fbf9f3;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.sup-sum em {
  font-style: normal;
  font-size: 0.68rem;
  color: var(--gray);
}

.sup-sum b {
  font-size: 1.02rem;
  color: var(--forest-dark);
}

.sup-sum b i {
  font-style: normal;
  font-size: 0.66rem;
  color: var(--gray);
  margin-left: 3px;
}

.sup-sum span {
  font-size: 0.68rem;
  color: var(--gray-light);
  line-height: 1.5;
}

.sup-table {
  font-size: 0.76rem;
}

.sup-table th {
  white-space: nowrap;
}

.sup-table td {
  vertical-align: middle;
}

.sup-table .place {
  white-space: nowrap;
  font-weight: 500;
  color: var(--ink);
}

.tag-camp {
  font-style: normal;
  font-size: 0.6rem;
  padding: 1px 5px;
  border-radius: 3px;
  margin-left: 5px;
  color: var(--forest);
  background: var(--forest-soft);
}

.ok {
  font-size: 0.68rem;
  padding: 1px 7px;
  border-radius: 999px;
  background: #eaf4ee;
  color: var(--forest);
  white-space: nowrap;
}

.ok.no {
  background: #f4f1ea;
  color: var(--gray-light);
}

.sig {
  white-space: nowrap;
  font-size: 0.72rem;
  color: var(--gray);
}

.water-row {
  display: grid;
  grid-template-columns: repeat(3, 96px) minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.w-item {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 9px 11px;
  text-align: center;
  background: #fbf9f3;
}

.w-item b {
  display: block;
  font-size: 1.1rem;
  color: var(--forest-dark);
}

.w-item span {
  font-size: 0.66rem;
  color: var(--gray);
}

.w-note {
  font-size: 0.76rem;
  line-height: 1.8;
  color: var(--ink-soft);
}

.exit-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.exit-list li {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px 12px;
  background: #fcfbf7;
}

.ex-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.ex-head b {
  font-size: 0.82rem;
  color: var(--forest-dark);
}

.ex-head span {
  font-size: 0.7rem;
  color: var(--gray-light);
}

.ex-head em {
  margin-left: auto;
  font-style: normal;
  font-size: 0.74rem;
  color: var(--earth);
}

.exit-list p {
  font-size: 0.75rem;
  line-height: 1.7;
  color: var(--ink-soft);
  margin-top: 4px;
}

.ex-trans {
  color: var(--gray) !important;
}

.emerg {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.em-item {
  border-left: 3px solid var(--earth-light);
  background: #fdfaf3;
  border-radius: 0 9px 9px 0;
  padding: 9px 12px;
}

.em-item b {
  font-size: 0.8rem;
  color: #7a4a20;
}

.em-item p {
  margin-top: 4px;
  font-size: 0.75rem;
  line-height: 1.75;
  color: var(--ink-soft);
}

@media (max-width: 1080px) {
  .water-row {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .w-note {
    grid-column: 1 / -1;
  }
}

@media (max-width: 680px) {
  .sup-sum,
  .emerg {
    grid-template-columns: minmax(0, 1fr);
  }
}

/* 四季与光 */
.shots-note {
  font-size: 0.76rem;
  line-height: 1.8;
  color: var(--gray);
  margin: -4px 0 12px;
}

.shots {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 11px;
}

.shot {
  margin: 0;
  border-radius: 10px;
  overflow: hidden;
  background: #e6ebe4;
  cursor: zoom-in;
  border: 1px solid var(--line);
}

.shot img {
  width: 100%;
  aspect-ratio: 3 / 2;
  object-fit: cover;
  display: block;
  transition: transform 0.35s ease;
}

.shot:hover img {
  transform: scale(1.04);
}

.shot figcaption {
  padding: 7px 9px 8px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.shot figcaption b {
  font-size: 0.72rem;
  color: var(--forest-dark);
}

.shot figcaption span {
  font-size: 0.66rem;
  color: var(--gray-light);
  line-height: 1.5;
}

.lb-link {
  font-size: 0.78rem;
  padding: 7px 14px;
  border-radius: 999px;
  background: var(--forest);
  color: #fff;
  text-decoration: none;
}

.lb-src {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.6);
}

.missing {
  padding: calc(var(--nav-h) + 80px) 28px;
  text-align: center;
  color: var(--gray);
}

.missing button {
  margin-top: 14px;
  padding: 8px 18px;
  border-radius: 8px;
  border: 1px solid var(--forest);
  background: var(--forest);
  color: #fff;
  cursor: pointer;
}

@media (max-width: 1080px) {
  .map-row,
  .link-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .shots {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .shots {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .note-form {
    grid-template-columns: minmax(0, 1fr);
  }
  .note-form button {
    height: 36px;
  }
}

@media (max-width: 680px) {
  .shots {
    grid-template-columns: minmax(0, 1fr);
  }
  .hero-inner,
  .sticky-inner,
  .wrap {
    padding-left: 16px;
    padding-right: 16px;
  }
  .hero h1 {
    font-size: 1.4rem;
  }
  .hero-nums {
    gap: 16px;
  }
  .sticky-inner {
    flex-direction: column;
    align-items: stretch;
  }
  .quick-links {
    margin-left: 0;
    padding-bottom: 8px;
  }
}
</style>
