# 漫画角色一致性报告 — 第1话

- 生成时间：2026-07-21T22:13:40
- 结论：warn
- 角色数：5
- 出场绑定：32
- block/warn/info：0 / 11 / 0
- 并排复核图：`生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg`

## 记录

- VLM 并排判定任务包已刷新：生产数据/comic_vlm_judge_tasks_第1话.json（裁决 0/46）；由多模态 agent 看图执行并写回 verdict 文件。
- 已生成角色一致性并排复核图：生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_BEGGAR | 2 | 1 |
| CHAR_CHEN | 2 | 9 |
| CHAR_DAOIST | 2 | 4 |
| CHAR_WANG | 2 | 12 |
| MON_PAINTED_SKIN | 1 | 6 |

## Findings

| severity | code | character | panel | artifact | reason |
|---|---|---|---|---|---|
| warn | hair_fingerprint_low | CHAR_CHEN | P011 | 出图/第1话/panels/P011.png | CHAR_CHEN hair 指纹与参考图相似度偏低：score=0.437。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_CHEN | P012 | 出图/第1话/panels/P012.png | CHAR_CHEN hair 指纹与参考图相似度偏低：score=0.410。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_DAOIST | P006 | 出图/第1话/panels/P006.png | CHAR_DAOIST hair 指纹与参考图相似度偏低：score=0.319。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG | P002 | 出图/第1话/panels/P002.png | CHAR_WANG face 指纹与参考图相似度偏低：score=0.452。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG | P004 | 出图/第1话/panels/P004.png | CHAR_WANG hair 指纹与参考图相似度偏低：score=0.430。这是色彩分布代理，需并排人审。 |
| warn | outfit_fingerprint_low | CHAR_WANG | P005 | 出图/第1话/panels/P005.png | CHAR_WANG outfit 指纹与参考图相似度偏低：score=0.382。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG | P006 | 出图/第1话/panels/P006.png | CHAR_WANG face 指纹与参考图相似度偏低：score=0.450。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG | P006 | 出图/第1话/panels/P006.png | CHAR_WANG hair 指纹与参考图相似度偏低：score=0.275。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG | P007 | 出图/第1话/panels/P007.png | CHAR_WANG face 指纹与参考图相似度偏低：score=0.427。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG | P007 | 出图/第1话/panels/P007.png | CHAR_WANG hair 指纹与参考图相似度偏低：score=0.424。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | MON_PAINTED_SKIN | P001 | 出图/第1话/panels/P001.png | MON_PAINTED_SKIN hair 指纹与参考图相似度偏低：score=0.429。这是色彩分布代理，需并排人审。 |
