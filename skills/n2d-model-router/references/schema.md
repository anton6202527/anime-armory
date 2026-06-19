# n2d video model routes schema

`n2d-model-router` 输出两份文件：

- `出视频/第N集/prompt/video_model_routes.json`：机器真值。
- `出视频/第N集/prompt/video_model_routes.md`：人审表。

## JSON 顶层

```json
{
  "kind": "n2d_video_model_routes",
  "version": 1,
  "root": "制漫剧/剧名",
  "episode": "第1集",
  "routing_mode": "auto",
  "production_mode": "配音先行",
  "av_mode": "voice_first",
  "default_backend": "dreamina",
  "generated_at": "2026-06-08T00:00:00Z",
  "routes": [],
  "multishot_groups": []
}
```

字段：

- `routing_mode`: `auto` 或 `fixed_default`。默认 `auto`；若 `_设置.md` 写 `视频模型路由: 固定生视频模型` 才是 `fixed_default`（旧值 `固定生视频AI` 兼容）。
- `production_mode`: 从 `_设置.md 制作模式` 读取（`配音先行`|`先出视频后配音`|`原生音画`）。
- `av_mode`: 音画路线，`voice_first`（默认，配音链路控制台词）或 `native_av`（`制作模式=原生音画`：说话镜一次出同步音画）。
- `default_backend`: 从 `_设置.md 生视频模型` 归一化而来；旧项目 fallback 读取 `生视频AI`，再 fallback 到 `生视频渠道`。`Seedance 2.0` 归一为 `seedance`；`即梦/Dreamina` 归一为 `dreamina`；原生音画后端 `seedance|veo|sora`。
- `routes`: 每条 Clip 一个对象。
- `multishot_groups`: 多镜单次生成候选组清单 `[{group_id, members:[clip_id...], backend, approx_seconds}]`（**advisory**）。在 primary 全部定稿（含跨集 baseline 锚定）后，扫出**连续 ≥2 条接力镜 + 同一支持多镜的 primary**（如直连 Seedance 的项目）的镜组——这段最适合一次 co-generate 消灭接缝、最稳跨镜一致。**组大小受物理约束封顶**：单次多镜生成的总输出长度 ≤ 后端 `max_clip_seconds`（Seedance ~15s），按**累计时长**切组（缺时长时退到 ≤4 成员护栏），所以**镜本身已接近单镜上限时不会成组**（各自已是长单镜，归「更长单镜」覆盖）；多镜单次生成的甜点是**多个短接力镜**一次出。**只是提示，不合并 Clip、不改 primary/mode**：逐 Clip 仍是独立可追踪可重跑单元（模型矩阵立身原则），是否真的一次出由出片侧/用户按接缝风险与重跑需求决定。即梦渠道下执行后端是 dreamina（非多镜叙事核验渠道）→ 保守不标注。

## route 对象

```json
{
  "clip_id": "Clip_01",
  "shot_type": "fight_exchange",
  "template": "fight_exchange",
  "primary_backend": "kling",
  "fallback_backends": ["seedance", "dreamina"],
  "mode": "frames2video",
  "native_audio_policy": "none",
  "identity_requirement": "character_id_or_reference_group",
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
- `mode`: `image2video|frames2video|text2video|multi_shot|native_av|voice_conditioned_lipsync`。注：`multi_shot` 是保留值——多镜单次生成走 **advisory** 的 `multishot_groups` 候选组（见顶层），router **不会**把逐镜 mode 自动改成 `multi_shot`（保逐 Clip 可重跑粒度），需要真合并时由出片侧/用户显式决定。`native_av`=原生音画模式说话镜，一次出同步音画（后端自生成台词，绕过配音先行）；`voice_conditioned_lipsync`=`voice_first`+`对口型` opt-in 的说话镜，把克隆配音 `line_NN.wav` 当口型条件喂进支持音频参考的后端（Seedance 2.0 音素级 / 可灵 Omni）同帧出对口型画面，**音轨仍是配音轨、模型音频不接管声音**——区别于 native_av 的根本点。
- `native_audio_policy`: `none|ambience|native_sfx|native_speech|lipsync_condition_only`，只表达生成意图；compose 是否混入仍由 `视频原生音轨`/`制作模式` 决定。`native_speech`（台词+口型由后端原生生成）只在 `av_mode=native_av` 的说话镜出现；`lipsync_condition_only`（配音仅作口型条件、不进音轨）只在 `voice_conditioned_lipsync` 镜出现，compose 必须用 voice-first 配音轨、丢弃模型这条音频。
- `identity_requirement`: 身份层要求：
  - `none`
  - `first_frame_only`
  - `reference_group`
  - `character_id_or_reference_group`
  - `face_lock_or_reference_group`
  - `reference_controls_or_reference_group`
- `max_clip_seconds`: 该 primary 后端建议单 Clip 上限。超出后回 `n2d-script` 拆 Clip 或换长单镜后端。
- `risk_flags`: `multi_person`、`mouth_visible`、`native_audio_risk`、`native_speech`（原生音画说话镜，须查唇音同步）、`long_duration`、`contact_motion`、`identity_drift_risk`、`motion_reference_candidate`（可用视频运动参考）、`multishot_candidate`（属多镜单次生成候选组）等。
- `quality_tier`: 质量档路由意图，`fast|high|n/a`。`high`=身份/物理吃重镜（脸/接触/多人/原生台词/已升锁），值后端 pro 档把脸与运动钉稳；`fast`=空镜/通用低风险镜，量产省成本；`n/a`=该 primary 无 fast/pro 档（如 veo）。**只表达路由意图，不写死 model_version**——落档侧出片脚本把 `high→pro`、`fast→fast` 解析成后端实际质量档；成本事件带 `quality_tier` 时 dashboard 的 `cost_by_provider` 会按 `provider@tier:unit` 拆出 fast/pro 花销。
- `motion_reference`: `{applicable, use, note}`。长连续运动镜（追逐/飞行/打斗）且 primary 支持 `reference_video_motion`（Seedance/Kling）时 `applicable=true`，提示把**同段前一条已通过 clip 作运动/风格视频参考**喂进去锁运镜节奏（与图身份锁正交的跨镜运动连续性轴）；首条镜无前序参考自然跳过。
- `multishot_candidate`: `{group_id, members, note}`，仅当本镜属一个多镜单次生成候选组时出现。见顶层 `multishot_groups`。
- `motion_control`: 复杂物理交互控制契约，所有 route 都必须有；普通镜写 `level=none`。`fight_exchange`、`intimate_interaction`、`hug_or_pull` 或带 `physical_interaction/contact_motion/feature_melting_risk` 的镜头必须 `level=required`、`manifest_required=true`，并指向 `出视频/第N集/control/Clip_XX/motion_control_manifest.json`。
  - `level`: `none|recommended|required`。`recommended` 用于多人站位/追逐/飞行等可选增强；`required` 用于打斗命中、拥抱、抓腕、拉扯、近距离接触。
  - `required_inputs`: 该镜头需要的控制资产键。高危接触通常至少包含 `pose_sequence`、`depth_sequence`、`instance_masks`；武器/接触点再加 `contact_map`。
  - `backend_control_level/backend_capabilities`: primary 后端的控制能力摘要，只用于 route/gate/prompt，不代表一定已经接入该能力。
  - `recommended_control_backends`: 后续接入顺序，优先 `comfyui_ltx` / `kling_motion_control` / `seedance_reference_video` 这类可控后端。
  - `failure_modes`: 审片重点，如 `feature_melting`、`limb_fusion`、`hand_fusion`、`body_interpenetration`、`weapon_contact_drift`。
  - `gate_policy`: `block_without_ready_manifest_or_degrade_only_manifest` 表示视频 gate 会阻断缺 manifest；manifest 必须是 `ready` 或 `degrade_only`。
- `rationale`: 选择原因，供导演/制片快速审。
- `prompt_requirements`: 该路由要求 prompt 必写的约束。
- `degrade_plan`: 失败后的拆镜/换后端策略。

## motion_control_manifest.json

高危物理接触镜头的 manifest 放在：

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

没有 ready 控制资产但决定拆镜时，写 `status=degrade_only`，必须包含 `degrade_plan`。这表示不直接生成全身复杂接触，改走模板降级方案；gate 会放行拆镜执行，但不会把它当作已接入 Motion Control。`status=ready` 时，`control_inputs.*.path/glob` 必须能匹配到本地控制资产文件；只有字符串路径、没有实际文件会被 gate 阻断。

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

| Clip | shot_type | primary | fallback | mode | native_audio | identity | motion_control | 风险 | 降级 |
|---|---|---|---|---|---|---|---|---|---|
```

`n2d-video/prompt/00_总览.md` 必须复制或引用这张「本集模型路由表」。
