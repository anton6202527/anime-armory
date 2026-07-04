# n2d 生产数据仪表盘

- 生成时间：2026-07-04T03:02:19+00:00
- 事件日志：`/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/production_events.jsonl`
- 投放数据：`未发现 platform_metrics.*`

## 总览

| 集数 | 事件数 | 成本 | 耗时 | 生成次数 | 重抽 | QA阻断 | QA警告 | 生成通过率 | 可交付通过率 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 10 | 931 | credits 2436.00 | 14h53m30s | 200 | 13 | 271 | 372 | 96.0% | 0.0% |

## ROI

| 成片分钟 | 每分钟成本 | 每集耗时 | 一次通过率 | 重抽率 | 投放播放 | 投放收入 | 投放成本 | 净回收 | 回收/生产成本 |
|---:|---|---:|---:|---:|---:|---|---|---|---:|
| 3m54s | credits 625.30/min | 14h53m30s | 92.5% | 6.5% | 0 | — | — | — | — |

## Gate 噪声

| warn/生成 | block/生成 | 误报回收 | 误报回收率 |
|---:|---:|---:|---:|
| 1.86 | 1.355 | 0 | 0.0% |

## 行业基准对照（只读 · 非闸门 · 采集 2026-06-25）

> 厂商宣传口径、会过期，只作并排参照线，不参与告警/阻断。可在 `_设置.md`（`基准一次通过率`/`基准重抽率`）或 `生产数据/industry_benchmark.json` 覆盖；以一次 `n2d-review` 流程自审复核为准。

| 指标 | 本作实测 | 行业基准 | 对照 |
|---|---:|---:|:---:|
| 一次通过率 | 92.5% | 90.0% | ✅ 达标 |
| 重抽率 | 6.5% | 10.0% | ✅ 达标 |
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
| 第1集 | 审查验收 | credits 2320.00 | credits 1155.04/min | 8h11m25s | 99.2% | 0.0% | — | 259 | — | — | — | — | — | — |
| 第2集 | 图生视频 | credits 116.00 | credits 61.47/min | 6h42m04s | 82.7% | 16.1% | 刀入身体部位不连续，需同一胸口入体点重抽×2；补录 provider；该旧图仍因刀入身体部位不连续被拒绝×2；face_reference_coverage face_verdict_noface；动作镜主检脸不可机检，归档重抽×1 | 12 | — | — | — | — | — | — |
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
| 脸漂/身份 (face_consistency) | 8 | 62% |
| 时序/接缝 (temporal) | 4 | 31% |
| 其他 (other) | 1 | 8% |
| **一致性小计**（脸漂/服装/场景/画风） | **8** | **62%** |

## 最新阻断

- 第1集 / image_preflight / 角色资产包: 创作区/制漫剧/那妖魔是姜大人/设定库/character_assets/CHAR_01__姜月初/prompts — 角色资产包分区不存在：prompts
- 第1集 / image_preflight / 角色资产包: 创作区/制漫剧/那妖魔是姜大人/设定库/character_assets/CHAR_01__姜月初/lora — 角色资产包分区不存在：lora
- 第1集 / image_preflight / 角色资产包: 创作区/制漫剧/那妖魔是姜大人/设定库/character_assets/CHAR_01__姜月初/voice — 角色资产包分区不存在：voice
- 第1集 / image_preflight / 角色资产包: 创作区/制漫剧/那妖魔是姜大人/设定库/character_assets/CHAR_01__姜月初/adapters — 角色资产包分区不存在：adapters
- 第1集 / image_preflight / 角色资产包: 创作区/制漫剧/那妖魔是姜大人/设定库/character_assets/CHAR_01__姜月初/qc — 角色资产包分区不存在：qc
- 第1集 / image_preflight / 角色资产包: 创作区/制漫剧/那妖魔是姜大人/设定库/character_assets/CHAR_02__裴长青/reference — 角色资产包分区不存在：reference
- 第1集 / image_preflight / 角色资产包: 创作区/制漫剧/那妖魔是姜大人/设定库/character_assets/CHAR_02__裴长青/prompts — 角色资产包分区不存在：prompts
- 第1集 / image_preflight / 角色资产包: 创作区/制漫剧/那妖魔是姜大人/设定库/character_assets/CHAR_02__裴长青/lora — 角色资产包分区不存在：lora
- 第2集 / image / temporal_continuity: 出图/第2集/图片/Clip01_first.png|出图/第2集/图片/Clip01_mid.png — Clip01 first/mid 同一把横刀入裴长青胸口的入体点不连续，疑似多刀/跳伤口；判定重抽 Clip01 全组三帧。
- 第2集 / image / face_reference_coverage: 出图/第2集/图片/Clip04_mid.png — Clip04_mid 动作中段主检角色脸部不可被 full image_qc 抓取（face_verdict_noface）；不得签过，需归档重抽并保持动作轴线/横刀/虎妖比例。
- 第2集 / image / anatomy_continuity: 出图/第2集/图片/Clip05_end.png — Clip05_end 女主出现额外/镜像右手，卷轴触碰手与扶剑手的左右手和手臂归属不成立；不得签过，需归档重抽并固化手部/肢体归属铁律。
- 第2集 / video / 后端跨集锁: 创作区/制漫剧/那妖魔是姜大人/设定库/model_routes_baseline.json — 第2集 含高风险/含角色路由（Clip_01、Clip_02、Clip_03、Clip_04、Clip_05、Clip_06）但缺 `设定库/model_routes_baseline.json`。第2集起必须先用打样集 `n2d-model-router --write-baseline` 建立 shot_type→primary 后端基线，否则跨集自然路由可能换后端导致脸质感、运动质感和画风漂移。
- 第2集 / video / 生视频后端适配: 创作区/制漫剧/那妖魔是姜大人/出视频/第2集/prompt/video_model_routes.json — 生视频后端「seedance」（渠道 Dreamina，执行后端 dreamina）缺少本次官方 API/CLI 刷新证据：refresh evidence is 1 day(s) old。正式付费出视频前必须实时查官方文档/本机 CLI 或 API help，确认单 Clip 上限、首尾/多帧能力、原生音画/口型、身份绑定、分辨率/价格/额度和输出 schema，再记录刷新证据：`python3 skills/n2d/_lib/video_backend_adapter.py record-refresh <作品根> --backend "seedance" --channel "Dreamina" --source "<官方文档或CLI/API证据>" --note "<本次能力结论>"`。证据文件：创作区/制漫剧/那妖魔是姜大人/生产数据/video_backend_capabilities/seedance__via_dreamina.json。未刷新不得开跑，避免旧 API 或能力误判造成整集返工。
- 第2集 / video / 生视频后端适配: 创作区/制漫剧/那妖魔是姜大人/出视频/第2集/prompt/video_model_routes.json — 生视频后端「dreamina」（渠道 Dreamina，执行后端 dreamina）缺少本次官方 API/CLI 刷新证据：refresh evidence is 1 day(s) old。正式付费出视频前必须实时查官方文档/本机 CLI 或 API help，确认单 Clip 上限、首尾/多帧能力、原生音画/口型、身份绑定、分辨率/价格/额度和输出 schema，再记录刷新证据：`python3 skills/n2d/_lib/video_backend_adapter.py record-refresh <作品根> --backend "dreamina" --channel "Dreamina" --source "<官方文档或CLI/API证据>" --note "<本次能力结论>"`。证据文件：创作区/制漫剧/那妖魔是姜大人/生产数据/video_backend_capabilities/dreamina__via_dreamina.json。未刷新不得开跑，避免旧 API 或能力误判造成整集返工。
- 第2集 / video / 强配方Schema(RCP2): 生产数据/production_events.jsonl — [production一致性升级:重复同维度] 脚本/第2集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_version, qc_version, backend_version/model_version, seed_effective_or_unsupported；recipe_hash 已有但还不能完整复现/归因。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第2集.json 的 accepted 后复跑；finding_hash=95d678c0acae，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第2集 / video / 强配方Schema(RCP2): 生产数据/production_events.jsonl — [production一致性升级:重复同维度] 合成/第2集/配音/voice_zh.wav 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_version, qc_version, backend_version/model_version, seed_effective_or_unsupported；recipe_hash 已有但还不能完整复现/归因。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第2集.json 的 accepted 后复跑；finding_hash=3c31fc18c5bb，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。

## 验收总账

| 集 | 状态 | 实体数 | block | high | medium | 重点实体 |
|---|---|---:|---:|---:|---:|---|
| 第1集 | blocked | 7 | 7 | 0 | 8 | 虎山神 / 虎妖(block)；姜月初(medium)；裴长青(medium) |
| 第2集 | blocked | 10 | 3 | 0 | 15 | 姜月初(medium)；裴长青(medium)；虎山神 / 虎妖(medium) |
