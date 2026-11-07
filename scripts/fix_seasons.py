# -*- coding: utf-8 -*-
"""定向补抓几项季节图（关键词带城市，避免串到外地图）。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_seasons as fs

fs.MIN_W = 900
MAN = os.path.join(fs.ROOT, 'scripts', 'season_cand.json')
m = json.load(open(MAN, encoding='utf-8'))

FIX = {
    '017|冬': '从化 流溪香雪 梅花',
    '018|冬': '从化石门国家森林公园 红叶',
    '053|春': '张家界 天子山 春',
    '065|春': '惠州 象头山 森林',
    '065|秋': '惠州 象头山',
    '070|冬': '莽山 雾凇 宜章',
}

for k, word in FIX.items():
    v = m[k]
    cs = fs.search(word)
    got = []
    for c in cs:
        if len(got) >= 3:
            break
        dst = os.path.join(fs.OUT_DIR, '%03d_%s_f%d.jpg' % (v['idx'], v['season'], len(got)))
        try:
            size = fs.download(c['u'], dst)
        except Exception:
            continue
        if not size:
            continue
        rel = os.path.relpath(dst, fs.ROOT).replace(os.sep, '/')
        got.append({'path': rel, 'w': size[0], 'h': size[1], 'title': c['title'],
                    'score': fs.pick_score(c, word.split()[0], v['season'], word.split()[-1]),
                    'src': c['u']})
    if got:
        v['cands'] = got
        v['word'] = word
    print(k, v['name'], v['season'], '|', word, '->', len(got),
          [g['title'][:22] for g in got], flush=True)

json.dump(m, open(MAN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('done')
