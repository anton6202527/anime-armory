# 漫画角色一致性报告 — 第2话

- 生成时间：2026-07-22T15:24:28
- 结论：warn
- 角色数：5
- 出场绑定：32
- block/warn/info：0 / 18 / 0
- 并排复核图：`生产数据/qa_previews/第2话_character_consistency_contact_sheet.jpg`

## 记录

- VLM 并排判定任务包已刷新：生产数据/comic_vlm_judge_tasks_第2话.json（裁决 0/57）；由多模态 agent 看图执行并写回 verdict 文件。
- 已生成角色一致性并排复核图：生产数据/qa_previews/第2话_character_consistency_contact_sheet.jpg

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_JIA_CHILD | 5 | 16 |
| CHAR_JIA_FATHER | 3 | 2 |
| CHAR_JIA_MOTHER | 3 | 2 |
| MON_FOX_BROTHERS | 2 | 4 |
| MON_FOX_SERVANT | 2 | 8 |

## Findings

| severity | code | character | panel | artifact | reason |
|---|---|---|---|---|---|
| warn | ccip_identity_low | CHAR_JIA_CHILD | P007 | 出图/第2话/panels/P007.png | CHAR_JIA_CHILD CCIP 身份距离 0.2126 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | hair_fingerprint_low | CHAR_JIA_CHILD | P007 | 出图/第2话/panels/P007.png | CHAR_JIA_CHILD hair 指纹与参考图相似度偏低：score=0.341。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_JIA_CHILD | P015 | 出图/第2话/panels/P015.png | CHAR_JIA_CHILD hair 指纹与参考图相似度偏低：score=0.294。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_JIA_FATHER | P006 | 出图/第2话/panels/P006.png | CHAR_JIA_FATHER hair 指纹与参考图相似度偏低：score=0.450。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_JIA_MOTHER | P002 | 出图/第2话/panels/P002.png | CHAR_JIA_MOTHER hair 指纹与参考图相似度偏低：score=0.431。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | MON_FOX_BROTHERS | P004 | 出图/第2话/panels/P004.png | MON_FOX_BROTHERS face 指纹与参考图相似度偏低：score=0.491。这是色彩分布代理，需并排人审。 |
| warn | ccip_identity_low | MON_FOX_BROTHERS | P007 | 出图/第2话/panels/P007.png | MON_FOX_BROTHERS CCIP 身份距离 0.2107 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | face_fingerprint_low | MON_FOX_BROTHERS | P007 | 出图/第2话/panels/P007.png | MON_FOX_BROTHERS face 指纹与参考图相似度偏低：score=0.392。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | MON_FOX_BROTHERS | P007 | 出图/第2话/panels/P007.png | MON_FOX_BROTHERS hair 指纹与参考图相似度偏低：score=0.274。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | MON_FOX_BROTHERS | P015 | 出图/第2话/panels/P015.png | MON_FOX_BROTHERS face 指纹与参考图相似度偏低：score=0.450。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | MON_FOX_BROTHERS | P015 | 出图/第2话/panels/P015.png | MON_FOX_BROTHERS hair 指纹与参考图相似度偏低：score=0.260。这是色彩分布代理，需并排人审。 |
| warn | ccip_identity_low | MON_FOX_SERVANT | P007 | 出图/第2话/panels/P007.png | MON_FOX_SERVANT CCIP 身份距离 0.2219 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | face_fingerprint_low | MON_FOX_SERVANT | P007 | 出图/第2话/panels/P007.png | MON_FOX_SERVANT face 指纹与参考图相似度偏低：score=0.438。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | MON_FOX_SERVANT | P007 | 出图/第2话/panels/P007.png | MON_FOX_SERVANT hair 指纹与参考图相似度偏低：score=0.325。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | MON_FOX_SERVANT | P008 | 出图/第2话/panels/P008.png | MON_FOX_SERVANT hair 指纹与参考图相似度偏低：score=0.438。这是色彩分布代理，需并排人审。 |
| warn | ccip_identity_low | MON_FOX_SERVANT | P015 | 出图/第2话/panels/P015.png | MON_FOX_SERVANT CCIP 身份距离 0.196 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | face_fingerprint_low | MON_FOX_SERVANT | P015 | 出图/第2话/panels/P015.png | MON_FOX_SERVANT face 指纹与参考图相似度偏低：score=0.462。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | MON_FOX_SERVANT | P015 | 出图/第2话/panels/P015.png | MON_FOX_SERVANT hair 指纹与参考图相似度偏低：score=0.281。这是色彩分布代理，需并排人审。 |
