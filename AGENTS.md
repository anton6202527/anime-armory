<!-- 手工维护，勿用 codex /init（或任何 agent 的 init）覆盖。本文件是跨工具的工具中立入口，Codex/Cursor 等会按约定名自动读取。 -->

# AGENTS.md — 给 AI 编码/创作 agent 的入口

> 本文件是**工具中立**的项目说明，供任何 AI agent（Cursor / Cline / Gemini-CLI / Codex / Copilot / Claude Code…）或人进仓库时快速上手。不绑定任何特定 AI。

## 怎么用这些 skill（任何 agent 通用）

1. **发现**：先读 [`skills/README.md`](skills/README.md)（分类总览）。普通独立 skill 位于 `skills/<skill-name>/SKILL.md`，画布/Web App 独立 skill 位于 `skills/app/<app-skill-name>/SKILL.md`；六个既有系列仍由 `skills/<line>/SKILL.md` 总入口分诊其历史子 skill。
   - SKILL.md 的 frontmatter `description` + 正文 `Triggers`/`Use when` **就是路由依据**：用户意图命中哪个，就用哪个。
2. **执行**：照 SKILL.md 的步骤做事；普通独立 skill 的脚本在 `skills/<skill-name>/scripts/`，画布/Web App 独立 skill 的脚本在 `skills/app/<app-skill-name>/scripts/`，系列总入口脚本在 `skills/<line>/scripts/`，既有子 skill 脚本在 `skills/<line>/<skill-name>/scripts/`。
3. **脚本是通用的**：纯 Python / bash，只调通用工具（`ffmpeg` / `librosa` / `whisper` / `yt-dlp` / 生图生视频 CLI 等），**无任何某家 AI 的专有 API**，谁都能直接执行。引用路径用中立的 `skills/...`。
4. **写法**：对用户输出“下一步”或推荐调用某个 skill 时，一律写裸 skill 名（如 `n2d-image`），**不要**写成 `/n2d-image`。有些 AI agent 会把 `/...` 当内置斜杠命令并报 `Unrecognized command`。

仓库级维护工具不放在 `skills/`，统一放 `tools/`；例如清理工具见 `tools/shared-cleanup/SKILL.md`，作品资产索引/doctor/渐进迁移见 `tools/artifact-catalog/SKILL.md`。

> Claude Code 用户：`.claude/skills → ../skills` 是软链；普通独立 skill 可直接发现，画布/Web App skill 按本表进入 `skills/app/`，六个系列总入口继续分诊既有子 skill。其他工具：把用户意图对照下表/各 SKILL.md 的 Triggers 自行选 skill。

## 选哪个 skill（按意图）

| 用户想做 | 入口 skill（总调度，会再分诊到子 skill） |
|---|---|
| 写小说、导入源书、生活观察素材、审美样本、扩写/改写/续写/评分/审稿/专业编辑、穿越/系统流的力量体系·等级·成长值一致性自检 | **`novel`**（分诊到 novel-create/observe/aesthetic/fetch/rewrite/review/edit/score/wiki 等） |
| 把小说做成 AI 漫剧/短剧（分镜/配音/出图/出视频/合成） | **`n2d`**（分诊到 n2d-script/voice/image/video/compose） |
| 在画布中把故事变成可编辑镜头与资产，持续生成、返修、质检并合成为最终母版 | **`app-script-workbench`**（`skills/app/` 独立 skill；不经过系列分诊） |
| 在画布中把单张角色参考做成正面、侧面、背面一致的设定图 | **`app-character-turnaround`**（`skills/app/` 独立 skill；不经过 `comic` / `n2d` 分诊） |
| 在画布中从真实首帧设计动作和运镜并生成视频任务 | **`app-first-frame-video`**（`skills/app/` 独立 skill；不经过 `n2d-video` / `mv-video` 分诊） |
| 在画布中分析音频段落与节拍并生成卡点视频任务 | **`app-audio-video`**（`skills/app/` 独立 skill；不经过 `mv` / `song` 分诊） |
| 用 agent 方式总控 n2d、自动跑前置、生成 context pack/creative loop、派发少量专家 | **`n2d-supervisor`**（消费 `n2d/run.py next --json`；不替代 n2d 状态机/gate/skill） |
| 画漫画、条漫/页漫、写分格脚本、页面排版、漫画出图、嵌字和长图导出 | **`comic`**（分诊到 comic-script/layout/image/compose/review） |
| 写歌、改词、作曲、多版挑版、翻唱/换声、审歌、发布交付和真实反馈回灌 | **`song`**（分诊到 song-craft/lyrics/compose/cover/review/feedback 等） |
| 给歌曲做 MV、卡点、出图出视频、卡拉 OK 字幕、合成 | **`mv`**（分诊到 mv-script/beat/plan/image/video/compose 等） |
| 做广告片、TVC、信息流广告、产品 demo、带货视频、投放前广告评分 | **`ad`**（分诊到 ad-concept/script/voice/image/video/compose/score/review） |
| 检查各系列 skill 更新是否影响项目、生成最小返工/重审/重评计划 | **`novel-update` / `n2d-update` / `comic-update` / `song-update` / `mv-update` / `ad-update`**（按作品线选择；内容快照比对 + 最小返工/重制计划；只写计划/基线，不改正文、媒体或 `_进度.md`） |
| 查看项目进度/下一步，或在仓库根汇总某条线项目 | **`novel-progress` / `n2d-progress` / `comic-progress` / `song-progress` / `mv-progress` / `ad-progress`**（按作品线选择；只读扫描，不回写 `_进度.md`） |
| 修改/审计项目设置、选择点或全局默认 | **`novel-settings` / `n2d-settings` / `comic-settings` / `song-settings` / `mv-settings` / `ad-settings`**（按作品线选择；包住本线 `_设置.md` 读写/校验/重置/同步全局默认） |
| 制漫剧少量图片/视频选择性刷新计划 | **`n2d-update`**（`media` 子命令做指定图片/视频的证据驱动刷新计划） |
| 审计作品生成文件、建立可视化读取索引、规划旧目录渐进迁移 | **`tools/artifact-catalog`**（只读 catalog/doctor；`migrate` 默认 dry-run，确认后才 `--apply`；不成为任一系列依赖） |
| 清理 / 瘦身生成垃圾 | **`tools/shared-cleanup`**（仓库级 dev 工具；默认扫 `skills/`，可 `--repo` 扫全仓；确认后只删低风险缓存/临时文件并统计节省空间） |
| 审计各系列是否仍独立、是否误引公共层/别线代码 | **`tools/independence-audit`**（静态扫描；代码级跨线依赖会失败） |
| 刷新选择点候选（模型/后端清单是否过期）| 本线 **`skills/<line>/_lib/refresh.py`**（仅 n2d/ad 有候选源；机检快照新鲜度 → 实时搜索核验 → 改候选 + bump 采集日期 + 落 provenance；守各线策略差异不合并） |

> 本仓库包含 **novel / n2d / comic / song / mv / ad** 六条并列创作生产线。每条线都必须自包含、可单独分发：本线脚本只 import 本线 `_lib` 或本线 craft 工具，不依赖 `skills/common/`，也不 import 其他系列实现。novel 与 n2d 必须保持零交接、零数据耦合；其它跨线交付只能是用户显式选择的成品文件交接，交接缺失时必须优雅降级，不能让本线主流程跑不起来。

## 必须遵守的项目约定

> **完整设计法条（怎么*建造* skill）的唯一权威是 [`docs/skill-design-principles.md`](docs/skill-design-principles.md)**（跨线宪法：独立性 / 选择点适配 / 合规闸门 / VCS-free 交付 / README 同步）。下面是速查摘要，新增或改 skill 前请读宪法本体，别在各处复述。可机检的条文跑 `python3 tools/validate_skills.py`（E1 无 git / B2 裸 skill 名 / B7 定妆基础包 / B9 无持久主体 ID 与项目记忆分层 / F1 README 索引 / F3 入口文档同步 / F7 系列规模统计）与 `tools/independence-audit/scripts/check_independence.py`（跨线独立性）。

- **进度**：每个作品根有 `_进度.md`（状态机）。**先读它**判断走到哪一步、下一步做什么；做完**回写**。
- **状态 / 哈希 / 完成**：每条线的每个作品/集交付单元或独立 workflow 实例只认一个权威业务前沿；同一权威对象只认一个 canonical SHA-256 口径；该交付单元最终完成只由一个 release/completion verdict 聚合当前合同、产物、gate 与收据后判定。dashboard、队列、provider `succeeded`、telemetry 和 `machine_complete` 都只是派生证据，不能宣布第二套状态或冒充最终完成。
- **偏好/选择点**：普通、可逆项缺失时采用本线有证据优势的推荐值→用本线 `*-settings` 写进 `<作品根>/_设置.md`→同项目沉默沿用。付费生成把作品/阶段/输入 SHA/scope/模型/渠道/调用与重抽上限/费用上限/有效期绑定为一个阶段预算包，只在创建、扩大、过期或合同变化时确认，包内连续执行；权利合规、逐图当前像素闸、不可逆发布/覆盖和最终成品验收仍是硬边界。若作品设置已明确授权执行者实际查看当前像素，本线可用 `human_signoff=false` 的 hash-bound 收据连续推进可逆中间生产，但不得冒充最终具名真人验收。**别在 skill 代码里写死**唯一路径，也别让 runner 自发批准预算。
- **候选项更新 + 适配层**：选择菜单只是带日期的候选快照，不是真理。涉及模型/平台/法规/价格/规格等会变的信息，执行前应按需要用专业知识、项目 references、官方文档或实时搜索核验并刷新候选；用户永远可以手输 `自定义`/`manual`。skill 执行时不要直接依赖菜单文案，而要经适配层把用户选择归一到能力、参数、CLI/API、降级方案和合规闸门；适配不了就停下说明缺口，不要偷偷换路。机检与落地工具（仅 n2d/ad 有候选源）：`python3 skills/<line>/_lib/freshness.py` 报哪些候选快照过期；同目录 `refresh.py` 跑「搜索核验 → 改候选 → bump 采集日期 + 落 provenance」。各线策略差异是故意的（如 ad 禁即梦 ≠ n2d 放行即梦官方），分别刷新、绝不合并候选清单。
- **合规闸门（硬性）**：克隆真人歌手嗓需授权（2026 opt-in），未授权拒做。词曲/小说默认公版 / 自有 / 已授权。
- **改了 skill 集合**（增/删/改职责）→ 必须同步更新 `skills/README.md` 索引。
- **新增 skill 的目录**：普通独立 skill 默认创建在 `skills/<skill-name>/`；现阶段仅供画布/Web App 使用的独立 skill 统一放在 `skills/app/<app-skill-name>/`，并必须以 `app-` 开头。`app-` 表示交互表面，不代表作品线归属。独立 skill 可以参考系列 skill，但必须自带入口、脚本、schema 与状态，默认不 import/调用系列实现。现有系列子 skill 保持原位，除非用户明确要求迁移。
- **改了任一系列或独立 skill（含 `skills/app/`）的文本/脚本** → 跑 `python3 tools/update_skill_stats.py`，同步 `skills/README.md` 统计表和各总领 skill 第一行规模统计；`validate_skills.py --only F7` 会拦截过期统计。
- **改了跨线引用 / `_lib` / 调度入口** → 跑 `python3 tools/independence-audit/scripts/check_independence.py`，确保没有误引公共层或别线代码。
- **本机工具/环境**（macOS）：`ffmpeg`（精简版，**无 libass/drawtext**，字幕走 Pillow 渲 PNG + overlay）；conda 环境 `cosyvoice`(含 librosa/whisper)、`acestep`(本地出歌)、`fish-speech`；系统 Python 3.14 + PEP668 装不了重依赖，音频类用上述 conda env。踩坑细节见各 skill `references/`。

## 不在 git 里的东西

- 各 AI 自己的私有配置（如 `.claude/`、`.cursor/` 等）与用户私有偏好默认不进共享 skill。
- 大模型权重、conda 环境在仓库外（`~/ACE-Step`、`~/CosyVoice` 等），按 `references/` 安装说明本地准备。
