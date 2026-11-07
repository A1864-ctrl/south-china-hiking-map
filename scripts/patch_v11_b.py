# -*- coding: utf-8 -*-
"""v11 补丁 B：MeView 模板（好友段 / 编辑弹窗 / 安全弹窗）+ CSS"""
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


# ── R10 好友段 + 更新页脚说明 ──
rep(
    """            <p class="foot-note">
              账号与数据都存在这台设备的浏览器里（localStorage），换设备不同步。密码用「盐 + SHA-256」本地校验，
              没有服务端；接上后端后会换成真正的手机验证码登录。
            </p>""",
    """            <!-- 08 山友 -->
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
            </p>""",
    'R10',
)

# ── R11 编辑资料弹窗重构 ──
rep(
    """      <!-- 编辑资料 -->
      <div v-if="editing" class="mask" @click.self="editing = false">
        <div class="dlg">
          <h3>编辑资料</h3>
          <label>
            <span>昵称</span>
            <input v-model="form.nickname" maxlength="16" placeholder="不超过 16 个字" />
          </label>
          <label>
            <span>签名</span>
            <input v-model="form.bio" maxlength="60" placeholder="一句话介绍自己，例：走过 20 条海岸线" />
          </label>
          <p class="dlg-tip">资料保存在你的云账号下，多设备登录都会同步。</p>
          <div class="dlg-acts">
            <button class="mini" @click="editing = false">取消</button>
            <button class="primary sm" @click="saveEdit">保存</button>
          </div>
        </div>
      </div>""",
    """      <!-- 编辑资料：头像 / 封面 / 昵称 / 签名 / 性别 / 地区 -->
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
              <input ref="avatarEl" type="file" accept="image/*" hidden @change="onAvatarPick" />
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
      </div>""",
    'R11',
)

# ── R12 CSS 追加 ──
css = """
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
  max-width: 460px;
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
.ed-genders {
  display: flex;
  gap: 6px;
  flex: 1;
}
.ed-genders button {
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
.ed-genders button.on {
  border-color: var(--forest);
  background: var(--forest-soft);
  color: var(--forest-dark);
}
.ed-region {
  display: flex;
  gap: 6px;
  flex: 1;
}
.ed-region select {
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
.ed-bg-up span {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 74%;
  font-size: 1rem;
  color: var(--gray-light);
}
.ed-bg-up i {
  text-align: center;
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
"""

pos = s.rfind('</style>')
assert pos > 0
s = s[:pos] + css + '\n' + s[pos:]
applied.append('R12-css')

io.open(P, 'w', encoding='utf-8').write(s)
print('PART2 ok:', ', '.join(applied), f'({orig_len} -> {len(s)})')
