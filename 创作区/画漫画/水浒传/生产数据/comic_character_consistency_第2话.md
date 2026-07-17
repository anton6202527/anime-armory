# 漫画角色一致性报告 — 第2话

- 生成时间：2026-07-17T21:54:10
- 结论：pass
- 角色数：3
- 出场绑定：38
- block/warn/info：0 / 0 / 3
- 并排复核图：`生产数据/qa_previews/第2话_character_consistency_contact_sheet.jpg`

## 记录

- CCIP 动漫身份 embedding 不可用（色彩指纹只是代理，换脸同色调会漏报）。建议在独立 venv 安装 dghs-imgutils（pip install dghs-imgutils）后重跑，获得阈值化的同角色判定（threshold=0.178）。
- VLM 并排判定任务包已刷新：生产数据/comic_vlm_judge_tasks_第2话.json（裁决 0/74）；由多模态 agent 看图执行并写回 verdict 文件。
- 已生成角色一致性并排复核图：生产数据/qa_previews/第2话_character_consistency_contact_sheet.jpg
- 已按 生产数据/character_consistency_acceptance_第2话.json 人审签收 3 条角色一致性 finding；原始机器 severity 保留在 machine_severity。

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_ABBOT_SHANGQING | 5 | 12 |
| CHAR_EMPEROR_RENZONG | 4 | 3 |
| CHAR_HONG_XIN | 5 | 23 |

## Findings

| severity | code | character | panel | artifact | reason |
|---|---|---|---|---|---|
| info | hair_fingerprint_low | CHAR_ABBOT_SHANGQING | P029 | 出图/第2话/panels/P029.png | CHAR_ABBOT_SHANGQING hair 指纹与参考图相似度偏低：score=0.405。这是色彩分布代理，需并排人审。 |
| info | face_fingerprint_low | CHAR_ABBOT_SHANGQING | P030 | 出图/第2话/panels/P030.png | CHAR_ABBOT_SHANGQING face 指纹与参考图相似度偏低：score=0.428。这是色彩分布代理，需并排人审。 |
| info | hair_fingerprint_low | CHAR_ABBOT_SHANGQING | P030 | 出图/第2话/panels/P030.png | CHAR_ABBOT_SHANGQING hair 指纹与参考图相似度偏低：score=0.373。这是色彩分布代理，需并排人审。 |
