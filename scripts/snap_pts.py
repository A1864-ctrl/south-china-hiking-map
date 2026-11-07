# -*- coding: utf-8 -*-
"""把仍然落在水面的关键点推到最近的陆地（就地改 routes.js）。

一次只改一个点，改完重新扫，避免字符串偏移错位。
"""
import io, os, re
from check_water import sample, is_water
from fix_paths import offset

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'data', 'routes.js')
PT = re.compile(r"\{ name: '([^']+)', lat: ([\d.]+), lng: ([\d.]+)")
ROUTE_START = re.compile(r"\{\s*\n\s*name: '")


def water(lat, lng):
    rgb = sample(lat, lng)
    return bool(rgb and is_water(rgb))


def nearest_land(lat, lng, max_m=520):
    for r in range(30, max_m + 1, 30):
        for b in range(0, 360, 15):
            q = offset((lat, lng), r, b)
            if not water(*q):
                return q
    return None


def block_of(s, route):
    i = s.index("name: '%s'" % route)
    nxt = ROUTE_START.search(s, i + 8)
    return i, (nxt.start() if nxt else len(s))


def scan(s):
    out = []
    for m in ROUTE_START.finditer(s):
        q1 = m.end()
        q2 = s.index("'", q1)
        route = s[q1:q2]
        a, b = block_of(s, route)
        for p in PT.finditer(s[a:b]):
            lat, lng = float(p.group(2)), float(p.group(3))
            if water(lat, lng):
                out.append((route, p.group(1), a + p.start(), a + p.end(), lat, lng))
    return out


def main():
    s = io.open(SRC, encoding='utf-8').read()
    changes = []
    for _ in range(60):
        bad = scan(s)
        if not bad:
            break
        route, pname, i, j, lat, lng = bad[0]
        q = nearest_land(lat, lng) or offset((lat, lng), 900, 0)
        s = s[:i] + ("{ name: '%s', lat: %.5f, lng: %.5f" % (pname, q[0], q[1])) + s[j:]
        changes.append((route, pname, lat, lng, q[0], q[1]))
    io.open(SRC, 'w', encoding='utf-8').write(s)
    print('修正关键点', len(changes))
    for c in changes:
        print('  %-18s %-10s %.4f,%.4f → %.4f,%.4f' % c)


if __name__ == '__main__':
    main()
