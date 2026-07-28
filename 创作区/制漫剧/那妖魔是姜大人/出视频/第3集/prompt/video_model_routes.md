# 视频模型路由

- episode: 第3集
- routing_mode: auto
- production_mode: 混合自动路由 (av_mode=hybrid)
- default_backend: seedance
- execution_adapter_v2: {'automated_ready': 8}
- generated_at: 2026-07-28T02:21:24+00:00

## 本集模型路由表

| Clip | characters | shot_type | primary | fallback | mode | 时间基准 | 声音策略 | 表演轨 | 档 | 帧消费 | native_audio | identity | motion_control | policy | 风险 | 降级 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Clip_01 | CHAR_01/镇魔司制服态, CHAR_03/风尘劲装态, GROUP_01/齐跪态 | ensemble_blocking | seedance | dreamina | image2video | text_estimate_no_audio | base_video_then_post_lipsync | missing | high | native_multiframe | none | native_identity_lock_required | required | identity_affinity | base_video_only, identity_drift_risk, identity_escalated, multi_person, native_multiframe, post_lipsync_required | 先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。 |
| Clip_02 | CHAR_01/囚服残损态 | general_motion | seedance | dreamina | image2video | text_estimate_no_audio | base_video_then_post_lipsync | missing | high | first_frame | none | native_identity_lock_required | none | identity_affinity | base_video_only, identity_escalated, post_lipsync_required | 先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。 |
| Clip_03 | CHAR_01/囚服转制服态 | dialogue_shot_reverse | seedance | dreamina | image2video | text_estimate_no_audio | post_dub | missing | high | native_multiframe | none | native_identity_lock_required | none | identity_affinity | identity_escalated, mouth_visible, native_multiframe | Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails. |
| Clip_04 | CHAR_01/镇魔司制服态 | empty_establishing | seedance | dreamina | image2video | text_estimate_no_audio | post_dub | missing | fast | native_multiframe | none | reference_group | none | cost_quality_tier | duration_segment_relay, low_identity_risk, native_multiframe | Use Dreamina/Seedance silent clip and add SFX/BGM in compose. |
| Clip_05 | CHAR_01/镇魔司制服态, CHAR_03/风尘劲装态, GROUP_01/列队戒备态 | ensemble_blocking | seedance | dreamina | image2video | text_estimate_no_audio | base_video_then_post_lipsync | missing | high | native_multiframe | none | native_identity_lock_required | required | identity_affinity | base_video_only, identity_drift_risk, identity_escalated, multi_person, native_multiframe, post_lipsync_required | 先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。 |
| Clip_06 | CHAR_01/镇魔司制服态, CHAR_03/风尘劲装态, GROUP_01/列队戒备态 | dialogue_shot_reverse | seedance | dreamina | image2video | text_estimate_no_audio | base_video_then_post_lipsync | missing | high | native_multiframe | none | native_identity_lock_required | none | identity_affinity | base_video_only, duration_segment_relay, identity_escalated, mouth_visible, native_multiframe, post_lipsync_required | 先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。 |
| Clip_07 | CHAR_01/镇魔司制服态, CHAR_03/风尘劲装态, GROUP_01/齐跪态 | ensemble_blocking | seedance | dreamina | image2video | text_estimate_no_audio | base_video_then_post_lipsync | missing | high | native_multiframe | none | native_identity_lock_required | required | identity_affinity | base_video_only, identity_drift_risk, identity_escalated, mouth_visible, multi_person, native_multiframe, post_lipsync_required | 先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。 |
| Clip_08 | CHAR_01/镇魔司制服态, GROUP_01/齐跪态焦外 | ensemble_blocking | seedance | dreamina | image2video | text_estimate_no_audio | base_video_then_post_lipsync | missing | high | native_multiframe | none | native_identity_lock_required | required | identity_affinity | base_video_only, identity_drift_risk, identity_escalated, mouth_visible, multi_person, native_multiframe, post_lipsync_required | 先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。 |

## 逐 Clip 路由理由

### Clip_01 — ensemble_blocking
- characters: CHAR_01/镇魔司制服态, CHAR_03/风尘劲装态, GROUP_01/齐跪态
- primary: seedance
- fallback: dreamina
- mode: image2video
- sound: timing_basis=text_estimate_no_audio / audio_strategy=base_video_then_post_lipsync / performance_track=missing / voice_lock=pending
- final_sound: stage=post_lipsync_before_compose / post_lipsync_required=True / base_video_only=True
- quality_tier: high
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=False)
- motion_control: required (manifest=出视频/第3集/control/Clip_01/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=出视频/第3集/control/Clip_01/motion_control_manifest.json
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - multi-person staging needs reference controls and stable screen direction
  - single-backend generic generation often swaps faces or screen positions
  - 5+ 同框/群像：Sora 已从自动路由移除；Kling 负责槽位/主体约束，仍不稳按 degrade_plan 拆组，不要把 5+ 清晰正脸压在同一镜。
  - 混合路由：当前无已签收表演音轨，只生成中性嘴型的基础视频；音轨就绪后走独立后期表演/口型驱动。
  - 执行渠道「即梦/Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 10.52s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 4 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - write screen positions and focus hierarchy; background crowd must be silhouette, back view, or soft focus
  - one speaking/action focus per clip; do not ask every crowd member to have a clear face
  - bind each named registered character id to its own screen slot (LEFT/RIGHT/FOREGROUND/BACKGROUND) AND its own subject/reference anchor — regional/mask binding per subject; never feed one shared reference for the whole frame (single shared ref makes the model average faces)
  - base_video_only=true；嘴唇保持自然闭合/静息，不做可辨识发音动作，不让模型即兴说话；为后期表演驱动保留稳定正脸与表情空间。
- degrade_plan: 先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。

### Clip_02 — general_motion
- characters: CHAR_01/囚服残损态
- primary: seedance
- fallback: dreamina
- mode: image2video
- sound: timing_basis=text_estimate_no_audio / audio_strategy=base_video_then_post_lipsync / performance_track=missing / voice_lock=locked
- final_sound: stage=post_lipsync_before_compose / post_lipsync_required=True / base_video_only=True
- quality_tier: high
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- identity: native_identity_lock_required
- frame_consumption: first_frame (execution=dreamina, anchors=0, need_end=False)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=first_frame anchors=0; refs_max=0; control_manifest=-
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cross_episode_baseline, cost_quality_tier -> identity_affinity
- rationale:
  - general motion can use the project default backend for cost and speed
  - 混合路由：当前无已签收表演音轨，只生成中性嘴型的基础视频；音轨就绪后走独立后期表演/口型驱动。
  - ⚠️本镜 identity 已失败 2 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - keep character/camera/dynamic detail three-part prompt explicit
  - base_video_only=true；嘴唇保持自然闭合/静息，不做可辨识发音动作，不让模型即兴说话；为后期表演驱动保留稳定正脸与表情空间。
- degrade_plan: 先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。

### Clip_03 — dialogue_shot_reverse
- characters: CHAR_01/囚服转制服态
- primary: seedance
- fallback: dreamina
- mode: image2video
- sound: timing_basis=text_estimate_no_audio / audio_strategy=post_dub / performance_track=missing / voice_lock=locked
- final_sound: stage=post_video_before_compose / post_lipsync_required=False / base_video_only=False
- quality_tier: high
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cross_episode_baseline, cost_quality_tier -> identity_affinity
- rationale:
  - dialogue shots are identity-sensitive and often need lip-sync or strong reference controls
  - default n2d audio remains voiceover-first; do not let the video backend generate speech
  - 执行渠道「即梦/Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 11.755s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 5 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - mark mouth_visible and speech_policy=no_native_speech
  - prefer side/back/OTS if lip-sync is disabled
- degrade_plan: Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.

### Clip_04 — empty_establishing
- characters: CHAR_01/镇魔司制服态
- primary: seedance
- fallback: dreamina
- mode: image2video
- sound: timing_basis=text_estimate_no_audio / audio_strategy=post_dub / performance_track=missing / voice_lock=locked
- final_sound: stage=post_video_before_compose / post_lipsync_required=False / base_video_only=False
- quality_tier: fast
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- identity: reference_group
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=-
- policy_resolution: winner=cost_quality_tier signoff_required=False
- rationale:
  - empty/ambience shots have low identity risk and can use native ambience when opted in
  - text2video is acceptable when no character identity must be preserved
  - 本镜 15.383s 超过 seedance 单次上限 15s；执行侧必须按现有首/中/尾帧拆成 2 段 first_last_relay 付费提交，每段不超过上限，再在后续合成阶段接回。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - 质量档=fast：通用/低身份风险镜走量产快档省成本（落档侧解析为后端 fast model_version）。
- prompt_requirements:
  - confirm mouth_visible=no and speech_policy=no_native_speech
  - keep ambience sound low-risk; no voices, no narration, no humming
  - 长镜分段接力：不要单次提交整镜；按 duration_segment_relay.segments 用首帧→中段锚帧→尾帧分段生成。
- degrade_plan: Use Dreamina/Seedance silent clip and add SFX/BGM in compose.

### Clip_05 — ensemble_blocking
- characters: CHAR_01/镇魔司制服态, CHAR_03/风尘劲装态, GROUP_01/列队戒备态
- primary: seedance
- fallback: dreamina
- mode: image2video
- sound: timing_basis=text_estimate_no_audio / audio_strategy=base_video_then_post_lipsync / performance_track=missing / voice_lock=pending
- final_sound: stage=post_lipsync_before_compose / post_lipsync_required=True / base_video_only=True
- quality_tier: high
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=False)
- motion_control: required (manifest=出视频/第3集/control/Clip_05/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=出视频/第3集/control/Clip_05/motion_control_manifest.json
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - multi-person staging needs reference controls and stable screen direction
  - single-backend generic generation often swaps faces or screen positions
  - 5+ 同框/群像：Sora 已从自动路由移除；Kling 负责槽位/主体约束，仍不稳按 degrade_plan 拆组，不要把 5+ 清晰正脸压在同一镜。
  - 混合路由：当前无已签收表演音轨，只生成中性嘴型的基础视频；音轨就绪后走独立后期表演/口型驱动。
  - 执行渠道「即梦/Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 4 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - write screen positions and focus hierarchy; background crowd must be silhouette, back view, or soft focus
  - one speaking/action focus per clip; do not ask every crowd member to have a clear face
  - bind each named registered character id to its own screen slot (LEFT/RIGHT/FOREGROUND/BACKGROUND) AND its own subject/reference anchor — regional/mask binding per subject; never feed one shared reference for the whole frame (single shared ref makes the model average faces)
  - base_video_only=true；嘴唇保持自然闭合/静息，不做可辨识发音动作，不让模型即兴说话；为后期表演驱动保留稳定正脸与表情空间。
- degrade_plan: 先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。

### Clip_06 — dialogue_shot_reverse
- characters: CHAR_01/镇魔司制服态, CHAR_03/风尘劲装态, GROUP_01/列队戒备态
- primary: seedance
- fallback: dreamina
- mode: image2video
- sound: timing_basis=text_estimate_no_audio / audio_strategy=base_video_then_post_lipsync / performance_track=missing / voice_lock=pending
- final_sound: stage=post_lipsync_before_compose / post_lipsync_required=True / base_video_only=True
- quality_tier: high
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=3, need_end=True)
- motion_control: none (manifest=-)
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=3; refs_max=0; control_manifest=-
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cross_episode_baseline, cost_quality_tier -> identity_affinity
- rationale:
  - dialogue shots are identity-sensitive and often need lip-sync or strong reference controls
  - default n2d audio remains voiceover-first; do not let the video backend generate speech
  - 混合路由：当前无已签收表演音轨，只生成中性嘴型的基础视频；音轨就绪后走独立后期表演/口型驱动。
  - 执行渠道「即梦/Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 15.551s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 本镜 15.551s 超过 seedance 单次上限 15s；执行侧必须按现有首/中/尾帧拆成 4 段 first_last_relay 付费提交，每段不超过上限，再在后续合成阶段接回。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 10 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - mark mouth_visible and speech_policy=no_native_speech
  - prefer side/back/OTS if lip-sync is disabled
  - base_video_only=true；嘴唇保持自然闭合/静息，不做可辨识发音动作，不让模型即兴说话；为后期表演驱动保留稳定正脸与表情空间。
  - 长镜分段接力：不要单次提交整镜；按 duration_segment_relay.segments 用首帧→中段锚帧→尾帧分段生成。
- degrade_plan: 先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。

### Clip_07 — ensemble_blocking
- characters: CHAR_01/镇魔司制服态, CHAR_03/风尘劲装态, GROUP_01/齐跪态
- primary: seedance
- fallback: dreamina
- mode: image2video
- sound: timing_basis=text_estimate_no_audio / audio_strategy=base_video_then_post_lipsync / performance_track=missing / voice_lock=pending
- final_sound: stage=post_lipsync_before_compose / post_lipsync_required=True / base_video_only=True
- quality_tier: high
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=2, need_end=True)
- motion_control: required (manifest=出视频/第3集/control/Clip_07/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=2; refs_max=0; control_manifest=出视频/第3集/control/Clip_07/motion_control_manifest.json
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - multi-person staging needs reference controls and stable screen direction
  - single-backend generic generation often swaps faces or screen positions
  - 5+ 同框/群像：Sora 已从自动路由移除；Kling 负责槽位/主体约束，仍不稳按 degrade_plan 拆组，不要把 5+ 清晰正脸压在同一镜。
  - 混合路由：当前无已签收表演音轨，只生成中性嘴型的基础视频；音轨就绪后走独立后期表演/口型驱动。
  - 执行渠道「即梦/Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 12.221s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 8 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - write screen positions and focus hierarchy; background crowd must be silhouette, back view, or soft focus
  - one speaking/action focus per clip; do not ask every crowd member to have a clear face
  - bind each named registered character id to its own screen slot (LEFT/RIGHT/FOREGROUND/BACKGROUND) AND its own subject/reference anchor — regional/mask binding per subject; never feed one shared reference for the whole frame (single shared ref makes the model average faces)
  - base_video_only=true；嘴唇保持自然闭合/静息，不做可辨识发音动作，不让模型即兴说话；为后期表演驱动保留稳定正脸与表情空间。
- degrade_plan: 先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。

### Clip_08 — ensemble_blocking
- characters: CHAR_01/镇魔司制服态, GROUP_01/齐跪态焦外
- primary: seedance
- fallback: dreamina
- mode: image2video
- sound: timing_basis=text_estimate_no_audio / audio_strategy=base_video_then_post_lipsync / performance_track=missing / voice_lock=locked
- final_sound: stage=post_lipsync_before_compose / post_lipsync_required=True / base_video_only=True
- quality_tier: high
- execution_adapter_v2: state=automated_ready adapter=dreamina_cli_v2 automated=True
- identity: native_identity_lock_required
- frame_consumption: native_multiframe (execution=dreamina, anchors=1, need_end=True)
- motion_control: required (manifest=出视频/第3集/control/Clip_08/motion_control_manifest.json)
- motion_control_required_inputs: pose_sequence, depth_sequence, instance_masks
- execution_recipe: execution=dreamina; frames=native_multiframe anchors=1; refs_max=0; control_manifest=出视频/第3集/control/Clip_08/motion_control_manifest.json
- policy_resolution: winner=identity_affinity signoff_required=False
  - conflict backend_choice: identity_affinity, cost_quality_tier -> identity_affinity
- rationale:
  - multi-person staging needs reference controls and stable screen direction
  - single-backend generic generation often swaps faces or screen positions
  - 5+ 同框/群像：Sora 已从自动路由移除；Kling 负责槽位/主体约束，仍不稳按 degrade_plan 拆组，不要把 5+ 清晰正脸压在同一镜。
  - 混合路由：当前无已签收表演音轨，只生成中性嘴型的基础视频；音轨就绪后走独立后期表演/口型驱动。
  - 执行渠道「即梦/Dreamina」下改用可执行后端「seedance」；原 primary「kling」storyboard 帧/时长契约不匹配（duration 11.534s exceeds kling max 10s; storyboard has mid anchors but primary lacks native mid-anchor control）；当前渠道不可自动付费路由（confidence=conservative; execution_backend=kling），降为 fallback。
  - 本镜中段锚帧会被后端作为原生时间轴关键帧消费。
  - ⚠️本镜 identity 已失败 10 次：primary「seedance」已具原生身份锁，强制 native_identity_lock_required，并补 reference_group 角度 / 拆镜降难度。
  - 质量档=high：本镜身份/物理吃重，值 pro 档把脸与运动钉稳（落档侧解析为后端 pro model_version）。
- prompt_requirements:
  - write screen positions and focus hierarchy; background crowd must be silhouette, back view, or soft focus
  - one speaking/action focus per clip; do not ask every crowd member to have a clear face
  - bind each named registered character id to its own screen slot (LEFT/RIGHT/FOREGROUND/BACKGROUND) AND its own subject/reference anchor — regional/mask binding per subject; never feed one shared reference for the whole frame (single shared ref makes the model average faces)
  - base_video_only=true；嘴唇保持自然闭合/静息，不做可辨识发音动作，不让模型即兴说话；为后期表演驱动保留稳定正脸与表情空间。
- degrade_plan: 先完成无台词基础视频；音色定妆与最终/可信导引音轨就绪后运行 lipsync_pass 独立驱动口型和表情。基础视频未经该 pass 不得作为最终说话镜进入 compose。

