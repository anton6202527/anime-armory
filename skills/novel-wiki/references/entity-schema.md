# 动态百科 + 逻辑哨兵 + 叙事对账 schema

## 1. 动态百科（`设定/动态百科.json`）

实体名为 key 的字典。支持角色状态、人物关系与世界演进。

```json
{
  "王敦": {
    "category": "character",
    "status": "active",
    "psychological_arc": {
      "internal_conflict": "对皇室的盲忠 vs 亲眼所见的腐败",
      "resolution_progress": 0.35,
      "current_mindset": "开始质疑，但尚未行动"
    },
    "location": "青云山",
    "last_update": 45
  }
}
```

## 2. 人物关系矩阵（`设定/relationship_matrix.json`）

```json
{
  "kind": "novel_relationship_matrix",
  "version": 1,
  "matrix": {
    "沈念|王敦": {
      "temperature": 25,
      "labels": ["戒备", "由于Clip_48救命之恩开始松动"],
      "last_update": 48
    }
  }
}
```

## 3. 伏笔与回收账本（`设定/foreshadowing_ledger.json`）

```json
{
  "kind": "novel_foreshadowing_ledger",
  "seeds": [
    {
      "id": "SEED_001",
      "description": "沈念在第5章捡到半块断剑",
      "status": "pending",      // pending | partially_resolved | resolved | dropped
      "planted_chapter": 5,
      "expected_payoff_chapter": 50,
      "actual_payoff_chapter": null,
      "importance": "high",     // low | medium | high | critical
      "linked_entities": ["沈念", "断剑"]
    }
  ]
}
```

## 4. 世界演进账本（`设定/world_state_ledger.json`）

```json
{
  "kind": "novel_world_state_evolution",
  "major_changes": [
    {
      "event": "青云宗禁地被破",
      "impact": "禁术流出，原本的'无法瞬间位移'规则被打破",
      "chapter": 42
    }
  ]
}
```

## 5. 张力账本（`设定/tension_ledger.json`）

情绪 ROI 追踪（schema 见 `novel-craft/references/tension-ledger.md`）：`unresolved_hooks`（高悬念钩子）、
`reader_promises`（读者承诺 + `deadline_event`）、`chapter_tension_curve`（逐章张力分 + 主导情绪）。
由 LLM/编辑经 state_delta 维护（与 character_changes/伏笔种子同一套纪律）；逻辑哨兵据此跑钩子过期/
承诺违约/张力疲劳三规则。

## 6. 剧情环 vs 伏笔账本——明确分工（去冗余）

两者都"追埋了没收"，但**分层不同，勿双重登记同一条**：
- **`foreshadowing_ledger.json`（细伏笔·机检层）**：具体种子（某物/某话/某细节）→ 回收章。有确定性
  机检（`foreshadow_ledger.py` / 逻辑哨兵 `foreshadowing_overdue`：高价值超窗 = 阻断级）。**需要机器盯
  回收率的，登记在这里。**
- **`剧情环.json`（卷级结构大环·提醒层）**：明线循环/角色弧/卷级悬念这类**结构性大环**，作 `draft_packets`
  写作包里的人读提醒（不做独立机检，避免与伏笔账本重复打分）。**结构编排提示登记在这里。**
- 同一条线索二选一登记：细节级 → 伏笔账本；结构级 → 剧情环。

## 7. 逻辑告警（`审稿/logic_alerts_<章>.json`）

类型：
- `foreshadowing_overdue`（建议级）：高价值种子超过 `expected_payoff_chapter` 仍未处理。
- `relationship_flip`（建议级）：人物关系温度在单章内波动超过 40 度（除非有重大转折事件）。
- `world_rule_violation`（阻断级）：违反 `world_state_ledger` 中已确立/未确立的演进事实（需声明 `forbidden_before`/`forbidden_after` 关键词）。
- `hook_stale`（建议级）：`urgency=high` 钩子超过 10 章未解。
- `promise_broken`（阻断级）：`deadline_event` 已在本章触发但读者承诺未兑现。
- `tension_fatigue`（建议级）：连续 3 章 `tension_score < 5`。

