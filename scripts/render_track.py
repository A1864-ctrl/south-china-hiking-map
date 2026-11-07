# -*- coding: utf-8 -*-
"""离线渲染轨迹：拼高德瓦片 + 画折线，用于目检轨迹是否贴着地形走。

python scripts/render_track.py 幕阜山 衡山·经典登顶线 ...
输出 shots/trk_<序号>.png
"""
import io
import json
import math
import os
import re
import sys
import urllib.request

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import check_water as cw  # noqa: E402

Z = 14
TILE = os.path.join(ROOT, 'scripts', '_tiles')
os.makedirs(TILE, exist_ok=True)


def tile(x, y):
    p = os.path.join(TILE, 'r_%d_%d_%d.png' % (Z, x, y))
    if os.path.exists(p):
        return Image.open(p)
    u = 'https://webrd0%d.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x=%d&y=%d&z=%d' % (
        1 + (x + y) % 4, x, y, Z)
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.amap.com/'})
        d = urllib.request.urlopen(req, timeout=20).read()
        im = Image.open(io.BytesIO(d)).convert('RGB')
        im.save(p)
        return im
    except Exception:
        return Image.new('RGB', (256, 256), (235, 235, 230))


def to_px(lat, lng, x0, y0):
    glat, glng = cw.wgs2gcj(lat, lng)
    fx, fy = cw.lonlat_to_pixel(glat, glng, Z)
    return (fx - x0) * 256, (fy - y0) * 256


def render(name, path, pts, out, pad=36):
    fx = [cw.lonlat_to_pixel(*cw.wgs2gcj(p[0], p[1]), Z) for p in path]
    allp = fx + [cw.lonlat_to_pixel(*cw.wgs2gcj(p[0], p[1]), Z) for p in pts]
    minx = min(p[0] for p in allp); maxx = max(p[0] for p in allp)
    miny = min(p[1] for p in allp); maxy = max(p[1] for p in allp)
    x0 = int(math.floor(minx)) - 1; y0 = int(math.floor(miny)) - 1
    x1 = int(math.ceil(maxx)) + 1; y1 = int(math.ceil(maxy)) + 1
    W = (x1 - x0 + 1) * 256; H = (y1 - y0 + 1) * 256
    canvas = Image.new('RGB', (W, H))
    for tx in range(x0, x1 + 1):
        for ty in range(y0, y1 + 1):
            canvas.paste(tile(tx, ty), ((tx - x0) * 256, (ty - y0) * 256))
    d = ImageDraw.Draw(canvas)
    xy = [to_px(p[0], p[1], x0, y0) for p in path]
    d.line(xy, fill=(230, 60, 40), width=4, joint='curve')
    for i, p in enumerate(pts):
        x, y = to_px(p[0], p[1], x0, y0)
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(30, 90, 200), outline=(255, 255, 255), width=2)
    # 裁到轨迹范围
    xs = [p[0] for p in xy]; ys = [p[1] for p in xy]
    box = (max(0, int(min(xs)) - pad), max(0, int(min(ys)) - pad),
           min(W, int(max(xs)) + pad), min(H, int(max(ys)) + pad))
    canvas = canvas.crop(box)
    w = min(1100, canvas.width)
    canvas = canvas.resize((w, int(canvas.height * w / canvas.width)), Image.LANCZOS)
    canvas.save(out, 'JPEG', quality=86)
    return canvas.size


def load_routes():
    src = open(os.path.join(ROOT, 'src', 'data', 'routes.js'), encoding='utf-8').read()
    out = {}
    for m in re.finditer(r"\n  \{\n    name: '([^']+)', province:", src):
        st = m.start()
        en = src.find('\n  },', st)
        block = src[st:en]
        pts = [(float(a), float(b)) for a, b in re.findall(
            r"name: '[^']+', lat: ([\d.]+), lng: ([\d.]+)", block)]
        pm = re.search(r'path: (\[\[.*?\]\])', block, re.S)
        path = [tuple(p) for p in json.loads(pm.group(1))] if pm else pts
        out[m.group(1)] = (path, pts)
    return out


if __name__ == '__main__':
    routes = load_routes()
    names = [a for a in sys.argv[1:] if not a.startswith('-')] or list(routes)[:3]
    for i, n in enumerate(names):
        if n not in routes:
            print('未找到', n)
            continue
        path, pts = routes[n]
        out = os.path.join(ROOT, 'shots', 'trk_%02d.png' % i)
        size = render(n, path, pts, out)
        print('%-22s 点%4d %s' % (n, len(path), out), size)
