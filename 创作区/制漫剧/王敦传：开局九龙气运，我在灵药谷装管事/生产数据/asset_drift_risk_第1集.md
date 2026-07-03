# 出图前·物料漂移风险分（场景/道具/武器/特效·事前预测·只提示不阻断）

- episode: 第1集
- 高危物料 🔴 0 · 中危 🟡 6

| 资产 | 类型 | 风险 | 分 | 主驱动 |
|---|---|---|---|---|
| LOC_QI_PRISON_L7（LOC_QI_PRISON_L7） | 场景 | 🟡 medium | 30 | 禁漂项 2 个(+8)；结构/件数强锁(+8)；颜色/拖尾强锁(+8) |
| LOC_WASTE_DITCH_BLACK_RIVER（LOC_WASTE_DITCH_BLACK_RIVER） | 场景 | 🟡 medium | 30 | 禁漂项 2 个(+8)；结构/件数强锁(+8)；颜色/拖尾强锁(+8) |
| LOC_QI_CITY_LOCKDOWN（LOC_QI_CITY_LOCKDOWN） | 场景 | 🟡 medium | 30 | 禁漂项 2 个(+8)；结构/件数强锁(+8)；颜色/拖尾强锁(+8) |
| LOC_BLACK_RIVER_EXIT（LOC_BLACK_RIVER_EXIT） | 场景 | 🟡 medium | 30 | 禁漂项 2 个(+8)；结构/件数强锁(+8)；颜色/拖尾强锁(+8) |
| LOC_LINGYAO_VALLEY（LOC_LINGYAO_VALLEY） | 场景 | 🟡 medium | 30 | 禁漂项 2 个(+8)；结构/件数强锁(+8)；颜色/拖尾强锁(+8) |
| LOC_LINGYAO_VALLEY_GATE（LOC_LINGYAO_VALLEY_GATE） | 场景 | 🟡 medium | 30 | 禁漂项 2 个(+8)；结构/件数强锁(+8)；颜色/拖尾强锁(+8) |

## 🟡 LOC_QI_PRISON_L7（LOC_QI_PRISON_L7·场景）· 分 30
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。
- 颜色/拖尾强锁：写死 color_target(HSV) 与拖尾长度，避免跨镜窜色（特效最易漂）。

## 🟡 LOC_WASTE_DITCH_BLACK_RIVER（LOC_WASTE_DITCH_BLACK_RIVER·场景）· 分 30
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。
- 颜色/拖尾强锁：写死 color_target(HSV) 与拖尾长度，避免跨镜窜色（特效最易漂）。

## 🟡 LOC_QI_CITY_LOCKDOWN（LOC_QI_CITY_LOCKDOWN·场景）· 分 30
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。
- 颜色/拖尾强锁：写死 color_target(HSV) 与拖尾长度，避免跨镜窜色（特效最易漂）。

## 🟡 LOC_BLACK_RIVER_EXIT（LOC_BLACK_RIVER_EXIT·场景）· 分 30
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。
- 颜色/拖尾强锁：写死 color_target(HSV) 与拖尾长度，避免跨镜窜色（特效最易漂）。

## 🟡 LOC_LINGYAO_VALLEY（LOC_LINGYAO_VALLEY·场景）· 分 30
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。
- 颜色/拖尾强锁：写死 color_target(HSV) 与拖尾长度，避免跨镜窜色（特效最易漂）。

## 🟡 LOC_LINGYAO_VALLEY_GATE（LOC_LINGYAO_VALLEY_GATE·场景）· 分 30
- 结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。
- 颜色/拖尾强锁：写死 color_target(HSV) 与拖尾长度，避免跨镜窜色（特效最易漂）。


说明：本表是**出图前**的物料漂移预案——high/medium 物料按建议提前补多视图/锁结构/锁颜色/上状态机，比等审片 multimodal/场景 O2 事后报、再回头重出省返工。不阻断出图（落档闸门是 image_qc）。
