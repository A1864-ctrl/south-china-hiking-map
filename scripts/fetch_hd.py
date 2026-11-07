# -*- coding: utf-8 -*-
"""为低分辨率配图抓高清原图（360 图片搜索 imgurl 为原始尺寸）。

用法:
    python scripts/fetch_hd.py            # 全部待替换项
    python scripts/fetch_hd.py gal-s02.jpg
输出:
    scripts/_hd/<file>_<k>.jpg  候选图
    scripts/hd_cand.json        候选清单（含标题/尺寸/来源）
"""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'scripts', '_hd')
TARGETS = os.path.join(ROOT, 'scripts', os.environ.get('HD_TARGETS', 'hd_targets.json'))
CAND_JSON = os.path.join(ROOT, 'scripts', os.environ.get('HD_CAND', 'hd_cand.json'))

# 更精准的搜索词（默认用 城市+名称）
QUERY = {
    '龙脊梯田': '龙脊梯田 金坑 梯田',
    '白云山': '广州白云山 摩星岭',
    '越秀公园': '越秀公园 五羊石像',
    '七娘山': '七娘山 大鹏',
    '西冲海滩': '西冲海滩 西涌',
    '马峦山': '马峦山 瀑布 深圳',
    '大梅沙': '大梅沙 海滨公园',
    '观澜湖': '观澜湖 高尔夫 深圳',
    '石燕湖': '石燕湖 长沙',
    '黑麋峰': '黑麋峰 长沙',
    '凤凰古城': '凤凰古城 沱江 吊脚楼',
    '猛洞河漂流': '猛洞河',
    '坐龙峡': '坐龙峡 古丈',
    '老司城': '老司城 遗址 永顺',
    '巽寮湾': '巽寮湾 惠州',
    '南昆山': '南昆山 森林 惠州',
    '湖南博物院': '湖南省博物馆 建筑 外观',
    '便江': '永兴 便江 风光',
    '陈家祠': '广州陈家祠 建筑',
    '罗浮山': '罗浮山 飞云顶 惠州',
    '象头山': '象头山 自然保护区 惠州',
    '罗浮山': '罗浮山 飞云顶 惠州',
    '象头山': '象头山 自然保护区 惠州',
    '仰天湖草原': '仰天湖大草原 郴州',
    '万时山': '万时山 仁化',
    '湖南博物院': '湖南省博物馆 建筑 外观',
    '便江': '永兴 便江 风光',
    '陈家祠': '广州陈家祠 建筑',
    '罗浮山': '罗浮山 飞云顶 惠州',
    '象头山': '象头山 自然保护区 惠州',
    '罗浮山': '罗浮山 飞云顶 惠州',
    '象头山': '象头山 自然保护区 惠州',
    '仰天湖草原': '仰天湖大草原 郴州',
    '万时山': '万时山 仁化',
    '船底顶·罗新线': '船底顶 草甸 韶关',
    '丹霞山·长老峰': '丹霞山 长老峰',
    '广东大峡谷': '广东大峡谷 乳源',
    '云髻山': '云髻山 新丰',
    '大南山': '大南山 惠东',
    '东西冲海岸线': '东西冲 海岸线 穿越',
    '排牙山': '排牙山 深圳',
    '八排山': '八排山 连州',
    '衡山·经典登顶线': '南岳衡山 祝融峰',
    '八大公山': '八大公山 原始森林 桑植',
    '阳明山·万寿寺': '阳明山 万寿寺 永州',
    '酃峰·神农谷': '酃峰 神农谷',
    '壶瓶山': '壶瓶山 石门',
    '幕阜山': '幕阜山 平江',
    '武功山·金顶穿越': '武功山 金顶 高山草甸',
    '黄山·天都峰环线': '黄山 天都峰',
    '华山·五峰连穿': '华山 五峰 全景',
    '虎跳峡·高路': '虎跳峡 高路 徒步',
    '观音山·王山寺': '东莞观音山 森林公园',
    '十里画廊骑行': '阳朔 十里画廊 骑行',
    '红石林': '古丈红石林',
    '象头山': '象头山 森林 溪谷',
    '莲花山': '番禺莲花山 古采石场',
}

BAD_WORDS = ('地图', '示意', '门票', 'logo', 'LOGO', '路线图', '轨迹', '海报',
             '广告', '证件', '截图', '二维码', '人物写真')
PER_FILE = 6
MIN_W = 1500
MIN_RATIO, MAX_RATIO = 1.25, 1.85
if os.environ.get('HD_RELAX'):
    MIN_W = 1200
    MIN_RATIO, MAX_RATIO = 1.05, 2.1


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
        except Exception as e:
            print('   搜索失败', word, str(e)[:60])
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
            if w < MIN_W:
                continue
            ratio = w / float(h)
            if not (MIN_RATIO <= ratio <= MAX_RATIO):
                continue
            title = (it.get('title') or '').strip()
            if any(b in title for b in BAD_WORDS):
                continue
            out.append({'u': u, 'w': w, 'h': h, 'title': title})
    # 去重 + 打分：标题命中名称优先，其次分辨率，再次接近 3:2
    seen = set()
    uniq = []
    key = word.split()[0]
    for c in out:
        if c['u'] in seen:
            continue
        seen.add(c['u'])
        score = 0
        if key[:2] in c['title']:
            score += 40
        score += min(c['w'], 4000) / 100.0
        score += 12 - abs(c['w'] / c['h'] - 1.5) * 20
        c['score'] = round(score, 1)
        uniq.append(c)
    uniq.sort(key=lambda c: -c['score'])
    return uniq


def download(u, dst):
    req = urllib.request.Request(u, headers={
        'User-Agent': UA, 'Referer': 'https://image.so.com/'})
    with urllib.request.urlopen(req, timeout=30) as f:
        data = f.read()
    if len(data) < 60000:
        return None
    im = Image.open(io.BytesIO(data))
    im.load()
    if im.width < MIN_W:
        return None
    im.convert('RGB').save(dst, 'JPEG', quality=95)
    return im.size


def main():
    targets = json.load(open(TARGETS, encoding='utf-8'))
    want = sys.argv[1:] or None
    # 同一图片可能对应多个名称，取第一个（更短）作为搜索词
    ordered = []
    seen = {}
    for t in targets:
        if t['file'] in seen:
            seen[t['file']]['names'].append(t['name'])
        else:
            t = dict(t)
            t['names'] = [t['name']]
            seen[t['file']] = t
            ordered.append(t)

    if want:
        ordered = [t for t in ordered if t['file'] in want]

    os.makedirs(OUT_DIR, exist_ok=True)
    manifest = {}
    if os.path.exists(CAND_JSON):
        manifest = json.load(open(CAND_JSON, encoding='utf-8'))

    for t in ordered:
        name = t['names'][0]
        word = QUERY.get(name) or (t.get('city', '') + ' ' + name).strip()
        print('===', t['file'], name, '|', word)
        cands = search(word)
        got = []
        for k, c in enumerate(cands):
            if len(got) >= PER_FILE:
                break
            dst = os.path.join(OUT_DIR, '%s_%d.jpg' % (t['file'].replace('.jpg', ''), len(got)))
            try:
                size = download(c['u'], dst)
            except Exception as e:
                continue
            if not size:
                continue
            got.append({'path': os.path.relpath(dst, ROOT).replace('\\', '/'),
                        'w': size[0], 'h': size[1], 'title': c['title'],
                        'score': c['score'], 'src': c['u']})
        if not got and manifest.get(t['file'], {}).get('cands'):
            print('   本轮为空，保留旧候选')
            continue
        if not got and manifest.get(t['file'], {}).get('cands'):
            print('   本轮为空，保留旧候选')
            continue
        manifest[t['file']] = {'name': name, 'names': t['names'], 'word': word, 'cands': got}
        print('   拿到', len(got), '张')
        json.dump(manifest, open(CAND_JSON, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        time.sleep(0.6)

    json.dump(manifest, open(CAND_JSON, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('完成', len(manifest), '项')


if __name__ == '__main__':
    main()
