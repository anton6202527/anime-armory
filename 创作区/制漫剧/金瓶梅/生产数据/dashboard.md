# n2d 生产数据仪表盘

- 生成时间：2026-08-18T09:55:48+00:00
- 事件日志：`创作区/制漫剧/金瓶梅/生产数据/production_events.jsonl`
- 投放数据：`未发现 platform_metrics.*`

## 总览

| 集数 | 事件数 | 成本 | 耗时 | 生成次数 | 重抽 | QA阻断 | QA警告 | 生成通过率 | 可交付通过率 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 10 | 654 | — | 8h34m55s | 347 | 0 | 13 | 199 | 84.7% | 0.0% |

## ROI

| 成片分钟 | 每分钟成本 | 每集耗时 | 一次通过率 | 重抽率 | 投放播放 | 投放收入 | 投放成本 | 净回收 | 回收/生产成本 |
|---:|---|---:|---:|---:|---:|---|---|---|---:|
| 2m26s | — | 8h34m55s | 49.3% | 0.0% | 0 | — | — | — | — |

## Gate 噪声

| warn/生成 | block/生成 | 误报回收 | 误报回收率 |
|---:|---:|---:|---:|
| 0.5735 | 0.0375 | 0 | 0.0% |

## 行业基准对照（只读 · 非闸门 · 采集 2026-06-25）

> 厂商宣传口径、会过期，只作并排参照线，不参与告警/阻断。可在 `_设置.md`（`基准一次通过率`/`基准重抽率`）或 `生产数据/industry_benchmark.json` 覆盖；以一次 `n2d-review` 流程自审复核为准。

| 指标 | 本作实测 | 行业基准 | 对照 |
|---|---:|---:|:---:|
| 一次通过率 | 49.3% | 90.0% | ⚠️ 差距 |
| 重抽率 | 0.0% | 10.0% | ✅ 达标 |
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
| 第1集 | 出图 | — | — | 8h34m55s | 49.3% | 0.0% | — | 13 | — | — | — | — | — | — |
| 第2集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第3集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第4集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第5集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第6集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第7集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第8集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第9集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第10集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |

## 最新阻断

- 第1集 / image / 表情连续(EXP1): 脚本/第1集/storyboard.json — [production一致性升级:重复同维度] Clip_09：角色 CHAR_WUSONG 相邻镜情绪硬跳（喜→怒/悲/惊）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=9477f3aefd25，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第1集 / image / 表情连续(EXP1): 脚本/第1集/storyboard.json — [production一致性升级:重复同维度] Clip_09：角色 CHAR_PANJINLIAN 相邻镜情绪硬跳（喜→怒/悲/惊）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=ff50f685763a，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第1集 / image / 表情连续(EXP1): 脚本/第1集/storyboard.json — [production一致性升级:重复同维度] Clip_15：角色 CHAR_WUSONG 相邻镜情绪硬跳（悲→怒）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=8ff00690254d，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第1集 / image / 表情连续(EXP1): 脚本/第1集/storyboard.json — [production一致性升级:重复同维度] Clip_15：角色 CHAR_PANJINLIAN 相邻镜情绪硬跳（悲→怒）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=07749aa2fd1a，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第1集 / image / 节奏密度(Rhythm): 脚本/第1集/storyboard.json — [production一致性升级:关键场景] 连续 10 个长镜聚集（EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10→EP01_CLIP11），疑节奏塌·掉留存。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=4b0a014fd90b，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第1集 / image / 音乐母题(LM1): 设定库/leitmotif_registry.json — [production一致性升级:重复同维度] 音乐母题 MOTIF_WUSONG 缺 file/audio/clip；生成式 BGM 只写描述无法保证跨集复现。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=7a12f8043531，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第1集 / image / 音乐母题(LM1): 设定库/leitmotif_registry.json — [production一致性升级:重复同维度] 音乐母题 MOTIF_WUSONG 缺 audio_sha256/hash/cue；无法确认 compose 复用的是同一段动机。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=12e6ac717039，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 第1集 / image / 音乐母题(LM1): 设定库/leitmotif_registry.json — [production一致性升级:重复同维度] 音乐母题 MOTIF_JINLIAN 缺 file/audio/clip；生成式 BGM 只写描述无法保证跨集复现。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=bb63aaa5c68e，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。

## 验收总账

| 集 | 状态 | 实体数 | block | high | medium | 重点实体 |
|---|---|---:|---:|---:|---:|---|
| 第1集 | blocked | 31 | 5 | 0 | 34 | 武松(medium)；BEAST_TIGER(warn)；Hunters(warn) |
