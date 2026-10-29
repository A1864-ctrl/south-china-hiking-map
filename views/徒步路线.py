"""徒步轨迹：贴合真实路网的轨迹线 + 途经点 + 高程/速度剖面，也可上传自己的 GPX。

轨迹数据来自 data/tracks/*.json，由 tools/build_tracks.py 一次性构建：
途经点按 OSM 官方坐标定位 → OSRM 步行路网规划 → SRTM 30m 取真实海拔。
运行时不联网，所以页面不会因为外部接口挂掉而白屏。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import altair as alt
import folium
import pandas as pd
import streamlit as st

from app_utils import (
    BASEMAP_CHOICES,
    load_routes,
    load_track,
    new_map,
    parse_gpx,
    safe_run,
    show_map,
    sidebar_common,
    track_points,
    track_profile,
    track_stats,
    track_to_gpx,
)

DIFF_COLORS = {
    "入门": "#43a047",
    "较易": "#7cb342",
    "中等": "#fbc02d",
    "较难": "#f57c00",
    "难": "#e53935",
}

TRACK_COLOR = "#ff6d00"


def naismith_hours(distance_km: float, ascent_m: float) -> float:
    """奈史密斯规则估算耗时：平路 4.5km/h，爬升每 600m 加 1 小时。"""
    return distance_km / 4.5 + ascent_m / 600.0


def waypoint_icon(idx: int, total: int) -> folium.DivIcon:
    """两步路那种带编号的标注点。起点绿、终点红、中间橙。"""
    if idx == 0:
        bg, txt = "#2e7d32", "起"
    elif idx == total - 1:
        bg, txt = "#c62828", "终"
    else:
        bg, txt = "#ef6c00", str(idx)
    return folium.DivIcon(
        icon_size=(26, 26),
        icon_anchor=(13, 13),
        html=(
            f"<div style='background:{bg};color:#fff;border:2px solid #fff;border-radius:50%;"
            f"width:22px;height:22px;line-height:18px;text-align:center;font-size:12px;"
            f"font-weight:700;box-shadow:0 1px 4px rgba(0,0,0,.45)'>{txt}</div>"
        ),
    )


def track_map(track, basemap, color=TRACK_COLOR, height=520, show_wp=True):
    """轨迹地图：贴合路网的折线 + 编号途经点 + 起终点。"""
    pts = track["points"]
    lats = [p[0] for p in pts]
    lons = [p[1] for p in pts]
    span = max(max(lats) - min(lats), max(lons) - min(lons))
    zoom = 15 if span < 0.01 else 14 if span < 0.03 else 13 if span < 0.07 else 12 if span < 0.15 else 11
    center = [(max(lats) + min(lats)) / 2, (max(lons) + min(lons)) / 2]

    m = new_map(center=center, zoom=zoom, basemap=basemap)

    # 轨迹线：先画一层宽的半透明做描边，再画细的实线，视觉上更像 GPS 轨迹
    line = [[p[0], p[1]] for p in pts]
    folium.PolyLine(line, color="#ffffff", weight=8, opacity=0.55).add_to(m)
    folium.PolyLine(
        line,
        color=color,
        weight=4,
        opacity=0.95,
        tooltip=f"{track['name']}　{track['stats']['distance_km']:.1f} km",
    ).add_to(m)

    if show_wp:
        wps = track.get("waypoints") or []
        for i, w in enumerate(wps):
            folium.Marker(
                location=[w["lat"], w["lon"]],
                icon=waypoint_icon(i, len(wps)),
                tooltip=f"{w['name']}　{w['km']:.1f} km　{w['ele']:.0f} m",
                popup=(
                    f"<b>{w['name']}</b><br>里程 {w['km']:.2f} km<br>"
                    f"海拔 {w['ele']:.0f} m<br>"
                    f"<a href='https://uri.amap.com/marker?position={w['lon']},{w['lat']}' "
                    f"target='_blank'>在高德地图打开</a>"
                ),
            ).add_to(m)

    show_map(m, height=height)


def profile_chart(prof, height=230):
    """高程剖面（两步路那种红色面积图）。prof = [(km, ele), ...]"""
    df = pd.DataFrame(prof, columns=["km", "ele"])
    base = alt.Chart(df).encode(
        x=alt.X("km:Q", title="距离 (km)", axis=alt.Axis(format=".1f", tickCount=12)),
        y=alt.Y("ele:Q", title="海拔 (m)", scale=alt.Scale(zero=False)),
        tooltip=[
            alt.Tooltip("km:Q", title="距离", format=".2f"),
            alt.Tooltip("ele:Q", title="海拔", format=".0f"),
        ],
    )
    area = base.mark_area(line={"color": "#d32f2f", "strokeWidth": 2.2}, color="#ef9a9a", opacity=0.5)
    return area.properties(height=height).interactive(bind_y=False)


def speed_chart(speed, height=150):
    """速度—距离曲线。速度由坡度 + Tobler 徒步函数推算，解释见下方说明。"""
    if not speed:
        return None
    df = pd.DataFrame(speed, columns=["km", "v"])
    base = alt.Chart(df).encode(
        x=alt.X("km:Q", title="距离 (km)", axis=alt.Axis(format=".1f", tickCount=12)),
        y=alt.Y("v:Q", title="速度 (km/h)", scale=alt.Scale(zero=False)),
        tooltip=[
            alt.Tooltip("km:Q", title="距离", format=".2f"),
            alt.Tooltip("v:Q", title="速度", format=".2f"),
        ],
    )
    return base.mark_line(color="#1565c0", strokeWidth=1.6).properties(height=height)


def steepest_section(prof_pts):
    """找最陡的一段，返回 (起点 km, 坡度%)。prof_pts = [(km, ele), ...]"""
    best = (0.0, 0.0)
    for (k1, e1), (k2, e2) in zip(prof_pts, prof_pts[1:]):
        dk = k2 - k1
        if dk < 0.04:  # 至少 40 米才统计，避免噪声
            continue
        grade = (e2 - e1) / (dk * 1000.0) * 100.0
        if grade > best[1]:
            best = (k1, grade)
    return best


def stat_cards(stats, prof_pts):
    """指标卡。参数名别用 st，会把 streamlit 模块遮蔽掉。"""
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("里程", f"{stats['distance_km']:.2f} km")
    c2.metric("累计爬升", f"{stats['ascent_m']:.0f} m")
    c3.metric("累计下降", f"{stats['descent_m']:.0f} m")
    hi = f"{stats['ele_max']:.0f} m" if stats.get("ele_max") is not None else "—"
    c4.metric("最高海拔", hi)
    c5.metric("预计耗时", f"{naismith_hours(stats['distance_km'], stats['ascent_m']):.1f} 小时")


def waypoint_table(track):
    wps = track.get("waypoints") or []
    if not wps:
        return
    df = pd.DataFrame(
        [
            {
                "序号": "起" if i == 0 else ("终" if i == len(wps) - 1 else str(i + 1)),
                "途经点": w["name"],
                "里程 (km)": round(w["km"], 2),
                "海拔 (m)": round(w["ele"]),
            }
            for i, w in enumerate(wps)
        ]
    )
    st.markdown("##### 途经点")
    st.dataframe(df, hide_index=True, use_container_width=True)


def tab_library():
    df = load_routes()
    df["city_short"] = df["city"].astype(str).str.split("市").str[0]

    with st.sidebar:
        st.markdown("### 筛选路线")
        prov = st.multiselect("省份", sorted(df["province"].unique()), default=[])
        cities = st.multiselect("城市", sorted(df["city_short"].unique()), default=[])
        diffs = st.multiselect("难度", ["入门", "较易", "中等", "较难", "难"], default=[])
        km_range = st.slider(
            "里程区间 (km)",
            float(df["distance_km"].min()),
            float(df["distance_km"].max()),
            (float(df["distance_km"].min()), float(df["distance_km"].max())),
        )
        show_wp = st.checkbox("显示途经点标注", value=True)
        basemap = st.selectbox("底图", BASEMAP_CHOICES, index=2)

    work = df.copy()
    if prov:
        work = work[work["province"].isin(prov)]
    if cities:
        work = work[work["city_short"].isin(cities)]
    if diffs:
        work = work[work["difficulty"].isin(diffs)]
    work = work[
        (work["distance_km"] >= km_range[0]) & (work["distance_km"] <= km_range[1])
    ].sort_values("heat", ascending=False)

    if work.empty:
        st.warning("没有符合条件的路线，放宽一下筛选条件。")
        return

    st.markdown(f"共 **{len(work)}** 条路线，按热度排序。")

    left, right = st.columns([1, 1.6], gap="large")

    with left:
        options = [
            f"{r['name']}｜{r['difficulty']}｜{r['distance_km']:g}km" for _, r in work.iterrows()
        ]
        pick = st.selectbox("选择路线", options, index=0)
        row = work.iloc[options.index(pick)]

        st.markdown("##### 路线列表")
        st.dataframe(
            work[["name", "city_short", "difficulty", "distance_km", "ascent_m", "heat"]].rename(
                columns={
                    "name": "路线",
                    "city_short": "城市",
                    "difficulty": "难度",
                    "distance_km": "里程",
                    "ascent_m": "爬升",
                    "heat": "热度",
                }
            ),
            hide_index=True,
            height=330,
        )

    track = load_track(str(row["track_id"]))

    with right:
        st.subheader(row["name"])
        st.caption(
            f"{row['province']} · {row['city']}　｜　{row['type']}　｜　"
            f"{row['days']}　｜　最佳季节 {row['best_season']}"
        )
        st.markdown(f"**难度** {row['difficulty']}　　**热度** {int(row['heat'])}/100")
        st.markdown(row["desc"])
        if track is None:
            st.warning("这条路线的轨迹文件还没生成，先看文字说明。")
        else:
            track_map(track, basemap, show_wp=show_wp)

    if track is None:
        return

    pts = track_points(track)
    prof = track_profile(pts)

    st.divider()
    st.markdown("#### 路线数据")
    stat_cards(track["stats"], prof)

    km_at, grade = steepest_section(prof)
    st.caption(
        f"最陡一段出现在 **{km_at:.1f} km** 处，坡度约 **{grade:.0f}%**"
        f"（每走 100 米上升 {grade:.0f} 米）。轨迹共 {len(track['points'])} 个坐标点，"
        f"每个点都落在实际道路上。"
    )

    col_a, col_b = st.columns([2.1, 1], gap="large")
    with col_a:
        st.markdown("#### 高程剖面")
        st.caption("横轴累计里程，纵轴海拔。陡升段就是爬坡，长平台是山脊或平路。")
        st.altair_chart(profile_chart(prof), use_container_width=True)
    with col_b:
        st.markdown("#### 速度曲线")
        st.caption("按坡度推算的步行速度：平路最快，上坡减速，陡降也减速。")
        sc = speed_chart(track.get("speed"))
        if sc is not None:
            st.altair_chart(sc, use_container_width=True)

    waypoint_table(track)

    st.download_button(
        "下载这条轨迹的 GPX（可导入两步路 / 高德 / 户外助手）",
        track_to_gpx(pts, track["name"]).encode("utf-8"),
        file_name=f"{row['name']}.gpx",
        mime="application/gpx+xml",
    )

    st.info(
        "**轨迹怎么来的：**途经点坐标取自 OpenStreetMap 官方数据，路径用 Valhalla 步行路网规划"
        f"（{track.get('built', '')} 构建），海拔取 SRTM 30 米高程，每 45 米取一个高程点。"
        "所以线是贴着真实道路和山径走的，不是两点直连。"
        "但 OSM 在部分山区步道覆盖不全，走位仍可能与现场有偏差，**导航请以现场路标和官方轨迹为准**。",
        icon="ℹ️",
    )


def tab_gpx():
    st.markdown("上传你自己记录或下载的 GPX，用**真实轨迹点**重算里程、爬升和剖面。")
    up = st.file_uploader("选择 GPX 文件", type=["gpx", "xml"], accept_multiple_files=False)

    if up is None:
        st.info(
            "没有 GPX？两步路、户外助手、Garmin、Strava 都能导出。"
            "也可以先在「路线库」下载一份，看看格式。"
        )
        return

    try:
        pts = parse_gpx(up.read(), up.name)
    except Exception as exc:  # noqa: BLE001
        st.error(f"这个文件解析不出来：{exc}")
        return

    st.success(f"解析成功：{len(pts)} 个轨迹点，来自 {up.name}")

    basemap = st.selectbox("底图", BASEMAP_CHOICES, index=2, key="gpx_bm")
    stats = track_stats(pts)
    prof = track_profile(pts)
    stat_cards(stats, prof)

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        fake = {"name": up.name, "points": [[p[0], p[1], p[2] or 0, 0] for p in pts], "waypoints": []}
        track_map(fake, basemap, color="#1e88e5", height=460, show_wp=False)
    with right:
        st.markdown("#### 高程剖面")
        st.altair_chart(profile_chart(prof, height=430), use_container_width=True)

    km_at, grade = steepest_section(prof)
    st.caption(f"最陡一段在 **{km_at:.1f} km** 处，坡度约 **{grade:.0f}%**。")

    st.download_button(
        "导出为 GPX",
        track_to_gpx(pts, up.name.rsplit(".", 1)[0]).encode("utf-8"),
        file_name=f"{up.name.rsplit('.', 1)[0]}_标准化.gpx",
        mime="application/gpx+xml",
    )


def main():
    sidebar_common()
    st.title("🥾 徒步轨迹")
    st.caption(
        "轨迹贴着真实道路和山径走，带途经点、高程剖面和速度曲线——出发前先看清这条路长什么样。"
    )

    df = load_routes()
    n_prov = df["province"].nunique()
    tab1, tab2 = st.tabs(
        [f"📚 路线库（{n_prov} 省 · {len(df)} 条）", "📤 上传 GPX 分析"]
    )
    with tab1:
        tab_library()
    with tab2:
        tab_gpx()


safe_run(main)
