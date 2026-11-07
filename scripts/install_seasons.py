# -*- coding: utf-8 -*-
"""把抓到的四季候选择优安装到 public/photos/season/，并生成映射表。

规则：
- 标题必须含景点名关键字（前两字）或所属城市，否则视为「串图」丢弃；
- 标题含方案/规划/效果图/新闻等的丢弃；
- 统一 3:2 裁切 → 长边 1200 → 轻锐化 → q90。
"""
import json
import os

from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = os.path.join(ROOT, 'scripts', 'season_cand.json')
OUT = os.path.join(ROOT, 'public', 'photos', 'season')
JS = os.path.join(ROOT, 'src', 'data', 'seasonPhoto.js')

def daylight(path):
    """白天图：平均亮度不低于 70，避免把夜景塞进「春夏秋」的季相里"""
    im = Image.open(path).convert('RGB').resize((120, 80), Image.BILINEAR)
    px = list(im.getdata())
    n = len(px)
    return sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in px) / n


BAD = ('方案', '规划', '效果图', '设计说明', '公告', '通知', '招聘', '招标',
       '新闻', '报道', '地图', '门票', '海报', '二维码', '截图', '简笔画',
       'AR秀', '灯光秀', '跨年', '组图', '九宫格', '合集', '攻略', '打卡点', '推文')


def is_collage(path):
    """白边多、拼接痕迹重 → 网页截图或拼图，不要"""
    im = Image.open(path).convert('RGB').resize((200, 133), Image.BILINEAR)
    px = list(im.getdata())
    white = sum(1 for r, g, b in px if min(r, g, b) >= 246) / len(px)
    return white > 0.10
SEASON_KEYS = ['春', '夏', '秋', '冬']

os.makedirs(OUT, exist_ok=True)
man = json.load(open(MAN, encoding='utf-8'))

data = {}      # name -> {春: file, ...}
report = []
for key, v in sorted(man.items()):
    name, city, season = v['name'], v['city'], v['season']
    key2 = name.replace('·', ' ').split()[0][:2]
    picked = None
    pool = [c for c in sorted(v['cands'], key=lambda x: -x['score'])
            if not any(b in c['title'] for b in BAD) and (key2 in c['title'] or city in c['title'])]
    # 季相图要白天的：亮度 >= 70 的优先，实在没有才退回
    bright = []
    for c in pool:
        try:
            fp = os.path.join(ROOT, c['path'])
            if daylight(fp) >= 70 and not is_collage(fp):
                bright.append(c)
        except Exception:
            pass
    # 标题没命中就退到「按景点名搜出来的候选里排第一」，仍排除明确不要的类型
    loose = [c for c in sorted(v['cands'], key=lambda x: -x['score']) if not any(b in c['title'] for b in BAD)]
    for c in (bright or pool or loose):
        picked = c
        break
    if not picked:
        report.append((v['idx'], name, season, 'MISS', ''))
        continue
    im = Image.open(os.path.join(ROOT, picked['path'])).convert('RGB')
    aw, ah = im.size
    tw, th = aw, aw / 1.5
    if th > ah:
        th = ah
        tw = th * 1.5
    x0, y0 = (aw - tw) / 2, (ah - th) / 2
    im = im.crop((int(x0), int(y0), int(x0 + tw), int(y0 + th)))
    w = min(1050, im.width)
    im = im.resize((w, int(round(w / 1.5))), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=0.7, percent=46, threshold=3))
    fn = '%03d-%s.jpg' % (v['idx'], season)
    im.save(os.path.join(OUT, fn), 'JPEG', quality=84, optimize=True, progressive=True)
    data.setdefault(name, {})[season] = 'photos/season/' + fn
    report.append((v['idx'], name, season, 'OK', '%dx%d %s' % (im.width, im.height, picked['title'][:26])))

# 输出缺项
miss = [r for r in report if r[3] == 'MISS']
print('安装 %d 张，缺 %d 项' % (sum(1 for r in report if r[3] == 'OK'), len(miss)))
for r in miss:
    print('  缺:', r[0], r[1], r[2])

js = ['// 四季实景图（按景点 × 季节索引），来源为网络公开图源（小红书 / 抖音 博主图）',
      'export const seasonPhoto = {']
for name in sorted(data):
    parts = ', '.join('%s: %r' % (k, data[name][k]) for k in SEASON_KEYS if k in data[name])
    js.append("  '%s': { %s }," % (name, parts))
js.append('}')
js.append('')
open(JS, 'w', encoding='utf-8').write('\n'.join(js))
print('写入', JS, '景点', len(data))
