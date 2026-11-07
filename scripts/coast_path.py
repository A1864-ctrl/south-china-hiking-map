# -*- coding: utf-8 -*-
"""沿着陆地走线：贪心绕开水面，生成可绘制的 path。

比「把落水点推到最近陆地」更接近真实走法：每 90 m 走一步，
正前方是水就左右偏转找最近的可行方向，于是海岸线会自然贴着岸走。
"""
import io, json, math, os, re, sys
from check_water import sample, is_water
from fix_paths import hav, offset, bearing, rdp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'data', 'routes.js')
PT = re.compile(r"\{ name: '([^']+)', lat: ([\d.]+), lng: ([\d.]+)")
ROUTE_START = re.compile(r"\{\s*\n\s*name: '")

STEP = 90.0
BENDS = [0, 12, -12, 24, -24, 36, -36, 48, -48, 60, -60, 75, -75, 90, -90, 110, -110, 135, -135, 160, -160]


def water(p):
    rgb = sample(p[0], p[1])
    return bool(rgb and is_water(rgb))


def walk(a, b, max_steps=900):
    """从 a 走到 b，遇到水面就偏转。"""
    out = [a]
    cur = a
    for _ in range(max_steps):
        d = hav(cur, b)
        if d <= STEP:
            out.append(b)
            return out
        br = bearing(cur, b)
        moved = False
        for delta in BENDS:
            ang = (br + delta) % 360
            # 偏转越大，单步越短，避免绕出去太远
            step = STEP * (1 if abs(delta) <= 24 else 0.7 if abs(delta) <= 60 else 0.5)
            cand = offset(cur, step, ang)
            if water(cand):
                continue
            # 不要往回走：新点到终点的距离必须缩短，或至少不明显变远
            if hav(cand, b) > d + STEP * 0.6:
                continue
            cur = cand
            out.append(cur)
            moved = True
            break
        if not moved:
            # 卡住了（比如被水包围），直接连到终点，由后面的抽稀兜底
            out.append(b)
            return out
    out.append(b)
    return out


def parse_routes():
    s = io.open(SRC, encoding='utf-8').read()
    out = []
    for m in ROUTE_START.finditer(s):
        a = m.end()
        name = s[a:s.index("'", a)]
        i = s.index("name: '%s'" % name)
        j = ROUTE_START.search(s, i + 8)
        blk = s[i:(j.start() if j else len(s))]
        pts = [(float(p.group(2)), float(p.group(3))) for p in PT.finditer(blk)]
        out.append({'name': name, 'pts': pts})
    return out


def main():
    rs = parse_routes()
    result = {}
    for r in rs:
        if not r['pts'] or len(r['pts']) < 2:
            continue
        path = [r['pts'][0]]
        for i in range(len(r['pts']) - 1):
            seg = walk(r['pts'][i], r['pts'][i + 1])
            path.extend(seg[1:])
        simplified = rdp(path, 55)
        bad = sum(1 for p in rdp(path, 30) if water(p))
        result[r['name']] = [[round(p[0], 5), round(p[1], 5)] for p in simplified]
        if bad:
            print('  %-22s 仍有 %d 个水面采样点，节点 %d' % (r['name'], bad, len(simplified)))
    io.open(os.path.join(ROOT, 'scripts', 'paths.json'), 'w', encoding='utf-8').write(
        json.dumps(result, ensure_ascii=False))
    print('生成', len(result), '条 path')
    patch(result)


def patch(result):
    s = io.open(SRC, encoding='utf-8').read()
    for name, path in result.items():
        i = s.index("name: '%s'" % name)
        a = s.index('pts: [', i)
        k = s.index('\n    ],', a)
        end = k + len('\n    ],')
        body = ',\n    path: ' + json.dumps(path, separators=(',', ':'))
        # 已有 path：替换到该行结束
        tail = s[end:end + 12]
        if tail.strip().startswith(',') and 'path:' in s[end:end + 40]:
            e2 = s.index('\n', s.index('path:', end))
            s = s[:end] + body + s[e2:]
        else:
            s = s[:end] + body + s[end:]
    io.open(SRC, 'w', encoding='utf-8').write(s)
    print('已写入 routes.js')


if __name__ == '__main__':
    main()
