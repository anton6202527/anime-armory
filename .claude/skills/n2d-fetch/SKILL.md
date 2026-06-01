---
name: n2d-fetch
description: Stage 0.5 of novel2drama pipeline — given a book name (or chapter-index URL), find and fetch a public-domain novel's full text from the web and write it as .txt + .docx into artifacts/<书名>/小说/, ready for /n2d-script. Defaults to public-domain / openly-licensed sources (古登堡 Gutenberg / 中文维基文库 Wikisource); refuses known paywalled sites. Use when given only a book name with no local file, or asked 抓小说/下载小说/找小说原文/联网取书. Triggers 抓小说, 下载小说, 找原文, 联网取书, 公版小说, Gutenberg, 维基文库, fetch novel.
---

# n2d-fetch — Stage 0.5：联网取书

给定**书名**（或章节目录页 URL）→ 联网抓公版小说全文 → 落 `artifacts/<书名>/小说/<书名>.txt` + `.docx` → 直接接 `/n2d-script`。

## 合法性铁律（不可逾越）

- **只抓公版 / 开放授权来源**：已过版权期的经典、CC 授权、作者自授权、或用户明确声明有权使用的文本。
- 脚本对已知付费墙/反爬站（起点、番茄、晋江 等，见 `references/sources.md`）**直接拒抓**，不替用户规避。
- 通用兜底抓**非公版** URL 时，抓取前必须让用户**声明有权使用**（CLI `--i-have-rights`）。
- 不实现绕过反爬 / 付费墙 / 登录墙的逻辑。

## 工作流

### 第 1 步 — 锁定唯一一本

- **用户给了书名**：用 WebSearch/WebFetch 在公版站检索，列出候选表，每个候选**强制带区分维度**：作者、来源站、字数/卷数、译本、全本 vs 节选。让用户确认唯一一本并拿到**章节目录页 / 作品页 URL**。优先推荐 中文维基文库（中文公版）/ Project Gutenberg（英文公版）。
- **用户已给 URL**：跳过搜索，直接进第 2 步。
- 命中付费墙站 → 解释铁律，引导改用公版来源。

### 第 2 步 — 跑脚本抓取 + 转格式

```bash
python3 <skill>/scripts/fetch_novel.py "<目录页URL>" --name "<书名>" [--out <作品根>] [--source auto|gutenberg|wikisource|generic]
```

- 缺依赖 → 脚本打印 `pip install ...`，照做后重跑。
- 通用兜底非公版来源 → 脚本要求 `--i-have-rights`（仅在用户已声明授权时加）。
- 脚本逐章打印抓取状态（ok/empty/fail），完成后打印 txt/docx 路径。

### 第 3 步 — 报告 + 推进

报告：书名、来源、章节数、字数、两个输出路径。下一步建议：
```
/n2d-script <作品根>   ← Stage 1 拆集 + 精修第1集
```

## 输出约定

- 落点 `artifacts/<书名>/小说/`（与 n2d 目录铁律一致，作品根 = `小说/` 的父级）。
- txt 章节用 `第N章 标题` 行（`split_novel.py` 的 `CHAPTER_RE` 可识别）；文件头是 provenance 注释块，会被 `strip_frontmatter` 自动跳过。
- docx 章节标题用 Heading 1，正文段落化。
- 详见 `references/formats.md`。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 直接抓付费墙站 | 拒绝；引导公版来源 |
| 把搜索得到的第一个结果就抓 | 必先列候选 + 用户确认唯一一本 |
| 通用兜底硬抓非公版还不声明授权 | 必须 `--i-have-rights`（用户已确认有权时） |
| 输出散落 | 一律落 `artifacts/<书名>/小说/` |
| 抓完不提示下一步 | 报告后建议 `/n2d-script <作品根>` |
