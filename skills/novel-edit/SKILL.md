---
name: novel-edit
description: Professional editing workflow for completed or in-progress novel drafts. Use after draft/review/score when the user wants editorial assessment, developmental editing, line editing, copyediting, proofreading, human-primary polishing, or a publishing-grade revision plan. It does not generate new chapters by default; it turns reports, scene cards, reader feedback, and manuscript samples into a layered edit plan and task packets. Triggers 专业编辑, 发展性编辑, 行文编辑, 文案编辑, 校对, 精修, 主编轮次, editorial assessment, developmental edit, line edit, copyedit, proofread, publishing edit.
---

# novel-edit — 分层专业编辑流程

本 skill 负责把“审稿发现问题”变成可执行的编辑轮次。它不替代 `novel-review` 的硬伤质检，也不替代 `novel-score` 的市场判定；它解决的是：结构怎么改、场景怎么重排、段落怎么精修、投稿前怎么收尾。

产物落在作品根：

- `修订/edit_plan.json`
- `修订/编辑计划.md`
- 可选：`修订/第NN章_line_edit_packet.md`

## 四层编辑

| 层级 | 解决什么 | 何时做 |
|---|---|---|
| `editorial_assessment` | 整体诊断：题旨、市场定位、主线、人物弧、读者承诺是否成立 | Demo 后、第一卷后、全稿后 |
| `developmental_edit` | 结构级重修：删合并章节、重排 arc、补动机、改结局、修主线 | score/review/balance 发现结构问题后 |
| `line_edit` | 行文级精修：场景节奏、对白潜台词、句式、五感、文风、去 AI 味 | 章节定稿前 |
| `copyedit_proofread` | 终稿清扫：错字、标点、术语、称谓、格式、章节标题 | 导出/投稿前 |

## 工作流

1. 先跑已有证据层：`novel-review`、必要时 `novel-score`、`novel-balance`、`novel-feedback`。
2. 若已有 `设定/scene_cards.json`，优先按场景诊断；缺场景卡时先用 `novel-craft/scripts/scene_cards.py scaffold` 生成骨架。
3. 生成分层编辑计划：

```bash
python3 skills/novel-edit/scripts/edit_plan.py "<作品根>"
```

4. 按 `修订/编辑计划.md` 从上到下处理。结构级任务先于行文级任务；结构没定稿前不要花大量精力润句子。
5. 结构改完回跑 `novel-review` / `novel-score`；行文改完回跑 `mechanical_check.py` 和文风漂移检查；终稿前再跑 export gate。

## 人类主创模式

当 `_设置.md` 的 `文本主创模式=人类主创` 或目标平台对 AI 正文敏感时，本 skill 的输出只作为编辑任务、问题清单和修改建议；最终正文由人类作者改写并承担署名责任。AI 可以辅助诊断、比对、找错和提出改法，但不要直接把 AI 大段正文当投稿稿件。

## 与其它 skill 的边界

- `novel-review`：找硬伤并生成 schema 化 QA 报告。
- `novel-edit`：把多份报告转成编辑轮次和修订任务。
- `novel-rewrite`：执行结构级改写或重开版本。
- `novel-craft`：提供写章任务包、scene cards、state ledger、导出 gate。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 结构未定就逐句润色 | 先 developmental edit，再 line edit |
| 把审稿意见当编辑计划 | 审稿是发现问题；编辑计划要排序、分层、给回流阶段 |
| 一轮改完直接投稿 | 至少回跑 review/export gate，平台项目还要复核 AI 使用披露和合规 profile |
