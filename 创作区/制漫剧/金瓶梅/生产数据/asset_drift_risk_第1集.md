# 出图前·物料漂移风险分（场景/道具/武器/特效·事前预测·只提示不阻断）

- episode: 第1集
- 高危物料 🔴 1 · 中危 🟡 23

| 资产 | 类型 | 风险 | 分 | 主驱动 |
|---|---|---|---|---|
| 武大家楼屋雪夜（LOC_WUDA_HOME） | 场景 | 🔴 high | 54 | 本集出镜 8 次(+24)；禁漂项 2 个(+8)；结构/件数强锁(+8) |
| 炭盆（PROP_BRAZIER） | 道具 | 🟡 medium | 46 | 禁漂项 5 个(+20)；本集出镜 4 次(+12)；结构/件数强锁(+8) |
| 阳谷街面与武大家楼窗（LOC_YANGGU_STREET） | 场景 | 🟡 medium | 45 | 本集出镜 5 次(+15)；禁漂项 2 个(+8)；结构/件数强锁(+8) |
| 门闩（PROP_DOOR_LATCH） | 道具 | 🟡 medium | 43 | 禁漂项 6 个(+20)；本集出镜 3 次(+9)；结构/件数强锁(+8) |
| 梢棒（PROP_QUARTERSTAFF） | 道具 | 🟡 medium | 40 | 禁漂项 5 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| 半杯酒（PROP_WINE_CUP） | 道具 | 🟡 medium | 40 | 禁漂项 5 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| 景阳冈夜间空地（LOC_JINGYANGGANG） | 场景 | 🟡 medium | 39 | 本集出镜 3 次(+9)；禁漂项 2 个(+8)；结构/件数强锁(+8) |
| 都头腰牌（PROP_BADGE） | 道具 | 🟡 medium | 37 | 禁漂项 6 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| 公文（PROP_OFFICIAL_DOC） | 道具 | 🟡 medium | 37 | 禁漂项 5 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| 叉竿（PROP_CURTAIN_FORK） | 道具 | 🟡 medium | 37 | 禁漂项 5 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| REWARD SILVER（PROP_REWARD_SILVER） | 道具 | 🟡 medium | 34 | 禁漂项 6 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| 炊饼担（PROP_CAKE_POLE） | 道具 | 🟡 medium | 34 | 禁漂项 5 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| WINDOW LATTICE（PROP_WINDOW_LATTICE） | 道具 | 🟡 medium | 34 | 禁漂项 6 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| STAIR RAIL（PROP_STAIR_RAIL） | 道具 | 🟡 medium | 34 | 禁漂项 6 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| DINING TABLE（PROP_DINING_TABLE） | 道具 | 🟡 medium | 34 | 禁漂项 6 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| TEA CUP（PROP_TEA_CUP） | 道具 | 🟡 medium | 34 | 禁漂项 6 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| DOORFRAME（PROP_DOORFRAME） | 道具 | 🟡 medium | 34 | 禁漂项 6 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| SPILLED WINE（PROP_SPILLED_WINE） | 道具 | 🟡 medium | 34 | 禁漂项 5 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| 素布行李（PROP_LUGGAGE） | 道具 | 🟡 medium | 34 | 禁漂项 5 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| 武大家木门（PROP_DOOR） | 道具 | 🟡 medium | 34 | 禁漂项 8 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| 东京礼担（PROP_GIFT_LOAD） | 道具 | 🟡 medium | 34 | 禁漂项 5 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| WINDOW CURTAIN（PROP_WINDOW_CURTAIN） | 道具 | 🟡 medium | 34 | 禁漂项 5 个(+20)；结构/件数强锁(+8)；复用跨度(+6) |
| 县衙案厅（LOC_COUNTY_YAMEN） | 场景 | 🟡 medium | 33 | 禁漂项 2 个(+8)；结构/件数强锁(+8)；颜色/拖尾强锁(+8) |
| 阳谷城门清晨（LOC_CITY_GATE） | 场景 | 🟡 medium | 33 | 禁漂项 2 个(+8)；结构/件数强锁(+8)；颜色/拖尾强锁(+8) |

## 🔴 武大家楼屋雪夜（LOC_WUDA_HOME·场景）· 分 54
- 本集高频场景：登记 scene_atlas.base_views（G-I2 场景多机位锁：front + 反打/侧机位 ready），锁 layout/axis/light_anchor，反打不越轴（production 核心 LOC 缺则 gate BLOCK）。
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。
- 颜色/拖尾强锁：写死 color_target(HSV) 与拖尾长度，避免跨镜窜色（特效最易漂）。
- 风险 high：出图后重点看 image_qc 道具/特效 P2 + 场景 O2 初筛，必要时上 asset 状态机结构化 lifecycle（防回退）。

## 🟡 炭盆（PROP_BRAZIER·道具）· 分 46
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 阳谷街面与武大家楼窗（LOC_YANGGU_STREET·场景）· 分 45
- 本集高频场景：登记 scene_atlas.base_views（G-I2 场景多机位锁：front + 反打/侧机位 ready），锁 layout/axis/light_anchor，反打不越轴（production 核心 LOC 缺则 gate BLOCK）。
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。
- 颜色/拖尾强锁：写死 color_target(HSV) 与拖尾长度，避免跨镜窜色（特效最易漂）。

## 🟡 门闩（PROP_DOOR_LATCH·道具）· 分 43
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 梢棒（PROP_QUARTERSTAFF·道具）· 分 40
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 半杯酒（PROP_WINE_CUP·道具）· 分 40
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 景阳冈夜间空地（LOC_JINGYANGGANG·场景）· 分 39
- 本集高频场景：登记 scene_atlas.base_views（G-I2 场景多机位锁：front + 反打/侧机位 ready），锁 layout/axis/light_anchor，反打不越轴（production 核心 LOC 缺则 gate BLOCK）。
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。
- 颜色/拖尾强锁：写死 color_target(HSV) 与拖尾长度，避免跨镜窜色（特效最易漂）。

## 🟡 都头腰牌（PROP_BADGE·道具）· 分 37
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 公文（PROP_OFFICIAL_DOC·道具）· 分 37
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 叉竿（PROP_CURTAIN_FORK·道具）· 分 37
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 REWARD SILVER（PROP_REWARD_SILVER·道具）· 分 34
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 炊饼担（PROP_CAKE_POLE·道具）· 分 34
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 WINDOW LATTICE（PROP_WINDOW_LATTICE·道具）· 分 34
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 STAIR RAIL（PROP_STAIR_RAIL·道具）· 分 34
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 DINING TABLE（PROP_DINING_TABLE·道具）· 分 34
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 TEA CUP（PROP_TEA_CUP·道具）· 分 34
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 DOORFRAME（PROP_DOORFRAME·道具）· 分 34
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 SPILLED WINE（PROP_SPILLED_WINE·道具）· 分 34
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 素布行李（PROP_LUGGAGE·道具）· 分 34
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 武大家木门（PROP_DOOR·道具）· 分 34
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 东京礼担（PROP_GIFT_LOAD·道具）· 分 34
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 WINDOW CURTAIN（PROP_WINDOW_CURTAIN·道具）· 分 34
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。

## 🟡 县衙案厅（LOC_COUNTY_YAMEN·场景）· 分 33
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。
- 颜色/拖尾强锁：写死 color_target(HSV) 与拖尾长度，避免跨镜窜色（特效最易漂）。

## 🟡 阳谷城门清晨（LOC_CITY_GATE·场景）· 分 33
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。
- 颜色/拖尾强锁：写死 color_target(HSV) 与拖尾长度，避免跨镜窜色（特效最易漂）。


说明：本表是**出图前**的物料漂移预案——high/medium 物料按建议提前补多视图/锁结构/锁颜色/上状态机，比等审片 multimodal/场景 O2 事后报、再回头重出省返工。不阻断出图（落档闸门是 image_qc）。
