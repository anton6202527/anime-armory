# n2d 生产数据仪表盘

- 生成时间：2026-07-03T15:06:58+00:00
- 事件日志：`/Users/lalala/learn/anime-armory/创作区/制漫剧/王敦传：开局九龙气运，我在灵药谷装管事/生产数据/production_events.jsonl`
- 投放数据：`未发现 platform_metrics.*`

## 总览

| 集数 | 事件数 | 成本 | 耗时 | 生成次数 | 重抽 | QA阻断 | QA警告 | 生成通过率 | 可交付通过率 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 10 | 389 | — | 35m01s | 21 | 2 | 56 | 292 | 95.2% | 0.0% |

## ROI

| 成片分钟 | 每分钟成本 | 每集耗时 | 一次通过率 | 重抽率 | 投放播放 | 投放收入 | 投放成本 | 净回收 | 回收/生产成本 |
|---:|---|---:|---:|---:|---:|---|---|---|---:|
| 3m37s | — | 35m01s | 90.5% | 9.5% | 0 | — | — | — | — |

## Gate 噪声

| warn/生成 | block/生成 | 误报回收 | 误报回收率 |
|---:|---:|---:|---:|
| 13.9048 | 2.6667 | 0 | 0.0% |

## 行业基准对照（只读 · 非闸门 · 采集 2026-06-25）

> 厂商宣传口径、会过期，只作并排参照线，不参与告警/阻断。可在 `_设置.md`（`基准一次通过率`/`基准重抽率`）或 `生产数据/industry_benchmark.json` 覆盖；以一次 `n2d-review` 流程自审复核为准。

| 指标 | 本作实测 | 行业基准 | 对照 |
|---|---:|---:|:---:|
| 一次通过率 | 90.5% | 90.0% | ✅ 达标 |
| 重抽率 | 9.5% | 10.0% | ✅ 达标 |
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
| 第1集 | 出图 | — | — | 35m01s | 90.5% | 9.5% | manual-第1集 Codex image_generation 真实重出 CHAR_XIAO_LIUZI::定妆_CHAR_XIAO_LIUZI__常态，禁止本地贴脸修复×2 | 56 | — | — | — | — | — | — |
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
| 脸漂/身份 (face_consistency) | 2 | 100% |
| **一致性小计**（脸漂/服装/场景/画风） | **2** | **100%** |

## 最新阻断

- 第1集 / image_preflight / 预防式合同: CHAR_HE_PINGSHENG — reference_slot_gate: 核心/出场角色 CHAR_HE_PINGSHENG 引用槽位未绑定真实产物：reference_slots 缺可解析的真实文件 path/hash
- 第1集 / image_preflight / 预防式合同: CHAR_JAILER_A — reference_slot_gate: 核心/出场角色 CHAR_JAILER_A 引用槽位未绑定真实产物：reference_slots 缺可解析的真实文件 path/hash
- 第1集 / image_preflight / 预防式合同: CHAR_JAILER_B — reference_slot_gate: 核心/出场角色 CHAR_JAILER_B 引用槽位未绑定真实产物：reference_slots 缺可解析的真实文件 path/hash
- 第1集 / image_preflight / 预防式合同: CHAR_PURSUER — reference_slot_gate: 核心/出场角色 CHAR_PURSUER 引用槽位未绑定真实产物：reference_slots 缺可解析的真实文件 path/hash
- 第1集 / image_preflight / 预防式合同: CHAR_WANG_DUN — reference_slot_gate: 核心/出场角色 CHAR_WANG_DUN 引用槽位未绑定真实产物：reference_slots 缺可解析的真实文件 path/hash
- 第1集 / image_preflight / 预防式合同: CHAR_XIAO_LIUZI — reference_slot_gate: 核心/出场角色 CHAR_XIAO_LIUZI 引用槽位未绑定真实产物：reference_slots 缺可解析的真实文件 path/hash
- 第1集 / image_preflight / 预防式合同: CROWD_VALLEY_WORKERS — reference_slot_gate: 核心/出场角色 CROWD_VALLEY_WORKERS 引用槽位未绑定真实产物：reference_slots 缺可解析的真实文件 path/hash
- 第1集 / image_preflight / 预防式合同: LOC_BLACK_RIVER_EXIT — reference_slot_gate: 道具/场景 LOC_BLACK_RIVER_EXIT 引用槽位未绑定真实产物：reference_slots 缺可解析的真实文件 path/hash
