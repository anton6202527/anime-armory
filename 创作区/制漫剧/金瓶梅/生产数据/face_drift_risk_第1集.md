# 出图前·脸漂风险分（事前预测 + 实测漂移回灌）

- episode: 第1集 · 默认后端: codex
- ⛔ 阻断 0 · 🔴 预测高危 3 · 🟡 中危 1

| 角色 | 风险 | 分 | 锁脸档 | 主驱动 |
|---|---|---|---|---|
| 武松（CHAR_WUSONG/28岁打虎态） | 🔴 high | 80.0 | multi_reference | 大表情 4 镜(+24)；极端角度 4 镜(+24)；锁脸档位=multi_reference(+22) |
| 武大（CHAR_WUDA/日常卖饼态） | 🔴 high | 72.0 | multi_reference | 大表情 3 镜(+24)；锁脸档位=multi_reference(+22)；多人同框 11/11(+20.0) |
| 潘金莲（CHAR_PANJINLIAN/25岁武大家常态） | 🔴 high | 58.0 | multi_reference | 锁脸档位=multi_reference(+22)；多人同框 7/7(+20.0)；大表情 2 镜(+16) |
| 知县（CHAR_MAGISTRATE/常态） | 🟡 medium | 36.0 | multi_reference | 锁脸档位=multi_reference(+22)；多人同框 1/1(+20.0)；同源场景 in-context 记功(strong·如 GPT Image 2)(+-6) |

## 🔴 武松（CHAR_WUSONG/28岁打虎态）· 分 80.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 大表情镜多：必建表情库 expressions + 脸部特写参考，首尾双帧只插值（对齐 image_qc no_expression_lib_ref）。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high：默认先走 image2image / 多图参考链补强（脸部特写、同源表情库、逐主体真实图片入参、full image_qc）；只有已有快速本机加速或明确云训路径时，才把 LoRA 作为可选升档，不把慢速本机训练当出图前置。
- 当前角色库档位=core_full 且本档/本集镜头需要 3/4 侧脸：补 `reference_atlas.base_views.three_quarter`（45°/三分之二侧脸）并出图标 ready。

## 🔴 武大（CHAR_WUDA/日常卖饼态）· 分 72.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 大表情镜多：必建表情库 expressions + 脸部特写参考，首尾双帧只插值（对齐 image_qc no_expression_lib_ref）。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high：默认先走 image2image / 多图参考链补强（脸部特写、同源表情库、逐主体真实图片入参、full image_qc）；只有已有快速本机加速或明确云训路径时，才把 LoRA 作为可选升档，不把慢速本机训练当出图前置。
- 当前角色库档位=recurring_standard 且本档/本集镜头需要 3/4 侧脸：补 `reference_atlas.base_views.three_quarter`（45°/三分之二侧脸）并出图标 ready。

## 🔴 潘金莲（CHAR_PANJINLIAN/25岁武大家常态）· 分 58.0
- 已写明项目记忆/真实参考图束路线：当前后端仍无持久主体 ID，但不再因这一点自动阻断。后续必须先生成共享定妆和脸部锚，再让执行端把这些 PNG 作为真实图片入参传入，并以 full image_qc 回验。
- 注意：这不是官方服务端 subject_id；若 codex_reference_bundles 出现 actual image inputs=0、missing_ready_refs 未清零或多人同框未按分层/反打执行，仍应在 image_preflight/image 阶段阻断。
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 大表情镜多：必建表情库 expressions + 脸部特写参考，首尾双帧只插值（对齐 image_qc no_expression_lib_ref）。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high：默认先走 image2image / 多图参考链补强（脸部特写、同源表情库、逐主体真实图片入参、full image_qc）；只有已有快速本机加速或明确云训路径时，才把 LoRA 作为可选升档，不把慢速本机训练当出图前置。
- 当前角色库档位=core_full 且本档/本集镜头需要 3/4 侧脸：补 `reference_atlas.base_views.three_quarter`（45°/三分之二侧脸）并出图标 ready。

## 🟡 知县（CHAR_MAGISTRATE/常态）· 分 36.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。

## 含人共享资产镜脸漂诊断（治诊断侧盲区·武器/道具/海报）
- 🔴 0 · 🟡 0 · 🟢 24
| 资产 | 脸策略 | 风险 | 主驱动 |
|---|---|---|---|
| `LOC_JINGYANGGANG`（scene） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_QUARTERSTAFF`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_BADGE`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_REWARD_SILVER`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `LOC_YANGGU_STREET`（scene） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_CAKE_POLE`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_WINDOW_LATTICE`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `LOC_WUDA_HOME`（scene） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_STAIR_RAIL`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_DINING_TABLE`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_TEA_CUP`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_DOORFRAME`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_DOOR_LATCH`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_BRAZIER`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_WINE_CUP`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_SPILLED_WINE`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_LUGGAGE`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_DOOR`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `LOC_COUNTY_YAMEN`（scene） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_OFFICIAL_DOC`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_GIFT_LOAD`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `LOC_CITY_GATE`（scene） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_WINDOW_CURTAIN`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_CURTAIN_FORK`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |


说明：🔴/🟡 是**出图前预测**（按建议提前加强参考、建表情库、走 image2image/多图参考链；LoRA 只在快速/云训路径明确时作为可选升档）；⛔ 包含两类：n2d-identity 对已出图集**实测**到的跨集漂移回灌，或核心长线角在无持久主体后端上预测 high 且缺项目记忆/真实参考图束/分层合成/QC 执行计划。前者先处置漂移，后者先补执行计划或升档。
