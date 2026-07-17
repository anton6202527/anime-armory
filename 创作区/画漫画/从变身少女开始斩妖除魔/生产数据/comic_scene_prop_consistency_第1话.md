# 漫画场景/道具一致性报告 — 第1话

- 生成时间：2026-07-17T05:36:16
- 结论：warn
- 场景锚：1 | 道具：2
- block/warn：0 / 11

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
| warn | vlm_judge_background_suspect | LOC_DESOLATE_WILDERNESS | P017 | VLM 并排判定低分/存疑：layout=2；本格转为水墨意象合成画面，荒原地平线与岩壁结构完全未继承，空间连续性断裂（疑为有意的心象插页） |
| warn | vlm_judge_background_suspect | LOC_DESOLATE_WILDERNESS | P018 | VLM 并排判定低分/存疑：layout=2、lighting=2；由墨色意象骤回深红实景，布局与光位无从继承，背景链路在此断开 |
| warn | vlm_judge_prop_suspect | PROP_HENGDAO_BROKEN | P018 | VLM 并排判定低分/存疑：structure=2；裴长青手中为完整修长弯刀，无断口无环首，与断横刀参考的断裂刀身结构不符 |
| warn | vlm_judge_prop_suspect | PROP_HENGDAO_BROKEN | P023 | VLM 并排判定低分/存疑：structure=2；姜月初握柄姿态合理，但刀身是弧形长弯刀且刃尖完整、护手金饰，与锚定的直刃环首断刀刃口崩缺不符 |
| warn | vlm_judge_prop_suspect | PROP_HENGDAO_BROKEN | P024 | VLM 并排判定低分/存疑：structure=2；手持弯刀完整无断口、无环首，与断横刀锚定不符（与P023同一把弯刀，批内自洽但对锚漂移） |
| warn | vlm_judge_prop_suspect | PROP_HENGDAO_BROKEN | P025 | VLM 并排判定低分/存疑：structure=2；变成直刃但配金色分段华丽剑柄，无环首无崩口无血渍缠布，规格材质与锚定断刀不符 |
| warn | vlm_judge_prop_suspect | PROP_HENGDAO_BROKEN | P026 | VLM 并排判定低分/存疑：structure=1；双手倒持的是对称双刃宝剑（卷云鎏金剑格），完全不是单刃环首断横刀 |
| warn | vlm_judge_prop_suspect | PROP_HENGDAO_BROKEN | P027 | VLM 并排判定低分/存疑：structure=2；手中为金柄弯刀刃形完整，与锚定直刃断刀结构不符 |
| warn | vlm_judge_prop_suspect | PROP_HENGDAO_BROKEN | P028 | VLM 并排判定低分/存疑：structure=1；刺下的仍是P026那柄鎏金双刃剑，非断横刀，属道具彻底替换 |

## 记录

- VLM 三轴裁决进度：93/93（生产数据/comic_vlm_judge_verdicts_第1话.json）。
