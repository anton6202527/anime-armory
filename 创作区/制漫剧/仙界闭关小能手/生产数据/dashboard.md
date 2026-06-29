# n2d 生产数据仪表盘

- 生成时间：2026-06-29T09:10:08+00:00
- 事件日志：`创作区/制漫剧/仙界闭关小能手/生产数据/production_events.jsonl`
- 投放数据：`未发现 platform_metrics.*`

## 总览

| 集数 | 事件数 | 成本 | 耗时 | 生成次数 | 重抽 | QA阻断 | QA警告 | 生成通过率 | 可交付通过率 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 4 | 538 | — | 19m32s | 8 | 0 | 318 | 181 | 100.0% | 0.0% |

## ROI

| 成片分钟 | 每分钟成本 | 每集耗时 | 一次通过率 | 重抽率 | 投放播放 | 投放收入 | 投放成本 | 净回收 | 回收/生产成本 |
|---:|---|---:|---:|---:|---:|---|---|---|---:|
| 1m55s | — | 19m32s | 100.0% | 0.0% | 0 | — | — | — | — |

## Gate 噪声

| warn/生成 | block/生成 | 误报回收 | 误报回收率 |
|---:|---:|---:|---:|
| 22.625 | 39.75 | 0 | 0.0% |

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
| 第1集 | 出图 | — | — | 19m32s | 100.0% | 0.0% | — | 318 | — | — | — | — | — | — |
| 第2集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第3集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |
| 第4集 | 阶段1·剧本改编 | — | — | 0s | — | — | — | 0 | — | — | — | — | — | — |

## 最新阻断

- 第1集 / image / 生图后端基线: 创作区/制漫剧/仙界闭关小能手/生产数据/image_backend_baseline.json — 本项目尚未锁定生图后端基线。production 必须每部剧固定一组生图模型/渠道；先确认当前 _设置.md 的 `生图AI/生图模型` 后执行 `python3 skills/n2d/_lib/image_backend_adapter.py record-baseline "创作区/制漫剧/仙界闭关小能手"`，再进入付费出图。
- 第1集 / image / 关键镜候选: 创作区/制漫剧/仙界闭关小能手/生产数据/candidate_selection_第1集.json — production 出图后缺 candidate_selection_第1集.json；关键镜必须经过 best-of-N 选优而不是单张通过。生成候选后跑 `python3 skills/n2d-image/scripts/candidate_select.py "创作区/制漫剧/仙界闭关小能手" 第1集 --apply`。
- 第1集 / image / 主角装备库: 创作区/制漫剧/仙界闭关小能手/出图/共享/identity_registry.json character#1 form#1 signature_equipment — 核心动作角色缺 signature_equipment；请把主角常用武器/法宝/标志性道具登记为 WEAPON_xx/PROP_xx/VFX_xx，并在角色 form 上绑定，避免主角形象只锁脸不锁随身装备。
- 第1集 / image / 资产身份注册层: 创作区/制漫剧/仙界闭关小能手/出图/共享/identity_registry.json character#1 form#1 — reference_atlas.base_views 基础视角必须为 ready 且有路径：front, three_quarter, side, back, half_body；所有人物/形态都强制包含 45°/three_quarter 与脸部特写基础锚，不能登记为 planned 后放行。
- 第1集 / image / 资产身份注册层: 创作区/制漫剧/仙界闭关小能手/出图/共享/identity_registry.json character#1 form#1 — reference_atlas 至少登记一个 ready 的同源脸部特写/表情参考（face_anchor_refs 或 expression_refs）；功能角色也不能只靠正脸硬扛近景，planned 脸锚不能放行。
- 第1集 / image / 资产身份注册层: 创作区/制漫剧/仙界闭关小能手/出图/共享/identity_registry.json character#1 form#1 — reference_group 缺核心路径：three_quarter
- 第1集 / image / 资产身份注册层: 创作区/制漫剧/仙界闭关小能手/出图/共享/identity_registry.json character#1 form#1 — side ready 拆分定妆必须是同源母本派生，登记 derivation.method/source_path/source_sha256/crop_box；45°/侧/背优先从人审通过 turnaround 拆，半身/脸部特写优先从已通过正面裁；若使用真实 image2image/multiref 后端生成，必须登记 method=controlled_multiref_generation 并保留可校验 source_path/source_sha256。禁止逐张文生图补角度导致脸漂。
- 第1集 / image / 资产身份注册层: 创作区/制漫剧/仙界闭关小能手/出图/共享/identity_registry.json character#1 form#1 — back ready 拆分定妆必须是同源母本派生，登记 derivation.method/source_path/source_sha256/crop_box；45°/侧/背优先从人审通过 turnaround 拆，半身/脸部特写优先从已通过正面裁；若使用真实 image2image/multiref 后端生成，必须登记 method=controlled_multiref_generation 并保留可校验 source_path/source_sha256。禁止逐张文生图补角度导致脸漂。

## 验收总账

| 集 | 状态 | 实体数 | block | high | medium | 重点实体 |
|---|---|---:|---:|---:|---:|---|
| 第1集 | blocked | 16 | 5 | 3 | 13 | 贺平生(block)；黑陶破盆(block)；张老大(high) |
