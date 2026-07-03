# 视频模型路由

- episode: 第1集
- routing_mode: auto
- production_mode: 先出视频后配音 (av_mode=voice_first)
- default_backend: dreamina
- generated_at: 2026-07-03T12:54:56+00:00

## 本集模型路由表

| Clip | characters | shot_type | primary | fallback | mode | 档 | 帧消费 | native_audio | identity | motion_control | policy | 风险 | 降级 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Clip_01 | CHAR_01 | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | native_multiframe | lipsync_condition_only | native_identity_lock_required | none | identity_affinity | identity_escalated, native_multiframe, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_02 | CHAR_01, CHAR_03 | realm_portal | seedance | dreamina | image2video | high | native_multiframe | none | native_identity_lock_required | none | identity_affinity | duration_segment_relay, identity_drift_risk, identity_escalated, native_multiframe, readability_hold_required, seam_relay, vfx_consistency_risk | Split into setup plate, activation/impact insert, and result/reaction; keep VFX shape from shared assets or overlay geometry. |
| Clip_03 | CHAR_01, CHAR_02 | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | native_multiframe | lipsync_condition_only | native_identity_lock_required | none | identity_affinity | duration_segment_relay, identity_escalated, mouth_visible, native_multiframe, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_04 | CHAR_01, CHAR_02 | multi_character_same_frame | seedance | dreamina | voice_conditioned_lipsync | high | native_multiframe | lipsync_condition_only | native_identity_lock_required | required | identity_affinity | identity_drift_risk, identity_escalated, mouth_visible, multi_person, native_multiframe, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_05 | CHAR_01, CHAR_02, CHAR_03 | reveal_reaction_chain | seedance | dreamina | image2video | high | native_multiframe | none | native_identity_lock_required | none | identity_affinity | identity_drift_risk, identity_escalated, mouth_visible, native_multiframe, seam_relay | Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift. |
| Clip_06 | CHAR_01, CHAR_02, CHAR_03 | fight_exchange | seedance | dreamina | voice_conditioned_lipsync | high | native_multiframe | lipsync_condition_only | native_identity_lock_required | required | identity_affinity | action_choreography_required, contact_motion, feature_melting_risk, identity_drift_risk, identity_escalated, motion_reference_candidate, mouth_visible, multi_person, native_multiframe, physical_interaction, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_07 | CHAR_01, CHAR_02 | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | native_multiframe | lipsync_condition_only | native_identity_lock_required | none | identity_affinity | identity_escalated, native_multiframe, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_08 | CHAR_01, CHAR_02, CHAR_03 | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | native_multiframe | lipsync_condition_only | native_identity_lock_required | none | identity_affinity | identity_escalated, native_multiframe, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_09 | CHAR_01, CHAR_02, CHAR_03 | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | native_multiframe | lipsync_condition_only | native_identity_lock_required | none | identity_affinity | identity_escalated, mouth_visible, native_multiframe, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_10 | CHAR_01, CHAR_02 | fight_exchange | seedance | dreamina | voice_conditioned_lipsync | high | native_multiframe | lipsync_condition_only | native_identity_lock_required | required | identity_affinity | action_choreography_required, contact_motion, feature_melting_risk, identity_drift_risk, identity_escalated, motion_reference_candidate, mouth_visible, native_multiframe, physical_interaction, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_11 | CHAR_01, CHAR_02, CHAR_03 | multi_character_same_frame | seedance | dreamina | frames2video | high | first_frame | none | native_identity_lock_required | required | identity_affinity | identity_drift_risk, identity_escalated, multi_person | If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip. |

## 逐 Clip 路由理由

### Clip_01 — dialogue_shot_reverse
- characters: CHAR_01
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 2 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_02 — realm_portal
- characters: CHAR_01, CHAR_03
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
  - high-energy genre spectacle needs stable VFX/asset locks and controlled progression rather than freeform effects
  - image2video preserves the keyed lightning/array/portal/summon plate while letting light, particles, and camera move
  - 执行渠道「Dreamina」下改用可执行后端「dreamina」；原 primary「seedance」storyboard 帧/时长契约不匹配（duration 16.57s exceeds seedance max 15s），降为 fallback。
  - 接力镜：primary「dreamina」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜 16.57s 超过 dreamina 单次上限 15s；执行侧必须按现有首/中/尾帧拆成 2 段 first_last_relay 付费提交，每段不超过上限，再在后续合成阶段接回。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 2 次：primary「dreamina」无原生身份锁，升锁改用「seedance」(Character ID/Face Lock) 把脸钉死后再生成。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - lock all VFX/asset ids from template_contract; do not invent new lightning, array geometry, portal shape, summon silhouette, or contract mark
  - one spectacle result per clip; split omen/setup, activation/entry, and reveal/result if the beat chain is longer than three steps
  - write readability_beats and degrade_plan from the template_contract; text/numbers/talent labels go to overlay when present
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 长镜分段接力：不要单次提交整镜；按 duration_segment_relay.segments 用首帧→中段锚帧→尾帧分段生成。
- degrade_plan: Split into setup plate, activation/impact insert, and result/reaction; keep VFX shape from shared assets or overlay geometry.

### Clip_03 — dialogue_shot_reverse
- characters: CHAR_01, CHAR_02
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 执行渠道「Dreamina」下改用可执行后端「dreamina」；原 primary「seedance」storyboard 帧/时长契约不匹配（duration 18.752s exceeds seedance max 15s），降为 fallback。
  - 接力镜：primary「dreamina」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜 18.752s 超过 dreamina 单次上限 15s；执行侧必须按现有首/中/尾帧拆成 2 段 first_last_relay 付费提交，每段不超过上限，再在后续合成阶段接回。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 2 次：primary「dreamina」无原生身份锁，升锁改用「seedance」(Character ID/Face Lock) 把脸钉死后再生成。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 长镜分段接力：不要单次提交整镜；按 duration_segment_relay.segments 用首帧→中段锚帧→尾帧分段生成。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_04 — multi_character_same_frame
- characters: CHAR_01, CHAR_02
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_04/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=出视频/第1集/control/Clip_04/motion_control_manifest.json
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 2 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_05 — reveal_reaction_chain
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
  - reveal scenes are identity- and reaction-chain-sensitive
  - these shots carry irreversible story state changes, so visual identity, eyeline, and reaction order outrank generic speech routing
  - 执行渠道「Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 12.995s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 2 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - mark mouth_visible when faces speak; speech_policy=no_native_speech unless this clip is explicitly rerouted to a native AV backend
  - lock reveal_object, knowledge_order, reaction_beats, and cut_point from template_contract
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.

### Clip_06 — fight_exchange
- characters: CHAR_01, CHAR_02, CHAR_03
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- motion_reference: 用前序已通过 clip 作运动/风格参考(reference_video_motion)
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_06/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks, contact_map, camera_path
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=出视频/第1集/control/Clip_06/motion_control_manifest.json
- action_choreography: setup_attack_impact_reaction_recovery (gate=block_prompt_without_action_choreography_contract)
- action_choreography_required_fields: beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 2 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
  - seedance 支持视频片段参考（reference_video_motion）：把同段前一条已通过的 clip 作运动/风格参考喂进去，锁运镜节奏与运动风格（与图身份锁正交的跨镜运动连续性轴）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 必须在单 Clip prompt 写 Action Choreography/动作编排契约，并逐项覆盖 beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat；缺字段先回 n2d-script/n2d-video 补，不进入付费出视频。
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 若有同段前序已通过 clip：把它作为视频运动/风格参考(reference_video_motion)喂给后端，锁运镜节奏；首条镜无前序参考则跳过。
  - motion_spectacle_guidance：按本字段把风格自适应视觉盛宴落进运动描述（体积光/速度线随风格族变体·勿给赛璐璐/水墨硬塞写实 motion blur）
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_07 — dialogue_shot_reverse
- characters: CHAR_01, CHAR_02
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 2 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_08 — dialogue_shot_reverse
- characters: CHAR_01, CHAR_02, CHAR_03
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 2 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_09 — dialogue_shot_reverse
- characters: CHAR_01, CHAR_02, CHAR_03
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 2 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_10 — fight_exchange
- characters: CHAR_01, CHAR_02
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- motion_reference: 用前序已通过 clip 作运动/风格参考(reference_video_motion)
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_10/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks, contact_map, camera_path
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=出视频/第1集/control/Clip_10/motion_control_manifest.json
- action_choreography: setup_attack_impact_reaction_recovery (gate=block_prompt_without_action_choreography_contract)
- action_choreography_required_fields: beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 2 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
  - seedance 支持视频片段参考（reference_video_motion）：把同段前一条已通过的 clip 作运动/风格参考喂进去，锁运镜节奏与运动风格（与图身份锁正交的跨镜运动连续性轴）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 必须在单 Clip prompt 写 Action Choreography/动作编排契约，并逐项覆盖 beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat；缺字段先回 n2d-script/n2d-video 补，不进入付费出视频。
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 若有同段前序已通过 clip：把它作为视频运动/风格参考(reference_video_motion)喂给后端，锁运镜节奏；首条镜无前序参考则跳过。
  - motion_spectacle_guidance：按本字段把风格自适应视觉盛宴落进运动描述（体积光/速度线随风格族变体·勿给赛璐璐/水墨硬塞写实 motion blur）
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_11 — multi_character_same_frame
- characters: CHAR_01, CHAR_02, CHAR_03
- primary: seedance
- fallback: dreamina
- mode: frames2video
- quality_tier: high
- identity: native_identity_lock_required
- frame_consumption: first_frame (execution=dreamina, anchors=0, need_end=False)
- motion_control: required (manifest=出视频/第1集/control/Clip_11/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=first_frame anchors=0; refs_max=0; control_manifest=出视频/第1集/control/Clip_11/motion_control_manifest.json
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - multi-person staging needs reference controls and stable screen direction
  - single-backend generic generation often swaps faces or screen positions
  - 执行渠道「Dreamina」下改用可执行后端「seedance」；原 primary「kling」当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - ⚠️本镜 identity 已失败 2 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - freeze character slots, left/right positions, and face priority
  - keep two to three named faces maximum; lower-priority faces may be side/back/soft focus
  - bind each named registered character id to its own screen slot (LEFT/RIGHT/FOREGROUND/BACKGROUND) AND its own subject/reference anchor — regional/mask binding per subject; never feed one shared reference for the whole frame (single shared ref makes the model average faces)
- degrade_plan: If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.

