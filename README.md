# anime-armory

一套面向 AI 内容生产的本地流水线：把一个点子、一本书或一首歌，推进成可交付的小说、AI 漫剧短视频或 AI 音乐 MV。

仓库的核心不是单个脚本，而是根目录 `skills/` 下的一组可复用 workflow skill。它们按两组创作线和生产线组织：

- **写小说** -> **制漫剧**：小说文本 -> AI 漫剧 / 短剧
- **写歌** -> **制MV**：成品歌 -> AI 音乐 MV

产物落在顶层中文目录：`写小说/`、`制漫剧/`、`写歌/`、`制MV/`。每个作品一个子目录，通常都有 `_进度.md` 和 `_设置.md` 来记录状态与选择。

> 给 AI agent 或人快速进仓库：先读 [AGENTS.md](AGENTS.md)。  
> skill 完整索引与职责边界：读 [skills/README.md](skills/README.md)。

## 先看 Demo

仓库里现有作品就是端到端样例，可以直接看目录结构、进度文件和产物组织方式。

| 类型 | 示例 | 说明 |
|---|---|---|
| MV 成片 | `制MV/仗剑下山/成片_MV.mp4` | 从 `写歌/仗剑下山/歌/song.wav` 到卡点、出图、出视频、字幕与合成 |
| 写歌产物 | `写歌/仗剑下山/词/lyrics.md`、`写歌/仗剑下山/歌/song.wav` | 词、歌、人声成品的最小示例 |
| 小说产物 | `写小说/本宫才是这皇宫最大的妖/`、`写小说/看花胖子，藏到了飞升/` | 原作、导出、章节、评分与审稿数据 |
| 漫剧工程 | `制漫剧/本宫才是这皇宫最大的妖/` | 小说、脚本、设定库、出图、合规、生产数据等工程结构 |
| 迭代截图 | `docs/images/novel-iterate-*.png` | 小说评分、改写选择点、书名评估等流程截图 |

这些 demo 默认按作者本人 / 公版 / 已授权素材展示。复用本工具时请自备合法素材。

## 快速开始

在本地 AI agent 里打开仓库，然后按目标选择入口 skill。入口 skill 会读取作品 `_进度.md`，判断下一步要走哪个子阶段。

| 你想做什么 | 入口 |
|---|---|
| 写、改、续、扩、缩一本小说 | `/novel-author <想法/书名/路径/动作>` |
| 从零写一本原创小说 | `/novel-create <题材或想法>` |
| 给小说做评分、判断值不值得改 | `/novel-score <写小说/项目>` |
| 把小说做成 AI 漫剧 | `/novel2drama <小说路径或 制漫剧/项目>` |
| 查看漫剧项目进度与下一步 | `/n2d-progress <制漫剧/项目>` 或直接问“当前进度” |
| 直接创作或编辑一首歌 | `/song <主题/风格/想法 或 写歌/项目>` |
| 把成品歌做成 MV | `/mv <歌曲路径或 制MV/项目>` |
| 图片 / 视频换脸 | `/shared-image-faceswap`、`/shared-video-faceswap` |
| 给图片 / 视频加 AI 标识或品牌水印 | `/shared-watermark` |
| 清理 `skills/` 里的缓存和临时文件 | `/shared-cleanup` |

常见完整链路：

```text
写小说：/novel-author -> novel-create/fetch/rewrite/continue/... -> novel-review/novel-score
制漫剧：/novel2drama -> n2d-script -> n2d-voice -> n2d-script(分镜) -> n2d-image -> n2d-video -> n2d-compose
写歌：/song -> song-lyrics/song-score -> song-compose -> song-review
制MV：/mv -> mv-beat -> mv-plan -> mv-image -> mv-video -> mv-lyric-sync -> mv-compose -> mv-review
```

## 打包与下载版本

给用户分发时，推荐发轻量 starter 包：只包含 README、AGENTS、`skills/`、`docs/`、桌面端源码和空作品目录，不包含仓库里的 demo 媒体、未追踪产物、`.venv`、`node_modules`、私有 agent 配置和缓存。

本仓库提供打包脚本：

```bash
bash scripts/package_release.sh 2026-06-10
```

输出在 `dist/`：

```text
dist/anime-armory-starter-2026-06-10.zip
dist/anime-armory-starter-2026-06-10.zip.sha256
```

发布时把这两个文件上传到 GitHub Release、网盘、飞书云盘或其他下载位置即可。用户下载后解压，用本地 AI agent 打开目录，先读 `AGENTS.md`，再按本 README 的入口 skill 开新项目。

如果要打“完整源码包”（包含 git 已追踪的 demo 工程与示例媒体），先确认工作区已经提交，再执行：

```bash
mkdir -p dist
git archive --format=zip --prefix=anime-armory-full/ -o dist/anime-armory-full.zip HEAD
shasum -a 256 dist/anime-armory-full.zip > dist/anime-armory-full.zip.sha256
```

`dist/` 已被 `.gitignore` 忽略，压缩包默认不进仓库；它是发布附件，不是源码的一部分。

## 四条主线

### 写小说

入口是 `novel-author`。它负责分诊，不直接写作：根据输入或 `写小说/<项目>/_进度.md` 路由到子 skill。

主要能力包括：

- `novel-create`：从想法访谈到设定圣经、章纲、Demo、批量写章。
- `novel-fetch`：抓取公版 / 授权小说并落成本地项目。
- `novel-rewrite`、`novel-spinoff`、`novel-continue`、`novel-expand`、`novel-condense`：改写、外传、续写、扩写、精简。
- `novel-review`：审硬伤，查视角、人设、设定、锚点和照搬风险。
- `novel-score`：联网对标热榜和第一方战绩，判断市场潜力与改写 ROI。
- `novel-style`、`novel-wiki`、`novel-simulate`、`novel-balance`、`novel-promote`：文风、动态百科、模拟读者、节奏热力、宣发爆点等增强模块。

### 制漫剧

入口是 `novel2drama`。默认推荐“配音先行”：先用真实配音时长驱动分镜，再出图、出视频和合成，减少音画错位返工。

主流程：

1. `n2d-script`：拆集、台词、BGM、角色卡、场景卡、视觉风格。
2. `n2d-voice`：角色配音、拼接音轨、生成句级时长清单。
3. `n2d-script` 回跑：按实测时长生成故事板、素材清单和字幕。
4. `n2d-image`：共享定妆库 + 本集分镜图。
5. `n2d-video`：图生视频，按故事板和镜头调度生成 clips。
6. `n2d-compose`：配音、BGM、字幕、水印、clips 合成成片。

工业化横切能力：

- `n2d-compliance`：源文本、肖像、声音克隆、AI 标识、平台审核等合规包。
- `n2d-identity`、`n2d-lora`、`n2d-asset-market`：角色身份、LoRA 生命周期、跨项目资产库。
- `n2d-model-router`：按镜头类型选择视频后端与 fallback。
- `n2d-dashboard`、`n2d-batch`、`n2d-score`、`n2d-review-ui`、`n2d-feedback`：成本、批量任务、机器评分、人审 UI、投放回灌。

### 写歌

入口是 `song`。它既能从主题/风格/想法直接创作歌曲，也能读取已有 `写歌/<曲名>/` 做改词、改曲风、重生成、多版挑版、换声和质检。产物落 `写歌/<曲名>/`，成品歌可交给 `mv` 线继续生产视频。

- `song-lyrics`：访谈式作词、结构、押韵、hook。
- `song-compose`：Suno / Udio / ACE-Step / DiffRhythm 等后端的作曲与人声成品管理。
- `song-cover`：翻唱 / 换声。
- `song-review`、`song-score`：歌词可唱性、音频质量、音色合规与市场评估。

### 制MV

入口是 `mv`。这条线自包含，不复用 n2d 的分镜、出图、出视频逻辑。

1. `mv-beat`：BPM、鼓点、能量、段落和 beatgrid。
2. `mv-plan`：clip plan、timeline manifest、出图 / 出视频 prompt 包。
3. `mv-image`：MV 共享定妆和分段分镜图。
4. `mv-video`：多版图生视频、登记、评分、挑版。
5. `mv-lyric-sync`：Whisper / WhisperX 对齐歌词，生成卡拉 OK 字幕。
6. `mv-compose`：按 timeline 合成成片。
7. `mv-review`、`mv-score`：卡点、字幕、音画、视觉一致性、平台披露与成片评分。

## 公共能力

| Skill | 用途 |
|---|---|
| `shared-image-faceswap` | 图片换脸，本人 / 授权 / 合成脸限定，强制 AI 标识 |
| `shared-video-faceswap` | 视频换脸，同样走合规闸门和水印 |
| `shared-watermark` | 给图片 / 视频加 AI 标识或品牌水印，只加不去 |
| `shared-cleanup` | 清理 `skills/` 下低风险生成垃圾，默认先扫描 |

换脸、声音克隆、真人仿声都属于高风险能力：必须有授权，且必须保留 AI 标识。未授权真人歌手嗓音克隆直接拒做。

## 关键约定

- **先读 `_进度.md`**：每个作品的当前状态、下一步和已完成产物都以它为准；做完要回写。
- **选择写进 `_设置.md`**：平台、后端、分辨率、音色、制作模式等选择点首次问一次，之后同项目沉默沿用。
- **skill 保持通用**：不要把个人偏好、平台账号、唯一后端写死进 skill。
- **合规前置**：换脸、仿声、改编权、AI 标识不要等成片后补救。
- **改 skill 集合要同步索引**：新增、删除或改变职责时，同步更新 [skills/README.md](skills/README.md)。
- **不要覆盖 AGENTS.md**：它是手工维护的工具中立入口，不要用任何 init 命令重建。

## 本地环境

项目面向 macOS 本地工作流，重活依赖外部工具或 conda 环境：

- `ffmpeg`：当前本机常见是精简版，无 `libass` / `drawtext`，字幕通常走 Pillow 渲 PNG 后 overlay。
- `cosyvoice` / `fish-speech`：配音、音频处理、Whisper 相关能力。
- `acestep`：本地出歌 demo。
- `facefusion`：换脸底座。
- 图生视频 / 生图 CLI：按各 skill 的后端选择点配置，不在 README 写死。

系统 Python 可能受 PEP 668 限制，重依赖优先放到对应 conda 环境；脚本细节看各 skill 的 `references/`。

## 目录结构

```text
anime-armory/
├── README.md                 快速入口
├── AGENTS.md                 工具中立入口，AI agent 先读
├── skills/                   全部 workflow skill
│   ├── README.md             skill 分类索引
│   ├── _偏好约定.md          选择点和私有偏好规则
│   ├── common/               共享契约与通用脚本
│   ├── novel-*               写小说能力
│   ├── novel2drama/ n2d-*    制漫剧能力
│   ├── song/ song-*          写歌能力
│   ├── mv/ mv-*              制MV能力
│   └── shared-*              公共能力
├── .claude/skills -> ../skills
├── 写小说/<项目>/             小说产物
├── 制漫剧/<项目>/             漫剧工程与成片产物
├── 写歌/<曲名>/               歌词、歌曲、人声产物
├── 制MV/<曲名>/               MV 工程与成片
├── 资产库/                    跨项目复用资产
└── docs/images/              文档截图
```

## 维护边界

根 README 只放快速开始和稳定约定。具体阶段、脚本参数、后端差异、验收标准放在对应 `skills/<name>/SKILL.md` 和 `references/` 里。这样可以避免 README 变成第二份过期索引。
