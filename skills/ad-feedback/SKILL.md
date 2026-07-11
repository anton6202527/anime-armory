---
name: ad-feedback
description: 拍广告投放后的 Test→Learn→Refresh 闭环。导入平台 CSV/JSONL，按 hook/key-message/CTA 变体聚合曝光、3秒观看、完播、CTR、CVR、CPA、ROAS、frequency，使用最小样本与 Wilson 区间避免小样本武断胜出，识别疲劳并产下一轮 ad-concept/ad-script 刷新建议。Use when asked 广告投放复盘, A/B测试, CTR/CPA/ROAS, 创意疲劳, 投放数据回灌, ad-feedback.
---

# ad-feedback — 投放反馈与创意学习

输入行至少含 `variant_id`、`impressions`；建议同时带 `hook_id`、`message_id`、`cta_id`、`clicks`、`conversions`、`spend`、`revenue`、`video_3s`、`completed_views`、`frequency`、`date`。

```bash
python3 skills/ad-feedback/scripts/feedback_ingest.py "<作品根>" --input 投放.csv --mark-progress
```

输出 `投放反馈/feedback_report.json` 与 `.md`。只有达到最小曝光且置信区间形成可解释优势时才标 `qualified_winner`；否则只给方向性信号。结果回流 `ad-concept`/`ad-script`，不自动覆盖原片或客户 brief。

## 原则

- 创意假设必须可分解为 hook / key message / CTA，避免把多个变量同时改变后误判因果。
- 归因窗口、conversion event、平台、受众和预算须与 brief.measurement 对齐。
- frequency 上升且 CTR/ROAS 下滑时标疲劳，优先刷新 hook/caption/开场，不把疲劳误判为产品失败。
- 不用投放前启发式代替真实数据，也不凭小样本宣布胜者。
