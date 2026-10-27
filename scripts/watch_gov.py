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
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

REQUEST_INTERVAL = 1.2  # 秒；对政府网站保持克制

# 采集护栏（防假绿）：全站不可达时旧逻辑会打印 new_count=0 并 success，
# 与「今天真没有新政策」无法区分。低于下限一律按采集失败处理（非零退出）。
MIN_EXPECTED_SCAN = 30        # 单次巡检至少应采集到的条数（15 关键词实测稳定 ~120）
MAX_KEYWORD_FAILURES = 7      # 允许失败的检索词上限（超过半数即判定接口异常）

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
    failed = []
    for idx, kw in enumerate(KEYWORDS):
        if idx:
            time.sleep(REQUEST_INTERVAL)  # 限速：遵守采集合规纪律
        try:
            d = query(kw)
        except Exception as e:  # 网络问题不中断整体巡检
            failed.append(kw)
            print(f"[warn] keyword '{kw}' failed: {e}", file=sys.stderr)
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
    return found, failed


def mark_seen_only(result_path: Path) -> int:
    """通知成功后才调用的状态推进：只把本次已上报的条目写入 seen.json。

    （2026-10-27 红队审计修复：原流程在生成通知之前就 --mark-seen，
    通知失败时政策被标记已见却从未通知 → 永久丢失。）
    """
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("degraded"):
        print("[fatal] result file is degraded; refusing to advance state", file=sys.stderr)
        return 2
    STATE.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    before = len(state)
    for it in result.get("new", []):
        if it.get("url"):
            state[it["url"]] = it
    STATE.write_text(json.dumps(dict(sorted(state.items())), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[state] 上报成功后写入 {len(state) - before} 条，累计 {len(state)} 条。", file=sys.stderr)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mark-seen", action="store_true")
    ap.add_argument("--mark-seen-only", metavar="RESULT_JSON", default=None,
                    help="通知成功后推进状态：只标记该 result.json 中已上报的条目")
    args = ap.parse_args()

    if args.mark_seen_only:
        sys.exit(mark_seen_only(Path(args.mark_seen_only)))

    found, failed = collect()

    # ---- 采集护栏：让「采集失败」无法伪装成「今天没有新政策」 ----
    degraded = len(found) < MIN_EXPECTED_SCAN or len(failed) > MAX_KEYWORD_FAILURES
    if degraded:
        print(json.dumps({
            "checked": date.today().isoformat(),
            "total_scanned": len(found),
            "new_count": 0,
            "new": [],
            "degraded": True,
            "failed_keywords": failed,
            "error": f"scan below floor: {len(found)} < {MIN_EXPECTED_SCAN} or {len(failed)} keyword failures",
        }, ensure_ascii=False, indent=2))
        print(
            f"[fatal] 采集异常：采集到 {len(found)} 条（下限 {MIN_EXPECTED_SCAN}），"
            f"检索词失败 {len(failed)}/{len(KEYWORDS)}。状态文件未更新，按失败退出。",
            file=sys.stderr,
        )
        sys.exit(2)

    STATE.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else None

    def save(known: dict):
        STATE.write_text(json.dumps(dict(sorted(known.items())), ensure_ascii=False, indent=2), encoding="utf-8")

    if not isinstance(state, dict):
        save(found)
        print(f"[baseline] 首次运行，建立基线 {len(found)} 条，未上报。", file=sys.stderr)
        return

    seen = state
    new_items = [found[u] for u in found if u not in seen]
    new_items.sort(key=lambda x: x.get("date") or "", reverse=True)

    print(json.dumps({
        "checked": date.today().isoformat(),
        "total_scanned": len(found),
        "new_count": len(new_items),
        "new": new_items,
        "degraded": False,
    }, ensure_ascii=False, indent=2))

    if args.mark_seen:
        seen.update(found)
        save(seen)
        print(f"[state] 已写入，累计 {len(seen)} 条。", file=sys.stderr)


if __name__ == "__main__":
    main()
