"""批量把一整个文件夹的 GPX 导入路线库。

用法：
    python tools/import_gpx_dir.py D:\\gpx\\武功山
    python tools/import_gpx_dir.py D:\\gpx --province 江西省 --city 萍乡市 --heat 85
    python tools/import_gpx_dir.py D:\\gpx --dry-run     # 只解析看统计，不落库

文件名会当成路线名（去掉 .gpx 后缀）。同名的已存在就覆盖。
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="放 GPX 文件的文件夹")
    ap.add_argument("--province", default="")
    ap.add_argument("--city", default="")
    ap.add_argument("--type", default="穿越", choices=["穿越", "往返", "环线", "登顶"])
    ap.add_argument("--difficulty", default="中等", choices=["入门", "较易", "中等", "较难", "难"])
    ap.add_argument("--heat", type=int, default=70)
    ap.add_argument("--season", default="春秋")
    ap.add_argument("--dry-run", action="store_true", help="只解析统计，不写文件")
    args = ap.parse_args()

    if not os.path.isdir(args.folder):
        print(f"文件夹不存在：{args.folder}")
        return

    import gpx_store
    from app_utils import parse_gpx

    files = sorted(
        f for f in os.listdir(args.folder) if f.lower().endswith((".gpx", ".xml"))
    )
    if not files:
        print("这个文件夹里没有 .gpx 文件。")
        return

    print(f"找到 {len(files)} 个文件\n")
    ok = fail = 0
    for fn in files:
        name = os.path.splitext(fn)[0]
        path = os.path.join(args.folder, fn)
        try:
            with open(path, "rb") as f:
                raw = f.read()
            pts, wpts = parse_gpx(raw, fn, with_waypoints=True)
            meta = {
                "id": gpx_store.make_id(name),
                "name": name,
                "province": args.province,
                "city": args.city,
                "type": args.type,
                "difficulty": args.difficulty,
                "days": 1,
                "best_season": args.season,
                "desc": f"从 {fn} 导入的实测航迹。",
                "heat": args.heat,
                "waypoints": wpts,
            }
            doc = gpx_store.build_doc(pts, meta)
            st = doc["stats"]
            if args.dry_run:
                print(
                    f"  [试跑] {name:28} {st['distance_km']:7.2f} km  "
                    f"爬升 {st['ascent_m'] if st['ascent_m'] is not None else '-'} m  "
                    f"海拔 {st['ele_min']}-{st['ele_max']}  路点 {len(wpts)}"
                )
            else:
                gpx_store.save_doc(doc, meta)
                print(
                    f"  [入库] {name:28} {st['distance_km']:7.2f} km  "
                    f"爬升 {st['ascent_m']} m  点 {len(doc['points'])}  路点 {len(doc['waypoints'])}"
                )
            ok += 1
        except Exception as exc:  # noqa: BLE001
            fail += 1
            print(f"  [失败] {name:28} {type(exc).__name__}: {str(exc)[:90]}")

    print(f"\n完成：成功 {ok}，失败 {fail}。")
    if not args.dry_run and ok:
        print("重启页面（或刷新）即可在「路线库」看到。")


if __name__ == "__main__":
    main()
