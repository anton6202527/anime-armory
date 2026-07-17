---
name: mv
description: 制MV 总调度 — 把歌曲或歌曲企划做成 AI 音乐 MV 视频，开跑先让用户选择【歌曲输入时序】：先传音乐（先有成品歌/用户音频，按真实 beatgrid 卡点）或后配歌曲（先做视觉蓝图 rough，后续补入定稿歌，再重跑卡点与正式 timeline）。产物落 创作区/制MV/曲名/(成片_MV.mp4)。**mv 视觉/剪辑阶段自包含**。读 _进度.md 路由到 mv-progress(只读进度) / mv-update(更新影响计划) / mv-craft(共享契约/AI披露) / mv-script(视觉蓝图) / mv-beat(卡点) / mv-plan(clip/timeline规划) / mv-image(出图) / mv-video(出视频+挑版) / mv-lyric-sync(卡拉OK字幕) / mv-compose(合成)。Use when given a finished song/audio, a song concept that needs MV planning before final audio, or an existing 创作区/制MV/曲名/ folder, or asked 做MV / 给这首歌做视频 / 先做MV后配歌 / 先传音乐做MV / 卡点 / 卡拉OK / MV出图出视频 / 合成成片. Triggers MV, 音乐视频, 做MV, 给歌做视频, 先传音乐, 后配歌曲, 卡点, 卡拉OK, 歌词字幕, MV出图, MV出视频, MV合成, mv.
---
> 规模统计：Skill 数 14 | SKILL.md 总行数 1128 | 目录文本总行数 19967

# mv — 制MV 生产线 · 总调度

把**一首歌或歌曲企划**做成 AI 音乐 MV 视频。**产物 = `创作区/制MV/<曲名>/成片_MV.mp4`**。开跑先确认 `歌曲输入时序`：
- **先传音乐**：用户已有成品歌/音频，先入 `歌/song.*`，再用真实 beatgrid 卡点，这是正式 MV 推荐路径。
- **后配歌曲**：用户还没最终音频，先做视觉蓝图 rough；等用户补入成品歌后，必须再跑 `mv-beat`，用真实节拍重算 `mv-plan`，再出图/视频/合成。

**完全独立铁律**：mv-* 的视觉、卡点、分镜、出图、出视频、字幕、合成阶段**自包含**。外部音频或歌词只作为用户提供的文件进入 `歌/song.*` + `词/lyrics.md`；mv 阶段仍用自己的脚本和契约。

**生产数据分层**：beatgrid、timeline、选择记录、正式画面与母版仍是 mv 自己的业务真值；`生产数据/artifact_catalog.json` 只是可删除、可重建的只读索引，缺失不得阻断 MV。机器真值优先 JSON/JSONL，人读 Markdown/HTML 放 `生产数据/views/`，可重建缓存单独标识。只持久化作品根相对路径；外部歌曲先复制进 `歌/song.*`，在 `_meta.json` 记录导入副本相对路径、原文件名和 SHA，不保存源机绝对路径。mv 不 import 仓库维护工具或其它系列实现，不回读其它系列状态/缓存。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/mv-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`MV用途`、`歌曲输入时序`、`MV视觉风格`、`MV规划粒度`、`卡点策略`、`生视频模型`（固定/兜底）、`生视频渠道`（固定/调用入口偏好）、`生图模型`、`生图渠道`（旧 `生图AI` 仅兼容）、`MV一致性增强`、`出视频规格`、`演唱口型`、`字幕语言`、`合成画幅`、`AI视觉使用披露`、`发行目标平台`。

> 作为生产线入口：开新曲（`创作区/制MV/<曲名>/`）时先问 `歌曲输入时序`（先传音乐 / 后配歌曲）和 `MV视觉风格` 等影响创作顺序/视觉方向的选择，再初始化 `<作品根>/_设置.md`。若用户已经给音频，可默认建议“先传音乐”；若用户只有歌名/歌词/视觉想法，可建议“后配歌曲”。视频后端不在立项时强问：`生视频模型` / `生视频渠道` 只在用户明确固定、账号/交付只能单后端、或 mv-video 探测不到可执行入口时再问并覆盖落档。旧 `生视频AI` 只作兼容 fallback。

## 作品根约定
```
创作区/制MV/<曲名>/
├── _进度.md / _meta.json / _设置.md
├── 视觉蓝图.md          MV 视觉概念：主角/场景/画风 + 段落↔画面映射 + 卡点策略
├── 歌/song.wav          输入成品歌（先传音乐时开局就有；后配歌曲时后续补入）
├── 词/lyrics.md         按需：字幕/正面唱演镜使用；纯器乐且无字幕/口型可缺省
├── 节拍/beatgrid.json   BPM + beat/downbeat + 段落图（mv-beat 产）
├── 分镜/                clip_plan + timeline_manifest + semantic_prompts + timeline.otio + animatic
├── 字幕/                karaoke.ass / lyrics.lrc（mv-lyric-sync 产）
├── 设定/                角色卡/场景卡/global_style（mv 自管，锁视觉一致性）
├── 出图/                mv-image：共享定妆 + 分段分镜 PNG
├── 出视频/              jobs_manifest.json + takes/ + 视频/（mv-video 产）
├── 制片/                shot list + picture lock + finishing checklist
├── 生产数据/            animatic/otio/image_qc/video_qc/delivery_qc/consistency findings
├── 合规/                AI视觉使用披露（mv-craft 产）
└── 成片_MV_master.mov + 成片_MV.mp4
```

## 阶段 + 路由

| 阶段 | skill | 产物 | 状态 |
|---|---|---|---|
| 共享契约/立项 | 本调度 + **`mv-craft`** | `_设置.md` + `_meta.json` + `_进度.md` + AI披露脚本 | ✅ 已建 |
| 歌曲入库/定稿 | 用户提供 / 本项目维护 | `歌/song.*` + `词/lyrics.md` | ✅ 已建（阶段顺序随 `歌曲输入时序` 变化） |
| 卡点 | **`mv-beat`** | `节拍/beatgrid.json`（BPM+beat+downbeat+能量+段落） | ✅ 已建（librosa） |
| 歌词时间轴（条件） | **`mv-lyric-sync`** | hash-bound 字符覆盖 `alignment_report` + karaoke.ass/lrc | ✅ 字幕或唱演口型启用时前置；纯器乐无字幕可跳过 |
| 剧本创作 | **`mv-script`** | `视觉蓝图.md` + 角色/场景设定 | ✅ 已建 |
| clip/timeline 规划 | **`mv-plan`** | `分镜/clip_plan.json` + `timeline_manifest.json` + prompt 包 | ✅ 已建 |
| 节奏预检 | **`mv-score`** | 绑定 plan/beatgrid/song 的 deterministic receipt | ✅ 正式付费前必有；主观阈值仅显式选择时生效 |
| 出图 | **`mv-image`** | `出图/`（共享定妆 + 分段分镜 PNG） | ✅ 已建（生图 CLI） |
| Animatic/Picture Lock | **`mv-craft`** | 可播放 animatic + OTIO + 绑定 hash 的人工锁版 | ✅ 已建（正式出视频前强制） |
| 出视频 | **`mv-video`** | `出视频/jobs_manifest.json` + `sequence_units` + `takes/` + `视频/`（按段落+卡点挑版） | ✅ 已建（生视频 CLI/登记脚本） |
| 合成/交付 | **`mv-compose`** | ProRes/PCM 母版 + BT.709 MP4 + delivery QC + provenance/C2PA 接口 | ✅ 已建（自包含 ffmpeg） |
| 质检/自审(横切) | **`mv-review`** | `consistency_findings.json` + 双模 QA：作品质检（视觉一致性/卡点/字幕/音画合成/合规）+ 流程自审 | ✅ 已建（机检+人判，不生产只审） |

| 用户输入 | 路由到 |
|---|---|
| 有成品歌/用户音频，要立项做 MV | 本调度选择 `歌曲输入时序=先传音乐`，建 `创作区/制MV/<曲名>/`（拷入歌+词）→ `mv-beat` |
| 还没有歌，但想先定 MV 视觉 | 本调度选择 `歌曲输入时序=后配歌曲`，先 `mv-script` 做 rough 视觉蓝图；随后等用户补入成品歌，再回 `mv-beat` |
| 要分析卡点 | `mv-beat` |
| 要按歌自动拆 clip / 生成时间线 | `mv-plan` |
| 已有分镜，要评估视觉概念与节奏 | `mv-score`（生成前打分） |
| 要给 MV 出画 | `mv-image`（出图）→ `mv-video`（出视频）；整首当一个"作品"，段落≈分镜组 |
| 要卡拉OK字幕 | `mv-lyric-sync` |
| 素材齐了要合成成片 | `mv-compose` |
| 审 MV / 卡点对账 / 字幕检查 / 成片体检 / 流程自审 | `mv-review`（成品后审，出定位报告） |
| 给了 `创作区/制MV/<曲名>/` 没说动作 / 问进度或下一步 | `mv-progress`（只读扫描 `_进度.md`，报进度 + 建议下一步） |
| 问 skill 更新是否影响本 MV / 要返工计划 / 重审重评前先看范围 | `mv-update`（只写更新影响计划和基线，不改素材/视频/进度） |

> **先传音乐推荐顺序**：成品歌（及按需歌词）入库 → 立项 → 卡点并具名确认 timing → 按需歌词强制对齐 → 视觉蓝图 → timeline + 全量语义分镜 → 节奏预检 → 出图/QC/生成收据 → 真实 animatic/OTIO/picture lock → 视频评分挑版/逐缝语义签收 → 母版/派生交付 → provenance/总审。纯器乐且设置为“无字幕+关闭口型”时跳过歌词时间轴。

> **后配歌曲推荐顺序**：mv-craft 立项/选择 → mv-script rough 视觉蓝图/设定 → 用户补入成品歌+歌词 → mv-beat + mv-lyric-sync → mv-script 按真实 beatgrid 复核 → mv-plan 全量语义时间线 → mv-score → 出图/QC → animatic/OTIO/picture lock → 视频任务/挑版 → 合成 → AI使用披露/质检。**未补最终音频前不得跑 mv-plan / mv-image / mv-video / mv-compose 的正式产物**。

> 每阶段“凭什么通过、谁签、失败回哪一级”的单一说明见 `mv-craft/references/production-standards.md`。导演视角负责创意与镜头，但剪辑、音乐时间、连续性和交付 QC 是独立责任维度，不能合并成一句“专业导演已看过”。

> **mv-image/mv-video 是 mv 自己的视觉 skill**。两层定妆、尾帧接力、出图前一致性包和视频动作模板化都在 mv 家族内自持。

> **MV 版一致性边界**：除身份、主色、画风和母题外，还锁状态变体、服装/道具状态、场景拓扑、屏幕方向/视线、动作速度/相位、光线方向、字幕安全区、色彩管理、主歌轨 hash 与交付来源链。主角/主唱最严，段落场景中等，特效转场最宽松。
> **MV 出图一致性增强**：组图前 `mv-image` 必须提示 `MV一致性增强` 四档：共享定妆+锚点（默认）、指定参考图、后端主体库、+LoRA。MV 不默认训练 LoRA；只有用户已有或明确授权的 LoRA 资产才接入。

> **MV 动作/运镜知识库**：炫酷动作优先从 `mv-video/references/action_knowledge.md` 选动作家族，运镜优先从 `mv/references/运镜/manifest.json` 选结构化词，再写进 `clip_plan.json` 的 `action_family/action_peak/visual_motif/transition_motif/shot_design.camera_movement`。原则是“一 clip 一个主动作 + 一个主运镜，动作峰值踩 beat/downbeat”，避免空泛写“炫酷运镜”。

## 合法性
- 仓库内用户直接提供/创作的歌曲默认同源原创、权利人自有；明确为第三方、翻唱、克隆嗓音或外部参考时，必须切换到对应授权路径并留证。
- 正式付费生成前用 `mv-craft/scripts/rights_manifest.py` 记录歌曲、视觉参考、真人肖像、品牌、场地和编舞权利状态；该记录不替代平台/地区专业审查。
- AI 标识/AI 披露/水印不再由本流水线处理：mv-compose 出成片即收尾，不生成可见水印、不调用任何 watermark skill；若投放地区/平台需要 AI 标识或披露，由使用方在工具之外按当地法规自行处理。

## 持续改进
工艺/翻车 → 写进对应 mv-* skill 的 `references/`。**新增/改 mv-* skill 后同步更新 `skills/README.md`。**

## 常见错误

| 错误 | 纠正 |
|---|---|
| 后配歌曲路线在未定稿音频前就正式拆 timeline/出视频 | 只能先做 rough 视觉蓝图；最终歌入库后必须跑 `mv-beat` + `mv-plan` |
| 将半成品或尚未完成创作的音频当成先传音乐路线送入制MV管线 | 先传音乐路线要求音频是最终成品；若还会改歌，请选后配歌曲 |
| 跳过视觉蓝图直接批量生成片段 | 分镜与生成必须要有总体视觉规划和卡点策略引导，不要无脑调用 `mv-video` |
| 交付前遗漏 AI 使用留痕 | 在交付最终 MP4 之前通过 `mv-craft` 完成 AI 使用说明和披露登记（项目留痕）；AI 标识/披露/水印不由本流水线处理，按各平台/地区法规自行处理 |
