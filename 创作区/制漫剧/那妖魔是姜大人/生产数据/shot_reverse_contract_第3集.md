# 第3集 正反打合同与镜头语法审计

- status: pass
- patterns: 5
- block: 0
- warn: 1

## 正反打合同

| Clip | A | B | 站位模式 | 轴线 | 覆盖 | 审计 |
|---|---|---|---|---|---|---|
| EP03_CLIP06 | CHAR_01 | CHAR_04 | vertical_depth_9x16 | LOC_02 官道轴线：姜月初画左/上位，陈青源画右/下位；反打不越轴。 | clean single + shot/reverse-shot + fire-torch insert/reaction；清晰近景默认拆正反打，不把姜月初、陈 | pass |
| EP03_CLIP07 | CHAR_01 | CHAR_04 | left_right | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP03_CLIP08 | CHAR_01 | CHAR_04 | vertical_depth_9x16 | LOC_02 官道轴线延续：陈青源低位画左/下，姜月初高位画右/上；危机信息用反打吸收。 | clean single + reaction close-up + fire-shadow insert；危机信息只用火把阴影和低饱和剪影承接，不插入完整狼妖 | pass |
| EP03_CLIP09 | CHAR_01 | CHAR_04 | left_right | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP03_CLIP10 | CHAR_01 | CHAR_04 | vertical_depth_9x16 | LOC_02 低位求救/高位沉默轴线延续到硬切黑；陈青源低位，姜月初高位。 | low-angle clean single + foreground reaction close-up + torch insert + hard-cut  | pass |

## 审计问题

| Clip | Severity | Code | Message |
|---|---|---|---|
| EP03_CLIP07 | warn | vertical_crowd_risk | 9:16 正反打含 3+ 主体，横向并排会导致脸小和关系乱。 |

## 传统影视镜头语法使用建议

| Clip | Techniques |
|---|---|
| EP03_CLIP01 | match_on_action, insert_cutaway, reaction_shot |
| EP03_CLIP02 | match_on_action, insert_cutaway, reaction_shot |
| EP03_CLIP03 | match_on_action, insert_cutaway, reaction_shot |
| EP03_CLIP05 | match_on_action, insert_cutaway, reaction_shot |
| EP03_CLIP06 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP03_CLIP07 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut |
| EP03_CLIP08 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP03_CLIP09 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action, reestablishing_buffer, axial_pressure, reveal_closeup |
| EP03_CLIP10 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |

## 9:16 规则

- 不频繁横向多人并排，近景优先单人 clean single / OTS。
- 使用前景肩部、背景脸、上下高低位和纵深站位维持关系。
- 插入道具、手部、火把、门框、尘土、眼神反应用于节奏和越轴缓冲。
