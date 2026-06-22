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
5. 失败时怎么降级或拆镜。
6. prompt / 平台参数 / gate 要怎样执行这条路由。

## 触发

- 用户说：模型适配层、model routing、模型路由、后端路由、视频模型选择、不要固定一个视频模型。
- `n2d-video` 生成视频 prompt 前，尤其本集有打斗、追逐、对话反打、真相揭示/身份曝光、公开对质/审讯/谈判、关系转折、飞行、空镜、法术爆发、亲密互动、拥抱拉扯、多人同框、群像站位。
- `n2d-review` 发现某类镜头在同一后端反复失败，需要沉淀成路由规则。

## 输入 / 输出 / 读写边界

- **输入**：`_设置.md`、`storyboard.json`、`identity_registry.json`、视频模型/渠道能力档案、跨集路由基线。
- **输出**：`出视频/第N集/prompt/video_model_routes.json` 和 `.md`，第 1 集打样后写 `设定库/model_routes_baseline.json`。第 2 集起凡含核心/角色身份或高风险镜头（打斗/追逐/多人/揭示/对质/关系转折等），`n2d-review gate` 会要求路由按该基线锚定；自然路由漂移需刷新基线或写结构化 `baseline_override`（`accepted/reviewer/reason/expires_at/affected_routes`）。
- **读写边界**：只写路由表和基线；不生成视频、不改 `_进度.md`、不替 `n2d-video` 写最终 clip prompt。
- **契约关系**：模型路由是 `skills/n2d/_lib/n2d_contract.py` 的横切工具（`CROSS_CUTTING_TOOLS`），不是进度 readiness 项；motion control / native AV / lipsync 判定必须复用契约常量。

## 核心原则

- **能力先于品牌**：先判断镜头需要“强运动 / 长单镜 / 口型 / 原生环境声 / 角色 ID / 首尾帧 / 多主体互动”等能力，再映射到当前模型。版本名只放在 `n2d/references/模型矩阵.md` 快照里。
- **项目默认只做兜底**：`_设置.md` 的 `生视频模型` 是默认/兜底，不再固定所有 Clip；`生视频渠道` 只决定实际去哪调用。旧 `生视频AI` 兼容读取。除非 `视频模型路由=固定生视频模型`，否则按本层自动路由。
- **固定模式最高优先**：`视频模型路由=固定生视频模型` 时，用户选定模型优先于 native AV / 对口型自动抢路由；需要原生音画时应关闭固定模式或显式改默认模型，不得悄悄切到其它 native_speech 后端。若本机只有一个可用 CLI/渠道，可在 `_设置.md` 写 `视频备用后端=无`，固定模式不得把不可执行后端写成 fallback。旧值 `固定生视频AI` 兼容。
- **复杂镜不从零写**：若 `storyboard.json clips[].template` 已命中专项模板，路由必须继承模板，不靠 prompt 现场猜。
- **物理交互不靠文本猜**：打斗命中、拥抱、抓腕、拉扯、近距离接触等 `physical_interaction` 镜头必须输出 `motion_control.level=required` 和 `manifest_path`。视频 gate 会要求该 manifest 为 `ready`（有 pose/depth/instance/contact 控制资产）或 `degrade_only`（明确拆成手部特写/反打/释放帧），缺 manifest 不进入付费出视频。`ready` 控制资产用本地 `path/glob` 时必须能匹配真实文件；用远端 `uri` 时必须是 `https/s3/gs`，并带 `verified_at=YYYY-MM-DD` + `sha256/checksum/etag` 之一，裸 URI 或 `file://` 不放行。
- **控制资产脚手架（补"只 gate 不生成"的摩擦）**：路由只声明、gate 只校验，中间用 `scripts/motion_control.py` 把骨架和清单补上，别让操作者照 schema 手搓 JSON：
  - `python3 scripts/motion_control.py <作品根> 第N集 scaffold [--clip Clip_03]` —— 读 `video_model_routes.json`，为每个 `level=required` 的 Clip 生成/合并一份**非 ready 骨架** manifest（`status=planned`、逐 input `status=missing`+规范路径，已填字段不回退），并打印"该 Clip 还要产出哪几个控制文件 + 接触语义字段"的精确清单。骨架仍被 gate 阻断（这是对的：还没就位）。
  - `python3 scripts/motion_control.py <作品根> 第N集 check` —— 对照磁盘：文件已就位的 input 客观翻 `ready`（**不**自动翻顶层 status——`contact_points/occlusion_order/body_part_ownership` 语义要人确认后手改 ready），报告 gate 会不会过。
  - `python3 scripts/motion_control.py <作品根> 第N集 generate [--clip ...] [--no-cache]` —— 可选：装 `controlnet_aux`(DWPose)/depth 库时从首/尾帧抽 pose/depth 种子帧；缺库优雅跳过、显式标，`instance_masks/contact_map` 始终留人工（需 SAM+人定接触点）。**步内指纹缓存**：抽前先对「源首/尾帧 PNG 内容 SHA + 抽取参数」算 git-free 指纹（复用 `n2d/_lib/skill_snapshot.artifact_fingerprint`，与 n2d-update `inputs_fingerprint` 同源），写进 manifest 的 `generate_cache.<input>`；重跑该镜时指纹未变且产物已在 → 复用不重算，只有源帧/参数变了或产物缺失才重抽。诚实：指纹缺失/失配/产物不在一律当需重抽，绝不臆造跳过。强制重抽用 `--no-cache` 或 `N2D_MOTION_CONTROL_NO_CACHE=1`（留痕）。
  - 输出形状与 gate `check_motion_control_manifest` 单一真值源对齐（已交叉验证：planned 阻断 / 填齐 ready 放行 / degrade_only+plan 放行）。
- **T2V 原生动作通道 (Mid-term Upgrade · 解锁物理引擎)**：对于标记为 `fight_exchange`（打斗）、`chase`（追逐）等高动量/复杂物理镜头，若 `_设置.md` 开启了 `T2V动作通道=开启`，路由将优先切换至 `mode=text2video`。**收益**：解除武打戏对静态首帧起幅的强物理约束，让 Veo 3 / Seedance 等当前可执行后端的原生物理能力从头演算动量与物理反馈，减少“幻灯片微动”感。Sora 已是 legacy/manual-only，不进自动路由示例。**执行**：路由至 T2V 时，`n2d-image` 将跳过首帧生成（或仅作为参考）；`n2d-video` 闸门将自动豁免 `firstframe_png` 存在性校验。
- **mouth_visible 自动预填**：`scripts/mouth_detect.py <作品根> 第N集` 为每 Clip 预填/复核 `mouth_visible`（决定原生音画 opt-in 与是否要口型同步）。文本端复用 `clip_has_mouth_visible`（单一真值源），图像端装 insightface 时从首帧 PNG 用 106 关键点判正脸+嘴可见（缺库优雅回退文本端、标 `image=unknown`，绝不臆造）。图↔文本/图↔prompt 不一致标 warn（以图为准），省得逐镜手判后还填错原生音画策略。
- **三条音画路线，按 `制作模式` + `对口型` 选（避免被代差绕过）**：
  - **`配音先行`（强配音控制模式）**：说话镜由配音链路控制，**不让视频模型生成台词**；只有空镜/远景/无口型低风险镜头可 opt-in 原生环境声/音效（`ambience/native_sfx`）。
  - **`配音先行 + 对口型 opt-in`（voice_conditioned_lipsync）**：`制作模式=配音先行` 且 `对口型≠关闭` 时，**说话镜（对话反打/说话特写/mouth_visible）路由 `mode=voice_conditioned_lipsync`、`native_audio_policy=lipsync_condition_only`**，primary 选支持音频参考口型的后端（Seedance 2.0 音素级 / 可灵 Omni，见 `LIPSYNC_AUDIO_REF_BACKENDS`），把本镜配音 `line_NN.wav` 当**口型条件**喂进去同帧出对口型画面。**关键：音轨仍是 voice-first 克隆音色（compose 用配音轨），模型音频只作口型条件、不接管声音**——既不双人声、又省一道后期 MuseTalk/Wav2Lip 对口型 pass。后端不支持音频参考口型 → 按 degrade_plan 回退「image2video 静音 + 后期对口型 pass」或分镜规避。这是 native_av 与「配音→后期对口型」之间的中间路线。
  - **`原生音画`（native AV·opt-in 整剧）**：`制作模式=原生音画` 时，**说话镜路由到原生同步音画后端**（Seedance 2.0 / Veo 3，见 `NATIVE_AV_BACKENDS`），`mode=native_av`、`native_audio_policy=native_speech`，一次出台词+口型+环境声，**绕过配音先行的时长清单**（台词文本/情绪/单镜时长来自脚本）。Sora legacy/manual-only，不进入 `NATIVE_AV_BACKENDS`。规避「配音→对口型」代差与占位返工；代价是少了逐句音色控制。原生口型/音质不达标 → 按 degrade_plan 本镜回退配音先行。**动作/空镜等非说话镜不变。** native_speech / lipsync 镜的真人音色克隆仍需授权（compliance gate）。
- **身份优先级**：含主要角色且高风险角度/多人互动时，优先选择有 `Character ID / Face Lock / reference controls` 可用的后端；没有 registered/ready 状态时，在降级方案里写明首尾帧 + reference_group 或拆镜。
- **逐镜角色绑定是机器字段**：含身份要求的 route 必须写 `clip_characters[]`，从 `storyboard.json` 的 `characters/character_ids/cast/subjects/character_refs` 或文本里的 `CHAR_xx/形态` 提取。gate 会用它把身份锁检查缩到本 Clip 实际角色；缺该字段的身份镜会被要求重跑 router。
- **接力镜 → 双关键帧（seam_relay，2026 起一等公民）**：接力/无缝镜（`continuity.need_endframe=true` 或 transition∈接力/relay/seamless）路由会带 `seam_relay` 子表。`backend_supports_dual_keyframe`（首尾硬约束插值：即梦 multiframe / 可灵 O3 的 `first_last_frame|native_multiframe`）的后端做 primary → `seam_guaranteed=true`：把上一镜尾帧作本镜首帧**硬约束**插值，接缝结构保证、且**边界帧两镜复用省一次出图**；primary 不支持则从 fallback 挑一个支持的（`dual_keyframe_fallback`）并在 rationale 里提示改用它。注意这是**预防侧**——落档侧 `temporal_consistency` 接缝机检照常 block（双关键帧镜接缝仍漂=后端没真消费尾帧/被拆段，是真故障，不因「声明了」就放过）。
- **QC 失败自动升锁（E4·闭环）**：`route_episode` 开跑先读 `生产数据/production_events.jsonl`，按 clip 聚合**本集 identity 失败次数**（redraw status=fail / qa_gate block 且原因命中脸/身份关键词）。某镜 ≥2 次 → `escalate_identity_for_failures` 自动升锁：`identity_requirement=native_identity_lock_required` + `risk_flag=identity_escalated`，primary 无原生身份锁(Character ID/Face Lock)时换成有的后端（**固定后端模式只收紧 requirement + 提示手动换厂/补 ref/拆镜，绝不擅自换厂**）。把"反复崩脸还路由到同一弱锁后端白烧"的静态盲点闭环。
- **失败可回滚**：每条路由都写 fallback 和 degrade plan，让 n2d-batch 只重跑受影响 Clip。
- **空间复杂镜 → 评估世界模型类后端（spatial-heavy·新兴能力·防过期）**：同场景多镜需 **3D 空间一致 + 道具恒存**的镜——长连续运镜、绕物/环绕运镜、可探索环境、镜头穿越空间——纯 2D 视频后端易出空间漂移与道具凭空增减。命中这类镜时，在 fallback/rationale 里**提示评估世界模型类能力后端**（采集 2026-06-19：Kling 3.0 原生多镜+主体锁、Genie 3 类、NVIDIA Cosmos、Marble，原生维护 4D 空间与 object permanence）。**这类后端仍新兴、未必接入 n2d 渠道**：先作 primary 候选**评估**、不擅自硬切，落地前以 `n2d-video/references/platforms.md` 官方能力档案复核（与模型矩阵「二、视频」同源）。判定走能力档案，不 hardcode 厂商名。
- **质量档路由（成本×质量轴·2026-06-19 流程自审落地）**：Seedance 家族有 fast/pro 档（fast≈$0.022/s 量产默认，pro 留吃重镜）。每条路由出 `quality_tier`：身份/物理吃重镜（脸/接触/多人/原生台词/已升锁）→ `high`（值 pro 把脸与运动钉稳），空镜/通用低风险镜 → `fast`（量产省成本），后端无档位能力 → `n/a`。**只表达路由意图，不写死 model_version**——落档侧出片脚本把 `high→pro`、`fast→fast` 解析成实际质量档；成本事件带 `quality_tier` 时 `n2d-dashboard` 的 `cost_by_provider` 按 `provider@tier:unit` 拆出同后端 fast vs pro 花销，让成本×质量轴可回看。判据走 shot_type + risk_flags，不 hardcode 厂商。
- **时效档路由（成本轴·与质量档正交·2026-06-22 落地选择点 `投放时效`）**：2026 视频 API 首现「batch/隔夜半价」（Sora2 Batch 24h SLA -50%、Seedance flex -50% 预告）。`urgency_tier_from_settings` 读 `_设置.md` 的 `投放时效`（实时/隔夜批量）→ 项目级 `urgency_tier`（`realtime` 默认 / `batch_24h`），写进 plan 顶层 + 逐镜留痕。成本事件带 `urgency_tier=batch_24h` 时 `n2d-dashboard` 的 `cost_by_provider` 按 `provider#batch_24h:unit` 拆 realtime vs batch 花销，回看「隔夜批量省了多少」。**诚实边界**：本档只产**路由意图 + 成本拆账**；实际 async batch endpoint 由视频后端能力决定，属执行适配层 follow-up（后端 batch 通道接入后才真省）。默认 `实时`——绝不静默把赶投放的集延迟到隔夜。
- **视频运动参考（reference_video_motion·跨镜运动连续性轴）**：长连续运动镜（追逐/飞行/打斗）且 primary 支持 `reference_video_motion`（Seedance/Kling）时，路由 `motion_reference.applicable=true` + `risk_flag=motion_reference_candidate`，提示把**同段前一条已通过 clip 作运动/风格视频参考**喂进后端，锁运镜节奏与运动风格（与图身份锁正交）。首条镜无前序参考自然跳过；这是预防侧指引，不强制。
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
| 打斗 / 命中 / 多主体接触 | Kling | Seedance / Dreamina | 首尾帧、运动笔刷、Character ID、多主体互动更重要；`motion_control=required` |
| 追逐 / 飞行 / 长连续运动 | Seedance | Kling | 长单镜、连续运镜、背景运动更重要 |
| 对话反打 / 说话近景 | Kling | Veo / Seedance | 口型/身份锁定/角色稳定优先；若海外或原生口型 opt-in 可切 Veo |
| 对话反打 / 说话近景（`配音先行`+`对口型≠关闭`） | Seedance / 可灵 Omni | Kling / Veo | `mode=voice_conditioned_lipsync`：把配音 `line_NN.wav` 当口型条件喂进支持音频参考的后端，音轨仍走配音轨（不双人声、省后期对口型 pass） |
| 真相揭示 / 身份曝光 | Kling | Veo / Seedance | 证据物稳定、反应链、脸部微表情和台词口型优先；通常走 high 档 |
| 公开对质 / 审讯 / 谈判 | Kling | Seedance / Veo | 多人空间层级、裁决者/证人/对手反应和台词密度优先；必要时拆正反打 |
| 关系转折 / 告白 / 决裂 / 和解 | Kling | Veo / Seedance | 微表情、关系距离、称谓/台词和身份稳定优先；大表情跨度需首尾帧或降级 MCU |
| 空镜 / 转场 / 氛围远景 | Veo 或 Seedance | Dreamina | 可 opt-in 环境声/动作音效；无人物时一致性风险低 |
| 法术爆发 / 特效扩散 | Seedance | Kling / Dreamina | 光效扩散、连续动态、长一点的能量 buildup 更重要 |
| 亲密互动 / 近距离肢体接触 | Kling | Seedance | 接触关系、遮挡、多人脸稳定优先；`motion_control=required`；不稳就拆成反打/手部/空镜 |
| 拥抱 / 拉扯 / 抓腕 | Kling | Seedance + 拆镜 | 明确接触点、力量方向和释放帧；`motion_control=required`；不稳就拆手部特写/反打/释放帧 |
| 多人同框 | Kling | Seedance + 拆镜 | 角色槽位、脸优先级、多参考/主体控制优先；错脸就拆 OTS/反打 |
| 群像站位 / 队列 / 围堵 | Kling | Seedance + 拆镜 | 主次层级和背景人简化优先；同框人数过多时拆成 establish + 反打 + 群体反应 |
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

锚定时若本集某 clip 的自然路由与基线不符，会在 `video_model_routes.json.baseline_drift` 留痕，并由 video gate 复核（基线胜，原后端进 fallback）。高风险/含角色镜头的漂移默认 BLOCK；只有结构化 `baseline_override` 覆盖当前 `clip_id` 且未过期时才降级为 WARN：

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

**③ 一角一后端亲和（核心硬钉）**：基线按 `shot_type` 锁后端，但同一**核心角色**若跨镜被不同 shot_type 路由到不同后端，脸质感会漂。router 读 `identity_registry`，对**已注册原生视频主体**（Character ID / face_lock，status registered/ready）的角色，逐镜对账"该角色原生主体后端 vs 本镜 primary"。核心/主演角色冲突时，router 会把本镜 `primary_backend` **硬钉**到该角色的原生主体后端，原 primary 降为 fallback，并在 rationale 留痕；若同镜多个原生主体无法同时满足，则保留 `character_backend_conflicts` + risk_flag `character_backend_conflict`，video gate 出「一角一后端」WARN，要求拆正反打/分区。没注册原生主体的角色零告警（避免噪音）。

### 4. 接入 n2d-video

`n2d-video` 生成 `00_总览.md` 前先生成路由表；`00_总览.md` 必须包含「本集模型路由表」；每个 Clip prompt 必须包含：

- `**模型路由**`：shot_type、primary、fallback、mode、rationale、degrade_plan。
- `**Motion Control / 物理交互控制**`：高危接触镜必填，普通镜写“无”；写 `level`、`manifest_path`、`required_inputs`、`failure_modes`、`gate_policy`。
- 中文 prompt 里的 `模型路由约束`：说明按哪个后端写平台参数，不能把 Kling/Seedance/Veo/Dreamina 的能力词混成一坨。
- 中文 prompt 里的 `物理交互约束`：说明该镜使用 ready 控制资产，或按 `degrade_only` manifest 拆镜；不得只靠文本 prompt 生成全身复杂接触。
- `平台参数`：primary_backend、fallback_backends、mode、duration、resolution、identity adapter、native_audio policy。

`dashboard.py gate --stage video`（生产入口，底层调 `n2d-review/scripts/gate.py --json`）会阻断缺路由的 prompt。

### 5. 失败回流

生成失败或审片失败后，把失败原因写入生产数据：

- 动作崩 / 肢体扭曲：改路由到强运动后端或拆镜。
- FeatureMelting / 手脚融合 / 接触穿模：补 `motion_control_manifest.json` 的 pose/depth/instance/contact 控制资产；若暂不接可控后端，改 `status=degrade_only` 并按模板拆成手部/反打/释放帧。
- 脸漂 / 多人错脸：改路由到有身份注册能力的后端，或补 registry，再重跑受影响 Clip。
- 原生人声误入：取消 native audio opt-in，回默认配音链路。
- 时长超限 / 运动不连贯：切长单镜后端或按模板拆成 2-3 个短 Clip。

再用 `n2d-batch` 只重排受影响 Clip，不整集重来。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 不看 storyboard 就临场路由 | 复杂镜若在 `storyboard.json` 命中了专项模板，路由必须继承模板的指导 |
| 固定单一后端包打天下 | `生视频模型` 的全局默认只做普通镜和兜底，除非用户明确要求“固定生视频模型”，否则应自动按能力打散 |
| 把 `native_av` 混用于不兼容后端 | 原生音画需要支持台词生成的模型（如 Veo 3 / Seedance 2.0），乱选会导致无声或降级 |
| 缺 Motion Control 时强行出视频 | 高危接触（打斗、拥抱等）如果没有 ready/degrade_only 的 manifest，会被 gate 直接拦截 |
