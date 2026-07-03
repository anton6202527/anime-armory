# 第1集 视频分镜 Prompt

说明：本文件由 25 Clip storyboard、video_model_routes、director_camera_plan、identity_adapter_matrix 同步生成。

## Clip 01（时长 3.5s · EP01_CLIP01 · Clip_01 · 黑殿全景慢推）

**首帧**：`出图/第1集/图片/Clip01_first.png`
**尾帧**：`出图/第1集/图片/Clip01_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：秀竹峰杂役大殿/夜/内
**导演意图**：冷开场·首屏压迫；本镜只完成一个动作/信息点：黑暗的大殿里，十四岁的贺平生第一次听见别人叫他“费钱货”。
**起幅**：黑暗杂役大殿，全景慢推。贺平生站在画左下方，张老大画右前景形成压迫，周围杂役只露半身和笑影。
**落幅**：张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；贺平生画左下，张老大画右前景，群杂役只作两侧笑影。
**表演节拍**：[0-3.5s] 黑暗杂役大殿，全景慢推。贺平生站在画左下方，张老大画右前景形成压迫，周围杂役只露半身和笑影。（全景·慢推）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=冷开场·首屏压迫; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=ensemble_blocking; {"beats": ["黑殿建立", "主角低位出现", "张老大压迫入画"], "blocking": "贺平生画左下，张老大画右前景，群杂役只作两侧笑影。", "camera_rule": "从大殿全景慢推到人物压迫关系，守张老大→贺平生横轴。", "continuity_must": ["大殿低冷光", "贺平生十四岁瘦削", "张老大画右压迫"], "crowd_simplification": "群杂役/围观人群只保留轮廓、肩背、笑影和站位压迫；清晰正脸不超过一人，必要时切反应插入。", "focus_hierarchy": ["primary=CHAR_HE_PINGSHENG", "其他角色只作侧脸/背影/肩背/虚化，避免同框抢脸。", "群像/围观者只作后景情绪，不解析为新角色。"], "negative": ["不要把大殿画成仙宫", "不要让群杂役变成具名正脸", "不要提前出现破盆"], "screen_positions": {"BACKGROUND_SLOT": "CROWD_ZAYI/虚化或长老背影，不解析脸。", "LEFT_SLOT": "CHAR_HE_PINGSHENG/常态，画左下或画左近景，primary face。", "RIGHT_SLOT": "CHAR_ZHANG_LAODA/常态，画右前景，secondary face。"}, "template_id": "ensemble_blocking"}
**模型路由**：shot_type=ensemble_blocking; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,seam_relay,spectacle_prior_routed; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第1集/control/Clip_01/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 2, "reference_only": false, "requires_split_relay": false}, "mode": "frames2video", "quality_tier": "n/a", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_ZHANG_LAODA", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "", "form": ""}], "identity_preservation_plan": {"applies_to": "ensemble_blocking", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "character_id_or_reference_group", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 3, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_01/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；degrade_plan=本 Clip 只有旁白/画面信息，无画内角色对白；视频阶段禁止模型生成旁白音频，旁白交 n2d-compose，画面按静音 image2video/frames2video 执行。。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态,CHAR_ZHANG_LAODA/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_ZHANG_LAODA: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CROWD_ZAYI: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA,CROWD_ZAYI；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：黑暗杂役大殿，全景慢推。贺平生站在画左下方，张老大画右前景形成压迫，周围杂役只露半身和笑影。
- 出点：张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。
- 转场：j_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：黑暗杂役大殿，全景慢推。贺平生站在画左下方，张老大画右前景形成压迫，周围杂役只露半身和笑影。
- action：黑暗杂役大殿，全景慢推。贺平生站在画左下方，张老大画右前景形成压迫，周围杂役只露半身和笑影。
- end_state：张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。
- constraints：首帧=出图/第1集/图片/Clip01_first.png; 尾帧=出图/第1集/图片/Clip01_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA,CROWD_ZAYI; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 黑暗杂役大殿，全景慢推。贺平生站在画左下方，张老大画右前景形成压迫，周围杂役只露半身和笑影。
  action: 黑暗杂役大殿，全景慢推。贺平生站在画左下方，张老大画右前景形成压迫，周围杂役只露半身和笑影。
  end_state: 张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。
  constraints: 首帧=出图/第1集/图片/Clip01_first.png; 尾帧=出图/第1集/图片/Clip01_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA,CROWD_ZAYI; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：冷开场·首屏压迫；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：黑暗杂役大殿，全景慢推。贺平生站在画左下方，张老大画右前景形成压迫，周围杂役只露半身和笑影。;
落幅：张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。;
场面调度：贺平生画左下，张老大画右前景，群杂役只作两侧笑影。;
表演节拍：[0-3.5s] 黑暗杂役大殿，全景慢推。贺平生站在画左下方，张老大画右前景形成压迫，周围杂役只露半身和笑影。（全景·慢推）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=ensemble_blocking；beats=黑殿建立, 主角低位出现, 张老大压迫入画；negative=不要把大殿画成仙宫, 不要让群杂役变成具名正脸, 不要提前出现破盆;
模型路由约束：shot_type=ensemble_blocking; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,seam_relay,spectacle_prior_routed; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_ZHANG_LAODA: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CROWD_ZAYI: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：黑暗杂役大殿，全景慢推。贺平生站在画左下方，张老大画右前景形成压迫，周围杂役只露半身和笑影。;
镜头运动：全景·慢推，速度克制，服务 冷开场·首屏压迫;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=j_cut;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 黑暗杂役大殿，全景慢推。贺平生站在画左下方，张老大画右前景形成压迫，周围杂役只露半身和笑影。; action: 黑暗杂役大殿，全景慢推。贺平生站在画左下方，张老大画右前景形成压迫，周围杂役只露半身和笑影。; end: 张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。; constraints: 首帧=出图/第1集/图片/Clip01_first.png; 尾帧=出图/第1集/图片/Clip01_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA,CROWD_ZAYI; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 冷开场·首屏压迫; camera motion: 全景·慢推, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 02（时长 3.5s · EP01_CLIP02 · Clip_02 · 张老大问年龄）

**首帧**：`出图/第1集/图片/Clip02_first.png`
**尾帧**：`出图/第1集/图片/Clip02_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：秀竹峰杂役大殿/夜/内
**导演意图**：审问·反打起势；本镜只完成一个动作/信息点：你叫贺平生？多大了？
**起幅**：张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。
**落幅**：贺平生近景，瘦小身形被大殿阴影压住，低头拱手。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；张老大画右前景，贺平生只作画左低位反应或肩背。
**表演节拍**：[0-3.5s] 张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。（中近景·低角度）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=审问·反打起势; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=dialogue_shot_reverse; {"axis": "张老大画右前景、贺平生画左下/画左近景，张老大→贺平生横轴锁定；正反打不得交换左右。", "beats": ["张老大抬眼", "问姓名年龄"], "blocking": "张老大画右前景，贺平生只作画左低位反应或肩背。", "camera_rule": "反打不换轴，张老大视线始终向画左下。", "continuity_must": ["张老大粗壮油污手", "大殿画左冷光", "贺平生低位承压"], "eyeline": "按本集视觉契约继承；贺平生在大殿看画右上，在水缸区看后景水缸，在浅潭看画右下潭底。", "negative": ["不要让张老大站到画左", "不要加入仙门长老", "不要夸张成喜剧审问"], "shot_pairing": "与相邻反打/反应镜保持同一 180 度轴线；说话者与听者以单主体近景或 OTS/肩背配对，不在同镜抢两张正脸。", "template_id": "dialogue_shot_reverse"}
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "native_speech", "native_speech": true, "requires_voice_track": false, "speech_policy": "native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 20, "reference_only": false, "requires_split_relay": false}, "mode": "native_av", "quality_tier": "high", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_ZHANG_LAODA", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_ZHANG_LAODA/常态,CHAR_HE_PINGSHENG/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_ZHANG_LAODA: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_ZHANG_LAODA,CHAR_HE_PINGSHENG；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留
**衔接设计**：
- 入点：张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。
- 出点：贺平生近景，瘦小身形被大殿阴影压住，低头拱手。
- 转场：shot_reverse_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。
- action：张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。
- end_state：贺平生近景，瘦小身形被大殿阴影压住，低头拱手。
- constraints：首帧=出图/第1集/图片/Clip02_first.png; 尾帧=出图/第1集/图片/Clip02_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_ZHANG_LAODA,CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。
  action: 张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。
  end_state: 贺平生近景，瘦小身形被大殿阴影压住，低头拱手。
  constraints: 首帧=出图/第1集/图片/Clip02_first.png; 尾帧=出图/第1集/图片/Clip02_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_ZHANG_LAODA,CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：审问·反打起势；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。;
落幅：贺平生近景，瘦小身形被大殿阴影压住，低头拱手。;
场面调度：张老大画右前景，贺平生只作画左低位反应或肩背。;
表演节拍：[0-3.5s] 张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。（中近景·低角度）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=dialogue_shot_reverse；beats=张老大抬眼, 问姓名年龄；negative=不要让张老大站到画左, 不要加入仙门长老, 不要夸张成喜剧审问;
模型路由约束：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_ZHANG_LAODA: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：台词+口型由原生音画后端生成；mouth_visible=yes；speech_policy=native_speech；生成后保留原片音轨并检查声源/口型同步。
人物运动：张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。;
镜头运动：中近景·低角度，速度克制，服务 审问·反打起势;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=shot_reverse_cut;
声音约束：台词和口型由原生音画后端生成；保留原片音轨；禁止新增旁白或改写对白事实。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。; action: 张老大中近景，赤裸上身，油污大手搭在膝上，抬眼审问。; end: 贺平生近景，瘦小身形被大殿阴影压住，低头拱手。; constraints: 首帧=出图/第1集/图片/Clip02_first.png; 尾帧=出图/第1集/图片/Clip02_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_ZHANG_LAODA,CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 审问·反打起势; camera motion: 中近景·低角度, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group.
native audio policy: native speech enabled; generate dialogue and lip sync natively, keep original generated audio, no narration voice.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 03（时长 3.5s · EP01_CLIP03 · Clip_03 · 贺平生答十四岁）

**首帧**：`出图/第1集/图片/Clip03_first.png`
**尾帧**：`出图/第1集/图片/Clip03_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：秀竹峰杂役大殿/夜/内
**导演意图**：审问·低头承压；本镜只完成一个动作/信息点：回张老大的话，我今年十四岁。
**起幅**：贺平生近景，瘦小身形被大殿阴影压住，低头拱手。
**落幅**：张老大半身反打，眼神漫不经心。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；贺平生画左下近景，张老大只保留画右上压迫视线。
**表演节拍**：[0-3.5s] 贺平生近景，瘦小身形被大殿阴影压住，低头拱手。（近景·轻微下压）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=审问·低头承压; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=dialogue_shot_reverse; {"axis": "张老大画右前景、贺平生画左下/画左近景，张老大→贺平生横轴锁定；正反打不得交换左右。", "beats": ["贺平生低头", "谨慎回答十四岁"], "blocking": "贺平生画左下近景，张老大只保留画右上压迫视线。", "camera_rule": "接上张老大反打，贺平生视线向画右上后迅速垂下。", "continuity_must": ["少年瘦削脸", "粗布杂役服", "十四岁事实锁定"], "eyeline": "按本集视觉契约继承；贺平生在大殿看画右上，在水缸区看后景水缸，在浅潭看画右下潭底。", "negative": ["不要画成年", "不要抬头挑衅", "不要换成白天"], "shot_pairing": "与相邻反打/反应镜保持同一 180 度轴线；说话者与听者以单主体近景或 OTS/肩背配对，不在同镜抢两张正脸。", "template_id": "dialogue_shot_reverse"}
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "native_speech", "native_speech": true, "requires_voice_track": false, "speech_policy": "native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 20, "reference_only": false, "requires_split_relay": false}, "mode": "native_av", "quality_tier": "high", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_ZHANG_LAODA", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态,CHAR_ZHANG_LAODA/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_ZHANG_LAODA: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留
**衔接设计**：
- 入点：贺平生近景，瘦小身形被大殿阴影压住，低头拱手。
- 出点：张老大半身反打，眼神漫不经心。
- 转场：shot_reverse_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：贺平生近景，瘦小身形被大殿阴影压住，低头拱手。
- action：贺平生近景，瘦小身形被大殿阴影压住，低头拱手。
- end_state：张老大半身反打，眼神漫不经心。
- constraints：首帧=出图/第1集/图片/Clip03_first.png; 尾帧=出图/第1集/图片/Clip03_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 贺平生近景，瘦小身形被大殿阴影压住，低头拱手。
  action: 贺平生近景，瘦小身形被大殿阴影压住，低头拱手。
  end_state: 张老大半身反打，眼神漫不经心。
  constraints: 首帧=出图/第1集/图片/Clip03_first.png; 尾帧=出图/第1集/图片/Clip03_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：审问·低头承压；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：贺平生近景，瘦小身形被大殿阴影压住，低头拱手。;
落幅：张老大半身反打，眼神漫不经心。;
场面调度：贺平生画左下近景，张老大只保留画右上压迫视线。;
表演节拍：[0-3.5s] 贺平生近景，瘦小身形被大殿阴影压住，低头拱手。（近景·轻微下压）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=dialogue_shot_reverse；beats=贺平生低头, 谨慎回答十四岁；negative=不要画成年, 不要抬头挑衅, 不要换成白天;
模型路由约束：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_ZHANG_LAODA: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：台词+口型由原生音画后端生成；mouth_visible=yes；speech_policy=native_speech；生成后保留原片音轨并检查声源/口型同步。
人物运动：贺平生近景，瘦小身形被大殿阴影压住，低头拱手。;
镜头运动：近景·轻微下压，速度克制，服务 审问·低头承压;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=shot_reverse_cut;
声音约束：台词和口型由原生音画后端生成；保留原片音轨；禁止新增旁白或改写对白事实。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 贺平生近景，瘦小身形被大殿阴影压住，低头拱手。; action: 贺平生近景，瘦小身形被大殿阴影压住，低头拱手。; end: 张老大半身反打，眼神漫不经心。; constraints: 首帧=出图/第1集/图片/Clip03_first.png; 尾帧=出图/第1集/图片/Clip03_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 审问·低头承压; camera motion: 近景·轻微下压, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group.
native audio policy: native speech enabled; generate dialogue and lip sync natively, keep original generated audio, no narration voice.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 04（时长 3.0s · EP01_CLIP04 · Clip_04 · 张老大问灵根）

**首帧**：`出图/第1集/图片/Clip04_first.png`
**尾帧**：`出图/第1集/图片/Clip04_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：秀竹峰杂役大殿/夜/内
**导演意图**：审问·压缩追问；本镜只完成一个动作/信息点：什么灵根？
**起幅**：张老大半身反打，眼神漫不经心。
**落幅**：贺平生嘴唇轻抿，抬眼又迅速垂下。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；张老大仍画右前，贺平生低位在画左边缘。
**表演节拍**：[0-3s] 张老大半身反打，眼神漫不经心。（半身反打）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=审问·压缩追问; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=dialogue_shot_reverse; {"axis": "张老大画右前景、贺平生画左下/画左近景，张老大→贺平生横轴锁定；正反打不得交换左右。", "beats": ["张老大追问灵根", "漫不经心压迫"], "blocking": "张老大仍画右前，贺平生低位在画左边缘。", "camera_rule": "短反打，保持横轴和低冷光。", "continuity_must": ["张老大画右", "贺平生低头", "大殿光位继承"], "eyeline": "按本集视觉契约继承；贺平生在大殿看画右上，在水缸区看后景水缸，在浅潭看画右下潭底。", "negative": ["不要跳轴", "不要加灵根光效", "不要让张老大变友善"], "shot_pairing": "与相邻反打/反应镜保持同一 180 度轴线；说话者与听者以单主体近景或 OTS/肩背配对，不在同镜抢两张正脸。", "template_id": "dialogue_shot_reverse"}
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "native_speech", "native_speech": true, "requires_voice_track": false, "speech_policy": "native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 20, "reference_only": false, "requires_split_relay": false}, "mode": "native_av", "quality_tier": "high", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_ZHANG_LAODA", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_ZHANG_LAODA/常态,CHAR_HE_PINGSHENG/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_ZHANG_LAODA: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_ZHANG_LAODA,CHAR_HE_PINGSHENG；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留
**衔接设计**：
- 入点：张老大半身反打，眼神漫不经心。
- 出点：贺平生嘴唇轻抿，抬眼又迅速垂下。
- 转场：hard_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：张老大半身反打，眼神漫不经心。
- action：张老大半身反打，眼神漫不经心。
- end_state：贺平生嘴唇轻抿，抬眼又迅速垂下。
- constraints：首帧=出图/第1集/图片/Clip04_first.png; 尾帧=出图/第1集/图片/Clip04_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_ZHANG_LAODA,CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 张老大半身反打，眼神漫不经心。
  action: 张老大半身反打，眼神漫不经心。
  end_state: 贺平生嘴唇轻抿，抬眼又迅速垂下。
  constraints: 首帧=出图/第1集/图片/Clip04_first.png; 尾帧=出图/第1集/图片/Clip04_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_ZHANG_LAODA,CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：审问·压缩追问；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：张老大半身反打，眼神漫不经心。;
落幅：贺平生嘴唇轻抿，抬眼又迅速垂下。;
场面调度：张老大仍画右前，贺平生低位在画左边缘。;
表演节拍：[0-3s] 张老大半身反打，眼神漫不经心。（半身反打）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=dialogue_shot_reverse；beats=张老大追问灵根, 漫不经心压迫；negative=不要跳轴, 不要加灵根光效, 不要让张老大变友善;
模型路由约束：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_ZHANG_LAODA: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：台词+口型由原生音画后端生成；mouth_visible=yes；speech_policy=native_speech；生成后保留原片音轨并检查声源/口型同步。
人物运动：张老大半身反打，眼神漫不经心。;
镜头运动：半身反打，速度克制，服务 审问·压缩追问;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=hard_cut;
声音约束：台词和口型由原生音画后端生成；保留原片音轨；禁止新增旁白或改写对白事实。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 张老大半身反打，眼神漫不经心。; action: 张老大半身反打，眼神漫不经心。; end: 贺平生嘴唇轻抿，抬眼又迅速垂下。; constraints: 首帧=出图/第1集/图片/Clip04_first.png; 尾帧=出图/第1集/图片/Clip04_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_ZHANG_LAODA,CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 审问·压缩追问; camera motion: 半身反打, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group.
native audio policy: native speech enabled; generate dialogue and lip sync natively, keep original generated audio, no narration voice.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 05（时长 3.0s · EP01_CLIP05 · Clip_05 · 贺平生答五行灵根）

**首帧**：`出图/第1集/图片/Clip05_first.png`
**尾帧**：`出图/第1集/图片/Clip05_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：秀竹峰杂役大殿/夜/内
**导演意图**：审问·羞辱触发；本镜只完成一个动作/信息点：五行灵根。
**起幅**：贺平生嘴唇轻抿，抬眼又迅速垂下。
**落幅**：群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；贺平生画左近景，张老大压力来自画右上视线。
**表演节拍**：[0-3s] 贺平生嘴唇轻抿，抬眼又迅速垂下。（近景·轻抬眼）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=审问·羞辱触发; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=dialogue_shot_reverse; {"axis": "张老大画右前景、贺平生画左下/画左近景，张老大→贺平生横轴锁定；正反打不得交换左右。", "beats": ["贺平生抿唇", "说出五行灵根"], "blocking": "贺平生画左近景，张老大压力来自画右上视线。", "camera_rule": "用微表情完成回答，不新增玄幻强光。", "continuity_must": ["五行灵根事实锁定", "少年不敢抬头", "大殿阴影压脸"], "eyeline": "按本集视觉契约继承；贺平生在大殿看画右上，在水缸区看后景水缸，在浅潭看画右下潭底。", "negative": ["不要画成觉醒爆发", "不要强光环绕全身", "不要改灵根类型"], "shot_pairing": "与相邻反打/反应镜保持同一 180 度轴线；说话者与听者以单主体近景或 OTS/肩背配对，不在同镜抢两张正脸。", "template_id": "dialogue_shot_reverse"}
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "native_speech", "native_speech": true, "requires_voice_track": false, "speech_policy": "native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 20, "reference_only": false, "requires_split_relay": false}, "mode": "native_av", "quality_tier": "high", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_ZHANG_LAODA", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态,CHAR_ZHANG_LAODA/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_ZHANG_LAODA: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留
**衔接设计**：
- 入点：贺平生嘴唇轻抿，抬眼又迅速垂下。
- 出点：群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。
- 转场：reaction_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：贺平生嘴唇轻抿，抬眼又迅速垂下。
- action：贺平生嘴唇轻抿，抬眼又迅速垂下。
- end_state：群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。
- constraints：首帧=出图/第1集/图片/Clip05_first.png; 尾帧=出图/第1集/图片/Clip05_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 贺平生嘴唇轻抿，抬眼又迅速垂下。
  action: 贺平生嘴唇轻抿，抬眼又迅速垂下。
  end_state: 群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。
  constraints: 首帧=出图/第1集/图片/Clip05_first.png; 尾帧=出图/第1集/图片/Clip05_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：审问·羞辱触发；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：贺平生嘴唇轻抿，抬眼又迅速垂下。;
落幅：群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。;
场面调度：贺平生画左近景，张老大压力来自画右上视线。;
表演节拍：[0-3s] 贺平生嘴唇轻抿，抬眼又迅速垂下。（近景·轻抬眼）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=dialogue_shot_reverse；beats=贺平生抿唇, 说出五行灵根；negative=不要画成觉醒爆发, 不要强光环绕全身, 不要改灵根类型;
模型路由约束：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_ZHANG_LAODA: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：台词+口型由原生音画后端生成；mouth_visible=yes；speech_policy=native_speech；生成后保留原片音轨并检查声源/口型同步。
人物运动：贺平生嘴唇轻抿，抬眼又迅速垂下。;
镜头运动：近景·轻抬眼，速度克制，服务 审问·羞辱触发;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=reaction_cut;
声音约束：台词和口型由原生音画后端生成；保留原片音轨；禁止新增旁白或改写对白事实。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 贺平生嘴唇轻抿，抬眼又迅速垂下。; action: 贺平生嘴唇轻抿，抬眼又迅速垂下。; end: 群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。; constraints: 首帧=出图/第1集/图片/Clip05_first.png; 尾帧=出图/第1集/图片/Clip05_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 审问·羞辱触发; camera motion: 近景·轻抬眼, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group.
native audio policy: native speech enabled; generate dialogue and lip sync natively, keep original generated audio, no narration voice.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 06（时长 4.0s · EP01_CLIP06 · Clip_06 · 群杂役笑影压近）

**首帧**：`出图/第1集/图片/Clip06_first.png`
**尾帧**：`出图/第1集/图片/Clip06_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：秀竹峰杂役大殿/夜/内
**导演意图**：审问·群嘲碎切；本镜只完成一个动作/信息点：哈哈哈哈！
**起幅**：群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。
**落幅**：水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；群杂役只作虚化笑影，贺平生保留画面低位轮廓。
**表演节拍**：[0-4s] 群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。（碎切CU/后景虚化）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=审问·群嘲碎切; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=ensemble_blocking; {"beats": ["笑声爆开", "灰尘落下", "贺平生被围压"], "blocking": "群杂役只作虚化笑影，贺平生保留画面低位轮廓。", "camera_rule": "碎切但不跳轴，笑声作声桥接下个解释镜。", "continuity_must": ["群杂役不解析脸", "大殿灰尘", "贺平生孤立"], "crowd_simplification": "群杂役/围观人群只保留轮廓、肩背、笑影和站位压迫；清晰正脸不超过一人，必要时切反应插入。", "focus_hierarchy": ["primary=CHAR_HE_PINGSHENG", "其他角色只作侧脸/背影/肩背/虚化，避免同框抢脸。", "群像/围观者只作后景情绪，不解析为新角色。"], "negative": ["不要出现现代喜剧表情", "不要新增具名角色", "不要把笑影画成恶鬼"], "screen_positions": {"BACKGROUND_SLOT": "CROWD_ZAYI/虚化或长老背影，不解析脸。", "LEFT_SLOT": "CHAR_HE_PINGSHENG/常态，画左下或画左近景，primary face。", "RIGHT_SLOT": "CHAR_ZHANG_LAODA/常态，画右前景，secondary face。"}, "template_id": "ensemble_blocking"}
**模型路由**：shot_type=ensemble_blocking; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,multishot_candidate,seam_relay,mouth_visible,native_speech; degrade_plan=Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways.
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "native_speech", "native_speech": true, "requires_voice_track": false, "speech_policy": "native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第1集/control/Clip_06/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways.", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 2, "reference_only": false, "requires_split_relay": false}, "mode": "native_av", "quality_tier": "n/a", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "", "form": ""}], "identity_preservation_plan": {"applies_to": "ensemble_blocking", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "character_id_or_reference_group", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_06/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；degrade_plan=Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways.。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CROWD_ZAYI: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG,CROWD_ZAYI；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留
**衔接设计**：
- 入点：群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。
- 出点：水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。
- 转场：sound_bridge
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。
- action：群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。
- end_state：水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。
- constraints：首帧=出图/第1集/图片/Clip06_first.png; 尾帧=出图/第1集/图片/Clip06_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CROWD_ZAYI; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。
  action: 群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。
  end_state: 水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。
  constraints: 首帧=出图/第1集/图片/Clip06_first.png; 尾帧=出图/第1集/图片/Clip06_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CROWD_ZAYI; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：审问·群嘲碎切；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。;
落幅：水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。;
场面调度：群杂役只作虚化笑影，贺平生保留画面低位轮廓。;
表演节拍：[0-4s] 群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。（碎切CU/后景虚化）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=ensemble_blocking；beats=笑声爆开, 灰尘落下, 贺平生被围压；negative=不要出现现代喜剧表情, 不要新增具名角色, 不要把笑影画成恶鬼;
模型路由约束：shot_type=ensemble_blocking; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,multishot_candidate,seam_relay,mouth_visible,native_speech; degrade_plan=Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways.;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CROWD_ZAYI: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：台词+口型由原生音画后端生成；mouth_visible=yes；speech_policy=native_speech；生成后保留原片音轨并检查声源/口型同步。
人物运动：群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。;
镜头运动：碎切CU/后景虚化，速度克制，服务 审问·群嘲碎切;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=sound_bridge;
声音约束：台词和口型由原生音画后端生成；保留原片音轨；禁止新增旁白或改写对白事实。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。; action: 群杂役碎切笑影，灰尘从房梁簌簌落下，贺平生被笑声包围。; end: 水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。; constraints: 首帧=出图/第1集/图片/Clip06_first.png; 尾帧=出图/第1集/图片/Clip06_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CROWD_ZAYI; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 审问·群嘲碎切; camera motion: 碎切CU/后景虚化, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group.
native audio policy: native speech enabled; generate dialogue and lip sync natively, keep original generated audio, no narration voice.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 07（时长 5.0s · EP01_CLIP07 · Clip_07 · 五行光点被压灭）

**首帧**：`出图/第1集/图片/Clip07_first.png`
**尾帧**：`出图/第1集/图片/Clip07_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：秀竹峰杂役大殿/夜/概念快闪
**导演意图**：信息增量·灵根代价；本镜只完成一个动作/信息点：金木水火土俱全，听起来像天赋，可在太虚门，这种灵根要吞掉无数资源。
**起幅**：水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。
**落幅**：外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；概念光点围绕贺平生剪影，不变成觉醒仪式。
**表演节拍**：[0-5s] 水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。（概念快闪·水墨粒子）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=信息增量·灵根代价; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=reveal_reaction_chain; {"beats": ["五行光点出现", "光点被灰暗压灭", "代价信息落下"], "blocking": "概念光点围绕贺平生剪影，不变成觉醒仪式。", "camera_rule": "快闪后回到大殿冷调，光效小而短。", "continuity_must": ["五行俱全但弱", "不提前觉醒", "大殿灰褐压光"], "cut_point": "在「外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下」落幅后切出；不得延伸新增剧情。", "knowledge_order": ["观众先读到画面信息", "贺平生只按本镜状态反应", "不提前泄露第25镜之后的信息"], "negative": ["不要神器光柱", "不要把贺平生画成天才觉醒", "不要新增测灵石主视觉"], "reaction_beats": ["五行光点出现", "光点被灰暗压灭", "代价信息落下"], "reveal_object": "VFX_WUXING_GUANGDIAN", "template_id": "reveal_reaction_chain"}
**模型路由**：shot_type=talent_test; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; risk_flags=identity_drift_risk,multishot_candidate,object_continuity_risk,readability_hold_required,seam_relay,text_overlay_required; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "Use static product/test-result keyframe plus flame/light overlay; cut to hand/detail/reaction if the object morphs or the process stage jumps.", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 2, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "n/a", "reference_inputs": {"assets": [], "characters": [{"binding": "reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。
- 出点：外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。
- 转场：match_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。
- action：水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。
- end_state：外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。
- constraints：首帧=出图/第1集/图片/Clip07_first.png; 尾帧=出图/第1集/图片/Clip07_end.png; asset_ids=VFX_WUXING_GUANGDIAN,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。
  action: 水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。
  end_state: 外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。
  constraints: 首帧=出图/第1集/图片/Clip07_first.png; 尾帧=出图/第1集/图片/Clip07_end.png; asset_ids=VFX_WUXING_GUANGDIAN,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：信息增量·灵根代价；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。;
落幅：外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。;
场面调度：概念光点围绕贺平生剪影，不变成觉醒仪式。;
表演节拍：[0-5s] 水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。（概念快闪·水墨粒子）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=reveal_reaction_chain；beats=五行光点出现, 光点被灰暗压灭, 代价信息落下；negative=不要神器光柱, 不要把贺平生画成天才觉醒, 不要新增测灵石主视觉;
模型路由约束：shot_type=talent_test; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; risk_flags=identity_drift_risk,multishot_candidate,object_continuity_risk,readability_hold_required,seam_relay,text_overlay_required; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。;
镜头运动：概念快闪·水墨粒子，速度克制，服务 信息增量·灵根代价;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=match_cut;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。; action: 水墨式快闪五行光点短暂环绕，立刻被灰暗大殿压灭。; end: 外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。; constraints: 首帧=出图/第1集/图片/Clip07_first.png; 尾帧=出图/第1集/图片/Clip07_end.png; asset_ids=VFX_WUXING_GUANGDIAN,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 信息增量·灵根代价; camera motion: 概念快闪·水墨粒子, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 08（时长 5.0s · EP01_CLIP08 · Clip_08 · 外门长老转身离开）

**首帧**：`出图/第1集/图片/Clip08_first.png`
**尾帧**：`出图/第1集/图片/Clip08_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：太虚门外门觉醒台/日/回忆
**导演意图**：信息增量·无人愿收；本镜只完成一个动作/信息点：太虚门的那些长老，没有一个愿意收他；最后，贺平生连外门弟子的资格都没有。
**起幅**：外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。
**落幅**：回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；长老只给背影，贺平生小比例站在台下。
**表演节拍**：[0-5s] 外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。（回忆远景·背影）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=信息增量·无人愿收; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=reveal_reaction_chain; {"beats": ["长老背影离开", "少年台下孤立", "外门资格落空"], "blocking": "长老只给背影，贺平生小比例站在台下。", "camera_rule": "回忆镜头去饱和，切回大殿前不解析长老正脸。", "continuity_must": ["长老背影", "少年孤立", "无外门资格事实"], "cut_point": "在「回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。」落幅后切出；不得延伸新增剧情。", "knowledge_order": ["观众先读到画面信息", "贺平生只按本镜状态反应", "不提前泄露第25镜之后的信息"], "negative": ["不要给长老正脸", "不要让贺平生穿华服", "不要变成公开授奖"], "reaction_beats": ["长老背影离开", "少年台下孤立", "外门资格落空"], "reveal_object": "长老背影离开", "template_id": "reveal_reaction_chain"}
**模型路由**：shot_type=general_motion; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.；若本镜含对白/画内发声，必须走 voice-first 配音补偿链路，或拆出 native_speech 说话特写后重跑路由。", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 2, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "n/a", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_TAIXUMEN_ZHANGLAO", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态,CHAR_TAIXUMEN_ZHANGLAO/回忆背影; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_TAIXUMEN_ZHANGLAO: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG,CHAR_TAIXUMEN_ZHANGLAO；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。
- 出点：回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。
- 转场：memory_flash
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。
- action：外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。
- end_state：回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。
- constraints：首帧=出图/第1集/图片/Clip08_first.png; 尾帧=出图/第1集/图片/Clip08_end.png; asset_ids=,LOC_WAIMEN_JIUYUAN; character_ids=CHAR_HE_PINGSHENG,CHAR_TAIXUMEN_ZHANGLAO; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。
  action: 外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。
  end_state: 回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。
  constraints: 首帧=出图/第1集/图片/Clip08_first.png; 尾帧=出图/第1集/图片/Clip08_end.png; asset_ids=,LOC_WAIMEN_JIUYUAN; character_ids=CHAR_HE_PINGSHENG,CHAR_TAIXUMEN_ZHANGLAO; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：信息增量·无人愿收；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。;
落幅：回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。;
场面调度：长老只给背影，贺平生小比例站在台下。;
表演节拍：[0-5s] 外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。（回忆远景·背影）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=reveal_reaction_chain；beats=长老背影离开, 少年台下孤立, 外门资格落空；negative=不要给长老正脸, 不要让贺平生穿华服, 不要变成公开授奖;
模型路由约束：shot_type=general_motion; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_TAIXUMEN_ZHANGLAO: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。;
镜头运动：回忆远景·背影，速度克制，服务 信息增量·无人愿收;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=memory_flash;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。; action: 外门觉醒大会残影，几位长老背影转身离开，少年贺平生孤零零站在台下。; end: 回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。; constraints: 首帧=出图/第1集/图片/Clip08_first.png; 尾帧=出图/第1集/图片/Clip08_end.png; asset_ids=,LOC_WAIMEN_JIUYUAN; character_ids=CHAR_HE_PINGSHENG,CHAR_TAIXUMEN_ZHANGLAO; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 信息增量·无人愿收; camera motion: 回忆远景·背影, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 09（时长 5.5s · EP01_CLIP09 · Clip_09 · 张老大拍肩落命令）

**首帧**：`出图/第1集/图片/Clip09_first.png`
**尾帧**：`出图/第1集/图片/Clip09_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：秀竹峰杂役大殿/夜/内
**导演意图**：命令·重压落下；本镜只完成一个动作/信息点：从今日起，秀竹峰挑水的活儿，就归你了。天不亮开始，晚上才能停；否则老爷们责罚下来，谁也担不起。
**起幅**：回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。
**落幅**：贺平生肩膀被拍得一沉，低头应下。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；张老大画右前压，贺平生画左下承受，手部插入镜缓冲接触。
**表演节拍**：[0-5.5s] 回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。（中景到手部插入）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=命令·重压落下; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=dialogue_shot_reverse; {"axis": "张老大画右前景、贺平生画左下/画左近景，张老大→贺平生横轴锁定；正反打不得交换左右。", "beats": ["张老大收笑", "手掌拍肩", "挑水命令落下"], "blocking": "张老大画右前压，贺平生画左下承受，手部插入镜缓冲接触。", "camera_rule": "手部插入镜避免多人接触漂移，仍守横轴。", "continuity_must": ["油污手掌", "贺平生肩膀下沉", "挑水命令事实"], "eyeline": "按本集视觉契约继承；贺平生在大殿看画右上，在水缸区看后景水缸，在浅潭看画右下潭底。", "negative": ["不要换成殴打", "不要让贺平生反抗", "不要新增惩罚画面"], "shot_pairing": "与相邻反打/反应镜保持同一 180 度轴线；说话者与听者以单主体近景或 OTS/肩背配对，不在同镜抢两张正脸。", "template_id": "dialogue_shot_reverse"}
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multi_person,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "native_speech", "native_speech": true, "requires_voice_track": false, "speech_policy": "native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 20, "reference_only": false, "requires_split_relay": false}, "mode": "native_av", "quality_tier": "high", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_ZHANG_LAODA", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态,CHAR_ZHANG_LAODA/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_ZHANG_LAODA: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留
**衔接设计**：
- 入点：回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。
- 出点：贺平生肩膀被拍得一沉，低头应下。
- 转场：hard_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。
- action：回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。
- end_state：贺平生肩膀被拍得一沉，低头应下。
- constraints：首帧=出图/第1集/图片/Clip09_first.png; 尾帧=出图/第1集/图片/Clip09_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。
  action: 回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。
  end_state: 贺平生肩膀被拍得一沉，低头应下。
  constraints: 首帧=出图/第1集/图片/Clip09_first.png; 尾帧=出图/第1集/图片/Clip09_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：命令·重压落下；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。;
落幅：贺平生肩膀被拍得一沉，低头应下。;
场面调度：张老大画右前压，贺平生画左下承受，手部插入镜缓冲接触。;
表演节拍：[0-5.5s] 回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。（中景到手部插入）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=dialogue_shot_reverse；beats=张老大收笑, 手掌拍肩, 挑水命令落下；negative=不要换成殴打, 不要让贺平生反抗, 不要新增惩罚画面;
模型路由约束：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multi_person,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_ZHANG_LAODA: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：台词+口型由原生音画后端生成；mouth_visible=yes；speech_policy=native_speech；生成后保留原片音轨并检查声源/口型同步。
人物运动：回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。;
镜头运动：中景到手部插入，速度克制，服务 命令·重压落下;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=hard_cut;
声音约束：台词和口型由原生音画后端生成；保留原片音轨；禁止新增旁白或改写对白事实。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。; action: 回到杂役大殿，张老大突然收笑，身体前压，手掌落到贺平生肩上。; end: 贺平生肩膀被拍得一沉，低头应下。; constraints: 首帧=出图/第1集/图片/Clip09_first.png; 尾帧=出图/第1集/图片/Clip09_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 命令·重压落下; camera motion: 中景到手部插入, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group.
native audio policy: native speech enabled; generate dialogue and lip sync natively, keep original generated audio, no narration voice.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 10（时长 3.5s · EP01_CLIP10 · Clip_10 · 贺平生低头应是）

**首帧**：`出图/第1集/图片/Clip10_first.png`
**尾帧**：`出图/第1集/图片/Clip10_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：秀竹峰杂役大殿/夜/内
**导演意图**：命令·短反应；本镜只完成一个动作/信息点：是。
**起幅**：贺平生肩膀被拍得一沉，低头应下。
**落幅**：身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；贺平生近景占画左，张老大手掌离开画右边缘。
**表演节拍**：[0-3.5s] 贺平生肩膀被拍得一沉，低头应下。（近景·肩线下沉）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=命令·短反应; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=dialogue_shot_reverse; {"axis": "张老大画右前景、贺平生画左下/画左近景，张老大→贺平生横轴锁定；正反打不得交换左右。", "beats": ["肩膀下沉", "压住慌乱", "低头应是"], "blocking": "贺平生近景占画左，张老大手掌离开画右边缘。", "camera_rule": "短反应后硬切前情快闪。", "continuity_must": ["贺平生压住慌乱", "张老大压力未消", "大殿低冷光"], "eyeline": "按本集视觉契约继承；贺平生在大殿看画右上，在水缸区看后景水缸，在浅潭看画右下潭底。", "negative": ["不要哭喊", "不要反击", "不要改台词"], "shot_pairing": "与相邻反打/反应镜保持同一 180 度轴线；说话者与听者以单主体近景或 OTS/肩背配对，不在同镜抢两张正脸。", "template_id": "dialogue_shot_reverse"}
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "native_speech", "native_speech": true, "requires_voice_track": false, "speech_policy": "native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 20, "reference_only": false, "requires_split_relay": false}, "mode": "native_av", "quality_tier": "high", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_ZHANG_LAODA", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态,CHAR_ZHANG_LAODA/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_ZHANG_LAODA: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留
**衔接设计**：
- 入点：贺平生肩膀被拍得一沉，低头应下。
- 出点：身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。
- 转场：hard_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：贺平生肩膀被拍得一沉，低头应下。
- action：贺平生肩膀被拍得一沉，低头应下。
- end_state：身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。
- constraints：首帧=出图/第1集/图片/Clip10_first.png; 尾帧=出图/第1集/图片/Clip10_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 贺平生肩膀被拍得一沉，低头应下。
  action: 贺平生肩膀被拍得一沉，低头应下。
  end_state: 身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。
  constraints: 首帧=出图/第1集/图片/Clip10_first.png; 尾帧=出图/第1集/图片/Clip10_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：命令·短反应；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：贺平生肩膀被拍得一沉，低头应下。;
落幅：身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。;
场面调度：贺平生近景占画左，张老大手掌离开画右边缘。;
表演节拍：[0-3.5s] 贺平生肩膀被拍得一沉，低头应下。（近景·肩线下沉）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=dialogue_shot_reverse；beats=肩膀下沉, 压住慌乱, 低头应是；negative=不要哭喊, 不要反击, 不要改台词;
模型路由约束：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_ZHANG_LAODA: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：台词+口型由原生音画后端生成；mouth_visible=yes；speech_policy=native_speech；生成后保留原片音轨并检查声源/口型同步。
人物运动：贺平生肩膀被拍得一沉，低头应下。;
镜头运动：近景·肩线下沉，速度克制，服务 命令·短反应;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=hard_cut;
声音约束：台词和口型由原生音画后端生成；保留原片音轨；禁止新增旁白或改写对白事实。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 贺平生肩膀被拍得一沉，低头应下。; action: 贺平生肩膀被拍得一沉，低头应下。; end: 身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。; constraints: 首帧=出图/第1集/图片/Clip10_first.png; 尾帧=出图/第1集/图片/Clip10_end.png; asset_ids=,LOC_ZAYI_DADIAN; character_ids=CHAR_HE_PINGSHENG,CHAR_ZHANG_LAODA; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 命令·短反应; camera motion: 近景·肩线下沉, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group.
native audio policy: native speech enabled; generate dialogue and lip sync natively, keep original generated audio, no narration voice.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 11（时长 6.0s · EP01_CLIP11 · Clip_11 · 父母亡故资源被抢）

**首帧**：`出图/第1集/图片/Clip11_first.png`
**尾帧**：`出图/第1集/图片/Clip11_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：贺家旧宅/日夜碎片/回忆
**导演意图**：前情·碎片快闪；本镜只完成一个动作/信息点：八岁那年，贺平生的父亲贺三杰外出寻机缘，被妖兽所杀；母亲也很快离世，家里留下的修真资源被人抢得干干净净。
**起幅**：身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。
**落幅**：江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；快闪只给背影和物件，不新增需要长期保持的正脸。
**表演节拍**：[0-6s] 身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。（碎片蒙太奇）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=前情·碎片快闪; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=reveal_reaction_chain; {"beats": ["父亲遇妖兽背影", "母亲病榻", "资源被抢空"], "blocking": "快闪只给背影和物件，不新增需要长期保持的正脸。", "camera_rule": "三段碎片各短切，避免单镜长解释拖慢。", "continuity_must": ["父母亡故事实", "资源被抢干净", "少年孤立因果"], "cut_point": "在「江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。」落幅后切出；不得延伸新增剧情。", "knowledge_order": ["观众先读到画面信息", "贺平生只按本镜状态反应", "不提前泄露第25镜之后的信息"], "negative": ["不要血腥细节", "不要把父母画成当前登场角色", "不要出现现代物品"], "reaction_beats": ["父亲遇妖兽背影", "母亲病榻", "资源被抢空"], "reveal_object": "PROP_XIUZHEN_ZIYUAN", "template_id": "reveal_reaction_chain"}
**模型路由**：shot_type=general_motion; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.；若本镜含对白/画内发声，必须走 voice-first 配音补偿链路，或拆出 native_speech 说话特写后重跑路由。", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 2, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "n/a", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。
- 出点：江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。
- 转场：memory_flash
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。
- action：身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。
- end_state：江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。
- constraints：首帧=出图/第1集/图片/Clip11_first.png; 尾帧=出图/第1集/图片/Clip11_end.png; asset_ids=PROP_XIUZHEN_ZIYUAN,LOC_WAIMEN_JIUYUAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。
  action: 身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。
  end_state: 江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。
  constraints: 首帧=出图/第1集/图片/Clip11_first.png; 尾帧=出图/第1集/图片/Clip11_end.png; asset_ids=PROP_XIUZHEN_ZIYUAN,LOC_WAIMEN_JIUYUAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：前情·碎片快闪；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。;
落幅：江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。;
场面调度：快闪只给背影和物件，不新增需要长期保持的正脸。;
表演节拍：[0-6s] 身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。（碎片蒙太奇）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=reveal_reaction_chain；beats=父亲遇妖兽背影, 母亲病榻, 资源被抢空；negative=不要血腥细节, 不要把父母画成当前登场角色, 不要出现现代物品;
模型路由约束：shot_type=general_motion; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。;
镜头运动：碎片蒙太奇，速度克制，服务 前情·碎片快闪;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=memory_flash;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。; action: 身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化镜头表现。; end: 江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。; constraints: 首帧=出图/第1集/图片/Clip11_first.png; 尾帧=出图/第1集/图片/Clip11_end.png; asset_ids=PROP_XIUZHEN_ZIYUAN,LOC_WAIMEN_JIUYUAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 前情·碎片快闪; camera motion: 碎片蒙太奇, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 12（时长 5.0s · EP01_CLIP12 · Clip_12 · 江剑背影送往秀竹峰）

**首帧**：`出图/第1集/图片/Clip12_first.png`
**尾帧**：`出图/第1集/图片/Clip12_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：太虚门外门旧院/日/回忆
**导演意图**：前情·托付收束；本镜只完成一个动作/信息点：这些年，父亲旧友江剑照拂着他。如今江剑大道无望、年岁渐晚，只能把他推荐到秀竹峰杂役班。
**起幅**：江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。
**落幅**：贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；江剑只给背影或侧背，贺平生画面左后小比例。
**表演节拍**：[0-5s] 江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。（中景背影）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=前情·托付收束; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=multi_character_same_frame; {"beats": ["江剑背影收拾行囊", "少年站院口", "秀竹峰路尽头"], "blocking": "江剑只给背影或侧背，贺平生画面左后小比例。", "camera_rule": "中景静拍，不解析江剑正脸，接下一镜抬头看仙人。", "character_slots": {"BACKGROUND_SLOT": "外门旧院/觉醒台，低饱和回忆。", "LEFT_SLOT": "CHAR_HE_PINGSHENG/常态 状态=少年小比例或背影，小比例或背影。", "RIGHT_SLOT": "记忆人物背影，不解析正脸。"}, "continuity_must": ["江剑父亲旧友身份", "推荐到杂役班", "旧院朴素"], "face_priority": ["primary=CHAR_HE_PINGSHENG", "其他角色只作侧脸/背影/肩背/虚化，避免同框抢脸。"], "negative": ["不要让江剑御剑离开", "不要新增仙门仪式", "不要把贺平生画成年"], "overlap_rules": "人物身体/手臂/道具不得穿模；前后景分层，接触动作优先切手部/肩背插入，避免两张脸同强度抢焦。", "template_id": "multi_character_same_frame"}
**模型路由**：shot_type=multi_character_same_frame; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,multishot_candidate,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第1集/control/Clip_12/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 20, "reference_only": false, "requires_split_relay": false}, "mode": "frames2video", "quality_tier": "high", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_JIANG_JIAN", "form": ""}], "identity_preservation_plan": {"applies_to": "multi_character_same_frame", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "character_id_or_reference_group", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_12/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；degrade_plan=本 Clip 只有旁白/画面信息，无画内角色对白；视频阶段禁止模型生成旁白音频，旁白交 n2d-compose，画面按静音 image2video/frames2video 执行。。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态,CHAR_JIANG_JIAN/背影; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_JIANG_JIAN: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG,CHAR_JIANG_JIAN；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。
- 出点：贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。
- 转场：memory_match_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。
- action：江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。
- end_state：贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。
- constraints：首帧=出图/第1集/图片/Clip12_first.png; 尾帧=出图/第1集/图片/Clip12_end.png; asset_ids=,LOC_WAIMEN_JIUYUAN; character_ids=CHAR_HE_PINGSHENG,CHAR_JIANG_JIAN; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。
  action: 江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。
  end_state: 贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。
  constraints: 首帧=出图/第1集/图片/Clip12_first.png; 尾帧=出图/第1集/图片/Clip12_end.png; asset_ids=,LOC_WAIMEN_JIUYUAN; character_ids=CHAR_HE_PINGSHENG,CHAR_JIANG_JIAN; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：前情·托付收束；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。;
落幅：贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。;
场面调度：江剑只给背影或侧背，贺平生画面左后小比例。;
表演节拍：[0-5s] 江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。（中景背影）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=multi_character_same_frame；beats=江剑背影收拾行囊, 少年站院口, 秀竹峰路尽头；negative=不要让江剑御剑离开, 不要新增仙门仪式, 不要把贺平生画成年;
模型路由约束：shot_type=multi_character_same_frame; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,multishot_candidate,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_JIANG_JIAN: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。;
镜头运动：中景背影，速度克制，服务 前情·托付收束;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=memory_match_cut;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。; action: 江剑的背影收拾行囊，少年贺平生站在院口，路尽头是秀竹峰。; end: 贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。; constraints: 首帧=出图/第1集/图片/Clip12_first.png; 尾帧=出图/第1集/图片/Clip12_end.png; asset_ids=,LOC_WAIMEN_JIUYUAN; character_ids=CHAR_HE_PINGSHENG,CHAR_JIANG_JIAN; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 前情·托付收束; camera motion: 中景背影, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 13（时长 5.5s · EP01_CLIP13 · Clip_13 · 选择留下望向仙途）

**首帧**：`出图/第1集/图片/Clip13_first.png`
**尾帧**：`出图/第1集/图片/Clip13_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：秀竹峰杂役院门口/日/外
**导演意图**：前情·主角欲望；本镜只完成一个动作/信息点：所谓杂役弟子，就是打杂干活的人。因此，贺平生从外门遗孤变成了秀竹峰最底层的杂役；可他还是选择留下，离仙人近一点，也许就能离仙途近一点。
**起幅**：贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。
**落幅**：韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；修士只作远处剪影，贺平生站在灰门前画左。
**表演节拍**：[0-5.5s] 贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。（远景抬头）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=前情·主角欲望; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：{"beat_model": "takeoff_cruise_maneuver_arrival", "failure_modes": ["pose_drift", "altitude_curve_drift", "mount_shape_drift", "background_stickiness", "camera_float"], "gate_policy": "block_prompt_without_action_choreography_contract", "notes": ["lock rider/body pose and move cloud/mountain/parallax layers; only maneuver shots may change pose", "write altitude curve and mount/cloud lock so sword/cloud shape does not morph"], "required": true, "required_fields": ["beats", "speed_curve", "spatial_path", "camera_path", "readability_beats", "degrade_plan", "keyframe_plan", "post_cue_points", "physics_guard", "flight_path", "altitude_curve", "pose_lock", "parallax_layers", "mount_or_cloud_lock"], "shot_type": "flight"}
**专项镜头模板**：template_id=reveal_reaction_chain; {"beats": ["杂役身份落定", "远处修士掠过", "选择留下"], "blocking": "修士只作远处剪影，贺平生站在灰门前画左。", "camera_rule": "抬头跟随但不做高速飞行镜，重点在主角选择。", "continuity_must": ["杂役低位", "离仙途近的欲望", "不提前获得机缘"], "cut_point": "在「韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。」落幅后切出；不得延伸新增剧情。", "knowledge_order": ["观众先读到画面信息", "贺平生只按本镜状态反应", "不提前泄露第25镜之后的信息"], "negative": ["不要让主角飞起来", "不要给修士正脸", "不要变成热血胜利镜"], "reaction_beats": ["杂役身份落定", "远处修士掠过", "选择留下"], "reveal_object": "杂役身份落定", "template_id": "reveal_reaction_chain"}
**模型路由**：shot_type=flight; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=action_choreography_required,high_speed_motion,identity_drift_risk,motion_reference_candidate,multishot_candidate,pose_drift_risk,seam_relay,spatial_path_risk; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": true}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第1集/control/Clip_13/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "camera_path", "spatial_path", "parallax_layers"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 20, "reference_only": false, "requires_split_relay": false}, "mode": "frames2video", "quality_tier": "high", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}], "identity_preservation_plan": {"applies_to": "flight", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "character_id_or_reference_group", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": true, "library_path": "生产数据/motion_reference_library.json", "policy": "use same sequence/shot_type approved reference when available"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_13/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,camera_path,spatial_path,parallax_layers；failure_modes=pose_drift,altitude_curve_drift,mount_shape_drift,background_stickiness；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；degrade_plan=本 Clip 只有旁白/画面信息，无画内角色对白；视频阶段禁止模型生成旁白音频，旁白交 n2d-compose，画面按静音 image2video/frames2video 执行。。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。
- 出点：韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。
- 转场：match_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。
- action：贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。
- end_state：韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。
- constraints：首帧=出图/第1集/图片/Clip13_first.png; 尾帧=出图/第1集/图片/Clip13_end.png; asset_ids=,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。
  action: 贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。
  end_state: 韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。
  constraints: 首帧=出图/第1集/图片/Clip13_first.png; 尾帧=出图/第1集/图片/Clip13_end.png; asset_ids=,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：前情·主角欲望；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。;
落幅：韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。;
场面调度：修士只作远处剪影，贺平生站在灰门前画左。;
表演节拍：[0-5.5s] 贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。（远景抬头）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：{"beat_model": "takeoff_cruise_maneuver_arrival", "failure_modes": ["pose_drift", "altitude_curve_drift", "mount_shape_drift", "background_stickiness", "camera_float"], "gate_policy": "block_prompt_without_action_choreography_contract", "notes": ["lock rider/body pose and move cloud/mountain/parallax layers; only maneuver shots may change pose", "write altitude curve and mount/cloud lock so sword/cloud shape does not morph"], "required": true, "required_fields": ["beats", "speed_curve", "spatial_path", "camera_path", "readability_beats", "degrade_plan", "keyframe_plan", "post_cue_points", "physics_guard", "flight_path", "altitude_curve", "pose_lock", "parallax_layers", "mount_or_cloud_lock"], "shot_type": "flight"};
专项模板约束：template_id=reveal_reaction_chain；beats=杂役身份落定, 远处修士掠过, 选择留下；negative=不要让主角飞起来, 不要给修士正脸, 不要变成热血胜利镜;
模型路由约束：shot_type=flight; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=action_choreography_required,high_speed_motion,identity_drift_risk,motion_reference_candidate,multishot_candidate,pose_drift_risk,seam_relay,spatial_path_risk; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。;
镜头运动：远景抬头，速度克制，服务 前情·主角欲望;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=match_cut;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。; action: 贺平生抬头看远处御空而过的修士，身后是杂役院的灰门。; end: 韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。; constraints: 首帧=出图/第1集/图片/Clip13_first.png; 尾帧=出图/第1集/图片/Clip13_end.png; asset_ids=,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 前情·主角欲望; camera motion: 远景抬头, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 14（时长 5.5s · EP01_CLIP14 · Clip_14 · 韩老三指两口水缸）

**首帧**：`出图/第1集/图片/Clip14_first.png`
**尾帧**：`出图/第1集/图片/Clip14_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：秀竹峰水缸区/日/外
**导演意图**：现实压迫·任务落地；本镜只完成一个动作/信息点：看见那两口水缸了吗？每天必须挑满。后山山泉，来回二里，一天至少二十趟。
**起幅**：韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。
**落幅**：贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；韩老三画右前，贺平生画左后，两口水缸占后景。
**表演节拍**：[0-5.5s] 韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。（广角WS）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=现实压迫·任务落地; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=multi_character_same_frame; {"beats": ["韩老三指水缸", "水缸比例压迫", "二十趟任务落地"], "blocking": "韩老三画右前，贺平生画左后，两口水缸占后景。", "camera_rule": "固定广角建立比例，不环绕，不交换左右站位。", "character_slots": {"BACKGROUND_SLOT": "两口水缸/空屋/灰门作为空间压迫锚。", "LEFT_SLOT": "CHAR_HE_PINGSHENG/常态，画左或画左后，primary face。", "RIGHT_SLOT": "CHAR_HAN_LAOSAN/常态，画右前或侧背，secondary face。"}, "continuity_must": ["两口水缸巨大", "一天至少二十趟", "来回二里事实"], "face_priority": ["primary=CHAR_HE_PINGSHENG", "其他角色只作侧脸/背影/肩背/虚化，避免同框抢脸。"], "negative": ["不要把水缸画成小桶", "不要新增豪华庭院", "不要让两张脸同时抢焦点"], "overlap_rules": "人物身体/手臂/道具不得穿模；前后景分层，接触动作优先切手部/肩背插入，避免两张脸同强度抢焦。", "template_id": "multi_character_same_frame"}
**模型路由**：shot_type=multi_character_same_frame; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,multishot_candidate,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第1集/control/Clip_14/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 2, "reference_only": false, "requires_split_relay": false}, "mode": "frames2video", "quality_tier": "n/a", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_HAN_LAOSAN", "form": ""}], "identity_preservation_plan": {"applies_to": "multi_character_same_frame", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "character_id_or_reference_group", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_14/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态,CHAR_HAN_LAOSAN/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_HAN_LAOSAN: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG,CHAR_HAN_LAOSAN；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。
- 出点：贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。
- 转场：hard_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。
- action：韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。
- end_state：贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。
- constraints：首帧=出图/第1集/图片/Clip14_first.png; 尾帧=出图/第1集/图片/Clip14_end.png; asset_ids=PROP_WATER_JARS,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG,CHAR_HAN_LAOSAN; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。
  action: 韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。
  end_state: 贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。
  constraints: 首帧=出图/第1集/图片/Clip14_first.png; 尾帧=出图/第1集/图片/Clip14_end.png; asset_ids=PROP_WATER_JARS,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG,CHAR_HAN_LAOSAN; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：现实压迫·任务落地；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。;
落幅：贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。;
场面调度：韩老三画右前，贺平生画左后，两口水缸占后景。;
表演节拍：[0-5.5s] 韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。（广角WS）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=multi_character_same_frame；beats=韩老三指水缸, 水缸比例压迫, 二十趟任务落地；negative=不要把水缸画成小桶, 不要新增豪华庭院, 不要让两张脸同时抢焦点;
模型路由约束：shot_type=multi_character_same_frame; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,multishot_candidate,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_HAN_LAOSAN: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。;
镜头运动：广角WS，速度克制，服务 现实压迫·任务落地;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=hard_cut;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。; action: 韩老三带贺平生站在两口巨大水缸前，水缸压满竖屏画面。; end: 贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。; constraints: 首帧=出图/第1集/图片/Clip14_first.png; 尾帧=出图/第1集/图片/Clip14_end.png; asset_ids=PROP_WATER_JARS,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG,CHAR_HAN_LAOSAN; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 现实压迫·任务落地; camera motion: 广角WS, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 15（时长 4.5s · EP01_CLIP15 · Clip_15 · 贺平生仰看水缸）

**首帧**：`出图/第1集/图片/Clip15_first.png`
**尾帧**：`出图/第1集/图片/Clip15_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：秀竹峰水缸区/日/外
**导演意图**：现实压迫·比例落点；本镜只完成一个动作/信息点：对一个十四岁的少年，这不是活儿，是压在肩上的山。
**起幅**：贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。
**落幅**：韩老三匆忙把钥匙和铁索交给贺平生，转身就走。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；贺平生画左下，水缸占画面后上方，韩老三可离画。
**表演节拍**：[0-4.5s] 贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。（低角度仰拍）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=现实压迫·比例落点; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=multi_character_same_frame; {"beats": ["水缸边沿高过肩", "贺平生沉默仰看", "旁白压实任务重量"], "blocking": "贺平生画左下，水缸占画面后上方，韩老三可离画。", "camera_rule": "低角度压迫，切出前保持水缸纵深轴。", "character_slots": {"BACKGROUND_SLOT": "两口水缸/空屋/灰门作为空间压迫锚。", "LEFT_SLOT": "CHAR_HE_PINGSHENG/常态，画左或画左后，primary face。", "RIGHT_SLOT": "CHAR_HAN_LAOSAN/常态，画右前或侧背，secondary face。"}, "continuity_must": ["十四岁少年比例", "水缸压迫", "任务像山"], "face_priority": ["primary=CHAR_HE_PINGSHENG", "其他角色只作侧脸/背影/肩背/虚化，避免同框抢脸。"], "negative": ["不要夸张成魔法水缸", "不要让贺平生露出兴奋", "不要改变年龄"], "overlap_rules": "人物身体/手臂/道具不得穿模；前后景分层，接触动作优先切手部/肩背插入，避免两张脸同强度抢焦。", "template_id": "multi_character_same_frame"}
**模型路由**：shot_type=multi_character_same_frame; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,multishot_candidate,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第1集/control/Clip_15/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 2, "reference_only": false, "requires_split_relay": false}, "mode": "frames2video", "quality_tier": "n/a", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}], "identity_preservation_plan": {"applies_to": "multi_character_same_frame", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "character_id_or_reference_group", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_15/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。
- 出点：韩老三匆忙把钥匙和铁索交给贺平生，转身就走。
- 转场：reaction_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。
- action：贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。
- end_state：韩老三匆忙把钥匙和铁索交给贺平生，转身就走。
- constraints：首帧=出图/第1集/图片/Clip15_first.png; 尾帧=出图/第1集/图片/Clip15_end.png; asset_ids=PROP_WATER_JARS,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。
  action: 贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。
  end_state: 韩老三匆忙把钥匙和铁索交给贺平生，转身就走。
  constraints: 首帧=出图/第1集/图片/Clip15_first.png; 尾帧=出图/第1集/图片/Clip15_end.png; asset_ids=PROP_WATER_JARS,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：现实压迫·比例落点；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。;
落幅：韩老三匆忙把钥匙和铁索交给贺平生，转身就走。;
场面调度：贺平生画左下，水缸占画面后上方，韩老三可离画。;
表演节拍：[0-4.5s] 贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。（低角度仰拍）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=multi_character_same_frame；beats=水缸边沿高过肩, 贺平生沉默仰看, 旁白压实任务重量；negative=不要夸张成魔法水缸, 不要让贺平生露出兴奋, 不要改变年龄;
模型路由约束：shot_type=multi_character_same_frame; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,multishot_candidate,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。;
镜头运动：低角度仰拍，速度克制，服务 现实压迫·比例落点;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=reaction_cut;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。; action: 贺平生仰看水缸，水缸边沿比他肩头高，形成比例压迫。; end: 韩老三匆忙把钥匙和铁索交给贺平生，转身就走。; constraints: 首帧=出图/第1集/图片/Clip15_first.png; 尾帧=出图/第1集/图片/Clip15_end.png; asset_ids=PROP_WATER_JARS,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 现实压迫·比例落点; camera motion: 低角度仰拍, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 16（时长 4.5s · EP01_CLIP16 · Clip_16 · 韩老三交钥匙铁索）

**首帧**：`出图/第1集/图片/Clip16_first.png`
**尾帧**：`出图/第1集/图片/Clip16_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：秀竹峰杂役院/日暮/外
**导演意图**：现实压迫·安置冷淡；本镜只完成一个动作/信息点：这是你的房间。前面是食堂，吃饭别晚，晚了就没了。
**起幅**：韩老三匆忙把钥匙和铁索交给贺平生，转身就走。
**落幅**：空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；手部插入镜为主，韩老三可侧背离画，贺平生接物不追问。
**表演节拍**：[0-4.5s] 韩老三匆忙把钥匙和铁索交给贺平生，转身就走。（手部插入到背影）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=现实压迫·安置冷淡; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=multi_character_same_frame; {"beats": ["钥匙铁索交手", "韩老三转身离开", "食堂规则交代"], "blocking": "手部插入镜为主，韩老三可侧背离画，贺平生接物不追问。", "camera_rule": "动作切连接空屋，不做复杂拉扯。", "character_slots": {"BACKGROUND_SLOT": "两口水缸/空屋/灰门作为空间压迫锚。", "LEFT_SLOT": "CHAR_HE_PINGSHENG/常态，画左或画左后，primary face。", "RIGHT_SLOT": "CHAR_HAN_LAOSAN/常态，画右前或侧背，secondary face。"}, "continuity_must": ["钥匙和铁索", "韩老三冷淡", "贺平生接过"], "face_priority": ["primary=CHAR_HE_PINGSHENG", "其他角色只作侧脸/背影/肩背/虚化，避免同框抢脸。"], "negative": ["不要变成礼物递交", "不要新增温情拥抱", "不要出现现代钥匙扣"], "overlap_rules": "人物身体/手臂/道具不得穿模；前后景分层，接触动作优先切手部/肩背插入，避免两张脸同强度抢焦。", "template_id": "multi_character_same_frame"}
**模型路由**：shot_type=multi_character_same_frame; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第1集/control/Clip_16/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 2, "reference_only": false, "requires_split_relay": false}, "mode": "frames2video", "quality_tier": "n/a", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_HAN_LAOSAN", "form": ""}], "identity_preservation_plan": {"applies_to": "multi_character_same_frame", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "character_id_or_reference_group", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_16/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态,CHAR_HAN_LAOSAN/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_HAN_LAOSAN: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG,CHAR_HAN_LAOSAN；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：韩老三匆忙把钥匙和铁索交给贺平生，转身就走。
- 出点：空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。
- 转场：action_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：韩老三匆忙把钥匙和铁索交给贺平生，转身就走。
- action：韩老三匆忙把钥匙和铁索交给贺平生，转身就走。
- end_state：空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。
- constraints：首帧=出图/第1集/图片/Clip16_first.png; 尾帧=出图/第1集/图片/Clip16_end.png; asset_ids=PROP_KEY_LOCK,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG,CHAR_HAN_LAOSAN; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 韩老三匆忙把钥匙和铁索交给贺平生，转身就走。
  action: 韩老三匆忙把钥匙和铁索交给贺平生，转身就走。
  end_state: 空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。
  constraints: 首帧=出图/第1集/图片/Clip16_first.png; 尾帧=出图/第1集/图片/Clip16_end.png; asset_ids=PROP_KEY_LOCK,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG,CHAR_HAN_LAOSAN; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：现实压迫·安置冷淡；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：韩老三匆忙把钥匙和铁索交给贺平生，转身就走。;
落幅：空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。;
场面调度：手部插入镜为主，韩老三可侧背离画，贺平生接物不追问。;
表演节拍：[0-4.5s] 韩老三匆忙把钥匙和铁索交给贺平生，转身就走。（手部插入到背影）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=multi_character_same_frame；beats=钥匙铁索交手, 韩老三转身离开, 食堂规则交代；negative=不要变成礼物递交, 不要新增温情拥抱, 不要出现现代钥匙扣;
模型路由约束：shot_type=multi_character_same_frame; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色；CHAR_HAN_LAOSAN: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：韩老三匆忙把钥匙和铁索交给贺平生，转身就走。;
镜头运动：手部插入到背影，速度克制，服务 现实压迫·安置冷淡;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=action_cut;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 韩老三匆忙把钥匙和铁索交给贺平生，转身就走。; action: 韩老三匆忙把钥匙和铁索交给贺平生，转身就走。; end: 空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。; constraints: 首帧=出图/第1集/图片/Clip16_first.png; 尾帧=出图/第1集/图片/Clip16_end.png; asset_ids=PROP_KEY_LOCK,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG,CHAR_HAN_LAOSAN; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 现实压迫·安置冷淡; camera motion: 手部插入到背影, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 17（时长 5.0s · EP01_CLIP17 · Clip_17 · 空屋硬板床铁碗）

**首帧**：`出图/第1集/图片/Clip17_first.png`
**尾帧**：`出图/第1集/图片/Clip17_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：秀竹峰杂役空屋/夜/内
**导演意图**：现实压迫·贫瘠空镜；本镜只完成一个动作/信息点：房间里空空荡荡。没有被子，没有生活用具，只有一只铁碗。
**起幅**：空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。
**落幅**：贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；人物可只在门口边缘，主视觉是铁碗和硬板床。
**表演节拍**：[0-5s] 空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。（空屋慢移）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=现实压迫·贫瘠空镜; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=reveal_reaction_chain; {"beats": ["空屋建立", "铁碗冷月", "无被子无用具"], "blocking": "人物可只在门口边缘，主视觉是铁碗和硬板床。", "camera_rule": "慢移扫过物件，保持月光画右后。", "continuity_must": ["只有铁碗", "没有被子", "冷月窗格"], "cut_point": "在「贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。」落幅后切出；不得延伸新增剧情。", "knowledge_order": ["观众先读到画面信息", "贺平生只按本镜状态反应", "不提前泄露第25镜之后的信息"], "negative": ["不要出现丰盛家具", "不要加现代生活用品", "不要让房间温暖"], "reaction_beats": ["空屋建立", "铁碗冷月", "无被子无用具"], "reveal_object": "PROP_TIE_WAN、PROP_KEY_LOCK", "template_id": "reveal_reaction_chain"}
**模型路由**：shot_type=general_motion; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; risk_flags=multishot_candidate,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "If action or identity fails twice, reroute to the nearest specialized shot type.", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 20, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "fast", "reference_inputs": {"assets": [], "characters": [{"binding": "reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。
- 出点：贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。
- 转场：match_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。
- action：空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。
- end_state：贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。
- constraints：首帧=出图/第1集/图片/Clip17_first.png; 尾帧=出图/第1集/图片/Clip17_end.png; asset_ids=PROP_TIE_WAN,PROP_KEY_LOCK,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。
  action: 空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。
  end_state: 贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。
  constraints: 首帧=出图/第1集/图片/Clip17_first.png; 尾帧=出图/第1集/图片/Clip17_end.png; asset_ids=PROP_TIE_WAN,PROP_KEY_LOCK,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：现实压迫·贫瘠空镜；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。;
落幅：贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。;
场面调度：人物可只在门口边缘，主视觉是铁碗和硬板床。;
表演节拍：[0-5s] 空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。（空屋慢移）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=reveal_reaction_chain；beats=空屋建立, 铁碗冷月, 无被子无用具；negative=不要出现丰盛家具, 不要加现代生活用品, 不要让房间温暖;
模型路由约束：shot_type=general_motion; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; risk_flags=multishot_candidate,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。;
镜头运动：空屋慢移，速度克制，服务 现实压迫·贫瘠空镜;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=match_cut;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。; action: 空屋内景，硬板床、铁碗、冷月窗格，几乎没有生活物件。; end: 贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。; constraints: 首帧=出图/第1集/图片/Clip17_first.png; 尾帧=出图/第1集/图片/Clip17_end.png; asset_ids=PROP_TIE_WAN,PROP_KEY_LOCK,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 现实压迫·贫瘠空镜; camera motion: 空屋慢移, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 18（时长 5.0s · EP01_CLIP18 · Clip_18 · 门口自语先认路）

**首帧**：`出图/第1集/图片/Clip18_first.png`
**尾帧**：`出图/第1集/图片/Clip18_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：秀竹峰杂役空屋门口/夜/内外
**导演意图**：主动选择·行动前置；本镜只完成一个动作/信息点：明天再挑，万一出状况就来不及了。我必须先去认路。
**起幅**：贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。
**落幅**：动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；门框包住贺平生，空屋在画面后方冷月中。
**表演节拍**：[0-5s] 贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。（中近景·门框构图）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=主动选择·行动前置; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=dialogue_shot_reverse; {"axis": "韩老三画右前、贺平生画左后，水缸/空屋作纵深压迫轴；不得左右互换。", "beats": ["回望空屋", "压住疲惫", "决定先认路"], "blocking": "门框包住贺平生，空屋在画面后方冷月中。", "camera_rule": "短自语不需要反打，保持人物低声克制。", "continuity_must": ["手握钥匙", "疲惫但主动", "决定认路"], "eyeline": "按本集视觉契约继承；贺平生在大殿看画右上，在水缸区看后景水缸，在浅潭看画右下潭底。", "negative": ["不要大喊宣言", "不要突然斗志爆燃", "不要出现破盆"], "shot_pairing": "与相邻反打/反应镜保持同一 180 度轴线；说话者与听者以单主体近景或 OTS/肩背配对，不在同镜抢两张正脸。", "template_id": "dialogue_shot_reverse"}
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "native_speech", "native_speech": true, "requires_voice_track": false, "speech_policy": "native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 20, "reference_only": false, "requires_split_relay": false}, "mode": "native_av", "quality_tier": "high", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留
**衔接设计**：
- 入点：贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。
- 出点：动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。
- 转场：action_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。
- action：贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。
- end_state：动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。
- constraints：首帧=出图/第1集/图片/Clip18_first.png; 尾帧=出图/第1集/图片/Clip18_end.png; asset_ids=PROP_KEY_LOCK,PROP_TIE_WAN,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。
  action: 贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。
  end_state: 动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。
  constraints: 首帧=出图/第1集/图片/Clip18_first.png; 尾帧=出图/第1集/图片/Clip18_end.png; asset_ids=PROP_KEY_LOCK,PROP_TIE_WAN,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：主动选择·行动前置；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。;
落幅：动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。;
场面调度：门框包住贺平生，空屋在画面后方冷月中。;
表演节拍：[0-5s] 贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。（中近景·门框构图）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=dialogue_shot_reverse；beats=回望空屋, 压住疲惫, 决定先认路；negative=不要大喊宣言, 不要突然斗志爆燃, 不要出现破盆;
模型路由约束：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：台词+口型由原生音画后端生成；mouth_visible=yes；speech_policy=native_speech；生成后保留原片音轨并检查声源/口型同步。
人物运动：贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。;
镜头运动：中近景·门框构图，速度克制，服务 主动选择·行动前置;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=action_cut;
声音约束：台词和口型由原生音画后端生成；保留原片音轨；禁止新增旁白或改写对白事实。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。; action: 贺平生站在门口回望空屋，手握钥匙，眼神压住疲惫。; end: 动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。; constraints: 首帧=出图/第1集/图片/Clip18_first.png; 尾帧=出图/第1集/图片/Clip18_end.png; asset_ids=PROP_KEY_LOCK,PROP_TIE_WAN,LOC_ZAYI_YUAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 主动选择·行动前置; camera motion: 中近景·门框构图, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group.
native audio policy: native speech enabled; generate dialogue and lip sync natively, keep original generated audio, no narration voice.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 19（时长 7.0s · EP01_CLIP19 · Clip_19 · 挑水动作蒙太奇）

**首帧**：`出图/第1集/图片/Clip19_first.png`
**尾帧**：`出图/第1集/图片/Clip19_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：杂役院门口/后山山路/夜
**导演意图**：加速·体力消耗；本镜只完成一个动作/信息点：他锁上门，推门出去，挑起两个水桶往后山走。第一趟，两桶水压得他喘不过气；第三趟，肩膀已经被扁担磨得发疼。
**起幅**：动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。
**落幅**：夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；单人动作蒙太奇，水桶和扁担始终跟随贺平生。
**表演节拍**：[0-7s] 动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。（动作蒙太奇·跟拍碎切）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=加速·体力消耗; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=multi_character_same_frame; {"beats": ["锁门推门", "挑起水桶", "山路脚步", "扁担压肩"], "blocking": "单人动作蒙太奇，水桶和扁担始终跟随贺平生。", "camera_rule": "碎切加速但不跳空间方向，前景树枝作自然擦切。", "character_slots": {"BACKGROUND_SLOT": "冷月光、小瀑布、山路暗景。", "LEFT_SLOT": "CHAR_HE_PINGSHENG/常态 状态=肩颈红痕，画左前或侧背。", "RIGHT_SLOT": "后山浅潭/黑陶破盆/水桶，道具优先锁定。"}, "continuity_must": ["两个水桶", "扁担压肩红痕", "第一趟到第三趟递进"], "face_priority": ["primary=CHAR_HE_PINGSHENG", "其他角色只作侧脸/背影/肩背/虚化，避免同框抢脸。"], "negative": ["不要让桶变成一个", "不要让贺平生轻松飞奔", "不要出现仙术代步"], "overlap_rules": "人物身体/手臂/道具不得穿模；前后景分层，接触动作优先切手部/肩背插入，避免两张脸同强度抢焦。", "template_id": "multi_character_same_frame"}
**模型路由**：shot_type=multi_character_same_frame; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第1集/control/Clip_19/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 2, "reference_only": false, "requires_split_relay": false}, "mode": "frames2video", "quality_tier": "n/a", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}], "identity_preservation_plan": {"applies_to": "multi_character_same_frame", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "character_id_or_reference_group", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_19/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。
- 出点：夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。
- 转场：montage_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。
- action：动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。
- end_state：夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。
- constraints：首帧=出图/第1集/图片/Clip19_first.png; 尾帧=出图/第1集/图片/Clip19_end.png; asset_ids=PROP_SHUI_TONG,PROP_BIAN_DAN,LOC_HOUSHAN_QIANTAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。
  action: 动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。
  end_state: 夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。
  constraints: 首帧=出图/第1集/图片/Clip19_first.png; 尾帧=出图/第1集/图片/Clip19_end.png; asset_ids=PROP_SHUI_TONG,PROP_BIAN_DAN,LOC_HOUSHAN_QIANTAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：加速·体力消耗；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。;
落幅：夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。;
场面调度：单人动作蒙太奇，水桶和扁担始终跟随贺平生。;
表演节拍：[0-7s] 动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。（动作蒙太奇·跟拍碎切）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=multi_character_same_frame；beats=锁门推门, 挑起水桶, 山路脚步, 扁担压肩；negative=不要让桶变成一个, 不要让贺平生轻松飞奔, 不要出现仙术代步;
模型路由约束：shot_type=multi_character_same_frame; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。;
镜头运动：动作蒙太奇·跟拍碎切，速度克制，服务 加速·体力消耗;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=montage_cut;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。; action: 动作蒙太奇：锁门、推门、挑桶、山路脚步、扁担压肩，前景树枝掠过。; end: 夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。; constraints: 首帧=出图/第1集/图片/Clip19_first.png; 尾帧=出图/第1集/图片/Clip19_end.png; asset_ids=PROP_SHUI_TONG,PROP_BIAN_DAN,LOC_HOUSHAN_QIANTAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 加速·体力消耗; camera motion: 动作蒙太奇·跟拍碎切, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 20（时长 5.0s · EP01_CLIP20 · Clip_20 · 第五次水边微光）

**首帧**：`出图/第1集/图片/Clip20_first.png`
**尾帧**：`出图/第1集/图片/Clip20_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：后山山泉浅潭/夜/外
**导演意图**：异常前奏·疲惫到钩子；本镜只完成一个动作/信息点：夜越来越深，他还是决定再挑一次。第五次来到水边时，清澈的浅潭底下，忽然有一点微光。
**起幅**：夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。
**落幅**：贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；贺平生画左前，浅潭画右下，微光只是一点。
**表演节拍**：[0-5s] 夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。（低机位到水面CU）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=异常前奏·疲惫到钩子; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=reveal_reaction_chain; {"beats": ["第五次到水边", "弯腰打水", "潭底微光出现"], "blocking": "贺平生画左前，浅潭画右下，微光只是一点。", "camera_rule": "低机位慢压到水面，微光不要变强。", "continuity_must": ["第五次事实", "疲惫状态", "一点微光"], "cut_point": "在「贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。」落幅后切出；不得延伸新增剧情。", "knowledge_order": ["观众先读到画面信息", "贺平生只按本镜状态反应", "不提前泄露第25镜之后的信息"], "negative": ["不要强光照亮全场", "不要让破盆提前完整浮出", "不要让主角兴奋跳起"], "reaction_beats": ["第五次到水边", "弯腰打水", "潭底微光出现"], "reveal_object": "PROP_SHUI_TONG、PROP_HEI_TAO_PEN", "template_id": "reveal_reaction_chain"}
**模型路由**：shot_type=general_motion; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; risk_flags=multishot_candidate,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "If action or identity fails twice, reroute to the nearest specialized shot type.", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 20, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "fast", "reference_inputs": {"assets": [], "characters": [{"binding": "reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。
- 出点：贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。
- 转场：j_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。
- action：夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。
- end_state：贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。
- constraints：首帧=出图/第1集/图片/Clip20_first.png; 尾帧=出图/第1集/图片/Clip20_end.png; asset_ids=PROP_SHUI_TONG,PROP_HEI_TAO_PEN,LOC_HOUSHAN_QIANTAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。
  action: 夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。
  end_state: 贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。
  constraints: 首帧=出图/第1集/图片/Clip20_first.png; 尾帧=出图/第1集/图片/Clip20_end.png; asset_ids=PROP_SHUI_TONG,PROP_HEI_TAO_PEN,LOC_HOUSHAN_QIANTAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：异常前奏·疲惫到钩子；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。;
落幅：贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。;
场面调度：贺平生画左前，浅潭画右下，微光只是一点。;
表演节拍：[0-5s] 夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。（低机位到水面CU）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=reveal_reaction_chain；beats=第五次到水边, 弯腰打水, 潭底微光出现；negative=不要强光照亮全场, 不要让破盆提前完整浮出, 不要让主角兴奋跳起;
模型路由约束：shot_type=general_motion; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; risk_flags=multishot_candidate,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。;
镜头运动：低机位到水面CU，速度克制，服务 异常前奏·疲惫到钩子;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=j_cut;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。; action: 夜色下第五次到水边，贺平生弯腰打水，潭底忽然有一点微光。; end: 贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。; constraints: 首帧=出图/第1集/图片/Clip20_first.png; 尾帧=出图/第1集/图片/Clip20_end.png; asset_ids=PROP_SHUI_TONG,PROP_HEI_TAO_PEN,LOC_HOUSHAN_QIANTAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 异常前奏·疲惫到钩子; camera motion: 低机位到水面CU, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 21（时长 3.5s · EP01_CLIP21 · Clip_21 · 贺平生屏息停住）

**首帧**：`出图/第1集/图片/Clip21_first.png`
**尾帧**：`出图/第1集/图片/Clip21_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：后山山泉浅潭/夜/外
**导演意图**：异常·反应停顿；本镜只完成一个动作/信息点：这是……
**起幅**：贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。
**落幅**：水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；贺平生脸在画左，水桶和潭面在画右下。
**表演节拍**：[0-3.5s] 贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。（近景·水桶半浸）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=异常·反应停顿; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=dialogue_shot_reverse; {"axis": "贺平生画左前，浅潭/破盆画右下，视线沿画左上到画右下斜轴。", "beats": ["动作停住", "疲惫转警觉", "短句屏息"], "blocking": "贺平生脸在画左，水桶和潭面在画右下。", "camera_rule": "一拍停顿，不拉长，不让微光抢全镜。", "continuity_must": ["水桶半浸", "疲惫警觉", "短句事实"], "eyeline": "按本集视觉契约继承；贺平生在大殿看画右上，在水缸区看后景水缸，在浅潭看画右下潭底。", "negative": ["不要惊叫", "不要发现神器全貌", "不要转成白天"], "shot_pairing": "与相邻反打/反应镜保持同一 180 度轴线；说话者与听者以单主体近景或 OTS/肩背配对，不在同镜抢两张正脸。", "template_id": "dialogue_shot_reverse"}
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "native_speech", "native_speech": true, "requires_voice_track": false, "speech_policy": "native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 20, "reference_only": false, "requires_split_relay": false}, "mode": "native_av", "quality_tier": "high", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词/口型/声源同步，确认原片音轨保留
**衔接设计**：
- 入点：贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。
- 出点：水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。
- 转场：reaction_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。
- action：贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。
- end_state：水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。
- constraints：首帧=出图/第1集/图片/Clip21_first.png; 尾帧=出图/第1集/图片/Clip21_end.png; asset_ids=PROP_SHUI_TONG,LOC_HOUSHAN_QIANTAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。
  action: 贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。
  end_state: 水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。
  constraints: 首帧=出图/第1集/图片/Clip21_first.png; 尾帧=出图/第1集/图片/Clip21_end.png; asset_ids=PROP_SHUI_TONG,LOC_HOUSHAN_QIANTAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：异常·反应停顿；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。;
落幅：水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。;
场面调度：贺平生脸在画左，水桶和潭面在画右下。;
表演节拍：[0-3.5s] 贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。（近景·水桶半浸）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=dialogue_shot_reverse；beats=动作停住, 疲惫转警觉, 短句屏息；negative=不要惊叫, 不要发现神器全貌, 不要转成白天;
模型路由约束：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback_backends=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group; risk_flags=mouth_visible,multishot_candidate,native_speech,seam_relay; degrade_plan=原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：台词+口型由原生音画后端生成；mouth_visible=yes；speech_policy=native_speech；生成后保留原片音轨并检查声源/口型同步。
人物运动：贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。;
镜头运动：近景·水桶半浸，速度克制，服务 异常·反应停顿;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=reaction_cut;
声音约束：台词和口型由原生音画后端生成；保留原片音轨；禁止新增旁白或改写对白事实。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。; action: 贺平生停住动作，水桶半浸在水里，脸上是疲惫中的警觉。; end: 水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。; constraints: 首帧=出图/第1集/图片/Clip21_first.png; 尾帧=出图/第1集/图片/Clip21_end.png; asset_ids=PROP_SHUI_TONG,LOC_HOUSHAN_QIANTAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 异常·反应停顿; camera motion: 近景·水桶半浸, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=native_av; native_audio_policy=native_speech; identity_requirement=character_id_or_reference_group.
native audio policy: native speech enabled; generate dialogue and lip sync natively, keep original generated audio, no narration voice.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 22（时长 4.5s · EP01_CLIP22 · Clip_22 · 水下黑陶破盆特写）

**首帧**：`出图/第1集/图片/Clip22_first.png`
**尾帧**：`出图/第1集/图片/Clip22_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：后山山泉浅潭/夜/水下
**导演意图**：异常·道具揭示；本镜只完成一个动作/信息点：水底躺着一个黑乎乎的破旧陶盆，正好反出一缕月光。
**起幅**：水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。
**落幅**：贺平生把陶盆从水里捞起，水珠顺着破口滴落。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；无人脸，道具占画面中心偏右，砂石稳定。
**表演节拍**：[0-4.5s] 水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。（水下ECU）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=异常·道具揭示; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=reveal_reaction_chain; {"beats": ["水下特写", "黑陶破盆现身", "一缕月光反射"], "blocking": "无人脸，道具占画面中心偏右，砂石稳定。", "camera_rule": "固定水下特写，水纹轻动，保持月光冷蓝。", "continuity_must": ["黑乎乎破旧陶盆", "砂石水下", "一缕月光"], "cut_point": "在「贺平生把陶盆从水里捞起，水珠顺着破口滴落。」落幅后切出；不得延伸新增剧情。", "knowledge_order": ["观众先读到画面信息", "贺平生只按本镜状态反应", "不提前泄露第25镜之后的信息"], "negative": ["不要变成金盆", "不要发强光", "不要出现文字符号"], "reaction_beats": ["水下特写", "黑陶破盆现身", "一缕月光反射"], "reveal_object": "PROP_HEI_TAO_PEN", "template_id": "reveal_reaction_chain"}
**模型路由**：shot_type=general_motion; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=none; risk_flags=multishot_candidate,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "If action or identity fails twice, reroute to the nearest specialized shot type.", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 20, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "fast", "reference_inputs": {"assets": [], "characters": [], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=none; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；无命名人物；道具/场景按 asset registry 和首帧锁定。
**近景/反打身份锁定**：主焦点=无；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。
- 出点：贺平生把陶盆从水里捞起，水珠顺着破口滴落。
- 转场：hard_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。
- action：水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。
- end_state：贺平生把陶盆从水里捞起，水珠顺着破口滴落。
- constraints：首帧=出图/第1集/图片/Clip22_first.png; 尾帧=出图/第1集/图片/Clip22_end.png; asset_ids=PROP_HEI_TAO_PEN,LOC_HOUSHAN_QIANTAN; character_ids=; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。
  action: 水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。
  end_state: 贺平生把陶盆从水里捞起，水珠顺着破口滴落。
  constraints: 首帧=出图/第1集/图片/Clip22_first.png; 尾帧=出图/第1集/图片/Clip22_end.png; asset_ids=PROP_HEI_TAO_PEN,LOC_HOUSHAN_QIANTAN; character_ids=; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：异常·道具揭示；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。;
落幅：贺平生把陶盆从水里捞起，水珠顺着破口滴落。;
场面调度：无人脸，道具占画面中心偏右，砂石稳定。;
表演节拍：[0-4.5s] 水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。（水下ECU）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=reveal_reaction_chain；beats=水下特写, 黑陶破盆现身, 一缕月光反射；negative=不要变成金盆, 不要发强光, 不要出现文字符号;
模型路由约束：shot_type=general_motion; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=none; risk_flags=multishot_candidate,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：无命名人物；道具/场景按 asset registry 和首帧锁定。;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。;
镜头运动：水下ECU，速度克制，服务 异常·道具揭示;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=hard_cut;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。; action: 水下特写，黑乎乎的旧陶盆躺在砂石间，只反出一线冷月光。; end: 贺平生把陶盆从水里捞起，水珠顺着破口滴落。; constraints: 首帧=出图/第1集/图片/Clip22_first.png; 尾帧=出图/第1集/图片/Clip22_end.png; asset_ids=PROP_HEI_TAO_PEN,LOC_HOUSHAN_QIANTAN; character_ids=; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 异常·道具揭示; camera motion: 水下ECU, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=image2video; native_audio_policy=none; identity_requirement=none.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 23（时长 5.5s · EP01_CLIP23 · Clip_23 · 捞起破盆误判普通）

**首帧**：`出图/第1集/图片/Clip23_first.png`
**尾帧**：`出图/第1集/图片/Clip23_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：后山山泉浅潭/夜/外
**导演意图**：异常·误判松气；本镜只完成一个动作/信息点：我还以为是什么宝贝，原来是个破盆啊。
**起幅**：贺平生把陶盆从水里捞起，水珠顺着破口滴落。
**落幅**：贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；贺平生手臂和破盆主导，脸只作疲惫松气反应。
**表演节拍**：[0-5.5s] 贺平生把陶盆从水里捞起，水珠顺着破口滴落。（中景到道具CU）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=异常·误判松气; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=reveal_reaction_chain; {"beats": ["伸手捞起", "水珠滴落", "误判普通破盆"], "blocking": "贺平生手臂和破盆主导，脸只作疲惫松气反应。", "camera_rule": "动作切清楚交代捞起，破盆形态保持旧黑陶。", "continuity_must": ["旧黑陶破盆", "水珠滴落", "误判不是宝贝"], "cut_point": "在「贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。」落幅后切出；不得延伸新增剧情。", "knowledge_order": ["观众先读到画面信息", "贺平生只按本镜状态反应", "不提前泄露第25镜之后的信息"], "negative": ["不要让破盆完整修复", "不要显露系统界面", "不要强行发光"], "reaction_beats": ["伸手捞起", "水珠滴落", "误判普通破盆"], "reveal_object": "PROP_HEI_TAO_PEN、PROP_SHUI_TONG", "template_id": "reveal_reaction_chain"}
**模型路由**：shot_type=general_motion; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=reference_group; risk_flags=seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "If action or identity fails twice, reroute to the nearest specialized shot type.", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 20, "reference_only": false, "requires_split_relay": false}, "mode": "frames2video", "quality_tier": "fast", "reference_inputs": {"assets": [], "characters": [{"binding": "reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：贺平生把陶盆从水里捞起，水珠顺着破口滴落。
- 出点：贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。
- 转场：action_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：贺平生把陶盆从水里捞起，水珠顺着破口滴落。
- action：贺平生把陶盆从水里捞起，水珠顺着破口滴落。
- end_state：贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。
- constraints：首帧=出图/第1集/图片/Clip23_first.png; 尾帧=出图/第1集/图片/Clip23_end.png; asset_ids=PROP_HEI_TAO_PEN,PROP_SHUI_TONG,LOC_HOUSHAN_QIANTAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 贺平生把陶盆从水里捞起，水珠顺着破口滴落。
  action: 贺平生把陶盆从水里捞起，水珠顺着破口滴落。
  end_state: 贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。
  constraints: 首帧=出图/第1集/图片/Clip23_first.png; 尾帧=出图/第1集/图片/Clip23_end.png; asset_ids=PROP_HEI_TAO_PEN,PROP_SHUI_TONG,LOC_HOUSHAN_QIANTAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：异常·误判松气；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：贺平生把陶盆从水里捞起，水珠顺着破口滴落。;
落幅：贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。;
场面调度：贺平生手臂和破盆主导，脸只作疲惫松气反应。;
表演节拍：[0-5.5s] 贺平生把陶盆从水里捞起，水珠顺着破口滴落。（中景到道具CU）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=reveal_reaction_chain；beats=伸手捞起, 水珠滴落, 误判普通破盆；negative=不要让破盆完整修复, 不要显露系统界面, 不要强行发光;
模型路由约束：shot_type=general_motion; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=reference_group; risk_flags=seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：贺平生把陶盆从水里捞起，水珠顺着破口滴落。;
镜头运动：中景到道具CU，速度克制，服务 异常·误判松气;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=action_cut;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 贺平生把陶盆从水里捞起，水珠顺着破口滴落。; action: 贺平生把陶盆从水里捞起，水珠顺着破口滴落。; end: 贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。; constraints: 首帧=出图/第1集/图片/Clip23_first.png; 尾帧=出图/第1集/图片/Clip23_end.png; asset_ids=PROP_HEI_TAO_PEN,PROP_SHUI_TONG,LOC_HOUSHAN_QIANTAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 异常·误判松气; camera motion: 中景到道具CU, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=reference_group.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 24（时长 4.5s · EP01_CLIP24 · Clip_24 · 夹破盆转身能用）

**首帧**：`出图/第1集/图片/Clip24_first.png`
**尾帧**：`出图/第1集/图片/Clip24_end.png`
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：后山山泉浅潭/夜/外
**导演意图**：异常·务实遮掩；本镜只完成一个动作/信息点：不过也能用。拿回去洗脸洗衣服，正好。
**起幅**：贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。
**落幅**：破盆离水的极近特写，盆底微光短短一亮，画面硬断。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；贺平生背向/侧身，破盆夹在臂弯可见，水桶仍在。
**表演节拍**：[0-4.5s] 贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。（中景·转身）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=异常·务实遮掩; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=multi_character_same_frame; {"beats": ["破盆夹臂弯", "重新挑水桶", "务实转身"], "blocking": "贺平生背向/侧身，破盆夹在臂弯可见，水桶仍在。", "camera_rule": "中景转身接最终道具特写，人物不看盆底。", "character_slots": {"BACKGROUND_SLOT": "冷月光、小瀑布、山路暗景。", "LEFT_SLOT": "CHAR_HE_PINGSHENG/常态 状态=肩颈红痕，画左前或侧背。", "RIGHT_SLOT": "后山浅潭/黑陶破盆/水桶，道具优先锁定。"}, "continuity_must": ["臂弯夹破盆", "继续挑水", "务实判断"], "face_priority": ["primary=CHAR_HE_PINGSHENG", "其他角色只作侧脸/背影/肩背/虚化，避免同框抢脸。"], "negative": ["不要让主角看到微光", "不要丢失水桶", "不要让破盆变新"], "overlap_rules": "人物身体/手臂/道具不得穿模；前后景分层，接触动作优先切手部/肩背插入，避免两张脸同强度抢焦。", "template_id": "multi_character_same_frame"}
**模型路由**：shot_type=multi_character_same_frame; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第1集/control/Clip_24/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "first_last", "first_frame": true, "last_frame": true, "mid_anchors": 0, "native_timeline_frames": 2, "reference_only": false, "requires_split_relay": false}, "mode": "frames2video", "quality_tier": "n/a", "reference_inputs": {"assets": [], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_HE_PINGSHENG", "form": ""}], "identity_preservation_plan": {"applies_to": "multi_character_same_frame", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "character_id_or_reference_group", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_24/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.。
**角色身份注册层**：reference_group=identity_registry.reference_group; character_id=CHAR_HE_PINGSHENG/常态; face_lock=reference_group_fallback; 脸型/五官比例/发型发髻/服装配色保持不变。；CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色
**近景/反打身份锁定**：主焦点=CHAR_HE_PINGSHENG；使用 identity_registry / identity_adapter_matrix / reference_group / Face Lock / 表情锚；锁脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色和年龄段；配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。
- 出点：破盆离水的极近特写，盆底微光短短一亮，画面硬断。
- 转场：hard_cut
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。
- action：贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。
- end_state：破盆离水的极近特写，盆底微光短短一亮，画面硬断。
- constraints：首帧=出图/第1集/图片/Clip24_first.png; 尾帧=出图/第1集/图片/Clip24_end.png; asset_ids=PROP_HEI_TAO_PEN,PROP_SHUI_TONG,PROP_BIAN_DAN,LOC_HOUSHAN_QIANTAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。
  action: 贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。
  end_state: 破盆离水的极近特写，盆底微光短短一亮，画面硬断。
  constraints: 首帧=出图/第1集/图片/Clip24_first.png; 尾帧=出图/第1集/图片/Clip24_end.png; asset_ids=PROP_HEI_TAO_PEN,PROP_SHUI_TONG,PROP_BIAN_DAN,LOC_HOUSHAN_QIANTAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：异常·务实遮掩；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。;
落幅：破盆离水的极近特写，盆底微光短短一亮，画面硬断。;
场面调度：贺平生背向/侧身，破盆夹在臂弯可见，水桶仍在。;
表演节拍：[0-4.5s] 贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。（中景·转身）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=multi_character_same_frame；beats=破盆夹臂弯, 重新挑水桶, 务实转身；negative=不要让主角看到微光, 不要丢失水桶, 不要让破盆变新;
模型路由约束：shot_type=multi_character_same_frame; primary_backend=seedance; fallback_backends=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; risk_flags=identity_drift_risk,multi_person,seam_relay; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。;
镜头运动：中景·转身，速度克制，服务 异常·务实遮掩;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=hard_cut;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。; action: 贺平生把破盆夹在臂弯，重新挑起水桶，务实地转身。; end: 破盆离水的极近特写，盆底微光短短一亮，画面硬断。; constraints: 首帧=出图/第1集/图片/Clip24_first.png; 尾帧=出图/第1集/图片/Clip24_end.png; asset_ids=PROP_HEI_TAO_PEN,PROP_SHUI_TONG,PROP_BIAN_DAN,LOC_HOUSHAN_QIANTAN; character_ids=CHAR_HE_PINGSHENG; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 异常·务实遮掩; camera motion: 中景·转身, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸

## Clip 25（时长 4.5s · EP01_CLIP25 · Clip_25 · 盆底微光硬断）

**首帧**：`出图/第1集/图片/Clip25_first.png`
**中段锚帧**：`出图/第1集/图片/Clip25_mid.png`（2.2s；集尾微光必须单独锁定，避免变成强光神器。）
**中段锚帧豁免**：2026-07-01 镜头密度返工：每个细分镜头已拆成 3-7s 物理 Clip，单 Clip 只承载一个动作/信息点，内部不再新增中段锚帧。
**场景**：后山山泉浅潭/夜/外
**导演意图**：留白·集尾硬断；本镜只完成一个动作/信息点：他没有看见，陶盆离开水面的一瞬间，盆底那点微光，又亮了一下。
**起幅**：破盆离水的极近特写，盆底微光短短一亮，画面硬断。
**落幅**：黑陶破盆离水一瞬，盆底微光再亮，画面硬断。
**场面调度**：细分镜头后每 Clip 只保留一个主体动作；多人/群像只在远景或虚化层出现，清晰正脸不超过一人。；人物只露手臂或背影边缘，观众视线锁在盆底微光。
**表演节拍**：[0-4.5s] 破盆离水的极近特写，盆底微光短短一亮，画面硬断。（极近特写·定格硬断）；微表情=起承转合只服务本镜一个动作/信息点；不在单 Clip 内塞多次表演转折。
**运动精修**：幅度=低到中；能量=留白·集尾硬断; 身体守卫=脸部轮廓、五官比例、发型发髻、肩颈、手部和道具不拉伸不穿模。
**环境交互**：尘雾、衣料、水面、月光或道具反光只随本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。
**专项镜头模板**：template_id=reveal_reaction_chain; {"beats": ["破盆离水", "盆底微光一亮", "画面硬断"], "blocking": "人物只露手臂或背影边缘，观众视线锁在盆底微光。", "camera_rule": "极近特写，微光只一瞬，硬断到黑。", "continuity_must": ["主角没有看见", "微光极弱", "集尾硬断"], "cut_point": "在「黑陶破盆离水一瞬，盆底微光再亮，画面硬断。」落幅后切出；不得延伸新增剧情。", "knowledge_order": ["观众先读到画面信息", "贺平生只按本镜状态反应", "不提前泄露第25镜之后的信息"], "negative": ["不要变成光柱", "不要出现系统文字", "不要让主角回头发现"], "reaction_beats": ["破盆离水", "盆底微光一亮", "画面硬断"], "reveal_object": "PROP_HEI_TAO_PEN", "template_id": "reveal_reaction_chain"}
**模型路由**：shot_type=general_motion; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=none; risk_flags=native_multiframe; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。
**执行配方 / Execution Recipe**：{"audio_inputs": {"native_audio_policy": "none", "native_speech": false, "requires_voice_track": false, "speech_policy": "off"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "If action or identity fails twice, reroute to the nearest specialized shot type.", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 20, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "fast", "reference_inputs": {"assets": [], "characters": [], "identity_preservation_plan": {"applies_to": "prop_closeup", "fallback_plan": "no character face in frame", "reference_strategy": "asset_registry", "required_identity_anchors": []}, "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。level=none；manifest_path=；required_inputs=；failure_modes=；gate_policy=not_required。
**角色身份注册层**：无人物；本镜为黑陶破盆物件特写，identity_requirement=none。
**近景/反打身份锁定**：无人物；只锁 PROP_HEI_TAO_PEN 形状、材质、缺口和微光强度。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=off；compose_policy=丢弃；review=生成后确认无原生人声、无旁白、无哼唱
**衔接设计**：
- 入点：破盆离水的极近特写，盆底微光短短一亮，画面硬断。
- 出点：黑陶破盆离水一瞬，盆底微光再亮，画面硬断。
- 转场：hard_cut_to_black
- 连贯性：轴线、人物左右站位、出入画方向、首尾帧约束、服装发型、光位和道具比例保持一致。

**continuity**：
- start_state：破盆离水的极近特写，盆底微光短短一亮，画面硬断。
- action：破盆离水的极近特写，盆底微光短短一亮，画面硬断。
- end_state：黑陶破盆离水一瞬，盆底微光再亮，画面硬断。
- constraints：首帧=出图/第1集/图片/Clip25_first.png; 尾帧=无; asset_ids=PROP_HEI_TAO_PEN,LOC_HOUSHAN_QIANTAN; character_ids=; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
- negative：不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。

### 视频 prompt（中文，目标=即梦/Seedance/Dreamina）

```text
continuity:
  start_state: 破盆离水的极近特写，盆底微光短短一亮，画面硬断。
  action: 破盆离水的极近特写，盆底微光短短一亮，画面硬断。
  end_state: 黑陶破盆离水一瞬，盆底微光再亮，画面硬断。
  constraints: 首帧=出图/第1集/图片/Clip25_first.png; 尾帧=无; asset_ids=PROP_HEI_TAO_PEN,LOC_HOUSHAN_QIANTAN; character_ids=; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。
  negative: 不要换脸、不要换衣、不要新增清晰陌生脸、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要强仙侠光柱、不要现代物。
导演意图：留白·集尾硬断；本镜只完成一个动作/信息点，不重设首帧视觉；
起幅：破盆离水的极近特写，盆底微光短短一亮，画面硬断。;
落幅：黑陶破盆离水一瞬，盆底微光再亮，画面硬断。;
场面调度：人物只露手臂或背影边缘，观众视线锁在盆底微光。;
表演节拍：[0-4.5s] 破盆离水的极近特写，盆底微光短短一亮，画面硬断。（极近特写·定格硬断）;
运动精修约束：幅度低到中，身体守卫锁脸型/手部/道具边界，不穿模，不融化;
环境交互约束：尘雾、衣料、水面、月光或道具反光只做小幅物理响应;
动作编排约束：无。readability_beats=按本镜单动作链检查；degrade_plan=必要时拆为短镜/反应/道具特写。;
专项模板约束：template_id=reveal_reaction_chain；beats=破盆离水, 盆底微光一亮, 画面硬断；negative=不要变成光柱, 不要出现系统文字, 不要让主角回头发现;
模型路由约束：shot_type=general_motion; primary_backend=seedance; fallback_backends=seedance; mode=image2video; native_audio_policy=none; identity_requirement=none; risk_flags=native_multiframe; degrade_plan=本 Clip 不提交原生台词；视频阶段禁止模型生成旁白/台词音频，旁白/不可见台词交 n2d-compose 或配音链，画面按静音图生视频执行。;
物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact/camera_path/spatial_path 控制资产；degrade_only 时按 degrade_plan 拆成手部特写/反打/OTS/道具特写/固定镜，不直接生成超出控制资产的复杂动作；禁止只靠文本 prompt 猜遮挡、手部归属、路径或高度;
身份锁定约束：CHAR_HE_PINGSHENG: Character ID / Face Lock / reference_group / identity_registry 锁脸型、年龄段、发型发髻、服装配色;
近景身份锁定约束：CU/MCU/反打/说话镜锁脸型、五官比例、发型发髻、标志配饰、服装配色；表情只动面部肌肉，锁脸不锁情;
原生音画约束：无对白、无旁白、禁止原生人声；mouth_visible=no；speech_policy=off；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
人物运动：破盆离水的极近特写，盆底微光短短一亮，画面硬断。;
镜头运动：极近特写·定格硬断，速度克制，服务 留白·集尾硬断;
动态细节：衣料/发丝/尘雾/水面/月光小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，转场=hard_cut_to_black;
声音约束：无对白、无旁白、不要生成原生人声；如平台自动产出环境声，compose 默认丢弃，本镜只保留画面。
```

### 视频 prompt（英文，目标=安全兜底/海外）

```text
continuity start: 破盆离水的极近特写，盆底微光短短一亮，画面硬断。; action: 破盆离水的极近特写，盆底微光短短一亮，画面硬断。; end: 黑陶破盆离水一瞬，盆底微光再亮，画面硬断。; constraints: 首帧=出图/第1集/图片/Clip25_first.png; 尾帧=无; asset_ids=PROP_HEI_TAO_PEN,LOC_HOUSHAN_QIANTAN; character_ids=; 保持光位、轴线、服装、年龄、道具比例和 reference_group 身份锁。; negative: no face change, no costume change, no new clear faces, no text, no watermark.
director intent: 留白·集尾硬断; camera motion: 极近特写·定格硬断, restrained speed; dynamic detail: dust, cloth, water, moonlight or prop reflections respond subtly to the action.
identity constraint: use identity_registry, identity_adapter_matrix, reference_group and Face Lock; preserve facial proportions, hairstyle, accessories, outfit palette, age and costume.
model route constraint: primary_backend=seedance; fallback=seedance; mode=image2video; native_audio_policy=none; identity_requirement=none.
native audio policy: no dialogue or narration voice; speech_policy=off; discard any generated audio at compose.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全
2. ✅ 人物运动动作链明确，幅度可控，可由首帧自然推出
3. ✅ 镜头运动词明确，速度和方向明确
4. ✅ 动态细节与环境交互成立，不改首帧设定
5. ✅ 模型路由、执行配方、身份锁定、原生音画策略与 route 一致
6. ✅ Motion Control 若 required，manifest_path、required_inputs、failure_modes、degrade_plan 已写；生成后检查 FeatureMelting/特征融化

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然；动作编排/可读性节拍成立
- [ ] 镜头运动符合 prompt
- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序、路径/姿态/视差漂移和特征融化
- [ ] 衔接落点可接下一 Clip
- [ ] 身份不漂移，道具不消失，轴线不反，光位不跳，无新增清晰陌生脸
