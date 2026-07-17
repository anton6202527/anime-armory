# 漫画角色一致性报告 — 第1话

- 生成时间：2026-07-17T21:36:38
- 结论：pass
- 角色数：9
- 出场绑定：76
- block/warn/info：0 / 0 / 4
- 并排复核图：`生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg`

## 记录

- CCIP 动漫身份 embedding 不可用（色彩指纹只是代理，换脸同色调会漏报）。建议在独立 venv 安装 dghs-imgutils（pip install dghs-imgutils）后重跑，获得阈值化的同角色判定（threshold=0.178）。
- VLM 并排判定任务包已刷新：生产数据/comic_vlm_judge_tasks_第1话.json（裁决 0/183）；由多模态 agent 看图执行并写回 verdict 文件。
- 已生成角色一致性并排复核图：生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg
- 已按 生产数据/character_consistency_acceptance_第1话.json 人审签收 4 条角色一致性 finding；原始机器 severity 保留在 machine_severity。

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_ABBOT_SHANGQING | 5 | 16 |
| CHAR_EMPEROR_RENZONG | 4 | 7 |
| CHAR_FAN_ZHONGYAN | 2 | 1 |
| CHAR_HONG_XIN | 5 | 36 |
| CHAR_MASTER_XUJING | 3 | 5 |
| CHAR_WEN_YANBO | 2 | 2 |
| CHAR_ZHAO_ZHE | 2 | 2 |
| MON_SNOW_SERPENT | 3 | 4 |
| MON_WHITE_TIGER | 3 | 3 |

## Findings

| severity | code | character | panel | artifact | reason |
|---|---|---|---|---|---|
| info | face_fingerprint_low | CHAR_WEN_YANBO | P004 | 出图/第1话/panels/P004.png | CHAR_WEN_YANBO face 指纹与参考图相似度偏低：score=0.451。这是色彩分布代理，需并排人审。 |
| info | hair_fingerprint_low | CHAR_WEN_YANBO | P004 | 出图/第1话/panels/P004.png | CHAR_WEN_YANBO hair 指纹与参考图相似度偏低：score=0.168。这是色彩分布代理，需并排人审。 |
| info | outfit_fingerprint_low | CHAR_WEN_YANBO | P004 | 出图/第1话/panels/P004.png | CHAR_WEN_YANBO outfit 指纹与参考图相似度偏低：score=0.329。这是色彩分布代理，需并排人审。 |
| info | hair_fingerprint_low | CHAR_WEN_YANBO | P005 | 出图/第1话/panels/P005.png | CHAR_WEN_YANBO hair 指纹与参考图相似度偏低：score=0.296。这是色彩分布代理，需并排人审。 |
