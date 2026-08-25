# n2d video model routes schema

`n2d-model-router` 输出两份文件：

- `出视频/第N集/prompt/video_model_routes.json`：机器真值。
- `出视频/第N集/prompt/video_model_routes.md`：人审表。

## JSON 顶层

```json
{
  "kind": "n2d_video_model_routes",
  "version": 1,
  "root": "创作区/制漫剧/剧名",
  "episode": "第1集",
  "routing_mode": "auto",
  "production_mode": "配音先行",
  "av_mode": "voice_first",
  "default_backend": "dreamina",
  "backend_consistency_scope": {
    "image_generation": "single_model_channel_per_project",
    "video_generation": "per_clip_allowed_with_baseline",
    "required_guards": ["model_routes_baseline", "identity_handoff", "execution_recipe", "post_video_qc"]
  },
  "generated_at": "2026-06-08T00:00:00Z",
  "routes": [],
  "multishot_groups": [],
  "multishot_reroute_recommendations": []
}
```

字段：

- `routing_mode`: `auto` 或 `fixed_default`。默认 `auto`；若 `_设置.md` 写 `视频模型路由: 固定生视频模型` 才是 `fixed_default`（旧值 `固定生视频AI` 兼容）。
- `production_mode`: 从 `_设置.md 制作模式` 读取（`配音先行`|`先出视频后配音`|`原生音画`）。
- `av_mode`: 音画路线，`voice_first`（默认，配音链路控制台词）或 `native_av`（`制作模式=原生音画`：说话镜一次出同步音画）。
- `default_backend`: 从 `_设置.md 生视频模型` 归一化而来；旧项目 fallback 读取 `生视频AI`，再 fallback 到 `生视频渠道`。`Seedance 2.0` 归一为 `seedance`；`即梦/Dreamina` 归一为 `dreamina`；原生音画后端 `seedance|veo|sora`。
- `backend_consistency_scope`: 后端一致性作用域声明。生图侧必须是 `single_model_channel_per_project`（同项目/同集统一生图模型+渠道）；视频侧允许 `per_clip_allowed_with_baseline`（逐镜按能力路由），但必须同时有 `model_routes_baseline`、`identity_handoff`、`execution_recipe`、`post_video_qc` 四类 guard。若 route 表实际混用多个 `primary_backend` 而缺本字段，`video_preflight` 会 BLOCK；这是把“出图统一”和“视频逐镜能力路由”拆成不同作用域，避免互相误伤。
- `routes`: 每条 Clip 一个对象。
- `multishot_groups`: 多镜单次生成**候选组** `[{group_id, members:[clip_id...], backend, approx_seconds}]`。在 primary 全部定稿（含跨集 baseline 锚定）后，扫出**连续 ≥2 条接力镜 + 同一支持多镜的 primary**（如直连 Seedance 的项目）的镜组——这段最适合一次 co-generate 消灭接缝、最稳跨镜一致。**组大小受物理约束封顶**：单次多镜生成的总输出长度 ≤ 后端 `max_clip_seconds`（Seedance ~15s），按**累计时长**切组（缺时长时退到 ≤4 成员护栏），所以**镜本身已接近单镜上限时不会成组**（各自已是长单镜，归「更长单镜」覆盖）；多镜单次生成的甜点是**多个短接力镜**一次出。router 不合并 Clip、不改 primary/mode；出片侧 `multishot_plan.py` 在 `原生多镜生成=自动|开启` 时按 adapter v2 能力激活，一次生成后再按 `edit_target_sec` 拆回原 Clip，继续使用逐 Clip QC/返修/进度与 hash 收据。显式关闭、即梦 Dreamina 渠道（非多镜叙事核验渠道）或 adapter 缺失时自动降级逐镜，无需停问用户。
- `multishot_reroute_recommendations`: 同场景/同角色连续镜的**换后端建议**清单 `[{group_id, members, suggested_backend, basis, roster_switch_required, note}]`（**advisory**·2026-06 一致性加固）。`annotate_multishot_groups` 只在 primary **本身已支持多镜**时标候选；本字段补的是另一半：primary **不支持多镜**（如 dreamina）时，若存在一段「同场景(`同场景`)」或「同角色集(`同角色集`)」连续 ≥2 镜，建议这段改走原生多镜后端（Kling Element Binding / Director Memory 物体恒存、Seedance/Veo 多镜叙事），用单次多镜生成把跨镜身份/场景/对象持久性焊住，省 `inherit_contract` 硬拦。`suggested_backend` 优先取项目 roster（default+fallback）里已有的多镜后端；roster 内没有则给规范候选并置 `roster_switch_required=true`，提醒**换后端须整项目统一、勿混用**（anti-mixing 闸）。同样**不改 primary、不合并 Clip**，逐 Clip 仍可追踪可重跑，由出片侧/用户定夺。对应 route 上有 `multishot_reroute_suggestion` + risk_flag `multishot_reroute_candidate`。

## route 对象

```json
{
  "clip_id": "Clip_01",
  "shot_type": "fight_exchange",
  "template": "fight_exchange",
  "primary_backend": "kling",
  "fallback_backends": ["seedance", "dreamina"],
  "mode": "frames2video",
  "video_generation_audio_policy": "无声视频流",
  "native_audio_policy": "none",
  "identity_requirement": "character_id_or_reference_group",
  "identity_preservation_plan": {
    "priority": "motion_may_reduce_static_anchor_density_but_not_identity_contract",
    "must_keep": ["CHAR_01 face_shape/hairstyle/outfit_palette", "reference_group or native subject binding"],
    "allowed_motion_overrides": ["use wider shot", "reduce closeup face deformation checks during impact frames"],
    "fallback": "split identity closeup + action wide shot"
  },
  "clip_characters": [
    {"character_id": "CHAR_01", "form": "常态"}
  ],
  "max_clip_seconds": 10,
  "risk_flags": ["contact_motion", "feature_melting_risk", "physical_interaction"],
  "motion_control": {
    "level": "required",
    "required": true,
    "manifest_required": true,
    "manifest_path": "出视频/第1集/control/Clip_01/motion_control_manifest.json",
    "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks", "contact_map"],
    "backend_control_level": "medium",
    "backend_capabilities": ["first_last_frame", "motion_brush", "reference_video_motion", "character_id"],
    "recommended_control_backends": ["comfyui_ltx", "kling_motion_control", "seedance_reference_video"],
    "failure_modes": ["feature_melting", "limb_fusion", "weapon_contact_drift"],
    "gate_policy": "block_without_ready_manifest_or_degrade_only_manifest",
    "degrade_allowed": true,
    "notes": ["OpenPose/DWPose alone is not enough for weapon/body contact; add depth + instance masks where possible"]
  },
  "action_choreography": {
    "required": true,
    "shot_type": "fight_exchange",
    "beat_model": "setup_attack_impact_reaction_recovery",
    "required_fields": ["beats", "speed_curve", "spatial_path", "camera_path", "readability_beats", "degrade_plan", "attack_path", "impact_frame", "contact_points", "force_direction", "recovery_beat"],
    "failure_modes": ["unclear_hit", "wrong_force_direction", "limb_fusion", "weapon_contact_drift"],
    "gate_policy": "block_prompt_without_action_choreography_contract"
  },
  "execution_recipe": {
    "backend": "kling",
    "execution_backend": "kling",
    "mode": "frames2video",
    "quality_tier": "high",
    "urgency_tier": "realtime",
    "frame_inputs": {
      "first_frame": true,
      "last_frame": true,
      "mid_anchors": 0,
      "consumption_mode": "first_frame",
      "native_timeline_frames": 2,
      "requires_split_relay": false,
      "reference_only": false
    },
    "reference_inputs": {
      "characters": [{"character_id": "CHAR_01", "form": "常态", "binding": "character_id_or_reference_group"}],
      "assets": ["WEAPON_01"],
      "max_reference_images": 4,
      "motion_reference": {
        "allowed": true,
        "library_path": "生产数据/motion_reference_library.json",
        "policy": "use same sequence/shot_type approved reference when available"
      }
    },
    "control_inputs": {
      "manifest_path": "出视频/第1集/control/Clip_01/motion_control_manifest.json",
      "required": true,
      "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks", "contact_map"],
      "gate_policy": "block_without_ready_manifest_or_degrade_only_manifest"
    },
    "audio_inputs": {"video_generation_audio_policy": "无声视频流", "native_audio_policy": "none", "speech_policy": "no_native_speech"},
    "fallback": {"fallback_backends": ["seedance", "dreamina"], "degrade_plan": "Split into setup and impact clips."},
    "capability_match": {"frame_contract_supported": true, "motion_reference_supported": true, "motion_control_level": "medium"}
  },
  "rationale": [
    "fight/contact motion benefits from first/last frame control and motion brush",
    "named characters require identity adapter or reference_group fallback"
  ],
  "prompt_requirements": [
    "write first frame and end frame as hard constraints",
    "keep impact beat short; avoid multi-action choreography in one clip"
  ],
  "degrade_plan": "Split into setup and impact clips; keep one contact action per clip."
}
```

字段：

- `clip_id`: Clip 编号，尽量与 `storyboard.json` 一致；缺失时生成 `Clip_XX`。
- `shot_type`: 路由识别出的镜头类型，常见值：
  - `fight_exchange`
  - `chase`
  - `dialogue_shot_reverse`
  - `dialogue_closeup`
  - `magic_burst`
  - `flight`
  - `mount_ride`
  - `vehicle_ride`
  - `vessel_flight`
  - `road_vehicle`
  - `screen_insert`
  - `evidence_search`
  - `stealth_stalk`
  - `tribulation_breakthrough`
  - `meditation_cultivation`
  - `alchemy_forging`
  - `dual_cultivation`
  - `kiss_or_near_kiss`
  - `array_ritual`
  - `soul_manifestation`
  - `realm_portal`
  - `contract_summon`
  - `talent_test`
  - `empty_establishing`
  - `intimate_interaction`
  - `hug_or_pull`
  - `multi_character_same_frame`
  - `ensemble_blocking`
  - `multi_person_blocking`
  - `general_motion`
- `template`: 来自 `storyboard.json clips[].template`；没有写 `none`。
- `primary_backend`: 首选后端，归一化为 `dreamina|kling|seedance|veo|sora`。
- `fallback_backends`: 备用后端，按优先级排序。
- `mode`: `image2video|frames2video|text2video|multi_shot|native_av|voice_conditioned_lipsync`。`voice_conditioned_lipsync` 可由混合 route 的获批 performance/guide 轨触发，不要求整项目先有 final voice；模型音频只作表演/口型条件，成片仍用获批 final voice。没有可信轨时保持 image2video base plate，并由 `post_lipsync_required` 打开独立后期通道。`native_av` 仅给逐镜合同允许且能力已核验的同步音画镜。其它 text2video/multi_shot 边界不变。
- `audio_strategy`: `performance_audio_first|base_video_then_post_lipsync|rough_timing_final_dub_later|post_dub|picture_first|native_av`，混合模式必填。
- `timing_basis`: 本镜使用 final/guide performance、`text_estimate_no_audio`、picture rhythm 或 native AV script timing。
- `performance_track_status/path`: 可见口型镜头的表演证据；路径必须指向真实音频，不能写计划路径冒充 ready。
- `voice_casting_status` / `final_voice_stage`: 声音定妆与最终声音阶段。
- `base_video_only` / `neutral_mouth_policy` / `post_lipsync_required` / `post_lipsync_output`: 基础视频后置口型合同；最终 video/compose/review 按输出路径验收。
- `video_generation_audio_policy`: `无声视频流|配音对齐口型|低风险环境声|原生音画|自定义`。非原生音画默认 `无声视频流`，表示执行层应走 video-only/no-audio 图生视频或多关键帧视频流；不要因为后期 `视频原生音轨` 设置而改走音频条件或原生人声路径。只有显式 opt-in 时才允许 `voice_conditioned_lipsync`、`native_sfx/ambience` 或 `native_speech`。
- `native_audio_policy`: `none|ambience|native_sfx|native_speech|lipsync_condition_only`，只表达生成意图；compose 是否混入仍由 `视频原生音轨`/`制作模式` 决定。`native_speech`（台词+口型由后端原生生成）只在 `av_mode=native_av` 的说话镜出现；`lipsync_condition_only`（配音仅作口型条件、不进音轨）只在 `voice_conditioned_lipsync` 镜出现，compose 必须用 voice-first 配音轨、丢弃模型这条音频。
- `requires_voice_fallback`: 可选布尔。仅用于 `av_mode=native_av` 但本 Clip 因固定后端/身份优先模板不能走 `native_speech` 的说话/口型镜。为 `true` 时必须同时写 `fallback_production_mode=voice_first`，表示本镜重新打开 n2d-voice 真实配音链路；video/compose gate 会阻断缺配音或占位配音，防止无声对白镜。
- `identity_requirement`: 身份层要求：
  - `none`
  - `first_frame_only`
  - `reference_group`
  - `character_id_or_reference_group`
  - `face_lock_or_reference_group`
  - `reference_controls_or_reference_group`
- `identity_preservation_plan`: 高动作/接触/大场面镜且有身份要求时必填。它声明“运动优先时哪些身份契约仍不可牺牲”：必须保留的脸型/发型/服饰锚、实际可消费的 reference/native subject/Face Lock 绑定、允许为物理运动让步的项（例如改远景而不是近景硬打）、失败时拆成身份近景 + 动作远景的 fallback。若该镜 `motion_control.required=true` 且缺本字段，video gate 会 BLOCK。
- `clip_characters`: 本 Clip 实际出现的角色绑定，身份镜必填。元素至少含 `character_id`，可选 `form`。router 从 `storyboard.json` 的结构化角色字段或 `CHAR_xx/形态` 提取；普通自然语言人名只可作为人审信息，不能替代 `character_id`。`n2d-review gate` 用该字段把身份 adapter matrix 检查缩到本 Clip 角色；`identity_requirement != none` 且缺有效 `clip_characters[]` 会 BLOCK 并要求重跑 router/补 storyboard 角色 ID。
- `max_clip_seconds`: 该 primary 后端建议单 Clip 上限。超出后回 `n2d-script` 拆 Clip 或换长单镜后端。
- `risk_flags`: `multi_person`、`mouth_visible`、`native_audio_risk`、`native_speech`（原生音画说话镜，须查唇音同步）、`long_duration`、`contact_motion`、`high_speed_motion`、`spatial_path_risk`、`action_choreography_required`、`identity_drift_risk`、`motion_reference_candidate`（可用视频运动参考）、`multishot_candidate`（属多镜单次生成候选组）等。
- `quality_tier`: 质量档路由意图，`fast|high|n/a`。`high`=身份/物理吃重镜（脸/接触/多人/原生台词/已升锁），值后端 pro 档把脸与运动钉稳；`fast`=空镜/通用低风险镜，量产省成本；`n/a`=该 primary 无 fast/pro 档（如 veo）。**只表达路由意图，不写死 model_version**——落档侧出片脚本把 `high→pro`、`fast→fast` 解析成后端实际质量档；成本事件带 `quality_tier` 时 dashboard 的 `cost_by_provider` 会按 `provider@tier:unit` 拆出 fast/pro 花销。
- `motion_reference`: `{applicable, use, note}`。长连续运动镜（追逐/飞行/御兽/马车/飞舟/现代车辆/尾随潜入/打斗）且 primary 支持 `reference_video_motion`（Seedance/Kling）时 `applicable=true`，提示把**同段前一条已通过 clip 作运动/风格视频参考**喂进去锁运镜节奏（与图身份锁正交的跨镜运动连续性轴）；首条镜无前序参考自然跳过。
- `execution_recipe`: 调用层配方，所有 route 必须有。它不是给人读的理由，而是把 route 归一为执行代码/人工跑后端时必须消费的输入：
  - `frame_inputs`: 首帧/尾帧/中段锚帧、后端实际消费模式、native timeline 帧数、是否仅作 reference。
  - `reference_inputs`: 本镜角色、资产、参考图上限、可用动作参考库路径（`生产数据/motion_reference_library.json`）。
  - `control_inputs`: Motion Control manifest、required_inputs 和 gate policy；`required=true` 时缺 `manifest_path` 会被 video gate 阻断。
  - `audio_inputs`: 上述逐镜声音字段 + `video_generation_audio_policy` + native audio/speech policy，供无声 base、表演条件、后配与原生音画分流。
  - `fallback`: fallback 后端和降级拆镜方案，供重试/批量回流消费。
  - `capability_match`: 帧契约、运动参考、控制能力是否满足，供 gate 和执行层做最后兜底。
- `multishot_candidate`: `{group_id, members, note}`，仅当本镜属一个多镜单次生成候选组时出现。见顶层 `multishot_groups`。
- `motion_control`: 复杂动作/物理交互控制契约，所有 route 都必须有；普通镜写 `level=none`。`fight_exchange`、`chase`、`flight`、`mount_ride`、`vehicle_ride`、`vessel_flight`、`road_vehicle`、`stealth_stalk`、`intimate_interaction`、`hug_or_pull`、多人/群像调度，或带 `physical_interaction/contact_motion/high_speed_motion/spatial_path_risk` 的镜头必须 `level=required`、`manifest_required=true`，并指向 `出视频/第N集/control/Clip_XX/motion_control_manifest.json`。
  - `level`: `none|recommended|required`。`required` 用于打斗命中、追逐、飞行、御兽/坐骑、马车/载具、飞舟/御物、现代车辆/车流、尾随/潜入、拥抱、抓腕、拉扯、近距离接触和复杂空间调度；普通低幅度镜头为 `none`。
  - `required_inputs`: 该镜头需要的控制资产键。高危接触通常至少包含 `pose_sequence`、`depth_sequence`、`instance_masks`；武器/接触点再加 `contact_map`。追逐常见 `pose_sequence`、`depth_sequence`、`camera_path`、`spatial_path`；飞行常见 `pose_sequence`、`depth_sequence`、`camera_path`、`parallax_layers`；御兽常见 `pose_sequence`、`depth_sequence`、`instance_masks`、`contact_map`、`camera_path`、`spatial_path`、`parallax_layers`；马车/飞舟/现代车辆常见 `depth_sequence`、`camera_path`、`spatial_path`、`parallax_layers`；尾随潜入常见 `pose_sequence`、`depth_sequence`、`camera_path`、`spatial_path`、`parallax_layers`。
  - `backend_control_level/backend_capabilities`: primary 后端的控制能力摘要，只用于 route/gate/prompt，不代表一定已经接入该能力。
  - `recommended_control_backends`: 后续接入顺序，优先 `comfyui_ltx` / `kling_motion_control` / `seedance_reference_video` 这类可控后端。
  - `failure_modes`: 审片重点，如 `feature_melting`、`limb_fusion`、`hand_fusion`、`body_interpenetration`、`weapon_contact_drift`。
  - `gate_policy`: `block_without_ready_manifest_or_degrade_only_manifest` 表示视频 gate 会阻断缺 manifest；manifest 必须是 `ready` 或 `degrade_only`。
- `rationale`: 选择原因，供导演/制片快速审。
- `prompt_requirements`: 该路由要求 prompt 必写的约束。
- `degrade_plan`: 失败后的拆镜/换后端策略。
- `action_choreography`: 高动作编排契约，普通镜可写 `{"required": false}`。
  - `required`: `fight_exchange/chase/magic_burst/flight/mount_ride/vehicle_ride/vessel_flight/road_vehicle/stealth_stalk` 必须为 `true`。
  - `required_fields`: n2d-video prompt 的「动作编排契约」必须逐项写出的字段。通用字段为 `beats/speed_curve/spatial_path/camera_path/readability_beats/degrade_plan/keyframe_plan/post_cue_points/physics_guard`。
  - `fight_exchange` 额外字段：`attack_path/impact_frame/contact_points/force_direction/recovery_beat`。
  - `magic_burst` 额外字段：`charge_frame/release_frame/effect_asset/energy_path/collision_or_apex_frame/power_shift`。
  - `chase` 额外字段：`screen_direction/distance_curve/obstacle_beats/parallax_layers/overtake_or_escape_beat`。
  - `flight` 额外字段：`flight_path/altitude_curve/pose_lock/parallax_layers/mount_or_cloud_lock`。
  - `mount_ride` 额外字段：`mount_contact/gait_cycle/screen_direction/parallax_layers/harness_lock`。
  - `vehicle_ride` 额外字段：`vehicle_lock/wheel_rotation/harness_lock/screen_direction/parallax_layers`。
  - `vessel_flight` 额外字段：`vehicle_lock/flight_path/altitude_curve/screen_direction/parallax_layers`。
  - `road_vehicle` 额外字段：`vehicle_lock/wheel_rotation/driver_control_lock/lane_lock/traffic_flow/screen_direction/parallax_layers`。
  - `stealth_stalk` 额外字段：`screen_direction/distance_curve/occlusion_layers/light_shadow_lock/reveal_or_hide_beat/parallax_layers`。
  - `gate_policy`: `block_prompt_without_action_choreography_contract` 表示 video prompt 缺动作编排契约或字段不全会被 gate 阻断。

## motion_control_manifest.json

高危动作/物理镜头的 manifest 放在：

```text
出视频/第N集/control/Clip_XX/motion_control_manifest.json
```

`ready` 示例：

```json
{
  "kind": "n2d_motion_control_manifest",
  "version": 1,
  "clip_id": "Clip_01",
  "status": "ready",
  "control_inputs": {
    "pose_sequence": { "type": "openpose_or_dwpose", "status": "ready", "path": "出视频/第1集/control/Clip_01/openpose_%03d.png" },
    "depth_sequence": { "type": "depth", "status": "ready", "path": "出视频/第1集/control/Clip_01/depth_%03d.png" },
    "instance_masks": { "type": "instance_mask", "status": "ready", "path": "出视频/第1集/control/Clip_01/seg_%03d.png" },
    "contact_map": { "type": "contact_map", "status": "ready", "path": "出视频/第1集/control/Clip_01/contact_map.json" }
  },
  "contact_points": [{ "a": "CHAR_A.right_hand", "b": "CHAR_B.left_wrist", "frames": "12-36" }],
  "occlusion_order": ["CHAR_A.right_hand over CHAR_B.left_wrist"],
  "body_part_ownership": ["CHAR_A.right_hand", "CHAR_B.left_wrist"],
  "failure_modes": ["feature_melting", "hand_fusion"],
  "degrade_plan": "若控制资产不被后端支持，拆成手部特写 + 反打 + 释放帧。"
}
```

追逐/飞行/御兽/马车/飞舟/现代车辆/尾随潜入类 `ready` manifest 可以不写刀剑命中语义字段，但要提供动作路径、接触/牵引、车道/遮挡或视差控制输入，例如：

```json
{
  "control_inputs": {
    "pose_sequence": { "type": "openpose_or_dwpose", "status": "ready", "path": "出视频/第1集/control/Clip_03/openpose_%03d.png" },
    "depth_sequence": { "type": "depth", "status": "ready", "path": "出视频/第1集/control/Clip_03/depth_%03d.png" },
    "camera_path": { "type": "camera_path", "status": "ready", "path": "出视频/第1集/control/Clip_03/camera_path.json" },
    "parallax_layers": { "type": "parallax_layers", "status": "ready", "path": "出视频/第1集/control/Clip_03/parallax_layers.json" }
  }
}
```

没有 ready 控制资产但决定拆镜时，写 `status=degrade_only`，必须包含 `degrade_plan`。这表示不直接生成全身复杂接触或长连续高速动作，改走模板保真实现分解方案；gate 会放行拆镜执行，但不会把它当作已接入 Motion Control。`status=ready` 时，`control_inputs.*.path/glob` 必须能匹配到本地控制资产文件；只有字符串路径、没有实际文件会被 gate 阻断。

远端控制资产不能只写裸 URI。`control_inputs.*` 若使用 `uri`，必须是对象，并且同时满足：

- `uri` scheme 只能是 `https://`、`s3://` 或 `gs://`；`file://` 和任意本地缺失路径不放行。
- `verified_at` 是 `YYYY-MM-DD`。
- 至少填写 `sha256`、`checksum`、`etag` 之一，保证可审计。

示例：

```json
{
  "pose_sequence": {
    "type": "openpose_or_dwpose",
    "status": "ready",
    "uri": "s3://asset-bucket/show/Clip_01/openpose.zip",
    "verified_at": "2026-06-08",
    "sha256": "..."
  }
}
```

## Markdown 总览

`video_model_routes.md` 至少包含：

```markdown
## 本集模型路由表

| Clip | characters | shot_type | primary | execution_recipe | fallback | mode | native_audio | identity | motion_control | 风险 | 降级 |
|---|---|---|---|---|---|---|---|---|---|---|---|
```

`n2d-video/prompt/00_总览.md` 必须复制或引用这张「本集模型路由表」。

## baseline override

第 2 集起，高风险/含角色 route 要按 `设定库/model_routes_baseline.json` 锚定。自然路由漂移会写 `baseline_drift`；高风险/含角色漂移在 gate 中默认 BLOCK。临时改后端必须写结构化 `baseline_override`，不能只写自由文本原因：

```json
{
  "baseline_override": {
    "accepted": true,
    "reviewer": "qa",
    "reason": "本集为满足动作控制临时换后端，已人工复核角色一致性",
    "expires_at": "2099-01-01",
    "affected_routes": ["Clip_01", "Clip_02"]
  }
}
```

要求：`accepted=true`、`reviewer`、`reason`、未过期 `expires_at`、非空 `affected_routes`；`affected_routes` 可用 `*`，否则必须覆盖当前 `clip_id`。
