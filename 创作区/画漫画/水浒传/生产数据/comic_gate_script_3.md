# 漫画 Gate — script — 3

- 生成时间：2026-07-18T10:58:24
- 结论：block
- block/warn/info：6 / 0 / 0

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=3 block=5 warn=0

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| block | panel_script_missing | 脚本/3/panel_script.json | gate 必需文件缺失。 | script | 补齐该阶段产物后重跑 gate。 |
| block | chapter_contract_receipt_stale | 脚本/第3话/panel_script.json | panel_script 合同 SHA 不是当前本话 contract：85ec5dee17592696d65340a2a5a255a0d697400c596ffcc416a1bcbe9d62bf12 != 8508e5841718e6bc18e1d23f88ed23da60851068d9ae5115e6570f4aec18177e。 | script | 修正 chapter_contract 的 entry_state/continuity_delta/exit_state，并重签下游合同。 |
| block | chapter_entry_state_missing_previous_fact | 脚本/第3话/panel_script.json | 本话 entry_state 静默丢失上一话 exit_state 的 CHAR_ABBOT_SHANGQING.story_state='已向洪信说明一百零八魔君的来历，留守龙虎山修整殿宇、重立石碑。'。 | script | 修正 chapter_contract 的 entry_state/continuity_delta/exit_state，并重签下游合同。 |
| block | chapter_entry_state_missing_previous_fact | 脚本/第3话/panel_script.json | 本话 entry_state 静默丢失上一话 exit_state 的 CHAR_HONG_XIN.story_state='知道天罡地煞真相、主动封口并向天子隐瞒放魔责任的复职官员。'。 | script | 修正 chapter_contract 的 entry_state/continuity_delta/exit_state，并重签下游合同。 |
| block | chapter_entry_state_missing_previous_fact | 脚本/第3话/panel_script.json | 本话 entry_state 静默丢失上一话 exit_state 的 CHAR_HONG_XIN.visual_state='返京朝觐时重新整理为洁净官服，外表恢复稳拿，掌心仍有冷汗。'。 | script | 修正 chapter_contract 的 entry_state/continuity_delta/exit_state，并重签下游合同。 |
| block | chapter_entry_state_missing_previous_fact | 脚本/第3话/panel_script.json | 本话 entry_state 静默丢失上一话 exit_state 的 PROP_IMPERIAL_EDICT.location='收藏于上清宫御书匣。'。 | script | 修正 chapter_contract 的 entry_state/continuity_delta/exit_state，并重签下游合同。 |
