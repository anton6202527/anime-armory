# n2d 生产数据仪表盘

- 生成时间：2026-06-29T09:40:02+00:00
- 事件日志：`/Users/wesley/learn/anime-arsenal/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/production_events.jsonl`
- 投放数据：`未发现 platform_metrics.*`

## 总览

| 集数 | 事件数 | 成本 | 耗时 | 生成次数 | 重抽 | QA阻断 | QA警告 | 生成通过率 | 可交付通过率 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 3 | 522 | — | 5h46m40s | 81 | 0 | 294 | 137 | 100.0% | 0.0% |

## ROI

| 成片分钟 | 每分钟成本 | 每集耗时 | 一次通过率 | 重抽率 | 投放播放 | 投放收入 | 投放成本 | 净回收 | 回收/生产成本 |
|---:|---|---:|---:|---:|---:|---|---|---|---:|
| 1m30s | — | 5h46m40s | 100.0% | 0.0% | 0 | — | — | — | — |

## Gate 噪声

| warn/生成 | block/生成 | 误报回收 | 误报回收率 |
|---:|---:|---:|---:|
| 1.6914 | 3.6296 | 0 | 0.0% |

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
| 第1集 | 出图 | — | — | 5h46m40s | 100.0% | 0.0% | — | 294 | — | — | — | — | — | — |
| 第2集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第3集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |

## 最新阻断

- 第1集 / image_preflight / 参考规划落实: 创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/reference_plan_第1集.json — 逐镜参考规划有 20 条行动项未确认落实（无持久主体 ID 后端×大变化镜 11 镜）：镜头 EP01_CLIP01、EP01_CLIP02、EP01_CLIP03、EP01_CLIP04、EP01_CLIP05、EP01_CLIP06、EP01_CLIP07、EP01_CLIP08…。请按 reference_plan_第1集.md 把补拍/多样参考/控制网/升档落进 出图/第1集/prompt/01_分镜出图.md 后再付费出图；不能让参考规划停在侧车文件里。若已完成人审落实，请写结构化 `生产数据/reference_plan_application_第1集.json`（kind=n2d_reference_plan_application, accepted=true, reviewer, plan_sha256, prompt_path, prompt_sha256, applied_action_count, applied_evidence）。当前落实证据状态：applied_action_count=11 少于待落实行动项 20。 建议升 LoRA：CHAR_JIANG_YUECHU/战场形态。
- 第1集 / image_preflight / 风格化脸机检: 创作区/制漫剧/从变身少女开始斩妖除魔/_设置.md — 基础视觉风格「冷灰写实3D国风漫剧」属于风格化/漫剧脸，当前脸一致性机检后端=arcface；建议项目级设置 `脸一致性机检后端: styleid` 并配置 N2D_STYLEID_MODEL。未配置前，角色脸一致性 KPI 按降级档处理，近景结果需提高人审权重。 当前已触发发布闸门（release standard (demo=production·B11)）：缺可用 N2D_STYLEID_MODEL 时不得进入正式投放/高近景角色镜。若确认接受降级，需写结构化 生产数据/styleid_release_signoff_第1集.json（kind=n2d_styleid_release_signoff, accepted=true, reviewer, reason, expires_at）后复跑。
- 第1集 / image_preflight / 资产身份注册层: 创作区/制漫剧/从变身少女开始斩妖除魔/出图/共享/identity_registry.json character#1 form#1 — reference_atlas.base_views 基础视角必须为 ready 且有路径：three_quarter, side, back, half_body；所有人物/形态都强制包含 45°/three_quarter 与脸部特写基础锚，不能登记为 planned 后放行。
- 第1集 / image_preflight / 资产身份注册层: 创作区/制漫剧/从变身少女开始斩妖除魔/出图/共享/identity_registry.json character#1 form#1 — reference_atlas 至少登记一个 ready 的同源脸部特写/表情参考（face_anchor_refs 或 expression_refs）；功能角色也不能只靠正脸硬扛近景，planned 脸锚不能放行。
- 第1集 / image_preflight / 资产身份注册层: 创作区/制漫剧/从变身少女开始斩妖除魔/出图/共享/identity_registry.json character#1 form#1 — three_quarter ready 拆分定妆必须是同源母本派生，登记 derivation.method/source_path/source_sha256/crop_box；45°/侧/背优先从人审通过 turnaround 拆，半身/脸部特写优先从已通过正面裁；若使用真实 image2image/multiref 后端生成，必须登记 method=controlled_multiref_generation 并保留可校验 source_path/source_sha256。禁止逐张文生图补角度导致脸漂。
- 第1集 / image_preflight / 资产身份注册层: 创作区/制漫剧/从变身少女开始斩妖除魔/出图/共享/identity_registry.json character#1 form#1 — side ready 拆分定妆必须是同源母本派生，登记 derivation.method/source_path/source_sha256/crop_box；45°/侧/背优先从人审通过 turnaround 拆，半身/脸部特写优先从已通过正面裁；若使用真实 image2image/multiref 后端生成，必须登记 method=controlled_multiref_generation 并保留可校验 source_path/source_sha256。禁止逐张文生图补角度导致脸漂。
- 第1集 / image_preflight / 资产身份注册层: 创作区/制漫剧/从变身少女开始斩妖除魔/出图/共享/identity_registry.json character#1 form#1 — back ready 拆分定妆必须是同源母本派生，登记 derivation.method/source_path/source_sha256/crop_box；45°/侧/背优先从人审通过 turnaround 拆，半身/脸部特写优先从已通过正面裁；若使用真实 image2image/multiref 后端生成，必须登记 method=controlled_multiref_generation 并保留可校验 source_path/source_sha256。禁止逐张文生图补角度导致脸漂。
- 第1集 / image_preflight / 资产身份注册层: 创作区/制漫剧/从变身少女开始斩妖除魔/出图/共享/identity_registry.json character#1 form#1 — half_body ready 拆分定妆必须是同源母本派生，登记 derivation.method/source_path/source_sha256/crop_box；45°/侧/背优先从人审通过 turnaround 拆，半身/脸部特写优先从已通过正面裁；若使用真实 image2image/multiref 后端生成，必须登记 method=controlled_multiref_generation 并保留可校验 source_path/source_sha256。禁止逐张文生图补角度导致脸漂。

## 验收总账

| 集 | 状态 | 实体数 | block | high | medium | 重点实体 |
|---|---|---:|---:|---:|---:|---|
| 第1集 | blocked | 20 | 6 | 0 | 19 | 姜月初(block)；年轻校尉(warn)；大唐皇帝(warn) |
