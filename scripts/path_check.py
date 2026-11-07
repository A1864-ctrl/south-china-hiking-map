# -*- coding: utf-8 -*-
"""轨迹几何自检：路径是否经过全部关键点 / 折线里程与标注里程是否一致。"""
import json
import math
import re
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, 'src', 'data', 'routes.js'), encoding='utf-8').read()


def hav(a, b):
    R = 6371.0
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    d = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(d))


def seg_dist(p, a, b):
    """点到线段的近似距离（km），用等距投影。"""
    kx = 111.32 * math.cos(math.radians(p[0]))
    ky = 110.57
    px, py = p[1] * kx, p[0] * ky
    ax, ay = a[1] * kx, a[0] * ky
    bx, by = b[1] * kx, b[0] * ky
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


routes = []
for m in re.finditer(r"\n  \{\n    name: '([^']+)', province:", src):
    start = m.start()
    end = src.find('\n  },', start)
    if end < 0:
        end = src.find('\n  }\n', start)
    routes.append((m.group(1), src[start:end]))

print('解析路线', len(routes))
rows = []
for name, block in routes:
    dm = re.search(r'distance: ([\d.]+)', block)
    stated = float(dm.group(1)) if dm else 0
    pts = [(float(a), float(b)) for a, b in re.findall(
        r"name: '[^']+', lat: ([\d.]+), lng: ([\d.]+)", block)]
    pm = re.search(r'path: (\[\[.*?\]\])', block, re.S)
    path = json.loads(pm.group(1)) if pm else []
    if not path:
        rows.append((name, stated, 0, 0, '无 path', len(pts)))
        continue
    km = sum(hav(path[i], path[i + 1]) for i in range(len(path) - 1))
    dev = 0
    for p in pts:
        d = min((seg_dist(p, path[i], path[i + 1]) for i in range(len(path) - 1)), default=99)
        dev = max(dev, d)
    ratio = km / stated if stated else 0
    flag = []
    if ratio < 0.82:
        flag.append('里程偏短')
    if ratio > 1.5:
        flag.append('里程偏长')
    if dev > 0.45:
        flag.append('偏点%.2fkm' % dev)
    rows.append((name, stated, round(km, 1), round(ratio, 2), ' '.join(flag) or 'OK', len(pts), round(dev, 2)))

bad = [r for r in rows if r[4] != 'OK']
print('问题路线', len(bad), '/', len(rows))
for r in sorted(bad, key=lambda r: r[3] if isinstance(r[3], float) else 9):
    print('%-22s 标注%6.1f 折线%6.1f 比%.2f 点%2d 偏差%.2f  %s' % (r[0], r[1], r[2], r[3], r[5], r[6], r[4]))
json.dump(rows, open(os.path.join(ROOT, 'scripts', 'path_check.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
