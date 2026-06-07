---
name: novel-craft
description: Shared writing-primitives library for the novel-* skill family — generic guides for outline crafting, single-chapter writing discipline, in-place expansion, and condensation. Other novel-* skills reference these by file path; users can also invoke directly for a one-shot writing-craft question. Triggers 怎么写章纲, 怎么写单章, 子代理 prompt 怎么写, 写作工艺, novel writing primitives, 章纲编织, 单章守则, 扩写法, 精简法.
---

# novel-craft — 通用小说写作 primitives

不强制流程。一组"怎么写"的工艺参考。其他 novel-* skills 引用本 references；用户也可以直接调它问某一节工艺。

## 包含的 primitives

| 主题 | 参考 | 何时引用 |
|---|---|---|
| **设定圣经 schema（统一·单一真值源）** | `references/setting-bible.md` | 建设定/角色卡/世界观时——create 从零建、spinoff/rewrite/continue 从原作抽改，**都用这一套字段**（含金手指必有代价 + 首现章/复用范围一致性三列） |
| 拆分标准（章 / 集 边界 + 字数分档） | `references/split.md` | 章纲编织**之前**先定总章数与字数分档 |
| 章纲编织 | `references/outline.md` | 拆分定下后；进入逐章写作前 |
| 单章写作守则 | `references/chapter.md` | 每章下笔前；子代理 prompt 模板在此 |
| 扩写法 | `references/expand.md` | 现有文本太短，想**加章节内细节**（时间不动） |
| 续写法 | `references/continue.md` | 原作末章后，**加新章节**（时间向前推） |
| 精简法 | `references/condense.md` | 现有文本太长想压缩时 |

## 共享脚本（家族通用工具，避免各 skill 各写一份）

| 脚本 | 干什么 | 谁用 |
|---|---|---|
| `scripts/export.py` | 章节/第NN章.md 合并 → txt / docx / 大纲 / n2d-script 目录；`--combine` 走续写合本（原作+新章节·章号续编） | create / spinoff / rewrite / expand / condense / continue **共用同一份**（旧的 expand.py/condense.py/continue.py/spinoff·export.py 已删除合并到此） |

```bash
python3 novel-craft/scripts/export.py "<作品根>" --formats txt,docx,outline[,n2d] [--combine] [--title "<书名>"]
```

- `--formats` 缺省读 `_meta.json.outputs`；书名缺省按 `_meta.json` 的 `kind` 推导（spinoff=「原作-配角外传」、expand=「原作-扩写」、condense=「原作-精简」、continue=「原作-续写」、rewrite=「原作-改写」、create=`title`）。
- 含 `n2d` 时在 `导出/n2d-script/小说/<书名>.docx` 铺好 n2d-script 入口，直接喂 `novel2drama`。
- 依赖：`python-docx`（仅 docx/n2d 格式时）。

## 用法

- **作为被引用方**：其他 skill 的 SKILL.md 通过文件路径引用本 references / scripts。例：novel-spinoff 第 4 步章纲 → 引 `outline.md`；novel-expand 第 5 步 Demo → 引 `chapter.md` + `expand.md`；各派生 skill 第 7/8 步导出 → 调 `scripts/export.py`。
- **作为被直接调用**：用户问"章纲怎么搭""子代理 prompt 怎么写"等通用问题时，把对应 references 摘要回给用户。

## 何时不用本 skill

- 用户在跑完整的 spinoff / expand / condense 流水线 → 走那条 skill 的主流程；本 skill 内容会被那条流水线引用过去。
- 用户在写完全原创小说没有锚点约束 → 本 skill 的 chapter.md / outline.md 仍可用。

## 设计原则

- **不入侵流程**：本 skill 不规定"先做 X 再做 Y"；只给"X 怎么做、Y 怎么做"。
- **可独立摘录**：每个 references 文件都是自包含的，引用方可以只摘其中一节。
- **不重复 novel-* 主流程**：流程性内容在调用方的 SKILL.md / workflow.md 里，本库只放"工艺细节"。
