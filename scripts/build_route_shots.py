# -*- coding: utf-8 -*-
"""为每条徒步路线组装 6-8 张实拍：本线封面 + 最近点位的四季 / 晚霞 / 夜景。

不新抓图（图源今天被封），全部复用已人工核验过的图库：
  routeGallery  → 本线封面
  seasonPhoto   → 春 / 夏 / 秋 / 冬
  lightPhoto    → 晚霞 / 夜景
标注来源：同名点位 / 附近实拍（含距离）/ 仅本线。
"""
import json
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(p):
    return open(os.path.join(ROOT, p), encoding='utf-8').read()


routes_src = read('src/data/routes.js')
season_src = read('src/data/seasonPhoto.js')
light_src = read('src/data/lightPhoto.js')
gal_src = read('src/data/gallery.js')
spots_src = read('src/data/spots.js')

# 路线：名字 + 起点坐标
route_rows = []
for m in re.finditer(r"name: '([^']+)', province: '([^']+)', city: '([^']+)', terrain: '([^']+)'.*?center: \[([\d.]+), ([\d.]+)\]",
                     routes_src, re.S):
    route_rows.append({'name': m.group(1), 'province': m.group(2), 'city': m.group(3),
                       'terrain': m.group(4), 'lat': float(m.group(5)), 'lng': float(m.group(6))})

# 景点坐标
spot_pos = {}
for m in re.finditer(r"^\s*\['([^']+)', '([^']+)', '([^']+)', '([^']+)', \d+, '[^']*', '[^']*', '[^']*', \[[^\]]*\], ([\d.]+), ([\d.]+)\]",
                     spots_src, re.M):
    spot_pos[m.group(1)] = (float(m.group(5)), float(m.group(6)))


def parse_map(src, key):
    out = {}
    for m in re.finditer(r"'([^']+)': \{ ([^}]*) \}", src):
        body = m.group(2)
        d = {}
        for k, v in re.findall(r"(\S+): '([^']+)'", body):
            d[k] = v
        out[m.group(1)] = d
    return out


season = parse_map(season_src, 'seasonPhoto')
light = parse_map(light_src, 'lightPhoto')

# 路线封面
route_gal = {}
for m in re.finditer(r"'([^']+)': '(gal-r\d+\.jpg)'", gal_src):
    route_gal[m.group(1)] = 'photos/gal/' + m.group(2)

SEASON_LABEL = {'春': '春 · 3-5月', '夏': '夏 · 6-9月', '秋': '秋 · 10-11月', '冬': '冬 · 12-2月'}
LIGHT_LABEL = {'sunset': '晚霞 · 日落前 40 分钟', 'night': '夜色 · 亮灯后'}


def hav(a, b):
    R = 6371.0
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    d = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(d))


out = {}
for r in route_rows:
    shots = []
    cover = route_gal.get(r['name'])
    if cover:
        shots.append({'k': '本线', 'src': cover, 'label': '本线实拍 · 图集原图',
                      'title': r['name'], 'note': f"{r['city']} · {r['terrain']}"})

    # 找最近的、有四季图的点位
    best, bd = None, 1e9
    for name, pos in spot_pos.items():
        if name not in season:
            continue
        d = hav((r['lat'], r['lng']), pos)
        if d < bd:
            best, bd = name, d

    if best and bd <= 160:
        same = best == r['name'] or r['name'].split('·')[0] in best or best.startswith(r['name'].split('·')[0])
        tag = '同名点位' if same else f'附近实拍 · {best}（{bd:.0f}km）'
        s = season.get(best, {})
        for k in ('春', '夏', '秋', '冬'):
            if s.get(k):
                shots.append({'k': k, 'src': s[k], 'label': f'{SEASON_LABEL[k]} · {tag}',
                              'title': f'{r["name"]} · {k}', 'note': f'取景自 {best}'})
        lp = light.get(best, {})
        for slot in ('sunset', 'night'):
            if lp.get(slot):
                shots.append({'k': '晚霞' if slot == 'sunset' else '夜色', 'src': lp[slot],
                              'label': f'{LIGHT_LABEL[slot]} · {tag}',
                              'title': f'{r["name"]} · {"晚霞" if slot == "sunset" else "夜色"}',
                              'note': f'取景自 {best}'})
    out[r['name']] = shots

lines = ['// 每条路线的影像集：本线封面 + 最近点位的四季/晚霞/夜景（附来源标注）',
         '// 由 scripts/build_route_shots.py 生成，图片均来自已核验的图库',
         'export const routeShots = {']
for name, shots in out.items():
    items = ', '.join(
        "{ k: %r, src: %r, label: %r, title: %r, note: %r }" % (s['k'], s['src'], s['label'], s['title'], s['note'])
        for s in shots)
    lines.append("  %r: [%s]," % (name, items))
lines.append('}')
lines.append('')

open(os.path.join(ROOT, 'src', 'data', 'routeShots.js'), 'w', encoding='utf-8').write('\n'.join(lines))
counts = [len(v) for v in out.values()]
print('路线', len(out), '影像总数', sum(counts), '每线', min(counts), '-', max(counts))
print('只有封面的路线', [k for k, v in out.items() if len(v) <= 1])
