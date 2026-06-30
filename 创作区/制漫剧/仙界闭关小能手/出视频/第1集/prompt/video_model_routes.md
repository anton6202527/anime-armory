# 视频模型路由

- episode: 第1集
- routing_mode: auto
- production_mode: 原生音画 (av_mode=native_av)
- default_backend: seedance
- generated_at: 2026-06-30T08:28:35+00:00

## 本集模型路由表

| Clip | characters | shot_type | primary | fallback | mode | 档 | 帧消费 | native_audio | identity | motion_control | policy | 风险 | 降级 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Clip_01 | CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CROWD_ZAYI | dialogue_shot_reverse | seedance | seedance | native_av | high | first_last | native_speech | character_id_or_reference_group | none | native_voice_fallback | mouth_visible, multi_person, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_02 | CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CROWD_ZAYI | dialogue_shot_reverse | seedance | seedance | native_av | high | first_last | native_speech | character_id_or_reference_group | none | native_voice_fallback | mouth_visible, multi_person, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_03 | CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CHAR_TAIXUMEN_ZHANGLAO | dialogue_shot_reverse | seedance | seedance | native_av | high | first_last | native_speech | character_id_or_reference_group | none | native_voice_fallback | mouth_visible, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_04 | CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CHAR_TAIXUMEN_ZHANGLAO | dialogue_shot_reverse | seedance | seedance | native_av | high | first_last | native_speech | character_id_or_reference_group | none | native_voice_fallback | mouth_visible, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_05 | CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN, CHAR_HE_SANJIE, CROWD_TAIXU_CULTIVATOR, CHAR_JIANG_JIAN/背影在中景偏右, CHAR_HE_SANJIE/回忆影只作旧影或旧物暗示, CHAR_HE_PINGSHENG/常态或幼年, CHAR_JIANG_JIAN/背影, CHAR_HE_SANJIE/回忆影 | ensemble_blocking | seedance | seedance | native_av | high | first_last | native_speech | character_id_or_reference_group | required | native_voice_fallback | identity_drift_risk, mouth_visible, multi_person, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_06 | CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN, CHAR_HE_SANJIE, CROWD_TAIXU_CULTIVATOR, CHAR_JIANG_JIAN/背影在中景偏右, CHAR_HE_SANJIE/回忆影只作旧影或旧物暗示, CHAR_HE_PINGSHENG/常态或幼年, CHAR_JIANG_JIAN/背影, CHAR_HE_SANJIE/回忆影 | ensemble_blocking | seedance | seedance | native_av | high | first_last | native_speech | character_id_or_reference_group | required | native_voice_fallback | identity_drift_risk, mouth_visible, multi_person, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_07 | CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN, CHAR_HE_PINGSHENG/常态, CHAR_HAN_LAOSAN/常态 | multi_character_same_frame | seedance | seedance | native_av | high | first_last | native_speech | none | required | native_voice_fallback | mouth_visible, multi_person, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_08 | CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN, CHAR_HE_PINGSHENG/常态, CHAR_HAN_LAOSAN/常态 | multi_character_same_frame | seedance | seedance | native_av | high | first_last | native_speech | none | required | native_voice_fallback | mouth_visible, multi_person, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_09 | CHAR_HE_PINGSHENG | road_vehicle | seedance | seedance | image2video | high | first_last | none | face_lock_or_reference_group | required | motion_control_required | action_choreography_required, high_speed_motion, identity_drift_risk, motion_reference_candidate, pose_drift_risk, seam_relay, spatial_path_risk | Cut to front/back reaction shots or split into approach, pass-by, and exit clips. |
| Clip_10 | CHAR_HE_PINGSHENG | road_vehicle | seedance | seedance | image2video | high | first_last | none | face_lock_or_reference_group | required | motion_control_required | action_choreography_required, high_speed_motion, identity_drift_risk, motion_reference_candidate, pose_drift_risk, seam_relay, spatial_path_risk | Cut to front/back reaction shots or split into approach, pass-by, and exit clips. |
| Clip_11 | CHAR_HE_PINGSHENG | general_motion | seedance | seedance | image2video | fast | native_multiframe | none | reference_group | none | cost_quality_tier | native_multiframe, seam_relay | If action or identity fails twice, reroute to the nearest specialized shot type. |
| Clip_12 | CHAR_HE_PINGSHENG | general_motion | seedance | seedance | image2video | fast | native_multiframe | none | reference_group | none | cost_quality_tier | native_multiframe | If action or identity fails twice, reroute to the nearest specialized shot type. |

## 逐 Clip 路由理由

### Clip_01 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CROWD_ZAYI
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——本批次不切外部后端；失败先按 degrade_only 拆镜或同后端重试，外部后端需重新 record-refresh + video_preflight。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_02 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CROWD_ZAYI
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——本批次不切外部后端；失败先按 degrade_only 拆镜或同后端重试，外部后端需重新 record-refresh + video_preflight。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_03 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CHAR_TAIXUMEN_ZHANGLAO
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——本批次不切外部后端；失败先按 degrade_only 拆镜或同后端重试，外部后端需重新 record-refresh + video_preflight。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_04 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CHAR_TAIXUMEN_ZHANGLAO
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——本批次不切外部后端；失败先按 degrade_only 拆镜或同后端重试，外部后端需重新 record-refresh + video_preflight。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_05 — ensemble_blocking
- characters: CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN, CHAR_HE_SANJIE, CROWD_TAIXU_CULTIVATOR, CHAR_JIANG_JIAN/背影在中景偏右, CHAR_HE_SANJIE/回忆影只作旧影或旧物暗示, CHAR_HE_PINGSHENG/常态或幼年, CHAR_JIANG_JIAN/背影, CHAR_HE_SANJIE/回忆影
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_05/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=出视频/第1集/control/Clip_05/motion_control_manifest.json
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——本批次不切外部后端；失败先按 degrade_only 拆镜或同后端重试，外部后端需重新 record-refresh + video_preflight。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_06 — ensemble_blocking
- characters: CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN, CHAR_HE_SANJIE, CROWD_TAIXU_CULTIVATOR, CHAR_JIANG_JIAN/背影在中景偏右, CHAR_HE_SANJIE/回忆影只作旧影或旧物暗示, CHAR_HE_PINGSHENG/常态或幼年, CHAR_JIANG_JIAN/背影, CHAR_HE_SANJIE/回忆影
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_06/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=出视频/第1集/control/Clip_06/motion_control_manifest.json
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——本批次不切外部后端；失败先按 degrade_only 拆镜或同后端重试，外部后端需重新 record-refresh + video_preflight。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_07 — multi_character_same_frame
- characters: CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN, CHAR_HE_PINGSHENG/常态, CHAR_HAN_LAOSAN/常态
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- identity: none
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_07/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=出视频/第1集/control/Clip_07/motion_control_manifest.json
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——本批次不切外部后端；失败先按 degrade_only 拆镜或同后端重试，外部后端需重新 record-refresh + video_preflight。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_08 — multi_character_same_frame
- characters: CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN, CHAR_HE_PINGSHENG/常态, CHAR_HAN_LAOSAN/常态
- primary: seedance
- fallback: seedance
- mode: native_av
- quality_tier: high
- identity: none
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_08/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=出视频/第1集/control/Clip_08/motion_control_manifest.json
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——本批次不切外部后端；失败先按 degrade_only 拆镜或同后端重试，外部后端需重新 record-refresh + video_preflight。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_09 — general_motion
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: seedance
- mode: image2video
- quality_tier: high
- motion_reference: 用前序已通过 clip 作运动/风格参考(reference_video_motion)
- identity: reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_09/motion_control_manifest.json)
- motion_control_required_inputs: depth_sequence, camera_path, spatial_path, parallax_layers
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=出视频/第1集/control/Clip_09/motion_control_manifest.json
- action_choreography: none (carrying-water montage; controlled by Motion Control degrade_only manifest, not road_vehicle)
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - walking/carrying-water montage should stay low-amplitude and readable; put fatigue into shoulders, bucket sway, water surface, and restrained camera movement
  - 接力镜：primary「seedance」无首尾硬约束能力——本批次不切外部后端；失败先按 degrade_only 拆镜或同后端重试，外部后端需重新 record-refresh + video_preflight。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
  - seedance 支持视频片段参考（reference_video_motion）：把同段前一条已通过的 clip 作运动/风格参考喂进去，锁运镜节奏与运动风格（与图身份锁正交的跨镜运动连续性轴）。
- prompt_requirements:
  - keep body pose stable; put speed into background, foreground occluders, cloth and camera tracking
  - avoid large limb changes unless there is an end frame
  - follow Motion Control degrade_only manifest; do not invent vehicle/road/lane/wheel constraints
  - same-backend retry only; no Kling/Veo fallback without new evidence refresh and preflight
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 若有同段前序已通过 clip：把它作为视频运动/风格参考(reference_video_motion)喂给后端，锁运镜节奏；首条镜无前序参考则跳过。
- degrade_plan: 按 Motion Control degrade_only 拆成低幅步行、肩颈/水桶/手部/水面/反应镜；不跨后端，不做连续高速运动。

### Clip_10 — general_motion
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: seedance
- mode: image2video
- quality_tier: high
- motion_reference: 用前序已通过 clip 作运动/风格参考(reference_video_motion)
- identity: reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_10/motion_control_manifest.json)
- motion_control_required_inputs: depth_sequence, camera_path, spatial_path, parallax_layers
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=出视频/第1集/control/Clip_10/motion_control_manifest.json
- action_choreography: none (carrying-water montage; controlled by Motion Control degrade_only manifest, not road_vehicle)
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - walking/carrying-water montage should stay low-amplitude and readable; put fatigue into shoulders, bucket sway, water surface, and restrained camera movement
  - 接力镜：primary「seedance」无首尾硬约束能力——本批次不切外部后端；失败先按 degrade_only 拆镜或同后端重试，外部后端需重新 record-refresh + video_preflight。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
  - seedance 支持视频片段参考（reference_video_motion）：把同段前一条已通过的 clip 作运动/风格参考喂进去，锁运镜节奏与运动风格（与图身份锁正交的跨镜运动连续性轴）。
- prompt_requirements:
  - keep body pose stable; put speed into background, foreground occluders, cloth and camera tracking
  - avoid large limb changes unless there is an end frame
  - follow Motion Control degrade_only manifest; do not invent vehicle/road/lane/wheel constraints
  - same-backend retry only; no Kling/Veo fallback without new evidence refresh and preflight
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 若有同段前序已通过 clip：把它作为视频运动/风格参考(reference_video_motion)喂给后端，锁运镜节奏；首条镜无前序参考则跳过。
- degrade_plan: 按 Motion Control degrade_only 拆成低幅步行、肩颈/水桶/手部/水面/反应镜；不跨后端，不做连续高速运动。

### Clip_11 — general_motion
- characters: CHAR_HE_PINGSHENG
- primary: seedance
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
  - 接力镜：primary「seedance」无首尾硬约束能力——本批次不切外部后端；失败先按 degrade_only 拆镜或同后端重试，外部后端需重新 record-refresh + video_preflight。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=fast：通用/低身份风险镜走量产快档省成本（落档侧解析为后端 fast model_version）。
- prompt_requirements:
  - keep character/camera/dynamic detail three-part prompt explicit
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: If action or identity fails twice, reroute to the nearest specialized shot type.

### Clip_12 — general_motion
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: seedance
- mode: image2video
- quality_tier: fast
- identity: reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=False)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - general motion can use the project default backend for cost and speed
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=fast：通用/低身份风险镜走量产快档省成本（落档侧解析为后端 fast model_version）。
- prompt_requirements:
  - keep character/camera/dynamic detail three-part prompt explicit
- degrade_plan: If action or identity fails twice, reroute to the nearest specialized shot type.

