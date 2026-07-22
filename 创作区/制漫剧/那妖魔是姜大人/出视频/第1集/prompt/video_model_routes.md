# 视频模型路由

- episode: 第1集
- routing_mode: auto
- production_mode: 混合自动路由 (av_mode=hybrid)
- default_backend: seedance
- execution_adapter_v2: {'automated_ready': 8}
- generated_at: 2026-07-21T20:41:39+00:00

## 本集模型路由表

| Clip | characters | shot_type | primary | fallback | mode | 时间基准 | 声音策略 | 表演轨 | 档 | 帧消费 | native_audio | identity | motion_control | policy | 风险 | 降级 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Clip_01 | CHAR_01/囚途残损态, CHAR_02/濒死态, BEAST_01/复生态焦外 | general_motion | seedance | dreamina | image2video | final_voice | performance_audio_first | final_ready | high | native_multiframe | none | native_identity_lock_required | none | identity_affinity | identity_escalated, native_multiframe | If action or identity fails twice, reroute to the nearest specialized shot type. |
| Clip_02 | CHAR_01/囚途残损态, CHAR_02/半跪重伤态, BEAST_01/伪死态 | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | final_voice | performance_audio_first | final_ready | high | native_multiframe | lipsync_condition_only | native_identity_lock_required | none | identity_affinity | identity_escalated, mouth_visible, native_multiframe | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_03 | CHAR_01/囚途残损态, CHAR_02/半跪重伤态 | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | final_voice | performance_audio_first | final_ready | high | native_multiframe | lipsync_condition_only | native_identity_lock_required | none | identity_affinity | identity_escalated, mouth_visible, native_multiframe | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_04 | CHAR_01/囚途残损态, CHAR_02/重伤态, BEAST_01/伪死态 | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | final_voice | performance_audio_first | final_ready | high | native_multiframe | lipsync_condition_only | native_identity_lock_required | none | identity_affinity | identity_escalated, mouth_visible, native_multiframe | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_05 | CHAR_01/囚途残损态, CHAR_02/重伤搀扶态, BEAST_01/复生态 | reveal_reaction_chain | seedance | dreamina | image2video | final_voice | performance_audio_first | final_ready | high | native_multiframe | none | native_identity_lock_required | none | identity_affinity | identity_drift_risk, identity_escalated, native_multiframe | Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift. |
| Clip_06 | CHAR_01/囚途残损态, CHAR_02/搏命冲锋至倒地濒死态, BEAST_01/复生态 | fight_exchange | seedance | dreamina | voice_conditioned_lipsync | final_voice | performance_audio_first | final_ready | high | native_multiframe | lipsync_condition_only | native_identity_lock_required | required | identity_affinity | action_choreography_required, contact_motion, feature_melting_risk, identity_drift_risk, identity_escalated, motion_reference_candidate, mouth_visible, multi_person, native_multiframe, physical_interaction | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_07 | CHAR_01/囚途残损态, CHAR_02/濒死态, BEAST_01/复生态 | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | final_voice | performance_audio_first | final_ready | high | native_multiframe | lipsync_condition_only | native_identity_lock_required | none | identity_affinity | identity_escalated, native_multiframe | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_08 | CHAR_01/囚途残损态, CHAR_02/濒死受刀态, BEAST_01/焦外 | fight_exchange | seedance | dreamina | frames2video | final_voice | performance_audio_first | final_ready | high | native_multiframe | none | native_identity_lock_required | required | identity_affinity | action_choreography_required, contact_motion, feature_melting_risk, identity_drift_risk, identity_escalated, motion_reference_candidate, native_multiframe, physical_interaction | Split into setup and impact clips; keep the hit frame as the end frame. |

## 逐 Clip 路由理由

### Clip_01 — general_motion
- characters: CHAR_01/囚途残损态, CHAR_02/濒死态, BEAST_01/复生态焦外
- primary: seedance
- fallback: dreamina
- mode: image2video
- sound: timing_basis=final_voice / audio_strategy=performance_audio_first / performance_track=final_ready / voice_lock=locked
- final_sound: stage=post_video_before_compose / post_lipsync_required=False / base_video_only=False
- quality_tier: high
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - general motion can use the project default backend for cost and speed
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 6 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - keep character/camera/dynamic detail three-part prompt explicit
- degrade_plan: If action or identity fails twice, reroute to the nearest specialized shot type.

### Clip_02 — dialogue_shot_reverse
- characters: CHAR_01/囚途残损态, CHAR_02/半跪重伤态, BEAST_01/伪死态
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- sound: timing_basis=final_voice / audio_strategy=performance_audio_first / performance_track=final_ready / voice_lock=locked
- final_sound: stage=post_video_before_compose / post_lipsync_required=False / base_video_only=False
- quality_tier: high
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=2, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=2; refs_max=0; control_manifest=-
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 4 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_03 — dialogue_shot_reverse
- characters: CHAR_01/囚途残损态, CHAR_02/半跪重伤态
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- sound: timing_basis=final_voice / audio_strategy=performance_audio_first / performance_track=final_ready / voice_lock=locked
- final_sound: stage=post_video_before_compose / post_lipsync_required=False / base_video_only=False
- quality_tier: high
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=2, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=2; refs_max=0; control_manifest=-
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 4 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_04 — dialogue_shot_reverse
- characters: CHAR_01/囚途残损态, CHAR_02/重伤态, BEAST_01/伪死态
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- sound: timing_basis=final_voice / audio_strategy=performance_audio_first / performance_track=final_ready / voice_lock=locked
- final_sound: stage=post_video_before_compose / post_lipsync_required=False / base_video_only=False
- quality_tier: high
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 4 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_05 — reveal_reaction_chain
- characters: CHAR_01/囚途残损态, CHAR_02/重伤搀扶态, BEAST_01/复生态
- primary: seedance
- fallback: dreamina
- mode: image2video
- sound: timing_basis=final_voice / audio_strategy=performance_audio_first / performance_track=final_ready / voice_lock=locked
- final_sound: stage=post_video_before_compose / post_lipsync_required=False / base_video_only=False
- quality_tier: high
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=2, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=2; refs_max=0; control_manifest=-
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - reveal scenes are identity- and reaction-chain-sensitive
  - these shots carry irreversible story state changes, so visual identity, eyeline, and reaction order outrank generic speech routing
  - 执行渠道「即梦/Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 9 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - mark mouth_visible when faces speak; speech_policy=no_native_speech unless this clip is explicitly rerouted to a native AV backend
  - lock reveal_object, knowledge_order, reaction_beats, and cut_point from template_contract
- degrade_plan: Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.

### Clip_06 — fight_exchange
- characters: CHAR_01/囚途残损态, CHAR_02/搏命冲锋至倒地濒死态, BEAST_01/复生态
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- sound: timing_basis=final_voice / audio_strategy=performance_audio_first / performance_track=final_ready / voice_lock=locked
- final_sound: stage=post_video_before_compose / post_lipsync_required=False / base_video_only=False
- quality_tier: high
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- motion_reference: 用前序已通过 clip 作运动/风格参考(reference_video_motion)
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=3, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_06/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks, contact_map, camera_path
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=3; refs_max=0; control_manifest=出视频/第1集/control/Clip_06/motion_control_manifest.json
- action_choreography: setup_attack_impact_reaction_recovery (gate=block_prompt_without_action_choreography_contract)
- action_choreography_required_fields: beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 8 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
  - seedance 支持视频片段参考（reference_video_motion）：把同段前一条已通过的 clip 作运动/风格参考喂进去，锁运镜节奏与运动风格（与图身份锁正交的跨镜运动连续性轴）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 必须在单 Clip prompt 写 Action Choreography/动作编排契约，并逐项覆盖 beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat；缺字段先回 n2d-script/n2d-video 补，不进入付费出视频。
  - 若有同段前序已通过 clip：把它作为视频运动/风格参考(reference_video_motion)喂给后端，锁运镜节奏；首条镜无前序参考则跳过。
  - motion_spectacle_guidance：按本字段把风格自适应视觉盛宴落进运动描述（体积光/速度线随风格族变体·勿给赛璐璐/水墨硬塞写实 motion blur）
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_07 — dialogue_shot_reverse
- characters: CHAR_01/囚途残损态, CHAR_02/濒死态, BEAST_01/复生态
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- sound: timing_basis=final_voice / audio_strategy=performance_audio_first / performance_track=final_ready / voice_lock=locked
- final_sound: stage=post_video_before_compose / post_lipsync_required=False / base_video_only=False
- quality_tier: high
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=2, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=2; refs_max=0; control_manifest=-
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 8 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_08 — fight_exchange
- characters: CHAR_01/囚途残损态, CHAR_02/濒死受刀态, BEAST_01/焦外
- primary: seedance
- fallback: dreamina
- mode: frames2video
- sound: timing_basis=final_voice / audio_strategy=performance_audio_first / performance_track=final_ready / voice_lock=locked
- final_sound: stage=post_video_before_compose / post_lipsync_required=False / base_video_only=False
- quality_tier: high
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- motion_reference: 用前序已通过 clip 作运动/风格参考(reference_video_motion)
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=4, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_08/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks, contact_map, camera_path
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=4; refs_max=0; control_manifest=出视频/第1集/control/Clip_08/motion_control_manifest.json
- action_choreography: setup_attack_impact_reaction_recovery (gate=block_prompt_without_action_choreography_contract)
- action_choreography_required_fields: beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - fight/contact motion benefits from first/last frame control
  - impact beats need short controllable motion rather than free choreography
  - 执行渠道「即梦/Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 12.88s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 12 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
  - seedance 支持视频片段参考（reference_video_motion）：把同段前一条已通过的 clip 作运动/风格参考喂进去，锁运镜节奏与运动风格（与图身份锁正交的跨镜运动连续性轴）。
- prompt_requirements:
  - write first frame and end frame as hard constraints
  - one contact action per clip; avoid multi-hit choreography
  - fill Action Choreography/动作编排契约: beats, speed_curve, spatial_path, camera_path, readability_beats, attack_path, impact_frame, contact_points, force_direction, recovery_beat
  - 必须在单 Clip prompt 写 Action Choreography/动作编排契约，并逐项覆盖 beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat；缺字段先回 n2d-script/n2d-video 补，不进入付费出视频。
  - 若有同段前序已通过 clip：把它作为视频运动/风格参考(reference_video_motion)喂给后端，锁运镜节奏；首条镜无前序参考则跳过。
  - motion_spectacle_guidance：按本字段把风格自适应视觉盛宴落进运动描述（体积光/速度线随风格族变体·勿给赛璐璐/水墨硬塞写实 motion blur）
- degrade_plan: Split into setup and impact clips; keep the hit frame as the end frame.

