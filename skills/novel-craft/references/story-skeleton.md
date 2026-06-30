# 剧情骨架统一 schema

`novel-expand` 和 `novel-condense` 对原作的结构化抽象原各用一套 schema：
- expand 用 `设定/事件骨架.json`（细粒度：bullet 级对话、心理、空间锚点）
- condense 用 `设定/主线骨架.json`（粗粒度：只标记不能砍的骨头——反转、钩子、高情绪段落）

两者追踪的都是"原作的剧情结构"，但格式不互通。若先 condense 再 expand（合理需求），两个骨架无法直接转换。

**统一方案**：用单一 `设定/剧情骨架.json`，内含 `granularity` 字段区分细/粗粒度，
两种技能的消费者按需读取对应层。

## 文件位置

`<作品根>/设定/剧情骨架.json`

## JSON Schema

```json
{
  "schema_version": 1,
  "kind": "novel_story_skeleton",
  "granularity": "fine",
  "source": "原作.txt",
  "extracted_at": "2026-06-25",
  "chapters": [
    {
      "chapter": 1,
      "title": "开端",
      "beats": [
        {
          "id": "CH01_B01",
          "type": "hook",
          "description": "主角发现第一条线索",
          "priority": "must_keep",
          "fine_detail": {
            "dialogue": ["「这不可能——」"],
            "psychology": "震惊→怀疑→决定追查",
            "spatial_anchor": "深夜书房，窗外暴雨",
            "sensory": "旧书霉味，雨水滴答"
          },
          "characters": ["主角"],
          "threads": ["第一条线索"]
        }
      ],
      "reversal_points": ["CH01_B01"],
      "hook_points": ["CH01_B01"]
    }
  ],
  "global": {
    "reversal_map": {"1": "CH01_B01", "2": "CH12_B03"},
    "must_keep_hooks": ["第一条线索", "身份伏笔", "最终对决"]
  }
}
```

## 粒度层级

| 字段 | fine（expand 用） | coarse（condense 用） |
|------|------------------|---------------------|
| `fine_detail` | ✅ 对话/心理/空间锚点/五感 | ❌ 省略 |
| `type` | 全部类型（hook/reversal/bond/action/reveal/filler） | 仅 must_keep 的 beat |
| `priority` | 全部标注 | 仅 `must_keep` |

## 消费者适配

- **novel-expand**：读 `granularity=fine` 的骨架，用 `fine_detail` 引导扩写方向。
  如果骨架是 coarse 粒度 → 提示先跑 `extract_skeleton.py --granularity fine` 重抽。
- **novel-condense**：读任意粒度的骨架，以 `priority=must_keep` 的 beat 为压缩底线；
  其余 beat 按 `type` 决定压缩策略（filler → 一刀切，hook → 保留概述，reversal → 必须保留）。
- **互转**：`fine → coarse` 只需丢弃 `fine_detail` 并过滤非 must_keep beat；
  `coarse → fine` 需重抽（不可自动补全）。

## 迁移

存量项目可继续使用旧文件名（`事件骨架.json` / `主线骨架.json`），新技能加载时优先读新 `剧情骨架.json`；
不存在则回退到旧文件。由 `novel-craft/scripts/extract_skeleton.py`（待建）统一处理。
