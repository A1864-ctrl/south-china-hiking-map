# -*- coding: utf-8 -*-
"""v12 补丁：性别间距(特异性修复) + 弹窗自适应 + 大背景可换 + 头像直点更换"""
import io

P = 'src/views/MeView.vue'
s = io.open(P, encoding='utf-8').read()
orig_len = len(s)
applied = []


def rep(old, new, tag, count=1):
    global s
    n = s.count(old)
    assert n == count, f'[{tag}] 期望 {count} 次，实际 {n} 次'
    s = s.replace(old, new)
    applied.append(tag)


# ── 1) 角贴照片回到预设轮换（自定义图改作用于大背景） ──
rep(
    """const bg = computed(() =>
  auth.bgUrl ? { src: auth.bgUrl, label: '自定义封面' } : BG[(auth.bgIndex || 0) % BG.length]
)""",
    """const bg = computed(() => BG[(auth.bgIndex || 0) % BG.length])

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
}""",
    'C1-bg-band',
)

# ── 2) cycleBg 文案微调（作用对象是角贴照片+预设） ──
rep(
    """      ui.toast('已换回预设封面，自定义图可在「编辑资料」重新上传')""",
    """      ui.toast('已恢复默认绿色大背景，可随时重新上传')""",
    'C2-cycle-text',
)

# ── 3) 编辑脚本：pickBg / onBgPick / saveEdit / clearBand ──
rep(
    """function pickBg(i) {
  form.value.bg = i
  form.value.bgPath = ''
}""",
    """function pickBg(i) {
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
}""",
    'C3-pickbg',
)
rep(
    """  if (kind === 'avatar') {
    await auth.updateProfile({ avatarPath: path })
  } else {
    await auth.updateProfile({ bgPath: path })
    form.value.bgPath = path
  }
}""",
    """  if (kind === 'avatar') {
    await auth.updateProfile({ avatarPath: path })
  } else {
    await auth.updateProfile({ bgPath: path })
  }
}""",
    'C3b-upload',
)
rep(
    """  uploadingBg.value = true
  try {
    await uploadProfileImage(f, 'bg')
    ui.toast('自定义封面已保存，保存资料后生效')
  } catch (err) {
    ui.toast(err.message || '封面上传失败')
  } finally {
    uploadingBg.value = false
  }
}""",
    """  uploadingBg.value = true
  try {
    await uploadProfileImage(f, 'bg')
    ui.toast('大背景已更新，立即生效')
  } catch (err) {
    ui.toast(err.message || '大背景上传失败')
  } finally {
    uploadingBg.value = false
  }
}""",
    'C3c-toast',
)
rep(
    """    await auth.updateProfile({
      nickname: n,
      bio: form.value.bio.trim(),
      gender: form.value.gender,
      regionProvince: form.value.regionProvince,
      regionCity: form.value.regionCity,
      bg: form.value.bg,
      bgPath: form.value.bgPath || null
    })""",
    """    await auth.updateProfile({
      nickname: n,
      bio: form.value.bio.trim(),
      gender: form.value.gender,
      regionProvince: form.value.regionProvince,
      regionCity: form.value.regionCity,
      bg: form.value.bg
    })""",
    'C3d-save',
)
rep(
    """const form = ref({ nickname: '', bio: '', gender: 0, regionProvince: '', regionCity: '', bg: 0, bgPath: '' })""",
    """const form = ref({ nickname: '', bio: '', gender: 0, regionProvince: '', regionCity: '', bg: 0 })""",
    'C3e-form',
)
rep(
    """    regionCity: auth.profile.regionCity || '',
    bg: auth.bgIndex || 0,
    bgPath: auth.profile.bgPath || ''
  }
  editing.value = true""",
    """    regionCity: auth.profile.regionCity || '',
    bg: auth.bgIndex || 0
  }
  editing.value = true""",
    'C3f-open',
)

# ── 4) 模板：封面条点击/提示 + 头像直点 ──
rep(
    """      <header class="cover">
        <svg class="topo" viewBox="0 0 1200 260" preserveAspectRatio="none" aria-hidden="true">""",
    """      <header class="cover" :style="coverBgStyle" title="点空白处上传自定义大背景" @click="onBandClick">
        <span class="band-hint">＋ 上传自定义大背景</span>
        <svg class="topo" viewBox="0 0 1200 260" preserveAspectRatio="none" aria-hidden="true">""",
    'C4a-band-tpl',
)
rep(
    """            <span class="stamp" :class="{ 'has-img': auth.avatarUrl }">
              <img v-if="auth.avatarUrl" :src="auth.avatarUrl" alt="头像" />
              <template v-else>{{ auth.initial }}</template>
            </span>""",
    """            <span class="stamp" :class="{ 'has-img': auth.avatarUrl }" title="点击更换头像" @click.stop="avatarEl.click()">
              <img v-if="auth.avatarUrl" :src="auth.avatarUrl" alt="头像" />
              <template v-else>{{ auth.initial }}</template>
            </span>""",
    'C4b-stamp',
)

# ── 5) 编辑弹窗模板：角贴照片网格去掉上传块、加大背景行、隐藏输入移到根部 ──
rep(
    """          <div class="ed-bg">
            <span class="ed-lab">主页封面</span>
            <div class="ed-bgs">
              <button
                v-for="(b, i) in BG"
                :key="b.src"
                type="button"
                class="ed-bg"
                :class="{ on: !form.bgPath && form.bg === i }"
                @click="pickBg(i)"
              >
                <img :src="b.src" :alt="b.label" />
                <i>{{ b.label }}</i>
              </button>
              <button type="button" class="ed-bg ed-bg-up" :class="{ on: !!form.bgPath }" @click="bgEl.click()">
                <template v-if="form.bgPath && auth.bgUrl">
                  <img :src="auth.bgUrl" alt="" />
                  <i>我的自定义</i>
                </template>
                <template v-else>
                  <span>{{ uploadingBg ? '…' : '＋' }}</span>
                  <i>上传自定义</i>
                </template>
              </button>
              <input ref="bgEl" type="file" accept="image/*" hidden @change="onBgPick" />
            </div>
          </div>""",
    """          <div class="ed-bg">
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
          </div>""",
    'C5-dialog-tpl',
)

# ── 6) 隐藏输入移到根部（弹窗关闭时头像也能直接点换） ──
rep(
    """              <p>JPG / PNG，自动压缩到 400px，存云存储</p>
              <input ref="avatarEl" type="file" accept="image/*" hidden @change="onAvatarPick" />""",
    """              <p>JPG / PNG，自动压缩到 400px，存云存储</p>""",
    'C6a-rm-avatar-input',
)
rep(
    """      <LightBox :images="lbImages" :index="lbIndex" :open="lbOpen" @close="lbOpen = false" @update:index="lbIndex = $event" />""",
    """      <input ref="avatarEl" type="file" accept="image/*" hidden @change="onAvatarPick" />
      <input ref="bgEl" type="file" accept="image/*" hidden @change="onBgPick" />

      <LightBox :images="lbImages" :index="lbIndex" :open="lbOpen" @close="lbOpen = false" @update:index="lbIndex = $event" />""",
    'C6b-root-inputs',
)

io.open(P, 'w', encoding='utf-8').write(s)
print('PART-A ok:', ', '.join(applied), f'({orig_len} -> {len(s)})')
