#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
野径 · 旅行社交平台　MySQL 一键建库脚本

用法（密码通过环境变量传，不落在命令行历史里）：

    # Git Bash
    MYSQL_PWD='你的密码' python db/setup.py

    # Windows CMD
    set MYSQL_PWD=你的密码 && python db\setup.py

    # 或用参数（会出现在进程列表，仅本机调试用）
    python db/setup.py --password 你的密码

它做四件事：
  1. 找到本机 mysql.exe 并验证连接
  2. 依次执行 01_schema.sql / 02_seed.sql / 03_queries.sql
  3. 查 information_schema 做结构验收（表 / 视图 / 触发器 / 空间索引）
  4. 跑三条关键查询验证功能真的可用（附近的人 / 找搭子 / 路线卡片）
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

CANDIDATES = [
    r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
    r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe",
    r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqladmin.exe",
    "/usr/bin/mysql",
    "/usr/local/bin/mysql",
    "/usr/local/mysql/bin/mysql",
]

FILES = [
    ("01_schema.sql", "建库 + 23 表 + 索引 + 视图 + 触发器"),
    ("02_seed.sql", "演示数据"),
    ("04_user.sql", "应用账号（最小权限）"),
    ("03_queries.sql", "核心查询（会打印结果）"),
]


def find_mysql():
    for p in CANDIDATES:
        if os.path.exists(p):
            return p
    # 兜底：PATH 里找
    from shutil import which

    for name in ("mysql", "mysql.exe"):
        p = which(name)
        if p:
            return p
    return None


def run(mysql, args, stdin_file=None, password=None):
    env = os.environ.copy()
    if password:
        env["MYSQL_PWD"] = password
    cmd = [mysql, "-uroot", "--default-character-set=utf8mb4"] + args
    if stdin_file:
        with open(stdin_file, "rb") as f:
            proc = subprocess.run(cmd, stdin=f, capture_output=True, env=env)
    else:
        proc = subprocess.run(cmd, input=b"", capture_output=True, env=env)
    return proc


def decode(b):
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return str(b)


def fail(msg, proc=None):
    print("\n[失败] " + msg)
    if proc is not None:
        out = decode(proc.stdout or b"").strip()
        err = decode(proc.stderr or b"").strip()
        if err:
            print("--- stderr ---")
            print(err[:2000])
        if out:
            print("--- stdout ---")
            print(out[:2000])
    sys.exit(1)


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    password = None
    for i, a in enumerate(sys.argv):
        if a == "--password" and i + 1 < len(sys.argv):
            password = sys.argv[i + 1]
    if password is None:
        password = os.environ.get("MYSQL_PWD")

    mysql = find_mysql()
    if not mysql:
        fail("没找到 mysql.exe，请确认 MySQL Server 已安装（默认在 C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin\\）")
    print("mysql 客户端: " + mysql)

    # 1) 连接测试
    proc = run(mysql, ["-N", "-B", "-e", "SELECT VERSION(), @@port, @@character_set_server;"], password=password)
    if proc.returncode != 0:
        hint = decode(proc.stderr or b"")
        if "Access denied" in hint:
            fail("root 密码不对。用 MYSQL_PWD='你的密码' python db/setup.py 重试；忘了密码可以先看 db/README.md 的重置步骤。")
        fail("连不上 MySQL 服务，确认 MySQL80 服务已启动。", proc)
    print("连接成功: " + decode(proc.stdout or b"").strip())

    # 2) 依次执行
    for fn, desc in FILES:
        path = os.path.join(ROOT, fn)
        if not os.path.exists(path):
            fail("缺少文件 " + path)
        print("\n>>> 执行 %-16s %s" % (fn, desc))
        proc = run(mysql, [], stdin_file=path, password=password)
        if proc.returncode != 0:
            fail(fn + " 执行出错", proc)
        out = decode(proc.stdout or b"").strip()
        if out:
            lines = out.splitlines()
            for ln in lines[:40]:
                print("    " + ln)
            if len(lines) > 40:
                print("    ...（共 %d 行输出）" % len(lines))
        print("    完成")

    # 3) 结构验收
    print("\n" + "=" * 58)
    print("结构验收")
    print("=" * 58)
    checks = [
        ("表数量", "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='yejing' AND table_type='BASE TABLE';", "23"),
        ("视图数量", "SELECT COUNT(*) FROM information_schema.views WHERE table_schema='yejing';", "2"),
        ("触发器数量", "SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema='yejing';", "3"),
        ("空间索引数量", "SELECT COUNT(DISTINCT index_name) FROM information_schema.statistics WHERE table_schema='yejing' AND index_type='SPATIAL';", "6"),
        ("外键数量", "SELECT COUNT(*) FROM information_schema.referential_constraints WHERE constraint_schema='yejing';", "—"),
        ("ngram 全文索引", "SELECT COUNT(DISTINCT index_name) FROM information_schema.statistics WHERE table_schema='yejing' AND index_type='FULLTEXT';", "3"),
    ]
    for label, sql, expect in checks:
        proc = run(mysql, ["-N", "-B", "-e", sql], password=password)
        val = decode(proc.stdout or b"").strip() if proc.returncode == 0 else "ERR"
        flag = "" if expect == "—" or val == expect else "  ← 期望 " + expect
        print("  %-14s %s%s" % (label, val, flag))

    rows = [
        ("app_user", "用户"), ("poi", "景点"), ("trail", "路线"),
        ("gear_item", "装备"), ("post", "帖子"), ("buddy_post", "搭子帖"),
        ("presence", "位置"), ("favorite", "收藏"),
    ]
    print("\n  数据行数")
    for t, cn in rows:
        proc = run(mysql, ["-N", "-B", "-e", "SELECT COUNT(*) FROM yejing.%s;" % t], password=password)
        print("    %-14s %-6s %s" % (t, cn, decode(proc.stdout or b"").strip() if proc.returncode == 0 else "ERR"))

    # 4) 功能验证
    print("\n" + "=" * 58)
    print("功能验证")
    print("=" * 58)
    demos = [
        ("附近的人（500m 内）",
         """USE yejing;
SET @me = ST_GeomFromText('POINT(23.106600 113.324500)', 4326);
SELECT u.nickname,
       ROUND(ST_Distance_Sphere(@me, p.geom)) AS 距离米,
       p.city
FROM presence p JOIN app_user u ON u.id = p.user_id
WHERE p.visible = 1
  AND p.geom IS NOT NULL
  AND ST_Distance_Sphere(@me, p.geom) <= 500
ORDER BY 距离米 ASC;"""),
        ("找搭子（时间重叠 + 打分）",
         """USE yejing;
SELECT b.id, b.dest_city AS 目的地, b.start_date AS 出发, b.end_date AS 返回,
       b.slots AS 还差, u.nickname AS 发起人
FROM buddy_post b JOIN app_user u ON u.id = b.owner_id
WHERE b.status = 1
  AND b.end_date >= '2026-11-12' AND b.start_date <= '2026-11-16'
ORDER BY b.start_date;"""),
        ("路线卡片视图",
         """USE yejing;
SELECT name AS 路线, city AS 城市,
       ROUND(distance_km, 1) AS 公里, climb_m AS 爬升, days AS 天, fav_cnt AS 收藏
FROM v_trail_card ORDER BY distance_km DESC LIMIT 5;"""),
    ]
    for label, sql in demos:
        print("\n  " + label)
        proc = run(mysql, ["-B", "-e", sql], password=password)
        out = decode(proc.stdout or b"").strip()
        if proc.returncode != 0:
            print("    ERR: " + decode(proc.stderr or b"").strip()[:300])
        elif not out:
            print("    （无数据）")
        else:
            for ln in out.splitlines():
                print("    " + ln)

    print("\n" + "=" * 58)
    print("建库完成。连接串：")
    print("  应用（读写） mysql+pymysql://yj_app:YeJing2026_App@127.0.0.1:3306/yejing?charset=utf8mb4")
    print("  只读演示     mysql+pymysql://yj_ro:YeJing2026_Read@127.0.0.1:3306/yejing?charset=utf8mb4")
    print("  账号密码写在 db/04_user.sql 里，换机器部署请改掉。")
    print("=" * 58)


if __name__ == "__main__":
    main()
