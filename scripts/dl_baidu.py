"""下载百度候选图，供人工核对。"""

import io
import json
import os
import time
import urllib.request

UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0 Safari/537.36'
)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'scripts', 'baidu_cand.json')
OUT = os.path.join(ROOT, 'shots', 'cand2')
PER = 6


def main():
    data = json.load(io.open(SRC, encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    report = {}
    for si, (name, cands) in enumerate(data.items()):
        d = os.path.join(OUT, '%02d' % si)
        os.makedirs(d, exist_ok=True)
        got = []
        for ci, c in enumerate(cands[:PER]):
            fp = os.path.join(d, '%d.jpg' % ci)
            if os.path.exists(fp) and os.path.getsize(fp) > 20000:
                got.append({'file': fp, 'title': c['title'], 'page': c['page'], 'w': c['w'], 'h': c['h']})
                continue
            try:
                req = urllib.request.Request(
                    c['url'], headers={'User-Agent': UA, 'Referer': 'https://image.baidu.com/'}
                )
                with urllib.request.urlopen(req, timeout=30) as f:
                    body = f.read()
                if len(body) < 20000:
                    continue
                io.open(fp, 'wb').write(body)
                got.append({'file': fp, 'title': c['title'], 'page': c['page'], 'w': c['w'], 'h': c['h']})
            except Exception as e:
                print('  fail', name, ci, str(e)[:50])
            time.sleep(0.35)
        report[name] = got
        print('%02d %s -> %d' % (si, name, len(got)))

    io.open(os.path.join(ROOT, 'scripts', 'baidu_files.json'), 'w', encoding='utf-8').write(
        json.dumps(report, ensure_ascii=False, indent=1)
    )
    print('total files', sum(len(v) for v in report.values()))


if __name__ == '__main__':
    main()
