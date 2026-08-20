---
name: mv-review
description: 制MV 质检 + 流程自审（mv 生产线的 QA 环节，不生产内容只审）。双模——模式①「作品质检」：对一支 MV 的产物做体检（规划：clip_plan/timeline/jobs 对账；一致性：identity/asset/reference 注册、图生视频继承合约、主角崩脸/场景漂移/画风跳变；卡点节奏：clip 时长对齐 beatgrid downbeats·不等长·副歌密 verse 疏·爽点对鼓点·clip 总时长≈歌长；视频QC：selected clip 时长/画幅/音轨；卡拉OK字幕：占位未精修/时间越界/重叠/行数对账/对齐报告；音画合成：成片时长≈歌长·画幅符 _meta.aspect·有音轨；AI 视觉使用披露；运镜服务节奏），机检+人判，出严重度分级·定位到 Clip/段落/时间码的报告。模式②「流程自审」：联网拉当前 AI MV/音乐视频市场基准，对照 mv 各 skill + references，产出"差距清单 + 该改哪个 skill 哪段"的优化建议。Use when asked to MV质检, 审MV, 查崩脸, 卡点对账, 卡拉OK字幕检查, MV成片体检, 验收MV, 流程自审, mv 还能优化啥, mv-review. Triggers MV质检, 审MV, MV审片, 崩脸, 卡点对账, 卡点检查, 卡拉OK检查, 字幕越界, MV成片体检, MV验收, 流程自审, 流程优化, 自我优化, mv-review, QA.
---

# mv-review — 制MV 质检 + 流程自审

不生产内容，只**审**。是 `mv`（制MV 生产线）家族的 QA 环节。两个模式：

- **模式①「作品质检」**——审**一支 MV 的产物**（`创作区/制MV/<曲名>/`）：先汇总单曲身份/参考/出图/视频/字幕一致性 findings，再扫问题 → 定位（Clip / 段落 / 时间码）→ 定级 → 给修法 → 出报告。出成片前 / 各阶段闸门跑。
- **模式②「流程自审」**——审**制MV 流水线本身**：联网拉市场基准，对照 `mv-*` 各 skill + references，产出"差距清单 + 建议改哪个 skill 哪段"。让"整套流程不断自我优化"成为一条可复跑命令。

> MV 三大验收维：**视觉一致性 · 卡点节奏（MV 的命）· 音画合成与合规**。clip 时长必须踩 beatgrid，不能等长。正向标尺：卡点 = `mv-beat/SKILL.md` 卡点原则；运镜 = `mv-video/references/prompt_format.md`；一致性 = `mv-image/references/prompt_format.md`；合成 = `mv-compose/references/usage.md`。

---

# 模式①：作品质检

## 机检 / 人判分工

- **机检（确定性，先跑）**：`scripts/mv_check.py <制MV作品根>` —— 秒级出确定性问题：
	  - **卡点**：`beatgrid.json` 绑定当前歌曲 SHA-256；正式版小节首/sections 有具名签收且完整覆盖；BPM、单调性、歌长一致。
	  - **规划**：`分镜/clip_plan.json` / `timeline_manifest.json` 存在可解析、clip_id 不重复、timeline 与 plan 对账、timeline selected video 是否存在。
	  - **一致性注册**：`设定/identity_registry.json` / `asset_registry.json` / `分镜/reference_plan.json` / `设定/reference_requirements.json` 存在可解析，参考组与正式参考图覆盖度有快照。
	  - **制片锁版**：animatic、V1+A1+markers OTIO/receipt、shot list、setup schedule、take log、picture lock 是否齐且 edit/input hash 新鲜。
	  - **视频任务**：`出视频/jobs_manifest.json` 存在可解析、已选 take 是否真的落到 `出视频/视频/Clip_XXX.mp4`。
	  - **图生视频继承 / 视频QC**：报告存在、hash 对应当前 plan/jobs/video；正式项目缺报告或语义签收直接阻断。
	  - **正式版 readiness**：`生产数据/formal_readiness/formal_readiness.json` 存在时读取状态；demo 项目只作为信息提示，正式项目 blocked/review 会暴露。
	  - **clip 节奏**（需 `ffprobe`，缺则显式跳过）：每个 `出视频/视频/*.mp4` 时长、**clip 是否疑似等长（不卡点）**、clip 总时长 ≈ 歌长。
	  - **卡拉OK字幕**：LRC/ASS 解析、占位/越界/重叠/行数；alignment report 是否为当前 schema v5 并绑定当前歌/歌词/对齐音轨/ASS/LRC；正式验收只接受 calibrated、singing-specific、eligible 的逐行声学证据，或绑定当前内容的具名逐行听审；stem→master offset/drift 必须有效。
	  - **音画合成/交付**（需 `ffprobe`）：母版和 MP4、音画差、画幅/音轨、BT.709/H.264/48kHz；delivery QC 对比输入母带与输出响度/真峰值/时长，provenance 是否齐。
  - **AI 披露 / C2PA**：已有成片时检查 `合规/ai_usage.json` 是否当前。C2PA requested 时分别报告 embedded、structural validity、signature validity、trust anchors / trusted、test certificate、`timestamp_validated` 与 `timestamp_trusted`；`signature_info.time` 不是 TSA 证明，结构或签名有效也不等于生产可信。**C2PA/Content Credentials 绝不替代目标平台的 AI 内容声明**。
  - **完整性/对账**：词/歌/beatgrid/出图/clip/成片 产物快照、`_meta.has_song/has_lyrics` vs 实际文件、段落数 vs `_meta.structure`。
  ```bash
  python3 <skill>/scripts/consistency_findings.py <制MV作品根> --write
  python3 <skill>/scripts/mv_check.py <制MV作品根>          # 人读
  python3 <skill>/scripts/mv_check.py <制MV作品根> --json   # 喂回 LLM 汇总
  # 完成人审后才显式写具名收据（不可用 AI/agent 作 reviewer）
  python3 <skill>/scripts/mv_check.py <制MV作品根> --write-receipt \
    --reviewer "王晓明" --notes "已逐项审片，同意当前版本交付"
  ```
  默认的人读 / JSON 命令都**严格只读**，不会顺手把 review 标完成。只有显式 `--write-receipt`、`--reviewer` 为真实姓名、`--notes` 非空，且机检 `hard_blocks=0`，并由 completion 复算 compose / disclosure / provenance 及已进入的 image / video_jobs / video 健康度均无错误，才写 `生产数据/review/review_receipt.json`。收据必须同时绑定当前 `成片_MV.mp4`、`成片_MV_master.mov`、`delivery_qc.json`、`provenance.json`、`ai_usage.json` 的 SHA-256；任一文件变化后旧收据自动过期。
  `consistency_findings.py` 写 `生产数据/consistency_findings.{json,md}`，把 `identity_registry` / `reference_plan` / `shot_variety` / `craft_audit` / `drift_risk` / `image_qc` / B14 ledger / `verifier_coverage` / `inherit_contract` / `video_qc` / `alignment_report` 收成一个统一一致性证据面，供审片和返修排序使用。另含**止损轻量件**（stop_loss lite，按 MV 单曲工位裁剪）：读 `生产数据/production_events.jsonl` 算出图重画率（>35% → warn `image_redraw_rate_high`）、读 `出视频/jobs_manifest.json` 算平均每 clip take 数（>3 → warn `takes_per_clip_high`）——同一张图反复重抽/一个 clip 抽一堆 take 挑不出，是积分烧穿前兆，该回头修 prompt 锚点/参考图而不是硬抽。degraded/manual review/旧 `--accept-degraded` 均不能替代 B14 的 full machine QC 与逐图当前验收。
- **视觉多样性事前机检（出图前跑，最便宜的点）**：`scripts/shot_variety_audit.py <制MV作品根> --write` —— 读 `分镜/clip_plan.json` 的 `shot_design`，在花积分出图前拦「同构图反复 / 景别单调 / 副歌静镜 / 场景滞留 / 大变化镜头缺参考锚」。report-only（最高 warn，永不 block），写 `生产数据/shot_variety/shot_variety.{json,md}`，被 gate（image 阶段）、`consistency_findings` 与 `mv_check` 消费。补 `mv-score`/`pacing.py` 纯数值卡点引擎**从不读画面字段**的盲区——MV 命门除了卡点就是**视觉不重复**。出图后由 `mv-image` 的 `image_qc` dHash 做像素级现实核对；MV 无台词，因此只采用视觉信号。
- **VLM 并排裁决任务包（出图后跑·内容级判官·2026-07-17 参照漫画线复裁闭环）**：`scripts/vlm_judge.py <制MV作品根> --write` —— mv 的数值机检（脸余弦/dHash/ΔE）不看内容，"主角是不是同一个人 / 接缝首末帧接不接得上"此前只有人判。任务包两轴：lead_identity（已出图 clip 首帧 vs reference_inputs 身份定妆组）、seam_continuity（need_end_frame 的 clip 末帧 vs 下一 clip 首帧）。多模态 agent 逐条看图打分回填 `生产数据/vlm_judge/vlm_judge_verdicts.json`，裁决必须原样复制 image_sha256/task_sha256/references_sha256 且带 evaluator{model,version}——重抽后旧裁决自动作废、空壳裁决被丢弃。gate（image/video_jobs/compose）消费两个文件做覆盖率对账：缺任务包→建议跑；任务包存在但 0 有效裁决→**机检空转 warn**（漫画线实证过该空档：93 条任务 0 裁决、画错主体照样放行）；部分裁决→覆盖率不足 warn；suspect/score<=2→逐条 warn 交人审。advisory 铁律：永不 block。
- **传统 MV 手法机检（出图前跑·craft audit）**：`scripts/craft_audit.py <制MV作品根> --write` —— 把真人 MV 片场沉淀的**结构律**做成计划期机检：①副歌复现升级律（第 k 次副歌无新场景/新景别/新母题/更高运镜能量/更多镜 → warn `chorus_no_escalation`；末副歌该给全曲最大 payoff）；②动静对比律（副歌平均运镜能量 ≤ 主歌 → warn `no_dynamics_contrast`；主歌拉满 → info headroom 耗尽）；③hook 上脸律（副歌无对镜演唱近景 → warn；全曲无表演线 → info 自检纯叙事意图）；④冷开场律（首钩信号前 >8s → warn，竖屏前 3 秒定生死）；⑤关键镜候选律（key 镜候选 <2 → warn/未计划 → info，「shoot options for the edit」片场惯例）；⑥bridge 换气律（音乐转折画面不转 → info）；⑦词画呼应（歌词意象与画面零重合 → info 弱信号自检）。写 `生产数据/craft_audit/craft_audit.{json,md}`，report-only（最高 warn），被 gate（image/video_jobs）与 `consistency_findings` 消费。配套：`mv-craft/pacing.py` 新增**晚切偏置** `late_cut_bias`（对齐切点中晚于拍点 >0.04s 的比例——剪辑手法是压拍或提前 1-3 帧落刀，晚切读感拖；mv-score 打印 >0.3 提示）。
- **现实验证器覆盖账本（fail-closed）**：`consistency_findings` 的 `verifier_coverage` 维度——声明每个现实验证器（出图脸检 insightface / 主色 palette / 构图 dHash / 视频脸检 / 视频抽帧感知）是否**适用**（项目登记了要查的数据）且**真跑过**（后端真出活）。治「跑了 QC 数据却没真执行一致性」：insightface/Pillow 缺失时最强检测器静默降级休眠，报告看着"跑过 QC"其实全程空转——适用但休眠 → warn 现形（正式项目 image 脸检休眠已由 gate 的 precision≠full 硬拦，本层不重复造 block）。
- **一致性 Charter 防静默降级（流程自检·不读项目）**：`scripts/consistency_charter.py` —— mv load-bearing 闸的 enforcement 单一意图源，现同时守版权/节拍/歌词声学与 stem 时基/B14/身份/picture lock、model×channel 真实提交、具名 cut map、整数帧 OTIO、逐输入色彩、最终 PCM、C2PA 分层、review/handoff 收据与可移植路径。每闸声明**守护片段**与 **is_demo 引用冻结基线**；新增豁免或删掉承重检查会让测试变红，必须先显式更新裁决与日期。`python3 scripts/consistency_charter.py` 退非 0 即违规。
  > `ffprobe` 缺失时，clip/成片 的时长·分辨率·音轨检查**显式标「跳过」**，绝不静默略过。`song.wav` 时长优先走标准库 `wave`，mp3/m4a/flac 走 ffprobe。

- **人判（判断题）**：机检覆盖不了的语义维度。逐维见 `references/checklist.md`。
  - **崩脸 / 场景漂移 / 画风跳变用图判**：把 `出图/段落/图片/镜头*.png` 与 `出图/共享/图片/定妆_*.png` **并排读图比对**（脸型/发型/服色/画风锚点）；装了 `face_recognition`/`insightface` 可给相似度分，缺库则人判兜。
  - **接缝跳切用图判（逐接缝过）**：取相邻 clip 的 Clip K 末帧 vs Clip K+1 首帧**并排读图**，对照 `分镜/clip_plan.json` + `timeline_manifest.json` 的接缝契约：① 标 `need_end_frame=true`/连续硬切但两帧姿态/站位/视线/光线明显对不上 → 跳切/闪烁；② 标 `need_end_frame=true` 却没出 `_end.png`（mv-image 漏做）→ 接力断链；③ 服装/发型/道具在接缝处突变 → 接缝崩。**注意 MV 容差更宽**：副歌卡点硬切处的视觉跳变若踩准鼓点、是有意冲击，**不算问题**（卡点切本就允许画面跳）；只标"非卡点切又接不住"的接缝。修法：回 mv-image 补尾帧 / 回 mv-video 用首尾双帧重出该 clip。
  - **运镜与动作服务节奏**：副歌快速推镜头/甩镜/环绕/冲击变焦、verse 缓慢推镜头/稳定器跟拍、bridge 换机位/前景遮挡揭示，爽点对 downbeat 同帧砸下；动作家族、动作峰值、转场母题对 `mv-video/references/action_knowledge.md` + `mv-video/references/prompt_format.md`，运镜词对 `mv/references/运镜/manifest.json`。只写“炫酷动作/炫酷运镜”但没有可执行动作链和结构化镜头运动，标为建议级。
	  - **单曲视觉一致性**：除身份/画风，还逐接缝审状态变体、服装/道具状态、持握手、场景拓扑、屏幕方向、视线、动作速度/相位、光线方向和字幕安全区；结论由 `video_qc --accept-semantic` 同时绑定当前视频 hashes 与 seam-contract hash。
  - **卡点体感**：机检给"clip 是否对齐 downbeat"的客观判断，**踩得爽不爽**由人判（看成片副歌切点是否砸在鼓点）。

## 工作流（模式①）

0. **定位 + 确认范围**：作品根 = `创作区/制MV/<曲名>/`。读 `_进度.md` 知各阶段进度（未到的阶段不当问题报，如还没合成就别报"缺成片"）。
1. **跑机检** → 确定性问题清单（卡点 + clip + 字幕 + 合成 + 对账）。
2. **人判**：对照 `references/checklist.md` 逐维，**只记真问题**，每条带证据（Clip / 段落 / 时间码 / 图路径）。崩脸并排读图。
3. **汇总报告** → 写 `创作区/制MV/<曲名>/_质检.md`：按严重度排序，每条 = 位置（`Clip07` / `[chorus]@时间码` / 文件）+ 维度 + 问题 + **修法** + 证据。附"健康度概览"表。
4. **具名验收**：真实复核人看完当前成片与清单后，显式跑 `--write-receipt --reviewer ... --notes ...`。机器绿灯本身不会写收据，C2PA 也不能代替此人审或平台披露。
5. **修复回流（关键）**：MV 的修法**回源头改、重跑回流**，不在成片 MP4 上硬剪。报告里每条修法都指明**回哪个 skill 重跑**（如"崩脸→回 `mv-image` 重出该镜""clip 不卡点→回 `mv-video` 按 beatgrid 重定 clip 时长""字幕越界→回 `mv-lyric-sync` 重对齐""成片无音轨→回 `mv-compose` 重铺歌轨"）。

## 严重度（定级 + 容错铁律）

| 级别 | 含 | 处置 |
|---|---|---|
| 🔴 阻断级 | 崩脸/角色断层、字幕占位未精修、成片无音轨、beatgrid 损坏/乱序/与当前歌不匹配、正式收据/锁版失效、母带被截短或交付 QC hard block | **必改**，回源头重跑 |
| 🟡 建议级 | 场景轻漂、画风跳变、**非卡点切接缝跳切/接力断链**、**clip 疑似等长不卡点**、clip/成片总时长 vs 歌长差大、分辨率不符画幅、BPM 半/倍速嫌疑、字幕时间越界/重叠、运镜不服务节奏、爽点没对 downbeat | 建议改 |
| 🟢 润色级 | 个别运镜偏好、转场差一拍、字幕位置微调 | 可改可不改 |

**容错铁律**：只报"真问题"。轻微主观偏好不入报告；mv-image 的"筛选一致优先"不应被润色项淹没。

> **职责边界**：输入歌本身的深度体检不在本 skill 重复；mv-review 只关心"歌轨进没进成片、时长对不对、卡点踩没踩准"。

---

# 模式②：流程自审（让制MV 产线自我优化）

把"人工复盘整条 mv 线"固化成可复跑流程。**节律**：用户主动要 / 做完一批 MV / 接了新生图·生视频·卡点·对齐模型时跑一次。详细步骤见 `references/self_audit.md`，要点：

1. **拉基准**：联网搜当前（带年月）AI 音乐 MV / 卡点视频主流做法，分三轴取证——**视觉一致性**（定妆/参考/相似度、IP-Adapter/LoRA、跨段一致）、**卡点节奏**（beat-sync 工具、副歌踩点、运镜节奏、AI 卡点剪辑）、**音画合成与可控性**（卡拉OK对齐、画幅适配、字幕烧录、转场）+ 各 stage 模型演进（生图/生视频/对齐 SOTA）。
2. **对照**：逐 stage 把基准 vs `mv-*/SKILL.md` + `references/*` 比，找**真差距**（已做的别重复立项）。
3. **差距清单**：每条 = 差距 + 证据（带来源链接·日期）+ 落到哪个 skill 哪段 + 优先级（must/optional）+ 是否可脚本化（是→能进 `mv_check.py`）。
4. **起草**：高价值项起草建议 edit；**改任何 skill 必同步 `skills/README.md` 索引**（仓库硬约定）。
5. **人确认后再写**：模式②**默认只产建议报告**，不自动改 skill。**报告是一次性的——只讲给用户、不在 skill 目录留存 `_流程自审_*.md` 这类存档**（已 gitignore）。**每次自审/重审都从头按本流程重跑**（拉基准→对照→差距），**绝不读旧报告当捷径**——市场会变，旧结论可能已过时或已落地。

> **防过期铁律**：市场建议带"采集日期 + 来源链接"，旧建议可能已被采纳或过时——写进来前先核对当前 skill 是否已有。模型名/特性会变，写"能力"而非死绑某产品版本号（绑版本号的放 `prompt_format.md` 档案）。

---

## 详细参考
- 作品质检全维度清单（看什么 + 怎么判 + 定级 + 健康度概览）：`references/checklist.md`
- 流程自审操作手册（拉基准 / 对照 / 起草）：`references/self_audit.md`
- 正向标准：卡点 `mv-beat/SKILL.md` · 运镜/动作 `mv-video/references/prompt_format.md` + `mv-video/references/action_knowledge.md` · 一致性 `mv-image/references/prompt_format.md` + `mv-image/references/visual_consistency.md` · 合成 `mv-compose/references/usage.md`

## 常见错误

| 错误 | 纠正 |
|---|---|
| 只跑机检不做人判 | 机检只覆盖确定性问题；崩脸/运镜/卡点体感要 LLM 判（含并排读图） |
| 只人判不跑机检 | clip 等长/字幕越界/成片无音轨/对账这类秒查，漏跑等于白审 |
| 跳过 mv-plan 直接出视频 | 机检会提示缺 clip_plan/timeline；先补时间线，避免合成顺序和时长全靠猜 |
| 没装 ffprobe 就当 clip/成片"没问题" | ffprobe 缺失时相关项是"跳过"不是"通过"——机检会显式标 |
| 鸡蛋里挑骨头堆润色项 | 违容错铁律，硬伤被淹没 |
| 报问题不定位不给修法 | 必须 Clip+时间码定位 + 指明回哪个 skill 重跑 |
| 在成片 MP4 上直接剪 | 回源头改重跑回流；成片是产物不是源 |
| 把未到的阶段当问题报 | 先读 `_进度.md`：还没出视频就别报"缺 clip" |
| 重复审输入歌的音质/词 | mv 只审歌轨进没进、卡点对不对 |
| 模式②未经授权直接改 skill | 默认只出建议；用户像本次一样明确要求“自行全部优化”时可在范围内直接落地，仍须测试、同步统计并保留其他未提交改动 |
