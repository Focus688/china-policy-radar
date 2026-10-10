#!/usr/bin/env python3
"""
从 state/seen.json 生成政策清单（按年份分组）。

用法: python3 scripts/build_catalog.py [--since 2024]
输出: catalog/<since>-now-central-policies.md
"""
import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "seen.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2024")
    args = ap.parse_args()
    since = args.since

    data = json.loads(STATE.read_text(encoding="utf-8"))
    rows = [v for v in data.values() if (v.get("date") or "") >= f"{since}.01"]
    rows.sort(key=lambda x: x["date"], reverse=True)

    by_year = {}
    for r in rows:
        by_year.setdefault(r["date"][:4], []).append(r)

    lines = [
        f"# 中央及部委政策清单（{since} 年至今）",
        "",
        f"> 由中国政府网公开检索接口采集，采集日 {date.today().isoformat()}。",
        f"> 共 **{len(rows)}** 条。关键词扫描结果，非全量收录。",
        "> 每条均可点击原文核对。",
        "",
    ]
    for year in sorted(by_year, reverse=True):
        lines.append(f"## {year} 年（{len(by_year[year])} 条）")
        lines.append("")
        lines.append("| 日期 | 文件 | 发文字号 |")
        lines.append("|---|---|---|")
        for r in by_year[year]:
            t = r["title"].replace("|", "丨")
            lines.append(f"| {r['date']} | [{t}]({r['url']}) | {r.get('doc_number') or '—'} |")
        lines.append("")

    out = ROOT / "catalog" / f"{since}-now-central-policies.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"catalog: {len(rows)} 条 -> {out}")


if __name__ == "__main__":
    main()
