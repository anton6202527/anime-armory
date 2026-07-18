# 漫画角色一致性报告 — 第1话

- 生成时间：2026-07-18T17:09:51
- 结论：pass
- 角色数：5
- 出场绑定：74
- block/warn/info：0 / 0 / 14
- 并排复核图：`生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg`

## 记录

- CCIP 动漫身份 embedding 不可用（色彩指纹只是代理，换脸同色调会漏报）。建议在独立 venv 安装 dghs-imgutils（pip install dghs-imgutils）后重跑，获得阈值化的同角色判定（threshold=0.178）。
- VLM 并排判定任务包已刷新：生产数据/comic_vlm_judge_tasks_第1话.json（裁决 0/147）；由多模态 agent 看图执行并写回 verdict 文件。
- 已生成角色一致性并排复核图：生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg
- 已按 生产数据/character_consistency_acceptance_第1话.json 人审签收 14 条角色一致性 finding；原始机器 severity 保留在 machine_severity。

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_PAN_JINLIAN | 5 | 25 |
| CHAR_WANG_PO | 2 | 2 |
| CHAR_WU_DA | 3 | 17 |
| CHAR_WU_SONG | 5 | 25 |
| MON_JINGYANG_TIGER | 3 | 5 |

## Findings

| severity | code | character | panel | artifact | reason |
|---|---|---|---|---|---|
| info | hair_fingerprint_low | CHAR_PAN_JINLIAN | P014 | 出图/第1话/panels/P014.png | CHAR_PAN_JINLIAN hair 指纹与参考图相似度偏低：score=0.444。这是色彩分布代理，需并排人审。 |
| info | hair_fingerprint_low | CHAR_PAN_JINLIAN | P029 | 出图/第1话/panels/P029.png | CHAR_PAN_JINLIAN hair 指纹与参考图相似度偏低：score=0.368。这是色彩分布代理，需并排人审。 |
| info | hair_fingerprint_low | CHAR_PAN_JINLIAN | P036 | 出图/第1话/panels/P036.png | CHAR_PAN_JINLIAN hair 指纹与参考图相似度偏低：score=0.445。这是色彩分布代理，需并排人审。 |
| info | hair_fingerprint_low | CHAR_PAN_JINLIAN | P039 | 出图/第1话/panels/P039.png | CHAR_PAN_JINLIAN hair 指纹与参考图相似度偏低：score=0.346。这是色彩分布代理，需并排人审。 |
| info | face_fingerprint_low | CHAR_WU_DA | P039 | 出图/第1话/panels/P039.png | CHAR_WU_DA face 指纹与参考图相似度偏低：score=0.486。这是色彩分布代理，需并排人审。 |
| info | hair_fingerprint_low | CHAR_WU_DA | P039 | 出图/第1话/panels/P039.png | CHAR_WU_DA hair 指纹与参考图相似度偏低：score=0.335。这是色彩分布代理，需并排人审。 |
| info | face_fingerprint_low | CHAR_WU_DA | P040 | 出图/第1话/panels/P040.png | CHAR_WU_DA face 指纹与参考图相似度偏低：score=0.367。这是色彩分布代理，需并排人审。 |
| info | hair_fingerprint_low | CHAR_WU_DA | P040 | 出图/第1话/panels/P040.png | CHAR_WU_DA hair 指纹与参考图相似度偏低：score=0.318。这是色彩分布代理，需并排人审。 |
| info | hair_fingerprint_low | CHAR_WU_SONG | P003 | 出图/第1话/panels/P003.png | CHAR_WU_SONG hair 指纹与参考图相似度偏低：score=0.414。这是色彩分布代理，需并排人审。 |
| info | hair_fingerprint_low | CHAR_WU_SONG | P005 | 出图/第1话/panels/P005.png | CHAR_WU_SONG hair 指纹与参考图相似度偏低：score=0.441。这是色彩分布代理，需并排人审。 |
| info | hair_fingerprint_low | CHAR_WU_SONG | P029 | 出图/第1话/panels/P029.png | CHAR_WU_SONG hair 指纹与参考图相似度偏低：score=0.448。这是色彩分布代理，需并排人审。 |
| info | hair_fingerprint_low | MON_JINGYANG_TIGER | P006 | 出图/第1话/panels/P006.png | MON_JINGYANG_TIGER hair 指纹与参考图相似度偏低：score=0.386。这是色彩分布代理，需并排人审。 |
| info | hair_fingerprint_low | MON_JINGYANG_TIGER | P008 | 出图/第1话/panels/P008.png | MON_JINGYANG_TIGER hair 指纹与参考图相似度偏低：score=0.410。这是色彩分布代理，需并排人审。 |
| info | hair_fingerprint_low | MON_JINGYANG_TIGER | P009 | 出图/第1话/panels/P009.png | MON_JINGYANG_TIGER hair 指纹与参考图相似度偏低：score=0.385。这是色彩分布代理，需并排人审。 |
