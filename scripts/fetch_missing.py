#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给缺图的景点用英文/拼音别名再查一次 Commons，标题不强制匹配。"""
import json, os, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'public', 'photos')
UA = 'SouthChinaTrails/2.0 (personal hiking project)'
API = 'https://commons.wikimedia.org/w/api.php'
BADWORDS = ('map', 'metro', 'station', 'logo', 'diagram', 'pdf', 'svg', 'hotel', 'resort', 'office', 'poster')

spots = json.load(open(os.path.join(ROOT, 'scripts', 'spot_list.json'), encoding='utf-8'))
alias = json.load(open(os.path.join(ROOT, 'scripts', 'alias.json'), encoding='utf-8'))
have = json.load(open(os.path.join(ROOT, 'scripts', 'spot_extra_photos.json'), encoding='utf-8')) if os.path.exists(
    os.path.join(ROOT, 'scripts', 'spot_extra_photos.json')) else {}


def search(q):
    params = {
        'action': 'query', 'format': 'json', 'generator': 'search',
        'gsrsearch': q + ' filetype:bitmap', 'gsrnamespace': 6, 'gsrlimit': 8,
        'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata', 'iiurlwidth': 1000,
    }
    url = API + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print('err', str(e)[:40], q, flush=True)
        return {}


for s in spots:
    key = str(s['id'])
    if key in have:
        continue
    term = alias.get(s['name'])
    if not term:
        continue
    d = search(term)
    got = None
    for p in ((d.get('query', {}) or {}).get('pages', {}) or {}).values():
        ii = (p.get('imageinfo') or [{}])[0]
        t = p['title'][5:]
        w, h = ii.get('width', 0), ii.get('height', 0)
        if any(b in t.lower() for b in BADWORDS):
            continue
        if w < 1000 or h < 560 or not (1.2 <= w / h <= 2.9):
            continue
        got = {'title': t, 'thumb': ii.get('thumburl'), 'page': ii.get('descriptionurl'),
               'w': w, 'h': h, 'artist': 'Wikimedia'}
        break
    if got:
        have[key] = got
        print(key, s['name'], '->', got['title'][:50], flush=True)
        json.dump(have, open(os.path.join(ROOT, 'scripts', 'spot_extra_photos.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    else:
        print(key, s['name'], 'miss', flush=True)
    time.sleep(1.0)

# 下载 + 追加到 spotWiki.js
import re
src = open(os.path.join(ROOT, 'src', 'data', 'spotWiki.js'), encoding='utf-8').read()
add = []
for key, p in have.items():
    fn = f'spot-{key}-x.jpg'
    path = os.path.join(OUT, fn)
    if not (os.path.exists(path) and os.path.getsize(path) > 8000):
        try:
            req = urllib.request.Request(p['thumb'], headers={'User-Agent': UA})
            data = urllib.request.urlopen(req, timeout=45).read()
            if len(data) < 8000:
                continue
            open(path, 'wb').write(data)
        except Exception as e:
            print('dl fail', fn, str(e)[:40], flush=True)
            continue
    name = next((x['name'] for x in spots if str(x['id']) == key), None)
    if not name:
        continue
    add.append('  "%s": { src: "/photos/%s", all: ["/photos/%s"], title: "%s", credit: "Wikimedia Commons", license: "见原页面", page: "%s" },' % (
        name, fn, fn, p['title'].replace('"', '')[:60], p.get('page') or ''))
if add:
    src = src.rstrip().rstrip('}') + '\n' + '\n'.join(add) + '\n}\n'
    open(os.path.join(ROOT, 'src', 'data', 'spotWiki.js'), 'w', encoding='utf-8').write(src)
print('appended', len(add))
