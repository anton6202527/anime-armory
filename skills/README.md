# Skills 索引

本项目包含 **novel（写小说 / 源书孵化）**、**n2d（小说 → AI 漫剧/短剧）**、**comic（画漫画 / 条漫页漫）**、**song（写歌）**、**mv（制 MV）**、**ad（拍广告）** 六条并列生产线。每条线都必须**自包含、可单独分发、零公共层**：脚本只 import 本线 `_lib` 或本线 craft 工具，不依赖 `skills/common/`，也不 import 其他系列实现。novel 与 n2d 不设任何文件/数据交接；其它跨线交付只能是用户显式选择的成品文件交接。**目录保持扁平**（每个 skill 仍是 `skills/<name>/SKILL.md`）——
skill 之间用 `<skills>/<name>/...` 互相引用，故**不要**移进子目录，否则交叉引用与 skill 发现会失效。
仓库级维护工具不属于 workflow skill，放在根目录 `tools/`。
本文件仅作分类说明。

> **工具中立 / 跨 AI 使用**：真身在仓库根 `skills/`，**不绑定任何特定 AI**。
> - **Claude Code** 经软链 `.claude/skills → ../skills` 自动发现并用 `Skill` 工具按触发词路由（无需改动）。
> - **其他 AI agent / 人**：直接读 `skills/<name>/SKILL.md`（= 这个 skill 干啥、何时用；frontmatter 的 `description` + 正文 `Triggers` 就是路由依据），照其说明做事，需要时跑 `skills/<name>/scripts/` 下的脚本。
> - **脚本是通用的**：纯 Python/bash，只调通用工具（ffmpeg / librosa / whisper / yt-dlp / 生图生视频 CLI 等），**无任何 Claude 专有 API**，谁都能执行。引用一律走中立路径 `skills/...`（旧 `.claude/skills/...` 经软链仍兼容）。
> - **skill 名写法**：下一步建议、路由表和用户提示里一律写裸名（如 `n2d-image`、`n2d-compose`），不要加 `/`。`/n2d-image` 这类写法会被部分 AI agent 当成斜杠命令，导致 `Unrecognized command`。

> **偏好约定（通用化原则）**：所有 skill 保持**通用**，不把平台/后端/分辨率写死成唯一路径。凡「让用户选」的点都是**选择点**，用户的实际选择是**私有的**，存在用户自己的空间——每作品 `<作品根>/_设置.md`（权威）+ 私有全局默认（memory 区 `创作偏好-默认.md`，开新项目预填），**不进共享 skill 代码 / 不外发**。行为：选择点首次问一次→写 `_设置.md`→同项目沉默沿用；合规/不可逆/花钱多的点每次仍确认。机制与全部选择点目录见各线自己的 `references/选择点与偏好.md`；每个 skill 有「## 偏好（私有）」段引用它。**新增选择点**→加进本线选择点目录，别在正文写死。

> **候选项刷新 + 适配层原则**：选择点里的菜单只是**候选快照**，不是永久真值。模型、平台、规格、价格、法规、榜单等高变化信息，执行前或流程自审/更新时应按需要用项目 references、官方文档、实时搜索或自有投放/生成战绩刷新，并在引用处写清来源日期；不能核验时要明说“未核验”。用户永远可以手输 `自定义`/`manual`，由 skill 写入 `_设置.md` 并进入适配层。执行逻辑不要直接绑菜单文案，而要经适配层归一成能力标签、实际 CLI/API/网页入口、参数包、fallback/degrade plan、合规 gate 和产物 schema；适配层缺失时先补适配或停下提示，不静默换后端、不把旧菜单当权威。

> **AI 交互节点（Interactive Flow）约定**：凡遇到**「机器可自动计算，但需要结合文学/语义理解才能高质量完成」**的连贯流程（如算好卡点时间线后，需要给每个镜头写包含动作和运镜的 Prompt），**不要让用户手动去复制粘贴脚本命令**。应该在工作流 SKILL.md 中设置明确的**【AI 代理交互节点】**：让 AI 主动用人类语言向用户提问提供选项（如：“是否需要我启动语义引擎为你补全提示词？”），在用户做出「决定」后，由 AI 代理在后台全自动完成「跑脚本 → 读提示 → 调 LLM 生成 → JSON 落档并回写」的脏活累活。**原则：把枯燥的脚本命令藏在背后，让用户只做决策。**

## Skills 规模统计

> 统计时间：2026-07-08。`SKILL.md 总行数` 仅统计 `skills/*/SKILL.md` 的物理行数（`wc -l`）；`目录文本总行数` 统计每个 skill 目录下的 `.md/.py/.sh/.json/.html` 文本文件，包含 `scripts/`、`references/`、测试与示例，排除 `__pycache__/*.pyc`、根级 README/偏好文档与项目产物。原 `skills/common/` 公共层已删除，不再单独计入。

| 系列 | 统计范围 | Skill 数 | SKILL.md 总行数 | 目录文本总行数 |
|---|---|---:|---:|---:|
| n2d | `n2d` + `n2d-*` | 21 | 4593 | 233305 |
| novel | `novel` + `novel-*` | 29 | 3040 | 61473 |
| comic | `comic` + `comic-*` | 10 | 800 | 12124 |
| song | `song` + `song-*` | 10 | 534 | 4851 |
| mv | `mv` + `mv-*` | 14 | 992 | 10590 |
| ad | `ad` + `ad-*` | 13 | 822 | 11873 |
| **合计** | `skills/*/SKILL.md` | **97** | 10781 | 334216 |

> 仓库级清理工具 `tools/shared-cleanup` 已移出 `skills/`，不计入 skill 统计。

> **系列独立性闸门**：改跨线引用、`_lib`、调度入口或选择点时，跑 `python3 tools/independence-audit/scripts/check_independence.py`。它会阻断活动的 `skills/common` / `common/*.py` 路径引用和未允许的代码级跨线依赖；文档里的跨线 handoff 必须说清“可选、文件/数据交接、缺失可降级”。

> **视觉线逐图 QC 原则（各线自维护）**：n2d / comic / mv / ad 的出图阶段都必须把 QC 前移到**每张图片落档后**：生成一张、登记一张、跑本线自己的最小可用 QC/落档自检，`block` 先修当前图，不把坏图继续传给视频/合成；批次或全话/全集结束后再跑一次本线收尾总闸。实现必须留在各自系列：`n2d-image` 用 n2d 的 `image_qc`/dashboard gate，`comic-image` 用 comic 的 `panel_qc`，`mv-image` 用 mv 的 `image_qc`，`ad-image` 用 ad 的 `product_qc` 与广告落档自检；不得新增公共实现目录，不得让一个系列 import 另一个系列的 QC 脚本。若某线现有脚本只能全量扫描，就每张落档后全量跑一次并聚焦新图 finding，后续再由本线自行 target 化优化。

> **零公共层 · `skills/n2d/_lib/` 自包含（2026-06 重构）**：原 `skills/common/` 已**删除**，所有管道工具 vendored 进 n2d 自己的 `_lib/`。`n2d/_lib/` 带自己需要的：`settings.py`（`_设置.md` 读写/选择点）、`disclosure.py`（AI 使用 + 授权披露写盘/骨架）、`progress_md.py`（`_进度.md` 阶段表解析）、`io_utils.py`/`text_utils.py`/`markdown_parser.py`、`subtitle_render.py`（字幕渲染）、`voice_backends.py`（配音后端注册表）、`freshness.py`+`refresh.py`（候选项新鲜度机检 + `CANDIDATE_SOURCES`）。n2d 私有契约真身在 `skills/n2d/_lib/`（`n2d_contract.py` 等），约 50 个 `import n2d_contract` 的 n2d 脚本 sys.path 指向 `skills/n2d/_lib/`；**要改契约去 `skills/n2d/_lib/`**。进度只走 `n2d-progress`；更新/重制收口进 `n2d-update`（含 `media` 子命令）；开局能力/精度自检走 `skills/n2d/doctor.py`（脸部机检 full/degraded/none、配音后端、生图后端连通、生视频关键帧档——把静默降级前移到开局，只探不改）。

---

## 一、n2d ——「小说 → AI 漫剧/短剧」生产管线

`n2d` 是总调度，按 `_进度.md` 把用户路由到对应阶段 skill。阶段顺序（**默认 `制作模式=先出视频后配音`；强配音控制/少返工时改 `配音先行`；特殊同步音画后端才选 `原生音画`**）：`视频` 列完成表示 `clip_delivery_complete`（镜头 MP4 齐，可内部预览），不是可发布母版；`合成/验收` 是用户可选尾段，只有 `_设置.md` 写 `合成阶段: 启用` 或本集已经开始 `成片/验收` 时才进入。发布/母版口径还要过 compose、release/readiness、production locks、creative governance 和人工签收，才算 `master_delivery_complete`。新项目视频默认口径：`出视频规格=预算充足`、`视频分辨率=720p`、`视频生成音频策略=无声视频流`、`视频原生音轨=丢弃`、`对口型=关闭`、`合成阶段=跳过`。

| 阶段 | Skill | 职责 |
|---|---|---|
| 调度 | `n2d` | 检查 作品 根目录，**入口先跑源新鲜度自检**（`source_check.py`：比对 `小说/<剧>.txt` 与 `小说/_源指纹.json`，源小说更新→列出变动章/受影响集/是否触及已生产集，提示同步+重切，重切每次确认不自动），读 `_进度.md`，按 `skills/n2d/_lib/n2d_contract.py` 的阶段契约路由到下面的阶段 |
| Agent 总控（上层） | `n2d-supervisor` | 消费 `n2d/run.py next --json` 的 NextAction，把确定性前置、context pack、creative loop、trace 和 specialist handoff 串成 agentic runtime；只派发 `n2d-script-agent` / `n2d-visual-agent` / `n2d-qc-agent` / `n2d-producer-agent`，不替代 stage skill、不直接花钱、不绕过 gate、不直接改 `_进度.md` |
| 1 剧本改编 | `n2d-script` | 编剧室 + 导演预演 + 制片交接合同的上游入口：拆集前先过 **source comprehension gate**（源理解合同：现代白话理解、承诺账、人物动机、因果链、伏笔账、改编边界、设定/战力规则 confirmed），再做中段开工前情资产包 + 精修前 5-10 集窗口复核边界 + **改编取舍 triage（成戏/旁白/后文带出/并入/删除 + 有账短剧化改写）** + 配音台词/BGM/封面/角色场景卡/global_style；阶段1 后用 `table_read_packet` 做低成本围读验收 |
| 2 配音/时长 | `n2d-voice` | 默认后配音模式下：voiceover.txt → 占位/估算时长清单（配音=⏳rough）先驱动下游镜头；出视频后再补真实角色配音并拟合。`配音先行` 模式下则先出真实配音 + 拼接音轨 + 时长清单.json（逐句记 `voice_key` 实际音色键，一角一色跨集对账数据源，`n2d-identity` 消费）；`原生音画` 模式下主流程跳过配音硬依赖，仅作旁白/系统音或单镜回退层；macOS say 中文空音频时自动降级静音占位并醒目告警 |
| 3 分镜设计 | `n2d-script` | `先出视频后配音`：用占位/估算时长 + `FINALIZE_ALLOW_PLACEHOLDER=1` 生成分镜剧本/故事板/素材清单/字幕/镜头时长，真实配音后可能重定时；`配音先行`：配音后回跑，按实测时长定稿；`原生音画`：按 storyboard 规划时长定稿；storyboard 同步锁 `entity_schedule` 在场/画外/禁入/出入场链；定稿必须写 `script_quality_contract_第N集.json/md`，把核心看点、首屏钩、留存账本、主干提炼/Clip 时长权重、逐镜戏剧功能、观众问题账本拆成可签收字段；出图前还要确认 `animatic_packet` + P-3 五件套（production_breakdown / continuity_breakdown / continuity_bible / ai_shooting_schedule / ai_call_sheet） |
| 4 出图 | `n2d-image` | 两层出图 prompt（定妆库 + 本集分镜）→ 用 `生图模型` 生成（默认 GPT Image 2），经 `生图AI/生图渠道` 访问入口执行（默认 Codex CLI；**阶段2 起放行官方/已登录多参考模型/渠道** OpenAI/gpt-image、Dreamina/即梦官方 CLI、Seedream/可灵主体库/Nano Banana，Sora Cameo 仅旧项目 manual）。prompt 包必须消费 `script_quality_contract` 并写 `script_contract_applied_第N集.json` 的 `出图` scope，证明核心看点/首屏钩/逐镜戏剧功能进入 prompt。正式生图前默认跑 `dashboard gate --stage image_preflight`，两条硬闸门：① 项目内**不混用模型+渠道** ② **禁第三方逆向/未授权出图**。身份注册层含 `reference_group.expressions`**同源情绪定妆**（近景高频/情绪戏核心角必出「一脸多情绪」），供下游近景大表情镜做首尾双帧只插值、治表情漂移。每张 PNG 落档后立即跑 n2d 自己的 `scripts/image_qc.py`/dashboard image gate 最小可用检查，批次/全集结束后再跑收尾总闸；生图后 gate 复用 n2d-review 的崩脸/服装/场景/人体解剖N5/接缝/锚点门纯函数+阈值（单一真值源）把一致性机检前移到落档，并 lint 逐镜 prompt（参考图块/视线/锚点句/`CHAR_xx` 在 registry 合法性/**人体完整性·手部归属·身体接触面**防多手缺肢/身体融合/**近景大表情镜引用表情库**治表情漂），同时读 `production_events.jsonl` 抓**本地贴脸/换脸/裁脸贴回画面**产物；运行前/报告中必须明示机检能力 `full|degraded|none`、当前解释器、建议安装和阶段跳转，缺 Pillow/cv2/insightface/onnxruntime/buffalo_l 不得静默当通过；`verdict=block`（崩脸/人体解剖N5铁证/纯文生图/非法ID/接缝断/降级精度近景/缺高风险人体合约/**本地贴脸修复产物**）必修并回 `image`，`review`（像素初筛）人判；**degraded 精度近景自动拼「定妆主参考↔本镜脸」并排对比图供人审**（`n2d-review/face_compare_stitch.py` + Haar 几何粗筛）。出图前另跑 `scripts/face_drift_risk.py` 按分镜高危信号（近景占比/大表情/多人同框/极端角度+锁脸档）预测每角色本集脸漂风险，high/medium 给建表情库/补参考/上 LoRA 的**事前**建议；无公开持久主体 ID 的 Codex/OpenAI 类后端不等于不能锁角色，若已写齐项目记忆路线（`identity_registry` + 共享定妆 PNG + `codex_reference_bundles`/reference manifest + 真实 `--image` 入参 + 分层/反打 + full QC）则不因 `persistent_subject=False` 自动阻断；真正 block 的是 ready 参考缺失、actual image inputs=0、missing_ready_refs、多人同框缺 split_composite/身份槽位或 QC 失败。**其它物料（场景/道具/武器/特效）同构加强**：image_qc 落档并入**道具·特效 P2**（multimodal 组内离群初筛）+ 逐镜 **`LOC/PROP/OUTFIT/VFX_xx` 资产 id 合法性 lint**（`unknown_asset_id` block / `asset_ref_without_id` warn，对称 CHAR_xx）+ **资产状态机回退** lint（`scripts/asset_lifecycle.py`：结构化 lifecycle 状态只前进不回退，破损不自愈/特效不退级=block，自由文本=info）+ **场景/道具/特效漂移并排人审拼图**（`asset_review/`）；出图前 `scripts/asset_drift_risk.py` 按跨集复用度/出镜/禁漂项/多形态预测物料漂移高危，并对高频但缺 `constraints`/`drift_forbidden` 的资产抬风险 |
| 5 出视频 | `n2d-video` | 由故事板生成每 Clip 视频 prompt → 即梦/可灵/Veo/Seedance 图生视频；视频 prompt 必须消费 `script_quality_contract` 并跑 `script_contract_receipt.py --scope 出视频`，写 `script_contract_applied_第N集.json` 的 `出视频` scope，证明逐镜运动/表演继承 dramatic_function/audience_effect/retention promise。**支持能力报盘（backend_status）与自动化拆段接力（Split Relay）**。正式调用视频后端前默认跑 `dashboard gate --stage video_preflight`，`video_runner.py submit` 也默认先跑该 gate；`scripts/inherit_contract.py` 机检出图→出视频视觉契约继承（光位锚/轴线漂移=block，报告落 `生产数据/contract_inheritance_第N集.json/md`）+ **身份交接契约**（读 `video_model_routes.json` 命名角色镜，核验逐镜 prompt 真锁了身份=声明+具体锚 `CHAR_xx/定妆_/reference_group/character_id/face_lock`，缺=block，治首帧脸→视频脸无契约锚的脸漂）+ **物料约束继承**（C：出图逐镜绑定的 `LOC/PROP/OUTFIT/VFX_xx` 资产在出视频对应 Clip 不得丢失——整块缺=block、id 丢=warn，治场景/道具/特效跨镜无锚漂移）+ **在场链继承**（读取 required/offscreen/forbidden/entry_exit，禁止未登记人物/道具随机出现或消失）；`video_qc.py` 验收/批次 QC 内置**接缝机检**（前镜 end 帧 vs 后镜 start 帧 dHash+色距，阈值复用 n2d-review/temporal_consistency）+ **近景片内身份采样**（CU/MCU/反打镜抽 start/mid/end 帧查表情变化时脸被重画，未到重画阈值或景别不确定时 warn，已知近景非双帧且远超重画阈值时 block；精确同人判定走 n2d-review/temporal_consistency.analyze），`video_runner accept` 遇接缝 block **拒绝验收**（`--allow-qc-block` 确认误报后放行），qc 结果记 manifest+dashboard，并自动写/更新 `native_av_physics_第N集.json`，native_speech 且有音轨时抽取 `native_voice_identity_第N集.json` 声纹片段。`--allow-qc-block` 放行即记一条**机检误报样本**进 dashboard 事件流，供阈值校准。近景 prompt 含**表情锚/表情幅度/锁脸不锁情**三件套，大表情近景强制首尾双帧或 MCU 保真实现 |
| 模型适配层（横切） | `n2d-model-router` | P1 视频模型路由层：按镜头类型/专项模板/身份注册层/原生音画/时长上限，为打斗、追逐、对话、飞行、空镜、法术爆发、亲密互动、拥抱拉扯、多人同框、群像站位选择 primary/fallback；每条 route 写 `execution_recipe`，把后端能力落成调用层可消费的 frame/reference/control/audio/fallback 配方，并写 `policy_resolution`；顶层同步 `policy_lattice` + `生产数据/consistency_policy_lattice.json`，按 fixed mode / 合规硬能力 / native voice fallback / 身份亲和 / motion control / 跨集 baseline / benchmark / prior / 成本档裁决冲突，低优先级只可 deferred 或显式 override。**接力镜走 `seam_relay` 轴**——`need_endframe` 镜优先路由到有双关键帧（首尾硬约束插值）能力的后端，`seam_guaranteed` 时边界帧两镜复用省一次出图；`生视频模型` 只做默认/兜底，`生视频渠道` 只决定实际调用产品/API。三条音画路线：默认 `先出视频后配音`，说话镜先按无声 Image2Video 出画面，真实对白在出视频后拟合；`原生音画` 才把说话镜路由到原生同步音画后端（`mode=native_av`、`native_speech`）；**`配音先行`+`对口型≠关闭`** 说话镜路由 `mode=voice_conditioned_lipsync`（把克隆配音当口型条件喂进 Seedance 2.0/可灵 Omni，音轨仍走配音轨·不双人声·省后期对口型 pass）。`scripts/motion_control.py scaffold/check/generate` 为 `level=required` 镜头生成 gate 兼容的控制资产骨架 manifest + 待补清单（补"只 gate 不生成"的摩擦），可选 DWPose/depth 种子帧；`trajectory_controller_plan.py` 只在本机已准备 MotionCtrl/CameraCtrl/DragNUWA 环境时标 ready，否则留增强计划；`scripts/mouth_detect.py` 按首帧 PNG（装 insightface 时）+ 分镜文本预填/复核每 Clip `mouth_visible`（决定原生音画 opt-in/口型），图↔文本/prompt 冲突标 warn |
| 角色身份闭环（横切） | `n2d-identity` | P0/P1 身份资产执行层：把 `identity_registry.json` 与 reference group、Face Lock、Character ID、reference controls、LoRA 打通，生成 `identity_adapter_matrix` 和跨集 `identity_drift_report`（含 LoRA 升档自动建议 `recommendations` + `characters_needing_lora_upgrade`）；`voice_consistency.py` 对账配音时长清单×voicemap，`voice_print_consistency.py` 量真实声纹漂移并外发 `voice_consistency` 一致性 findings |
| 跨项目资产库（横切） | `n2d-asset-market` | P1 成本摊薄层：把角色原型/定妆组/`identity_registry` 片段、场景 `LOC_`、道具 `PROP_`、武器 `WEAPON_`、独立服装 `OUTFIT_`、特效 `VFX_`、视频模型路由经验、题材母题、招式/打斗套路(`combat_registry` 五帧拆招+动作编排+绑定 `WEAPON_`/`VFX_`)导出成本地资产包，开新剧/新增角色/场景/道具/武器/服装/VFX/设计打斗前先查 `资产库/`；角色导入即 fork 新身份（写 `fork_history[]` 多级溯源链），默认重置 Character ID / Face Lock / LoRA ready 状态并把被重置后端记入 `preserve_review` 审计留痕，再跑 `n2d-identity`；非角色资产导入合并到 `asset_registry.json` 并复制参考图；打斗导入 reskin 重置关键帧（须新剧重出图）。另有项目内内容哈希账本 `asset_registry.py scan/verify`，产 `生产数据/asset_registry.jsonl` / `asset_registry_summary.*`，用于发布资产追溯，不等同跨项目模板 export |
| LoRA 生命周期（横切） | `n2d-lora` | P2/P1 一致性重武器：只给核心长线角色管理 LoRA 数据集、训练任务、验证报告和 registry ready 回写；运行时先检测本机 SDXL/ComfyUI/LoRA 训练链，完整则优先本机 LoRA 训练，不完整则回落项目主/云端生图后端；先把 `.safetensors` 从散文件变成可审计资产；提供本机 SDXL/ComfyUI sidechain 的安装、doctor、route、workflow、production event 记录入口；`suggest` 子命令读 identity 漂移报表打印升档建议（升档触发已工程化）；少量 hero 镜使用非主生图链路 LoRA 时必须写 `生产数据/lora_exception_scope_第N集.json`，声明 clips/reason/style_bridge/QC，避免和项目内生图模型统一规则互相打架 |
| 合规与版权前置（横切） | `n2d-compliance` | P0 合规包：生成/检查 `合规/compliance_manifest.json`，把源文本/改编权、角色肖像授权、声音克隆授权、平台审核、出海本地化和广电备案前置到 gate；`distribution_intent=internal_only` 时平台投放/出海/备案域降 INFO 免检（授权照常 BLOCK）。AI 标识/披露/水印只做非阻断发布待办，compose 可 best-effort 辅助 |
| 6 合成（可选） | `n2d-compose` | 用户启用 `合成阶段` 后，拼 视频 clips + 配音 + BGM + 烧双语字幕 → 成片；**支持子段无缝拼接与 storyboard 转场感知**。默认不阻塞 `clip_delivery_complete`；母版/发布包必须继续过 release/readiness、锁版和人工验收。`tension_mix.py` 按 storyboard 每 Clip `rhythm` 出张力感知 BGM 增益包络（爽点抬/细节压，喂 `BGM_GAIN_EXPR`，不传则原固定行为） |
| 质检·自审（横切） | `n2d-review` | 双模 QA：①作品质检（崩脸/字幕错位/音画/节奏/合规，机检+人判，出定位报告）②流程自审（先 `scripts/self_audit.py` 做本地静态治理检查，再联网对标→审 skills+Q&A→出优化建议）。非必经阶段，任意闸门或成片后可跑。机检含片内时序+接缝（接缝阈值=绝对值+**本集分布自标定离群收紧**）、**跨集画风基线**（`style_consistency.py --cross`，集级指纹 vs 基线集）、动态百科含**角色/道具状态演进机检**（PROP lifecycle 默认结构化，状态泄露/数据质量问题进 gate，自由文本含演进语义标待升级）、**景别阶梯镜序列机检**（连续 ≥3 镜同景别且非反打=景别单调·缺远近/机位变化，warn）；`consistency_audit` 头部亮出本机**机检能力横幅**（无 insightface 时明示降级精度，防机检全绿错觉）。接缝意图以 **storyboard 为唯一真值源**（`_end.png` 存在 but 未声明 need_end_frame → 报真值源矛盾、dHash 降 info）；高动态成片证据 `spectacle_video_qc.py` 接入 SPECV，并可把证据侧写回 MOT1/CAM1/S2V sidecar；`motion_reference_library.py` 只沉淀已实测通过的小样作为后续动作参考；新增补充一致性合约：`motion_grammar_consistency.py`（运动语法 MG1）、`audio_space_consistency.py`（声音空间 ASP / 原生声纹 NV1）、`expression_state_consistency.py`（状态化表情 EXP2）、`intentional_discontinuity.py`（合法不连续签收 DIS）、`consistency_dependency_graph.py`（资产→镜头→图→视频→成片依赖传播 DEP）。**验收总账 `consistency_ledger.py`** 把剧情/角色/资产/镜头/音频/字幕/合规/score/review-ui/gate findings 和这些补充报告收成唯一交付面，`counts.block/high` 未清零不得签收 `验收=✅`。 |
| 进度·下一步（横切·只读）| `n2d-progress` | 扫 `创作区/制漫剧/<剧名>/_进度.md` 逐集矩阵 → 压缩出每部剧完成度 + 生产前沿（下一步该跑哪个 n2d skill）+ 可并行事项 + 次要缺口，按 `制作模式` 解释 `配音=⏳rough`、原生音画跳过配音硬依赖，以及 `合成/验收` 默认跳过；出图/视频/可选成片/配音等花钱·不可逆·合规步骤先提醒确认。**只读·不改文件**。脚本 `scan.py` 纯标准库。触发词：进度 / 当前进度 / 下一步 / 还差什么 / progress / check |
| 项目设置（横切·设置） | `n2d-settings` | `_设置.md` 选择点的唯一 CLI 入口：`audit` 审计非法/过期值，`set` 包住 `set_project_setting` 写入并记录，`reset` 包住 `reset_project_setting` 删除项目覆盖，`sync-global` 包住 `sync_global_settings` 同步私有全局默认；读写/校验仍以 `skills/n2d/_lib/settings.py` 为单一实现，旧别名（如 `保图刷新`）写入时归一到当前值 |
| skill 更新重制（横切·计划） | `n2d-update` | 检测 n2d 相关 `skills/` 文件相对上次快照是否变化，读 `_进度.md` 判断每集当前阶段，生成“从最早受影响阶段回放、最多只重制到当前阶段”的最小重制计划（`生产数据/skill_update_plan_第N集.{json,md}`）；用户说 更新/重制update/rebuild 某作品某集时触发。只生成计划和建议命令，不直接烧图/视频/配音；确认后交 `n2d-batch` 或对应 stage skill 执行。**重制策略选择点 `更新重制策略`**（`--regen-mode` / `_设置.md`）：`最小`（默认）/ `严审刷新`——后者按最新 skill 刷新文字阶段与出图 prompt，再用最新 prompt/QC/review 标准严审旧图，block/warn/降级或人工判定不符合预期的镜都应舍弃重出；旧名 `保图刷新` 仅作兼容 alias，不再表示“尽量保住图片”。**`media` 子命令**（原 `update` 分发器并入）：`update_plan.py media <作品根> 第N集 --image/--video/--target` 为指定集的少量图片/视频生成证据驱动的选择性刷新计划（写 `生产数据/media_refresh_plan_第N集.{json,md}` + `skill_update_runs.jsonl`），只生成计划、不审片，保留/重制结论必须来自已有 gate/QC/review findings 或显式人工输入 |
| 生产数据仪表盘（横切） | `n2d-dashboard` | P0 工业化 + ROI 指标层：每集记录成本、耗时、生成次数、重抽原因、QA 阻断项、最终通过率，并派生每分钟成本、一次通过率、重抽率、投放净回收、回收/生产成本；重抽原因按契约 `REDRAW_REASON_CATEGORIES` 九类维度归类（显式传或按关键词自动归类，存量读时归类），`dashboard.md` 出分维度表 + **一致性小计**；生成 `production_events.jsonl`、`dashboard.json/md`。**实时监控 + 阈值告警(纯本地·跨AI通用)**：record/gate 每次写事件即评估阈值(预算上限/通过率下限/重抽率/QA阻断/回收比)写 `alerts.json/md`；内置 `watch` 轮询 + 本机 `http.server` 自刷新 `dashboard.html`；可选本机弹窗(osascript/notify-send)与 webhook(`N2D_ALERT_WEBHOOK`)；`build --fail-on-critical` 退出码停线。**事件账本审计/重放**：`event_ledger.py audit|doctor|replay` 校验 JSONL、生成 hash chain、只从事件重放 dashboard，产 `production_events_audit.*` / `production_events_chain.jsonl` / `dashboard_replay.json` |
| 批量任务队列（横切） | `n2d-batch` | P1 批量编排 + worker 层：按 `_进度.md` 自动排队，支持并发 claim、失败重试、预算上限、按受影响镜头/Clip/产物最小范围重跑，并可直接承接 `n2d_consistency_ledger` root causes（验收总账，优先）和 `n2d_consistency_findings`（一致性审查 / 人审 UI 导出）生成返工队列；`runner.py` 可自动 claim、执行配置命令、写 dashboard telemetry、回写 pass/fail；生成 `生产数据/batch_queue.json`、`batch_queue.md`。**单机多 worker 安全（纯本地·零后端）**：`flock` 原子认领 + 原子写账本 + 任务租约(心跳续租) + 过期租约自动回收 + `--resume` 崩溃自愈；多机/私有算力池仍需真正的协调后端（flock 跨 NFS 不可靠）。**放量治理**：任务带 `idempotency_key`，失败写 `last_error_class`，超重试进 dead-letter；`governance.py init-slo/check/dead-letter` 产 `production_slo.json`、`batch_governance.*`、`dead_letter_queue.*` |

> **导演运镜 sidecar（script→image→video）**：`n2d-script/scripts/director_camera_plan.py <作品根> 第N集 --write` 在分镜定稿后输出 `生产数据/director_camera_plan_第N集.json/md`，把故事节奏、景别和结构化运镜建议落成两份注入：`n2d-image` 消费 `image_prompt_injection` 写首帧起幅/运动余量，`n2d-video` 消费 `video_prompt_injection` 写导演调度七字段和 `镜头运动`，让生图与生视频 prompt 都带导演镜头语言。
> **n2d agentic runtime（新增）**：`n2d-supervisor` 是上层总控，`n2d/_lib/n2d_action_registry.py` 是 action schema/registry，`n2d/scripts/context_pack.py` 产阶段最小上下文，`n2d/scripts/creative_loop.py` 产创作阶段 evaluator-optimizer 包，`n2d/_lib/n2d_trace.py` 给 dashboard/batch/agent 串 trace/span/idempotency。原则：skill 保持领域知识与确定性工具，supervisor 只派发少量 specialist，不把每个 `n2d-*` 变成自治 agent。
> **n2d-batch 协调后端状态 + adapter 注册表（P2-1）**：`queue.py coordination-status <作品根>` 会报告 `local_file` / `shared_fs` / `sqlite`（内置事务后端·active）/ `redis|db|object_store`，并把当前 `coordination` 写进 `batch_queue.json/md`。内置执行是 local/shared-FS 文件锁 + lease + SQLite。**外部协调后端不再是死路**：`queue.py` 定义了正式的 `CoordinationBackend` 协议（`load_queue/sync_from_queue/claim/mark/reclaim/renew` 六法）+ 注册表——ops 侧实现该协议的类后 `import queue; queue.register_coordination_backend("redis", RedisBackend)`，再设 `N2D_COORDINATION_BACKEND=redis`，`claim/mark/reclaim/renew/load_queue/save_queue` 会经统一分发口 `active_coordination_backend(root)` 真走它，`coordination-status` 也从 `declared_not_active` 转报 `ok·external_adapter`。`sqlite` 是内置参考实现，JSON 账本始终是可移植真值镜像。未注册工厂时仍如实报 `declared_not_active`，不假装多机安全。
| 自动审片评分（横切） | `n2d-score` | P2 机器评分层：每集输出语义继承/状态百科/多模态漂移 + 角色/服装/场景/字幕/音画/节奏/风格维度分，并接入图像相似度、字幕 OCR、音画时长对账、口型风险/检测报告、成片节奏密度；脸 G1 无 insightface 时按 `pillow_fallback` 降权分消费（不再整维度缺数据）；低于阈值生成 `auto_return_tasks`，可写入 `n2d-batch` 定向返工队列 |
| 人审可视化 UI（横切） | `n2d-review-ui` | P2 可视化层（零构建 HTML/JSON，只读不改状态）：① `review_ui.py` 单集人审画布（首帧/尾帧/clip/接缝/定妆/QA flag/机器分；接缝卡装配 video_qc 机检距离并按 transition 分级——**match/hard/action cut 标必看人判**，机检对设计切镜不可判匹配元素），可 `--export-findings` 输出 `review_ui_findings_第N集.json` 供 `n2d-batch --from-consistency-findings` 回流；② `board.py` 整部生产看板（读 `_进度.md`→作品/集/阶段/Clip+接力链+进度色，`--serve` 本地 127.0.0.1）——PC端+无限画布愿景的 MVP（Q36）；③ `calibration.py init/score` 用金标 case 校准审片员 block/warn/pass 口径，产 `review_calibration.json/md` |
| 投放数据回灌（横切） | `n2d-feedback` | P2 增长反馈层：导入平台留存/追更/跳出数据（实时投放 API 经摄取适配器规范化成标准 `platform_metrics` 文件，支持中文列名别名），并从 `storyboard.json` 自动抽取导演标签；同集开场/封面/集尾断点/标题文案 A/B，按 paired lift 分析；新增付费/追更闭环字段 `paywall_position_sec/paywall_after_promise_id/unlock_friction/continue_path`，分析解锁卡点和续看路径；生成 `platform_feedback.json/md`，可更新 `导演节奏.md` 快照和 `creative_priors.json`；`experiments.py upsert/audit` 维护 `creative_experiments.json` 并审计 A/B 是否有实验定义、变体与样本；另读 `生产数据/consistency_findings_*.json` / `review_ui_findings_*.json` 出「一致性问题 Top」与留存/跳出并排（QA 线接进投放闭环） |

> **高动态/大场景工业化前置（2026-06）**：`n2d/run.py next` 到 `image_prompt` 前自动跑 `n2d-script/scripts/spectacle_contract_audit.py`、`shot_risk_audit.py`、`spectacle_plan.py --write`、`spectacle_sequence_plan.py --write`、`scene_layer_pack.py --write`、`spectacle_probe_pack.py --write`；到 `video_prompt/video` 前自动写 `motion_control_manifest.json` 骨架与 `trajectory_controller_plan_第N集.*`；到 `compose` 前自动写 `action_edit_cues_第N集.json/md`；审查后可写 `spectacle_video_qc_第N集.json` 与 `motion_reference_library.json`。核心产物：`生产数据/spectacle_plan_第N集.*`、`spectacle_sequence_plan_第N集.*`、`scene_layer_pack_plan_第N集.*`、`spectacle_probe_pack_第N集.*`、`spectacle_backend_benchmark.json`、`action_edit_cues_第N集.*`、`spectacle_video_qc_第N集.json`、`motion_reference_library.json`。动作/奇观模板统一要求 `keyframe_plan`、`post_cue_points`、`physics_guard`；`magic_burst`（法术/武技/剑气/斗法撞点）已进入奇观计划、Motion Control、路由、合成 cue 和 SPECV。router 会读取 benchmark，把打斗/追逐/飞行/武技爆发/大场景小样结果回灌到 primary/fallback（固定后端模式除外），并在 `execution_recipe` 中暴露 motion reference 调用口。

> **选择点 `制作模式`（出片顺序）**：默认 `先出视频后配音`（后配音：先用估算/占位时长推进分镜、出图和无声 Image2Video，默认到 `clip_delivery_complete`；若用户启用 `合成阶段`，再补真实配音并在 compose 前拟合；推进快，但可能重定时或重出部分镜头）。强配音控制、指定配音演员音色、少返工或后端 image2video-only 且需精准口型时选 `配音先行`（真实配音时长驱动镜头，音画准·表演可控）；特殊同步音画后端/快速预览才选 `原生音画`（说话镜一次出同步音画，少逐句音色控制，仿真人音色仍需授权）。三种流程图 + 完整理由见 `n2d/SKILL.md`「制作模式」节；选择点定义见 n2d 线 `references/选择点与偏好.md`。
> **选择点 `合成阶段`（可选尾段）**：默认 `跳过`，即 `_进度.md` 的 `视频` 列完成只算 `clip_delivery_complete`。用户需要母带、BGM、烧字幕、屏幕文案 overlay、交付矩阵或发布证据包时，设为 `启用` 或直接调用 `n2d-compose`；从那一刻起 `成片/验收` 才参与路由，最终以 `master_delivery_complete` 口径交付。
> **三轨音字执行铁律**：`n2d-script` 把每个物理 Clip 拆成 `dialogue / narration / screen_text` 三轨并写入 `dialogue_fact_contract_第N集.json`。`n2d-video` 只生成画面和必要的画内角色对白口型；旁白不交视频模型生成，屏幕文案/花字/字幕不让视频模型烤字。默认视频完成不做后期音字叠加；需要旁白混入、字幕/花字/系统面板数值或屏幕文案 overlay 时启用 `n2d-compose`，它是唯一执行这些后期层的阶段。
> **机器契约层**：n2d 的阶段图、`_进度.md` schema、gate stage、manifest 与结构化回滚字段集中在 `skills/n2d/_lib/n2d_contract.py`，人读版见 `n2d/references/contract.md`。`skills/n2d/_lib/n2d_route.py`、`n2d/progress.py`、`n2d-progress/scan.py` 和 `n2d-review/scripts/gate.py` 复用同一契约；阶段职责变更时先改 contract，再同步本索引与各 SKILL.md。**横切口径分两层**（判据=「在位与否是否影响生产推进」，不是「有没有输出文件」）：① 影响生产推进的就绪信号（合规[硬前置]/身份/LoRA/资产库/仪表盘/投放回灌）登记在 `n2d_contract.CROSS_CUTTING_READINESS`（旧别名 `CROSS_CUTTING` 兼容），`n2d-progress` 据此输出「横切就绪」；② 无稳定就绪标志、或本身是调度/观察/计划工具的（model-router/batch/progress/review + **评分/审片UI/skill 更新重制**这类可选观察产物）登记在 `n2d_contract.CROSS_CUTTING_TOOLS`，不进「就绪」行（`n2d-progress` 把有 per-work 产物的工具单列为「横切观察·非前置」），不污染 `_进度.md` 流程表。新增横切能力时按这两个边界登记 + 同步本索引。每次 `progress.py set` 会自动刷新 `脚本/第N集/manifest.json` 快照，也可用 `python3 skills/n2d/manifest.py <作品根> 第N集 [--stage stage_key]` 手动重建。

> **合规与版权前置（P0）**：新剧或投放前先跑 `python3 skills/n2d-compliance/scripts/compliance.py <作品根> --init`，人工补齐后用 `--check` 预检。`n2d-review/scripts/gate.py` 在 image/video/compose/review 四个阶段都会读取 `合规/compliance_manifest.json`：源文本/改编权、角色肖像授权、声音克隆授权、平台审核、出海本地化或广电备案缺任一项，先阻断，不能等成片后补救。AI 标识/披露/水印只做 INFO 发布待办，不阻断主流程。
> **仙侠武侠打斗专项工艺**：`n2d-script/references/打斗分镜.md`（五帧拆招/命中帧出图/首尾帧锁动作/后期补打击感），已挂接 script/image/video/compose/review 全链；总纲见 `n2d/Q&A.md` Q31。
> **动作奇观精修标准**：`n2d-script/references/动作奇观精修标准.md`（战斗/飞行/突破/武技高光，把“经费燃烧感”拆成关键帧覆盖、命中/峰值可读、剪辑/音效同步三项 premium QC），同样挂接 script/model-router/video/compose/review 全链。
> **仙侠非打斗奇观工艺**：`n2d-script/references/仙侠场面分镜.md`（御剑飞行/追逐/渡劫突破/炼丹炼器/大阵法阵/大场面 establish/斗法对轰/神魂(神识·元神出窍·夺舍)——飞行追逐锁姿态动背景、渡劫炼丹法阵对轰爆发帧出图+元素入库、神魂元神=肉身半透明派生治"二我"、大场面三镜由远及近），同样挂接全链；总纲见 `n2d/Q&A.md` Q33。
> **静修 / 炼制 / 双修 / 亲密动作工艺**：`n2d-script/references/静修炼制双修精修标准.md` 与 `n2d-script/references/亲密动作精修标准.md`。打坐/静坐/冥想不写空镜，必须锁坐姿、呼吸周天、灵气路径和内在结果；炼丹/炼器必须锁阶段流程、火候曲线、材料状态和成品揭示；双修只做成年人、自愿、非露骨的能量循环/疗伤表达；接吻/拥抱/牵手/搀扶必须锁年龄语境、同意边界、脸部角度、接触点、遮挡顺序、身体部位归属和释放/停住帧。
> **资产库题材自适应**：共享定妆库通用三类（角色/场景/道具）+ ⚙️仙侠玄幻可选两类（**法宝/特效**，本命法宝按形态多态、剑气/光效锁颜色拖尾）；**人物定妆固定标准三视图**——所有人物角色先出正面 / 侧面 / 背面生产拆图，并生成 `定妆_<角色>_三视图.png` 人审拼版；场景才按题材和复用程度补**场景多视图（四视图）**保跨镜背景自洽；见 `n2d-image/references/prompt_format.md §1`+`角色一致性checklist.md`、`Q&A.md` Q32。
> **题材母题(motif)增强工艺（穿越/系统流复现桥段·横切全链）**：穿越/系统流爽文里"系统面板出现/升级/系统刷新/签到/抽奖/爆装备"是相对固定但带成长（面板进化、等级只增不减）的高频复现母题，做好观众爱看。motif 是 n2d 线内一等概念：① `n2d-script/scripts/motif_detector.py` 在分镜阶段**检测题材+母题桥段**（关键词单一真值源 `n2d_const.GENRE_KEYWORDS/MOTIF_TYPE_KEYWORDS`），出 `生产数据/motif_plan_第N集.md` 建议→**人确认后** `--write` 注回 `storyboard.json`（`template=system_panel`/`motif_id`）+ 写 `出图/共享/motif_registry.json`；题材落 `_设置.md` `题材`/`母题增强` 弱选择点（检测预填可覆盖）。② 镜头模板 `专项镜头模板库.md` §0.2 通用 motif 形态 + §12 `system_panel`。③ **混合渲染**：`n2d-image` 让 AI 只出锁色锁形发光光幕底框（`VFX_系统面板`，`drift_forbidden` 含 `text_baked_in`、prompt 强制 negative 掉文字数字），成长用 `asset_lifecycle.py` 状态机机检面板档位只进不退（零新增代码）；④ `n2d-compose/render_panel.py` 读 `motif_registry` progression+overlay_spec，把等级/属性数值用 Pillow overlay 叠成清晰文字层（面板层在字幕层之下，复用 subtitle_render 链）；⑤ `n2d-asset-market export/import-motif` 跨剧复用母题 pack（import 重置成长 progression）。系统面板是首样板，后续金手指/签到/抽奖只加配置不改架构。总纲见 `n2d-script/references/题材母题框架.md`。
> **模型矩阵 + 模型路由（防过期快照）**：各轴 SOTA vs n2d 默认 vs 升级触发（含图/视频/配音 + **口型 lip-sync**：后端音频参考口型（Seedance 2.0 音素级/可灵 Omni，由 router `voice_conditioned_lipsync` 喂克隆配音、不双人声）首选，后期 MuseTalk/Wav2Lip/LatentSync 兜底；配音情绪解耦 IndexTTS-2），见 `n2d/references/模型矩阵.md`，由 `n2d-review` 流程自审每次检查，默认只给刷新建议；用户确认落地后再刷新矩阵——版本名只活在带日期的快照里，正文写能力不绑版本。视频阶段新增 `n2d-model-router`：`视频模型路由=自动按镜头路由` 时，打斗/追逐/对话/飞行/空镜/法术爆发/亲密互动/拥抱拉扯/多人同框/群像站位按能力选择 primary/fallback；`生视频模型` 不再固定每个 Clip，只作为普通镜和兜底模型，`生视频渠道` 只决定执行入口。新作品开局不再强问具体视频模型/渠道，只有固定后端、账号/交付约束或探测失败时再问。
> **单 Clip 上限按后端（非一刀切 8s）**：机器真值源在 `skills/n2d/_lib/n2d_platform_profiles.py`（即梦 image2video≤8s / Seedance≤15s / 可灵≈10s / Veo 3.1≈8s；Sora legacy/manual-only 不进自动路由），`n2d-video/references/platforms.md` 负责人读解释，`n2d-model-router` 与 gate 读 `_lib` 值——能一镜到底就别切碎（更少拼接缝·跨镜更稳）。
> **clip 衔接接力链（治"剪起来跳"·横切全链）**：clip 间顺滑是一条逐级继承的接力链，单一真值源在 `n2d-script`。① `n2d-script` 在 `故事板.md`/`storyboard.json` 把每个接缝写成契约：`上一 Clip 出点 = 下一 Clip 入点`（同一句）+ `转场类型` + `需要尾帧?` + `entity_schedule` 在场链（required/offscreen/forbidden/entry_exit，解释人物/物件入画出画或画外保留）（见 `references/formats.md §4`）。② `n2d-image` 在标 `需要尾帧` 的接缝出**尾帧 PNG `镜头N_end.png`**（命名=首帧名+`_end`，亦兼容 `Clip_NN.png`→`Clip_NN_end.png`；=下一 Clip 首帧构图，最省做法复用下一 Clip 参考图组）。③ `n2d-script/scripts/anchor_planner.py` 执行**风险分层三帧契约**：打斗/追逐/飞行/亲密接触/大表情、≥8s 多拍长镜、R3 漂移重抽镜强制规划 `_a1.._aN`；普通低风险镜只有 `中段锚帧默认=开启` 且后端能表达 ≥3 帧时才补 `_mid`，ROI/速度优先可关闭并写 `policy.midframe_default=false` 留痕。④ `n2d-video` **读取**契约不重写 start_state，并按后端能力落地：即梦 `multiframe2video` 已核验可原生吃 2–20 张首/中/尾时间轴帧；Veo/Luma/可灵等首尾帧后端只确认 first/last，中锚需拆段接力、extend/interpolate 或仅作 QC；首帧/参考图后端退回单首帧 + 强 end_state 文字或 reroute。`video_preflight` 查契约完整、prompt 誊抄不丢锚，并对不支持中锚的路由给「多帧能力」WARN，避免 `_mid` 被静默忽略；在场链会被转成正负 prompt 约束，禁止未登记人物/道具随机出现或消失。⑤ `n2d-compose` 按 `转场类型` 接 clip（有意硬切硬切/跳变微溶解/缺空镜报警），不盲拼。⑥ `n2d-review` 逐接缝并排读图查跳切/闪烁/接力断链。
> **机器闸门**：n2d 高风险阶段正式生产入口统一跑 `python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image_preflight|video_preflight|image|video|compose|review`。默认用法分两层：正式调用后端前跑 `image_preflight` / `video_preflight`，生成落档后跑 `image` / `video` 回验。它调用底层 `n2d-review/scripts/gate.py --json`，检查合规包、占位配音、`storyboard.json` continuity、尾帧、prompt 检查段、生图模型/渠道一致性、clip 音轨/时长、**P0 语义谱系 / P1 状态百科（角色+道具状态演进）/ 景别阶梯镜序列** 等项，并把 `block/warn/info`、`return_to_stage`、`rerun_scope`、`affected_artifacts` 写入 `生产数据/`；同时外发 `gate_findings_<stage>_第N集.json`（kind=`n2d_consistency_findings`），可直接交给 `n2d-batch --from-consistency-findings` 入队；验收总账 `consistency_ledger_第N集.json` 可交 `n2d-batch --from-consistency-ledger` 按 root cause 入队。退出码沿用 gate（有 block 即 1）。裸 `gate.py --json` 只作调试/机器消费入口。preflight/image/video/compose/review gate 都会阻断缺 `合规/compliance_manifest.json` 或角色授权/声音克隆授权/平台审核/出海本地化/广电备案未就绪；image_preflight/image gate 放行官方/已登录多参考后端但阻断项目内后端混用，且**合并出图落档机检 `image_qc` findings**（生图前无 PNG 时像素项为空但 prompt lint 生效；生图后真验像素），并读 `production_events.jsonl` 硬拦本地贴脸/换脸/裁脸贴回画面产物——运行前/报告中必须明示 `qc_environment.precision_level=full|degraded|none`、当前解释器、建议安装和阶段跳转，推荐 full stack 为 Pillow + cv2 + insightface + onnxruntime + buffalo_l（优先 `facefusion` conda env），缺依赖不得静默跳过或当作通过；角色 DNA 像素机检覆盖第1层脸 G1 / 第2层发型 H1 / 第3层服装 N1（第4层配饰由 registry + 人审对照），并跑场景 O2 / 人体解剖 N5 / 接缝 / 锚点门 N3 + 逐镜 prompt lint（参考图块/视线/锚点句/`CHAR_xx` 在 registry 合法性/人体完整性·手部归属·身体接触面），硬阻断（崩脸/人体解剖N5铁证/纯文生图/非法 CHAR_id/接缝断/降级精度近景/缺高风险人体合约/本地贴脸修复产物）让 gate 非零并回 `image`，初筛项 warn 交人判；image_preflight/image gate 另机检**景别阶梯镜序列单调**（读 `storyboard.json clips[]` 景别序列，连续 ≥3 镜同景别且非反打/过肩=缺远近·机位变化，warn）与**道具状态演进**（PROP lifecycle 默认结构化，状态泄露/未结构化进 gate）；`n2d-update` 重制计划覆盖 image 阶段时自动追加 image gate 作验证步，闭合"重出图→验像素"环；video_preflight/video gate 会阻断缺导演一致性契约或逐 Clip 缺导演调度五字段，并**前置核验输入首帧出图落档机检**（读 `image_qc` 持久化结果 + 最新 image 生产事件：`hard_blocks>0` 或本地贴脸修复产物=BLOCK；缺结果、旧版 QC、非 full、覆盖缺口、帧晚于 QC 也回 `image`——image2video 忠实动画首帧缺陷，别花最贵的图生视频钱动画一张崩脸/未验首帧）**并核验视频 prompt `01_clips.md` 实际提交的首帧/尾帧 PNG**（runner 喂后端的那条路径，与 storyboard 字段分开誊抄：首帧缺=BLOCK 必白扣一次，尾帧缺/双帧意图丢=WARN 降单首帧）；review gate 另跑 **P2 多模态视觉语义/道具漂移** + **L1 双语字幕对齐**（中↔英短语边界/阅读速度/译文完整性，补 mechanical_check 条数对账盲区）。
> **角色 DNA + 资产引用闭环（P0）**：人物/形态先归 `设定库/角色圣经.md`（Character Bible，人读总入口），机器执行真值归 `identity_registry.json`，并统一按**角色 DNA 四层**登记和审查：脸 / 发型 / 服装 / 配饰；气质/动作习惯放在角色圣经作为表演层，不塞进 registry 四键。关键场景、关键道具、独立服装/盔甲、法宝/VFX 归 `asset_registry.json`。逐镜 prompt 必须写 `角色圣经引用`、`资产身份注册层` 与 `资产引用注册层`，用 `CHAR_xx/形态`、`LOC_xx`、`PROP_xx`、`OUTFIT_xx`、`VFX_xx` 绑定参考组与漂移禁区；image gate 缺注册表、缺逐镜 ID 绑定、ID 类型前缀不匹配、关键道具结构约束不完整都会阻断。服装若是角色形态的一部分，放在 `identity_registry.json` 形态里；能跨角色/跨场单独复用或会独立漂移的服装才建 `OUTFIT_xx`。只锁脸不算角色 DNA 一致，发型、服装或标志配饰漂了同样按换人感处理。`identity_registry.json.generation_control` 可登记固定 seed pool；支持 seed 的后端传池内值，不支持/未暴露 seed 的后端记 `seed_effective=false` no-op 降级，不把 Codex 等入口误报成可复现。
> **生产数据仪表盘 + ROI（P0）**：每次 n2d 生成、审查或投放回收后，调用 `n2d-dashboard` 记录事件；成本、耗时、生成次数、重抽原因、QA 阻断、最终通过率、每分钟成本、一次通过率、重抽率、投放净回收、回收/生产成本统一落 `创作区/制漫剧/<剧名>/生产数据/`。`_进度.md` 只管阶段状态，`n2d-dashboard` 才是判断“工业级是否成立”的指标真值源。gate 结果用 `python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image_preflight|video_preflight|image|video|compose|review` 入账，生成事件用 `record` 入账；平台收入/投放成本放 `生产数据/platform_metrics.csv|jsonl|json` 或 `record --event release` 入账。**开跑前成本预检**用 `dashboard.py forecast <作品根> 第N集 [--budget N --unit CNY]`：历史 `cost_per_finished_min` × 本集计划时长给预测成本 + 预算够撑几集 + 重抽漏点 Top（事后记账之外补一个事前估算；无历史/无计划时长则不臆造）。`dashboard.md` 另出**行业基准对照**（默认读 `n2d-dashboard/references/industry_benchmark.json`，一次通过率/重抽率/每分钟成本/跨集一致性 并排行业宣传基准，只读·非闸门，可 `_设置.md` 或项目级 `生产数据/industry_benchmark.json` 覆盖，基准以 `n2d-review` 流程自审复核为准；留存基准刷新后必须跑 `validate_benchmark_schema.py`）。
> **工业化量产可行性分析**：详见 `docs/n2d-industrial-feasibility-study.md`，从原子化解耦、SSOT、ROI 导向等维度评估漫剧生产线的工业化成熟度与优化路线图。
> **批量任务队列（P1）**：多集推进时先用 `python3 skills/n2d-batch/scripts/queue.py plan <作品根> --episodes 1-10 --max-concurrency 2 --budget <N>` 生成队列；执行者用 `claim` 占并发槽，用 `mark` 记录 pass/fail，失败按 `max_retries` 自动回到 `retry_queued` 或落 `failed`。配置 `生产数据/batch_runner.json` 后，可用 `python3 skills/n2d-batch/scripts/runner.py <作品根> --until-empty` 自动 claim、执行、写 dashboard telemetry、回写状态；标准 wrapper 在 `skills/n2d-batch/scripts/run_n2d_image.sh`、`run_n2d_video.sh`、`run_n2d_compose.sh`，示例配置见 `skills/n2d-batch/references/batch_runner.example.json`。定妆变更、gate finding、审片问题用 `--rerun-from image|video|compose --affected-shot/--affected-artifact` 只重跑受影响范围，不整集重来。**单机多 worker**：各 worker `runner.py <作品根> --until-empty --worker w1 [--resume]`——`claim/mark` 全在 `batch_queue.lock` 的 `flock` 内重读最新队列+原子写，绝不双认领；任务带租约+心跳续租，worker 崩了租约过期自动被别的 worker 回收，`--resume` 立即自愈本 worker 残留 running。`queue.py reclaim <作品根>` 手动回收。**这是纯本地零后端方案；真·多机要换协调后端**。
> **自动审片评分（P2）**：成片或阶段审查后跑 `python3 skills/n2d-score/scripts/score.py <作品根> 第N集 --run-checks --threshold 85`，生成 `生产数据/score_第N集.json/md`。它汇总 n2d-review 机检、一致性审查、n2d-dashboard 阻断，并新增 `visual_checks.py`：接缝图像相似度、字幕 OCR、成片/配音/SRT/storyboard 时长对账、口型检测报告/口型风险、成片节奏密度。语义继承/状态百科/多模态漂移和原有视觉/字幕/音画/节奏维度都会映射回 `script_stage2` / `image` / `compose`；加 `--enqueue-low` 可直接写入 `n2d-batch` 返工队列。
> **人审 UI / 无限画布（P2）**：机检和机器分之后跑 `python3 skills/n2d-review-ui/scripts/review_ui.py <作品根> 第N集 --write --export-findings --markdown`，生成 `生产数据/review_ui_第N集.html/json` 与 `review_ui_findings_第N集.json`。HTML 静态可打开，集中看首帧、尾帧、clip、接缝、定妆参考、QA flag、机器分和缺素材；批量审片时先用筛选器看 block/warn，再逐接缝和高风险 clip 人判，红黄 flag 可直接交给 `n2d-batch --from-consistency-findings` 回流。
> **投放数据回灌（P2）**：上线一批后跑 `python3 skills/n2d-feedback/scripts/feedback.py <作品根> --metrics <平台指标.csv> --update-guide`，用平台留存/追更/跳出数据反哺 `n2d/references/导演节奏.md`。`creative_features` 默认从 `脚本/第N集/storyboard.json` 自动抽取 `opening_type/cliffhanger_type/shot_density_per_min/hook_interval_sec`，需要复核时加 `--write-features` 落 `creative_features.auto.json`，手工文件或 `--features` 仍可覆盖；同一集多投放版本时在 metrics/features 写 `ab_test_id + variant_id + opening_variant/cover_variant/cliffhanger_cut_variant/title_variant`，报告会额外算同集 paired lift，比较开场、封面、集尾断点、标题文案对留存/追更的影响；付费/追更平台还要写 `paywall_position_sec/paywall_after_promise_id/unlock_friction/continue_path`，报告会分析解锁卡点和续看路径；样本不足只写观察，不把偶然数据写成铁律。
> **视觉契约 + 基础视觉风格契约三层同源**：色调/光位/轴线·视线/人物状态/景别这些**视频改不动、要烤进首帧像素**的导演决策，源头在 `n2d-script` 分镜设计——`storyboard.json` 写 `visual_contract` 种子块 → `n2d-image` 的 `出图/第N集/prompt/00_总览.md`「本集视觉一致性契约」继承+细化、逐镜带 `视线方向/光位锚/起幅·运动余量`（首帧=起幅非动作顶点、为运镜留构图余量）→ `n2d-video` 的导演一致性契约再继承。基础视觉风格同理：用户先选 `基础视觉风格` → `global_style.md` 写风格源头 → `storyboard.json.style_contract` 写风格名/视觉基调/镜头与构图/光色策略/运动边界/风格禁忌 → 出图总览「本集基础视觉风格契约」把所选风格烤进首帧 → 出视频总览继承并只做相容运动。image gate 阻断 storyboard 缺 `visual_contract` / `style_contract` 或总览缺契约；compose gate 另查成片时长对账（amix 静默截断超长配音）+ 合规包待办提醒（画幅按 `_设置.md` 不写死）。配音侧 `设定库/voicemap.json` 持久绑定角色→音色（跨集稳定，manifest 记 `音色键/voice_id` 供机检），零样本克隆喂参考音同 `voice_clone.py` 一样硬闸门要 `VOICE_CLONE_AUTHORIZED=1`。
> **崩脸机检（自标定 flag-band）**：装 `insightface` 后跑 `n2d-review/scripts/face_consistency.py <作品根> 第N集` —— **不写死阈值**，用本作定妆组内部互相余弦当"同一人下限"地板，每镜低于 地板−margin=🔴/地板带=🟡（治写死 0.45 对风格化脸误杀/放过）；缺库优雅跳过交人判，纯数学部分带 pytest。
> **一致性机检套件（都自标定·缺库优雅跳过·纯数学带 pytest）**：① **P0 `semantic_continuity.py` 语义谱系 Diff**：抽取 `voiceover.txt → storyboard.json → 出图 prompt → 出视频 prompt` 的角色/场景/状态/风格/模板/continuity 关键词，检查下游是否继承上游，匹配层含精确词/常见同义别名/中文 bigram 重叠，提前抓语义变形；② **P1 `state_continuity.py` n2d 动态百科/状态哨兵**：读取 `storyboard.json.visual_contract.角色状态演进` + `出图/共享/visual_state_ledger.json`，抓状态提前泄露、开始后漏继承、区间结束后泄露，`until/至 ClipN/本镜` 会被当作状态区间；`state_ledger_build.py <作品根> --episodes 1-10 --write` 可从 storyboard 确定性生成跨集 visual_state_ledger；③ **P2 `multimodal_consistency.py` 多模态视觉语义/道具漂移**：按非角色参考资产（场景/道具/法宝/特效）分组，用本地视觉 embedding（RGB 直方图 + dHash；可后续接 CLIP/DINO/SAM）找组内离群，角色优先由 `identity_registry.json` 判定，非角色资产优先由 `asset_registry.json` 判定；④ `face_consistency.py` 锁角色 DNA 第1层**脸**（含 `--audit-anchor`=**N3 定妆主参考质量门**：恰好 1 张清晰够大正脸才配当锚点，治"锚点一脏下游每镜继承"）；⑤ `hair_consistency.py` 锁角色 DNA 第2层**发型/发色**（头部区域发色+发型轮廓复合指纹，治"脸过了但披发变盘发/黑发变白发"）；⑥ `outfit_consistency.py` 锁角色 DNA 第3层**服装/配色**（加权色相直方图，治"脸没崩但夹克色第4镜就漂"，需 Pillow；**含同角色镜组相对离群二次校准**——老逻辑拿"镜头整帧 vs 中性灰底定妆"算绝对相似度，戏剧布光/CU 构图会把整组镜一起拉低误报，校准后整组一起低=场景污染放行、只报相对本角色明显偏低的镜，镜组<3 张 block 降 warn，`--rel-margin/--min-group` 可调，只下调误报不新增漏报）；角色 DNA 第4层**配饰**以 registry `character_dna.accessories` + 人判并排图为主；⑦ `temporal_consistency.py` 锁**单 clip 内**身份漂移 + flicker/TCI（ffmpeg 抽帧，治"几秒后脸渐变/发际线闪"，对标行业 scene-stability 记分卡）；⑧ `quality_check.py`=**N4 糊/低质无参考质检**（Laplacian 方差·自标定本集中位数，关键镜更严）；⑨ `scene_consistency.py`=**O2 场景/环境一致性**（同场景多镜 dHash 结构离群 + **光位/色调离群**[明度+饱和加权色相指纹·光位锚的可机检代理]·自标定，治背景漂移与光打错向/色温跳，需 Pillow）；⑩ `style_consistency.py`=**S1 风格一致性**（每镜风格指纹[饱和+明度直方图+边缘密度]·median-中心自标定，治"某镜突然偏离所选风格"，补 `style_contract` 落地后零机检的盲区，需 Pillow）；⑪ `temporal_consistency.py --seam`=**接缝接力**（尾帧 vs 下一首帧 dHash，距大=出视频跳切，把"逐接缝人判"降成机检初筛）；⑫ `n2d-identity/voice_print_consistency.py`=**音色声纹一致性**（speaker embedding，自标定 flag-band，输出 `voice_consistency` findings）。**一键编排 `consistency_audit.py <作品根> 第N集`** 串跑视觉/语义类检测器出一张汇总分档表，并保留 `details/affected_shots/affected_artifacts/auto_return_tasks`（O1·检测器再多没被自动跑=没有）——`n2d-review` 模式①工作流第 1 步即调它。覆盖「语义继承→状态演进→视觉语义/道具→定妆(锚点门)→首帧→接缝→片内→场景(结构+光色)→风格→清晰度」全链。另：`n2d-identity/scripts/identity.py <作品根> --write` 汇总 Face Lock / Character ID / LoRA / reference group adapter matrix，并生成跨集 `identity_drift_report` 与声纹 findings；gate 还强制逐镜负向含风格禁忌、运镜越运动边界 WARN、风格名↔基础视觉风格软校验。
> **定妆变更影响扫描 + 连锁更新自动化**：改了共享定妆资产后，`n2d-image/scripts/asset_impact.py <作品根> <资产名>` 列出引用它的下游镜头（已出图的需重出），属 `n2d-review` 机检家族；兼容两种 prompt schema。加 `--rerun-plan` 直接出**连锁重跑计划**（受影响集 → 重出图 → 刷新身份 → 重出视频 → 重合成 → 每集一条最小范围 `n2d-batch --rerun-from image --affected-artifact/--affected-shot` 命令），把"改一个定妆要回头排查哪些集/镜头/clip"的人工活自动化。除文本「参考图」行外**同时读 registry 结构化绑定**（prompt 只写 `CHAR_xx` ID、靠 registry 自动取参考的镜头不再漏）；`--include-video` 加「已出视频需重生」清单、`--check-native-adapters` 列「后端身份注册基于旧定妆需重注册」、`--output-batch-tasks 计划.json` 输出 batch 直接可吃的任务 JSON（`queue.py plan <作品根> --from-asset-impact 计划.json` 自动排队，免手抄命令）。
> **接缝自动化（n2d-compose 已落地）**：`n2d-compose/seam_concat.py` 按 `storyboard.json` 每接缝 `continuity.transition` 自动接 clip——硬切裸拼 / 跳变·未焊→局部 `xfade` 微溶解 / 缺空镜→报警；硬切相连段先 `concat -c copy`、只在溶解接缝重编码，无溶解时等价旧行为，ffmpeg 失败自动回退裸拼。`compose.sh` 拼接步已接入（`SEAM_FALLBACK`/`SEAM_DISSOLVE_SEC` 可覆盖）。
> **角色身份闭环（P0/P1）**：`identity_registry.json` 是真值，`n2d-identity` 把它展开成 `identity_adapter_matrix.json/md` 和 `identity_drift_report.json/md`。reference group、Face Lock、Character ID、reference controls、LoRA 都必须进同一矩阵；`registered/ready` 空句柄、后端 mode 不匹配、LoRA ready 缺 `base_model/model_path/trigger` 都由 gate 阻断。跨集脸漂不再只靠人记，报表会给出角色级 `first_bad_episode`，供 `n2d-batch` 只重跑受影响集/镜头。
> **跨项目资产库提示（让用户不用记 CLI）**：开新剧、建角色卡、出图新增共享定妆/场景/道具/武器/服装/VFX，或某类路由/打斗经验值得沉淀时，agent 先提醒“我会查资产库，有可复用模板就问你是否导入”，再后台跑 `python3 skills/n2d-asset-market/scripts/market.py list`。制作过程会先自动沉淀到本项目 `identity_registry` / `asset_registry` / `character_assets`，但不会自动外溢到跨项目 `资产库/`；只有用户或 agent 判断资产稳定、审过、授权清楚、值得复用后，才主动导出。导入角色模板后必须 fork 新 `character_id/name`，并跑 `python3 skills/n2d-identity/scripts/identity.py <作品根> --write`；用户只需说“查资产库 / 导入冷宫废妃模板为沈念 / 把这个武器导出成模板 / 把这套打斗沉淀成模板”，不要要求用户背命令。
> **LoRA 生命周期（第三档一致性）**：LoRA 不默认启用；只有核心长线角色在参考图派生 + 后端原生角色 ID/主体库仍不稳时，才调 `n2d-lora`。它管理 `设定库/lora/<CHAR_ID>/<形态>/` 下的 `lora_card`、`dataset_manifest`、`train_job`、`validation_report` 和 `.safetensors`；验证报告未 `pass` 不得写 `identity_registry` 的 `lora.status=ready`。用户只需说“给沈念启动 LoRA 生命周期 / 验证这个 safetensors / 写回 registry”，不要背命令。
> **角色 DNA 梯子（出图）**：①参考图派生（默认）→ **②后端原生角色ID/主体**（可灵主体库 / Seedream Universal Reference；Sora Cameo 仅旧项目 manual·注册一次按 ID 引用·opt-in·先于 LoRA 用尽）→ ③LoRA。能力对照见 `n2d-image/references/platforms.md`「后端原生角色ID / 主体库」，opt-in 流程见 `n2d-image/SKILL.md` 同名节；后端无持久 ID 自动回退第①档。**出图侧锚定双保险**：锚点句（锁特征词）+ **身份锁定句**（锁"与参考图①同一角色 DNA"，多参考/编辑类模型最敏感）叠加用；定妆 ≥1024px·覆盖 3–6 角度。**多人同框/复杂站位可选增强（控制网双保险）**：站位易乱且后端支持 pose/depth 时，用骨架/深度图锁站位+景别（控制网锁"站位"、参考图锁"身份"·正交叠加），后端不暴露控制网则退回多参考后端/分别出图合成，不为上控制网而混后端（见 `n2d-image/SKILL.md` 多角色同框节 (c)）。
> **一致性梯子（出视频·治 image2video 脸漂）**：除首帧锁脸外，有原生角色一致能力的后端把定妆喂进去当**持久角色参考**——可灵 3.0 **Character ID** / Seedance 2.0 **Face Lock** / Veo 3.1 **reference controls**；**极端角度/大暗部/人物过小**是公认崩脸高危带，分镜阶段就规避（见 `n2d-script/references/分镜语法.md`「一致性高危镜」+ `角色一致性checklist §二`）。缺原生能力退回「首帧+首尾双帧+强 end_state 文字」。

## 公共能力与仓库级元工具

| 入口 | 职责 |
|---|---|
| `n2d-progress` | n2d **只读进度扫描**：识别 `创作区/制漫剧/` 作品根或仓库根，输出当前前沿/下一步；不回写 `_进度.md` |
| `novel-progress` / `comic-progress` / `song-progress` / `mv-progress` / `ad-progress` | 其它生产线的**只读进度扫描**：分别扫描 `创作区/写小说/`、`创作区/画漫画/`、`创作区/写歌/`、`创作区/制MV/`、`创作区/拍广告/`，输出当前前沿/下一步；不回写 `_进度.md` |
| `novel-update` / `song-update` / `mv-update` / `ad-update` | 其它生产线的 **skill 更新影响扫描**：按本线 `_进度.md` 当前阶段 + 本线 skill 内容快照，生成最小返工/重审/重评计划；只写 `生产数据/*_skill_update_plan.*` 和快照，不改正文、媒体或 `_进度.md` |
| `novel-settings` / `n2d-settings` / `comic-settings` / `song-settings` / `mv-settings` / `ad-settings` | 各线 **设置管理**：设置/重置/审计 `_设置.md` 选择点，并把项目设置同步到私有全局默认；只包本线 `_lib/settings.py`，不跨线复用实现 |
| `tools/shared-cleanup` | 通用**瘦身清理**（仓库级 dev 工具）：默认扫描/删除 `skills/` 下低风险生成垃圾，也可 `--repo` 检查整个仓库；自动删除仅限 `__pycache__`、pytest/mypy/ruff 缓存、`.DS_Store`、临时/备份文件等 allowlist 项，并输出 deleted bytes / saved space。placeholder skill / 大目录只报告不自动删 |
| `tools/independence-audit` | 系列独立性静态审计：阻断活动的 `skills/common` / `common/*.py` 路径引用和未允许的代码级跨线依赖 |
| `tools/run_all_checks.sh` | **仓库级回归闸门**：一处跑齐 `pytest skills/`+`pytest tools/`+`validate_skills`+`independence-audit`，收成单一退出码。CI（`.github/workflows/ci.yml`）每次 push/PR 跑；本机 pre-commit 快子集装一次 `git config core.hooksPath .githooks`（`--fast`/`--changed` 子集）。改契约/改 skill 后的"有没有弄坏别处"统一入口；重 conda 依赖测试优雅跳过故无模型权重也绿 |

> **候选项刷新随 n2d**：易变候选清单（生图模型/生图渠道〔旧称生图AI〕/生视频模型/配音后端）是带 `采集日期` 的候选快照，会过期。`skills/n2d/_lib/refresh.py status` 机检过期（读 `_lib/freshness.py:CANDIDATE_SOURCES`），核验后 `bump` 推日期 + 落 provenance。生图标准层与后端选择解耦：`skills/n2d/_lib/image_backend_standards.py` 定义统一出图能力标准，`skills/n2d/_lib/image_backend_adapter.py` 负责把所选模型/渠道映射为原生能力或自动弥补措施（参考组/脸嵌入/分层合成/overlay/整图重抽/QC）；每次付费出图前用 `record-refresh` 记录当天官方 API/CLI 核验，`image_preflight` 缺当天证据会 BLOCK。生视频同理：`skills/n2d/_lib/video_backend_adapter.py` 负责把 `生视频模型` + `生视频渠道` 归一为执行后端、帧消费计划、原生音画/口型/身份能力；每次付费出视频前对 route 中的 primary/fallback 用 `record-refresh` 记录当天官方 API/CLI 核验，`video` gate 缺当天证据会 BLOCK。**后端 smoke 证据**：刷新证明文档/API 新鲜，`backend_smoke.py probe|record|status` 证明本项目最近可运行；默认不阻断，放量时设 `_设置.md` `后端Smoke硬闸: 是` 或 `N2D_REQUIRE_BACKEND_SMOKE=1` 后，image/video gate 要求默认 7 天内 fresh smoke。**设置管理**：用户入口走 `n2d-settings`，底层单一实现仍是 `skills/n2d/_lib/settings.py`。

---

## 二、novel ——「写小说」文本工坊

novel 负责从点子/源书/派生需求生产可审计文本资产，产物落 `创作区/写小说/<项目>/`。它只承诺小说文本、审稿、评分、宣发和本地化产物，不生成其它生产线交接包。

| 类型 | Skill | 职责 |
|---|---|---|
| 调度 | `novel` | 路由 novel 请求、导入源书、读取 `_进度.md` 续跑 |
| 原创新书 | `novel-create` | 访谈 → 创作蓝图 → 设定圣经 → 章纲 → Demo gate → 逐章写作 → 导出 |
| 书名 | `novel-title` | 标题候选、平台适配、撞名风险初判 |
| 公版/源书 | `novel-fetch` | 获取公版或授权源书（如红楼梦、西游记、三国演义、金瓶梅等，默认可走 generic 加 --i-have-rights 兜底解析维基文库繁体回目）并落 manifest |
| 写作 primitives | `novel-craft` | contract、draft packets、arc packets、queue、progress、QA gate、export、AI 使用披露、compliance profile、统一修订计划、state_delta 草案等家族共享工具 |
| 生活观察 | `novel-observe` | 生活观察、采访纪要、人物行为、五感和场景烟火气素材库；产 `素材/观察札记.jsonl` + `素材/观察素材库.md` |
| 正向审美 | `novel-aesthetic` | 授权/自有/公版/项目 Demo 的高光样本拆解，沉淀“为什么有效”和可迁移规则；产 `设定/aesthetic_bank.json` |
| 扩写 | `novel-expand` | 把短文本扩成章节内细节，时间不推进 |
| 精简 | `novel-condense` | 长篇压缩成短版 |
| 续写 | `novel-continue` | 从已有末章继续往后写新章节 |
| 改写 | `novel-rewrite` | 改主线、换设定、重构派生作品 |
| 外传/视角 | `novel-spinoff` | 锁定原事件，换角色 POV 或写配角外传 |
| 质检 | `novel-review` | OOC、视角、设定、节奏、伏笔、文风漂移、逐章读者契约与弧段 gate、流程自审 |
| 专业编辑 | `novel-edit` | 发展性编辑、行文编辑、拷贝编辑、校样四层编辑计划；把 review/score/balance/feedback/scene cards 汇总成投稿前修订轮次 |
| 市场评分 | `novel-score` | 当前市场基准 + 证据质量 + 第一方投放战绩 + 真实读者反馈 + 模拟读者信号 + 参考分布百分位，输出 go/revise/kill 决策 |
| 专业资料包 | `novel-research` | 医疗/法律/刑侦/金融/军事/历史/宗教/海外/科技/职业文等专业场景的证据层：产 `资料/专业资料包_<主题>.md` + `research_sources.json`，支持 `research_required_domains` 必需领域，刷新审计产 `research_refresh_plan.md`，写章包自动引用，review/export 阻断缺失或过期高风险资料包 |
| 文风 | `novel-style` | 文风指纹、样本授权、漂移检查 |
| 动态百科 | `novel-wiki` | 人物状态、伏笔、关系温度、设定一致性维护 |
| 模拟读者 | `novel-simulate` | 虚拟试读、留存先验、弃书点和套路密度；默认 signal-only，QA gate 会提示只能低权重参考 |
| 真实反馈 | `novel-feedback` | 导入平台后台/测试读者 CSV·JSONL，聚合章节完读率、弃读率、评论情绪、掉点和 A/B/take 归因 |
| 节奏平衡 | `novel-balance` | 情节热力图、注水、断章、爽点节奏 |
| 宣发 | `novel-promote` | 爆点提取、短视频脚本底稿、视频 brief |
| 出海/本地化 | `novel-localize` | 术语锁（专名跨章 canonical 译名）+ 文化适配逐章翻译 + 未译残留/术语/覆盖/manifest 元数据机检；翻译后端选择点；源书权利/目标辖区/AI 标识三连合规 |
| 更新影响 | `novel-update` | novel skill 内容快照比对 + 最小文本返工/重审/重评计划；只写 `生产数据/novel_skill_update_plan.{json,md}` 和基线，不改正文/进度 |
| 设置管理 | `novel-settings` | 设置/重置/审计 `_设置.md` 选择点，并把项目设置同步到私有全局默认；底层只调用 `skills/novel/_lib/settings.py` |
| 进度·下一步（只读）| `novel-progress` | 扫 `创作区/写小说/<项目>/_进度.md` 章节矩阵 → 汇总完成度 + 创作前沿（下一步该跑哪个 novel skill）+ 可并行事项；只读不改文件 |
| 生产控制台（只读） | `novel-dashboard` | 聚合 pipeline plan、stale artifacts、语义任务、review/score blockers、revision tasks、batch 队列、release readiness，写 `生产数据/novel_dashboard.{json,md,html}`；不改正文/进度 |
| Agent 总控（上层） | `novel-supervisor` | novel 线 agent 编排层：消费 pipeline runner 计划、语义任务、revision plan 与 batch 状态，输出 next action；不绕过蓝图/设定/Demo 等人工审批 |
| 并发调度（横切）| `novel-batch` | 纯本地单机多 worker 原子锁排队，支持 claim、lease、renew、reclaim、retry、dead-letter 和幂等 plan，提供多章节审稿/评分/dashboard 刷新任务队列 |

**默认产品路径**：`novel-create` / 派生 skill 产文本 → 必要时 `novel-research` 补专业资料包、`novel-observe` 补生活观察素材、`novel-aesthetic` 建正向审美样本 → `novel-score` 给生产决策 → `novel-review` 回扫 → `novel-edit` 生成分层编辑计划与 line edit packet → `novel-craft` 用 `revision_planner.py` 合并修订任务并导出 txt/docx/outline → `release_manifest.py` 固化交付版本。运营层用 `novel-dashboard` 看全局状态，放量任务用 `novel-batch` 排队，长流程 agent 派发用 `novel-supervisor` 输出 next action；skill 升级后用 `novel-update` 做内容快照比对与最小文本返工计划。项目设置入口走 `novel-settings`，底层仍是本线 `skills/novel/_lib/settings.py`。`小说生成工作流` 选择点支持 `默认单步` / `三步迭代` / `边写边自检`；长篇/商业连载/漫剧源书默认三步迭代，除非项目显式写 `默认单步`。`边写边自检` 会把每章正文 + state_delta + `post_write.py` 自检闭环写进任务包和 flow 下一步提示，写后可先用 `propose_state_delta.py` 生成 delta 草案，`post_write.py` 先过读者契约 sentry，再过账本/百科/逻辑/力量体系自检；每 3-5 章可用 `arc_packets.py` + `arc_gate.py` 做长篇弧段压力测试；发布/出海/KDP/中国公开发布等目标用 `compliance_profile.py` 生成平台/辖区合规清单，QA gate 统一读取。

> **力量体系自检（穿越/系统流/修仙·等级·成长值·战力严丝合缝·实时监控）**：网文力量体系是命门——等级跳变、战力前后矛盾、属性突变、升级节奏崩（数值膨胀/越级无代价）是高发穿帮，人脑记不住几百章。落地：① `novel-create` 立项按题材自动脚手架 `设定/power_system_registry.json`（研究落地的等级体系模板 + 系统面板字段[属性≤7] + 升级节奏[每章小奖/每5章中奖/每20章大奖] + 逐章成长 progression），见 `novel-craft/references/力量体系设计.md`；② 引擎 `novel-wiki/scripts/power_system.py` 确定性机检：等级/境界/战力**只增不减**（退档=阻断·除非标跌境/废修豁免）、未知境界=阻断、越级过快/面板属性超7/系统流久无升级桥段=建议；③ **实时监控**：`novel/scripts/post_write.py` 每章写后自动跑（受 `力量体系自检` 选择点控制），`context_loader` 写章前把"主角现状(Lv/境界/属性/战力)"喂给上下文让 AI 按现状推进；④ 审稿 `novel-review/consistency_audit.py` 含 `power_system` 子runner。真值/默认在 `novel/_lib/power_system_defs.py`。

---

## 三、song ——「写歌 / 作曲 / 翻唱」

song 负责从点子、歌词草稿或半成品音频生产可审计歌曲资产，产物落 `创作区/写歌/<项目>/`。它不依赖 mv；交给 MV 时只输出成品歌和歌词文件。

| 类型 | Skill | 职责 |
|---|---|---|
| 调度 | `song` | 路由写歌请求、读取 `_进度.md` 续跑 |
| 进度·下一步（只读） | `song-progress` | 扫 `创作区/写歌/<项目>/_进度.md` 阶段表 → 汇总完成度 + 当前前沿 + 后续待办；只读不改文件 |
| 更新影响（只写计划） | `song-update` | 本线 skill 内容快照比对 + 最小歌词/作曲/换声/质检返工计划；只写计划/基线，不改歌词、音频或 `_进度.md` |
| 设置管理 | `song-settings` | 设置/重置/审计 `_设置.md` 选择点，并把项目设置同步到私有全局默认；底层只调用 `skills/song/_lib/settings.py` |
| 合约/骨架 | `song-craft` | 项目骨架、契约、进度、AI 使用披露 |
| 作词 | `song-lyrics` | 创作蓝图、歌词结构、押韵与可唱性 |
| 歌词评分 | `song-score` | 结构、押韵、hook、可唱性前置体检 |
| 作曲/演唱 | `song-compose` | 生成任务包、多版登记、挑版、定稿 |
| 翻唱/换声 | `song-cover` | RVC / SVC 换声，含授权闸门 |
| 质检 | `song-review` | 歌词、音频、合规和流程自审 |

**允许的跨线交接**：成品 `歌/song.*` 与 `词/lyrics.md` 可作为 mv 输入；song 不 import mv 实现。

---

## 四、mv ——「歌曲 → 音乐视频」

mv 负责把已有歌曲或后配歌曲企划做成音乐视频，产物落 `创作区/制MV/<项目>/`。它的视觉、卡点、字幕、合成脚本自包含；输入歌只按文件接入。

| 类型 | Skill | 职责 |
|---|---|---|
| 调度 | `mv` | 路由 MV 请求、处理先传音乐/后配歌曲两种时序 |
| 进度·下一步（只读） | `mv-progress` | 扫 `创作区/制MV/<项目>/_进度.md` 阶段表 → 汇总完成度 + 当前前沿 + 后续待办；只读不改文件 |
| 更新影响（只写计划） | `mv-update` | 本线 skill 内容快照比对 + 最小卡点/蓝图/分镜/出图/出视频/合成返工计划；只写计划/基线，不改素材、视频或 `_进度.md` |
| 设置管理 | `mv-settings` | 设置/重置/审计 `_设置.md` 选择点，并把项目设置同步到私有全局默认；底层只调用 `skills/mv/_lib/settings.py` |
| 合约/骨架 | `mv-craft` | 项目骨架、契约、进度、gate、AI 使用披露 |
| 节拍 | `mv-beat` | BPM、beatgrid、downbeat、能量段落 |
| 视觉蓝图 | `mv-script` | 听歌识影、角色/场景/叙事结构 |
| 分镜规划 | `mv-plan` | clip/timeline 规划与 prompt 任务包 |
| 出图 | `mv-image` | 单曲共享定妆、Clip 首/尾帧；每张 PNG 落档后跑 mv 自己的 `image_qc`，批后再收尾复核 |
| 出视频 | `mv-video` | 生成/维护视频任务 manifest 与挑版 |
| 字幕 | `mv-lyric-sync` | 歌词强制对齐、LRC/ASS/Karaoke |
| 合成 | `mv-compose` | 歌轨、clips、卡拉 OK 字幕合成成片 |
| 质检/评分 | `mv-review` / `mv-score` | 卡点、成片、视觉一致性、分镜表现力 |

**允许的跨线交接**：song 或用户提供的成品歌/歌词文件可进入 mv；mv 不 import song 实现，深度审歌只提示回 `song-review`。

---

## 五、comic ——「故事 → 漫画」

comic 负责把故事源、点子或已有脚本做成条漫/页漫，产物落 `创作区/画漫画/<项目>/`。它以 `panel/格` 为最小单位，不要求完整小说源本；原创漫画可以从故事蓝图和分话大纲开始。

| 类型 | Skill | 职责 |
|---|---|---|
| 调度 | `comic` | 路由画漫画请求、初始化项目、读取 `_进度.md` 并分诊到阶段 skill |
| 进度·下一步（只读） | `comic-progress` | 扫 `创作区/画漫画/<项目>/_进度.md` 阶段表 → 汇总每话前沿；只读不改文件；出图后会检查共享参考、长线多视图和风格一致性报告是否阻断合成 |
| 设置管理 | `comic-settings` | 设置/重置/审计 `_设置.md` 选择点，并把项目设置同步到私有全局默认；底层只调用 `skills/comic/_lib/settings.py` |
| 流程批跑 | `comic-batch` | 读取当前前沿，批量推进一话；出图前后自动跑 comic gate；出图阶段可按确认预算多抽、重抽指定格并归档候选 |
| 漫画脚本 | `comic-script` | 源本/点子/脚本 → 故事圣经、分话大纲、`panel_script.json` |
| 页面排版 | `comic-layout` | `panel_script.json` → 页漫/条漫 `layout.json`，含阅读顺序、格子坐标、气泡占位 |
| 一致性资产 | `comic-identity` | 共享定妆、专门定妆多视图、定型图角色 DNA、年龄/形态继承、`identity_registry.json`、引用绑定、缺失引用检查和受影响格重抽计划 |
| 出图 | `comic-image` | 逐格 prompt/job 包、后端参考图预算适配、真实参考图入参、风格锚/角色 DNA 契约注入、面板图登记；每格落档写 comic 自己的 `panel_qc`，`block` 不算 ready；不绑定具体后端 |
| 嵌字/导出 | `comic-compose` | `lettering.json`、文字语言选择、按 layout 渲染页面图、长图分段、WebP/PNG 尺寸 fallback、`export_manifest.json` 与进度回写 |
| 质检/自审 | `comic-review` | 阶段 gate、阅读顺序、文字遮挡、角色一致性并排复核与 face/hair/outfit 启发式、风格一致性/场景族群基线/调色离群/拼贴或外框嫌疑、高一致性风格锚/形态继承硬闸、导出规格、权利状态与返修清单 |

**默认产品路径**：`comic` 立项 → `comic-script` 分话大纲/分格 → `comic-layout` 排版 → `comic-identity` 共享定妆/一致性引用 → `comic-image` 面板图 → `comic-review` 风格一致性复核 → `comic-compose` 嵌字/长图导出 → `comic-review` 发布审查。需要从当前前沿批量推进或预算充足多抽时用 `comic-batch` 编排阶段脚本。默认按长线连载口径补专门定妆多视图；文字默认后期中文嵌字，可在 `文字语言` 选择英文或中英双语，不让图像模型直接烘焙正文；人物/资产漂移先回 `comic-identity`，风格/调色/拼贴/外框离群先回 `comic-image`，不要直接合成。

---

## 六、ad ——「Brief → 广告片」

ad 负责把客户 brief 或产品需求做成广告主片与多版本交付件，产物落 `创作区/拍广告/<项目>/`。它不拆集，不复用 n2d/mv 的实现。

| 类型 | Skill | 职责 |
|---|---|---|
| 调度 | `ad` | 路由广告请求、初始化项目与 brief |
| 进度·下一步（只读） | `ad-progress` | 扫 `创作区/拍广告/<项目>/_进度.md` 阶段表和交付版本矩阵 → 汇总完成度 + brief 缺口 + 当前前沿；只读不改文件 |
| 更新影响（只写计划） | `ad-update` | 本线 skill 内容快照比对 + 最小 brief/创意/脚本/配音/出图/出视频/交付返工计划；只写计划/基线，不改 brief、媒体或 `_进度.md` |
| 设置管理 | `ad-settings` | 设置/重置/审计 `_设置.md` 选择点，并把项目设置同步到私有全局默认；底层只调用 `skills/ad/_lib/settings.py` |
| 合约/骨架 | `ad-craft` | `_进度.md`、brief contract、gate、AI 使用披露 |
| 创意 | `ad-concept` | brief 访谈、big idea、创意脚本 |
| 脚本/分镜 | `ad-script` | 广告脚本、VO、时间轴、广告法机检、配音后分镜 |
| 配音 | `ad-voice` | VO 配音与时长清单 |
| 出图 | `ad-image` | 产品/角色/场景三层定妆与逐镜图；每张关键图落档后跑 ad 自己的 `product_qc`/广告落档自检 |
| 出视频 | `ad-video` | 广告图生视频、模型路由、视觉契约继承 |
| 合成/交付 | `ad-compose` | 主片、cutdown、多比例、包装、交付矩阵 |
| 评分（投放前·横切） | `ad-score` | 出图烧积分前 pre-spend 评分闸门：钩子前3秒/卖点/CTA/品牌露出/广告法/时长贴合，确定性 prescore + LLM 语义分 → 三档 go/revise/reject + 低分维度回流 ad-concept/ad-script/ad-image |
| 质检/自审 | `ad-review` | 模式①投放前 M0 硬项+交付件人工复核；模式②流程自审（钩子/合规/成本三轴拉市场基准对照 ad-* 找差距） |

**允许的跨线交接**：无默认必需交接。ad 可借鉴其他线工艺概念，但脚本和契约必须留在 ad 家族内。

---

> 本仓库的长期维护原则：**每条线自包含、可单独分发，优先于跨线复用代码**。如需交接，只交文件、JSONL 或成品媒体；不要让一个系列 import 另一个系列的脚本。
