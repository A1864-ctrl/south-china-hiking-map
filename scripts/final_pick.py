"""合并两轮候选，按人工核对结果定稿，并导出核对用总表。"""

import io
import json
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, 'scripts', 'baidu_pick.json')          # 第一轮自动挑选
B = os.path.join(ROOT, 'scripts', 'baidu_extra_files.json')   # 第二轮补充候选
OUT = os.path.join(ROOT, 'scripts', 'final_pick.json')

# 人工核对后改定的：景点 -> 补充候选里的序号（从 1 开始）
SWAP = {
    '海珠湖': 2,
    '德夯大峡谷': 3,
    '越秀公园': 6,
    '大围山': 1,
    '石燕湖': 4,
    '古东瀑布': 6,
    '老司城': 6,
    '南昆山': 5,
    '象头山': 5,
    '黑排角': 1,
    '苏仙岭': 4,
    '湖南博物院': 4,
}


def main():
    first = json.load(io.open(A, encoding='utf-8'))
    second = json.load(io.open(B, encoding='utf-8'))

    final = {}
    for name, it in first.items():
        final[name] = dict(it, src='first')
    for name, idx in SWAP.items():
        items = second.get(name) or []
        if idx - 1 < len(items):
            final[name] = dict(items[idx - 1], src='extra')

    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(final, ensure_ascii=False, indent=1))
    print('final', len(final))

    # 核对总表
    names = list(final.keys())
    cols, TW, TH = 4, 340, 210
    PER = 16
    outdir = os.path.join(ROOT, 'shots', 'final')
    os.makedirs(outdir, exist_ok=True)
    for gi in range(0, len(names), PER):
        group = names[gi:gi + PER]
        rows = (len(group) + cols - 1) // cols
        sheet = Image.new('RGB', (TW * cols, (TH + 20) * rows), '#ffffff')
        d = ImageDraw.Draw(sheet)
        for i, name in enumerate(group):
            im = Image.open(final[name]['file']).convert('RGB')
            im.thumbnail((TW - 6, TH - 6))
            x = (i % cols) * TW
            y = (i // cols) * (TH + 20)
            sheet.paste(im, (x + 3, y + 20))
            d.rectangle([x, y, x + TW, y + 19], fill='#1e3d29')
            d.text((x + 5, y + 4), '%d %s' % (gi + i + 1, name), fill='white')
        p = os.path.join(outdir, 'final-%d.png' % (gi // PER + 1))
        sheet.save(p)
        print(p)


if __name__ == '__main__':
    main()
