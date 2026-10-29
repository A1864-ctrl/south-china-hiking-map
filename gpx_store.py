"""把 GPX 航迹转成站点内部的轨迹 JSON，并落库到 data/tracks/。

与 tools/build_tracks.py 生成的轨迹共用同一套 JSON 结构，区别只在 source 字段：

    planned  —— Valhalla 按 OSM 路网规划出来的路径
    gpx      —— 设备/两步路实测航迹，精度等于 GPS 记录本身

为什么要这个模块：OSM 在华南山区步道覆盖很稀，规划器只能沿着公路和村道走，
画出来是折线，到不了「一脚一脚」的精度。唯一可靠的办法是把实测航迹灌进来。
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
import time

from app_utils import DATA_DIR, TRACK_DIR, haversine_m

CUSTOM_CSV = os.path.join(DATA_DIR, "custom_routes.csv")

# 存在感死区：海拔抖动 3 米以内不计入爬升，避免把 GPS 噪声累加成假爬升
ELE_DEADBAND = 3.0
# 抽稀容差（米）。两步路导出的航迹动辄上万点，直接渲染会卡死浏览器
SIMPLIFY_TOL = 4.0

CSV_COLUMNS = [
    "track_id", "name", "province", "city", "type", "lon", "lat",
    "distance_km", "ascent_m", "ele_max", "n_points", "n_waypoints",
    "difficulty", "days", "best_season", "desc", "heat",
]


# ------------------------------------------------------------------ 几何
def cumulative_km(points: list) -> list:
    cum = [0.0]
    for a, b in zip(points, points[1:]):
        cum.append(cum[-1] + haversine_m((a[0], a[1]), (b[0], b[1])) / 1000.0)
    return cum


def _dp(pts: list, tol_m: float) -> list:
    """Douglas-Peucker，迭代实现，避免上万点时爆递归栈。"""
    n = len(pts)
    if n < 3:
        return list(pts)
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        lo, hi = stack.pop()
        if hi - lo < 2:
            continue
        ax, ay = pts[lo][0], pts[lo][1]
        bx, by = pts[hi][0], pts[hi][1]
        # 用平面近似（纬度缩放），在几公里尺度上误差可忽略
        kx = math.cos(math.radians((ay + by) / 2.0))
        best_i, best_d = -1, -1.0
        for i in range(lo + 1, hi):
            px, py = pts[i][0], pts[i][1]
            # 点到线段的垂直距离（米）
            dx, dy = (bx - ax) * kx * 111320.0, (by - ay) * 111320.0
            vx, vy = (px - ax) * kx * 111320.0, (py - ay) * 111320.0
            seg = dx * dx + dy * dy
            if seg <= 1e-9:
                d = math.hypot(vx, vy)
            else:
                t = max(0.0, min(1.0, (vx * dx + vy * dy) / seg))
                d = math.hypot(vx - t * dx, vy - t * dy)
            if d > best_d:
                best_i, best_d = i, d
        if best_d > tol_m and best_i > 0:
            keep[best_i] = True
            stack.append((lo, best_i))
            stack.append((best_i, hi))
    return [p for p, k in zip(pts, keep) if k]


def simplify(points: list, tol_m: float = SIMPLIFY_TOL) -> list:
    """抽稀，但保证不丢掉首尾和明显的转折点。"""
    if len(points) <= 2:
        return list(points)
    out = _dp(points, tol_m)
    if len(out) >= 20:
        return out
    # 轨迹本身接近直线时 DP 会抽到只剩首尾，改用等距抽样保底
    step = max(1, len(points) // 40)
    fallback = list(points[::step])
    if fallback[-1] != points[-1]:
        fallback.append(points[-1])
    return fallback


# ------------------------------------------------------------------ 统计
def _smooth_series(vals: list, window: int = 5) -> list:
    """滑动平均，压掉 GPS 高程抖动。None 原样保留。"""
    n = len(vals)
    if n == 0 or window < 3:
        return list(vals)
    half = window // 2
    out = list(vals)
    for i in range(n):
        seg = [v for v in vals[max(0, i - half): i + half + 1] if v is not None]
        if seg:
            out[i] = sum(seg) / len(seg)
    return out


def compute_stats(points: list) -> dict:
    """里程、累计爬升/下降、海拔极值。

    爬升用「平滑后的高程」+ 死区计算：GPS 高程抖动常有 ±10 米，
    直接逐点累加会把噪声攒成几千米的假爬升。
    海拔极值仍取原始值，避免平滑把顶峰削低。
    """
    total = 0.0
    for a, b in zip(points, points[1:]):
        total += haversine_m((a[0], a[1]), (b[0], b[1]))

    raw_eles = [p[2] for p in points]
    sm = _smooth_series(raw_eles, 5)
    has_ele = any(e is not None for e in raw_eles)

    up = down = 0.0
    base = None
    for e in sm:
        if e is None:
            continue
        if base is None:
            base = e
            continue
        diff = e - base
        if abs(diff) >= ELE_DEADBAND:
            if diff > 0:
                up += diff
            else:
                down -= diff
            base = e

    eles = [e for e in raw_eles if e is not None]
    return {
        "distance_km": round(total / 1000.0, 2),
        "ascent_m": round(up) if has_ele else None,
        "descent_m": round(down) if has_ele else None,
        "ele_min": round(min(eles)) if eles else None,
        "ele_max": round(max(eles)) if eles else None,
        "n_points": len(points),
    }


def speed_profile(points: list, cum_km: list) -> list:
    """按 Tobler 徒步速度函数估算每段速度（km/h），用于画速度曲线。

    Tobler: v = 6 * exp(-3.5 * |坡度 + 0.05|)，坡度 = 高差/水平距离
    """
    out = []
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        seg_m = haversine_m((a[0], a[1]), (b[0], b[1]))
        if seg_m < 0.5:
            continue
        if a[2] is not None and b[2] is not None:
            slope = (b[2] - a[2]) / seg_m
        else:
            slope = 0.0
        v = 6.0 * math.exp(-3.5 * abs(slope + 0.05))
        out.append(
            {
                "km": round(cum_km[i], 3),
                "kmh": round(max(0.4, min(6.0, v)), 2),
                "grade": round(slope * 100, 1),
            }
        )
    return out


# ------------------------------------------------------------------ 落库
def _slug(text: str) -> str:
    """把中文名转成稳定的 ascii id 片段。"""
    import hashlib

    raw = str(text).strip()
    ascii_part = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    if len(ascii_part) >= 3:
        return ascii_part[:24]
    return "r" + hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]


def make_id(name: str) -> str:
    """由路线名生成稳定的 track_id。"""
    return "gpx-" + _slug(name)


def build_doc(points: list, meta: dict) -> dict:
    """points: [(lat, lon, ele_or_None)]；meta 里至少要有 name。"""
    name = (meta.get("name") or "未命名轨迹").strip()
    cum = cumulative_km(points)
    stats = compute_stats(points)

    # 逐点累计里程，供地图按里程取点
    pts_out = [
        [round(p[0], 6), round(p[1], 6),
         (round(p[2], 1) if p[2] is not None else None),
         round(cum[i], 3)]
        for i, p in enumerate(points)
    ]

    waypoints = []
    for w in meta.get("waypoints") or []:
        # 投影到最近的轨迹点，拿到里程与海拔
        best_i, best_d = 0, 1e18
        for i, p in enumerate(points):
            d = haversine_m((w["lat"], w["lon"]), (p[0], p[1]))
            if d < best_d:
                best_i, best_d = i, d
        if best_d > 2000:  # 离轨迹两公里以上的路点丢掉，多半是别的点
            continue
        waypoints.append(
            {
                "name": w.get("name") or "路点",
                "lat": round(points[best_i][0], 5),
                "lon": round(points[best_i][1], 5),
                "km": round(cum[best_i], 2),
                "ele": round(points[best_i][2]) if points[best_i][2] is not None else None,
            }
        )
    if not waypoints:
        for idx, tag in ((0, "起点"), (len(points) - 1, "终点")):
            waypoints.append(
                {
                    "name": tag,
                    "lat": round(points[idx][0], 5),
                    "lon": round(points[idx][1], 5),
                    "km": round(cum[idx], 2),
                    "ele": round(points[idx][2]) if points[idx][2] is not None else None,
                }
            )
    waypoints.sort(key=lambda x: x["km"])

    return {
        "id": meta["id"],
        "name": name,
        "provider": "GPX 实测航迹（用户导入）",
        "source": "gpx",
        "built": time.strftime("%Y-%m-%d"),
        "points": simplify(pts_out),
        "waypoints": waypoints,
        "dropped_labels": [],
        "speed": speed_profile(points, cum),
        "stats": stats,
        "reliable": True,
        "quality_note": "",
    }


def save_doc(doc: dict, meta: dict) -> str:
    """写轨迹 JSON + 往 custom_routes.csv 追加一行。返回 track_id。"""
    os.makedirs(TRACK_DIR, exist_ok=True)
    fn = os.path.join(TRACK_DIR, f"{doc['id']}.json")
    with open(fn, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

    st0 = doc["stats"]
    w0 = doc["waypoints"][0]
    row = {
        "track_id": doc["id"],
        "name": doc["name"],
        "province": meta.get("province") or "",
        "city": meta.get("city") or "",
        "type": meta.get("type") or "穿越",
        "lon": w0["lon"],
        "lat": w0["lat"],
        "distance_km": st0["distance_km"],
        "ascent_m": st0["ascent_m"] if st0["ascent_m"] is not None else 0,
        "ele_max": st0["ele_max"] if st0["ele_max"] is not None else 0,
        "n_points": len(doc["points"]),
        "n_waypoints": len(doc["waypoints"]),
        "difficulty": meta.get("difficulty") or "中等",
        "days": meta.get("days") or 1,
        "best_season": meta.get("best_season") or "春秋",
        "desc": meta.get("desc") or "",
        "heat": int(meta.get("heat") or 60),
    }

    is_new = not os.path.exists(CUSTOM_CSV)
    existing = []
    if not is_new:
        with open(CUSTOM_CSV, encoding="utf-8-sig", newline="") as f:
            existing = [r for r in csv.DictReader(f) if r.get("track_id") != row["track_id"]]
    existing.append(row)
    with open(CUSTOM_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(existing)
    return doc["id"]


def import_gpx(raw_bytes: bytes, meta: dict, parse_fn=None) -> dict:
    """一步到位：解析 → 算统计 → 落库。返回写入的 doc。"""
    if parse_fn is None:
        from app_utils import parse_gpx

        parse_fn = parse_gpx
    points = parse_fn(raw_bytes, meta.get("name") or "gpx")
    meta = dict(meta)
    meta.setdefault("id", "gpx-" + _slug(meta.get("name") or "track"))
    doc = build_doc(points, meta)
    save_doc(doc, meta)
    return doc


def list_custom() -> list:
    if not os.path.exists(CUSTOM_CSV):
        return []
    with open(CUSTOM_CSV, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def delete_custom(track_id: str) -> bool:
    """删掉一条导入的路线（轨迹 JSON + CSV 行）。"""
    if not os.path.exists(CUSTOM_CSV):
        return False
    with open(CUSTOM_CSV, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    keep = [r for r in rows if r.get("track_id") != track_id]
    if len(keep) == len(rows):
        return False
    with open(CUSTOM_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(keep)
    fn = os.path.join(TRACK_DIR, f"{track_id}.json")
    if os.path.exists(fn):
        os.remove(fn)
    return True
