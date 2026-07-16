# 漫画场景/道具一致性报告 — 第1话

- 生成时间：2026-07-16T01:31:56
- 结论：warn
- 场景锚：1 | 道具：2
- block/warn：0 / 2

## 场景锚

| anchor | refs | panels | contact sheet |
|---|---:|---:|---|
| LOC_DESOLATE_WILDERNESS | 1 | 28 | 生产数据/qa_previews/第1话_scene_LOC_DESOLATE_WILDERNESS_sheet.jpg |

## 道具

| prop | refs | panels | contact sheet |
|---|---:|---:|---|
| OUTFIT_BASE | 0 | 27 | 生产数据/qa_previews/第1话_prop_OUTFIT_BASE_sheet.jpg |
| PROP_HENGDAO_BROKEN | 1 | 11 | 生产数据/qa_previews/第1话_prop_PROP_HENGDAO_BROKEN_sheet.jpg |

## Findings

| severity | code | subject | panel | reason |
|---|---|---|---|---|
| warn | scene_layout_outlier | LOC_DESOLATE_WILDERNESS | P021 | P021 的布局指纹在场景锚 LOC_DESOLATE_WILDERNESS 组内离群（0.826 < 中位 0.928 - 0.1）。机位变化合法，但整格结构换掉（门窗家具错位/常驻物件消失）需要人审。 |
| warn | prop_reference_missing | OUTFIT_BASE |  | OUTFIT_BASE 在本话出场（P002,P003,P004,P005,P006,P007,P008,P009）但没有参考图，无法并排核对同一物。 |

## 记录

- VLM 三轴裁决进度：0/93（生产数据/comic_vlm_judge_verdicts_第1话.json）。
