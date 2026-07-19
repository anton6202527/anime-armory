# 漫画角色一致性报告 — 第6话

- 生成时间：2026-07-19T18:54:19
- 结论：warn
- 角色数：4
- 出场绑定：86
- block/warn/info：0 / 37 / 0
- 并排复核图：`生产数据/qa_previews/第6话_character_consistency_contact_sheet.jpg`

## 记录

- CCIP 动漫身份 embedding 不可用（色彩指纹只是代理，换脸同色调会漏报）。建议在独立 venv 安装 dghs-imgutils（pip install dghs-imgutils）后重跑，获得阈值化的同角色判定（threshold=0.178）。
- VLM 并排判定任务包已刷新：生产数据/comic_vlm_judge_tasks_第6话.json（裁决 0/130）；由多模态 agent 看图执行并写回 verdict 文件。
- 已生成角色一致性并排复核图：生产数据/qa_previews/第6话_character_consistency_contact_sheet.jpg

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_SHI_JIN | 3 | 41 |
| CHAR_SHI_TAIGONG | 2 | 10 |
| CHAR_WANG_JIN | 3 | 29 |
| CHAR_WANG_MOTHER | 3 | 6 |

## Findings

| severity | code | character | panel | artifact | reason |
|---|---|---|---|---|---|
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P002 | 出图/第6话/panels/P002.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.451。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P010 | 出图/第6话/panels/P010.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.448。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P017 | 出图/第6话/panels/P017.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.391。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P018 | 出图/第6话/panels/P018.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.423。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P031 | 出图/第6话/panels/P031.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.317。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_SHI_JIN | P032 | 出图/第6话/panels/P032.png | CHAR_SHI_JIN face 指纹与参考图相似度偏低：score=0.452。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P032 | 出图/第6话/panels/P032.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.210。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_SHI_JIN | P040 | 出图/第6话/panels/P040.png | CHAR_SHI_JIN face 指纹与参考图相似度偏低：score=0.392。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P040 | 出图/第6话/panels/P040.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.248。这是色彩分布代理，需并排人审。 |
| warn | outfit_fingerprint_low | CHAR_SHI_TAIGONG | P003 | 出图/第6话/panels/P003.png | CHAR_SHI_TAIGONG outfit 指纹与参考图相似度偏低：score=0.328。这是色彩分布代理，需并排人审。 |
| warn | outfit_fingerprint_low | CHAR_SHI_TAIGONG | P005 | 出图/第6话/panels/P005.png | CHAR_SHI_TAIGONG outfit 指纹与参考图相似度偏低：score=0.330。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_SHI_TAIGONG | P029 | 出图/第6话/panels/P029.png | CHAR_SHI_TAIGONG face 指纹与参考图相似度偏低：score=0.471。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_TAIGONG | P029 | 出图/第6话/panels/P029.png | CHAR_SHI_TAIGONG hair 指纹与参考图相似度偏低：score=0.255。这是色彩分布代理，需并排人审。 |
| warn | outfit_fingerprint_low | CHAR_SHI_TAIGONG | P029 | 出图/第6话/panels/P029.png | CHAR_SHI_TAIGONG outfit 指纹与参考图相似度偏低：score=0.221。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_TAIGONG | P033 | 出图/第6话/panels/P033.png | CHAR_SHI_TAIGONG hair 指纹与参考图相似度偏低：score=0.436。这是色彩分布代理，需并排人审。 |
| warn | outfit_fingerprint_low | CHAR_SHI_TAIGONG | P033 | 出图/第6话/panels/P033.png | CHAR_SHI_TAIGONG outfit 指纹与参考图相似度偏低：score=0.335。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_TAIGONG | P042 | 出图/第6话/panels/P042.png | CHAR_SHI_TAIGONG hair 指纹与参考图相似度偏低：score=0.443。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_TAIGONG | P044 | 出图/第6话/panels/P044.png | CHAR_SHI_TAIGONG hair 指纹与参考图相似度偏低：score=0.412。这是色彩分布代理，需并排人审。 |
| warn | outfit_fingerprint_low | CHAR_SHI_TAIGONG | P044 | 出图/第6话/panels/P044.png | CHAR_SHI_TAIGONG outfit 指纹与参考图相似度偏低：score=0.417。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P002 | 出图/第6话/panels/P002.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.305。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P010 | 出图/第6话/panels/P010.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.434。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P016 | 出图/第6话/panels/P016.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.451。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P017 | 出图/第6话/panels/P017.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.295。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG_JIN | P018 | 出图/第6话/panels/P018.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.491。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P018 | 出图/第6话/panels/P018.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.339。这是色彩分布代理，需并排人审。 |
| warn | outfit_fingerprint_low | CHAR_WANG_JIN | P023 | 出图/第6话/panels/P023.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.418。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG_JIN | P024 | 出图/第6话/panels/P024.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.480。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P024 | 出图/第6话/panels/P024.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.422。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG_JIN | P026 | 出图/第6话/panels/P026.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.433。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P026 | 出图/第6话/panels/P026.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.427。这是色彩分布代理，需并排人审。 |
| warn | outfit_fingerprint_low | CHAR_WANG_JIN | P026 | 出图/第6话/panels/P026.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.334。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG_JIN | P029 | 出图/第6话/panels/P029.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.401。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P029 | 出图/第6话/panels/P029.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.436。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P031 | 出图/第6话/panels/P031.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.319。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG_JIN | P032 | 出图/第6话/panels/P032.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.364。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_JIN | P032 | 出图/第6话/panels/P032.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.189。这是色彩分布代理，需并排人审。 |
| warn | outfit_fingerprint_low | CHAR_WANG_JIN | P038 | 出图/第6话/panels/P038.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.365。这是色彩分布代理，需并排人审。 |
