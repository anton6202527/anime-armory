# 视频模型路由

- episode: 第2集
- routing_mode: auto
- production_mode: 先出视频后配音 (av_mode=voice_first)
- default_backend: seedance
- generated_at: 2026-07-03T14:58:31+00:00

## 本集模型路由表

| Clip | characters | shot_type | primary | fallback | mode | 档 | 帧消费 | native_audio | identity | motion_control | policy | 风险 | 降级 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Clip_01 | - | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_02 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_03 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_04 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_05 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_06 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_07 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_08 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_09 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_10 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_11 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_12 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_13 | CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA | dialogue_shot_reverse | veo | seedance, dreamina | voice_conditioned_lipsync | n/a | first_last | lipsync_condition_only | character_id_or_reference_group | none | spectacle_prior | seam_relay, spectacle_prior_routed | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_14 | CHAR_ZHANG_LAODA, CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_15 | CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_16 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_17 | CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_18 | CHAR_ZHANG_LAODA, CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_19 | CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_20 | CHAR_ZHANG_LAODA, CHAR_HE_PINGSHENG | reveal_reaction_chain | seedance | dreamina | image2video | high | first_last | none | character_id_or_reference_group | none | cost_quality_tier | identity_drift_risk, multishot_candidate, seam_relay | Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift. |
| Clip_21 | CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_22 | CHAR_ZHANG_LAODA, CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_23 | CHAR_ZHANG_LAODA, CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_24 | CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_25 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | multishot_candidate, seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_26 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_last | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | seam_relay | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |
| Clip_27 | CHAR_HE_PINGSHENG | dialogue_shot_reverse | seedance | dreamina | voice_conditioned_lipsync | high | first_frame | lipsync_condition_only | character_id_or_reference_group | none | cost_quality_tier | - | 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。 |

## 多镜单次生成候选组（advisory·可选一次 co-generate 消缝）

- MSG_01（seedance）: Clip_01, Clip_02, Clip_03 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_02（seedance）: Clip_04, Clip_05 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_03（seedance）: Clip_06, Clip_07, Clip_08 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_04（seedance）: Clip_09, Clip_10 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_05（seedance）: Clip_11, Clip_12 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_06（seedance）: Clip_14, Clip_15 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_07（seedance）: Clip_16, Clip_17 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_08（seedance）: Clip_18, Clip_19 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_09（seedance）: Clip_20, Clip_21, Clip_22 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。
- MSG_10（seedance）: Clip_23, Clip_24, Clip_25 — 连续接力镜，可一次出多镜消缝；权衡=牺牲逐镜独立重跑粒度，按接缝风险与重跑需求决定。

## 逐 Clip 路由理由

### Clip_01 — dialogue_shot_reverse
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_01 ['Clip_01', 'Clip_02', 'Clip_03']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_02 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_01 ['Clip_01', 'Clip_02', 'Clip_03']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_03 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_01 ['Clip_01', 'Clip_02', 'Clip_03']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_04 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_02 ['Clip_04', 'Clip_05']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_05 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_02 ['Clip_04', 'Clip_05']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_06 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_03 ['Clip_06', 'Clip_07', 'Clip_08']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_07 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_03 ['Clip_06', 'Clip_07', 'Clip_08']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_08 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_03 ['Clip_06', 'Clip_07', 'Clip_08']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_09 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_04 ['Clip_09', 'Clip_10']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_10 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_04 ['Clip_09', 'Clip_10']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_11 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_05 ['Clip_11', 'Clip_12']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_12 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_05 ['Clip_11', 'Clip_12']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_13 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA
- primary: veo
- fallback: seedance, dreamina
- mode: voice_conditioned_lipsync
- quality_tier: n/a
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=veo, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=veo; frames=first_last anchors=0; refs_max=3; control_manifest=-
- policy_resolution: winner=spectacle_prior signoff_required=False
  - conflict backend_choice: spectacle_prior, cost_quality_tier -> spectacle_prior
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
  - spectacle cold-start prior: large_establishing 默认排序首选 veo（large_establishing 吃运镜语言与尺度: Veo cinematography 强, Seedance 转场次之）；通用兜底 seedance 改为 prior 首选，原后端保留为 fallback。跑 probe 后由 benchmark 覆盖。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_14 — dialogue_shot_reverse
- characters: CHAR_ZHANG_LAODA, CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_06 ['Clip_14', 'Clip_15']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_15 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_06 ['Clip_14', 'Clip_15']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_16 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_07 ['Clip_16', 'Clip_17']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_17 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_07 ['Clip_16', 'Clip_17']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_18 — dialogue_shot_reverse
- characters: CHAR_ZHANG_LAODA, CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_08 ['Clip_18', 'Clip_19']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_19 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_08 ['Clip_18', 'Clip_19']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_20 — reveal_reaction_chain
- characters: CHAR_ZHANG_LAODA, CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: image2video
- quality_tier: high
- multishot_candidate: MSG_09 ['Clip_20', 'Clip_21', 'Clip_22']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - reveal scenes are identity- and reaction-chain-sensitive
  - these shots carry irreversible story state changes, so visual identity, eyeline, and reaction order outrank generic speech routing
  - 执行渠道「即梦/Dreamina」下改用可执行后端「seedance」；原 primary「kling」当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - mark mouth_visible when faces speak; speech_policy=no_native_speech unless this clip is explicitly rerouted to a native AV backend
  - lock reveal_object, knowledge_order, reaction_beats, and cut_point from template_contract
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.

### Clip_21 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_09 ['Clip_20', 'Clip_21', 'Clip_22']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_22 — dialogue_shot_reverse
- characters: CHAR_ZHANG_LAODA, CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_09 ['Clip_20', 'Clip_21', 'Clip_22']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_23 — dialogue_shot_reverse
- characters: CHAR_ZHANG_LAODA, CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_10 ['Clip_23', 'Clip_24', 'Clip_25']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_24 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_10 ['Clip_23', 'Clip_24', 'Clip_25']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_25 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- multishot_candidate: MSG_10 ['Clip_23', 'Clip_24', 'Clip_25']
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_26 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: first_last (execution=dreamina, anchors=0, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_last anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 接力镜：primary「seedance」支持双关键帧——把上一镜尾帧作本镜首帧硬约束(首尾插值)，接缝结构保证。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
  - 接力：上一镜尾帧 PNG = 本镜首帧硬约束(dual-keyframe)，边界帧只授权一次、两镜复用（省一次出图）。
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

### Clip_27 — dialogue_shot_reverse
- characters: CHAR_HE_PINGSHENG
- primary: seedance
- fallback: dreamina
- mode: voice_conditioned_lipsync
- quality_tier: high
- identity: character_id_or_reference_group
- frame_consumption: first_frame (execution=dreamina, anchors=0, need_end=False)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_frame anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - voice_first + 对口型 opt-in：把克隆配音 line_NN.wav 当口型条件喂进支持音频参考的后端，同帧出对口型画面
  - 音轨仍是 voice-first 克隆音色，模型音频仅作口型条件不接管声音——避免双人声，且省一道后期 MuseTalk/Wav2Lip pass
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - 把本镜配音 line_NN.wav 作为音频参考/口型驱动输入喂给后端；不要让后端另生成台词或环境人声
  - speech_policy=no_native_speech（声音由 voice-first 克隆轨提供，模型音频仅口型条件，compose 用配音轨）
- degrade_plan: 后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。

