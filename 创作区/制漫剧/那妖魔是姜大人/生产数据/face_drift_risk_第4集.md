# 出图前·脸漂风险分（事前预测 + 实测漂移回灌）

- episode: 第4集 · 默认后端: codex
- ⛔ 阻断 0 · 🔴 预测高危 4 · 🟡 中危 0

| 角色 | 风险 | 分 | 锁脸档 | 主驱动 |
|---|---|---|---|---|
| 陈青源（CHAR_04/常态） | 🔴 high | 100.0 | multi_reference | 近景占比 5/6(+25.0)；极端角度 6 镜(+24)；锁脸档位=multi_reference(+22) |
| 姜月初（CHAR_01/囚犯初醒态） | 🔴 high | 99.7 | multi_reference | 近景占比 7/8(+26.2)；极端角度 7 镜(+24)；锁脸档位=multi_reference(+22) |
| 青面郎君（CHAR_05/常态） | 🔴 high | 84.0 | multi_reference | 近景占比 4/4(+30.0)；锁脸档位=multi_reference(+22)；大表情 2 镜(+16) |
| 虎山神 / 虎妖（CHAR_03/诈死复苏态） | 🔴 high | 72.0 | multi_reference | 近景占比 1/1(+30.0)；锁脸档位=multi_reference(+22)；多人同框 1/1(+20.0) |

## 🔴 陈青源（CHAR_04/常态）· 分 100.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 大表情镜多：必建表情库 expressions + 脸部特写参考，首尾双帧只插值（对齐 image_qc no_expression_lib_ref）。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high：默认先走 image2image / 多图参考链补强（脸部特写、同源表情库、逐主体真实图片入参、full image_qc）；只有已有快速本机加速或明确云训路径时，才把 LoRA 作为可选升档，不把慢速本机训练当出图前置。

## 🔴 姜月初（CHAR_01/囚犯初醒态）· 分 99.7
- 已补 ready 的同源表情参考：Codex-only 仍按 high 风险进入逐镜多参考 + split_composite + full image_qc 回验，不再因预测 high 在 preflight 阶段硬阻断。
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 大表情镜多：必建表情库 expressions + 脸部特写参考，首尾双帧只插值（对齐 image_qc no_expression_lib_ref）。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high：默认先走 image2image / 多图参考链补强（脸部特写、同源表情库、逐主体真实图片入参、full image_qc）；只有已有快速本机加速或明确云训路径时，才把 LoRA 作为可选升档，不把慢速本机训练当出图前置。

## 🔴 青面郎君（CHAR_05/常态）· 分 84.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 大表情镜多：必建表情库 expressions + 脸部特写参考，首尾双帧只插值（对齐 image_qc no_expression_lib_ref）。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high：默认先走 image2image / 多图参考链补强（脸部特写、同源表情库、逐主体真实图片入参、full image_qc）；只有已有快速本机加速或明确云训路径时，才把 LoRA 作为可选升档，不把慢速本机训练当出图前置。

## 🔴 虎山神 / 虎妖（CHAR_03/诈死复苏态）· 分 72.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high：默认先走 image2image / 多图参考链补强（脸部特写、同源表情库、逐主体真实图片入参、full image_qc）；只有已有快速本机加速或明确云训路径时，才把 LoRA 作为可选升档，不把慢速本机训练当出图前置。

## 含人共享资产镜脸漂诊断（治诊断侧盲区·武器/道具/海报）
- 🔴 0 · 🟡 0 · 🟢 11
| 资产 | 脸策略 | 风险 | 主驱动 |
|---|---|---|---|
| `LOC_01`（scene） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_尸场物资包`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `LOC_02`（scene） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `LOC_03`（scene） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `WEAPON_01`（weapon） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_镇魔司黑衣赤纹`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `MOUNT_GROUP_01`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_上盘村断石碑`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_村道血迹破布`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_木架残肢剪影`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `VFX_狼爪寒光`（vfx） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |


说明：🔴/🟡 是**出图前预测**（按建议提前加强参考、建表情库、走 image2image/多图参考链；LoRA 只在快速/云训路径明确时作为可选升档）；⛔ 包含两类：n2d-identity 对已出图集**实测**到的跨集漂移回灌，或核心长线角在无持久主体后端上预测 high 且缺项目记忆/真实参考图束/分层合成/QC 执行计划。前者先处置漂移，后者先补执行计划或升档。（本次无可用实测数据：identity_drift_report 缺失或无 insightface，仅预测档生效。）
