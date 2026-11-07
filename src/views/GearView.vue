<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { GEAR, GEAR_GROUPS, GROUP_DESC, SCENES } from '../data/gear.js'
import { matchLoose, haystack } from '../utils/search.js'
import { useGearStore } from '../stores/gear.js'

const store = useGearStore()
const route = useRoute()

const scene = ref('all')
// 支持 ?q=水 深链（也方便把某次搜索发给别人）
const keyword = ref(String(route.query.q || ''))
const onlyReq = ref(false)

const sceneCount = computed(() => {
  const m = { all: GEAR.length }
  SCENES.forEach((s) => {
    m[s.k] = GEAR.filter((it) => it.scenes.includes(s.k)).length
  })
  return m
})

const filtered = computed(() =>
  GEAR.filter((it) => {
    if (scene.value !== 'all' && !it.scenes.includes(scene.value)) return false
    if (onlyReq.value && !it.req) return false
    if (keyword.value.trim()) {
      if (!matchLoose(haystack(it.name, it.group, it.sub, it.note, it.scenes), keyword.value)) return false
    }
    return true
  })
)

const groups = computed(() =>
  GEAR_GROUPS.map((g) => {
    const items = filtered.value.filter((it) => it.group === g)
    return { group: g, desc: GROUP_DESC[g], items }
  }).filter((g) => g.items.length)
)

const keyOf = (it) => `g:${it.id}`
const keysOf = (items) => items.map(keyOf)
const packedCount = computed(() => store.countOf(filtered.value.map(keyOf)))
const percent = computed(() =>
  filtered.value.length ? Math.round((packedCount.value / filtered.value.length) * 100) : 0
)
const requiredLeft = computed(
  () => filtered.value.filter((it) => it.req && !store.isPacked(keyOf(it))).length
)

function allPacked(items) {
  return items.length > 0 && items.every((it) => store.isPacked(keyOf(it)))
}
function toggleGroup(items) {
  store.setMany(keysOf(items), !allPacked(items))
}
function reset() {
  store.clearPrefix('g:')
}
function printList() {
  window.print()
}
const reqOfScene = computed(() =>
  filtered.value.filter((it) => it.req).length
)
</script>

<template>
  <div class="gear-page">
    <header class="hero">
      <div class="hero-inner">
        <p class="kicker">EQUIPMENT CHECKLIST</p>
        <h1>户外徒步装备清单</h1>
        <p class="lede">
          按「着装、背负、宿营、行进、饮食、导航、急救、杂物」八大系统整理 <b>{{ GEAR.length }}</b> 项，
          分单日徒步 / 重装露营 / 长线高难度三种场景。勾选会存在本机浏览器，换设备不同步；
          每条路线的专属清单（含为什么带）在「徒步轨迹 → 选一条线 → 装备」里。
        </p>
        <router-link to="/gear-lab" class="lab-link">
          <span>已有装备按分类记账、按路线生成清单并和库存比对 →</span>
          <b>我的装备库</b>
        </router-link>
      </div>
    </header>

    <div class="bar-wrap">
      <div class="bar">
        <div class="tabs">
          <button :class="{ on: scene === 'all' }" @click="scene = 'all'">
            全部场景 <i>{{ sceneCount.all }}</i>
          </button>
          <button v-for="s in SCENES" :key="s.k" :class="{ on: scene === s.k }" @click="scene = s.k">
            {{ s.label }} <i>{{ sceneCount[s.k] }}</i>
          </button>
        </div>

        <label class="search">
          <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
            <circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" stroke-width="1.8" />
            <path d="M16 16l4.5 4.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
          </svg>
          <input v-model="keyword" type="search" placeholder="搜装备，输入一个字就能命中（例：水）" />
          <button v-if="keyword" class="clear" @click="keyword = ''">×</button>
        </label>

        <label class="switch">
          <input v-model="onlyReq" type="checkbox" />
          <span>只看必带</span>
        </label>
      </div>

      <div class="progress">
        <div class="prog-top">
          <span>已打包 <b>{{ packedCount }}</b> / {{ filtered.length }} 项</span>
          <span v-if="requiredLeft" class="left">还有 {{ requiredLeft }} 项必带没勾</span>
          <span v-else class="done">必带都齐了</span>
          <em>{{ percent }}%</em>
        </div>
        <div class="track"><i :style="{ width: percent + '%' }"></i></div>
      </div>
    </div>

    <main class="wrap">
      <p v-if="!groups.length" class="empty">没有匹配的装备，换个关键词或场景试试</p>

      <section v-for="g in groups" :key="g.group" class="group">
        <div class="g-top">
          <div>
            <h2>{{ g.group }}</h2>
            <p class="g-desc">{{ g.desc }}</p>
          </div>
          <div class="g-act">
            <span class="g-count">{{ g.items.filter((it) => store.isPacked(keyOf(it))).length }}/{{ g.items.length }}</span>
            <button @click="toggleGroup(g.items)">{{ allPacked(g.items) ? '取消全选' : '全选' }}</button>
          </div>
        </div>

        <ul class="items">
          <li
            v-for="it in g.items"
            :key="it.id"
            :class="{ on: store.isPacked(keyOf(it)) }"
            @click="store.toggle(keyOf(it))"
          >
            <span class="box">
              <svg v-if="store.isPacked(keyOf(it))" viewBox="0 0 24 24" width="13" height="13">
                <path d="M4 12.5l5 5L20 6.5" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
            <span class="txt">
              <span class="name">
                {{ it.name }}
                <em v-if="it.req" class="req">必带</em>
                <em v-if="it.sub" class="sub">{{ it.sub }}</em>
              </span>
              <span class="note">{{ it.note }}</span>
            </span>
          </li>
        </ul>
      </section>

      <div class="actions">
        <button class="primary" @click="printList">打印清单</button>
        <button class="ghost" @click="reset">重置勾选</button>
        <router-link to="/routes" class="link">去挑一条路线，看专属装备 →</router-link>
      </div>

      <p class="tip">
        装备只解决「带什么」，「怎么用」还得练：新鞋、新包、新炉头都在出发前用一次；
        南方山区多雨，防水做两遍（背包防雨罩 + 内部防水袋）比只做一遍靠谱。
      </p>
    </main>
  </div>
</template>

<style scoped>
.lab-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  padding: 7px 14px;
  border: 1px solid rgba(45, 90, 61, 0.28);
  border-radius: 999px;
  text-decoration: none;
  font-size: 0.72rem;
  color: var(--forest-dark);
  background: rgba(255, 255, 255, 0.6);
  transition: 0.18s;
}
.lab-link:hover {
  background: #fff;
  border-color: var(--forest);
}
.lab-link b {
  font-weight: 600;
  color: var(--forest);
}
.gear-page {
  padding-top: var(--nav-h);
  padding-bottom: 60px;
}

.hero {
  background: linear-gradient(160deg, #244634, #16281d);
  color: #fff;
  padding: 44px 0 38px;
}

.hero-inner {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 28px;
}

.kicker {
  font-family: var(--serif);
  font-size: 0.7rem;
  letter-spacing: 0.28em;
  color: var(--earth-light);
  margin-bottom: 10px;
}

.hero h1 {
  font-family: var(--serif);
  font-size: 2rem;
  letter-spacing: -0.01em;
}

.lede {
  margin-top: 12px;
  max-width: 780px;
  font-size: 0.86rem;
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.76);
}

.lede b {
  color: #fff;
}

.bar-wrap {
  position: sticky;
  top: var(--nav-h);
  z-index: 30;
  background: rgba(246, 242, 233, 0.95);
  backdrop-filter: saturate(180%) blur(12px);
  border-bottom: 1px solid var(--line);
}

.bar {
  max-width: 1180px;
  margin: 0 auto;
  padding: 12px 28px;
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.tabs {
  display: flex;
  gap: 3px;
  background: #eae4d6;
  border-radius: 9px;
  padding: 3px;
}

.tabs button {
  border: none;
  background: transparent;
  padding: 6px 11px;
  border-radius: 7px;
  font-size: 0.78rem;
  color: var(--ink-soft);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.tabs button i {
  font-style: normal;
  font-size: 0.68rem;
  color: var(--gray-light);
}

.tabs button.on {
  background: #fff;
  color: var(--forest-dark);
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}

.tabs button.on i {
  color: var(--forest-light);
}

.search {
  flex: 1;
  min-width: 200px;
  display: flex;
  align-items: center;
  gap: 7px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 0 10px;
  height: 34px;
  color: var(--gray-light);
}

.search input {
  border: none;
  outline: none;
  flex: 1;
  font-size: 0.8rem;
  background: transparent;
  color: var(--ink);
}

.clear {
  border: none;
  background: transparent;
  color: var(--gray-light);
  font-size: 1rem;
  cursor: pointer;
  line-height: 1;
}

.switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.78rem;
  color: var(--ink-soft);
  cursor: pointer;
  white-space: nowrap;
}

.switch input {
  accent-color: var(--forest);
  width: 15px;
  height: 15px;
}

.progress {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 28px 12px;
}

.prog-top {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.74rem;
  color: var(--gray);
  margin-bottom: 6px;
}

.prog-top b {
  color: var(--forest-dark);
}

.prog-top .left {
  color: var(--earth);
}

.prog-top .done {
  color: var(--forest-light);
}

.prog-top em {
  margin-left: auto;
  font-style: normal;
  font-variant-numeric: tabular-nums;
  color: var(--forest-dark);
  font-weight: 600;
}

.track {
  height: 5px;
  border-radius: 99px;
  background: #e7e1d3;
  overflow: hidden;
}

.track i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--forest-light), var(--forest));
  transition: width 0.25s ease;
}

.wrap {
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px 28px 0;
}

.group {
  border: 1px solid var(--line);
  border-radius: 13px;
  background: #fff;
  margin-bottom: 14px;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.g-top {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 15px 18px 13px;
  border-bottom: 1px solid var(--line);
  background: linear-gradient(180deg, #fbf9f3, #fff);
}

.g-top h2 {
  font-family: var(--serif);
  font-size: 1rem;
  color: var(--forest-dark);
}

.g-desc {
  margin-top: 4px;
  font-size: 0.73rem;
  line-height: 1.7;
  color: var(--gray);
  max-width: 780px;
}

.g-act {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 9px;
  flex-shrink: 0;
}

.g-count {
  font-size: 0.72rem;
  color: var(--gray-light);
  font-variant-numeric: tabular-nums;
}

.g-act button {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--forest);
  font-size: 0.7rem;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
}

.g-act button:hover {
  border-color: var(--forest-light);
  background: var(--forest-soft);
}

.items {
  list-style: none;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  background: var(--line);
}

.items li {
  display: flex;
  gap: 10px;
  padding: 11px 16px;
  background: #fff;
  cursor: pointer;
  transition: background 0.15s;
}

.items li:hover {
  background: #fbfaf6;
}

.items li.on {
  background: #f4f8f5;
}

.box {
  width: 17px;
  height: 17px;
  border-radius: 5px;
  border: 1.5px solid #cfcabb;
  flex-shrink: 0;
  margin-top: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  transition: all 0.15s;
}

.items li.on .box {
  background: var(--forest);
  border-color: var(--forest);
}

.txt {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.name {
  font-size: 0.82rem;
  color: var(--ink);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.items li.on .name {
  color: var(--gray);
  text-decoration: line-through;
  text-decoration-color: #c9d3cb;
}

.req {
  font-style: normal;
  font-size: 0.62rem;
  padding: 0 5px;
  border-radius: 3px;
  color: var(--forest);
  background: var(--forest-soft);
  border: 1px solid rgba(45, 90, 61, 0.16);
}

.sub {
  font-style: normal;
  font-size: 0.62rem;
  color: var(--gray-light);
}

.note {
  font-size: 0.72rem;
  line-height: 1.65;
  color: var(--gray);
}

.empty {
  padding: 40px 0;
  text-align: center;
  color: var(--gray-light);
  font-size: 0.84rem;
}

.actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 18px;
}

.actions button,
.actions .link {
  font-size: 0.78rem;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  text-decoration: none;
}

.primary {
  background: var(--forest);
  color: #fff;
  border: 1px solid var(--forest);
}

.ghost {
  background: #fff;
  color: var(--ink-soft);
  border: 1px solid var(--line);
}

.actions .link {
  margin-left: auto;
  color: var(--forest);
  padding: 8px 0;
}

.tip {
  margin-top: 18px;
  font-size: 0.76rem;
  line-height: 1.9;
  color: var(--gray);
  background: #f4f1e7;
  border-radius: 10px;
  padding: 13px 16px;
}

@media (max-width: 900px) {
  .items {
    grid-template-columns: minmax(0, 1fr);
  }
  .hero h1 {
    font-size: 1.55rem;
  }
  .bar {
    padding: 10px 16px;
  }
  .progress,
  .wrap {
    padding-left: 16px;
    padding-right: 16px;
  }
}

@media print {
  .bar-wrap,
  .hero,
  .actions,
  .tip {
    display: none;
  }
  .gear-page {
    padding: 0;
  }
  .wrap {
    padding: 0;
  }
  .group {
    break-inside: avoid;
    box-shadow: none;
  }
  .items li.on .name {
    text-decoration: none;
  }
}
</style>
