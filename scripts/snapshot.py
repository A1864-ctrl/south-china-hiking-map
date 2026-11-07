# -*- coding: utf-8 -*-
"""把当前项目快照到桌面「户外徒步网站修改/快照/<时间戳>/」，可随时回滚。

用法:
    python scripts/snapshot.py "这一版改了什么"
"""
import datetime
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESK = os.path.join(os.path.expanduser('~'), 'Desktop')
BASE = os.path.join(DESK, '户外徒步网站修改', '快照')

# 只备份「代码与数据」，图片是生成物（体积大、可从 scripts 重跑）
INCLUDE = [
    ('src', 'src'),
    ('index.html', 'index.html'),
    ('package.json', 'package.json'),
    ('vite.config.js', 'vite.config.js'),
    ('README.md', 'README.md'),
]
IGNORE = shutil.ignore_patterns('__pycache__', '*.pyc', '_tiles', '_seasons', '_light',
                                '_hd', '_seasonfix', 'node_modules')


def snap():
    ts = datetime.datetime.now().strftime('%Y-%m-%d_%H%M')
    note = sys.argv[1] if len(sys.argv) > 1 else ''
    dst = os.path.join(BASE, ts)
    if os.path.exists(dst):
        dst = dst + '_' + str(len(os.listdir(BASE)))
    os.makedirs(dst, exist_ok=True)

    for src, name in INCLUDE:
        s = os.path.join(ROOT, src)
        if not os.path.exists(s):
            continue
        d = os.path.join(dst, name)
        if os.path.isdir(s):
            shutil.copytree(s, d, ignore=IGNORE)
        else:
            shutil.copy2(s, d)

    # 构建产物（小，只有 js/css/html），方便直接对比线上
    dist_assets = os.path.join(ROOT, 'dist', 'assets')
    if os.path.isdir(dist_assets):
        shutil.copytree(dist_assets, os.path.join(dst, 'dist-assets'))

    # 脚本（只复制 py，跳过缓存目录）
    sd = os.path.join(dst, 'scripts')
    os.makedirs(sd, exist_ok=True)
    for f in os.listdir(os.path.join(ROOT, 'scripts')):
        if f.endswith('.py'):
            shutil.copy2(os.path.join(ROOT, 'scripts', f), os.path.join(sd, f))

    # 版本索引
    idx_path = os.path.join(BASE, 'index.json')
    idx = []
    if os.path.exists(idx_path):
        try:
            idx = json.load(open(idx_path, encoding='utf-8'))
        except Exception:
            idx = []
    files = sum(len(fs) for _, _, fs in os.walk(dst))
    idx.append({'time': ts, 'dir': os.path.basename(dst), 'note': note,
                'files': files, 'at': datetime.datetime.now().isoformat(timespec='seconds')})
    json.dump(idx, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    with open(os.path.join(BASE, '版本记录.md'), 'w', encoding='utf-8') as f:
        f.write('# 版本快照记录\n\n')
        f.write('每次改完都会在 `快照/` 下留一份 `src + 配置 + 脚本 + 构建产物` 的副本。\n\n')
        f.write('回滚命令（在项目根目录执行）：\n\n```bash\npython "C:/Users/Tsy20723/Desktop/户外徒步网站修改/快照/回滚.py" ' + ts + '\n```\n\n')
        f.write('| 时间 | 文件夹 | 文件数 | 说明 |\n|---|---|---|---|\n')
        for it in reversed(idx):
            f.write('| %s | %s | %s | %s |\n' % (it['time'], it['dir'], it['files'], it['note'] or '—'))

    print('快照完成:', dst, files, '个文件')
    print('版本记录:', os.path.join(BASE, '版本记录.md'))


if __name__ == '__main__':
    snap()
