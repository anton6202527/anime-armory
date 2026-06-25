# 市场基准采集

`novel-create` 的商业/平台立项、`novel-score` 评分和 `novel-review` 流程自审共用同一套市场基准，避免各拉各的、日期不一致。

## 必须产物

每次商业/平台立项、评分或流程自审前，落在项目的 `评分/` 目录：

```text
评分/题材热榜_<YYYY-MM-DD>.md
评分/market_baseline_<YYYY-MM-DD>.json
```

`score_report.json.market_baseline.baseline_path` 必须指向本次人读基准 `题材热榜_<YYYY-MM-DD>.md`；`baseline_json_path` 指向同日期 `market_baseline_<YYYY-MM-DD>.json`。

若目标平台命中红果/抖音/漫剧/短剧但缺有效覆盖，采集器还会写：

```text
评分/market_evidence_tasks.json
评分/市场证据待补.md
```

这些文件是给 `novel-research` 的待办，不是可评分证据；补完结构化且未过期的证据后必须回跑采集器，让 `market_baseline_<YYYY-MM-DD>.json.manual_evidence[]` 成为 score 可读取的来源。

## 采集入口

```bash
python3 skills/novel-score/scripts/collect_market_baseline.py "<作品根>/评分" \
  --target-platform "<目标平台>" \
  --allow-fetch-errors
```

默认抓取公开榜单入口：番茄、起点、晋江。红果/抖音短剧·漫剧榜在 App/小程序内、无公开网页，所以脚本会默认追加 **红果/抖音 的 `status=manual_required` 可见占位行**（不计入有效证据），并在 `target_platform` 命中 红果/抖音/漫剧/短剧 却无任何未过期来源/结构化人工证据覆盖时写 `coverage_warnings`，同时生成 `evidence_tasks` 和待补文件。这逼采集者用 `--manual-evidence "红果短剧|YYYY-MM-DD|第三方榜单|结论|URL"` 或 `--source "红果短剧|<第三方报告URL>"` 显式补齐——避免"基准看起来覆盖了、实则对主投放平台是盲区"。`--note` 只做人读备注，不再计入有效证据；`--no-manual-required` 可关掉占位行。

采集器会同步写证据质量：

- `sources[].source_quality`：`score/confidence/reasons`，综合 `status=ok`、signals 数量、页面标题、https、rank 用途等。
- `manual_evidence[].evidence_quality`：结构化人工证据的质量提示，综合 URL、来源类型、摘要信息量、核验日期。
- `evidence_quality`：整份 baseline 的平均置信度与有效证据数。

证据质量不是“事实真伪判定器”，只是给 `novel-score` prompt 的可信度提示：high/medium/low 来源不能等权；fetch_error/manual_required 仍保留在报告里暴露缺口，但不当趋势证据。

## 使用规则

- 不凭记忆判断“当下热门题材”。没有来源链接或采集日期的趋势，不进评分证据。
- 有效基准必须有证据承载：至少一个来源 `status=ok` 且 `signals` 非空，或 `manual_evidence[]` 中有结构化人工核验证据（`platform/date/source/summary` 必填，date 必须是 `YYYY-MM-DD`）。来源日期或人工证据日期必须落在 `expires_after_days` 内；过期证据会触发 `evidence_stale`，红果/抖音/漫剧/短剧目标还会继续触发覆盖缺口。全是 `fetch_error`、空 `signals`、过期人工证据或自由文本 `notes` 的 JSON 只能说明“本次采集失败/人工备注”，不能拿来评分。
- 评分时必须看 `evidence_quality`：低质量证据只做弱先验；高质量但覆盖平台错位的证据仍要被 `coverage_warnings` 降权。
- 基准建议有效期 14-28 天；超过 `expires_after_days` 重新采集。`score.py` 默认会硬性检查缺失/过期基准，只有离线测试或人工明确豁免才加 `--allow-stale-baseline`。该豁免必须写入 `score_report.waivers[]` 和 `审稿/waiver_log.jsonl`，且 QA gate 会把 `market_baseline.freshness.blocking=true` 作为 `SCORE-BASELINE` 处理；有豁免时只降为 warning。
- score 判单本作品；review/self-audit 判产线升级。两者可共用同一份基准，但不要复用旧报告替代重新核验。
- 抓取失败不是趋势证据，只能作为“该来源本次不可用”的记录。
- **拥挤度/同质化要单独留痕**（不只记"热不热"，还要记"挤不挤"）：采集时顺手记同题材占榜比例、雷同套路扎堆程度，写进 baseline 的 `signals`（或 `manual_evidence` 的 `summary`）。`rubric.md` 的「题材红海/同质化饱和」扣分项据此判——2025 下半年热门 IP 改编均 ROI 已跌破 1:1.5 盈亏线，正是同质化所致；只看热度不看拥挤会把红海题材当成机会。
