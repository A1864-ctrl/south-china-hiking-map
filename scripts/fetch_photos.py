#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 Wikimedia Commons 抓取景点实景图（开放版权，保留署名）。
用法：
  python scripts/fetch_photos.py --dry     # 只产候选清单，不下载
  python scripts/fetch_photos.py           # 下载并生成 src/data/photos.js
"""
import json, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'public', 'photos')
CAND = os.path.join(ROOT, 'scripts', 'photo_candidates.json')
UA = 'south-china-hiking-map/2.0 (personal hiking portfolio; contact: local)'
API = 'https://commons.wikimedia.org/w/api.php'

BAD = re.compile(
    r'(\.pdf$|\.svg$|地图|地圖|map of|\bmap\b|metro|地铁|地鐵|station|站台|站厅|站廳|月台|platform|'
    r'logo|标志|標誌|flag|seal|diagram|chart|plan of|stamp|ticket|screenshot|poster|book cover|coin|'
    r'street map|panorama of|panorama$)', re.I)


def norm(name):
    n = name.split('·')[0]
    for suf in ['国家森林公园', '森林公园', '风景区', '景区', '旅游区']:
        n = n.replace(suf, '')
    return n.strip()


def api(params):
    url = API + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception:
            time.sleep(1.2)
    return {}


def search(query, limit=10):
    d = api({
        'action': 'query', 'format': 'json', 'generator': 'search',
        'gsrsearch': query, 'gsrnamespace': 6, 'gsrlimit': limit,
        'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata', 'iiurlwidth': 900,
    })
    if d is None:
        return None
    out = []
    for p in (d.get('query', {}).get('pages', {}) or {}).values():
        ii = (p.get('imageinfo') or [{}])[0]
        w, h = ii.get('width', 0), ii.get('height', 0)
        if not w or not h:
            continue
        if w < 900 or h < 500:
            continue
        ar = w / h
        if ar < 1.15 or ar > 2.9:
            continue
        if BAD.search(p['title']):
            continue
        md = ii.get('extmetadata', {}) or {}
        out.append({
            'title': p['title'][5:],
            'thumb': ii.get('thumburl'),
            'page': ii.get('descriptionurl'),
            'w': w, 'h': h,
            'artist': re.sub('<[^>]+>', '', (md.get('Artist', {}) or {}).get('value', '') or '').strip()[:60],
            'license': (md.get('LicenseShortName', {}) or {}).get('value', '') or '',
        })
    return out


def build_tasks():
    """景点与路线的查询词，优先精确名称，其次城市 + 类型补充词。"""
    spots = json.load(open(os.path.join(ROOT, 'scripts', 'spot_list.json'), encoding='utf-8'))
    tasks = []
    for s in spots:
        base = norm(s['name'])
        queries = [f'{base} -地铁 -metro -station -站 -pdf']
        if s['city'] and s['city'] not in base:
            queries.append(f'{base} {s["city"]} -地铁 -metro -station -pdf')
        tasks.append({'key': f'spot-{s["id"]}', 'name': s['name'], 'queries': queries})
    return tasks


def run(dry=False):
    tasks = build_tasks()
    os.makedirs(OUT_DIR, exist_ok=True)
    cache = {}
    if os.path.exists(CAND):
        cache = json.load(open(CAND, encoding='utf-8'))

    def work(t):
        if t['key'] in cache and cache[t['key']].get('picks'):
            return t['key'], cache[t['key']]
        picked, seen = [], set()
        for q in t['queries']:
            for c in search(q):
                if c['title'] in seen:
                    continue
                seen.add(c['title'])
                picked.append(c)
            if len(picked) >= 4:
                break
            time.sleep(0.35)
        return t['key'], {'name': t['name'], 'picks': picked[:4]}

    with ThreadPoolExecutor(max_workers=6) as ex:
        for key, res in ex.map(work, tasks):
            cache[key] = res
            print(key, res['name'], len(res['picks']), flush=True)
    json.dump(cache, open(CAND, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    if dry:
        return

    jobs = []
    for key, res in cache.items():
        for i, p in enumerate(res['picks'][:3]):
            jobs.append((f'{key}-{i + 1}.jpg', p['thumb']))

    def dl(job):
        fn, url = job
        path = os.path.join(OUT_DIR, fn)
        if os.path.exists(path) and os.path.getsize(path) > 8000:
            return fn, True
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                data = r.read()
            if len(data) < 8000:
                return fn, False
            open(path, 'wb').write(data)
            return fn, True
        except Exception as e:
            return fn, False

    ok = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for fn, good in ex.map(dl, jobs):
            ok += 1 if good else 0
    print(f'downloaded {ok}/{len(jobs)}')

    # 生成前端清单
    lines = ["// 自动生成：scripts/fetch_photos.py（图片来源 Wikimedia Commons，署名见 credits）",
             "export const photoCredits = {"]
    for key, res in cache.items():
        for i, p in enumerate(res['picks'][:3]):
            fn = f'{key}-{i + 1}.jpg'
            if not os.path.exists(os.path.join(OUT_DIR, fn)):
                continue
            art = (p['artist'] or 'Wikimedia 贡献者').replace('"', "'")[:40]
            lines.append(
                f'  "{fn}": {{ t: "{p["title"].replace(chr(34), "")[:70]}", a: "{art}", l: "{p["license"]}", u: "{p["page"]}" }},')
    lines.append('}')
    open(os.path.join(ROOT, 'src', 'data', 'photoCredits.js'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote src/data/photoCredits.js')


if __name__ == '__main__':
    run(dry='--dry' in sys.argv)
