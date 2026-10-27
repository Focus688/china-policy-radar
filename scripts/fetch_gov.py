#!/usr/bin/env python3
"""
从中国政府网/新华社抓取政策原文，输出纯文本 + 元数据。

用法:
    python3 scripts/fetch_gov.py <url> [--out data/raw/xxx.txt]

设计原则:
  - 只抓公开页面，不绕过任何反爬
  - 保留原始 URL 作为来源凭证
  - 输出保留段落结构，便于后续条款切分
  - 【安全】URL 与输出路径都受围栏约束：只允许 http/https + *.gov.cn，
    解析后 IP 必须是公网地址，重定向逐跳校验；--out 只能落在 data/raw/ 下。
    （2026-10-27 红队审计修复：原实现可被提示注入驱动读取 file:// 本地文件、
    写穿任意路径。）
"""
import argparse
import ipaddress
import re
import socket
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = (ROOT / "data" / "raw").resolve()

ALLOWED_SCHEMES = ("http", "https")
ALLOWED_HOST_ROOT = "gov.cn"
MAX_REDIRECTS = 3


class UnsupportedURLError(ValueError):
    pass


def validate_url(url: str) -> str:
    """只放行 http(s)://*.gov.cn 且解析到公网 IP 的地址。

    残留风险（已知并接受，见 SECURITY-NOTES）：本函数校验用的 DNS 解析与
    urllib 实际连接时的解析是两次独立查询，理论上存在 DNS rebinding 的
    TOCTOU 窗口。攻击前提是攻击者能控制某个 *.gov.cn 子域的解析（子域接管），
    对本仓库「每日抓一次政务公开页」的场景，风险低于引入自签 TLS 固定 IP 的复杂度。
    若要彻底消除：解析一次并把 IP 固定进连接（自定义 HTTPHandler + peer 校验）。
    """
    parts = urllib.parse.urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsupportedURLError(f"scheme not allowed: {parts.scheme!r}")
    host = parts.hostname or ""
    if parts.username or parts.password:
        raise UnsupportedURLError("credentials in URL are not allowed")
    h = host.lower().rstrip(".")
    # 必须是 gov.cn 本身或其子域；不能用 endswith("gov.cn")，那会放行 evilgov.cn
    if not (h == ALLOWED_HOST_ROOT or h.endswith("." + ALLOWED_HOST_ROOT)):
        raise UnsupportedURLError(f"host not in allowlist: {host!r}")
    # 解析到公网地址，挡住内网/回环/链路本地/云元数据
    try:
        infos = socket.getaddrinfo(host, parts.port or (443 if parts.scheme == "https" else 80))
    except socket.gaierror as e:
        raise UnsupportedURLError(f"DNS resolution failed for {host!r}: {e}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise UnsupportedURLError(f"host {host!r} resolves to non-public address {ip}")
    return url


class _ValidatingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """重定向逐跳校验：不让 302 把请求带去非白名单主机。"""

    max_redirections = MAX_REDIRECTS

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_ValidatingRedirectHandler)


def fetch(url: str, timeout: int = 40) -> str:
    validate_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    raw = _OPENER.open(req, timeout=timeout).read()
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


def confined_out_path(raw_path: str) -> Path:
    """--out 只能写在 data/raw/ 之内。"""
    p = Path(raw_path)
    p = (p if p.is_absolute() else ROOT / p).resolve()
    if not p.is_relative_to(OUT_DIR):
        raise SystemExit(f"[fatal] --out must be inside {OUT_DIR}; got {p}")
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    try:
        html = fetch(args.url)
    except UnsupportedURLError as e:
        print(f"[fatal] refused URL: {e}", file=sys.stderr)
        return 2

    text = html_to_text(html)
    title = extract_title(html)

    header = f"# source: {args.url}\n# fetched: {date.today().isoformat()}\n# title: {title}\n\n"
    out = header + text

    if args.out:
        p = confined_out_path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(out, encoding="utf-8")
        print(f"saved {len(out)} chars -> {p}")
    else:
        print(out[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
