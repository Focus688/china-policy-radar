# 站点地图 · Sitemap

> 本仓库全部入口一览。**数量以 [`index.json`](index.json) 的 `count_by_status` 为准**（本文件不硬编码会漂移的数字）。

---

## 给 AI Agent 的入口（首选）

| 路径 | 用途 |
|---|---|
| [`AGENTS.md`](AGENTS.md) | **agent 接入说明**：格式约定、三类内容可信度分级、引用格式、已知限制 |
| [`index.json`](index.json) | **机器可读索引**：全部条目（含 `status`、`doc_number`、`sources`）|
| [`llms.txt`](llms.txt) | 仓库总览（GEO 入口）|

**读取顺序**：`AGENTS.md` → `index.json` → 按需读 `data/` 条目 → 需判断时读 `scoreboard/`。

---

## 政策数据

| 路径 | 内容 |
|---|---|
| [`data/<年>/`](data/) | 结构化政策条目（`status: structured` 含条款；`status: pending` 仅元数据）|
| [`catalog/2024-now-central-policies.md`](catalog/2024-now-central-policies.md) | 2024 至今中央及部委政策清单（机器扫描）|
| [`catalog/central-ai-tech-2024-2026.md`](catalog/central-ai-tech-2024-2026.md) | 26 份重点文件（人工核验）|
| [`diffs/AI-plus-timeline.md`](diffs/AI-plus-timeline.md) | 「人工智能+」用词演进 + 部委专项文件 |
| [`schema/policy.schema.json`](schema/policy.schema.json) | 数据格式定义 |

## 可申报通道

| 路径 | 内容 |
|---|---|
| [`CHANNELS.md`](CHANNELS.md) | 资金与项目通道清单 |

## 专题

| 路径 | 内容 |
|---|---|
| [`topics/OPC-one-person-company.md`](topics/OPC-one-person-company.md) | OPC 专题索引 |
| [`topics/OPC-policies.md`](topics/OPC-policies.md) | OPC 政策清单（国家/省/市 16 份）|
| [`topics/OPC-subsidy-comparison.md`](topics/OPC-subsidy-comparison.md) | 补贴口径分级（真给钱 vs 挂牌子）|
| [`topics/OPC-eligibility.md`](topics/OPC-eligibility.md) | 申报条件（户籍 vs 注册地、在职可否）|
| [`topics/OPC-cases.md`](topics/OPC-cases.md) | 案例清单（企业 + 社区/园区）|
| [`topics/OPC-dongguan.md`](topics/OPC-dongguan.md) | 东莞专场 |
| [`topics/OPC-community-funding.md`](topics/OPC-community-funding.md) | 给社区运营方/服务提供方的资金通道 |
| [`topics/OPC-overseas.md`](topics/OPC-overseas.md) | 海外一人公司对照 |

## 框架与方法

| 路径 | 内容 |
|---|---|
| [`frameworks/sector-entry-evaluation.md`](frameworks/sector-entry-evaluation.md) | 赛道进入评估框架（退出残值判据）|
| [`DATA-SOURCES.md`](DATA-SOURCES.md) | 六环证据链数据源矩阵 |
| [`scoreboard/`](scoreboard/) | 政策回测记分牌 |
| [`ROADMAP.md`](ROADMAP.md) | 长线路线图 |
| [`SUCCESS.md`](SUCCESS.md) | 本仓库自身的成功判据与失效判据 |

## 治理

| 路径 | 内容 |
|---|---|
| [`DISCLAIMER.md`](DISCLAIMER.md) | 免责声明（非官方、不构成投资/法律/申报建议）|
| [`COMPLIANCE.md`](COMPLIANCE.md) | 采集合规说明（含已知瑕疵披露）|
| [`LICENSE`](LICENSE) | 分层授权 |
| [`CORRECTIONS.md`](CORRECTIONS.md) | **更正记录**（公开、不静默修改）|
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | 协作与分工约定 |

## 工具

| 路径 | 用途 |
|---|---|
| `scripts/fetch_gov.py` | 抓取单篇政策原文 |
| `scripts/watch_gov.py` | 政策巡检（发现新文件）|
| `scripts/build_catalog.py` | 生成政策清单 |
| `scripts/build_stubs.py` | catalog → data stub 生成 |
| `scripts/build_index.py` | 生成 index.json |
| `scripts/check_links.py` | 外部链接失效巡检 |
| `state/seen.json` | 巡检状态 |

---

最后更新：2026-10-10
