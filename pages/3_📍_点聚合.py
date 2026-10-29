"""点聚合：用国内城市点位做聚合标注，替换原来索取美国城市/区域数据的写法。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import folium
import geopandas as gpd
import leafmap.foliumap as leafmap
import pandas as pd
import streamlit as st

from app_utils import add_base_map, data_path, safe_run, sidebar_common

st.set_page_config(page_title="点聚合", layout="wide", page_icon="📍")


def main():
    sidebar_common()
    st.title("📍 点聚合标注")
    st.caption("点太多会糊成一片，聚合后先看数量，放大再展开成单个标注。")

    df = pd.read_csv(data_path("china_city_price.csv"))

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 参数")
        color_by = st.selectbox("按什么分类着色", ["province", "无"])
        show_province = st.checkbox("叠加省级边界", value=True)
        basemap = st.selectbox("底图", ["高德矢量", "高德影像", "腾讯矢量"], key="cluster_base")
        radius = st.slider("聚合半径", 20, 100, 50)

    col1, col2 = st.columns([3, 1])
    with col2:
        province = st.multiselect("只看这些省份", sorted(df["province"].unique().tolist()))
    work = df[df["province"].isin(province)] if province else df

    with col1:
        m = add_base_map(leafmap.Map(center=[34, 108], zoom=4), basemap)
        if show_province:
            try:
                gdf = gpd.read_file(data_path("china_provinces.geojson"))
                gdf = gdf[gdf["name"].notna()]
                folium.GeoJson(
                    gdf.to_json(),
                    style_function=lambda _: {
                        "fillColor": "#000000",
                        "color": "#555555",
                        "weight": 1,
                        "fillOpacity": 0.03,
                    },
                ).add_to(m)
            except Exception:  # noqa: BLE001
                st.caption("省级边界加载失败，已跳过。")

        try:
            color_col = None if color_by == "无" else color_by
            marker_colors = None
            if color_col:
                # leafmap 要求：颜色数量必须 ≥ 分类数量，否则直接抛 ValueError
                base = [
                    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
                    "#46f0f0", "#f032e6", "#bcf60c", "#fabebe", "#008080",
                    "#e6beff", "#9a6324", "#800000", "#aaffc3", "#808000",
                    "#000075", "#808080", "#ffe119", "#d2f53c", "#fabed4",
                    "#dcbeff", "#fffac8", "#aa6e28", "#ffd8b1",
                ]
                n = max(1, work[color_col].nunique())
                marker_colors = [base[i % len(base)] for i in range(n)]

            m.add_points_from_xy(
                work,
                x="lon",
                y="lat",
                popup=["city", "price_yuan_sqm"],
                color_column=color_col,
                marker_colors=marker_colors,
                add_legend=color_col is not None,
                layer_name="城市点位",
                radius=radius,
            )
        except TypeError:
            # 不同 leafmap 版本参数名有差异，退回到最简调用
            m.add_points_from_xy(work, x="lon", y="lat", popup=["city"])
        m.to_streamlit(height=620)

    st.markdown("---")
    st.subheader("点位明细")
    st.dataframe(work, use_container_width=True, height=260)

    st.download_button(
        "下载当前筛选结果（CSV）",
        work.to_csv(index=False).encode("utf-8-sig"),
        file_name="cities_filtered.csv",
        mime="text/csv",
    )


safe_run(main)
