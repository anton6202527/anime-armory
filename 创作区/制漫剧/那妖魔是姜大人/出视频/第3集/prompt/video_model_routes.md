# 视频模型路由

- episode: 第3集
- routing_mode: auto
- production_mode: 先出视频后配音 (av_mode=voice_first)
- default_backend: dreamina
- generated_at: 2026-07-06T02:29:03+00:00

## 本集模型路由表

| Clip | characters | shot_type | primary | fallback | mode | 档 | 帧消费 | native_audio | identity | motion_control | policy | 风险 | 降级 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Clip_01 | CHAR_01, CHAR_02 | multi_character_same_frame | seedance | dreamina | frames2video | high | native_multiframe | none | character_id_or_reference_group | required | motion_control_required | identity_drift_risk, mouth_visible, multi_person, native_multiframe, seam_relay | If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip. |
| Clip_02 | CHAR_01 | general_motion | dreamina | seedance | image2video | fast | native_multiframe | none | reference_group | none | spectacle_prior | frame_anchor_rerouted, native_multiframe, seam_relay, spectacle_prior_routed | If action or identity fails twice, reroute to the nearest specialized shot type. |
| Clip_03 | CHAR_01 | dialogue_shot_reverse | seedance | dreamina | image2video | high | native_multiframe | none | character_id_or_reference_group | none | frame_anchor_required | duration_segment_relay, native_multiframe, seam_relay | Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails. |
| Clip_04 | CHAR_01 | empty_establishing | dreamina | seedance | image2video | fast | native_multiframe | none | reference_group | none | frame_anchor_required | duration_segment_relay, low_identity_risk, multishot_reroute_candidate, native_multiframe, seam_relay | Use Dreamina/Seedance silent clip and add SFX/BGM in compose. |
| Clip_05 | CHAR_01, CHAR_04, GROUP_飞鹰门马队 | mount_ride | dreamina | seedance | image2video | high | native_multiframe | none | face_lock_or_reference_group | required | motion_control_required | action_choreography_required, duration_segment_relay, high_speed_motion, identity_drift_risk, multishot_reroute_candidate, native_multiframe, pose_drift_risk, seam_relay, spatial_path_risk | Cut to front/back reaction shots or split into approach, pass-by, and exit clips. |
| Clip_06 | CHAR_01, CHAR_04, GROUP_飞鹰门马队 | dialogue_shot_reverse | seedance | dreamina | image2video | high | native_multiframe | none | character_id_or_reference_group | none | frame_anchor_required | duration_segment_relay, mouth_visible, multi_person, native_multiframe, seam_relay | Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails. |
| Clip_07 | CHAR_01, CHAR_04, GROUP_飞鹰门马队 | ensemble_blocking | seedance | dreamina | frames2video | high | native_multiframe | none | character_id_or_reference_group | required | motion_control_required | identity_drift_risk, multi_person, native_multiframe, seam_relay | Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways. |
| Clip_08 | CHAR_01, CHAR_04 | dialogue_shot_reverse | seedance | dreamina | image2video | high | native_multiframe | none | character_id_or_reference_group | none | frame_anchor_required | duration_segment_relay, mouth_visible, native_multiframe, seam_relay | Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails. |
| Clip_09 | CHAR_01, CHAR_04 | relationship_turn | seedance | dreamina | image2video | high | native_multiframe | none | character_id_or_reference_group | none | frame_anchor_required | duration_segment_relay, identity_drift_risk, multi_person, native_multiframe, seam_relay | Switch to single-face CU, hand insert, or OTS if the two-shot overplays contact or expression. |
| Clip_10 | CHAR_01, CHAR_04 | dialogue_shot_reverse | seedance | dreamina | image2video | high | native_multiframe | none | character_id_or_reference_group | none | frame_anchor_required | mouth_visible, native_multiframe, seam_relay | Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails. |

## 逐 Clip 路由理由

### Clip_01 — multi_character_same_frame
- characters: CHAR_01, CHAR_02
- primary: seedance
- fallback: dreamina
- mode: frames2video
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=3, need_end=True)
- motion_control: required (manifest=出视频/第3集/control/Clip_01/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=3; refs_max=0; control_manifest=出视频/第3集/control/Clip_01/motion_control_manifest.json
- policy_resolution: winner=motion_control_required signoff_required=False
  - conflict backend_choice: cross_episode_baseline, cost_quality_tier -> cross_episode_baseline
- rationale:
  - multi-person staging needs reference controls and stable screen direction
  - single-backend generic generation often swaps faces or screen positions
  - 执行渠道「Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 10.88s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - freeze character slots, left/right positions, and face priority
  - keep two to three named faces maximum; lower-priority faces may be side/back/soft focus
  - bind each named registered character id to its own screen slot (LEFT/RIGHT/FOREGROUND/BACKGROUND) AND its own subject/reference anchor — regional/mask binding per subject; never feed one shared reference for the whole frame (single shared ref makes the model average faces)
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.

### Clip_02 — general_motion
- characters: CHAR_01
- primary: dreamina
- fallback: seedance
- mode: image2video
- quality_tier: fast
- identity: reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=spectacle_prior signoff_required=False
  - conflict backend_choice: spectacle_prior, cost_quality_tier -> spectacle_prior
- rationale:
  - general motion can use the project default backend for cost and speed
  - 接力镜：primary「dreamina」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=fast：通用/低身份风险镜走量产快档省成本（落档侧解析为后端 fast model_version）。
  - spectacle cold-start prior: large_establishing 默认排序首选 veo（large_establishing 吃运镜语言与尺度: Veo cinematography 强, Seedance 转场次之）；通用兜底 dreamina 改为 prior 首选，原后端保留为 fallback。跑 probe 后由 benchmark 覆盖。
  - frame_anchor_required: 本镜声明中段锚帧，veo 只能 split_relay；改用 dreamina 原生多关键帧以避免中锚被降级。
- prompt_requirements:
  - keep character/camera/dynamic detail three-part prompt explicit
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: If action or identity fails twice, reroute to the nearest specialized shot type.

### Clip_03 — dialogue_shot_reverse
- characters: CHAR_01
- primary: seedance
- fallback: dreamina
- mode: image2video
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=4, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=4; refs_max=0; control_manifest=-
- policy_resolution: winner=frame_anchor_required signoff_required=False
  - conflict backend_choice: cross_episode_baseline, cost_quality_tier -> cross_episode_baseline
- rationale:
  - dialogue shots are identity-sensitive and often need lip-sync or strong reference controls
  - default n2d audio remains voiceover-first; do not let the video backend generate speech
  - 执行渠道「Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 24.832s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜 24.832s 超过 seedance 单次上限 15s；执行侧必须按现有首/中/尾帧拆成 5 段 first_last_relay 付费提交，每段不超过上限，再在后续合成阶段接回。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - mark mouth_visible and speech_policy=no_native_speech
  - prefer side/back/OTS if lip-sync is disabled
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 长镜分段接力：不要单次提交整镜；按 duration_segment_relay.segments 用首帧→中段锚帧→尾帧分段生成。
- degrade_plan: Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.

### Clip_04 — empty_establishing
- characters: CHAR_01
- primary: dreamina
- fallback: seedance
- mode: image2video
- quality_tier: fast
- identity: reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=6, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=6; refs_max=0; control_manifest=-
- policy_resolution: winner=frame_anchor_required signoff_required=False
- rationale:
  - empty/ambience shots have low identity risk and can use native ambience when opted in
  - text2video is acceptable when no character identity must be preserved
  - 执行渠道「Dreamina」下改用可执行后端「dreamina」；原 primary「seedance」storyboard 帧/时长契约不匹配（duration 33.363s exceeds seedance max 15s），降为 fallback。
  - 接力镜：primary「dreamina」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜 33.363s 超过 dreamina 单次上限 15s；执行侧必须按现有首/中/尾帧拆成 7 段 first_last_relay 付费提交，每段不超过上限，再在后续合成阶段接回。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=fast：通用/低身份风险镜走量产快档省成本（落档侧解析为后端 fast model_version）。
- prompt_requirements:
  - confirm mouth_visible=no and speech_policy=no_native_speech
  - keep ambience sound low-risk; no voices, no narration, no humming
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 长镜分段接力：不要单次提交整镜；按 duration_segment_relay.segments 用首帧→中段锚帧→尾帧分段生成。
- degrade_plan: Use Dreamina/Seedance silent clip and add SFX/BGM in compose.

### Clip_05 — mount_ride
- characters: CHAR_01, CHAR_04, GROUP_飞鹰门马队
- primary: dreamina
- fallback: seedance
- mode: image2video
- quality_tier: high
- identity: face_lock_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=3, need_end=True)
- motion_control: required (manifest=出视频/第3集/control/Clip_05/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks, contact_map, camera_path, spatial_path, parallax_layers
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=3; refs_max=0; control_manifest=出视频/第3集/control/Clip_05/motion_control_manifest.json
- action_choreography: mount_establish_gait_turn_arrival (gate=block_prompt_without_action_choreography_contract)
- action_choreography_required_fields: beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, mount_contact, gait_cycle, screen_direction, parallax_layers, harness_lock
- policy_resolution: winner=motion_control_required signoff_required=False
- rationale:
  - long continuous motion and moving backgrounds benefit from longer single-shot generation
  - flight/chase/mount/vehicle/vessel/road/stealth shots should lock subject shape and put speed or suspense into background, parallax, gait, wheels, traffic, light, or occlusion layers
  - 执行渠道「Dreamina」下改用可执行后端「dreamina」；原 primary「seedance」storyboard 帧/时长契约不匹配（duration 23.557s exceeds seedance max 15s），降为 fallback。
  - 接力镜：primary「dreamina」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜 23.557s 超过 dreamina 单次上限 15s；执行侧必须按现有首/中/尾帧拆成 4 段 first_last_relay 付费提交，每段不超过上限，再在后续合成阶段接回。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - keep body pose stable; put speed into background, foreground occluders, cloth and camera tracking
  - avoid large limb changes unless there is an end frame
  - fill Action Choreography/动作编排契约: beats, speed_curve, spatial_path, camera_path, readability_beats, parallax_layers and route-specific chase/flight/mount/vehicle/vessel/road/stealth fields
  - 必须在单 Clip prompt 写 Action Choreography/动作编排契约，并逐项覆盖 beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, mount_contact, gait_cycle, screen_direction, parallax_layers, harness_lock；缺字段先回 n2d-script/n2d-video 补，不进入付费出视频。
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 长镜分段接力：不要单次提交整镜；按 duration_segment_relay.segments 用首帧→中段锚帧→尾帧分段生成。
- degrade_plan: Cut to front/back reaction shots or split into approach, pass-by, and exit clips.

### Clip_06 — dialogue_shot_reverse
- characters: CHAR_01, CHAR_04, GROUP_飞鹰门马队
- primary: seedance
- fallback: dreamina
- mode: image2video
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=3, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=3; refs_max=0; control_manifest=-
- policy_resolution: winner=frame_anchor_required signoff_required=False
  - conflict backend_choice: cross_episode_baseline, cost_quality_tier -> cross_episode_baseline
- rationale:
  - dialogue shots are identity-sensitive and often need lip-sync or strong reference controls
  - default n2d audio remains voiceover-first; do not let the video backend generate speech
  - 执行渠道「Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 20.955s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜 20.955s 超过 seedance 单次上限 15s；执行侧必须按现有首/中/尾帧拆成 4 段 first_last_relay 付费提交，每段不超过上限，再在后续合成阶段接回。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - mark mouth_visible and speech_policy=no_native_speech
  - prefer side/back/OTS if lip-sync is disabled
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 长镜分段接力：不要单次提交整镜；按 duration_segment_relay.segments 用首帧→中段锚帧→尾帧分段生成。
- degrade_plan: Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.

### Clip_07 — ensemble_blocking
- characters: CHAR_01, CHAR_04, GROUP_飞鹰门马队
- primary: seedance
- fallback: dreamina
- mode: frames2video
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=2, need_end=True)
- motion_control: required (manifest=出视频/第3集/control/Clip_07/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=2; refs_max=0; control_manifest=出视频/第3集/control/Clip_07/motion_control_manifest.json
- policy_resolution: winner=motion_control_required signoff_required=False
- rationale:
  - multi-person staging needs reference controls and stable screen direction
  - single-backend generic generation often swaps faces or screen positions
  - 5+ 同框/群像：Sora 已从自动路由移除；Kling 负责槽位/主体约束，仍不稳按 degrade_plan 拆组，不要把 5+ 清晰正脸压在同一镜。
  - 执行渠道「Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 13.998s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - write screen positions and focus hierarchy; background crowd must be silhouette, back view, or soft focus
  - one speaking/action focus per clip; do not ask every crowd member to have a clear face
  - bind each named registered character id to its own screen slot (LEFT/RIGHT/FOREGROUND/BACKGROUND) AND its own subject/reference anchor — regional/mask binding per subject; never feed one shared reference for the whole frame (single shared ref makes the model average faces)
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways.

### Clip_08 — dialogue_shot_reverse
- characters: CHAR_01, CHAR_04
- primary: seedance
- fallback: dreamina
- mode: image2video
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=9, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=9; refs_max=0; control_manifest=-
- policy_resolution: winner=frame_anchor_required signoff_required=False
  - conflict backend_choice: cross_episode_baseline, cost_quality_tier -> cross_episode_baseline
- rationale:
  - dialogue shots are identity-sensitive and often need lip-sync or strong reference controls
  - default n2d audio remains voiceover-first; do not let the video backend generate speech
  - 执行渠道「Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 34.492s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜 34.492s 超过 seedance 单次上限 15s；执行侧必须按现有首/中/尾帧拆成 10 段 first_last_relay 付费提交，每段不超过上限，再在后续合成阶段接回。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - mark mouth_visible and speech_policy=no_native_speech
  - prefer side/back/OTS if lip-sync is disabled
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 长镜分段接力：不要单次提交整镜；按 duration_segment_relay.segments 用首帧→中段锚帧→尾帧分段生成。
  - motion_spectacle_guidance：按本字段把风格自适应视觉盛宴落进运动描述（体积光/速度线随风格族变体·勿给赛璐璐/水墨硬塞写实 motion blur）
- degrade_plan: Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.

### Clip_09 — relationship_turn
- characters: CHAR_01, CHAR_04
- primary: seedance
- fallback: dreamina
- mode: image2video
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=4, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=4; refs_max=0; control_manifest=-
- policy_resolution: winner=frame_anchor_required signoff_required=False
- rationale:
  - relationship turns depend on micro-expression, eyeline, and precise before/after state
  - these shots carry irreversible story state changes, so visual identity, eyeline, and reaction order outrank generic speech routing
  - 执行渠道「Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 16.842s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜 16.842s 超过 seedance 单次上限 15s；执行侧必须按现有首/中/尾帧拆成 5 段 first_last_relay 付费提交，每段不超过上限，再在后续合成阶段接回。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - mark mouth_visible when faces speak; speech_policy=no_native_speech unless this clip is explicitly rerouted to a native AV backend
  - lock relationship_state_before, turning_action, subtext, and relationship_state_after from template_contract
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 长镜分段接力：不要单次提交整镜；按 duration_segment_relay.segments 用首帧→中段锚帧→尾帧分段生成。
- degrade_plan: Switch to single-face CU, hand insert, or OTS if the two-shot overplays contact or expression.

### Clip_10 — dialogue_shot_reverse
- characters: CHAR_01, CHAR_04
- primary: seedance
- fallback: dreamina
- mode: image2video
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=3, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=3; refs_max=0; control_manifest=-
- policy_resolution: winner=frame_anchor_required signoff_required=False
  - conflict backend_choice: cross_episode_baseline, cost_quality_tier -> cross_episode_baseline
- rationale:
  - dialogue shots are identity-sensitive and often need lip-sync or strong reference controls
  - default n2d audio remains voiceover-first; do not let the video backend generate speech
  - 执行渠道「Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 13.06s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - mark mouth_visible and speech_policy=no_native_speech
  - prefer side/back/OTS if lip-sync is disabled
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.

