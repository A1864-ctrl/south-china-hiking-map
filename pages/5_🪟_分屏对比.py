"""分屏对比：左影像、右矢量，同屏对照看地貌与路网。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import leafmap.foliumap as leafmap
import streamlit as st

from app_utils import TILES, safe_run, sidebar_common

st.set_page_config(page_title="分屏对比", layout="wide", page_icon="🪟")


def main():
    sidebar_common()
    st.title("🪟 分屏对比地图")
    st.caption("中间那条竖线可以左右拖动，两边地图同步移动缩放。")

    pairs = {
        "影像 vs 矢量": ("高德影像", "高德矢量"),
        "矢量 vs 影像": ("高德矢量", "高德影像"),
        "影像 vs 路网注记": ("高德影像", "高德路网注记"),
        "腾讯 vs 高德": ("腾讯矢量", "高德矢量"),
    }

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 参数")
        combo = st.selectbox("对比组合", list(pairs.keys()))
        zoom = st.slider("初始缩放级别", 3, 12, 5)
        lat = st.number_input("中心纬度", value=30.55, format="%.2f")
        lon = st.number_input("中心经度", value=104.07, format="%.2f")

    left, right = pairs[combo]
    m = leafmap.Map(center=[lat, lon], zoom=zoom, draw_control=False)
    try:
        m.split_map(
            left_layer=TILES[left],
            right_layer=TILES[right],
            left_label=left,
            right_label=right,
        )
    except Exception:  # noqa: BLE001
        st.info("当前 leafmap 版本的分屏插件加载失败，已退回到单幅地图。")
        m.add_tile_layer(url=TILES[right], name=right, attribution=" ")

    m.to_streamlit(height=660)

    st.markdown("---")
    st.markdown(
        """
**怎么用**
- 拖动中间的滑块：控制左右各显示多少
- 滚轮缩放、按住拖动：两边同步
- 影像适合看地形、水系、建筑形态；矢量适合看路名、行政边界
"""
    )


safe_run(main)
