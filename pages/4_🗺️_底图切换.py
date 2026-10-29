"""底图切换：内置国内可直连底图 + xyzservices 全量检索 + 自定义 XYZ。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import leafmap.foliumap as leafmap
import streamlit as st

from app_utils import TILES, add_base_map, new_map, safe_run, sidebar_common

st.set_page_config(page_title="底图切换", layout="wide", page_icon="🗺️")


def main():
    sidebar_common()
    st.title("🗺️ 底图切换")
    st.caption("先选一个能打开的底图（国内直连），再考虑叠加业务图层。")

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 底图")
        domestic = st.selectbox("国内底图（推荐）", ["高德矢量", "高德影像", "腾讯矢量", "天地图影像", "OpenStreetMap"])
        extra = st.text_input("自定义 XYZ 瓦片地址（可选）", value="", placeholder="https://.../{z}/{x}/{y}.png")
        keyword = st.text_input("或搜索全球底图（关键词，英文更准）", value="")
        overlay_province = st.checkbox("叠加省级边界", value=False)

    tiles = None
    if keyword:
        try:
            options = leafmap.search_xyz_services(keyword=keyword)
            if options:
                tiles = st.multiselect(f"匹配到 {len(options)} 个，选择要显示的：", options)
            else:
                st.warning("没有匹配的底图，换个关键词试试（例如 terrain、satellite、dark）。")
        except Exception as exc:  # noqa: BLE001
            st.warning(f"底图检索不可用：{exc}")

    m = new_map(zoom=4, basemap=domestic)
    if domestic == "天地图影像":
        st.info("天地图需要先把 `app_utils.py` 里的 `tk=您的密钥` 换成你自己的天地图密钥，否则瓦片会显示空白。")

    if extra.strip():
        try:
            m.add_tile_layer(url=extra.strip(), name="自定义底图", attribution=" ")
        except Exception:  # noqa: BLE001
            st.warning("自定义瓦片地址格式不对，已忽略。")

    if tiles:
        for t in tiles:
            try:
                m.add_xyz_service(t)
            except Exception:  # noqa: BLE001
                st.warning(f"底图 {t} 加载失败，已跳过。")

    if overlay_province:
        import geopandas as gpd

        from app_utils import data_path

        gdf = gpd.read_file(data_path("china_provinces.geojson"))
        gdf = gdf[gdf["name"].notna()]
        m.add_gdf(gdf, layer_name="省级边界", info_mode="on_hover", fields=["name"])

    m.to_streamlit(height=640)

    with st.expander("这些底图的来源与建议"):
        st.markdown(
            """
- **高德 / 腾讯**：国内加载最快，日常查看、演示都够用；商用请遵守对应服务条款。
- **天地图**：国家地理信息公共服务平台，影像最权威，需要免费申请密钥（`tianditu.gov.cn`）。
- **OpenStreetMap**：数据最开放，但国内访问速度不稳定。
- 全球底图（xyzservices）里很多服务在境外，国内可能加载缓慢或打不开，优先用上面几个。
"""
        )


safe_run(main)
