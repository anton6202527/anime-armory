---
name: n2d-review
description: 漫剧质检 + 流程自审（n2d 的 QA 环节，不生产内容只审）。双模——模式①「作品质检」：对已产出的某集/整部漫剧做穿帮体检（角色崩脸/场景漂移/构图景别/字幕错位/音画不同步/双人声/节奏留存/口型），机检+人判，出严重度分级·定位到镜头的报告。模式②「流程自审」：联网拉当前市场基准，对照 n2d 各 skill + Q&A，产出"差距清单 + 该改哪个 skill 哪段"的优化建议，让整条流水线可重复自我体检。Use when asked to 漫剧质检, 审片, 查崩脸, 查穿帮, 字幕对账, 成片体检, 流程自审, 自我优化, n2d 还能优化啥, n2d-review. Triggers 漫剧质检, 审片, 崩脸, 穿帮, 字幕错位, 音画同步, 成片体检, 验收, 流程自审, 流程优化, 自我优化, n2d-review, QA.
---

# n2d-review — 漫剧质检 + 流程自审

不生产内容，只**审**。是 n2d 家族的 QA 环节，与 `novel-review`（审小说）同构。两个模式：

- **模式①「作品质检」**——审**某集/整部漫剧的产物**：扫穿帮 → 定位（镜头 + 时间码）→ 定级 → 给修法 → 出报告。出成片前 / 各阶段闸门跑。
- **模式②「流程自审」**——审**流水线本身**：联网拉市场基准，对照 n2d 各 skill + 累积 Q&A，产出"差距清单 + 建议改哪个 skill 哪段"。让"整套流程不断自我优化"成为一条可复跑的命令，而非靠人想起来。

> 行业把 **一致性 · 效率 · 可控性** 定为漫剧三大验收维（《AI漫剧工业化白皮书》）；商用"AI审片系统"自动识别约 12 类问题（角色断层/崩脸/构图错/糊/字幕错…）。本 skill 把这套体检在 n2d 产线里落成可跑流程。

---

## 输入 / 输出 / 读写边界

- **输入**：某集/整部的脚本、分镜、图包、视频、字幕、配音、dashboard/gate 数据、identity/score/review-ui 产物；流程自审还读 n2d skill 文档和模型矩阵。
- **输出**：机械检查、一致性 findings、gate findings、质检报告、流程自审报告；按需触发 score/review-ui/batch 的下游产物。
- **读写边界**：不生产图/视频/配音；作品质检只写 QA/报告/ findings，修复必须回对应 stage 重跑；流程自审默认 report-only，用户确认后才改 skill。
- **契约关系**：gate stage、finding kind、回流字段、官方生图后端白名单等从 `skills/n2d/_lib/n2d_contract.py` 读取；生产入口统一推荐 `n2d-dashboard gate`。

# 模式①：作品质检

## 机检 / 人判分工（照搬 novel-review 的成熟做法）

- **机检（确定性，先跑）**：`scripts/mechanical_check.py <作品根> 第N集` —— 秒级出确定性问题：字幕↔配音文本/时间码对账、中英字幕错位、占位未精修、单行溢出、配音占位音色未替换、产物完整性对账、钩子/集尾留存信号缺失、**脏标点 lint（中英）**（中文 `||` 气口残留 `。，`/`，，`/行首逗号 + 英文 标点前空格/多空格/叠逗号/行首逗号·省略号 `...` 豁免——即便字幕与配音"同样脏"对账能过也单独抓；源头 `voice_text.clean_text` + `finalize._clean_punct/_clean_en` 已修，旧集 stale 数据靠它兜）。**审查第1步即自动跑，无需人记得扫。**
  ```bash
  python3 <skill>/scripts/mechanical_check.py <作品根> 第N集          # 人读
  python3 <skill>/scripts/mechanical_check.py <作品根> 第N集 --json   # 喂回 LLM 汇总
  ```
- **算法层一致性（P0/P1/P2，已接入 `consistency_audit.py` + stage gate）**：
  - **P0 语义谱系 Diff**：`semantic_continuity.py` 把 `voiceover.txt → storyboard.json → 出图 prompt → 出视频 prompt` 抽成关键词谱系，检查角色、场景、状态、风格、专项模板、continuity 是否逐层继承；匹配层是精确词 + 常见同义别名 + 中文 bigram 重叠，仍保持无依赖可进 gate。
  - **P1 n2d 动态百科 / 状态哨兵**：`state_continuity.py` 读取 `storyboard.json.visual_contract.角色状态演进` + `出图/共享/visual_state_ledger.json`，抓状态提前泄露、区间结束后泄露、开始后漏继承；`until/至 ClipN/本镜` 会被当作状态区间，不再默认延到集尾。跨集账本可用 `state_ledger_build.py <作品根> --episodes 1-10 --write` 从 storyboard 确定性生成。
  - **P2 多模态视觉语义 / 道具漂移 / 场景结构唯一性**：`multimodal_consistency.py` 按资产分组查离群；`scene_consistency.py` 进一步集成 `asset_registry.json`，自动提取场景/道具的**结构唯一性约束**（如：LOC_01 必须单门单窗、PROP_02 毒酒瓶必须圆口无嘴），在 QC 报告中显式列出作为人判/机检的**强约束基准**，防止 AI 在视频中随机增减背景结构。
- **阶段 gate（确定性，生产前跑）**：正式生产入口统一用 `python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image_preflight|video_preflight|image|video|compose|review`。默认在正式调用后端前跑 `image_preflight` / `video_preflight`，生成落档后跑 `image` / `video` 回验。它会调用底层 `scripts/gate.py --json`，把高风险流程规则脚本化检查并把 `block/warn/info`、回流 stage、重跑范围写进 `生产数据/`，同时外发 `gate_findings_<stage>_第N集.json`（kind=`n2d_consistency_findings`，可直接交给 `n2d-batch --from-consistency-findings`）；`block` 退出码 1，先修再进入该阶段。底层 `scripts/gate.py --json` 只作调试/机器消费入口，不作为生产推荐入口。检查范围包括：合规包、`storyboard.json` continuity、尾帧、prompt 检查段、共享定妆、资产身份注册层、占位配音、clip 原生音轨/原生音画 opt-in/时长、基础视觉风格契约、复杂镜头模板、Motion Control、生图 AI 一致性、**P0 语义谱系 / P1 状态百科前置**；`review` gate 另跑 **P2 多模态漂移**。
  - **输入首帧脸一致性硬闸**：`video_preflight`/`video` 读取 `生产数据/image_qc/<ep>/image_qc_<ep>.json`，不重跑像素引擎但严格消费证据。缺 image_qc、旧版 QC 缺 `face_reference_coverage`、`qc_environment.precision_level!=full`、`summary.hard_blocks>0`、`face_reference_coverage.missing>0`、PNG 晚于 QC，全部 BLOCK 回 `image`。每张已落档角色 PNG 必须逐张对定妆/身份主参考过 full 精度脸部比对；这是图生视频前置铁律，不能降级成 WARN。
- **QA 入账铁律（P0）**：每次跑 gate 或作品质检，都要把 QA 结果写入 `n2d-dashboard`。生产前 gate 不再先跑裸 `gate.py` 再补记账；直接用上面的 `dashboard.py gate` 单入口。人判报告里的新增阻断用 `record --stage review --event qa --qa-sev block|warn|info` 补录；否则仪表盘无法统计 QA 阻断率。
- **自动审片评分（P2）**：作品质检完成后跑 `python3 skills/n2d-score/scripts/score.py <作品根> 第N集 --run-checks --threshold 85`，把语义继承、状态百科、多模态漂移、角色一致性、服装一致性、场景一致性、字幕正确性、音画同步、音色一致性、节奏密度、风格一致性汇总成机器分。`--run-checks` 还会缓存 `score_inputs/第N集_visual.json` 与 `score_inputs/第N集_voice_print.json`，接入图像相似度、字幕 OCR、成片/配音/SRT/storyboard 时长对账、口型风险/检测报告、成片节奏密度和声纹机检，让机器分更贴近观感。若用户要求自动返工或批量回流，加 `--enqueue-low`，低分维度会转成 `n2d-batch` 的 rerun 队列。评分后需要人审时，跑 `python3 skills/n2d-review-ui/scripts/review_ui.py <作品根> 第N集 --write --markdown`，把机器分、QA flag、首尾帧、clip、接缝和定妆参考放进可视化画布。
- **人判（LLM 判断题）**：机检覆盖不了的语义维度——崩脸/场景漂移、**clip 接缝跳切/闪烁**、构图景别（对 `n2d-script/references/分镜语法.md`）、节奏体感（对 `n2d/references/导演节奏.md`）、口型、原生音频双人声。逐维见 `references/checklist.md`。
  - **崩脸用图判**：把该集 `出图/第N集/图片/镜头*.png` 与 `出图/共享/图片/定妆_<角色>.png` **并排读图比对**（脸型/发型/服色/配饰/锚点特征），漂了就标。装了 `insightface` 时跑 `scripts/face_consistency.py <作品根> 第N集` 给余弦相似度分——**不写死阈值**，而是**自标定 flag-band**：用本作定妆组内部互相余弦（同角色 正脸↔侧脸/半身 本就该高度相似）当"同一人下限"地板，每镜低于 地板−margin 标 🔴、地板带标 🟡（写死 0.45 对风格化脸要么误杀要么放过；业界 ArcFace 同人≈0.5–0.68 且因画风而异）。注意：进入视频前不只靠审片人“看过”，必须先由 `image_qc.face_reference_coverage` 证明每张已落档角色 PNG 都有 full 精度定妆/身份主参考比对记录；缺库、降级、warn/noface、缺比对行都回 `n2d-image`。
  - **服装/配色漂移用机检（脸之外的漂）**：脸锁住不等于服装锁住——2026 公认"夹克色第 4 镜就漂"。装 Pillow 时跑 `scripts/outfit_consistency.py <作品根> 第N集`：对人物镜取**加权色相直方图**（饱和度×明度加权，压低灰暗背景），与该角色定妆组（优先半身）比，同样**自标定 flag-band**（定妆组内部直方图余弦设地板）。缺库由人判并排比服色/发型。
  - **片内时序用机检（单 clip 内身份漂移 + flicker）**：n2d-review 只查首帧 + 接缝，漏查 clip 内部"几秒后脸渐变/发际线闪"。装 ffmpeg(+insightface) 时跑 `scripts/temporal_consistency.py <作品根> 第N集`：每条 clip **按时长自适应抽帧**（≈1帧/秒，近景镜 ×1.5 加密，floor=6·封顶24——固定 6 帧对 10–60s 长镜太稀，片中段渐变脸漂会从采样缝漏过，2026 各家 long-range 时序仍是软肋），量 ① 相邻帧人脸余弦最小值（片内身份漂移）② 相邻帧亮度绝对差均值=flicker/TCI，超阈标 🔴/🟡。对标行业 scene-stability 记分卡；缺库由人判抽帧看。
  - **定妆主参考质量门（N3·锚点不能脏）**：锚点一脏下游每镜继承错。装 insightface+cv2 跑 `scripts/face_consistency.py <作品根> 第N集 --audit-anchor`：每个 `定妆_<角色>.png` 主参考须**恰好 1 张清晰、够大的正脸**（0 张/多张=🔴，脸太小=🟡）——出图共享先行闸门前就拦，别让脏锚点污染全集。
  - **糊/低质无参考质检（N4）**：装 Pillow 跑 `scripts/quality_check.py <作品根> 第N集`：用 **Laplacian 方差**测清晰度，**自标定本集中位数**（绝对阈值因画风漂），显著低于中位数=相对糊（关键镜更严），标 🔴/🟡。与一致性正交，同属「崩脸/糊」族。
  - **风格漂移用机检（S1·补 style_contract 落地后零机检的盲区）**：装 Pillow 跑 `scripts/style_consistency.py <作品根> 第N集`：每镜取风格指纹（饱和直方图+明度直方图+边缘密度），**自标定 median-中心 flag-band**——内聚度显著低于本集中位=某镜突然偏离所选风格（突然照片感/插画/高饱和）。配合 `style_contract` 与逐镜负向风格禁忌（gate 已强制）形成"契约定风格→负向堵→S1 兜底机检"闭环。缺库人判读「本集基础视觉风格契约」并排看。
  - **接缝跳切先机检再人判（N2接力·把"逐接缝并排读图"降成初筛）**：装 Pillow 跑 `scripts/temporal_consistency.py <作品根> 第N集 --seam`，**两个互补量化指标**：① 尾帧 `镜头N_end.png` vs 下一首帧 **dHash 距**（灰度结构）抓构图/姿态错位；② **RGB 直方图 cosine 距**抓"同构图但灯光/色温跳"的剪辑点闪光（dHash 看不到颜色）。任一超阈即报、取较重者定级；色彩端缺 Pillow 时静默退化为纯 dHash（不臆造）。距大=尾帧没对上下一首帧→出视频必跳切/闪；距小不代表姿态完美仍需人判，但距大几乎必跳——先机检筛出可疑接缝再逐个人判。
  - **跨集人物一致性（⑦·身份闭环报表）**：优先跑 `python3 skills/n2d-identity/scripts/identity.py <作品根> --episodes 1-10 --write`，生成 `identity_adapter_matrix` + `identity_drift_report`；它把 registry 的 Face Lock / Character ID / LoRA / reference group binding 与逐集 🔴/🟡 漂移合并。旧命令 `scripts/face_consistency.py <作品根> 第N集 --cross-ep` 仍可单独看脸相似度，但不含 adapter 闭环。
  - **接缝跳切用图判（逐接缝过）**：沿接力链逐个查相邻 Clip 的接缝——取 Clip K 末帧 vs Clip K+1 首帧**并排读图**，对照 `故事板.md` 该接缝契约：① 契约说"姿态连续硬切/有尾帧"但两帧人物姿态/站位/视线/光线明显对不上 → 跳切/闪烁，标问题；② 契约 `需要尾帧?=是` 却没出 `镜头N_end.png`（n2d-image 漏做）→ 标接力断链；③ 服装/发型/道具在接缝处突变 → 接缝崩。轻微姿态差走容错铁律放行。修法：回 n2d-image 补尾帧 / 回 n2d-video 用首尾双帧重出该 Clip。
  - **导演一致性契约用人判（整段读）**：审视频 prompt 或成片时先读 `出视频/第N集/prompt/00_总览.md` 的「本集导演一致性契约」，再逐 Clip 判断是否违反主色调、镜头语法、轴线、剧情状态锁、场景状态。典型问题：爽点特效提前泄露、同场景灯位/雨雾跳变、人物左右站位反复跳轴、铺垫段乱甩镜、落幅接不上下一镜。修法：回 n2d-video 改 prompt；若首尾状态源头不对，回 n2d-script 改故事板接力契约，必要时回 n2d-image 补尾帧。
  - **基础视觉风格契约用人判（整段读）**：审图包、视频 prompt 或成片时先读「本集基础视觉风格契约」（旧项目读「本集真实电影感契约」），再判断画面是否稳定遵守所选风格：角色比例/材质或线条是否一致、光色是否守策略、运动是否在边界内、是否触犯该风格的禁忌。修法：源头回 n2d-script 改 `style_contract`，再让 n2d-image/video 继承；只在单镜末尾补某个风格词视为无效修复。

## 工作流（模式①）

1. **定位 + 确认范围**：作品根 = `制漫剧/<剧名>/`。问审一集还是整部、审到哪个阶段（出图后 / 成片后）。读 `_进度.md` 知各集进度。
2. **跑机检 + 一致性编排 + 身份闭环 + 合规包 + QA 入账** → 确定性问题清单（按集）：先 `scripts/mechanical_check.py`（字幕/对账/占位），再 **`scripts/consistency_audit.py <作品根> 第N集` 一键串跑视觉/语义一致性检测器**（**语义谱系 P0 · 状态百科 P1 · 多模态 P2 · 视觉契约继承** · 锚点门 N3 · 脸 G1 · 服装配色 N1 · 片内时序 N2 · 场景 O2 · 糊 N4 · **风格 S1** · **接缝接力** · **字幕对齐 L1**[双语短语边界/阅读速度/译文完整性，补 mechanical_check 条数对账盲区；`scripts/subtitle_align.py` 可单跑]）——默认同时**结构化外发** `生产数据/consistency_findings_第N集.json`（kind=`n2d_consistency_findings`，逐条带维度/严重度/镜头定位/`return_to_stage`，`n2d-feedback` 读它做一致性回灌；`--no-export` 关闭）并登记一条 dashboard `consistency_findings` 事件；脸 G1 在无 insightface 时自动降级 **Pillow 基础机检**（图存在/可解码/分辨率/清晰度，标 `pillow_fallback`+`insufficient_precision`，绝不臆造相似度，n2d-score 按降权分消费），再跑 `python3 skills/n2d-identity/scripts/identity.py <作品根> --write` 生成 adapter matrix、跨集漂移报表和 `consistency_findings_voice_print_第N集.json` 声纹一致性 findings；缺 `合规/compliance_manifest.json` 时先跑 `python3 skills/n2d-compliance/scripts/compliance.py <作品根> 第N集 --init` 并人工补齐。阶段 gate 结果必须同步跑 `python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage review` 或对应生产 stage 入账。别只跑单个检测器漏掉其余。
3. **生成机器分**：跑 `python3 skills/n2d-score/scripts/score.py <作品根> 第N集 --run-checks --threshold 85`，把机检、dashboard 阻断、一致性结果和 visual checks 落成 `生产数据/score_第N集.json/md`。若要自动回流，追加 `--enqueue-low`，让低分维度进入 `n2d-batch` 队列。
3.5. **一致性总账（E3·单页画像）**：跑 `python3 skills/n2d-review/scripts/consistency_ledger.py <作品根> 第N集`，把散在 ≥4 处的一致性信号——事前(face/asset_drift_risk)、落档(image_qc/consistency_findings)、契约(contract_inheritance 的 identity/asset handoff)——按**每角色 × 每资产**滚成一张三态表 + 综合档，落 `生产数据/consistency_ledger_第N集.{json,md}`。只读不阻断，让 agent/审片人只读这一份就知道"哪个角色/资产到底稳不稳"，不必同时盯好几个 JSON。
4. **生成人审画布**：跑 `python3 skills/n2d-review-ui/scripts/review_ui.py <作品根> 第N集 --write --export-findings --markdown`，输出 `生产数据/review_ui_第N集.html/json` 与 `review_ui_findings_第N集.json`（kind=`n2d_consistency_findings`）。先看全局机器分和 QA flag，再按画布逐个核首帧、尾帧、clip、接缝、定妆参考和缺素材；工业级批量审片不得只依赖文本报告。
5. **人判**：集多时**每集独立审查**（省主上下文），优先打开 `review_ui_第N集.html` 做视觉核查，再对照 `references/checklist.md` 逐维，**只记真问题**，每条带证据（引文 / 图路径 / 时间码）。
6. **汇总报告 + 修复回流** → 写 `制漫剧/<剧名>/_质检_第N集.md`（整部则 `_质检_全片.md`）：按严重度排序，每条 = 位置（镜头N·@时间码 / 文件）+ 维度 + 问题 + **修法** + 证据。附"健康度概览"表（各维度 通过/问题数 + 一致性度量分如有）。漫剧的修法**回源头改、重跑回流**，不在成片上剪；报告里每条修法都指明**回哪个 stage 重跑**（如"崩脸→回 n2d-image 重出该镜""字幕错位→重跑 finalize_storyboard""节奏塌→回 n2d-script 阶段2 重切镜头时长曲线"）。
   - 批量返工时，优先把 `consistency_findings_第N集.json`、`review_ui_findings_第N集.json`、`gate_findings_<stage>_第N集.json` 或 `consistency_findings_voice_print_第N集.json` 直接交给 batch：`python3 skills/n2d-batch/scripts/queue.py plan <作品根> --from-consistency-findings <作品根>/生产数据/review_ui_findings_第N集.json`。需要手工补充时，再把 finding 的 `return_to_stage` / `affected_artifacts` / 具体 Clip 转成定向任务：`python3 skills/n2d-batch/scripts/queue.py plan <作品根> --episodes 第N集 --rerun-from image|video|compose --affected-shot Clip_03 --affected-artifact <路径> --scope "<问题摘要>"`。只重跑受影响镜头，不整集重来。

## 严重度（定级 + 容错铁律）

| 级别 | 含 | 处置 |
|---|---|---|
| 🔴 阻断级 | 崩脸/角色断层、字幕错位或占位未精修、配音占位未替换、双人声打架、合规未授权克隆 | **必改**，回源头重跑 |
| 🟡 建议级 | 场景轻漂、clip 接缝跳切/闪烁、构图/景别违 `分镜语法`、节奏塌/钩子弱/集尾不够、字幕溢出、卡点没对上爽点时间戳 | 建议改 |
| 🟢 润色级 | 个别动态细节弱、留白差一拍、音效偏好 | 可改可不改 |

> **生图 AI 不一致单独提级**：生产前发现设置/prompt 口径混用多个官方/已登录后端，或出现 `同视频AI` 含糊口径、第三方逆向/web 自动化出图口径，按 🔴 阻断处理；成片后才发现，按画面结果定级，但报告必须写清"疑似因生图后端混用造成一致性税"，修法是回 `n2d-image` 统一到同一个官方后端并重出受影响定妆/分镜。

> **双人同框 × 单图参考后端 硬阻断（脸漂真凶工程化）**：`image_preflight` gate 在「生图AI=无原生主体锁的单图参考后端（persistent_subject=False，如 Codex/OpenAI/Dreamina/Nano Banana）」时，对任一 ≥2 具名角色同框、且未声明多主体策略（多参考/主体库/角色ID/Seedream/Nano Banana）也未登记「分别出图+合成」降级的镜头 **升 🔴 BLOCK**（单图只锁一个主体、第二人必随机重画）。有原生主体能力的后端（Seedream/可灵/Sora）按 🟡 WARN，不过度阻断。逃生门：本镜显式登记「分别出图+合成」降级即放行。能力判定走契约 `persistent_subject`，不 hardcode 后端名。

**容错铁律**：只报"真问题"。轻微主观偏好不入报告（等同 n2d 出图的「筛选宽容铁律」、novel-review 的容错铁律）——否则噪声淹没硬伤。

---

# 模式②：流程自审（让产线自我优化）

把"我这次手动做的 n2d 复盘"固化成可复跑流程。**节律**：用户主动要 / 每隔一批集 / 接了新视频·图·配音模型时跑一次。详细步骤见 `references/self_audit.md`，要点：

0. **本地静态自审**：先跑 `python3 skills/n2d-review/scripts/self_audit.py [--json]`。它不联网、不改文件，检查 `_进度.md` 并发安全、gate 单入口、横切覆盖率、行业基准外置、生图后端白名单文档一致性和文档体量；0 block / 0 warn 才进入市场对标。
   > 注：`self_audit.py` 是 **n2d 线特有的产线治理脚本**（检查的是 n2d 流水线专属约束）。同构的 `novel-review`/`mv-review`/`song-review` 模式② 目前只有联网对标，无对应本地静态自审脚本——四线共享的是 `references/self_audit.md` 工艺，不是这个脚本。
1. **拉基准**：联网搜当前（带年月）AI 漫剧/短剧主流做法，分三轴取证——**一致性**（定妆/参考/相似度 KPI、多参考/多视图/LoRA、同一生图后端贯穿）、**效率**（成本/周期/批量）、**可控性**（口型/音画/节奏工具）+ 各 stage 模型演进（图/视频/配音 SOTA）。
2. **对照**：逐 stage 把基准 vs `n2d-*/SKILL.md` + `n2d/Q&A.md` 比，找**真差距**（已做的别重复立项）。
3. **差距清单**：每条 = 差距 + 证据（带来源链接·日期）+ 落到哪个 skill 哪段 + 优先级（must/optional）+ 是否可脚本化。
4. **起草**：高价值项直接起草 `Q&A` 新条目 + 建议 edit；**改任何 skill 必同步 `skills/README.md` 索引**（仓库硬约定）。
5. **人确认后再写**：模式②**默认 report-only**，只产建议报告 + 可选 diff 草案，不自动改 skill / Q&A / 模型矩阵（改产线是高影响动作）。用户明确要求“落地/刷新矩阵/改 skill”后，才进入 `refresh-matrix` 或编辑模式。**报告是一次性的——只讲给用户、不在 skill 目录留存 `_流程自审_*.md` 这类存档**（已 gitignore）。**每次自审/重审都从头按本流程重跑**（拉基准→对照→差距），**绝不读旧报告当捷径**——市场会变，旧结论可能已过时或已落地。

> **防过期铁律**：市场建议带"采集日期 + 来源链接"，旧建议可能已被采纳或过时——写进来前先核对当前 skill 是否已有（本 skill 自己也按此自查）。

---

## 详细参考
- 作品质检两层维度全清单（看什么 + 定级 + 怎么判）：`references/checklist.md`
- 流程自审操作手册（拉基准 / 对照 / 起草）：`references/self_audit.md`
- P0/P1/P2 算法一致性：`scripts/semantic_continuity.py`（语义谱系 Diff） / `scripts/state_continuity.py`（动态百科·状态哨兵） / `scripts/state_ledger_build.py`（从 storyboard 构建跨集视觉状态账本） / `scripts/multimodal_consistency.py`（视觉语义/道具 embedding 离群）
- 各轴 SOTA vs n2d 默认 vs 升级触发（防过期快照；report-only 只给刷新建议，用户确认后再改）：`n2d/references/模型矩阵.md`
- 定妆变更影响扫描（崩脸/换装重抽后，列出引用该资产的下游镜头一并重出）：`n2d-image/scripts/asset_impact.py`
- 正向标准（镜头空间 / 时间留存）：`n2d-script/references/分镜语法.md` + `n2d/references/导演节奏.md`
- 一致性全链：`n2d-image/references/角色一致性checklist.md`
- 角色身份闭环 + 跨集漂移报表：`n2d-identity/SKILL.md`
- 翻车修正沉淀：`n2d/Q&A.md`

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
| 审完没有机器分 | 跑 `n2d-score`，让评分维度、visual checks 和回流 stage 进入 `生产数据/score_第N集.json` |
| 批量审片只看文本报告 | 跑 `n2d-review-ui` 生成 `review_ui_第N集.html/json`，用画布同时看首尾帧、clip、接缝、定妆参考、QA flag 和机器分 |
| 合规等成片后补救 | 先跑 `n2d-compliance` 建 `合规/compliance_manifest.json`，gate 会在 image/video/compose/review 前置阻断 |
