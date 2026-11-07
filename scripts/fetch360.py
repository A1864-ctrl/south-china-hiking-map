"""用 360 图片搜索抓取景点原图（imgurl 是原始尺寸，不是缩略图）。

筛选：横构图、原始宽度 >= 1000、短边 >= 700，标题优先命中景点名。
"""

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
OUT_DIR = os.path.join(ROOT, 'shots', 'c4')
OUT_JSON = os.path.join(ROOT, 'scripts', 'p360_files.json')

QUERIES = {
    '相公山观景台': '相公山 漓江 观景台',
    '猫儿山': '猫儿山 云海',
    '十里画廊骑行': '阳朔 十里画廊',
    '八角寨': '资源 八角寨 丹霞',
    '古东瀑布': '古东瀑布 桂林',
    '全州天湖': '全州 天湖',
    '越秀公园': '越秀公园 五羊石像',
    '从化溪头村': '从化 溪头村',
    '石门国家森林公园': '石门国家森林公园 红叶',
    '海珠湖': '海珠湖 广州',
    '大鹏所城': '大鹏所城',
    '马峦山': '马峦山 瀑布',
    '观澜湖': '观澜湖 深圳',
    '湖南博物院': '湖南博物院',
    '大围山': '大围山 杜鹃',
    '石燕湖': '石燕湖',
    '铜官窑古镇': '铜官窑古镇',
    '德夯大峡谷': '德夯大峡谷',
    '红石林': '古丈 红石林',
    '边城茶峒': '边城 茶峒',
    '坐龙峡': '古丈 坐龙峡',
    '老司城': '老司城 遗址',
    '张家界大峡谷': '张家界大峡谷 玻璃桥',
    '七星山': '张家界 七星山',
    '南昆山': '南昆山',
    '象头山': '象头山',
    '黑排角': '黑排角',
    '大亚湾': '大亚湾 海岸',
    '飞天山': '郴州 飞天山',
    '仰天湖草原': '仰天湖 草原',
    '板梁古村': '板梁古村',
    '苏仙岭': '苏仙岭',
}
PER_SPOT = 6


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
            if ratio < 1.2 or ratio > 2.15:
                continue
            if w < 1000 or h < 650:
                continue
            out.append({
                'url': u,
                'w': w,
                'h': h,
                'title': (it.get('title') or '').strip(),
                'page': it.get('imgkey') or it.get('url') or '',
            })
        time.sleep(0.9)
    return out


def key(name):
    return name.replace('观景台', '').replace('骑行', '').replace('国家森林公园', '')[:2]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    report = {}
    for si, (name, word) in enumerate(QUERIES.items()):
        cands = search(word)
        k = key(name)
        cands.sort(key=lambda c: (0 if (k in c['title'] or name in c['title']) else 1, -(c['w'] * c['h'])))
        d = os.path.join(OUT_DIR, '%02d' % si)
        os.makedirs(d, exist_ok=True)
        got = []
        for ci, c in enumerate(cands):
            if len(got) >= PER_SPOT:
                break
            fp = os.path.join(d, '%d.jpg' % ci)
            try:
                req = urllib.request.Request(
                    c['url'],
                    headers={'User-Agent': UA, 'Referer': 'https://image.so.com/'},
                )
                with urllib.request.urlopen(req, timeout=30) as f:
                    body = f.read()
                if len(body) < 40000:
                    continue
                io.open(fp, 'wb').write(body)
                got.append(dict(c, file=fp))
            except Exception:
                continue
            time.sleep(0.3)
        report[name] = got
        print('%02d %-8s 候选 %d -> 下载 %d' % (si, name, len(cands), len(got)))

    io.open(OUT_JSON, 'w', encoding='utf-8').write(json.dumps(report, ensure_ascii=False, indent=1))
    print('total', sum(len(v) for v in report.values()))


if __name__ == '__main__':
    main()
