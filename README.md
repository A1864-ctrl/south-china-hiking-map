# 湘粤赣桂旅游与徒步地图

一个 Streamlit 应用：查景点、看徒步轨迹（贴合真实路网）、比城市热度。
覆盖广东、湖南、江西、广西桂林。

## 三个页面

| 页面 | 干什么 |
|---|---|
| 🔍 景点搜索 | 输入地名/景点名/类型，地图定位 + 卡片详情（值得去的点、门票、建议时长、最佳季节） |
| 🥾 徒步轨迹 | 轨迹线 + 编号途经点 + 高程剖面 + 速度曲线 + GPX 导出/上传分析 |
| 🔥 热度榜 | 城市维度汇总景点与路线，综合热度排名、观光/徒步散点、热度地图 |

## 轨迹是怎么来的（这是本项目最关键的部分）

不是两点直连，也不是随机折线，而是三层真实数据拼出来的：

```
途经点（地名） → OSM 官方坐标 → Valhalla 步行路网规划 → SRTM 30m 海拔 → data/tracks/*.json
```

1. **定位**：`tools/fetch_osm_index.py` 一次性拉取华南（20-31°N, 105-121°E）全部具名峰顶、
   景点、古迹、村镇，约 20 万个元素，存成按名字索引的本地库。之后按名字查表即可，
   峰顶还带官方海拔（祝融峰 1290 m、武功山金顶 1918 m、船底顶 1586 m）。
2. **规划**：`tools/build_tracks.py` 用 **Valhalla 的 pedestrian 配置**在途经点之间找真实步道。
   为什么不用 OSRM：OSM 在衡山这类景区步道不连通，OSRM 会把祖师殿→高台寺（直线 500 米）
   绕成 55 km；Valhalla 给 1.24 km，与实际相符。
3. **取海拔**：沿轨迹每 45 米查一次 SRTM 30 米高程，算出真实爬升、下降、剖面和坡度。

所以轨迹能看出盘山公路的之字形、绕湖段、山脊线。生成的 JSON 里每个点都是
`[lat, lon, ele, 累计公里]`，34 条路线共 **15,330** 个坐标点。

### 质量闸门

构建时会自动判不合格并跳过，避免画出误导性轨迹：

- 总里程超过途经点直线和 4.5 倍（说明路网缺失，在绕大圈）
- 单段走了 8 倍以上直线距离且超过 6 km（说明某个途经点坐标写偏）
- 登顶率低于 85%，即轨迹最高点远低于公开主峰海拔（说明没爬到山顶）
- 未及顶峰（<95%）且整条线不足 3 km（说明登山口落在山腰）
- 轨迹短于 0.6 km（说明途经点被吸附到一起）

> 注意：**登山线天然「直线短、实际长」**（盘山路、之字形上升），所以绕行倍数
> 只用来粗筛明显不连通的情况，判断「有没有上山」靠的是登顶率。

47 条候选路线里 34 条上架，其余 13 条被拦下。逐条原因见
[`轨迹体检报告.md`](轨迹体检报告.md)，也可以用 `python tools/audit_tracks.py` 重新生成。

## 导入真实航迹（GPX）

要说清楚一件事：**内置路线的线是「规划路径」，不是实测航迹。**
OSM 在华南山区的步道覆盖很稀，规划器只能沿公路和村道走，画出来会偏直、会绕远，
达不到两步路那种「一脚一脚」的精度。

要真实走位，把实测 GPX 导进来。导入后轨迹来源标为「🛰 实测」，和内置路线并列显示。

**方式一：页面导入**（单条）

「徒步路线 → 上传 GPX 分析」→ 选文件 → 看统计确认没选错 → 填名称/省份/城市 →
「保存到路线库」。

**方式二：批量导入**（一次几十条）

```bash
# 先试跑，只解析看统计，不写文件
python tools/import_gpx_dir.py D:\gpx\武功山 --dry-run

# 确认没问题再入库
python tools/import_gpx_dir.py D:\gpx\武功山 --province 江西省 --city 萍乡市 --heat 92
```

文件名当路线名，同名覆盖。数据落在 `data/tracks/gpx-*.json` + `data/custom_routes.csv`，
不动内置的 `hiking_routes.csv`，所以重新构建轨迹也不会冲掉导入的数据。

**GPX 从哪来**：两步路「我的 → 轨迹 → 导出 GPX」、高德「足迹 → 导出」、
Garmin / Coros / Suunto 手表同步出来的原始文件都可以。

导入时会做三件事：把 `wpt` 路点单独拎出来当途经点（不混进轨迹线）、
对高程做 5 点滑动平均后再算爬升（压掉 GPS 抖动造成的假爬升）、
按 4 米容差抽稀（上万点直接渲染会卡死浏览器）。

## 重新构建轨迹

```bash
# 首次：建立 OSM 坐标索引（约 7 分钟，30 MB，不进仓库）
python tools/fetch_osm_index.py

# 构建全部轨迹 + 重写 data/hiking_routes.csv
python tools/build_tracks.py

# 只重建某一条，并打印每个途经点的定位依据
python tools/build_tracks.py --only hengyang --verbose

# 体检：哪些路线没通过、为什么
python tools/audit_tracks.py --md 轨迹体检报告.md
```

## 目录

```
Home.py                 入口，只负责导航注册
app_utils.py            底图、异常兜底、轨迹读取、GPX 解析、距离计算
gpx_store.py            GPX → 轨迹 JSON 入库（页面导入与批量脚本共用）
views/                  4 个页面
data/attractions.csv    155 个景点（粤 71 / 湘 55 / 赣 16 / 桂 13）
data/hiking_routes.csv  内置徒步路线（里程爬升取自轨迹实测）
data/custom_routes.csv  导入的 GPX 路线（由 gpx_store 维护，可随时删）
data/tracks/*.json      每条路线的轨迹：坐标点、途经点、速度剖面、统计
tools/                  轨迹构建、体检与批量导入工具（运行时不依赖，不进页面）
```

## 本地运行

```bash
pip install -r requirements.txt
streamlit run Home.py
```

注意用虚拟环境里的解释器（`.\venv\Scripts\python.exe`），系统 Python 没装 streamlit。
Windows 上也可以直接双击 `start_local.bat`。

## 部署上线

仓库已就绪：`requirements.txt`（Python 依赖）、`packages.txt`（系统依赖）、
`.streamlit/config.toml`（主题 / 无头模式 / 上传上限）、`Dockerfile`（云服务器路线）。

- **免费方案**：Streamlit Community Cloud —— `share.streamlit.io` → Create app →
  选本仓库、分支 `master`、主文件 `Home.py`，Advanced settings 里 Python 版本选 `3.12`。
- **自建方案**：`docker build -t hiking-map . && docker run -d -p 8501:8501 --restart unless-stopped hiking-map`

完整步骤、验证清单、报错对照见 [`部署手册.md`](部署手册.md)。

## 文档

| 文件 | 内容 |
|---|---|
| [`部署手册.md`](部署手册.md) | 从本机到公网：Git 提交、GitHub 推送、云平台部署、别人打不开怎么办 |
| [`轨迹体检报告.md`](轨迹体检报告.md) | 47 条候选路线逐条体检，13 条未通过的根因与解法 |
| [`简历项目经验.md`](简历项目经验.md) | 功能梳理、技术栈、工程难点、简历写法、可投岗位分析 |

## 数据可信度

- **景点**：整理自公开资料，门票为参考价，以景区公告为准。
- **轨迹**：路径与海拔是真实数据（OSM + SRTM），但 OSM 在部分山区步道录入不全，
  走位仍可能与现场有偏差，**导航请以现场路标和官方轨迹为准**。
- **热度**：综合指数（景区等级、知名度、可达性估算），不是游客量统计。
