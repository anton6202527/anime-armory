# 漫画角色一致性报告 — 第2话

- 生成时间：2026-07-09T11:05:20
- 结论：pass
- 角色数：2
- 出场绑定：19
- block/warn/info：0 / 0 / 2
- 并排复核图：`生产数据/qa_previews/第2话_character_consistency_contact_sheet.jpg`

## 记录

- 已生成角色一致性并排复核图：生产数据/qa_previews/第2话_character_consistency_contact_sheet.jpg
- 已按 生产数据/character_consistency_acceptance_第2话.json 人审签收 2 条角色一致性 finding；原始机器 severity 保留在 machine_severity。

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_JYC | 6 | 14 |
| CHAR_PEI | 6 | 5 |

## Findings

| severity | code | character | panel | artifact | reason |
|---|---|---|---|---|---|
| info | face_fingerprint_low | CHAR_JYC | P010 | 出图/第2话/panels/P010.png | CHAR_JYC face 指纹与参考图相似度偏低：score=0.408。这是启发式提示，需并排人审。 |
| info | outfit_fingerprint_low | CHAR_JYC | P010 | 出图/第2话/panels/P010.png | CHAR_JYC outfit 指纹与参考图相似度偏低：score=0.298。这是启发式提示，需并排人审。 |
