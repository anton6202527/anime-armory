---
name: n2d-review
description: 漫剧质检 + 流程自审（novel2drama 的 QA 环节，不生产内容只审）。双模——模式①「作品质检」：对已产出的某集/整部漫剧做穿帮体检（角色崩脸/场景漂移/构图景别/字幕错位/音画不同步/双人声/节奏留存/口型/合规水印），机检+人判，出严重度分级·定位到镜头的报告。模式②「流程自审」：联网拉当前市场基准，对照 n2d 各 skill + Q&A，产出"差距清单 + 该改哪个 skill 哪段"的优化建议，让整条流水线可重复自我体检。Use when asked to 漫剧质检, 审片, 查崩脸, 查穿帮, 字幕对账, 成片体检, 流程自审, 自我优化, n2d 还能优化啥, n2d-review. Triggers 漫剧质检, 审片, 崩脸, 穿帮, 字幕错位, 音画同步, 成片体检, 验收, 流程自审, 流程优化, 自我优化, n2d-review, QA.
---

# n2d-review — 漫剧质检 + 流程自审

不生产内容，只**审**。是 novel2drama 家族的 QA 环节，与 `novel-review`（审小说）同构。两个模式：

- **模式①「作品质检」**——审**某集/整部漫剧的产物**：扫穿帮 → 定位（镜头 + 时间码）→ 定级 → 给修法 → 出报告。出成片前 / 各阶段闸门跑。
- **模式②「流程自审」**——审**流水线本身**：联网拉市场基准，对照 n2d 各 skill + 累积 Q&A，产出"差距清单 + 建议改哪个 skill 哪段"。让"整套流程不断自我优化"成为一条可复跑的命令，而非靠人想起来。

> 行业把 **一致性 · 效率 · 可控性** 定为漫剧三大验收维（《AI漫剧工业化白皮书》）；商用"AI审片系统"自动识别约 12 类问题（角色断层/崩脸/构图错/糊/字幕错…）。本 skill 把这套体检在 n2d 产线里落成可跑流程。

---

# 模式①：作品质检

## 机检 / 人判分工（照搬 novel-review 的成熟做法）

- **机检（确定性，先跑）**：`scripts/mechanical_check.py <作品根> 第N集` —— 秒级出确定性问题：字幕↔配音文本/时间码对账、中英字幕错位、占位未精修、单行溢出、配音占位音色未替换、产物完整性对账、钩子/集尾留存信号缺失、**脏标点 lint（中英）**（中文 `||` 气口残留 `。，`/`，，`/行首逗号 + 英文 标点前空格/多空格/叠逗号/行首逗号·省略号 `...` 豁免——即便字幕与配音"同样脏"对账能过也单独抓；源头 `voice_text.clean_text` + `finalize._clean_punct/_clean_en` 已修，旧集 stale 数据靠它兜）。**审查第1步即自动跑，无需人记得扫。**
  ```bash
  python3 <skill>/scripts/mechanical_check.py <作品根> 第N集          # 人读
  python3 <skill>/scripts/mechanical_check.py <作品根> 第N集 --json   # 喂回 LLM 汇总
  ```
- **阶段 gate（确定性，生产前跑）**：`scripts/gate.py <作品根> 第N集 --stage image|video|compose|review` —— 把高风险流程规则脚本化：`合规/compliance_manifest.json`、`storyboard.json` continuity、尾帧、prompt 检查段、共享定妆、资产身份注册层、占位配音、clip 原生音轨/原生音画 opt-in/时长、水印等。合规包由 `n2d-compliance` 初始化和预检；`image/video/compose/review` 都会阻断缺合规包，或源文本/改编权、角色肖像授权、声音克隆授权、AI 标识、可见水印/元数据/C2PA 或平台隐式标识、平台审核、出海本地化缺口。`image` 阶段会严格阻断出图 prompt 漏项：逐镜必须有参考图、双语正向 prompt、负向 prompt、导演八维、提交前检查、生成后自检、重抽预算；含角色镜头还必须显式带锚点句、脸/妆造漂移自检、服装/配色约束。人物共享定妆 prompt 会阻断缺**标准三视图**（正面主参考 + 侧面 + 背面 + `定妆_<角色>_三视图.png` 拼版），不再接受只出正脸/半身或背面按需省略。`image/video/compose/review` 都会阻断缺 `出图/共享/identity_registry.json` 或角色/形态缺 `reference_group`、`identity_adapters`、`angle_policy`、`drift_forbidden`；`video/compose/review` 还会阻断缺 `生产数据/identity_adapter_matrix.json`，保证 registry 已展开成 Face Lock / Character ID / LoRA / reference group 的可执行 binding。视频及之后阶段还会检查核心参考图路径真实存在，保证 Character ID / Face Lock / LoRA 状态可追踪。registry 还会阻断未知 `status`、后端能力不匹配的 `mode`、`registered/ready` 空句柄、LoRA ready 缺 `base_model/model_path/trigger/validation_report/model_hash`、验证报告非 `pass`、模型 hash 不一致，或 `dataset_has_warnings` 被人工放行但缺 `manual_review.notes`，防止 Face Lock / Character ID / LoRA 假登记。`image/video` 都会阻断缺 `storyboard.json.style_contract` 或总览缺**本集基础视觉风格契约**（风格名/视觉基调/镜头与构图/光色策略/运动边界/风格禁忌），防止只靠 cinematic/realistic/anime 泛词。旧 `cinematic_contract` 兼容旧项目。复杂镜头 gate 也会阻断：打斗、追逐、对话反打、法术爆发、飞行、亲密互动、拥抱/拉扯、多人同框、群像站位必须在 `storyboard.json` 写 `template` + `template_contract`，按 `n2d-script/references/专项镜头模板库.md` 的模板字段继承到下游。**复杂物理交互 gate 也会阻断**：打斗命中、亲密接触、拥抱/抓腕/拉扯等 `physical_interaction/contact_motion` 镜头必须在 `video_model_routes.json.motion_control` 声明 `manifest_path`，且 `motion_control_manifest.json` 必须是 `ready` 或 `degrade_only`。`ready` 的 `control_inputs.*.path/glob` 必须匹配本地文件；远端 `uri` 必须是 `https/s3/gs` 且带 `verified_at` + `sha256/checksum/etag`，裸 URI 或 `file://` 不放行。`video` 阶段会严格阻断视频 prompt 漏项：`00_总览.md` 必须有**本集导演一致性契约**（主色调/镜头语法/轴线/剧情状态锁/场景状态），每个 Clip 必须有**导演调度五字段**（导演意图/起幅/落幅/场面调度/表演节拍）、原生音画策略、衔接设计、continuity、中英视频 prompt、提交前检查、生成后自检。共享定妆 prompt 同查双语、负向、定妆组、锚点和落档自检。**生图 AI 一致性也在 image gate 阻断**：同一项目/同一集必须统一到一个官方/已登录生图后端（默认 Codex，可选 Dreamina/即梦官方 CLI、Seedream/可灵主体库/Nano Banana/Sora Cameo）；若 `_设置.md` 或 prompt 出现多后端混用，或写 `同视频AI` 含糊口径、第三方逆向/web 自动化出图口径，必须先明确提示用户"后端不一致会导致角色/画风漂移，本次不会继续生图"，统一到同一个官方后端后再跑。`block` 退出码 1，先修再进入该阶段。`--json` 输出保留 `sev/dim/loc/msg`，并追加 `return_to_stage` / `rerun_scope` / `affected_artifacts`，用于最小范围返工。
- **QA 入账铁律（P0）**：每次跑 gate 或作品质检，都要把 QA 结果写入 `n2d-dashboard`。确定性 gate 用 `python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image|video|compose|review`，它会调用 `gate.py --json` 并把 `block/warn/info`、回流 stage、重跑范围写进 `生产数据/`。人判报告里的新增阻断也用 `record --stage review --event qa --qa-sev block|warn|info` 补录；否则仪表盘无法统计 QA 阻断率。
- **自动审片评分（P2）**：作品质检完成后跑 `python3 skills/n2d-score/scripts/score.py <作品根> 第N集 --run-checks --threshold 85`，把角色一致性、服装一致性、场景一致性、字幕正确性、音画同步、节奏密度、风格一致性汇总成机器分。`--run-checks` 还会缓存 `score_inputs/第N集_visual.json`，接入图像相似度、字幕 OCR、成片/配音/SRT/storyboard 时长对账、口型风险/检测报告、成片节奏密度，让机器分更贴近观感。若用户要求自动返工或批量回流，加 `--enqueue-low`，低分维度会转成 `n2d-batch` 的 rerun 队列。评分后需要人审时，跑 `python3 skills/n2d-review-ui/scripts/review_ui.py <作品根> 第N集 --write --markdown`，把机器分、QA flag、首尾帧、clip、接缝和定妆参考放进可视化画布。
- **人判（LLM 判断题）**：机检覆盖不了的语义维度——崩脸/场景漂移、**clip 接缝跳切/闪烁**、构图景别（对 `n2d-script/references/分镜语法.md`）、节奏体感（对 `novel2drama/references/导演节奏.md`）、口型、原生音频双人声、合规水印。逐维见 `references/checklist.md`。
  - **崩脸用图判**：把该集 `出图/第N集/图片/镜头*.png` 与 `出图/共享/图片/定妆_<角色>.png` **并排读图比对**（脸型/发型/服色/配饰/锚点特征），漂了就标。装了 `insightface` 时跑 `scripts/face_consistency.py <作品根> 第N集` 给余弦相似度分——**不写死阈值**，而是**自标定 flag-band**：用本作定妆组内部互相余弦（同角色 正脸↔侧脸/半身 本就该高度相似）当"同一人下限"地板，每镜低于 地板−margin 标 🔴、地板带标 🟡（写死 0.45 对风格化脸要么误杀要么放过；业界 ArcFace 同人≈0.5–0.68 且因画风而异）。缺库则此项由人判兜，机检会显式标"跳过"。
  - **服装/配色漂移用机检（脸之外的漂）**：脸锁住不等于服装锁住——2026 公认"夹克色第 4 镜就漂"。装 Pillow 时跑 `scripts/outfit_consistency.py <作品根> 第N集`：对人物镜取**加权色相直方图**（饱和度×明度加权，压低灰暗背景），与该角色定妆组（优先半身）比，同样**自标定 flag-band**（定妆组内部直方图余弦设地板）。缺库由人判并排比服色/发型。
  - **片内时序用机检（单 clip 内身份漂移 + flicker）**：n2d-review 只查首帧 + 接缝，漏查 clip 内部"几秒后脸渐变/发际线闪"。装 ffmpeg(+insightface) 时跑 `scripts/temporal_consistency.py <作品根> 第N集`：每条 clip 抽 K 帧，量 ① 相邻帧人脸余弦最小值（片内身份漂移）② 相邻帧亮度绝对差均值=flicker/TCI，超阈标 🔴/🟡。对标行业 scene-stability 记分卡；缺库由人判抽帧看。
  - **定妆主参考质量门（N3·锚点不能脏）**：锚点一脏下游每镜继承错。装 insightface+cv2 跑 `scripts/face_consistency.py <作品根> 第N集 --audit-anchor`：每个 `定妆_<角色>.png` 主参考须**恰好 1 张清晰、够大的正脸**（0 张/多张=🔴，脸太小=🟡）——出图共享先行闸门前就拦，别让脏锚点污染全集。
  - **糊/低质无参考质检（N4）**：装 Pillow 跑 `scripts/quality_check.py <作品根> 第N集`：用 **Laplacian 方差**测清晰度，**自标定本集中位数**（绝对阈值因画风漂），显著低于中位数=相对糊（关键镜更严），标 🔴/🟡。与一致性正交，同属「崩脸/糊」族。
  - **风格漂移用机检（S1·补 style_contract 落地后零机检的盲区）**：装 Pillow 跑 `scripts/style_consistency.py <作品根> 第N集`：每镜取风格指纹（饱和直方图+明度直方图+边缘密度），**自标定 median-中心 flag-band**——内聚度显著低于本集中位=某镜突然偏离所选风格（突然照片感/插画/高饱和）。配合 `style_contract` 与逐镜负向风格禁忌（gate 已强制）形成"契约定风格→负向堵→S1 兜底机检"闭环。缺库人判读「本集基础视觉风格契约」并排看。
  - **接缝跳切先机检再人判（N2接力·把"逐接缝并排读图"降成初筛）**：装 Pillow 跑 `scripts/temporal_consistency.py <作品根> 第N集 --seam`：尾帧 `镜头N_end.png` vs 下一首帧 dHash 距，距大=尾帧没对上下一首帧→出视频必跳切（尾帧接力本应近乎同构图）。距小不代表姿态完美仍需人判，但距大几乎必跳——先机检筛出可疑接缝再逐个人判。
  - **跨集人物一致性（⑦·身份闭环报表）**：优先跑 `python3 skills/n2d-identity/scripts/identity.py <作品根> --episodes 1-10 --write`，生成 `identity_adapter_matrix` + `identity_drift_report`；它把 registry 的 Face Lock / Character ID / LoRA / reference group binding 与逐集 🔴/🟡 漂移合并。旧命令 `scripts/face_consistency.py <作品根> 第N集 --cross-ep` 仍可单独看脸相似度，但不含 adapter 闭环。
  - **接缝跳切用图判（逐接缝过）**：沿接力链逐个查相邻 Clip 的接缝——取 Clip K 末帧 vs Clip K+1 首帧**并排读图**，对照 `故事板.md` 该接缝契约：① 契约说"姿态连续硬切/有尾帧"但两帧人物姿态/站位/视线/光线明显对不上 → 跳切/闪烁，标问题；② 契约 `需要尾帧?=是` 却没出 `镜头N_end.png`（n2d-image 漏做）→ 标接力断链；③ 服装/发型/道具在接缝处突变 → 接缝崩。轻微姿态差走容错铁律放行。修法：回 n2d-image 补尾帧 / 回 n2d-video 用首尾双帧重出该 Clip。
  - **导演一致性契约用人判（整段读）**：审视频 prompt 或成片时先读 `出视频/第N集/prompt/00_总览.md` 的「本集导演一致性契约」，再逐 Clip 判断是否违反主色调、镜头语法、轴线、剧情状态锁、场景状态。典型问题：爽点特效提前泄露、同场景灯位/雨雾跳变、人物左右站位反复跳轴、铺垫段乱甩镜、落幅接不上下一镜。修法：回 n2d-video 改 prompt；若首尾状态源头不对，回 n2d-script 改故事板接力契约，必要时回 n2d-image 补尾帧。
  - **基础视觉风格契约用人判（整段读）**：审图包、视频 prompt 或成片时先读「本集基础视觉风格契约」（旧项目读「本集真实电影感契约」），再判断画面是否稳定遵守所选风格：角色比例/材质或线条是否一致、光色是否守策略、运动是否在边界内、是否触犯该风格的禁忌。修法：源头回 n2d-script 改 `style_contract`，再让 n2d-image/video 继承；只在单镜末尾补某个风格词视为无效修复。

## 工作流（模式①）

1. **定位 + 确认范围**：作品根 = `制漫剧/<剧名>/`。问审一集还是整部、审到哪个阶段（出图后 / 成片后）。读 `_进度.md` 知各集进度。
2. **跑机检 + 一致性编排 + 身份闭环 + 合规包 + QA 入账** → 确定性问题清单（按集）：先 `scripts/mechanical_check.py`（字幕/对账/占位），再 **`scripts/consistency_audit.py <作品根> 第N集` 一键串跑全部一致性检测器**（锚点门 N3 · 脸 G1 · 服装配色 N1 · 片内时序 N2 · 场景 O2 · 糊 N4 · **风格 S1** · **接缝接力**），再跑 `python3 skills/n2d-identity/scripts/identity.py <作品根> --write` 生成 adapter matrix + 跨集漂移报表；缺 `合规/compliance_manifest.json` 时先跑 `python3 skills/n2d-compliance/scripts/compliance.py <作品根> 第N集 --init` 并人工补齐。阶段 gate 结果必须同步跑 `python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage review` 或对应生产 stage 入账。别只跑单个检测器漏掉其余。
3. **生成机器分**：跑 `python3 skills/n2d-score/scripts/score.py <作品根> 第N集 --run-checks --threshold 85`，把机检、dashboard 阻断、一致性结果和 visual checks 落成 `生产数据/score_第N集.json/md`。若要自动回流，追加 `--enqueue-low`，让低分维度进入 `n2d-batch` 队列。
4. **生成人审画布**：跑 `python3 skills/n2d-review-ui/scripts/review_ui.py <作品根> 第N集 --write --markdown`，输出 `生产数据/review_ui_第N集.html/json`。先看全局机器分和 QA flag，再按画布逐个核首帧、尾帧、clip、接缝、定妆参考和缺素材；工业级批量审片不得只依赖文本报告。
5. **人判**：集多时**每集独立审查**（省主上下文），优先打开 `review_ui_第N集.html` 做视觉核查，再对照 `references/checklist.md` 逐维，**只记真问题**，每条带证据（引文 / 图路径 / 时间码）。
6. **汇总报告 + 修复回流** → 写 `制漫剧/<剧名>/_质检_第N集.md`（整部则 `_质检_全片.md`）：按严重度排序，每条 = 位置（镜头N·@时间码 / 文件）+ 维度 + 问题 + **修法** + 证据。附"健康度概览"表（各维度 通过/问题数 + 一致性度量分如有）。漫剧的修法**回源头改、重跑回流**，不在成片上剪；报告里每条修法都指明**回哪个 stage 重跑**（如"崩脸→回 n2d-image 重出该镜""字幕错位→重跑 finalize_storyboard""节奏塌→回 n2d-script 阶段2 重切镜头时长曲线"）。
   - 批量返工时，把 finding 的 `return_to_stage` / `affected_artifacts` / 具体 Clip 转成 `n2d-batch` 定向任务：`python3 skills/n2d-batch/scripts/queue.py plan <作品根> --episodes 第N集 --rerun-from image|video|compose --affected-shot Clip_03 --affected-artifact <路径> --scope "<问题摘要>"`。只重跑受影响镜头，不整集重来。

## 严重度（定级 + 容错铁律）

| 级别 | 含 | 处置 |
|---|---|---|
| 🔴 阻断级 | 崩脸/角色断层、字幕错位或占位未精修、配音占位未替换、双人声打架、AI 标识水印缺失、合规未授权换脸/克隆 | **必改**，回源头重跑 |
| 🟡 建议级 | 场景轻漂、clip 接缝跳切/闪烁、构图/景别违 `分镜语法`、节奏塌/钩子弱/集尾不够、字幕溢出、卡点没对上爽点时间戳 | 建议改 |
| 🟢 润色级 | 个别动态细节弱、留白差一拍、音效偏好 | 可改可不改 |

> **生图 AI 不一致单独提级**：生产前发现设置/prompt 口径混用多个官方/已登录后端，或出现 `同视频AI` 含糊口径、第三方逆向/web 自动化出图口径，按 🔴 阻断处理；成片后才发现，按画面结果定级，但报告必须写清"疑似因生图后端混用造成一致性税"，修法是回 `n2d-image` 统一到同一个官方后端并重出受影响定妆/分镜。

**容错铁律**：只报"真问题"。轻微主观偏好不入报告（等同 n2d 出图的「筛选宽容铁律」、novel-review 的容错铁律）——否则噪声淹没硬伤。

---

# 模式②：流程自审（让产线自我优化）

把"我这次手动做的 n2d 复盘"固化成可复跑流程。**节律**：用户主动要 / 每隔一批集 / 接了新视频·图·配音模型时跑一次。详细步骤见 `references/self_audit.md`，要点：

1. **拉基准**：联网搜当前（带年月）AI 漫剧/短剧主流做法，分三轴取证——**一致性**（定妆/参考/相似度 KPI、多参考/多视图/LoRA、同一生图后端贯穿）、**效率**（成本/周期/批量）、**可控性**（口型/音画/节奏工具）+ 各 stage 模型演进（图/视频/配音 SOTA）。
2. **对照**：逐 stage 把基准 vs `n2d-*/SKILL.md` + `novel2drama/Q&A.md` 比，找**真差距**（已做的别重复立项）。
3. **差距清单**：每条 = 差距 + 证据（带来源链接·日期）+ 落到哪个 skill 哪段 + 优先级（must/optional）+ 是否可脚本化。
4. **起草**：高价值项直接起草 `Q&A` 新条目 + 建议 edit；**改任何 skill 必同步 `skills/README.md` 索引**（仓库硬约定）。
5. **人确认后再写**：模式②**默认 report-only**，只产建议报告 + 可选 diff 草案，不自动改 skill / Q&A / 模型矩阵（改产线是高影响动作）。用户明确要求“落地/刷新矩阵/改 skill”后，才进入 `refresh-matrix` 或编辑模式。**报告是一次性的——只讲给用户、不在 skill 目录留存 `_流程自审_*.md` 这类存档**（已 gitignore）。**每次自审/重审都从头按本流程重跑**（拉基准→对照→差距），**绝不读旧报告当捷径**——市场会变，旧结论可能已过时或已落地。

> **防过期铁律**：市场建议带"采集日期 + 来源链接"，旧建议可能已被采纳或过时——写进来前先核对当前 skill 是否已有（本 skill 自己也按此自查）。

---

## 详细参考
- 作品质检两层维度全清单（看什么 + 定级 + 怎么判）：`references/checklist.md`
- 流程自审操作手册（拉基准 / 对照 / 起草）：`references/self_audit.md`
- 各轴 SOTA vs n2d 默认 vs 升级触发（防过期快照；report-only 只给刷新建议，用户确认后再改）：`novel2drama/references/模型矩阵.md`
- 定妆变更影响扫描（崩脸/换装重抽后，列出引用该资产的下游镜头一并重出）：`n2d-image/scripts/asset_impact.py`
- 正向标准（镜头空间 / 时间留存）：`n2d-script/references/分镜语法.md` + `novel2drama/references/导演节奏.md`
- 一致性全链：`n2d-image/references/角色一致性checklist.md`
- 角色身份闭环 + 跨集漂移报表：`n2d-identity/SKILL.md`
- 翻车修正沉淀：`novel2drama/Q&A.md`

## 常见错误

| 错误 | 纠正 |
|---|---|
| 只跑机检不做人判 | 机检只覆盖确定性问题；崩脸/构图/节奏体感要 LLM 判（含并排读图比对） |
| 只人判不跑机检 | 字幕错位/占位/对账这类秒查，漏跑等于白审 |
| 鸡蛋里挑骨头堆润色项 | 违容错铁律，硬伤被淹没 |
| 报问题不定位不给修法 | 必须 镜头+时间码定位 + 指明回哪个 stage 重跑 |
| 在成片 MP4 上直接剪 | 回源头改重跑回流（同 Q27）；成片是产物不是源 |
| 模式②直接改 skill | 默认只出建议报告，人确认后改；改 skill 必同步 README 索引 |
| 模式②抄一堆已实现的"建议" | 先核对当前 skill 是否已有；建议带来源日期防过期 |
| 审完没有机器分 | 跑 `n2d-score`，让七维评分、visual checks 和回流 stage 进入 `生产数据/score_第N集.json` |
| 批量审片只看文本报告 | 跑 `n2d-review-ui` 生成 `review_ui_第N集.html/json`，用画布同时看首尾帧、clip、接缝、定妆参考、QA flag 和机器分 |
| 合规等成片后补救 | 先跑 `n2d-compliance` 建 `合规/compliance_manifest.json`，gate 会在 image/video/compose/review 前置阻断 |
