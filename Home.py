import streamlit as st

st.set_page_config(
    page_title="徒步路线与地理空间工具",
    page_icon="🥾",
    layout="wide",
)

# ---------------------------------------------------------------- 侧边栏
st.sidebar.markdown("### 快速上手")
st.sidebar.markdown(
    """
1. 左侧菜单选一个功能页
2. 底图默认高德，国内直连
3. 地图左键拖动、滚轮缩放
"""
)
st.sidebar.markdown("---")
st.sidebar.markdown("### 关于")
st.sidebar.info(
    """
    基于 [streamlit-geospatial](https://github.com/opengeos/streamlit-geospatial)（MIT）二次开发，
    改造为国内可用的中文界面。

    底图与专题数据来自高德地图、阿里 DataV、ESA WorldCover 等公开服务。
    """
)
st.sidebar.caption("仅供学习与个人使用，请遵守各数据源的授权条款。")

# ---------------------------------------------------------------- 首页
st.title("🥾 徒步路线与地理空间工具")
st.markdown(
    "一个可以直接用的中文地图工作台：看路线、比底图、查房价、叠专题图层。"
    "**不依赖 Google Earth Engine，不需要任何 API 密钥**，打开即用。"
)

st.success(
    "当前所有页面均可正常运行。若某个页面提示数据源不可用，通常是外部服务网络问题，刷新或换底图即可。",
    icon="✅",
)

cols = st.columns(4)
cards = [
    ("🏠", "中国住房价格", "省级均价着色 + 城市气泡 + 排名榜，可上传自己的 CSV"),
    ("🔥", "热力图", "把点位密度或数值权重渲染成热区，一眼看出聚集"),
    ("📍", "点聚合", "点多时自动聚成一团，放大再展开成单个标注"),
    ("🗺️", "底图切换", "高德矢量/影像、腾讯、天地图、OSM 一键切换"),
    ("🪟", "分屏对比", "左影像右矢量，拖动中间滑块对照看"),
    ("🔲", "矢量数据", "上传 GeoJSON / Shapefile / KML，直接上图并看属性"),
    ("📦", "在线地图服务", "WMS 专题图层叠加，含全球地表覆盖（替代 GEE 版本）"),
    ("🥾", "徒步路线", "上传 GPX，算里程爬升、画高程剖面、导出 GeoJSON"),
]
for i, (icon, name, desc) in enumerate(cards):
    with cols[i % 4]:
        st.markdown(f"##### {icon} {name}")
        st.caption(desc)

st.markdown("---")
st.markdown(
    """
### 推荐使用顺序

| 场景 | 用哪一页 |
| --- | --- |
| 想快速看某条徒步路线 | 🥾 徒步路线 → 上传 GPX |
| 想找一片区域的地形 | 🗺️ 底图切换 → 高德影像 |
| 想对比影像和路网 | 🪟 分屏对比 |
| 想知道哪里房价最高 | 🏠 中国住房价格 → 三维视图 |
| 有自己的点数据要看分布 | 📍 点聚合 或 🔥 热力图 |
| 有自己画的边界文件 | 🔲 矢量数据 |
"""
)

with st.expander("这次改造做了什么？（原页面的报错与处理）"):
    st.markdown(
        """
| 原页面 | 原来的问题 | 现在怎么处理 |
| --- | --- | --- |
| U.S. Housing | 依赖美国 realtor.com 数据，国内下载失败（CURL 报错），且内容是美国房价 | 整页重做为**中国住房价格**，数据内置、可上传替换 |
| Timelapse / Earth Engine Datasets / Land Cover / Building Footprints | 依赖 `earthengine-api` + Google Earth Engine 账号授权，公共环境永远无法运行 | 下线这 4 页；其中「土地覆盖」用 ESA WorldCover 的 WMS 服务替代，放在「在线地图服务」页 |
| Web Map Service | 调用了 leafmap 已删除的 `leafmap.foliumap.get_wms_layers`，必报 AttributeError | 改为 `leafmap.get_wms_layers`，并改成「点按钮才请求」，避免每次打开都慢 |
| Raster Data Visualization | 依赖 localtileserver + 在线 COG 瓦片服务，缺依赖直接 IndexError | 下线；栅格影像需求用「底图切换」里的高德影像满足 |
| Vector Data Visualization | 顶部 `import fiona`，但依赖里没装 fiona | 改用 geopandas 自带的 pyogrio 引擎，去掉 fiona 依赖 |
| Heatmap / Marker Cluster / Basemaps / Split Map | 运行时去 GitHub 拉美国城市数据，国内常超时；底图默认是国外服务 | 全部换成本地中国城市数据 + 高德底图 |
| 全站 | `requirements.txt` 被精简到只剩 4 个包，但页面 import 了更多包 | 补齐依赖清单，并去掉需要编译 GDAL 的重型依赖 |
"""
    )

with st.expander("常见问题"):
    st.markdown(
        """
**地图一片灰白，没有底图？**
多半是该底图在你当前网络下打不开。回到「底图切换」换成「高德矢量」或「高德影像」。

**想换成自己的房价数据？**
在「中国住房价格」页左侧选「上传我的 CSV」，文件有两列即可：`province,price`
（省份名用「北京市」这种全称），或 `city,price,lat,lon` 做城市级气泡。

**上传 Shapefile 报错？**
把 `.shp / .dbf / .shx / .prj` 打成一个 zip 再上传，不要只传 .shp。

**为什么有的页面删掉了？**
它们必须连 Google Earth Engine 才能出图，而 GEE 需要个人账号授权，公开访问的网站没法带上你的密钥。留着只会永远报错。
"""
    )
