---
name: novel-simulate
description: 多代理人"模拟读者"测试 — 在正式发布前进行虚拟试读会。通过构建不同人格偏好的 AI 读者(小白、逻辑党、嗑糖党等),提供多维度的定性反馈。帮助作者提前识别弃书点、验证爽点捕获率、评估受众兼容性。Use when asked to 模拟读者, 读者反馈, 试读, 测一下留存, 读者怎么看, 虚拟试读, simulate readers, reader feedback, mock audience. Triggers 模拟读者, 虚拟试读, 读者反馈, 弃书点, 爽点捕获, 留存测试, novel simulate, reader panel.
---

# novel-simulate — 多代理人“模拟读者”测试

这是一种**定性**的评估工具，旨在模拟真实读者阅读时的心理活动。

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
python3 skills/novel-simulate/scripts/simulate_panel.py "<作品根>" [--scope opening|chapter] [--personas rookie,logic,emote]
```
- **opening**：读前 3 章，模拟新读者的留存决策。
- **chapter**：读指定章节，模拟追更读者的反馈。

### 2. 产出报告（确定性信号 + LLM 定性骨架）
脚本产两份：
- `评分/读者试读反馈_<日期>.md`（人读）：每个人格一节，**确定性信号**（关注词密度/钩子强度/套路密度）已算好，**定性心声 / 弃书点**留「【AI 代理填写】」占位 → AI 代理按人格 prompt 读文本补全（同 `skills/novel-craft/references/选择点与偏好.md` 的交互节点约定）。
- `评分/reader_panel_signals.json`（机读）：含各人格信号 + `retention_prior`（爽点密度·钩子·多样性·套路加权的留存近似），并明确 `analysis_mode=signal_only`、`signal_only=true`、`qualitative_completed=false`、`personas_completed=[]`。供 `novel-score` 作为低权重留存先验；只有报告里的「人格心声 / 弃书点」被 AI/人工补完并回写状态后，才算完整模拟读者面板。

报告含：总评(受众兼容度) / 爽点捕获图 / 弃书点预警 / 各人格针对性改法。

## 何时使用

- **Demo Gate 之后**：在投入大量精力写全本前，先看看这组 Demo 章是否能抓住预期受众。
- **重大转折章之后**：验证读者的反应是否如作者所愿（是被惊艳还是被劝退）。

## 详细参考
- 人格库定义、信号 schema、retention_prior 公式、判读铁律：`references/reader-personas.md`

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把模拟读者当审稿机 | 读者反馈是主观的，不一定“正确”，但代表了“感受” |
| 人格选择单一 | 至少选择 3 个差异化的人格，以获得全面的视角 |
| 把 `reader_panel_signals.json` 当完整试读结论 | 默认只是 signal-only；定性占位未补完时只能低权重参考 |
