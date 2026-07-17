# 漫画角色一致性报告 — 第1话

- 生成时间：2026-07-17T07:41:57
- 结论：warn
- 角色数：3
- 出场绑定：57
- block/warn/info：0 / 15 / 0
- 并排复核图：`生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg`

## 记录

- VLM 并排判定任务包已刷新：生产数据/comic_vlm_judge_tasks_第1话.json（裁决 95/95）；由多模态 agent 看图执行并写回 verdict 文件。
- 已生成角色一致性并排复核图：生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_JIANG_YUECHU | 6 | 25 |
| CHAR_PEI_CHANGQING | 3 | 21 |
| MON_TIGER_SHANSHEN | 5 | 11 |

## Findings

| severity | code | character | panel | artifact | reason |
|---|---|---|---|---|---|
| warn | ccip_identity_low | CHAR_JIANG_YUECHU | P003 | 出图/第1话/panels/P003.png | CHAR_JIANG_YUECHU CCIP 身份距离 0.2279 超过同角色阈值 0.178，疑似换脸/不同角色。 |
| warn | ccip_identity_low | CHAR_JIANG_YUECHU | P004 | 出图/第1话/panels/P004.png | CHAR_JIANG_YUECHU CCIP 身份距离 0.2595 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | CHAR_JIANG_YUECHU | P016 | 出图/第1话/panels/P016.png | CHAR_JIANG_YUECHU CCIP 身份距离 0.2363 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | CHAR_PEI_CHANGQING | P016 | 出图/第1话/panels/P016.png | CHAR_PEI_CHANGQING CCIP 身份距离 0.1922 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | CHAR_PEI_CHANGQING | P026 | 出图/第1话/panels/P026.png | CHAR_PEI_CHANGQING CCIP 身份距离 0.233 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | MON_TIGER_SHANSHEN | P015 | 出图/第1话/panels/P015.png | MON_TIGER_SHANSHEN CCIP 身份距离 0.2323 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | MON_TIGER_SHANSHEN | P018 | 出图/第1话/panels/P018.png | MON_TIGER_SHANSHEN CCIP 身份距离 0.2001 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | MON_TIGER_SHANSHEN | P019 | 出图/第1话/panels/P019.png | MON_TIGER_SHANSHEN CCIP 身份距离 0.2405 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | MON_TIGER_SHANSHEN | P020 | 出图/第1话/panels/P020.png | MON_TIGER_SHANSHEN CCIP 身份距离 0.2465 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | MON_TIGER_SHANSHEN | P022 | 出图/第1话/panels/P022.png | MON_TIGER_SHANSHEN CCIP 身份距离 0.2292 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | MON_TIGER_SHANSHEN | P024 | 出图/第1话/panels/P024.png | MON_TIGER_SHANSHEN CCIP 身份距离 0.2238 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | MON_TIGER_SHANSHEN | P025 | 出图/第1话/panels/P025.png | MON_TIGER_SHANSHEN CCIP 身份距离 0.2163 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | MON_TIGER_SHANSHEN | P026 | 出图/第1话/panels/P026.png | MON_TIGER_SHANSHEN CCIP 身份距离 0.3421 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | vlm_judge_character_suspect | CHAR_JIANG_YUECHU | P003 | 出图/第1话/panels/P003.png | VLM 并排判定给出低分/存疑：verdict=suspect；P003 仅左下角失焦的灰白衣肩臂与苍白手掌入镜，无脸无发型可辨，无法确认是姜月初本人 |
| warn | vlm_judge_character_suspect | CHAR_JIANG_YUECHU | P016 | 出图/第1话/panels/P016.png | VLM 并排判定给出低分/存疑：verdict=suspect；左侧女子长发完全披散无高马尾束发，袍子比定妆整洁垂坠且背身看不到脸，认脸存疑 |
