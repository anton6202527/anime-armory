# n2d-dashboard schema

## Event: `production_events.jsonl`

Each line is one JSON object.

```json
{
  "kind": "n2d_production_event",
  "version": 1,
  "ts": "2026-06-08T12:00:00+00:00",
  "episode": "第1集",
  "stage": "image",
  "event": "generation",
  "source": "manual",
  "cost": {
    "amount": 0.06,
    "currency": "USD",
    "unit": "USD",
    "provider": "codex"
  },
  "duration_sec": 38,
  "generation": {
    "asset": "Clip_01.png",
    "attempt": 1,
    "status": "pass",
    "redraw_reason": ""
  },
  "qa": {
    "severity": "block",
    "dim": "角色一致性",
    "loc": "Clip_02",
    "msg": "脸漂移"
  },
  "meta": {
    "native_audio": "no"
  },
  "release": {
    "plays": 12000,
    "revenue": 86.5,
    "spend": 30,
    "currency": "CNY",
    "runtime_sec": 92
  }
}
```

## Required fields

| Field | Meaning |
|---|---|
| `kind` | Must be `n2d_production_event` |
| `version` | Schema version, currently `1` |
| `ts` | ISO timestamp |
| `episode` | `第N集` |
| `stage` | `script` / `voice` / `image` / `video` / `compose` / `review` / custom |
| `event` | `generation` / `redraw` / `qa_gate` / `qa_gate_run` / `cost` / `duration` / `manual` / `release` / `revenue` |
| `source` | `manual`, script path, or backend |

## Metric rules

| Metric | Source |
|---|---|
| Cost | Sum `cost.amount` grouped by `cost.unit` and provider |
| Elapsed time | Sum positive `duration_sec` |
| Generation attempts | Count generation/redraw events, or `generation.attempts` when supplied |
| Redraw count | `event=redraw` or any event with `generation.redraw_reason` |
| Redraw reasons | Counter of `generation.redraw_reason` |
| QA blockers | Count `qa.severity=block` |
| QA warnings | Count `qa.severity=warn` |
| Final pass rate | `generation_passes / (generation_passes + generation_fails)` |
| Finished runtime | `release.runtime_sec` / `platform_metrics.duration_sec` / `storyboard.json.total_duration` |
| Cost per finished minute | `cost_totals[unit] / (runtime_sec / 60)` |
| One-pass rate | Pass events with `event=generation` and `generation.attempt<=1`, divided by generation attempts |
| Redraw rate | `redraw_count / generation_attempts` |
| Release revenue | Sum `release.revenue` or `platform_metrics.revenue/gross_revenue/ad_revenue/...` by currency |
| Release spend | Sum `release.spend` or `platform_metrics.distribution_spend/ad_spend/promotion_spend/...` by currency |
| Net recoup | `release_revenue_totals - release_spend_totals` |
| Recoup ratio | `release_net_totals[unit] / cost_totals[unit]`; no cross-currency conversion |

## Platform ROI ingestion

`dashboard.py build` automatically reads:

```text
生产数据/platform_metrics.csv
生产数据/platform_metrics.jsonl
生产数据/platform_metrics.json
```

Accepted ROI fields:

| Meaning | Field aliases |
|---|---|
| Plays | `plays`, `views`, `播放量` |
| Revenue | `revenue`, `gross_revenue`, `total_revenue`, `income`, `回收`, `收入`; if absent, sums `ad_revenue`, `paid_revenue`, `platform_revenue`, `creator_revenue`, `iap_revenue` |
| Distribution spend | `distribution_spend`, `promotion_spend`, `ad_spend`, `traffic_cost`, `platform_spend`, `投放成本` |
| Currency/unit | `revenue_currency`, `currency`, `unit`; default `CNY` |
| Runtime | `final_duration_sec`, `runtime_sec`, `video_duration_sec`, `total_duration_sec`, `duration_sec` |

Keep `n2d-feedback` for retention/A-B analysis; dashboard consumes the same platform metrics to calculate ROI.

## Gate ingestion

`dashboard.py gate <作品根> 第N集 --stage image_preflight|video_preflight|image|video|compose|review` converts every `n2d-review/scripts/gate.py --json` finding into a `qa_gate` event and adds one `qa_gate_run` summary event. Use preflight stages before paid backend calls; use `image` / `video` after assets are landed:

```json
{
  "event": "qa_gate_run",
  "qa_gate": {
    "blocks": 2,
    "warns": 1,
    "infos": 0
  }
}
```

By default, a new gate run replaces previous gate events for the same episode and stage. Use `--append` only when comparing historical gate runs.

## 阈值配置 alert_thresholds.json（实时监控 + 告警）

放在 `生产数据/alert_thresholds.json`（也可在 `<作品根>/_设置.md` 写 `告警*` 键；JSON 优先）。`None`/缺省=关闭该项。默认只对 QA 阻断开箱即告。

| 键 | 含义 | 默认 |
|---|---|---|
| `budget_cap` | 单币种累计成本上限，超→critical | None |
| `budget_warn_ratio` | 达上限该比例先 warn | 0.8 |
| `final_pass_rate_floor` | 总通过率低于→critical（逐集低于→warn 定位） | None |
| `redraw_rate_ceiling` | 重抽率高于→warn | None |
| `qa_blockers_ceiling` | QA 阻断数 > 此→critical | 0 |
| `cost_per_min_ceiling` | 每分钟成本上限（单币种）→warn | None |
| `recoup_floor` | 回收比低于→warn（仅有投放数据时） | None |

环境变量 `N2D_ALERT_BUDGET_CAP` 可覆盖 `budget_cap`；`N2D_ALERT_WEBHOOK` 设外发告警 URL。

## alerts.json / alerts.md（告警快照·幂等覆盖非追加）

`build`/`record`/`gate`/`watch` 每次评估后写 `生产数据/alerts.{json,md}`，反映**当前状态**（不是日志）。`alerts.json`：

```json
{
  "kind": "n2d_production_alerts", "version": 1, "root": "制漫剧/剧名",
  "generated_at": "...", "thresholds": { ... },
  "counts": {"critical": 1, "warn": 2},
  "alerts": [
    {"level": "critical", "kind": "qa_blockers", "scope": "totals", "message": "QA 阻断 1 项…", "value": 1, "threshold": 0}
  ]
}
```

`kind` ∈ `qa_blockers / final_pass_rate / redraw_rate / budget / cost_per_min / recoup`；`level` ∈ `critical / warn`；`scope` = `totals` 或具体 `第N集`。`dashboard.json` 也内嵌 `alerts` + `alert_counts`。`dashboard.html` = 自动刷新看板（`watch --serve`，本机 http.server）。
