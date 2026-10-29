"""徒步路线：湖南 / 广东路线库 + GPX 轨迹分析。

- 路线库：内置湘粤两省 30+ 条公开徒步路线，可按省份/难度/里程筛选，点开看详情
- GPX 分析：上传手表或手机导出的轨迹，自动算里程、爬升、高程剖面
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import folium
import leafmap.foliumap as leafmap
import pandas as pd
import streamlit as st

from app_utils import (
    BASEMAP_CHOICES,
    TILES,
    add_base_map,
    data_path,
    fmt_km,
    parse_gpx,
    safe_run,
    sidebar_common,
    track_stats,
)

DIFF_COLORS = {"入门": "#2e7d32", "较易": "#7cb342", "中等": "#f9a825", "较难": "#ef6c00", "难": "#c62828"}
LINE_COLORS = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#008080"]


def demo_track(lat0=30.2455, lon0=120.1440, n=260):
    """生成一条环湖示例轨迹（带起伏高程），仅用于演示。"""
    import math

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


@st.cache_data(show_spinner=False)
def load_routes():
    df = pd.read_csv(data_path("hiking_routes.csv"))
    for c in ("distance_km", "ascent_m", "lon", "lat"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# ---------------------------------------------------------------- 路线库
def tab_route_library(basemap):
    df = load_routes()

    st.markdown(
        "湖南、广东两省主要徒步路线（山岳古道、丹霞、海岸线、城市步道），"
        "先按条件和难度筛，再点开看细节。"
    )

    c1, c2, c3 = st.columns([1.1, 1, 1.4])
    with c1:
        provinces = st.multiselect("省份", ["湖南省", "广东省"], default=["湖南省", "广东省"])
    with c2:
        diffs = st.multiselect(
            "难度", ["入门", "较易", "中等", "较难", "难"], default=["入门", "较易", "中等", "较难", "难"]
        )
    with c3:
        km = st.slider(
            "里程区间（km）",
            float(df["distance_km"].min()),
            float(df["distance_km"].max()),
            (float(df["distance_km"].min()), float(df["distance_km"].max())),
        )

    view = df[
        df["province"].isin(provinces)
        & df["difficulty"].isin(diffs)
        & df["distance_km"].between(km[0], km[1])
    ].copy()

    if view.empty:
        st.warning("没有符合条件的路线，放宽一下筛选条件。")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("路线数", f"{len(view)} 条")
    m2.metric("平均里程", fmt_km(view["distance_km"].mean()))
    m3.metric("最长路线", f"{view.loc[view['distance_km'].idxmax(), 'name']}",
              delta=f"{view['distance_km'].max():.1f} km", delta_color="off")
    m4.metric("平均爬升", f"{view['ascent_m'].mean():.0f} m")

    left, right = st.columns([1.65, 1])

    with left:
        m = add_base_map(
            leafmap.Map(
                center=[view["lat"].mean(), view["lon"].mean()],
                zoom=6 if len(view) > 8 else 7,
                draw_control=False,
                tiles=None,
            ),
            basemap,
        )
        for _, r in view.iterrows():
            color = DIFF_COLORS.get(r["difficulty"], "#555555")
            folium.CircleMarker(
                location=[r["lat"], r["lon"]],
                radius=7,
                color="#ffffff",
                weight=1.5,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                popup=folium.Popup(
                    f"<b>{r['name']}</b><br>{r['province']}·{r['city']}<br>"
                    f"里程 {r['distance_km']} km｜爬升 {r['ascent_m']} m<br>难度 {r['difficulty']}｜{r['days']}<br>{r['desc']}",
                    max_width=280,
                ),
                tooltip=r["name"],
            ).add_to(m)
        m.to_streamlit(height=520)
        legend = "".join(
            "<span style='display:inline-flex;align-items:center;margin:2px 14px 2px 0;font-size:12px'>"
            f"<span style='width:11px;height:11px;border-radius:50%;background:{c};margin-right:5px;"
            "border:1px solid #fff;box-shadow:0 0 2px #999'></span>"
            f"{d}</span>"
            for d, c in DIFF_COLORS.items()
        )
        st.markdown(legend, unsafe_allow_html=True)
        st.caption("点圆点看详情。颜色代表难度，圆点大小一致。")

    with right:
        st.subheader("路线详情")
        picked = st.selectbox("选一条路线", view["name"].tolist())
        row = view[view["name"] == picked].iloc[0]
        st.markdown(f"#### {row['name']}")
        st.markdown(f"**{row['province']} · {row['city']}**　｜　{row['type']}")
        a, b = st.columns(2)
        a.metric("里程", f"{row['distance_km']} km")
        b.metric("累计爬升", f"{row['ascent_m']} m")
        a.metric("难度", row["difficulty"])
        b.metric("建议天数", row["days"])
        st.markdown(f"**最佳季节**：{row['best_season']}")
        st.markdown(row["desc"])
        st.code(f"{row['lat']:.4f}, {row['lon']:.4f}", language="text")
        st.caption("上面这行是可粘贴到高德/百度地图的坐标（纬度, 经度）。")

    st.markdown("---")
    st.subheader("全部路线")
    st.dataframe(
        view[
            ["name", "province", "city", "type", "distance_km", "ascent_m", "difficulty", "days", "best_season"]
        ].rename(
            columns={
                "name": "路线",
                "province": "省份",
                "city": "位置",
                "type": "类型",
                "distance_km": "里程(km)",
                "ascent_m": "爬升(m)",
                "difficulty": "难度",
                "days": "天数",
                "best_season": "季节",
            }
        ),
        use_container_width=True,
        height=380,
    )
    st.download_button(
        "导出这份路线清单（CSV）",
        view.to_csv(index=False).encode("utf-8-sig"),
        file_name="hiking_routes_hn_gd.csv",
        mime="text/csv",
    )
    st.caption(
        "⚠️ 里程与爬升是公开资料整理的**参考值**，不同来源口径不同（是否含往返、是否从山门起算），"
        "出发前请以官方公告和最新轨迹为准；坐标标注的是登山口/景区一带，非精确起点。"
    )


# ---------------------------------------------------------------- GPX 分析
def tab_gpx(basemap):
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
- 手表：Garmin / 华为 / 佳明 App 都能导出
- 手机：两步路、六只脚、户外助手、Strava 的「导出轨迹」
- 也可以先用轨迹记录类小程序录完再导出

**为什么用 GPX 而不是直接看地图？**
路书上的里程是估算，GPX 是你真实走过的每一秒，里程、爬升、配速都算得出来。
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
    m = add_base_map(leafmap.Map(center=[first[0], first[1]], zoom=13, draw_control=False, tiles=None), basemap)

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

    m.to_streamlit(height=520)

    st.markdown("---")
    st.subheader("轨迹汇总")
    st.dataframe(summary.drop(columns=["distance_km", "ascent_m"]), use_container_width=True)

    st.subheader("高程剖面")
    pick = st.selectbox("选择轨迹", list(tracks.keys()))
    pts = tracks[pick]
    km = cumulative_km(pts)
    ele = [p[2] if p[2] is not None else 0.0 for p in pts]
    profile = pd.DataFrame({"里程 (km)": km, "海拔 (m)": ele}).set_index("里程 (km)")
    smooth = st.slider("平滑窗口", 1, 25, 5)
    if smooth > 1:
        profile["海拔 (m)"] = profile["海拔 (m)"].rolling(smooth, center=True, min_periods=1).mean()
    st.area_chart(profile, height=320)
    st.caption(f"共 {len(pts)} 个点。窗口越大曲线越平缓，但会削掉小的起伏。")

    import json

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


def main():
    sidebar_common()
    st.title("🥾 徒步路线")
    st.caption("左边是湖南/广东的路线库，右边可以分析你自己手表导出的 GPX 轨迹。")

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 底图")
        basemap = st.selectbox("底图", BASEMAP_CHOICES, index=1, key="hike_base")
        st.caption("看山形用水影像，找路口用矢量。")

    tab1, tab2 = st.tabs(["📚 路线库（湖南 · 广东）", "📈 上传 GPX 分析"])
    with tab1:
        tab_route_library(basemap)
    with tab2:
        tab_gpx(basemap)


safe_run(main)
