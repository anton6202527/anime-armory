# 出图前·脸漂风险分（事前预测 + 实测漂移回灌）

- episode: 第1集 · 默认后端: codex
- ⛔ 阻断 0 · 🔴 预测高危 3 · 🟡 中危 0

| 角色 | 风险 | 分 | 锁脸档 | 主驱动 |
|---|---|---|---|---|
| 裴长青（CHAR_02/濒死战损态） | 🔴 high | 95.0 | multi_reference | 近景占比 9/10(+27.0)；极端角度 5 镜(+24)；锁脸档位=multi_reference(+22) |
| 姜月初（CHAR_01/囚犯初醒态） | 🔴 high | 93.5 | multi_reference | 近景占比 10/11(+27.3)；极端角度 6 镜(+24)；锁脸档位=multi_reference(+22) |
| 虎山神 / 虎妖（CHAR_03/诈死复苏态） | 🔴 high | 90.0 | multi_reference | 近景占比 7/7(+30.0)；极端角度 4 镜(+24)；锁脸档位=multi_reference(+22) |

## 🔴 裴长青（CHAR_02/濒死战损态）· 分 95.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high 且未上 LoRA：考虑 python3 skills/n2d-lora/scripts/lora.py init '/Users/wesley/learn/anime-arsenal/创作区/制漫剧/那妖魔是姜大人' --character-id CHAR_02 --form '濒死战损态'（事前升档，别等跨集漂了再补）。

## 🔴 姜月初（CHAR_01/囚犯初醒态）· 分 93.5
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high 且未上 LoRA：考虑 python3 skills/n2d-lora/scripts/lora.py init '/Users/wesley/learn/anime-arsenal/创作区/制漫剧/那妖魔是姜大人' --character-id CHAR_01 --form '囚犯初醒态'（事前升档，别等跨集漂了再补）。

## 🔴 虎山神 / 虎妖（CHAR_03/诈死复苏态）· 分 90.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high 且未上 LoRA：考虑 python3 skills/n2d-lora/scripts/lora.py init '/Users/wesley/learn/anime-arsenal/创作区/制漫剧/那妖魔是姜大人' --character-id CHAR_03 --form '诈死复苏态'（事前升档，别等跨集漂了再补）。

## 含人共享资产镜脸漂诊断（治诊断侧盲区·武器/道具/海报）
- 🔴 0 · 🟡 0 · 🟢 1
| 资产 | 脸策略 | 风险 | 主驱动 |
|---|---|---|---|
| `WEAPON_01`（weapon） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |


说明：🔴/🟡 是**出图前预测**（按建议提前加强参考/建表情库/上 LoRA）；⛔ 包含两类：n2d-identity 对已出图集**实测**到的跨集漂移回灌，或核心长线角在无持久主体后端上预测 high 且缺项目记忆/真实参考图束/分层合成/QC 执行计划。前者先处置漂移，后者先补执行计划或升档。（本次无可用实测数据：identity_drift_report 缺失或无 insightface，仅预测档生效。）
