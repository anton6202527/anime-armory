# 第3集 视频 Clip prompt

## 本集留存承诺账本（script_quality_contract）

- R01: hook_id=EP02_TAIL_HOOK_PAYOFF；opened_at=EP02_CLIP10；payoff_clip=EP03_CLIP05；payoff_due=第3集 EP03_CLIP05；payoff_status=paid；promise=火把马蹄逼近尸场，来者会如何判断姜月初。；promise_type=opening_payoff
- R02: hook_id=EP03_IDENTITY_SKIN；opened_at=EP03_CLIP03；payoff_clip=EP03_CLIP06；payoff_due=第3集 EP03_CLIP06-07；payoff_status=paid；promise=镇魔司黑衣能给她临时身份，也会带来追查和责任。；promise_type=mid_hook
- R03: hook_id=EP03_TAIL_CHOICE；opened_at=EP03_CLIP10；payoff_due=第4集 EP04_CLIP01；payoff_status=open；promise=她成为上盘村唯一希望；救人会暴露，拒绝最安全。；promise_type=tail_hook

## Clip 01（时长 10.880s · EP03_CLIP01 · 埋尸冷开：欠命账落地）

**首帧**：`出图/第3集/图片/Clip01_first.png`
**尾帧**：`出图/第3集/图片/Clip01_end.png`
**锚帧1**：`出图/第3集/图片/Clip01_first_a1.png`（at_sec=3.09）
**锚帧2**：`出图/第3集/图片/Clip01_first_a2.png`（at_sec=6.18）
**锚帧3**：`出图/第3集/图片/Clip01_first_a3.png`（at_sec=9.27）
**场景**：LOC_01 荒野尸骸战场/冷灰月夜/外
**剧本可看性合同**：dramatic_function=冷开承接第2集尾声后的道德债：她亲手埋掉被自己刺死的裴长青，观众立刻读到欠命与求生并存。；audience_effect=观众先被“她杀了人还要亲手埋”抓住，再追问她会不会因此软下来。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：冷开承接第2集尾声后的道德债：她亲手埋掉被自己刺死的裴长青，观众立刻读到欠命与求生并存。
**起幅**：冷灰月夜下的浅坑占画面下半部，姜月初半跪撒土，裴长青遗体只保留低位轮廓。
**落幅**：姜月初从浅坑旁转向尸场物资，手在包裹前停了一拍。
**场面调度**：LS 低机位固定 → CU 手部到侧脸；角色=CHAR_01、CHAR_02；资产=LOC_01, WEAPON_01 横刀；轴线/视线=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 半跪撒土的动作很小，土粒落下后停半拍，画面保持冷灰写实3D国风漫剧，纵向9:16。；手从土上收回，侧脸微微垂下，情绪克制，不让遗体复活或说话。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=冷灰尸场建立、姜月初半跪撒土、裴长青遗体低位半掩、手部收回切向亏欠侧脸；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.
**专项镜头模板**：template=multi_character_same_frame；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=multi_character_same_frame; primary_backend=seedance; fallback=dreamina; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=3；consumption_mode=native_multiframe；native_timeline_frames=5；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_02；binding=character_id_or_reference_group；assets=LOC_01、LOC_02；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；identity_preservation_plan=required_identity_anchors=face_shape、hairstyle、age_read、outfit_palette、named_character_screen_slot；reference_strategy=character_id_or_reference_group；motion_readability_allowances=prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups、allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot、keep first/end frame and registered reference group as identity truth when motion control needs simpler movement；fallback_plan=If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.；applies_to=multi_character_same_frame；control_inputs=manifest_path=出视频/第3集/control/Clip_01/motion_control_manifest.json；required=True；required_inputs=pose_sequence、depth_sequence、instance_masks；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=3；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第3集/control/Clip_01/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；本镜绑定=CHAR_01、CHAR_02；资产引用注册层=LOC_01, WEAPON_01 横刀。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：冷灰月夜下的浅坑占画面下半部，姜月初半跪撒土，裴长青遗体只保留低位轮廓。
- 出点：姜月初从浅坑旁转向尸场物资，手在包裹前停了一拍。
- 转场：match_cut
- 连贯性：required_presence=CHAR_01、CHAR_02、WEAPON_01 横刀、LOC_01; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。

**continuity**：
- start_state：冷灰月夜下的浅坑占画面下半部，姜月初半跪撒土，裴长青遗体只保留低位轮廓。
- action：半跪撒土的动作很小，土粒落下后停半拍，画面保持冷灰写实3D国风漫剧，纵向9:16。；手从土上收回，侧脸微微垂下，情绪克制，不让遗体复活或说话。
- end_state：姜月初从浅坑旁转向尸场物资，手在包裹前停了一拍。
- constraints：required_presence=CHAR_01、CHAR_02、WEAPON_01 横刀、LOC_01; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 冷灰月夜下的浅坑占画面下半部，姜月初半跪撒土，裴长青遗体只保留低位轮廓。
  action: 半跪撒土的动作很小，土粒落下后停半拍，画面保持冷灰写实3D国风漫剧，纵向9:16。；手从土上收回，侧脸微微垂下，情绪克制，不让遗体复活或说话。
  end_state: 姜月初从浅坑旁转向尸场物资，手在包裹前停了一拍。
  constraints: required_presence=CHAR_01、CHAR_02、WEAPON_01 横刀、LOC_01; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。
剧本可看性合同：dramatic_function=冷开承接第2集尾声后的道德债：她亲手埋掉被自己刺死的裴长青，观众立刻读到欠命与求生并存。; audience_effect=观众先被“她杀了人还要亲手埋”抓住，再追问她会不会因此软下来。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：冷开承接第2集尾声后的道德债：她亲手埋掉被自己刺死的裴长青，观众立刻读到欠命与求生并存。;
起幅：冷灰月夜下的浅坑占画面下半部，姜月初半跪撒土，裴长青遗体只保留低位轮廓。;
落幅：姜月初从浅坑旁转向尸场物资，手在包裹前停了一拍。;
场面调度：LS 低机位固定 → CU 手部到侧脸；角色槽位=CHAR_01、CHAR_02；资产ID=LOC_01, WEAPON_01 横刀；
表演节拍：[0-30%] 承接首帧；[30-75%] 半跪撒土的动作很小，土粒落下后停半拍，画面保持冷灰写实3D国风漫剧，纵向9:16。；手从土上收回，侧脸微微垂下，情绪克制，不让遗体复活或说话。；[75-100%] 姜月初从浅坑旁转向尸场物资，手在包裹前停了一拍。;
运动精修约束：幅度=小到中；人物槽位不漂移；能量=克制；表情和视线先动，身体后动；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=冷灰尸场建立、姜月初半跪撒土、裴长青遗体低位半掩、手部收回切向亏欠侧脸；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.；
专项模板约束：template=multi_character_same_frame；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=frames2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.；
物理交互约束：读取 motion_control_manifest.json；level=required；manifest_path=出视频/第3集/control/Clip_01/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；degrade_plan=If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态：reference_group=ready；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=大；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：半跪撒土的动作很小，土粒落下后停半拍，画面保持冷灰写实3D国风漫剧，纵向9:16。；手从土上收回，侧脸微微垂下，情绪克制，不让遗体复活或说话。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或缓慢推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务冷开钩子；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按match_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 冷灰月夜下的浅坑占画面下半部，姜月初半跪撒土，裴长青遗体只保留低位轮廓。; perform only 半跪撒土的动作很小，土粒落下后停半拍，画面保持冷灰写实3D国风漫剧，纵向9:16。；手从土上收回，侧脸微微垂下，情绪克制，不让遗体复活或说话。; end on 姜月初从浅坑旁转向尸场物资，手在包裹前停了一拍。; preserve required_presence=CHAR_01、CHAR_02、WEAPON_01 横刀、LOC_01; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
director intent: 冷开承接第2集尾声后的道德债：她亲手埋掉被自己刺死的裴长青，观众立刻读到欠命与求生并存。; audience effect: 观众先被“她杀了人还要亲手埋”抓住，再追问她会不会因此软下来。.
character motion: 半跪撒土的动作很小，土粒落下后停半拍，画面保持冷灰写实3D国风漫剧，纵向9:16。；手从土上收回，侧脸微微垂下，情绪克制，不让遗体复活或说话。; camera motion: 固定或缓慢推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
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
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_01.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 02（时长 11.778s · EP03_CLIP02 · 搜尸求生：生存物资）

**首帧**：`出图/第3集/图片/Clip02_first.png`
**尾帧**：`出图/第3集/图片/Clip02_end.png`
**中段锚帧**：`出图/第3集/图片/Clip02_mid.png`
**场景**：LOC_01 荒野尸骸战场/冷灰月夜/外
**剧本可看性合同**：dramatic_function=把道德迟疑转成生存动作：死人不会再喊疼，活人还要银子、水囊、肉脯和衣服。；audience_effect=观众理解她不是无情扫荡，而是在极端环境里把恶心压下去。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：把道德迟疑转成生存动作：死人不会再喊疼，活人还要银子、水囊、肉脯和衣服。
**起幅**：姜月初从浅坑旁转向尸场物资，手在包裹前停了一拍。
**落幅**：姜月初手里拎起黑衣赤纹，尸场仍在身后。
**场面调度**：MS 横移 → INSERT 物资三连；角色=CHAR_01；资产=LOC_01, PROP_尸场物资包；轴线/视线=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 横移很慢，展示尸场空间和她的生存压力。；道具插入清晰，黑衣边角作为下一 Clip 的视觉接力。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；只执行本镜主动作链
- 能量：克制匀速
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=按 storyboard shots 顺序执行；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.
**专项镜头模板**：template=none；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=general_motion; primary_backend=dreamina; fallback=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=1；consumption_mode=native_multiframe；native_timeline_frames=3；reference_inputs=characters=character_id=CHAR_01；binding=reference_group；assets=LOC_01、LOC_02；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=seedance；degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.；anchor_consumption=backend=dreamina；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=1；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；本镜绑定=CHAR_01；资产引用注册层=LOC_01, PROP_尸场物资包。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：姜月初从浅坑旁转向尸场物资，手在包裹前停了一拍。
- 出点：姜月初手里拎起黑衣赤纹，尸场仍在身后。
- 转场：match_cut
- 连贯性：required_presence=CHAR_01、PROP_尸场物资包、LOC_01; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。

**continuity**：
- start_state：姜月初从浅坑旁转向尸场物资，手在包裹前停了一拍。
- action：横移很慢，展示尸场空间和她的生存压力。；道具插入清晰，黑衣边角作为下一 Clip 的视觉接力。
- end_state：姜月初手里拎起黑衣赤纹，尸场仍在身后。
- constraints：required_presence=CHAR_01、PROP_尸场物资包、LOC_01; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 姜月初从浅坑旁转向尸场物资，手在包裹前停了一拍。
  action: 横移很慢，展示尸场空间和她的生存压力。；道具插入清晰，黑衣边角作为下一 Clip 的视觉接力。
  end_state: 姜月初手里拎起黑衣赤纹，尸场仍在身后。
  constraints: required_presence=CHAR_01、PROP_尸场物资包、LOC_01; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。
剧本可看性合同：dramatic_function=把道德迟疑转成生存动作：死人不会再喊疼，活人还要银子、水囊、肉脯和衣服。; audience_effect=观众理解她不是无情扫荡，而是在极端环境里把恶心压下去。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：把道德迟疑转成生存动作：死人不会再喊疼，活人还要银子、水囊、肉脯和衣服。;
起幅：姜月初从浅坑旁转向尸场物资，手在包裹前停了一拍。;
落幅：姜月初手里拎起黑衣赤纹，尸场仍在身后。;
场面调度：MS 横移 → INSERT 物资三连；角色槽位=CHAR_01；资产ID=LOC_01, PROP_尸场物资包；
表演节拍：[0-30%] 承接首帧；[30-75%] 横移很慢，展示尸场空间和她的生存压力。；道具插入清晰，黑衣边角作为下一 Clip 的视觉接力。；[75-100%] 姜月初手里拎起黑衣赤纹，尸场仍在身后。;
运动精修约束：幅度=小幅；只执行本镜主动作链；能量=克制匀速；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=按 storyboard shots 顺序执行；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.；
专项模板约束：template=none；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=dreamina，fallback=seedance，mode=image2video，native_audio_policy=none，identity_requirement=reference_group；失败按 degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.；
物理交互约束：读取 motion_control_manifest.json；level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=中；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：横移很慢，展示尸场空间和她的生存压力。；道具插入清晰，黑衣边角作为下一 Clip 的视觉接力。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或极缓推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务生存压力；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按match_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 姜月初从浅坑旁转向尸场物资，手在包裹前停了一拍。; perform only 横移很慢，展示尸场空间和她的生存压力。；道具插入清晰，黑衣边角作为下一 Clip 的视觉接力。; end on 姜月初手里拎起黑衣赤纹，尸场仍在身后。; preserve required_presence=CHAR_01、PROP_尸场物资包、LOC_01; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
director intent: 把道德迟疑转成生存动作：死人不会再喊疼，活人还要银子、水囊、肉脯和衣服。; audience effect: 观众理解她不是无情扫荡，而是在极端环境里把恶心压下去。.
character motion: 横移很慢，展示尸场空间和她的生存压力。；道具插入清晰，黑衣边角作为下一 Clip 的视觉接力。; camera motion: 固定或极缓推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
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
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_02.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 03（时长 24.832s · EP03_CLIP03 · 黑衣赤纹：借来的官威）

**首帧**：`出图/第3集/图片/Clip03_first.png`
**尾帧**：`出图/第3集/图片/Clip03_end.png`
**锚帧1**：`出图/第3集/图片/Clip03_first_a1.png`（at_sec=4.91）
**锚帧2**：`出图/第3集/图片/Clip03_first_a2.png`（at_sec=9.81）
**锚帧3**：`出图/第3集/图片/Clip03_first_a3.png`（at_sec=14.72）
**锚帧4**：`出图/第3集/图片/Clip03_first_a4.png`（at_sec=19.62）
**场景**：LOC_01 荒野尸骸战场/冷灰月夜/外
**剧本可看性合同**：dramatic_function=完成从囚犯逃亡态到镇魔司伪装态的视觉转身，给后面误认做因果铺垫。；audience_effect=观众获得第一个外形爽点：她终于不再像刚从死牢里爬出来。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：完成从囚犯逃亡态到镇魔司伪装态的视觉转身，给后面误认做因果铺垫。
**起幅**：姜月初手里拎起黑衣赤纹，尸场仍在身后。
**落幅**：她握住横刀后抬眼，看向官道深处。
**场面调度**：CU 衣纹 → MS 完成态 → CU 腰刀/眼神；角色=CHAR_01；资产=LOC_01, PROP_镇魔司黑衣赤纹, WEAPON_01 横刀；轴线/视线=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 衣纹不生成文字，赤纹只是图案。；动作克制，不拍裸露换衣过程，只拍完成态与道歉。；横刀固定在腰侧，脸不换人，黑衣赤纹形成身份锚。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=按 storyboard shots 顺序执行；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**专项镜头模板**：template=none；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=4；consumption_mode=native_multiframe；native_timeline_frames=6；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group；assets=LOC_01、LOC_02；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=4；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；本镜绑定=CHAR_01；资产引用注册层=LOC_01, PROP_镇魔司黑衣赤纹, WEAPON_01 横刀。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：姜月初手里拎起黑衣赤纹，尸场仍在身后。
- 出点：她握住横刀后抬眼，看向官道深处。
- 转场：eyeline_cut
- 连贯性：required_presence=CHAR_01、PROP_镇魔司黑衣赤纹、WEAPON_01 横刀、LOC_01; offscreen_presence=CHAR_02; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。

**continuity**：
- start_state：姜月初手里拎起黑衣赤纹，尸场仍在身后。
- action：衣纹不生成文字，赤纹只是图案。；动作克制，不拍裸露换衣过程，只拍完成态与道歉。；横刀固定在腰侧，脸不换人，黑衣赤纹形成身份锚。
- end_state：她握住横刀后抬眼，看向官道深处。
- constraints：required_presence=CHAR_01、PROP_镇魔司黑衣赤纹、WEAPON_01 横刀、LOC_01; offscreen_presence=CHAR_02; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 姜月初手里拎起黑衣赤纹，尸场仍在身后。
  action: 衣纹不生成文字，赤纹只是图案。；动作克制，不拍裸露换衣过程，只拍完成态与道歉。；横刀固定在腰侧，脸不换人，黑衣赤纹形成身份锚。
  end_state: 她握住横刀后抬眼，看向官道深处。
  constraints: required_presence=CHAR_01、PROP_镇魔司黑衣赤纹、WEAPON_01 横刀、LOC_01; offscreen_presence=CHAR_02; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。
剧本可看性合同：dramatic_function=完成从囚犯逃亡态到镇魔司伪装态的视觉转身，给后面误认做因果铺垫。; audience_effect=观众获得第一个外形爽点：她终于不再像刚从死牢里爬出来。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：完成从囚犯逃亡态到镇魔司伪装态的视觉转身，给后面误认做因果铺垫。;
起幅：姜月初手里拎起黑衣赤纹，尸场仍在身后。;
落幅：她握住横刀后抬眼，看向官道深处。;
场面调度：CU 衣纹 → MS 完成态 → CU 腰刀/眼神；角色槽位=CHAR_01；资产ID=LOC_01, PROP_镇魔司黑衣赤纹, WEAPON_01 横刀；
表演节拍：[0-30%] 承接首帧；[30-75%] 衣纹不生成文字，赤纹只是图案。；动作克制，不拍裸露换衣过程，只拍完成态与道歉。；横刀固定在腰侧，脸不换人，黑衣赤纹形成身份锚。；[75-100%] 她握住横刀后抬眼，看向官道深处。;
运动精修约束：幅度=小到中；人物槽位不漂移；能量=克制；表情和视线先动，身体后动；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=按 storyboard shots 顺序执行；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
专项模板约束：template=none；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=image2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
物理交互约束：读取 motion_control_manifest.json；level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=中；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：衣纹不生成文字，赤纹只是图案。；动作克制，不拍裸露换衣过程，只拍完成态与道歉。；横刀固定在腰侧，脸不换人，黑衣赤纹形成身份锚。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或缓慢推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务身份转身；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按eyeline_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 姜月初手里拎起黑衣赤纹，尸场仍在身后。; perform only 衣纹不生成文字，赤纹只是图案。；动作克制，不拍裸露换衣过程，只拍完成态与道歉。；横刀固定在腰侧，脸不换人，黑衣赤纹形成身份锚。; end on 她握住横刀后抬眼，看向官道深处。; preserve required_presence=CHAR_01、PROP_镇魔司黑衣赤纹、WEAPON_01 横刀、LOC_01; offscreen_presence=CHAR_02; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
director intent: 完成从囚犯逃亡态到镇魔司伪装态的视觉转身，给后面误认做因果铺垫。; audience effect: 观众获得第一个外形爽点：她终于不再像刚从死牢里爬出来。.
character motion: 衣纹不生成文字，赤纹只是图案。；动作克制，不拍裸露换衣过程，只拍完成态与道歉。；横刀固定在腰侧，脸不换人，黑衣赤纹形成身份锚。; camera motion: 固定或缓慢推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
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
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_03.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 04（时长 33.363s · EP03_CLIP04 · 掌心刀法与身份死局）

**首帧**：`出图/第3集/图片/Clip04_first.png`
**尾帧**：`出图/第3集/图片/Clip04_end.png`
**锚帧1**：`出图/第3集/图片/Clip04_first_a1.png`（at_sec=4.77）
**锚帧2**：`出图/第3集/图片/Clip04_first_a2.png`（at_sec=9.53）
**锚帧3**：`出图/第3集/图片/Clip04_first_a3.png`（at_sec=14.3）
**锚帧4**：`出图/第3集/图片/Clip04_first_a4.png`（at_sec=19.06）
**锚帧5**：`出图/第3集/图片/Clip04_first_a5.png`（at_sec=23.83）
**锚帧6**：`出图/第3集/图片/Clip04_first_a6.png`（at_sec=28.6）
**场景**：LOC_02 荒野官道夜路/冷月/外
**剧本可看性合同**：dramatic_function=刀法记忆让她短暂稳住，但无户籍无路引的死局马上把“活得像个人”变成主线问题。；audience_effect=观众从换装爽点转到新问题：这层皮能不能让她进城活下去。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：刀法记忆让她短暂稳住，但无户籍无路引的死局马上把“活得像个人”变成主线问题。
**起幅**：她握住横刀后抬眼，看向官道深处。
**落幅**：官道远景，孤月下她独自走在路中。
**场面调度**：CU 手握刀柄 → ELS 官道孤人 → MCU 侧脸；角色=CHAR_01；资产=LOC_02, WEAPON_01 横刀；轴线/视线=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 刀不出鞘，微光很克制，不做魔法爆炸。；人物比例小，空间压力大，官道方向锁定。；侧脸看向远处城路，不出现现代证件。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；高光点只给一次明确动作
- 能量：蓄力后定住
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=按 storyboard shots 顺序执行；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Use Dreamina/Seedance silent clip and add SFX/BGM in compose.
**专项镜头模板**：template=none；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=empty_establishing; primary_backend=dreamina; fallback=seedance; mode=image2video; native_audio_policy=none; identity_requirement=reference_group; degrade_plan=Use Dreamina/Seedance silent clip and add SFX/BGM in compose.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=6；consumption_mode=native_multiframe；native_timeline_frames=8；reference_inputs=characters=character_id=CHAR_01；binding=reference_group；assets=LOC_02、LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=seedance；degrade_plan=Use Dreamina/Seedance silent clip and add SFX/BGM in compose.；anchor_consumption=backend=dreamina；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=6；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Use Dreamina/Seedance silent clip and add SFX/BGM in compose.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；本镜绑定=CHAR_01；资产引用注册层=LOC_02, WEAPON_01 横刀。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：她握住横刀后抬眼，看向官道深处。
- 出点：官道远景，孤月下她独自走在路中。
- 转场：j_cut
- 连贯性：required_presence=CHAR_01、WEAPON_01 横刀、LOC_02; offscreen_presence=CHAR_02; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。

**continuity**：
- start_state：她握住横刀后抬眼，看向官道深处。
- action：刀不出鞘，微光很克制，不做魔法爆炸。；人物比例小，空间压力大，官道方向锁定。；侧脸看向远处城路，不出现现代证件。
- end_state：官道远景，孤月下她独自走在路中。
- constraints：required_presence=CHAR_01、WEAPON_01 横刀、LOC_02; offscreen_presence=CHAR_02; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 她握住横刀后抬眼，看向官道深处。
  action: 刀不出鞘，微光很克制，不做魔法爆炸。；人物比例小，空间压力大，官道方向锁定。；侧脸看向远处城路，不出现现代证件。
  end_state: 官道远景，孤月下她独自走在路中。
  constraints: required_presence=CHAR_01、WEAPON_01 横刀、LOC_02; offscreen_presence=CHAR_02; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。
剧本可看性合同：dramatic_function=刀法记忆让她短暂稳住，但无户籍无路引的死局马上把“活得像个人”变成主线问题。; audience_effect=观众从换装爽点转到新问题：这层皮能不能让她进城活下去。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：刀法记忆让她短暂稳住，但无户籍无路引的死局马上把“活得像个人”变成主线问题。;
起幅：她握住横刀后抬眼，看向官道深处。;
落幅：官道远景，孤月下她独自走在路中。;
场面调度：CU 手握刀柄 → ELS 官道孤人 → MCU 侧脸；角色槽位=CHAR_01；资产ID=LOC_02, WEAPON_01 横刀；
表演节拍：[0-30%] 承接首帧；[30-75%] 刀不出鞘，微光很克制，不做魔法爆炸。；人物比例小，空间压力大，官道方向锁定。；侧脸看向远处城路，不出现现代证件。；[75-100%] 官道远景，孤月下她独自走在路中。;
运动精修约束：幅度=小幅；高光点只给一次明确动作；能量=蓄力后定住；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=按 storyboard shots 顺序执行；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Use Dreamina/Seedance silent clip and add SFX/BGM in compose.；
专项模板约束：template=none；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=dreamina，fallback=seedance，mode=image2video，native_audio_policy=none，identity_requirement=reference_group；失败按 degrade_plan=Use Dreamina/Seedance silent clip and add SFX/BGM in compose.；
物理交互约束：读取 motion_control_manifest.json；level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Use Dreamina/Seedance silent clip and add SFX/BGM in compose.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=中；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：刀不出鞘，微光很克制，不做魔法爆炸。；人物比例小，空间压力大，官道方向锁定。；侧脸看向远处城路，不出现现代证件。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：缓慢推近，尾端定格；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务信息钩子；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按j_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 她握住横刀后抬眼，看向官道深处。; perform only 刀不出鞘，微光很克制，不做魔法爆炸。；人物比例小，空间压力大，官道方向锁定。；侧脸看向远处城路，不出现现代证件。; end on 官道远景，孤月下她独自走在路中。; preserve required_presence=CHAR_01、WEAPON_01 横刀、LOC_02; offscreen_presence=CHAR_02; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
director intent: 刀法记忆让她短暂稳住，但无户籍无路引的死局马上把“活得像个人”变成主线问题。; audience effect: 观众从换装爽点转到新问题：这层皮能不能让她进城活下去。.
character motion: 刀不出鞘，微光很克制，不做魔法爆炸。；人物比例小，空间压力大，官道方向锁定。；侧脸看向远处城路，不出现现代证件。; camera motion: 缓慢推近，尾端定格; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
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
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_04.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 05（时长 23.557s · EP03_CLIP05 · 马队火把齐停）

**首帧**：`出图/第3集/图片/Clip05_first.png`
**尾帧**：`出图/第3集/图片/Clip05_end.png`
**锚帧1**：`出图/第3集/图片/Clip05_a1.png`（at_sec=5.0）
**锚帧2**：`出图/第3集/图片/Clip05_a2.png`（at_sec=11.0）
**锚帧3**：`出图/第3集/图片/Clip05_a3.png`（at_sec=17.0）
**场景**：LOC_02 荒野官道夜路/火把压近/外
**剧本可看性合同**：dramatic_function=第2集尾钩兑现：官道火把和十几骑飞鹰门马队逼近，陈青源把她误认成镇魔司大人。；audience_effect=观众看到追兵疑云变成误会反转，期待她怎么应对。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：第2集尾钩兑现：官道火把和十几骑飞鹰门马队逼近，陈青源把她误认成镇魔司大人。
**起幅**：官道远景，孤月下她独自走在路中。
**落幅**：陈青源问“可是镇魔司的大人当面”，火光照到姜月初脸上。
**场面调度**：ELS 官道纵深 → LS 马队停下 → MS 陈青源下马；角色=CHAR_01、CHAR_04、GROUP_飞鹰门马队；资产=LOC_02, MOUNT_GROUP_01 飞鹰门马匹与火把, PROP_镇魔司黑衣赤纹；轴线/视线=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 火把由远变亮，人物保持前景小体量。；重点是齐停，不追逐不冲撞。；陈青源主脸清楚，后方骑手保持剪影。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：中等；背景/前景视差动，主体不变形
- 能量：匀速压近；关键节点短暂停顿
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=远景火把压近、勒缰停马、陈青源下马看清黑衣、误认镇魔司大人；speed_curve=远景慢压近，中景突然勒停，之后转为静态问话。；spatial_path=从画面深处官道向前景/中景推进，停在姜月初数步外。；camera_path=ELS 固定建立距离，MS 轻推到陈青源下马。；readability_beats=先读到火把、再读到马队停下、最后读到陈青源看清黑衣；degrade_plan=若完整马队不稳，拆为火把远景、马蹄停下、陈青源下马三帧。；keyframe_plan=at_sec=5.0；frame=Clip05_a1；purpose=远景火把压近、at_sec=11.0；frame=Clip05_a2；purpose=勒缰停马、at_sec=17.0；frame=Clip05_a3；purpose=陈青源下马误认；post_cue_points=at_sec=5.0；cue=马蹄声由远变近、at_sec=14.0；cue=勒缰停顿、at_sec=20.0；cue=陈青源开口；physics_guard=马、人、缰绳、地面接触关系明确；马队不穿模、不越轴。；mount_contact=骑手手握缰绳、脚在马镫或落地；马蹄只接触官道，不穿过人物。；gait_cycle=远景小跑到勒停，停下后蹄尘前冲一拍。；screen_direction=马队由画面深处到画右中景，姜月初始终前景偏左。；parallax_layers=前景姜月初、中景官道尘土、后景火把马队、远景冷月；harness_lock=缰绳、鞍具、火把归属清楚；陈青源下马后不再漂浮在马背上。
**专项镜头模板**：template=mount_ride；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=mount_ride; primary_backend=dreamina; fallback=seedance; mode=image2video; native_audio_policy=none; identity_requirement=face_lock_or_reference_group; degrade_plan=Cut to front/back reaction shots or split into approach, pass-by, and exit clips.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=3；consumption_mode=native_multiframe；native_timeline_frames=5；reference_inputs=characters=character_id=CHAR_01；binding=face_lock_or_reference_group、character_id=CHAR_04；binding=face_lock_or_reference_group、binding=face_lock_or_reference_group；assets=LOC_02、LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；identity_preservation_plan=required_identity_anchors=face_shape、hairstyle、age_read、outfit_palette、named_character_screen_slot；reference_strategy=face_lock_or_reference_group；motion_readability_allowances=prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups、allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot、keep first/end frame and registered reference group as identity truth when motion control needs simpler movement；fallback_plan=If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.；applies_to=mount_ride；control_inputs=manifest_path=出视频/第3集/control/Clip_05/motion_control_manifest.json；required=True；required_inputs=pose_sequence、depth_sequence、instance_masks、contact_map、camera_path、spatial_path、parallax_layers；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=seedance；degrade_plan=Cut to front/back reaction shots or split into approach, pass-by, and exit clips.；anchor_consumption=backend=dreamina；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=3；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第3集/control/Clip_05/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path,spatial_path,parallax_layers；failure_modes=rider_mount_contact_drift,gait_cycle_reset,pose_drift,harness_morph,background_stickiness；degrade_plan=Cut to front/back reaction shots or split into approach, pass-by, and exit clips.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_04/常态：reference_group=ready；锚点句=陈青源·虬髯中年门主·深灰黑江湖劲装·火把侧照急迫恭敬·跪地求救。；GROUP_飞鹰门马队：registry form 未在 adapter matrix 摘要中命中，使用首帧+reference_group 兜底。；本镜绑定=CHAR_01、CHAR_04、GROUP_飞鹰门马队；资产引用注册层=LOC_02, MOUNT_GROUP_01 飞鹰门马匹与火把, PROP_镇魔司黑衣赤纹。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：官道远景，孤月下她独自走在路中。
- 出点：陈青源问“可是镇魔司的大人当面”，火光照到姜月初脸上。
- 转场：reaction_cut
- 连贯性：required_presence=CHAR_01、CHAR_04、GROUP_飞鹰门马队、MOUNT_GROUP_01 飞鹰门马匹与火把、PROP_镇魔司黑衣赤纹、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。

**continuity**：
- start_state：官道远景，孤月下她独自走在路中。
- action：火把由远变亮，人物保持前景小体量。；重点是齐停，不追逐不冲撞。；陈青源主脸清楚，后方骑手保持剪影。
- end_state：陈青源问“可是镇魔司的大人当面”，火光照到姜月初脸上。
- constraints：required_presence=CHAR_01、CHAR_04、GROUP_飞鹰门马队、MOUNT_GROUP_01 飞鹰门马匹与火把、PROP_镇魔司黑衣赤纹、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 官道远景，孤月下她独自走在路中。
  action: 火把由远变亮，人物保持前景小体量。；重点是齐停，不追逐不冲撞。；陈青源主脸清楚，后方骑手保持剪影。
  end_state: 陈青源问“可是镇魔司的大人当面”，火光照到姜月初脸上。
  constraints: required_presence=CHAR_01、CHAR_04、GROUP_飞鹰门马队、MOUNT_GROUP_01 飞鹰门马匹与火把、PROP_镇魔司黑衣赤纹、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。
剧本可看性合同：dramatic_function=第2集尾钩兑现：官道火把和十几骑飞鹰门马队逼近，陈青源把她误认成镇魔司大人。; audience_effect=观众看到追兵疑云变成误会反转，期待她怎么应对。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：第2集尾钩兑现：官道火把和十几骑飞鹰门马队逼近，陈青源把她误认成镇魔司大人。;
起幅：官道远景，孤月下她独自走在路中。;
落幅：陈青源问“可是镇魔司的大人当面”，火光照到姜月初脸上。;
场面调度：ELS 官道纵深 → LS 马队停下 → MS 陈青源下马；角色槽位=CHAR_01、CHAR_04、GROUP_飞鹰门马队；资产ID=LOC_02, MOUNT_GROUP_01 飞鹰门马匹与火把, PROP_镇魔司黑衣赤纹；
表演节拍：[0-30%] 承接首帧；[30-75%] 火把由远变亮，人物保持前景小体量。；重点是齐停，不追逐不冲撞。；陈青源主脸清楚，后方骑手保持剪影。；[75-100%] 陈青源问“可是镇魔司的大人当面”，火光照到姜月初脸上。;
运动精修约束：幅度=中等；背景/前景视差动，主体不变形；能量=匀速压近；关键节点短暂停顿；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=远景火把压近、勒缰停马、陈青源下马看清黑衣、误认镇魔司大人；speed_curve=远景慢压近，中景突然勒停，之后转为静态问话。；spatial_path=从画面深处官道向前景/中景推进，停在姜月初数步外。；camera_path=ELS 固定建立距离，MS 轻推到陈青源下马。；readability_beats=先读到火把、再读到马队停下、最后读到陈青源看清黑衣；degrade_plan=若完整马队不稳，拆为火把远景、马蹄停下、陈青源下马三帧。；keyframe_plan=at_sec=5.0；frame=Clip05_a1；purpose=远景火把压近、at_sec=11.0；frame=Clip05_a2；purpose=勒缰停马、at_sec=17.0；frame=Clip05_a3；purpose=陈青源下马误认；post_cue_points=at_sec=5.0；cue=马蹄声由远变近、at_sec=14.0；cue=勒缰停顿、at_sec=20.0；cue=陈青源开口；physics_guard=马、人、缰绳、地面接触关系明确；马队不穿模、不越轴。；mount_contact=骑手手握缰绳、脚在马镫或落地；马蹄只接触官道，不穿过人物。；gait_cycle=远景小跑到勒停，停下后蹄尘前冲一拍。；screen_direction=马队由画面深处到画右中景，姜月初始终前景偏左。；parallax_layers=前景姜月初、中景官道尘土、后景火把马队、远景冷月；harness_lock=缰绳、鞍具、火把归属清楚；陈青源下马后不再漂浮在马背上。；
专项模板约束：template=mount_ride；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=dreamina，fallback=seedance，mode=image2video，native_audio_policy=none，identity_requirement=face_lock_or_reference_group；失败按 degrade_plan=Cut to front/back reaction shots or split into approach, pass-by, and exit clips.；
物理交互约束：读取 motion_control_manifest.json；level=required；manifest_path=出视频/第3集/control/Clip_05/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path,spatial_path,parallax_layers；failure_modes=rider_mount_contact_drift,gait_cycle_reset,pose_drift,harness_morph,background_stickiness；degrade_plan=Cut to front/back reaction shots or split into approach, pass-by, and exit clips.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_04/常态：reference_group=ready；锚点句=陈青源·虬髯中年门主·深灰黑江湖劲装·火把侧照急迫恭敬·跪地求救。；GROUP_飞鹰门马队：registry form 未在 adapter matrix 摘要中命中，使用首帧+reference_group 兜底。；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=大；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：火把由远变亮，人物保持前景小体量。；重点是齐停，不追逐不冲撞。；陈青源主脸清楚，后方骑手保持剪影。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：缓慢跟拍或微推，保持官道轴线；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务外部势力入场；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按reaction_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 官道远景，孤月下她独自走在路中。; perform only 火把由远变亮，人物保持前景小体量。；重点是齐停，不追逐不冲撞。；陈青源主脸清楚，后方骑手保持剪影。; end on 陈青源问“可是镇魔司的大人当面”，火光照到姜月初脸上。; preserve required_presence=CHAR_01、CHAR_04、GROUP_飞鹰门马队、MOUNT_GROUP_01 飞鹰门马匹与火把、PROP_镇魔司黑衣赤纹、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
director intent: 第2集尾钩兑现：官道火把和十几骑飞鹰门马队逼近，陈青源把她误认成镇魔司大人。; audience effect: 观众看到追兵疑云变成误会反转，期待她怎么应对。.
character motion: 火把由远变亮，人物保持前景小体量。；重点是齐停，不追逐不冲撞。；陈青源主脸清楚，后方骑手保持剪影。; camera motion: 缓慢跟拍或微推，保持官道轴线; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
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
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_05.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 06（时长 20.955s · EP03_CLIP06 · 少说话的冷面官威）

**首帧**：`出图/第3集/图片/Clip06_first.png`
**尾帧**：`出图/第3集/图片/Clip06_end.png`
**锚帧1**：`出图/第3集/图片/Clip06_first_a1.png`（at_sec=5.24）
**锚帧2**：`出图/第3集/图片/Clip06_first_a2.png`（at_sec=10.48）
**锚帧3**：`出图/第3集/图片/Clip06_first_a3.png`（at_sec=15.72）
**场景**：LOC_02 荒野官道夜路/火把近景/外
**剧本可看性合同**：dramatic_function=她内心慌乱，却靠惜字如金误打误撞坐实镇魔司冷面官威。；audience_effect=观众获得反差爽点：越怕露馅，外人越觉得她像大人。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：她内心慌乱，却靠惜字如金误打误撞坐实镇魔司冷面官威。
**起幅**：陈青源问“可是镇魔司的大人当面”，火光照到姜月初脸上。
**落幅**：众人还站在马队后方，陈青源跨前一步报出飞鹰门门主身份。
**场面调度**：CU 姜月初反应 → OTS 陈青源 → CU 姜月初；角色=CHAR_01、CHAR_04、GROUP_飞鹰门马队；资产=LOC_02, PROP_镇魔司黑衣赤纹；轴线/视线=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 外表冷，眼神有一瞬僵住。；反打保持视线方向，不越轴。；嘴部动作很小，视频阶段不做口型驱动。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=姜月初内心慌乱、陈青源等待回答、她少说“何事”、陈青源更恭敬；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**专项镜头模板**：template=dialogue_shot_reverse；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=3；consumption_mode=native_multiframe；native_timeline_frames=5；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_04；binding=character_id_or_reference_group、binding=character_id_or_reference_group；assets=LOC_02、LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=3；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_04/常态：reference_group=ready；锚点句=陈青源·虬髯中年门主·深灰黑江湖劲装·火把侧照急迫恭敬·跪地求救。；GROUP_飞鹰门马队：registry form 未在 adapter matrix 摘要中命中，使用首帧+reference_group 兜底。；本镜绑定=CHAR_01、CHAR_04、GROUP_飞鹰门马队；资产引用注册层=LOC_02, PROP_镇魔司黑衣赤纹。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：陈青源问“可是镇魔司的大人当面”，火光照到姜月初脸上。
- 出点：众人还站在马队后方，陈青源跨前一步报出飞鹰门门主身份。
- 转场：dialogue_cut
- 连贯性：required_presence=CHAR_01、CHAR_04、GROUP_飞鹰门马队、PROP_镇魔司黑衣赤纹、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。

**continuity**：
- start_state：陈青源问“可是镇魔司的大人当面”，火光照到姜月初脸上。
- action：外表冷，眼神有一瞬僵住。；反打保持视线方向，不越轴。；嘴部动作很小，视频阶段不做口型驱动。
- end_state：众人还站在马队后方，陈青源跨前一步报出飞鹰门门主身份。
- constraints：required_presence=CHAR_01、CHAR_04、GROUP_飞鹰门马队、PROP_镇魔司黑衣赤纹、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 陈青源问“可是镇魔司的大人当面”，火光照到姜月初脸上。
  action: 外表冷，眼神有一瞬僵住。；反打保持视线方向，不越轴。；嘴部动作很小，视频阶段不做口型驱动。
  end_state: 众人还站在马队后方，陈青源跨前一步报出飞鹰门门主身份。
  constraints: required_presence=CHAR_01、CHAR_04、GROUP_飞鹰门马队、PROP_镇魔司黑衣赤纹、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。
剧本可看性合同：dramatic_function=她内心慌乱，却靠惜字如金误打误撞坐实镇魔司冷面官威。; audience_effect=观众获得反差爽点：越怕露馅，外人越觉得她像大人。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：她内心慌乱，却靠惜字如金误打误撞坐实镇魔司冷面官威。;
起幅：陈青源问“可是镇魔司的大人当面”，火光照到姜月初脸上。;
落幅：众人还站在马队后方，陈青源跨前一步报出飞鹰门门主身份。;
场面调度：CU 姜月初反应 → OTS 陈青源 → CU 姜月初；角色槽位=CHAR_01、CHAR_04、GROUP_飞鹰门马队；资产ID=LOC_02, PROP_镇魔司黑衣赤纹；
表演节拍：[0-30%] 承接首帧；[30-75%] 外表冷，眼神有一瞬僵住。；反打保持视线方向，不越轴。；嘴部动作很小，视频阶段不做口型驱动。；[75-100%] 众人还站在马队后方，陈青源跨前一步报出飞鹰门门主身份。;
运动精修约束：幅度=小到中；人物槽位不漂移；能量=克制；表情和视线先动，身体后动；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=姜月初内心慌乱、陈青源等待回答、她少说“何事”、陈青源更恭敬；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
专项模板约束：template=dialogue_shot_reverse；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=image2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
物理交互约束：读取 motion_control_manifest.json；level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_04/常态：reference_group=ready；锚点句=陈青源·虬髯中年门主·深灰黑江湖劲装·火把侧照急迫恭敬·跪地求救。；GROUP_飞鹰门马队：registry form 未在 adapter matrix 摘要中命中，使用首帧+reference_group 兜底。；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=中；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：外表冷，眼神有一瞬僵住。；反打保持视线方向，不越轴。；嘴部动作很小，视频阶段不做口型驱动。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或缓慢推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务误认爽点；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按dialogue_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 陈青源问“可是镇魔司的大人当面”，火光照到姜月初脸上。; perform only 外表冷，眼神有一瞬僵住。；反打保持视线方向，不越轴。；嘴部动作很小，视频阶段不做口型驱动。; end on 众人还站在马队后方，陈青源跨前一步报出飞鹰门门主身份。; preserve required_presence=CHAR_01、CHAR_04、GROUP_飞鹰门马队、PROP_镇魔司黑衣赤纹、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
director intent: 她内心慌乱，却靠惜字如金误打误撞坐实镇魔司冷面官威。; audience effect: 观众获得反差爽点：越怕露馅，外人越觉得她像大人。.
character motion: 外表冷，眼神有一瞬僵住。；反打保持视线方向，不越轴。；嘴部动作很小，视频阶段不做口型驱动。; camera motion: 固定或缓慢推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
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
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_06.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 07（时长 13.998s · EP03_CLIP07 · 陈青源跪求出手）

**首帧**：`出图/第3集/图片/Clip07_first.png`
**尾帧**：`出图/第3集/图片/Clip07_end.png`
**锚帧1**：`出图/第3集/图片/Clip07_first_a1.png`（at_sec=4.6）
**锚帧2**：`出图/第3集/图片/Clip07_first_a2.png`（at_sec=9.2）
**场景**：LOC_02 荒野官道夜路/火把跪地/外
**剧本可看性合同**：dramatic_function=陈青源报出飞鹰门与上盘村危机，单膝跪地带动众人跪求，假身份第一次变成真实责任。；audience_effect=观众意识到这不是白捡权威，所有人把命压给了她。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：陈青源报出飞鹰门与上盘村危机，单膝跪地带动众人跪求，假身份第一次变成真实责任。
**起幅**：众人还站在马队后方，陈青源跨前一步报出飞鹰门门主身份。
**落幅**：“恳请大人出手”的余音未散，陈青源抬头说明狼妖与上盘村惨状。
**场面调度**：MCU 陈青源 → LS 群体跪地 → CU 姜月初；角色=CHAR_01、CHAR_04、GROUP_飞鹰门马队；资产=LOC_02, MOUNT_GROUP_01 飞鹰门马匹与火把；轴线/视线=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 陈青源主脸稳定，虬髯、风尘、火光急迫。；群体不清脸，动作层级清楚。；姜月初站立高位，底部留字幕区。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；只执行本镜主动作链
- 能量：克制匀速
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=陈青源自报身份、单膝跪地、众人齐跪、姜月初被架到高位；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways.
**专项镜头模板**：template=ensemble_blocking；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=ensemble_blocking; primary_backend=seedance; fallback=dreamina; mode=frames2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=2；consumption_mode=native_multiframe；native_timeline_frames=4；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_04；binding=character_id_or_reference_group、binding=character_id_or_reference_group；assets=LOC_02、LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；identity_preservation_plan=required_identity_anchors=face_shape、hairstyle、age_read、outfit_palette、named_character_screen_slot；reference_strategy=character_id_or_reference_group；motion_readability_allowances=prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups、allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot、keep first/end frame and registered reference group as identity truth when motion control needs simpler movement；fallback_plan=If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.；applies_to=ensemble_blocking；control_inputs=manifest_path=出视频/第3集/control/Clip_07/motion_control_manifest.json；required=True；required_inputs=pose_sequence、depth_sequence、instance_masks；gate_policy=block_without_ready_manifest_or_degrade_only_manifest；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=2；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第3集/control/Clip_07/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；degrade_plan=Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_04/常态：reference_group=ready；锚点句=陈青源·虬髯中年门主·深灰黑江湖劲装·火把侧照急迫恭敬·跪地求救。；GROUP_飞鹰门马队：registry form 未在 adapter matrix 摘要中命中，使用首帧+reference_group 兜底。；本镜绑定=CHAR_01、CHAR_04、GROUP_飞鹰门马队；资产引用注册层=LOC_02, MOUNT_GROUP_01 飞鹰门马匹与火把。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=中；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：众人还站在马队后方，陈青源跨前一步报出飞鹰门门主身份。
- 出点：“恳请大人出手”的余音未散，陈青源抬头说明狼妖与上盘村惨状。
- 转场：l_cut
- 连贯性：required_presence=CHAR_01、CHAR_04、GROUP_飞鹰门马队、MOUNT_GROUP_01 飞鹰门马匹与火把、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。

**continuity**：
- start_state：众人还站在马队后方，陈青源跨前一步报出飞鹰门门主身份。
- action：陈青源主脸稳定，虬髯、风尘、火光急迫。；群体不清脸，动作层级清楚。；姜月初站立高位，底部留字幕区。
- end_state：“恳请大人出手”的余音未散，陈青源抬头说明狼妖与上盘村惨状。
- constraints：required_presence=CHAR_01、CHAR_04、GROUP_飞鹰门马队、MOUNT_GROUP_01 飞鹰门马匹与火把、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 众人还站在马队后方，陈青源跨前一步报出飞鹰门门主身份。
  action: 陈青源主脸稳定，虬髯、风尘、火光急迫。；群体不清脸，动作层级清楚。；姜月初站立高位，底部留字幕区。
  end_state: “恳请大人出手”的余音未散，陈青源抬头说明狼妖与上盘村惨状。
  constraints: required_presence=CHAR_01、CHAR_04、GROUP_飞鹰门马队、MOUNT_GROUP_01 飞鹰门马匹与火把、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。
剧本可看性合同：dramatic_function=陈青源报出飞鹰门与上盘村危机，单膝跪地带动众人跪求，假身份第一次变成真实责任。; audience_effect=观众意识到这不是白捡权威，所有人把命压给了她。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：陈青源报出飞鹰门与上盘村危机，单膝跪地带动众人跪求，假身份第一次变成真实责任。;
起幅：众人还站在马队后方，陈青源跨前一步报出飞鹰门门主身份。;
落幅：“恳请大人出手”的余音未散，陈青源抬头说明狼妖与上盘村惨状。;
场面调度：MCU 陈青源 → LS 群体跪地 → CU 姜月初；角色槽位=CHAR_01、CHAR_04、GROUP_飞鹰门马队；资产ID=LOC_02, MOUNT_GROUP_01 飞鹰门马匹与火把；
表演节拍：[0-30%] 承接首帧；[30-75%] 陈青源主脸稳定，虬髯、风尘、火光急迫。；群体不清脸，动作层级清楚。；姜月初站立高位，底部留字幕区。；[75-100%] “恳请大人出手”的余音未散，陈青源抬头说明狼妖与上盘村惨状。;
运动精修约束：幅度=小幅；只执行本镜主动作链；能量=克制匀速；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=陈青源自报身份、单膝跪地、众人齐跪、姜月初被架到高位；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways.；
专项模板约束：template=ensemble_blocking；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=frames2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways.；
物理交互约束：读取 motion_control_manifest.json；level=required；manifest_path=出视频/第3集/control/Clip_07/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=slot_drift,pose_drift,identity_drift；degrade_plan=Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_04/常态：reference_group=ready；锚点句=陈青源·虬髯中年门主·深灰黑江湖劲装·火把侧照急迫恭敬·跪地求救。；GROUP_飞鹰门马队：registry form 未在 adapter matrix 摘要中命中，使用首帧+reference_group 兜底。；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=中；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：陈青源主脸稳定，虬髯、风尘、火光急迫。；群体不清脸，动作层级清楚。；姜月初站立高位，底部留字幕区。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或极缓推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务责任反噬；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按l_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 众人还站在马队后方，陈青源跨前一步报出飞鹰门门主身份。; perform only 陈青源主脸稳定，虬髯、风尘、火光急迫。；群体不清脸，动作层级清楚。；姜月初站立高位，底部留字幕区。; end on “恳请大人出手”的余音未散，陈青源抬头说明狼妖与上盘村惨状。; preserve required_presence=CHAR_01、CHAR_04、GROUP_飞鹰门马队、MOUNT_GROUP_01 飞鹰门马匹与火把、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
director intent: 陈青源报出飞鹰门与上盘村危机，单膝跪地带动众人跪求，假身份第一次变成真实责任。; audience effect: 观众意识到这不是白捡权威，所有人把命压给了她。.
character motion: 陈青源主脸稳定，虬髯、风尘、火光急迫。；群体不清脸，动作层级清楚。；姜月初站立高位，底部留字幕区。; camera motion: 固定或极缓推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
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
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_07.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 08（时长 34.492s · EP03_CLIP08 · 上盘村狼妖危机）

**首帧**：`出图/第3集/图片/Clip08_first.png`
**尾帧**：`出图/第3集/图片/Clip08_end.png`
**锚帧1**：`出图/第3集/图片/Clip08_first_a1.png`（at_sec=3.41）
**锚帧2**：`出图/第3集/图片/Clip08_first_a2.png`（at_sec=6.82）
**锚帧3**：`出图/第3集/图片/Clip08_first_a3.png`（at_sec=10.23）
**锚帧4**：`出图/第3集/图片/Clip08_first_a4.png`（at_sec=13.64）
**锚帧5**：`出图/第3集/图片/Clip08_first_a5.png`（at_sec=17.05）
**锚帧6**：`出图/第3集/图片/Clip08_first_a6.png`（at_sec=20.46）
**锚帧7**：`出图/第3集/图片/Clip08_first_a7.png`（at_sec=23.86）
**锚帧8**：`出图/第3集/图片/Clip08_first_a8.png`（at_sec=27.27）
**锚帧9**：`出图/第3集/图片/Clip08_first_a9.png`（at_sec=30.68）
**场景**：LOC_02 荒野官道夜路/火把与夜风/外
**剧本可看性合同**：dramatic_function=陈青源把飞鹰门折损、亲族被困、狼妖每日拖人说清，把救与不救的代价压实。；audience_effect=观众从误会爽点转入道德悬念：她能不能真扛这个身份。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：陈青源把飞鹰门折损、亲族被困、狼妖每日拖人说清，把救与不救的代价压实。
**起幅**：“恳请大人出手”的余音未散，陈青源抬头说明狼妖与上盘村惨状。
**落幅**：狼妖危机说尽后，姜月初在火光里沉默，黑衣赤纹压在肩上。
**场面调度**：CU 姜月初 → MCU 陈青源 → INSERT 火把/祠堂阴影想象；角色=CHAR_01、CHAR_04；资产=LOC_02, MOUNT_GROUP_01 飞鹰门马匹与火把；轴线/视线=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 眼神压住荒诞和烦躁。；台词由后期配音，画面重在急迫表情。；想象画面克制，避免新增未定妆妖怪资产。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=姜月初内心吐槽、陈青源交代折损、狼妖围祠堂信息压实、上盘村将成坟；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**专项镜头模板**：template=dialogue_shot_reverse；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=9；consumption_mode=native_multiframe；native_timeline_frames=11；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_04；binding=character_id_or_reference_group；assets=LOC_02、LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=9；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_04/常态：reference_group=ready；锚点句=陈青源·虬髯中年门主·深灰黑江湖劲装·火把侧照急迫恭敬·跪地求救。；本镜绑定=CHAR_01、CHAR_04；资产引用注册层=LOC_02, MOUNT_GROUP_01 飞鹰门马匹与火把。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：“恳请大人出手”的余音未散，陈青源抬头说明狼妖与上盘村惨状。
- 出点：狼妖危机说尽后，姜月初在火光里沉默，黑衣赤纹压在肩上。
- 转场：reaction_cut
- 连贯性：required_presence=CHAR_01、CHAR_04、MOUNT_GROUP_01 飞鹰门马匹与火把、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。

**continuity**：
- start_state：“恳请大人出手”的余音未散，陈青源抬头说明狼妖与上盘村惨状。
- action：眼神压住荒诞和烦躁。；台词由后期配音，画面重在急迫表情。；想象画面克制，避免新增未定妆妖怪资产。
- end_state：狼妖危机说尽后，姜月初在火光里沉默，黑衣赤纹压在肩上。
- constraints：required_presence=CHAR_01、CHAR_04、MOUNT_GROUP_01 飞鹰门马匹与火把、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: “恳请大人出手”的余音未散，陈青源抬头说明狼妖与上盘村惨状。
  action: 眼神压住荒诞和烦躁。；台词由后期配音，画面重在急迫表情。；想象画面克制，避免新增未定妆妖怪资产。
  end_state: 狼妖危机说尽后，姜月初在火光里沉默，黑衣赤纹压在肩上。
  constraints: required_presence=CHAR_01、CHAR_04、MOUNT_GROUP_01 飞鹰门马匹与火把、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。
剧本可看性合同：dramatic_function=陈青源把飞鹰门折损、亲族被困、狼妖每日拖人说清，把救与不救的代价压实。; audience_effect=观众从误会爽点转入道德悬念：她能不能真扛这个身份。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：陈青源把飞鹰门折损、亲族被困、狼妖每日拖人说清，把救与不救的代价压实。;
起幅：“恳请大人出手”的余音未散，陈青源抬头说明狼妖与上盘村惨状。;
落幅：狼妖危机说尽后，姜月初在火光里沉默，黑衣赤纹压在肩上。;
场面调度：CU 姜月初 → MCU 陈青源 → INSERT 火把/祠堂阴影想象；角色槽位=CHAR_01、CHAR_04；资产ID=LOC_02, MOUNT_GROUP_01 飞鹰门马匹与火把；
表演节拍：[0-30%] 承接首帧；[30-75%] 眼神压住荒诞和烦躁。；台词由后期配音，画面重在急迫表情。；想象画面克制，避免新增未定妆妖怪资产。；[75-100%] 狼妖危机说尽后，姜月初在火光里沉默，黑衣赤纹压在肩上。;
运动精修约束：幅度=小到中；人物槽位不漂移；能量=克制；表情和视线先动，身体后动；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=姜月初内心吐槽、陈青源交代折损、狼妖围祠堂信息压实、上盘村将成坟；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
专项模板约束：template=dialogue_shot_reverse；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=image2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
物理交互约束：读取 motion_control_manifest.json；level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_04/常态：reference_group=ready；锚点句=陈青源·虬髯中年门主·深灰黑江湖劲装·火把侧照急迫恭敬·跪地求救。；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=大；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：眼神压住荒诞和烦躁。；台词由后期配音，画面重在急迫表情。；想象画面克制，避免新增未定妆妖怪资产。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或缓慢推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务危机加码；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按reaction_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from “恳请大人出手”的余音未散，陈青源抬头说明狼妖与上盘村惨状。; perform only 眼神压住荒诞和烦躁。；台词由后期配音，画面重在急迫表情。；想象画面克制，避免新增未定妆妖怪资产。; end on 狼妖危机说尽后，姜月初在火光里沉默，黑衣赤纹压在肩上。; preserve required_presence=CHAR_01、CHAR_04、MOUNT_GROUP_01 飞鹰门马匹与火把、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
director intent: 陈青源把飞鹰门折损、亲族被困、狼妖每日拖人说清，把救与不救的代价压实。; audience effect: 观众从误会爽点转入道德悬念：她能不能真扛这个身份。.
character motion: 眼神压住荒诞和烦躁。；台词由后期配音，画面重在急迫表情。；想象画面克制，避免新增未定妆妖怪资产。; camera motion: 固定或缓慢推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
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
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_08.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 09（时长 16.842s · EP03_CLIP09 · 黑衣绑身：拒绝最安全）

**首帧**：`出图/第3集/图片/Clip09_first.png`
**尾帧**：`出图/第3集/图片/Clip09_end.png`
**锚帧1**：`出图/第3集/图片/Clip09_first_a1.png`（at_sec=3.37）
**锚帧2**：`出图/第3集/图片/Clip09_first_a2.png`（at_sec=6.74）
**锚帧3**：`出图/第3集/图片/Clip09_first_a3.png`（at_sec=10.11）
**锚帧4**：`出图/第3集/图片/Clip09_first_a4.png`（at_sec=13.47）
**场景**：LOC_02 荒野官道夜路/火把摇晃/外
**剧本可看性合同**：dramatic_function=她清楚拒绝最安全，答应最像镇魔司；这身黑衣从护身符变成枷锁。；audience_effect=观众看到主角的自私求生和救人责任正面冲突。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：她清楚拒绝最安全，答应最像镇魔司；这身黑衣从护身符变成枷锁。
**起幅**：狼妖危机说尽后，姜月初在火光里沉默，黑衣赤纹压在肩上。
**落幅**：夜风吹过，火把摇晃。陈青源抬头看着她，像看着最后一道救命符。
**场面调度**：CU 姜月初沉默 → ECU 黑衣/脸；角色=CHAR_01、CHAR_04；资产=LOC_02, PROP_镇魔司黑衣赤纹, WEAPON_01 横刀；轴线/视线=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 眼神在火光里左右微动，身体不动。；脸和衣纹同框，情绪峰值落在“活下去”。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小幅；只执行本镜主动作链
- 能量：克制匀速
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=拒绝最安全、答应最像镇魔司、黑衣成为枷锁、她说只想活下去；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to single-face CU, hand insert, or OTS if the two-shot overplays contact or expression.
**专项镜头模板**：template=relationship_turn；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=relationship_turn; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=Switch to single-face CU, hand insert, or OTS if the two-shot overplays contact or expression.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=4；consumption_mode=native_multiframe；native_timeline_frames=6；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_04；binding=character_id_or_reference_group；assets=LOC_02、LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=Switch to single-face CU, hand insert, or OTS if the two-shot overplays contact or expression.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=4；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to single-face CU, hand insert, or OTS if the two-shot overplays contact or expression.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_04/常态：reference_group=ready；锚点句=陈青源·虬髯中年门主·深灰黑江湖劲装·火把侧照急迫恭敬·跪地求救。；本镜绑定=CHAR_01、CHAR_04；资产引用注册层=LOC_02, PROP_镇魔司黑衣赤纹, WEAPON_01 横刀。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：狼妖危机说尽后，姜月初在火光里沉默，黑衣赤纹压在肩上。
- 出点：夜风吹过，火把摇晃。陈青源抬头看着她，像看着最后一道救命符。
- 转场：eyeline_cut
- 连贯性：required_presence=CHAR_01、CHAR_04、PROP_镇魔司黑衣赤纹、WEAPON_01 横刀、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。

**continuity**：
- start_state：狼妖危机说尽后，姜月初在火光里沉默，黑衣赤纹压在肩上。
- action：眼神在火光里左右微动，身体不动。；脸和衣纹同框，情绪峰值落在“活下去”。
- end_state：夜风吹过，火把摇晃。陈青源抬头看着她，像看着最后一道救命符。
- constraints：required_presence=CHAR_01、CHAR_04、PROP_镇魔司黑衣赤纹、WEAPON_01 横刀、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 狼妖危机说尽后，姜月初在火光里沉默，黑衣赤纹压在肩上。
  action: 眼神在火光里左右微动，身体不动。；脸和衣纹同框，情绪峰值落在“活下去”。
  end_state: 夜风吹过，火把摇晃。陈青源抬头看着她，像看着最后一道救命符。
  constraints: required_presence=CHAR_01、CHAR_04、PROP_镇魔司黑衣赤纹、WEAPON_01 横刀、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。
剧本可看性合同：dramatic_function=她清楚拒绝最安全，答应最像镇魔司；这身黑衣从护身符变成枷锁。; audience_effect=观众看到主角的自私求生和救人责任正面冲突。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：她清楚拒绝最安全，答应最像镇魔司；这身黑衣从护身符变成枷锁。;
起幅：狼妖危机说尽后，姜月初在火光里沉默，黑衣赤纹压在肩上。;
落幅：夜风吹过，火把摇晃。陈青源抬头看着她，像看着最后一道救命符。;
场面调度：CU 姜月初沉默 → ECU 黑衣/脸；角色槽位=CHAR_01、CHAR_04；资产ID=LOC_02, PROP_镇魔司黑衣赤纹, WEAPON_01 横刀；
表演节拍：[0-30%] 承接首帧；[30-75%] 眼神在火光里左右微动，身体不动。；脸和衣纹同框，情绪峰值落在“活下去”。；[75-100%] 夜风吹过，火把摇晃。陈青源抬头看着她，像看着最后一道救命符。;
运动精修约束：幅度=小幅；只执行本镜主动作链；能量=克制匀速；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=拒绝最安全、答应最像镇魔司、黑衣成为枷锁、她说只想活下去；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to single-face CU, hand insert, or OTS if the two-shot overplays contact or expression.；
专项模板约束：template=relationship_turn；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=image2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=Switch to single-face CU, hand insert, or OTS if the two-shot overplays contact or expression.；
物理交互约束：读取 motion_control_manifest.json；level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to single-face CU, hand insert, or OTS if the two-shot overplays contact or expression.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_04/常态：reference_group=ready；锚点句=陈青源·虬髯中年门主·深灰黑江湖劲装·火把侧照急迫恭敬·跪地求救。；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=大；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：眼神在火光里左右微动，身体不动。；脸和衣纹同框，情绪峰值落在“活下去”。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或极缓推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务选择困局；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按eyeline_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 狼妖危机说尽后，姜月初在火光里沉默，黑衣赤纹压在肩上。; perform only 眼神在火光里左右微动，身体不动。；脸和衣纹同框，情绪峰值落在“活下去”。; end on 夜风吹过，火把摇晃。陈青源抬头看着她，像看着最后一道救命符。; preserve required_presence=CHAR_01、CHAR_04、PROP_镇魔司黑衣赤纹、WEAPON_01 横刀、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
director intent: 她清楚拒绝最安全，答应最像镇魔司；这身黑衣从护身符变成枷锁。; audience effect: 观众看到主角的自私求生和救人责任正面冲突。.
character motion: 眼神在火光里左右微动，身体不动。；脸和衣纹同框，情绪峰值落在“活下去”。; camera motion: 固定或极缓推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
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
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_09.mp4`；失败进废料并改 prompt/拆 Clip。

## Clip 10（时长 13.060s · EP03_CLIP10 · 唯一希望：集尾硬断）

**首帧**：`出图/第3集/图片/Clip10_first.png`
**尾帧**：`出图/第3集/图片/Clip10_end.png`
**锚帧1**：`出图/第3集/图片/Clip10_first_a1.png`（at_sec=3.21）
**锚帧2**：`出图/第3集/图片/Clip10_first_a2.png`（at_sec=6.43）
**锚帧3**：`出图/第3集/图片/Clip10_first_a3.png`（at_sec=9.64）
**场景**：LOC_02 荒野官道夜路/火把尾钩/外
**剧本可看性合同**：dramatic_function=陈青源把她当作最后一道救命符，她成了上盘村唯一希望，硬断到下一集。；audience_effect=观众带着“她到底救不救”进入下一集。；retention promise / audience question 必须由运动和表演承接，不改写承诺。
**导演意图**：陈青源把她当作最后一道救命符，她成了上盘村唯一希望，硬断到下一集。
**起幅**：夜风吹过，火把摇晃。陈青源抬头看着她，像看着最后一道救命符。
**落幅**：姜月初没有立刻答应，也没有拒绝；火把在她眼里摇成一条细亮的线，尾帧定住半拍后硬切黑。
**场面调度**：MCU 陈青源抬头 → CU 姜月初 → ECU 火把/眼神硬断；角色=CHAR_01、CHAR_04；资产=LOC_02, MOUNT_GROUP_01 飞鹰门马匹与火把；轴线/视线=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] 火把在他身后摇晃，脸部稳定。；沉默比台词更重。；末镜不需要尾帧，停止在悬念。；[75-100%] 停到落幅，给下一镜接点。
**运动精修**：物理层锁定；动作只服务本镜导演意图。
- 幅度：小到中；人物槽位不漂移
- 能量：克制；表情和视线先动，身体后动
- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。
**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。
**动作编排契约 / Action Choreography**：beats=夜风吹过火把、陈青源抬头求救、姜月初成为唯一希望、硬切黑；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**专项镜头模板**：template=dialogue_shot_reverse；blocking/continuity_must/negative 继承 storyboard，不临场改戏。
**模型路由**：shot_type=dialogue_shot_reverse; primary_backend=seedance; fallback=dreamina; mode=image2video; native_audio_policy=none; identity_requirement=character_id_or_reference_group; degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**执行配方 / Execution Recipe**：frame_inputs=first_frame=True；last_frame=True；mid_anchors=3；consumption_mode=native_multiframe；native_timeline_frames=5；reference_inputs=characters=character_id=CHAR_01；binding=character_id_or_reference_group、character_id=CHAR_04；binding=character_id_or_reference_group；assets=LOC_02、LOC_01；motion_reference=library_path=生产数据/motion_reference_library.json；policy=not_supported_or_not_needed；control_inputs=gate_policy=not_required；audio_inputs=video_generation_audio_policy=无声视频流；native_audio_policy=none；speech_policy=no_native_speech；fallback=fallback_backends=dreamina；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；anchor_consumption=backend=seedance；execution_backend=dreamina；frame_control_mode=multi_keyframe；anchor_count=3；need_end=True；consumption_mode=native_multiframe；consumes_mid_anchors_natively=True；consumes_endframe=True；known_profile=True；supports_native_mid_anchors=True；supports_last_frame=True；auto_routable=True；action=submit first/mid/end frames in one native multi-keyframe request
**Motion Control / 物理交互控制**：level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.
**角色身份注册层**：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_04/常态：reference_group=ready；锚点句=陈青源·虬髯中年门主·深灰黑江湖劲装·火把侧照急迫恭敬·跪地求救。；本镜绑定=CHAR_01、CHAR_04；资产引用注册层=LOC_02, MOUNT_GROUP_01 飞鹰门马匹与火把。
**近景/反打身份锁定**：主焦点=CHAR_01；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度=大；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。
**衔接设计**：
- 入点：夜风吹过，火把摇晃。陈青源抬头看着她，像看着最后一道救命符。
- 出点：姜月初没有立刻答应，也没有拒绝；火把在她眼里摇成一条细亮的线，尾帧定住半拍后硬切黑。
- 转场：cliffhanger_cut
- 连贯性：required_presence=CHAR_01、CHAR_04、MOUNT_GROUP_01 飞鹰门马匹与火把、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。

**continuity**：
- start_state：夜风吹过，火把摇晃。陈青源抬头看着她，像看着最后一道救命符。
- action：火把在他身后摇晃，脸部稳定。；沉默比台词更重。；末镜不需要尾帧，停止在悬念。
- end_state：姜月初没有立刻答应，也没有拒绝；火把在她眼里摇成一条细亮的线，尾帧定住半拍后硬切黑。
- constraints：required_presence=CHAR_01、CHAR_04、MOUNT_GROUP_01 飞鹰门马匹与火把、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。

**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```
continuity:
  start_state: 夜风吹过，火把摇晃。陈青源抬头看着她，像看着最后一道救命符。
  action: 火把在他身后摇晃，脸部稳定。；沉默比台词更重。；末镜不需要尾帧，停止在悬念。
  end_state: 姜月初没有立刻答应，也没有拒绝；火把在她眼里摇成一条细亮的线，尾帧定住半拍后硬切黑。
  constraints: required_presence=CHAR_01、CHAR_04、MOUNT_GROUP_01 飞鹰门马匹与火把、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。
剧本可看性合同：dramatic_function=陈青源把她当作最后一道救命符，她成了上盘村唯一希望，硬断到下一集。; audience_effect=观众带着“她到底救不救”进入下一集。; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；
导演意图：陈青源把她当作最后一道救命符，她成了上盘村唯一希望，硬断到下一集。;
起幅：夜风吹过，火把摇晃。陈青源抬头看着她，像看着最后一道救命符。;
落幅：姜月初没有立刻答应，也没有拒绝；火把在她眼里摇成一条细亮的线，尾帧定住半拍后硬切黑。;
场面调度：MCU 陈青源抬头 → CU 姜月初 → ECU 火把/眼神硬断；角色槽位=CHAR_01、CHAR_04；资产ID=LOC_02, MOUNT_GROUP_01 飞鹰门马匹与火把；
表演节拍：[0-30%] 承接首帧；[30-75%] 火把在他身后摇晃，脸部稳定。；沉默比台词更重。；末镜不需要尾帧，停止在悬念。；[75-100%] 姜月初没有立刻答应，也没有拒绝；火把在她眼里摇成一条细亮的线，尾帧定住半拍后硬切黑。;
运动精修约束：幅度=小到中；人物槽位不漂移；能量=克制；表情和视线先动，身体后动；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；
环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；
动作编排约束：beats=夜风吹过火把、陈青源抬头求救、姜月初成为唯一希望、硬切黑；speed_curve=慢→稳→定；spatial_path=沿既定轴线，不重置距离；camera_path=固定/微推，服务可读性；readability_beats=起势/动作/落点都可读；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
专项模板约束：template=dialogue_shot_reverse；按 storyboard template_contract 执行；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=seedance，fallback=dreamina，mode=image2video，native_audio_policy=none，identity_requirement=character_id_or_reference_group；失败按 degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；
物理交互约束：读取 motion_control_manifest.json；level=none；manifest_path=无；required_inputs=；failure_modes=；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；
身份锁定约束：CHAR_01/囚犯初醒态：reference_group=ready；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_04/常态：reference_group=ready；锚点句=陈青源·虬髯中年门主·深灰黑江湖劲装·火把侧照急迫恭敬·跪地求救。；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；
近景身份锁定约束：表情锚起→止，表情幅度=大；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；
原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；
人物运动：火把在他身后摇晃，脸部稳定。；沉默比台词更重。；末镜不需要尾帧，停止在悬念。；表情只动面部肌肉，脸型五官比例不变；
镜头运动：固定或缓慢推近；
情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务集尾钩子；
动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按cliffhanger_cut服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；
声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```
continuity: start from 夜风吹过，火把摇晃。陈青源抬头看着她，像看着最后一道救命符。; perform only 火把在他身后摇晃，脸部稳定。；沉默比台词更重。；末镜不需要尾帧，停止在悬念。; end on 姜月初没有立刻答应，也没有拒绝；火把在她眼里摇成一条细亮的线，尾帧定住半拍后硬切黑。; preserve required_presence=CHAR_01、CHAR_04、MOUNT_GROUP_01 飞鹰门马匹与火把、LOC_02; offscreen_presence=无; forbidden_presence=modern vehicles、phones、random readable text、watermark; eyeline=姜月初视线按 LOC_01/LOC_02 轴线锁定裴长青遗体、横刀、陈青源或官道深处；非 POV 镜不看镜头。; avoid face drift, costume changes, new characters, text, logos, watermarks, and generated native voice.
director intent: 陈青源把她当作最后一道救命符，她成了上盘村唯一希望，硬断到下一集。; audience effect: 观众带着“她到底救不救”进入下一集。.
character motion: 火把在他身后摇晃，脸部稳定。；沉默比台词更重。；末镜不需要尾帧，停止在悬念。; camera motion: 固定或缓慢推近; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.
close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.
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
- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。
- [ ] 落档判定：通过落 `出视频/第3集/视频/Clip_10.mp4`；失败进废料并改 prompt/拆 Clip。
