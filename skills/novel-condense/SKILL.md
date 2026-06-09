---
name: novel-condense
description: Given a long novel (.txt/.docx), compress it into a shorter version by cutting descriptions / minor subplots / repetitive interiority and merging adjacent chapters. Preserves main plot, anchor events, reversal points, hooks, and ending. Target uses include shorter readable version, AI 漫剧 storyboard-friendly cut, or chapter-grade outline. Defaults to public-domain / user-owned / user-licensed sources. Triggers 精简, 压缩小说, 砍章, 改成短版, 改成漫剧版, 提取大纲, condense novel, shorten novel.
---

# novel-condense — 精简一部小说

给定**原作长篇**（公版 / 自有 / 用户已声明授权）→ 输出一部**主线保留、细节大幅压缩**的精简版。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`权利来源`、`输出格式`、`小说生成模式`、`章节生成粒度`、`AI使用披露`。

## 合法性铁律

同 novel-spinoff / novel-expand。当代受版权网文 → 拒做。

## 用途分档

| 目标用途 | 压缩比 | 输出形态 |
|---|---|---|
| 短读版 | 1.5–3× | txt+docx，章节结构基本保留 |
| 漫剧友好版 | 5–10× | txt+docx + n2d-script 友好目录，按戏剧节拍重切 |
| 大纲级 | 20×+ | outline.md 为主，不再是小说 |

## 工作流（七步）

> **派生同构阶段表**：本 skill 的 `_meta.json` / `_进度.md` 必须遵守 `novel-craft/references/contract.md`。机器阶段 key 固定为 `setup → source_model → direction_spec → title → outline → demo → draft → review → export`；本 skill 中 `source_model` = 主线骨架/锚点/反转点，`direction_spec` = 压缩比/目标用途/合章策略。

### 第 0 步 — 输入

- 原作路径
- **目标压缩比** 或 目标字数
- **目标用途**（短读版 / 漫剧版 / 大纲）
- 输出形式

### 第 1 步 — 建项目

```bash
python3 <skill>/scripts/init_project.py "<原作>" \
  --ratio 5 \
  --target 漫剧 \
  [--target-chapters 60] \
  [--draft-mode 漫剧源书] [--chapter-granularity 逐章] [--ai-text-usage AI-assisted] \
  [--out <输出根>] \
  [--i-have-rights]
```

`init_project.py` 会根据 `target_chars_estimate + target/outputs` 推导 `target_chapters / target_words_per_chapter / demo_chapters / draft_mode`，并把 `draft_mode / chapter_granularity / ai_text_usage` 同步写进 `_meta.json` 与 `_设置.md`；若漫剧版已有明确集/章规划，必须传 `--target-chapters`，保证后续 `draft_packets.py --next` 按机器字段推进。

### 第 2 步 — 标主线 / 锚点 / 反转点

读原作，输出 `设定/主线骨架.json` —— 标记不可砍的"硬骨头"：
- 主角关键决定
- 所有锚点事件
- 反转点
- 章末钩子
- 关键人物首次出场
- 大高潮的情绪段

### 第 3 步 — 划章 / 合章

按 `_meta.json.target_chapters` 与目标压缩比决定新章数。相邻同主题章合并；纯支线章砍掉或缩成一句话。映射写入 `设定/章节映射.md`。

### 第 4 步 — 章纲

**先按 `novel-craft/references/split.md` 反推精简后总章数 / 字数分档**（短读版 1.5-3× 压缩 / 漫剧友好版 5-10× / 大纲级 20×+，对应章数差极大）；然后引用 `novel-craft/references/outline.md` + `condense.md` 编织章纲。注意：漫剧友好版的章 = 戏剧节拍 ≠ 原作章节。

### 第 5 步 — Demo（前 2-3 章）+ 用户审

引用 `novel-craft/references/chapter.md` + `condense.md`。每章独立写、独立审。
Demo 审完必须写 `审稿/demo_gate.json`（见 `novel-craft/references/demo-gate.md`）；`status != passed` 不进第 6 步。

### 第 6 步 — 续 + 回扫

先读 `novel-craft/references/draft-pipeline.md`，跑 `python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --next|--range A-B` 生成逐章任务包。
续压子任务必须喂 `审稿/demo_gate.json` 的 `style_anchor` / `reader_promises` / `setting_constraints`，并读取 `审稿/state_ledger.json`。
每章写完填 `审稿/state_delta_第NN章.json`，记录主线骨架、钩子、反转点是否保留。
重点扫：
- 主线骨架是否完整
- 钩子是否还在
- 反转点是否保留
- 节奏是否仍连贯
- 没有大段原文照搬

### 第 7 步 — 导出

发布/交平台前先用 `novel-craft/scripts/ai_usage.py` 写 AI 使用披露。

```bash
python3 novel-craft/scripts/export.py "<作品根>" --formats txt,docx[,n2d,outline]   # 家族通用导出器（漫剧友好版传 n2d 喂 n2d-script）
```

## 输出约定

- 默认落 `写小说/<原作名>-精简/`。
- 终态进 `导出/`，中间产物留作品根。

## 何时不用本 skill

- 用户想**扩写** → 用 novel-expand。
- 用户想**配角视角续写** → 用 novel-spinoff。
- 用户想**做漫剧脚本但不要精简版小说** → 直接 novel2drama / n2d-script，更直接。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 砍了反转点 | 反转点是钩子来源，必须保 |
| 每章压成一段 | 那是大纲不是小说；按目标用途分档 |
| 漫剧版仍按原章节切 | 漫剧要按戏剧节拍切，跨章合理 |
| 大段复刻原作高潮段 | 即便高潮段也要重写，不搬文本 |
| 均匀压缩每段砍 50% | 高潮段失去击穿；要重点保高潮 |
| Demo 没审就续 | 第 5 步 gate 必须等用户点头 |
| Demo 过审后不跑 `draft_packets.py` | 缺单章上下文包和状态账本，容易砍丢主线或钩子 |
| Demo 过审但没写 `审稿/demo_gate.json` | 后续压缩缺保留风格/承诺的机器锚点 |
