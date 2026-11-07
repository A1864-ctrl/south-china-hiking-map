# -*- coding: utf-8 -*-
"""按「景点名 + 季节」批量抓四季实景图（360 图片检索，多来自小红书/抖音博主原图）。

用法:
    python scripts/fetch_seasons.py            # 全部景点四季
    python scripts/fetch_seasons.py 广州塔     # 指定景点
输出:
    scripts/_seasons/<idx>_<s>_<k>.jpg
    scripts/season_cand.json
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'scripts', '_seasons')
CAND_JSON = os.path.join(ROOT, 'scripts', 'season_cand.json')

SEASONS = [('春', '春天'), ('夏', '夏天'), ('秋', '秋天'), ('冬', '冬天')]
PER_FILE = 3
MIN_W = 1100
MIN_RATIO, MAX_RATIO = 1.2, 2.0
BAD_WORDS = ('地图', '示意', '门票', 'logo', 'LOGO', '路线图', '轨迹', '海报',
             '广告', '证件', '截图', '二维码', '写真', '壁纸', '简笔画', '手绘')


def load_spots():
    src = open(os.path.join(ROOT, 'src', 'data', 'spots.js'), encoding='utf-8').read()
    rows = re.findall(r"^\s*\['([^']+)', '([^']+)', '([^']+)', '([^']+)'", src, re.M)
    return [{'name': n, 'city': c, 'district': d, 'type': t} for n, c, d, t in rows]


def search(word):
    out = []
    for sn in (0, 30):
        params = {'q': word, 'src': 'srp', 'correct': word, 'sn': sn, 'pn': 30}
        url = 'https://image.so.com/j?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={
            'User-Agent': UA, 'Referer': 'https://image.so.com/'})
        try:
            with urllib.request.urlopen(req, timeout=25) as f:
                data = json.loads(f.read().decode('utf-8', 'ignore'))
        except Exception:
            break
        for it in data.get('list') or []:
            u = it.get('imgurl') or it.get('img') or ''
            try:
                w = int(it.get('width') or 0)
                h = int(it.get('height') or 0)
            except (TypeError, ValueError):
                continue
            if not u.startswith('http') or not w or not h or w < MIN_W:
                continue
            if not (MIN_RATIO <= w / float(h) <= MAX_RATIO):
                continue
            title = (it.get('title') or '').strip()
            if any(b in title for b in BAD_WORDS):
                continue
            out.append({'u': u, 'w': w, 'h': h, 'title': title})
    seen, uniq = set(), []
    for c in out:
        if c['u'] in seen:
            continue
        seen.add(c['u'])
        uniq.append(c)
    return uniq[:40]


def download(u, dst):
    req = urllib.request.Request(u, headers={
        'User-Agent': UA, 'Referer': 'https://image.so.com/'})
    with urllib.request.urlopen(req, timeout=30) as f:
        data = f.read()
    if len(data) < 50000:
        return None
    im = Image.open(io.BytesIO(data))
    im.load()
    if im.width < MIN_W:
        return None
    im.convert('RGB').save(dst, 'JPEG', quality=95)
    return im.size


def pick_score(c, name, season_kw, s_word):
    """标题里带景点名 + 带季节词才值得要。"""
    key = name.replace('·', ' ').split()[0]
    t = c['title']
    sc = 0
    if key[:2] and key[:2] in t:
        sc += 40
    elif key[:2] and key[:2] not in t:
        sc -= 25
    if s_word in t or ('春' == season_kw and any(x in t for x in ('春', '花', '踏青'))):
        sc += 25
    sc += min(c['w'], 4000) / 200.0
    sc += 8 - abs(c['w'] / c['h'] - 1.5) * 12
    return round(sc, 1)


def work(args):
    idx, spot, season, s_word = args
    name = spot['name']
    word = '%s %s' % (name, s_word)
    cands = search(word)
    got = []
    for c in cands:
        if len(got) >= PER_FILE:
            break
        dst = os.path.join(OUT_DIR, '%03d_%s_%d.jpg' % (idx, season, len(got)))
        try:
            size = download(c['u'], dst)
        except Exception:
            continue
        if not size:
            continue
        got.append({'path': os.path.relpath(dst, ROOT).replace('\\', '/'),
                    'w': size[0], 'h': size[1], 'title': c['title'],
                    'score': pick_score(c, name, season, s_word), 'src': c['u']})
    print('%s %s %s -> %d' % (idx, name, season, len(got)), flush=True)
    return ('%03d|%s' % (idx, season), {'idx': idx, 'name': name, 'city': spot['city'],
                                       'season': season, 'word': word, 'cands': got})


def main():
    spots = load_spots()
    want = sys.argv[1:]
    if want:
        spots = [s for s in spots if s['name'] in want]
        base = {s['name']: i for i, s in enumerate(load_spots())}
        jobs = [(base[s['name']], s, k, w) for s in spots for k, w in SEASONS]
    else:
        jobs = [(i, s, k, w) for i, s in enumerate(spots) for k, w in SEASONS]

    os.makedirs(OUT_DIR, exist_ok=True)
    manifest = {}
    if os.path.exists(CAND_JSON):
        manifest = json.load(open(CAND_JSON, encoding='utf-8'))

    done = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for key, val in ex.map(work, jobs):
            manifest[key] = val
            done += 1
            if done % 12 == 0:
                json.dump(manifest, open(CAND_JSON, 'w', encoding='utf-8'),
                          ensure_ascii=False, indent=1)
    json.dump(manifest, open(CAND_JSON, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    empty = [k for k, v in manifest.items() if not v['cands']]
    print('完成 %d 项，缺失 %d 项' % (len(manifest), len(empty)))
    print('缺失:', empty)


if __name__ == '__main__':
    main()
