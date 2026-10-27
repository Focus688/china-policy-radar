# SECURITY-NOTES · 安全威胁模型与已知残留风险

> 本仓库的文件经过前沿模型（Claude Opus）红队审计。审计发现、修复与残留风险记录在此，
> 不做静默处理。最近一轮：2026-10-27。

## 信任边界

1. **政策页面内容 = 不可信输入。** 抓回来的 HTML 可能包含任何文本，包括针对 Agent 的提示注入。
2. **脚本可能被 Agent 调用。** `fetch_gov.py <url>` 的 URL 常常来自 Agent 从页面/搜索结果里读到的字符串，
   因此必须把 URL 当作攻击者可控输入处理。
3. **本仓库的 GitHub Actions 每天自动运行并向仓库写状态。** 任何静默失败都会变成"看起来正常的丢数据"。

## 已修复（2026-10-27 审计）

| 位置 | 问题 | 修复 |
|---|---|---|
| `scripts/fetch_gov.py` `fetch()` | 任意 URL 直通 `urlopen`：`file://` 可读本机任意文件，重定向不校验，可打内网/云元数据 | scheme 白名单（http/https）+ 主机白名单（gov.cn 及其子域）+ 解析后 IP 必须 `is_global` + 重定向逐跳校验 |
| `scripts/fetch_gov.py` `--out` | 输出路径不受限，注入可写穿到 `state/seen.json`、`~/.bashrc`、脚本自身 | 解析后必须位于 `data/raw/` 内，否则拒绝执行 |
| `.github/workflows/daily-watch.yml` | `gh issue create ... || echo 忽略`：通知失败被吞，workflow 仍绿 | 带 label 失败降级重试一次；两次都失败 → job 红 |
| `.github/workflows/daily-watch.yml` | `--mark-seen` 在通知之前执行：通知失败仍提交状态 → 政策永久丢失 | 巡检只产出 result.json；**Issue 创建成功后**才 `--mark-seen-only`；提交步骤加 `if: success()` |
| `ALLOWED_HOST_SUFFIXES` 初版修复 | `endswith("gov.cn")` 会放行 `evilgov.cn` | 改为 `host == "gov.cn" or host.endswith(".gov.cn")` |

## 已知残留风险（明确接受，不装作没有）

1. **DNS rebinding / TOCTOU** — `validate_url` 的解析与 urllib 实际连接的解析是两次查询。
   消除需把 IP 固定进连接并校验 peer 证书，复杂度高于本场景收益（前提是攻击者能接管某个 `*.gov.cn` 子域）。
2. **HTML → 文本的粗糙清洗** — 只做正则去标签，不解析 DOM；恶意页面可构造畸形 HTML 干扰提取，
   但影响范围限于"提取质量"，不涉及执行。
3. **政策检索接口的合规瑕疵** — `sousuo.www.gov.cn` 的 robots.txt 为 `Disallow: /`，已在 `scripts/watch_gov.py`
   头部声明并限速（每日一次、请求间隔 ≥1s）。这不是安全风险，但同样是已知问题。

## 审计方法（可复现）

```bash
# 单文件（中转站上游 >4KB 会 500，脚本已限制每次送 2500 字符，超长请分批）
python3 ~/.hermes/scripts/opus_review.py scripts/fetch_gov.py --focus "SSRF/注入/静默失败"
```

判据：高危项为 0 才允许合并；中危需在 commit message 里说明为何暂不修。
