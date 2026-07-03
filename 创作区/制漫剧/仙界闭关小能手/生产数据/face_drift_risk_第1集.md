# 出图前·脸漂风险分（事前预测 + 实测漂移回灌）

- episode: 第1集 · 默认后端: codex
- ⛔ 阻断 0 · 🔴 预测高危 3 · 🟡 中危 2

| 角色 | 风险 | 分 | 锁脸档 | 主驱动 |
|---|---|---|---|---|
| 张老大（CHAR_ZHANG_LAODA/常态） | 🔴 high | 80.0 | multi_reference | 极端角度 4 镜(+24)；锁脸档位=multi_reference(+22)；近景占比 4/6(+20.0) |
| 贺平生（CHAR_HE_PINGSHENG/常态） | 🔴 high | 67.9 | multi_reference | 极端角度 7 镜(+24)；锁脸档位=multi_reference(+22)；近景占比 13/24(+16.2) |
| 群杂役（CROWD_ZAYI/虚化） | 🔴 high | 66.0 | multi_reference | 近景占比 2/2(+30.0)；锁脸档位=multi_reference(+22)；多人同框 2/2(+20.0) |
| 韩老三（CHAR_HAN_LAOSAN/常态） | 🟡 medium | 54.0 | multi_reference | 锁脸档位=multi_reference(+22)；多人同框 4/4(+20.0)；极端角度 3 镜(+18) |
| 江剑（CHAR_JIANG_JIAN/背影） | 🟡 medium | 36.0 | multi_reference | 锁脸档位=multi_reference(+22)；多人同框 2/2(+20.0)；同源场景 in-context 记功(strong·如 GPT Image 2)(+-6) |

## 🔴 张老大（CHAR_ZHANG_LAODA/常态）· 分 80.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high 且未上 LoRA：考虑 python3 skills/n2d-lora/scripts/lora.py init '/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手' --character-id CHAR_ZHANG_LAODA --form '常态'（事前升档，别等跨集漂了再补）。

## 🔴 贺平生（CHAR_HE_PINGSHENG/常态）· 分 67.9
- 已补 ready 的同源表情参考：Codex-only 仍按 high 风险进入逐镜多参考 + split_composite + full image_qc 回验，不再因预测 high 在 preflight 阶段硬阻断。
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high 且未上 LoRA：考虑 python3 skills/n2d-lora/scripts/lora.py init '/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手' --character-id CHAR_HE_PINGSHENG --form '常态'（事前升档，别等跨集漂了再补）。

## 🔴 群杂役（CROWD_ZAYI/虚化）· 分 66.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 风险 high 且未上 LoRA：考虑 python3 skills/n2d-lora/scripts/lora.py init '/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手' --character-id CROWD_ZAYI --form '虚化'（事前升档，别等跨集漂了再补）。
- 基础定妆包缺 ready 的 3/4 侧脸参考：补 `reference_atlas.base_views.three_quarter`（45°/三分之二侧脸）并出图标 ready——45° 是全员基础角，不再按近景占比或角色体量延后。

## 🟡 韩老三（CHAR_HAN_LAOSAN/常态）· 分 54.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。

## 🟡 江剑（CHAR_JIANG_JIAN/背影）· 分 36.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 基础定妆包缺 ready 的 3/4 侧脸参考：补 `reference_atlas.base_views.three_quarter`（45°/三分之二侧脸）并出图标 ready——45° 是全员基础角，不再按近景占比或角色体量延后。

## 含人共享资产镜脸漂诊断（治诊断侧盲区·武器/道具/海报）
- 🔴 0 · 🟡 0 · 🟢 7
| 资产 | 脸策略 | 风险 | 主驱动 |
|---|---|---|---|
| `PROP_XIUZHEN_ZIYUAN`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_WATER_JARS`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_KEY_LOCK`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_TIE_WAN`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_SHUI_TONG`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_BIAN_DAN`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |
| `PROP_HEI_TAO_PEN`（prop） | faceless | 🟢 low | faceless·须背身/裁脸·落档像素验 0 清晰脸 |


说明：🔴/🟡 是**出图前预测**（按建议提前加强参考/建表情库/上 LoRA）；⛔ 包含两类：n2d-identity 对已出图集**实测**到的跨集漂移回灌，或核心长线角在无持久主体后端上预测 high 且缺项目记忆/真实参考图束/分层合成/QC 执行计划。前者先处置漂移，后者先补执行计划或升档。
