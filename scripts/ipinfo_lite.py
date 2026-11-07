#!/usr/bin/env python3
"""IPinfo Lite 归因查询（免费档：国家级归属 + ASN，不限次数）。

用法:
    python3 scripts/ipinfo_lite.py 8.8.8.8 [更多IP...]

行为:
    - 设了 IPINFO_TOKEN（推荐，注册 ipinfo.io 免费拿）→ 走 Lite API，无限次
    - 没设 token → 回落 ipinfo.io 免费端点（无 token 约 1000 次/日，够兜底）

定位说明（2026-11-07 决策记录）:
    fetch_gov.py 的 SSRF 防护用的是 Python ipaddress 的 is_global，
    对「解析出的 IP 必须是公网地址」这一目的已经足够，不需要也不应该
    改成依赖外部 IP API（反而引入新失败点/隐私外泄点）。
    本脚本的用途是**归因与观察**：把访问来源 IP 标注国家/ASN，
    用于访问日志归因、流量地区判断，不进入安全校验路径。
"""
import json
import os
import sys
import urllib.request

TOKEN = os.environ.get("IPINFO_TOKEN", "")


def lookup(ip: str) -> dict:
    if TOKEN:
        url = f"https://api.ipinfo.io/lite/{ip}?token={TOKEN}"
    else:
        url = f"https://ipinfo.io/{ip}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "china-policy-radar/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    data["_source"] = "lite-api" if TOKEN else "free-endpoint(no-token)"
    return data


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    for ip in sys.argv[1:]:
        try:
            d = lookup(ip)
            country = d.get("country", "?")
            asn = d.get("asn", d.get("org", "?"))
            print(f"{ip:>15}  {country:<4} {asn}  [{d['_source']}]")
        except Exception as e:  # noqa: BLE001 - CLI 工具，逐条报错继续
            print(f"{ip:>15}  ERROR {e}")


if __name__ == "__main__":
    main()
