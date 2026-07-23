# 第2集 视频 Clip prompt

## 本集留存承诺账本（script_quality_contract）

- R01: hook_id=EP02_OPEN；opened_at=EP02_CLIP01；payoff_clip=EP02_CLIP03；payoff_due=EP02_CLIP03；payoff_status=paid；promise=杀裴所得二十年能否救命；promise_type=opening_hook
- R02: hook_id=EP02_SYSTEM；opened_at=EP02_CLIP04；payoff_clip=EP02_CLIP05；payoff_due=EP02_CLIP05；payoff_status=paid；promise=百年道行收录虎山神会得到什么；promise_type=mid_hook
- R03: hook_id=EP02_TAIL；opened_at=EP02_CLIP08；payoff_due=后续摹影进阶剧情；promise=摹影继续进阶会把姜月初变成什么；promise_type=cliffhanger

## Clip 01（时长 12.606s · EP02_CLIP01 · 杀人余震与二十年到账）

**首帧**：`出图/第2集/图片/EP02_CLIP01_start.png`
**尾帧**：`出图/第2集/图片/Clip01_end.png`
**锚帧1**：`出图/第2集/图片/EP02_CLIP01_start_a1.png`（at_sec=3.6）
**锚帧2**：`出图/第2集/图片/EP02_CLIP01_start_a2.png`（at_sec=8.6）
**锚帧3**：`出图/第2集/图片/EP02_CLIP01_start_a3.png`（at_sec=12.0）
**场景**：尸骸荒野/夕/外
**剧本可看性合同**：dramatic_function=承接上集后果并兑现第一笔道行；audience_effect=惊惧→确认生机；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：承接上集后果并兑现第一笔道行
**起幅**：承接第1集：横刀刚刺入裴胸口，虎妖在东北背景
**落幅**：姜月初拔刀转向虎妖，横刀低垂，二十年已到账
**场面调度**：ECU固定 → MS微拉 → CU缓推；角色=CHAR_01、CHAR_02、BEAST_01；资产=LOC_01, WEAPON_横刀, VFX_百妖谱；轴线/视线=姜月初看右上虎妖；虎妖看左下姜月初
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：姜月初看右上虎妖；虎妖看左下姜月初；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 裴失焦眼、胸前刀柄、姜月初带血颤手与上方虎爪同屏；虎妖后景讥讽，姜月初中景不回头，裴局部留前景；无字百妖谱底框掠过眼前，后期叠二十年结算，姜月初眼神聚焦；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=按 storyboard shots 顺序执行；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**专项镜头模板**：template=none；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=reveal_reaction_chain; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=3；anchor_count=3；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第2集/图片/EP02_CLIP01_start.png；end_frame=出图/第2集/图片/Clip01_end.png；midframes=3；seam_mode=match_on_action；need_end_anchor=True；transition=动作接虎妖下扑；entry_exit=三者均承接上集在场，无新增或消失；出画/画外保留：CHAR_02、VFX_百妖谱；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=3；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**连续性链路 / Continuity Chain**：入点=第1集/Clip_08→第2集/Clip_01；scope=episode_boundary；policy=design_cut；strictness=mode_specific；transition=hard_cut_to_black_then_same-scene_reveal；以同一横刀、裴胸口位置与虎妖东北背景复位；from_end=横刀刚没入裴长青胸前衣料，生死与结算未知。；to_start=承接第1集：横刀刚刺入裴胸口，虎妖在东北背景；出点=第2集/Clip_01→第2集/Clip_02；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=动作接虎妖下扑；from_end=姜月初拔刀转向虎妖，横刀低垂，二十年已到账；to_start=姜月初拔刀转向虎妖，横刀低垂，二十年已到账
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=3；consumption_mode=native_multiframe；native_timeline_frames=5；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_02；binding=character_id_or_reference_group、binding=character_id_or_reference_group；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=base_video_then_post_lipsync；timing_basis=text_estimate_no_audio；performance_track_status=missing；requires_performance_audio_before_final=True；post_lipsync_required=True；base_video_only=True；base_video_mouth_policy=neutral_rest_no_visible_articulation；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=3；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**角色身份注册层**：CHAR_01：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；CHAR_02：reference_group=ready；registry_form=“濒死重伤态”；锚点句=年轻硬朗长方脸·浓直眉克制目光·黑发高束·墨黑暗赤镇魔司劲装·左臂骨折；BEAST_01：reference_group=ready；registry_form=“穿心复生态”；锚点句=真实虎首人形巨躯·琥珀竖瞳·右眉骨旧裂·胸前黑血洞·深褐破围腰；本镜绑定=CHAR_01、CHAR_02、BEAST_01；资产引用注册层=LOC_01, WEAPON_横刀, VFX_百妖谱。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：承接第1集：横刀刚刺入裴胸口，虎妖在东北背景
- 出点：姜月初拔刀转向虎妖，横刀低垂，二十年已到账
- 转场：动作接虎妖下扑
- 连贯性：required_presence=CHAR_01、CHAR_02、BEAST_01、WEAPON_横刀; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看右上虎妖；虎妖看左下姜月初; inner_focus=无

**continuity**：
- start_state：承接第1集：横刀刚刺入裴胸口，虎妖在东北背景
- action：裴失焦眼、胸前刀柄、姜月初带血颤手与上方虎爪同屏；虎妖后景讥讽，姜月初中景不回头，裴局部留前景；无字百妖谱底框掠过眼前，后期叠二十年结算，姜月初眼神聚焦
- end_state：姜月初拔刀转向虎妖，横刀低垂，二十年已到账
- constraints：required_presence=CHAR_01、CHAR_02、BEAST_01、WEAPON_横刀; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看右上虎妖；虎妖看左下姜月初
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut; story_span_sec=12.606; edit_target_sec=12.606; backend_request_sec=13.0; action_start_sec=0.25; action_end_sec=12.106; hold_end_sec=12.606; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=6e5f5ab7d12ae7b5c1f40bbfcc5ba91d9b94473139b89fb7d6569c5d8bd744d7
```text
以已提交首帧为视觉真值。 主动作：裴失焦眼、胸前刀柄、姜月初带血颤手与上方虎爪同屏；虎妖后景讥讽，姜月初中景不回头，裴局部留前景；无字百妖谱底框掠过眼前，后期叠二十年结算，姜月初眼神聚焦。 镜头：固定机位，锁定人物与戏内视线目标的相对关系；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：姜月初看右上虎妖；虎妖看左下姜月初；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：冷开场·危机钩子·长镜内多切。 时间：0.25-12.11秒完成主动作，持续保持落幅到12.61秒。12.61-13.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：姜月初拔刀转向虎妖，横刀低垂，二十年已到账。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已由完整合同承接，未塞入模型提交 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ compiler 已按 primary_backend / mode 生成唯一提交 prompt，语言与负向策略匹配后端。
- ✅ 在场链 required_presence/offscreen_presence/forbidden_presence 保留在完整合同与真实输入层。
- ✅ 接缝执行包 / 执行配方已进入完整合同，frame/reference/control/audio 输入与 route 一致。
- ✅ Continuity Chain 保留在完整合同和锚帧输入层；提交 prompt 只保留动作、运镜、节奏、落幅。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ 运镜动机：摄影机运动能说明揭示了什么新信息；说不清时使用固定机位，由表演、画内调度与剪辑承载张力。
- ✅ 视线表演：非 POV/破第四墙镜头已写清戏内视线目标与头眼方向，角色不迎着摄影机转脸。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不靠乱推、乱甩或随机环绕。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致；固定镜无漂移、呼吸式缩放或无意义重构，运动镜确实完成登记的叙事动机。
- [ ] 视线与迎镜头：抽起/中/止帧检查眼睛、鼻梁轴和头部朝向；非 POV/破第四墙镜角色始终看戏内对象，出现无动机正视镜头或迎镜头转脸即废料重跑。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第2集/视频/Clip_01.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 02（时长 12.076s · EP02_CLIP02 · 二十年尽付一刀）

**首帧**：`出图/第2集/图片/EP02_CLIP02_start.png`
**尾帧**：`出图/第2集/图片/EP02_CLIP02_preimpact.png`
**锚帧1**：`出图/第2集/图片/EP02_CLIP02_start_a1.png`（at_sec=6.04）
**场景**：尸骸荒野/夕/外
**剧本可看性合同**：dramatic_function=明确求生动机、资源代价与攻击起手；audience_effect=理解选择→屏息；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：明确求生动机、资源代价与攻击起手
**起幅**：姜月初拔刀转向虎妖，横刀低垂，二十年已到账
**落幅**：虎爪距姜月初额前尚有一臂，横刀刚进入横斩起点，双方尚未接触
**场面调度**：CU缓推 → LS短跟；角色=CHAR_01、BEAST_01；资产=LOC_01, WEAPON_横刀；轴线/视线=姜月初看虎妖胸颈破绽，虎妖看她持刀手
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：姜月初看虎妖胸颈破绽，虎妖看她持刀手；看向对手/目标；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：axis_id=AXIS_LOC_尸骸荒野_BEAST_01_VS_CHAR_01；A=BEAST_01，位置=BEAST_01，视线=看向对手/目标，不看镜头；B=CHAR_01，位置=CHAR_01，视线=看向对手/目标，不看镜头；站位模式=vertical_depth_9x16，A/B 不互换；OTS 前景肩部=焦点 BEAST_01；CHAR_01 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。 / 焦点 CHAR_01；BEAST_01 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。；coverage=clean singles + insert + side action master；镜头匹配=单人反打维持相近主体尺度；虎妖略低机位表现压迫，侧面镜回同一水平线；越轴策略=命中前不越轴；下一Clip错身后用虎首落地insert重建方向；缓冲镜=虎爪insert与侧面preimpact承担空间重建
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 姜月初压下颤抖，双手握刀，力量沿刀脊收束；虎妖右上扑下，姜月初左下起刀，停在将触未触；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=姜月初压下悔意、虎妖轻敌施压、双方接近、停在将触未触；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**专项镜头模板**：template=dialogue_shot_reverse；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=2；anchor_count=1；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第2集/图片/EP02_CLIP02_start.png；end_frame=出图/第2集/图片/EP02_CLIP02_preimpact.png；midframes=1；seam_mode=continuous_take_relay；need_end_anchor=True；transition=同动作相位接命中镜；entry_exit=裴转画外仍在原位；姜月初与虎妖沿原轴接近；出画/画外保留：CHAR_02、VFX_百妖谱；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**连续性链路 / Continuity Chain**：入点=第2集/Clip_01→第2集/Clip_02；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=动作接虎妖下扑；from_end=姜月初拔刀转向虎妖，横刀低垂，二十年已到账；to_start=姜月初拔刀转向虎妖，横刀低垂，二十年已到账；出点=第2集/Clip_02→第2集/Clip_03；scope=intra_episode；policy=relay；strictness=strict；transition=同动作相位接命中镜；from_end=虎爪距姜月初额前尚有一臂，横刀刚进入横斩起点，双方尚未接触；to_start=虎爪距姜月初额前尚有一臂，横刀刚进入横斩起点，双方尚未接触；boundary_frame=出图/第2集/图片/EP02_CLIP02_preimpact.png
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、binding=character_id_or_reference_group；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=base_video_then_post_lipsync；timing_basis=text_estimate_no_audio；performance_track_status=missing；requires_performance_audio_before_final=True；post_lipsync_required=True；base_video_only=True；base_video_mouth_policy=neutral_rest_no_visible_articulation；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**角色身份注册层**：CHAR_01：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；BEAST_01：reference_group=ready；registry_form=“穿心复生态”；锚点句=真实虎首人形巨躯·琥珀竖瞳·右眉骨旧裂·胸前黑血洞·深褐破围腰；本镜绑定=CHAR_01、BEAST_01；资产引用注册层=LOC_01, WEAPON_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=CHAR_02, VFX_百妖谱 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：姜月初拔刀转向虎妖，横刀低垂，二十年已到账
- 出点：虎爪距姜月初额前尚有一臂，横刀刚进入横斩起点，双方尚未接触
- 转场：同动作相位接命中镜
- 连贯性：required_presence=CHAR_01、BEAST_01、WEAPON_横刀; offscreen_presence=CHAR_02、VFX_百妖谱; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看虎妖胸颈破绽，虎妖看她持刀手; inner_focus=无

**continuity**：
- start_state：姜月初拔刀转向虎妖，横刀低垂，二十年已到账
- action：姜月初压下颤抖，双手握刀，力量沿刀脊收束；虎妖右上扑下，姜月初左下起刀，停在将触未触
- end_state：虎爪距姜月初额前尚有一臂，横刀刚进入横斩起点，双方尚未接触
- constraints：required_presence=CHAR_01、BEAST_01、WEAPON_横刀; offscreen_presence=CHAR_02、VFX_百妖谱; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看虎妖胸颈破绽，虎妖看她持刀手
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut; story_span_sec=12.076; edit_target_sec=12.076; backend_request_sec=13.0; action_start_sec=0.25; action_end_sec=11.576; hold_end_sec=12.076; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=b8eb98ab40dc3f9eb4817651ef9e1c9262835b84b86848a9757dad4a386e6adc
```text
以已提交首帧为视觉真值。 主动作：姜月初压下颤抖，双手握刀，力量沿刀脊收束；虎妖右上扑下，姜月初左下起刀，停在将触未触。 镜头：固定机位，用前中后景和人物入出画建立空间关系；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：姜月初看虎妖胸颈破绽，虎妖看她持刀手；看向对手/目标；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：加速·碎切。 时间：0.25-11.58秒完成主动作，持续保持落幅到12.08秒。12.08-13.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：虎爪距姜月初额前尚有一臂，横刀刚进入横斩起点，双方尚未接触。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已由完整合同承接，未塞入模型提交 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ compiler 已按 primary_backend / mode 生成唯一提交 prompt，语言与负向策略匹配后端。
- ✅ 在场链 required_presence/offscreen_presence/forbidden_presence 保留在完整合同与真实输入层。
- ✅ 接缝执行包 / 执行配方已进入完整合同，frame/reference/control/audio 输入与 route 一致。
- ✅ Continuity Chain 保留在完整合同和锚帧输入层；提交 prompt 只保留动作、运镜、节奏、落幅。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ 运镜动机：摄影机运动能说明揭示了什么新信息；说不清时使用固定机位，由表演、画内调度与剪辑承载张力。
- ✅ 视线表演：非 POV/破第四墙镜头已写清戏内视线目标与头眼方向，角色不迎着摄影机转脸。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不靠乱推、乱甩或随机环绕。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致；固定镜无漂移、呼吸式缩放或无意义重构，运动镜确实完成登记的叙事动机。
- [ ] 视线与迎镜头：抽起/中/止帧检查眼睛、鼻梁轴和头部朝向；非 POV/破第四墙镜角色始终看戏内对象，出现无动机正视镜头或迎镜头转脸即废料重跑。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第2集/视频/Clip_02.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 03（时长 7.390s · EP02_CLIP03 · 一刀断虎首）

**首帧**：`出图/第2集/图片/EP02_CLIP02_preimpact.png`
**尾帧**：`出图/第2集/图片/Clip03_end.png`
**锚帧1**：`出图/第2集/图片/EP02_CLIP03_impact.png`（at_sec=1.12）
**锚帧2**：`出图/第2集/图片/EP02_CLIP03_recovery.png`（at_sec=2.12）
**场景**：尸骸荒野/夕/外
**剧本可看性合同**：dramatic_function=动作兑现与数值反转；audience_effect=爆发→死寂→惊喜；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：动作兑现与数值反转
**起幅**：虎爪距姜月初额前尚有一臂，横刀刚进入横斩起点，双方尚未接触
**落幅**：姜月初单膝跪地，虎妖身首分离且已静止，百年结算完成
**场面调度**：CU固定+轻冲击 → MS固定 → CU结果镜；角色=CHAR_01、BEAST_01；资产=LOC_01, WEAPON_横刀；轴线/视线=姜月初视线锁定虎妖颈部破绽
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：姜月初视线锁定虎妖颈部破绽；看向画面下方/后景的戏内对象；看向画面上方/前景的戏内对象；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：axis_id=AXIS_LOC_尸骸荒野_CHAR_01_VS_BEAST_01；A=CHAR_01，位置=画面前景/高位/主动压场，按 storyboard 纵深站位锁定，视线=看向画面下方/后景的戏内对象，不看镜头；B=BEAST_01，位置=画面后景/低位/受压或压出，按 storyboard 纵深站位锁定，视线=看向画面上方/前景的戏内对象，不看镜头；站位模式=vertical_depth_9x16，A/B 不互换；OTS 前景肩部=焦点 CHAR_01；BEAST_01 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。 / 焦点 BEAST_01；CHAR_01 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。；coverage=establishing master + paired clean singles + true OTS with foreground shoulder + insert/cutaway + reaction shot；镜头匹配=A/B 反打保持相近焦段、镜头距离、镜头高度、光位和背景深度；权力高低只用轻微机位差表达。；越轴策略=默认禁止越轴；如剧情必须越轴，先用建立镜/中线移动/道具插入/空镜缓冲重新定向。；缓冲镜=建立镜/前景肩部/道具插入/反应近景负责重新定向；竖屏优先用纵深和上下高低位，不直接跳反轴。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 刀颈接触命中，头仍连接，接触后才开始分离；姜月初单膝落地喘息，横刀脱手插土；虎首后落，百年结算overlay出现；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=将触未触、横刀命中、双方错身、主角落势、虎首后落；speed_curve=将触未触慢→横斩快→命中顿两帧→错身快→结果留白；spatial_path=双方沿西南—东北轴相向，错身后各落原轴两侧；camera_path=侧面固定，命中轻推5%，不环绕；readability_beats=0.72s看清刀爪来路、1.12s看清接触点、2.12s看清主角落势、3.12s后才见虎首滚落；degrade_plan=动作生成不稳时降级为手部/刀爪特写 + 反应镜头 + 尘土/妖气遮挡，剧情结果不变。；keyframe_plan=start=0.0s将触未触；intent_mid=0.72s横斩加速；impact_or_apex=1.12s刀颈接触；result_or_recovery=2.12s姜月初单膝落地；end=7.39s虎首已落、百年结算；post_cue_points=pre_peak=0.97s抽真空0.15秒；peak=1.12s hit-stop两帧+低频impact；aftershock_or_hold=2.12-3.12s只留喘息与风声；physics_guard=identity=CHAR_01与BEAST_01身份不变；path=锁双方相向轴与横刀轨迹；contact_point=横刀刀刃接触虎妖颈部，不接触胸口或空气；forbid=命中前断首、刀穿身、多人增生、第二动作；attack_path=横刀由姜月初左下沿左→右水平略上扬轨迹切向虎妖颈部；impact_frame=1.12s 刀刃与虎颈接触、暖金刀弧遮挡切口，头仍在受力初相；contact_points=刀锋/狼爪/妖气/地面尘土按本镜 beats 发生接触或视觉撞点。；force_direction=刀力左下→右上；虎扑右上→左下；颈部受力向画右；recovery_beat=姜月初单膝跪地、横刀脱手插土、喘息一拍
**专项镜头模板**：template=fight_exchange；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=fight_exchange; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=3；anchor_count=2；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第2集/图片/EP02_CLIP02_preimpact.png；end_frame=出图/第2集/图片/Clip03_end.png；midframes=2；seam_mode=insert_cutaway；need_end_anchor=True；transition=虎血滴落接谱页墨线；entry_exit=虎妖由活体进入死亡态，不消失；姜月初仍在原场；出画/画外保留：BEAST_01、WEAPON_横刀；入画/现身：VFX_百妖谱；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=2；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**连续性链路 / Continuity Chain**：入点=第2集/Clip_02→第2集/Clip_03；scope=intra_episode；policy=relay；strictness=strict；transition=同动作相位接命中镜；from_end=虎爪距姜月初额前尚有一臂，横刀刚进入横斩起点，双方尚未接触；to_start=虎爪距姜月初额前尚有一臂，横刀刚进入横斩起点，双方尚未接触；boundary_frame=出图/第2集/图片/EP02_CLIP02_preimpact.png；出点=第2集/Clip_03→第2集/Clip_04；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=虎血滴落接谱页墨线；from_end=姜月初单膝跪地，虎妖身首分离且已静止，百年结算完成；to_start=姜月初单膝跪地，虎妖身首分离且已静止，百年结算完成
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=2；consumption_mode=native_multiframe；native_timeline_frames=4；reference_inputs=characters=character_id=CHAR_01；binding=reference_group、binding=reference_group；motion_reference=allowed=True；library_path=生产数据/motion_reference_library.json；policy=use same sequence/shot_type approved reference when available；identity_preservation_plan=required_identity_anchors=face_shape、hairstyle、age_read、outfit_palette、named_character_screen_slot；reference_strategy=reference_group；motion_readability_allowances=prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups、allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot、keep first/end frame and registered reference group as identity truth when motion control needs simpler movement；fallback_plan=If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.；applies_to=fight_exchange；control_inputs=manifest_path=出视频/第2集/control/Clip_03/motion_control_manifest.json；required=True；required_inputs=pose_sequence、depth_sequence、instance_masks、contact_map、camera_path；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=base_video_then_post_lipsync；timing_basis=text_estimate_no_audio；performance_track_status=missing；requires_performance_audio_before_final=True；post_lipsync_required=True；base_video_only=True；base_video_mouth_policy=neutral_rest_no_visible_articulation；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=2；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第2集/control/Clip_03/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path；failure_modes=feature_melting,limb_fusion,weapon_contact_drift,body_interpenetration；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**角色身份注册层**：CHAR_01：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；BEAST_01：reference_group=ready；registry_form=“穿心复生态”；锚点句=真实虎首人形巨躯·琥珀竖瞳·右眉骨旧裂·胸前黑血洞·深褐破围腰；本镜绑定=CHAR_01、BEAST_01；资产引用注册层=LOC_01, WEAPON_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=CHAR_02, VFX_百妖谱 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：虎爪距姜月初额前尚有一臂，横刀刚进入横斩起点，双方尚未接触
- 出点：姜月初单膝跪地，虎妖身首分离且已静止，百年结算完成
- 转场：虎血滴落接谱页墨线
- 连贯性：required_presence=CHAR_01、BEAST_01、WEAPON_横刀; offscreen_presence=CHAR_02、VFX_百妖谱; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初视线锁定虎妖颈部破绽; inner_focus=无

**continuity**：
- start_state：虎爪距姜月初额前尚有一臂，横刀刚进入横斩起点，双方尚未接触
- action：刀颈接触命中，头仍连接，接触后才开始分离；姜月初单膝落地喘息，横刀脱手插土；虎首后落，百年结算overlay出现
- end_state：姜月初单膝跪地，虎妖身首分离且已静止，百年结算完成
- constraints：required_presence=CHAR_01、BEAST_01、WEAPON_横刀; offscreen_presence=CHAR_02、VFX_百妖谱; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初视线锁定虎妖颈部破绽
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut; story_span_sec=7.39; edit_target_sec=7.39; backend_request_sec=8.0; action_start_sec=0.25; action_end_sec=6.89; hold_end_sec=7.39; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=29f22d0371b6443b8cc6168a1eeaf539f82f26e69e6504fbb3f93387f3c69207
```text
以已提交首帧为视觉真值。 主动作：刀颈接触命中，头仍连接，接触后才开始分离；姜月初单膝落地喘息，横刀脱手插土；虎首后落，百年结算overlay出现。 镜头：固定机位，锁定人物与戏内视线目标的相对关系；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：姜月初视线锁定虎妖颈部破绽；看向画面下方/后景的戏内对象；看向画面上方/前景的戏内对象；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：爽点·CU硬切。 时间：0.25-6.89秒完成主动作，持续保持落幅到7.39秒。7.39-8.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：姜月初单膝跪地，虎妖身首分离且已静止，百年结算完成。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已由完整合同承接，未塞入模型提交 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ compiler 已按 primary_backend / mode 生成唯一提交 prompt，语言与负向策略匹配后端。
- ✅ 在场链 required_presence/offscreen_presence/forbidden_presence 保留在完整合同与真实输入层。
- ✅ 接缝执行包 / 执行配方已进入完整合同，frame/reference/control/audio 输入与 route 一致。
- ✅ Continuity Chain 保留在完整合同和锚帧输入层；提交 prompt 只保留动作、运镜、节奏、落幅。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ 运镜动机：摄影机运动能说明揭示了什么新信息；说不清时使用固定机位，由表演、画内调度与剪辑承载张力。
- ✅ 视线表演：非 POV/破第四墙镜头已写清戏内视线目标与头眼方向，角色不迎着摄影机转脸。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不靠乱推、乱甩或随机环绕。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致；固定镜无漂移、呼吸式缩放或无意义重构，运动镜确实完成登记的叙事动机。
- [ ] 视线与迎镜头：抽起/中/止帧检查眼睛、鼻梁轴和头部朝向；非 POV/破第四墙镜角色始终看戏内对象，出现无动机正视镜头或迎镜头转脸即废料重跑。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第2集/视频/Clip_03.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 04（时长 5.270s · EP02_CLIP04 · 百年道行与收录选择）

**首帧**：`出图/第2集/图片/EP02_CLIP04_start.png`
**尾帧**：`出图/第2集/图片/EP02_CLIP04_end.png`
**场景**：百妖谱主观层/荒野叠化
**剧本可看性合同**：dramatic_function=抛出新规则并保留主角选择权；audience_effect=好奇→决定；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：抛出新规则并保留主角选择权
**起幅**：姜月初单膝跪地，虎妖身首分离且已静止，百年结算完成
**落幅**：姜月初明确选择收录，百妖谱开始吸收虎血
**场面调度**：CU固定；角色=CHAR_01；资产=LOC_01, VFX_百妖谱；轴线/视线=姜月初视线落在上中谱页
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：姜月初视线落在上中谱页；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 虎血滴化墨，无字谱页+后期问题文字，姜月初说收录；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=血滴化墨、空谱页展开、overlay问题、主角选择；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=先看百年入账、再看收录问题、最后看姜月初选择；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**专项镜头模板**：template=system_panel；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=general_motion; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**帧策略 / Frame Strategy**：strategy=first_last；reason=single_beat_with_required_end_state；shot_count=1；anchor_count=0；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第2集/图片/EP02_CLIP04_start.png；end_frame=出图/第2集/图片/EP02_CLIP04_end.png；midframes=0；seam_mode=continuous_take_relay；need_end_anchor=True；transition=墨线继续生长成虎形；entry_exit=现实尸体均画外保留，未消失；出画/画外保留：BEAST_01、WEAPON_横刀；入画/现身：VFX_百妖谱；入画/现身：VFX_墨虎谱影、WEAPON_横刀；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；need_end=True；consumption_mode=first_last；frame_strategy=first_last；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first+last frames as timeline endpoints；fallback=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**连续性链路 / Continuity Chain**：入点=第2集/Clip_03→第2集/Clip_04；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=虎血滴落接谱页墨线；from_end=姜月初单膝跪地，虎妖身首分离且已静止，百年结算完成；to_start=姜月初单膝跪地，虎妖身首分离且已静止，百年结算完成；出点=第2集/Clip_04→第2集/Clip_05；scope=intra_episode；policy=relay；strictness=strict；transition=墨线继续生长成虎形；from_end=姜月初明确选择收录，百妖谱开始吸收虎血；to_start=姜月初明确选择收录，百妖谱开始吸收虎血；boundary_frame=出图/第2集/图片/EP02_CLIP04_end.png
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；consumption_mode=first_last；native_timeline_frames=2；reference_inputs=characters=character_id=CHAR_01；binding=reference_group；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=base_video_then_post_lipsync；timing_basis=text_estimate_no_audio；performance_track_status=missing；requires_performance_audio_before_final=True；post_lipsync_required=True；base_video_only=True；base_video_mouth_policy=neutral_rest_no_visible_articulation；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；need_end=True；consumption_mode=first_last；frame_strategy=first_last；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first+last frames as timeline endpoints
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**角色身份注册层**：CHAR_01：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；本镜绑定=CHAR_01；资产引用注册层=LOC_01, VFX_百妖谱。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=微；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=CHAR_02, BEAST_01死亡态, BEAST_01, WEAPON_横刀, VFX_墨虎谱影 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：姜月初单膝跪地，虎妖身首分离且已静止，百年结算完成
- 出点：姜月初明确选择收录，百妖谱开始吸收虎血
- 转场：墨线继续生长成虎形
- 连贯性：required_presence=CHAR_01、VFX_百妖谱; offscreen_presence=CHAR_02、BEAST_01死亡态、BEAST_01、WEAPON_横刀、VFX_墨虎谱影; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初视线落在上中谱页; inner_focus=无

**continuity**：
- start_state：姜月初单膝跪地，虎妖身首分离且已静止，百年结算完成
- action：虎血滴化墨，无字谱页+后期问题文字，姜月初说收录
- end_state：姜月初明确选择收录，百妖谱开始吸收虎血
- constraints：required_presence=CHAR_01、VFX_百妖谱; offscreen_presence=CHAR_02、BEAST_01死亡态、BEAST_01、WEAPON_横刀、VFX_墨虎谱影; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初视线落在上中谱页
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=first_last; story_span_sec=5.27; edit_target_sec=5.27; backend_request_sec=6.0; action_start_sec=0.25; action_end_sec=4.77; hold_end_sec=5.27; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=efa332baf74223f88007f536d2c8d73db5a6e42599e5a339bec7e70bec25ad47
```text
从首帧连续运动到尾帧。 主动作：虎血滴化墨，无字谱页+后期问题文字，姜月初说收录。 镜头：固定机位，锁定构图、轴线与景别；人物和环境只在画内运动；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：姜月初视线落在上中谱页；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：加速·碎切。 时间：0.25-4.77秒完成主动作，持续保持落幅到5.27秒。5.27-6.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：姜月初明确选择收录，百妖谱开始吸收虎血。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已由完整合同承接，未塞入模型提交 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ compiler 已按 primary_backend / mode 生成唯一提交 prompt，语言与负向策略匹配后端。
- ✅ 在场链 required_presence/offscreen_presence/forbidden_presence 保留在完整合同与真实输入层。
- ✅ 接缝执行包 / 执行配方已进入完整合同，frame/reference/control/audio 输入与 route 一致。
- ✅ Continuity Chain 保留在完整合同和锚帧输入层；提交 prompt 只保留动作、运镜、节奏、落幅。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ 运镜动机：摄影机运动能说明揭示了什么新信息；说不清时使用固定机位，由表演、画内调度与剪辑承载张力。
- ✅ 视线表演：非 POV/破第四墙镜头已写清戏内视线目标与头眼方向，角色不迎着摄影机转脸。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不靠乱推、乱甩或随机环绕。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致；固定镜无漂移、呼吸式缩放或无意义重构，运动镜确实完成登记的叙事动机。
- [ ] 视线与迎镜头：抽起/中/止帧检查眼睛、鼻梁轴和头部朝向；非 POV/破第四墙镜角色始终看戏内对象，出现无动机正视镜头或迎镜头转脸即废料重跑。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第2集/视频/Clip_04.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 05（时长 9.207s · EP02_CLIP05 · 摹影虎山神获圆满刀法）

**首帧**：`出图/第2集/图片/EP02_CLIP04_end.png`
**尾帧**：`出图/第2集/图片/Clip05_end.png`
**锚帧1**：`出图/第2集/图片/EP02_CLIP04_end_a1.png`（at_sec=3.07）
**锚帧2**：`出图/第2集/图片/EP02_CLIP04_end_a2.png`（at_sec=6.14）
**场景**：百妖谱主观层/荒野叠化
**剧本可看性合同**：dramatic_function=系统母题视觉奇观与成长兑现；audience_effect=神秘→爽感；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：系统母题视觉奇观与成长兑现
**起幅**：姜月初明确选择收录，百妖谱开始吸收虎血
**落幅**：墨虎完成收录，姜月初伤势恢复并重新握住横刀
**场面调度**：CU缓推 → MCU固定；角色=CHAR_01；资产=LOC_01, VFX_百妖谱, VFX_墨虎谱影, WEAPON_横刀；轴线/视线=姜月初先看谱页后看持刀手
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：姜月初先看谱页后看持刀手；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 墨线成虎、虎眼亮，文字后期叠加；力量倒灌，伤势恢复，姜月初重新握刀；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=墨线成骨、虎形完整、虎眼apex、力量倒灌、握刀契合；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=看清七十五年扣除、看清虎形完成、看清圆满刀法结果；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**专项镜头模板**：template=system_panel；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=general_motion; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=2；anchor_count=2；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第2集/图片/EP02_CLIP04_end.png；end_frame=出图/第2集/图片/Clip05_end.png；midframes=2；seam_mode=graphic_match；need_end_anchor=True；transition=握刀手图形匹配到替裴合眼的手；entry_exit=系统主观层结束回现实；虎妖仅保持尸体画外；入画/现身：VFX_墨虎谱影、WEAPON_横刀；出画/画外保留：VFX_墨虎谱影；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=2；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**连续性链路 / Continuity Chain**：入点=第2集/Clip_04→第2集/Clip_05；scope=intra_episode；policy=relay；strictness=strict；transition=墨线继续生长成虎形；from_end=姜月初明确选择收录，百妖谱开始吸收虎血；to_start=姜月初明确选择收录，百妖谱开始吸收虎血；boundary_frame=出图/第2集/图片/EP02_CLIP04_end.png；出点=第2集/Clip_05→第2集/Clip_06；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=握刀手图形匹配到替裴合眼的手；from_end=墨虎完成收录，姜月初伤势恢复并重新握住横刀；to_start=墨虎完成收录，姜月初伤势恢复并重新握住横刀
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=2；consumption_mode=native_multiframe；native_timeline_frames=4；reference_inputs=characters=character_id=CHAR_01；binding=reference_group；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=base_video_then_post_lipsync；timing_basis=text_estimate_no_audio；performance_track_status=missing；requires_performance_audio_before_final=True；post_lipsync_required=True；base_video_only=True；base_video_mouth_policy=neutral_rest_no_visible_articulation；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=2；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**角色身份注册层**：CHAR_01：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；本镜绑定=CHAR_01；资产引用注册层=LOC_01, VFX_百妖谱, VFX_墨虎谱影, WEAPON_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=CHAR_02, BEAST_01死亡态 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：姜月初明确选择收录，百妖谱开始吸收虎血
- 出点：墨虎完成收录，姜月初伤势恢复并重新握住横刀
- 转场：握刀手图形匹配到替裴合眼的手
- 连贯性：required_presence=CHAR_01、VFX_百妖谱、VFX_墨虎谱影、WEAPON_横刀; offscreen_presence=CHAR_02、BEAST_01死亡态; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初先看谱页后看持刀手; inner_focus=无

**continuity**：
- start_state：姜月初明确选择收录，百妖谱开始吸收虎血
- action：墨线成虎、虎眼亮，文字后期叠加；力量倒灌，伤势恢复，姜月初重新握刀
- end_state：墨虎完成收录，姜月初伤势恢复并重新握住横刀
- constraints：required_presence=CHAR_01、VFX_百妖谱、VFX_墨虎谱影、WEAPON_横刀; offscreen_presence=CHAR_02、BEAST_01死亡态; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初先看谱页后看持刀手
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut; story_span_sec=9.207; edit_target_sec=9.207; backend_request_sec=10.0; action_start_sec=0.25; action_end_sec=8.707; hold_end_sec=9.207; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=5fe70343c76a05bd20e8dc885426892720a01c786b0a63a1d68b2e8a10f30edd
```text
以已提交首帧为视觉真值。 主动作：墨线成虎、虎眼亮，文字后期叠加；力量倒灌，伤势恢复，姜月初重新握刀。 镜头：固定机位，锁定构图、轴线与景别；人物和环境只在画内运动；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：姜月初先看谱页后看持刀手；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：爽点·CU硬切。 时间：0.25-8.71秒完成主动作，持续保持落幅到9.21秒。9.21-10.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：墨虎完成收录，姜月初伤势恢复并重新握住横刀。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已由完整合同承接，未塞入模型提交 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ compiler 已按 primary_backend / mode 生成唯一提交 prompt，语言与负向策略匹配后端。
- ✅ 在场链 required_presence/offscreen_presence/forbidden_presence 保留在完整合同与真实输入层。
- ✅ 接缝执行包 / 执行配方已进入完整合同，frame/reference/control/audio 输入与 route 一致。
- ✅ Continuity Chain 保留在完整合同和锚帧输入层；提交 prompt 只保留动作、运镜、节奏、落幅。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ 运镜动机：摄影机运动能说明揭示了什么新信息；说不清时使用固定机位，由表演、画内调度与剪辑承载张力。
- ✅ 视线表演：非 POV/破第四墙镜头已写清戏内视线目标与头眼方向，角色不迎着摄影机转脸。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不靠乱推、乱甩或随机环绕。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致；固定镜无漂移、呼吸式缩放或无意义重构，运动镜确实完成登记的叙事动机。
- [ ] 视线与迎镜头：抽起/中/止帧检查眼睛、鼻梁轴和头部朝向；非 POV/破第四墙镜角色始终看戏内对象，出现无动机正视镜头或迎镜头转脸即废料重跑。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第2集/视频/Clip_05.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 06（时长 10.520s · EP02_CLIP06 · 结算闻弦初境与二十五年余额）

**首帧**：`出图/第2集/图片/EP02_CLIP06_start.png`
**尾帧**：`出图/第2集/图片/EP02_CLIP06_end.png`
**锚帧1**：`出图/第2集/图片/EP02_CLIP06_start_a1.png`（at_sec=5.9）
**场景**：尸骸荒野/夕/外
**剧本可看性合同**：dramatic_function=锁定成长规则与跨集资源状态；audience_effect=理解规则→情绪回落；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：锁定成长规则与跨集资源状态
**起幅**：墨虎完成收录，姜月初伤势恢复并重新握住横刀
**落幅**：状态结算完成，姜月初松刀并看向裴尸体
**场面调度**：MCU固定 → CU轻拉；角色=CHAR_01；资产=LOC_01, VFX_百妖谱, WEAPON_横刀；轴线/视线=先看刀锋，后看画左下裴尸体
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：先看刀锋，后看画左下裴尸体；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 姜月初重新握刀并理解收录规则；极简状态overlay后收起，姜月初视线落向裴；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=按 storyboard shots 顺序执行；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**专项镜头模板**：template=none；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=2；anchor_count=1；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第2集/图片/EP02_CLIP06_start.png；end_frame=出图/第2集/图片/EP02_CLIP06_end.png；midframes=1；seam_mode=eyeline_cut；need_end_anchor=False；transition=视线切至裴尸体；entry_exit=百妖谱overlay收起；裴仍在原地画外；出画/画外保留：VFX_墨虎谱影；出画/画外保留：VFX_百妖谱；入画/现身：CHAR_02；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**连续性链路 / Continuity Chain**：入点=第2集/Clip_05→第2集/Clip_06；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=握刀手图形匹配到替裴合眼的手；from_end=墨虎完成收录，姜月初伤势恢复并重新握住横刀；to_start=墨虎完成收录，姜月初伤势恢复并重新握住横刀；出点=第2集/Clip_06→第2集/Clip_07；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=视线切至裴尸体；from_end=状态结算完成，姜月初松刀并看向裴尸体；to_start=状态结算完成，姜月初松刀并看向裴尸体
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=base_video_then_post_lipsync；timing_basis=text_estimate_no_audio；performance_track_status=missing；requires_performance_audio_before_final=True；post_lipsync_required=True；base_video_only=True；base_video_mouth_policy=neutral_rest_no_visible_articulation；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**角色身份注册层**：CHAR_01：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；本镜绑定=CHAR_01；资产引用注册层=LOC_01, VFX_百妖谱, WEAPON_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=CHAR_02, BEAST_01死亡态, VFX_墨虎谱影 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：墨虎完成收录，姜月初伤势恢复并重新握住横刀
- 出点：状态结算完成，姜月初松刀并看向裴尸体
- 转场：视线切至裴尸体
- 连贯性：required_presence=CHAR_01、WEAPON_横刀; offscreen_presence=CHAR_02、BEAST_01死亡态、VFX_墨虎谱影; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=先看刀锋，后看画左下裴尸体; inner_focus=无

**continuity**：
- start_state：墨虎完成收录，姜月初伤势恢复并重新握住横刀
- action：姜月初重新握刀并理解收录规则；极简状态overlay后收起，姜月初视线落向裴
- end_state：状态结算完成，姜月初松刀并看向裴尸体
- constraints：required_presence=CHAR_01、WEAPON_横刀; offscreen_presence=CHAR_02、BEAST_01死亡态、VFX_墨虎谱影; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=先看刀锋，后看画左下裴尸体
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut; story_span_sec=10.52; edit_target_sec=10.52; backend_request_sec=11.0; action_start_sec=0.25; action_end_sec=10.02; hold_end_sec=10.52; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=1f49f8e5161a14c0df2c181feedc6e893059bb4021d3855f9d5569028586e85a
```text
以已提交首帧为视觉真值。 主动作：姜月初重新握刀并理解收录规则；极简状态overlay后收起，姜月初视线落向裴。 镜头：固定机位，过肩/反打保持轴线、景别和视线目标；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：先看刀锋，后看画左下裴尸体；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：铺垫·长镜。 时间：0.25-10.02秒完成主动作，持续保持落幅到10.52秒。10.52-11.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：状态结算完成，姜月初松刀并看向裴尸体。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已由完整合同承接，未塞入模型提交 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ compiler 已按 primary_backend / mode 生成唯一提交 prompt，语言与负向策略匹配后端。
- ✅ 在场链 required_presence/offscreen_presence/forbidden_presence 保留在完整合同与真实输入层。
- ✅ 接缝执行包 / 执行配方已进入完整合同，frame/reference/control/audio 输入与 route 一致。
- ✅ Continuity Chain 保留在完整合同和锚帧输入层；提交 prompt 只保留动作、运镜、节奏、落幅。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ 运镜动机：摄影机运动能说明揭示了什么新信息；说不清时使用固定机位，由表演、画内调度与剪辑承载张力。
- ✅ 视线表演：非 POV/破第四墙镜头已写清戏内视线目标与头眼方向，角色不迎着摄影机转脸。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不靠乱推、乱甩或随机环绕。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致；固定镜无漂移、呼吸式缩放或无意义重构，运动镜确实完成登记的叙事动机。
- [ ] 视线与迎镜头：抽起/中/止帧检查眼睛、鼻梁轴和头部朝向；非 POV/破第四墙镜角色始终看戏内对象，出现无动机正视镜头或迎镜头转脸即废料重跑。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第2集/视频/Clip_06.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 07（时长 10.645s · EP02_CLIP07 · 替裴合眼与还命承诺）

**首帧**：`出图/第2集/图片/EP02_CLIP07_start.png`
**尾帧**：`出图/第2集/图片/Clip07_end.png`
**锚帧1**：`出图/第2集/图片/EP02_CLIP07_start_a1.png`（at_sec=3.55）
**锚帧2**：`出图/第2集/图片/EP02_CLIP07_start_a2.png`（at_sec=7.1）
**场景**：尸骸荒野/夕/外
**剧本可看性合同**：dramatic_function=爽点后情绪偿债与主角弧推进；audience_effect=共情与道德余震；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：爽点后情绪偿债与主角弧推进
**起幅**：状态结算完成，姜月初松刀并看向裴尸体
**落幅**：裴双眼已合，姜月初右手停在其额前，横刀放在右膝旁
**场面调度**：MS轻跟 → CU固定；角色=CHAR_01、CHAR_02；资产=LOC_01, WEAPON_横刀；轴线/视线=姜月初视线落在裴的双眼
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：姜月初视线落在裴的双眼；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 姜月初走回裴身边蹲下，横刀放在右膝旁；右手替裴合眼，前3/4脸悔意与苦涩自嘲；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=按 storyboard shots 顺序执行；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**专项镜头模板**：template=none；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=2；anchor_count=2；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第2集/图片/EP02_CLIP07_start.png；end_frame=出图/第2集/图片/Clip07_end.png；midframes=2；seam_mode=eyeline_cut；need_end_anchor=True；transition=姜月初抬眼看百妖谱虎影；entry_exit=姜月初走近并蹲下；裴死亡态不动；虎妖尸体保持画外；出画/画外保留：VFX_百妖谱；入画/现身：CHAR_02；出画/画外保留：CHAR_02、WEAPON_横刀；入画/现身：VFX_墨虎谱影、VFX_百妖谱；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=2；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**连续性链路 / Continuity Chain**：入点=第2集/Clip_06→第2集/Clip_07；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=视线切至裴尸体；from_end=状态结算完成，姜月初松刀并看向裴尸体；to_start=状态结算完成，姜月初松刀并看向裴尸体；出点=第2集/Clip_07→第2集/Clip_08；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=姜月初抬眼看百妖谱虎影；from_end=裴双眼已合，姜月初右手停在其额前，横刀放在右膝旁；to_start=裴双眼已合，姜月初右手停在其额前，横刀放在右膝旁
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=2；consumption_mode=native_multiframe；native_timeline_frames=4；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_02；binding=character_id_or_reference_group；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=base_video_then_post_lipsync；timing_basis=text_estimate_no_audio；performance_track_status=missing；requires_performance_audio_before_final=True；post_lipsync_required=True；base_video_only=True；base_video_mouth_policy=neutral_rest_no_visible_articulation；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=2；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**角色身份注册层**：CHAR_01：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；CHAR_02：reference_group=ready；registry_form=“濒死重伤态”；锚点句=年轻硬朗长方脸·浓直眉克制目光·黑发高束·墨黑暗赤镇魔司劲装·左臂骨折；本镜绑定=CHAR_01、CHAR_02；资产引用注册层=LOC_01, WEAPON_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=BEAST_01死亡态, VFX_百妖谱, VFX_墨虎谱影 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：状态结算完成，姜月初松刀并看向裴尸体
- 出点：裴双眼已合，姜月初右手停在其额前，横刀放在右膝旁
- 转场：姜月初抬眼看百妖谱虎影
- 连贯性：required_presence=CHAR_01、CHAR_02; offscreen_presence=BEAST_01死亡态、VFX_百妖谱、VFX_墨虎谱影; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初视线落在裴的双眼; inner_focus=无

**continuity**：
- start_state：状态结算完成，姜月初松刀并看向裴尸体
- action：姜月初走回裴身边蹲下，横刀放在右膝旁；右手替裴合眼，前3/4脸悔意与苦涩自嘲
- end_state：裴双眼已合，姜月初右手停在其额前，横刀放在右膝旁
- constraints：required_presence=CHAR_01、CHAR_02; offscreen_presence=BEAST_01死亡态、VFX_百妖谱、VFX_墨虎谱影; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初视线落在裴的双眼
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut; story_span_sec=10.645; edit_target_sec=10.645; backend_request_sec=11.0; action_start_sec=0.25; action_end_sec=10.145; hold_end_sec=10.645; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=468db0c4c148e5eefe14e57b83a0a01cff0f8166ae2ad2fad7804340eaabf973
```text
以已提交首帧为视觉真值。 主动作：姜月初走回裴身边蹲下，横刀放在右膝旁；右手替裴合眼，前3/4脸悔意与苦涩自嘲。 镜头：固定机位，锁定人物与戏内视线目标的相对关系；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：姜月初视线落在裴的双眼；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：留白·定格。 时间：0.25-10.14秒完成主动作，持续保持落幅到10.64秒。10.64-11.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：裴双眼已合，姜月初右手停在其额前，横刀放在右膝旁。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已由完整合同承接，未塞入模型提交 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ compiler 已按 primary_backend / mode 生成唯一提交 prompt，语言与负向策略匹配后端。
- ✅ 在场链 required_presence/offscreen_presence/forbidden_presence 保留在完整合同与真实输入层。
- ✅ 接缝执行包 / 执行配方已进入完整合同，frame/reference/control/audio 输入与 route 一致。
- ✅ Continuity Chain 保留在完整合同和锚帧输入层；提交 prompt 只保留动作、运镜、节奏、落幅。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ 运镜动机：摄影机运动能说明揭示了什么新信息；说不清时使用固定机位，由表演、画内调度与剪辑承载张力。
- ✅ 视线表演：非 POV/破第四墙镜头已写清戏内视线目标与头眼方向，角色不迎着摄影机转脸。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不靠乱推、乱甩或随机环绕。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致；固定镜无漂移、呼吸式缩放或无意义重构，运动镜确实完成登记的叙事动机。
- [ ] 视线与迎镜头：抽起/中/止帧检查眼睛、鼻梁轴和头部朝向；非 POV/破第四墙镜角色始终看戏内对象，出现无动机正视镜头或迎镜头转脸即废料重跑。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第2集/视频/Clip_07.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 08（时长 4.213s · EP02_CLIP08 · 摹影进阶会变成什么）

**首帧**：`出图/第2集/图片/EP02_CLIP08_start.png`
**尾帧**：`出图/第2集/图片/EP02_CLIP08_end.png`
**锚帧1**：`出图/第2集/图片/EP02_CLIP08_start_a1.png`（at_sec=2.5）
**场景**：尸骸荒野/百妖谱主观层
**剧本可看性合同**：dramatic_function=长线异化悬念与下一集身份转折接力；audience_effect=不安与追更欲；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：长线异化悬念与下一集身份转折接力
**起幅**：裴双眼已合，姜月初右手停在其额前，横刀放在右膝旁
**落幅**：墨虎双眼短亮，姜月初未得到答案，切黑
**场面调度**：CU缓推 → ECU固定；角色=CHAR_01；资产=LOC_01, VFX_百妖谱, VFX_墨虎谱影；轴线/视线=姜月初看上中虎影；虎影不看现实镜头而朝纸外正前
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：姜月初看上中虎影；虎影朝纸外正前；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 姜月初前3/4脸抬眼，旧金反光扫过眼睛；纸上墨虎双眼短亮，未离开谱页，硬切黑；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=面板底框浮现、overlay 信息刷新、角色反应承接；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**专项镜头模板**：template=system_panel；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=general_motion; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=2；anchor_count=1；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第2集/图片/EP02_CLIP08_start.png；end_frame=出图/第2集/图片/EP02_CLIP08_end.png；midframes=1；seam_mode=hard_cut；need_end_anchor=False；transition=硬切黑；entry_exit=全体实体均未物理离场；以切黑结束；出画/画外保留：CHAR_02、WEAPON_横刀；入画/现身：VFX_墨虎谱影、VFX_百妖谱；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**连续性链路 / Continuity Chain**：入点=第2集/Clip_07→第2集/Clip_08；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=姜月初抬眼看百妖谱虎影；from_end=裴双眼已合，姜月初右手停在其额前，横刀放在右膝旁；to_start=裴双眼已合，姜月初右手停在其额前，横刀放在右膝旁；出点=第1集/Clip_08→第2集/Clip_01；scope=episode_boundary；policy=design_cut；strictness=mode_specific；transition=hard_cut_to_black_then_same-scene_reveal；以同一横刀、裴胸口位置与虎妖东北背景复位；from_end=横刀刚没入裴长青胸前衣料，生死与结算未知。；to_start=承接第1集：横刀刚刺入裴胸口，虎妖在东北背景
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；binding=reference_group；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=base_video_then_post_lipsync；timing_basis=text_estimate_no_audio；performance_track_status=missing；requires_performance_audio_before_final=True；post_lipsync_required=True；base_video_only=True；base_video_mouth_policy=neutral_rest_no_visible_articulation；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**角色身份注册层**：CHAR_01：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；本镜绑定=CHAR_01；资产引用注册层=LOC_01, VFX_百妖谱, VFX_墨虎谱影。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=CHAR_02, BEAST_01死亡态, WEAPON_横刀 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：裴双眼已合，姜月初右手停在其额前，横刀放在右膝旁
- 出点：墨虎双眼短亮，姜月初未得到答案，切黑
- 转场：硬切黑
- 连贯性：required_presence=CHAR_01、VFX_墨虎谱影; offscreen_presence=CHAR_02、BEAST_01死亡态、WEAPON_横刀; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看上中虎影；虎影不看现实镜头而朝纸外正前; inner_focus=无

**continuity**：
- start_state：裴双眼已合，姜月初右手停在其额前，横刀放在右膝旁
- action：姜月初前3/4脸抬眼，旧金反光扫过眼睛；纸上墨虎双眼短亮，未离开谱页，硬切黑
- end_state：墨虎双眼短亮，姜月初未得到答案，切黑
- constraints：required_presence=CHAR_01、VFX_墨虎谱影; offscreen_presence=CHAR_02、BEAST_01死亡态、WEAPON_横刀; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=姜月初看上中虎影；虎影不看现实镜头而朝纸外正前
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut; story_span_sec=4.213; edit_target_sec=4.213; backend_request_sec=5.0; action_start_sec=0.25; action_end_sec=3.713; hold_end_sec=4.213; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=9ababce4b3369b3d622b16999fee9e2447480d0da0c6a8d4f8597f3ad7ed121e
```text
以已提交首帧为视觉真值。 主动作：姜月初前3/4脸抬眼，旧金反光扫过眼睛；纸上墨虎双眼短亮，未离开谱页，硬切黑。 镜头：固定机位，锁定屏幕/光幕平面和可读区域；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：姜月初看上中虎影；虎影朝纸外正前；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：留白·定格。 时间：0.25-3.71秒完成主动作，持续保持落幅到4.21秒。4.21-5.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：墨虎双眼短亮，姜月初未得到答案，切黑。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。
- ✅ 剧本可看性合同 dramatic_function / audience_effect 已由完整合同承接，未塞入模型提交 prompt。
- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。
- ✅ compiler 已按 primary_backend / mode 生成唯一提交 prompt，语言与负向策略匹配后端。
- ✅ 在场链 required_presence/offscreen_presence/forbidden_presence 保留在完整合同与真实输入层。
- ✅ 接缝执行包 / 执行配方已进入完整合同，frame/reference/control/audio 输入与 route 一致。
- ✅ Continuity Chain 保留在完整合同和锚帧输入层；提交 prompt 只保留动作、运镜、节奏、落幅。
- ✅ ④人物运动动作链明确，幅度与能量可控。
- ✅ ②镜头运动有结构化运镜词和速度。
- ✅ 运镜动机：摄影机运动能说明揭示了什么新信息；说不清时使用固定机位，由表演、画内调度与剪辑承载张力。
- ✅ 视线表演：非 POV/破第四墙镜头已写清戏内视线目标与头眼方向，角色不迎着摄影机转脸。
- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不靠乱推、乱甩或随机环绕。
- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。
- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。
- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。
- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。
- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。
- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。
- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。
- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致；固定镜无漂移、呼吸式缩放或无意义重构，运动镜确实完成登记的叙事动机。
- [ ] 视线与迎镜头：抽起/中/止帧检查眼睛、鼻梁轴和头部朝向；非 POV/破第四墙镜角色始终看戏内对象，出现无动机正视镜头或迎镜头转脸即废料重跑。
- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。
- [ ] 导演调度完成本镜意图，起幅/落幅可剪。
- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。
- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。
- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第2集/视频/Clip_08.mp4`；失败进废料并改 prompt/拆 Clip。
