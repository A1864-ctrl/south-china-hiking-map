"""城市热度榜：把景点和徒步路线按城市汇总，比出哪个城市更值得去。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import altair as alt
import folium
import pandas as pd
import streamlit as st

from app_utils import (
    BASEMAP_CHOICES,
    load_attractions,
    load_routes,
    new_map,
    safe_run,
    show_map,
    sidebar_common,
)


def norm_city(c) -> str:
    """统一城市名，让景点表和路线表能对上。

    景点表里 city 是「广州」「深圳」这种短名，
    路线表里是「深圳市大鹏新区」「衡阳市南岳区」这种带区县的全称，
    所以取「市」之前的部分做 key。
    """
    s = str(c)
    if "市" in s:
        s = s.split("市")[0]
    return s.strip()


def build_city_frame(prov: str):
    """按城市聚合景点与路线，算出综合热度。"""
    df_a = load_attractions()
    df_r = load_routes()
    df_r["city_key"] = df_r["city"].map(norm_city)
    df_a["city_key"] = df_a["city"].map(norm_city)

    if prov != "全部":
        df_a = df_a[df_a["province"] == prov]
        df_r = df_r[df_r["province"] == prov]

    ga = df_a.groupby("city_key").agg(
        景点数=("name", "size"),
        景点热度=("heat", "mean"),
        最高景点热度=("heat", "max"),
        省份=("province", "first"),
        中心纬=("lat", "mean"),
        中心经=("lon", "mean"),
    )
    gr = df_r.groupby("city_key").agg(
        徒步路线数=("name", "size"),
        路线热度=("heat", "mean"),
        最长路线=("distance_km", "max"),
    )

    city = ga.join(gr, how="outer")
    city["景点数"] = city["景点数"].fillna(0).astype(int)
    city["徒步路线数"] = city["徒步路线数"].fillna(0).astype(int)
    city["景点热度"] = city["景点热度"].fillna(0.0)
    city["路线热度"] = city["路线热度"].fillna(0.0)
    city["最高景点热度"] = city["最高景点热度"].fillna(0.0)
    city["最长路线"] = city["最长路线"].fillna(0.0)

    # 规模分：景点和路线越多越高，封顶 100
    city["规模分"] = (city["景点数"] * 6 + city["徒步路线数"] * 10).clip(upper=100)

    # 综合热度：景点占一半，规模占三成，路线占两成
    city["综合热度"] = (
        city["景点热度"] * 0.5 + city["规模分"] * 0.3 + city["路线热度"] * 0.2
    ).round(1)

    return city.sort_values("综合热度", ascending=False).reset_index()


def main():
    sidebar_common()
    st.title("🔥 城市热度榜")
    st.caption("把景点和徒步路线按城市汇总，看看哪个城市更值得排进行程。")

    with st.sidebar:
        st.markdown("### 筛选")
        all_prov = sorted(set(load_attractions()["province"]) | set(load_routes()["province"]))
        prov = st.radio("省份", ["全部"] + all_prov, index=0)
        basemap = st.selectbox("底图", BASEMAP_CHOICES, index=0)
        top_n = st.slider("榜单显示条数", 5, 30, 15)

    city = build_city_frame(prov)

    # ---------------- 总览 ----------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("城市数", f"{len(city)} 个")
    c2.metric("景点最多的城市", f"{city.loc[city['景点数'].idxmax(), 'city_key']}")
    c3.metric("综合热度最高", f"{city.loc[city['综合热度'].idxmax(), 'city_key']}")
    c4.metric(
        "徒步氛围最浓",
        f"{city.loc[city['徒步路线数'].idxmax(), 'city_key']}（{int(city['徒步路线数'].max())} 条）",
    )

    # ---------------- 榜单 ----------------
    st.markdown(f"#### 综合热度 Top {top_n}")
    top = city.head(top_n)

    bars = (
        alt.Chart(top)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X("综合热度:Q", title="综合热度指数（0-100）", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("city_key:N", title="", sort="-x"),
            color=alt.Color(
                "综合热度:Q",
                scale=alt.Scale(scheme="orangered"),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("city_key:N", title="城市"),
                alt.Tooltip("综合热度:Q", title="综合热度", format=".1f"),
                alt.Tooltip("景点数:Q", title="景点数"),
                alt.Tooltip("景点热度:Q", title="平均景点热度", format=".1f"),
                alt.Tooltip("徒步路线数:Q", title="徒步路线数"),
                alt.Tooltip("路线热度:Q", title="平均路线热度", format=".1f"),
            ],
        )
        .properties(height=max(240, len(top) * 26))
    )
    st.altair_chart(bars, use_container_width=True)

    # ---------------- 两个维度对比 ----------------
    st.markdown("#### 玩法对比：观光 vs 徒步")
    st.caption("右下角是「景点多、徒步路线也多」的全能城市；贴近横轴说明可徒步路线偏少。")

    scatter_df = city[(city["景点数"] > 0) & (city["徒步路线数"] > 0)]
    if not scatter_df.empty:
        scatter = (
            alt.Chart(scatter_df)
            .mark_circle(opacity=0.75, stroke="white", strokeWidth=1)
            .encode(
                x=alt.X("景点热度:Q", title="平均景点热度", scale=alt.Scale(zero=False)),
                y=alt.Y("路线热度:Q", title="平均徒步路线热度", scale=alt.Scale(zero=False)),
                size=alt.Size("景点数:Q", title="景点数", scale=alt.Scale(range=[80, 900])),
                color=alt.Color("综合热度:Q", scale=alt.Scale(scheme="orangered"), legend=None),
                tooltip=[
                    alt.Tooltip("city_key:N", title="城市"),
                    alt.Tooltip("景点数:Q", title="景点数"),
                    alt.Tooltip("景点热度:Q", title="平均景点热度", format=".1f"),
                    alt.Tooltip("徒步路线数:Q", title="路线数"),
                    alt.Tooltip("路线热度:Q", title="平均路线热度", format=".1f"),
                ],
            )
            .properties(height=340)
        )
        st.altair_chart(scatter, use_container_width=True)
    else:
        st.info("当前筛选下，没有同时具备景点和徒步路线的城市。")

    # ---------------- 地图 ----------------
    st.markdown("#### 热度地图")
    st.caption("圆点大小和颜色都对应综合热度。点圆点看城市明细。")
    geo = city.dropna(subset=["中心纬", "中心经"])
    if not geo.empty:
        m = new_map(
            center=[float(geo["中心纬"].mean()), float(geo["中心经"].mean())],
            zoom=6 if prov == "全部" else 7,
            basemap=basemap,
        )
        for _, r in geo.iterrows():
            heat = float(r["综合热度"])
            color = "#b71c1c" if heat >= 70 else "#e53935" if heat >= 55 else "#fb8c00" if heat >= 40 else "#fdd835"
            folium.CircleMarker(
                location=[r["中心纬"], r["中心经"]],
                radius=6 + heat / 8,
                color="white",
                weight=1.2,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                tooltip=f"{r['city_key']}｜综合 {heat:.0f}｜景点 {int(r['景点数'])} · 路线 {int(r['徒步路线数'])}",
                popup=(
                    f"<b>{r['city_key']}</b><br>"
                    f"综合热度：{heat:.1f}<br>"
                    f"景点 {int(r['景点数'])} 个，平均热度 {r['景点热度']:.0f}<br>"
                    f"徒步路线 {int(r['徒步路线数'])} 条，平均热度 {r['路线热度']:.0f}"
                ),
            ).add_to(m)
        show_map(m, height=440)

    # ---------------- 明细表 ----------------
    st.markdown("#### 明细数据")
    table = city[
        ["city_key", "省份", "景点数", "景点热度", "最高景点热度", "徒步路线数", "路线热度", "最长路线", "综合热度"]
    ].rename(
        columns={
            "city_key": "城市",
            "景点热度": "平均景点热度",
            "最高景点热度": "最高景点热度",
            "路线热度": "平均路线热度",
            "最长路线": "最长路线(km)",
        }
    )
    st.dataframe(
        table.style.format(
            {
                "平均景点热度": "{:.0f}",
                "最高景点热度": "{:.0f}",
                "平均路线热度": "{:.0f}",
                "最长路线(km)": "{:.1f}",
                "综合热度": "{:.1f}",
            }
        ),
        hide_index=True,
        height=420,
    )

    st.download_button(
        "下载这份榜单 CSV",
        table.to_csv(index=False).encode("utf-8-sig"),
        file_name="城市热度榜.csv",
        mime="text/csv",
    )

    with st.expander("热度指数是怎么算的", expanded=False):
        st.markdown(
            """
**综合热度 = 平均景点热度 × 0.5 + 规模分 × 0.3 + 平均路线热度 × 0.2**

- **平均景点热度**：该城市所有景点的 `heat` 均值（0-100）
- **规模分**：`min(100, 景点数 × 6 + 徒步路线数 × 10)`，反映这个城市有多少地方可去
- **平均路线热度**：该城市徒步路线的 `heat` 均值，没有路线就是 0

为什么这么配：先看这城市有没有好景点（权重最大），再看可玩的总量（规模），
最后看徒步资源。一个只有 1 个 5A 但什么配套都没有的城市，不该排在
「有 8 个景点 + 5 条徒步线」的城市前面。

**这些数字不是游客量统计**，是根据景区等级、知名度、可达性做的估算指数，
用于横向排序参考。
"""
        )


safe_run(main)
