# 逐 Clip 视频 prompt

本文件由 n2d-video 阶段A按 storyboard/video_model_routes/identity/director sidecars 生成；每段含提交前检查与生成后自检。

### 剧本可看性合同（全局签收）
**core_attraction**：category=穿越求生 + 金手指觉醒 + 道德反转 cliffhanger；type=危机求生/系统爽点/反选择；why_watch=姜月初刚穿越就落在尸场和虎妖面前，唯一生路来自百妖谱规则，但规则逼她把刀指向唯一可能救她的人。；audience_payoff=观众先得到尸场醒来和虎妖复活的压迫，再看到百妖谱开局规则，最后被“杀裴换活路”的反常选择钩到第2集。；viewer_question=她刺下这一刀后，百妖谱会不会生效？裴长青是真死还是另有后手？虎山神会如何反扑？；climax=EP01_CLIP10-EP01_CLIP11：姜月初长刀入胸，低声说“我只想活下去”。。
**first_3s_visual_hook**：hook_type=危机；visual_hook=姜月初脸侧压着血尘枯草猛然睁眼，前景虚焦是尸骸手指，静音也能看出她在死人堆中醒来。；content_promise=姜月初为什么会在死人堆中醒来，她能否从虎妖尸场活下去。；viewer_question=这个现代女孩为什么穿越成囚犯，死人堆里还有什么活物在盯着她？；onscreen_text=刚穿越就躺进死人堆，她今晚还能活下来吗？；muted_readable=True。
**retention_promise_ledger**：
- hook_id=OPEN_01；promise_type=opening_hook；opened_at=EP01_CLIP01；payoff_clip=EP01_CLIP07；payoff_due=EP01_CLIP07；payoff_status=paid；promise=姜月初为什么在尸场醒来，她能否找到活路。；payoff_evidence=百妖谱第一次开启，给出斩杀生物获得道行的活路。
- hook_id=MID_01；promise_type=mid_hook；opened_at=EP01_CLIP05；payoff_clip=EP01_CLIP06；payoff_due=EP01_CLIP06；payoff_status=paid；promise=死透的虎妖为什么还能复活。；payoff_evidence=裴长青确认此前斩穿心脏仍杀不死虎妖，虎妖以复苏态压制全场。
- hook_id=TAIL_01；promise_type=cliffhanger；opened_at=EP01_CLIP10；payoff_due=第2集开场；promise=姜月初刺杀裴长青后，能否借百妖谱获得道行并反杀或收录虎山神。
**audience_question_ledger**：
- question_id=Q01；signal=系统；status=paid_or_progressed；expected_next_handling=本集兑现/推进
- question_id=Q02；signal=系统；status=paid_or_progressed；expected_next_handling=本集兑现/推进
- question_id=Q03；signal=系统；status=paid_or_progressed；expected_next_handling=本集兑现/推进
- question_id=Q04；signal=系统；status=paid_or_progressed；expected_next_handling=本集兑现/推进
- question_id=Q05；signal=系统；status=paid_or_progressed；expected_next_handling=本集兑现/推进
- question_id=Q06；signal=系统；status=paid_or_progressed；expected_next_handling=本集兑现/推进
- question_id=Q07；signal=系统；status=paid_or_progressed；expected_next_handling=本集兑现/推进
- question_id=Q08；signal=系统；status=paid_or_progressed；expected_next_handling=本集兑现/推进
- question_id=Q09；signal=为什么；status=paid_or_progressed；expected_next_handling=本集兑现/推进
- question_id=Q10；signal=为什么；status=paid_or_progressed；expected_next_handling=本集兑现/推进
- question_id=Q11；signal=为什么；status=paid_or_progressed；expected_next_handling=本集兑现/推进
- question_id=Q12；signal=系统；status=paid_or_progressed；expected_next_handling=本集兑现/推进
- question_id=Q13；signal=系统；status=paid_or_progressed；expected_next_handling=本集兑现/推进
- question_id=Q14；signal=为何；status=paid_or_progressed；expected_next_handling=本集兑现/推进
- question_id=Q15；signal=系统；status=paid_or_progressed；expected_next_handling=本集兑现/推进
- question_id=Q16；signal=系统；status=paid_or_progressed；expected_next_handling=本集兑现/推进

## Clip 01（时长 9.236s · EP01_CLIP01 · 死人堆惊醒）　**节奏**：铺垫·长镜　**张力**：紧张
**剧本可看性合同**：clip_id=EP01_CLIP01；dramatic_function=冷开场建立“尸场醒来”的生死危机，把观众立即拉进主角无助处境。；audience_effect=静音也能读懂她刚穿越就落入死局，产生“她怎么活”的第一问题。；spectacle_story_function=无。

**首帧**：`出图/第1集/图片/Clip01_first.png`
**锚帧1**（3.0s · qc）：`出图/第1集/图片/Clip01_mid.png`
**尾帧**：`出图/第1集/图片/Clip01_end.png`
**场景**：LOC_01 荒野尸骸战场/冷灰夜/外；资产：LOC_01
**导演意图**：屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在ECU→ELS/LS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：姜月初从近前尸骸扫向画右远景巨岩。
**表演节拍**：[0-2.0s] 姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。; [2.0-4.0s] dialogue_shot_reverse; [4.0-6s] 姜月初坐在尸堆边，抬头望向远处巨岩黑影。
**运动精修**：幅度=小/中; 能量=紧张; 身体守卫=重心、手部归属、遮挡层级、脸部轮廓和发髻稳定；张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。
**专项镜头模板**：template_id=无; 无
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; risk_flags=identity_escalated,native_multiframe,seam_relay; policy_resolution.winner=identity_affinity; degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "lipsync_condition_only", "requires_voice_track": false, "speech_policy": "no_native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "voice_conditioned_lipsync", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01"], "characters": [{"binding": "native_identity_lock_required", "character_id": "CHAR_01", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。
**角色身份注册层**：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。 → 止：姜月初坐在尸堆边，抬头望向远处巨岩黑影。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=配音仅可作为口型条件输入，模型音频不进成片。禁止模型生成台词、旁白、哼唱或环境人声。
**在场链约束**：required_presence=['CHAR_01', '尸骸前景', '荒野尸场']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。
- 出点：姜月初坐在尸堆边，抬头望向远处巨岩黑影。
- 转场：eyeline
- 连贯性：eyeline=姜月初从近前尸骸扫向画右远景巨岩。; shot_size=ECU→ELS/LS; need_endframe=True

**continuity**：
- start_state：姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。
- action：dialogue_shot_reverse
- end_state：姜月初坐在尸堆边，抬头望向远处巨岩黑影。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01；保持 CHAR_01 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。
  action: dialogue_shot_reverse
  end_state: 姜月初坐在尸堆边，抬头望向远处巨岩黑影。
  constraints: 保持 LOC_01、LOC_01、CHAR_01 的视觉连续；轴线=姜月初从近前尸骸扫向画右远景巨岩。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在ECU→ELS/LS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：姜月初从近前尸骸扫向画右远景巨岩。;
表演节拍：[0-2.0s] 姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。; [2.0-4.0s] dialogue_shot_reverse; [4.0-6s] 姜月初坐在尸堆边，抬头望向远处巨岩黑影。;
运动精修约束：幅度小到中，能量=紧张，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：无。;
专项模板约束：template_id=无，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; prompt 只使用 primary_backend 真实支持的能力，失败按 degrade_plan/fallback 执行;
物理交互约束：无。; FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败;
身份锁定约束：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。 → 止：姜月初坐在尸堆边，抬头望向远处巨岩黑影。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01', '尸骸前景', '荒野尸场']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；若 route.native_audio_policy=lipsync_condition_only，只把配音轨当口型条件，不保留模型音频；禁止原生人声、台词、旁白、哼唱和字幕文字。;
人物运动：dialogue_shot_reverse；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：固定机位，锁定屏幕/光幕平面，不漂移，只允许轻微呼吸式微动;
情绪节奏：[0-终点] 姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。 -> 姜月初坐在尸堆边，抬头望向远处巨岩黑影。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按eyeline服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: 屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。;
opening frame state: 姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。;
ending frame state: 姜月初坐在尸堆边，抬头望向远处巨岩黑影。;
blocking: 姜月初从近前尸骸扫向画右远景巨岩。;
performance beats: [0-2.0s] 姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。; [2.0-4.0s] dialogue_shot_reverse; [4.0-6s] 姜月初坐在尸堆边，抬头望向远处巨岩黑影。;
motion refinement: amplitude=low-to-medium, energy follows tension, anatomy_guard=stable center of gravity, clear hand/weapon ownership, no face stretching;
ambient interaction: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
close-up identity lock: use face close-up / expression references / reference_group first; lock face not emotion, keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01', '尸骸前景', '荒野尸场']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: dialogue_shot_reverse;
camera motion: 固定机位，锁定屏幕/光幕平面，不漂移，只允许轻微呼吸式微动; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative; audio constraint: 禁止后端生成台词；配音仅作口型条件，声源归属=画内说话主体，compose_policy=丢弃模型音轨；旁白与屏幕文字只交 n2d-compose，不生成旁白音频，不渲染字幕。
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=voice_conditioned_lipsync; quality_tier=high; duration=9.236s; aspect=9:16; native_audio_policy=lipsync_condition_only; identity adapter=native_identity_lock_required; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全
5. ✅ ②镜头运动：推/拉/跟/固定/轻震等词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：CHAR_01/囚犯初醒态、CHAR_02/濒死战损态、CHAR_03/诈死复苏态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; risk=low; speech_policy=no_native_speech; compose_policy=丢弃模型音轨; review=确认无原生人声/旁白/哼唱；lipsync_condition_only 仅作口型条件，不保留模型音频。
14. ✅ Motion Control：本镜不要求控制资产

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃。
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_01_死人堆惊醒.mp4` ｜ 进废料重跑 ｜ 改 prompt/拆 Clip 后重跑

### 保真实现分解方案
- 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

## Clip 02（时长 16.57s · EP01_CLIP02 · 看见虎妖尸身）　**节奏**：铺垫·长镜　**张力**：克制
**剧本可看性合同**：clip_id=EP01_CLIP02；dramatic_function=扩大世界观危险：虎首人身妖魔尸身与荒野尸场证明这是妖魔大唐。；audience_effect=观众确认危险不是幻觉，同时被“虎妖真死了吗”悬念牵住。；spectacle_story_function=无。

**首帧**：`出图/第1集/图片/Clip02_first.png`
**锚帧1**（4.0s · split）：`出图/第1集/图片/Clip02_mid.png`
**尾帧**：`出图/第1集/图片/Clip02_end.png`
**场景**：LOC_01 荒野尸骸战场/巨岩方向；资产：LOC_01
**导演意图**：屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在MCU→LS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：姜月初坐在尸堆画左前景，低头看囚服；远处巨岩与虎妖尸身保持画右远景。
**表演节拍**：[0-2.7s] 姜月初坐在尸堆边，抬头望向远处巨岩黑影。; [2.7-5.3s] 确认现代记忆 / 囚服身份落点 / 异界尸场显景; [5.3-8s] 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。
**运动精修**：幅度=小/中; 能量=克制; 身体守卫=重心、手部归属、遮挡层级、脸部轮廓和发髻稳定；张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。
**专项镜头模板**：template_id=realm_portal; {"template_id": "realm_portal", "beats": ["确认现代记忆", "囚服身份落点", "异界尸场显景"], "blocking": "姜月初坐在尸堆画左前景，低头看囚服；远处巨岩与虎妖尸身保持画右远景。", "camera_rule": "先 MCU 锁姜月初囚服与脸，再 eyeline cut 到异界尸场，不做旋涡穿越闪回。", "continuity_must": ["姜月初脸和囚服连续", "源世界只用旁白确认不出画面", "落点固定为大唐荒野尸骸战场", "虎妖诈死态金眼不亮"], "negative": ["不要中途换脸换衣", "不要把尸场变成现代房间", "不要出现传送门实体", "不要提前触发百妖谱规则视觉"], "portal_lock": "无可见传送门；采用记忆断裂式魂穿，入口只存在于旁白时间差。", "source_world_anchor": "二十一世纪普通人、三分钟前仍在现代生活；不出画面，只作为旁白记忆锚。", "destination_anchor": "大唐荒野尸骸战场，冷灰月光，囚服尸骸、巨岩、虎妖尸身三点锁位。", "entry_exit_path": "她已在尸堆中醒来，镜头只呈现落地后的低头认知与抬眼显景。", "body_continuity_lock": "CHAR_01 统一使用囚犯初醒态，脸型发式不变，只有表情从惊疑到恐惧。", "transition_vfx": "无旋涡；用低频心跳、短促耳鸣和冷灰风声表现穿越断片。", "readability_beats": ["低头看囚服", "旁白给出现代到大唐落差", "远景显出虎妖尸身"], "degrade_plan": "若一镜内认知和显景不稳，拆成囚服特写、尸场全景、虎妖尸身远景三张锚帧。"}
**模型路由**：shot_type=realm_portal; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; risk_flags=duration_segment_relay,identity_drift_risk,identity_escalated,native_multiframe,readability_hold_required,seam_relay,vfx_consistency_risk; policy_resolution.winner=identity_affinity; degrade_plan=Split into setup plate, activation/impact insert, and result/reaction; keep VFX shape from shared assets or overlay geometry.; duration_segment_relay=required; segments=Clip_02_seg01(0.0-4.0s first_frame->mid_anchor_1),Clip_02_seg02(4.0-16.57s mid_anchor_1->end_frame)
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "none", "requires_voice_track": false, "speech_policy": "no_native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "Split into setup plate, activation/impact insert, and result/reaction; keep VFX shape from shared assets or overlay geometry.", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01"], "characters": [{"binding": "native_identity_lock_required", "character_id": "CHAR_01", "form": ""}, {"binding": "native_identity_lock_required", "character_id": "CHAR_03", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime", "video_segments": {"max_clip_seconds": 15, "max_segment_seconds": 12.57, "mode": "first_last_relay", "reason": "split paid generation into first/mid/end relay segments under backend cap", "required": true, "segments": [{"duration_sec": 4.0, "end_sec": 4.0, "from_frame": "first_frame", "segment_id": "Clip_02_seg01", "start_sec": 0.0, "submit_mode": "first_last_relay", "to_frame": "mid_anchor_1"}, {"duration_sec": 12.57, "end_sec": 16.57, "from_frame": "mid_anchor_1", "segment_id": "Clip_02_seg02", "start_sec": 4.0, "submit_mode": "first_last_relay", "to_frame": "end_frame"}]}}
**Motion Control / 物理交互控制**：无。
**角色身份注册层**：CHAR_01/囚犯初醒态; identity_requirement=face_lock_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_03/诈死复苏态; identity_requirement=face_lock_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：姜月初坐在尸堆边，抬头望向远处巨岩黑影。 → 止：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=静音图生视频。禁止模型生成台词、旁白、哼唱或环境人声。
**在场链约束**：required_presence=['CHAR_01', 'CHAR_03', '巨岩', '黑色妖血']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：姜月初坐在尸堆边，抬头望向远处巨岩黑影。
- 出点：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。
- 转场：j_cut
- 连贯性：eyeline=姜月初视线由自己囚服转向画右远景虎妖尸身，再转向裴长青。; shot_size=MCU→LS; need_endframe=True

**continuity**：
- start_state：姜月初坐在尸堆边，抬头望向远处巨岩黑影。
- action：确认现代记忆；囚服身份落点；异界尸场显景
- end_state：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01；保持 CHAR_01, CHAR_03 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 姜月初坐在尸堆边，抬头望向远处巨岩黑影。
  action: 确认现代记忆；囚服身份落点；异界尸场显景
  end_state: 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。
  constraints: 保持 LOC_01、LOC_01、CHAR_01, CHAR_03 的视觉连续；轴线=姜月初视线由自己囚服转向画右远景虎妖尸身，再转向裴长青。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在MCU→LS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：姜月初坐在尸堆画左前景，低头看囚服；远处巨岩与虎妖尸身保持画右远景。;
表演节拍：[0-2.7s] 姜月初坐在尸堆边，抬头望向远处巨岩黑影。; [2.7-5.3s] 确认现代记忆 / 囚服身份落点 / 异界尸场显景; [5.3-8s] 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。;
运动精修约束：幅度小到中，能量=克制，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：无。;
专项模板约束：template_id=realm_portal，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=realm_portal; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; prompt 只使用 primary_backend 真实支持的能力，失败按 degrade_plan/fallback 执行；长镜必须按 duration_segment_relay 分段提交，不得单次提交整镜;
物理交互约束：无。; FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败;
身份锁定约束：CHAR_01/囚犯初醒态; identity_requirement=face_lock_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_03/诈死复苏态; identity_requirement=face_lock_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：姜月初坐在尸堆边，抬头望向远处巨岩黑影。 → 止：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01', 'CHAR_03', '巨岩', '黑色妖血']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；禁止原生人声、台词、旁白、哼唱和字幕文字。;
人物运动：确认现代记忆；囚服身份落点；异界尸场显景；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：固定机位，锁定屏幕/光幕平面，不漂移，只允许轻微呼吸式微动;
情绪节奏：[0-终点] 姜月初坐在尸堆边，抬头望向远处巨岩黑影。 -> 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按j_cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: 屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。;
opening frame state: 姜月初坐在尸堆边，抬头望向远处巨岩黑影。;
ending frame state: 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。;
blocking: 姜月初坐在尸堆画左前景，低头看囚服；远处巨岩与虎妖尸身保持画右远景。;
performance beats: [0-2.7s] 姜月初坐在尸堆边，抬头望向远处巨岩黑影。; [2.7-5.3s] 确认现代记忆 / 囚服身份落点 / 异界尸场显景; [5.3-8s] 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。;
motion refinement: amplitude=low-to-medium, energy follows tension, anatomy_guard=stable center of gravity, clear hand/weapon ownership, no face stretching;
ambient interaction: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
close-up identity lock: use face close-up / expression references / reference_group first; lock face not emotion, keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01', 'CHAR_03', '巨岩', '黑色妖血']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 确认现代记忆; 囚服身份落点; 异界尸场显景;
camera motion: 固定机位，锁定屏幕/光幕平面，不漂移，只允许轻微呼吸式微动; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative; audio constraint: 默认禁止原生人声：无对白、无旁白、不要生成原生人声；只允许静默画面，若平台强出声音也由 compose 丢弃。
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=image2video; quality_tier=high; duration=16.57s; aspect=9:16; native_audio_policy=none; identity adapter=native_identity_lock_required; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全
5. ✅ ②镜头运动：推/拉/跟/固定/轻震等词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：CHAR_01/囚犯初醒态、CHAR_02/濒死战损态、CHAR_03/诈死复苏态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; risk=low; speech_policy=no_native_speech; compose_policy=丢弃模型音轨; review=确认无原生人声/旁白/哼唱；lipsync_condition_only 仅作口型条件，不保留模型音频。
14. ✅ Motion Control：本镜不要求控制资产

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃。
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_02_看见虎妖尸身.mp4` ｜ 进废料重跑 ｜ 改 prompt/拆 Clip 后重跑

### 保真实现分解方案
- 若一镜内认知和显景不稳，拆成囚服特写、尸场全景、虎妖尸身远景三张锚帧。

## Clip 03（时长 18.752s · EP01_CLIP03 · 镇魔司压迫交易）　**节奏**：加速·碎切　**张力**：爆发
**剧本可看性合同**：clip_id=EP01_CLIP03；dramatic_function=让裴长青以威胁和交易介入，给姜月初一个不可信但暂时可走的生路。；audience_effect=观众感到她被官差和身份双重压迫，理解她没有轻松逃跑选项。；spectacle_story_function=无。

**首帧**：`出图/第1集/图片/Clip03_first.png`
**锚帧1**（4.0s · split）：`出图/第1集/图片/Clip03_mid.png`
**尾帧**：`出图/第1集/图片/Clip03_end.png`
**场景**：LOC_01 荒野尸骸战场/裴长青半跪处；资产：LOC_01, 断刀
**导演意图**：大表情近景最怕脸被运动重画；轻微推近比环绕/甩镜更稳，也能把情绪怼近。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在CU/MCU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：姜月初画左前景，裴长青画右近中景半跪；断刀钉在二人之间偏画左。
**表演节拍**：[0-3.7s] 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。; [3.7-7.3s] 裴长青沙哑命令 / 姜月初后退反问 / 断刀钉地威胁 / 裴长青报镇魔司身份提出交易; [7.3-11s] 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。
**运动精修**：幅度=小/中; 能量=爆发; 身体守卫=重心、手部归属、遮挡层级、脸部轮廓和发髻稳定；张力=爆发；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。
**专项镜头模板**：template_id=dialogue_shot_reverse; {"template_id": "dialogue_shot_reverse", "beats": ["裴长青沙哑命令", "姜月初后退反问", "断刀钉地威胁", "裴长青报镇魔司身份提出交易"], "blocking": "姜月初画左前景，裴长青画右近中景半跪；断刀钉在二人之间偏画左。", "camera_rule": "正反打守姜月初↔裴长青横轴，过肩只从姜月初肩后向画右拍。", "continuity_must": ["姜月初画左", "裴长青画右", "裴左臂重伤不复原", "断刀落点不漂"], "negative": ["不要跳轴", "不要交换左右站位", "不要新增镇魔司活人", "不要让裴长青突然站稳"], "axis": "姜月初↔裴长青横轴", "eyeline": "姜月初看画右裴长青，裴长青看画左姜月初", "shot_pairing": "姜月初戒备 MCU / 裴长青惨白 CU / 断刀脚边插入特写"}
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; risk_flags=duration_segment_relay,identity_escalated,mouth_visible,native_multiframe,seam_relay; policy_resolution.winner=identity_affinity; degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。; duration_segment_relay=required; segments=Clip_03_seg01(0.0-4.0s first_frame->mid_anchor_1),Clip_03_seg02(4.0-18.752s mid_anchor_1->end_frame)
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "lipsync_condition_only", "requires_voice_track": false, "speech_policy": "no_native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "voice_conditioned_lipsync", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01"], "characters": [{"binding": "native_identity_lock_required", "character_id": "CHAR_01", "form": ""}, {"binding": "native_identity_lock_required", "character_id": "CHAR_02", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime", "video_segments": {"max_clip_seconds": 15, "max_segment_seconds": 14.752, "mode": "first_last_relay", "reason": "split paid generation into first/mid/end relay segments under backend cap", "required": true, "segments": [{"duration_sec": 4.0, "end_sec": 4.0, "from_frame": "first_frame", "segment_id": "Clip_03_seg01", "start_sec": 0.0, "submit_mode": "first_last_relay", "to_frame": "mid_anchor_1"}, {"duration_sec": 14.752, "end_sec": 18.752, "from_frame": "mid_anchor_1", "segment_id": "Clip_03_seg02", "start_sec": 4.0, "submit_mode": "first_last_relay", "to_frame": "end_frame"}]}}
**Motion Control / 物理交互控制**：无。
**角色身份注册层**：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。 → 止：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=配音仅可作为口型条件输入，模型音频不进成片。禁止模型生成台词、旁白、哼唱或环境人声。
**在场链约束**：required_presence=['CHAR_01', 'CHAR_02', '断刀']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。
- 出点：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。
- 转场：action_cut
- 连贯性：eyeline=姜月初看画右裴长青，裴长青看画左姜月初。; shot_size=CU/MS 正反打; need_endframe=True

**continuity**：
- start_state：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。
- action：裴长青沙哑命令；姜月初后退反问；断刀钉地威胁；裴长青报镇魔司身份提出交易
- end_state：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, 断刀；保持 CHAR_01, CHAR_02 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。
  action: 裴长青沙哑命令；姜月初后退反问；断刀钉地威胁；裴长青报镇魔司身份提出交易
  end_state: 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。
  constraints: 保持 LOC_01、LOC_01, 断刀、CHAR_01, CHAR_02 的视觉连续；轴线=姜月初看画右裴长青，裴长青看画左姜月初。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：大表情近景最怕脸被运动重画；轻微推近比环绕/甩镜更稳，也能把情绪怼近。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在CU/MCU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：姜月初画左前景，裴长青画右近中景半跪；断刀钉在二人之间偏画左。;
表演节拍：[0-3.7s] 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。; [3.7-7.3s] 裴长青沙哑命令 / 姜月初后退反问 / 断刀钉地威胁 / 裴长青报镇魔司身份提出交易; [7.3-11s] 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。;
运动精修约束：幅度小到中，能量=爆发，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：无。;
专项模板约束：template_id=dialogue_shot_reverse，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; prompt 只使用 primary_backend 真实支持的能力，失败按 degrade_plan/fallback 执行；长镜必须按 duration_segment_relay 分段提交，不得单次提交整镜;
物理交互约束：无。; FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败;
身份锁定约束：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。 → 止：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01', 'CHAR_02', '断刀']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；若 route.native_audio_policy=lipsync_condition_only，只把配音轨当口型条件，不保留模型音频；禁止原生人声、台词、旁白、哼唱和字幕文字。;
人物运动：裴长青沙哑命令；姜月初后退反问；断刀钉地威胁；裴长青报镇魔司身份提出交易；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：轻微推镜头，沿视线轴轻推，最后稳定停住，落到CU/MCU;
情绪节奏：[0-终点] 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。 -> 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按action_cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: 大表情近景最怕脸被运动重画；轻微推近比环绕/甩镜更稳，也能把情绪怼近。;
opening frame state: 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。;
ending frame state: 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。;
blocking: 姜月初画左前景，裴长青画右近中景半跪；断刀钉在二人之间偏画左。;
performance beats: [0-3.7s] 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。; [3.7-7.3s] 裴长青沙哑命令 / 姜月初后退反问 / 断刀钉地威胁 / 裴长青报镇魔司身份提出交易; [7.3-11s] 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。;
motion refinement: amplitude=low-to-medium, energy follows tension, anatomy_guard=stable center of gravity, clear hand/weapon ownership, no face stretching;
ambient interaction: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
close-up identity lock: use face close-up / expression references / reference_group first; lock face not emotion, keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01', 'CHAR_02', '断刀']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 裴长青沙哑命令; 姜月初后退反问; 断刀钉地威胁; 裴长青报镇魔司身份提出交易;
camera motion: 轻微推镜头，沿视线轴轻推，最后稳定停住，落到CU/MCU; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative; audio constraint: 禁止后端生成台词；配音仅作口型条件，声源归属=画内说话主体，compose_policy=丢弃模型音轨；旁白与屏幕文字只交 n2d-compose，不生成旁白音频，不渲染字幕。
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=voice_conditioned_lipsync; quality_tier=high; duration=18.752s; aspect=9:16; native_audio_policy=lipsync_condition_only; identity adapter=native_identity_lock_required; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全
5. ✅ ②镜头运动：推/拉/跟/固定/轻震等词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：CHAR_01/囚犯初醒态、CHAR_02/濒死战损态、CHAR_03/诈死复苏态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; risk=low; speech_policy=no_native_speech; compose_policy=丢弃模型音轨; review=确认无原生人声/旁白/哼唱；lipsync_condition_only 仅作口型条件，不保留模型音频。
14. ✅ Motion Control：本镜不要求控制资产

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃。
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_03_镇魔司压迫交易.mp4` ｜ 进废料重跑 ｜ 改 prompt/拆 Clip 后重跑

### 保真实现分解方案
- 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

## Clip 04（时长 10.01s · EP01_CLIP04 · 被迫扶裴南行）　**节奏**：铺垫·长镜　**张力**：紧张
**剧本可看性合同**：clip_id=EP01_CLIP04；dramatic_function=用搀扶南行让姜月初暂时接受交易，并把人物位置推进到虎妖复苏前一刻。；audience_effect=观众获得短暂缓和后立刻等待背后异响的反扑。；spectacle_story_function=无。

**首帧**：`出图/第1集/图片/Clip04_first.png`
**锚帧1**（4.0s · split）：`出图/第1集/图片/Clip04_mid.png`
**尾帧**：`出图/第1集/图片/Clip04_end.png`
**场景**：LOC_01 荒野尸骸战场/南向逃路线；资产：LOC_01
**导演意图**：定场镜用升降建立地理和权力关系，不抢人物表演。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在LS/ELS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：CHAR_01 在 LEFT_SLOT 承重前行，CHAR_02 在 RIGHT_LOW_SLOT 半倒压肩；画右远景虎妖仍保持诈死地标。
**表演节拍**：[0-2.7s] 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。; [2.7-5.3s] 姜月初伸手扶起裴长青 / 二人沿南向逃路线踉跄移动 / 湿咳声打断逃跑; [5.3-8s] 二人刚走出几步，身后传来湿咳声。
**运动精修**：幅度=小/中; 能量=紧张; 身体守卫=重心、手部归属、遮挡层级、脸部轮廓和发髻稳定；张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。
**专项镜头模板**：template_id=multi_character_same_frame; {"template_id": "multi_character_same_frame", "beats": ["姜月初伸手扶起裴长青", "二人沿南向逃路线踉跄移动", "湿咳声打断逃跑"], "blocking": "CHAR_01 在 LEFT_SLOT 承重前行，CHAR_02 在 RIGHT_LOW_SLOT 半倒压肩；画右远景虎妖仍保持诈死地标。", "camera_rule": "MS 跟拍到 LS 留空间，清晰双脸同框不稳时按 character_slots 分层合成。", "continuity_must": ["CHAR_01 画左前景", "CHAR_02 重伤压肩且左臂扭曲", "南向移动方向保持画左", "虎妖不提前复苏"], "negative": ["不要让裴长青突然站稳", "不要交换左右站位", "不要新增第三个清晰人脸", "不要让虎妖金眼提前亮起"], "character_slots": [{"slot": "LEFT_SLOT", "character_id": "CHAR_01", "screen_position": "画左前景/近景主检脸，囚犯初醒态或百妖谱触发态", "face_priority": "主检"}, {"slot": "RIGHT_LOW_SLOT", "character_id": "CHAR_02", "screen_position": "画右下/近中景半跪或倒地，黑衣赤纹战损，左臂扭曲", "face_priority": "次检"}], "face_priority": ["CHAR_01"], "overlap_rules": ["CHAR_01 肩部可被 CHAR_02 手臂压住，但主检脸不可遮挡", "CHAR_02 可半侧脸/低头，不得恢复站立", "虎妖只作远景地标，不给清晰第三张脸"]}
**模型路由**：shot_type=multi_character_same_frame; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; risk_flags=identity_drift_risk,identity_escalated,mouth_visible,multi_person,native_multiframe,seam_relay; policy_resolution.winner=identity_affinity; degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "lipsync_condition_only", "requires_voice_track": false, "speech_policy": "no_native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第1集/control/Clip_04/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "voice_conditioned_lipsync", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01"], "characters": [{"binding": "native_identity_lock_required", "character_id": "CHAR_01", "form": ""}, {"binding": "native_identity_lock_required", "character_id": "CHAR_02", "form": ""}], "identity_preservation_plan": {"applies_to": "multi_character_same_frame", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "native_identity_lock_required", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：level=required; manifest_path=出视频/第1集/control/Clip_04/motion_control_manifest.json; required_inputs=pose_sequence,depth_sequence,instance_masks; failure_modes=slot_drift,pose_drift,identity_drift; status=ready 或 degrade_only；若无 pose/depth/instance/contact/camera_path，则执行保真实现分解，不直接生成全身复杂接触或长连续高速动作。
**角色身份注册层**：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。 → 止：二人刚走出几步，身后传来湿咳声。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=配音仅可作为口型条件输入，模型音频不进成片。禁止模型生成台词、旁白、哼唱或环境人声。
**在场链约束**：required_presence=['CHAR_01', 'CHAR_02']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。
- 出点：二人刚走出几步，身后传来湿咳声。
- 转场：j_cut
- 连贯性：eyeline=姜月初看向南向逃路，偶尔回头警惕虎妖方向。; shot_size=MS→LS; need_endframe=True

**continuity**：
- start_state：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。
- action：姜月初伸手扶起裴长青；二人沿南向逃路线踉跄移动；湿咳声打断逃跑
- end_state：二人刚走出几步，身后传来湿咳声。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01；保持 CHAR_01, CHAR_02 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。
  action: 姜月初伸手扶起裴长青；二人沿南向逃路线踉跄移动；湿咳声打断逃跑
  end_state: 二人刚走出几步，身后传来湿咳声。
  constraints: 保持 LOC_01、LOC_01、CHAR_01, CHAR_02 的视觉连续；轴线=姜月初看向南向逃路，偶尔回头警惕虎妖方向。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：定场镜用升降建立地理和权力关系，不抢人物表演。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在LS/ELS，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：CHAR_01 在 LEFT_SLOT 承重前行，CHAR_02 在 RIGHT_LOW_SLOT 半倒压肩；画右远景虎妖仍保持诈死地标。;
表演节拍：[0-2.7s] 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。; [2.7-5.3s] 姜月初伸手扶起裴长青 / 二人沿南向逃路线踉跄移动 / 湿咳声打断逃跑; [5.3-8s] 二人刚走出几步，身后传来湿咳声。;
运动精修约束：幅度小到中，能量=紧张，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：无。;
专项模板约束：template_id=multi_character_same_frame，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=multi_character_same_frame; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; prompt 只使用 primary_backend 真实支持的能力，失败按 degrade_plan/fallback 执行;
物理交互约束：level=required; manifest_path=出视频/第1集/control/Clip_04/motion_control_manifest.json; required_inputs=pose_sequence,depth_sequence,instance_masks; failure_modes=slot_drift,pose_drift,identity_drift; status=ready 或 degrade_only；若无 pose/depth/instance/contact/camera_path，则执行保真实现分解，不直接生成全身复杂接触或长连续高速动作。; FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败;
身份锁定约束：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。 → 止：二人刚走出几步，身后传来湿咳声。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01', 'CHAR_02']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；若 route.native_audio_policy=lipsync_condition_only，只把配音轨当口型条件，不保留模型音频；禁止原生人声、台词、旁白、哼唱和字幕文字。;
人物运动：姜月初伸手扶起裴长青；二人沿南向逃路线踉跄移动；湿咳声打断逃跑；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：缓慢升降，轻微上升/下降揭示空间层次，落到LS/ELS;
情绪节奏：[0-终点] 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。 -> 二人刚走出几步，身后传来湿咳声。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按j_cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: 定场镜用升降建立地理和权力关系，不抢人物表演。;
opening frame state: 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。;
ending frame state: 二人刚走出几步，身后传来湿咳声。;
blocking: CHAR_01 在 LEFT_SLOT 承重前行，CHAR_02 在 RIGHT_LOW_SLOT 半倒压肩；画右远景虎妖仍保持诈死地标。;
performance beats: [0-2.7s] 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。; [2.7-5.3s] 姜月初伸手扶起裴长青 / 二人沿南向逃路线踉跄移动 / 湿咳声打断逃跑; [5.3-8s] 二人刚走出几步，身后传来湿咳声。;
motion refinement: amplitude=low-to-medium, energy follows tension, anatomy_guard=stable center of gravity, clear hand/weapon ownership, no face stretching;
ambient interaction: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
close-up identity lock: use face close-up / expression references / reference_group first; lock face not emotion, keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01', 'CHAR_02']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 姜月初伸手扶起裴长青; 二人沿南向逃路线踉跄移动; 湿咳声打断逃跑;
camera motion: 缓慢升降，轻微上升/下降揭示空间层次，落到LS/ELS; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative; audio constraint: 禁止后端生成台词；配音仅作口型条件，声源归属=画内说话主体，compose_policy=丢弃模型音轨；旁白与屏幕文字只交 n2d-compose，不生成旁白音频，不渲染字幕。
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=voice_conditioned_lipsync; quality_tier=high; duration=10.01s; aspect=9:16; native_audio_policy=lipsync_condition_only; identity adapter=native_identity_lock_required; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全
5. ✅ ②镜头运动：推/拉/跟/固定/轻震等词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：CHAR_01/囚犯初醒态、CHAR_02/濒死战损态、CHAR_03/诈死复苏态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; risk=low; speech_policy=no_native_speech; compose_policy=丢弃模型音轨; review=确认无原生人声/旁白/哼唱；lipsync_condition_only 仅作口型条件，不保留模型音频。
14. ✅ Motion Control：已继承 level/manifest_path/required_inputs/failure_modes；无控制资产时按 degrade_only 保真实现分解，不靠文本硬扛

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃。
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜
- [ ] Motion Control：检查 FeatureMelting/特征融化、limb_fusion、weapon_contact_drift、slot_drift；若失败按 degrade_only 拆为手部/反打/释放帧。
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_04_被迫扶裴南行.mp4` ｜ 进废料重跑 ｜ 改 prompt/拆 Clip 后重跑

### 保真实现分解方案
- 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

## Clip 05（时长 12.995s · EP01_CLIP05 · 虎妖诈死复苏）　**节奏**：揭示·反应链　**张力**：爆发
**剧本可看性合同**：clip_id=EP01_CLIP05；dramatic_function=反转虎妖未死，推翻“尸体安全”的判断，把逃生计划打碎。；audience_effect=观众从安全误判跌回绝境，期待裴长青如何解释或抵抗。；spectacle_story_function=虎妖金眼复亮和胸口黑血洞服务“妖物杀不死”的剧情反转，而不是单纯怪物展示。。

**首帧**：`出图/第1集/图片/Clip05_first.png`
**锚帧1**（4.0s · split）：`出图/第1集/图片/Clip05_mid.png`
**尾帧**：`出图/第1集/图片/Clip05_end.png`
**场景**：LOC_01 荒野尸骸战场/巨岩复苏点；资产：LOC_01, VFX_虎山神摹影
**导演意图**：大表情近景最怕脸被运动重画；轻微推近比环绕/甩镜更稳，也能把情绪怼近。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在CU/MCU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：虎山神画右远景巨岩处站起，姜月初和裴长青画左前景被迫回头。
**表演节拍**：[0-3.0s] 二人刚走出几步，身后传来湿咳声。; [3.0-6.0s] 湿咳声打断逃跑 / 虎妖从尸身复苏 / 虎妖开口拦路 / 裴长青确认不可能; [6.0-9s] 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。
**运动精修**：幅度=小/中; 能量=爆发; 身体守卫=重心、手部归属、遮挡层级、脸部轮廓和发髻稳定；张力=爆发；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。
**专项镜头模板**：template_id=reveal_reaction_chain; {"template_id": "reveal_reaction_chain", "beats": ["湿咳声打断逃跑", "虎妖从尸身复苏", "虎妖开口拦路", "裴长青确认不可能"], "blocking": "虎山神画右远景巨岩处站起，姜月初和裴长青画左前景被迫回头。", "camera_rule": "先给姜月初/裴长青反应CU，再低机位拍虎妖复苏，最后反打裴长青骇然。", "continuity_must": ["虎妖胸口黑血窟窿保持", "虎妖从巨岩处起身不瞬移", "裴长青摔在姜月初近旁"], "negative": ["不要让虎妖伤口消失", "不要新增妖群", "不要把黑血做成猎奇特写", "不要让裴长青恢复站立"], "reveal_object": "虎山神诈死复苏态与胸口黑血窟窿", "knowledge_order": ["观众先听湿咳", "姜月初和裴长青同时意识到虎妖未死", "裴长青最后说出斩穿心脏仍不死的反常"], "reaction_beats": ["姜月初手松", "裴长青摔地", "裴长青血色尽褪"], "cut_point": "虎妖金黄凶眼亮起并咧嘴拦路"}
**模型路由**：shot_type=reveal_reaction_chain; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; risk_flags=identity_drift_risk,identity_escalated,mouth_visible,native_multiframe,seam_relay; policy_resolution.winner=identity_affinity; degrade_plan=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "none", "requires_voice_track": false, "speech_policy": "no_native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01"], "characters": [{"binding": "native_identity_lock_required", "character_id": "CHAR_01", "form": ""}, {"binding": "native_identity_lock_required", "character_id": "CHAR_02", "form": ""}, {"binding": "native_identity_lock_required", "character_id": "CHAR_03", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。
**角色身份注册层**：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：二人刚走出几步，身后传来湿咳声。 → 止：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=静音图生视频。禁止模型生成台词、旁白、哼唱或环境人声。
**在场链约束**：required_presence=['CHAR_01', 'CHAR_02', 'CHAR_03', 'VFX_虎山神摹影']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：二人刚走出几步，身后传来湿咳声。
- 出点：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。
- 转场：hard_cut
- 连贯性：eyeline=姜月初和裴长青同时回头看画右远景虎妖；虎妖看画左前景二人。; shot_size=CU→LS低机位→CU; need_endframe=True

**continuity**：
- start_state：二人刚走出几步，身后传来湿咳声。
- action：湿咳声打断逃跑；虎妖从尸身复苏；虎妖开口拦路；裴长青确认不可能
- end_state：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, VFX_虎山神摹影；保持 CHAR_01, CHAR_02, CHAR_03 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 二人刚走出几步，身后传来湿咳声。
  action: 湿咳声打断逃跑；虎妖从尸身复苏；虎妖开口拦路；裴长青确认不可能
  end_state: 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。
  constraints: 保持 LOC_01、LOC_01, VFX_虎山神摹影、CHAR_01, CHAR_02, CHAR_03 的视觉连续；轴线=姜月初和裴长青同时回头看画右远景虎妖；虎妖看画左前景二人。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：大表情近景最怕脸被运动重画；轻微推近比环绕/甩镜更稳，也能把情绪怼近。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在CU/MCU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：虎山神画右远景巨岩处站起，姜月初和裴长青画左前景被迫回头。;
表演节拍：[0-3.0s] 二人刚走出几步，身后传来湿咳声。; [3.0-6.0s] 湿咳声打断逃跑 / 虎妖从尸身复苏 / 虎妖开口拦路 / 裴长青确认不可能; [6.0-9s] 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。;
运动精修约束：幅度小到中，能量=爆发，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：无。;
专项模板约束：template_id=reveal_reaction_chain，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=reveal_reaction_chain; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; prompt 只使用 primary_backend 真实支持的能力，失败按 degrade_plan/fallback 执行;
物理交互约束：无。; FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败;
身份锁定约束：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：二人刚走出几步，身后传来湿咳声。 → 止：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01', 'CHAR_02', 'CHAR_03', 'VFX_虎山神摹影']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；禁止原生人声、台词、旁白、哼唱和字幕文字。;
人物运动：湿咳声打断逃跑；虎妖从尸身复苏并开口拦路；裴长青骇然确认不可能；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：轻微推镜头，沿视线轴轻推，最后稳定停住，落到CU/MCU;
情绪节奏：[0-终点] 二人刚走出几步，身后传来湿咳声。 -> 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按hard_cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: 大表情近景最怕脸被运动重画；轻微推近比环绕/甩镜更稳，也能把情绪怼近。;
opening frame state: 二人刚走出几步，身后传来湿咳声。;
ending frame state: 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。;
blocking: 虎山神画右远景巨岩处站起，姜月初和裴长青画左前景被迫回头。;
performance beats: [0-3.0s] 二人刚走出几步，身后传来湿咳声。; [3.0-6.0s] 湿咳声打断逃跑 / 虎妖从尸身复苏 / 虎妖开口拦路 / 裴长青确认不可能; [6.0-9s] 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。;
motion refinement: amplitude=low-to-medium, energy follows tension, anatomy_guard=stable center of gravity, clear hand/weapon ownership, no face stretching;
ambient interaction: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
close-up identity lock: use face close-up / expression references / reference_group first; lock face not emotion, keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01', 'CHAR_02', 'CHAR_03', 'VFX_虎山神摹影']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 湿咳声打断逃跑; 虎妖从尸身复苏; 虎妖开口拦路; 裴长青确认不可能;
camera motion: 轻微推镜头，沿视线轴轻推，最后稳定停住，落到CU/MCU; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative; audio constraint: 默认禁止原生人声：无对白、无旁白、不要生成原生人声；只允许静默画面，若平台强出声音也由 compose 丢弃。
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=image2video; quality_tier=high; duration=12.995s; aspect=9:16; native_audio_policy=none; identity adapter=native_identity_lock_required; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全
5. ✅ ②镜头运动：推/拉/跟/固定/轻震等词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：CHAR_01/囚犯初醒态、CHAR_02/濒死战损态、CHAR_03/诈死复苏态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; risk=low; speech_policy=no_native_speech; compose_policy=丢弃模型音轨; review=确认无原生人声/旁白/哼唱；lipsync_condition_only 仅作口型条件，不保留模型音频。
14. ✅ Motion Control：本镜不要求控制资产

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃。
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_05_虎妖诈死复苏.mp4` ｜ 进废料重跑 ｜ 改 prompt/拆 Clip 后重跑

### 保真实现分解方案
- Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.；若本镜含对白/画内发声，必须走 voice-first 配音补偿链路，或拆出 no_native_speech 说话特写后重跑路由。

## Clip 06（时长 14.586s · EP01_CLIP06 · 裴长青最后一击被踹飞）　**节奏**：加速·碎切　**张力**：爆发
**剧本可看性合同**：clip_id=EP01_CLIP06；dramatic_function=裴长青最后一击失败，证明正面武力路线断绝。；audience_effect=观众看到最强战力被一脚击溃，接受姜月初必须寻找非常规活路。；spectacle_story_function=打斗只保留起手、命中、倒飞三拍，用失败动作证明虎妖等级碾压。。

**首帧**：`出图/第1集/图片/Clip06_first.png`
**锚帧1**（3.0s · split）：`出图/第1集/图片/Clip06_mid.png`
**尾帧**：`出图/第1集/图片/Clip06_end.png`
**场景**：LOC_01 荒野尸骸战场/虎妖攻防轴；资产：LOC_01, WEAPON_01, VFX_虎山神摹影
**导演意图**：大表情近景最怕脸被运动重画；轻微推近比环绕/甩镜更稳，也能把情绪怼近。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在CU/MCU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：裴长青从画左前景扑向画右巨岩处虎妖；虎妖始终画右高位，姜月初在画左前景被迫目击。
**表演节拍**：[0-3.0s] 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。; [3.0-6.0s] 裴长青捡刀起手 / 裴长青合身扑向虎妖 / 虎妖右腿后发先至命中胸口 / 裴长青倒飞砸回姜月初脚边; [6.0-9s] 裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。
**运动精修**：幅度=小/中; 能量=爆发; 身体守卫=重心、手部归属、遮挡层级、脸部轮廓和发髻稳定；张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：{"required": true, "shot_type": "fight_exchange", "beats": ["裴长青捡刀起手", "裴长青合身扑向虎妖", "虎妖右腿后发先至命中胸口", "裴长青倒飞砸回姜月初脚边"], "speed_curve": "裴长青起手慢半拍→扑击快切→命中顿帧0.3s→倒飞落地留0.5s", "spatial_path": "画左前景裴长青沿斜线扑向画右巨岩，命中后抛回画左前景姜月初脚边", "camera_path": "起手固定微推，命中帧短促快推，受击落地低幅震动", "readability_beats": ["起手看清裴已重伤", "命中帧看清虎妖脚掌接触裴胸口", "落地看清裴砸到姜月初脚边"], "degrade_plan": "若双主体接触不稳，拆为裴起手单人镜、虎妖脚掌命中特写、裴倒飞受击反应三段。", "keyframe_plan": {"start": "裴长青捡刀起手", "intent_mid": "裴长青扑向虎妖", "impact_or_apex": "虎妖脚掌命中裴胸口", "result_or_recovery": "裴倒飞砸地", "end": "横刀落在姜月初脚边"}, "post_cue_points": {"pre_peak": "0:45 出刀破风 whoosh", "peak": "5.0s impact 重低音 + 轻震屏 + 2帧hit-stop", "aftershock_or_hold": "0:50 尘土扑面，BGM压低半拍"}, "physics_guard": {"identity_lock": ["CHAR_02", "CHAR_03"], "axis_lock": "画左裴长青 ↔ 画右虎妖，不越轴", "contact_lock": "只允许虎妖右脚掌接触裴胸口", "forbid": ["新增第二击", "裴长青突然恢复健康", "虎妖伤口消失"]}, "attack_path": "裴长青横刀自画左下向画右上斩向虎妖脖颈，虎妖右腿自画右中线蹬向画左前景裴胸口。", "impact_frame": "命中 5.0s：虎妖脚掌命中裴长青胸口，裴身体弓起，尘土和衣摆顺画左方向飞散。", "contact_points": ["虎妖右脚掌", "裴长青胸口"], "force_direction": "虎妖画右→裴长青画左前景，力向右上到左下", "recovery_beat": "裴长青倒地后横刀落在姜月初可触及的位置"}
**专项镜头模板**：template_id=fight_exchange; {"template_id": "fight_exchange", "beats": ["裴长青捡刀起手", "裴长青合身扑向虎妖", "虎妖右腿后发先至命中胸口", "裴长青倒飞砸回姜月初脚边"], "blocking": "裴长青从画左前景扑向画右巨岩处虎妖；虎妖始终画右高位，姜月初在画左前景被迫目击。", "camera_rule": "MS起手→CU命中帧→MS受击落地；不环绕，不越轴，命中帧短促快推。", "continuity_must": ["裴长青黑衣赤纹和左臂重伤保持", "虎妖胸口黑血窟窿保持", "裴从画左扑向画右再被踹回画左"], "negative": ["不要让裴长青飞向错误方向", "不要新增武器", "不要多人混战", "不要看镜头摆拍"], "pose_reference_required": true, "regional_construct_required": true, "attack_path": "裴长青横刀自画左下向画右上斩向虎妖脖颈，虎妖右腿自画右中线蹬向画左前景裴胸口。", "impact_frame": "命中 5.0s：虎妖脚掌命中裴长青胸口，裴身体弓起，尘土和衣摆顺画左方向飞散。", "action_scope": "一击失败，虎妖只做一脚反击，不追加第二动作。", "contact_points": ["虎妖右脚掌", "裴长青胸口"], "force_direction": "虎妖画右→裴长青画左前景，力向右上到左下", "screen_direction": "裴长青画左→画右进攻，被踢回画左", "speed_curve": "裴长青起手慢半拍→扑击快切→命中顿帧0.3s→倒飞落地留0.5s", "spatial_path": "画左前景裴长青沿斜线扑向画右巨岩，命中后抛回画左前景姜月初脚边", "camera_path": "起手固定微推，命中帧短促快推，受击落地低幅震动", "readability_beats": ["起手看清裴已重伤", "命中帧看清虎妖脚掌接触裴胸口", "落地看清裴砸到姜月初脚边"], "recovery_beat": "裴长青倒地后横刀落在姜月初可触及的位置", "degrade_plan": "若双主体接触不稳，拆为裴起手单人镜、虎妖脚掌命中特写、裴倒飞受击反应三段。", "keyframe_plan": {"start": "裴长青捡刀起手", "intent_mid": "裴长青扑向虎妖", "impact_or_apex": "虎妖脚掌命中裴胸口", "result_or_recovery": "裴倒飞砸地", "end": "横刀落在姜月初脚边"}, "post_cue_points": {"pre_peak": "0:45 出刀破风 whoosh", "peak": "5.0s impact 重低音 + 轻震屏 + 2帧hit-stop", "aftershock_or_hold": "0:50 尘土扑面，BGM压低半拍"}, "physics_guard": {"identity_lock": ["CHAR_02", "CHAR_03"], "axis_lock": "画左裴长青 ↔ 画右虎妖，不越轴", "contact_lock": "只允许虎妖右脚掌接触裴胸口", "forbid": ["新增第二击", "裴长青突然恢复健康", "虎妖伤口消失"]}, "interaction_graph": {"participants": ["CHAR_02", "CHAR_03", "WEAPON_01"], "contact_points": [{"source": "CHAR_03.right_foot", "target": "CHAR_02.chest", "frame": "impact_frame"}, {"source": "CHAR_02.right_hand", "target": "WEAPON_01.hilt", "frame": "start_to_impact"}], "body_part_ownership": {"CHAR_03.right_foot": "虎妖右脚掌，命中主体", "CHAR_02.chest": "裴长青胸口，受击主体", "CHAR_02.right_hand": "裴长青持横刀手", "WEAPON_01.hilt": "裴长青持握，命中后脱手"}, "release_frame": "命中后裴长青倒飞落地，右手松开横刀；WEAPON_01 落在姜月初脚边，供 EP01_CLIP08 手摸刀承接。", "transfer_event": "WEAPON_01 从 CHAR_02 持握状态转为落地可拾取状态；不是递交，因受击脱手完成持有因果。", "occlusion_order": ["虎妖右脚掌位于命中接触点最前层", "裴长青胸口和身体弓起为中层", "横刀侧向运动不遮挡脚掌接触点", "姜月初只作前景/侧景目击者，不参与接触"], "force_direction": "虎妖画右高位向画左前景蹬出，力向右上到左下", "motion_vector": "CHAR_02 从画左扑向画右，命中后被反向抛回画左前景"}, "combat_micro_expression": "裴长青咬牙强撑，命中时痛苦瞳孔收缩；虎妖轻蔑无惧。", "secondary_motion": "裴衣摆、尘土和血珠顺画左方向飞出。", "apex_light": "命中瞬间冷灰尘雾被短促边缘光拉出轮廓。"}
**模型路由**：shot_type=fight_exchange; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; risk_flags=action_choreography_required,contact_motion,feature_melting_risk,identity_drift_risk,identity_escalated,motion_reference_candidate,mouth_visible,multi_person,native_multiframe,physical_interaction,seam_relay; policy_resolution.winner=identity_affinity; degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "lipsync_condition_only", "requires_voice_track": false, "speech_policy": "no_native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": true}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第1集/control/Clip_06/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks", "contact_map", "camera_path"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "voice_conditioned_lipsync", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01", "WEAPON_01"], "characters": [{"binding": "native_identity_lock_required", "character_id": "CHAR_01", "form": ""}, {"binding": "native_identity_lock_required", "character_id": "CHAR_02", "form": ""}, {"binding": "native_identity_lock_required", "character_id": "CHAR_03", "form": ""}], "identity_preservation_plan": {"applies_to": "fight_exchange", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "native_identity_lock_required", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": true, "library_path": "生产数据/motion_reference_library.json", "policy": "use same sequence/shot_type approved reference when available"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：level=required; manifest_path=出视频/第1集/control/Clip_06/motion_control_manifest.json; required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path; failure_modes=feature_melting,limb_fusion,weapon_contact_drift,body_interpenetration; status=ready 或 degrade_only；若无 pose/depth/instance/contact/camera_path，则执行保真实现分解，不直接生成全身复杂接触或长连续高速动作。
**角色身份注册层**：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。 → 止：裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=配音仅可作为口型条件输入，模型音频不进成片。禁止模型生成台词、旁白、哼唱或环境人声。
**在场链约束**：required_presence=['CHAR_02', 'CHAR_03', 'WEAPON_01']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。
- 出点：裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。
- 转场：action_cut
- 连贯性：eyeline=裴长青看画右虎妖，虎妖看画左裴长青，姜月初看脚边裴。; shot_size=MS→CU命中→MS; need_endframe=True

**continuity**：
- start_state：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。
- action：裴长青捡刀起手；裴长青合身扑向虎妖；虎妖右腿后发先至命中胸口；裴长青倒飞砸回姜月初脚边
- end_state：裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, WEAPON_01, VFX_虎山神摹影；保持 CHAR_01, CHAR_02, CHAR_03 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。
  action: 裴长青捡刀起手；裴长青合身扑向虎妖；虎妖右腿后发先至命中胸口；裴长青倒飞砸回姜月初脚边
  end_state: 裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。
  constraints: 保持 LOC_01、LOC_01, WEAPON_01, VFX_虎山神摹影、CHAR_01, CHAR_02, CHAR_03 的视觉连续；轴线=裴长青看画右虎妖，虎妖看画左裴长青，姜月初看脚边裴。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：大表情近景最怕脸被运动重画；轻微推近比环绕/甩镜更稳，也能把情绪怼近。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在CU/MCU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：裴长青从画左前景扑向画右巨岩处虎妖；虎妖始终画右高位，姜月初在画左前景被迫目击。;
表演节拍：[0-3.0s] 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。; [3.0-6.0s] 裴长青捡刀起手 / 裴长青合身扑向虎妖 / 虎妖右腿后发先至命中胸口 / 裴长青倒飞砸回姜月初脚边; [6.0-9s] 裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。;
运动精修约束：幅度小到中，能量=爆发，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：{"required": true, "shot_type": "fight_exchange", "beats": ["裴长青捡刀起手", "裴长青合身扑向虎妖", "虎妖右腿后发先至命中胸口", "裴长青倒飞砸回姜月初脚边"], "speed_curve": "裴长青起手慢半拍→扑击快切→命中顿帧0.3s→倒飞落地留0.5s", "spatial_path": "画左前景裴长青沿斜线扑向画右巨岩，命中后抛回画左前景姜月初脚边", "camera_path": "起手固定微推，命中帧短促快推，受击落地低幅震动", "readability_beats": ["起手看清裴已重伤", "命中帧看清虎妖脚掌接触裴胸口", "落地看清裴砸到姜月初脚边"], "degrade_plan": "若双主体接触不稳，拆为裴起手单人镜、虎妖脚掌命中特写、裴倒飞受击反应三段。", "keyframe_plan": {"start": "裴长青捡刀起手", "intent_mid": "裴长青扑向虎妖", "impact_or_apex": "虎妖脚掌命中裴胸口", "result_or_recovery": "裴倒飞砸地", "end": "横刀落在姜月初脚边"}, "post_cue_points": {"pre_peak": "0:45 出刀破风 whoosh", "peak": "5.0s impact 重低音 + 轻震屏 + 2帧hit-stop", "aftershock_or_hold": "0:50 尘土扑面，BGM压低半拍"}, "physics_guard": {"identity_lock": ["CHAR_02", "CHAR_03"], "axis_lock": "画左裴长青 ↔ 画右虎妖，不越轴", "contact_lock": "只允许虎妖右脚掌接触裴胸口", "forbid": ["新增第二击", "裴长青突然恢复健康", "虎妖伤口消失"]}, "attack_path": "裴长青横刀自画左下向画右上斩向虎妖脖颈，虎妖右腿自画右中线蹬向画左前景裴胸口。", "impact_frame": "命中 5.0s：虎妖脚掌命中裴长青胸口，裴身体弓起，尘土和衣摆顺画左方向飞散。", "contact_points": ["虎妖右脚掌", "裴长青胸口"], "force_direction": "虎妖画右→裴长青画左前景，力向右上到左下", "recovery_beat": "裴长青倒地后横刀落在姜月初可触及的位置"};
专项模板约束：template_id=fight_exchange，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=fight_exchange; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; prompt 只使用 primary_backend 真实支持的能力，失败按 degrade_plan/fallback 执行;
物理交互约束：level=required; manifest_path=出视频/第1集/control/Clip_06/motion_control_manifest.json; required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path; failure_modes=feature_melting,limb_fusion,weapon_contact_drift,body_interpenetration; status=ready 或 degrade_only；若无 pose/depth/instance/contact/camera_path，则执行保真实现分解，不直接生成全身复杂接触或长连续高速动作。; FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败;
身份锁定约束：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。 → 止：裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_02', 'CHAR_03', 'WEAPON_01']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；若 route.native_audio_policy=lipsync_condition_only，只把配音轨当口型条件，不保留模型音频；禁止原生人声、台词、旁白、哼唱和字幕文字。;
人物运动：裴长青捡刀起手；裴长青合身扑向虎妖；虎妖右腿后发先至命中胸口；裴长青倒飞砸回姜月初脚边；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：轻微推镜头，沿视线轴轻推，最后稳定停住，落到CU/MCU;
情绪节奏：[0-终点] 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。 -> 裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按action_cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: 大表情近景最怕脸被运动重画；轻微推近比环绕/甩镜更稳，也能把情绪怼近。;
opening frame state: 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。;
ending frame state: 裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。;
blocking: 裴长青从画左前景扑向画右巨岩处虎妖；虎妖始终画右高位，姜月初在画左前景被迫目击。;
performance beats: [0-3.0s] 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。; [3.0-6.0s] 裴长青捡刀起手 / 裴长青合身扑向虎妖 / 虎妖右腿后发先至命中胸口 / 裴长青倒飞砸回姜月初脚边; [6.0-9s] 裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。;
motion refinement: amplitude=low-to-medium, energy follows tension, anatomy_guard=stable center of gravity, clear hand/weapon ownership, no face stretching;
ambient interaction: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
close-up identity lock: use face close-up / expression references / reference_group first; lock face not emotion, keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_02', 'CHAR_03', 'WEAPON_01']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 裴长青捡刀起手; 裴长青合身扑向虎妖; 虎妖右腿后发先至命中胸口; 裴长青倒飞砸回姜月初脚边;
camera motion: 轻微推镜头，沿视线轴轻推，最后稳定停住，落到CU/MCU; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative; audio constraint: 禁止后端生成台词；配音仅作口型条件，声源归属=画内说话主体，compose_policy=丢弃模型音轨；旁白与屏幕文字只交 n2d-compose，不生成旁白音频，不渲染字幕。
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=voice_conditioned_lipsync; quality_tier=high; duration=14.586s; aspect=9:16; native_audio_policy=lipsync_condition_only; identity adapter=native_identity_lock_required; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全
5. ✅ ②镜头运动：推/拉/跟/固定/轻震等词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：CHAR_01/囚犯初醒态、CHAR_02/濒死战损态、CHAR_03/诈死复苏态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; risk=low; speech_policy=no_native_speech; compose_policy=丢弃模型音轨; review=确认无原生人声/旁白/哼唱；lipsync_condition_only 仅作口型条件，不保留模型音频。
14. ✅ Motion Control：已继承 level/manifest_path/required_inputs/failure_modes；无控制资产时按 degrade_only 保真实现分解，不靠文本硬扛

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃。
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜
- [ ] Motion Control：检查 FeatureMelting/特征融化、limb_fusion、weapon_contact_drift、slot_drift；若失败按 degrade_only 拆为手部/反打/释放帧。
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_06_裴长青最后一击被踹飞.mp4` ｜ 进废料重跑 ｜ 改 prompt/拆 Clip 后重跑

### 保真实现分解方案
- 若双主体接触不稳，拆为裴起手单人镜、虎妖脚掌命中特写、裴倒飞受击反应三段。

## Clip 07（时长 11.197s · EP01_CLIP07 · 百妖谱第一次开启）　**节奏**：爽点·CU硬切　**张力**：爆发
**剧本可看性合同**：clip_id=EP01_CLIP07；dramatic_function=百妖谱第一次开启，给主角绝境中的唯一规则性生路。；audience_effect=观众获得金手指爽点，同时立刻想知道规则能否马上救命。；spectacle_story_function=无。

**首帧**：`出图/第1集/图片/Clip07_first.png`
**锚帧1**（3.0s · split）：`出图/第1集/图片/Clip07_mid.png`
**尾帧**：`出图/第1集/图片/Clip07_end.png`
**场景**：LOC_01 荒野尸骸战场/姜月初主观视野；资产：LOC_01, VFX_系统面板, WEAPON_01
**导演意图**：屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在CU→POV，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：面板位于姜月初主观视野中央偏上，姜月初脸部或眼睛作为反应镜。
**表演节拍**：[0-2.7s] 裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。; [2.7-5.3s] 姜月初绝望吐槽 / 金色古卷面板浮现 / 基础属性overlay出现 / 姜月初眼睛被金光照亮; [5.3-8s] 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。
**运动精修**：幅度=小/中; 能量=爆发; 身体守卫=重心、手部归属、遮挡层级、脸部轮廓和发髻稳定；张力=紧张；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。
**专项镜头模板**：template_id=system_panel; {"template_id": "system_panel", "beats": ["姜月初绝望吐槽", "金色古卷面板浮现", "基础属性overlay出现", "姜月初眼睛被金光照亮"], "blocking": "面板位于姜月初主观视野中央偏上，姜月初脸部或眼睛作为反应镜。", "camera_rule": "POV/过肩，面板正对屏幕，不透视变形，不随镜头漂移。", "continuity_must": ["面板金色古卷边框", "内部留空给overlay", "金光只照姜月初眼睛和手部"], "negative": ["不要AI生成可读文字", "不要现代手机UI", "不要蓝色科幻屏", "不要随机数字"], "motif_id": "MOTIF_系统面板", "vfx_asset": "VFX_系统面板", "text_layer": "overlay", "growth_ref": "MOTIF_系统面板.v1.at_EP01_CLIP07", "panel_tier": "v1_素纹古卷", "overlay_lines": ["宿主：姜月初", "境界：凡境", "武学：无", "道行：零"]}
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; risk_flags=identity_escalated,native_multiframe,seam_relay; policy_resolution.winner=identity_affinity; degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "lipsync_condition_only", "requires_voice_track": false, "speech_policy": "no_native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "voice_conditioned_lipsync", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01"], "characters": [{"binding": "native_identity_lock_required", "character_id": "CHAR_01", "form": ""}, {"binding": "native_identity_lock_required", "character_id": "CHAR_02", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。
**角色身份注册层**：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。 → 止：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=配音仅可作为口型条件输入，模型音频不进成片。禁止模型生成台词、旁白、哼唱或环境人声。
**在场链约束**：required_presence=['CHAR_01', 'VFX_系统面板']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。
- 出点：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。
- 转场：match_cut
- 连贯性：eyeline=姜月初先看脚边裴长青，再看眼前金色面板。; shot_size=CU→POV; need_endframe=True

**continuity**：
- start_state：裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。
- action：姜月初绝望吐槽；金色古卷面板浮现；基础属性overlay出现；姜月初眼睛被金光照亮
- end_state：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, VFX_系统面板, WEAPON_01；保持 CHAR_01, CHAR_02 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。
  action: 姜月初绝望吐槽；金色古卷面板浮现；基础属性overlay出现；姜月初眼睛被金光照亮
  end_state: 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。
  constraints: 保持 LOC_01、LOC_01, VFX_系统面板, WEAPON_01、CHAR_01, CHAR_02 的视觉连续；轴线=姜月初先看脚边裴长青，再看眼前金色面板。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在CU→POV，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：面板位于姜月初主观视野中央偏上，姜月初脸部或眼睛作为反应镜。;
表演节拍：[0-2.7s] 裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。; [2.7-5.3s] 姜月初绝望吐槽 / 金色古卷面板浮现 / 基础属性overlay出现 / 姜月初眼睛被金光照亮; [5.3-8s] 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。;
运动精修约束：幅度小到中，能量=爆发，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：无。;
专项模板约束：template_id=system_panel，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; prompt 只使用 primary_backend 真实支持的能力，失败按 degrade_plan/fallback 执行;
物理交互约束：无。; FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败;
身份锁定约束：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。 → 止：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01', 'VFX_系统面板']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；若 route.native_audio_policy=lipsync_condition_only，只把配音轨当口型条件，不保留模型音频；禁止原生人声、台词、旁白、哼唱和字幕文字。;
人物运动：姜月初绝望吐槽；金色古卷面板浮现；基础属性overlay出现；姜月初眼睛被金光照亮；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：固定机位，锁定屏幕/光幕平面，不漂移，只允许轻微呼吸式微动;
情绪节奏：[0-终点] 裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。 -> 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按match_cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: 屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。;
opening frame state: 裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。;
ending frame state: 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。;
blocking: 面板位于姜月初主观视野中央偏上，姜月初脸部或眼睛作为反应镜。;
performance beats: [0-2.7s] 裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。; [2.7-5.3s] 姜月初绝望吐槽 / 金色古卷面板浮现 / 基础属性overlay出现 / 姜月初眼睛被金光照亮; [5.3-8s] 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。;
motion refinement: amplitude=low-to-medium, energy follows tension, anatomy_guard=stable center of gravity, clear hand/weapon ownership, no face stretching;
ambient interaction: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
close-up identity lock: use face close-up / expression references / reference_group first; lock face not emotion, keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01', 'VFX_系统面板']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 姜月初绝望吐槽; 金色古卷面板浮现; 基础属性overlay出现; 姜月初眼睛被金光照亮;
camera motion: 固定机位，锁定屏幕/光幕平面，不漂移，只允许轻微呼吸式微动; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative; audio constraint: 禁止后端生成台词；配音仅作口型条件，声源归属=画内说话主体，compose_policy=丢弃模型音轨；旁白与屏幕文字只交 n2d-compose，不生成旁白音频，不渲染字幕。
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=voice_conditioned_lipsync; quality_tier=high; duration=11.197s; aspect=9:16; native_audio_policy=lipsync_condition_only; identity adapter=native_identity_lock_required; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全
5. ✅ ②镜头运动：推/拉/跟/固定/轻震等词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：CHAR_01/囚犯初醒态、CHAR_02/濒死战损态、CHAR_03/诈死复苏态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; risk=low; speech_policy=no_native_speech; compose_policy=丢弃模型音轨; review=确认无原生人声/旁白/哼唱；lipsync_condition_only 仅作口型条件，不保留模型音频。
14. ✅ Motion Control：本镜不要求控制资产

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃。
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_07_百妖谱第一次开启.mp4` ｜ 进废料重跑 ｜ 改 prompt/拆 Clip 后重跑

### 保真实现分解方案
- 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

## Clip 08（时长 8.588s · EP01_CLIP08 · 系统规则指向唯一活物）　**节奏**：铺垫·长镜　**张力**：爆发
**剧本可看性合同**：clip_id=EP01_CLIP08；dramatic_function=把系统规则指向“斩杀生物”，并把可杀目标从虎妖转向裴长青。；audience_effect=观众意识到规则有代价，开始预判主角会不会突破道德底线。；spectacle_story_function=无。

**首帧**：`出图/第1集/图片/Clip08_first.png`
**锚帧1**（4.0s · split）：`出图/第1集/图片/Clip08_mid.png`
**尾帧**：`出图/第1集/图片/Clip08_end.png`
**场景**：LOC_01 荒野尸骸战场/百妖谱面板与横刀；资产：LOC_01, VFX_系统面板, WEAPON_01
**导演意图**：屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在POV/OTS→CU手部，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：面板画面上方稳定悬浮，姜月初手和横刀在下方，裴长青在画面右下近景。
**表演节拍**：[0-2.7s] 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。; [2.7-5.3s] 规则overlay显示 / 姜月初手摸到横刀 / 姜月初视线从虎妖移到裴长青 / 面板稳定悬浮; [5.3-8s] 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。
**运动精修**：幅度=小/中; 能量=爆发; 身体守卫=重心、手部归属、遮挡层级、脸部轮廓和发髻稳定；张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。
**专项镜头模板**：template_id=system_panel; {"template_id": "system_panel", "beats": ["规则overlay显示", "姜月初手摸到横刀", "姜月初视线从虎妖移到裴长青", "面板稳定悬浮"], "blocking": "面板画面上方稳定悬浮，姜月初手和横刀在下方，裴长青在画面右下近景。", "camera_rule": "过肩/主观镜，面板和刀柄同框时保持面板不变形。", "continuity_must": ["面板仍为v1素纹古卷", "文字走overlay", "横刀位于姜月初脚边", "裴长青仍有一口气"], "negative": ["不要AI生成文字", "不要让横刀漂移到虎妖旁", "不要让裴长青死亡状态提前"], "motif_id": "MOTIF_系统面板", "vfx_asset": "VFX_系统面板", "text_layer": "overlay", "growth_ref": "MOTIF_系统面板.v1.at_EP01_CLIP08", "panel_tier": "v1_素纹古卷", "overlay_lines": ["斩杀生物，可得道行", "摹其形，夺其神通"]}
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; risk_flags=identity_escalated,native_multiframe,seam_relay; policy_resolution.winner=identity_affinity; degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "lipsync_condition_only", "requires_voice_track": false, "speech_policy": "no_native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "voice_conditioned_lipsync", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01"], "characters": [{"binding": "native_identity_lock_required", "character_id": "CHAR_01", "form": ""}, {"binding": "native_identity_lock_required", "character_id": "CHAR_02", "form": ""}, {"binding": "native_identity_lock_required", "character_id": "CHAR_03", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。
**角色身份注册层**：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。 → 止：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=配音仅可作为口型条件输入，模型音频不进成片。禁止模型生成台词、旁白、哼唱或环境人声。
**在场链约束**：required_presence=['CHAR_01', 'VFX_系统面板', 'WEAPON_01', 'CHAR_02']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。
- 出点：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。
- 转场：eyeline
- 连贯性：eyeline=姜月初看面板，再看虎妖，最后低头看裴长青。; shot_size=POV/OTS→CU手部; need_endframe=True

**continuity**：
- start_state：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。
- action：规则overlay显示；姜月初手摸到横刀；姜月初视线从虎妖移到裴长青；面板稳定悬浮
- end_state：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, VFX_系统面板, WEAPON_01；保持 CHAR_01, CHAR_02, CHAR_03 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。
  action: 规则overlay显示；姜月初手摸到横刀；姜月初视线从虎妖移到裴长青；面板稳定悬浮
  end_state: 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。
  constraints: 保持 LOC_01、LOC_01, VFX_系统面板, WEAPON_01、CHAR_01, CHAR_02, CHAR_03 的视觉连续；轴线=姜月初看面板，再看虎妖，最后低头看裴长青。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在POV/OTS→CU手部，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：面板画面上方稳定悬浮，姜月初手和横刀在下方，裴长青在画面右下近景。;
表演节拍：[0-2.7s] 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。; [2.7-5.3s] 规则overlay显示 / 姜月初手摸到横刀 / 姜月初视线从虎妖移到裴长青 / 面板稳定悬浮; [5.3-8s] 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。;
运动精修约束：幅度小到中，能量=爆发，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：无。;
专项模板约束：template_id=system_panel，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; prompt 只使用 primary_backend 真实支持的能力，失败按 degrade_plan/fallback 执行;
物理交互约束：无。; FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败;
身份锁定约束：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。 → 止：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01', 'VFX_系统面板', 'WEAPON_01', 'CHAR_02']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；若 route.native_audio_policy=lipsync_condition_only，只把配音轨当口型条件，不保留模型音频；禁止原生人声、台词、旁白、哼唱和字幕文字。;
人物运动：规则overlay显示；姜月初手摸到横刀；姜月初视线从虎妖移到裴长青；面板稳定悬浮；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：固定机位，锁定屏幕/光幕平面，不漂移，只允许轻微呼吸式微动;
情绪节奏：[0-终点] 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。 -> 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按eyeline服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: 屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。;
opening frame state: 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。;
ending frame state: 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。;
blocking: 面板画面上方稳定悬浮，姜月初手和横刀在下方，裴长青在画面右下近景。;
performance beats: [0-2.7s] 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。; [2.7-5.3s] 规则overlay显示 / 姜月初手摸到横刀 / 姜月初视线从虎妖移到裴长青 / 面板稳定悬浮; [5.3-8s] 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。;
motion refinement: amplitude=low-to-medium, energy follows tension, anatomy_guard=stable center of gravity, clear hand/weapon ownership, no face stretching;
ambient interaction: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
close-up identity lock: use face close-up / expression references / reference_group first; lock face not emotion, keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01', 'VFX_系统面板', 'WEAPON_01', 'CHAR_02']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 规则overlay显示; 姜月初手摸到横刀; 姜月初视线从虎妖移到裴长青; 面板稳定悬浮;
camera motion: 固定机位，锁定屏幕/光幕平面，不漂移，只允许轻微呼吸式微动; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative; audio constraint: 禁止后端生成台词；配音仅作口型条件，声源归属=画内说话主体，compose_policy=丢弃模型音轨；旁白与屏幕文字只交 n2d-compose，不生成旁白音频，不渲染字幕。
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=voice_conditioned_lipsync; quality_tier=high; duration=8.588s; aspect=9:16; native_audio_policy=lipsync_condition_only; identity adapter=native_identity_lock_required; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全
5. ✅ ②镜头运动：推/拉/跟/固定/轻震等词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：CHAR_01/囚犯初醒态、CHAR_02/濒死战损态、CHAR_03/诈死复苏态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; risk=low; speech_policy=no_native_speech; compose_policy=丢弃模型音轨; review=确认无原生人声/旁白/哼唱；lipsync_condition_only 仅作口型条件，不保留模型音频。
14. ✅ Motion Control：本镜不要求控制资产

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃。
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_08_系统规则指向唯一活物.mp4` ｜ 进废料重跑 ｜ 改 prompt/拆 Clip 后重跑

### 保真实现分解方案
- 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

## Clip 09（时长 9.988s · EP01_CLIP09 · 刀尖抬起）　**节奏**：加速·碎切　**张力**：爆发
**剧本可看性合同**：clip_id=EP01_CLIP09；dramatic_function=姜月初摸刀并权衡虎妖与裴长青，完成刺杀选择前的心理转折。；audience_effect=观众看见她不是冲动黑化，而是在无路可走中被规则逼到刀口。；spectacle_story_function=无。

**首帧**：`出图/第1集/图片/Clip09_first.png`
**锚帧1**（4.0s · split）：`出图/第1集/图片/Clip09_mid.png`
**尾帧**：`出图/第1集/图片/Clip09_end.png`
**场景**：LOC_01 荒野尸骸战场/姜月初选择点；资产：LOC_01, WEAPON_01, VFX_系统面板
**导演意图**：屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在LS→CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：虎山神画右远景，姜月初画左前景，裴长青画右下近景；横刀在姜月初手中。
**表演节拍**：[0-2.7s] 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。; [2.7-5.3s] 虎妖远景嘲弄 / 姜月初看裴长青 / 旁白点明唯一活物 / 姜月初握刀下决心; [5.3-8s] 刀身反光划过姜月初眼睛，她下定决心。
**运动精修**：幅度=小/中; 能量=爆发; 身体守卫=重心、手部归属、遮挡层级、脸部轮廓和发髻稳定；张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。
**专项镜头模板**：template_id=dialogue_shot_reverse; {"template_id": "dialogue_shot_reverse", "beats": ["虎妖远景嘲弄", "姜月初看裴长青", "旁白点明唯一活物", "姜月初握刀下决心"], "blocking": "虎山神画右远景，姜月初画左前景，裴长青画右下近景；横刀在姜月初手中。", "camera_rule": "远景压迫 + 姜月初CU + 裴长青低角度反应，不越轴。", "continuity_must": ["虎妖不突然近身", "裴长青仍有一口气", "姜月初已持有横刀", "百妖谱金光仍在她眼底"], "negative": ["不要让虎妖发动新攻击", "不要把姜月初拍成主动兴奋", "不要让裴长青站起"], "axis": "姜月初/裴长青 ↔ 虎妖斜向轴", "eyeline": "虎妖看画左前景姜月初；姜月初低头看画右下裴长青；裴长青眼神失焦看姜月初背影", "shot_pairing": "虎妖远景压迫 / 姜月初CU握刀 / 裴长青低角度虚弱反应"}
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; risk_flags=identity_escalated,mouth_visible,native_multiframe,seam_relay; policy_resolution.winner=identity_affinity; degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "lipsync_condition_only", "requires_voice_track": false, "speech_policy": "no_native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "voice_conditioned_lipsync", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01"], "characters": [{"binding": "native_identity_lock_required", "character_id": "CHAR_01", "form": ""}, {"binding": "native_identity_lock_required", "character_id": "CHAR_02", "form": ""}, {"binding": "native_identity_lock_required", "character_id": "CHAR_03", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无。
**角色身份注册层**：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。 → 止：刀身反光划过姜月初眼睛，她下定决心。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=配音仅可作为口型条件输入，模型音频不进成片。禁止模型生成台词、旁白、哼唱或环境人声。
**在场链约束**：required_presence=['CHAR_01', 'CHAR_02', 'CHAR_03', 'WEAPON_01']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。
- 出点：刀身反光划过姜月初眼睛，她下定决心。
- 转场：hard_cut
- 连贯性：eyeline=姜月初低头看裴长青，虎妖从远景看姜月初。; shot_size=LS→CU; need_endframe=True

**continuity**：
- start_state：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。
- action：虎妖远景嘲弄；姜月初看裴长青；旁白点明唯一活物；姜月初握刀下决心
- end_state：刀身反光划过姜月初眼睛，她下定决心。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, WEAPON_01, VFX_系统面板；保持 CHAR_01, CHAR_02, CHAR_03 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。
  action: 虎妖远景嘲弄；姜月初看裴长青；旁白点明唯一活物；姜月初握刀下决心
  end_state: 刀身反光划过姜月初眼睛，她下定决心。
  constraints: 保持 LOC_01、LOC_01, WEAPON_01, VFX_系统面板、CHAR_01, CHAR_02, CHAR_03 的视觉连续；轴线=姜月初低头看裴长青，虎妖从远景看姜月初。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在LS→CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：虎山神画右远景，姜月初画左前景，裴长青画右下近景；横刀在姜月初手中。;
表演节拍：[0-2.7s] 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。; [2.7-5.3s] 虎妖远景嘲弄 / 姜月初看裴长青 / 旁白点明唯一活物 / 姜月初握刀下决心; [5.3-8s] 刀身反光划过姜月初眼睛，她下定决心。;
运动精修约束：幅度小到中，能量=爆发，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：无。;
专项模板约束：template_id=dialogue_shot_reverse，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; prompt 只使用 primary_backend 真实支持的能力，失败按 degrade_plan/fallback 执行;
物理交互约束：无。; FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败;
身份锁定约束：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。 → 止：刀身反光划过姜月初眼睛，她下定决心。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01', 'CHAR_02', 'CHAR_03', 'WEAPON_01']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；若 route.native_audio_policy=lipsync_condition_only，只把配音轨当口型条件，不保留模型音频；禁止原生人声、台词、旁白、哼唱和字幕文字。;
人物运动：虎妖远景嘲弄；姜月初看裴长青；旁白点明唯一活物；姜月初握刀下决心；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：固定机位，锁定屏幕/光幕平面，不漂移，只允许轻微呼吸式微动;
情绪节奏：[0-终点] 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。 -> 刀身反光划过姜月初眼睛，她下定决心。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按hard_cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: 屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。;
opening frame state: 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。;
ending frame state: 刀身反光划过姜月初眼睛，她下定决心。;
blocking: 虎山神画右远景，姜月初画左前景，裴长青画右下近景；横刀在姜月初手中。;
performance beats: [0-2.7s] 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。; [2.7-5.3s] 虎妖远景嘲弄 / 姜月初看裴长青 / 旁白点明唯一活物 / 姜月初握刀下决心; [5.3-8s] 刀身反光划过姜月初眼睛，她下定决心。;
motion refinement: amplitude=low-to-medium, energy follows tension, anatomy_guard=stable center of gravity, clear hand/weapon ownership, no face stretching;
ambient interaction: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
close-up identity lock: use face close-up / expression references / reference_group first; lock face not emotion, keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01', 'CHAR_02', 'CHAR_03', 'WEAPON_01']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 虎妖远景嘲弄; 姜月初看裴长青; 旁白点明唯一活物; 姜月初握刀下决心;
camera motion: 固定机位，锁定屏幕/光幕平面，不漂移，只允许轻微呼吸式微动; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative; audio constraint: 禁止后端生成台词；配音仅作口型条件，声源归属=画内说话主体，compose_policy=丢弃模型音轨；旁白与屏幕文字只交 n2d-compose，不生成旁白音频，不渲染字幕。
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=voice_conditioned_lipsync; quality_tier=high; duration=9.988s; aspect=9:16; native_audio_policy=lipsync_condition_only; identity adapter=native_identity_lock_required; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全
5. ✅ ②镜头运动：推/拉/跟/固定/轻震等词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：CHAR_01/囚犯初醒态、CHAR_02/濒死战损态、CHAR_03/诈死复苏态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; risk=low; speech_policy=no_native_speech; compose_policy=丢弃模型音轨; review=确认无原生人声/旁白/哼唱；lipsync_condition_only 仅作口型条件，不保留模型音频。
14. ✅ Motion Control：本镜不要求控制资产

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃。
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_09_刀尖抬起.mp4` ｜ 进废料重跑 ｜ 改 prompt/拆 Clip 后重跑

### 保真实现分解方案
- 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

## Clip 10（时长 6.54s · EP01_CLIP10 · 刺杀裴长青）　**节奏**：爽点·CU硬切　**张力**：爆发
**剧本可看性合同**：clip_id=EP01_CLIP10；dramatic_function=执行反选择：姜月初刺杀裴长青，把本集推到道德反转高潮。；audience_effect=观众受到“她真刺了”的冲击，追问系统是否认可、裴长青是否会死。；spectacle_story_function=刺杀动作服务主角求生选择和集尾反转，重在刀入胸与眼神冻结，不炫技。。

**首帧**：`出图/第1集/图片/Clip10_first.png`
**锚帧1**（3.5s · qc）：`出图/第1集/图片/Clip10_mid.png`
**尾帧**：`出图/第1集/图片/Clip10_end.png`
**场景**：LOC_01 荒野尸骸战场/裴长青脚边；资产：LOC_01, WEAPON_01, VFX_系统面板
**导演意图**：屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在ECU/CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：姜月初画左上方俯身，裴长青画右下方倒地，横刀从画左上向画右下短促推进。
**表演节拍**：[0-2.3s] 刀身反光划过姜月初眼睛，她下定决心。; [2.3-4.7s] 姜月初低声道歉 / 裴长青困惑抬眼 / 姜月初短促刺下 / 裴长青瞳孔僵住; [4.7-7s] 长刀入胸，裴长青眼神僵住，BGM 抽空。
**运动精修**：幅度=小/中; 能量=爆发; 身体守卫=重心、手部归属、遮挡层级、脸部轮廓和发髻稳定；张力=爆发；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：{"required": true, "shot_type": "fight_exchange", "beats": ["姜月初低声道歉", "裴长青困惑抬眼", "姜月初短促刺下", "裴长青瞳孔僵住"], "speed_curve": "道歉慢→裴反问停半拍→刺下快→瞳孔僵住留白", "spatial_path": "姜月初俯身靠近裴长青，横刀沿短直线刺下", "camera_path": "固定近景，命中帧轻微快推，不环绕", "readability_beats": ["先看清姜月初道歉", "再看清裴长青不理解", "最后看清刀柄推进和裴眼神僵住"], "degrade_plan": "若接触镜不稳，拆为姜月初道歉脸部、横刀刀柄推进手部、裴长青眼睛僵住三个特写。", "keyframe_plan": {"start": "姜月初低头道歉", "intent_mid": "裴长青困惑抬眼", "impact_or_apex": "横刀刀柄短促推进", "result_or_recovery": "裴长青瞳孔僵住", "end": "姜月初低头不看裴长青"}, "post_cue_points": {"pre_peak": "1:18 裴长青反问后静半拍", "peak": "5.0s 入肉声 + BGM抽空 + 2帧hit-stop", "aftershock_or_hold": "1:22 只留风声和心跳"}, "physics_guard": {"identity_lock": ["CHAR_01", "CHAR_02"], "axis_lock": "姜月初在画左上，裴长青在画右下，不交换位置", "contact_lock": "只允许横刀刀尖接触裴长青胸口，避免血腥扩散", "forbid": ["新增搏斗", "裴长青站起", "虎妖插手本镜"]}, "attack_path": "姜月初双手持横刀自画左上向画右下短促刺向裴长青胸口。", "impact_frame": "命中 5.0s：横刀没入裴长青胸口，画面只给刀柄推进和裴瞳孔僵住。", "contact_points": ["横刀刀尖", "裴长青胸口"], "force_direction": "姜月初画左上→裴长青画右下", "recovery_beat": "BGM抽空，裴长青不动，姜月初低头进入集尾定格"}
**专项镜头模板**：template_id=fight_exchange; {"template_id": "fight_exchange", "beats": ["姜月初低声道歉", "裴长青困惑抬眼", "姜月初短促刺下", "裴长青瞳孔僵住"], "blocking": "姜月初画左上方俯身，裴长青画右下方倒地，横刀从画左上向画右下短促推进。", "camera_rule": "ECU嘴唇/眼神→手部特写→裴长青瞳孔CU；不拍猎奇血腥正面。", "continuity_must": ["姜月初仍穿囚服", "裴长青仍濒死倒地", "横刀由姜月初持有", "百妖谱金光仍映眼"], "negative": ["不要猎奇血腥喷溅", "不要让姜月初表情兴奋", "不要让裴长青突然反击", "不要新增道具"], "pose_reference_required": true, "regional_construct_required": true, "attack_path": "姜月初双手持横刀自画左上向画右下短促刺向裴长青胸口。", "impact_frame": "命中 5.0s：横刀没入裴长青胸口，画面只给刀柄推进和裴瞳孔僵住。", "action_scope": "一次短促刺下，不追加拔刀或二次动作。", "contact_points": ["横刀刀尖", "裴长青胸口"], "force_direction": "姜月初画左上→裴长青画右下", "screen_direction": "画左上到画右下", "speed_curve": "道歉慢→裴反问停半拍→刺下快→瞳孔僵住留白", "spatial_path": "姜月初俯身靠近裴长青，横刀沿短直线刺下", "camera_path": "固定近景，命中帧轻微快推，不环绕", "readability_beats": ["先看清姜月初道歉", "再看清裴长青不理解", "最后看清刀柄推进和裴眼神僵住"], "recovery_beat": "BGM抽空，裴长青不动，姜月初低头进入集尾定格", "degrade_plan": "若接触镜不稳，拆为姜月初道歉脸部、横刀刀柄推进手部、裴长青眼睛僵住三个特写。", "keyframe_plan": {"start": "姜月初低头道歉", "intent_mid": "裴长青困惑抬眼", "impact_or_apex": "横刀刀柄短促推进", "result_or_recovery": "裴长青瞳孔僵住", "end": "姜月初低头不看裴长青"}, "post_cue_points": {"pre_peak": "1:18 裴长青反问后静半拍", "peak": "5.0s 入肉声 + BGM抽空 + 2帧hit-stop", "aftershock_or_hold": "1:22 只留风声和心跳"}, "physics_guard": {"identity_lock": ["CHAR_01", "CHAR_02"], "axis_lock": "姜月初在画左上，裴长青在画右下，不交换位置", "contact_lock": "只允许横刀刀尖接触裴长青胸口，避免血腥扩散", "forbid": ["新增搏斗", "裴长青站起", "虎妖插手本镜"]}, "interaction_graph": {"participants": ["CHAR_01", "CHAR_02", "WEAPON_01"], "contact_points": [{"source": "CHAR_01.left_hand+CHAR_01.right_hand", "target": "WEAPON_01.hilt", "frame": "intent_mid_to_impact"}, {"source": "WEAPON_01.tip", "target": "CHAR_02.chest", "frame": "impact_frame"}], "body_part_ownership": {"CHAR_01.left_hand": "姜月初左手握横刀刀柄", "CHAR_01.right_hand": "姜月初右手压住横刀刀柄", "WEAPON_01.tip": "横刀刀尖，唯一接触点", "CHAR_02.chest": "裴长青胸口，受击主体"}, "occlusion_order": ["横刀刀柄和姜月初双手位于前景", "横刀刀尖只在接触点短促进入裴长青胸口", "裴长青脸部和瞳孔反应保持可读，不被刀柄遮挡", "虎妖不进入本镜接触层"], "force_direction": "姜月初画左上向画右下短促刺入", "motion_vector": "WEAPON_01 沿画左上到画右下的短直线推进，命中后停顿不拔出", "release_frame": "命中后横刀停在裴长青胸口，姜月初双手仍握刀柄，WEAPON_01 保持由 CHAR_01 持握，不发生递交或脱手。", "transfer_event": "WEAPON_01 在本镜前已由 CHAR_01 拾取并持有；本镜只发生从 CHAR_01 持握状态到刺入/停顿状态的状态变化，不转移给 CHAR_02。"}, "combat_micro_expression": "姜月初嘴唇颤抖、眼神压狠；裴长青困惑转为僵住。", "secondary_motion": "姜月初发丝轻晃，横刀推进带轻微手抖。", "apex_light": "金色百妖谱光在命中前一瞬擦过刀柄和姜月初眼睛。"}
**模型路由**：shot_type=fight_exchange; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; risk_flags=action_choreography_required,contact_motion,feature_melting_risk,identity_drift_risk,identity_escalated,motion_reference_candidate,mouth_visible,native_multiframe,physical_interaction,seam_relay; policy_resolution.winner=identity_affinity; degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "lipsync_condition_only", "requires_voice_track": false, "speech_policy": "no_native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": true}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第1集/control/Clip_10/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks", "contact_map", "camera_path"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "voice_conditioned_lipsync", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01", "WEAPON_01"], "characters": [{"binding": "native_identity_lock_required", "character_id": "CHAR_01", "form": ""}, {"binding": "native_identity_lock_required", "character_id": "CHAR_02", "form": ""}], "identity_preservation_plan": {"applies_to": "fight_exchange", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "native_identity_lock_required", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": true, "library_path": "生产数据/motion_reference_library.json", "policy": "use same sequence/shot_type approved reference when available"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：level=required; manifest_path=出视频/第1集/control/Clip_10/motion_control_manifest.json; required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path; failure_modes=feature_melting,limb_fusion,weapon_contact_drift,body_interpenetration; status=ready 或 degrade_only；若无 pose/depth/instance/contact/camera_path，则执行保真实现分解，不直接生成全身复杂接触或长连续高速动作。
**角色身份注册层**：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：刀身反光划过姜月初眼睛，她下定决心。 → 止：长刀入胸，裴长青眼神僵住，BGM 抽空。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=配音仅可作为口型条件输入，模型音频不进成片。禁止模型生成台词、旁白、哼唱或环境人声。
**在场链约束**：required_presence=['CHAR_01', 'CHAR_02', 'WEAPON_01']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：刀身反光划过姜月初眼睛，她下定决心。
- 出点：长刀入胸，裴长青眼神僵住，BGM 抽空。
- 转场：hard_cut
- 连贯性：eyeline=姜月初低头看裴长青但不敢对视；裴长青抬眼看姜月初。; shot_size=ECU/CU; need_endframe=True

**continuity**：
- start_state：刀身反光划过姜月初眼睛，她下定决心。
- action：姜月初低声道歉；裴长青困惑抬眼；姜月初短促刺下；裴长青瞳孔僵住
- end_state：长刀入胸，裴长青眼神僵住，BGM 抽空。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, WEAPON_01, VFX_系统面板；保持 CHAR_01, CHAR_02 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 刀身反光划过姜月初眼睛，她下定决心。
  action: 姜月初低声道歉；裴长青困惑抬眼；姜月初短促刺下；裴长青瞳孔僵住
  end_state: 长刀入胸，裴长青眼神僵住，BGM 抽空。
  constraints: 保持 LOC_01、LOC_01, WEAPON_01, VFX_系统面板、CHAR_01, CHAR_02 的视觉连续；轴线=姜月初低头看裴长青但不敢对视；裴长青抬眼看姜月初。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在ECU/CU，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：姜月初画左上方俯身，裴长青画右下方倒地，横刀从画左上向画右下短促推进。;
表演节拍：[0-2.3s] 刀身反光划过姜月初眼睛，她下定决心。; [2.3-4.7s] 姜月初低声道歉 / 裴长青困惑抬眼 / 姜月初短促刺下 / 裴长青瞳孔僵住; [4.7-7s] 长刀入胸，裴长青眼神僵住，BGM 抽空。;
运动精修约束：幅度小到中，能量=爆发，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：{"required": true, "shot_type": "fight_exchange", "beats": ["姜月初低声道歉", "裴长青困惑抬眼", "姜月初短促刺下", "裴长青瞳孔僵住"], "speed_curve": "道歉慢→裴反问停半拍→刺下快→瞳孔僵住留白", "spatial_path": "姜月初俯身靠近裴长青，横刀沿短直线刺下", "camera_path": "固定近景，命中帧轻微快推，不环绕", "readability_beats": ["先看清姜月初道歉", "再看清裴长青不理解", "最后看清刀柄推进和裴眼神僵住"], "degrade_plan": "若接触镜不稳，拆为姜月初道歉脸部、横刀刀柄推进手部、裴长青眼睛僵住三个特写。", "keyframe_plan": {"start": "姜月初低头道歉", "intent_mid": "裴长青困惑抬眼", "impact_or_apex": "横刀刀柄短促推进", "result_or_recovery": "裴长青瞳孔僵住", "end": "姜月初低头不看裴长青"}, "post_cue_points": {"pre_peak": "1:18 裴长青反问后静半拍", "peak": "5.0s 入肉声 + BGM抽空 + 2帧hit-stop", "aftershock_or_hold": "1:22 只留风声和心跳"}, "physics_guard": {"identity_lock": ["CHAR_01", "CHAR_02"], "axis_lock": "姜月初在画左上，裴长青在画右下，不交换位置", "contact_lock": "只允许横刀刀尖接触裴长青胸口，避免血腥扩散", "forbid": ["新增搏斗", "裴长青站起", "虎妖插手本镜"]}, "attack_path": "姜月初双手持横刀自画左上向画右下短促刺向裴长青胸口。", "impact_frame": "命中 5.0s：横刀没入裴长青胸口，画面只给刀柄推进和裴瞳孔僵住。", "contact_points": ["横刀刀尖", "裴长青胸口"], "force_direction": "姜月初画左上→裴长青画右下", "recovery_beat": "BGM抽空，裴长青不动，姜月初低头进入集尾定格"};
专项模板约束：template_id=fight_exchange，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=fight_exchange; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; prompt 只使用 primary_backend 真实支持的能力，失败按 degrade_plan/fallback 执行;
物理交互约束：level=required; manifest_path=出视频/第1集/control/Clip_10/motion_control_manifest.json; required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path; failure_modes=feature_melting,limb_fusion,weapon_contact_drift,body_interpenetration; status=ready 或 degrade_only；若无 pose/depth/instance/contact/camera_path，则执行保真实现分解，不直接生成全身复杂接触或长连续高速动作。; FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败;
身份锁定约束：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：刀身反光划过姜月初眼睛，她下定决心。 → 止：长刀入胸，裴长青眼神僵住，BGM 抽空。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01', 'CHAR_02', 'WEAPON_01']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；若 route.native_audio_policy=lipsync_condition_only，只把配音轨当口型条件，不保留模型音频；禁止原生人声、台词、旁白、哼唱和字幕文字。;
人物运动：姜月初低声道歉；裴长青困惑抬眼；姜月初短促刺下；裴长青瞳孔僵住；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：固定机位，锁定屏幕/光幕平面，不漂移，只允许轻微呼吸式微动;
情绪节奏：[0-终点] 刀身反光划过姜月初眼睛，她下定决心。 -> 长刀入胸，裴长青眼神僵住，BGM 抽空。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按hard_cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: 屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。;
opening frame state: 刀身反光划过姜月初眼睛，她下定决心。;
ending frame state: 长刀入胸，裴长青眼神僵住，BGM 抽空。;
blocking: 姜月初画左上方俯身，裴长青画右下方倒地，横刀从画左上向画右下短促推进。;
performance beats: [0-2.3s] 刀身反光划过姜月初眼睛，她下定决心。; [2.3-4.7s] 姜月初低声道歉 / 裴长青困惑抬眼 / 姜月初短促刺下 / 裴长青瞳孔僵住; [4.7-7s] 长刀入胸，裴长青眼神僵住，BGM 抽空。;
motion refinement: amplitude=low-to-medium, energy follows tension, anatomy_guard=stable center of gravity, clear hand/weapon ownership, no face stretching;
ambient interaction: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
close-up identity lock: use face close-up / expression references / reference_group first; lock face not emotion, keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01', 'CHAR_02', 'WEAPON_01']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 姜月初低声道歉; 裴长青困惑抬眼; 姜月初短促刺下; 裴长青瞳孔僵住;
camera motion: 固定机位，锁定屏幕/光幕平面，不漂移，只允许轻微呼吸式微动; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative; audio constraint: 禁止后端生成台词；配音仅作口型条件，声源归属=画内说话主体，compose_policy=丢弃模型音轨；旁白与屏幕文字只交 n2d-compose，不生成旁白音频，不渲染字幕。
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=voice_conditioned_lipsync; quality_tier=high; duration=6.54s; aspect=9:16; native_audio_policy=lipsync_condition_only; identity adapter=native_identity_lock_required; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全
5. ✅ ②镜头运动：推/拉/跟/固定/轻震等词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：CHAR_01/囚犯初醒态、CHAR_02/濒死战损态、CHAR_03/诈死复苏态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; risk=low; speech_policy=no_native_speech; compose_policy=丢弃模型音轨; review=确认无原生人声/旁白/哼唱；lipsync_condition_only 仅作口型条件，不保留模型音频。
14. ✅ Motion Control：已继承 level/manifest_path/required_inputs/failure_modes；无控制资产时按 degrade_only 保真实现分解，不靠文本硬扛

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃。
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜
- [ ] Motion Control：检查 FeatureMelting/特征融化、limb_fusion、weapon_contact_drift、slot_drift；若失败按 degrade_only 拆为手部/反打/释放帧。
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_10_刺杀裴长青.mp4` ｜ 进废料重跑 ｜ 改 prompt/拆 Clip 后重跑

### 保真实现分解方案
- 若接触镜不稳，拆为姜月初道歉脸部、横刀刀柄推进手部、裴长青眼睛僵住三个特写。

## Clip 11（时长 2.053s · EP01_CLIP11 · 我只想活下去）　**节奏**：留白·定格　**张力**：紧张
**剧本可看性合同**：clip_id=EP01_CLIP11；dramatic_function=在刺杀后留白，锁住“我只想活下去”的人物底色和第2集悬念。；audience_effect=观众带着百妖谱是否生效、虎妖是否扑来、裴长青命运三重问题进入下一集。；spectacle_story_function=无。

**首帧**：`出图/第1集/图片/Clip11_first.png`
**场景**：LOC_01 荒野尸骸战场/集尾定格；资产：LOC_01, WEAPON_01, VFX_系统面板
**导演意图**：屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。
**起幅**：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。
**落幅**：落在CU 定格，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：CHAR_01 占 LEFT_SLOT/前景主检脸，CHAR_02 只保留 RIGHT_LOW_SLOT 局部承接态，CHAR_03 为 RIGHT_BACKGROUND_SLOT 巨大阴影。
**表演节拍**：[0-2.0s] 长刀入胸，裴长青眼神僵住，BGM 抽空。; [2.0-4.0s] 长刀入胸后的静默停顿 / 姜月初低头说只想活下去 / 虎妖阴影在背景停住; [4.0-6s] 姜月初低头说“我只想活下去”，虎妖阴影在背景停住。
**运动精修**：幅度=小/中; 能量=紧张; 身体守卫=重心、手部归属、遮挡层级、脸部轮廓和发髻稳定；张力=克制；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。
**动作编排契约 / Action Choreography**：无。
**专项镜头模板**：template_id=multi_character_same_frame; {"template_id": "multi_character_same_frame", "beats": ["长刀入胸后的静默停顿", "姜月初低头说只想活下去", "虎妖阴影在背景停住"], "blocking": "CHAR_01 占 LEFT_SLOT/前景主检脸，CHAR_02 只保留 RIGHT_LOW_SLOT 局部承接态，CHAR_03 为 RIGHT_BACKGROUND_SLOT 巨大阴影。", "camera_rule": "CU 缓推姜月初，不切换清晰三脸；裴长青和虎妖作为前景/背景状态锚。", "continuity_must": ["横刀刀柄在前景", "CHAR_01 低头不兴奋", "CHAR_02 不突然消失", "CHAR_03 只停在背景不给结果"], "negative": ["不要猎奇血腥", "不要让姜月初直视镜头微笑", "不要让虎妖扑上来", "不要把裴长青拍成站立状态"], "character_slots": [{"slot": "LEFT_SLOT", "character_id": "CHAR_01", "screen_position": "画左前景/近景主检脸，囚犯初醒态或百妖谱触发态", "face_priority": "主检"}, {"slot": "RIGHT_LOW_SLOT", "character_id": "CHAR_02", "screen_position": "画右下/近中景半跪或倒地，黑衣赤纹战损，左臂扭曲", "face_priority": "次检"}, {"slot": "RIGHT_BACKGROUND_SLOT", "character_id": "CHAR_03", "screen_position": "画右远景巨岩旁或背景高位，虎首人身巨大尺度", "face_priority": "次检"}], "face_priority": ["CHAR_01"], "overlap_rules": ["CHAR_01 主检脸不被刀柄遮挡", "CHAR_02 只保留局部承接态，可虚焦", "CHAR_03 只作背景阴影，不与前景清晰脸竞争"]}
**模型路由**：shot_type=multi_character_same_frame; primary_backend=seedance; fallback=dreamina; mode=frames2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; risk_flags=identity_drift_risk,identity_escalated,multi_person; policy_resolution.winner=identity_affinity; degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "none", "requires_voice_track": false, "speech_policy": "no_native_speech"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第1集/control/Clip_11/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "first_frame", "first_frame": true, "last_frame": false, "mid_anchors": 0, "native_timeline_frames": 1, "reference_only": false, "requires_split_relay": false}, "mode": "frames2video", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01"], "characters": [{"binding": "native_identity_lock_required", "character_id": "CHAR_01", "form": ""}, {"binding": "native_identity_lock_required", "character_id": "CHAR_02", "form": ""}, {"binding": "native_identity_lock_required", "character_id": "CHAR_03", "form": ""}], "identity_preservation_plan": {"applies_to": "multi_character_same_frame", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "native_identity_lock_required", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：level=required; manifest_path=出视频/第1集/control/Clip_11/motion_control_manifest.json; required_inputs=pose_sequence,depth_sequence,instance_masks; failure_modes=slot_drift,pose_drift,identity_drift; status=ready 或 degrade_only；若无 pose/depth/instance/contact/camera_path，则执行保真实现分解，不直接生成全身复杂接触或长连续高速动作。
**角色身份注册层**：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：长刀入胸，裴长青眼神僵住，BGM 抽空。 → 止：姜月初低头说“我只想活下去”，虎妖阴影在背景停住。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=静音图生视频。禁止模型生成台词、旁白、哼唱或环境人声。
**在场链约束**：required_presence=['CHAR_01', 'WEAPON_01', 'VFX_系统面板']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：长刀入胸，裴长青眼神僵住，BGM 抽空。
- 出点：姜月初低头说“我只想活下去”，虎妖阴影在背景停住。
- 转场：hard_cut
- 连贯性：eyeline=姜月初低头不看镜头，虎妖阴影从背景压住她。; shot_size=CU 定格; need_endframe=False

**continuity**：
- start_state：长刀入胸，裴长青眼神僵住，BGM 抽空。
- action：长刀入胸后的静默停顿；姜月初低头说只想活下去；虎妖阴影在背景停住
- end_state：姜月初低头说“我只想活下去”，虎妖阴影在背景停住。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, WEAPON_01, VFX_系统面板；保持 CHAR_01, CHAR_02, CHAR_03 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 长刀入胸，裴长青眼神僵住，BGM 抽空。
  action: 长刀入胸后的静默停顿；姜月初低头说只想活下去；虎妖阴影在背景停住
  end_state: 姜月初低头说“我只想活下去”，虎妖阴影在背景停住。
  constraints: 保持 LOC_01、LOC_01, WEAPON_01, VFX_系统面板、CHAR_01, CHAR_02, CHAR_03 的视觉连续；轴线=姜月初低头不看镜头，虎妖阴影从背景压住她。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定。;
落幅：落在CU 定格，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。;
场面调度：CHAR_01 占 LEFT_SLOT/前景主检脸，CHAR_02 只保留 RIGHT_LOW_SLOT 局部承接态，CHAR_03 为 RIGHT_BACKGROUND_SLOT 巨大阴影。;
表演节拍：[0-2.0s] 长刀入胸，裴长青眼神僵住，BGM 抽空。; [2.0-4.0s] 长刀入胸后的静默停顿 / 姜月初低头说只想活下去 / 虎妖阴影在背景停住; [4.0-6s] 姜月初低头说“我只想活下去”，虎妖阴影在背景停住。;
运动精修约束：幅度小到中，能量=紧张，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：无。;
专项模板约束：template_id=multi_character_same_frame，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=multi_character_same_frame; primary_backend=seedance; fallback=dreamina; mode=frames2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; prompt 只使用 primary_backend 真实支持的能力，失败按 degrade_plan/fallback 执行;
物理交互约束：level=required; manifest_path=出视频/第1集/control/Clip_11/motion_control_manifest.json; required_inputs=pose_sequence,depth_sequence,instance_masks; failure_modes=slot_drift,pose_drift,identity_drift; status=ready 或 degrade_only；若无 pose/depth/instance/contact/camera_path，则执行保真实现分解，不直接生成全身复杂接触或长连续高速动作。; FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败;
身份锁定约束：CHAR_01/囚犯初醒态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态; identity_requirement=character_id_or_reference_group; reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png; Character ID / Face Lock / reference controls: fallback_reference_group; 脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png; expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png; 身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：长刀入胸，裴长青眼神僵住，BGM 抽空。 → 止：姜月初低头说“我只想活下去”，虎妖阴影在背景停住。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01', 'WEAPON_01', 'VFX_系统面板']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；禁止原生人声、台词、旁白、哼唱和字幕文字。;
人物运动：长刀入胸后的静默停顿；姜月初低头说只想活下去；虎妖阴影在背景停住；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：固定机位，锁定屏幕/光幕平面，不漂移，只允许轻微呼吸式微动;
情绪节奏：[0-终点] 长刀入胸，裴长青眼神僵住，BGM 抽空。 -> 姜月初低头说“我只想活下去”，虎妖阴影在背景停住。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按hard_cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: 屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。;
opening frame state: 长刀入胸，裴长青眼神僵住，BGM 抽空。;
ending frame state: 姜月初低头说“我只想活下去”，虎妖阴影在背景停住。;
blocking: CHAR_01 占 LEFT_SLOT/前景主检脸，CHAR_02 只保留 RIGHT_LOW_SLOT 局部承接态，CHAR_03 为 RIGHT_BACKGROUND_SLOT 巨大阴影。;
performance beats: [0-2.0s] 长刀入胸，裴长青眼神僵住，BGM 抽空。; [2.0-4.0s] 长刀入胸后的静默停顿 / 姜月初低头说只想活下去 / 虎妖阴影在背景停住; [4.0-6s] 姜月初低头说“我只想活下去”，虎妖阴影在背景停住。;
motion refinement: amplitude=low-to-medium, energy follows tension, anatomy_guard=stable center of gravity, clear hand/weapon ownership, no face stretching;
ambient interaction: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
close-up identity lock: use face close-up / expression references / reference_group first; lock face not emotion, keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01', 'WEAPON_01', 'VFX_系统面板']; offscreen_presence=[]; forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字']; entry_exit=按本镜衔接设计：入画/出画/画外保留由 storyboard start/end_state 与转场解释; required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 长刀入胸后的静默停顿; 姜月初低头说只想活下去; 虎妖阴影在背景停住;
camera motion: 固定机位，锁定屏幕/光幕平面，不漂移，只允许轻微呼吸式微动; dynamic detail: 人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative; audio constraint: 默认禁止原生人声：无对白、无旁白、不要生成原生人声；只允许静默画面，若平台强出声音也由 compose 丢弃。
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=frames2video; quality_tier=high; duration=2.053s; aspect=9:16; native_audio_policy=none; identity adapter=native_identity_lock_required; frame_inputs={"consumption_mode": "first_frame", "first_frame": true, "last_frame": false, "mid_anchors": 0, "native_timeline_frames": 1, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全
5. ✅ ②镜头运动：推/拉/跟/固定/轻震等词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：CHAR_01/囚犯初醒态、CHAR_02/濒死战损态、CHAR_03/诈死复苏态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; risk=low; speech_policy=no_native_speech; compose_policy=丢弃模型音轨; review=确认无原生人声/旁白/哼唱；lipsync_condition_only 仅作口型条件，不保留模型音频。
14. ✅ Motion Control：已继承 level/manifest_path/required_inputs/failure_modes；无控制资产时按 degrade_only 保真实现分解，不靠文本硬扛

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃。
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜
- [ ] Motion Control：检查 FeatureMelting/特征融化、limb_fusion、weapon_contact_drift、slot_drift；若失败按 degrade_only 拆为手部/反打/释放帧。
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_11_我只想活下去.mp4` ｜ 进废料重跑 ｜ 改 prompt/拆 Clip 后重跑

### 保真实现分解方案
- If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.
