# -*- coding: utf-8 -*-
"""用 Photon（OSM）给每条路线的关键点做一次真实坐标校正。

做法：以现有点位为偏置，按地名查询，取 6 km 内、名字能对上的最近候选。
只输出建议（JSON + 控制台），不改数据文件。
"""
import io, json, math, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def haversine(a, b):
    R = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    d = 2 * R * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
    return d


def norm(s):
    return re.sub(r'[·\s\-—()（）]', '', s)


def photon(q, lat, lon, limit=6):
    url = 'https://photon.komoot.io/api/?' + urllib.parse.urlencode({'q': q, 'lat': lat, 'lon': lon, 'limit': limit, 'lang': 'default'})
    req = urllib.request.Request(url, headers={'User-Agent': 'hiking-demo/1.0'})
    for _ in range(3):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=20).read().decode('utf-8'))
        except Exception as e:
            time.sleep(1.2)
    return None


def parse_routes():
    src = os.path.join(ROOT, 'src', 'data', 'routes.js')
    s = io.open(src, encoding='utf-8').read()
    out = []
    for blk in re.finditer(r"\{\s*\n\s*name: '([^']+)'[\s\S]*?pts: \[([\s\S]*?)\n    \],", s):
        name = blk.group(1)
        pts = []
        for m in re.finditer(r"\{ name: '([^']+)', lat: ([\d.]+), lng: ([\d.]+), ele: (\d+)", blk.group(2)):
            pts.append({'name': m.group(1), 'lat': float(m.group(2)), 'lng': float(m.group(3)), 'ele': int(m.group(4))})
        out.append({'route': name, 'pts': pts})
    return out


if __name__ == '__main__':
    rs = parse_routes()
    report = []
    for r in rs:
        for p in r['pts']:
            q = p['name']
            js = photon(q, p['lat'], p['lng'])
            best = None
            if js:
                for f in js.get('features', []):
                    pr = f.get('properties', {})
                    nm = pr.get('name') or ''
                    lon, lat = f['geometry']['coordinates'][:2]
                    d = haversine((p['lat'], p['lng']), (lat, lon))
                    if d > 8:
                        continue
                    score = 0
                    if norm(nm) == norm(q):
                        score = 3
                    elif norm(q) in norm(nm) or norm(nm) in norm(q):
                        score = 2
                    else:
                        continue
                    key = (score, -d)
                    if best is None or key > best[0]:
                        best = (key, nm, lat, lon, d, pr.get('osm_value') or pr.get('type'))
            if best:
                _, nm, lat, lon, d, kind = best
                if d > 0.15:
                    report.append({
                        'route': r['route'], 'pt': q, 'osm_name': nm, 'kind': kind,
                        'from': [p['lat'], p['lng']], 'to': [round(lat, 5), round(lon, 5)],
                        'moved_m': round(d * 1000)
                    })
            time.sleep(0.45)
    out = os.path.join(ROOT, 'scripts', 'geocode_report.json')
    json.dump(report, io.open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('建议调整点数', len(report), '→', out)
    for x in sorted(report, key=lambda z: -z['moved_m'])[:40]:
        print('%-22s %-12s → %-14s %6d m' % (x['route'][:20], x['pt'][:10], x['osm_name'][:12], x['moved_m']))
