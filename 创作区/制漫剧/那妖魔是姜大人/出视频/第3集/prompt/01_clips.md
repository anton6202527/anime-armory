# 第3集 视频 Clip prompt

## 本集留存承诺账本（script_quality_contract）

- R01: hook_id=OPEN_01；opened_at=EP03_CLIP01；payoff_clip=EP03_CLIP07；payoff_due=EP03_CLIP07；payoff_status=paid；promise=这些人为何把姜月初当成唯一救命者；promise_type=opening_hook
- R02: hook_id=MID_01；opened_at=EP03_CLIP03；payoff_clip=EP03_CLIP06；payoff_due=EP03_CLIP06；payoff_status=paid；promise=偷穿制服究竟是护身符还是催命符；promise_type=identity_risk
- R03: hook_id=TAIL_01；opened_at=EP03_CLIP08；payoff_due=第4集；payoff_status=open；promise=顶着假身份去上盘村剿狼妖，她能活着回来吗；promise_type=cliffhanger

## Clip 01（时长 10.520s · EP03_CLIP01 · 众人跪求的假大人）

**首帧**：`出图/第3集/图片/Clip01_first.png`
**锚帧1**：`出图/第3集/图片/Clip01_first_a1.png`（at_sec=5.26）
**场景**：LOC_02/未来片段·官道群跪
**剧本可看性合同**：dramatic_function=先展示假身份被跪求的结果，再回到换装之前，让身份反噬成为本集命题。；audience_effect=立刻追问这些刀客为何跪求一个年轻女子，她又为何心虚。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：先展示假身份被跪求的结果，再回到换装之前，让身份反噬成为本集命题。
**起幅**：未来片段：众人已跪，姜月初已着镇魔司制服。
**落幅**：她僵在群跪之前，内心自问如何沦为救命稻草。
**场面调度**：35mm → 85mm；角色=CHAR_01/镇魔司制服态、CHAR_03/风尘劲装态、GROUP_01/齐跪态；资产=LOC_02, WEAPON_横刀；轴线/视线=众人向画右前叩首；姜月初视线低垂向画左下。
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：众人向画右前叩首；姜月初视线低垂向画左下；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 官道群跪全景，尘土未落，马队在后。；姜月初错愕心虚的脸，指节收紧，喉头轻动。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=群骑急停、十余人齐跪、姜月初僵直反应；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**专项镜头模板**：template=ensemble_blocking；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=ensemble_blocking; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**帧策略 / Frame Strategy**：strategy=edit_cut_pending_assets；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=2；anchor_count=1；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第3集/图片/Clip01_first.png；end_frame=无；midframes=1；seam_mode=intentional_discontinuity；need_end_anchor=False；transition=时间回切至埋尸。；entry_exit=只交代群跪、制服、心虚三要素；不出现浅坟与囚服。；出画/画外保留：CHAR_03、GROUP_01；入画/现身：CHAR_02、PROP_镇魔司制服；出画/画外保留：CHAR_03、GROUP_01；入画/现身：CHAR_02、PROP_镇魔司制服；出画/画外保留：CHAR_03、GROUP_01；入画/现身：PROP_镇魔司制服；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；consumption_mode=edit_cut_pending_assets；frame_strategy=edit_cut_pending_assets；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=create missing shot-boundary images before paid generation；fallback=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**连续性链路 / Continuity Chain**：入点=第2集/Clip_08→第3集/Clip_01；scope=episode_boundary；policy=intentional_discontinuity；strictness=mode_specific；transition=第2集墨虎眼亮后切黑；第3集以稍后的官道群跪倒叙冷开，再回到埋尸时点；from_end=墨虎双眼短亮，姜月初未得到答案，切黑；to_start=未来片段：众人已跪，姜月初已着镇魔司制服。；intentional_discontinuity=长线摉影进阶承诺延后处理；本集先承接杀裴的现实后果和身份代价。；出点=第3集/Clip_01→第3集/Clip_02；scope=intra_episode；policy=intentional_discontinuity；strictness=mode_specific；transition=时间回切至埋尸。；from_end=她僵在群跪之前，内心自问如何沦为救命稻草。；to_start=她僵在群跪之前，内心自问如何沦为救命稻草。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=2；reference_inputs=characters=character_id=CHAR_01；form=镇魔司制服态；binding=native_identity_lock_required、character_id=CHAR_03；form=风尘劲装态；binding=native_identity_lock_required、binding=native_identity_lock_required；assets=LOC_02；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；identity_preservation_plan=required_identity_anchors=face_shape、hairstyle、age_read、outfit_palette、named_character_screen_slot；reference_strategy=native_identity_lock_required；motion_readability_allowances=prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups、allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot、keep first frame and registered reference group as identity truth when motion control needs simpler movement；fallback_plan=If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.；applies_to=ensemble_blocking；control_inputs=manifest_path=出视频/第3集/control/Clip_01/motion_control_manifest.json；required=True；required_inputs=pose_sequence、depth_sequence、instance_masks；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=base_video_then_post_lipsync；timing_basis=text_estimate_no_audio；performance_track_status=missing；requires_performance_audio_before_final=True；post_lipsync_required=True；base_video_only=True；base_video_mouth_policy=neutral_rest_no_visible_articulation；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；consumption_mode=edit_cut_pending_assets；frame_strategy=edit_cut_pending_assets；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=create missing shot-boundary images before paid generation
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第3集/control/Clip_01/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**角色身份注册层**：CHAR_01/镇魔司制服态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；CHAR_03/风尘劲装态：reference_group=ready；registry_form=常态；锚点句=03·03 的剧情视觉真值必须入画：本集入镜角色；成年古装角色，年龄感按剧情身份保守处理；03 的脸型、年龄感、肤色和五官比例必须稳定；五官清楚耐看，不使用同质化网红脸。·03 穿低饱和古装衣袍，领口、袖口、腰带和下摆结构稳定，不出现现代服饰。；GROUP_01/齐跪态：reference_group=ready；registry_form=常态；锚点句=GROUP_01·GROUP_01 的剧情视觉真值必须入画：本集入镜角色；三至五名低饱和粗布背景人群，只保留肩线、侧后轮廓和虚化嘴形，不建立清晰正脸。·三至五名低饱和粗布背景人群，只保留肩线、侧后轮廓和虚化嘴形，不建立清晰正脸。；本镜绑定=CHAR_01/镇魔司制服态、CHAR_03/风尘劲装态、GROUP_01/齐跪态；资产引用注册层=LOC_02, WEAPON_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01/镇魔司制服态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/镇魔司制服态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=CHAR_02, PROP_镇魔司制服 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：未来片段：众人已跪，姜月初已着镇魔司制服。
- 出点：她僵在群跪之前，内心自问如何沦为救命稻草。
- 转场：时间回切至埋尸。
- 连贯性：required_presence=CHAR_01、CHAR_03、GROUP_01; offscreen_presence=CHAR_02、PROP_镇魔司制服; forbidden_presence=CHAR_02、BEAST_01; eyeline=众人向画右前叩首；姜月初视线低垂向画左下。; inner_focus=无

**continuity**：
- start_state：未来片段：众人已跪，姜月初已着镇魔司制服。
- action：官道群跪全景，尘土未落，马队在后。；姜月初错愕心虚的脸，指节收紧，喉头轻动。
- end_state：她僵在群跪之前，内心自问如何沦为救命稻草。
- constraints：required_presence=CHAR_01、CHAR_03、GROUP_01; offscreen_presence=CHAR_02、PROP_镇魔司制服; forbidden_presence=CHAR_02、BEAST_01; eyeline=众人向画右前叩首；姜月初视线低垂向画左下。
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut_pending_assets; story_span_sec=10.52; edit_target_sec=10.52; backend_request_sec=11.0; action_start_sec=0.25; action_end_sec=10.02; hold_end_sec=10.52; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=ae445518e3fd9d623b7f560d9f6e5ad16eedf319041a34e921d3d8ccf94626df
```text
以已提交首帧为视觉真值。 主动作：官道群跪全景，尘土未落，马队在后。；姜月初错愕心虚的脸，指节收紧，喉头轻动。 镜头：固定机位，用前中后景和人物入出画建立空间关系；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：众人向画右前叩首；姜月初视线低垂向画左下；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：冷开场·ELS压CU硬切。 时间：0.25-10.02秒完成主动作，持续保持落幅到10.52秒。10.52-11.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：她僵在群跪之前，内心自问如何沦为救命稻草。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_01.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 02（时长 7.441s · EP03_CLIP02 · 荒坡埋尸告别）

**首帧**：`出图/第3集/图片/Clip02_first.png`
**场景**：LOC_01/荒野边缘浅坟
**剧本可看性合同**：dramatic_function=她亲手埋葬给过她自由承诺的人，并拿走死者之物——杀裴的道德代价落地为可见动作。；audience_effect=感到她的自嘲与愧疚，理解拿走制服是求生而非贪财。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：她亲手埋葬给过她自由承诺的人，并拿走死者之物——杀裴的道德代价落地为可见动作。
**起幅**：她僵在群跪之前，内心自问如何沦为救命稻草。
**落幅**：她抱起制服与横刀起身，背向浅坟。
**场面调度**：50mm → 85mm；角色=CHAR_01/囚服残损态；资产=LOC_01, WEAPON_横刀, PROP_镇魔司制服；轴线/视线=她看坟向画左下，起身后视线转向怀中制服。
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：她看坟向画左下，起身后视线转向怀中制服；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 镜头1（50mm）：浅坟与断枝，姜月初拍实浮土后静默半拍。；镜头2（85mm）：她低头道『得罪了兄弟』，抱起制服包袱与横刀起身。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=按 storyboard shots 顺序执行；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**专项镜头模板**：template=none；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=general_motion; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**帧策略 / Frame Strategy**：strategy=single_take_multishot；reason=storyboard_take_policy_single_take_and_backend_multishot_native；shot_count=2；anchor_count=0；首尾帧后端不得把 split relay 冒充原生三帧。
**单拍多镜合同 / Single-Take Multishot**：take_policy=single_take_multishot；内部镜位 2 个由 multishot-native 后端一次生成（镜头阶梯：镜头1（50mm）：浅坟与断枝，姜月初拍实浮土后静默半拍。；镜头2（85mm）：她低头道『得罪了兄弟』，抱起制服包袱与横刀起身。）；不拆独立付费 take、不消费 edit_cut 边界锚为时间轴；后端不支持或时长超窗时必须回落 edit_cut 拆 take，不得静默按单镜直提。
**接缝执行包 / Handoff Package**：first_frame=出图/第3集/图片/Clip02_first.png；end_frame=无；midframes=0；seam_mode=hard_cut；need_end_anchor=False；transition=同场景接换装。；entry_exit=浅坟、断枝、制服包袱首次入画；遗容全程不入画。；出画/画外保留：CHAR_03、GROUP_01；入画/现身：CHAR_02、PROP_镇魔司制服；出画/画外保留：CHAR_02；出画/画外保留：CHAR_03、GROUP_01；入画/现身：CHAR_02、PROP_镇魔司制服；出画/画外保留：CHAR_02；出画/画外保留：CHAR_03、GROUP_01；入画/现身：PROP_镇魔司制服；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；consumption_mode=single_take_multishot；frame_strategy=single_take_multishot；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=manual confirmation required before paid generation；fallback=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**连续性链路 / Continuity Chain**：入点=第3集/Clip_01→第3集/Clip_02；scope=intra_episode；policy=intentional_discontinuity；strictness=mode_specific；transition=时间回切至埋尸。；from_end=她僵在群跪之前，内心自问如何沦为救命稻草。；to_start=她僵在群跪之前，内心自问如何沦为救命稻草。；出点=第3集/Clip_02→第3集/Clip_03；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=同场景接换装。；from_end=她抱起制服与横刀起身，背向浅坟。；to_start=她抱起制服与横刀起身，背向浅坟。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；consumption_mode=first_frame；native_timeline_frames=1；reference_inputs=characters=character_id=CHAR_01；form=囚服残损态；binding=native_identity_lock_required；assets=LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=base_video_then_post_lipsync；timing_basis=text_estimate_no_audio；performance_track_status=missing；requires_performance_audio_before_final=True；post_lipsync_required=True；base_video_only=True；base_video_mouth_policy=neutral_rest_no_visible_articulation；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；consumption_mode=single_take_multishot；frame_strategy=single_take_multishot；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=manual confirmation required before paid generation
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**角色身份注册层**：CHAR_01/囚服残损态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；本镜绑定=CHAR_01/囚服残损态；资产引用注册层=LOC_01, WEAPON_横刀, PROP_镇魔司制服。
**近景/反打身份锁定**：主焦点=CHAR_01/囚服残损态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/囚服残损态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=CHAR_02, CHAR_03, GROUP_01 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：她僵在群跪之前，内心自问如何沦为救命稻草。
- 出点：她抱起制服与横刀起身，背向浅坟。
- 转场：同场景接换装。
- 连贯性：required_presence=CHAR_01、PROP_镇魔司制服; offscreen_presence=CHAR_02、CHAR_03、GROUP_01; forbidden_presence=BEAST_01、CHAR_03、GROUP_01; eyeline=她看坟向画左下，起身后视线转向怀中制服。; inner_focus=无

**continuity**：
- start_state：她僵在群跪之前，内心自问如何沦为救命稻草。
- action：镜头1（50mm）：浅坟与断枝，姜月初拍实浮土后静默半拍。；镜头2（85mm）：她低头道『得罪了兄弟』，抱起制服包袱与横刀起身。
- end_state：她抱起制服与横刀起身，背向浅坟。
- constraints：required_presence=CHAR_01、PROP_镇魔司制服; offscreen_presence=CHAR_02、CHAR_03、GROUP_01; forbidden_presence=BEAST_01、CHAR_03、GROUP_01; eyeline=她看坟向画左下，起身后视线转向怀中制服。
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=single_take_multishot; story_span_sec=7.441; edit_target_sec=7.441; backend_request_sec=8.0; action_start_sec=0.25; action_end_sec=6.941; hold_end_sec=7.441; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=799a6d10d56fb3701dbb023f608ab912653fb1fe58c3aa22207f53fcb43c4ad7
```text
以已提交首帧为视觉真值。 主动作：镜头1（50mm）：浅坟与断枝，姜月初拍实浮土后静默半拍。；镜头2（85mm）：她低头道『得罪了兄弟』，抱起制服包袱与横刀起身。 镜头：固定机位，过肩/反打保持轴线、景别和视线目标；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：她看坟向画左下，起身后视线转向怀中制服；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：慢·静场。 时间：0.25-6.94秒完成主动作，持续保持落幅到7.44秒。7.44-8.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：她抱起制服与横刀起身，背向浅坟。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_02.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 03（时长 11.755s · EP03_CLIP03 · 黑衣赤纹换装）

**首帧**：`出图/第3集/图片/Clip03_first.png`
**尾帧**：`出图/第3集/图片/EP03_CLIP03_a1.png`
**锚帧1**：`出图/第3集/图片/EP03_CLIP03_a1.png`（at_sec=9.0）
**场景**：LOC_01/荒野边缘换装
**剧本可看性合同**：dramatic_function=囚犯到假镇魔司的身份转换用衣料、束发、佩刀三动作完成；她清醒知道这步棋的双刃。；audience_effect=看见她『变成』镇魔司的过程，同时被『狼窝门口』的预言埋下不安。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：囚犯到假镇魔司的身份转换用衣料、束发、佩刀三动作完成；她清醒知道这步棋的双刃。
**起幅**：她抱起制服与横刀起身，背向浅坟。
**落幅**：换装完成：黑衣赤纹、束发、佩刀，囚服弃地。
**场面调度**：50mm → 35mm；角色=CHAR_01/囚服转制服态；资产=LOC_01, WEAPON_横刀, PROP_镇魔司制服；轴线/视线=低头看衣料与刀，站定后望向画左后官道方向。
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：低头看衣料与刀，站定后望向画左后官道方向；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 镜头1（50mm）：赤纹披肩、束发、佩刀三个动作完成点连切。；镜头2（35mm）：黑衣赤纹全身立姿，囚服弃于脚边，手按刀柄。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=衣料披肩、束发佩刀、全身立姿确认；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**专项镜头模板**：template=dialogue_shot_reverse；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**帧策略 / Frame Strategy**：strategy=single_take_multishot；reason=storyboard_take_policy_single_take_and_backend_multishot_native；shot_count=2；anchor_count=1；首尾帧后端不得把 split relay 冒充原生三帧。
**单拍多镜合同 / Single-Take Multishot**：take_policy=single_take_multishot；内部镜位 2 个由 multishot-native 后端一次生成（镜头阶梯：镜头1（50mm）：赤纹披肩、束发、佩刀三个动作完成点连切。；镜头2（35mm）：黑衣赤纹全身立姿，囚服弃于脚边，手按刀柄。）；不拆独立付费 take、不消费 edit_cut 边界锚为时间轴；后端不支持或时长超窗时必须回落 edit_cut 拆 take，不得静默按单镜直提。
**接缝执行包 / Handoff Package**：first_frame=出图/第3集/图片/Clip03_first.png；end_frame=出图/第3集/图片/EP03_CLIP03_a1.png；midframes=1；seam_mode=hard_cut；need_end_anchor=True；transition=离开荒野切官道行路。；entry_exit=囚服自此退场；制服态自此为常态。；出画/画外保留：CHAR_02；出画/画外保留：PROP_镇魔司制服；出画/画外保留：CHAR_02；出画/画外保留：PROP_镇魔司制服；出画/画外保留：PROP_镇魔司制服；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=single_take_multishot；frame_strategy=single_take_multishot；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=manual confirmation required before paid generation；fallback=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**连续性链路 / Continuity Chain**：入点=第3集/Clip_02→第3集/Clip_03；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=同场景接换装。；from_end=她抱起制服与横刀起身，背向浅坟。；to_start=她抱起制服与横刀起身，背向浅坟。；出点=第3集/Clip_03→第3集/Clip_04；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=离开荒野切官道行路。；from_end=换装完成：黑衣赤纹、束发、佩刀，囚服弃地。；to_start=换装完成：黑衣赤纹、束发、佩刀，囚服弃地。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；form=囚服转制服态；binding=native_identity_lock_required；assets=LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=post_dub；timing_basis=text_estimate_no_audio；performance_track_status=missing；base_video_mouth_policy=route_default；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=single_take_multishot；frame_strategy=single_take_multishot；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=manual confirmation required before paid generation
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**角色身份注册层**：CHAR_01/囚服转制服态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；本镜绑定=CHAR_01/囚服转制服态；资产引用注册层=LOC_01, WEAPON_横刀, PROP_镇魔司制服。
**近景/反打身份锁定**：主焦点=CHAR_01/囚服转制服态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=微；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/囚服转制服态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=CHAR_02 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：她抱起制服与横刀起身，背向浅坟。
- 出点：换装完成：黑衣赤纹、束发、佩刀，囚服弃地。
- 转场：离开荒野切官道行路。
- 连贯性：required_presence=CHAR_01、PROP_镇魔司制服、WEAPON_横刀; offscreen_presence=CHAR_02; forbidden_presence=CHAR_02、CHAR_03、GROUP_01、BEAST_01; eyeline=低头看衣料与刀，站定后望向画左后官道方向。; inner_focus=无

**continuity**：
- start_state：她抱起制服与横刀起身，背向浅坟。
- action：镜头1（50mm）：赤纹披肩、束发、佩刀三个动作完成点连切。；镜头2（35mm）：黑衣赤纹全身立姿，囚服弃于脚边，手按刀柄。
- end_state：换装完成：黑衣赤纹、束发、佩刀，囚服弃地。
- constraints：required_presence=CHAR_01、PROP_镇魔司制服、WEAPON_横刀; offscreen_presence=CHAR_02; forbidden_presence=CHAR_02、CHAR_03、GROUP_01、BEAST_01; eyeline=低头看衣料与刀，站定后望向画左后官道方向。
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=single_take_multishot; story_span_sec=11.755; edit_target_sec=11.755; backend_request_sec=12.0; action_start_sec=0.25; action_end_sec=11.255; hold_end_sec=11.755; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=51c4ae35a6f72831665d55deb98964b5233721a1493e93c8a60d36e37c83dec2
```text
以已提交首帧为视觉真值。 主动作：镜头1（50mm）：赤纹披肩、束发、佩刀三个动作完成点连切。；镜头2（35mm）：黑衣赤纹全身立姿，囚服弃于脚边，手按刀柄。 镜头：固定机位，让人物在固定构图中退场或停留；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：低头看衣料与刀，站定后望向画左后官道方向；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：常速·三动作蒙太奇。 时间：0.25-11.26秒完成主动作，持续保持落幅到11.76秒。11.76-12.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：换装完成：黑衣赤纹、束发、佩刀，囚服弃地。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_03.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 04（时长 15.383s · EP03_CLIP04 · 贱籍死局与马蹄）

**首帧**：`出图/第3集/图片/Clip04_first.png`
**尾帧**：`出图/第3集/图片/Clip04_end.png`
**锚帧1**：`出图/第3集/图片/Clip04_first_a1.png`（at_sec=7.69）
**场景**：LOC_02/官道行路
**剧本可看性合同**：dramatic_function=贱籍无路引的死局把她的选择压到墙角，马蹄声在绝路尽头骤然响起。；audience_effect=理解她为何只能硬着头皮扮下去，并因马蹄声瞬间提起心弦。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：贱籍无路引的死局把她的选择压到墙角，马蹄声在绝路尽头骤然响起。
**起幅**：换装完成：黑衣赤纹、束发、佩刀，囚服弃地。
**落幅**：她驻足回身按刀，马队尘头在道路尽头出现。
**场面调度**：35mm → 85mm；角色=CHAR_01/镇魔司制服态；资产=LOC_02, WEAPON_横刀；轴线/视线=行路视线向画左后纵深；回身后望向画左后尘头。
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：行路视线向画左后纵深；回身后望向画左后尘头；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 官道独行，纵深车辙，步频承内心盘算。；烦躁苦笑转骤然警觉：驻足回身，手按刀柄，远处尘头。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=按 storyboard shots 顺序执行；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Use Dreamina/Seedance silent clip and add SFX/BGM in compose.
**专项镜头模板**：template=none；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=empty_establishing; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; degrade_plan=Use Dreamina/Seedance silent clip and add SFX/BGM in compose.
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=single_take_multishot_fallback_backend_unsupported_or_span_exceeds_window；shot_count=2；anchor_count=1；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第3集/图片/Clip04_first.png；end_frame=出图/第3集/图片/Clip04_end.png；midframes=1；seam_mode=hard_cut；need_end_anchor=False；transition=马队冲近接急停。；entry_exit=官道与车辙纵深首次入画；马队以远处尘头预告入画。；出画/画外保留：PROP_镇魔司制服；入画/现身：CHAR_03、GROUP_01；出画/画外保留：PROP_镇魔司制服；入画/现身：CHAR_03、GROUP_01；出画/画外保留：PROP_镇魔司制服；入画/现身：CHAR_03、GROUP_01；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=Use Dreamina/Seedance silent clip and add SFX/BGM in compose.
**连续性链路 / Continuity Chain**：入点=第3集/Clip_03→第3集/Clip_04；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=离开荒野切官道行路。；from_end=换装完成：黑衣赤纹、束发、佩刀，囚服弃地。；to_start=换装完成：黑衣赤纹、束发、佩刀，囚服弃地。；出点=第3集/Clip_04→第3集/Clip_05；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=马队冲近接急停。；from_end=她驻足回身按刀，马队尘头在道路尽头出现。；to_start=她驻足回身按刀，马队尘头在道路尽头出现。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；form=镇魔司制服态；binding=reference_group；assets=LOC_02；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=post_dub；timing_basis=text_estimate_no_audio；performance_track_status=missing；base_video_mouth_policy=route_default；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=Use Dreamina/Seedance silent clip and add SFX/BGM in compose.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Use Dreamina/Seedance silent clip and add SFX/BGM in compose.
**角色身份注册层**：CHAR_01/镇魔司制服态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；本镜绑定=CHAR_01/镇魔司制服态；资产引用注册层=LOC_02, WEAPON_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01/镇魔司制服态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/镇魔司制服态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=GROUP_01, PROP_镇魔司制服, CHAR_03 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：换装完成：黑衣赤纹、束发、佩刀，囚服弃地。
- 出点：她驻足回身按刀，马队尘头在道路尽头出现。
- 转场：马队冲近接急停。
- 连贯性：required_presence=CHAR_01、WEAPON_横刀; offscreen_presence=GROUP_01、PROP_镇魔司制服、CHAR_03; forbidden_presence=CHAR_03、GROUP_01; eyeline=行路视线向画左后纵深；回身后望向画左后尘头。; inner_focus=无

**continuity**：
- start_state：换装完成：黑衣赤纹、束发、佩刀，囚服弃地。
- action：官道独行，纵深车辙，步频承内心盘算。；烦躁苦笑转骤然警觉：驻足回身，手按刀柄，远处尘头。
- end_state：她驻足回身按刀，马队尘头在道路尽头出现。
- constraints：required_presence=CHAR_01、WEAPON_横刀; offscreen_presence=GROUP_01、PROP_镇魔司制服、CHAR_03; forbidden_presence=CHAR_03、GROUP_01; eyeline=行路视线向画左后纵深；回身后望向画左后尘头。
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut; story_span_sec=15.383; edit_target_sec=15.383; backend_request_sec=15.0; action_start_sec=0.25; action_end_sec=14.5; hold_end_sec=15.0; trim_mode=none; requires_split=true; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=09090cda02cfbe313801be963a16f8e55a992e7708bcbee9c1f93339a84a84b8
```text
以已提交首帧为视觉真值。 主动作：官道独行，纵深车辙，步频承内心盘算。；烦躁苦笑转骤然警觉：驻足回身，手按刀柄，远处尘头。 镜头：固定机位，用前中后景和人物入出画建立空间关系；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：行路视线向画左后纵深；回身后望向画左后尘头；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：快盘算转骤停。 时间：0.25-14.50秒完成主动作，持续保持落幅到15.00秒。 结尾停稳在：她驻足回身按刀，马队尘头在道路尽头出现。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_04.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 05（时长 4.428s · EP03_CLIP05 · 马队急停试探）

**首帧**：`出图/第3集/图片/Clip05_first.png`
**锚帧1**：`出图/第3集/图片/Clip05_first_a1.png`（at_sec=2.21）
**场景**：LOC_02/官道对峙
**剧本可看性合同**：dramatic_function=十几骑的武力压迫在一件制服前放缓成试探；她用两个字撑住第一回合。；audience_effect=为她第一句话捏汗，又因『两个字唬住刀客』获得反转快感。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：十几骑的武力压迫在一件制服前放缓成试探；她用两个字撑住第一回合。
**起幅**：她驻足回身按刀，马队尘头在道路尽头出现。
**落幅**：急停对峙成形：陈青源执礼试探，她以『何事』撑住。
**场面调度**：35mm → 50mm；角色=CHAR_01/镇魔司制服态、CHAR_03/风尘劲装态、GROUP_01/列队戒备态；资产=LOC_02, WEAPON_横刀；轴线/视线=陈青源自马上俯向画右前；她侧首回望向画左后。
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：陈青源自马上俯向画右前；她侧首回望向画左后；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 马队冲近急停，尘土漫过她衣摆，她立定不退。；陈青源马上拱手试探；她半拍沉默后侧首吐出两字。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=马队纵深冲近、勒马急停、陈青源拱手试探；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**专项镜头模板**：template=ensemble_blocking；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=ensemble_blocking; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**帧策略 / Frame Strategy**：strategy=edit_cut_pending_assets；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=2；anchor_count=1；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第3集/图片/Clip05_first.png；end_frame=无；midframes=1；seam_mode=hard_cut；need_end_anchor=False；transition=同场景接陈情。；entry_exit=陈青源与飞鹰门马队正式入画。；入画/现身：CHAR_03、GROUP_01；入画/现身：CHAR_03、GROUP_01；入画/现身：CHAR_03、GROUP_01；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；consumption_mode=edit_cut_pending_assets；frame_strategy=edit_cut_pending_assets；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=create missing shot-boundary images before paid generation；fallback=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**连续性链路 / Continuity Chain**：入点=第3集/Clip_04→第3集/Clip_05；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=马队冲近接急停。；from_end=她驻足回身按刀，马队尘头在道路尽头出现。；to_start=她驻足回身按刀，马队尘头在道路尽头出现。；出点=第3集/Clip_05→第3集/Clip_06；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=同场景接陈情。；from_end=急停对峙成形：陈青源执礼试探，她以『何事』撑住。；to_start=急停对峙成形：陈青源执礼试探，她以『何事』撑住。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=2；reference_inputs=characters=character_id=CHAR_01；form=镇魔司制服态；binding=native_identity_lock_required、character_id=CHAR_03；form=风尘劲装态；binding=native_identity_lock_required、binding=native_identity_lock_required；assets=LOC_02；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；identity_preservation_plan=required_identity_anchors=face_shape、hairstyle、age_read、outfit_palette、named_character_screen_slot；reference_strategy=native_identity_lock_required；motion_readability_allowances=prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups、allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot、keep first frame and registered reference group as identity truth when motion control needs simpler movement；fallback_plan=If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.；applies_to=ensemble_blocking；control_inputs=manifest_path=出视频/第3集/control/Clip_05/motion_control_manifest.json；required=True；required_inputs=pose_sequence、depth_sequence、instance_masks；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=base_video_then_post_lipsync；timing_basis=text_estimate_no_audio；performance_track_status=missing；requires_performance_audio_before_final=True；post_lipsync_required=True；base_video_only=True；base_video_mouth_policy=neutral_rest_no_visible_articulation；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；consumption_mode=edit_cut_pending_assets；frame_strategy=edit_cut_pending_assets；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=create missing shot-boundary images before paid generation
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第3集/control/Clip_05/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**角色身份注册层**：CHAR_01/镇魔司制服态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；CHAR_03/风尘劲装态：reference_group=ready；registry_form=常态；锚点句=03·03 的剧情视觉真值必须入画：本集入镜角色；成年古装角色，年龄感按剧情身份保守处理；03 的脸型、年龄感、肤色和五官比例必须稳定；五官清楚耐看，不使用同质化网红脸。·03 穿低饱和古装衣袍，领口、袖口、腰带和下摆结构稳定，不出现现代服饰。；GROUP_01/列队戒备态：reference_group=ready；registry_form=常态；锚点句=GROUP_01·GROUP_01 的剧情视觉真值必须入画：本集入镜角色；三至五名低饱和粗布背景人群，只保留肩线、侧后轮廓和虚化嘴形，不建立清晰正脸。·三至五名低饱和粗布背景人群，只保留肩线、侧后轮廓和虚化嘴形，不建立清晰正脸。；本镜绑定=CHAR_01/镇魔司制服态、CHAR_03/风尘劲装态、GROUP_01/列队戒备态；资产引用注册层=LOC_02, WEAPON_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01/镇魔司制服态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/镇魔司制服态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：她驻足回身按刀，马队尘头在道路尽头出现。
- 出点：急停对峙成形：陈青源执礼试探，她以『何事』撑住。
- 转场：同场景接陈情。
- 连贯性：required_presence=CHAR_01、CHAR_03、GROUP_01; offscreen_presence=无; forbidden_presence=BEAST_01; eyeline=陈青源自马上俯向画右前；她侧首回望向画左后。; inner_focus=无

**continuity**：
- start_state：她驻足回身按刀，马队尘头在道路尽头出现。
- action：马队冲近急停，尘土漫过她衣摆，她立定不退。；陈青源马上拱手试探；她半拍沉默后侧首吐出两字。
- end_state：急停对峙成形：陈青源执礼试探，她以『何事』撑住。
- constraints：required_presence=CHAR_01、CHAR_03、GROUP_01; offscreen_presence=无; forbidden_presence=BEAST_01; eyeline=陈青源自马上俯向画右前；她侧首回望向画左后。
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut_pending_assets; story_span_sec=4.428; edit_target_sec=4.428; backend_request_sec=5.0; action_start_sec=0.25; action_end_sec=3.928; hold_end_sec=4.428; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=7cc4112cc086f623ade6d078bc2fb89afd4a3340146cad5541f80c3b11d237bc
```text
以已提交首帧为视觉真值。 主动作：马队冲近急停，尘土漫过她衣摆，她立定不退。；陈青源马上拱手试探；她半拍沉默后侧首吐出两字。 镜头：固定机位，锁定揭示物、人物反应和画面重心；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：陈青源自马上俯向画右前；她侧首回望向画左后；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：急停·压迫对峙。 时间：0.25-3.93秒完成主动作，持续保持落幅到4.43秒。4.43-5.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：急停对峙成形：陈青源执礼试探，她以『何事』撑住。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_05.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 06（时长 15.551s · EP03_CLIP06 · 陈情与硬装）

**首帧**：`出图/第3集/图片/Clip06_first.png`
**尾帧**：`出图/第3集/图片/Clip06_end.png`
**锚帧1**：`出图/第3集/图片/Clip06_first_a1.png`（at_sec=3.89）
**锚帧2**：`出图/第3集/图片/Clip06_first_a2.png`（at_sec=7.78）
**锚帧3**：`出图/第3集/图片/Clip06_first_a3.png`（at_sec=11.66）
**场景**：LOC_02/官道陈情
**剧本可看性合同**：dramatic_function=陈青源报名陈情坐实误认；她的沉默被读作官威，假身份第一次真正兑现。；audience_effect=同时看见两层戏：明面的求援陈情与暗面的心虚硬撑。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：陈青源报名陈情坐实误认；她的沉默被读作官威，假身份第一次真正兑现。
**起幅**：急停对峙成形：陈青源执礼试探，她以『何事』撑住。
**落幅**：陈情说完，她仍未接话；心虚被读作深沉。
**场面调度**：50mm → 85mm；角色=CHAR_01/镇魔司制服态、CHAR_03/风尘劲装态、GROUP_01/列队戒备态；资产=LOC_02, WEAPON_横刀；轴线/视线=陈青源仰视画右前；她俯视画左下，避开对视半寸。
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：陈青源仰视画右前；她俯视画左下，避开对视半寸；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 陈青源下马抱拳陈情，信息完整不切碎。；她面沉如水的反打：眼神游移半寸，拇指抠刀柄。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=陈青源下马陈情、信息完整说出、姜月初心虚反应；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**专项镜头模板**：template=dialogue_shot_reverse；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=2；anchor_count=3；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第3集/图片/Clip06_first.png；end_frame=出图/第3集/图片/Clip06_end.png；midframes=3；seam_mode=hard_cut；need_end_anchor=False；transition=同场景升级为跪求。；entry_exit=上盘村、狼妖、县令手令等信息全部由台词入局，不闪回。；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=3；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**连续性链路 / Continuity Chain**：入点=第3集/Clip_05→第3集/Clip_06；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=同场景接陈情。；from_end=急停对峙成形：陈青源执礼试探，她以『何事』撑住。；to_start=急停对峙成形：陈青源执礼试探，她以『何事』撑住。；出点=第3集/Clip_06→第3集/Clip_07；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=同场景升级为跪求。；from_end=陈情说完，她仍未接话；心虚被读作深沉。；to_start=陈情说完，她仍未接话；心虚被读作深沉。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=3；consumption_mode=native_multiframe；native_timeline_frames=5；reference_inputs=characters=character_id=CHAR_01；form=镇魔司制服态；binding=native_identity_lock_required、character_id=CHAR_03；form=风尘劲装态；binding=native_identity_lock_required、binding=native_identity_lock_required；assets=LOC_02；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=base_video_then_post_lipsync；timing_basis=text_estimate_no_audio；performance_track_status=missing；requires_performance_audio_before_final=True；post_lipsync_required=True；base_video_only=True；base_video_mouth_policy=neutral_rest_no_visible_articulation；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=3；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**角色身份注册层**：CHAR_01/镇魔司制服态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；CHAR_03/风尘劲装态：reference_group=ready；registry_form=常态；锚点句=03·03 的剧情视觉真值必须入画：本集入镜角色；成年古装角色，年龄感按剧情身份保守处理；03 的脸型、年龄感、肤色和五官比例必须稳定；五官清楚耐看，不使用同质化网红脸。·03 穿低饱和古装衣袍，领口、袖口、腰带和下摆结构稳定，不出现现代服饰。；GROUP_01/列队戒备态：reference_group=ready；registry_form=常态；锚点句=GROUP_01·GROUP_01 的剧情视觉真值必须入画：本集入镜角色；三至五名低饱和粗布背景人群，只保留肩线、侧后轮廓和虚化嘴形，不建立清晰正脸。·三至五名低饱和粗布背景人群，只保留肩线、侧后轮廓和虚化嘴形，不建立清晰正脸。；本镜绑定=CHAR_01/镇魔司制服态、CHAR_03/风尘劲装态、GROUP_01/列队戒备态；资产引用注册层=LOC_02, WEAPON_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01/镇魔司制服态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/镇魔司制服态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：急停对峙成形：陈青源执礼试探，她以『何事』撑住。
- 出点：陈情说完，她仍未接话；心虚被读作深沉。
- 转场：同场景升级为跪求。
- 连贯性：required_presence=CHAR_01、CHAR_03; offscreen_presence=无; forbidden_presence=BEAST_01; eyeline=陈青源仰视画右前；她俯视画左下，避开对视半寸。; inner_focus=无

**continuity**：
- start_state：急停对峙成形：陈青源执礼试探，她以『何事』撑住。
- action：陈青源下马抱拳陈情，信息完整不切碎。；她面沉如水的反打：眼神游移半寸，拇指抠刀柄。
- end_state：陈情说完，她仍未接话；心虚被读作深沉。
- constraints：required_presence=CHAR_01、CHAR_03; offscreen_presence=无; forbidden_presence=BEAST_01; eyeline=陈青源仰视画右前；她俯视画左下，避开对视半寸。
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut; story_span_sec=15.551; edit_target_sec=15.551; backend_request_sec=15.0; action_start_sec=0.25; action_end_sec=14.5; hold_end_sec=15.0; trim_mode=none; requires_split=true; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=64154466ac662baf024f234e27480c6eb6996e808716ce23ab37eefb7045befd
```text
以已提交首帧为视觉真值。 主动作：陈青源下马抱拳陈情，信息完整不切碎。；她面沉如水的反打：眼神游移半寸，拇指抠刀柄。 镜头：固定机位，锁定人物与证据物的构图关系；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：陈青源仰视画右前；她俯视画左下，避开对视半寸；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：常速陈情压内心快切。 时间：0.25-14.50秒完成主动作，持续保持落幅到15.00秒。 结尾停稳在：陈情说完，她仍未接话；心虚被读作深沉。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_06.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 07（时长 12.221s · EP03_CLIP07 · 百十条人命压身）

**首帧**：`出图/第3集/图片/Clip07_first.png`
**尾帧**：`出图/第3集/图片/EP03_CLIP07_a1.png`
**锚帧1**：`出图/第3集/图片/Clip07_first_a1.png`（at_sec=4.0）
**锚帧2**：`出图/第3集/图片/EP03_CLIP07_a1.png`（at_sec=8.0）
**场景**：LOC_02/官道群跪
**剧本可看性合同**：dramatic_function=由单人陈情升级为群体跪求，虚假的权力高位被拍成道德夹逼；时间线在此追上冷开场。；audience_effect=认出这就是开场那一跪，悬念闭环；替她感到百十条人命压上肩的窒息。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：由单人陈情升级为群体跪求，虚假的权力高位被拍成道德夹逼；时间线在此追上冷开场。
**起幅**：陈情说完，她仍未接话；心虚被读作深沉。
**落幅**：众人齐跪叩首，时间线与冷开场闭合，她被架上高位。
**场面调度**：50mm → 35mm → 85mm；角色=CHAR_01/镇魔司制服态、CHAR_03/风尘劲装态、GROUP_01/齐跪态；资产=LOC_02, WEAPON_横刀；轴线/视线=众人向画右前叩首；她视线从人群缓缓垂落到自己手上。
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：众人向画右前叩首；她视线从人群缓缓垂落到自己手上；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 陈青源沉痛陈述，单膝落地。；众人齐跪叩首，复现冷开场构图，尘土轻扬。；她僵住的手指与强装冷静的脸。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=陈青源单膝落地、众人齐跪复现、姜月初僵住；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**专项镜头模板**：template=ensemble_blocking；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=ensemble_blocking; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=3；anchor_count=2；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第3集/图片/Clip07_first.png；end_frame=出图/第3集/图片/EP03_CLIP07_a1.png；midframes=2；seam_mode=hard_cut；need_end_anchor=True；transition=情绪峰顶接她的崩溃自嘲。；entry_exit=群跪构图与EP03_CLIP01同锚复现；祠堂惨状仅在台词中。；出画/画外保留：CHAR_03；出画/画外保留：CHAR_03；出画/画外保留：CHAR_03；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=2；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**连续性链路 / Continuity Chain**：入点=第3集/Clip_06→第3集/Clip_07；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=同场景升级为跪求。；from_end=陈情说完，她仍未接话；心虚被读作深沉。；to_start=陈情说完，她仍未接话；心虚被读作深沉。；出点=第3集/Clip_07→第3集/Clip_08；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=情绪峰顶接她的崩溃自嘲。；from_end=众人齐跪叩首，时间线与冷开场闭合，她被架上高位。；to_start=众人齐跪叩首，时间线与冷开场闭合，她被架上高位。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=2；consumption_mode=native_multiframe；native_timeline_frames=4；reference_inputs=characters=character_id=CHAR_01；form=镇魔司制服态；binding=native_identity_lock_required、character_id=CHAR_03；form=风尘劲装态；binding=native_identity_lock_required、binding=native_identity_lock_required；assets=LOC_02；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；identity_preservation_plan=required_identity_anchors=face_shape、hairstyle、age_read、outfit_palette、named_character_screen_slot；reference_strategy=native_identity_lock_required；motion_readability_allowances=prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups、allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot、keep first/end frame and registered reference group as identity truth when motion control needs simpler movement；fallback_plan=If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.；applies_to=ensemble_blocking；control_inputs=manifest_path=出视频/第3集/control/Clip_07/motion_control_manifest.json；required=True；required_inputs=pose_sequence、depth_sequence、instance_masks；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=base_video_then_post_lipsync；timing_basis=text_estimate_no_audio；performance_track_status=missing；requires_performance_audio_before_final=True；post_lipsync_required=True；base_video_only=True；base_video_mouth_policy=neutral_rest_no_visible_articulation；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=2；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第3集/control/Clip_07/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**角色身份注册层**：CHAR_01/镇魔司制服态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；CHAR_03/风尘劲装态：reference_group=ready；registry_form=常态；锚点句=03·03 的剧情视觉真值必须入画：本集入镜角色；成年古装角色，年龄感按剧情身份保守处理；03 的脸型、年龄感、肤色和五官比例必须稳定；五官清楚耐看，不使用同质化网红脸。·03 穿低饱和古装衣袍，领口、袖口、腰带和下摆结构稳定，不出现现代服饰。；GROUP_01/齐跪态：reference_group=ready；registry_form=常态；锚点句=GROUP_01·GROUP_01 的剧情视觉真值必须入画：本集入镜角色；三至五名低饱和粗布背景人群，只保留肩线、侧后轮廓和虚化嘴形，不建立清晰正脸。·三至五名低饱和粗布背景人群，只保留肩线、侧后轮廓和虚化嘴形，不建立清晰正脸。；本镜绑定=CHAR_01/镇魔司制服态、CHAR_03/风尘劲装态、GROUP_01/齐跪态；资产引用注册层=LOC_02, WEAPON_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01/镇魔司制服态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/镇魔司制服态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：陈情说完，她仍未接话；心虚被读作深沉。
- 出点：众人齐跪叩首，时间线与冷开场闭合，她被架上高位。
- 转场：情绪峰顶接她的崩溃自嘲。
- 连贯性：required_presence=CHAR_01、CHAR_03、GROUP_01; offscreen_presence=无; forbidden_presence=BEAST_01; eyeline=众人向画右前叩首；她视线从人群缓缓垂落到自己手上。; inner_focus=无

**continuity**：
- start_state：陈情说完，她仍未接话；心虚被读作深沉。
- action：陈青源沉痛陈述，单膝落地。；众人齐跪叩首，复现冷开场构图，尘土轻扬。；她僵住的手指与强装冷静的脸。
- end_state：众人齐跪叩首，时间线与冷开场闭合，她被架上高位。
- constraints：required_presence=CHAR_01、CHAR_03、GROUP_01; offscreen_presence=无; forbidden_presence=BEAST_01; eyeline=众人向画右前叩首；她视线从人群缓缓垂落到自己手上。
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut; story_span_sec=12.221; edit_target_sec=12.221; backend_request_sec=13.0; action_start_sec=0.25; action_end_sec=11.721; hold_end_sec=12.221; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=ad7cfae5cd828e95f8af2f42a5be9f03ae1334582f51d54908338cf1272f215c
```text
以已提交首帧为视觉真值。 主动作：陈青源沉痛陈述，单膝落地。；众人齐跪叩首，复现冷开场构图，尘土轻扬。；她僵住的手指与强装冷静的脸。 镜头：固定机位，锁定人物与戏内视线目标的相对关系；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：众人向画右前叩首；她视线从人群缓缓垂落到自己手上；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：层层加压至情绪峰。 时间：0.25-11.72秒完成主动作，持续保持落幅到12.22秒。12.22-13.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：众人齐跪叩首，时间线与冷开场闭合，她被架上高位。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_07.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 08（时长 11.534s · EP03_CLIP08 · 被迫接局·集尾）

**首帧**：`出图/第3集/图片/Clip08_first.png`
**尾帧**：`出图/第3集/图片/EP03_CLIP08_a1.png`
**锚帧1**：`出图/第3集/图片/EP03_CLIP08_a1.png`（at_sec=8.5）
**场景**：LOC_02/官道集尾
**剧本可看性合同**：dramatic_function=她对老天的怨怼化作破罐子破摔的决意；三重死局并置，集尾悬置在『能否活着回来』。；audience_effect=在她自嘲中获得反差爽感，又被『活着回来吗』钉进下一集。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：她对老天的怨怼化作破罐子破摔的决意；三重死局并置，集尾悬置在『能否活着回来』。
**起幅**：众人齐跪叩首，时间线与冷开场闭合，她被架上高位。
**落幅**：她默认接下驰援，集尾定格切黑；狼妖村之行悬置到第4集。
**场面调度**：85mm → 85mm；角色=CHAR_01/镇魔司制服态、GROUP_01/齐跪态焦外；资产=LOC_02, WEAPON_横刀；轴线/视线=先仰望画上方，后平视画左前众人。
**视线表演合同**：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：先仰望画上方，后平视画左前众人；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。
**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。
**内心戏主体隔离**：非内心戏/按 entity_schedule 在场链执行
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 仰头苦笑三声，喉头滚动，怨怼老天。；压平呼吸转身面向众人，眼底疲惫与决意并存，定格切黑。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；人物动作在画内完成，摄影机运动不与表演争夺注意
- 能量：静止
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。
**动作编排契约 / Action Choreography**：beats=姜月初仰头苦笑、压平呼吸、转身面对跪众；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**专项镜头模板**：template=ensemble_blocking；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=ensemble_blocking; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=native_identity_lock_required; degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**帧策略 / Frame Strategy**：strategy=edit_cut；reason=multiple_editorial_shots_require_hard_cut_coverage；shot_count=2；anchor_count=1；首尾帧后端不得把 split relay 冒充原生三帧。
**接缝执行包 / Handoff Package**：first_frame=出图/第3集/图片/Clip08_first.png；end_frame=出图/第3集/图片/EP03_CLIP08_a1.png；midframes=1；seam_mode=hard_cut；need_end_anchor=True；transition=切黑收束，第4集冷开接踏上驰援之路。；entry_exit=本集人物无新增退场；三重压力以台词并置收束。；出画/画外保留：CHAR_03；出画/画外保留：CHAR_03；出画/画外保留：CHAR_03；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts；fallback=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**连续性链路 / Continuity Chain**：入点=第3集/Clip_07→第3集/Clip_08；scope=intra_episode；policy=design_cut；strictness=mode_specific；transition=情绪峰顶接她的崩溃自嘲。；from_end=众人齐跪叩首，时间线与冷开场闭合，她被架上高位。；to_start=众人齐跪叩首，时间线与冷开场闭合，她被架上高位。；出点=第2集/Clip_08→第3集/Clip_01；scope=episode_boundary；policy=intentional_discontinuity；strictness=mode_specific；transition=第2集墨虎眼亮后切黑；第3集以稍后的官道群跪倒叙冷开，再回到埋尸时点；from_end=墨虎双眼短亮，姜月初未得到答案，切黑；to_start=未来片段：众人已跪，姜月初已着镇魔司制服。；intentional_discontinuity=长线摉影进阶承诺延后处理；本集先承接杀裴的现实后果和身份代价。
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；form=镇魔司制服态；binding=native_identity_lock_required、binding=native_identity_lock_required；assets=LOC_02；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；identity_preservation_plan=required_identity_anchors=face_shape、hairstyle、age_read、outfit_palette、named_character_screen_slot；reference_strategy=native_identity_lock_required；motion_readability_allowances=prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups、allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot、keep first/end frame and registered reference group as identity truth when motion control needs simpler movement；fallback_plan=If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.；applies_to=ensemble_blocking；control_inputs=manifest_path=出视频/第3集/control/Clip_08/motion_control_manifest.json；required=True；required_inputs=pose_sequence、depth_sequence、instance_masks；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；audio_strategy=base_video_then_post_lipsync；timing_basis=text_estimate_no_audio；performance_track_status=missing；requires_performance_audio_before_final=True；post_lipsync_required=True；base_video_only=True；base_video_mouth_policy=neutral_rest_no_visible_articulation；post_video_qc=identity_qc_required=True；dense_face_watch_required=True；required_reports=video_qc、temporal_consistency、video_face_drift_watch；sample_policy=start/mid/end machine QC plus dense human frame review on clear-face windows；acceptance_policy=block_clear_wrong_closeup_face; block_dense_warn_until_human_review; no VLM/signoff override for true face drift；return_to_stage=video_or_image_then_compose；fallback=fallback_backends=dreamina；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=edit_cut；frame_strategy=edit_cut；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=generate separate physical takes for storyboard shots and join them with editorial cuts
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第3集/control/Clip_08/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；degrade_plan=先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。
**角色身份注册层**：CHAR_01/镇魔司制服态：reference_group=ready；registry_form=“囚途残损态”；锚点句=窄椭圆脸利落下颌·细长杏眼锐利目光·乌黑松散长发·高挑纤细·灰褐窄袖囚服；GROUP_01/齐跪态焦外：reference_group=ready；registry_form=常态；锚点句=GROUP_01·GROUP_01 的剧情视觉真值必须入画：本集入镜角色；三至五名低饱和粗布背景人群，只保留肩线、侧后轮廓和虚化嘴形，不建立清晰正脸。·三至五名低饱和粗布背景人群，只保留肩线、侧后轮廓和虚化嘴形，不建立清晰正脸。；本镜绑定=CHAR_01/镇魔司制服态、GROUP_01/齐跪态焦外；资产引用注册层=LOC_02, WEAPON_横刀。
**近景/反打身份锁定**：主焦点=CHAR_01/镇魔司制服态；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**近景升格守卫**：近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 CHAR_01/镇魔司制服态 直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。
**尾端落幅保持**：最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；offscreen_presence=CHAR_03 不得在剪点前被拉回清晰脸、全身主体或新增动作。若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：众人齐跪叩首，时间线与冷开场闭合，她被架上高位。
- 出点：她默认接下驰援，集尾定格切黑；狼妖村之行悬置到第4集。
- 转场：切黑收束，第4集冷开接踏上驰援之路。
- 连贯性：required_presence=CHAR_01; offscreen_presence=CHAR_03; forbidden_presence=BEAST_01; eyeline=先仰望画上方，后平视画左前众人。; inner_focus=无

**continuity**：
- start_state：众人齐跪叩首，时间线与冷开场闭合，她被架上高位。
- action：仰头苦笑三声，喉头滚动，怨怼老天。；压平呼吸转身面向众人，眼底疲惫与决意并存，定格切黑。
- end_state：她默认接下驰援，集尾定格切黑；狼妖村之行悬置到第4集。
- constraints：required_presence=CHAR_01; offscreen_presence=CHAR_03; forbidden_presence=BEAST_01; eyeline=先仰望画上方，后平视画左前众人。
- negative：禁止：换脸或五官比例漂移；换衣或发型漂移；新增未登记人物或道具；改变场景、光位或构图；随机文字、logo 或水印；无剧情动机的正视镜头、迎镜头转脸或对镜表演；原生人声；表情变化不得改变脸型、眼距、鼻梁或下颌。 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。

**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。

### 后端编译提交 prompt
**编译元数据**：kind=n2d_compiled_video_prompt; version=2; profile_version=2026-07-22.1; profile=zh_motion_first; backend=seedance; mode=image2video; language=zh; native_audio_policy=none; frame_strategy=edit_cut; story_span_sec=11.534; edit_target_sec=11.534; backend_request_sec=12.0; action_start_sec=0.25; action_end_sec=11.034; hold_end_sec=11.534; trim_mode=trim_tail; requires_split=false; duration_quantization=integer_range:4-15/step=1; source_contract_sha256=6957768ede64fb0e44804102c50786ad87451c434b586cd31ae7d3eac5b6182b
```text
以已提交首帧为视觉真值。 主动作：仰头苦笑三声，喉头滚动，怨怼老天。；压平呼吸转身面向众人，眼底疲惫与决意并存，定格切黑。 镜头：固定机位，锁定人物与戏内视线目标的相对关系；摄影机保持完全静止，人物呼吸与环境微动留在画内。 视线与头部朝向：摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：先仰望画上方，后平视画左前众人；人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。 节奏：慢·崩溃自嘲收束成死局定格。 时间：0.25-11.03秒完成主动作，持续保持落幅到11.53秒。11.53-12.00秒只保持落幅供后期裁切，不开始新动作。 结尾停稳在：她默认接下驰援，集尾定格切黑；狼妖村之行悬置到第4集。 仅保留已登记主体；人物身份、服装、构图与光位保持稳定；画面保持干净，不增加文字或水印。
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
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_08.mp4`；失败进废料并改 prompt/拆 Clip。
