# 视频模型路由

- episode: 第1集
- routing_mode: auto
- production_mode: 原生音画 (av_mode=native_av)
- default_backend: dreamina
- generated_at: 2026-07-01T12:37:32+00:00

## 本集模型路由表

| Clip | characters | shot_type | primary | fallback | mode | 档 | 帧消费 | native_audio | identity | motion_control | policy | 风险 | 降级 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Clip_01 | CHAR_01 | dialogue_shot_reverse | seedance | seedance | native_av | high | native_multiframe | native_speech | character_id_or_reference_group | none | native_voice_fallback | multishot_candidate, native_multiframe, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_02 | CHAR_01, CHAR_03 | realm_portal | seedance | dreamina | image2video | high | native_multiframe | none | face_lock_or_reference_group | none | cost_quality_tier | identity_drift_risk, multishot_candidate, native_multiframe, readability_hold_required, seam_relay, vfx_consistency_risk | Split into setup plate, activation/impact insert, and result/reaction; keep VFX shape from shared assets or overlay geometry. |
| Clip_03 | CHAR_01, CHAR_02 | dialogue_shot_reverse | seedance | seedance | native_av | high | native_multiframe | native_speech | character_id_or_reference_group | none | native_voice_fallback | mouth_visible, native_multiframe, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_04 | CHAR_01, CHAR_02 | multi_character_same_frame | seedance | seedance | native_av | high | native_multiframe | native_speech | character_id_or_reference_group | required | native_voice_fallback | identity_drift_risk, mouth_visible, multi_person, native_multiframe, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_05 | CHAR_01, CHAR_02, CHAR_03 | reveal_reaction_chain | seedance | seedance | native_av | high | native_multiframe | native_speech | character_id_or_reference_group | none | native_voice_fallback | identity_drift_risk, mouth_visible, native_multiframe, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_06 | CHAR_01, CHAR_02, CHAR_03 | fight_exchange | seedance | seedance | native_av | high | native_multiframe | native_speech | character_id_or_reference_group | required | native_voice_fallback | action_choreography_required, contact_motion, feature_melting_risk, identity_drift_risk, motion_reference_candidate, mouth_visible, multi_person, native_multiframe, native_speech, physical_interaction, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_07 | CHAR_01, CHAR_02 | dialogue_shot_reverse | seedance | seedance | native_av | high | native_multiframe | native_speech | character_id_or_reference_group | none | native_voice_fallback | native_multiframe, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_08 | CHAR_01, CHAR_02, CHAR_03 | dialogue_shot_reverse | seedance | seedance | native_av | high | native_multiframe | native_speech | character_id_or_reference_group | none | native_voice_fallback | native_multiframe, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_09 | CHAR_01, CHAR_02, CHAR_03 | dialogue_shot_reverse | seedance | seedance | native_av | high | native_multiframe | native_speech | character_id_or_reference_group | none | native_voice_fallback | mouth_visible, multishot_candidate, native_multiframe, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_10 | CHAR_01, CHAR_02 | fight_exchange | seedance | seedance | native_av | high | native_multiframe | native_speech | character_id_or_reference_group | required | native_voice_fallback | action_choreography_required, contact_motion, feature_melting_risk, identity_drift_risk, motion_reference_candidate, mouth_visible, multishot_candidate, native_multiframe, native_speech, physical_interaction, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_11 | CHAR_01, CHAR_02, CHAR_03 | multi_character_same_frame | dreamina | seedance | frames2video | high | native_multiframe | none | character_id_or_reference_group | required | motion_control_required | identity_drift_risk, multi_person, native_multiframe | If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip. |

## 多镜单次生成候选组（advisory·可选一次 co-generate 消缝）

- MSG_01（seedance）: Clip_01, Clip_02 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_02（seedance）: Clip_09, Clip_10 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。

## 逐 Clip 路由理由

### Clip_01 — dialogue_shot_reverse
- characters: CHAR_01
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- multishot_candidate: MSG_01 ['Clip_01', 'Clip_02']
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 dreamina 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_02 — realm_portal
- characters: CHAR_01, CHAR_03
- primary: seedance
- fallback: dreamina
- mode: image2video
- quality_tier: high
- multishot_candidate: MSG_01 ['Clip_01', 'Clip_02']
- identity: face_lock_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - high-energy genre spectacle needs stable VFX/asset locks and controlled progression rather than freeform effects
  - image2video preserves the keyed lightning/array/portal/summon plate while letting light, particles, and camera move
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 kling 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - lock all VFX/asset ids from template_contract; do not invent new lightning, array geometry, portal shape, summon silhouette, or contract mark
  - one spectacle result per clip; split omen/setup, activation/entry, and reveal/result if the beat chain is longer than three steps
  - write readability_beats and degrade_plan from the template_contract; text/numbers/talent labels go to overlay when present
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: Split into setup plate, activation/impact insert, and result/reaction; keep VFX shape from shared assets or overlay geometry.

### Clip_03 — dialogue_shot_reverse
- characters: CHAR_01, CHAR_02
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 dreamina 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_04 — multi_character_same_frame
- characters: CHAR_01, CHAR_02
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_04/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=出视频/第1集/control/Clip_04/motion_control_manifest.json
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 dreamina 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_05 — reveal_reaction_chain
- characters: CHAR_01, CHAR_02, CHAR_03
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 dreamina 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_06 — fight_exchange
- characters: CHAR_01, CHAR_02, CHAR_03
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- motion_reference: 用前序已通过 clip 作运动/风格参考(reference_video_motion)
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_06/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks, contact_map, camera_path
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=出视频/第1集/control/Clip_06/motion_control_manifest.json
- action_choreography: setup_attack_impact_reaction_recovery (gate=block_prompt_without_action_choreography_contract)
- action_choreography_required_fields: beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 dreamina 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
  - seedance 支持视频片段参考（reference_video_motion）：把同段前一条已通过的 clip 作运动/风格参考喂进去，锁运镜节奏与运动风格（与图身份锁正交的跨镜运动连续性轴）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 必须在单 Clip prompt 写 Action Choreography/动作编排契约，并逐项覆盖 beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat；缺字段先回 n2d-script/n2d-video 补，不进入付费出视频。
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 若有同段前序已通过 clip：把它作为视频运动/风格参考(reference_video_motion)喂给后端，锁运镜节奏；首条镜无前序参考则跳过。
  - motion_spectacle_guidance：按本字段把风格自适应视觉盛宴落进运动描述（体积光/速度线随风格族变体·勿给赛璐璐/水墨硬塞写实 motion blur）
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_07 — dialogue_shot_reverse
- characters: CHAR_01, CHAR_02
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 dreamina 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_08 — dialogue_shot_reverse
- characters: CHAR_01, CHAR_02, CHAR_03
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 dreamina 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_09 — dialogue_shot_reverse
- characters: CHAR_01, CHAR_02, CHAR_03
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- multishot_candidate: MSG_02 ['Clip_09', 'Clip_10']
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 dreamina 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_10 — fight_exchange
- characters: CHAR_01, CHAR_02
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- motion_reference: 用前序已通过 clip 作运动/风格参考(reference_video_motion)
- multishot_candidate: MSG_02 ['Clip_09', 'Clip_10']
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_10/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks, contact_map, camera_path
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=出视频/第1集/control/Clip_10/motion_control_manifest.json
- action_choreography: setup_attack_impact_reaction_recovery (gate=block_prompt_without_action_choreography_contract)
- action_choreography_required_fields: beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 dreamina 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
  - seedance 支持视频片段参考（reference_video_motion）：把同段前一条已通过的 clip 作运动/风格参考喂进去，锁运镜节奏与运动风格（与图身份锁正交的跨镜运动连续性轴）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 必须在单 Clip prompt 写 Action Choreography/动作编排契约，并逐项覆盖 beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, attack_path, impact_frame, contact_points, force_direction, recovery_beat；缺字段先回 n2d-script/n2d-video 补，不进入付费出视频。
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 若有同段前序已通过 clip：把它作为视频运动/风格参考(reference_video_motion)喂给后端，锁运镜节奏；首条镜无前序参考则跳过。
  - motion_spectacle_guidance：按本字段把风格自适应视觉盛宴落进运动描述（体积光/速度线随风格族变体·勿给赛璐璐/水墨硬塞写实 motion blur）
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_11 — multi_character_same_frame
- characters: CHAR_01, CHAR_02, CHAR_03
- primary: dreamina
- fallback: seedance
- mode: frames2video
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=False)
- motion_control: required (manifest=出视频/第1集/control/Clip_11/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=出视频/第1集/control/Clip_11/motion_control_manifest.json
- policy_resolution: winner=motion_control_required signoff_required=False
- rationale:
  - multi-person staging needs reference controls and stable screen direction
  - single-backend generic generation often swaps faces or screen positions
  - 执行渠道「Dreamina」对 dreamina 具备多关键帧/尾帧能力；原 primary「kling」与本镜 storyboard 帧/时长契约不匹配（storyboard has mid anchors but primary lacks native mid-anchor control），因此改用项目默认后端执行，原 primary 降为 fallback。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - freeze character slots, left/right positions, and face priority
  - keep two to three named faces maximum; lower-priority faces may be side/back/soft focus
  - bind each named registered character id to its own screen slot (LEFT/RIGHT/FOREGROUND/BACKGROUND) AND its own subject/reference anchor — regional/mask binding per subject; never feed one shared reference for the whole frame (single shared ref makes the model average faces)
- degrade_plan: If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.

