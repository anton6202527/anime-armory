---
name: n2d-feedback
description: P2 platform performance feedback loop for n2d. Ingest platform metrics, analyze retention/follow/A-B lift, write platform_feedback, and optionally update director rhythm. Use when asked for 投放数据回灌, 平台数据反哺, 留存数据, 追更率, 跳出率, 投放A/B, platform feedback.
---

# n2d-feedback — P2 投放数据回灌

`n2d-feedback` 把平台投放数据反哺 `导演节奏.md`。它回答四类问题：

- 哪种 **0-3s 开场** 留存最高；
- 哪类 **cliffhanger** 追更率最高；
- 哪个 **镜头密度 / 钩子间隔** 导致跳出。
- 同一集做不同 **开场 / 封面 / 集尾断点 / 标题文案** 时，哪个变体的同集 paired lift 更高。

它不替代 `n2d-dashboard`。dashboard 管生产成本、每分钟成本、每集耗时、一次通过率、重抽率、投放回收；feedback 管上线后的留存、追更、跳出和 A/B lift，并把结论写回导演节奏规则。`platform_metrics.*` 可被两者共用：feedback 看用户行为，dashboard 看 ROI。

## 输入 / 输出 / 读写边界

- **输入**：`platform_metrics.*`、`creative_features.*`、`storyboard.json` 自动导演标签、consistency/review-ui findings。
- **输出**：`生产数据/platform_feedback.json/md`、可选 `导演节奏.md` 快照块、`creative_experiments.json`、`creative_experiment_audit.json/md`。
- **读写边界**：只做投放归因和节奏反哺；不审片、不重剪已上线集、不直接改生产产物。
- **契约关系**：一致性 findings 使用统一 kind；ROI 指标与 `n2d-dashboard` 共享数据边界但不重复记账。

## 输入数据

需要两类数据 join：

1. **platform metrics**：平台侧指标，如 `retention_3s`、`retention_6s`、`retention_15s`、`retention_25_pct`、`retention_50_pct`、`retention_75_pct`、`completion_rate`、`follow_next_rate`、`avg_watch_sec`、`avg_episodes_per_user`、`episodes_per_session`、`unlock_or_subscribe_rate`、`story_roi`、`bounce_3s`、`plays`。这些字段来自 `n2d-dashboard/references/industry_benchmark.json` 的 `episode_kpi_targets.required_metrics`；缺失会进入 `input_audit`，不能当成“平台没给就无事发生”。付费/追剧闭环必须补 `paywall_position_sec`、`paywall_after_promise_id`、`unlock_friction`、`continue_path`，用于分析“卡点是否落在承诺之后、解锁摩擦是否伤留存、哪条续看路径追更最高”。A/B 时每个变体一行，建议带 `ab_test_id`、`variant_id`、`ctr`。App/剧集包级可带 `d1_retention/d7_retention/d14_retention`。
2. **creative features**：导演标签，如 `opening_type`、`cliffhanger_type`、`shot_density_per_min`、`hook_interval_sec`、`first_3s_visual_hook`、`onscreen_text_hook`、`muted_safe_proof`、`retention_promise_ids`。A/B 时补 `opening_variant`、`cover_variant`、`cliffhanger_cut_variant`、`title_variant`。默认从 `脚本/第N集/storyboard.json` 自动抽取基础标签；已有手工 `creative_features.*` 或显式 `--features` 时优先手工。

默认读取：

```text
创作区/制漫剧/<剧名>/生产数据/platform_metrics.csv|jsonl|json
创作区/制漫剧/<剧名>/生产数据/creative_features.csv|jsonl|json（可选，覆盖自动抽取）
```

详细 schema 见 `references/schema.md`。

## 标准命令

```bash
python3 skills/n2d-feedback/scripts/feedback.py <作品根> \
  --metrics <平台指标.csv>
```

输出：

```text
生产数据/platform_feedback.json
生产数据/platform_feedback.md
```

## 投放 A/B 化

> **实验结论必须满足统计合同**：`experiments.py audit` 的 `min_samples` 按**每个变体**计算，不再把 A+B 总播放量相加；每个变体输出加权转化率与 Wilson 95% 区间，候选相对登记的 control 做双侧两比例 z 检验，多候选用 Bonferroni 校正。只有每个变体都达样本量且校正后 `p < alpha` 才可 `promote_variant/keep_control`；否则是 `no_significant_difference` 或 `insufficient_samples`。分流差异过大、固定样本实验出现多次 `look_index` 又无 alpha-spending 时标 `analysis_design_review`，禁止把中途偷看后的偶然领先写成导演铁律。

同一集可以上多个变体，不再只复盘单版本。最小做法：

1. 为同一集生成 2-4 个变体：开场顺序、封面/首图、集尾断点、标题文案一次只重点改 1-2 个变量，避免归因混乱。
2. `platform_metrics` 每个变体一行，写 `episode + platform + ab_test_id + variant_id + plays + retention_3s + retention_6s + retention_15s + retention_25_pct + retention_50_pct + retention_75_pct + completion_rate + follow_next_rate`；平台能导出点击率时加 `ctr`，付费/追剧平台加 `unlock_or_subscribe_rate`、`avg_episodes_per_user`。
3. `creative_features` 每个变体一行，写 `opening_variant / cover_variant / cliffhanger_cut_variant / title_variant`，并补首屏与承诺字段：`first_3s_visual_hook / onscreen_text_hook / muted_safe_proof / retention_promise_ids`。付费平台再补 `paywall_after_promise_id / unlock_friction / continue_path`，确认解锁卡点接在已登记承诺之后。如果只改标题或封面，基础 `opening_type/cliffhanger_type` 可继承自动抽取。
4. 运行 feedback 后看新增四张表：`A/B 开场留存`、`A/B 封面留存`、`A/B 集尾断点追更`、`A/B 标题文案留存`。这些表使用同一 `episode/platform/ab_test_id` 内的 paired lift，优先级高于跨集泛分组。

推荐字段示例：

```csv
episode,platform,ab_test_id,variant_id,opening_variant,cover_variant,cliffhanger_cut_variant,title_variant,plays,ctr,retention_3s,retention_15s,completion_rate,follow_next_rate
第1集,douyin,EP01_launch,A,cold_open_first,face_closeup,hard_cut_before_reveal,她刚重生就被赐死,12000,0.061,0.78,0.52,0.31,0.18
第1集,douyin,EP01_launch,B,system_panel_first,crisis_tableau,truth_half_reveal,系统第十七弹赐死局,11000,0.055,0.63,0.41,0.25,0.11
```

> A/B 结论只在每组至少 `--min-samples` 个 paired context 后给强建议。单集单平台只有一次 A/B 时，报告会展示表格，但仍按“观察中”处理。

### 实验登记（避免事后归因）

A/B 开跑前先登记实验定义，投放数据回来后审计 `platform_metrics` 是否都有对应定义、变体是否齐、样本是否够：

```bash
python3 skills/n2d-feedback/scripts/experiments.py upsert <作品根> \
  --id EP01_launch \
  --episode 第1集 \
  --hypothesis "前3秒先露危机比先露系统面板留存更高" \
  --variant A=cold_open_first \
  --variant B=system_panel_first \
  --primary-metric retention_3s \
  --min-samples 1000 \
  --alpha 0.05 \
  --write

python3 skills/n2d-feedback/scripts/experiments.py audit <作品根> \
  --metrics <平台指标.csv> --alpha 0.05 --write
```

输出 `生产数据/creative_experiments.json` 与 `creative_experiment_audit.json/md`。`audit.status=fail` 表示 metrics 里有 `ab_test_id` 没有实验定义；`observe` 表示变体或样本不足，只能观察，不能写成导演铁律。

## 写回导演节奏

```bash
python3 skills/n2d-feedback/scripts/feedback.py <作品根> \
  --metrics <平台指标.csv> \
  --update-guide
```

`--update-guide` 只替换 `导演节奏.md` 里的 `n2d-feedback` 快照块，不改基础规则。样本不足时只写“观察中”，不把偶然值升级成铁律。

## 写回机器可读先验（投放→生成输入闭环）

`--update-guide` 写的是给人看的导演节奏规则；`--write-priors` 写的是给机器读的**第一方先验**——把 A/B paired-lift 胜出的开场/集尾断点/封面/标题变体，以及分组 lift 胜出的付费卡点位置、续看路径，凝成 `生产数据/creative_priors.json`（kind `n2d_creative_priors`），`n2d-script` 阶段2 finalize 读它作开场/断点/卡点/追更设计的**建议先验**。

**闭环修真（F2·2026-06-26·破橡皮图章）**：此前 finalize 对每条先验**无条件**盖 `status='applied'`，让 `beat_audit --strict` 的 `creative_prior_not_acknowledged` 形同虚设——跑一下 finalize 就「已确认」，第一方投放胜出信号被橡皮图章吞掉。现 finalize 按 storyboard 的 `creative_variants_used`（{字段:{variant:采用的变体, reason?:不采胜出时的理由}}）**真验证采纳**：采用胜出变体=`applied`；采用他变体+写理由=`rejected`(可解释)；采用他变体无理由 / 未声明=`pending`（beat_audit --strict 会拦，交分析师真决策）。证据元数据键改名 `prior_metrics`（原 `applied_creative_priors`），避免 beat_audit legacy 路径误把元数据当 applied 自动盖章。**不自动改写内容**——尊重 analyst-in-loop（2026 SOTA：全自动闭环尚不成立，结构化人审在环才是前沿；本闭环只「自动 ingest 先验 + 强制人对每条胜出信号真决策」，不替分析师改剧本）。

```bash
python3 skills/n2d-feedback/scripts/feedback.py <作品根> \
  --metrics <平台指标.csv> \
  --write-priors
```

每个维度只在「同集内 `paired_lift ≥ --min-lift` 且 paired context 数 `≥ --min-samples`」时才写先验，缺省维度直接不写（**不臆造**）；无任一维度达标时落空 `priors:{}`，下游 no-op。每条先验带 `winner / paired_lift / primary_metric / metric_value / n / plays / episodes`，并写入 `generated_at` 采集时间供下游判先验新鲜度。`--no-write` 同时抑制 priors 写出。

读端在 `n2d-script` 阶段2 finalize：存在 `creative_priors.json` 才读（缺则 no-op·向后兼容），把胜出先验作为开场/断点/付费卡点/追更路径设计的建议注入——落 `脚本/第N集/applied_creative_priors.json` 证据 + 打印人可见提示（逐维度点名 winner / lift / n），不静默吞。先验是建议非硬约束，样本不足的维度不出现、不必强套；但已有先验必须被 `beat_audit --strict` 看见 applied 或 rejected + reason。

## 写回 pacing 密度带校准（第一方留存 → 节奏阈值）

`density_slow/fast_per_min`（节奏机检"健康镜/分钟带"）原是 `confidence=low` 的内部启发式——`industry_benchmark.json` 明写「短剧 CPM/SPM 无可辩护的公开基准，真值须由 n2d-feedback 第一方留存数据校准」。`--write-pacing-profiles` 即该校准的**写端**：据已算好的 `shot_density_bounce`（按 `shot_density_bucket` 看 `bounce_3s`，越低留存越好），把「跳出率 ≤ 全剧均值且样本 ≥ `max(--min-samples,3)`」的密度档并成健康带 `[slow,fast)`，写 `生产数据/pacing_profiles.json`（kind `n2d_pacing_profiles`）。

```bash
python3 skills/n2d-feedback/scripts/feedback.py <作品根> \
  --metrics <平台指标.csv> \
  --write-pacing-profiles
```

诚实边界：无合格档 / 样本不足 / 退化成窄带 → `evidence_status='insufficient_samples'` 且 `thresholds={}`（**不臆造**），消费端只认 `calibrated`，否则静默退回 benchmark/默认。读端是 `n2d-review/scripts/pacing_retention.py`：阈值优先级 **env 覆盖 > 第一方校准 profile > benchmark JSON > 写死默认**；采用校准时在报告 `metrics.pacing_threshold_source` 标 `calibrated(genre,n)` 留痕。**advisory 契约不变**——校准只调"健康密度带"，`verdict` 仍封顶到 `warn`，绝不创造 block。

## 投放摄取适配器（实时投放 API → 标准文件）

`platform_metrics.{csv,jsonl,json}` 是**摄取边界契约**：实时投放数据不直连脚本，而是由定时任务 / webhook（可配合 `schedule`/`loop`）把平台 API 导出**规范化成这个标准文件**，feedback 再消费——后端可换，闭环不变。列名只要落在适配器别名表内即可被摄取（含中文列）：`3秒留存率→retention_3s`、`追更率→follow_next_rate`、`完播率→completion_rate`、`播放量→plays`、`封面点击率→ctr` 等（见 `references/schema.md`「投放摄取适配器」）。无实时 API 时，手工导出 CSV 落到该路径即可，流程一致。

## 自动导演标签

默认没有 `creative_features.*` 时，脚本会按平台指标里的集号读取 `脚本/第N集/storyboard.json`，自动推断：

- `opening_type`：由首 Clip / 前 15 秒的冲突、系统钩、倒叙、对白钩、奇观、慢设定等信号判定；
- `cliffhanger_type`：由尾部两 Clip 的危机悬置、真相半露、反转预告、讲完整收干净等信号判定；
- `shot_density_per_min`：`clips[]` 数量 ÷ `total_duration`；
- `hook_interval_sec`：按 `rhythm`、转场、系统/危机/爽点/反转/真相关键词推断钩子时间点后求平均间隔。

抽取结果会带 `opening_confidence`、`cliffhanger_confidence`、`*_signals` 和 `creative_features_source=storyboard_auto`，用于人工复核。需要落文件时：

```bash
python3 skills/n2d-feedback/scripts/feedback.py <作品根> --extract-features-only --write-features
python3 skills/n2d-feedback/scripts/feedback.py <作品根> --metrics <平台指标.csv> --write-features
```

手工特征仍可用 `--features <导演标签.csv>` 覆盖；需要强制旧模式时用 `--no-auto-features`。

## 使用原则

- **没有导演标签就不能归因**：平台数据只知道留存，不知道开场类型；默认先从 `storyboard.json` 自动抽取，低置信或误判再用手工 `creative_features` 覆盖。
- **样本不足只做观察**：默认每组至少 `2` 个样本才给强建议，可用 `--min-samples` 调整。**两套"样本"口径必须分清（2026-07 审计澄清）**：feedback 的 `min_samples` 数的是 **paired context 数**（同集同平台配对组，探索性地板，2 个 context 可能只有几十次播放）；experiments 的 `min_samples` 数的是 **每变体播放量**（默认 1000，统计合同地板）。前者只配"观察/建议"，**铁律必须过 experiments audit**。
- **写回有统计合同门（2026-07 落地）**：metrics 含 `ab_test_id` 行时，`--write-priors/--update-guide/--write-pacing-profiles` 会先跑 `experiments.audit_metrics`；status 非 `pass`（缺实验定义/每变体欠样本/顺序偷看）默认**拒写**并打印原因，`--force-writeback` 才可显式强推（留痕自负）。input_audit 存在 `must` 级缺口（付费维度字段缺失）时写回前打印醒目告警。纯观察数据（无 A/B 行）不受此门限制。
- **看 lift，不看孤立绝对值**：跨集分组看相对总体 lift；A/B 先看同集 paired lift，避免剧情强弱、平台流量波动误导。
- **A/B 一次别混太多变量**：开场、封面、断点、标题可以同集多版本，但要在字段里标清；若四项同时变化，结论只能说“组合胜出”，不能硬归因到单个元素。
- **回灌只改节奏策略**：结论进入 `导演节奏.md`，不直接改已生产集；下一批分镜时由 `n2d-script` 吸收。
- **平台分开看**：抖音、红果、YouTube Shorts 的用户行为不同；数据可混看，但报告保留 `platform`，必要时按平台分批跑。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 只导出播放量 | 播放量不是留存；至少要 `retention_3s`、`completion_rate`、`follow_next_rate` |
| 没有开场/cliffhanger 标签 | 先确认 `脚本/第N集/storyboard.json` 是否存在；可跑 `--extract-features-only --write-features` 生成自动标签，再人工修正 |
| 一集数据就改铁律 | 样本不足只写观察，不写“必须” |
| 同一集多个投放版本但没写 `variant_id` | 补 `ab_test_id + variant_id`；否则脚本只能当普通多条平台数据，不能算 paired lift |
| 开场/封面/标题/断点全一起改 | 可以测试组合，但不能单因素归因；下一轮拆成单变量或正交实验 |
| 把投放回灌当审片 | 审片走 `n2d-review` / `n2d-score`；feedback 看上线后的用户行为 |

## 一致性问题回灌（QA 线接进投放闭环）

`analyze` 时自动读 `生产数据/consistency_findings_*.json`（`n2d-review` 的 `consistency_audit.py` 外发）和 `review_ui_findings_*.json`（人审 UI 导出），两者 kind 都是 `n2d_consistency_findings`。报告新增「一致性问题 Top」节：按维度（脸/服装/场景/风格/语义/状态/契约继承等）计数、标出一致性问题最严重的集，并与同集留存/跳出指标**并排呈现**——回答"脸漂严重的集是不是跳出率也高"。无 findings 文件时优雅跳过，不影响原有分析。
