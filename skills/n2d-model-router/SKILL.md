---
name: n2d-model-router
description: 横切模型适配层：在 n2d 出视频前，按镜头类型/专项模板/原生音画/身份锁定/时长，把每个 Clip 路由到最适合的视频后端 primary/fallback，避免固定一个视频模型包打天下。Use when asked about model routing, 模型适配层, 后端路由, 视频模型选择, 打斗/对话/真相揭示/公开对质/关系转折/飞行/空镜/法术爆发/亲密互动/拥抱拉扯/多人同框/群像站位该用哪个视频模型.
---

# n2d-model-router — 视频模型适配层

你是 **n2d 视频模型路由员**。你的任务不是写更长 prompt，而是在 `n2d-video` 烧视频积分前，先回答每条 Clip：

1. 这是什么镜头类型。
2. 它需要哪种后端能力。
3. primary 后端是谁，fallback 后端是谁。
4. 复杂物理交互是否需要 Motion Control manifest。
5. 失败时怎么换实现路径、补控制资产或拆镜拍全。
6. prompt / 平台参数 / gate 要怎样执行这条路由。

## 触发

- 用户说：模型适配层、model routing、模型路由、后端路由、视频模型选择、不要固定一个视频模型。
- `n2d-video` 生成视频 prompt 前，尤其本集有打斗、追逐、对话反打、真相揭示/身份曝光、公开对质/审讯/谈判、关系转折、飞行、空镜、法术爆发、亲密互动、拥抱拉扯、多人同框、群像站位。
- `n2d-review` 发现某类镜头在同一后端反复失败，需要沉淀成路由规则。

## 输入 / 输出 / 读写边界

- **输入**：`_设置.md`、`storyboard.json`、`identity_registry.json`、视频模型/渠道能力档案、跨集路由基线；若存在 `生产数据/spectacle_backend_benchmark.json`，自动读取打斗/追逐/飞行/大场景 probe 结果作为自动路由加权。
- **输出**：`出视频/第N集/prompt/video_model_routes.json` 和 `.md`，同步写 `生产数据/consistency_policy_lattice.json`；第 1 集打样后写 `设定库/model_routes_baseline.json`。第 2 集起凡含核心/角色身份或高风险镜头（打斗/追逐/多人/揭示/对质/关系转折等），`n2d-review gate` 会要求路由按该基线锚定；自然路由漂移需刷新基线或写结构化 `baseline_override`（`accepted/reviewer/reason/expires_at/affected_routes`）。
- **读写边界**：只写路由表和基线；不生成视频、不改 `_进度.md`、不替 `n2d-video` 写最终 clip prompt。
- **契约关系**：模型路由是 `skills/n2d/_lib/n2d_contract.py` 的横切工具（`CROSS_CUTTING_TOOLS`），不是进度 readiness 项；motion control / native AV / lipsync 判定必须复用契约常量。

## 核心原则

- **能力先于品牌**：先判断镜头需要“强运动 / 长单镜 / 口型 / 原生环境声 / 角色 ID / 首尾帧 / 多主体互动”等能力，再映射到当前模型。讲能力取舍的散文/路由表可用品牌族标签；具体版本名只放在 `n2d/references/模型矩阵.md` 快照里。
- **路由产物必须指认到具体模型（设计宪法 C5）**：`video_model_routes.json` 每个 Clip 的 `primary/fallback` 落地时必须解析成**具体模型名+版本**（如 `Seedance 2.0` / `Veo 3.1` / `Kling 3.0`）作为生成者，**渠道/CLI（即梦/Dreamina、Google Gemini API 等）单独记为访问入口**——不得只写渠道或厂商当生成者；route/dashboard 记账以**模型为主键、渠道为副**。下表的品牌族标签是能力路由，落地前由适配层归一到模型+版本。
- **剧情/质量优先（设计宪法 C6）**：路由表里的"拆 OTS/反打 / 拆 establish+反打"是**把难镜拍全的手段**，不是删戏——镜头该不该存在由剧情决定，路由只决定**用哪个模型 + 要不要拆/合成**把它做到位。
- **项目默认只做兜底**：`_设置.md` 的 `生视频模型` 是默认/兜底，不再固定所有 Clip；`生视频渠道` 只决定实际去哪调用。旧 `生视频AI` 兼容读取。除非 `视频模型路由=固定生视频模型`，否则按本层自动路由。
- **后端一致性按作用域，不混成一条规则**：生图阶段的硬规则是 `single_model_channel_per_project`（同项目/同集统一生图模型+渠道，防脸和画风漂）；视频阶段默认是 `per_clip_allowed_with_baseline`（逐镜按能力路由），但 route 表顶层必须写 `backend_consistency_scope`，并配齐 `model_routes_baseline`、`identity_handoff`、`execution_recipe`、`post_video_qc` guard。也就是说：视频可以因打斗/对话/原生音画换 primary，但必须有基线、身份交接、执行配方和成片回验；不能把“生图不混用”误用成“视频所有镜头必须同一后端”，也不能把视频逐镜路由当作无约束混厂。
- **一致性策略优先级是机器契约**：所有 route 最终都写 `policy_resolution`，顶层写 `policy_lattice`，并把同一表落到 `生产数据/consistency_policy_lattice.json`。同一 surface 冲突时按优先级裁决：`fixed_mode` > 合规/硬能力证据 > `native_voice_fallback` > `identity_affinity`/失败升锁 > `motion_control_required`/帧锚契约 > `cross_episode_baseline` > `spectacle_benchmark` > `spectacle_prior` > 成本/质量档 > motion reference / multishot advisory。低优先级 pass 只能记录 deferred 或显式 override 证据，不能静默覆盖高优先级。
- **固定模式最高优先**：`视频模型路由=固定生视频模型` 时，用户选定模型优先于 native AV / 对口型自动抢路由；需要原生音画时应关闭固定模式或显式改默认模型，不得悄悄切到其它 native_speech 后端。若本机只有一个可用 CLI/渠道，可在 `_设置.md` 写 `视频备用后端=无`，固定模式不得把不可执行后端写成 fallback。旧值 `固定生视频AI` 兼容。
- **复杂镜不从零写**：若 `storyboard.json clips[].template` 已命中专项模板，路由必须继承模板，不靠 prompt 现场猜。
- **高动作不靠文本猜**：打斗命中、追逐、飞行/腾云驾雾/御剑、拥抱、抓腕、拉扯、近距离接触等高动作/物理镜头必须输出 `motion_control.level=required` 和 `manifest_path`。视频 gate 会要求该 manifest 为 `ready`（有 pose/depth/instance/contact/camera_path/spatial_path/parallax_layers 控制资产）或 `degrade_only`（实现分解方案：手部特写/反打/释放帧/正反打追逐/起飞巡航机动抵达，保留剧情 beat 与动作目标），缺 manifest 不进入付费出视频。`ready` 控制资产用本地 `path/glob` 时必须能匹配真实文件；用远端 `uri` 时必须是 `https/s3/gs`，并带 `verified_at=YYYY-MM-DD` + `sha256/checksum/etag` 之一，裸 URI 或 `file://` 不放行。
- **动作编排契约（action_choreography）**：`fight_exchange/chase/flight` 路由必须额外输出 `action_choreography.required=true`，列出 beats、speed_curve、spatial_path、camera_path、readability_beats、degrade_plan 和模板专属字段。打斗锁 attack_path/impact_frame/contact_points/force_direction/recovery_beat；追逐锁 screen_direction/distance_curve/obstacle_beats/parallax_layers/overtake_or_escape_beat；飞行锁 flight_path/altitude_curve/pose_lock/parallax_layers/mount_or_cloud_lock。n2d-video prompt 缺「动作编排契约」会被 gate 阻断。
- **高动作身份优先级必须明写**：打斗、追逐、飞行、拥抱拉扯、多人接触、大场面等镜头若 `identity_requirement != none`，route 必须写 `identity_preservation_plan`。它要列明必须保留的身份锚（脸型/发型/服饰/主体绑定）、允许为运动可读性让步的范围（如改远景、减少近景变形检查窗口）、以及失败 fallback（身份近景 + 动作远景/反打拆镜）。`motion_control.required=true` 且缺该计划时，video gate 会 BLOCK，避免“为了物理运动把人拍成另一个人”。
- **执行配方不是说明文字**：每条 route 必须输出 `execution_recipe`，把 `primary_backend` 归一成调用层可消费的 `frame_inputs`、`reference_inputs`、`control_inputs`、`audio_inputs`、`fallback` 和 `capability_match`。video gate 会阻断缺 `execution_recipe` 或 Motion Control 需要但缺 `manifest_path` 的 route，避免后端能力只停留在路由文案里。
- **probe 结果可回灌，但不覆盖高优先级锁定**：`n2d-script/scripts/spectacle_probe_pack.py` 会产出小样矩阵和 `生产数据/spectacle_backend_benchmark.json` 填写 schema。自动路由模式下，router 读取该文件：若某类镜头的 probe 推荐了更稳 primary（如 fight_exchange 从 Kling 改 Seedance），会把推荐后端升为 primary、原 primary 保留为 fallback，并在 `spectacle_benchmark` 留痕；但它不得覆盖固定模式、角色后端锁或跨集基线。确需覆盖基线/身份锁，benchmark 记录必须显式写 `override_baseline=true` / `override_identity_lock=true`，并在 QC 签收后执行。
- **冷启动后端先验（benchmark 缺失兜底）**：没跑过 probe 的项目，对「关键词识别为打斗/追逐/腾云/大场景、但 shot_type 通用、路由落到 default」那批镜，自动按动作类型默认排序兜底（打斗→Kling、连续追逐→Seedance、飞行/大场景→Veo；单一真值源 `n2d_platform_profiles.SPECTACLE_BACKEND_PRIOR`），原 default 保留为 fallback，留痕 `spectacle_prior` + `risk_flag=spectacle_prior_routed`。仅自动路由生效；benchmark 一旦填写即覆盖先验，`固定生视频模型`/baseline 锚定不动。
- **控制资产脚手架（补"只 gate 不生成"的摩擦）**：路由只声明、gate 只校验，中间用 `scripts/motion_control.py` 把骨架和清单补上，别让操作者照 schema 手搓 JSON：
  - `python3 scripts/motion_control.py <作品根> 第N集 scaffold [--clip Clip_03]` —— 读 `video_model_routes.json`，为每个 `level=required` 的 Clip 生成/合并一份**非 ready 骨架** manifest（`status=planned`、逐 input `status=missing`+规范路径，已填字段不回退），并打印"该 Clip 还要产出哪几个控制文件 + 接触语义字段"的精确清单。骨架仍被 gate 阻断（这是对的：还没就位）。
  - `python3 scripts/motion_control.py <作品根> 第N集 check` —— 对照磁盘：文件已就位的 input 客观翻 `ready`（**不**自动翻顶层 status——`contact_points/occlusion_order/body_part_ownership` 语义要人确认后手改 ready），报告 gate 会不会过。
  - `python3 scripts/motion_control.py <作品根> 第N集 generate [--clip ...] [--no-cache]` —— 可选：装 `controlnet_aux`(DWPose)/depth 库时从首/尾帧抽 pose/depth 种子帧；缺库优雅跳过、显式标，`instance_masks/contact_map` 始终留人工（需 SAM+人定接触点）。**步内指纹缓存**：抽前先对「源首/尾帧 PNG 内容 SHA + 抽取参数」算 git-free 指纹（复用 `n2d/_lib/skill_snapshot.artifact_fingerprint`，与 n2d-update `inputs_fingerprint` 同源），写进 manifest 的 `generate_cache.<input>`；重跑该镜时指纹未变且产物已在 → 复用不重算，只有源帧/参数变了或产物缺失才重抽。诚实：指纹缺失/失配/产物不在一律当需重抽，绝不臆造跳过。强制重抽用 `--no-cache` 或 `N2D_MOTION_CONTROL_NO_CACHE=1`（留痕）。
  - 输出形状与 gate `check_motion_control_manifest` 单一真值源对齐（已交叉验证：planned 阻断 / 填齐 ready 放行 / degrade_only+plan 放行）。
- **T2V 原生动作通道（实验特例 · 默认关闭）**：`mode=text2video` 不是主线默认，也不能绕过角色身份链。只有同时满足以下条件才允许路由切到 T2V：① `_设置.md` 显式写 `T2V动作通道=实验开启`；② Clip 是 `fight_exchange` / `chase` 等高动量、强物理镜头；③ 镜头不是核心角色近景/清晰脸/身份验收重点，或已写 `t2v_identity_reference_plan`（reference_inputs、禁漂身份锚、资产锚、失败回退）；④ route 写明 `experimental_t2v=true`、`degrade_plan=image2video_or_frames2video`。**收益**：在远景高速动作、空中追逐、群体运动等对物理连贯性高于脸部一致性的镜头里，让 Veo / Seedance 等后端从文本和参考资产重算动量，减少“静态首帧微动”感。**执行边界**：T2V 只可跳过付费首帧 PNG，不可跳过共享定妆、角色/场景/道具参考包、视觉/风格契约和 route 证据；`n2d-video` 的 frame 检查只对 `experimental_t2v=true` 的 Clip 豁免 `firstframe_png`，仍要检查 reference_inputs、identity anchors、motion contract 和失败回退。若这些专用字段缺失，router 必须回退 image2video/frames2video，而不是直接走文生视频。
- **mouth_visible 自动预填**：`scripts/mouth_detect.py <作品根> 第N集` 为每 Clip 预填/复核 `mouth_visible`（决定原生音画 opt-in 与是否要口型同步）。文本端复用 `clip_has_mouth_visible`（单一真值源），图像端装 insightface 时从首帧 PNG 用 106 关键点判正脸+嘴可见（缺库优雅回退文本端、标 `image=unknown`，绝不臆造）。图↔文本/图↔prompt 不一致标 warn（以图为准），省得逐镜手判后还填错原生音画策略。
- **三条音画路线，按 `制作模式` + `对口型` 选（避免被代差绕过）**：
  - **`配音先行`（强配音控制模式）**：说话镜由配音链路控制，**不让视频模型生成台词**；只有空镜/远景/无口型低风险镜头可 opt-in 原生环境声/音效（`ambience/native_sfx`）。
  - **`配音先行 + 对口型 opt-in`（voice_conditioned_lipsync）**：`制作模式=配音先行` 且 `对口型≠关闭` 时，**说话镜（对话反打/说话特写/mouth_visible）路由 `mode=voice_conditioned_lipsync`、`native_audio_policy=lipsync_condition_only`**，primary 选支持音频参考口型的后端（Seedance 2.0 音素级 / 可灵 Omni，见 `LIPSYNC_AUDIO_REF_BACKENDS`），把本镜配音 `line_NN.wav` 当**口型条件**喂进去同帧出对口型画面。**关键：音轨仍是 voice-first 克隆音色（compose 用配音轨），模型音频只作口型条件、不接管声音**——既不双人声、又省一道后期 MuseTalk/Wav2Lip 对口型 pass。后端不支持音频参考口型 → 按 `degrade_plan` 回退「image2video 静音 + 后期对口型 pass」，或改用侧脸/背身/反应镜实现同一对白 beat。这是 native_av 与「配音→后期对口型」之间的中间路线。
  - **`原生音画`（native AV·opt-in 整剧）**：`制作模式=原生音画` 时，**说话镜路由到原生同步音画后端**（Seedance 2.0 / Veo 3.1，见 `NATIVE_AV_BACKENDS`），`mode=native_av`、`native_audio_policy=native_speech`，一次出台词+口型+环境声，**绕过配音先行的时长清单**（台词文本/情绪/单镜时长来自脚本）。Sora legacy/manual-only，不进入 `NATIVE_AV_BACKENDS`。规避「配音→对口型」代差与占位返工；代价是少了逐句音色控制。原生口型/音质不达标 → 按 degrade_plan 本镜回退配音先行。若 `视频模型路由=固定生视频模型` 或身份优先模板导致说话镜不能走 `native_speech`，router 必须写 `requires_voice_fallback=true` + `fallback_production_mode=voice_first`，gate 会强制先补真实 n2d-voice 配音，避免“无声对白镜”。**动作/空镜等非说话镜不变。** native_speech / lipsync 镜的真人音色克隆仍需授权（compliance gate）。
- **身份优先级**：含主要角色且高风险角度/多人互动时，优先选择有 `Character ID / Face Lock / reference controls` 可用的后端；没有 registered/ready 状态时，在实现分解方案里写明首尾帧 + reference_group 或拆镜。
- **逐镜角色绑定是机器字段**：含身份要求的 route 必须写 `clip_characters[]`，从 `storyboard.json` 的 `characters/character_ids/cast/subjects/character_refs` 或文本里的 `CHAR_xx/形态` 提取。gate 会用它把身份锁检查缩到本 Clip 实际角色；缺该字段的身份镜会被要求重跑 router。
- **接力镜 → 双关键帧（seam_relay，2026 起一等公民）**：接力/无缝镜（`continuity.need_endframe=true` 或 transition∈接力/relay/seamless）路由会带 `seam_relay` 子表。`backend_supports_dual_keyframe`（首尾硬约束插值：即梦 multiframe / 可灵 O3 的 `first_last_frame|native_multiframe`）的后端做 primary → `seam_guaranteed=true`：把上一镜尾帧作本镜首帧**硬约束**插值，接缝结构保证、且**边界帧两镜复用省一次出图**；primary 不支持则从 fallback 挑一个支持的（`dual_keyframe_fallback`）并在 rationale 里提示改用它。注意这是**预防侧**——落档侧 `temporal_consistency` 接缝机检照常 block（双关键帧镜接缝仍漂=后端没真消费尾帧/被拆段，是真故障，不因「声明了」就放过）。
- **QC 失败自动升锁（E4·闭环）**：`route_episode` 开跑先读 `生产数据/production_events.jsonl`，按 clip 聚合**本集 identity 失败次数**（redraw status=fail / qa_gate block 且原因命中脸/身份关键词）。某镜 ≥2 次 → `escalate_identity_for_failures` 自动升锁：`identity_requirement=native_identity_lock_required` + `risk_flag=identity_escalated`，primary 无原生身份锁(Character ID/Face Lock)时换成有的后端（**固定后端模式只收紧 requirement + 提示手动换厂/补 ref/拆镜，绝不擅自换厂**）。把"反复崩脸还路由到同一弱锁后端白烧"的静态盲点闭环。
- **失败可回滚**：每条路由都写 fallback 和 `degrade_plan`（实现分解/回退方案），让 n2d-batch 只重跑受影响 Clip。
- **空间复杂镜 → 评估世界模型类后端（spatial-heavy·新兴能力·防过期）**：同场景多镜需 **3D 空间一致 + 道具恒存**的镜——长连续运镜、绕物/环绕运镜、可探索环境、镜头穿越空间——纯 2D 视频后端易出空间漂移与道具凭空增减。命中这类镜时，在 fallback/rationale 里**提示评估世界模型类能力后端**（采集 2026-06-19：Kling 3.0 原生多镜+主体锁、Genie 3 类、NVIDIA Cosmos、Marble，原生维护 4D 空间与 object permanence）。**这类后端仍新兴、未必接入 n2d 渠道**：先作 primary 候选**评估**、不擅自硬切，落地前以 `n2d-video/references/platforms.md` 官方能力档案复核（与模型矩阵「二、视频」同源）。判定走能力档案，不 hardcode 厂商名。
- **质量档路由（成本×质量轴·2026-06-19 流程自审落地）**：Seedance 家族有 fast/pro 档（fast≈$0.022/s 量产默认，pro 留吃重镜）。每条路由出 `quality_tier`：身份/物理吃重镜（脸/接触/多人/原生台词/已升锁）→ `high`（值 pro 把脸与运动钉稳），空镜/通用低风险镜 → `fast`（量产省成本），后端无档位能力 → `n/a`。**只表达路由意图，不写死 model_version**——落档侧出片脚本把 `high→pro`、`fast→fast` 解析成实际质量档；成本事件带 `quality_tier` 时 `n2d-dashboard` 的 `cost_by_provider` 按 `provider@tier:unit` 拆出同后端 fast vs pro 花销，让成本×质量轴可回看。判据走 shot_type + risk_flags，不 hardcode 厂商。
- **时效档路由（成本轴·与质量档正交·2026-06-22 落地选择点 `投放时效`）**：2026 视频 API 首现「batch/隔夜半价」（Sora2 Batch 24h SLA -50%、Seedance flex -50% 预告）。`urgency_tier_from_settings` 读 `_设置.md` 的 `投放时效`（实时/隔夜批量）→ 项目级 `urgency_tier`（`realtime` 默认 / `batch_24h`），写进 plan 顶层 + 逐镜留痕。成本事件带 `urgency_tier=batch_24h` 时 `n2d-dashboard` 的 `cost_by_provider` 按 `provider#batch_24h:unit` 拆 realtime vs batch 花销，回看「隔夜批量省了多少」。**诚实边界**：本档只产**路由意图 + 成本拆账**；实际 async batch endpoint 由视频后端能力决定，属执行适配层 follow-up（后端 batch 通道接入后才真省）。默认 `实时`——绝不静默把赶投放的集延迟到隔夜。
- **batch 提交清单 + 折扣投影（F4·2026-06-26）**：`python3 batch_plan.py <作品根> 第N集 [--rate 每秒成本] [--unit 单位]` 读 `video_model_routes.json` 收 `urgency_tier=batch_24h` 的 clip，产 `生产数据/batch_submission_plan_第N集.json`——① 后端接入 batch endpoint 时消费的**提交清单**（哪些 clip 走 batch 异步提交·文件契约 seam）② **折扣投影**（`N2D_BATCH_DISCOUNT` 默认 0.5=-50%）。**诚实**：不调用任何后端 API、**不臆造各家单价**（2026 多源价格互相打架）——要 ¥ 估算请 `--rate` 按当前官方价填，不传则只报「可走 batch 的镜数/总秒数/折扣率」。与 dashboard 按 urgency_tier 拆 realtime vs batch 的**实际**成本账互补（一个事前投影、一个事后对账）。
- **视频运动参考（reference_video_motion·跨镜运动连续性轴）**：长连续运动镜（追逐/飞行/打斗）且 primary 支持 `reference_video_motion`（Seedance/Kling）时，路由 `motion_reference.applicable=true` + `risk_flag=motion_reference_candidate`，提示把**同段前一条已通过 clip 作运动/风格视频参考**喂进后端，锁运镜节奏与运动风格（与图身份锁正交）。首条镜无前序参考自然跳过；这是预防侧指引，不强制。
- **开源轨迹控制增强（P3·可选）**：router 写完后可跑 `python3 skills/n2d-model-router/scripts/trajectory_controller_plan.py <作品根> 第N集 --write`。它读取 `execution_recipe.control_inputs.required_inputs`，按 `camera_path/spatial_path` 选择 MotionCtrl / CameraCtrl / DragNUWA 候选，只有本机设置 `MOTIONCTRL_HOME` / `CAMERACTRL_HOME` / `DRAGNUWA_HOME` 时才标 `ready_to_run`；未准备环境只写 `planned_env_missing`，不下载、不强接、不阻断主流程。
- **多镜单次生成候选组（multishot_groups·advisory）**：Seedance 2.0 等可一次出多镜头叙事且跨镜一致、无缝转场。primary 全部定稿后（route_episode 末尾），扫**连续 ≥2 条接力镜 + 同一支持多镜的 primary**（如直连 Seedance 的项目）→ 标 `multishot_candidate` + 进 `multishot_groups`。**这段最适合一次 co-generate 消缝、最稳跨镜一致，但只是提示**：不合并 Clip、不改 primary/mode，逐 Clip 仍是独立可追踪可重跑单元（模型矩阵立身原则），是否真合并由出片侧/用户按接缝风险与重跑需求决定。**组大小受物理约束封顶**——单次多镜总输出 ≤ 后端 `max_clip_seconds`（Seedance ~15s），按累计时长切组（缺时长退 ≤4 成员护栏），所以镜本身已近单镜上限时不会成组（甜点是多个短接力镜）。即梦渠道下执行后端是 dreamina（非多镜叙事核验渠道）→ 保守不标注。

## 工作流

### 1. 读取输入

必读：

- `<作品根>/_设置.md`：`生视频模型`、`生视频渠道`、`视频模型路由`、`视频备用后端`（固定模式可设 `无`）、`制作模式`（=原生音画→说话镜走 native_speech）、`视频原生音轨`、`对口型`。旧 `生视频AI` 兼容读取。
- `<作品根>/脚本/第N集/storyboard.json`：`clips[]`、`template`、`template_contract`、时长、场景、动作文字。
- `<作品根>/出图/共享/identity_registry.json`：角色 ID / Face Lock / reference controls 状态。
- `skills/n2d-video/references/platforms.md`：后端能力档案。
- `skills/n2d/references/模型矩阵.md`：版本快照，只用来更新档案，不把版本号硬塞进逐 Clip prompt。

### 2. 生成路由表

运行：

```bash
python3 skills/n2d-model-router/scripts/router.py <作品根> 第N集 --write
```

输出：

- `出视频/第N集/prompt/video_model_routes.json`
- `出视频/第N集/prompt/video_model_routes.md`

`video_model_routes.json` 是机器真值，`video_model_routes.md` 供人审。字段约定见 `references/schema.md`。

### 3. 路由基线

| 镜头类型 | primary | fallback | 适配理由 |
|---|---|---|---|
| 打斗 / 命中 / 多主体接触 | Kling | Seedance / Dreamina | 首尾帧、运动笔刷、Character ID、多主体互动更重要；`motion_control=required`；`action_choreography=required` |
| 追逐 / 飞行 / 长连续运动 | Seedance | Kling | 长单镜、连续运镜、背景运动更重要；`motion_control=required`；`action_choreography=required`；优先视频运动参考 |
| 对话反打 / 说话近景 | Kling | Veo / Seedance | 口型/身份锁定/角色稳定优先；若海外或原生口型 opt-in 可切 Veo |
| 对话反打 / 说话近景（`配音先行`+`对口型≠关闭`） | Seedance / 可灵 Omni | Kling / Veo | `mode=voice_conditioned_lipsync`：把配音 `line_NN.wav` 当口型条件喂进支持音频参考的后端，音轨仍走配音轨（不双人声、省后期对口型 pass） |
| 真相揭示 / 身份曝光 | Kling | Veo / Seedance | 证据物稳定、反应链、脸部微表情和台词口型优先；通常走 high 档 |
| 公开对质 / 审讯 / 谈判 | Kling | Seedance / Veo | 多人空间层级、裁决者/证人/对手反应和台词密度优先；必要时拆正反打 |
| 关系转折 / 告白 / 决裂 / 和解 | Kling | Veo / Seedance | 微表情、关系距离、称谓/台词和身份稳定优先；大表情跨度需首尾帧或 MCU 保真实现 |
| 空镜 / 转场 / 氛围远景 | Veo 或 Seedance | Dreamina | 可 opt-in 环境声/动作音效；无人物时一致性风险低 |
| 法术爆发 / 特效扩散 | Seedance | Kling / Dreamina | 光效扩散、连续动态、长一点的能量 buildup 更重要 |
| 亲密互动 / 近距离肢体接触 | Kling | Seedance | 接触关系、遮挡、多人脸稳定优先；`motion_control=required`；不稳就拆成反打/手部/空镜，保留亲密互动 beat |
| 拥抱 / 拉扯 / 抓腕 | Kling | Seedance + 拆镜 | 明确接触点、力量方向和释放帧；`motion_control=required`；不稳就拆手部特写/反打/释放帧，保留力量关系 |
| 多人同框 | Kling | Seedance + 拆镜 | 角色槽位、脸优先级、多参考/主体控制优先；错脸就拆 OTS/反打或分区构建 |
| 群像站位 / 队列 / 围堵 | Kling | Seedance + 拆镜 | 主次层级和背景人简化优先；同框人数过多时拆成 establish + 反打 + 群体反应，不删人数/站位功能 |
| 普通单人运动 | 项目默认 `生视频模型` | Seedance / Kling | 成本和速度优先，必要时按失败原因升级 |

这张表是能力路由，不是永久品牌铁律。后端能力变了，先改 `references/platforms.md` 和本 skill，再同步 Q&A/README。

**跨集后端锁（`设定库/model_routes_baseline.json`）**：上表是"每集按 shot_type 各自路由"，但同一 shot_type 在不同集若漂到不同后端，同角色跨集会风格/质感漂移。第1集打样后把 `shot_type → primary_backend` 锁成跨集基线，后续集自动锚定同一后端：

```bash
# 第1集打样：锁基线（用本集自然路由抽 shot_type→后端）
python3 skills/n2d-model-router/scripts/router.py <作品根> 第1集 --write --write-baseline
# 后续集：默认读 设定库/model_routes_baseline.json 锚定 primary（原自然后端降为 fallback 保留，不丢）
python3 skills/n2d-model-router/scripts/router.py <作品根> 第2集 --write
#   --no-anchor 可临时不锚定；后端能力升级想换基线时重跑首集 --write-baseline 刷新
```

锚定时若本集某 clip 的自然路由与基线不符，会在 `video_model_routes.json.baseline_drift` 留痕，并由 video gate 复核。baseline 的优先级低于固定模式和一角一后端亲和：固定模式或 `locked_backend` 冲突时只写 `baseline_deferred` + risk flag，不改 primary；普通自动路由才按基线锚定，原后端进 fallback。高风险/含角色镜头的漂移默认 BLOCK；只有结构化 `baseline_override` 覆盖当前 `clip_id` 且未过期时才降级为 WARN：

```json
{
  "baseline_override": {
    "accepted": true,
    "reviewer": "producer_or_qa",
    "reason": "本集动作镜为满足 Motion Control 临时换后端，已人工确认角色一致性",
    "expires_at": "2099-01-01",
    "affected_routes": ["Clip_01"]
  }
}
```

**③ 一角一后端亲和（核心硬钉）**：基线按 `shot_type` 锁后端，但同一**核心角色**若跨镜被不同 shot_type 路由到不同后端，脸质感会漂。router 读 `identity_registry`，对**已注册原生视频主体**（Character ID / face_lock，status registered/ready）的角色，逐镜对账"该角色原生主体后端 vs 本镜 primary"。核心/主演角色冲突时，router 会把本镜 `primary_backend` **硬钉**到该角色的原生主体后端，原 primary 降为 fallback，并在 rationale 留痕；若 baseline 或 benchmark 想改走别的后端，只能写 deferred/override，不得静默覆盖这个锁。若同镜多个原生主体无法同时满足，则保留 `character_backend_conflicts` + risk_flag `character_backend_conflict`，video gate 出「一角一后端」WARN，要求拆正反打/分区。没注册原生主体的角色零告警（避免噪音）。

### 4. 接入 n2d-video

`n2d-video` 生成 `00_总览.md` 前先生成路由表；`00_总览.md` 必须包含「本集模型路由表」；每个 Clip prompt 必须包含：

- `**模型路由**`：shot_type、primary、fallback、mode、rationale、degrade_plan（实现分解/回退方案）。
- `**动作编排契约 / Action Choreography**`：打斗/追逐/飞行必填，普通镜写“无”；写 beats、speed_curve、spatial_path、camera_path、readability_beats、degrade_plan（实现分解/回退方案）和模板专属字段。
- `**Motion Control / 物理交互控制**`：高危动作/物理镜必填，普通镜写“无”；写 `level`、`manifest_path`、`required_inputs`、`failure_modes`、`gate_policy`。
- 中文 prompt 里的 `模型路由约束`：说明按哪个后端写平台参数，不能把 Kling/Seedance/Veo/Dreamina 的能力词混成一坨。
- 中文 prompt 里的 `物理交互约束`：说明该镜使用 ready 控制资产，或按 `degrade_only` manifest 执行实现分解/拆镜；不得只靠文本 prompt 生成全身复杂接触。
- `平台参数`：primary_backend、fallback_backends、mode、duration、resolution、identity adapter、native_audio policy。

`dashboard.py gate --stage video`（生产入口，底层调 `n2d-review/scripts/gate.py --json`）会阻断缺路由的 prompt。

### 5. 失败回流

生成失败或审片失败后，把失败原因写入生产数据：

- 动作崩 / 肢体扭曲：改路由到强运动后端或拆镜。
- FeatureMelting / 手脚融合 / 接触穿模：补 `motion_control_manifest.json` 的 pose/depth/instance/contact 控制资产；若暂不接可控后端，改 `status=degrade_only` 并按模板拆成手部/反打/释放帧，保留动作目标。
- 脸漂 / 多人错脸：改路由到有身份注册能力的后端，或补 registry，再重跑受影响 Clip。
- 原生人声误入：取消 native audio opt-in，回默认配音链路。
- 时长超限 / 运动不连贯：切长单镜后端或按模板拆成 2-3 个短 Clip。

再用 `n2d-batch` 只重排受影响 Clip，不整集重来。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 不看 storyboard 就临场路由 | 复杂镜若在 `storyboard.json` 命中了专项模板，路由必须继承模板的指导 |
| 固定单一后端包打天下 | `生视频模型` 的全局默认只做普通镜和兜底，除非用户明确要求“固定生视频模型”，否则应自动按能力打散 |
| 把 `native_av` 混用于不兼容后端 | 原生音画需要支持台词生成的模型（如 Veo 3 / Seedance 2.0），乱选会导致无声或回退配音先行 |
| 缺 Motion Control 时强行出视频 | 高危动作/物理镜（打斗、追逐、飞行、拥抱等）如果没有 ready/degrade_only 的 manifest，会被 gate 直接拦截 |
| 动作 prompt 只写“精彩打斗/高速飞行” | 高动作镜必须写 `action_choreography` 对应的速度曲线、空间路径、镜头路径、可读性节拍和专属字段 |
