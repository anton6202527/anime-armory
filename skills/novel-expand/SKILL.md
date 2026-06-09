---
name: novel-expand
description: Given a short story or compact novel (.txt/.docx), expand it into a longer work by adding environment / internal monologue / detailed dialogue / minor side-scenes — while keeping the original event skeleton, character arcs, and ending intact. Defaults to public-domain / user-owned / user-licensed sources and refuses copyrighted contemporary web novels without an explicit rights declaration. Triggers 扩写, 扩写小说, 丰富细节, 改写成长篇, 把短篇拉长, expand novel, lengthen novel.
---

# novel-expand — 扩写一部小说

给定**原作**（公版 / 自有 / 用户已声明授权）→ 输出一部**事件骨架不变、细节大幅丰富**的扩写版。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`目标平台`、`权利来源`、`输出格式`、`小说生成模式`、`章节生成粒度`、`AI使用披露`。

## ⚠️ 区别 novel-continue（最容易混的兄弟 skill）

| 你想做的事 | 用哪个 |
|---|---|
| 已有 10 章，要**在第 1-10 章内加内心戏 / 环境 / 对话细节**（时间不动，章节字数变厚） | **novel-expand 本 skill** |
| 已有 10 章，要**在第 11 章之后继续写新故事**（时间向前推） | `novel-continue` |
| 已有 10 章，要**换个配角视角重写 1-10 章** | `novel-spinoff` |

口诀：**扩写时间不动 / 续写时间向前 / 视角续写换 POV**。

## 合法性铁律（同 novel-spinoff）

- 公版 / 自有 / `--i-have-rights` 才可处理。
- 当代受版权网文 / 出版物 → 拒做。
- 用户声明授权走 `--i-have-rights`，provenance 中记录。
- **扩写中不大段复刻原作原文** —— 保骨架时用事件骨架描述，不搬文本。

## 工作流（七步）

> **派生同构阶段表**：本 skill 的 `_meta.json` / `_进度.md` 必须遵守 `novel-craft/references/contract.md`。机器阶段 key 固定为 `setup → source_model → direction_spec → title → outline → demo → draft → review → export`；本 skill 中 `source_model` = 事件骨架/人物/世界观，`direction_spec` = 扩写比例/章节映射。

### 第 0 步 — 输入

- 原作路径（.txt / .docx）
- **扩写比例**（2× / 5× / 10× / 或目标总字数）
- 目标平台（影响章长 / 节奏 / 加什么内容）
- 输出形式（txt+docx / outline.md / n2d-friendly）

### 第 1 步 — 建项目

```bash
python3 <skill>/scripts/init_project.py "<原作>" \
  --ratio 5 \
  --target-platform 抖音漫剧 \
  [--target-chapters 90] \
  [--draft-mode 稳妥初稿] [--chapter-granularity 逐章] [--ai-text-usage AI-assisted] \
  [--out <输出根>] \
  [--i-have-rights]
```

落点 `写小说/<原作名>-扩写/`。骨架同 novel-spinoff 模式（`设定/` / `章节/` / `导出/` / `_meta.json` / `_进度.md`）。
`init_project.py` 会根据 `target_chars_estimate + target_platform` 推导 `target_chapters / target_words_per_chapter / demo_chapters`，并把 `draft_mode / chapter_granularity / ai_text_usage` 同步写进 `_meta.json` 与 `_设置.md`；若用户已明确总章数，必须传 `--target-chapters`，不要只写在人类说明里。

### 第 2 步 — 提取骨架

读原作，输出 `设定/事件骨架.json` —— 每段对应一个事件 / 一段对话 / 一段心理。同时提取 `设定/人物.md`（主要人物简卡）和 `设定/世界观.md`。

### 第 3 步 — 划章

确定扩写后章节数（按 `_meta.json.target_chapters` / 目标字数 / 平台节奏）。每章映射到原作的若干骨架点，写入 `设定/章节映射.md`。

### 第 4 步 — 章纲

**先按 `novel-craft/references/split.md` 反推扩写后总章数 / 字数分档**（按 target_platform；漫剧友好 vs 网文长篇 章数差一个量级）；然后引用 `novel-craft/references/outline.md` + `expand.md` 编织章纲。每章一行 outline，标注本章主要加什么类型的细节（环境 / 内心 / 对话 / 次要互动 / 支线）。

### 第 5 步 — Demo（前 2-3 章）+ 用户审

引用 `novel-craft/references/chapter.md` + `expand.md`。逐章独立写，**每章审过才进下一章**。
Demo 审完必须写 `审稿/demo_gate.json`（见 `novel-craft/references/demo-gate.md`）；`status != passed` 不进第 6 步。

### 第 6 步 — 续扩 + 回扫

先读 `novel-craft/references/draft-pipeline.md`，跑 `python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --next|--range A-B` 生成逐章任务包。
续扩子任务必须喂 `审稿/demo_gate.json` 的 `style_anchor` / `reader_promises` / `setting_constraints`，并读取 `审稿/state_ledger.json`。
每章写完填 `审稿/state_delta_第NN章.json`，只记录细节加厚带来的关系/伏笔状态，不新增会改主线的新规则。
每写一组 5 章跑轻量回扫；全本写完跑全量。重点扫：
- 事件骨架是否对齐
- 结局是否未变
- 设定是否未推翻
- 没有新主要人物 / 新主线事件被加入

### 第 7 步 — 导出

发布/交平台前先用 `novel-craft/scripts/ai_usage.py` 写 AI 使用披露。

```bash
python3 novel-craft/scripts/export.py "<作品根>" --formats txt,docx[,outline,n2d]   # 家族通用导出器
```

## 输出约定

- 默认落 `写小说/<原作名>-扩写/`。
- 终态进 `导出/`，中间产物留作品根。

## 何时不用本 skill

- 用户想**改写主线 / 改结局** → 不在范围；那是改写，本 skill 不做。
- 用户想**配角视角续写** → 用 novel-spinoff。
- 用户想**压缩** → 用 novel-condense。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 扩写时改了结局 | 绝对禁止——扩写不是改写 |
| 加新主要人物 | 不加；只能加路人 / 随从级 |
| 加新设定 / 新规则 | 不加；只用原作已有 |
| 大段复刻原作 | 用事件骨架对齐，不搬文本 |
| 加支线把节奏打散 | 支线密度 ≤ 1 段 / 章；超过先精简 |
| 一次性扩完不让用户审 | 第 5 步 Demo gate 必须等用户点头 |
| Demo 过审后不跑 `draft_packets.py` | 缺单章上下文包和状态账本，容易注水漂移 |
| Demo 过审但没写 `审稿/demo_gate.json` | 后续扩写缺风格和承诺锚点，容易注水漂移 |
