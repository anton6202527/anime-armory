# 漫画场景/道具一致性报告 — 第1话

- 生成时间：2026-07-24T08:20:24
- 结论：warn
- 场景锚：2 | 道具：1
- block/warn：0 / 8

## 场景锚

| anchor | refs | panels | contact sheet |
|---|---:|---:|---|
| LOC_MARKET_TEMPLE | 1 | 3 | 生产数据/qa_previews/第1话_scene_LOC_MARKET_TEMPLE_sheet.jpg |
| LOC_WANG_COURTYARD | 1 | 13 | 生产数据/qa_previews/第1话_scene_LOC_WANG_COURTYARD_sheet.jpg |

## 道具

| prop | refs | panels | contact sheet |
|---|---:|---:|---|
| OUTFIT_BASE | 3 | 16 | 生产数据/qa_previews/第1话_prop_OUTFIT_BASE_sheet.jpg |

## Findings

| severity | code | subject | panel | reason |
|---|---|---|---|---|
| warn | vlm_judge_location_suspect | LOC_WANG_COURTYARD | P002 | VLM 并排判定低分/存疑：structure=1、materials=2；Anchor is a private brick courtyard residence with tiled roof, lattice windows and a canal; panel P002 is an open-air market street with awning stalls and a distant city gate tower — a different building type/location entirely, not merely a different camera angle. |
| warn | vlm_judge_location_suspect | LOC_MARKET_TEMPLE | P006 | VLM 并排判定低分/存疑：structure=2；Anchor's landmark is a thick city-wall gate tower with a carved archway; panel P006 instead shows a freestanding temple gate on a stepped platform flanked by stone lions — a different gate structure, not the same building re-angled. |
| warn | vlm_judge_background_suspect | LOC_WANG_COURTYARD | P002 | VLM 并排判定低分/存疑：layout=1、lighting=1、axis=2；P001 is a night-time interior room (monster painting a portrait at a desk by lamplight); P002 is a daytime outdoor market street — no shared layout, light direction, or axis between the two panels. |
| warn | vlm_judge_background_suspect | LOC_WANG_COURTYARD | P003 | VLM 并排判定低分/存疑：layout=2、lighting=2、axis=2；P002为雨天集市街道（远景城门楼、摊棚苫布、泥泞道路，风格更接近LOC_MARKET_TEMPLE而非王家院落），P003为室内厅堂（暗色木案、油灯、软榻），空间布局与光源冷暖完全不同，怀疑该背景延续性标注与LOC_WANG_COURTYARD锚点不符。 |
| warn | vlm_judge_background_suspect | LOC_MARKET_TEMPLE | P006 | VLM 并排判定低分/存疑：lighting=2；P004 is overcast daylight with the gate tower distant on the right; P006 is full night with a different-looking temple gate now in the left foreground — lighting flips from day to night and the landmark structure itself differs, not just camera position. |
| warn | vlm_judge_background_suspect | LOC_WANG_COURTYARD | P007 | VLM 并排判定低分/存疑：layout=2、axis=2；P005为书房场景（书架、烛台、条案，男主在门外窥视），P007为卧房场景（床榻、床头柜），两格家具配置与房间功能完全不同，虽同为暖色夜间光源，但门窗/家具方位无法视为同一镜头的延续，怀疑该背景延续性标注有误。 |
| warn | vlm_judge_background_suspect | LOC_WANG_COURTYARD | P009 | VLM 并排判定低分/存疑：layout=2、lighting=2、axis=2；P008 is an enclosed dim interior bedroom (bed, hanging curtain, small candlelit side table) while P009 is a bright open exterior brick courtyard/alley with tiled roofs — this is not a camera move within one room but a jump to an entirely different physical space, so layout/lighting/axis do not carry over at all. |
| warn | vlm_judge_background_suspect | LOC_WANG_COURTYARD | P016 | VLM 并排判定低分/存疑：layout=2、axis=2；P015中深色书架/柜位于画面左侧、窗棂居中偏右；P016中同款书架却出现在画面右侧、窗棂居中偏左，家具左右位置发生镜像翻转而非合理的反打机位，怀疑场景结构被镜像/翻转。 |

## 记录

- VLM 四轴裁决进度：62/62（生产数据/comic_vlm_judge_verdicts_第1话.json）。
