# 第1集 正反打合同与镜头语法审计

- status: pass
- patterns: 8
- block: 0
- warn: 0

## 正反打合同

| Clip | A | B | 站位模式 | 轴线 | 覆盖 | 审计 |
|---|---|---|---|---|---|---|
| EP01_CLIP04 | CHAR_01 | BEAST_01 | vertical_depth_9x16 | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP01_CLIP05 | CHAR_01 | CHAR_02 | vertical_depth_9x16 | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP01_CLIP07 | CHAR_01 | CHAR_02 | left_right | CHAR_01与CHAR_02连线，摄影机守尸场主轴近侧。 | clean single、轻OTS、手部insert、reaction。 | pass |
| EP01_CLIP09 | CHAR_01 | CHAR_02 | vertical_depth_9x16 | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP01_CLIP11 | CHAR_01 | CHAR_02 | vertical_depth_9x16 | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP01_CLIP15 | CHAR_01 | CHAR_02 | left_right | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP01_CLIP16 | CHAR_01 | CHAR_02 | vertical_depth_9x16 | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP01_CLIP17 | CHAR_01 | CHAR_02 | vertical_depth_9x16 | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |

## 审计问题

| Clip | Severity | Code | Message |
|---|---|---|---|
| - | pass | - | 未发现确定性硬伤 |

## 传统影视镜头语法使用建议

| Clip | Techniques |
|---|---|
| EP01_CLIP01 | match_on_action, insert_cutaway, reaction_shot |
| EP01_CLIP04 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action, reestablishing_buffer, axial_pressure, reveal_closeup |
| EP01_CLIP05 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action, reestablishing_buffer, axial_pressure, reveal_closeup |
| EP01_CLIP07 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP01_CLIP09 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action, reestablishing_buffer, axial_pressure, reveal_closeup |
| EP01_CLIP10 | match_on_action, insert_cutaway, reaction_shot |
| EP01_CLIP11 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP01_CLIP12 | match_on_action, insert_cutaway, reaction_shot |
| EP01_CLIP13 | match_on_action, insert_cutaway, reaction_shot |
| EP01_CLIP15 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, reestablishing_buffer, axial_pressure, reveal_closeup |
| EP01_CLIP16 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action, reestablishing_buffer, axial_pressure, reveal_closeup |
| EP01_CLIP17 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |

## 9:16 规则

- 不频繁横向多人并排，近景优先单人 clean single / OTS。
- 使用前景肩部、背景脸、上下高低位和纵深站位维持关系。
- 插入道具、手部、火把、门框、尘土、眼神反应用于节奏和越轴缓冲。
