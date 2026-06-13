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

## 5. 逻辑告警（`审稿/logic_alerts_<章>.json`）

新增类型：
- `foreshadowing_overdue`（阻断级）：高价值种子超过 `expected_payoff_chapter` 仍未处理。
- `relationship_flip`（建议级）：人物关系温度在单章内波动超过 40 度（除非有重大转折事件）。
- `world_rule_violation`（阻断级）：违反了 `world_state_ledger` 中已确立的演进事实。

