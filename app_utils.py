"""
公共工具模块：底图、异常兜底、GPX 解析、距离计算。

设计目标：任何一个页面出错时，用户看到的是一句中文提示，
而不是一大段 Python traceback（线上那种红色报错页）。
"""

import math
import os
import random
import traceback
import xml.etree.ElementTree as ET

import streamlit as st

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")

# ---------------------------------------------------------------- 国内可用底图
# 这些瓦片由访问者浏览器直接加载，国内网络可直接打开，无需 API Key。
#
# 注意 {s} 子域名：高德只接受 1/2/3/4，而 folium 默认会填 a/b/c，
# 那样就会去请求 webrd0a.is.autonavi.com（不存在）→ 地图整片灰。
# 所以下面每个底图都要显式带上 subdomains。
TILES = {
    "高德矢量": "https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
    "高德影像": "https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}",
    "高德注记": "https://webst0{s}.is.autonavi.com/appmaptile?style=8&x={x}&y={y}&z={z}",
    "Carto浅色": "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
}

SUBDOMAINS = {"高德矢量": "1234", "高德影像": "1234", "高德注记": "1234"}

ATTRS = {
    "高德矢量": "© 高德地图",
    "高德影像": "© 高德地图",
    "高德注记": "© 高德地图",
    "Carto浅色": "© OpenStreetMap contributors © CARTO",
}

# 界面上给用户选的底图（都是实测能出图的）
BASEMAP_CHOICES = ["高德矢量", "高德影像", "高德影像 + 注记", "Carto浅色"]


def tile_url(name: str) -> str:
    return TILES.get(name, TILES["高德矢量"])


def tile_layer_kwargs(name: str) -> dict:
    """把一个底图名转成 folium TileLayer 的参数。"""
    key = "高德影像" if name not in TILES else name
    kwargs = {
        "url": TILES[key],
        "name": name,
        "attribution": ATTRS.get(key, " "),
        "max_zoom": 18,
    }
    if key in SUBDOMAINS:
        kwargs["subdomains"] = SUBDOMAINS[key]
    return kwargs


def add_base_map(m, name: str = "高德矢量"):
    """给 leafmap 地图对象加底图。支持「高德影像 + 注记」两层叠加。"""
    if name == "高德影像 + 注记":
        m.add_tile_layer(**tile_layer_kwargs("高德影像"))
        m.add_tile_layer(**tile_layer_kwargs("高德注记"))
        return m
    m.add_tile_layer(**tile_layer_kwargs(name))
    return m


def new_map(center=(35.0, 105.0), zoom=4, basemap="高德矢量"):
    """创建以中国为中心的 leafmap 地图。"""
    import leafmap.foliumap as leafmap

    if basemap not in BASEMAP_CHOICES:
        basemap = "高德矢量"
    m = leafmap.Map(center=list(center), zoom=zoom, draw_control=False, tiles=None)
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


# ---------------------------------------------------------------- 地图渲染
def show_map(m, height: int = 560, scrolling: bool = False):
    """在 Streamlit 页面上渲染 folium / leafmap 地图。

    刻意不用 leafmap 的 m.to_streamlit()：它内部走 to_html()，而 to_html()
    会先把地图 save 到临时文件，再用 `open(outfile)`（不指定编码）读回来。
    中文 Windows 的默认编码是 GBK，读 UTF-8 内容必然抛
    UnicodeDecodeError: 'gbk' codec can't decode byte ...

    这里改成直接 render 成字符串，全程不落盘，与操作系统编码完全无关。
    """
    import streamlit.components.v1 as components

    try:
        # to_html() 原本会顺手补一个图层控件，这里等价补上
        if getattr(m, "options", {}).get("layersControl", False):
            m.add_layer_control()
            m.options["layersControl"] = False
    except Exception:  # noqa: BLE001  控件加不上不影响出图
        pass

    components.html(m.get_root().render(), height=height, scrolling=scrolling)


# ---------------------------------------------------------------- 读表
def read_csv_smart(src, **kwargs):
    """读 CSV，自动适配 UTF-8 / 带 BOM 的 UTF-8 / GBK。

    中文 Windows 上 Excel 另存的 CSV 通常是 GBK，网上下的通常是 UTF-8，
    光靠默认编码一定会踩坑，所以按顺序试。
    """
    import pandas as pd

    if "encoding" in kwargs:
        return pd.read_csv(src, **kwargs)

    last_err = None
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            if hasattr(src, "seek"):
                src.seek(0)
            return pd.read_csv(src, encoding=enc, **kwargs)
        except (UnicodeDecodeError, UnicodeError) as exc:
            last_err = exc
            continue
    raise last_err


@st.cache_data(show_spinner=False)
def load_attractions():
    """加载景点表。"""
    return read_csv_smart(data_path("attractions.csv"))


@st.cache_data(show_spinner=False)
def load_routes():
    """加载徒步路线表：内置规划轨迹 + 用户导入的 GPX 实测航迹。"""
    import pandas as pd

    base = read_csv_smart(data_path("hiking_routes.csv"))
    base["source"] = "planned"

    custom_fn = data_path("custom_routes.csv")
    if os.path.exists(custom_fn):
        try:
            extra = read_csv_smart(custom_fn)
            if len(extra):
                extra["source"] = "gpx"
                # 只取两边都有的列，避免导入表结构升级后把老数据带崩
                cols = [c for c in base.columns if c in extra.columns]
                merged = pd.concat([base[cols], extra[cols]], ignore_index=True)
                return merged
        except Exception:  # noqa: BLE001  导入表坏了也不该拖垮整页
            pass
    return base


# ---------------------------------------------------------------- 真实轨迹
TRACK_DIR = os.path.join(DATA_DIR, "tracks")


@st.cache_data(show_spinner=False)
def load_track(track_id: str):
    """读取构建好的真实轨迹（含途经点、海拔、速度剖面）。

    轨迹由 tools/build_tracks.py 一次性生成：途经点 → OSRM 步行路网 →
    SRTM 30m 海拔。运行时不访问任何外部接口，所以页面不会因为接口挂了而白屏。
    """
    import json

    fn = os.path.join(TRACK_DIR, f"{track_id}.json")
    if not os.path.exists(fn):
        return None
    with open(fn, encoding="utf-8") as f:
        return json.load(f)


def track_points(track) -> list:
    """把轨迹 JSON 转成 [(lat, lon, ele), ...]。"""
    if not track:
        return []
    return [(p[0], p[1], p[2] if len(p) > 2 else None) for p in track["points"]]


def track_km_at(track, index: int) -> float:
    pts = track["points"]
    index = max(0, min(index, len(pts) - 1))
    return pts[index][3] if len(pts[index]) > 3 else 0.0



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


# ---------------------------------------------------------------- 示意轨迹
def _stable_seed(text: str) -> int:
    """把字符串转成稳定整数（内置 hash() 每个进程随机，不能用）。"""
    h = 2166136261
    for ch in str(text):
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def gen_track(name, lat, lon, distance_km, ascent_m, n_points=None):
    """按路线的「起点 + 标称里程 + 标称爬升」反推一条确定性示意轨迹。

    注意：这不是实测 GPX。两步路那类真实轨迹需要下载或实地记录，
    这里生成的折线走向自然、长度与爬升都贴合标称值，用于在没有 GPX 时
    把路线画在地图上；要真实轨迹请用 GPX 上传替换。

    返回 [(lat, lon, ele), ...]
    """
    total_m = max(800.0, float(distance_km) * 1000.0)
    n = n_points or int(min(360, max(48, total_m / 110.0)))
    n = max(int(n), 8)

    rnd = random.Random(_stable_seed(name))
    heading = rnd.uniform(0, 360.0)
    drift = rnd.choice([-1, 1]) * rnd.uniform(0.1, 0.35)
    swing_amp = rnd.uniform(12.0, 30.0)
    swing_freq = rnd.uniform(2.5, 6.5)
    phase = rnd.uniform(0, 2 * math.pi)
    base = rnd.uniform(20.0, 120.0)  # 山脚基准海拔

    # 海拔剖面：主趋势整体爬升，叠加两级起伏。
    # 起伏幅度必须大于趋势单步升幅，否则曲线单调向上、累计下降会算成 0。
    raw = []
    for i in range(n):
        t = i / (n - 1)
        raw.append(
            0.70 * t
            + 0.080 * math.sin(t * math.pi * 6.0 + phase)
            + 0.035 * math.sin(t * math.pi * 13.0 + phase * 1.7)
        )

    def build(step_len):
        pts = []
        cur_lat, cur_lon = float(lat), float(lon)
        for i in range(n):
            pts.append([cur_lat, cur_lon])
            if i == n - 1:
                break
            t = i / (n - 1)
            h = math.radians(
                heading + drift * i + math.sin(t * math.pi * swing_freq + phase) * swing_amp
            )
            cur_lat += (step_len * math.cos(h)) / 111320.0
            cur_lon += (step_len * math.sin(h)) / (111320.0 * math.cos(math.radians(cur_lat)))
        return pts

    # 先按均分步长生成，再按实际长度校正一次，让里程贴近标称值
    step = total_m / (n - 1)
    pts = build(step)
    actual = sum(haversine_m(p, q) for p, q in zip(pts, pts[1:]))
    if actual > 0:
        pts = build(step * total_m / actual)

    # 按「累计正向爬升」归一化，使总爬升贴近标称爬升值
    pos = sum(max(0.0, b - a) for a, b in zip(raw, raw[1:]))
    scale = (float(ascent_m) / pos) if (pos > 1e-9 and ascent_m) else 400.0
    eles = [max(1.0, base + v * scale) for v in raw]

    return [(p[0], p[1], e) for p, e in zip(pts, eles)]


def track_profile(points):
    """把轨迹转成剖面数据 [(累计距离 km, 海拔 m), ...]。"""
    out, acc = [], 0.0
    for i, p in enumerate(points):
        if i:
            acc += haversine_m(points[i - 1], p)
        out.append((acc / 1000.0, p[2] if p[2] is not None else 0.0))
    return out


def track_to_gpx(points, name="track"):
    """导出 GPX 文本，可直接导入两步路 / 户外助手等 App。"""
    from xml.sax.saxutils import escape

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="xiangyue-map" '
        'xmlns="http://www.topografix.com/GPX/1/1">',
        f"  <trk><name>{escape(str(name))}</name><trkseg>",
    ]
    for p in points:
        ele = "" if p[2] is None else f"<ele>{p[2]:.1f}</ele>"
        parts.append(f'    <trkpt lat="{p[0]:.6f}" lon="{p[1]:.6f}">{ele}</trkpt>')
    parts += ["  </trkseg></trk>", "</gpx>"]
    return "\n".join(parts)


# ---------------------------------------------------------------- GPX / 距离
def _localname(tag: str) -> str:
    return tag.split("}")[-1]


def parse_gpx(raw: bytes, source_name: str = "track", with_waypoints: bool = False):
    """解析 GPX，返回 [(lat, lon, ele_or_None), ...]。

    只取 trkpt / rtept 作为轨迹点；wpt 是独立路点（补给点、垭口），
    混进轨迹会让线头尾乱跳，所以单独拿出来。
    文件里没有轨迹段时才退回用 wpt 当轨迹。

    with_waypoints=True 时返回 (points, waypoints)，waypoints 为
    [{'name','lat','lon','ele'}]。
    """
    root = ET.fromstring(raw)
    trk, wpts = [], []
    for elem in root.iter():
        tag = _localname(elem.tag)
        if tag not in ("trkpt", "rtept", "wpt"):
            continue
        try:
            lat = float(elem.attrib["lat"])
            lon = float(elem.attrib["lon"])
        except (KeyError, ValueError):
            continue
        ele = None
        name = None
        for child in elem:
            ctag = _localname(child.tag)
            if ctag == "ele" and child.text:
                try:
                    ele = float(child.text)
                except ValueError:
                    pass
            elif ctag == "name" and child.text:
                name = child.text.strip()
        if tag == "wpt":
            wpts.append({"name": name or "路点", "lat": lat, "lon": lon, "ele": ele})
        else:
            trk.append((lat, lon, ele))

    points = trk or [(w["lat"], w["lon"], w["ele"]) for w in wpts]
    if not points:
        raise ValueError(f"{source_name} 里没有找到轨迹点（trkpt/rtept/wpt）")
    if with_waypoints:
        return points, wpts
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
        "1. 左侧菜单切换页面\n"
        "2. 景点页左列点选，右列看「值得去的理由」\n"
        "3. 徒步页选路线，地图点起点可看轨迹\n"
        "4. 底图默认高德，国内可正常加载"
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("景点与路线信息整理自公开资料，出行前请以官方公告为准。")
