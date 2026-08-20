---
name: novel-simulate
description: 合成叙事探针（兼容“模拟读者”叫法）— 用不同阅读偏好视角和可复核的表面信号提出阅读中断点、理解障碍、预测重合等正文复核问题。输出不是抽样读者、真实留存预测或统计证据，不参与自动评分或自动约束创作；真实平台/内测数据走 novel-feedback。Use when asked to 模拟读者, 合成读者探针, 读者视角复核, 弃书点假设, 读者怎么看, 虚拟试读, simulate readers, narrative probes, mock audience. Triggers 模拟读者, 合成探针, 虚拟试读, 读者反馈, 弃书点, 可预测性, novel simulate, reader panel.
---

# novel-simulate — 多视角合成叙事探针

这是一个**合成、定性、待验证**的编辑工具：用多种阅读偏好提出“值得去正文里复核什么”的问题。它不模拟出具有统计代表性的真实读者，也不输出真实留存概率。

## 内置阅读视角预设

| 人格 ID | 名称 | 关注点 | 预设复核问题示例 |
|---|---|---|---|
| `rookie` | 小白爽文党 | 节奏、升级感、反杀、不憋屈 | 目标与阻碍是否足够快地建立？ |
| `logic` | 逻辑考据党 | 设定自洽、力量体系、智斗逻辑、无降智 | 人物选择是否有可见动机与代价？ |
| `emote` | 情感/互动党 | 人物弧光、CP感、情感张力、金句 | 关系变化是否落实为动作或选择？ |
| `critic` | 毒舌老书虫 | 同质化套路、文笔质感、新意 | 熟悉母题是否产生了作品自己的转折？ |

这些是方便复用的**编辑视角标签**，不是四类真实人群。探针只能据此提出问题、引用正文证据并保留分歧，不能代替某类读者发言。

## 工作流

### 1. 发起模拟试读
```bash
python3 skills/novel/novel-simulate/scripts/simulate_panel.py "<作品根>" \
  [--scope opening|chapter] [--personas rookie,logic,emote] \
  [--cohort "<cohort.json>"] \
  [--viewpoint '{"id":"slow_burn","name":"慢热关系视角","focus":"关系细微移动","probe_questions":["关系变化是否落实为选择？"]}']
```
- **opening**：读前 3 章，提出入口理解、期待建立和阅读中断点的候选问题。
- **chapter**：读指定章节，提出追读过程中的具体复核问题。
- **默认视角**：未提供任何自定义输入时，脚本只用 `目标平台` 归一档选择内置视角组合；平台不再改变任何聚合公式，因为 schema v3 不生成聚合留存分。
- **项目级自定义**：若存在 `<作品根>/设定/reader_probe_cohort.json`，且 CLI 未显式指定视角，自动读取该文件。`--cohort` 可指定另一份 JSON；`--viewpoint` 可重复追加单个 JSON 视角；`--personas` 保留内置预设兼容。
- **安全边界**：自定义视角只接受阅读史、题材熟悉度、容忍项、期待机制、关注词和复核问题。未知字段（包括人口统计画像字段）会拒绝；输出固定写 `population_representativeness=none`，不能声称代表年龄、性别、族裔或任何真实群体。
- 关键词词表来自单一定义源 `skills/novel/_lib/keyword_banks.py`（与 novel-balance/novel-promote 共用）。

### 2. 产出报告（确定性信号 + LLM 定性骨架）
脚本产两份：
- `评分/读者试读反馈_<日期>.md`（人读）：逐视角列**关注词字面命中**、预设复核问题和「【AI 代理填写】」证据槽；AI 代理必须引用支持/反驳问题的具体句段，不能替虚构人群宣告偏好。
- `评分/reader_panel_signals.json`（机读，schema v3）：保留三类未校准分量——章尾钩子标记的原始命中/覆盖、CJK 4-gram 表面去重计数与比率、套路词/各视角关注词字面命中和千字密度。**不计算、不落盘、不展示任何聚合留存数**；`aggregate_score=null` 且策略声明未经真实结果校准不得建立聚合分。
- v3 必带 `source_snapshot`，只绑定本次实际 scope：`opening` 是当时存在的前 3 个编号章节，`chapter` 只绑定精确请求章。请求章不存在会报错，**绝不回退第一章**；路径为作品根相对路径并带 SHA-256。
- `novel-score` / `novel-edit` / 修订计划消费前重算实际 scope：正文改动、scope 文件新增/删除或 hash 不符时只提示重跑，旧信号值不再展示为当前事实。v1/v2 因没有 scope 快照，明确标为“新鲜度未知”并隐藏旧值；重跑即可迁移 v3。
- 文件明确 `evidence_type=synthetic_probe`、`validation_status=unvalidated`、`decision_authority=context_only`、`numeric_score_eligible=false`。`novel-score` 只展示分量上下文、不自动调分；QA gate 会写 `SIMULATE-SIGNAL-ONLY` warning。

报告含：可复算的表面分量 / 各视角证据问题 / 视角分歧 / 待真人或平台数据验证的假设。没有“受众兼容度总分”或“留存概率”。

### 3. 合成预测的表面比较（context-only）

合成视角可以在章末先写“下一章会发生什么”，但同一模型换视角不等于独立读者，字面相似也不等于剧情相同。该协议只保存可复核的预测文本，并在下一章存在时比较 2-gram 表面差异/重合：

1. **面板预测**（AI 代理执行）：读到第 NN 章末，每个视角写 2-5 条"下一章会发生什么"的
   一句话短预测，落盘
   `评分/reader_predictions_第NN章.json`（`{chapter, predictions:[{persona,text}…]}`）。
   若要比较“预测时点 vs 后来正文”，预测时禁止先看下一章；否则只把它当普通问题清单。
2. **中性表面比较**：`python3 skills/novel/novel-simulate/scripts/behavioral_signals.py "<作品根>"`
   - `pairwise_surface_difference`：预测两两 2-gram 字面差异；不命名为悬念，也没有优劣阈值。
   - `next_chapter_max_surface_overlap`：任一预测与下一章开头的最大字面重合；重合可能是有效伏笔兑现、类型承诺、偶然同词或过度明示，**重合本身不等于陈词滥调，也不要求反转**。
   输出 `评分/behavioral_signals.json` schema v2，固定 `decision_authority=context_only`、`automatic_constraint_eligible=false`、`alerts=[]`；只生成正文复核问题，不自动改稿、不进评分、不成为写章负约束。

### 4. 标准问卷协议（beta reader 六问·2026-07）

传统 beta reader 实务有一组固定问题（Jane Friedman/FoxPrint 等业界口径），比"自由发感想"
更能定位问题。合成执行时每个视角读完第 NN 章后**逐视角**作答六问，落盘
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
- 若要观察 staged recall 文本，先作答再看上一章；脚本只报告 recall 与上一章的字面重合，**不能据此推断记忆、信息留存或真实读者行为**。
- AI 代理填写的问卷仍是合成探针，只能提出问题；真人 beta reader 的同类问卷与平台数据应走 `novel-feedback`，不得混在同一证据层。
- 脚本保留 bored/confused/disbelief 的视角 ID 与 span，转成“此句段是否存在目标停滞/指代缺口/人物因果矛盾？”等问题；不做多数投票，不生成弃书风险、信息事故、OOC 或 recall failure 结论。

## 何时使用

- **Demo Gate 之后**：在投入大量精力写全本前，用不同阅读视角补一轮正文证据问题。
- **重大转折章之后**：复核作品意图、人物因果和文本明示程度是否一致，不替真实读者发言。
- **尚无真实数据时**：已有完读率、弃读、评论导出时先走 `novel-feedback`；真实反馈权重高于模拟试读。

## 详细参考
- 内置视角、项目 cohort schema、信号 schema v3、旧版兼容和判读铁律：`references/reader-personas.md`

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把模拟角色当成真实读者样本 | 它只代表模型按提示生成的假设；用正文证据和真人反馈验证 |
| 人格选择单一 | 至少选择 3 个差异化的人格，以获得全面的视角 |
| 把 `reader_panel_signals.json` 当留存预测或调分依据 | 它始终是 synthetic/context-only；只生成复核问题，不自动改分 |
| 用年龄/性别/族裔等拼一个“典型读者” | 改写为阅读史、题材熟悉度、容忍项、期待机制和可验证问题；合成视角没有人口代表性 |
| 预测与正文重合就强制反转 | 重合可能是有效兑现；只问“合理兑现还是过度明示”，作者意图、人物因果和已批准章纲优先 |
| 把合成问卷多数当弃读/OOC/留存证据 | 保留 span 和字面重合供复核；真实人群结论走 novel-feedback |
