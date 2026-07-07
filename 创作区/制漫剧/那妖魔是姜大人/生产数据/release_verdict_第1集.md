# n2d Release Verdict

- 集：第1集
- 状态：internal-only
- profile：demo
- 汇总：{'block': 0, 'warn': 5, 'pass': 13}

| component | status | message |
|---|---|---|
| progress_dag | pass | progress DAG 通过。 |
| production_handoff | pass | P-3 制片/场记交接已 confirmed。 |
| pilot_release_gate | pass | 首集 pilot 通过：clips=4。 |
| mini_pilot | pass | mini-pilot 已覆盖本集新/高风险条件：risk_clips=3。 |
| contract_trace | pass | 源理解 trace_id 已贯通到每集合同/分镜/生成证据/镜头产物。 |
| compliance | warn | 字段级合规存在发布待办：INFO/WARN=1；distribution_intent=internal_only。 |
| release_profile | pass | 发行 profile=demo；正式发布请改 cn_public/overseas/commercial 复核。 |
| gate | warn | gate 有 warn=259，需结合 taxonomy 判断是否只可 demo。 |
| score | pass | score 通过：score=93, threshold=85。 |
| ledger | pass | consistency ledger 通过。 |
| review_ui | warn | review-ui findings 有 warn=62。 |
| image_qc | pass | image_qc full 且新鲜。 |
| generation_recipe | pass | 生成配方 manifest 通过。 |
| audience_experience | warn | 观众体验 gate 有 warn：可能制作没错但不想追。 |
| stop_loss | pass | 批量 stop-loss 未触发。 |
| final_master | pass | 最终母版存在：合成/第1集/成片_第1集_zh.mp4。 |
| release_evidence_freshness | pass | 发布证据晚于最终母版，时序新鲜。 |
| failure_taxonomy | warn | 存在 findings=475 条，但未升级 block。 |
