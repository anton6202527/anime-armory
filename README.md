# anime-armory

小说生产工具库 —— 两大可复用 Claude Code skill 系列，各管一条产线、各有独立产物文件夹。

| 系列 | 调度入口 | 成员 skill | 干什么 | 产物落 |
|---|---|---|---|---|
| **novel2drama 系列** | `novel2drama` | `n2d-script` / `n2d-image` / `n2d-video` | 小说 → **AI 漫剧 / 短剧**（分镜/出图/出视频/字幕，对接即梦·可灵·Seedance·Veo）| **`制漫剧/`** |
| **novel-author 系列** | `novel-author` | `novel-fetch` / `novel-title` / `novel-spinoff` / `novel-rewrite` / `novel-continue` / `novel-expand` / `novel-condense` / `novel-craft` / `novel-review` | **纯文本小说生产**（联网取公版 / 起书名 / 配角视角外传 / 改写魔改 / 续写 / 扩写 / 精简 / 写作工艺 / 质检审稿）| **`写小说/`** |

> 两系列在交界处衔接：`novel-author` 写好的小说可交给 `novel2drama` 改编成漫剧（产物从 `写小说/` 流向 `制漫剧/`）。
> skill 目录在 `.claude/skills/` 下保持扁平（按 `novel2drama`/`n2d-*` 与 `novel-author`/`novel-*` 前缀分族），因为 Claude Code 只发现一层 `*/SKILL.md`。

---

## 目录结构

```
anime-armory/
├── .claude/skills/                  ← 两系列（扁平，按前缀分族）
│   │  ── novel2drama 系列 ──
│   ├── novel2drama/                 Stage 0 调度（扫作品根→读 _进度.md→推荐下一步）
│   ├── n2d-script/                  Stage 1 拆集 + 8 类素材（scripts/split_novel.py）
│   ├── n2d-image/                   Stage 2 出图 prompt + 生图（两层架构 + 5 步 SOP + 扫 CLI）
│   ├── n2d-video/                   Stage 3 出视频 prompt + 生视频（image2video + 扫 CLI）
│   │  ── novel-author 系列 ──
│   ├── novel-author/                调度（路由到下面子 skill）+ 家族经验沉淀(Q&A)
│   ├── novel-fetch/                 联网抓公版小说 → txt+docx
│   ├── novel-title/                 起书名（5 维评分）
│   ├── novel-spinoff/               配角视角并行外传（锚点锁定，init_project/export 脚本）
│   ├── novel-rewrite/               改写/重构/魔改（改动spec + 新设定圣经，与外传镜像）
│   ├── novel-continue/              续写后续章节
│   ├── novel-expand/ novel-condense/ 扩写 / 精简
│   ├── novel-craft/                 写作工艺基元（章纲/单章/扩缩，被其他 skill 引用）
│   └── novel-review/                已写章节质检/审稿（机检脚本 + 两层 checklist）
│
├── 制漫剧/                          ← novel2drama 系列产物（1 剧 = 1 顶层文件夹）
│   └── 冷宫有妖气/
│       ├── 小说/  common/(_进度.md·global_style·characters·locations·废料)
│       ├── 脚本/第N集/      分镜剧本·故事板·素材清单·配音·BGM·封面·字幕中/英
│       ├── 出图/(common 定妆库 + 第N集 分镜图)
│       └── 出视频/第N集/    clips prompt + mp4
│
└── 写小说/                          ← novel-author 系列产物（1 部 = 1 顶层文件夹）
    └── 仙界闭关小能手-王敦外传/      （王敦视角并行外传 = 调用 novel-spinoff）
        ├── _meta.json  原作.txt  _进度.md
        ├── 设定/(角色卡·世界观·锚点表·章纲·书名候选)
        ├── 章节/第NN章.md
        ├── 审稿/(审稿报告.md + arc 明细)   ← novel-review 产物
        └── 导出/(<书名>.txt/.docx/大纲.md)
```

## 快速开始（在 Claude Code 中）

**做漫剧**：`/novel2drama <小说路径或制漫剧/项目>` → 按 Stage 跑 `/n2d-script` → `/n2d-image` → `/n2d-video`。
**写/审小说**：`/novel-author <书名/路径/动作>` 路由，或直接调
- `/novel-fetch <书名>`（取公版）、`/novel-title`（起名）、`/novel-spinoff <原作> <配角>`（外传）、`/novel-continue`（续写）、`/novel-review <写小说/项目>`（质检）。

## 当前进度

- **制漫剧/冷宫有妖气**：第 1–15 集已全套精修（定妆照 + 双语字幕）；第 1–9 集附即梦/可灵/Veo 三平台适配。详见 `制漫剧/冷宫有妖气/common/_进度.md`。
- **写小说/仙界闭关小能手-王敦外传**：82 章规划，01–37 已写（Demo 1–3 + 11–37 + 补齐 4–10）；Ch11–37 已过 `novel-review` 全量审稿（见 `审稿/审稿报告.md`，3 个 🔴 待修）。详见项目 `_进度.md`。

## 说明

- 仓库私有。`制漫剧/冷宫有妖气/小说/*.docx`、`写小说/仙界闭关小能手-王敦外传/原作.txt` 为版权原文（用户为《仙界闭关小能手》作者本人，对其派生创作拥有权利）；如需公开先移除版权原文。
- 字幕 SRT 时间码为按故事板推导的初稿，成片时在剪辑软件内微调。
