# n2d 横切 skill 地图（P0/P1/P2 · 非必经）

> 主状态机（`n2d-script`→`n2d-voice`/原生音画旁白层→`n2d-image`→`n2d-video`→`n2d-compose`→`n2d-review`）之外的横切能力全文档。
> SKILL.md 只留一行触发表，全文与产物在这里。**编排器 `skills/n2d/run.py next` 已把其中的确定性前置
> （gate / model-router / 身份矩阵刷新 / 合规检查）自动跑进每个 stage 的 prework**——下面这些条目用于
> 用户**显式**点名某能力时路由，或理解某横切层的完整职责。

---

## 生产数据仪表盘 + ROI（P0 横切）— `n2d-dashboard`

阶段完成后不只回写 `_进度.md`，还要调用 `n2d-dashboard` 写 `生产数据/production_events.jsonl` 并刷新 `dashboard.json` / `dashboard.md`。`_进度.md` 回答"哪步完成了"，仪表盘回答"每分钟成本、每集耗时、一次通过率、重抽率、QA 阻断、投放回收是否支撑工业级"。每次出图/出视频/配音/合成/审查都要入账；上线后把 `platform_metrics.*` 或 `record --event release` 补进去，不能只停在"能生成"。

发布、停线或交接前优先跑统一交付门：`python3 skills/n2d/scripts/production_readiness.py <作品根> 第N集 --write`。它会串起 `run.py next --json`、artifact validation、strict trace 的 `event_ledger.py audit/replay`、release manifest、artifact lineage、batch governance/reconcile 和 genre pack 校验；需要单独排障时再跑 `event_ledger.py doctor <作品根>` / `replay --write`。

## 角色身份闭环（P0/P1 横切）— `n2d-identity`

用户要"identity_registry / Face Lock / Character ID / LoRA / reference group / 跨集漂移报表"时，调 `n2d-identity`。它读取 `出图/共享/identity_registry.json`，生成 `生产数据/identity_adapter_matrix.json/md` 和 `identity_drift_report.json/md`。出图/出视频/审片只从这套矩阵取身份 binding，不在 prompt 现场手写临时 ID。

## LoRA 生命周期（P2/P1 横切）— `n2d-lora`

用户要"LoRA 自动化 / LoRA 训练 / LoRA 部署 / 第三代一致性 / safetensors 注册"时，调 `n2d-lora`。它只服务核心长线角色，管理 `设定库/lora/<CHAR_ID>/<形态>/` 下的数据集、训练任务、验证报告和 registry ready 回写；验证未通过不能写 `lora.status=ready`。

## 跨项目资产库 + 项目资产账本（P1 横切）— `n2d-asset-market`

用户要"查资产库 / 导入角色模板 / 导出服装武器 VFX 模板 / 沉淀打斗套路 / 成本摊薄"时，调 `n2d-asset-market`。跨项目层写 `资产库/.../asset_pack.json`，导入角色必须 fork 新身份并重置后端 Character ID / Face Lock / LoRA ready；导入非角色资产合并到本剧 `asset_registry.json`。

发布追溯另走项目内内容账本：`python3 skills/n2d-asset-market/scripts/asset_registry.py scan <作品根> --write` 生成 `生产数据/asset_registry.jsonl` 与摘要，记录脚本/图片/视频/成片/合规文件的 SHA256；`verify` 用于发现发布前资产缺失或被改。这个账本不等同跨项目模板 export。

## 合规与版权前置（P0 横切）— `n2d-compliance`

用户要"合规前置 / 版权前置 / 角色授权 / 声音克隆授权 / 平台审核 / 出海本地化"时，调 `n2d-compliance`。它生成/检查 `合规/compliance_manifest.json`，作为 `n2d-review gate` 的硬输入；image 前阻断源文本/改编权/角色肖像授权缺口，video 前阻断声音克隆缺口。`platform_review` / `localization` / `regulatory_filing` 是发布边界域：`publish_candidate` 在 image/video 只报 INFO 待办，compose/review/release 前转 BLOCK；`paid_distribution` 从任意阶段开始都 BLOCK；`internal_only` 降 INFO 但不得直接投放。合规不可沉默沿用，规则 profile 必须带检查日期。**AI 标识/AI 披露/水印只做 INFO 发布待办；compose 可 best-effort 辅助，但不得阻断主流程。**

正式交付前用 `python3 skills/n2d-compose/release_manifest.py build <作品根> 第N集 --stage review --write` 汇总母带 SHA256、合规缺口、gate findings、机器分、人审签收、AI 标识待办和事件账本审计路径；该命令会强制写/引用 `生产数据/artifact_lineage_第N集.json`，`check` 不通过时不能进入投放。

## 批量任务队列（P1 横切）— `n2d-batch`

用户要"多集一起跑 / 自动排队 / 并发 / 失败重试 / 只重跑受影响镜头 / worker 自动执行队列"时，调 `n2d-batch`。它按 `_进度.md` 生成 `生产数据/batch_queue.json`，执行者用 `claim` 占并发槽、用 `mark` 回写 pass/fail；配置 `生产数据/batch_runner.json` 后，`runner.py` 可自动 claim、执行配置命令、写 dashboard telemetry、回写状态。定妆变更或审查回流用 `--rerun-from image|video|compose --affected-shot/--affected-artifact` 做最小范围重跑。

放量治理入口是 `governance.py`：`init-slo` 写 `production_slo.json`，`check --write` 写 `batch_governance.json/md`，`dead-letter --write` 写 `dead_letter_queue.json/md`。任务自带 `idempotency_key`，runner 注入 `N2D_IDEMPOTENCY_KEY` 并把错误分类写入 `last_error_class`；死信出现后先停线修根因，再重新排最小范围任务。

## 模型适配层（P1 横切）— `n2d-model-router`

路由到 `n2d-video` 前，先调 `n2d-model-router` 生成 `出视频/第N集/prompt/video_model_routes.json/md`。`视频模型路由=自动按镜头路由` 为默认：打斗、追逐、对话反打、真相揭示、公开对质、关系转折、飞行、空镜、法术爆发、亲密互动、拥抱拉扯、多人同框、群像站位按模型能力选 primary/fallback；`生视频模型` 只做普通镜/兜底，不再固定全片。`生视频渠道` 只决定实际通过哪个产品/API/CLI 调用。若用户明确账号/预算限制只能用单模型，才写 `视频模型路由=固定生视频模型`，但每 Clip 仍要写模型路由字段和 fallback/degrade plan。旧值 `固定生视频AI` 兼容。

## 自动审片评分（P2 横切）— `n2d-score`

用户要"机器分 / 自动审片评分 / 低于阈值自动回流 / 图像相似度 / 字幕 OCR / 口型检测 / 成片节奏密度"，或完成一次成片/阶段审查后，调 `n2d-score`。它把 `n2d-review` 机检、一致性审查、`n2d-dashboard` 阻断和 `visual_checks.py` 汇总成七维分：角色一致性、服装一致性、场景一致性、字幕正确性、音画同步、节奏密度、风格一致性。默认阈值 `85`；低分输出 `auto_return_tasks`，加 `--enqueue-low` 可直接写入 `n2d-batch` 返工队列。

## 人审可视化 UI（P2 横切）— `n2d-review-ui`

用户要"人审 UI / 审片 UI / 无限画布 / 可视化审片 / 看首帧尾帧 clip 接缝定妆 QA flag 机器分"时，调 `n2d-review-ui`。它消费 `storyboard.json`、出图首尾帧、出视频 clip、`identity_registry`、`n2d-score` 输出和 score inputs，生成 `生产数据/review_ui_第N集.html/json`；先用机器分和 QA flag 筛 block/warn，再在画布里逐接缝、逐 clip 人判。

批量人审前跑 `calibration.py init` 建金标 case，再用 `calibration.py score --votes <csv|jsonl> --write` 产 `review_calibration.json/md`。`needs_calibration` 说明审片员口径不一致，先校准再签收。

## 投放数据回灌（P2 横切）— `n2d-feedback`

用户要"平台数据反哺 / 投放数据回灌 / 哪种开场留存高 / 哪类 cliffhanger 追更高 / 镜头密度导致跳出 / 自动提取导演标签 / 同集开场封面标题集尾 A/B"，调 `n2d-feedback`。它读取 `platform_metrics`，默认从 `storyboard.json` 自动抽取 `creative_features`（opening/cliffhanger/镜头密度/钩子间隔），也支持同一集多版本 `ab_test_id + variant_id`，比较 `opening_variant / cover_variant / cliffhanger_cut_variant / title_variant` 的同集 paired lift；生成 `生产数据/platform_feedback.json/md`，并可用 `--update-guide` 更新 `n2d/references/导演节奏.md` 的数据化快照。手工 `creative_features` 可覆盖自动标签；样本不足只观察。

A/B 开跑前用 `experiments.py upsert --id <ab_test_id> --variant A=... --variant B=... --write` 登记假设、变体、主指标和最小样本；数据回来后 `experiments.py audit --metrics <平台指标.csv> --write`。metrics 里有未登记 `ab_test_id` 或样本/变体不足时，不把结果写成导演铁律。
