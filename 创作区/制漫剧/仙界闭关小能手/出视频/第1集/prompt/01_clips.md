# 第1集 视频分镜 Prompt

说明：本文件由当前 storyboard、video_model_routes、director_camera_plan、identity_adapter_matrix 生成；12 个 Clip 与 video_preflight 拆分后的故事板一一对应。

## Clip 01（时长 8.5s · EP01_CLIP01 · 黑殿审问上）

**首帧**：`出图/第1集/图片/Clip01_黑殿审问.png`
**尾帧**：`出图/第1集/图片/Clip01_黑殿审问_mid.png`
**中段锚帧豁免**：本 Clip 是视频 preflight 按原中段锚帧拆出的短半段；旧中帧已作为段边界尾帧/首帧复用，内部不再新增中段锚帧。
**场景**：秀竹峰杂役大殿/夜/内
**导演意图**：定场镜用升降建立地理和权力关系，不抢人物表演。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在LS/ELS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：shot_reverse_shot；多人同框执行策略：shot_reverse_shot_or_split_composite_required；清晰正脸不超过一人，群杂役只作后景虚化。；守张老大→贺平生横轴；反打不交换左右站位。
**表演节拍**：[0-4s] 黑暗大殿中贺平生被审问。（全景·慢推）；[4-8.5s] 张老大问年龄，贺平生低头回答。（中近景反打）；微表情/表情幅度：贺平生：起 AU4轻压眉+AU24抿唇，止 AU5轻抬眼后迅速垂下；张老大：起漫不经心，止嘴角嘲笑。
**三轨音频**：旁白音频后期 compose 叠加；视频生成阶段不要生成旁白音频，只允许画内角色对白口型。
**三轨修补**：屏幕文案（后期overlay）：十四岁 · 五行灵根；不得让视频模型生成文字，compose 阶段叠清晰字。
**运动精修**：张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。；身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：门缝冷光、屋顶漏光和殿内尘雾随人物呼吸轻微变化，背景杂役只作暗影虚化。
**涉及资产**：LOC_ZAYI_DADIAN

**专项镜头模板**：template_id=dialogue_shot_reverse；beats=张老大审问年龄；贺平生低头回答；张老大问灵根；群杂役哄笑；blocking=贺平生画左下，张老大画右前景，群杂役后景围压。；camera_rule=守张老大→贺平生横轴；反打不交换左右站位。；continuity_must=贺平生始终少年瘦削；张老大画右压迫；大殿低冷光不跳；negative=不要跳轴；不要新增仙门长老正脸；不要把杂役大殿画成仙宫；axis=张老大→贺平生横轴；eyeline=贺平生看画右上，张老大看画左下；shot_pairing=张老大 MS/CU 反打贺平生 CU，群杂役只作后景笑影。

**模型路由**：shot_type=dialogue_shot_reverse; clip_characters=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; policy_resolution.winner=native_voice_fallback; risk_flags=mouth_visible, multi_person, native_speech, seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

**动作编排契约 / Action Choreography**：无。

**Motion Control / 物理交互控制**：无。

**角色身份注册层**：
- CHAR_HE_PINGSHENG（贺平生）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_贺平生.png; 出图/共享/图片/定妆_贺平生_侧.png; 出图/共享/图片/定妆_贺平生_背.png; 出图/共享/图片/定妆_贺平生_半身.png; 出图/共享/图片/定妆_贺平生_三视图.png; 出图/共享/图片/定妆_贺平生_脸部特写.png; 出图/共享/图片/定妆_贺平生_表情_克制.png; 出图/共享/图片/定妆_贺平生_表情_疲惫隐忍.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CHAR_ZHANG_LAODA（张老大）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_张老大.png; 出图/共享/图片/定妆_张老大_侧.png; 出图/共享/图片/定妆_张老大_背.png; 出图/共享/图片/定妆_张老大_半身.png; 出图/共享/图片/定妆_张老大_三视图.png; 出图/共享/图片/定妆_张老大_脸部特写.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CROWD_ZAYI（群杂役）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_群杂役_虚化.png; 出图/共享/图片/定妆_群杂役_虚化_侧.png; 出图/共享/图片/定妆_群杂役_虚化_背.png; 出图/共享/图片/定妆_群杂役_虚化_半身.png; 出图/共享/图片/定妆_群杂役_虚化_三视图.png; 出图/共享/图片/定妆_群杂役_虚化_群像sheet.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。

**近景/反打身份锁定**：主焦点角色=CHAR_HE_PINGSHENG（贺平生）、CHAR_ZHANG_LAODA（张老大）、CROWD_ZAYI（群杂役）；使用 identity_registry / identity_adapter_matrix / reference_group / face_anchor / expressions。锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；表情只动面部肌肉，不改脸型；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜，保留 story beat。

**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留

**衔接设计**：
- 入点：首帧大殿黑暗，全景慢推到贺平生被审问。
- 出点：中段接力帧：多人反打和笑声包围，需要中锚锁站位。
- 转场：split_relay
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：首帧大殿黑暗，全景慢推到贺平生被审问。
- action：黑暗大殿中贺平生被审问。，张老大问年龄，贺平生低头回答。
- end_state：中段接力帧：多人反打和笑声包围，需要中锚锁站位。
- constraints：首帧=出图/第1集/图片/Clip01_黑殿审问.png; 尾帧=出图/第1集/图片/Clip01_黑殿审问_mid.png; asset_ids=LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CROWD_ZAYI; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 首帧大殿黑暗，全景慢推到贺平生被审问。
  action: 黑暗大殿中贺平生被审问。，张老大问年龄，贺平生低头回答。
  end_state: 中段接力帧：多人反打和笑声包围，需要中锚锁站位。
  constraints: 首帧=出图/第1集/图片/Clip01_黑殿审问.png; 尾帧=出图/第1集/图片/Clip01_黑殿审问_mid.png; asset_ids=LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CROWD_ZAYI; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：定场镜用升降建立地理和权力关系，不抢人物表演。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在LS/ELS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：贺平生画左下，张老大画右前景，群杂役后景围压。;
表演节拍：[0-4s] 黑暗大殿中贺平生被审问。（全景·慢推）；[4-8.5s] 张老大问年龄，贺平生低头回答。（中近景反打）;
三轨音频：旁白音频后期 compose 叠加；本视频生成不要生成旁白音频，只允许画内角色对白口型;
三轨修补：屏幕文案仅后期overlay显示「十四岁 · 五行灵根」，本视频生成不要画字、不要生成字幕卡、不要生成logo;
运动精修约束：张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。; 身体守卫=脸部轮廓和发髻不拉伸，肩颈/手部不穿模，道具不粘连;
环境交互约束：门缝冷光、屋顶漏光和殿内尘雾随人物呼吸轻微变化，背景杂役只作暗影虚化。;
专项模板约束：template_id=dialogue_shot_reverse；beats=张老大审问年龄；贺平生低头回答；张老大问灵根；群杂役哄笑；blocking=贺平生画左下，张老大画右前景，群杂役后景围压。；camera_rule=守张老大→贺平生横轴；反打不交换左右站位。；continuity_must=贺平生始终少年瘦削；张老大画右压迫；大殿低冷光不跳；negative=不要跳轴；不要新增仙门长老正脸；不要把杂役大殿画成仙宫；axis=张老大→贺平生横轴；eyeline=贺平生看画右上，张老大看画左下；shot_pairing=张老大 MS/CU 反打贺平生 CU，群杂役只作后景笑影。
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=seedance，mode=native_av，native_audio_policy=native_speech，identity_requirement=character_id_or_reference_group；只使用 Seedance via Dreamina 已刷新证据支持的能力；失败按 degrade_plan 或 Motion Control degrade_only 停审，不临场改后端;
身份锁定约束：读取 identity_registry.json 和 identity_adapter_matrix.json；使用首/尾帧与 reference_group，保持 drift_forbidden=face_shape/hairstyle/outfit_palette/age/costume；角色=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CROWD_ZAYI;
近景身份锁定约束：CU/MCU/反打/说话镜优先脸部特写、表情参考、front/side/back reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；配角近景不稳则用 MCU/OTS/侧脸/手部/物件反应镜;
原生音画约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
人物运动：黑暗大殿中贺平生被审问。，张老大问年龄，贺平生低头回答。;
镜头运动：缓慢升降，轻微上升/下降揭示空间层次，落到LS/ELS; 后端控制写法：自然语言运镜：缓慢升降，轻微上升/下降揭示空间层次，落到LS/ELS；首帧锚定，不改变角色、光位、轴线和场景设定。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=split_relay;
声音约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 首帧大殿黑暗，全景慢推到贺平生被审问。; action: 黑暗大殿中贺平生被审问。，张老大问年龄，贺平生低头回答。; end: 中段接力帧：多人反打和笑声包围，需要中锚锁站位。; constraints: 首帧=出图/第1集/图片/Clip01_黑殿审问.png; 尾帧=出图/第1集/图片/Clip01_黑殿审问_mid.png; asset_ids=LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CROWD_ZAYI; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 定场镜用升降建立地理和权力关系，不抢人物表演。; camera motion: 缓慢升降，轻微上升/下降揭示空间层次，落到LS/ELS; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。.
identity constraint: use identity_registry, reference_group, face anchors, and expression references; preserve facial proportions, hairstyle, accessories, outfit palette, age, and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group.
audio constraint: native speech is intentional, keep original generated clip audio and verify lip sync.
```

### 检查清单（视频三件套自查）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、身份锁定、原生音画策略与 route 一致

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然
- [ ] 镜头运动符合 prompt
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸
## Clip 02（时长 8.5s · EP01_CLIP02 · 黑殿审问下）

**首帧**：`出图/第1集/图片/Clip01_黑殿审问_mid.png`
**尾帧**：`出图/第1集/图片/Clip01_黑殿审问_end.png`
**中段锚帧豁免**：本 Clip 是视频 preflight 按原中段锚帧拆出的短半段；旧中帧已作为段边界尾帧/首帧复用，内部不再新增中段锚帧。
**场景**：秀竹峰杂役大殿/夜/内
**导演意图**：定场镜用升降建立地理和权力关系，不抢人物表演。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在LS/ELS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：shot_reverse_shot；多人同框执行策略：shot_reverse_shot_or_split_composite_required；清晰正脸不超过一人，群杂役只作后景虚化。；守张老大→贺平生横轴；反打不交换左右站位。
**表演节拍**：[0-1.5s] 贺平生答完年龄后的短暂停顿，张老大追问灵根；本段不重复年龄对白。（中近景反打）；[1.5-8.5s] 五行灵根出口，群杂役哄笑，灰尘落下。（CU碎切）；微表情/表情幅度：贺平生：起 AU4轻压眉+AU24抿唇，止 AU5轻抬眼后迅速垂下；张老大：起漫不经心，止嘴角嘲笑。
**运动精修**：张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。；身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：门缝冷光、屋顶漏光和殿内尘雾随人物呼吸轻微变化，背景杂役只作暗影虚化。
**涉及资产**：LOC_ZAYI_DADIAN

**专项镜头模板**：template_id=dialogue_shot_reverse；beats=张老大审问年龄；贺平生低头回答；张老大问灵根；群杂役哄笑；blocking=贺平生画左下，张老大画右前景，群杂役后景围压。；camera_rule=守张老大→贺平生横轴；反打不交换左右站位。；continuity_must=贺平生始终少年瘦削；张老大画右压迫；大殿低冷光不跳；negative=不要跳轴；不要新增仙门长老正脸；不要把杂役大殿画成仙宫；axis=张老大→贺平生横轴；eyeline=贺平生看画右上，张老大看画左下；shot_pairing=张老大 MS/CU 反打贺平生 CU，群杂役只作后景笑影。

**模型路由**：shot_type=dialogue_shot_reverse; clip_characters=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; policy_resolution.winner=native_voice_fallback; risk_flags=mouth_visible, multi_person, native_speech, seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

**动作编排契约 / Action Choreography**：无。

**Motion Control / 物理交互控制**：无。

**角色身份注册层**：
- CHAR_HE_PINGSHENG（贺平生）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_贺平生.png; 出图/共享/图片/定妆_贺平生_侧.png; 出图/共享/图片/定妆_贺平生_背.png; 出图/共享/图片/定妆_贺平生_半身.png; 出图/共享/图片/定妆_贺平生_三视图.png; 出图/共享/图片/定妆_贺平生_脸部特写.png; 出图/共享/图片/定妆_贺平生_表情_克制.png; 出图/共享/图片/定妆_贺平生_表情_疲惫隐忍.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CHAR_ZHANG_LAODA（张老大）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_张老大.png; 出图/共享/图片/定妆_张老大_侧.png; 出图/共享/图片/定妆_张老大_背.png; 出图/共享/图片/定妆_张老大_半身.png; 出图/共享/图片/定妆_张老大_三视图.png; 出图/共享/图片/定妆_张老大_脸部特写.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CHAR_TAIXUMEN_ZHANGLAO（太虚门长老）：split_handoff_compat=继承旧出图 Clip_02 的低清背影身份锚；仅作为远景/回忆背影 reference_group 兼容项，不生成清晰正脸，不提升为本半段表演主体；reference_group=出图/共享/图片/定妆_太虚门长老_回忆背影.png。
- CROWD_ZAYI（群杂役）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_群杂役_虚化.png; 出图/共享/图片/定妆_群杂役_虚化_侧.png; 出图/共享/图片/定妆_群杂役_虚化_背.png; 出图/共享/图片/定妆_群杂役_虚化_半身.png; 出图/共享/图片/定妆_群杂役_虚化_三视图.png; 出图/共享/图片/定妆_群杂役_虚化_群像sheet.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。

**近景/反打身份锁定**：主焦点角色=CHAR_HE_PINGSHENG（贺平生）、CHAR_ZHANG_LAODA（张老大）、CROWD_ZAYI（群杂役）；使用 identity_registry / identity_adapter_matrix / reference_group / face_anchor / expressions。锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；表情只动面部肌肉，不改脸型；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜，保留 story beat。

**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留

**衔接设计**：
- 入点：中段接力帧：多人反打和笑声包围，需要中锚锁站位。
- 出点：贺平生低头说出五行灵根，群杂役笑声压满大殿。
- 转场：j_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：中段接力帧：多人反打和笑声包围，需要中锚锁站位。
- action：贺平生答完年龄后的短暂停顿，张老大追问灵根；本段不重复年龄对白。，五行灵根出口，群杂役哄笑，灰尘落下。
- end_state：贺平生低头说出五行灵根，群杂役笑声压满大殿。
- constraints：首帧=出图/第1集/图片/Clip01_黑殿审问_mid.png; 尾帧=出图/第1集/图片/Clip01_黑殿审问_end.png; asset_ids=LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CROWD_ZAYI; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 中段接力帧：多人反打和笑声包围，需要中锚锁站位。
  action: 贺平生答完年龄后的短暂停顿，张老大追问灵根；本段不重复年龄对白。，五行灵根出口，群杂役哄笑，灰尘落下。
  end_state: 贺平生低头说出五行灵根，群杂役笑声压满大殿。
  constraints: 首帧=出图/第1集/图片/Clip01_黑殿审问_mid.png; 尾帧=出图/第1集/图片/Clip01_黑殿审问_end.png; asset_ids=LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CROWD_ZAYI; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：定场镜用升降建立地理和权力关系，不抢人物表演。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在LS/ELS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：贺平生画左下，张老大画右前景，群杂役后景围压。;
表演节拍：[0-1.5s] 贺平生答完年龄后的短暂停顿，张老大追问灵根；本段不重复年龄对白。（中近景反打）；[1.5-8.5s] 五行灵根出口，群杂役哄笑，灰尘落下。（CU碎切）;
运动精修约束：张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。; 身体守卫=脸部轮廓和发髻不拉伸，肩颈/手部不穿模，道具不粘连;
环境交互约束：门缝冷光、屋顶漏光和殿内尘雾随人物呼吸轻微变化，背景杂役只作暗影虚化。;
专项模板约束：template_id=dialogue_shot_reverse；beats=张老大审问年龄；贺平生低头回答；张老大问灵根；群杂役哄笑；blocking=贺平生画左下，张老大画右前景，群杂役后景围压。；camera_rule=守张老大→贺平生横轴；反打不交换左右站位。；continuity_must=贺平生始终少年瘦削；张老大画右压迫；大殿低冷光不跳；negative=不要跳轴；不要新增仙门长老正脸；不要把杂役大殿画成仙宫；axis=张老大→贺平生横轴；eyeline=贺平生看画右上，张老大看画左下；shot_pairing=张老大 MS/CU 反打贺平生 CU，群杂役只作后景笑影。
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=seedance，mode=native_av，native_audio_policy=native_speech，identity_requirement=character_id_or_reference_group；只使用 Seedance via Dreamina 已刷新证据支持的能力；失败按 degrade_plan 或 Motion Control degrade_only 停审，不临场改后端;
身份锁定约束：读取 identity_registry.json 和 identity_adapter_matrix.json；使用首/尾帧与 reference_group，保持 drift_forbidden=face_shape/hairstyle/outfit_palette/age/costume；角色=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CROWD_ZAYI;
近景身份锁定约束：CU/MCU/反打/说话镜优先脸部特写、表情参考、front/side/back reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；配角近景不稳则用 MCU/OTS/侧脸/手部/物件反应镜;
原生音画约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
人物运动：贺平生答完年龄后的短暂停顿，张老大追问灵根；本段不重复年龄对白。，五行灵根出口，群杂役哄笑，灰尘落下。;
镜头运动：缓慢升降，轻微上升/下降揭示空间层次，落到LS/ELS; 后端控制写法：自然语言运镜：缓慢升降，轻微上升/下降揭示空间层次，落到LS/ELS；首帧锚定，不改变角色、光位、轴线和场景设定。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=j_cut;
声音约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 中段接力帧：多人反打和笑声包围，需要中锚锁站位。; action: 贺平生答完年龄后的短暂停顿，张老大追问灵根；本段不重复年龄对白。，五行灵根出口，群杂役哄笑，灰尘落下。; end: 贺平生低头说出五行灵根，群杂役笑声压满大殿。; constraints: 首帧=出图/第1集/图片/Clip01_黑殿审问_mid.png; 尾帧=出图/第1集/图片/Clip01_黑殿审问_end.png; asset_ids=LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CROWD_ZAYI; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 定场镜用升降建立地理和权力关系，不抢人物表演。; camera motion: 缓慢升降，轻微上升/下降揭示空间层次，落到LS/ELS; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。.
identity constraint: use identity_registry, reference_group, face anchors, and expression references; preserve facial proportions, hairstyle, accessories, outfit palette, age, and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group.
audio constraint: native speech is intentional, keep original generated clip audio and verify lip sync.
```

### 检查清单（视频三件套自查）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、身份锁定、原生音画策略与 route 一致

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然
- [ ] 镜头运动符合 prompt
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 03（时长 9s · EP01_CLIP03 · 挑水命令上）

**首帧**：`出图/第1集/图片/Clip02_挑水命令.png`
**尾帧**：`出图/第1集/图片/Clip02_挑水命令_mid.png`
**中段锚帧豁免**：本 Clip 是视频 preflight 按原中段锚帧拆出的短半段；旧中帧已作为段边界尾帧/首帧复用，内部不再新增中段锚帧。
**场景**：秀竹峰杂役大殿/夜/内
**导演意图**：反转/打脸/觉醒在近景里用推近强化压迫，不用大幅旋转破坏表演。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：shot_reverse_shot；多人同框执行策略：shot_reverse_shot_or_split_composite_required；张老大与贺平生以反打和手部插入镜为主。；反打守横轴，拍肩用手部插入镜缓冲。
**表演节拍**：[0-9s] 五行光点被灰暗大殿压灭，长老背影离开。（概念快闪）；微表情/表情幅度：贺平生：AU4眉间收紧+AU24抿唇，肩膀被拍后短促吸气。
**三轨音频**：旁白音频后期 compose 叠加；视频生成阶段不要生成旁白音频，只允许画内角色对白口型。
**三轨修补**：屏幕文案（后期overlay）：五行俱全，却无人愿收；不得让视频模型生成文字，compose 阶段叠清晰字。
**运动精修**：张力=爆发；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。；身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：门缝冷光、屋顶漏光和殿内尘雾随人物呼吸轻微变化，背景杂役只作暗影虚化。
**涉及资产**：LOC_ZAYI_DADIAN, 外门觉醒台

**专项镜头模板**：template_id=dialogue_shot_reverse；beats=五行灵根解释；长老背影离开；张老大拍肩下命令；贺平生应是；blocking=回到大殿后，张老大仍画右前压，贺平生画左下承受。；camera_rule=反打守横轴，拍肩用手部插入镜缓冲。；continuity_must=张老大手掌油污；贺平生肩膀被拍沉；大殿光位继承 Clip01；negative=不要换成白天；不要让长老正脸抢戏；不要把贺平生画成年；axis=张老大→贺平生横轴；eyeline=贺平生看画右上张老大；shot_pairing=五行灵根概念快闪 / 张老大拍肩 CU / 贺平生低头反应 CU。

**模型路由**：shot_type=dialogue_shot_reverse; clip_characters=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CHAR_TAIXUMEN_ZHANGLAO; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; policy_resolution.winner=native_voice_fallback; risk_flags=mouth_visible, native_speech, seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

**动作编排契约 / Action Choreography**：无。

**Motion Control / 物理交互控制**：无。

**角色身份注册层**：
- CHAR_HE_PINGSHENG（贺平生）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_贺平生.png; 出图/共享/图片/定妆_贺平生_侧.png; 出图/共享/图片/定妆_贺平生_背.png; 出图/共享/图片/定妆_贺平生_半身.png; 出图/共享/图片/定妆_贺平生_三视图.png; 出图/共享/图片/定妆_贺平生_脸部特写.png; 出图/共享/图片/定妆_贺平生_表情_克制.png; 出图/共享/图片/定妆_贺平生_表情_疲惫隐忍.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CHAR_ZHANG_LAODA（张老大）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_张老大.png; 出图/共享/图片/定妆_张老大_侧.png; 出图/共享/图片/定妆_张老大_背.png; 出图/共享/图片/定妆_张老大_半身.png; 出图/共享/图片/定妆_张老大_三视图.png; 出图/共享/图片/定妆_张老大_脸部特写.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CHAR_TAIXUMEN_ZHANGLAO（太虚门长老）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_太虚门长老_回忆背影.png; 出图/共享/图片/定妆_太虚门长老_回忆背影_侧.png; 出图/共享/图片/定妆_太虚门长老_回忆背影_背.png; 出图/共享/图片/定妆_太虚门长老_回忆背影_半身.png; 出图/共享/图片/定妆_太虚门长老_回忆背影_三视图.png; 出图/共享/图片/定妆_太虚门长老_回忆背影_侧背.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CHAR_JIANG_JIAN（江剑）：split_handoff_compat=继承旧出图 Clip_03 的背影身份锚；仅作为后续回忆蒙太奇低清背影 reference_group 兼容项，不生成清晰正脸，不参与本半段大殿表演；reference_group=出图/共享/图片/定妆_江剑_背影.png。
- CHAR_HE_SANJIE（贺三杰）：split_handoff_compat=继承旧出图 Clip_03 的回忆影身份锚；仅作为后续回忆蒙太奇旧影/旧物暗示 reference_group 兼容项，不生成清晰正脸，不画死亡细节；reference_group=出图/共享/图片/定妆_贺三杰_回忆影.png。

**近景/反打身份锁定**：主焦点角色=CHAR_HE_PINGSHENG（贺平生）、CHAR_ZHANG_LAODA（张老大）、CHAR_TAIXUMEN_ZHANGLAO（太虚门长老）；使用 identity_registry / identity_adapter_matrix / reference_group / face_anchor / expressions。锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；表情只动面部肌肉，不改脸型；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜，保留 story beat。

**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留

**衔接设计**：
- 入点：贺平生低头说出五行灵根，群杂役笑声压满大殿。
- 出点：中段接力帧：从回忆背影回到大殿命令，需要中锚避免人物换脸。
- 转场：split_relay
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：贺平生低头说出五行灵根，群杂役笑声压满大殿。
- action：五行光点被灰暗大殿压灭，长老背影离开。
- end_state：中段接力帧：从回忆背影回到大殿命令，需要中锚避免人物换脸。
- constraints：首帧=出图/第1集/图片/Clip02_挑水命令.png; 尾帧=出图/第1集/图片/Clip02_挑水命令_mid.png; asset_ids=LOC_ZAYI_DADIAN, 外门觉醒台; character_ids=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CHAR_TAIXUMEN_ZHANGLAO; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 贺平生低头说出五行灵根，群杂役笑声压满大殿。
  action: 五行光点被灰暗大殿压灭，长老背影离开。
  end_state: 中段接力帧：从回忆背影回到大殿命令，需要中锚避免人物换脸。
  constraints: 首帧=出图/第1集/图片/Clip02_挑水命令.png; 尾帧=出图/第1集/图片/Clip02_挑水命令_mid.png; asset_ids=LOC_ZAYI_DADIAN, 外门觉醒台; character_ids=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CHAR_TAIXUMEN_ZHANGLAO; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：反转/打脸/觉醒在近景里用推近强化压迫，不用大幅旋转破坏表演。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：回到大殿后，张老大仍画右前压，贺平生画左下承受。;
表演节拍：[0-9s] 五行光点被灰暗大殿压灭，长老背影离开。（概念快闪）;
三轨音频：旁白音频后期 compose 叠加；本视频生成不要生成旁白音频，只允许画内角色对白口型;
三轨修补：屏幕文案仅后期overlay显示「五行俱全，却无人愿收」，本视频生成不要画字、不要生成字幕卡、不要生成logo;
运动精修约束：张力=爆发；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。; 身体守卫=脸部轮廓和发髻不拉伸，肩颈/手部不穿模，道具不粘连;
环境交互约束：门缝冷光、屋顶漏光和殿内尘雾随人物呼吸轻微变化，背景杂役只作暗影虚化。;
专项模板约束：template_id=dialogue_shot_reverse；beats=五行灵根解释；长老背影离开；张老大拍肩下命令；贺平生应是；blocking=回到大殿后，张老大仍画右前压，贺平生画左下承受。；camera_rule=反打守横轴，拍肩用手部插入镜缓冲。；continuity_must=张老大手掌油污；贺平生肩膀被拍沉；大殿光位继承 Clip01；negative=不要换成白天；不要让长老正脸抢戏；不要把贺平生画成年；axis=张老大→贺平生横轴；eyeline=贺平生看画右上张老大；shot_pairing=五行灵根概念快闪 / 张老大拍肩 CU / 贺平生低头反应 CU。
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=seedance，mode=native_av，native_audio_policy=native_speech，identity_requirement=character_id_or_reference_group；只使用 Seedance via Dreamina 已刷新证据支持的能力；失败按 degrade_plan 或 Motion Control degrade_only 停审，不临场改后端;
身份锁定约束：读取 identity_registry.json 和 identity_adapter_matrix.json；使用首/尾帧与 reference_group，保持 drift_forbidden=face_shape/hairstyle/outfit_palette/age/costume；角色=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CHAR_TAIXUMEN_ZHANGLAO;
近景身份锁定约束：CU/MCU/反打/说话镜优先脸部特写、表情参考、front/side/back reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；配角近景不稳则用 MCU/OTS/侧脸/手部/物件反应镜;
原生音画约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
人物运动：五行光点被灰暗大殿压灭，长老背影离开。;
镜头运动：缓慢推镜头，沿人物视线/证据物方向推近，落到CU; 后端控制写法：自然语言运镜：缓慢推镜头，沿人物视线/证据物方向推近，落到CU；首帧锚定，不改变角色、光位、轴线和场景设定。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=split_relay;
声音约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 贺平生低头说出五行灵根，群杂役笑声压满大殿。; action: 五行光点被灰暗大殿压灭，长老背影离开。; end: 中段接力帧：从回忆背影回到大殿命令，需要中锚避免人物换脸。; constraints: 首帧=出图/第1集/图片/Clip02_挑水命令.png; 尾帧=出图/第1集/图片/Clip02_挑水命令_mid.png; asset_ids=LOC_ZAYI_DADIAN, 外门觉醒台; character_ids=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CHAR_TAIXUMEN_ZHANGLAO; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 反转/打脸/觉醒在近景里用推近强化压迫，不用大幅旋转破坏表演。; camera motion: 缓慢推镜头，沿人物视线/证据物方向推近，落到CU; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。.
identity constraint: use identity_registry, reference_group, face anchors, and expression references; preserve facial proportions, hairstyle, accessories, outfit palette, age, and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group.
audio constraint: native speech is intentional, keep original generated clip audio and verify lip sync.
```

### 检查清单（视频三件套自查）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、身份锁定、原生音画策略与 route 一致

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然
- [ ] 镜头运动符合 prompt
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸
## Clip 04（时长 9s · EP01_CLIP04 · 挑水命令下）

**首帧**：`出图/第1集/图片/Clip02_挑水命令_mid.png`
**尾帧**：`出图/第1集/图片/Clip02_挑水命令_end.png`
**中段锚帧豁免**：本 Clip 是视频 preflight 按原中段锚帧拆出的短半段；旧中帧已作为段边界尾帧/首帧复用，内部不再新增中段锚帧。
**场景**：秀竹峰杂役大殿/夜/内
**导演意图**：反转/打脸/觉醒在近景里用推近强化压迫，不用大幅旋转破坏表演。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：shot_reverse_shot；多人同框执行策略：shot_reverse_shot_or_split_composite_required；张老大与贺平生以反打和手部插入镜为主。；反打守横轴，拍肩用手部插入镜缓冲。
**表演节拍**：[0-1s] 五行光点被灰暗大殿压灭，长老背影离开。（概念快闪）；[1-9s] 张老大拍肩命令挑水，贺平生低头应是。（MS到CU）；微表情/表情幅度：贺平生：AU4眉间收紧+AU24抿唇，肩膀被拍后短促吸气。
**运动精修**：张力=爆发；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。；身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：门缝冷光、屋顶漏光和殿内尘雾随人物呼吸轻微变化，背景杂役只作暗影虚化。
**涉及资产**：LOC_ZAYI_DADIAN, 外门觉醒台

**专项镜头模板**：template_id=dialogue_shot_reverse；beats=五行灵根解释；长老背影离开；张老大拍肩下命令；贺平生应是；blocking=回到大殿后，张老大仍画右前压，贺平生画左下承受。；camera_rule=反打守横轴，拍肩用手部插入镜缓冲。；continuity_must=张老大手掌油污；贺平生肩膀被拍沉；大殿光位继承 Clip01；negative=不要换成白天；不要让长老正脸抢戏；不要把贺平生画成年；axis=张老大→贺平生横轴；eyeline=贺平生看画右上张老大；shot_pairing=五行灵根概念快闪 / 张老大拍肩 CU / 贺平生低头反应 CU。

**模型路由**：shot_type=dialogue_shot_reverse; clip_characters=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CHAR_TAIXUMEN_ZHANGLAO; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; policy_resolution.winner=native_voice_fallback; risk_flags=mouth_visible, native_speech, seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

**动作编排契约 / Action Choreography**：无。

**Motion Control / 物理交互控制**：无。

**角色身份注册层**：
- CHAR_HE_PINGSHENG（贺平生）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_贺平生.png; 出图/共享/图片/定妆_贺平生_侧.png; 出图/共享/图片/定妆_贺平生_背.png; 出图/共享/图片/定妆_贺平生_半身.png; 出图/共享/图片/定妆_贺平生_三视图.png; 出图/共享/图片/定妆_贺平生_脸部特写.png; 出图/共享/图片/定妆_贺平生_表情_克制.png; 出图/共享/图片/定妆_贺平生_表情_疲惫隐忍.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CHAR_ZHANG_LAODA（张老大）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_张老大.png; 出图/共享/图片/定妆_张老大_侧.png; 出图/共享/图片/定妆_张老大_背.png; 出图/共享/图片/定妆_张老大_半身.png; 出图/共享/图片/定妆_张老大_三视图.png; 出图/共享/图片/定妆_张老大_脸部特写.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CHAR_TAIXUMEN_ZHANGLAO（太虚门长老）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_太虚门长老_回忆背影.png; 出图/共享/图片/定妆_太虚门长老_回忆背影_侧.png; 出图/共享/图片/定妆_太虚门长老_回忆背影_背.png; 出图/共享/图片/定妆_太虚门长老_回忆背影_半身.png; 出图/共享/图片/定妆_太虚门长老_回忆背影_三视图.png; 出图/共享/图片/定妆_太虚门长老_回忆背影_侧背.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。

**近景/反打身份锁定**：主焦点角色=CHAR_HE_PINGSHENG（贺平生）、CHAR_ZHANG_LAODA（张老大）、CHAR_TAIXUMEN_ZHANGLAO（太虚门长老）；使用 identity_registry / identity_adapter_matrix / reference_group / face_anchor / expressions。锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；表情只动面部肌肉，不改脸型；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜，保留 story beat。

**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留

**衔接设计**：
- 入点：中段接力帧：从回忆背影回到大殿命令，需要中锚避免人物换脸。
- 出点：张老大手压在贺平生肩上，挑水命令落下，贺平生低头应是。
- 转场：hard_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：中段接力帧：从回忆背影回到大殿命令，需要中锚避免人物换脸。
- action：五行光点被灰暗大殿压灭，长老背影离开。，张老大拍肩命令挑水，贺平生低头应是。
- end_state：张老大手压在贺平生肩上，挑水命令落下，贺平生低头应是。
- constraints：首帧=出图/第1集/图片/Clip02_挑水命令_mid.png; 尾帧=出图/第1集/图片/Clip02_挑水命令_end.png; asset_ids=LOC_ZAYI_DADIAN, 外门觉醒台; character_ids=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CHAR_TAIXUMEN_ZHANGLAO; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 中段接力帧：从回忆背影回到大殿命令，需要中锚避免人物换脸。
  action: 五行光点被灰暗大殿压灭，长老背影离开。，张老大拍肩命令挑水，贺平生低头应是。
  end_state: 张老大手压在贺平生肩上，挑水命令落下，贺平生低头应是。
  constraints: 首帧=出图/第1集/图片/Clip02_挑水命令_mid.png; 尾帧=出图/第1集/图片/Clip02_挑水命令_end.png; asset_ids=LOC_ZAYI_DADIAN, 外门觉醒台; character_ids=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CHAR_TAIXUMEN_ZHANGLAO; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：反转/打脸/觉醒在近景里用推近强化压迫，不用大幅旋转破坏表演。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：回到大殿后，张老大仍画右前压，贺平生画左下承受。;
表演节拍：[0-1s] 五行光点被灰暗大殿压灭，长老背影离开。（概念快闪）；[1-9s] 张老大拍肩命令挑水，贺平生低头应是。（MS到CU）;
运动精修约束：张力=爆发；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。; 身体守卫=脸部轮廓和发髻不拉伸，肩颈/手部不穿模，道具不粘连;
环境交互约束：门缝冷光、屋顶漏光和殿内尘雾随人物呼吸轻微变化，背景杂役只作暗影虚化。;
专项模板约束：template_id=dialogue_shot_reverse；beats=五行灵根解释；长老背影离开；张老大拍肩下命令；贺平生应是；blocking=回到大殿后，张老大仍画右前压，贺平生画左下承受。；camera_rule=反打守横轴，拍肩用手部插入镜缓冲。；continuity_must=张老大手掌油污；贺平生肩膀被拍沉；大殿光位继承 Clip01；negative=不要换成白天；不要让长老正脸抢戏；不要把贺平生画成年；axis=张老大→贺平生横轴；eyeline=贺平生看画右上张老大；shot_pairing=五行灵根概念快闪 / 张老大拍肩 CU / 贺平生低头反应 CU。
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=seedance，mode=native_av，native_audio_policy=native_speech，identity_requirement=character_id_or_reference_group；只使用 Seedance via Dreamina 已刷新证据支持的能力；失败按 degrade_plan 或 Motion Control degrade_only 停审，不临场改后端;
身份锁定约束：读取 identity_registry.json 和 identity_adapter_matrix.json；使用首/尾帧与 reference_group，保持 drift_forbidden=face_shape/hairstyle/outfit_palette/age/costume；角色=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CHAR_TAIXUMEN_ZHANGLAO;
近景身份锁定约束：CU/MCU/反打/说话镜优先脸部特写、表情参考、front/side/back reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；配角近景不稳则用 MCU/OTS/侧脸/手部/物件反应镜;
原生音画约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
人物运动：五行光点被灰暗大殿压灭，长老背影离开。，张老大拍肩命令挑水，贺平生低头应是。;
镜头运动：缓慢推镜头，沿人物视线/证据物方向推近，落到CU; 后端控制写法：自然语言运镜：缓慢推镜头，沿人物视线/证据物方向推近，落到CU；首帧锚定，不改变角色、光位、轴线和场景设定。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=hard_cut;
声音约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 中段接力帧：从回忆背影回到大殿命令，需要中锚避免人物换脸。; action: 五行光点被灰暗大殿压灭，长老背影离开。，张老大拍肩命令挑水，贺平生低头应是。; end: 张老大手压在贺平生肩上，挑水命令落下，贺平生低头应是。; constraints: 首帧=出图/第1集/图片/Clip02_挑水命令_mid.png; 尾帧=出图/第1集/图片/Clip02_挑水命令_end.png; asset_ids=LOC_ZAYI_DADIAN, 外门觉醒台; character_ids=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CHAR_TAIXUMEN_ZHANGLAO; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 反转/打脸/觉醒在近景里用推近强化压迫，不用大幅旋转破坏表演。; camera motion: 缓慢推镜头，沿人物视线/证据物方向推近，落到CU; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。.
identity constraint: use identity_registry, reference_group, face anchors, and expression references; preserve facial proportions, hairstyle, accessories, outfit palette, age, and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group.
audio constraint: native speech is intentional, keep original generated clip audio and verify lip sync.
```

### 检查清单（视频三件套自查）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、身份锁定、原生音画策略与 route 一致

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然
- [ ] 镜头运动符合 prompt
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 05（时长 11s · EP01_CLIP05 · 外门遗孤上）

**首帧**：`出图/第1集/图片/Clip03_外门遗孤.png`
**尾帧**：`出图/第1集/图片/Clip03_外门遗孤_mid.png`
**中段锚帧豁免**：本 Clip 是视频 preflight 按原中段锚帧拆出的短半段；旧中帧已作为段边界尾帧/首帧复用，内部不再新增中段锚帧。
**场景**：太虚门外门旧院/日/回忆
**导演意图**：动作过程需要空间方向清楚；匀速移镜比自由漂浮更容易守轴线和人物站位。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在蒙太奇→WS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：贺平生站画左前院门边；CHAR_JIANG_JIAN/背影在中景偏右；CHAR_HE_SANJIE/回忆影只作旧影或旧物暗示；CROWD_TAIXU_CULTIVATOR/远景剪影在画面深处山间云雾里。；回忆蒙太奇低饱和柔冷光，慢推或固定切片；不做无动机环绕，不切成血腥事件。
**表演节拍**：[0-8s] 父母亡故、资源被抢。（碎片蒙太奇）；[8-11s] 江剑收拾行囊，把贺平生送向秀竹峰。（中景背影）；微表情/表情幅度：贺平生：回忆中沉默低眼，望向远处修士剪影时眼睑微抬，呼吸变稳。
**三轨音频**：旁白音频后期 compose 叠加；视频生成阶段不要生成旁白音频，只允许画内角色对白口型。
**运动精修**：张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。；身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：旧院尘土、低饱和天光和山间薄雾轻动，非主角人物保持背影、剪影或虚化。
**涉及资产**：LOC_WAIMEN_JIUYUAN, 旧行囊, 秀竹峰山门

**专项镜头模板**：template_id=ensemble_blocking；beats=旧院空景和旧行囊暗示前情；幼年贺平生短闪；江剑背影收拾行囊；十四岁贺平生望向远处修士剪影；blocking=贺平生站画左前院门边；CHAR_JIANG_JIAN/背影在中景偏右；CHAR_HE_SANJIE/回忆影只作旧影或旧物暗示；CROWD_TAIXU_CULTIVATOR/远景剪影在画面深处山间云雾里。；camera_rule=回忆蒙太奇低饱和柔冷光，慢推或固定切片；不做无动机环绕，不切成血腥事件。；continuity_must=贺平生年龄形态与 identity_registry 对齐；江剑只背影/侧背；贺三杰不清晰露脸；远景修士只小比例剪影；外门旧院不豪华化；negative=不要清晰父母死亡；不要血腥；不要豪华宗门正殿；不要现代校园；不要新增清晰陌生脸；screen_positions=LEFT_FOREGROUND=CHAR_HE_PINGSHENG/常态或幼年，唯一可清晰脸。；MID_RIGHT=CHAR_JIANG_JIAN/背影，不露清晰正脸。；BACKGROUND_MEMORY=CHAR_HE_SANJIE/回忆影，只用旧影/旧物，不画死亡细节。；FAR_BACKGROUND=CROWD_TAIXU_CULTIVATOR/远景剪影，小比例不露脸。；LOCATION_PLATE=LOC_WAIMEN_JIUYUAN 灰旧院门、低矮院墙、远处山门。；focus_hierarchy=CHAR_HE_PINGSHENG；LOC_WAIMEN_JIUYUAN；CHAR_JIANG_JIAN/背影；CROWD_TAIXU_CULTIVATOR/远景剪影；CHAR_HE_SANJIE/回忆影；crowd_simplification=除贺平生外，所有人都按背影、侧背、剪影、虚化或旧物暗示处理；不得新增清晰父母死亡画面。；keyframe_plan=start=张老大手压在贺平生肩上，挑水命令落下，贺平生低头应是。；end=中段接力帧：回忆蒙太奇跨时间，需要中锚锁主角少年常态。；motion_control=level=degrade_only；reason=回忆群像不直接生成复杂连续动作，拆成空景/背影/远景剪影短镜。。

**模型路由**：shot_type=ensemble_blocking; clip_characters=CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN, CHAR_HE_SANJIE; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; policy_resolution.winner=native_voice_fallback; risk_flags=identity_drift_risk, mouth_visible, multi_person, native_speech, seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

**动作编排契约 / Action Choreography**：无。

**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_05/motion_control_manifest.json；required_inputs=pose_sequence, depth_sequence, instance_masks；failure_modes=slot_drift, pose_drift, identity_drift；gate_policy=block_without_ready_manifest_or_degrade_only_manifest。

**角色身份注册层**：
- CHAR_HE_PINGSHENG（贺平生）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_贺平生.png; 出图/共享/图片/定妆_贺平生_侧.png; 出图/共享/图片/定妆_贺平生_背.png; 出图/共享/图片/定妆_贺平生_半身.png; 出图/共享/图片/定妆_贺平生_三视图.png; 出图/共享/图片/定妆_贺平生_脸部特写.png; 出图/共享/图片/定妆_贺平生_表情_克制.png; 出图/共享/图片/定妆_贺平生_表情_疲惫隐忍.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CHAR_JIANG_JIAN（江剑）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_江剑_背影.png; 出图/共享/图片/定妆_江剑_背影_侧.png; 出图/共享/图片/定妆_江剑_背影_背.png; 出图/共享/图片/定妆_江剑_背影_半身.png; 出图/共享/图片/定妆_江剑_背影_三视图.png; 出图/共享/图片/定妆_江剑_背影_侧背.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CHAR_HE_SANJIE（贺三杰）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_贺三杰_回忆影.png; 出图/共享/图片/定妆_贺三杰_回忆影_侧.png; 出图/共享/图片/定妆_贺三杰_回忆影_背.png; 出图/共享/图片/定妆_贺三杰_回忆影_半身.png; 出图/共享/图片/定妆_贺三杰_回忆影_三视图.png; 出图/共享/图片/定妆_贺三杰_回忆影_侧影.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CROWD_TAIXU_CULTIVATOR（太虚门远景修士剪影）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_远景修士剪影.png; 出图/共享/图片/定妆_远景修士剪影_侧.png; 出图/共享/图片/定妆_远景修士剪影_背.png; 出图/共享/图片/定妆_远景修士剪影_半身.png; 出图/共享/图片/定妆_远景修士剪影_三视图.png; 出图/共享/图片/定妆_远景修士剪影_sheet.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。

**近景/反打身份锁定**：主焦点角色=CHAR_HE_PINGSHENG（贺平生）、CHAR_JIANG_JIAN（江剑）、CHAR_HE_SANJIE（贺三杰）、CROWD_TAIXU_CULTIVATOR（太虚门远景修士剪影）；使用 identity_registry / identity_adapter_matrix / reference_group / face_anchor / expressions。锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；表情只动面部肌肉，不改脸型；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜，保留 story beat。

**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留

**衔接设计**：
- 入点：张老大手压在贺平生肩上，挑水命令落下，贺平生低头应是。
- 出点：中段接力帧：回忆蒙太奇跨时间，需要中锚锁主角少年常态。
- 转场：split_relay
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：张老大手压在贺平生肩上，挑水命令落下，贺平生低头应是。
- action：父母亡故、资源被抢。，江剑收拾行囊，把贺平生送向秀竹峰。
- end_state：中段接力帧：回忆蒙太奇跨时间，需要中锚锁主角少年常态。
- constraints：首帧=出图/第1集/图片/Clip03_外门遗孤.png; 尾帧=出图/第1集/图片/Clip03_外门遗孤_mid.png; asset_ids=LOC_WAIMEN_JIUYUAN, 旧行囊, 秀竹峰山门; character_ids=CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN, CHAR_HE_SANJIE, CROWD_TAIXU_CULTIVATOR; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 张老大手压在贺平生肩上，挑水命令落下，贺平生低头应是。
  action: 父母亡故、资源被抢。，江剑收拾行囊，把贺平生送向秀竹峰。
  end_state: 中段接力帧：回忆蒙太奇跨时间，需要中锚锁主角少年常态。
  constraints: 首帧=出图/第1集/图片/Clip03_外门遗孤.png; 尾帧=出图/第1集/图片/Clip03_外门遗孤_mid.png; asset_ids=LOC_WAIMEN_JIUYUAN, 旧行囊, 秀竹峰山门; character_ids=CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN, CHAR_HE_SANJIE, CROWD_TAIXU_CULTIVATOR; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：动作过程需要空间方向清楚；匀速移镜比自由漂浮更容易守轴线和人物站位。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在蒙太奇→WS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：贺平生站画左前院门边；CHAR_JIANG_JIAN/背影在中景偏右；CHAR_HE_SANJIE/回忆影只作旧影或旧物暗示；CROWD_TAIXU_CULTIVATOR/远景剪影在画面深处山间云雾里。;
表演节拍：[0-8s] 父母亡故、资源被抢。（碎片蒙太奇）；[8-11s] 江剑收拾行囊，把贺平生送向秀竹峰。（中景背影）;
三轨音频：旁白音频后期 compose 叠加；本视频生成不要生成旁白音频，只允许画内角色对白口型;
运动精修约束：张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。; 身体守卫=脸部轮廓和发髻不拉伸，肩颈/手部不穿模，道具不粘连;
环境交互约束：旧院尘土、低饱和天光和山间薄雾轻动，非主角人物保持背影、剪影或虚化。;
专项模板约束：template_id=ensemble_blocking；beats=旧院空景和旧行囊暗示前情；幼年贺平生短闪；江剑背影收拾行囊；十四岁贺平生望向远处修士剪影；blocking=贺平生站画左前院门边；CHAR_JIANG_JIAN/背影在中景偏右；CHAR_HE_SANJIE/回忆影只作旧影或旧物暗示；CROWD_TAIXU_CULTIVATOR/远景剪影在画面深处山间云雾里。；camera_rule=回忆蒙太奇低饱和柔冷光，慢推或固定切片；不做无动机环绕，不切成血腥事件。；continuity_must=贺平生年龄形态与 identity_registry 对齐；江剑只背影/侧背；贺三杰不清晰露脸；远景修士只小比例剪影；外门旧院不豪华化；negative=不要清晰父母死亡；不要血腥；不要豪华宗门正殿；不要现代校园；不要新增清晰陌生脸；screen_positions=LEFT_FOREGROUND=CHAR_HE_PINGSHENG/常态或幼年，唯一可清晰脸。；MID_RIGHT=CHAR_JIANG_JIAN/背影，不露清晰正脸。；BACKGROUND_MEMORY=CHAR_HE_SANJIE/回忆影，只用旧影/旧物，不画死亡细节。；FAR_BACKGROUND=CROWD_TAIXU_CULTIVATOR/远景剪影，小比例不露脸。；LOCATION_PLATE=LOC_WAIMEN_JIUYUAN 灰旧院门、低矮院墙、远处山门。；focus_hierarchy=CHAR_HE_PINGSHENG；LOC_WAIMEN_JIUYUAN；CHAR_JIANG_JIAN/背影；CROWD_TAIXU_CULTIVATOR/远景剪影；CHAR_HE_SANJIE/回忆影；crowd_simplification=除贺平生外，所有人都按背影、侧背、剪影、虚化或旧物暗示处理；不得新增清晰父母死亡画面。；keyframe_plan=start=张老大手压在贺平生肩上，挑水命令落下，贺平生低头应是。；end=中段接力帧：回忆蒙太奇跨时间，需要中锚锁主角少年常态。；motion_control=level=degrade_only；reason=回忆群像不直接生成复杂连续动作，拆成空景/背影/远景剪影短镜。。
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=seedance，mode=native_av，native_audio_policy=native_speech，identity_requirement=character_id_or_reference_group；只使用 Seedance via Dreamina 已刷新证据支持的能力；失败按 degrade_plan 或 Motion Control degrade_only 停审，不临场改后端;
身份锁定约束：读取 identity_registry.json 和 identity_adapter_matrix.json；使用首/尾帧与 reference_group，保持 drift_forbidden=face_shape/hairstyle/outfit_palette/age/costume；角色=CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN, CHAR_HE_SANJIE, CROWD_TAIXU_CULTIVATOR;
近景身份锁定约束：CU/MCU/反打/说话镜优先脸部特写、表情参考、front/side/back reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；配角近景不稳则用 MCU/OTS/侧脸/手部/物件反应镜;
原生音画约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
人物运动：父母亡故、资源被抢。，江剑收拾行囊，把贺平生送向秀竹峰。;
镜头运动：匀速移镜头，横移跟随主体，保持轴线方向不反转，落到蒙太奇→WS; 后端控制写法：自然语言运镜：匀速移镜头，横移跟随主体，保持轴线方向不反转，落到蒙太奇→WS；首帧锚定，不改变角色、光位、轴线和场景设定。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=split_relay;
声音约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 张老大手压在贺平生肩上，挑水命令落下，贺平生低头应是。; action: 父母亡故、资源被抢。，江剑收拾行囊，把贺平生送向秀竹峰。; end: 中段接力帧：回忆蒙太奇跨时间，需要中锚锁主角少年常态。; constraints: 首帧=出图/第1集/图片/Clip03_外门遗孤.png; 尾帧=出图/第1集/图片/Clip03_外门遗孤_mid.png; asset_ids=LOC_WAIMEN_JIUYUAN, 旧行囊, 秀竹峰山门; character_ids=CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN, CHAR_HE_SANJIE, CROWD_TAIXU_CULTIVATOR; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 动作过程需要空间方向清楚；匀速移镜比自由漂浮更容易守轴线和人物站位。; camera motion: 匀速移镜头，横移跟随主体，保持轴线方向不反转，落到蒙太奇→WS; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。.
identity constraint: use identity_registry, reference_group, face anchors, and expression references; preserve facial proportions, hairstyle, accessories, outfit palette, age, and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group.
audio constraint: native speech is intentional, keep original generated clip audio and verify lip sync.
```

### 检查清单（视频三件套自查）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、身份锁定、原生音画策略与 route 一致

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然
- [ ] 镜头运动符合 prompt
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 06（时长 11s · EP01_CLIP06 · 外门遗孤下）

**首帧**：`出图/第1集/图片/Clip03_外门遗孤_mid.png`
**尾帧**：`出图/第1集/图片/Clip03_外门遗孤_end.png`
**中段锚帧豁免**：本 Clip 是视频 preflight 按原中段锚帧拆出的短半段；旧中帧已作为段边界尾帧/首帧复用，内部不再新增中段锚帧。
**场景**：太虚门外门旧院/日/回忆
**导演意图**：动作过程需要空间方向清楚；匀速移镜比自由漂浮更容易守轴线和人物站位。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在蒙太奇→WS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：贺平生站画左前院门边；CHAR_JIANG_JIAN/背影在中景偏右；CHAR_HE_SANJIE/回忆影只作旧影或旧物暗示；CROWD_TAIXU_CULTIVATOR/远景剪影在画面深处山间云雾里。；回忆蒙太奇低饱和柔冷光，慢推或固定切片；不做无动机环绕，不切成血腥事件。
**表演节拍**：[0-4s] 江剑收拾行囊，把贺平生送向秀竹峰。（中景背影）；[4-11s] 贺平生看远处修士剪影掠过山间云雾，决定留下。（远景抬头）；微表情/表情幅度：贺平生：回忆中沉默低眼，望向远处修士剪影时眼睑微抬，呼吸变稳。
**三轨音频**：旁白音频后期 compose 叠加；视频生成阶段不要生成旁白音频，只允许画内角色对白口型。
**运动精修**：张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。；身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：旧院尘土、低饱和天光和山间薄雾轻动，非主角人物保持背影、剪影或虚化。
**涉及资产**：LOC_WAIMEN_JIUYUAN, 旧行囊, 秀竹峰山门

**专项镜头模板**：template_id=ensemble_blocking；beats=旧院空景和旧行囊暗示前情；幼年贺平生短闪；江剑背影收拾行囊；十四岁贺平生望向远处修士剪影；blocking=贺平生站画左前院门边；CHAR_JIANG_JIAN/背影在中景偏右；CHAR_HE_SANJIE/回忆影只作旧影或旧物暗示；CROWD_TAIXU_CULTIVATOR/远景剪影在画面深处山间云雾里。；camera_rule=回忆蒙太奇低饱和柔冷光，慢推或固定切片；不做无动机环绕，不切成血腥事件。；continuity_must=贺平生年龄形态与 identity_registry 对齐；江剑只背影/侧背；贺三杰不清晰露脸；远景修士只小比例剪影；外门旧院不豪华化；negative=不要清晰父母死亡；不要血腥；不要豪华宗门正殿；不要现代校园；不要新增清晰陌生脸；screen_positions=LEFT_FOREGROUND=CHAR_HE_PINGSHENG/常态或幼年，唯一可清晰脸。；MID_RIGHT=CHAR_JIANG_JIAN/背影，不露清晰正脸。；BACKGROUND_MEMORY=CHAR_HE_SANJIE/回忆影，只用旧影/旧物，不画死亡细节。；FAR_BACKGROUND=CROWD_TAIXU_CULTIVATOR/远景剪影，小比例不露脸。；LOCATION_PLATE=LOC_WAIMEN_JIUYUAN 灰旧院门、低矮院墙、远处山门。；focus_hierarchy=CHAR_HE_PINGSHENG；LOC_WAIMEN_JIUYUAN；CHAR_JIANG_JIAN/背影；CROWD_TAIXU_CULTIVATOR/远景剪影；CHAR_HE_SANJIE/回忆影；crowd_simplification=除贺平生外，所有人都按背影、侧背、剪影、虚化或旧物暗示处理；不得新增清晰父母死亡画面。；keyframe_plan=start=中段接力帧：回忆蒙太奇跨时间，需要中锚锁主角少年常态。；end=贺平生站在秀竹峰杂役身份边缘，决定留下，离仙途更近一步。；motion_control=level=degrade_only；reason=回忆群像不直接生成复杂连续动作，拆成空景/背影/远景剪影短镜。。

**模型路由**：shot_type=ensemble_blocking; clip_characters=CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN, CHAR_HE_SANJIE; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; policy_resolution.winner=native_voice_fallback; risk_flags=identity_drift_risk, mouth_visible, multi_person, native_speech, seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

**动作编排契约 / Action Choreography**：无。

**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_06/motion_control_manifest.json；required_inputs=pose_sequence, depth_sequence, instance_masks；failure_modes=slot_drift, pose_drift, identity_drift；gate_policy=block_without_ready_manifest_or_degrade_only_manifest。

**角色身份注册层**：
- CHAR_HE_PINGSHENG（贺平生）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_贺平生.png; 出图/共享/图片/定妆_贺平生_侧.png; 出图/共享/图片/定妆_贺平生_背.png; 出图/共享/图片/定妆_贺平生_半身.png; 出图/共享/图片/定妆_贺平生_三视图.png; 出图/共享/图片/定妆_贺平生_脸部特写.png; 出图/共享/图片/定妆_贺平生_表情_克制.png; 出图/共享/图片/定妆_贺平生_表情_疲惫隐忍.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CHAR_JIANG_JIAN（江剑）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_江剑_背影.png; 出图/共享/图片/定妆_江剑_背影_侧.png; 出图/共享/图片/定妆_江剑_背影_背.png; 出图/共享/图片/定妆_江剑_背影_半身.png; 出图/共享/图片/定妆_江剑_背影_三视图.png; 出图/共享/图片/定妆_江剑_背影_侧背.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CHAR_HE_SANJIE（贺三杰）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_贺三杰_回忆影.png; 出图/共享/图片/定妆_贺三杰_回忆影_侧.png; 出图/共享/图片/定妆_贺三杰_回忆影_背.png; 出图/共享/图片/定妆_贺三杰_回忆影_半身.png; 出图/共享/图片/定妆_贺三杰_回忆影_三视图.png; 出图/共享/图片/定妆_贺三杰_回忆影_侧影.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CROWD_TAIXU_CULTIVATOR（太虚门远景修士剪影）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_远景修士剪影.png; 出图/共享/图片/定妆_远景修士剪影_侧.png; 出图/共享/图片/定妆_远景修士剪影_背.png; 出图/共享/图片/定妆_远景修士剪影_半身.png; 出图/共享/图片/定妆_远景修士剪影_三视图.png; 出图/共享/图片/定妆_远景修士剪影_sheet.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。

**近景/反打身份锁定**：主焦点角色=CHAR_HE_PINGSHENG（贺平生）、CHAR_JIANG_JIAN（江剑）、CHAR_HE_SANJIE（贺三杰）、CROWD_TAIXU_CULTIVATOR（太虚门远景修士剪影）；使用 identity_registry / identity_adapter_matrix / reference_group / face_anchor / expressions。锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；表情只动面部肌肉，不改脸型；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜，保留 story beat。

**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留

**衔接设计**：
- 入点：中段接力帧：回忆蒙太奇跨时间，需要中锚锁主角少年常态。
- 出点：贺平生站在秀竹峰杂役身份边缘，决定留下，离仙途更近一步。
- 转场：match_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：中段接力帧：回忆蒙太奇跨时间，需要中锚锁主角少年常态。
- action：江剑收拾行囊，把贺平生送向秀竹峰。，贺平生看远处修士剪影掠过山间云雾，决定留下。
- end_state：贺平生站在秀竹峰杂役身份边缘，决定留下，离仙途更近一步。
- constraints：首帧=出图/第1集/图片/Clip03_外门遗孤_mid.png; 尾帧=出图/第1集/图片/Clip03_外门遗孤_end.png; asset_ids=LOC_WAIMEN_JIUYUAN, 旧行囊, 秀竹峰山门; character_ids=CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN, CHAR_HE_SANJIE, CROWD_TAIXU_CULTIVATOR; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 中段接力帧：回忆蒙太奇跨时间，需要中锚锁主角少年常态。
  action: 江剑收拾行囊，把贺平生送向秀竹峰。，贺平生看远处修士剪影掠过山间云雾，决定留下。
  end_state: 贺平生站在秀竹峰杂役身份边缘，决定留下，离仙途更近一步。
  constraints: 首帧=出图/第1集/图片/Clip03_外门遗孤_mid.png; 尾帧=出图/第1集/图片/Clip03_外门遗孤_end.png; asset_ids=LOC_WAIMEN_JIUYUAN, 旧行囊, 秀竹峰山门; character_ids=CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN, CHAR_HE_SANJIE, CROWD_TAIXU_CULTIVATOR; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：动作过程需要空间方向清楚；匀速移镜比自由漂浮更容易守轴线和人物站位。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在蒙太奇→WS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：贺平生站画左前院门边；CHAR_JIANG_JIAN/背影在中景偏右；CHAR_HE_SANJIE/回忆影只作旧影或旧物暗示；CROWD_TAIXU_CULTIVATOR/远景剪影在画面深处山间云雾里。;
表演节拍：[0-4s] 江剑收拾行囊，把贺平生送向秀竹峰。（中景背影）；[4-11s] 贺平生看远处修士剪影掠过山间云雾，决定留下。（远景抬头）;
三轨音频：旁白音频后期 compose 叠加；本视频生成不要生成旁白音频，只允许画内角色对白口型;
运动精修约束：张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。; 身体守卫=脸部轮廓和发髻不拉伸，肩颈/手部不穿模，道具不粘连;
环境交互约束：旧院尘土、低饱和天光和山间薄雾轻动，非主角人物保持背影、剪影或虚化。;
专项模板约束：template_id=ensemble_blocking；beats=旧院空景和旧行囊暗示前情；幼年贺平生短闪；江剑背影收拾行囊；十四岁贺平生望向远处修士剪影；blocking=贺平生站画左前院门边；CHAR_JIANG_JIAN/背影在中景偏右；CHAR_HE_SANJIE/回忆影只作旧影或旧物暗示；CROWD_TAIXU_CULTIVATOR/远景剪影在画面深处山间云雾里。；camera_rule=回忆蒙太奇低饱和柔冷光，慢推或固定切片；不做无动机环绕，不切成血腥事件。；continuity_must=贺平生年龄形态与 identity_registry 对齐；江剑只背影/侧背；贺三杰不清晰露脸；远景修士只小比例剪影；外门旧院不豪华化；negative=不要清晰父母死亡；不要血腥；不要豪华宗门正殿；不要现代校园；不要新增清晰陌生脸；screen_positions=LEFT_FOREGROUND=CHAR_HE_PINGSHENG/常态或幼年，唯一可清晰脸。；MID_RIGHT=CHAR_JIANG_JIAN/背影，不露清晰正脸。；BACKGROUND_MEMORY=CHAR_HE_SANJIE/回忆影，只用旧影/旧物，不画死亡细节。；FAR_BACKGROUND=CROWD_TAIXU_CULTIVATOR/远景剪影，小比例不露脸。；LOCATION_PLATE=LOC_WAIMEN_JIUYUAN 灰旧院门、低矮院墙、远处山门。；focus_hierarchy=CHAR_HE_PINGSHENG；LOC_WAIMEN_JIUYUAN；CHAR_JIANG_JIAN/背影；CROWD_TAIXU_CULTIVATOR/远景剪影；CHAR_HE_SANJIE/回忆影；crowd_simplification=除贺平生外，所有人都按背影、侧背、剪影、虚化或旧物暗示处理；不得新增清晰父母死亡画面。；keyframe_plan=start=中段接力帧：回忆蒙太奇跨时间，需要中锚锁主角少年常态。；end=贺平生站在秀竹峰杂役身份边缘，决定留下，离仙途更近一步。；motion_control=level=degrade_only；reason=回忆群像不直接生成复杂连续动作，拆成空景/背影/远景剪影短镜。。
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=seedance，mode=native_av，native_audio_policy=native_speech，identity_requirement=character_id_or_reference_group；只使用 Seedance via Dreamina 已刷新证据支持的能力；失败按 degrade_plan 或 Motion Control degrade_only 停审，不临场改后端;
身份锁定约束：读取 identity_registry.json 和 identity_adapter_matrix.json；使用首/尾帧与 reference_group，保持 drift_forbidden=face_shape/hairstyle/outfit_palette/age/costume；角色=CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN, CHAR_HE_SANJIE, CROWD_TAIXU_CULTIVATOR;
近景身份锁定约束：CU/MCU/反打/说话镜优先脸部特写、表情参考、front/side/back reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；配角近景不稳则用 MCU/OTS/侧脸/手部/物件反应镜;
原生音画约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
人物运动：江剑收拾行囊，把贺平生送向秀竹峰。，贺平生看远处修士剪影掠过山间云雾，决定留下。;
镜头运动：匀速移镜头，横移跟随主体，保持轴线方向不反转，落到蒙太奇→WS; 后端控制写法：自然语言运镜：匀速移镜头，横移跟随主体，保持轴线方向不反转，落到蒙太奇→WS；首帧锚定，不改变角色、光位、轴线和场景设定。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=match_cut;
声音约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 中段接力帧：回忆蒙太奇跨时间，需要中锚锁主角少年常态。; action: 江剑收拾行囊，把贺平生送向秀竹峰。，贺平生看远处修士剪影掠过山间云雾，决定留下。; end: 贺平生站在秀竹峰杂役身份边缘，决定留下，离仙途更近一步。; constraints: 首帧=出图/第1集/图片/Clip03_外门遗孤_mid.png; 尾帧=出图/第1集/图片/Clip03_外门遗孤_end.png; asset_ids=LOC_WAIMEN_JIUYUAN, 旧行囊, 秀竹峰山门; character_ids=CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN, CHAR_HE_SANJIE, CROWD_TAIXU_CULTIVATOR; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 动作过程需要空间方向清楚；匀速移镜比自由漂浮更容易守轴线和人物站位。; camera motion: 匀速移镜头，横移跟随主体，保持轴线方向不反转，落到蒙太奇→WS; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。.
identity constraint: use identity_registry, reference_group, face anchors, and expression references; preserve facial proportions, hairstyle, accessories, outfit palette, age, and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group.
audio constraint: native speech is intentional, keep original generated clip audio and verify lip sync.
```

### 检查清单（视频三件套自查）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、身份锁定、原生音画策略与 route 一致

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然
- [ ] 镜头运动符合 prompt
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 07（时长 9.5s · EP01_CLIP07 · 两缸水和空屋上）

**首帧**：`出图/第1集/图片/Clip04_两缸水和空屋.png`
**尾帧**：`出图/第1集/图片/Clip04_两缸水和空屋_mid.png`
**中段锚帧豁免**：本 Clip 是视频 preflight 按原中段锚帧拆出的短半段；旧中帧已作为段边界尾帧/首帧复用，内部不再新增中段锚帧。
**场景**：秀竹峰水缸区/杂役院/日转夜
**导演意图**：对白/反打优先表演和脸稳；固定机位或微推比无目的漂移更有戏。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在WS→MS→空镜CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：shot_reverse_shot；多人同框执行策略：shot_reverse_shot_or_split_composite_required；韩老三和贺平生只在水缸远景短暂同框，近景拆成单人镜。；固定广角建立空间压迫，后接单人中景和空屋插入镜；不环绕，不交换左右站位。
**表演节拍**：[0-9.5s] 韩老三指两口巨大水缸，贺平生仰看。（广角WS）；微表情/表情幅度：贺平生：水缸前短暂怔住，空屋门口眼神收紧但不抱怨。
**三轨音频**：旁白音频后期 compose 叠加；视频生成阶段不要生成旁白音频，只允许画内角色对白口型。
**三轨修补**：屏幕文案（后期overlay）：一天至少二十趟；不得让视频模型生成文字，compose 阶段叠清晰字。
**运动精修**：张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。；身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：水缸冷湿反光、钥匙铁锁和空屋月光有轻微物理反馈，空间保持贫瘠不豪华化。
**涉及资产**：LOC_ZAYI_YUAN, PROP_KEY_LOCK, PROP_TIE_WAN, 两口水缸, 秀竹峰水缸区

**专项镜头模板**：template_id=multi_character_same_frame；beats=韩老三指向两口水缸；贺平生仰看水缸；韩老三交钥匙离开；空屋只剩铁碗和冷月光；blocking=贺平生画左后，韩老三画右前，两口水缸占后景；近景拆成单人镜，只有水缸远景短暂同框。；camera_rule=固定广角建立空间压迫，后接单人中景和空屋插入镜；不环绕，不交换左右站位。；continuity_must=贺平生始终画左或画左后；韩老三不遮挡贺平生正脸；两口水缸后景比例保持巨大；negative=不要让两张脸同时抢焦点；不要新增具名角色；不要把水缸区画成仙宫庭院；overlap_rules=韩老三可侧脸虚焦；韩老三不可遮挡贺平生眼睛；两口水缸可遮挡身体下半部分但不挡主角脸。

**模型路由**：shot_type=multi_character_same_frame; clip_characters=CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=none; policy_resolution.winner=native_voice_fallback; risk_flags=mouth_visible, multi_person, native_speech, seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

**动作编排契约 / Action Choreography**：无。

**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_07/motion_control_manifest.json；required_inputs=pose_sequence, depth_sequence, instance_masks；failure_modes=slot_drift, pose_drift, identity_drift；gate_policy=block_without_ready_manifest_or_degrade_only_manifest。

**角色身份注册层**：
- CHAR_HE_PINGSHENG（贺平生）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_贺平生.png; 出图/共享/图片/定妆_贺平生_侧.png; 出图/共享/图片/定妆_贺平生_背.png; 出图/共享/图片/定妆_贺平生_半身.png; 出图/共享/图片/定妆_贺平生_三视图.png; 出图/共享/图片/定妆_贺平生_脸部特写.png; 出图/共享/图片/定妆_贺平生_表情_克制.png; 出图/共享/图片/定妆_贺平生_表情_疲惫隐忍.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CHAR_HAN_LAOSAN（韩老三）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_韩老三.png; 出图/共享/图片/定妆_韩老三_侧.png; 出图/共享/图片/定妆_韩老三_背.png; 出图/共享/图片/定妆_韩老三_半身.png; 出图/共享/图片/定妆_韩老三_三视图.png; 出图/共享/图片/定妆_韩老三_脸部特写.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。

**近景/反打身份锁定**：主焦点角色=CHAR_HE_PINGSHENG（贺平生）、CHAR_HAN_LAOSAN（韩老三）；使用 identity_registry / identity_adapter_matrix / reference_group / face_anchor / expressions。锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；表情只动面部肌肉，不改脸型；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜，保留 story beat。

**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留

**衔接设计**：
- 入点：贺平生站在秀竹峰杂役身份边缘，决定留下，离仙途更近一步。
- 出点：中段接力帧：从水缸区切空屋，需锁空间贫瘠感和主角状态。
- 转场：split_relay
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：贺平生站在秀竹峰杂役身份边缘，决定留下，离仙途更近一步。
- action：韩老三指两口巨大水缸，贺平生仰看。
- end_state：中段接力帧：从水缸区切空屋，需锁空间贫瘠感和主角状态。
- constraints：首帧=出图/第1集/图片/Clip04_两缸水和空屋.png; 尾帧=出图/第1集/图片/Clip04_两缸水和空屋_mid.png; asset_ids=LOC_ZAYI_YUAN, PROP_KEY_LOCK, PROP_TIE_WAN, 两口水缸, 秀竹峰水缸区; character_ids=CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 贺平生站在秀竹峰杂役身份边缘，决定留下，离仙途更近一步。
  action: 韩老三指两口巨大水缸，贺平生仰看。
  end_state: 中段接力帧：从水缸区切空屋，需锁空间贫瘠感和主角状态。
  constraints: 首帧=出图/第1集/图片/Clip04_两缸水和空屋.png; 尾帧=出图/第1集/图片/Clip04_两缸水和空屋_mid.png; asset_ids=LOC_ZAYI_YUAN, PROP_KEY_LOCK, PROP_TIE_WAN, 两口水缸, 秀竹峰水缸区; character_ids=CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：对白/反打优先表演和脸稳；固定机位或微推比无目的漂移更有戏。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在WS→MS→空镜CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：贺平生画左后，韩老三画右前，两口水缸占后景；近景拆成单人镜，只有水缸远景短暂同框。;
表演节拍：[0-9.5s] 韩老三指两口巨大水缸，贺平生仰看。（广角WS）;
三轨音频：旁白音频后期 compose 叠加；本视频生成不要生成旁白音频，只允许画内角色对白口型;
三轨修补：屏幕文案仅后期overlay显示「一天至少二十趟」，本视频生成不要画字、不要生成字幕卡、不要生成logo;
运动精修约束：张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。; 身体守卫=脸部轮廓和发髻不拉伸，肩颈/手部不穿模，道具不粘连;
环境交互约束：水缸冷湿反光、钥匙铁锁和空屋月光有轻微物理反馈，空间保持贫瘠不豪华化。;
专项模板约束：template_id=multi_character_same_frame；beats=韩老三指向两口水缸；贺平生仰看水缸；韩老三交钥匙离开；空屋只剩铁碗和冷月光；blocking=贺平生画左后，韩老三画右前，两口水缸占后景；近景拆成单人镜，只有水缸远景短暂同框。；camera_rule=固定广角建立空间压迫，后接单人中景和空屋插入镜；不环绕，不交换左右站位。；continuity_must=贺平生始终画左或画左后；韩老三不遮挡贺平生正脸；两口水缸后景比例保持巨大；negative=不要让两张脸同时抢焦点；不要新增具名角色；不要把水缸区画成仙宫庭院；overlap_rules=韩老三可侧脸虚焦；韩老三不可遮挡贺平生眼睛；两口水缸可遮挡身体下半部分但不挡主角脸。
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=seedance，mode=native_av，native_audio_policy=native_speech，identity_requirement=none；只使用 Seedance via Dreamina 已刷新证据支持的能力；失败按 degrade_plan 或 Motion Control degrade_only 停审，不临场改后端;
身份锁定约束：读取 identity_registry.json 和 identity_adapter_matrix.json；使用首/尾帧与 reference_group，保持 drift_forbidden=face_shape/hairstyle/outfit_palette/age/costume；角色=CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN;
近景身份锁定约束：CU/MCU/反打/说话镜优先脸部特写、表情参考、front/side/back reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；配角近景不稳则用 MCU/OTS/侧脸/手部/物件反应镜;
原生音画约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
人物运动：韩老三指两口巨大水缸，贺平生仰看。;
镜头运动：固定机位，过肩/反打保持轴线，只允许呼吸式微推，只允许轻微呼吸式微动; 后端控制写法：自然语言运镜：固定机位，过肩/反打保持轴线，只允许呼吸式微推，只允许轻微呼吸式微动；首帧锚定，不改变角色、光位、轴线和场景设定。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=split_relay;
声音约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 贺平生站在秀竹峰杂役身份边缘，决定留下，离仙途更近一步。; action: 韩老三指两口巨大水缸，贺平生仰看。; end: 中段接力帧：从水缸区切空屋，需锁空间贫瘠感和主角状态。; constraints: 首帧=出图/第1集/图片/Clip04_两缸水和空屋.png; 尾帧=出图/第1集/图片/Clip04_两缸水和空屋_mid.png; asset_ids=LOC_ZAYI_YUAN, PROP_KEY_LOCK, PROP_TIE_WAN, 两口水缸, 秀竹峰水缸区; character_ids=CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 对白/反打优先表演和脸稳；固定机位或微推比无目的漂移更有戏。; camera motion: 固定机位，过肩/反打保持轴线，只允许呼吸式微推，只允许轻微呼吸式微动; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。.
identity constraint: use identity_registry, reference_group, face anchors, and expression references; preserve facial proportions, hairstyle, accessories, outfit palette, age, and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=none.
audio constraint: native speech is intentional, keep original generated clip audio and verify lip sync.
```

### 检查清单（视频三件套自查）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、身份锁定、原生音画策略与 route 一致

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然
- [ ] 镜头运动符合 prompt
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸
## Clip 08（时长 9.5s · EP01_CLIP08 · 两缸水和空屋下）

**首帧**：`出图/第1集/图片/Clip04_两缸水和空屋_mid.png`
**尾帧**：`出图/第1集/图片/Clip04_两缸水和空屋_end.png`
**中段锚帧豁免**：本 Clip 是视频 preflight 按原中段锚帧拆出的短半段；旧中帧已作为段边界尾帧/首帧复用，内部不再新增中段锚帧。
**场景**：秀竹峰水缸区/杂役院/日转夜
**导演意图**：对白/反打优先表演和脸稳；固定机位或微推比无目的漂移更有戏。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在WS→MS→空镜CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：shot_reverse_shot；多人同框执行策略：shot_reverse_shot_or_split_composite_required；韩老三和贺平生只在水缸远景短暂同框，近景拆成单人镜。；固定广角建立空间压迫，后接单人中景和空屋插入镜；不环绕，不交换左右站位。
**表演节拍**：[0-0.5s] 韩老三指两口巨大水缸，贺平生仰看。（广角WS）；[0.5-9.5s] 韩老三交钥匙离开，空房只剩铁碗和冷月光。（MS到空镜）；微表情/表情幅度：贺平生：水缸前短暂怔住，空屋门口眼神收紧但不抱怨。
**三轨音频**：旁白音频后期 compose 叠加；视频生成阶段不要生成旁白音频，只允许画内角色对白口型。
**运动精修**：张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。；身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：水缸冷湿反光、钥匙铁锁和空屋月光有轻微物理反馈，空间保持贫瘠不豪华化。
**涉及资产**：LOC_ZAYI_YUAN, PROP_KEY_LOCK, PROP_TIE_WAN, 两口水缸, 秀竹峰水缸区

**专项镜头模板**：template_id=multi_character_same_frame；beats=韩老三指向两口水缸；贺平生仰看水缸；韩老三交钥匙离开；空屋只剩铁碗和冷月光；blocking=贺平生画左后，韩老三画右前，两口水缸占后景；近景拆成单人镜，只有水缸远景短暂同框。；camera_rule=固定广角建立空间压迫，后接单人中景和空屋插入镜；不环绕，不交换左右站位。；continuity_must=贺平生始终画左或画左后；韩老三不遮挡贺平生正脸；两口水缸后景比例保持巨大；negative=不要让两张脸同时抢焦点；不要新增具名角色；不要把水缸区画成仙宫庭院；overlap_rules=韩老三可侧脸虚焦；韩老三不可遮挡贺平生眼睛；两口水缸可遮挡身体下半部分但不挡主角脸。

**模型路由**：shot_type=multi_character_same_frame; clip_characters=CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=none; policy_resolution.winner=native_voice_fallback; risk_flags=mouth_visible, multi_person, native_speech, seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

**动作编排契约 / Action Choreography**：无。

**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_08/motion_control_manifest.json；required_inputs=pose_sequence, depth_sequence, instance_masks；failure_modes=slot_drift, pose_drift, identity_drift；gate_policy=block_without_ready_manifest_or_degrade_only_manifest。

**角色身份注册层**：
- CHAR_HE_PINGSHENG（贺平生）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_贺平生.png; 出图/共享/图片/定妆_贺平生_侧.png; 出图/共享/图片/定妆_贺平生_背.png; 出图/共享/图片/定妆_贺平生_半身.png; 出图/共享/图片/定妆_贺平生_三视图.png; 出图/共享/图片/定妆_贺平生_脸部特写.png; 出图/共享/图片/定妆_贺平生_表情_克制.png; 出图/共享/图片/定妆_贺平生_表情_疲惫隐忍.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。
- CHAR_HAN_LAOSAN（韩老三）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_韩老三.png; 出图/共享/图片/定妆_韩老三_侧.png; 出图/共享/图片/定妆_韩老三_背.png; 出图/共享/图片/定妆_韩老三_半身.png; 出图/共享/图片/定妆_韩老三_三视图.png; 出图/共享/图片/定妆_韩老三_脸部特写.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。

**近景/反打身份锁定**：主焦点角色=CHAR_HE_PINGSHENG（贺平生）、CHAR_HAN_LAOSAN（韩老三）；使用 identity_registry / identity_adapter_matrix / reference_group / face_anchor / expressions。锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；表情只动面部肌肉，不改脸型；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜，保留 story beat。

**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留

**衔接设计**：
- 入点：中段接力帧：从水缸区切空屋，需锁空间贫瘠感和主角状态。
- 出点：贺平生站在空房门口，手里只有钥匙、铁锁和铁碗。
- 转场：action_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：中段接力帧：从水缸区切空屋，需锁空间贫瘠感和主角状态。
- action：韩老三指两口巨大水缸，贺平生仰看。，韩老三交钥匙离开，空房只剩铁碗和冷月光。
- end_state：贺平生站在空房门口，手里只有钥匙、铁锁和铁碗。
- constraints：首帧=出图/第1集/图片/Clip04_两缸水和空屋_mid.png; 尾帧=出图/第1集/图片/Clip04_两缸水和空屋_end.png; asset_ids=LOC_ZAYI_YUAN, PROP_KEY_LOCK, PROP_TIE_WAN, 两口水缸, 秀竹峰水缸区; character_ids=CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 中段接力帧：从水缸区切空屋，需锁空间贫瘠感和主角状态。
  action: 韩老三指两口巨大水缸，贺平生仰看。，韩老三交钥匙离开，空房只剩铁碗和冷月光。
  end_state: 贺平生站在空房门口，手里只有钥匙、铁锁和铁碗。
  constraints: 首帧=出图/第1集/图片/Clip04_两缸水和空屋_mid.png; 尾帧=出图/第1集/图片/Clip04_两缸水和空屋_end.png; asset_ids=LOC_ZAYI_YUAN, PROP_KEY_LOCK, PROP_TIE_WAN, 两口水缸, 秀竹峰水缸区; character_ids=CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：对白/反打优先表演和脸稳；固定机位或微推比无目的漂移更有戏。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在WS→MS→空镜CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：贺平生画左后，韩老三画右前，两口水缸占后景；近景拆成单人镜，只有水缸远景短暂同框。;
表演节拍：[0-0.5s] 韩老三指两口巨大水缸，贺平生仰看。（广角WS）；[0.5-9.5s] 韩老三交钥匙离开，空房只剩铁碗和冷月光。（MS到空镜）;
三轨音频：旁白音频后期 compose 叠加；本视频生成不要生成旁白音频，只允许画内角色对白口型;
运动精修约束：张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。; 身体守卫=脸部轮廓和发髻不拉伸，肩颈/手部不穿模，道具不粘连;
环境交互约束：水缸冷湿反光、钥匙铁锁和空屋月光有轻微物理反馈，空间保持贫瘠不豪华化。;
专项模板约束：template_id=multi_character_same_frame；beats=韩老三指向两口水缸；贺平生仰看水缸；韩老三交钥匙离开；空屋只剩铁碗和冷月光；blocking=贺平生画左后，韩老三画右前，两口水缸占后景；近景拆成单人镜，只有水缸远景短暂同框。；camera_rule=固定广角建立空间压迫，后接单人中景和空屋插入镜；不环绕，不交换左右站位。；continuity_must=贺平生始终画左或画左后；韩老三不遮挡贺平生正脸；两口水缸后景比例保持巨大；negative=不要让两张脸同时抢焦点；不要新增具名角色；不要把水缸区画成仙宫庭院；overlap_rules=韩老三可侧脸虚焦；韩老三不可遮挡贺平生眼睛；两口水缸可遮挡身体下半部分但不挡主角脸。
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=seedance，mode=native_av，native_audio_policy=native_speech，identity_requirement=none；只使用 Seedance via Dreamina 已刷新证据支持的能力；失败按 degrade_plan 或 Motion Control degrade_only 停审，不临场改后端;
身份锁定约束：读取 identity_registry.json 和 identity_adapter_matrix.json；使用首/尾帧与 reference_group，保持 drift_forbidden=face_shape/hairstyle/outfit_palette/age/costume；角色=CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN;
近景身份锁定约束：CU/MCU/反打/说话镜优先脸部特写、表情参考、front/side/back reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；配角近景不稳则用 MCU/OTS/侧脸/手部/物件反应镜;
原生音画约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
人物运动：韩老三指两口巨大水缸，贺平生仰看。，韩老三交钥匙离开，空房只剩铁碗和冷月光。;
镜头运动：固定机位，过肩/反打保持轴线，只允许呼吸式微推，只允许轻微呼吸式微动; 后端控制写法：自然语言运镜：固定机位，过肩/反打保持轴线，只允许呼吸式微推，只允许轻微呼吸式微动；首帧锚定，不改变角色、光位、轴线和场景设定。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=action_cut;
声音约束：台词、口型和保留原片音轨由原生音画后端生成；声源归属=画内说话主体；compose_policy=保留原片音轨；生成后复核口型同步。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 中段接力帧：从水缸区切空屋，需锁空间贫瘠感和主角状态。; action: 韩老三指两口巨大水缸，贺平生仰看。，韩老三交钥匙离开，空房只剩铁碗和冷月光。; end: 贺平生站在空房门口，手里只有钥匙、铁锁和铁碗。; constraints: 首帧=出图/第1集/图片/Clip04_两缸水和空屋_mid.png; 尾帧=出图/第1集/图片/Clip04_两缸水和空屋_end.png; asset_ids=LOC_ZAYI_YUAN, PROP_KEY_LOCK, PROP_TIE_WAN, 两口水缸, 秀竹峰水缸区; character_ids=CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 对白/反打优先表演和脸稳；固定机位或微推比无目的漂移更有戏。; camera motion: 固定机位，过肩/反打保持轴线，只允许呼吸式微推，只允许轻微呼吸式微动; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。.
identity constraint: use identity_registry, reference_group, face anchors, and expression references; preserve facial proportions, hairstyle, accessories, outfit palette, age, and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=none.
audio constraint: native speech is intentional, keep original generated clip audio and verify lip sync.
```

### 检查清单（视频三件套自查）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、身份锁定、原生音画策略与 route 一致

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然
- [ ] 镜头运动符合 prompt
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 09（时长 10s · EP01_CLIP09 · 夜挑五趟上）

**首帧**：`出图/第1集/图片/Clip05_夜挑五趟.png`
**尾帧**：`出图/第1集/图片/Clip05_夜挑五趟_mid.png`
**中段锚帧豁免**：本 Clip 是视频 preflight 按原中段锚帧拆出的短半段；旧中帧已作为段边界尾帧/首帧复用，内部不再新增中段锚帧。
**场景**：杂役院门口/后山山路/后山山泉浅潭/夜
**导演意图**：默认给镜头一点目的性：轻微推近能增加叙事关注，同时风险低。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在MS→montage→CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：主体位置、前后景、视线和轴线继承 storyboard。；
**表演节拍**：[0-5s] 贺平生锁门后决定先去认路。（MS）；[5-10s] 挑桶、山路、喘息、扁担压肩，重复到第五趟。（动作蒙太奇）；微表情/表情幅度：贺平生：自语时抿唇下定决心，挑水后眼睑疲惫，看到微光时眼睛微睁。
**三轨音频**：旁白音频后期 compose 叠加；视频生成阶段不要生成旁白音频，只允许画内角色对白口型。
**运动精修**：张力=聚焦；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。；身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：冷蓝月光、水面细波、桶中水晃和黑陶盆湿痕只随可见动作触发。
**涉及资产**：LOC_HOUSHAN_QIANTAN, LOC_ZAYI_YUAN, PROP_SHUI_TONG, 后山山路, 扁担

**专项镜头模板**：无。

**模型路由**：shot_type=general_motion; clip_characters=CHAR_HE_PINGSHENG; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; policy_resolution.winner=cost_quality_tier; risk_flags=seam_relay; degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.

**动作编排契约 / Action Choreography**：无。挑水负重蒙太奇不使用 road_vehicle/高速追逐模板；节奏由 Motion Control degrade_only 拆镜控制。

**Motion Control / 物理交互控制**：level=degrade_only；manifest_path=出视频/第1集/control/Clip_09/motion_control_manifest.json；required_inputs=depth_sequence, camera_path, spatial_path, parallax_layers；failure_modes=pose_drift, prop_merge, identity_drift, direction_flip；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；degrade_plan=肩颈红痕特写、扁担/水桶晃动特写、山路脚步、水面反光、主角疲惫反应镜，结尾稳定到中段接力帧。

**角色身份注册层**：
- CHAR_HE_PINGSHENG（贺平生）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_贺平生.png; 出图/共享/图片/定妆_贺平生_侧.png; 出图/共享/图片/定妆_贺平生_背.png; 出图/共享/图片/定妆_贺平生_半身.png; 出图/共享/图片/定妆_贺平生_三视图.png; 出图/共享/图片/定妆_贺平生_脸部特写.png; 出图/共享/图片/定妆_贺平生_表情_克制.png; 出图/共享/图片/定妆_贺平生_表情_疲惫隐忍.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。

**近景/反打身份锁定**：主焦点角色=CHAR_HE_PINGSHENG（贺平生）；使用 identity_registry / identity_adapter_matrix / reference_group / face_anchor / expressions。锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；表情只动面部肌肉，不改脸型；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜，保留 story beat。

**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=no_dialogue；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱

**衔接设计**：
- 入点：贺平生站在空房门口，手里只有钥匙、铁锁和铁碗。
- 出点：中段接力帧：挑水蒙太奇跨度大，需中锚锁扁担、水桶、肩颈红痕。
- 转场：split_relay
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：贺平生站在空房门口，手里只有钥匙、铁锁和铁碗。
- action：贺平生锁门后决定先去认路。，挑桶、山路、喘息、扁担压肩，重复到第五趟。
- end_state：中段接力帧：挑水蒙太奇跨度大，需中锚锁扁担、水桶、肩颈红痕。
- constraints：首帧=出图/第1集/图片/Clip05_夜挑五趟.png; 尾帧=出图/第1集/图片/Clip05_夜挑五趟_mid.png; asset_ids=LOC_HOUSHAN_QIANTAN, LOC_ZAYI_YUAN, PROP_SHUI_TONG, 后山山路, 扁担; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 贺平生站在空房门口，手里只有钥匙、铁锁和铁碗。
  action: 贺平生锁门后决定先去认路。，挑桶、山路、喘息、扁担压肩，重复到第五趟。
  end_state: 中段接力帧：挑水蒙太奇跨度大，需中锚锁扁担、水桶、肩颈红痕。
  constraints: 首帧=出图/第1集/图片/Clip05_夜挑五趟.png; 尾帧=出图/第1集/图片/Clip05_夜挑五趟_mid.png; asset_ids=LOC_HOUSHAN_QIANTAN, LOC_ZAYI_YUAN, PROP_SHUI_TONG, 后山山路, 扁担; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：默认给镜头一点目的性：轻微推近能增加叙事关注，同时风险低。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在MS→montage→CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：继承 storyboard 槽位;
表演节拍：[0-5s] 贺平生锁门后决定先去认路。（MS）；[5-10s] 挑桶、山路、喘息、扁担压肩，重复到第五趟。（动作蒙太奇）;
三轨音频：旁白音频后期 compose 叠加；本视频生成不要生成旁白音频，只允许画内角色对白口型;
运动精修约束：张力=聚焦；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。; 身体守卫=脸部轮廓和发髻不拉伸，肩颈/手部不穿模，道具不粘连;
环境交互约束：冷蓝月光、水面细波、桶中水晃和黑陶盆湿痕只随可见动作触发。;
专项模板约束：无。
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=seedance，mode=image2video，native_audio_policy=none，identity_requirement=reference_group；只使用 Seedance via Dreamina 已刷新证据支持的能力；失败按 degrade_plan 或 Motion Control degrade_only 停审，不临场改后端;
身份锁定约束：读取 identity_registry.json 和 identity_adapter_matrix.json；使用首/尾帧与 reference_group，保持 drift_forbidden=face_shape/hairstyle/outfit_palette/age/costume；角色=CHAR_HE_PINGSHENG;
近景身份锁定约束：CU/MCU/反打/说话镜优先脸部特写、表情参考、front/side/back reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；配角近景不稳则用 MCU/OTS/侧脸/手部/物件反应镜;
物理交互约束：按 Motion Control degrade_only 执行，只做低幅步行/肩颈压痕/水桶晃动/脚步/水面反光/疲惫反应镜；不生成车辆、车道、车轮或高速运动；检查 FeatureMelting，扁担和水桶不得并入身体;
原生音画约束：无对白、无旁白、不要生成原生人声；如产生原生音轨，compose 默认丢弃。
人物运动：贺平生锁门后决定先去认路。，挑桶、山路、喘息、扁担压肩，重复到第五趟。;
镜头运动：轻微推镜头，沿主体动作/视线方向轻推，落到MS→montage→CU; 后端控制写法：自然语言运镜：轻微推镜头，沿主体动作/视线方向轻推，落到MS→montage→CU；首帧锚定，不改变角色、光位、轴线和场景设定。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=split_relay;
声音约束：无对白、无旁白、不要生成原生人声；如产生原生音轨，compose 默认丢弃。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 贺平生站在空房门口，手里只有钥匙、铁锁和铁碗。; action: 贺平生锁门后决定先去认路。，挑桶、山路、喘息、扁担压肩，重复到第五趟。; end: 中段接力帧：挑水蒙太奇跨度大，需中锚锁扁担、水桶、肩颈红痕。; constraints: 首帧=出图/第1集/图片/Clip05_夜挑五趟.png; 尾帧=出图/第1集/图片/Clip05_夜挑五趟_mid.png; asset_ids=LOC_HOUSHAN_QIANTAN, LOC_ZAYI_YUAN, PROP_SHUI_TONG, 后山山路, 扁担; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 默认给镜头一点目的性：轻微推近能增加叙事关注，同时风险低。; camera motion: 轻微推镜头，沿主体动作/视线方向轻推，落到MS→montage→CU; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。.
identity constraint: use identity_registry, reference_group, face anchors, and expression references; preserve facial proportions, hairstyle, accessories, outfit palette, age, and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group.
audio constraint: no dialogue, no narration, no generated native voice.
```

### 检查清单（视频三件套自查）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、身份锁定、原生音画策略与 route 一致

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：肩颈、手部、扁担、水桶不穿模不融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 10（时长 10s · EP01_CLIP10 · 夜挑五趟下）

**首帧**：`出图/第1集/图片/Clip05_夜挑五趟_mid.png`
**尾帧**：`出图/第1集/图片/Clip05_夜挑五趟_end.png`
**中段锚帧豁免**：本 Clip 是视频 preflight 按原中段锚帧拆出的短半段；旧中帧已作为段边界尾帧/首帧复用，内部不再新增中段锚帧。
**场景**：杂役院门口/后山山路/后山山泉浅潭/夜
**导演意图**：默认给镜头一点目的性：轻微推近能增加叙事关注，同时风险低。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在MS→montage→CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：主体位置、前后景、视线和轴线继承 storyboard。；
**表演节拍**：[0-3s] 挑桶、山路、喘息、扁担压肩，重复到第五趟。（动作蒙太奇）；[3-10s] 第五次到潭边，水下出现一点微光。（低机位CU）；微表情/表情幅度：贺平生：自语时抿唇下定决心，挑水后眼睑疲惫，看到微光时眼睛微睁。
**三轨音频**：旁白音频后期 compose 叠加；视频生成阶段不要生成旁白音频，只允许画内角色对白口型。
**三轨修补**：屏幕文案（后期overlay）：第五趟，夜已深；不得让视频模型生成文字，compose 阶段叠清晰字。
**运动精修**：张力=聚焦；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。；身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：冷蓝月光、水面细波、桶中水晃和黑陶盆湿痕只随可见动作触发。
**涉及资产**：LOC_HOUSHAN_QIANTAN, LOC_ZAYI_YUAN, PROP_SHUI_TONG, 后山山路, 扁担

**专项镜头模板**：无。

**模型路由**：shot_type=general_motion; clip_characters=CHAR_HE_PINGSHENG; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; policy_resolution.winner=cost_quality_tier; risk_flags=seam_relay; degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.

**动作编排契约 / Action Choreography**：无。挑水负重蒙太奇不使用 road_vehicle/高速追逐模板；节奏由 Motion Control degrade_only 拆镜控制。

**Motion Control / 物理交互控制**：level=degrade_only；manifest_path=出视频/第1集/control/Clip_10/motion_control_manifest.json；required_inputs=depth_sequence, camera_path, spatial_path, parallax_layers；failure_modes=pose_drift, prop_merge, identity_drift, direction_flip；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；degrade_plan=承接中段帧、放下水桶、俯身看水、手部拨开水面、微光反射到脸侧，结尾稳定到 Clip05_end。

**角色身份注册层**：
- CHAR_HE_PINGSHENG（贺平生）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_贺平生.png; 出图/共享/图片/定妆_贺平生_侧.png; 出图/共享/图片/定妆_贺平生_背.png; 出图/共享/图片/定妆_贺平生_半身.png; 出图/共享/图片/定妆_贺平生_三视图.png; 出图/共享/图片/定妆_贺平生_脸部特写.png; 出图/共享/图片/定妆_贺平生_表情_克制.png; 出图/共享/图片/定妆_贺平生_表情_疲惫隐忍.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。

**近景/反打身份锁定**：主焦点角色=CHAR_HE_PINGSHENG（贺平生）；使用 identity_registry / identity_adapter_matrix / reference_group / face_anchor / expressions。锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；表情只动面部肌肉，不改脸型；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜，保留 story beat。

**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=no_dialogue；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱

**衔接设计**：
- 入点：中段接力帧：挑水蒙太奇跨度大，需中锚锁扁担、水桶、肩颈红痕。
- 出点：夜潭水面反出一点微光，贺平生停住脚步。
- 转场：j_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：中段接力帧：挑水蒙太奇跨度大，需中锚锁扁担、水桶、肩颈红痕。
- action：挑桶、山路、喘息、扁担压肩，重复到第五趟。，第五次到潭边，水下出现一点微光。
- end_state：夜潭水面反出一点微光，贺平生停住脚步。
- constraints：首帧=出图/第1集/图片/Clip05_夜挑五趟_mid.png; 尾帧=出图/第1集/图片/Clip05_夜挑五趟_end.png; asset_ids=LOC_HOUSHAN_QIANTAN, LOC_ZAYI_YUAN, PROP_SHUI_TONG, 后山山路, 扁担; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 中段接力帧：挑水蒙太奇跨度大，需中锚锁扁担、水桶、肩颈红痕。
  action: 挑桶、山路、喘息、扁担压肩，重复到第五趟。，第五次到潭边，水下出现一点微光。
  end_state: 夜潭水面反出一点微光，贺平生停住脚步。
  constraints: 首帧=出图/第1集/图片/Clip05_夜挑五趟_mid.png; 尾帧=出图/第1集/图片/Clip05_夜挑五趟_end.png; asset_ids=LOC_HOUSHAN_QIANTAN, LOC_ZAYI_YUAN, PROP_SHUI_TONG, 后山山路, 扁担; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：默认给镜头一点目的性：轻微推近能增加叙事关注，同时风险低。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在MS→montage→CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：继承 storyboard 槽位;
表演节拍：[0-3s] 挑桶、山路、喘息、扁担压肩，重复到第五趟。（动作蒙太奇）；[3-10s] 第五次到潭边，水下出现一点微光。（低机位CU）;
三轨音频：旁白音频后期 compose 叠加；本视频生成不要生成旁白音频，只允许画内角色对白口型;
三轨修补：屏幕文案仅后期overlay显示「第五趟，夜已深」，本视频生成不要画字、不要生成字幕卡、不要生成logo;
运动精修约束：张力=聚焦；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。; 身体守卫=脸部轮廓和发髻不拉伸，肩颈/手部不穿模，道具不粘连;
环境交互约束：冷蓝月光、水面细波、桶中水晃和黑陶盆湿痕只随可见动作触发。;
专项模板约束：无。
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=seedance，mode=image2video，native_audio_policy=none，identity_requirement=reference_group；只使用 Seedance via Dreamina 已刷新证据支持的能力；失败按 degrade_plan 或 Motion Control degrade_only 停审，不临场改后端;
身份锁定约束：读取 identity_registry.json 和 identity_adapter_matrix.json；使用首/尾帧与 reference_group，保持 drift_forbidden=face_shape/hairstyle/outfit_palette/age/costume；角色=CHAR_HE_PINGSHENG;
近景身份锁定约束：CU/MCU/反打/说话镜优先脸部特写、表情参考、front/side/back reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；配角近景不稳则用 MCU/OTS/侧脸/手部/物件反应镜;
物理交互约束：按 Motion Control degrade_only 执行，只做水桶落地、俯身、手部拨水、微光反射和侧脸反应；不生成车辆、车道、车轮或高速运动；检查 FeatureMelting，手部、水桶、水面和脸侧反光不得融化;
原生音画约束：无对白、无旁白、不要生成原生人声；如产生原生音轨，compose 默认丢弃。
人物运动：挑桶、山路、喘息、扁担压肩，重复到第五趟。，第五次到潭边，水下出现一点微光。;
镜头运动：轻微推镜头，沿主体动作/视线方向轻推，落到MS→montage→CU; 后端控制写法：自然语言运镜：轻微推镜头，沿主体动作/视线方向轻推，落到MS→montage→CU；首帧锚定，不改变角色、光位、轴线和场景设定。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=j_cut;
声音约束：无对白、无旁白、不要生成原生人声；如产生原生音轨，compose 默认丢弃。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 中段接力帧：挑水蒙太奇跨度大，需中锚锁扁担、水桶、肩颈红痕。; action: 挑桶、山路、喘息、扁担压肩，重复到第五趟。，第五次到潭边，水下出现一点微光。; end: 夜潭水面反出一点微光，贺平生停住脚步。; constraints: 首帧=出图/第1集/图片/Clip05_夜挑五趟_mid.png; 尾帧=出图/第1集/图片/Clip05_夜挑五趟_end.png; asset_ids=LOC_HOUSHAN_QIANTAN, LOC_ZAYI_YUAN, PROP_SHUI_TONG, 后山山路, 扁担; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 默认给镜头一点目的性：轻微推近能增加叙事关注，同时风险低。; camera motion: 轻微推镜头，沿主体动作/视线方向轻推，落到MS→montage→CU; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。.
identity constraint: use identity_registry, reference_group, face anchors, and expression references; preserve facial proportions, hairstyle, accessories, outfit palette, age, and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group.
audio constraint: no dialogue, no narration, no generated native voice.
```

### 检查清单（视频三件套自查）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、身份锁定、原生音画策略与 route 一致

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：手部、水桶、水面、脸侧反光不穿模不融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸
## Clip 11（时长 15s · EP01_CLIP11 · 水底破盆）

**首帧**：`出图/第1集/图片/Clip06_水底破盆.png`
**中段锚帧**：`出图/第1集/图片/Clip06_水底破盆_mid.png`
**尾帧**：`出图/第1集/图片/Clip06_水底破盆_end.png`
**场景**：后山山泉浅潭/夜/外
**导演意图**：默认给镜头一点目的性：轻微推近能增加叙事关注，同时风险低。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在CU→ECU→MS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：主体位置、前后景、视线和轴线继承 storyboard。；
**表演节拍**：[0-2s] 贺平生屏息停住。（CU）；[2-7s] 黑陶破盆躺在砂石间，反出一线月光。（水下ECU）；[7-15s] 贺平生捞起破盆，误判为普通旧物。（MS到道具CU）；微表情/表情幅度：贺平生：起屏息警觉，见是破盆后眉心松开，露出疲惫实用判断。
**三轨音频**：旁白音频后期 compose 叠加；视频生成阶段不要生成旁白音频，只允许画内角色对白口型。
**运动精修**：张力=聚焦；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。；身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：冷蓝月光、水面细波、桶中水晃和黑陶盆湿痕只随可见动作触发。
**涉及资产**：LOC_HOUSHAN_QIANTAN, PROP_HEI_TAO_PEN, PROP_SHUI_TONG

**专项镜头模板**：无。

**模型路由**：shot_type=general_motion; clip_characters=CHAR_HE_PINGSHENG; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; policy_resolution.winner=cost_quality_tier; risk_flags=native_multiframe, seam_relay; degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.

**动作编排契约 / Action Choreography**：无。

**Motion Control / 物理交互控制**：无。

**角色身份注册层**：
- CHAR_HE_PINGSHENG（贺平生）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_贺平生.png; 出图/共享/图片/定妆_贺平生_侧.png; 出图/共享/图片/定妆_贺平生_背.png; 出图/共享/图片/定妆_贺平生_半身.png; 出图/共享/图片/定妆_贺平生_三视图.png; 出图/共享/图片/定妆_贺平生_脸部特写.png; 出图/共享/图片/定妆_贺平生_表情_克制.png; 出图/共享/图片/定妆_贺平生_表情_疲惫隐忍.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。

**近景/反打身份锁定**：主焦点角色=CHAR_HE_PINGSHENG（贺平生）；使用 identity_registry / identity_adapter_matrix / reference_group / face_anchor / expressions。锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；表情只动面部肌肉，不改脸型；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜，保留 story beat。

**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=no_dialogue；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱

**衔接设计**：
- 入点：夜潭水面反出一点微光，贺平生停住脚步。
- 出点：贺平生把黑陶破盆从水中拿起，认定只是能用的旧盆。
- 转场：hard_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：夜潭水面反出一点微光，贺平生停住脚步。
- action：贺平生屏息停住。，黑陶破盆躺在砂石间，反出一线月光。，贺平生捞起破盆，误判为普通旧物。
- end_state：贺平生把黑陶破盆从水中拿起，认定只是能用的旧盆。
- constraints：首帧=出图/第1集/图片/Clip06_水底破盆.png; 中段锚帧=出图/第1集/图片/Clip06_水底破盆_mid.png; 尾帧=出图/第1集/图片/Clip06_水底破盆_end.png; asset_ids=LOC_HOUSHAN_QIANTAN, PROP_HEI_TAO_PEN, PROP_SHUI_TONG; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 夜潭水面反出一点微光，贺平生停住脚步。
  action: 贺平生屏息停住。，黑陶破盆躺在砂石间，反出一线月光。，贺平生捞起破盆，误判为普通旧物。
  end_state: 贺平生把黑陶破盆从水中拿起，认定只是能用的旧盆。
  constraints: 首帧=出图/第1集/图片/Clip06_水底破盆.png; 中段锚帧=出图/第1集/图片/Clip06_水底破盆_mid.png; 尾帧=出图/第1集/图片/Clip06_水底破盆_end.png; asset_ids=LOC_HOUSHAN_QIANTAN, PROP_HEI_TAO_PEN, PROP_SHUI_TONG; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：默认给镜头一点目的性：轻微推近能增加叙事关注，同时风险低。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在CU→ECU→MS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：继承 storyboard 槽位;
表演节拍：[0-2s] 贺平生屏息停住。（CU）；[2-7s] 黑陶破盆躺在砂石间，反出一线月光。（水下ECU）；[7-15s] 贺平生捞起破盆，误判为普通旧物。（MS到道具CU）;
三轨音频：旁白音频后期 compose 叠加；本视频生成不要生成旁白音频，只允许画内角色对白口型;
运动精修约束：张力=聚焦；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。; 身体守卫=脸部轮廓和发髻不拉伸，肩颈/手部不穿模，道具不粘连;
环境交互约束：冷蓝月光、水面细波、桶中水晃和黑陶盆湿痕只随可见动作触发。;
专项模板约束：无。
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=seedance，mode=image2video，native_audio_policy=none，identity_requirement=reference_group；只使用 Seedance via Dreamina 已刷新证据支持的能力；失败按 degrade_plan 或 Motion Control degrade_only 停审，不临场改后端;
身份锁定约束：读取 identity_registry.json 和 identity_adapter_matrix.json；使用首/尾帧与 reference_group，保持 drift_forbidden=face_shape/hairstyle/outfit_palette/age/costume；角色=CHAR_HE_PINGSHENG;
近景身份锁定约束：CU/MCU/反打/说话镜优先脸部特写、表情参考、front/side/back reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；配角近景不稳则用 MCU/OTS/侧脸/手部/物件反应镜;
原生音画约束：无对白、无旁白、不要生成原生人声；如产生原生音轨，compose 默认丢弃。
人物运动：贺平生屏息停住。，黑陶破盆躺在砂石间，反出一线月光。，贺平生捞起破盆，误判为普通旧物。;
镜头运动：轻微推镜头，沿主体动作/视线方向轻推，落到CU→ECU→MS; 后端控制写法：自然语言运镜：轻微推镜头，沿主体动作/视线方向轻推，落到CU→ECU→MS；首帧锚定，不改变角色、光位、轴线和场景设定。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=hard_cut;
声音约束：无对白、无旁白、不要生成原生人声；如产生原生音轨，compose 默认丢弃。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 夜潭水面反出一点微光，贺平生停住脚步。; action: 贺平生屏息停住。，黑陶破盆躺在砂石间，反出一线月光。，贺平生捞起破盆，误判为普通旧物。; end: 贺平生把黑陶破盆从水中拿起，认定只是能用的旧盆。; constraints: 首帧=出图/第1集/图片/Clip06_水底破盆.png; 中段锚帧=出图/第1集/图片/Clip06_水底破盆_mid.png; 尾帧=出图/第1集/图片/Clip06_水底破盆_end.png; asset_ids=LOC_HOUSHAN_QIANTAN, PROP_HEI_TAO_PEN, PROP_SHUI_TONG; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 默认给镜头一点目的性：轻微推近能增加叙事关注，同时风险低。; camera motion: 轻微推镜头，沿主体动作/视线方向轻推，落到CU→ECU→MS; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。.
identity constraint: use identity_registry, reference_group, face anchors, and expression references; preserve facial proportions, hairstyle, accessories, outfit palette, age, and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group.
audio constraint: no dialogue, no narration, no generated native voice.
```

### 检查清单（视频三件套自查）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、身份锁定、原生音画策略与 route 一致

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然
- [ ] 镜头运动符合 prompt
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 12（时长 4s · EP01_CLIP12 · 盆底微光）

**首帧**：`出图/第1集/图片/Clip07_盆底微光.png`
**中段锚帧**：`出图/第1集/图片/Clip07_盆底微光_mid.png`
**尾帧**：无（最终/豁免 Clip）
**场景**：后山山泉浅潭/夜/外
**导演意图**：铺垫和压迫段用慢推聚焦信息，让观众逐步靠近秘密。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在MS/MCU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：主体位置、前后景、视线和轴线继承 storyboard。；
**表演节拍**：[0-4s] 破盆离水，盆底极弱微光一闪，硬断。（ECU定格）；微表情/表情幅度：人物不看镜头，靠手部动作和道具微光表达异常感。
**三轨音频**：旁白音频后期 compose 叠加；视频生成阶段不要生成旁白音频，只允许画内角色对白口型。
**三轨修补**：屏幕文案（后期overlay）：他没有看见，盆底又亮了一下；不得让视频模型生成文字，compose 阶段叠清晰字。
**运动精修**：张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。；身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：冷蓝月光、水面细波、桶中水晃和黑陶盆湿痕只随可见动作触发。
**涉及资产**：LOC_HOUSHAN_QIANTAN, PROP_HEI_TAO_PEN

**专项镜头模板**：无。

**模型路由**：shot_type=general_motion; clip_characters=CHAR_HE_PINGSHENG; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; policy_resolution.winner=cost_quality_tier; risk_flags=native_multiframe; degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.

**动作编排契约 / Action Choreography**：无。

**Motion Control / 物理交互控制**：无。

**角色身份注册层**：
- CHAR_HE_PINGSHENG（贺平生）：video_binding=dreamina:reference_group；reference_group=出图/共享/图片/定妆_贺平生.png; 出图/共享/图片/定妆_贺平生_侧.png; 出图/共享/图片/定妆_贺平生_背.png; 出图/共享/图片/定妆_贺平生_半身.png; 出图/共享/图片/定妆_贺平生_三视图.png; 出图/共享/图片/定妆_贺平生_脸部特写.png; 出图/共享/图片/定妆_贺平生_表情_克制.png; 出图/共享/图片/定妆_贺平生_表情_疲惫隐忍.png；禁漂=脸型/五官比例/发型发髻/服装配色/年龄段。

**近景/反打身份锁定**：主焦点角色=CHAR_HE_PINGSHENG（贺平生）；使用 identity_registry / identity_adapter_matrix / reference_group / face_anchor / expressions。锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；表情只动面部肌肉，不改脸型；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜，保留 story beat。

**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=no_dialogue；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱

**衔接设计**：
- 入点：贺平生把黑陶破盆从水中拿起，认定只是能用的旧盆。
- 出点：黑陶破盆离水一瞬，盆底微光再亮，画面硬断。
- 转场：hard_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：贺平生把黑陶破盆从水中拿起，认定只是能用的旧盆。
- action：破盆离水，盆底极弱微光一闪，硬断。
- end_state：黑陶破盆离水一瞬，盆底微光再亮，画面硬断。
- constraints：首帧=出图/第1集/图片/Clip07_盆底微光.png; 中段锚帧=出图/第1集/图片/Clip07_盆底微光_mid.png; asset_ids=LOC_HOUSHAN_QIANTAN, PROP_HEI_TAO_PEN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 贺平生把黑陶破盆从水中拿起，认定只是能用的旧盆。
  action: 破盆离水，盆底极弱微光一闪，硬断。
  end_state: 黑陶破盆离水一瞬，盆底微光再亮，画面硬断。
  constraints: 首帧=出图/第1集/图片/Clip07_盆底微光.png; 中段锚帧=出图/第1集/图片/Clip07_盆底微光_mid.png; asset_ids=LOC_HOUSHAN_QIANTAN, PROP_HEI_TAO_PEN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：铺垫和压迫段用慢推聚焦信息，让观众逐步靠近秘密。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在MS/MCU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：继承 storyboard 槽位;
表演节拍：[0-4s] 破盆离水，盆底极弱微光一闪，硬断。（ECU定格）;
三轨音频：旁白音频后期 compose 叠加；本视频生成不要生成旁白音频，只允许画内角色对白口型;
三轨修补：屏幕文案仅后期overlay显示「他没有看见，盆底又亮了一下」，本视频生成不要画字、不要生成字幕卡、不要生成logo;
运动精修约束：张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。; 身体守卫=脸部轮廓和发髻不拉伸，肩颈/手部不穿模，道具不粘连;
环境交互约束：冷蓝月光、水面细波、桶中水晃和黑陶盆湿痕只随可见动作触发。;
专项模板约束：无。
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=seedance，mode=image2video，native_audio_policy=none，identity_requirement=reference_group；只使用 Seedance via Dreamina 已刷新证据支持的能力；失败按 degrade_plan 或 Motion Control degrade_only 停审，不临场改后端;
身份锁定约束：读取 identity_registry.json 和 identity_adapter_matrix.json；使用首/尾帧与 reference_group，保持 drift_forbidden=face_shape/hairstyle/outfit_palette/age/costume；角色=CHAR_HE_PINGSHENG;
近景身份锁定约束：CU/MCU/反打/说话镜优先脸部特写、表情参考、front/side/back reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；配角近景不稳则用 MCU/OTS/侧脸/手部/物件反应镜;
原生音画约束：无对白、无旁白、不要生成原生人声；如产生原生音轨，compose 默认丢弃。
人物运动：破盆离水，盆底极弱微光一闪，硬断。;
镜头运动：缓慢推镜头，从场面关系慢推到人物/物证，落到MS/MCU; 后端控制写法：自然语言运镜：缓慢推镜头，从场面关系慢推到人物/物证，落到MS/MCU；首帧锚定，不改变角色、光位、轴线和场景设定。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=hard_cut;
声音约束：无对白、无旁白、不要生成原生人声；如产生原生音轨，compose 默认丢弃。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 贺平生把黑陶破盆从水中拿起，认定只是能用的旧盆。; action: 破盆离水，盆底极弱微光一闪，硬断。; end: 黑陶破盆离水一瞬，盆底微光再亮，画面硬断。; constraints: 首帧=出图/第1集/图片/Clip07_盆底微光.png; 中段锚帧=出图/第1集/图片/Clip07_盆底微光_mid.png; asset_ids=LOC_HOUSHAN_QIANTAN, PROP_HEI_TAO_PEN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 铺垫和压迫段用慢推聚焦信息，让观众逐步靠近秘密。; camera motion: 缓慢推镜头，从场面关系慢推到人物/物证，落到MS/MCU; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。.
identity constraint: use identity_registry, reference_group, face anchors, and expression references; preserve facial proportions, hairstyle, accessories, outfit palette, age, and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group.
audio constraint: no dialogue, no narration, no generated native voice.
```

### 检查清单（视频三件套自查）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、身份锁定、原生音画策略与 route 一致

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然
- [ ] 镜头运动符合 prompt
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸
