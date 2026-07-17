# 漫画场景/道具一致性报告 — 第2话

- 生成时间：2026-07-17T05:28:21
- 结论：warn
- 场景锚：1 | 道具：2
- block/warn：0 / 2

## 场景锚

| anchor | refs | panels | contact sheet |
|---|---:|---:|---|
| LOC_DESOLATE_WILDERNESS | 1 | 6 | 生产数据/qa_previews/第2话_scene_LOC_DESOLATE_WILDERNESS_sheet.jpg |

## 道具

| prop | refs | panels | contact sheet |
|---|---:|---:|---|
| OUTFIT_BASE | 0 | 6 | 生产数据/qa_previews/第2话_prop_OUTFIT_BASE_sheet.jpg |
| PROP_HENGDAO_BROKEN | 1 | 2 | 生产数据/qa_previews/第2话_prop_PROP_HENGDAO_BROKEN_sheet.jpg |

## Findings

| severity | code | subject | panel | reason |
|---|---|---|---|---|
| warn | prop_reference_missing | OUTFIT_BASE |  | OUTFIT_BASE 在本话出场（P001,P002,P003,P004,P005,P006）但没有参考图，无法并排核对同一物。 |
| warn | vlm_judge_background_suspect | LOC_DESOLATE_WILDERNESS | P006 | VLM 并排判定低分/存疑：verdict=suspect；姜左/虎右的轴线继承，但主光源从 P005 的画面左侧低日移到 P006 的中央偏左，且中部倒卧者由黑红绣袍变成粗麻褐袍，场景要素有实质变化需人工确认。 |

## 记录

- VLM 三轴裁决进度：19/19（生产数据/comic_vlm_judge_verdicts_第2话.json）。
