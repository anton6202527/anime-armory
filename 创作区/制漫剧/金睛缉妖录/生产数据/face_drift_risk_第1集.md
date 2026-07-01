# 出图前·脸漂风险分（事前预测 + 实测漂移回灌）

- episode: 第1集 · 默认后端: codex
- ⛔ 阻断 0 · 🔴 预测高危 0 · 🟡 中危 1

| 角色 | 风险 | 分 | 锁脸档 | 主驱动 |
|---|---|---|---|---|
| 陈妻（CHAR_CHEN_WIFE/局部参考） | 🟡 medium | 36.0 | multi_reference | 锁脸档位=multi_reference(+22)；多人同框 1/1(+20.0)；同源场景 in-context 记功(strong·如 GPT Image 2)(+-6) |
| 沈砚（CHAR_SHEN_YAN/常态） | 🟢 low | 21.0 | multi_reference | 锁脸档位=multi_reference(+22)；近景占比 1/10(+3.0)；多人同框 1/10(+2.0) |

## 🟡 陈妻（CHAR_CHEN_WIFE/局部参考）· 分 36.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 基础定妆包缺 ready 的 3/4 侧脸参考：补 `reference_atlas.base_views.three_quarter`（45°/三分之二侧脸）并出图标 ready——45° 是全员基础角，不再按近景占比或角色体量延后。

## 含人共享资产镜脸漂诊断（治诊断侧盲区·武器/道具/海报）
- 🔴 0 · 🟡 0 · 🟢 7
| 资产 | 脸策略 | 风险 | 主驱动 |
|---|---|---|---|
| `PROP_BLOOD_THRESHOLD`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_MUD_FOOTPRINT`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_CLEAN_BLACK_BOOT`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_STILL_TEA`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_OLD_COPPER_HALF`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_RECORD_PAPER`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `WEAPON_PEIJUE_SHORT_BLADE`（weapon） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |


说明：🔴/🟡 是**出图前预测**（按建议提前加强参考/建表情库/上 LoRA）；⛔ 包含两类：n2d-identity 对已出图集**实测**到的跨集漂移回灌，或核心长线角在无持久主体后端上预测 high 且缺项目记忆/真实参考图束/分层合成/QC 执行计划。前者先处置漂移，后者先补执行计划或升档。（本次无可用实测数据：identity_drift_report 缺失或无 insightface，仅预测档生效。）
