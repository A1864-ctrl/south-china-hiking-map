# -*- coding: utf-8 -*-
"""把 pick 出来的高清候选拼成带编号的对照图，便于逐张目检。"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
m = json.load(open(os.path.join(ROOT, 'scripts', 'hd_cand.json'), encoding='utf-8'))

FONT = 'C:/Windows/Fonts/msyh.ttc'
try:
    font = ImageFont.truetype(FONT, 20)
except OSError:
    font = ImageFont.load_default()

CELL_W, CELL_H, PAD, LABEL = 400, 267, 8, 30
COLS = 5


def pick(file):
    v = m[file]
    name = v['names'][0]
    cands = sorted(v['cands'], key=lambda c: -c['score'])
    key = name.replace('·', '').replace(' ', '')[:3]
    hit = [c for c in cands if any(ch in c['title'] for ch in key)]
    return name, (hit or cands)[0]


def make_sheet(files, out, mode='pick'):
    rows = (len(files) + COLS - 1) // COLS
    W = COLS * (CELL_W + PAD) + PAD
    H = rows * (CELL_H + LABEL + PAD) + PAD
    sheet = Image.new('RGB', (W, H), (245, 245, 245))
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(files):
        name, c = pick(f)
        im = Image.open(os.path.join(ROOT, c['path'])).convert('RGB')
        im.thumbnail((CELL_W, CELL_H), Image.LANCZOS)
        cx = PAD + (i % COLS) * (CELL_W + PAD)
        cy = PAD + (i // COLS) * (CELL_H + LABEL + PAD)
        sheet.paste(im, (cx + (CELL_W - im.width) // 2, cy + (CELL_H - im.height) // 2))
        d.text((cx + 2, cy + CELL_H + 2), '%s  %dx%d' % (name, c['w'], c['h']),
               fill=(20, 20, 20), font=font)
    sheet.save(out, 'JPEG', quality=88)
    print(out, sheet.size)


files = sorted(m.keys())
half = (len(files) + 1) // 2
make_sheet(files[:half], os.path.join(ROOT, 'shots', 'hd_a.jpg'))
make_sheet(files[half:], os.path.join(ROOT, 'shots', 'hd_b.jpg'))
