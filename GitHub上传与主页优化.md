# 把项目上传到 GitHub，并让 HR 一眼看懂

> 对象：这个项目 `D:\TJM\streamlit-geospatial`
> 目标：代码在 GitHub 上，主页打开就能看懂这是什么、能跑、是你写的。
> 全程按顺序做，每步都有「怎么确认成功」。

---

## 先回答你最关心的：需要「删掉旧项目」吗？

**不用删，也不建议删。** 原因：

1. GitHub 上那个仓库 **就是** 这个项目的仓库——本地代码和它已经连在一起（`origin`），
   你之前的提交都在里面。删掉重建 = 把提交历史、贡献记录一起删掉，
   而 HR 恰恰会看「有多少次提交、有没有持续迭代」。
2. 你真正不满意的应该是**仓库里混着别人项目的东西**（模板残留），
   这个已经处理完了，见下面第二节。

**唯一值得考虑的是"改个名字"**：`streamlit-geospatial` 是原模板的名字，
HR 搜一下会发现是别人的开源模板。改成 `south-china-hiking-map` 这类名字，
第一印象立刻变成"这个人自己做的项目"。改名会自动 301 跳转，旧链接不会失效。

---

## 一、从零上传到 GitHub 的完整流程

> 你的仓库已经建好了，这一节是**原理 + 备用操作**。
> 将来换电脑、换项目，照这个流程走一遍就行。

### 步骤 1：本机确认 Git 已装好

```powershell
git --version
```

有版本号就行（`git version 2.x`）。没有就去 https://git-scm.com/download/win 装，
一路默认下一步。

### 步骤 2：告诉 Git「你是谁」

只做一次，全局生效：

```powershell
git config --global user.name "A1864-ctrl"
git config --global user.email "你的GitHub注册邮箱"
```

> 为什么必须设：每次提交都会把这两个信息写进历史，HR 在 GitHub 上看到的
> 提交作者就是它。**邮箱要和 GitHub 账号一致**，否则提交不会算到你名下（头像不显示）。

### 步骤 3：在 GitHub 上建仓库

1. 登录 https://github.com → 右上角 **+** → **New repository**
2. **Repository name** 填 `south-china-hiking-map`（用英文，别用中文和空格）
3. 描述填一句英文的：`Interactive map of attractions and hiking trails in South China`
4. 选 **Public**（HR 要能点开看；Private 只有你自己看得到）
5. **不要**勾 "Add a README file"（你本地已有 README，勾了会冲突）
6. 点 **Create repository**

建完会看到一个空仓库页面，里面有一串命令——那就是下一步要用的。

### 步骤 4：把本地项目推上去

```powershell
cd D:\TJM\streamlit-geospatial

git init                                   # 只有第一次需要；已建过会提示 reinit，无害
git add -A                                 # 把改动放进暂存区
git commit -m "feat: 初始提交"              # 打包成一次提交
git branch -M main                         # 主分支改名（GitHub 默认叫 main）
git remote add origin https://github.com/你的用户名/仓库名.git
git push -u origin main
```

> 如果仓库已经有 `origin`（你这台机器就有），第 5 行会报
> `remote origin already exists`。改成：
> `git remote set-url origin https://github.com/你的用户名/仓库名.git`

**这一步会弹出登录窗口**，用户名填 GitHub 用户名，密码位置**必须填令牌（PAT）**，
不是账号密码——GitHub 从 2021 年起就不支持密码推送了。

### 步骤 5：生成访问令牌（PAT）——卡住最多的地方

1. GitHub 右上头像 → **Settings**
2. 左侧最下面 → **Developer settings**
3. **Personal access tokens** → **Tokens (classic)** → 右上 **Generate new token (classic)**
4. 可能要求输入密码确认身份，输入账号密码
5. 填表：
   - **Note**：`my-laptop-push`（随便写，自己能认出来就行）
   - **Expiration**：90 days（到期重新生成）
   - **Select scopes**：**只勾 `repo`**（这一个就够推代码，勾多了是安全隐患）
6. 拉到底点 **Generate token**
7. 页面显示 `ghp_xxxxxxxx...`，**立刻复制**——离开页面就再也看不到了

> **安全提醒**：令牌等于密码。不要写进代码、不要发到群里、不要贴在 URL 里。
> 如果怀疑泄露：回到同一个页面点 **Delete** 删掉，重新生成一个即可。

### 步骤 6：验证成功

```powershell
git log --oneline -1        # 能看到刚提交的说明
git remote -v               # origin 指向你的仓库
```

浏览器打开 `https://github.com/你的用户名/仓库名`，看两件事：

- 文件列表里有 `Home.py`、`app_utils.py`、`views/`、`data/`
- 页面下方能读到 README 渲染出来的内容（有标题、有徽章、有表格）

---

## 二、让仓库看起来「是你的项目」（已帮你做完，说明一下）

之前仓库里混着一批**原模板的东西**，HR 点开会觉得是照抄的。这些已经清掉了：

| 删掉的文件 | 为什么要删 |
|---|---|
| `index.html` | 里面写死 `share.streamlit.io/giswqs/streamlit-geospatial/app.py`，是**别人的应用地址** |
| `.github/FUNDING.yml` | 赞助链接指向原模板作者 `giswqs`，等于给别人的账户引流 |
| `Procfile` / `setup.sh` | Heroku 时代的部署文件，现在用 Streamlit Cloud / Docker 都不需要 |
| `.pre-commit-config.yaml` | 模板自带，本项目从没启用 |
| `data/china_provinces.geojson` | 582 KB，代码里已经没有任何地方引用它 |

同时做了两件事：

- **`LICENSE`**：保留原作者 MIT 声明 + 追加你的版权行。这是 MIT 协议的**义务**（保留原声明），
  做了反而说明你懂开源合规，不要删。
- **`README.md`** 重写成对外可读的样子：一句话定位 → 功能 → 架构图 → 技术决策 → 怎么跑。
  README 是 HR 在仓库里唯一一定会读的文件。

---

## 三、把「HR 打开主页就能看懂」做到位（5 件事）

这五件都在 GitHub 网页上点，不用写代码。

### 1. 改仓库名（建议做）

仓库页 → **Settings** → 最上面 **Rename** → 改成 `south-china-hiking-map` → 输入名字确认。

改完本地要同步一下，否则推送会报错：

```powershell
git remote set-url origin https://github.com/你的用户名/south-china-hiking-map.git
git remote -v    # 确认已经是新地址
```

### 2. 填仓库描述（Description）和标签（Topics）

在仓库首页右侧，**About** 那一栏点齿轮：

- **Description**：`Interactive Streamlit map for attractions and hiking trails in South China (155 spots · 34 trails · 15,330 GPS points)`
- **Website**：填你的在线地址（部署完再填，见部署手册）
- **Topics**：`streamlit` `gis` `python` `openstreetmap` `hiking` `data-visualization`
  `geospatial` `folium` `altair`

> 为什么重要：GitHub 搜索和 HR 第一眼都靠这两个字段判断"这是什么项目"。
> Topics 会显示成彩色小标签，视觉上很专业。

### 3. 把项目置顶到主页（**这一步最关键**）

HR 看的是**你的个人主页**（`https://github.com/A1864-ctrl`），不是某个仓库链接。
默认主页只显示"最近活跃的仓库"，你的项目可能排不到前面。

1. 打开自己的主页 `https://github.com/A1864-ctrl`
2. 右上角 **Customize your pins**（或右侧 Pinned 区域的铅笔图标）
3. 勾选 `south-china-hiking-map`
4. 拖到第一位 → **Save pins**

> 效果：任何人打开你的主页，第一块内容就是"Pinned"卡片，带仓库名 + 描述 + 语言。
> 这是简历里放主页链接能真正起作用的前提。

### 4. 让 README 顶部有「在线体验」链接

README 里现在写的是：

```markdown
> 🚧 **在线体验**：（部署后把这里换成 `https://xxx.streamlit.app`，步骤见 [部署手册](部署手册.md)）
```

部署完成后，把这一行换成：

```markdown
> 🔗 **在线体验**：https://你的域名.streamlit.app
```

> HR 不会为了看你的项目去配 Python 环境。**能点开就能用**，决定了他会不会认真看。

### 5. 顺手把个人主页也用起来

- **头像 + 简介**：Settings → Public profile → Bio 写一句
  `Python / GIS · 用公开地理数据做可视化应用`
- 简介里可以放项目链接
- 如果以后想更正式，可以建一个和自己用户名同名的仓库（`A1864-ctrl`），
  它的 README 会渲染在你的主页顶部——相当于一张个人名片

---

## 四、HR 视角的检查清单

发简历之前，用**无痕窗口**（Ctrl+Shift+N，不登录）打开你的主页，逐条打勾：

- [ ] 主页第一屏能看到 Pinned 里有这个项目
- [ ] 点进去，README 第一屏就有：一句话说明 + 徽章 + 在线链接
- [ ] 能看出**数据规模**（155 景点 / 34 路线 / 15,330 点）
- [ ] 能看出**用了什么技术**（README 有技术栈表格）
- [ ] 有架构图（Mermaid 图在 GitHub 上会渲染成真正的流程图）
- [ ] 仓库是 **Public**，不登录也能看
- [ ] 没有别人的名字混在里面（FUNDING、别人的部署地址都已清理）
- [ ] 有 License（说明你懂开源规则）
- [ ] 在线链接点得开（这一步取决于你有没有部署，见部署手册）

### 加分但不必强求

- README 里有 3–4 张界面截图（HR 看图比读字快）
- 提交信息是像样的英文/中文句子，不是 `update`、`1`、`fix bug`
- 有 `docs/` 目录放架构说明、数据字典

---

## 五、常见问题

### Q1：push 报 `schannel: failed to receive handshake` 或 `CONNECT tunnel failed, response 502`

**不是代码问题，是网络连不上 github.com**。按顺序试：

1. 关掉代理软件（Clash / V2Ray / 加速器），直连重试
2. 反过来：打开代理并切一个节点，再试
3. 换手机热点（这一步成功率最高）
4. 用 DNS 检查：`nslookup github.com` 能解析出 IP 才说明是连不通而不是解析失败

判断方法：`curl -o /dev/null -w "%{http_code}" https://github.com/` 返回 `200` 才代表通；
`000` 就是连不上。

### Q2：`Updates were rejected because the remote contains work...`

远端有你本地没有的提交（比如你在网页上直接改过 README）。先合并再推：

```powershell
git pull --rebase origin master
git push origin master
```

### Q3：`Authentication failed` / 一直要求输密码

令牌过期或被删了。重新生成一个（步骤 5），然后清掉系统缓存：

Windows 开始菜单搜「凭据管理器」→ **Windows 凭据** → 找到 `git:https://github.com` → **删除**，
下次 push 会重新弹窗。

### Q4：我改了分支名，Streamlit Cloud 上部署失败

部署时 Branch 字段要跟着改（`master` ↔ `main`）。或者干脆统一用 `master`：
GitHub 仓库 Settings → Default branch 改成 master。

### Q5：怎么确认「GitHub 上的文件就是本地的最终版」

```powershell
git status              # 显示 nothing to commit 就是都提交了
git log origin/master..HEAD --oneline    # 空 = 本地没有未推送的提交
```

第二条命令输出为空，才代表**线上和本地完全一致**。

---

## 六、以后每次改完的固定四步

```powershell
cd D:\TJM\streamlit-geospatial
git status                     # 看改了什么
git add -A
git commit -m "feat: 新增 XX 景点"    # 说清改了什么
git push origin master
```

推送完 2–3 分钟，Streamlit Cloud 会自动重新部署，不用做别的。
