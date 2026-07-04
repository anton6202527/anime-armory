# n2d 生产数据仪表盘

- 生成时间：2026-07-03T17:44:03+00:00
- 事件日志：`创作区/制漫剧/仙界闭关小能手/生产数据/production_events.jsonl`
- 投放数据：`未发现 platform_metrics.*`

## 总览

| 集数 | 事件数 | 成本 | 耗时 | 生成次数 | 重抽 | QA阻断 | QA警告 | 生成通过率 | 可交付通过率 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 10 | 1878 | credits 6268.00 | 19h52m22s | 385 | 58 | 317 | 1067 | 98.4% | 0.0% |

## ROI

| 成片分钟 | 每分钟成本 | 每集耗时 | 一次通过率 | 重抽率 | 投放播放 | 投放收入 | 投放成本 | 净回收 | 回收/生产成本 |
|---:|---|---:|---:|---:|---:|---|---|---|---:|
| 4m29s | credits 1396.85/min | 19h52m22s | 82.6% | 15.1% | 0 | — | — | — | — |

## Gate 噪声

| warn/生成 | block/生成 | 误报回收 | 误报回收率 |
|---:|---:|---:|---:|
| 2.7714 | 0.8234 | 0 | 0.0% |

## 行业基准对照（只读 · 非闸门 · 采集 2026-06-25）

> 厂商宣传口径、会过期，只作并排参照线，不参与告警/阻断。可在 `_设置.md`（`基准一次通过率`/`基准重抽率`）或 `生产数据/industry_benchmark.json` 覆盖；以一次 `n2d-review` 流程自审复核为准。

| 指标 | 本作实测 | 行业基准 | 对照 |
|---|---:|---:|:---:|
| 一次通过率 | 82.6% | 90.0% | ⚠️ 差距 |
| 重抽率 | 15.1% | 10.0% | ⚠️ 差距 |
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
| 第1集 | 审查验收 | credits 6268.00 | credits 2983.58/min | 14h09m47s | 95.3% | 1.5% | global color grade to clear S1 style cohesion block; no face patch/swap×2；deterministic global color grade to clear S1 style cohesion block; no face patch/swap×2 | 302 | — | — | — | — | — | — |
| 第2集 | 图生视频 | — | — | 5h42m35s | 50.5% | 49.5% | 002-image-rerun Codex image_generation 真实重出 Clip_16_end，禁止本地贴脸修复×2；002-image-rerun Codex image_generation 真实重出 Clip_01，禁止本地贴脸修复×1；002-image-rerun Codex image_generation 真实重出 Clip_01_end，禁止本地贴脸修复×1 | 15 | — | — | — | — | — | — |
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
| 脸漂/身份 (face_consistency) | 54 | 93% |
| 画风 (style_drift) | 4 | 7% |
| **一致性小计**（脸漂/服装/场景/画风） | **58** | **100%** |

## 最新阻断

- 第1集 / video / 视频语义一致(VSEM): 生产数据/video_semantic_consistency_第1集.json — DINOv2 whole-frame similarity is below the configured VSEM threshold.
- 第1集 / video / 视频语义一致(VSEM): 生产数据/video_semantic_consistency_第1集.json — DINOv2 whole-frame similarity is below the configured VSEM threshold.
- 第1集 / video / 节奏密度(Rhythm): 脚本/第1集/storyboard.json — [production一致性升级:重复同维度] 节奏/留存 advisory 总分偏低：67.8。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=6e58cc9e054c，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第1集 / video / 节奏密度(Rhythm): 脚本/第1集/storyboard.json — [production一致性升级:重复同维度] 连续 11 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10→EP01_CLIP11），疑节奏塌·掉留存。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=01e346aa30e7，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第1集 / video_preflight / 出图落档QC: 创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/image_qc_第1集.json — 输入首帧 image_qc 仍有 49 项硬阻断（崩脸/接缝断/降级精度近景/非法 CHAR）——图生视频会忠实把这些缺陷动起来，是最贵工位上的纯浪费。先回 n2d-image 修复并重跑 image_qc 再出视频。
- 第1集 / compose / 人物在场链: 创作区/制漫剧/仙界闭关小能手/脚本/第1集/storyboard.json clip#1→clip#2 — 连续接缝里实体从上一 Clip 消失但未解释出画/离场/反打/画外保留：CROWD_ZAYI。请在上一或下一 Clip 的 continuity.entry_exit/offscreen_presence 写清楚，或改为换场/空镜/时间跳跃接缝。
- 第1集 / compose / 人物在场链: 创作区/制漫剧/仙界闭关小能手/脚本/第1集/storyboard.json clip#5→clip#6 — 连续接缝里实体从上一 Clip 消失但未解释出画/离场/反打/画外保留：CHAR_ZHANG_LAODA。请在上一或下一 Clip 的 continuity.entry_exit/offscreen_presence 写清楚，或改为换场/空镜/时间跳跃接缝。
- 第1集 / compose / 人物在场链: 创作区/制漫剧/仙界闭关小能手/脚本/第1集/storyboard.json clip#5→clip#6 — 连续接缝里实体在下一 Clip 凭空出现但未解释入画/进场/现身：CROWD_ZAYI。请在 continuity.entry_exit 写入画动作，或用空镜/换场/时间跳跃隔开。
- 第2集 / video / 风格(S1): 出图/第2集/图片 — 一致性审计发现问题
- 第2集 / video / 风格(S1): 出图/第2集/图片 — 一致性审计发现问题
- 第2集 / video / 风格(S1): 出图/第2集/图片 — 一致性审计发现问题
- 第2集 / video / 强配方Schema(RCP2): 生产数据/production_events.jsonl — [production一致性升级:重复同维度] 脚本/第2集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_version, qc_version, backend_version/model_version, seed_effective_or_unsupported；recipe_hash 已有但还不能完整复现/归因。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第2集.json 的 accepted 后复跑；finding_hash=95d678c0acae，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第2集 / video / 强配方Schema(RCP2): 生产数据/production_events.jsonl — [production一致性升级:重复同维度] 合成/第2集/配音/voice_zh.wav 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_version, qc_version, backend_version/model_version, seed_effective_or_unsupported；recipe_hash 已有但还不能完整复现/归因。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第2集.json 的 accepted 后复跑；finding_hash=3c31fc18c5bb，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第2集 / video / 生成配方(RCP): 生产数据/production_events.jsonl — [production一致性升级:重复同维度] 脚本/第2集/voiceover.txt 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=88863180b1df2f34，但复跑审计证据不完整。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第2集.json 的 accepted 后复跑；finding_hash=9517906d5f39，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第2集 / video / 生成配方(RCP): 生产数据/production_events.jsonl — [production一致性升级:重复同维度] 合成/第2集/配音/voice_zh.wav 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=8a71a91fbbbc3a12，但复跑审计证据不完整。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第2集.json 的 accepted 后复跑；finding_hash=d9e3a43e2a7a，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第2集 / image / 出图落档QC: 创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/image_qc_第2集.json — 输入首帧 image_qc 仍有 1 项硬阻断（崩脸/人体解剖N5/接缝断/降级精度近景/非法 CHAR/缺高风险人体合约）——图生视频会忠实把这些缺陷动起来，是最贵工位上的纯浪费。先回 n2d-image 修复并重跑 image_qc 再出视频。

## 验收总账

| 集 | 状态 | 实体数 | block | high | medium | 重点实体 |
|---|---|---:|---:|---:|---:|---|
| 第1集 | blocked | 20 | 7 | 0 | 11 | 贺平生(block)；张老大(medium)；韩老三(medium) |
| 第2集 | blocked | 20 | 4 | 0 | 21 | 贺平生(medium)；张老大(medium)；韩老三(warn) |
