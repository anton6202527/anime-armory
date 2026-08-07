---
name: novel-simulate
description: 合成叙事探针（兼容“模拟读者”叫法）— 用不同阅读偏好视角和可复核的表面信号提出弃书点、理解障碍、可预测性等候选假设。输出不是抽样读者、真实留存预测或统计证据，不参与自动评分；真实平台/内测数据走 novel-feedback。Use when asked to 模拟读者, 合成读者探针, 读者视角复核, 弃书点假设, 读者怎么看, 虚拟试读, simulate readers, narrative probes, mock audience. Triggers 模拟读者, 合成探针, 虚拟试读, 读者反馈, 弃书点, 可预测性, novel simulate, reader panel.
---

# novel-simulate — 多代理人“模拟读者”测试

这是一个**合成、定性、待验证**的编辑工具：用多种阅读偏好提出“值得去正文里复核什么”的问题。它不模拟出具有统计代表性的真实读者，也不输出真实留存概率。

## 读者人格库

| 人格 ID | 名称 | 关注点 | 典型反馈风格 |
|---|---|---|---|
| `rookie` | 小白爽文党 | 节奏、升级感、反杀、不憋屈 | "爽！打脸真快，后面还要更爽。" |
| `logic` | 逻辑考据党 | 设定自洽、力量体系、智斗逻辑、无降智 | "这里主角的动机不合理，逻辑有硬伤。" |
| `emote` | 情感/互动党 | 人物弧光、CP感、情感张力、金句 | "这段互动太好磕了，细节很有质感。" |
| `critic` | 毒舌老书虫 | 同质化套路、文笔质感、新意 | "又是这个老梗，开头有点劝退。" |

## 工作流

### 1. 发起模拟试读
```bash
python3 skills/novel/novel-simulate/scripts/simulate_panel.py "<作品根>" [--scope opening|chapter] [--personas rookie,logic,emote]
```
- **opening**：读前 3 章，模拟新读者的留存决策。
- **chapter**：读指定章节，模拟追更读者的反馈。
- **按目标平台定默认视角集与代理公式**：不传 `--personas` 时，脚本读 `目标平台` 选择点（经 `keyword_banks.classify_platform` 归一为 `商业爽文向`/`品质向`，口径同 novel-score）选默认视角。兼容字段 `retention_prior` 在 schema v2 中等同 `retention_proxy`，只是关键词、章末标记和文本多样性的表面代理，不是留存预测。
- 关键词词表来自单一定义源 `skills/novel/_lib/keyword_banks.py`（与 novel-balance/novel-promote 共用）。

### 2. 产出报告（确定性信号 + LLM 定性骨架）
脚本产两份：
- `评分/读者试读反馈_<日期>.md`（人读）：每个人格一节，**确定性信号**（关注词密度/钩子强度/套路密度）已算好，**定性心声 / 弃书点**留「【AI 代理填写】」占位 → AI 代理按人格 prompt 读文本补全（同 `skills/novel/novel-craft/references/选择点与偏好.md` 的交互节点约定）。
- `评分/reader_panel_signals.json`（机读）：含各视角信号和 `retention_proxy`（保留 `retention_prior` 兼容字段），并明确 `evidence_type=synthetic_probe`、`validation_status=unvalidated`、`decision_authority=context_only`、`numeric_score_eligible=false`。`novel-score` 只展示上下文、不自动调分；QA gate 会写 `SIMULATE-SIGNAL-ONLY` warning。补完「人格心声 / 弃书点」后仍属于合成证据，不会升级成真实读者面板。

报告含：总评(受众兼容度) / 爽点捕获图 / 弃书点预警 / 各人格针对性改法。

### 3. 行为式读者度量（2026-07·补"可预测性"缺失维度）

传统"扮演读者发感想"只产主观定性；行为式协议改测**读者的预测行为**（arXiv 2412.15239 想象
续写预测 engagement + arXiv 2604.09854 Spoiler Alert 张力指标——后者是目前唯一能把人类小说
正确排在 LLM 产出之上的自动指标，抓的正是评分模型抓不到的"套路化/可预测"维度）：

1. **面板预测**（AI 代理执行）：读到第 NN 章末，每个人格写 2-5 条"下一章会发生什么"的
   一句话短预测（全面板合计 ≥5 条，10-20 条更稳），落盘
   `评分/reader_predictions_第NN章.json`（`{chapter, predictions:[{persona,text}…]}`）。
   **禁止先看下一章再写预测**（污染度量）；建议在关键节点章（黄金三章末/弧段高潮前）采集。
2. **确定性度量**：`python3 skills/novel/novel-simulate/scripts/behavioral_signals.py "<作品根>"`
   - **悬念值** = 预测两两相异度（全员猜同一方向 → `suspense_collapse` 建议级：只剩一条明线）；
   - **意外度** = 1 − 预测对真实下一章的最大包含度（真实剧情被猜中 → `predictable_plot`
     建议级：剧情太顺，考虑做一次预期颠覆）。
   输出 `评分/behavioral_signals.json`；advisory 恒不阻断，字面近似只报低分候选（换词猜中会漏，
   高分不认证为"真悬念"）。

### 4. 标准问卷协议（beta reader 六问·2026-07）

传统 beta reader 实务有一组固定问题（Jane Friedman/FoxPrint 等业界口径），比"自由发感想"
更能定位问题。每个人格读完第 NN 章后**逐人格**作答六问，落盘
`评分/reader_survey_第NN章.json`（schema 稳定，`behavioral_signals.py` 依赖它做确定性聚合）：

```json
{"schema_version": 1, "kind": "novel_reader_survey", "chapter": 7,
 "responses": [
   {"persona": "rookie",
    "bored":      {"span": "中段比武排位流水账", "note": "想跳过"},
    "confused":   null,
    "disbelief":  {"span": "林昭突然原谅仇人", "characters": ["林昭"], "note": "前文恨意没消解"},
    "favorite_character":  {"name": "苏九", "reason": "毒舌但护短"},
    "annoying_character":  {"name": "王管家", "reason": "工具人感重"},
    "recall": "上一章主角擂台反杀镇北王，师妹身份暴露。"}
 ]}
```

- **六问**：bored（哪里想放下/走神）、confused（哪里困惑到回读）、disbelief（哪里不再相信，
  须点名人物）、favorite/annoying 角色+一句话原因、prediction（走第 3 节现有
  `reader_predictions_第NN章.json`，**不建重复字段**）、recall（复述上一章）。
- 无该项感受填 `null`；span 摘录正文短语（供修订工单定位），不超过 30 字。
- **recall 铁律**：凭记忆复述**上一章**发生了什么（一两句），**禁止回看上一章原文再作答**
  （污染记忆留存度量，同预测协议的禁看铁律）。
- 聚合（跑同一条 `behavioral_signals.py` 命令）产四个确定性信号（全建议级）：
  `reader_bored_run`（连续 ≥2 章过半读者 bored → 弃书风险段）、`reader_confusion_spike`
  （单章过半 confused → 信息管理事故）、`reader_disbelief`（点名人物的不信 → OOC 候选）、
  `recall_failure`（过半读者复述对上一章 2-gram 包含度 < 阈值 → 该章信息未留存）。
  阈值 env：`NOVEL_BEHAV_BORED_RUN`/`NOVEL_BEHAV_MAJORITY`/`NOVEL_BEHAV_RECALL_MIN`/
  `NOVEL_BEHAV_MIN_SURVEY`。

## 何时使用

- **Demo Gate 之后**：在投入大量精力写全本前，先看看这组 Demo 章是否能抓住预期受众。
- **重大转折章之后**：验证读者的反应是否如作者所愿（是被惊艳还是被劝退）。
- **尚无真实数据时**：已有完读率、弃读、评论导出时先走 `novel-feedback`；真实反馈权重高于模拟试读。

## 详细参考
- 人格库定义、信号 schema、retention_prior 公式、判读铁律：`references/reader-personas.md`

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把模拟角色当成真实读者样本 | 它只代表模型按提示生成的假设；用正文证据和真人反馈验证 |
| 人格选择单一 | 至少选择 3 个差异化的人格，以获得全面的视角 |
| 把 `reader_panel_signals.json` 当留存预测或调分依据 | 它始终是 synthetic/context-only；只生成复核问题，不自动改分 |
