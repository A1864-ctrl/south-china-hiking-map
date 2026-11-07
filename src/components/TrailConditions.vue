<script setup>
/**
 * 路况与天气：挂在路线详情页
 * 只显示这条线的已审核路况、按起点经纬度算的天气、同线营地
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { camps } from '../data/camps.js'
import { mountainWeather } from '../data/weather.js'
import { fetchWeather, iconOf } from '../data/openmeteo.js'
import { sunInfo } from '../data/sun.js'
import { REPORT_TYPES, REPORT_LEVEL, useFieldStore } from '../stores/field.js'
import { useAuthStore } from '../stores/auth.js'
import { useFavStore } from '../stores/fav.js'
import { useUiStore } from '../stores/ui.js'

const props = defineProps({ route: { type: Object, required: true } })

const field = useFieldStore()
const auth = useAuthStore()
const fav = useFavStore()
const ui = useUiStore()
const router = useRouter()

const reports = computed(() => field.reportsFor(props.route.id))
const start = computed(() => props.route.waypoints[0])
const modelWx = computed(() => mountainWeather(start.value.lat, start.value.lng, { ele: start.value.ele, days: 7 }))
const real = ref(null)
const loading = ref(false)
const wx = computed(() => real.value || modelWx.value)
const isReal = computed(() => !!real.value)
const bigTemp = computed(() => (isReal.value && wx.value.now ? wx.value.now.temp : wx.value.today.high))

async function loadReal() {
  if (!navigator.onLine) {
    real.value = null
    return
  }
  loading.value = true
  try {
    real.value = await fetchWeather(start.value.lat, start.value.lng, { ele: start.value.ele, days: 7 })
  } catch {
    real.value = null
  } finally {
    loading.value = false
  }
}

onMounted(loadReal)
const sun = computed(() => {
  try {
    return sunInfo(start.value.lat, start.value.lng, new Date())
  } catch {
    return null
  }
})
const nearbyCamps = computed(() => camps.filter((c) => c.rid === Number(props.route.id)))

const typeMeta = (k) => REPORT_TYPES.find((t) => t.k === k) || REPORT_TYPES[0]
const levelMeta = (v) => REPORT_LEVEL.find((l) => l.v === Number(v)) || REPORT_LEVEL[0]

function ago(ts) {
  const d = Date.now() - ts
  const h = Math.floor(d / 3600000)
  if (h < 1) return `${Math.max(1, Math.floor(d / 60000))} 分钟前`
  if (h < 24) return `${h} 小时前`
  return `${Math.floor(h / 24)} 天前`
}

const walked = computed(() => field.isWalked(props.route.id))
function toggleWalk() {
  if (!auth.isLogged) return auth.openDialog('login')
  const on = field.toggleWalked(props.route.id)
  ui.toast(on ? '已记入「我的轨迹」' : '已从我的轨迹移除')
}
</script>

<template>
  <div class="conds">
    <div class="top">
      <div class="wx-now">
        <div class="wn-l">
          <p class="wn-k">
            起点 · {{ start.name }}
            <span class="wn-src">{{ isReal ? `Open-Meteo ${wx.updated}` : '模拟' }}</span>
          </p>
          <p class="wn-t">{{ bigTemp }}<em>℃</em><span>/ {{ wx.today.low }}℃</span></p>
          <p class="wn-c">{{ wx.today.name }} · 降水 {{ wx.today.precip || 0 }}mm · 风 {{ wx.today.wind }} 级</p>
          <p class="wn-geo">{{ start.lat.toFixed(3) }}°N {{ start.lng.toFixed(3) }}°E · {{ start.ele }}m</p>
        </div>
        <div class="wn-r">
          <span>{{ wx.today.icon }}</span>
          <p class="wn-sun">日出 {{ sun ? sun.sunrise : '--:--' }} · 日落 {{ sun ? sun.sunset : '--:--' }}</p>
        </div>
      </div>
      <div class="days">
        <div v-for="d in wx.days" :key="d.iso" class="d">
          <em>{{ d.wd }}</em>
          <span class="d-ic">{{ d.icon || iconOf(d.cond) }}</span>
          <b>{{ d.high }}°</b>
          <i>{{ d.low }}°</i>
          <span class="d-rain" :class="{ wet: d.precip >= 10 }">{{ d.precip ? d.precip + 'mm' : '—' }}</span>
        </div>
      </div>
    </div>

    <div v-if="wx.warnings.length" class="warns">
      <span class="w-label">预警</span>
      <span v-for="w in wx.warnings" :key="w.k" class="w" :style="{ borderColor: w.tone + '55', color: w.tone }">{{ w.text }}</span>
    </div>

    <div class="acts">
      <button class="act" @click="router.push('/reports')">上报路况</button>
      <button class="act" :class="{ on: walked }" @click="toggleWalk">{{ walked ? '✓ 已走过' : '标记走过' }}</button>
      <button class="act" @click="router.push('/safety')">安全报备</button>
      <button class="act" @click="router.push(`/weather`)">完整天气 →</button>
      <button class="act" :class="{ on: fav.has('route', route.id) }" @click="fav.toggle('route', route.id); ui.toast(fav.has('route', route.id) ? '已收藏' : '已取消收藏')">
        {{ fav.has('route', route.id) ? '★ 已收藏' : '☆ 收藏' }}
      </button>
    </div>

    <div class="grid2">
      <!-- 路况 -->
      <section class="card-block">
        <header class="cb-head">
          <h3>这段路现在什么情况</h3>
          <span v-if="reports.length">{{ reports.length }} 条已挂载</span>
          <span v-else>暂无上报</span>
        </header>

        <div v-if="reports.length" class="rlist">
          <article v-for="r in reports.slice(0, 5)" :key="r.id" class="r">
            <span class="r-ic" :style="{ background: typeMeta(r.type).tone + '14', color: typeMeta(r.type).tone }">
              {{ typeMeta(r.type).icon }}
            </span>
            <div class="r-b">
              <p class="r-t">
                {{ typeMeta(r.type).name }}
                <em :style="{ color: levelMeta(r.level).tone, borderColor: levelMeta(r.level).tone + '55' }">{{ levelMeta(r.level).name }}</em>
                <span class="r-time">{{ ago(r.at) }}</span>
              </p>
              <p class="r-n">{{ r.note }}</p>
              <p class="r-by">{{ r.by }} · {{ r.confirm }} 人确认</p>
            </div>
          </article>
        </div>
        <p v-else class="cb-empty">这条线最近没人报路况。走过的话，顺手报一条，下一个人会感谢你。</p>
      </section>

      <!-- 营地 -->
      <section class="card-block">
        <header class="cb-head">
          <h3>沿线营地</h3>
          <span>{{ nearbyCamps.length }} 处</span>
        </header>

        <div v-if="nearbyCamps.length" class="clist">
          <article v-for="c in nearbyCamps" :key="c.id" class="c">
            <div class="c-top">
              <b>{{ c.name }}</b>
              <em>{{ c.ele }}m</em>
            </div>
            <p class="c-attrs">
              <span :class="{ no: c.fire === '禁止' }">明火 {{ c.fire }}</span>
              <span :class="{ no: c.water.startsWith('无') }">{{ c.water }}</span>
              <span>{{ c.night }}</span>
              <span>{{ c.fee }}</span>
            </p>
            <p class="c-note">{{ c.note }}</p>
          </article>
        </div>
        <p v-else class="cb-empty">这条线没有收录营地，按单日往返准备。</p>
        <button class="more" @click="router.push('/camps')">看全部 {{ camps.length }} 处营地 →</button>
      </section>
    </div>

    <p class="note">
      路况由山友上报，审核通过后挂到这里。天气默认接入 Open-Meteo 真实预报（卡片左上角标注来源与更新时间），
      断网时回退模型数据。提示条按预报推算，不是官方预警信号；出行前请以气象台预报与景区公告为准。
    </p>
  </div>
</template>

<style scoped>
.conds {
  animation: fade 0.3s ease;
}
@keyframes fade {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
}
.top {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}
.wx-now {
  background: linear-gradient(150deg, #1e3d29, #2f5c3e);
  color: #fff;
  border-radius: 10px;
  padding: 13px 16px 12px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
.wn-k {
  font-size: 0.6rem;
  color: rgba(255, 255, 255, 0.55);
  font-family: var(--mono, ui-monospace, monospace);
}
.wn-t {
  font-family: var(--serif);
  font-size: 2rem;
  line-height: 1.1;
  margin-top: 3px;
}
.wn-t em {
  font-size: 0.9rem;
  font-style: normal;
  opacity: 0.7;
}
.wn-t span {
  font-size: 0.9rem;
  opacity: 0.55;
}
.wn-c {
  font-size: 0.64rem;
  color: rgba(255, 255, 255, 0.75);
  margin-top: 3px;
}
.wn-src {
  display: inline-block;
  margin-left: 6px;
  padding: 0 5px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.14);
  font-size: 0.5rem;
  color: rgba(255, 255, 255, 0.72);
  letter-spacing: 0.04em;
}
.wn-geo {
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.54rem;
  color: rgba(255, 255, 255, 0.44);
  margin-top: 3px;
}
.wn-r {
  text-align: right;
}
.wn-r > span {
  font-size: 2rem;
  line-height: 1;
}
.wn-sun {
  font-size: 0.58rem;
  color: rgba(255, 255, 255, 0.6);
  margin-top: 6px;
  white-space: nowrap;
}
.days {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 5px;
  align-items: start;
}
.d {
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px 2px 11px;
  text-align: center;
  background: #fff;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 132px;
  gap: 1px;
}
.d-rain {
  display: block;
  font-size: 0.56rem;
  color: var(--gray-light);
  margin-top: 4px;
  padding-top: 3px;
  border-top: 1px dashed var(--line);
  width: 70%;
  margin-left: auto;
  margin-right: auto;
}
.d-rain.wet {
  color: #2f6f9e;
}
.d em {
  display: block;
  font-size: 0.56rem;
  font-style: normal;
  color: var(--gray);
}
.d-ic {
  display: block;
  font-size: 0.92rem;
  margin: 4px 0 2px;
}
.d b {
  display: block;
  font-family: var(--serif);
  font-size: 0.8rem;
  color: var(--ink);
}
.d i {
  display: block;
  font-size: 0.58rem;
  font-style: normal;
  color: var(--gray-light);
}
.warns {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.w-label {
  font-size: 0.58rem;
  color: var(--gray-light);
  letter-spacing: 0.08em;
}
.w {
  font-size: 0.6rem;
  padding: 2px 8px;
  border: 1px solid;
  border-radius: 999px;
  background: #fff;
}
.acts {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
  margin-top: 14px;
}
.act {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 4px;
  font-size: 0.68rem;
  padding: 5px 12px;
  color: var(--ink-soft);
  cursor: pointer;
  transition: 0.16s;
}
.act:hover {
  border-color: var(--forest-light);
  color: var(--forest);
}
.act.on {
  border-color: var(--forest);
  background: var(--forest-soft);
  color: var(--forest-dark);
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 16px;
}
.card-block {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 13px 15px 14px;
  background: #fff;
}
.cb-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-bottom: 9px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 9px;
}
.cb-head h3 {
  font-family: var(--serif);
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--ink);
}
.cb-head span {
  font-size: 0.58rem;
  color: var(--gray-light);
}
.r {
  display: flex;
  gap: 9px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(230, 225, 214, 0.6);
}
.r:last-child {
  border-bottom: none;
}
.r-ic {
  flex: 0 0 auto;
  width: 26px;
  height: 26px;
  border-radius: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.76rem;
}
.r-b {
  flex: 1;
  min-width: 0;
}
.r-t {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--ink);
}
.r-t em {
  font-size: 0.52rem;
  font-style: normal;
  border: 1px solid;
  border-radius: 2px;
  padding: 0 4px;
  font-weight: 400;
}
.r-time {
  margin-left: auto;
  font-size: 0.56rem;
  color: var(--gray-light);
  font-weight: 400;
}
.r-n {
  font-size: 0.68rem;
  color: var(--ink-soft);
  line-height: 1.7;
  margin-top: 3px;
}
.r-by {
  font-size: 0.56rem;
  color: var(--gray-light);
  margin-top: 3px;
}
.c {
  padding: 8px 0;
  border-bottom: 1px solid rgba(230, 225, 214, 0.6);
}
.c:last-child {
  border-bottom: none;
}
.c-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
}
.c-top b {
  font-size: 0.72rem;
  color: var(--ink);
}
.c-top em {
  font-size: 0.56rem;
  font-style: normal;
  color: var(--gray-light);
  font-family: var(--mono, ui-monospace, monospace);
}
.c-attrs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}
.c-attrs span {
  font-size: 0.56rem;
  padding: 1px 6px;
  border-radius: 2px;
  background: var(--forest-soft);
  color: var(--forest);
}
.c-attrs span.no {
  background: #f7eae7;
  color: #a9462f;
}
.c-note {
  font-size: 0.6rem;
  color: var(--gray);
  line-height: 1.7;
  margin-top: 4px;
}
.cb-empty {
  font-size: 0.68rem;
  color: var(--gray);
  line-height: 1.8;
  padding: 6px 0;
}
.more {
  border: none;
  background: none;
  font-size: 0.6rem;
  color: var(--forest);
  cursor: pointer;
  padding: 6px 0 0;
}
.note {
  font-size: 0.6rem;
  color: var(--gray-light);
  line-height: 1.8;
  margin-top: 12px;
}
@media (max-width: 900px) {
  .top {
    grid-template-columns: 1fr;
  }
  .grid2 {
    grid-template-columns: 1fr;
  }
  .days {
    grid-template-columns: repeat(4, 1fr);
  }
}
</style>
