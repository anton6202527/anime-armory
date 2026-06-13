<!-- 手工维护，勿用 codex /init（或任何 agent 的 init）覆盖。本文件是跨工具的工具中立入口，Codex/Cursor 等会按约定名自动读取。 -->

# AGENTS.md — 给 AI 编码/创作 agent 的入口

> 本文件是**工具中立**的项目说明，供任何 AI agent（Cursor / Cline / Gemini-CLI / Codex / Copilot / Claude Code…）或人进仓库时快速上手。不绑定任何特定 AI。

## 怎么用这些 skill（任何 agent 通用）

1. **发现**：读 [`skills/README.md`](skills/README.md)（分类总览）和每个 `skills/<name>/SKILL.md`。
   - SKILL.md 的 frontmatter `description` + 正文 `Triggers`/`Use when` **就是路由依据**：用户意图命中哪个，就用哪个。
2. **执行**：照 SKILL.md 的步骤做事；需要算力的步骤跑 `skills/<name>/scripts/` 下的脚本。
3. **脚本是通用的**：纯 Python / bash，只调通用工具（`ffmpeg` / `librosa` / `whisper` / `yt-dlp` / 生图生视频 CLI 等），**无任何某家 AI 的专有 API**，谁都能直接执行。引用路径用中立的 `skills/...`。
4. **写法**：对用户输出“下一步”或推荐调用某个 skill 时，一律写裸 skill 名（如 `n2d-image`），**不要**写成 `/n2d-image`。有些 AI agent 会把 `/...` 当内置斜杠命令并报 `Unrecognized command`。

> Claude Code 用户：`.claude/skills → ../skills` 是软链，会自动发现并按触发词路由，无需手动指。其他工具：把用户意图对照下表/各 SKILL.md 的 Triggers 自行选 skill。

## 选哪个 skill（按意图）

| 用户想做 | 入口 skill（总调度，会再分诊到子 skill） |
|---|---|
| 写/改/续/扩/缩一本小说，或不知用哪个 | **`novel`**（分诊到 novel-create/fetch/spinoff/rewrite/continue/expand/condense/title/review/craft） |
| 把小说做成 AI 漫剧/短剧（分镜/配音/出图/出视频/合成） | **`n2d`**（分诊到 n2d-script/voice/image/video/compose） |
| 直接创作/编辑一首带人声的歌 | **`song`**（可从主题直接创作，也可改词、改曲风、重生成、挑版；过程中分诊到 song-lyrics/song-score/song-compose/song-cover/song-review/song-craft） |
| 把成品歌或歌曲企划做成音乐 MV（先传音乐/后配歌曲、卡点、出图出视频、卡拉OK、合成） | **`mv`**（先选歌曲输入时序，分诊到 mv-script/beat/plan/image/video/lyric-sync/compose） |
| 把客户需求/品牌产品做成 AI 广告片（创意/脚本/配音/分镜/出图出视频/剪辑包装/成片） | **`ad`**（分诊到 ad-craft/concept/script/voice/image/video/compose/review；不拆集，多时长 cutdown + 多比例交付） |
| 查看任意项目进度/下一步，或在仓库根汇总所有项目 | **`progress`**（只读分发到各产线自己的进度脚本，不回写 `_进度.md`） |
| 检查 skill 更新是否影响项目、生成重制计划 | **`update`**（n2d 支持 skill 快照比对 + 最小重制计划；n2d/mv/ad 支持少量图片/视频选择性刷新计划；song/novel 明确转线 no-op） |
| 给视频/图片换脸（n2d/mv/ad 各自一份） | 本线的 **`<line>-video-faceswap`** / **`<line>-image-faceswap`**（如 `n2d-video-faceswap`；带合规闸门） |
| 给图/视频加水印（合规 AI 标识 / 品牌 logo·账号） | 本线的 **`<line>-watermark`**（如 `mv-watermark`；图视频同工具；AI 标识只加不去） |
| 清理 / 瘦身生成垃圾 | **`shared-cleanup`**（仓库级 dev 工具；默认扫 `skills/`，可 `--repo` 扫全仓；确认后只删低风险缓存/临时文件并统计节省空间） |
| 刷新选择点候选（模型/后端清单是否过期）| 本线 **`skills/<line>/_lib/refresh.py`**（仅 n2d/ad 有候选源；机检快照新鲜度 → 实时搜索核验 → 改候选 + bump 采集日期 + 落 provenance；守各线策略差异不合并） |

> 五条线**互不依赖、各自自包含、可单独打包分发**（2026-06 全独立化：删 `skills/common/`，管道模块 vendored 进各线 `skills/<line>/_lib/`；换脸/水印各线各带 `<line>-watermark`/`<line>-*-faceswap`，n2d/mv/ad 有、song/novel 无）。换脸打标调**本线** `<line>-watermark`。独立性由 `tools/check_independence.py` 闸门守。拍广告(`ad-*`)是第五条生产线：客户需求→创意→脚本→配音→分镜→定妆/出图→出视频→剪辑包装→AI披露→质检，**不拆集**（多时长 cutdown + 多比例走交付件矩阵），内置《广告法》违禁词机检。

## 必须遵守的项目约定

- **进度**：每个作品根有 `_进度.md`（状态机）。**先读它**判断走到哪一步、下一步做什么；做完**回写**。
- **偏好/选择点**：凡"让用户选"的点（平台/后端/分辨率/音色…），首次问一次→写进 `<作品根>/_设置.md`→同项目沉默沿用。**别在 skill 代码里写死**唯一路径。
- **候选项更新 + 适配层**：选择菜单只是带日期的候选快照，不是真理。涉及模型/平台/法规/价格/规格等会变的信息，执行前应按需要用专业知识、项目 references、官方文档或实时搜索核验并刷新候选；用户永远可以手输 `自定义`/`manual`。skill 执行时不要直接依赖菜单文案，而要经适配层把用户选择归一到能力、参数、CLI/API、降级方案和合规闸门；适配不了就停下说明缺口，不要偷偷换路。机检与落地工具（仅 n2d/ad 有候选源）：`python3 skills/<line>/_lib/freshness.py` 报哪些候选快照过期；同目录 `refresh.py` 跑「搜索核验 → 改候选 → bump 采集日期 + 落 provenance」。各线策略差异是故意的（如 ad 禁即梦 ≠ n2d 放行即梦官方），分别刷新、绝不合并候选清单。
- **合规闸门（硬性）**：换脸仅限本人/已授权/合成脸 + 强制 AI 标识；克隆真人歌手嗓需授权（2026 opt-in），未授权拒做。词曲/小说默认公版 / 自有 / 已授权。
- **改了 skill 集合**（增/删/改职责）→ 必须同步更新 `skills/README.md` 索引。
- **本机工具/环境**（macOS）：`ffmpeg`（精简版，**无 libass/drawtext**，字幕走 Pillow 渲 PNG + overlay）；conda 环境 `cosyvoice`(含 librosa/whisper)、`acestep`(本地出歌)、`fish-speech`、`facefusion`；系统 Python 3.14 + PEP668 装不了重依赖，音频类用上述 conda env。踩坑细节见各 skill `references/`。

## 不在 git 里的东西

- 各 AI 自己的私有配置（如 `.claude/`、`.cursor/` 等）与用户私有偏好默认不进共享 skill。
- 大模型权重、conda 环境在仓库外（`~/ACE-Step`、`~/CosyVoice` 等），按 `references/` 安装说明本地准备。
