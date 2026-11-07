#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
景点实景图抓取 v2：优先用中文维基百科条目首图 / 条目内插图（地点准确），
再退回 Commons 搜索。全部为开放版权图片，保留署名。

用法：
  python scripts/fetch_photos2.py --dry
  python scripts/fetch_photos2.py
"""
import json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'public', 'photos')
CAND = os.path.join(ROOT, 'scripts', 'photo_candidates2.json')
UA = 'south-china-hiking-map/2.0 (personal hiking portfolio)'
ZH = 'https://zh.wikipedia.org/w/api.php'
COMMONS = 'https://commons.wikimedia.org/w/api.php'

BAD = re.compile(
    r'(\.pdf$|\.svg$|\.ogg$|\.webm$|地图|地圖|map of|location|metro|地铁|地鐵|station|车站|車站|站台|站厅|月台|'
    r'platform|logo|标志|標誌|flag|seal|diagram|chart|plan|stamp|ticket|screenshot|poster|book|coin|icon|'
    r'coat of arms|commons-|wiki|disambig|question|ambox|edit-|symbol|nuvola|padlock)', re.I)


def api(base, params, tries=4):
    url = base + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                d = json.loads(r.read().decode('utf-8'))
            if 'error' in d:
                raise RuntimeError(d['error'].get('code'))
            return d
        except Exception as e:
            print('   !', str(e)[:60], flush=True)
            time.sleep(2.5 + i * 3)
    return None


def norm(name):
    n = name.split('·')[0]
    for suf in ['国家森林公园', '森林公园', '风景区', '景区', '旅游区', '竹筏', '漂流', '骑行', '观景台']:
        n = n.replace(suf, '')
    return n.strip()


def wp_page(name):
    d = api(ZH, {
        'action': 'query', 'format': 'json', 'titles': name, 'redirects': 1,
        'prop': 'pageimages|images', 'piprop': 'original|thumbnail', 'pithumbsize': 900,
        'imlimit': 24,
    })
    if not d:
        return None
    pages = (d.get('query', {}) or {}).get('pages', {})
    for pid, p in pages.items():
        if pid == '-1':
            continue
        return {
            'title': p.get('title'),
            'pageimage': (p.get('original') or {}).get('source'),
            'files': [im['title'] for im in (p.get('images') or [])
                      if im['title'].lower().endswith(('.jpg', '.jpeg', '.png'))],
        }
    return None


def commons_info(files):
    """批量拿文件尺寸、缩略图、作者、许可"""
    out = {}
    for i in range(0, len(files), 20):
        chunk = files[i:i + 20]
        d = api(COMMONS, {
            'action': 'query', 'format': 'json', 'titles': '|'.join(chunk),
            'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata', 'iiurlwidth': 900,
        })
        if not d:
            continue
        for p in ((d.get('query', {}) or {}).get('pages', {}) or {}).values():
            ii = (p.get('imageinfo') or [{}])[0]
            md = ii.get('extmetadata', {}) or {}
            out[p['title']] = {
                'title': p['title'][5:],
                'thumb': ii.get('thumburl'),
                'page': ii.get('descriptionurl'),
                'w': ii.get('width', 0), 'h': ii.get('height', 0),
                'artist': re.sub('<[^>]+>', '', (md.get('Artist', {}) or {}).get('value', '') or '').strip()[:50],
                'license': (md.get('LicenseShortName', {}) or {}).get('value', '') or '',
            }
        time.sleep(0.5)
    return out


def pick_spot(spot):
    base = norm(spot['name'])
    info, order = {}, []

    # 1) 维基条目插图
    page = wp_page(base)
    if not page and base != spot['name']:
        page = wp_page(spot['name'])
    if page:
        files = []
        if page.get('pageimage'):
            files.append(page['pageimage'])
        files += [f for f in page['files'] if f not in files]
        # 只要和条目名相关的图，避免条目里混入无关图示
        info = commons_info(files[:20])
        for src in files:
            # pageimage 是原始 URL，转成文件名匹配
            if src.startswith('http'):
                fn = urllib.parse.unquote(src.split('/')[-1])
                key = 'File:' + fn
            else:
                key = src
            it = info.get(key)
            if not it or not it.get('thumb'):
                continue
            if BAD.search(it['title']):
                continue
            w, h = it['w'], it['h']
            if w < 900 or h < 500 or not (1.15 <= w / h <= 2.9):
                continue
            if it['title'] in [o['title'] for o in order]:
                continue
            it['from'] = 'wikipedia'
            order.append(it)
            if len(order) >= 3:
                break

    # 2) Commons 搜索兜底
    if len(order) < 2:
        d = api(COMMONS, {
            'action': 'query', 'format': 'json', 'generator': 'search',
            'gsrsearch': f'{base} -地铁 -metro -station -站 -pdf', 'gsrnamespace': 6, 'gsrlimit': 10,
            'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata', 'iiurlwidth': 900,
        })
        if d:
            for p in ((d.get('query', {}) or {}).get('pages', {}) or {}).values():
                ii = (p.get('imageinfo') or [{}])[0]
                md = ii.get('extmetadata', {}) or {}
                t = p['title'][5:]
                w, h = ii.get('width', 0), ii.get('height', 0)
                if BAD.search(t) or w < 900 or h < 500 or not (1.15 <= w / h <= 2.9):
                    continue
                if not ii.get('thumburl'):
                    continue
                if t in [o['title'] for o in order]:
                    continue
                order.append({
                    'title': t, 'thumb': ii['thumburl'], 'page': ii.get('descriptionurl'),
                    'w': w, 'h': h,
                    'artist': re.sub('<[^>]+>', '', (md.get('Artist', {}) or {}).get('value', '') or '').strip()[:50],
                    'license': (md.get('LicenseShortName', {}) or {}).get('value', '') or '',
                    'from': 'commons',
                })
                if len(order) >= 3:
                    break
    return order[:3]


def main(dry=False):
    spots = json.load(open(os.path.join(ROOT, 'scripts', 'spot_list.json'), encoding='utf-8'))
    cache = json.load(open(CAND, encoding='utf-8')) if os.path.exists(CAND) else {}
    os.makedirs(OUT_DIR, exist_ok=True)

    for s in spots:
        key = f'spot-{s["id"]}'
        if cache.get(key, {}).get('picks'):
            continue
        picks = pick_spot(s)
        cache[key] = {'name': s['name'], 'picks': picks}
        print(key, s['name'], len(picks), [p['title'][:24] for p in picks], flush=True)
        json.dump(cache, open(CAND, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        time.sleep(0.8)

    if dry:
        return

    jobs = []
    for key, v in cache.items():
        for i, p in enumerate(v['picks'][:3]):
            jobs.append((f'{key}-{i + 1}.jpg', p['thumb']))

    ok = 0
    for fn, url in jobs:
        path = os.path.join(OUT_DIR, fn)
        if os.path.exists(path) and os.path.getsize(path) > 8000:
            ok += 1
            continue
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            data = urllib.request.urlopen(req, timeout=50).read()
            if len(data) > 8000:
                open(path, 'wb').write(data)
                ok += 1
        except Exception as e:
            print('dl fail', fn, str(e)[:50], flush=True)
        time.sleep(0.3)
    print(f'downloaded {ok}/{len(jobs)}')

    lines = ['// 自动生成：scripts/fetch_photos2.py（来源 Wikipedia / Wikimedia Commons，署名见此处）',
             'export const photoCredits = {']
    for key, v in cache.items():
        for i, p in enumerate(v['picks'][:3]):
            fn = f'{key}-{i + 1}.jpg'
            if not os.path.exists(os.path.join(OUT_DIR, fn)):
                continue
            art = (p['artist'] or 'Wikimedia 贡献者').replace('"', "'")[:40]
            ttl = p['title'].replace('"', '')[:70]
            lines.append(f'  "{fn}": {{ t: "{ttl}", a: "{art}", l: "{p["license"]}", u: "{p["page"]}", s: "{p["from"]}" }},')
    lines.append('}')
    open(os.path.join(ROOT, 'src', 'data', 'photoCredits.js'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote src/data/photoCredits.js')


if __name__ == '__main__':
    main(dry='--dry' in sys.argv)
