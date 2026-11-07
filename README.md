# 野径 · 华南徒步图鉴

**YEJING · South China Trails** —— 一个覆盖广东、湖南、江西、广西的徒步旅行站点：找景点、看路线、查天气、找搭子、记装备。

| 在线入口 | 地址 | 说明 |
|---|---|---|
| 🌟 **完整版（推荐）** | https://south-china-hiking.app.workbuddy.host/?sharecode=NXC6GS3IF3 | 云账号登录 · 社区 · 收藏同步 · 真实天气，功能全开 |
| 🪞 GitHub Pages 镜像 | https://a1864-ctrl.github.io/south-china-hiking-map/ | 免登录浏览全部内容；云功能按域名绑定在完整版上 |

> 分享给朋友时请**复制完整链接**（含 `?sharecode=` 后缀），只发域名会打不开。

## 界面一览

**首页 —— 一个页面把周末安排明白**

![首页](docs/screenshots/home.jpg)

**景点路书与路线详情**（76 个景点 / 53 条路线，双底图：高德矢量 + 天地图卫星）

| 景点路书 | 徒步轨迹 |
|---|---|
| ![景点路书](docs/screenshots/spots.jpg) | ![路线详情](docs/screenshots/route.jpg) |

**山野工具**（真实天气 · 营地库 · 社区）

| 点位天气（Open-Meteo 真实预报） | 营地库（22 处 · 五项权限可筛选） | 山友社区 |
|---|---|---|
| ![天气](docs/screenshots/weather.jpg) | ![营地](docs/screenshots/camps.jpg) | ![社区](docs/screenshots/community.jpg) |

## 有什么

- 📍 **76 个景点**：四季看点、实拍机位、吃什么、交通接驳
- 🥾 **53 条徒步路线**：8 个详情标签——概览轨迹 / 四季与光 / 分段路书 / 装备清单 / 补给与风险 / **路况与天气** / **山野科普**（22 个地区自然地理档案 × 8 类地貌：地形·植被带谱·动物·注意事项）/ 更多跳转
- 🌤️ **点位天气**：Open-Meteo 免费**真实预报**——当前实况 + 7 天 + 降水概率 + 阵风，按路线起点自动定位；断网自动回退本地模型
- ⛺ **营地库**：明火 / 水源 / 厕所 / 收费 / 过夜权限五项筛选，坐标全部取自路线真实途经点
- 👥 **山友社区**：发帖 / 点赞评论 / 找搭子（时间重叠 + 偏好匹配）/ **好友系统**（搜索 · 申请 · 同意）/ 路况上报（塌方·杂草·水源·蜂群，山友确认即审核挂载）/ 安全报备（平安打卡）
- 🎒 **装备库**：分类记账 + 按路线难度生成清单并与已有装备逐项比对
- 📖 **知识库**：LNT 无痕山林 8 篇 + 山野急救 8 篇
- 👤 **账号体系**：手机验证码 / 邮箱验证码 / 微信 / WorkBuddy 四种登录；等级按「累计使用时长 + 上传数据量」计算（Lv.1 初探 → Lv.6 传奇）；自定义头像与大背景

## 技术栈

`Vue 3` `<script setup>` · `Vite 5` · `Pinia` · `Vue Router`（hash） · `Leaflet 1.9`（GCJ-02 / WGS84 双底图） · 平台云服务（PostgreSQL 16 表 + 行级安全 + 云存储 + OAuth） · Open-Meteo · 零 UI 框架（全手写样式）

## 本地运行

```bash
npm install     # Node 18+
npm run dev     # http://127.0.0.1:5178
npm run build   # 产物在 dist/，双击 index.html 可离线打开
```

## 部署到 GitHub Pages（发布 / 更新网站）

一行命令（本仓库已配好脚本）：

```bash
python scripts/deploy_pages.py
```

脚本自动完成：构建 → 准备 gh-pages 工作副本 → 提交 → 推送 → GitHub Pages 自动发布。约 1–2 分钟后刷新 <https://a1864-ctrl.github.io/south-china-hiking-map/> 即可看到新版。首次使用前需要 `npm install`，且本机 git 已能推送 GitHub（已配置）。

> 前提说明：云登录 / 社区等按域名安全绑定在完整版站点上，Pages 镜像上这些按钮不可用；浏览、地图、天气、科普全部正常。

## 目录结构

```
├─ public/          静态资源源文件（564 张已核验实景图库）
├─ src/
│  ├─ data/         景点 / 路线 / 营地 / 天气模型 / 路线科普 / 省市数据
│  ├─ stores/       auth · social · fav · field · friends · ui
│  ├─ services/     云服务客户端（endpoint 配置由平台生成）
│  ├─ components/   18 个组件（LightBox / TopNav / AuthDialog …）
│  └─ views/        16 个页面
├─ db/              MySQL 8 设计（23 表 / 2 视图 / 3 触发器，建库 SQL）
├─ docs/            文档与截图
└─ scripts/         快照 / 验证 / 部署工具
```

## 数据与版本

- 数据规模：76 景点 · 53 路线 · 850km 轨迹 · 22 营地 · 74 装备 · 16 篇知识文章
- 版本沿革与逐轮对照：见站点内「更新日志」（页脚）或 `docs/`
- 本仓库 `main` 分支为源码正本，`gh-pages` 分支为 Pages 发布产物
