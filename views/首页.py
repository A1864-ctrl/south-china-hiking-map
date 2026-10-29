"""首页：说明这个站点是干什么的、怎么用。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from app_utils import load_attractions, load_routes, sidebar_common


def main():
    sidebar_common()

    st.title("🗺️ 湘粤赣桂旅游与徒步地图")
    st.caption("广东 · 湖南 · 江西 · 广西桂林 ｜ 找景点、看徒步轨迹、看城市热度")

    st.markdown("这个站点回答三个问题：")
    st.markdown(
        "① **去某个地方玩，那里有什么值得去的？** —— 输入地名看推荐和理由\n\n"
        "② **这条徒步路线贴着哪条路走、中间经过哪里、走起来多累？** —— 看轨迹线、途经点、高程剖面\n\n"
        "③ **哪个城市更值得排进行程？** —— 看城市热度榜"
    )

    df_a = load_attractions()
    df_r = load_routes()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("景点", f"{len(df_a)} 个")
    c2.metric("徒步路线", f"{len(df_r)} 条")
    c3.metric("覆盖省市", f"{df_r['province'].nunique()} 省 / {df_a['city'].nunique()} 市")
    c4.metric("轨迹坐标点", f"{int(df_r['n_points'].sum()):,} 个")

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1, st.container(border=True):
        st.subheader("🔍 景点搜索")
        st.markdown(
            "输入「潮州」「张家界」「丹霞山」这类地名或景点名，"
            "列出这一片的推荐景点，每个都写清**值得去的点**、门票、"
            "建议玩多久、什么季节去最好。"
        )
        st.caption("适合：出行前排行程、到了当地临时找地方")

    with col2, st.container(border=True):
        st.subheader("🥾 徒步轨迹")
        st.markdown(
            "选一条路线，地图上画出**贴着真实道路和山径**的轨迹线，"
            "沿途标出途经点（第几个点、多少公里、海拔多少），"
            "下方给高程剖面和速度曲线。可导出 GPX，也能上传自己的 GPX 分析。"
        )
        st.caption("适合：挑线、评估体力、复盘走过的路")

    with col3, st.container(border=True):
        st.subheader("🔥 城市热度")
        st.markdown(
            "按城市汇总：景点数量、平均热度、徒步路线数，"
            "算一个综合热度指数，横向比出哪个城市更值得去。"
        )
        st.caption("适合：决定先玩哪个城市")

    st.divider()

    with st.expander("轨迹是怎么做出来的（这点最关键，请看）", expanded=True):
        st.markdown(
            """
**三步生成，每一步都用真实数据：**

1. **定位途经点** —— 用 OpenStreetMap 的官方坐标确定登山口、寺庙、峰顶等点位
   （峰顶还带官方海拔，比如祝融峰 1290 m、金顶 1918 m）。
2. **规划路径** —— 用 Valhalla 步行路由在这些点之间找**真实存在的道路和步道**，
   返回的是几百到上千个坐标点连成的折线，不是两点直连。
   （试过 OSRM，它在衡山这类景区把祖师殿到高台寺——直线 500 米——绕成 55 公里，
   因为 OSM 里那两段步道没连通；Valhalla 给的是 1.24 公里，与实际相符。）
3. **取海拔** —— 沿轨迹每 45 米取一次 SRTM 30 米高程，算出真实爬升、下降和剖面。

所以轨迹是**贴着实路走的**，能看出盘山路、之字形上坡、绕湖段。

**边界也要说清**：OSM 在部分偏远山区步道录入不全，个别路段可能沿公路绕行；
轨迹用于**规划和比较**，实际导航请以现场路标和你下载的官方轨迹为准。
"""
        )

    with st.expander("景点与路线数据来源", expanded=False):
        st.markdown(
            f"""
**景点**（`data/attractions.csv`，{len(df_a)} 条）
整理自公开资料，覆盖广东、湖南主要景区，每个都有坐标和「值得去的点」。
门票为参考价，景区调价频繁，以官方为准。

**徒步路线**（`data/hiking_routes.csv`，{len(df_r)} 条）
分布在 {df_r['province'].nunique()} 个省区、{df_r['city'].nunique()} 个市州，
每条都有独立轨迹文件（`data/tracks/`）。

**热度值**是综合指数（0-100），由景区等级、知名度、可达性估算，
**不是官方游客量统计**。用它排序参考可以，不要当权威数据引用。
"""
        )

    st.info(
        "想换成自己的数据？改 `data/attractions.csv` 或 `data/hiking_routes.csv`"
        "（保持表头不变），刷新页面即可生效；要重新生成轨迹跑 "
        "`python tools/build_tracks.py`。"
    )


main()
