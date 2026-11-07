# -*- coding: utf-8 -*-
"""按人工挑选结果替换四季图里的问题图。"""
import json
import os

from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, 'scripts', 'season_fix.json')
PUB = os.path.join(ROOT, 'public')

PICK = {
    ('七娘山', '秋'): 0, ('七娘山', '冬'): 1,
    ('人才公园', '秋'): 1,
    ('便江', '春'): 0, ('便江', '夏'): 1, ('便江', '秋'): 2, ('便江', '冬'): 1,
    ('南昆山', '冬'): 0,
    ('大梅沙', '夏'): 3, ('大梅沙', '冬'): 0,
    ('太平老街', '春'): 0, ('太平老街', '秋'): 1,
    ('张家界国家森林公园', '冬'): 0,
    ('杨梅坑', '夏'): 0, ('杨梅坑', '冬'): 0,
    ('梧桐山', '秋'): 1,
    ('橘子洲', '夏'): 2,
    ('永庆坊', '夏'): 2,
    ('海珠湖', '秋'): 3,
    ('深圳湾公园', '冬'): 2,
    ('湖南博物院', '冬'): 2,
    ('白云山', '冬'): 2,
    ('矮寨大桥', '冬'): 2,
    ('苏仙岭', '秋'): 0,
    ('莲花山', '冬'): 1,
    ('观澜湖', '夏'): 2,
    ('边城茶峒', '秋'): 0,
    ('陈家祠', '春'): 0, ('陈家祠', '夏'): 1, ('陈家祠', '秋'): 2, ('陈家祠', '冬'): 3,
    ('飞天山', '春'): 1, ('飞天山', '秋'): 2, ('飞天山', '冬'): 0,
    ('黑排角', '冬'): 1,
    ('黑麋峰', '秋'): 3, ('黑麋峰', '冬'): 0,
}

fix = json.load(open(FIX, encoding='utf-8'))
done = 0
for (name, season), idx in sorted(PICK.items()):
    v = fix.get('%s|%s' % (name, season))
    if not v or not v['cands']:
        print('跳过', name, season)
        continue
    c = v['cands'][min(idx, len(v['cands']) - 1)]
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
    im = im.filter(ImageFilter.UnsharpMask(radius=0.7, percent=46, threshold=3))
    f = v['cands'][0].get('file')
    if not f:
        print('跳过(无季节文件)', name, season)
        continue
    out = os.path.join(PUB, f.replace('/', os.sep))
    im.save(out, 'JPEG', quality=90, optimize=True, progressive=True)
    done += 1
    print('替换', name, season, '->', v['cands'][0]['file'], im.size, c['title'][:24])
print('共替换', done, '张')
