# n2d Series Bible

- kind: n2d_series_bible
- episodes: 10
- hooks: 19
- threads: 9

## 真值源
- global_style: 设定库/global_style.md
- 角色圣经: 未登记
- setup_payoff_ledger: 设定库/setup_payoff_ledger.json
- narrative_state_ledger: 未登记
- story_integrity_ledger: 设定库/story_integrity_ledger.json
- thread_scheduler: 设定库/thread_scheduler.json
- leitmotif_registry: 设定库/leitmotif_registry.json
- ambient_map: 未登记
- ui_asset_registry: 未登记
- translation_glossary: 未登记
- series_packaging: 未登记
- location_spatial_memory: 未登记
- scene_floorplan: 未登记

## 每集叙事图

| 集 | Clips | 角色 | 资产 | 钩子 | 线程 |
|---|---:|---|---|---|---|
| 第1集 | 19 | CHAR_01、CHAR_02、BEAST_01 | LOC_01、VFX_01、PROP_01、PROP_01在两者中间、PROP_02、VFX_01占右上负空间、VFX_01作为仅姜可见叠加进入、PROP_02在裴右侧地面、PROP_02落点不跳、VFX_01退出清晰画面、PROP_02由持起转为刺入状态 | 6 | 8 |
| 第2集 | 0 | - | - | 0 | 0 |
| 第3集 | 0 | - | - | 2 | 0 |
| 第4集 | 0 | - | - | 1 | 0 |
| 第5集 | 0 | - | - | 1 | 0 |
| 第6集 | 0 | - | - | 2 | 0 |
| 第7集 | 0 | - | - | 2 | 0 |
| 第8集 | 0 | - | - | 0 | 1 |
| 第9集 | 0 | - | - | 3 | 0 |
| 第10集 | 0 | - | - | 2 | 0 |

## 角色表演签名

| 角色 | 形态 | performance_signature | signature_equipment |
|---|---|---|---|

## Findings
- WARN [missing_identity_registry] 缺 identity_registry.json，series_bible 只能建立叙事层，无法汇总角色 DNA。
- INFO [missing_asset_registry] 缺 asset_registry.json；若尚未进入出图阶段可接受，出图前需补。
- INFO [episode_missing_storyboard] 部分集缺 storyboard.json：第2集、第3集、第4集、第5集、第6集、第7集、第8集、第9集
- INFO [series_layers_not_registered] 以下剧级层尚未登记：narrative_state_ledger、ambient_map、ui_asset_registry、translation_glossary、series_packaging、location_spatial_memory、scene_floorplan
