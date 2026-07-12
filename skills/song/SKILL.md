---
name: song
description: 写歌总调度 — 直接创作或编辑一首带人声的歌（词 + 曲 + 演唱）。支持从主题/几个字/曲风想法从零创作，也支持在已有 `创作区/写歌/<曲名>/`、歌词、曲风、半成品音频基础上改词、改结构、改曲风、重生成、多版挑版、换声、质检、进度查询和 skill 更新影响检查。产物落 创作区/写歌/<曲名>/(词/lyrics.md + 歌/song.wav)。创作过程中可按需调用 song-progress(只读进度) / song-update(更新影响计划) / song-lyrics(作词/改词) / song-score(歌词体检) / song-compose(作曲+演唱与多版挑版) / song-cover(翻唱/换声) / song-review(质检) / song-craft(合约与AI使用披露)。Use when asked to 写首歌 / 做首歌 / 从零写歌 / 创作歌曲 / 改这首歌 / 改词 / 改曲风 / 重生成 / 我有个歌的点子 / 作词作曲. Triggers 写歌, 做歌, 写首歌, 创作曲, 创作歌曲, 改歌, 改词, 改曲风, 重做这首歌, 作词作曲, 原创歌曲, 我想写首歌, song, write a song.
---
> 规模统计：Skill 数 11 | SKILL.md 总行数 657 | 目录文本总行数 9850

# song — 写歌创作线 · 总调度

把"主题 / 几个字 / 曲风想法"直接创作成**一首成品歌**（词 + 曲 + 演唱），也可以对已有歌词、曲风、半成品音频或 `创作区/写歌/<曲名>/` 项目做编辑迭代。**完全独立、自包含**，只用通用工具（Suno / ACE-Step / RVC 等不是 skill）。

总调度不是一次性黑盒：创作过程中可以按实际需要调用 `song-craft` 做 A&R 简报、参考边界、旋律/和声草图、权益元数据、发布包和合规留痕，调用 `song-lyrics` 改词/补 hook，调用 `song-score` 做歌词体检，调用 `song-compose` 生成或重生成多版歌曲并结构化试听挑版，调用 `song-cover` 换合法音色，调用 `song-review` 做成品质检/母带检查，发布后调用 `song-feedback` 回灌真实数据。

产物落 **`创作区/写歌/<曲名>/`**（`词/lyrics.md` + `歌/song.wav`）。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/song-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`歌曲用途`、`目标时长`、`语言`、`BPM/速度`、`调性`、`作曲后端`、`生成版数`、`挑版策略`、`翻唱后端`、`演唱音色(合规·需声明)`、`AI音频使用披露`、`发行目标平台`。
> 作为创作线入口：开新曲（`创作区/写歌/<曲名>/`）时按全局默认初始化 `<作品根>/_设置.md`。

## 作品根约定
```
创作区/写歌/<曲名>/
├── _设置.md / _进度.md / _meta.json
├── 创作蓝图.md      主题/曲风/情绪/平台/演唱音色
├── 创作/            song_brief.json（A&R 简报）
├── 词/lyrics.md     结构化歌词（[verse]/[chorus]/[bridge]…）
├── 歌/              song_form.json + compose_task.md + takes_manifest.json + take_review.json + revision_jobs.json + takes/ + song.wav
├── 混音/            pre_master.wav + mix_signoff.json + master_check.json
├── 评审/            quality_gate_*.json + consistency_findings.json / consistency_findings.md
├── 合规/            AI使用说明.md / ai_usage.json / rights_metadata.json / split_sheet.md
├── 发行/            release_metadata.json + release_metadata_check.json + feedback_summary.json
├── 素材/            参考曲/风格样本/已有半成品
└── 导出/            master.wav + master_delivery.json + release_pack.json
```

## 阶段 + 路由

| 阶段 | skill | 产物 | 状态 |
|---|---|---|---|
| A&R 简报 + 参考边界 | **`song-craft`** | `创作/song_brief.json` + `素材/reference_pack.json` | ✅ 已建（目标听众、核心承诺、参考曲边界） |
| 立项 + 词 | **`song-lyrics`** | 创作蓝图 + `词/lyrics.md`（结构化、可唱、押韵） | ✅ 已建（零依赖） |
| 歌词体检(可选) | **`song-score`** | 结构与押韵分析报告 | ✅ 已建（音频生成前拦截平庸词） |
| 旋律/和声草图 | **`song-craft`** | `歌/song_form.json` + `chord_sheet.md` + `topline_notes.md` | ✅ 已建（作曲前控制曲式与 topline 方向） |
| 作曲任务包 + 多版挑版 | **`song-compose`** | schema v3 输入 hash 合同 + 后端编译字段 + 六维 `take_review` + selection receipt + `pre_master.wav` | ✅ 已建（前置/挑版双闸门） |
| 翻唱 / 换声(可选) | **`song-cover`** | 换音色人声 | ✅ 已建（RVC，带合规闸门） |
| 质检 / 母带检查 / 自审(横切) | **`song-review`** | 作品质检 + consistency findings + BS.1770 响度/true-peak 报告 | ✅ 已建（机检+人判，不生产只审） |
| 合约 / 合规 / 发布包(横切) | **`song-craft`** | AI 披露 + 条件式 rights check + release metadata + hash-bound release pack | ✅ 已建（work/resource/release 元数据分层） |
| 发行反馈(可选) | **`song-feedback`** | `发行/feedback_summary.json` + 回测报告 | ✅ 已建（真实播放/完播/收藏/分享/评论回灌） |

| 用户输入 | 路由到 |
|---|---|
| 没有词，只有想法 | `song-lyrics` |
| 已有歌词，要改词/改结构/补 hook | `song-lyrics`，必要时再跑 `song-score` |
| 已有曲风/参考方向，要直接创作歌曲 | 先 `song-lyrics` 固化蓝图和歌词，再 `song-compose` 多版生成 |
| 已有词，要评估能不能出好歌 | `song-score`（分析结构与押韵） |
| 已有词，要生成带人声的歌 | `song-compose` |
| 已有歌但不满意，要改曲风/重生成/挑新版 | `song-compose`（保留 take manifest，多版登记评分后重选） |
| 已有歌，要换音色/翻唱 | `song-cover` |
| 要发布/交平台前补 AI 使用留痕 | `song-craft/scripts/ai_usage.py` |
| 要正式发行/交付前补权益、split、ISRC/ISWC、发布包 | `song-craft/scripts/rights_metadata.py` + `release_pack.py` |
| 审歌 / 查词 / 可唱性·出歌·合规体检 / 流程自审 | `song-review`（成品后审，出定位报告） |
| 已发布或小流量测试后，要导入播放/完播/收藏/分享/评论数据 | `song-feedback` |
| 给了 `创作区/写歌/<曲名>/` 没说动作 / 问进度或下一步 | `song-progress`（只读扫描 `_进度.md`，报进度 + 建议下一步） |
| 问 skill 更新是否影响本曲 / 要返工计划 / 重审重评前先看范围 | `song-update`（只写更新影响计划和基线，不改歌词/音频/进度） |

> 推荐顺序：**A&R 简报/参考边界 → 词 → prosody/体检 → 曲式/和声草图 → compose gate → 多版生成 → 六维盲听 → timecode 局部返修 → select gate →（可选换声）→ pre-master 人工表演/混音签核 → 24-bit delivery master → BS.1770 检查 → AI/rights/release metadata → hash-bound 发布包 → 同实验反馈 + Wilson 区间**。逐阶段标准见 `song-craft/references/production-standards.md`。

## 后端选型（song-compose 唱歌的声音 —— 装什么）
> **TTS（CosyVoice/FishSpeech）是说话，不能唱歌。** 唱歌走音乐生成模型或歌声转换。

| 路线 | 方案 | 装/要 | Mac |
|---|---|---|---|
| 云·最快 | **Suno / Udio** | 接账号/API | ✅ |
| 本地·主力候选 | **ACE-Step v1.5**（翻唱/50+语言） | pip+权重，官方支持 Mac/CUDA | ✅ |
| 本地·扩散 | **DiffRhythm 2**（出整首快） | pip+权重，偏 CUDA | ⚠️ |
| 翻唱换声 | **RVC / so-vits-svc** | WebUI+GPU | ⚠️ |

> 选型像 LoRA 那样先本地验证再定主力；MVP 先接 Suno 云。没有凭证/SDK 时，`song-compose/scripts/compose_song.py` 先生成 prompt 包和 take manifest，外部生成后再登记，不把某个云平台写成唯一执行路径。

## 合法性铁律
- 词/曲**原创** = 用户自有，天然合法。
- **克隆真实歌手嗓音**：2026 WMG×Suno / UMG×Udio 和解后转 **opt-in 授权**——需歌手授权。默认只用 **自有嗓 / 授权音色 / 合成音色**；未授权真人嗓 → 拒做。
- 翻唱已发行歌曲的**词曲版权**另属原作者，商用需授权。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 没有歌词直接让大模型唱 | TTS 只能说话，必须使用音乐生成大模型（如 Suno/Udio/ACE-Step 等）来完成带有旋律和人声的演唱 |
| 将已发行的商业歌曲未授权直接翻唱商用 | 如果是给他人做 MV，需注意词曲翻唱可能存在的版权风险，本调度线已设置合法性铁律 |
| 用一版生成结果就定稿 | 音乐生成方差大，务必走多版生成（takes manifest），让用户试听后挑版 |
