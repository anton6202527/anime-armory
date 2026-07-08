# 第1集 正反打合同与镜头语法审计

- status: pass
- patterns: 1
- block: 0
- warn: 1

## 正反打合同

| Clip | A | B | 站位模式 | 轴线 | 覆盖 | 审计 |
|---|---|---|---|---|---|---|
| EP01_CLIP01 | CHAR_HE_PINGSHENG | CHAR_ZHANG_LAODA | left_right | 黑殿左右轴线稳定，反打不越轴 | establishing master + paired clean singles + true OTS with foreground shoulder + | pass |

## 审计问题

| Clip | Severity | Code | Message |
|---|---|---|---|
| EP01_CLIP01 | warn | vertical_crowd_risk | 9:16 正反打含 3+ 主体，横向并排会导致脸小和关系乱。 |

## 传统影视镜头语法使用建议

| Clip | Techniques |
|---|---|
| EP01_CLIP01 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP01_CLIP02 | match_on_action, insert_cutaway, reaction_shot, montage_ellipsis, j_cut_l_cut |
| EP01_CLIP03 | match_on_action, insert_cutaway, reaction_shot, montage_ellipsis, j_cut_l_cut |
| EP01_CLIP04 | match_on_action, insert_cutaway, reaction_shot |
| EP01_CLIP06 | match_on_action, insert_cutaway, reaction_shot |

## 9:16 规则

- 不频繁横向多人并排，近景优先单人 clean single / OTS。
- 使用前景肩部、背景脸、上下高低位和纵深站位维持关系。
- 插入道具、手部、火把、门框、尘土、眼神反应用于节奏和越轴缓冲。
