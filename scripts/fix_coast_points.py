# -*- coding: utf-8 -*-
"""手工校正一批「原来填在海里」的关键点（坐标取自 OSM / Photon 实测 POI）。"""
import io, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'data', 'routes.js')

# route -> [(point, lat, lng)]
FIX = {
    '东西冲海岸线': [
        ('东涌沙滩', 22.49253, 114.57745),
        ('穿鼻岩', 22.47772, 114.55821),
        ('崖壁拉绳段', 22.47540, 114.54600),
        ('西涌沙滩', 22.47637, 114.53098)
    ],
    '大鹿港海岸线': [
        ('西涌起步点', 22.47637, 114.53098),
        ('大鹿港湾', 22.49520, 114.52520),
        ('岩壁攀爬段', 22.50420, 114.53060),
        ('东涌出口', 22.49253, 114.57745)
    ],
    '七娘山': [
        ('地质公园登山口', 22.53180, 114.55120),
        ('一号平台', 22.52840, 114.54760),
        ('七娘山顶', 22.52509, 114.54380),
        ('杨梅坑', 22.54749, 114.56638)
    ],
    '马峦山瀑布群': [
        ('小梅沙', 22.60319, 114.32244),
        ('马峦山瀑布', 22.62000, 114.33500),
        ('老围村', 22.63200, 114.33300),
        ('大梅沙', 22.60215, 114.30530)
    ],
    '黑排角海岸线': [
        ('平海古城', 22.64620, 114.72800),
        ('黑排角礁石段', 22.65000, 114.77500),
        ('高洋尾沙滩', 22.65300, 114.80600)
    ],
    '万时山': [
        ('万时山顶', 25.19300, 113.76200)
    ],
    '岳麓山·桃花岭穿越': [
        ('梅溪湖', 28.19102, 112.88783)
    ]
}

PT = re.compile(r"\{ name: '([^']+)', lat: ([\d.]+), lng: ([\d.]+)")
ROUTE_START = re.compile(r"\{\s*\n\s*name: '")

s = io.open(SRC, encoding='utf-8').read()
n = 0
for route, pts in FIX.items():
    m = ROUTE_START.search(s, s.index("name: '%s'" % route) - 6)
    start = s.index("name: '%s'" % route)
    nxt = ROUTE_START.search(s, start + 8)
    a, b = start, (nxt.start() if nxt else len(s))
    blk = s[a:b]
    for pname, lat, lng in pts:
        pm = re.search(r"\{ name: '%s', lat: [\d.]+, lng: [\d.]+" % re.escape(pname), blk)
        if not pm:
            print('未找到', route, pname)
            continue
        blk = blk[:pm.start()] + ("{ name: '%s', lat: %.5f, lng: %.5f" % (pname, lat, lng)) + blk[pm.end():]
        n += 1
    s = s[:a] + blk + s[b:]

io.open(SRC, 'w', encoding='utf-8').write(s)
print('改写关键点', n)
