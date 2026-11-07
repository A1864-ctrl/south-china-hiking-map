# -*- coding: utf-8 -*-
"""为 53 条徒步路线抓「四季 + 晚霞 + 夜景」实拍，供详情页做影像栏。

优先复用同名景点的四季图（已有 304 张），缺的再按「路线名 + 季节/时段」检索。
输出 scripts/route_shot_cand.json + scripts/_rshots/*.jpg
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_seasons as fs

ROOT = fs.ROOT
OUT = os.path.join(ROOT, 'scripts', '_rshots')
MAN = os.path.join(ROOT, 'scripts', 'route_shot_cand.json')
os.makedirs(OUT, exist_ok=True)
fs.MIN_W = 1000

SLOTS = [
    ('spring', '春天'), ('summer', '夏天'), ('autumn', '秋天'), ('winter', '冬天'),
    ('sunset', '日落 晚霞'), ('night', '夜景 星空')
]


def load_routes():
    src = open(os.path.join(ROOT, 'src', 'data', 'routes.js'), encoding='utf-8').read()
    rows = re.findall(r"name: '([^']+)', province: '([^']+)', city: '([^']+)', terrain: '([^']+)'", src)
    return [{'id': i + 1, 'name': n, 'province': p, 'city': c, 'terrain': t}
            for i, (n, p, c, t) in enumerate(rows)]


def tone(path):
    im = Image.open(path).convert('RGB').resize((160, 107), Image.BILINEAR)
    px = list(im.getdata())
    n = len(px)
    l = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in px) / n
    w = sum(r - b for r, g, b in px) / n
    return round(l, 1), round(w, 1)


def ok_slot(slot, l, w):
    if slot == 'night':
        return l <= 88
    if slot == 'sunset':
        return w >= 6 and 40 <= l <= 180
    return l >= 70


def work(job):
    r, slot, word = job
    kw = '%s %s' % (r['name'].split('·')[0], word)
    got = []
    for c in fs.search(kw)[:10]:
        if len(got) >= 2:
            break
        dst = os.path.join(OUT, '%03d_%s_%d.jpg' % (r['id'], slot, len(got)))
        try:
            size = fs.download(c['u'], dst)
        except Exception:
            continue
        if not size:
            continue
        l, w = tone(dst)
        if not ok_slot(slot, l, w):
            os.remove(dst)
            continue
        rel = os.path.relpath(dst, ROOT).replace(os.sep, '/')
        got.append({'path': rel, 'w': size[0], 'h': size[1], 'title': c['title'],
                    'l': l, 'wx': w, 'src': c['u']})
    rec = {'id': r['id'], 'name': r['name'], 'city': r['city'], 'slot': slot,
           'word': kw, 'cands': got}
    json.dump(rec, open(os.path.join(OUT, '%03d_%s.json' % (r['id'], slot)), 'w', encoding='utf-8'),
              ensure_ascii=False)
    print('%03d %s %s -> %d' % (r['id'], r['name'], slot, len(got)), flush=True)
    return rec


def main():
    routes = load_routes()
    done = {f[:-5] for f in os.listdir(OUT) if f.endswith('.json')}
    jobs = []
    for r in routes:
        for slot, word in SLOTS:
            key = '%03d_%s' % (r['id'], slot)
            if key in done:
                continue
            jobs.append((r, slot, word))
    print('待抓', len(jobs), '项')
    with ThreadPoolExecutor(max_workers=6) as ex:
        for _ in ex.map(work, jobs):
            pass
    print('完成')


if __name__ == '__main__':
    main()
