---
name: novel-review
description: Use when checking / auditing the quality of ALREADY-WRITTEN novel chapters (.md/.txt) — finding POV slips (串视角/视角穿帮), OOC / 人设崩, plot holes, anchor & timeline drift, setting contradictions (设定矛盾), pacing / missing-hook problems, voice drift (文风漂移), or copied source text (原文照搬) — and producing a severity-tagged, location-pinned review report. For 续写/外传 projects it cross-checks 设定/(角色卡·世界观·锚点表·章纲) and 原作. Does NOT write/continue the story. Triggers 审稿, 质检, 检查小说质量, 查人设崩, 视角穿帮, 串视角, 设定矛盾, 锚点对齐, 一致性回扫, 伏笔回收, 节奏, 文风漂移, 原文照搬, 质量报告, novel review, QA.
---

# novel-review — 已写小说章节质检 / 审稿

不写、不续小说，只**审已写的章节**：扫出问题 → 定位（章 + 行/段）→ 定级 → 给可执行修法 → 产出审稿报告。是 novel-* 家族的质检环节，把 `novel-spinoff` 第 7 步回扫 + Demo 自检清单**通用化、独立化**。

## 机检 / 人判分工

- **机检（确定性，先跑）**：`scripts/mechanical_check.py` —— 格式/字数带宽/章末钩子缺失/视角"我"泄漏/称谓·术语漂移/**原文照搬（n-gram vs 原作.txt）**/章号与章纲对齐。秒级出确定性问题清单。
- **人判（LLM 判断题）**：机检覆盖不了的——视角穿帮、OOC、情节漏洞、锚点语义对齐、节奏（爽点/钩子/反转）、伏笔回收、留白、文风漂移、show-don't-tell、过度直白。维度逐条见 `references/checklist.md`。

## 工作流

0. **定位项目**：作品根需含 `章节/*.md`（理想还有 `设定/`、`原作.txt`、`设定/章纲.md`）。先确认三件事：① POV 角色 + 人称（如"王敦/第三人称限定"）② 文风锚点章（如 Demo 第1章）③ 是否续写/外传（是 → 需锚点对齐 + 原文照搬检查）。
1. **跑机检脚本** → 确定性问题清单。
2. **分 arc 人判**：章多时**每个 arc 派一个 subagent** 审（省主上下文），每章对照 `references/checklist.md` 维度，**只记真问题**，每条带原文引文证据。
3. **汇总报告** → 写 `审稿/审稿报告.md`：按严重度排序，每条 = 位置（第N章·第X段）+ 维度 + 问题 + **建议修法** + 证据引文。附"健康度概览"表（各维度通过/问题数）。
4. **（可选 `--fix`）**：只就地做**润色级**小改；**阻断/建议级只报不自动改**，交作者定夺。

## 严重度（定级 + 容错铁律）

| 级别 | 含 | 处置 |
|---|---|---|
| 🔴 阻断级 | 视角穿帮/串视角、OOC 人设崩、锚点错位、设定自相矛盾、原文大段照搬、漫剧档章末无钩子、情节硬伤 | **必改**，只报不自动改 |
| 🟡 建议级 | 节奏拖/爽点弱、伏笔未回收、信息密度低、留白未填、配角脸谱化 | 建议改 |
| 🟢 润色级 | 用词重复、个别过度直白、标点/错别字 | 可改可不改，`--fix` 可自动 |

**容错铁律**：只报"真问题"。轻微主观偏好（"我会换个词"）**不入报告**——否则噪声淹没硬伤。这条等同 n2d 出图的"筛选宽容铁律"。

## 详细参考
- 两层质检维度全清单（看什么 + ✅/❌ + 定级）：`references/checklist.md`
- 正向标准（单章该长啥样）：`novel-craft/references/chapter.md`
- 锚点/视角规则（外传）：`novel-spinoff/references/timeline-anchoring.md` + `pov-craft.md`

## 常见错误

| 错误 | 纠正 |
|---|---|
| 只跑脚本不做人判 | 机检只覆盖确定性问题；OOC/节奏/锚点语义要 LLM 判 |
| 只人判不跑脚本 | 原文照搬/字数/钩子缺失这类机检秒查，漏跑等于白审 |
| 鸡蛋里挑骨头堆一堆润色项 | 违容错铁律；硬伤被噪声淹没 |
| 报问题不定位不给修法 | 必须 章+段定位 + 可执行建议（业界：把模糊意见变 actionable） |
| 阻断级自动改 | 阻断级（人设/情节/锚点）只报，交作者；自动只碰润色级 |
| 续写项目跳过锚点对齐 | 外传/续写必查与 `锚点表`/`原作` 的事件骨架是否一致 |
