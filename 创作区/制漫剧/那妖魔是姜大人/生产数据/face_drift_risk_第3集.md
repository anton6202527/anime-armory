# 出图前·脸漂风险分（事前预测 + 实测漂移回灌）

- episode: 第3集 · 默认后端: codex
- ⛔ 阻断 0 · 🔴 预测高危 0 · 🟡 中危 0

| 角色 | 风险 | 分 | 锁脸档 | 主驱动 |
|---|---|---|---|---|
| 姜月初（CHAR_01/“囚途残损态”） | 🟢 low | 22.0 | multi_reference | 锁脸档位=multi_reference(+22)；极端角度 1 镜(+6)；同源场景 in-context 记功(strong·如 GPT Image 2)(+-6) |

## 含人共享资产镜脸漂诊断（治诊断侧盲区·武器/道具/海报）
- 🔴 0 · 🟡 0 · 🟢 5
| 资产 | 脸策略 | 风险 | 主驱动 |
|---|---|---|---|
| `LOC_02`（scene） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `WEAPON_01`（weapon） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `WEAPON_横刀`（weapon） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `LOC_01`（scene） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_镇魔司制服`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |


说明：🔴/🟡 是**出图前预测**（按建议提前加强参考、建表情库、走 image2image/多图参考链；LoRA 只在快速/云训路径明确时作为可选升档）；⛔ 包含两类：n2d-identity 对已出图集**实测**到的跨集漂移回灌，或核心长线角在无持久主体后端上预测 high 且缺项目记忆/真实参考图束/分层合成/QC 执行计划。前者先处置漂移，后者先补执行计划或升档。
