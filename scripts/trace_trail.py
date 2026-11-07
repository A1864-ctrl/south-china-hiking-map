# -*- coding: utf-8 -*-
"""沿高德瓦片上可见的步道/小路走线，替换「关键点直连」。

原理：高德路网瓦片（style=8）里，公路与登山步道都渲染成浅白细线，底图是淡绿。
把近白像素当「可走线」，水面给高代价，用最小代价路径逐段穿过去，
再简化成折线并转回 WGS84 —— 比直线贴合地形得多。

python scripts/trace_trail.py 武功山·金顶穿越
输出 scripts/traces/<name>.json  {"path": [[lat,lng]...], "stat": {...}}
"""
import io
import json
import math
import os
import sys
import urllib.request

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import check_water as cw  # noqa: E402

TILE_DIR = os.path.join(ROOT, 'scripts', '_tiles')
OUT_DIR = os.path.join(ROOT, 'scripts', 'traces')
os.makedirs(TILE_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

MAX_PX = 1700          # 单段画布上限（控制内存）
MARGIN_M = 260         # 段外扩，给绕行留余量


def gcj2wgs(lat, lng):
    """GCJ-02 → WGS84，迭代反解（误差 < 0.5 m）。"""
    wlat, wlng = lat, lng
    for _ in range(6):
        glat, glng = cw.wgs2gcj(wlat, wlng)
        wlat += lat - glat
        wlng += lng - glng
    return wlat, wlng


def tile_px(x, y, z):
    p = os.path.join(TILE_DIR, 't_%d_%d_%d.png' % (z, x, y))
    if os.path.exists(p):
        return Image.open(p).convert('RGB')
    u = 'https://webrd0%d.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x=%d&y=%d&z=%d' % (
        1 + (x + y) % 4, x, y, z)
    try:
        req = urllib.request.Request(u, headers={
            'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.amap.com/'})
        d = urllib.request.urlopen(req, timeout=25).read()
        im = Image.open(io.BytesIO(d)).convert('RGB')
        im.save(p)
        return im
    except Exception:
        return Image.new('RGB', (256, 256), (207, 232, 167))


def px_of(lat, lng, z):
    """WGS84 → 该缩放级别下的整幅像素坐标（lonlat_to_pixel 返回的是瓦片单位）。"""
    x, y = cw.lonlat_to_pixel(*cw.wgs2gcj(lat, lng), z)
    return x * 256.0, y * 256.0


def pick_zoom(lat_a, lng_a, lat_b, lng_b):
    """让整段跨度落在 MAX_PX 像素内，取最大缩放级别。"""
    for z in (16, 15, 14, 13, 12):
        ax, ay = px_of(lat_a, lng_a, z)
        bx, by = px_of(lat_b, lng_b, z)
        if max(abs(bx - ax), abs(by - ay)) <= MAX_PX:
            return z
    return 12


def build_canvas(lat_a, lng_a, lat_b, lng_b, z):
    from concurrent.futures import ThreadPoolExecutor
    pts = [px_of(lat_a, lng_a, z), px_of(lat_b, lng_b, z)]
    mpp = 156543.0 * math.cos(math.radians(lat_a)) / (2 ** z)
    mx = MARGIN_M / mpp
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0 = int(math.floor((min(xs) - mx) / 256.0)); x1 = int(math.ceil((max(xs) + mx) / 256.0))
    y0 = int(math.floor((min(ys) - mx) / 256.0))
    y1 = int(math.ceil((max(ys) + mx) / 256.0))
    W, H = (x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    jobs = [(tx, ty) for tx in range(x0, x1 + 1) for ty in range(y0, y1 + 1)]
    with ThreadPoolExecutor(max_workers=12) as ex:
        ims = list(ex.map(lambda p: tile_px(p[0], p[1], z), jobs))
    for (tx, ty), im in zip(jobs, ims):
        arr[(ty - y0) * 256:(ty - y0 + 1) * 256,
            (tx - x0) * 256:(tx - x0 + 1) * 256] = np.asarray(im)
    return arr, x0 * 256, y0 * 256


def cost_of(arr):
    a = arr.astype(np.int16)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mx_ = np.maximum(np.maximum(r, g), b)
    mn_ = np.minimum(np.minimum(r, g), b)
    white = (mn_ > 228) & ((mx_ - mn_) < 16)          # 步道 / 广场（纯白）
    road = (r > 236) & (g > 224) & (b < 214) & (b > 150)   # 省道等黄白路面色
    water = (b > r + 25) & (b > 195)                   # 水面
    green = (g > r) & (g > b) & (g > 150)              # 林地底图
    cost = np.full(arr.shape[:2], 30.0, dtype=np.float32)
    cost[green] = 28.0
    cost[water] = 300.0
    cost[white] = 1.0
    cost[road] = 7.0        # 公路让一让，优先走登山步道
    return cost


def trace_segment(lat_a, lng_a, lat_b, lng_b):
    z = pick_zoom(lat_a, lng_a, lat_b, lng_b)
    arr, ox, oy = build_canvas(lat_a, lng_a, lat_b, lng_b, z)
    cost = cost_of(arr)
    ax, ay = px_of(lat_a, lng_a, z)
    bx, by = px_of(lat_b, lng_b, z)
    s = (int(ay - oy), int(ax - ox))
    e = (int(by - oy), int(bx - ox))
    H, W = cost.shape
    s = (min(max(s[0], 0), H - 1), min(max(s[1], 0), W - 1))
    e = (min(max(e[0], 0), H - 1), min(max(e[1], 0), W - 1))

    from skimage.graph import route_through_array
    path, w = route_through_array(cost, s, e, fully_connected=True, geometric=True)
    path = np.array(path, dtype=np.float64)
    # 简化
    from skimage.measure import approximate_polygon
    simp = approximate_polygon(path, tolerance=1.6)
    out = []
    for py, px in simp:
        fx = (px + ox) / 256.0
        fy = (py + oy) / 256.0
        lat, lng = cw.pixel_to_lonlat(fx, fy, z) if hasattr(cw, 'pixel_to_lonlat') else (None, None)
        if lat is None:
            # 反解墨卡托
            n = 2.0 ** z
            lng_g = fx / n * 360.0 - 180.0
            lat_g = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * fy / n))))
            lat, lng = gcj2wgs(lat_g, lng_g)
        out.append((round(lat, 5), round(lng, 5)))
    return out, z, len(path)


def hav(a, b):
    R = 6371.0
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    x = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def plen(p):
    return sum(hav(p[i], p[i + 1]) for i in range(len(p) - 1))


def trace_route(pts):
    full = []
    zs = []
    for i in range(len(pts) - 1):
        seg, z, npx = trace_segment(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
        zs.append(z)
        full.extend(seg[:-1] if i < len(pts) - 2 else seg)
    return full, zs


def load_routes():
    src = open(os.path.join(ROOT, 'src', 'data', 'routes.js'), encoding='utf-8').read()
    out = {}
    for m in __import__('re').finditer(r"\n  \{\n    name: '([^']+)', province:", src):
        st = m.start(); en = src.find('\n  },', st)
        block = src[st:en]
        pts = [(float(a), float(b)) for a, b in __import__('re').findall(
            r"name: '[^']+', lat: ([\d.]+), lng: ([\d.]+)", block)]
        dm = __import__('re').search(r'distance: ([\d.]+)', block)
        out[m.group(1)] = {'pts': pts, 'distance': float(dm.group(1)) if dm else 0}
    return out


if __name__ == '__main__':
    routes = load_routes()
    names = [a for a in sys.argv[1:] if not a.startswith('-')] or list(routes)[:2]
    for name in names:
        if name not in routes:
            print('未找到', name)
            continue
        r = routes[name]
        path, zs = trace_route(r['pts'])
        L = plen(path)
        straight = plen(r['pts'])
        stat = {'name': name, 'zoom': zs, 'pts': len(r['pts']), 'nodes': len(path),
                'straight': round(straight, 2), 'traced': round(L, 2),
                'stated': r['distance'], 'ratio': round(L / r['distance'], 2) if r['distance'] else 0}
        json.dump({'path': path, 'stat': stat},
                  open(os.path.join(OUT_DIR, name.replace('/', '_') + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False)
        print('%-22s 直线%6.1f 追踪%6.1f 标注%6.1f 比%.2f 点%4d z%s'
              % (name, straight, L, r['distance'], stat['ratio'], len(path), zs))
