# n2d 生产数据仪表盘

- 生成时间：2026-07-09T12:22:37+00:00
- 事件日志：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/production_events.jsonl`
- 投放数据：`未发现 platform_metrics.*`

## 总览

| 集数 | 事件数 | 成本 | 耗时 | 生成次数 | 重抽 | QA阻断 | QA警告 | 生成通过率 | 可交付通过率 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 10 | 1702 | credits 3462.00 | 35h15m56s | 483 | 51 | 143 | 878 | 97.3% | 0.0% |

## ROI

| 成片分钟 | 每分钟成本 | 每集耗时 | 一次通过率 | 重抽率 | 投放播放 | 投放收入 | 投放成本 | 净回收 | 回收/生产成本 |
|---:|---|---:|---:|---:|---:|---|---|---|---:|
| 13m49s | credits 250.55/min | 35h15m56s | 94.2% | 10.6% | 0 | — | — | — | — |

## Gate 噪声

| warn/生成 | block/生成 | 误报回收 | 误报回收率 |
|---:|---:|---:|---:|
| 1.8178 | 0.2961 | 0 | 0.0% |

## 行业基准对照（只读 · 非闸门 · 采集 2026-06-25）

> 厂商宣传口径、会过期，只作并排参照线，不参与告警/阻断。可在 `_设置.md`（`基准一次通过率`/`基准重抽率`）或 `生产数据/industry_benchmark.json` 覆盖；以一次 `n2d-review` 流程自审复核为准。

| 指标 | 本作实测 | 行业基准 | 对照 |
|---|---:|---:|:---:|
| 一次通过率 | 94.2% | 90.0% | ✅ 达标 |
| 重抽率 | 10.6% | 10.0% | ⚠️ 差距 |
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
| 第1集 | ✅已验收 | credits 2600.00 | credits 1294.44/min | 8h22m09s | 95.0% | 27.3% | legacy_multi_pass_selection_current_artifact_accepted×25；backend_migration_or_pipeline_upgrade_backfilled×8；faceless_reaction_anchor_derivative_for_clip06_face_drift_fix×4 | 22 | — | — | — | — | — | — |
| 第2集 | ✅已验收 | credits 696.00 | credits 368.81/min | 6h47m35s | 84.9% | 13.1% | 刀入身体部位不连续，需同一胸口入体点重抽×2；补录 provider；该旧图仍因刀入身体部位不连续被拒绝×2；face_reference_coverage face_verdict_noface；动作镜主检脸不可机检，归档重抽×1 | 5 | — | — | — | — | — | — |
| 第3集 | 图生视频 | credits 166.00 | credits 48.88/min | 9h57m01s | 97.8% | 0.0% | — | 52 | — | — | — | — | — | — |
| 第4集 | 视频prompt | — | — | 5h35m19s | 98.5% | 0.0% | — | 46 | — | — | — | — | — | — |
| 第5集 | 出图 | — | — | 4h33m51s | 95.2% | 0.0% | — | 18 | — | — | — | — | — | — |
| 第6集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第7集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第8集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第9集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第10集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |

## 重抽原因分维度

| 维度 | 次数 | 占比 |
|---|---:|---:|
| 其他 (other) | 24 | 47% |
| 后端/管线迁移 (backend_migration) | 11 | 22% |
| 脸漂/身份 (face_consistency) | 8 | 16% |
| 参考图裁切 (reference_crop) | 4 | 8% |
| 时序/接缝 (temporal) | 4 | 8% |
| **一致性小计**（脸漂/服装/场景/画风） | **8** | **16%** |

## 最新阻断

- 第1集 / image / 产物存在性: 出图/第1集/图片/Clip11_mid.png — 最新 `image` pass 事件登记的产物不存在：出图/第1集/图片/Clip11_mid.png。事件账本不能替代当前文件存在性；重出或恢复该产物后再放行。
- 第1集 / image / 产物存在性: 出图/第1集/图片/Clip11_end.png — 最新 `image` pass 事件登记的产物不存在：出图/第1集/图片/Clip11_end.png。事件账本不能替代当前文件存在性；重出或恢复该产物后再放行。
- 第1集 / video / 产物存在性: /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_02_看见虎妖尸身.mp4 — 最新 `video` pass 事件登记的产物不存在：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_02_看见虎妖尸身.mp4。事件账本不能替代当前文件存在性；重出或恢复该产物后再放行。
- 第1集 / video / 产物存在性: /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_03_镇魔司压迫交易.mp4 — 最新 `video` pass 事件登记的产物不存在：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_03_镇魔司压迫交易.mp4。事件账本不能替代当前文件存在性；重出或恢复该产物后再放行。
- 第1集 / video / 产物存在性: /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_06_裴长青最后一击被踹飞.mp4 — 最新 `video` pass 事件登记的产物不存在：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_06_裴长青最后一击被踹飞.mp4。事件账本不能替代当前文件存在性；重出或恢复该产物后再放行。
- 第1集 / video / 产物存在性: /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_05_虎妖诈死复苏.mp4 — 最新 `video` pass 事件登记的产物不存在：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_05_虎妖诈死复苏.mp4。事件账本不能替代当前文件存在性；重出或恢复该产物后再放行。
- 第1集 / video / 产物存在性: /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_07_百妖谱第一次开启.mp4 — 最新 `video` pass 事件登记的产物不存在：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_07_百妖谱第一次开启.mp4。事件账本不能替代当前文件存在性；重出或恢复该产物后再放行。
- 第1集 / video / 产物存在性: /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_01_死人堆惊醒.mp4 — 最新 `video` pass 事件登记的产物不存在：/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_01_死人堆惊醒.mp4。事件账本不能替代当前文件存在性；重出或恢复该产物后再放行。
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
| 第1集 | pass | 24 | 0 | 0 | 24 | 姜月初(medium)；陈青源(warn)；青面郎君(warn) |
| 第2集 | pass | 23 | 0 | 0 | 27 | 姜月初(medium)；陈青源(warn)；青面郎君(warn) |
| 第3集 | blocked | 24 | 4 | 0 | 18 | 姜月初(block)；陈青源(medium)；青面郎君(warn) |
| 第4集 | blocked | 24 | 3 | 0 | 22 | 姜月初(medium)；陈青源(medium)；GROUP_飞鹰门众人(warn) |
