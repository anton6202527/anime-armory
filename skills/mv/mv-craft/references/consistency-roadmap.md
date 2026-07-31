# mv 流程与一致性审查·落地记录与暂缓路线图

> 2026-07-20 全线审查（流程闸门链 + 视觉一致性执行 + 实时调研）后的单一记录：哪些缺口已修、哪些是**有意暂缓**及理由。再次审查前先读本文件，避免重复议题或误判「漏做」。

## 已落地（2026-07-20）

| 缺口 | 修复 | 落点 |
|---|---|---|
| image_qc 新鲜度用 mtime 判过期（全线唯一时间戳闸，可被恢复旧图/跨机复制骗过） | QC 报告携带 `assets_sha256` 内容收据，gate 按 hash 核对；旧报告 mtime 兜底 + 提示升级 | `image_qc.py` / `gate._image_qc_errors_warnings` |
| `generated_at` 混进被 hash 载荷：同输入隔天重跑 → clip_plan hash 变 → timeline/semantic/picture_lock 全链无谓失效 | `write_json_stable`（仅 volatile 字段不同则不重写，字节稳定）用于 clip_plan/timeline/注册表/semantic 收据 | `mv/_lib/io_utils.py` + plan_clips/identity_registry/compose_prompts |
| 出图→出视频无像素级绑定（视频不证明来自已过 QC 的那张首帧） | `--register` 登记时落 `first/end_frame_sha256`；inherit_contract 核对当前 PNG，不一致 block | `video_jobs.register_take` / `inherit_contract.check_clip` |
| seed/生成参数零留痕，可复现性断裂 | 图侧 `record_generation.py --seed/--param/--provider-job-id`；视频侧 `--register --seed/--generation-param/--provider-job-id` | 两侧登记脚本（已知必记、缺省不阻断） |
| 锚点句 lint 仅 advisory：身份合同未进 prompt 也能过付费闸 | 正式项目 `missing_anchor_identity/forbidden/prompt_missing` → hard（B12 合同消费闸）；demo 与参考/视觉块保持 advisory | `image_qc.FORMAL_HARD_LINT_CODES` |
| 视频阶段脸漂永不硬拦（真正花大钱的阶段反而无同人底线） | 重度带（自标定阈值−0.15，下限 0.20）block；具名+绑定视频 hash 的 waiver 是唯一出口 | `video_qc.face_drift_verdict` + `--accept-face-drift` |
| formal_readiness 残留旧式 `manual_review_accepted` 裸布尔口径（比 gate 宽松） | 对齐 gate：具名 + `bound_report_sha256` 绑定当前报告 | `formal_readiness.build_report` |
| 无单一编排入口：`_进度.md` 与 gate 解耦，agent 靠散文路由自觉选下一步；「假 done」被动现形 | `mv/run.py next --json`：前沿 + 登记制 stop_reason + gate + 已 done 付费阶段收据健康度巡检 | `skills/mv/run.py` |
| 无 clip 粒度返工计算（改一个 clip 后下游重做范围靠人脑） | `mv/run.py impact --clip --change image\|prompt\|edit` 确定性级联清单 + 接缝邻居提示 | 同上 |
| 新硬闸可被后续「优化」静默降级 | 全部登记进 charter（gate guard tokens + QC 硬闸片段），introspect 测试守护 | `mv-review/scripts/consistency_charter.py` |

## 有意暂缓（评估过、当前不做）

- **生产事件账本 hash 链 + 成本预测 dashboard**：MV 是单作品短周期产线，无跨集成本曲线可滚；现有 `production_events.jsonl` + jobs_manifest 已覆盖审计需求。项目规模上来（多曲批产）再评估。
- **逐镜参考事前处方（reference_planner 式）**：mv 已有 drift_risk（事前预测）+ reference_plan（注册表注入）+ `MV一致性增强` 四档；再加一层处方器在 16–64 clip 规模收益低于维护成本（B10：闸已饱和，收敛优先）。
- **逐镜模型路由基线 / 一角一后端亲和**：mv 契约是「全程同一后端」（`backend_policy=uniform_default`，混用即 provenance block），单主角单曲下亲和钉选无对象；若未来放开逐镜混路由再引入。
- **VLM 裁决升硬闸**：`vlm_judge` 保持 advisory 三档告警（缺任务包/空转/覆盖不足）。裁决质量依赖外部多模态 agent，不满足 B10「BLOCK 须有可复算证据」；防空转已有合同校验（image_sha256/task_sha256/evaluator 逐字复制）。
- **beatgrid↔alignment hash 联动**：alignment 只绑 lyrics+song 是对的（对齐真值是音频不是分镜）；plan 侧变化由 mv_check 行数对账兜底，升级为 hash 级联收益小。
- **口型质量测量**：`演唱口型` 质量仍以 `--lip-sync-score` 人判为准；本地自动化音素对齐评测（音画偏移测量）等工具链成熟且确有正面唱演大盘需求时再接。

## 调研快照（2026-07-20，来源见 production-standards.md 官方依据一节）

- 业界一致性共识与本线架构一致：清晰参考图 + 锁风格 + 首尾帧接力 + 固定关键词序（锚点块）+ 角色 sheet 是主流做法；多主体同框仍是通用难点（本线 drift_risk 的 `multi_subject` 信号已覆盖）。
- 歌词对齐：已知歌词强制对齐（不让 ASR 改词）+ 人声 stem 预处理即当前最佳实践（WhisperX/wav2vec2 路线，词界 ±50ms 量级），本线 mv-lyric-sync 口径正确，无需换轨。
- seed/参数可复现：各后端支持度不一，「登记时已知则必记、拿不到不阻断」是与 C3/C4 兼容的正确强度。
