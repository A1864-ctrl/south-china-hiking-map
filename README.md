# 徒步路线与地理空间工具（中文版）

> 基于 [opengeos/streamlit-geospatial](https://github.com/opengeos/streamlit-geospatial)（MIT）二次开发，
> 已改造为**国内网络可直接使用**的中文界面，**不需要 Google Earth Engine、不需要任何 API 密钥**。

侧边栏按用途分成三组：**开始 / 地理空间工具 / 户外徒步**。

## 页面清单（8 个，全部可正常运行）

| 分组 | 页面 | 能做什么 |
| --- | --- | --- |
| 开始 | 🏠 首页 · 能力说明 | 这个站能干什么、数据可信度、以及"要不要拆成两个站点"的建议 |
| 地理空间工具 | 🏘️ 中国住房价格 | 省级均价着色 + 城市气泡 + 三维柱状 + 排名榜，可上传 CSV |
| | 🔥 热力图 | 全国 / 广东 / 湖南三档视野，权重可选房价或人口，也可只看密度 |
| | 📍 点聚合 | 大量点位自动聚合，放大展开，颜色按价格档位或省份 |
| | 🗺️ 底图切换 | 高德矢量 / 影像 / 影像+注记 / CARTO 浅色，支持自定义 XYZ |
| | 🪟 分屏对比 | 左影像右矢量，拖动中缝对比 |
| | 🔲 矢量数据 | 上传 GeoJSON / Shapefile(zip) / KML / GPKG，属性表 + 导出 |
| | 📦 在线地图服务 | WMS 专题图层叠加，含 ESA WorldCover 地表覆盖（免密钥） |
| 户外徒步 | 🥾 徒步路线 | 湖南 15 条 + 广东 16 条路线库；上传 GPX 算里程爬升、画高程剖面 |

## 目录结构

```
Home.py              入口，用 st.navigation 做分组导航
app_utils.py         公共模块：底图配置、异常兜底、GPX 解析、距离计算
views/               8 个页面（导航模式下不用 pages/ 自动发现）
data/
  china_provinces.geojson    省级边界（含港澳台）
  china_province_price.csv   省级房价（演示数据）
  china_city_price.csv       城市点位 + 房价 + 人口
  hiking_routes.csv          湖南 / 广东徒步路线库
requirements.txt     依赖（不再需要编译 GDAL）
packages.txt         系统包
```

## 技术栈

Python · Streamlit（st.navigation）· Leafmap · Folium · GeoPandas(pyogrio) · PyDeck · 高德瓦片

## 本地运行

```bash
python -m venv venv
venv\Scripts\activate                 # Windows
pip install -r requirements.txt
streamlit run Home.py
```

## 部署到 Streamlit Community Cloud

```bash
git add -A
git commit -m "feat: 分组导航 + 广东湖南路线库 + 修复底图灰屏"
git push origin master
```

推送后约 2–3 分钟自动重新部署。

> Streamlit Community Cloud 目前对未登录访问者统一要求登录（官方策略）。
> 想让别人免登录直接打开，可考虑 Hugging Face Spaces 或自己的云服务器。

## 关键坑位（改代码前务必看）

1. **高德瓦片的 `{s}` 子域名只能是 1/2/3/4**。folium 的 `TileLayer` 默认子域名是 `a/b/c`，
   会去请求 `webrd0a.is.autonavi.com`（不存在），结果就是**整片灰**。
   本项目所有底图都在 `app_utils.tile_layer_kwargs()` 里显式设置了 `subdomains="1234"`，
   分屏 map 通过 `left_args / right_args` 传入。
2. **`gdf.to_json()` 遇到数组型属性列会崩**（`center`、`acroutes` 等），
   用 `app_utils.json_safe_gdf()` 先过滤成标量列。
3. **`leafmap.add_points_from_xy` 要求 `marker_colors` 数量 ≥ 分类数**，否则 ValueError。
4. **导航模式（st.navigation）下页面里不能再调 `st.set_page_config`**，只能在 `Home.py` 调一次。
5. 页面脚本要 import 根目录模块时，需手动把项目根加进 `sys.path`（每个 views 页顶部已有）。

## 数据来源与可信度

| 数据 | 来源 | 可信度 |
| --- | --- | --- |
| 省级行政区边界 | 阿里 DataV GeoAtlas | 高 |
| 底图瓦片 | 高德地图 / CARTO | 高（第三方服务，商用看条款） |
| 城市房价 | **演示用近似值** | ⚠️ 低，仅演示流程 |
| 城市人口 | 2020 七普量级 | 中（取整） |
| 徒步路线里程/爬升 | 公开资料整理 | 中（口径不同） |
| 地表覆盖 | ESA WorldCover 2020 | 高 |

## 更新记录

- 2026-10-29 修复底图灰屏（`{s}` 子域名）、省级边界叠加失败（ndarray 序列化）
- 2026-10-29 热力图增加区域视野（全国/广东/湖南）与人口权重；新增广东 21 市、湖南 14 市州点位
- 2026-10-29 徒步页新增湖南 15 条 + 广东 16 条路线库
- 2026-10-29 导航改为分组（地理空间工具 / 户外徒步），新增「首页 · 能力说明」
- 2026-10-29 首页去掉 4 张 GitHub 外链大 GIF（国内加载卡死导致刷新转圈）
- 2026-10-29 首轮：下线 4 个 GEE 页面、WMS 接口修复、fiona 依赖修复、美国住房改中国住房

## 许可证

MIT，遵循上游项目协议。
