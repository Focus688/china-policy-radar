#!/usr/bin/env python3
"""
外链失效巡检：检查仓库内所有外链是否可访问。

用法:
    python3 scripts/check_links.py              # 全量检查（慢）
    python3 scripts/check_links.py --limit 20   # 只查前 20 条（快速自检）
    python3 scripts/check_links.py --json       # 输出 JSON

设计要点:
  - 从 index.json 与 markdown 文件中抽取 http(s) 链接
  - 逐个 HEAD/GET 探测，限速 1s，超时 15s
  - 区分「死链」（404/410）与「不可达」（403/429/超时/SSL）——后者不一定是死链
  - 只报告，不自动修改
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; china-policy-radar-linkcheck/1.0)"
INTERVAL = 1.0
TIMEOUT = 15
SKIP_HOSTS = ("localhost", "127.0.0.1", "example.com")


def collect_links():
    """从 index.json 与所有 markdown 中抽取链接 -> {url: [来源文件]}"""
    found = {}

    def add(url, src):
        url = url.rstrip(").,;")
        if not url.startswith("http"):
            return
        if any(h in url for h in SKIP_HOSTS):
            return
        found.setdefault(url, set()).add(src)

    idx = ROOT / "index.json"
    if idx.exists():
        for e in json.loads(idx.read_text(encoding="utf-8")).get("entries", []):
            for s in e.get("sources", []):
                if s.get("url"):
                    add(s["url"], "index.json")

    for p in ROOT.rglob("*.md"):
        if ".git" in p.parts:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"\]\((https?://[^)\s]+)\)", text):
            add(m.group(1), str(p.relative_to(ROOT)))

    return {u: sorted(v) for u, v in found.items()}


def probe(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, "ok"
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return e.code, "dead"
        return e.code, "blocked"      # 403/429/5xx 多为反爬或临时不可达
    except Exception as e:
        return None, f"unreachable: {type(e).__name__}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    links = collect_links()
    urls = sorted(links)
    if args.limit:
        urls = urls[: args.limit]

    results = []
    for i, u in enumerate(urls):
        if i:
            time.sleep(INTERVAL)
        status, verdict = probe(u)
        results.append({"url": u, "status": status, "verdict": verdict, "in": links[u]})
        if not args.json:
            mark = {"ok": "OK  ", "dead": "DEAD", "blocked": "BLK "}.get(verdict, "ERR ")
            print(f"{mark} {status} {u[:100]}")

    dead = [r for r in results if r["verdict"] == "dead"]
    blocked = [r for r in results if r["verdict"] not in ("ok", "dead")]

    if args.json:
        print(json.dumps({"checked": len(results), "dead": dead, "blocked": blocked},
                         ensure_ascii=False, indent=2))
    else:
        print(f"\n检查 {len(results)} 条 | 死链 {len(dead)} | 不可达 {len(blocked)}")
        if dead:
            print("\n=== 死链（需替换来源）===")
            for r in dead:
                print(f"  {r['status']} {r['url']}")
                print(f"      出现在: {', '.join(r['in'][:3])}")

    # 死链存在时返回非零，便于 CI 报警
    return 1 if dead else 0


if __name__ == "__main__":
    sys.exit(main())
