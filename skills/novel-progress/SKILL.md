---
name: novel-progress
description: 写小说(novel)「当前进度仪表盘 + 下一步建议」（只读 QA，不生产内容）。扫描写小说作品根的 `_进度.md` 章节流程矩阵，汇总每部小说的完成度 + 创作前沿（下一步该跑哪个 novel skill）+ 可并行事项，并给出可一键继续的建议。不改任何文件。Use when the user wants a novel project status overview or asks "what's next" for a novel project. Triggers novel-progress, 小说进度, 写作进度, 到哪了, 下一步做什么, 查进度.
---

# novel-progress — 小说进度仪表盘 + 下一步建议

你是小说线的**只读进度向导**。扫描 `写小说/` 下各剧作的 `_进度.md`，报告完成度并给出下一步建议。

## 输入 / 输出 / 读写边界

- **输入**：`写小说/<剧名>/_进度.md`。
- **输出**：终端摘要：阶段完成度、当前前沿、下一步建议。
- **读写边界**：严格只读；不写 `_进度.md`。

## 怎么跑

```bash
python3 skills/novel-progress/scan.py                 # 扫描 写小说/ 下所有项目
python3 skills/novel-progress/scan.py <作品根>         # 只看指定项目
```

## 列 → 该跑的 novel skill（路由表）

| 进度列 | 下一步 skill |
|---|---|
| 大纲 | `novel-create` |
| 细纲 | `novel-expand` |
| 正文初稿 | `novel-continue` |
| 机检 / 审稿 | `novel-review` |
| 评分 | `novel-score` |
| 改写 | `novel-rewrite` |
| 导出 | `novel-craft` |
