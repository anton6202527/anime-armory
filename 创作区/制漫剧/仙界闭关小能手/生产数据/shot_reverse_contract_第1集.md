# 第1集 正反打合同与镜头语法审计

- status: pass
- patterns: 1
- block: 0
- warn: 0

## 正反打合同

| Clip | A | B | 站位模式 | 轴线 | 覆盖 | 审计 |
|---|---|---|---|---|---|---|
| EP01_CLIP02 | CHAR_01 | CHAR_02 | left_right | CHAR_01↔CHAR_02横轴 | 双人建立+清洁单人+手部插入+反应特写 | pass |

## 审计问题

| Clip | Severity | Code | Message |
|---|---|---|---|
| - | pass | - | 未发现确定性硬伤 |

## 传统影视镜头语法使用建议

| Clip | Techniques |
|---|---|
| EP01_CLIP01 | match_on_action, insert_cutaway, reaction_shot |
| EP01_CLIP02 | establishing_master, ots_pair, clean_single, reaction_shot, insert_cutaway, eyeline_cut, match_on_action |
| EP01_CLIP03 | match_on_action, insert_cutaway, reaction_shot |
| EP01_CLIP05 | match_on_action, insert_cutaway, reaction_shot |
| EP01_CLIP06 | match_on_action, insert_cutaway, reaction_shot |
| EP01_CLIP07 | match_on_action, insert_cutaway, reaction_shot |

## 9:16 规则

- 不频繁横向多人并排，近景优先单人 clean single / OTS。
- 使用前景肩部、背景脸、上下高低位和纵深站位维持关系。
- 插入道具、手部、火把、门框、尘土、眼神反应用于节奏和越轴缓冲。
