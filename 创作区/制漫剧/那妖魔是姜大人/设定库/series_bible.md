# n2d Series Bible

- kind: n2d_series_bible
- episodes: 10
- hooks: 25
- threads: 17

## 真值源
- global_style: 设定库/global_style.md
- 角色圣经: 设定库/角色圣经.md
- setup_payoff_ledger: 设定库/setup_payoff_ledger.json
- narrative_state_ledger: 未登记
- story_integrity_ledger: 设定库/story_integrity_ledger.json
- thread_scheduler: 设定库/thread_scheduler.json
- leitmotif_registry: 设定库/leitmotif_registry.json
- ambient_map: 设定库/ambient_map.json
- ui_asset_registry: 未登记
- translation_glossary: 未登记
- series_packaging: 未登记
- location_spatial_memory: 设定库/location_spatial_memory.json
- scene_floorplan: 设定库/scene_floorplan.json

## 每集叙事图

| 集 | Clips | 角色 | 资产 | 钩子 | 线程 |
|---|---:|---|---|---|---|
| 第1集 | 11 | CHAR_01、CHAR_03、CHAR_02 | LOC_01、VFX_虎妖黑血妖气、WEAPON_01、VFX_系统面板 | 6 | 8 |
| 第2集 | 10 | CHAR_01、CHAR_02、CHAR_03 | LOC_01、WEAPON_01、VFX_系统面板、VFX_虎山神摹影 | 6 | 8 |
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
| CHAR_01 姜月初 | 囚犯初醒态 | ready | ['WEAPON_01', 'VFX_系统面板', 'VFX_虎山神摹影', 'VFX_道行计数overlay'] |
| CHAR_02 裴长青 | 濒死战损态 | ready | - |
| CHAR_03 虎山神 / 虎妖 | 诈死复苏态 | ready | ['VFX_虎山神摹影'] |

## Findings
- INFO [episode_missing_storyboard] 部分集缺 storyboard.json：第3集、第4集、第5集、第6集、第7集、第8集、第9集、第10集
- INFO [series_layers_not_registered] 以下剧级层尚未登记：narrative_state_ledger、ui_asset_registry、translation_glossary、series_packaging
