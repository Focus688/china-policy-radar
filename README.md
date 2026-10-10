# 中国政策雷达 · China Policy Radar

> 把中国的政策文件变成**结构化、可追溯、机器可读**的数据层。
> 每条结论都带原始出处链接。没有引用，不予收录。

A machine-readable, source-cited index of Chinese policy documents — built for humans **and AI agents**.

[![update](https://img.shields.io/badge/更新-每日-blue)]() [![license](https://img.shields.io/badge/license-CC%20BY%204.0-green)]()

---

## 为什么存在这个仓库

政策解读的文章每天有几百篇，但**没有一篇能被机器可靠地引用**——它们没有原文链接、没有条款定位、没有版本对比。

这个仓库做三件别人不做的事：

1. **一手原文 + 可追溯引用**：不转述、不洗稿，每条都是一手文件的结构化摘录，附官方来源 URL
2. **政策 Diff**：追踪同一主题文件的版本演进——哪条是新加的，哪条被删了
3. **落地链条**：中央文件 → 部委细则 → 地方实施方案，三级对照

## 目录结构

```
data/<年>/<发布日期>-<slug>.md     一条政策 = 一个文件
schema/policy.schema.json          数据格式定义
scripts/fetch_gov.py               从政府网抓取原文
scripts/structure.py               原文 → 结构化条目
llms.txt                           给 AI agent 的索引（GEO）
ROADMAP.md                         长线路线图
```

## 数据规范（摘要）

每条政策记录必须包含：

| 字段 | 说明 |
|---|---|
| `title` | 文件全称，与原文一致 |
| `issuer` | 发文机关 |
| `date` | 印发日期（YYYY-MM-DD） |
| `sources[]` | **至少一个一手来源 URL**（gov.cn / 新华社 / 部委官网）|
| `clauses[]` | 条款级摘录，含条款编号 |
| `tags[]` | 主题标签 |

> 铁律：**没有一手来源 URL 的条目，一律不收。** 宁可少，不可假。

## 免责声明

本项目仅整理**公开发布**的政府文件原文与公开数据，供研究与信息检索使用。
所有分析不构成投资建议。政策文本以官方发布为准。

## License

文档内容 CC BY 4.0；脚本代码 MIT。
