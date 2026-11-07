<script setup>
/**
 * 营地独立库
 * 五项硬信息（明火 / 水源 / 厕所 / 收费 / 过夜权限）做成可筛选的图标行
 */
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { camps, campStats } from '../data/camps.js'

const router = useRouter()

const fire = ref('全部')
const night = ref('全部')
const onlyWater = ref(false)
const onlyToilet = ref(false)
const onlyFree = ref(false)
const sort = ref('ele')

const list = computed(() => {
  let l = camps.slice()
  if (fire.value !== '全部')
    l = l.filter((c) => (fire.value === '可明火' ? c.fire === '允许' || c.fire === '限指定区域' : c.fire === fire.value))
  if (night.value !== '全部') l = l.filter((c) => c.night === night.value)
  if (onlyWater.value) l = l.filter((c) => !c.water.startsWith('无'))
  if (onlyToilet.value) l = l.filter((c) => c.toilet !== '无')
  if (onlyFree.value) l = l.filter((c) => c.fee === '免费')
  if (sort.value === 'ele') l.sort((a, b) => b.ele - a.ele)
  else if (sort.value === 'cap') l.sort((a, b) => b.cap - a.cap)
  return l
})

const activeCount = computed(
  () =>
    (fire.value !== '全部' ? 1 : 0) +
    (night.value !== '全部' ? 1 : 0) +
    (onlyWater.value ? 1 : 0) +
    (onlyToilet.value ? 1 : 0) +
    (onlyFree.value ? 1 : 0)
)

function reset() {
  fire.value = '全部'
  night.value = '全部'
  onlyWater.value = false
  onlyToilet.value = false
  onlyFree.value = false
}

const fireTone = (f) => (f === '允许' ? '#2d5a3d' : f === '限指定区域' ? '#8a6d2f' : '#a9462f')
const nightTone = (n) => (n === '可过夜' ? '#2d5a3d' : n === '禁止过夜' ? '#a9462f' : '#8a6d2f')
</script>

<template>
  <div class="page">
    <div class="container">
      <header class="hd">
        <div>
          <p class="k">CAMPSITES · 营地独立库</p>
          <h1>今晚睡哪，先看这五件事</h1>
          <p class="d">
            营地是徒步里最容易出事的一环：能不能生火、有没有水、要不要钱、允不允许过夜——任何一项判断错，轻则被赶下山，重则失温。
            下面每一处营地的坐标都取自对应路线的真实途经点，不是估的。
          </p>
        </div>
        <div class="stats">
          <div><b>{{ campStats.total }}</b><span>处营地</span></div>
          <div><b>{{ campStats.nightOk }}</b><span>可过夜</span></div>
          <div><b>{{ campStats.water }}</b><span>有水源</span></div>
          <div><b>{{ campStats.free }}</b><span>免费</span></div>
        </div>
      </header>

      <div class="filters">
        <div class="fgroup">
          <span class="fl">明火</span>
          <button :class="{ on: fire === '全部' }" @click="fire = '全部'">全部</button>
          <button :class="{ on: fire === '可明火' }" @click="fire = '可明火'">允许 / 限区</button>
          <button :class="{ on: fire === '禁止' }" @click="fire = '禁止'">禁止</button>
        </div>
        <div class="fgroup">
          <span class="fl">过夜</span>
          <button :class="{ on: night === '全部' }" @click="night = '全部'">全部</button>
          <button :class="{ on: night === '可过夜' }" @click="night = '可过夜'">可过夜</button>
          <button :class="{ on: night === '需报备' }" @click="night = '需报备'">需报备</button>
          <button :class="{ on: night === '禁止过夜' }" @click="night = '禁止过夜'">禁止</button>
          <button :class="{ on: night === '限指定营地' }" @click="night = '限指定营地'">限指定</button>
        </div>
        <div class="fgroup">
          <button class="tog" :class="{ on: onlyWater }" @click="onlyWater = !onlyWater">必须有水源</button>
          <button class="tog" :class="{ on: onlyToilet }" @click="onlyToilet = !onlyToilet">有厕所</button>
          <button class="tog" :class="{ on: onlyFree }" @click="onlyFree = !onlyFree">免费</button>
        </div>
        <div class="fgroup right">
          <span class="fl">排序</span>
          <button :class="{ on: sort === 'ele' }" @click="sort = 'ele'">海拔</button>
          <button :class="{ on: sort === 'cap' }" @click="sort = 'cap'">容量</button>
          <button v-if="activeCount" class="clear" @click="reset">清空 {{ activeCount }}</button>
        </div>
      </div>

      <p class="count">共 {{ list.length }} 处 · 按{{ sort === 'ele' ? '海拔从高到低' : '容量从大到小' }}排列</p>

      <div class="grid">
        <article v-for="c in list" :key="c.id" class="camp">
          <figure @click="router.push(`/route/${c.rid}?tab=live&from=camps`)">
            <img v-if="c.photo" :src="c.photo" :alt="c.name" loading="lazy" />
            <span class="ele">{{ c.ele }} m</span>
            <span class="kind">{{ c.kind }}</span>
          </figure>
          <div class="c-body">
            <div class="c-top">
              <h3>{{ c.name }}</h3>
              <span class="cap" v-if="c.cap">可容 {{ c.cap }} 顶</span>
            </div>
            <p class="c-route" @click="router.push(`/route/${c.rid}?tab=live&from=camps`)">
              {{ c.routeName }} · {{ c.city }} →
            </p>

            <dl class="attrs">
              <div>
                <dt>明火</dt>
                <dd :style="{ color: fireTone(c.fire) }">{{ c.fire }}</dd>
              </div>
              <div>
                <dt>水源</dt>
                <dd :class="{ none: c.water.startsWith('无') }">{{ c.water }}</dd>
              </div>
              <div>
                <dt>厕所</dt>
                <dd :class="{ none: c.toilet === '无' }">{{ c.toilet }}</dd>
              </div>
              <div>
                <dt>收费</dt>
                <dd>{{ c.fee }}</dd>
              </div>
              <div class="wide">
                <dt>过夜</dt>
                <dd :style="{ color: nightTone(c.night) }">{{ c.night }}</dd>
              </div>
            </dl>

            <p class="c-note">{{ c.note }}</p>
            <div class="c-tags">
              <span v-for="t in c.tags" :key="t">{{ t }}</span>
            </div>
          </div>
        </article>
      </div>

      <p v-if="!list.length" class="empty">没有同时满足这些条件的营地，放宽一项试试。</p>

      <div class="foot">
        <p class="f-t">数据说明</p>
        <p>
          营地坐标取自对应路线的途经点（WGS84），海拔为轨迹点海拔；「明火 / 过夜」以保护区与景区公开规定为准，
          但规定会变，出发前请再看一眼当地公告。标「禁止过夜」的营地只作为休息点收录，不是推荐扎营。
        </p>
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
  gap: 22px;
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

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
  align-items: center;
  padding: 12px 14px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
}
.fgroup {
  display: flex;
  align-items: center;
  gap: 5px;
}
.fgroup.right {
  margin-left: auto;
}
.fl {
  font-size: 0.62rem;
  color: var(--gray-light);
  letter-spacing: 0.08em;
  margin-right: 2px;
}
.fgroup button {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 3px;
  font-size: 0.66rem;
  padding: 4px 9px;
  color: var(--ink-soft);
  cursor: pointer;
  transition: 0.16s;
}
.fgroup button:hover {
  border-color: var(--forest-light);
  color: var(--forest);
}
.fgroup button.on {
  background: var(--forest);
  border-color: var(--forest);
  color: #fff;
}
.fgroup button.tog.on {
  background: var(--forest-soft);
  border-color: var(--forest-light);
  color: var(--forest-dark);
}
.fgroup button.clear {
  color: #a9462f;
  border-color: #e0c5be;
}
.count {
  font-size: 0.64rem;
  color: var(--gray);
  margin: 10px 2px 12px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.camp {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: 0.2s;
}
.camp:hover {
  box-shadow: 0 8px 20px rgba(30, 61, 41, 0.09);
  border-color: #d8d2c2;
}
.camp figure {
  position: relative;
  margin: 0;
  cursor: pointer;
  overflow: hidden;
}
.camp img {
  width: 100%;
  height: 132px;
  object-fit: cover;
  display: block;
  background: var(--cream-dark);
  transition: transform 0.4s;
}
.camp:hover img {
  transform: scale(1.03);
}
.ele {
  position: absolute;
  left: 8px;
  bottom: 8px;
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.58rem;
  padding: 2px 6px;
  border-radius: 2px;
  background: rgba(16, 26, 19, 0.66);
  color: #eee6d3;
  letter-spacing: 0.06em;
}
.kind {
  position: absolute;
  right: 8px;
  top: 8px;
  font-size: 0.56rem;
  padding: 2px 6px;
  border-radius: 2px;
  background: rgba(246, 242, 233, 0.9);
  color: #4a4a42;
}
.c-body {
  padding: 12px 14px 14px;
  flex: 1;
  display: flex;
  flex-direction: column;
}
.c-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.c-top h3 {
  font-family: var(--serif);
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.4;
}
.cap {
  flex: 0 0 auto;
  font-size: 0.56rem;
  color: var(--gray-light);
}
.c-route {
  font-size: 0.64rem;
  color: var(--forest);
  margin-top: 3px;
  cursor: pointer;
}
.c-route:hover {
  text-decoration: underline;
}
.attrs {
  margin: 10px 0 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  border-top: 1px solid var(--line);
}
.attrs > div {
  display: flex;
  align-items: baseline;
  gap: 5px;
  padding: 5px 0;
  border-bottom: 1px solid rgba(230, 225, 214, 0.6);
}
.attrs > div:nth-child(odd) {
  padding-right: 8px;
}
.attrs > div.wide {
  grid-column: 1 / -1;
  border-bottom: none;
}
.attrs dt {
  font-size: 0.58rem;
  color: var(--gray-light);
  flex: 0 0 26px;
  letter-spacing: 0.04em;
}
.attrs dd {
  margin: 0;
  font-size: 0.66rem;
  color: var(--ink-soft);
  line-height: 1.5;
}
.attrs dd.none {
  color: var(--gray-light);
}
.c-note {
  font-size: 0.64rem;
  color: var(--gray);
  line-height: 1.75;
  margin-top: 9px;
  flex: 1;
}
.c-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}
.c-tags span {
  font-size: 0.54rem;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--forest-soft);
  color: var(--forest);
}
.empty {
  padding: 40px 0;
  text-align: center;
  font-size: 0.76rem;
  color: var(--gray);
}
.foot {
  margin-top: 22px;
  padding: 14px 16px;
  background: #fcfaf5;
  border: 1px solid var(--line);
  border-radius: 5px;
}
.f-t {
  font-size: 0.64rem;
  color: var(--ink);
  font-weight: 600;
  margin-bottom: 5px;
}
.foot p:last-child {
  font-size: 0.62rem;
  color: var(--gray);
  line-height: 1.9;
}

@media (max-width: 1100px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 700px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .hd h1 {
    font-size: 1.4rem;
  }
  .fgroup.right {
    margin-left: 0;
  }
}
</style>
