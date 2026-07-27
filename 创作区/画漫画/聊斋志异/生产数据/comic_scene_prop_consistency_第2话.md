# 漫画场景/道具一致性报告 — 第2话

- 生成时间：2026-07-24T20:06:47
- 结论：warn
- 场景锚：3 | 道具：3
- block/warn：0 / 3

## 场景锚

| anchor | refs | panels | contact sheet |
|---|---:|---:|---|
| LOC_HE_GARDEN | 1 | 5 | 生产数据/qa_previews/第2话_scene_LOC_HE_GARDEN_sheet.jpg |
| LOC_JIA_HOME | 1 | 4 | 生产数据/qa_previews/第2话_scene_LOC_JIA_HOME_sheet.jpg |
| LOC_MARKET_STREET | 1 | 7 | 生产数据/qa_previews/第2话_scene_LOC_MARKET_STREET_sheet.jpg |

## 道具

| prop | refs | panels | contact sheet |
|---|---:|---:|---|
| OUTFIT_BASE | 3 | 16 | 生产数据/qa_previews/第2话_prop_OUTFIT_BASE_sheet.jpg |
| PROP_FAKE_FOX_TAIL | 1 | 6 | 生产数据/qa_previews/第2话_prop_PROP_FAKE_FOX_TAIL_sheet.jpg |
| PROP_POISON_WINE | 1 | 6 | 生产数据/qa_previews/第2话_prop_PROP_POISON_WINE_sheet.jpg |

## Findings

| severity | code | subject | panel | reason |
|---|---|---|---|---|
| warn | vlm_judge_prop_suspect | PROP_FAKE_FOX_TAIL | P001 | VLM 并排判定低分/存疑：identity=2；PROP_FAKE_FOX_TAIL anchor is a grey-tan/black rope-bound bristly costume piece, but the panel shows a smooth bright orange-red tail with a distinct white tip tucked in the belt — a clear color/material mismatch, reading as a natural fox tail rather than the reference craft object. |
| warn | vlm_judge_prop_suspect | PROP_POISON_WINE | P010 | VLM 并排判定低分/存疑：identity=2；The reference sheet's defining poison material is a dark reddish-brown clumped powder, but the panel shows the girl pouring a light/white powder from the paper packet into the jar; the jar itself also lacks the reference's clear side loop-handle and reads wider-mouthed than the amphora-style reference jugs. |
| warn | vlm_judge_prop_suspect | PROP_FAKE_FOX_TAIL | P011 | VLM 并排判定低分/存疑：identity=2；Same drift as P001: the tail hanging from the child's hip is a smooth bright orange-red fox-colored tail with a white tip, not the grey/tan/black rope-bound bristly object shown in the PROP_FAKE_FOX_TAIL anchor. |

## 记录

- VLM 四轴裁决进度：73/73（生产数据/comic_vlm_judge_verdicts_第2话.json）。
