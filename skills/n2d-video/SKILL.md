---
name: n2d-video
description: Stage 5 of n2d pipeline — for a 作品 episode whose 出图(PNG) is done, run/consume n2d-model-router, generate per-Clip video prompts from 故事板.md + video_model_routes.json, machine-check 出图→出视频 视觉契约继承 (scripts/inherit_contract.py 逐字段 Diff，光位锚/轴线漂移=block), then invoke a local video-gen CLI/API channel (Dreamina/即梦, Kling, Veo/Gemini, Seedance, manual) or guide manual generation. Writes progress to `_进度.md` (视频 column). Use when asked to 出视频, 视频 prompt, 生成视频, 跑视频, image2video, model routing, 契约继承校验, or anything video-generation-related for a n2d project. Triggers 出视频, 视频prompt, 图生视频, image2video, 即梦视频, 可灵视频, Veo, Seedance, 运镜, 模型路由, 后端路由, 契约继承.
---

# n2d-video — Stage 5：视频 prompt + 生视频

你是 **AI 漫剧出视频制作**。本 skill 只关心一件事：把 出图齐（分镜设计→出图后）的一集，先生成"开箱即用"的视频 prompt（按 Clip 维度），然后按 `_设置.md` 的 `生视频模型` + `生视频渠道` 调本机 CLI/API（或一步步指导用户在即梦/可灵/Gemini/Veo 等渠道手动跑），最后把 MP4 落档 + 更新进度。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/n2d/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`基础视觉风格`（只继承，不在本阶段重选）、`生视频模型`（普通镜/兜底模型）、`生视频渠道`（实际调用渠道/产品/API）、`视频模型路由`（默认自动按镜头路由）、`视频备用后端`（固定模式下可设 `无`，避免把本机不可用 CLI 写成 fallback）、`出视频规格`（三档预算·每次调模型/渠道前告知·见下「出视频规格」节）、`视频分辨率`、`画幅`、`对口型`、`生成粒度`、`生成优先序`、`制作模式`（决定占位闸门是否放行·见输入前置条件）、`视频原生音轨`（只由 n2d-compose 执行处理，n2d-video 阶段不剥音轨）、`目标平台`、`发行地区`、`合规用途`。后 3 项必须同步落 `合规/compliance_manifest.json`，不得只写 `_设置.md`。旧 `生视频AI` 兼容读取。

## 核心原则

- **图生视频为主，文生视频为辅**：每个 Clip 以出图阶段的 PNG 为首帧（可灵/部分平台支持首尾帧），生视频模型只控制"动作 + 运镜"。纯空镜/转场/氛围镜头可文生视频。
- **首帧崩脸 → 片崩脸（付费前置·省最贵那一步的钱）**：image2video 会**忠实把首帧缺陷动起来**，所以付费出视频前 `gate.py --stage video_preflight` 会核验输入首帧的出图落档机检——读 `image_qc` 持久化结果（`生产数据/image_qc/第N集/...json`，不重跑像素引擎）：`summary.hard_blocks>0`（崩脸/接缝断/降级精度近景/非法 CHAR）**BLOCK**，回 n2d-image 修复并重跑 image_qc 再出视频；缺 image_qc 结果或帧晚于上次 QC（出图后改过帧）则 **WARN**。别花最贵工位的钱去动画一张未验/崩脸的首帧。
- **模型路由铁律（P1）**：默认 `视频模型路由=自动按镜头路由`，`生视频模型` 只作为普通镜和兜底模型，不再固定每个 Clip；`生视频渠道` 只决定实际调用产品/API。出视频 prompt 前必须先跑 `n2d-model-router` 生成 `video_model_routes.json/md`：打斗/追逐/对话反打/飞行/空镜/法术爆发/亲密互动/拥抱拉扯/多人同框/群像站位按能力选择 primary/fallback，并写入总览「本集模型路由表」和每个 Clip 的 `模型路由` 字段。只有账号/预算/交付明确要求单模型时，才可设 `视频模型路由=固定生视频模型`；即便固定，也要写 fallback 与降级方案。旧值 `固定生视频AI` 兼容。
- **Motion Control 前置闸门（P1.5 · 复杂物理交互）**：打斗命中、拥抱、抓腕、拉扯、近距离接触等 `physical_interaction/contact_motion` 镜头不能只靠文本 prompt 猜动作。`video_model_routes.json` 会给这类 Clip 输出 `motion_control.level=required` 和 `manifest_path`；正式付费出视频前，`gate.py --stage video_preflight` 会要求 `出视频/第N集/control/Clip_XX/motion_control_manifest.json` 为 `status=ready`（有 pose/depth/instance/contact 控制资产）或 `status=degrade_only`（明确拆成手部特写/反打/释放帧）。OpenPose/DWPose 只锁姿态，不能单独解决遮挡和肢体归属；高危接触优先补 depth/instance masks/contact_map，暂不接可控后端时必须拆镜降级。控制资产用本地 `path/glob` 时必须匹配真实文件；用远端 `uri` 时必须是 `https/s3/gs`，并带 `verified_at=YYYY-MM-DD` + `sha256/checksum/etag` 之一，裸 URI 或 `file://` 不放行。**撞 gate 别手搓 JSON**：先跑 `python3 skills/n2d-model-router/scripts/motion_control.py <作品根> 第N集 scaffold` 生成骨架 manifest + 待补清单，补齐控制资产/接触语义后 `check` 核对再改 `status=ready`（或决定拆镜改 `degrade_only`）。
- **原生音画 opt-in 铁律（P1）**：默认仍是**配音先行 + 原生音轨丢弃**；Veo / Seedance / Kling 等后端的原生环境声/音效只对低风险镜头 opt-in：纯空镜、转场、远景氛围、背身/侧脸/剪影、无口型、无台词。正面说话特写、角色台词、旁白、系统音、克隆音色镜头禁止启用原生人声。每个 Clip prompt 必填 `原生音画策略`：`audio_intent`、`risk`、`mouth_visible`、`speech_policy`、`compose_policy`、`review`；开启环境声/音效时必须 `risk=low + mouth_visible=no + speech_policy=no_native_speech`。**`mouth_visible` 别凭印象填**：先跑 `python3 skills/n2d-model-router/scripts/mouth_detect.py <作品根> 第N集` 按首帧 PNG（装 insightface 时）+ 分镜文本预填/复核，图↔文本/图↔prompt 冲突会标 warn（以图为准）——脚本**只读不回写**，`mouth_visible` 真值就是每 Clip prompt 的 `原生音画策略` 字段，照建议要改的是 prompt——避免给说话镜误开环境声。详见 `references/原生音画opt-in.md`。
- **原生音频保留到 compose 处理（2026 新坑）**：Veo 3.1 / Seedance 2.0 等会**原生生成同步音频**（环境音甚至台词）。n2d-video 阶段的职责是拿回平台**原片**、抽帧验画、落档；**不要提前 `-an` 去音轨，不要转成无声版覆盖原片，也不要把原片挪进 `_raw_with_audio/` 再用无声版占正式 Clip 名**。调用时按 `原生音画策略` 写声音约束：默认"无对白、无旁白、不要生成原生人声"；低风险 opt-in 镜头可写"允许环境声/动作音效，禁止人声/台词/旁白"。若平台生成了音轨，在 `00_总览.md` 标记"含原生音轨"，交 n2d-compose 按 `视频原生音轨` 选择点统一处理。`gate.py --stage video|compose` 会阻断 `出视频/第N集/视频/` 下的 `.noaudio.mp4`、`*_noaudio.mp4`、`_raw_with_audio/` 等提前剥音轨痕迹。
- **合规与版权前置（P0 · 付费生视频前）**：视频生成前必须已有 `合规/compliance_manifest.json`。正式调用视频后端前默认跑 `dashboard.py gate --stage video_preflight`，它会继续阻断：声音克隆未授权、平台/地区/用途不清、角色身份注册层与角色授权不一致。视频是最贵工位，不能等成片后才发现不能投放。
- **长镜/多关键帧走后端能力档，不拼贴板**（2026-06 退役「分段故事版参考/拼贴板」模式）：长镜或"一段多镜"**不要**把多张帧合成一张大图喂后端，拼成网格会降采样且有"整板被动画化"风险。正确路径=**故事板(导演设计) → n2d-image 出关键帧(首/中锚/尾) → 按 `n2d_platform_profiles.frame_control` 选择执行**：即梦 `multiframe2video` 已核验可原生收 2–20 张时间轴关键帧；Veo/Luma/可灵等按档案先视为首尾帧能力；Runway/Pika/Sora 等未核验任意多帧时按首帧/参考图保守处理。非原生多帧后端不得静默吞 `_mid`：video_preflight 会 WARN，并要求改首尾帧、拆段接力或 reroute。
- **共享视频库（空镜/转场跨集复用）**：反复出现的纯空镜/转场/氛围 clip（宫门推、烛火空镜、妖气扩散转场）= 共享资产，出一次落 `出视频/共享/视频/`，跨集直接复用，别每集重生成（与出图的场景库同理，省视频积分）。带角色的镜头不进共享库（各集表演不同）。
  - **接入 compose 的方式（别漏）**：`n2d-compose/compose.sh` 只扫 `出视频/<集>/视频/*.mp4`，**不会**自动从 `出视频/共享/` 取片。复用某条共享 clip 时，需在该集时间轴位置把它**复制或软链**进 `出视频/<集>/视频/`（按 Clip 序命名），compose 才看得到。
- **产物归集铁律**：所有 prompt md 进 `出视频/第N集/prompt/`；**生成的 clip MP4 全部落 `出视频/第N集/视频/`**（供 n2d-compose 归集合成）。废片去 `废料/出视频/第N集/`。
- **视觉锚点闭环**：脚本会自动从 `出视频/第N集/prompt/01_clips.md` 提取 `**尾帧**` PNG。若存在尾帧，生成时会切换至 `multimodal2video` 模式，将首帧与尾帧同时作为参考，强制 AI 在指定时长内完成从起点到终点的演变，极大提升了 Clip 间的接缝平滑度。付费前 `gate.py --stage video_preflight` 会**核验 `01_clips.md` 实际引用的首帧/尾帧 PNG**（runner 真正喂后端的那条路径，与 `storyboard.firstframe_png` 分开誊抄、可能漂）：**首帧缺失 = BLOCK**（image2video 必失败、白扣一次）；**声明了尾帧但 PNG 缺失、或 storyboard 标 `need_endframe=true` 而 prompt 漏写尾帧 = WARN**（双帧接力降级为单首帧，大表情近景有脸重画风险）。
- **中段锚帧（默认铁律·三帧契约·能力门控）**：首尾双帧只锁两端，**长 Clip 中段**模型仍自由发挥；**默认每镜至少 3 帧、不管 cost**，gate 默认强制每镜有 `_mid` 声明或豁免（读 `policy.video_backend` 判能力，缺/未知=强制）。**唯一豁免=后端不支持 ≥3 帧**（由 adapter `backend_supports_three_plus_frames` 自动判定：即梦原生多帧、可灵/Veo/Luma 首尾档可拆段凑≥3帧 都强制；仅 seedance/sora/runway/pika 这类 first-frame-only 豁免），不因 cost/风格关。打斗/追逐/≥8s 多拍长镜/R3 漂移重抽镜可规划 `_a1.._aN` 多锚。`storyboard.json` 声明 `continuity.midframe` 或 `continuity.anchors` 后，执行分三档：① **原生多帧（首选·即梦 `multiframe2video`）**——[首帧, 锚帧1..K, 尾帧] 一次生成连续视频（2–20 帧、每段 0.5–8s、总≥2s），无 concat，不按 K+1 倍烧视频；② **首尾帧后端（Veo/Luma/可灵等档案）**——首尾两帧作为时间轴约束，中段锚帧只能改为拆段接力、extend/interpolate 或作为 QC/参考图，gate 会 WARN；③ **首帧/参考图后端**——退回单首帧 + 强 end_state 文字，或直接 reroute 到 Dreamina/native multiframe。两路/三路对 compose/进度/配音时长都仍是同一个 Clip，不重编号、不动 `镜头时长.json`。Clip 块头在 `**首帧**`/`**尾帧**` 后逐锚加 `**中段锚帧**`/`**锚帧K**` 行；storyboard 声明数 > prompt 引用数、引用 PNG 缺失、或后端不能消费声明帧 = `video_preflight` WARN。详见 `references/prompt_format.md`「中段锚帧 Clip」和 `references/platforms.md`「关键帧/多帧能力」。
- **运动 + 运镜 + 动态细节三件套必写**：只写画面不写运动 → AI 会随机推断，常翻车。
- **导演调度七字段硬要求**：每个 Clip 必须先写 `导演意图`、`起幅`、`落幅`、`场面调度`、`表演节拍`、`运动精修`、`环境交互`，再写人物运动/镜头运动/动态细节。目标不是把 prompt 写长，而是让它回答"这一镜为什么这样拍、从哪里接、停到哪里、空间关系怎么守、物理层如何稳、环境如何动"。缺任一字段不得提交视频生成，`dashboard.py gate --stage video`（生产入口，底层调 `n2d-review/scripts/gate.py --json`）会阻断。
- **专项镜头模板继承铁律（复杂镜头）**：凡 `storyboard.json` 的 Clip 带 `template/template_contract`，视频 prompt 必须增写 `专项镜头模板` 字段，并把模板里的 beats、blocking、camera_rule、continuity_must、negative 和专属字段转成**人物运动 / 镜头运动 / 衔接约束 / 降级方案**。打斗、追逐、对话反打、法术爆发、飞行、亲密互动、拥抱/拉扯、多人同框、群像站位不能只靠自由描述；`gate.py --stage video_preflight` 会先阻断 storyboard 缺模板或字段不全。
- **本集导演一致性契约**：`00_总览.md` 必须先写 `本集导演一致性契约`，锁住主色调、镜头语法、轴线、剧情状态锁、场景状态。单 Clip 再好，缺整集契约也会剪起来像随机素材；因此生成和审查都按这个契约验收。
- **本集基础视觉风格契约**：`00_总览.md` 必须继承出图总览 / `storyboard.json` 的「本集基础视觉风格契约」，锁住所选 `基础视觉风格` 的风格名、视觉基调、镜头与构图、光色策略、运动边界、风格禁忌。视频阶段只做与首帧和所选风格相容的运动；写实电影感可慢推/固定/轻微手持，赛璐璐可更弹性，水墨偏慢，赛博可更锐利，但都禁止把首帧改成另一种风格或无理由乱甩。
- **衔接设计必读**：从 `故事板.md` 读取每个 Clip 的 `衔接设计`（入点/出点/转场/连贯性），写进视频 prompt 的"衔接约束"和 `00_总览.md` 状态表。视频模型仍只生成画面运动，不生成台词；`声音先行(J-cut)` 只作为 n2d-compose 的后期意图。
- **中英双 prompt 铁律**：每个 Clip prompt 块默认同时写 `视频 prompt（中文）` + `视频 prompt（英文）`。中文 prompt 更便于本土导演语义和即梦/可灵中文理解，但部分平台可能对中文描述误触安全规避；英文 prompt 是同义兜底和海外后端兼容层。执行时优先用项目/平台最稳的一版；中文被拒、被改写或跑偏时，直接切英文版，不临场重写。
- **导演视角八维（视频版）**：视频 prompt 是导演视角八维的"运动落地"——①镜头/③人物外貌/⑤场景/⑥光影/⑧画风**已由首帧 PNG 锁死**（出图阶段做完），视频阶段**只升级 ④动作→人物运动+表情变化、②机位→运镜、⑦情绪→张力词**，其余维度严禁重定（改了=与首帧打架=闪烁漂移）。详见 `n2d/references/导演视角prompt.md §三`。
- **锚点句复用 + 跨AI锚定句不重拼**：含角色的 clip，prompt 里**复用角色卡『锚点句』**（来自 `n2d-script/references/formats.md §1`）稳住跨镜脸/妆造；但**跨 AI 锚定句只在出图阶段拼**（已由首帧 PNG 承载），**视频 prompt 不再追加任何风格锚定句**——视频 prompt 针对的是已锚定的首帧。
- **资产身份注册层继承铁律**：出视频前先跑 `python3 skills/n2d-identity/scripts/identity.py <作品根> --write`，读取 `生产数据/identity_adapter_matrix.json` 和 `出图/共享/identity_registry.json`；含角色 Clip 若目标后端有 `registered/ready` 的 Character ID / Face Lock / reference controls，必须写入平台参数；若是 `fallback_reference_group` / `unregistered`，prompt 明确回退到首帧 + 尾帧 + reference_group，并把高危镜头登记为后续注册候选。image2video 每帧独立推理会**累积漂移**，**极端角度 / 大暗部 / 人物在画面太小**时尤其崩；各后端用法见 `references/platforms.md` 各档案「角色一致性」行。
- **配角近景身份锁定铁律**：CU/MCU/反打/说话镜不能只写“reference_group 保持一致”。必须新增 `近景/反打身份锁定`，把脸型、五官比例、发型发髻、标志配饰、服装配色、脸部特写/表情参考、无原生 Face Lock 时的低幅度表情/小角度转头限制写清。配角没有脸部特写或连续脸漂时，直接降级 MCU/OTS/侧脸/手部/物件反应镜，别继续用泛化形容词硬撑正脸近景。
- **近景表情一致性铁律（治"近景不同表情时脸漂"）**：近景人物跨情绪变表情（哭/笑/怒/惊）最易**脸被表情带着重画**。`近景/反打身份锁定` 必带三子字段——**表情锚**（起→止，各引 `expressions` 对应情绪定妆图）、**表情幅度**（微/中/大，CU≤中、配角CU≤微）、**锁脸不锁情**（表情只动面部肌肉，脸型/五官比例/眼距/鼻梁/下颌/痣疤 must hold，写进 negative）。**表情幅度=大的近景**走「近景大表情变化类 Clip」首尾双帧只插值（首=起表情、尾=止表情定妆图，`mode=frames2video`）或降级 MCU，禁止单首帧让模型自由生成跨情绪表情。料源在 `n2d-image` 的 `reference_group.expressions` 同源情绪定妆；缺则该角大表情近景降级。详见 `references/prompt_format.md`「近景大表情变化类 Clip」。
- **运镜服务情绪/节奏，不是炫技**（`n2d/references/导演节奏.md §四/§五`）：从 `故事板.md` 的节奏注记派生运镜——逼近/聚焦=推近、释放/孤独=拉远、代入=跟、**高光/爽点=环绕或轻甩**、克制/压迫=固定。铺垫段运镜缓慢，爽点 Clip 运镜短促有冲击。每条视频 prompt 带一个**张力词**（克制/紧张/爆发/释放）锚定这条镜头的情绪强度。
- **平台差异在档案里，选择由路由表执行**：单 Clip 时长 / 运镜词偏好 / 首尾帧机制 / 提示词语言 / 模型路由能力速查见 `references/platforms.md`。逐 Clip 以 `video_model_routes.json` 的 primary/fallback 为准；普通镜或兜底模型读 `_设置.md` 的 `生视频模型`，实际调用读 `生视频渠道`，新项目首跑应已选一次。
- **出视频规格按三档预算 + 每次调模型/渠道前告知**：调即梦（dreamina）或任何生视频模型/渠道（Kling/Veo/Seedance…）出视频前，**像出图预算提示一样，先把本次的生成规格告知用户**——规格打包成 `出视频规格` 三档预算（**预算充足 / 预算一般（默认）/ 预算不够**），每档预设*分辨率·帧率·每Clip跑几条挑稳·平台质量档*。**首次问一次**→记入 `_设置.md`→之后**沉默沿用但每次开跑前一行告知当前档**（便于用户随时打断改）。三档表 + 告知话术见下「出视频规格」节。
- **生产数据记账铁律（P0）**：每次提交 image2video、每次重跑、每条 Clip 落档后，都要调用 `n2d-dashboard` 记录事件：`stage=video`、`asset`、`status=pass|fail`、`duration_sec`、`cost/provider`、`redraw_reason`、必要时 `meta=native_audio=yes/no`。视频是最贵工位，不记录成本/耗时/重跑原因，就无法判断批量化是否真的可控。
- **生视频调用优先级**：本机已装的官方 CLI → Bash 直调；没装 → 一步步指导手动；大批量可并行多个独立任务。
- **废料归档**：所有废视频片段 → `制漫剧/<剧名>/废料/出视频/第N集/`，**不留在 Downloads**。
- **视频生成贵**：单条 5-10s 视频从几毛到几块不等，**比图贵 1-2 个数量级**。提示词写不好就废一条——所以**先在图阶段把所有视觉变量锁死**，视频阶段只调动作/运镜。

## 可选增强：对口型 lip-sync（opt-in · 说话特写才值得）

说话近景/特写（CU/MCU）若口型与配音对不上会很跳。**默认不做**（远景/侧脸/背身/旁白镜头看不出，不值这成本）。仅当**人脸正面说话的特写**且预算允许时启用：

- **配音对齐·音频参考口型（首选·voice_conditioned_lipsync）**：`制作模式=配音先行` 且 `对口型≠关闭` 时，`n2d-model-router` 会把说话镜路由成 `mode=voice_conditioned_lipsync`、`native_audio_policy=lipsync_condition_only`，primary 选支持音频参考口型的后端（Seedance 2.0 音素级 / 可灵 Omni）。执行时**把该 Clip 的配音 `line_NN.wav` 当作音频参考/口型驱动输入喂给后端**，同帧出对口型画面。**铁律：模型这条音频只作口型条件、不接管声音**——成片音轨仍用 voice-first 克隆配音轨（compose 丢弃模型音频），既不双人声、又省一道后期对口型 pass。后端不支持音频参考口型/对不齐 → 按路由 `degrade_plan` 回退后期 pass 或分镜规避。**与 native_av 区别**：native_av 是后端自生成台词（绕过配音先行、换掉逐句音色控制），voice_conditioned_lipsync 保留克隆音色只借口型。
- **后期对口型 pass（回退档）**：后端不支持音频参考口型时，clip 出好后用本地对口型工具把口型对到配音轨（合成前的可选层）。工具按需选（2026-06）：**MuseTalk**（口型+画质均衡、近实时，当前最佳免费，**首选**）｜ **Wav2Lip**（SyncNet 同步精度最稳，规模化/真人底片）｜ **LatentSync**（ByteDance 扩散、身份保持好）。能力会变，以 `n2d/references/模型矩阵.md` 横切「音画联合」为准。
- 启用与否 + 档位记入 `_设置.md`（选择点 `对口型`：`关闭`(默认) / `配音对齐`(=voice_conditioned_lipsync·后端音频参考口型，首选) / `后期pass`(强制走 MuseTalk 等后期)）；不启用时在分镜阶段就**少给正面大特写说话镜**（用侧脸/背身/空镜配旁白规避），是零成本的替代。

## 出视频规格（选择点 `出视频规格` · 三档预算 · 每次调 AI 前告知）

和出图阶段的预算提示同一套思路：**真正调生视频模型/渠道前，把本次的生成规格告知用户**，避免默默用了贵档或抠档。规格不是单点，而是打包成三档预算，每档预设四件事——**分辨率 · 帧率 · 每个 Clip 跑几条挑稳 · 平台质量/模型档**：

| 规格档 | 分辨率 | 帧率 | 每 Clip 跑几条挑稳 | 平台质量/模型档 |
|---|---|---|---|---|
| **预算充足** | 1080p | 30fps | 关键镜 2-3 条挑最稳 · 普通镜 2 条 | 平台高质量档（即梦 Pro / 可灵 Master / Veo 高保真 / Seedance Pro） |
| **预算一般**（默认） | 720p | 24-30fps | **全部 1 条 + QC 门控重抽**（image_qc/video_qc 不过才重抽，关键镜可加挑 1 条） | 平台标准档 |
| **预算不够** | 720p | 24fps | 全部 1 条 · 不主动挑稳 | 平台快速/省积分档（即梦 Lite 等） |

> **为什么默认改成 QC 门控重抽（2026-06·对齐可用率 90%）**：Seedance 2.0 等可用率已从 20% 跃到 **~90%**（行业基准 `n2d-dashboard/references/industry_benchmark.json`），盲目"每镜跑 2 条挑稳"在 ROI ~1.1 的现实下是浪费——**默认改为先跑 1 条、过 `image_qc`/`video_qc` 就用、不过才重抽**（坏的那 ~10% 才花第二次钱）。`dashboard.redraw_rate` 实时校准这个决策：重抽率显著高于基准 0.1 时再回升挑稳条数。关键镜（🔑 爽点/反转/封面/人脸特写）可在 1 条基础上**加挑 1 条**取更稳的。要稳画质优先选 `预算充足`。

- **解析顺序**（按 `../skills/n2d/references/选择点与偏好.md`）：读 `<作品根>/_设置.md` 的 `出视频规格` → 缺则全局默认（`预算一般`）预填并告知一句 → 再缺则**首次问一次**→写回 `_设置.md`。**默认 `预算一般`**（对齐既有 720p 默认 + 视频贵的克制）。
- **每次开跑前必告知当前档**（沉默沿用 ≠ 闷头跑）：进真正调 AI 那一步，先念一行——
  > 「即将出视频，当前规格档 = **预算一般**（720p · 24-30fps · **全部 1 条 + QC 不过才重抽**（对齐可用率 90%）· 标准档）。可改 **预算充足**（1080p·30fps·关键镜 2-3 条挑稳·高质量档，更清晰更贵）或 **预算不够**（720p·24fps·全 1 条不挑稳·省积分档，最省）。要改说一声，否则按此档跑。」
- **关键镜 = 故事板里 🔑 爽点/反转/钩子/封面候选 / 人脸特写**；其余为普通镜。「跑几条挑稳」就是下文「为什么大多数视频跑两遍才稳」的预算开关——本档统一决定，不再每 Clip 临时拍脑袋。
- **单项可覆盖**：规格档只设默认，`视频分辨率` 等单项仍可在 `_设置.md` 单独覆盖（如选了 `预算一般` 但单独把分辨率改 1080p）。单 Clip **时长不在本档内**——由配音 `镜头时长.json` 驱动（见输入前置条件）；`画幅` 另见同名选择点。
- **落实到调用**：选定档后，把该档的分辨率/帧率喂给 CLI 的 `--resolution`/`--fps`（或平台对应 flag，确切写法见 `references/cli_registry.md`），并按「跑几条」决定每 Clip 抽几条挑稳。

## 生成粒度 + 优先序（选择点 · 逐单位停审，不满意即时调）

视频比图贵 1-2 个数量级，**默认更不该整集闷头一次过**。真正调 AI 出视频前，处理两个选择点（与 n2d-image 同义同源）：

- `生成优先序`（按 `../skills/n2d/references/选择点与偏好.md`：读 `_设置.md`→全局默认→首次问一次→沉默沿用）：**关键镜优先**（默认，故事板里对应 🔑 爽点/反转/钩子的 Clip 排队首，贵币先花在高光镜、先看运动稳不稳）｜ **分镜顺序**（Clip1→N 叙事序）｜ **先易后难**（单人/空镜/简单运镜先，复杂打斗/多人/强运镜后）
- `生成粒度`：⚠️**每次都问，不沉默沿用**（视频更贵，token/积分敏感）——**每集进出视频前必把下面四档菜单念给用户选一次**，`_设置.md` 里的值只作默认建议/预选。

**进入出视频前必做（报盘 → 必弹菜单 → 排队）**：
1. 数清本集要出的 **Clip 总数**并告知用户：「本集共需出 **X 个 Clip**。视频较贵，先选这次的**切分颗粒度**：」
2. **原样展示四档菜单**（标出当前默认，等用户选定才开抽）：
   > 1. **逐个（一张/一Clip）** — 最细：每出 1 个 Clip 就停下展示，等你确认或调整再继续下一个。最易即时优化，打招呼最频繁。
   > 2. **小批（默认每批 5 个）** — 折中：每批 ~5 个出完一起看、一停（批大小可随口改）。兼顾效率和可控。
   > 3. **按场景/段落分批** — 同一场景/段落的连续镜头作一批一停（天然贴合故事板分段，跨镜一致性也顺带更稳）。
   > 4. **整集一次过** — 一口气全出完最后统一看（最省打招呼，最粗，最废 token/时间/积分）。
3. 用户选定 → 按该档执行；可写回 `_设置.md` 作下次默认建议，但**下次仍要再弹一次菜单**。
4. 按 `生成优先序` 给本集 Clip 排出生成队列；共享视频库（空镜/转场复用）先核对，不重生成。

**逐单位循环**（每个粒度单位）：生成 → 检查（人脸不抖/动作合理/运镜对）→ **停下给用户看这一单位**（贴 MP4 路径 + 一句说明）→ 问「OK 还是重跑/改 prompt/拆 Clip？」→ 用户定夺 → 回写 `视频` 列分子（X/Y）→ 下一单位。

每个 Clip 的 prompt 块必须同时包含两段检查：
- `检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）`：提交前看 prompt 是否合格。
- `自检（生成后逐条过 · 落档闸门）`：生成后决定通过、进废料重跑，还是改 prompt/拆 Clip。

不要只写一个泛化 checklist；要像 n2d-image 的出图 prompt 一样，把"提交前自查"和"生成后落档闸门"分开写清楚。缺任一段都先补齐再提交视频生成。

> **整集档例外**：选 `整集` 才回旧行为（>6 Clip 可 spawn 2-3 子 agent 并发、每账号 ≤4 并发，最后统一报告），不逐单位停。`小批`/`按场景` 在「批」层停审。本节与「每 Clip 默认跑 2 条挑稳的」正交：粒度/优先序定**出的顺序与停审颗粒**，跑 2 条定**单 Clip 内挑哪条**。

## 输入前置条件

- `配音先行` 模式：`_进度.md` 该集 `配音=✅`（真实配音）+ `分镜设计=✅` + `出图` 列分子=分母；`配音=⏳rough` 不准出视频。`先出视频后配音` 模式：`配音=⏳rough` 可作为估算时间脚手架放行到出视频，但必须复述不推荐理由，并确认用户接受后期补真音可能重切/重出。原生音画模式：`配音` 是可选旁白层，不要求 `配音` 列 ✅；但必须已由 `finalize_storyboard.py` 从 `storyboard.json clips[].duration` 生成 `镜头时长.json`，且 `分镜设计` ✅ + `出图` 满。**Clip 时长读定稿 `故事板.md` / `镜头时长.json`，不再用平台默认估**；平台档案只约束单 Clip 上限——**按后端读 `references/platforms.md`「单 Clip 上限铁律」（即梦 image2video≤8s / Seedance 2.0≤15s / 可灵多镜较长 / Veo≈8s），不是一刀切 8s**，超上限才拆 Clip。
- 正式出视频前必须先跑模型路由，再跑确定性 preflight gate：
  1. `python3 skills/n2d-identity/scripts/identity.py <作品根> --write`
  2. `python3 skills/n2d-model-router/scripts/router.py <作品根> 第N集 --write`
  3. `python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage video_preflight`
  preflight gate 会检查 `合规/compliance_manifest.json`、声音克隆授权、占位闸门、`storyboard.json` continuity、专项镜头模板契约、资产身份注册层、尾帧 PNG、出图完成度、`00_总览.md` 本集导演一致性契约/本集基础视觉风格契约/本集模型路由表/本集近景身份风险表、单 Clip 导演调度七字段、近景/反打身份锁定、模型路由、continuity、中英 prompt、检查段，并把 QA 结果写入 `生产数据/`。有 block 先修合规包/prompt/故事板/尾帧/registry/路由表，**不得**调用生视频模型/渠道。
- **占位闸门（出视频最贵，必查）**：读 `合成/第N集/配音/时长清单.json`，若有 `占位:true` → 默认（`制作模式=配音先行`）**拒绝出视频**并提示先 `n2d-voice` 换真实配音重跑 + 回跑 `n2d-script 阶段2` 重定时。占位时长出的 clip 长度全错，是返工成本最高的坑。
  - **例外：`制作模式=先出视频后配音`（快速 demo·不推荐）**——用户已主动选择此模式，本闸门**放行**，但出视频前**必须向用户复述** n2d SKILL「制作模式」节的不推荐理由（尤其"出视频最贵，后期补真音对不上要重出，浪费最大"），并确认继续。真实配音将在视频出齐后、合成前补跑。
- 否则报错并建议用户先调 `n2d-script` 或 `n2d-image`

## 工作流

### 阶段 A — 视频 prompt 生成

源数据：`脚本/第N集/故事板.md`（阶段2·分镜设计 写的 Clip 表，时长配音驱动）+ `脚本/第N集/storyboard.json` + `出图/第N集/图片/镜头N_*.png`（出图阶段的定稿首帧）+ `出视频/第N集/prompt/video_model_routes.json`（由 `n2d-model-router` 生成）。

输出：`出视频/第N集/prompt/00_总览.md` + `出视频/第N集/prompt/01_clips.md`（按 Clip 一段一块）+ `video_model_routes.json/md`（路由真值与人审表）。

`00_总览.md` 必须包含 **本集导演一致性契约**：
- 主色调：本集/本段默认色调，以及哪些特效色只能在指定爽点后出现。
- 镜头语法：铺垫/对峙/爽点/留白各自用什么运镜，哪些运镜禁用。
- 轴线：主要人物左右站位、视线方向、出入画方向。
- 剧情状态锁：关键状态不得提前泄露（觉醒、金瞳、妖气、伤痕、变身等）。
- 场景状态：同场景连续 Clip 的灯位、雨雾、道具、门窗方向、背景布局继承规则。

同时必须**原样誊抄**出图总览的 **本集视觉一致性契约** 五字段（色调基线 / 场景光位锚 / 场景轴线视线 / 角色状态演进 / 景别阶梯，来自 `出图/第N集/prompt/00_总览.md`）——这是像素层契约的逐字真值，导演一致性契约只是它的运动层落地、**不可替代**。允许在原文之后追加视频侧的有意收紧/细化（超集），**不许改写或丢字段**。誊抄完必须跑契约继承 Diff 机检（防"人工誊抄改错轴线/光位无机器检出"）：

```bash
python3 skills/n2d-video/scripts/inherit_contract.py <作品根> 第N集
```

逐字段归一化比对两侧契约，报告落 `生产数据/contract_inheritance_第N集.json/.md`：**光位锚/轴线漂移或视频侧缺字段 = block（exit 1），必须按出图侧原文修复后再出视频**；色调/状态/景别漂移 = warn（确认是否有意改写）；出图侧本来就缺 = 提示不拦（上游问题，回 `n2d-image` 补）。

> **同一条 Diff 还把「出图首帧脸 → 出视频脸」纳入身份交接契约校验（②·脸的契约级 Diff）**：视觉契约五字段管色调/光位/轴线/状态/景别，**不含脸**；inherit_contract 再读 `出视频/第N集/prompt/video_model_routes.json` 的每个命名角色镜（`identity_requirement != none`），核验其 `01_clips.md` 逐镜 prompt 是否**真锁了身份**（既有「身份锁定/身份注册层」声明、又落到具体锚点 `CHAR_xx/定妆_/reference_group/character_id/face_lock/脸部特写`）。命名角色镜缺逐镜 prompt 或未锁身份 = **block**（首帧脸→视频脸无契约锚，出视频必脸漂）。这补上了 router 只「要求」锁脸、却没人核验逐镜 prompt 是否「兑现」的缺口。

> **同一条 Diff 还做「物料约束继承」（C·场景/道具/服装/特效逐镜资产交接）**：出图逐镜 `资产引用注册层` 绑定的 `LOC_xx/PROP_xx/OUTFIT_xx/VFX_xx`，出视频对应 Clip 的逐镜 prompt 不得丢失——丢了执行端取不到该资产的 `reference_group/constraints/drift_forbidden`，场景/道具/特效跨镜必漂。inherit_contract 逐 Clip 对账两侧资产 id 集合：出视频该 Clip 整块缺失 = block（`asset_clip_prompt_missing`）；资产 id 在出视频该镜丢了 = warn（`asset_handoff_dropped`，可能是记忆遮罩/转场的有意松引用，交人确认、补回 id 让结构/颜色/光位锚自动继承）。报告写进同一份 `contract_inheritance_第N集.json/md` 的 `asset_handoff` 段。

> **这套契约继承机检已接进 video_preflight/video gate 退出码**（`dashboard.py gate --stage video_preflight` 和生成后 `--stage video` 都会内部调 `inherit_contract.diff_contracts`，光位锚/轴线漂移→BLOCK），不再只靠这条裸命令的"自觉跑"——裸命令用于单独复核。**原生音画(native_av)不绕过这条链**：native_av 说话镜仍以出图首帧 PNG 作图生视频引导，像素层五字段契约链与配音先行模式完全一致，gate 同样强制；只有"纯文生视频同步音画、无首帧 PNG"的特殊后端才不适用（此类镜须在总览标注并降级为运动层约束）。

同时必须包含 **本集基础视觉风格契约**（继承出图总览，不重发明）：
- 风格名：来自 `_设置.md` 的 `基础视觉风格`。
- 视觉基调：该风格的角色比例、材质/线条、画面密度和整体质感。
- 镜头与构图：该风格下可用的景别、透视、留白、剪影或线稿纪律。
- 光色策略：主色、强调色、何时允许强调色出现。
- 运动边界：与风格相容的推/拉/跟/固定/弹性运动，不无理由乱甩。
- 风格禁忌：随所选风格派生，不能把写实电影感的禁忌套到所有风格。

同时必须包含 **本集模型路由表**（继承 `video_model_routes.json`，不临场重选）：
- routing_mode：`auto` 或 `fixed_default`。
- default_backend：从 `_设置.md 生视频模型` 读取，只作普通镜/兜底；旧项目 fallback 读取 `生视频AI`，实际调用渠道看 `生视频渠道`。
- 每 Clip：shot_type / primary_backend / fallback_backends / mode / native_audio_policy / identity_requirement / risk_flags / degrade_plan。
- 复杂镜头路由理由：打斗、追逐、对话反打、飞行、空镜、法术爆发、亲密互动、拥抱拉扯、多人同框、群像站位各自为什么选这个后端。

同时必须包含 **本集近景身份风险表**（继承 identity registry / adapter matrix，不靠记忆判断）：
- 逐角色/形态列出本集 CU/MCU/反打/说话镜 Clip。
- 写明可用脸部特写/表情参考/expressions、**表情跨度（微/中/大）**、当前后端身份锁能力、风险等级、工艺（首尾双帧/降级/直出）。
- **表情跨度=大的近景一律标高危**，强制走首尾双帧或降级 MCU；缺对应情绪 expressions 定妆图时风险再升一级、提示回 `n2d-image` 补表情定妆。
- 配角近景必须写“不稳时改 MCU/OTS/侧脸/手部/物件反应镜”，否则容易在正脸近景重绘脸型、发髻和配饰。

**单 Clip prompt 块标准格式**（详见 `references/prompt_format.md §1`）：

```markdown
## Clip K（时长 7s · 镜头 N1+N2）

**首帧**：`出图/第N集/图片/镜头N1_<描述>.png`
**尾帧**（默认首尾双帧接力：除最终 Clip 外，非豁免接缝**必用**；平台支持双帧的走 frames2video）：`出图/第N集/图片/镜头N_end.png`（n2d-image 在接缝出的尾帧=下一 Clip 首帧构图）。有尾帧就**首尾双帧引导**，把接点焊死，比只靠 end_state 文字稳得多；平台不支持双帧时退回首帧+强 end_state 文字。若非最终 Clip 没有尾帧，必须在 `storyboard.json` 写 `endframe_exempt_reason`，否则 gate 阻断。
**场景**：{场景名}（夜晚/内）
**导演意图**：{这一镜在剧情里的功能，说明为什么这样拍}
**起幅**：{从首帧/上一 Clip 接什么姿态、站位、视线、道具、场景状态开始}
**落幅**：{结尾停到哪里，给下一镜接什么}
**场面调度**：{人物左右站位、前后景关系、轴线方向、视线方向、出入画方向；无人物镜写画面重心}
**表演节拍**：{按时间段写唯一主动作链，如 [0-2s] 抬眼 [2-5s] 压住呼吸 [5-7s] 定住}
**运动精修**：{幅度 / 能量 / 身体守卫（重心、锁定部位、不穿模约束）}
**环境交互**：{描述动作对光影、粒子、背景物体的物理影响}
**专项镜头模板**（复杂镜必填，普通镜写“无”）：{template_id + beats + blocking + camera_rule + continuity_must + negative + 专属字段；来自 storyboard.json template_contract，不临场重写}
**模型路由**（每 Clip 必填，来自 `video_model_routes.json`）：{shot_type；primary_backend；fallback_backends；mode=image2video|frames2video|text2video|multi_shot；native_audio_policy；identity_requirement；risk_flags；rationale；degrade_plan}
**角色身份注册层**（含角色镜必填，普通镜写“无”）：{读取 `identity_adapter_matrix.json` + `identity_registry.json`；角色/形态 registry id；目标视频后端可用的 Character ID / Face Lock / reference controls / LoRA binding；fallback reference_group；高危角度/禁漂项}
**近景/反打身份锁定**（CU/MCU/说话镜/反应镜必填，普通远景/空镜写“无”）：{主焦点角色；脸部特写/表情参考/expressions 路径；无原生 Character ID/Face Lock/reference controls 时的 fallback reference_group；锁脸型/五官比例/发型发髻/标志配饰/服装配色；配角近景低幅表情和小角度转头；不稳则降级 MCU/OTS/侧脸/手部/物件反应镜｜**表情锚** 起→止（各引 expressions 情绪图）｜**表情幅度** 微/中/大（CU≤中、配角CU≤微）｜**锁脸不锁情**（表情只动面部肌肉、脸型五官比例不变）｜表情幅度=大走首尾双帧或降 MCU}
**原生音画策略**（每 Clip 必填，默认丢弃）：{audio_intent=none|ambience|native_sfx；risk=low|medium|high；mouth_visible=yes|no；speech_policy=no_native_speech；compose_policy=丢弃|低音量混入环境声|保留原片音轨；review=生成后确认无原生人声}
**衔接设计**：
- 入点：{承接上一个 Clip 的动作/视线/声音/空镜}
- 出点：{本 Clip 结束时停住的姿态/视线/道具/画面重心}
- 转场：{match cut / eyeline cut / 动作切 / 空镜缓冲 / 声音先行(J-cut) / 硬切}
- 连贯性：{轴线方向、人物左右站位、出入画方向、首尾帧约束}

**continuity**（必填，**读取**接力契约派生而非重写；缺字段先补，不提交生成）：
- start_state：**直接抄上一 Clip 的 `end_state`**（来自 `故事板.md` 衔接设计 / `storyboard.json` continuity——单一真值源，不要自己重新描述，否则相邻镜语义漂移就是跳切的根源）；首 Clip 则取首帧画面 + 入点。
- action：{本 Clip 内唯一主动作链，幅度可控，不重设人物/场景}
- end_state：{给下一 Clip 承接的结尾姿态、视线方向、画面重心或可切出的物件/空镜}
- constraints：{服装发型、人物左右站位、轴线方向、光线、天气、道具、背景布局保持一致}
- negative：{不要换脸、不要换衣、不要新增人物、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要生成原生人声}

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
\`\`\`
continuity:
  start_state: {start_state}
  action: {action}
  end_state: {end_state}
  constraints: {constraints}
  negative: {negative}
导演意图：{导演意图};
起幅：{起幅};
落幅：{落幅};
场面调度：{场面调度};
表演节拍：{表演节拍};
运动精修约束：{幅度 / 能量 / 身体守卫};
环境交互约束：{光影 / 粒子 / 物理反馈};
专项模板约束：{若有 template_contract，写明本 Clip 必须遵守的模板动作/站位/运镜/负向；普通镜写“无”};
模型路由约束：{读取 video_model_routes.json；本镜 primary_backend=...，fallback=...，mode=...；prompt 只使用 primary 后端真实支持的能力，不能混用其它后端专属能力；若失败按 degrade_plan 切 fallback 或拆镜};
身份锁定约束：{读取 identity_adapter_matrix.json + identity_registry.json；若目标后端 binding ready，写入 Character ID / Face Lock / reference controls / LoRA trigger 等平台参数；否则回退首帧+尾帧+reference_group，保持 drift_forbidden};
近景身份锁定约束：{CU/MCU/反打/说话镜优先脸部特写/表情参考/expressions；表情按 表情锚 起→止、幅度不超本镜封顶；锁脸不锁情——表情只动面部肌肉，脸型/五官比例/眼距/鼻梁/下颌/痣疤不变；无原生锁时限制低幅表情、小角度转头和低强度运镜，锁脸型/五官比例/发型发髻/标志配饰/服装配色；表情跨情绪（大）走首尾双帧或降 MCU；配角近景不稳则降级 MCU/OTS/侧脸/手部/物件反应镜};
原生音画约束：{默认禁止原生人声；若 audio_intent=ambience/native_sfx，则只允许环境声/动作音效，禁止台词/旁白/哼唱，生成后需确认无原生人声};
人物运动：{角色 A 动作} → {角色 A 表情变化——按 表情锚 起→止、幅度不超封顶、锁脸不锁情}；
镜头运动：{推/拉/跟/环绕/固定 + 速度词}；
动态细节：{烛火摇曳 / 晨雾流动 / 衣袂飘动 / 妖气扩散 ...};
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按{转场}服务下一镜；
声音约束：无对白、无旁白、不要生成原生人声；若故事板标声音先行，仅给 n2d-compose 使用；
（末尾视情况追加平台风格词，详见 platforms.md）
\`\`\`

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
\`\`\`
continuity:
  start_state: ...
  action: ...
  end_state: ...
  constraints: ...
  negative: ...
director intent: ...; opening frame state: ...; ending frame state: ...; blocking: ...; performance beats: ...
motion refinement: amplitude=..., energy=..., anatomy_guard=...;
ambient interaction: shadows, particles, props, and background reacting to the action;
close-up identity lock: for CU/MCU/reaction/speaking shots use face close-up or expression references first; if only reference_group fallback is available, keep expression and head motion low-amplitude, preserve facial proportions, hairstyle, signature accessories, costume palette, and downgrade unstable supporting-character close-ups to MCU/OTS/side-face or hand/object reaction shots;
character motion: ...; camera motion: dolly in slowly; dynamic detail: ...
continuity constraint: begin from continuity.start_state, perform only continuity.action, end on continuity.end_state, preserve continuity.constraints, avoid continuity.negative; audio constraint: no dialogue, no narration, no generated native voice.
\`\`\`

### 平台参数
- primary_backend / fallback_backends / mode / 模型质量档 / 时长 / 帧率 / 画幅 / image2video 强度 / identity adapter / native_audio_policy

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全，且服务本集导演一致性契约
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：运动精修写明重心、锁定部位、遮挡层级和不穿模/不拉脸约束
5. ✅ ②镜头运动：推/拉/跟/环绕/固定等词明确，速度词明确，不只写"运镜"
6. ✅ 动态细节 & 环境交互：烛火/雨丝/衣袂/雾气/灵光等 ≥1 条，且包含动作对光影/粒子/道具/背景的反馈，不改首帧设定
7. ✅ ⑦张力：运镜与"节奏/张力"一致（铺垫缓慢、爽点短促、留白定格）
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全，且已读取上一/下一 Clip 的衔接信息
9. ✅ 模型路由：已读取 `video_model_routes.json`，本镜有 primary/fallback/mode/rationale/degrade_plan，且平台参数只写目标后端支持的能力
10. ✅ 原生音画策略：已填 audio_intent/risk/mouth_visible/speech_policy/compose_policy；默认丢弃，只有低风险无口型无台词镜头才 opt-in 环境声/音效
11. ✅ 复杂镜头：已继承 `专项镜头模板`，且人物运动/镜头运动/衔接约束未违反 template_contract
12. ✅ 角色身份注册层：含角色 Clip 已读取 `identity_adapter_matrix.json` + `identity_registry.json`，明确 Character ID/Face Lock/reference controls/LoRA 或 fallback reference_group，且未违反高危角度/禁漂项
13. ✅ 近景身份锁定：CU/MCU/反打/说话镜已写脸型、五官比例、发型发髻、标志配饰、服装配色、脸部特写/表情参考或降级方案；已写 表情锚/表情幅度/锁脸不锁情，大表情近景已走首尾双帧或降 MCU
14. ✅ 复杂度可控：无超复杂打斗/多人混战；复杂动作已有降级方案

### 自检（生成后逐条过 · 落档闸门）
> 生成后过/重跑判定。筛选宽容：轻微偏差放行，只命中硬伤才重跑或改 prompt。

- [ ] 首帧一致性：开头画面与 `出图/第N集/图片/镜头N1_<描述>.png` 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化
- [ ] 镜头运动：符合 prompt 的推/拉/跟/固定等设计，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：至少 1 个动态细节成立，动作对光影/粒子/道具/背景的反馈成立，且没有引入现代物件/文字/logo/水印
- [ ] 导演调度：视频实际完成本镜导演意图；起幅、落幅、场面调度、表演节拍、运动精修、环境交互没有偏离；未违反 `00_总览.md` 本集导演一致性契约
- [ ] 模型路由：结果符合本镜 primary 后端的强项；若连续失败，按 fallback_backends/degrade_plan 重跑，不临场乱换后端
- [ ] 近景身份：CU/MCU/反打/说话镜检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角近景漂移则废料重跑或降级 MCU/OTS/侧脸/手部/物件反应镜
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；若本镜 opt-in 环境声/音效，确认仅为环境底并在总览「原生音画 opt-in 清单」标记；交 n2d-compose 按选择点处理
- [ ] 落档判定：⬜通过落 `出视频/第N集/视频/ClipK_<描述>.mp4` ｜ ⬜进废料重跑 ｜ ⬜改 prompt/拆 Clip 后重跑

### 降级方案
（若 image2video 推不动该动作，怎么改 prompt 或拆 Clip）
```

完成后：`_进度.md` 该集 `视频prompt` 列填 ✅。旧项目若表头缺 `视频prompt`，先迁移一次：
```bash
python3 skills/n2d/progress.py ensure-col <作品根> 视频prompt ⬜
```bash
python3 skills/n2d/progress.py set <作品根> 第N集 视频prompt ✅
```

### 阶段 B — 确定目标生视频 CLI

按 `references/cli_registry.md` 或内置探测工具扫描本机环境，定位与 `生视频渠道` 匹配的 CLI/API（例如 `生视频渠道=即梦/Dreamina` → dreamina；旧 `生视频AI=即梦` 兼容）。不再要求大模型使用原始 bash 循环去试探，直接通过生态内的检查工具/记录确定路径即可。

**统一执行器（推荐入口）**：

1. **能力报盘**：运行 `python3 skills/n2d-video/scripts/backend_status.py <作品根>` 查看后端多帧能力与拆段策略。
2. **自动化准备**：用 `scripts/video_runner.py` 写稳定 manifest。若后端不支持原生多帧，将自动执行 **Split Relay (拆段接力)**。

> **长镜/多关键帧**：不走拼贴板 segment 流程（已退役）。`video_runner prepare` 会自动从 `storyboard.json` 的 `continuity.anchors` 给有中段锚帧的 Clip 拼 `multiframe2video` 调用（首/中锚/尾 一次出连续镜），无需额外的故事版/segment 步骤——见「中段锚帧」节。

```bash
# 1) 准备稳定 manifest（prompt 文件落 生产数据/video_batches/...，不落 /private/tmp）
python3 skills/n2d-video/scripts/video_runner.py prepare <作品根> 第N集 --range 06-10 \
  --backend dreamina --resolution 720p --model-version 3.0

# 2) 提交单条（会花费视频积分；提交前 manifest 先标 submitting）
python3 skills/n2d-video/scripts/video_runner.py submit <作品根> <manifest.json> --clip Clip_06

# 3) 查询并下载到 出视频/第N集/视频/ 原片
python3 skills/n2d-video/scripts/video_runner.py query <作品根> <manifest.json> --clip Clip_06

# 4) 验收：抽帧 QC、dashboard 记账、回写 视频 X/Y
python3 skills/n2d-video/scripts/video_runner.py accept <作品根> <manifest.json> --clip Clip_06

# 批次抽帧 QC（只读原片，不剥音轨）
python3 skills/n2d-video/scripts/video_runner.py qc <作品根> <manifest.json>
```

`video_runner.py submit --dry-run` 可先检查将要调用的后端参数；若一次命令被打断，先跑 `video_runner.py status <manifest.json>`，必要时用平台任务列表核对最近任务，再决定是否重提。

### 阶段 C — 分支决策
**分支 1：找到匹配 CLI**
- 选定后**先念「出视频规格」告知话术**（当前规格档 + 三档可改，见上节），用户确认/沉默即按当前档；规格的分辨率/帧率/跑几条/质量档据此落实到调用
- 再告知用户："找到 X，将用它出视频。如不同意请打断。"
- 按 `生成粒度` + `生成优先序`（见上节）**逐单位停审**出视频，不要整集闷头跑；每单位调用见"调用规范"
- **批量加速可选（仅 `生成粒度: 整集` 档）**：整集档下 >6 个 Clip 时，可并行 2-3 个独立任务调用 CLI；**逐个/小批/按场景档按单位串行停审，不并发**
- 中间筛选 → 废视频 `废料/出视频/第N集/`，定稿 MP4 → `出视频/第N集/视频/Clip<K>_<描述>.mp4`

**分支 2：本机无合适 CLI**
- 告知用户："本机未检测到合适的视频生成 CLI/API（已扫 dreamina/kling/veo/seedance）。可由我一步步指导你在 `_设置.md` 选择的生视频渠道网页或你指定的外部工具上跑 image2video，每跑一段回传，我帮你筛选 + 落档。"
- 进入"手动指导模式"：
  - 一次一 Clip，列出 prompt + 首帧路径 + 平台参数
  - 用户上传首帧 + 粘贴 prompt → 平台跑 → MP4 下载
  - 用户回传 MP4（或路径）→ 执行者评判 → 通过则用户 mv 到 `出视频/第N集/视频/`，不通过则建议调整 prompt（多数情况是动作过复杂，需简化）

### 阶段 D — 进度回写 + 推进

每出一条定稿 MP4：
1. MP4 落档到 `出视频/第N集/视频/Clip<K>_<描述>.mp4`
2. `出视频/第N集/prompt/00_总览.md` 对应 Clip 行状态改 ✅
3. 若 MP4 含音频流，只记录"含原生音轨"；**不要在 n2d-video 阶段去音轨**，由 n2d-compose 统一选择处理。抽帧 QC 只读原片，统一放 `生产数据/video_qc/第N集/<批次>/`（`frames/` + `contact_sheet_*.jpg` + `video_qc_*.json/md`）；不得生成 `.noaudio.mp4` 作为正式视频产物。
4. 回写 `视频` 列：`python3 skills/n2d/progress.py set <作品根> 第N集 视频 X/Y`
5. 记录生产数据：
   ```bash
   python3 skills/n2d-dashboard/scripts/dashboard.py record <作品根> \
     --episode 第N集 --stage video --event generation \
     --asset <MP4路径> --status pass \
     --duration-sec <本次耗时秒> --provider <生视频后端> \
     --cost <成本数值> --unit <USD|CNY|credits> \
     --meta native_audio=<yes|no>
   ```
   若本条重跑或失败，改用 `--event redraw --status fail --redraw-reason "<动作崩|脸抖|运镜错|原生人声|...>"`；这条原因会进 `dashboard.md` 的重抽原因 Top。

本集 `视频` 列 = 分母时：
```
第K集 视频完成（X/X）
- 总时长：~Y 秒
- Clip 数：X
下一步：
- 合成：n2d-compose <作品根> 第K集  → 视频/ + 配音轨 + BGM + 烧字幕 → 成片
- 或继续 n2d-video <作品根> 第K+1集
```

## 调用规范（找到 CLI 时）

**通用流程**（每个 Clip）：

1. 从 `出视频/第N集/prompt/01_clips.md` 读出本段 prompt + 首帧路径 + 平台参数
2. 走 CLI：
   ```bash
   <cli> image2video \
      --image <出图/第N集/图片/镜头N1_xxx.png> \
       --prompt "$(cat <prompt 块>)" \
       --duration 7 \
       --aspect 9:16 \
       --resolution 720p \   # ← 按当前 `出视频规格` 档：预算充足=1080p，一般/不够=720p
       --fps 24 \            # ← 按规格档：充足=30，一般=24-30，不够=24（flag 名以平台为准）
       --out <出视频/第N集/视频/ClipK_<描述>.mp4>
   ```
   （各 CLI 具体子命令/参数 + 分辨率/帧率/质量档 flag 写法见 `references/cli_registry.md`）
3. 检查产出：人脸不抖 / 动作合理 / 运镜与 prompt 一致 → 通过；否则进 `废料/出视频/第N集/`
4. 音轨处理：允许用 `ffprobe` 检查是否含音频流并记录；**禁止为了"静音"把定稿 MP4 提前 `-an` 覆盖**。
5. **首尾帧机制**：默认读取 `storyboard.json` 的 `endframe_png`；目标平台支持首尾帧时用 `--first <PNG> --last <PNG>` / frames2video 双图引导，不支持时把 `end_state` 和下一 Clip 入点写进 prompt 作降级约束

**关于"为什么大多数视频跑两遍才稳"**：image2video 的运动估计有随机性，同 prompt 不同 seed 出来差异可观。所以**每个 Clip 跑几条挑稳由 `出视频规格` 档统一决定**（预算充足=关键镜2-3条·普通镜2条；一般=关键镜2条·普通镜1条；不够=全1条），不再每 Clip 临时定。挑视觉一致性更好的那条落档。

## 详细参考

- **导演视角八维（视频版·只调动作/运镜/张力，其余继承首帧）**：`n2d/references/导演视角prompt.md §三`
- **视频 prompt 单块格式 + 故事板 Clip 表 → prompt 派生规则**：`references/prompt_format.md`
- **原生音画 opt-in 策略（低风险环境声/音效才可启用）**：`references/原生音画opt-in.md`
- **平台档案 + 运镜词偏好 + 首尾帧机制**：`references/platforms.md`
- **已知视频 CLI 清单 + 调用模板**：`references/cli_registry.md`
- **翻车 + 修正案例**：`n2d/Q&A.md` 的 Q1（先图后视频）、Q14-Q17（CLI 安全）、Q18（图 AI vs 生视频模型/渠道关系）、Q34（先出视频后配音=快速 demo·不推荐，占位闸门放行）

## 常见错误

| 错误 | 纠正 |
|---|---|
| 视频 prompt 只写画面不写运动 | 必含人物运动 + 镜头运动 + 动态细节 |
| 视频 prompt 只有三件套，没有导演意图/起落幅/调度/节拍/精修/交互 | 先补 `导演意图`、`起幅`、`落幅`、`场面调度`、`表演节拍`、`运动精修`、`环境交互`；这些字段决定物理连贯性和环境真实感，缺任一项不得生成 |
| `00_总览.md` 只列 Clip 表，没有本集导演一致性契约 | 补 `本集导演一致性契约`：主色调、镜头语法、轴线、剧情状态锁、场景状态；否则 gate 阻断 |
| 视觉一致性契约凭手抄、改错轴线/光位没人发现 | 从出图总览原样誊抄五字段后跑 `python3 skills/n2d-video/scripts/inherit_contract.py <作品根> 第N集`——光位锚/轴线漂移或缺字段=block，必须修复再出视频；细化可以（超集），改写不行 |
| 没跑 `gate.py --stage video_preflight` 就调生视频模型/渠道 | 先跑确定性 preflight gate；有 block 先修 prompt/故事板/尾帧，视频贵，不靠生成后碰运气 |
| 含角色 Clip 没读 `identity_adapter_matrix.json` / `identity_registry.json` | 违反资产身份注册层继承铁律——先从 matrix/registry 取角色/形态 ID、Face Lock/Character ID/reference controls/LoRA 或 fallback reference_group，再写平台参数和身份锁定约束 |
| 原生音画策略缺失或随手开启 | 每个 Clip 必填 `原生音画策略`；只有低风险、无口型、无台词镜头可 opt-in 环境声/音效，正面说话/旁白/角色台词默认禁止 |
| 不告知规格就闷头调生视频模型/渠道 | 违反 `出视频规格` 选择点——调用前先念三档话术告知当前规格档（分辨率/帧率/跑几条/质量档），用户可改 |
| 设计超复杂打斗/人群 | 改为 AI 易生成的单人/双人动作、固定或简单运镜；过复杂的拆 Clip |
| 复杂镜头自由写视频 prompt | 先继承 `storyboard.json.template_contract`，补 `专项镜头模板` 字段，再把模板约束转成人物运动/镜头运动/衔接约束 |
| 跨集首帧画风跳变 | 出图阶段的定妆/分镜 PNG 都基于共享层定妆图复用，本 skill 直接用即可 |
| 用文生视频做有角色的镜头 | 改用 image2video，首帧用出图阶段 PNG |
| 在 n2d-video 阶段提前去音轨 | 错。n2d-video 保留平台原片，只标记是否含原生音轨；是否丢弃/混入/保留交给 n2d-compose 的 `视频原生音轨` 选择点 |
| 让 Veo/Seedance/Kling 原生台词进 clip | 只允许低风险环境声/音效 opt-in；原生台词/旁白/哼唱默认禁，若仍有原生音轨则保留原片并标记，compose 默认丢弃以避免双人声 |
| 反复空镜/转场每集重生成 | 进 `出视频/共享/视频/` 共享库跨集复用 |
| 正面大特写说话镜口型对不上 | 启用对口型 lip-sync，或分镜阶段改用侧脸/背身/空镜配旁白规避 |
| 单 Clip 时长超**该后端**上限（即梦 image2video>8s / Veo>8s；Seedance 2.0 可到 15s / 可灵多镜更长） | 拆成两个 Clip，补首尾双帧接力：上一 Clip 尾帧 = 下一 Clip 首帧。**别用 8s 一刀切**——上限按后端读 `references/platforms.md`，能一镜到底就别切碎 |
| 以为所有后端都能一次吃首/中/尾三帧 | 错。只有能力档确认的原生多帧后端可把 `_mid/_aK` 当时间轴关键帧；首尾帧后端只吃 first/last，首帧后端只能退回文字/参考图。跑 `video_preflight` 看「多帧能力」WARN，必要时改 Dreamina multiframe、拆段接力或 reroute |
| 选了首尾帧后端还期待 `_mid` 自动生效 | `_mid` 可保留作 QC/参考，但不能假装在一次请求里锁中段。需要中段锁动作时拆 A→M、M→B 接力并验内部接缝；若想无焊缝，改走已核验的 native multiframe |
| 废视频留在 Downloads | 全部归档 `废料/出视频/第N集/`，Downloads 清空 |
| 装第三方逆向 CLI | 违 ToS、封号风险，仅装官方 |
| 不报 Clip 总数就闷头整集出视频 | 违反 `生成粒度` 选择点——进出视频前先报本集 Clip 总数 + 按优先序排队，默认逐个停审 |
| 逐个/小批档还 spawn 子 agent 并发 | 并发只在 `整集` 档；逐个/小批/按场景档按单位串行，每单位停下让用户审 |
| 整集档全串行生 12 条 Clip | 仅整集档：可 spawn 子 agent 并发，但每账号 ≤4 并发避免限速 |
