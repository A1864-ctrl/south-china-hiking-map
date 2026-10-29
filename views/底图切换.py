"""底图切换：内置实测可用的国内底图 + 自定义 XYZ + 全球底图检索。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geopandas as gpd
import leafmap.foliumap as leafmap
import streamlit as st

from app_utils import (
    BASEMAP_CHOICES,
    SUBDOMAINS,
    add_base_map,
    data_path,
    json_safe_gdf,
    read_csv_smart,
    safe_run,
    show_map,
    sidebar_common,
)

def main():
    sidebar_common()
    st.title("🗺️ 底图切换")
    st.caption("四个底图都已实测能出图；先在这里确认底图正常，再去看其他页面就不会一片灰。")

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 底图")
        basemap = st.selectbox("底图（国内直连）", BASEMAP_CHOICES)
        st.caption("「影像 + 注记」= 卫星影像叠一层地名，找地方最方便。")
        custom = st.text_input("自定义 XYZ 地址（可选）", value="", placeholder="https://.../{z}/{x}/{y}.png")
        st.markdown("### 叠加图层")
        overlay_province = st.checkbox("省级边界", value=False)
        overlay_city = st.checkbox("城市点位（房价）", value=False)
        keyword = st.text_input("搜索全球底图（英文关键词）", value="")

    m = leafmap.Map(center=[35, 105], zoom=4, draw_control=False, tiles=None)
    add_base_map(m, basemap)

    if custom.strip():
        try:
            kwargs = {"url": custom.strip(), "name": "自定义底图", "max_zoom": 18}
            if "{s}" in custom:
                kwargs["subdomains"] = "1234"
            m.add_tile_layer(**kwargs)
        except Exception:  # noqa: BLE001
            st.warning("自定义瓦片地址格式不对，已忽略。")

    if overlay_province:
        try:
            gdf = gpd.read_file(data_path("china_provinces.geojson"))
            gdf = gdf[gdf["name"].notna()]
            m.add_gdf(json_safe_gdf(gdf), layer_name="省级边界", info_mode="on_hover", fields=["name"])
        except Exception as exc:  # noqa: BLE001
            st.caption(f"省级边界加载失败，已跳过（{type(exc).__name__}）。")

    if overlay_city:
        import folium
        import pandas as pd

        cities = read_csv_smart(data_path("china_city_price.csv")).dropna(subset=["lon", "lat"])
        for _, r in cities.iterrows():
            folium.CircleMarker(
                location=[r["lat"], r["lon"]],
                radius=4,
                color="#c62828",
                fill=True,
                fill_opacity=0.7,
                popup=f"{r['city']}：¥{r['price_yuan_sqm']:,.0f}/㎡",
            ).add_to(m)

    tiles = None
    if keyword:
        try:
            options = leafmap.search_xyz_services(keyword=keyword)
            if options:
                tiles = st.multiselect(f"匹配到 {len(options)} 个，选要叠加的：", options)
            else:
                st.warning("没有匹配的底图，换个关键词（terrain / satellite / dark）。")
        except Exception as exc:  # noqa: BLE001
            st.warning(f"底图检索不可用：{exc}")

    if tiles:
        for t in tiles:
            try:
                m.add_xyz_service(t)
            except Exception:  # noqa: BLE001
                st.warning(f"底图 {t} 加载失败，已跳过（境外服务可能被墙）。")

    show_map(m, height=640)

    with st.expander("底图说明：为什么只有这几个可用"):
        st.markdown(
            f"""
我们只保留了**实测能出图**的底图：

| 底图 | 用途 | 说明 |
| --- | --- | --- |
| 高德矢量 | 日常查看、看路名 | 国内最快，字大清晰 |
| 高德影像 | 看地形、建筑、水系 | 卫星影像，无地名 |
| 高德影像 + 注记 | 找具体地点 | 影像上叠一层地名注记，最推荐 |
| Carto浅色 | 做数据图、打点 | 浅色背景不抢戏，适合叠加分析 |

**为什么去掉了腾讯、天地图、OSM？**
- 腾讯瓦片接口返回的不是标准图片（需要额外的 TMS 坐标系转换），直接拿来做底图会灰屏；
- 天地图必须带自己申请的密钥（`tk=`），没有密钥一律返回空白，留着只会让人以为程序坏了；
- OpenStreetMap 在国内网络下经常打不开。

如果你有天地图密钥，可以在 `app_utils.py` 的 `TILES` 里加一条，`subdomains` 不用填。

当前高德瓦片的子域名配置：`{SUBDOMAINS.get("高德矢量")}`（高德只认 1/2/3/4，
填错字母就会整片灰——这是之前几个页面空白的原因）。
"""
        )


safe_run(main)
