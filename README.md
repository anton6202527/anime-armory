# anime-armory

**AI 创作内容工厂** —— 一套可复用的 Claude Code skills，覆盖 **写小说→制漫剧**、**写歌→制MV** 两组「创作线 × 生产线」，外加公共换脸能力。仓库内的现有作品（`写小说/`·`制漫剧/`·`写歌/`·`制MV/`）是 **demo 演示**，展示这套 skill 的产出。

> skill 详细索引见 [`.claude/skills/README.md`](.claude/skills/README.md)；本文件是项目总览。

---

## 四条线：创作线 × 生产线

成对、两两对应、**互不依赖**——创作线产成品（小说/歌），生产线把它做成视频（漫剧/MV）。衔接只在**成品文件层面**，不是 skill 依赖。

| 创作线（产成品） | 生产线（成品→视频） | 产物落 |
|---|---|---|
| **写小说** `novel-author` + `novel-*`<br>原创从零 / 取公版 / 起书名 / 外传 / 改写魔改 / 续写 / 扩写 / 精简 / 工艺 / 审稿 | **制漫剧** `novel2drama` + `n2d-*`<br>拆集→配音→分镜→出图→出视频→合成（即梦/可灵/Seedance/Veo） | `写小说/`<br>`制漫剧/` |
| **写歌** `song` + `song-*`<br>访谈作词 / 作曲+演唱 / 翻唱换声 | **制MV** `mv` + `mv-*`<br>卡点→出图→出视频→卡拉OK字幕→合成（自包含，不复用 n2d-*） | `写歌/`<br>`制MV/` |

**公共能力**（不属任何家族，谁都能调）：
- `video-faceswap` / `image-faceswap` —— 视频/图片换脸（FaceFusion 本地底座）+ 强制 AI 标识，**仅本人/授权/合成脸**，带合规闸门。

每条线各有一个**调度入口** skill（`novel2drama` / `novel-author` / `song` / `mv`），读项目 `_进度.md` 路由到对应阶段。

---

## 设计原则：skill 通用，选择私有

- **skill 保持通用**：不把平台/后端/分辨率/时长写死成唯一路径。凡「让用户选」的都是**选择点**。
- **选择是私有的**，存在用户自己的空间、不进共享 skill 代码：
  - 每作品 `<作品根>/_设置.md`（权威，与 `_进度.md` 并列）
  - 全局默认 [`.claude/创作偏好-默认.md`](.claude/创作偏好-默认.md)（跨项目个人默认，随私有库多机同步，开新项目预填）
- **行为**：选择点首次问一次 → 写 `_设置.md` → 同项目沉默沿用；合规/不可逆/花钱多的点每次仍确认。
- 机制与全部选择点目录见 [`.claude/skills/_偏好约定.md`](.claude/skills/_偏好约定.md)。

几个已固化的默认（都可在 `_设置.md` 改）：
- 生视频/生图 = 即梦；视频分辨率 = 720p（可 1080p）
- 配音 = CosyVoice；作曲 = Suno（云）
- **单集时长 = 验收区间**：默认「前长后短」第1集 120–180s / 其余集 60–120s——最终切多长**由爽点/钩子等节拍锚定，落进区间即可**（字数只切粗胚→节拍重切→配音实测）。

---

## 本地 AI 后端（Apple Silicon）

| 用途 | 后端 | 位置 |
|---|---|---|
| 配音（声音克隆） | CosyVoice / Fish-Speech | `~/CosyVoice` · `~/fish-speech`（conda env，本地 server） |
| 作曲（出整首歌） | ACE-Step（本地，短样可跑）/ **Suno 云（整首推荐）** | `~/ACE-Step` |
| 换脸 | FaceFusion（onnxruntime CoreML） | `~/facefusion`（conda env `facefusion`，py3.12） |

> 云后端（Suno/即梦/可灵等）凭证缺失时各 skill 会优雅回退（如配音回退 macOS `say` 占位）。

---

## 目录结构

```
anime-armory/
├── README.md  TODO.md  .gitignore
├── .claude/
│   ├── 创作偏好-默认.md            ← 私有全局默认偏好（随库同步）
│   └── skills/                     ← 全部自定义 skill（扁平，按前缀分族）
│       ├── _偏好约定.md            通用偏好机制 + 选择点目录
│       ├── README.md               skill 索引
│       ├── novel-author/ novel-*   写小说（create/fetch/title/spinoff/rewrite/
│       │                           continue/expand/condense/craft/review）
│       ├── novel2drama/ n2d-*       制漫剧（script/voice/image/video/compose）
│       ├── song/ song-*            写歌（lyrics/compose/cover）
│       ├── mv/ mv-*                制MV（beat/image/video/lyric-sync/compose）
│       └── video-faceswap/ image-faceswap/   公共换脸
│
├── 写小说/<项目>/                  ← 写小说产物（设定/章节/审稿/导出 + _进度.md + _设置.md）
├── 制漫剧/<剧名>/                  ← 制漫剧产物（小说/脚本/出图/出视频/成片 + common/_进度.md）
├── 写歌/<曲名>/                    ← 写歌产物（词/lyrics.md + 歌/song.wav + _进度.md）
└── 制MV/<曲名>/                    ← 制MV产物（节拍/出图/出视频/字幕/成片_MV.mp4）
```

## 快速开始（在 Claude Code 中）

- **写小说**：`/novel-author <书名/路径/想法/动作>` 路由；或直接 `/novel-create`（从零原创）、`/novel-fetch <书名>`、`/novel-spinoff <原作> <配角>`、`/novel-review <项目>`。
- **做漫剧**：`/novel2drama <小说路径或 制漫剧/项目>` → `/n2d-script` → `/n2d-voice` → `/n2d-script`(分镜) → `/n2d-image` → `/n2d-video` → `/n2d-compose`。
- **写歌**：`/song <主题/想法>` → `/song-lyrics` → `/song-compose`（→ `/song-cover` 可选）。
- **做MV**：`/mv <成品歌或 制MV/曲名>` → `/mv-beat` → `/mv-image` → `/mv-video` → `/mv-lyric-sync` → `/mv-compose`。
- **换脸**：`/image-faceswap`（图）/ `/video-faceswap`（视频）—— 先过合规闸门。

## 当前进度

- **制漫剧/冷宫有妖气**：第 1–15 集全套精修（定妆 + 双语字幕）；详见 `制漫剧/冷宫有妖气/common/_进度.md`。
- **写小说/**：`仙界闭关小能手-王敦外传`（外传）、`阿蒙乌沙`、`尼罗河黑墓`、`秦陵寻踪` —— 各项目进度见其 `_进度.md`。
- **写歌+制MV/仗剑下山**：成品歌（`写歌/仗剑下山/歌/song.wav`）+ MV 成片（`制MV/仗剑下山/成片_MV.mp4`）。

## 说明

- **现有作品 = demo 演示**：`写小说/`·`制漫剧/`·`写歌/`·`制MV/` 下的成品是展示 skill 产出的样例，可随意参考。
- **只想拿工具**：如果你想把这套 skill 单独拿去用、不带这些 demo 作品，见 [`TODO.md`](TODO.md)（如何剥离个人内容做成干净模板）。
- **版权**：demo 所用原文为作者本人作品 / 公版 / 已授权；**复用本工具时请自备合法素材**，公版/自有/已授权为准。
- **换脸合规**：换脸/克隆真人 = deepfake，强监管——仅本人/授权/合成脸，强制 AI 标识水印，绝不抹标识。
