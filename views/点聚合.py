"""点聚合：点位多了先聚合，放大再展开，避免地图糊成一片。

颜色由本页自己控制（不用 leafmap 的自动配色，因为它按字符串排序取色，
颜色和图例对不上档位）。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import folium
import geopandas as gpd
import leafmap.foliumap as leafmap
import pandas as pd
import streamlit as st
from folium.plugins import MarkerCluster

from app_utils import (
    BASEMAP_CHOICES,
    add_base_map,
    data_path,
    json_safe_gdf,
    safe_run,
    sidebar_common,
)

# 价格档位：低 → 高，颜色从绿到红（涨红跌绿不适用，这里用"越贵越红"的常识色）
BINS = [
    ("2 万以下", 0, 20000, "#2e7d32"),
    ("2–5 万", 20000, 50000, "#f9a825"),
    ("5–10 万", 50000, 100000, "#ef6c00"),
    ("10 万以上", 100000, 10**9, "#c62828"),
]

PALETTE_CYCLE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
    "#e377c2", "#17becf", "#bcbd22", "#7f7f7f", "#aec7e8", "#ffbb78",
]


def dot(color: str) -> folium.DivIcon:
    return folium.DivIcon(
        html=(
            "<div style='width:13px;height:13px;border-radius:50%;background:"
            f"{color};border:2px solid #ffffff;box-shadow:0 0 3px rgba(0,0,0,0.45)'></div>"
        ),
        icon_size=(13, 13),
        icon_anchor=(6, 6),
    )


def swatch_legend(items, limit=8):
    shown = items[:limit]
    html = "".join(
        "<span style='display:inline-flex;align-items:center;margin:2px 16px 2px 0;font-size:12px'>"
        f"<span style='width:11px;height:11px;border-radius:50%;background:{c};margin-right:5px;"
        "border:1px solid #fff;box-shadow:0 0 2px #999'></span>"
        f"{lbl}</span>"
        for lbl, c in shown
    )
    if len(items) > limit:
        html += f"<span style='font-size:12px;color:#888'>… 另外 {len(items) - limit} 类</span>"
    st.markdown(html, unsafe_allow_html=True)


def main():
    sidebar_common()
    st.title("📍 点聚合标注")
    st.caption("点一多就会糊成一片；聚合后先看数量，放大自动展开成单个标注。")

    df = pd.read_csv(data_path("china_city_price.csv"))

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 参数")
        color_mode = st.selectbox("标注颜色", ["按价格档位", "按省份", "统一颜色"])
        show_province = st.checkbox("叠加省级边界", value=False)
        basemap = st.selectbox("底图", BASEMAP_CHOICES, index=0, key="cluster_base")
        radius = st.slider("聚合半径（像素）", 20, 110, 55)

    col1, col2 = st.columns([3, 1])
    with col2:
        province = st.multiselect("只看这些省份", sorted(df["province"].unique().tolist()))

    work = df[df["province"].isin(province)] if province else df
    work = work.dropna(subset=["lon", "lat"]).copy()

    if work.empty:
        st.warning("当前筛选条件下没有点位。")
        return

    with col1:
        m = add_base_map(
            leafmap.Map(center=[34.5, 108], zoom=4, draw_control=False, tiles=None), basemap
        )

        if show_province:
            try:
                gdf = gpd.read_file(data_path("china_provinces.geojson"))
                gdf = gdf[gdf["name"].notna()]
                folium.GeoJson(
                    json_safe_gdf(gdf).to_json(),
                    style_function=lambda _: {
                        "fillColor": "#000000",
                        "color": "#666666",
                        "weight": 1,
                        "fillOpacity": 0.02,
                    },
                ).add_to(m)
            except Exception as exc:  # noqa: BLE001
                st.caption(f"省级边界加载失败，已跳过（{type(exc).__name__}）。")

        legend_items = []
        if color_mode == "按价格档位":

            def bin_color(v):
                for _, lo, hi, col in BINS:
                    if lo <= float(v) < hi:
                        return col
                return BINS[0][3]

            work["_color"] = work["price_yuan_sqm"].map(bin_color)
            legend_items = [(b[0], b[3]) for b in BINS]
            work = work.sort_values("price_yuan_sqm")
        elif color_mode == "按省份":
            uniq = sorted(work["province"].unique())
            cmap = {p: PALETTE_CYCLE[i % len(PALETTE_CYCLE)] for i, p in enumerate(uniq)}
            work["_color"] = work["province"].map(cmap)
            legend_items = [(p, cmap[p]) for p in uniq]
        else:
            work["_color"] = "#2f6fed"

        mc = MarkerCluster(name="城市点位", options={"maxClusterRadius": radius})
        for _, r in work.iterrows():
            folium.Marker(
                location=[r["lat"], r["lon"]],
                icon=dot(r["_color"]),
                popup=folium.Popup(
                    f"<b>{r['city']}</b><br>{r['province']}<br>"
                    f"均价 ¥{r['price_yuan_sqm']:,.0f}/㎡",
                    max_width=240,
                ),
                tooltip=f"{r['city']}  ¥{r['price_yuan_sqm']:,.0f}",
            ).add_to(mc)
        mc.add_to(m)

        m.to_streamlit(height=600)
        if legend_items:
            swatch_legend(legend_items)

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("当前点位", len(work))
    c2.metric("涉及省份", work["province"].nunique())
    c3.metric("均价中位数", f"¥{work['price_yuan_sqm'].median():,.0f}/㎡")

    st.subheader("点位明细")
    st.dataframe(work, use_container_width=True, height=300)
    st.download_button(
        "下载当前筛选结果（CSV）",
        work.to_csv(index=False).encode("utf-8-sig"),
        file_name="cities_filtered.csv",
        mime="text/csv",
    )

    st.caption(
        "聚合圆上的数字＝这一团包含多少个点。放到街道级别会自动散成单个彩点，点开能看到城市与均价。"
    )


safe_run(main)
