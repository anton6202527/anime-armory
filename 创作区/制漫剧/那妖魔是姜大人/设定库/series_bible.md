# n2d Series Bible

- kind: n2d_series_bible
- episodes: 10
- hooks: 29
- threads: 21

## 真值源
- global_style: 设定库/global_style.md
- 角色圣经: 设定库/角色圣经.md
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
| 第1集 | 8 | CHAR_01/囚途残损态、CHAR_02/濒死态、BEAST_01/复生态焦外、CHAR_02/半跪重伤态、BEAST_01/伪死态、CHAR_02/重伤态、CHAR_02/重伤搀扶态、BEAST_01/复生态、CHAR_02/搏命冲锋至倒地濒死态、CHAR_02/濒死受刀态、BEAST_01/焦外 | LOC_01、PROP_横刀、PROP_断刀、PROP_翻覆囚车、PROP_断刀中景横向封路、PROP_横刀右下地面、LOC_01光位、VFX_百妖谱、VFX_系统面板、PROP_横刀中轴 | 6 | 8 |
| 第2集 | 8 | CHAR_01、CHAR_02、BEAST_01 | LOC_01、WEAPON_横刀、VFX_百妖谱、LOC_01冷灰侧逆光无人物底板、VFX_墨虎谱影、VFX_系统面板 | 6 | 8 |
| 第3集 | 8 | CHAR_01/镇魔司制服态、CHAR_03/风尘劲装态、GROUP_01/齐跪态、CHAR_01/囚服残损态、CHAR_02/浅坟遗体态、CHAR_01/囚服转制服态、GROUP_01/列队戒备态、GROUP_01/齐跪态焦外 | LOC_02、LOC_02黄土官道的双车辙、WEAPON_横刀、PROP_镇魔司制服、LOC_01 | 6 | 4 |
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
| CHAR_01 姜月初 | “囚途残损态” | ready | ['WEAPON_01', 'WEAPON_横刀', 'VFX_系统面板'] |
| CHAR_02 裴长青 | “濒死重伤态” | ready | ['WEAPON_01', 'WEAPON_横刀'] |
| BEAST_01 虎妖 | “穿心复生态” | ready | ['WEAPON_01', 'WEAPON_横刀'] |

## Findings
- INFO [episode_missing_storyboard] 部分集缺 storyboard.json：第4集、第5集、第6集、第7集、第8集、第9集、第10集
- INFO [series_layers_not_registered] 以下剧级层尚未登记：narrative_state_ledger、ambient_map、ui_asset_registry、translation_glossary、series_packaging、location_spatial_memory、scene_floorplan
