import streamlit as st
import leafmap.foliumap as leafmap

st.set_page_config(page_title="徒步路线地图工具", layout="wide")

st.sidebar.markdown("### 徒步路线使用指南")
st.sidebar.markdown("1. 选择「底图」切换为 OpenStreetMap 查看徒步道路")
st.sidebar.markdown("2. 可通过地图缩放定位目标徒步区域")
st.sidebar.markdown("3. 支持测量路线距离、查看地形与卫星影像")
st.sidebar.markdown("---")

st.sidebar.title("About")
st.sidebar.info("""
    - Web App URL: <https://streamlit.gishub.org>
    - GitHub repository: <https://github.com/opengeos/streamlit-geospatial>
    """)

st.sidebar.title("Contact")
st.sidebar.info("""
    Qiusheng Wu at [wetlands.io](https://wetlands.io) | [GitHub](https://github.com/giswqs) | [Twitter](https://twitter.com/giswqs) | [YouTube](https://youtube.com/@giswqs) | [LinkedIn](https://www.linkedin.com/in/giswqs)
    """)

st.sidebar.title("Support")
st.sidebar.info("""
    If you want to reward my work, I'd love a cup of coffee from you. Thanks!
    [buymeacoffee.com/giswqs](http://buymeacoffee.com/giswqs)
    """)


st.title("徒步路线可视化与地图工具")
st.markdown("基于开源地理空间项目二次开发，支持路线查看、图层切换、坐标定位，适用户外徒步路线规划与轨迹查看")


st.markdown("""
    This multi-page web app demonstrates various interactive web apps created using [streamlit](https://streamlit.io) and open-source mapping libraries,
    such as [leafmap](https://leafmap.org), [geemap](https://geemap.org), [pydeck](https://deckgl.readthedocs.io), and [kepler.gl](https://docs.kepler.gl/docs/keplergl-jupyter).
    This is an open-source project and you are very welcome to contribute your comments, questions, resources, and apps as [issues](https://github.com/opengeos/streamlit-geospatial/issues) or
    [pull requests](https://github.com/opengeos/streamlit-geospatial/pulls) to the [GitHub repository](https://github.com/opengeos/streamlit-geospatial).

    """)

st.info("Click on the left sidebar menu to navigate to the different apps.")

st.subheader("Timelapse of Satellite Imagery")
st.markdown("""
    The following timelapse animations were created using the Timelapse web app. Click `Timelapse` on the left sidebar menu to create your own timelapse for any location around the globe.
""")

row1_col1, row1_col2 = st.columns(2)
with row1_col1:
    st.image("https://github.com/giswqs/data/raw/main/timelapse/spain.gif")
    st.image("https://github.com/giswqs/data/raw/main/timelapse/las_vegas.gif")

with row1_col2:
    st.image("https://github.com/giswqs/data/raw/main/timelapse/goes.gif")
    st.image("https://github.com/giswqs/data/raw/main/timelapse/fire.gif")
