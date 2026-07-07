# 第1集 视频 Clip prompt

## 本集留存承诺账本（script_quality_contract）

- R01: hook_id=OPEN_01；opened_at=EP01_CLIP01；payoff_clip=EP01_CLIP07；payoff_due=EP01_CLIP07；payoff_status=paid；promise=姜月初为什么在尸场醒来，她能否找到活路。；promise_type=opening_hook
- R02: hook_id=MID_01；opened_at=EP01_CLIP05；payoff_clip=EP01_CLIP06；payoff_due=EP01_CLIP06；payoff_status=paid；promise=死透的虎妖为什么还能复活。；promise_type=mid_hook
- R03: hook_id=TAIL_01；opened_at=EP01_CLIP10；payoff_due=第2集开场；promise=姜月初刺杀裴长青后，能否借百妖谱获得道行并反杀或收录虎山神。；promise_type=cliffhanger

## Clip 01（时长 9.236s · EP01_CLIP01 · 死人堆惊醒）

**首帧**：`出图/第1集/图片/Clip01_first.png`
**尾帧**：`出图/第1集/图片/Clip01_end.png`
**锚帧1**：`出图/第1集/图片/Clip01_mid.png`（at_sec=3.0）
**场景**：LOC_01 荒野尸骸战场/冷灰夜/外
**剧本可看性合同**：dramatic_function=冷开场建立“尸场醒来”的生死危机，把观众立即拉进主角无助处境。；audience_effect=静音也能读懂她刚穿越就落入死局，产生“她怎么活”的第一问题。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：冷开场建立“尸场醒来”的生死危机，把观众立即拉进主角无助处境。
**起幅**：姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。
**落幅**：姜月初坐在尸堆边，抬头望向远处巨岩黑影。
**场面调度**：ECU 固定 → ELS→LS 缓慢推近；角色=CHAR_01；资产=LOC_01；轴线/视线=姜月初从近前尸骸扫向画右远景巨岩。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 固定近景，姜月初猛然睁眼，风吹发丝和枯草，冷灰月光擦过脸侧。；慢推交代大唐边地荒野尸场，远处巨岩黑影压迫。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=按 storyboard shots 顺序执行；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**专项镜头模板**：template=none；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group；assets=LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；本镜绑定=CHAR_01；资产引用注册层=LOC_01。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。
- 出点：姜月初坐在尸堆边，抬头望向远处巨岩黑影。
- 转场：eyeline
- 连贯性：required_presence=CHAR_01、尸骸前景、荒野尸场; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初从近前尸骸扫向画右远景巨岩。; inner_focus=无

**continuity**：
- start_state：姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。
- action：固定近景，姜月初猛然睁眼，风吹发丝和枯草，冷灰月光擦过脸侧。；慢推交代大唐边地荒野尸场，远处巨岩黑影压迫。
- end_state：姜月初坐在尸堆边，抬头望向远处巨岩黑影。
- constraints：required_presence=CHAR_01、尸骸前景、荒野尸场; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初从近前尸骸扫向画右远景巨岩。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。
  action: 固定近景，姜月初猛然睁眼，风吹发丝和枯草，冷灰月光擦过脸侧。；慢推交代大唐边地荒野尸场，远处巨岩黑影压迫。
  end_state: 姜月初坐在尸堆边，抬头望向远处巨岩黑影。
  constraints: required_presence=CHAR_01、尸骸前景、荒野尸场; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初从近前尸骸扫向画右远景巨岩。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。
剧本可看性合同：dramatic_function=冷开场建立“尸场醒来”的生死危机，把观众立即拉进主角无助处境。; audience_effect=静音也能读懂她刚穿越就落入死局，产生“她怎么活”的第一问题。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：冷开场建立“尸场醒来”的生死危机，把观众立即拉进主角无助处境。;
起幅：姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。;
落幅：姜月初坐在尸堆边，抬头望向远处巨岩黑影。;
场面调度：ECU 固定 → ELS→LS 缓慢推近；角色槽位=CHAR_01；资产ID=LOC_01；
内心戏主体隔离：非内心戏/按在场链执行；
表演节拍：[0-30%] 承接首帧；[30-75%] 固定近景，姜月初猛然睁眼，风吹发丝和枯草，冷灰月光擦过脸侧。；慢推交代大唐边地荒野尸场，远处巨岩黑影压迫。；[75-100%] 姜月初坐在尸堆边，抬头望向远处巨岩黑影。;
运动精修约束：幅度=小到中；人物槽位不漂移；能量=克制；表情和视线先动，身体后动；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=按 storyboard shots 顺序执行；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
专项模板约束：template=none；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=image2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
物理交互约束：读取 motion_control_manifest.json；level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=中；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
近景升格守卫：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。；
尾端落幅保持：按 continuity.end_state 停住，不提前预演下一 Clip。；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：固定近景，姜月初猛然睁眼，风吹发丝和枯草，冷灰月光擦过脸侧。；慢推交代大唐边地荒野尸场，远处巨岩黑影压迫。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或缓慢推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务铺垫·长镜；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按eyeline服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；内心戏镜头不得重复上一镜群像/妖魔/道具陈列；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 姜月初脸侧贴着血尘枯草猛然睁眼，尸骸手指虚焦压前景。; perform only 固定近景，姜月初猛然睁眼，风吹发丝和枯草，冷灰月光擦过脸侧。；慢推交代大唐边地荒野尸场，远处巨岩黑影压迫。; end on 姜月初坐在尸堆边，抬头望向远处巨岩黑影。; preserve required_presence=CHAR_01、尸骸前景、荒野尸场; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初从近前尸骸扫向画右远景巨岩。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
inner-focus isolation: not an inner-focus shot; follow entity schedule.
director intent: 冷开场建立“尸场醒来”的生死危机，把观众立即拉进主角无助处境。; audience effect: 静音也能读懂她刚穿越就落入死局，产生“她怎么活”的第一问题。.
character motion: 固定近景，姜月初猛然睁眼，风吹发丝和枯草，冷灰月光擦过脸侧。；慢推交代大唐边地荒野尸场，远处巨岩黑影压迫。; camera motion: 固定或缓慢推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
close-up promotion guard: do not turn a small, distant, side/back, occluded, or non-primary anchor face into a clear close-up face unless a same-source close-up anchor/expression reference has passed full image QC.
ending reaction hold: hold the continuity.end_state until the cut and do not preview the next clip early.
native audio policy: audio_intent=none; speech_policy=no_native_speech; compose_policy=discard.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已进入 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ 中文 prompt 已写首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不乱甩。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_01.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 02（时长 16.570s · EP01_CLIP02 · 看见虎妖尸身）

**首帧**：`出图/第1集/图片/Clip02_first.png`
**尾帧**：`出图/第1集/图片/Clip02_end.png`
**锚帧1**：`出图/第1集/图片/Clip02_mid.png`（at_sec=4.0）
**场景**：LOC_01 荒野尸骸战场/巨岩方向
**剧本可看性合同**：dramatic_function=扩大世界观危险：虎首人身妖魔尸身与荒野尸场证明这是妖魔大唐。；audience_effect=观众确认危险不是幻觉，同时被“虎妖真死了吗”悬念牵住。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：扩大世界观危险：虎首人身妖魔尸身与荒野尸场证明这是妖魔大唐。
**起幅**：姜月初坐在尸堆边，抬头望向远处巨岩黑影。
**落幅**：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。
**场面调度**：MCU 轻摇 → LS 固定；角色=CHAR_01、CHAR_03；资产=LOC_01；轴线/视线=姜月初视线由自己囚服转向画右远景虎妖尸身，再转向裴长青。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 镜头轻摇到囚服衣襟和麻绳腰束，再回到她惊疑的脸。；冷灰低雾中，虎妖尸身巨大如山，胸口黑血缓慢滴落，不提前亮眼。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；只执行本镜主动作链
- 能量：克制匀速
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=确认现代记忆、囚服身份落点、异界尸场显景；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=低头看囚服、旁白给出现代到大唐落差、远景显出虎妖尸身；degrade_plan=若一镜内认知和显景不稳，拆成囚服特写、尸场全景、虎妖尸身远景三张锚帧。
**专项镜头模板**：template=realm_portal；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=realm_portal; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=face_lock_or_reference_group; degrade_plan=Split into setup plate, activation/impact insert, and result/reaction; keep VFX shape from shared assets or overlay geometry.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；binding=face_lock_or_reference_group、character_id=CHAR_03；binding=face_lock_or_reference_group；assets=LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=Split into setup plate, activation/impact insert, and result/reaction; keep VFX shape from shared assets or overlay geometry.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Split into setup plate, activation/impact insert, and result/reaction; keep VFX shape from shared assets or overlay geometry.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_03/诈死复苏态：reference_group=ready；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼；本镜绑定=CHAR_01、CHAR_03；资产引用注册层=LOC_01。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：姜月初坐在尸堆边，抬头望向远处巨岩黑影。
- 出点：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。
- 转场：j_cut
- 连贯性：required_presence=CHAR_01、CHAR_03、巨岩、黑色妖血; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初视线由自己囚服转向画右远景虎妖尸身，再转向裴长青。; inner_focus=无

**continuity**：
- start_state：姜月初坐在尸堆边，抬头望向远处巨岩黑影。
- action：镜头轻摇到囚服衣襟和麻绳腰束，再回到她惊疑的脸。；冷灰低雾中，虎妖尸身巨大如山，胸口黑血缓慢滴落，不提前亮眼。
- end_state：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。
- constraints：required_presence=CHAR_01、CHAR_03、巨岩、黑色妖血; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初视线由自己囚服转向画右远景虎妖尸身，再转向裴长青。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 姜月初坐在尸堆边，抬头望向远处巨岩黑影。
  action: 镜头轻摇到囚服衣襟和麻绳腰束，再回到她惊疑的脸。；冷灰低雾中，虎妖尸身巨大如山，胸口黑血缓慢滴落，不提前亮眼。
  end_state: 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。
  constraints: required_presence=CHAR_01、CHAR_03、巨岩、黑色妖血; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初视线由自己囚服转向画右远景虎妖尸身，再转向裴长青。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。
剧本可看性合同：dramatic_function=扩大世界观危险：虎首人身妖魔尸身与荒野尸场证明这是妖魔大唐。; audience_effect=观众确认危险不是幻觉，同时被“虎妖真死了吗”悬念牵住。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：扩大世界观危险：虎首人身妖魔尸身与荒野尸场证明这是妖魔大唐。;
起幅：姜月初坐在尸堆边，抬头望向远处巨岩黑影。;
落幅：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。;
场面调度：MCU 轻摇 → LS 固定；角色槽位=CHAR_01、CHAR_03；资产ID=LOC_01；
内心戏主体隔离：非内心戏/按在场链执行；
表演节拍：[0-30%] 承接首帧；[30-75%] 镜头轻摇到囚服衣襟和麻绳腰束，再回到她惊疑的脸。；冷灰低雾中，虎妖尸身巨大如山，胸口黑血缓慢滴落，不提前亮眼。；[75-100%] 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。;
运动精修约束：幅度=小幅；只执行本镜主动作链；能量=克制匀速；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=确认现代记忆、囚服身份落点、异界尸场显景；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=低头看囚服、旁白给出现代到大唐落差、远景显出虎妖尸身；degrade_plan=若一镜内认知和显景不稳，拆成囚服特写、尸场全景、虎妖尸身远景三张锚帧。；
专项模板约束：template=realm_portal；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=image2video，native_audio_policy=none，identity_requirement=face_lock_or_reference_group；失败按 degrade_plan=Split into setup plate, activation/impact insert, and result/reaction; keep VFX shape from shared assets or overlay geometry.；
物理交互约束：读取 motion_control_manifest.json；level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Split into setup plate, activation/impact insert, and result/reaction; keep VFX shape from shared assets or overlay geometry.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_03/诈死复苏态：reference_group=ready；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=中；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
近景升格守卫：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。；
尾端落幅保持：按 continuity.end_state 停住，不提前预演下一 Clip。；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：镜头轻摇到囚服衣襟和麻绳腰束，再回到她惊疑的脸。；冷灰低雾中，虎妖尸身巨大如山，胸口黑血缓慢滴落，不提前亮眼。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或极缓推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务铺垫·长镜；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按j_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；内心戏镜头不得重复上一镜群像/妖魔/道具陈列；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 姜月初坐在尸堆边，抬头望向远处巨岩黑影。; perform only 镜头轻摇到囚服衣襟和麻绳腰束，再回到她惊疑的脸。；冷灰低雾中，虎妖尸身巨大如山，胸口黑血缓慢滴落，不提前亮眼。; end on 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。; preserve required_presence=CHAR_01、CHAR_03、巨岩、黑色妖血; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初视线由自己囚服转向画右远景虎妖尸身，再转向裴长青。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
inner-focus isolation: not an inner-focus shot; follow entity schedule.
director intent: 扩大世界观危险：虎首人身妖魔尸身与荒野尸场证明这是妖魔大唐。; audience effect: 观众确认危险不是幻觉，同时被“虎妖真死了吗”悬念牵住。.
character motion: 镜头轻摇到囚服衣襟和麻绳腰束，再回到她惊疑的脸。；冷灰低雾中，虎妖尸身巨大如山，胸口黑血缓慢滴落，不提前亮眼。; camera motion: 固定或极缓推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
close-up promotion guard: do not turn a small, distant, side/back, occluded, or non-primary anchor face into a clear close-up face unless a same-source close-up anchor/expression reference has passed full image QC.
ending reaction hold: hold the continuity.end_state until the cut and do not preview the next clip early.
native audio policy: audio_intent=none; speech_policy=no_native_speech; compose_policy=discard.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已进入 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ 中文 prompt 已写首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不乱甩。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_02.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 03（时长 18.752s · EP01_CLIP03 · 镇魔司压迫交易）

**首帧**：`出图/第1集/图片/Clip03_first.png`
**尾帧**：`出图/第1集/图片/Clip03_end.png`
**锚帧1**：`出图/第1集/图片/Clip03_mid.png`（at_sec=4.0）
**场景**：LOC_01 荒野尸骸战场/裴长青半跪处
**剧本可看性合同**：dramatic_function=让裴长青以威胁和交易介入，给姜月初一个不可信但暂时可走的生路。；audience_effect=观众感到她被官差和身份双重压迫，理解她没有轻松逃跑选项。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：让裴长青以威胁和交易介入，给姜月初一个不可信但暂时可走的生路。
**起幅**：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。
**落幅**：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。
**场面调度**：CU 反打 → MS/CU 碎切；角色=CHAR_01、CHAR_02；资产=LOC_01, WEAPON_01；轴线/视线=姜月初看画右裴长青，裴长青看画左姜月初。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 冷灰近景正反打，姜月初戒备，裴长青半跪惨白。；断刀破风钉地，姜月初僵住，裴长青抬眼压迫。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=裴长青沙哑命令、姜月初后退反问、断刀钉地威胁、裴长青报镇魔司身份提出交易；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**专项镜头模板**：template=dialogue_shot_reverse；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_02；binding=character_id_or_reference_group；assets=LOC_01、WEAPON_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；本镜绑定=CHAR_01、CHAR_02；资产引用注册层=LOC_01, WEAPON_01。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。
- 出点：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。
- 转场：action_cut
- 连贯性：required_presence=CHAR_01、CHAR_02、WEAPON_01; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看画右裴长青，裴长青看画左姜月初。; inner_focus=无

**continuity**：
- start_state：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。
- action：冷灰近景正反打，姜月初戒备，裴长青半跪惨白。；断刀破风钉地，姜月初僵住，裴长青抬眼压迫。
- end_state：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。
- constraints：required_presence=CHAR_01、CHAR_02、WEAPON_01; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看画右裴长青，裴长青看画左姜月初。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。
  action: 冷灰近景正反打，姜月初戒备，裴长青半跪惨白。；断刀破风钉地，姜月初僵住，裴长青抬眼压迫。
  end_state: 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。
  constraints: required_presence=CHAR_01、CHAR_02、WEAPON_01; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看画右裴长青，裴长青看画左姜月初。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。
剧本可看性合同：dramatic_function=让裴长青以威胁和交易介入，给姜月初一个不可信但暂时可走的生路。; audience_effect=观众感到她被官差和身份双重压迫，理解她没有轻松逃跑选项。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：让裴长青以威胁和交易介入，给姜月初一个不可信但暂时可走的生路。;
起幅：虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。;
落幅：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。;
场面调度：CU 反打 → MS/CU 碎切；角色槽位=CHAR_01、CHAR_02；资产ID=LOC_01, WEAPON_01；
内心戏主体隔离：非内心戏/按在场链执行；
表演节拍：[0-30%] 承接首帧；[30-75%] 冷灰近景正反打，姜月初戒备，裴长青半跪惨白。；断刀破风钉地，姜月初僵住，裴长青抬眼压迫。；[75-100%] 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。;
运动精修约束：幅度=小到中；人物槽位不漂移；能量=克制；表情和视线先动，身体后动；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=裴长青沙哑命令、姜月初后退反问、断刀钉地威胁、裴长青报镇魔司身份提出交易；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
专项模板约束：template=dialogue_shot_reverse；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=image2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
物理交互约束：读取 motion_control_manifest.json；level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=大；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
近景升格守卫：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。；
尾端落幅保持：按 continuity.end_state 停住，不提前预演下一 Clip。；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：冷灰近景正反打，姜月初戒备，裴长青半跪惨白。；断刀破风钉地，姜月初僵住，裴长青抬眼压迫。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或缓慢推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务加速·碎切；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按action_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；内心戏镜头不得重复上一镜群像/妖魔/道具陈列；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 虎妖胸口黑血滴落声压住环境，姜月初视线转向画右半跪的裴长青。; perform only 冷灰近景正反打，姜月初戒备，裴长青半跪惨白。；断刀破风钉地，姜月初僵住，裴长青抬眼压迫。; end on 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。; preserve required_presence=CHAR_01、CHAR_02、WEAPON_01; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看画右裴长青，裴长青看画左姜月初。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
inner-focus isolation: not an inner-focus shot; follow entity schedule.
director intent: 让裴长青以威胁和交易介入，给姜月初一个不可信但暂时可走的生路。; audience effect: 观众感到她被官差和身份双重压迫，理解她没有轻松逃跑选项。.
character motion: 冷灰近景正反打，姜月初戒备，裴长青半跪惨白。；断刀破风钉地，姜月初僵住，裴长青抬眼压迫。; camera motion: 固定或缓慢推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
close-up promotion guard: do not turn a small, distant, side/back, occluded, or non-primary anchor face into a clear close-up face unless a same-source close-up anchor/expression reference has passed full image QC.
ending reaction hold: hold the continuity.end_state until the cut and do not preview the next clip early.
native audio policy: audio_intent=none; speech_policy=no_native_speech; compose_policy=discard.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已进入 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ 中文 prompt 已写首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不乱甩。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_03.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 04（时长 10.010s · EP01_CLIP04 · 被迫扶裴南行）

**首帧**：`出图/第1集/图片/Clip04_first.png`
**尾帧**：`出图/第1集/图片/Clip04_end.png`
**锚帧1**：`出图/第1集/图片/Clip04_mid.png`（at_sec=4.0）
**场景**：LOC_01 荒野尸骸战场/南向逃路线
**剧本可看性合同**：dramatic_function=用搀扶南行让姜月初暂时接受交易，并把人物位置推进到虎妖复苏前一刻。；audience_effect=观众获得短暂缓和后立刻等待背后异响的反扑。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：用搀扶南行让姜月初暂时接受交易，并把人物位置推进到虎妖复苏前一刻。
**起幅**：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。
**落幅**：二人刚走出几步，身后传来湿咳声。
**场面调度**：MS→LS 缓慢跟拍；角色=CHAR_01、CHAR_02；资产=LOC_01；轴线/视线=姜月初看向南向逃路，偶尔回头警惕虎妖方向。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 缓慢跟拍，裴长青大半重量压在姜月初肩上，枯草和低雾横向掠过。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=姜月初伸手扶起裴长青、二人沿南向逃路线踉跄移动、湿咳声打断逃跑；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.
**专项镜头模板**：template=multi_character_same_frame；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=multi_character_same_frame; primary_backend=seedance; fallback=dreamina; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_02；binding=character_id_or_reference_group；assets=LOC_01、WEAPON_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；identity_preservation_plan=required_identity_anchors=face_shape、hairstyle、age_read、outfit_palette、named_character_screen_slot；reference_strategy=character_id_or_reference_group；motion_readability_allowances=prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups、allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot、keep first/end frame and registered reference group as identity truth when motion control needs simpler movement；fallback_plan=If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.；applies_to=multi_character_same_frame；control_inputs=manifest_path=出视频/第1集/control/Clip_04/motion_control_manifest.json；required=True；required_inputs=pose_sequence、depth_sequence、instance_masks；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_04/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；本镜绑定=CHAR_01、CHAR_02；资产引用注册层=LOC_01。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。
- 出点：二人刚走出几步，身后传来湿咳声。
- 转场：j_cut
- 连贯性：required_presence=CHAR_01、CHAR_02; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看向南向逃路，偶尔回头警惕虎妖方向。; inner_focus=无

**continuity**：
- start_state：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。
- action：缓慢跟拍，裴长青大半重量压在姜月初肩上，枯草和低雾横向掠过。
- end_state：二人刚走出几步，身后传来湿咳声。
- constraints：required_presence=CHAR_01、CHAR_02; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看向南向逃路，偶尔回头警惕虎妖方向。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。
  action: 缓慢跟拍，裴长青大半重量压在姜月初肩上，枯草和低雾横向掠过。
  end_state: 二人刚走出几步，身后传来湿咳声。
  constraints: required_presence=CHAR_01、CHAR_02; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看向南向逃路，偶尔回头警惕虎妖方向。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。
剧本可看性合同：dramatic_function=用搀扶南行让姜月初暂时接受交易，并把人物位置推进到虎妖复苏前一刻。; audience_effect=观众获得短暂缓和后立刻等待背后异响的反扑。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：用搀扶南行让姜月初暂时接受交易，并把人物位置推进到虎妖复苏前一刻。;
起幅：姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。;
落幅：二人刚走出几步，身后传来湿咳声。;
场面调度：MS→LS 缓慢跟拍；角色槽位=CHAR_01、CHAR_02；资产ID=LOC_01；
内心戏主体隔离：非内心戏/按在场链执行；
表演节拍：[0-30%] 承接首帧；[30-75%] 缓慢跟拍，裴长青大半重量压在姜月初肩上，枯草和低雾横向掠过。；[75-100%] 二人刚走出几步，身后传来湿咳声。;
运动精修约束：幅度=小到中；人物槽位不漂移；能量=克制；表情和视线先动，身体后动；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=姜月初伸手扶起裴长青、二人沿南向逃路线踉跄移动、湿咳声打断逃跑；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.；
专项模板约束：template=multi_character_same_frame；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=frames2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.；
物理交互约束：读取 motion_control_manifest.json；level=required；manifest_path=出视频/第1集/control/Clip_04/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=中；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
近景升格守卫：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。；
尾端落幅保持：按 continuity.end_state 停住，不提前预演下一 Clip。；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：缓慢跟拍，裴长青大半重量压在姜月初肩上，枯草和低雾横向掠过。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或缓慢推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务铺垫·长镜；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按j_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；内心戏镜头不得重复上一镜群像/妖魔/道具陈列；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 姜月初低头看刀，再看裴长青，最终咬牙伸手扶他。; perform only 缓慢跟拍，裴长青大半重量压在姜月初肩上，枯草和低雾横向掠过。; end on 二人刚走出几步，身后传来湿咳声。; preserve required_presence=CHAR_01、CHAR_02; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看向南向逃路，偶尔回头警惕虎妖方向。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
inner-focus isolation: not an inner-focus shot; follow entity schedule.
director intent: 用搀扶南行让姜月初暂时接受交易，并把人物位置推进到虎妖复苏前一刻。; audience effect: 观众获得短暂缓和后立刻等待背后异响的反扑。.
character motion: 缓慢跟拍，裴长青大半重量压在姜月初肩上，枯草和低雾横向掠过。; camera motion: 固定或缓慢推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
close-up promotion guard: do not turn a small, distant, side/back, occluded, or non-primary anchor face into a clear close-up face unless a same-source close-up anchor/expression reference has passed full image QC.
ending reaction hold: hold the continuity.end_state until the cut and do not preview the next clip early.
native audio policy: audio_intent=none; speech_policy=no_native_speech; compose_policy=discard.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已进入 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ 中文 prompt 已写首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不乱甩。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_04.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 05（时长 12.995s · EP01_CLIP05 · 虎妖诈死复苏）

**首帧**：`出图/第1集/图片/Clip05_first.png`
**尾帧**：`出图/第1集/图片/Clip05_end.png`
**锚帧1**：`出图/第1集/图片/Clip05_mid.png`（at_sec=4.0）
**场景**：LOC_01 荒野尸骸战场/巨岩复苏点
**剧本可看性合同**：dramatic_function=反转虎妖未死，推翻“尸体安全”的判断，把逃生计划打碎。；audience_effect=观众从安全误判跌回绝境，期待裴长青如何解释或抵抗。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：反转虎妖未死，推翻“尸体安全”的判断，把逃生计划打碎。
**起幅**：二人刚走出几步，身后传来湿咳声。
**落幅**：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。
**场面调度**：CU 硬切 → LS 低机位慢推；角色=CHAR_01、CHAR_02、CHAR_03；资产=LOC_01, VFX_虎山神摹影；轴线/视线=姜月初和裴长青同时回头看画右远景虎妖；虎妖看画左前景二人。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 湿咳声后，姜月初手指松开，裴长青砸进尘土，二人惊恐回头。；低机位拍虎首人身巨妖从诈死尸身站起，金黄凶眼亮起，黑灰妖气回流。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；只执行本镜主动作链
- 能量：克制匀速
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=湿咳声打断逃跑、虎妖从尸身复苏、虎妖开口拦路、裴长青确认不可能；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.
**专项镜头模板**：template=reveal_reaction_chain；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=reveal_reaction_chain; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_02；binding=character_id_or_reference_group、character_id=CHAR_03；binding=character_id_or_reference_group；assets=LOC_01、WEAPON_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态：reference_group=ready；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼；本镜绑定=CHAR_01、CHAR_02、CHAR_03；资产引用注册层=LOC_01, VFX_虎山神摹影。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：二人刚走出几步，身后传来湿咳声。
- 出点：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。
- 转场：hard_cut
- 连贯性：required_presence=CHAR_01、CHAR_02、CHAR_03、VFX_虎山神摹影; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初和裴长青同时回头看画右远景虎妖；虎妖看画左前景二人。; inner_focus=无

**continuity**：
- start_state：二人刚走出几步，身后传来湿咳声。
- action：湿咳声后，姜月初手指松开，裴长青砸进尘土，二人惊恐回头。；低机位拍虎首人身巨妖从诈死尸身站起，金黄凶眼亮起，黑灰妖气回流。
- end_state：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。
- constraints：required_presence=CHAR_01、CHAR_02、CHAR_03、VFX_虎山神摹影; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初和裴长青同时回头看画右远景虎妖；虎妖看画左前景二人。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 二人刚走出几步，身后传来湿咳声。
  action: 湿咳声后，姜月初手指松开，裴长青砸进尘土，二人惊恐回头。；低机位拍虎首人身巨妖从诈死尸身站起，金黄凶眼亮起，黑灰妖气回流。
  end_state: 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。
  constraints: required_presence=CHAR_01、CHAR_02、CHAR_03、VFX_虎山神摹影; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初和裴长青同时回头看画右远景虎妖；虎妖看画左前景二人。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。
剧本可看性合同：dramatic_function=反转虎妖未死，推翻“尸体安全”的判断，把逃生计划打碎。; audience_effect=观众从安全误判跌回绝境，期待裴长青如何解释或抵抗。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：反转虎妖未死，推翻“尸体安全”的判断，把逃生计划打碎。;
起幅：二人刚走出几步，身后传来湿咳声。;
落幅：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。;
场面调度：CU 硬切 → LS 低机位慢推；角色槽位=CHAR_01、CHAR_02、CHAR_03；资产ID=LOC_01, VFX_虎山神摹影；
内心戏主体隔离：非内心戏/按在场链执行；
表演节拍：[0-30%] 承接首帧；[30-75%] 湿咳声后，姜月初手指松开，裴长青砸进尘土，二人惊恐回头。；低机位拍虎首人身巨妖从诈死尸身站起，金黄凶眼亮起，黑灰妖气回流。；[75-100%] 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。;
运动精修约束：幅度=小幅；只执行本镜主动作链；能量=克制匀速；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=湿咳声打断逃跑、虎妖从尸身复苏、虎妖开口拦路、裴长青确认不可能；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.；
专项模板约束：template=reveal_reaction_chain；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=image2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.；
物理交互约束：读取 motion_control_manifest.json；level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态：reference_group=ready；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=大；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
近景升格守卫：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。；
尾端落幅保持：按 continuity.end_state 停住，不提前预演下一 Clip。；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：湿咳声后，姜月初手指松开，裴长青砸进尘土，二人惊恐回头。；低机位拍虎首人身巨妖从诈死尸身站起，金黄凶眼亮起，黑灰妖气回流。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或极缓推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务揭示·反应链；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按hard_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；内心戏镜头不得重复上一镜群像/妖魔/道具陈列；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 二人刚走出几步，身后传来湿咳声。; perform only 湿咳声后，姜月初手指松开，裴长青砸进尘土，二人惊恐回头。；低机位拍虎首人身巨妖从诈死尸身站起，金黄凶眼亮起，黑灰妖气回流。; end on 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。; preserve required_presence=CHAR_01、CHAR_02、CHAR_03、VFX_虎山神摹影; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初和裴长青同时回头看画右远景虎妖；虎妖看画左前景二人。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
inner-focus isolation: not an inner-focus shot; follow entity schedule.
director intent: 反转虎妖未死，推翻“尸体安全”的判断，把逃生计划打碎。; audience effect: 观众从安全误判跌回绝境，期待裴长青如何解释或抵抗。.
character motion: 湿咳声后，姜月初手指松开，裴长青砸进尘土，二人惊恐回头。；低机位拍虎首人身巨妖从诈死尸身站起，金黄凶眼亮起，黑灰妖气回流。; camera motion: 固定或极缓推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
close-up promotion guard: do not turn a small, distant, side/back, occluded, or non-primary anchor face into a clear close-up face unless a same-source close-up anchor/expression reference has passed full image QC.
ending reaction hold: hold the continuity.end_state until the cut and do not preview the next clip early.
native audio policy: audio_intent=none; speech_policy=no_native_speech; compose_policy=discard.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已进入 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ 中文 prompt 已写首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不乱甩。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_05.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 06（时长 14.586s · EP01_CLIP06 · 裴长青最后一击被踹飞）

**首帧**：`出图/第1集/图片/Clip06_first.png`
**尾帧**：`出图/第1集/图片/Clip06_end_reaction.png`
**锚帧1**：`出图/第1集/图片/Clip06_mid_reaction.png`（at_sec=5.0）
**场景**：LOC_01 荒野尸骸战场/虎妖攻防轴
**剧本可看性合同**：dramatic_function=裴长青最后一击失败，证明正面武力路线断绝。；audience_effect=观众看到最强战力被一脚击溃，接受姜月初必须寻找非常规活路。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：裴长青最后一击失败，证明正面武力路线断绝。
**起幅**：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。
**落幅**：裴长青倒飞砸在姜月初脚边，横刀滑到画左前景；尘土扫过姜月初手背和衣袖，她只以侧背/OTS轮廓接住反应，不露清晰正脸。
**场面调度**：MS 固定微推 → CU 命中帧 → MS 低机位 + 手部/横刀插入镜；角色=CHAR_02、CHAR_03；资产=LOC_01, WEAPON_01, VFX_虎山神摹影；轴线/视线=裴长青看画右虎妖，虎妖看画左裴长青；姜月初只以画外/侧背视线目击脚边裴，不给清晰脸。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 裴长青强撑重伤捡刀，画左向画右扑击。；虎妖脚掌命中裴胸口，尘土和衣摆顺画左方向炸开，轻震屏。；裴长青倒飞砸地，横刀滑到画左前景；尘土扫过姜月初手背和灰褐衣袖，她只作侧背/OTS轮廓反应，不露清晰正脸。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；只执行本镜主动作链
- 能量：克制匀速
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=裴长青捡刀起手、裴长青合身扑向虎妖、虎妖右腿后发先至命中胸口、裴长青倒飞砸回姜月初脚边；speed_curve=裴长青起手慢半拍→扑击快切→命中顿帧0.3s→倒飞落地留0.5s；spatial_path=画左前景裴长青沿斜线扑向画右巨岩，命中后抛回画左前景姜月初脚边；camera_path=起手固定微推，命中帧短促快推，受击落地低幅震动；readability_beats=起手看清裴已重伤、命中帧看清虎妖脚掌接触裴胸口、落地看清裴砸到姜月初脚边；degrade_plan=若双主体接触不稳，拆为裴起手单人镜、虎妖脚掌命中特写、裴倒飞砸地+横刀滑近姜月初手部/侧背反应三段；禁止姜月初正脸近景。；keyframe_plan=end=横刀落在姜月初脚边，姜月初手部/衣袖入画，不露正脸；impact_or_apex=虎妖脚掌命中裴胸口；intent_mid=裴长青扑向虎妖；result_or_recovery=裴倒飞砸地；start=裴长青捡刀起手；post_cue_points=aftershock_or_hold=0:50 尘土扑面，BGM压低半拍；peak=5.0s impact 重低音 + 轻震屏 + 2帧hit-stop；pre_peak=0:45 出刀破风 whoosh；physics_guard=axis_lock=画左裴长青 ↔ 画右虎妖，不越轴；contact_lock=只允许虎妖右脚掌接触裴胸口；forbid=新增第二击、裴长青突然恢复健康、虎妖伤口消失；identity_lock=CHAR_02、CHAR_03；attack_path=裴长青横刀自画左下向画右上斩向虎妖脖颈，虎妖右腿自画右中线蹬向画左前景裴胸口。；impact_frame=命中 5.0s：虎妖脚掌命中裴长青胸口，裴身体弓起，尘土和衣摆顺画左方向飞散。；contact_points=虎妖右脚掌、裴长青胸口；force_direction=虎妖画右→裴长青画左前景，力向右上到左下；recovery_beat=裴长青倒地后横刀落在姜月初可触及的位置，只用手部/衣袖/侧背轮廓表现她的惊恐反应
**专项镜头模板**：template=fight_exchange；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=fight_exchange; primary_backend=seedance; fallback=dreamina; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_02；binding=character_id_or_reference_group、character_id=CHAR_03；binding=character_id_or_reference_group；assets=LOC_01、WEAPON_01；motion_reference=allowed=True；library_path=生产数据/motion_reference_library.json；policy=use same sequence/shot_type approved reference when available；identity_preservation_plan=required_identity_anchors=face_shape、hairstyle、age_read、outfit_palette、named_character_screen_slot；reference_strategy=character_id_or_reference_group；motion_readability_allowances=prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups、allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot、keep first/end frame and registered reference group as identity truth when motion control needs simpler movement；fallback_plan=If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.；applies_to=fight_exchange；control_inputs=manifest_path=出视频/第1集/control/Clip_06/motion_control_manifest.json；required=True；required_inputs=pose_sequence、depth_sequence、instance_masks、contact_map、camera_path；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_06/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path；failure_modes=feature_melting,limb_fusion,weapon_contact_drift,body_interpenetration；degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.
**角色身份注册层**：CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态：reference_group=ready；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼；本镜绑定=CHAR_02、CHAR_03；资产引用注册层=LOC_01, WEAPON_01, VFX_虎山神摹影。
**近景/反打身份锁定**：主焦点=CHAR_02；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_02 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=CHAR_01 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。
- 出点：裴长青倒飞砸在姜月初脚边，横刀滑到画左前景；尘土扫过姜月初手背和衣袖，她只以侧背/OTS轮廓接住反应，不露清晰正脸。
- 转场：action_cut
- 连贯性：required_presence=CHAR_02、CHAR_03、WEAPON_01; offscreen_presence=CHAR_01; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=裴长青看画右虎妖，虎妖看画左裴长青；姜月初只以画外/侧背视线目击脚边裴，不给清晰脸。; inner_focus=无

**continuity**：
- start_state：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。
- action：裴长青强撑重伤捡刀，画左向画右扑击。；虎妖脚掌命中裴胸口，尘土和衣摆顺画左方向炸开，轻震屏。；裴长青倒飞砸地，横刀滑到画左前景；尘土扫过姜月初手背和灰褐衣袖，她只作侧背/OTS轮廓反应，不露清晰正脸。
- end_state：裴长青倒飞砸在姜月初脚边，横刀滑到画左前景；尘土扫过姜月初手背和衣袖，她只以侧背/OTS轮廓接住反应，不露清晰正脸。
- constraints：required_presence=CHAR_02、CHAR_03、WEAPON_01; offscreen_presence=CHAR_01; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=裴长青看画右虎妖，虎妖看画左裴长青；姜月初只以画外/侧背视线目击脚边裴，不给清晰脸。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。
  action: 裴长青强撑重伤捡刀，画左向画右扑击。；虎妖脚掌命中裴胸口，尘土和衣摆顺画左方向炸开，轻震屏。；裴长青倒飞砸地，横刀滑到画左前景；尘土扫过姜月初手背和灰褐衣袖，她只作侧背/OTS轮廓反应，不露清晰正脸。
  end_state: 裴长青倒飞砸在姜月初脚边，横刀滑到画左前景；尘土扫过姜月初手背和衣袖，她只以侧背/OTS轮廓接住反应，不露清晰正脸。
  constraints: required_presence=CHAR_02、CHAR_03、WEAPON_01; offscreen_presence=CHAR_01; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=裴长青看画右虎妖，虎妖看画左裴长青；姜月初只以画外/侧背视线目击脚边裴，不给清晰脸。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。
剧本可看性合同：dramatic_function=裴长青最后一击失败，证明正面武力路线断绝。; audience_effect=观众看到最强战力被一脚击溃，接受姜月初必须寻找非常规活路。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：裴长青最后一击失败，证明正面武力路线断绝。;
起幅：虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。;
落幅：裴长青倒飞砸在姜月初脚边，横刀滑到画左前景；尘土扫过姜月初手背和衣袖，她只以侧背/OTS轮廓接住反应，不露清晰正脸。;
场面调度：MS 固定微推 → CU 命中帧 → MS 低机位 + 手部/横刀插入镜；角色槽位=CHAR_02、CHAR_03；资产ID=LOC_01, WEAPON_01, VFX_虎山神摹影；
内心戏主体隔离：非内心戏/按在场链执行；
表演节拍：[0-30%] 承接首帧；[30-75%] 裴长青强撑重伤捡刀，画左向画右扑击。；虎妖脚掌命中裴胸口，尘土和衣摆顺画左方向炸开，轻震屏。；裴长青倒飞砸地，横刀滑到画左前景；尘土扫过姜月初手背和灰褐衣袖，她只作侧背/OTS轮廓反应，不露清晰正脸。；[75-100%] 裴长青倒飞砸在姜月初脚边，横刀滑到画左前景；尘土扫过姜月初手背和衣袖，她只以侧背/OTS轮廓接住反应，不露清晰正脸。;
运动精修约束：幅度=小幅；只执行本镜主动作链；能量=克制匀速；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=裴长青捡刀起手、裴长青合身扑向虎妖、虎妖右腿后发先至命中胸口、裴长青倒飞砸回姜月初脚边；speed_curve=裴长青起手慢半拍→扑击快切→命中顿帧0.3s→倒飞落地留0.5s；spatial_path=画左前景裴长青沿斜线扑向画右巨岩，命中后抛回画左前景姜月初脚边；camera_path=起手固定微推，命中帧短促快推，受击落地低幅震动；readability_beats=起手看清裴已重伤、命中帧看清虎妖脚掌接触裴胸口、落地看清裴砸到姜月初脚边；degrade_plan=若双主体接触不稳，拆为裴起手单人镜、虎妖脚掌命中特写、裴倒飞砸地+横刀滑近姜月初手部/侧背反应三段；禁止姜月初正脸近景。；keyframe_plan=end=横刀落在姜月初脚边，姜月初手部/衣袖入画，不露正脸；impact_or_apex=虎妖脚掌命中裴胸口；intent_mid=裴长青扑向虎妖；result_or_recovery=裴倒飞砸地；start=裴长青捡刀起手；post_cue_points=aftershock_or_hold=0:50 尘土扑面，BGM压低半拍；peak=5.0s impact 重低音 + 轻震屏 + 2帧hit-stop；pre_peak=0:45 出刀破风 whoosh；physics_guard=axis_lock=画左裴长青 ↔ 画右虎妖，不越轴；contact_lock=只允许虎妖右脚掌接触裴胸口；forbid=新增第二击、裴长青突然恢复健康、虎妖伤口消失；identity_lock=CHAR_02、CHAR_03；attack_path=裴长青横刀自画左下向画右上斩向虎妖脖颈，虎妖右腿自画右中线蹬向画左前景裴胸口。；impact_frame=命中 5.0s：虎妖脚掌命中裴长青胸口，裴身体弓起，尘土和衣摆顺画左方向飞散。；contact_points=虎妖右脚掌、裴长青胸口；force_direction=虎妖画右→裴长青画左前景，力向右上到左下；recovery_beat=裴长青倒地后横刀落在姜月初可触及的位置，只用手部/衣袖/侧背轮廓表现她的惊恐反应；
专项模板约束：template=fight_exchange；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=frames2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.；
物理交互约束：读取 motion_control_manifest.json；level=required；manifest_path=出视频/第1集/control/Clip_06/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path；failure_modes=feature_melting,limb_fusion,weapon_contact_drift,body_interpenetration；degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态：reference_group=ready；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=中；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
近景升格守卫：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_02 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。；
尾端落幅保持：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=CHAR_01 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：裴长青强撑重伤捡刀，画左向画右扑击。；虎妖脚掌命中裴胸口，尘土和衣摆顺画左方向炸开，轻震屏。；裴长青倒飞砸地，横刀滑到画左前景；尘土扫过姜月初手背和灰褐衣袖，她只作侧背/OTS轮廓反应，不露清晰正脸。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或极缓推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务加速·碎切；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按action_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；内心戏镜头不得重复上一镜群像/妖魔/道具陈列；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 虎山神咧嘴，金黄凶眼亮起；裴长青脸色血色尽褪。; perform only 裴长青强撑重伤捡刀，画左向画右扑击。；虎妖脚掌命中裴胸口，尘土和衣摆顺画左方向炸开，轻震屏。；裴长青倒飞砸地，横刀滑到画左前景；尘土扫过姜月初手背和灰褐衣袖，她只作侧背/OTS轮廓反应，不露清晰正脸。; end on 裴长青倒飞砸在姜月初脚边，横刀滑到画左前景；尘土扫过姜月初手背和衣袖，她只以侧背/OTS轮廓接住反应，不露清晰正脸。; preserve required_presence=CHAR_02、CHAR_03、WEAPON_01; offscreen_presence=CHAR_01; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=裴长青看画右虎妖，虎妖看画左裴长青；姜月初只以画外/侧背视线目击脚边裴，不给清晰脸。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
inner-focus isolation: not an inner-focus shot; follow entity schedule.
director intent: 裴长青最后一击失败，证明正面武力路线断绝。; audience effect: 观众看到最强战力被一脚击溃，接受姜月初必须寻找非常规活路。.
character motion: 裴长青强撑重伤捡刀，画左向画右扑击。；虎妖脚掌命中裴胸口，尘土和衣摆顺画左方向炸开，轻震屏。；裴长青倒飞砸地，横刀滑到画左前景；尘土扫过姜月初手背和灰褐衣袖，她只作侧背/OTS轮廓反应，不露清晰正脸。; camera motion: 固定或极缓推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
close-up promotion guard: do not turn a small, distant, side/back, occluded, or non-primary anchor face into a clear close-up face unless a same-source close-up anchor/expression reference has passed full image QC.
ending reaction hold: 最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=CHAR_01 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
native audio policy: audio_intent=none; speech_policy=no_native_speech; compose_policy=discard.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已进入 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ 中文 prompt 已写首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不乱甩。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_06.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 07（时长 11.197s · EP01_CLIP07 · 百妖谱第一次开启）

**首帧**：`出图/第1集/图片/Clip07_first.png`
**尾帧**：`出图/第1集/图片/Clip07_end.png`
**锚帧1**：`出图/第1集/图片/Clip07_mid.png`（at_sec=3.0）
**场景**：LOC_01 荒野尸骸战场/姜月初主观视野
**剧本可看性合同**：dramatic_function=百妖谱第一次开启，给主角绝境中的唯一规则性生路。；audience_effect=观众获得金手指爽点，同时立刻想知道规则能否马上救命。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：百妖谱第一次开启，给主角绝境中的唯一规则性生路。
**起幅**：裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。
**落幅**：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。
**场面调度**：CU → POV 慢推；角色=CHAR_01、CHAR_02；资产=LOC_01, VFX_系统面板, WEAPON_01；轴线/视线=姜月初先看脚边裴长青，再看眼前金色面板。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 冷灰特写，尘土扑面，姜月初眼神濒临崩溃。；金色古卷空光幕从姜月初视野中展开，内部空白，金光映亮她的眼睛。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=姜月初绝望吐槽、金色古卷面板浮现、基础属性overlay出现、姜月初眼睛被金光照亮；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**专项镜头模板**：template=system_panel；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_02；binding=character_id_or_reference_group；assets=LOC_01、WEAPON_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；本镜绑定=CHAR_01、CHAR_02；资产引用注册层=LOC_01, VFX_系统面板, WEAPON_01。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。
- 出点：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。
- 转场：match_cut
- 连贯性：required_presence=CHAR_01、VFX_系统面板; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初先看脚边裴长青，再看眼前金色面板。; inner_focus=无

**continuity**：
- start_state：裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。
- action：冷灰特写，尘土扑面，姜月初眼神濒临崩溃。；金色古卷空光幕从姜月初视野中展开，内部空白，金光映亮她的眼睛。
- end_state：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。
- constraints：required_presence=CHAR_01、VFX_系统面板; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初先看脚边裴长青，再看眼前金色面板。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。
  action: 冷灰特写，尘土扑面，姜月初眼神濒临崩溃。；金色古卷空光幕从姜月初视野中展开，内部空白，金光映亮她的眼睛。
  end_state: 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。
  constraints: required_presence=CHAR_01、VFX_系统面板; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初先看脚边裴长青，再看眼前金色面板。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。
剧本可看性合同：dramatic_function=百妖谱第一次开启，给主角绝境中的唯一规则性生路。; audience_effect=观众获得金手指爽点，同时立刻想知道规则能否马上救命。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：百妖谱第一次开启，给主角绝境中的唯一规则性生路。;
起幅：裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。;
落幅：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。;
场面调度：CU → POV 慢推；角色槽位=CHAR_01、CHAR_02；资产ID=LOC_01, VFX_系统面板, WEAPON_01；
内心戏主体隔离：非内心戏/按在场链执行；
表演节拍：[0-30%] 承接首帧；[30-75%] 冷灰特写，尘土扑面，姜月初眼神濒临崩溃。；金色古卷空光幕从姜月初视野中展开，内部空白，金光映亮她的眼睛。；[75-100%] 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。;
运动精修约束：幅度=小到中；人物槽位不漂移；能量=克制；表情和视线先动，身体后动；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=姜月初绝望吐槽、金色古卷面板浮现、基础属性overlay出现、姜月初眼睛被金光照亮；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
专项模板约束：template=system_panel；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=image2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
物理交互约束：读取 motion_control_manifest.json；level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=大；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
近景升格守卫：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。；
尾端落幅保持：按 continuity.end_state 停住，不提前预演下一 Clip。；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：冷灰特写，尘土扑面，姜月初眼神濒临崩溃。；金色古卷空光幕从姜月初视野中展开，内部空白，金光映亮她的眼睛。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或缓慢推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务爽点·CU硬切；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按match_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；内心戏镜头不得重复上一镜群像/妖魔/道具陈列；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 裴长青倒飞砸在姜月初脚边，尘土扑到她脸上。; perform only 冷灰特写，尘土扑面，姜月初眼神濒临崩溃。；金色古卷空光幕从姜月初视野中展开，内部空白，金光映亮她的眼睛。; end on 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。; preserve required_presence=CHAR_01、VFX_系统面板; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初先看脚边裴长青，再看眼前金色面板。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
inner-focus isolation: not an inner-focus shot; follow entity schedule.
director intent: 百妖谱第一次开启，给主角绝境中的唯一规则性生路。; audience effect: 观众获得金手指爽点，同时立刻想知道规则能否马上救命。.
character motion: 冷灰特写，尘土扑面，姜月初眼神濒临崩溃。；金色古卷空光幕从姜月初视野中展开，内部空白，金光映亮她的眼睛。; camera motion: 固定或缓慢推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
close-up promotion guard: do not turn a small, distant, side/back, occluded, or non-primary anchor face into a clear close-up face unless a same-source close-up anchor/expression reference has passed full image QC.
ending reaction hold: hold the continuity.end_state until the cut and do not preview the next clip early.
native audio policy: audio_intent=none; speech_policy=no_native_speech; compose_policy=discard.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已进入 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ 中文 prompt 已写首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不乱甩。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_07.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 08（时长 8.588s · EP01_CLIP08 · 系统规则指向唯一活物）

**首帧**：`出图/第1集/图片/Clip08_first.png`
**尾帧**：`出图/第1集/图片/Clip08_end.png`
**锚帧1**：`出图/第1集/图片/Clip08_mid.png`（at_sec=4.0）
**场景**：LOC_01 荒野尸骸战场/百妖谱面板与横刀
**剧本可看性合同**：dramatic_function=把系统规则指向“斩杀生物”，并把可杀目标从虎妖转向裴长青。；audience_effect=观众意识到规则有代价，开始预判主角会不会突破道德底线。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：把系统规则指向“斩杀生物”，并把可杀目标从虎妖转向裴长青。
**起幅**：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。
**落幅**：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。
**场面调度**：过肩主观镜 → CU 手部；角色=CHAR_01、CHAR_02、CHAR_03；资产=LOC_01, VFX_系统面板, WEAPON_01；轴线/视线=姜月初看面板，再看虎妖，最后低头看裴长青。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 金色古卷面板悬浮稳定，姜月初侧脸被金光照亮，内部不要文字。；手部特写，灰褐囚袖，手指摸到黑色缠柄横刀，背景裴长青虚焦。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=规则overlay显示、姜月初手摸到横刀、姜月初视线从虎妖移到裴长青、面板稳定悬浮；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**专项镜头模板**：template=system_panel；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_02；binding=character_id_or_reference_group、character_id=CHAR_03；binding=character_id_or_reference_group；assets=LOC_01、WEAPON_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态：reference_group=ready；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼；本镜绑定=CHAR_01、CHAR_02、CHAR_03；资产引用注册层=LOC_01, VFX_系统面板, WEAPON_01。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。
- 出点：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。
- 转场：eyeline
- 连贯性：required_presence=CHAR_01、VFX_系统面板、WEAPON_01、CHAR_02; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看面板，再看虎妖，最后低头看裴长青。; inner_focus=无

**continuity**：
- start_state：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。
- action：金色古卷面板悬浮稳定，姜月初侧脸被金光照亮，内部不要文字。；手部特写，灰褐囚袖，手指摸到黑色缠柄横刀，背景裴长青虚焦。
- end_state：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。
- constraints：required_presence=CHAR_01、VFX_系统面板、WEAPON_01、CHAR_02; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看面板，再看虎妖，最后低头看裴长青。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。
  action: 金色古卷面板悬浮稳定，姜月初侧脸被金光照亮，内部不要文字。；手部特写，灰褐囚袖，手指摸到黑色缠柄横刀，背景裴长青虚焦。
  end_state: 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。
  constraints: required_presence=CHAR_01、VFX_系统面板、WEAPON_01、CHAR_02; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看面板，再看虎妖，最后低头看裴长青。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。
剧本可看性合同：dramatic_function=把系统规则指向“斩杀生物”，并把可杀目标从虎妖转向裴长青。; audience_effect=观众意识到规则有代价，开始预判主角会不会突破道德底线。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：把系统规则指向“斩杀生物”，并把可杀目标从虎妖转向裴长青。;
起幅：金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。;
落幅：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。;
场面调度：过肩主观镜 → CU 手部；角色槽位=CHAR_01、CHAR_02、CHAR_03；资产ID=LOC_01, VFX_系统面板, WEAPON_01；
内心戏主体隔离：非内心戏/按在场链执行；
表演节拍：[0-30%] 承接首帧；[30-75%] 金色古卷面板悬浮稳定，姜月初侧脸被金光照亮，内部不要文字。；手部特写，灰褐囚袖，手指摸到黑色缠柄横刀，背景裴长青虚焦。；[75-100%] 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。;
运动精修约束：幅度=小到中；人物槽位不漂移；能量=克制；表情和视线先动，身体后动；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=规则overlay显示、姜月初手摸到横刀、姜月初视线从虎妖移到裴长青、面板稳定悬浮；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
专项模板约束：template=system_panel；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=image2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
物理交互约束：读取 motion_control_manifest.json；level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态：reference_group=ready；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=大；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
近景升格守卫：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。；
尾端落幅保持：按 continuity.end_state 停住，不提前预演下一 Clip。；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：金色古卷面板悬浮稳定，姜月初侧脸被金光照亮，内部不要文字。；手部特写，灰褐囚袖，手指摸到黑色缠柄横刀，背景裴长青虚焦。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或缓慢推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务铺垫·长镜；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按eyeline服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；内心戏镜头不得重复上一镜群像/妖魔/道具陈列；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 金色百妖谱空面板稳定浮现，映亮姜月初瞳孔。; perform only 金色古卷面板悬浮稳定，姜月初侧脸被金光照亮，内部不要文字。；手部特写，灰褐囚袖，手指摸到黑色缠柄横刀，背景裴长青虚焦。; end on 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。; preserve required_presence=CHAR_01、VFX_系统面板、WEAPON_01、CHAR_02; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看面板，再看虎妖，最后低头看裴长青。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
inner-focus isolation: not an inner-focus shot; follow entity schedule.
director intent: 把系统规则指向“斩杀生物”，并把可杀目标从虎妖转向裴长青。; audience effect: 观众意识到规则有代价，开始预判主角会不会突破道德底线。.
character motion: 金色古卷面板悬浮稳定，姜月初侧脸被金光照亮，内部不要文字。；手部特写，灰褐囚袖，手指摸到黑色缠柄横刀，背景裴长青虚焦。; camera motion: 固定或缓慢推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
close-up promotion guard: do not turn a small, distant, side/back, occluded, or non-primary anchor face into a clear close-up face unless a same-source close-up anchor/expression reference has passed full image QC.
ending reaction hold: hold the continuity.end_state until the cut and do not preview the next clip early.
native audio policy: audio_intent=none; speech_policy=no_native_speech; compose_policy=discard.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已进入 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ 中文 prompt 已写首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不乱甩。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_08.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 09（时长 9.988s · EP01_CLIP09 · 刀尖抬起）

**首帧**：`出图/第1集/图片/Clip09_first.png`
**尾帧**：`出图/第1集/图片/Clip09_end.png`
**锚帧1**：`出图/第1集/图片/Clip09_mid.png`（at_sec=4.0）
**场景**：LOC_01 荒野尸骸战场/姜月初选择点
**剧本可看性合同**：dramatic_function=姜月初摸刀并权衡虎妖与裴长青，完成刺杀选择前的心理转折。；audience_effect=观众看见她不是冲动黑化，而是在无路可走中被规则逼到刀口。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：姜月初摸刀并权衡虎妖与裴长青，完成刺杀选择前的心理转折。
**起幅**：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。
**落幅**：刀身反光划过姜月初眼睛，她下定决心。
**场面调度**：LS 压迫远景 → CU 慢推；角色=CHAR_01、CHAR_02、CHAR_03；资产=LOC_01, WEAPON_01, VFX_系统面板；轴线/视线=姜月初低头看裴长青，虎妖从远景看姜月初。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 巨大虎妖画右远景压迫，姜月初画左前景握刀，裴长青倒在脚边。；姜月初手臂发抖，横刀刀尖慢慢抬起，金光和冷月同时映入眼睛。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=虎妖远景嘲弄、姜月初看裴长青、旁白点明唯一活物、姜月初握刀下决心；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**专项镜头模板**：template=dialogue_shot_reverse；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_02；binding=character_id_or_reference_group、character_id=CHAR_03；binding=character_id_or_reference_group；assets=LOC_01、WEAPON_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态：reference_group=ready；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼；本镜绑定=CHAR_01、CHAR_02、CHAR_03；资产引用注册层=LOC_01, WEAPON_01, VFX_系统面板。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。
- 出点：刀身反光划过姜月初眼睛，她下定决心。
- 转场：hard_cut
- 连贯性：required_presence=CHAR_01、CHAR_02、CHAR_03、WEAPON_01; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初低头看裴长青，虎妖从远景看姜月初。; inner_focus=无

**continuity**：
- start_state：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。
- action：巨大虎妖画右远景压迫，姜月初画左前景握刀，裴长青倒在脚边。；姜月初手臂发抖，横刀刀尖慢慢抬起，金光和冷月同时映入眼睛。
- end_state：刀身反光划过姜月初眼睛，她下定决心。
- constraints：required_presence=CHAR_01、CHAR_02、CHAR_03、WEAPON_01; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初低头看裴长青，虎妖从远景看姜月初。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。
  action: 巨大虎妖画右远景压迫，姜月初画左前景握刀，裴长青倒在脚边。；姜月初手臂发抖，横刀刀尖慢慢抬起，金光和冷月同时映入眼睛。
  end_state: 刀身反光划过姜月初眼睛，她下定决心。
  constraints: required_presence=CHAR_01、CHAR_02、CHAR_03、WEAPON_01; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初低头看裴长青，虎妖从远景看姜月初。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。
剧本可看性合同：dramatic_function=姜月初摸刀并权衡虎妖与裴长青，完成刺杀选择前的心理转折。; audience_effect=观众看见她不是冲动黑化，而是在无路可走中被规则逼到刀口。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：姜月初摸刀并权衡虎妖与裴长青，完成刺杀选择前的心理转折。;
起幅：姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。;
落幅：刀身反光划过姜月初眼睛，她下定决心。;
场面调度：LS 压迫远景 → CU 慢推；角色槽位=CHAR_01、CHAR_02、CHAR_03；资产ID=LOC_01, WEAPON_01, VFX_系统面板；
内心戏主体隔离：非内心戏/按在场链执行；
表演节拍：[0-30%] 承接首帧；[30-75%] 巨大虎妖画右远景压迫，姜月初画左前景握刀，裴长青倒在脚边。；姜月初手臂发抖，横刀刀尖慢慢抬起，金光和冷月同时映入眼睛。；[75-100%] 刀身反光划过姜月初眼睛，她下定决心。;
运动精修约束：幅度=小到中；人物槽位不漂移；能量=克制；表情和视线先动，身体后动；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=虎妖远景嘲弄、姜月初看裴长青、旁白点明唯一活物、姜月初握刀下决心；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
专项模板约束：template=dialogue_shot_reverse；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=image2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
物理交互约束：读取 motion_control_manifest.json；level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态：reference_group=ready；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=大；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
近景升格守卫：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。；
尾端落幅保持：按 continuity.end_state 停住，不提前预演下一 Clip。；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：巨大虎妖画右远景压迫，姜月初画左前景握刀，裴长青倒在脚边。；姜月初手臂发抖，横刀刀尖慢慢抬起，金光和冷月同时映入眼睛。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或缓慢推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务加速·碎切；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按hard_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；内心戏镜头不得重复上一镜群像/妖魔/道具陈列；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 姜月初视线从虎妖移到脚边裴长青，手摸到横刀刀柄。; perform only 巨大虎妖画右远景压迫，姜月初画左前景握刀，裴长青倒在脚边。；姜月初手臂发抖，横刀刀尖慢慢抬起，金光和冷月同时映入眼睛。; end on 刀身反光划过姜月初眼睛，她下定决心。; preserve required_presence=CHAR_01、CHAR_02、CHAR_03、WEAPON_01; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初低头看裴长青，虎妖从远景看姜月初。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
inner-focus isolation: not an inner-focus shot; follow entity schedule.
director intent: 姜月初摸刀并权衡虎妖与裴长青，完成刺杀选择前的心理转折。; audience effect: 观众看见她不是冲动黑化，而是在无路可走中被规则逼到刀口。.
character motion: 巨大虎妖画右远景压迫，姜月初画左前景握刀，裴长青倒在脚边。；姜月初手臂发抖，横刀刀尖慢慢抬起，金光和冷月同时映入眼睛。; camera motion: 固定或缓慢推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
close-up promotion guard: do not turn a small, distant, side/back, occluded, or non-primary anchor face into a clear close-up face unless a same-source close-up anchor/expression reference has passed full image QC.
ending reaction hold: hold the continuity.end_state until the cut and do not preview the next clip early.
native audio policy: audio_intent=none; speech_policy=no_native_speech; compose_policy=discard.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已进入 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ 中文 prompt 已写首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不乱甩。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_09.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 10（时长 6.540s · EP01_CLIP10 · 刺杀裴长青）

**首帧**：`出图/第1集/图片/Clip10_first.png`
**尾帧**：`出图/第1集/图片/Clip10_end.png`
**锚帧1**：`出图/第1集/图片/Clip10_mid.png`（at_sec=5.0）
**场景**：LOC_01 荒野尸骸战场/裴长青脚边
**剧本可看性合同**：dramatic_function=执行反选择：姜月初刺杀裴长青，把本集推到道德反转高潮。；audience_effect=观众受到“她真刺了”的冲击，追问系统是否认可、裴长青是否会死。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：执行反选择：姜月初刺杀裴长青，把本集推到道德反转高潮。
**起幅**：刀身反光划过姜月初眼睛，她下定决心。
**落幅**：长刀入胸，裴长青眼神僵住，BGM 抽空。
**场面调度**：ECU → CU 手部/眼睛；角色=CHAR_01、CHAR_02；资产=LOC_01, WEAPON_01, VFX_系统面板；轴线/视线=姜月初低头看裴长青但不敢对视；裴长青抬眼看姜月初。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 极近特写，姜月初嘴唇颤抖说抱歉，裴长青低角度困惑看她。；克制手部特写，横刀刀柄推进，随后切裴长青眼睛僵住，不做血腥喷溅。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；高光点只给一次明确动作
- 能量：蓄力后定住
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=姜月初低声道歉、裴长青困惑抬眼、姜月初短促刺下、裴长青瞳孔僵住；speed_curve=道歉慢→裴反问停半拍→刺下快→瞳孔僵住留白；spatial_path=姜月初俯身靠近裴长青，横刀沿短直线刺下；camera_path=固定近景，命中帧轻微快推，不环绕；readability_beats=先看清姜月初道歉、再看清裴长青不理解、最后看清刀柄推进和裴眼神僵住；degrade_plan=若接触镜不稳，拆为姜月初道歉脸部、横刀刀柄推进手部、裴长青眼睛僵住三个特写。；keyframe_plan=end=姜月初低头不看裴长青；impact_or_apex=横刀刀柄短促推进；intent_mid=裴长青困惑抬眼；result_or_recovery=裴长青瞳孔僵住；start=姜月初低头道歉；post_cue_points=aftershock_or_hold=1:22 只留风声和心跳；peak=5.0s 入肉声 + BGM抽空 + 2帧hit-stop；pre_peak=1:18 裴长青反问后静半拍；physics_guard=axis_lock=姜月初在画左上，裴长青在画右下，不交换位置；contact_lock=只允许横刀刀尖接触裴长青胸口，避免血腥扩散；forbid=新增搏斗、裴长青站起、虎妖插手本镜；identity_lock=CHAR_01、CHAR_02；attack_path=姜月初双手持横刀自画左上向画右下短促刺向裴长青胸口。；impact_frame=命中 5.0s：横刀没入裴长青胸口，画面只给刀柄推进和裴瞳孔僵住。；contact_points=横刀刀尖、裴长青胸口；force_direction=姜月初画左上→裴长青画右下；recovery_beat=BGM抽空，裴长青不动，姜月初低头进入集尾定格
**专项镜头模板**：template=fight_exchange；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=fight_exchange; primary_backend=seedance; fallback=dreamina; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_02；binding=character_id_or_reference_group；assets=LOC_01、WEAPON_01；motion_reference=allowed=True；library_path=生产数据/motion_reference_library.json；policy=use same sequence/shot_type approved reference when available；identity_preservation_plan=required_identity_anchors=face_shape、hairstyle、age_read、outfit_palette、named_character_screen_slot；reference_strategy=character_id_or_reference_group；motion_readability_allowances=prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups、allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot、keep first/end frame and registered reference group as identity truth when motion control needs simpler movement；fallback_plan=If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.；applies_to=fight_exchange；control_inputs=manifest_path=出视频/第1集/control/Clip_10/motion_control_manifest.json；required=True；required_inputs=pose_sequence、depth_sequence、instance_masks、contact_map、camera_path；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_10/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path；failure_modes=feature_melting,limb_fusion,weapon_contact_drift,body_interpenetration；degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；本镜绑定=CHAR_01、CHAR_02；资产引用注册层=LOC_01, WEAPON_01, VFX_系统面板。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：刀身反光划过姜月初眼睛，她下定决心。
- 出点：长刀入胸，裴长青眼神僵住，BGM 抽空。
- 转场：hard_cut
- 连贯性：required_presence=CHAR_01、CHAR_02、WEAPON_01; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初低头看裴长青但不敢对视；裴长青抬眼看姜月初。; inner_focus=无

**continuity**：
- start_state：刀身反光划过姜月初眼睛，她下定决心。
- action：极近特写，姜月初嘴唇颤抖说抱歉，裴长青低角度困惑看她。；克制手部特写，横刀刀柄推进，随后切裴长青眼睛僵住，不做血腥喷溅。
- end_state：长刀入胸，裴长青眼神僵住，BGM 抽空。
- constraints：required_presence=CHAR_01、CHAR_02、WEAPON_01; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初低头看裴长青但不敢对视；裴长青抬眼看姜月初。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 刀身反光划过姜月初眼睛，她下定决心。
  action: 极近特写，姜月初嘴唇颤抖说抱歉，裴长青低角度困惑看她。；克制手部特写，横刀刀柄推进，随后切裴长青眼睛僵住，不做血腥喷溅。
  end_state: 长刀入胸，裴长青眼神僵住，BGM 抽空。
  constraints: required_presence=CHAR_01、CHAR_02、WEAPON_01; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初低头看裴长青但不敢对视；裴长青抬眼看姜月初。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。
剧本可看性合同：dramatic_function=执行反选择：姜月初刺杀裴长青，把本集推到道德反转高潮。; audience_effect=观众受到“她真刺了”的冲击，追问系统是否认可、裴长青是否会死。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：执行反选择：姜月初刺杀裴长青，把本集推到道德反转高潮。;
起幅：刀身反光划过姜月初眼睛，她下定决心。;
落幅：长刀入胸，裴长青眼神僵住，BGM 抽空。;
场面调度：ECU → CU 手部/眼睛；角色槽位=CHAR_01、CHAR_02；资产ID=LOC_01, WEAPON_01, VFX_系统面板；
内心戏主体隔离：非内心戏/按在场链执行；
表演节拍：[0-30%] 承接首帧；[30-75%] 极近特写，姜月初嘴唇颤抖说抱歉，裴长青低角度困惑看她。；克制手部特写，横刀刀柄推进，随后切裴长青眼睛僵住，不做血腥喷溅。；[75-100%] 长刀入胸，裴长青眼神僵住，BGM 抽空。;
运动精修约束：幅度=小幅；高光点只给一次明确动作；能量=蓄力后定住；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=姜月初低声道歉、裴长青困惑抬眼、姜月初短促刺下、裴长青瞳孔僵住；speed_curve=道歉慢→裴反问停半拍→刺下快→瞳孔僵住留白；spatial_path=姜月初俯身靠近裴长青，横刀沿短直线刺下；camera_path=固定近景，命中帧轻微快推，不环绕；readability_beats=先看清姜月初道歉、再看清裴长青不理解、最后看清刀柄推进和裴眼神僵住；degrade_plan=若接触镜不稳，拆为姜月初道歉脸部、横刀刀柄推进手部、裴长青眼睛僵住三个特写。；keyframe_plan=end=姜月初低头不看裴长青；impact_or_apex=横刀刀柄短促推进；intent_mid=裴长青困惑抬眼；result_or_recovery=裴长青瞳孔僵住；start=姜月初低头道歉；post_cue_points=aftershock_or_hold=1:22 只留风声和心跳；peak=5.0s 入肉声 + BGM抽空 + 2帧hit-stop；pre_peak=1:18 裴长青反问后静半拍；physics_guard=axis_lock=姜月初在画左上，裴长青在画右下，不交换位置；contact_lock=只允许横刀刀尖接触裴长青胸口，避免血腥扩散；forbid=新增搏斗、裴长青站起、虎妖插手本镜；identity_lock=CHAR_01、CHAR_02；attack_path=姜月初双手持横刀自画左上向画右下短促刺向裴长青胸口。；impact_frame=命中 5.0s：横刀没入裴长青胸口，画面只给刀柄推进和裴瞳孔僵住。；contact_points=横刀刀尖、裴长青胸口；force_direction=姜月初画左上→裴长青画右下；recovery_beat=BGM抽空，裴长青不动，姜月初低头进入集尾定格；
专项模板约束：template=fight_exchange；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=frames2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.；
物理交互约束：读取 motion_control_manifest.json；level=required；manifest_path=出视频/第1集/control/Clip_10/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path；failure_modes=feature_melting,limb_fusion,weapon_contact_drift,body_interpenetration；degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=大；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
近景升格守卫：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。；
尾端落幅保持：按 continuity.end_state 停住，不提前预演下一 Clip。；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：极近特写，姜月初嘴唇颤抖说抱歉，裴长青低角度困惑看她。；克制手部特写，横刀刀柄推进，随后切裴长青眼睛僵住，不做血腥喷溅。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：缓慢推近，尾端定格；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务爽点·CU硬切；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按hard_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；内心戏镜头不得重复上一镜群像/妖魔/道具陈列；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 刀身反光划过姜月初眼睛，她下定决心。; perform only 极近特写，姜月初嘴唇颤抖说抱歉，裴长青低角度困惑看她。；克制手部特写，横刀刀柄推进，随后切裴长青眼睛僵住，不做血腥喷溅。; end on 长刀入胸，裴长青眼神僵住，BGM 抽空。; preserve required_presence=CHAR_01、CHAR_02、WEAPON_01; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初低头看裴长青但不敢对视；裴长青抬眼看姜月初。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
inner-focus isolation: not an inner-focus shot; follow entity schedule.
director intent: 执行反选择：姜月初刺杀裴长青，把本集推到道德反转高潮。; audience effect: 观众受到“她真刺了”的冲击，追问系统是否认可、裴长青是否会死。.
character motion: 极近特写，姜月初嘴唇颤抖说抱歉，裴长青低角度困惑看她。；克制手部特写，横刀刀柄推进，随后切裴长青眼睛僵住，不做血腥喷溅。; camera motion: 缓慢推近，尾端定格; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
close-up promotion guard: do not turn a small, distant, side/back, occluded, or non-primary anchor face into a clear close-up face unless a same-source close-up anchor/expression reference has passed full image QC.
ending reaction hold: hold the continuity.end_state until the cut and do not preview the next clip early.
native audio policy: audio_intent=none; speech_policy=no_native_speech; compose_policy=discard.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已进入 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ 中文 prompt 已写首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不乱甩。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_10.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 11（时长 2.053s · EP01_CLIP11 · 我只想活下去）

**首帧**：`出图/第1集/图片/Clip11_first.png`
**场景**：LOC_01 荒野尸骸战场/集尾定格
**剧本可看性合同**：dramatic_function=在刺杀后留白，锁住“我只想活下去”的人物底色和第2集悬念。；audience_effect=观众带着百妖谱是否生效、虎妖是否扑来、裴长青命运三重问题进入下一集。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：在刺杀后留白，锁住“我只想活下去”的人物底色和第2集悬念。
**起幅**：长刀入胸，裴长青眼神僵住，BGM 抽空。
**落幅**：姜月初低头说“我只想活下去”，虎妖阴影在背景停住。
**场面调度**：CU 缓慢推近；角色=CHAR_01、CHAR_02、CHAR_03；资产=LOC_01, WEAPON_01, VFX_系统面板；轴线/视线=姜月初低头不看镜头，虎妖阴影从背景压住她。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 缓慢推近姜月初低头特写，前景横刀刀柄，背景巨大虎妖阴影停住，只留风声心跳。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=长刀入胸后的静默停顿、姜月初低头说只想活下去、虎妖阴影在背景停住；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.
**专项镜头模板**：template=multi_character_same_frame；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=multi_character_same_frame; primary_backend=seedance; fallback=dreamina; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；consumption_mode=first_frame；native_timeline_frames=1；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_02；binding=character_id_or_reference_group、character_id=CHAR_03；binding=character_id_or_reference_group；assets=LOC_01、WEAPON_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；identity_preservation_plan=required_identity_anchors=face_shape、hairstyle、age_read、outfit_palette、named_character_screen_slot；reference_strategy=character_id_or_reference_group；motion_readability_allowances=prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups、allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot、keep first frame and registered reference group as identity truth when motion control needs simpler movement；fallback_plan=If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.；applies_to=multi_character_same_frame；control_inputs=manifest_path=出视频/第1集/control/Clip_11/motion_control_manifest.json；required=True；required_inputs=pose_sequence、depth_sequence、instance_masks；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；consumption_mode=first_frame；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=manual confirmation required before paid generation
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_11/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态：reference_group=ready；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼；本镜绑定=CHAR_01、CHAR_02、CHAR_03；资产引用注册层=LOC_01, WEAPON_01, VFX_系统面板。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：长刀入胸，裴长青眼神僵住，BGM 抽空。
- 出点：姜月初低头说“我只想活下去”，虎妖阴影在背景停住。
- 转场：hard_cut
- 连贯性：required_presence=CHAR_01、WEAPON_01、VFX_系统面板; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初低头不看镜头，虎妖阴影从背景压住她。; inner_focus=无

**continuity**：
- start_state：长刀入胸，裴长青眼神僵住，BGM 抽空。
- action：缓慢推近姜月初低头特写，前景横刀刀柄，背景巨大虎妖阴影停住，只留风声心跳。
- end_state：姜月初低头说“我只想活下去”，虎妖阴影在背景停住。
- constraints：required_presence=CHAR_01、WEAPON_01、VFX_系统面板; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初低头不看镜头，虎妖阴影从背景压住她。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 长刀入胸，裴长青眼神僵住，BGM 抽空。
  action: 缓慢推近姜月初低头特写，前景横刀刀柄，背景巨大虎妖阴影停住，只留风声心跳。
  end_state: 姜月初低头说“我只想活下去”，虎妖阴影在背景停住。
  constraints: required_presence=CHAR_01、WEAPON_01、VFX_系统面板; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初低头不看镜头，虎妖阴影从背景压住她。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。
剧本可看性合同：dramatic_function=在刺杀后留白，锁住“我只想活下去”的人物底色和第2集悬念。; audience_effect=观众带着百妖谱是否生效、虎妖是否扑来、裴长青命运三重问题进入下一集。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：在刺杀后留白，锁住“我只想活下去”的人物底色和第2集悬念。;
起幅：长刀入胸，裴长青眼神僵住，BGM 抽空。;
落幅：姜月初低头说“我只想活下去”，虎妖阴影在背景停住。;
场面调度：CU 缓慢推近；角色槽位=CHAR_01、CHAR_02、CHAR_03；资产ID=LOC_01, WEAPON_01, VFX_系统面板；
内心戏主体隔离：非内心戏/按在场链执行；
表演节拍：[0-30%] 承接首帧；[30-75%] 缓慢推近姜月初低头特写，前景横刀刀柄，背景巨大虎妖阴影停住，只留风声心跳。；[75-100%] 姜月初低头说“我只想活下去”，虎妖阴影在背景停住。;
运动精修约束：幅度=小到中；人物槽位不漂移；能量=克制；表情和视线先动，身体后动；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=长刀入胸后的静默停顿、姜月初低头说只想活下去、虎妖阴影在背景停住；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.；
专项模板约束：template=multi_character_same_frame；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=frames2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.；
物理交互约束：读取 motion_control_manifest.json；level=required；manifest_path=出视频/第1集/control/Clip_11/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态：reference_group=ready；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=中；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
近景升格守卫：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。；
尾端落幅保持：按 continuity.end_state 停住，不提前预演下一 Clip。；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：缓慢推近姜月初低头特写，前景横刀刀柄，背景巨大虎妖阴影停住，只留风声心跳。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或缓慢推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务留白·定格；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按hard_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；内心戏镜头不得重复上一镜群像/妖魔/道具陈列；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 长刀入胸，裴长青眼神僵住，BGM 抽空。; perform only 缓慢推近姜月初低头特写，前景横刀刀柄，背景巨大虎妖阴影停住，只留风声心跳。; end on 姜月初低头说“我只想活下去”，虎妖阴影在背景停住。; preserve required_presence=CHAR_01、WEAPON_01、VFX_系统面板; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初低头不看镜头，虎妖阴影从背景压住她。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
inner-focus isolation: not an inner-focus shot; follow entity schedule.
director intent: 在刺杀后留白，锁住“我只想活下去”的人物底色和第2集悬念。; audience effect: 观众带着百妖谱是否生效、虎妖是否扑来、裴长青命运三重问题进入下一集。.
character motion: 缓慢推近姜月初低头特写，前景横刀刀柄，背景巨大虎妖阴影停住，只留风声心跳。; camera motion: 固定或缓慢推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
close-up promotion guard: do not turn a small, distant, side/back, occluded, or non-primary anchor face into a clear close-up face unless a same-source close-up anchor/expression reference has passed full image QC.
ending reaction hold: hold the continuity.end_state until the cut and do not preview the next clip early.
native audio policy: audio_intent=none; speech_policy=no_native_speech; compose_policy=discard.
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已进入 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ 中文 prompt 已写首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不乱甩。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第1集/视频/Clip_11.mp4`；失败进废料并改 prompt/拆 Clip。
