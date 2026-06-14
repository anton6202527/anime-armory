---
name: novel-wiki
description: 长篇小说逻辑一致性守护者 — 自动提取并维护《动态百科》,监控角色生死、地点变迁、道具归属、能力副作用等核心状态。提供"逻辑哨兵"功能,在写作前或写完后交叉比对最新章节与百科库,拦截硬性冲突(如死人复活、时间线倒流、技能副作用遗忘)。与 novel-review 配合,解决长篇小说"越写越崩"的问题。Use when asked to 维护百科, 查逻辑错误, 检查设定冲突, 动态设定, 逻辑哨兵, 自动更新设定, check novel consistency, world-building wiki. Triggers 动态百科, 逻辑哨兵, 查冲突, 查死人复活, 设定对齐, 状态追踪, novel wiki, logic sentry.
---

# novel-wiki — 动态百科与逻辑哨兵

专门解决长篇小说（>10万字）中因记忆偏差导致的**逻辑硬伤**。它不负责文采，只负责**状态的真实性**。

产物落盘在 `<作品根>/设定/动态百科.json`。

## 核心机制（确定性骨架 + LLM 补语义）

1. **增量提取 (Wiki Builder)**：`wiki_builder.py` 从 `设定/角色卡.md` 播种实体、扫章节算 `last_seen_chapter`、用死亡关键词做**疑似阵亡候选**（带 `auto` 标志 + 证据章，非闪回语境才记）。伤势细节、道具归属精确变更等语义状态由 LLM 在交互节点补全——脚本给确定性底座，让哨兵有真实可比对的状态。
2. **交叉验证 (Logic Sentry)**：`logic_sentry.py` 确定性扫**硬冲突候选**（死人复活/弃置道具复用/位置跳变），只报硬冲突，软性突变交 `novel-review`。
3. **伏笔台账 (Foreshadow Ledger)**：`foreshadow_ledger.py` 维护 `设定/foreshadowing_ledger.json`，把「埋了哪些伏笔、该在哪一章收、收没收」记成账。**伏笔的识别（哪段算埋、哪段算收）是 LLM/人工的活，脚本不做正则式"自动伏笔检测"**（中文长篇里那只会制造噪声）；脚本负责的确定性部分是：超期(overdue)判定、回收率计算、状态机合法迁移与 JSON 完整性——和 logic_sentry 的"只报硬冲突候选"同一条诚实边界。

## 工作流

### 1. 初始化/更新百科库
```bash
python3 skills/novel-wiki/scripts/wiki_builder.py "<作品根>" [--range 1-50]
```
- 扫描指定章节。
- 产出/更新 `<作品根>/设定/动态百科.json`（实体名为 key 的字典）。
- **脚本确定性写入**：`category`、`status`、`last_seen_chapter`、`last_update`（死亡候选另写 `death_chapter`/`auto`/`evidence`）。
- **LLM/人工补全字段**：`location`、`owner`、`health`、`inventory`、`notes` 等语义状态——脚本不臆测，留交互节点补。完整 who-writes-what 见 `references/entity-schema.md`。

### 2. 逻辑哨兵巡检
```bash
python3 skills/novel-wiki/scripts/logic_sentry.py "<作品根>" --chapter <章节号或路径>
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
python3 skills/novel-wiki/scripts/foreshadow_ledger.py "<作品根>" plant \
    --desc "沈念捡到半块断剑" --at 5 --by 50 [--id SEED_001] [--importance high] [--entities 沈念,断剑]
# 回收（--partial 记部分回收 partially_resolved）
python3 skills/novel-wiki/scripts/foreshadow_ledger.py "<作品根>" payoff --id SEED_001 --at 48 [--evidence "断剑认主"] [--partial]
# 作废（从回收率分母剔除）
python3 skills/novel-wiki/scripts/foreshadow_ledger.py "<作品根>" drop --id SEED_001 [--reason "线索废弃"]
# 巡检：按当前进度章号算超期 + 回收率 → 审稿/foreshadow_report.json
python3 skills/novel-wiki/scripts/foreshadow_ledger.py "<作品根>" scan --through 60 [--grace 5]
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
- **novel-balance**：它承诺的「烂尾预警」一直缺真实数据源——现在 `foreshadow_ledger.py scan` 产出的 `审稿/foreshadow_report.json`（超期高价值伏笔 + 回收率）就是这个数据源；balance 读它即可把"哪些大伏笔要烂尾了"落到具体 `id`。
- **novel-review**：作为"机检"环节的深度增强，由 `novel-review/scripts/consistency_audit.py` 一键串跑（建百科 → 逐章哨兵 → 汇总 `审稿/logic_alerts_summary.json`）；哨兵候选带 `auto` 标志，最终由人/LLM 定夺。`consistency_audit.py` 是顺带串跑伏笔巡检（`foreshadow_ledger.py scan --through <进度章>`）的天然位置——把 `审稿/foreshadow_report.json` 并进汇总即可；该挂接留给 novel-review，本 skill 不越界改它。

## 详细参考
- 百科 + 告警字段定义、死亡候选规则、三类硬冲突：`references/entity-schema.md`

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把百科当角色卡 | 角色卡是静态设定（性格/身世）；百科是动态状态（现状/伤势/位置） |
| 扫描全本烧 Token | 采用增量扫描，只读 `_进度.md` 标记为新出的章节 |
| 误报过多 | 哨兵只报“硬冲突”（生死、所有权），软性的“性格突变”交给 `novel-review` |
