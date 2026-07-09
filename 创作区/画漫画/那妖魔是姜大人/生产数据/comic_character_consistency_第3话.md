# 漫画角色一致性报告 — 第3话

- 生成时间：2026-07-09T14:31:46
- 结论：pass
- 角色数：2
- 出场绑定：15
- block/warn/info：0 / 0 / 1
- 并排复核图：`生产数据/qa_previews/第3话_character_consistency_contact_sheet.jpg`

## 记录

- 已生成角色一致性并排复核图：生产数据/qa_previews/第3话_character_consistency_contact_sheet.jpg
- 已按 生产数据/character_consistency_acceptance_第3话.json 人审签收 1 条角色一致性 finding；原始机器 severity 保留在 machine_severity。

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_JYC | 6 | 14 |
| CHAR_PEI | 6 | 1 |

## Findings

| severity | code | character | panel | artifact | reason |
|---|---|---|---|---|---|
| info | face_fingerprint_low | CHAR_JYC | P010 | 出图/第3话/panels/P010.png | CHAR_JYC face 指纹与参考图相似度偏低：score=0.491。这是启发式提示，需并排人审。 |
