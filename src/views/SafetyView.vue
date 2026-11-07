<script setup>
/**
 * 出行安全报备
 * 出发前登记：路线 / 日期 / 同行人 / 紧急联系人
 * 进山后：平安打卡（记录时间与状态），下山关闭报备
 * 数据只在本机；「复制行程」用于把报备文本发给家人
 */
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { routes } from '../data/routes.js'
import { useAuthStore } from '../stores/auth.js'
import { useFieldStore } from '../stores/field.js'
import { useUiStore } from '../stores/ui.js'

const auth = useAuthStore()
const field = useFieldStore()
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

const today = new Date()
const pad = (n) => String(n).padStart(2, '0')
const todayStr = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`

const form = ref({
  routeId: '',
  startDate: todayStr,
  days: 2,
  party: '',
  emergencyName: '',
  emergencyPhone: '',
  note: ''
})

const picked = computed(() => routes.find((r) => r.id === Number(form.value.routeId)) || null)

function submit() {
  if (!auth.isLogged) return auth.openDialog('login')
  if (!form.value.routeId) return ui.toast('先选一条路线')
  if (!form.value.emergencyName.trim() || !form.value.emergencyPhone.trim())
    return ui.toast('紧急联系人不能空着')
  if (!/^\d{6,}$/.test(form.value.emergencyPhone.trim())) return ui.toast('电话格式不对')
  field.addPlan({
    routeId: form.value.routeId,
    startDate: form.value.startDate,
    days: form.value.days,
    party: form.value.party.split(/[,，、\s]+/).filter(Boolean),
    emergencyName: form.value.emergencyName,
    emergencyPhone: form.value.emergencyPhone,
    note: form.value.note
  })
  ui.toast('已登记，出发前把行程发给家人')
}

const plan = computed(() => field.activePlan)

const QUICK = ['到达起点，开始进山', '已到营地，一切正常', '天气转差，准备下撤', '已回到公路，安全']

const note = ref('')
function check(text) {
  if (!plan.value) return
  field.checkin(plan.value.id, text || note.value || '平安打卡', 'safe')
  note.value = ''
  ui.toast('已记录')
}
function finish() {
  if (!plan.value) return
  field.closePlan(plan.value.id)
  ui.toast('报备已关闭')
}

const history = computed(() => field.myPlans.filter((p) => p.status === 'done').slice().reverse())

function planText(p) {
  const r = routes.find((x) => x.id === Number(p.routeId))
  return [
    `【出行安全报备】${auth.nickname}`,
    `路线：${r ? r.name : '未知'}（${r ? r.province + r.city : ''}）`,
    `出发：${p.startDate} · 计划 ${p.days} 天`,
    `同行：${p.party.length ? p.party.join('、') : '无（单独行动）'}`,
    `紧急联系人：${p.emergencyName} ${p.emergencyPhone}`,
    p.note ? `备注：${p.note}` : '',
    p.checkins.length ? `最近打卡：${p.checkins[p.checkins.length - 1].note}` : '',
    '如逾期未联系，请按上表联系紧急联系人并报警。'
  ]
    .filter(Boolean)
    .join('\n')
}

async function copyPlan(p) {
  const text = planText(p)
  try {
    await navigator.clipboard.writeText(text)
    ui.toast('行程文本已复制，发给家人吧')
  } catch {
    ui.toast('复制失败，请手动选择文本')
  }
}

function ago(ts) {
  const d = Date.now() - ts
  const m = Math.floor(d / 60000)
  if (m < 60) return `${Math.max(1, m)} 分钟前`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} 小时前`
  return `${Math.floor(h / 24)} 天前`
}
const routeName = (id) => (routes.find((r) => r.id === Number(id)) || {}).name || '未知路线'
</script>

<template>
  <div class="page">
    <div class="container">
      <header class="hd">
        <div>
          <p class="k">TRIP PLAN · 出行安全报备</p>
          <h1>让一个人知道，你去了哪</h1>
          <p class="d">
            山里没有信号的时候，唯一能替你做决定的，是那个知道你的路线、同行人和预计返回时间的人。
            这里登记的信息只存在本机，点「复制行程」可以整段发给家人或队友。
          </p>
        </div>
        <div class="hd-badge" :class="{ on: plan }">
          <span>{{ plan ? '进行中' : '未报备' }}</span>
          <em>{{ plan ? routeName(plan.routeId) : '出发前登记一次' }}</em>
        </div>
      </header>

      <div class="cols">
        <!-- 左：进行中的报备 -->
        <section class="panel left">
          <template v-if="plan">
            <div class="p-head">
              <div>
                <p class="p-k">进行中的行程</p>
                <h2>{{ routeName(plan.routeId) }}</h2>
                <p class="p-meta">
                  {{ plan.startDate }} 出发 · 计划 {{ plan.days }} 天 · 同行
                  {{ plan.party.length ? plan.party.join('、') : '单独行动' }}
                </p>
                <p class="p-emerg">
                  紧急联系人：{{ plan.emergencyName }} <a :href="`tel:${plan.emergencyPhone}`">{{ plan.emergencyPhone }}</a>
                </p>
              </div>
              <button class="link" @click="router.push(`/route/${plan.routeId}?tab=live&from=safety`)">看路线实况 →</button>
            </div>

            <div class="quick">
              <p class="q-title">一键打卡</p>
              <div class="q-btns">
                <button v-for="q in QUICK" :key="q" @click="check(q)">{{ q }}</button>
              </div>
              <div class="custom">
                <input v-model="note" maxlength="40" placeholder="或者自己写一句：在哪儿、状态如何" />
                <button @click="check('')">打卡</button>
              </div>
            </div>

            <div class="timeline">
              <p class="q-title">打卡记录 {{ plan.checkins.length }}</p>
              <ol>
                <li v-for="(c, i) in plan.checkins.slice().reverse()" :key="i" :class="c.type">
                  <span class="dot"></span>
                  <div>
                    <p class="c-note">{{ c.note }}</p>
                    <p class="c-time">{{ new Date(c.at).toLocaleString('zh-CN', { hour12: false }) }} · {{ ago(c.at) }}</p>
                  </div>
                </li>
              </ol>
            </div>

            <div class="p-acts">
              <button class="btn primary" @click="finish">我已安全下山</button>
              <button class="btn" @click="copyPlan(plan)">复制行程给家人</button>
            </div>
          </template>

          <template v-else>
            <div class="blank">
              <span class="blank-mark">
                <svg viewBox="0 0 24 24" width="26" height="26">
                  <path d="M12 3l7 3v6c0 4.2-2.9 7.6-7 9-4.1-1.4-7-4.8-7-9V6l7-3z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" />
                  <path d="M8.8 12.2l2.2 2.2 4.2-4.6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </span>
              <h2>当前没有进行中的行程</h2>
              <p>右边填一次，出发前把生成的文本发给家人。山里每到一处打一次卡，对方就知道你走到哪了。</p>
            </div>
            <div class="why">
              <p class="w-t">为什么值得花 2 分钟填</p>
              <ul>
                <li>搜救队最先问的三个问题：走哪条线、几个人、原计划几天回来——这里都有</li>
                <li>「平安打卡」带上时间戳，逾期没打卡就是最直接的报警信号</li>
                <li>紧急联系人电话在山里没信号时，是别人替你打的</li>
              </ul>
            </div>
          </template>

          <div v-if="history.length" class="history">
            <p class="q-title">历史报备 {{ history.length }}</p>
            <div v-for="h in history.slice(0, 4)" :key="h.id" class="h-row">
              <div>
                <p class="h-name">{{ routeName(h.routeId) }}</p>
                <p class="h-meta">{{ h.startDate }} · {{ h.days }} 天 · {{ h.checkins.length }} 次打卡</p>
              </div>
              <button class="link" @click="copyPlan(h)">复制</button>
            </div>
          </div>
        </section>

        <!-- 右：登记表单 -->
        <section class="panel">
          <h2 class="f-title">登记一次行程</h2>
          <p class="f-sub">带 * 为必填。信息只保存在本机浏览器。</p>

          <label class="fld">
            <span>路线 *</span>
            <select v-model="form.routeId">
              <option value="">选择路线…</option>
              <optgroup v-for="[p, list] in byProvince" :key="p" :label="p">
                <option v-for="r in list" :key="r.id" :value="r.id">{{ r.name }}</option>
              </optgroup>
            </select>
          </label>

          <div v-if="picked" class="picked">
            <span>{{ picked.distance }} km</span><i></i><span>↑ {{ picked.climb }} m</span><i></i>
            <span>{{ picked.days }}</span><i></i><span>{{ picked.terrain }}</span>
          </div>

          <div class="row2">
            <label class="fld">
              <span>出发日期</span>
              <input v-model="form.startDate" type="date" />
            </label>
            <label class="fld">
              <span>计划天数</span>
              <input v-model.number="form.days" type="number" min="1" max="10" />
            </label>
          </div>

          <label class="fld">
            <span>同行人员</span>
            <input v-model="form.party" placeholder="用逗号分开，例：阿野、小林" />
            <em class="hint">单独行动也建议写「无」，让家人知道。</em>
          </label>

          <div class="row2">
            <label class="fld">
              <span>紧急联系人 *</span>
              <input v-model="form.emergencyName" placeholder="姓名" maxlength="12" />
            </label>
            <label class="fld">
              <span>联系电话 *</span>
              <input v-model="form.emergencyPhone" placeholder="手机号" maxlength="15" />
            </label>
          </div>

          <label class="fld">
            <span>备注</span>
            <textarea v-model="form.note" rows="3" maxlength="120" placeholder="例：车停在罗坑镇小学门口，粤 A XXXXX。"></textarea>
          </label>

          <button class="btn primary full" @click="submit">{{ auth.isLogged ? '登记报备' : '登录后登记' }}</button>
          <p class="f-note">
            真实系统里这一步会触发短信/微信通知给紧急联系人；当前是本地版本，请点右侧「复制行程」手动发送。
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
  gap: 24px;
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
  max-width: 660px;
  margin-top: 8px;
}
.hd-badge {
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px 16px;
  background: #fff;
  min-width: 168px;
}
.hd-badge.on {
  border-color: #cfdccf;
  background: #f6faf6;
}
.hd-badge span {
  display: block;
  font-size: 0.68rem;
  color: #8a6d2f;
  letter-spacing: 0.08em;
}
.hd-badge.on span {
  color: var(--forest);
}
.hd-badge em {
  display: block;
  font-size: 0.78rem;
  font-style: normal;
  color: var(--ink);
  margin-top: 4px;
}
.cols {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
  align-items: start;
}
.panel {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 20px 22px;
}
.left {
  min-height: 420px;
}
.p-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.p-k {
  font-size: 0.62rem;
  color: var(--forest);
  letter-spacing: 0.08em;
}
.p-head h2 {
  font-family: var(--serif);
  font-size: 1.16rem;
  font-weight: 600;
  color: var(--ink);
  margin-top: 4px;
}
.p-meta,
.p-emerg {
  font-size: 0.68rem;
  color: var(--gray);
  margin-top: 5px;
}
.p-emerg a {
  color: var(--forest);
  text-decoration: none;
}
.link {
  border: none;
  background: none;
  font-size: 0.66rem;
  color: var(--forest);
  cursor: pointer;
  white-space: nowrap;
}
.link:hover {
  text-decoration: underline;
}
.quick {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed var(--line);
}
.q-title {
  font-size: 0.64rem;
  color: var(--gray);
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}
.q-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.q-btns button {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 999px;
  font-size: 0.66rem;
  padding: 5px 11px;
  color: var(--ink-soft);
  cursor: pointer;
  transition: 0.18s;
}
.q-btns button:hover {
  border-color: var(--forest-light);
  color: var(--forest);
  background: var(--forest-soft);
}
.custom {
  display: flex;
  gap: 7px;
  margin-top: 8px;
}
.custom input {
  flex: 1;
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 7px 10px;
  font-size: 0.72rem;
  background: #fcfaf5;
  outline: none;
  color: var(--ink);
}
.custom button {
  border: 1px solid var(--forest);
  background: #fff;
  color: var(--forest);
  border-radius: 4px;
  font-size: 0.68rem;
  padding: 0 14px;
  cursor: pointer;
}
.timeline {
  margin-top: 18px;
  padding-top: 13px;
  border-top: 1px dashed var(--line);
}
.timeline ol {
  list-style: none;
  margin: 0;
  padding: 0;
}
.timeline li {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(230, 225, 214, 0.6);
}
.timeline li:last-child {
  border-bottom: none;
}
.dot {
  flex: 0 0 auto;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-top: 5px;
  background: var(--forest-light);
}
.timeline li.go .dot {
  background: #8a6d2f;
}
.timeline li.done .dot {
  background: #2f6f9e;
}
.c-note {
  font-size: 0.74rem;
  color: var(--ink-soft);
}
.c-time {
  font-size: 0.6rem;
  color: var(--gray-light);
  margin-top: 2px;
}
.p-acts {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}
.btn {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 4px;
  font-size: 0.72rem;
  padding: 7px 14px;
  color: var(--ink-soft);
  cursor: pointer;
}
.btn:hover {
  border-color: var(--forest-light);
  color: var(--forest);
}
.btn.primary {
  background: var(--forest);
  border-color: var(--forest);
  color: #fff;
}
.btn.primary:hover {
  background: var(--forest-dark);
}
.btn.full {
  width: 100%;
  margin-top: 16px;
  padding: 9px 0;
  font-size: 0.8rem;
}
.blank {
  text-align: center;
  padding: 34px 20px 22px;
}
.blank-mark {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  background: var(--forest-soft);
  color: var(--forest);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}
.blank h2 {
  font-family: var(--serif);
  font-size: 1.02rem;
  color: var(--ink);
}
.blank p {
  font-size: 0.74rem;
  color: var(--gray);
  line-height: 1.85;
  max-width: 380px;
  margin: 7px auto 0;
}
.why {
  margin: 0 20px 18px;
  padding: 13px 15px;
  background: #fcfaf5;
  border: 1px solid var(--line);
  border-radius: 5px;
}
.w-t {
  font-size: 0.66rem;
  color: var(--ink);
  font-weight: 600;
  margin-bottom: 6px;
}
.why ul {
  margin: 0;
  padding-left: 15px;
}
.why li {
  font-size: 0.64rem;
  color: var(--gray);
  line-height: 1.9;
}
.history {
  margin-top: 18px;
  padding-top: 13px;
  border-top: 1px solid var(--line);
}
.h-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 7px 0;
  border-bottom: 1px solid rgba(230, 225, 214, 0.6);
}
.h-row:last-child {
  border-bottom: none;
}
.h-name {
  font-size: 0.72rem;
  color: var(--ink);
}
.h-meta {
  font-size: 0.6rem;
  color: var(--gray);
  margin-top: 2px;
}
.f-title {
  font-family: var(--serif);
  font-size: 1rem;
  font-weight: 600;
  color: var(--ink);
}
.f-sub {
  font-size: 0.64rem;
  color: var(--gray);
  margin-top: 4px;
}
.fld {
  display: block;
  margin-top: 12px;
  position: relative;
}
.fld > span {
  display: block;
  font-size: 0.64rem;
  color: var(--gray);
  letter-spacing: 0.05em;
  margin-bottom: 5px;
}
.fld input,
.fld select,
.fld textarea {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 7px 9px;
  font-size: 0.76rem;
  background: #fcfaf5;
  color: var(--ink);
  outline: none;
  font-family: inherit;
  resize: vertical;
}
.fld input:focus,
.fld select:focus,
.fld textarea:focus {
  border-color: var(--forest-light);
  background: #fff;
}
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.hint {
  display: block;
  font-size: 0.58rem;
  font-style: normal;
  color: var(--gray-light);
  margin-top: 4px;
  line-height: 1.6;
}
.picked {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
  margin-top: 7px;
  font-size: 0.62rem;
  color: var(--ink-soft);
}
.picked i {
  width: 1px;
  height: 8px;
  background: var(--line);
}
.f-note {
  font-size: 0.6rem;
  color: var(--gray-light);
  line-height: 1.7;
  margin-top: 8px;
}

@media (max-width: 980px) {
  .cols {
    grid-template-columns: 1fr;
  }
  .hd h1 {
    font-size: 1.4rem;
  }
}
</style>
