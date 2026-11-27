#!/usr/bin/env python3
"""IPinfo Lite 归因查询（免费档：国家级归属 + ASN，不限次数）。

用法:
    python3 scripts/ipinfo_lite.py 8.8.8.8 [更多IP...]
    python3 scripts/ipinfo_lite.py --token-env IPINFO_TOKEN 1.1.1.1

行为:
    - 设了 IPINFO_TOKEN（推荐，注册 ipinfo.io 免费拿）→ 走 Lite API，无限次
    - 没设 token → 回落 ipinfo.io 免费端点（无 token 约 1000 次/日，够兜底）
    - token 只通过 Authorization 头发送，不进 URL（URL 会落进代理/访问日志）

定位说明（2026-11-07 决策记录）:
    fetch_gov.py 的 SSRF 防护用的是 Python ipaddress 的 is_global，
    对「解析出的 IP 必须是公网地址」这一目的已经足够，不需要也不应该
    改成依赖外部 IP API（反而引入新失败点/隐私外泄点）。
    本脚本的用途是**归因与观察**：把访问来源 IP 标注国家/ASN，
    用于访问日志归因、流量地区判断，不进入安全校验路径。
"""
import argparse
import ipaddress
import json
import os
import sys
import urllib.parse
import urllib.request

TIMEOUT = 10
TOKEN_ENV = "IPINFO_TOKEN"


def lookup(ip: str, token: str) -> dict:
    headers = {"User-Agent": "china-policy-radar/1.0"}
    if token:
        url = f"https://api.ipinfo.io/lite/{urllib.parse.quote(ip)}"
        headers["Authorization"] = f"Bearer {token}"
    else:
        url = f"https://ipinfo.io/{urllib.parse.quote(ip)}/json"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    data["_source"] = "lite-api" if token else "free-endpoint(no-token)"
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ips", nargs="+", metavar="IP", help="要查询的 IPv4/IPv6 地址")
    ap.add_argument("--token-env", default=TOKEN_ENV, help=f"从哪个环境变量读 token（默认 {TOKEN_ENV}）")
    args = ap.parse_args()

    bad = []
    for s in args.ips:
        try:
            ipaddress.ip_address(s)
        except ValueError:
            bad.append(s)
    if bad:
        ap.error(f"不是合法 IP 地址: {bad}（--help 查看用法）")

    token = os.environ.get(args.token_env, "")
    failed = 0
    for ip in args.ips:
        try:
            d = lookup(ip, token)
            country = d.get("country", "?")
            asn = d.get("asn", d.get("org", "?"))
            print(f"{ip:>15}  {country:<4} {asn}  [{d['_source']}]")
        except Exception as e:  # noqa: BLE001 - CLI 工具，逐条报错继续
            failed += 1
            print(f"{ip:>15}  ERROR {e}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
