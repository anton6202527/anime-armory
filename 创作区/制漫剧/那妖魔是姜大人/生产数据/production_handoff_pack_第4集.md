# P-3 制片拆解包 — 第4集

本包位于 Stage 2 分镜之后、出图 prompt 之前，用来把导演分镜翻译成可执行的制片交接。

## Required Files

- `脚本/第4集/production_breakdown.json`
- `脚本/第4集/continuity_breakdown.json`
- `脚本/第4集/continuity_chain.json`
- `脚本/第4集/continuity_bible.json`
- `脚本/第4集/ai_shooting_schedule.json`
- `脚本/第4集/ai_call_sheet.md`
- `生产数据/ai_shooting_schedule_batch_seed_第4集.json`

## Check

- 状态：block
- 通过：4/8

| 文件 | 状态 | 问题 |
|---|---|---|
| `脚本/第4集/production_breakdown.json` | pass | - |
| `脚本/第4集/continuity_breakdown.json` | pass | - |
| `脚本/第4集/continuity_chain.json` | block | status 不是 confirmed；continuity_chain 仍有阻断 seam：Clip_03→Clip_04(missing_episode_boundary_contract) |
| `脚本/第4集/continuity_bible.json` | block | status 不是 confirmed |
| `脚本/第4集/ai_shooting_schedule.json` | block | status 不是 confirmed |
| `脚本/第4集/ai_call_sheet.md` | pass | - |
| `脚本/第4集/production_handoff_pack.json` | block | status 不是 confirmed |
| `生产数据/ai_shooting_schedule_batch_seed_第4集.json` | pass | - |
