# 出图前·脸漂风险分（事前预测 + 实测漂移回灌）

- episode: 第1集 · 默认后端: codex
- ⛔ 阻断 0 · 🔴 预测高危 0 · 🟡 中危 1

| 角色 | 风险 | 分 | 锁脸档 | 主驱动 |
|---|---|---|---|---|
| 程老（CHAR_CHENG_LAO/朝堂常态） | 🟡 medium | 31.0 | multi_reference | 锁脸档位=multi_reference(+22)；近景占比 1/2(+15.0)；同源场景 in-context 记功(strong·如 GPT Image 2)(+-6) |
| 姜月初（CHAR_JIANG_YUECHU/战场形态） | 🟢 low | 19.3 | multi_reference | 锁脸档位=multi_reference(+22)；近景占比 1/9(+3.3)；同源场景 in-context 记功(strong·如 GPT Image 2)(+-6) |

## 🟡 程老（CHAR_CHENG_LAO/朝堂常态）· 分 31.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。

## 含人共享资产镜脸漂诊断（治诊断侧盲区·武器/道具/海报）
- 🔴 0 · 🟡 0 · 🟢 1
| 资产 | 脸策略 | 风险 | 主驱动 |
|---|---|---|---|
| `WEAPON_DAHUANG_HALBERD`（weapon） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |


说明：🔴/🟡 是**出图前预测**（按建议提前加强参考/建表情库/上 LoRA）；⛔ 包含两类：n2d-identity 对已出图集**实测**到的跨集漂移回灌，或核心长线角在无持久主体后端上预测 high 且缺项目记忆/真实参考图束/分层合成/QC 执行计划。前者先处置漂移，后者先补执行计划或升档。（本次无可用实测数据：identity_drift_report 缺失或无 insightface，仅预测档生效。）
