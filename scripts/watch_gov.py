#!/usr/bin/env python3
"""
政策巡检：通过中国政府网公开检索接口，发现新发布的中央/部委政策。

用法:
    python3 scripts/watch_gov.py                 # 巡检，打印新发现
    python3 scripts/watch_gov.py --mark-seen     # 巡检并把新条目写入 state/seen.json

设计要点:
  - 使用 gov.cn 公开检索接口（无需登录、无需付费）
  - 已知文件 URL 持久化到 state/seen.json，避免重复上报
  - 首次运行时把当前全部结果作为基线写入，不上报（避免噪音）
  - 输出 JSON，便于 GitHub Action 生成 Issue

⚠️ 采集合规声明（详见仓库 COMPLIANCE.md）:
  - sousuo.www.gov.cn 的 robots.txt 声明 Disallow: /，本脚本使用该接口属已知合规瑕疵
  - 缓解措施：每日仅运行一次；单次请求间隔 >= 1 秒；UA 标明项目身份便于站点识别
  - 如站点管理方提出异议，立即停止使用该接口
  - 若接入方自行使用本脚本，请自行评估并承担合规责任
"""
import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

REQUEST_INTERVAL = 1.2  # 秒；对政府网站保持克制

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "seen.json"

API = "https://sousuo.www.gov.cn/search-gov/data"
KEYWORDS = [
    "人工智能", "新质生产力", "机器人", "算力", "数据要素",
    "专精特新", "低空经济", "商业航天", "生物制造", "具身智能",
    "量子科技", "6G", "智能制造", "设备更新", "新型工业化",
]
CATS = ["gongwen", "bumenfile"]


def query(q: str, n: int = 20):
    params = {
        "t": "zhengcelibrary", "q": q, "timetype": "timeqb",
        "sort": "pubtime", "sortType": "1", "searchfield": "title",
        "p": "1", "n": str(n),
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; china-policy-radar/1.0)",
        "Referer": "https://sousuo.www.gov.cn/",
    })
    raw = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")
    return json.loads(raw)


def strip_tags(s: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", s or "")


def collect():
    found = {}
    for idx, kw in enumerate(KEYWORDS):
        if idx:
            time.sleep(REQUEST_INTERVAL)  # 限速：遵守采集合规纪律
        try:
            d = query(kw)
        except Exception as e:  # 网络问题不中断整体巡检
            print(f"[warn] keyword '{kw}' failed: {e}")
            continue
        cats = (d.get("searchVO") or {}).get("catMap") or {}
        for cat in CATS:
            node = cats.get(cat) or {}
            for it in (node.get("listVO") or []):
                u = it.get("url")
                if not u:
                    continue
                found[u] = {
                    "url": u,
                    "title": strip_tags(it.get("title")),
                    "date": it.get("pubtimeStr"),
                    "doc_number": it.get("pcode"),
                    "matched_keyword": kw,
                    "category": cat,
                }
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mark-seen", action="store_true")
    args = ap.parse_args()

    found = collect()
    STATE.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else None

    def save(known: dict):
        STATE.write_text(json.dumps(dict(sorted(known.items())), ensure_ascii=False, indent=2), encoding="utf-8")

    if not isinstance(state, dict):
        save(found)
        print(f"[baseline] 首次运行，建立基线 {len(found)} 条，未上报。")
        return

    seen = state
    new_items = [found[u] for u in found if u not in seen]
    new_items.sort(key=lambda x: x.get("date") or "", reverse=True)

    print(json.dumps({
        "checked": date.today().isoformat(),
        "total_scanned": len(found),
        "new_count": len(new_items),
        "new": new_items,
    }, ensure_ascii=False, indent=2))

    if args.mark_seen:
        seen.update(found)
        save(seen)
        print(f"[state] 已写入，累计 {len(seen)} 条。")


if __name__ == "__main__":
    main()
