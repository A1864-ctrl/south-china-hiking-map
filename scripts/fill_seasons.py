# -*- coding: utf-8 -*-
"""补齐四季里仍然空着的 10 个（景点, 季节），换更短/更少广告味的词。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_seasons as fs

fs.MIN_W = 900
MAN = os.path.join(fs.ROOT, 'scripts', 'season_cand.json')
m = json.load(open(MAN, encoding='utf-8'))

FIX = {
    ('相公山观景台', '夏'): '相公山 漓江 云海',
    ('十里画廊骑行', '秋'): '阳朔 十里画廊 秋',
    ('石门国家森林公园', '春'): '从化石门 花海',
    ('猛洞河漂流', '春'): '猛洞河 峡谷',
    ('猛洞河漂流', '夏'): '猛洞河 漂流',
    ('猛洞河漂流', '秋'): '猛洞河 峡谷',
    ('猛洞河漂流', '冬'): '猛洞河 峡谷',
    ('天子山', '夏'): '张家界 天子山 云海',
    ('张家界大峡谷', '冬'): '张家界大峡谷 雪',
    ('巽寮湾', '夏'): '巽寮湾 海滩',
}

for (name, season), word in FIX.items():
    key = next((k for k, v in m.items() if v['name'] == name and v['season'] == season), None)
    if not key:
        print('找不到', name, season)
        continue
    got = []
    for c in fs.search(word):
        if len(got) >= 3:
            break
        dst = os.path.join(fs.OUT_DIR, '%03d_%s_g%d.jpg' % (m[key]['idx'], season, len(got)))
        try:
            size = fs.download(c['u'], dst)
        except Exception:
            continue
        if not size:
            continue
        rel = os.path.relpath(dst, fs.ROOT).replace(os.sep, '/')
        got.append({'path': rel, 'w': size[0], 'h': size[1], 'title': c['title'],
                    'score': fs.pick_score(c, name, season, word.split()[-1]), 'src': c['u']})
    if got:
        m[key]['cands'] = got
        m[key]['word'] = word
    print(name, season, word, '->', len(got), [g['title'][:22] for g in got], flush=True)

json.dump(m, open(MAN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('done')
