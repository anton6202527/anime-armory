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
  如果骨架是 coarse 粒度 → 提示按本文 schema 以 fine 粒度重抽（LLM 抽取，粒度字段照此登记）。
- **novel-condense**：读任意粒度的骨架，以 `priority=must_keep` 的 beat 为压缩底线；
  其余 beat 按 `type` 决定压缩策略（filler → 一刀切，hook → 保留概述，reversal → 必须保留）。
- **互转**：`fine → coarse` 只需丢弃 `fine_detail` 并过滤非 must_keep beat；
  `coarse → fine` 需重抽（不可自动补全）。

## 迁移（现状如实说明）

**当前实现现状**：expand 实际产 `设定/事件骨架.json`、condense 实际产 `设定/主线骨架.json`，两套字段近似但**并未统一**，也没有自动互转脚本——统一的 `剧情骨架.json`（带 `granularity` 字段）是本文档定义的**目标 schema**，供两线新项目直接采用。骨架抽取本身是语义工作（判断哪个是 beat、哪个 must_keep），按线内分层应走 LLM/语义任务，不做正则抽取脚本；
"fine → coarse 丢字段、coarse → fine 重抽"的互转规则见上节，手工或 LLM 按规则执行即可。
存量项目可继续用旧文件名；新项目建议直接落 `设定/剧情骨架.json` 并标 `granularity`，消费方优先读新文件、缺则回退旧文件。
