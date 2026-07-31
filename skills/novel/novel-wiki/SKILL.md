---
name: novel-wiki
description: 长篇小说逻辑一致性守护者 — 自动提取并维护《动态百科》,监控角色生死、地点变迁、道具归属、能力副作用等核心状态。提供"逻辑哨兵"功能,在写作前或写完后交叉比对最新章节与百科库,拦截硬性冲突(如死人复活、时间线倒流、技能副作用遗忘)。与 novel-review 配合,解决长篇小说"越写越崩"的问题。另含**storyworld 写前压力测试 `storyworld_pressure_test.py`**（角色能动性、世界规则、地理势力、时间因果、章纲压力、读者契约、力量进阶）和**力量体系自检引擎 `power_system.py`**：穿越/系统流/修仙的等级·成长值·战力逐章一致性机检（等级/境界/战力只增不减、未知境界、越级过快、面板属性≤7、系统流久无升级桥段），真值在 `设定/power_system_registry.json`。另含**角色知情账 `knowledge_sentry.py`**：谁在第几章知道了什么秘密（掉马/身份/悬疑线的知情错乱机检——揭示超期、账目矛盾、泄密候选），真值在 `设定/knowledge_ledger.json`。Use when asked to 维护百科, 查逻辑错误, 检查设定冲突, 动态设定, 逻辑哨兵, 写前压力测试, storyworld, 自动更新设定, 力量体系自检, 等级一致性, 战力崩坏, 升级体系, 系统面板, 知情账, 谁知道什么, 掉马穿帮, check novel consistency, world-building wiki, power system. Triggers 动态百科, 逻辑哨兵, 查冲突, 查死人复活, 设定对齐, 状态追踪, 写前压力测试, storyworld, 力量体系, 等级体系, 战力一致, 升级数值, 系统面板, 知情账, 知情错乱, 掉马, 泄密穿帮, novel wiki, logic sentry, power system, knowledge ledger.
---

# novel-wiki — 动态百科与逻辑哨兵

专门解决长篇小说（>10万字）中因记忆偏差导致的**逻辑硬伤**。它不负责文采，只负责**状态的真实性**。

产物落盘在 `<作品根>/设定/动态百科.json`。

## 核心机制（确定性骨架 + LLM 补语义）

1. **增量提取 (Wiki Builder)**：`wiki_builder.py` 从 `设定/角色卡.md` 播种实体、扫章节算 `last_seen_chapter`、用死亡关键词做**疑似阵亡候选**（带 `auto` 标志 + 证据章，非闪回语境才记）。伤势细节、道具归属精确变更等语义状态由 LLM 在交互节点补全——脚本给确定性底座，让哨兵有真实可比对的状态。
2. **交叉验证 (Logic Sentry)**：`logic_sentry.py` 确定性扫**硬冲突候选**（死人复活/弃置道具复用/位置跳变/**数值漂移**——角色卡声明的年龄锚点被本章写成不同年龄且非时间跳跃语境），只报硬冲突，软性突变交 `novel-review`。**2026 通电**：原 `pass` 空桩已实现——**world_rule_violation**(违 `world_state_ledger` 已确立/未确立演进事实，靠 `forbidden_before/after` 关键词判)、**relationship_flip**(`relationship_matrix` 温度单章跳变>40 且无重大转折)、**张力账本三规则**(钩子过期/承诺违约/张力疲劳，读 `设定/tension_ledger.json`)。
   - **B10 收口（脆弱启发式不得硬阻断）**：上述检测器**几乎都是关键词/子串/邻近扫正文**，属跨线宪法 [`docs/skill-design-principles.md` B10](../../docs/skill-design-principles.md) 定义的**脆弱启发式**——只能 ≤建议级、**不硬挡 post_write**。落地走 novel 线单一收口 `novel/_lib/heuristic_gate.py`（实现 B10 的降级守卫）：`scan_chapter()`/`analyze()` 在库边界给每条 finding 标 `confidence`，把 `heuristic` 的 `阻断级` 自动降为 `建议级`（记 `downgraded_from` + `heuristic_downgraded` 计数·可见不静默）。**唯一保留阻断级的是确定性证据闸**——只比较 curated 台账的结构化整数、不扫正文：白名单 `foreshadowing_overdue`（伏笔台账 `expected_payoff` vs `through_chapter`）、`timeline_event_disorder`（`timeline.json` 的 `order` vs 成章序）。死人复活/弃置道具/世界规则/关系突变/角色护栏等正文关键词类**检出仍在、但只作建议级候选交人/LLM 定夺**。
   - **新增同线检测器**：`antagonist_scaling.py`(反派/威胁战力反向崩坏·建议级)、`timeline_check.py`(时间线倒流=建议级 / `设定/timeline.json` 事件乱序=阻断级·确定性台账序)、`minor_characters.py`(反复出场却未建卡的配角候选·建议级)。三者都进 `novel-review/consistency_audit` 汇总；唯 `timeline_event_disorder` 这类确定性台账闸仍硬挡 `post_write`。
   - **检索增强**：`novel/_lib/retrieval.py`（CJK-bigram BM25·纯标准库）给 `draft_packets` 写作包注入"跨 3 章窗口之外的相关旧章回溯"，补长程依赖盲区（写第230章想得起第47章埋的伏笔）。
3. **伏笔台账 (Foreshadow Ledger)**：`foreshadow_ledger.py` 维护 `设定/foreshadowing_ledger.json`，把「埋了哪些伏笔、该在哪一章收、收没收」记成账。**伏笔的识别（哪段算埋、哪段算收）是 LLM/人工的活，脚本不做正则式"自动伏笔检测"**（中文长篇里那只会制造噪声）；脚本负责的确定性部分是：超期(overdue)判定、回收率计算、状态机合法迁移与 JSON 完整性——和 logic_sentry 的"只报硬冲突候选"同一条诚实边界。

4. **角色别名脚手架 (Alias Scaffold)**：`alias_scaffold.py <作品根>` 从 角色卡/动态百科 抽**候选**别名（本名↔封号↔化名），并用正文共现/连通分量补一批 `candidate_clusters`（一簇疑似一个角色，供人逐簇确认），写 `设定/角色别名.json`（status=`draft`）。**人工核对后把 status 改 `confirmed`**，并把确认簇手动并入 `aliases/character_aliases`，`graph_sentry` 生命周期硬闸才会用它做实体消解——治"死亡记在本名、复现记在封号→硬闸漏判"（实体消解是确定性一致性闸的强制前置）。draft 期不影响判定；自动抽取/共现聚类可能误并同名角色或同场角色，故必须人确认才入硬闸。

5. **角色知情账 (Knowledge Sentry)**：`knowledge_sentry.py` 维护 `设定/knowledge_ledger.json`——每条秘密记
   knowers（第几章、怎么知道的）/ suspects / 误信者 / 读者知情章 / 计划揭示章 / 公开章（schema 见
   `references/entity-schema.md §8`）。**得知/怀疑/公开的语义识别是 LLM/人工的活**（交互节点判断后用
   `learn/suspect/reveal` 记账）；脚本管确定性部分：账目自洽（得知章 vs 公开章的序、与百科死亡章交叉）、
   `reveal_overdue`（计划揭示超 grace 未公开，high/critical=阻断级，与伏笔超期同口径）、泄密候选
   （`tell_keywords` 在任何知情锚点之前的章节出现——正文关键词扫描属脆弱启发式 B10，恒建议级）。
   写作端 `draft_packets.py` 自动把未公开秘密的知情面注入写章包；review 端由 `consistency_audit.py`
   子检测器 `knowledge_state` 汇总（`审稿/knowledge_report.json`）。

```bash
python3 skills/novel/novel-wiki/scripts/knowledge_sentry.py "<作品根>" add \
    --fact "沈念是前朝公主" --importance critical --holder 沈念:1 \
    [--reader-since 1] [--planned-reveal 40] [--keywords 前朝公主,皇室血脉] [--linked-seed SEED_003]
python3 skills/novel/novel-wiki/scripts/knowledge_sentry.py "<作品根>" learn --id SECRET_001 --name 王敦 --at 12 --how 偷听
python3 skills/novel/novel-wiki/scripts/knowledge_sentry.py "<作品根>" suspect --id SECRET_001 --name 皇帝 --at 22
python3 skills/novel/novel-wiki/scripts/knowledge_sentry.py "<作品根>" reveal --id SECRET_001 --at 40
python3 skills/novel/novel-wiki/scripts/knowledge_sentry.py "<作品根>" scan [--through 60] [--grace 5]
```

## 工作流

### 0. Storyworld 写前压力测试（长篇/复杂设定先跑）
长篇、商业连载、系统流、修仙、群像或世界规则复杂的项目，在批量写正文前先跑：

```bash
python3 skills/novel/novel-wiki/scripts/storyworld_pressure_test.py "<作品根>"
```

产物：
- `审稿/storyworld_pressure_test.json`
- `审稿/storyworld_pressure_test_<YYYY-MM-DD>.md`

检查 7 个轴：`character_agency`、`world_rules`、`geography_and_factions`、`timeline_causality`、`outline_pressure`、`reader_contract`、`power_progression`。判定是**结构化实质检查**（`check_depth: structural`）——逐角色核对目标、规则词多样性、时间线事件数、契约必备信号（题旨/承诺/禁偏至少两类）、章纲冲突覆盖率 ≥30%，塞关键词的空壳设定过不了；但语义自洽（规则互斥、目标是否挤压出冲突、承诺可否兑现、有无想象力支点）判不了——加 `--register-semantic-job` 登记 `语义任务/storyworld_semantic_review` 交 LLM 复核，报告的 `semantic_followup` 也会列出建议人判轴。结论：
- `block_pre_draft`：至少 3 个 risk，先回 `novel-craft`/`novel-create` 补设定，不进入批量写章。
- `revise_setting`：少量 risk，先补对应设定再写。
- `pass_with_review`：只剩 review 轴，允许写但后续重点盯。
- `pass`：可进入任务包生成。

### 1. 初始化/更新百科库
```bash
python3 skills/novel/novel-wiki/scripts/wiki_builder.py "<作品根>" [--range 1-50]
```
- 扫描指定章节。
- 产出/更新 `<作品根>/设定/动态百科.json`（实体名为 key 的字典）。
- **脚本确定性写入**：`category`、`status`、`last_seen_chapter`、`last_update`（死亡候选另写 `death_chapter`/`auto`/`evidence`）。
- **LLM/人工补全字段**：`location`、`owner`、`health`、`inventory`、`notes` 等语义状态——脚本不臆测，留交互节点补。完整 who-writes-what 见 `references/entity-schema.md`。

### 2. 逻辑哨兵巡检
```bash
python3 skills/novel/novel-wiki/scripts/logic_sentry.py "<作品根>" --chapter <章节号或路径>
```
- 读取百科库 + 目标文本。
- 扫描：
  - **生命状态**：是否引用了已标记为 `deceased` 的角色？
  - **位置冲突**：角色是否瞬间移动到了千里之外？
  - **道具归属**：角色是否使用了已丢弃或不在手上的道具？
  - **技能冷却/代价**：是否连续发动了有巨大代价且未冷却的禁招？
- 产出：`审稿/logic_alerts_<章节>.json`。

### 3. 伏笔台账：种—收对账 + 烂尾预警
契约注册表早已声明 `foreshadowing_ledger → 设定/foreshadowing_ledger.json`（owner=novel-wiki），
本能力是这个**已声明、原先没人落地**的产物的实现——dispatcher 与 novel-balance 一直承诺的「伏笔回收 / 烂尾预警」终于有了真实数据源。

```bash
# 埋伏笔（在交互节点由 LLM/人判断出"这里埋了伏笔"后登记）
python3 skills/novel/novel-wiki/scripts/foreshadow_ledger.py "<作品根>" plant \
    --desc "沈念捡到半块断剑" --at 5 --by 50 [--id SEED_001] [--importance high] [--entities 沈念,断剑]
# 回收（--partial 记部分回收 partially_resolved）
python3 skills/novel/novel-wiki/scripts/foreshadow_ledger.py "<作品根>" payoff --id SEED_001 --at 48 [--evidence "断剑认主"] [--partial]
# 作废（从回收率分母剔除）
python3 skills/novel/novel-wiki/scripts/foreshadow_ledger.py "<作品根>" drop --id SEED_001 [--reason "线索废弃"]
# 巡检：按当前进度章号算超期 + 回收率 → 审稿/foreshadow_report.json
python3 skills/novel/novel-wiki/scripts/foreshadow_ledger.py "<作品根>" scan --through 60 [--grace 5]
```
- **确定性产出**（脚本算）：`overdue`（未回收且越过 `expected_payoff_chapter + grace`）、`payoff_rate.回收率`（`resolved`÷有效伏笔，`dropped` 不进分母，`partially_resolved` 记半收，全空时为 `null` 不谎报 0/0）、严重度分级（`importance` high/critical 超期=阻断级=烂尾预警，其余=建议级）。
- **LLM/人工补**：到底哪段算埋伏笔、哪段算回收——脚本只记账、不识别。
- 账本 schema 与 `wiki_builder.py` 已初始化的同名文件、`references/entity-schema.md §3` 完全对齐（`kind=novel_foreshadowing_ledger`，`seeds[]`，状态 `pending|partially_resolved|resolved|dropped`）。

## 伏笔台账示例 (`foreshadowing_ledger.json`)
```json
{
  "kind": "novel_foreshadowing_ledger",
  "seeds": [
    {
      "id": "SEED_001",
      "description": "沈念捡到半块断剑",
      "status": "pending",
      "planted_chapter": 5,
      "expected_payoff_chapter": 50,
      "actual_payoff_chapter": null,
      "importance": "high",
      "linked_entities": ["沈念", "断剑"],
      "evidence": null
    }
  ]
}
```

## 百科条目示例 (`动态百科.json`)
> `health`/`location`/`inventory`/`owner` 为 LLM/人工补全字段（非脚本产出）；脚本只写 `category`/`status`/`last_seen_chapter`/`last_update` + 死亡候选字段。
```json
{
  "王敦": {
    "category": "character",
    "status": "active",
    "health": "wounded (left arm)",
    "location": "青云山",
    "inventory": ["残破的玉佩", "引雷符*2"],
    "last_update": 45
  },
  "清月剑": {
    "category": "item",
    "owner": "李慕白",
    "status": "shattered",
    "location": "断魂崖",
    "last_update": 42
  }
}
```

## 与家族其它 Skill 的联动

- **novel-create / continue**：在写新章前，先跑一次 `logic_sentry` 确认前置状态；新章埋下/回收伏笔时用 `foreshadow_ledger.py plant|payoff` 记一笔。
- **novel-balance**：它承诺的「烂尾预警」数据源就是 `foreshadow_ledger.py scan` 产出的 `审稿/foreshadow_report.json`（超期高价值伏笔 + 回收率）。`pacing_analyzer.py` 已读它，在 `情节热力图_<日期>.md` 出「烂尾预警（伏笔回收）」一节并写进 `pacing_signals.json.烂尾预警`，把"哪些大伏笔要烂尾了"落到具体 `id`。
- **novel-review**：作为"机检"环节的深度增强，由 `novel-review/scripts/consistency_audit.py` 一键串跑（建百科 → 逐章哨兵 → 汇总 `审稿/logic_alerts_summary.json`）；哨兵候选带 `auto` 标志，最终由人/LLM 定夺。`consistency_audit.py` 已把伏笔巡检接成子检测器 `foreshadow`：跑 `foreshadow_ledger.analyze(project)`（自动取已写最大章号为 `through`），落 `审稿/foreshadow_report.json` 并并进 `审稿/consistency_audit.json` 汇总，超期高价值伏笔记为阻断级 alert。

## 详细参考
- 百科 + 告警字段定义、死亡候选规则、四类硬冲突（死人复活/弃置道具复用/位置跳变/数值漂移）：`references/entity-schema.md`

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把百科当角色卡 | 角色卡是静态设定（性格/身世）；百科是动态状态（现状/伤势/位置） |
| 扫描全本烧 Token | 采用增量扫描，只读 `_进度.md` 标记为新出的章节 |
| 误报过多 | 哨兵只报“硬冲突”（生死、所有权），软性的“性格突变”交给 `novel-review` |
