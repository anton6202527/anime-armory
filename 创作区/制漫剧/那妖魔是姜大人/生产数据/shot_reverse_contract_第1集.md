# 第1集 正反打合同与镜头语法审计

- status: pass
- patterns: 6
- block: 0
- warn: 9

## 正反打合同

| Clip | A | B | 站位模式 | 轴线 | 覆盖 | 审计 |
|---|---|---|---|---|---|---|
| EP01_CLIP02 | CHAR_01/囚途残损态 | CHAR_02/半跪重伤态 | vertical_depth_9x16 | LOC_01/一炷香前 左右轴线；反打不越轴 | 35mm双人空间建立 + 85mm单人反应 + 断刀插入镜；近景不让三张清晰脸同框 | pass |
| EP01_CLIP03 | CHAR_01 | CHAR_02 | left_right | LOC_01 左右轴线；反打不越轴 | 85mm OTS/CU 交替 + 手部/断刀插入；反打只保一张清晰主脸 | pass |
| EP01_CLIP04 | CHAR_01/囚途残损态 | CHAR_02/重伤态 | vertical_depth_9x16 | LOC_01 左右轴线；反打不越轴 | 50mm双人MS为主 + 单人反应 + 搀扶手部插入；虎妖保持焦外伪死 | pass |
| EP01_CLIP05 | CHAR_01 | CHAR_02 | left_right | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP01_CLIP06 | CHAR_01 | CHAR_02 | left_right | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |
| EP01_CLIP08 | CHAR_01 | CHAR_02 | left_right | 按本场 180° 行动轴线；摄影机守同一侧。 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |

## 审计问题

| Clip | Severity | Code | Message |
|---|---|---|---|
| EP01_CLIP02 | warn | closeup_anchor_pending | 近景/反打镜未看到已落档的近景锚定图或脸锚引用。 |
| EP01_CLIP03 | warn | closeup_anchor_pending | 近景/反打镜未看到已落档的近景锚定图或脸锚引用。 |
| EP01_CLIP04 | warn | closeup_anchor_pending | 近景/反打镜未看到已落档的近景锚定图或脸锚引用。 |
| EP01_CLIP05 | warn | closeup_anchor_pending | 近景/反打镜未看到已落档的近景锚定图或脸锚引用。 |
| EP01_CLIP05 | warn | vertical_crowd_risk | 9:16 正反打含 3+ 主体，横向并排会导致脸小和关系乱。 |
| EP01_CLIP06 | warn | closeup_anchor_pending | 近景/反打镜未看到已落档的近景锚定图或脸锚引用。 |
| EP01_CLIP06 | warn | vertical_crowd_risk | 9:16 正反打含 3+ 主体，横向并排会导致脸小和关系乱。 |
| EP01_CLIP08 | warn | closeup_anchor_pending | 近景/反打镜未看到已落档的近景锚定图或脸锚引用。 |
| EP01_CLIP08 | warn | vertical_crowd_risk | 9:16 正反打含 3+ 主体，横向并排会导致脸小和关系乱。 |

## 传统影视镜头语法使用建议

| Clip | Techniques |
|---|---|
| EP01_CLIP01 | match_on_action, insert_cutaway, reaction_shot |
| EP01_CLIP02 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP01_CLIP03 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP01_CLIP04 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP01_CLIP05 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action, reestablishing_buffer, axial_pressure, reveal_closeup |
| EP01_CLIP06 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP01_CLIP07 | match_on_action, insert_cutaway, reaction_shot |
| EP01_CLIP08 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |

## 9:16 规则

- 不频繁横向多人并排，近景优先单人 clean single / OTS。
- 使用前景肩部、背景脸、上下高低位和纵深站位维持关系。
- 插入道具、手部、火把、门框、尘土、眼神反应用于节奏和越轴缓冲。
