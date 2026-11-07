"""从百度图片按景点名检索候选配图。

筛选规则：
- 只要横构图（宽/高 1.15 ~ 2.2），竖图裁成横图会丢内容
- 原始尺寸足够大（短边 >= 700）
- 标题里包含景点名的关键词，降低张冠李戴的概率
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
OUT = os.path.join(ROOT, 'scripts', 'baidu_cand.json')

# spot 名 -> 检索词（括号里补充定位信息，避免同名撞车）
QUERIES = {
    '相公山观景台': '相公山 漓江 观景台',
    '猫儿山': '猫儿山 桂林 云海',
    '十里画廊骑行': '阳朔 十里画廊 田园',
    '八角寨': '资源 八角寨 丹霞',
    '古东瀑布': '古东瀑布 桂林',
    '全州天湖': '全州 天湖 高山',
    '越秀公园': '越秀公园 广州',
    '从化溪头村': '从化 溪头村',
    '石门国家森林公园': '从化 石门国家森林公园 红叶',
    '海珠湖': '广州 海珠湖 公园',
    '大鹏所城': '大鹏所城 深圳',
    '马峦山': '马峦山 瀑布 深圳',
    '观澜湖': '观澜湖 深圳',
    '湖南博物院': '湖南博物院 长沙',
    '大围山': '浏阳 大围山 杜鹃',
    '石燕湖': '长沙 石燕湖',
    '铜官窑古镇': '长沙 铜官窑古镇',
    '德夯大峡谷': '德夯大峡谷 吉首',
    '红石林': '古丈 红石林',
    '边城茶峒': '边城 茶峒 湘西',
    '坐龙峡': '古丈 坐龙峡',
    '老司城': '老司城 永顺 遗址',
    '张家界大峡谷': '张家界大峡谷 玻璃桥',
    '七星山': '张家界 七星山',
    '南昆山': '南昆山 惠州 森林',
    '象头山': '象头山 惠州',
    '黑排角': '黑排角 惠州 海岸',
    '大亚湾': '大亚湾 惠州 海岛',
    '飞天山': '郴州 飞天山 丹霞',
    '仰天湖草原': '郴州 仰天湖 草原',
    '板梁古村': '永兴 板梁古村',
    '苏仙岭': '郴州 苏仙岭',
}


def search(word, pages=2):
    out = []
    for pn in range(pages):
        params = {
            'tn': 'resultjson_com',
            'ipn': 'rj',
            'ct': '201326592',
            'fp': 'result',
            'word': word,
            'pn': pn * 20,
            'rn': 20,
        }
        url = 'https://image.baidu.com/search/acjson?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'zh-CN'})
        try:
            with urllib.request.urlopen(req, timeout=25) as f:
                data = json.loads(f.read().decode('utf-8', 'ignore'))
        except Exception as e:
            print('  query fail', word, str(e)[:60])
            break
        for it in data.get('data', []):
            if not it.get('middleURL'):
                continue
            w, h = it.get('width') or 0, it.get('height') or 0
            out.append({
                'url': it['middleURL'],
                'w': w,
                'h': h,
                'title': (it.get('fromPageTitleEnc') or '').strip(),
                'from': it.get('fromURLHost') or '',
                'page': it.get('fromURL') or '',
            })
        time.sleep(0.8)
    return out


def score(c, name):
    """横构图、尺寸大、标题对得上，评分越高"""
    w, h = c['w'], c['h']
    if not w or not h:
        return -1
    ratio = w / h
    if ratio < 1.15 or ratio > 2.2:
        return -1
    if min(w, h) < 700:
        return -1
    s = 0
    s += min(w * h / 1e6, 3) * 2  # 像素量
    s += 1.5 if abs(ratio - 1.5) < 0.25 else 0  # 接近 3:2
    key = name.replace('骑行', '').replace('观景台', '')
    if key[:2] in c['title']:
        s += 2
    if name[:2] in c['title']:
        s += 1
    bad = ['地图', '路线图', '攻略图', '票价', '门票', '大全', '排名', '民宿', '酒店', '广告']
    if any(b in c['title'] for b in bad):
        s -= 3
    return s


def main():
    result = {}
    for name, word in QUERIES.items():
        print('##', name, '|', word)
        cands = search(word)
        seen = set()
        keep = []
        for c in cands:
            if c['url'] in seen:
                continue
            seen.add(c['url'])
            sc = score(c, name)
            if sc > 0:
                c['score'] = round(sc, 2)
                keep.append(c)
        keep.sort(key=lambda x: -x['score'])
        result[name] = keep[:8]
        print('   raw %d -> keep %d' % (len(cands), len(keep)))
        time.sleep(1.2)

    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(result, ensure_ascii=False, indent=1))
    total = sum(len(v) for v in result.values())
    print('saved', OUT, 'spots', len(result), 'candidates', total)


if __name__ == '__main__':
    main()
