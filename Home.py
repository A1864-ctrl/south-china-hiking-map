"""湘粤赣桂旅游与徒步地图 —— 应用入口。

Streamlit 多页面：这里只做两件事——设置全局配置、注册导航。
真正的页面内容都在 views/ 下，一个文件一页。
"""

import streamlit as st

st.set_page_config(
    page_title="湘粤赣桂旅游与徒步地图",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "开始": [
        st.Page("views/首页.py", title="项目说明", icon="🏠", default=True),
    ],
    "找景点": [
        st.Page("views/景点搜索.py", title="景点搜索", icon="🔍"),
    ],
    "去徒步": [
        st.Page("views/徒步路线.py", title="徒步轨迹", icon="🥾"),
    ],
    "看热度": [
        st.Page("views/热度榜.py", title="热度榜", icon="🔥"),
    ],
}

st.navigation(pages).run()
