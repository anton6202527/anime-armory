# n2d-feedback Schema

## platform_metrics

支持 CSV、JSONL、JSON list。推荐路径：

```text
制漫剧/<剧名>/生产数据/platform_metrics.csv
```

字段：

| 字段 | 必填 | 说明 |
|---|---|---|
| `episode` | 是 | `第1集` 或 `1` |
| `platform` | 否 | 平台，如 `douyin` / `hongguo` / `youtube_shorts` |
| `publish_id` | 否 | 平台稿件 ID |
| `ab_test_id` | A/B 建议 | 同一组 A/B 实验 ID；同集同平台下用于 paired lift |
| `variant_id` | A/B 建议 | 变体 ID，如 `A` / `B` / `open_cold_v1` |
| `published_at` | 否 | 发布时间 |
| `plays` | 否 | 播放量；用于加权均值 |
| `revenue` | ROI 建议 | 投放/分账/广告/付费总收入；也兼容 `gross_revenue/total_revenue/income` |
| `distribution_spend` | ROI 建议 | 投流/买量/分发成本；也兼容 `promotion_spend/ad_spend/traffic_cost/platform_spend` |
| `currency` | ROI 建议 | 收入和投放成本币种，默认 CNY；dashboard 只做同币种回收比，不跨币种换算 |
| `ctr` | 否 | 点击率/封面标题点击率，0-1；平台能导出时用于封面/标题复核 |
| `retention_3s` | 建议 | 3 秒留存，0-1 |
| `retention_5s` | 否 | 5 秒留存，0-1 |
| `retention_15s` | 建议 | 15 秒留存，0-1 |
| `completion_rate` | 建议 | 完播率，0-1 |
| `follow_next_rate` | 建议 | 追更/下一集点击率，0-1 |
| `bounce_3s` | 建议 | 3 秒跳出率，0-1；缺失时用 `1-retention_3s` 估算 |
| `avg_watch_sec` | 否 | 平均观看秒数 |
| `duration_sec` | ROI 建议 | 成片时长；dashboard 用它算每分钟成本。缺失时回退 `storyboard.json.total_duration` |

示例：

```csv
episode,platform,ab_test_id,variant_id,plays,revenue,distribution_spend,currency,duration_sec,ctr,retention_3s,retention_15s,completion_rate,follow_next_rate,bounce_3s
第1集,douyin,EP01_opening,A,12000,86.5,30,CNY,92,0.061,0.78,0.52,0.31,0.18,0.12
第1集,douyin,EP01_opening,B,11000,64.0,30,CNY,92,0.055,0.63,0.41,0.25,0.11,0.24
第2集,douyin,EP02_opening,A,9000,40.0,25,CNY,78,0.058,0.55,0.35,0.22,0.09,0.28
```

> A/B 数据一条变体一行。没有 `ab_test_id/variant_id` 时仍按旧版单集复盘；有它们时报告额外生成同集 paired lift，避免不同集剧情差异误导。
> ROI 字段由 `n2d-dashboard` 自动读取并合并进 `dashboard.json/md`；`n2d-feedback` 只用留存/追更/A-B 分析，不负责算生产回收比。

## creative_features

推荐路径：

```text
制漫剧/<剧名>/生产数据/creative_features.csv
制漫剧/<剧名>/生产数据/creative_features.auto.json
```

`creative_features.csv|jsonl|json` 是手工覆盖文件；缺失时 `feedback.py` 默认从 `脚本/第N集/storyboard.json` 自动抽取。自动文件只作复核快照，不覆盖手工标签。

字段：

| 字段 | 必填 | 说明 |
|---|---|---|
| `episode` | 是 | 与 platform metrics 对齐 |
| `ab_test_id` | A/B 建议 | 与 platform metrics 对齐；也可只放在 metrics 中 |
| `variant_id` | A/B 建议 | 与 platform metrics 对齐；features 会按 `episode+variant_id` join，缺变体特征时回退 episode 基础特征 |
| `opening_type` | 建议 | 开场类型，如 `cold_conflict` / `reverse_flash` / `dialogue_hook` / `slow_lore` |
| `opening_variant` | A/B 建议 | 开场变体，如 `cold_open_first` / `system_panel_first` |
| `cover_variant` | A/B 建议 | 封面/首图变体 ID，如 `face_closeup` / `crisis_tableau` |
| `cliffhanger_type` | 建议 | 集尾类型，如 `crisis_suspend` / `truth_half_reveal` / `reversal_signal` / `resolved_clean` |
| `cliffhanger_cut_variant` | A/B 建议 | 集尾断点变体，如 `hard_cut_before_reveal` / `truth_half_reveal` |
| `title_variant` | A/B 建议 | 标题/文案变体 ID 或短文案；也兼容 `title_copy` |
| `shot_density_per_min` | 建议 | 每分钟镜头数；缺失可用 `avg_shot_sec` 推算 |
| `avg_shot_sec` | 否 | 平均镜头秒数 |
| `hook_interval_sec` | 建议 | 平均钩子/信息增量间隔 |
| `first_3s_asset` | 否 | 开场镜头或台词标识 |
| `final_hook_asset` | 否 | 集尾钩子镜头或台词标识 |
| `opening_confidence` | 自动 | 自动推断置信度，0-1 |
| `opening_signals` | 自动 | 自动推断命中的开场信号 |
| `cliffhanger_confidence` | 自动 | 自动推断置信度，0-1 |
| `cliffhanger_signals` | 自动 | 自动推断命中的集尾信号 |
| `hook_count` | 自动 | 自动识别的钩子/爽点/反转/信息增量数量 |
| `hook_signals` | 自动 | 自动识别钩子的 Clip 与原因 |
| `creative_features_source` | 自动 | `storyboard_auto` 或人工来源 |

示例：

```csv
episode,ab_test_id,variant_id,opening_type,opening_variant,cover_variant,cliffhanger_type,cliffhanger_cut_variant,title_variant,shot_density_per_min,hook_interval_sec
第1集,EP01_opening,A,cold_conflict,cold_open_first,face_closeup,crisis_suspend,hard_cut_before_reveal,"她刚重生，就被赐死",24,15
第1集,EP01_opening,B,system_hook,system_panel_first,crisis_tableau,truth_half_reveal,truth_half_reveal,"系统第十七弹：赐死局",24,15
第2集,EP02_opening,A,slow_lore,lore_first,face_closeup,resolved_clean,resolved_clean,"冷宫第一夜",11,28
```

自动抽取命令：

```bash
python3 skills/n2d-feedback/scripts/feedback.py 制漫剧/<剧名> --extract-features-only --write-features
python3 skills/n2d-feedback/scripts/feedback.py 制漫剧/<剧名> --metrics 制漫剧/<剧名>/生产数据/platform_metrics.csv --write-features
```

自动抽取规则：

| 字段 | 来源 |
|---|---|
| `opening_type` | 首 Clip / 前 15 秒的冲突、系统钩、倒叙、对白钩、奇观、慢设定信号 |
| `cliffhanger_type` | 尾部两 Clip 的危机悬置、真相半露、反转预告、讲完整收干净信号 |
| `shot_density_per_min` | `len(clips) / total_duration * 60` |
| `avg_shot_sec` | `total_duration / len(clips)` |
| `hook_interval_sec` | `rhythm`、转场、系统/危机/爽点/反转/真相信号识别钩子后求平均间隔 |

## 输出

```text
生产数据/platform_feedback.json
生产数据/platform_feedback.md
```

顶层 JSON：

```json
{
  "kind": "n2d_platform_feedback",
  "version": 1,
  "generated_at": "2026-06-08T00:00:00+00:00",
  "sample_count": 12,
  "source": {
    "metrics": "生产数据/platform_metrics.csv",
    "features": "storyboard:auto"
  },
  "feature_extraction": {
    "mode": "storyboard_auto",
    "episodes": ["第1集", "第2集"],
    "missing_storyboards": []
  },
  "analyses": {
    "opening_retention": {},
    "cliffhanger_follow": {},
    "shot_density_bounce": {},
    "hook_interval_retention": {},
    "ab_opening_retention": {},
    "ab_cover_retention": {},
    "ab_cliffhanger_follow": {},
    "ab_title_retention": {}
  },
  "recommendations": []
}
```

A/B 分析说明：

| analysis | 分组字段 | 主指标 | 说明 |
|---|---|---|---|
| `ab_opening_retention` | `opening_variant` | `retention_3s` | 同一集不同开场的 3 秒留存 paired lift |
| `ab_cover_retention` | `cover_variant` | `retention_3s` | 同一集不同封面/首图的留存；有 `ctr` 时同时展示点击率 |
| `ab_cliffhanger_follow` | `cliffhanger_cut_variant` | `follow_next_rate` | 同一集不同集尾断点的追更 paired lift |
| `ab_title_retention` | `title_variant` | `retention_3s` | 同一集不同标题文案的 3 秒留存；有 `ctr` 时同时展示点击率 |

`n` 表示有可比较 paired context 的数量；context = `episode/platform/ab_test_id`。单版本或同一 context 里只有一个变体时，不会生成强建议。

## 导演节奏写回

`--update-guide` 会替换 `skills/novel2drama/references/导演节奏.md` 中：

```text
<!-- n2d-feedback:start -->
...
<!-- n2d-feedback:end -->
```

只替换快照，不覆盖人工维护的基础规则。

## 自有题材战绩库（genre_performance_record · 跨项目闭环）

`--emit-ledger` 把本剧第一方战绩按题材追加进 append-only JSONL 战绩库，供 `novel-score` 读为题材热度的第一方先验，闭合 **选题→生产→投放→反哺选题**。

- 路径：`$N2D_GENRE_LEDGER` 或 `<repo>/生产战绩/genre_ledger.jsonl`（`--ledger` 覆盖）。**跨项目共享**。
- 一条记录 = 一次「某剧×某次回灌」的题材级聚合：

```json
{
  "kind": "genre_performance_record",
  "version": 1,
  "recorded_at": "2026-06-08T00:00:00+00:00",
  "work": "制漫剧/某仙侠剧",
  "title": "某仙侠剧",
  "genre": "仙侠",
  "subgenres": ["复仇", "马甲"],
  "platform": "红果",
  "episode_count": 12,
  "metrics": {
    "retention_3s": 0.58,
    "retention_15s": 0.41,
    "completion_rate": 0.29,
    "follow_next_rate": 0.33,
    "roi": 1.4,
    "plays": 1200000
  },
  "features": {
    "opening_type": "cold_conflict",
    "cliffhanger_type": "crisis_suspend",
    "shot_density_bucket": "20-30/m 标准快节奏"
  },
  "source": "n2d-feedback"
}
```

- `metrics` 内除 `plays`（总和）外均按播放量加权；`roi` 取 metrics 的 `roi/roas/回收比`（加权）或 `revenue÷spend`（汇总），无则省略。
- `features`：该剧主导创意特征（按播放量加权众数）；缺 creative_features/storyboard 时为 `{}`。供差异化引擎做"题材×特征"白空间分析。
- 读取端（novel-score）按 `genre` 聚合匹配记录；题材未命中时回退全库整体水位并标注。两条线**只在此文件层连接，不互相 import**。

## 差异化候选 差异化候选.json（反同质化引擎 differentiate.py 产物）

读战绩库点云 +（可选）公榜基线 → `生产战绩/差异化候选.{json,md}`：

```json
{
  "kind": "n2d_differentiation_candidates", "version": 1, "metric": "follow_next_rate",
  "ledger_records": 5, "candidate_genres": ["仙侠", "都市"],
  "proven_opening": {"reverse_flash": 0.41},
  "proven_cliffhanger": {"crisis_suspend": 0.39, "reversal_signal": 0.41},
  "saturated_genres": {"仙侠": 4, "都市": 1},
  "occupied_combos": [{"combo": ["仙侠", "cold_conflict", "crisis_suspend"], "n": 2}],
  "candidates": [
    {"genre": "都市", "opening_type": "reverse_flash", "cliffhanger_type": "crisis_suspend",
     "label": "都市 × 倒叙闪回 × 危机悬置", "score": 2.49, "market_saturation": 1,
     "reuses_proven": ["开场 倒叙闪回(已验证追更 41%)", "结尾 危机悬置(已验证 39%)"]}
  ],
  "notes": ["样本不足只作启发…"]
}
```

`candidates` = 未被我们做过（occupancy=0）× 复用 ≥1 已验证轴 × 避开最饱和题材，按"是否复用已验证轴→市场饱和→分数"排序。选题端（novel-create/novel-title/novel-score）读它当差异化输入；novel-score 第一方题材先验仍优先。`--genres` 注入候选题材；引擎不凭空捏造题材，样本/基线不足时在 notes 显式降级。

## 投放摄取适配器（实时投放 API → 标准文件）

`生产数据/platform_metrics.{csv,jsonl,json}` 是**摄取边界契约**。实时投放数据由定时任务/webhook 规范化成该文件，feedback 再消费——平台/后端可换，闭环不变。`metric()` 解析时按下表把常见列名（含中文）映射到 canonical，所以平台原始导出无需手工改列：

| canonical | 别名（任一命中即可） |
|---|---|
| `retention_3s` | `3s_retention` / `ret3s` / `3秒留存` / `3秒留存率` / `三秒留存` |
| `retention_15s` | `15s_retention` / `ret15s` / `15秒留存` / `15秒留存率` |
| `completion_rate` | `completion` / `complete_rate` / `完播率` / `完播` / `看完率` |
| `follow_next_rate` | `follow_rate` / `next_follow_rate` / `追更率` / `追更` / `下集点击率` |
| `plays` | `play_count` / `views` / `view_count` / `exposure` / `播放` / `播放量` / `曝光` |
| `ctr` | `click_through_rate` / `点击率` / `封面点击率` / `封面ctr` |

ROI 相关（用于战绩库）：`roi/roas/回收比/投产比`，或 `revenue/income/营收/收入/回收` ÷ `spend/cost/投放成本/成本/花费`。别名表外的列名仍可用 `--features` 或预处理对齐后再喂。
