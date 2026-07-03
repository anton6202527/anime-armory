# 视频模型路由

- episode: 第1集
- routing_mode: auto
- production_mode: 原生音画 (av_mode=native_av)
- default_backend: seedance
- generated_at: 2026-06-30T16:46:06+00:00

## 本集模型路由表

| Clip | characters | shot_type | primary | fallback | mode | 档 | 帧消费 | native_audio | identity | motion_control | policy | 风险 | 降级 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Clip_01 | CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CROWD_ZAYI | ensemble_blocking | veo | seedance | native_av | n/a | first_last | native_speech | character_id_or_reference_group | required | native_voice_fallback | identity_drift_risk, mouth_visible, multi_person, native_speech, seam_relay, spectacle_prior_routed | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_02 | CHAR_ZHANG_LAODA, CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | veo | native_av | high | first_last | native_speech | character_id_or_reference_group | none | native_voice_fallback | mouth_visible, multishot_candidate, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_03 | CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA | dialogue_shot_reverse | seedance | veo | native_av | high | first_last | native_speech | character_id_or_reference_group | none | native_voice_fallback | mouth_visible, multishot_candidate, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_04 | CHAR_ZHANG_LAODA, CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | veo | native_av | high | first_last | native_speech | character_id_or_reference_group | none | native_voice_fallback | mouth_visible, multishot_candidate, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_05 | CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA | dialogue_shot_reverse | seedance | veo | native_av | high | first_last | native_speech | character_id_or_reference_group | none | native_voice_fallback | mouth_visible, multishot_candidate, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_06 | CHAR_HE_PINGSHENG, CROWD_ZAYI | ensemble_blocking | kling | seedance, dreamina, veo | frames2video | n/a | first_last | none | character_id_or_reference_group | required | motion_control_required | identity_drift_risk, multi_person, multishot_candidate, seam_relay | Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways. |
| Clip_07 | CHAR_HE_PINGSHENG | talent_test | kling | seedance, dreamina, veo | image2video | n/a | first_last | none | reference_group | none | cost_quality_tier | identity_drift_risk, multishot_candidate, object_continuity_risk, readability_hold_required, seam_relay, text_overlay_required | Use static product/test-result keyframe plus flame/light overlay; cut to hand/detail/reaction if the object morphs or the process stage jumps. |
| Clip_08 | CHAR_HE_PINGSHENG, CHAR_TAIXUMEN_ZHANGLAO | reveal_reaction_chain | kling | veo, seedance, dreamina | image2video | n/a | first_last | none | character_id_or_reference_group | none | native_voice_fallback | identity_drift_risk, mouth_visible, seam_relay | Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.；若本镜含对白/画内发声，必须走 voice-first 配音补偿链路，或拆出 native_speech 说话特写后重跑路由。 |
| Clip_09 | CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA | dialogue_shot_reverse | seedance | veo | native_av | high | first_last | native_speech | character_id_or_reference_group | none | native_voice_fallback | mouth_visible, multi_person, multishot_candidate, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_10 | CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA | dialogue_shot_reverse | seedance | veo | native_av | high | first_last | native_speech | character_id_or_reference_group | none | native_voice_fallback | mouth_visible, multishot_candidate, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_11 | CHAR_HE_PINGSHENG | reveal_reaction_chain | kling | veo, seedance, dreamina | image2video | n/a | first_last | none | character_id_or_reference_group | none | native_voice_fallback | identity_drift_risk, mouth_visible, seam_relay | Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.；若本镜含对白/画内发声，必须走 voice-first 配音补偿链路，或拆出 native_speech 说话特写后重跑路由。 |
| Clip_12 | CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN | multi_character_same_frame | seedance | veo | native_av | high | first_last | native_speech | character_id_or_reference_group | required | native_voice_fallback | identity_drift_risk, mouth_visible, multi_person, multishot_candidate, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_13 | CHAR_HE_PINGSHENG | flight | seedance | veo | native_av | high | first_last | native_speech | character_id_or_reference_group | required | native_voice_fallback | action_choreography_required, high_speed_motion, identity_drift_risk, motion_reference_candidate, mouth_visible, multishot_candidate, native_speech, pose_drift_risk, seam_relay, spatial_path_risk | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_14 | CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN | multi_character_same_frame | kling | seedance, dreamina, veo | frames2video | n/a | first_last | none | character_id_or_reference_group | required | motion_control_required | identity_drift_risk, multi_person, multishot_candidate, seam_relay | If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip. |
| Clip_15 | CHAR_HE_PINGSHENG | multi_character_same_frame | kling | seedance, dreamina, veo | frames2video | n/a | first_last | none | character_id_or_reference_group | required | motion_control_required | identity_drift_risk, multi_person, multishot_candidate, seam_relay | If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip. |
| Clip_16 | CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN | multi_character_same_frame | kling | seedance, dreamina, veo | frames2video | n/a | first_last | none | character_id_or_reference_group | required | motion_control_required | identity_drift_risk, multi_person, seam_relay | If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip. |
| Clip_17 | CHAR_HE_PINGSHENG | general_motion | seedance | kling, dreamina, veo | image2video | fast | first_last | none | reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | If action or identity fails twice, reroute to the nearest specialized shot type. |
| Clip_18 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | veo | native_av | high | first_last | native_speech | character_id_or_reference_group | none | native_voice_fallback | mouth_visible, multishot_candidate, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_19 | CHAR_HE_PINGSHENG | multi_character_same_frame | kling | seedance, dreamina, veo | frames2video | n/a | first_last | none | character_id_or_reference_group | required | motion_control_required | identity_drift_risk, multi_person, seam_relay | If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip. |
| Clip_20 | CHAR_HE_PINGSHENG | general_motion | seedance | kling, dreamina, veo | image2video | fast | first_last | none | reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | If action or identity fails twice, reroute to the nearest specialized shot type. |
| Clip_21 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | veo | native_av | high | first_last | native_speech | character_id_or_reference_group | none | native_voice_fallback | mouth_visible, multishot_candidate, native_speech, seam_relay | 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。 |
| Clip_22 | - | general_motion | seedance | kling, dreamina, veo | image2video | fast | first_last | none | reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | If action or identity fails twice, reroute to the nearest specialized shot type. |
| Clip_23 | CHAR_HE_PINGSHENG | general_motion | seedance | kling, dreamina, veo | image2video | fast | first_last | none | reference_group | none | cost_quality_tier | seam_relay | If action or identity fails twice, reroute to the nearest specialized shot type. |
| Clip_24 | CHAR_HE_PINGSHENG | multi_character_same_frame | kling | seedance, dreamina, veo | frames2video | n/a | first_last | none | character_id_or_reference_group | required | motion_control_required | identity_drift_risk, multi_person, seam_relay | If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip. |
| Clip_25 | CHAR_HE_PINGSHENG | general_motion | seedance | dreamina | image2video | fast | native_multiframe | none | reference_group | none | cost_quality_tier | native_multiframe | If action or identity fails twice, reroute to the nearest specialized shot type. |

## 多镜单次生成候选组（advisory·可选一次 co-generate 消缝）

- MSG_01（seedance）: Clip_02, Clip_03, Clip_04, Clip_05 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_02（kling）: Clip_06, Clip_07 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_03（seedance）: Clip_09, Clip_10 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_04（seedance）: Clip_12, Clip_13 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_05（kling）: Clip_14, Clip_15 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_06（seedance）: Clip_17, Clip_18 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_07（seedance）: Clip_20, Clip_21, Clip_22 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。

## 逐 Clip 路由理由

### Clip_01 — ensemble_blocking
- characters: CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA, CROWD_ZAYI
- primary: veo
- fallback: seedance
- mode: native_av
- quality_tier: n/a
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=veo, anchors=0, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_01/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=veo; frames=first_last anchors=0; refs_max=3; control_manifest=出视频/第1集/control/Clip_01/motion_control_manifest.json
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict backend_choice: spectacle_prior, cost_quality_tier -> spectacle_prior
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 可灵O3/即梦多帧等首尾帧后端 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
  - spectacle cold-start prior: large_establishing 默认排序首选 veo（large_establishing 吃运镜语言与尺度: Veo cinematography 强, Seedance 转场次之）；通用兜底 seedance 改为 prior 首选，原后端保留为 fallback。跑 probe 后由 benchmark 覆盖。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_02 — dialogue_shot_reverse
- characters: CHAR_ZHANG_LAODA, CHAR_HE_PINGSHENG
- primary: seedance
- fallback: veo
- mode: native_av
- quality_tier: high
- multishot_candidate: MSG_01 ['Clip_02', 'Clip_03', 'Clip_04', 'Clip_05']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 可灵O3/即梦多帧等首尾帧后端 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_03 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA
- primary: seedance
- fallback: veo
- mode: native_av
- quality_tier: high
- multishot_candidate: MSG_01 ['Clip_02', 'Clip_03', 'Clip_04', 'Clip_05']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 可灵O3/即梦多帧等首尾帧后端 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_04 — dialogue_shot_reverse
- characters: CHAR_ZHANG_LAODA, CHAR_HE_PINGSHENG
- primary: seedance
- fallback: veo
- mode: native_av
- quality_tier: high
- multishot_candidate: MSG_01 ['Clip_02', 'Clip_03', 'Clip_04', 'Clip_05']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 可灵O3/即梦多帧等首尾帧后端 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_05 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA
- primary: seedance
- fallback: veo
- mode: native_av
- quality_tier: high
- multishot_candidate: MSG_01 ['Clip_02', 'Clip_03', 'Clip_04', 'Clip_05']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 可灵O3/即梦多帧等首尾帧后端 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - motion_spectacle_guidance：按本字段把风格自适应视觉盛宴落进运动描述（体积光/速度线随风格族变体·勿给赛璐璐/水墨硬塞写实 motion blur）
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_06 — ensemble_blocking
- characters: CHAR_HE_PINGSHENG, CROWD_ZAYI
- primary: kling
- fallback: seedance, dreamina, veo
- mode: frames2video
- quality_tier: n/a
- multishot_candidate: MSG_02 ['Clip_06', 'Clip_07']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=kling, anchors=0, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_06/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=kling; frames=first_last anchors=0; refs_max=0; control_manifest=出视频/第1集/control/Clip_06/motion_control_manifest.json
- policy_resolution: winner=motion_control_required signoff_required=False
- rationale:
  - multi-person staging needs reference controls and stable screen direction
  - single-backend generic generation often swaps faces or screen positions
  - 5+ 同框/群像：Sora 已从自动路由移除；Kling 负责槽位/主体约束，仍不稳按 degrade_plan 拆组，不要把 5+ 清晰正脸压在同一镜。
  - 接力镜：primary「kling」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
- prompt_requirements:
  - write screen positions and focus hierarchy; background crowd must be silhouette, back view, or soft focus
  - one speaking/action focus per clip; do not ask every crowd member to have a clear face
  - bind each named registered character id to its own screen slot (LEFT/RIGHT/FOREGROUND/BACKGROUND) AND its own subject/reference anchor — regional/mask binding per subject; never feed one shared reference for the whole frame (single shared ref makes the model average faces)
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: Split the ensemble into establishing shot, two-character OTS pair, and crowd reaction cutaways.

### Clip_07 — talent_test
- characters: CHAR_HE_PINGSHENG
- primary: kling
- fallback: seedance, dreamina, veo
- mode: image2video
- quality_tier: n/a
- multishot_candidate: MSG_02 ['Clip_06', 'Clip_07']
- identity: reference_group
- frame_consumption: first_last (execution=kling, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=kling; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - craft/test shots are object-readability sensitive: the furnace, artifact, material sequence, and result must not morph
  - first-frame preservation plus low-to-medium process motion keeps product/talent result legible
  - 接力镜：primary「kling」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
- prompt_requirements:
  - lock furnace_or_forge/test_artifact, material/result sequence, process_stage_ladder, heat_curve, material_state_ladder, hand pose, flame/light color, and product/result state
  - use overlay_policy for numbers, rankings, talent names, attribute text, or panel-like readouts
  - one result reveal per clip; split preparation, process stage, state transformation, and result if needed
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: Use static product/test-result keyframe plus flame/light overlay; cut to hand/detail/reaction if the object morphs or the process stage jumps.

### Clip_08 — reveal_reaction_chain
- characters: CHAR_HE_PINGSHENG, CHAR_TAIXUMEN_ZHANGLAO
- primary: kling
- fallback: veo, seedance, dreamina
- mode: image2video
- quality_tier: n/a
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=kling, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=kling; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - reveal scenes are identity- and reaction-chain-sensitive
  - these shots carry irreversible story state changes, so visual identity, eyeline, and reaction order outrank generic speech routing
  - 制作模式=原生音画，但本专项模板优先锁身份/表情/反应链；若必须原生人声，拆成说话特写或手动改用 native AV fallback。
  - 本镜未声明 native_speech 时必须补 voice-first 配音轨；不能让原生音画项目出现无声对白/反应链。
  - 接力镜：primary「kling」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
- prompt_requirements:
  - mark mouth_visible when faces speak; speech_policy=no_native_speech unless this clip is explicitly rerouted to a native AV backend
  - lock reveal_object, knowledge_order, reaction_beats, and cut_point from template_contract
  - native_av_project_note=visual_consistency_first_for_narrative_state_scene
  - requires_voice_fallback=true；若本镜有台词/画内说话，先补 n2d-voice，再以 no_native_speech 出视频
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.；若本镜含对白/画内发声，必须走 voice-first 配音补偿链路，或拆出 native_speech 说话特写后重跑路由。

### Clip_09 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA
- primary: seedance
- fallback: veo
- mode: native_av
- quality_tier: high
- multishot_candidate: MSG_03 ['Clip_09', 'Clip_10']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 可灵O3/即梦多帧等首尾帧后端 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_10 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA
- primary: seedance
- fallback: veo
- mode: native_av
- quality_tier: high
- multishot_candidate: MSG_03 ['Clip_09', 'Clip_10']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 可灵O3/即梦多帧等首尾帧后端 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_11 — reveal_reaction_chain
- characters: CHAR_HE_PINGSHENG
- primary: kling
- fallback: veo, seedance, dreamina
- mode: image2video
- quality_tier: n/a
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=kling, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=kling; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - reveal scenes are identity- and reaction-chain-sensitive
  - these shots carry irreversible story state changes, so visual identity, eyeline, and reaction order outrank generic speech routing
  - 制作模式=原生音画，但本专项模板优先锁身份/表情/反应链；若必须原生人声，拆成说话特写或手动改用 native AV fallback。
  - 本镜未声明 native_speech 时必须补 voice-first 配音轨；不能让原生音画项目出现无声对白/反应链。
  - 接力镜：primary「kling」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
- prompt_requirements:
  - mark mouth_visible when faces speak; speech_policy=no_native_speech unless this clip is explicitly rerouted to a native AV backend
  - lock reveal_object, knowledge_order, reaction_beats, and cut_point from template_contract
  - native_av_project_note=visual_consistency_first_for_narrative_state_scene
  - requires_voice_fallback=true；若本镜有台词/画内说话，先补 n2d-voice，再以 no_native_speech 出视频
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.；若本镜含对白/画内发声，必须走 voice-first 配音补偿链路，或拆出 native_speech 说话特写后重跑路由。

### Clip_12 — multi_character_same_frame
- characters: CHAR_HE_PINGSHENG, CHAR_JIANG_JIAN
- primary: seedance
- fallback: veo
- mode: native_av
- quality_tier: high
- multishot_candidate: MSG_04 ['Clip_12', 'Clip_13']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_12/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=出视频/第1集/control/Clip_12/motion_control_manifest.json
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 可灵O3/即梦多帧等首尾帧后端 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - motion_spectacle_guidance：按本字段把风格自适应视觉盛宴落进运动描述（体积光/速度线随风格族变体·勿给赛璐璐/水墨硬塞写实 motion blur）
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_13 — flight
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: veo
- mode: native_av
- quality_tier: high
- motion_reference: 用前序已通过 clip 作运动/风格参考(reference_video_motion)
- multishot_candidate: MSG_04 ['Clip_12', 'Clip_13']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_13/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, camera_path, spatial_path, parallax_layers
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=出视频/第1集/control/Clip_13/motion_control_manifest.json
- action_choreography: takeoff_cruise_maneuver_arrival (gate=block_prompt_without_action_choreography_contract)
- action_choreography_required_fields: beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, flight_path, altitude_curve, pose_lock, parallax_layers, mount_or_cloud_lock
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 可灵O3/即梦多帧等首尾帧后端 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
  - seedance 支持视频片段参考（reference_video_motion）：把同段前一条已通过的 clip 作运动/风格参考喂进去，锁运镜节奏与运动风格（与图身份锁正交的跨镜运动连续性轴）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 必须在单 Clip prompt 写 Action Choreography/动作编排契约，并逐项覆盖 beats, speed_curve, spatial_path, camera_path, readability_beats, degrade_plan, keyframe_plan, post_cue_points, physics_guard, flight_path, altitude_curve, pose_lock, parallax_layers, mount_or_cloud_lock；缺字段先回 n2d-script/n2d-video 补，不进入付费出视频。
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - 若有同段前序已通过 clip：把它作为视频运动/风格参考(reference_video_motion)喂给后端，锁运镜节奏；首条镜无前序参考则跳过。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_14 — multi_character_same_frame
- characters: CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN
- primary: kling
- fallback: seedance, dreamina, veo
- mode: frames2video
- quality_tier: n/a
- multishot_candidate: MSG_05 ['Clip_14', 'Clip_15']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=kling, anchors=0, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_14/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=kling; frames=first_last anchors=0; refs_max=0; control_manifest=出视频/第1集/control/Clip_14/motion_control_manifest.json
- policy_resolution: winner=motion_control_required signoff_required=False
- rationale:
  - multi-person staging needs reference controls and stable screen direction
  - single-backend generic generation often swaps faces or screen positions
  - 接力镜：primary「kling」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
- prompt_requirements:
  - freeze character slots, left/right positions, and face priority
  - keep two to three named faces maximum; lower-priority faces may be side/back/soft focus
  - bind each named registered character id to its own screen slot (LEFT/RIGHT/FOREGROUND/BACKGROUND) AND its own subject/reference anchor — regional/mask binding per subject; never feed one shared reference for the whole frame (single shared ref makes the model average faces)
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.

### Clip_15 — multi_character_same_frame
- characters: CHAR_HE_PINGSHENG
- primary: kling
- fallback: seedance, dreamina, veo
- mode: frames2video
- quality_tier: n/a
- multishot_candidate: MSG_05 ['Clip_14', 'Clip_15']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=kling, anchors=0, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_15/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=kling; frames=first_last anchors=0; refs_max=0; control_manifest=出视频/第1集/control/Clip_15/motion_control_manifest.json
- policy_resolution: winner=motion_control_required signoff_required=False
- rationale:
  - multi-person staging needs reference controls and stable screen direction
  - single-backend generic generation often swaps faces or screen positions
  - 接力镜：primary「kling」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
- prompt_requirements:
  - freeze character slots, left/right positions, and face priority
  - keep two to three named faces maximum; lower-priority faces may be side/back/soft focus
  - bind each named registered character id to its own screen slot (LEFT/RIGHT/FOREGROUND/BACKGROUND) AND its own subject/reference anchor — regional/mask binding per subject; never feed one shared reference for the whole frame (single shared ref makes the model average faces)
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.

### Clip_16 — multi_character_same_frame
- characters: CHAR_HE_PINGSHENG, CHAR_HAN_LAOSAN
- primary: kling
- fallback: seedance, dreamina, veo
- mode: frames2video
- quality_tier: n/a
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=kling, anchors=0, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_16/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=kling; frames=first_last anchors=0; refs_max=0; control_manifest=出视频/第1集/control/Clip_16/motion_control_manifest.json
- policy_resolution: winner=motion_control_required signoff_required=False
- rationale:
  - multi-person staging needs reference controls and stable screen direction
  - single-backend generic generation often swaps faces or screen positions
  - 接力镜：primary「kling」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
- prompt_requirements:
  - freeze character slots, left/right positions, and face priority
  - keep two to three named faces maximum; lower-priority faces may be side/back/soft focus
  - bind each named registered character id to its own screen slot (LEFT/RIGHT/FOREGROUND/BACKGROUND) AND its own subject/reference anchor — regional/mask binding per subject; never feed one shared reference for the whole frame (single shared ref makes the model average faces)
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
  - motion_spectacle_guidance：按本字段把风格自适应视觉盛宴落进运动描述（体积光/速度线随风格族变体·勿给赛璐璐/水墨硬塞写实 motion blur）
- degrade_plan: If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.

### Clip_17 — general_motion
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: kling, dreamina, veo
- mode: image2video
- quality_tier: fast
- multishot_candidate: MSG_06 ['Clip_17', 'Clip_18']
- identity: reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - general motion can use the project default backend for cost and speed
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 kling 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 质量档=fast：通用/低身份风险镜走量产快档省成本（落档侧解析为后端 fast model_version）。
- prompt_requirements:
  - keep character/camera/dynamic detail three-part prompt explicit
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: If action or identity fails twice, reroute to the nearest specialized shot type.

### Clip_18 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: veo
- mode: native_av
- quality_tier: high
- multishot_candidate: MSG_06 ['Clip_17', 'Clip_18']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 可灵O3/即梦多帧等首尾帧后端 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_19 — multi_character_same_frame
- characters: CHAR_HE_PINGSHENG
- primary: kling
- fallback: seedance, dreamina, veo
- mode: frames2video
- quality_tier: n/a
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=kling, anchors=0, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_19/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=kling; frames=first_last anchors=0; refs_max=0; control_manifest=出视频/第1集/control/Clip_19/motion_control_manifest.json
- policy_resolution: winner=motion_control_required signoff_required=False
- rationale:
  - multi-person staging needs reference controls and stable screen direction
  - single-backend generic generation often swaps faces or screen positions
  - 接力镜：primary「kling」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
- prompt_requirements:
  - freeze character slots, left/right positions, and face priority
  - keep two to three named faces maximum; lower-priority faces may be side/back/soft focus
  - bind each named registered character id to its own screen slot (LEFT/RIGHT/FOREGROUND/BACKGROUND) AND its own subject/reference anchor — regional/mask binding per subject; never feed one shared reference for the whole frame (single shared ref makes the model average faces)
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.

### Clip_20 — general_motion
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: kling, dreamina, veo
- mode: image2video
- quality_tier: fast
- multishot_candidate: MSG_07 ['Clip_20', 'Clip_21', 'Clip_22']
- identity: reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - general motion can use the project default backend for cost and speed
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 kling 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 质量档=fast：通用/低身份风险镜走量产快档省成本（落档侧解析为后端 fast model_version）。
- prompt_requirements:
  - keep character/camera/dynamic detail three-part prompt explicit
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: If action or identity fails twice, reroute to the nearest specialized shot type.

### Clip_21 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: veo
- mode: native_av
- quality_tier: high
- multishot_candidate: MSG_07 ['Clip_20', 'Clip_21', 'Clip_22']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=native_voice_fallback signoff_required=False
  - conflict voice_identity: native_voice_fallback, cost_quality_tier -> native_voice_fallback
- rationale:
  - 制作模式=原生音画：让原生同步音画后端一次生成台词+口型+环境声，规避「配音→对口型」代差与占位返工
  - 台词文本/情绪/单镜时长来自脚本，不读配音先行的时长清单；本镜不再走 n2d-voice 逐句配音
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 可灵O3/即梦多帧等首尾帧后端 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 提供本镜台词文本 + 情绪 + 时长，要求后端做唇音同步的原生人声
  - speech_policy=native_speech；声音须为合成音色，真人音色克隆仍需授权（见 compliance）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 原生口型/音画质量不达标 → 本镜回退配音先行：改 image2video + 静音生成，交 n2d-voice 配音 + 可选对口型。

### Clip_22 — general_motion
- primary: seedance
- fallback: kling, dreamina, veo
- mode: image2video
- quality_tier: fast
- multishot_candidate: MSG_07 ['Clip_20', 'Clip_21', 'Clip_22']
- identity: reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - general motion can use the project default backend for cost and speed
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 kling 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 质量档=fast：通用/低身份风险镜走量产快档省成本（落档侧解析为后端 fast model_version）。
- prompt_requirements:
  - keep character/camera/dynamic detail three-part prompt explicit
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: If action or identity fails twice, reroute to the nearest specialized shot type.

### Clip_23 — general_motion
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: kling, dreamina, veo
- mode: image2video
- quality_tier: fast
- identity: reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - general motion can use the project default backend for cost and speed
  - 接力镜：primary「seedance」无首尾硬约束能力——优先改用 kling 把尾帧作硬约束插值，接缝才结构保证，否则尾帧靠自由外推易漂。
  - 质量档=fast：通用/低身份风险镜走量产快档省成本（落档侧解析为后端 fast model_version）。
- prompt_requirements:
  - keep character/camera/dynamic detail three-part prompt explicit
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: If action or identity fails twice, reroute to the nearest specialized shot type.

### Clip_24 — multi_character_same_frame
- characters: CHAR_HE_PINGSHENG
- primary: kling
- fallback: seedance, dreamina, veo
- mode: frames2video
- quality_tier: n/a
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=kling, anchors=0, need_end=True)
- motion_control: required (manifest=出视频/第1集/control/Clip_24/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=kling; frames=first_last anchors=0; refs_max=0; control_manifest=出视频/第1集/control/Clip_24/motion_control_manifest.json
- policy_resolution: winner=motion_control_required signoff_required=False
- rationale:
  - multi-person staging needs reference controls and stable screen direction
  - single-backend generic generation often swaps faces or screen positions
  - 接力镜：primary「kling」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
- prompt_requirements:
  - freeze character slots, left/right positions, and face priority
  - keep two to three named faces maximum; lower-priority faces may be side/back/soft focus
  - bind each named registered character id to its own screen slot (LEFT/RIGHT/FOREGROUND/BACKGROUND) AND its own subject/reference anchor — regional/mask binding per subject; never feed one shared reference for the whole frame (single shared ref makes the model average faces)
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: If faces swap or slots drift, split into two-shot, OTS, and reaction inserts; keep one face-priority target per clip.

### Clip_25 — general_motion
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
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

