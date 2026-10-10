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


def _unquote(val: str) -> str:
    """只剥掉成对的引号；标题里 '人工智能+制造' 这类内嵌引号必须保留。"""
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
        return val[1:-1]
    return val


def parse_front_matter(text: str):
    """极简 YAML 子集解析：标量、内联数组，以及 sources 块中的 publisher/url/type。"""
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not m:
        return {}
    lines = m.group(1).splitlines()
    data = {}
    sources = []
    key = None
    in_sources = False
    for line in lines:
        if not line.strip():
            continue
        if in_sources:
            # 顶层键（无缩进且匹配 key:）出现 = sources 块结束，回到主解析
            if re.match(r"^[A-Za-z_]\w*:", line):
                in_sources = False
            else:
                m_sub = re.match(r"^\s+-\s*publisher:\s*(.*)$", line)
                m_kv = re.match(r"^\s+(\w+):\s*(.*)$", line)
                if m_sub:
                    sources.append({"publisher": _unquote(m_sub.group(1))})
                elif m_kv and sources:
                    k, v = m_kv.group(1), _unquote(m_kv.group(2))
                    sources[-1][k] = v
                continue
        m2 = re.match(r"^([A-Za-z_][\w]*):\s*(.*)$", line)
        if m2:
            key, val = m2.group(1), m2.group(2).strip()
            if key == "sources":
                in_sources = True
                data["sources"] = sources
                continue
            if val == "":
                data[key] = []
            elif val.startswith("[") and val.endswith("]"):
                data[key] = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
            elif val == "null":
                data[key] = None
            else:
                data[key] = _unquote(val)
    return data


def main():
    entries = []
    for p in sorted(DATA.rglob("*.md")):
        if p.parent.name == "raw":
            continue
        fm = parse_front_matter(p.read_text(encoding="utf-8"))
        if not fm.get("title"):
            continue
        srcs = [s for s in (fm.get("sources") or []) if s.get("url")]
        entries.append({
            "id": fm.get("id") or p.stem,
            "title": fm.get("title"),
            "issuer": fm.get("issuer"),
            "date": fm.get("date"),
            "doc_number": fm.get("doc_number"),
            "status": fm.get("status") or "structured",  # pending=stub 仅元数据；structured=含条款
            "tags": fm.get("tags", []),
            "path": str(p.relative_to(ROOT)),
            "sources": [
                {"publisher": s.get("publisher"), "url": s["url"], "type": s.get("type", "primary")}
                for s in srcs
            ],
        })
    entries.sort(key=lambda x: x.get("date") or "", reverse=True)
    by_status = {}
    for e in entries:
        by_status[e["status"]] = by_status.get(e["status"], 0) + 1
    doc = {
        "repo": "china-policy-radar",
        "official": False,
        "generated": date.today().isoformat(),
        "count": len(entries),
        "count_by_status": by_status,  # 数字以本文件为准，文档不要硬编码
        "usage_note": (
            "本索引为机器可读入口。引用时必须保留 sources 中的官方链接。"
            "status=pending 的条目仅有元数据与一手链接，条款未补录，"
            "不得据其内容作任何条款性表述；status=structured 的条目含条款摘录。"
            "条目正文中以「分析（非原文）」开头的段落属判断而非政策原文，不得作为官方口径引用。"
            "详见 AGENTS.md。"
        ),
        "entries": entries,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"index.json: {len(entries)} entries -> {OUT}")
    print(f"  status 分布: {by_status}")


if __name__ == "__main__":
    main()
