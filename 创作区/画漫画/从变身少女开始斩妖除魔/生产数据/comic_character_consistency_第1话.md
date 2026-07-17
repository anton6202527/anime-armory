# 漫画角色一致性报告 — 第1话

- 生成时间：2026-07-17T05:36:14
- 结论：warn
- 角色数：3
- 出场绑定：55
- block/warn/info：0 / 8 / 0
- 并排复核图：`生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg`

## 记录

- CCIP 动漫身份 embedding 不可用（色彩指纹只是代理，换脸同色调会漏报）。建议在独立 venv 安装 dghs-imgutils（pip install dghs-imgutils）后重跑，获得阈值化的同角色判定（threshold=0.178）。
- VLM 并排判定任务包已刷新：生产数据/comic_vlm_judge_tasks_第1话.json（裁决 93/93）；由多模态 agent 看图执行并写回 verdict 文件。
- 已生成角色一致性并排复核图：生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_JIANG_YUECHU | 6 | 25 |
| CHAR_PEI_CHANGQING | 3 | 21 |
| MON_TIGER_SHANSHEN | 5 | 9 |

## Findings

| severity | code | character | panel | artifact | reason |
|---|---|---|---|---|---|
| warn | vlm_judge_character_suspect | CHAR_JIANG_YUECHU | P003 | 出图/第1话/panels/P003.png | VLM 并排判定给出低分/存疑：verdict=suspect；P003 仅左下角失焦的灰白衣肩臂与苍白手掌入镜，无脸无发型可辨，无法确认是姜月初本人 |
| warn | vlm_judge_character_suspect | MON_TIGER_SHANSHEN | P015 | 出图/第1话/panels/P015.png | VLM 并排判定给出低分/存疑：face=2、outfit=1、build=2；背景右侧虎怪呈普通橙黄虎纹真虎毛色、通体无灰黑鳞甲、胸口黑洞金纹不可见，与registry DNA严重不符 |
| warn | vlm_judge_character_suspect | CHAR_JIANG_YUECHU | P016 | 出图/第1话/panels/P016.png | VLM 并排判定给出低分/存疑：verdict=suspect；左侧女子长发完全披散无高马尾束发，袍子比定妆整洁垂坠且背身看不到脸，认脸存疑 |
| warn | vlm_judge_character_suspect | MON_TIGER_SHANSHEN | P018 | 出图/第1话/panels/P018.png | VLM 并排判定给出低分/存疑：face=2、outfit=1；虎怪变为橙黄真虎头与毛色、全身无鳞甲改穿破布裤束绳腰带，仅胸口黑洞保留，严重漂移 |
| warn | vlm_judge_character_suspect | MON_TIGER_SHANSHEN | P019 | 出图/第1话/panels/P019.png | VLM 并排判定给出低分/存疑：face=2、outfit=1；橙黄虎头无灰黑鳞甲、下身破布裤，仅胸口黑洞存在，与虎山神DNA不符 |
| warn | vlm_judge_character_suspect | MON_TIGER_SHANSHEN | P020 | 出图/第1话/panels/P020.png | VLM 并排判定给出低分/存疑：outfit=2；虎首人身直立且胸口有黑洞，但通体橙黄普通虎纹、身穿破布长袍，完全没有registry要求的灰黑鳞甲与金纹 |
| warn | vlm_judge_character_suspect | MON_TIGER_SHANSHEN | P022 | 出图/第1话/panels/P022.png | VLM 并排判定给出低分/存疑：outfit=2；远景虎首人身直立、胸口黑洞清晰，但仍是破布长袍无鳞甲，毛色灰棕非定妆的灰白虎首配灰黑鳞甲 |
| warn | vlm_judge_character_suspect | MON_TIGER_SHANSHEN | P024 | 出图/第1话/panels/P024.png | VLM 并排判定给出低分/存疑：outfit=2；直立虎人胸口黑洞在，但橙黄普通虎头、赤膊配毛皮短裙，灰黑鳞甲完全缺失 |
