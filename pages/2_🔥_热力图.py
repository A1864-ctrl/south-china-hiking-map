"""热力图：用国内城市点位做房价热力，替换原来索取美国城市数据的写法。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import leafmap.foliumap as leafmap
import pandas as pd
import streamlit as st

from app_utils import add_base_map, data_path, safe_run, sidebar_common

st.set_page_config(page_title="热力图", layout="wide", page_icon="🔥")


def main():
    sidebar_common()
    st.title("🔥 热力图")
    st.caption("把点的密度/权重渲染成热度，适合快速看出「哪里最集中、最贵」。")

    df = pd.read_csv(data_path("china_city_price.csv"))

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 参数")
        weight_col = st.selectbox("热度权重列", ["price_yuan_sqm", "常量（只看密度）"])
        radius = st.slider("热力半径（像素）", 8, 40, 22)
        blur = st.slider("模糊度", 5, 30, 15)
        basemap = st.selectbox("底图", ["高德矢量", "高德影像", "腾讯矢量"])

    up = st.file_uploader("也可以上传自己的点位 CSV（需要 lon/lat 列）", type=["csv"])
    if up is not None:
        try:
            df = pd.read_csv(up)
            df.columns = [c.strip().lower() for c in df.columns]
            if not {"lon", "lat"}.issubset(df.columns):
                st.error("CSV 至少需要 lon 和 lat 两列。")
                st.stop()
            st.success(f"已载入 {len(df)} 个点。")
        except Exception as exc:  # noqa: BLE001
            st.error(f"读取失败：{exc}")
            st.stop()

    work = df.dropna(subset=["lon", "lat"]).copy()
    if weight_col != "常量（只看密度）":
        work["value"] = work[weight_col].astype(float)
    else:
        work["value"] = 1.0

    col1, col2, col3 = st.columns(3)
    col1.metric("点位数", f"{len(work)}")
    col2.metric("权重合计", f"{work['value'].sum():,.0f}")
    col3.metric("最高权重点", str(work.loc[work["value"].idxmax(), work.columns[0]]) if len(work) else "-")

    m = add_base_map(leafmap.Map(center=[34, 108], zoom=4), basemap)
    m.add_heatmap(
        work,
        latitude="lat",
        longitude="lon",
        value="value",
        name="热度",
        radius=radius,
        blur=blur,
        min_opacity=0.3,
    )
    m.to_streamlit(height=620)

    st.caption("提示：热力图颜色由权重决定，颜色越亮代表该处权重越高、点位越密集。")


safe_run(main)
