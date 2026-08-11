# n2d Series Bible

- kind: n2d_series_bible
- episodes: 10
- hooks: 6
- threads: 8

## 真值源
- global_style: 设定库/global_style.md
- 角色圣经: 未登记
- setup_payoff_ledger: 设定库/setup_payoff_ledger.json
- narrative_state_ledger: 设定库/narrative_state_ledger.json
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
| 第1集 | 15 | CHAR_WUSONG/酒后战损态、BEAST_TIGER/扑击态、CHAR_WUSONG/打虎后至都头态、BEAST_TIGER/战败态、CROWD_HUNTERS/群像、CHAR_WUDA/卖饼劳作态、CHAR_PANJINLIAN/楼窗压抑态、CHAR_WUSONG/都头态、CHAR_WUDA/惊喜态、CHAR_PANJINLIAN/初见审视态、CHAR_WUSONG/克制常服态、CHAR_PANJINLIAN/试探态、CHAR_WUDA/在场后转画外、CHAR_WUSONG/克制警觉态、CHAR_PANJINLIAN/主动试探态、CHAR_WUDA/出门后画外、CHAR_PANJINLIAN/急切试探态、CHAR_WUSONG/愤怒克制态、CHAR_PANJINLIAN/越界后羞怒态、CHAR_WUDA/迟疑态、CHAR_PANJINLIAN/表演受害态、CHAR_WUSONG/沉默画外、CHAR_WUSONG/搬离态、CHAR_WUDA/慌乱态、CHAR_PANJINLIAN/沉默后景、CHAR_WUDA/门内态、CHAR_PANJINLIAN/门内态、CHAR_WUSONG/都头公务态、CHAR_MAGISTRATE/知县态、CHAR_WUSONG/出城行装态、CHAR_WUDA/送别态、CHAR_PANJINLIAN/楼窗画外、CHAR_WUSONG/出城远景、CHAR_PANJINLIAN/隔帘态、CHAR_XIMENQING/未揭面剪影态 | LOC_JINGYANGGANG、PROP_QUARTERSTAFF、PROP_BADGE、PROP_REWARD_SILVER、LOC_YANGGU_STREET、PROP_CAKE_POLE、PROP_WINDOW_LATTICE、LOC_WUDA_HOME、PROP_STAIR_RAIL、PROP_DINING_TABLE、PROP_DOORFRAME、PROP_TEA_CUP、PROP_BRAZIER、PROP_DOOR_LATCH、PROP_WINE_CUP、PROP_SPILLED_WINE、PROP_LUGGAGE、PROP_DOOR、PROP_GIFT_LOAD、PROP_OFFICIAL_DOC、LOC_COUNTY_YAMEN、PROP_CURTAIN_FORK、PROP_WINDOW_CURTAIN、LOC_CITY_GATE | 6 | 8 |
| 第2集 | 0 | - | - | 0 | 0 |
| 第3集 | 0 | - | - | 0 | 0 |
| 第4集 | 0 | - | - | 0 | 0 |
| 第5集 | 0 | - | - | 0 | 0 |
| 第6集 | 0 | - | - | 0 | 0 |
| 第7集 | 0 | - | - | 0 | 0 |
| 第8集 | 0 | - | - | 0 | 0 |
| 第9集 | 0 | - | - | 0 | 0 |
| 第10集 | 0 | - | - | 0 | 0 |

## 角色表演签名

| 角色 | 形态 | performance_signature | signature_equipment |
|---|---|---|---|

## Findings
- WARN [missing_identity_registry] 缺 identity_registry.json，series_bible 只能建立叙事层，无法汇总角色 DNA。
- INFO [missing_asset_registry] 缺 asset_registry.json；若尚未进入出图阶段可接受，出图前需补。
- INFO [episode_missing_storyboard] 部分集缺 storyboard.json：第2集、第3集、第4集、第5集、第6集、第7集、第8集、第9集
- INFO [series_layers_not_registered] 以下剧级层尚未登记：ambient_map、ui_asset_registry、translation_glossary、series_packaging、location_spatial_memory
