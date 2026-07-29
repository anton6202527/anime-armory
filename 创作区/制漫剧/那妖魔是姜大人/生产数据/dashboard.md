# n2d 生产数据仪表盘

- 生成时间：2026-07-29T12:43:12+00:00
- 事件日志：`创作区/制漫剧/那妖魔是姜大人/生产数据/production_events.jsonl`
- 投放数据：`未发现 platform_metrics.*`

## 总览

| 集数 | 事件数 | 成本 | 耗时 | 生成次数 | 重抽 | QA阻断 | QA警告 | 生成通过率 | 可交付通过率 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 10 | 1747 | credits 3872.00 | 17h14m43s | 577 | 76 | 351 | 662 | 92.3% | 0.0% |

## ROI

| 成片分钟 | 每分钟成本 | 每集耗时 | 一次通过率 | 重抽率 | 投放播放 | 投放收入 | 投放成本 | 净回收 | 回收/生产成本 |
|---:|---|---:|---:|---:|---:|---|---|---|---:|
| 3m58s | credits 975.07/min | 17h14m43s | 57.4% | 13.2% | 0 | — | — | — | — |

## Gate 噪声

| warn/生成 | block/生成 | 误报回收 | 误报回收率 |
|---:|---:|---:|---:|
| 1.1473 | 0.6083 | 0 | 0.0% |

## 行业基准对照（只读 · 非闸门 · 采集 2026-06-25）

> 厂商宣传口径、会过期，只作并排参照线，不参与告警/阻断。可在 `_设置.md`（`基准一次通过率`/`基准重抽率`）或 `生产数据/industry_benchmark.json` 覆盖；以一次 `n2d-review` 流程自审复核为准。

| 指标 | 本作实测 | 行业基准 | 对照 |
|---|---:|---:|:---:|
| 一次通过率 | 57.4% | 90.0% | ⚠️ 差距 |
| 重抽率 | 13.2% | 10.0% | ⚠️ 差距 |
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
| 第1集 | ✅视频已完成（默认收尾） | credits 1624.00 | credits 1257.29/min | 3h13m44s | 39.9% | 26.1% | 配方 schema 补全（像素未改）×11；配方 provider 补全（像素未改）×11；刀刃误指颈部，精确下移至胸骨前且未接触×1 | 165 | — | — | — | — | — | — |
| 第2集 | ✅视频已完成（默认收尾） | credits 2248.00 | credits 1875.23/min | 6h20m21s | 72.6% | 1.5% | 用户明确拒绝旧像素：姜月初换脸；以脸锚+45度+全身+场景+墨虎卷轴五张精确参考重抽。×1；旧 a1 换脸；从当前已验收 start 单向派生，只推进视线和纸上墨虎眼光。×1；尾帧候选身份基本可辨，但违背剧本硬事实：纸上墨虎应双眼短亮，候选侧头只能看到单眼；不晋升。×1 | 150 | — | — | — | — | — | — |
| 第3集 | 图生视频 | — | — | 7h40m39s | 33.3% | 32.3% | 补录当前像素的完整强配方 schema 与不可用 seed 降级证据；像素不变。×8；补齐正式媒体生成证据必填字段；当前像素不变。×5；补齐正式媒体实际图像输入清单；当前像素不变。×5 | 36 | — | — | — | — | — | — |
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
| 其他 (other) | 51 | 67% |
| 时序/接缝 (temporal) | 8 | 11% |
| 道具/特效 (prop_structure) | 7 | 9% |
| 脸漂/身份 (face_consistency) | 5 | 7% |
| 参考图裁切 (reference_crop) | 4 | 5% |
| 服装/配色 (outfit_consistency) | 1 | 1% |
| **一致性小计**（脸漂/服装/场景/画风） | **6** | **8%** |

## 最新阻断

- 第1集 / image_prompt_preflight / P-3制片交接包: 创作区/制漫剧/那妖魔是姜大人/生产数据/production_breakdown_check_第1集.json — P-3 制片交接包未通过：7/9 confirmed。进入出图/视频前必须补齐并确认 continuity_chain.json、continuity_bible.json、ai_shooting_schedule.json、ai_call_sheet.md 等交接文件；问题示例：脚本/第1集/production_handoff_pack.json: inputs_fingerprint 已过期，上游输入变更后需重新确认 P-3 handoff；脚本/第1集/production_handoff_signoff.json: input_fingerprint 缺失或过期；上游输入变化后必须重新签收；approval[user:wesley:producer] 未绑定当前 input_fingerprint；缺 handoff 审批；允许角色：assistant_director, producer, script_supervisor。统一修复入口：`python3 skills/n2d/scripts/repair_preflight.py "创作区/制漫剧/那妖魔是姜大人" 第1集 --stage image_prompt_preflight --write-missing`。
- 第1集 / image / 出图落档QC: 创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/image_qc_第1集.json — 输入首帧 image_qc 的 `inputs_fingerprint` 与当前文件失配（prompt、registry 或 PNG 已变）。当前结论作废；出视频前先重跑 image_qc。
- 第1集 / image / 发型(H1): 出图/第1集/图片 — 一致性审计发现问题
- 第1集 / image / 发型(H1): 出图/第1集/图片 — 一致性审计发现问题
- 第1集 / image / 发型(H1): 出图/第1集/图片 — 一致性审计发现问题
- 第1集 / image / 发型(H1): 出图/第1集/图片 — 一致性审计发现问题
- 第1集 / image / 发型(H1): 出图/第1集/图片 — 一致性审计发现问题
- 第1集 / image / character_consistency: 图片/Clip01_end.png — 降级精度多人同框：图片/Clip01_end.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_01_compare.png
- 第2集 / image_prompt_preflight / 脸漂报告新鲜度: 第2集 — 脸漂实测报告内容级陈旧：历史集 ['第1集(指纹不符)'] 的当前 PNG 像素与报告记录的指纹不一致——图在报告生成后重出过，集级覆盖看着没问题、报告其实基于旧像素，measured-drift 环会误判『全绿』。重跑 `python3 skills/n2d-identity/scripts/identity.py <作品根> --write` 基于当前 PNG 重算后再出图。
- 第2集 / image_prompt_preflight / 空间硬控: 创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json clip#3 — 该 fight_exchange 模板具有 pose_reference_required: true 约束，必须配置 pose_image_path。
- 第2集 / image_prompt_preflight / 分区合成: 创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json clip#3 — 该 fight_exchange 模板具有 regional_construct_required: true 约束，检测到同框多角色，请在 execution_strategy / multi_subject_strategy / template_contract.execution_strategy 中明确保底合成策略以防串脸。
- 第2集 / image_prompt_preflight / 专项镜头模板: 创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json clip#8 — template=system_panel 的 template_contract 缺字段：growth_ref
- 第2集 / image_prompt_preflight / 专项镜头模板: 创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json clip#8 — template=system_panel 的 template_contract 缺字段：panel_tier
- 第2集 / image_prompt_preflight / 跨集承接合同: 创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json — 早期集必须显式写跨集承接合同，避免集与集之间像拼接短片：缺 previous_episode_pickup/opening_bridge：本集开头没有明示接住上一集问题、延迟兑现或切线理由。建议字段：series_handoff.previous_episode_pickup / opening_bridge / ending_throw / next_episode_receivable_hook。
- 第2集 / image_prompt_preflight / P-3制片交接包: 创作区/制漫剧/那妖魔是姜大人/生产数据/production_breakdown_check_第2集.json — P-3 制片交接包未通过：7/9 confirmed。进入出图/视频前必须补齐并确认 continuity_chain.json、continuity_bible.json、ai_shooting_schedule.json、ai_call_sheet.md 等交接文件；问题示例：脚本/第2集/production_handoff_pack.json: inputs_fingerprint 已过期，上游输入变更后需重新确认 P-3 handoff；脚本/第2集/production_handoff_signoff.json: input_fingerprint 缺失或过期；上游输入变化后必须重新签收；approval[user:wesley:producer] 未绑定当前 input_fingerprint；缺 handoff 审批；允许角色：assistant_director, producer, script_supervisor。统一修复入口：`python3 skills/n2d/scripts/repair_preflight.py "创作区/制漫剧/那妖魔是姜大人" 第2集 --stage image_prompt_preflight --write-missing`。
- 第2集 / image_prompt_preflight / 物料新鲜度: 第2集 — 前期物料可能已过期：n2d-image 自上次 skill 基线后有改动，可能影响本阶段（image_prompt）的输入物料。出图/出视频是花钱且不可逆的步骤——先跑 `python3 skills/n2d-update/scripts/update_plan.py check "创作区/制漫剧/那妖魔是姜大人" 第2集` 评估哪些物料需重制；统一修复/预检入口：`python3 skills/n2d/scripts/repair_preflight.py "创作区/制漫剧/那妖魔是姜大人" 第2集 --stage image_prompt --write-missing`。完成重制或确认接受现状后再 `python3 skills/n2d-update/scripts/update_plan.py record "创作区/制漫剧/那妖魔是姜大人" 第2集` 固化新基线。
- 第3集 / image_prompt_preflight / 脸漂实测: 姜月初（CHAR_01） — 上一集已实测脸漂漂移（既成事实非预测）：⛔ 上一集已实测跨集脸漂（已出现 block 级脸漂 3 镜（first=第2集））：本集出图前先处置（重出漂移集 / 升原生主体或 LoRA），别带病续出——这是既成事实不是预测。
- 第3集 / image_prompt_preflight / 表情一致性: 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json clip#3 — continuity.expression_span='小' 非法；必须是 微/中/大 之一。
- 第3集 / image_prompt_preflight / 实体排程: 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json clip#2 — 同一实体同时被登记为可见/必须出现和 offscreen_presence：CHAR_02。画外保留只能用于不清晰入画的声音、影子、手部/物件/反应承接；请拆清楚可见槽位与画外槽位。
- 第3集 / image_prompt_preflight / 实体排程: 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json clip#6 — 同一实体同时被登记为可见/必须出现和 offscreen_presence：GROUP_01。画外保留只能用于不清晰入画的声音、影子、手部/物件/反应承接；请拆清楚可见槽位与画外槽位。

## 验收总账

| 集 | 状态 | 实体数 | block | high | medium | 重点实体 |
|---|---|---:|---:|---:|---:|---|
| 第1集 | blocked | 9 | 12 | 0 | 5 | 姜月初(block)；尸骸荒野(block)；横刀(block) |
| 第2集 | blocked | 9 | 7 | 0 | 10 | 姜月初(block)；尸骸荒野(block)；裴长青(warn) |
| 第3集 | blocked | 10 | 6 | 0 | 11 | 姜月初(warn)；03(warn)；裴长青(warn) |
