"""分屏对比：左右两幅同位置地图，拖动中缝对照看。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import leafmap.foliumap as leafmap
import streamlit as st

from app_utils import SUBDOMAINS, TILES, safe_run, sidebar_common

PAIRS = {
    "影像 vs 矢量（最常用）": ("高德影像", "高德矢量"),
    "矢量 vs 影像": ("高德矢量", "高德影像"),
    "影像 vs 影像+注记": ("高德影像", "高德注记"),
    "影像 vs 浅色底图": ("高德影像", "Carto浅色"),
}


def main():
    sidebar_common()
    st.title("🪟 分屏对比地图")
    st.caption("中间那条竖线可以左右拖动，两边地图同步平移缩放。")

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 参数")
        combo = st.selectbox("对比组合", list(PAIRS.keys()))
        zoom = st.slider("初始缩放级别", 3, 14, 6)
        lat = st.number_input("中心纬度", value=23.35, format="%.2f")
        lon = st.number_input("中心经度", value=113.45, format="%.2f")

    left, right = PAIRS[combo]

    def args_for(name):
        # 注意：split_map 内部自己会传 attr=" "，这里再传 attr 会报
        # TileLayer() got multiple values for keyword argument 'attr'
        kwargs = {}
        if name in SUBDOMAINS:
            kwargs["subdomains"] = SUBDOMAINS[name]
        return kwargs

    m = leafmap.Map(center=[lat, lon], zoom=zoom, draw_control=False, tiles=None)
    try:
        m.split_map(
            left_layer=TILES[left],
            right_layer=TILES[right],
            left_args=args_for(left),
            right_args=args_for(right),
            left_label=left,
            right_label=right,
        )
    except Exception as exc:  # noqa: BLE001
        st.warning(f"分屏插件加载失败（{type(exc).__name__}），已退回单幅地图。")
        m.add_tile_layer(url=TILES[right], name=right, attribution=" ", subdomains="1234")

    m.to_streamlit(height=660)

    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(
            """
**怎么用**
- 拖中间滑块：控制左右各显示多少（0 或 100% 就是单幅）
- 滚轮缩放、按住拖动：两边完全同步
- 右上角图层按钮：切换底图
"""
        )
    with col2:
        st.markdown(
            """
**看什么**
- 影像：地形、水系、建筑形态、植被覆盖
- 矢量：路名、行政边界、POI
- 左边看「实际长什么样」，右边看「怎么走、叫什么」
"""
        )


safe_run(main)
