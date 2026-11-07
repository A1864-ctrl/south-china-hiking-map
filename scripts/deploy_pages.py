# -*- coding: utf-8 -*-
"""
一键部署到 GitHub Pages（gh-pages 分支）。
用法：python scripts/deploy_pages.py
流程：npm run build → 准备 gh-pages 工作副本 → 提交 → 推送 → GitHub 自动发布。
"""
import io
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'dist')
WORK = os.path.join(ROOT, '.gh-pages-tmp')
REMOTE = 'https://github.com/A1864-ctrl/south-china-hiking-map.git'
PAGES_URL = 'https://a1864-ctrl.github.io/south-china-hiking-map/'


def run(cmd, cwd=None, capture=True):
    print('  $', ' '.join(cmd))
    r = subprocess.run(
        cmd, cwd=cwd or ROOT, shell=(os.name == 'nt'),
        capture_output=capture, text=True, encoding='utf-8', errors='replace',
        env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'},
    )
    if r.returncode != 0:
        tail = (r.stderr or r.stdout or '')[-500:]
        print(f'  命令失败（exit {r.returncode}）：{tail}')
        sys.exit(1)
    return r


def main():
    os.chdir(ROOT)

    print('[1/4] 构建站点（首次需先 npm install）')
    npm = shutil.which('npm') or 'npm'
    run([npm, 'run', 'build'])
    if not os.path.isfile(os.path.join(DIST, 'index.html')):
        print('构建产物缺失，中止')
        sys.exit(1)

    print('[2/4] 准备 gh-pages 工作副本')
    if os.path.isdir(WORK):
        shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    run(['git', 'init', '-b', 'gh-pages'], cwd=WORK)
    run(['git', 'remote', 'add', 'origin', REMOTE], cwd=WORK)
    # 拷贝构建产物
    for item in os.listdir(DIST):
        src = os.path.join(DIST, item)
        dst = os.path.join(WORK, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    # 关闭 Jekyll 处理（避免下划线开头的资源被忽略）
    with io.open(os.path.join(WORK, '.nojekyll'), 'w', encoding='utf-8') as f:
        f.write('')

    print('[3/4] 提交并推送')
    run(['git', 'add', '-A'], cwd=WORK)
    stamp = time.strftime('%Y-%m-%d %H:%M')
    commit = run(['git', 'commit', '-m', f'deploy: 构建产物更新（{stamp}）'], cwd=WORK)
    if 'nothing to commit' in (commit.stdout or ''):
        print('  内容无变化，跳过推送 —— 线上已是最新')
        return
    run(['git', 'push', 'origin', 'gh-pages', '--force'], cwd=WORK)

    print('[4/4] 完成')
    print('GitHub Pages 将在 1-2 分钟内自动发布：')
    print(' ', PAGES_URL)
    print('提示：如果刷新后还是旧内容，等一分钟再刷新（首次构建稍慢）。')
    shutil.rmtree(WORK, ignore_errors=True)  # 清理工作副本
    shutil.rmtree(WORK, ignore_errors=True)  # 清理工作副本


if __name__ == '__main__':
    main()
