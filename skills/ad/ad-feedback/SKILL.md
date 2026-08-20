---
name: ad-feedback
description: 拍广告投放实验与 Test→Learn→Refresh 闭环。花钱前预注册本地二项实验的 baseline/MDE/alpha/power、独立分析单元、停止规则与 Bonferroni，或绑定平台原生实验配置 receipt；投放后严格校验计数并重核当前素材/证据 SHA。只有功效样本量与停止条件均满足才允许本地两比例 score-test 结论；Wilson 仅展示，平台原生结果 receipt 绑定实验 ID 与当前素材 SHA 后优先。Use when asked 广告投放复盘, A/B测试, CTR/CPA/ROAS, 创意疲劳, 投放数据回灌, ad-feedback.
---

# ad-feedback — 投放反馈与创意学习

花预算前先选 `design_mode`：

- `local_binomial`：除实验假设、KPI、归因窗口、决策规则、平台/**具体 placement**/受众、日期与不变量外，必须预注册 `metric_definition.numerator/denominator`、`baseline_rate`、绝对百分点 `minimum_detectable_effect`、`alpha`、`power`、`multiple_comparison_method` 与 `stopping_rule`。`randomization_unit` 和 `analysis_unit` 都必须等于 denominator 的独立事件单元（CTR=`impression`，CVR=`click`），并显式 `independent_bernoulli=true`；用户/桶随机化、重复曝光或聚类数据走 `platform_native`。脚本用两比例正态近似计算每臂目标，最终用同口径 pooled two-proportion score test；两臂可用 `none`，多臂仅支持 `bonferroni`，未实现的 Holm 不得声明。`min_impressions` 仅是运营诊断快筛线，绝不代替功效。
- `platform_native`：在 `platform_experiment` 中写实验 ID；`config_receipt` 自身也必须显式写同一 ID，并用作品内相对证据路径、证据 SHA 与 `asset_bindings` 逐变体绑定当前媒体。投放结束把平台导出的结论 receipt 放到 `投放反馈/platform_experiment_result.json`；它同样须绑定 experiment ID、KPI、作品内证据 SHA 和全部当前素材 SHA。反馈导入会重新哈希实际媒体、配置证据、结果证据及 receipt 文件，不能拿预注册时的旧 SHA 冒充当前状态。

两种模式的每个变体都要以 `asset_path + asset_sha256` 绑定实际媒体；实验仍只改 hook / key message / CTA 其中一个维度，预算、竞价、落地页、版位保持一致。

正式花预算前必须先有当前 `生产数据/campaign_readiness.json`：只接受 `mode=formal`、`summary.release_ready=true`、`summary.block=0`，且 `brief_sha256` 必须匹配当前 `需求/brief.json`。预注册会从当前 brief 与项目内证据完整重跑 landing/准入/埋点/归因/路由/privacy readiness，并比较确定性语义；手写一个自报 ready 的最小 JSON、sample、缺失或证据变化后的旧 readiness 都不能批准实验。

```bash
# 先闭合正式投放就绪；sample readiness 永远不能进入付费实验
python3 skills/ad/ad-craft/scripts/campaign_readiness.py "<作品根>" --mode formal

# 先预注册；验证通过后固化为 投放反馈/experiment_plan.json + validation.json
python3 skills/ad/ad-feedback/scripts/experiment_plan.py "<作品根>" --input experiment_plan.json

# 投放后导入原始导出；先复制到 投放反馈/raw/，再解析这份 canonical bytes 并以 SHA-256 绑定报告
python3 skills/ad/ad-feedback/scripts/feedback_ingest.py "<作品根>" --input 投放.csv --mark-progress
```

输入行至少含 `variant_id/platform/placement/audience` 和预注册 KPI 的逐行计数：CTR=`clicks/impressions`，CVR=`conversions/clicks`。二项计数必须是有限非负整数，并逐行满足 `conversions <= clicks <= impressions`（字段适用时）；非法字符串、NaN/Inf、负数和小数计数均 block。建议同时带 `conversion_event/attribution_window/landing_page/bidding/budget` 复核不变量，以及 `hook_id/message_id/cta_id/spend/revenue/video_3s/completed_views/frequency/date`。同一变体内 platform/placement/audience 出现多个值即视为层级漂移。

输出 `投放反馈/feedback_report.json` 与 `.md`，并分开给 `analysis_status=interim/complete/invalid`。validation 是可重算派生物：导入和阶段验收都会从 canonical plan 重算功效、停止规则、平台配置与 readiness，忽略时间字段后语义不一致即失效，不能只靠旧 `plan_sha256`。`analysis_receipts` 绑定当前 plan、validation、brief、campaign readiness、canonical raw、逐变体媒体、平台配置/结果 receipt 及其证据 SHA；路径必须是作品内相对路径，绝对路径、`..` 与 symlink 越界均拒绝，任一内容变化都会令 feedback stale。未达到功效样本量或停止条件时仍可生成 `directional_only` 中期报告，但不得 `--mark-progress`，也不能取得 feedback 阶段 ✅；停止条件满足但无显著赢家可是 `complete + directional_only`。没有当前、已批准的预注册计划时会 block 且绝不宣布胜者。`local_binomial` 只有计数口径/独立单元一致、同层可比、每臂达到功效目标、停止条件完成，且 Bonferroni 后的 pooled score tests 均支持头名优于其它臂时，才给 `local_qualified_winner`；Wilson 区间只作展示。`platform_native` 的当前、完整 receipt 可给 `platform_qualified_winner/platform_no_winner/platform_inconclusive`。CPA/ROAS 只有聚合值而没有事件级方差时一律只作方向性读取。结果回流 `ad-concept`/`ad-script`，不自动覆盖原片或客户 brief。

## 原则

- 创意假设必须可分解为 hook / key message / CTA，避免把多个变量同时改变后误判因果。
- 归因窗口、conversion event、平台、placement、受众和预算须与 brief.measurement/platform_pack 对齐；跨版位数据不是同一可比层。
- 平台原生的随机分桶、显著性与实验报告优先；本地判定只用与功效设计一致、按预注册 familywise alpha 调整的两比例 score test。Wilson 区间仅展示，不冒充平台 bucket/Jackknife 方法。
- frequency 上升且 CTR/ROAS 下滑时标疲劳，优先刷新 hook/caption/开场，不把疲劳误判为产品失败。
- 3s 观看率（hook rate）有数据且样本合格时按基准地板快筛：`view_3s_rate < 25%` → `hook_rate_low` warn（2026 业界基准·会过期快照）——前 3 秒失败时后段再强也到不了，优先单变量换 hook 复测；`video_3s` 全 0 视为字段缺失不判。
- 不用投放前启发式代替真实数据，也不凭小样本宣布胜者。

共同计划字段：`design_mode/hypothesis/primary_kpi/conversion_event/attribution_window/platform/placement/audience/randomization_unit/decision_rule/start_date/end_date/min_impressions/held_constant/variants[]`；每个 variant 必填作品根内相对 `asset_path` 与当前 `asset_sha256`。本地模式再必填功效、计数口径、`analysis_unit/independent_bernoulli`、停止和 Bonferroni 字段；平台模式必填显式实验 ID 的配置 receipt。导入时 KPI、变体、平台、placement、受众、功效目标、停止规则和所有文件 SHA 均从已批准计划读取并现场重核，不能投放后换素材或调低门槛。
