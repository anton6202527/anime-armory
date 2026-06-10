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

- **novel-create / continue**：在写新章前，先跑一次 `logic_sentry` 确认前置状态。
- **novel-review**：作为"机检"环节的深度增强，由 `novel-review/scripts/consistency_audit.py` 一键串跑（建百科 → 逐章哨兵 → 汇总 `审稿/logic_alerts_summary.json`）；哨兵候选带 `auto` 标志，最终由人/LLM 定夺。

## 详细参考
- 百科 + 告警字段定义、死亡候选规则、三类硬冲突：`references/entity-schema.md`

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把百科当角色卡 | 角色卡是静态设定（性格/身世）；百科是动态状态（现状/伤势/位置） |
| 扫描全本烧 Token | 采用增量扫描，只读 `_进度.md` 标记为新出的章节 |
| 误报过多 | 哨兵只报“硬冲突”（生死、所有权），软性的“性格突变”交给 `novel-review` |
