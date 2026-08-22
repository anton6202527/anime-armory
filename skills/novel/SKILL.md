---
name: novel
description: Top-level dispatcher for the novel-* skill family — inspects an open-ended novel request (a bare idea / exploratory draft / few words / book name / URL / dragged file path / spin-off character / expand·condense·rewrite / 审稿查硬伤 / 评分·能不能火 / 专业资料包 / 真实性文化审读 / 真实读者反馈) and routes to the right sub-skill, imports a dragged novel file/link into 创作区/写小说/项目名/ when no action is specified, or resumes an in-progress 创作区/写小说/项目名/ from its _进度.md. Use when the user gives a novel-related task without specifying which tool. Does not write novels itself — only routes/imports source material; the canonical sub-skill roster is the routing table in the body. Triggers 小说工坊, novel, 小说相关任务, 探索型写作, 角色试镜, 拖进一本小说, 导入小说, 帮我处理小说, 不知道用哪个小说 skill, 小说打分, 小说评分, 能不能火, 值不值得改, 审稿, 真实性审读, 文化审读, 专业资料包, 行业感, 别外行, 医疗法律刑侦金融军事历史宗教海外科技职业文, 真实读者反馈, 完读率, 弃读, 力量体系, 等级一致性, 战力崩坏, 系统流升级, 系统面板, 小说进度, novel-progress.
---
> 规模统计：Skill 数 29 | SKILL.md 总行数 3308 | 目录文本总行数 83453

# novel — 小说工坊调度入口

不直接写小说，**读取用户输入 → 路由**到 novel-* 家族最合适的 sub-skill。

本线只管纯文本小说生产，**产物统一落 `创作区/写小说/<项目>/`**（如 `创作区/写小说/仙界闭关小能手-王敦外传/`）。

**生产数据分层与独立性**：小说正文、蓝图、设定、状态账、评审与事件账仍是 novel 自己的业务真值；`生产数据/artifact_catalog.json` 只是可删除、可重建的只读索引，缺失或过期不得阻断 novel。机器真值优先 JSON/JSONL，给人看的重复 Markdown/HTML 放 `生产数据/views/` 并标明来源；缓存必须可重建并有清理边界。路径只持久化作品根相对路径。novel 不 import `tools/artifact-catalog`、其它系列实现，也不读取其它系列作品目录。

**当前默认口径保持不变**：`写小说` 默认进入 novel 纯文本小说生产线，但不默认等于“专门制作漫剧的小说”。新建原创项目时先定 `小说用途`，且该选择点**无默认值**；用户可选 `传统小说 / 漫剧源书 / 微短剧源书 / 短读/短篇 / 出海译制底稿 / 自定义`。只有用户明确选择 `漫剧源书` 或 `微短剧源书`，才启用对应的短章、强钩子、市场基准和后续转制检查；否则按普通小说/网文项目推进。

**默认成书工作流**：已有作品根时，优先跑 `python3 skills/novel/novel-craft/scripts/author_workflow.py "<作品根>" --write`。它会按作者视角检查“入口设置与 human-first seed / 非正史探索 → 作者意图/蓝图/读者契约 → 资料/观察/审美与事实落场景 → 按创作工艺档建立场景卡/结构地图 → Demo 双闸门 → 分章写作 → review/score → 真实读者验证 → 分层编辑、editor query 与按需真实性/文化审读 → AI/合规/发布元数据 → release manifest”，输出当前步骤、真实 blocker/warning 和下一步命令；`flow.py`、`pipeline_runner.py`、`novel-dashboard` 都以这套默认流程作为可落地的导航层。

**一键成书默认**：新项目默认 `审阅策略=用户授权制作代理`。蓝图、设定圣经和 Demo 仍必须经过与写作角色分离的 specialist review，但 supervisor 应返回 `dispatch` 并在同一任务连续派发，不再一律 `needs_human`。蓝图/设定批准用 `pipeline_runner.py --approve-stage ... --delegated --agent delegate:novel-specialist-reviewer` 写 hash-bound receipt，明确 `review_mode=delegated_autonomy`、`independent_human_review=false`，绝不冒充人审。只有 author intent/权利来源等真实缺失、显式 `human_required` 语义任务、跨来源冲突、连续三次同因失败、不可逆发布与最终署名/验收停下。

**Prompt 分层裁决（2026-07）**：小说线不新增“把完整写作合同压成短 prompt”的 provider compiler。蓝图、设定圣经、状态账本、读者契约、章纲、场景卡、上一章窗口与修订项本来就是正文生成所需上下文，擅自精简会造成设定/人物/伏笔漂移。正确边界由 `draft_packets.py` 的逐章/逐 pass 任务包、static/dynamic context、检索命中、source/state hash、语义任务绑定和 `prompt_cache_metrics.py` 提供；只有某个实际文本后端出现独立结构字段时，才在小说线 `_lib` 内新增对应 adapter，不能为了与其它媒介形式统一而强造 compiler。

**本系列成员**见下方"路由规则"表（家族唯一权威名册；新增/移除子 skill 只改那张表）。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/novel/novel-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md`；再缺则对普通、可逆项采用推荐值并写回，同项目沉默沿用。权利/合规、不可逆发布与最终验收仍确认；模型费用按一次阶段预算包授权，包内不逐章重复问。

本 skill 涉及的选择点：`小说用途`、`目标平台`、`创作工艺档`、`权利来源`、`权利辖区`、`发行地区`、`输出格式`、`篇幅档`、`小说生成模式`、`小说生成工作流`、`小批回扫间隔`、`章节生成粒度`、`审阅策略`、`文本主创模式`、`AI使用披露`。

> 作为入口：路由到子 skill 前，若已有项目则读其 `<作品根>/_设置.md`，新项目按全局默认初始化。

## 路由规则

> 机器校验源：`novel-craft/scripts/registry.py`；测试会校验它与本表、`skills/README.md`、磁盘目录一致。

| 用户输入形态 | 路由到 |
|---|---|
| **只有几个字 / 一个想法 / 部分风格 / 零散笔记 / 半成品片段**，没有成型源文 → 要写一本**原创新书** | `novel-create`（先保留 human-first seed；可先非正史探索，再访谈→蓝图→设定→章纲→Demo→成书） |
| 拖进来一本**本地小说文件/目录/file:///URL**，但没说下一步动作，只是要先建档 | `novel/scripts/import_novel.py` → `创作区/写小说/<书名>/` |
| 给了**书名 / 作者 / URL**，明确要把公版书"取回来" | `novel-fetch` |
| 已有原作 + 想**起一个好书名** | `novel-title` |
| 已有原作 + 指定一个**配角名**，要**视角续写**（POV 切换、事件锁定） | `novel-spinoff` |
| 已有原作 + 要**改主线 / 换设定 / 加原创材料**（魔改 / 重构 / 翻拍 / 二创重写） | `novel-rewrite` |
| 已有原作 + 要**接着末章往后写新章节**（时间向前推） | `novel-continue` |
| 已有一段较短的文本，要**扩写章节内细节**（时间不动 / 加厚） | `novel-expand` |
| 已有长篇，要**压缩为短版 / 漫剧脚本量级** | `novel-condense` |
| 自己手写小说时要**工艺指南**，或先做**不进入正史的角色/场景/POV/声音/结构试写** | `novel-craft`（探索稿走 `exploration.py`，hash-bound 晋升也只生成候选） |
| 要补**生活观察 / 采访纪要 / 人物行为 / 场景五感 / 烟火气素材库** | `novel-observe` |
| 要建**正向审美样本库 / 拆解为什么这段好 / 高光场景标尺 / 精品化审美对照** | `novel-aesthetic` |
| 已有在建项目，要看**当前进度 / 全线看板 / 下一步该跑哪个 skill** | `novel-progress` |
| 已有在建项目，要**查看 / 修改 / 审计 `_设置.md` 选择点**（用途、平台、生成模式、AI 使用披露等） | `novel-settings` |
| 已有在建项目，novel skill 改版后要**判断是否需要返工 / 重审 / 重评** | `novel-update` |
| 已有在建项目，要**消除操作摩擦 / 找精准下一步指令 / 检查状态缺失** | `python3 skills/novel/scripts/flow.py "<作品根>"` |
| 已有在建项目，要**按 registry 做 workflow dry-run / 生成 runner 计划 / 判断 optional specialist agent 该接哪一步** | `python3 skills/novel/scripts/pipeline_runner.py "<作品根>" --write-plan`；长流程执行态用 `--start-run` / `--claim-stage` / `--complete-stage`；默认由独立代理复核 blueprint/setting 后用 `--approve-stage ... --delegated --agent delegate:... --reason ...` 留 hash-bound 批准，显式逐阶段人审项目不加 `--delegated` |
| 要把生产线跑成**一键代理闭环 / 自愈修稿（QA gate findings 自动回流重写）/ 派发 writer·reviewer·researcher specialist** | `novel-supervisor`（上层 agent 编排；普通可逆审阅默认 dispatch 给独立 specialist，高风险边界才 `needs_human`） |
| 已有在建项目，要看**生产控制台 / gate blockers / 修订任务 / 语义任务 / 队列状态 / release readiness** | `novel-dashboard`（只读聚合面板，写 `生产数据/novel_dashboard.*`，不改正文/进度） |
| 要把**多章节审稿、评分、dashboard 刷新、修订任务**排队给多个 worker 并发处理 | `novel-batch`（本地 flock 队列，claim/lease/reclaim/dead-letter，不直接执行模型） |
| 已有成品或准成品小说，准备交给视觉生产线前要**检查文本、权利、审稿、评分、AI 披露、改编潜力是否齐** | `python3 skills/novel/novel-craft/scripts/screen_adaptation_ready.py "<作品根>"` |
| 已写好若干章，要**质检 / 审稿 / 查问题**（人设崩 / 视角穿帮 / 设定矛盾 / 锚点漂移 / 题旨偏移 / 读者承诺违约 / 文学性变薄 / 节奏 / 原文照搬 / **五感缺失 / 伏笔逾期**） | `novel-review` |
| 已有审稿/评分/读者反馈后，要做**专业编辑 / 发展性编辑 / 行文编辑 / 拷贝编辑 / 校样 / 真实性或文化审读 / 投稿前精修计划** | `novel-edit`（分层编辑；真实性审读默认咨询，只有项目显式 required 才进发布硬闸） |
| 已写好若干章，要**打分 / 评分 / 市场体检**（题材够不够热、能不能火、值不值得继续写/改、要不要弃稿重立） | `novel-score` |
| 要写或审**专业、真实、行业感、别外行**的场景（医疗/法律/刑侦/金融/军事/历史/宗教/海外/科技/职业文），或商业投稿/出海/改编前要事实证据层 | `novel-research`（产 `资料/专业资料包_<主题>.md` + `research_sources.json` + `research_scene_usage.json`；写章包自动引用，review 查证据缺口） |
| **跑过 score、想据评分弱项直接开改写**（评分→改写串法） | `novel-rewrite --score-source 评分/score_report.json`（读 scores/verdict/deductions 预填 改动spec②，建议·待与用户要求对账） |
| 已写好若干章，要**查逻辑硬伤 / 维护设定百科 / 角色生死状态 / 伏笔回收 / 关系温度 / 知情账（谁知道什么秘密·掉马穿帮）** | `novel-wiki` |
| 已写好若干章，要用**合成读者视角找弃书点 / 可预测性假设**（不预测真实留存） | `novel-simulate` |
| 有平台后台、测试读者表单、评论导出，要**导入真实读者反馈 / 完读率 / 弃读点 / 评论掉点** | `novel-feedback` |
| 想要**提取授权样本/项目 Demo 的文风指纹 / 保持笔力一致 / 查文风漂移** | `novel-style` |
| 想要**分析情节节奏 / 画热力图 / 查注水 / 查断章** | `novel-balance` |
| 想要**宣发引流 / 写视频脚本 / 挖掘爆点章节** | `novel-promote` |
| 想要**出海 / 本地化 / 翻译成英文·东南亚等多语言版本** | `novel-localize` |

⚠️ **续 / 扩 / 视角 / 改 四者很容易混**：
- **续写** = 加**新章节**（时间向前推） → novel-continue
- **扩写** = 加**章节内细节**（时间不动 / 既有内容更厚） → novel-expand
- **视角续写** = **换 POV** 写同一段时间、**事件锁定不改** → novel-spinoff
- **改写** = **改主线 / 换设定 / 加原创材料**（事件可改、可新增设定，与视角续写正相反）→ novel-rewrite

⚠️ **QA 不是若干个对等裁决，而是「裁决 + 经验数据 + 分析仪」**（用户给“已写好的若干章 + 一个评估诉求”时按诉求**性质**分流）：

**裁决型（直接出结论，可入 gate）**
- **写得对不对**（人设崩/视角穿帮/设定矛盾/原文照搬/题旨偏移）→ `novel-review`（挑硬伤）
- **值不值得做 / 能不能火**（题材热度/爽点/留存/文学性 → 总分+判定+改写ROI）→ `novel-score`

**经验数据（真实行为，不和合成输出混权重）**
- **真实读者在哪里流失**（平台后台/内测表单/评论导出、完读率、弃读点）→ `novel-feedback`

**分析仪型（产出数据/台账，喂给上面的裁决，不单独当验收结论）**
- **从多种合成阅读视角找待验证的中断点/理解障碍/可预测性假设** → `novel-simulate`；只保留未校准表面分量与正文复核问题，不预测真实留存
- **逻辑/设定一致性 + 动态百科 + 伏笔台账**（角色生死、伏笔 planted→payoff 逾期、关系温度、设定自洽）→ `novel-wiki`。它是 `novel-review` 的一致性引擎（由 review 的 `consistency_audit.py` 一键串跑），也是 `设定/动态百科.json` 与 `设定/foreshadowing_ledger.json` 的权威存储。
- **节奏热力图**（注水、断章、高潮密集度）→ `novel-balance`；其「烂尾预警」读 `novel-wiki` 的伏笔台账回收率。

- 速记：问"能不能火/要不要继续写"=score；"哪里写崩了"=review；"哪些阅读中断/可预测性假设值得复核"=simulate；"真实读者在哪里流失"=feedback；"设定/伏笔有没有漏"=wiki；"节奏拖不拖"=balance。
- 串用顺序：先 score 定方向 → review 抠硬伤（自动调 wiki 查一致性/伏笔）→ balance 收节奏 → simulate 提出多视角正文复核假设；已有真实读者数据时先跑 `novel-feedback`，score 会优先读真实反馈。多份报告都跑过后，用 `novel-craft/scripts/revision_planner.py` 合并成统一修订计划 `修订/revision_plan.json`，避免各报告各自回流；该计划会被 `draft_packets.py`/`arc_packets.py` 读回，命中章/弧段的修订项自动注入下一轮写章包，闭环回流。
- 投稿/出版级精修：score/review/balance/feedback 都跑过后，再跑 `novel-edit` 生成分层编辑计划；结构级任务先改，行文级任务后改，校样最后做。
- 专业事实串用：先 `novel-research` 建资料包 → `novel-craft` 写章任务包自动引用 → `novel-review` 检查专业事实是否有证据支持；证据缺口回 `novel-research`，不要靠 prompt 记忆硬写。
- 生活质感串用：先 `novel-observe` 建观察素材库 → 写章/编辑时选素材注入任务包 → `novel-review`/`novel-edit` 检查人物是否仍悬浮。事实归 `novel-research`，生活细节归 `novel-observe`。
- 审美标尺串用：Demo 或授权/公版样本进 `novel-aesthetic` → `novel-style` 抽统计/语义风格 → `novel-edit` line packet 引用 transfer_rule → `novel-score` 品质向维度引用正向样本，避免只会扣分不会判断“好在哪里”。
- **score→rewrite 串法**：若 score 判 `小改/大改`（非 `弃稿重立`）且用户要据评分开改写，把报告喂给 `novel-rewrite --score-source 评分/score_report.json`——不与作者要求冲突的诊断按推荐方案并入新项目 `设定/改动spec.md` 的②栏；冲突时以作者要求为准。评分判 `弃稿重立` 会改变作品合同和主线方向，才停下确认是否走 `novel-create` 另起。改写后可回跑 score 做 before/after 对照。**写完一卷别只跑 review/score**：wiki（伏笔逾期）+ balance（节奏）+ simulate（可预测性/中断假设）是常被漏掉的三项，可自动串跑免费确定性检查。

⚠️ **"文风漂移"双触发仲裁**：提取/分析文风指纹、查笔力一致 → `novel-style`（文风是它的主责）；只有当诉求是"**作为质检项**报告某章偏离全书文风"且同时要查别的硬伤时，才并入 `novel-review`。单看文风一律走 style。

每条路由在输入足以区分动作时**直接调起对应 skill 并继续**；普通可逆歧义采用推荐路由。只有不同答案会改变作者意图、权利边界或作品合同时，才合并成一个最小澄清问题。不要在本 skill 里硬写小说。

## 决策树

0. **先看有没有在建项目**：用户指向（或当前正处于）某个 `创作区/写小说/<项目>/`，且其下有 `_进度.md` → **先读进度**：
   - **默认成书工作流**：先跑 `python3 skills/novel/novel-craft/scripts/author_workflow.py "<作品根>" --write`，拿到作者视角当前步骤、阻断项、警告和下一步命令；它不写正文、不改 `_进度.md`。
   - **进度路由**：跑 `python3 skills/novel/progress.py "<作品根>"` 找第一条未完成项（基于章节矩阵表）；也可调 `novel-progress` 查看全线看板。
   - **操作指挥 (Flow)**：若对下一步命令有疑虑、或想检查状态对账/就绪度，跑 `python3 skills/novel/scripts/flow.py "<作品根>"` 获取精准下一步指令。
   - **生产控制台 (Dashboard)**：若想汇总 pipeline/gate/语义任务/修订/队列/release 状态，跑 `python3 skills/novel/novel-dashboard/scripts/dashboard.py "<作品根>" --write --html`。
   - **确定性 Workflow runner**：若要让薄 agent 编排长流程，先跑 `python3 skills/novel/scripts/pipeline_runner.py "<作品根>" --write-plan`。它只读 registry、查输入/输出/gate、写 `生产数据/novel_pipeline_plan.{json,md}` 和 provenance；不写正文、不调用模型。需要恢复/追踪执行态时用 `--start-run` 创建 `生产数据/pipeline_runs/<run_id>.json`，再用 `--claim-stage` / `--complete-stage` / `--fail-stage` / `--block-stage` 更新阶段。`blueprint` / `setting` 即使已有初始化骨架也不会自动完成：默认由独立 specialist 复核后用 `--approve-stage <stage> --delegated --agent delegate:... --reason <说明>` 写 `审稿/stage_approvals.json`；显式逐阶段用户确认项目不加 `--delegated` 并提供具名人工 reviewer。批准同时绑定当前输入与产物 hash，任一侧改动后自动失效。
   - **批量队列 (Batch)**：若要多 worker 并发处理多章节 review/score 等任务，先用 `python3 skills/novel/novel-batch/scripts/queue.py plan "<作品根>" --kind review --chapters 1-10`，worker 再 `claim`，失败用 `reclaim`/`dead-letter` 处理。
   - **转制就绪**：若用户表示要继续做视觉生产/短剧/漫剧成片，先跑 `python3 skills/novel/novel-craft/scripts/screen_adaptation_ready.py "<作品根>"`；只检查小说侧条件，不替视觉生产线生成资产或镜头结构。
   - **准入检查 (Gate)**：在进入 `drafting` (写正文)、`review`/`score` 或 `export` 前，跑 `python3 skills/novel/novel-gate.py <作品根> --stage <阶段>`；该入口统一调用 novel QA gate。`drafting` 只查写作前置物，不要求既有 `score_report`；`review`/`score` 要求本章 `state_delta` 已合并进 `state_ledger`，且动态百科分级新鲜度达标（滞后 ≥3 章、或整个缺失且正文已 ≥5 章 → 阻断；轻度滞后仅提醒——百科是审稿的一致性引擎，不能拿过期事实索引审新章）；`export` 覆盖 rights/research/review/score/state closure/AI usage/compliance profile，并在商业/平台/出海/KDP/中国公开发布等目标要求 AI 使用披露、专业资料包和平台/辖区清单闭环。
   - **文本主创模式**：投稿/发布前 gate 会读取 `_设置.md` 的 `文本主创模式` 与 `合规/ai_usage.json`。晋江/起点/番茄/红果等中文网文平台目标下，`AI生成` 正文会阻断，除非补 `合规/platform_ai_evidence.json`（当日平台规则证据）并写入作用域匹配的 `ai_generated_text_platform_exception` 豁免；推荐走 `人类主创` 或 `AI辅助`。
   - **写后自动化**：每写完一章，先填 `审稿/state_delta_第NN章.json` 和对账结论 `审稿/state_verify_第NN章.json`，再跑 `python3 skills/novel/scripts/post_write.py <作品根> --chapter 第NN章 --conclusion <作品根>/审稿/state_verify_第NN章.json`；该入口会先过状态对账/百科/逻辑/力量体系机检，全部硬闸通过并合并状态账本后才自动勾选进度。若 `_设置.md` 选 `小说生成工作流：边写边自检`，`draft_packets.py` 会把这套闭环自动写进每章任务包，`flow.py` 也会把执行命令作为下一步提示；同时按 `小批回扫间隔`（默认 5 章，可改 3 章/关闭）保留 novel-review 的文风、节奏、钩子、人设、读者承诺集中修正；全书 40-60% 进度带自动按半间隔加密回扫（**中段防守**：长篇一致性实证的矛盾高发区；due 点单一真值源 `novel/_lib/sweep_schedule.py`）。逐章情绪/张力实测（`设定/emotional_progression.json`）由 `post_write.py` 在逻辑哨兵前自动回填（tone_check --write-progression，advisory 不阻断）——`logic_sentry` 的"连续 N 章张力塌陷"节奏预警因此每章都有最新曲线可用；回扫窗口无需再手跑，除非项目未走 post_write 闭环。
   - **标准化旧项目**：若 `_进度.md` 格式陈旧，跑 `python3 skills/novel/scripts/standardize_progress.py <作品根>` 迁移到标准矩阵。
   - 仅当 `_进度.md` 显示已全部完成、或用户明确要开新动作时，才往下走 1-5。
1. 用户给了**本地 .txt/.md/.docx、目录、file:// 或 URL**，且意图是"拖进来/导入/先建作品/纳管源书"，或没说具体动作 → 先跑 `python3 skills/novel/scripts/import_novel.py "<路径或URL>"` 建 `创作区/写小说/<书名>/`。
2. 用户给了**本地文件路径** + 明确动作（续写XX视角 / 起书名 / 扩 / 缩 / 漫剧改编）→ 直接按动作路由。
3. 用户给了**书名 / 作者 / 公版目录 URL**，明确说"抓回来/下载公版/联网取书" → `novel-fetch`。
4. 用户的输入是**只言片语 / 一个想法 / 一点风格 / 零散碎片**，要写一本**原创新书**（没有成型源文）→ `novel-create`（它会用访谈把碎片补全成蓝图，**别在这里反问"给我个文件"**）。
5. 用户给了**碎片 + 已有半成品/笔记文件**，要继续往成书走 → 也走 `novel-create`，用 `--ingest` 把碎片吃进 `素材/`。

## 拖入小说 / 链接建档

当用户说"从任何地方拖进来一本小说"、只给一个路径/URL、或只是要先把源书收进仓库时，不要问"要做什么"。先导入建档：

```bash
python3 skills/novel/scripts/import_novel.py "<路径或URL>"
```

脚本行为：
- 自动从文件名、URL、HTML title 或正文首行推断书名，落到 `创作区/写小说/<书名>/`。
- 写入 `原作.txt`、`小说/<书名>.txt`、可用时写 `小说/<书名>.docx`、`小说/source_manifest.json`、`_meta.json`、`_设置.md`、`_进度.md`。
- `_meta.json` 含作品卡片字段 `synopsis`（导入型作品无 premise，留空待后续回填，不阻断纳管）与 `cover`（纯文本线无图片产物，恒为 `null`，桌面卡片自动用产线图标占位）。
- `_进度.md` 使用 import 阶段表，`novel-progress` 与 `flow.py` 能直接读出下一步，不再把导入项目误判为普通章节矩阵。
- 本地 `.txt/.md/.docx` 可直接纳管；通用 URL 必须加 `--i-have-rights`，Project Gutenberg / Wikisource 自动记为 `public-domain`，但只写入来源侧公版依据和辖区提示；跨地区发行或商用前必须补 `--distribution-regions`/权利复核；已知付费墙站拒抓。
- 如果目标作品已存在，交互环境会提示 `新建版本 / 覆盖 / 使用现有 / 取消`。非交互环境不会自动覆盖，必须显式传：

```bash
python3 skills/novel/scripts/import_novel.py "<路径或URL>" --on-exists new-version
python3 skills/novel/scripts/import_novel.py "<路径或URL>" --on-exists overwrite --force
python3 skills/novel/scripts/import_novel.py "<路径或URL>" --on-exists use-existing
```

## 何时不路由

- 用户在写**完全原创**小说（无源文本）→ 路由到 `novel-create`（它有访谈立项 + 蓝图/设定/章纲/Demo/进度跟踪的引导流程）。**只有**用户明确只想"随手聊两句、不要立项不要建项目"时，才不走 skill、直接帮写。

## 合法性继承（铁律）

novel-* 家族的合法性规则一致：**公版 / 自有 / 用户声明授权（`--i-have-rights`）**，并且公版必须记录辖区。

- 命中付费墙站或当代受版权网文，本 skill **拒绝路由** novel-spinoff / novel-rewrite / novel-expand / novel-condense（这些都会派生作品）。
- 仅当 `novel-fetch` 用来取公版书、或 `novel-title` 用来起原创书名时，才可对原作版权状态宽松。
- `public-domain` 不是“全球自动可商用”。`source_manifest.json/_meta.json` 会记录 `rights_jurisdiction`、`rights_covered_regions`、`distribution_regions`、`source_license_url`；导出合本或商业项目前，QA gate 会阻断发行地区未写或不被来源辖区覆盖的公版素材。
- 路由前先做一次铁律筛查；命中即拒做并解释为什么。

## 持续改进（meta-capability）

novel 同时承担 novel-* 家族的**经验累积**职责。在跑任何 novel-* 流水线的过程中，遇到以下**信号**时及时把发现写进对应文件：

### 触发信号

- **用户明确反馈**："这点不错"/"这样写就对了"/"以后都这样"/"不要那样，要这样"
- **自检反复出现的弱点**：同一类问题在两章 Demo 里都出现 → 升格为 skill 守则
- **用户重复问同一个问题**：可能跨项目都会问 → 升格为 Q&A
- **跨 skill 的判断模式**：例如"用什么标准甄别主角 vs 配角"、"原作太大锚点怎么精筛"

### 写到哪里

| 发现类型 | 写到 |
|---|---|
| 单 skill 的工艺细节 | 该 skill 的 `references/<相关>.md` |
| 单章写作守则 | `novel-craft/references/chapter.md` |
| 章纲编织模式 | `novel-craft/references/outline.md` |
| 扩 / 续 / 缩 的特定工艺 | `novel-craft/references/{expand,continue,condense}.md` |
| 路由判断模式（哪个 skill 适合哪种输入） | `novel/SKILL.md` 路由表 |
| 跨 skill 的 Q&A / 判断标准 | `novel/Q&A.md` |
| 项目特有的设定 / 角色口吻 | 项目本地的 `设定/角色卡.md`，**不写进 skill** |

### 节奏

- 不要每条都写——**只有清晰、可重用、跨场景适用**的才写。
- 用户明确叫停"别写"时不写。
- 写之前可以确认一次（"我想把这条加进 <文件>，要不要？"）；auto mode 下可以更主动，但优先选 `Q&A.md` 这个低风险落点。

### 反模式

- 把项目特有细节误写进 skill references（如某项目角色卡里的具体设定）。
- 在 SKILL.md 末尾堆 changelog——经验整合到正文，不要 changelog。
- 写进 skill 后不更新该 skill 的"常见错误"表，造成经验孤岛。
- 同一条经验在两个 skill 里写两份——应合并到 `novel-craft/` 后引用。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 任意模糊都停下来问 | 可逆歧义采用最有证据的推荐路由；只有会改变作者意图、权利边界或作品合同的真歧义才问一个最小问题 |
| 跳过合法性筛查 | 路由前必须查；本 skill 的最大职责就是把铁律前置 |
| 在本 skill 里直接开始写 | 不写；路由出去 |
