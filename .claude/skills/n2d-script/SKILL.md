---
name: n2d-script
description: Stage 1 of novel2drama pipeline — split a novel (.txt/.docx) into per-episode dramatic beats and produce the 8 per-episode material types (分镜剧本 / 故事板 / 素材清单 / 配音 / BGM / 封面 / 字幕中 / 字幕英) plus the shared global_style.md, characters/ and locations/. Use when given a novel path (first run = split + refine episode 1) or asked to refine a specific episode's materials. Triggers 拆集, 分镜剧本, 故事板, 素材清单, 配音文案, BGM, 封面 prompt, 双语字幕, SRT, 角色卡, 场景卡, global_style.
---

# n2d-script — Stage 1：拆集 + 8 类素材

你是 **AI 漫剧编剧/导演**。本 skill 只关心 Stage 1：从小说到"可进入出图阶段"的全部文本素材。**不出图、不出视频**——那是 `n2d-image` 和 `n2d-video` 的事。

## 核心原则

- **集 = 戏剧节拍单元，≠ 章**：一集是一个完整爽剧节拍（冲突→爽点→反转→钩子），边界由导演按节拍定。`split_novel.py` 拆出的只是**粗胚脚手架**；精修时以 `raw.txt` 为素材按节拍重切。
- **角色/场景一致性第一**：先建卡（含定妆 prompt），后续所有分镜严格复用。形态变体（觉醒态/银牌态）单列。
- **平台无关核心 + 平台档案**：分镜/卡片/节拍/字幕都平台无关；各平台档案见 `references/platforms.md`。默认 = 即梦AI。
- **爽剧节奏**：每集约 90~120 秒、8~15 镜头；前 3 秒冲突、前 15 秒矛盾、中段情绪提升、结尾钩子、每集 ≥1 次反转。
- **画风统一**：依项目 `global_style.md`；禁止低幼Q版/画风漂移。

## 入口

**情境 A — 首次拿到小说**（作品根不存在）：
执行"第 1 步 拆集 + 建骨架" → "第 2 步 全局" → "第 3 步 精修第1集"。完成后报告，让用户决定继续精修后续集或调 `/n2d-image` 出图。

**情境 B — 精修某具体集**（作品根已存在）：
跳到"第 3 步 精修该集"。先读 `_进度.md` 看该集物料列状态。

## 工作流

### 第 0 步 — 确认双轴

跟用户确认（缺省即用默认）：
- 小说路径
- **目标视频 AI**（决定最终成片风格 + image2video 运动估计分布）—— 默认即梦；可选 可灵 / Seedance / Veo
- **目标图 AI**（出图工具）—— 默认 = 同视频 AI；可独立选 Gemini / DALL-E / Flux 等

详见 `references/platforms.md` 的"两轴架构"章节。**输出位置 = 作品根（与 `小说/` 同级）**：8 类素材进 `脚本/第N集/`；全局 `_进度.md` / `global_style.md` / `characters/` / `locations/` 进作品根的 `common/`。把两个 AI 都记到 `common/global_style.md` 顶部。

> **关键铁律**：若**图 AI ≠ 视频 AI**，所有 image prompt 末尾**必须**拼接对应视频 AI 的"图像风格锚定句"（详细在 `n2d-image` skill 里）。Stage 1 这里只负责把决策写进 `global_style.md` 顶部。

### 第 1 步 — 自动拆集 + 建骨架

```bash
python3 <skill>/scripts/split_novel.py "<小说路径>"
# 按章节边界 + 字数双约束切（更贴戏剧节拍）：
python3 <skill>/scripts/split_novel.py "<小说路径>" --by-chapter
```

脚本默认按 ~1000 字/集 在段/句边界切分，自动剥离开头的简介/标签/看点等元数据（`--keep-frontmatter` 可保留）。

**约定**：小说应放在 `制漫剧/<剧名>/小说/<剧名>.docx`。若用户给的是裸文件，先 mv 进去。**默认输出到 `制漫剧/<剧名>/`**（作品根直接铺各阶段子文件夹）。

生成的骨架：

```
制漫剧/<剧名>/
├── 小说/<剧名>.docx          ← 原文
├── common/
│   ├── _进度.md              逐集勾选进度表
│   ├── global_style.md       全局画风/世界观（第 2 步精修）
│   ├── characters/           角色卡（第 2 步建卡）
│   └── locations/            场景卡（第 2 步建卡）
└── 脚本/
    └── 第N集/
        └── raw.txt           拆集出来的原文片段
```

向用户报告：输出路径、共拆几集、字数范围。

> ⚠️ **拆分是粗胚脚手架，不是最终集边界**（一章 ≠ 一集）。第 3 步精修时以 `raw.txt` 为素材按戏剧节拍重切：一个节拍可跨多章合并、长章可拆上/下集。集数与 raw 分块不必一一对应。

### 第 2 步 — 先定全局（只做一次）

1. 通读小说（或抽样若干集）确定 `global_style.md`：
   - 顶部记 **目标视频AI** + **目标图AI**
   - 画风词、世界观、统一负面词
2. 为**主要角色/场景**建卡，存入 `common/characters/`、`common/locations/`。格式见 `references/formats.md §1 §2`：
   - 角色卡必含**妆造拆解**（发型/妆容/服装/配饰/色卡）+ **① 定妆照 prompt**（A-pose 全身 + 脸部特写、干净背景、中英双版）+ **② 出镜 prompt**
   - **本 skill 只生成 prompt 文本**——实际出定妆照在 Stage 2 (`/n2d-image`) 做
3. 新角色/场景在其首次出现的那一集补建卡。

### 第 3 步 — 逐集精修 8 类素材

先按戏剧节拍确定本集边界（合并/拆分 `raw.txt`，一章 ≠ 一集），再按 `references/formats.md` 填写：

1. `分镜剧本.md` — 逐镜头脚本（画面视觉描述 / 台词·音效·旁白）
2. `故事板.md`（**草稿**）— Clip 表（相邻分镜合成片段；写清人物运动 + 镜头运动 + 动态细节；**Clip 时长留空/标 TBD —— 时长在配音后由 /n2d-voice 的时长清单定稿，本步不锁**；运镜按目标视频 AI 档案）
3. `素材清单.md` — 角色/场景/道具的 AI 图片 prompt（复用角色卡锚定，中文 + 英文）
4. `voiceover.txt` — 逐镜头配音文案（角色·情绪）
5. `bgm.txt` — 整体情绪 + BGM 风格 + 关键音效点
6. `封面.md` — 高点击率封面/首图 prompt
（注：`字幕_中文.srt` / `字幕_英文.srt` **不在本步生成**。它们的时间轴必须由真实配音时长决定 → 在 /n2d-voice 跑完后，于本 skill 的**阶段2 定稿**生成，见下。本步只产出英文字幕**文本草稿**供阶段2 重定时用。）

完成后在 `_进度.md` 勾选阶段1 物料列：分镜剧本 / 草稿故事板 / 素材清单 / 配音文案(voiceover) / bgm / 封面 / 字幕英(草稿文本) ✅。**下一步是 /n2d-voice 配音**（不是出图）。

> **本 skill 不写出图 prompt**（即 `出图/common/` 与 `出图/第N集/` 下的所有 prompt + PNG）。物料齐后用户调 `/n2d-image`，那个 skill 才负责出图 prompt 两层架构。

**批量提示**：用户要"一次多集"时，逐集复用同一批角色卡/场景卡，保证跨集一致；不要重新发明角色外貌。

### 第 4 步 — 报告 + 推进

每集物料齐后：

```
第K集 阶段1 物料齐：
- 分镜剧本 / 草稿故事板(时长未锁) / 素材清单 / voiceover / bgm / 封面 / 字幕英草稿 ✅
- _进度.md 已勾选阶段1 列
下一步建议：
- 调 /n2d-voice <作品根> 第K集  生成配音 + 时长清单（**配音先于出图**）
- 配音齐后回跑 /n2d-script 阶段2 定稿故事板时长 + SRT
```

## 阶段2 — 故事板/字幕定稿（配音后回跑本 skill）

**触发**：该集 `配音` 列 ✅（/n2d-voice 已产 `出视频/第N集/配音/时长清单.json`）后，回跑本 skill 做定稿。`配音` 列未 ✅ 时拒绝定稿并提示先 /n2d-voice。

**做两件事**：
1. 生成真实时间轴的 SRT + 每镜时长：
   ```bash
   python3 <skill>/finalize_storyboard.py <作品根> 第N集
   ```
   产出 `脚本/第N集/字幕_{中文,英文}.srt`（按配音逐句实测时长重定时）+ `脚本/第N集/镜头时长.json`（每镜聚合时长）。
2. 用 `镜头时长.json` **锁定 `故事板.md` 的 Clip 时长**：每个 Clip 时长 = 其包含分镜的镜头时长之和；单 Clip 超目标视频 AI 上限（如即梦 ≤8s）则**拆 Clip**（尾帧=下一首帧）。

**完成后**：`_进度.md` 勾选 `故事板定稿` / `字幕中` / `字幕英` ✅。下一步 /n2d-image。

## 平台提示词规范

见 `references/platforms.md`（各视频/图 AI 档案：提示词语言/画幅/Clip时长/角色一致性机制/运镜词/负面词，及"如何新增平台"）。默认即梦 AI。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 跳过建卡直接出镜头 | 必先建角色/场景卡，镜头里复用锚定句 |
| 视频 prompt 只写画面不写运动 | 必含人物运动 + 镜头运动 + 动态细节 |
| 设计超复杂打斗/人群 | 改为 AI 易生成的单人/双人动作、固定或简单运镜 |
| 平淡过渡、长旁白 | 每集保冲突/爽点/钩子/反转 |
| 角色跨集外貌漂移 | 严格复用同一张角色卡 |
| 输出散乱不入文件夹 | 所有素材写进 `第N集/` 对应文件 |
| 把出图 prompt 写进本 skill | 出图 prompt 是 `n2d-image` 的事，本 skill 只写 prompt 给那边作引用 |

## 详细案例与 Q&A

实战翻车 + 修正案例集中在 `novel2drama/Q&A.md`（调度器 skill 下，全阶段共用）。本 skill 涉及的相关问题：

- Q1：直接文生视频 vs 先出图再视频
- Q2：制作一集整体步骤
- Q13：文件归档约定
- Q18：图 AI vs 视频 AI 关系
- Q19：定妆图跨集复用 / 共享层架构
