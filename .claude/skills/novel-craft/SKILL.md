---
name: novel-craft
description: Shared writing-primitives library for the novel-* skill family — generic guides for outline crafting, single-chapter writing discipline, in-place expansion, and condensation. Other novel-* skills reference these by file path; users can also invoke directly for a one-shot writing-craft question. Triggers 怎么写章纲, 怎么写单章, 子代理 prompt 怎么写, 写作工艺, novel writing primitives, 章纲编织, 单章守则, 扩写法, 精简法.
---

# novel-craft — 通用小说写作 primitives

不强制流程。一组"怎么写"的工艺参考。其他 novel-* skills 引用本 references；用户也可以直接调它问某一节工艺。

## 包含的 primitives

| 主题 | 参考 | 何时引用 |
|---|---|---|
| 章纲编织 | `references/outline.md` | 进入逐章写作前 |
| 单章写作守则 | `references/chapter.md` | 每章下笔前；子代理 prompt 模板在此 |
| 扩写法 | `references/expand.md` | 现有文本太短，想**加章节内细节**（时间不动） |
| 续写法 | `references/continue.md` | 原作末章后，**加新章节**（时间向前推） |
| 精简法 | `references/condense.md` | 现有文本太长想压缩时 |

## 用法

- **作为被引用方**：其他 skill 的 SKILL.md 通过文件路径引用本 references。例：novel-spinoff 第 4 步章纲 → 引 `outline.md`；novel-expand 第 5 步 Demo → 引 `chapter.md` + `expand.md`。
- **作为被直接调用**：用户问"章纲怎么搭""子代理 prompt 怎么写"等通用问题时，把对应 references 摘要回给用户。

## 何时不用本 skill

- 用户在跑完整的 spinoff / expand / condense 流水线 → 走那条 skill 的主流程；本 skill 内容会被那条流水线引用过去。
- 用户在写完全原创小说没有锚点约束 → 本 skill 的 chapter.md / outline.md 仍可用。

## 设计原则

- **不入侵流程**：本 skill 不规定"先做 X 再做 Y"；只给"X 怎么做、Y 怎么做"。
- **可独立摘录**：每个 references 文件都是自包含的，引用方可以只摘其中一节。
- **不重复 novel-* 主流程**：流程性内容在调用方的 SKILL.md / workflow.md 里，本库只放"工艺细节"。
