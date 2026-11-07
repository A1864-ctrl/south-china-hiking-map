"""把 spotWiki 里已有的封面拼成总览图，检查观感是否统一。"""

import io
import os
import re

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'data', 'spotWiki.js')
OUT = os.path.join(ROOT, 'shots', 'old')
PAT = re.compile(r'^\s*"([^"]+)":\s*\{\s*src:\s*"([^"]+)"', re.M)


def main():
    text = io.open(SRC, encoding='utf-8').read()
    ents = PAT.findall(text)
    print('covers', len(ents))
    os.makedirs(OUT, exist_ok=True)
    cols, tw, th, per = 4, 300, 180, 20
    for gi in range(0, len(ents), per):
        group = ents[gi:gi + per]
        rows = (len(group) + cols - 1) // cols
        sheet = Image.new('RGB', (tw * cols, (th + 18) * rows), 'white')
        dr = ImageDraw.Draw(sheet)
        for i, (name, src) in enumerate(group):
            p = os.path.join(ROOT, 'public', src)
            try:
                im = Image.open(p).convert('RGB')
            except Exception:
                continue
            im.thumbnail((tw - 6, th - 6))
            x = (i % cols) * tw
            y = (i // cols) * (th + 18)
            sheet.paste(im, (x + 3, y + 18))
            dr.rectangle([x, y, x + tw, y + 17], fill='#333')
            dr.text((x + 4, y + 3), '%d %s' % (gi + i + 1, name), fill='white')
        q = os.path.join(OUT, 'o%d.png' % (gi // per + 1))
        sheet.save(q)
        print(q)


if __name__ == '__main__':
    main()
