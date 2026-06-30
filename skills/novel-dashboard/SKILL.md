---
name: novel-dashboard
description: Read-only production control dashboard for novel projects. Use when the user wants a single operational view of pipeline stage readiness, stale artifacts, open semantic jobs, revision tasks, batch queue state, review/score blockers, market evidence jobs, and release readiness. Writes dashboard artifacts only under 生产数据 and does not change progress or story content. Triggers novel-dashboard, 小说控制台, 小说生产看板, 全线看板, 运营面板, dashboard, control-plane.
---

# novel-dashboard — 小说生产控制台

`novel-dashboard` 是 novel 线的只读运营面板。它不写正文、不改 `_进度.md`、不认领任务，只把当前项目的关键生产信号聚合到一个地方。

产物：

- `生产数据/novel_dashboard.json`
- `生产数据/novel_dashboard.md`
- 可选 `生产数据/novel_dashboard.html`

## 汇总内容

- `pipeline_runner` dry-run：下一阶段、每阶段 done/ready/blocked。
- artifact graph：stale artifacts 与受影响消费者。
- `语义任务/*.json`：未完成语义任务。
- `修订/revision_plan.json`：P0/P1/P2 任务与冲突。
- `生产数据/novel_batch_queue.json`：队列状态、dead-letter 数。
- `生产数据/batch_runs/*.json`：run-one 执行次数、耗时、子进程资源、截断日志数、状态与输出 diff。
- `审稿/review_report.json`：阻断 finding。
- `审稿/review_board.json`：主编/人工仲裁板决策。
- `评分/score_report.json`：生产决策、评分结论、市场证据缺口。
- `生产数据/prompt_cache_metrics.json`：任务包 cache readiness、真实 cached input token 命中率（若有 usage）。
- `生产数据/vector_store_eval.json`：RAG/长篇记忆检索 Recall@K/MRR。
- `生产数据/supervisor_ledger.json`：跨 run rolling circuit breaker。
- `生产数据/novel_dashboard_history.jsonl`：每次 `--write` 追加 ops SLO 历史，用于趋势对比。
- 导出/release 相关产物是否存在。

## 用法

```bash
python3 skills/novel-dashboard/scripts/dashboard.py "<作品根>" --write --html
python3 skills/novel-dashboard/scripts/dashboard.py "<作品根>" --json
```

## 和其它 skill 的边界

- 想知道“下一步具体命令”时，仍可跑 `novel/scripts/flow.py`。
- 想批量执行任务时，交给 `novel-batch`。
- 想自动派发 writer/reviewer 时，交给 `novel-supervisor`。
- 本 skill 只提供事实面板和聚合，不替用户决定是否改稿、重评或导出。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把 dashboard 当 gate | dashboard 汇总 gate 信号；真正阻断由 `novel-gate.py` / export gate 判 |
| dashboard 过期后继续看 | 重要操作前重新 `--write` |
| 用面板结果直接改正文 | 先进入 `revision_planner.py` / `novel-edit` / 对应 stage skill |
