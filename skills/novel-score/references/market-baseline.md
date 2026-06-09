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

默认抓取公开榜单入口：番茄、起点、晋江。红果/抖音短剧很多时候需要 App、浏览器或第三方报告核验；这类结果用 `--note` 补进同一份基准，必须写清来源、日期、用途。

## 使用规则

- 不凭记忆判断“当下热门题材”。没有来源链接或采集日期的趋势，不进评分证据。
- 有效基准必须有证据承载：至少一个来源 `status=ok` 且 `signals` 非空，或 `notes` 中有人工核验补充（写清来源、日期、用途）。全是 `fetch_error` 或空 `signals` 的 JSON 只能说明“本次采集失败”，不能拿来评分。
- 基准建议有效期 14-28 天；超过 `expires_after_days` 重新采集。`score.py` 默认会硬性检查缺失/过期基准，只有离线测试或人工明确豁免才加 `--allow-stale-baseline`。该豁免必须写入 `score_report.waivers[]` 和 `审稿/waiver_log.jsonl`，且 QA gate 会把 `market_baseline.freshness.blocking=true` 作为 `SCORE-BASELINE` 处理；有豁免时只降为 warning。
- score 判单本作品；review/self-audit 判产线升级。两者可共用同一份基准，但不要复用旧报告替代重新核验。
- 抓取失败不是趋势证据，只能作为“该来源本次不可用”的记录。
