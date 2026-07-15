# 出图前·脸漂风险分（事前预测 + 实测漂移回灌）

- episode: 第1集 · 默认后端: codex
- ⛔ 阻断 0 · 🔴 预测高危 0 · 🟡 中危 2

| 角色 | 风险 | 分 | 锁脸档 | 主驱动 |
|---|---|---|---|---|
| 姜月初（CHAR_01/常态） | 🟡 medium | 44.0 | multi_reference | 锁脸档位=multi_reference(+22)；多人同框 7/7(+20.0)；大表情 1 镜(+8) |
| 裴长青（CHAR_02/常态） | 🟡 medium | 39.6 | multi_reference | 锁脸档位=multi_reference(+22)；多人同框 7/9(+15.6)；大表情 1 镜(+8) |
| 虎山神（CHAR_04/常态） | 🟢 low | 16.0 | multi_reference | 锁脸档位=multi_reference(+22)；同源场景 in-context 记功(strong·如 GPT Image 2)(+-6) |

## 🟡 姜月初（CHAR_01/常态）· 分 44.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 当前角色库档位=core_full 且本档/本集镜头需要 3/4 侧脸：补 `reference_atlas.base_views.three_quarter`（45°/三分之二侧脸）并出图标 ready。

## 🟡 裴长青（CHAR_02/常态）· 分 39.6
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 当前角色库档位=named_minimal 且本档/本集镜头需要 3/4 侧脸：补 `reference_atlas.base_views.three_quarter`（45°/三分之二侧脸）并出图标 ready。

## 含人共享资产镜脸漂诊断（治诊断侧盲区·武器/道具/海报）
- 🔴 0 · 🟡 0 · 🟢 10
| 资产 | 脸策略 | 风险 | 主驱动 |
|---|---|---|---|
| `LOC_01`（scene） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `WEAPON_01`（weapon） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_横刀`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_断刀`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_翻覆囚车`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `VFX_百妖谱`（vfx） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `VFX_道行灌注`（vfx） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_虎首`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `VFX_黑妖血`（vfx） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `VFX_道行反噬`（vfx） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |


说明：🔴/🟡 是**出图前预测**（按建议提前加强参考、建表情库、走 image2image/多图参考链；LoRA 只在快速/云训路径明确时作为可选升档）；⛔ 包含两类：n2d-identity 对已出图集**实测**到的跨集漂移回灌，或核心长线角在无持久主体后端上预测 high 且缺项目记忆/真实参考图束/分层合成/QC 执行计划。前者先处置漂移，后者先补执行计划或升档。（本次无可用实测数据：identity_drift_report 缺失或无 insightface，仅预测档生效。）
