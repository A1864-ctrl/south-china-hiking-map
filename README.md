# 湘粤旅游与徒步地图

广东、湖南两省的**景点搜索**、**徒步轨迹分析**、**城市热度榜**。

一个 Streamlit 应用，只回答三个问题：

1. 去某个地方玩，那里有什么值得去的？—— 输入地名看推荐和理由
2. 这条徒步路线长什么样、走起来多累？—— 看轨迹线、高程剖面、里程爬升
3. 哪个城市更值得排进行程？—— 看城市热度榜

## 功能

| 页面 | 做什么 |
|---|---|
| 🏠 项目说明 | 站点定位、数据可信度、怎么改数据 |
| 🔍 景点搜索 | 按地名/区县/类型搜索，地图定位 + 卡片详情（值得去的点、门票、建议时长、最佳季节） |
| 🥾 徒步轨迹 | 31 条路线库，地图画轨迹（起点绿终点红）+ 高程剖面 + 最陡段分析 + 导出 GPX；也可上传自己的 GPX 做同样分析 |
| 🔥 热度榜 | 城市维度汇总景点与路线，算综合热度指数，条形榜 + 观光/徒步散点对比 + 热度地图 |

## 数据

| 文件 | 内容 | 规模 |
|---|---|---|
| `data/attractions.csv` | 景点：名称、省市县、经纬度、等级、类型、门票、建议时长、最佳季节、**值得去的点**、热度 | 126 条（粤 71 / 湘 55） |
| `data/hiking_routes.csv` | 徒步路线：名称、位置、坐标、里程、爬升、难度、天数、季节、描述、热度 | 31 条（粤 16 / 湘 15） |

改数据不用动代码：保持表头不变，直接替换 CSV，刷新页面即可。

### 数据可信度（重要）

- **景点信息**整理自公开资料，门票为参考价，以官方为准。
- **徒步里程与爬升**来自公开资料，不同来源口径不同（是否含往返、起点算山门还是停车场）。
- **轨迹线是按标称里程和爬升自动生成的示意线**，不是实测航迹。里程、爬升、海拔剖面与标称值一致，但具体走位与实际路网有偏差，**不能用来导航**。要真实轨迹请上传 GPX。
- **热度值是估算指数**（0-100，由等级、知名度、可达性综合），**不是官方游客量统计**。

## 本地运行

```powershell
cd D:\TJM\streamlit-geospatial
.\venv\Scripts\python.exe -m streamlit run Home.py --server.port 8531
```

浏览器打开 http://localhost:8531

> ⚠️ 改了 `app_utils.py` 必须 `Ctrl+C` 重启服务。Streamlit 只热重载页面脚本，
> 不会重新导入被 import 的模块，否则会看到 `ImportError: cannot import name ...`。

## 项目结构

```
streamlit-geospatial/
├── Home.py               # 入口：全局配置 + 导航注册
├── app_utils.py          # 公共模块：底图、地图渲染、CSV 读取、轨迹生成、GPX 解析
├── views/
│   ├── 首页.py
│   ├── 景点搜索.py
│   ├── 徒步路线.py
│   └── 热度榜.py
├── data/
│   ├── attractions.csv
│   ├── hiking_routes.csv
│   └── china_provinces.geojson
├── requirements.txt
└── packages.txt
```

技术要点：

- **底图**用高德瓦片，`{s}` 子域名必须显式设成 `1/2/3/4`（folium 默认填 `a/b/c`，高德不认，会整片灰）
- **地图渲染**走 `app_utils.show_map()`（`get_root().render()` 直接拿字符串），不用 leafmap 的 `to_streamlit()`——后者会落盘再用系统编码读回，中文 Windows 下必崩（GBK 解码 UTF-8）
- **读表**走 `app_utils.read_csv_smart()`，依次尝试 utf-8-sig / utf-8 / gb18030，兼容 Excel 另存的 GBK 版 CSV

## 部署

见 `部署手册.md`。要点：Streamlit Community Cloud → 仓库 `A1864-ctrl/streamlit-geospatial` → 分支 `master` → Main file path `Home.py` → Advanced settings 里把 Python 版本选成 3.12。

## 许可

基于 [opengeos/streamlit-geospatial](https://github.com/opengeos/streamlit-geospatial)（MIT）的架构二次开发。
