# 动态百科 + 逻辑哨兵 schema

## 动态百科（`设定/动态百科.json`，`wiki_builder.py` 产）

实体名为 key 的字典。脚本播种 + 增量更新，人/LLM 可手补语义字段。

```json
{
  "王敦": {
    "category": "character",
    "status": "active",            // active | deceased | （人工可加 wounded 等）
    "last_seen_chapter": 45,
    "last_update": 45,
    "death_chapter": 0,            // status=deceased 时由脚本填
    "auto": true,                  // 该状态为脚本自动推断，待复核
    "evidence": "……终于力竭身亡……",
    "location": "青云山",          // 人工/LLM 补
    "inventory": ["引雷符*2"]       // 人工/LLM 补
  },
  "清月剑": {
    "category": "item",
    "status": "shattered",         // 弃置/损毁类：discarded|shattered|lost|破碎|损毁|遗失
    "owner": "李慕白",
    "last_update": 42
  }
}
```

| 字段 | 谁写 | 说明 |
|---|---|---|
| `category` | 脚本（角色）/人工 | `character` 自动；`item`/`location` 需人工标 |
| `status` | 脚本播种 active + 死亡候选；人工补伤势 | 哨兵据此判冲突 |
| `last_seen_chapter` / `last_update` | 脚本 | 增量扫描更新 |
| `death_chapter` | 脚本 | 疑似阵亡章，哨兵以此为界判"死后复活" |
| `auto` / `evidence` | 脚本 | 自动推断标志 + 证据原文，**复核后可删 auto 转人工确认** |
| `location` / `inventory` / `owner` | 人工/LLM | 脚本不臆测位置/归属，留语义层补 |

**死亡候选规则**：角色名 ±18 字窗口出现死亡词（死了/身亡/阵亡/殒/葬身/气绝/命丧/战死…）且窗口内无闪回词（回忆/闪回/梦中/亡魂/托梦…）才记，避免把"差点死/回忆里死"误判。

## 逻辑告警（`审稿/logic_alerts_<章>.json`，`logic_sentry.py` 产）

```json
{ "status": "conflicts", "chapter": 50, "blocking": 1,
  "alerts": [
    {"type":"deceased_reactivation","entity":"王敦","severity":"阻断级",
     "chapter":50,"death_chapter":45,"evidence":"……","auto":true,"note":"……"}
  ] }
```

三类硬冲突：
- `deceased_reactivation`（阻断级）：deceased 角色在 `death_chapter` 之后再在场行动，且非闪回。
- `discarded_item_reuse`（阻断级）：弃置/损毁道具又被使用动词（用/催动/祭出…）带到。
- `location_jump`（建议级·保守）：角色出现在与百科 `location` 不同的已知地点，且全章无位移过渡词——**易误报**，纯候选，必须人判。

容错铁律：哨兵宁缺毋滥。所有 `auto:true` 是线索不是判决，伏笔/闪回/合理位移由人/LLM 豁免。
