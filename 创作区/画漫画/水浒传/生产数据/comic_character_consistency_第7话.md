# 漫画角色一致性报告 — 第7话

- 生成时间：2026-07-20T12:12:52
- 结论：warn
- 角色数：5
- 出场绑定：89
- block/warn/info：0 / 3 / 0
- 并排复核图：`生产数据/qa_previews/第7话_character_consistency_contact_sheet.jpg`

## 记录

- CCIP 动漫身份 embedding 不可用（色彩指纹只是代理，换脸同色调会漏报）。建议在独立 venv 安装 dghs-imgutils（pip install dghs-imgutils）后重跑，获得阈值化的同角色判定（threshold=0.178）。
- VLM 并排判定任务包已刷新：生产数据/comic_vlm_judge_tasks_第7话.json（裁决 0/132）；由多模态 agent 看图执行并写回 verdict 文件。
- 已生成角色一致性并排复核图：生产数据/qa_previews/第7话_character_consistency_contact_sheet.jpg

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_CHEN_DA | 3 | 20 |
| CHAR_LI_JI | 3 | 4 |
| CHAR_SHI_JIN | 3 | 33 |
| CHAR_YANG_CHUN | 3 | 16 |
| CHAR_ZHU_WU | 3 | 16 |

## Findings

| severity | code | character | panel | artifact | reason |
|---|---|---|---|---|---|
| warn | hair_fingerprint_low | CHAR_LI_JI | P002 | 出图/第7话/panels/P002.png | CHAR_LI_JI hair 指纹与参考图相似度偏低：score=0.373。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_LI_JI | P004 | 出图/第7话/panels/P004.png | CHAR_LI_JI hair 指纹与参考图相似度偏低：score=0.455。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_YANG_CHUN | P047 | 出图/第7话/panels/P047.png | CHAR_YANG_CHUN hair 指纹与参考图相似度偏低：score=0.276。这是色彩分布代理，需并排人审。 |
