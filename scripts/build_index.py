#!/usr/bin/env python3
"""
从 data/**/*.md 的 YAML front matter 生成 index.json。
给 AI agent / 站点 读取用的机器可读索引。

用法: python3 scripts/build_index.py
"""
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "index.json"


def parse_front_matter(text: str):
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not m:
        return {}
    fm_raw = m.group(1)
    data = {}
    key = None
    for line in fm_raw.splitlines():
        if not line.strip():
            continue
        if re.match(r"^\s*-\s", line) and key:
            data.setdefault(key, [])
            if isinstance(data[key], list):
                data[key].append(line.strip()[2:].strip())
            continue
        m2 = re.match(r"^([A-Za-z_][\w]*):\s*(.*)$", line)
        if m2:
            key, val = m2.group(1), m2.group(2).strip()
            if val == "":
                data[key] = []
            elif val.startswith("[") and val.endswith("]"):
                data[key] = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
            else:
                data[key] = val.strip("'\"")
    return data


def main():
    entries = []
    for p in sorted(DATA.rglob("*.md")):
        if p.parent.name == "raw":
            continue
        fm = parse_front_matter(p.read_text(encoding="utf-8"))
        if not fm.get("title"):
            continue
        entries.append({
            "id": fm.get("id") or p.stem,
            "title": fm.get("title"),
            "issuer": fm.get("issuer"),
            "date": fm.get("date"),
            "tags": fm.get("tags", []),
            "path": str(p.relative_to(ROOT)),
        })
    entries.sort(key=lambda x: x.get("date") or "", reverse=True)
    doc = {
        "repo": "china-policy-radar",
        "generated": date.today().isoformat(),
        "count": len(entries),
        "entries": entries,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"index.json: {len(entries)} entries -> {OUT}")


if __name__ == "__main__":
    main()
