---
name: novel-craft
description: Shared writing-primitives and deterministic production helpers for the novel-* skill family — generic guides for outline crafting, single-chapter writing discipline, batch draft packet orchestration, state ledger updates, in-place expansion, condensation, export, progress, QA gate, and AI usage disclosure. Other novel-* skills reference these by file path; users can also invoke directly for a one-shot writing-craft or drafting workflow question. Triggers 怎么写章纲, 怎么写单章, 子代理 prompt 怎么写, 批量写章, 写作任务包, draft packets, 状态账本, AI使用披露, 写作工艺, novel writing primitives, 章纲编织, 单章守则, 扩写法, 精简法.
---

# novel-craft — 通用小说写作 primitives

不强制流程。一组"怎么写"的工艺参考。其他 novel-* skills 引用本 references；用户也可以直接调它问某一节工艺。

## 包含的 primitives

| 主题 | 参考 | 何时引用 |
|---|---|---|
| **机器契约（_meta/_进度/schema/分档/原创/派生阶段表）** | `references/contract.md` + `scripts/contract.py` | 任何脚本、init、导出、进度续跑要读写共享字段时；这是 novel 系列的机器单一真值源 |
| **QA 报告 schema** | `references/qa-report-schema.md` | `novel-review` / `novel-score` 产出 JSON 报告、上层要按报告回流阶段时 |
| **Demo gate 留痕 schema** | `references/demo-gate.md` | Demo 章过审后；批量写章、review 查文风漂移、score 复盘前都要读 |
| **设定圣经 schema（统一·单一真值源）** | `references/setting-bible.md` | 建设定/角色卡/世界观时——create 从零建、spinoff/rewrite/continue 从原作抽改，**都用这一套字段**（含金手指必有代价 + 首现章/复用范围一致性三列） |
| **批量写章闭环** | `references/draft-pipeline.md` | Demo 过审后进入 draft；需要任务包、状态增量、章节生成粒度、写章回扫时 |
| 拆分标准（章 / 集 边界 + 字数分档） | `references/split.md` | 章纲编织**之前**先定总章数与字数分档 |
| 章纲编织 | `references/outline.md` | 拆分定下后；进入逐章写作前 |
| 单章写作守则 | `references/chapter.md` | 每章下笔前；子代理 prompt 模板在此 |
| 扩写法 | `references/expand.md` | 现有文本太短，想**加章节内细节**（时间不动） |
| 续写法 | `references/continue.md` | 原作末章后，**加新章节**（时间向前推） |
| 精简法 | `references/condense.md` | 现有文本太长想压缩时 |

## 共享脚本（家族通用工具，避免各 skill 各写一份）

| 脚本 | 干什么 | 谁用 |
|---|---|---|
| `scripts/contract.py` | 机器单一真值源：scale 分档、输出格式、kind/title 规则、原创/派生阶段表、进度 schema marker | 全部 novel-* 脚本和测试 |
| `scripts/waivers.py` | 统一生成 / 读取 `审稿/waiver_log.jsonl`，所有 gate 绕过都要留同构痕迹 | export / draft_packets / score / report_gate |
| `scripts/report_snapshot.py` | 给 review/score 报告记录正文文件 hash 与 aggregate hash；QA gate 用它判断报告是否仍绑定当前正文 | novel-review / novel-score / qa_gate |
| `scripts/qa_gate.py` / `scripts/report_gate.py` | 读取 `审稿/review_report.json` + `评分/score_report.json` + `审稿/waiver_log.jsonl`；缺 review、报告 schema 不合规、报告 hash 过期、阻断 finding、阻断 score verdict、baseline freshness 阻断都会进入 gate；`--waive-missing-score` 只豁免带作用域的缺评分 | progress / export / novel-author 续跑 |
| `scripts/export.py` | 章节/第NN章.md 合并 → txt / docx / 大纲 / n2d-script 目录；默认执行 export QA gate，缺 review 或阻断未清不能导出；`--ignore-qa-gate` 会写带章节 hash / blocker ids / formats 的 waiver log；`--combine` 走续写合本 | create / spinoff / rewrite / expand / condense / continue **共用同一份** |
| `scripts/progress.py` | 只读扫描 `<作品根>/_进度.md`，输出第一条未完成项 + stage owner/gate/on_fail + QA 阻断 | 所有会写 `_进度.md` 的 novel-* 项目 |
| `scripts/draft_packets.py` | 生成 `写作任务/第NN章.md` + 初始化 `审稿/state_ledger.json`；默认要求 Demo gate passed；不调用 AI | 所有 `draft` 阶段，先包上下文再写章 |
| `scripts/reconcile_ledger.py` | 输出正文/Delta 核对 prompt；仅在提供已通过核对的 `--verified` JSON 后合并入 `state_ledger.json` | 所有 `draft` 阶段，写章后同步状态 |
| `scripts/ai_usage.py` | 写 `合规/ai_usage.json` + `合规/AI使用说明.md`，记录 AI-generated / AI-assisted / 未使用 AI 文本 | 发布、导出、交平台前 |

## 工业化生产线（批量写章闭环）

1.  **准备阶段**：`python3 scripts/draft_packets.py <作品根> --next`。生成 `写作任务/第NN章.md`，内含本章章纲、前文摘要、风格锚点及**当前状态账本（State Ledger）**快照。
2.  **写章阶段**：按任务包要求完成 `章节/第NN章.md`，并根据内容填写 `审稿/state_delta_第NN章.json`（记录本章引入的新事实、人设变动、新线索）。
3.  **对账与同步**：
    -   **Audit**：`python3 scripts/reconcile_ledger.py <作品根> --chapter NN --audit`，用输出 prompt 核对正文与 Delta 是否一致，防止「记了没写」或「写了没记」。
    -   **Merge**：把核对结论保存成 `审稿/state_verify_第NN章.json`（必须含 `chapter: NN`、`status: ok`、`chapter_file_hash`、`delta_hash`；hash 由 audit prompt 给出），再跑 `python3 scripts/reconcile_ledger.py <作品根> --chapter NN --merge --verified 审稿/state_verify_第NN章.json`。未经验证不合并，泛化 `{"status":"ok"}` 不合并；正文或 delta 改动导致 hash 不匹配时必须重新 audit。
4.  **质检阶段**：`python3 ../novel-review/scripts/mechanical_check.py <作品根>` 检查硬伤。
5.  **循环**：直至完成所有 Demo 章或目标章节。

```bash
python3 novel-craft/scripts/export.py "<作品根>" --formats txt,docx,outline[,n2d] [--combine] [--title "<书名>"]
```

- `--formats` 缺省读 `_meta.json.outputs`；书名缺省按 `_meta.json` 的 `kind` 推导（spinoff=「原作-配角外传」、expand=「原作-扩写」、condense=「原作-精简」、continue=「原作-续写」、rewrite=「原作-改写」、create=`title`）。
- 导出前默认要求 `审稿/review_report.json` 存在，并读取 `评分/score_report.json`；报告必须符合 `qa-report-schema.md` 且带 `source_snapshot` 绑定当前 `章节/` 正文 hash，正文新增、删除或改动后旧报告会阻断。商业连载/漫剧源书或目标平台含红果/番茄/抖音/漫剧时，缺 score 也阻断；其他项目缺 score 显示 warning。确需跳过评分，用 `report_gate.py --waive-missing-score --reason "<原因>"` 写带章节 hash 的豁免；只有用户明确要求强制导出时才加 `--ignore-qa-gate`，并自动写带作用域的 `审稿/waiver_log.jsonl`。
- 若未传 `--formats` 且 `_meta.json.outputs` 缺失 / 为空，导出器会直接报错，不再“成功但无产物”。
- 含 `n2d` 时在 `导出/n2d-script/小说/<书名>.docx` 铺好 n2d-script 入口，直接喂 `novel2drama`。
- 依赖：`python-docx`（仅 docx/n2d 格式时）。

```bash
python3 novel-craft/scripts/progress.py "<作品根>"
```

```bash
python3 novel-craft/scripts/report_gate.py "<作品根>"          # export 硬闸
python3 novel-craft/scripts/report_gate.py "<作品根>" --progress-mode  # 续跑提示，缺 review 仅 warning
python3 novel-craft/scripts/report_gate.py "<作品根>" --progress-mode --waive-missing-score --reason "<原因>"
```

```bash
python3 novel-craft/scripts/draft_packets.py "<作品根>" --chapter 4
python3 novel-craft/scripts/draft_packets.py "<作品根>" --range 4-8
python3 novel-craft/scripts/draft_packets.py "<作品根>" --next
```

```bash
python3 novel-craft/scripts/ai_usage.py "<作品根>" --text-mode AI-generated --publish-target KDP
```

## 用法

- **作为被引用方**：其他 skill 的 SKILL.md 通过文件路径引用本 references / scripts。例：novel-spinoff 第 4 步章纲 → 引 `outline.md`；novel-expand 第 5 步 Demo → 引 `chapter.md` + `expand.md`；各派生 skill draft → 先调 `scripts/draft_packets.py`；各派生 skill 第 7/8 步导出 → 调 `scripts/export.py`。
- **作为被直接调用**：用户问"章纲怎么搭""子代理 prompt 怎么写"等通用问题时，把对应 references 摘要回给用户。

## 何时不用本 skill

- 用户在跑完整的 spinoff / expand / condense 流水线 → 走那条 skill 的主流程；本 skill 内容会被那条流水线引用过去。
- 用户在写完全原创小说没有锚点约束 → 本 skill 的 chapter.md / outline.md 仍可用。

## 设计原则

- **不抢写作权**：`draft_packets.py` 只生成任务包和状态模板，不直接生成正文；正文仍由当前 novel skill / agent 按项目目标写。
- **可独立摘录**：每个 references 文件都是自包含的，引用方可以只摘其中一节。
- **不重复 novel-* 主流程**：流程性内容在调用方的 SKILL.md / workflow.md 里，本库只放"工艺细节"。
