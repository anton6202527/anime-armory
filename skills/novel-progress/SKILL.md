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

> `scan.py` 现在还会在每部作品末尾追加一行 `⛔ QA gate 阻断: N 项`（当 rights/review/score gate 有阻断时），让进度看板和 `novel-gate.py` 不再两套口径。

## 进度矩阵之外的「常被漏掉」分析仪（建议在写完一卷后主动提示）

进度矩阵只逐章跟踪 大纲→…→导出，**不含**下列项目级 QA。它们不是 gate，但写完一卷只跑 review/score 会漏掉节奏、伏笔、留存问题——当某卷正文初稿已成段时，主动建议用户补跑：

- `novel-wiki`：伏笔台账（planted→payoff 逾期）+ 设定一致性（`设定/foreshadowing_ledger.json` / `动态百科.json`）。
- `novel-balance`：节奏热力图 / 注水 / 烂尾预警（读 wiki 的伏笔回收率）。
- `novel-simulate`：模拟读者留存 / 找弃书点。

（三者都按 `目标平台` 自适应口径：品质向不会被爽文尺子误判。）
