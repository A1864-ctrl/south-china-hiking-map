"""景点搜索：输入地名，看这一片值得去哪、为什么值得去。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import folium
import streamlit as st

from app_utils import (
    BASEMAP_CHOICES,
    load_attractions,
    new_map,
    safe_run,
    show_map,
    sidebar_common,
)

# 类型 → 颜色（地图点用）
TYPE_COLORS = {
    "自然风光": "#2e7d32",
    "人文古迹": "#8d6e63",
    "主题乐园": "#ef6c00",
    "城市地标": "#1565c0",
    "城市公园": "#66bb6a",
    "山岳": "#1b5e20",
    "海岛海滨": "#00838f",
    "乡村田园": "#9ccc65",
    "街区古镇": "#6a1b9a",
}

LEVEL_BADGE = {"5A": "🟥 5A", "4A": "🟧 4A", "3A": "🟨 3A"}


def heat_bar(heat: int) -> str:
    """把热度画成一条小进度条。"""
    n = int(round(max(0, min(100, heat)) / 10))
    return "█" * n + "░" * (10 - n)


def main():
    sidebar_common()
    df = load_attractions()

    st.title("🔍 景点搜索")
    st.caption("输入地名（城市、区县、景点名或类型），看这个片区值得去哪些地方、为什么值得去。")

    # ---------------- 侧边栏筛选 ----------------
    with st.sidebar:
        st.markdown("### 筛选")
        provinces = st.multiselect("省份", sorted(df["province"].unique()), default=[])
        types = st.multiselect("类型", sorted(df["type"].unique()), default=[])
        min_heat = st.slider("最低热度", 50, 100, 50, step=5)
        basemap = st.selectbox("底图", BASEMAP_CHOICES, index=0)

    # ---------------- 搜索 ----------------
    if "search_q" not in st.session_state:
        st.session_state["search_q"] = ""

    st.text_input(
        "搜索地名或景点",
        key="search_q",
        placeholder="试试：潮州 / 张家界 / 海岛 / 丹霞山 / 南澳",
        label_visibility="collapsed",
    )
    search = st.session_state["search_q"]

    # 快捷城市
    hot_cities = (
        df.groupby("city")["heat"].sum().sort_values(ascending=False).head(8).index.tolist()
    )
    st.caption("热门城市快捷入口：")
    cols = st.columns(len(hot_cities))
    for i, city in enumerate(hot_cities):
        if cols[i].button(city, key=f"city_{city}", use_container_width=True):
            st.session_state["search_q"] = city
            st.rerun()

    # ---------------- 过滤 ----------------
    work = df.copy()
    if provinces:
        work = work[work["province"].isin(provinces)]
    if types:
        work = work[work["type"].isin(types)]
    work = work[work["heat"] >= min_heat]

    if search and search.strip():
        q = search.strip()
        mask = (
            work["name"].str.contains(q, na=False)
            | work["city"].str.contains(q, na=False)
            | work["district"].str.contains(q, na=False)
            | work["type"].str.contains(q, na=False)
            | work["best_season"].str.contains(q, na=False)
        )
        work = work[mask]

    if work.empty:
        st.warning("没有匹配的景点。换个更短的词试试，比如只输入城市名「郴州」。")
        return

    # ---------------- 地图 ----------------
    center = [float(work["lat"].mean()), float(work["lon"].mean())]
    n = len(work)
    zoom = 12 if n <= 2 else 10 if n <= 6 else 8 if n <= 20 else 7

    m = new_map(center=center, zoom=zoom, basemap=basemap)
    for _, r in work.iterrows():
        color = TYPE_COLORS.get(r["type"], "#607d8b")
        folium.CircleMarker(
            location=[r["lat"], r["lon"]],
            radius=5 + (float(r["heat"]) - 50) / 12,
            color="white",
            weight=1.2,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            tooltip=f"{r['name']}｜{r['city']}｜热度 {int(r['heat'])}",
            popup=f"<b>{r['name']}</b><br>{r['city']}{r['district']}<br>{r['level']} {r['type']}",
        ).add_to(m)
    show_map(m, height=430)

    legend = "　".join(
        f"<span style='color:{c};font-size:15px'>●</span>"
        f"<span style='font-size:12px'> {t}</span>"
        for t, c in TYPE_COLORS.items()
    )
    st.markdown(
        f"<div style='margin:-6px 0 10px'>{legend}"
        f"<span style='font-size:12px;color:#888'>　（圆点越大 = 热度越高）</span></div>",
        unsafe_allow_html=True,
    )

    # ---------------- 结果 ----------------
    st.markdown(f"#### 找到 **{len(work)}** 个景点")

    left, right = st.columns([1, 1.5], gap="large")

    with left:
        options = [
            f"{r['name']}（{r['city']}·热度{int(r['heat'])}）" for _, r in work.iterrows()
        ]
        pick = st.selectbox("选一个看详情", options, index=0)
        picked_name = pick.split("（")[0]
        row = work[work["name"] == picked_name].iloc[0]

        st.markdown("##### 热度前 10")
        top = work.sort_values("heat", ascending=False).head(10)[
            ["name", "city", "level", "heat"]
        ]
        st.dataframe(top, hide_index=True, height=380)

    with right:
        badge = LEVEL_BADGE.get(row["level"], row["level"])
        st.subheader(f"{row['name']}　{badge}")
        st.caption(f"{row['province']} · {row['city']} · {row['district']}　｜　{row['type']}")

        c1, c2, c3 = st.columns(3)
        c1.metric("热度指数", f"{int(row['heat'])}")
        c2.metric("门票", "免费" if float(row["ticket"]) == 0 else f"¥{int(row['ticket'])}")
        c3.metric("建议游玩", f"{row['recommend_hours']:g} 小时")

        st.markdown(f"**热度** `{heat_bar(int(row['heat']))}` {int(row['heat'])}/100")
        st.markdown(f"**最佳季节**：{row['best_season']}")

        st.markdown("##### 值得去的点")
        st.info(row["highlight"])

        # 同城其他景点
        same_city = df[(df["city"] == row["city"]) & (df["name"] != row["name"])].sort_values(
            "heat", ascending=False
        )
        if not same_city.empty:
            st.markdown(f"##### {row['city']}还有其他 {len(same_city)} 个")
            chips = "　".join(
                f"`{r['name']}`" for _, r in same_city.head(8).iterrows()
            )
            st.markdown(chips)

    st.divider()
    with st.expander("为什么这是我的推荐排序", expanded=False):
        st.markdown(
            "热度指数（0-100）综合了景区等级（5A/4A）、知名度、可达性（是否通高铁/靠近市区）、"
            "以及是否有独特不可替代的看点。它是**排序参考**，不是官方游客量统计。\n\n"
            "想按别的维度排？改 `data/attractions.csv` 里的 `heat` 列，或者在左列表格里自己排。"
        )
        st.download_button(
            "下载当前筛选结果 CSV",
            work.to_csv(index=False).encode("utf-8-sig"),
            file_name="景点筛选结果.csv",
            mime="text/csv",
        )


safe_run(main)
