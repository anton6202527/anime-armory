---
name: novel-review
description: 小说质检 + 流程自审（novel-* 家族的 QA 环节，不写作只审，与 n2d-review/mv-review/song-review 同构）。双模——模式①「作品质检」：审 ALREADY-WRITTEN 章节（.md/.txt）——POV slips(串视角/视角穿帮)、OOC/人设崩、plot holes、anchor & timeline drift、设定矛盾、节奏/缺钩子、文风漂移、原文照搬——机检+人判，出严重度分级·定位到章/段的报告；续写/外传交叉核对 设定/(角色卡·世界观·锚点表·章纲) 与 原作。模式②「流程自审」：联网拉当前小说/网文市场基准，对照 novel-* 各 skill + novel-craft + Q&A，产出"差距清单 + 该改哪个 skill 哪段"的优化建议。Does NOT write/continue the story. Triggers 审稿, 质检, 检查小说质量, 查人设崩, 视角穿帮, 串视角, 设定矛盾, 锚点对齐, 一致性回扫, 伏笔回收, 节奏, 文风漂移, 原文照搬, 质量报告, 流程自审, 流程优化, 自我优化, novel 还能优化啥, novel review, QA.
---

# novel-review — 小说质检 + 流程自审

不写、不续小说，只**审**。是 novel-* 家族的 QA 环节，与 `n2d-review`/`mv-review`/`song-review` 同构。两个模式：

- **模式①「作品质检」**——审**已写的章节**：扫出问题 → 定位（章 + 行/段）→ 定级 → 给可执行修法 → 产出审稿报告。把 `novel-spinoff` 第 7 步回扫 + Demo 自检清单**通用化、独立化**。
- **模式②「流程自审」**——审**写小说流水线本身**：联网拉市场基准，对照 novel-* 各 skill + novel-craft + 累积 Q&A，产出"差距清单 + 建议改哪个 skill 哪段"。让"整条创作线不断自我优化"成为可复跑命令。

---

# 模式①：作品质检

## 机检 / 人判分工

- **机检（确定性，先跑）**：一键串跑用 `scripts/consistency_audit.py <作品根> [--pov 角色名] [--anchor 设定/风格指纹.json]`，它把家族里三个确定性检测器一次跑完并汇总到 `审稿/consistency_audit.json`：
  - `scripts/mechanical_check.py` —— 格式/字数带宽/章号与章纲对齐/视角"我"密度提示/称谓·术语漂移/**原文照搬（n-gram vs 原作.txt）**。术语默认从 `设定/设定圣经.md`、`角色卡.md`、`世界观.md`、`锚点表.json` 自动抽取，也可用 `--terms` 追加。
  - `novel-wiki/logic_sentry.py`（先 `wiki_builder.py` 建《动态百科》）—— **死人复活 / 弃置道具复用 / 位置跳变**等硬冲突候选 → `审稿/logic_alerts_*.json`。这是把"设定自相矛盾/锚点漂移"从纯人判下沉到机检的深度增强（无角色卡则优雅跳过并记原因）。
  - `novel-style/extract_style.py --compare` —— 每章文风指纹 vs **锚点章指纹**算漂移分，超带宽即记"文风漂移"候选 → `审稿/style_drift_summary.json`（无锚点指纹则跳过，提示先提取）。
  缺输入的检测器一律**跳过并落原因**，不静默略过冒充全覆盖。
- **人判（LLM 判断题）**：机检覆盖不了的——视角穿帮、OOC、情节漏洞、锚点语义对齐、节奏（爽点/钩子/反转）、伏笔回收、留白、文风漂移、show-don't-tell、过度直白。维度逐条见 `references/checklist.md`。机检产出的 `logic_alerts`/`style_drift` 候选是**线索不是定论**（带 `auto` 标志），仍需人判结合语境确认（容错铁律：宁缺毋滥，闪回/伏笔可豁免）。

## 工作流

0. **定位项目**：作品根需含 `章节/*.md`（理想还有 `设定/`、`原作.txt`、`设定/章纲.md`）。先读 `_进度.md` 和 `审稿/demo_gate.json`（如存在）；确认三件事：① POV 角色 + 人称（如"王敦/第三人称限定"）② 文风锚点章（优先 `demo_gate.style_anchor.source_chapter`）③ 是否续写/外传（是 → 需锚点对齐 + 原文照搬检查）。
1. **跑机检脚本** → 确定性问题清单；同时落盘机器结果。一次跑全套：
   `python3 skills/novel-review/scripts/consistency_audit.py <作品根> [--pov 角色名] [--anchor 设定/风格指纹.json]`（内部串跑 mechanical_check + logic_sentry + style-drift，汇总 `审稿/consistency_audit.json`）。
   只想跑基础机检也可单独：`python3 skills/novel-review/scripts/mechanical_check.py <作品根> ... --json-out 审稿/mechanical_findings.json`。
2. **分 arc 人判**：章多时**每个 arc 拆给子任务/子代理**审（省主上下文），每章对照 `references/checklist.md` 维度，**只记真问题**，每条带原文引文证据。
3. **汇总报告** → 先用汇总器把机检 + 人判 JSON 转成调度器可消费的报告：
   `python3 skills/novel-review/scripts/build_review_report.py <作品根> [--human-assessment 审稿/human_findings.json]`。
   默认缺少 `审稿/mechanical_findings.json` 会失败；只有人工明确只做纯人判报告时才加 `--allow-missing-mechanical`，且报告必须在 `waivers[]` 和 Markdown「显式豁免」中记录 `missing_mechanical`，不能伪装成正常全量通过。
   该脚本会写两份产物：
   - `审稿/审稿报告.md`：给人读，按严重度排序，每条 = 位置（第N章·第X段）+ 维度 + 问题 + **建议修法** + 证据引文。附"健康度概览"表（各维度通过/问题数）。
   - `审稿/review_report.json`：给调度器读，遵守 `novel-craft/references/qa-report-schema.md`，必须带 `source_snapshot` 绑定当前 `章节/` 全量 hash；每条问题必须带 `recommended_skill`、`return_to_stage`、`affected_files`、`blocking`；所有显式豁免必须进 `waivers[]`。
4. **（可选 `--fix`）**：只就地做**润色级**小改；**阻断/建议级只报不自动改**，交作者定夺。

## 严重度（定级 + 容错铁律）

| 级别 | 含 | 处置 |
|---|---|---|
| 🔴 阻断级 | 视角穿帮/串视角、OOC 人设崩、锚点错位、设定自相矛盾、原文大段照搬、漫剧档章末无钩子、情节硬伤 | **必改**，只报不自动改 |
| 🟡 建议级 | 节奏拖/爽点弱、伏笔未回收、信息密度低、留白未填、配角脸谱化 | 建议改 |
| 🟢 润色级 | 用词重复、个别过度直白、标点/错别字 | 可改可不改，`--fix` 可自动 |

**容错铁律**：只报"真问题"。轻微主观偏好（"我会换个词"）**不入报告**——否则噪声淹没硬伤。这条等同 n2d 出图的"筛选宽容铁律"。

> **修法回哪个 skill**（同 n2d/mv-review 的回流定位）：每条阻断/建议级修法都指明回源头重跑——OOC/设定矛盾→回 `novel-rewrite`/`novel-create` 改设定圣经再回扫；锚点漂移→对 `novel-spinoff` 锚点表；节奏塌/钩子弱→回写章纲（`novel-craft/references/outline.md`）；原文照搬→回对应派生 skill 重写该章。审已写章节、**未到的阶段不当问题报**（先读 `_进度.md`）。

---

# 模式②：流程自审（让写小说产线自我优化）

把"人工复盘整条 novel 线"固化成可复跑流程。**节律**：用户主动要 / 写完一批书后 / 接了新写作工艺·新平台套路时跑一次。详细步骤见 `references/self_audit.md`，要点：

1. **先跑本地静态治理检查**：`python3 skills/novel-review/scripts/self_audit.py [--project-root "<作品根>"]`。它不联网、不改文件，检查 registry/README/author 路由同步、`_进度.md` 写入口、`state_ledger` 原子写、批量写章队列、市场基准新鲜度。
2. **拉基准**：联网搜当前（带年月）网文/小说主流做法，分三轴取证——**题材/市场契合**（红果/番茄/晋江/抖音当下热题材与套路，复用 `novel-score/scripts/collect_market_baseline.py` 的热榜拉取）、**写作工艺**（黄金三章钩子、爽点密度、章纲编织、单章守则 vs `novel-craft/references/*`）、**一致性/合规来源**（设定圣经/锚点一致性方法、公版/授权来源边界 vs fetch/spinoff/rewrite 的合规闸门）+ 各能力演进。
3. **对照**：逐 skill 把基准 vs `novel-*/SKILL.md` + `novel-craft` + `novel-author/Q&A.md` 比，找**真差距**（已做的别重复立项，标"✅ 已覆盖"一行带过）。
4. **差距清单**：每条 = 差距 + 证据（带来源链接·日期）+ 落到哪个 skill 哪段 + 优先级（must/optional）+ 是否可脚本化（是→能进 `mechanical_check.py`）。
5. **起草**：高价值项起草建议 edit；**改任何 skill 必同步 `skills/README.md` 索引**（仓库硬约定）。
6. **人确认后再写**：模式②**默认只产建议报告**，不自动改 skill。**报告是一次性的——只讲给用户、不在 skill 目录留存 `_流程自审_*.md` 这类存档**（已 gitignore）。**每次自审/重审都从头按本流程重跑**（拉基准→对照→差距），**绝不读旧报告当捷径**——市场会变，旧结论可能已过时或已落地。

> **防过期铁律**：市场建议带"采集日期 + 来源链接"，旧建议可能已被采纳或过时——写进来前先核对当前 skill 是否已有。与 `novel-score` 共用 `novel-score/references/market-baseline.md` 和 `scripts/collect_market_baseline.py`，避免两处各拉一份。

---

## 详细参考
- 一键机检 runner：`scripts/consistency_audit.py`（串跑 mechanical + `novel-wiki/logic_sentry` + `novel-style` 漂移）
- 流程自审本地治理检查：`scripts/self_audit.py`（registry / 进度写入 / 账本原子写 / draft queue / market baseline freshness）
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
