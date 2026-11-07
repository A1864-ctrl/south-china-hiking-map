// 山友社区的数据层：动态（帖子）/ 找搭子 / 附近的人
// 登录与否都能看：帖子、搭子、路况公开读；写操作需要登录（云端 RLS 兜底）
// 附近的人仍是本机演示数据；myLoc / ping 存本机
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { useAuthStore } from './auth.js'
import { cloud } from '../services/cloud.js'

const CACHE_KEY = 'yejing:social:cache:v1'

/** 两坐标间球面距离（米） */
export function distanceM(a, b) {
  if (!a || !b) return Infinity
  const R = 6371000
  const rad = Math.PI / 180
  const dLat = (b.lat - a.lat) * rad
  const dLng = (b.lng - a.lng) * rad
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(s))
}

/** 距离分档：只给区间不给精确米数，避免被反推住址 */
export function distanceBand(m) {
  if (!isFinite(m)) return '位置未知'
  if (m <= 500) return '500m 内'
  if (m <= 1000) return '1km 内'
  if (m <= 3000) return '3km 内'
  if (m <= 5000) return '5km 内'
  return '5km 外'
}

const HOUR = 3600 * 1000
const DAY = 24 * HOUR
const now = () => Date.now()

/** 演示用的「附近的人」——真实产品里来自 presence 表，这里给一份可看的样本 */
const SEED_PEOPLE = [
  { account: 'demo_a', name: '山野阿野', initial: '野', lat: 23.1069, lng: 113.3247, city: '广州', activity: '正在看东西冲穿越', level: 3, credit: 4.8, tags: ['海岸线', '重装'] },
  { account: 'demo_b', name: '小满', initial: '满', lat: 23.1082, lng: 113.3264, city: '广州', activity: '刚收藏了漓江·杨堤至兴坪', level: 2, credit: 4.6, tags: ['摄影', '慢走'] },
  { account: 'demo_c', name: '老林', initial: '林', lat: 23.1135, lng: 113.3301, city: '广州', activity: '在整理武功山的装备清单', level: 4, credit: 4.9, tags: ['重装', '日出'] },
  { account: 'demo_d', name: '阿青', initial: '青', lat: 23.1201, lng: 113.3388, city: '广州', activity: '在看城市热度排行', level: 1, credit: 4.2, tags: ['城市山'] },
  { account: 'demo_e', name: '石头', initial: '石', lat: 23.1290, lng: 113.3452, city: '广州', activity: '发布了找搭子：船底顶 罗新线', level: 5, credit: 5.0, tags: ['高强度', '露营'] },
  { account: 'demo_f', name: '鹿鸣', initial: '鹿', lat: 23.1410, lng: 113.3602, city: '广州', activity: '刚给「东西冲」点了赞', level: 2, credit: 4.4, tags: ['轻装', '拍照'] }
]

function readCache() {
  try {
    return JSON.parse(localStorage.getItem(CACHE_KEY) || 'null')
  } catch {
    return null
  }
}
function writeCache(state) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(state))
  } catch {
    /* ignore */
  }
}

function toMs(ts) {
  const t = new Date(ts).getTime()
  return Number.isFinite(t) ? t : now()
}
function firstChar(s) {
  return String(s || '').trim().slice(0, 1) || '山'
}

export const useSocialStore = defineStore('social', () => {
  const auth = useAuthStore()

  const cached = readCache()
  const posts = ref(cached?.posts || [])
  const buddies = ref(cached?.buddies || [])
  const people = ref(SEED_PEOPLE)
  const loaded = ref(false)
  /** 我的位置：默认放在广州塔，可在页面上换城市 */
  const myLoc = ref(cached?.myLoc || { lat: 23.1066, lng: 113.3245, city: '广州', label: '广州塔' })
  const pingAt = ref(cached?.pingAt || now())

  function persistLocal() {
    writeCache({ posts: posts.value, buddies: buddies.value, myLoc: myLoc.value, pingAt: pingAt.value })
  }

  /** 从云端拉全量（公开读，游客也能看），失败时保留缓存 */
  async function load() {
    try {
      const [pRes, lRes, cRes, bRes, aRes] = await Promise.all([
        cloud.database.from('posts').select('*').order('created_at', { ascending: false }).limit(100),
        cloud.database.from('post_likes').select('post_id, owner_id'),
        cloud.database.from('post_comments').select('*').order('created_at', { ascending: true }),
        cloud.database.from('buddies').select('*').order('created_at', { ascending: false }).limit(100),
        cloud.database.from('buddy_applications').select('*').order('created_at', { ascending: true })
      ])
      if (pRes.error || lRes.error || cRes.error || bRes.error || aRes.error) return
      const likesBy = {}
      for (const l of lRes.data || []) (likesBy[l.post_id] ||= []).push(l.owner_id)
      const commentsBy = {}
      for (const c of cRes.data || []) {
        ;(commentsBy[c.post_id] ||= []).push({
          id: c.id,
          account: c.owner_id,
          name: c.owner_name || '山友',
          text: c.body,
          at: toMs(c.created_at)
        })
      }
      const appsBy = {}
      for (const a of aRes.data || []) {
        ;(appsBy[a.buddy_id] ||= []).push({
          aid: a.id,
          account: a.owner_id,
          name: a.owner_name || '山友',
          msg: a.msg || '',
          status: a.status,
          at: toMs(a.created_at)
        })
      }
      posts.value = (pRes.data || []).map((p) => ({
        id: p.id,
        account: p.owner_id,
        author: p.owner_name || '山友',
        initial: firstChar(p.owner_name),
        title: p.title,
        body: p.body,
        trailId: p.trail_id,
        trailName: p.trail_name || '',
        city: p.city || '',
        images: p.images || [],
        tags: p.tags || [],
        likes: likesBy[p.id] || [],
        comments: commentsBy[p.id] || [],
        createdAt: toMs(p.created_at)
      }))
      buddies.value = (bRes.data || []).map((b) => ({
        id: b.id,
        account: b.owner_id,
        owner: b.owner_name || '山友',
        initial: firstChar(b.owner_name),
        destCity: b.dest_city,
        trailId: b.trail_id,
        trailName: b.trail_name || '',
        startDate: b.start_date,
        endDate: b.end_date,
        level: b.level,
        budget: b.budget,
        genderPref: b.gender_pref,
        slots: b.slots,
        tags: b.tags || [],
        intro: b.intro || '',
        applicants: appsBy[b.id] || [],
        createdAt: toMs(b.created_at)
      }))
      loaded.value = true
      persistLocal()
    } catch {
      /* 离线：保留缓存里的内容 */
    }
  }

  /* ── 动态 ── */

  /** 发一条动态：登录后才能发，作者就是当前账号 */
  async function addPost({ title, body, trailId, trailName, city, tags, images }) {
    if (!auth.isLogged) throw new Error('登录后才能发帖')
    const row = {
      title: String(title || '').trim() || '无标题',
      body: String(body || '').trim(),
      trail_id: trailId || null,
      trail_name: trailName || '',
      city: city || '',
      tags: tags || [],
      images: images || [],
      owner_name: auth.nickname
    }
    const { data, error } = await cloud.database.from('posts').insert(row).select().single()
    if (error) throw error
    const p = {
      id: data.id,
      account: data.owner_id,
      author: data.owner_name || auth.nickname,
      initial: firstChar(data.owner_name),
      title: data.title,
      body: data.body || '',
      trailId: data.trail_id,
      trailName: data.trail_name || '',
      city: data.city || '',
      images: data.images || [],
      tags: data.tags || [],
      likes: [],
      comments: [],
      createdAt: toMs(data.created_at)
    }
    posts.value = [p, ...posts.value]
    persistLocal()
    return p
  }

  async function removePost(id) {
    const { error } = await cloud.database.from('posts').delete().eq('id', Number(id))
    if (error) return
    posts.value = posts.value.filter((p) => p.id !== Number(id))
    persistLocal()
  }

  /** 点赞：同一账号只能点一次，再点取消 */
  async function toggleLike(id) {
    if (!auth.isLogged) throw new Error('登录后才能点赞')
    const me = auth.account
    const post = posts.value.find((p) => p.id === Number(id))
    if (!post) return
    const liked = post.likes.includes(me)
    if (liked) {
      const { error } = await cloud.database.from('post_likes').delete().match({ post_id: Number(id), owner_id: me })
      if (error) return
      post.likes = post.likes.filter((a) => a !== me)
    } else {
      const { error } = await cloud.database.from('post_likes').insert({ post_id: Number(id) })
      if (error) return
      post.likes = [...post.likes, me]
    }
    persistLocal()
  }

  async function addComment(id, text) {
    if (!auth.isLogged) throw new Error('登录后才能评论')
    const t = String(text || '').trim()
    if (!t) return
    const { data, error } = await cloud.database
      .from('post_comments')
      .insert({ post_id: Number(id), body: t, owner_name: auth.nickname })
      .select()
      .single()
    if (error) throw error
    posts.value = posts.value.map((p) =>
      p.id === Number(id)
        ? {
            ...p,
            comments: [
              ...p.comments,
              { id: data.id, account: data.owner_id, name: data.owner_name || auth.nickname, text: data.body, at: toMs(data.created_at) }
            ]
          }
        : p
    )
    persistLocal()
  }

  const feed = computed(() => [...posts.value].sort((a, b) => b.createdAt - a.createdAt))
  const myPostCount = computed(() =>
    auth.isLogged ? posts.value.filter((p) => p.account === auth.account).length : 0
  )

  /* ── 找搭子 ── */

  async function addBuddy(payload) {
    if (!auth.isLogged) throw new Error('登录后才能发布')
    const row = {
      dest_city: payload.destCity,
      trail_id: payload.trailId || null,
      trail_name: payload.trailName || '',
      start_date: payload.startDate,
      end_date: payload.endDate,
      level: payload.level || 2,
      budget: payload.budget || 0,
      gender_pref: payload.genderPref || 0,
      slots: payload.slots || 1,
      tags: payload.tags || [],
      intro: payload.intro || '',
      owner_name: auth.nickname
    }
    const { data, error } = await cloud.database.from('buddies').insert(row).select().single()
    if (error) throw error
    const b = {
      id: data.id,
      account: data.owner_id,
      owner: data.owner_name || auth.nickname,
      initial: firstChar(data.owner_name),
      destCity: data.dest_city,
      trailId: data.trail_id,
      trailName: data.trail_name || '',
      startDate: data.start_date,
      endDate: data.end_date,
      level: data.level,
      budget: data.budget,
      genderPref: data.gender_pref,
      slots: data.slots,
      tags: data.tags || [],
      intro: data.intro || '',
      applicants: [],
      createdAt: toMs(data.created_at)
    }
    buddies.value = [b, ...buddies.value]
    persistLocal()
    return b
  }

  /** 申请加入：写 buddy_applications，状态 0 = 等待发起人确认 */
  async function applyBuddy(id, msg) {
    if (!auth.isLogged) throw new Error('登录后才能申请')
    const me = auth.account
    const buddy = buddies.value.find((b) => b.id === Number(id))
    if (!buddy || buddy.account === me) return
    if (buddy.applicants.some((a) => a.account === me)) return
    const { data, error } = await cloud.database
      .from('buddy_applications')
      .insert({ buddy_id: Number(id), msg: String(msg || '').trim(), owner_name: auth.nickname })
      .select()
      .single()
    if (error) throw error
    buddy.applicants = [
      ...buddy.applicants,
      { aid: data.id, account: data.owner_id, name: data.owner_name || auth.nickname, msg: data.msg || '', status: data.status, at: toMs(data.created_at) }
    ]
    persistLocal()
  }

  /** 发起人处理申请：同意 1 / 拒绝 2 */
  async function decideApply(buddyId, applicantAccount, status) {
    const buddy = buddies.value.find((b) => b.id === Number(buddyId))
    if (!buddy) return
    const app = buddy.applicants.find((a) => a.account === applicantAccount)
    if (!app?.aid) return
    const { error } = await cloud.database.from('buddy_applications').update({ status }).eq('id', app.aid)
    if (error) return
    buddy.applicants = buddy.applicants.map((a) => (a.aid === app.aid ? { ...a, status } : a))
    persistLocal()
  }

  const openBuddies = computed(() => buddies.value.filter((b) => b.slots > 0))

  /**
   * 匹配打分：时间重叠 35% + 偏好相似 25% + 活跃 15% + 信誉 15% + 距离 10%。
   * 我的行程由页面上的筛选条给出，不填就只看时间窗内的全部。
   */
  function scoreBuddy(b, want) {
    const parts = {}

    // 时间重叠：交集天数 / 我的天数。区间按「含首尾」算 ——
    // 单日行程恰好同一天时差值是 0，按开区间会被误判成不重叠
    if (want.startDate && want.endDate) {
      const DAY_MS = 86400000
      const s1 = new Date(b.startDate).getTime()
      const e1 = new Date(b.endDate).getTime()
      const s2 = new Date(want.startDate).getTime()
      const e2 = new Date(want.endDate).getTime()
      const span = Math.abs(e1 - s1) + DAY_MS
      const mine = Math.abs(e2 - s2) + DAY_MS
      const overlapDays = (Math.min(e1, e2) - Math.max(s1, s2)) / DAY_MS + 1
      const shorter = Math.min(mine, span)
      parts.time = overlapDays <= 0 ? 0 : Math.min(1, (overlapDays * DAY_MS) / Math.max(DAY_MS, shorter))
    } else {
      parts.time = 1
    }

    // 偏好相似：标签 Jaccard + 难度接近
    const myTags = want.tags || []
    if (myTags.length) {
      const a = new Set(myTags)
      const bb = new Set(b.tags || [])
      const inter = [...a].filter((t) => bb.has(t)).length
      const union = new Set([...a, ...bb]).size || 1
      parts.pref = inter / union
    } else {
      parts.pref = 0.6
    }
    if (want.level) {
      const diff = Math.abs(Number(b.level) - Number(want.level))
      parts.pref = parts.pref * 0.7 + Math.max(0, 1 - diff / 3) * 0.3
    }

    // 活跃：最近 3 天内发布算满
    const age = now() - b.createdAt
    parts.active = Math.max(0, 1 - age / (7 * DAY))

    // 信誉：申请人多说明可信
    parts.credit = Math.min(1, (b.applicants.length + 1) / 5)

    // 距离：同城优先
    parts.dist = want.city && b.destCity === want.city ? 1 : 0.3

    const score =
      0.35 * parts.time + 0.25 * parts.pref + 0.15 * parts.active + 0.15 * parts.credit + 0.1 * parts.dist
    return { score, parts, overlap: parts.time }
  }

  /** 按我的行程筛选并打分排序；时间完全不重叠的直接丢掉 */
  function matchBuddies(want) {
    return openBuddies.value
      .map((b) => ({ ...b, match: scoreBuddy(b, want) }))
      .filter((b) => (want.startDate && want.endDate ? b.match.parts.time > 0 : true))
      .sort((a, b) => b.match.score - a.match.score)
  }

  /* ── 附近的人 ── */

  /** 换我的位置（页面上选城市） */
  function setMyLoc(loc) {
    myLoc.value = loc
    pingAt.value = now()
    persistLocal()
  }

  /** 报个到：把「最后活跃」刷新到现在，30 分钟后自动从列表消失 */
  function ping() {
    pingAt.value = now()
    persistLocal()
  }

  const nearbyPeople = computed(() =>
    people.value
      .map((p) => ({ ...p, meters: distanceM(myLoc.value, p) }))
      .filter((p) => p.meters <= 5000)
      .sort((a, b) => a.meters - b.meters)
  )

  /** 我自己是否还在线：5 分钟内报过到 */
  const iAmOnline = computed(() => now() - pingAt.value < 5 * 60 * 1000)

  return {
    posts,
    buddies,
    people,
    myLoc,
    pingAt,
    loaded,
    feed,
    myPostCount,
    openBuddies,
    nearbyPeople,
    iAmOnline,
    load,
    addPost,
    removePost,
    toggleLike,
    addComment,
    addBuddy,
    applyBuddy,
    decideApply,
    matchBuddies,
    scoreBuddy,
    setMyLoc,
    ping
  }
})
