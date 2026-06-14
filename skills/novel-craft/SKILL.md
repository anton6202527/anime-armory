---
name: novel-craft
description: Shared writing-primitives and deterministic production helpers for the novel-* skill family — generic guides for outline crafting, single-chapter writing discipline, batch draft packet orchestration, state ledger updates, in-place expansion, condensation, export, progress, QA gate, and AI usage disclosure. Other novel-* skills reference these by file path; users can also invoke directly for a one-shot writing-craft or drafting workflow question. Triggers 怎么写章纲, 怎么写单章, 子代理 prompt 怎么写, 批量写章, 写作任务包, draft packets, 状态账本, AI使用披露, 写作工艺, novel writing primitives, 章纲编织, 单章守则, 扩写法, 精简法.
---

# novel-craft — 通用小说写作 primitives

不强制流程。一组"怎么写"的工艺参考。其他 novel-* skills 引用本 references；用户也可以直接调它问某一节工艺。

## 包含的 primitives

| 主题 | 参考 | 何时引用 |
|---|---|---|
| **机器契约（_meta/_进度/schema/分档/原创/派生阶段表/skill roster）** | `references/contract.md` + `scripts/contract.py` + `scripts/registry.py` | 任何脚本、init、导出、进度续跑、路由表同步要读写共享字段时；这是 novel 系列的机器单一真值源 |
| **QA 报告 schema** | `references/qa-report-schema.md` | `novel-review` / `novel-score` 产出 JSON 报告、上层要按报告回流阶段时 |
| **Demo gate 留痕 schema** | `references/demo-gate.md` | Demo 章过审后；批量写章、review 查文风漂移、score 复盘前都要读 |
| **读者契约 / 题旨契约** | `references/reader-contract.md` | 蓝图/spec/章纲通过后固化 `设定/读者契约.md`；Demo gate 同步 `reader_contract`；每章任务包用它防止偏题、承诺遗忘和文学质感变薄 |
| **设定圣经 schema（统一·单一真值源）** | `references/setting-bible.md` | 建设定/角色卡/世界观时——create 从零建、spinoff/rewrite/continue 从原作抽改，**都用这一套字段**（含金手指必有代价 + 首现章/复用范围一致性三列） |
| **批量写章闭环** | `references/draft-pipeline.md` | Demo 过审后进入 draft；需要任务包、状态增量、章节生成粒度、写章回扫时 |
| **三段式精品写章** | `references/trio-pipeline.md` | `商业连载` / `漫剧源书` / `小说生成工作流=三步迭代`；每章拆成 Architect → Ghostwriter → Senior Editor 三个任务包 |
| **派生流水线后半段（rewrite/continue/expand/condense/spinoff 共用）** | `references/derive-pipeline.md` | 任一派生 skill 的阶段表 / demo_gate / draft / export / ai_usage 通用机制——各 skill 只写自己的 source_model/direction_spec 映射，通用部分引此 |
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
| `scripts/registry.py` | novel-* 家族机器 roster；测试会校验它与磁盘目录、`novel` 路由表、`skills/README.md` 一致 | novel / README / self_audit |
| `scripts/store.py` | 跨脚本加锁与原子写：`file_lock`、`atomic_write_text/json` | progress / draft_queue / draft_packets / reconcile_ledger |
| `scripts/waivers.py` | 统一生成 / 读取 `审稿/waiver_log.jsonl`，所有 gate 绕过都要留同构痕迹 | export / draft_packets / score / report_gate |
| `scripts/report_snapshot.py` | 给 review/score 报告记录正文文件 hash 与 aggregate hash；QA gate 用它判断报告是否仍绑定当前正文 | novel-review / novel-score / qa_gate |
| `scripts/qa_gate.py` / `scripts/report_gate.py` | 读取 `审稿/review_report.json` + `评分/score_report.json` + `审稿/waiver_log.jsonl`；缺 review、报告 schema 不合规、报告 hash 过期、阻断 finding、阻断 score verdict、baseline freshness 阻断都会进入 gate；`--waive-missing-score` 只豁免带作用域的缺评分 | progress / export / novel 续跑 |
| `scripts/export.py` | 章节/第NN章.md 合并 → txt / docx / 大纲 / n2d-script 目录；默认执行 export QA gate，缺 review 或阻断未清不能导出；`--ignore-qa-gate` 会写带章节 hash / blocker ids / formats 的 waiver log；`--combine` 走续写合本 | create / spinoff / rewrite / expand / condense / continue **共用同一份** |
| `scripts/progress.py` | 扫描 `<作品根>/_进度.md`，输出第一条未完成项 + stage owner/gate/on_fail + QA 阻断；`set <stage> done|todo` 通过 `_进度.lock` 加锁原子更新机器阶段 | 所有会写 `_进度.md` 的 novel-* 项目 |
| `scripts/draft_queue.py` | 批量写章队列：初始化待写章节、claim 租约认领、done/fail/todo 标记，避免小批/多代理重复写同一章 | `draft` 阶段，尤其小批/全书草稿 |
| `scripts/draft_packets.py` | 生成 `写作任务/第NN章.md` 或三段式 `第NN章_{architect,ghostwriter,editor}.md` + 初始化 `审稿/state_ledger.json`；默认要求 Demo gate passed；不调用 AI | 所有 `draft` 阶段，先包上下文再写章；商业连载/漫剧源书默认三段式 |
| `scripts/reconcile_ledger.py` | 输出正文/Delta 核对 prompt；仅在提供已通过核对的 `--verified` JSON 后合并入 `state_ledger.json` | 所有 `draft` 阶段，写章后同步状态 |
| `scripts/ai_usage.py` | 写 `合规/ai_usage.json` + `合规/AI使用说明.md`，记录 AI-generated / AI-assisted / 未使用 AI 文本 | 发布、导出、交平台前 |

## 工业化生产线（批量写章闭环）

1.  **准备阶段**：先用 `python3 skills/novel-craft/scripts/draft_queue.py <作品根> init` 建队列；小批/多代理写章时用 `claim --agent <名字>` 认领章节，再跑 `python3 skills/novel-craft/scripts/draft_packets.py <作品根> --chapter NN`。任务包内含本章章纲、前文摘要、风格锚点及**当前状态账本（State Ledger）**快照。`商业连载` / `漫剧源书` 或 `_设置.md` 写 `小说生成工作流：三步迭代` 时，默认生成 `_architect`、`_ghostwriter`、`_editor` 三份任务包；显式 `--step full` 可降回单包，显式 `--step trio` 可强制三包。
2.  **写章阶段**：普通项目按 `第NN章.md` 完成 `章节/第NN章.md`；三段式按 `_architect` 产 beats、`_ghostwriter` 产 draft、`_editor` 写最终正文。然后根据内容填写 `审稿/state_delta_第NN章.json`（记录本章引入的新事实、人设变动、新线索）。
3.  **对账与同步**：
    -   **Audit**：`python3 skills/novel-craft/scripts/reconcile_ledger.py <作品根> --chapter NN --audit`，用输出 prompt 核对正文与 Delta 是否一致，防止「记了没写」或「写了没记」。
    -   **Merge**：把核对结论保存成 `审稿/state_verify_第NN章.json`（必须含 `chapter: NN`、`status: ok`、`chapter_file_hash`、`delta_hash`；hash 由 audit prompt 给出），再跑 `python3 skills/novel-craft/scripts/reconcile_ledger.py <作品根> --chapter NN --merge --verified 审稿/state_verify_第NN章.json`。未经验证不合并，泛化 `{"status":"ok"}` 不合并；正文或 delta 改动导致 hash 不匹配时必须重新 audit。
4.  **质检阶段**：`python3 skills/novel-review/scripts/mechanical_check.py <作品根>` 检查硬伤。
5.  **循环**：章节通过回扫后用 `draft_queue.py <作品根> done NN --agent <名字>` 标记完成；若返工则 `fail NN --reason "<原因>"` 或 `todo NN` 放回队列，直至完成所有 Demo 章或目标章节。

```bash
python3 skills/novel-craft/scripts/export.py "<作品根>" --formats txt,docx,outline[,n2d] [--combine] [--title "<书名>"] [--n2d-dest 制漫剧/<剧名>]
```

- `--formats` 缺省读 `_meta.json.outputs`；书名缺省按 `_meta.json` 的 `kind` 推导（spinoff=「原作-配角外传」、expand=「原作-扩写」、condense=「原作-精简」、continue=「原作-续写」、rewrite=「原作-改写」、create=`title`）。
- 导出前默认要求 `审稿/review_report.json` 存在，并读取 `评分/score_report.json`；报告必须符合 `qa-report-schema.md` 且带 `source_snapshot` 绑定当前 `章节/` 正文 hash，正文新增、删除或改动后旧报告会阻断。商业连载/漫剧源书或目标平台含红果/番茄/抖音/漫剧时，缺 score 也阻断；其他项目缺 score 显示 warning。确需跳过评分，用 `report_gate.py --waive-missing-score --reason "<原因>"` 写带章节 hash 的豁免；只有用户明确要求强制导出时才加 `--ignore-qa-gate`，并自动写带作用域的 `审稿/waiver_log.jsonl`。
- 若未传 `--formats` 且 `_meta.json.outputs` 缺失 / 为空，导出器会直接报错，不再“成功但无产物”。
- 含 `n2d` 时**自动把交接稿铺进 `制漫剧/<书名>/小说/<书名>.docx` + `_n2d_handoff.json` + `asset_registry_preflight.json`（留痕来源/版权/hash/资产标签预检）**——落点是 n2d 标准作品根，`split_novel.py` 直接吃该 docx 即把生产树建在正确位置，**无需 `--out`、不用人工搬运**；export 末尾打印可一键运行的 split 命令。`--n2d-dest` 显式指定落点；找不到含『制漫剧/』的仓库根时回退项目内 `导出/n2d-script/`（此时 split 须带 `--out`，脚本会提示）。
- 依赖：`python-docx`（仅 docx/n2d 格式时）。

```bash
python3 skills/novel-craft/scripts/progress.py "<作品根>"
python3 skills/novel-craft/scripts/progress.py set "<作品根>" draft done
```

```bash
python3 skills/novel-craft/scripts/report_gate.py "<作品根>"          # export 硬闸
python3 skills/novel-craft/scripts/report_gate.py "<作品根>" --progress-mode  # 续跑提示，缺 review 仅 warning
python3 skills/novel-craft/scripts/report_gate.py "<作品根>" --progress-mode --waive-missing-score --reason "<原因>"
```

```bash
python3 skills/novel-craft/scripts/draft_queue.py "<作品根>" init
python3 skills/novel-craft/scripts/draft_queue.py "<作品根>" claim --agent agent-a
python3 skills/novel-craft/scripts/draft_queue.py "<作品根>" done 4 --agent agent-a
```

```bash
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --chapter 4
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --range 4-8
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --next
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --chapter 4 --step trio
```

```bash
python3 skills/novel-craft/scripts/ai_usage.py "<作品根>" --text-mode AI-generated --publish-target KDP
```

## 用法

- **作为被引用方**：其他 skill 的 SKILL.md 通过文件路径引用本 references / scripts。例：novel-spinoff 第 4 步章纲 → 引 `outline.md`；novel-expand 第 5 步 Demo → 引 `chapter.md` + `expand.md`；各派生 skill draft → 先调 `scripts/draft_packets.py`；各派生 skill 第 7/8 步导出 → 调 `scripts/export.py`。
- **作为被直接调用**：用户问"章纲怎么搭""子代理 prompt 怎么写"等通用问题时，把对应 references 摘要回给用户。

## 何时不用本 skill

- 用户在跑完整的 spinoff / expand / condense 流水线 → 走那条 skill 的主流程；本 skill 内容会被那条流水线引用过去。
- 用户在写完全原创小说没有锚点约束 → 本 skill 的 chapter.md / outline.md 仍可用。

## 设计原则

> 跨线通用原则（选择点不写死 C1/C2、脚本不伪装云端自动化 B4、合规闸门 D1…）见 [`docs/skill-design-principles.md`](../../docs/skill-design-principles.md)，此处只列 novel 线特有原则。

- **不抢写作权**：`draft_packets.py` 只生成任务包和状态模板，不直接生成正文；正文仍由当前 novel skill / agent 按项目目标写。
- **可独立摘录**：每个 references 文件都是自包含的，引用方可以只摘其中一节。
- **不重复 novel-* 主流程**：流程性内容在调用方的 SKILL.md / workflow.md 里，本库只放"工艺细节"。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 导出前未检查 QA gate | `export.py` 默认会执行报告验证，直接跳过并强制导出可能会将隐患代入下一生产环节 |
| 跨章设定不记录账本 | 跳过 `state_ledger.json` 会导致后续章节丧失一致性依据，务必通过 `reconcile_ledger.py` 原子化合并新设定 |
| 让 draft_packets.py 直接写正文 | 该脚本仅用于组装上下文和包，不要期望它执行 LLM 写入操作 |
| 手动修改进度文件且不加锁 | 强行在外部编辑 `_进度.md` 可能引发冲突，应始终用 `progress.py set` |
