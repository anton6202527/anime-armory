---
name: n2d-feedback
description: P2 platform performance feedback loop for novel2drama/n2d. Ingest release/platform metrics (real-time API exports normalize into a standard platform_metrics file via an ingest adapter), auto-extract creative feature tags from storyboard.json when missing, support same-episode A/B variants for opening, cover, cliffhanger cut, and title copy, analyze retention/follow lift, write platform_feedback JSON/Markdown plus optional director rhythm updates, AND emit a per-genre first-party performance record (with dominant creative features) to a cross-project 自有题材战绩库 (genre ledger) so novel-score can use it as a first-party 题材热度 prior — closing the 选题→生产→投放→反哺选题 loop. Also includes an anti-homogenization differentiation engine (differentiate.py) that reverse-derives under-explored 题材×开场×结尾 combinations from the ledger point cloud + market baseline (white space × proven feature axes × avoid saturated genres). Use when asked for 投放数据回灌, 平台数据反哺, 留存数据, 追更率, 跳出率, 开场留存, cliffhanger追更, 镜头密度跳出, 投放A/B, AB测试, 开场AB, 封面AB, 标题AB, 集尾断点AB, 反哺选题, 题材战绩库, genre ledger, 选题闭环, 反同质化, 差异化选题, 差异化引擎, 未被做烂的组合, 白空间, differentiation, growth feedback, platform feedback, 自动提取导演标签, creative_features.
---

# n2d-feedback — P2 投放数据回灌

`n2d-feedback` 把平台投放数据反哺 `导演节奏.md`。它回答四类问题：

- 哪种 **0-3s 开场** 留存最高；
- 哪类 **cliffhanger** 追更率最高；
- 哪个 **镜头密度 / 钩子间隔** 导致跳出。
- 同一集做不同 **开场 / 封面 / 集尾断点 / 标题文案** 时，哪个变体的同集 paired lift 更高。

它不替代 `n2d-dashboard`。dashboard 管生产成本、每分钟成本、每集耗时、一次通过率、重抽率、投放回收；feedback 管上线后的留存、追更、跳出和 A/B lift，并把结论写回导演节奏规则。`platform_metrics.*` 可被两者共用：feedback 看用户行为，dashboard 看 ROI。

## 输入数据

需要两类数据 join：

1. **platform metrics**：平台侧指标，如 `retention_3s`、`retention_15s`、`completion_rate`、`follow_next_rate`、`bounce_3s`、`plays`。A/B 时每个变体一行，建议带 `ab_test_id`、`variant_id`、`ctr`。
2. **creative features**：导演标签，如 `opening_type`、`cliffhanger_type`、`shot_density_per_min`、`hook_interval_sec`。A/B 时补 `opening_variant`、`cover_variant`、`cliffhanger_cut_variant`、`title_variant`。默认从 `脚本/第N集/storyboard.json` 自动抽取基础标签；已有手工 `creative_features.*` 或显式 `--features` 时优先手工。

默认读取：

```text
制漫剧/<剧名>/生产数据/platform_metrics.csv|jsonl|json
制漫剧/<剧名>/生产数据/creative_features.csv|jsonl|json（可选，覆盖自动抽取）
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

同一集可以上多个变体，不再只复盘单版本。最小做法：

1. 为同一集生成 2-4 个变体：开场顺序、封面/首图、集尾断点、标题文案一次只重点改 1-2 个变量，避免归因混乱。
2. `platform_metrics` 每个变体一行，写 `episode + platform + ab_test_id + variant_id + plays + retention_3s + retention_15s + completion_rate + follow_next_rate`；平台能导出点击率时加 `ctr`。
3. `creative_features` 每个变体一行，写 `opening_variant / cover_variant / cliffhanger_cut_variant / title_variant`。如果只改标题或封面，基础 `opening_type/cliffhanger_type` 可继承自动抽取。
4. 运行 feedback 后看新增四张表：`A/B 开场留存`、`A/B 封面留存`、`A/B 集尾断点追更`、`A/B 标题文案留存`。这些表使用同一 `episode/platform/ab_test_id` 内的 paired lift，优先级高于跨集泛分组。

推荐字段示例：

```csv
episode,platform,ab_test_id,variant_id,opening_variant,cover_variant,cliffhanger_cut_variant,title_variant,plays,ctr,retention_3s,retention_15s,completion_rate,follow_next_rate
第1集,douyin,EP01_launch,A,cold_open_first,face_closeup,hard_cut_before_reveal,她刚重生就被赐死,12000,0.061,0.78,0.52,0.31,0.18
第1集,douyin,EP01_launch,B,system_panel_first,crisis_tableau,truth_half_reveal,系统第十七弹赐死局,11000,0.055,0.63,0.41,0.25,0.11
```

> A/B 结论只在每组至少 `--min-samples` 个 paired context 后给强建议。单集单平台只有一次 A/B 时，报告会展示表格，但仍按“观察中”处理。

## 写回导演节奏

```bash
python3 skills/n2d-feedback/scripts/feedback.py <作品根> \
  --metrics <平台指标.csv> \
  --update-guide
```

`--update-guide` 只替换 `导演节奏.md` 里的 `n2d-feedback` 快照块，不改基础规则。样本不足时只写“观察中”，不把偶然值升级成铁律。

## 反哺选题（跨项目「自有题材战绩库」· 闭环上游）

`--update-guide` 反哺的是**节奏层**（开场/集尾/密度/钩子）。要闭合**选题→生产→投放→反哺选题**的环，还要把本剧第一方战绩**按题材**沉淀进一个**跨项目战绩库**，供 `novel-score` 当题材热度的第一方先验——这是 n2d 在内卷市场的结构性优势（公榜谁都能爬，自有 ROI/留存只有你有）。

```bash
python3 skills/n2d-feedback/scripts/feedback.py <作品根> \
  --metrics <平台指标.csv> --emit-ledger --genre 仙侠 --subgenres 复仇,马甲
```

- 把本剧按播放量加权的 `retention_3s/retention_15s/completion_rate/follow_next_rate/roi/plays` 聚合成一条 `genre_performance_record`，按 **(work, genre, platform) upsert** 写入战绩库（JSONL）——同剧同题材同平台**重 emit 替换旧快照、不堆重复行**（战绩库是作品级聚合，重复行会让 novel-score 按播放量重复加权、带偏题材先验）；不同剧/题材/平台各占一行。无 ROI（缺 roi/roas/回收比，也无 revenue+spend）时 stderr 提示，novel-score 该维度将缺席。
- 默认路径 `$N2D_GENRE_LEDGER` 或 `<repo>/生产战绩/genre_ledger.jsonl`（`--ledger` 可改）。**跨项目共享**，不是 per-work。
- `--genre` 缺省时读 `_meta.json` 的 `genre/题材` 或 `_设置.md 题材`；读不到记 `unknown` 并告警（无法按题材反哺）。
- ROI 来自 metrics 的 `roi/roas/回收比`（按播放量加权）或 `revenue÷spend` 汇总。
- **闭环对端**：`novel-score` 用 `--genre-ledger`（默认同路径）读它 → 把「题材自有战绩」注入打分 prompt 的市场基准；本题材自有 ROI/留存若明显低于公榜热度，`topic_heat` 应下调并提示选题代差。两条线**只在这个文件层连接**，不互相 import。

> 架构：novel-* 与 n2d-* 是独立生产线，本战绩库是它们在**数据产物层**的唯一连接点（一端写、一端读，各自实现读写）。记录格式见 `references/schema.md`「自有题材战绩库」。
> `--emit-ledger` 还会把该剧**主导创意特征**（按播放量加权众数的 opening_type / cliffhanger_type / shot_density_bucket）写进记录的 `features`，供下面的差异化引擎做"题材×特征"白空间分析。

## 反同质化差异化引擎（反推"未被做烂的组合"）

内卷市场（爆款率仅 0.16%）里，光知道"什么题材热"不够——还要知道"什么组合还没被做烂"。`differentiate.py` 从战绩库这朵点云（`题材 × 开场 × 结尾节奏 × 镜头密度`）+（可选）novel-score 公榜基线，反推**差异化选题候选**：

```bash
python3 skills/n2d-feedback/scripts/differentiate.py \
  [--ledger genre_ledger.jsonl] [--baseline 评分/market_baseline_*.json] \
  [--genres 悬疑,年代] [--metric follow_next_rate] [--top 12] [--out 生产战绩/差异化候选.md]
```

三路信号合成（透明启发式，非黑箱）：
- **占用度**：战绩库里每个 `题材×开场×结尾` 组合我们做过几次 → 没做过的是白空间。
- **已验证轴**：战绩库 metrics 里加权高于均值的 opening/cliffhanger 值 = 对我们有效的节奏轴，可复用进新组合。
- **市场饱和**：公榜基线里某题材出现越多 = 越被全行业做烂 → 差异化应避开/慎投（惩罚因子）。
- **白空间候选** = 我们没做过 × 复用 ≥1 已验证轴 × 避开最饱和题材，排序输出（如「都市 × 倒叙闪回 × 危机悬置」：把仙侠里验证有效的倒叙+危机节奏，搬到没做烂的都市题材）。

`--genres` 可注入"有需求但我们没做过"的题材一起探索；只在被告知的题材集合内推荐，**不凭空捏造题材**。**诚实纪律**：战绩库样本 <3 时只作启发不作铁律；无公榜基线时仅按自有占用+已验证轴推荐，引擎会在 notes 里明说。

**缺省双写 canonical 文件**：不带 `--out` 时，`differentiate.py` 把候选写到 `<repo>/生产战绩/差异化候选.{md,json}`（固定路径，不再只打印），`novel-create` 立项访谈、`novel-title` 起名时会**自动读这个 json** 作为差异化方向输入——把"反哺选题"从产物落到选题端能稳定发现的位置。仍只在数据产物层连接，**不互相 import**。

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
- **样本不足只做观察**：默认每组至少 `2` 个样本才给强建议，可用 `--min-samples` 调整。
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

`analyze` 时自动读 `生产数据/consistency_findings_*.json`（`n2d-review` 的 `consistency_audit.py` 外发，kind=`n2d_consistency_findings`），在 `platform_feedback` 报告新增「一致性问题 Top」节：按维度（脸/服装/场景/风格/语义/状态）计数、标出一致性问题最严重的集，并与同集留存/跳出指标**并排呈现**——回答"脸漂严重的集是不是跳出率也高"。无 findings 文件时优雅跳过，不影响原有分析。
