"""为首页已有但封面不合格的点位补拍候选（复用 360 图片搜索）。"""

import io
import json
import os
import time
import urllib.parse
import urllib.request

UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0 Safari/537.36'
)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'shots', 'c5')
OUT_JSON = os.path.join(ROOT, 'scripts', 'p360b_files.json')

QUERIES = {
    '白云山': '广州白云山 摩星岭',
    '华南植物园': '华南植物园 广州',
    '梧桐山': '梧桐山 深圳 云海',
    '七娘山': '七娘山 深圳',
    '西冲海滩': '西冲 海滩 深圳',
    '仙湖植物园': '仙湖植物园 深圳',
    '莽山': '莽山 五指峰',
    '黑麋峰': '黑麋峰 长沙',
    '橘子洲': '橘子洲 头 长沙',
    '广州塔': '广州塔 夜景 珠江',
    '太平老街': '长沙 太平老街',
    '洋湖湿地': '洋湖湿地公园 长沙',
    '岳麓山': '岳麓山 爱晚亭',
}
PER_SPOT = 5


def search(word):
    out = []
    for sn in (0, 30):
        params = {'q': word, 'src': 'srp', 'correct': word, 'sn': sn, 'pn': 30}
        url = 'https://image.so.com/j?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url, headers={'User-Agent': UA, 'Referer': 'https://image.so.com/'}
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as f:
                data = json.loads(f.read().decode('utf-8', 'ignore'))
        except Exception as e:
            print('  search fail', word, str(e)[:50])
            break
        for it in data.get('list') or []:
            u = it.get('imgurl') or it.get('img') or ''
            try:
                w = int(it.get('width') or 0)
                h = int(it.get('height') or 0)
            except (TypeError, ValueError):
                continue
            if not u.startswith('http') or not w or not h:
                continue
            ratio = w / h
            if ratio < 1.25 or ratio > 2.05 or w < 1100 or h < 700:
                continue
            out.append({
                'url': u, 'w': w, 'h': h,
                'title': (it.get('title') or '').strip(),
                'page': it.get('imgkey') or '',
            })
        time.sleep(0.9)
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    report = {}
    for si, (name, word) in enumerate(QUERIES.items()):
        cands = search(word)
        cands.sort(key=lambda c: -(c['w'] * c['h']))
        d = os.path.join(OUT_DIR, '%02d' % si)
        os.makedirs(d, exist_ok=True)
        got = []
        for ci, c in enumerate(cands):
            if len(got) >= PER_SPOT:
                break
            fp = os.path.join(d, '%d.jpg' % ci)
            try:
                req = urllib.request.Request(
                    c['url'], headers={'User-Agent': UA, 'Referer': 'https://image.so.com/'}
                )
                with urllib.request.urlopen(req, timeout=30) as f:
                    body = f.read()
                if len(body) < 50000:
                    continue
                io.open(fp, 'wb').write(body)
                got.append(dict(c, file=fp))
            except Exception:
                continue
            time.sleep(0.3)
        report[name] = got
        print('%-8s 候选 %2d -> %d' % (name, len(cands), len(got)))

    io.open(OUT_JSON, 'w', encoding='utf-8').write(json.dumps(report, ensure_ascii=False, indent=1))
    print('total', sum(len(v) for v in report.values()))


if __name__ == '__main__':
    main()
