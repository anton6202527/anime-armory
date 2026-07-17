# 漫画场景/道具一致性报告 — 第1话

- 生成时间：2026-07-17T10:52:44
- 结论：warn
- 场景锚：7 | 道具：9
- block/warn：0 / 5

## 场景锚

| anchor | refs | panels | contact sheet |
|---|---:|---:|---|
| LOC_CAPITAL_PLAGUE_STREET | 1 | 1 | 生产数据/qa_previews/第1话_scene_LOC_CAPITAL_PLAGUE_STREET_sheet.jpg |
| LOC_FUMO_HALL_EXTERIOR | 1 | 3 | 生产数据/qa_previews/第1话_scene_LOC_FUMO_HALL_EXTERIOR_sheet.jpg |
| LOC_FUMO_HALL_INTERIOR | 1 | 3 | 生产数据/qa_previews/第1话_scene_LOC_FUMO_HALL_INTERIOR_sheet.jpg |
| LOC_LONGHUSHAN_PATH | 1 | 18 | 生产数据/qa_previews/第1话_scene_LOC_LONGHUSHAN_PATH_sheet.jpg |
| LOC_ROAD_TO_LONGHUSHAN | 1 | 1 | 生产数据/qa_previews/第1话_scene_LOC_ROAD_TO_LONGHUSHAN_sheet.jpg |
| LOC_SHANGQING_PALACE | 1 | 13 | 生产数据/qa_previews/第1话_scene_LOC_SHANGQING_PALACE_sheet.jpg |
| LOC_ZICHEN_HALL | 1 | 9 | 生产数据/qa_previews/第1话_scene_LOC_ZICHEN_HALL_sheet.jpg |

## 道具

| prop | refs | panels | contact sheet |
|---|---:|---:|---|
| OUTFIT_BASE | 0 | 30 | 生产数据/qa_previews/第1话_prop_OUTFIT_BASE_sheet.jpg |
| OUTFIT_COURT_ENVOY | 0 | 13 | 生产数据/qa_previews/第1话_prop_OUTFIT_COURT_ENVOY_sheet.jpg |
| OUTFIT_HERDBOY | 0 | 5 | 生产数据/qa_previews/第1话_prop_OUTFIT_HERDBOY_sheet.jpg |
| OUTFIT_MOUNTAIN_PLAIN | 0 | 23 | 生产数据/qa_previews/第1话_prop_OUTFIT_MOUNTAIN_PLAIN_sheet.jpg |
| PROP_FUMO_SEALS | 1 | 5 | 生产数据/qa_previews/第1话_prop_PROP_FUMO_SEALS_sheet.jpg |
| PROP_IMPERIAL_EDICT | 1 | 30 | 生产数据/qa_previews/第1话_prop_PROP_IMPERIAL_EDICT_sheet.jpg |
| PROP_SILVER_CENSER | 1 | 28 | 生产数据/qa_previews/第1话_prop_PROP_SILVER_CENSER_sheet.jpg |
| PROP_STONE_STELE | 1 | 3 | 生产数据/qa_previews/第1话_prop_PROP_STONE_STELE_sheet.jpg |
| VFX_108_STARLIGHTS | 0 | 2 | 生产数据/qa_previews/第1话_prop_VFX_108_STARLIGHTS_sheet.jpg |

## Findings

| severity | code | subject | panel | reason |
|---|---|---|---|---|
| warn | prop_reference_missing | OUTFIT_BASE |  | OUTFIT_BASE 在本话出场（P003,P004,P005,P006,P008,P009,P010,P012）但没有参考图，无法并排核对同一物。 |
| warn | prop_reference_missing | OUTFIT_COURT_ENVOY |  | OUTFIT_COURT_ENVOY 在本话出场（P010,P011,P012,P016,P017,P018,P042,P043）但没有参考图，无法并排核对同一物。 |
| warn | prop_reference_missing | OUTFIT_HERDBOY |  | OUTFIT_HERDBOY 在本话出场（P034,P035,P036,P037,P038）但没有参考图，无法并排核对同一物。 |
| warn | prop_reference_missing | OUTFIT_MOUNTAIN_PLAIN |  | OUTFIT_MOUNTAIN_PLAIN 在本话出场（P019,P020,P021,P022,P023,P024,P025,P026）但没有参考图，无法并排核对同一物。 |
| warn | prop_reference_missing | VFX_108_STARLIGHTS |  | VFX_108_STARLIGHTS 在本话出场（P047,P048）但没有参考图，无法并排核对同一物。 |

## 记录

- VLM 三轴裁决进度：0/183（生产数据/comic_vlm_judge_verdicts_第1话.json）。
