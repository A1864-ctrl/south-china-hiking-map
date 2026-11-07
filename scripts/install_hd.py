# -*- coding: utf-8 -*-
"""把 pick 出的高清候选覆盖到 public/photos/gal/，统一 3:2 / 1400px。

python scripts/install_hd.py
"""
import json
import os

from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'public', 'photos', 'gal')
m = json.load(open(os.path.join(ROOT, 'scripts', 'hd_cand.json'), encoding='utf-8'))

# 人工复核后的指定候选（未列出的按标题命中 + 分数择优）
OVERRIDE = {
    'gal-r20.jpg': 1,   # 阳明山：原 #0 是钢笔手绘，换云海实拍
    'gal-s12.jpg': 2,   # 白云山：原 #0 主体是城市天际线，换山林视角
    'gal-r11.jpg': 1,   # 排牙山：原 #0 带贴纸文字，换岩石山脊
    'gal-s42.jpg': 5,   # 黑麋峰：换分辨率最高的一张
}

report = []
for f, v in sorted(m.items()):
    name = v['names'][0]
    cands = sorted(v['cands'], key=lambda c: -c['score'])
    if not cands:
        print('!! 无候选', f, name)
        continue
    if f in OVERRIDE:
        pick = cands[OVERRIDE[f]]
    else:
        key = name.replace('·', '').replace(' ', '')[:3]
        hit = [c for c in cands if any(ch in c['title'] for ch in key)]
        pick = (hit or cands)[0]

    im = Image.open(os.path.join(ROOT, pick['path'])).convert('RGB')
    aw, ah = im.size
    tw, th = aw, aw / 1.5
    if th > ah:
        th = ah
        tw = th * 1.5
    x0 = (aw - tw) / 2.0
    y0 = (ah - th) * 0.5
    im = im.crop((int(x0), int(y0), int(x0 + tw), int(y0 + th)))
    w = min(1500, im.width)
    im = im.resize((w, int(round(w / 1.5))), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=0.7, percent=48, threshold=3))
    im.save(os.path.join(OUT, f), 'JPEG', quality=92, optimize=True, progressive=True)
    report.append({'file': f, 'name': name, 'size': im.size, 'title': pick['title'],
                   'src': pick['src']})
    print('%-12s %-14s %sx%s  %s' % (f, name, im.size[0], im.size[1], pick['title'][:30]))

json.dump(report, open(os.path.join(ROOT, 'scripts', 'hd_installed.json'), 'w',
                       encoding='utf-8'), ensure_ascii=False, indent=1)
print('安装', len(report), '张')
