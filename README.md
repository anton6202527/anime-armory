# anime-armory

小说 → **AI 漫剧 / 短剧** 工业化生产工具与素材库。

包含一组可复用的 Claude Code skill — **`novel2drama` 调度 + 可选 `n2d-fetch`（联网取书）+ `n2d-script` / `n2d-image` / `n2d-video` 三阶段**，以及用它生产的示例项目《冷宫有妖气》全套素材。

---

## 这是什么

把一部长篇小说，自动拆分并精修成可直接进入 AI 视频流水线的**逐集生产素材**：分镜剧本、角色/场景卡（含定妆照）、图片 prompt、视频 prompt、配音文案、BGM、封面、中英双语字幕。

- **平台无关核心 + 平台档案**：分镜/卡片/节拍/字幕与平台无关；各平台（**即梦AI**默认 / **可灵Kling** / **Seedance** / **Veo·海外**）的差异收敛到「平台档案」，跨平台只换"视频生成适配层"。
- **一致性第一**：角色首次出现即建卡 + 定妆照，作为"角色参考/图生图"锚点，所有镜头与视频首帧复用，锁脸锁妆造。
- **集 = 戏剧节拍单元，≠ 章**：脚本拆分只是粗胚，集边界由导演按爽剧节拍（冲突→爽点→反转→钩子）重切。

## 目录结构

```
anime-armory/
├── .claude/skills/
│   ├── novel2drama/                       ← Stage 0 调度
│   │   ├── SKILL.md                       薄路由：扫作品根 → 读 _进度.md → 推荐下一步该调哪个 skill
│   │   ├── Q&A.md                         全阶段实战 Q&A 沉淀
│   │   └── references/architecture.md     四阶段流水线总览 + 目录铁律 + 首跑示范
│   ├── n2d-fetch/                         ← Stage 0.5（可选）：联网抓公版小说 → txt+docx
│   │   ├── SKILL.md                       搜候选 → 确认 → 跑脚本 → 落 小说/ + 合法性铁律
│   │   ├── scripts/fetch_novel.py         站点适配器(Gutenberg/Wikisource)+通用兜底+txt/docx 双输出
│   │   └── references/{sources,formats}.md
│   ├── n2d-script/                        ← Stage 1：拆集 + 8 类素材
│   │   ├── SKILL.md
│   │   ├── scripts/split_novel.py         自动拆集 + 建目录骨架
│   │   └── references/{formats,platforms}.md
│   ├── n2d-image/                         ← Stage 2：出图 prompt + 生图
│   │   ├── SKILL.md                       两层架构（共享定妆 + 本集分镜）+ 5 步 SOP + 扫 CLI/手动指导
│   │   └── references/{prompt_format,platforms,cli_registry}.md
│   └── n2d-video/                         ← Stage 3：出视频 prompt + 生视频
│       ├── SKILL.md                       Clip prompt 派生 + image2video + 扫 CLI/手动指导
│       └── references/{prompt_format,platforms,cli_registry}.md
└── artifacts/冷宫有妖气/                  ← 示例产出（1 skill = 1 顶层文件夹）
    ├── 小说/冷宫有妖气.docx                小说原文
    ├── common/                             跨阶段共用资产
    │   ├── _进度.md                        全作品 dashboard
    │   ├── global_style.md                 全局画风/世界观/目标 AI
    │   ├── characters/                     角色卡（含定妆 prompt 源头）
    │   ├── locations/                      场景卡
    │   └── 废料/                           4 选 1 / 废图 / 废视频
    │       ├── 出图/{common,第N集}/
    │       └── 出视频/第N集/
    ├── 脚本/第N集/                         ← Stage 1：n2d-script 产物
    │                                        raw.txt + 分镜剧本.md/故事板/素材清单
    │                                        + voiceover/bgm/封面 + 字幕_中文/英文.srt
    ├── 出图/                               ← Stage 2：n2d-image 产物
    │   ├── common/                         扁平：00_索引 + 角色/场景/道具定妆.md + 定妆_*.png
    │   └── 第N集/                          prompt/（00_总览.md + 01_分镜出图.md）+ 镜头N_*.png
    └── 出视频/第N集/                       ← Stage 3：n2d-video 产物
                                             prompt/（00_总览.md + 01_clips.md）+ ClipK_*.mp4
```

## 快速开始（在 Claude Code 中）

1. **首跑**：对 Claude 说「把这个小说转成 AI 漫剧素材：<小说路径>」，或 `/novel2drama <小说路径>` — 调度会推荐你跑 `/n2d-script`。
2. **Stage 1**：`/n2d-script <小说路径>` 自动拆集 + 精修第 1 集物料（8 类素材 + 全局/角色/场景）。也可直接跑脚本：
   ```bash
   python3 .claude/skills/n2d-script/scripts/split_novel.py "<小说路径>"
   python3 .claude/skills/n2d-script/scripts/split_novel.py "<小说路径>" --by-chapter
   ```
3. **Stage 2**：`/n2d-image <作品根> 第N集` — 生成两层出图 prompt（共享 + 本集），扫本机生图 CLI（dreamina / gemini-cli / ...）或一步步指导手动跑即梦 web。
4. **Stage 3**：`/n2d-video <作品根> 第N集` — 从故事板派生视频 prompt，扫本机生视频 CLI 或指导手动跑。
5. **路由不确定时**：调 `/novel2drama <作品根>`，它会读 `_进度.md` 报告"当前在哪一阶段、下一步调谁"。

## 当前进度（《冷宫有妖气》）

第 1–15 集已全套精修（含定妆照、双语字幕）；第 1–9 集附即梦/可灵/Veo 三平台适配样例。其余集为待精修骨架。详见 `artifacts/冷宫有妖气/common/_进度.md`。

## 说明

- 仓库为私有。`冷宫有妖气.docx` 为第三方小说原文，仅作内部生产用途；如需公开请先移除原文与受版权保护的素材。
- 字幕 SRT 的时间码为按故事板推导的初稿，套到成片时在剪辑软件内微调。
