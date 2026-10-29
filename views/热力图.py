"""热力图：按区域看点位密度与权重。

支持按「全国 / 广东省 / 湖南省」切换视野，权重可选房价或人口，
解决原来全国撒 35 个点、广东几乎看不清的问题。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import folium
import leafmap.foliumap as leafmap
import pandas as pd
import streamlit as st

from app_utils import BASEMAP_CHOICES, add_base_map, data_path, read_csv_smart, safe_run, show_map, sidebar_common

REGIONS = {
    "全国": {"center": (34.5, 108.0), "zoom": 4, "provinces": None},
    "广东省": {"center": (23.35, 113.45), "zoom": 7, "provinces": ["广东省"]},
    "湖南省": {"center": (27.65, 111.7), "zoom": 7, "provinces": ["湖南省"]},
}

WEIGHTS = {
    "房价（元/㎡）": "price_yuan_sqm",
    "人口（万人）": "population_wan",
    "只算密度（每个点权重相同）": None,
}


def main():
    sidebar_common()
    st.title("🔥 热力图")
    st.caption("颜色越亮红，代表该处的「权重 × 密度」越高。选区域可以直接看广东、湖南这类局部。")

    df = read_csv_smart(data_path("china_city_price.csv"))

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 视野与权重")
        region = st.selectbox("看哪个区域", list(REGIONS.keys()), index=1)
        weight_label = st.selectbox("热度权重", list(WEIGHTS.keys()), index=0)
        radius = st.slider("热力半径（像素）", 8, 45, 26)
        blur = st.slider("模糊度", 5, 35, 18)
        basemap = st.selectbox("底图", BASEMAP_CHOICES, index=0, key="heat_base")
        show_label = st.checkbox("叠加城市名", value=True)

    up = st.file_uploader("也可以上传自己的点位 CSV（需要 lon/lat 列）", type=["csv"])
    if up is not None:
        try:
            df = read_csv_smart(up)
            df.columns = [c.strip().lower() for c in df.columns]
            if not {"lon", "lat"}.issubset(df.columns):
                st.error("CSV 至少需要 lon 和 lat 两列。")
                st.stop()
            if "province" not in df.columns:
                df["province"] = "上传数据"
            if "city" not in df.columns:
                df["city"] = [f"点{i + 1}" for i in range(len(df))]
            st.success(f"已载入 {len(df)} 个点。")
        except Exception as exc:  # noqa: BLE001
            st.error(f"读取失败：{exc}")
            st.stop()

    cfg = REGIONS[region]
    pool = df if cfg["provinces"] is None else df[df["province"].isin(cfg["provinces"])]
    work = pool.dropna(subset=["lon", "lat"]).copy()
    if work.empty:
        st.warning(f"这个区域没有点位数据（{region}）。")
        return

    weight_col = WEIGHTS[weight_label]
    if weight_col and weight_col in work.columns:
        work["value"] = pd.to_numeric(work[weight_col], errors="coerce").fillna(0)
    else:
        work["value"] = 1.0
        if weight_col and weight_col not in work.columns:
            st.info(f"数据里没有 `{weight_col}` 列，已按「只算密度」渲染。")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("点位数", len(work))
    c2.metric("权重合计", f"{work['value'].sum():,.0f}")
    c3.metric("平均权重", f"{work['value'].mean():,.0f}")
    top = work.loc[work["value"].idxmax()]
    c4.metric("最热点", str(top.get("city", "—")), delta=f"{top['value']:,.0f}", delta_color="off")

    m = add_base_map(
        leafmap.Map(center=list(cfg["center"]), zoom=cfg["zoom"], draw_control=False, tiles=None),
        basemap,
    )
    m.add_heatmap(
        work,
        latitude="lat",
        longitude="lon",
        value="value",
        name=f"热度（{weight_label}）",
        radius=radius,
        blur=blur,
        min_opacity=0.35,
        max_zoom=12,
    )

    if show_label:
        for _, r in work.iterrows():
            txt = f"{r.get('city', '')}｜{r['value']:,.0f}"
            folium.Marker(
                location=[r["lat"], r["lon"]],
                icon=folium.DivIcon(
                    html=(
                        "<div style='font-size:10px;color:#333;background:rgba(255,255,255,0.72);"
                        "padding:1px 3px;border-radius:3px;white-space:nowrap;'>" + txt + "</div>"
                    ),
                    icon_size=(1, 1),
                    icon_anchor=(4, 4),
                ),
            ).add_to(m)

    show_map(m, height=620)

    st.markdown("---")
    left, right = st.columns([1.4, 1])
    with left:
        st.subheader(f"{region} 权重排行")
        show_cols = [c for c in ["city", "province", "price_yuan_sqm", "population_wan"] if c in work.columns]
        st.dataframe(
            work.sort_values("value", ascending=False)[show_cols].head(15),
            use_container_width=True,
            height=360,
        )
    with right:
        st.subheader("怎么读这张图")
        st.markdown(
            """
**密度**：同一块地方点越多，颜色越亮——它反映「点位扎堆程度」。

**权重**：每个点自带一个数值（房价或人口），权重大的点会把颜色拉得更亮，
所以珠三角会明显比粤北、粤东亮。

**两者叠加**：颜色 = 密集程度 × 单个点的权重大小。
只想看聚集、不看数值，就把权重切成「只算密度」。

**半径**调大会让相邻城市热区连成一片，适合看都市圈；
调小则能分辨单个城市，适合看具体哪里最热。
"""
        )


safe_run(main)
