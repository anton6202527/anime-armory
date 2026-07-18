---
name: n2d-image
description: >-
  Stage 4 of n2d pipeline — for a 作品 episode whose mode-aware 分镜设计 is done (`分镜设计` 列 ✅: 原生音画 uses storyboard-driven 镜头时长, 配音先行 requires real 配音, 先出视频后配音 may use explicit rough timing), generate the two-layer 出图 prompt pack (shared 定妆库 + 本集分镜), then generate images. The generation axis is a CONCRETE MODEL (design-constitution C5): choice point 生图模型 defaults to GPT Image 2 / OpenAI GPT Image family (exact model id verified per run); 生图AI is the access channel (default Codex CLI). Non-Codex/OpenAI image backends, including Dreamina/即梦官方 CLI, require explicit per-project signoff before paid generation; video backends remain separate. Writes progress to `_进度.md` (出图prompt + 出图 columns). Use when asked to 出图, 出图prompt, 生成定妆, 生成分镜图, GPT Image/GPT Image 2 生图, Codex 生图, image2image, or anything image-generation-related for a n2d project. Triggers 出图, 出图prompt, 定妆, 分镜出图, 生图模型, GPT Image, GPT Image 2, Codex, codex, image2image, 生图.
---

# n2d-image — Stage 4：出图 prompt + 生图

你是 **AI 漫剧出图制作**。本 skill 关心一件事：把**模式感知分镜设计已定稿**的一集（`分镜设计` ✅；`原生音画` 由 storyboard 推出 `镜头时长.json`、不要求先跑配音；`配音先行` 才要求真实配音；`先出视频后配音` 只在用户显式选择 rough timing 后放行），先生成"开箱即用"的两层出图 prompt 文件夹，然后**用所选生图模型**生成 PNG，落档 + 更新进度。出图 prompt 必须消费 `生产数据/script_quality_contract_第N集.json`：把上游定义的核心看点、首屏钩、留存承诺、逐镜戏剧功能写进总览和逐镜 prompt，并写 `script_contract_applied_第N集.json` 的 `出图` scope。**生成轴=具体模型（设计宪法 C5）**：选择点 `生图模型` 默认 **GPT Image 2 / OpenAI GPT Image 系列**（n2d 归一名；执行前以 OpenAI 官方 GPT Image/ChatGPT Images 2.0 口径和本次 model id 证据为准）——「由什么生成这张图」必须指认到**具体模型**，不写 `Codex`/`某后端`/`渠道商` 这类壳（`codex` 只是访问入口）。GPT Image 系列是 2026 第一梯队的高保真多参考/编辑模型，支持 4K 级尺寸和强上下文一致性，**但当前官方文档未证实可注册的服务端持久主体 ID/handle**；它不能按原生主体库使用。访问入口是 `生图AI`(=`生图渠道`)，默认 **Codex CLI**；其它可选模型（Seedream 5.0/4.5 / 可灵主体库模型 / Nano Banana 2/Pro 等）经各自官方/已登录渠道，Sora Character Cameo 仅旧项目/人工路径。出图阶段唯二硬闸门：① **同一项目/同一集原则上不得混用多个生图模型**（混用是跨镜漂移真凶）；唯一例外是本 skill「图片后端止损/故障切换铁律」规定的、用户预先签核且有完整 handoff 的一次性单向灾备切换；② **禁止第三方逆向/未授权出图路径**（含糊的 `同视频AI` / `某后端`、非官方 CLI、web 自动化出图仍禁）。这条统一规则只约束**生图作用域**：它不禁止 `n2d-model-router` 在出视频阶段按镜头能力逐 Clip 选择视频 primary；视频侧必须用 `backend_consistency_scope=per_clip_allowed_with_baseline`、基线、身份交接、执行配方和成片 QC 来管住一致性。若所选模型/渠道无法落 PNG 且没有已签核灾备，就停下报告，不要偷偷换兜底。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/n2d/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`基础视觉风格`（只继承，不在本阶段重选）、`生图模型`、`生图AI`（旧称，实为 `生图渠道`/访问入口）、`一致性增强(LoRA)`、`重抽预算策略`、`生成粒度`、`生成优先序`、`合规用途`。涉及版权、改编权、角色肖像/形象授权的判断不走普通偏好，必须写入 `合规/compliance_manifest.json`；其中源文本和同源改编权按设计宪法 D4 默认用户为原著作者 / 权利人，写 `original` 留痕，明确第三方来源时才要求 evidence/ref。出图阶段只需保证合规包已声明、不漏未授权形象。`distribution_intent=internal_only` 只免**平台审核/出海本地化**，**角色授权照常 BLOCK**，不因内部 demo 豁免（详见 `n2d-compliance`）。AI 生图内容的 **AI 标识/AI 披露/水印** 只做非阻断发布待办，不影响出图主流程。

## 核心原则

- **图片 prompt 克制铁律（P1·提交口径）**：图片 prompt 不是越多越稳，而是视觉变量必须明确、互相不打架。定妆图负责锁“档案稳定”，分镜图负责锁“这一帧怎么拍”；不要把角色卡全文、世界观、剧情解释、路由理由和无关设定整段塞进单条 prompt。角色/场景/道具等长期信息在 `identity_registry.json` / `asset_registry.json` / 角色圣经 / 共享定妆里承载；单条 prompt 只展开本图真正会影响像素的变量。定妆图按 `角色身份 / 年龄或年龄档 / 固定外貌 / 服装妆造 / 定妆要求 / 画风规格 / 禁止` 收束；分镜图按 `身份保持 / 镜头构图 / 动作瞬间 / 场景光影 / 情绪张力 / 画风规格 / 禁止` 收束。
- **完整合同 ≠ 实际提交 Prompt（compiler 硬边界）**：完整 Markdown 必须继续保留导演、身份/资产、参考计划、预算、检查清单和 QC 合同；但 Codex、Dreamina 或其它图片后端只能消费 `skills/n2d/_lib/image_prompt_compiler.py` 生成的编译请求。compiler 按角色定妆/场景/道具/风格锚/分镜/接力/多主体任务 profile 与具体后端 profile，输出像素目标、真实附件角色、参数和必要守卫；内部路径、registry 文案、路由理由、预算和自检不得进入模型文本。runner 禁止在 compiler 后追加未入哈希的创作指令。逐块编译预览、冲突优先级、回执和 A/B 口径见 `references/image_prompt_compiler.md`。
- **编译请求可追溯铁律**：每次实际提交必须保存完整提交文本、独立负向字段、真实参数、附件顺序与附件完整 SHA-256，并记录 source contract / execution context / compiled request / actual submit prompt 的 SHA-256。`image_preflight` 与 `image` gate 会阻断缺编译块、编译块过期、后端不一致、画幅冲突、悬空参考编号、负向策略错误或内部合同泄漏；不能只写说明文档而不改 runner/gate。
- **内心戏主体隔离铁律（分镜图）**：当 storyboard 标出内心戏、心声、心理反应、顿悟/疑惧等主观镜时，出图 prompt 默认只让思考主体成为画面焦点（CU/MCU、眼神、手部、呼吸、光影或象征物）；其他人物、妖魔、系统面板、武器/道具默认写入画外、虚焦剪影、弱记忆符号或禁入，避免把上一镜群像/怪物/道具重复摆进画面。确需同框压迫时必须继承 `inner_focus_context_reason`，且写明非焦点实体不露清晰脸、不做新增动作、不抢情绪焦点。
- **导演视角八维铁律（分镜图）**：每张**分镜图** prompt 按导演视角八维装配（**镜头·机位·人物·动作·场景·光影·情绪·画质**），不是画师视角的"好看插画"——必读 `n2d/references/导演视角prompt.md`。最易漏也最出戏的三维：**②机位**（别默认正面平视，机位即态度）、**⑥光影**（光替剧情说话，别均匀打亮）、**⑦情绪/张力**（驱动色调与运镜）。注意：**定妆图是中性档案**（正面/均匀光/无戏，只锁脸锁造型），**只有分镜图上全八维**——定妆图打戏剧光会污染下游参考。
- **剧本可看性合同必须消费（上游“好看”落画面）**：`n2d-script` 已把“好看”拆成 `script_quality_contract_第N集.json` 的可签收字段；本阶段必须把这些字段写入 `出图/第N集/prompt/00_总览.md` 的「本集可看性签收合同」和每镜 `**剧本可看性合同**`。逐镜出图不是只画 `description`，而是按 `dramatic_function` 决定画面信息焦点，按 `audience_effect` 决定表情/机位/光影，按 `retention_promise_ledger` 保护承诺与兑现链，按 `spectacle_story_function` 避免空洞奇观。prompt 包生成后必须自动写 `生产数据/script_contract_applied_第N集.json` 的 `出图` scope，并写 `生产数据/consumed_contracts_image_prompt_第N集.json`，绑定 storyboard、continuity_chain、script_quality_contract、director_camera_plan、reference_plan 与当前 prompt 文件 SHA；`image_preflight/image` gate 会按这些 SHA 检查，缺失或过期即回 prompt 阶段。
- **打斗视线铁律（动作镜 · 主镜头不是对手）**：打斗、追逐、法术、强互动镜头里，主镜头默认是**旁观摄影机**，不是对手 POV，更不是自拍镜头。除非逐镜明确写 `opponent POV` / `主观镜头` / `破第四墙`，角色**不得直视主镜头、不得与镜头 eye contact、不得 portrait pose**；视线必须锁在**对手、武器来路、命中点、破绽或下一动作目标**。需要锁脸时写“脸部可辨的三分之二侧脸 / 侧脸 / 背身侧轮廓”，不要把动作镜写成“清晰正脸 / clear frontal face / looking at viewer”。逐镜正向 prompt 要写“镜头是旁观者、不看镜头、视线锁定 X”，负向补 `looking at viewer, eye contact with camera, portrait pose, front-facing portrait`。`image_qc` 会对动作镜的看镜头词和正脸肖像化倾向 hard block，缺视线防呆句 warn。
- **正反打 prompt 消费铁律**：`dialogue_shot_reverse` 镜头必须优先消费 `脚本/第N集/shot_reverse_contract.json`，并兼容继承 P-2 `axis_blocking_map.json#shot_reverse_patterns` 和 P-3 `continuity_bible.json#shot_reverse_continuity`：180° 行动轴线、A/B 屏幕左右或窄画幅纵深高低位、互补视线、OTS/clean single/insert coverage、镜头高度/距离匹配、越轴策略和缓冲镜。逐镜 prompt 不能只写“反打/对话近景”；必须写清“谁在屏幕左/右或前/后、看向哪边、谁的肩/侧背在前景、谁是焦点、镜头距离和情绪功能”。`consumed_contracts_image_prompt_第N集.json` 会记录 `shot_reverse_contract` 的 path/sha256。
- **出图连续性铁律（图片一致性 · 不得松动）**：同一 Clip 的 first/mid/end 或多锚帧不是三张独立插画，而是同一镜头状态的连续推进。凡上一帧已经确定的**角色站位、武器/道具接触点、伤口位置、手握位置、入射角/刀柄角度、光位、轴线、关键道具结构**，后续帧必须继承；动作推进只能在表情、烟尘、光效、身体微姿态、镜头距离上变化。尤其是刀剑枪矛等武器**插入/刺入/贯穿身体**时，画面只能有一个明确入体点，且必须落在 prompt 指定身体部位；不得把“胸口一刀”画成腹部/腰部/肩部跳位，不得让同一把刀像插了多刀。此类问题不按“剧情解释”豁免，全部视为图片一致性硬伤：标 `temporal_continuity` block，归档/重抽受影响 Clip，全量重跑 image_qc 和 image gate；禁止为省成本把连续性硬伤降级为 warn 或人工签过。
- **手部/肢体归属铁律（崩手 · 不得松动）**：任何人物手部、武器握持、道具触碰、卷轴/面板操作、打斗受力或亲密接触镜头，必须能一眼判断每只可见手属于哪个角色、左/右哪一侧手臂、正在接触什么；单个人形角色最多两条手臂两只手，手必须自然连接到同侧手腕、前臂、肘部和肩线。额外手掌、镜像右手/镜像左手、漂浮断手、同一只手在两个位置重复出现、手从光效/道具/武器里长出、左右手归属互换、多指/粘连畸形，都与脸漂/接触点漂移同级，标 `anatomy_continuity` 或 `hands` block，归档重抽；不得因构图、光影或系统特效好看而签过。若不需要展示某只手，宁可用身体、袖子、画幅或道具自然遮挡，也不能生成第三只手。
- **人体完整性合约铁律（N5 · 不只锁脸）**：每个含人物分镜 prompt 必须写 `人体完整性/解剖完整性` 合约，至少交代可见身体范围、允许裁切/遮挡、不得多手多肢/缺肢畸形、不得身体与地面/道具/光效融合。全身/站立/跪倒/倒地/地面接触镜还必须写脚底/膝盖/身体接触面和 `不埋入、不穿模、不融合`；全身照必须头到脚、脚/鞋可见。手部、握持、触碰、武器道具操作镜必须额外写 `手部归属`：每只手属于哪个 `CHAR_xx`、左/右哪侧、如何连接同侧手腕/前臂/肘肩、接触点在哪里。`image_qc` 会把缺手部归属、缺身体接触面、缺全身完整约束 hard block；普通人物镜缺人体合约 warn。
- **人物主流审美默认铁律（除非特殊说明）**：出人物时，prompt 默认把角色写到**当下主流可播审美 + 镜头友好**：脸部比例协调、五官清晰有辨识度、发型/妆容/服装整理到位、服饰剪裁和材质有质感、光影让五官立体好看，画面观感精致耐看。它是默认底色，不替代角色 DNA：年龄、身份阶层、病弱/战损/疲惫、反派怪相、恐怖妖异、喜剧丑角、丑化讽刺、写实粗粝、用户指定的非主流审美或角色圣经里的缺陷特征优先；不得把所有角色洗成同一张网红脸、过度磨皮塑料脸、无辨识度高颜值模板。定妆 prompt 必写「人物审美基线」；分镜人物镜也要继承该基线，再叠加本镜状态、情绪和导演机位。
- **用户人物参考图脸锚铁律（只取身份/身形，不继承整图风格）**：用户给的主角图/人物参考图默认只作为**身份与身形锚**，只提取基础身高、体型/身材比例、体态、脸型、五官比例、眼神气质、肤质、年龄感等身份信息；**不得继承**参考图里的画风、照片/摄影风格、渲染风格、滤镜、色彩分级、光影方案、景深、清晰度质感、构图/镜头语言、背景、服装、裸露程度、发型/发饰、表情、姿态、配饰、场景、IP/水印或原图剧情状态。外部参考图的**风格权重视为 0**；项目风格必须以 `<作品根>/_设置.md` 的 `基础视觉风格`、`storyboard.json.style_contract`、`00_总览.md` 的「本集基础视觉风格契约」和角色/资产 registry 为唯一真值，统一转译到项目风格。服饰、表情、配饰、武器、法宝、觉醒/妖化/战场/常服等各种形态，必须以**小说原文、角色圣经、identity_registry 的 form/wardrobe_profile、asset_registry 和本镜分镜状态**为准；除非用户明确说“这张图的衣服/发型/配饰也要沿用”，否则外部图只进 `face_anchor_refs`/身份母本，不进服装/形态真值。生成 prompt 和 runner 必须把这条写进正向约束，负向补“不要继承参考图画风/摄影风格/滤镜/光色/构图/衣装/裸露/姿态/表情/配饰/场景”。若已生成定妆明显继承外部参考图风格，它不得成为共享 reference_group，必须标脏并按项目基础视觉风格重出整套定妆包。
- **外部参考图付费准入铁律（权利/SHA/水印 fail-closed）**：外部人物或风格图必须先登记到 `设定库/参考资料/视觉参考/reference_manifest.json`；只有行内 `rights_status` 明确为 `authorized` / `user_owned`（或等价已授权值）、`eligible_for_generation=true`、`backend_upload_allowed=true`、`watermark_present=false`，且当前文件 SHA-256 与声明 `sha256` 完全一致时，才可进入真实后端附件。`analysis_only`、任何 pending/unknown/unlicensed、带水印或水印状态未明确、缺布尔准入、SHA 缺失/失配、项目外/非规范路径一律不 attach；旧 `出图/共享/图片/*定型参考*` 若无该收据也只保留迁移，不自动放行。非 dry-run 的 `codex_image_runner.py --shared-targets` 会先跑不可由 `--skip-preflight` 绕过的 `shared_asset_preflight`：只检查合规清单与外部参考准入，不要求尚未生成的五视图像素/签收包；共享资产落地并签收后，Clip 仍须走完整 `image_preflight`。
- **低分辨率参考增强铁律（用户图/截图不降质）**：用户给的参考图可能是低分辨率截图、压缩图或带播放器 UI/字幕/搜索框。正式传入生图后端前，runner 必须先做入参质量处理：短边 <1024px 的参考图写入确定性增强副本 `生产数据/reference_enhanced/<第N集>/...png`（默认 LANCZOS 升采样 + 轻锐化，长边上限 2048px；原图不覆盖，保留原始 sha 与增强 sha），`codex exec --image` 等真实附件优先传增强副本，manifest/production event 记录 `prepared_rel_path/prepared_sha256/reference_quality`。增强图只改善参考信号，不允许把参考图的低清、模糊、压缩块、截图质感、播放按钮、平台 UI、字幕、水印带进最终图；prompt 必须明确“低清参考只锁身份/兽脸/结构，最终输出按项目高质量高清 PNG 生成”。Pillow 不可用或图像不可读时不得静默假增强：保留原图并在 manifest 标 `pillow_unavailable` / `unreadable_raster`，高风险角色参考仍应补更清晰母本或重出脸锚。
- **所有入画人物脸一致性铁律（资产也算人物）**：只要画面里出现可辨人物脸或具名角色体貌，无论文件名是角色定妆、VFX、武器比例、道具、场景、动作参考还是分镜图，都必须能追溯到 `identity_registry` 的具体 `CHAR_xx/形态`，并使用同源定妆组/脸锚/表情参考锁脸；不得让非角色资产“顺手长出一张新脸”。非角色资产/VFX/道具/武器/场景默认 `face_policy=faceless`：未显式声明 `owner/carries_identity` 且 `face_policy=face_locked` 时，只允许纯资产/纯特效/环境，或下巴以下、背身、侧后剪影、无脸人台等尺度参考；若生成结果出现未绑定身份的清晰人物脸，一律按脸漂失败归档重出。
- **人物全身照鞋靴铁律（全身必须头到脚）**：凡人物全身、标准立绘、正面/前45°/侧面/后45°/背面、turnaround、全身动作参考，必须从头到脚完整入画，鞋靴/脚部清楚可见；不得裁掉脚、不得用衣摆/烟雾/画幅把鞋完全遮住、不得用半身构图冒充全身。只有明确命名为半身、脸部特写、手部/局部参考的目标可豁免。
- **统一标准层铁律（标准不跟后端走）**：n2d 出图标准只描述“必须达到什么”，不描述“用哪个后端怎么做”。统一标准在 `skills/n2d/_lib/image_backend_standards.py`：官方可审计入口、角色身份连续性、多主体身份隔离、参考图真实入参、合法修复路径、文字/overlay、参考预算、QC 回退闭环。所选 `生图模型 + 生图AI/生图渠道` 只进入 `image_backend_adapter.py` 做能力映射：原生能做到就走原生能力；做不到就自动加载弥补措施（reference_group + face_embedding / regional_construct_required / split_composite_required / compose overlay / 整图重抽 / full QC / 人审队列等）。**标准不因后端短板而下调**，只改变实现路径与成本；适配层无法弥补时才要求换后端或停线。
- **核心五角 turnaround 铁律（定妆＝对齐档案，不是五张好看图）**：`core_full` 固定为正面 / 前3/4 / 侧面 / 后3/4 / 背面五角，并保留 turnaround 目视总览板；各角必须**中性同源、同身高、同比例、头顶线/脚底线/身体中心线/水平视平线/景别距离对齐**。五角是与动画生产实践和多视图一致性研究相容的 n2d 核心人物基线，不是所有角色/项目的普适强制标准；`core_full >=10集`、512px 等数值是项目默认启发式。生产优先「整张五角 turnaround 同框出 → `derive_makeup_pack.py` 同源拆图」；“独立视角”只要求不同可喂图路径和完整派生收据，不要求分别生成，但五个桶不得只是同一像素的复制文件、软链或换标签。所有证据路径必须是解析后仍位于作品根的规范相对路径；绝对路径、`..` 越界、软链别名和非规范别名均不参与放行，同源母本产生的不同真实裁切像素不受影响。`image_qc.audit_turnaround_alignment` 会给出可复算的全身/脸框几何，但阈值属于启发式，只能 WARN；真正 BLOCK 的是缺图、当前像素不合法，或缺少与当前 PNG hash 绑定的逐视图目视收据。默认仍要求人工收据；只有作品 `_设置.md` 留有用户明确授权“执行者实际像素目视”时，才允许 `image_qc.py --review-view ... --view-review-kind executor_visual --view-reviewer <执行者标识> --accept-current-pixels` 写独立 `visual_review` 收据，且固定记录 `human_signoff=false`，不得冒充导演/用户签收。人工兼容入口继续用 `--view-review-kind human`（默认）；expression 用 `--view-path` 精确指定。两类收据都必须绑定当前 PNG SHA、角色/形态/档位/视角/路径、review contract、完整 criteria、带时区时间，并精确写 `confirmation={"kind":"explicit_current_pixels_acceptance","accepted_current_pixels":true}`。本地 reviewer 字符串只能记录本次声明，不能认证真实身份或独立性；强保证需外部认证 ID、签名或审批收据。五角 + 总览 + 至少一个表情/脸锚收据齐全后才能 `--mark-finalized`。低置信几何偏差保持 WARN；目视收据判定存在身份/服装/对齐硬伤时不得落档。详见 `references/prompt_format.md §1.2`、`references/角色一致性checklist.md §二` 与 `n2d-review/references/production_acceptance_v2.md`。
- **标准定妆背景铁律（定妆照不是场景照）**：人物定妆照必须使用**统一中性灰白 / 18% 灰棚拍底、柔和均匀棚拍光、无剧情场景**。背景只能是干净灰底，不得出现雨窗、房间、家具、门框、案几、油灯、道具、街景、战场、剧情光效或任何环境叙事；这些会把场景信息烤进身份锚，导致后续分镜把角色误带回同一背景。`style_anchor` 只控制**材质 / 渲染 / 色彩倾向 / 镜头质感**，不得控制角色定妆背景；角色定妆 prompt 必须明写“中性灰白/18%灰棚拍背景，无窗、无房间、无家具、无剧情道具”。已经生成的雨窗/房间背景角色图只能作为风格探针或废料，不得标为 `ready`、不得写 `self_check_passed=true`、不得作为 `identity_registry` 的身份锚进入分镜。
- **逐张定妆比对硬闸门（分镜角色图）**：每张已落档、含角色的本集分镜 PNG，进入 `n2d-video` 前必须在 `image_qc` 里留下 `face_reference_coverage` 证据：该镜来自逐镜 prompt 的角色镜清单，且已用 full 精度脸部 embedding 对定妆/身份主参考完成比对。缺 `image_qc`、旧版 QC 缺覆盖字段、`qc_environment.precision_level!=full`、该镜缺 face row、face row=`warn`/`noface`、PNG 晚于 QC，全部按硬阻断回 `image`。动作镜也不例外：刀光、火花、风发、暗影、极端侧背或纯剪影把主检角色脸压到机检不可读时，不按“动作好看”签过，归档重抽或改构图到可核验。人工觉得“看着像”不能替代这条机器闸门；需要人判时先补 full QC 证据，再记录复核结论。
- **视频近景升格锚帧铁律（防最终 MP4 换脸）**：若 storyboard / video prompt 的落幅、反打或表演节拍会把某角色从小脸、远景、侧背或遮挡状态推成 CU/MCU/半特写清晰脸，本阶段必须先生成同源近景锚帧/脸部特写/表情参考并过 full `image_qc`。不要指望视频模型从远景小脸“补”成主角近脸；这会绕过分镜 PNG 的脸检，导致成片里出现新演员脸。缺近景锚帧时，回分镜改成 OTS/侧脸/手部/物件反应或保持原景别，再进入 `n2d-video`。
- **本地贴脸修复禁用铁律（反作弊硬闸）**：**别再用本地贴脸修复**。严禁把定妆照/参考图中的脸裁出来，经过 resize、调色、alpha blend、Poisson seamless clone、face swap/facefix 等方式贴回分镜图，再拿去跑 embedding 过 QC。embedding 分数只是证据，不是目标；“为了让脸部 embedding 分数过 QC”而贴脸，是掩耳盗铃式自欺欺人。命中 `local_face_patch`、`face_patch`、`facefix`、`faceswap`、`inswapper`、`facefusion`、`roop` 或等价本地裁脸/换脸/贴脸操作的产物，一律归档为失败实验/废料，**不得作为最终图留在 `出图/第N集/图片/`，不得进入 video**。正确修法：重出该镜；近景/反打/表情镜改用同源表情库、脸部特写参考或官方后端真实 image2image/inpainting 派生，让模型重绘整张脸并自然融进镜头光影；必要时降低“必须完全像定妆”的硬修倾向，优先保持真实镜头光影和表演。允许的本地操作仅限不替换身份像素的裁切/缩放/色彩整理/归档；一旦替换了角色脸部身份像素，就不是修复，是禁用产物。**边界澄清（别误判合法的「分区逐次构建」）**：本条禁的是「**对一张已成片的多人镜抠脸贴回**」；它**不禁**「**从空场景底板按区域分次构建**」——先出无人/纯环境底板，再用官方后端的 inpaint / regional-prompt 逐区域（左区/右区）各喂**该角色自己的 reference_group** 把人一个个画进对应区域，每区可叠 Adetailer / IP-Adapter Face 做脸部二次精修。区别在于：分区构建是**模型重绘整张脸并自然融光**（合法），事后贴脸是**移植既有脸部身份像素**（禁用）。多人同框走 GPT Image/OpenAI 系列（经 Codex CLI/OpenAI Images API）路线时这是首选实现，详见「多角色同框是硬触发点」条与 `references/prompt_format.md §2.2`。`image_qc` 和 video gate 会读 `生产数据/production_events.jsonl`：最新 image 落档事件若来自上述贴脸链路，直接 hard block；只有后续真实重抽或官方 image2image 落一条新的 pass 事件才能覆盖旧记录。
- **出图前角色 DNA 定档铁律（P0 · 每个角色做到哪一档，先说清再出图）**：付费出任何角色定妆前，必须先产出/刷新一张**「角色 DNA 一致性定档表」**并落进 `出图/共享/prompt/00_索引.md`。表里同时区分两种档位：① **角色库深度**：`core_full`（主角/核心长线/预计出场≥10集）、`recurring_standard`（复现配角）、`named_minimal`（具名短线）、`restricted_partial`（局部群像）；② **身份锁执行档**：参考图派生 → face_embedding → 后端原生主体 ID → LoRA。两者不能混成一列。所有具名人物至少有正面、半身/全身服装锚、同源脸锚和 asset bundle；`core_full` 固定补齐正/前3/4/侧/后3/4/背 + turnaround，其他角度、表情库与动作参考按档位和实际分镜需求补齐。身份锁仍按跨集风险升档。逐角色方法见 `references/lora_consistency.md「出图前角色 DNA 定档框架」`。
- **后端身份能力矩阵铁律（执行真值）**：定档不要凭后端名字猜；读取 `skills/n2d/_lib/n2d_contract.py` 转出的 `IMAGE_IDENTITY_PROFILES`。Codex/OpenAI/Dreamina/即梦/Nano Banana/Gemini 属于**多参考/图生图但无持久主体 ID**，每镜仍要喂定妆组、基础脸锚/表情库和锚点句；Seedream/可灵属于**可注册持久主体/角色 ID**，核心长线角和多人同框高危镜优先注册；Sora Cameo 只按旧项目/人工路径处理；LoRA 只在前两档压不住时启动。**中间档 `face_embedding`（P2a·IP-Adapter FaceID 等免训练脸嵌入锁·backend 无关）**：填 reference-group↔LoRA 的断档——给无持久主体 ID 后端一个比纯参考图组强、又不必训 LoRA 的身份锚，登记在 `identity_adapters.image.face_embedding`（`{status:ready, type:ip_adapter_faceid}`）。`scripts/face_drift_risk.py` 按矩阵输出 `multi_reference / face_embedding / native_unregistered / native_subject / lora` 风险档（强度递增），不再把 Dreamina 或 Nano/Gemini 误判成 Seedream。
  - **无注册主体ID后端的锁脸保障 gate（设计宪法 B9/C6）**：`persistent_subject=false` 只表示**没有可注册的服务端持久主体 ID/handle**，**不等于不能做角色一致性**——GPT Image/OpenAI 系列（经 Codex CLI/OpenAI Images API）有高保真多参考/编辑能力和强上下文一致性，是第一梯队模型；但它仍不是主体库/角色 ID 后端。所以这道 gate 是**对没有 subject-id 的模型补一层锁脸质量保障**：`image_preflight` 在 `persistent_subject=false` 时硬卡四类脸漂真凶——① 多人同框只写普通多参考、不登记「分别出图+合成/单人分层出图」**或**未给每主体身份槽位（见下）；② 多人同框虽写了分层/合成但缺 `多人同框身份槽位`（每个 `CHAR_xx/形态` 对应自己的画面位置、脸部参考/表情库和 primary 星标）；③ 近景/反打/大表情镜缺同源脸部特写、`face_anchor_refs` 或 expressions 表情库参考；④ 暗光/黑烟/VFX 叠脸却缺「眼鼻嘴三角区清晰、特效不遮脸、不重画五官」约束。**关键（C6 剧情优先）**：这四类 gate 拦的是「**没把难镜做对**」，**不是「这镜不该存在」**——多人同框该不该出由剧情决定，gate 不删镜、不强行降人数，只要求**用质量手段把它做对**（每主体身份槽位 / 分别出图+分区合成 / 必要时该镜用更强多主体模型如 Seedream 4.5 主体库）。解决优先级：先给身份槽位 + 喂全各主体定妆，其次分区构建/分别出图+合成（GPT Image/OpenAI 系列在位绑定下单帧同框已较稳），再次同源 image2image 接力，最后才靠锚点句兜底。注意：`若多主体仍不稳再分别出图` 这类条件式兜底不算登记执行策略，必须把执行路径写成本镜硬执行；多人同框也不得用 `参考图①/reference image 1` 做泛化身份锁，必须逐主体写 `CHAR_xx/形态` 对应自己的定妆/脸部特写/表情库。
  - **后端能力先查证铁律**：不得凭记忆或旧经验断言“某后端不能做多图 / 主体 / seed / 批量 / 价格规格”。凡要阻断、迁移、回退/保真实现或写进 skill 的后端能力结论，必须先做三步：① 查官方文档/实时资料；② 查本机 CLI/API `--help` 或能力枚举；③ 高风险/高成本能力做最小 smoke test。能力归一读 `skills/n2d/_lib/image_backend_adapter.py`，它把 Codex/OpenAI/Dreamina/Seedream/可灵/Nano/Sora 等映射成统一的 `generation_modes/reference_input/native_subject/supports_edit/supports_mask/output`。每次正式付费出图前，把当天查到的官方 API/CLI 证据落档：`python3 skills/n2d/_lib/image_backend_adapter.py record-refresh <作品根> --backend "<生图AI/生图渠道>" --source "<官方文档或CLI/API证据>" --source-url "<链接或留空>" --evidence-kind official_docs --exact-model-id "<本次实际模型id，可无>" --note "<本次能力结论>"`；`image_preflight` 会检查 `生产数据/image_backend_capabilities/<backend>.json` 是否为当天刷新，并要求存在 `capability_assertions`，且每项能力都有 source、source_url/evidence_kind 或 observed_text。`GPT Image 2` 在本仓是 OpenAI GPT Image 系列的归一标签；只有 `--exact-model-id` 或等价 per-run 证据存在时，生产事件才可把它当精确 provider model id 记录。证据不足只能说“当前未证实”，不能说“没有”。能力一旦证实存在，runner 必须把它接成可审计结构化入参，而不是继续把路径写进 prompt 里。
  - **Codex 多图入参落地铁律**：截至 2026-06-20 已查证 Codex CLI `codex exec` 支持 `--image <FILE>...` 多图附件，但未证实有持久主体 ID / 角色库。`codex_image_runner.py` 必须把每镜 `reference_bundle` 中 ready 的母本、定妆、道具、场景/VFX 图转成真实 `codex exec --image ...` 入参；中段/尾帧还必须把同 Clip 已有首帧/锚帧作为 `source_frame` 附件。每次生成必须落 `生产数据/codex_reference_bundles/第N集/<shot>.json`，记录 `reference_input_mode=codex_exec_image_flags`、`cli_image_input_count`、实际传入路径、sha256、来源角色/资产；`production_events.jsonl` 也必须记录 `reference_manifest`、`reference_input_count` 和 `reference_input_paths`。高风险角色镜不再因“Codex 文字引用”笼统阻断；真正阻断的是缺 ready 参考图、runner 未传 `--image`、或需要持久主体 ID 但后端未证实支持。网络错误、HTTP 5xx、传输断开及单次超时只允许按同一 target、同一编译请求做有限重试，不能悄悄跳到下一张；一轮 runner 的有界重试耗尽后必须记基础设施 fail，禁止无限重启同一 Codex 任务。
  - **图片后端止损/故障切换铁律（不得死磕 Codex）**：默认仍守“同项目/同集单一生图模型”，但用户已对本项目明确签核备用官方图片后端时，以下任一条件触发**一次性单向故障切换**：① Codex 明确返回 quota / credit / rate-limit exhausted；② 同一 target 的一轮 Codex runner 已耗尽其有界重试，且失败均属于 timeout / network / transport / HTTP 5xx。签核写入 `<作品根>/合规/image_backend_override.json`，至少含 `approved=true`、`scope=image`、备用 `backend`、原因和触发条件。触发后：记录 Codex infrastructure fail + backend handoff 事件；实时查询备用后端额度和当天官方 CLI/API 能力证据；从该张起改走备用官方 runner（本仓即梦为 `dreamina_image_runner.py`），不得再弹回 Codex、不得 Codex/即梦交替抽卡。已验收旧图可保留，但所有未生成/待重抽图统一走备用后端，并把角色 reference_group、脸锚、场景/道具参考、已验收相邻帧和完整 compiler 合同作为 handoff；首张备用后端图必须与最近已验收图做实际像素风格/身份/道具连续性对照，并跑 full `image_qc`。若 handoff 首图漂移到无法修复，再决定统一重出受影响镜，不能为了“单后端”继续烧已失效的 Codex 配额。没有项目签核时仍只记 fail 并停线，绝不静默换模型。
    - **即梦异步任务不得误判失败/重复扣费**：`image2image` 返回 `submit_id` 后，`query_result` 的 `gen_status=querying` / `queue_status=Generating` 且下载目录暂时为空，是正常排队/生成态，不是失败。runner 必须在本次 timeout 内持续轮询**同一 submit_id**，直到图片落盘、明确 terminal fail/cancel 或超时；禁止因为第一次查询无文件就重新提交同一 target。超时后也先用原 submit_id 查询回收，确认终态失败后才允许新建付费任务。
      - 若官方 CLI 已完成付费提交、随后在 `get_history_by_ids` 返回 `ret=2008` 而丢失 stdout 中的 submit id，runner 必须先用 `dreamina list_task` 按**完整本次 prompt**匹配最新保存任务并回收 submit id，再继续 `query_result`；不得把这类“提交成功、查询失败”当成未提交而重扣一次。
      - `--recover-submit-id` 只下载/收尾已有付费任务，不创建新任务，因此不适用“付费前 image_preflight”；runner 应跳过 pre-spend gate，但成图落档后仍必须跑该 target 的机器 QC、实际像素目视与 exact-hash QA 收据，恢复模式不是质量豁免。
    - **跨 Clip 精确状态接力母帧**：新 Clip 首帧若 `storyboard.json` 的 `continuity.start_state` 与上一 Clip 的 `continuity.end_state` 精确相同，且本帧不是无人物/无脸物件插镜，则即梦 image2image 必须把上一 Clip 最后一个、当前 hash 已有 `qa accepted` 收据的物理锚帧作为附件 1 `source_frame`；再附人物/场景/道具参考。这样继承姿态、手持点和道具拓扑，禁止只喂定妆图导致“肩挑扁担”在切镜后漂成“腰前横提”。没有 exact-hash accepted 收据时不静默借旧图。
  - **视频剪辑词不得污染物理关键帧**：故事板 `video_prompt` 归视频阶段所有；图片编译只保留单帧可执行的姿态/微动作，不把“跳切、蒙太奇、转场、分屏”等剪辑词直接喂给生图后端。每个首帧/中锚/尾帧都必须是一个连续相机画面，禁止三联画、多格漫画、拼贴和接触表；实际像素一旦出现分屏/拼贴，即使人物与道具正确也必须拒收，先修编译约束，再做有故障归因的返工。
- **本集视觉契约先行铁律（像素层 · 三层同源）**：出图阶段是**把视觉变量焊死成像素**的阶段——凡视频改不动的导演决策（色调 / 光位 / 轴线·视线 / 人物状态 / 景别阶梯）都必须在出图阶段下完，**不能下推到 `n2d-video` 的「本集导演一致性契约」**（到那一步首帧 PNG 已把这些烤进像素，太晚）。**真值源在上游**：n2d-script 已在分镜设计阶段把这些写进 `脚本/第N集/storyboard.json` 的 `visual_contract` 种子块——本步是把种子**誊抄+细化**进 `出图/第N集/prompt/00_总览.md` 的「本集视觉一致性契约」，**不是凭空发明**；种子缺失就回 `n2d-script` 补 `visual_contract` 再出图。契约至少五字段：**色调基线 / 场景光位锚 / 场景轴线·视线 / 角色状态演进表 / 景别阶梯**（格式见 `references/prompt_format.md §2.1`）。下游出视频契约再**继承**它——storyboard 种子 → 出图契约 → 出视频契约三层同源、不各写一套。`gate.py --stage image_preflight` / 生成后 `--stage image` 缺契约或缺任一字段即阻断（与出视频侧同级）。**`景别阶梯` 不止查字段在不在**：gate 还机检 `storyboard.json clips[]` 的**实际景别序列**——连续 ≥3 镜同景别、且段内无反打/过肩（对白正反打交替是合法变化，豁免）= 景别阶梯单调、缺远近/机位变化，记 WARN（`景别阶梯` 维度，`return_to_stage=image`），提示按导演意图穿插不同景别/机位。
- **本集基础视觉风格契约（风格层 · 三层同源）**：风格来自用户选择点 `基础视觉风格`，不是本 skill 写死的“真实电影感”。`storyboard.json` 的 `style_contract` 是真值源，本步必须誊抄+细化进 `出图/第N集/prompt/00_总览.md` 的「本集基础视觉风格契约」：**风格名 / 视觉基调 / 镜头与构图 / 光色策略 / 运动边界 / 风格禁忌**。每张首帧都按这份契约生成；写实电影感、国漫写实、二次元赛璐璐、水墨国风等各有自己的正向词和禁忌。`gate.py --stage image_preflight` / 生成后 `--stage image` 缺本契约即阻断；旧项目的「本集真实电影感契约」仅兼容，不作为新产物标题。
- **风格归属佐证（风格层 · 选定风格 vs 实际渲染机检）**：六字段是**存在性**+**负面词**约束，不能证明出图真是那个风格——选了「国漫写实」却整集漂成「照片剧照感/插画设定图感/欧美脸」时，色调可自洽、六字段可写全，但风格归属错了。补法：定妆阶段必须先为选定风格出 **1–2 张风格锚图**（style anchor，体现该风格该有的样子，默认存 `出图/共享/图片/风格锚_<风格名>.png`），登记进 `style_contract.style_anchor`（路径数组）并写入 `出图/共享/style_anchor_registry.json`。风格锚落档后必须先实际查看当前 PNG，再运行 `image_qc.py <作品根> --finalize-style-anchor --style-reviewer <标识> --style-review-kind <human|executor_visual> --accept-current-pixels`，把当前 SHA 与审阅类型写进 `human_review` 或 `visual_review`；执行者收据仍要求项目已明确授权，固定 `human_signoff=false`，不得用生成器内部状态切换或手改 JSON 代替。出图后 `image_qc` 的 `style_attribution`（纯 Pillow·默认环境可跑）以风格锚为基准，量本集帧的**风格指纹（饱和度/明暗对比/线条边缘度）**整集中位数对照——明显偏离锚=**warn·人判**（提示是否踩风格禁忌、回 n2d-image 重出偏离镜或重锚），归入 `style_consistency` 维度。**未登记锚 / 登记锚图缺失 / registry 未 ready 一律 production BLOCK**：runner 付费生成 Clip 前卡住，`image_qc` 和 image gate 也硬拦，不再降级成人审 warn；装了 VLM 后端可在上层升级成语义判定。阈值 env 可调（`N2D_STYLE_SAT_SCALE/CONTRAST_SCALE/EDGE_SCALE/DEVIATION`），应在真实渲染集按风格/后端标定。
- **风格锚输入隔离铁律（控制资产不是剧情剧照）**：生成风格锚时，只消费 `style_contract` 的风格名、材质/线条/色彩/光比语言与项目画幅；**不得把 `style_contract.镜头与构图` 中的剧情机位、前中后景、人物调度、地点、建筑、兵器、道具或妖物注入风格板**。风格锚用中性灰底的抽象色卡、光比阶梯、线条笔触与近裁材质样本表达完成度，不出现人物、动物/妖物、具体场景、文字或剧情动作；否则即使画面漂亮也必须作为“场景污染”废稿重抽，不能标 `ready`、不能喂给角色/资产定妆。
- **专项镜头模板继承铁律（复杂镜头 · 像素层锁变量）**：若 `storyboard.json clips[]` 有 `template/template_contract`，本阶段必须把模板契约誊抄到 `00_总览.md` 的「本集专项镜头模板速查」和对应逐镜 prompt。打斗/追逐/反打/真相揭示/公开对质/关系转折/法术爆发/飞行/亲密互动/多人站位的轴线、站位、证据物、反应链、关系前后态、接触点、关键帧、光效资产、负向约束，必须在首帧/尾帧里锁住；不能只靠 n2d-video 运动 prompt 事后补。`gate.py --stage image_preflight` 会先阻断 storyboard 缺模板或模板字段不全。
- **轴线/视线像素焊死铁律**：每个含角色的分镜 prompt 必填 `视线方向`（画左 / 画右 / 镜头外上方…），取自本场轴线，与反打镜对位。轴线和视线一旦烤进首帧像素，出视频只动作、不改站位/视线，**救不回**——正反打穿帮的根在出图，不在出视频。
- **场景光位锚铁律（光的一致性与物理级塑光）**：同一场戏跨镜的主光方向 / **色温 (Kelvin)** / 动机光源必须一致，否则剪起来闪（和脸漂同级穿帮，白平衡漂移是视频质感杀手）。像「场景定妆锁几何」一样给每场定一条**光位锚**，该场所有镜头继承。**光效参数必须物理化**：不再只写"暖光/冷月光"，必须写明确色温（如 `5600K 窗外冷月主光`, `3200K 宫灯暖色轮廓光`），并引入物理塑光手法（女性特写用 `Rembrandt lighting`/`Butterfly lighting`，压迫感加 `Negative fill` 负补光）。改光（吹烛 / 开窗 / 点灯）必须显式写剧情理由。每个分镜 prompt 的 ⑥光影 = 继承本场光位锚，不各打各的光。**色温数值化体检（gate）**：`光位锚` 字段的色温写成 Kelvin 数值（`3000K 暖`/`5600K 冷月`），`gate --stage image` 会做确定性体检——色温值离谱（超 ~1000–20000K）或**单一色温值与暖/冷描述自相矛盾**（如 `3000K` 偏暖却写"冷调"）记 WARN（混合布光的主光冷+轮廓暖不误判）。
- **状态演进铁律（人物集内连续性）**：人物的伤 / 泪 / 妆 / 服 / 发随剧情**单调推进、不回退、不提前泄露**。出图前在契约里列**角色状态演进表**，首帧逐张照表烤渐进状态——出血的镜后面不许干净、乱发不许自愈、觉醒前不发光。这条治集内连续性；跨资产改动（换装/锁脸微调）仍走 `scripts/asset_impact.py`。
  - **机器辅助（opt-in）：视觉状态账本 `scripts/visual_state_manager.py` + `n2d-review/scripts/state_ledger_build.py`**。把"左臂受伤/衣破/获得法宝"这类**跨集累积、会失效的可变状态**沉淀成 `出图/共享/visual_state_ledger.json`（kind=`n2d_visual_state_ledger`，注册在 `n2d/_lib/n2d_contract.py` 的 `BOUNDARY_PRODUCT_KINDS`；旧名 `PRODUCT_KINDS` 兼容）。默认只可跑 `visual_state_manager.py --audit` 做只读提示；若 storyboard 已有结构化 `visual_contract.角色状态演进`，优先用 `python3 skills/n2d-review/scripts/state_ledger_build.py <作品根> --episodes 1-10 --write` 确定性生成跨集动态百科，再按需 `visual_state_manager.py --inject N` 注入分镜 prompt（注入幂等）。状态简单的剧用契约里的状态演进表足矣，不把账本作为出图 prompt 完成的硬前置。
  - **边界（务必分清，别塞错层）**：`visual_state_ledger`=**状态演进层**（会变的状态修饰符）；`identity_registry.json`=**身份锁定层**（不变的定妆库人脸/形态/asset_key）。受伤/战损/脏污记进 ledger、绝不塞进 registry；角色身份/定妆登记进 registry、不塞进 ledger。两者互补叠加：registry 锁"是同一个人"，ledger 叠"这个人现在什么状态"。
- **首帧=起幅 + 运镜留余量铁律（出图为视频铺路）**：喂 image2video 的 clip **首帧抓起幅、不抓动作顶点**；镜头若声明镜内尾锚，动作顶点/落幅由 `图片/镜头N_end.png` 承接。首帧构图要为计划运镜预留框：推近→框略宽、环绕→主体周围留空、跟摇→运动方向留 lead room。阶段2 若已产 `生产数据/director_camera_plan_第N集.json/md`，逐镜优先读取其中 `image_prompt_injection`；缺 sidecar 先回 n2d-script 跑 `director_camera_plan.py --write`。封面/定格图例外，仍抓顶点。
- **关键帧按用途出图，不设普通镜默认尾帧/三帧**：先读 `continuity.seam_mode/end_anchor_required/frame_strategy/anchors[].use`。只有 `continuous_take_relay` 用 `need_endframe=true` 表示跨镜同帧；非 relay 若因大表情、高动作或构图控制需要镜内尾锚，写 `end_anchor_required=true`，不得冒充接力。R1/R2/R3 高风险连续动作或用户显式 opt-in 才出 `_mid/_aK`；E1 多镜位在明确切点出 `use=edit_cut` 边界图。`use=qc/reference` 只作验收。所有执行锚仍须从同 Clip/同 reference_group 母本 image2image 派生并登记时间、用途、来源。
- **检查清单双段硬闸门**：每个待生成的 prompt 块（共享定妆、本集分镜）在提交生图前必须同时具备两段检查；缺任一段禁止生图，先补 prompt。
  - 分镜图标题固定为：`检查清单（八维自查·最易漏②机位/⑥光影/⑦张力）` + `自检（生成后逐张过 · 落档闸门）`。
  - 共享定妆标题固定为：`检查清单（定妆自查·最易漏③人物/⑥中性光影/一致性）` + `自检（生成后逐张过 · 落档闸门）`。定妆不套完整剧情八维，但必须检查人物/场景/道具关键特征、中性光、不带戏、跨图一致性。
  - 执行阶段必须先核对标题存在，再提交 `生图模型 + 生图AI/生图渠道` 所选官方/已登录入口的生图任务；不要边生图边补检查清单。默认入口是 Codex / GPT Image 2；Dreamina/即梦官方 CLI 只能在用户签核例外后用于图片，第三方逆向或 web 自动化仍禁。
  - 口径说明：**分镜图**是剧情镜头，必须按导演视角八维装配，所以使用 `八维自查·最易漏②机位/⑥光影/⑦张力`；**定妆图**按产线规则是中性档案，不做剧情八维、不带戏剧光和情绪，只锁脸/造型/场景/道具基准，所以使用 `定妆自查·最易漏③人物/⑥中性光影/一致性`。以后所有出图都会先过这个检查结构再生图。
- **中英双 prompt 铁律**：共享定妆和本集分镜 prompt 块默认都写 `正向 prompt（中文）` + `正向 prompt（英文）` 两版。中文 prompt 更贴本土语义，但部分平台可能对中文词误触安全规避；英文 prompt 是同义兜底 and 海外后端兼容层。执行时优先用项目/平台最稳的一版；中文被拒或跑偏时，直接切英文版，不临场重写。
- **负向 prompt 后端适配铁律**：人读文档里的「硬性禁忌 / 风格禁忌」可以写成完整中文约束；但实际提交给后端的 negative prompt 必须按该后端语法归一。Imagen / Gemini 类后端优先用**平铺的 unwanted attributes / objects / artifacts**，避免把 `不要 / 不得 / 禁止 / no / don't` 这类指令句塞进 negative prompt；OpenAI/Codex 类也保持短词组优先，硬性行为约束放正向 prompt 或本镜约束里。适配器或人工执行时把「无字幕、无水印、不要血浆」归一成 `字幕, 水印, logo, blood splatter` 这类负面词；不要把一整段审查规则原样当负向 prompt 传给模型。
- **两层架构**：定妆（角色/场景/反复入镜道具）放**共享层**全篇复用；分镜出图（一镜一图）放**本集层**。
- **prompt / 产物分离铁律**：每个 `出图/` 目录（`共享/` 或 `第N集/`；旧项目 `common/` 仅读取兼容）都分两层——所有 prompt md 进 `prompt/` 子目录，定妆 PNG 与分镜 PNG 进 `图片/` 子目录。详见 `references/prompt_format.md §1 §2` 与 `n2d/references/architecture.md` "prompt / 产物分离铁律"章节。
- **本集图片命名空间唯一铁律（旧轮清场）**：`出图/第N集/prompt/01_分镜出图.md` 当前声明的目标 PNG 是本集 live 图片目录的**唯一真值**。重切分镜、重生成 prompt、从 7 段粗分镜改为 25 镜细分镜，或任何目标文件名/张数变化后，旧 `ClipNN_*.png` 若未被当前 prompt 声明，必须先移入 `废料/出图/第N集/...`，再继续生图；严禁旧轮与新轮同时留在 `出图/第N集/图片/`。同步要求：`storyboard.json`、`出视频/第N集/prompt/01_clips.md`、manifest/进度分母都必须指向当前目标集；视频阶段不得引用已归档旧图。`codex_image_runner.py` 生成前会拒绝这种混放，`image_qc.py` 落档后也会把当前 prompt 未声明的 live Clip PNG 记为 hard block。
- **强制 5 步 SOP**：每集出图 prompt 生成前必走"扫共享 → 列需求 → 差集 → 追加共享 → 建本集"，**跳过第 1 步必跨集脸漂移**。
- **同场景 batch-as-video-frames 默认路径（P2b·`scene_batch.py`·选择点 `同场景批量出图`=默认开）**：建本集分镜图前，默认先跑 `python3 skills/n2d-image/scripts/scene_batch.py <作品根> 第N集`——把 storyboard 里**连续同场景（同 LOC）≥2 镜**编成 `scene_coherent_batch` 作业（写 `出图/<集>/control/scene_batch_plan.json`）：这组首帧**共享场景定妆/光位锚/风格契约 + 同源种子，按一段连贯场景 pass 出再拆镜**，利用生成模型的时空一致性根治「同场景多镜漂移」（2026 DreamShot 思路）。**这是默认出图路径，不是 opt-in**；选择点 `同场景批量出图` 可关，单组 <2 镜或跨场景切换自动断组回退逐镜独立出。铁律：batch 只锁场景/光/风格，**不锁人物身份**（身份仍走两层定妆库 + 多人同框空间槽位绑定）。
- **共享先行硬闸门**：本集分镜 PNG 生成前，必须先把本集所引用的 `出图/共享/图片/` 共享定妆 PNG 全部生成并在 `出图/共享/prompt/00_索引.md` 标 ✅。**这里的 ✅ = 该定妆已过「生成后落档闸门自检」**（妆造逐项对角色卡 / 三件套同一个人 / 所有人物身份 DNA 零漂移，见 `references/prompt_format.md §1.2` 自检块），不是"出了张图"就算过——定妆是锚点，脸漂了下游每镜继承。**缺任一共享 PNG 或其自检未过时，禁止生成/重生成本集镜头图**；先补共享层、过自检，再以共享 PNG 作为参考图/角色参考生成本集图。
- **Clip 图前分档资产基础包铁律（总闸门）**：任何分镜 PNG 生成前，本集共享资产必须先满足“所属角色库档位 + 当前镜头实际需求”。所有具名人物先有正面、半身/全身服装锚、同源脸锚；`core_full` 再有前3/4/侧/后3/4/背/turnaround，`recurring_standard` 再有前3/4，`named_minimal` 只有在当前镜头为近景、转头、过肩、侧背或动作视线锁时才补相应角度，`restricted_partial` 只验允许局部。任何本档/本镜必需项为 planned 都不能放行。场景、道具、配饰、武器、法宝、VFX 仍须有参考图与 registry 结构约束，核心武器还要 `weapon_profile`。缺项时只能补共享层，**不得生成 Clip 分镜图**。共享库先行顺序不可被 `--skip-preflight`、P0 垂直切片、抽样验证、局部 `--shots`、`keyshot_candidate_runner` 或 `candidate_select --apply` 豁免；所有付费候选与候选晋升都复用 `enforce_shared_first_interlock`。
- **资产身份注册层铁律（P0 · 角色 ID / Face Lock / LoRA 适配）**：共享定妆库不再只是一堆 PNG 和 `00_索引.md`；必须同步维护 `出图/共享/identity_registry.json`，把每个角色形态登记成可复用身份。`reference_group` / `reference_atlas.build_tier` 按角色库档位校验：`core_full` 要正/前3/4/侧/后3/4/背 + turnaround + body + face anchor/expression；`recurring_standard` 要正/前3/4 + body + face anchor；`named_minimal` 要正 + body + face anchor；`restricted_partial` 只建允许局部。本镜实际需要却仍 planned 的角度必须先补成 ready。完整情绪库与动作参考按风险增强；下游近景大表情镜仍必须引用同源表情参考并做首尾双帧只插值。其它 `identity_adapters`、`angle_policy`、`drift_forbidden` 与逐镜 `CHAR_xx/形态` 绑定规则不变。每次补定妆/注册后跑 `n2d-identity --write`。
- **角色 DNA 五层铁律（P0 · 不再只说锁脸）**：产线统一把角色身份称为**角色 DNA**，五层固定为 **脸 / 发型 / 服装 / 配饰 / 质感**。角色卡、`identity_registry.json`、逐镜 prompt 和 QC 报告都必须按这五层说话：① 脸=脸型、五官比例、肤色、疤/鳞/痣；② 发型=发色、发髻/披发轮廓、发饰；③ 服装=款式、领口、袖型、材质、主辅色、剪影；④ 配饰=发簪、腰牌、护甲、钥匙、法宝挂件等标志物；⑤ 质感=皮肤毛孔、布料经纬、反光率等微相物理细节。`drift_forbidden` 不得只写 `face_shape`，还要覆盖会改变观众认人判断的 `hairstyle`、`outfit_palette`、`signature_accessory` 或更具体的锚点；逐镜 `近景/反打身份锁定`、尾帧/中段锚帧自检也要写“锁角色 DNA 五层”。只锁脸会出现第1集白发、第20集黑发、第50集红发这类观众认定换人的硬伤。
- **角色圣经铁律（Character Bible · 人读总入口）**：每个作品根必须维护 `设定库/角色圣经.md`，它是角色设定的人读总入口；`identity_registry.json` 是机器执行真值。角色圣经按 `CHAR_xx/形态` 聚合锚点句、五层角色 DNA 和气质/动作习惯；生成或修改定妆 prompt、分镜 prompt、video prompt、QC/返工说明时，先读角色圣经，再绑定 registry 的 `CHAR_xx/形态`，不得从散落角色卡临场拼设定。角色卡、角色圣经、registry 三者冲突时先停下对账；生产 ID 以角色圣经 + registry 为准。
- **角色资产包铁律（Character Assets · 可迁移打包层）**：所有入镜具名人物都必须维护项目内 `角色库/<CHAR_ID>__<slug>/manifest.json`，按 `reference/ prompts/ lora/ voice/ adapters/ qc/` 分区并登记 `library_tier`。它只替代旧 `设定库/character_assets/`，不替代更广的 `设定库/`、`identity_registry.json` 或角色圣经。短线角色使用 `named_minimal`，不是无包。跨作品复用走 `n2d-asset-market` 导出到 `创作区/制漫剧/_资产库/`；跨系列/机器只传经 `verify-pack` 的自包含单包，不直接复用旧后端身份。
- **固定 seed pool 铁律（辅助一致性 · 支持则执行、不支持则回退记录）**：`identity_registry.json` 的每个 `characters[].forms[]` 可登记 `generation_control.seed_strategy=fixed_pool`、`seed_pool` 与用途映射（turnaround/expression/closeup/shot）。执行时先按本镜用途取 `requested_seed`：若所选官方后端明确支持 seed，就把该 seed 传入并在 dashboard 记 `effective_seed=<同值> / seed_effective=true / seed_support=supported`；若 Codex/OpenAI/Dreamina 等当前入口未暴露或无法确认 seed，就**不把它当可复现生产线**，仍记录 `requested_seed=<池内值> / effective_seed=none / seed_effective=false / seed_support=unsupported_or_unknown`，然后回退到角色圣经 + `reference_group` + 后端主体/LoRA + QC。seed 只锁随机起点，不能替代角色 DNA、定妆参考组和审图。
- **角色表演层（P0 · 气质/动作进 prompt，不塞 registry DNA）**：五层角色 DNA 锁视觉身份；**气质/性格/动作习惯**锁“像不像这个角色在演”。角色卡和角色圣经可写 `气质/动作习惯`（如清冷克制、低眉含泪、量人目光、叩案施压），逐镜 prompt 在 `③人物` 或 `表演层` 继承；它不写进 `identity_registry.character_dna` 五键，避免把可变表演误当固定外观。
- **跨集成长升级铁律（P0 · 同一张脸，外层升级）**：长线角色从炼气期到金丹期、从病弱常态到掌权稳定态，必须让观众感到“同一个人变强”，不是换演员。`identity_registry.json.characters[].evolution_profile` 记录成长轨道：`identity_invariants` 锁脸型/五官比例/核心发际线/体态/标志疤痣，`allowed_evolution_axes` 只允许年龄体量、服装、法宝、气场/VFX、配饰权重和姿态气质升级。跨入新阶段时必须新建对应 form（如 18岁少年态 / 22岁青年态 / 金丹态 / 化神态 / 掌权态）+ 新 `reference_group/reference_atlas`，并用上一阶段正脸/脸部特写 image2image 派生；禁止纯文生图重抽新脸。**年龄敏感命名**：若 `evolution_profile.age_sensitive=true`，新增/重出的成长 form 与目标定妆文件名必须含年龄或年龄档，格式 `定妆_<角色>_<年龄或年龄档>_<形态>*.png`；旧项目无年龄 form/文件只能作 `legacy_alias`，必须补 `age_band/stage_label`，下一次补拍或重出时改用带年龄命名。**机检（E）**：`gate.py` 对 `evolution_profile` 渐进升级角色的**非锚定派生形态定妆**，若未声明「从锚定形态 image2image 派生」即 BLOCK（`跨集成长一致性`，`return_to_stage=image`）——纯文生图重抽=同一个人换脸，且下游每镜会忠实继承这张错脸。边界：临时伤、泪、脏污、战损仍走 `visual_state_ledger`；会跨多集复用并改变年龄体量/服装/法宝/气场识别的成长，走 `evolution_profile + form`。
- **年龄阶段定妆命名铁律（P0 · 看文件名就知道何时换定妆）**：少年成长、十年后、成年/中年、返老还童、长生态、境界跨度导致年龄观感变化的角色，不能只用 `定妆_<角色>.png` 一路复用。新建或重出定妆时，把年龄/年龄档写进 `forms[].form` 或 `forms[].age_band/stage_label`、`evolution_profile.stages[].target_file_prefix` 和所有共享 PNG 文件名：`定妆_贺平生_18岁少年.png`、`定妆_贺平生_22岁青年_侧.png`、`定妆_贺平生_300岁化神_三视图.png`。同一年龄阶段的正/前3/4/侧/后3/4/背/半身/脸锚/表情/turnaround 全部用同一前缀；不得把不同年龄阶段的参考图混进同一个 form。
- **UI/系统面板定妆铁律（P1 · 穿越系统流题材元素跨集一致）**：穿越/系统流的**系统面板/血条/等级框/属性条/签到/抽奖**以及牌匾匾额等**图中中文文字**，不是临场画的桥段而是和角色脸同级的**锁定资产**——AI 出图的 UI 版式与中文字渲染极不稳，逐集重画必漂。把它们登记到 `设定库/ui_asset_registry.json`（`assets[].{id:UI_*, frame, palette, font, layout, text_template, reference_png}`，schema 见 `n2d-review/references/扩展一致性登记表.md`），跨集复用同一张面板定妆底图、image2image 只换数值/文案区（必要时数值用独立文字图层叠加而非让模型画）。逐镜面板出图须绑定 `UI_*`；n2d-review 的 `系统面板(UI1)` 据此对账。
- **画中文字只做构图占位，expected text 必须交账**：凡分镜需要系统面板、牌匾、标题卡、弹窗、属性数字、血条数值或任何可读中文，出图 prompt 只能负责版式/留白/面板底图，不得依赖生图模型烤准文字。逐镜必须把期望文字写进 `screen_text_lines[]` / `expected_text`，绑定 `UI_*` 或文字资产，并标 `render_policy=compose_overlay_only`；落图后若只是占位图，要同步给 compose 留 overlay 区域和安全框。review/score 中 `text_render_consistency` 缺 expected text 或 OCR sidecar 时，先回本阶段补声明，再由 compose 叠字/出 OCR 证据。
- **场景 DNA 铁律（P0 · 角色归属感）**：观众记住的是“角色 + 环境”。长线/高频场景必须在 `asset_registry.json.assets[].scene_dna` 锁七项：归属锚、地标/识别物、空间布局/轴线、建筑材质/主色、光色/天气/气候、常驻物件/植被/水体、禁漂项。示例：青云宗不是泛称，必须锁悬空仙山、云海、白玉台阶、金色飞檐洞府、固定青石、灵泉、竹林。逐镜引用 `LOC_xx` 时必须继承 `scene_dna + constraints`，不能只写“仙门大殿/冷宫外院”临场重画。
- **服饰/形态定妆铁律（P0 · 换装不是状态修饰）**：同一角色只要出现会复用、会改变轮廓/主色/身份识别的可见形态，就必须独立登记 `characters[].forms[]` 并单独出一套 `reference_group`：红衣觉醒态、白衣常态、战甲态、伪装态、幼年态、妖化态都各自有 `asset_key` 和定妆组，逐镜 prompt 必须绑定匹配的 `CHAR_xx/形态`。每个可复用形态推荐补 `forms[].wardrobe_profile`，把服装从“白衣/红衣”自由文本升级成剪影、层次、领型、袖型、腰封、下摆、材质、纹样、主辅点缀色、禁漂项和允许状态的机器契约；`reference_atlas.outfit_refs` 登记全身、领口袖口、腰封下摆、纹样材质色卡等局部锚。禁止用白衣/常态/旧形态参考去生红衣/换装/觉醒镜头，也禁止把不同服饰的正侧背/表情图混进同一 form。短期可逆的伤、泪、血迹、脏污、破损、能量光效进 `visual_state_ledger` / 分镜状态演进，不进 registry；一旦换装会跨镜复用或改变服装主色/剪影，就升级成独立 form。`gate.py` 会提示不完整的 `wardrobe_profile`，`image_qc` 会从 `wardrobe_profile` / `character_dna.outfit` / 锚点句派生服装别名，拦“prompt 写玄青官袍却绑定月白寝衣 form”的单人角色镜。
- **资产引用注册层铁律（P0 · 场景/道具/武器库/独立服装/VFX ID 映射）**：关键非人物资产也必须有机器真值源 `出图/共享/asset_registry.json`，但不要混进人物身份层。反复复用或容易漂移的场景写 `LOC_xx`，关键道具写 `PROP_xx`，主角/核心反派长期使用的武器、法宝实体和封面级装备写 `WEAPON_xx`，独立复用服装/套装写 `OUTFIT_xx`，光效/VFX 写 `VFX_xx`；每条登记 `reference_group.primary`、`constraints`（场景锁 layout/axis/light_anchor，道具/武器锁 structure/件数/部件）、`drift_forbidden`。`WEAPON_xx` 还必须有 `weapon_profile`（设计意图、剪影、尺度、材质、色卡、纹样母题、携带方式、战斗用法、VFX 签名、禁漂项）和 owner/character_id；角色 form 用 `signature_equipment` 绑定。逐镜 prompt 的 `资产引用注册层` 必须写具体 `LOC_xx` / `PROP_xx` / `WEAPON_xx` 等，执行端据此自动取对应参考图和约束；用了场景/道具/武器参考却没写 ID，gate 阻断。详见 `references/资产引用注册层.md`。
- **主角装备库铁律（P0 · 设计审美 + 索引复用）**：主角图片设计不只设计脸、服装，也要设计其随身武器、法宝、坐骑/飞行器物和标志性道具。长期动作角色的 `identity_registry.characters[].forms[].signature_equipment` 必须引用 `WEAPON_xx/PROP_xx/VFX_xx`；`WEAPON_xx.weapon_profile.design_intent` 要明确“好看、大气、符合大众审美但不廉价堆装饰”的方向，并锁握持比例、携带方式、招式用途和禁漂项。打斗、追逐、腾云驾雾、御剑飞行镜头优先使用 `reference_group.scale_reference/wielding`，不要让视频阶段临场发明武器形态。
- **预算前硬挂钩铁律（P0 · 执行层不许松动）**：`image_preflight` 闸门不再只是「默认跑」的纪律提示——`codex_image_runner.py` / `dreamina_image_runner.py` 在**生成循环开始前**就先跑 runner 级 shared-first 顺序锁和 `gate --stage image_preflight`，**block 即拒绝生成、不花钱**（镜像 `video_runner` 的 `run_preflight_gate`）；并且生成后 `--stage image` 现在也接 `check_input_frame_qc`，**崩脸/接缝断/降级精度近景/脸覆盖缺口在最近的出图闸门即 BLOCK**，不再拖到最贵的「出视频」工位才发现。**所有逃生口都留痕，但共享库先行顺序不可逃生**：`--skip-preflight` / `--skip-final-gate` / `--skip-image-qc` 一旦使用，runner 自动写一条 dashboard `waiver` 事件（`dashboard.py waiver … --waiver <逃生口> --reason …`），让「执行时松动」从静默变成可审计；其中 `--skip-preflight` 只跳过普通 dashboard preflight，不能跳过 `enforce_shared_first_interlock`。同理 gate 侧的 `N2D_ALLOW_DEGRADED_QC` 降级放行记 WARN/waiver 而非静默通过。逃生口可以留（迁移/应急要用），但必须可见且不得改变“共享库先齐再碰镜头”的硬顺序。
- **被引用即必需机器证据（P2 · 自断言→机器派生）**：`check_referenced_assets_finalized` 不再是「缺字段=放行」的纯 opt-in。**项目一旦启用 finalize/锚点追踪**（任一 form/asset 登记过 `self_check_passed` 或 `anchor_sha`），本集逐镜引用的、确属本 registry 的共享定妆/资产**必须有机器可读证据**（`self_check_passed=true` 或 `anchor_sha`）——只靠人读 ✅ 或漏登记 = 缺证据即 BLOCK，堵住「给一部分置 true、其余留空就静默放行」。`anchor_sha` 单独算档①参考派生的机器证据；档②原生主体 ID / 档③ LoRA 的就绪另由 `check_identity_registry/route` 验，不强逼所有 form 都钉 anchor 而误伤档②/③。完全没启用追踪的项目（demo/先出视频）仍跳过，不突然阻断。
- **出图落档 QC 指纹防伪造（P2）**：`check_input_frame_qc` 的 freshness 只证明「报告声明的那批文件没变」，不证明「真把全部图都验了」——一份手写/陈旧报告可只声明 1 张图、算对那张 sha 就过。现在 gate 独立枚举 `出图/<ep>/图片/` 的真实 PNG，核对 image_qc 指纹是否覆盖每一张实际落档图，有真实 PNG 不在核验范围 = 没被机检 → BLOCK。
- **承载角色脸的资产·脸锚落档硬闸（P0·治定妆脸漂真因·后端无关）**：含具名角色脸的 `VFX_`/海报/关系图/封面板，其 `reference_group` 只能自引用尚不存在的产出 → 模型另画一张新脸，定妆阶段即脸漂（万妖血脉 VFX vs 沈念基础包正是此坑）。`carries_identity`（显式 `CHAR_xx[/形态]` 或按类型/人物上下文推断）治本，**此前只在 `codex/dreamina` runner 的出图前 spend 闸门 enforced**——手工出图/其它后端/旧图绕过即漏检。现在 `image_qc.audit_carried_identity_anchors` 把同一铁律前移到**后端无关的落档机检**：对 `asset_registry` 每个承载身份的资产，按 `identity_registry` 静态核验承载角色至少有 1 张 ready 脸锚可注入——0 张 ready 锚=`unanchored_identity_plate`、承载角色未登记=`carried_identity_unknown`，两码均进 `HARD_LINT_CODES` → `summary.hard_blocks` → `video_preflight` 据此回 `image`。复用 runner 的 `_asset_carried_identities`/`_collect_ready_image_paths`（单一真值源·不 fork）；逃生口同 runner `N2D_ALLOW_UNANCHORED_IDENTITY_PLATE=1`（降 warn 留痕）。
- **人物脸一致性铁律（P0·face_policy·治"含人资产镜自由生成脸"——大荒碎星戟握持镜脸漂真因）**：**任何会出现具名角色清晰脸的资产定妆（武器/道具/场景/VFX/海报/关系图），绝不允许放任后端自由生成脸。** 每个资产由 `codex_image_runner.resolve_face_policy`（单一真值源）判定脸策略，两条路、缺一不可：① **`faceless`**（武器握持比例/尺度参考——人只作背身/裁到下巴以下/无脸中性人台）：出图带 faceless prompt 锁句，落档 `image_qc.audit_asset_face_policy` 对已生成 PNG **实时像素核验**（`face_consistency.verify_faceless`），检出清晰脸 = `asset_faceless_face_detected` **硬拦**（**不信任**资产里手写的 `verdict`——证现实不证声明，一律重新像素核验）；② **`face_locked`**（持械动作/VFX 上身/海报/关系图/角色镜——必须保持承载角色身份）：**`_asset_carried_identities` 现已 owner-aware**——`owner: CHAR_xx`（不只 `carries_identity`）会被折入参考 bundle 的脸锚（修了"武器 owner 只写 owner 字段→旧逻辑捞不到→持械镜自画新脸"的盲区）；face_locked 却无任何 owner/承载角色 = `asset_face_locked_no_owner` 硬拦，再叠 `audit_carried_identity_anchors` 验脸锚 ready。两码进 `HARD_LINT_CODES`。缺 insightface → faceless 像素核验降级人审（`N2D_ALLOW_DEGRADED_QC=1` 留痕）。**红线：含人脸的镜，要么锁脸(喂 owner 脸锚)，要么无脸(像素验 0 脸)，没有第三种——人物脸一致性绝不放松。**
- **镜头不是对视对象铁律（P0·camera-is-not-the-gaze-target·治"角色总看镜头/摆拍宣传照"）**：为防脸漂反复堆「清晰正脸/主检脸/frontal」会把扩散模型带偏成**角色正对镜头摆拍/自拍肖像**，削弱力线、空间关系和真实感（打斗里视线本该锁对手·武器·撞点，而非镜头）。**锁脸不放弃，但身份可辨 ≠ 正对镜头**：① `codex_image_runner` 出图 prompt 已把主检锁脸句**重述**为「镜头是旁观者不是对手 POV，角色视线锁场内目标（对手眼/胸/腕·武器来路·攻击落点·破绽方向·被击撞点·对话对象），不与镜头对视；三分之二侧脸/侧脸/过肩/背侧轮廓即满足主检，不必也不应转正对镜头；打斗镜动作优先于脸」，并对**非 POV 镜**注入全局负面 `CAMERA_GAZE_NEGATIVES`（looking at viewer/eye contact/portrait pose/front-facing symmetric/fashion portrait/selfie·单一真值源 `n2d_const`）。② 落档 `image_qc`：动作镜直视镜头/正脸肖像倾向 = `combat_camera_eye_contact`/`combat_frontal_portrait_bias` **硬拦**（`HARD_LINT_CODES`）；非动作镜同倾向且无「不看镜头/视线锁定」防呆句 = `camera_gaze_portrait_bias` WARN（全场景覆盖）。**唯一例外**=本镜显式声明 POV/破第四墙/对观众压迫感特写（`CAMERA_GAZE_EXCEPTION_MARKERS` 豁免）。③ **生成侧前移**（治"QC 只在出图后检测、参考却仍把动作镜锚向正脸"）：`reference_planner.py` 对命中动作标记且非 POV 的镜标 `action_eyeline_lock` → **把 ¾/侧脸提为主身份锚**（`strength≥0.78`、排在 front 之前）、front 降权为辅助身份核对，并逐镜开 `pose_gaze_directive`（不看镜头·视线锁戏内目标·camera=observer + `CAMERA_GAZE_NEGATIVES`），缺 ¾ 参考则记补拍——让偏置在选参考/出图前就被掰正，而非交付后返工。**红线：除非声明 POV，角色绝不直视镜头；脸可辨但视线必锁戏内目标。**
- **缺核心检测工具→交付边界拦截（P1）**：compose/review 交付边界缺 ffprobe（双人声无法探测）、缺 insightface（脸/像素一致性降级）等，默认 BLOCK 而非静默/WARN 放行；统一逃生口 `N2D_ALLOW_DEGRADED_QC=1`（留痕·自负其责）。
- **合规与版权前置（P0 · 付费生图前）**：生图前必须已建立 `合规/compliance_manifest.json`。正式调用生图后端前默认跑 `dashboard.py gate --stage image_preflight`，它会先阻断：源文本/改编权/音乐音效/字体权属缺失或 pending；`identity_registry.json` 里的角色没有对应 `character_likeness` 授权记录；第三方/授权类 evidence 缺失；`distribution_intent` 与目标平台/地区冲突。源文本/同源改编按设计宪法 D4 默认 `original` 不因缺外部证明阻断；角色、声音和第三方素材授权仍照常拦截。角色长得再稳，不能授权发布也不能进付费生成。
- **占位配音放行铁律（仅视频先行 demo）**：`配音先行` 模式下 `配音=⏳rough` / `时长清单.json` 含 `占位:true` 不能过 image 付费 gate，必须先换真实配音并回写 `配音=✅`。只有 `制作模式=先出视频后配音` 时，`⏳rough` 才能作为显式选择的时间脚手架继续生成共享定妆与本集 PNG；本轮报告、`_设置.md` 或 prompt 总览必须醒目标注「占位配音驱动」。真实音色仍是正式成片/付费投放前的质量要求：换真实音色后若句长或镜头时长变化明显，应回跑 `n2d-voice` → `n2d-script` 阶段2 → 必要时更新出图 prompt，再决定是否重出受影响镜头。
- **角色锚点铁律**：每张含角色的分镜 image prompt 末尾**必拼该角色卡的『锚点句』**（3-5 个不可漂特征压成一句，见 `n2d-script/references/formats.md` 角色卡）——跨镜/跨集锁脸锁妆造，比单纯调参考图强度更稳，直接治"图片不准确/脸漂移"。
- **多人同框防串脸 + 多角度参考喂养（C3/C4/C6·image_qc lint）**：**多人同框由剧情决定、不回避（C6）**——这些 lint 是「把同框做对」的质量手段，**不是删镜/砍人数的理由**；该有的同框戏照出，用槽位+合成+足量参考保质量。① `multi_person_no_spatial_binding`（preflight 为 BLOCK，image_qc 作漏网/旧项目复核）——同框 ≥2 具名角色却没声明逐角色空间站位（blocking / 画左·画右 / 前后景）和 `多人同框身份槽位` 时必须补齐；2026 多主体模型(Seedream 4.5/Nano Banana Pro)支持按画面位置绑主体，给每角色绑位能在**生成端**按位锁主体防串脸（研究证实多主体身份混淆随参考数上升，但这是"要绑位"不是"要避开"）。② `native_multiref_underfed`（info）——定妆库已建多角度组(≥3)、本镜参考图块却只引用 1 张时提示喂全组；多参考模型(Seedream≤14/可灵 Elements≤4)按镜头从正/前3/4/侧/后3/4/背中喂满高相关角度锁主体更稳，单参考模型可忽略。③ 人数多到单帧难压时，**首选拆 establish+反打/分区合成把戏拍全**，而不是把同框人物删到"后端舒适区"——后端在变强，按当下短板砍戏会过期。
- **近景/反打身份锁定铁律（表情镜专项）**：CU/ECU、正反打、过肩反应、表情特写这类镜头不能只靠“深蓝宫装/整齐高髻”这种大类锚点。逐镜 prompt 必须增加 `近景/反打身份锁定` 字段：① 引用 `reference_group.face_anchor_refs[]` / `定妆_<角色>_脸部特写.png`；强情绪镜再引用 `reference_group.expressions[]` / `定妆_<角色>_表情.png`；② 明确锁 `脸型 / 五官比例 / 发型发髻 / 标志配饰 / 服装配色`；③ 相邻接力帧（如 Clip12_end → Clip13）要写“若发髻/脸型不一致即返工”；④ **近景必带微表情节拍**（见下「近景微表情深化铁律」）。没有完整表情库时，可以从已通过的正面/半身定妆**裁切脸部特写作为基础脸锚**先补，不要重新抽一张“表情定妆”制造第二张脸；这张脸部特写只能喂给官方后端做真实 image2image 派生，不能本地贴回正式镜头。`gate.py --stage image` 会阻断缺这条的正反打/反应/表情近景。
- **近景微表情深化铁律（FACS/AU 级 + GPT Image/OpenAI 表情表·治"近景空洞脸/表情漂"）**：3 档 `expression_span`(微/中/大) 锁的是**情绪跨度**，但近景观众看的是**肌肉级微表情**——只写"愤怒/隐忍"会出空洞脸或被模型重画。近景/特写人物镜的逐镜 prompt 必须在 `⑦情绪` 或 `表演层` 写一条 **`微表情节拍`**：用 **FACS Action Unit 级**可见线索描述本镜表情的**起止与峰值**，覆盖 **眉**（眉峰/眉头紧锁/挑眉=AU1/2/4）、**眼**（眼轮匝肌收紧/上睑提肌/眼神焦点/含泪将落=AU5/6/7）、**鼻唇**（皱鼻/法令加深=AU9/11）、**嘴**（嘴角微扬抿紧/下唇压/咬肌=AU12/14/15/17/23/24）、**呼吸与微动**（屏息/鼻翼张/喉结动/下颌微颤）。`expression_span=大` 的近景：首帧写**起表情的 AU 组**、尾帧写**止表情的 AU 组**，走首尾双帧只插值（锁脸不锁情），不让模型自由跨情绪重画脸。**表情库用 GPT Image/OpenAI 系列原生"表情表/expression sheet"批量产同源情绪库**：以角色正面脸锚为母图，一次 image2image 出该角色一脸多情绪（喜/怒/哀/惊/隐忍/将哭…）的同源 expression sheet，拆进 `reference_group.expressions[]`（同一张脸、只换 AU 组），比逐张重抽表情更同源、更省。微表情节拍写进 prompt 时优先英文 AU 线索（FACS 术语英文最稳），中文版给口语化等义。配角近景表情幅度上限按 `expression_span` 收（CU≤中、配角 CU≤微）。
- **尾锚图生图派生铁律（镜内/relay 共同，防纯文重抽换脸）**：凡产出尾锚的角色镜都不能用纯文字重新生成；逐镜 prompt 的兼容字段 `尾帧接力生成方式` 实际表示“尾锚派生方式”，必须写明以上一张成图或同镜首帧 `image2image` 为母图，只改表情/眼神/嘴角/微动作，不重画角色 DNA。`image_qc` / image gate 对声明尾锚却缺同源派生的角色镜 hard block。它只约束图片来源；尾锚是否与下一首帧相同仍由 `seam_mode` 决定。
- **尾帧身份交接铁律（防主镜身份拉扯尾帧角色）**：若一个 Clip 的 `资产身份注册层` 绑定 A，但 `尾帧 / _end / 下一镜入点 / 接力反应` 实际承担 B 的表情或失控入点（典型：主镜是沈念，`Clip_12_end.png` 是柳娘子反应），逐镜 prompt 必须额外写 `尾帧专用重抽提示`：① 明确尾帧服务哪个角色/形态；② 写目标 `CHAR_xx/形态` 或 `定妆_<角色>_<形态>_脸部特写.png` / 表情参考；③ 写清母图只保构图、光位、前景遮挡，目标脸按 B 的定妆锁定。只写中文名或只沿用主镜 `资产身份注册层` 不够，容易被 facefix/局部修复美化成通用脸。`image_qc` / `dashboard gate --stage image_preflight|image` 会把缺 `尾帧专用重抽提示` 或缺目标定妆引用记为 hard block。
- **角色 DNA 全链对照**：出图前对照 `references/角色一致性checklist.md`（建卡→定妆→复用→锚点→出视频 一条铁律链 + 出图前 30 秒速查）——把跨集“脸 + 发型 + 服装 + 配饰 + 质感”做成可勾选流程。
- **外部参考图身份限定铁律（防把参考图衣装搬进小说）**：定妆照生成若使用外部人物参考图，参考图**最多只提供脸型/五官/眼睛神态/体态比例/身材气质这类身份与体态信号**；发型、发饰、服装、配饰、妆容、身份阶层、磨损状态必须回到小说原文、角色圣经、当前剧情阶段和形态变体来定。参考图里的衣服、首饰、现代发型、拍摄妆造等一律视为污染源，不得复制进定妆；除非小说/角色卡明确写同款，否则 prompt 必须写“不要继承参考图服装/发型/配饰，只继承脸与体态”。若生成图把参考图衣装/发饰带入，按妆造漂移处理，重抽或重写 prompt。
- **角色定妆基础包铁律（分档生产，不一刀切）**：所有具名人物至少三类 ready 资产：① 正面主参考；② 半身或全身服装/体态锚；③ 同源脸部特写或表情脸锚；各档仍须锁定角色 DNA 中的服装配色与**配饰/标志物**。`core_full`（主角/核心长线/预计出场≥10集）再强制前3/4、侧面、后3/4、背面和 turnaround 人审拼版；`recurring_standard` 强制前3/4，侧背按实际分镜补；`named_minimal` 在近景、转头、过肩、侧背或多集复用时升档；`restricted_partial` 只建手部/肩背/服装/剪影局部，不生成清晰正脸。五角拆图必须同源、对齐，且拼版不能替代可喂图拆分资产。形态变体按所属档位生产，并从上一阶段主参考派生。详见 `references/角色一致性checklist.md §二` 与 `references/prompt_format.md §1.2`。
- **Codex 文本路径禁补拆分定妆**：Codex `image_generation` runner 没有稳定的原生 image2image/multiref 入参绑定，不能拿它逐张生成角色 `前45度/侧/后45度/背/半身/脸部特写`；否则每张都是新抽脸，必漂。该 runner 对这些拆分定妆默认 hard block。正确做法：① 从同一张已通过人审的五角 turnaround/设定表拆出正/前3/4/侧/后3/4/背；② 从已通过正面主参考裁切脸部特写和半身；③ 或切到真正支持官方 image2image/multiref/主体库的后端生成并回写 registry。只有 `front` / `turnaround` 候选可以走 Codex 文本生成后再逐视图人审，且未过人审不得标 ready。
- **同源母本派生铁律（防脸漂落地层）**：下一步不是继续逐张生成缺口，而是先拿一张目视通过的同源设定表/turnaround 当母本；`前45度/侧/后45度/背` 只能从这同一张图拆，`半身/脸部特写` 只能从已通过正面裁切。派生用 `python3 skills/n2d-image/scripts/derive_makeup_pack.py <作品根> --write`；启用逐张验收时必须加单个 `--view <three_quarter|side|rear_three_quarter|back|half_body|face_anchor_refs>`，每次只落一个 PNG，QC/目视通过后再派生下一张。新标准存在 `rear_three_quarter` 槽时按五列拆，旧四列 registry 保持历史映射、不得把旧背面误标为后3/4。脸锚固定输出 1024×1024 紧裁切，核心长线角色仍由 full QC 检查脸框占比。每个拆图在 `identity_registry.json` 写入 `derivation.method/source_path/source_sha256/crop_box`；没有来源指纹的拆分定妆即使 PNG 存在也不得标 `ready`。母本改过后必须重裁切并重签逐视图 hash 收据。
- **脸部锚信噪比门铁律（①·参考质量·`image_qc.weak_face_anchor` / `weak_face_anchor_core`）**：弱脸锚是被忽视的脸漂源头——`face_anchor_refs` / `表情_*` / `脸部特写` 这类**应当紧裁**的脸锚，n2d 当前制作目标是 **≥1024px、脸占画面 30–50%**；这是项目质量目标，不冒充跨模型行业标准。脸太小会削弱身份信号。`image_qc` 对已落档脸锚机检**脸占比（<12%）+ 裁切短边（<768px）**；这些数值阈值仍属启发式，应结合可复算像素证据和人工复核解释，不得据此宣称已外部校准。**只管脸锚**，不碰「双手可见」的宽身位主参考（那张本就该脸小——身份信噪比是脸部锚那张紧裁图的职责，二者分工互补）。检测器漏检风格化脸时只按分辨率判、不据占比误杀；degraded 精度仍可按分辨率判。
- **45° 镜头需要铁律（`reference_atlas.base_views.three_quarter`）**：45°/三分之二侧脸是 CU、过肩、反打和动作镜的高价值身份锚。它对 `core_full` / `recurring_standard` 是基础硬闸；对 `named_minimal` 不前置烧图，但一旦本镜是近景、转头、过肩、反打、极端角度或动作视线锁，必须先补为 ready，planned 不能放行。
- **语义漂移信号铁律（③·`semantic_drift` DINO/CLIP-I）**：服装/场景/道具/武器的 发型 H1 / 服装 N1 / 场景 O2 / 道具 P2 机检走**调色板 + dHash**（项目自标「初筛、非阻断」），盲区是**同色但剪裁/结构/布局变了**（月白圆领→月白交领、直剑→宽刃刀）——palette/dHash 抓不到。2026 身份保真评测标准：非脸身份用 **DINO + CLIP-I 图像级 cosine**。`semantic_drift.py` 把「资产参考 ↔ 本镜」的语义 cosine 当**第二意见**，覆盖**场景 / 道具 / 武器 / 服装**（服装按角色取 `定妆_<角色>` 全身板做对照——治「同色不同剪裁」这个头号 palette 盲区，月白圆领→月白交领）：palette 未报但语义低 → `semantic_drift_low`（warn·人判，抓 palette 漏掉的结构漂）；palette 报了但语义高 → `semantic_drift_lighting`（info·疑似只灯光/天气，降人审优先级）。关键场景/道具/武器/独立服装/VFX 一旦进入 scene/multimodal QC，若语义嵌入后端不可用，`image_qc` 会把“语义嵌入缺席”记为 block；必须补 full QC 环境重跑，人工复核记录只能辅助定位，不能替代 video/compose 前的 full QC gate。阈值 `SEMANTIC_FLOOR=0.55` 是起步线，应在真实渲染集按后端/风格标定。
  - **启用（降门槛·三条嵌入后端，默认顺序 DINO→open_clip→DreamSim）**：① `transformers`+`torch`（DINOv2 `facebook/dinov2-small`，默认优先）；② **`open_clip`+`torch`**（CLIP-I，比 transformers 全栈更轻、部分环境更易装到，自动 fallback；`N2D_OPENCLIP_MODEL`/`N2D_OPENCLIP_PRETRAINED` 可指定）；③ **`dreamsim`+`torch`**（2026 同主体判定基准·感知度量，**胜原始 CLIP/DINO cosine** 做"是否同一主体"；`N2D_SEMANTIC_BACKEND=dreamsim` 显式前置）。**注意 DreamSim 的 cosine 尺度与 DINO 不同——用它时按真实渲染集经 `N2D_SEMANTIC_FLOOR` 重标定 floor**（默认 0.55 是 DINO 口径）。装在 full 精度 conda env（与 image_qc 同环境 facefusion）。首次跑设 `N2D_ALLOW_MODEL_DOWNLOAD=1` 预热权重（之后读本地缓存、不再触网）。装好依赖后**它自动在 `image_qc` 落档时跑**（`payload["semantic_drift"]`），不用单独记一步；想对某集单独抽查场景/服装**结构**漂移，跑 `python3 skills/n2d-image/scripts/semantic_drift.py <作品根> 第N集`。无任一后端且本集有已登记关键非脸资产 → block，不再静默当通过；**sidecar 整段加载失败**（payload 无 `semantic_drift` 键）与「无后端」等价处理——一次模块加载异常不会让非脸兜底静默蒸发。
- **契约像素兜底铁律（④·`tone_light_contract` 色调/光位·纯 Pillow·默认环境可跑）**：本集视觉一致性契约把 `色调基线`/`场景光位锚` 标成 **block 级「焊进首帧像素」**，但全仓契约校验（`n2d_contract_diff`）只在**文本层誊抄 Diff**——出图写「冷青灰压暗」、视频誊抄对了就 pass，**从不核对像素里到底是冷是暖、是明是暗**（审计点名的最大「松动」：声称焊像素、实则零像素核对）。`tone_light_contract.py` 补这一刀：解析契约的暖/冷（暖金/3000K…vs 冷青/5600K…，**领先 token 定基调**，"冷…暖金点缀"判冷）+ 明/暗意图，量本集出图帧的**全局暖冷(R−B)·亮度(luma) 中位数**，**明确矛盾**（契约冷却整集偏暖 / 契约压暗却整集偏亮）→ `tone_warmth_contradiction`/`tone_brightness_contradiction`（**WARN·人判**·dim=style_consistency）。设计**保守**：默认 WARN 不升 hard（色调本身模糊，单帧暖特写不夺基调，故用**整集中位数**+宽裕阈值，宁可漏不可误杀）；与 semantic_drift 同样**自动在 `image_qc` 落档时跑**（`payload["tone_light_contract"]`，不用单独记一步），想单独抽查跑 `python3 skills/n2d-image/scripts/tone_light_contract.py <作品根> 第N集`。阈值 `N2D_TONE_WARM_MARGIN=12`/`N2D_TONE_BRIGHT_LUMA=165`/`N2D_TONE_DARK_LUMA=95` 是起步线，应按后端/风格标定。
- **契约像素兜底铁律（④·`shot_scale_contract` 景别阶梯·脸占比近似）**：契约 `景别阶梯` 此前只查 storyboard 里**人填的景别标签序列**，**从不看出图 PNG 的实际景别**——标 `CU 特写` 却渲染成大远景、标 `LS 远景` 却糊一张大脸，文本层全过。脸占比是景别强代理（特写脸大、远景脸小）：`shot_scale_contract.py` 把 storyboard 声明景别 × 实测脸占比对照，**只抓两端极端矛盾**（声明特写(CU/ECU)却脸占比 <`N2D_SCALE_CLOSEUP_MIN`(默认5%)=实为远景误标；声明远景(LS/ELS)却脸占比 >`N2D_SCALE_WIDE_MAX`(默认22%)=实为近景误标）→ WARN·人判·dim=style_consistency。**保守避误杀**：只在**检到脸**时判（`CU 铜镜` 等无脸特写本就合法，脸占比=None 即跳过）、中景/过肩/反打暧昧档不判。依赖人脸检测（与崩脸机检同栈 cv2/insightface），无检测器→available False 整段跳过（不臆造）。自动随 `image_qc` 落档跑（`payload["shot_scale_contract"]`），单独抽查 `python3 skills/n2d-image/scripts/shot_scale_contract.py <作品根> 第N集`。**剩 轴线视线/状态演进** 两字段的像素兜底仍是 follow-up（gaze/状态检测无廉价像素代理，靠 ④ VLM `vlm_verify`）。
- **VLM 语义判定铁律（④·`vlm_verify` 描述↔渲染图·opt-in 可 block）**：指纹（脸 G1/发型 H1/调色板 N1/O2/P2）和 embedding cosine（③ semantic_drift）都答「像不像参考图」，**答不了「符不符合设定描述」**——月白窄袖被画成交领、左腕核心识别疤丢了、素布发带变金步摇，embedding/调色板可能全过但**语义崩了设定**。2026 同主体评测基准（SAM3 抽轨迹 + MLLM verifier 核对角色描述）正是 **VLM-as-judge** 补这层。`vlm_verify.py` 把「角色/资产 canonical 设定（`character_dna`/`scene_dna`/`anchor_phrase`）↔ 本镜渲染图」交给 VLM 判：是否吻合、缺哪几项、置信度。**关键注册资产/角色 × 判不符 × 置信度≥`N2D_VLM_BLOCK_FLOOR`(默认0.6) → `vlm_semantic_mismatch` block**（既成语义崩，硬挡进 video，与 image_qc summarize/to_findings 接线，不塞 lint 避免被覆盖）；置信不足/非关键 → `vlm_semantic_review` warn 人判；吻合/判定失败 → 不加噪。
  - **启用（opt-in·厂商无关·缺则整段跳过不阻断默认产线）**：VLM 后端是**选择点**，经 `N2D_VLM_CMD` 注入一条命令模板（占位 `{image}` `{prompt}`，stdout 回判定 JSON `{"match":bool,"confidence":0-1,"mismatches":[...],"reason":"..."}`）。例：`export N2D_VLM_CMD='python3 ~/bin/vlm_judge.py --image {image} --prompt {prompt}'`，包装脚本可指向 Claude/OpenAI 视觉 API、本地 Qwen-VL/InternVL CLI 等任意能读图判文的命令，不 hardcode 厂商。`N2D_VLM_BLOCK_FLOOR` 按真实渲染集×所选 VLM 标定（与 semantic_drift floor 同理）。本机默认模板见 `n2d-review/references/vlm_backend.md`：未显式设置 `N2D_VLM_CMD` 时，若检测到 `n2dvlm` conda 环境 + 仓库内 `vlm_cmd_mlxvlm.py`，`vlm_verify.py` 会自动接入 MLX-VLM；显式 `N2D_VLM_CMD=off` 可关闭。装好后自动在 `image_qc` 落档时跑（`payload["vlm_consistency"]`）；单独抽查跑 `python3 skills/n2d-image/scripts/vlm_verify.py <作品根> 第N集`。没有显式命令且本机默认后端不可用 → `available=False` 跳过，绝不阻断无依赖产线。
  - **自一致投票（G1·2026-06-22·默认关）**：2026 VLM-as-judge 最佳实践是多次采样聚合提稳（单次判定不可靠）。设 `N2D_VLM_VOTES`（默认 1·零行为变化）≥3 时，每镜对 judge 自一致采样多次取多数票定 match；投票分歧 ≥`N2D_VLM_VOTE_DISAGREE`（默认 0.34）时**绝不硬挡**，本可 block 的镜降级 `vlm_semantic_review` warn 人判（judge 自己都拿不准，换 judge 或加采样复判）——与视频侧 VLM1（`n2d-review/video_vlm_consistency`）同口径。
- **多参考喂养按后端分层铁律（④·`image_qc` C4·info）**：`persistent_subject=True`（Seedream/可灵；Sora Cameo 仅旧项目/人工路径）逐镜应按**已注册主体 ID + 单张干净强锚**引用——2026 实践「单强锚 > 弱参考拼盘」，不必每镜堆全角度组（多样集只在**注册主体**环节喂）。所以对持久主体后端把「喂全组」的 `native_multiref_underfed` nudge 换成 `native_subject_anchor_ok`（ID+单强锚口径），不再误导其堆图；只有多参考后端（Codex/Dreamina/Nano 等 `persistent_subject=False`）才提示喂满全角度组。
- **半身服装参考裁切 + 居中铁律（落档闸门）**：`定妆_<角色>_半身.png` **必须从已通过自检的正面主参考裁切并放大/重采样回项目所选画幅**，用来提供更近的衣领 / 袖型 / 腰带 / 配色 / 手部服装信息；不得新抽一张半身导致脸漂，也不得把上半身贴到项目画布后用白底/浅灰底/空白补满下半截。半身服装参考还必须**人物主体居中**：头身中线接近画面中线，左右留白基本均衡，不能把大块空白或偏边构图喂给下游多图参考。下半截大块纯色补底、人物明显偏边都会污染下游多图参考，诱导分镜图出现截断身体、异常留白或角色偏位。角色定妆 prompt 的落档自检必须显式写入此规则；`gate.py --stage image` 缺该规则时阻断。注意：这是**定妆/半身参考图**的硬闸门，正式剧情分镜图按导演构图和运镜处理，不强制居中。
- **关键道具结构唯一性铁律（落档闸门）**：反复入镜或剧情关键道具（酒壶/瓶/瓷壶、匕首、白绫、托盘、铜镜、法宝等）必须在共享道具定妆和重道具分镜里**锁结构拓扑与数量**，防止模型把动作描述误解成新增部件。写法要具体：白瓷毒酒瓶/毒酒壶 = **唯一短颈圆口 / 无侧嘴 / 无斜嘴 / 无双口 / 无额外开口 / 无管状嘴**；短匕首 = **一柄一刃 / 无双刃 / 无多刃**；铜镜 = **单面单镜面 / 无多镜面 / 无重复镜框**；赐死托盘 = **白绫、短匕首、白瓷毒酒瓶三件套数量锁定**。不要写容易诱导结构幻觉的“壶嘴逼近唇边”；改写成“**白瓷毒酒瓶的唯一短颈圆口靠近唇边，不倒出、不新增嘴/管/斜口**”。关键道具出现侧嘴、斜嘴、双口、重复瓶口、多刃、多镜面、件数错 = 核心物件错位硬伤，必须重抽或重裁；`asset_registry.json` 的关键 PROP 必须写 `constraints.structure`，瓶/酒/药类还必须写 `constraints.must_not_have` 或 `asset.must_not_have`（如 `["壶嘴","侧嘴","喷口","出水口"]`）。逐镜 prompt 引用 `PROP_xx` 时必须继承这些禁项，`image_qc` 会以 `asset_must_not_have_not_propagated` block 漏传；出图后凡引用带 `must_not_have` 的关键 PROP 且 PNG 已落档，`image_qc` 会生成 `prop_shape_review` 逐图复核队列和参考并排图，未在 `生产数据/image_qc/<ep>/prop_shape_confirmations.json` 逐图确认无禁形前按 hard block 处理。`dashboard.py gate --stage image` 会合并该阻断；确认不了就重出对应 PNG。
- **武器实体 / 特效光轨分离铁律（落档闸门）**：武器是实体资产，刀光、爪光、剑气、妖气是 VFX 资产；二者不得在生图里互相变形。`WEAPON_xx` 必须锁**一柄/一把/一刃/单刃或明确的武器拓扑**、握柄、护手、刀背/刃口关系和唯一握持点；`VFX_xx` 必须锁“半透明光效/轨迹/气浪”，不得变成第二把实体刀刃、第二个刀尖、双向开刃或额外武器。横刀、短刀、匕首等默认不是双刃奇门兵器，除非 asset_registry 明确声明；否则出现双刃、多刃、刀光实体化、爪光变刀刃、同一手握出两把刀，都按 `prop_shape_review`/物料拓扑 hard block 归档重抽。逐镜 prompt 引用 `WEAPON_xx` / `VFX_xx` 时必须继承 `constraints.must_not_have`，并在动作句里写清“实体刀刃只有一条，VFX 只作光轨”。
- **道具/背景结构「在场恒存」铁律（跨镜·object permanence）**：锁拓扑只解决"长得对不对"，不解决"该在的还在不在"。**同一场景内已确立的常驻物件与背景结构（`scene_dna.常驻物件` + 场景内已立 `PROP_xx`）默认在该场镜头序列里持续存在**，不得在后续镜凭空消失、又凭空回来，或背景结构（门/窗/柱/陈设）逐镜 pop in/out——这是 2026 世界模型强调的 object permanence，纯 2D 生图最易翻车。**两条豁免**：① 近景/特写把道具裁出画框 = 出框，不算消失（构图正常）；② 剧情动作明确移除/取走/打碎该道具 = 合法状态变更，应在 storyboard 该场的状态/接力契约里**显式声明**（与 `角色状态演进` 同源记法），之后镜头不再要求其在场。写 storyboard/出图 prompt 时：同场景反复镜对常驻物件保持一致的存在与位置；要移除就写成显式状态变更，不要让它"自己消失"。人审侧由 `n2d-review` 逐场核常驻物件在场连续性（机检的视觉级在场检测属 backlog，先靠契约声明 + 人判）。
- **多图参考派生铁律**：含角色的分镜镜头图**一律用「定妆组 + 场景图」多图参考派生**（image-to-image / 多图参考 / 平台角色绑定），**禁止纯文生图（text2image）出镜头图**。能喂几张就喂几张：该角色正面主参考（主，强度 ~0.8）+ 侧面参考（侧脸/转头/过肩镜尤其加，强度 ~0.5-0.6）+ 背面参考（背身/转身/追逐/过肩镜加，强度 ~0.5-0.6）+ 半身/全身服装参考（全身动作、站位、服装易漂时加，强度 ~0.5）+ 本镜场景定妆（~0.4-0.5）。这是量产产线把跨镜相似度做稳的核心做法，比单纯堆 prompt 稳。锚点句仍每镜拼——两者**叠加不互斥**（参考图锁像、锚点句锁特征词）。
- **接缝分类铁律（尾帧不等于接力）**：每个 outgoing seam 必须由 P2 导演剪辑表显式选择 `continuous_take_relay / match_on_action / graphic_match / eyeline_cut / reaction_cut / insert_cutaway / j_cut / l_cut / dissolve / hard_cut / intentional_discontinuity` 并给对应证据。**只有 `continuous_take_relay` 要求上一镜尾帧与下一镜首帧是同一授权边界帧**，此时设 `need_endframe=true`、回填 `endframe_png`，并对齐构图、光位、人物状态及 SHA。其余模式允许相邻画面不同，分别靠动作相位、图形韵律、视线、反应、插入物、声桥、叠化时长或跳切理由成立；若它们仍需镜内尾锚，只写 `end_anchor_required=true`。任何尾锚都从同镜首帧 image2image 派生，但不得因此把普通剪辑误判为连续 take。
- **中段锚帧（默认规划·执行按后端能力）**：尾帧焊的是 **Clip 之间**的接缝；Clip 内部中段动作/景别/表情也可能漂。n2d-image 不自行决定要不要中锚，只执行 `storyboard.json`：若 `continuity.midframe`（单锚 `_mid`）或 `continuity.anchors`（N 锚 `_a1.._aN`）已由 `n2d-script/scripts/anchor_planner.py --write` 或人工声明，就逐张出**锚帧 PNG**；若 `policy.midframe_default=true`，未声明的镜头必须有 `midframe_exempt_reason`。锚帧内容 = 该 Clip `表演节拍` 在各 `at_sec`/`split_at_sec` 时刻的中间拍姿态，**同一套定妆组 + 同光位锚 + image2image 派生锁人**（以首帧/同镜成图为母图只改姿态，不重画脸/发髻/服装；打斗模板镜对齐 `template_contract.beats` 的起手/发力/命中/受击/收势）。出完回填 `midframe.midframe_png`/`anchors[].anchor_png`，并跟尾帧一样过 `image_qc`（锚帧崩 = 原生多帧或拆段接力都会崩，必须先修）。最终是否原生多帧、首尾 fallback、拆段接力或仅作 QC，由 n2d-video 按 `frame_control` 能力档决定。
  - **中锚是状态替换，不是叠加**：中锚 image2image 只继承角色身份/服装、场景几何/光位/轴线，以及既有道具的结构、总数量和归属；人物姿态、手握点、道具位置与接触状态必须替换为该 `at_sec` 的 storyboard 真值。禁止同时保留源帧旧姿态/旧位置又新增一套新状态（例如两只悬挂桶仍在、又在地上新增两桶），禁止复制人物、肢体或道具。实际像素发现“旧状态 + 新状态并存”必须拒收并先修编译约束。
  - **同目标局部返工母图**：若当前目标 PNG 的**当前 hash**已有执行者实际像素 `qa rejected` 收据，且拒收原因是可定位的局部数量/结构/脸部修正，同目标 Dreamina 返工必须优先把这张拒收像素作为附件 1 `source_frame`，再附脸锚/资产锚，只改收据点名的局部；禁止又回到更早首帧重算整套动作，导致已经正确的姿势、场景和道具状态反复漂移。当前 PNG 与拒收 hash 不一致时不得借用旧收据。
    - 若同一局部缺陷在“拒收像素母图”上连续返工仍未消失，必须止损，不继续死磕坏像素；可显式使用 `dreamina_image_runner.py --canonical-reset` 做一次 canonical reset：不附分镜源帧，只从同源人物身份锚、场景/道具 registry 参考重建。该开关只允许当前 PNG 当前 hash 已有 `executor_visual qa rejected` 收据时使用；重建后仍须重新跑机器 QC 和实际像素目视，不能沿用旧验收。
- **锚帧语义对齐铁律（首/中/尾不只要像，还要对剧情状态）**：锚帧必须同时对齐 `storyboard.json` 的 `start_state` / 中段节拍 / `end_state`、`dramatic_function`、状态演进和 UI/HUD `screen_text_lines`。尤其是系统面板、状态面板、数值变化、人物觉醒/受伤/变身这类 Clip，尾帧必须真的呈现最终面板/最终人物状态；不能把早一拍滚动面板、正面站姿或重复首帧当 `_end`。否则视频可能按 prompt 生成得可看，但 VSEM/S2V/SPECV 会拿错误参考锚做比较并在 video gate 误阻断。进入 n2d-video 前，先用 image gate / image_qc / 锚帧 contact sheet 人审首中尾语义；锚帧语义错位时回 n2d-image 最小范围重出，不用 `consistency_advisory_signoff` 代替修图。
- **帧生成顺序铁律（定妆库 → 首帧 → 中帧 → 可选尾锚）**：一个 Clip 的多帧是严格有序的 image2image 派生链。定妆库先行；首帧抓起幅；中帧从同镜首帧派生；声明了 relay 边界或 `end_anchor_required` 时，尾锚最后从首帧/已有中锚派生。relay 尾帧对齐下一镜同一边界帧；非 relay 尾锚只对齐本镜落幅，不要求等于下一首帧。首帧不存在则中/尾锚无源可派生，禁止并行各自文生图。
- **场景图建库复用铁律**：反复出现的场景（宫殿 / 冷宫 / 庭院）和角色一样进**共享定妆库**——出一次 `出图/共享/图片/定妆_<场景>.png`，跨集所有该场景镜头都引用它当参考图，**别每集重画背景**（背景漂移和脸漂移一样穿帮）。新场景走和角色相同的 5 步 SOP 入库。
- **视频兼容锚定铁律**：出图阶段不为了生视频而提前询问具体后端；若用户已明确固定生视频模型，image prompt 末尾拼对应模型的"图像风格锚定句"。未固定时，按 `基础视觉风格` + 通用视频兼容锚定出图，并在 prompt/总览标注 `video_backend_decision=deferred`；n2d-video 之后只能选择能消化现有首帧风格的后端，若用户临时固定不兼容后端，必须提示重出图/重拼锚定或改路由。
- **筛选宽容铁律**：候选图**能用就用，尽量不重抽**。只有"特别不匹配"才提重抽——即触发以下硬伤之一：① 核心人/物/场景错位（如该镜要木榻拍成石凳、该出现的人没出现）② 定妆脸/服漂移到识别不出 ③ 违反 prompt 检查项里的硬性禁忌（如要求"无血浆"却出血浆、要求"特写"却出全景）。轻微偏差（构图小动、表情微差、目光朝向略偏、环境细节小出入）→ 直接通过落档，**不要拖节奏**。
- **重抽预算铁律（两档全局统一 · n2d/mv/ad 同义）**：`重抽预算策略` 只保留两档，按 `../skills/n2d/references/选择点与偏好.md` 读 `_设置.md`→全局默认+首次问一次，**默认=预算充足**。旧值 `预算不足` / `预算不够` 一律归并为 `预算一般`。这里的“满意”以本张图的落档自检 + 用户/制作判断为准，每次重抽都必须记 dashboard 事件、保留候选或废料，不设固定次数上限：

  | 策略 | 主要人物 / 关键镜（爽点·反转·觉醒·威压·封面候选） | 配角 / 普通镜 | 终止条件 |
  |---|---|---|---|
  | **预算充足**（默认）| 严格自检，脸/妆造零漂移容忍；不满意就继续重抽/改 prompt/换参考，直到满意落档 | 同样严格自检；普通镜也不将就，直到满意落档 | 满意为止 |
  | **预算一般** | **只关键图片严格自检**；关键镜/主要人物不满意就继续重抽/改 prompt/换参考，直到满意落档 | 普通镜走筛选宽容：无核心错位、无身份漂移、无硬性禁忌即可落档，不追小瑕疵 | 关键图满意；普通图可用 |

  **关键图片判定**：标题或计划中标 `🔑关键镜`、封面候选、首镜/尾镜、爽点/反转/觉醒/威压、主要人物 CU/ECU/反打/情绪特写、多人同框核心关系、产品/道具/场景基准图、后续会被视频强引用的尾帧/中段锚帧。`预算一般` 下非关键普通镜仍要过硬伤自检，但不因为轻微构图、表情、环境细节偏差反复消耗。
- **生产数据记账铁律（P0）**：每次提交 `生图模型 + 生图AI/生图渠道` 所选官方组合、每次重抽、每张图落档后，都要调用 `n2d-dashboard` 记录事件：`stage=image`、`asset`、`status=pass|fail`、`duration_sec`、`cost/provider`（拿不到成本也要记耗时和 provider）、`redraw_reason`。正式/production 项目每个最终 PNG 的最新 pass 事件还必须记录 `recipe_hash`、`prompt_sha256`、`reference_bundle_sha256`、`backend_version`、`quality_tier`、`actual_image_inputs`、`input_fingerprint`、`settings_sha256`、`identity_registry_sha256`、`asset_registry_sha256`、`artifact_sha256`；若 seed 不可执行，必须明确 `seed_effective=false` / `effective_seed=none` / `seed_support=unsupported_or_unknown`，不能把“请求过 seed”当成可复现。若本镜/定妆登记了固定 seed pool，事件还必须记 `requested_seed`、`effective_seed`、`seed_effective`、`seed_support`、`seed_strategy`：支持 seed 的后端写真实传参，不支持/未暴露 seed 的后端写 no-op 回退，不能把 Codex 这类入口误报成可复现。`_进度.md` 只管 X/Y；成本、耗时、生成次数、重抽原因、最终通过率统一落 `生产数据/`，否则无法判断出图是否可工业化扩量。
- **出图落档机检铁律（生图后闸门 · 一致性把控）**：本集分镜全部落档后必须跑 `python3 skills/n2d-image/scripts/image_qc.py <作品根> 第N集`。它把 `n2d-review` 的一致性机检（角色 DNA 第1层脸 G1 / 第2层发型 H1 / 第3层服装 N1 / 场景 O2 / **道具·武器·特效 P2**（multimodal 组内离群，**B 前移到出图落档**，初筛非阻断）/ 接缝接力 / 锚点门 N3）**前移到出图落档**，复用同一套已校准纯函数与阈值（单一真值源），并 lint 逐镜 prompt（角色镜是否有参考图块/视线方向/锚点句/身份锁定句，**`CHAR_xx/形态` 是否在 identity_registry 合法存在**，**`LOC/PROP/WEAPON/OUTFIT/VFX_xx` 是否在 asset_registry 合法存在 + 用了定妆资产却没绑 id**（A 对称 CHAR_xx：`unknown_asset_id` block / `asset_ref_without_id` warn），尾帧身份交接是否有专用目标定妆锁定，**近景大表情镜是否引用基础脸锚 face_anchor_refs / 表情库 expressions / 脸部特写**（`no_expression_lib_ref` block，治表情镜脸漂），**资产状态机回退**（F：结构化 lifecycle 的 `lifecycle_regression` block，道具破了不能自愈）——gate 结构检查不替你验这些）。与生图前的 gate 互补：gate 查契约结构，image_qc 查真出的像素 + 漏拼，并读取 `production_events.jsonl` 抓**本地贴脸/换脸/裁脸贴回画面**产物。`verdict=block`（崩脸 / **接缝接力断**（尾帧没接上下镜首帧，出视频必跳切；seam_analyze 已对设计切镜降 info，故 block=真断）/ 纯文生图 / 非法 CHAR_id / **非法资产 id** / **资产状态回退** / **尾帧身份交接未锁目标身份** / **降级精度下的近景脸**（无 insightface 时 Pillow 降级无法验同人，CU/MCU/反打镜不放行）/ **降级精度下的多人同框帧**（A：无 insightface 时 detect_face_swaps 串脸检测整组失效，同框 ≥2 具名角色帧比照近景不放行——读 storyboard `character_ids` 判，单人中景不误杀）/ **本地贴脸修复产物**）必须修复后重跑；`cross_episode_face_drift`（B：把历年 `ep_mean_score` 串成时间序，调 `face_consistency.cross_episode_drift` 抓"每集各自过 floor、但整体逐集偏离锚点"的慢性漂移，advisory 级写进 `生产数据/face_drift_history.json` 增量累积、不 hard block，趋势性掉幅在硬伤前就预警）；`verdict=review`（发型/服装/场景/道具/武器调色板初筛、漏字段）交人二次判、确认误报可放行；不被噪声淹没。**降级精度近景脸会自动拼一张「定妆主参考 ↔ 本镜脸」并排对比图**（`生产数据/image_qc/第N集/face_review/`，Haar 几何粗筛优先级），**场景/道具/武器/特效漂移也拼「资产参考 ↔ 本镜」并排图**（`生产数据/image_qc/第N集/asset_review/`，D）让人眼一屏秒判。详见 `scripts/image_qc.py` + `scripts/asset_lifecycle.py` + `n2d-review/scripts/face_compare_stitch.py`。
- **关键 PROP 禁形/尺寸逐图复核（image_qc hard block）**：`image_qc` 对带 `must_not_have` 的 `PROP_xx` 不只查 prompt 是否传禁项，还会扫描已落档 `Clip_xx*.png`，生成 `生产数据/image_qc/<ep>/prop_shape_review/` 并排复核图；每张 PNG 都必须重出到无禁形且尺寸符合 `constraints.scale`，或在 `prop_shape_confirmations.json` 逐条写 `{"asset":"PROP_01","png":"图片/Clip_01_x.png","verdict":"ok","png_sha256":"..."}`，这里的 `ok` 表示**禁形和尺寸都已确认**，且 `png_sha256` 必须匹配当前图片内容；同名 PNG 重出后旧确认自动失效。未确认项会进入 `summary.hard_blocks`、`to_findings()` 和重生成清单，`dashboard gate --stage image` 返回非零。尤其瓶/酒/药类：无嘴白瓷小瓷瓶只允许唯一短颈圆口；侧嘴、斜嘴、喷口、奶嘴状瓶嘴、双口、额外开口、管状嘴，以及小瓶变大酒坛/大白瓷罐，都算硬伤。
  - 操作入口：`python3 skills/n2d-image/scripts/image_qc.py <作品根> 第N集 --prop-shape-report` 只列队列和最小重出范围；`--prop-shape-write-skeleton` 写 `verdict=review` 骨架（不放行）；人工看并排图确认后用 `--prop-shape-confirm-ok all --prop-shape-reviewer <name> --prop-shape-reason "<原因>"` 写 `ok`；配置了 `N2D_VLM_CMD` 时可用 `--prop-shape-vlm-confirm` 让视觉模型先批量确认高置信 ok，其余保留人工复核/重出。只想把 pending 转成 batch 重出参数，用 `--prop-shape-affected-shots`。
- **图片质检环境告知铁律（P0 · 不静默降级 / 不跳过 image_qc）**：进入 `image_preflight` / `image` / `image_qc` 前，先探测实际解释器与依赖，并明示给用户：`图片质检环境：full|degraded|none；当前解释器：...；建议安装：...；当前应停在/回退：image_preflight|image|image_qc_setup；原因：...`。三档口径：`full` = Pillow + cv2 + insightface + onnxruntime + buffalo_l model 可用，可跑脸嵌入/服装/场景/接缝/锚点门，image gate 结果才可当机器通过依据；`degraded` = 只有 Pillow 或部分像素库可用，必须明说缺失项，近景脸/**多人同框帧**/同人判断不可自动放行（A：无 insightface 时串脸检测失效），正式出视频前要安装 full stack 并重跑；`none` = Pillow 不可用或像素机检未跑，禁止宣称图片已质检，先停在依赖安装/`image_qc` setup，不能直接跳 `video`。推荐优先复用本机 `facefusion` conda 环境：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python -m pip install pillow opencv-python onnxruntime insightface scikit-image`，再首次运行 `FaceAnalysis(name='buffalo_l')` 预热/下载模型；没有该环境时新建 Python 3.10-3.12 conda env。系统 Python 3.14 不作为重视觉依赖首选。若 full QC 出 `block`，`return_to_stage=image`，列出受影响镜头/PNG/prompt 并只重出最小范围；若只有 `warn/review`，明确告知需要人审，不等于自动通过。
- **跨集高严重度漂移覆盖规则**：`cross_episode_face_drift` 的 `severity=high` 不再只是 KPI 预警；`image_qc.summarize` / dashboard gate 会把它计入 hard block，先回 `n2d-image` 补主体库/参考包/重抽并重跑 QC。`severity=medium` 仍作为趋势预警。
- **生图模型/渠道规则（安全硬闸门 + 后端选择点）**：
  - **① 安全铁律（invariant·硬·永不放行）**：只用**官方/已登录入口**（Codex 会话内置生图 / Codex 插件 / 官方 OpenAI 生图入口 / Dreamina/即梦官方 CLI / 官方厂商 API）；**绝不装第三方逆向 CLI**。`同视频AI` / `同视频模型` 含糊口径、非官方 CLI 或 web 自动化出图仍禁。
  - **② 模型 + 渠道选择（Codex image2 优先）**：`生图模型` 是生成轴，默认 GPT Image 2 / OpenAI GPT Image 系列；`生图AI` 是旧字段名，实际表示 `生图渠道`/访问入口，默认 Codex CLI。无用户签核时只走 Codex/OpenAI 图片入口；Dreamina/即梦官方 CLI、Seedream、可灵主体库、Nano Banana、Sora Cameo 等非 Codex/OpenAI 后端只能作为单项目例外，签核写入 `<作品根>/合规/image_backend_override.json` 后再花钱。旧项目 `_设置.md` 写 `同视频AI` 时必须改成显式生图渠道，并补齐对应 `生图模型`；视频阶段即使使用 Dreamina，也不代表图片阶段可自动切 Dreamina。
  - **③ API/能力适配（每次出图前刷新）**：`生图模型` + `生图渠道` 不直接驱动流程分支，先经 `image_backend_adapter.py inspect/recommend/probe` 归一为能力包：生成入口、编辑/掩码能力、多参考预算、是否有主体库/Character ID、输出 schema、探活方式和升级建议。`image_preflight` 会要求当天的 `record-refresh` 证据；没有证据即 BLOCK。若适配层评分显示当前模型/渠道不适合本集（如长线核心角仍用无持久主体后端），它会给 `生图后端适配` WARN：可升一档到 Seedream/可灵主体库等，但切换前必须统一 `_设置.md` 和 prompt，重做该集定妆/参考包，不能半集混用。
- **生图模型/渠道一致性提示（必须明说）**：每次进入正式生图前，先确认 `_设置.md`、`出图/第N集/prompt/00_总览.md`、逐镜 prompt 的 `生图模型` 与 `生图渠道/生图AI` 口径**统一到同一组官方/已登录模型+渠道**。发现混用或含糊/未授权口径时不要静默跳过，也不要边跑边修；直接对用户说：`检测到本项目生图模型/渠道口径不一致或混用（_设置.md=X，prompt=Y）。混用模型/渠道会导致同一角色脸型、服装、画风跨镜漂移。本次先停止生图，我会把设置/prompt 统一到同一组官方模型+渠道后再继续；同视频AI/同视频模型/第三方逆向/web 自动化出图禁用，默认 Codex/OpenAI，Dreamina/即梦官方 CLI 等非 Codex/OpenAI 图片后端需用户签核例外。` 然后统一口径并重跑 `python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image_preflight`。
- **多角色同框是硬触发点（剧情优先·把它做对，不是避开它·C6）**：**多人同框由剧情决定**——该有的同框戏照出，**不为迁就后端把人物删到"舒适区"**。真实情况：单帧 co-generate 多张**清晰具名脸**仍是**所有后端的共同难点**（GPT Image 2 也含；无可注册主体 ID + 注意力串扰，研究证实 ≥3 具名脸混淆上升、实测基线一致性≈85%）——**但这是"要用对方法做"，不是"结构性不可能"**。处理顺序按 ROI 从高到低，目标始终是**把这场戏完整拍出来**：
  - **① 分镜调度服务剧情（默认·最高 ROI）**：上游 `n2d-script` 分镜按戏剧需要排镜（见 n2d-script「多人同框分镜调度铁律」）。多人同框戏**优先用 establish 全景 + 景别分层 + 反打把戏拍全**（清晰主角领镜、其余过肩/前后景/反打承接），让观众看清每个人——这是**叙事手法**，不是为躲后端。**2-3 张清晰具名脸只是相对省钱/稳定的构图区，不是免登记区**：任一单镜清晰同框 ≥2 具名角色，都必须写 `多人同框身份槽位` + `多人同框执行策略`；剧情需要 ≥4 张清晰脸同框时照出，但必须优先走 split_composite / regional construct / 原生主体槽位，把每张脸分别锁住再合成或按位绑定。`gate.py --stage image_preflight|image`：单镜清晰同框 **≥2 具名脸且未登记身份槽位/执行策略 → BLOCK**（提示"登记分区合成/主体槽位把它做对"，**不是"删到≤1"**；远景群像脸不解析须显式标 `远景/群像` 豁免）；多人近景同框还必须声明反打/分层/分别出图等真分开生成路径，不能只写普通多参考。
  - **② 同框优先路由到原生主体 ID 模型（有则用）**：含 ≥2 具名角色、尤其 ≥3 清晰脸的镜**优先**路由到可注册持久主体的模型（Nano Banana Pro 免训练最多 5 人 / Seedream 4.5 多图主体 / 可灵 Kling Character ID；Sora Cameo 仅旧项目人工路径）并写 `native_subject_slots`——这类模型按位绑主体能在生成端直接锁脸，是同框戏的**质量首选**。默认生成模型 GPT Image 2（经 Codex CLI）在位绑定下单帧 2–3 脸已较稳；路由不到强模型时不强制切换，继续用 GPT Image 2 并做好 ③④ 强化（gate 不因"非主体库模型"阻断，只在缺 split/槽位/区分锚点时阻断或提示）。多参考别超喂，**2–5 张最佳**。
  - **③ 分区逐次构建 + 区域精修（GPT Image 2 等无主体库模型的同框首选实现）**：在 `persistent_subject=false` 模型，单镜 ≥2 具名角色 **BLOCK**，除非本镜同时登记 ① `多人同框身份槽位`（LEFT/RIGHT/FOREGROUND/BACKGROUND 逐一绑定 `CHAR_xx/形态`、屏幕位置、视线、脸部参考/表情库、primary 星标）+ ② `多人同框执行策略`（硬写 `regional_construct_required`，并保留兼容 token `split_composite_required`/`单人分层出图`，不是"若不稳再"）+ ③ `empty_plate`/`region masks`/统一融光。**这道 BLOCK 拦的是"没登记怎么把同框做对"，不是拦同框戏本身**。实现=**空场景底板 → inpaint/regional 逐区域各喂该角色 reference_group 把人画进去 → relighting/color match → Adetailer/IP-Adapter Face 脸部精修**（合法分区构建，**不是**禁用的事后贴脸，见「本地贴脸修复禁用铁律」边界澄清）；可叠 (c)〔可选增强·构图控制网〕用 pose/depth 锁站位（模型不暴露控制网时退回，**不为上控制网而混模型**）。
  - **④ 锚点去重（配合 ①③·降串脸）**：同框角色越像越易被模型平均成一张脸。逐主体写 **5–7 个互斥锚点**（各自唯一发色/发型/服装主色 HEX/标志配饰），并确保两两**不撞色**；`reference_planner.py` 会按 registry 的 `character_dna` 算 `distinct_anchors`（撞色对 + 处方），逐镜 prompt 须落 `区分锚点` 字段，gate 缺此字段对 Codex 多人镜记 WARN。
  - **⑤ 核心角色 LoRA 兜底**：反复出现且必须 CU 同框的核心角，前四步压不住时走 `n2d-lora`（一角一 LoRA，推理多 LoRA 叠加 + 区域绑定，别训多人 LoRA）。
  - 详见 `references/角色一致性checklist.md §四` 与 `references/prompt_format.md §2.2`。
- **后端生图判定**：选定后端后，确认它**能落 PNG**再开工。Codex 路线：检查 `codex features list` 是否启用 `image_generation`、`codex plugin list` 是否有可产图插件、当前 agent 是否有内置 `image_gen` 工具；生成后从 `$CODEX_HOME/generated_images/...` 复制/移动到作品目录，不能把项目资产留在 `$CODEX_HOME`。Dreamina 路线：检查 `dreamina` 官方 CLI 登录/会员状态和 `text2image`/`image2image` 可落盘参数。官方厂商 API 路线（Seedream/可灵/Gemini/Sora）：用官方 API/控制台，注册主体/Cameo 后按 ID 引用（见下「可选增强」）。**所选后端无法落 PNG 就停止并说明，不要偷偷换别的后端兜底**（换后端=混用）。
- **废料归档**：所有筛选拼图 / 废图 → `创作区/制漫剧/<剧名>/废料/出图/{共享,第N集}/图片/`，**绝不留在 Downloads 或散落作品根**。

## 逐镜参考规划（治跨集脸漂 · 出图前前置）

场景参考规划不是建议性孤岛：`scene_reference_planner.py` 产出的核心高复用场景计划必须指向真实 master plate/reference group；声称走后端主体库时，对应主体状态必须是 `registered/ready`；触发 scene LoRA 升档却仍未登记时，image gate 阻断。`scene_lock.py` 的执行回执与实际 primary/master 文件由 gate 对账，不能只写 planner 文案。

**为什么**：跨集脸漂的一个真因是——不同集的**服装/表情/景别/角度/光线**变化时，只靠**单张定妆照做图生图不够准**。定妆照对 AI 只是"固定板式"，身份判别细节不足，模型在新条件下会重画整张脸，逐集累积成漂移。光有核心五角 turnaround 定妆**不等于**每镜都喂对了参考。

**怎么治**：付费出图前先跑**能力路由的逐镜参考规划器**，它按**每镜变化量 × 所选后端真实能力**给出"这一镜该喂哪些参考 + 要不要控制网 + 要不要升档"的处方：

```bash
python3 skills/n2d-image/scripts/reference_planner.py <作品根> 第N集
```

产 `生产数据/reference_plan_第N集.{json,md}`（建议侧车）。逐镜逐角色：
- **近景/大表情** → 先引用基础脸锚 `face_anchor_refs`，强情绪高频角色再加表情库 `expressions`（缺真情绪表情库只剩中性特写时**标补拍**，与 image_qc 的 `no_expression_lib_ref` 互补：规划器 pre-gen 选、image_qc post-gen 验）；
- **极端角度 / `angle_policy.requires_extra_reference`** → 补侧/背/全身参考，或改分镜避开；
- **跨集记忆锚（G2·memory-sink）** → n2d-identity 的 `memory_anchor.py` 产 `生产数据/memory_anchor_plan_第N集.json`，规划器按文件契约消费（不互 import）：对**长间隔再登场 / 晚集 / 已测漂移**的角色，把其**最早集定妆记忆锚**作为最高优先锚（`role=memory_anchor`）前置注入、参与后端参考预算封顶——治"逐镜重注入仍随复现间隔衰减"。消费必须 fail-closed：plan v3 必须 `status=ready`、`available=true`、episode 精确匹配，当前 identity registry / drift report / storyboard 三个 SHA 都存在且与 `source_fingerprint` 精确一致，每个 `memory_anchor_refs` 真实存在且 current SHA 相符；角色 key 只许精确 `(character_id, form)`，单形态时才允许无歧义 name/cid 迁移，禁止子串串绑。核心/长线项目缺失、陈旧或 `status=warn` 的 plan 会进 `action_required` 并由 preflight 阻断；首个视觉集在确无更早 PNG 时允许 ready 空历史基线。`summary.memory_anchor_contract` 的 `required_char_keys / consumed_char_keys / consumed_clip_ids_by_char` 从最终真实 clip plan 反推，可逐项核销；
- **多人同框** → clip 级输出 `multi_subject_strategy`：无持久主体后端写 `regional_construct_required` + 身份槽位 + `empty_plate`/`region masks`/统一融光，并保留 `split_composite_required` 兼容 token；持久主体后端写 `native_subject_slots`；站位复杂且后端支持时叠加 pose/depth 锁站位；
- **无成本图片增强档** → 出图前跑 `reference_pack.py` 与 `keyshot_candidates.py`：把核心角色多角度/表情/动作姿态、场景 empty plate、道具/VFX sheet、多候选关键镜和选优 manifest 变成可审侧车，再进入付费生成；`keyshot_candidates.py` 还把**原著名场面/爽点兑现镜**（打脸/逆袭/封神/重逢/告白/复仇/真相大白/决战…）识别为 `signature_scene` 最高优先档（封面级 6 候选 + 跨后端多版兜底建议）——IP 改编漫剧的初始流量冲这些高光而来，必须一眼认出、做到位；该标签同时被 `n2d-model-router` 的跨后端英雄镜多版消费；
- **作品级封面（作品卡片封面·无成本 writer）** → `python3 cover_pack.py <作品根> --write` 产出 `出图/封面/cover_prompt.md` + `出图/封面/cover_job.json`：一张**竖版（9:16 / 约 5:7）**高点击率作品封面的 prompt/job 包。**只产 prompt/job + 合规留痕，不生成 PNG、不调后端**（C4/B4 优雅降级：纯净机上 `_meta.json` 的 `cover` 保持 `null`）。job 里 `生图模型` 落到**具体模型名**（如 `GPT Image 2`·C5），`生图渠道`/`访问入口` 作为 access path 分列，复用 `image_backend_adapter.current_image_backend_selection`。封面含具名角色时必须绑 `identity_registry` 的 `CHAR_xx/形态` + `reference_group` 同源脸锚（B7/B9）；脸锚未 ready 只标 `render_blocking=missing_ready_face_anchor` 交由出图 runner 生成前补齐，本 writer 不硬阻断。封面文案复用已有 `脚本/第N集/封面.md` 封面策略与本剧 `synopsis`/一句话卖点。渲染出竖版 PNG 并人审通过后跑 `python3 cover_pack.py <作品根> --backfill-cover`，用确定性 helper 把 `_meta.json` 的 `cover` 回填为作品根相对路径 `出图/封面/cover.png`（校验：在作品根内、真实可解码 PNG、不覆盖已有 `cover`）。`synopsis`/`cover` 字段读写单一真值源在 `../n2d/_lib/work_card_meta.py`。
- **best-of-N 自动选片（治批量抽卡人工瓶颈·2026-06-26）** → 一个可用镜常生 N 张候选靠人挑（行业实测 20-30 张/镜），批量产线最大人工触点之一。`python3 candidate_select.py <作品根> 第N集 [--clip 镜头X] [--apply]` 对 `出图/<集>/候选/<镜>/*.png` **自动排序选最优 + 判是否全废需 reroll**，写 `生产数据/candidate_selection_第N集.json`（`--apply` 才拷选中图到落档路径·不可逆=显式）。三层（缺则降级·绝不臆造）：① 硬伤确定性淘汰（崩脸/纯文生图/接缝断=`qc_hard_fail`，对齐**筛选宽容铁律**的三类硬伤）② **VLM ranker**（配厂商无关 `N2D_VLM_COMPARE_CMD`·占位 `{image_a}{image_b}{prompt}`·回 `{"winner":"a|b|tie"}`）在合格者间单淘汰选冠军——**关键：VLM 当成对 ranker 用、绝不当绝对打分器**（arXiv 2604.25235「VLM 能排序不能打分」，绝对分不可校准）③ 无 VLM 时按 face 余弦→QC→清晰度 确定性排序。最优者 face 余弦仍 < `N2D_CANDIDATE_IDENTITY_FLOOR`(默认 0.45) → 标 reroll（最好的也崩脸·别落档）；reroll 只出决策不自动执行（生成由后端命令做）。**Genflow 式纠偏 reroll（arXiv 2605.16748·2026）**：reroll 不止二元"重抽"，而是从**失败分布**（崩脸/纯文生图/接缝断/崩手/构图·读候选 sidecar 的 `qc_fail_reason`/`fail_codes` + face 余弦，确定性·非 LLM）生成**负权纠偏处方** `corrective`（该加的 negatives + 该强化的 reinforce + `raise_face_anchor`/`force_image2image` 标志），喂 runner 下一轮**有的放矢**重生成（动态纠偏 vs 固定 best-of-N 抽卡把可用率 42%→89%）。**可用率账本（yield·2026 工业级第一指标）**：每次选片把逐镜可用率（survivors/总生成）追加到 `生产数据/yield_ledger.jsonl`、重算滚动 `yield_summary.json`（reroll 后再跑记新一轮·可用率随纠偏回升可见；`--no-ledger` 跳过）；报告含 `yield`(集级)/`yield_summary`(滚动) 块，n2d-feedback/self_audit 可读看趋势；
- **按后端能力路由**（`IMAGE_IDENTITY_PROFILES`）：multi_reference 后端（Codex/OpenAI/Dreamina/Nano）组**逐镜多样参考包**（受 `max_reference_images` 约束）；persistent_subject 后端（Seedream/可灵；Sora 旧项目人工路径）未注册→**提示注册时喂多样集（多角度+多表情+多光）而非单 sheet**（Kling 优先 Custom Model 吃多帧/视频），已注册→按 ID 引用 + 参考双保险；
- **参考预算与入参清洁铁律**：出图前必须按后端容量选参考，不全量喂图；预算内优先级为**当前镜角色脸锚/表情 → 侧背/全身/服装体态 → 场景/道具 → 风格参考**。每镜落地 `参考图入参清单与预算`，列出 `backend_limit / selected / dropped / role_priority / input_files`，让执行者知道实际传了哪几张、放弃了哪几张、为什么。Gemini/Nano 类后端按官方口径最多约 14 张总参考、人物高保真参考约 5 张；超限时 `reference_plan` 标 `参考预算溢出`，人审应拆镜、升档或重选参考包。传入图只用本项目 ready 资产或已授权用户参考，并按所选官方后端要求做入参清洁：格式受支持、画面清楚、无水印/Logo/无关文字/NSFW；不合格先裁切、重出或剔除，再付费生图。
- **无持久主体 ID 后端 × 核心长线角 × 大变化镜** → 给锁定档升档建议（注册原生主体 / 启用 face_embedding / `n2d-lora init`），与 `face_drift_risk` / identity 漂移报表同口径。

**落地**：核心/长线角色与所有已明确人物镜默认必跑，产侧车后**人审把处方落进** `出图/第N集/prompt/01_分镜出图.md`（规划器不自动改已定稿 prompt）。`gate.py --stage image_preflight` 读 plan 做**落实对账**：核心/长线角色缺 plan 或 plan 有未落实行动项 → `参考规划落实` BLOCK；普通角色镜缺 plan → WARN。不能只生成 `reference_plan` 留在侧车里，必须把补拍/多样参考/控制网/升档建议写回最终 prompt 后再付费出图。写回后还要落结构化证据 `生产数据/reference_plan_application_第N集.json`（`kind=n2d_reference_plan_application`、`accepted=true`、`reviewer`、`plan_sha256`、`prompt_path`、`prompt_sha256`、`applied_action_count`、`applied_evidence[]`），让 gate 确认本次 plan 和本次 prompt 是同一版；不要手改 `reference_plan` 把 `action_required` 清空。

## 可选增强：后端原生角色ID / 主体库（opt-in · 比参考图派生更稳更省）

一致性方案有三档梯子，**默认走第①档**，往上是"参考图压不住时才上的重武器"：

> ① 锚点句 + 定妆**参考图派生**（默认，每次喂图）　→　② **后端原生角色ID / 主体库**（注册一次，按 ID 引用）　→　③ **LoRA**（自训，最重，见下节）

**第②档（本节）**：当生图模型/渠道支持把角色**注册成可复用的"角色ID / 主体"**时，用已过自检的定妆 PNG 注册一次，之后各镜**按 ID 引用**，不必每张重喂参考图——比参考图派生**跨镜/跨集更稳、也更省**（少传图少抽轮）。是 ②，先于 ③ LoRA 用尽（见 `references/角色一致性checklist.md §七`）。

- **哪些后端支持**（能力对照见 `references/platforms.md`「后端原生角色ID / 主体库」节）：可灵 Kling 主体库 / Custom Model / Element Library、Seedream Universal Reference（免 LoRA 跨图锁人）。Sora Character Cameo 仅旧项目/人工路径兼容，不作新项目默认推荐。**Codex/官方 OpenAI gpt-image、DALL-E、Gemini、Flux、Dreamina/即梦官方 CLI 无持久角色ID** → 不走本节，回退第①档参考图派生。
- **怎么做**：① 角色定妆过**阶段 C 硬闸门自检**后，`core_full` 用正/前3/4/侧/后3/4/背五角 + 半身/全身与脸锚，其它档位用本档 ready 资产，在后端**注册角色ID/主体**；② 把平台返回的 ID/句柄写进 `出图/共享/identity_registry.json` 对应 `characters[].forms[].identity_adapters.image.<backend>`，`00_索引.md` 只做人读提示，不当机器真值；③ 分镜出图按 registry 的 ID / reference group 引用 + 仍拼锚点句（双保险）。形态变体（觉醒态…）各注册各的 ID。
- **后端支持就强制注册核心长线角色（不靠"想起来"）**：当 `生图AI/生图渠道` 解析到的后端**支持原生主体**（Seedream/可灵等，`identity_registry` 该后端 `default_status=unregistered`）而**核心长线角色仍未注册**时，付费出图前必须先注册主体——这是省钱前置，不是事后补救。`gate.py --stage image_preflight` 已机检兜底：选了支持原生主体的后端 + 核心长线角色（registry `scope` 含 全篇/全程/长线/主角/主反派…）在该后端 `status` 非 `registered/ready` → 出 `原生主体注册` **BLOCK**。**Codex/OpenAI，以及签核例外的 Dreamina 等无持久主体后端不触发"注册主体"硬闸**——它们本就没有可注册的主体层，自动回退第①档参考图派生。短线配角/单元妖按「ROI 默认最小化」不前置注册，机检也不 nudge。**但长线 production 例外**：无持久主体 ID 后端跑**长篇/多集（≥3 集）**时，`image_preflight` 会另出 `生图AI一致性`（兼容维度名）**BLOCK**（`check_long_running_weak_backend`，函数名兼容旧测试）：核心/常驻角色必须有 native subject / Face Lock / face_embedding / 可用于当前后端的 LoRA / 已登记 `image2image_reference_chain` 之一；demo/探索仅 WARN，进入批量/production 前必须补锁。若 registry 未标核心/常驻角色也按同档处理，先补 scope/tier 再判断谁必须升档。
- **opt-in 边界调整**：第②档仍是“后端支持时才可用”的增强层；但一旦用户选择了支持原生主体的后端，核心长线角色就不再允许长期停留在未注册兜底。后端不支持 → 自动回退参考图派生；短线配角通常不注册角色 ID，并按 `named_minimal` 建最小角色包，镜头需要时再补角度。
- **与 LoRA 的关系**：先用尽本档（无需 GPU、无需训练），仍压不住脸的**贯穿几十集核心角色**才考虑下节 LoRA。

## 可选增强：LoRA 角色一致性（opt-in · 引导式）

默认角色 DNA 一致性方案 = **锚点句 + 定妆参考图 + 平台建角色**（见 `references/角色一致性checklist.md`），绝大多数角色已够。**LoRA 是其上的可选增强层，默认不启用。**

> 入口在哪：阶段 B 末尾「生图前确认」已就**主要人物的 LoRA / 指定参考图**问过用户一次——用户在那答「有 LoRA」时即进入本节流程；答「有参考图」走图生图派生、答「没有」走默认方案，都不进本节。本节是那个确认点的展开，不是另一道独立提问。

- **何时把它作为选项提出来**：某个**贯穿几十集的核心角色**（如女主）拼了锚点句、调高参考图强度后**脸/妆造仍反复漂移**，或用户主动问"要不要训练/LoRA/提高一致性"。提的时候说清三点：① 这是可选增强，不启用也能继续出图；② 只对核心长线角色划算，一次性角色不值；③ LoRA 是开源支线（Flux/ComfyUI），即梦/可灵不接受自训 LoRA，是**混合产线非替换**。
- **用户选择启用后**：路由到 `n2d-lora`，用 `skills/n2d-lora/scripts/lora.py` 管理 `lora_card/dataset_manifest/train_job/validation_report/register`。训练仍按 `references/lora_consistency.md` 的 Stage 0-5 引导，但所有产物必须落到 `设定库/lora/<CHAR_ID>/<形态>/`；验证报告未 `pass` 前不得把 registry lora 标成 `ready`。若 LoRA 只用于少量 hero 镜且底模/链路不同于本剧主生图模型，必须先用 `lora.py exception-scope` 写 `生产数据/lora_exception_scope_第N集.json`，声明 `clips/reason/project_image_model/lora_base_model/style_bridge/qc_required/not_a_project_model_switch=true`；否则按“生图模型混用”处理，回主生图链路或补范围。
- **用户不选**：继续默认参考图 + 锚点句出图，不要强推。

## 可选增强：多镜一次性故事板（opt-in · 连贯分镜批量出）

当所选生图入口支持多参考或批量生成时，可把**同一场景的一组连续镜头**作为一个**故事板批次**一次性生成，而不是一镜一图各自孤立抽。详见 `references/platforms.md` 各平台「多镜 / 多参考」字段。Dreamina/即梦官方 CLI 支持的故事/多参考能力可进入 n2d 出图链路，但仍必须整集统一后端、落 PNG 到项目目录。

- **收益**：同批镜头共享同一套角色 / 光线 / 场景潜变量 → 跨镜一致性更稳、也更快（少抽几轮）。
- **何时用**：同场景、同角色、连续 3-6 个镜头的段落（如一段对话戏、一个打斗 beat）。**跨场景大跳切不要硬塞进一批**。
- **怎么做**：把这组镜头的 `01_分镜出图.md` 块按场景聚成「故事板批次」，统一喂同一套定妆 / 场景参考图，按 `references/platforms.md` 各平台多镜语法**一次请求出一组帧**；产出仍按一镜一图落档到 `出图/第N集/图片/`，进度照常按张计。
- **回退铁律**：后端不支持多镜时**自动回退到一镜一图**（现有流程），绝不阻塞出图。它是加速 / 增稳层，不是新的必经步骤。

## 生成粒度 + 优先序（选择点 · 逐单位验收；可显式授权无停顿自检）

出图**默认不再整集闷头一次过**。真正调 AI 生图前，处理两个选择点：

- `生成优先序`（按 `../skills/n2d/references/选择点与偏好.md` 读 `_设置.md`→全局默认+首次问一次→沉默沿用）：**关键镜优先**（默认，`01_分镜出图.md` 里标 🔑 的爽点/反转/钩子/封面候选排队首，先定基调先锁主角脸）｜ **分镜顺序**（Clip1→N 叙事序）｜ **先易后难**（单人静态/空镜先，复杂打斗/多人镜后）
- `生成粒度`：⚠️**每次都问，不沉默沿用**（花钱/token 敏感点）——**每集进生图前必把下面四档菜单念给用户选一次**，`_设置.md` 里的值只作默认建议/预选。例外有两种：①用户在当前请求里明确说“中途不用问 / 一直执行 / 自动做到某集完结”等无停顿授权；②用户明确把“每张生成 → 机器 QC → 执行者实际像素目视 → 通过才下一张”设为跨项目长期规则，并由 n2d-settings 写入全局 `图片验收模式: 逐张机器QC+实际目视`。例外②固定等价于 `生成粒度=逐个`，后续生图动作卡不再重复弹粒度菜单，runner 一次正式调用解析多张时必须拒绝；两种例外都只免粒度问答，不免本次付费授权、合规闸门或必须由真人完成的发布签收。

**进入生图前必做（报盘 → 必弹菜单 → 排队）**：
1. 数清本集要出的**总量**并告知用户：「本集共需出 **X 张分镜图**（另有共享定妆 N 项将先在硬闸门处理）。先选这次的**切分颗粒度**：」
2. **原样展示四档菜单**（标出当前默认，等用户选定才开抽）：
   > 1. **逐个（一张/一Clip）** — 最细：每出 1 张图 / 1 个 Clip 就停下展示，等你确认或调整再继续下一个。最易即时优化，打招呼最频繁。
   > 2. **小批（默认每批 5 个）** — 折中：每批 ~5 个出完一起看、一停（批大小可随口改）。兼顾效率和可控。
   > 3. **按场景/段落分批** — 同一场景/段落的连续镜头作一批一停（天然贴合故事板分段，跨镜一致性也顺带更稳）。
   > 4. **整集一次过** — 一口气全出完最后统一看（最省打招呼，最串，最废 token/时间）。
3. 用户选定 → 按该档执行；可把选择写回 `_设置.md` 作下次默认建议，但**下次仍要再弹一次菜单**。若全局 `图片验收模式=逐张机器QC+实际目视`，本步直接采用“逐个”，不再弹粒度菜单。
4. 按 `生成优先序` 给本集分镜排出生成队列.
5. **共享定妆库永远排在最前**（阶段 C 硬闸门，与本选择点无关）——定妆没全 ✅ 不许出分镜。

**逐单位循环**（每个粒度单位 = 1 张 / N 张 / 一场景）：
1. 生成这一单位。
2. 走「筛选宽容 + 重抽预算」自检，落档 / 废料归档（与本节正交：粒度/优先序定**出的顺序与停审颗粒**，预算/筛选定**每张抽几次、何时放行**）。
3. **逐图即时 QC**：每生成并落档 1 张 PNG（含共享定妆、首帧、中段锚帧、尾帧），立即跑 n2d 自己的 `image_qc` 最小可用入口；当前脚本若只能全量扫描，就对当前作品/本集全量跑一次并只把新图相关 finding 作为继续/重抽依据。`block` 或降级精度命中近景/多人同框时先修这张，不继续生成后续图；`review/warn` 必须在本线报告里留下人工签收或重抽记录。不得把这一步抽成公共实现，也不得复用其它系列的 QC 实现。
4. 执行者必须实际查看当前像素，并按 prompt 的「自检（生成后逐张过）」复核脸、手、人体、构图、身份/资产、光位和禁忌。普通交互模式再停下来给用户看并询问；**当前请求已有无停顿授权时，逐个自动自检后继续，不弹确认**。
   - storyboard 的 `insert/ECU/局部/特写` 若当前物理帧只拍手、脚、桶、盆、容器、器具、道具、伤口或水下细节，按 `detail_insert` 处理：仍检查手部/道具/构图与连续性，但不要求不存在于画面的角色脸做 embedding 覆盖；纯物件镜同理不得用后续人物镜替代当前时点。
5. `block`、执行者目视硬伤或 QC 能力降为 `degraded|none` 时，只允许归档废料、修 prompt/参考或重抽当前单位；`review/warn` 必须由执行者完成实际像素复核并留下结论，不能因自动模式静默放行。通过后才出下一单位。
   - 全局 `图片验收模式=逐张机器QC+实际目视` 时，目视通过必须用 n2d-dashboard 写 `event=qa,status=accepted`，并在 `meta.artifact_sha256` 绑定当前 PNG；runner 会阻止不同目标越过缺失或旧 hash 的验收事件。同目标重抽不受阻，便于一直改到满意。
6. 每单位落档后即回写 `出图` 列分子（X/Y），进度随时可查（`n2d-progress`）。

> **无停顿不等于批量后补 QC**：即使用户要求“一直执行到完结”，顺序仍是“一张生成 → 一张落档 → 一张 QC → 一张实际查看 → 通过后下一张”。runner 默认的逐 target `run_target_image_qc` 不得用 `--skip-image-qc` 绕过；该 flag 只允许调试/迁移并必须留下 waiver，不能用于正式生成。批次/整集完成后仍要再跑一次全量 image gate。执行者实际像素目视只有在 `_设置.md` 明确记录用户授权时，才能按 `review_kind=executor_visual`、`reviewer_role=ai_visual_executor`、`human_signoff=false` 写独立收据；它绝不是人工签收，也不得伪造 `identity_eval_pack` 的人工 reviewer。遇到必须由真人签收的发布合同仍只能保留待签状态。

> **整集档例外**：选 `整集` 才回到旧行为（>10 张可 spawn 子 agent 并发、最后统一报告），不逐单位停审。`小批`/`按场景` 在「批」层停审。

## 输入前置条件

- 作品根存在，`_进度.md` 该集 `分镜设计` 列 ✅（= 按 `制作模式` 定稿：`原生音画` 由 storyboard 推 `镜头时长.json`，不要求 `配音` 列 ✅；`配音先行` 必须真实配音后定稿；`先出视频后配音` 只在用户显式选择 rough timing 后放行）。
  - 该集产物齐：`脚本/第N集/storyboard.json` + `分镜剧本.md` + `素材清单.md` + `生产数据/script_quality_contract_第N集.json`（QUICKSTART 旧清单列的三件仍兼容，但正式出图 prompt 前必须有剧本可看性合同）。
  - **占位配音做 demo 的前置（易踩空）**：`分镜设计 ✅` 由 `finalize_storyboard.py` 写，而它**默认拒绝占位配音定稿**。所以"视频先行 + 占位驱动出图 demo"这条路要先用 `FINALIZE_ALLOW_PLACEHOLDER=1 python3 n2d-script/finalize_storyboard.py <作品根> 第N集` 定稿，拿到 `分镜设计 ✅` 且 `_进度.md` `配音=⏳rough` 后本步才放行（见下「占位配音放行铁律」）。`配音先行` 模式不要加这个环境变量，先补真音。
  - 出图 prompt 中每个可执行共享资产块/逐镜块必须有与当前完整合同、项目画幅和所选图片后端一致的 `后端编译提交 image prompt`；缺块、source SHA 过期、compiled hash 错、后端/任务 profile 不符、内部路径泄漏或悬空附件编号都会在 `image_preflight` BLOCK。
- 正式生图前必须先跑确定性 preflight gate 并入账：`python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image_preflight`（内部调用 `n2d-review/scripts/gate.py --json`；检查合规包、版权/改编权/角色形象授权、占位提示、`storyboard.json`、尾帧契约、共享定妆索引、资产身份注册层、资产引用注册层、本集视觉契约、本集基础视觉风格契约、专项镜头模板契约、出图 prompt 严格结构、**P0 语义谱系继承 / P1 状态百科**）。缺合规包时先跑 `python3 skills/n2d-compliance/scripts/compliance.py <作品根> 第N集 --init`，人工补齐后再 `--check`。`image_preflight` gate 会阻断以下漏项：**缺 `合规/compliance_manifest.json` 或版权/改编权/角色授权未通过**；**缺 `出图/共享/identity_registry.json` 或角色/形态缺 `character_dna.face/hair/outfit/accessories`、`reference_group` / `reference_atlas.build_tier` 本档必需项未 ready（所有具名人物要 front + body/outfit + face anchor；core_full 追加 three_quarter/side/rear_three_quarter/back/turnaround，且五角 + turnaround + 至少一张 expression/face anchor 必须有绑定当前 PNG hash 的逐视图人工声明收据；recurring_standard 追加 three_quarter；named_minimal 的额外角度按本镜真实需要补）、`identity_adapters`、`angle_policy`、`drift_forbidden`，任一人物角色缺 `asset_bundle.manifest`，production 核心动作角色缺 `signature_equipment`，已启用 `generation_control` 但 seed_pool/usage/backend_support/fallback_policy/record_required 不完整**；**缺 `出图/共享/asset_registry.json`，或关键场景/道具/武器缺 `reference_group` / `constraints` / `drift_forbidden`，`WEAPON_xx` 缺 `weapon_profile`，反复场景缺 `scene_dna` 七项环境锚，或逐镜用了场景/道具/武器参考却缺 `LOC_xx` / `PROP_xx` / `WEAPON_xx` 绑定**；**本集总览缺「本集视觉一致性契约」或缺五字段（色调基线/光位锚/轴线/状态演进/景别阶梯）**；**storyboard/总览缺 `style_contract` /「本集基础视觉风格契约」或缺六字段（风格名/视觉基调/镜头与构图/光色策略/运动边界/风格禁忌）**；复杂 Clip 疑似打斗/追逐/反打/法术/飞行/亲密互动/多人站位但缺 `template/template_contract` 或模板字段不全；逐镜缺参考图 / 双语正向 prompt / 负向 prompt / 导演八维 / 检查清单 / 生成后自检 / 重抽预算 / **光位锚字段 / 起幅·运动余量字段**；含角色镜头缺锚点句、脸/妆造漂移自检、服装/配色约束、**视线方向**；共享定妆 prompt 缺目标存档、双语、负向、定妆组、锚点或落档自检；P0/P1 命中语义断继承、状态提前泄露/漏继承时会带 `return_to_stage`、`affected_shots`、`affected_artifacts`。命中后先补 prompt/合规包，禁止直接生图.
  - **`image_preflight` 和 `image` 都会合并 `image_qc` findings**（dashboard 在 n2d-image/n2d-review 之上、用 subprocess 调，无循环依赖）：除上面的契约结构检查外，同时跑 `image_qc` 的角色 DNA 像素机检（脸 G1 / 发型 H1 / 服装 N1）+ 场景 O2 / 接缝接力 / 锚点门 N3 + 逐镜 prompt lint（参考图块/视线/锚点句/`CHAR_xx` 在 registry 合法性/尾帧身份交接锁定）。**生图前跑 `image_preflight`**（无 PNG）时像素项自然空、lint 仍提前抓非法 CHAR_id / 纯文生图风险 / 尾帧换主体却未锁目标定妆；**生图后跑 `image`** 则真验像素。`image_qc` 的硬阻断（崩脸 / 接缝接力断 / 纯文生图 / 非法 CHAR_id / 尾帧身份交接未锁目标身份 / 降级精度近景脸）会让 gate 返回非零；初筛项（hair/outfit/scene 调色板/dHash）记为 warn 交人判，不被噪声卡死。所以阶段 E 落档后回跑一次 `dashboard gate --stage image` 即等于完整出图阶段总闸。
- 否则报错并建议用户先调 `n2d-script <作品根> 第N集`

## 工作流

### 阶段 A — 出图 prompt 生成（5 步强制 SOP）

**① 扫描共享库**
- 读 `设定库/角色圣经.md`（人读总入口；若不存在，先从角色卡 + `identity_registry.json` 生成/补齐骨架，再继续出图）
- 读 `角色库/_index.json`（若存在；项目内角色资产包索引，只做可迁移资产打包层，不替代 registry/bible）
- 读 `出图/共享/prompt/00_索引.md`（若不存在则首次创建——格式见 `references/prompt_format.md §1`）
- 读 `出图/共享/identity_registry.json`（若不存在则创建骨架——schema 见 `references/资产身份注册层.md`）
- 读 `出图/共享/asset_registry.json`（若不存在则创建骨架——schema 见 `references/资产引用注册层.md`）
- 盘清楚：已有哪些角色（含形态变体）/场景/道具，及状态（✅/⏳/⬜）
- 同步盘清：每个角色形态的 `reference_group`、`reference_atlas`（基础视角 / 表情 / 动作 / 选图策略）、角色级 `evolution_profile`（成长阶段 / 身份不变量 / 允许升级项 / 当前阶段）、后端角色 ID/Face Lock/LoRA 状态、`generation_control` 固定 seed pool、允许角度、禁漂项；缺项先补 registry，并跑 `n2d-identity` 生成 adapter matrix，不进入分镜出图。若项目/后端支持 seed，后续按 pool 传参；若不支持，仍按 pool 记录 `seed_effective=false`，不把本次结果当可复现。`reference_atlas` 槽位只有 `status=ready` 才能实际传图；`planned` 只记缺口，不当参考图使用。
- 同步盘清：所有人物角色/形态是否有 `characters[].asset_bundle` 指向 `角色库/<CHAR_ID>__<slug>/manifest.json`；若已建资产包，读取其 reference/prompts/lora/voice/adapters/qc 摘要和缺口。资产包缺失会阻断任一入镜人物；短线/功能角色建最小包即可，LoRA/主体 ID 可标 `not_needed`。
- 同步盘清：每个关键场景/道具/武器/独立服装/VFX 的 `LOC_xx` / `PROP_xx` / `WEAPON_xx` / `OUTFIT_xx` / `VFX_xx`、`reference_group.primary`、场景 `scene_dna`（地标 / 空间布局 / 建筑材质 / 光色天气 / 常驻物件）、武器 `weapon_profile`（设计意图 / 剪影 / 尺度 / 材质 / 色卡 / 携带方式 / 战斗用法 / VFX 签名）、`constraints`、`drift_forbidden`；缺项先补 `asset_registry.json`，不进入分镜出图
- **跨项目资产库提醒**：如果本集会新增角色/场景/道具/特效定妆，AI 必须先提示“我会先查 `创作区/制漫剧/_资产库/`，有可复用模板就导入 fork，没有再新建定妆。”并后台跑 `python3 skills/n2d-asset-market/scripts/market.py list`。命中角色模板时，用 `import-character` 导入为本剧新 `CHAR_...`，再跑 `n2d-identity --write`；不要让用户记 CLI。
- **出图前脸漂风险预测（事前预案，把 LoRA/加强参考从「事后升档」前移）**：**`dashboard gate --stage image_preflight` 现在会自动跑这条 + 下条物料预案，把普通 high/medium 项内联进同一份预检报告（high→WARN·medium→INFO），但「核心/长线角色 + 无持久主体后端 + 预测 high」升 **⛔block**，要求先切真实参考/主体库后端、补 face_embedding/表情库/已登记 image2image 强参考链，或显式处理风险。** 也可单独跑 `python3 skills/n2d-image/scripts/face_drift_risk.py <作品根> 第N集`。它读 `storyboard.json` + `identity_registry.json`，按本集分镜的高危信号（近景占比/大表情数/多人同框/极端角度命中 `angle_policy.risky` + 锁脸档位）给每个角色算**本集脸漂风险分**（block/high/medium/low），对 high/medium 角色给可执行建议（建表情库 expressions、补侧/背/角度参考、多人同框换多参考后端或拆正反打、默认走 image2image / 多图参考链补强；LoRA 只在快速本机加速或云训路径明确时作为可选升档，不把慢速本机训练当前置）。**②实测漂移回灌**：本脚本还读 `生产数据/identity_drift_report.json`（`n2d-identity` 对**已出图集**真量出的跨集漂移：embedding 质心 high / block 级脸漂镜）——命中角色升 **⛔block**（既成事实非预测），退出码 2，让 SOP/gate 卡住"带病续出下一集图"，把"等跨集漂了再事后升档"压成"上一集一漂、下一集出图前就停"。无该报告 / 无 insightface → 仅预测档生效，不假报。落 `生产数据/face_drift_risk_第N集.{json,md}`。
- **出图前物料漂移风险预测（E·场景/道具/武器/特效版的脸漂风险分）**：同样扫完 registry 后、付费出图前，跑 `python3 skills/n2d-image/scripts/asset_drift_risk.py <作品根> 第N集`。它读 `asset_registry.json` + `storyboard.json`，按本集分镜高危信号（跨集复用度/本集出镜次数/drift_forbidden 项数/结构·颜色强锁/多形态）给每个**场景/道具/武器/特效**算漂移风险分；高频资产若缺 `constraints`/`drift_forbidden` 会被额外抬风险，`WEAPON_xx` 缺 `weapon_profile` 则先回共享层补武器库画像，避免“登记信息不足”被误判为稳定。high/medium 给可执行建议（高复用进共享库一次出别每集重画、补场景四视图/不同机位、锁结构件数、锁武器握持比例、锁颜色拖尾防窜色、多形态上结构化状态机）。只提示不阻断，落 `生产数据/asset_drift_risk_第N集.{json,md}`。背景/武器漂移和脸漂一样穿帮，这条把"哪些物料本集容易漂"也前移到出图前。

**② 列出本集需求**
- 读 `脚本/第N集/分镜剧本.md` + `素材清单.md`
- 读 `生产数据/director_camera_plan_第N集.json/md`（若存在必须消费；若缺且 `storyboard.json` 已定稿，先回 n2d-script 生成）
- 提取本集需要的所有角色/场景/道具/特殊视觉

**③ 差集 = 新增项**
- 本集需求 − 共享已有 = 必须新加入共享库的项
- 包括"首次出现的全新项" + "已有角色的新形态变体"

**④ 追加共享库**（仅新增项才做）
- 共享 `00_索引.md` 追加 ⬜ 行（含 ID / 首现集 / 复用范围）
- 对应 `角色|场景|道具定妆.md` 追加完整 prompt 块（格式见 `references/prompt_format.md §2`）
- 若新增项是角色/角色形态，同步在 `identity_registry.json` 增加 `characters[].forms[]`：先填 `reference_group` 目标路径、`reference_atlas` 骨架（基础视角 ready/planned、表情/动作按 ROI 分层登记、`selection_policy`）、Codex fallback、视频后端 `unregistered|fallback_reference_group`、LoRA `not_needed|candidate`、`generation_control.seed_strategy=fixed_pool`（固定 `seed_pool` + `usage` + 后端支持/回退记录口径）、`angle_policy`、`drift_forbidden`。若这是长线成长阶段（境界/权势/法宝/气场跨集升级），还必须更新该角色的 `evolution_profile.stages[]`，写清 `locked_identity_from` 和 `visual_delta`，并规定从上一阶段锚图派生。
- 若新增项是角色/角色形态，同步创建或更新 `角色库/<CHAR_ID>__<slug>/manifest.json` 与可选 `_index.json`，至少含 `library_tier`、`reference/ prompts/ lora/ voice/ adapters/ qc/` 分区和 `truth_sources`；并在 `identity_registry.json.characters[].asset_bundle` 写 manifest 引用。该 manifest 只归拢资产和缺口，不复制一套新角色 DNA；主角/核心长线/预计出场≥10集用 `core_full`，复现配角用 `recurring_standard`，具名短线用 `named_minimal`，局部群像用 `restricted_partial`。
- 若新增项是关键场景/道具/武器/独立服装/VFX，同步在 `asset_registry.json` 增加 `assets[]`：先分配 `LOC_xx` / `PROP_xx` / `WEAPON_xx` / `OUTFIT_xx` / `VFX_xx`，填 `reference_group.primary` 目标路径、`constraints`、`drift_forbidden`；若是场景/地点，还必须填 `scene_dna` 七项环境锚（归属锚 / 地标 / 空间布局 / 建筑材质 / 光色天气 / 常驻物件 / 禁漂项），否则长线场景归属感无法锁住；若是主角/核心反派武器或法宝实体，还必须填 `weapon_profile` 并把 ID 写入对应角色形态的 `signature_equipment`

**⑤ 建本集 prompt 文件夹**
- `出图/第N集/prompt/00_总览.md`（**先写「本集视觉一致性契约」五字段：色调基线 / 场景光位锚 / 场景轴线·视线 / 角色状态演进表 / 景别阶梯** + **「本集可看性签收合同」**（从 `script_quality_contract_第N集.json` 誊抄核心看点、首屏钩、留存承诺、观众问题账本）+ **「本集基础视觉风格契约」六字段：风格名 / 视觉基调 / 镜头与构图 / 光色策略 / 运动边界 / 风格禁忌** + **「本集专项镜头模板速查」**（从 `storyboard.json` 誊抄复杂 Clip 的 template_contract）+ 本集图清单 + 引用共享 + 进度）
- `出图/第N集/prompt/01_分镜出图.md`（本集 N 张分镜，一镜一图，复杂镜拆 NA/NB；每镜含 `剧本可看性合同` / `视线方向` / `光位锚` / `起幅·运动余量` 四类字段，且 `剧本可看性合同` 来自 `script_quality_contract` 的 `dramatic_function/audience_effect/spectacle_story_function`，`起幅·运动余量` 优先从 `director_camera_plan_第N集.json` 的 `image_prompt_injection` 落入；复杂镜另含 `专项镜头模板` 字段并继承 `template_contract`；含角色镜头从 `identity_registry.json` 读取 `reference_group`、`reference_atlas.selection_policy`、`evolution_profile` 当前成长阶段、`signature_equipment`、`angle_policy`、`drift_forbidden`，按 closeup/profile/back_view/full_body_action/fight_or_spell 等镜头类型选择 ready 参考图；同框 ≥2 个 `CHAR_` 的镜头必须从 `reference_plan_第N集.md` / `storyboard.template_contract.character_slots` 落入 `多人同框身份槽位` + `多人同框执行策略`，不许只在参考图块堆多张角色图；含关键场景/道具/武器/独立服装/VFX 从 `asset_registry.json` 读取 `reference_group`、场景 `scene_dna`、武器 `weapon_profile`、`constraints`、`drift_forbidden`，不临场猜参考图）
- `生产数据/script_contract_applied_第N集.json`（`出图` scope，绑定当前 `script_quality_contract` SHA 与 `01_分镜出图.md` SHA，证明出图 prompt 已消费上游“好看”字段）
- `生产数据/consumed_contracts_image_prompt_第N集.json`（绑定 storyboard / continuity_chain / script_quality_contract / director_camera_plan / reference_plan 与两个出图 prompt 文件 SHA；任一上游或 prompt 改动后必须重跑 prompt pack）
- `image_prompt_pack.py` 必须给每个可执行的共享资产块和逐镜块追加 `后端编译提交 image prompt`：从 `_设置.md` 读取实际画幅、模型与渠道，从 `storyboard.style_contract` 读取所选风格，经 task/backend profile 编译；禁止模板默认 `9:16` 或“写实国漫”。完整合同仍原样保留，gate 用 source text SHA 检查编译块是否随合同同步更新。

**⑥ 【可选】视觉状态账本同步（World State Modeling）**
建完 prompt 文件夹后，默认只做轻量判断：若本集存在伤痕/战损/换装/获得法宝等会跨镜或跨集持续的状态，先提示用户“本集有持续视觉状态，我建议跑一次视觉状态账本 `--audit`；确认后再写入/注入。”状态简单时直接沿用 `00_总览.md` 的角色状态演进表，不跑账本。
- 可选只读审计：`python3 skills/n2d-image/scripts/visual_state_manager.py <作品根> --audit`。
- 只有用户确认或状态复杂度高时，AI 才读取审计输出生成 Visual Modifiers JSON。
- 注入项目：`python3 skills/n2d-image/scripts/visual_state_manager.py <作品根> --apply-mock <JSON路径>`，再执行 `--inject N` 回写入 `01_分镜出图.md`。

**完成后**：
- `_进度.md` 该集 **`出图prompt` 列填 ✅**（共享层新增 + 本集总览 + 本集分镜完成即算 ✅；视觉状态账本是可选增强，不作为默认硬前置）
- `_进度.md` 该集 **`出图` 列填 已完成张数/总张数**（如 `2/16`；分子含共享复用，分母 = 共享需要 + 本集分镜）

**完成后提示用户**（出图 prompt 已就绪，进入生图前先打个招呼，别闷头继续）：
> "本集出图 prompt 已生成完毕（共享层定妆 N 项 + 本集分镜 **X 张**）。接下来进入**出图环节**：先补齐共享定妆库（硬闸门），再按 `生成优先序`（默认**关键镜🔑优先**）排队生成。**生图前我会先扫描当前可用生图渠道并核对生图模型**：如果有多个可自动落 PNG 的官方/已登录渠道，会列出优劣建议让你选一组 `生图模型 + 生图AI/生图渠道`；如果一个都没有，会停止并提示先准备可用生图渠道。选定后本集/本项目统一写 `_设置.md` 的 `生图模型` + `生图AI`，不混用、不偷偷换模型/渠道、不走第三方逆向/web 自动化兜底。随后再请你选这次的切分颗粒度（每次都问）：①逐个（一张/一Clip，最细，每个停审）②小批（默认每批 5，批大小可改）③按场景/段落分批 ④整集一次过。"

> 然后**原样展示「生成粒度 + 优先序」段的四档菜单**等用户选定，再开抽.

### 阶段 B — 重新扫描本机生图能力

```bash
# 每次生图前都跑；详细清单见 references/cli_registry.md
for cli in codex openai dreamina gemini-cli seedream kling sora; do
  command -v "$cli" >/dev/null 2>&1 && echo "found: $cli ($(command -v $cli))"
done
codex features list 2>/dev/null | rg 'image_generation|artifact' || true
codex plugin list 2>/dev/null | rg -i 'image|openai|fal|replicate|browser|computer-use' || true
python3 skills/n2d/_lib/image_backend_adapter.py scan --json
```

按 `image_backend_adapter.py scan --json` 的 `usable_backends` 处理：

- **0 个可用**：停下并告诉用户：`当前无可用生图渠道，请准备好可以生图的官方/已登录渠道（例如登录/配置 Codex/OpenAI/Dreamina/Seedream/可灵/Nano Banana 等官方入口），再继续 n2d-image。` 若扫描到 `needs_confirmation_backends`，单独列为“检测到但未能自动确认可用”，要求先人工确认登录态/会员/API key/额度/能落 PNG；未确认不得当作可用。
- **1 个可用**：若 `_设置.md` 没有显式 `生图AI`/`生图渠道`，可建议使用该渠道，并同时确认对应 `生图模型`，用 `n2d-settings set <作品根> 生图AI <渠道>` + `n2d-settings set <作品根> 生图模型 <模型>` 落档；若 `_设置.md` 已显式选了其它渠道但探活不通，先说明当前选择不可用，再问是否整集统一切到这组模型/渠道，用户确认后再落档。
- **≥2 个可用**：必须先让用户选择一组 `生图模型 + 生图AI/生图渠道`，不能替用户静默挑。给菜单时同时给简短建议：长篇/多集/核心常驻角色/多人同框吃重优先支持原生主体/角色 ID 或多参考强的模型/渠道（如 Seedream / 可灵 / Nano Banana 这类已证实能力的官方入口）；单集 demo、快速迭代、当前 Codex 内置生图可稳定落 PNG 时可选 GPT Image 2 via Codex；需要强编辑/文字/透明背景等能力时按当天官方文档和 CLI/API help 重新核验 OpenAI/Gemini 等能力；若用户关心“社区当前推荐”，先实时核验近期官方/社区资料再给建议，不把旧口碑写死。用户选定后写入 `生图模型` + `生图AI`；整集统一一组模型/渠道。

按 `references/cli_registry.md` 的优先级只在**用户选定的 `生图AI/生图渠道`** 内部选可自动产 PNG 并能落到作品目录的入口。Codex 会话内置 `image_gen` 可用时优先；`codex` CLI 仅作为能力探测/插件管理入口，当前 help 没有独立 `images generate` 子命令时，不要把它当成直接生图 CLI。若用户签核 `生图AI=Dreamina/即梦` 例外，才扫描并调用官方 `dreamina` CLI 的图片能力，同时在记录里写清实际 `生图模型`。

**生图前确认（主要人物一致性素材 · 调 AI 出图前必问一次）**：扫完本机能力、真正调 AI 生图之前，先就**本集主要人物**（角色卡复用范围标【全篇】或长线核心，如女主 / 主反派）问用户一句——

> "本集主要人物你有没有**训练好的 LoRA 模型**，或**指定的参考图片**？
> - **有** → 把模型 / 图片给我，我据此走**图生图**派生，按你的反馈反复抽到满意为止（跨镜一致性最稳）。
> - **没有** → 我按既定 prompt 让 AI 自行生成（默认锚点句 + 定妆参考图方案）。"

- **用户给了 LoRA** → 按 `references/lora_consistency.md` 接产线（先过 Stage 0 三决策门再逐阶段推进）。
- **用户给了参考图** → 把它登记为该角色的**定妆主参考 / 角色参考**，落到 `出图/共享/图片/`；后续含该角色的所有镜头一律以它做**图生图 / 多图参考派生**（见「多图参考派生铁律」），并按筛选反馈重抽至满意。
- **用户没有** → 走默认方案（阶段 C 生成共享定妆 → 阶段 D 多图参考派生 + 锚点句），**不强推 LoRA**。
- 该选择对应偏好点 `一致性增强(LoRA)`：用户答过一次即按 `../skills/n2d/references/选择点与偏好.md` 写回 `_设置.md`，同项目之后沉默沿用，不再每集重问.

### 阶段 C — 共享定妆先行（硬闸门）

在任何本集分镜图生成前，先执行并通过这组检查：

0. **占位配音警告（模式化放行）**：扫 `_设置.md` 与 `合成/第N集/配音/时长清单.json`。若 `制作模式=先出视频后配音` 且进度为 `配音=⏳rough`，可以继续生成共享定妆 / 本集分镜 PNG，但开工前先提示：当前图包由占位/rough timing 驱动，适合快速 demo；真实音色替换后镜头时长可能变化，正式成片/付费投放前应回跑 `n2d-voice` → `n2d-script` 阶段2，并按差异决定是否更新 prompt / 重出受影响镜头。落档记录里标注「占位配音驱动」。若 `配音先行` 模式仍含 `占位:true`，停止并要求先补真实配音。
0.5. **检查清单闸门（硬）**：逐个扫描将要生成的共享定妆 / 分镜 prompt 块，必须同时有提交前 `检查清单（...）` 与生成后 `自检（生成后逐张过 · 落档闸门）`。缺任一段，先补齐再生图.
1. 读 `出图/第N集/prompt/00_总览.md` 的共享引用清单.
2. 对照 `出图/共享/prompt/00_索引.md`，确认每个共享项都有 PNG 路径.
3. 检查每个 PNG 文件真实存在、可打开、方向/画幅可用.
4. 缺图或状态不是 ✅ 时，先生成共享定妆 PNG，并落到 `出图/共享/图片/`；更新共享索引状态为 ✅.
5. 只有共享引用全部 ✅ 后，才进入本集分镜图生成.

本阶段是**流程闸门**，不是建议. 原因：本集镜头图必须以共享定妆图锁脸锁妆造；先生成镜头图再补共享层，会导致同一角色在同集/跨集漂移.

### 阶段 D — 分支决策

**分支 1：所选官方后端能落 PNG**
- 按 `_设置.md` 的 `生图模型 + 生图AI/生图渠道`（默认 OpenAI GPT Image 系列 via Codex）选定**单一模型+渠道**。非 Codex/OpenAI 后端必须先有 `<作品根>/合规/image_backend_override.json` 签核；扫描到 `同视频AI` / `同视频模型`、第三方逆向或 web 自动化出图口径必须忽略并改回显式官方后端；**全集统一一组模型+渠道，不混用**。
- runner 必须用具体 target、实际附件、模型、渠道和请求参数重新运行 image prompt compiler，并只把编译请求交给后端；Codex 外层只保留“必须调用真实生图工具/输出 PNG”的执行指令，Dreamina 的 `--prompt` 直接等于 compiler 文本。每次调用先写 immutable compiled request 回执，后端不得自行拼另一套创作 Prompt。
- 选定后告知用户："本项目生图模型/渠道 = X（官方入口），将用它出图。如不同意请打断。"
- 按 `生成粒度` + `生成优先序`（见上节）逐单位出图；普通模式逐单位停审，当前请求有无停顿授权时逐单位自动自检后继续；每单位调用见"调用规范"
- **批量加速可选（仅 `生成粒度: 整集` 档）**：整集档下 >10 张时，可并行多个独立任务调用 CLI（每个负责一段镜头），主流程收集结果；**逐个/小批/按场景档按单位串行停审，不并发**
- 中间筛选废料 → `废料/出图/{共享,第N集}/图片/`，定稿 PNG → `出图/共享/图片/` 或 `出图/第N集/图片/`

**分支 2：所选后端无可落 PNG 的入口**
- 停下并报告：
  > "本项目生图模型/渠道为 X，但本机/当前会话未检测到可自动落 PNG 的对应入口。我不会偷偷换别的后端兜底（换后端=混用，会让角色跨镜漂移），也不会用第三方逆向或 web 自动化出图。若扫描结果里有其它可用官方后端，请你选择是否整集统一切换到其中一个；若一个都没有，当前无可用生图渠道，请先准备好可以生图并能落 PNG 的官方/已登录渠道。"
- **手动指导模式（仅用户明确要求时）**：
  - 一次一张（或一批），把 prompt + 所选后端参数列出来
  - 让用户截图回传 → 执行者按**筛选宽容铁律**评判 → 通过则落档（用户从 Downloads 挪 PNG 进 `出图/共享/图片/` 或 `出图/第N集/图片/`），只有触发硬伤才建议调整 prompt 或重抽
- 不提供第三方逆向或 web 自动化手动指导。若用户临时要做后端对比实验，需另开手动实验流程，不回写为 n2d 默认生图结果。

### 阶段 E — 进度回写 + 推进

每出一张定稿 PNG：
1. PNG 落档到正确位置（共享定妆 → `出图/共享/图片/`；本集分镜 → `出图/第N集/图片/`）
2. 共享 `00_索引.md` 该项状态改 ✅，填 PNG 路径
3. 回写 `出图` 列：`python3 skills/n2d/progress.py set <作品根> 第N集 出图 X/Y`（X=已出张数）
4. 记录生产数据：
   ```bash
   python3 skills/n2d-dashboard/scripts/dashboard.py record <作品根> \
     --episode 第N集 --stage image --event generation \
     --asset <PNG路径> --status pass \
     --duration-sec <本次耗时秒> --provider <生图渠道> \
     --cost <成本数值> --unit <USD|CNY|credits> \
     --meta requested_seed=<seed_pool取值> \
     --meta effective_seed=<真实传入seed或none> \
     --meta seed_effective=<true|false> \
     --meta seed_support=<supported|unsupported_or_unknown|backend_dependent_verify_adapter> \
     --meta seed_strategy=fixed_pool \
     --meta recipe_hash=<本次生成配方hash> \
     --meta prompt_sha256=<最终prompt_sha256> \
     --meta reference_bundle_sha256=<reference_bundle_sha256> \
     --meta backend_version=<后端/CLI/API版本或采集标识> \
     --meta quality_tier=<draft|standard|high|release> \
     --meta actual_image_inputs=<实际入参图路径或manifest> \
     --meta input_fingerprint=<prompt+参考+设置+registry的输入指纹> \
     --meta settings_sha256=<作品设置hash> \
     --meta identity_registry_sha256=<identity_registry.json hash> \
     --meta asset_registry_sha256=<asset_registry.json hash> \
     --meta artifact_sha256=<最终PNG sha256>
   ```
   - 若落档的是 `continuity.midframe/anchors` 声明的 `_mid` / `_aK` 中段锚帧，**必须先按该镜「中段锚帧生成方式」和自检确认动作/姿态确实处于首帧与尾帧之间**，再在记账命令追加 `--meta self_check=pass`（可再补 `--meta mode=codex_image2image_midframe`、`--meta source_image=...`）。`video_preflight` 会读取最新一条该资产 image generation/redraw 事件；PNG 存在但缺 `self_check=pass`，或最新记录是 fail，会 BLOCK，避免“只锁人锁景、动作未成立”的 `_mid` 混进正式闸门。
   若本次是重抽或失败，`--event redraw --status fail --redraw-reason "<脸漂移|构图错|硬性禁忌|...>"` 也必须记录。

需要校准 compiler/profile 时，先用 `image_prompt_metrics.py register` 注册固定时域 A/B，再通过 `N2D_IMAGE_PROMPT_EXPERIMENT_ID` + `N2D_IMAGE_PROMPT_VARIANT` 给预分配资产打完整标签；不得把不同时间、不同剧情难度的未标记版本 cohort 当随机实验。阶段/批次结束后运行 `python3 skills/n2d-image/scripts/image_prompt_metrics.py report <作品根> --write`，联合 production events 与真实 image_qc 统计首抽通过、身份漂移、手部失败、重抽、成本和 input token；只有样本达标、显著提升且安全指标不退化才升级 profile。完整命令见 `references/image_prompt_compiler.md`。

**每张/每单位落档后先跑出图落档机检；本集分镜全部落档后再跑一次收尾总闸（生图后闸门，与 gate 互补）**：
```bash
# 首选 full QC 环境（有 Pillow/cv2/insightface/onnxruntime/buffalo_l）
/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python skills/n2d-image/scripts/image_qc.py <作品根> 第N集 --json
/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image

# 只有确认该 python 有 full stack 时，才可换成其它解释器
python3 skills/n2d-image/scripts/image_qc.py <作品根> 第N集 --json
```
- gate（阶段前）查的是 prompt/契约**结构是否齐全**；image_qc（落档后）查的是**真出的 PNG 像素一致性 + 逐镜 prompt 漏拼**——复用 `n2d-review` 的角色 DNA 机检（脸 G1 / 发型 H1 / 服装 N1）+ 场景 O2 / 接缝接力 / 锚点门 N3 纯函数与已校准阈值（单一真值源，不重复定义），把"等整集出完进审片才发现漂移"前移到刚出完这批、最便宜的点。
- **判定分两级 + 角色脸覆盖硬闸 + 贴脸反作弊硬闸**：`verdict=block`（硬阻断——崩脸、接缝断、纯文生图、非法 `CHAR_xx`、尾帧身份/接力硬伤、降级精度近景、`face_reference_coverage.missing>0`、`prohibited_face_patch.outputs>0`）→ 必须修复/重抽后重跑，不得推进；`verdict=review`（初筛人判——outfit/scene/道具特效/锚点门/漏视线锚点句等）→ 交人二次判，确认误报可放行；`verdict=ok` → 放行。加 `--strict-pixel` 可把像素机检 block（服装换装/场景换景/道具特效漂移）从 review 升为硬阻断 block（默认 off，保留宽松判定）。`face_reference_coverage` 是铁律：每张已落档角色图都必须有 full 精度定妆/身份主参考比对证据，warn/noface 不算通过；`prohibited_face_patch` 是更高优先级的事实闸门：最新落档事件若来自本地贴脸/换脸/裁脸贴回画面，即使 embedding 分数过线也一律不合格，必须真实重抽或用官方 image2image 派生替换。
- **先告知环境再判阶段**：报告落 `生产数据/image_qc/第N集/`，其中 `qc_environment.precision_level` 和 `face_reference_coverage` 必须读给用户或摘要给用户。只有 `precision_level=full`、`hard_blocks=0`、`face_reference_coverage.verdict=ok` 且 QC 时间晚于所有 PNG 时，才能建议进入 `video`；`degraded`/`none`、旧版 QC 缺覆盖字段、缺比对行或 PNG 改动后未重验，一律回 `image` 或 `image_qc_setup`，不能把缺依赖/缺证据当作图片通过。
- **缺依赖安装口径必须明说**：优先安装到 `facefusion` conda env：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python -m pip install pillow opencv-python onnxruntime insightface scikit-image`，首次运行 `FaceAnalysis(name='buffalo_l')` 预热模型；无该 env 时新建 Python 3.10-3.12 conda env。系统 Python 3.14 不作为重视觉依赖首选。旧口径“无 Pillow/insightface 时静默降级”废弃；可以降级运行以生成报告，但必须把降级、安装建议和阶段跳转写清。

本集 `出图` 列 = 分母时：
```
第K集 出图完成（X/X）
- 共享层新增定妆：<列项目>
- 本集分镜：<张数>
下一步建议：
- 调 n2d-video <作品根> 第K集  生成视频 prompt + MP4
- 或继续 n2d-image <作品根> 第K+1集
```

## 调用规范（找到 CLI 时）

**通用流程**（每张图）：

1. 从对应 prompt 文件读出本张的正向 + 负向 prompt + 参考图（如有）
2. 走 CLI：
   ```bash
   <cli> <subcommand> --prompt "$(cat <prompt_file_or_inline>)" \
                     --negative "..." \
                     --ref-image <出图/共享/图片/定妆_xxx.png> \
                     --ref-strength 0.8 \
                     --aspect <_设置.md中的项目画幅> \
                     --out <目标 PNG 路径>
   ```
   （各 Codex/OpenAI 入口具体参数见 `references/cli_registry.md`）
3. 检查产出 → 通过则原位 PNG 已落档；废图 → `mv` 到 `废料/出图/{共享,第N集}/图片/`
4. **视频兼容锚定**：组装 prompt 时若项目已固定生视频模型，自动在 prompt 末尾追加该模型锚定句；若未固定，使用通用视频兼容锚定并记录 `video_backend_decision=deferred`，不回到开局要求用户选择视频后端（详见 `references/platforms.md`）

**安装新 CLI 时**（用户同意才做）：
- 走 `references/cli_registry.md §安装审查` 的 5 步流程（域名核对 / WebFetch 读脚本 / 不 sudo / 不写敏感位置 / 无可疑行为）
- 绝不 `curl xxx | bash` 不审

## 定妆变更影响扫描（改了共享资产 → 哪些镜头要重出）

共享定妆库的卖点是"一处改、全篇用"，但**改了某个 `出图/共享/图片/定妆_<X>.png` 后，已出的分镜镜头不会自动更新**——靠人记哪些镜头引用了它极易漏。改定妆（换装/锁脸微调/场景重绘/法宝改形）后，跑：

```bash
python3 <skill>/scripts/asset_impact.py <作品根> 定妆_沈念 [更多资产名…]   # 人读
python3 <skill>/scripts/asset_impact.py <作品根> 沈念 --json               # 喂回 LLM
```

它扫各集 `出图/<集>/prompt/*.md` 的「参考图」引用（兼容两种 prompt schema：本宫式 `目标：…png`+裸名、看花胖子式 `## Clip N`+`定妆_x.png`），**并读 `identity_registry.json` / `asset_registry.json` 的结构化绑定**——镜头 prompt 只写了 `CHAR_xx`/`LOC_xx`/`PROP_xx`/`WEAPON_xx` ID 或角色名、靠 registry 自动取参考的镜头同样命中，不再只靠文本「参考图：」行。按目标 PNG 是否已存在分两类：**🔁 已出图·需重出**（回本 skill 重出 these 镜头）/ **⬜ 未出图**（下次出图自然用新版，无需动作）。只读，不改图。资产名可写 `定妆_沈念.png` / `定妆_沈念_侧` / `沈念` / `CHAR_01` / `WEAPON_01`，自动归一到核心键匹配.

**失效半径扩展（视频层 + 后端身份注册）**：定妆改动的连锁失效不止出图层——
```bash
python3 <skill>/scripts/asset_impact.py <作品根> 沈念 --include-video           # 加「已出视频需重生」清单（clip 用旧定妆首帧出的）
python3 <skill>/scripts/asset_impact.py <作品根> 沈念 --check-native-adapters   # 加「后端身份注册基于旧定妆」提醒（Kling 主体库/Seedream/Sora Cameo 等 status∈registered/ready 的句柄需重新注册）
```

**连锁更新自动化（`--rerun-plan`，免人工排查）**：一条命令把"改了定妆"直接展开成连锁重跑计划——受影响集 → 重出图 → 刷新身份(`n2d-identity`) → 受影响 Clip 重出视频 → 受影响集重合成 → 每集一条**最小范围** `n2d-batch` 重跑命令（只含已出图的镜头/产物）：
```bash
python3 <skill>/scripts/asset_impact.py <作品根> 定妆_沈念 --rerun-plan            # 人读连锁计划
python3 <skill>/scripts/asset_impact.py <作品根> 沈念 --rerun-plan --json --out 计划.json
```
计划里第 5 步即可直接复制运行的 `queue.py plan … --rerun-from image --affected-artifact <png> --affected-shot <镜>` 命令（每集一条）。未出图的镜头不进重跑（下次出图自然用新版）。

**与 n2d-batch 无缝对接（免手抄命令）**：`--output-batch-tasks` 输出 batch 可直接消费的任务 JSON（kind=`n2d_asset_rerun_plan`），queue 一口吃下自动排队：
```bash
python3 <skill>/scripts/asset_impact.py <作品根> 沈念 --output-batch-tasks 计划.json
python3 skills/n2d-batch/scripts/queue.py plan <作品根> --from-asset-impact 计划.json
```
仍可手动单跑：
```bash
python3 skills/n2d-batch/scripts/queue.py plan <作品根> \
  --episodes 第N集 --rerun-from image \
  --affected-shot Clip_03 \
  --affected-artifact 出图/第N集/图片/Clip_03.png \
  --scope "定妆_<X> 更新，只重跑受影响镜头"
```

> 这是 `n2d-review` 机检家族的一员——质检时若发现某定妆崩脸需重抽，重抽后用它列出受影响的下游镜头一并重出，避免改了源头却漏改引用镜头.

## 详细参考

- **角色 DNA checklist（跨集锁脸锁发型锁服装锁配饰全链对照）**：`references/角色一致性checklist.md`
- **资产身份注册层（角色 ID / Face Lock / LoRA 适配）**：`references/资产身份注册层.md`
- **资产引用注册层（场景/道具/武器库/独立服装/VFX ID 映射）**：`references/资产引用注册层.md`
- **角色身份闭环 + 跨集漂移报表**：`n2d-identity/SKILL.md` + `n2d-identity/scripts/identity.py`
- **LoRA 增强一致性（可选 · 引导式五阶段）**：`references/lora_consistency.md`；生命周期执行层见 `../n2d-lora/SKILL.md`
- **导演视角八维 prompt 装配（画师视角→导演视角升级）**：`n2d/references/导演视角prompt.md`——分镜图必读
- **prompt 两层架构 + 定妆 prompt 块标准格式**：`references/prompt_format.md`
- **后端感知 Image Prompt Compiler + profiles + hashes + gate + A/B**：`references/image_prompt_compiler.md`
- **平台档案 + 锚定句速查**：`references/platforms.md`
- **已知 CLI 清单 + 安装/调用规范**：`references/cli_registry.md`
- **翻车 + 修正案例**（实战沉淀）：`n2d/Q&A.md` 的 Q3-Q12（定妆/场景细节）、Q14-Q18（CLI 安全 + 跨 AI）、Q19-Q20（共享层 + 跨集复用 SOP）

## 常见错误

| 错误 | 纠正 |
|---|---|
| 分镜图写成"好看插画"（画师视角）| 按导演视角八维装配（镜头·机位·人物·动作·场景·光影·情绪·画质），补齐易漏的机位/光影/张力 |
| 直接逐镜出图、本集总览没写视觉契约 | 违反**本集视觉契约先行铁律**——00_总览 先写五字段（色调基线/光位锚/轴线·视线/状态演进/景别阶梯），凡视频改不动的导演决策在出图阶段下完 |
| 正反打两镜视线都朝同一边 / 没填视线方向 | 违反**轴线/视线像素焊死铁律**——每个含角色镜必填 `视线方向` 并对位本场轴线；轴线烤进像素后出视频救不回 |
| 打斗/动作镜人物看主镜头 | 违反**打斗视线铁律**——主镜头默认是旁观者，角色视线锁对手/武器/命中点；除非明确 opponent POV/破第四墙，不得 looking at viewer / eye contact with camera / clear frontal portrait |
| 同场跨镜各打各的光、剪起来闪 | 违反**场景光位锚铁律**——每场定一条光位锚（主光方向/色温/动机光源），所有镜继承，改光写理由 |
| 出血的镜后面又干净 / 乱发自愈 / 觉醒前提前发光 | 违反**状态演进铁律**——按角色状态演进表单调推进、不回退、不提前泄露 |
| clip 首帧就画成动作顶点、视频没运动余量 | 违反**首帧=起幅铁律**——首帧抓起幅、顶点交尾帧；按计划运镜预留构图余量（推近框宽/环绕留空/跟摇留 lead room）|
| `director_camera_plan_第N集` 已有但没落实到 `01_分镜出图.md` | 把 `image_prompt_injection` 的 `镜头/机位`、`起幅·运动余量`、`构图防呆` 逐镜写入；若人工不采纳，写明理由，不能让导演运镜计划停在 sidecar |
| 尾帧只对齐构图、光或状态却跳了 | 尾帧要「构图+光位+人物状态」三者都=下一首帧，照本场光位锚和状态演进表对齐 |
| 分镜图默认正面平视 + 均匀打亮 | 机位即态度（仰/俯/过肩）、光替剧情说话（动机光/方向/调性），见 `导演视角prompt.md` |
| 给定妆图也打戏剧光/带情绪 | 定妆=中性档案（正面均匀光无戏），只锁脸锁造型；戏剧光只上分镜图，否则污染下游参考 |
| 外部人物参考图的衣服/发型/配饰被带进定妆 | 参考图只借脸型/五官/眼神/体态/身材气质；发型、服装、配饰、妆容按小说和角色圣经定。 prompt 补“不继承参考图服装/发型/配饰”后重抽 |
| 跳过 SOP 第 ① 步（不扫共享） | 必然重复劳动 + 跨集脸漂移 |
| 重切/细分后旧命名 PNG 仍留在 `出图/第N集/图片/` | 违反**本集图片命名空间唯一铁律**——当前 `01_分镜出图.md` 未声明的 `ClipNN_*.png` 必须移入 `废料/出图/第N集/...`；同时把 `storyboard.json`、视频 prompt、manifest/进度分母同步到当前目标集 |
| 只有 `00_索引.md` 和定妆 PNG，没有 `identity_registry.json` | 违反资产身份注册层铁律——补 `reference_group` / `identity_adapters` / `angle_policy` / `drift_forbidden`，让出图、出视频和审查读同一身份真值 |
| 只有 `00_索引.md` 和场景/道具/武器 PNG，没有 `asset_registry.json` | 违反资产引用注册层铁律——补 `LOC_xx` / `PROP_xx` / `WEAPON_xx` / `OUTFIT_xx` / `VFX_xx`、`weapon_profile`（武器）、`constraints`、`drift_forbidden`，逐镜写资产 ID 绑定 |
| 核心人物只出单张正脸 / 半身定妆 | `core_full` 必须补正面 / 前3/4 / 侧面 / 后3/4 / 背面 + turnaround 总览 + 半身或全身服装锚 + 脸锚/表情，并逐视图签当前 hash 收据；`recurring_standard` / `named_minimal` 仍按分档与真实镜头需求生产，不能被本行误读成一刀切全量 |
| 半身服装参考人物偏一侧、大块空白 | 违反半身服装参考裁切 + 居中铁律；从已通过正面主参考重新裁切，人物主体居中、头身中线贴近画面中线、左右留白均衡，再落档 |
| 把“三视图”拆成多张却没有总览图 | 拆图是生产资产，必须另存 `图片/定妆_<角色>_三视图.png` 供人审归档；不要把定妆组误叫三视图 |
| 含角色镜头图用纯文生图 | 一律「定妆组 + 场景图」多图参考派生，禁纯 text2image |
| 中/尾帧跳过首帧直接出 / 三帧并行各自文生图 | 违反**帧生成顺序铁律**——顺序焊死：定妆库→首帧→中帧→尾帧，中/尾帧必以同 Clip 首帧（尾帧可叠加中帧）为母图 image2image 派生；跳过首帧=重抽新演员脸 |
| 跑了 `reference_plan` 但逐镜 prompt 没落实 | 把 `recommended_references` / `distinct_anchors` / `shot_scheduling` / `controlnet` / 升档建议落进 `01_分镜出图.md`；未采用的动作项必须写原因，不能让 plan 停在侧车；落实后写 `生产数据/reference_plan_application_第N集.json` 绑定 plan/prompt SHA，不要手改 `action_required` |
| 参考图全量堆进后端或混入脏图 | 按后端容量写 `参考图入参清单与预算`，列 selected/dropped；只传 ready、清晰、无水印/Logo/无关文字/NSFW、格式受支持的参考图 |
| 反复出现的场景每集重画 | 场景同样入共享库，跨集引用同一 `图片/定妆_<场景>.png` 当参考 |
| 武器握持比例图画成角色立绘，露出清晰人物脸 | 武器比例图是尺度/握点/重心参考，不是角色定妆；人体只作尺度尺或握持手部参考，必须裁到下巴以下、背身、侧后剪影或无脸中性人台，禁止出现可继承的肖像脸。若已出图检出清晰脸且低于角色定妆组地板，标记该 `scale_reference` 为 `review_failed` 并重出共享库 |
| 非最终 Clip 只出首帧、没出尾帧 | 先看 `seam_mode`：`continuous_take_relay` 缺尾帧是硬错，补同一边界帧并回填 SHA；其他接缝不默认补尾帧，只有 `end_anchor_required=true` 才补镜内尾锚 |
| 改了共享定妆却没回头重出引用镜头 | 跑 `scripts/asset_impact.py <作品根> <资产名>` 列出受影响镜头（已出图的需重出），别漏改 |
| 把连续同场景镜头各自孤立抽 | 后端支持时按故事板批次多镜一次出，跨镜更稳更省 |
| 把定妆图当本集分镜放到 `出图/第N集/图片/` | 共享资产去 `出图/共享/图片/` |
| 角色切换时不清空参考图 | 即梦参考图框是粘性的，新角色前必须清空（见 Q&A Q8） |
| 场景图带角色参考图 | 场景定妆**必须**清空人物参考图（见 Q&A Q12） |
| 固定了生视频模型却漏拼锚定句 | image prompt 末尾必须拼对应模型锚定句 |
| 未固定视频后端时强迫用户先选 | 违反后移规则；用通用视频兼容锚定，具体生视频后端到 n2d-video 阶段由 router/probe 决定 |
| 负向 prompt 写成整段“不要/禁止/不得”说明 | 人读禁忌保留在文档里；实际提交后端前归一成短负面词/短语，硬性动作约束放正向 prompt 或本镜约束 |
| 装第三方逆向 CLI | 违 ToS、封号风险，仅装官方 |
| 废图留在 Downloads | 全部归档 `废料/出图/{共享,第N集}/图片/`，Downloads 清空 |
| 不报总量就闷头整集出图 | 违反 `生成粒度` 选择点——进生图前先报本集总张数 + 按优先序排队，默认逐个停审 |
| 逐个/小批档还 spawn 子 agent 并发 | 并发只在 `整集` 档；逐个/小批/按场景档按单位串行，每单位停下让用户审 |
| 整集档大量分镜全串行生 100 张 | 仅整集档：可 spawn 子 agent 并发调 CLI 提速 |
| 候选图轻微偏差就喊重抽 | 违反**筛选宽容铁律**——只对核心错位/定妆漂移/硬性禁忌违反 才重抽，小动小偏直接放行 |
| 人物多出一只手 / 两只右手 / 手从道具光效里长出来 | 违反**手部/肢体归属铁律**——不是小瑕疵，按 `hands` / `anatomy_continuity` block 归档重抽；prompt 必须写清可见手数、左右手、手臂连接和道具/武器接触点 |
| 一张图反复重抽烧 credit | 先确认 `重抽预算策略`：预算充足允许出到满意；预算一般只对关键图片严格抽到满意，普通图无硬伤就收 |
| 把"预算一般"当成所有图都随便过 | 预算一般不是不审图；关键图严格自检直到满意，普通图也必须无核心错位、无身份漂移、无硬性禁忌 |
| 看到 `dreamina` 就自动拿来生图 | 错。全项目生图优先 Codex / GPT Image 2；Dreamina/即梦图片只允许用户签核例外，且仍禁第三方逆向、`同视频AI` / `同视频模型` 含糊口径和 web 自动化 |
| 一集里这镜 Codex、那镜 Seedream | 后端混用是跨镜漂移真凶，gate 会 BLOCK——全集统一一个官方后端 |
| `_设置.md` 没改，但实际换后端重出了整集 | 仍 BLOCK：基线对账除了比 `_设置.md` 声明，还比 `production_events` **真实落档后端**——声明没改而事件后端≠锁定基线=视觉 DNA 漂移；统一回基线后端重出，或 `n2d-update media` 重制计划 + `record-baseline --force` |
| 看到 `codex` 就假定能命令行生图 | 必须检查 `image_generation` feature / 插件 / 内置 `image_gen`；没有直接保存 PNG 的命令时用 Codex 会话生图工具落档 |
| 无 CLI 就直接进即梦 web 手动模式 | 违反当前生产闸门。所选生图渠道不可用时必须停下报告，不得用 web 自动化兜底 |
