---
name: novel-continue
description: Given an existing novel (.txt/.docx) — finished or in-progress — append NEW chapters that continue the story forward from the last chapter. Differs from novel-expand (which adds detail INSIDE existing chapters without changing the event skeleton) and from novel-spinoff (which rewrites the same story from a side character's POV). Supports two modes — 续编 (sequel after a complete ending) and 接更 (continue an unfinished novel). Defaults to public-domain / user-owned / user-licensed sources. Triggers 续写, 续写章节, 接着写, 写后续, 写续集, 接更, 补完结局, sequel, continue novel, append chapters.
---

# novel-continue — 续写新章节

给定**原作**（已完结 / 仍在连载 / 公版 / 自有 / 用户已声明授权）→ 从原作末章之后**续写新章节**。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`目标平台`、`权利来源`、`输出格式`。

## 和兄弟 skill 的区别（先看清楚再用）

| 你想做的事 | 用哪个 skill |
|---|---|
| 在原作之后**接着写新章节**（时间向前推） | **novel-continue 本 skill** |
| 在原作既有章节内**加细节**（时间不动） | `novel-expand` |
| 把原作**重新换个视角写**（POV 切换） | `novel-spinoff` |
| 把原作**压短** | `novel-condense` |

口诀：
- **续写 = 加后续章节**（新故事节点）
- **扩写 = 加章节内细节**（既有节点更厚）
- **视角续写 = 换 POV 写同一段时间**

## 合法性铁律

- 公版 / 自有 / `--i-have-rights` 才可处理。
- 当代受版权网文 / 出版物 → 拒做。
- 用户声明授权走 `--i-have-rights`，provenance 中记录。
- 续写章节里**不大段复刻原作原文**——必要的"回顾上一章"用一两句简短带过。

## 续写场景分两类

| 场景 | 触发 | 续写策略 |
|---|---|---|
| **续编** (sequel) | 原作已完结，在结局后继续 | 自由度大；新故事核心由 Claude 提议、用户拍板；要给原作结局接一个能延续的钩子 |
| **接更** (continuation) | 原作未完结（卡更 / 烂尾 / 太监），从末章继续 | 自由度小；尽量延续原作既定主线轨迹与作者口吻；尊重作者已埋伏笔 |

第 0 步必须问清楚哪种。

## 工作流（八步）

### 第 0 步 — 输入

- 原作路径
- **续写模式**：续编 / 接更
- **新章数**：建议 5–30
- 目标平台 / 风格
- 是否输出**合本**（原作 + 新章节合一）还是**仅新章节**

### 第 1 步 — 建项目

```bash
python3 <skill>/scripts/init_project.py "<原作>" \
  --mode sequel|continuation \
  --new-chapters 20 \
  [--target-platform <name>] \
  [--out <输出根>] \
  [--i-have-rights]
```

落点 `写小说/<原作名>-续写/`。骨架同其他 novel-* 派生 skill 模式（`设定/` / `章节/` / `导出/` / `_meta.json` / `_进度.md`）。

### 第 2 步 — 吸收原作（最长的一步）

读全本，输出：

- `设定/人物.md` —— 主要人物简卡，状态截止到**末章**
- `设定/世界观.md` —— 已确立规则
- `设定/主线骨架.json` —— 已发生的关键事件
- `设定/末章状态.md` —— 人物在哪 / 做什么 / **未回收的伏笔 / 悬念 / 钩子**（这是续写最珍贵的资产）
- `设定/作者口吻.md` —— 原作的句长 / 词汇密度 / 标志性短句 / 节奏特征（续写文风的锚定）

**未回收伏笔表**是续写章纲的输入；列得越完整，续写越像同一本书。

### 第 3 步 — 续写方向（最重要 gate）

Claude 基于第 2 步给用户 **2–3 个续写方向**，每个方向附：
- 主线一句话（要解决什么 / 走到哪）
- **用上的未回收伏笔列表**（必须覆盖 ≥ 50% 的伏笔）
- 风险点（会不会偏离原作设定 / 文风 / 既定走向）

用户选定一个方向。**不许凭空续编全新故事线——必须根植于原作伏笔**。

### 第 4 步 — 新章纲

**先按 `novel-craft/references/split.md` 反推总章数 / 字数分档**（按 target_platform；漫剧友好 ≠ 网文长篇）；然后引用 `novel-craft/references/outline.md` + `continue.md` 编织章纲。每章一行 outline，含：本章主要伏笔回收 / 新冲突 / 新角色（如有，不可主导主角线）/ 钩子。

### 第 5 步 — Demo（前 2–3 章）+ 用户审

引用 `novel-craft/references/chapter.md` + `continue.md`。

**续写 Demo 比扩写 / spinoff Demo 都敏感**——第一章直接决定读者是否相信"这是同一本书的下一章"。文风 / 口吻 / 人物状态必须严丝合缝。每章独立审，过了才进下一章。

### 第 6 步 — 续余下新章节

子代理 prompt 必须包含：
- 原作**末 1–2 章全文**（文风锚点）
- 设定卡（人物 / 世界观 / 末章状态 / 作者口吻）
- 新章纲全本
- 上一新章节末尾衔接（~500 字）
- 写作守则（chapter.md + continue.md）

### 第 7 步 — 一致性回扫

重点扫：
- 文风 / 口吻是否仍像原作（抽 3-5 章对比原作的章节）
- 人物状态是否从末章合理推进（不跳跃 / 不倒退）
- 未回收伏笔是否按章纲承诺回收
- 没有新设定推翻原作
- 没有大段复刻原作原文

### 第 8 步 — 导出

```bash
python3 <skill>/scripts/continue.py "<作品根>" [--combine]
```

- 默认：输出 `导出/<原作名>-续写.txt`（仅新章节）。
- `--combine`：输出 `导出/<原作名>-合本.txt`（原作末章后拼接新章节；仅在合法时——公版 / 自有 / --i-have-rights 均可）。

## 输出约定

- 默认作品根 `写小说/<原作名>-续写/`，`--out` 可改。
- 终态进 `导出/`；中间产物（章节 md / 设定卡 / 末章状态）保留作品根。

## 何时不用本 skill

- 想**换视角** → `novel-spinoff`
- 想**加章节内细节** → `novel-expand`
- 想**精简** → `novel-condense`
- 想写**完全脱离原作末章状态的新故事**（自己另开一本） → 不在本 skill 范围；直接由 Claude 协助原创

## 常见错误

| 错误 | 纠正 |
|---|---|
| 续编时凭空开新故事线 | 必须根植原作未回收伏笔 ≥ 50% |
| 接更时改了作者已埋的伏笔走向 | 接更要尊重作者既定轨迹；要改就用续编模式 |
| 文风漂移 | 子代理 prompt 必塞原作末 1-2 章作锚点 + 作者口吻卡 |
| 续写 Demo 没逐章审 | 续写比 spinoff 更敏感；Demo 必逐章独立审 |
| 大段复刻原作 | 仅可在续写章里**简短回顾**（一两句），不大段引 |
| 把新角色推到主角位 | 续写不是改写主角；原主角必须仍是主角 |
| 第 3 步用户没拍方向就开写章纲 | 方向是续写最大的 gate，未敲定不进第 4 步 |
| 跟 novel-expand 搞混 | 续写加新章 / 扩写加章节内细节，再看一遍区别表 |
