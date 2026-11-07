<script setup>
/**
 * 点位天气
 * 按经纬度 + 海拔生成 7 天山区天气（确定性模型，不联网）；日出日落用 NOAA 算法实时算
 */
import { computed, onMounted, ref, watch } from 'vue'
import { spots } from '../data/spots.js'
import { routes } from '../data/routes.js'
import { mountainWeather } from '../data/weather.js'
import { sunInfo } from '../data/sun.js'
import { fetchWeather, iconOf } from '../data/openmeteo.js'
import { useUiStore } from '../stores/ui.js'

const ui = useUiStore()

const mode = ref('route')
const picked = ref(routes.find((r) => r.name.includes('船底顶'))?.id || routes[0].id)
const pickedSpot = ref(spots[0].name)
const day = ref(0)

const target = computed(() => {
  if (mode.value === 'route') {
    const r = routes.find((x) => x.id === Number(picked.value)) || routes[0]
    const start = r.waypoints[0]
    return {
      name: r.name,
      sub: `${r.province} · ${r.city} · 起点 ${start.name}`,
      lat: start.lat,
      lng: start.lng,
      ele: start.ele,
      maxEle: r.maxEle,
      routeId: r.id
    }
  }
  const s = spots.find((x) => x.name === pickedSpot.value) || spots[0]
  return { name: s.name, sub: `${s.city} · ${s.district} · ${s.type}`, lat: s.lat, lng: s.lng, ele: 0, maxEle: 0, routeId: 0 }
})

/* 模型永远先算出来当兜底；配了 Key 再用真实数据替换 */
const modelWx = computed(() => mountainWeather(target.value.lat, target.value.lng, { ele: target.value.ele, days: 7 }))
const real = ref(null)
const loading = ref(false)
const errText = ref('')
const wx = computed(() => real.value || modelWx.value)
const isReal = computed(() => !!real.value)

async function loadReal() {
  errText.value = ''
  if (!navigator.onLine) {
    real.value = null
    errText.value = '当前离线，显示模拟数据'
    return
  }
  loading.value = true
  try {
    real.value = await fetchWeather(target.value.lat, target.value.lng, { ele: target.value.ele, days: 7 })
  } catch (e) {
    real.value = null
    errText.value = e.message || '真实天气获取失败'
    ui.toast(`${errText.value}，已回退模拟数据`)
  } finally {
    loading.value = false
  }
}

const sun = computed(() => {
  try {
    return sunInfo(target.value.lat, target.value.lng, new Date())
  } catch {
    return null
  }
})

watch([mode, picked, pickedSpot], () => {
  day.value = 0
  loadReal()
})

onMounted(loadReal)

const cur = computed(() => wx.value.days[day.value] || wx.value.days[0])
const bigTemp = computed(() => {
  if (isReal.value && wx.value.now && day.value === 0) return wx.value.now.temp
  return cur.value.high
})
const realNote = computed(() => {
  if (!isReal.value) return `体感按海拔 ${target.value.ele} m 修正`
  const n = wx.value.now || {}
  return `当前 ${n.temp}℃，体感 ${n.feels}℃ · ${n.windDir || ''}${n.wind} 级 · 湿度 ${n.humidity}%`
})
const srcNote = computed(() => (errText.value ? errText.value : '接口未返回或离线'))

const windText = (n) => `${n} 级`
const mmText = (v) => (v ? `${v} mm` : '—')

const spotGroups = computed(() => {
  const map = new Map()
  for (const s of spots) {
    if (!map.has(s.city)) map.set(s.city, [])
    map.get(s.city).push(s)
  }
  return [...map.entries()]
})

const routeGroups = computed(() => {
  const map = new Map()
  for (const r of routes) {
    if (!map.has(r.province)) map.set(r.province, [])
    map.get(r.province).push(r)
  }
  return [...map.entries()]
})
</script>

<template>
  <div class="page">
    <div class="container">
      <header class="hd">
        <div>
          <p class="k">MOUNTAIN WEATHER · 点位天气</p>
          <h1>山里比城里，早两小时变天</h1>
          <p class="d">
            7 天点位天气，按经纬度逐点查询，默认接入 Open-Meteo 免费真实预报（当前气温、降水概率、阵风）；
            断网或接口失败时自动回退到本地模型（温度按海拔 0.6℃/100m 修正），页面上会明确标出当前是哪一种。
          </p>
        </div>
        <div class="src">
          <span class="src-dot" :class="{ live: isReal }"></span>
          <template v-if="isReal">
            <b>Open-Meteo · 实时</b>
            <em>{{ wx.updated }} 更新{{ wx.cached ? ' · 缓存' : '' }}</em>
          </template>
          <template v-else>
            <b>模拟数据</b>
            <em>{{ srcNote }}</em>
          </template>
          <button class="src-btn" :disabled="loading" @click="loadReal">{{ loading ? '更新中…' : '刷新' }}</button>
        </div>
      </header>

      <div class="cols">
        <!-- 左：选点位 -->
        <aside class="picker">
          <div class="modes">
            <button :class="{ on: mode === 'route' }" @click="mode = 'route'">按路线</button>
            <button :class="{ on: mode === 'spot' }" @click="mode = 'spot'">按景点</button>
          </div>

          <template v-if="mode === 'route'">
            <label class="sel">
              <span>选择路线</span>
              <select v-model="picked">
                <optgroup v-for="[p, list] in routeGroups" :key="p" :label="p">
                  <option v-for="r in list" :key="r.id" :value="r.id">{{ r.name }}</option>
                </optgroup>
              </select>
            </label>
          </template>
          <template v-else>
            <label class="sel">
              <span>选择点位</span>
              <select v-model="pickedSpot">
                <optgroup v-for="[c, list] in spotGroups" :key="c" :label="c">
                  <option v-for="s in list" :key="s.name" :value="s.name">{{ s.name }}</option>
                </optgroup>
              </select>
            </label>
          </template>

          <div class="place">
            <p class="p-name">{{ target.name }}</p>
            <p class="p-sub">{{ target.sub }}</p>
            <p class="p-geo">
              <span>{{ target.lat.toFixed(4) }}°N</span>
              <i></i>
              <span>{{ target.lng.toFixed(4) }}°E</span>
              <i></i>
              <span>{{ target.ele }} m</span>
            </p>
            <p v-if="target.maxEle" class="p-max">最高点 {{ target.maxEle }} m</p>
          </div>

          <div class="warns">
            <p class="w-title">当前预警 {{ wx.warnings.length }}</p>
            <div v-if="wx.warnings.length" class="w-list">
              <div v-for="w in wx.warnings" :key="w.k" class="w-item" :style="{ borderLeftColor: w.tone }">
                <b :style="{ color: w.tone }">{{ w.kind || w.text.slice(0, 2) }}</b>
                <span>{{ w.text }}</span>
              </div>
            </div>
            <p v-else class="w-none">未来 7 天没有明显预警。</p>
          </div>

          <div class="astro">
            <div>
              <span>日出</span>
              <b>{{ sun ? sun.sunrise : '—' }}</b>
            </div>
            <div>
              <span>日落</span>
              <b>{{ sun ? sun.sunset : '—' }}</b>
            </div>
            <div>
              <span>云海概率</span>
              <b>{{ wx.seaOfCloud }}%</b>
            </div>
            <div>
              <span>观星指数</span>
              <b>{{ isReal ? '—' : wx.stars }}</b>
            </div>
          </div>

        </aside>

        <!-- 右：天气 -->
        <section class="wx">
          <div class="now">
            <div class="now-l">
              <p class="now-k">{{ cur.wd }} · {{ cur.date }}</p>
              <p class="now-t">
                {{ bigTemp }}<em>℃</em>
                <span> / {{ cur.low }}℃</span>
              </p>
              <p class="now-c">{{ cur.name }} · {{ realNote }}</p>
              <p class="now-bar">
                <span>降水 {{ mmText(cur.precip) }}</span>
                <i></i>
                <span>概率 {{ cur.prob }}%</span>
                <i></i>
                <span>风力 {{ windText(cur.wind) }}（阵风 {{ cur.gust }} 级）</span>
              </p>
            </div>
            <div class="now-r">
              <span class="now-icon">{{ cur.icon || iconOf(cur.cond) }}</span>
            </div>
          </div>

          <div class="strip">
            <button
              v-for="(d, i) in wx.days"
              :key="d.iso"
              class="day"
              :class="{ on: day === i }"
              @click="day = i"
            >
              <em>{{ d.wd }}</em>
              <span class="ic">{{ d.icon || iconOf(d.cond) }}</span>
              <b>{{ d.high }}°</b>
              <i>{{ d.low }}°</i>
              <span class="rain" :class="{ wet: d.precip >= 10 }">{{ d.precip ? d.precip + 'mm' : '—' }}</span>
              <span class="wind">{{ d.wind }}级</span>
            </button>
          </div>

          <div class="detail">
            <div class="d-card">
              <p class="dc-t">降水与雷电</p>
              <p class="dc-v">{{ cur.precip ? cur.precip + ' mm' : '无降水' }} · 概率 {{ cur.prob }}%</p>
              <p class="dc-n">
                {{
                  cur.cond === 'storm'
                    ? '午后强对流，山脊与草甸 11–16 点最危险，避开无遮挡段。'
                    : cur.precip >= 10
                      ? '有中雨，岩面、树根、碎石坡都会变滑，下坡放慢。'
                      : '降水影响不大，仍建议带一件硬壳。'
                }}
              </p>
            </div>
            <div class="d-card">
              <p class="dc-t">风力</p>
              <p class="dc-v">{{ cur.wind }} 级 · 阵风 {{ cur.gust }} 级</p>
              <p class="dc-n">
                {{
                  cur.gust >= 7
                    ? '阵风偏大：帐篷压石、拉满风绳，别在孤立大树下扎营。'
                    : cur.gust >= 5
                      ? '有风，草甸与垭口体感更冷，加一层防风。'
                      : '风不大，适合在鞍部扎营。'
                }}
              </p>
            </div>
            <div class="d-card">
              <p class="dc-t">昼夜温差</p>
              <p class="dc-v">{{ cur.high - cur.low }}℃</p>
              <p class="dc-n">
                {{
                  cur.high - cur.low >= 12
                    ? '温差超过 12℃，夜里必须加保暖层，睡袋按低温选。'
                    : '温差正常，按三季装备准备即可。'
                }}
              </p>
            </div>
          </div>

          <div class="tip-line">
            <b>怎么用</b>
            <span>出发前看第 1–2 天；报备时把「雷电 / 大风」写进备注；路线详情页的「路况与天气」用的就是这套数据。</span>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  background: var(--cream);
}
.hd {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--line);
}
.k {
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.62rem;
  letter-spacing: 0.18em;
  color: var(--forest-light);
  margin-bottom: 7px;
}
.hd h1 {
  font-family: var(--serif);
  font-size: 1.72rem;
  font-weight: 600;
  color: var(--forest-dark);
}
.d {
  font-size: 0.8rem;
  color: var(--gray);
  line-height: 1.9;
  max-width: 780px;
  margin-top: 8px;
}
.src {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  flex-shrink: 0;
}
.src-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #a97a17;
}
.src-dot.live {
  background: #2d5a3d;
  box-shadow: 0 0 0 3px rgba(45, 90, 61, 0.12);
}
.src b {
  font-size: 0.7rem;
  color: var(--ink);
  font-weight: 600;
}
.src em {
  font-size: 0.6rem;
  font-style: normal;
  color: var(--gray-light);
}
.src-btn {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 999px;
  font-size: 0.6rem;
  padding: 3px 9px;
  color: var(--gray);
  cursor: pointer;
  margin-left: 4px;
}
.src-btn:hover {
  border-color: var(--forest-light);
  color: var(--forest);
}
.src-btn:disabled {
  opacity: 0.6;
  cursor: wait;
}
.cols {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}
.picker {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 16px 18px;
  position: sticky;
  top: calc(var(--nav-h) + 18px);
}
.modes {
  display: flex;
  border: 1px solid var(--line);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}
.modes button {
  flex: 1;
  border: none;
  background: #fff;
  font-size: 0.68rem;
  padding: 6px 0;
  color: var(--gray);
  cursor: pointer;
}
.modes button.on {
  background: var(--forest);
  color: #fff;
}
.sel span {
  display: block;
  font-size: 0.62rem;
  color: var(--gray);
  margin-bottom: 5px;
}
.sel select {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 7px 9px;
  font-size: 0.74rem;
  background: #fcfaf5;
  color: var(--ink);
  outline: none;
  font-family: inherit;
}
.place {
  margin-top: 14px;
  padding: 12px 0;
  border-top: 1px dashed var(--line);
  border-bottom: 1px dashed var(--line);
}
.p-name {
  font-family: var(--serif);
  font-size: 1rem;
  color: var(--ink);
  line-height: 1.45;
}
.p-sub {
  font-size: 0.62rem;
  color: var(--gray);
  margin-top: 3px;
}
.p-geo {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 7px;
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.58rem;
  color: var(--ink-soft);
  flex-wrap: wrap;
}
.p-geo i {
  width: 1px;
  height: 7px;
  background: var(--line);
}
.p-max {
  font-size: 0.58rem;
  color: var(--gray-light);
  margin-top: 4px;
}
.warns {
  margin-top: 13px;
}
.w-title {
  font-size: 0.62rem;
  color: var(--gray);
  letter-spacing: 0.06em;
  margin-bottom: 7px;
}
.w-item {
  display: flex;
  gap: 7px;
  align-items: flex-start;
  padding: 6px 8px;
  background: #fcfaf5;
  border-left: 2px solid;
  border-radius: 0 3px 3px 0;
  margin-bottom: 5px;
}
.w-item b {
  font-size: 0.6rem;
  flex: 0 0 auto;
}
.w-item span {
  font-size: 0.62rem;
  color: var(--ink-soft);
  line-height: 1.6;
}
.w-none {
  font-size: 0.64rem;
  color: var(--gray-light);
}
.astro {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: 4px;
  overflow: hidden;
  margin-top: 14px;
}
.astro div {
  background: #fff;
  padding: 8px 10px;
}
.astro span {
  display: block;
  font-size: 0.56rem;
  color: var(--gray-light);
}
.astro b {
  display: block;
  font-family: var(--serif);
  font-size: 0.88rem;
  color: var(--forest-dark);
  margin-top: 2px;
}

.wx {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 20px 22px;
}
.now {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--line);
}
.now-k {
  font-size: 0.66rem;
  color: var(--gray);
  letter-spacing: 0.06em;
}
.now-t {
  font-family: var(--serif);
  font-size: 3.1rem;
  line-height: 1.1;
  color: var(--forest-dark);
  margin-top: 4px;
}
.now-t em {
  font-size: 1.1rem;
  font-style: normal;
  color: var(--forest-light);
  margin-left: 2px;
}
.now-t span {
  font-size: 1.1rem;
  color: var(--gray-light);
}
.now-c {
  font-size: 0.72rem;
  color: var(--ink-soft);
  margin-top: 4px;
}
.now-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 0.66rem;
  color: var(--gray);
  flex-wrap: wrap;
}
.now-bar i {
  width: 1px;
  height: 8px;
  background: var(--line);
}
.now-icon {
  font-size: 3.4rem;
  line-height: 1;
}
.strip {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 6px;
  margin-top: 16px;
}
.day {
  border: 1px solid var(--line);
  border-radius: 5px;
  background: #fff;
  padding: 9px 4px 8px;
  cursor: pointer;
  text-align: center;
  transition: 0.18s;
}
.day:hover {
  border-color: var(--forest-light);
}
.day.on {
  border-color: var(--forest);
  background: var(--forest-soft);
}
.day em {
  display: block;
  font-size: 0.6rem;
  font-style: normal;
  color: var(--gray);
}
.day .ic {
  display: block;
  font-size: 1.05rem;
  margin: 4px 0 3px;
}
.day b {
  display: block;
  font-family: var(--serif);
  font-size: 0.88rem;
  color: var(--ink);
}
.day i {
  display: block;
  font-size: 0.64rem;
  font-style: normal;
  color: var(--gray-light);
}
.day .rain,
.day .wind {
  display: block;
  font-size: 0.56rem;
  color: var(--gray-light);
  margin-top: 3px;
}
.day .rain.wet {
  color: #2f6f9e;
  font-weight: 600;
}
.detail {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 18px;
}
.d-card {
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 12px 13px;
  background: #fcfaf5;
}
.dc-t {
  font-size: 0.62rem;
  color: var(--gray);
  letter-spacing: 0.06em;
}
.dc-v {
  font-family: var(--serif);
  font-size: 0.95rem;
  color: var(--forest-dark);
  margin-top: 4px;
}
.dc-n {
  font-size: 0.64rem;
  color: var(--gray);
  line-height: 1.75;
  margin-top: 6px;
}
.tip-line {
  display: flex;
  gap: 8px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--line);
  font-size: 0.64rem;
  color: var(--gray);
  line-height: 1.75;
}
.tip-line b {
  flex: 0 0 auto;
  color: var(--forest);
  font-weight: 600;
}

@media (max-width: 1000px) {
  .cols {
    grid-template-columns: 1fr;
  }
  .picker {
    position: static;
  }
  .strip {
    grid-template-columns: repeat(4, 1fr);
  }
  .detail {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 600px) {
  .hd h1 {
    font-size: 1.36rem;
  }
  .now-t {
    font-size: 2.4rem;
  }
  .strip {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
