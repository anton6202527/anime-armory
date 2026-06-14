<!-- 手工维护，勿用 codex /init（或任何 agent 的 init）覆盖。本文件是跨工具的工具中立入口，Codex/Cursor 等会按约定名自动读取。 -->

# AGENTS.md — 给 AI 编码/创作 agent 的入口

> 本文件是**工具中立**的项目说明，供任何 AI agent（Cursor / Cline / Gemini-CLI / Codex / Copilot / Claude Code…）或人进仓库时快速上手。不绑定任何特定 AI。

## 怎么用这些 skill（任何 agent 通用）

1. **发现**：读 [`skills/README.md`](skills/README.md)（分类总览）和每个 `skills/<name>/SKILL.md`。
   - SKILL.md 的 frontmatter `description` + 正文 `Triggers`/`Use when` **就是路由依据**：用户意图命中哪个，就用哪个。
2. **执行**：照 SKILL.md 的步骤做事；需要算力的步骤跑 `skills/<name>/scripts/` 下的脚本。
3. **脚本是通用的**：纯 Python / bash，只调通用工具（`ffmpeg` / `librosa` / `whisper` / `yt-dlp` / 生图生视频 CLI 等），**无任何某家 AI 的专有 API**，谁都能直接执行。引用路径用中立的 `skills/...`。
4. **写法**：对用户输出“下一步”或推荐调用某个 skill 时，一律写裸 skill 名（如 `n2d-image`），**不要**写成 `/n2d-image`。有些 AI agent 会把 `/...` 当内置斜杠命令并报 `Unrecognized command`。

仓库级维护工具不放在 `skills/`，统一放 `tools/`；例如清理工具见 `tools/shared-cleanup/SKILL.md`。

> Claude Code 用户：`.claude/skills → ../skills` 是软链，会自动发现并按触发词路由，无需手动指。其他工具：把用户意图对照下表/各 SKILL.md 的 Triggers 自行选 skill。

## 选哪个 skill（按意图）

| 用户想做 | 入口 skill（总调度，会再分诊到子 skill） |
|---|---|
| 写小说、导入源书、扩写/改写/续写/评分/审稿 | **`novel`**（分诊到 novel-create/fetch/rewrite/review/score 等） |
| 把小说做成 AI 漫剧/短剧（分镜/配音/出图/出视频/合成） | **`n2d`**（分诊到 n2d-script/voice/image/video/compose） |
| 写歌、改词、作曲、多版挑版、翻唱/换声、审歌 | **`song`**（分诊到 song-lyrics/compose/cover/review 等） |
| 给歌曲做 MV、卡点、出图出视频、卡拉 OK 字幕、合成 | **`mv`**（分诊到 mv-script/beat/plan/image/video/compose 等） |
| 做广告片、TVC、信息流广告、产品 demo、带货视频 | **`ad`**（分诊到 ad-concept/script/voice/image/video/compose/review） |
| 查看项目进度/下一步，或在仓库根汇总所有 n2d 项目 | **`n2d-progress`**（只读扫描 n2d 进度，不回写 `_进度.md`） |
| 修改/审计项目设置、选择点或全局默认 | **`n2d-settings`**（包住 `_设置.md` 读写/校验/重置/同步全局默认） |
| 检查 skill 更新是否影响项目、生成重制计划、只重出部分图片/视频 | **`n2d-update`**（skill 快照比对 + 最小重制计划；`media` 子命令做少量图片/视频选择性刷新计划） |
| 清理 / 瘦身生成垃圾 | **`tools/shared-cleanup`**（仓库级 dev 工具；默认扫 `skills/`，可 `--repo` 扫全仓；确认后只删低风险缓存/临时文件并统计节省空间） |
| 审计各系列是否仍独立、是否误引公共层/别线代码 | **`tools/independence-audit`**（静态扫描；代码级跨线依赖会失败） |
| 刷新选择点候选（模型/后端清单是否过期）| 本线 **`skills/<line>/_lib/refresh.py`**（仅 n2d/ad 有候选源；机检快照新鲜度 → 实时搜索核验 → 改候选 + bump 采集日期 + 落 provenance；守各线策略差异不合并） |

> 本仓库包含 **novel / n2d / song / mv / ad** 五条并列创作生产线。每条线都必须自包含、可单独分发：本线脚本只 import 本线 `_lib` 或本线 craft 工具，不依赖 `skills/common/`，也不 import 其他系列实现。跨线只允许**可选文件/数据交接**，例如 novel 导出 n2d 源书、song 交成品歌给 mv、n2d-feedback 写题材战绩 JSONL 供 novel-score 读取；交接缺失时必须优雅降级，不能让本线主流程跑不起来。

## 必须遵守的项目约定

> **完整设计法条（怎么*建造* skill）的唯一权威是 [`docs/skill-design-principles.md`](docs/skill-design-principles.md)**（跨线宪法：独立性 / 选择点适配 / 合规闸门 / VCS-free 交付 / README 同步）。下面是速查摘要，新增或改 skill 前请读宪法本体，别在各处复述。可机检的条文跑 `python3 tools/validate_skills.py`（E1 无 git / B2 裸 skill 名 / F1 README 索引 / F3 入口文档同步）与 `tools/independence-audit/scripts/check_independence.py`（跨线独立性）。

- **进度**：每个作品根有 `_进度.md`（状态机）。**先读它**判断走到哪一步、下一步做什么；做完**回写**。
- **偏好/选择点**：凡"让用户选"的点（平台/后端/分辨率/音色…），首次问一次→用 `n2d-settings` 写进 `<作品根>/_设置.md`→同项目沉默沿用。**别在 skill 代码里写死**唯一路径。
- **候选项更新 + 适配层**：选择菜单只是带日期的候选快照，不是真理。涉及模型/平台/法规/价格/规格等会变的信息，执行前应按需要用专业知识、项目 references、官方文档或实时搜索核验并刷新候选；用户永远可以手输 `自定义`/`manual`。skill 执行时不要直接依赖菜单文案，而要经适配层把用户选择归一到能力、参数、CLI/API、降级方案和合规闸门；适配不了就停下说明缺口，不要偷偷换路。机检与落地工具（仅 n2d/ad 有候选源）：`python3 skills/<line>/_lib/freshness.py` 报哪些候选快照过期；同目录 `refresh.py` 跑「搜索核验 → 改候选 → bump 采集日期 + 落 provenance」。各线策略差异是故意的（如 ad 禁即梦 ≠ n2d 放行即梦官方），分别刷新、绝不合并候选清单。
- **合规闸门（硬性）**：克隆真人歌手嗓需授权（2026 opt-in），未授权拒做。词曲/小说默认公版 / 自有 / 已授权。
- **改了 skill 集合**（增/删/改职责）→ 必须同步更新 `skills/README.md` 索引。
- **改了跨线引用 / `_lib` / 调度入口** → 跑 `python3 tools/independence-audit/scripts/check_independence.py`，确保没有误引公共层或别线代码。
- **本机工具/环境**（macOS）：`ffmpeg`（精简版，**无 libass/drawtext**，字幕走 Pillow 渲 PNG + overlay）；conda 环境 `cosyvoice`(含 librosa/whisper)、`acestep`(本地出歌)、`fish-speech`；系统 Python 3.14 + PEP668 装不了重依赖，音频类用上述 conda env。踩坑细节见各 skill `references/`。

## 不在 git 里的东西

- 各 AI 自己的私有配置（如 `.claude/`、`.cursor/` 等）与用户私有偏好默认不进共享 skill。
- 大模型权重、conda 环境在仓库外（`~/ACE-Step`、`~/CosyVoice` 等），按 `references/` 安装说明本地准备。
