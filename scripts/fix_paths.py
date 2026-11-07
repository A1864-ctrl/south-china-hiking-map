# -*- coding: utf-8 -*-
"""把每条路线的走线落到陆地上，并加密成可直接绘制的 path。

流程：关键点 → 每 110 m 加密 → 逐点判定水面（高德瓦片颜色）→
落水的点向最近陆地推（先垂直方向，再扩圈）→ RDP 抽稀 → 写回 routes.js 的 path 字段。
"""
import io, json, math, os, re, sys
from check_water import sample, is_water

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'data', 'routes.js')


def hav(a, b):
    R = 6371000.0
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    d = 2 * R * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
    return d


def densify(pts, step=110.0):
    out = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        d = hav(a, b)
        n = max(1, int(round(d / step)))
        for j in range(n):
            t = j / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    out.append(tuple(pts[-1]))
    return out


def offset(pt, meters, bearing_deg):
    R = 6371000.0
    br = math.radians(bearing_deg)
    la1, lo1 = math.radians(pt[0]), math.radians(pt[1])
    dr = meters / R
    la2 = math.asin(math.sin(la1) * math.cos(dr) + math.cos(la1) * math.sin(dr) * math.cos(br))
    lo2 = lo1 + math.atan2(math.sin(br) * math.sin(dr) * math.cos(la1), math.cos(dr) - math.sin(la1) * math.sin(la2))
    return (math.degrees(la2), math.degrees(lo2))


def water(pt):
    rgb = sample(pt[0], pt[1])
    return bool(rgb and is_water(rgb))


def snap(pt, hint_dir=None, max_m=420):
    """把落水点推到最近的陆地。hint_dir 是建议方位（垂直于前进方向）"""
    best = None
    order = []
    if hint_dir is not None:
        order = [(hint_dir + d) % 360 for d in (0, 25, -25, 50, -50, 80, -80, 110, -110, 150, -150, 180)]
    else:
        order = list(range(0, 360, 20))
    for r in range(25, max_m + 1, 25):
        for b in order:
            c = offset(pt, r, b)
            if not water(c):
                d = r
                if best is None or d < best[0]:
                    best = (d, c)
                break
        if best:
            break
    return best[1] if best else pt


def bearing(a, b):
    la1, la2 = math.radians(a[0]), math.radians(b[0])
    dlo = math.radians(b[1] - a[1])
    y = math.sin(dlo) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dlo)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def rdp(points, eps_m):
    if len(points) < 3:
        return points
    # 用米制近似做 Douglas-Peucker
    def d2(p, a, b):
        ax, ay = a[1] * 111320 * math.cos(math.radians(a[0])), a[0] * 110540
        bx, by = b[1] * 111320 * math.cos(math.radians(b[0])), b[0] * 110540
        px, py = p[1] * 111320 * math.cos(math.radians(p[0])), p[0] * 110540
        dx, dy = bx - ax, by - ay
        if dx == dy == 0:
            return math.hypot(px - ax, py - ay)
        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    def rec(pts):
        if len(pts) < 3:
            return pts
        a, b = pts[0], pts[-1]
        idx, dmax = 0, 0
        for i in range(1, len(pts) - 1):
            d = d2(pts[i], a, b)
            if d > dmax:
                idx, dmax = i, d
        if dmax > eps_m:
            l = rec(pts[:idx + 1])
            r = rec(pts[idx:])
            return l[:-1] + r
        return [a, b]

    return rec(points)


def parse_routes():
    s = io.open(SRC, encoding='utf-8').read()
    out = []
    for blk in re.finditer(r"\{\s*\n\s*name: '([^']+)'[\s\S]*?pts: \[([\s\S]*?)\n    \],", s):
        name = blk.group(1)
        pts = []
        for m in re.finditer(r"\{ name: '([^']+)', lat: ([\d.]+), lng: ([\d.]+), ele: (\d+)", blk.group(2)):
            pts.append((float(m.group(2)), float(m.group(3))))
        out.append({'name': name, 'pts': pts})
    return out


SAFE_WATER = ('漂流', )  # 本来就该在水上的路线，不做避让


def main():
    apply = '--apply' in sys.argv
    rs = parse_routes()
    result = {}
    report = []
    for r in rs:
        if any(k in r['name'] for k in SAFE_WATER):
            continue
        ctrl = r['pts']
        dense = densify(ctrl, 100)
        fixed = []
        moved = 0
        for i, p in enumerate(dense):
            if not water(p):
                fixed.append(p)
                continue
            nxt = dense[min(i + 2, len(dense) - 1)]
            prv = dense[max(i - 2, 0)]
            br = bearing(prv, nxt)
            q = snap(p, hint_dir=br + 90 if i % 2 == 0 else br - 90)
            if q != p:
                moved += 1
            fixed.append(q)
        # 平滑一次，避免锯齿
        sm = []
        for i in range(len(fixed)):
            a = fixed[max(0, i - 1)]
            b = fixed[min(len(fixed) - 1, i + 1)]
            sm.append(((a[0] + 2 * fixed[i][0] + b[0]) / 4, (a[1] + 2 * fixed[i][1] + b[1]) / 4))
        sm[0], sm[-1] = fixed[0], fixed[-1]
        path = rdp(sm, 45)
        # 复核
        bad = sum(1 for p in densify(path, 60) if water(p))
        result[r['name']] = [[round(p[0], 5), round(p[1], 5)] for p in path]
        if moved or bad:
            report.append((r['name'], moved, bad, len(path)))
    io.open(os.path.join(ROOT, 'scripts', 'paths.json'), 'w', encoding='utf-8').write(
        json.dumps(result, ensure_ascii=False))
    print('已生成 path', len(result), '条')
    for x in report:
        print('  %-24s 挪动 %3d 点, 剩余水面 %2d, 节点 %3d' % x)
    if apply:
        patch(result)


def patch(result):
    s = io.open(SRC, encoding='utf-8').read()
    for name, path in result.items():
        key = "name: '%s'" % name
        i = s.index(key)
        j = s.index('pts: [', i)
        k = s.index('\n    ],', j)
        body = ',\n    path: ' + json.dumps(path, separators=(',', ':'))
        # 已有 path 则替换
        tail = s[k + len('\n    ],'):k + len('\n    ],') + 40]
        if tail.strip().startswith(',\n    path:'):
            end = s.index('\n', s.index('path:', k))
            s = s[:k + len('\n    ],')] + body + s[end:]
        else:
            s = s[:k + len('\n    ],')] + body + s[k + len('\n    ],'):]
    io.open(SRC, 'w', encoding='utf-8').write(s)
    print('已写入 routes.js')


if __name__ == '__main__':
    main()
