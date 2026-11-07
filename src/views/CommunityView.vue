<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { routes } from '../data/routes.js'
import { cityStats } from '../data/cities.js'
import { useAuthStore } from '../stores/auth.js'
import { useSocialStore, distanceBand } from '../stores/social.js'
import { useUiStore } from '../stores/ui.js'
import LightBox from '../components/LightBox.vue'

const auth = useAuthStore()
const social = useSocialStore()
const ui = useUiStore()
const router = useRouter()
const route = useRoute()

const tabs = [
  { k: 'feed', label: '山友动态', sub: '走过的路，说给人听' },
  { k: 'buddy', label: '找搭子', sub: '按行程配对' },
  { k: 'nearby', label: '附近的人', sub: '5 公里内' }
]
const tab = ref(['feed', 'buddy', 'nearby'].includes(String(route.query.tab)) ? String(route.query.tab) : 'feed')

/** 切标签时同步到地址栏，链接可以直接指向某个标签 */
function pickTab(k) {
  tab.value = k
  router.replace({ query: { ...route.query, tab: k } })
}

/* ── 通用：时间显示 ── */
function ago(ts) {
  const d = Date.now() - ts
  const m = Math.floor(d / 60000)
  if (m < 1) return '刚刚'
  if (m < 60) return `${m} 分钟前`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} 小时前`
  const day = Math.floor(h / 24)
  if (day < 30) return `${day} 天前`
  return new Date(ts).toLocaleDateString('zh-CN')
}

/* ── 动态 ── */
const draft = ref({ title: '', body: '', trailId: '', tags: '' })
const commenting = ref('')
const commentText = ref('')
const postError = ref('')

const trailOptions = computed(() => routes.map((r) => ({ id: r.id, name: r.name, city: r.city })))

function submitPost() {
  postError.value = ''
  try {
    if (!draft.value.title.trim() && !draft.value.body.trim()) {
      postError.value = '标题或正文至少写一个'
      return
    }
    const picked = trailOptions.value.find((t) => String(t.id) === String(draft.value.trailId))
    social.addPost({
      title: draft.value.title,
      body: draft.value.body,
      trailId: picked ? picked.id : null,
      trailName: picked ? picked.name : '',
      city: picked ? picked.city : '',
      tags: draft.value.tags
        .split(/[,，\s]+/)
        .map((t) => t.trim())
        .filter(Boolean)
        .slice(0, 4)
    })
    draft.value = { title: '', body: '', trailId: '', tags: '' }
    ui.toast('已发布')
  } catch (e) {
    postError.value = e.message
  }
}

function like(p) {
  try {
    social.toggleLike(p.id)
  } catch (e) {
    postError.value = e.message
  }
}

function submitComment(p) {
  try {
    social.addComment(p.id, commentText.value)
    commentText.value = ''
    commenting.value = ''
  } catch (e) {
    postError.value = e.message
  }
}

const likedByMe = (p) => (auth.isLogged ? p.likes.includes(auth.account) : false)

/* ── 找搭子 ── */
const today = new Date()
const fmt = (d) => d.toISOString().slice(0, 10)
const plus = (n) => fmt(new Date(Date.now() + n * 86400000))

const want = ref({
  startDate: plus(6),
  endDate: plus(9),
  city: '',
  level: 0,
  tags: ''
})

const wantTags = computed(() =>
  want.value.tags
    .split(/[,，\s]+/)
    .map((t) => t.trim())
    .filter(Boolean)
)
const wantForScore = computed(() => ({
  startDate: want.value.startDate,
  endDate: want.value.endDate,
  city: want.value.city,
  level: Number(want.value.level) || 0,
  tags: wantTags.value
}))

const matched = computed(() => social.matchBuddies(wantForScore.value))

const publishing = ref(false)
const buddyDraft = ref({
  destCity: '萍乡',
  trailId: '',
  startDate: plus(7),
  endDate: plus(8),
  level: 2,
  budget: 400,
  genderPref: 0,
  slots: 2,
  tags: '',
  intro: ''
})
const buddyError = ref('')

const cityNames = computed(() => cityStats.map((c) => c.name))

function submitBuddy() {
  buddyError.value = ''
  try {
    const picked = trailOptions.value.find((t) => String(t.id) === String(buddyDraft.value.trailId))
    const meta = cityStats.find((c) => c.name === buddyDraft.value.destCity)
    social.addBuddy({
      destCity: buddyDraft.value.destCity,
      trailId: picked ? picked.id : null,
      trailName: picked ? picked.name : '',
      startDate: buddyDraft.value.startDate,
      endDate: buddyDraft.value.endDate,
      level: Number(buddyDraft.value.level) || 1,
      budget: Number(buddyDraft.value.budget) || 0,
      genderPref: Number(buddyDraft.value.genderPref) || 0,
      slots: Number(buddyDraft.value.slots) || 1,
      tags: buddyDraft.value.tags
        .split(/[,，\s]+/)
        .map((t) => t.trim())
        .filter(Boolean)
        .slice(0, 4),
      intro: buddyDraft.value.intro,
      lat: meta?.center?.[0] || 0,
      lng: meta?.center?.[1] || 0
    })
    publishing.value = false
    ui.toast('招募已发布')
  } catch (e) {
    buddyError.value = e.message
  }
}

const applying = ref('')
const applyMsg = ref('')

function submitApply(b) {
  try {
    social.applyBuddy(b.id, applyMsg.value)
    applying.value = ''
    applyMsg.value = ''
    ui.toast('申请已发出，等发起人确认')
  } catch (e) {
    buddyError.value = e.message
  }
}

const iOwn = (b) => auth.isLogged && b.account === auth.account
const applied = (b) => auth.isLogged && b.applicants.some((a) => a.account === auth.account)

const levelText = { 1: '轻松', 2: '中等', 3: '偏难', 4: '困难', 5: '高强度' }
const levelOf = (n) => levelText[Math.min(5, Math.max(1, Number(n) || 1))]

/* ── 附近 ── */
const locOptions = computed(() =>
  cityStats.map((c) => ({ city: c.name, lat: c.center[0], lng: c.center[1], label: c.name }))
)

const myLabel = computed(() => social.myLoc.label || social.myLoc.city)

function pickLoc(e) {
  const opt = locOptions.value.find((o) => o.city === e.target.value)
  if (opt) social.setMyLoc({ lat: opt.lat, lng: opt.lng, city: opt.city, label: opt.label })
}

const bands = computed(() => {
  const groups = { '500m 内': [], '1km 内': [], '3km 内': [], '5km 内': [] }
  for (const p of social.nearbyPeople) {
    const band = distanceBand(p.meters)
    if (groups[band]) groups[band].push(p)
  }
  return groups
})

/* 点帖子的图看大图 */
const lbOpen = ref(false)
const lbIndex = ref(0)
const lbList = ref([])
function openShots(images, i) {
  lbList.value = images.map((src) => ({ src, title: '' }))
  lbIndex.value = i
  lbOpen.value = true
}

onMounted(() => {
  social.load()
  social.ping()
})
</script>

<template>
  <div class="page">
    <div class="container">
      <header class="head">
        <p class="eyebrow">COMMUNITY</p>
        <h1>走过的人，比攻略更可靠</h1>
        <p class="lead">
          发一条动态记下这条路怎么走，找个人一起分摊营地费，或者看看 5 公里内还有谁在收拾包。
          这里的账号就是站点账号，登录后直接参与。
        </p>
        <div class="head-nums">
          <div><b>{{ social.posts.length }}</b><span>条动态</span></div>
          <div><b>{{ social.openBuddies.length }}</b><span>个招募中</span></div>
          <div><b>{{ social.nearbyPeople.length }}</b><span>位附近山友</span></div>
        </div>
      </header>

      <div class="tabs">
        <button v-for="t in tabs" :key="t.k" :class="{ on: tab === t.k }" @click="pickTab(t.k)">
          <b>{{ t.label }}</b><em>{{ t.sub }}</em>
        </button>
      </div>

      <!-- ══════ 动态 ══════ -->
      <section v-if="tab === 'feed'" class="pane">
        <div v-if="auth.isLogged" class="composer card">
          <div class="who">
            <span class="avatar">{{ auth.initial }}</span>
            <div>
              <b>{{ auth.nickname }}</b>
              <em>说点这条路上别人不知道的</em>
            </div>
          </div>
          <input v-model="draft.title" class="in" placeholder="标题，例：武功山两天，金顶日出值得熬夜" maxlength="60" />
          <textarea
            v-model="draft.body"
            class="in area"
            rows="3"
            placeholder="怎么走、在哪补水、哪段最容易迷路——具体一点对别人更有用"
            maxlength="600"
          ></textarea>
          <div class="row">
            <select v-model="draft.trailId" class="in sel">
              <option value="">不关联路线</option>
              <option v-for="t in trailOptions" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
            <input v-model="draft.tags" class="in tags" placeholder="标签，逗号分隔" maxlength="40" />
            <button class="primary" @click="submitPost">发布</button>
          </div>
          <p v-if="postError" class="err">{{ postError }}</p>
        </div>

        <div v-else class="login-hint card">
          <p>登录后可以发帖、点赞、评论。账号就在本站，不用另外注册。</p>
          <button class="primary" @click="auth.openDialog('login')">登录 / 注册</button>
        </div>

        <div class="feed">
          <article v-for="p in social.feed" :key="p.id" class="post card">
            <header class="ph">
              <span class="avatar sm">{{ p.initial }}</span>
              <div class="meta">
                <b>{{ p.author }}</b>
                <em>{{ ago(p.createdAt) }}<template v-if="p.city"> · {{ p.city }}</template></em>
              </div>
              <router-link v-if="p.trailId" :to="`/route/${p.trailId}`" class="trail-tag">
                {{ p.trailName }} →
              </router-link>
            </header>

            <h2>{{ p.title }}</h2>

            <div v-if="p.images && p.images.length" class="p-imgs" :class="{ multi: p.images.length > 1 }">
              <figure v-for="(src, k) in p.images" :key="k" @click="openShots(p.images, k)">
                <img :src="src" :alt="p.title" loading="lazy" />
              </figure>
            </div>

            <p class="body-text">{{ p.body }}</p>

            <div v-if="p.tags.length" class="tag-row">
              <span v-for="t in p.tags" :key="t">#{{ t }}</span>
            </div>

            <footer class="pf">
              <button class="act" :class="{ on: likedByMe(p) }" @click="like(p)">
                <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
                  <path
                    d="M12 20s-7-4.4-7-9a4 4 0 017-2.6A4 4 0 0119 11c0 4.6-7 9-7 9z"
                    :fill="likedByMe(p) ? 'currentColor' : 'none'"
                    stroke="currentColor"
                    stroke-width="1.6"
                  />
                </svg>
                {{ p.likes.length || '赞' }}
              </button>
              <button class="act" @click="commenting = commenting === p.id ? '' : p.id">
                <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
                  <path d="M4 5h16v11H9l-5 4V5z" fill="none" stroke="currentColor" stroke-width="1.6" />
                </svg>
                {{ p.comments.length || '评论' }}
              </button>
              <span class="spacer"></span>
              <button v-if="p.account === auth.account" class="del" @click="social.removePost(p.id)">
                删除
              </button>
            </footer>

            <div v-if="p.comments.length || commenting === p.id" class="comments">
              <div v-for="c in p.comments" :key="c.id" class="cm">
                <b>{{ c.name }}</b>
                <span>{{ c.text }}</span>
                <em>{{ ago(c.at) }}</em>
              </div>
              <div v-if="commenting === p.id" class="cm-input">
                <input v-model="commentText" class="in" placeholder="写点什么…" @keyup.enter="submitComment(p)" />
                <button class="mini" @click="submitComment(p)">发送</button>
              </div>
            </div>
          </article>
        </div>
      </section>

      <!-- ══════ 找搭子 ══════ -->
      <section v-else-if="tab === 'buddy'" class="pane">
        <div class="matcher card">
          <h3>我的行程</h3>
          <p class="sub">填得越全，匹配分越准。时间完全不重叠的会直接被筛掉。</p>
          <div class="m-row">
            <label>
              <span>出发</span>
              <input v-model="want.startDate" type="date" class="in" />
            </label>
            <label>
              <span>返回</span>
              <input v-model="want.endDate" type="date" class="in" />
            </label>
            <label>
              <span>目的地</span>
              <select v-model="want.city" class="in sel">
                <option value="">不限</option>
                <option v-for="c in cityNames" :key="c" :value="c">{{ c }}</option>
              </select>
            </label>
            <label>
              <span>强度</span>
              <select v-model="want.level" class="in sel">
                <option :value="0">不限</option>
                <option :value="1">轻松</option>
                <option :value="2">中等</option>
                <option :value="3">偏难</option>
                <option :value="4">困难</option>
              </select>
            </label>
            <label class="grow">
              <span>想玩的</span>
              <input v-model="want.tags" class="in" placeholder="重装,摄影,日出" />
            </label>
          </div>
        </div>

        <div class="sec-head">
          <h3>匹配到 {{ matched.length }} 个招募</h3>
          <button v-if="auth.isLogged" class="primary" @click="publishing = !publishing">
            {{ publishing ? '收起' : '发起招募' }}
          </button>
          <button v-else class="primary" @click="auth.openDialog('login')">登录后发起</button>
        </div>

        <div v-if="publishing" class="publish card">
          <div class="m-row">
            <label>
              <span>目的地城市</span>
              <select v-model="buddyDraft.destCity" class="in sel">
                <option v-for="c in cityNames" :key="c" :value="c">{{ c }}</option>
              </select>
            </label>
            <label class="grow">
              <span>走哪条线</span>
              <select v-model="buddyDraft.trailId" class="in sel">
                <option value="">暂不指定</option>
                <option v-for="t in trailOptions" :key="t.id" :value="t.id">{{ t.name }}</option>
              </select>
            </label>
          </div>
          <div class="m-row">
            <label><span>出发</span><input v-model="buddyDraft.startDate" type="date" class="in" /></label>
            <label><span>返回</span><input v-model="buddyDraft.endDate" type="date" class="in" /></label>
            <label>
              <span>强度</span>
              <select v-model="buddyDraft.level" class="in sel">
                <option :value="1">轻松</option>
                <option :value="2">中等</option>
                <option :value="3">偏难</option>
                <option :value="4">困难</option>
              </select>
            </label>
            <label><span>还差几人</span><input v-model="buddyDraft.slots" type="number" min="1" max="8" class="in" /></label>
            <label><span>人均预算</span><input v-model="buddyDraft.budget" type="number" min="0" step="50" class="in" /></label>
          </div>
          <div class="m-row">
            <label class="grow"><span>标签</span><input v-model="buddyDraft.tags" class="in" placeholder="重装,露营,日出" /></label>
          </div>
          <textarea v-model="buddyDraft.intro" class="in area" rows="2" placeholder="说清节奏和分工，比写「有意者联系」有用得多"></textarea>
          <div class="row end">
            <button class="primary" @click="submitBuddy">发布招募</button>
          </div>
          <p v-if="buddyError" class="err">{{ buddyError }}</p>
        </div>

        <div class="buddy-list">
          <article v-for="b in matched" :key="b.id" class="buddy card">
            <div class="b-top">
              <span class="avatar sm">{{ b.initial }}</span>
              <div class="b-meta">
                <b>{{ b.owner }}</b>
                <em>{{ b.destCity }} · {{ b.startDate }} → {{ b.endDate }} · {{ levelOf(b.level) }}</em>
              </div>
              <div class="score" :title="`时间重叠 ${Math.round(b.match.parts.time * 100)}% · 偏好 ${Math.round(b.match.parts.pref * 100)}%`">
                <b>{{ Math.round(b.match.score * 100) }}</b>
                <span>匹配</span>
              </div>
            </div>

            <router-link v-if="b.trailId" :to="`/route/${b.trailId}`" class="b-trail">{{ b.trailName }} →</router-link>

            <p class="b-intro">{{ b.intro }}</p>

            <div class="b-facts">
              <span>还差 <b>{{ b.slots }}</b> 人</span>
              <span>人均 <b>¥{{ b.budget }}</b></span>
              <span>已申请 <b>{{ b.applicants.length }}</b> 人</span>
              <span v-for="t in b.tags" :key="t" class="tag">#{{ t }}</span>
            </div>

            <div v-if="iOwn(b) && b.applicants.length" class="apply-list">
              <div v-for="a in b.applicants" :key="a.account" class="apply">
                <b>{{ a.name }}</b>
                <span>{{ a.msg || '（没留言）' }}</span>
                <template v-if="a.status === 0">
                  <button class="mini ok" @click="social.decideApply(b.id, a.account, 1)">同意</button>
                  <button class="mini no" @click="social.decideApply(b.id, a.account, 2)">拒绝</button>
                </template>
                <em v-else :class="a.status === 1 ? 'passed' : 'rejected'">
                  {{ a.status === 1 ? '已同意' : '已拒绝' }}
                </em>
              </div>
            </div>

            <div class="b-foot">
              <template v-if="!auth.isLogged">
                <button class="mini" @click="auth.openDialog('login')">登录后申请</button>
              </template>
              <template v-else-if="iOwn(b)">
                <span class="own">这是你发起的</span>
              </template>
              <template v-else-if="applied(b)">
                <span class="own">已申请，等对方确认</span>
              </template>
              <template v-else>
                <input v-model="applyMsg" class="in" placeholder="一句话介绍下自己" />
                <button class="mini" @click="submitApply(b)">申请加入</button>
              </template>
            </div>
          </article>

          <p v-if="!matched.length" class="empty">这个时间窗里没有人发招募。换个日期，或者你自己发起一个。</p>
        </div>
      </section>

      <!-- ══════ 附近 ══════ -->
      <section v-else class="pane">
        <div class="nearby-head card">
          <div>
            <h3>我现在在</h3>
            <select class="in sel" :value="social.myLoc.city" @change="pickLoc">
              <option v-for="o in locOptions" :key="o.city" :value="o.city">{{ o.label }}</option>
            </select>
            <p class="sub">
              位置只精确到「城市 + 网格」，对外显示的是距离区间而不是米数——防止被人用三个点反推出你住哪。
              超过 5 公里的人不会出现在列表里。
            </p>
          </div>
          <div class="my-status">
            <span class="dot" :class="{ live: social.iAmOnline }"></span>
            <b>{{ social.iAmOnline ? '在线' : '离线' }}</b>
            <em>点一下报个到</em>
            <button class="mini" @click="social.ping()">报个到</button>
          </div>
        </div>

        <div class="bands">
          <div v-for="(list, band) in bands" :key="band" class="band">
            <div class="band-head"><b>{{ band }}</b><span>{{ list.length }} 人</span></div>
            <div class="band-body">
              <div v-for="p in list" :key="p.account" class="person card">
                <span class="avatar sm">{{ p.initial }}</span>
                <div class="p-meta">
                  <b>{{ p.name }}</b>
                  <em>{{ p.activity }}</em>
                  <div class="p-tags">
                    <span v-for="t in p.tags" :key="t">#{{ t }}</span>
                    <span class="credit">信誉 {{ p.credit }}</span>
                  </div>
                </div>
                <span class="dist">{{ distanceBand(p.meters) }}</span>
              </div>
              <p v-if="!list.length" class="empty sm">这一档暂时没人</p>
            </div>
          </div>
        </div>

        <p class="hint">
          这份列表是演示数据：真实产品里每个用户上报位置后写进 presence 表，30 分钟不活跃自动消失。
          现在只有你一个真实账号，所以其他人是预置样本，用来看匹配和分档的效果。
        </p>
      </section>
    </div>

    <LightBox
      :images="lbList"
      :index="lbIndex"
      :open="lbOpen"
      @close="lbOpen = false"
      @update:index="lbIndex = $event"
    />
  </div>
</template>

<style scoped>
.page {
  padding-top: calc(var(--nav-h) + 28px);
  padding-bottom: 70px;
}

.head h1 {
  font-family: var(--font-serif);
  font-size: clamp(1.5rem, 3vw, 2.1rem);
  font-weight: 600;
  letter-spacing: -0.01em;
  margin-bottom: 10px;
}

.eyebrow {
  font-family: var(--mono);
  font-size: 0.68rem;
  letter-spacing: 0.22em;
  color: var(--sand);
  margin-bottom: 10px;
}

.lead {
  max-width: 660px;
  font-size: 0.9rem;
  color: var(--ink-soft);
  line-height: 1.8;
}

.head-nums {
  display: flex;
  gap: 26px;
  margin-top: 20px;
}

.head-nums div {
  display: flex;
  flex-direction: column;
}

.head-nums b {
  font-size: 1.3rem;
  color: var(--forest-dark);
  font-variant-numeric: tabular-nums;
}

.head-nums span {
  font-size: 0.7rem;
  color: var(--gray);
}

.tabs {
  display: flex;
  gap: 6px;
  margin: 26px 0 20px;
  border-bottom: 1px solid var(--line);
}

.tabs button {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 10px 16px 12px;
  border: none;
  background: none;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  color: var(--gray);
  text-align: left;
}

.tabs button b {
  font-size: 0.9rem;
  font-weight: 500;
}

.tabs button em {
  font-style: normal;
  font-size: 0.68rem;
  opacity: 0.8;
}

.tabs button.on {
  color: var(--forest-dark);
  border-bottom-color: var(--forest);
}

.card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
}

.pane {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.in {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 11px;
  font-size: 0.82rem;
  font-family: inherit;
  color: var(--ink);
  background: #fff;
  outline: none;
}

.in:focus {
  border-color: var(--forest-light);
}

.in.area {
  resize: vertical;
  line-height: 1.7;
}

.in.sel {
  cursor: pointer;
}

.row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.row.end {
  justify-content: flex-end;
}

.primary {
  border: none;
  background: var(--forest);
  color: #fff;
  font-size: 0.8rem;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
}

.primary:hover {
  background: var(--forest-dark);
}

.mini {
  border: 1px solid rgba(45, 90, 61, 0.28);
  background: var(--forest-soft);
  color: var(--forest-dark);
  font-size: 0.74rem;
  padding: 4px 11px;
  border-radius: 999px;
  cursor: pointer;
  white-space: nowrap;
}

.mini:hover {
  background: var(--forest);
  color: #fff;
}

.mini.ok {
  background: var(--forest);
  color: #fff;
}

.mini.no {
  background: #fff;
  color: #a4523f;
  border-color: rgba(164, 82, 63, 0.3);
}

.avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--forest);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  flex-shrink: 0;
}

.avatar.sm {
  width: 30px;
  height: 30px;
  font-size: 0.76rem;
}

.composer {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.composer .who {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 2px;
}

.composer .who b {
  font-size: 0.86rem;
  display: block;
}

.composer .who em {
  font-style: normal;
  font-size: 0.7rem;
  color: var(--gray);
}

.composer .row .tags {
  flex: 1;
}

.composer .row .sel {
  width: 200px;
}

.err {
  font-size: 0.74rem;
  color: #a4523f;
}

.login-hint {
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.login-hint p {
  font-size: 0.84rem;
  color: var(--ink-soft);
}

.feed {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.post {
  padding: 16px 18px 14px;
}

.ph {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.meta b {
  font-size: 0.84rem;
  display: block;
}

.meta em {
  font-style: normal;
  font-size: 0.7rem;
  color: var(--gray);
}

.trail-tag {
  margin-left: auto;
  font-size: 0.72rem;
  color: var(--forest);
  background: var(--forest-soft);
  padding: 3px 10px;
  border-radius: 999px;
  text-decoration: none;
}

.post h2 {
  font-family: var(--font-serif);
  font-size: 1.06rem;
  font-weight: 600;
  margin-bottom: 7px;
  line-height: 1.4;
}

.body-text {
  font-size: 0.84rem;
  line-height: 1.85;
  color: var(--ink-soft);
  white-space: pre-line;
}

.p-imgs {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 6px;
  margin: 10px 0 2px;
}

.p-imgs.multi {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.p-imgs figure {
  margin: 0;
  overflow: hidden;
  border-radius: 9px;
  cursor: zoom-in;
  background: #eef0ec;
  /* 帖子里的图是「带一眼」用的，不占满屏：
     单图固定 240 高铺满整宽，多图排两列各 160 高 */
  height: 240px;
}

.p-imgs img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.4s ease;
}

.p-imgs.multi figure {
  height: 160px;
}

.p-imgs figure:hover img {
  transform: scale(1.03);
}

.tag-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 9px;
}

.tag-row span {
  font-size: 0.71rem;
  color: var(--forest);
}

.pf {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  padding-top: 11px;
  border-top: 1px solid var(--line-soft, #eee);
}

.act {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: none;
  background: none;
  font-size: 0.75rem;
  color: var(--gray);
  cursor: pointer;
  padding: 4px 9px;
  border-radius: 999px;
}

.act:hover {
  background: #f5f3ec;
  color: var(--forest-dark);
}

.act.on {
  color: #c4533f;
}

.spacer {
  flex: 1;
}

.del {
  border: none;
  background: none;
  font-size: 0.72rem;
  color: var(--gray);
  cursor: pointer;
}

.del:hover {
  color: #a4523f;
}

.comments {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--line);
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.cm {
  font-size: 0.78rem;
  display: flex;
  gap: 7px;
  align-items: baseline;
  flex-wrap: wrap;
}

.cm b {
  color: var(--forest-dark);
}

.cm span {
  color: var(--ink-soft);
}

.cm em {
  font-style: normal;
  font-size: 0.68rem;
  color: var(--gray);
}

.cm-input {
  display: flex;
  gap: 7px;
}

.matcher {
  padding: 16px 18px;
}

.matcher h3 {
  font-size: 0.9rem;
  font-weight: 500;
  margin-bottom: 3px;
}

.sub {
  font-size: 0.74rem;
  color: var(--gray);
  line-height: 1.7;
  margin-bottom: 12px;
}

.m-row {
  display: flex;
  gap: 9px;
  flex-wrap: wrap;
  margin-bottom: 9px;
}

.m-row label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 120px;
}

.m-row label.grow {
  flex: 1;
  min-width: 180px;
}

.m-row label span {
  font-size: 0.7rem;
  color: var(--gray);
}

.sec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 4px;
}

.sec-head h3 {
  font-size: 0.92rem;
  font-weight: 500;
}

.publish {
  padding: 16px 18px;
}

.buddy-list {
  display: flex;
  flex-direction: column;
  gap: 11px;
}

.buddy {
  padding: 15px 17px;
}

.b-top {
  display: flex;
  align-items: center;
  gap: 10px;
}

.b-meta b {
  font-size: 0.86rem;
  display: block;
}

.b-meta em {
  font-style: normal;
  font-size: 0.72rem;
  color: var(--gray);
}

.score {
  margin-left: auto;
  text-align: center;
}

.score b {
  display: block;
  font-size: 1.2rem;
  color: var(--forest);
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}

.score span {
  font-size: 0.64rem;
  color: var(--gray);
}

.b-trail {
  display: inline-block;
  margin-top: 8px;
  font-size: 0.73rem;
  color: var(--forest);
  text-decoration: none;
}

.b-intro {
  font-size: 0.82rem;
  color: var(--ink-soft);
  line-height: 1.75;
  margin-top: 7px;
}

.b-facts {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 10px;
  font-size: 0.73rem;
  color: var(--gray);
}

.b-facts b {
  color: var(--forest-dark);
}

.b-facts .tag {
  color: var(--forest);
}

.apply-list {
  margin-top: 11px;
  padding-top: 10px;
  border-top: 1px dashed var(--line);
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.apply {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.77rem;
  flex-wrap: wrap;
}

.apply b {
  color: var(--forest-dark);
}

.apply span {
  color: var(--ink-soft);
}

.apply em {
  font-style: normal;
  font-size: 0.72rem;
}

.apply em.passed {
  color: #3b6d11;
}

.apply em.rejected {
  color: #a4523f;
}

.b-foot {
  margin-top: 11px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
  display: flex;
  gap: 8px;
  align-items: center;
}

.b-foot .in {
  flex: 1;
}

.own {
  font-size: 0.74rem;
  color: var(--gray);
}

.empty {
  padding: 34px 0;
  text-align: center;
  font-size: 0.82rem;
  color: var(--gray);
}

.empty.sm {
  padding: 12px 0;
  font-size: 0.75rem;
}

.nearby-head {
  padding: 16px 18px;
  display: flex;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}

.nearby-head h3 {
  font-size: 0.9rem;
  font-weight: 500;
  margin-bottom: 8px;
}

.nearby-head .sel {
  max-width: 200px;
  margin-bottom: 8px;
}

.nearby-head .sub {
  max-width: 520px;
  margin-bottom: 0;
}

.my-status {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 0.76rem;
  color: var(--ink-soft);
  align-self: flex-start;
}

.my-status em {
  font-style: normal;
  font-size: 0.7rem;
  color: var(--gray);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #c3c0b5;
}

.dot.live {
  background: #5aa469;
  box-shadow: 0 0 0 3px rgba(90, 164, 105, 0.18);
}

.bands {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.band-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 7px;
}

.band-head b {
  font-size: 0.84rem;
  color: var(--forest-dark);
}

.band-head span {
  font-size: 0.7rem;
  color: var(--gray);
}

.band-body {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
}

.person {
  padding: 11px 13px;
  display: flex;
  align-items: flex-start;
  gap: 9px;
}

.p-meta b {
  font-size: 0.83rem;
  display: block;
}

.p-meta em {
  font-style: normal;
  font-size: 0.72rem;
  color: var(--gray);
  display: block;
  margin-top: 1px;
}

.p-tags {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
  margin-top: 4px;
  font-size: 0.68rem;
  color: var(--forest);
}

.p-tags .credit {
  color: var(--sand);
}

.dist {
  margin-left: auto;
  font-size: 0.7rem;
  color: var(--gray);
  white-space: nowrap;
}

.hint {
  font-size: 0.73rem;
  color: var(--gray);
  line-height: 1.8;
  padding: 12px 14px;
  background: #faf8f2;
  border-radius: 8px;
}

@media (max-width: 860px) {
  .band-body {
    grid-template-columns: minmax(0, 1fr);
  }
  .composer .row {
    flex-direction: column;
    align-items: stretch;
  }
  .composer .row .sel {
    width: 100%;
  }
  .login-hint {
    flex-direction: column;
    align-items: flex-start;
  }
  .tabs {
    overflow-x: auto;
  }
  .tabs button {
    white-space: nowrap;
  }
}
</style>
