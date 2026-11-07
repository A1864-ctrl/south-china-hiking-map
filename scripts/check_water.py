# -*- coding: utf-8 -*-
"""检查路线关键点是否落在水面（海/湖/江）上。

思路：把 WGS84 点转 GCJ02，算高德瓦片 x/y/z，取 256px 瓦片，看像素颜色。
高德标准底图水面是浅蓝（R 低、B 高、G 居中），陆地是米白/浅绿/灰。
"""
import os, io, json, math, re, sys, time, hashlib
import urllib.request
from PIL import Image

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_tiles')
os.makedirs(CACHE, exist_ok=True)

A = 6378245.0
EE = 0.00669342162296594323
PI = math.pi


def out_of_china(lat, lng):
    return lng < 72.004 or lng > 137.8347 or lat < 0.8293 or lat > 55.8271


def _tlat(x, y):
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += ((20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0) / 3.0
    ret += ((20.0 * math.sin(y * PI) + 40.0 * math.sin((y / 3.0) * PI)) * 2.0) / 3.0
    ret += ((160.0 * math.sin((y / 12.0) * PI) + 320 * math.sin((y * PI) / 30.0)) * 2.0) / 3.0
    return ret


def _tlng(x, y):
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += ((20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0) / 3.0
    ret += ((20.0 * math.sin(x * PI) + 40.0 * math.sin((x / 3.0) * PI)) * 2.0) / 3.0
    ret += ((150.0 * math.sin((x / 12.0) * PI) + 300.0 * math.sin((x / 30.0) * PI)) * 2.0) / 3.0
    return ret


def wgs2gcj(lat, lng):
    if out_of_china(lat, lng):
        return lat, lng
    dlat = _tlat(lng - 105.0, lat - 35.0)
    dlng = _tlng(lng - 105.0, lat - 35.0)
    rad = lat / 180.0 * PI
    magic = math.sin(rad)
    magic = 1 - EE * magic * magic
    sm = math.sqrt(magic)
    dlat = (dlat * 180.0) / (((A * (1 - EE)) / (magic * sm)) * PI)
    dlng = (dlng * 180.0) / ((A / sm) * math.cos(rad) * PI)
    return lat + dlat, lng + dlng


def lonlat_to_pixel(lat, lng, z):
    n = 2 ** z
    x = (lng + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / PI) / 2.0 * n
    return x, y


def fetch_tile(x, y, z):
    name = '%d_%d_%d.png' % (z, x, y)
    p = os.path.join(CACHE, name)
    if os.path.exists(p):
        return Image.open(p).convert('RGB')
    url = 'https://webrd0%s.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x=%d&y=%d&z=%d' % (
        (x + y) % 4 + 1, x, y, z)
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = urllib.request.urlopen(req, timeout=15).read()
            open(p, 'wb').write(data)
            return Image.open(io.BytesIO(data)).convert('RGB')
        except Exception:
            time.sleep(0.8)
    return None


def is_water(rgb):
    r, g, b = rgb
    # 高德水面：浅蓝 (大约 199,226,244) 到深一点的 (170,210,240)
    return b > 200 and b - r > 18 and b - g > 8 and r < 215 and g < 235


def sample(lat, lng, z=16, k=4):
    """取该点周围 (2k+1)^2 像素的中位数颜色 —— 单点容易被 POI 图标、路名骗到。"""
    glat, glng = wgs2gcj(lat, lng)
    fx, fy = lonlat_to_pixel(glat, glng, z)
    tx, ty = int(fx), int(fy)
    px, py = int((fx - tx) * 256), int((fy - ty) * 256)
    im = fetch_tile(tx, ty, z)
    if im is None:
        return None
    rs, gs, bs = [], [], []
    for dx in range(-k, k + 1):
        for dy in range(-k, k + 1):
            x = min(255, max(0, px + dx))
            y = min(255, max(0, py + dy))
            r, g, b = im.getpixel((x, y))
            rs.append(r); gs.append(g); bs.append(b)
    rs.sort(); gs.sort(); bs.sort()
    m = len(rs) // 2
    return (rs[m], gs[m], bs[m])


def parse_routes():
    src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'data', 'routes.js')
    s = io.open(src, encoding='utf-8').read()
    out = []
    for blk in re.finditer(r"\{\s*\n\s*name: '([^']+)'[\s\S]*?pts: \[([\s\S]*?)\n    \],", s):
        name = blk.group(1)
        pts = []
        for m in re.finditer(r"\{ name: '([^']+)', lat: ([\d.]+), lng: ([\d.]+), ele: (\d+)", blk.group(2)):
            pts.append({'name': m.group(1), 'lat': float(m.group(2)), 'lng': float(m.group(3)), 'ele': int(m.group(4))})
        out.append({'name': name, 'pts': pts})
    return out


if __name__ == '__main__':
    # 自检：一个明确的海面点和一个明确的山地点
    print('海面自检', sample(22.455, 114.575), '山地点自检', sample(29.317, 110.435))
    rs = parse_routes()
    print('路线数', len(rs), '关键点总数', sum(len(r['pts']) for r in rs))
    bad = []
    for r in rs:
        hits = []
        for p in r['pts']:
            rgb = sample(p['lat'], p['lng'])
            if rgb and is_water(rgb):
                hits.append((p['name'], rgb))
        if hits:
            bad.append((r['name'], hits))
    print('落入水面的路线', len(bad))
    for name, hits in bad:
        print(' -', name, ':', ', '.join('%s%s' % (h[0], h[1]) for h in hits))
