"""首页：说明这个站点是干什么的、怎么用。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from app_utils import load_attractions, load_routes, sidebar_common


def main():
    sidebar_common()

    st.title("🗺️ 湘粤旅游与徒步地图")
    st.caption("广东 · 湖南 ｜ 找景点、看徒步轨迹、看城市热度")

    st.markdown(
        "这个站点只回答三个问题："
    )
    st.markdown(
        "① **去某个地方玩，那里有什么值得去的？** —— 输入地名看推荐和理由\n\n"
        "② **这条徒步路线长什么样、走起来多累？** —— 看轨迹线、高程剖面、里程爬升\n\n"
        "③ **哪个城市更值得排进行程？** —— 看城市热度榜"
    )

    df_a = load_attractions()
    df_r = load_routes()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("景点", f"{len(df_a)} 个")
    c2.metric("徒步路线", f"{len(df_r)} 条")
    c3.metric("覆盖城市", f"{df_a['city'].nunique()} 个")
    c4.metric("5A 景区", f"{int((df_a['level'] == '5A').sum())} 个")

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
            "选一条路线，地图上画出轨迹线（起点绿、终点红），"
            "下方给**高程剖面图**：哪里爬升陡、哪里是缓坡一眼看出。"
            "还能上传自己的 GPX 做同样分析。"
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

    with st.expander("数据来源与可信度（请务必看一眼）", expanded=False):
        st.markdown(
            """
**景点数据**（`data/attractions.csv`，126 条）
整理自公开资料，覆盖广东 71 个、湖南 55 个主要景点，每个都有真实坐标和
「值得去的点」。门票为参考价，景区调价频繁，以官方为准。

**徒步路线**（`data/hiking_routes.csv`，31 条）
里程与爬升来自公开资料整理，不同来源口径不同（是否含往返、起点算山门还是停车场）。

**轨迹线**是**示意轨迹**，不是实测 GPX。做法是按路线的标称里程和标称爬升，
反推一条走向自然、长度和爬升都匹配的折线——所以里程、爬升、海拔剖面是对的，
但**具体走位与实际路网有偏差**，不能拿来导航。

要真实轨迹：在你的徒步 App（两步路、户外助手等）里导出 GPX，在徒步页上传，
系统会用真实轨迹重新算里程、爬升和剖面。

**热度值**是综合指数（0-100），由景点等级、知名度、可达性和路线里程综合估算，
**不是官方游客量统计**。用它排序参考可以，不要当权威数据引用。
"""
        )

    st.info(
        "提示：想换成自己的数据？直接改 `data/attractions.csv` 和 "
        "`data/hiking_routes.csv`（保持表头不变），刷新页面即可生效。"
    )


main()
