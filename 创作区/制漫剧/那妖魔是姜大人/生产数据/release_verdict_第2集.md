# n2d Release Verdict

- 集：第2集
- 状态：internal-only
- profile：demo
- 汇总：{'block': 0, 'warn': 6, 'pass': 12}

| component | status | message |
|---|---|---|
| progress_dag | pass | progress DAG 通过。 |
| production_handoff | pass | P-3 制片/场记交接已 confirmed。 |
| pilot_release_gate | pass | 非首集，不要求本集 pilot signoff。 |
| mini_pilot | warn | 本集有 3 个新/高风险代表镜头缺 mini-pilot；demo/internal 可继续，放量前必须补。 |
| contract_trace | warn | 源理解 trace_id 未完全贯通；demo/internal 可继续，但 production 不能只靠 confirmed。 |
| compliance | warn | 字段级合规存在发布待办：INFO/WARN=4；distribution_intent=internal_only。 |
| release_profile | pass | 发行 profile=demo；正式发布请改 cn_public/overseas/commercial 复核。 |
| gate | warn | gate 有 warn=239，需结合 taxonomy 判断是否只可 demo。 |
| score | pass | score 通过：score=90, threshold=85。 |
| ledger | pass | consistency ledger 通过。 |
| review_ui | warn | review-ui findings 有 warn=150。 |
| image_qc | pass | image_qc full 且新鲜。 |
| generation_recipe | pass | 生成配方 manifest 通过。 |
| audience_experience | pass | 观众体验 gate 通过：首钩/回报节奏/尾钩具备。 |
| stop_loss | pass | 批量 stop-loss 未触发。 |
| final_master | pass | 最终母版存在：合成/第2集/成片_第2集_zh.mp4。 |
| release_evidence_freshness | pass | 发布证据晚于最终母版，时序新鲜。 |
| failure_taxonomy | warn | 存在 findings=510 条，但未升级 block。 |
