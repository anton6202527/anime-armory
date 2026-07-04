# n2d Series Bible

- kind: n2d_series_bible
- episodes: 10
- hooks: 22
- threads: 28

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
- scene_floorplan: 设定库/scene_floorplan.json

## 每集叙事图

| 集 | Clips | 角色 | 资产 | 钩子 | 线程 |
|---|---:|---|---|---|---|
| 第1集 | 25 | CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA、CROWD_ZAYI、CHAR_TAIXUMEN_ZHANGLAO、CHAR_JIANG_JIAN、CHAR_HAN_LAOSAN | LOC_ZAYI_DADIAN、VFX_WUXING_GUANGDIAN、LOC_WAIMEN_JIUYUAN、PROP_XIUZHEN_ZIYUAN、LOC_ZAYI_YUAN、PROP_WATER_JARS、PROP_KEY_LOCK、PROP_TIE_WAN、PROP_SHUI_TONG、PROP_BIAN_DAN、LOC_HOUSHAN_QIANTAN、PROP_HEI_TAO_PEN | 6 | 8 |
| 第2集 | 27 | CHAR_HAN_LAOSAN、CHAR_TAIXUMEN_ZHANGLAO、CHAR_JIANG_JIAN、CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA | PROP_HEI_TAO_PEN、PROP_GREEN_WATER、LOC_ZAYI_HUT、VFX_BASIN_MICROGLOW、PROP_SHUI_TONG、LOC_HOUSHAN_WATER_PATH、LOC_ZAYI_FOOD_YARD、PROP_FOOD_BOWL、PROP_WATER_JARS、LOC_ZAYI_WATER_JARS、PROP_SPIRIT_RICE_BAG、PROP_GRAY_RICE | 6 | 8 |
| 第3集 | 13 | CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA | PROP_BLACK_BASIN、PROP_GOLD_RICE、LOC_SERVANT_HUT、PROP_GREY_RICE_MEMORY、PROP_DOOR_LOCK、PROP_DOOR、PROP_TROUSER_PILLOW、PROP_MOUNTAIN_SPRING、PROP_WATER_BUCKETS、LOC_MOUNTAIN_SPRING、PROP_WATER_JAR、LOC_KITCHEN_YARD、PROP_INNER_SECT_LANTERN、VFX_INNER_SECT_FACELESS_SILHOUETTE、LOC_INNER_SECT_DISTANCE | 6 | 8 |
| 第4集 | 0 | - | - | 0 | 0 |
| 第5集 | 0 | - | - | 2 | 1 |
| 第6集 | 0 | - | - | 0 | 0 |
| 第7集 | 0 | - | - | 0 | 1 |
| 第8集 | 0 | - | - | 1 | 1 |
| 第9集 | 0 | - | - | 0 | 0 |
| 第10集 | 0 | - | - | 1 | 1 |

## 角色表演签名

| 角色 | 形态 | performance_signature | signature_equipment |
|---|---|---|---|
| CHAR_HE_PINGSHENG 贺平生 | 常态 | ready | - |
| CHAR_ZHANG_LAODA 张老大 | 常态 | ready | - |
| CHAR_HAN_LAOSAN 韩老三 | 常态 | ready | - |
| CHAR_JIANG_JIAN 江剑 | 背影 | ready | - |
| CHAR_TAIXUMEN_ZHANGLAO 太虚门长老 | 回忆背影 | ready | - |
| CHAR_HE_SANJIE 贺三杰 | 回忆影 | ready | - |
| CROWD_ZAYI 群杂役 | 虚化 | ready | - |
| CROWD_TAIXU_CULTIVATOR 太虚门远景修士剪影 | 远景剪影 | ready | - |

## Findings
- INFO [episode_missing_storyboard] 部分集缺 storyboard.json：第4集、第5集、第6集、第7集、第8集、第9集、第10集
- INFO [series_layers_not_registered] 以下剧级层尚未登记：narrative_state_ledger、ambient_map、ui_asset_registry、translation_glossary、series_packaging、location_spatial_memory
