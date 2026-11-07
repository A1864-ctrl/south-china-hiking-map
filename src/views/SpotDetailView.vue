<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { spots } from '../data/spots.js'
import { getSpotExtra, xhsUrl, dyUrl } from '../data/spotExtra.js'
import { getGuide } from '../data/spotGuide.js'
import { cityFoodShops } from '../data/food.js'
import { spotPhotos, seasonPhotosOf, lightPhotoOf, nearbyMood } from '../data/photos.js'
import { sunInfo, LIGHT_TIP } from '../data/sun.js'
import { xhs, dy, amapNav } from '../utils/links.js'
import LightBox from '../components/LightBox.vue'
import { useAuthStore } from '../stores/auth.js'
import { useFavStore } from '../stores/fav.js'
import { useUiStore } from '../stores/ui.js'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const fav = useFavStore()
const ui = useUiStore()

const isFav = computed(() => (spot.value ? fav.has('spot', spot.value.name) : false))

function toggleFav() {
  if (!spot.value) return
  if (!auth.isLogged) {
    auth.openDialog('login')
    ui.toast('登录后就能收藏')
    return
  }
  const on = fav.toggle('spot', spot.value.name)
  ui.toast(on ? '已收藏，去「我的」看看' : '已取消收藏')
}

/** 返回列表：是从景点列表点进来的就后退（保留筛选与位置），否则直接进列表 */
function goBack() {
  const back = window.history.state && window.history.state.back
  if (typeof back === 'string' && back.startsWith('/spots')) router.back()
  else router.push('/spots')
}

const name = computed(() => decodeURIComponent(String(route.params.name || '')))
const spot = computed(() => spots.find((s) => s.name === name.value) || null)
const extra = computed(() => (spot.value ? getSpotExtra(spot.value) : null))
const guide = computed(() => (spot.value ? getGuide(spot.value.name, spot.value.city) : null))
const photos = computed(() => (spot.value ? spotPhotos(spot.value.name) : []))
const sun = computed(() => (spot.value ? sunInfo(spot.value.lat, spot.value.lng) : null))
const tip = computed(() => LIGHT_TIP[extra.value?.theme] || LIGHT_TIP.mountain)

const seasons = computed(() => {
  if (!spot.value) return []
  const map = Object.fromEntries(seasonPhotosOf(spot.value.name).map((x) => [x.k, x.src]))
  return (extra.value?.seasons || []).map((s) => ({ ...s, src: map[s.k] || '' }))
})

const sunsetPhoto = computed(() => {
  if (!spot.value) return null
  return lightPhotoOf(spot.value.name, 'sunset', spot.value.city) || nearbyMood(spot.value, 'sunset')
})
const nightPhoto = computed(() => {
  if (!spot.value) return null
  const sun0 = sunsetPhoto.value
  return lightPhotoOf(spot.value.name, 'night', spot.value.city) || nearbyMood(spot.value, 'night', sun0 ? [sun0.name] : [])
})

/** 同城其它点位：路由「路书」可以互相跳 */
const nearby = computed(() => {
  if (!spot.value) return []
  return spots.filter((s) => s.city === spot.value.city && s.name !== spot.value.name).slice(0, 6)
})

const tabs = [
  { k: 'overview', label: '概览' },
  { k: 'season', label: '四季' },
  { k: 'light', label: '日落与光' },
  { k: 'shot', label: '机位与走法' },
  { k: 'eat', label: '吃什么' },
  { k: 'go', label: '怎么去' }
]
const tab = computed(() => String(route.query.tab || 'overview'))
function go(k) {
  router.replace({ path: `/spot/${encodeURIComponent(name.value)}`, query: { tab: k } })
}

/* 灯箱：把这个点位的所有图集中起来 */
const gallery = computed(() => {
  const g = []
  photos.value.forEach((p) => g.push({ src: p.src, title: spot.value.name, caption: '点位实拍' }))
  seasons.value.forEach((s) => s.src && g.push({ src: s.src, title: `${spot.value.name} · ${s.k}`, caption: '四季实拍' }))
  if (sunsetPhoto.value) g.push({ src: sunsetPhoto.value.src, title: `${spot.value.name} · 晚霞`, caption: '黄昏实拍' })
  if (nightPhoto.value) g.push({ src: nightPhoto.value.src, title: `${spot.value.name} · 夜色`, caption: '夜间实拍' })
  return g
})
const lbOpen = ref(false)
const lbIndex = ref(0)
function openAt(i) {
  lbIndex.value = i
  lbOpen.value = true
}

/* 光线罗盘：把太阳落点画成一个方向盘 */
const compass = computed(() => {
  if (!sun.value) return null
  const deg = sun.value.az.deg
  return { deg, rad: ((deg - 90) * Math.PI) / 180, label: sun.value.az.label }
})

const verdict = (n) => (n >= 5 ? '最值得' : n === 4 ? '值得' : n === 3 ? '一般' : '不建议')
const shops = computed(() => (spot.value ? cityFoodShops[spot.value.city] || [] : []))
</script>

<template>
  <div v-if="spot" class="page">
    <!-- 顶部：大图 + 标题 -->
    <header class="hero" @dblclick="openAt(0)">
      <img v-if="photos.length" class="hero-img" :src="photos[0].src" :alt="spot.name" />
      <div class="hero-shade"></div>
      <button class="back" @click="goBack" @dblclick.stop>
        <svg viewBox="0 0 24 24" width="14" height="14"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
        返回景点列表
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
        <p class="kicker">{{ spot.city }} · {{ spot.district }}</p>
        <h1>{{ spot.name }}</h1>
        <p class="hero-meta">{{ spot.type }} · {{ spot.ticket }} · 建议 {{ spot.hours }}</p>
        <div class="hero-tags">
          <span v-for="t in spot.tags" :key="t">{{ t }}</span>
        </div>
      </div>
      <span class="zoom-hint">双击看大图</span>
    </header>

    <!-- 常驻分页 -->
    <div class="sticky">
      <div class="sticky-inner">
        <nav class="tabs">
          <button v-for="t in tabs" :key="t.k" :class="{ on: tab === t.k }" @click="go(t.k)">{{ t.label }}</button>
        </nav>
        <div class="quick-links">
          <a :href="xhs(spot.name + ' 拍照')" target="_blank" rel="noreferrer" class="q">小红书实拍</a>
          <a :href="amapNav(spot.lat, spot.lng, spot.name)" target="_blank" rel="noreferrer" class="q primary">导航过去</a>
        </div>
      </div>
    </div>

    <main class="wrap">
      <!-- 概览 -->
      <section v-if="tab === 'overview'" class="pane">
        <div class="block">
          <p class="reason">{{ spot.reason }}</p>
          <div class="badges">
            <span class="badge">热度 {{ spot.heat }}</span>
            <span class="badge ghost">{{ spot.city }} · {{ spot.district }}</span>
            <span class="badge ghost">{{ spot.type }}</span>
            <span class="badge ghost">{{ spot.ticket }}</span>
          </div>
        </div>

        <!-- 创新：当日光线时间轴 + 罗盘 -->
        <div v-if="sun" class="light-board">
          <div class="timeline">
            <h3>今天的这条光线</h3>
            <div class="tl">
              <div class="tl-item">
                <b>{{ sun.goldenStart }}</b>
                <span>暖光开始</span>
                <em>光线压低，山体开始出侧面阴影</em>
              </div>
              <div class="tl-item key">
                <b>{{ sun.sunset }}</b>
                <span>日落</span>
                <em>太阳落在 {{ sun.az.label }} {{ sun.az.deg }}°</em>
              </div>
              <div class="tl-item">
                <b>{{ sun.blue }}</b>
                <span>蓝调</span>
                <em>天光还在、灯已亮，最容易出片</em>
              </div>
            </div>
          </div>

          <div v-if="compass" class="compass">
            <svg viewBox="0 0 200 200" width="100%" height="100%">
              <circle cx="100" cy="100" r="82" fill="none" stroke="#e3ddcd" stroke-width="1.5" />
              <circle cx="100" cy="100" r="58" fill="none" stroke="#efe9da" stroke-width="1" />
              <line x1="100" y1="18" x2="100" y2="182" stroke="#e3ddcd" stroke-width="1" />
              <line x1="18" y1="100" x2="182" y2="100" stroke="#e3ddcd" stroke-width="1" />
              <text x="100" y="14" text-anchor="middle" font-size="10" fill="#9ca3af">北</text>
              <text x="186" y="103" text-anchor="middle" font-size="10" fill="#9ca3af">东</text>
              <text x="100" y="194" text-anchor="middle" font-size="10" fill="#9ca3af">南</text>
              <text x="14" y="103" text-anchor="middle" font-size="10" fill="#9ca3af">西</text>
              <line
                x1="100"
                y1="100"
                :x2="100 + Math.cos(compass.rad) * 74"
                :y2="100 + Math.sin(compass.rad) * 74"
                stroke="#d97706"
                stroke-width="3"
                stroke-linecap="round"
              />
              <circle :cx="100 + Math.cos(compass.rad) * 74" :cy="100 + Math.sin(compass.rad) * 74" r="6" fill="#d97706" />
              <circle cx="100" cy="100" r="4" fill="#2d5a3d" />
            </svg>
            <p>太阳落点 <b>{{ compass.deg }}°</b> · {{ compass.label }}</p>
          </div>
        </div>

        <div class="block">
          <h2>同城还能去哪<span class="sub">同一座城市里可以串成一天的点位</span></h2>
          <div class="nearby">
            <button v-for="n in nearby" :key="n.name" class="nb" @click="router.push(`/spot/${encodeURIComponent(n.name)}`)">
              <b>{{ n.name }}</b>
              <span>{{ n.type }} · 热度 {{ n.heat }}</span>
            </button>
          </div>
        </div>
      </section>

      <!-- 四季 -->
      <section v-else-if="tab === 'season'" class="pane">
        <div class="block">
          <h2>四季表现<span class="sub">按月份、适合度和现场观感</span></h2>
          <div class="seasons">
            <figure
              v-for="(s, i) in seasons"
              :key="s.k"
              class="season"
              @click="photos.length + i < gallery.length && openAt(photos.length + i)"
            >
              <img v-if="s.src" :src="s.src" :alt="s.k" loading="lazy" />
              <div v-else class="season-empty">暂无该季实拍</div>
              <figcaption>
                <div class="sh">
                  <b>{{ s.k }}</b>
                  <span>{{ s.m }}</span>
                  <em :class="'v' + s.s">{{ verdict(s.s) }}</em>
                </div>
                <div class="bars"><i v-for="n in 5" :key="n" :class="{ f: n <= s.s }"></i></div>
                <p>{{ s.t }}</p>
              </figcaption>
            </figure>
          </div>
          <p class="tip">{{ extra.tip }}</p>
        </div>
      </section>

      <!-- 日落与光 -->
      <section v-else-if="tab === 'light'" class="pane">
        <div v-if="sun" class="sun-bar">
          <div class="sun-item"><b>{{ sun.sunset }}</b><span>今日日落</span></div>
          <div class="sun-item"><b>{{ sun.goldenStart }}</b><span>暖光开始</span></div>
          <div class="sun-item"><b>{{ sun.az.deg }}°</b><span>太阳落点 · {{ sun.az.label }}</span></div>
          <div class="sun-item"><b>{{ sun.blue }}</b><span>蓝调时刻</span></div>
        </div>

        <div class="two">
          <div class="block">
            <figure v-if="sunsetPhoto" class="big" @click="openAt(photos.length + seasons.length)">
              <img :src="sunsetPhoto.src" alt="晚霞" loading="lazy" />
              <figcaption>{{ sunsetPhoto.own ? '本点位实拍' : '同城实拍' }} · {{ sunsetPhoto.name }}</figcaption>
            </figure>
            <h2>日落与晚霞</h2>
            <p class="lead">{{ extra.golden.sunset }}</p>
            <ul class="facts">
              <li v-if="sun"><span>时间</span>日落 {{ sun.sunset }}，{{ sun.goldenStart }}–{{ sun.goldenEnd }} 是暖光窗口，提前 40 分钟到位</li>
              <li v-if="sun"><span>方位</span>太阳落在 {{ sun.az.deg }}°（{{ sun.az.label }}），落点放在画面右三分之一</li>
              <li><span>光线</span>{{ tip.light }}</li>
              <li><span>参数</span>{{ tip.gear }}</li>
            </ul>
          </div>

          <div class="block">
            <figure v-if="nightPhoto" class="big" @click="openAt(gallery.length - 1)">
              <img :src="nightPhoto.src" alt="夜色" loading="lazy" />
              <figcaption>{{ nightPhoto.own ? '本点位实拍' : '同城实拍' }} · {{ nightPhoto.name }}</figcaption>
            </figure>
            <h2>入夜之后</h2>
            <p class="lead">{{ extra.golden.night }}</p>
            <ul class="facts">
              <li v-if="sun"><span>顺序</span>先拍 {{ sun.blue }} 的蓝调，再过 30 分钟才是纯夜景</li>
              <li><span>参数</span>f/8 · ISO 400 · 三脚架 2–4 秒，强光主体 -1EV 保高光</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- 机位 -->
      <section v-else-if="tab === 'shot'" class="pane">
        <div class="block">
          <h2>怎么走<span class="sub">沿主步道的取景顺序</span></h2>
          <p class="lead">{{ guide.route }}</p>
          <ul class="pts">
            <li v-for="p in guide.photo" :key="p"><span class="dot"></span>{{ p }}</li>
          </ul>
        </div>
        <div class="block">
          <h2>机位笔记</h2>
          <ul class="shots-list">
            <li v-for="s in extra.shots" :key="s.n">
              <b>{{ s.n }}</b>
              <p>{{ s.t }}</p>
            </li>
            <li v-if="!extra.shots.length" class="muted">以自然景观为主，沿主步道走即可，沿途都能取景。</li>
          </ul>
        </div>
      </section>

      <!-- 吃什么 -->
      <section v-else-if="tab === 'eat'" class="pane">
        <div class="block">
          <h2>{{ spot.city }}吃什么<span class="sub">本地老店，价格为 2025 年前后人均</span></h2>
          <div class="eats">
            <div v-for="f in shops" :key="f.n" class="eat">
              <b>{{ f.n }}</b>
              <p>{{ f.d }}</p>
              <span>{{ f.p }} · {{ f.loc }}</span>
            </div>
          </div>
          <ul class="dots">
            <li v-for="e in extra.eats" :key="e">{{ e }}</li>
          </ul>
          <div class="jumps">
            <a :href="xhs(spot.city + ' 必吃')" target="_blank" rel="noreferrer">小红书 · {{ spot.city }}必吃</a>
            <a :href="dy(spot.city + ' 美食')" target="_blank" rel="noreferrer">抖音 · {{ spot.city }}美食</a>
          </div>
        </div>
      </section>

      <!-- 怎么去 -->
      <section v-else class="pane">
        <div class="block">
          <h2>怎么去</h2>
          <p class="lead">{{ guide.access }}</p>
          <div class="jumps">
            <a :href="amapNav(spot.lat, spot.lng, spot.name)" target="_blank" rel="noreferrer">高德导航到 {{ spot.name }}</a>
            <router-link v-if="spot.city" :to="{ path: '/routes', query: {} }">看 {{ spot.city }} 附近的徒步路线</router-link>
          </div>
        </div>
        <div class="block">
          <h2>实用提醒</h2>
          <p class="tip">{{ extra.tip }}</p>
          <p class="muted">开放时间、门票与预约方式会变，出发前以景区公告为准。</p>
        </div>
      </section>
    </main>

    <LightBox
      :images="gallery"
      :index="lbIndex"
      :open="lbOpen"
      @close="lbOpen = false"
      @update:index="lbIndex = $event"
    />
  </div>

  <div v-else class="missing">
    <p>没有这个点位</p>
    <button @click="router.push('/spots')">回到景点列表</button>
  </div>
</template>

<style scoped>
.page {
  padding-top: var(--nav-h);
  padding-bottom: 70px;
}

.hero {
  position: relative;
  height: clamp(260px, 38vh, 420px);
  background: #22392c;
  overflow: hidden;
}

.hero-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  cursor: zoom-in;
}

.hero-shade {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(to top, rgba(10, 18, 13, 0.86) 0%, rgba(10, 18, 13, 0.2) 58%, rgba(10, 18, 13, 0.3) 100%);
}

.hero-inner {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  max-width: 1240px;
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

/* 收藏：同一条 hero 上，右侧对齐 */
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

.kicker {
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  color: rgba(255, 255, 255, 0.7);
}

.hero h1 {
  font-family: var(--serif);
  font-size: 2rem;
  margin: 4px 0 6px;
}

.hero-meta {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.78);
}

.hero-tags {
  display: flex;
  gap: 6px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.hero-tags span {
  font-size: 0.68rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
}

.zoom-hint {
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

.hero:hover .zoom-hint {
  opacity: 1;
  transform: none;
}

.sticky {
  position: sticky;
  top: var(--nav-h);
  z-index: 40;
  background: rgba(250, 248, 242, 0.97);
  backdrop-filter: saturate(180%) blur(12px);
  border-bottom: 1px solid var(--line);
}

.sticky-inner {
  max-width: 1240px;
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
  padding: 13px 12px;
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
  text-decoration: none;
  white-space: nowrap;
}

.q.primary {
  background: var(--forest);
  border-color: var(--forest);
  color: #fff;
}

.wrap {
  max-width: 1240px;
  margin: 0 auto;
  padding: 20px 28px 0;
}

.pane {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.block {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 13px;
  padding: 16px 18px;
  box-shadow: var(--shadow-sm);
}

.reason {
  font-size: 0.9rem;
  line-height: 1.95;
  color: var(--ink-soft);
}

.badges {
  display: flex;
  gap: 7px;
  margin-top: 11px;
  flex-wrap: wrap;
}

.badge {
  font-size: 0.7rem;
  padding: 3px 9px;
  border-radius: 5px;
  color: #fff;
  background: var(--forest);
}

.badge.ghost {
  background: #f2efe6;
  color: var(--ink-soft);
}

/* 光线板 */
.light-board {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 190px;
  align-items: stretch;
  gap: 14px;
  background: linear-gradient(160deg, #2b4a37, #1c3225);
  border-radius: 14px;
  padding: 16px 18px;
  color: #fff;
}

.timeline h3 {
  font-family: var(--serif);
  font-size: 0.95rem;
  margin-bottom: 12px;
  color: #f4ecd8;
}

.tl {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.tl-item {
  border-left: 2px solid rgba(255, 255, 255, 0.18);
  padding-left: 10px;
}

.tl-item.key {
  border-left-color: #e0a83c;
}

.tl-item b {
  font-size: 1.05rem;
  font-variant-numeric: tabular-nums;
}

.tl-item span {
  display: block;
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.62);
  margin-top: 1px;
}

.tl-item em {
  display: block;
  font-style: normal;
  font-size: 0.68rem;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 5px;
}

.compass {
  text-align: center;
  align-self: center;
}

.compass svg {
  width: 156px;
  height: 156px;
  display: block;
  margin: 0 auto;
}

.compass p {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.66);
  margin-top: 6px;
  white-space: nowrap;
}

/* 同城 */
.nearby {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 9px;
}

.nb {
  text-align: left;
  border: 1px solid var(--line);
  background: #fcfbf6;
  border-radius: 9px;
  padding: 9px 11px;
  cursor: pointer;
}

.nb:hover {
  border-color: var(--forest-light);
  background: var(--forest-soft);
}

.nb b {
  display: block;
  font-size: 0.8rem;
  color: var(--forest-dark);
}

.nb span {
  font-size: 0.68rem;
  color: var(--gray);
}

/* 四季 */
.seasons {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 11px;
}

.season {
  margin: 0;
  border: 1px solid var(--line);
  border-radius: 11px;
  overflow: hidden;
  background: #fff;
  cursor: zoom-in;
}

.season img {
  width: 100%;
  aspect-ratio: 3 / 2;
  object-fit: cover;
  display: block;
}

.season-empty {
  aspect-ratio: 3 / 2;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  color: var(--gray-light);
  background: repeating-linear-gradient(45deg, #f4f5f2, #f4f5f2 8px, #eef0ec 8px, #eef0ec 16px);
}

.season figcaption {
  padding: 9px 10px 10px;
}

.sh {
  display: flex;
  align-items: baseline;
  gap: 7px;
}

.sh b {
  font-size: 0.92rem;
  color: var(--forest-dark);
}

.sh span {
  font-size: 0.66rem;
  color: var(--gray-light);
}

.sh em {
  margin-left: auto;
  font-style: normal;
  font-size: 0.64rem;
  padding: 1px 6px;
  border-radius: 4px;
  background: #eef4ee;
  color: var(--forest);
}

.sh em.v5,
.sh em.v4 {
  background: var(--forest);
  color: #fff;
}

.bars {
  display: flex;
  gap: 3px;
  margin: 6px 0;
}

.bars i {
  flex: 1;
  height: 3px;
  border-radius: 99px;
  background: #e9e3d5;
}

.bars i.f {
  background: var(--forest-light);
}

.season p {
  font-size: 0.71rem;
  line-height: 1.65;
  color: var(--gray);
}

/* 日落 */
.sun-bar {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: 11px;
  overflow: hidden;
}

.sun-item {
  background: #fbf9f3;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sun-item b {
  font-size: 1rem;
  color: var(--forest-dark);
  font-variant-numeric: tabular-nums;
}

.sun-item span {
  font-size: 0.66rem;
  color: var(--gray);
}

.two {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.big {
  margin: 0 0 12px;
  border-radius: 10px;
  overflow: hidden;
  cursor: zoom-in;
}

.big img {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  display: block;
}

.big figcaption {
  font-size: 0.68rem;
  color: var(--gray);
  padding: 6px 9px;
  background: var(--cream);
}

.block h2 {
  font-family: var(--serif);
  font-size: 1rem;
  color: var(--forest-dark);
  display: flex;
  align-items: baseline;
  gap: 9px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.block h2 .sub {
  font-family: inherit;
  font-size: 0.7rem;
  font-weight: 400;
  color: var(--gray);
}

.lead {
  font-size: 0.84rem;
  line-height: 1.85;
  color: var(--ink-soft);
  margin-bottom: 10px;
}

.facts {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.facts li {
  font-size: 0.77rem;
  line-height: 1.7;
  color: var(--ink-soft);
  padding-left: 48px;
  position: relative;
}

.facts li span {
  position: absolute;
  left: 0;
  top: 1px;
  width: 40px;
  text-align: center;
  font-size: 0.64rem;
  font-weight: 700;
  color: var(--forest);
  background: #eef4ee;
  border-radius: 4px;
}

.tip {
  margin-top: 10px;
  font-size: 0.78rem;
  line-height: 1.85;
  color: var(--ink-soft);
  background: #f8f5ec;
  border-radius: 9px;
  padding: 11px 13px;
}

/* 机位 / 吃 / 去 */
.pts,
.shots-list,
.dots {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.pts li {
  display: flex;
  gap: 8px;
  font-size: 0.78rem;
  line-height: 1.7;
  color: var(--ink-soft);
}

.dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--forest-light);
  margin-top: 8px;
  flex-shrink: 0;
}

.shots-list li b {
  font-size: 0.79rem;
  color: var(--forest-dark);
}

.shots-list li p {
  font-size: 0.76rem;
  line-height: 1.7;
  color: var(--ink-soft);
}

.eats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
}

.eat {
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 9px 11px;
}

.eat b {
  font-size: 0.8rem;
  color: var(--forest-dark);
}

.eat p {
  font-size: 0.72rem;
  color: var(--gray);
  line-height: 1.6;
  margin: 3px 0;
}

.eat span {
  font-size: 0.68rem;
  color: var(--gray-light);
}

.jumps {
  display: flex;
  gap: 10px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.jumps a {
  font-size: 0.75rem;
  color: var(--forest);
  text-decoration: none;
  border-bottom: 1px solid rgba(45, 90, 61, 0.3);
  padding-bottom: 1px;
}

.muted {
  color: var(--gray-light);
  font-size: 0.76rem;
  margin-top: 6px;
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
  .light-board,
  .two,
  .eats {
    grid-template-columns: minmax(0, 1fr);
  }
  .seasons {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .compass {
    max-width: 200px;
    margin: 0 auto;
  }
}

@media (max-width: 680px) {
  .hero-inner,
  .sticky-inner,
  .wrap {
    padding-left: 16px;
    padding-right: 16px;
  }
  .hero h1 {
    font-size: 1.45rem;
  }
  .sticky-inner {
    flex-direction: column;
    align-items: stretch;
  }
  .quick-links {
    margin-left: 0;
    padding-bottom: 8px;
  }
  .tl {
    grid-template-columns: minmax(0, 1fr);
  }
  .seasons,
  .nearby,
  .sun-bar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .facts li {
    padding-left: 0;
  }
  .facts li span {
    position: static;
    display: inline-block;
    width: auto;
    padding: 0 6px;
    margin-right: 6px;
  }
}
</style>
