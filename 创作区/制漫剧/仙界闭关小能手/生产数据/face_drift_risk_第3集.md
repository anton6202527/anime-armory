# 出图前·脸漂风险分（事前预测 + 实测漂移回灌）

- episode: 第3集 · 默认后端: codex
- ⛔ 阻断 0 · 🔴 预测高危 0 · 🟡 中危 1

| 角色 | 风险 | 分 | 锁脸档 | 主驱动 |
|---|---|---|---|---|
| 张老大（CHAR_ZHANG_LAODA/常态） | 🟡 medium | 36.0 | multi_reference | 锁脸档位=multi_reference(+22)；多人同框 2/2(+20.0)；同源场景 in-context 记功(strong·如 GPT Image 2)(+-6) |
| 贺平生（CHAR_HE_PINGSHENG/常态） | 🟢 low | 25.3 | multi_reference | 锁脸档位=multi_reference(+22)；极端角度 1 镜(+6)；多人同框 2/12(+3.3) |

## 🟡 张老大（CHAR_ZHANG_LAODA/常态）· 分 36.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。

## 含人共享资产镜脸漂诊断（治诊断侧盲区·武器/道具/海报）
- 🔴 0 · 🟡 0 · 🟢 11
| 资产 | 脸策略 | 风险 | 主驱动 |
|---|---|---|---|
| `PROP_BLACK_BASIN`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_GOLD_RICE`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_GREY_RICE_MEMORY`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_DOOR_LOCK`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_DOOR`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_GOLD_RICE_visible`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_TROUSER_PILLOW`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_MOUNTAIN_SPRING`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_WATER_BUCKETS`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_WATER_JAR`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_INNER_SECT_LANTERN`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |


说明：🔴/🟡 是**出图前预测**（按建议提前加强参考/建表情库/上 LoRA）；⛔ 包含两类：n2d-identity 对已出图集**实测**到的跨集漂移回灌，或核心长线角在无持久主体后端上预测 high 且缺项目记忆/真实参考图束/分层合成/QC 执行计划。前者先处置漂移，后者先补执行计划或升档。（本次无可用实测数据：identity_drift_report 缺失或无 insightface，仅预测档生效。）
