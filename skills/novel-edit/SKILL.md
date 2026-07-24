---
name: novel-edit
description: Professional editing workflow for completed or in-progress novel drafts. Use after draft/review/score when the user wants editorial assessment, developmental editing, line editing, copyediting, proofreading, human-primary polishing, or a publishing-grade revision plan. It does not generate new chapters by default; it turns reports, scene cards, reader feedback, and manuscript samples into a layered edit plan and task packets. Triggers 专业编辑, 发展性编辑, 行文编辑, 文案编辑, 校对, 精修, 主编轮次, editorial assessment, developmental edit, line edit, copyedit, proofread, publishing edit.
---

# novel-edit — 分层专业编辑流程

本 skill 负责把“审稿发现问题”变成可执行的编辑轮次。它不替代 `novel-review` 的硬伤质检，也不替代 `novel-score` 的市场判定；它解决的是：结构怎么改、场景怎么重排、段落怎么精修、投稿前怎么收尾。

产物落在作品根：

- `修订/edit_plan.json`
- `修订/编辑计划.md`
- `修订/editorial_letter.md`：主编信，先裁决方向、结构、人物弧和读者承诺。
- `修订/style_sheet.md`：术语、称谓、格式、设定和 AI/平台口径一致性表。
- `修订/proof_checklist.md`：投稿/导出前终校清单。
- `修订/edit_task_closure.jsonl`：P0/P1 编辑任务关闭记录。
- `修订/editor_queries.jsonl`：编辑/作者问答记录；未回答 query 会阻断专业编辑阶段进入发布。
- `修订/style_sheet_check.json` / `.md`：术语、称谓、格式、章节口径终校准备度检查。
- 可选：`修订/第NN章_line_edit_packet.md`

## 四层编辑

| 层级 | 解决什么 | 何时做 |
|---|---|---|
| `editorial_assessment` | 整体诊断：题旨、市场定位、主线、人物弧、读者承诺是否成立 | Demo 后、第一卷后、全稿后 |
| `developmental_edit` | 结构级重修：删合并章节、重排 arc、补动机、改结局、修主线 | score/review/balance 发现结构问题后 |
| `line_edit` | 行文级精修：场景节奏、对白潜台词、句式、五感、文风、去 AI 味 | 章节定稿前 |
| `copyedit_proofread` | 终稿清扫：错字、标点、术语、称谓、格式、章节标题 | 导出/投稿前 |

**冷却通读（cold read-through）——四层之前的传统前置**：全稿或整卷完成后，**隔一段时间**
（传统作家隔数周；生产线上至少隔一个批次/换一个会话）再从头到尾**只读不改**，用读者速度
通读，只做三类批注：①哪里想跳读（节奏）②哪里没看懂/记不起前情（衔接与信息管理）
③哪里情绪没到（落地拍缺失）。通读批注是 `editorial_assessment` 的第一手输入——跳过冷却
直接进四层，编辑会带着"写作时的记忆"补脑，看不见读者真实的断点。AI 生产线的等价物：
**换一个没有写作上下文的会话/代理做通读**（写作会话自读=作者热读，等于没冷却）；机检可先跑
`consistency_audit`（含 chapter_transition/plot_variety/prose_craft）把结构性问题清掉，
通读专注机检抓不到的主观断点。行文层的朗读 pass（读出来拗口的句子必有问题）放在
`line_edit` 内做，不单独成层。

**倒序审校（backwards editing）——`copyedit_proofread` 层的传统手法**：终稿清扫按
**章序倒着来**（最后一章→第一章；行文级也可段落倒序）。原理：顺读时叙事惯性会催眠
审校眼——读者被故事带着走就看不见错字与机械复读；倒序破坏叙事流，每一段都被当成
孤立文本冷眼检视（Writer's Digest / ALLi 编辑实务）。AI 生产线等价物：把 `copyedit`
批次任务按章号**降序**派发即可，零成本；`line_edit` 层不倒序（行文节奏需要顺读语境）。

## 工作流

1. 先跑已有证据层：`novel-review`、必要时 `novel-score`、`novel-balance`、`novel-simulate`、`novel-feedback`；多份报告已齐时先用 `novel-craft/scripts/revision_planner.py` 汇成 `修订/revision_plan.json`。
2. `edit_plan.py` 会优先读取 `修订/revision_plan.json`，并兜底读取 `评分/pacing_signals.json`、`评分/reader_panel_signals.json`、真实反馈、score/review 和 scene cards，避免节奏/留存信号停在各自报告里。
3. 若已有 `设定/scene_cards.json`，优先按场景诊断；缺场景卡时先用 `novel-craft/scripts/scene_cards.py scaffold` 生成骨架。
4. 生成分层编辑计划：

```bash
python3 skills/novel-edit/scripts/edit_plan.py "<作品根>"
```

5. 对进入行文精修的章节生成执行包：

```bash
python3 skills/novel-edit/scripts/edit_plan.py "<作品根>" --line-packet 4
```

`第NN章_line_edit_packet.md` 会汇总本章编辑任务、scene cards、人物内驱字段、`novel-observe` 观察素材和 `novel-aesthetic` 正向审美样本。改稿时在包内记录 before/after 与改动理由，避免“润色了一遍但不知道提升了什么”。
同一次运行也会写 `editorial_letter.md`、`style_sheet.md` 和 `proof_checklist.md`，把专业编辑的三类交付物落盘，避免只有任务 JSON 没有人类可执行的主编意见、统一表和终校表。

6. 按 `修订/编辑计划.md` 从上到下处理。结构级任务先于行文级任务；结构没定稿前不要花大量精力润句子。每处理完一条 P0/P1，关闭任务并留 before/after 或接受风险原因：

```bash
python3 skills/novel-edit/scripts/edit_plan.py "<作品根>" \
  --close-task EDIT-001 --status fixed --actor "<编辑/作者>" --note "<改法与回测>"
```

需要作者裁决的问题不要停在聊天里，登记为 editor query；回答后再关闭。未回答 query 会被 `author_workflow.py` 和 pipeline edit gate 当作阻断：

```bash
python3 skills/novel-edit/scripts/edit_plan.py "<作品根>" \
  --query-task EDIT-001 --query "结局是否允许主角牺牲师门名誉换取真相公开？" --query-severity P0 --asker "主编"
python3 skills/novel-edit/scripts/edit_plan.py "<作品根>" \
  --answer-query QUERY-001 --answer "允许，但必须保留主角承担后果的尾声。" --query-status answered
```

7. 终校前跑 style sheet 检查：

```bash
python3 skills/novel-edit/scripts/style_sheet_check.py "<作品根>" --write
```

8. 结构改完回跑 `novel-review` / `novel-score`；行文改完回跑 `mechanical_check.py`、文风漂移检查和必要的读者反馈复测；终稿前再跑 export gate。

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
