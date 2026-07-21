# n2d 生产数据仪表盘

- 生成时间：2026-07-20T13:33:12+00:00
- 事件日志：`/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/production_events.jsonl`
- 投放数据：`未发现 platform_metrics.*`

## 总览

| 集数 | 事件数 | 成本 | 耗时 | 生成次数 | 重抽 | QA阻断 | QA警告 | 生成通过率 | 可交付通过率 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 2 | 333 | — | 5h47m30s | 140 | 19 | 17 | 117 | 75.7% | 0.0% |

## ROI

| 成片分钟 | 每分钟成本 | 每集耗时 | 一次通过率 | 重抽率 | 投放播放 | 投放收入 | 投放成本 | 净回收 | 回收/生产成本 |
|---:|---|---:|---:|---:|---:|---|---|---|---:|
| 50s | — | 5h47m30s | 43.6% | 13.6% | 0 | — | — | — | — |

## Gate 噪声

| warn/生成 | block/生成 | 误报回收 | 误报回收率 |
|---:|---:|---:|---:|
| 0.8357 | 0.1214 | 0 | 0.0% |

## 行业基准对照（只读 · 非闸门 · 采集 2026-06-25）

> 厂商宣传口径、会过期，只作并排参照线，不参与告警/阻断。可在 `_设置.md`（`基准一次通过率`/`基准重抽率`）或 `生产数据/industry_benchmark.json` 覆盖；以一次 `n2d-review` 流程自审复核为准。

| 指标 | 本作实测 | 行业基准 | 对照 |
|---|---:|---:|:---:|
| 一次通过率 | 43.6% | 90.0% | ⚠️ 差距 |
| 重抽率 | 13.6% | 10.0% | ⚠️ 差距 |
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
| 第1集 | 出图 | — | — | 5h47m30s | 43.6% | 13.6% | dreamina-第1集 Dreamina image2image 真实参考图重出 Clip_06_first×4；dreamina-第1集 Dreamina image2image 真实参考图重出 Clip_05_first×3；dreamina-第1集 Dreamina image2image 真实参考图重出 Clip_05_a1×3 | 17 | — | — | — | — | — | — |
| 全剧 | — | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |

## 重抽原因分维度

| 维度 | 次数 | 占比 |
|---|---:|---:|
| 后端/管线迁移 (backend_migration) | 19 | 100% |
| **一致性小计**（脸漂/服装/场景/画风） | **0** | **0%** |

## 最新阻断

- 第1集 / image / 关键镜候选: 创作区/制漫剧/仙界闭关小能手/生产数据/candidate_selection_第1集.json — 关键镜 best-of-N 未闭环：缺选片行 EP01_CLIP01、EP01_CLIP02、EP01_CLIP04、EP01_CLIP07。补候选、重跑 candidate_select.py，直到每个关键镜都有 K>=3 的终选或明确重抽处方。
- 第1集 / image / 节奏密度(Rhythm): 脚本/第1集/storyboard.json — [production一致性升级:重复同维度] 节奏/留存 advisory 总分偏低：62.6。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=570e538a85f9，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第1集 / image / 节奏密度(Rhythm): 脚本/第1集/storyboard.json — [production一致性升级:重复同维度] 连续 4 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04），疑节奏塌·掉留存。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=5e14896904e8，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第1集 / image / 节奏密度(Rhythm): 脚本/第1集/storyboard.json — [production一致性升级:重复同维度] 开场镜未见冷开场/钩子标注（rhythm/label=『铺垫·长镜 低梁下的羞辱』），疑慢热；开场镜时长 6.2s > 5s，前3秒易掉留存。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=a78143b8d487，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第1集 / image / 音乐母题(LM1): 设定库/leitmotif_registry.json — [production一致性升级:关键场景] 本集有配乐/多角色但缺 设定库/leitmotif_registry.json——建议像 voice_key 一样为主要角色/情绪主题登记主题动机（subject→motif），保证跨集 BGM 母题可复现不串用。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=9b41af5cf013，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。

## 验收总账

| 集 | 状态 | 实体数 | block | high | medium | 重点实体 |
|---|---|---:|---:|---:|---:|---|
| 第1集 | blocked | 12 | 6 | 0 | 14 | 贺平生(block)；张老大(medium)；杂役背景组(warn) |
