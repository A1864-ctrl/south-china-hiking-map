"""
公共工具模块：底图、异常兜底、GPX 解析、距离计算。

设计目标：任何一个页面出错时，用户看到的是一句中文提示，
而不是一大段 Python traceback（线上那种红色报错页）。
"""

import math
import os
import traceback
import xml.etree.ElementTree as ET

import streamlit as st

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")

# ---------------------------------------------------------------- 国内可用底图
# 这些瓦片由访问者浏览器直接加载，国内网络可直接打开，无需 API Key。
TILES = {
    "高德矢量": "https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
    "高德影像": "https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}",
    "高德路网注记": "https://webst0{s}.is.autonavi.com/appmaptile?style=8&x={x}&y={y}&z={z}",
    "腾讯矢量": "https://rt0.map.gtimg.com/tile?z={z}&x={x}&y={-y}&type=vector&styleid=3",
    "天地图影像": "https://t0.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=您的密钥",
    "OpenStreetMap": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
}


def tile_url(name: str) -> str:
    return TILES[name]


def add_base_map(m, name: str = "高德矢量", attribution: str = "© 高德地图"):
    """给 leafmap 地图对象加一层底图。"""
    url = TILES.get(name, TILES["高德矢量"])
    m.add_tile_layer(url=url, name=name, attribution=attribution, max_zoom=18)
    return m


def new_map(center=(35.0, 105.0), zoom=4, basemap="高德矢量"):
    """创建以中国为中心的 leafmap 地图。"""
    import leafmap.foliumap as leafmap

    m = leafmap.Map(center=list(center), zoom=zoom, draw_control=False)
    add_base_map(m, basemap)
    return m


# ---------------------------------------------------------------- 异常兜底
def safe_run(main_func):
    """包住整个页面逻辑，任何异常都转成友好的中文提示。"""
    try:
        main_func()
    except Exception as exc:  # noqa: BLE001
        st.error("这个页面遇到了问题，已拦截，页面其余功能不受影响。")
        st.markdown(f"**错误摘要：**`{type(exc).__name__}: {exc}`")
        st.info(
            "常见原因：网络无法访问外部数据源、上传的文件格式不对、或依赖未安装。"
            "可以尝试刷新页面、换一个数据源，或上传自己的数据。"
        )
        with st.expander("展开技术细节（给开发者看）"):
            st.code(traceback.format_exc(), language="python")


def data_path(*parts) -> str:
    return os.path.join(DATA_DIR, *parts)


def json_safe_gdf(gdf):
    """只保留能安全转成 JSON 的列（去掉列表/数组类型的属性列）。

    GeoJSON 数据集里常见的 center、acroutes 等字段是数组，
    geopandas 的 to_json() 会直接抛 TypeError: ndarray is not JSON serializable。
    """
    keep = []
    for col in gdf.columns:
        if col == "geometry":
            keep.append(col)
            continue
        vals = gdf[col]
        if vals.map(lambda v: isinstance(v, (str, int, float, bool)) or v is None).all():
            keep.append(col)
    return gdf[keep]


# ---------------------------------------------------------------- GPX / 距离
def _localname(tag: str) -> str:
    return tag.split("}")[-1]


def parse_gpx(raw: bytes, source_name: str = "track") -> list:
    """解析 GPX，返回 [(lat, lon, ele_or_None), ...]。支持 trkpt / rtept / wpt。"""
    root = ET.fromstring(raw)
    points = []
    for elem in root.iter():
        if _localname(elem.tag) in ("trkpt", "rtept", "wpt"):
            try:
                lat = float(elem.attrib["lat"])
                lon = float(elem.attrib["lon"])
            except (KeyError, ValueError):
                continue
            ele = None
            for child in elem:
                if _localname(child.tag) == "ele" and child.text:
                    try:
                        ele = float(child.text)
                    except ValueError:
                        ele = None
                    break
            points.append((lat, lon, ele))
    if not points:
        raise ValueError(f"{source_name} 里没有找到轨迹点（trkpt/rtept/wpt）")
    return points


def haversine_m(a, b) -> float:
    """两点球面距离（米）。a/b = (lat, lon)。"""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371008.8 * math.asin(math.sqrt(h))


def track_stats(points):
    """计算总距离(km)、累计爬升(m)、累计下降(m)、最高/最低海拔。"""
    total = 0.0
    up = down = 0.0
    for p, q in zip(points, points[1:]):
        total += haversine_m(p, q)
        if p[2] is not None and q[2] is not None:
            diff = q[2] - p[2]
            if diff > 0:
                up += diff
            else:
                down -= diff
    eles = [p[2] for p in points if p[2] is not None]
    return {
        "distance_km": total / 1000.0,
        "ascent_m": up,
        "descent_m": down,
        "ele_min": min(eles) if eles else None,
        "ele_max": max(eles) if eles else None,
        "n_points": len(points),
    }


def fmt_km(km: float) -> str:
    return f"{km:.2f} km" if km < 10 else f"{km:.1f} km"


def page_header(title: str, subtitle: str = ""):
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def sidebar_common():
    st.sidebar.markdown("### 使用提示")
    st.sidebar.markdown(
        "1. 左侧菜单切换不同功能页面\n"
        "2. 底图默认使用高德，国内可正常加载\n"
        "3. 地图上按住左键拖动，滚轮缩放"
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("数据与底图均来自公开服务，仅供学习与演示使用。")
