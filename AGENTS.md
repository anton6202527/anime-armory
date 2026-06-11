<!-- 手工维护，勿用 codex /init（或任何 agent 的 init）覆盖。本文件是跨工具的工具中立入口，Codex/Cursor 等会按约定名自动读取。 -->

# AGENTS.md — 给 AI 编码/创作 agent 的入口

> 本文件是**工具中立**的项目说明，供任何 AI agent（Cursor / Cline / Gemini-CLI / Codex / Copilot / Claude Code…）或人进仓库时快速上手。不绑定任何特定 AI。

## 怎么用这些 skill（任何 agent 通用）

1. **发现**：读 [`skills/README.md`](skills/README.md)（分类总览）和每个 `skills/<name>/SKILL.md`。
   - SKILL.md 的 frontmatter `description` + 正文 `Triggers`/`Use when` **就是路由依据**：用户意图命中哪个，就用哪个。
2. **执行**：照 SKILL.md 的步骤做事；需要算力的步骤跑 `skills/<name>/scripts/` 下的脚本。
3. **脚本是通用的**：纯 Python / bash，只调通用工具（`ffmpeg` / `librosa` / `whisper` / `yt-dlp` / 生图生视频 CLI 等），**无任何某家 AI 的专有 API**，谁都能直接执行。引用路径用中立的 `skills/...`。

> Claude Code 用户：`.claude/skills → ../skills` 是软链，会自动发现并按触发词路由，无需手动指。其他工具：把用户意图对照下表/各 SKILL.md 的 Triggers 自行选 skill。

## 选哪个 skill（按意图）

| 用户想做 | 入口 skill（总调度，会再分诊到子 skill） |
|---|---|
| 写/改/续/扩/缩一本小说，或不知用哪个 | **`novel-author`**（分诊到 novel-create/fetch/spinoff/rewrite/continue/expand/condense/title/review/craft） |
| 把小说做成 AI 漫剧/短剧（分镜/配音/出图/出视频/合成） | **`novel2drama`**（分诊到 n2d-script/voice/image/video/compose） |
| 直接创作/编辑一首带人声的歌 | **`song`**（可从主题直接创作，也可改词、改曲风、重生成、挑版；过程中分诊到 song-lyrics/song-score/song-compose/song-cover/song-review/song-craft） |
| 把成品歌做成音乐 MV（卡点/出图出视频/卡拉OK/合成） | **`mv`**（分诊到 mv-beat/image/video/lyric-sync/compose） |
| 给视频/图片换脸（公共，任何流程可调） | **`shared-video-faceswap`** / **`shared-image-faceswap`**（带合规闸门） |
| 给图/视频加水印（合规 AI 标识 / 品牌 logo·账号，公共） | **`shared-watermark`**（图视频同工具；AI 标识只加不去） |
| 清理 / 瘦身 `skills/` 里的生成垃圾 | **`shared-cleanup`**（默认扫描，确认后只删低风险缓存/临时文件） |

> 四条线**互不依赖、各自自包含**（mv-* 不复用 n2d-* 等）。`shared-*` 是公共能力；换脸打标调 `shared-watermark`。

## 必须遵守的项目约定

- **进度**：每个作品根有 `_进度.md`（状态机）。**先读它**判断走到哪一步、下一步做什么；做完**回写**。
- **偏好/选择点**：凡"让用户选"的点（平台/后端/分辨率/音色…），首次问一次→写进 `<作品根>/_设置.md`→同项目沉默沿用。**别在 skill 代码里写死**唯一路径。
- **合规闸门（硬性）**：换脸仅限本人/已授权/合成脸 + 强制 AI 标识；克隆真人歌手嗓需授权（2026 opt-in），未授权拒做。词曲/小说默认公版 / 自有 / 已授权。
- **改了 skill 集合**（增/删/改职责）→ 必须同步更新 `skills/README.md` 索引。
- **本机工具/环境**（macOS）：`ffmpeg`（精简版，**无 libass/drawtext**，字幕走 Pillow 渲 PNG + overlay）；conda 环境 `cosyvoice`(含 librosa/whisper)、`acestep`(本地出歌)、`fish-speech`、`facefusion`；系统 Python 3.14 + PEP668 装不了重依赖，音频类用上述 conda env。踩坑细节见各 skill `references/`。

## 不在 git 里的东西

- 各 AI 自己的私有配置（如 `.claude/`、`.cursor/` 等）与用户私有偏好默认不进共享 skill。
- 大模型权重、conda 环境在仓库外（`~/ACE-Step`、`~/CosyVoice` 等），按 `references/` 安装说明本地准备。
