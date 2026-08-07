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
| **作者成书通用流程** | `references/author-workflow.md` + `scripts/author_workflow.py` | 从构思到定稿的引导式工作流：检查作者意图、资料/观察/审美、结构地图、Demo、读者测试、编辑、AI/合规和发布元数据证据，给下一步命令并写 `生产数据/author_workflow.json` / `作者成书流程.md` |
| **设定圣经 schema（统一·单一真值源）** | `references/setting-bible.md` | 建设定/角色卡/世界观时——create 从零建、spinoff/rewrite/continue 从原作抽改，**都用这一套字段**（高杠杆机制按需登记边界与后果 + 首现章/复用范围一致性三列） |
| **批量写章闭环** | `references/draft-pipeline.md` | Demo 过审后进入 draft；需要任务包、状态增量、章节生成粒度、写章回扫时 |
| **生活观察素材库** | `novel-observe` + `素材/观察札记.jsonl` | 人物悬浮、场景缺生活感、职业/地域/日常质感不足时；写章包自动读取 `写作任务/观察素材_第NN章.md`，没有精选包时提示先 select |
| **正向审美样本库** | `novel-aesthetic` + `设定/aesthetic_bank.json` | Demo 高光、授权/公版样本、项目审美标尺；写章包、line edit 和 score 可引用“为什么有效/可迁移规则” |
| **专业资料包注入** | `novel-research` + `资料/research_sources.json` | 医疗/法律/刑侦/金融/军事/历史/宗教/海外/科技/职业文等专业场景；`draft_packets.py` 自动把适用章节的 `资料/专业资料包_<主题>.md` 加进必读源文件 |
| **合规 profile / 平台辖区清单** | `scripts/compliance_profile.py` | KDP/中国公开发布/欧盟/出海/微短剧等目标命中时，生成 `合规/compliance_profile.json` 并在 QA gate 中提示/阻断 |
| **Workflow registry / runner** | `../novel/_lib/novel_pipeline.py` + `../novel/scripts/pipeline_runner.py` | 长流程恢复、薄 agent 编排、dry-run 下一阶段、创建 `pipeline_runs/<run_id>.json`、阶段 claim/complete/fail/block/skip、生成 handoff contract；blueprint/setting 另用 `--approve-stage` 记录与阶段输入、产物 hash 同时绑定的人工批准，输入不全或任一侧变更都不能越过 human gate；runner 不直接写正文或调用模型 |
| **生产控制台** | `novel-dashboard` + `../novel-dashboard/scripts/dashboard.py` | 汇总 pipeline、stale artifacts、语义任务、review/score blockers、revision、batch、release readiness、review board、prompt cache metrics，写 `生产数据/novel_dashboard.*` |
| **批量任务队列** | `novel-batch` + `../novel-batch/scripts/queue.py` | 多章节审稿/评分/dashboard 刷新等任务的本地 flock 队列；支持 claim/lease/renew/reclaim/dead-letter，不直接执行模型 |
| **统一修订计划** | `scripts/revision_planner.py` | review/score/balance/feedback/simulate 都跑过后，合并成 `修订/revision_plan.json` + `修订/修订计划.md` |
| **语义任务队列** | `scripts/semantic_job.py` + `scripts/semantic_schemas.py` | 需要 LLM/人工深读但又要保留机器绑定时，把 prompt、source_snapshot、response_contract、assigned_role、attempts、model/provider、human/review_required、回填命令写成 `语义任务/*.json`；完成时按 schema 校验后才复制到目标产物 |
| **Provenance 事件账本** | `scripts/provenance.py` | pipeline plan、pipeline run、semantic job 创建/领取/完成等关键节点写 `生产数据/provenance.jsonl`，记录输入/输出路径、sha256、工具和元数据，并可查 artifact lineage / OpenLineage 风格事件 |
| **Pipeline golden eval** | `../novel/scripts/tests/golden_pipeline_cases.json` + `../novel/scripts/test_pipeline_eval.py` | 最小原创/导入项目样例，固定 runner next_stage 与 done stage 预期；改 registry、stage 输入输出、gate 时必须同步 |
| **转制就绪检查** | `scripts/screen_adaptation_ready.py` | 小说成品准备进入视觉生产线前，只检查文本、权利、评分、审稿、AI 披露、改编潜力等小说侧条件是否齐备，不生成视觉侧契约 |
| **Review board** | `scripts/review_board.py` | 聚合 review/score/revision/feedback/release 信号，校验 review/score source_snapshot 与 release_manifest 新鲜度，写 `审稿/review_board.{json,md}`，`--html` 另写仲裁页；不替代 QA gate |
| **Prompt cache metrics** | `scripts/prompt_cache_metrics.py` | 递归扫描 `写作任务/**/*.md` 与 `语义任务/**/*.json` 的 `static_context/cache_control`，输出 cache_readiness 估算；若有 usage JSON/JSONL 则汇总真实 cached input tokens，写 `生产数据/prompt_cache_metrics.{json,md}` |
| **三段式精品写章** | `references/trio-pipeline.md` | 长篇 / `商业连载` / `漫剧源书` / `小说生成工作流=三步迭代`；每章拆成 Architect → Ghostwriter → Senior Editor 三个任务包 |
| **弧段任务包 / 长篇压力测试** | `scripts/arc_packets.py` + `novel-review/scripts/arc_gate.py` | 每 3-5 章或自然 arc 前后；写前物化弧段目标，写后抓连续不推进读者契约、整段无题旨对齐等中段跑偏 |
| **弧段记忆摘要** | `references/arc-memory.md` + `scripts/arc_memory.py` | 每 3-5 章压缩剧情/人物/情绪/未收钩子，写后形成 `arc_summaries.json` / `emotional_progression.json`，写章包自动读取当前弧段摘要 |
| **场景卡（scene cards）** | `references/scene-cards.md` + `scripts/scene_cards.py` | 章纲定稿后，把章节拆成 POV/目标/阻碍/冲突/转折/价值变化的场景卡，并补 want/need/misbelief/fear/tactic/choice_cost 人物内驱字段；`draft_packets.py` 自动注入当前章场景卡 |
| **边写边自检闭环** | `references/draft-pipeline.md` | `小说生成工作流=边写边自检`；任务包自动写入正文 + state_delta + `novel/scripts/post_write.py` 自检闭环，并按 `小批回扫间隔` 保留 3-5 章一次的 `novel-review` 集中修正 |
| **派生流水线后半段（rewrite/continue/expand/condense/spinoff 共用）** | `references/derive-pipeline.md` | 任一派生 skill 的阶段表 / demo_gate / draft / export / ai_usage 通用机制——各 skill 只写自己的 source_model/direction_spec 映射，通用部分引此 |
| 拆分标准（章 / 集 边界 + 字数分档） | `references/split.md` | 章纲编织**之前**先定总章数与字数分档 |
| 章纲编织 | `references/outline.md` | 拆分定下后；进入逐章写作前 |
| 黄金开篇（前三章 / 前 300 字） | `references/opening.md` | 写**第一章**前；留存生死线，字句级落地 |
| 钩子库 + 爽点配比 | `references/hooks.md` | 写章末钩、设计爽点节奏、`novel-review` 查"钩子失效/平铺爽点"时 |
| 结局/完本工艺（终局弧/清账/尾声落点） | `references/ending.md` | 进度过 ~85% 规划终局弧、完本前清账（伏笔/支线/must_answer）、`novel-score` 完本评估、防仓促收/无限拖/主题跑偏三形态烂尾 |
| 题材化情绪三拍（15 题材模板 + 反套路） | `references/情绪节奏.md` | 写章、章纲、配 `tone_curve.json`、`novel-review` 查"情绪曲线/爽点平淡/无情绪点"时 |
| 卷级大节奏（arc） | `references/arc-pacing.md` | 规划/回扫一个 story arc（5-20 章）；`novel-balance` 判卷级起伏 |
| 张力账本 + 行级微张力 | `references/tension-ledger.md` | 追踪未解钩子 / 读者承诺 / 章级张力曲线 + 段落级 micro-tension；`novel-wiki` 逻辑哨兵、写时逐段自检 |
| 伏笔工艺（埋—养—收） | `references/foreshadowing.md` | 埋/回收伏笔、落 `foreshadowing_ledger.json`、`novel-wiki`/`novel-review` 查逾期烂尾 |
| 单章写作守则 | `references/chapter.md` | 每章下笔前；子代理 prompt 模板在此 |
| 对白工艺（潜台词/归属/一人一腔/信息差） | `references/dialogue.md` | 对白多的章、`relationship/confrontation/reveal-scenes` 落地、`novel-review` 查"对白无戏/角色一个腔/talking heads"时 |
| 女频情感（颗粒度/心理戏/CP张力/糖度） | `references/女频情感.md` | 言情/甜宠/先婚后爱/大女主等女频向章节；`draft_packets.py` 按项目题材/平台命中女频时**自动注入**清单；`novel-review` 查"情感悬浮/发糖发腻/工业糖精"时 |
| 描写与文白（白描vs工笔/密度即节奏/古今register） | `references/描写.md` | 写景物/心理/古言历史向；`novel-review` 查"描写堆砌/节奏拖沓/文白串味/开篇慢热"时 |
| 文笔精修（叙事距离/滤镜词/自由间接引语/词汇意外度/专业质感） | `references/文笔精修.md` | 写章精修、`novel-edit` line packet、`novel-review` 查 `prose/文学质感`；是 `novel-review/scripts/prose_craft_audit.py`（滤镜词/副词标签/说教结尾/情绪生理化）的写作侧对手盘 |
| 转场与衔接（因果链但/因此·断章勾-开章拉·转场类型·多线交叉） | `references/转场与衔接.md` | 编章纲、写章、`novel-review` 查"剧情散/章节割裂/开篇复述/多线断线"；对应机检 `chapter_transition.py`（章首承接）+ `plot_variety_audit.py`（开篇同型） |
| 世界观构建（新奇感/会生场景的核心设定/冰山铺陈/自洽） | `references/世界观构建.md` | 立世设、玄幻/科幻/脑洞/规则怪谈、`novel-review` 查"世界观悬浮/炫设定无戏/规则打架"；与 `setting-bible.md`（存储）、`力量体系设计.md`（数值）分工 |
| 喜剧与轻松感（笑点五源/吐槽流/反差萌/喜剧节奏） | `references/喜剧与轻松感.md` | 轻松向章节/系统吐槽/日常番外、`novel-review` 查"该好笑却冷场/强行搞笑尬"时 |
| 名场面/高光场景（set-piece 五型·四放大器·布局） | `references/名场面.md` | 规划高光章/写卷末大高潮/终局、`novel-review` 查"该封神却平淡"、`novel-score` ⑧"可一句话转述传播"；一本书压 1-3 个 |
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
| `../novel/scripts/pipeline_runner.py` | 读取 `novel_pipeline.py` registry，生成 `生产数据/novel_pipeline_plan.{json,md}`，声明每阶段 owner/input/output/gate/cost/semantic/parallel/agent_role；可创建 `pipeline_runs/<run_id>.json` 并对阶段 claim/complete/fail/block/skip；`--artifact-graph` 查产物依赖和 stale，`--handoff <stage>` 生成 specialist agent 边界契约，`--approve-stage blueprint|setting --agent ... --reason ...` 记录 hash-bound 人工批准 | 长流程 dry-run、恢复、agent 编排前置 |
| `scripts/qa_gate.py`（薄转发，真值源在 `novel/_lib/qa_gate.py`）/ `scripts/report_gate.py` | 读取 rights / research / review / score / **arc 弧段** / state closure / AI usage / compliance profile / simulate signal-only；缺 review、报告 schema 不合规、报告 hash 过期、阻断 finding、阻断 score verdict、baseline freshness、required 专业资料包缺失、**已跑的 arc_gate 仍含阻断**、写后状态未合并、商业/平台导出缺 AI 披露或平台/辖区合规缺口都会进入 gate；长篇从未跑 arc_gate 会 warning；`drafting` 不因缺 score 阻断，`--waive-missing-score` 只豁免带作用域的缺评分 | progress / export / novel 续跑 |
| `scripts/export.py` | 章节/第NN章.md 合并 → txt / docx / 大纲；默认执行 export QA gate，缺 review 或阻断未清不能导出；`--ignore-qa-gate` 会写带章节 hash / blocker ids / formats 的 waiver log；`--combine` 走续写合本 | create / spinoff / rewrite / expand / condense / continue **共用同一份** |
| `scripts/progress.py` | 扫描 `<作品根>/_进度.md`，输出第一条未完成项 + stage owner/gate/on_fail + QA 阻断；`set <stage> done|todo` 通过 `_进度.lock` 加锁原子更新机器阶段 | 所有会写 `_进度.md` 的 novel-* 项目 |
| `scripts/author_workflow.py` | 按 `author-workflow.md` 检查从构思到定稿的默认证据链，并读取 research/review/score/reader/edit/AI/metadata/release 报告里的 blocker/warning，输出当前步骤和下一步命令，可写 `生产数据/author_workflow.json` / `作者成书流程.md`；不写正文、不改进度 | 用户要“按流程一步步成书”、dashboard/supervisor 需要作者视角状态 |
| `scripts/author_intent.py` | 脚手架/检查 `设定/author_intent.json` + `设定/作者意图.md`，固化主题、目标余味、不可妥协项、审美/伦理边界、禁用套路和误读风险 | 蓝图前；让后续设定、读者契约、审稿和编辑有作者意图基准 |
| `scripts/demo_readiness.py` | Demo 章批量写作前双闸门：读取 `demo_gate.json`、`score_report.json` 和 `aesthetic_bank.json`，输出商业放量 gate + 文学/审美锚点 gate + 黄金三章硬对表（`DEMO-OPENING-CONFLICT-HOLLOW`/`DEMO-SELLING-POINT-LATE`；2026-07 第五轮增 `DEMO-EARLY-FLASHBACK`——前 3 章单章 ≥2 段命中强闪回引导词=开篇回忆杀退稿信号，词表 `keyword_banks.FLASHBACK_MARKERS`，倒叙框架人工豁免），写 `审稿/demo_readiness.{json,md}`；`ready_for_batch=false` 时 pipeline/author_workflow 阻断 | Demo 章过审后、批量写章前，避免开篇未验证就长篇扩写 |
| `scripts/draft_queue.py` | 批量写章队列：初始化待写章节、claim 租约认领、done/fail/todo 标记，避免小批/多代理重复写同一章 | `draft` 阶段，尤其小批/全书草稿 |
| `scripts/draft_packets.py` | 生成 `写作任务/第NN章.md` 或三段式 `第NN章_{architect,ghostwriter,editor}.md` + 初始化 `审稿/state_ledger.json`；默认要求 Demo gate passed；章纲命中打斗/追逐/逃亡/突破/升级、真相揭示/掉马、公开对质/审讯/谈判、告白/决裂/和解时自动注入专项清单；项目题材/平台为女频·言情向时按题材门控自动注入女频情感清单；有 `资料/research_sources.json` 时自动注入当前章节适用的专业资料包；有 `写作任务/观察素材_第NN章.md` 时注入生活观察精选；有 `设定/aesthetic_bank.json` 时注入正向审美迁移规则；有 `设定/角色弧光.json` 时注入在场角色弧光阶段、本章 ≥3 名角色同台时注入群像辨识度提醒；不调用 AI | 所有 `draft` 阶段，先包上下文再写章；长篇/商业连载/漫剧源书默认三段式 |
| `scripts/arc_packets.py` | 生成 `写作任务/弧段_第AA-BB章.md` + `审稿/arc_plan_第AA-BB章.json`，把一小段章节的章纲、读者契约、未收线程和 gate 命令物化 | 长篇每 3-5 章或一个自然 arc 的写前计划 |
| `scripts/arc_memory.py` | 生成/检查 `设定/arc_summaries.json` 与 `设定/emotional_progression.json`；把旧章窗口压成可注入的弧段级长期记忆 | 每 3-5 章或自然 arc 写完后 |
| `scripts/scene_cards.py` | 生成/检查 `设定/scene_cards.json`；每个场景记录 POV、目标、阻碍、冲突、转折、价值变化、潜台词与五感锚点，另有可选 `outcome`（场景结局极性 yes/yes-but/no-and/no-but，try-fail 循环纪律）与 `plotline`（情节线标签）、`turn_source`（转折能动性来源枚举：主角行动/对手行动/盟友援手/伏笔兑现/巧合——Pixar 巧合纪律的数据面）；outcome/turn_source 填了但不在枚举内分别报 `SCENE-CARD-OUTCOME-INVALID`/`SCENE-CARD-TURN-SOURCE-INVALID`（建议级） | 章纲定稿后、Demo/批量写章前；`draft_packets.py` 注入当前章场景卡 |
| `scripts/manuscript_map.py` | 从 `设定/章纲.md`、`scene_cards.json` 和 `章节/第*.md` 生成 `设定/manuscript_map.{json,md}`，按章列出主欲望、阻碍、转折、价值变化、揭示/回收和五感锚点；缺转折/价值变化会阻断。review 链 advisory 信号：`SEQUEL-GAP-RUN`（连续高压不落地）、`SENSORY-ANCHOR-DROPPED`（意象锚被丢弃）、`OUTCOME-YES-RUN`/`OUTCOME-NO-COST-CLIMB`（try-fail 缺失：无阻力连胜/全书 yes 占比过高，outcome 填充率不足优雅跳过）、`PLOTLINE-LONG-RUN`（金圣叹"横云断山"：同线连续过长无间笔）、`CLIMAX-NO-AFTERWAVE`（金圣叹"獭尾法"：张力峰值章无余波、下一章开场即新冲突）；2026-07 第五轮增：`SCENE-GROUNDING-DROPPED`（场景落地对账——场景卡登记 pov+location/time 而章首 250 字双双零命中=悬空开场，词段拆 2-gram 命中、保守方向压告警）、`TURN-COINCIDENCE-RESCUE`（Pixar 第 19 条：turn_source=巧合且 outcome 有利=巧合捞人出麻烦是作弊；巧合+失败合法不报）、`SCENE-REPEAT-NO-VARIATION`（金圣叹"正犯法"/毛宗岗"同树异枝"：跨章同 POV 同地点同结局极性且目标/阻碍 2-gram 相似度 ≥0.6=犯而不避，专治 AI 自我复写；系列套路戏人工豁免） | 中长篇 review/edit 前，把全稿结构变成可审查地图 |
| `scripts/reconcile_ledger.py` | 输出正文/Delta 核对 prompt，并登记带 `ledger_reconcile` schema 与 hash snapshot 的 `语义任务/`；仅在提供已通过核对的 `--verified` JSON 后合并入 `state_ledger.json`（`--stamp-hashes` 免手抄 sha256，供写后即时对账）；`--rollup --before N` 压缩旧章逐章明细控制账本膨胀（canonical 状态不动） | 所有 `draft` 阶段，写章后同步状态；长篇定期 rollup |
| `scripts/semantic_job.py` | 创建/展示/领取/阻塞/拒收/重开/完成/审核批准绑定 prompt 的语义任务；任务含 schema_ref、source_snapshot、response_contract、assigned_role、attempts、provider/model、cost_estimate、human_required、review_required，完成时按 `semantic_schemas.py` 校验 JSON 并写 provenance 后复制到目标产物 | 需要 AI/人工判断但必须可追踪、可续跑的步骤 |
| `scripts/provenance.py` | 追加写 `生产数据/provenance.jsonl`；记录输入/输出文件 sha256、工具、事件类型与元数据；支持 `lineage` / `artifact-events` / `openlineage` 查询 | runner、semantic job、后续关键 workflow 脚本 |
| `scripts/propose_state_delta.py` | 为单章生成 `审稿/state_delta_第NN章.suggested.json` 草案，含章节 hash、候选实体和待填槽位；确认后再另存正式 delta 并 merge | 写完章节后，减少从空白 JSON 开始写 state_delta 的摩擦 |
| `scripts/ai_usage.py` | 写 `合规/ai_usage.json` + `合规/AI使用说明.md`，分别记录文本、图片/封面、译文的 AI-generated / AI-assisted / 未使用状态，以及人工贡献、AI 介入直接程度、人类 steering、可替代性、直接纳入程度、复核步骤和逐章 `chapter_usage` | 发布、导出、交平台前 |
| `scripts/compliance_profile.py` | 写 `合规/compliance_profile.json` + `.md`；支持 `--confirm <requirement_id>` 留痕平台侧披露/备案/权利确认 | 发布、出海、KDP/中国/欧盟/微短剧等目标 |
| `scripts/metadata_pack.py` | 写 `导出/metadata_pack.json` + `.md`，整理标题、副标题、系列信息、短简介、长简介、关键词、分类、年龄/内容提示、平台目标、权利摘要和 AI/合规披露摘要 | 投稿、平台发布、KDP/self-pub 前；release manifest 发布 profile 会检查 |
| `scripts/revision_planner.py` | 合并 `review_report`、`score_report`、balance/heatmap、真实读者反馈、合成叙事探针（仅 P2 人工复核假设）、市场证据任务为统一修订计划 `修订/revision_plan.json`；**该计划会回流**——`draft_packets.py` 把命中本章的修订任务注入写章包「本章待处理修订项」，`arc_packets.py` 注入弧段窗内任务，不再是无人读的终端报告。2026-07 增 **macro-before-micro 修订纪律**（传统编辑共识：结构未锁前不做行文修补，否则移场景/并章时行文功夫白费）：每个任务自动归 structure/scene/line 三层（`tier` 字段），同优先级内结构级先行；存在未决结构级 P0/P1 时行文级任务打 `deferred_until_structure` 缓办标记（不删任务，只排序+标记，Markdown 表有 tier 列） | 大改/小改前，避免各报告各说各话 |
| `scripts/character_arc_audit.py` | 人物弧线推进机检（advisory）：scene_cards 人物引擎字段（Weiland Lie/Want/Need 内构）的跨章对账——want==need 逐字相同（内外目标塌缩）、misbelief 连续 ≥6 章不付 choice_cost（谎言从不逼选择=弧线停摆）、引擎填充率前紧后松（计划纪律衰减）；引擎字段从未启用则优雅跳过。已接进 `consistency_audit`（键 `character_arc`）与 review_report | 中长篇每次 review；弧段收口前 |
| `scripts/screen_adaptation_ready.py` | 检查导出文本/章节、权利声明、核心设定、审稿、评分、AI 使用披露、短剧/漫剧目标的改编潜力与市场基准，写 `导出/转制就绪检查.md` + JSON；缺必要结构/权利/报告可阻断，主观评分与改编潜力阈值只 warning | 小说成品准备进入视觉生产线前的小说侧准入 |
| `scripts/manage_takes.py` | 登记、列出、选择同一章节多版 take；可配合 `novel-score` 对 take 独立评分并同步 manifest | A/B、开篇多版、章节多版挑选 |
| `scripts/story_vcs.py` | VCS-free 文件级分支：branch manifest 记录 base hash，merge dry-run 检冲突/缺分支文件/legacy 无 base hash，正式 merge 先备份并写 audit/provenance，可 rollback；`migrate` 迁移旧分支，`health` 汇总分支健康；旧分支无 base hash 必须显式 `--accept-legacy-no-base` 或可信迁移 `--trust-current-main` | 多版设定/百科/进度试写，避免 A/B 分支静默覆盖主线 |
| `scripts/release_manifest.py` | 固化导出物、章节、review/score、AI 使用、合规 profile、research、revision、reader test、metadata pack、waiver 的 hash，写 `导出/release_manifest.{json,md}`，并按 `--release-profile internal_draft|beta_read|platform_publish|kdp_publish|data_validated_launch|archive` 计算 `release_ready`；普通 platform/KDP 发布把缺 reader telemetry 记为市场验证 warning，只有显式 `data_validated_launch` 才把 reader plan + 真实 telemetry 设为硬前置 | 导出/投稿/交付前，证明各报告绑定同一版文本 |
| `../novel/scripts/vector_store_eval.py` | 读取 `生产数据/retrieval_golden.json`，从保存 index 或 `章节/` 构建检索库，按 Recall@K/MRR 阈值写 `生产数据/vector_store_eval.{json,md}` 并作为回归闸门 | 长篇记忆/RAG/别名与时间线检索质量回归 |

## 工业化生产线（批量写章闭环）

1.  **准备阶段**：先用 `python3 skills/novel/novel-craft/scripts/draft_queue.py <作品根> init` 建队列；小批/多代理写章时用 `claim --agent <名字>` 认领章节，再跑 `python3 skills/novel/novel-craft/scripts/draft_packets.py <作品根> --chapter NN`。任务包内含本章章纲、前文摘要、风格锚点及**当前状态账本（State Ledger）**快照。长篇 / `商业连载` / `漫剧源书` 或 `_设置.md` 写 `小说生成工作流：三步迭代` 时，默认生成 `_architect`、`_ghostwriter`、`_editor` 三份任务包；显式 `--step full` 或 `_设置.md` 写 `默认单步` 可降回单包，显式 `--step trio` 可强制三包。长篇每 3-5 章先跑 `arc_packets.py` 生成弧段计划，写完该窗口后跑 `arc_gate.py`。`小说生成工作流：边写边自检` 时，任务包会把 `post_write.py` 写后自检命令写进去，并按 `小批回扫间隔` 提示 3-5 章一次的 novel-review 集中修正；用户只需选择该工作流并按任务包执行。
2.  **写章阶段**：普通项目按 `第NN章.md` 完成 `章节/第NN章.md`；三段式按 `_architect` 产 beats、`_ghostwriter` 产 draft、`_editor` 写最终正文。然后根据内容填写 `审稿/state_delta_第NN章.json`（记录本章引入的新事实、人设变动、新线索）。不想从空白 JSON 开始时，先跑 `propose_state_delta.py --chapter NN` 生成 `.suggested.json` 草案，再人工/AI 补全为正式 delta。
3.  **对账与同步**：
    -   **Audit**：`python3 skills/novel/novel-craft/scripts/reconcile_ledger.py <作品根> --chapter NN --audit`，用输出 prompt 核对正文与 Delta 是否一致，防止「记了没写」或「写了没记」；脚本会把该核对登记为 `语义任务/*.json`，方便后续 agent 接着完成。
    -   **Merge**：把核对结论保存成 `审稿/state_verify_第NN章.json`（必须含 `chapter: NN`、`status: ok`、`chapter_file_hash`、`delta_hash`；hash 由 audit prompt 给出），再跑 `python3 skills/novel/novel-craft/scripts/reconcile_ledger.py <作品根> --chapter NN --merge --verified 审稿/state_verify_第NN章.json`。未经验证不合并，泛化 `{"status":"ok"}` 不合并；正文或 delta 改动导致 hash 不匹配时必须重新 audit。
4.  **质检阶段**：`python3 skills/novel/novel-review/scripts/mechanical_check.py <作品根>` 检查硬伤；字数带宽默认从 `_meta.target_wordcount_min_max` / scale / target words 自动解析，只有人工复核确认需要时才传 `--min/--max` 覆盖。
5.  **循环**：章节通过回扫后用 `draft_queue.py <作品根> done NN --agent <名字>` 标记完成；若返工则 `fail NN --reason "<原因>"` 或 `todo NN` 放回队列，直至完成所有 Demo 章或目标章节。

```bash
python3 skills/novel/novel-craft/scripts/export.py "<作品根>" --formats txt,docx,outline [--combine] [--title "<书名>"]
```

- `--formats` 缺省读 `_meta.json.outputs`；书名缺省按 `_meta.json` 的 `kind` 推导（spinoff=「原作-配角外传」、expand=「原作-扩写」、condense=「原作-精简」、continue=「原作-续写」、rewrite=「原作-改写」、create=`title`）。
- 导出前默认要求 `审稿/review_report.json` 存在，并读取适用的 `评分/score_report.json`、写后状态闭环、AI 使用披露、专业资料包和合规 profile；报告必须符合 schema 且用 `source_snapshot` 绑定当前正文。缺适用报告、schema/snapshot/freshness 损坏可阻断；主观 score verdict 只 warning。普通 `platform_publish` / `kdp_publish` 不要求先有真实读者历史数据；缺 telemetry 只提示市场验证不足，显式 `data_validated_launch` 才要求 reader plan + telemetry 或 scoped waiver。确需跳过确定性 gate 时必须显式留痕。
- 若未传 `--formats` 且 `_meta.json.outputs` 缺失 / 为空，导出器会直接报错，不再“成功但无产物”。
- 依赖：`python-docx`（仅 docx 格式时）。

```bash
python3 skills/novel/novel-craft/scripts/author_workflow.py "<作品根>" --write
python3 skills/novel/novel-craft/scripts/author_intent.py scaffold "<作品根>"
python3 skills/novel/novel-craft/scripts/manuscript_map.py "<作品根>" --write
python3 skills/novel/novel-craft/scripts/demo_readiness.py "<作品根>" --write
python3 skills/novel/novel-craft/scripts/progress.py "<作品根>"
python3 skills/novel/novel-craft/scripts/progress.py set "<作品根>" draft done
```

```bash
python3 skills/novel/novel-craft/scripts/report_gate.py "<作品根>"          # export 硬闸
python3 skills/novel/novel-craft/scripts/report_gate.py "<作品根>" --progress-mode  # 续跑提示，缺 review 仅 warning
python3 skills/novel/novel-craft/scripts/report_gate.py "<作品根>" --progress-mode --waive-missing-score --reason "<原因>"
```

```bash
python3 skills/novel/scripts/pipeline_runner.py "<作品根>" --write-plan
python3 skills/novel/scripts/pipeline_runner.py --registry-only
python3 skills/novel/scripts/pipeline_runner.py "<作品根>" --artifact-graph --json
python3 skills/novel/scripts/pipeline_runner.py "<作品根>" --handoff blueprint
python3 skills/novel/scripts/pipeline_runner.py "<作品根>" --approve-stage blueprint --agent "<复核人>" --reason "<批准说明>"
python3 skills/novel/scripts/pipeline_runner.py "<作品根>" --start-run --agent orchestrator
python3 skills/novel/scripts/pipeline_runner.py "<作品根>" --run-id run_YYYYMMDD_HHMMSS --claim-stage blueprint --agent writer-agent
python3 skills/novel/scripts/pipeline_runner.py "<作品根>" --run-id run_YYYYMMDD_HHMMSS --complete-stage blueprint
```

```bash
python3 skills/novel/novel-dashboard/scripts/dashboard.py "<作品根>" --write --html
python3 skills/novel/novel-batch/scripts/queue.py plan "<作品根>" --kind review --chapters 1-10
python3 skills/novel/novel-batch/scripts/queue.py claim "<作品根>" --worker worker-a --json
python3 skills/novel/novel-batch/scripts/queue.py mark "<作品根>" --task-id "<task_id>" --worker worker-a --status pass
```

```bash
python3 skills/novel/novel-craft/scripts/draft_queue.py "<作品根>" init
python3 skills/novel/novel-craft/scripts/draft_queue.py "<作品根>" claim --agent agent-a
python3 skills/novel/novel-craft/scripts/draft_queue.py "<作品根>" done 4 --agent agent-a
```

```bash
python3 skills/novel/novel-craft/scripts/draft_packets.py "<作品根>" --chapter 4
python3 skills/novel/novel-craft/scripts/draft_packets.py "<作品根>" --range 4-8
python3 skills/novel/novel-craft/scripts/draft_packets.py "<作品根>" --next
python3 skills/novel/novel-craft/scripts/draft_packets.py "<作品根>" --chapter 4 --step trio
```

```bash
python3 skills/novel/novel-craft/scripts/propose_state_delta.py "<作品根>" --chapter 4
python3 skills/novel/novel-craft/scripts/revision_planner.py "<作品根>"
```

```bash
python3 skills/novel/novel-craft/scripts/semantic_job.py show "<作品根>/语义任务/<job_id>.json"
python3 skills/novel/novel-craft/scripts/semantic_job.py claim "<作品根>/语义任务/<job_id>.json" --claimed-by reviewer --model-provider openai --model "<model>"
python3 skills/novel/novel-craft/scripts/semantic_job.py complete "<作品根>/语义任务/<job_id>.json" --response "<评估或核对JSON>"
python3 skills/novel/novel-craft/scripts/semantic_job.py approve "<作品根>/语义任务/<job_id>.json" --reviewer human-editor
python3 skills/novel/novel-craft/scripts/provenance.py lineage "<作品根>" "审稿/review_report.json"
python3 skills/novel/novel-craft/scripts/provenance.py openlineage "<作品根>"
```

```bash
python3 skills/novel/novel-craft/scripts/screen_adaptation_ready.py "<作品根>"
python3 skills/novel/novel-craft/scripts/release_manifest.py "<作品根>" --release-name v1
python3 skills/novel/novel-craft/scripts/release_manifest.py "<作品根>" --release-name beta1 --release-profile beta_read
python3 skills/novel/novel-craft/scripts/release_manifest.py "<作品根>" --release-name kdp-v1 --release-profile kdp_publish
python3 skills/novel/novel-craft/scripts/release_manifest.py "<作品根>" --release-name v1 --allow-not-ready
python3 skills/novel/novel-craft/scripts/metadata_pack.py "<作品根>" --write
python3 skills/novel/novel-craft/scripts/review_board.py "<作品根>" --write
python3 skills/novel/novel-craft/scripts/review_board.py "<作品根>" --write --html
python3 skills/novel/novel-craft/scripts/prompt_cache_metrics.py "<作品根>" --write
python3 skills/novel/novel-craft/scripts/prompt_cache_metrics.py "<作品根>" --usage-file 生产数据/model_usage.jsonl --write
python3 skills/novel/scripts/vector_store_eval.py "<作品根>" --write
```

```bash
python3 skills/novel/novel-craft/scripts/ai_usage.py "<作品根>" \
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
python3 skills/novel/novel-craft/scripts/compliance_profile.py "<作品根>" --write
python3 skills/novel/novel-craft/scripts/compliance_profile.py "<作品根>" \
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
| 多份报告各自回流 | 先跑 `revision_planner.py` 生成统一修订计划，再让写章包/弧段包读取计划，不要让 review、score、市场证据各自驱动改稿 |
| 小说侧直接生成视觉生产契约 | 小说线只跑 `screen_adaptation_ready.py` 判断是否具备转制条件；视觉资产、镜头、音频、合成等生产约束由用户显式选择的生产线重新建立 |
| 导出后没有版本留痕 | 跑 `release_manifest.py`，把导出物与 review/score/AI 使用/资料包 hash 绑定，避免交付物和报告错版 |
