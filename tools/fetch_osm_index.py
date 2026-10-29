"""一次性拉取华南 OSM 具名地物，建成按名字索引的本地坐标库。

为什么这么做：逐条路线查 Overpass 要发 45 个请求、被限流后跑一小时都不一定完；
一次拉全区域只要 1 个请求（约 7 分钟），之后按名字查表是毫秒级，且完全可复现。

覆盖范围：纬度 20-31°N、经度 105-121°E，含广东、湖南、江西、广西、福建西部。
"""

import json
import os
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tools", ".cache", "osm_index.json")
EP = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"

QUERY = """[out:json][timeout:240];
(
  node["natural"="peak"]["name"](20,105,31,121);
  node["tourism"~"attraction|viewpoint|museum|theme_park"]["name"](20,105,31,121);
  node["historic"~"memorial|monument|castle|fort"]["name"](20,105,31,121);
  node["place"~"village|town|hamlet|suburb"]["name"](20,105,31,121);
  node["amenity"="place_of_worship"]["name"](20,105,31,121);
);
out;"""


def main():
    s = requests.Session()
    s.trust_env = False
    s.headers.update({"User-Agent": "hiking-track-builder/1.0"})

    print("正在拉取 OSM 数据（约 5-8 分钟）…")
    t0 = time.time()
    r = s.post(EP, data={"data": QUERY}, timeout=600)
    r.raise_for_status()
    elements = r.json().get("elements", [])
    print(f"  收到 {len(elements)} 个元素，用时 {time.time() - t0:.0f}s")

    idx = {}
    for e in elements:
        tags = e.get("tags", {})
        nm = tags.get("name")
        if not nm or e.get("lat") is None:
            continue
        try:
            ele = float(str(tags.get("ele", "")).replace("m", "").strip())
        except ValueError:
            ele = None
        kind = (
            tags.get("natural")
            or tags.get("tourism")
            or tags.get("historic")
            or tags.get("place")
            or tags.get("amenity")
            or "?"
        )
        idx.setdefault(nm, []).append(
            {"lat": e["lat"], "lon": e["lon"], "ele": ele, "kind": kind}
        )

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False)
    peaks = sum(1 for v in idx.values() for c in v if c["kind"] == "peak")
    print(f"已写 {OUT}")
    print(f"  地名 {len(idx)} 个，其中峰顶 {peaks} 个，文件 {os.path.getsize(OUT) / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
