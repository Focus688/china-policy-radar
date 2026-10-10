#!/usr/bin/env python3
"""
从 catalog/*.md 的清单表格生成「待结构化 stub」记录，填进 data/<年>/。

动机：data/ 只有 3 条全结构化记录，而 catalog 已人工核验 26 条——
机器可读层（index.json）与人类清单严重脱节。本脚本把清单条目变成
schema 合法的最小记录（标题/机关/日期/文号/一手链接 + status: pending），
条款摘录留空，等人工/LLM 后续补录（补完后把 status 改成 structured）。

诚实纪律：
  - stub 不编造任何条款原文，clauses 为空数组
  - 只收录 catalog 表格中本身带链接的条目（无链接=违反一手来源铁律，不收）
  - 已存在的 data/ 记录（按 doc_number / URL / 日期+标题前缀匹配）跳过，不覆盖

用法: python3 scripts/build_stubs.py [--dry-run]
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOGS = ["catalog/central-ai-tech-2024-2026.md", "catalog/2024-now-central-policies.md"]
DATA = ROOT / "data"

LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
# 表格行: | 日期 | 链接列 | 发文 | 文号 |  (4列或3列)
ROW_RE = re.compile(r"^\|\s*(\d{4})[.\-](\d{2})[.\-](\d{2})\s*\|(.*)$")


def parse_catalog(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line.strip())
        if not m:
            continue
        y, mo, d = m.group(1), m.group(2), m.group(3)
        rest = m.group(4)
        cells = [c.strip() for c in rest.split("|")]
        if not cells:
            continue
        link_cell = cells[0]
        lm = LINK_RE.search(link_cell)
        if not lm:
            continue  # 无链接不收（一手来源铁律）
        title = lm.group(1).replace("**", "").strip()
        url = lm.group(2)
        rest_cells = [c.replace("**", "").strip() for c in cells[1:] if c.strip() not in ("—", "-", "")]
        doc_number = issuer = ""
        for c in rest_cells:
            if ("〔" in c and "号" in c) or re.match(r"^第?\d+号", c):
                doc_number = c
            elif not issuer:
                issuer = c
        tags = guess_tags(title)
        rows.append({"date": f"{y}-{mo}-{d}", "title": title, "url": url,
                     "issuer": issuer, "doc_number": doc_number, "tags": tags})
    return rows


TOPIC_SLUGS = [
    ("数据要素", "data-elements"), ("数据资产", "data-assets"), ("数据跨境", "cross-border-data"),
    ("数据流通", "data-circulation"), ("数据标准", "data-standards"), ("公共数据", "public-data"),
    ("数据产业", "data-industry"), ("未来产业", "future-industries"), ("设备更新", "equipment-renewal"),
    ("数字人才", "digital-talent"), ("资本市场", "capital-markets"), ("智慧城市", "smart-city"),
    ("标准化体系", "standards-system"), ("创业投资", "venture-capital"), ("深化改革", "deepening-reform"),
    ("信息基础设施", "info-infrastructure"), ("物流成本", "logistics-cost"),
    ("数字化转型", "digital-transformation"), ("东数西算", "east-data-west-compute"),
    ("算力", "computing-power"), ("应急机器人", "emergency-robotics"), ("政府工作报告", "gov-work-report"),
    ("五年规划", "five-year-plan"), ("人工智能", "ai-plus"), ("智能", "ai"), ("机器人", "robotics"),
    ("低空经济", "low-altitude"), ("能源", "energy"), ("电力", "power"), ("药监", "drug-regulation"),
    ("教育", "education"), ("人社", "hrss"), ("消费", "consumption"), ("软件", "software"),
    ("制造", "manufacturing"), ("招标投标", "bidding"), ("伦理", "ethics"), ("拟人化", "anthropomorphic-ai"),
    ("新质生产力", "new-quality-productive-forces"), ("非化石能源", "non-fossil-energy"),
]


def guess_tags(title: str):
    tag_map = [
        ("人工智能", "人工智能+"), ("AI", "人工智能+"), ("数据", "数据要素"),
        ("算力", "算力基础设施"), ("机器人", "机器人"), ("低空", "低空经济"),
        ("设备更新", "设备更新"), ("制造", "智能制造"), ("软件", "软件产业"),
        ("资本市场", "资本市场"), ("金融", "金融供给"), ("新质生产力", "新质生产力"),
        ("未来产业", "未来产业"), ("量子", "未来产业"), ("生物", "生物制造"),
        ("能源", "能源"), ("教育", "教育"), ("消费", "消费"), ("标准化", "标准体系"),
        ("伦理", "AI治理"), ("监管", "监管"), ("规划", "顶层设计"), ("决定", "顶层设计"),
        ("意见", None), ("通知", None),
    ]
    tags, seen = [], set()
    for zh, tag in tag_map:
        if zh in title and tag and tag not in seen:
            tags.append(tag); seen.add(tag)
    if not tags:
        for zh, en in TOPIC_SLUGS:
            if zh in title:
                tags.append(zh); break
    return tags[:4]


def slugify(title: str, date: str) -> str:
    base = None
    for zh, en in TOPIC_SLUGS:
        if zh in title:
            base = en
            break
    if base is None:
        ascii_part = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower()
        ascii_part = "-".join(w for w in ascii_part.split("-") if w)[:40]
        base = ascii_part if len(ascii_part) >= 3 else None
    if base is None:
        import hashlib
        base = "doc-" + hashlib.sha1(f"{date}|{title}".encode()).hexdigest()[:8]
    return base


def existing_keys():
    """扫全部 data/**/*.md，收集 (doc_number, url, date+title前12字) 三种身份。"""
    ids = {"doc": set(), "url": set(), "dt": set()}
    for p in DATA.rglob("*.md"):
        text = p.read_text(encoding="utf-8")
        fm = text.split("---")[1] if text.startswith("---") else ""
        for u in re.findall(r"url:\s*(https?://\S+)", fm):
            ids["url"].add(u.rstrip("/"))
        dn = re.search(r"doc_number:\s*(.+)", fm)
        if dn and dn.group(1).strip() not in ("null", "[]", ""):
            ids["doc"].add(dn.group(1).strip())
        dt = re.search(r"^date:\s*(\S+)", fm, re.M)
        tt = re.search(r"^title:\s*[\"']?(.{0,12})", fm, re.M)
        if dt and tt:
            ids["dt"].add(dt.group(1) + "|" + tt.group(1))
    return ids


def render_stub(r: dict, slug: str) -> str:
    issuer_yaml = f"[{r['issuer']}]" if r["issuer"] else "[]"
    dn = r["doc_number"] if r["doc_number"] else None
    dn_yaml = f'"{dn}"' if dn else "null"
    body = "\n".join(f"> {ln}" for ln in r["title"].splitlines()[:1])
    import json as _json
    return f"""---
id: {r['date']}-{slug}
title: {_json.dumps(r['title'], ensure_ascii=False)}
issuer: {issuer_yaml}
date: {r['date']}
doc_number: {_json.dumps(dn, ensure_ascii=False) if dn else "null"}
sources:
  - publisher: 官方原文（链接见 catalog 核验记录）
    url: {r['url']}
    type: primary
tags: [{', '.join(r.get('tags') or ['待分类'])}]
status: pending
supersedes: null
---

# {r['title']}

> ⚠️ 本条为 **status: pending** 的 stub：仅含清单级元数据与一手链接，**条款摘录未补录**。
> 补录步骤见 `schema/policy.schema.json` 与已有 `data/2026/2026-10-09-*.md` 范例；补完后将 `status` 改为 `structured`。

原文入口：[{r['title']}]({r['url']})
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ids = existing_keys()
    created = skipped = 0
    for cat in CATALOGS:
        p = ROOT / cat
        if not p.exists():
            print(f"!! 缺清单: {cat}", file=sys.stderr)
            continue
        for r in parse_catalog(p):
            key_dt = r["date"] + "|" + r["title"][:12]
            if (r["doc_number"] and r["doc_number"] in ids["doc"]) or \
               r["url"].rstrip("/") in ids["url"] or key_dt in ids["dt"]:
                skipped += 1
                continue
            slug = slugify(r["title"], r["date"])
            out = DATA / r["date"][:4] / f"{r['date']}-{slug}.md"
            _n = 2
            while out.exists():
                out = DATA / r["date"][:4] / f"{r['date']}-{slug}-{_n}.md"
                _n += 1
            if out.exists():
                skipped += 1
                continue
            if args.dry_run:
                print(f"[dry] {out.relative_to(ROOT)}  <- {r['title'][:40]}")
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(render_stub(r, slug), encoding="utf-8")
                ids["dt"].add(key_dt)
                ids["url"].add(r["url"].rstrip("/"))
            created += 1
    print(f"stubs: created={created} skipped_existing={skipped} (dry_run={args.dry_run})")


if __name__ == "__main__":
    main()
