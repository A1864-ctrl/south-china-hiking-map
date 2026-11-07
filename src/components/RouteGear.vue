<script setup>
import { computed } from 'vue'
import { routeGear } from '../data/routeGear.js'
import { useGearStore } from '../stores/gear.js'

const props = defineProps({
  route: { type: Object, required: true }
})

const store = useGearStore()
const rg = computed(() => routeGear(props.route))
const ns = computed(() => `r${props.route.id}:`)
const keyOf = (it) => `${ns.value}${it.id}`
const keyOfExtra = (i) => `${ns.value}x${i}`

const allItems = computed(() => rg.value.groups.flatMap((g) => g.items))
const totalCount = computed(() => allItems.value.length + rg.value.extras.length)
const packedCount = computed(
  () =>
    allItems.value.filter((it) => store.isPacked(keyOf(it))).length +
    rg.value.extras.filter((x, i) => store.isPacked(keyOfExtra(i))).length
)
const percent = computed(() => (totalCount.value ? Math.round((packedCount.value / totalCount.value) * 100) : 0))
const requiredKeys = computed(() => [
  ...allItems.value.filter((it) => it.req).map(keyOf),
  ...rg.value.extras.map((x, i) => (x.req ? keyOfExtra(i) : null)).filter(Boolean)
])

function packRequired() {
  store.setMany(requiredKeys.value, true)
}
function reset() {
  store.clearPrefix(ns.value)
}
function printList() {
  window.print()
}
</script>

<template>
  <div class="rg">
    <!-- 顶部：这条线算出来的关键数字 -->
    <div class="rg-sum">
      <div class="cell">
        <em>场景判定</em>
        <b>{{ rg.scene }}</b>
      </div>
      <div class="cell">
        <em>预计行程</em>
        <b>{{ rg.stats.hours }}<i>h</i></b>
      </div>
      <div class="cell">
        <em>建议带水</em>
        <b>{{ rg.stats.water }}<i>L</i></b>
      </div>
      <div class="cell">
        <em>路餐份数</em>
        <b>{{ rg.stats.snacks }}<i>份</i></b>
      </div>
      <div class="cell">
        <em>背包容量</em>
        <b>{{ rg.stats.pack }}</b>
      </div>
      <div class="cell progress-cell">
        <em>已打包 {{ packedCount }} / {{ totalCount }}</em>
        <div class="mini-track"><i :style="{ width: percent + '%' }"></i></div>
      </div>
    </div>

    <!-- 这条线特有的提醒 -->
    <ul v-if="rg.warnings.length" class="rg-warn">
      <li v-for="w in rg.warnings" :key="w">{{ w }}</li>
    </ul>

    <!-- 分组清单 -->
    <div class="rg-groups">
      <section v-for="g in rg.groups" :key="g.group" class="rg-group">
        <h4>
          {{ g.group }}
          <span>{{ g.items.filter((it) => store.isPacked(keyOf(it))).length }}/{{ g.items.length }}</span>
        </h4>
        <ul>
          <li
            v-for="it in g.items"
            :key="it.id"
            :class="{ on: store.isPacked(keyOf(it)) }"
            @click="store.toggle(keyOf(it))"
          >
            <span class="box">
              <svg v-if="store.isPacked(keyOf(it))" viewBox="0 0 24 24" width="11" height="11">
                <path d="M4 12.5l5 5L20 6.5" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
            <span class="body">
              <span class="nm">{{ it.name }}<em v-if="it.req">必带</em></span>
              <span v-if="it.why" class="why">{{ it.why }}</span>
              <span v-else class="why muted">{{ it.note }}</span>
            </span>
          </li>
        </ul>
      </section>

      <section v-if="rg.extras.length" class="rg-group extra">
        <h4>
          这条线额外要带
          <span>{{ rg.extras.filter((x, i) => store.isPacked(keyOfExtra(i))).length }}/{{ rg.extras.length }}</span>
        </h4>
        <ul>
          <li
            v-for="(x, i) in rg.extras"
            :key="x.name"
            :class="{ on: store.isPacked(keyOfExtra(i)) }"
            @click="store.toggle(keyOfExtra(i))"
          >
            <span class="box">
              <svg v-if="store.isPacked(keyOfExtra(i))" viewBox="0 0 24 24" width="11" height="11">
                <path d="M4 12.5l5 5L20 6.5" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
            <span class="body">
              <span class="nm">{{ x.name }}<em v-if="x.req">必带</em></span>
              <span class="why">{{ x.why }}</span>
            </span>
          </li>
        </ul>
      </section>
    </div>

    <div class="rg-act">
      <button class="primary" @click="packRequired">勾上所有必带</button>
      <button class="ghost" @click="reset">清空本线路</button>
      <button class="ghost" @click="printList">打印</button>
      <router-link to="/gear" class="link">看完整 74 项装备清单 →</router-link>
    </div>
  </div>
</template>

<style scoped>
.rg {
  display: flex;
  flex-direction: column;
  gap: 13px;
}

.rg-sum {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
}

.cell {
  background: #fbf9f3;
  padding: 9px 11px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.cell em {
  font-style: normal;
  font-size: 0.66rem;
  color: var(--gray);
}

.cell b {
  font-size: 0.92rem;
  color: var(--forest-dark);
  font-weight: 700;
}

.cell b i {
  font-style: normal;
  font-size: 0.66rem;
  font-weight: 400;
  color: var(--gray);
  margin-left: 2px;
}

.progress-cell {
  justify-content: center;
}

.mini-track {
  height: 4px;
  border-radius: 99px;
  background: #e3ddcd;
  overflow: hidden;
}

.mini-track i {
  display: block;
  height: 100%;
  background: var(--forest-light);
  transition: width 0.25s;
}

.rg-warn {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.rg-warn li {
  font-size: 0.75rem;
  line-height: 1.7;
  color: #7a4a20;
  background: #fdf6ea;
  border-left: 3px solid var(--earth-light);
  border-radius: 0 7px 7px 0;
  padding: 7px 11px;
}

.rg-groups {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 11px;
  align-items: start;
}

.rg-group {
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}

.rg-group h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--forest-dark);
  background: #f7f5ee;
  padding: 8px 11px;
  border-bottom: 1px solid var(--line);
}

.rg-group h4 span {
  margin-left: auto;
  font-size: 0.68rem;
  font-weight: 400;
  color: var(--gray-light);
  font-variant-numeric: tabular-nums;
}

.rg-group.extra h4 {
  background: #f2f7f3;
}

.rg-group ul {
  list-style: none;
}

.rg-group li {
  display: flex;
  gap: 8px;
  padding: 8px 11px;
  cursor: pointer;
  border-top: 1px solid #f2efe6;
}

.rg-group li:first-child {
  border-top: none;
}

.rg-group li:hover {
  background: #fcfbf7;
}

.rg-group li.on {
  background: #f5f9f6;
}

.box {
  width: 15px;
  height: 15px;
  border: 1.5px solid #cfcabb;
  border-radius: 4px;
  flex-shrink: 0;
  margin-top: 1px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.rg-group li.on .box {
  background: var(--forest);
  border-color: var(--forest);
}

.body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.nm {
  font-size: 0.78rem;
  color: var(--ink);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.rg-group li.on .nm {
  color: var(--gray);
  text-decoration: line-through;
}

.nm em {
  font-style: normal;
  font-size: 0.6rem;
  padding: 0 4px;
  border-radius: 3px;
  color: var(--forest);
  background: var(--forest-soft);
}

.why {
  font-size: 0.7rem;
  line-height: 1.6;
  color: var(--gray);
}

.why.muted {
  color: var(--gray-light);
}

.rg-act {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
}

.rg-act button {
  font-size: 0.74rem;
  padding: 7px 13px;
  border-radius: 7px;
  cursor: pointer;
}

.primary {
  background: var(--forest);
  color: #fff;
  border: 1px solid var(--forest);
}

.ghost {
  background: #fff;
  border: 1px solid var(--line);
  color: var(--ink-soft);
}

.rg-act .link {
  margin-left: auto;
  font-size: 0.74rem;
  color: var(--forest);
  text-decoration: none;
}

@media (max-width: 1080px) {
  .rg-sum {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .rg-groups {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media print {
  .rg-act {
    display: none;
  }
}
</style>
