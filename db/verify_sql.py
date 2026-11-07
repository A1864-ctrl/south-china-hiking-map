"""用 sqlglot 按 MySQL 方言解析三个 .sql 文件，检查语法结构是否成立。

本机没有 MySQL 服务时，这是能做的最强离线校验。两处「翻译」是为了绕过解析器
的建模缺口，不影响 SQL 本身在 MySQL 8.0 的合法性：

1. 列级空间属性 `SRID 4326`（MySQL 8.0 合法）→ 解析前剥掉
2. 空间类型 `POINT / LINESTRING`（MySQL 8.0 合法）→ 解析时替换成 `GEOMETRY`
   （sqlglot 30 只认 GEOMETRY，不认具体的空间子类型）
"""

import re
import sys

import sqlglot

FILES = ["db/01_schema.sql", "db/02_seed.sql", "db/03_queries.sql"]


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"--[^\n]*", "", text)
    return text


def split_statements(text: str):
    """按分号切分；DELIMITER $$ 段整体作为一个语句。"""
    lines = text.splitlines()
    out, buf = [], []
    in_delim = False
    for line in lines:
        if re.match(r"\s*DELIMITER\s+\$\$", line, re.I):
            in_delim = True
            continue
        if in_delim and re.match(r"\s*DELIMITER\s*;", line, re.I):
            in_delim = False
            continue
        buf.append(line)
        joined = "\n".join(buf)
        if in_delim:
            if line.strip().endswith("$$"):
                out.append(joined.replace("$$", ";"))
                buf = []
        elif ";" in line:
            parts = joined.split(";")
            buf = [parts[-1]]
            for p in parts[:-1]:
                if p.strip():
                    out.append(p)
    if "\n".join(buf).strip():
        out.append("\n".join(buf))
    return [s.strip() for s in out if s.strip()]


def to_parsable(stmt: str) -> str:
    probe = re.sub(r"\s+SRID\s+\d+", "", stmt)
    probe = re.sub(r"\b(POINT|LINESTRING|POLYGON|MULTIPOINT|MULTILINESTRING)\b", "GEOMETRY", probe)
    return probe


def main():
    total, failed = 0, []
    for path in FILES:
        raw = open(path, encoding="utf-8").read()
        stmts = split_statements(strip_comments(raw))
        ok = 0
        for s in stmts:
            head = s.strip().replace("\n", " ")[:56]
            try:
                sqlglot.parse_one(to_parsable(s), read="mysql")
                ok += 1
            except Exception as e:
                failed.append((path, head, str(e).split("\n")[0][:130]))
            total += 1
        print(f"{path}: {ok}/{len(stmts)} 条通过")
    print(f"\n合计 {total} 条，失败 {len(failed)} 条")
    for f in failed:
        print("  ✗", f[0], "|", f[1], "|", f[2])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
