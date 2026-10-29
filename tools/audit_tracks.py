"""轨迹体检：逐条给出「已上架 / 未通过」的状态和根因分类。

用法：
    ./venv/Scripts/python.exe tools/audit_tracks.py            # 打印到终端
    ./venv/Scripts/python.exe tools/audit_tracks.py --md 报告.md  # 同时写 markdown

不需要联网：已上架的读 data/tracks/*.json，未上架的读 tools/.cache/ 里
Valhalla 的原始规划结果，只做几何分析（全长、直线和、逐段绕行）。
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from build_tracks import decode_polyline6, haversine_m  # noqa: E402
from routes_manifest import ROUTES  # noqa: E402

OUT = os.path.join(ROOT, "data", "tracks")
CACHE = os.path.join(ROOT, "tools", ".cache")


def _legs(raw: dict) -> list:
    body = raw.get("trip", raw)
    if "legs" in body:
        return body["legs"]
    if "trip" in body:
        return body["trip"]["legs"]
    return []


def _straight(wps: list) -> float:
    return (
        sum(
            haversine_m((a["lat"], a["lon"]), (b["lat"], b["lon"]))
            for a, b in zip(wps, wps[1:])
        )
        / 1000.0
    )


def analyse_cache(cfg: dict) -> dict:
    """从未上架路线的 Valhalla 缓存反推问题类型。"""
    hits = glob.glob(os.path.join(CACHE, f"{cfg['id']}-*.json"))
    straight = _straight(cfg["waypoints"])
    info = {"path_km": 0.0, "straight_km": straight, "ratio": 0.0, "worst": None, "note": ""}
    if not hits:
        info["note"] = "没有规划结果（缓存缺失）"
        return info

    legs = _legs(json.load(open(hits[0], encoding="utf-8")))
    if not legs:
        info["note"] = "没有规划结果（Valhalla 未返回路段）"
        return info

    path = 0.0
    worst = None  # (倍数, 里程, 直线, 起名, 终名)
    for i, leg in enumerate(legs):
        pts = decode_polyline6(leg["shape"])
        seg = sum(haversine_m(pts[j], pts[j + 1]) for j in range(len(pts) - 1)) / 1000.0
        path += seg
        st = haversine_m(
            (cfg["waypoints"][i]["lat"], cfg["waypoints"][i]["lon"]),
            (cfg["waypoints"][i + 1]["lat"], cfg["waypoints"][i + 1]["lon"]),
        ) / 1000.0
        if st > 0.2 and seg > 1.0:
            k = seg / st
            if worst is None or k > worst[0]:
                worst = (k, seg, st, cfg["waypoints"][i]["name"], cfg["waypoints"][i + 1]["name"])

    info["path_km"] = path
    info["ratio"] = path / max(straight, 0.001)
    info["worst"] = worst

    # 根因分类
    if info["ratio"] < 0.9:
        info["note"] = "途经点吸附异常（路径比直线还短，两个点被吸到同一条路上）"
    elif worst and worst[0] > 5.0 and worst[1] > 4.0:
        info["note"] = (
            f"OSM 无步道：{worst[3]}→{worst[4]} 直线 {worst[2]:.1f}km 被迫绕 {worst[1]:.0f}km"
        )
    elif info["ratio"] > 3.0:
        info["note"] = f"整体绕行 {info['ratio']:.1f}× 直线（步道不连通）"
    else:
        info["note"] = "几何正常，卡在海拔校验（走不到主峰 / 爬升不足 3km）"
    return info


def read_reject(cfg: dict):
    """build_tracks 落下的体检记录（含真实校验原因）。"""
    fn = os.path.join(CACHE, f"reject-{cfg['id']}.json")
    if not os.path.exists(fn):
        return None
    return json.load(open(fn, encoding="utf-8"))


def classify(rej: dict) -> str:
    """把校验原因归成可操作的类别。"""
    st = rej["stats"]
    peak = rej.get("peak_m") or 0
    ratio = rej.get("ratio") or 0
    km = st["distance_km"]
    reach = (st["ele_max"] / peak) if peak else 1.0
    notes = "；".join(rej["problems"])

    if km < 0.6:
        return "D"
    if peak and reach < 0.30:
        return "A"          # 轨迹根本没上山，基本是途经点坐标错了
    if "一段绕" in notes or ratio > 4.5:
        return "B"          # OSM 步道缺失，被迫绕公路
    if peak and reach < 0.85:
        return "C"          # 上了山但停在半路，要补山脊上的途经点
    return "C"


CAUSE = {
    "A": ("途经点坐标写错", "起点/终点落在了平地或别的山头，轨迹根本没进山。改 routes_manifest.py 里的坐标后单条重建。"),
    "B": ("OSM 步道缺失", "这一带 OpenStreetMap 没有可通行的步道，规划器只能绕公路（几公里绕成几十公里）。改不了算法，只能换数据源。"),
    "C": ("只上到半山", "路径能走通，但停在山腰没到顶，通常是中间缺一个山脊/垭口的途经点。补一个点再重建。"),
    "D": ("途经点重合", "两个途经点被吸附到同一条路上，重建后只剩几百米。核对坐标是否重复或过近。"),
}


def collect() -> list:
    rows = []
    for cfg in ROUTES:
        fn = os.path.join(OUT, f"{cfg['id']}.json")
        if os.path.exists(fn):
            doc = json.load(open(fn, encoding="utf-8"))
            st = doc["stats"]
            rows.append(
                {
                    "id": cfg["id"],
                    "name": cfg["name"],
                    "province": cfg["province"],
                    "ok": True,
                    "km": st["distance_km"],
                    "ascent": st["ascent_m"],
                    "ele": f"{st['ele_min']:.0f}-{st['ele_max']:.0f}",
                    "pts": len(doc["points"]),
                    "note": "",
                    "cache": None,
                    "cause": None,
                }
            )
        else:
            rej = read_reject(cfg)
            if rej:
                st = rej["stats"]
                rows.append(
                    {
                        "id": cfg["id"],
                        "name": cfg["name"],
                        "province": cfg["province"],
                        "ok": False,
                        "km": st["distance_km"],
                        "ascent": st["ascent_m"],
                        "ele": f"{st['ele_min']:.0f}-{st['ele_max']:.0f}",
                        "pts": 0,
                        "note": "；".join(rej["problems"]),
                        "cache": {"ratio": rej.get("ratio", 0), "path_km": st["distance_km"]},
                        "cause": classify(rej),
                    }
                )
                continue
            info = analyse_cache(cfg)
            rows.append(
                {
                    "id": cfg["id"],
                    "name": cfg["name"],
                    "province": cfg["province"],
                    "ok": False,
                    "km": info["path_km"],
                    "ascent": 0,
                    "ele": "-",
                    "pts": 0,
                    "note": info["note"],
                    "cache": info,
                    "cause": None,
                }
            )
    return rows


def render(rows: list) -> str:
    ok = [r for r in rows if r["ok"]]
    bad = [r for r in rows if not r["ok"]]
    lines = []
    lines.append(f"# 轨迹体检报告\n")
    lines.append(f"共 {len(rows)} 条候选路线，已上架 **{len(ok)}** 条，未通过 **{len(bad)}** 条。\n")

    lines.append("## 一、已上架（轨迹贴合 OSM 真实路网）\n")
    lines.append("| 路线 | 省份 | 里程 | 爬升 | 海拔 | 坐标点 |")
    lines.append("|---|---|---|---|---|---|")
    for r in sorted(ok, key=lambda x: (x["province"], -x["km"])):
        lines.append(
            f"| {r['name']} | {r['province']} | {r['km']:.2f} km | {r['ascent']:.0f} m | "
            f"{r['ele']} m | {r['pts']} |"
        )
    lines.append("")

    lines.append("## 二、未通过及原因\n")
    lines.append("| 路线 | 省份 | 里程 | 海拔 | 绕行倍数 | 类别 | 校验拦截原因 |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in sorted(bad, key=lambda x: (str(x["cause"]), x["province"], -(x["cache"] or {}).get("ratio", 0))):
        c = r["cache"] or {}
        ratio = f"{c.get('ratio', 0):.1f}×" if c.get("ratio") else "-"
        lines.append(
            f"| {r['name']} | {r['province']} | {r['km']:.1f} km | {r['ele']} m | {ratio} "
            f"| {r['cause'] or '?'} | {r['note']} |"
        )
    lines.append("")

    lines.append("## 三、根因归类与处理建议\n")
    buckets = {}
    for r in bad:
        buckets.setdefault(r["cause"] or "?", []).append(r["name"])
    order = ["A", "B", "C", "D", "?"]
    for k in order:
        if k not in buckets:
            continue
        if k in CAUSE:
            title, advice = CAUSE[k]
        else:
            title, advice = "未能归类", "需要联网重算确认。"
        lines.append(f"### {k}. {title}（{len(buckets[k])} 条）\n")
        lines.append(f"**涉及：**{'、'.join(buckets[k])}\n")
        lines.append(f"**怎么解决：**{advice}\n")

    lines.append("## 四、四类问题对应的通用解法\n")
    lines.append(
        "| 解法 | 适用 | 做法 | 成本 |\n"
        "|---|---|---|---|\n"
        "| 1. 改途经点坐标 | A、C、D 类 | 改 `tools/routes_manifest.py` 的 `waypoints`，"
        "`python tools/build_tracks.py --only <id> --verbose` 单条重建 | 低 |\n"
        "| 2. 补 OSM 步道 | B 类 | 在 openstreetmap.org 上把登山步道画上去（走一段画一段），"
        "几天后 Valhalla 才会用到 | 高，需人工测绘 |\n"
        "| 3. 导入 GPX 航迹 | 全部，尤其 B 类 | 从两步路/高德导出 GPX，直接当轨迹用，"
        "不再依赖路网规划 | 低，最准 |\n"
        "| 4. 不上架 | B 类且无 GPX | 保持现状，宁缺毋滥，避免画出绕 50 km 的假轨迹 | 零 |\n"
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default=None, help="把报告写到指定 markdown 文件")
    args = ap.parse_args()

    rows = collect()
    text = render(rows)
    print(text)
    if args.md:
        path = args.md if os.path.isabs(args.md) else os.path.join(ROOT, args.md)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\n报告已写入 {path}")


if __name__ == "__main__":
    main()
