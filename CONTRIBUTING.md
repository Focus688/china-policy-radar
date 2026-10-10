# 协作约定 · Contributing

> 本仓库目前有**多个维护者（含 AI Agent）在同一个工作目录协作**。没有约定就会互相覆盖。
> 本文件是**最低限度的协作纪律**，不追求流程完整。

---

## 一、当前维护方

| 维护方 | 说明 |
|---|---|
| 人类维护者 | 仓库所有者 |
| 协作 Agent（Vex 等） | 同机同目录运行，直接读写本仓库 |

**风险声明**：多个 Agent 共享同一工作目录时，**「本地提交」与「远端提交」可能分叉**，且一方不了解另一方的未推送改动。

---

## 二、硬性纪律（违反会破坏数据可信度）

### 1. 数据铁律

- **没有一手来源 URL 的条目，一律不收**
- **不得凭印象写数字**——所有数字必须来自实际打开的原文
- **未查到的口径必须写"未查到"**，不得推测填补
- **区分原文与分析**：分析段落必须以「**分析（非原文）**」开头

### 2. 更正纪律

- 发现错误 → **公开更正，不静默修改**
- 原始表述**保留在文件内**，加更正说明
- 同时在 [`CORRECTIONS.md`](CORRECTIONS.md) 追加条目

### 3. status 字段纪律

- `status: structured` = 含条款摘录（可引用条款）
- `status: pending` = 仅元数据 + 一手链接（**不得作任何条款性表述**）
- stub 转正时把 `status` 改为 `structured`，**不要留模糊状态**

---

## 三、避免互相覆盖的操作约定

### 推送前必做

```bash
git fetch origin           # 先看远端有没有别人的提交
git status && git log --oneline -3
git pull --rebase origin master   # 有分叉先变基
```

### 网络受限时的替代通道

`github.com:443` 被阻断时（GnuTLS recv error / 连接超时），可用 REST API 逐文件推送：

```bash
gh api -X PUT repos/<owner>/<repo>/contents/<path> --input - <<'JSON'
{"message": "...", "content": "<base64>", "sha": "<现有文件 sha>"}
JSON
```

⚠️ **代价**：API 推送会在远端产生**与本地不同的 commit SHA**，导致历史分叉。**每次用 API 推送后，必须在网络恢复时执行 `git fetch && git reset --hard origin/master` 对账**（本地未推的提交若内容已在远端，可直接丢弃）。

### 文件级分工建议

| 文件/目录 | 约定 |
|---|---|
| `scripts/` | 改动前先 `git log -1 -- <file>` 看最近改动者 |
| `AGENTS.md` / `README.md` / `llms.txt` | **入口文件**，改动影响 agent 消费，改动后须同步核对 `sitemap.md` |
| `index.json` | **由脚本生成，不要手改**——改 `data/` 后跑 `python3 scripts/build_index.py` |
| `state/seen.json` | 由巡检脚本维护 |

---

## 四、不要做的事

- ❌ **不要硬编码会漂移的数字**（如"共 91 条"）——以 `index.json` 的 `count_by_status` 为准
- ❌ 不要在数据文件里写未核实的内容后不标 `status: pending`
- ❌ 不要手改 `index.json`
- ❌ 不要把自媒体来源当一手来源；来源须分级（🟢官方 / 🟡媒体 / 🔴待核）
- ❌ 不要删除已有的更正记录

---

## 五、提交信息约定

```
<类型>(<范围>): <一句话>

类型：feat / fix / data / docs / compliance / ci
```

**准确比漂亮重要**：拿不准的地方在提交信息里写明"待核实"。

---

最后更新：2026-10-10
