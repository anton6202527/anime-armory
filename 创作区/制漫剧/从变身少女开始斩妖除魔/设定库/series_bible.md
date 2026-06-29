# n2d Series Bible

- kind: n2d_series_bible
- episodes: 3
- hooks: 8
- threads: 9

## 真值源
- global_style: 设定库/global_style.md
- 角色圣经: 设定库/角色圣经.md
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
| 第1集 | 13 | CHAR_JIANG_YUECHU、CHAR_GARRISON_SURVIVORS、CHAR_CHENG_LAO、CHAR_EMPEROR_TANG、CHAR_COURT_MINISTERS、CHAR_YOUNG_CAPTAIN | LOC_BAXI_BATTLEFIELD、WEAPON_DAHUANG_HALBERD、LOC_BAXI_BATTLEFIELD_ESTABLISH、VFX_WHITE_QI、VFX_SYSTEM_PANEL、VFX_ESSENCE_STREAMS、VFX_YINSHAN_MIST、LOC_TANG_COURT、PROP_IMPERIAL_DESK、PROP_STATE_LETTER、LOC_BROKEN_HOUSE、VFX_RED_FLOOD_DRAGON_SCROLL、LOC_CONSCIOUSNESS_SEA、VFX_THREE_DRAGON_ORBS | 6 | 8 |
| 第2集 | 0 | - | - | 1 | 1 |
| 第3集 | 0 | - | - | 1 | 0 |

## 角色表演签名

| 角色 | 形态 | performance_signature | signature_equipment |
|---|---|---|---|
| CHAR_JIANG_YUECHU 姜月初 | 战场形态 | ready | ['WEAPON_DAHUANG_HALBERD'] |
| CHAR_JIANG_YUECHU 姜月初 | 觉醒蓝调母本 | ready | - |

## Findings
- INFO [episode_missing_storyboard] 部分集缺 storyboard.json：第2集、第3集
- INFO [series_layers_not_registered] 以下剧级层尚未登记：narrative_state_ledger、leitmotif_registry、ambient_map、ui_asset_registry、translation_glossary、series_packaging、location_spatial_memory、scene_floorplan
