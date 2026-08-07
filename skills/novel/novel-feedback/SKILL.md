---
name: novel-feedback
description: Ingest real reader telemetry and comments for an in-progress novel project, normalize chapter-level reads/completions/drops/comments from CSV or JSONL, and feed scored reader evidence back into novel-score/novel-balance/novel-simulate. Use when the user has platform backend data, test-reader forms, comments, drop-off points, read-completion metrics, or wants to turn real reader feedback into next rewrite priorities. Triggers 真实读者反馈, 读者数据, 留存数据, 完读率, 掉点, 评论分析, 平台后台, reader telemetry, reader feedback ingestion.
---

# novel-feedback — 真实读者反馈回灌

把平台后台、测试读者表单、评论导出里的真实读者信号整理成章节级证据，供 `novel-score`、`novel-balance`、`novel-simulate` 使用。它不模拟读者，也不替代审稿；它只把真实读端数据结构化。

## 适用场景

- 有 CSV/JSONL：章节阅读、开始阅读、完读、弃读、平均阅读时长、点赞、追更、评论。
- 有测试读者表单：每章是否读完、哪里弃书、评论文本。
- 想让 `novel-score` 在留存维度接入真实经验数据，而不是只看市场语境或合成叙事探针。

## 工作流

### 0. 先做读者测试计划（推荐）

在拿真实反馈前，先明确测试目标、版本、样本量和决策阈值：

```bash
python3 skills/novel/novel-feedback/scripts/reader_test_plan.py "<作品根>" \
  --platform "红果测试投放" \
  --source-name "开篇A/B小样本" \
  --scope "opening:1-3" \
  --target-reader "红果爽文读者" \
  --cohort "核心读者|来自同题材书单/社群|近30天读过同题材" \
  --ab-test-id "opening-ab-001" \
  --assignment "randomized" \
  --privacy-note "只保存匿名读端指标和必要评论，不收集真实姓名/联系方式" \
  --take "opening-v1" --hypothesis "第1章前300字提前抛羞辱冲突，预期提升完读" \
  --take "opening-v2" --hypothesis "保留原开头但加强章末钩子，检验追读欲"
```

产物：

- `评分/reader_test_plan.json`
- `评分/读者测试计划.md`

计划只规定怎么测，不替代真实数据。每个版本必须写清假设、最小样本量和最小效果差；正式计划还应写 `cohorts`、`experiment_design`、`data_collection_fields`、`privacy_note`，后续 CSV/JSONL 导入必须尽量带 `ab_test_id`、`variant_id`、`take_id`，才能把结果归因到具体稿件版本。改稿后必须同范围复测或说明不可比，否则只做方向性解释。真实读者 telemetry 属于**市场验证**，不是 KDP/普通平台发布合规前置条件：`platform_publish` / `kdp_publish` 缺数据只 warning；只有用户显式选择 `--release-profile data_validated_launch` 时才要求 `reader_test_plan.json` + 真实 telemetry（或作用域匹配的显式 waiver）。

### 1. 导入真实反馈

```bash
python3 skills/novel/novel-feedback/scripts/ingest_reader_events.py "<作品根>" \
  --input "<反馈导出.csv或.jsonl>" \
  --platform "红果测试投放" \
  --source-name "2026-06-22 小流量测试"
```

产物：

- `评分/reader_telemetry.jsonl`：规范化后的逐条事件。
- `评分/reader_telemetry_summary.json`：章节级聚合，含完读率、弃读率、评论情绪线索、风险旗标；若输入含 `ab_test_id` / `variant_id` / `take_id`，会生成 `experiments.groups` 与 `leaders_by_ab_test`。兼容字段 `best_by_ab_test` 仍保留，但条目明确是描述性 leader，不是 winner。当前流程未完整实现随机分配、cohort/窗口可比性、置信区间与停止规则协议，因此恒为 `decision=inconclusive` / `context_only`，不得据裸 uplift 宣布胜负。
- `评分/真实读者反馈_<YYYY-MM-DD>.md`：给人读的掉点/优先修订清单。

## 字段兼容

输入字段可用中文或英文，脚本会归一：

| 含义 | 可识别字段 |
|---|---|
| 章节 | `chapter` / `章节` / `chapter_no` |
| 事件 | `event` / `事件`，如 `start`、`complete`、`drop`、`comment`、`like`、`follow` |
| 数量 | `count` / `数量` |
| 直接指标 | `starts` / `completes` / `drops` / `views` / `completion_rate` / `drop_rate` / `avg_read_seconds` |
| 评论 | `comment` / `评论` / `text` |
| 情绪 | `sentiment` / `情绪`，可填 `positive` / `negative` / `neutral` |
| A/B 实验 | `ab_test_id` / `experiment_id` / `AB测试` |
| 实验版本 | `variant_id` / `variant` / `版本` / `组别` |
| 稿件/素材版本 | `take_id` / `take` / `稿件版本` / `素材版本` |

## 判读铁律

- 先有测试计划，再导入反馈；没有计划时也能导入，但报告只能做事后解释，A/B 归因可信度更低。
- 测试计划要写清 cohort 来源/纳入标准、A/B 分配方式和隐私说明；不要把混合人群的小样本当作全平台结论。
- 证据分层：真实读者反馈与经审计的自有投放数据是经验数据；`novel-simulate` 是 synthetic/context-only 假设生成器；外部公榜只作市场语境。
- 单章低完读、弃读高、负面评论集中，只说明“这一章读端有伤口”，不自动证明设定或文学性错误；需要回 `novel-review` / `novel-balance` 定因。
- 样本量低时报告会标 `low_sample`，不得把小样本波动当硬结论。
- A/B 只在同一 `ab_test_id` 内比较；`take_id` 用来把结果归因到具体章节稿/开头版本/投放素材，不要混到全书评价里。
- A/B 完读率差异低于测试计划里的 `completion_rate_delta` 时，不判胜负，记为 `inconclusive`。
- 改稿后要复测；未复测的“修好了”只能当编辑假设，不能当读者事实。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把评论情绪当最终审稿结论 | 评论只定位痛点，定因还要 review/balance |
| 只看均值不看章节掉点 | 重点看 weakest_chapters 和 flags |
| 真实反馈与模拟反馈冲突时平均处理 | 真实反馈优先；模拟只解释可能原因 |
| A/B 版本没有 take_id | 补 `take_id`，否则无法追溯是哪次修订或素材导致数据变化 |
