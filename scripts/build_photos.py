#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并候选清单，下载图片，生成 spotWiki.js 清单。
优先 Wikipedia 条目插图，其次 Commons 搜索里标题包含景点名的图。
"""
import json, os, re, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'public', 'photos')
UA = 'SouthChinaTrails/2.0 (personal hiking project)'
os.makedirs(OUT, exist_ok=True)

spots = json.load(open(os.path.join(ROOT, 'scripts', 'spot_list.json'), encoding='utf-8'))
c1 = json.load(open(os.path.join(ROOT, 'scripts', 'photo_candidates.json'), encoding='utf-8'))
c2 = json.load(open(os.path.join(ROOT, 'scripts', 'photo_candidates2.json'), encoding='utf-8'))

BAD = re.compile(r'(酒店|hotel|resort|民宿|遗址|售票|停车场|车站|站厅|站台|施工|楼盘|办公室|office)', re.I)


def base(n):
    n = n.split('·')[0]
    for s in ['国家森林公园', '森林公园', '风景区', '景区', '旅游区', '竹筏', '漂流', '骑行', '观景台']:
        n = n.replace(s, '')
    return n.strip()


picks = {}
for s in spots:
    key = f'spot-{s["id"]}'
    b = base(s['name'])
    cands = []
    for p in (c2.get(key, {}).get('picks') or []):
        if p.get('from') == 'wikipedia' or not p.get('from'):
            cands.append((0, p))
    for p in (c1.get(key, {}).get('picks') or []):
        if b and b in p['title'] and not BAD.search(p['title']):
            cands.append((1, p))
    for p in (c2.get(key, {}).get('picks') or []):
        if b and b in p['title'] and not BAD.search(p['title']):
            cands.append((1, p))
    seen, final = set(), []
    for _, p in sorted(cands, key=lambda x: x[0]):
        if p['title'] in seen or BAD.search(p['title']):
            continue
        seen.add(p['title'])
        final.append(p)
    picks[key] = final[:2]

ok = 0
lines = ['// 自动生成：scripts/build_photos.py（图片来源 Wikipedia / Wikimedia Commons，署名与许可见条目页）',
         'export const spotPhotoFiles = {']
for s in spots:
    key = f'spot-{s["id"]}'
    files = []
    for i, p in enumerate(picks.get(key, [])):
        fn = f'{key}-{i + 1}.jpg'
        path = os.path.join(OUT, fn)
        if not (os.path.exists(path) and os.path.getsize(path) > 8000):
            try:
                req = urllib.request.Request(p['thumb'], headers={'User-Agent': UA})
                data = urllib.request.urlopen(req, timeout=45).read()
                if len(data) < 8000:
                    continue
                open(path, 'wb').write(data)
                time.sleep(0.25)
            except Exception as e:
                print('dl fail', fn, str(e)[:40], flush=True)
                continue
        ok += 1
        files.append('/photos/' + fn)
    if files:
        credit = (picks[key][0].get('artist') or 'Wikimedia')[:30].replace('"', '')
        lic = picks[key][0].get('license', '')
        lines.append('  "%s": { src: "%s", all: %s, title: "%s", credit: "%s", license: "%s", page: "%s" },' % (
            s['name'], files[0], json.dumps(files), (picks[key][0]['title'])[:60].replace('"', ''),
            credit, lic, picks[key][0].get('page') or ''))
lines.append('}')
open(os.path.join(ROOT, 'src', 'data', 'spotWiki.js'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('downloaded', ok, 'spots with photo', sum(1 for s in spots if picks.get(f'spot-{s["id"]}')))
