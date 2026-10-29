"""按名字在 OSM 里查真实坐标。

为什么需要：手工填山名坐标容易偏一两公里，路线就会绕远或缩短。
这里用 Overpass 一次性拉取华南（20-31°N, 105-121°E）全部具名峰顶、景点、
古迹、村镇，存成本地索引；之后按名字查表即可，不再联网。

索引文件 tools/.cache/osm_index.json 约 30 MB，不进 git。
重建：python tools/fetch_osm_index.py
"""

from __future__ import annotations

import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "tools", ".cache", "osm_index.json")

_index_cache = None


def load_index() -> dict:
    global _index_cache
    if _index_cache is None:
        if os.path.exists(INDEX):
            with open(INDEX, encoding="utf-8") as f:
                _index_cache = json.load(f)
        else:
            _index_cache = {}
    return _index_cache


def _dist_km(a, b) -> float:
    r = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def lookup(names, center=None, radius_deg=0.11):
    """兼容旧接口：直接从本地索引取候选。"""
    idx = load_index()
    return {n: idx.get(n, []) for n in dict.fromkeys(names) if n}


def _bonus(kind: str, prefer_peak: bool) -> float:
    k = (kind or "").lower()
    if k == "peak":
        return 3.0 if prefer_peak else -1.0
    if k in ("attraction", "viewpoint", "museum", "theme_park"):
        return 2.0
    if k in ("memorial", "monument", "castle", "fort"):
        return 1.2
    if k in ("village", "town", "hamlet", "suburb", "city"):
        return 0.8
    if k == "place_of_worship":
        return 0.5
    return 0.0


def resolve(name, hint, cache=None, prefer_peak=False, max_km=6.0):
    """在候选点里挑最可信的一个。返回 (lat, lon, 说明)。

    只按距离挑会踩坑：全国有几十个「凤凰山」「莲花山」，
    所以既要距离近，也要类型对（峰顶优先 peak）。
    """
    cands = (cache or load_index()).get(name, [])
    cands = [c for c in cands if c and c.get("lat") is not None]
    if not cands:
        return hint[0], hint[1], "OSM 无收录，用手写坐标"

    if prefer_peak:
        peaks = [c for c in cands if (c.get("kind") or "").lower() == "peak"]
        if peaks:
            cands = peaks

    def score(c):
        return _dist_km(hint, (c["lat"], c["lon"])) - _bonus(c.get("kind"), prefer_peak)

    cands.sort(key=score)
    best = cands[0]
    d = _dist_km(hint, (best["lat"], best["lon"]))
    if d > max_km:
        return hint[0], hint[1], f"最近同名点 {d:.1f} km（{best.get('kind')}），判定不符，用手写坐标"
    ele = f" {best['ele']:.0f}m" if best.get("ele") else ""
    return best["lat"], best["lon"], f"OSM {best.get('kind')}{ele} 偏移{d:.1f}km"
