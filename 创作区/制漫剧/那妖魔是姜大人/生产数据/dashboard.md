# n2d 生产数据仪表盘

- 生成时间：2026-07-21T12:32:53+00:00
- 事件日志：`创作区/制漫剧/那妖魔是姜大人/生产数据/production_events.jsonl`
- 投放数据：`未发现 platform_metrics.*`

## 总览

| 集数 | 事件数 | 成本 | 耗时 | 生成次数 | 重抽 | QA阻断 | QA警告 | 生成通过率 | 可交付通过率 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 10 | 16 | — | 15m00s | 1 | 0 | 5 | 6 | 100.0% | 0.0% |

## ROI

| 成片分钟 | 每分钟成本 | 每集耗时 | 一次通过率 | 重抽率 | 投放播放 | 投放收入 | 投放成本 | 净回收 | 回收/生产成本 |
|---:|---|---:|---:|---:|---:|---|---|---|---:|
| 1m15s | — | 15m00s | 100.0% | 0.0% | 0 | — | — | — | — |

## Gate 噪声

| warn/生成 | block/生成 | 误报回收 | 误报回收率 |
|---:|---:|---:|---:|
| 6.0 | 5.0 | 0 | 0.0% |

## 行业基准对照（只读 · 非闸门 · 采集 2026-06-25）

> 厂商宣传口径、会过期，只作并排参照线，不参与告警/阻断。可在 `_设置.md`（`基准一次通过率`/`基准重抽率`）或 `生产数据/industry_benchmark.json` 覆盖；以一次 `n2d-review` 流程自审复核为准。

| 指标 | 本作实测 | 行业基准 | 对照 |
|---|---:|---:|:---:|
| 一次通过率 | 100.0% | 90.0% | ✅ 达标 |
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
| 第1集 | 出图prompt | — | — | 15m00s | 100.0% | 0.0% | — | 5 | — | — | — | — | — | — |
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

- 第1集 / image_prompt_preflight / 空间硬控: 创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#6 — 该 fight_exchange 模板具有 pose_reference_required: true 约束，必须配置 pose_image_path。
- 第1集 / image_prompt_preflight / 实体排程: 创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#8 — 同一实体同时被登记为可见/必须出现和 offscreen_presence：VFX_百妖谱。画外保留只能用于不清晰入画的声音、影子、手部/物件/反应承接；请拆清楚可见槽位与画外槽位。
- 第1集 / image_prompt_preflight / 持有账本(POS): 创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json — storyboard 已出现核心道具/武器/证物/法宝的持有、交接、丢失或拾取（EP01_CLIP03:PROP_断刀/PROP_横刀/PROP_翻覆囚车、EP01_CLIP04:PROP_断刀/PROP_横刀、EP01_CLIP05:PROP_横刀、EP01_CLIP08:PROP_横刀），但缺 possession_ledger；请先在 创作区/制漫剧/那妖魔是姜大人/生产数据/possession_ledger_第1集.json 记录 clip、asset、holder、action，避免道具跨镜瞬移。
- 第1集 / image_prompt_preflight / P-3制片交接包: 创作区/制漫剧/那妖魔是姜大人/生产数据/production_breakdown_check_第1集.json — P-3 制片交接包未通过：1/9 confirmed。进入出图/视频前必须补齐并确认 continuity_chain.json、continuity_bible.json、ai_shooting_schedule.json、ai_call_sheet.md 等交接文件；问题示例：脚本/第1集/production_breakdown.json: status 不是 confirmed；脚本/第1集/continuity_breakdown.json: status 不是 confirmed；脚本/第1集/continuity_chain.json: status 不是 confirmed；脚本/第1集/continuity_bible.json: status 不是 confirmed；脚本/第1集/ai_shooting_schedule.json: status 不是 confirmed；脚本/第1集/ai_call_sheet.md: 缺 status: confirmed / 状态: confirmed。统一修复入口：`python3 skills/n2d/scripts/repair_preflight.py "创作区/制漫剧/那妖魔是姜大人" 第1集 --stage image_prompt_preflight --write-missing`。
- 第1集 / image_prompt_preflight / 物料新鲜度: 第1集 — 前期物料可能已过期：n2d-image, n2d-voice 自上次 skill 基线后有改动，可能影响本阶段（image_prompt）的输入物料。出图/出视频是花钱且不可逆的步骤——先跑 `python3 skills/n2d-update/scripts/update_plan.py check "创作区/制漫剧/那妖魔是姜大人" 第1集` 评估哪些物料需重制；统一修复/预检入口：`python3 skills/n2d/scripts/repair_preflight.py "创作区/制漫剧/那妖魔是姜大人" 第1集 --stage image_prompt --write-missing`。完成重制或确认接受现状后再 `python3 skills/n2d-update/scripts/update_plan.py record "创作区/制漫剧/那妖魔是姜大人" 第1集` 固化新基线。（注：当前基线为自动建立的临时 bootstrap，看不到更早 skill 版本的差异；确认现有产物可接受后请 `record` 固化）
