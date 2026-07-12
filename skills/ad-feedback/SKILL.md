---
name: ad-feedback
description: 拍广告投放实验与 Test→Learn→Refresh 闭环。花钱前预注册单变量实验（假设/KPI/归因窗/随机化/决策规则/样本线/不变量），投放后导入并哈希绑定平台 CSV/JSONL，按 hook/key-message/CTA 聚合 CTR/CVR/CPA/ROAS/frequency；Wilson 区间只作聚合二项快筛，平台原生实验结论优先，避免小样本或不可比层武断胜出。Use when asked 广告投放复盘, A/B测试, CTR/CPA/ROAS, 创意疲劳, 投放数据回灌, ad-feedback.
---

# ad-feedback — 投放反馈与创意学习

花预算前先把实验假设、KPI、归因窗口、随机化单元、决策规则、平台/**具体 placement**/受众、日期、样本快筛线与不变量写进 JSON。每个变体还要以 `asset_path + asset_sha256` 绑定实际媒体；每个实验只改 hook / key message / CTA 其中一个维度，预算、竞价、落地页、版位保持一致。

```bash
# 先预注册；验证通过后固化为 投放反馈/experiment_plan.json + validation.json
python3 skills/ad-feedback/scripts/experiment_plan.py "<作品根>" --input experiment_plan.json

# 投放后导入原始导出；输入会复制到 投放反馈/raw/ 并以 SHA-256 绑定报告
python3 skills/ad-feedback/scripts/feedback_ingest.py "<作品根>" --input 投放.csv --mark-progress
```

输入行至少含 `variant_id`、`impressions`；建议同时带 `hook_id`、`message_id`、`cta_id`、`clicks`、`conversions`、`spend`、`revenue`、`video_3s`、`completed_views`、`frequency`、`date`。

输出 `投放反馈/feedback_report.json` 与 `.md`。没有当前、已批准的预注册计划时，仍可生成诊断报告，但会 block 且绝不宣布胜者。只有同层可比、达到最小曝光且 CTR/CVR 的 Wilson 区间形成可解释优势时，才给本地 `qualified_winner`；它不是平台原生随机实验推断的替代品。CPA/ROAS 只有聚合值而没有方差/事件级数据时一律只作方向性读取。结果回流 `ad-concept`/`ad-script`，不自动覆盖原片或客户 brief。

## 原则

- 创意假设必须可分解为 hook / key message / CTA，避免把多个变量同时改变后误判因果。
- 归因窗口、conversion event、平台、placement、受众和预算须与 brief.measurement/platform_pack 对齐；跨版位数据不是同一可比层。
- 平台原生的随机分桶、显著性与实验报告优先；本地 Wilson 95% 区间只适用于聚合二项 CTR/CVR 快筛，不冒充 Google 等平台的 bucket/Jackknife 方法。
- frequency 上升且 CTR/ROAS 下滑时标疲劳，优先刷新 hook/caption/开场，不把疲劳误判为产品失败。
- 不用投放前启发式代替真实数据，也不凭小样本宣布胜者。

最小计划字段：`hypothesis/primary_kpi/conversion_event/attribution_window/platform/placement/audience/randomization_unit/decision_rule/start_date/end_date/min_impressions/held_constant/variants[]`；每个 variant 必填 `asset_path/asset_sha256`。导入时 KPI、变体、平台、placement、受众和样本线均从已批准计划读取，不能投放后换素材或调低门槛。
