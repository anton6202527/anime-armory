---
name: mv-review
description: 制MV 质检 + 流程自审（mv 写歌→制MV 生产线的 QA 环节，不生产内容只审）。双模——模式①「作品质检」：对一支 MV 的产物做体检（规划：clip_plan/timeline/jobs 对账；视觉一致性：主角崩脸/场景漂移/画风跳变；卡点节奏：clip 时长对齐 beatgrid downbeats·不等长·副歌密 verse 疏·爽点对鼓点·clip 总时长≈歌长；卡拉OK字幕：占位未精修/时间越界/重叠/行数对账/对齐报告；音画合成：成片时长≈歌长·画幅符 _meta.aspect·有音轨；AI 视觉使用披露；运镜服务节奏；换脸合规 AI 标识+授权），机检+人判，出严重度分级·定位到 Clip/段落/时间码的报告。模式②「流程自审」：联网拉当前 AI MV/音乐视频市场基准，对照 mv 各 skill + references，产出"差距清单 + 该改哪个 skill 哪段"的优化建议。Use when asked to MV质检, 审MV, 查崩脸, 卡点对账, 卡拉OK字幕检查, MV成片体检, 验收MV, 流程自审, mv 还能优化啥, mv-review. Triggers MV质检, 审MV, MV审片, 崩脸, 卡点对账, 卡点检查, 卡拉OK检查, 字幕越界, MV成片体检, MV验收, 流程自审, 流程优化, 自我优化, mv-review, QA.
---

# mv-review — 制MV 质检 + 流程自审

不生产内容，只**审**。是 `mv`（制MV 生产线）家族的 QA 环节，与 `n2d-review`（审漫剧）/ `novel-review`（审小说）/ `song-review`（审歌）同构。两个模式：

- **模式①「作品质检」**——审**一支 MV 的产物**（`制MV/<曲名>/`）：扫问题 → 定位（Clip / 段落 / 时间码）→ 定级 → 给修法 → 出报告。出成片前 / 各阶段闸门跑。
- **模式②「流程自审」**——审**制MV 流水线本身**：联网拉市场基准，对照 `mv-*` 各 skill + references，产出"差距清单 + 建议改哪个 skill 哪段"。让"整套流程不断自我优化"成为一条可复跑命令。

> MV 三大验收维：**视觉一致性 · 卡点节奏（MV 的命）· 音画合成与合规**。卡点是 MV 区别于漫剧的核心——clip 时长必须踩 beatgrid，不能等长。正向标尺：卡点 = `mv-beat/SKILL.md` 卡点原则；运镜 = `mv-video/references/prompt_format.md`；一致性 = `mv-image/references/prompt_format.md`；合成 = `mv-compose/references/usage.md`。

---

# 模式①：作品质检

## 机检 / 人判分工（照搬 n2d-review 的成熟做法）

- **机检（确定性，先跑）**：`scripts/mv_check.py <制MV作品根>` —— 秒级出确定性问题：
  - **卡点**：`节拍/beatgrid.json` 存在/可解析、BPM 合理（半速/倍速嫌疑）、beats/downbeats 单调递增、`歌/song.*` 时长 vs beatgrid.duration 一致。
  - **规划**：`分镜/clip_plan.json` / `timeline_manifest.json` 存在可解析、clip_id 不重复、timeline 与 plan 对账、timeline selected video 是否存在。
  - **视频任务**：`出视频/jobs_manifest.json` 存在可解析、已选 take 是否真的落到 `出视频/视频/Clip_XXX.mp4`。
  - **clip 节奏**（需 `ffprobe`，缺则显式跳过）：每个 `出视频/视频/*.mp4` 时长、**clip 是否疑似等长（不卡点）**、clip 总时长 ≈ 歌长。
  - **卡拉OK字幕**：`字幕/lyrics.lrc` / `karaoke.ass` 解析、占位未精修、时间单调/不重叠、**时间戳越界（超歌长）**、字幕行数对账、`alignment_report.json` warnings。
  - **音画合成**（需 `ffprobe`）：`成片_MV.mp4` 存在、时长 ≈ 歌长、分辨率符 `_meta.aspect`、**有音轨**（MV 没声音=废）。
  - **AI 视觉使用披露**：已有成片时检查 `合规/ai_usage.json` 是否留痕、枚举是否有效。
  - **完整性/对账**：词/歌/beatgrid/出图/clip/成片 产物快照、`_meta.has_song/has_lyrics` vs 实际文件、段落数 vs `_meta.structure`。
  ```bash
  python3 <skill>/scripts/mv_check.py <制MV作品根>          # 人读
  python3 <skill>/scripts/mv_check.py <制MV作品根> --json   # 喂回 LLM 汇总
  ```
  > `ffprobe` 缺失时，clip/成片 的时长·分辨率·音轨检查**显式标「跳过」**，绝不静默略过（同 n2d 脸相似度库的处理）。`song.wav` 时长优先走标准库 `wave`，mp3/m4a/flac 走 ffprobe。

- **人判（判断题）**：机检覆盖不了的语义维度。逐维见 `references/checklist.md`。
  - **崩脸 / 场景漂移 / 画风跳变用图判**：把 `出图/段落/图片/镜头*.png` 与 `出图/共享/图片/定妆_*.png` **并排读图比对**（脸型/发型/服色/画风锚点）；装了 `face_recognition`/`insightface` 可给相似度分，缺库则人判兜。
  - **接缝跳切用图判（逐接缝过）**：取相邻 clip 的 Clip K 末帧 vs Clip K+1 首帧**并排读图**，对照 `分镜/clip_plan.json` + `timeline_manifest.json` 的接缝契约：① 标 `need_end_frame=true`/连续硬切但两帧姿态/站位/视线/光线明显对不上 → 跳切/闪烁；② 标 `need_end_frame=true` 却没出 `_end.png`（mv-image 漏做）→ 接力断链；③ 服装/发型/道具在接缝处突变 → 接缝崩。**注意 MV 容差更宽**：副歌卡点硬切处的视觉跳变若踩准鼓点、是有意冲击，**不算问题**（卡点切本就允许画面跳）；只标"非卡点切又接不住"的接缝。修法：回 mv-image 补尾帧 / 回 mv-video 用首尾双帧重出该 clip。
  - **运镜与动作服务节奏**：副歌快推/环绕、verse 缓推/跟、bridge 换机位、爽点对 downbeat 同帧砸下；动作家族、动作峰值、转场母题对 `mv-video/references/action_knowledge.md` + `prompt_format.md`。只写“炫酷动作”但没有可执行动作链，标为建议级。
  - **单曲视觉一致性**：审 `mv-image/references/visual_consistency.md` 的身份锚点、主色、段落 look、母题、`reference_inputs` 是否贯穿；若 `_设置.md` 启用了指定参考图、后端主体库或 `+LoRA`，prompt 必须登记路径/主体 ID/LoRA trigger+底模+授权说明。MV 不要求跨集状态，但一支歌内不能换脸换主画风。
  - **卡点体感**：机检给"clip 是否对齐 downbeat"的客观判断，**踩得爽不爽**由人判（看成片副歌切点是否砸在鼓点）。
  - **换脸合规**：若用了 `mv-video-faceswap`——AI 标识水印在否、未被裁、源脸授权。

## 工作流（模式①）

0. **定位 + 确认范围**：作品根 = `制MV/<曲名>/`。读 `_进度.md` 知各阶段进度（未到的阶段不当问题报，如还没合成就别报"缺成片"）。
1. **跑机检** → 确定性问题清单（卡点 + clip + 字幕 + 合成 + 对账）。
2. **人判**：对照 `references/checklist.md` 逐维，**只记真问题**，每条带证据（Clip / 段落 / 时间码 / 图路径）。崩脸并排读图。
3. **汇总报告** → 写 `制MV/<曲名>/_质检.md`：按严重度排序，每条 = 位置（`Clip07` / `[chorus]@时间码` / 文件）+ 维度 + 问题 + **修法** + 证据。附"健康度概览"表。
4. **修复回流（关键）**：MV 的修法**回源头改、重跑回流**，不在成片 MP4 上硬剪——和漫剧"回源头重跑"同理。报告里每条修法都指明**回哪个 skill 重跑**（如"崩脸→回 `mv-image` 重出该镜""clip 不卡点→回 `mv-video` 按 beatgrid 重定 clip 时长""字幕越界→回 `mv-lyric-sync` 重对齐""成片无音轨→回 `mv-compose` 重铺歌轨"）。

## 严重度（定级 + 容错铁律）

| 级别 | 含 | 处置 |
|---|---|---|
| 🔴 阻断级 | 崩脸/角色断层、字幕占位未精修、**成片无音轨（歌没进去）**、beatgrid 损坏不可解析、换脸 AI 标识缺失/未授权、成片缺失但进度标已合成 | **必改**，回源头重跑 |
| 🟡 建议级 | 场景轻漂、画风跳变、**非卡点切接缝跳切/接力断链**、**clip 疑似等长不卡点**、clip/成片总时长 vs 歌长差大、分辨率不符画幅、BPM 半/倍速嫌疑、字幕时间越界/重叠、运镜不服务节奏、爽点没对 downbeat | 建议改 |
| 🟢 润色级 | 个别运镜偏好、转场差一拍、字幕位置微调 | 可改可不改 |

**容错铁律**：只报"真问题"。轻微主观偏好不入报告（等同 n2d-review 容错铁律、mv-image 的"筛选一致优先"）——否则噪声淹没硬伤。

> **职责边界**：输入歌本身的深度体检（削波/静音/可唱性/词押韵）属 `song-review`，不在本 skill 重复——mv-review 只关心"歌轨进没进成片、时长对不对、卡点踩没踩准"。

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
- 输入歌体检（不在本 skill 重复）：`song-review`

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
| 重复审输入歌的音质/词 | 那是 song-review 的活；mv 只审歌轨进没进、卡点对不对 |
| 模式②直接改 skill | 默认只出建议报告，人确认后改；改 skill 必同步 README 索引 |
