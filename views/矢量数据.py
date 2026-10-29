"""矢量数据可视化：上传 GeoJSON / Shapefile(zip) / KML / CSV 点位，直接上图。

原页面顶部 `import fiona` 是报错主因（依赖里没有 fiona），这里改用
geopandas 1.x 默认的 pyogrio 引擎，不再需要 fiona。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os
import tempfile

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st

from app_utils import BASEMAP_CHOICES, data_path, json_safe_gdf, new_map, safe_run, show_map, sidebar_common

def to_gdf(uploaded):
    suffix = os.path.splitext(uploaded.name)[1].lower()
    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, uploaded.name)
    with open(path, "wb") as f:
        f.write(uploaded.getbuffer())
    if suffix == ".zip":
        path = "zip://" + path
    return gpd.read_file(path)


def main():
    sidebar_common()
    st.title("🔲 矢量数据可视化")
    st.caption("上传边界/点位数据，直接看形状、属性和分布。不依赖 fiona，纯 wheel 安装即可跑。")

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 数据与样式")
        source = st.radio("数据来源", ["内置：中国省级边界", "上传文件"])
        basemap = st.selectbox("底图", BASEMAP_CHOICES, index=0)
        fillcolor = st.color_picker("填充色", "#1f77b4")
        opacity = st.slider("填充透明度", 0.0, 1.0, 0.45)
        show_table = st.checkbox("显示属性表", value=True)

    gdf = None
    if source == "内置：中国省级边界":
        gdf = gpd.read_file(data_path("china_provinces.geojson"))
        gdf = gdf[gdf["name"].notna()].drop(columns=["center"], errors="ignore")
        st.caption("来源：阿里 DataV GeoAtlas 公开行政区划边界（省级，含港澳台）。")
    else:
        up = st.file_uploader("支持 .geojson / .json / .zip(Shapefile) / .kml / .gpkg", type=["geojson", "json", "zip", "kml", "gpkg"])
        if up is None:
            st.info("请先上传一个文件。想快速体验可以直接选左侧的「内置：中国省级边界」。")
            return
        try:
            gdf = to_gdf(up)
        except Exception as exc:  # noqa: BLE001
            st.error(f"文件解析失败：{exc}")
            st.info("Shapefile 请把 .shp/.dbf/.shx 一起打成 zip 再上传；GeoJSON 请确保是标准坐标系（WGS84）。")
            return

    if gdf is None or gdf.empty:
        st.warning("数据为空。")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("要素数量", f"{len(gdf)}")
    c2.metric("几何类型", ", ".join(sorted(set(gdf.geom_type.dropna()))))
    c3.metric("坐标系", str(gdf.crs) if gdf.crs else "未定义")

    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)

    # 去掉数组型属性列，避免 to_json 抛 ndarray 序列化错误
    safe = json_safe_gdf(gdf)

    m = new_map(zoom=4, basemap=basemap)
    label_field = next(
        (c for c in ("name", "NAME", "名称", "city", "省", "市") if c in gdf.columns), None
    )
    try:
        folium.GeoJson(
            safe.to_json(),
            style_function=lambda _: {"fillColor": fillcolor, "color": "#333333", "weight": 1, "fillOpacity": opacity},
            tooltip=folium.GeoJsonTooltip(fields=[label_field], aliases=["名称"]) if label_field else None,
        ).add_to(m)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"地图渲染失败，已跳过绘制：{exc}")
    show_map(m, height=560)

    if show_table:
        st.markdown("---")
        st.subheader("属性表")
        table = pd.DataFrame(safe.drop(columns="geometry"))
        st.dataframe(table, use_container_width=True, height=300)
        st.download_button(
            "下载为 GeoJSON",
            safe.to_json().encode("utf-8"),
            file_name="data.geojson",
            mime="application/geo+json",
        )


safe_run(main)
