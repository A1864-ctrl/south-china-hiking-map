# -*- coding: utf-8 -*-
"""对四季抓取里「没结果」或「标题不含景点名」的条目，用短名 + 季节重抓。"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_seasons as fs

ROOT = fs.ROOT
MAN = os.path.join(ROOT, 'scripts', 'season_cand.json')

# 短名：去掉 · 后的补充说明
SHORT = {
    '漓江·杨堤至兴坪': '漓江', '东江湖·小东江': '东江湖', '张家界国家森林公园': '张家界',
    '坐龙峡': '坐龙峡 溪谷', '洋湖湿地': '洋湖湿地公园', '从化溪头村': '溪头村 从化',
    '华南植物园': '华南植物园 落羽杉', '石门国家森林公园': '石门国家森林公园 红叶',
    '湖南博物院': '湖南省博物馆', '凤凰古城': '凤凰古城', '天子山': '张家界天子山',
    '罗浮山': '罗浮山', '象头山': '象头山', '相公山观景台': '相公山 漓江',
    '猫儿山': '猫儿山 兴安', '金鞭溪': '张家界金鞭溪', '莽山': '莽山 郴州',
    '天门山': '张家界天门山',
}
# 季节专属替换词（南方不常见雪，用雾/落羽杉/红叶等真实特征）
SEASON_WORD = {
    ('冬', '华南植物园'): '落羽杉',
    ('冬', '石门国家森林公园'): '红叶',
    ('冬', '从化溪头村'): '梅花',
    ('冬', '莽山'): '雾凇',
    ('秋', '华南植物园'): '落羽杉',
    ('春', '象头山'): '春色',
    ('春', '天子山'): '云海',
}

fs.MIN_W = 900


def todo(man):
    out = []
    for k, v in man.items():
        if not v['cands']:
            out.append(k)
            continue
        key = v['name'].replace('·', ' ').split()[0][:2]
        if not any(key in c['title'] for c in v['cands']):
            out.append(k)
    return sorted(out)


def work(key):
    man = json.load(open(MAN, encoding='utf-8'))
    v = man[key]
    name, season = v['name'], v['season']
    base = SHORT.get(name, name.replace('·', ' ').split()[0])
    word = SEASON_WORD.get((season, name)) or ('%s %s' % (base, dict(fs.SEASONS)[season]))
    cands = fs.search(word)
    got = []
    for c in cands:
        if len(got) >= fs.PER_FILE:
            break
        dst = os.path.join(fs.OUT_DIR, '%03d_%s_r%d.jpg' % (v['idx'], season, len(got)))
        try:
            size = fs.download(c['u'], dst)
        except Exception:
            continue
        if not size:
            continue
        got.append({'path': os.path.relpath(dst, ROOT).replace('\\', '/'),
                    'w': size[0], 'h': size[1], 'title': c['title'],
                    'score': fs.pick_score(c, base, season, word.split()[-1]), 'src': c['u']})
    print('%s %s %s | %s -> %d' % (v['idx'], name, season, word, len(got)), flush=True)
    return key, got, word


def main():
    man = json.load(open(MAN, encoding='utf-8'))
    keys = todo(man)
    print('待重抓', len(keys))
    results = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        for key, got, word in ex.map(work, keys):
            results[key] = (got, word)
    for key, (got, word) in results.items():
        if got:
            man[key]['cands'] = got
            man[key]['word'] = word
    json.dump(man, open(MAN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    left = [k for k in keys if not man[k]['cands']]
    print('仍缺', len(left), left)


if __name__ == '__main__':
    main()
