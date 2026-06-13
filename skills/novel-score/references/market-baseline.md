# 市场基准采集

`novel-score` 和 `novel-review` 流程自审共用同一套市场基准，避免各拉各的、日期不一致。

## 必须产物

每次评分或流程自审前，落在项目的 `评分/` 目录：

```text
评分/题材热榜_<YYYY-MM-DD>.md
评分/market_baseline_<YYYY-MM-DD>.json
```

`score_report.json.market_baseline.baseline_path` 必须指向本次人读基准 `题材热榜_<YYYY-MM-DD>.md`；`baseline_json_path` 指向同日期 `market_baseline_<YYYY-MM-DD>.json`。

## 采集入口

```bash
python3 skills/novel-score/scripts/collect_market_baseline.py "<作品根>/评分" \
  --target-platform "<目标平台>" \
  --allow-fetch-errors
```

默认抓取公开榜单入口：番茄、起点、晋江。红果/抖音短剧·漫剧榜在 App/小程序内、无公开网页，所以脚本会默认追加 **红果/抖音 的 `status=manual_required` 可见占位行**（不计入有效证据），并在 `target_platform` 命中 红果/抖音/漫剧/短剧 却无任何来源/结构化人工证据覆盖时写一条 `coverage_warnings`（同时 stderr 告警）。这逼采集者用 `--manual-evidence "红果短剧|YYYY-MM-DD|第三方榜单|结论|URL"` 或 `--source "红果短剧|<第三方报告URL>"` 显式补齐——避免"基准看起来覆盖了、实则对主投放平台是盲区"。`--note` 只做人读备注，不再计入有效证据；`--no-manual-required` 可关掉占位行。

## 使用规则

- 不凭记忆判断“当下热门题材”。没有来源链接或采集日期的趋势，不进评分证据。
- 有效基准必须有证据承载：至少一个来源 `status=ok` 且 `signals` 非空，或 `manual_evidence[]` 中有结构化人工核验证据（`platform/date/source/summary` 必填，date 必须是 `YYYY-MM-DD`）。全是 `fetch_error`、空 `signals` 或自由文本 `notes` 的 JSON 只能说明“本次采集失败/人工备注”，不能拿来评分。
- 基准建议有效期 14-28 天；超过 `expires_after_days` 重新采集。`score.py` 默认会硬性检查缺失/过期基准，只有离线测试或人工明确豁免才加 `--allow-stale-baseline`。该豁免必须写入 `score_report.waivers[]` 和 `审稿/waiver_log.jsonl`，且 QA gate 会把 `market_baseline.freshness.blocking=true` 作为 `SCORE-BASELINE` 处理；有豁免时只降为 warning。
- score 判单本作品；review/self-audit 判产线升级。两者可共用同一份基准，但不要复用旧报告替代重新核验。
- 抓取失败不是趋势证据，只能作为“该来源本次不可用”的记录。
