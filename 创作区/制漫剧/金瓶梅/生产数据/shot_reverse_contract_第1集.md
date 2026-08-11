# 第1集 正反打合同与镜头语法审计

- status: pass
- patterns: 11
- block: 0
- warn: 2

## 正反打合同

| Clip | A | B | 站位模式 | 轴线 | 覆盖 | 审计 |
|---|---|---|---|---|---|---|
| EP01_CLIP01 | character_id=BEAST_TIGER；screen_position=画面上方压下的攻击主体 | CHAR_WUSONG | vertical_depth_9x16 | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP01_CLIP02 | CHAR_WUSONG | character_id=BEAST_TIGER/扑击态；screen_position=画面后景/低位/受压或压出，按 storyboard 纵深站位锁定 | vertical_depth_9x16 | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP01_CLIP06 | CHAR_PANJINLIAN | CHAR_WUSONG | left_right | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP01_CLIP07 | CHAR_PANJINLIAN | CHAR_WUSONG | left_right | 炭盆—桌面横轴，潘左武松右。 | clean singles / OTS / insert / reaction | pass |
| EP01_CLIP08 | CHAR_PANJINLIAN | CHAR_WUSONG | left_right | 潘左武松右的炭盆横轴。 | clean singles / OTS / insert / reaction | pass |
| EP01_CLIP09 | CHAR_PANJINLIAN | CHAR_WUSONG | left_right | 潘左武松右，杯沿左→右越线。 | clean singles / OTS / insert / reaction | pass |
| EP01_CLIP10 | CHAR_PANJINLIAN | CHAR_WUDA | left_right | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP01_CLIP11 | CHAR_PANJINLIAN | CHAR_WUSONG | left_right | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP01_CLIP12 | CHAR_WUSONG | CHAR_WUDA | vertical_depth_9x16 | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP01_CLIP13 | CHAR_MAGISTRATE | CHAR_WUSONG | left_right | 案桌横轴，知县左武松右。 | clean singles / OTS / insert / reaction | pass |
| EP01_CLIP14 | CHAR_WUDA | CHAR_WUSONG | left_right | 门前横轴，武大左武松右。 | clean singles / OTS / insert / reaction | pass |

## 审计问题

| Clip | Severity | Code | Message |
|---|---|---|---|
| EP01_CLIP06 | warn | vertical_crowd_risk | 9:16 正反打含 3+ 主体，横向并排会导致脸小和关系乱。 |
| EP01_CLIP11 | warn | vertical_crowd_risk | 9:16 正反打含 3+ 主体，横向并排会导致脸小和关系乱。 |

## 传统影视镜头语法使用建议

| Clip | Techniques |
|---|---|
| EP01_CLIP01 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP01_CLIP02 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action, montage_ellipsis, j_cut_l_cut |
| EP01_CLIP03 | match_on_action, insert_cutaway, reaction_shot |
| EP01_CLIP04 | match_on_action, insert_cutaway, reaction_shot |
| EP01_CLIP05 | match_on_action, insert_cutaway, reaction_shot |
| EP01_CLIP06 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action, reestablishing_buffer, axial_pressure, reveal_closeup |
| EP01_CLIP07 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP01_CLIP08 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP01_CLIP09 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP01_CLIP10 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action, reestablishing_buffer, axial_pressure, reveal_closeup |
| EP01_CLIP11 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action, reestablishing_buffer, axial_pressure, reveal_closeup |
| EP01_CLIP12 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action, reestablishing_buffer, axial_pressure, reveal_closeup |
| EP01_CLIP13 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP01_CLIP14 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP01_CLIP15 | match_on_action, insert_cutaway, reaction_shot, reestablishing_buffer, axial_pressure, reveal_closeup, eyeline_cut |

## 9:16 规则

- 不频繁横向多人并排，近景优先单人 clean single / OTS。
- 使用前景肩部、背景脸、上下高低位和纵深站位维持关系。
- 插入道具、手部、火把、门框、尘土、眼神反应用于节奏和越轴缓冲。
