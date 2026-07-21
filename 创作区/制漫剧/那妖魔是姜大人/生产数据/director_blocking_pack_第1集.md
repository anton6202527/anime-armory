# P-2 导演排戏包 — 第1集

本包位于 Stage 1 台词之后、Stage 2 分镜之前，用来先锁导演排戏、镜头衔接和竖屏调度。

## Required Files

- `脚本/第1集/director_beat_sheet.json`
- `脚本/第1集/axis_blocking_map.json`
- `脚本/第1集/shot_progression_plan.json`
- `脚本/第1集/transition_map.json`
- `脚本/第1集/vertical_composition_plan.json`
- `脚本/第1集/edit_rhythm_map.json`

## Check

- 状态：block
- 通过：6/7

| 文件 | 状态 | 问题 |
|---|---|---|
| `脚本/第1集/director_beat_sheet.json` | pass | - |
| `脚本/第1集/axis_blocking_map.json` | pass | - |
| `脚本/第1集/shot_progression_plan.json` | pass | - |
| `脚本/第1集/transition_map.json` | pass | - |
| `脚本/第1集/vertical_composition_plan.json` | pass | - |
| `脚本/第1集/edit_rhythm_map.json` | pass | - |
| `脚本/第1集/director_blocking_signoff.json` | block | input_fingerprint 缺失或过期；上游输入变化后必须重新签收；approval[user:wesley:director] 未绑定当前 input_fingerprint；approval[user:wesley:producer] 未绑定当前 input_fingerprint；缺 creative 审批；允许角色：director；缺 production 审批；允许角色：editor, producer |
