# n2d Series Bible

- kind: n2d_series_bible
- episodes: 1
- hooks: 6
- threads: 6

## 真值源
- global_style: 设定库/global_style.md
- 角色圣经: 未登记
- setup_payoff_ledger: 设定库/setup_payoff_ledger.json
- narrative_state_ledger: 未登记
- story_integrity_ledger: 设定库/story_integrity_ledger.json
- thread_scheduler: 设定库/thread_scheduler.json
- leitmotif_registry: 未登记
- ambient_map: 未登记
- ui_asset_registry: 未登记
- translation_glossary: 未登记
- series_packaging: 未登记
- location_spatial_memory: 未登记
- scene_floorplan: 未登记

## 每集叙事图

| 集 | Clips | 角色 | 资产 | 钩子 | 线程 |
|---|---:|---|---|---|---|
| 第1集 | 7 | CHAR_01、CHAR_02、GROUP_01 | LOC_01、PROP_木牌、LOC_02、PROP_旧布包、PROP_扁担、PROP_水桶、PROP_旧布包在上镜身世插入镜后留在杂役院画外、LOC_03、PROP_01、PROP_01仍未入画、PROP_01从画左浅水入画并被CHAR_01抱起 | 6 | 6 |

## 角色表演签名

| 角色 | 形态 | performance_signature | signature_equipment |
|---|---|---|---|

## Findings
- WARN [missing_identity_registry] 缺 identity_registry.json，series_bible 只能建立叙事层，无法汇总角色 DNA。
- INFO [missing_asset_registry] 缺 asset_registry.json；若尚未进入出图阶段可接受，出图前需补。
- INFO [series_layers_not_registered] 以下剧级层尚未登记：narrative_state_ledger、leitmotif_registry、ambient_map、ui_asset_registry、translation_glossary、series_packaging、location_spatial_memory、scene_floorplan
