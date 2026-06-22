---
name: novel-feedback
description: Ingest real reader telemetry and comments for an in-progress novel project, normalize chapter-level reads/completions/drops/comments from CSV or JSONL, and feed scored reader evidence back into novel-score/novel-balance/novel-simulate. Use when the user has platform backend data, test-reader forms, comments, drop-off points, read-completion metrics, or wants to turn real reader feedback into next rewrite priorities. Triggers 真实读者反馈, 读者数据, 留存数据, 完读率, 掉点, 评论分析, 平台后台, reader telemetry, reader feedback ingestion.
---

# novel-feedback — 真实读者反馈回灌

把平台后台、测试读者表单、评论导出里的真实读者信号整理成章节级证据，供 `novel-score`、`novel-balance`、`novel-simulate` 使用。它不模拟读者，也不替代审稿；它只把真实读端数据结构化。

## 适用场景

- 有 CSV/JSONL：章节阅读、开始阅读、完读、弃读、平均阅读时长、点赞、追更、评论。
- 有测试读者表单：每章是否读完、哪里弃书、评论文本。
- 想让 `novel-score` 在留存维度优先参考真实反馈，而不是只看公榜或虚拟试读。

## 工作流

```bash
python3 skills/novel-feedback/scripts/ingest_reader_events.py "<作品根>" \
  --input "<反馈导出.csv或.jsonl>" \
  --platform "红果测试投放" \
  --source-name "2026-06-22 小流量测试"
```

产物：

- `评分/reader_telemetry.jsonl`：规范化后的逐条事件。
- `评分/reader_telemetry_summary.json`：章节级聚合，含完读率、弃读率、评论情绪线索、风险旗标。
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

## 判读铁律

- 权重序：真实读者反馈 > 自有投放战绩 > `novel-simulate` 虚拟试读 > 外部公榜泛化。
- 单章低完读、弃读高、负面评论集中，只说明“这一章读端有伤口”，不自动证明设定或文学性错误；需要回 `novel-review` / `novel-balance` 定因。
- 样本量低时报告会标 `low_sample`，不得把小样本波动当硬结论。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把评论情绪当最终审稿结论 | 评论只定位痛点，定因还要 review/balance |
| 只看均值不看章节掉点 | 重点看 weakest_chapters 和 flags |
| 真实反馈与模拟反馈冲突时平均处理 | 真实反馈优先；模拟只解释可能原因 |
