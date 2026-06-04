# Skills 索引

本项目的自定义 skills 按 创作线×生产线 + 公共能力 组织（写小说→制漫剧、写歌→制MV，外加公共 video-faceswap / image-faceswap 换脸）。**目录保持扁平**（每个 skill 仍是 `skills/<name>/SKILL.md`）——
skill 之间用 `<skills>/<name>/...` 互相引用，故**不要**移进子目录，否则交叉引用与 skill 发现会失效。
本文件仅作分类说明。

> **工具中立 / 跨 AI 使用**：真身在仓库根 `skills/`，**不绑定任何特定 AI**。
> - **Claude Code** 经软链 `.claude/skills → ../skills` 自动发现并用 `Skill` 工具按触发词路由（无需改动）。
> - **其他 AI agent / 人**：直接读 `skills/<name>/SKILL.md`（= 这个 skill 干啥、何时用；frontmatter 的 `description` + 正文 `Triggers` 就是路由依据），照其说明做事，需要时跑 `skills/<name>/scripts/` 下的脚本。
> - **脚本是通用的**：纯 Python/bash，只调通用工具（ffmpeg / librosa / whisper / yt-dlp / 生图生视频 CLI 等），**无任何 Claude 专有 API**，谁都能执行。引用一律走中立路径 `skills/...`（旧 `.claude/skills/...` 经软链仍兼容）。

> **偏好约定（通用化原则）**：所有 skill 保持**通用**，不把平台/后端/分辨率写死成唯一路径。凡「让用户选」的点都是**选择点**，用户的实际选择是**私有的**，存在用户自己的空间——每作品 `<作品根>/_设置.md`（权威）+ 私有全局默认（memory 区 `创作偏好-默认.md`，开新项目预填），**不进共享 skill 代码 / 不进 git**。行为：选择点首次问一次→写 `_设置.md`→同项目沉默沿用；合规/不可逆/花钱多的点每次仍确认。机制与全部选择点目录见 [`_偏好约定.md`](_偏好约定.md)；每个 skill 有「## 偏好（私有）」段引用它。**新增选择点**→加进 `_偏好约定.md` 目录，别在正文写死。

---

## 一、n2d ——「小说 → AI 漫剧/短剧」生产管线

`novel2drama` 是总调度，按 `_进度.md` 把用户路由到对应阶段 skill。阶段顺序：

| 阶段 | Skill | 职责 |
|---|---|---|
| 调度 | `novel2drama` | 检查 作品 根目录，读 `_进度.md`，路由到下面的阶段 |
| 1 剧本改编 | `n2d-script` | 拆集 + 配音台词/BGM/封面/角色场景卡/global_style；配音后回跑做分镜设计 |
| 2 配音 | `n2d-voice` | voiceover.txt → 角色配音 + 拼接音轨 + 时长清单.json（驱动下游镜头时长） |
| 3 出图 | `n2d-image` | 两层出图 prompt（定妆库 + 本集分镜）→ 即梦/gemini/DALL-E/Flux 生图 |
| 4 出视频 | `n2d-video` | 由故事板生成每 Clip 视频 prompt → 即梦/可灵/Veo/Seedance 图生视频 |
| 5 合成 | `n2d-compose` | 拼 视频 clips + 配音 + BGM + 烧双语字幕 → 成片 |

## 二、novel ——「写小说」创作工坊

`novel-author` 是总调度，按输入（几个字/想法/书名/URL/路径/配角名/扩缩需求）路由到下面的子 skill。

| Skill | 职责 |
|---|---|
| `novel-author` | 顶层分派器，只路由不写作 |
| `novel-create` | **原创从零·访谈引导**：只有几个字/想法/部分风格/碎片时，访谈→创作蓝图→设定圣经→章纲→Demo→成书（家族里唯一从零生成，其余都需既有源） |
| `novel-title` | 头脑风暴 5–8 个书名候选，5 维打分排序 |
| `novel-fetch` | 按书名/章节目录 URL 联网抓公版小说全文 → txt + docx |
| `novel-craft` | 写作工艺共享库（章纲编织/单章守则/扩写/精简），被其他 novel-* 按路径引用 |
| `novel-expand` | 短篇 → 长篇：在保留事件骨架前提下加细节 |
| `novel-condense` | 长篇 → 短版：砍描写/支线/重复内心戏，并章 |
| `novel-continue` | 续编（完本后写续集）/ 接更（接未完本往后写） |
| `novel-rewrite` | 改写/魔改/翻拍：改主线、加原创设定的转化型重写 |
| `novel-spinoff` | 配角平行视角外传，锚点处锁定原作事件 |
| `novel-review` | 审稿质检：串视角/人设崩/设定矛盾/锚点漂移/原文照搬，出定位报告 |

## 三、song ——「写歌」创作线（词 + 曲 + 演唱 → 成品歌）

`song` 是总调度，从主题/几个字/曲风 → 一首带人声的成品歌。与 novel-author(写小说) 平行的创作线；产物落 `写歌/<曲名>/`（`词/lyrics.md` + `歌/song.wav`），交给 制MV(mv) 做视频。

| Skill | 职责 | 状态 |
|---|---|---|
| `song` | 写歌总调度 | ✅ |
| `song-lyrics` | 访谈式作词 + 作词工艺知识库（结构/押韵/字数贴旋律/hook），**零安装** | ✅ |
| `song-compose` | 词→带人声的歌：云 Suno / 本地 ACE-Step(Mac可跑) / DiffRhythm | ✅ |
| `song-cover` | 翻唱/换声：RVC / so-vits-svc | ✅ |

> 唱歌的声音要装东西：TTS（CosyVoice/FishSpeech）不能唱；唱歌走音乐生成模型(Suno/ACE-Step)或歌声转换(RVC)。**克隆真人嗓需授权（2026 opt-in）。**

## 四、mv ——「制MV」生产线（成品歌 → AI 音乐 MV 视频）

`mv` 是总调度，**输入 = 一首已做好的歌**（来自 写歌/ 或用户给），产物落 `制MV/<曲名>/成片_MV.mp4`。与 novel2drama(制漫剧) 平行：**写歌→制MV**，正如 **写小说→制漫剧**。**完全独立、自包含——不复用 n2d-* 或任何家族 skill**。

| 阶段 | Skill | 职责 | 状态 |
|---|---|---|---|
| 调度+立项 | `mv` | 扫 制MV 根，拷入歌+词，定视觉蓝图，路由 | ✅ |
| 卡点 | `mv-beat` | librosa 检测 BPM+鼓点 → beatgrid | ✅ |
| 出图 | `mv-image` | mv 自建：共享定妆 + 分段分镜 PNG | ✅ |
| 出视频 | `mv-video` | mv 自建：图生视频（按段落+卡点） | ✅ |
| 卡拉OK字幕 | `mv-lyric-sync` | whisperx 词级对齐 → karaoke.ass | ✅ |
| 合成 | `mv-compose` | 歌轨 + 卡点剪辑 + 卡拉OK烧录 → 成片_MV.mp4（自带 mv_compose.sh + render_lyrics.py） | ✅ |

> 独立铁律：mv-* 即便与 n2d 逻辑相似也各写各的；只用通用外部工具（非 skill）。

## 公共能力（不属任何家族，谁都能调）

| Skill | 职责 |
|---|---|
| `video-faceswap` | 通用**视频**换脸（FaceFusion，Mac可跑）+ 强制 AI 标识；**仅本人/授权/合成脸**，带合规闸门。制MV/制漫剧/单独使用都可调 |
| `image-faceswap` | 通用**图片**换脸（同 FaceFusion 底座，单图秒级）+ 强制 AI 标识（图片版打标 label_watermark_image.py）；**仅本人/授权/合成脸**，带合规闸门。出图阶段/单独使用都可调 |

> 换脸/克隆真人 = deepfake，2026 强监管：须**肖像同意 + AI 标识水印**（中国《标识办法》、US DEFIANCE/NO FAKES）；video-/image-faceswap 已内置合规闸门，仅本人/授权/合成脸，且强制打标。两者共用同一 FaceFusion 安装，视频版打标走 ffmpeg、图片版走纯 Pillow。

---

> 四条线两两对应、**互不依赖**：**写小说→制漫剧**、**写歌→制MV**。创作线产成品（小说/歌）→ 生产线做视频（漫剧/MV）。衔接只在成品文件层面，不是 skill 依赖。换脸是公共 `video-faceswap`（视频）/ `image-faceswap`（图片）。
