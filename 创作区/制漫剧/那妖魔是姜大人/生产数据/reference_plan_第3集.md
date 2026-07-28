# 逐镜参考规划（治跨集脸漂）

- root: 创作区/制漫剧/那妖魔是姜大人
- episode: 第3集
- 生图后端: GPT Image 2（渠道 Codex CLI）（codex · 策略 multi_reference）
- 镜头数: 8 ｜ 弱后端×大变化镜: 8

> 定妆照对 AI 只是固定板式；本表按**每镜变化量 + 后端能力**给参考处方。建议侧车，人审后落进 `01_分镜出图.md`；gate 在 image_preflight 对账。

## 备注
- G3 多人同框：本集 5/8 镜多人同框，当前生图模型 GPT Image 2（渠道 Codex CLI）（非持久主体/reference-library 后端）。多人同框是 2026 崩脸/串脸高发区，若本剧群像/对手戏重，建议在选择点 `生图模型` 把**整项目**统一切到 reference-library 后端（Seedream Universal Reference / 可灵主体库 / Sora Character Cameo·官方多参考后端按官方口径最多约 14 张/保 5 人）。注意：勿逐镜换后端（=项目内模型混用，gate 会拦）；切则整项目切并重置后端主体/Face Lock 状态。（本集多人镜占比高，优先评估）

## 共享资产脸策略（含人资产镜·治规划侧脸漂盲区）
- `LOC_02`（scene）→ **faceless**：出图须背身/裁到下巴以下/无脸中性人台·禁清晰五官；落档像素核验 0 清晰脸。
- `WEAPON_01`（weapon）→ **faceless**：出图须背身/裁到下巴以下/无脸中性人台·禁清晰五官；落档像素核验 0 清晰脸。
- `WEAPON_横刀`（weapon）→ **faceless**：出图须背身/裁到下巴以下/无脸中性人台·禁清晰五官；落档像素核验 0 清晰脸。
- `LOC_01`（scene）→ **faceless**：出图须背身/裁到下巴以下/无脸中性人台·禁清晰五官；落档像素核验 0 清晰脸。
- `PROP_镇魔司制服`（prop）→ **faceless**：出图须背身/裁到下巴以下/无脸中性人台·禁清晰五官；落档像素核验 0 清晰脸。

## 建议升 LoRA（弱后端压不住的核心角）
- CHAR_01/“囚途残损态”、CHAR_01/镇魔司制服态

## 多人同框策略

> ① 分镜调度优先：`slots_required`=≥2 清晰具名同框必须登记槽位+策略；`large_same_frame_requires_strategy`=高人数同框建议拆组/分区；`split_or_layer_required`=多人近景必须反打/分层/分别出图；④ 锚点撞色=同框角色发色/服装主色雷同，逐主体补互斥 `区分锚点`。

| 镜头 | 模式 | 角色槽位 | 分镜调度 | 撞色 | prompt 必填 | 执行 |
|---|---|---|---|---|---|---|
| EP03_CLIP01 | regional_construct_required | CHAR_01/镇魔司制服态、CHAR_03/常态、GROUP_01/常态 | ⚠️slots_required | - | 多人同框身份槽位、多人同框执行策略、screen_positions/blocking、逐主体参考绑定、primary 星标具体注册角色ID*、区分锚点（互斥发色/服装主色/配饰）、空场景底板 empty_plate、区域遮罩/region masks、统一 relighting/color match、相对身量/身高比例（relative_scale） | 无持久角色 ID 后端：默认走空场景底板 empty_plate + 官方 inpaint / regional-prompt 分区构建；每个槽位只喂该角色自己的 reference_group / face_anchor_refs / expressions，逐区域生成后统一 relighting/color match。本模式等价硬执行 token：regional_construct_required + split_composite_required，不是条件式兜底。 |
| EP03_CLIP05 | regional_construct_required | CHAR_01/镇魔司制服态、CHAR_03/常态、GROUP_01/常态 | ⚠️slots_required | - | 多人同框身份槽位、多人同框执行策略、screen_positions/blocking、逐主体参考绑定、primary 星标具体注册角色ID*、区分锚点（互斥发色/服装主色/配饰）、空场景底板 empty_plate、区域遮罩/region masks、统一 relighting/color match、相对身量/身高比例（relative_scale） | 无持久角色 ID 后端：默认走空场景底板 empty_plate + 官方 inpaint / regional-prompt 分区构建；每个槽位只喂该角色自己的 reference_group / face_anchor_refs / expressions，逐区域生成后统一 relighting/color match。本模式等价硬执行 token：regional_construct_required + split_composite_required，不是条件式兜底。 |
| EP03_CLIP06 | regional_construct_required | CHAR_01/镇魔司制服态、CHAR_03/常态、GROUP_01/常态 | ⚠️split_or_layer_required | - | 多人同框身份槽位、多人同框执行策略、screen_positions/blocking、逐主体参考绑定、primary 星标具体注册角色ID*、区分锚点（互斥发色/服装主色/配饰）、空场景底板 empty_plate、区域遮罩/region masks、统一 relighting/color match、相对身量/身高比例（relative_scale） | 无持久角色 ID 后端：默认走空场景底板 empty_plate + 官方 inpaint / regional-prompt 分区构建；每个槽位只喂该角色自己的 reference_group / face_anchor_refs / expressions，逐区域生成后统一 relighting/color match。本模式等价硬执行 token：regional_construct_required + split_composite_required，不是条件式兜底。 |
| EP03_CLIP07 | regional_construct_required | CHAR_01/镇魔司制服态、CHAR_03/常态、GROUP_01/常态 | ⚠️slots_required | - | 多人同框身份槽位、多人同框执行策略、screen_positions/blocking、逐主体参考绑定、primary 星标具体注册角色ID*、区分锚点（互斥发色/服装主色/配饰）、空场景底板 empty_plate、区域遮罩/region masks、统一 relighting/color match、相对身量/身高比例（relative_scale） | 无持久角色 ID 后端：默认走空场景底板 empty_plate + 官方 inpaint / regional-prompt 分区构建；每个槽位只喂该角色自己的 reference_group / face_anchor_refs / expressions，逐区域生成后统一 relighting/color match。本模式等价硬执行 token：regional_construct_required + split_composite_required，不是条件式兜底。 |
| EP03_CLIP08 | regional_construct_required | CHAR_01/镇魔司制服态、GROUP_01/常态 | ⚠️split_or_layer_required | - | 多人同框身份槽位、多人同框执行策略、screen_positions/blocking、逐主体参考绑定、primary 星标具体注册角色ID*、区分锚点（互斥发色/服装主色/配饰）、空场景底板 empty_plate、区域遮罩/region masks、统一 relighting/color match、相对身量/身高比例（relative_scale） | 无持久角色 ID 后端：默认走空场景底板 empty_plate + 官方 inpaint / regional-prompt 分区构建；每个槽位只喂该角色自己的 reference_group / face_anchor_refs / expressions，逐区域生成后统一 relighting/color match。本模式等价硬执行 token：regional_construct_required + split_composite_required，不是条件式兜底。 |

> 喂法（后端能力路由）：分图分标镜 8、可喂视频参考镜 0。多参考后端喂**分离带标签图**而非拼 sheet；支持视频参考的后端对大表情/近景/原生主体注册可喂定妆视频/多帧。

## 逐镜处方

| 镜头 | 角色/形态 | 档位 | 变化量 | 推荐参考 | 喂法 | 预算 | 控制网 | 补拍缺口 | 升档 |
|---|---|---|---|---|---|---|---|---|---|
| EP03_CLIP01 | CHAR_01/镇魔司制服态 | multi_reference | closeup、extreme_angle:face_too_small、multi_character | front(0.8)<br>three_quarter(0.65)<br>face_anchor(0.7)<br>outfit(0.5)<br>expression(0.6)<br>turnaround(0.5) | 分图分标 | 6/不限 | pose、depth | - | ✅需升档 |
| EP03_CLIP01 | CHAR_03/常态 | multi_reference | closeup、extreme_angle:face_too_small、multi_character | front(0.8)<br>three_quarter(0.65)<br>face_anchor(0.7)<br>outfit(0.5)<br>expression(0.6) | 分图分标 | 5/不限 | pose、depth | - | - |
| EP03_CLIP01 | GROUP_01/常态 | multi_reference | closeup、extreme_angle:face_too_small、multi_character | outfit(0.5) | 单参考 | 1/不限 | pose、depth | 45°/three_quarter 角度参考（当前角色库档位=named_minimal，本镜实际需要）<br>脸部特写基础锚（所有角色/形态强制 ready）<br>脸部特写主参考 | - |
| EP03_CLIP02 | CHAR_01/“囚途残损态” | multi_reference | closeup | front(0.8)<br>three_quarter(0.65)<br>face_anchor(0.7)<br>outfit(0.5)<br>expression(0.6) | 分图分标 | 5/不限 | - | - | ✅需升档 |
| EP03_CLIP03 | CHAR_01/“囚途残损态” | multi_reference | closeup、extreme_angle:face_too_small | front(0.8)<br>three_quarter(0.65)<br>face_anchor(0.7)<br>outfit(0.5)<br>expression(0.6)<br>turnaround(0.5) | 分图分标 | 6/不限 | - | - | ✅需升档 |
| EP03_CLIP04 | CHAR_01/镇魔司制服态 | multi_reference | closeup、extreme_angle:face_too_small | front(0.8)<br>three_quarter(0.65)<br>face_anchor(0.7)<br>outfit(0.5)<br>expression(0.6)<br>turnaround(0.5) | 分图分标 | 6/不限 | - | - | ✅需升档 |
| EP03_CLIP05 | CHAR_01/镇魔司制服态 | multi_reference | extreme_angle:face_too_small、multi_character | front(0.8)<br>three_quarter(0.65)<br>face_anchor(0.7)<br>outfit(0.5)<br>turnaround(0.5) | 分图分标 | 5/不限 | pose、depth | - | ✅需升档 |
| EP03_CLIP05 | CHAR_03/常态 | multi_reference | extreme_angle:face_too_small、multi_character | front(0.8)<br>three_quarter(0.65)<br>face_anchor(0.7)<br>outfit(0.5) | 分图分标 | 4/不限 | pose、depth | - | - |
| EP03_CLIP05 | GROUP_01/常态 | multi_reference | extreme_angle:face_too_small、multi_character | outfit(0.5) | 单参考 | 1/不限 | pose、depth | 45°/three_quarter 角度参考（当前角色库档位=named_minimal，本镜实际需要）<br>脸部特写基础锚（所有角色/形态强制 ready） | - |
| EP03_CLIP06 | CHAR_01/镇魔司制服态 | multi_reference | closeup、multi_character | front(0.8)<br>three_quarter(0.65)<br>face_anchor(0.7)<br>outfit(0.5)<br>expression(0.6) | 分图分标 | 5/不限 | pose、depth | - | ✅需升档 |
| EP03_CLIP06 | CHAR_03/常态 | multi_reference | closeup、multi_character | front(0.8)<br>three_quarter(0.65)<br>face_anchor(0.7)<br>outfit(0.5)<br>expression(0.6) | 分图分标 | 5/不限 | pose、depth | - | - |
| EP03_CLIP06 | GROUP_01/常态 | multi_reference | closeup、multi_character | outfit(0.5) | 单参考 | 1/不限 | pose、depth | 45°/three_quarter 角度参考（当前角色库档位=named_minimal，本镜实际需要）<br>脸部特写基础锚（所有角色/形态强制 ready）<br>脸部特写主参考 | - |
| EP03_CLIP07 | CHAR_01/镇魔司制服态 | multi_reference | closeup、strong_emotion、extreme_angle:face_too_small、multi_character | front(0.8)<br>three_quarter(0.65)<br>face_anchor(0.7)<br>outfit(0.5)<br>expression(0.6)<br>turnaround(0.5) | 分图分标 | 6/不限 | pose、depth | - | ✅需升档 |
| EP03_CLIP07 | CHAR_03/常态 | multi_reference | closeup、strong_emotion、extreme_angle:face_too_small、multi_character | front(0.8)<br>three_quarter(0.65)<br>face_anchor(0.7)<br>outfit(0.5)<br>expression(0.6) | 分图分标 | 5/不限 | pose、depth | 情绪表情库（哭/怒/惊…起止表情；当前仅中性脸部特写或缺） | - |
| EP03_CLIP07 | GROUP_01/常态 | multi_reference | closeup、strong_emotion、extreme_angle:face_too_small、multi_character | outfit(0.5) | 单参考 | 1/不限 | pose、depth | 45°/three_quarter 角度参考（当前角色库档位=named_minimal，本镜实际需要）<br>脸部特写基础锚（所有角色/形态强制 ready）<br>情绪表情库（哭/怒/惊…起止表情；当前仅中性脸部特写或缺） | - |
| EP03_CLIP08 | CHAR_01/镇魔司制服态 | multi_reference | closeup、strong_emotion、extreme_angle:extreme_low、multi_character | front(0.8)<br>three_quarter(0.65)<br>face_anchor(0.7)<br>outfit(0.5)<br>expression(0.6)<br>side(0.55) | 分图分标 | 6/不限 | pose、depth | - | ✅需升档 |
| EP03_CLIP08 | GROUP_01/常态 | multi_reference | closeup、strong_emotion、extreme_angle:extreme_low、multi_character | outfit(0.5) | 单参考 | 1/不限 | pose、depth | 45°/three_quarter 角度参考（当前角色库档位=named_minimal，本镜实际需要）<br>脸部特写基础锚（所有角色/形态强制 ready）<br>情绪表情库（哭/怒/惊…起止表情；当前仅中性脸部特写或缺）<br>侧脸参考（极端角度/转头镜） | - |

## 行动项（人审后落进 prompt）
- [EP03_CLIP01] CHAR_01/镇魔司制服态：弱后端×核心长线角×大变化镜：建议升档——注册原生主体(Seedream/可灵/Sora)；仍压不住则 `python3 skills/n2d-lora/scripts/lora.py init <作品根> --character-id CHAR_01 --form '镇魔司制服态'`
- [EP03_CLIP01] GROUP_01/常态：补拍：45°/three_quarter 角度参考（当前角色库档位=named_minimal，本镜实际需要）；脸部特写基础锚（所有角色/形态强制 ready）；脸部特写主参考
- [EP03_CLIP01] 多人同框：regional_construct_required；角色槽位=CHAR_01/镇魔司制服态、CHAR_03/常态、GROUP_01/常态；必填=多人同框身份槽位、多人同框执行策略、screen_positions/blocking、逐主体参考绑定、primary 星标具体注册角色ID*、区分锚点（互斥发色/服装主色/配饰）、空场景底板 empty_plate、区域遮罩/region masks、统一 relighting/color match、相对身量/身高比例（relative_scale）；无持久角色 ID 后端：默认走空场景底板 empty_plate + 官方 inpaint / regional-prompt 分区构建；每个槽位只喂该角色自己的 reference_group / face_anchor_refs / expressions，逐区域生成后统一 relighting/color match。本模式等价硬执行 token：regional_construct_required + split_composite_required，不是条件式兜底。
- [EP03_CLIP02] CHAR_01/“囚途残损态”：弱后端×核心长线角×大变化镜：建议升档——注册原生主体(Seedream/可灵/Sora)；仍压不住则 `python3 skills/n2d-lora/scripts/lora.py init <作品根> --character-id CHAR_01 --form '“囚途残损态”'`
- [EP03_CLIP03] CHAR_01/“囚途残损态”：弱后端×核心长线角×大变化镜：建议升档——注册原生主体(Seedream/可灵/Sora)；仍压不住则 `python3 skills/n2d-lora/scripts/lora.py init <作品根> --character-id CHAR_01 --form '“囚途残损态”'`
- [EP03_CLIP04] CHAR_01/镇魔司制服态：弱后端×核心长线角×大变化镜：建议升档——注册原生主体(Seedream/可灵/Sora)；仍压不住则 `python3 skills/n2d-lora/scripts/lora.py init <作品根> --character-id CHAR_01 --form '镇魔司制服态'`
- [EP03_CLIP05] CHAR_01/镇魔司制服态：弱后端×核心长线角×大变化镜：建议升档——注册原生主体(Seedream/可灵/Sora)；仍压不住则 `python3 skills/n2d-lora/scripts/lora.py init <作品根> --character-id CHAR_01 --form '镇魔司制服态'`
- [EP03_CLIP05] GROUP_01/常态：补拍：45°/three_quarter 角度参考（当前角色库档位=named_minimal，本镜实际需要）；脸部特写基础锚（所有角色/形态强制 ready）
- [EP03_CLIP05] 多人同框：regional_construct_required；角色槽位=CHAR_01/镇魔司制服态、CHAR_03/常态、GROUP_01/常态；必填=多人同框身份槽位、多人同框执行策略、screen_positions/blocking、逐主体参考绑定、primary 星标具体注册角色ID*、区分锚点（互斥发色/服装主色/配饰）、空场景底板 empty_plate、区域遮罩/region masks、统一 relighting/color match、相对身量/身高比例（relative_scale）；无持久角色 ID 后端：默认走空场景底板 empty_plate + 官方 inpaint / regional-prompt 分区构建；每个槽位只喂该角色自己的 reference_group / face_anchor_refs / expressions，逐区域生成后统一 relighting/color match。本模式等价硬执行 token：regional_construct_required + split_composite_required，不是条件式兜底。
- [EP03_CLIP06] CHAR_01/镇魔司制服态：弱后端×核心长线角×大变化镜：建议升档——注册原生主体(Seedream/可灵/Sora)；仍压不住则 `python3 skills/n2d-lora/scripts/lora.py init <作品根> --character-id CHAR_01 --form '镇魔司制服态'`
- [EP03_CLIP06] GROUP_01/常态：补拍：45°/three_quarter 角度参考（当前角色库档位=named_minimal，本镜实际需要）；脸部特写基础锚（所有角色/形态强制 ready）；脸部特写主参考
- [EP03_CLIP06] 多人同框：regional_construct_required；角色槽位=CHAR_01/镇魔司制服态、CHAR_03/常态、GROUP_01/常态；必填=多人同框身份槽位、多人同框执行策略、screen_positions/blocking、逐主体参考绑定、primary 星标具体注册角色ID*、区分锚点（互斥发色/服装主色/配饰）、空场景底板 empty_plate、区域遮罩/region masks、统一 relighting/color match、相对身量/身高比例（relative_scale）；无持久角色 ID 后端：默认走空场景底板 empty_plate + 官方 inpaint / regional-prompt 分区构建；每个槽位只喂该角色自己的 reference_group / face_anchor_refs / expressions，逐区域生成后统一 relighting/color match。本模式等价硬执行 token：regional_construct_required + split_composite_required，不是条件式兜底。
- [EP03_CLIP07] CHAR_01/镇魔司制服态：弱后端×核心长线角×大变化镜：建议升档——注册原生主体(Seedream/可灵/Sora)；仍压不住则 `python3 skills/n2d-lora/scripts/lora.py init <作品根> --character-id CHAR_01 --form '镇魔司制服态'`
- [EP03_CLIP07] CHAR_03/常态：补拍：情绪表情库（哭/怒/惊…起止表情；当前仅中性脸部特写或缺）
- [EP03_CLIP07] GROUP_01/常态：补拍：45°/three_quarter 角度参考（当前角色库档位=named_minimal，本镜实际需要）；脸部特写基础锚（所有角色/形态强制 ready）；情绪表情库（哭/怒/惊…起止表情；当前仅中性脸部特写或缺）
- [EP03_CLIP07] 多人同框：regional_construct_required；角色槽位=CHAR_01/镇魔司制服态、CHAR_03/常态、GROUP_01/常态；必填=多人同框身份槽位、多人同框执行策略、screen_positions/blocking、逐主体参考绑定、primary 星标具体注册角色ID*、区分锚点（互斥发色/服装主色/配饰）、空场景底板 empty_plate、区域遮罩/region masks、统一 relighting/color match、相对身量/身高比例（relative_scale）；无持久角色 ID 后端：默认走空场景底板 empty_plate + 官方 inpaint / regional-prompt 分区构建；每个槽位只喂该角色自己的 reference_group / face_anchor_refs / expressions，逐区域生成后统一 relighting/color match。本模式等价硬执行 token：regional_construct_required + split_composite_required，不是条件式兜底。
- [EP03_CLIP08] CHAR_01/镇魔司制服态：弱后端×核心长线角×大变化镜：建议升档——注册原生主体(Seedream/可灵/Sora)；仍压不住则 `python3 skills/n2d-lora/scripts/lora.py init <作品根> --character-id CHAR_01 --form '镇魔司制服态'`
- [EP03_CLIP08] GROUP_01/常态：补拍：45°/three_quarter 角度参考（当前角色库档位=named_minimal，本镜实际需要）；脸部特写基础锚（所有角色/形态强制 ready）；情绪表情库（哭/怒/惊…起止表情；当前仅中性脸部特写或缺）；侧脸参考（极端角度/转头镜）
- [EP03_CLIP08] 多人同框：regional_construct_required；角色槽位=CHAR_01/镇魔司制服态、GROUP_01/常态；必填=多人同框身份槽位、多人同框执行策略、screen_positions/blocking、逐主体参考绑定、primary 星标具体注册角色ID*、区分锚点（互斥发色/服装主色/配饰）、空场景底板 empty_plate、区域遮罩/region masks、统一 relighting/color match、相对身量/身高比例（relative_scale）；无持久角色 ID 后端：默认走空场景底板 empty_plate + 官方 inpaint / regional-prompt 分区构建；每个槽位只喂该角色自己的 reference_group / face_anchor_refs / expressions，逐区域生成后统一 relighting/color match。本模式等价硬执行 token：regional_construct_required + split_composite_required，不是条件式兜底。
