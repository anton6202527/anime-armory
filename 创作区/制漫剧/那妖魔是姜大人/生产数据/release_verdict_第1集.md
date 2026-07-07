# n2d Release Verdict

- 集：第1集
- 状态：blocked
- profile：demo
- 汇总：{'block': 5, 'warn': 2, 'pass': 11}

| component | status | message |
|---|---|---|
| progress_dag | pass | progress DAG 通过。 |
| production_handoff | pass | P-3 制片/场记交接已 confirmed。 |
| pilot_release_gate | pass | 首集 pilot 通过：clips=4。 |
| mini_pilot | pass | mini-pilot 已覆盖本集新/高风险条件：risk_clips=3。 |
| contract_trace | pass | 源理解 trace_id 已贯通到每集合同/分镜/生成证据/镜头产物。 |
| compliance | warn | 字段级合规存在发布待办：INFO/WARN=1；distribution_intent=internal_only。 |
| release_profile | pass | 发行 profile=demo；正式发布请改 cn_public/overseas/commercial 复核。 |
| gate | block | gate 仍有 block=8, warn=258。 |
| score | block | score 未达标：score=80, threshold=85, status=fail。 |
| ledger | block | ledger 未放行：status=blocked, block=4, high=0。 |
| review_ui | block | review-ui findings 仍有 block=25, warn=38。 |
| image_qc | pass | image_qc full 且新鲜。 |
| generation_recipe | pass | 生成配方 manifest 通过。 |
| audience_experience | warn | 观众体验 gate 有 warn：可能制作没错但不想追。 |
| stop_loss | pass | 批量 stop-loss 未触发。 |
| final_master | pass | 最终母版存在：合成/第1集/成片_第1集_zh.mp4。 |
| release_evidence_freshness | pass | 发布证据晚于最终母版，时序新鲜。 |
| failure_taxonomy | block | report-only findings 升级为 block：37 条。 |
