<script setup>
/**
 * 路况上报
 * 提交 → 待审核 → 挂载到对应路线 → 30 天后自动过期（页面写明规则）
 * 审核在真实系统里由后台/版主完成，这里是本地演示：待审核条目可手动放行，用来验证「挂载」效果
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { routes } from '../data/routes.js'
import { useFieldStore, REPORT_TYPES, REPORT_LEVEL } from '../stores/field.js'
import { useAuthStore } from '../stores/auth.js'
import { useUiStore } from '../stores/ui.js'

const field = useFieldStore()
const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()

const byProvince = computed(() => {
  const map = new Map()
  for (const r of routes) {
    if (!map.has(r.province)) map.set(r.province, [])
    map.get(r.province).push(r)
  }
  return [...map.entries()]
})

/* 提交表单 */
const form = ref({ routeId: '', type: 'slide', level: 2, note: '' })
const submitting = ref(false)

function submit() {
  if (!auth.isLogged) {
    auth.openDialog('login')
    return
  }
  if (!form.value.routeId) return ui.toast('先选一条路线')
  if (form.value.note.trim().length < 6) return ui.toast('说明再具体一点（至少 6 个字）')
  submitting.value = true
  field.addReport({
    routeId: Number(form.value.routeId),
    type: form.value.type,
    level: form.value.level,
    note: form.value.note.trim()
  })
  form.value.note = ''
  submitting.value = false
  ui.toast('已提交，进入待审核队列')
  filter.value = 'pending'
  typeFilter.value = 'all'
}

/* 筛选 */
const filter = ref('all')
const typeFilter = ref('all')

const list = computed(() => {
  let l = field.approvedReports
  if (filter.value === 'pending') l = field.pendingReports
  if (filter.value === 'mine') l = [...field.reports].filter((r) => r.by === auth.nickname).sort((a, b) => b.at - a.at)
  if (typeFilter.value !== 'all') l = l.filter((r) => r.type === typeFilter.value)
  return l
})

const typeMeta = (k) => REPORT_TYPES.find((t) => t.k === k) || REPORT_TYPES[0]
const levelMeta = (v) => REPORT_LEVEL.find((l) => l.v === Number(v)) || REPORT_LEVEL[0]

const routeName = (id) => (routes.find((r) => r.id === Number(id)) || {}).name || '未知路线'
const routeOne = (id) => routes.find((r) => r.id === Number(id))

function ago(ts) {
  const d = Date.now() - ts
  const h = Math.floor(d / 3600000)
  if (h < 1) return `${Math.max(1, Math.floor(d / 60000))} 分钟前`
  if (h < 24) return `${h} 小时前`
  return `${Math.floor(h / 24)} 天前`
}

/* 每类的具体提示 */
const TIPS = {
  slide: '写清「哪个节点往上/下多少米」，以及能不能绕、要不要手脚并用。',
  weed: '写清哪一段路迹消失，以及现在靠什么辨认（丝带、溪流、山脊线）。',
  water: '写清最后一个可靠水源在哪、缺水量，建议背多少升。',
  bee: '写清蜂巢位置（岩壁/树洞）、活动时段，以及绕行方向。',
  closed: '写清封闭原因、区间、预计持续到什么时候，有没有官方绕行路线。',
  animal: '写清出现时段与地点，是否有幼崽（有幼崽的野猪最危险）。'
}

onMounted(() => {
  auth.ensureFresh()
})
</script>

<template>
  <div class="page">
    <div class="container">
      <header class="hd">
        <div>
          <p class="k">TRAIL STATUS · 路况上报</p>
          <h1>路上有什么，先说一声</h1>
          <p class="d">
            塌方、杂草、水源干涸、蜂群、封路、野兽——提交后进入审核队列，通过后会自动挂到对应路线详情页的「路况与天气」里。
            这是全网最容易过期的一类信息，所以每条都带时间，30 天后自动降级为「历史」。
          </p>
        </div>
        <div class="hd-nums">
          <div><b>{{ field.approvedReports.length }}</b><span>已挂载</span></div>
          <div><b>{{ field.pendingReports.length }}</b><span>待审核</span></div>
          <div><b>{{ new Set(field.approvedReports.map((r) => r.routeId)).size }}</b><span>覆盖路线</span></div>
        </div>
      </header>

      <div class="cols">
        <!-- 表单 -->
        <section class="panel form">
          <h2>提交一条路况</h2>
          <p class="hint">越具体越容易被通过：点位 + 方向 + 影响 + 建议。</p>

          <label class="fld">
            <span>哪条路线</span>
            <select v-model="form.routeId">
              <option value="">选择路线…</option>
              <optgroup v-for="[p, list] in byProvince" :key="p" :label="p">
                <option v-for="r in list" :key="r.id" :value="r.id">{{ r.name }}</option>
              </optgroup>
            </select>
          </label>

          <div class="fld">
            <span>路况类型</span>
            <div class="types">
              <button
                v-for="t in REPORT_TYPES"
                :key="t.k"
                class="type"
                :class="{ on: form.type === t.k }"
                :style="{ '--tone': t.tone }"
                @click="form.type = t.k"
              >
                <em>{{ t.icon }}</em>{{ t.name }}
              </button>
            </div>
            <p class="tip">{{ TIPS[form.type] }}</p>
          </div>

          <div class="fld">
            <span>影响程度</span>
            <div class="levels">
              <button
                v-for="l in REPORT_LEVEL"
                :key="l.v"
                class="level"
                :class="{ on: form.level === l.v }"
                :style="{ '--tone': l.tone }"
                @click="form.level = l.v"
              >
                {{ l.name }}
              </button>
            </div>
          </div>

          <label class="fld">
            <span>具体情况</span>
            <textarea
              v-model="form.note"
              rows="4"
              maxlength="160"
              placeholder="例：乱石坡脚往上 200 米，左侧塌方堆了 2 米高，要贴右侧岩壁过，重装危险。"
            ></textarea>
            <em class="count">{{ form.note.length }} / 160</em>
          </label>

          <button class="submit" :disabled="submitting" @click="submit">
            {{ auth.isLogged ? '提交，进入审核' : '登录后提交' }}
          </button>
          <p class="rule">审核通过后挂载到路线；同一条路线同类路况 7 天内自动合并。</p>
        </section>

        <!-- 列表 -->
        <section class="panel list-panel">
          <div class="list-head">
            <div class="filters">
              <button :class="{ on: filter === 'all' }" @click="filter = 'all'">已挂载 {{ field.approvedReports.length }}</button>
              <button :class="{ on: filter === 'pending' }" @click="filter = 'pending'">待审核 {{ field.pendingReports.length }}</button>
              <button :class="{ on: filter === 'mine' }" @click="filter = 'mine'">我上报的</button>
            </div>
          </div>

          <div class="type-row">
            <button :class="{ on: typeFilter === 'all' }" @click="typeFilter = 'all'">全部类型</button>
            <button
              v-for="t in REPORT_TYPES"
              :key="t.k"
              :class="{ on: typeFilter === t.k }"
              @click="typeFilter = t.k"
            >
              {{ t.icon }} {{ t.name }}
            </button>
          </div>

          <div v-if="list.length" class="reports">
            <article v-for="r in list" :key="r.id" class="report" :class="{ pending: r.status === 'pending' }">
              <div class="r-icon" :style="{ background: typeMeta(r.type).tone + '14', color: typeMeta(r.type).tone }">
                {{ typeMeta(r.type).icon }}
              </div>
              <div class="r-body">
                <p class="r-top">
                  <span class="r-type">{{ typeMeta(r.type).name }}</span>
                  <span class="r-lv" :style="{ color: levelMeta(r.level).tone, borderColor: levelMeta(r.level).tone + '55' }">
                    {{ levelMeta(r.level).name }}
                  </span>
                  <a class="r-route" @click="router.push(`/route/${r.routeId}?tab=live&from=reports`)">{{ routeName(r.routeId) }} →</a>
                  <em class="r-time">{{ ago(r.at) }}</em>
                </p>
                <p class="r-note">{{ r.note }}</p>
                <p class="r-foot">
                  <span>{{ r.by }}</span>
                  <span v-if="r.status === 'pending'" class="pend">待审核 · 通过后自动挂载</span>
                  <template v-else>
                    <button class="confirm" @click="field.confirmReport(r.id)">我也遇到 · {{ r.confirm }}</button>
                    <span v-if="routeOne(r.routeId)" class="km">
                      在 {{ routeOne(r.routeId).province }} · {{ routeOne(r.routeId).city }}
                    </span>
                  </template>
                </p>
                <div v-if="r.status === 'pending'" class="audit">
                  <span>演示：模拟后台审核</span>
                  <button class="mini ok" @click="field.approveReport(r.id); ui.toast('已通过，看看路线详情')">通过并挂载</button>
                  <button class="mini no" @click="field.rejectReport(r.id)">驳回</button>
                </div>
              </div>
            </article>
          </div>
          <p v-else class="empty">这个筛选下还没有记录。</p>

          <div class="policy">
            <p class="p-title">审核与过期规则</p>
            <ul>
              <li>提交 → 待审核（同一路线同类合并）→ 通过后挂到路线详情</li>
              <li>「禁止通行」级别需要 2 人以上确认才置顶</li>
              <li>30 天后自动降级为历史记录，不再作为出行依据</li>
              <li>恶意上报会被封禁账号；请只报亲眼看到的情况</li>
            </ul>
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
  gap: 28px;
  flex-wrap: wrap;
  margin-bottom: 22px;
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
  max-width: 680px;
  margin-top: 8px;
}
.hd-nums {
  display: flex;
  gap: 26px;
}
.hd-nums div {
  text-align: right;
}
.hd-nums b {
  display: block;
  font-family: var(--serif);
  font-size: 1.5rem;
  color: var(--forest-dark);
}
.hd-nums span {
  font-size: 0.64rem;
  color: var(--gray);
}

.cols {
  display: grid;
  grid-template-columns: 344px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}
.panel {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 20px 22px;
}
.form {
  position: sticky;
  top: calc(var(--nav-h) + 18px);
}
.form h2 {
  font-family: var(--serif);
  font-size: 1rem;
  font-weight: 600;
  color: var(--ink);
}
.hint {
  font-size: 0.68rem;
  color: var(--gray);
  margin-top: 4px;
  line-height: 1.7;
}
.fld {
  display: block;
  margin-top: 14px;
  position: relative;
}
.fld > span {
  display: block;
  font-size: 0.66rem;
  color: var(--gray);
  letter-spacing: 0.06em;
  margin-bottom: 6px;
}
.fld select,
.fld textarea {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 8px 10px;
  font-size: 0.78rem;
  background: #fcfaf5;
  color: var(--ink);
  outline: none;
  font-family: inherit;
  resize: vertical;
}
.fld select:focus,
.fld textarea:focus {
  border-color: var(--forest-light);
  background: #fff;
}
.types {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}
.type {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 4px;
  padding: 7px 4px;
  font-size: 0.68rem;
  color: var(--ink-soft);
  cursor: pointer;
  transition: 0.18s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
}
.type em {
  font-style: normal;
}
.type.on {
  border-color: var(--tone);
  background: color-mix(in srgb, var(--tone) 8%, #fff);
  color: var(--tone);
  font-weight: 600;
}
.tip {
  font-size: 0.62rem;
  color: var(--gray);
  line-height: 1.65;
  margin-top: 6px;
}
.levels {
  display: flex;
  gap: 6px;
}
.level {
  flex: 1;
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 4px;
  padding: 6px 0;
  font-size: 0.66rem;
  color: var(--ink-soft);
  cursor: pointer;
}
.level.on {
  border-color: var(--tone);
  color: var(--tone);
  background: color-mix(in srgb, var(--tone) 8%, #fff);
  font-weight: 600;
}
.count {
  position: absolute;
  right: 9px;
  bottom: 8px;
  font-size: 0.58rem;
  font-style: normal;
  color: var(--gray-light);
}
.submit {
  width: 100%;
  margin-top: 16px;
  padding: 9px 0;
  border: none;
  border-radius: 4px;
  background: var(--forest);
  color: #fff;
  font-size: 0.8rem;
  letter-spacing: 0.04em;
  cursor: pointer;
}
.submit:hover {
  background: var(--forest-dark);
}
.rule {
  font-size: 0.6rem;
  color: var(--gray-light);
  line-height: 1.7;
  margin-top: 8px;
}

.list-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}
.filters {
  display: flex;
  gap: 4px;
}
.filters button {
  border: 1px solid transparent;
  background: none;
  font-size: 0.72rem;
  color: var(--gray);
  padding: 4px 10px;
  border-radius: 3px;
  cursor: pointer;
}
.filters button.on {
  background: var(--forest-soft);
  color: var(--forest-dark);
  font-weight: 600;
}
.type-row {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
  padding: 10px 0 12px;
}
.type-row button {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 999px;
  font-size: 0.63rem;
  padding: 3px 9px;
  color: var(--gray);
  cursor: pointer;
}
.type-row button.on {
  border-color: var(--forest);
  color: var(--forest);
  background: var(--forest-soft);
}
.reports {
  display: flex;
  flex-direction: column;
}
.report {
  display: flex;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid rgba(230, 225, 214, 0.75);
}
.report:last-child {
  border-bottom: none;
}
.r-icon {
  flex: 0 0 auto;
  width: 34px;
  height: 34px;
  border-radius: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
}
.r-body {
  flex: 1;
  min-width: 0;
}
.r-top {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.r-type {
  font-size: 0.74rem;
  font-weight: 600;
  color: var(--ink);
}
.r-lv {
  font-size: 0.58rem;
  padding: 1px 6px;
  border: 1px solid;
  border-radius: 2px;
}
.r-route {
  font-size: 0.68rem;
  color: var(--forest);
  cursor: pointer;
}
.r-route:hover {
  text-decoration: underline;
}
.r-time {
  margin-left: auto;
  font-size: 0.6rem;
  font-style: normal;
  color: var(--gray-light);
}
.r-note {
  font-size: 0.76rem;
  color: var(--ink-soft);
  line-height: 1.75;
  margin-top: 5px;
}
.r-foot {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 7px;
  font-size: 0.62rem;
  color: var(--gray-light);
  flex-wrap: wrap;
}
.confirm {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 999px;
  font-size: 0.6rem;
  padding: 2px 8px;
  color: var(--gray);
  cursor: pointer;
}
.confirm:hover {
  border-color: var(--forest-light);
  color: var(--forest);
}
.pend {
  color: #8a6d2f;
}
.km {
  margin-left: auto;
}
.audit {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 7px 9px;
  background: #fdf7e8;
  border: 1px dashed #e3d3a8;
  border-radius: 4px;
  font-size: 0.62rem;
  color: #8a6d2f;
}
.mini {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 3px;
  font-size: 0.6rem;
  padding: 2px 8px;
  cursor: pointer;
}
.mini.ok {
  border-color: var(--forest-light);
  color: var(--forest);
}
.mini.no {
  border-color: #d9b6ae;
  color: #a9462f;
}
.empty {
  padding: 30px 0;
  text-align: center;
  font-size: 0.76rem;
  color: var(--gray);
}
.policy {
  margin-top: 16px;
  padding-top: 13px;
  border-top: 1px dashed var(--line);
}
.p-title {
  font-size: 0.66rem;
  color: var(--gray);
  letter-spacing: 0.06em;
  margin-bottom: 6px;
}
.policy ul {
  margin: 0;
  padding-left: 16px;
}
.policy li {
  font-size: 0.64rem;
  color: var(--gray);
  line-height: 1.9;
}

@media (max-width: 980px) {
  .cols {
    grid-template-columns: 1fr;
  }
  .form {
    position: static;
  }
  .hd h1 {
    font-size: 1.4rem;
  }
}
</style>
