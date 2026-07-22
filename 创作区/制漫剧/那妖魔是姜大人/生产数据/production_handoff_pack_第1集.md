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
- 通过：7/9

| 文件 | 状态 | 问题 |
|---|---|---|
| `脚本/第1集/production_breakdown.json` | pass | - |
| `脚本/第1集/continuity_breakdown.json` | pass | - |
| `脚本/第1集/continuity_chain.json` | pass | - |
| `脚本/第1集/continuity_bible.json` | pass | - |
| `脚本/第1集/ai_shooting_schedule.json` | pass | - |
| `脚本/第1集/ai_call_sheet.md` | pass | - |
| `脚本/第1集/production_handoff_pack.json` | block | inputs_fingerprint 已过期，上游输入变更后需重新确认 P-3 handoff |
| `生产数据/ai_shooting_schedule_batch_seed_第1集.json` | pass | - |
| `脚本/第1集/production_handoff_signoff.json` | block | input_fingerprint 缺失或过期；上游输入变化后必须重新签收；approval[user:wesley:producer] 未绑定当前 input_fingerprint；缺 handoff 审批；允许角色：assistant_director, producer, script_supervisor |
