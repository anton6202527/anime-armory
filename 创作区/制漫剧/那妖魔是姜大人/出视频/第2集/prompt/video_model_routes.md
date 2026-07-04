# 视频模型路由

- episode: 第2集
- routing_mode: auto
- production_mode: 先出视频后配音 (av_mode=voice_first)
- default_backend: dreamina
- generated_at: 2026-07-04T02:41:48+00:00

## 本集模型路由表

| Clip | characters | shot_type | primary | fallback | mode | 档 | 帧消费 | native_audio | identity | motion_control | policy | 风险 | 降级 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Clip_01 | CHAR_01, CHAR_02, CHAR_03 | general_motion | seedance | dreamina | image2video | high | native_multiframe | none | native_identity_lock_required | none | identity_affinity | identity_escalated, native_multiframe, seam_relay | If action or identity fails twice, reroute to the nearest specialized shot type. |
| Clip_02 | CHAR_01, CHAR_02, CHAR_03 | dialogue_shot_reverse | seedance | dreamina | image2video | high | native_multiframe | none | character_id_or_reference_group | none | cross_episode_baseline | mouth_visible, native_multiframe, seam_relay | Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails. |
| Clip_03 | CHAR_01, CHAR_03, CHAR_02 | fight_exchange | seedance | dreamina | frames2video | high | native_multiframe | none | character_id_or_reference_group | required | motion_control_required | action_choreography_required, contact_motion, feature_melting_risk, identity_drift_risk, motion_reference_candidate, mouth_visible, native_multiframe, physical_interaction, seam_relay | Split into setup and impact clips; keep the hit frame as the end frame. |
| Clip_04 | CHAR_01, CHAR_03 | fight_exchange | seedance | dreamina | frames2video | high | native_multiframe | none | character_id_or_reference_group | required | motion_control_required | action_choreography_required, contact_motion, feature_melting_risk, identity_drift_risk, motion_reference_candidate, native_multiframe, physical_interaction, seam_relay | Split into setup and impact clips; keep the hit frame as the end frame. |
| Clip_05 | CHAR_01, CHAR_03 | stealth_stalk | seedance | dreamina | image2video | high | native_multiframe | none | face_lock_or_reference_group | required | motion_control_required | action_choreography_required, high_speed_motion, identity_drift_risk, motion_reference_candidate, mouth_visible, native_multiframe, pose_drift_risk, seam_relay, spatial_path_risk | Cut to front/back reaction shots or split into approach, pass-by, and exit clips. |
| Clip_06 | CHAR_01, CHAR_03 | general_motion | dreamina | seedance | image2video | fast | native_multiframe | none | reference_group | none | cost_quality_tier | mouth_visible, multishot_reroute_candidate, native_multiframe, seam_relay | If action or identity fails twice, reroute to the nearest specialized shot type. |
| Clip_07 | CHAR_01, CHAR_03 | general_motion | dreamina | seedance | image2video | fast | native_multiframe | none | reference_group | none | cost_quality_tier | duration_segment_relay, multishot_reroute_candidate, native_multiframe, seam_relay | If action or identity fails twice, reroute to the nearest specialized shot type. |
| Clip_08 | CHAR_01, CHAR_03, CHAR_02 | reveal_reaction_chain | seedance | dreamina | image2video | high | native_multiframe | none | character_id_or_reference_group | none | cross_episode_baseline | identity_drift_risk, native_multiframe, seam_relay | Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift. |
| Clip_09 | CHAR_01, CHAR_02 | intimate_interaction | seedance | dreamina | frames2video | high | native_multiframe | none | character_id_or_reference_group | required | motion_control_required | contact_motion, feature_melting_risk, identity_drift_risk, native_multiframe, physical_interaction, seam_relay | Replace full contact with reaction close-up, hand insert, or shot/reverse-shot. |
| Clip_10 | CHAR_01, CHAR_02 | stealth_stalk | seedance | dreamina | image2video | high | native_multiframe | none | face_lock_or_reference_group | required | motion_control_required | action_choreography_required, high_speed_motion, identity_drift_risk, motion_reference_candidate, native_multiframe, pose_drift_risk, seam_relay, spatial_path_risk | Cut to front/back reaction shots or split into approach, pass-by, and exit clips. |

## 逐 Clip 路由理由

### Clip_01 — general_motion
- characters: CHAR_01, CHAR_02, CHAR_03
- primary: seedance
- fallback: dreamina
- mode: image2video
- quality_tier: high
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - general motion can use the project default backend for cost and speed
  - 接力镜：primary「dreamina」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 2 次：primary「dreamina」无原生身份锁，升锁改用「seedance」(Character ID/Face Lock) 把脸钉死后再生成。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - keep character/camera/dynamic detail three-part prompt explicit
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: If action or identity fails twice, reroute to the nearest specialized shot type.

### Clip_02 — dialogue_shot_reverse
- characters: CHAR_01, CHAR_02, CHAR_03
- primary: seedance
- fallback: dreamina
- mode: image2video
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=cross_episode_baseline signoff_required=False
  - conflict backend_choice: cross_episode_baseline, cost_quality_tier -> cross_episode_baseline
- rationale:
  - dialogue shots are identity-sensitive and often need lip-sync or strong reference controls
  - default n2d audio remains voiceover-first; do not let the video backend generate speech
  - 执行渠道「Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 12.349s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - mark mouth_visible and speech_policy=no_native_speech
  - prefer side/back/OTS if lip-sync is disabled
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.

### Clip_03 — fight_exchange
- characters: CHAR_01, CHAR_03, CHAR_02
- primary: seedance
- fallback: dreamina
- mode: frames2video
- quality_tier: high
- motion_reference: 用前序已通过 clip 作运动/风格参考(reference_video_motion)
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=2, need_end=True)
- motion_control: required (manifest=出视频/第2集/control/Clip_03/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks, contact_map, camera_path
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=2; refs_max=0; control_manifest=出视频/第2集/control/Clip_03/motion_control_manifest.json
- action_choreography: setup_attack_impact_reaction_recovery (gate=block_prompt_without_action_choreography_contract)
- action_choreography_required_fields: beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat
- policy_resolution: winner=motion_control_required signoff_required=False
  - conflict backend_choice: cross_episode_baseline, cost_quality_tier -> cross_episode_baseline
- rationale:
  - fight/contact motion benefits from first/last frame control
  - impact beats need short controllable motion rather than free choreography
  - 执行渠道「Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 11.477s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
  - seedance 支持视频片段参考（reference_video_motion）：把同段前一条已通过的 clip 作运动/风格参考喂进去，锁运镜节奏与运动风格（与图身份锁正交的跨镜运动连续性轴）。
- prompt_requirements:
  - write first frame and end frame as hard constraints
  - one contact action per clip; avoid multi-hit choreography
  - fill Action Choreography/动作编排契约: beats, speed_curve, spatial_path, camera_path, readability_beats, attack_path, impact_frame, contact_points, force_direction, recovery_beat
  - 必须在单 Clip prompt 写 Action Choreography/动作编排契约，并逐项覆盖 beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat；缺字段先回 n2d-script/n2d-video 补，不进入付费出视频。
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 若有同段前序已通过 clip：把它作为视频运动/风格参考(reference_video_motion)喂给后端，锁运镜节奏；首条镜无前序参考则跳过。
  - motion_spectacle_guidance：按本字段把风格自适应视觉盛宴落进运动描述（体积光/速度线随风格族变体·勿给赛璐璐/水墨硬塞写实 motion blur）
- degrade_plan: Split into setup and impact clips; keep the hit frame as the end frame.

### Clip_04 — fight_exchange
- characters: CHAR_01, CHAR_03
- primary: seedance
- fallback: dreamina
- mode: frames2video
- quality_tier: high
- motion_reference: 用前序已通过 clip 作运动/风格参考(reference_video_motion)
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=3, need_end=True)
- motion_control: required (manifest=出视频/第2集/control/Clip_04/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks, contact_map, camera_path
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=3; refs_max=0; control_manifest=出视频/第2集/control/Clip_04/motion_control_manifest.json
- action_choreography: setup_attack_impact_reaction_recovery (gate=block_prompt_without_action_choreography_contract)
- action_choreography_required_fields: beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat
- policy_resolution: winner=motion_control_required signoff_required=False
  - conflict backend_choice: cross_episode_baseline, cost_quality_tier -> cross_episode_baseline
- rationale:
  - fight/contact motion benefits from first/last frame control
  - impact beats need short controllable motion rather than free choreography
  - 执行渠道「Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 11.995s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
  - seedance 支持视频片段参考（reference_video_motion）：把同段前一条已通过的 clip 作运动/风格参考喂进去，锁运镜节奏与运动风格（与图身份锁正交的跨镜运动连续性轴）。
- prompt_requirements:
  - write first frame and end frame as hard constraints
  - one contact action per clip; avoid multi-hit choreography
  - fill Action Choreography/动作编排契约: beats, speed_curve, spatial_path, camera_path, readability_beats, attack_path, impact_frame, contact_points, force_direction, recovery_beat
  - 必须在单 Clip prompt 写 Action Choreography/动作编排契约，并逐项覆盖 beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat；缺字段先回 n2d-script/n2d-video 补，不进入付费出视频。
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 若有同段前序已通过 clip：把它作为视频运动/风格参考(reference_video_motion)喂给后端，锁运镜节奏；首条镜无前序参考则跳过。
  - motion_spectacle_guidance：按本字段把风格自适应视觉盛宴落进运动描述（体积光/速度线随风格族变体·勿给赛璐璐/水墨硬塞写实 motion blur）
- degrade_plan: Split into setup and impact clips; keep the hit frame as the end frame.

### Clip_05 — stealth_stalk
- characters: CHAR_01, CHAR_03
- primary: seedance
- fallback: dreamina
- mode: image2video
- quality_tier: high
- motion_reference: 用前序已通过 clip 作运动/风格参考(reference_video_motion)
- identity: face_lock_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: required (manifest=出视频/第2集/control/Clip_05/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, camera_path, spatial_path, parallax_layers
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=出视频/第2集/control/Clip_05/motion_control_manifest.json
- action_choreography: hide_establish_shadow_approach_reveal_or_hide (gate=block_prompt_without_action_choreography_contract)
- action_choreography_required_fields: beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, screen_direction, distance_curve, occlusion_layers, light_shadow_lock, reveal_or_hide_beat, parallax_layers
- policy_resolution: winner=motion_control_required signoff_required=False
- rationale:
  - long continuous motion and moving backgrounds benefit from longer single-shot generation
  - flight/chase/mount/vehicle/vessel/road/stealth shots should lock subject shape and put speed or suspense into background, parallax, gait, wheels, traffic, light, or occlusion layers
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
  - seedance 支持视频片段参考（reference_video_motion）：把同段前一条已通过的 clip 作运动/风格参考喂进去，锁运镜节奏与运动风格（与图身份锁正交的跨镜运动连续性轴）。
- prompt_requirements:
  - keep body pose stable; put speed into background, foreground occluders, cloth and camera tracking
  - avoid large limb changes unless there is an end frame
  - fill Action Choreography/动作编排契约: beats, speed_curve, spatial_path, camera_path, readability_beats, parallax_layers and route-specific chase/flight/mount/vehicle/vessel/road/stealth fields
  - 必须在单 Clip prompt 写 Action Choreography/动作编排契约，并逐项覆盖 beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, screen_direction, distance_curve, occlusion_layers, light_shadow_lock, reveal_or_hide_beat, parallax_layers；缺字段先回 n2d-script/n2d-video 补，不进入付费出视频。
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 若有同段前序已通过 clip：把它作为视频运动/风格参考(reference_video_motion)喂给后端，锁运镜节奏；首条镜无前序参考则跳过。
- degrade_plan: Cut to front/back reaction shots or split into approach, pass-by, and exit clips.

### Clip_06 — general_motion
- characters: CHAR_01, CHAR_03
- primary: dreamina
- fallback: seedance
- mode: image2video
- quality_tier: fast
- identity: reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - general motion can use the project default backend for cost and speed
  - 接力镜：primary「dreamina」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=fast：通用/低身份风险镜走量产快档省成本（落档侧解析为后端 fast model_version）。
- prompt_requirements:
  - keep character/camera/dynamic detail three-part prompt explicit
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: If action or identity fails twice, reroute to the nearest specialized shot type.

### Clip_07 — general_motion
- characters: CHAR_01, CHAR_03
- primary: dreamina
- fallback: seedance
- mode: image2video
- quality_tier: fast
- identity: reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - general motion can use the project default backend for cost and speed
  - 接力镜：primary「dreamina」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜 16.492s 超过 dreamina 单次上限 15s；执行侧必须按现有首/中/尾帧拆成 2 段 first_last_relay 付费提交，每段不超过上限，再在后续合成阶段接回。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=fast：通用/低身份风险镜走量产快档省成本（落档侧解析为后端 fast model_version）。
- prompt_requirements:
  - keep character/camera/dynamic detail three-part prompt explicit
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 长镜分段接力：不要单次提交整镜；按 duration_segment_relay.segments 用首帧→中段锚帧→尾帧分段生成。
- degrade_plan: If action or identity fails twice, reroute to the nearest specialized shot type.

### Clip_08 — reveal_reaction_chain
- characters: CHAR_01, CHAR_03, CHAR_02
- primary: seedance
- fallback: dreamina
- mode: image2video
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=cross_episode_baseline signoff_required=False
  - conflict backend_choice: cross_episode_baseline, cost_quality_tier -> cross_episode_baseline
- rationale:
  - reveal scenes are identity- and reaction-chain-sensitive
  - these shots carry irreversible story state changes, so visual identity, eyeline, and reaction order outrank generic speech routing
  - 执行渠道「Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - mark mouth_visible when faces speak; speech_policy=no_native_speech unless this clip is explicitly rerouted to a native AV backend
  - lock reveal_object, knowledge_order, reaction_beats, and cut_point from template_contract
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.

### Clip_09 — intimate_interaction
- characters: CHAR_01, CHAR_02
- primary: seedance
- fallback: dreamina
- mode: frames2video
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=3, need_end=True)
- motion_control: required (manifest=出视频/第2集/control/Clip_09/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=3; refs_max=0; control_manifest=出视频/第2集/control/Clip_09/motion_control_manifest.json
- policy_resolution: winner=motion_control_required signoff_required=False
- rationale:
  - close contact and occlusion need precise motion and identity control
  - hands/faces are high-risk and should be constrained by first/last frames
  - 执行渠道「Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 13.207s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - write exact blocking and contact point; avoid ambiguous full-body interaction
  - use end frame for the final pose
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: Replace full contact with reaction close-up, hand insert, or shot/reverse-shot.

### Clip_10 — stealth_stalk
- characters: CHAR_01, CHAR_02
- primary: seedance
- fallback: dreamina
- mode: image2video
- quality_tier: high
- motion_reference: 用前序已通过 clip 作运动/风格参考(reference_video_motion)
- identity: face_lock_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: required (manifest=出视频/第2集/control/Clip_10/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, camera_path, spatial_path, parallax_layers
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=出视频/第2集/control/Clip_10/motion_control_manifest.json
- action_choreography: hide_establish_shadow_approach_reveal_or_hide (gate=block_prompt_without_action_choreography_contract)
- action_choreography_required_fields: beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, screen_direction, distance_curve, occlusion_layers, light_shadow_lock, reveal_or_hide_beat, parallax_layers
- policy_resolution: winner=motion_control_required signoff_required=False
- rationale:
  - long continuous motion and moving backgrounds benefit from longer single-shot generation
  - flight/chase/mount/vehicle/vessel/road/stealth shots should lock subject shape and put speed or suspense into background, parallax, gait, wheels, traffic, light, or occlusion layers
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
  - seedance 支持视频片段参考（reference_video_motion）：把同段前一条已通过的 clip 作运动/风格参考喂进去，锁运镜节奏与运动风格（与图身份锁正交的跨镜运动连续性轴）。
- prompt_requirements:
  - keep body pose stable; put speed into background, foreground occluders, cloth and camera tracking
  - avoid large limb changes unless there is an end frame
  - fill Action Choreography/动作编排契约: beats, speed_curve, spatial_path, camera_path, readability_beats, parallax_layers and route-specific chase/flight/mount/vehicle/vessel/road/stealth fields
  - 必须在单 Clip prompt 写 Action Choreography/动作编排契约，并逐项覆盖 beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, screen_direction, distance_curve, occlusion_layers, light_shadow_lock, reveal_or_hide_beat, parallax_layers；缺字段先回 n2d-script/n2d-video 补，不进入付费出视频。
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 若有同段前序已通过 clip：把它作为视频运动/风格参考(reference_video_motion)喂给后端，锁运镜节奏；首条镜无前序参考则跳过。
  - motion_spectacle_guidance：按本字段把风格自适应视觉盛宴落进运动描述（体积光/速度线随风格族变体·勿给赛璐璐/水墨硬塞写实 motion blur）
- degrade_plan: Cut to front/back reaction shots or split into approach, pass-by, and exit clips.

