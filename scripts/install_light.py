# -*- coding: utf-8 -*-
"""把抓到的日落 / 夜景候选安装到 public/photos/light/，并生成 lightPhoto.js。

- 每个景点优先用自己那几张（按画面尺寸、按时段契合度排序）
- 没有的时段退到「同城统一」的城市级图，前端图注会写明是同城
"""
import json
import os
import re

from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = os.path.join(ROOT, 'scripts', 'light_cand.json')
OUT = os.path.join(ROOT, 'public', 'photos', 'light')
JS = os.path.join(ROOT, 'src', 'data', 'lightPhoto.js')

os.makedirs(OUT, exist_ok=True)
man = json.load(open(MAN, encoding='utf-8'))


def score(c, slot):
    s = min(c['w'], 2000) / 100.0
    if slot == 'night':
        s += max(0, 90 - c['l']) / 6.0           # 越暗越像夜拍
    else:
        s += max(0, min(c['wx'], 40)) / 4.0      # 越暖越像黄昏
    s -= abs(c['w'] / c['h'] - 1.5) * 6
    return s


def install(c):
    im = Image.open(os.path.join(ROOT, c['path'])).convert('RGB')
    aw, ah = im.size
    tw, th = aw, aw / 1.5
    if th > ah:
        th = ah
        tw = th * 1.5
    x0, y0 = (aw - tw) / 2, (ah - th) / 2
    im = im.crop((int(x0), int(y0), int(x0 + tw), int(y0 + th)))
    w = min(1200, im.width)
    im = im.resize((w, int(round(w / 1.5))), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=0.7, percent=48, threshold=3))
    return im


own = {}
city_best = {}
for key, v in man.items():
    slot = v['slot']
    cands = [c for c in v['cands'] if c['w'] >= 900]
    if not cands:
        continue
    best = max(cands, key=lambda c: score(c, slot))
    fn = '%03d-%s.jpg' % (v['idx'], slot)
    im = install(best)
    im.save(os.path.join(OUT, fn), 'JPEG', quality=86, optimize=True, progressive=True)
    own.setdefault(v['name'], {})[slot] = 'photos/light/' + fn
    # 城市级：该城所有点位里最契合这个时段的一张
    cur = city_best.get(v['city'], {}).get(slot)
    if cur is None or score(best, slot) > cur[0]:
        city_best.setdefault(v['city'], {})[slot] = (score(best, slot), 'photos/light/' + fn, v['name'])

lines = ['// 每个景点自己的黄昏 / 夜景实拍（按景点名索引），来源为网络公开图源（小红书 / 抖音 博主图）',
         'export const lightPhoto = {']
for name in sorted(own):
    parts = ', '.join("%s: '%s'" % (k, own[name][k]) for k in ('sunset', 'night') if k in own[name])
    lines.append("  '%s': { %s }," % (name, parts))
lines.append('}')
lines.append('')
lines.append('// 城市级兜底：该点位缺某个时段时，用同城最贴合那个时段的一张')
lines.append('export const lightCity = {')
for city in sorted(city_best):
    parts = ', '.join(
        "%s: { src: '%s', from: '%s' }" % (k, city_best[city][k][1], city_best[city][k][2])
        for k in ('sunset', 'night') if k in city_best[city])
    lines.append("  '%s': { %s }," % (city, parts))
lines.append('}')
lines.append('')
open(JS, 'w', encoding='utf-8').write('\n'.join(lines))

miss = [n for n in own if len(own[n]) < 2]
print('安装点位', len(own), '文件', len(own) * 1)
print('缺一个时段的点位', len(miss), miss[:12])
print('城市兜底', {c: list(v) for c, v in city_best.items()})
