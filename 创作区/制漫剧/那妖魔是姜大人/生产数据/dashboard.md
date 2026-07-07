# n2d 生产数据仪表盘

- 生成时间：2026-07-07T06:39:20+00:00
- 事件日志：`创作区/制漫剧/那妖魔是姜大人/生产数据/production_events.jsonl`
- 投放数据：`未发现 platform_metrics.*`

## 总览

| 集数 | 事件数 | 成本 | 耗时 | 生成次数 | 重抽 | QA阻断 | QA警告 | 生成通过率 | 可交付通过率 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 10 | 1615 | credits 3112.00 | 28h44m56s | 414 | 46 | 201 | 823 | 97.3% | 0.0% |

## ROI

| 成片分钟 | 每分钟成本 | 每集耗时 | 一次通过率 | 重抽率 | 投放播放 | 投放收入 | 投放成本 | 净回收 | 回收/生产成本 |
|---:|---|---:|---:|---:|---:|---|---|---|---:|
| 11m17s | credits 275.94/min | 28h44m56s | 95.2% | 11.1% | 0 | — | — | — | — |

## Gate 噪声

| warn/生成 | block/生成 | 误报回收 | 误报回收率 |
|---:|---:|---:|---:|
| 1.9879 | 0.4855 | 0 | 0.0% |

## 行业基准对照（只读 · 非闸门 · 采集 2026-06-25）

> 厂商宣传口径、会过期，只作并排参照线，不参与告警/阻断。可在 `_设置.md`（`基准一次通过率`/`基准重抽率`）或 `生产数据/industry_benchmark.json` 覆盖；以一次 `n2d-review` 流程自审复核为准。

| 指标 | 本作实测 | 行业基准 | 对照 |
|---|---:|---:|:---:|
| 一次通过率 | 95.2% | 90.0% | ✅ 达标 |
| 重抽率 | 11.1% | 10.0% | ⚠️ 差距 |
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
| 第1集 | 审查验收 | credits 2320.00 | credits 1155.04/min | 8h15m10s | 99.2% | 26.2% | legacy_multi_pass_selection_current_artifact_accepted×25；backend_migration_or_pipeline_upgrade_backfilled×8 | 30 | — | — | — | — | — | — |
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
- 第1集 / review / 证据等级: 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_findings_第1集.json — 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。交付边界不放行——在装好进阶依赖的环境复跑，或显式 N2D_ALLOW_DEGRADED_QC=1 自负其责。
- 第1集 / review / 现实覆盖: 生产数据/scene_embed_第1集.json — 场景语义嵌入(DINOv2) 适用却休眠：项目登记了它要查的数据，但交付前它没真跑（缺后端/sidecar）——「跑了数据却没执行一致性」正是这种休眠。装好后端真验，或显式 N2D_ALLOW_DEGRADED_QC=1 计债放行。跑 python3 skills/n2d-review/scripts/scene_embed.py "创作区/制漫剧/那妖魔是姜大人" 第1集 --write（需对应重型后端 env）
- 第1集 / review / 现实覆盖: 生产数据/resident_presence_第1集.json — 场景常驻陈设在场(OWLv2) 适用却休眠：项目登记了它要查的数据，但交付前它没真跑（缺后端/sidecar）——「跑了数据却没执行一致性」正是这种休眠。装好后端真验，或显式 N2D_ALLOW_DEGRADED_QC=1 计债放行。跑 python3 skills/n2d-review/scripts/resident_presence.py "创作区/制漫剧/那妖魔是姜大人" 第1集 --write（需对应重型后端 env）
- 第1集 / review / 验收总账: 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_ledger_第1集.json — 一致性验收总账未清零：block=4 high=0 medium=21。review 不再按单镜看着像放行；请按 consistency_ledger 的交付域/根因回源头修复后复跑。
- 第1集 / review / 进度凭据对账: 第1集/成片 — 进度「成片」标 ✅ 却无新鲜通过的闸门凭据（gate_failed）：闸门未过：compose 仍有 3 个 block 级问题（见 gate_findings_compose_第1集.json）。修掉 block 后重跑 → python3 skills/n2d-dashboard/scripts/dashboard.py gate "创作区/制漫剧/那妖魔是姜大人" 第1集 --stage compose（凡绕过 progress set 直接写 ✅ 都会在此被抓——重跑该阶段闸门盖新鲜凭据后再交付）
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
| 第1集 | blocked | 24 | 4 | 0 | 21 | 姜月初(medium)；陈青源(warn)；青面郎君(warn) |
| 第2集 | pass | 23 | 0 | 0 | 27 | 姜月初(medium)；陈青源(warn)；青面郎君(warn) |
| 第3集 | blocked | 23 | 6 | 0 | 17 | 姜月初(block)；陈青源(medium)；青面郎君(warn) |
| 第4集 | blocked | 23 | 7 | 0 | 19 | 姜月初(block)；镇魔司黑衣赤纹(block)；陈青源(medium) |
