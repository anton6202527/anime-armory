---
name: novel-craft
description: Shared writing-primitives and deterministic production helpers for the novel-* skill family — generic guides for outline crafting, single-chapter writing discipline, batch draft packet orchestration, arc packets, state ledger updates, in-place expansion, condensation, export, progress, QA gate, and AI usage disclosure. Other novel-* skills reference these by file path; users can also invoke directly for a one-shot writing-craft or drafting workflow question. Triggers 怎么写章纲, 怎么写单章, 子代理 prompt 怎么写, 批量写章, 写作任务包, 弧段任务包, 长篇任务包, draft packets, arc packets, 状态账本, AI使用披露, 写作工艺, novel writing primitives, 章纲编织, 单章守则, 扩写法, 精简法.
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
| **专业资料包注入** | `novel-research` + `资料/research_sources.json` | 医疗/法律/刑侦/金融/军事/历史/宗教/海外/科技/职业文等专业场景；`draft_packets.py` 自动把适用章节的 `资料/专业资料包_<主题>.md` 加进必读源文件 |
| **合规 profile / 平台辖区清单** | `scripts/compliance_profile.py` | KDP/中国公开发布/欧盟/出海/微短剧等目标命中时，生成 `合规/compliance_profile.json` 并在 QA gate 中提示/阻断 |
| **统一修订计划** | `scripts/revision_planner.py` | review/score/balance/feedback/simulate 都跑过后，合并成 `修订/revision_plan.json` + `修订/修订计划.md` |
| **三段式精品写章** | `references/trio-pipeline.md` | 长篇 / `商业连载` / `漫剧源书` / `小说生成工作流=三步迭代`；每章拆成 Architect → Ghostwriter → Senior Editor 三个任务包 |
| **弧段任务包 / 长篇压力测试** | `scripts/arc_packets.py` + `novel-review/scripts/arc_gate.py` | 每 3-5 章或自然 arc 前后；写前物化弧段目标，写后抓连续不推进读者契约、整段无题旨对齐等中段跑偏 |
| **弧段记忆摘要** | `references/arc-memory.md` + `scripts/arc_memory.py` | 每 3-5 章压缩剧情/人物/情绪/未收钩子，写后形成 `arc_summaries.json` / `emotional_progression.json`，写章包自动读取当前弧段摘要 |
| **场景卡（scene cards）** | `references/scene-cards.md` + `scripts/scene_cards.py` | 章纲定稿后，把章节拆成 POV/目标/阻碍/冲突/转折/价值变化的场景卡；`draft_packets.py` 自动注入当前章场景卡 |
| **边写边自检闭环** | `references/draft-pipeline.md` | `小说生成工作流=边写边自检`；任务包自动写入正文 + state_delta + `novel/scripts/post_write.py` 自检闭环，并按 `小批回扫间隔` 保留 3-5 章一次的 `novel-review` 集中修正 |
| **派生流水线后半段（rewrite/continue/expand/condense/spinoff 共用）** | `references/derive-pipeline.md` | 任一派生 skill 的阶段表 / demo_gate / draft / export / ai_usage 通用机制——各 skill 只写自己的 source_model/direction_spec 映射，通用部分引此 |
| 拆分标准（章 / 集 边界 + 字数分档） | `references/split.md` | 章纲编织**之前**先定总章数与字数分档 |
| 章纲编织 | `references/outline.md` | 拆分定下后；进入逐章写作前 |
| 黄金开篇（前三章 / 前 300 字） | `references/opening.md` | 写**第一章**前；留存生死线，字句级落地 |
| 钩子库 + 爽点配比 | `references/hooks.md` | 写章末钩、设计爽点节奏、`novel-review` 查"钩子失效/平铺爽点"时 |
| 题材化情绪三拍（15 题材模板 + 反套路） | `references/情绪节奏.md` | 写章、章纲、配 `tone_curve.json`、`novel-review` 查"情绪曲线/爽点平淡/无情绪点"时 |
| 卷级大节奏（arc） | `references/arc-pacing.md` | 规划/回扫一个 story arc（5-20 章）；`novel-balance` 判卷级起伏 |
| 张力账本 + 行级微张力 | `references/tension-ledger.md` | 追踪未解钩子 / 读者承诺 / 章级张力曲线 + 段落级 micro-tension；`novel-wiki` 逻辑哨兵、写时逐段自检 |
| 伏笔工艺（埋—养—收） | `references/foreshadowing.md` | 埋/回收伏笔、落 `foreshadowing_ledger.json`、`novel-wiki`/`novel-review` 查逾期烂尾 |
| 单章写作守则 | `references/chapter.md` | 每章下笔前；子代理 prompt 模板在此 |
| 对白工艺（潜台词/归属/一人一腔/信息差） | `references/dialogue.md` | 对白多的章、`relationship/confrontation/reveal-scenes` 落地、`novel-review` 查"对白无戏/角色一个腔/talking heads"时 |
| 女频情感（颗粒度/心理戏/CP张力/糖度） | `references/女频情感.md` | 言情/甜宠/先婚后爱/大女主等女频向章节；`draft_packets.py` 按项目题材/平台命中女频时**自动注入**清单；`novel-review` 查"情感悬浮/发糖发腻/工业糖精"时 |
| 描写与文白（白描vs工笔/密度即节奏/古今register） | `references/描写.md` | 写景物/心理/古言历史向；`novel-review` 查"描写堆砌/节奏拖沓/文白串味/开篇慢热"时 |
| 群像与角色弧光（配角辨识度/弧光逐章推进） | `references/群像与角色弧光.md` | 群像多/配角脸盲/主角原地踏步时；`draft_packets.py` 按可选 `设定/角色弧光.json` 注入在场角色弧光阶段、≥3人同台注入群像提醒；`novel-review` 查"配角雷同/弧光停滞"时 |
| 平台雷点 + 反套路（市场避雷） | `references/平台雷点.md` | 选平台/题材、`novel-review` 平台合规预检、`novel-score` 市场匹配；各平台毒点差异 + 精品化迁移 |
| 动作场景专项 | `references/action-scenes.md` | 章纲命中打斗、追逐、逃亡、突破、升级、渡劫时；`draft_packets.py` 会自动把对应清单注入章节任务包 |
| 揭示场景专项 | `references/reveal-scenes.md` | 章纲命中真相揭示、身份曝光、掉马、旧案、内鬼、身世时；自动注入揭示清单 |
| 对质/智斗专项 | `references/confrontation-scenes.md` | 章纲命中公开对质、审讯、逼问、谈判、交易、智斗、当众打脸时；自动注入对质清单 |
| 关系情绪专项 | `references/relationship-scenes.md` | 章纲命中告白、决裂、和解、救赎、互相救场、吃醋、护短时；自动注入关系清单 |
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
| `scripts/qa_gate.py`（薄转发，真值源在 `novel/_lib/qa_gate.py`）/ `scripts/report_gate.py` | 读取 rights / research / review / score / **arc 弧段** / state closure / AI usage / compliance profile / simulate signal-only；缺 review、报告 schema 不合规、报告 hash 过期、阻断 finding、阻断 score verdict、baseline freshness、required 专业资料包缺失、**已跑的 arc_gate 仍含阻断**、写后状态未合并、商业/平台导出缺 AI 披露或平台/辖区合规缺口都会进入 gate；长篇从未跑 arc_gate 会 warning；`drafting` 不因缺 score 阻断，`--waive-missing-score` 只豁免带作用域的缺评分 | progress / export / novel 续跑 |
| `scripts/export.py` | 章节/第NN章.md 合并 → txt / docx / 大纲；默认执行 export QA gate，缺 review 或阻断未清不能导出；`--ignore-qa-gate` 会写带章节 hash / blocker ids / formats 的 waiver log；`--combine` 走续写合本 | create / spinoff / rewrite / expand / condense / continue **共用同一份** |
| `scripts/progress.py` | 扫描 `<作品根>/_进度.md`，输出第一条未完成项 + stage owner/gate/on_fail + QA 阻断；`set <stage> done|todo` 通过 `_进度.lock` 加锁原子更新机器阶段 | 所有会写 `_进度.md` 的 novel-* 项目 |
| `scripts/draft_queue.py` | 批量写章队列：初始化待写章节、claim 租约认领、done/fail/todo 标记，避免小批/多代理重复写同一章 | `draft` 阶段，尤其小批/全书草稿 |
| `scripts/draft_packets.py` | 生成 `写作任务/第NN章.md` 或三段式 `第NN章_{architect,ghostwriter,editor}.md` + 初始化 `审稿/state_ledger.json`；默认要求 Demo gate passed；章纲命中打斗/追逐/逃亡/突破/升级、真相揭示/掉马、公开对质/审讯/谈判、告白/决裂/和解时自动注入专项清单；项目题材/平台为女频·言情向时按题材门控自动注入女频情感清单；有 `资料/research_sources.json` 时自动注入当前章节适用的专业资料包；有 `设定/角色弧光.json` 时注入在场角色弧光阶段、本章 ≥3 名角色同台时注入群像辨识度提醒；不调用 AI | 所有 `draft` 阶段，先包上下文再写章；长篇/商业连载/漫剧源书默认三段式 |
| `scripts/arc_packets.py` | 生成 `写作任务/弧段_第AA-BB章.md` + `审稿/arc_plan_第AA-BB章.json`，把一小段章节的章纲、读者契约、未收线程和 gate 命令物化 | 长篇每 3-5 章或一个自然 arc 的写前计划 |
| `scripts/arc_memory.py` | 生成/检查 `设定/arc_summaries.json` 与 `设定/emotional_progression.json`；把旧章窗口压成可注入的弧段级长期记忆 | 每 3-5 章或自然 arc 写完后 |
| `scripts/scene_cards.py` | 生成/检查 `设定/scene_cards.json`；每个场景记录 POV、目标、阻碍、冲突、转折、价值变化、潜台词与五感锚点 | 章纲定稿后、Demo/批量写章前；`draft_packets.py` 注入当前章场景卡 |
| `scripts/reconcile_ledger.py` | 输出正文/Delta 核对 prompt；仅在提供已通过核对的 `--verified` JSON 后合并入 `state_ledger.json`（`--stamp-hashes` 免手抄 sha256，供写后即时对账）；`--rollup --before N` 压缩旧章逐章明细控制账本膨胀（canonical 状态不动） | 所有 `draft` 阶段，写章后同步状态；长篇定期 rollup |
| `scripts/propose_state_delta.py` | 为单章生成 `审稿/state_delta_第NN章.suggested.json` 草案，含章节 hash、候选实体和待填槽位；确认后再另存正式 delta 并 merge | 写完章节后，减少从空白 JSON 开始写 state_delta 的摩擦 |
| `scripts/ai_usage.py` | 写 `合规/ai_usage.json` + `合规/AI使用说明.md`，记录 AI-generated / AI-assisted / 未使用 AI 文本、人工贡献、AI 介入直接程度、人类 steering、可替代性、直接纳入程度与复核步骤 | 发布、导出、交平台前 |
| `scripts/compliance_profile.py` | 写 `合规/compliance_profile.json` + `.md`；支持 `--confirm <requirement_id>` 留痕平台侧披露/备案/权利确认 | 发布、出海、KDP/中国/欧盟/微短剧等目标 |
| `scripts/revision_planner.py` | 合并 `review_report`、`score_report`、balance/heatmap、`reader_telemetry_summary`、`reader_panel_signals` 为统一修订计划 `修订/revision_plan.json`；**该计划会回流**——`draft_packets.py` 把命中本章的修订任务注入写章包「本章待处理修订项」，`arc_packets.py` 注入弧段窗内任务，不再是无人读的终端报告 | 大改/小改前，避免各报告各说各话 |

## 工业化生产线（批量写章闭环）

1.  **准备阶段**：先用 `python3 skills/novel-craft/scripts/draft_queue.py <作品根> init` 建队列；小批/多代理写章时用 `claim --agent <名字>` 认领章节，再跑 `python3 skills/novel-craft/scripts/draft_packets.py <作品根> --chapter NN`。任务包内含本章章纲、前文摘要、风格锚点及**当前状态账本（State Ledger）**快照。长篇 / `商业连载` / `漫剧源书` 或 `_设置.md` 写 `小说生成工作流：三步迭代` 时，默认生成 `_architect`、`_ghostwriter`、`_editor` 三份任务包；显式 `--step full` 或 `_设置.md` 写 `默认单步` 可降回单包，显式 `--step trio` 可强制三包。长篇每 3-5 章先跑 `arc_packets.py` 生成弧段计划，写完该窗口后跑 `arc_gate.py`。`小说生成工作流：边写边自检` 时，任务包会把 `post_write.py` 写后自检命令写进去，并按 `小批回扫间隔` 提示 3-5 章一次的 novel-review 集中修正；用户只需选择该工作流并按任务包执行。
2.  **写章阶段**：普通项目按 `第NN章.md` 完成 `章节/第NN章.md`；三段式按 `_architect` 产 beats、`_ghostwriter` 产 draft、`_editor` 写最终正文。然后根据内容填写 `审稿/state_delta_第NN章.json`（记录本章引入的新事实、人设变动、新线索）。不想从空白 JSON 开始时，先跑 `propose_state_delta.py --chapter NN` 生成 `.suggested.json` 草案，再人工/AI 补全为正式 delta。
3.  **对账与同步**：
    -   **Audit**：`python3 skills/novel-craft/scripts/reconcile_ledger.py <作品根> --chapter NN --audit`，用输出 prompt 核对正文与 Delta 是否一致，防止「记了没写」或「写了没记」。
    -   **Merge**：把核对结论保存成 `审稿/state_verify_第NN章.json`（必须含 `chapter: NN`、`status: ok`、`chapter_file_hash`、`delta_hash`；hash 由 audit prompt 给出），再跑 `python3 skills/novel-craft/scripts/reconcile_ledger.py <作品根> --chapter NN --merge --verified 审稿/state_verify_第NN章.json`。未经验证不合并，泛化 `{"status":"ok"}` 不合并；正文或 delta 改动导致 hash 不匹配时必须重新 audit。
4.  **质检阶段**：`python3 skills/novel-review/scripts/mechanical_check.py <作品根>` 检查硬伤；字数带宽默认从 `_meta.target_wordcount_min_max` / scale / target words 自动解析，只有人工复核确认需要时才传 `--min/--max` 覆盖。
5.  **循环**：章节通过回扫后用 `draft_queue.py <作品根> done NN --agent <名字>` 标记完成；若返工则 `fail NN --reason "<原因>"` 或 `todo NN` 放回队列，直至完成所有 Demo 章或目标章节。

```bash
python3 skills/novel-craft/scripts/export.py "<作品根>" --formats txt,docx,outline [--combine] [--title "<书名>"]
```

- `--formats` 缺省读 `_meta.json.outputs`；书名缺省按 `_meta.json` 的 `kind` 推导（spinoff=「原作-配角外传」、expand=「原作-扩写」、condense=「原作-精简」、continue=「原作-续写」、rewrite=「原作-改写」、create=`title`）。
- 导出前默认要求 `审稿/review_report.json` 存在，并读取 `评分/score_report.json`、写后状态闭环、AI 使用披露、专业资料包和合规 profile；报告必须符合 `qa-report-schema.md` 且带 `source_snapshot` 绑定当前 `章节/` 正文 hash，正文新增、删除或改动后旧报告会阻断。商业连载/漫剧源书或目标平台含红果/番茄/抖音/漫剧时，缺 score 也阻断；`state_delta` 未合并进 `state_ledger` 会阻断；商业/平台/出海导出缺 `合规/ai_usage.json` 或缺人工贡献记录会阻断；required 专业资料包缺失、高风险资料包过期、KDP/中国公开发布/欧盟/微短剧等目标的合规缺口会阻断或 warning。确需跳过评分，用 `report_gate.py --waive-missing-score --reason "<原因>"` 写带章节 hash 的豁免；只有用户明确要求强制导出时才加 `--ignore-qa-gate`，并自动写带作用域的 `审稿/waiver_log.jsonl`。
- 若未传 `--formats` 且 `_meta.json.outputs` 缺失 / 为空，导出器会直接报错，不再“成功但无产物”。
- 依赖：`python-docx`（仅 docx 格式时）。

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
python3 skills/novel-craft/scripts/propose_state_delta.py "<作品根>" --chapter 4
python3 skills/novel-craft/scripts/revision_planner.py "<作品根>"
```

```bash
python3 skills/novel-craft/scripts/ai_usage.py "<作品根>" \
  --text-mode AI-generated \
  --text-authorship-mode AI生成 \
  --publish-target KDP \
  --human-contribution "用户提供蓝图、设定并人工审稿" \
  --text-directness outline_to_draft \
  --human-steering "人工指定大纲、角色弧和终稿取舍" \
  --replaceability assistive_non_replaceable \
  --direct-incorporation substantial_passages \
  --review-step 人工通读 \
  --review-step 设定一致性审稿
```

```bash
python3 skills/novel-craft/scripts/compliance_profile.py "<作品根>" --write
python3 skills/novel-craft/scripts/compliance_profile.py "<作品根>" \
  --confirm kdp_ai_generated_disclosure \
  --note "已在 KDP UI 完成 AI-generated 披露"
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
