# 漫画角色一致性报告 — 第5话

- 生成时间：2026-07-19T16:59:40
- 结论：warn
- 角色数：5
- 出场绑定：75
- block/warn/info：0 / 26 / 0
- 并排复核图：`生产数据/qa_previews/第5话_character_consistency_contact_sheet.jpg`

## 记录

- CCIP 动漫身份 embedding 不可用（色彩指纹只是代理，换脸同色调会漏报）。建议在独立 venv 安装 dghs-imgutils（pip install dghs-imgutils）后重跑，获得阈值化的同角色判定（threshold=0.178）。
- VLM 并排判定任务包已刷新：生产数据/comic_vlm_judge_tasks_第5话.json（裁决 0/117）；由多模态 agent 看图执行并写回 verdict 文件。
- 已生成角色一致性并排复核图：生产数据/qa_previews/第5话_character_consistency_contact_sheet.jpg

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_GAO_QIU | 5 | 2 |
| CHAR_SHI_JIN | 3 | 14 |
| CHAR_SHI_TAIGONG | 2 | 5 |
| CHAR_WANG_JIN | 3 | 36 |
| CHAR_WANG_MOTHER | 3 | 18 |

## Findings

| severity | code | character | panel | artifact | reason |
|---|---|---|---|---|---|
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P036 | 出图/第5话/panels/P036.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.453。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P042 | 出图/第5话/panels/P042.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.446。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_SHI_JIN | P043 | 出图/第5话/panels/P043.png | CHAR_SHI_JIN face 指纹与参考图相似度偏低：score=0.480。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P043 | 出图/第5话/panels/P043.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.369。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P046 | 出图/第5话/panels/P046.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.398。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG_JIN | P004 | 出图/第5话/panels/P004.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.435。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P004 | 出图/第5话/panels/P004.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.334。这是色彩分布代理，需并排人审。 |
| warn | outfit_fingerprint_low | CHAR_WANG_JIN | P009 | 出图/第5话/panels/P009.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.384。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG_JIN | P012 | 出图/第5话/panels/P012.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.405。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P012 | 出图/第5话/panels/P012.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.385。这是色彩分布代理，需并排人审。 |
| warn | outfit_fingerprint_low | CHAR_WANG_JIN | P012 | 出图/第5话/panels/P012.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.200。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG_JIN | P022 | 出图/第5话/panels/P022.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.416。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P022 | 出图/第5话/panels/P022.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.256。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG_JIN | P034 | 出图/第5话/panels/P034.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.271。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P034 | 出图/第5话/panels/P034.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.233。这是色彩分布代理，需并排人审。 |
| warn | outfit_fingerprint_low | CHAR_WANG_JIN | P034 | 出图/第5话/panels/P034.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.124。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P036 | 出图/第5话/panels/P036.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.388。这是色彩分布代理，需并排人审。 |
| warn | outfit_fingerprint_low | CHAR_WANG_JIN | P036 | 出图/第5话/panels/P036.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.395。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P043 | 出图/第5话/panels/P043.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.338。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG_JIN | P046 | 出图/第5话/panels/P046.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.428。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P046 | 出图/第5话/panels/P046.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.299。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG_MOTHER | P012 | 出图/第5话/panels/P012.png | CHAR_WANG_MOTHER face 指纹与参考图相似度偏低：score=0.287。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_MOTHER | P012 | 出图/第5话/panels/P012.png | CHAR_WANG_MOTHER hair 指纹与参考图相似度偏低：score=0.242。这是色彩分布代理，需并排人审。 |
| warn | outfit_fingerprint_low | CHAR_WANG_MOTHER | P012 | 出图/第5话/panels/P012.png | CHAR_WANG_MOTHER outfit 指纹与参考图相似度偏低：score=0.363。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG_MOTHER | P022 | 出图/第5话/panels/P022.png | CHAR_WANG_MOTHER face 指纹与参考图相似度偏低：score=0.391。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_MOTHER | P022 | 出图/第5话/panels/P022.png | CHAR_WANG_MOTHER hair 指纹与参考图相似度偏低：score=0.194。这是色彩分布代理，需并排人审。 |
