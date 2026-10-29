"""轨迹构建工具：途经点 → OSRM 真实步行路网 → SRTM 真实海拔 → data/tracks/*.json

为什么要在本地一次性构建，而不是运行时请求：
1. 运行时不依赖外网接口，页面秒开、离线可用、部署后不会因为接口挂掉而白屏；
2. OSRM 公共实例有速率限制，实时调用会被封；
3. 构建期可以做坐标校验（用 SRTM 海拔反查坐标是否写偏），运行期做不到。

用法：
    python tools/build_tracks.py            # 构建全部
    python tools/build_tracks.py --only 武功山
    python tools/build_tracks.py --verify   # 只校验，不写文件
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "tools", ".cache")
OUT = os.path.join(ROOT, "data", "tracks")

OSRM = "https://routing.openstreetmap.de/routed-foot/route/v1/foot"
ELEV = "https://api.opentopodata.org/v1/srtm30m"

_session = requests.Session()
_session.trust_env = False  # 系统代理会拦掉这两个域名
_session.headers.update({"User-Agent": "hiking-track-builder/1.0"})


# ---------------------------------------------------------------- 基础工具
def haversine_m(a, b) -> float:
    r = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = p2 - p1
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def get_json(url: str, params=None, tries: int = 4, sleep: float = 2.0):
    last = None
    for i in range(tries):
        try:
            r = _session.get(url, params=params, timeout=90)
            if r.status_code == 200:
                return r.json()
            last = RuntimeError(f"HTTP {r.status_code}: {r.text[:120]}")
        except Exception as exc:  # noqa: BLE001
            last = exc
        time.sleep(sleep * (i + 1))
    raise last


def find_peak_target(lat, lon, target_m, max_r=0.10):
    """在给定点附近找「海拔最接近公开值」的位置。

    注意不能直接取范围内的最高点：崀山八角寨 818 米，附近 10 公里内有别的
    千米级山峰，取最高会跑到另一座山上。这里用综合打分——
    海拔偏差为主，距离为辅——挑出真正的那座山头。
    """
    best = (1e18, lat, lon, 0.0)
    for r, st in ((max_r, 0.01), (0.008, 0.002), (0.002, 0.0005)):
        n = max(1, int(round(r / st)))
        grid = [
            (round(best[1] + i * st, 5), round(best[2] + j * st, 5))
            for i in range(-n, n + 1)
            for j in range(-n, n + 1)
        ]
        for k in range(0, len(grid), 90):
            chunk = grid[k : k + 90]
            try:
                eles = elevations(chunk)
            except Exception:  # noqa: BLE001
                continue
            for (a, b), e in zip(chunk, eles):
                dev = abs(e - target_m) / max(1.0, target_m)
                dist = haversine_m((lat, lon), (a, b)) / 1000.0
                score = dev * 6.0 + dist / max(2.0, max_r * 111)
                if score < best[0]:
                    best = (score, a, b, e)
    return best[1], best[2], best[3]


def find_peak(lat: float, lon: float, radius_deg: float = 0.03, step: float = 0.004):
    """在给定点附近扫海拔网格，找出真正的最高点。

    峰顶坐标靠人工写容易偏一两公里，SRTM 一扫就知道。返回 (lat, lon, ele)。
    """
    n = int(radius_deg / step)
    grid = [
        (round(lat + i * step, 5), round(lon + j * step, 5))
        for i in range(-n, n + 1)
        for j in range(-n, n + 1)
    ]
    best = (-1e9, lat, lon)
    for k in range(0, len(grid), 90):
        chunk = grid[k : k + 90]
        eles = elevations(chunk, batch=90)
        for (a, b), e in zip(chunk, eles):
            if e > best[0]:
                best = (e, a, b)
    return best[1], best[2], best[0]


def elevations(coords, batch: int = 90):
    """批量查 SRTM 海拔。opentopodata 限制每次 100 点、每秒 1 次。"""
    out = []
    for i in range(0, len(coords), batch):
        chunk = coords[i : i + batch]
        locs = "|".join(f"{a:.5f},{b:.5f}" for a, b in chunk)
        d = get_json(ELEV, {"locations": locs})
        got = d.get("results", [])
        if len(got) != len(chunk):
            raise RuntimeError(f"海拔返回数量不符 {len(got)}/{len(chunk)}")
        out.extend([float(x["elevation"] or 0.0) for x in got])
        if i + batch < len(coords):
            time.sleep(1.1)
    return out


# ---------------------------------------------------------------- 路径请求
def decode_polyline6(encoded: str):
    """Valhalla 返回的 shape 是 6 位精度 polyline，解成 [(lat, lon), ...]。"""
    coords, index, lat, lon = [], 0, 0, 0
    n = len(encoded)
    while index < n:
        for target in ("lat", "lon"):
            result, shift, b = 0, 0, 0x20
            while b >= 0x20:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if target == "lat":
                lat += delta
            else:
                lon += delta
        coords.append((lat / 1e6, lon / 1e6))
    return coords


def valhalla_route(waypoints, profile_cache_key: str | None = None):
    """用 Valhalla 的 pedestrian 配置在途经点之间找真实步行路径。

    为什么不用 OSRM：OSRM 的路网在衡山这类景区是断开的——祖师殿到高台寺
    直线 500 米，OSRM 会绕 55 km。Valhalla 对断头步道更宽容，同样两点给 1.24 km，
    大庙到祝融峰给 12.5 km（与实际情况相符）。
    """
    fp = hashlib.md5(repr([(round(w[1], 5), round(w[2], 5)) for w in waypoints]).encode()).hexdigest()[:12]
    key = f"{profile_cache_key or 'route'}-{fp}"
    cache_file = os.path.join(CACHE, f"{key}.json")
    if os.path.exists(cache_file):
        with open(cache_file, encoding="utf-8") as f:
            d = json.load(f)
    else:
        body = {
            "locations": [{"lat": w[1], "lon": w[2], "type": "break"} for w in waypoints],
            "costing": "pedestrian",
            "units": "kilometers",
            "shape_format": "polyline6",
            "directions_options": {"units": "kilometers"},
        }
        last = None
        for attempt in range(3):
            try:
                r = _session.post(
                    "https://valhalla1.openstreetmap.de/route", json=body, timeout=120
                )
                if r.status_code == 200:
                    d = r.json()
                    break
                last = RuntimeError(f"HTTP {r.status_code}: {r.text[:160]}")
            except Exception as exc:  # noqa: BLE001
                last = exc
            time.sleep(3 * (attempt + 1))
        else:
            raise RuntimeError(f"Valhalla 规划失败：{last}")

        os.makedirs(CACHE, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(d, f)

    trip = d.get("trip")
    if not trip:
        raise RuntimeError(f"Valhalla 无返回路线：{str(d)[:160]}")

    pts = []
    for leg in trip["legs"]:
        seg = decode_polyline6(leg["shape"])
        pts.extend(seg if not pts else seg[1:])

    # 逐段记录：路由长度 vs 两点直线距离，用来抓「某个点写偏导致绕路」
    legs = []
    for i, leg in enumerate(trip["legs"]):
        if i + 1 < len(waypoints):
            straight = haversine_m((waypoints[i][1], waypoints[i][2]),
                                   (waypoints[i + 1][1], waypoints[i + 1][2])) / 1000.0
        else:
            straight = 0.0
        legs.append((float(leg["summary"]["length"]), straight, waypoints[i][0]))

    return pts, float(trip["summary"]["length"]), legs


# ---------------------------------------------------------------- 统计
def build_profile(pts, eles):
    """带累计距离与海拔的轨迹点，做轻度平滑压掉 SRTM 噪声。"""
    # 5 点中值 + 3 点均值，去掉单点毛刺
    n = len(eles)
    sm = list(eles)
    for i in range(1, n - 1):
        sm[i] = sorted(eles[max(0, i - 2) : i + 3])[len(eles[max(0, i - 2) : i + 3]) // 2]
    smooth = []
    for i in range(n):
        lo, hi = max(0, i - 1), min(n, i + 2)
        smooth.append(sum(sm[lo:hi]) / (hi - lo))

    out, cum = [], 0.0
    for i, p in enumerate(pts):
        if i:
            cum += haversine_m(pts[i - 1], p)
        out.append([round(p[0], 5), round(p[1], 5), round(smooth[i], 1), round(cum / 1000.0, 4)])
    return out


def track_stats(prof, thresh: float = 3.0):
    """累计爬升/下降。用 3 m 死区过滤 SRTM 抖动，避免虚高。"""
    asc = desc = 0.0
    last = prof[0][2]
    for _, _, e, _ in prof[1:]:
        d = e - last
        if d > thresh:
            asc += d
            last = e
        elif d < -thresh:
            desc += -d
            last = e
    eles = [p[2] for p in prof]
    return {
        "distance_km": round(prof[-1][3], 2),
        "ascent_m": round(asc),
        "descent_m": round(desc),
        "ele_min": round(min(eles)),
        "ele_max": round(max(eles)),
    }


def simplify(prof, tol_m: float = 4.0):
    """Douglas-Peucker 简化，压体积又不改变形状（垂直方向容差 4 米）。

    上千个点时递归会超上限，这里显式把上限调高。
    """
    if len(prof) < 4:
        return prof
    sys.setrecursionlimit(max(10000, len(prof) * 4))

    def dp(lo, hi, keep):
        if hi <= lo + 1:
            return
        a, b = prof[lo], prof[hi]
        span = haversine_m(a[:2], b[:2]) or 1.0
        best, bi = -1.0, None
        for i in range(lo + 1, hi):
            p = prof[i]
            # 点到弦的距离（米）+ 海拔偏差
            t = (
                ((p[1] - a[1]) * (b[1] - a[1]) + (p[0] - a[0]) * (b[0] - a[0]))
                / (span * span)
                * 1.0
            )
            off = haversine_m(p[:2], [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t])
            score = max(off, abs(p[2] - (a[2] + (b[2] - a[2]) * t)))
            if score > best:
                best, bi = score, i
        if best > tol_m:
            keep.add(bi)
            dp(lo, bi, keep)
            dp(bi, hi, keep)

    keep = {0, len(prof) - 1}
    dp(0, len(prof) - 1, keep)
    return [prof[i] for i in sorted(keep)]


def sample_along(pts, step_m: float = 45.0):
    """按距离重采样，避免 SRTM 查询点数爆炸，又能刻画剖面。"""
    out = [pts[0]]
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = haversine_m(a, b)
        if seg <= 0:
            continue
        acc += seg
        if acc >= step_m:
            out.append(b)
            acc = 0.0
    if out[-1] != pts[-1]:
        out.append(pts[-1])
    return out


def speed_profile(prof):
    """按 Tobler 徒步函数由坡度推速度，做两步路那种「速度—距离」图。"""
    out = []
    for a, b in zip(prof, prof[1:]):
        d = (b[3] - a[3]) * 1000.0
        if d < 1:
            continue
        grade = (b[2] - a[2]) / d
        grade = max(-0.5, min(0.5, grade))
        v = 6.0 * math.exp(-3.5 * abs(grade + 0.05))  # km/h
        out.append([round(b[3], 3), round(max(1.2, min(5.5, v)), 2)])
    return out


# ---------------------------------------------------------------- 主流程
def project_on_track(pt, pts, step=1):
    """把一个点投影到轨迹上，返回 (最近点索引, 距离米)。"""
    best, bi = 1e18, 0
    for i in range(0, len(pts), step):
        d = haversine_m(pt, pts[i])
        if d < best:
            best, bi = d, i
    # 在最近点附近再细扫一遍
    for i in range(max(0, bi - step), min(len(pts), bi + step + 1)):
        d = haversine_m(pt, pts[i])
        if d < best:
            best, bi = d, i
    return bi, best


def build_one(cfg, write=True):
    """只沿着「必经点」规划路径；其余地名投影到轨迹上做标注点。

    为什么这么改：半山亭、南天门、观景台这类地名在全国有几十个同名点，
    硬当必经点会让 OSRM 绕出几倍的冤枉路（衡山曾绕出 58 km）。
    正确做法是走真实的登山主路径，再把沿途地名贴到最近的位置上——
    两步路的「标注点」也是这么来的。
    """
    name = cfg["name"]
    raw = []
    for i, w in enumerate(cfg["waypoints"]):
        if isinstance(w, dict):
            raw.append(
                dict(name=w["name"], lat=float(w["lat"]), lon=float(w["lon"]),
                     snap=w.get("snap"), r=w.get("r", 0.03), idx=i)
            )
        else:
            raw.append(dict(name=w[0], lat=float(w[1]), lon=float(w[2]), snap=None, r=0.03, idx=i))

    from osm_lookup import load_index, resolve  # noqa: PLC0415

    from osm_lookup import _dist_km  # noqa: PLC0415

    index = load_index()
    target = cfg.get("peak_m")
    for w in raw:
        la2, lo2, how = resolve(
            w["name"], (w["lat"], w["lon"]), index, prefer_peak=(w["snap"] == "peak")
        )
        if w["snap"] == "peak":
            # 只有 OSM 的峰顶坐标海拔够高才信；否则用目标海拔去搜真正的山顶
            use_osm = False
            for c in index.get(w["name"], []):
                if c.get("kind") != "peak" or c.get("lat") is None:
                    continue
                if _dist_km((w["lat"], w["lon"]), (c["lat"], c["lon"])) > 6:
                    continue
                if not target or (c.get("ele") and c["ele"] >= target * 0.85):
                    la2, lo2 = c["lat"], c["lon"]
                    how = f"OSM peak {c['ele'] or '?'}m"
                    use_osm = True
                    break
            if not use_osm:
                # 由近及远：先在手写坐标附近 3 km 内找，找不到才扩到 9 km。
                # 范围开太大容易把隔壁山头当成本峰（丹霞山曾因此跑到 8 km 外）。
                pick = None
                for radius in (0.028, 0.06, 0.10):
                    la3, lo3, ele = find_peak_target(w["lat"], w["lon"], target or 1000, max_r=radius)
                    if not target or ele >= target * 0.82:
                        pick = (la3, lo3, ele)
                        break
                    pick = pick or (la3, lo3, ele)
                la3, lo3, ele = pick
                how = f"SRTM 搜索峰顶 {ele:.0f}m"
                la2, lo2 = la3, lo3
        w["lat"], w["lon"], w["how"] = la2, lo2, how

    # Valhalla 对山地步道更宽容，全部途经点都作为必经点走一遍，
    # 这样「中间经过哪些地方」是真实走过的，不是投影出来的。
    must = raw
    labels = []

    if cfg.get("verbose"):
        for w in raw:
            tag = "必经" if w in must else "标注"
            print(f"      [{tag}] {w['name']}: {w['how']}")

    wps = [(w["name"], w["lat"], w["lon"]) for w in must]
    t0 = time.time()
    pts, dist, legs = valhalla_route(wps, profile_cache_key=cfg["id"])

    # 海拔：沿轨迹等距采样，再插值回每个点
    samples = sample_along(pts, step_m=cfg.get("step_m", 45.0))
    _t = time.time()
    eles = elevations([(p[0], p[1]) for p in samples])
    _t_ele = time.time() - _t

    full, si = [], 0
    cum_samples = [0.0]
    for a, b in zip(samples, samples[1:]):
        cum_samples.append(cum_samples[-1] + haversine_m(a, b))
    cum_pts = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum_pts.append(cum_pts[-1] + haversine_m(a, b))
    for c in cum_pts:
        while si < len(cum_samples) - 2 and cum_samples[si + 1] < c:
            si += 1
        d0 = cum_samples[si]
        d1 = cum_samples[si + 1] if si + 1 < len(cum_samples) else cum_samples[si]
        t = 0.0 if d1 == d0 else (c - d0) / (d1 - d0)
        full.append(eles[si] + (eles[si + 1] - eles[si]) * max(0.0, min(1.0, t)))

    prof = build_profile(pts, full)
    stats = track_stats(prof)

    # 质量闸门
    straight = sum(haversine_m((a[1], a[2]), (b[1], b[2])) for a, b in zip(wps, wps[1:]))
    ratio = stats["distance_km"] * 1000.0 / max(1.0, straight)
    problems = []
    if ratio > 3.0:
        problems.append(f"绕行 {ratio:.1f}×直线")
    # 单段绕行：某两个途经点之间走了 4 倍以上直线距离，基本是坐标写偏
    for length, straight, nm in legs:
        if straight > 0.3 and length / straight > 5.0 and length > 4.0:
            problems.append(f"{nm} 一段绕 {length / straight:.1f}×")
            break
    if stats["distance_km"] < 0.6:
        problems.append("轨迹过短")
    if target and target >= 600 and stats["ele_max"] < target * 0.80:
        problems.append(f"最高点 {stats['ele_max']:.0f}m 远低于主峰 {target}m")
    if target and target > 600 and stats["distance_km"] < 3.0:
        problems.append("爬升路线不足 3km")
    reliable = not problems

    # 标注点：投影到轨迹，离得太远的丢弃（说明是另一个同名地点）
    out_wps, dropped = [], []
    for w in must:
        i, d = project_on_track((w["lat"], w["lon"]), pts)
        out_wps.append({"name": w["name"], "lat": round(w["lat"], 5), "lon": round(w["lon"], 5),
                        "km": prof[i][3], "ele": prof[i][2]})
    for w in labels:
        i, d = project_on_track((w["lat"], w["lon"]), pts)
        if d <= 700:
            out_wps.append({"name": w["name"], "lat": round(pts[i][0], 5),
                            "lon": round(pts[i][1], 5), "km": prof[i][3], "ele": prof[i][2]})
        else:
            dropped.append(f"{w['name']}({d/1000:.1f}km)")
    out_wps.sort(key=lambda x: x["km"])

    doc = {
        "id": cfg["id"],
        "name": name,
        "provider": "OSRM foot (OpenStreetMap paths) + SRTM 30m elevation",
        "built": time.strftime("%Y-%m-%d"),
        "points": simplify(prof),
        "waypoints": out_wps,
        "dropped_labels": dropped,
        "speed": speed_profile(prof),
        "stats": stats,
        "reliable": reliable,
        "quality_note": "；".join(problems),
    }

    mark = "" if reliable else "  ✗ " + "；".join(problems)
    print(
        f"  {cfg['id']:24} {stats['distance_km']:6.2f} km  爬升{stats['ascent_m']:5} m  "
        f"海拔{stats['ele_min']:4}-{stats['ele_max']:4} m  点{len(doc['points']):4}  "
        f"标注{len(out_wps)}{mark}"
    )

    if not reliable:
        return doc, [("unreliable", 0)]

    if write:
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, f"{cfg['id']}.json"), "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    return doc, []


def write_csv():
    """按清单 + 已生成轨迹，重写 data/hiking_routes.csv。

    里程、爬升一律取轨迹实测值，保证「列表里写的」和「地图上画的」一致。
    """
    import csv

    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from routes_manifest import ROUTES  # noqa: PLC0415

    rows = []
    for cfg in ROUTES:
        fn = os.path.join(OUT, f"{cfg['id']}.json")
        if not os.path.exists(fn):
            continue
        with open(fn, encoding="utf-8") as f:
            doc = json.load(f)
        w0 = cfg["waypoints"][0]
        la, lo = (w0["lat"], w0["lon"]) if isinstance(w0, dict) else (w0[1], w0[2])
        rows.append(
            {
                "track_id": cfg["id"],
                "name": cfg["name"],
                "province": cfg["province"],
                "city": cfg["city"],
                "type": cfg["type"],
                "lon": round(float(lo), 5),
                "lat": round(float(la), 5),
                "distance_km": doc["stats"]["distance_km"],
                "ascent_m": doc["stats"]["ascent_m"],
                "ele_max": doc["stats"]["ele_max"],
                "n_points": len(doc["points"]),
                "n_waypoints": len(doc["waypoints"]),
                "difficulty": cfg["difficulty"],
                "days": cfg["days"],
                "best_season": cfg["best_season"],
                "desc": cfg["desc"],
                "heat": cfg["heat"],
            }
        )

    fn = os.path.join(ROOT, "data", "hiking_routes.csv")
    with open(fn, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: -r["heat"]))
    print(f"已写 {fn}：{len(rows)} 条")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="只构建 id 或名称包含该字符串的路线")
    ap.add_argument("--verify", action="store_true", help="只校验，不写文件")
    ap.add_argument("--list", action="store_true", help="列出已构建的轨迹")
    ap.add_argument("--verbose", action="store_true", help="打印每个途经点的定位依据")
    ap.add_argument("--fresh", action="store_true", help="忽略已有缓存，全部重算")
    ap.add_argument("--csv", action="store_true", help="只按已有轨迹重写 hiking_routes.csv")
    args = ap.parse_args()

    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from routes_manifest import ROUTES  # noqa: E402

    if args.csv:
        write_csv()
        return

    if args.list:
        if os.path.isdir(OUT):
            for f in sorted(os.listdir(OUT)):
                print(f)
        return

    if args.fresh and os.path.isdir(CACHE):
        for f in os.listdir(CACHE):
            if f.endswith(".json"):
                os.remove(os.path.join(CACHE, f))
    todo = [r for r in ROUTES if not args.only or args.only in r["id"] or args.only in r["name"]]
    if args.verbose:
        todo = [dict(r, verbose=True) for r in todo]
    print(f"待构建 {len(todo)} 条\n")
    bad = 0
    for cfg in todo:
        try:
            _, snap = build_one(cfg, write=not args.verify)
            if snap:
                bad += 1
        except Exception as exc:  # noqa: BLE001
            bad += 1
            print(f"  {cfg['id']:24} 失败：{type(exc).__name__} {str(exc)[:160]}")
    print(f"\n不合格/失败 {bad} 条 / 共 {len(todo)} 条")
    if not args.only and not args.verify:
        write_csv()


if __name__ == "__main__":
    main()
