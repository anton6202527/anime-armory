---
name: novel-rewrite
description: Use when rewriting / reimagining / 魔改 an existing novel into a NEW version that CHANGES the main storyline and/or ADDS original settings, materials, powers, factions, characters — a transformative rewrite (翻拍 / 重构 / 二创魔改 / 换设定重写). NOT a side-character POV retelling locked to source events (that's novel-spinoff), NOT appending new chapters forward (novel-continue), NOT in-place detail thickening (novel-expand). Defaults to public-domain / user-owned / user-declared rights. Triggers 改写, 重写, 重构, 魔改, 二创重写, 翻拍, 换设定重写, 加新设定, 移植设定, 原作重做.
---

# novel-rewrite — 改写 / 重构 / 魔改

给定**原作** + **改动方向**，产出一部**改了主线 / 换了设定 / 加了原创材料**的新小说。和 `novel-spinoff` 是镜像关系：外传**锚点锁定**原作事件，改写**主动打破**它。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**，按 `../_偏好约定.md`（家族统一的偏好读写机制 + 全部选择点目录与缺省）解析：`<作品根>/_设置.md` → 全局默认 `创作偏好-默认.md` 预填并告知一句 → 缺则**首次问一次**→写回 `_设置.md`→**沉默沿用**（合规/不可逆/花钱点每次仍确认）。

本 skill 涉及的选择点：`目标平台`、`权利来源`、`输出格式`、`篇幅档`、`小说生成模式`、`章节生成粒度`、`AI使用披露`。

## 与近邻 skill 的边界（防误路由）

| 你想做的 | 用 |
|---|---|
| 换配角视角看同一批事件、**事件不改** | `novel-spinoff` |
| 在末章后**加新章节**（时间前推） | `novel-continue` |
| 章节内**加细节**、事件骨架不变 | `novel-expand` |
| **改主线 / 换设定 / 加原创材料 / 魔改走向** | **novel-rewrite（本 skill）** |

## 核心原则

- **先定"保留什么内核"，再谈改**：改写不是推倒重来胡写——`设定/改动spec.md` 是这部改写的"宪法"，写明【保留的内核】【改的部分】【加的新料】三栏。丢了内核（人设魂/情感主线）的改写 = 烂二创。
- **新设定圣经 = 第一生产资料**：你"增加的各种设定/材料/势力/金手指"统一进 `设定/新设定.md` 并做**一致性追踪**——改写最大的翻车点是新设定前后自相矛盾。
- **改写更要重写文字，不照搬原作**：既是工艺也是法律边界（派生作品）。原作是**参考素材**，不是可粘贴的底稿。
- **自由但自洽**：不受原作事件束缚，但新世界内部必须逻辑闭环。

## 合法性铁律
原作须 **公版 / 用户自有 / 用户声明授权（`--i-have-rights`）**。派生作品是原作版权人专有权利；当代受版权网文/出版物未声明授权 → 拒做。同 novel-spinoff，详见 `novel-author/SKILL.md` 合法性继承。

## 工作流（七步，每步末用户审 gate）

> **派生流水线**：阶段表 + demo_gate / draft_packets / 状态账本 / export / ai_usage 的通用机制见 `novel-craft/references/derive-pipeline.md`。本 skill 的 `source_model` = 原作内核/旧设定吸收，`direction_spec` = 改动spec / 新设定确认。

0. **确认输入 + 合法性**：原作路径、**改动方向**（一句话：要把它改成什么）、规模（short/medium/long/微短剧/漫剧）、目标平台、输出（txt/docx/outline/n2d）。判版权。
1. **建骨架**：`python3 <skill>/scripts/init_project.py "<原作>" --rewrite-type "<方向>" --scale <档> [--draft-mode 稳妥初稿] [--chapter-granularity 逐章] [--ai-text-usage AI-assisted] [--i-have-rights]` → `写小说/<原作名>-改写/`（设定/{改动spec,新设定,角色卡,世界观,章纲} + 原作.txt 参考 + 章节/ + 导出/ + _meta + _进度）。
2. **填改动spec**（最重要）：三栏【保留内核 / 改什么 / 加什么】写实写细。→ 用户审。
3. **建新设定圣经 + 角色/世界观卡**：把"加的新设定/材料"系统化、列一致性约束，**按家族统一 schema `novel-craft/references/setting-bible.md`**（新金手指也必写代价、新设定标"改自原作哪条"+首现章）。→ 用户审。
4. **书名**：委托 `novel-title`（同人改写/魔改类型）。→ 用户审。
5. **章纲**：自由编织（不受原作章节束缚，可大改顺序/结局），三幕 + 反转 + 钩子；用 `novel-craft/references/{outline,split}.md`。→ 用户审。
6. **Demo（前几章）+ 用户审【最重要 gate】**：验文风 / 改动方向是否到位 / 新设定是否自洽 / 没丢内核 / 没照搬原文。每章独立审。Demo 审完必须写 `审稿/demo_gate.json`（见 `novel-craft/references/demo-gate.md`），`status != passed` 不批量写。
7. **续写余下 + 回扫 + 导出**：先读 `novel-craft/references/draft-pipeline.md`，跑 `python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --next|--range A-B` 生成逐章任务包，再拆给子任务/子代理写（喂 改动spec + 新设定圣经 + `审稿/demo_gate.json` + Demo 文风样本 + 状态账本）；写完填 `审稿/state_delta_第NN章.json`。用 `novel-review` 回扫（重点：**新设定一致性**、没跑回原作旧设定、内核没丢、没照搬）；发布前用 `novel-craft/scripts/ai_usage.py` 留 AI 使用披露；`novel-craft/scripts/export.py`（家族通用导出器，默认执行 QA gate）导出 txt/docx/outline[/n2d]。

## 详细参考
- 改动spec 模板 + 新设定圣经管理 + 一致性追踪 + 与 spinoff 的边界细则：`references/rewrite-spec.md`
- 章纲/单章/扩缩工艺：`novel-craft/references/`
- 质检：`novel-review`

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把改写当外传，锚点锁死原作事件 | 改写本就要改；锁了就成了外传，路由错 |
| 没定"保留内核"就开改 | 先填改动spec 的【保留】栏，否则改飞、丢魂 |
| 新设定前后矛盾 / 越改越崩 | 新设定圣经 + 一致性回扫，新世界也要逻辑闭环 |
| 大段照搬原作原文当底稿 | 原作只是参考素材；改写必须重写，触法律边界 |
| 改到把原作的情感主线/人设魂也丢了 | 内核栏锁住魂；改的是事件/设定，不是魂 |
| 跳过 Demo gate 直接写全本 | 改动方向对不对、新设定自不自洽，1 章就能看出 |
| Demo 过审后不跑 `draft_packets.py` | 缺单章上下文包和状态账本，改写长篇容易跑回旧设定或越改越漂 |
| Demo 过审但没写 `审稿/demo_gate.json` | 后续批量写章缺机器文风锚点，容易越改越漂 |
| 误把"加新章节"当改写 | 那是 novel-continue |
