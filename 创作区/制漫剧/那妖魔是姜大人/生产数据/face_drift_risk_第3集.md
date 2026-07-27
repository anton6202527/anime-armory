# 出图前·脸漂风险分（事前预测 + 实测漂移回灌）

- episode: 第3集 · 默认后端: codex
- ⛔ 阻断 1 · 🔴 预测高危 0 · 🟡 中危 0

| 角色 | 风险 | 分 | 锁脸档 | 主驱动 |
|---|---|---|---|---|
| 姜月初（CHAR_01/“囚途残损态”） | ⛔ block | 22.0 | multi_reference | 实测跨集漂移（既成事实）｜锁脸档位=multi_reference(+22)；极端角度 1 镜(+6)；同源场景 in-context 记功(strong·如 GPT Image 2)(+-6) |

## ⛔ 姜月初（CHAR_01/“囚途残损态”）· 分 22.0
- ⛔ 上一集已实测跨集脸漂（已出现 block 级脸漂 3 镜（first=第2集））：本集出图前先处置（重出漂移集 / 升原生主体或 LoRA），别带病续出——这是既成事实不是预测。
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。

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
