# -*- coding: utf-8 -*-
"""按景点抓「日落 / 夜景」实拍，并用画面明暗+色温过滤掉误入的白天图。

- 日落：R-B 偏暖 且 亮度 55~170（傍晚的天光）
- 夜景：平均亮度 <= 85（真实夜拍）
输出 scripts/light_cand.json + scripts/_light/*.jpg
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
OUT = os.path.join(ROOT, 'scripts', '_light')
MAN = os.path.join(ROOT, 'scripts', 'light_cand.json')
os.makedirs(OUT, exist_ok=True)

fs.MIN_W = 1000

WORDS = {
    'sunset': ['日落', '晚霞', '夕阳'],
    'night': ['夜景', '夜色', '灯光'],
}


def load_spots():
    src = open(os.path.join(ROOT, 'src', 'data', 'spots.js'), encoding='utf-8').read()
    rows = re.findall(r"^\s*\['([^']+)', '([^']+)', '([^']+)', '([^']+)'", src, re.M)
    return [{'name': n, 'city': c} for n, c, d, t in rows]


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
    return w >= 8 and 45 <= l <= 175


def work(job):
    idx, spot, slot = job
    name = spot['name']
    got = []
    used = set()
    for suffix in WORDS[slot]:
        if len(got) >= 3:
            break
        for word in ('%s %s' % (name.replace('·', ' ').split()[0], suffix),):
            if word in used:
                continue
            used.add(word)
            for c in fs.search(word)[:12]:
                if len(got) >= 3:
                    break
                dst = os.path.join(OUT, '%03d_%s_%d.jpg' % (idx, slot, len(got)))
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
    key = '%03d|%s' % (idx, slot)
    rec = {'idx': idx, 'name': name, 'city': spot['city'], 'slot': slot, 'cands': got}
    # 逐项落地，进程被中断也不丢结果
    json.dump(rec, open(os.path.join(OUT, key.replace('|', '_') + '.json'), 'w', encoding='utf-8'),
              ensure_ascii=False)
    print('%s %s %s -> %d' % (key, name, slot, len(got)), flush=True)
    return key, rec


def main():
    spots = load_spots()
    man = {}
    if os.path.exists(MAN):
        man = json.load(open(MAN, encoding='utf-8'))
    jobs = [(i, s, slot) for i, s in enumerate(spots) for slot in ('sunset', 'night')]
    done_keys = {f[:-5].replace('_', '|') for f in os.listdir(OUT) if f.endswith('.json')}
    if os.environ.get('LIGHT_FORCE') != '1':
        jobs = [j for j in jobs if ('%03d|%s' % (j[0], j[2])) not in done_keys]
    done = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(work, j) for j in jobs]
        for fu in futs:
            try:
                k, v = fu.result()
            except Exception as e:
                print('ERR', repr(e)[:120], flush=True)
                continue
            man[k] = v
            done += 1
            if done % 20 == 0:
                json.dump(man, open(MAN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(man, open(MAN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    empty = [k for k, v in man.items() if not v['cands']]
    print('完成 %d，缺 %d' % (len(man), len(empty)))
    print(empty)


if __name__ == '__main__':
    main()
