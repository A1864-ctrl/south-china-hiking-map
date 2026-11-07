<script setup>
/**
 * LNT 户外知识 + 山野急救科普
 * 左侧目录 / 右侧正文，支持 ?a=id 深链
 */
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { knowledge, knowledgeCats } from '../data/knowledge.js'
import { routes } from '../data/routes.js'
import RouteEcology from '../components/RouteEcology.vue'

const route = useRoute()
const router = useRouter()

const cat = ref(String(route.query.cat || 'lnt'))
const id = ref(String(route.query.a || ''))
const read = ref(new Set())

/* 第三类：路线科普 */
const ECO = {
  k: 'eco', name: '路线科普', en: 'TRAIL ECOLOGY', tone: '#8a6d2f',
  desc: '53 条徒步线逐条讲：地形地势、植被带谱、动物种类与注意事项。'
}
const cats = computed(() => [...knowledgeCats, ECO])
const ecoQ = ref('')
const ecoId = ref(Number(route.query.r) || routes[0].id)
const ecoRoute = computed(() => routes.find((r) => r.id === ecoId.value) || routes[0])
const ecoList = computed(() => {
  const q = ecoQ.value.trim()
  if (!q) return routes
  return routes.filter((r) => r.name.includes(q) || r.city.includes(q) || r.province.includes(q) || r.terrain.includes(q))
})
function pickEco(r) {
  ecoId.value = r.id
  router.replace({ query: { cat: 'eco', r: r.id } })
}

const list = computed(() => knowledge.filter((k) => k.cat === cat.value))
const cur = computed(() => knowledge.find((k) => k.id === id.value) || list.value[0] || knowledge[0])

watch(cur, (v) => {
  if (v && !id.value) id.value = v.id
  if (v) read.value = new Set([...read.value, v.id])
})

function pick(k) {
  id.value = k.id
  router.replace({ query: { ...route.query, cat: k.cat, a: k.id } })
}

function switchCat(c) {
  cat.value = c
  if (c === 'eco') {
    router.replace({ query: { cat: 'eco', r: ecoId.value } })
    return
  }
  const first = knowledge.find((k) => k.cat === c)
  if (first) pick(first)
}

const totalMins = computed(() => knowledge.filter((k) => k.cat === cat.value).reduce((a, k) => a + k.mins, 0))
</script>

<template>
  <div class="page">
    <div class="container">
      <header class="hd">
        <div>
          <p class="k">FIELD KNOWLEDGE · 山野知识库</p>
          <h1>先知道，再出发</h1>
          <p class="d">
            三套内容：无痕山林（LNT）七原则加华南海岸线、丹霞、梯田的落地做法；山野急救覆盖中暑、失温、蜂蜇、蛇咬、扭伤撤离、迷路求救；
            以及按 53 条路线逐条整理的「路线科普」——地形地势、植被带谱、动物种类与注意事项。
            不写「注意安全」这种空话，每条都能对应到一个具体动作。
          </p>
        </div>
        <div class="cats">
          <button
            v-for="c in cats"
            :key="c.k"
            class="cat"
            :class="{ on: cat === c.k }"
            :style="{ '--tone': c.tone }"
            @click="switchCat(c.k)"
          >
            <em>{{ c.en }}</em>
            <b>{{ c.name }}</b>
            <span v-if="c.k !== 'eco'">{{ knowledge.filter((k) => k.cat === c.k).length }} 篇 · {{ knowledge.filter((k) => k.cat === c.k).reduce((a, x) => a + x.mins, 0) }} 分钟</span>
            <span v-else>{{ routes.length }} 条路线 · 逐条讲</span>
          </button>
        </div>
      </header>

      <div class="cols">
        <aside class="toc">
          <template v-if="cat !== 'eco'">
            <p class="toc-head">
              {{ knowledgeCats.find((c) => c.k === cat)?.name }}
              <em>{{ list.length }} 篇 · {{ totalMins }} 分钟</em>
            </p>
            <button
              v-for="(k, i) in list"
              :key="k.id"
              class="toc-item"
              :class="{ on: cur.id === k.id, read: read.has(k.id) }"
              @click="pick(k)"
            >
              <em>{{ String(i + 1).padStart(2, '0') }}</em>
              <span>{{ k.title }}</span>
              <i>{{ k.mins }}′</i>
            </button>
            <div class="toc-foot">
              <p>读过的条目会打勾，只记录在本次浏览里。</p>
            </div>
          </template>

          <template v-else>
            <p class="toc-head">
              按路线查
              <em>{{ ecoList.length }} / {{ routes.length }} 条</em>
            </p>
            <input v-model="ecoQ" class="toc-search" placeholder="搜路线名 / 城市 / 地貌" />
            <button
              v-for="r in ecoList"
              :key="r.id"
              class="toc-item"
              :class="{ on: ecoRoute.id === r.id }"
              @click="pickEco(r)"
            >
              <em>{{ String(r.id).padStart(2, '0') }}</em>
              <span>{{ r.name }}</span>
              <i>{{ r.distance }}km</i>
            </button>
            <div class="toc-foot">
              <p>每条线都按当地自然地理整理，不是通用模板。</p>
            </div>
          </template>
        </aside>

        <article v-if="cat !== 'eco'" class="doc">
          <div class="doc-head">
            <p class="doc-cat">{{ knowledgeCats.find((c) => c.k === cur.cat)?.name }} · {{ cur.mins }} 分钟读完</p>
            <h2>{{ cur.title }}</h2>
            <div class="doc-tags">
              <span v-for="t in cur.tags" :key="t">{{ t }}</span>
            </div>
          </div>

          <p class="lead">{{ cur.lead }}</p>

          <template v-for="(b, i) in cur.blocks" :key="i">
            <div v-if="b.h" class="blk">
              <h3>{{ b.h }}</h3>
              <p v-if="b.p">{{ b.p }}</p>
            </div>
            <ul v-else-if="b.ul" class="ul">
              <li v-for="(x, j) in b.ul" :key="j">{{ x }}</li>
            </ul>
            <p v-else-if="b.tip" class="tip">
              <span>记住这句</span>{{ b.tip }}
            </p>
            <p v-else-if="b.p" class="para">{{ b.p }}</p>
          </template>

          <div class="doc-foot">
            <p>内容为本站整理，用于科普与行前准备，不能替代专业急救培训。建议至少参加一次 WFA（野外急救）课程。</p>
            <button class="next" @click="pick(list[(list.findIndex((x) => x.id === cur.id) + 1) % list.length])">
              下一篇 →
            </button>
          </div>
        </article>
        <article v-else class="doc eco-doc">
          <div class="doc-head">
            <p class="doc-cat">{{ ecoRoute.province }} · {{ ecoRoute.city }} · {{ ecoRoute.terrain }}</p>
            <h2>{{ ecoRoute.name }}</h2>
            <p class="eco-sub">
              {{ ecoRoute.distance }} km · ↑{{ ecoRoute.climb }} m · {{ ecoRoute.days }} · 最佳 {{ ecoRoute.season }}
            </p>
          </div>
          <RouteEcology :route="ecoRoute" />
        </article>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  background: var(--cream);
}
.toc-search {
  width: calc(100% - 12px);
  margin: 8px 6px 6px;
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 6px 9px;
  font-size: 0.7rem;
  background: #fcfaf5;
  color: var(--ink);
  outline: none;
  font-family: inherit;
}
.toc-search:focus {
  border-color: var(--forest-light);
  background: #fff;
}
.eco-sub {
  font-size: 0.68rem;
  color: var(--gray);
  margin-top: 6px;
}
.eco-doc {
  max-width: 980px;
}
.hd {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 30px;
  flex-wrap: wrap;
  margin-bottom: 22px;
  padding-bottom: 20px;
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
  max-width: 620px;
  margin-top: 8px;
}
.cats {
  display: flex;
  gap: 8px;
}
.cat {
  text-align: left;
  border: 1px solid var(--line);
  border-top: 2px solid var(--line);
  background: #fff;
  border-radius: 0 0 5px 5px;
  padding: 9px 14px 10px;
  cursor: pointer;
  min-width: 150px;
  transition: 0.18s;
}
.cat.on {
  border-top-color: var(--tone);
  background: #fff;
  box-shadow: 0 6px 16px rgba(30, 61, 41, 0.07);
}
.cat em {
  display: block;
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.5rem;
  letter-spacing: 0.12em;
  color: var(--gray-light);
  font-style: normal;
}
.cat b {
  display: block;
  font-family: var(--serif);
  font-size: 0.9rem;
  color: var(--ink);
  margin: 3px 0 2px;
}
.cat.on b {
  color: var(--tone);
}
.cat span {
  font-size: 0.58rem;
  color: var(--gray);
}
.cols {
  display: grid;
  grid-template-columns: 268px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}
.toc {
  position: sticky;
  top: calc(var(--nav-h) + 18px);
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 8px;
  max-height: calc(100vh - var(--nav-h) - 40px);
  overflow-y: auto;
  overscroll-behavior: contain;
}
.toc-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 0.68rem;
  color: var(--ink);
  padding: 7px 8px 9px;
  border-bottom: 1px solid var(--line);
}
.toc-head em {
  font-size: 0.56rem;
  font-style: normal;
  color: var(--gray-light);
}
.toc-item {
  display: flex;
  align-items: baseline;
  gap: 7px;
  width: 100%;
  text-align: left;
  border: none;
  background: none;
  border-left: 2px solid transparent;
  padding: 8px 7px 8px 9px;
  cursor: pointer;
  font-size: 0.72rem;
  color: var(--ink-soft);
  line-height: 1.45;
  transition: 0.16s;
}
.toc-item:hover {
  background: rgba(45, 90, 61, 0.05);
}
.toc-item.on {
  border-left-color: var(--forest);
  background: var(--forest-soft);
  color: var(--forest-dark);
  font-weight: 600;
}
.toc-item em {
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.54rem;
  font-style: normal;
  color: var(--gray-light);
  flex: 0 0 auto;
}
.toc-item span {
  flex: 1;
}
.toc-item i {
  font-size: 0.54rem;
  font-style: normal;
  color: var(--gray-light);
  flex: 0 0 auto;
}
.toc-item.read span::after {
  content: '✓';
  color: var(--forest-light);
  font-size: 0.6rem;
  margin-left: 4px;
}
.toc-foot {
  padding: 9px 8px 4px;
  border-top: 1px dashed var(--line);
  margin-top: 5px;
}
.toc-foot p {
  font-size: 0.56rem;
  color: var(--gray-light);
  line-height: 1.7;
}

.doc {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 26px 32px 24px;
  max-width: 860px;
}
.doc-cat {
  font-size: 0.6rem;
  letter-spacing: 0.1em;
  color: var(--forest-light);
}
.doc-head h2 {
  font-family: var(--serif);
  font-size: 1.44rem;
  font-weight: 600;
  color: var(--ink);
  margin-top: 6px;
  line-height: 1.4;
}
.doc-tags {
  display: flex;
  gap: 5px;
  margin-top: 9px;
}
.doc-tags span {
  font-size: 0.56rem;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--cream);
  color: #8a6d2f;
}
.lead {
  font-size: 0.84rem;
  color: var(--ink-soft);
  line-height: 1.95;
  margin-top: 16px;
  padding: 12px 14px;
  background: #fcfaf5;
  border-left: 2px solid var(--forest-light);
  border-radius: 0 3px 3px 0;
}
.blk {
  margin-top: 20px;
}
.blk h3 {
  font-family: var(--serif);
  font-size: 0.98rem;
  font-weight: 600;
  color: var(--forest-dark);
  margin-bottom: 7px;
}
.blk p,
.para {
  font-size: 0.82rem;
  color: var(--ink-soft);
  line-height: 2.05;
}
.para {
  margin-top: 14px;
}
.ul {
  margin: 12px 0 0;
  padding: 0 0 0 2px;
  list-style: none;
}
.ul li {
  position: relative;
  font-size: 0.8rem;
  color: var(--ink-soft);
  line-height: 1.95;
  padding-left: 16px;
  margin-bottom: 4px;
}
.ul li::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 11px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--forest-light);
  opacity: 0.7;
}
.tip {
  margin-top: 18px;
  padding: 11px 14px;
  background: #fdf7e8;
  border: 1px dashed #e3d3a8;
  border-radius: 4px;
  font-size: 0.78rem;
  color: #6b5320;
  line-height: 1.9;
}
.tip span {
  display: inline-block;
  font-size: 0.56rem;
  letter-spacing: 0.1em;
  color: #a97a17;
  margin-right: 8px;
  padding: 1px 6px;
  border: 1px solid #e3d3a8;
  border-radius: 2px;
}
.doc-foot {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-top: 26px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}
.doc-foot p {
  font-size: 0.62rem;
  color: var(--gray-light);
  line-height: 1.8;
  max-width: 520px;
}
.next {
  flex: 0 0 auto;
  border: 1px solid var(--forest);
  background: #fff;
  color: var(--forest);
  border-radius: 4px;
  font-size: 0.7rem;
  padding: 6px 14px;
  cursor: pointer;
}
.next:hover {
  background: var(--forest);
  color: #fff;
}

@media (max-width: 980px) {
  .cols {
    grid-template-columns: 1fr;
  }
  .toc {
    position: static;
  }
  .doc {
    padding: 20px 20px 18px;
  }
  .hd h1 {
    font-size: 1.4rem;
  }
  .cats {
    width: 100%;
  }
  .cat {
    flex: 1;
    min-width: 0;
  }
}
</style>
