"""徒步路线：轨迹线 + 高程剖面 + 里程爬升统计，也可上传自己的 GPX。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import altair as alt
import folium
import pandas as pd
import streamlit as st

from app_utils import (
    BASEMAP_CHOICES,
    gen_track,
    load_routes,
    new_map,
    parse_gpx,
    safe_run,
    show_map,
    sidebar_common,
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


def difficulty_badge(d: str) -> str:
    color = "green" if d in ("入门", "较易") else "orange" if d == "中等" else "red"
    return f":{color}[**{d}**]"


def naismith_hours(distance_km: float, ascent_m: float) -> float:
    """奈史密斯规则估算耗时：平路 4.5km/h，爬升每 600m 加 1 小时。"""
    return distance_km / 4.5 + ascent_m / 600.0


def track_map(pts, basemap, color="#e53935", height=460):
    """把轨迹画到地图上：线 + 绿色起点 + 红色终点。"""
    lats = [p[0] for p in pts]
    lons = [p[1] for p in pts]
    span = max(max(lats) - min(lats), max(lons) - min(lons))
    zoom = 14 if span < 0.02 else 13 if span < 0.05 else 12 if span < 0.12 else 11
    center = [(max(lats) + min(lats)) / 2, (max(lons) + min(lons)) / 2]

    m = new_map(center=center, zoom=zoom, basemap=basemap)
    folium.PolyLine(
        locations=[[p[0], p[1]] for p in pts],
        color=color,
        weight=4,
        opacity=0.9,
        tooltip="轨迹",
    ).add_to(m)
    folium.Marker(
        location=[pts[0][0], pts[0][1]],
        icon=folium.Icon(color="green", icon="play", prefix="fa"),
        tooltip="起点",
    ).add_to(m)
    folium.Marker(
        location=[pts[-1][0], pts[-1][1]],
        icon=folium.Icon(color="red", icon="flag-checkered", prefix="fa"),
        tooltip="终点",
    ).add_to(m)
    show_map(m, height=height)


def profile_chart(prof, height=240):
    """高程剖面图（两步路那种面积图）。prof = [(km, ele), ...]"""
    df = pd.DataFrame(prof, columns=["km", "ele"])
    base = alt.Chart(df).encode(
        x=alt.X("km:Q", title="距离 (km)", axis=alt.Axis(format=".1f")),
        y=alt.Y("ele:Q", title="海拔 (m)", scale=alt.Scale(zero=False)),
        tooltip=[
            alt.Tooltip("km:Q", title="距离", format=".2f"),
            alt.Tooltip("ele:Q", title="海拔", format=".0f"),
        ],
    )
    area = base.mark_area(
        line={"color": "#d32f2f", "strokeWidth": 2},
        color="#ef9a9a",
        opacity=0.45,
    )
    return area.properties(height=height).interactive(bind_y=False)


def steepest_section(pts):
    """找最陡的一段，返回 (起点 km, 坡度%)。"""
    prof = track_profile(pts)
    best = (0.0, 0.0)
    for (k1, e1), (k2, e2) in zip(prof, prof[1:]):
        dk = k2 - k1
        if dk < 0.05:  # 至少 50 米才统计，避免噪声
            continue
        grade = (e2 - e1) / (dk * 1000.0) * 100.0
        if grade > best[1]:
            best = (k1, grade)
    return best


def stat_cards(stats):
    """五个指标卡。参数名别用 st，会把 streamlit 模块遮蔽掉。"""
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("里程", f"{stats['distance_km']:.1f} km")
    c2.metric("累计爬升", f"{stats['ascent_m']:.0f} m")
    c3.metric("累计下降", f"{stats['descent_m']:.0f} m")
    hi = f"{stats['ele_max']:.0f} m" if stats["ele_max"] is not None else "—"
    c4.metric("最高海拔", hi)
    c5.metric("预计耗时", f"{naismith_hours(stats['distance_km'], stats['ascent_m']):.1f} 小时")


def tab_library():
    df = load_routes()
    # 城市名统一取「市」之前的部分：「深圳市大鹏新区」→「深圳」，和景点表一致
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
        basemap = st.selectbox("底图", ["高德矢量", "高德影像", "高德影像 + 注记"], index=1)

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
            f"{r['name']}｜{r['difficulty']}｜{r['distance_km']:g}km"
            for _, r in work.iterrows()
        ]
        pick = st.selectbox("选择路线", options, index=0)
        row = work.iloc[options.index(pick)]

        st.markdown("##### 路线列表")
        st.dataframe(
            work[
                ["name", "city_short", "difficulty", "distance_km", "ascent_m", "heat"]
            ].rename(
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

    pts = gen_track(
        row["name"],
        float(row["lat"]),
        float(row["lon"]),
        float(row["distance_km"]),
        float(row["ascent_m"]),
    )

    with right:
        st.subheader(row["name"])
        st.caption(
            f"{row['province']} · {row['city']}　｜　{row['type']}　｜　"
            f"{row['days']}　｜　最佳季节 {row['best_season']}"
        )
        st.markdown(
            f"**难度** {difficulty_badge(row['difficulty'])}　　"
            f"**热度** {int(row['heat'])}/100"
        )
        st.markdown(row["desc"])
        track_map(pts, basemap, color=DIFF_COLORS.get(row["difficulty"], "#e53935"))

    st.divider()
    st.markdown("#### 路线数据")
    stat_cards(track_stats(pts))

    km_at, grade = steepest_section(pts)
    st.caption(
        f"最陡一段出现在 **{km_at:.1f} km** 处，坡度约 **{grade:.0f}%**"
        f"（{grade:.0f}% ≈ 每走 100 米上升 {grade:.0f} 米）"
    )

    st.markdown("#### 高程剖面")
    st.caption("横轴累计距离，纵轴海拔。曲线陡的地方就是爬升段，平的地方是缓坡或平路。")
    st.altair_chart(profile_chart(track_profile(pts)), use_container_width=True)

    st.download_button(
        "下载这条轨迹的 GPX（可导入两步路 / 户外助手）",
        track_to_gpx(pts, row["name"]).encode("utf-8"),
        file_name=f"{row['name']}.gpx",
        mime="application/gpx+xml",
    )

    st.warning(
        "轨迹是**按标称里程和爬升自动生成的示意线**，不是实测航迹。"
        "里程、爬升、海拔剖面与标称值一致，但具体走位与实际路网有偏差，**不能用来导航**。"
        "要真实轨迹请用「上传 GPX 分析」标签页。",
        icon="⚠️",
    )


def tab_gpx():
    st.markdown(
        "上传你自己记录或下载的 GPX，这里会用**真实轨迹点**重新计算里程、爬升和剖面。"
    )
    up = st.file_uploader("选择 GPX 文件", type=["gpx", "xml"], accept_multiple_files=False)

    if up is None:
        st.info(
            "没有 GPX？两步路、户外助手、Garmin、Strava 都能导出 GPX。"
            "也可以先去「路线库」下载一份示意轨迹，看看格式。"
        )
        return

    try:
        pts = parse_gpx(up.read(), up.name)
    except Exception as exc:  # noqa: BLE001
        st.error(f"这个文件解析不出来：{exc}")
        return

    st.success(f"解析成功：{len(pts)} 个轨迹点，来自 {up.name}")

    basemap = st.selectbox("底图", BASEMAP_CHOICES, index=1, key="gpx_bm")
    stat_cards(track_stats(pts))

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        track_map(pts, basemap, color="#1e88e5")
    with right:
        st.markdown("#### 高程剖面")
        st.altair_chart(
            profile_chart(track_profile(pts), height=380), use_container_width=True
        )

    km_at, grade = steepest_section(pts)
    st.caption(f"最陡一段在 **{km_at:.1f} km** 处，坡度约 **{grade:.0f}%**。")

    st.download_button(
        "导出为 GPX",
        track_to_gpx(pts, up.name.rsplit(".", 1)[0]).encode("utf-8"),
        file_name=f"{up.name.rsplit('.', 1)[0]}_标准化.gpx",
        mime="application/gpx+xml",
    )


def main():
    sidebar_common()
    st.title("🥾 徒步路线")
    st.caption("轨迹线、高程剖面、里程爬升——挑线之前先看清这条路长什么样。")

    tab1, tab2 = st.tabs(["📚 路线库（湘粤 31 条）", "📤 上传 GPX 分析"])
    with tab1:
        tab_library()
    with tab2:
        tab_gpx()


safe_run(main)
