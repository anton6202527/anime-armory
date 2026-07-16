# n2d 生产告警

- root: /Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手
- generated_at: 2026-07-15T17:53:20+00:00
- 告警数: 2（critical 1 / warn 1）

| 级别 | 类型 | 范围 | 说明 |
|---|---|---|---|
| 🔴 critical | qa_blockers | totals | QA 阻断 7 项（阈值 >0）；先按 recent_blockers 修复再继续付费生成 |
| 🟡 warn | qa_blockers | 第1集 | 第1集 QA 阻断 7 项 |

## 当前阈值
```json
{
  "budget_cap": null,
  "budget_warn_ratio": 0.8,
  "final_pass_rate_floor": null,
  "redraw_rate_ceiling": null,
  "qa_blockers_ceiling": 0,
  "cost_per_min_ceiling": null,
  "recoup_floor": null,
  "retention_3s_floor": null,
  "bounce_3s_ceiling": null,
  "follow_next_rate_floor": null,
  "beat_density_variance_ceiling": null
}
```
