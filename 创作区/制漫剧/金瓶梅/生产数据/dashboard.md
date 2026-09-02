# n2d 生产数据仪表盘

- 生成时间：2026-09-02T04:45:54+00:00
- 事件日志：`创作区/制漫剧/金瓶梅/生产数据/production_events.jsonl`
- 投放数据：`未发现 platform_metrics.*`

## 总览

| 集数 | 事件数 | 成本 | 耗时 | 生成次数 | 重抽 | QA阻断 | QA警告 | 生成通过率 | 可交付通过率 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 10 | 695 | — | 9h44m13s | 367 | 4 | 18 | 217 | 84.5% | 0.0% |

## ROI

| 成片分钟 | 每分钟成本 | 每集耗时 | 一次通过率 | 重抽率 | 投放播放 | 投放收入 | 投放成本 | 净回收 | 回收/生产成本 |
|---:|---|---:|---:|---:|---:|---|---|---|---:|
| 2m26s | — | 9h44m13s | 48.2% | 1.1% | 0 | — | — | — | — |

## Gate 噪声

| warn/生成 | block/生成 | 误报回收 | 误报回收率 |
|---:|---:|---:|---:|
| 0.5913 | 0.049 | 0 | 0.0% |

## 行业基准对照（只读 · 非闸门 · 采集 2026-06-25）

> 厂商宣传口径、会过期，只作并排参照线，不参与告警/阻断。可在 `_设置.md`（`基准一次通过率`/`基准重抽率`）或 `生产数据/industry_benchmark.json` 覆盖；以一次 `n2d-review` 流程自审复核为准。

| 指标 | 本作实测 | 行业基准 | 对照 |
|---|---:|---:|:---:|
| 一次通过率 | 48.2% | 90.0% | ⚠️ 差距 |
| 重抽率 | 1.1% | 10.0% | ✅ 达标 |
| 每分钟成本（CNY） | — | CNY 6.00/min | — |
| 跨集角色一致性 | 见 n2d-score 视觉分 | 95.0% | — |

### 留存基准（只读）

| 指标 | 全球短剧App参考 | 中国短剧App参考 | 说明 |
|---|---:|---:|---|
| D1 留存 | 26.9% | 28.8% | App/剧集包级，不替代单集 retention_3s/15s |
| D7 留存 | 8.6% | 11.5% | 用于判断剧集包/账号复访能力 |
| D14 留存 | 5.6% | 6.8% | 长线追更和订阅复访参考 |

> 首屏创意参考：前3秒交代内容主张=True；前6秒强钩=True；字幕/烧屏文字 5-10 words/sec。

## 逐集

| 集 | 当前前沿 | 成本 | 每分钟成本 | 耗时 | 一次通过率 | 重抽率 | 重抽原因Top3 | QA阻断 | 净回收 | 回收/成本 | 3s留存 | 15s留存 | 完播率 | 追更率 |
|---|---|---|---|---:|---:|---:|---|---:|---|---:|---:|---:|---:|---:|
| 第1集 | 出图 | — | — | 9h44m13s | 48.2% | 1.1% | 补齐同一已验收像素的 canonical generation recipe；不发生新生成调用×2；001-image-rerun Codex image_generation 真实重出 Clip_04_a1，禁止本地贴脸修复×1；用户确认后的单张恢复重试；内置 image_gen 真实生成，按 timed sub-shot 仅保留潘金莲窗后心声镜×1 | 18 | — | — | — | — | — | — |
| 第2集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第3集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第4集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第5集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第6集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第7集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第8集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第9集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第10集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |

## 重抽原因分维度

| 维度 | 次数 | 占比 |
|---|---:|---:|
| prompt 冲突 (prompt_conflict) | 3 | 75% |
| 脸漂/身份 (face_consistency) | 1 | 25% |
| **一致性小计**（脸漂/服装/场景/画风） | **1** | **25%** |

## 最新阻断

- 第1集 / image / 生成配方证据: 创作区/制漫剧/金瓶梅/生产数据/production_events.jsonl — 出图/第1集/图片/Clip05_end.png 是本集最终媒体，但 production_events.jsonl 缺对应 image/video generation/redraw pass 记录；无法追溯 provider/model/channel/route_hash、capability_evidence_id、recipe_hash、prompt_sha256、reference_bundle_sha256、backend_version、quality_tier、actual_image_inputs 和 seed 是否真实生效。
- 第1集 / image / 生成配方证据: 创作区/制漫剧/金瓶梅/生产数据/production_events.jsonl — 出图/第1集/图片/Clip05_first_a3.png 是本集最终媒体，但 production_events.jsonl 缺对应 image/video generation/redraw pass 记录；无法追溯 provider/model/channel/route_hash、capability_evidence_id、recipe_hash、prompt_sha256、reference_bundle_sha256、backend_version、quality_tier、actual_image_inputs 和 seed 是否真实生效。
- 第1集 / image / 生成配方证据: 创作区/制漫剧/金瓶梅/生产数据/production_events.jsonl — 出图/第1集/图片/Clip06_first.png 是本集最终媒体，但 production_events.jsonl 缺对应 image/video generation/redraw pass 记录；无法追溯 provider/model/channel/route_hash、capability_evidence_id、recipe_hash、prompt_sha256、reference_bundle_sha256、backend_version、quality_tier、actual_image_inputs 和 seed 是否真实生效。
- 第1集 / image / 生成配方证据: 创作区/制漫剧/金瓶梅/生产数据/production_events.jsonl — 出图/第1集/图片/EP01_CLIP05_a1.png 是本集最终媒体，但 production_events.jsonl 缺对应 image/video generation/redraw pass 记录；无法追溯 provider/model/channel/route_hash、capability_evidence_id、recipe_hash、prompt_sha256、reference_bundle_sha256、backend_version、quality_tier、actual_image_inputs 和 seed 是否真实生效。
- 第1集 / image / 生成配方证据: 创作区/制漫剧/金瓶梅/生产数据/production_events.jsonl — 出图/第1集/图片/EP01_CLIP05_a2.png 是本集最终媒体，但 production_events.jsonl 缺对应 image/video generation/redraw pass 记录；无法追溯 provider/model/channel/route_hash、capability_evidence_id、recipe_hash、prompt_sha256、reference_bundle_sha256、backend_version、quality_tier、actual_image_inputs 和 seed 是否真实生效。
- 第1集 / image / 生成配方证据: 创作区/制漫剧/金瓶梅/生产数据/production_events.jsonl — 出图/第1集/图片/EP01_CLIP06_a1.png 是本集最终媒体，但 production_events.jsonl 缺对应 image/video generation/redraw pass 记录；无法追溯 provider/model/channel/route_hash、capability_evidence_id、recipe_hash、prompt_sha256、reference_bundle_sha256、backend_version、quality_tier、actual_image_inputs 和 seed 是否真实生效。
- 第1集 / image / 生成配方证据: 创作区/制漫剧/金瓶梅/生产数据/production_events.jsonl — 出图/第1集/图片/EP01_CLIP06_a2.png 是本集最终媒体，但 production_events.jsonl 缺对应 image/video generation/redraw pass 记录；无法追溯 provider/model/channel/route_hash、capability_evidence_id、recipe_hash、prompt_sha256、reference_bundle_sha256、backend_version、quality_tier、actual_image_inputs 和 seed 是否真实生效。

## 验收总账

| 集 | 状态 | 实体数 | block | high | medium | 重点实体 |
|---|---|---:|---:|---:|---:|---|
| 第1集 | blocked | 31 | 5 | 0 | 34 | 武松(block)；武大(block)；潘金莲(block) |
