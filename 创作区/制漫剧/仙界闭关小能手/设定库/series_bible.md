# n2d Series Bible

- kind: n2d_series_bible
- episodes: 4
- hooks: 6
- threads: 16

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
| 第1集 | 7 | CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA、CROWD_ZAYI、CHAR_TAIXUMEN_ZHANGLAO、CHAR_JIANG_JIAN、CHAR_HE_SANJIE、CROWD_TAIXU_CULTIVATOR、CHAR_HAN_LAOSAN | LOC_ZAYI_DADIAN、LOC_WAIMEN_JIUYUAN、PROP_TIE_WAN、PROP_KEY_LOCK、LOC_ZAYI_YUAN、PROP_SHUI_TONG、LOC_HOUSHAN_QIANTAN、PROP_HEI_TAO_PEN | 6 | 8 |
| 第2集 | 0 | - | - | 0 | 4 |
| 第3集 | 0 | - | - | 0 | 4 |
| 第4集 | 0 | - | - | 0 | 0 |

## 角色表演签名

| 角色 | 形态 | performance_signature | signature_equipment |
|---|---|---|---|
| CHAR_HE_PINGSHENG 贺平生 | 常态 | ready | - |
| CHAR_HE_PINGSHENG 贺平生 | 幼年 | ready | - |
| CHAR_ZHANG_LAODA 张老大 | 常态 | ready | - |
| CHAR_HAN_LAOSAN 韩老三 | 常态 | ready | - |
| CHAR_JIANG_JIAN 江剑 | 背影 | ready | - |
| CHAR_TAIXUMEN_ZHANGLAO 太虚门长老 | 回忆背影 | ready | - |
| CHAR_HE_SANJIE 贺三杰 | 回忆影 | ready | - |
| CROWD_ZAYI 群杂役 | 虚化 | ready | - |
| CROWD_TAIXU_CULTIVATOR 太虚门远景修士剪影 | 远景剪影 | ready | - |

## Findings
- INFO [episode_missing_storyboard] 部分集缺 storyboard.json：第2集、第3集、第4集
- INFO [series_layers_not_registered] 以下剧级层尚未登记：narrative_state_ledger、leitmotif_registry、ambient_map、ui_asset_registry、translation_glossary、series_packaging、location_spatial_memory、scene_floorplan
