# anime-armory

小说 → **AI 漫剧 / 短剧** 工业化生产工具与素材库。

包含一个可复用的 Claude Code skill **`novel2drama`**，以及用它生产的示例项目《冷宫有妖气》全套素材。

---

## 这是什么

把一部长篇小说，自动拆分并精修成可直接进入 AI 视频流水线的**逐集生产素材**：分镜剧本、角色/场景卡（含定妆照）、图片 prompt、视频 prompt、配音文案、BGM、封面、中英双语字幕。

- **平台无关核心 + 平台档案**：分镜/卡片/节拍/字幕与平台无关；各平台（**即梦AI**默认 / **可灵Kling** / **Seedance** / **Veo·海外**）的差异收敛到「平台档案」，跨平台只换"视频生成适配层"。
- **一致性第一**：角色首次出现即建卡 + 定妆照，作为"角色参考/图生图"锚点，所有镜头与视频首帧复用，锁脸锁妆造。
- **集 = 戏剧节拍单元，≠ 章**：脚本拆分只是粗胚，集边界由导演按爽剧节拍（冲突→爽点→反转→钩子）重切。

## 目录结构

```
anime-armory/
├── .claude/skills/novel2drama/        ← 可复用 skill
│   ├── SKILL.md                       主流程（导演系统 + 工作流）
│   ├── scripts/split_novel.py         自动拆集 + 建目录骨架（.txt/.docx）
│   └── references/
│       ├── formats.md                 9 类素材的标准格式模板
│       └── platforms.md               即梦/可灵Kling/Seedance/Veo 平台档案 + 新增平台指南
└── artifacts/冷宫有妖气/              ← 示例产出
    ├── 冷宫有妖气.docx                 小说原文
    └── 分镜剧本/                       与小说同级的素材库
        ├── global_style.md            全局画风/世界观/目标平台
        ├── characters/  locations/    角色卡（含定妆照）/ 场景卡 + 总表
        ├── _进度.md                    逐集逐项进度勾选
        └── 第N集/                      每集：raw.txt + 分镜剧本/故事板/素材清单
                                        /voiceover/bgm/封面 + 字幕_中文.srt/字幕_英文.srt
                                        （第1集另含 可灵Kling适配.md 跨平台样例）
```

## 快速开始（在 Claude Code 中）

1. 触发 skill：对 Claude 说「把这个小说转成 AI 漫剧素材：<小说路径>」，或 `/novel2drama <小说路径>`。
2. 自动拆集 + 建骨架：
   ```bash
   python3 .claude/skills/novel2drama/scripts/split_novel.py "<小说路径>"
   # 按章节边界切（更贴戏剧节拍）：
   python3 .claude/skills/novel2drama/scripts/split_novel.py "<小说路径>" --by-chapter
   ```
   默认输出到 `<小说所在目录>/分镜剧本/`，并自动剥离开头简介/标签等元数据。
3. 先定全局：精修 `global_style.md`（画风/世界观/目标平台）+ 为主要角色/场景建卡（含定妆照）。
4. 逐集精修 7 类素材（格式见 `references/formats.md`），跨平台 prompt 适配见 `references/platforms.md`。

## 当前进度（《冷宫有妖气》）

第 1–4 集已全套精修（含定妆照、双语字幕）；第 1 集附可灵 Kling 跨平台适配样例。其余集为待精修骨架。详见 `artifacts/冷宫有妖气/分镜剧本/_进度.md`。

## 说明

- 仓库为私有。`冷宫有妖气.docx` 为第三方小说原文，仅作内部生产用途；如需公开请先移除原文与受版权保护的素材。
- 字幕 SRT 的时间码为按故事板推导的初稿，套到成片时在剪辑软件内微调。
