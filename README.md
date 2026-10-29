# 徒步路线可视化与地图工具
> 本项目基于 [opengeos/streamlit-geospatial](https://github.com/opengeos/streamlit-geospatial)（⭐700+）二次开发，原项目开源协议：MIT

## ✨ 改造内容
1.  适配徒步业务场景，改造页面标题与侧边栏指引，新增徒步路线使用指南
2.  优化国内访问体验，聚焦基础地图浏览、图层切换、坐标定位核心能力
3.  完成本地 Windows 环境搭建与依赖调试，梳理多页面地图应用结构

## 技术栈
Python · Streamlit · Leaflet · OpenStreetMap · Folium · GeoPandas

## 本地运行
```bash
# 1. 创建虚拟环境
python -m venv venv

# 2. 激活环境（Windows）
venv\Scripts\activate

# 3. 安装核心依赖
pip install streamlit leafmap folium geopandas

# 4. 启动项目
streamlit run Home.py
