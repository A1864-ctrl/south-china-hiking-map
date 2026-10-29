# 徒步路线与地理空间工具（中文版）

> 基于 [opengeos/streamlit-geospatial](https://github.com/opengeos/streamlit-geospatial)（MIT）二次开发，
> 已改造为**国内网络可直接使用**的中文界面，**不需要 Google Earth Engine、不需要任何 API 密钥**。

## 页面清单（8 个，全部可正常运行）

| 页面 | 能做什么 |
| --- | --- |
| 🏠 中国住房价格 | 省级均价着色 + 城市气泡 + 三维柱状 + 排名榜，支持上传自己的 CSV |
| 🔥 热力图 | 点位密度 / 数值权重渲染成热区 |
| 📍 点聚合 | 大量点位自动聚合，放大展开 |
| 🗺️ 底图切换 | 高德矢量/影像、腾讯、天地图、OSM，以及 xyzservices 全球底图检索 |
| 🪟 分屏对比 | 左影像右矢量，滑动对比 |
| 🔲 矢量数据 | 上传 GeoJSON / Shapefile(zip) / KML / GPKG，属性表 + 导出 |
| 📦 在线地图服务 | WMS 专题图层叠加，含 ESA WorldCover 地表覆盖 |
| 🥾 徒步路线 | 上传 GPX，算里程/爬升，画高程剖面，导出 GeoJSON |

## 技术栈

Python · Streamlit · Leafmap · Folium · GeoPandas(pyogrio) · PyDeck · Leaflet · 高德地图瓦片

## 本地运行

```bash
# 1. 创建虚拟环境
python -m venv venv

# 2. 激活环境（Windows）
venv\Scripts\activate

# 3. 安装依赖（requirements.txt 已包含全部所需包）
pip install -r requirements.txt

# 4. 启动
streamlit run Home.py
```

## 部署到 Streamlit Community Cloud

```bash
git add -A
git commit -m "fix: 修复全部页面报错，中文化改造"
git push origin main
```

推送后 Streamlit Cloud 会自动重新部署（约 2–3 分钟）。
如果 GitHub 远端地址里的令牌失效，用 `git remote set-url origin https://<你的token>@github.com/A1864-ctrl/streamlit-geospatial.git` 重新设置。

> 注意：Streamlit Community Cloud 目前对**未登录访问者**统一要求登录（官方策略）。
> 想让别人免登录直接打开，可考虑 Hugging Face Spaces、或部署到自己的云服务器。

## 数据来源与说明

- 行政区划边界：阿里 DataV GeoAtlas 公开数据（省级，含港澳台）
- 底图瓦片：高德地图 / 腾讯地图 / OpenStreetMap / 天地图（需自行申请密钥）
- 地表覆盖：ESA WorldCover 2020，通过 `services.terrascope.be` 的 WMS 服务
- **房价数据为演示用近似值**（量级参考 2024 年前后二手房挂牌均价），不构成投资依据；
  严谨分析请在页面里上传真实 CSV。

## 本次修复的问题（原版本必崩的页面）

| 原页面 | 报错 | 原因 | 处理 |
| --- | --- | --- | --- |
| Timelapse / Earth Engine Datasets / Land Cover / Building Footprints | `ModuleNotFoundError: No module named 'ee'` | 依赖 `earthengine-api` + GEE 账号授权，公共环境无法运行 | 下线 4 页；地表覆盖改用 ESA WorldCover WMS |
| Web Map Service | `AttributeError: module 'leafmap.foliumap' has no attribute 'get_wms_layers'` | leafmap 新版把该方法移到顶层模块 | 改为 `leafmap.get_wms_layers`，并改为按需请求 |
| Vector Data Visualization | `ModuleNotFoundError: No module named 'fiona'` | 顶部 `import fiona`，但依赖未安装 | 改用 geopandas 自带 pyogrio 引擎 |
| Raster Data Visualization | `IndexError: list index out of range` | 依赖 localtileserver + 在线 COG 服务 | 下线 |
| U.S. Housing | `CURL error: ... revocation status is unknown` | 运行时下载美国 realtor.com 数据 | 整页重做为「中国住房价格」 |
| Heatmap / Marker Cluster / Basemaps / Split Map | GitHub 拉美国数据超时、底图境外 | 数据源与底图都不适合国内 | 换本地中国数据 + 高德底图 |
| 全站 | 依赖安装不完整 | `requirements.txt` 被精简到 4 个包 | 补齐依赖，去掉 GDAL 编译依赖 |

## 许可证

MIT，遵循上游项目协议。
