# 出图前·脸漂风险分（事前预测 + 实测漂移回灌）

- episode: 第1集 · 默认后端: dreamina
- ⛔ 阻断 0 · 🔴 预测高危 2 · 🟡 中危 0

| 角色 | 风险 | 分 | 锁脸档 | 主驱动 |
|---|---|---|---|---|
| 张老大（CHAR_02/常态） | 🔴 high | 84.0 | multi_reference | 近景占比 3/3(+30.0)；锁脸档位=multi_reference(+22)；多人同框 3/3(+20.0) |
| 贺平生（CHAR_01/本集为14岁杂役常态） | 🔴 high | 68.3 | multi_reference | 近景占比 6/7(+25.7)；锁脸档位=multi_reference(+22)；极端角度 2 镜(+12) |

## 🔴 张老大（CHAR_02/常态）· 分 84.0
- 即梦图像模型 Seedream 系（渠道 Dreamina/即梦官方 CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- Dreamina/即梦参考框有粘性：切换角色前清空参考图；场景定妆必须清空人物参考。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high：默认先走 image2image / 多图参考链补强（脸部特写、同源表情库、逐主体真实图片入参、full image_qc）；只有已有快速本机加速或明确云训路径时，才把 LoRA 作为可选升档，不把慢速本机训练当出图前置。

## 🔴 贺平生（CHAR_01/本集为14岁杂役常态）· 分 68.3
- 已补 ready 的同源表情参考：Codex-only 仍按 high 风险进入逐镜多参考 + split_composite + full image_qc 回验，不再因预测 high 在 preflight 阶段硬阻断。
- 即梦图像模型 Seedream 系（渠道 Dreamina/即梦官方 CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- Dreamina/即梦参考框有粘性：切换角色前清空参考图；场景定妆必须清空人物参考。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high：默认先走 image2image / 多图参考链补强（脸部特写、同源表情库、逐主体真实图片入参、full image_qc）；只有已有快速本机加速或明确云训路径时，才把 LoRA 作为可选升档，不把慢速本机训练当出图前置。

## 含人共享资产镜脸漂诊断（治诊断侧盲区·武器/道具/海报）
- 🔴 0 · 🟡 0 · 🟢 8
| 资产 | 脸策略 | 风险 | 主驱动 |
|---|---|---|---|
| `LOC_01`（scene） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_木牌`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `LOC_02`（scene） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_旧布包`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_扁担`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_水桶`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `LOC_03`（scene） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_01`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |


说明：🔴/🟡 是**出图前预测**（按建议提前加强参考、建表情库、走 image2image/多图参考链；LoRA 只在快速/云训路径明确时作为可选升档）；⛔ 包含两类：n2d-identity 对已出图集**实测**到的跨集漂移回灌，或核心长线角在无持久主体后端上预测 high 且缺项目记忆/真实参考图束/分层合成/QC 执行计划。前者先处置漂移，后者先补执行计划或升档。（本次无可用实测数据：identity_drift_report 缺失或无 insightface，仅预测档生效。）
