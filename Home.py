"""应用入口：侧边栏按「地理空间工具 / 户外徒步」分组导航。

用 st.navigation 而不是 pages/ 自动导航，好处是能分组、排序，
不会把两类完全不同的功能平铺成一长条菜单。
"""

import streamlit as st

st.set_page_config(
    page_title="徒步路线与地理空间工具",
    page_icon="🥾",
    layout="wide",
)

nav = {
    "开始": [
        st.Page("views/首页.py", title="首页 · 能力说明", icon="🏠", default=True),
    ],
    "地理空间工具": [
        st.Page("views/中国住房价格.py", title="中国住房价格", icon="🏘️"),
        st.Page("views/热力图.py", title="热力图", icon="🔥"),
        st.Page("views/点聚合.py", title="点聚合", icon="📍"),
        st.Page("views/底图切换.py", title="底图切换", icon="🗺️"),
        st.Page("views/分屏对比.py", title="分屏对比", icon="🪟"),
        st.Page("views/矢量数据.py", title="矢量数据", icon="🔲"),
        st.Page("views/在线地图服务.py", title="在线地图服务", icon="📦"),
    ],
    "户外徒步": [
        st.Page("views/徒步路线.py", title="徒步路线（湖南 · 广东）", icon="🥾"),
    ],
}

pg = st.navigation(nav)
pg.run()
