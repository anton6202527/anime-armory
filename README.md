# anime-armory

一套面向 AI 内容生产的本地流水线：把一个点子、一本书、一首歌或一份客户需求，推进成可交付的小说、AI 漫剧短视频、AI 音乐 MV 或 商业广告片。

仓库的核心不是单个脚本，而是根目录 `skills/` 下的一组可复用 workflow skill。它们构成四条彼此独立、可单独分发的生产线：

- **小说文本 -> AI 漫剧 / 短剧（n2d）**：拆集 -> 配音 -> 分镜 -> 出图 -> 出视频 -> 合成
- **歌曲（song）**：作词 -> 作曲 / 多版挑版 -> 翻唱 / 换声 -> 审歌
- **音乐 MV（mv）**：歌曲入库 -> beatgrid -> 视觉蓝图 -> clip 规划 -> 出图 / 出视频 -> 卡拉 OK 字幕 -> 合成
- **广告片（ad）**：brief -> 创意 -> 脚本 / VO -> 分镜 -> 产品 / 场景 / 角色定妆 -> 出图 / 出视频 -> 交付件

产物分别落在顶层中文目录 `制漫剧/`、`写歌/`、`制MV/`、`拍广告/`（跨项目可复用资产在 `资产库/`）。每个作品一个子目录，通常都有 `_进度.md` 和 `_设置.md` 来记录状态与选择。

> 给 AI agent 或人快速进仓库：先读 [AGENTS.md](AGENTS.md)。  
> skill 完整索引与职责边界：读 [skills/README.md](skills/README.md)。

## 下载安装

开箱即用的安装包，点击直接下载（链接始终指向最新发布版本）：

| 安装包 | 平台 | 下载 |
|---|---|---|
| 🖥️ 桌面端 App | macOS（通用，Intel/Apple Silicon） | [**AnimeArsenal_macos.dmg**](https://github.com/anton6202527/anime-armory/releases/latest/download/AnimeArsenal_macos.dmg) |
| 🖥️ 桌面端 App | Windows（`.exe` 安装程序） | [**AnimeArsenal_windows.exe**](https://github.com/anton6202527/anime-armory/releases/latest/download/AnimeArsenal_windows.exe) |
| 🧩 VS Code 插件 | 跨平台（`.vsix`） | [**anime-armory.vsix**](https://github.com/anton6202527/anime-armory/releases/latest/download/anime-armory.vsix) |

- **桌面端 App**：macOS 下载 `.dmg` 双击安装；Windows 下载 `.exe` 运行安装程序。打开即用，内置全部 skill。
- **VS Code 插件**：下载 `.vsix` 后，在 VS Code 命令面板执行 `Extensions: Install from VSIX…` 选中该文件安装。

> 链接始终指向 anime-armory **最新发布版**（已发布，可直接下载）；桌面端 App 内置当前全部 skill。历史版本与校验和见 [Releases 页](https://github.com/anton6202527/anime-armory/releases)。维护者出新版见下方“自行打包发布”（推 `desktop-v*` tag 触发云端构建，自动按稳定文件名发布到 Release）。

### 核心资产是 skill —— 也可以不装 App，自行下载调试

本项目真正可复用的核心不是某个安装包，而是 `skills/` 下那组 workflow skill；安装包只是把它们包进了更顺手的界面。你完全可以跳过 App，直接拿到 skill 自己跑、自己改：

```bash
# 克隆仓库，skill 全在 skills/ 下
git clone https://github.com/anton6202527/anime-armory
cd anime-armory
```

或在上面 Release 页面下载源码包 / starter 包。拿到后用本地 AI agent（Claude Code、Codex 等）打开目录，先读 [AGENTS.md](AGENTS.md)，再按下面的入口 skill 调试；改 skill、加后端、调提示词都直接编辑 `skills/<name>/SKILL.md` 即可。

## 先看 Demo

仓库里现有作品就是端到端样例，可以直接看目录结构、进度文件和产物组织方式。

| 类型 | 示例 | 说明 |
|---|---|---|
| 漫剧工程 | `制漫剧/本宫才是这皇宫最大的妖/` | 小说源、脚本、设定库、出图、合规、生产数据等工程结构 |

这些 demo 默认按作者本人 / 公版 / 已授权素材展示。复用本工具时请自备合法素材。

## 快速开始

在本地 AI agent 里打开仓库，然后按目标选择入口 skill。入口 skill 会读取作品 `_进度.md`，判断下一步要走哪个子阶段。

skill 名称按跨工具兼容写法展示：直接写 `n2d-image`、`n2d-progress` 这类裸名，不加 `/`。部分 AI agent 会把 `/n2d-image` 当成自身不支持的斜杠命令。

| 你想做什么 | 入口 |
|---|---|
| 把小说做成 AI 漫剧 | `n2d <小说路径或 制漫剧/项目>` |
| 写歌 / 改词 / 作曲 / 多版挑版 / 审歌 | `song <想法、歌词或 写歌/项目>` |
| 给歌曲做 MV / 卡点 / 出 MV 成片 | `mv <歌曲或 制MV/项目>` |
| 做广告片 / TVC / 信息流广告 / 产品 demo | `ad <brief 或 拍广告/项目>` |
| 查看项目进度与下一步 | `n2d-progress [作品目录]` 或直接问“当前进度” |
| 修改或审计项目设置 | `n2d-settings set/audit/reset/sync-global [作品目录] …` |
| 检查流水线更新与生成重制计划 | `n2d-update check [作品目录]` 或问“看看有没有更新”；只重出部分图片/视频走 `n2d-update media …` |
| 清理缓存和临时文件 | `tools/shared-cleanup`（默认 `skills/`，可 `--repo` 全仓） |
| 检查四条线是否仍独立 | `python3 tools/independence-audit/scripts/check_independence.py` |

常见完整链路：

```text
制漫剧：n2d -> n2d-script -> n2d-voice -> n2d-script(分镜) -> n2d-image -> n2d-video -> n2d-compose
写歌：song -> song-lyrics -> song-score -> song-compose -> song-cover(可选) -> song-review
MV：mv -> mv-beat -> mv-script -> mv-plan -> mv-image -> mv-video -> mv-lyric-sync -> mv-compose
广告：ad -> ad-concept -> ad-script -> ad-voice -> ad-script(分镜) -> ad-image -> ad-video -> ad-compose
```

## 自行打包发布（维护者）

上面“下载安装”里的安装包就是用本节脚本打出来后上传到 anime-armory 的 GitHub Release 的。自己分发或出新版时按下面流程重新打包即可。

**桌面端 App / VS Code 插件（推荐用云端构建，一步到位）**：

Windows 安装包**无法在 macOS 上交叉编译**，必须在 Windows 上构建。仓库已内置云端流水线 [`​.github/workflows/desktop-release.yml`](.github/workflows/desktop-release.yml)，用 GitHub Actions 同时在 macOS 与 Windows 上构建，并把安装包按“下载安装”表里的**稳定文件名**发布到 anime-armory 的 Release：

```bash
# 推一个 desktop-v* tag 即触发云端构建 + 发布（mac .dmg / win .exe[NSIS] / .vsix）
git tag desktop-v0.1.6 && git push origin desktop-v0.1.6
# 或在 Actions 页手动 workflow_dispatch（只产出 build artifact，不发 Release）
```

前置：在 anime-arsenal 仓库加一个 secret `ARMORY_RELEASE_TOKEN`（一个对 anime-armory 有 `contents: write` 权限的 PAT）——默认 `GITHUB_TOKEN` 只能写当前仓库，跨仓发布到 armory 必须用 PAT。流水线会自动把产物重命名为 `AnimeArsenal_macos.dmg`（macOS）/ `AnimeArsenal_windows.exe`（Windows NSIS 安装程序）/ `anime-armory.vsix`，与“下载安装”表里的 `releases/latest/download/...` 直链一一对应。Windows 只打 NSIS `.exe`（MSI/WiX 对大体积 `skills/` 资源树不稳定）。

本地手动打包（仅产出当前系统的安装包；macOS 上得不到 Windows 包）：

```bash
# 桌面端：在 desktop/ 里用 Tauri 打当前平台的安装包
cd desktop && npm install && npm run tauri build

# VS Code 插件：在 vscode-extension/ 里打 .vsix
cd vscode-extension && npx @vscode/vsce package
```

手动产物需自行上传到 anime-armory 的 Release，并重命名成上表的稳定文件名，`releases/latest/download/...` 链接才会指向它。

**轻量 starter 包（只发 skill 与工具）**：推荐发轻量 starter 包给只想用 skill 的用户——只包含 README、AGENTS、`skills/`、`tools/`、`docs/`、桌面端源码和空作品目录，不包含仓库里的 demo 媒体、未追踪产物、`.venv`、`node_modules`、私有 agent 配置和缓存。

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

## 生产线：小说 → AI 漫剧（n2d）

入口是 `n2d`。默认推荐“配音先行”：先用真实配音时长驱动分镜，再出图、出视频和合成，减少音画错位返工。

主流程：

1. `n2d-script`：拆集、台词、BGM、角色卡、场景卡、视觉风格。
2. `n2d-voice`：角色配音、拼接音轨、生成句级时长清单。
3. `n2d-script` 回跑：按实测时长生成故事板、素材清单和字幕。
4. `n2d-image`：共享定妆库 + 本集分镜图。
5. `n2d-video`：图生视频。支持能力报盘（backend_status）与自动化拆段接力（Split Relay），按镜头调度生成 clips。
6. `n2d-compose`：合成成片。支持子段无缝拼接与 storyboard 转场感知。

工业化横切能力：

- `n2d-compliance`：源文本、改编权、肖像、声音克隆、平台审核与出海本地化合规包。
- `n2d-identity`、`n2d-lora`、`n2d-asset-market`：角色身份、LoRA 生命周期、跨项目资产库。
- `n2d-model-router`：按镜头类型选择视频后端与 fallback。
- `n2d-dashboard`、`n2d-batch`、`n2d-score`、`n2d-review-ui`、`n2d-feedback`：成本、批量任务、机器评分、人审 UI、投放回灌。
- `n2d-progress`、`n2d-settings`、`n2d-update`：进度仪表盘、项目设置管理与 skill 更新最小重制计划（`n2d-update media` 还能只重出部分图片/视频）。

## 维护能力

| 入口 | 用途 |
|---|---|
| `n2d-progress` | 只读进度扫描：制漫剧项目查询当前前沿与下一步；仓库根可汇总所有 n2d 项目 |
| `n2d-settings` | 管理 `_设置.md`：设置/重置选择点，审计非法值，同步私有全局默认 |
| `tools/shared-cleanup` | 仓库级清理工具，默认扫 `skills/`，可 `--repo` 扫全仓，输出节省空间统计 |
| `tools/independence-audit` | 静态检查五条 skill 系列是否误引公共层或别线代码 |

> 水印 / 换脸 skill 已于 2026-06 下线，AI 标识/披露的强制闸门已移出本工具，由流水线之外的合规环节负责。

声音克隆、真人仿声都属于高风险能力：必须有授权。未授权真人歌手嗓音克隆直接拒做。

## 关键约定

- **先读 `_进度.md`**：每个作品的当前状态、下一步和已完成产物都以它为准；做完要回写。
- **选择写进 `_设置.md`**：平台、后端、分辨率、音色、制作模式等选择点首次问一次，用 `n2d-settings` 落档，之后同项目沉默沿用。
- **skill 保持通用**：不要把个人偏好、平台账号、唯一后端写死进 skill。
- **合规前置**：仿声、改编权不要等成片后补救。
- **改 skill 集合要同步索引**：新增、删除或改变职责时，同步更新 [skills/README.md](skills/README.md)。
- **系列互相独立**：n2d / song / mv / ad 不 import 彼此实现；跨线只走可选文件或数据交接。
- **不要覆盖 AGENTS.md**：它是手工维护的工具中立入口，不要用任何 init 命令重建。

## 本地环境

项目面向 macOS 本地工作流，重活依赖外部工具或 conda 环境：

- `ffmpeg`：当前本机常见是精简版，无 `libass` / `drawtext`，字幕通常走 Pillow 渲 PNG 后 overlay。
- `cosyvoice` / `fish-speech`：配音、音频处理、Whisper 相关能力。
- `acestep`：本地出歌 demo。
- 图生视频 / 生图 CLI：按各 skill 的后端选择点配置，不在 README 写死。

系统 Python 可能受 PEP 668 限制，重依赖优先放到对应 conda 环境；脚本细节看各 skill 的 `references/`。

## 目录结构

```text
anime-armory/
├── README.md                 快速入口
├── AGENTS.md                 工具中立入口，AI agent 先读
├── skills/                   全部 workflow skill
│   ├── README.md             skill 分类索引
│   ├── n2d/ n2d-*            制漫剧能力（契约与通用脚本 vendored 进 n2d/_lib/）
│   ├── song/ song-*          写歌、作曲、翻唱与审歌能力
│   ├── mv/ mv-*              制 MV、卡点、字幕与合成能力
│   └── ad/ ad-*              广告片创意、生产与交付能力
├── tools/
│   ├── shared-cleanup/       仓库级清理 dev 工具
│   └── independence-audit/   系列独立性静态审计
├── .claude/skills -> ../skills
├── 制漫剧/<项目>/             漫剧工程与成片产物
├── 写歌/<项目>/               歌曲工程与成品歌
├── 制MV/<项目>/               MV 工程与成片
├── 拍广告/<项目>/             广告工程与交付件
├── 资产库/                    跨项目复用资产
└── docs/images/              文档截图
```

## 维护边界

根 README 只放快速开始和稳定约定。具体阶段、脚本参数、后端差异、验收标准放在对应 `skills/<name>/SKILL.md` 和 `references/` 里。这样可以避免 README 变成第二份过期索引。
