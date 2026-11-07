# -*- coding: utf-8 -*-
"""v11 补丁：MeView(编辑资料/等级/好友/账号安全) + field.js(路况行补 account) + TopNav(头像)"""
import io

P = 'src/views/MeView.vue'
s = io.open(P, encoding='utf-8').read()
orig_len = len(s)
applied = []


def rep(old, new, tag):
    global s
    n = s.count(old)
    assert n == 1, f'[{tag}] 期望出现 1 次，实际 {n} 次'
    s = s.replace(old, new)
    applied.append(tag)


# ── R1 imports ──
rep(
    """import { useUiStore } from '../stores/ui.js'
import LightBox from '../components/LightBox.vue'""",
    """import { useUiStore } from '../stores/ui.js'
import { useFriendsStore } from '../stores/friends.js'
import { REGIONS, GENDERS, citiesOf, regionShort } from '../data/regions.js'
import { cloud } from '../services/cloud.js'
import LightBox from '../components/LightBox.vue'""",
    'R1a',
)
rep(
    """const field = useFieldStore()
const ui = useUiStore()""",
    """const field = useFieldStore()
const friends = useFriendsStore()
const ui = useUiStore()""",
    'R1b',
)

# ── R2 bg computed + cycleBg ──
rep(
    """const bg = computed(() => BG[(auth.bgIndex || 0) % BG.length])

function cycleBg() {
  const next = ((auth.bgIndex || 0) + 1) % BG.length
  auth.updateProfile({ bg: next })
  ui.toast(`封面换成「${BG[next].label}」`)
}""",
    """const bg = computed(() =>
  auth.bgUrl ? { src: auth.bgUrl, label: '自定义封面' } : BG[(auth.bgIndex || 0) % BG.length]
)

async function cycleBg() {
  if (auth.bgUrl) {
    try {
      await auth.updateProfile({ bgPath: null })
      ui.toast('已换回预设封面，自定义图可在「编辑资料」重新上传')
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
}""",
    'R2',
)

# ── R3 SECTIONS ──
rep(
    """  { k: 'safety', no: '07', label: '安全报备' }
]""",
    """  { k: 'safety', no: '07', label: '安全报备' },
  { k: 'friends', no: '08', label: '山友' }
]""",
    'R3',
)

# ── R4 counts ──
rep(
    """  safety: field.myPlans.length
}))""",
    """  safety: field.myPlans.length,
  friends: friends.count
}))""",
    'R4',
)

# ── R5 等级系统 ──
rep(
    """/* ── 等级 ── */
const LEVEL_STEP = 12
const score = computed(
  () => fav.total() * 1 + myPosts.value.length * 3 + myBuddies.value.length * 5 + myApplies.value.length * 2
)
const level = computed(() => Math.min(6, 1 + Math.floor(score.value / LEVEL_STEP)))
const levelProgress = computed(() =>
  level.value >= 6 ? 100 : Math.round(((score.value % LEVEL_STEP) / LEVEL_STEP) * 100)
)
const levelText = computed(() => ['初来', '常客', '熟人', '老山友', '活地图', '开山者'][level.value - 1] || '初来')
const toNext = computed(() => (level.value >= 6 ? 0 : LEVEL_STEP - (score.value % LEVEL_STEP)))""",
    """/* ── 等级：累计使用时长 + 上传数据量 → 经验值，体现户外经验与活跃度 ── */
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
const usageHours = computed(() => ((auth.profile.activeSeconds || 0) / 3600).toFixed(1))""",
    'R5',
)

# ── R6 编辑资料 / 好友 / 账号安全 脚本 ──
rep(
    """/* ── 编辑资料 ── */
const editing = ref(false)
const form = ref({ nickname: '', bio: '' })
function openEdit() {
  form.value = { nickname: auth.nickname, bio: auth.bio || '' }
  editing.value = true
}
function saveEdit() {
  const n = form.value.nickname.trim()
  if (!n) return ui.toast('昵称不能为空')
  auth.updateProfile({ nickname: n, bio: form.value.bio.trim() })
  editing.value = false
  ui.toast('资料已更新')
}""",
    """/* ── 编辑资料：头像 / 封面 / 昵称 / 签名 / 性别 / 地区 ── */
const editing = ref(false)
const form = ref({ nickname: '', bio: '', gender: 0, regionProvince: '', regionCity: '', bg: 0, bgPath: '' })
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
    bg: auth.bgIndex || 0,
    bgPath: auth.profile.bgPath || ''
  }
  editing.value = true
}

function pickBg(i) {
  form.value.bg = i
  form.value.bgPath = ''
}

/** 选图 → 本地压缩 → 传云存储 → 写进资料表 */
async function uploadProfileImage(file, kind) {
  if (!file) return
  if (!/^image\\//.test(file.type)) throw new Error('请选择图片文件')
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
    form.value.bgPath = path
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
    ui.toast('自定义封面已保存，保存资料后生效')
  } catch (err) {
    ui.toast(err.message || '封面上传失败')
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
      bg: form.value.bg,
      bgPath: form.value.bgPath || null
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
  return v.length >= 8 && /[a-zA-Z]/.test(v) && /\\d/.test(v)
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
  if (!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(resetForm.value.email)) return ui.toast('请输入正确的邮箱地址')
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
  if (!/^\\d{4,8}$/.test(code)) return ui.toast('请输入邮箱里的验证码')
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
}""",
    'R6',
)

# ── R7 封面头像 ──
rep(
    """            <span class="stamp">{{ auth.initial }}</span>""",
    """            <span class="stamp" :class="{ 'has-img': auth.avatarUrl }">
              <img v-if="auth.avatarUrl" :src="auth.avatarUrl" alt="头像" />
              <template v-else>{{ auth.initial }}</template>
            </span>""",
    'R7',
)

# ── R8 meta 加地区性别 ──
rep(
    """              <p class="bio">{{ auth.bio || '还没写签名。点下面「编辑资料」写一句。' }}</p>""",
    """              <p class="bio">{{ auth.bio || '还没写签名。点下面「编辑资料」写一句。' }}</p>
              <p v-if="regionLabel || genderLabel" class="meta sub-meta">
                <span v-if="regionLabel">{{ regionLabel }}</span>
                <template v-if="regionLabel && genderLabel"><i>·</i></template>
                <span v-if="genderLabel">{{ genderLabel }}</span>
              </p>""",
    'R8',
)

# ── R9 左栏：等级卡重构 + 安全卡 ──
rep(
    """            <div class="idx-card">
              <p class="idx-lv">Lv.{{ level }} · {{ levelText }}</p>
              <div class="lv-bar"><i :style="{ width: levelProgress + '%' }"></i></div>
              <p class="idx-tip">
                {{ toNext ? `再攒 ${toNext} 分升 Lv.${level + 1}` : '已到最高等级' }}
              </p>
              <p class="idx-rule">收藏 +1 · 发帖 +3 · 约伴 +5 · 申请 +2</p>
            </div>
            <router-link to="/versions" class="idx-link">看每轮改了什么 →</router-link>""",
    """            <div class="idx-card">
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
            <router-link to="/versions" class="idx-link">看每轮改了什么 →</router-link>""",
    'R9',
)

io.open(P, 'w', encoding='utf-8').write(s)
print('PART1 ok:', ', '.join(applied), f'({orig_len} -> {len(s)})')
