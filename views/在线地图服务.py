"""在线地图服务（WMS）：修复了原页面调用已废弃接口导致的报错。

原代码 `leafmap.foliumap.get_wms_layers(url)` 在 leafmap 0.5x 之后被移除，
正确写法是 `leafmap.get_wms_layers(url)`（注意不是 foliumap 子模块）。
这里还额外提供 ESA WorldCover 全球地表覆盖图层，用来替代原来依赖
Google Earth Engine 的「Land Cover」页面。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

import leafmap
import leafmap.foliumap as leafmap_folium
import streamlit as st

from app_utils import BASEMAP_CHOICES, add_base_map, safe_run, show_map, sidebar_common

WORLDCOVER_URL = "https://services.terrascope.be/wms/v2"
WORLDCOVER_LAYER = "WORLDCOVER_2020_MAP"


def main():
    sidebar_common()
    st.title("📦 在线地图服务（WMS）")
    st.caption("不下载数据、不占磁盘，直接把远端的专题图层叠到地图上。")

    mode = st.sidebar.radio("图层来源", ["内置：全球地表覆盖", "自定义 WMS 服务"])
    basemap = st.sidebar.selectbox("底图", BASEMAP_CHOICES, index=0)
    opacity = st.sidebar.slider("图层透明度", 0.0, 1.0, 0.7)

    m = add_base_map(leafmap_folium.Map(center=[30, 105], zoom=3, tiles=None), basemap)

    if mode == "内置：全球地表覆盖":
        st.markdown(
            """
**ESA WorldCover 2020**：10 米分辨率的全球地表覆盖数据，包含林地、耕地、草地、
建成区、水体、湿地、裸地等 11 类。数据由欧洲空间局提供，通过 WMS 直接叠加，
**不需要任何密钥**，也替代了原来必须登录 Google Earth Engine 才能看的土地覆盖页面。
"""
        )
        try:
            m.add_wms_layer(
                WORLDCOVER_URL,
                layers=WORLDCOVER_LAYER,
                name="全球地表覆盖 2020",
                format="image/png",
                transparent=True,
                opacity=opacity,
            )
            legend = leafmap.builtin_legends.get("ESA_WorldCover")
            if legend:
                m.add_legend(title="地表覆盖类型", builtin_legend="ESA_WorldCover")
        except Exception as exc:  # noqa: BLE001
            st.warning(f"该服务当前不可用（境外服务，可能网络受限）：{exc}")
            st.info("可以先在左侧底图里选择「高德影像」，同样能看清地表形态。")
    else:
        url = st.text_input("WMS 服务地址（GetCapabilities）", value=WORLDCOVER_URL)
        st.caption("注意：服务端需要能访问该地址。只填写你信任的公开服务。")

        layers = []
        if st.button("获取图层列表", type="primary"):
            try:
                with st.spinner("正在读取服务能力文档…"):
                    options = leafmap.get_wms_layers(url)
                st.session_state["wms_options"] = options
                st.session_state["wms_url"] = url
            except Exception as exc:  # noqa: BLE001
                st.error(f"读取失败：{exc}")
                st.info("可能是地址不对、服务不响应，或该地址返回的不是标准 WMS 能力文档。")

        options = st.session_state.get("wms_options", [])
        if options:
            st.success(f"共读取到 {len(options)} 个图层。")
            picked = st.multiselect("选择要叠加的图层", options, default=options[:1])
            layers = picked
        elif not options and st.session_state.get("wms_url"):
            st.warning("没有解析到图层，请确认服务地址。")

        if layers:
            for layer in layers:
                try:
                    m.add_wms_layer(url, layers=layer, name=layer, transparent=True, opacity=opacity)
                except Exception as exc:  # noqa: BLE001
                    st.warning(f"图层 {layer} 添加失败：{exc}")

        legend_text = st.text_area(
            "图例（可选，JSON 字典：{\"类别\": \"#颜色\"}）",
            value='{"示例类别": "#2e7d32"}',
            height=120,
        )
        if st.checkbox("把图例加到地图上", value=False):
            try:
                m.add_legend(legend_dict=json.loads(legend_text))
            except Exception:  # noqa: BLE001
                st.warning("图例格式不是合法 JSON，已忽略。")

    show_map(m, height=620)

    st.markdown("---")
    st.markdown(
        """
**WMS 是什么？** 一种「按需返回图片」的地图服务标准：浏览器把当前视野的范围发给服务端，
服务端实时渲染并返回图片瓦片，所以既能用最新数据，又不用把几百 GB 数据下载到本地。

国内常用的 WMS/WMTS 服务：天地图（需免费密钥）、部分省级地理信息公共服务平台、
以及各地自然资源部门的政务地图服务。
"""
    )


safe_run(main)
