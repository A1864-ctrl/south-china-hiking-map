<script setup>
/**
 * 装备库 + 智能装备清单
 * 左边管理自己的装备（分类 / 重量 / 是否已拥有）
 * 右边按路线难度生成清单，逐项和装备库比对，可保存
 */
import { computed, onMounted, ref } from 'vue'
import { routes } from '../data/routes.js'
import { routeGear } from '../data/routeGear.js'
import { GEAR_CATS, useFieldStore } from '../stores/field.js'
import { useAuthStore } from '../stores/auth.js'
import { useUiStore } from '../stores/ui.js'

const field = useFieldStore()
const auth = useAuthStore()
const ui = useUiStore()

onMounted(() => {
  auth.ensureFresh()
  field.ensureGear()
})

/* ── 装备库 ── */
const byCat = computed(() => field.gearByCat())
const ownedCount = computed(() => field.myGear.filter((g) => g.owned).length)
const totalWeight = computed(() => field.gearWeight())
const catName = (k) => (GEAR_CATS.find((c) => c.k === k) || {}).name || '其他'

const adding = ref(false)
const nf = ref({ name: '', cat: 'wear', weight: 300, count: 1 })
function addItem() {
  if (!nf.value.name.trim()) return ui.toast('写个名字')
  field.addGear({ ...nf.value })
  nf.value = { name: '', cat: nf.value.cat, weight: 300, count: 1 }
  adding.value = false
  ui.toast('已加入装备库')
}

/* ── 智能清单 ── */
const routeId = ref(routes.find((r) => r.id === 46)?.id || routes[0].id)
const cur = computed(() => routes.find((r) => r.id === Number(routeId.value)) || routes[0])
const plan = computed(() => routeGear(cur.value))

/* 估算重量：按同类装备常见重量，逐项匹配关键词 */
const W = [
  [/帐篷|双人帐/, 2000], [/睡袋/, 900], [/睡垫|防潮垫/, 450], [/背包|格里高利/, 1250],
  [/冲锋衣|硬壳/, 420], [/抓绒|羽绒/, 480], [/速干|长袖|短裤|内裤/, 180], [/徒步袜|袜/, 60],
  [/鞋|靴/, 700], [/头灯/, 130], [/急救/, 300], [/水袋|水壶/, 140], [/炉头/, 300],
  [/气罐/, 230], [/锅|杯/, 150], [/登山杖/, 240], [/雨衣|雨披/, 250], [/手套/, 80],
  [/帽|头巾/, 70], [/墨镜|眼镜/, 40], [/防晒/, 50], [/充电宝|电源/, 220],
  [/对讲/, 250], [/哨/, 20], [/毯/, 60], [/绳/, 180], [/地图|导航/, 60]
]
function est(name) {
  for (const [re, w] of W) if (re.test(name)) return w
  return 150
}

/* 清单所有条目（分组 + 路线专属加项） */
const planItems = computed(() => {
  const out = []
  for (const g of plan.value.groups) {
    for (const it of g.items) out.push({ name: it.name, group: g.group, req: it.req, why: it.why, w: est(it.name) })
  }
  for (const x of plan.value.extras) out.push({ name: x.name, group: '这条线专属', req: x.req, why: x.why, w: est(x.name) })
  return out
})

/* 参考重量只算「必备」项 + 路线专属必备，避免把可选装备全算进去 */
const planWeight = computed(() =>
  planItems.value.filter((i) => i.req).reduce((a, i) => a + i.w, 0)
)
const fullWeight = computed(() => planItems.value.reduce((a, i) => a + i.w, 0))

/* 和装备库比对：名字互相包含算「已有」 */
const myNames = computed(() => field.myGear.map((g) => g.name))
function have(name) {
  return myNames.value.some((n) => n.includes(name.slice(0, 4)) || name.includes(n.slice(0, 4)))
}
const missing = computed(() => planItems.value.filter((i) => i.req && !have(i.name)))
const covered = computed(() => planItems.value.filter((i) => have(i.name)).length)

/* 保存清单 */
const listName = ref('')
function save() {
  if (!auth.isLogged) return auth.openDialog('login')
  const name = listName.value.trim() || `${cur.value.name} · ${plan.value.stats.days}天`
  field.saveList({
    name,
    routeId: cur.value.id,
    items: planItems.value.map((i) => ({ name: i.name, cat: i.group, weight: i.w })),
    baseWeight: planWeight.value
  })
  listName.value = ''
  ui.toast('清单已保存')
}

const openList = ref('')
const kg = (g) => (g / 1000).toFixed(2) + ' kg'
</script>

<template>
  <div class="page">
    <div class="container">
      <header class="hd">
        <div>
          <p class="k">GEAR LIBRARY · 装备库</p>
          <h1>先盘点柜子，再决定买什么</h1>
          <p class="d">
            把已有的装备按分类记下来，重量也记上——很多「必备清单」之所以背不动，是因为根本不知道包里到底多少斤。
            右边按路线天数、爬升、地貌自动生成清单，并逐项告诉你哪些已经有了、哪些还得借或买。
          </p>
        </div>
        <div class="stats">
          <div><b>{{ field.myGear.length }}</b><span>装备条目</span></div>
          <div><b>{{ ownedCount }}</b><span>已拥有</span></div>
          <div><b>{{ (totalWeight / 1000).toFixed(2) }}</b><span>背包重量 kg</span></div>
        </div>
      </header>

      <div class="cols">
        <!-- 左：装备库 -->
        <section class="panel lib">
          <div class="p-head">
            <h2>我的装备库</h2>
            <button class="link" @click="adding = !adding">{{ adding ? '收起' : '+ 添加' }}</button>
          </div>

          <div v-if="adding" class="add">
            <input v-model="nf.name" maxlength="20" placeholder="装备名称，例：三季双人帐" />
            <div class="add-row">
              <select v-model="nf.cat">
                <option v-for="c in GEAR_CATS" :key="c.k" :value="c.k">{{ c.name }}</option>
              </select>
              <input v-model.number="nf.weight" type="number" min="0" max="9999" placeholder="克" />
              <input v-model.number="nf.count" type="number" min="1" max="9" placeholder="数量" />
            </div>
            <button class="primary sm" @click="addItem">加入</button>
          </div>

          <div v-for="c in GEAR_CATS" :key="c.k" class="cat-block">
            <template v-if="byCat[c.k] && byCat[c.k].length">
              <p class="c-name">
                <span class="dot" :style="{ background: c.tone }"></span>{{ c.name }}
                <em>{{ byCat[c.k].filter((g) => g.owned).length }}/{{ byCat[c.k].length }}</em>
              </p>
              <div v-for="g in byCat[c.k]" :key="g.id" class="gear" :class="{ off: !g.owned }">
                <button class="tick" :class="{ on: g.owned }" @click="field.toggleOwned(g.id)">
                  <svg v-if="g.owned" viewBox="0 0 24 24" width="11" height="11">
                    <path d="M5 12.5l4.5 4.5L19 7" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                </button>
                <div class="g-name">
                  {{ g.name }}
                  <em v-if="g.count > 1">×{{ g.count }}</em>
                </div>
                <span class="g-w">{{ g.weight * (g.count || 1) }} g</span>
                <button class="del" title="删除" @click="field.removeGear(g.id)">×</button>
              </div>
            </template>
          </div>

          <p class="lib-tip">
            勾选表示「我已经有」。重量按单件记，数量会一起算进总重。
          </p>
        </section>

        <!-- 右：智能清单 -->
        <section class="panel plan">
          <div class="p-head">
            <h2>智能装备清单</h2>
            <span class="scene">{{ plan.scene }}</span>
          </div>

          <div class="route-pick">
            <select v-model="routeId">
              <option v-for="r in routes" :key="r.id" :value="r.id">{{ r.name }}</option>
            </select>
            <p class="rp-meta">
              {{ cur.distance }}km · ↑{{ cur.climb }}m · {{ cur.days }} · {{ cur.terrain }}
            </p>
          </div>

          <div class="facts">
            <div><span>背包容量</span><b>{{ plan.stats.pack }}</b></div>
            <div><span>建议带水</span><b>{{ plan.stats.water }} L</b></div>
            <div><span>路餐</span><b>{{ plan.stats.snacks }} 份</b></div>
            <div><span>必备总重</span><b>{{ kg(planWeight) }}</b></div>
          </div>

          <div class="match">
            <span>装备库覆盖 <b>{{ covered }}</b> / {{ planItems.length }} 项</span>
            <span v-if="missing.length" class="miss">还缺 {{ missing.length }} 项必备</span>
            <span v-else class="ok">必备项都齐了</span>
          </div>

          <div v-if="plan.warnings.length" class="warn">
            <p v-for="w in plan.warnings" :key="w">{{ w }}</p>
          </div>

          <div class="groups">
            <div v-for="g in plan.groups" :key="g.group" class="group">
              <p class="g-head">
                {{ g.group }} <em>{{ g.items.length }}</em>
              </p>
              <div v-for="it in g.items" :key="it.name" class="item" :class="{ has: have(it.name), req: it.req }">
                <span class="i-mark">{{ have(it.name) ? '✓' : it.req ? '!' : '·' }}</span>
                <div>
                  <p class="i-name">{{ it.name }}<em v-if="it.req">必备</em></p>
                  <p v-if="it.why" class="i-why">{{ it.why }}</p>
                </div>
                <span class="i-w">{{ est(it.name) }}g</span>
              </div>
            </div>

            <div v-if="plan.extras.length" class="group">
              <p class="g-head">这条线专属 <em>{{ plan.extras.length }}</em></p>
              <div v-for="it in plan.extras" :key="it.name" class="item" :class="{ has: have(it.name), req: it.req }">
                <span class="i-mark">{{ have(it.name) ? '✓' : it.req ? '!' : '·' }}</span>
                <div>
                  <p class="i-name">{{ it.name }}<em v-if="it.req">必备</em></p>
                  <p v-if="it.why" class="i-why">{{ it.why }}</p>
                </div>
                <span class="i-w">{{ est(it.name) }}g</span>
              </div>
            </div>
          </div>

          <div class="save">
            <input v-model="listName" maxlength="24" :placeholder="`${cur.name} · ${plan.stats.days}天`" />
            <button class="primary sm" @click="save">保存这份清单</button>
          </div>

          <div v-if="field.myLists.length" class="saved">
            <p class="s-head">已保存的清单 {{ field.myLists.length }}</p>
            <div v-for="l in field.myLists" :key="l.id" class="s-row">
              <button class="s-main" @click="openList = openList === l.id ? '' : l.id">
                <b>{{ l.name }}</b>
                <em>{{ l.items.length }} 项 · 约 {{ (l.base / 1000).toFixed(2) }} kg · {{ l.routeName }}</em>
              </button>
              <button class="del" @click="field.removeList(l.id)">×</button>
              <div v-if="openList === l.id" class="s-items">
                <span v-for="i in l.items" :key="i.name">{{ i.name }}</span>
              </div>
            </div>
          </div>

          <p class="plan-tip">
            必备项合计约 {{ kg(planWeight) }}，全部列出项约 {{ kg(fullWeight) }}；重量按同类装备常见克重估算，
            把装备库里的真实重量填准会更准。
          </p>
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
  gap: 26px;
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
  max-width: 660px;
  margin-top: 8px;
}
.stats {
  display: flex;
  gap: 24px;
}
.stats div {
  text-align: right;
}
.stats b {
  display: block;
  font-family: var(--serif);
  font-size: 1.42rem;
  color: var(--forest-dark);
}
.stats span {
  font-size: 0.62rem;
  color: var(--gray);
}
.cols {
  display: grid;
  grid-template-columns: 330px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}
.panel {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 18px 20px;
}
.lib {
  position: sticky;
  top: calc(var(--nav-h) + 18px);
  max-height: calc(100vh - var(--nav-h) - 40px);
  overflow: auto;
}
.p-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 8px;
}
.p-head h2 {
  font-family: var(--serif);
  font-size: 0.96rem;
  font-weight: 600;
  color: var(--ink);
}
.link {
  border: none;
  background: none;
  font-size: 0.66rem;
  color: var(--forest);
  cursor: pointer;
}
.scene {
  font-size: 0.6rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--forest-soft);
  color: var(--forest);
}
.add {
  padding: 9px 10px;
  background: #fcfaf5;
  border: 1px dashed var(--line);
  border-radius: 4px;
  margin-bottom: 8px;
}
.add input,
.add select {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 3px;
  padding: 6px 8px;
  font-size: 0.72rem;
  background: #fff;
  color: var(--ink);
  outline: none;
  font-family: inherit;
}
.add-row {
  display: grid;
  grid-template-columns: 1.2fr 1fr 0.8fr;
  gap: 5px;
  margin: 5px 0 7px;
}
.add .primary.sm {
  width: 100%;
}
.cat-block {
  margin-top: 9px;
}
.c-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.64rem;
  color: var(--gray);
  letter-spacing: 0.06em;
  padding: 5px 0 4px;
}
.c-name .dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}
.c-name em {
  margin-left: auto;
  font-style: normal;
  font-size: 0.56rem;
  color: var(--gray-light);
}
.gear {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 0;
  border-bottom: 1px solid rgba(230, 225, 214, 0.55);
}
.gear.off {
  opacity: 0.62;
}
.gear.off .g-name {
  color: var(--gray);
}
.tick {
  flex: 0 0 auto;
  width: 15px;
  height: 15px;
  border: 1px solid var(--line);
  border-radius: 3px;
  background: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  padding: 0;
}
.tick.on {
  background: var(--forest);
  border-color: var(--forest);
}
.g-name {
  flex: 1;
  font-size: 0.7rem;
  color: var(--ink-soft);
  line-height: 1.4;
}
.g-name em {
  font-style: normal;
  color: var(--gray-light);
  font-size: 0.6rem;
  margin-left: 3px;
}
.g-w {
  font-size: 0.58rem;
  color: var(--gray-light);
  font-family: var(--mono, ui-monospace, monospace);
}
.del {
  border: none;
  background: none;
  color: var(--gray-light);
  font-size: 0.85rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 2px;
}
.del:hover {
  color: #a9462f;
}
.lib-tip {
  font-size: 0.58rem;
  color: var(--gray-light);
  line-height: 1.7;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--line);
}

.route-pick {
  margin-top: 10px;
}
.route-pick select {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 7px 9px;
  font-size: 0.76rem;
  background: #fcfaf5;
  color: var(--ink);
  outline: none;
  font-family: inherit;
}
.rp-meta {
  font-size: 0.62rem;
  color: var(--gray);
  margin-top: 5px;
}
.facts {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border: 1px solid var(--line);
  border-radius: 4px;
  margin-top: 12px;
  overflow: hidden;
}
.facts div {
  padding: 8px 10px;
  border-right: 1px solid var(--line);
}
.facts div:last-child {
  border-right: none;
}
.facts span {
  display: block;
  font-size: 0.56rem;
  color: var(--gray-light);
}
.facts b {
  display: block;
  font-family: var(--serif);
  font-size: 0.86rem;
  color: var(--forest-dark);
  margin-top: 2px;
}
.match {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 10px;
  font-size: 0.66rem;
  color: var(--gray);
}
.match b {
  color: var(--forest-dark);
}
.match .miss {
  color: #a9462f;
}
.match .ok {
  color: var(--forest);
}
.warn {
  margin-top: 10px;
  padding: 9px 11px;
  background: #fdf7e8;
  border: 1px dashed #e3d3a8;
  border-radius: 4px;
}
.warn p {
  font-size: 0.64rem;
  color: #6b5320;
  line-height: 1.8;
  position: relative;
  padding-left: 11px;
}
.warn p::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #a97a17;
}
.groups {
  margin-top: 14px;
}
.group {
  margin-bottom: 12px;
}
.g-head {
  font-size: 0.64rem;
  color: var(--gray);
  letter-spacing: 0.06em;
  padding-bottom: 5px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 4px;
}
.g-head em {
  font-style: normal;
  color: var(--gray-light);
  font-size: 0.56rem;
  margin-left: 4px;
}
.item {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  padding: 5px 0;
}
.i-mark {
  flex: 0 0 auto;
  width: 13px;
  height: 13px;
  border-radius: 50%;
  font-size: 0.52rem;
  line-height: 13px;
  text-align: center;
  margin-top: 2px;
  background: var(--cream);
  color: var(--gray-light);
}
.item.has .i-mark {
  background: var(--forest-soft);
  color: var(--forest);
}
.item.req:not(.has) .i-mark {
  background: #f7eae7;
  color: #a9462f;
}
.item > div {
  flex: 1;
  min-width: 0;
}
.i-name {
  font-size: 0.72rem;
  color: var(--ink-soft);
  line-height: 1.5;
}
.i-name em {
  font-style: normal;
  font-size: 0.52rem;
  color: #a9462f;
  border: 1px solid #e7cdc7;
  border-radius: 2px;
  padding: 0 3px;
  margin-left: 5px;
  vertical-align: 1px;
}
.i-why {
  font-size: 0.6rem;
  color: var(--gray-light);
  line-height: 1.65;
  margin-top: 1px;
}
.i-w {
  flex: 0 0 auto;
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.56rem;
  color: var(--gray-light);
  padding-top: 3px;
}
.save {
  display: flex;
  gap: 8px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}
.save input {
  flex: 1;
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 7px 10px;
  font-size: 0.72rem;
  background: #fcfaf5;
  color: var(--ink);
  outline: none;
}
.primary.sm {
  border: none;
  background: var(--forest);
  color: #fff;
  border-radius: 4px;
  font-size: 0.7rem;
  padding: 7px 14px;
  cursor: pointer;
  white-space: nowrap;
}
.primary.sm:hover {
  background: var(--forest-dark);
}
.saved {
  margin-top: 14px;
  padding-top: 11px;
  border-top: 1px dashed var(--line);
}
.s-head {
  font-size: 0.62rem;
  color: var(--gray);
  letter-spacing: 0.06em;
  margin-bottom: 6px;
}
.s-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 0;
  border-bottom: 1px solid rgba(230, 225, 214, 0.55);
  flex-wrap: wrap;
}
.s-main {
  flex: 1;
  text-align: left;
  border: none;
  background: none;
  cursor: pointer;
  padding: 0;
}
.s-main b {
  display: block;
  font-size: 0.72rem;
  color: var(--ink);
  font-weight: 600;
}
.s-main em {
  display: block;
  font-size: 0.58rem;
  font-style: normal;
  color: var(--gray);
  margin-top: 2px;
}
.s-items {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 5px 0 2px;
}
.s-items span {
  font-size: 0.56rem;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--cream);
  color: var(--gray);
}
.plan-tip {
  font-size: 0.58rem;
  color: var(--gray-light);
  line-height: 1.7;
  margin-top: 12px;
}

@media (max-width: 980px) {
  .cols {
    grid-template-columns: 1fr;
  }
  .lib {
    position: static;
    max-height: none;
  }
  .hd h1 {
    font-size: 1.4rem;
  }
}
</style>
