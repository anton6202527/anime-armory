# n2d 生产数据仪表盘

- 生成时间：2026-07-07T09:29:17+00:00
- 事件日志：`创作区/制漫剧/那妖魔是姜大人/生产数据/production_events.jsonl`
- 投放数据：`未发现 platform_metrics.*`

## 总览

| 集数 | 事件数 | 成本 | 耗时 | 生成次数 | 重抽 | QA阻断 | QA警告 | 生成通过率 | 可交付通过率 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 10 | 1622 | credits 3392.00 | 28h46m57s | 420 | 46 | 216 | 807 | 97.4% | 0.0% |

## ROI

| 成片分钟 | 每分钟成本 | 每集耗时 | 一次通过率 | 重抽率 | 投放播放 | 投放收入 | 投放成本 | 净回收 | 回收/生产成本 |
|---:|---|---:|---:|---:|---:|---|---|---|---:|
| 11m17s | credits 300.77/min | 28h46m57s | 94.8% | 10.9% | 0 | — | — | — | — |

## Gate 噪声

| warn/生成 | block/生成 | 误报回收 | 误报回收率 |
|---:|---:|---:|---:|
| 1.9214 | 0.5143 | 0 | 0.0% |

## 行业基准对照（只读 · 非闸门 · 采集 2026-06-25）

> 厂商宣传口径、会过期，只作并排参照线，不参与告警/阻断。可在 `_设置.md`（`基准一次通过率`/`基准重抽率`）或 `生产数据/industry_benchmark.json` 覆盖；以一次 `n2d-review` 流程自审复核为准。

| 指标 | 本作实测 | 行业基准 | 对照 |
|---|---:|---:|:---:|
| 一次通过率 | 94.8% | 90.0% | ✅ 达标 |
| 重抽率 | 10.9% | 10.0% | ⚠️ 差距 |
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
| 第1集 | 审查验收 | credits 2600.00 | credits 1294.44/min | 8h17m12s | 97.7% | 25.0% | legacy_multi_pass_selection_current_artifact_accepted×25；backend_migration_or_pipeline_upgrade_backfilled×8 | 45 | — | — | — | — | — | — |
| 第2集 | ✅已验收 | credits 696.00 | credits 368.81/min | 6h47m35s | 84.9% | 13.1% | 刀入身体部位不连续，需同一胸口入体点重抽×2；补录 provider；该旧图仍因刀入身体部位不连续被拒绝×2；face_reference_coverage face_verdict_noface；动作镜主检脸不可机检，归档重抽×1 | 5 | — | — | — | — | — | — |
| 第3集 | 图生视频 | credits 96.00 | credits 28.27/min | 9h56m57s | 97.8% | 0.0% | — | 57 | — | — | — | — | — | — |
| 第4集 | 出图 | — | — | 3h45m13s | 98.1% | 0.0% | — | 109 | — | — | — | — | — | — |
| 第5集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第6集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第7集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第8集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第9集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第10集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |

## 重抽原因分维度

| 维度 | 次数 | 占比 |
|---|---:|---:|
| 其他 (other) | 34 | 74% |
| 脸漂/身份 (face_consistency) | 8 | 17% |
| 时序/接缝 (temporal) | 4 | 9% |
| **一致性小计**（脸漂/服装/场景/画风） | **8** | **17%** |

## 最新阻断

- 第1集 / compose / 证据等级: 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_findings_第1集.json — 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。交付边界不放行——在装好进阶依赖的环境复跑，或显式 N2D_ALLOW_DEGRADED_QC=1 自负其责。
- 第1集 / compose / 现实覆盖: 生产数据/scene_embed_第1集.json — 场景语义嵌入(DINOv2) 适用却休眠：项目登记了它要查的数据，但交付前它没真跑（缺后端/sidecar）——「跑了数据却没执行一致性」正是这种休眠。装好后端真验，或显式 N2D_ALLOW_DEGRADED_QC=1 计债放行。跑 python3 skills/n2d-review/scripts/scene_embed.py "创作区/制漫剧/那妖魔是姜大人" 第1集 --write（需对应重型后端 env）
- 第1集 / compose / 现实覆盖: 生产数据/resident_presence_第1集.json — 场景常驻陈设在场(OWLv2) 适用却休眠：项目登记了它要查的数据，但交付前它没真跑（缺后端/sidecar）——「跑了数据却没执行一致性」正是这种休眠。装好后端真验，或显式 N2D_ALLOW_DEGRADED_QC=1 计债放行。跑 python3 skills/n2d-review/scripts/resident_presence.py "创作区/制漫剧/那妖魔是姜大人" 第1集 --write（需对应重型后端 env）
- 第1集 / video_preflight / 中段锚帧: /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#6 — 锚帧 1 PNG 已存在但缺中段动作自检 pass 记账：出图/第1集/图片/Clip06_mid_reaction.png；落档后必须记录 image generation --status pass --meta self_check=pass，确认它不是只锁人锁景，而是姿态/动作确实落在首尾帧中间。
- 第1集 / video_preflight / 出图落档QC: /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/image_qc_第1集.json — 输入首帧晚于上次 image_qc（出图后改过帧未重验）——出视频前先重跑 image_qc，避免动画一张未验首帧。
- 第1集 / video_preflight / 后端跨集锁: /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出视频/第1集/prompt/video_model_routes.json — 1 个 clip 的 shot_type 自然路由与 设定库/model_routes_baseline 不符，已按基线锚定（原后端降 fallback）；高风险/含角色镜头的路由漂移必须写结构化 baseline_override（accepted/reviewer/reason/expires_at/affected_routes）或刷新基线后重跑。Clip_02(realm_portal):dreamina→seedance
- 第1集 / video_preflight / 生成配方证据: /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/production_events.jsonl — 出图/第1集/图片/Clip06_end_reaction.png 是本集最终媒体，但 production_events.jsonl 缺对应 image/video generation/redraw pass 记录；无法追溯 provider/model/channel/route_hash、capability_evidence_id、recipe_hash、prompt_sha256、reference_bundle_sha256、backend_version、quality_tier、actual_image_inputs 和 seed 是否真实生效。
- 第1集 / video_preflight / 生成配方证据: /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/production_events.jsonl — 出图/第1集/图片/Clip06_mid_reaction.png 是本集最终媒体，但 production_events.jsonl 缺对应 image/video generation/redraw pass 记录；无法追溯 provider/model/channel/route_hash、capability_evidence_id、recipe_hash、prompt_sha256、reference_bundle_sha256、backend_version、quality_tier、actual_image_inputs 和 seed 是否真实生效。
- 第2集 / image / temporal_continuity: 出图/第2集/图片/Clip01_first.png|出图/第2集/图片/Clip01_mid.png — Clip01 first/mid 同一把横刀入裴长青胸口的入体点不连续，疑似多刀/跳伤口；判定重抽 Clip01 全组三帧。
- 第2集 / image / face_reference_coverage: 出图/第2集/图片/Clip04_mid.png — Clip04_mid 动作中段主检角色脸部不可被 full image_qc 抓取（face_verdict_noface）；不得签过，需归档重抽并保持动作轴线/横刀/虎妖比例。
- 第2集 / image / anatomy_continuity: 出图/第2集/图片/Clip05_end.png — Clip05_end 女主出现额外/镜像右手，卷轴触碰手与扶剑手的左右手和手臂归属不成立；不得签过，需归档重抽并固化手部/肢体归属铁律。
- 第2集 / image / 产物存在性: 出图/第2集/图片/Clip03_mid.png — 最新 `image` pass 事件登记的产物不存在：出图/第2集/图片/Clip03_mid.png。事件账本不能替代当前文件存在性；重出或恢复该产物后再放行。
- 第2集 / image / 产物存在性: 出图/第2集/图片/Clip04_mid.png — 最新 `image` pass 事件登记的产物不存在：出图/第2集/图片/Clip04_mid.png。事件账本不能替代当前文件存在性；重出或恢复该产物后再放行。
- 第3集 / video_prompt_preflight / 尾帧: 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip01_end.png — need_endframe=true 但尾帧 PNG 不存在
- 第3集 / video_prompt_preflight / 中段锚帧: 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip01_first_a1.png — 声明了锚帧 1 但锚帧 PNG 不存在
- 第3集 / video_prompt_preflight / 中段锚帧: 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip01_first_a2.png — 声明了锚帧 2 但锚帧 PNG 不存在
- 第3集 / video_prompt_preflight / 中段锚帧: 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip01_first_a3.png — 声明了锚帧 3 但锚帧 PNG 不存在
- 第3集 / video_prompt_preflight / 尾帧: 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip02_end.png — need_endframe=true 但尾帧 PNG 不存在
- 第3集 / video_prompt_preflight / 中段锚帧: 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip02_mid.png — 声明了锚帧 1 但锚帧 PNG 不存在
- 第3集 / video_prompt_preflight / 尾帧: 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip03_end.png — need_endframe=true 但尾帧 PNG 不存在

## 验收总账

| 集 | 状态 | 实体数 | block | high | medium | 重点实体 |
|---|---|---:|---:|---:|---:|---|
| 第1集 | blocked | 24 | 5 | 0 | 19 | 姜月初(medium)；陈青源(warn)；青面郎君(warn) |
| 第2集 | pass | 23 | 0 | 0 | 27 | 姜月初(medium)；陈青源(warn)；青面郎君(warn) |
| 第3集 | blocked | 23 | 6 | 0 | 17 | 姜月初(block)；陈青源(medium)；青面郎君(warn) |
| 第4集 | blocked | 23 | 7 | 0 | 19 | 姜月初(block)；镇魔司黑衣赤纹(block)；陈青源(medium) |
