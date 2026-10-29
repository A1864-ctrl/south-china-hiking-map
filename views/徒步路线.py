"""徒步轨迹：真实航迹 + 途经点 + 高程/速度剖面，也可导入自己的 GPX 入库。

两类轨迹共用一套 JSON 结构，靠 source 字段区分：
    planned —— 由 tools/build_tracks.py 按 OSM 路网规划（偏直、会绕公路）
    gpx     —— 用户导入的实测航迹（精度等于 GPS 采样）
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
import gpx_store

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
    up = stats.get("ascent_m")
    down = stats.get("descent_m")
    c1.metric("里程", f"{stats['distance_km']:.2f} km")
    c2.metric("累计爬升", f"{up:.0f} m" if up is not None else "—")
    c3.metric("累计下降", f"{down:.0f} m" if down is not None else "—")
    hi = f"{stats['ele_max']:.0f} m" if stats.get("ele_max") is not None else "—"
    c4.metric("最高海拔", hi)
    hours = (
        naismith_hours(stats["distance_km"], up)
        if up is not None
        else stats["distance_km"] / 4.5
    )
    c5.metric("预计耗时", f"{hours:.1f} 小时")


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

    work = work.copy()
    work["来源"] = (
        work["source"].map({"gpx": "🛰 实测", "planned": "🗺 规划"}).fillna("🗺 规划")
    )

    left, right = st.columns([1, 1.6], gap="large")

    with left:
        options = [
            f"{r['name']}｜{r['difficulty']}｜{r['distance_km']:g}km" for _, r in work.iterrows()
        ]
        pick = st.selectbox("选择路线", options, index=0)
        row = work.iloc[options.index(pick)]

        st.markdown("##### 路线列表")
        st.dataframe(
            work[
                ["name", "来源", "city_short", "difficulty", "distance_km", "ascent_m", "heat"]
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
        f"（每走 100 米上升 {grade:.0f} 米）。轨迹共 {len(track['points'])} 个坐标点。"
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

    if track.get("source") == "gpx":
        st.success(
            "**实测航迹：**这条线是导入的 GPX 记录，走位就是 GPS 当时打下的点，"
            f"精度等于采样本身。里程与爬升按原文件逐点重算（{track.get('built', '')} 入库）。",
            icon="🛰",
        )
    else:
        st.warning(
            "**这是规划路径，不是实测航迹。**途经点坐标取自 OpenStreetMap，路径由 Valhalla "
            f"步行路网规划（{track.get('built', '')} 构建），海拔取 SRTM 30 米。\n\n"
            "OSM 在华南山区步道覆盖很稀，规划器只能沿公路和村道走，所以线会偏直、会绕远，"
            "**达不到两步路那种一脚一脚的精度**。要精确走位，请到「上传 GPX」导入实测轨迹。",
            icon="⚠️",
        )


def imported_panel():
    """已导入的实测航迹列表 + 删除入口。"""
    rows = gpx_store.list_custom()
    st.markdown(f"##### 已导入的实测航迹（{len(rows)} 条）")
    if not rows:
        st.caption("还没有导入过。导入后会出现在这里，也会进「路线库」。")
        return
    df = pd.DataFrame(rows)[["name", "province", "city", "distance_km", "ascent_m"]]
    st.dataframe(
        df.rename(
            columns={
                "name": "路线",
                "province": "省份",
                "city": "城市",
                "distance_km": "里程",
                "ascent_m": "爬升",
            }
        ),
        hide_index=True,
    )
    with st.expander("删除已导入的路线"):
        pick = st.selectbox("选择路线", [r["name"] for r in rows], key="del_gpx_pick")
        if st.button("删除这条", key="del_gpx_btn"):
            tid = next(r["track_id"] for r in rows if r["name"] == pick)
            if gpx_store.delete_custom(tid):
                st.cache_data.clear()
                st.success(f"已删除「{pick}」")
                st.rerun()


def save_panel(filename: str, pts: list, wpts: list | None = None):
    """把刚上传的 GPX 正式存进路线库。"""
    st.markdown("#### 存进路线库")
    st.caption("存进去以后，它会和内置路线并列，来源标为「🛰 实测」。")
    default_name = os.path.splitext(os.path.basename(filename))[0]

    with st.form("save_gpx_form"):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("路线名", value=default_name)
        province = c2.text_input("省份", value="江西省")
        city = c3.text_input("城市", value="萍乡市")
        c4, c5, c6 = st.columns(3)
        rtype = c4.selectbox("类型", ["穿越", "往返", "环线", "登顶"], index=0)
        diff = c5.selectbox("难度", ["入门", "较易", "中等", "较难", "难"], index=2)
        days = c6.number_input("天数", min_value=1, max_value=15, value=1)
        c7, c8 = st.columns([1, 2])
        season = c7.text_input("最佳季节", value="春秋")
        desc = c8.text_input("一句话简介", value="")
        heat = st.slider("热度（决定列表排序）", 0, 100, 70)
        submitted = st.form_submit_button("保存到路线库", type="primary")

    if submitted:
        if not name.strip():
            st.error("路线名不能为空。")
            return
        meta = {
            "id": gpx_store.make_id(name),
            "name": name.strip(),
            "province": province.strip(),
            "city": city.strip(),
            "type": rtype,
            "difficulty": diff,
            "days": int(days),
            "best_season": season.strip(),
            "desc": desc.strip() or "用户导入的实测航迹。",
            "heat": int(heat),
            "waypoints": wpts or [],
        }
        doc = gpx_store.build_doc(pts, meta)
        gpx_store.save_doc(doc, meta)
        st.cache_data.clear()
        st.success(
            f"已保存「{meta['name']}」，保留 {len(doc['points'])} 个坐标点。"
            "切到「路线库」标签就能看到。"
        )


def tab_gpx():
    st.markdown(
        "上传 GPX 实测航迹，**存进路线库**——之后能像内置路线一样看轨迹、海拔剖面和速度曲线，"
        "而且走位是 GPS 真正打过的点。"
    )
    st.caption(
        "GPX 从哪来：两步路「我的 → 轨迹 → 导出 GPX」、高德「足迹 → 导出」、"
        "Garmin / Coros / Suunto 手表同步的原始文件都可以。"
    )

    up = st.file_uploader("选择 GPX 文件", type=["gpx", "xml"], accept_multiple_files=False)
    if up is None:
        imported_panel()
        return

    try:
        pts, wpts = parse_gpx(up.read(), up.name, with_waypoints=True)
    except Exception as exc:  # noqa: BLE001
        st.error(f"这个文件解析不出来：{exc}")
        return

    st.success(
        f"解析成功：{len(pts)} 个轨迹点"
        + (f"、{len(wpts)} 个命名路点" if wpts else "")
        + f"，来自 {up.name}"
    )

    basemap = st.selectbox("底图", BASEMAP_CHOICES, index=2, key="gpx_bm")
    stats = track_stats(pts)
    has_ele = stats.get("ele_max") is not None
    stat_cards(stats, [])

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        fake = {
            "name": up.name,
            "points": [[p[0], p[1], p[2] if p[2] is not None else 0, 0] for p in pts],
            "waypoints": [],
        }
        track_map(fake, basemap, color="#1e88e5", height=460, show_wp=False)

    with right:
        if has_ele:
            prof = track_profile(pts)
            st.markdown("#### 高程剖面")
            st.altair_chart(profile_chart(prof, height=430), use_container_width=True)
            km_at, grade = steepest_section(prof)
            st.caption(f"最陡一段在 **{km_at:.1f} km** 处，坡度约 **{grade:.0f}%**。")
        else:
            st.warning(
                "这个 GPX 没有 `<ele>` 高程标签，只能算里程，爬升和剖面画不出来。"
                "两步路导出的一般带高程，可以换一份再试。"
            )

    st.download_button(
        "导出为 GPX",
        track_to_gpx(pts, up.name.rsplit(".", 1)[0]).encode("utf-8"),
        file_name=f"{up.name.rsplit('.', 1)[0]}_标准化.gpx",
        mime="application/gpx+xml",
    )

    st.divider()
    save_panel(up.name, pts, wpts)


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
