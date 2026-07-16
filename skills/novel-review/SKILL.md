---
name: novel-review
description: 小说质检 + 流程自审（novel-* 家族的 QA 环节，不写作只审）。双模——模式①「作品质检」：审 ALREADY-WRITTEN 章节（.md/.txt）——POV slips(串视角/视角穿帮)、OOC/人设崩、plot holes、anchor & timeline drift、设定矛盾、读者契约兑现、弧段跑偏、**专业事实证据支持(医疗/法律/刑侦/金融/军事/历史/宗教/海外/科技/职业文是否有 novel-research 资料包)**、**力量体系一致性(穿越/系统流的等级·成长值·战力只增不减、未知境界、越级过快、面板属性≤7、系统流久无升级桥段)**、节奏/缺钩子、文风漂移、原文照搬、微短剧/漫剧源书平台合规预检——机检+人判，出严重度分级·定位到章/段的报告；续写/外传交叉核对 设定/(角色卡·世界观·锚点表·章纲) 与 原作。`consistency_audit.py` 含 `research_fact_support` / `power_system` 子runner；`platform_compliance.py` 做小说侧微短剧合规预检。模式②「流程自审」：联网拉当前小说/网文市场基准，对照 novel-* 各 skill + novel-craft + Q&A，产出"差距清单 + 该改哪个 skill 哪段"的优化建议。Does NOT write/continue the story. Triggers 审稿, 质检, 检查小说质量, 查人设崩, 视角穿帮, 串视角, 设定矛盾, 专业事实, 行业感, 别外行, 读者契约, 弧段 gate, 长篇跑偏, 锚点对齐, 一致性回扫, 伏笔回收, 微短剧合规, 平台合规, 力量体系自检, 等级一致性, 战力崩坏, 升级数值, 节奏, 文风漂移, 原文照搬, 质量报告, 流程自审, 流程优化, 自我优化, novel 还能优化啥, novel review, QA.
---

# novel-review — 小说质检 + 流程自审

不写、不续小说，只**审**。是 novel-* 家族的 QA 环节。两个模式：

- **模式①「作品质检」**——审**已写的章节**：扫出问题 → 定位（章 + 行/段）→ 定级 → 给可执行修法 → 产出审稿报告。把 `novel-spinoff` 第 7 步回扫 + Demo 自检清单**通用化、独立化**。
- **模式②「流程自审」**——审**写小说流水线本身**：联网拉市场基准，对照 novel-* 各 skill + novel-craft + 累积 Q&A，产出"差距清单 + 建议改哪个 skill 哪段"。让"整条创作线不断自我优化"成为可复跑命令。

---

# 模式①：作品质检

## 机检 / 人判分工

- **机检（确定性，先跑）**：一键串跑用 `scripts/consistency_audit.py <作品根> [--pov 角色名] [--anchor 设定/风格指纹.json]`，它把家族里全部确定性检测器（基础三件 + 2026 新增子检测器，共 14+ 个，见下）一次跑完并汇总到 `审稿/consistency_audit.json`：
  - `scripts/mechanical_check.py` —— 格式/字数带宽（默认读 `_meta.target_wordcount_min_max` / scale / target_words_per_chapter，可用 `--min/--max` 覆盖）/章号与章纲对齐/视角"我"密度提示/称谓·术语漂移/**原文照搬（n-gram vs 原作.txt）**/**AI腔·同质化启发式**（叙事中议论文式连接词=🟡·万能金句套话密度=🟢·advisory·线索非定论，`--no-ai-tell` 关闭；平台 AI 质检阈值属于易变信息，具体要求以 `novel-research` 平台资料包/`market_baseline` 为准；写作链路全程 AI 起草时，此项仍应作为过审风险前置自检）/**跨章重复率·机械文风**（相邻章字级 shingle Jaccard 近重复=🟡/🟢·跨章机械开篇=🟡·跨章整句逐字复用=🟡·句首词/短句式模板=🟢/🟡·全书/每章 zlib 压缩比=🟢·advisory·绝不 🔴·`--no-repetition` 关闭；对标番茄/红果对 AI 内容「连续章节重复率+机械化文风」的双重质检，阈值为内部启发式非平台公开硬数字；系统面板等刻意模板会命中，交人判）。术语**权威源优先**：人确认的 `设定/角色别名.json`（status=confirmed，由 `novel-wiki/alias_scaffold.py` 生成候选+人确认）里的规范名/别名直接采信（绕过正则启发式，含中点/单字/带「的之」的合法专名也不漏），其余从 `设定/设定圣经.md`、`角色卡.md`、`世界观.md`、`锚点表.json` 正则抽取补充，也可用 `--terms` 追加（`--no-auto-terms` 关闭确认表+正则两路自动抽取）。
  - `novel-wiki/logic_sentry.py`（先 `wiki_builder.py` 建《动态百科》）—— **死人复活 / 弃置道具复用 / 位置跳变 / 数值漂移（年龄锚点跨章不一致）**等硬冲突候选 → `审稿/logic_alerts_*.json`。这是把"设定自相矛盾/锚点漂移"从纯人判下沉到机检的深度增强（无角色卡/无年龄锚点则优雅跳过并记原因）。**审查重点章排序（ConStory arXiv 2603.05890）**：`logic_alerts_summary.json` 里 alerts 按 `priority` 降序（中段40-60% + 高 churn + 高字符熵章加权·`priority_factors` 标命中代理），并给 `review_focus_chapters` 热点表——把人工语义复审火力先投到最可能藏 bug 的章。**只排序不改 severity/blocking**（B10）。
  - `novel-style/extract_style.py --compare` —— 每章文风指纹 vs **锚点章指纹**算漂移分，超带宽即记"文风漂移"候选 → `审稿/style_drift_summary.json`（无锚点指纹则跳过，提示先提取）。
  - **2026 新增 9 个子检测器（一键串跑或按需跑，各自缺输入优雅跳过）**：① **断章钩子**(`hook_endings.py`)逐章末尾打钩子分、黄金三章更严(建议级)；② **角色语感**(`voice_drift.py`)口头禅消失/句长漂(读 `设定/角色语感.json`·建议级)；③ **情绪曲线**(`tone_check.py`)实测每章主导情绪 vs `设定/tone_curve.json` 目标弧(建议级)；④ **支线收口**(`thread_resolution.py`)open_threads 超期(建议级)、`--finale` 卷末/书末未收支线=阻断级烂尾防线；⑤ **反派战力**(`antagonist_scaling.py`)反向战力崩坏(建议级·需 registry 标 role/阵营)；⑥ **时间线**(`timeline_check.py`)年份倒流(建议级)+ `设定/timeline.json` 事件乱序(阻断级)；⑦ **配角连续性**(`minor_characters.py`)反复出场却未建卡(建议级)；⑧ **逐章读者契约**(`reader_contract_sentry.py`)阻断缺 `reader_contract_progress` / `theme_alignment` 的章节；⑨ **弧段 gate**(`arc_gate.py`)检查连续 3 章不推进契约、整段无题旨对齐、长窗口只种不收；⑩ **套路探测**(`trope_cliche.py`·想象力侧)扫创作蓝图/前提/首章开局命中的高频网文套路（系统绑定/赘婿/战神归来/重生复仇/废物觉醒/霸总契约/穿越退婚 等，多词 AND 高精度·建议级），已在「差异化决策/forbidden_tropes」点名的降为"已自觉"——补"只有行文级 AI 腔、没有情节/前提级套路探测"的洞，配套发散工艺见 `novel-craft/references/premise-divergence.md`。另：伏笔台账新增**终章未击发反查**（`foreshadow_ledger`：抵达 target_chapters 仍未回收的已确认伏笔=契诃夫之枪没击发，high/critical 阻断级），补 is_overdue 只抓"设了回收章又越窗"、抓不到"埋了却从没设回收章"的洞。另：`logic_sentry` 已通电的 **world_rule_violation(阻断级)/relationship_flip/钩子过期/承诺违约(阻断级)/张力疲劳/character_guardrails** 也随 `run_logic` 在 review 汇总（已传 project_root）。
  - **微短剧/漫剧源书平台合规预检**（小说侧）：当 `_设置.md` / `_meta.json` 命中 `微短剧/短剧/漫剧/红果/抖音`，先跑
    `python3 skills/novel-review/scripts/platform_compliance.py <作品根>`。
    它按最新广电公开要求做标题/正文关键词预检与上线前许可证/备案待办提示：片名不得恶俗恶趣味或渲染极端复仇暴戾焦虑；文本中色情低俗、血腥暴力、未成年人敏感、政治安全等明显风险可阻断。**经典 IP 复核**（广电2026-04新规）：`rights_status=public-domain` 或 `_meta.classic_ip_adaptation=true` 的源书在漫剧/微短剧目标下会 warn `classic_ip_alteration_review`——提示改编环节须复核「不得颠覆性魔改经典作品/英雄/历史人物形象、真人肖像须授权、按投资额三级备案、AI 内容片头标识」（judgment call·人判不硬阻断；该标记由 novel-rewrite/novel-spinoff init 写入 `_meta`，随交付契约传给改编环节）。产物 `审稿/platform_compliance.json` 只是小说侧预检，不替代平台审核、法律意见或成片报审。
  - **专业事实证据支持**：`consistency_audit.py` 会调用 `novel-research/scripts/research_pack.py check`，检测医疗/法律/刑侦/金融/军事/历史/宗教/海外/科技/职业文等高风险关键词是否有适用 `ready` 资料包；来源缺日期/可信度、事实未绑定来源、资料过期都会写入 `审稿/research_fact_support.json`，并在汇总报告里回流到 `novel-research`。`novel-craft` QA gate 会在 review/export 前读取同一索引，高风险资料包过期或缺 `updated_at` 会直接 blocking；全库刷新用 `research_pack.py refresh-audit "创作区/写小说"` 生成 `资料/research_refresh_plan.md`。
  缺输入的检测器一律**跳过并落原因**，不静默略过冒充全覆盖。
- **人判（LLM 判断题）**：机检覆盖不了的——视角穿帮、OOC、情节漏洞、锚点语义对齐、**题旨契约 / 读者承诺兑现**、节奏（爽点/钩子/反转）、伏笔回收、留白、文风漂移、文学质感、show-don't-tell、过度直白。维度逐条见 `references/checklist.md`。机检产出的 `logic_alerts`/`style_drift` 候选是**线索不是定论**（带 `auto` 标志），仍需人判结合语境确认（容错铁律：宁缺毋滥，闪回/伏笔可豁免）。

## 工作流

0. **定位项目**：作品根需含 `章节/*.md`（理想还有 `设定/`、`原作.txt`、`设定/章纲.md`）。先读 `_进度.md` 和 `审稿/demo_gate.json`（如存在）；确认三件事：① POV 角色 + 人称（如"王敦/第三人称限定"）② 文风锚点章（优先 `demo_gate.style_anchor.source_chapter`）③ 是否续写/外传（是 → 需锚点对齐 + 原文照搬检查）。
1. **跑机检脚本** → 确定性问题清单；同时落盘机器结果。一次跑全套：
   `python3 skills/novel-review/scripts/consistency_audit.py <作品根> [--pov 角色名] [--anchor 设定/风格指纹.json]`（内部串跑 mechanical_check + reader_contract_sentry + logic_sentry + style-drift + hook/voice/tone/thread/antagonist/timeline/minor/arc_gate/foreshadow/power_system 等全部子检测器，汇总 `审稿/consistency_audit.json`）。
   只想跑基础机检也可单独：`python3 skills/novel-review/scripts/mechanical_check.py <作品根> ... --json-out 审稿/mechanical_findings.json`。
   长篇逐章写后由 `novel/scripts/post_write.py` 自动调用 `reader_contract_sentry.py`；对已写窗口或历史项目，可手动跑：
   `python3 skills/novel-review/scripts/reader_contract_sentry.py <作品根> --chapter 第NN章`。
   每 3-5 章或自然 arc 写完后跑：
   `python3 skills/novel-review/scripts/arc_gate.py <作品根> --arc 1-5`。
   微短剧/漫剧源书或目标平台含红果/抖音时，同时跑：
   `python3 skills/novel-review/scripts/platform_compliance.py <作品根>`。
2. **分 arc 人判**：章多时**每个 arc 拆给子任务/子代理**审（省主上下文），每章对照 `references/checklist.md` 维度，**只记真问题**，每条带原文引文证据。
3. **汇总报告** → 先用汇总器把机检 + 一致性审计 + 人判 JSON 转成调度器可消费的报告：
   `python3 skills/novel-review/scripts/build_review_report.py <作品根> [--human-assessment 审稿/human_findings.json]`。
   默认缺少 `审稿/mechanical_findings.json` 会失败；只有人工明确只做纯人判报告时才加 `--allow-missing-mechanical`，且报告必须在 `waivers[]` 和 Markdown「显式豁免」中记录 `missing_mechanical`，不能伪装成正常全量通过。
   若存在 `审稿/consistency_audit.json`，汇总器会自动把 `logic_sentry` / `style_drift` / `power_system` 的阻断或建议级结果提升进 `review_report.findings`；不要只跑一致性审计却不让导出 gate 看见。
   该脚本会写两份产物：
   - `审稿/审稿报告.md`：给人读，按严重度排序，每条 = 位置（第N章·第X段）+ 维度 + 问题 + **建议修法** + 证据引文。附"健康度概览"表（各维度通过/问题数）。
   - `审稿/review_report.json`：给调度器读，遵守 `novel-craft/references/qa-report-schema.md`，必须带 `source_snapshot` 绑定当前 `章节/` 全量 hash；每条问题必须带 `recommended_skill`、`return_to_stage`、`affected_files`、`blocking`；所有显式豁免必须进 `waivers[]`。
4. **（可选 `--fix`）**：只就地做**润色级**小改；**阻断/建议级只报不自动改**，交作者定夺。

## 严重度（定级 + 容错铁律）

| 级别 | 含 | 处置 |
|---|---|---|
| 🔴 阻断级 | 视角穿帮/串视角、OOC 人设崩、主线 arc 明显偏离读者契约、锚点错位、设定自相矛盾、原文大段照搬、漫剧档章末无钩子、情节硬伤 | **必改**，只报不自动改 |
| 🟡 建议级 | 节奏拖/爽点弱、题旨推进不足、读者承诺长期无递进、伏笔未回收、信息密度低、留白未填、配角脸谱化、文学质感薄 | 建议改 |
| 🟢 润色级 | 用词重复、个别过度直白、标点/错别字 | 可改可不改，`--fix` 可自动 |

**容错铁律**：只报"真问题"。轻微主观偏好（"我会换个词"）**不入报告**——否则噪声淹没硬伤。

> **修法回哪个 skill**：每条阻断/建议级修法都指明回源头重跑——OOC/设定矛盾→回 `novel-rewrite`/`novel-create` 改设定圣经再回扫；锚点漂移→对 `novel-spinoff` 锚点表；节奏塌/钩子弱→回写章纲（`novel-craft/references/outline.md`）；原文照搬→回对应派生 skill 重写该章。审已写章节、**未到的阶段不当问题报**（先读 `_进度.md`）。

### 审稿模型分离（2026-06-25 P2-⑪）

**为什么要分离**：行业最佳实践（autonovel/Novel-OS）一致指出同一模型既写作又审稿会产生"self-congratulation bias"——AI 对自己生成的文本更宽容，漏报率显著高于不同模型交叉验证。

**推荐配置**：
- **写作（生成）**：Claude Opus / Sonnet（主模型）
- **审稿（判断）**：DeepSeek（独立 reviewer）——已有接入 `claude-ds` / `claude-ds-think`，Key 在 keychain；DeepSeek `/anthropic` 是原生协议无需额外 router。详见 `CLAUDE.md` → [[deepseek-fallback-claude-code]]。
- **模拟试读（novel-simulate）**：DeepSeek（与写作模型不同，提供真实的"他者视角"）
- **评分（novel-score 维度判断）**：建议也走 DeepSeek，尤其是 `prose` 维度（AI 对自己写的 prose 最容易给高分）
- **机检（确定性）**：不涉及 LLM，无需分离（`mechanical_check.py` / `consistency_audit.py` / `arc_gate.py` 等纯脚本）

**使用方式**：审稿时用 `/model claude-ds` 切换到 DeepSeek，再跑 review 的人判部分。或把 review 的人判 prompt 发到 DeepSeek 线程。理想流程：机检（本地脚本）→ 人判（DeepSeek）→ 汇总（本地 `build_review_report.py`）→ 修正（切成 Claude 写）。

如果只有一个模型可用：至少用高 temperature（0.7-0.9）跑 review、低 temperature（0.2-0.4）跑写作——温差本身能提供部分交叉验证效果。

---

# 模式②：流程自审（让写小说产线自我优化）

把"人工复盘整条 novel 线"固化成可复跑流程。**节律**：用户主动要 / 写完一批书后 / 接了新写作工艺·新平台套路时跑一次。详细步骤见 `references/self_audit.md`，要点：

1. **先跑本地静态治理检查**：`python3 skills/novel-review/scripts/self_audit.py [--project-root "<作品根>"]`。它不联网、不改文件，检查 registry/README/author 路由同步、`_进度.md` 写入口、`state_ledger` 原子写、批量写章队列、市场基准新鲜度，并**摄入生产线埋点**——`<作品根>/生产数据/优化信号.jsonl`（`novel/_lib/friction_log.py`，由 `novel-score` 等阶段在遇到豁免/覆盖缺口/低判定等摩擦时写入）里所有 open 信号翻成 `FRICTION-*` finding，让"生产时遇到的摩擦"自动进自审差距清单，无需用户重述就能持续触发自我优化。处理掉一条后用 `friction_log.resolve_signals` 标 resolved 即不再复现。
2. **拉基准**：联网搜当前（带年月）网文/小说主流做法，分三轴取证——**题材/市场契合**（红果/番茄/晋江/抖音当下热题材与套路，复用 `novel-score/scripts/collect_market_baseline.py` 的热榜拉取）、**写作工艺**（黄金三章钩子、爽点密度、章纲编织、单章守则 vs `novel-craft/references/*`）、**一致性/合规来源**（设定圣经/锚点一致性方法、公版/授权来源边界 vs fetch/spinoff/rewrite 的合规闸门）+ 各能力演进。
3. **对照**：逐 skill 把基准 vs `novel-*/SKILL.md` + `novel-craft` + `novel/Q&A.md` 比，找**真差距**（已做的别重复立项，标"✅ 已覆盖"一行带过）。
4. **差距清单**：每条 = 差距 + 证据（带来源链接·日期）+ 落到哪个 skill 哪段 + 优先级（must/optional）+ 是否可脚本化（是→能进 `mechanical_check.py`）。
5. **起草**：高价值项起草建议 edit；**改任何 skill 必同步 `skills/README.md` 索引**（仓库硬约定）。
6. **人确认后再写**：模式②**默认只产建议报告**，不自动改 skill。**报告是一次性的——只讲给用户、不在 skill 目录留存 `_流程自审_*.md` 这类存档**（已 gitignore）。**每次自审/重审都从头按本流程重跑**（拉基准→对照→差距），**绝不读旧报告当捷径**——市场会变，旧结论可能已过时或已落地。

> **防过期铁律**：市场建议带"采集日期 + 来源链接"，旧建议可能已被采纳或过时——写进来前先核对当前 skill 是否已有。与 `novel-score` 共用 `novel-score/references/market-baseline.md` 和 `scripts/collect_market_baseline.py`，避免两处各拉一份。

---

## 详细参考
- 一键机检 runner：`scripts/consistency_audit.py`（串跑 mechanical + `novel-wiki/logic_sentry` + `novel-style` 漂移）
- 流程自审本地治理检查：`scripts/self_audit.py`（registry / 进度写入 / 账本原子写 / draft queue / market baseline freshness / 生产摩擦埋点摄入 `生产数据/优化信号.jsonl`）
- 逻辑硬冲突机检：`novel-wiki`（动态百科 + 哨兵）；文风漂移机检：`novel-style`（指纹 + `--compare`）
- 两层质检维度全清单（看什么 + ✅/❌ + 定级）：`references/checklist.md`
- 正向标准（单章该长啥样）：`novel-craft/references/chapter.md`
- 锚点/视角规则（外传）：`novel-spinoff/references/timeline-anchoring.md` + `pov-craft.md`
- 机器报告 schema：`novel-craft/references/qa-report-schema.md`
- Demo gate 对照：`novel-craft/references/demo-gate.md`

## 常见错误

| 错误 | 纠正 |
|---|---|
| 只跑脚本不做人判 | 机检只覆盖确定性问题；OOC/节奏/锚点语义要 LLM 判 |
| 只人判不跑脚本 | 原文照搬/字数/钩子缺失这类机检秒查，漏跑等于白审 |
| 鸡蛋里挑骨头堆一堆润色项 | 违容错铁律；硬伤被噪声淹没 |
| 报问题不定位不给修法 | 必须 章+段定位 + 可执行建议（业界：把模糊意见变 actionable） |
| 阻断级自动改 | 阻断级（人设/情节/锚点）只报，交作者；自动只碰润色级 |
| 续写项目跳过锚点对齐 | 外传/续写必查与 `锚点表`/`原作` 的事件骨架是否一致 |
