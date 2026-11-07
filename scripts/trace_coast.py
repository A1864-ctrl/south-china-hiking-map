# -*- coding: utf-8 -*-
"""海岸线路线专用：沿真实海岸线生成走线。

做法：以起终点连线为基准，在每个经度上从基准纬度附近向两侧搜索最近的陆地像素，
得到一条连续的海岸线；再用中值滤波压掉离岸小岛造成的毛刺。
"""
import io, json, math, os, re
from check_water import sample, is_water

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'data', 'routes.js')
PT = re.compile(r"\{ name: '([^']+)', lat: ([\d.]+), lng: ([\d.]+)")
ROUTE_START = re.compile(r"\{\s*\n\s*name: '")
TARGETS = ['东西冲海岸线', '大鹿港海岸线', '黑排角海岸线']


def water(p):
    rgb = sample(p[0], p[1])
    return bool(rgb and is_water(rgb))


def mainland_shore(lng, lat_lo, lat_hi, step=0.00025):
    """自南向北找「大陆岸线」：要求该点往北 150/300 m 也是陆地，排除离岸礁石。"""
    la = lat_lo
    while la <= lat_hi:
        if not water((la, lng)) and not water((la + 0.0014, lng)) and not water((la + 0.0028, lng)):
            return la
        la += step
    return None


def build(pts):
    lat_a, lng_a = pts[0]
    lat_b, lng_b = pts[-1]
    lo = min(lat_a, lat_b) - 0.02
    hi = max(lat_a, lat_b) + 0.02
    n = max(16, int(abs(lng_b - lng_a) * 111320 * math.cos(math.radians((lat_a + lat_b) / 2)) / 110))
    raw = []
    for i in range(n + 1):
        lng = lng_a + (lng_b - lng_a) * i / n
        la = mainland_shore(lng, lo, hi)
        if la is not None:
            raw.append((la, lng))
    if len(raw) < 8:
        return None
    # 中值滤波压毛刺
    out = []
    for i in range(len(raw)):
        w = sorted(p[0] for p in raw[max(0, i - 2):min(len(raw), i + 3)])
        out.append((w[len(w) // 2], raw[i][1]))
    keep = [out[0]]
    for p in out[1:-1]:
        if abs(p[0] - keep[-1][0]) > 0.0003 or abs(p[1] - keep[-1][1]) > 0.002:
            keep.append(p)
    keep.append(out[-1])
    return keep


def patch(s, name, path):
    i = s.index("name: '%s'" % name)
    a = s.index('pts: [', i)
    k = s.index('\n    ],', a)
    acc = s.index('access:', k)
    body = '\n    ],\n    path: ' + json.dumps([[round(x, 5), round(y, 5)] for x, y in path], separators=(',', ':')) + ',\n    '
    return s[:k] + body + s[acc:]


def main():
    s = io.open(SRC, encoding='utf-8').read()
    for name in TARGETS:
        i = s.index("name: '%s'" % name)
        m = ROUTE_START.search(s, i + 8)
        blk = s[i:(m.start() if m else len(s))]
        pts = [(float(p.group(2)), float(p.group(3))) for p in PT.finditer(blk)]
        path = build(pts)
        if not path:
            print('!! 失败', name)
            continue
        bad = sum(1 for p in path if water(p))
        s = patch(s, name, path)
        print('%-14s 节点 %2d，水面节点 %d' % (name, len(path), bad))
    io.open(SRC, 'w', encoding='utf-8').write(s)


if __name__ == '__main__':
    main()
