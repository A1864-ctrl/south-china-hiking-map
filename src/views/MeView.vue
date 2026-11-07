<script setup>
/**
 * 个人主页 · 山野手帐
 * 版式刻意避开「整幅大图 + 居中头像 + 顶部标签」的常见做法：
 *   1. 顶部是档案封面条（色块 + 一张贴上去的小照片），图片只占右上一角
 *   2. 中间一条横向数字台账，六格等宽
 *   3. 山野工具条：路况 / 报备 / 营地 / 天气 / 装备库 / 知识库
 *   4. 主体是「左侧目录索引 + 单栏长卷」，滚动联动高亮，不用 tab 切换
 */
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { spots } from '../data/spots.js'
import { routes } from '../data/routes.js'
import { spotPhotos, routePhotoOf } from '../data/photos.js'
import { camps } from '../data/camps.js'
import { knowledge } from '../data/knowledge.js'
import { REPORT_TYPES, REPORT_LEVEL, useFieldStore, WALL_LIMIT } from '../stores/field.js'
import { useAuthStore } from '../stores/auth.js'
import { useFavStore } from '../stores/fav.js'
import { useSocialStore } from '../stores/social.js'
import { useUiStore } from '../stores/ui.js'
import { useFriendsStore } from '../stores/friends.js'
import { REGIONS, GENDERS, citiesOf, regionShort } from '../data/regions.js'
import { cloud } from '../services/cloud.js'
import LightBox from '../components/LightBox.vue'

const auth = useAuthStore()
const fav = useFavStore()
const social = useSocialStore()
const field = useFieldStore()
const friends = useFriendsStore()
const ui = useUiStore()
const router = useRouter()
const route = useRoute()

/* ── 封面照：五张实景轮换 ── */
const BG = [
  { src: 'photos/gal/gal-r29.jpg', label: '武功山 · 金顶穿越' },
  { src: 'photos/gal/gal-s01.jpg', label: '漓江 · 杨堤至兴坪' },
  { src: 'photos/gal/gal-s02.jpg', label: '龙脊梯田 · 平安寨' },
  { src: 'photos/gal/gal-s09.jpg', label: '雾漫小东江' },
  { src: 'photos/gal/gal-s34.jpg', label: '岳麓山 · 桃花岭' }
]
const bg = computed(() => BG[(auth.bgIndex || 0) % BG.length])

/** 大背景：上传了自定义图就铺满整条封面（压暗保证文字可读），否则保持默认绿色 */
const coverBgStyle = computed(() => {
  if (!auth.bgUrl) return {}
  return {
    backgroundImage: `linear-gradient(150deg, rgba(20,43,30,0.88) 0%, rgba(30,66,44,0.84) 58%, rgba(38,77,51,0.8) 100%), url(${auth.bgUrl})`,
    backgroundSize: 'cover',
    backgroundPosition: 'center'
  }
})

/** 点封面空白处 → 换大背景；按钮 / 照片 / 头像 / 文字区不拦 */
function onBandClick(e) {
  if (e.target.closest('button, a, figure, input, .who, .stamp, .cover-photo, .tally-wrap')) return
  bgEl.value?.click()
}

async function cycleBg() {
  if (auth.bgUrl) {
    try {
      await auth.updateProfile({ bgPath: null })
      ui.toast('已恢复默认绿色大背景，可随时重新上传')
    } catch {
      ui.toast('换回预设失败')
    }
    return
  }
  const next = ((auth.bgIndex || 0) + 1) % BG.length
  try {
    await auth.updateProfile({ bg: next })
    ui.toast(`封面换成「${BG[next].label}」`)
  } catch {
    ui.toast('换封面失败')
  }
}

/* ── 账号 ── */
const myAccount = computed(() => auth.account || '')
const myPosts = computed(() => social.posts.filter((p) => p.account === myAccount.value))
const myBuddies = computed(() => social.buddies.filter((b) => b.account === myAccount.value))
const myApplies = computed(() =>
  social.buddies
    .filter((b) => (b.applicants || []).some((a) => a.account === myAccount.value))
    .map((b) => ({ ...b, mine: b.applicants.find((a) => a.account === myAccount.value) }))
)

/* ── 我收到的互动 ── */
const received = computed(() => {
  const list = []
  for (const p of myPosts.value) {
    for (const acc of p.likes) {
      if (acc === myAccount.value) continue
      const who = social.people.find((x) => x.account === acc)
      list.push({ k: 'like', at: p.createdAt, who: who?.name || acc, post: p.title, id: p.id })
    }
    for (const c of p.comments) {
      if (c.account === myAccount.value) continue
      list.push({ k: 'reply', at: c.at, who: c.name, post: p.title, text: c.text, id: p.id })
    }
  }
  return list
})

/* ── 我在别人帖下的留言 ── */
const myComments = computed(() => {
  const out = []
  for (const p of social.posts) {
    if (p.account === myAccount.value) continue
    for (const c of p.comments || []) {
      if (c.account !== myAccount.value) continue
      out.push({ k: 'comment', at: c.at, post: p.title, text: c.text, id: p.id })
    }
  }
  return out
})

/* ── 时间线 ── */
const timeline = computed(() => {
  const list = []
  for (const p of myPosts.value) {
    list.push({ k: 'post', at: p.createdAt, title: p.title, text: p.body, id: p.id, thumb: p.images?.[0] || '' })
  }
  for (const c of myComments.value) list.push(c)
  for (const r of received.value) list.push(r)
  for (const b of myBuddies.value) {
    list.push({ k: 'buddy', at: b.createdAt || 0, title: `${b.destCity} · ${b.trailName || '未指定路线'}`, text: b.intro, id: b.id })
  }
  for (const p of field.myPlans) {
    list.push({ k: 'plan', at: p.createdAt, title: routeNameOfSafe(p.routeId), text: `出行报备 · ${p.days} 天 · ${p.status === 'done' ? '已结束' : '进行中'}`, id: p.id })
  }
  const sorted = list.sort((a, b) => b.at - a.at)
  // 同一条帖子的多个赞合成一条，避免「某某赞了…」刷屏
  const merged = []
  for (const it of sorted) {
    const prev = merged[merged.length - 1]
    if (it.k === 'like' && prev && prev.k === 'like' && prev.post === it.post && prev.at === it.at) {
      prev.who = prev.who + '、' + it.who
      prev.count += 1
      continue
    }
    merged.push({ ...it, count: 1 })
  }
  return merged.slice(0, 14)
})

function routeNameOfSafe(id) {
  const r = routes.find((x) => x.id === Number(id))
  return r ? r.name : '未知路线'
}

/* ── 等级：累计使用时长 + 上传数据量 → 经验值，体现户外经验与活跃度 ── */
const LEVELS = [
  { min: 0, name: '初探' },
  { min: 60, name: '山友' },
  { min: 180, name: '驴友' },
  { min: 420, name: '向导' },
  { min: 800, name: '山神' },
  { min: 1400, name: '传奇' }
]
const myCommentCount = computed(() => {
  let n = 0
  for (const p of social.posts) {
    for (const c of p.comments || []) if (c.account === myAccount.value) n += 1
  }
  return n
})
const myReportCount = computed(() => field.reports.filter((r) => r.account === myAccount.value).length)
const xpItems = computed(() => [
  ['使用时长', Math.floor((auth.profile.activeSeconds || 0) / 600), '10 分钟 +1'],
  ['上传照片', (field.myPhotos || []).length * 8, '1 张 +8'],
  ['发布帖子', myPosts.value.length * 12, '1 帖 +12'],
  ['留言互动', myCommentCount.value * 3, '1 条 +3'],
  ['路况上报', myReportCount.value * 10, '1 条 +10'],
  ['走过的线', walkStats.value.count * 6, '1 条 +6'],
  ['收藏', fav.total() * 2, '1 项 +2'],
  ['发起约伴', myBuddies.value.length * 8, '1 次 +8'],
  ['结交山友', friends.count * 4, '1 位 +4']
])
const xp = computed(() => xpItems.value.reduce((a, i) => a + i[1], 0))
const level = computed(() => {
  let lv = 1
  for (let i = 0; i < LEVELS.length; i += 1) if (xp.value >= LEVELS[i].min) lv = i + 1
  return lv
})
const levelText = computed(() => LEVELS[level.value - 1].name)
const levelProgress = computed(() => {
  if (level.value >= LEVELS.length) return 100
  const cur = LEVELS[level.value - 1].min
  const next = LEVELS[level.value].min
  return Math.min(99, Math.round(((xp.value - cur) / (next - cur)) * 100))
})
const toNext = computed(() => (level.value >= LEVELS.length ? 0 : LEVELS[level.value].min - xp.value))
const usageHours = computed(() => ((auth.profile.activeSeconds || 0) / 3600).toFixed(1))

/* ── 收藏与图 ── */
const favSpots = computed(() => fav.mine.spot.map((n) => spots.find((s) => s.name === n)).filter(Boolean))
const favRoutes = computed(() => fav.mine.route.map((n) => routes.find((r) => r.name === n)).filter(Boolean))

const spotCover = (s) => {
  const list = spotPhotos(s.name)
  if (list.length) return list[0].src
  const r = routes.find((x) => x.name.includes(s.name) || s.name.includes(x.name.slice(0, 3)))
  if (r) {
    const p = routePhotoOf(r, r.terrain)
    if (p) return p.src
  }
  return ''
}
const routeCover = (r) => {
  const p = routePhotoOf(r, r.terrain)
  return p ? p.src : ''
}

/* ── 走过的路线 ── */
const walked = computed(() => field.myWalked)
const walkStats = computed(() => field.walkStats)

/* ── 照片墙：帖子配图 + 走过/收藏的路线封面 + 收藏景点，去重后铺开 ── */
const photoWall = computed(() => {
  const seen = new Set()
  const out = []
  const push = (src, title, caption, extra = {}) => {
    if (!src || seen.has(src)) return
    seen.add(src)
    out.push({ src, title, caption, ...extra })
  }
  // 自己上传的最优先：这是「旅途中拍的」，比聚合来的封面更重要
  for (const ph of field.myPhotos) push(ph.src, ph.title, '我上传的', { mine: true, id: ph.id, at: ph.at })
  for (const p of myPosts.value) for (const src of p.images || []) push(src, p.title, '我发布的')
  for (const r of walked.value) push(routeCover(r), r.name, `${r.distance}km · ↑${r.climb}m`)
  for (const r of favRoutes.value) push(routeCover(r), r.name, '收藏的路线')
  for (const s of favSpots.value) push(spotCover(s), s.name, `${s.city} · ${s.type}`)
  return out
})

/* ── 工具条 ── */
const tools = computed(() => [
  {
    k: 'reports', to: '/reports', name: '路况上报', en: 'TRAIL STATUS',
    val: `${field.approvedReports.length}`, unit: '条已挂载',
    note: field.pendingReports.length ? `${field.pendingReports.length} 条待审核` : '塌方 · 杂草 · 水源 · 蜂群',
    tone: '#a9462f'
  },
  {
    k: 'safety', to: '/safety', name: '安全报备', en: 'TRIP PLAN',
    val: field.activePlan ? '进行中' : '未报备', unit: '',
    note: field.activePlan ? `${routeNameOfSafe(field.activePlan.routeId)} · ${field.activePlan.checkins.length} 次打卡` : '登记路线 · 紧急联系人',
    tone: field.activePlan ? '#2d5a3d' : '#8a6d2f'
  },
  {
    k: 'camps', to: '/camps', name: '营地库', en: 'CAMPSITES',
    val: `${camps.length}`, unit: '处营地',
    note: `可明火 ${camps.filter((c) => c.fire !== '禁止').length} · 有水源 ${camps.filter((c) => !c.water.startsWith('无')).length}`,
    tone: '#2f6f9e'
  },
  {
    k: 'weather', to: '/weather', name: '点位天气', en: 'MOUNTAIN WX',
    val: '7 天', unit: '按经纬度',
    note: '降水 · 风力 · 雷电预警',
    tone: '#4a5a7a'
  },
  {
    k: 'gear', to: '/gear-lab', name: '装备库', en: 'GEAR LIB',
    val: `${field.myGear.length}`, unit: '件装备',
    note: `已拥有 ${field.myGear.filter((g) => g.owned).length} 件 · 已存 ${field.myLists.length} 份清单`,
    tone: '#8a6d2f'
  },
  {
    k: 'learn', to: '/learn', name: '山野知识库', en: 'LNT & FIRST AID',
    val: `${knowledge.length}`, unit: '篇',
    note: '无痕山林 8 篇 · 急救 8 篇',
    tone: '#2d5a3d'
  }
])

/* ── 目录与滚动联动 ── */
const SECTIONS = [
  { k: 'feed', no: '01', label: '动态流' },
  { k: 'buddy', no: '02', label: '约伴' },
  { k: 'tracks', no: '03', label: '我的轨迹' },
  { k: 'posts', no: '04', label: '我发布的帖子' },
  { k: 'photos', no: '05', label: '照片墙' },
  { k: 'fav', no: '06', label: '收藏' },
  { k: 'safety', no: '07', label: '安全报备' },
  { k: 'friends', no: '08', label: '山友' }
]
const active = ref('feed')
const secRefs = ref({})
let ticking = false

const counts = computed(() => ({
  feed: timeline.value.length,
  buddy: myBuddies.value.length + myApplies.value.length,
  tracks: walked.value.length,
  posts: myPosts.value.length,
  photos: photoWall.value.length,
  fav: fav.total(),
  safety: field.myPlans.length,
  friends: friends.count
}))

function setSec(k, el) {
  if (el) secRefs.value[k] = el
}

function jump(k) {
  const el = secRefs.value[k]
  if (!el) return
  const top = el.getBoundingClientRect().top + window.scrollY - 96
  window.scrollTo({ top, behavior: 'smooth' })
  active.value = k
}

/** 按滚动位置判定当前段落：取「顶部已越过阅读线」的最后一段，比交叉比例稳 */
function onScroll() {
  if (ticking) return
  ticking = true
  requestAnimationFrame(() => {
    ticking = false
    const line = window.scrollY + 190
    let cur = SECTIONS[0].k
    for (const s of SECTIONS) {
      const el = secRefs.value[s.k]
      if (!el) continue
      const top = el.getBoundingClientRect().top + window.scrollY
      if (top <= line) cur = s.k
    }
    if (window.innerHeight + window.scrollY >= document.body.scrollHeight - 60) cur = SECTIONS[SECTIONS.length - 1].k
    active.value = cur
  })
}

onMounted(() => {
  auth.ensureFresh()
  field.ensureGear()
  window.addEventListener('scroll', onScroll, { passive: true })
  nextTick(() => {
    onScroll()
    // 兼容老链接 ?tab=fav / ?tab=buddy / ?tab=about
    const t = String(route.query.tab || '')
    const map = { fav: 'fav', buddy: 'buddy', feed: 'feed', about: 'safety' }
    if (map[t]) setTimeout(() => jump(map[t]), 120)
  })
  timer = setInterval(() => {
    now.value = Date.now()
    auth.ensureFresh()
  }, 15000)
  auth.touch()
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  if (timer) clearInterval(timer)
})

const now = ref(Date.now())
let timer = null
const loginState = computed(() => (auth.isLogged ? 'WorkBuddy 账号登录' : '未登录'))

function ago(ts) {
  if (!ts) return ''
  const d = Date.now() - ts
  const m = Math.floor(d / 60000)
  if (m < 1) return '刚刚'
  if (m < 60) return `${m} 分钟前`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} 小时前`
  const dd = Math.floor(h / 24)
  if (dd < 30) return `${dd} 天前`
  return `${Math.floor(dd / 30)} 个月前`
}

/* ── 收藏分段 ── */
const favTab = ref('spot')

/* ── 编辑资料：头像 / 封面 / 昵称 / 签名 / 性别 / 地区 ── */
const editing = ref(false)
const form = ref({ nickname: '', bio: '', gender: 0, regionProvince: '', regionCity: '', bg: 0 })
const savingProfile = ref(false)
const uploadingAvatar = ref(false)
const uploadingBg = ref(false)
const avatarEl = ref(null)
const bgEl = ref(null)
const formCities = computed(() => citiesOf(form.value.regionProvince))
const regionLabel = computed(() => regionShort(auth.profile.regionProvince, auth.profile.regionCity))
const genderLabel = computed(() =>
  auth.profile.gender ? GENDERS.find((g) => g.v === auth.profile.gender)?.label || '' : ''
)

function openEdit() {
  form.value = {
    nickname: auth.nickname,
    bio: auth.bio || '',
    gender: auth.profile.gender || 0,
    regionProvince: auth.profile.regionProvince || '',
    regionCity: auth.profile.regionCity || '',
    bg: auth.bgIndex || 0
  }
  editing.value = true
}

function pickBg(i) {
  form.value.bg = i
}

/** 恢复默认绿色大背景 */
async function clearBand() {
  try {
    await auth.updateProfile({ bgPath: null })
    ui.toast('已恢复默认绿色大背景')
  } catch (err) {
    ui.toast(err.message || '操作失败')
  }
}

/** 选图 → 本地压缩 → 传云存储 → 写进资料表 */
async function uploadProfileImage(file, kind) {
  if (!file) return
  if (!/^image\//.test(file.type)) throw new Error('请选择图片文件')
  if (file.size > 5 * 1024 * 1024) throw new Error('图片别超过 5MB')
  const data = await compress(file, kind === 'avatar' ? 400 : 1600, 0.82)
  const blob = await (await fetch(data)).blob()
  const path = cloud.storage.sharedPath(
    auth.account,
    `${kind}/${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}.jpg`
  )
  await cloud.storage.upload(path, blob, { contentType: 'image/jpeg', upsert: false })
  if (kind === 'avatar') {
    await auth.updateProfile({ avatarPath: path })
  } else {
    await auth.updateProfile({ bgPath: path })
  }
}

async function onAvatarPick(e) {
  const f = e.target.files && e.target.files[0]
  e.target.value = ''
  uploadingAvatar.value = true
  try {
    await uploadProfileImage(f, 'avatar')
    ui.toast('头像已更新')
  } catch (err) {
    ui.toast(err.message || '头像上传失败')
  } finally {
    uploadingAvatar.value = false
  }
}

async function onBgPick(e) {
  const f = e.target.files && e.target.files[0]
  e.target.value = ''
  uploadingBg.value = true
  try {
    await uploadProfileImage(f, 'bg')
    ui.toast('大背景已更新，立即生效')
  } catch (err) {
    ui.toast(err.message || '大背景上传失败')
  } finally {
    uploadingBg.value = false
  }
}

async function saveEdit() {
  const n = form.value.nickname.trim()
  if (!n) return ui.toast('昵称不能为空')
  if (n.length < 2) return ui.toast('昵称至少 2 个字')
  savingProfile.value = true
  try {
    await auth.updateProfile({
      nickname: n,
      bio: form.value.bio.trim(),
      gender: form.value.gender,
      regionProvince: form.value.regionProvince,
      regionCity: form.value.regionCity,
      bg: form.value.bg
    })
    editing.value = false
    ui.toast('资料已更新')
  } catch (err) {
    ui.toast(err.message || '保存失败')
  } finally {
    savingProfile.value = false
  }
}

/* ── 山友（好友）：搜索 / 申请 / 同意 / 删除 ── */
const friendKw = ref('')
async function doSearch() {
  if (!friendKw.value.trim()) return ui.toast('先输入昵称或账号 ID')
  try {
    await friends.search(friendKw.value)
  } catch (err) {
    ui.toast(err.message || '搜索失败')
  }
}
async function addFriend(uid) {
  try {
    const r = await friends.add(uid)
    ui.toast(r && r.autoAccepted ? '对方正好也申请了你，已成为好友' : '好友申请已发送，等对方同意')
  } catch (err) {
    ui.toast(err.message || '发送失败')
  }
}
async function acceptIncoming(uid) {
  const req = friends.incoming.find((o) => o.uid === uid)
  if (!req) return
  try {
    await friends.respond(req.rid, 1)
    ui.toast('已同意，你们现在是好友')
  } catch (err) {
    ui.toast(err.message || '操作失败')
  }
}
async function respondReq(rid, ok) {
  try {
    await friends.respond(rid, ok ? 1 : 2)
    ui.toast(ok ? '已同意' : ok === false ? '已拒绝' : '已撤回')
  } catch (err) {
    ui.toast(err.message || '操作失败')
  }
}
async function dropFriend(uid, name) {
  if (!window.confirm(`确定删除好友「${name}」吗？双方都会解除关系。`)) return
  try {
    await friends.removeFriend(uid)
    ui.toast('已删除好友')
  } catch (err) {
    ui.toast(err.message || '删除失败')
  }
}
const STATE_LABEL = { friends: '已是好友', pending_out: '已申请' }

/* ── 账号与安全：改密 / 邮箱找回 ── */
const secOpen = ref(false)
const pwForm = ref({ old: '', next: '', again: '' })
const changingPw = ref(false)
const resetOpen = ref(false)
const resetStep = ref(1)
const resetForm = ref({ email: '', code: '', next: '' })
const resetBusy = ref(false)

function pwOk(v) {
  return v.length >= 8 && /[a-zA-Z]/.test(v) && /\d/.test(v)
}
async function doChangePw() {
  const { old: o, next, again } = pwForm.value
  if (!o) return ui.toast('请输入当前密码')
  if (!pwOk(next)) return ui.toast('新密码至少 8 位，且同时包含字母和数字')
  if (next !== again) return ui.toast('两次输入的新密码不一致')
  changingPw.value = true
  try {
    await auth.changePassword(o, next)
    secOpen.value = false
    pwForm.value = { old: '', next: '', again: '' }
    ui.toast('密码已修改')
  } catch (err) {
    ui.toast(err.message || '修改失败：当前密码可能不对')
  } finally {
    changingPw.value = false
  }
}
async function doSendReset() {
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(resetForm.value.email)) return ui.toast('请输入正确的邮箱地址')
  resetBusy.value = true
  try {
    await auth.sendResetCode(resetForm.value.email)
    resetStep.value = 2
    ui.toast('验证码已发送到邮箱')
  } catch (err) {
    ui.toast(err.message || '发送失败：确认该邮箱已绑定账号')
  } finally {
    resetBusy.value = false
  }
}
async function doCompleteReset() {
  const { code, next } = resetForm.value
  if (!/^\d{4,8}$/.test(code)) return ui.toast('请输入邮箱里的验证码')
  if (!pwOk(next)) return ui.toast('新密码至少 8 位，且同时包含字母和数字')
  resetBusy.value = true
  try {
    await auth.completeReset(code, next)
    resetOpen.value = false
    resetStep.value = 1
    resetForm.value = { email: '', code: '', next: '' }
    ui.toast('密码已重置，已自动登录')
  } catch (err) {
    ui.toast(err.message || '重置失败：验证码可能已过期')
  } finally {
    resetBusy.value = false
  }
}
function logout() {
  auth.logout()
  router.push('/')
}

/* ── 灯箱 ── */
const lbOpen = ref(false)
const lbIndex = ref(0)
const lbImages = ref([])
function openWall(i) {
  lbImages.value = photoWall.value
  lbIndex.value = i
  lbOpen.value = true
}
function openPost(p) {
  lbImages.value = (p.images || []).map((src) => ({ src, title: p.title, caption: '我发布的动态配图' }))
  lbIndex.value = 0
  lbOpen.value = true
}

/* ── 照片上传：本地压缩后存 localStorage ── */
const fileEl = ref(null)
const uploading = ref(false)
const uploadedCount = computed(() => field.myPhotos.length)

function compress(file, maxSide = 1280, quality = 0.72) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    const url = URL.createObjectURL(file)
    img.onload = () => {
      const scale = Math.min(1, maxSide / Math.max(img.width, img.height))
      const c = document.createElement('canvas')
      c.width = Math.max(1, Math.round(img.width * scale))
      c.height = Math.max(1, Math.round(img.height * scale))
      const ctx = c.getContext('2d')
      ctx.drawImage(img, 0, 0, c.width, c.height)
      URL.revokeObjectURL(url)
      let data = c.toDataURL('image/jpeg', quality)
      if (data.length > 260000) data = c.toDataURL('image/jpeg', 0.5)
      resolve(data)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('这张图读不出来，换一张试试'))
    }
    img.src = url
  })
}

async function onPick(e) {
  const files = [...(e.target.files || [])].slice(0, 4)
  e.target.value = ''
  if (!files.length) return
  uploading.value = true
  let ok = 0
  for (const f of files) {
    try {
      const src = await compress(f)
      field.addPhoto({ src, title: f.name.replace(/\.[^.]+$/, '') })
      ok++
    } catch (err) {
      ui.toast(err.message || '这张图处理失败')
    }
  }
  uploading.value = false
  if (ok) ui.toast(`已加 ${ok} 张到照片墙（压缩后存在本机）`)
}

function delPhoto(id) {
  field.removePhoto(id)
  ui.toast('已从照片墙移除')
}

/* ── 安全报备：快速打卡 ── */
const checkNote = ref('')
function doCheckin() {
  const p = field.activePlan
  if (!p) return router.push('/safety')
  field.checkin(p.id, checkNote.value, 'safe')
  checkNote.value = ''
  ui.toast('已平安打卡')
}
function finishPlan() {
  const p = field.activePlan
  if (!p) return
  field.closePlan(p.id)
  ui.toast('报备已关闭，欢迎回来')
}

const goSpot = (s) => router.push(`/spot/${encodeURIComponent(s.name)}`)
const goRoute = (r) => router.push(`/route/${r.id}`)

function reportMeta(k) {
  return REPORT_TYPES.find((t) => t.k === k) || REPORT_TYPES[0]
}
function levelMeta(v) {
  return REPORT_LEVEL.find((l) => l.v === Number(v)) || REPORT_LEVEL[0]
}

/* 我的报备记录 */
const myReports = computed(() => field.reports.filter((r) => r.by === (auth.nickname || '')).slice(0, 4))
</script>

<template>
  <div class="page">
    <!-- 未登录 -->
    <div v-if="!auth.isLogged" class="gate">
      <div class="gate-card">
        <span class="gate-mark">
          <svg viewBox="0 0 24 24" width="26" height="26">
            <path d="M12 12a4 4 0 100-8 4 4 0 000 8zm-7 8a7 7 0 1114 0" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
        </span>
        <h1>这是你的山野手帐</h1>
        <p>走过的线、发过的帖、约过的人、传过的照片，都会按时间记在这本册子里。</p>
        <button class="primary" @click="auth.openDialog('login')">登录 / 注册</button>
      </div>
    </div>

    <template v-else>
      <!-- ══════════ 封面条 ══════════ -->
      <header class="cover" :style="coverBgStyle" title="点空白处上传自定义大背景" @click="onBandClick">
        <span class="band-hint">＋ 上传自定义大背景</span>
        <svg class="topo" viewBox="0 0 1200 260" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 200c90-40 150-10 220-40s130-80 210-60 120 70 210 40 150-90 240-60 180 80 320 40" />
          <path d="M0 228c100-32 160-4 236-34s128-72 206-54 118 64 208 36 152-84 242-56 176 74 308 36" />
          <path d="M0 176c80-44 140-16 208-46s132-84 214-64 122 74 214 44 148-86 236-58 178 78 328 38" />
        </svg>

        <div class="cover-in">
          <div class="identity">
            <span class="stamp" :class="{ 'has-img': auth.avatarUrl }" title="点击更换头像" @click.stop="avatarEl.click()">
              <img v-if="auth.avatarUrl" :src="auth.avatarUrl" alt="头像" />
              <template v-else>{{ auth.initial }}</template>
            </span>
            <div class="who">
              <p class="eyebrow">FIELD RECORD · 山野手帐</p>
              <h1>
                {{ auth.nickname }}
                <span class="lv">Lv.{{ level }} {{ levelText }}</span>
              </h1>
              <p class="meta">
                <span class="mono">{{ auth.account }}</span>
                <i>·</i> 加入 {{ auth.joinDate || '—' }}
                <i>·</i> {{ loginState }}
              </p>
              <p class="bio">{{ auth.bio || '还没写签名。点下面「编辑资料」写一句。' }}</p>
              <p v-if="regionLabel || genderLabel" class="meta sub-meta">
                <span v-if="regionLabel">{{ regionLabel }}</span>
                <template v-if="regionLabel && genderLabel"><i>·</i></template>
                <span v-if="genderLabel">{{ genderLabel }}</span>
              </p>
              <div class="who-acts">
                <button @click="openEdit">
                  <svg viewBox="0 0 24 24" width="12" height="12"><path d="M4 20h4L19 9l-4-4L4 16v4z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" /></svg>
                  编辑资料
                </button>
                <button @click="cycleBg">换封面</button>
                <button class="quiet" @click="logout">退出</button>
              </div>
            </div>
          </div>

          <figure class="cover-photo" @click="cycleBg" title="点一下换一张封面">
            <img :src="bg.src" :alt="bg.label" />
            <figcaption>
              <span>{{ bg.label }}</span>
              <em>换一张</em>
            </figcaption>
          </figure>
        </div>
      </header>

      <!-- ══════════ 数字台账 ══════════ -->
      <div class="tally-wrap">
        <div class="tally">
          <div class="cell">
            <b>{{ walkStats.count }}</b><span>走过的线</span>
          </div>
          <div class="cell">
            <b>{{ walkStats.km }}<i>km</i></b><span>累计里程</span>
          </div>
          <div class="cell">
            <b>{{ walkStats.climb.toLocaleString() }}<i>m</i></b><span>累计爬升</span>
          </div>
          <div class="cell">
            <b>{{ myPosts.length }}</b><span>发布帖子</span>
          </div>
          <div class="cell">
            <b>{{ myBuddies.length + myApplies.length }}</b><span>约伴</span>
          </div>
          <div class="cell">
            <b>{{ fav.total() }}</b><span>收藏</span>
          </div>
        </div>
      </div>

      <div class="wrap">
        <!-- ══════════ 山野工具箱 ══════════ -->
        <section class="kit">
          <div class="kit-head">
            <h2>山野工具</h2>
            <p>出行前后真正会用到的六件事，点进去都能直接用。</p>
          </div>
          <div class="kit-grid">
            <router-link v-for="t in tools" :key="t.k" :to="t.to" class="tool" :style="{ '--tone': t.tone }">
              <div class="tool-top">
                <span class="tool-dot"></span>
                <em>{{ t.en }}</em>
              </div>
              <h3>{{ t.name }}</h3>
              <p class="tool-val">{{ t.val }}<i v-if="t.unit">{{ t.unit }}</i></p>
              <p class="tool-note">{{ t.note }}</p>
              <span class="tool-go">进入 →</span>
            </router-link>
          </div>
        </section>

        <!-- ══════════ 目录 + 长卷 ══════════ -->
        <div class="spread">
          <aside class="index">
            <p class="idx-title">目录 <em>CONTENTS</em></p>
            <nav>
              <a
                v-for="s in SECTIONS"
                :key="s.k"
                href="#"
                :class="{ on: active === s.k }"
                @click.prevent="jump(s.k)"
              >
                <em>{{ s.no }}</em>
                <span>{{ s.label }}</span>
                <b>{{ counts[s.k] }}</b>
              </a>
            </nav>
            <div class="idx-card">
              <p class="idx-lv">Lv.{{ level }} · {{ levelText }}</p>
              <div class="lv-bar"><i :style="{ width: levelProgress + '%' }"></i></div>
              <p class="idx-tip">
                {{ toNext ? `再攒 ${toNext} 点经验升 Lv.${level + 1}` : '已是最高等级' }}
              </p>
              <p class="idx-rule">累计在线 {{ usageHours }} 小时 · 经验 {{ xp }}</p>
              <details class="xp-more">
                <summary>经验从哪来</summary>
                <p v-for="it in xpItems" :key="it[0]"><span>{{ it[0] }}</span><b>{{ it[1] }}</b><i>{{ it[2] }}</i></p>
              </details>
            </div>
            <div class="idx-card">
              <p class="idx-lv">账号与安全</p>
              <p class="sec-line">地区 <b>{{ regionLabel || '未填写' }}</b><i v-if="genderLabel">{{ genderLabel }}</i></p>
              <p class="sec-line">手机 <b>{{ auth.maskedPhone || '未绑定' }}</b></p>
              <p class="sec-line">邮箱 <b>{{ auth.maskedEmail || '未绑定' }}</b></p>
              <div class="sec-acts">
                <button class="mini" @click="secOpen = true">修改密码</button>
                <button class="mini" @click="resetOpen = true">邮箱找回密码</button>
              </div>
              <p class="idx-rule">换绑手机号暂未开放（平台限制）</p>
            </div>
            <router-link to="/versions" class="idx-link">看每轮改了什么 →</router-link>
          </aside>

          <main class="body">
            <!-- 01 动态流 -->
            <section :ref="(el) => setSec('feed', el)" data-k="feed" class="block">
              <header class="b-head">
                <span class="b-no">01</span>
                <h2>动态流</h2>
                <em>收藏 · 留言 · 互动</em>
              </header>

              <!-- 收藏掠影 -->
              <div v-if="favSpots.length || favRoutes.length" class="strip">
                <div class="strip-head">
                  <span>最近收藏</span>
                  <a href="#" @click.prevent="jump('fav')">全部 {{ fav.total() }} 项 →</a>
                </div>
                <div class="strip-row">
                  <button
                    v-for="r in favRoutes.slice(0, 3)"
                    :key="'sr' + r.id"
                    class="strip-item"
                    @click="goRoute(r)"
                  >
                    <img :src="routeCover(r)" :alt="r.name" loading="lazy" />
                    <span>{{ r.name }}</span>
                    <em>路线</em>
                  </button>
                  <button
                    v-for="s in favSpots.slice(0, 3)"
                    :key="'ss' + s.name"
                    class="strip-item"
                    @click="goSpot(s)"
                  >
                    <img :src="spotCover(s)" :alt="s.name" loading="lazy" />
                    <span>{{ s.name }}</span>
                    <em>景点</em>
                  </button>
                </div>
              </div>

              <ol v-if="timeline.length" class="line">
                <li v-for="(it, i) in timeline" :key="i" :class="'t-' + it.k">
                  <span class="dot"></span>
                  <div class="line-body">
                    <p class="line-top">
                      <b v-if="it.k === 'post'">我发布了动态</b>
                      <b v-else-if="it.k === 'comment'">我在「{{ it.post }}」下留言</b>
                      <b v-else-if="it.k === 'like'">{{ it.who }} 赞了我的「{{ it.post }}」</b>
                      <b v-else-if="it.k === 'reply'">{{ it.who }} 评论了我的「{{ it.post }}」</b>
                      <b v-else-if="it.k === 'buddy'">我发起了约伴</b>
                      <b v-else-if="it.k === 'plan'">我做了出行报备</b>
                      <em>{{ ago(it.at) }}</em>
                    </p>
                    <p v-if="it.k === 'post'" class="line-title">{{ it.title }}</p>
                    <p v-if="it.text" class="line-text">{{ it.text }}</p>
                    <p v-if="it.k === 'buddy' || it.k === 'plan'" class="line-title">{{ it.title }}</p>
                    <img v-if="it.thumb" :src="it.thumb" class="line-thumb" :alt="it.title || ''" loading="lazy" />
                  </div>
                </li>
              </ol>
              <div v-else class="empty">
                <p>这本册子还是空的。</p>
                <p class="empty-sub">发一条动态、收藏一个景点、或者约一次伴，这里就开始有记录了。</p>
                <div class="empty-acts">
                  <router-link to="/community" class="btn-line">去社区发帖</router-link>
                  <router-link to="/spots" class="btn-line">逛逛景点</router-link>
                </div>
              </div>
            </section>

            <!-- 02 约伴 -->
            <section :ref="(el) => setSec('buddy', el)" data-k="buddy" class="block">
              <header class="b-head">
                <span class="b-no">02</span>
                <h2>约伴</h2>
                <em>我发起的 · 我申请的</em>
              </header>

              <div class="two-col">
                <div class="col-card">
                  <div class="col-head">
                    <span>我发起的</span><b>{{ myBuddies.length }}</b>
                  </div>
                  <div v-if="myBuddies.length" class="mini-list">
                    <article v-for="b in myBuddies" :key="b.id" class="buddy">
                      <p class="buddy-t">{{ b.destCity }} · {{ b.trailName || '未指定路线' }}</p>
                      <p class="buddy-d">{{ b.startDate }} → {{ b.endDate }} · 还差 {{ b.slots }} 人 · 人均 ¥{{ b.budget }}</p>
                      <p class="buddy-i">{{ b.intro }}</p>
                      <div v-if="b.applicants.length" class="applies">
                        <div v-for="a in b.applicants" :key="a.account" class="apply">
                          <b>{{ a.name }}</b>
                          <span>{{ a.msg || '（没留言）' }}</span>
                          <template v-if="a.status === 0">
                            <button class="mini ok" @click="social.decideApply(b.id, a.account, 1)">同意</button>
                            <button class="mini no" @click="social.decideApply(b.id, a.account, 2)">拒绝</button>
                          </template>
                          <em v-else :class="a.status === 1 ? 'passed' : 'rejected'">{{ a.status === 1 ? '已同意' : '已拒绝' }}</em>
                        </div>
                      </div>
                    </article>
                  </div>
                  <p v-else class="mini-empty">还没发起过。<router-link to="/community?tab=buddy">发一条招募 →</router-link></p>
                </div>

                <div class="col-card">
                  <div class="col-head">
                    <span>我申请的</span><b>{{ myApplies.length }}</b>
                  </div>
                  <div v-if="myApplies.length" class="mini-list">
                    <article v-for="b in myApplies" :key="b.id" class="buddy">
                      <p class="buddy-t">{{ b.destCity }} · {{ b.trailName || '未指定路线' }}</p>
                      <p class="buddy-d">{{ b.startDate }} → {{ b.endDate }} · 发起人 {{ b.owner }}</p>
                      <p class="state" :class="'s' + b.mine.status">
                        {{ b.mine.status === 0 ? '等待确认' : b.mine.status === 1 ? '已通过' : '未通过' }}
                      </p>
                    </article>
                  </div>
                  <p v-else class="mini-empty">还没申请过别人的约伴。</p>
                </div>
              </div>
            </section>

            <!-- 03 我的轨迹 -->
            <section :ref="(el) => setSec('tracks', el)" data-k="tracks" class="block">
              <header class="b-head">
                <span class="b-no">03</span>
                <h2>我的轨迹</h2>
                <em>走过的线，都算数</em>
              </header>

              <div class="walk-bar">
                <div><b>{{ walkStats.count }}</b><span>条</span><em>已走</em></div>
                <div><b>{{ walkStats.km }}</b><span>km</span><em>里程</em></div>
                <div><b>{{ walkStats.climb.toLocaleString() }}</b><span>m</span><em>爬升</em></div>
                <div><b>{{ walkStats.days.toFixed(1) }}</b><span>天</span><em>在野</em></div>
              </div>

              <div v-if="walked.length" class="cards">
                <article v-for="r in walked" :key="r.id" class="card-route" @click="goRoute(r)">
                  <figure><img :src="routeCover(r)" :alt="r.name" loading="lazy" /></figure>
                  <div class="cr-body">
                    <p class="cr-name">{{ r.name }}</p>
                    <p class="cr-meta">{{ r.province }} · {{ r.city }} · {{ r.terrain }}</p>
                    <p class="cr-nums">
                      <b>{{ r.distance }}</b> km<i></i><b>{{ r.climb }}</b> m<i></i>{{ r.days }}
                    </p>
                  </div>
                </article>
              </div>
              <div v-else class="empty small">
                <p>还没有标记走过的路线。</p>
                <p class="empty-sub">打开任意一条路线详情，点「标记走过」，它会出现在这里并累计里程。</p>
                <router-link to="/routes" class="btn-line">去路线库挑一条</router-link>
              </div>
            </section>

            <!-- 04 我发布的帖子 -->
            <section :ref="(el) => setSec('posts', el)" data-k="posts" class="block">
              <header class="b-head">
                <span class="b-no">04</span>
                <h2>我发布的帖子</h2>
                <em>{{ myPosts.length }} 篇</em>
                <router-link to="/community" class="b-more">去社区 →</router-link>
              </header>

              <div v-if="myPosts.length" class="posts">
                <article v-for="p in myPosts" :key="p.id" class="post">
                  <figure v-if="p.images && p.images.length" @click="openPost(p)">
                    <img :src="p.images[0]" :alt="p.title" loading="lazy" />
                    <span v-if="p.images.length > 1" class="more">+{{ p.images.length - 1 }}</span>
                  </figure>
                  <div class="post-body">
                    <p class="post-title">{{ p.title }}</p>
                    <p class="post-text">{{ p.body }}</p>
                    <p class="post-foot">
                      <router-link v-if="p.trailId" :to="`/route/${p.trailId}`">{{ p.trailName }} →</router-link>
                      <span>{{ p.likes.length }} 赞 · {{ p.comments.length }} 评论 · {{ ago(p.createdAt) }}</span>
                    </p>
                  </div>
                </article>
              </div>
              <div v-else class="empty small">
                <p>还没发过帖子。</p>
                <p class="empty-sub">写一条路况、机位或装备心得，配图会同时进入你的照片墙。</p>
                <router-link to="/community" class="btn-line">写第一条</router-link>
              </div>
            </section>

            <!-- 05 照片墙 -->
            <section :ref="(el) => setSec('photos', el)" data-k="photos" class="block">
              <header class="b-head">
                <span class="b-no">05</span>
                <h2>照片墙</h2>
                <em>{{ uploadedCount }} 张上传 · 共 {{ photoWall.length }} 张</em>
                <button class="upload" :disabled="uploading" @click="fileEl.click()">
                  {{ uploading ? '处理中…' : '＋ 上传照片' }}
                </button>
                <input ref="fileEl" class="file" type="file" accept="image/*" multiple @change="onPick" />
              </header>

              <div v-if="photoWall.length" class="wall">
                <div
                  v-for="(p, i) in photoWall.slice(0, 15)"
                  :key="p.id || p.src"
                  class="wall-cell"
                >
                  <button class="wall-item" @click="openWall(i)">
                    <img :src="p.src" :alt="p.title" loading="lazy" />
                    <span class="wall-cap">
                      <b>{{ p.title }}</b>
                      <em>{{ p.caption }}</em>
                    </span>
                  </button>
                  <button v-if="p.mine" class="wall-del" title="从照片墙移除" @click.stop="delPhoto(p.id)">×</button>
                </div>
              </div>
              <div v-else class="empty small">
                <p>这里会收集你上传过的照片。</p>
                <p class="empty-sub">
                  点右上角「上传照片」，把手机里拍的图加进来（压缩后存在本机，最多 {{ WALL_LIMIT }} 张）；
                  发帖配图、走过的路线封面、收藏的景点实拍也会自动铺上来。
                </p>
                <button class="btn-line" @click="fileEl.click()">上传第一张</button>
              </div>
            </section>

            <!-- 06 收藏 -->
            <section :ref="(el) => setSec('fav', el)" data-k="fav" class="block">
              <header class="b-head">
                <span class="b-no">06</span>
                <h2>收藏</h2>
                <em>{{ fav.total() }} 项</em>
                <div class="seg">
                  <button :class="{ on: favTab === 'spot' }" @click="favTab = 'spot'">景点 {{ fav.count('spot') }}</button>
                  <button :class="{ on: favTab === 'route' }" @click="favTab = 'route'">路线 {{ fav.count('route') }}</button>
                </div>
              </header>

              <div v-if="favTab === 'spot'" class="tiles">
                <button v-for="s in favSpots" :key="s.name" class="tile" @click="goSpot(s)">
                  <img v-if="spotCover(s)" :src="spotCover(s)" :alt="s.name" loading="lazy" />
                  <span class="tile-name">{{ s.name }}</span>
                  <em>{{ s.city }} · {{ s.type }}</em>
                </button>
                <div v-if="!favSpots.length" class="empty small full">
                  <p>还没有收藏景点。</p>
                  <router-link to="/spots" class="btn-line">去景点列表，点卡片右上角收藏 →</router-link>
                </div>
              </div>

              <div v-else class="tiles">
                <button v-for="r in favRoutes" :key="r.id" class="tile" @click="goRoute(r)">
                  <img v-if="routeCover(r)" :src="routeCover(r)" :alt="r.name" loading="lazy" />
                  <span class="tile-name">{{ r.name }}</span>
                  <em>{{ r.distance }}km · ↑{{ r.climb }}m · {{ r.days }}</em>
                </button>
                <div v-if="!favRoutes.length" class="empty small full">
                  <p>还没有收藏路线。</p>
                  <router-link to="/routes" class="btn-line">去路线列表，点卡片右上角收藏 →</router-link>
                </div>
              </div>
            </section>

            <!-- 07 安全报备 -->
            <section :ref="(el) => setSec('safety', el)" data-k="safety" class="block">
              <header class="b-head">
                <span class="b-no">07</span>
                <h2>安全报备</h2>
                <em>出发登记 · 平安打卡</em>
                <router-link to="/safety" class="b-more">全部记录 →</router-link>
              </header>

              <div v-if="field.activePlan" class="plan">
                <div class="plan-top">
                  <div>
                    <p class="plan-kicker">进行中 · {{ field.activePlan.startDate }} 出发</p>
                    <p class="plan-name">{{ routeNameOfSafe(field.activePlan.routeId) }}</p>
                    <p class="plan-meta">
                      {{ field.activePlan.days }} 天 · 同行 {{ field.activePlan.party.length }} 人 ·
                      紧急联系人 {{ field.activePlan.emergencyName || '未填' }}
                    </p>
                  </div>
                  <button class="btn-line danger" @click="finishPlan">我已下山</button>
                </div>
                <ol class="checks">
                  <li v-for="(c, i) in field.activePlan.checkins" :key="i">
                    <span class="ck-dot" :class="c.type"></span>
                    <span class="ck-note">{{ c.note }}</span>
                    <em>{{ ago(c.at) }}</em>
                  </li>
                </ol>
                <div class="check-in">
                  <input v-model="checkNote" placeholder="报个平安：在哪儿、状态如何（可留空）" maxlength="40" />
                  <button class="primary sm" @click="doCheckin">平安打卡</button>
                </div>
              </div>

              <div v-else class="empty small">
                <p>当前没有进行中的行程。</p>
                <p class="empty-sub">出发前登记路线、同行人和紧急联系人；山里每到一处打一次卡，家人能看到你到哪了。</p>
                <router-link to="/safety" class="btn-line">去登记行程</router-link>
              </div>

              <div v-if="myReports.length" class="my-reports">
                <p class="mr-title">我上报的路况</p>
                <div v-for="r in myReports" :key="r.id" class="mr-row">
                  <span class="mr-icon">{{ reportMeta(r.type).icon }}</span>
                  <div>
                    <p class="mr-name">{{ routeNameOfSafe(r.routeId) }} · {{ reportMeta(r.type).name }}</p>
                    <p class="mr-note">{{ r.note }}</p>
                  </div>
                  <em class="mr-state" :style="{ color: levelMeta(r.level).tone }">
                    {{ r.status === 'approved' ? '已挂载' : r.status === 'pending' ? '待审核' : '未通过' }}
                  </em>
                </div>
              </div>
            </section>

            <!-- 08 山友 -->
            <section :ref="(el) => setSec('friends', el)" data-k="friends" class="block">
              <header class="b-head">
                <span class="b-no">08</span>
                <h2>山友</h2>
                <em>{{ friends.count }} 位好友 · {{ friends.incoming.length }} 个待处理申请</em>
              </header>

              <div class="fr-search">
                <input v-model="friendKw" placeholder="输入对方主页上的账号 ID，或昵称关键词" @keydown.enter="doSearch" />
                <button class="mini" :disabled="friends.searching" @click="doSearch">
                  {{ friends.searching ? '搜索中…' : '搜索山友' }}
                </button>
              </div>

              <div v-if="friends.results.length" class="fr-group">
                <p class="fr-sub">搜索结果</p>
                <div v-for="r in friends.results" :key="r.uid" class="fr-item">
                  <span class="fr-ava" :class="{ 'has-img': r.summary.avatar }">
                    <img v-if="r.summary.avatar" :src="r.summary.avatar" alt="" />
                    <template v-else>{{ r.summary.nickname.slice(0, 1) }}</template>
                  </span>
                  <div class="fr-info">
                    <b>{{ r.summary.nickname }}<i v-if="r.summary.region">{{ r.summary.region }}</i></b>
                    <p>{{ r.summary.bio || '还没有签名' }}</p>
                  </div>
                  <button v-if="r.state === 'none'" class="mini ok" @click="addFriend(r.uid)">+ 加好友</button>
                  <button v-else-if="r.state === 'pending_in'" class="mini ok" @click="acceptIncoming(r.uid)">同意申请</button>
                  <span v-else class="fr-state">{{ STATE_LABEL[r.state] }}</span>
                </div>
              </div>
              <p v-else-if="friends.searched && !friends.searching" class="fr-hint">
                没找到。昵称是精确包含匹配；账号 ID 在对方主页的「账号」一行能看到。
              </p>

              <div v-if="friends.incoming.length" class="fr-group">
                <p class="fr-sub">收到的申请（{{ friends.incoming.length }}）</p>
                <div v-for="o in friends.incoming" :key="o.rid" class="fr-item">
                  <span class="fr-ava" :class="{ 'has-img': o.summary.avatar }">
                    <img v-if="o.summary.avatar" :src="o.summary.avatar" alt="" />
                    <template v-else>{{ o.summary.nickname.slice(0, 1) }}</template>
                  </span>
                  <div class="fr-info">
                    <b>{{ o.summary.nickname }}<i v-if="o.summary.region">{{ o.summary.region }}</i></b>
                    <p>{{ o.summary.bio || '想和你成为山友' }}</p>
                  </div>
                  <div class="fr-acts">
                    <button class="mini ok" @click="respondReq(o.rid, true)">同意</button>
                    <button class="mini" @click="respondReq(o.rid, false)">拒绝</button>
                  </div>
                </div>
              </div>

              <div v-if="friends.outgoing.length" class="fr-group">
                <p class="fr-sub">我发出的申请（{{ friends.outgoing.length }}）</p>
                <div v-for="o in friends.outgoing" :key="o.rid" class="fr-item">
                  <span class="fr-ava" :class="{ 'has-img': o.summary.avatar }">
                    <img v-if="o.summary.avatar" :src="o.summary.avatar" alt="" />
                    <template v-else>{{ o.summary.nickname.slice(0, 1) }}</template>
                  </span>
                  <div class="fr-info">
                    <b>{{ o.summary.nickname }}<i v-if="o.summary.region">{{ o.summary.region }}</i></b>
                    <p>等待对方处理</p>
                  </div>
                  <button class="mini" @click="respondReq(o.rid, 2)">撤回</button>
                </div>
              </div>

              <div v-if="friends.list.length" class="fr-group">
                <p class="fr-sub">我的好友（{{ friends.count }}）</p>
                <div v-for="f in friends.list" :key="f.uid" class="fr-item">
                  <span class="fr-ava" :class="{ 'has-img': f.summary.avatar }">
                    <img v-if="f.summary.avatar" :src="f.summary.avatar" alt="" />
                    <template v-else>{{ f.summary.nickname.slice(0, 1) }}</template>
                  </span>
                  <div class="fr-info">
                    <b>{{ f.summary.nickname }}<i v-if="f.summary.region">{{ f.summary.region }}</i></b>
                    <p>{{ f.summary.bio || '还没有签名' }}</p>
                  </div>
                  <button class="mini quiet" @click="dropFriend(f.uid, f.summary.nickname)">删除</button>
                </div>
              </div>

              <p
                v-if="!friends.list.length && !friends.incoming.length && !friends.outgoing.length && !friends.results.length"
                class="empty-sub"
              >
                还没有山友。搜索对方的昵称或账号 ID（在对方主页「账号」一行），发一份好友申请；对方同意后即成为好友。
              </p>
            </section>

            <p class="foot-note">
              账号与资料存在平台云数据库（按账号隔离）：好友、收藏、帖子、报备多设备同步；登录支持手机验证码 / 邮箱 / 微信 / WorkBuddy 账号。
            </p>
          </main>
        </div>
      </div>

      <!-- 编辑资料：头像 / 封面 / 昵称 / 签名 / 性别 / 地区 -->
      <div v-if="editing" class="mask" @click.self="editing = false">
        <div class="dlg edit-dlg">
          <h3>编辑资料</h3>

          <div class="ed-ava-row">
            <span class="ed-ava" :class="{ 'has-img': auth.avatarUrl }">
              <img v-if="auth.avatarUrl" :src="auth.avatarUrl" alt="" />
              <template v-else>{{ auth.initial }}</template>
            </span>
            <div class="ed-ava-txt">
              <b>头像</b>
              <div>
                <button class="mini" :disabled="uploadingAvatar" @click="avatarEl.click()">
                  {{ uploadingAvatar ? '上传中…' : '上传新头像' }}
                </button>
              </div>
              <p>JPG / PNG，自动压缩到 400px，存云存储</p>
            </div>
          </div>

          <label>
            <span>昵称</span>
            <input v-model="form.nickname" maxlength="16" placeholder="2–16 个字" />
          </label>
          <label>
            <span>签名</span>
            <input v-model="form.bio" maxlength="60" placeholder="一句话介绍自己，例：走过 20 条海岸线" />
          </label>
          <label>
            <span>性别</span>
            <span class="ed-genders">
              <button
                v-for="g in GENDERS"
                :key="g.v"
                type="button"
                :class="{ on: form.gender === g.v }"
                @click="form.gender = g.v"
              >
                {{ g.label }}
              </button>
            </span>
          </label>
          <label>
            <span>所在地区</span>
            <span class="ed-region">
              <select v-model="form.regionProvince" @change="form.regionCity = ''">
                <option value="">选择省份</option>
                <option v-for="r in REGIONS" :key="r.p" :value="r.p">{{ r.p }}</option>
              </select>
              <select v-model="form.regionCity" :disabled="!formCities.length">
                <option value="">选择城市</option>
                <option v-for="ct in formCities" :key="ct" :value="ct">{{ ct }}</option>
              </select>
            </span>
          </label>

          <div class="ed-bg">
            <span class="ed-lab">角贴照片</span>
            <div class="ed-bgs">
              <button
                v-for="(b, i) in BG"
                :key="b.src"
                type="button"
                class="ed-bg"
                :class="{ on: form.bg === i }"
                @click="pickBg(i)"
              >
                <img :src="b.src" :alt="b.label" />
                <i>{{ b.label }}</i>
              </button>
            </div>
            <p class="ed-note">显示在主页右上角的拍立得小照片，也可点「换封面」或照片本身轮换。</p>
          </div>

          <div class="ed-bg band-row">
            <span class="ed-lab">主页大背景</span>
            <div class="ed-band">
              <div>
                <button type="button" class="mini" :disabled="uploadingBg" @click="bgEl.click()">
                  {{ uploadingBg ? '上传中…' : '上传自定义大图' }}
                </button>
                <button v-if="auth.bgUrl" type="button" class="mini" @click="clearBand">恢复默认绿色</button>
              </div>
              <p class="ed-note">
                {{ auth.bgUrl ? '当前已使用自定义大背景，铺满整条封面。' : '当前为默认绿色。上传后铺满整条封面，自动压暗保证文字可读。' }}
                直接点主页封面空白处也能上传。JPG / PNG ≤5MB。
              </p>
            </div>
          </div>

          <p class="dlg-tip">资料保存在你的云账号下，多设备登录都会同步。</p>
          <div class="dlg-acts">
            <button class="mini" @click="editing = false">取消</button>
            <button class="primary sm" :disabled="savingProfile" @click="saveEdit">
              {{ savingProfile ? '保存中…' : '保存' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 账号与安全：修改密码 -->
      <div v-if="secOpen" class="mask" @click.self="secOpen = false">
        <div class="dlg">
          <h3>修改密码</h3>
          <p class="sec-bind">当前绑定：手机 {{ auth.maskedPhone || '未绑定' }} · 邮箱 {{ auth.maskedEmail || '未绑定' }}</p>
          <label>
            <span>当前密码</span>
            <input v-model="pwForm.old" type="password" autocomplete="current-password" placeholder="从没设过密码？用「邮箱找回密码」" />
          </label>
          <label>
            <span>新密码</span>
            <input v-model="pwForm.next" type="password" autocomplete="new-password" placeholder="至少 8 位，含字母和数字" />
          </label>
          <label>
            <span>确认新密码</span>
            <input v-model="pwForm.again" type="password" autocomplete="new-password" />
          </label>
          <div class="dlg-acts">
            <button class="mini" @click="secOpen = false">取消</button>
            <button class="primary sm" :disabled="changingPw" @click="doChangePw">
              {{ changingPw ? '提交中…' : '修改密码' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 忘记密码：邮箱验证码重置（成功后自动登录） -->
      <div v-if="resetOpen" class="mask" @click.self="resetOpen = false; resetStep = 1">
        <div class="dlg">
          <h3>找回密码</h3>
          <template v-if="resetStep === 1">
            <p class="sec-bind">输入账号绑定的邮箱，平台会发一个验证码（手机号找回暂未开放）。</p>
            <label>
              <span>邮箱</span>
              <input v-model="resetForm.email" type="email" placeholder="you@example.com" />
            </label>
            <div class="dlg-acts">
              <button class="mini" @click="resetOpen = false; resetStep = 1">取消</button>
              <button class="primary sm" :disabled="resetBusy" @click="doSendReset">
                {{ resetBusy ? '发送中…' : '发送验证码' }}
              </button>
            </div>
          </template>
          <template v-else>
            <label>
              <span>邮箱验证码</span>
              <input v-model="resetForm.code" inputmode="numeric" maxlength="8" placeholder="查看邮箱收件箱" />
            </label>
            <label>
              <span>新密码</span>
              <input v-model="resetForm.next" type="password" placeholder="至少 8 位，含字母和数字" />
            </label>
            <div class="dlg-acts">
              <button class="mini" @click="resetStep = 1">上一步</button>
              <button class="primary sm" :disabled="resetBusy" @click="doCompleteReset">
                {{ resetBusy ? '提交中…' : '重置并登录' }}
              </button>
            </div>
          </template>
        </div>
      </div>

      <input ref="avatarEl" type="file" accept="image/*" hidden @change="onAvatarPick" />
      <input ref="bgEl" type="file" accept="image/*" hidden @change="onBgPick" />

      <LightBox :images="lbImages" :index="lbIndex" :open="lbOpen" @close="lbOpen = false" @update:index="lbIndex = $event" />
    </template>
  </div>
</template>

<style scoped>
.page {
  padding-top: 0;
  padding-bottom: 0;
  background: var(--cream);
}

/* ══════════ 未登录 ══════════ */
.gate {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - var(--nav-h));
  padding: 40px 20px;
}
.gate-card {
  text-align: center;
  max-width: 420px;
}
.gate-mark {
  width: 58px;
  height: 58px;
  border-radius: 14px;
  background: var(--forest-soft);
  color: var(--forest);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}
.gate-card h1 {
  font-family: var(--serif);
  font-size: 1.42rem;
  font-weight: 600;
  margin-bottom: 8px;
}
.gate-card p {
  font-size: 0.85rem;
  color: var(--gray);
  line-height: 1.85;
  margin-bottom: 18px;
}

/* ══════════ 封面条 ══════════ */
.cover {
  position: relative;
  margin-top: var(--nav-h);
  background: linear-gradient(150deg, #1b3626 0%, #264d34 58%, #2f5c3e 100%);
  color: #fff;
  overflow: hidden;
  padding: 32px 0 34px;
}
.topo {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0.13;
}
.topo path {
  fill: none;
  stroke: #dfe9df;
  stroke-width: 1.1;
}
.cover-in {
  position: relative;
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 32px 22px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 262px;
  gap: 32px;
  align-items: center;
}
.identity {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  min-width: 0;
}
.stamp {
  flex: 0 0 auto;
  width: 74px;
  height: 74px;
  border-radius: 8px;
  background: rgba(246, 242, 233, 0.12);
  border: 1px solid rgba(232, 220, 192, 0.55);
  box-shadow: inset 0 0 0 3px rgba(27, 54, 38, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--serif);
  font-size: 1.9rem;
  color: #f2ecdd;
}
.who {
  min-width: 0;
}
.eyebrow {
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.62rem;
  letter-spacing: 0.18em;
  color: rgba(232, 220, 192, 0.62);
  margin-bottom: 6px;
}
.who h1 {
  font-family: var(--serif);
  font-size: 1.72rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.lv {
  font-family: var(--sans, system-ui);
  font-size: 0.66rem;
  font-weight: 500;
  letter-spacing: 0.02em;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(232, 220, 192, 0.16);
  border: 1px solid rgba(232, 220, 192, 0.3);
  color: #ecdfc4;
}
.meta {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.55);
  margin-top: 7px;
}
.meta .mono {
  font-family: var(--mono, ui-monospace, monospace);
  letter-spacing: 0.04em;
}
.meta i {
  margin: 0 6px;
  font-style: normal;
  opacity: 0.4;
}
.bio {
  font-size: 0.83rem;
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.75;
  margin-top: 9px;
  max-width: 560px;
}

.cover-photo {
  margin: 0;
  cursor: pointer;
  transform: rotate(-1.1deg);
  background: #f6f2e9;
  padding: 7px 7px 0;
  box-shadow: 0 12px 26px rgba(0, 0, 0, 0.32);
  transition: transform 0.3s ease;
}
.cover-photo:hover {
  transform: rotate(0deg) translateY(-3px);
}
.cover-photo img {
  display: block;
  width: 100%;
  height: 132px;
  object-fit: cover;
}
.cover-photo figcaption {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 7px 2px 8px;
  font-size: 0.66rem;
  color: #4a4a42;
}
.cover-photo figcaption span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cover-photo figcaption em {
  flex: 0 0 auto;
  font-style: normal;
  color: #8a6d2f;
}

.who-acts {
  display: flex;
  gap: 7px;
  margin-top: 11px;
  flex-wrap: wrap;
}
.who-acts button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid rgba(232, 220, 192, 0.24);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.76);
  font-size: 0.68rem;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: 0.2s;
}
.who-acts button:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}
.who-acts button.quiet {
  border-color: transparent;
  color: rgba(255, 255, 255, 0.4);
  padding-left: 4px;
}
.who-acts button.quiet:hover {
  background: transparent;
  color: rgba(255, 255, 255, 0.7);
}

/* ══════════ 数字台账 ══════════ */
.tally-wrap {
  max-width: 1240px;
  margin: -26px auto 0;
  padding: 0 32px;
  position: relative;
  z-index: 2;
}
.tally {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
  box-shadow: 0 10px 24px rgba(30, 61, 41, 0.09);
  overflow: hidden;
}
.cell {
  padding: 14px 6px 13px;
  text-align: center;
  border-right: 1px solid var(--line);
}
.cell:last-child {
  border-right: none;
}
.cell b {
  display: block;
  font-family: var(--serif);
  font-size: 1.32rem;
  font-weight: 600;
  color: var(--forest-dark);
  line-height: 1.2;
}
.cell b i {
  font-size: 0.6rem;
  font-style: normal;
  color: var(--gray-light);
  margin-left: 2px;
  letter-spacing: 0.04em;
}
.cell span {
  display: block;
  font-size: 0.66rem;
  color: var(--gray);
  margin-top: 3px;
  letter-spacing: 0.06em;
}

/* ══════════ 通用容器 ══════════ */
.wrap {
  max-width: 1240px;
  margin: 0 auto;
  padding: 30px 32px 60px;
}

/* ══════════ 工具条 ══════════ */
.kit {
  margin-bottom: 34px;
}
.kit-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 14px;
}
.kit-head h2 {
  font-family: var(--serif);
  font-size: 1.06rem;
  font-weight: 600;
  color: var(--ink);
}
.kit-head p {
  font-size: 0.74rem;
  color: var(--gray);
}
.kit-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
}
.tool {
  position: relative;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 14px 14px 13px;
  text-decoration: none;
  color: inherit;
  transition: 0.22s ease;
  overflow: hidden;
}
.tool::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--tone);
  opacity: 0.85;
}
.tool:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(30, 61, 41, 0.1);
  border-color: #d8d2c2;
}
.tool-top {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 9px;
}
.tool-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--tone);
}
.tool-top em {
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.54rem;
  letter-spacing: 0.12em;
  color: var(--gray-light);
  font-style: normal;
}
.tool h3 {
  font-size: 0.84rem;
  font-weight: 600;
  color: var(--ink);
}
.tool-val {
  font-family: var(--serif);
  font-size: 1.18rem;
  color: var(--tone);
  margin-top: 4px;
  line-height: 1.2;
}
.tool-val i {
  font-family: var(--sans, system-ui);
  font-size: 0.6rem;
  font-style: normal;
  color: var(--gray);
  margin-left: 3px;
}
.tool-note {
  font-size: 0.64rem;
  color: var(--gray);
  line-height: 1.6;
  margin-top: 5px;
  min-height: 30px;
}
.tool-go {
  font-size: 0.62rem;
  color: var(--tone);
  margin-top: 6px;
  opacity: 0;
  transition: 0.2s;
}
.tool:hover .tool-go {
  opacity: 1;
}

/* ══════════ 目录 + 长卷 ══════════ */
.spread {
  display: grid;
  grid-template-columns: 176px minmax(0, 1fr);
  gap: 30px;
  align-items: start;
}
.index {
  position: sticky;
  top: calc(var(--nav-h) + 20px);
}
.idx-title {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 0.7rem;
  color: var(--gray);
  letter-spacing: 0.1em;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
}
.idx-title em {
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.5rem;
  font-style: normal;
  color: var(--gray-light);
  letter-spacing: 0.14em;
}
.index nav {
  display: flex;
  flex-direction: column;
  margin-top: 6px;
}
.index nav a {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 8px 8px 9px;
  border-left: 2px solid transparent;
  color: var(--ink-soft);
  text-decoration: none;
  font-size: 0.78rem;
  transition: 0.18s;
}
.index nav a em {
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.58rem;
  font-style: normal;
  color: var(--gray-light);
}
.index nav a span {
  flex: 1;
}
.index nav a b {
  font-size: 0.64rem;
  font-weight: 500;
  color: var(--gray-light);
}
.index nav a:hover {
  background: rgba(45, 90, 61, 0.05);
}
.index nav a.on {
  border-left-color: var(--forest);
  background: rgba(45, 90, 61, 0.06);
  color: var(--forest-dark);
  font-weight: 600;
}
.index nav a.on em,
.index nav a.on b {
  color: var(--forest);
}
.idx-card {
  margin-top: 18px;
  padding: 12px 12px 11px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
}
.idx-lv {
  font-size: 0.7rem;
  color: var(--forest-dark);
  font-weight: 600;
}
.lv-bar {
  height: 3px;
  background: var(--cream-dark);
  border-radius: 2px;
  margin: 7px 0 6px;
  overflow: hidden;
}
.lv-bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--forest-light), var(--forest));
  transition: width 0.5s;
}
.idx-tip {
  font-size: 0.64rem;
  color: var(--gray);
}
.idx-rule {
  font-size: 0.58rem;
  color: var(--gray-light);
  line-height: 1.6;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed var(--line);
}
.idx-link {
  display: block;
  margin-top: 10px;
  font-size: 0.64rem;
  color: var(--gray);
  text-decoration: none;
}
.idx-link:hover {
  color: var(--forest);
}

.body {
  min-width: 0;
}

/* ══════════ 区块 ══════════ */
.block {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 22px 24px 24px;
  margin-bottom: 20px;
  scroll-margin-top: 96px;
}
.b-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding-bottom: 13px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 16px;
}
.b-no {
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.62rem;
  color: var(--forest-light);
  letter-spacing: 0.1em;
}
.b-head h2 {
  font-family: var(--serif);
  font-size: 1.02rem;
  font-weight: 600;
  color: var(--ink);
}
.b-head > em {
  font-size: 0.68rem;
  font-style: normal;
  color: var(--gray);
}
.b-more {
  margin-left: auto;
  font-size: 0.68rem;
  color: var(--forest);
  text-decoration: none;
}
.b-more:hover {
  text-decoration: underline;
}

/* ── 收藏掠影 ── */
.strip {
  margin-bottom: 18px;
}
.strip-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.66rem;
  color: var(--gray);
  margin-bottom: 8px;
  letter-spacing: 0.06em;
}
.strip-head a {
  color: var(--forest);
  text-decoration: none;
}
.strip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 8px;
}
.strip-item {
  position: relative;
  flex: 0 0 132px;
  border: none;
  background: none;
  padding: 0;
  cursor: pointer;
  text-align: left;
}
.strip-item img {
  width: 132px;
  height: 82px;
  object-fit: cover;
  border-radius: 4px;
  display: block;
  background: var(--cream-dark);
}
.strip-item span {
  display: block;
  font-size: 0.62rem;
  color: var(--ink-soft);
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.strip-item em {
  position: absolute;
  top: 5px;
  left: 5px;
  font-size: 0.5rem;
  font-style: normal;
  padding: 1px 5px;
  border-radius: 2px;
  background: rgba(20, 32, 24, 0.62);
  color: #f0e8d6;
  letter-spacing: 0.06em;
}

/* ── 时间线 ── */
.line {
  list-style: none;
  padding: 0;
  margin: 0;
  position: relative;
}
.line::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 6px;
  bottom: 6px;
  width: 1px;
  background: var(--line);
}
.line li {
  position: relative;
  padding: 0 0 16px 22px;
}
.line li:last-child {
  padding-bottom: 0;
}
.dot {
  position: absolute;
  left: 0;
  top: 5px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid var(--forest-light);
}
.t-like .dot,
.t-reply .dot {
  border-color: #a97a17;
}
.t-comment .dot {
  border-color: #2f6f9e;
}
.t-buddy .dot {
  border-color: #8a6d2f;
  background: #8a6d2f;
}
.t-plan .dot {
  border-color: #2d5a3d;
  background: #2d5a3d;
}
.line-top {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}
.line-top b {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--ink);
}
.line-top em {
  font-size: 0.62rem;
  font-style: normal;
  color: var(--gray-light);
}
.line-title {
  font-family: var(--serif);
  font-size: 0.9rem;
  color: var(--forest-dark);
  margin-top: 4px;
}
.line-text {
  font-size: 0.76rem;
  color: var(--ink-soft);
  line-height: 1.75;
  margin-top: 3px;
}
.line-thumb {
  width: 104px;
  height: 68px;
  object-fit: cover;
  border-radius: 3px;
  margin-top: 7px;
  display: block;
}

/* ── 空态 ── */
.empty {
  padding: 26px 20px;
  text-align: center;
  border: 1px dashed var(--line);
  border-radius: 5px;
  background: #fcfaf5;
}
.empty.small {
  padding: 20px 16px;
}
.empty p {
  font-size: 0.8rem;
  color: var(--ink-soft);
}
.empty-sub {
  font-size: 0.7rem !important;
  color: var(--gray) !important;
  margin-top: 5px;
  line-height: 1.7;
}
.empty-acts {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-top: 12px;
}
.btn-line {
  display: inline-block;
  font-size: 0.7rem;
  padding: 6px 13px;
  border: 1px solid var(--forest);
  border-radius: 4px;
  color: var(--forest);
  background: #fff;
  text-decoration: none;
  cursor: pointer;
  transition: 0.2s;
}
.btn-line:hover {
  background: var(--forest);
  color: #fff;
}
.btn-line.danger {
  border-color: #a9462f;
  color: #a9462f;
}
.btn-line.danger:hover {
  background: #a9462f;
  color: #fff;
}

/* ── 两栏（约伴） ── */
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.col-card {
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 12px 15px 10px;
  background: #fcfaf5;
}
.col-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 0.72rem;
  color: var(--gray);
  padding-bottom: 8px;
  border-bottom: 1px dashed var(--line);
  margin-bottom: 10px;
}
.col-head b {
  font-family: var(--serif);
  font-size: 0.92rem;
  color: var(--forest-dark);
}
.buddy {
  padding: 8px 0;
  border-bottom: 1px solid rgba(230, 225, 214, 0.7);
}
.buddy:last-child {
  border-bottom: none;
}
.buddy-t {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--ink);
}
.buddy-d {
  font-size: 0.64rem;
  color: var(--gray);
  margin-top: 2px;
}
.buddy-i {
  font-size: 0.7rem;
  color: var(--ink-soft);
  line-height: 1.65;
  margin-top: 4px;
}
.applies {
  margin-top: 7px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.apply {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.64rem;
  color: var(--gray);
  flex-wrap: wrap;
}
.apply b {
  color: var(--ink);
}
.apply span {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mini {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 3px;
  font-size: 0.6rem;
  padding: 2px 7px;
  cursor: pointer;
  color: var(--ink-soft);
}
.mini.ok {
  border-color: var(--forest-light);
  color: var(--forest);
}
.mini.no {
  border-color: #d9b6ae;
  color: #a9462f;
}
.apply em {
  font-style: normal;
  font-size: 0.6rem;
}
.apply em.passed {
  color: var(--forest);
}
.apply em.rejected {
  color: #a9462f;
}
.state {
  display: inline-block;
  font-size: 0.6rem;
  padding: 1px 7px;
  border-radius: 2px;
  margin-top: 5px;
}
.state.s0 {
  background: #f4efe2;
  color: #8a6d2f;
}
.state.s1 {
  background: #e8f1e9;
  color: var(--forest);
}
.state.s2 {
  background: #f7eae7;
  color: #a9462f;
}
.mini-empty {
  font-size: 0.7rem;
  color: var(--gray);
  line-height: 1.7;
  padding: 6px 0;
}
.mini-empty a {
  color: var(--forest);
}

/* ── 我走过的路线 ── */
.walk-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border: 1px solid var(--line);
  border-radius: 5px;
  margin-bottom: 14px;
  overflow: hidden;
}
.walk-bar div {
  padding: 10px 12px;
  border-right: 1px solid var(--line);
  display: flex;
  align-items: baseline;
  gap: 3px;
  flex-wrap: wrap;
}
.walk-bar div:last-child {
  border-right: none;
}
.walk-bar b {
  font-family: var(--serif);
  font-size: 1.1rem;
  color: var(--forest-dark);
}
.walk-bar span {
  font-size: 0.6rem;
  color: var(--gray-light);
}
.walk-bar em {
  width: 100%;
  font-size: 0.62rem;
  font-style: normal;
  color: var(--gray);
}

.cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.card-route {
  display: grid;
  grid-template-columns: 126px 1fr;
  border: 1px solid var(--line);
  border-radius: 5px;
  overflow: hidden;
  cursor: pointer;
  background: #fff;
  transition: 0.2s;
}
.card-route:hover {
  border-color: #d3ccbb;
  box-shadow: 0 6px 16px rgba(30, 61, 41, 0.08);
}
.card-route figure {
  margin: 0;
  height: 100%;
}
.card-route img {
  width: 126px;
  height: 100%;
  min-height: 84px;
  object-fit: cover;
  display: block;
}
.cr-body {
  padding: 9px 11px;
  min-width: 0;
}
.cr-name {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cr-meta {
  font-size: 0.62rem;
  color: var(--gray);
  margin-top: 2px;
}
.cr-nums {
  font-size: 0.66rem;
  color: var(--ink-soft);
  margin-top: 6px;
}
.cr-nums b {
  font-family: var(--serif);
  color: var(--forest-dark);
}
.cr-nums i {
  display: inline-block;
  width: 1px;
  height: 8px;
  background: var(--line);
  margin: 0 6px;
  vertical-align: middle;
}

/* ── 帖子 ── */
.posts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.post {
  border: 1px solid var(--line);
  border-radius: 5px;
  overflow: hidden;
  background: #fff;
}
.post figure {
  margin: 0;
  position: relative;
  cursor: zoom-in;
}
.post figure img {
  width: 100%;
  height: 156px;
  object-fit: cover;
  display: block;
  background: var(--cream-dark);
}
.post .more {
  position: absolute;
  right: 8px;
  bottom: 8px;
  font-size: 0.6rem;
  padding: 1px 6px;
  border-radius: 2px;
  background: rgba(20, 32, 24, 0.6);
  color: #fff;
}
.post-body {
  padding: 11px 13px 12px;
}
.post-title {
  font-family: var(--serif);
  font-size: 0.9rem;
  color: var(--ink);
  line-height: 1.5;
}
.post-text {
  font-size: 0.72rem;
  color: var(--ink-soft);
  line-height: 1.7;
  margin-top: 5px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.post-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding-top: 7px;
  border-top: 1px dashed var(--line);
  font-size: 0.62rem;
  color: var(--gray);
  flex-wrap: wrap;
}
.post-foot a {
  color: var(--forest);
  text-decoration: none;
}
.post-foot span {
  margin-left: auto;
}

/* ── 照片墙 ── */
.wall {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-auto-rows: 126px;
  gap: 9px;
}
.wall-cell {
  position: relative;
  min-height: 0;
}
.wall-cell.tall {
  grid-row: span 2;
}
.wall-item {
  position: relative;
  display: block;
  width: 100%;
  height: 100%;
  border: none;
  padding: 0;
  margin: 0;
  cursor: zoom-in;
  background: none;
  overflow: hidden;
  border-radius: 4px;
}
.wall-del {
  position: absolute;
  top: 5px;
  right: 5px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: none;
  background: rgba(16, 26, 19, 0.62);
  color: #fff;
  font-size: 0.86rem;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  transition: 0.18s;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}
.wall-cell:hover .wall-del {
  opacity: 1;
}
.wall-del:hover {
  background: #a9462f;
}
.upload {
  margin-left: auto;
  border: 1px solid var(--forest);
  background: #fff;
  color: var(--forest);
  border-radius: 4px;
  font-size: 0.68rem;
  padding: 4px 11px;
  cursor: pointer;
  transition: 0.18s;
}
.upload:hover {
  background: var(--forest);
  color: #fff;
}
.upload:disabled {
  opacity: 0.55;
  cursor: wait;
}
.file {
  display: none;
}
.wall-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.45s ease, filter 0.3s;
}
.wall-item:hover img {
  filter: brightness(0.86);
}
.wall-cap {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 22px 9px 8px;
  background: linear-gradient(to top, rgba(10, 18, 13, 0.82), rgba(10, 18, 13, 0));
  opacity: 0;
  transition: 0.24s;
  text-align: left;
}
.wall-item:hover .wall-cap {
  opacity: 1;
}
.wall-item:hover img {
  transform: scale(1.04);
}
.wall-cap b {
  display: block;
  font-size: 0.66rem;
  font-weight: 600;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.wall-cap em {
  display: block;
  font-size: 0.55rem;
  font-style: normal;
  color: rgba(255, 255, 255, 0.72);
  margin-top: 2px;
}

/* ── 收藏 ── */
.seg {
  margin-left: auto;
  display: inline-flex;
  border: 1px solid var(--line);
  border-radius: 3px;
  overflow: hidden;
}
.seg button {
  border: none;
  background: #fff;
  font-size: 0.64rem;
  padding: 3px 10px;
  color: var(--gray);
  cursor: pointer;
}
.seg button.on {
  background: var(--forest);
  color: #fff;
}
.tiles {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.tile {
  border: 1px solid var(--line);
  border-radius: 4px;
  overflow: hidden;
  background: #fff;
  padding: 0;
  cursor: pointer;
  text-align: left;
  transition: 0.2s;
}
.tile:hover {
  border-color: #d3ccbb;
  transform: translateY(-1px);
}
.tile img {
  width: 100%;
  height: 124px;
  object-fit: cover;
  display: block;
  background: var(--cream-dark);
}
.tile-name {
  display: block;
  font-size: 0.72rem;
  color: var(--ink);
  padding: 6px 8px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tile em {
  display: block;
  font-size: 0.58rem;
  font-style: normal;
  color: var(--gray);
  padding: 2px 8px 8px;
}
.tiles .full {
  grid-column: 1 / -1;
}

/* ── 安全报备 ── */
.plan {
  border: 1px solid #cfdccf;
  background: #f6faf6;
  border-radius: 5px;
  padding: 15px 16px;
}
.plan-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
}
.plan-kicker {
  font-size: 0.62rem;
  color: var(--forest);
  letter-spacing: 0.06em;
}
.plan-name {
  font-family: var(--serif);
  font-size: 0.98rem;
  color: var(--ink);
  margin-top: 3px;
}
.plan-meta {
  font-size: 0.66rem;
  color: var(--gray);
  margin-top: 4px;
}
.checks {
  list-style: none;
  margin: 13px 0 0;
  padding: 0;
  border-top: 1px dashed #cfdccf;
  padding-top: 10px;
}
.checks li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 0.68rem;
  color: var(--ink-soft);
}
.ck-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--forest-light);
  flex: 0 0 auto;
}
.ck-dot.go {
  background: #8a6d2f;
}
.ck-dot.done {
  background: #2f6f9e;
}
.checks em {
  margin-left: auto;
  font-style: normal;
  font-size: 0.6rem;
  color: var(--gray-light);
}
.check-in {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}
.check-in input {
  flex: 1;
  border: 1px solid var(--line);
  border-radius: 3px;
  padding: 7px 10px;
  font-size: 0.72rem;
  background: #fff;
  color: var(--ink);
  outline: none;
}
.check-in input:focus {
  border-color: var(--forest-light);
}
.primary.sm {
  padding: 6px 14px;
  font-size: 0.7rem;
  border-radius: 3px;
  border: none;
  background: var(--forest);
  color: #fff;
  cursor: pointer;
  white-space: nowrap;
}
.primary.sm:hover {
  background: var(--forest-dark);
}
.my-reports {
  margin-top: 14px;
  border-top: 1px dashed var(--line);
  padding-top: 11px;
}
.mr-title {
  font-size: 0.66rem;
  color: var(--gray);
  letter-spacing: 0.06em;
  margin-bottom: 7px;
}
.mr-row {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 6px 0;
  border-bottom: 1px solid rgba(230, 225, 214, 0.6);
}
.mr-row:last-child {
  border-bottom: none;
}
.mr-icon {
  font-size: 0.9rem;
  line-height: 1.3;
}
.mr-row > div {
  flex: 1;
  min-width: 0;
}
.mr-name {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--ink);
}
.mr-note {
  font-size: 0.64rem;
  color: var(--gray);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mr-state {
  font-size: 0.6rem;
  font-style: normal;
  flex: 0 0 auto;
  padding-top: 2px;
}

.foot-note {
  font-size: 0.64rem;
  color: var(--gray-light);
  line-height: 1.9;
  padding: 4px 2px 0;
}

/* ══════════ 弹层 ══════════ */
.mask {
  position: fixed;
  inset: 0;
  z-index: 4000;
  background: rgba(20, 30, 24, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.dlg {
  width: 100%;
  max-width: 380px;
  background: #fff;
  border-radius: 8px;
  padding: 22px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.24);
  max-height: calc(100vh - 40px);
  overflow-y: auto;
}
.dlg h3 {
  font-family: var(--serif);
  font-size: 1.02rem;
  margin-bottom: 14px;
}
.dlg label {
  display: block;
  margin-bottom: 12px;
}
.dlg label span {
  display: block;
  font-size: 0.68rem;
  color: var(--gray);
  margin-bottom: 5px;
}
.dlg input {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 8px 10px;
  font-size: 0.8rem;
  outline: none;
  background: var(--cream);
  color: var(--ink);
}
.dlg input:focus {
  border-color: var(--forest-light);
  background: #fff;
}
.dlg-tip {
  font-size: 0.62rem;
  color: var(--gray-light);
  line-height: 1.7;
  margin-top: 2px;
}
.dlg-acts {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}
.dlg-acts .mini {
  padding: 6px 14px;
  font-size: 0.72rem;
}

/* ══════════ 响应式 ══════════ */
@media (max-width: 1180px) {
  .kit-grid {
    grid-template-columns: repeat(3, 1fr);
  }
  .wall {
    grid-template-columns: repeat(3, 1fr);
    grid-auto-rows: 118px;
  }
  .tiles {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 980px) {
  .cover-in {
    grid-template-columns: 1fr;
    gap: 18px;
    padding: 0 20px 18px;
  }
  .cover-photo {
    justify-self: start;
    width: 220px;
    transform: rotate(-0.8deg);
  }
  .cover-photo img {
    height: 108px;
  }
  .cover-acts {
    padding: 0 20px 14px;
  }
  .tally-wrap {
    padding: 0 20px;
  }
  .tally {
    grid-template-columns: repeat(3, 1fr);
  }
  .cell:nth-child(3) {
    border-right: none;
  }
  .cell:nth-child(1),
  .cell:nth-child(2),
  .cell:nth-child(3) {
    border-bottom: 1px solid var(--line);
  }
  .wrap {
    padding: 24px 20px 48px;
  }
  .kit-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 3px;
  }
  .kit-head h2 {
    white-space: nowrap;
  }
  .spread {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  .index {
    position: static;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: #fff;
    padding: 10px 12px;
  }
  .index nav {
    flex-direction: row;
    flex-wrap: nowrap;
    gap: 6px;
    overflow-x: auto;
    padding-bottom: 3px;
    scrollbar-width: none;
  }
  .index nav::-webkit-scrollbar {
    display: none;
  }
  .index nav a {
    border-left: none;
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 0.7rem;
    white-space: nowrap;
    flex: 0 0 auto;
    gap: 5px;
  }
  .index nav a.on {
    border-color: var(--forest);
    background: var(--forest-soft);
  }
  .index nav a em {
    font-size: 0.52rem;
  }
  .index nav a b {
    display: inline;
    font-size: 0.56rem;
  }
  .idx-card,
  .idx-link {
    display: none;
  }
  .two-col,
  .cards,
  .posts {
    grid-template-columns: 1fr;
  }
  .wall {
    grid-template-columns: repeat(2, 1fr);
    grid-auto-rows: 116px;
  }
  .tiles {
    grid-template-columns: repeat(2, 1fr);
  }
  .block {
    padding: 18px 16px 20px;
  }
}

@media (max-width: 620px) {
  .identity {
    gap: 13px;
  }
  .stamp {
    width: 56px;
    height: 56px;
    font-size: 1.4rem;
  }
  .who h1 {
    font-size: 1.3rem;
  }
  .kit-grid {
    grid-template-columns: 1fr 1fr;
  }
  .walk-bar {
    grid-template-columns: 1fr 1fr;
  }
  .walk-bar div:nth-child(2) {
    border-right: none;
  }
  .walk-bar div:nth-child(1),
  .walk-bar div:nth-child(2) {
    border-bottom: 1px solid var(--line);
  }
  .wall {
    grid-template-columns: repeat(2, 1fr);
    grid-auto-rows: 116px;
  }
  .wall {
    grid-auto-rows: 104px;
  }
  .card-route {
    grid-template-columns: 104px 1fr;
  }
  .card-route img {
    width: 104px;
  }
}

/* ══════════ v11：头像 / 编辑弹窗 / 山友 / 账号安全 ══════════ */
.stamp {
  overflow: hidden;
}
.stamp img,
.ed-ava img,
.fr-ava img,
.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  border-radius: inherit;
}
.sub-meta {
  margin-top: -6px;
  color: rgba(232, 220, 192, 0.66);
  font-size: 0.68rem;
}
.xp-more {
  margin-top: 7px;
  font-size: 0.62rem;
  color: var(--gray);
}
.xp-more summary {
  cursor: pointer;
  color: var(--forest);
  letter-spacing: 0.04em;
}
.xp-more p {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-top: 4px;
}
.xp-more span {
  flex: 1;
}
.xp-more b {
  font-weight: 600;
  color: var(--ink);
}
.xp-more i {
  font-style: normal;
  color: var(--gray-light);
  font-size: 0.54rem;
}
.sec-line {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 0.68rem;
  color: var(--gray);
  margin-top: 5px;
}
.sec-line b {
  font-weight: 600;
  color: var(--ink);
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.62rem;
}
.sec-line i {
  font-style: normal;
  color: var(--gray-light);
  margin-left: 4px;
}
.sec-acts {
  display: flex;
  gap: 6px;
  margin-top: 9px;
  flex-wrap: wrap;
}

/* 编辑弹窗 */
.edit-dlg {
  text-align: left;
  width: 100%;
  max-width: min(460px, calc(100vw - 32px));
}
.edit-dlg h3 {
  text-align: center;
}
.ed-ava-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0 4px;
}
.ed-ava {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: var(--forest-soft);
  color: var(--forest);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--serif);
  font-size: 1.4rem;
  overflow: hidden;
  flex: 0 0 auto;
}
.ed-ava-txt b {
  display: block;
  font-size: 0.74rem;
  color: var(--ink);
}
.ed-ava-txt p {
  font-size: 0.6rem;
  color: var(--gray-light);
  margin-top: 4px;
}
.ed-ava-txt .mini {
  margin-top: 5px;
}
.edit-dlg label {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 11px;
}
.edit-dlg label > span:first-child,
.ed-lab {
  flex: 0 0 62px;
  font-size: 0.7rem;
  color: var(--gray);
}
.edit-dlg input {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 8px 10px;
  font-size: 0.76rem;
  background: #fcfaf5;
  color: var(--ink);
  outline: none;
  font-family: inherit;
}
.edit-dlg input:focus {
  border-color: var(--forest-light);
  background: #fff;
}
.edit-dlg .ed-genders {
  display: flex;
  gap: 10px;
  flex: 1;
  margin-bottom: 0;
}
.edit-dlg .ed-genders button {
  flex: 1;
  border: 1px solid var(--line);
  background: #fcfaf5;
  border-radius: 5px;
  padding: 7px 0;
  font-size: 0.72rem;
  color: var(--gray);
  cursor: pointer;
  transition: 0.16s;
}
.edit-dlg .ed-genders button.on {
  border-color: var(--forest);
  background: var(--forest-soft);
  color: var(--forest-dark);
}
.edit-dlg .ed-region {
  display: flex;
  gap: 8px;
  flex: 1;
  margin-bottom: 0;
}
.edit-dlg .ed-region select {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 8px 8px;
  font-size: 0.72rem;
  background: #fcfaf5;
  color: var(--ink);
  outline: none;
  font-family: inherit;
}
.ed-region select:focus {
  border-color: var(--forest-light);
  background: #fff;
}
.ed-bg {
  margin-top: 6px;
}
.ed-bgs {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 6px;
  flex: 1;
}
.ed-bg {
  position: relative;
  border: 2px solid var(--line);
  border-radius: 5px;
  padding: 0;
  overflow: hidden;
  cursor: pointer;
  background: #fcfaf5;
  aspect-ratio: 4 / 3;
}
.ed-bg img {
  width: 100%;
  height: 74%;
  object-fit: cover;
  display: block;
}
.ed-bg i {
  display: block;
  font-style: normal;
  font-size: 0.48rem;
  color: var(--gray);
  padding: 2px 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ed-bg.on {
  border-color: var(--forest);
}
.sec-bind {
  font-size: 0.68rem;
  color: var(--gray);
  background: var(--cream);
  border-radius: 5px;
  padding: 8px 10px;
  margin-bottom: 10px;
  line-height: 1.8;
}

/* 山友 */
.fr-search {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
}
.fr-search input {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 9px 12px;
  font-size: 0.76rem;
  background: #fff;
  color: var(--ink);
  outline: none;
  font-family: inherit;
}
.fr-search input:focus {
  border-color: var(--forest-light);
}
.fr-hint {
  font-size: 0.62rem;
  color: var(--gray-light);
  margin: 6px 0 2px;
}
.fr-group {
  margin-top: 14px;
}
.fr-sub {
  font-size: 0.66rem;
  letter-spacing: 0.08em;
  color: var(--gray);
  padding-bottom: 6px;
  border-bottom: 1px dashed var(--line);
}
.fr-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 0;
  border-bottom: 1px solid var(--cream-dark);
}
.fr-ava {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--forest-soft);
  color: var(--forest);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--serif);
  font-size: 1rem;
  overflow: hidden;
  flex: 0 0 auto;
}
.fr-info {
  flex: 1;
  min-width: 0;
}
.fr-info b {
  font-size: 0.78rem;
  color: var(--ink);
  font-weight: 600;
}
.fr-info i {
  font-style: normal;
  font-size: 0.56rem;
  color: var(--forest);
  background: var(--forest-soft);
  border-radius: 999px;
  padding: 1px 7px;
  margin-left: 7px;
}
.fr-info p {
  font-size: 0.64rem;
  color: var(--gray);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fr-acts {
  display: flex;
  gap: 6px;
}
.fr-state {
  font-size: 0.62rem;
  color: var(--gray-light);
}
.mini.quiet {
  color: var(--gray-light);
}
.mini.ok {
  border-color: rgba(45, 90, 61, 0.4);
  color: var(--forest-dark);
}


/* ══════════ v12：大背景直换 / 头像直点 / 弹窗自适应 ══════════ */
.cover {
  cursor: pointer;
}
.cover button,
.cover a,
.cover figure {
  cursor: pointer;
}
.band-hint {
  position: absolute;
  right: 16px;
  bottom: 12px;
  z-index: 6;
  font-size: 0.6rem;
  color: rgba(255, 255, 255, 0.9);
  background: rgba(16, 26, 19, 0.55);
  border: 1px solid rgba(232, 220, 192, 0.32);
  border-radius: 999px;
  padding: 4px 11px;
  opacity: 0;
  transition: 0.2s;
  pointer-events: none;
  letter-spacing: 0.04em;
}
.cover:hover .band-hint {
  opacity: 1;
}
.stamp {
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}
.stamp:hover {
  border-color: rgba(232, 220, 192, 0.95);
  background: rgba(246, 242, 233, 0.22);
}
.ed-note {
  grid-column: 1 / -1;
  font-size: 0.58rem;
  color: var(--gray-light);
  line-height: 1.8;
  margin-top: 6px;
}
.band-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 13px;
}
.ed-band {
  flex: 1;
  min-width: 0;
}
.ed-band > div {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.ed-band .ed-note {
  margin-top: 7px;
}
@media (max-width: 640px) {
  .mask {
    padding: 12px;
  }
  .dlg {
    max-height: calc(100vh - 24px);
  }
  .edit-dlg {
    max-width: calc(100vw - 24px);
  }
  .ed-bgs {
    grid-template-columns: repeat(3, 1fr);
  }
  .ed-ava-row {
    flex-wrap: wrap;
  }
  .band-row {
    flex-direction: column;
    gap: 6px;
  }
}

</style>
