# P-3 制片拆解包 — 第1集

本包位于 Stage 2 分镜之后、出图 prompt 之前，用来把导演分镜翻译成可执行的制片交接。

## Required Files

- `脚本/第1集/production_breakdown.json`
- `脚本/第1集/continuity_breakdown.json`
- `脚本/第1集/continuity_chain.json`
- `脚本/第1集/continuity_bible.json`
- `脚本/第1集/ai_shooting_schedule.json`
- `脚本/第1集/ai_call_sheet.md`
- `生产数据/ai_shooting_schedule_batch_seed_第1集.json`

## Check

- 状态：block
- 通过：1/9

| 文件 | 状态 | 问题 |
|---|---|---|
| `脚本/第1集/production_breakdown.json` | block | status 不是 confirmed |
| `脚本/第1集/continuity_breakdown.json` | block | status 不是 confirmed |
| `脚本/第1集/continuity_chain.json` | block | status 不是 confirmed |
| `脚本/第1集/continuity_bible.json` | block | status 不是 confirmed |
| `脚本/第1集/ai_shooting_schedule.json` | block | status 不是 confirmed |
| `脚本/第1集/ai_call_sheet.md` | block | 缺 status: confirmed / 状态: confirmed |
| `脚本/第1集/production_handoff_pack.json` | block | status 不是 confirmed |
| `生产数据/ai_shooting_schedule_batch_seed_第1集.json` | pass | - |
| `脚本/第1集/production_handoff_signoff.json` | block | 缺上游签收：脚本/第1集/animatic_signoff.json；缺 handoff 审批；允许角色：assistant_director, producer, script_supervisor；signoff 尚未 approved |
