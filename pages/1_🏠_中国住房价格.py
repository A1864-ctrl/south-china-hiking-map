"""
中国住房价格地图
把原项目的「U.S. Housing」整页替换为国内数据版本：
省级均价choropleth + 城市房价气泡 + 排名榜 + 自备 CSV 上传。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os

import folium
import geopandas as gpd
import pandas as pd
import pydeck as pdk
import streamlit as st

from app_utils import DATA_DIR, data_path, new_map, safe_run, sidebar_common

st.set_page_config(page_title="中国住房价格", layout="wide", page_icon="🏠")

PALETTES = {
    "暖色（低价→高价）": ["#fff5eb", "#fdd49e", "#fdbb84", "#fc8d59", "#e34a33", "#b30000"],
    "蓝绿（低价→高价）": ["#f0f9e8", "#ccebc5", "#a8ddb5", "#7bccc4", "#43a2ca", "#0868ac"],
    "紫红（低价→高价）": ["#feebe2", "#fcc5c0", "#fa9fb5", "#f768a1", "#c51b8a", "#7a0177"],
}


def hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def make_scale(values, palette, n=6):
    """把数值线性映射到调色板，返回 (vmin, vmax, 取色函数)。"""
    colors = [hex_to_rgb(c) for c in PALETTES[palette]]
    vmin, vmax = float(min(values)), float(max(values))
    span = vmax - vmin or 1.0

    def pick(v):
        t = (float(v) - vmin) / span
        t = 0.0 if t < 0 else (1.0 if t > 1 else t)
        idx = min(int(t * (len(colors) - 1)), len(colors) - 2)
        local = t * (len(colors) - 1) - idx
        a, b = colors[idx], colors[idx + 1]
        return tuple(int(a[k] + (b[k] - a[k]) * local) for k in range(3))

    return vmin, vmax, pick


@st.cache_data(show_spinner=False)
def load_provinces():
    gdf = gpd.read_file(data_path("china_provinces.geojson"))
    gdf = gdf[gdf["name"].notna()].copy()
    gdf["name"] = gdf["name"].astype(str)
    # 只保留绘图需要的列：center/adcode 里是列表对象，会让 to_json 序列化失败
    return gdf[["name", "geometry"]]


@st.cache_data(show_spinner=False)
def load_province_price():
    df = pd.read_csv(data_path("china_province_price.csv"))
    df["province"] = df["province"].astype(str)
    return df


@st.cache_data(show_spinner=False)
def load_city_price():
    df = pd.read_csv(data_path("china_city_price.csv"))
    df["city"] = df["city"].astype(str)
    return df


def read_uploaded(file):
    """用户上传 CSV：需要 name + price 两列，可选 lat/lon。"""
    df = pd.read_csv(file)
    lower = {c.lower().strip(): c for c in df.columns}
    name_col = next((v for k, v in lower.items() if k in ("province", "city", "name", "省份", "城市", "名称")), None)
    price_col = next((v for k, v in lower.items() if k in ("price", "price_yuan_sqm", "均价", "房价", "价格")), None)
    if name_col is None or price_col is None:
        raise ValueError("CSV 需要包含名称列（name/province/city/省份/城市）和价格列（price/均价/房价）")
    df = df.rename(columns={name_col: "name", price_col: "price"})
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])
    for c in ("lat", "lon"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def main():
    sidebar_common()
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 数据源")
    source = st.sidebar.radio("选择数据", ["内置示例数据", "上传我的 CSV"], index=0)

    up_file = None
    if source == "上传我的 CSV":
        up_file = st.sidebar.file_uploader("上传 CSV（名称 + 均价两列）", type=["csv"])
        st.sidebar.caption("示例格式：`province,price` 或 `city,price,lat,lon`")

    st.title("🏠 中国住房价格地图")
    st.caption("省级均价分布 + 重点城市房价对比。所有数据均可在左侧替换为你自己的 CSV。")

    st.info(
        "内置数据为**演示用的近似值**（量级参考 2024 年前后二手房挂牌均价），"
        "不构成投资依据。要做严谨分析，请在左侧上传真实数据（如统计局、房价行情网导出的 CSV）。",
        icon="ℹ️",
    )

    provinces = load_provinces()
    prov_price = load_province_price()
    city_df = load_city_price()

    if up_file is not None:
        try:
            user_df = read_uploaded(up_file)
        except Exception as exc:  # noqa: BLE001
            st.error(f"文件读取失败：{exc}")
            st.stop()
        if {"lat", "lon"}.issubset(user_df.columns):
            city_df = user_df.dropna(subset=["lat", "lon"]).rename(columns={"name": "city"})
            city_df["price_yuan_sqm"] = city_df["price"]
            prov_price = None
        else:
            prov_price = pd.DataFrame(
                {"province": user_df["name"], "price_yuan_sqm": user_df["price"], "yoy_pct": 0.0}
            )
        st.success(f"已载入你的数据，共 {len(user_df)} 行。")

    # ------------------------------------------------ 指标卡
    price_series = (prov_price if prov_price is not None else city_df)["price_yuan_sqm"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("省级样本数" if prov_price is not None else "城市样本数", f"{len(price_series)} 个")
    c2.metric("最高均价", f"¥{price_series.max():,.0f}/㎡")
    c3.metric("最低均价", f"¥{price_series.min():,.0f}/㎡")
    c4.metric("均值", f"¥{price_series.mean():,.0f}/㎡")

    st.markdown("---")
    left, right = st.columns([3, 1])
    with right:
        palette = st.selectbox("配色方案", list(PALETTES.keys()))
        metric = st.radio("着色指标", ["均价（元/㎡）", "同比涨跌（%）"])
        show_city = st.checkbox("叠加城市气泡", value=True)
        top_n = st.slider("排名榜显示条数", 5, 20, 10)

    value_col = "price_yuan_sqm" if metric.startswith("均价") else "yoy_pct"

    gdf = provinces.copy()
    if prov_price is not None:
        gdf = gdf.merge(
            prov_price[["province", value_col]], left_on="name", right_on="province", how="left"
        ).drop(columns=["province"])
    else:
        gdf[value_col] = pd.NA

    with left:
        tab_map, tab_3d = st.tabs(["平面地图（高德底图）", "三维柱状视图"])

        with tab_map:
            m = new_map(zoom=3.6)
            has_value = gdf[value_col].notna().any()
            if has_value:
                vmin, vmax, pick = make_scale(gdf[value_col].dropna(), palette)

                def style_fn(feature):
                    v = feature["properties"].get(value_col)
                    color = pick(v) if v is not None else (200, 200, 200)
                    return {"fillColor": f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}", "color": "#666666", "weight": 1, "fillOpacity": 0.75}

                folium.GeoJson(
                    gdf.to_json(),
                    style_function=style_fn,
                    tooltip=folium.GeoJsonTooltip(
                        fields=["name", value_col],
                        aliases=["地区", "数值"],
                        localize=True,
                    ),
                ).add_to(m)
                st.caption(f"色阶：{vmin:,.2f} → {vmax:,.2f}")
            else:
                m.add_gdf(gdf, layer_name="省级边界")
                st.warning("你的数据没有匹配到省级名称，暂时只显示边界。请检查名称是否为「北京市」这类全称。")

            if show_city and "lat" in city_df.columns:
                for _, r in city_df.dropna(subset=["lat", "lon"]).iterrows():
                    folium.CircleMarker(
                        location=[r["lat"], r["lon"]],
                        radius=max(3, min(14, float(r["price_yuan_sqm"]) / 6000)),
                        color="#d62728",
                        fill=True,
                        fill_opacity=0.55,
                        popup=f"{r['city']}：¥{float(r['price_yuan_sqm']):,.0f}/㎡",
                    ).add_to(m)
            m.to_streamlit(height=560)

        with tab_3d:
            if prov_price is None:
                st.info("三维视图需要省级聚合数据；上传城市级数据时请使用平面地图气泡。")
            else:
                vmin, vmax, pick = make_scale(gdf[value_col].dropna(), palette)
                colors = []
                for v in gdf[value_col]:
                    rgb = pick(v) if pd.notna(v) else (200, 200, 200)
                    colors.append(list(rgb) + [200])
                gdf["fill_color"] = colors
                gdf["elevation"] = gdf[value_col].fillna(0).astype(float)

                layer = pdk.Layer(
                    "GeoJsonLayer",
                    gdf,
                    pickable=True,
                    opacity=0.8,
                    stroked=True,
                    filled=True,
                    extruded=True,
                    wireframe=True,
                    get_elevation="elevation",
                    elevation_scale=40,
                    get_fill_color="fill_color",
                    get_line_color=[80, 80, 80],
                )
                view = pdk.ViewState(latitude=35, longitude=105, zoom=3.2, pitch=45, bearing=0)
                st.pydeck_chart(
                    pdk.Deck(
                        layers=[layer],
                        initial_view_state=view,
                        map_provider="carto",
                        map_style="light",
                        tooltip={"html": "<b>{name}</b><br>数值：{elevation}"},
                    )
                )

    st.markdown("---")
    rank_df = prov_price if prov_price is not None else city_df[["city", "province", "price_yuan_sqm", "yoy_pct"]]
    name_col = "province" if prov_price is not None else "city"
    rank = (
        rank_df[[name_col, "price_yuan_sqm", "yoy_pct"]]
        .dropna(subset=["price_yuan_sqm"])
        .sort_values("price_yuan_sqm", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    rank.index = rank.index + 1
    rank.columns = ["地区", "均价（元/㎡）", "同比（%）"]

    col_a, col_b = st.columns([1.2, 1])
    with col_a:
        st.subheader(f"均价排名 Top {top_n}")
        st.dataframe(rank, use_container_width=True)
        st.download_button(
            "下载这份排名（CSV）",
            rank.to_csv(index=False).encode("utf-8-sig"),
            file_name="china_housing_rank.csv",
            mime="text/csv",
        )
    with col_b:
        st.subheader("涨跌分布")
        yoy = rank_df.dropna(subset=["yoy_pct"])
        if len(yoy):
            st.bar_chart(yoy.set_index(name_col)["yoy_pct"], height=380)
            st.caption("同比为负说明价格较去年同期下跌。")
        else:
            st.info("没有同比数据列。")


safe_run(main)
