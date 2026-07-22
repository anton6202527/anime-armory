# 第1集 视频 Clip prompt

## 本集留存承诺账本（script_quality_contract）

- R01: hook_id=OPEN_01；opened_at=EP01_CLIP01；payoff_clip=EP01_CLIP08；payoff_due=EP01_CLIP08；payoff_status=paid；promise=姜月初为何把刀对准人而不是妖；promise_type=opening_hook
- R02: hook_id=MID_01；opened_at=EP01_CLIP05；payoff_due=第2集；payoff_status=open；promise=穿心虎妖为何复生，二人能否逃走；promise_type=threat_reversal
- R03: hook_id=TAIL_01；opened_at=EP01_CLIP08；payoff_status=open；promise=裴长青是否死亡、姜月初能获得多少道行并如何面对虎妖；promise_type=cliffhanger

## Clip 01（时长 5.600s · EP01_CLIP01 · 刀口为何对准人）

**首帧**：`出图/第1集/图片/Clip01_first.png`
**尾帧**：`出图/第1集/图片/Clip01_end.png`
**锚帧1**：`出图/第1集/图片/EP01_CLIP01_a1.png`（at_sec=2.7）
**场景**：LOC_01/未来片段
**剧本可看性合同**：dramatic_function=先展示不可逆选择，再回到选择前。；audience_effect=立刻追问她为何不杀后景虎妖而杀人。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：先展示不可逆选择，再回到选择前。
**起幅**：未来片段，姜月初已持刀。
**落幅**：刀尖停在裴长青胸前，尚未落刀。
**场面调度**：85mm → 85mm；角色=CHAR_01/囚途残损态、CHAR_02/濒死态、BEAST_01/复生态焦外；资产=LOC_01, PROP_横刀；轴线/视线=姜月初向右下。
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 刀柄、发抖指节和衣料同轴。；染血脸与后景虎妖巨影，痛苦但已决定。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；只执行本镜主动作链
- 能量：克制匀速
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=按 storyboard shots 顺序执行；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.
**专项镜头模板**：template=none；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=general_motion; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=2；anchor_count=1；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第1集/图片/Clip01_first.png；end_frame=出图/第1集/图片/Clip01_end.png；midframes=1；seam_mode=intentional_discontinuity；need_end_anchor=True；transition=时间回切。；entry_exit=只交代刀、人、妖三角。；入画/现身：PROP_断刀、PROP_翻覆囚车；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=1；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=If action or identity fails twice, reroute to the nearest specialized shot type.
**连续性链路 / Continuity Chain**：入点=本镜为本集首镜且无前集边界，或 continuity_chain 未生成。；出点=第1集/Clip_01→第1集/Clip_02；scope=intra_episode；policy=intentional_discontinuity；strictness=mode_specific；transition=时间回切。；from_end=刀尖停在裴长青胸前，尚未落刀。；to_start=刀尖停在裴长青胸前，尚未落刀。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；form=囚途残损态；binding=native_identity_lock_required、character_id=CHAR_02；form=濒死态；binding=native_identity_lock_required、binding=native_identity_lock_required；assets=LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=performance_audio_first；timing_basis=final_voice；performance_track_status=final_ready；performance_audio_paths=合成/第1集/配音/line_00.wav；requires_performance_audio_before_final=True；base_video_mouth_policy=route_default；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=1；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.
**角色身份注册层**：CHAR_01/囚途残损态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；CHAR_02/濒死态：reference_group=ready；registry_form=“濒死重伤态”；锚点句=年轻硬朗长方脸·浓直眉克制目光·黑发高束·墨黑暗赤镇魔司劲装·左臂骨折；BEAST_01/复生态焦外：reference_group=ready；registry_form=“穿心复生态”；锚点句=真实虎首人形巨躯·琥珀竖瞳·右眉骨旧裂·胸前黑血洞·深褐破围腰；本镜绑定=CHAR_01/囚途残损态、CHAR_02/濒死态、BEAST_01/复生态焦外；资产引用注册层=LOC_01, PROP_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01/囚途残损态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/囚途残损态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=PROP_断刀, PROP_翻覆囚车 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：未来片段，姜月初已持刀。
- 出点：刀尖停在裴长青胸前，尚未落刀。
- 转场：时间回切。
- 连贯性：required_presence=CHAR_01、CHAR_02、PROP_横刀; offscreen_presence=PROP_断刀、PROP_翻覆囚车; forbidden_presence=主角妖化附体形态; eyeline=姜月初向右下。; inner_focus=无

**continuity**：
- start_state：未来片段，姜月初已持刀。
- action：刀柄、发抖指节和衣料同轴。；染血脸与后景虎妖巨影，痛苦但已决定。
- end_state：刀尖停在裴长青胸前，尚未落刀。
- constraints：required_presence=CHAR_01、CHAR_02、PROP_横刀; offscreen_presence=PROP_断刀、PROP_翻覆囚车; forbidden_presence=主角妖化附体形态; eyeline=姜月初向右下。
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-10.2; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut; story_span_sec=5.6; edit_target_sec=5.6; backend_request_sec=6.0; action_start_sec=0.25; action_end_sec=5.1; hold_end_sec=5.6; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=f9893403bdd0ae2a29435e5d02b150d02dfba5923ee6c5ee3b39f3ba32a308c7
```text
以已提交首帧为视觉真值。 主动作：刀柄、发抖指节和衣料同轴。；染血脸与后景虎妖巨影，痛苦但已决定。 镜头：固定或极缓推近。 节奏：冷开场·CU硬切。 时间：0.25-5.10秒完成主动作，持续保持落幅到5.60秒。5.60-6.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：刀尖停在裴长青胸前，尚未落刀。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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

## Clip 02（时长 14.920s · EP01_CLIP02 · 一炷香前的荒野死局）

**首帧**：`出图/第1集/图片/Clip02_first.png`
**尾帧**：`出图/第1集/图片/Clip02_end.png`
**锚帧1**：`出图/第1集/图片/EP01_CLIP02_face_reveal.png`（at_sec=1.0）
**锚帧2**：`出图/第1集/图片/EP01_CLIP02_a1.png`（at_sec=5.76）
**锚帧3**：`出图/第1集/图片/Clip02_end.png`（at_sec=11.2）
**场景**：LOC_01/一炷香前
**剧本可看性合同**：dramatic_function=建立穿越身份、尸场死局与裴长青仍能控场。；audience_effect=明白逃跑也未必能活。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：建立穿越身份、尸场死局与裴长青仍能控场。
**起幅**：刀尖停在裴长青胸前，尚未落刀。
**落幅**：断刀封路，姜月初停下。
**场面调度**：35mm → 85mm → 50mm；角色=CHAR_01/囚途残损态、CHAR_02/半跪重伤态、BEAST_01/伪死态；资产=LOC_01, PROP_断刀, PROP_横刀, PROP_翻覆囚车；轴线/视线=左看右/右看左
**正反打视频合同**：axis_id=AXIS_LOC_01_CHAR_01_囚途残损态_VS_CHAR_02_半跪重伤态；A=CHAR_01/囚途残损态，位置=画面前景/高位/主动压场，按 storyboard 纵深站位锁定，视线=看向画面下方/后景的戏内对象，不看镜头；B=CHAR_02/半跪重伤态，位置=画面后景/低位/受压或压出，按 storyboard 纵深站位锁定，视线=看向画面上方/前景的戏内对象，不看镜头；站位模式=vertical_depth_9x16，A/B 不互换；OTS 前景肩部=焦点 CHAR_01/囚途残损态；CHAR_02/半跪重伤态 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。 / 焦点 CHAR_02/半跪重伤态；CHAR_01/囚途残损态 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。；coverage=35mm双人空间建立 + 85mm单人反应 + 断刀插入镜；近景不让三张清晰脸同框；镜头匹配=A/B反打保持同一水平视平线与相近距离；裴长青半跪只通过主体高度体现；越轴策略=官道纵深为轴，默认不越轴；换侧前以尸场全景或断刀插入镜重建空间；缓冲镜=用尸场全景、断刀特写或翻覆囚车空镜作换侧缓冲
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 尸场空间一次建立。；姜月初摸到囚服，压住惊惧。；断刀封路，裴长青右前半跪。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=一炷香前的荒野死局、尸场空间一次建立。、姜月初摸到囚服，压住惊惧。、断刀封路，裴长青右前半跪。；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**专项镜头模板**：template=dialogue_shot_reverse；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=3；anchor_count=3；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第1集/图片/Clip02_first.png；end_frame=出图/第1集/图片/Clip02_end.png；midframes=3；seam_mode=eyeline_cut；need_end_anchor=False；transition=视线切裴长青。；entry_exit=姜月初退路被封。；入画/现身：PROP_断刀、PROP_翻覆囚车；出画/画外保留：BEAST_01、PROP_翻覆囚车；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=3；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**连续性链路 / Continuity Chain**：入点=第1集/Clip_01→第1集/Clip_02；scope=intra_episode；policy=intentional_discontinuity；strictness=mode_specific；transition=时间回切。；from_end=刀尖停在裴长青胸前，尚未落刀。；to_start=刀尖停在裴长青胸前，尚未落刀。；出点=第1集/Clip_02→第1集/Clip_03；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=视线切裴长青。；from_end=断刀封路，姜月初停下。；to_start=断刀封路，姜月初停下。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=2；consumption_mode=native_multiframe；native_timeline_frames=4；reference_inputs=characters=character_id=CHAR_01；form=囚途残损态；binding=native_identity_lock_required、character_id=CHAR_02；form=半跪重伤态；binding=native_identity_lock_required、binding=native_identity_lock_required；assets=LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=lipsync_condition_only；speech_policy=no_native_speech；audio_strategy=performance_audio_first；timing_basis=final_voice；performance_track_status=final_ready；performance_audio_paths=合成/第1集/配音/line_01.wav、合成/第1集/配音/line_02.wav、合成/第1集/配音/line_03.wav；requires_performance_audio_before_final=True；base_video_mouth_policy=route_default；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=3；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**角色身份注册层**：CHAR_01/囚途残损态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；CHAR_02/半跪重伤态：reference_group=ready；registry_form=“濒死重伤态”；锚点句=年轻硬朗长方脸·浓直眉克制目光·黑发高束·墨黑暗赤镇魔司劲装·左臂骨折；BEAST_01/伪死态：reference_group=ready；registry_form=“穿心复生态”；锚点句=真实虎首人形巨躯·琥珀竖瞳·右眉骨旧裂·胸前黑血洞·深褐破围腰；本镜绑定=CHAR_01/囚途残损态、CHAR_02/半跪重伤态、BEAST_01/伪死态；资产引用注册层=LOC_01, PROP_断刀, PROP_横刀, PROP_翻覆囚车。
**近景/反打身份锁定**：主焦点=CHAR_01/囚途残损态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/囚途残损态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=voice_conditioned_lipsync; risk=medium; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=配音只作口型条件，确认模型音轨未进入成片。
**衔接设计**：
- 入点：刀尖停在裴长青胸前，尚未落刀。
- 出点：断刀封路，姜月初停下。
- 转场：视线切裴长青。
- 连贯性：required_presence=CHAR_01、CHAR_02、PROP_断刀; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=左看右/右看左; inner_focus=无

**continuity**：
- start_state：刀尖停在裴长青胸前，尚未落刀。
- action：尸场空间一次建立。；姜月初摸到囚服，压住惊惧。；断刀封路，裴长青右前半跪。
- end_state：断刀封路，姜月初停下。
- constraints：required_presence=CHAR_01、CHAR_02、PROP_断刀; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=左看右/右看左
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-10.2; profile=zh_motion_first; backend=seedance; mode=voice_conditioned_lipsync; language=zh; native_audio_policy=lipsync_condition_only; frame_strategy=edit_cut; story_span_sec=14.92; edit_target_sec=14.92; backend_request_sec=15.0; action_start_sec=0.25; action_end_sec=14.42; hold_end_sec=14.92; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=861f3db068edb1f86e3e06d93c82414744c2ffd46336ad856ee891e88e96b803
```text
以已提交首帧为视觉真值。 主动作：尸场空间一次建立。；姜月初摸到囚服，压住惊惧。；断刀封路，裴长青右前半跪。 镜头：固定或缓慢推近。 节奏：铺垫·长镜。 时间：0.25-14.42秒完成主动作，持续保持落幅到14.92秒。14.92-15.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：断刀封路，姜月初停下。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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

## Clip 03（时长 10.960s · EP01_CLIP03 · 以脱籍换搀扶）

**首帧**：`出图/第1集/图片/Clip03_first.png`
**尾帧**：`出图/第1集/图片/Clip03_end.png`
**锚帧1**：`出图/第1集/图片/EP01_CLIP03_a1.png`（at_sec=5.99）
**锚帧2**：`出图/第1集/图片/Clip03_end.png`（at_sec=8.4）
**场景**：LOC_01
**剧本可看性合同**：dramatic_function=用刀、路引和距离把被迫结盟变成行动。；audience_effect=看见脱籍诱惑，也不完全信任裴长青。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：用刀、路引和距离把被迫结盟变成行动。
**起幅**：断刀封路，姜月初停下。
**落幅**：姜月初缩短到一臂半。
**场面调度**：85mm → 50mm → 85mm；角色=CHAR_01/囚途残损态、CHAR_02/半跪重伤态；资产=LOC_01, PROP_断刀, PROP_横刀；轴线/视线=左看右/右看左
**正反打视频合同**：axis_id=AXIS_LOC_01_CHAR_01_VS_CHAR_02；A=CHAR_01，位置=画左焦点，视线=看画右的戏内对象，不看镜头；B=CHAR_02，位置=画右焦点，视线=看画左的戏内对象，不看镜头；站位模式=left_right，A/B 不互换；OTS 前景肩部=焦点 CHAR_01；CHAR_02 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。 / 焦点 CHAR_02；CHAR_01 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。；coverage=85mm OTS/CU 交替 + 手部/断刀插入；反打只保一张清晰主脸；镜头匹配=A/B保持85mm与相近镜距；姜月初轻俯、裴长青低位的权力差有意保留；越轴策略=二人连线为轴，默认不越轴；若靠近则用手部插入镜缓冲；缓冲镜=断刀、路引或搀扶手部特写用于换侧前重建
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 姜月初警惕讥诮。；裴长青报身份与条件。；主角转为盘算。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=以脱籍换搀扶、姜月初警惕讥诮。、裴长青报身份与条件。、主角转为盘算。；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**专项镜头模板**：template=dialogue_shot_reverse；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=3；anchor_count=2；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第1集/图片/Clip03_first.png；end_frame=出图/第1集/图片/Clip03_end.png；midframes=2；seam_mode=l_cut；need_end_anchor=False；transition=裴长青声尾延续。；entry_exit=姜月初向右前靠近。；出画/画外保留：BEAST_01、PROP_翻覆囚车；出画/画外保留：PROP_断刀；入画/现身：BEAST_01；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=2；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**连续性链路 / Continuity Chain**：入点=第1集/Clip_02→第1集/Clip_03；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=视线切裴长青。；from_end=断刀封路，姜月初停下。；to_start=断刀封路，姜月初停下。；出点=第1集/Clip_03→第1集/Clip_04；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=裴长青声尾延续。；from_end=姜月初缩短到一臂半。；to_start=姜月初缩短到一臂半。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=2；consumption_mode=native_multiframe；native_timeline_frames=4；reference_inputs=characters=character_id=CHAR_01；form=囚途残损态；binding=native_identity_lock_required、character_id=CHAR_02；form=半跪重伤态；binding=native_identity_lock_required；assets=LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=lipsync_condition_only；speech_policy=no_native_speech；audio_strategy=performance_audio_first；timing_basis=final_voice；performance_track_status=final_ready；performance_audio_paths=合成/第1集/配音/line_04.wav、合成/第1集/配音/line_05.wav、合成/第1集/配音/line_06.wav；requires_performance_audio_before_final=True；base_video_mouth_policy=route_default；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=2；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**角色身份注册层**：CHAR_01/囚途残损态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；CHAR_02/半跪重伤态：reference_group=ready；registry_form=“濒死重伤态”；锚点句=年轻硬朗长方脸·浓直眉克制目光·黑发高束·墨黑暗赤镇魔司劲装·左臂骨折；本镜绑定=CHAR_01/囚途残损态、CHAR_02/半跪重伤态；资产引用注册层=LOC_01, PROP_断刀, PROP_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01/囚途残损态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/囚途残损态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=BEAST_01/伪死态, BEAST_01, PROP_翻覆囚车 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=voice_conditioned_lipsync; risk=medium; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=配音只作口型条件，确认模型音轨未进入成片。
**衔接设计**：
- 入点：断刀封路，姜月初停下。
- 出点：姜月初缩短到一臂半。
- 转场：裴长青声尾延续。
- 连贯性：required_presence=CHAR_01、CHAR_02、PROP_断刀; offscreen_presence=BEAST_01/伪死态、BEAST_01、PROP_翻覆囚车; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=左看右/右看左; inner_focus=无

**continuity**：
- start_state：断刀封路，姜月初停下。
- action：姜月初警惕讥诮。；裴长青报身份与条件。；主角转为盘算。
- end_state：姜月初缩短到一臂半。
- constraints：required_presence=CHAR_01、CHAR_02、PROP_断刀; offscreen_presence=BEAST_01/伪死态、BEAST_01、PROP_翻覆囚车; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=左看右/右看左
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-10.2; profile=zh_motion_first; backend=seedance; mode=voice_conditioned_lipsync; language=zh; native_audio_policy=lipsync_condition_only; frame_strategy=edit_cut; story_span_sec=10.96; edit_target_sec=10.96; backend_request_sec=11.0; action_start_sec=0.25; action_end_sec=10.46; hold_end_sec=10.96; trim_mode=none; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=b7a4a67eab2d3aa75ddcd84825d31fac31f0ca2e6e1d08d39ca44e220d4ddc43
```text
以已提交首帧为视觉真值。 主动作：姜月初警惕讥诮。；裴长青报身份与条件。；主角转为盘算。 镜头：固定或缓慢推近。 节奏：铺垫·长镜。 时间：0.25-10.46秒完成主动作，持续保持落幅到10.96秒。 结尾停稳在：姜月初缩短到一臂半。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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

## Clip 04（时长 9.400s · EP01_CLIP04 · 先活着再算账）

**首帧**：`出图/第1集/图片/Clip04_first.png`
**尾帧**：`出图/第1集/图片/Clip04_end.png`
**锚帧1**：`出图/第1集/图片/EP01_CLIP04_a1.png`（at_sec=4.2）
**场景**：LOC_01
**剧本可看性合同**：dramatic_function=主角基于生存算计接受交易。；audience_effect=短暂看见逃生路径。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：主角基于生存算计接受交易。
**起幅**：姜月初缩短到一臂半。
**落幅**：姜月初架起裴长青，面向画面下方。
**场面调度**：50mm → 85mm；角色=CHAR_01/囚途残损态、CHAR_02/重伤态、BEAST_01/伪死态；资产=LOC_01, PROP_横刀；轴线/视线=共同看逃生方向
**正反打视频合同**：axis_id=AXIS_LOC_01_CHAR_01_囚途残损态_VS_CHAR_02_重伤态；A=CHAR_01/囚途残损态，位置=画面前景/高位/主动压场，按 storyboard 纵深站位锁定，视线=看向画面下方/后景的戏内对象，不看镜头；B=CHAR_02/重伤态，位置=画面后景/低位/受压或压出，按 storyboard 纵深站位锁定，视线=看向画面上方/前景的戏内对象，不看镜头；站位模式=vertical_depth_9x16，A/B 不互换；OTS 前景肩部=焦点 CHAR_01/囚途残损态；CHAR_02/重伤态 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。 / 焦点 CHAR_02/重伤态；CHAR_01/囚途残损态 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。；coverage=50mm双人MS为主 + 单人反应 + 搀扶手部插入；虎妖保持焦外伪死；镜头匹配=反打保持50mm与相近镜距；架起动作后回双人MS建立新身高关系；越轴策略=二人行动方向为新轴，沿画面下方运动不越轴；缓冲镜=搀扶手部特写或双人离开全景用于动作接力与换侧缓冲
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 路引与镇魔司压实死局。；姜月初答应并架起裴长青。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=先活着再算账、路引与镇魔司压实死局。、姜月初答应并架起裴长青。；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**专项镜头模板**：template=dialogue_shot_reverse；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=2；anchor_count=1；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第1集/图片/Clip04_first.png；end_frame=出图/第1集/图片/Clip04_end.png；midframes=1；seam_mode=j_cut；need_end_anchor=False；transition=虎妖咳声先入。；entry_exit=二人向下方走数步。；出画/画外保留：PROP_断刀；入画/现身：BEAST_01；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=1；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**连续性链路 / Continuity Chain**：入点=第1集/Clip_03→第1集/Clip_04；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=裴长青声尾延续。；from_end=姜月初缩短到一臂半。；to_start=姜月初缩短到一臂半。；出点=第1集/Clip_04→第1集/Clip_05；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=虎妖咳声先入。；from_end=姜月初架起裴长青，面向画面下方。；to_start=姜月初架起裴长青，面向画面下方。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；form=囚途残损态；binding=native_identity_lock_required、character_id=CHAR_02；form=重伤态；binding=native_identity_lock_required、binding=native_identity_lock_required；assets=LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=lipsync_condition_only；speech_policy=no_native_speech；audio_strategy=performance_audio_first；timing_basis=final_voice；performance_track_status=final_ready；performance_audio_paths=合成/第1集/配音/line_07.wav、合成/第1集/配音/line_08.wav；requires_performance_audio_before_final=True；base_video_mouth_policy=route_default；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=1；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**角色身份注册层**：CHAR_01/囚途残损态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；CHAR_02/重伤态：reference_group=ready；registry_form=“濒死重伤态”；锚点句=年轻硬朗长方脸·浓直眉克制目光·黑发高束·墨黑暗赤镇魔司劲装·左臂骨折；BEAST_01/伪死态：reference_group=ready；registry_form=“穿心复生态”；锚点句=真实虎首人形巨躯·琥珀竖瞳·右眉骨旧裂·胸前黑血洞·深褐破围腰；本镜绑定=CHAR_01/囚途残损态、CHAR_02/重伤态、BEAST_01/伪死态；资产引用注册层=LOC_01, PROP_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01/囚途残损态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/囚途残损态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=PROP_断刀 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=voice_conditioned_lipsync; risk=medium; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=配音只作口型条件，确认模型音轨未进入成片。
**衔接设计**：
- 入点：姜月初缩短到一臂半。
- 出点：姜月初架起裴长青，面向画面下方。
- 转场：虎妖咳声先入。
- 连贯性：required_presence=CHAR_01、CHAR_02、BEAST_01; offscreen_presence=PROP_断刀; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=共同看逃生方向; inner_focus=无

**continuity**：
- start_state：姜月初缩短到一臂半。
- action：路引与镇魔司压实死局。；姜月初答应并架起裴长青。
- end_state：姜月初架起裴长青，面向画面下方。
- constraints：required_presence=CHAR_01、CHAR_02、BEAST_01; offscreen_presence=PROP_断刀; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=共同看逃生方向
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-10.2; profile=zh_motion_first; backend=seedance; mode=voice_conditioned_lipsync; language=zh; native_audio_policy=lipsync_condition_only; frame_strategy=edit_cut; story_span_sec=9.4; edit_target_sec=9.4; backend_request_sec=10.0; action_start_sec=0.25; action_end_sec=8.9; hold_end_sec=9.4; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=dd2c0bb439e1f62c3eee4c8128f36cfd5b57c88f730bf6de4046765c74c2869d
```text
以已提交首帧为视觉真值。 主动作：路引与镇魔司压实死局。；姜月初答应并架起裴长青。 镜头：固定或缓慢推近。 节奏：加速·关系落点。 时间：0.25-8.90秒完成主动作，持续保持落幅到9.40秒。9.40-10.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：姜月初架起裴长青，面向画面下方。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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

## Clip 05（时长 7.880s · EP01_CLIP05 · 死妖咳嗽站起）

**首帧**：`出图/第1集/图片/Clip05_first.png`
**尾帧**：`出图/第1集/图片/Clip05_end.png`
**锚帧1**：`出图/第1集/图片/EP01_CLIP05_a1.png`（at_sec=3.87）
**锚帧2**：`出图/第1集/图片/EP01_CLIP05_a2.png`（at_sec=7.74）
**场景**：LOC_01
**剧本可看性合同**：dramatic_function=推翻逃生路径，升级为绝对死局。；audience_effect=镇魔卫判断失效，体量差成立。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：推翻逃生路径，升级为绝对死局。
**起幅**：姜月初架起裴长青，面向画面下方。
**落幅**：虎妖站立逼近，裴长青拾横刀准备搏命。
**场面调度**：35mm → 85mm → 50mm；角色=CHAR_01/囚途残损态、CHAR_02/重伤搀扶态、BEAST_01/复生态；资产=LOC_01, PROP_横刀；轴线/视线=二人向上后景
**正反打视频合同**：axis_id=AXIS_LOC_01_CHAR_01_VS_CHAR_02；A=CHAR_01，位置=画左下人物层，视线=看画右的戏内对象，不看镜头；B=CHAR_02，位置=画右下反应层，视线=看画左的戏内对象，不看镜头；站位模式=left_right，A/B 不互换；OTS 前景肩部=焦点 CHAR_01；CHAR_02 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。 / 焦点 CHAR_02；CHAR_01 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。；coverage=establishing master + paired clean singles + true OTS with foreground shoulder + insert/cutaway + reaction shot；镜头匹配=A/B 反打保持相近焦段、镜头距离、镜头高度、光位和背景深度；权力高低只用轻微机位差表达。；越轴策略=默认禁止越轴；如剧情必须越轴，先用建立镜/中线移动/道具插入/空镜缓冲重新定向。；缓冲镜=双人建立镜、道具插入、反应近景或空镜负责重新定向；不得直接跳反轴近景。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 胸伤仍在，虎妖由伏到立。；裴长青镇定崩塌。；虎妖逼近，裴长青喊快逃并单臂探向横刀。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；只执行本镜主动作链
- 能量：克制匀速
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=死妖咳嗽站起、胸伤仍在，虎妖由伏到立。、裴长青镇定崩塌。、虎妖逼近，裴长青喊快逃并拾横刀准备搏命。；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.
**专项镜头模板**：template=reveal_reaction_chain；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=reveal_reaction_chain; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; degrade_plan=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=3；anchor_count=2；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第1集/图片/Clip05_first.png；end_frame=出图/第1集/图片/Clip05_end.png；midframes=2；seam_mode=match_on_action；need_end_anchor=True；transition=拾刀动作接下一镜冲锋。；entry_exit=虎妖从上后景向下。；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=2；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.
**连续性链路 / Continuity Chain**：入点=第1集/Clip_04→第1集/Clip_05；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=虎妖咳声先入。；from_end=姜月初架起裴长青，面向画面下方。；to_start=姜月初架起裴长青，面向画面下方。；出点=第1集/Clip_05→第1集/Clip_06；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=拾刀动作接下一镜冲锋。；from_end=虎妖站立逼近，裴长青拾横刀准备搏命。；to_start=虎妖站立逼近，裴长青拾起横刀准备搏命。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=2；consumption_mode=native_multiframe；native_timeline_frames=4；reference_inputs=characters=character_id=CHAR_01；form=囚途残损态；binding=native_identity_lock_required、character_id=CHAR_02；form=重伤搀扶态；binding=native_identity_lock_required、binding=native_identity_lock_required；assets=LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=performance_audio_first；timing_basis=final_voice；performance_track_status=final_ready；performance_audio_paths=合成/第1集/配音/line_09.wav、合成/第1集/配音/line_10.wav、合成/第1集/配音/line_11.wav、合成/第1集/配音/line_12.wav；requires_performance_audio_before_final=True；base_video_mouth_policy=route_default；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=2；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.
**角色身份注册层**：CHAR_01/囚途残损态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；CHAR_02/重伤搀扶态：reference_group=ready；registry_form=“濒死重伤态”；锚点句=年轻硬朗长方脸·浓直眉克制目光·黑发高束·墨黑暗赤镇魔司劲装·左臂骨折；BEAST_01/复生态：reference_group=ready；registry_form=“穿心复生态”；锚点句=真实虎首人形巨躯·琥珀竖瞳·右眉骨旧裂·胸前黑血洞·深褐破围腰；本镜绑定=CHAR_01/囚途残损态、CHAR_02/重伤搀扶态、BEAST_01/复生态；资产引用注册层=LOC_01, PROP_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01/囚途残损态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/囚途残损态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：姜月初架起裴长青，面向画面下方。
- 出点：虎妖站立逼近，裴长青拾横刀准备搏命。
- 转场：拾刀动作接下一镜冲锋。
- 连贯性：required_presence=CHAR_01、CHAR_02、BEAST_01; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=二人向上后景; inner_focus=无

**continuity**：
- start_state：姜月初架起裴长青，面向画面下方。
- action：胸伤仍在，虎妖由伏到立。；裴长青镇定崩塌。；虎妖逼近，裴长青喊快逃并单臂探向横刀。
- end_state：虎妖站立逼近，裴长青拾横刀准备搏命。
- constraints：required_presence=CHAR_01、CHAR_02、BEAST_01; offscreen_presence=无; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=二人向上后景
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-10.2; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut; story_span_sec=7.88; edit_target_sec=7.88; backend_request_sec=8.0; action_start_sec=0.25; action_end_sec=7.38; hold_end_sec=7.88; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=27b9b0a562cf71bcb068301956ce298700a2a1eca2bfe07cb3ffee092c726c85
```text
以已提交首帧为视觉真值。 主动作：胸伤仍在，虎妖由伏到立。；裴长青镇定崩塌。；虎妖逼近，裴长青喊快逃并单臂探向横刀。 镜头：固定或极缓推近。 节奏：反转·压迫升级。 时间：0.25-7.38秒完成主动作，持续保持落幅到7.88秒。7.88-8.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：虎妖站立逼近，裴长青拾横刀准备搏命。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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

## Clip 06（时长 8.800s · EP01_CLIP06 · 虎口最后威胁）

**首帧**：`出图/第1集/图片/Clip06_first.png`
**尾帧**：`出图/第1集/图片/Clip06_end.png`
**锚帧1**：`出图/第1集/图片/EP01_CLIP06_a1.png`（at_sec=3.0）
**锚帧2**：`出图/第1集/图片/EP01_CLIP06_a2.png`（at_sec=4.8）
**锚帧3**：`出图/第1集/图片/EP01_CLIP06_a3.png`（at_sec=6.6）
**场景**：LOC_01
**剧本可看性合同**：dramatic_function=让系统在马上被吃的压力下出现。；audience_effect=选择窗口压到几秒。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：让系统在马上被吃的压力下出现。
**起幅**：虎妖站立逼近，裴长青拾起横刀准备搏命。
**落幅**：裴长青被踢至姜月初脚边濒死，横刀脱手；虎妖继续逼近。
**场面调度**：50mm → 85mm → 50mm → 50mm→85mm；角色=CHAR_01/囚途残损态、CHAR_02/搏命冲锋至倒地濒死态、BEAST_01/复生态；资产=LOC_01, PROP_横刀；轴线/视线=上看虎妖再右下看裴
**正反打视频合同**：axis_id=AXIS_LOC_01_CHAR_01_VS_CHAR_02；A=CHAR_01，位置=画左中景主角，视线=看画右的戏内对象，不看镜头；B=CHAR_02，位置=画右下倒地，视线=看画左的戏内对象，不看镜头；站位模式=left_right，A/B 不互换；OTS 前景肩部=焦点 CHAR_01；CHAR_02 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。 / 焦点 CHAR_02；CHAR_01 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。；coverage=establishing master + paired clean singles + true OTS with foreground shoulder + insert/cutaway + reaction shot；镜头匹配=A/B 反打保持相近焦段、镜头距离、镜头高度、光位和背景深度；权力高低只用轻微机位差表达。；越轴策略=默认禁止越轴；如剧情必须越轴，先用建立镜/中线移动/道具插入/空镜缓冲重新定向。；缓冲镜=双人建立镜、道具插入、反应近景或空镜负责重新定向；不得直接跳反轴近景。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 裴长青单臂拾横刀，从右下向左上搏命冲锋。；虎妖正面一脚命中裴长青躯干，衣料受力清楚，无猎奇伤口。；裴长青与横刀沿原轴跌回姜月初脚边，她失声喊名。；虎妖伪善威胁；姜月初近景绝望反问凭什么又让我去死。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；只执行本镜主动作链
- 能量：克制匀速
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=裴长青单臂拾起横刀，沿右下至左上轴线搏命冲锋、虎妖正面抬腿，短促一脚命中裴长青躯干、裴长青与横刀沿原路跌回姜月初脚边、虎妖低机位威胁逼近，姜月初近景喊名并意识到自己又要死；speed_curve=拾刀短停→裴快速冲锋→虎妖极短爆发正蹬→裴失重飞退→落地后半拍静止。；spatial_path=裴从右下到左上，再沿同轴回落至姜月初脚边；虎妖保持左上高位。；camera_path=50mm短跟冲锋→85mm接触特写→50mm落地关系镜→低机位虎妖威胁与姜月初反应硬切。；readability_beats=拾刀搏命、虎足命中、人刀同落、姜月初喊名、虎妖威胁、我想活；degrade_plan=拆成拾刀、冲锋、接触、落地、威胁、反应六个短镜；接触帧用定格关键帧，不做端到端三人同框生成。；keyframe_plan=1.2秒锁拾刀起势，3.0秒锁踢击接触，4.8秒锁人刀落地，末尾锁虎妖威胁与姜月初绝望。；post_cue_points=踢击接触加低频闷响、落地后抽空半拍环境声、虎妖台词保持近压迫混响；physics_guard=裴的飞退方向、身体折线、衣摆与横刀惯性必须统一；虎妖支撑腿落地稳定，不悬浮。；attack_path=裴长青自画面右下持刀向左上冲锋；虎妖由左上向右下正蹬，双方力线正面对冲。；impact_frame=约3.0秒，虎足命中裴长青躯干，衣料压缩与身体折线同帧，不展示猎奇伤口。；contact_points=虎妖足底与裴长青躯干衣料、裴长青落地时肩背与泥地、脱手横刀与泥地；force_direction=虎妖踢击由左上指向右下，裴长青飞退与衣摆惯性同向。；recovery_beat=裴长青在姜月初脚边濒死喘息，横刀脱手落在两人之间。
**专项镜头模板**：template=fight_exchange；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=fight_exchange; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=4；anchor_count=3；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第1集/图片/Clip06_first.png；end_frame=出图/第1集/图片/Clip06_end.png；midframes=3；seam_mode=match_on_action；need_end_anchor=True；transition=动作匹配后外压硬切内在规则。；entry_exit=裴持刀冲锋后被踢回，横刀落在姜月初脚边；虎妖继续向下逼近。；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=3；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**连续性链路 / Continuity Chain**：入点=第1集/Clip_05→第1集/Clip_06；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=拾刀动作接下一镜冲锋。；from_end=虎妖站立逼近，裴长青拾横刀准备搏命。；to_start=虎妖站立逼近，裴长青拾起横刀准备搏命。；出点=第1集/Clip_06→第1集/Clip_07；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=动作匹配后外压硬切内在规则。；from_end=裴长青被踢至姜月初脚边濒死，横刀脱手；虎妖继续逼近。；to_start=裴长青濒死落在姜月初脚边，横刀脱手，虎妖继续逼近；姜月初尚未持刀。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=3；consumption_mode=native_multiframe；native_timeline_frames=5；reference_inputs=characters=character_id=CHAR_01；form=囚途残损态；binding=native_identity_lock_required、character_id=CHAR_02；form=搏命冲锋至倒地濒死态；binding=native_identity_lock_required、binding=native_identity_lock_required；assets=LOC_01；motion_reference=allowed=True；library_path=生产数据/motion_reference_library.json；policy=use same sequence/shot_type approved reference when available；identity_preservation_plan=required_identity_anchors=face_shape、hairstyle、age_read、outfit_palette、named_character_screen_slot；reference_strategy=native_identity_lock_required；motion_readability_allowances=prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups、allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot、keep first/end frame and registered reference group as identity truth when motion control needs simpler movement；fallback_plan=If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.；applies_to=fight_exchange；control_inputs=manifest_path=出视频/第1集/control/Clip_06/motion_control_manifest.json；required=True；required_inputs=pose_sequence、depth_sequence、instance_masks、contact_map、camera_path；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=lipsync_condition_only；speech_policy=no_native_speech；audio_strategy=performance_audio_first；timing_basis=final_voice；performance_track_status=final_ready；performance_audio_paths=合成/第1集/配音/line_13.wav、合成/第1集/配音/line_14.wav、合成/第1集/配音/line_15.wav；requires_performance_audio_before_final=True；base_video_mouth_policy=route_default；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=3；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_06/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path；failure_modes=feature_melting,limb_fusion,weapon_contact_drift,body_interpenetration；degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**角色身份注册层**：CHAR_01/囚途残损态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；CHAR_02/搏命冲锋至倒地濒死态：reference_group=ready；registry_form=“濒死重伤态”；锚点句=年轻硬朗长方脸·浓直眉克制目光·黑发高束·墨黑暗赤镇魔司劲装·左臂骨折；BEAST_01/复生态：reference_group=ready；registry_form=“穿心复生态”；锚点句=真实虎首人形巨躯·琥珀竖瞳·右眉骨旧裂·胸前黑血洞·深褐破围腰；本镜绑定=CHAR_01/囚途残损态、CHAR_02/搏命冲锋至倒地濒死态、BEAST_01/复生态；资产引用注册层=LOC_01, PROP_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01/囚途残损态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/囚途残损态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=VFX_百妖谱, VFX_系统面板 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=voice_conditioned_lipsync; risk=medium; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=配音只作口型条件，确认模型音轨未进入成片。
**衔接设计**：
- 入点：虎妖站立逼近，裴长青拾起横刀准备搏命。
- 出点：裴长青被踢至姜月初脚边濒死，横刀脱手；虎妖继续逼近。
- 转场：动作匹配后外压硬切内在规则。
- 连贯性：required_presence=CHAR_01、CHAR_02、BEAST_01; offscreen_presence=VFX_百妖谱、VFX_系统面板; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=上看虎妖再右下看裴; inner_focus=无

**continuity**：
- start_state：虎妖站立逼近，裴长青拾起横刀准备搏命。
- action：裴长青单臂拾横刀，从右下向左上搏命冲锋。；虎妖正面一脚命中裴长青躯干，衣料受力清楚，无猎奇伤口。；裴长青与横刀沿原轴跌回姜月初脚边，她失声喊名。；虎妖伪善威胁；姜月初近景绝望反问凭什么又让我去死。
- end_state：裴长青被踢至姜月初脚边濒死，横刀脱手；虎妖继续逼近。
- constraints：required_presence=CHAR_01、CHAR_02、BEAST_01; offscreen_presence=VFX_百妖谱、VFX_系统面板; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=上看虎妖再右下看裴
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-10.2; profile=zh_motion_first; backend=seedance; mode=voice_conditioned_lipsync; language=zh; native_audio_policy=lipsync_condition_only; frame_strategy=edit_cut; story_span_sec=8.8; edit_target_sec=8.8; backend_request_sec=9.0; action_start_sec=0.25; action_end_sec=8.3; hold_end_sec=8.8; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=402133fb65637c045de2d76db866c8090857c56c64b839f43636b8510e53d495
```text
以已提交首帧为视觉真值。 主动作：裴长青单臂拾横刀，从右下向左上搏命冲锋。；虎妖正面一脚命中裴长青躯干，衣料受力清楚，无猎奇伤口。；裴长青与横刀沿原轴跌回姜月初脚边，她失声喊名。；虎妖伪善威胁；姜月初近景绝望反问凭什么又让我去死。 镜头：固定或极缓推近。 节奏：加速·危机逼近。 时间：0.25-8.30秒完成主动作，持续保持落幅到8.80秒。8.80-9.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：裴长青被踢至姜月初脚边濒死，横刀脱手；虎妖继续逼近。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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

## Clip 07（时长 7.060s · EP01_CLIP07 · 百妖谱给出残酷选择）

**首帧**：`出图/第1集/图片/Clip07_first.png`
**尾帧**：`出图/第1集/图片/Clip07_end.png`
**锚帧1**：`出图/第1集/图片/EP01_CLIP07_a1.png`（at_sec=3.6）
**锚帧2**：`出图/第1集/图片/EP01_CLIP07_a2.png`（at_sec=6.2）
**场景**：LOC_01/主观系统层
**剧本可看性合同**：dramatic_function=只解释改变当下决定的规则，把斩杀指向唯一活人。；audience_effect=先兴奋再意识到伦理代价。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：只解释改变当下决定的规则，把斩杀指向唯一活人。
**起幅**：裴长青濒死落在姜月初脚边，横刀脱手，虎妖继续逼近；姜月初尚未持刀。
**落幅**：主角理解规则，视线落在裴与横刀。
**场面调度**：85mm → 50mm → 85mm；角色=CHAR_01/囚途残损态、CHAR_02/濒死态、BEAST_01/复生态；资产=LOC_01, PROP_横刀, VFX_百妖谱, VFX_系统面板；轴线/视线=上后景→右下
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 空白卷轴展开，黑墨游走。；规则与虎爪交替。；看向右下裴长青。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=百妖谱给出残酷选择、空白卷轴展开，黑墨游走。、规则与虎爪交替。、看向右下裴长青。；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**专项镜头模板**：template=system_panel；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=voice_conditioned_lipsync; native_audio_policy=lipsync_condition_only; identity_requirement=native_identity_lock_required; degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=3；anchor_count=2；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第1集/图片/Clip07_first.png；end_frame=出图/第1集/图片/Clip07_end.png；midframes=2；seam_mode=eyeline_cut；need_end_anchor=True；transition=视线切递刀手。；entry_exit=现实位置不重置。；入画/现身：VFX_百妖谱、VFX_系统面板；出画/画外保留：VFX_百妖谱；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=2；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**连续性链路 / Continuity Chain**：入点=第1集/Clip_06→第1集/Clip_07；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=动作匹配后外压硬切内在规则。；from_end=裴长青被踢至姜月初脚边濒死，横刀脱手；虎妖继续逼近。；to_start=裴长青濒死落在姜月初脚边，横刀脱手，虎妖继续逼近；姜月初尚未持刀。；出点=第1集/Clip_07→第1集/Clip_08；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=视线切递刀手。；from_end=主角理解规则，视线落在裴与横刀。；to_start=主角理解规则，视线落在裴与横刀。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=2；consumption_mode=native_multiframe；native_timeline_frames=4；reference_inputs=characters=character_id=CHAR_01；form=囚途残损态；binding=native_identity_lock_required、character_id=CHAR_02；form=濒死态；binding=native_identity_lock_required、binding=native_identity_lock_required；assets=LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=lipsync_condition_only；speech_policy=no_native_speech；audio_strategy=performance_audio_first；timing_basis=final_voice；performance_track_status=final_ready；performance_audio_paths=合成/第1集/配音/line_16.wav、合成/第1集/配音/line_17.wav；requires_performance_audio_before_final=True；base_video_mouth_policy=route_default；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=2；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
**角色身份注册层**：CHAR_01/囚途残损态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；CHAR_02/濒死态：reference_group=ready；registry_form=“濒死重伤态”；锚点句=年轻硬朗长方脸·浓直眉克制目光·黑发高束·墨黑暗赤镇魔司劲装·左臂骨折；BEAST_01/复生态：reference_group=ready；registry_form=“穿心复生态”；锚点句=真实虎首人形巨躯·琥珀竖瞳·右眉骨旧裂·胸前黑血洞·深褐破围腰；本镜绑定=CHAR_01/囚途残损态、CHAR_02/濒死态、BEAST_01/复生态；资产引用注册层=LOC_01, PROP_横刀, VFX_百妖谱, VFX_系统面板。
**近景/反打身份锁定**：主焦点=CHAR_01/囚途残损态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/囚途残损态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=voice_conditioned_lipsync; risk=medium; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=配音只作口型条件，确认模型音轨未进入成片。
**衔接设计**：
- 入点：裴长青濒死落在姜月初脚边，横刀脱手，虎妖继续逼近；姜月初尚未持刀。
- 出点：主角理解规则，视线落在裴与横刀。
- 转场：视线切递刀手。
- 连贯性：required_presence=CHAR_01、CHAR_02、BEAST_01、VFX_百妖谱; offscreen_presence=无; forbidden_presence=主角妖化附体形态; eyeline=上后景→右下; inner_focus=无

**continuity**：
- start_state：裴长青濒死落在姜月初脚边，横刀脱手，虎妖继续逼近；姜月初尚未持刀。
- action：空白卷轴展开，黑墨游走。；规则与虎爪交替。；看向右下裴长青。
- end_state：主角理解规则，视线落在裴与横刀。
- constraints：required_presence=CHAR_01、CHAR_02、BEAST_01、VFX_百妖谱; offscreen_presence=无; forbidden_presence=主角妖化附体形态; eyeline=上后景→右下
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-10.2; profile=zh_motion_first; backend=seedance; mode=voice_conditioned_lipsync; language=zh; native_audio_policy=lipsync_condition_only; frame_strategy=edit_cut; story_span_sec=7.06; edit_target_sec=7.06; backend_request_sec=8.0; action_start_sec=0.25; action_end_sec=6.56; hold_end_sec=7.06; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=548ce838bffc287668352037e3455ed0687e2b33897ab67cb893f7510d980431
```text
以已提交首帧为视觉真值。 主动作：空白卷轴展开，黑墨游走。；规则与虎爪交替。；看向右下裴长青。 镜头：固定或缓慢推近。 节奏：规则揭示。 时间：0.25-6.56秒完成主动作，持续保持落幅到7.06秒。7.06-8.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：主角理解规则，视线落在裴与横刀。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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

## Clip 08（时长 12.880s · EP01_CLIP08 · 对不住了，刀落人身）

**首帧**：`出图/第1集/图片/Clip08_first.png`
**尾帧**：`出图/第1集/图片/Clip08_end.png`
**锚帧1**：`出图/第1集/图片/EP01_CLIP08_anchor01.png`（at_sec=2.6）
**锚帧2**：`出图/第1集/图片/EP01_CLIP08_anchor_cut_0360.png`（at_sec=3.6）
**锚帧3**：`出图/第1集/图片/EP01_CLIP08_anchor02.png`（at_sec=5.6）
**锚帧4**：`出图/第1集/图片/EP01_CLIP08_a2.png`（at_sec=7.0）
**场景**：LOC_01
**剧本可看性合同**：dramatic_function=兑现开场反差：姜月初为求生主动将刀刺向濒死的裴长青，但本集不确认生死与结算。；audience_effect=震惊于她求生的主动性，并立刻想知道道行结算和裴的生死。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：兑现开场反差：姜月初为求生主动将刀刺向濒死的裴长青，但本集不确认生死与结算。
**起幅**：主角理解规则，视线落在裴与横刀。
**落幅**：横刀刚没入裴长青胸前衣料，生死与结算未知。
**场面调度**：85mm → 85mm → 85mm；角色=CHAR_01/囚途残损态、CHAR_02/濒死受刀态、BEAST_01/焦外；资产=LOC_01, PROP_横刀；轴线/视线=左上/右下互看后失焦
**正反打视频合同**：axis_id=AXIS_LOC_01_CHAR_01_VS_CHAR_02；A=CHAR_01，位置=CHAR_01/囚途残损态 画左/前景/高位，视线=看画右的戏内对象，不看镜头；B=CHAR_02，位置=CHAR_02/濒死受刀态 画右/后景/低位，视线=看画左的戏内对象，不看镜头；站位模式=left_right，A/B 不互换；OTS 前景肩部=焦点 CHAR_01；CHAR_02 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。 / 焦点 CHAR_02；CHAR_01 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。；coverage=establishing master + paired clean singles + true OTS with foreground shoulder + insert/cutaway + reaction shot；镜头匹配=A/B 反打保持相近焦段、镜头距离、镜头高度、光位和背景深度；权力高低只用轻微机位差表达。；越轴策略=默认禁止越轴；如剧情必须越轴，先用建立镜/中线移动/道具插入/空镜缓冲重新定向。；缓冲镜=双人建立镜、道具插入、反应近景或空镜负责重新定向；不得直接跳反轴近景。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 裴递刀让她自保。；姜月初看虎妖、横刀与裴长青，确认唯一可杀的活物，低声说我想活。；姜月初道歉后单次落刀；裴长青错愕，刀口刚没入胸前衣料即黑场。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；只执行本镜主动作链
- 能量：克制匀速
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=拾刀盘算、裴催她快逃、我想活、道歉、单次落刀；speed_curve=拾刀停顿→视线盘算→道歉停顿→极短落刀→立即黑场；spatial_path=主角靠近半步，裴始终右下；camera_path=手部→错愕反打→关系落幅；readability_beats=递刀本意、姜月初确认目标、我想活、道歉、单次落刀与错愕；degrade_plan=手部、闭眼反应、错愕、血点落衣拆镜替代。；keyframe_plan=2.6秒锁接刀，5.6秒锁主角意识到目标，约9.0秒锁错愕与衣料接触。；post_cue_points=刀落前抽空环境声、短促入肉声后立即全静；physics_guard=刀路与衣料受力同向；裴无主动迎刀。；attack_path=画左上至右下短距落刀，只一次。；impact_frame=约9.0s：刀口刚没入胸前衣料，受力与裴长青错愕同帧，不展示伤口。；contact_points=双手与刀柄、刀口与胸前衣料；force_direction=左上至右下短距下压；recovery_beat=无；刀入胸即黑场。
**专项镜头模板**：template=fight_exchange；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=fight_exchange; primary_backend=seedance; fallback=dreamina; mode=frames2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=3；anchor_count=4；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第1集/图片/Clip08_first.png；end_frame=出图/第1集/图片/Clip08_end.png；midframes=4；seam_mode=hard_cut；need_end_anchor=True；transition=hard_cut_to_black；entry_exit=主角靠近半步；裴不主动移动；百妖谱保持主观记忆层，不出现道行灌注或结算面板。；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=4；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=Split into setup and impact clips; keep the hit frame as the end frame.
**连续性链路 / Continuity Chain**：入点=第1集/Clip_07→第1集/Clip_08；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=视线切递刀手。；from_end=主角理解规则，视线落在裴与横刀。；to_start=主角理解规则，视线落在裴与横刀。；出点=本镜为本集末镜，或下一镜 seam 未登记。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=4；consumption_mode=native_multiframe；native_timeline_frames=6；reference_inputs=characters=character_id=CHAR_01；form=囚途残损态；binding=native_identity_lock_required、character_id=CHAR_02；form=濒死受刀态；binding=native_identity_lock_required、binding=native_identity_lock_required；assets=LOC_01；motion_reference=allowed=True；library_path=生产数据/motion_reference_library.json；policy=use same sequence/shot_type approved reference when available；identity_preservation_plan=required_identity_anchors=face_shape、hairstyle、age_read、outfit_palette、named_character_screen_slot；reference_strategy=native_identity_lock_required；motion_readability_allowances=prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups、allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot、keep first/end frame and registered reference group as identity truth when motion control needs simpler movement；fallback_plan=If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.；applies_to=fight_exchange；control_inputs=manifest_path=出视频/第1集/control/Clip_08/motion_control_manifest.json；required=True；required_inputs=pose_sequence、depth_sequence、instance_masks、contact_map、camera_path；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=performance_audio_first；timing_basis=final_voice；performance_track_status=final_ready；performance_audio_paths=合成/第1集/配音/line_18.wav、合成/第1集/配音/line_19.wav、合成/第1集/配音/line_20.wav、合成/第1集/配音/line_21.wav；requires_performance_audio_before_final=True；base_video_mouth_policy=route_default；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.；anchor_consumption=backend=seedance；execution_backend=seedance；frame_control_mode=first_frame_or_channel；anchor_count=4；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_08/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path；failure_modes=feature_melting,limb_fusion,weapon_contact_drift,body_interpenetration；degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.
**角色身份注册层**：CHAR_01/囚途残损态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；CHAR_02/濒死受刀态：reference_group=ready；registry_form=“濒死重伤态”；锚点句=年轻硬朗长方脸·浓直眉克制目光·黑发高束·墨黑暗赤镇魔司劲装·左臂骨折；BEAST_01/焦外：reference_group=ready；registry_form=“穿心复生态”；锚点句=真实虎首人形巨躯·琥珀竖瞳·右眉骨旧裂·胸前黑血洞·深褐破围腰；本镜绑定=CHAR_01/囚途残损态、CHAR_02/濒死受刀态、BEAST_01/焦外；资产引用注册层=LOC_01, PROP_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01/囚途残损态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/囚途残损态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=VFX_百妖谱 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：主角理解规则，视线落在裴与横刀。
- 出点：横刀刚没入裴长青胸前衣料，生死与结算未知。
- 转场：hard_cut_to_black
- 连贯性：required_presence=CHAR_01、CHAR_02、PROP_横刀; offscreen_presence=VFX_百妖谱; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=左上/右下互看后失焦; inner_focus=无

**continuity**：
- start_state：主角理解规则，视线落在裴与横刀。
- action：裴递刀让她自保。；姜月初看虎妖、横刀与裴长青，确认唯一可杀的活物，低声说我想活。；姜月初道歉后单次落刀；裴长青错愕，刀口刚没入胸前衣料即黑场。
- end_state：横刀刚没入裴长青胸前衣料，生死与结算未知。
- constraints：required_presence=CHAR_01、CHAR_02、PROP_横刀; offscreen_presence=VFX_百妖谱; forbidden_presence=modern vehicles, phones, random readable text, watermark; eyeline=左上/右下互看后失焦
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-10.2; profile=zh_motion_first; backend=seedance; mode=frames2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut; story_span_sec=12.88; edit_target_sec=12.88; backend_request_sec=13.0; action_start_sec=0.25; action_end_sec=12.38; hold_end_sec=12.88; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=b12f24d07b73e47bf7cc42abfc5cfbc43dd8178d368b995333755def54a1cb27
```text
从首帧连续运动到尾帧。 主动作：裴递刀让她自保。；姜月初看虎妖、横刀与裴长青，确认唯一可杀的活物，低声说我想活。；姜月初道歉后单次落刀；裴长青错愕，刀口刚没入胸前衣料即黑场。 镜头：固定或极缓推近。 节奏：反转·留静音。 时间：0.25-12.38秒完成主动作，持续保持落幅到12.88秒。12.88-13.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：横刀刚没入裴长青胸前衣料，生死与结算未知。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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
