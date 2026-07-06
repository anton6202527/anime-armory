# n2d Release Verdict

- 集：第2集
- 状态：blocked
- profile：demo
- 汇总：{'block': 5, 'warn': 5, 'pass': 8}

| component | status | message |
|---|---|---|
| progress_dag | pass | progress DAG 通过。 |
| production_handoff | pass | P-3 制片/场记交接已 confirmed。 |
| pilot_release_gate | pass | 非首集，不要求本集 pilot signoff。 |
| mini_pilot | warn | 本集有 3 个新/高风险代表镜头缺 mini-pilot；demo/internal 可继续，放量前必须补。 |
| contract_trace | warn | 源理解 trace_id 未完全贯通；demo/internal 可继续，但 production 不能只靠 confirmed。 |
| compliance | warn | 字段级合规存在发布待办：INFO/WARN=4；distribution_intent=internal_only。 |
| release_profile | pass | 发行 profile=demo；正式发布请改 cn_public/overseas/commercial 复核。 |
| gate | block | gate 仍有 block=4, warn=237。 |
| score | block | score 未达标：score=52, threshold=85, status=fail。 |
| ledger | block | ledger 未放行：status=blocked, block=3, high=0。 |
| review_ui | block | review-ui findings 仍有 block=7, warn=176。 |
| image_qc | pass | image_qc full 且新鲜。 |
| generation_recipe | pass | 生成配方 manifest 通过。 |
| audience_experience | warn | 观众体验 gate 有硬缺口；demo/internal 可看样，production 必须先修。 |
| stop_loss | warn | 批量 stop-loss 阈值触发；demo/internal 仅提示，放量前必须停线修复。 |
| final_master | pass | 最终母版存在：合成/第2集/成片_第2集_zh.mp4。 |
| release_evidence_freshness | pass | 发布证据晚于最终母版，时序新鲜。 |
| failure_taxonomy | block | report-only findings 升级为 block：524 条。 |
