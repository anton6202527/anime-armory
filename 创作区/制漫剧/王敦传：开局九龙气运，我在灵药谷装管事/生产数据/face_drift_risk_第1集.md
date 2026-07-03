# 出图前·脸漂风险分（事前预测 + 实测漂移回灌）

- episode: 第1集 · 默认后端: codex
- ⛔ 阻断 1 · 🔴 预测高危 2 · 🟡 中危 1

| 角色 | 风险 | 分 | 锁脸档 | 主驱动 |
|---|---|---|---|---|
| 王敦（CHAR_WANG_DUN/常态） | ⛔ block | 80.3 | multi_reference | 预测阻断（缺项目记忆/参考图束执行计划）｜近景占比 22/27(+24.4)；锁脸档位=multi_reference(+22)；极端角度 3 镜(+18) |
| 狱卒乙（CHAR_JAILER_B/常态） | 🔴 high | 66.0 | multi_reference | 近景占比 1/1(+30.0)；锁脸档位=multi_reference(+22)；多人同框 1/1(+20.0) |
| 小六子（CHAR_XIAO_LIUZI/常态） | 🔴 high | 60.0 | multi_reference | 锁脸档位=multi_reference(+22)；多人同框 6/7(+17.1)；近景占比 3/7(+12.9) |
| 狱卒甲（CHAR_JAILER_A/常态） | 🟡 medium | 36.0 | multi_reference | 锁脸档位=multi_reference(+22)；多人同框 1/1(+20.0)；同源场景 in-context 记功(strong·如 GPT Image 2)(+-6) |

## ⛔ 王敦（CHAR_WANG_DUN/常态）· 分 80.3
- ⛔ 预测高危已升级为阻断：先切到持久主体后端，或写齐项目记忆路线（真实参考图束/脸部锚/分层或反打/actual image input manifest/full QC），也可补 face_embedding/主体库/LoRA/同源表情库后重跑 preflight。
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 大表情镜多：必建表情库 expressions + 脸部特写参考，首尾双帧只插值（对齐 image_qc no_expression_lib_ref）。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high 且未上 LoRA：考虑 python3 skills/n2d-lora/scripts/lora.py init '/Users/lalala/learn/anime-armory/创作区/制漫剧/王敦传：开局九龙气运，我在灵药谷装管事' --character-id CHAR_WANG_DUN --form '常态'（事前升档，别等跨集漂了再补）。

## 🔴 狱卒乙（CHAR_JAILER_B/常态）· 分 66.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。
- 风险 high 且未上 LoRA：考虑 python3 skills/n2d-lora/scripts/lora.py init '/Users/lalala/learn/anime-armory/创作区/制漫剧/王敦传：开局九龙气运，我在灵药谷装管事' --character-id CHAR_JAILER_B --form '常态'（事前升档，别等跨集漂了再补）。

## 🔴 小六子（CHAR_XIAO_LIUZI/常态）· 分 60.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
- 近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。
- 多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。
- 极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。
- 风险 high 且未上 LoRA：考虑 python3 skills/n2d-lora/scripts/lora.py init '/Users/lalala/learn/anime-armory/创作区/制漫剧/王敦传：开局九龙气运，我在灵药谷装管事' --character-id CHAR_XIAO_LIUZI --form '常态'（事前升档，别等跨集漂了再补）。

## 🟡 狱卒甲（CHAR_JAILER_A/常态）· 分 36.0
- GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。


说明：🔴/🟡 是**出图前预测**（按建议提前加强参考/建表情库/上 LoRA）；⛔ 包含两类：n2d-identity 对已出图集**实测**到的跨集漂移回灌，或核心长线角在无持久主体后端上预测 high 且缺项目记忆/真实参考图束/分层合成/QC 执行计划。前者先处置漂移，后者先补执行计划或升档。（本次无可用实测数据：identity_drift_report 缺失或无 insightface，仅预测档生效。）
