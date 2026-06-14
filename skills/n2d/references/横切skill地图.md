# n2d 横切 skill 地图（P0/P1/P2 · 非必经）

> 主干六阶段（`n2d-script`→`n2d-voice`→`n2d-image`→`n2d-video`→`n2d-compose`）之外的横切能力全文档。
> SKILL.md 只留一行触发表，全文与产物在这里。**编排器 `skills/n2d/run.py next` 已把其中的确定性前置
> （gate / model-router / 身份矩阵刷新 / 合规检查）自动跑进每个 stage 的 prework**——下面这些条目用于
> 用户**显式**点名某能力时路由，或理解某横切层的完整职责。

---

## 生产数据仪表盘 + ROI（P0 横切）— `n2d-dashboard`

阶段完成后不只回写 `_进度.md`，还要调用 `n2d-dashboard` 写 `生产数据/production_events.jsonl` 并刷新 `dashboard.json` / `dashboard.md`。`_进度.md` 回答"哪步完成了"，仪表盘回答"每分钟成本、每集耗时、一次通过率、重抽率、QA 阻断、投放回收是否支撑工业级"。每次出图/出视频/配音/合成/审查都要入账；上线后把 `platform_metrics.*` 或 `record --event release` 补进去，不能只停在"能生成"。

## 角色身份闭环（P0/P1 横切）— `n2d-identity`

用户要"identity_registry / Face Lock / Character ID / LoRA / reference group / 跨集漂移报表"时，调 `n2d-identity`。它读取 `出图/共享/identity_registry.json`，生成 `生产数据/identity_adapter_matrix.json/md` 和 `identity_drift_report.json/md`。出图/出视频/审片只从这套矩阵取身份 binding，不在 prompt 现场手写临时 ID。

## LoRA 生命周期（P2/P1 横切）— `n2d-lora`

用户要"LoRA 自动化 / LoRA 训练 / LoRA 部署 / 第三代一致性 / safetensors 注册"时，调 `n2d-lora`。它只服务核心长线角色，管理 `设定库/lora/<CHAR_ID>/<形态>/` 下的数据集、训练任务、验证报告和 registry ready 回写；验证未通过不能写 `lora.status=ready`。

## 合规与版权前置（P0 横切）— `n2d-compliance`

用户要"合规前置 / 版权前置 / 角色授权 / 声音克隆授权 / 平台审核 / 出海本地化"时，调 `n2d-compliance`。它生成/检查 `合规/compliance_manifest.json`，作为 `n2d-review gate` 的硬输入；image 前阻断源文本/改编权/角色肖像授权缺口，video 前阻断声音克隆缺口，compose/review 前阻断平台审核和出海本地化缺口。合规不可沉默沿用，规则 profile 必须带检查日期。**AI 标识/AI 披露/水印不再由本流水线强制——该合规义务移到工具之外处理。**

## 批量任务队列（P1 横切）— `n2d-batch`

用户要"多集一起跑 / 自动排队 / 并发 / 失败重试 / 只重跑受影响镜头 / worker 自动执行队列"时，调 `n2d-batch`。它按 `_进度.md` 生成 `生产数据/batch_queue.json`，执行者用 `claim` 占并发槽、用 `mark` 回写 pass/fail；配置 `生产数据/batch_runner.json` 后，`runner.py` 可自动 claim、执行配置命令、写 dashboard telemetry、回写状态。定妆变更或审查回流用 `--rerun-from image|video|compose --affected-shot/--affected-artifact` 做最小范围重跑。

## 模型适配层（P1 横切）— `n2d-model-router`

路由到 `n2d-video` 前，先调 `n2d-model-router` 生成 `出视频/第N集/prompt/video_model_routes.json/md`。`视频模型路由=自动按镜头路由` 为默认：打斗、追逐、对话反打、飞行、空镜、法术爆发、亲密互动、拥抱拉扯、多人同框、群像站位按模型能力选 primary/fallback；`生视频模型` 只做普通镜/兜底，不再固定全片。`生视频渠道` 只决定实际通过哪个产品/API/CLI 调用。若用户明确账号/预算限制只能用单模型，才写 `视频模型路由=固定生视频模型`，但每 Clip 仍要写模型路由字段和 fallback/degrade plan。旧值 `固定生视频AI` 兼容。

## 自动审片评分（P2 横切）— `n2d-score`

用户要"机器分 / 自动审片评分 / 低于阈值自动回流 / 图像相似度 / 字幕 OCR / 口型检测 / 成片节奏密度"，或完成一次成片/阶段审查后，调 `n2d-score`。它把 `n2d-review` 机检、一致性审查、`n2d-dashboard` 阻断和 `visual_checks.py` 汇总成七维分：角色一致性、服装一致性、场景一致性、字幕正确性、音画同步、节奏密度、风格一致性。默认阈值 `85`；低分输出 `auto_return_tasks`，加 `--enqueue-low` 可直接写入 `n2d-batch` 返工队列。

## 人审可视化 UI（P2 横切）— `n2d-review-ui`

用户要"人审 UI / 审片 UI / 无限画布 / 可视化审片 / 看首帧尾帧 clip 接缝定妆 QA flag 机器分"时，调 `n2d-review-ui`。它消费 `storyboard.json`、出图首尾帧、出视频 clip、`identity_registry`、`n2d-score` 输出和 score inputs，生成 `生产数据/review_ui_第N集.html/json`；先用机器分和 QA flag 筛 block/warn，再在画布里逐接缝、逐 clip 人判。

## 投放数据回灌（P2 横切）— `n2d-feedback`

用户要"平台数据反哺 / 投放数据回灌 / 哪种开场留存高 / 哪类 cliffhanger 追更高 / 镜头密度导致跳出 / 自动提取导演标签 / 同集开场封面标题集尾 A/B"，调 `n2d-feedback`。它读取 `platform_metrics`，默认从 `storyboard.json` 自动抽取 `creative_features`（opening/cliffhanger/镜头密度/钩子间隔），也支持同一集多版本 `ab_test_id + variant_id`，比较 `opening_variant / cover_variant / cliffhanger_cut_variant / title_variant` 的同集 paired lift；生成 `生产数据/platform_feedback.json/md`，并可用 `--update-guide` 更新 `n2d/references/导演节奏.md` 的数据化快照。手工 `creative_features` 可覆盖自动标签；样本不足只观察。
