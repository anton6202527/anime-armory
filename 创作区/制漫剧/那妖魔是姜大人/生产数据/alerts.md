# n2d 生产告警

- root: 创作区/制漫剧/那妖魔是姜大人
- generated_at: 2026-07-03T07:51:51+00:00
- 告警数: 3（critical 2 / warn 1）

| 级别 | 类型 | 范围 | 说明 |
|---|---|---|---|
| 🔴 critical | qa_blockers | totals | QA 阻断 34 项（阈值 >0）；先按 recent_blockers 修复再继续付费生成 |
| 🔴 critical | unverified_progress | totals | 1 处未验证强标 ✅（第1集）：受闸列没有「真跑过+指纹新鲜」的闸门凭据，本季视为 provisional；对当前产物重跑对应 dashboard gate 销账。 |
| 🟡 warn | qa_blockers | 第2集 | 第2集 QA 阻断 34 项 |

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
