# -*- coding: utf-8 -*-
"""把 Photon 校正结果保守地写回 routes.js。

规则：
- 位移 ≤ 1200 m：直接采纳
- 位移 ≤ 3000 m 且 OSM 类型是 peak：也采纳
- 更大的位移不动（可能是同名异地）
按数值比对坐标，避免 29.35 与 29.350 这种写法差异导致匹配失败。
"""
import io, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'data', 'routes.js')
REP = os.path.join(ROOT, 'scripts', 'geocode_report.json')

r = json.load(io.open(REP, encoding='utf-8'))
ok = [x for x in r if x['moved_m'] <= 1200 or (x['kind'] == 'peak' and x['moved_m'] <= 3000)]
print('采纳', len(ok), '/', len(r))

s = io.open(SRC, encoding='utf-8').read()
ROUTE_START = re.compile(r"\{\s*\n\s*name: '")
PT = re.compile(r"\{ name: '([^']+)', lat: ([\d.]+), lng: ([\d.]+)")

done = 0

def block_bounds(s, route):
    i = s.index("name: '%s'" % route)
    m = ROUTE_START.search(s, i + 8)
    return i, (m.start() if m else len(s))

for x in sorted(ok, key=lambda z: -z['moved_m']):
    if x['route'] not in s:
        continue
    a, b = block_bounds(s, x['route'])
    blk = s[a:b]
    target = None
    for p in PT.finditer(blk):
        if p.group(1) != x['pt']:
            continue
        if abs(float(p.group(2)) - x['from'][0]) < 1e-6 and abs(float(p.group(3)) - x['from'][1]) < 1e-6:
            target = p
            break
    if not target:
        continue
    repl = "{ name: '%s', lat: %.5f, lng: %.5f" % (x['pt'], x['to'][0], x['to'][1])
    s = s[:a + target.start()] + repl + s[a + target.end():]
    done += 1

io.open(SRC, 'w', encoding='utf-8').write(s)
print('写入关键点', done)
