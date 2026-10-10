#!/usr/bin/env python3
"""
记分牌到期巡检：检查 scoreboard/*.md 里的观察节点是否到期/逾期。

用法:
    python3 scripts/check_scoreboard.py            # 列出所有节点状态
    python3 scripts/check_scoreboard.py --due-only  # 只输出已到期/逾期的（供 cron 判断）
    python3 scripts/check_scoreboard.py --json      # JSON 输出

设计要点:
  - 从 scoreboard markdown 表格里解析 | 节点 | 日期 | 要采集的数据 | 状态 | 行
  - 识别状态列里的 ⏳（待采）标记，日期已过且仍为待采 → 视为「逾期」
  - 「平时安静」：无逾期时 --due-only 输出空，便于 cron 只在必要时推送
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "scoreboard"


def parse_nodes():
    nodes = []
    if not BOARD.exists():
        return nodes
    for p in sorted(BOARD.rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        for line in text.splitlines():
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4:
                continue
            # 找到形如 YYYY-MM-DD 的单元格
            date_cell = None
            date_idx = None
            for i, c in enumerate(cells):
                m = re.search(r"(20\d\d)-(\d{2})-(\d{2})", c)
                if m:
                    date_cell = m.group(0)
                    date_idx = i
                    break
            if not date_cell:
                continue
            status_cell = cells[-1]
            nodes.append({
                "file": str(p.relative_to(ROOT)),
                "node": cells[0].replace("**", "") if date_idx > 0 else "—",
                "due": date_cell,
                "task": cells[date_idx + 1] if date_idx + 1 < len(cells) else "",
                "status": status_cell,
                "done": bool(re.search(r"✅|已完成|已填", status_cell)),
            })
    return nodes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--due-only", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    today = date.today()
    nodes = parse_nodes()
    for n in nodes:
        try:
            d = date.fromisoformat(n["due"])
        except ValueError:
            n["verdict"] = "bad-date"
            continue
        days = (today - d).days
        n["days_from_today"] = -days  # 正数=还剩几天；负数=已过
        if n["done"]:
            n["verdict"] = "done"
        elif days >= 0:
            n["verdict"] = "overdue"
        elif days >= -14:
            n["verdict"] = "due-soon"
        else:
            n["verdict"] = "pending"

    urgent = [n for n in nodes if n["verdict"] in ("overdue", "due-soon")]

    if args.json:
        print(json.dumps({"today": today.isoformat(), "total": len(nodes),
                          "urgent": urgent, "all": nodes}, ensure_ascii=False, indent=2))
    elif args.due_only:
        if urgent:
            print(f"记分牌到期提醒（{today.isoformat()}）：")
            for n in urgent:
                tag = "❗逾期" if n["verdict"] == "overdue" else "⏰临近"
                print(f"  {tag} {n['due']} | {n['node']} | 采集：{n['task'][:60]}")
                print(f"        文件：{n['file']}")
        # 无到期则不输出（保持安静）
    else:
        print(f"共 {len(nodes)} 个观察节点（今天 {today.isoformat()}）：")
        for n in sorted(nodes, key=lambda x: x["due"]):
            print(f"  [{n['verdict']:9}] {n['due']} (剩 {n['days_from_today']:>4} 天) {n['node']}")
            print(f"              采集：{n['task'][:70]}")
        print(f"\n需处理：{len(urgent)} 个")

    return 0


if __name__ == "__main__":
    sys.exit(main())
