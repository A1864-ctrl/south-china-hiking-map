"""徒步路线：上传 GPX 轨迹，看路线、算里程与爬升、画高程剖面。

这一页是把项目原本「徒步路线可视化」的定位补上——原项目里其实没有 GPX 功能。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import math

import folium
import leafmap.foliumap as leafmap
import pandas as pd
import streamlit as st

from app_utils import TILES, fmt_km, parse_gpx, safe_run, sidebar_common, track_stats

st.set_page_config(page_title="徒步路线", layout="wide", page_icon="🥾")

LINE_COLORS = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#008080"]


def demo_track(lat0=30.2455, lon0=120.1440, n=260):
    """生成一条环湖示例轨迹（带起伏高程），仅用于演示。"""
    pts = []
    for i in range(n):
        t = i / (n - 1) * 2 * math.pi
        r = 0.010 * (1 + 0.18 * math.sin(3 * t))
        lat = lat0 + r * math.sin(t)
        lon = lon0 + r * math.cos(t)
        ele = 20 + 45 * (1 - math.cos(2 * t)) / 2 + 6 * math.sin(9 * t)
        pts.append((lat, lon, ele))
    return pts


def cumulative_km(pts):
    from app_utils import haversine_m

    out, total = [0.0], 0.0
    for p, q in zip(pts, pts[1:]):
        total += haversine_m(p, q)
        out.append(total / 1000.0)
    return out


def main():
    sidebar_common()
    st.title("🥾 徒步路线")
    st.caption("上传 GPX 轨迹（手表、手机 App 都能导出），自动算里程、爬升，并画高程剖面。")

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 参数")
        basemap = st.selectbox("底图", ["高德影像", "高德矢量", "OpenStreetMap"], key="gpx_base")
        smooth = st.slider("高程剖面平滑窗口", 1, 25, 5)
        st.markdown("---")
        st.caption("没有 GPX 文件？点下面的按钮生成一条示例轨迹。")

    files = st.file_uploader("上传一个或多个 GPX 文件", type=["gpx"], accept_multiple_files=True)
    use_demo = st.button("生成示例路线")

    tracks = {}
    if files:
        for f in files:
            try:
                tracks[f.name] = parse_gpx(f.getvalue(), f.name)
            except Exception as exc:  # noqa: BLE001
                st.error(f"{f.name} 解析失败：{exc}")
    elif use_demo:
        tracks["示例路线（环湖一圈）"] = demo_track()

    if not tracks:
        st.info("等待轨迹数据：可以上传 .gpx，或点「生成示例路线」先看看效果。")
        st.markdown(
            """
**GPX 从哪来？**
- 手表：Garmin / 华为 / 佳明 App 都能导出 GPX
- 手机：两步路、六只脚、户外助手、Strava 的「导出轨迹」
- 也可以用「轨迹记录」类小程序录完再导出
"""
        )
        return

    rows = []
    for name, pts in tracks.items():
        s = track_stats(pts)
        rows.append(
            {
                "轨迹": name,
                "距离": fmt_km(s["distance_km"]),
                "累计爬升": f"{s['ascent_m']:.0f} m",
                "累计下降": f"{s['descent_m']:.0f} m",
                "最低海拔": "-" if s["ele_min"] is None else f"{s['ele_min']:.0f} m",
                "最高海拔": "-" if s["ele_max"] is None else f"{s['ele_max']:.0f} m",
                "轨迹点": s["n_points"],
                "distance_km": s["distance_km"],
                "ascent_m": s["ascent_m"],
            }
        )
    summary = pd.DataFrame(rows)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("轨迹条数", len(tracks))
    c2.metric("总里程", fmt_km(summary["distance_km"].sum()))
    c3.metric("总爬升", f"{summary['ascent_m'].sum():.0f} m")
    longest = summary.loc[summary["distance_km"].idxmax()]
    c4.metric("最长一条", fmt_km(longest["distance_km"]))

    first = next(iter(tracks.values()))[0]
    m = leafmap.Map(
        center=[first[0], first[1]],
        zoom=13,
        draw_control=False,
    )
    m.add_tile_layer(
        url=TILES.get(basemap, TILES["高德影像"]),
        name=basemap,
        attribution="© 高德地图",
        max_zoom=18,
    )

    for idx, (name, pts) in enumerate(tracks.items()):
        color = LINE_COLORS[idx % len(LINE_COLORS)]
        folium.PolyLine(
            [(p[0], p[1]) for p in pts], color=color, weight=4, opacity=0.9, tooltip=name
        ).add_to(m)
        folium.Marker(
            [pts[0][0], pts[0][1]], popup=f"{name} 起点", icon=folium.Icon(color="green", icon="play")
        ).add_to(m)
        folium.Marker(
            [pts[-1][0], pts[-1][1]], popup=f"{name} 终点", icon=folium.Icon(color="red", icon="stop")
        ).add_to(m)

    m.to_streamlit(height=560)

    st.markdown("---")
    st.subheader("轨迹汇总")
    st.dataframe(
        summary.drop(columns=["distance_km", "ascent_m"]), use_container_width=True
    )

    st.subheader("高程剖面")
    pick = st.selectbox("选择轨迹", list(tracks.keys()))
    pts = tracks[pick]
    km = cumulative_km(pts)
    ele = [p[2] if p[2] is not None else 0.0 for p in pts]
    profile = pd.DataFrame({"里程 (km)": km, "海拔 (m)": ele}).set_index("里程 (km)")
    if smooth > 1:
        profile["海拔 (m)"] = profile["海拔 (m)"].rolling(smooth, center=True, min_periods=1).mean()
    st.area_chart(profile, height=320)
    st.caption(f"共 {len(pts)} 个点，平滑窗口 {smooth}。窗口越大曲线越平缓，但会削掉小的起伏。")

    # 导出为 GeoJSON LineString
    feat = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": pick},
                "geometry": {"type": "LineString", "coordinates": [[p[1], p[0]] for p in pts]},
            }
        ],
    }
    st.download_button(
        "导出为 GeoJSON",
        json.dumps(feat, ensure_ascii=False).encode("utf-8"),
        file_name=f"{pick.rsplit('.', 1)[0]}.geojson",
        mime="application/geo+json",
    )


safe_run(main)
