# 漫画场景/道具一致性报告 — 第2话

- 生成时间：2026-07-17T17:15:48
- 结论：warn
- 场景锚：6 | 道具：3
- block/warn：0 / 3

## 场景锚

| anchor | refs | panels | contact sheet |
|---|---:|---:|---|
| LOC_CAPITAL_PLAGUE_STREET | 1 | 3 | 生产数据/qa_previews/第2话_scene_LOC_CAPITAL_PLAGUE_STREET_sheet.jpg |
| LOC_FUMO_HALL_EXTERIOR | 1 | 16 | 生产数据/qa_previews/第2话_scene_LOC_FUMO_HALL_EXTERIOR_sheet.jpg |
| LOC_FUMO_HALL_INTERIOR | 1 | 10 | 生产数据/qa_previews/第2话_scene_LOC_FUMO_HALL_INTERIOR_sheet.jpg |
| LOC_ROAD_TO_LONGHUSHAN | 1 | 4 | 生产数据/qa_previews/第2话_scene_LOC_ROAD_TO_LONGHUSHAN_sheet.jpg |
| LOC_SHANGQING_PALACE | 1 | 2 | 生产数据/qa_previews/第2话_scene_LOC_SHANGQING_PALACE_sheet.jpg |
| LOC_ZICHEN_HALL | 1 | 7 | 生产数据/qa_previews/第2话_scene_LOC_ZICHEN_HALL_sheet.jpg |

## 道具

| prop | refs | panels | contact sheet |
|---|---:|---:|---|
| OUTFIT_BASE | 0 | 15 | 生产数据/qa_previews/第2话_prop_OUTFIT_BASE_sheet.jpg |
| OUTFIT_COURT_ENVOY | 0 | 23 | 生产数据/qa_previews/第2话_prop_OUTFIT_COURT_ENVOY_sheet.jpg |
| VFX_108_STARLIGHTS | 0 | 10 | 生产数据/qa_previews/第2话_prop_VFX_108_STARLIGHTS_sheet.jpg |

## Findings

| severity | code | subject | panel | reason |
|---|---|---|---|---|
| warn | prop_reference_missing | OUTFIT_BASE |  | OUTFIT_BASE 在本话出场（P002,P003,P011,P012,P018,P022,P024,P026）但没有参考图，无法并排核对同一物。 |
| warn | prop_reference_missing | OUTFIT_COURT_ENVOY |  | OUTFIT_COURT_ENVOY 在本话出场（P002,P003,P011,P012,P014,P017,P018,P019）但没有参考图，无法并排核对同一物。 |
| warn | prop_reference_missing | VFX_108_STARLIGHTS |  | VFX_108_STARLIGHTS 在本话出场（P001,P006,P007,P008,P009,P010,P013,P015）但没有参考图，无法并排核对同一物。 |

## 记录

- VLM 三轴裁决进度：0/74（生产数据/comic_vlm_judge_verdicts_第2话.json）。
