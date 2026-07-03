# Novel Dashboard

- 作品：镇魔司：开局收录虎山神
- 生成：2026-07-02T10:22:23
- next_stage：source_import
- stage_counts：{'done': 6, 'ready': 3, 'blocked': 5}

## Blocked Stages

- post_write / 写后账本闭环：missing=['审稿/state_delta_第*.json'] gate=[]
- score / 市场评分：missing=['评分/market_baseline_*.json'] gate=[]
- revision / 统一修订计划：missing=['审稿/review_report.json', '评分/score_report.json', '评分/reader_telemetry_summary.json', '评分/reader_panel_signals.json', '评分/market_evidence_jobs.json'] gate=[]
- export / 导出：missing=['审稿/review_report.json', '评分/score_report.json', '合规/ai_usage.json'] gate=[]
- release_manifest / 发布版本清单：missing=['导出/*.txt', '导出/*.docx', '导出/*outline*.md'] gate=[]

## Signals

- review blockers：0 / findings=0
- score：None verdict= decision=
- revision tasks：0 by_priority={} conflicts=0
- semantic jobs：0
- stale artifacts：0
- batch：{} dead_letter=0
- batch runs：0 by_status={}
- release manifest：no ready=False blockers=0
- review board：no decision= approval_required=False
- prompt cache：no coverage=0.00 readiness=0.00 actual_hit=0.00
- vector eval：no passed=False recall=0.00 mrr=0.00
- supervisor：rolling_entries=0 tripped=0

## Ops SLO

- batch_avg_elapsed_ms=0 failed_runs=0 truncated_logs=0
- cache_readiness=0.00 actual_cache_hit=0.00 retrieval_recall=0.00
