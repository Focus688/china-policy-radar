#!/usr/bin/env python3
"""
从中国政府网/新华社抓取政策原文，输出纯文本 + 元数据。

用法:
    python3 scripts/fetch_gov.py <url> [--out data/raw/xxx.txt]

设计原则:
  - 只抓公开页面，不绕过任何反爬
  - 保留原始 URL 作为来源凭证
  - 输出保留段落结构，便于后续条款切分
"""
import argparse
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def fetch(url: str, timeout: int = 40) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    raw = urllib.request.urlopen(req, timeout=timeout).read()
    for enc in ("utf-8", "gb18030", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "ignore")


def html_to_text(html: str) -> str:
    html = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S | re.I)
    html = re.sub(r"<br\s*/?>|</p>|</div>|</h\d>", "\n", html, flags=re.I)
    text = re.sub(r"<[^>]+>", "", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&ldquo;", "「").replace("&rdquo;", "」")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.S | re.I)
    return m.group(1).strip() if m else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    html = fetch(args.url)
    text = html_to_text(html)
    title = extract_title(html)

    header = f"# source: {args.url}\n# fetched: {date.today().isoformat()}\n# title: {title}\n\n"
    out = header + text

    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(out, encoding="utf-8")
        print(f"saved {len(out)} chars -> {p}")
    else:
        print(out[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
