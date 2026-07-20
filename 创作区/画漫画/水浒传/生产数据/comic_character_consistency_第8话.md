# 漫画角色一致性报告 — 第8话

- 生成时间：2026-07-20T15:04:21
- 结论：warn
- 角色数：7
- 出场绑定：78
- block/warn/info：0 / 25 / 0
- 并排复核图：`生产数据/qa_previews/第8话_character_consistency_contact_sheet.jpg`

## 记录

- CCIP 动漫身份 embedding 不可用（色彩指纹只是代理，换脸同色调会漏报）。建议在独立 venv 安装 dghs-imgutils（pip install dghs-imgutils）后重跑，获得阈值化的同角色判定（threshold=0.178）。
- VLM 并排判定任务包已刷新：生产数据/comic_vlm_judge_tasks_第8话.json（裁决 0/119）；由多模态 agent 看图执行并写回 verdict 文件。
- 已生成角色一致性并排复核图：生产数据/qa_previews/第8话_character_consistency_contact_sheet.jpg

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_CHEN_DA | 3 | 8 |
| CHAR_COUNTY_LIEUTENANT | 2 | 4 |
| CHAR_LI_JI | 3 | 7 |
| CHAR_SHI_JIN | 3 | 21 |
| CHAR_WANG_SI | 2 | 21 |
| CHAR_YANG_CHUN | 3 | 8 |
| CHAR_ZHU_WU | 3 | 9 |

## Findings

| severity | code | character | panel | artifact | reason |
|---|---|---|---|---|---|
| warn | hair_fingerprint_low | CHAR_CHEN_DA | P040 | 出图/第8话/panels/P040.png | CHAR_CHEN_DA hair 指纹与参考图相似度偏低：score=0.297。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_CHEN_DA | P042 | 出图/第8话/panels/P042.png | CHAR_CHEN_DA hair 指纹与参考图相似度偏低：score=0.347。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_CHEN_DA | P044 | 出图/第8话/panels/P044.png | CHAR_CHEN_DA hair 指纹与参考图相似度偏低：score=0.312。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_CHEN_DA | P048 | 出图/第8话/panels/P048.png | CHAR_CHEN_DA hair 指纹与参考图相似度偏低：score=0.160。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_LI_JI | P027 | 出图/第8话/panels/P027.png | CHAR_LI_JI face 指纹与参考图相似度偏低：score=0.429。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_LI_JI | P027 | 出图/第8话/panels/P027.png | CHAR_LI_JI hair 指纹与参考图相似度偏低：score=0.219。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_LI_JI | P028 | 出图/第8话/panels/P028.png | CHAR_LI_JI hair 指纹与参考图相似度偏低：score=0.399。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P001 | 出图/第8话/panels/P001.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.308。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P014 | 出图/第8话/panels/P014.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.452。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P040 | 出图/第8话/panels/P040.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.391。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P042 | 出图/第8话/panels/P042.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.411。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_SHI_JIN | P044 | 出图/第8话/panels/P044.png | CHAR_SHI_JIN face 指纹与参考图相似度偏低：score=0.461。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P044 | 出图/第8话/panels/P044.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.388。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P048 | 出图/第8话/panels/P048.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.227。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_YANG_CHUN | P040 | 出图/第8话/panels/P040.png | CHAR_YANG_CHUN hair 指纹与参考图相似度偏低：score=0.339。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_YANG_CHUN | P044 | 出图/第8话/panels/P044.png | CHAR_YANG_CHUN hair 指纹与参考图相似度偏低：score=0.394。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_YANG_CHUN | P048 | 出图/第8话/panels/P048.png | CHAR_YANG_CHUN face 指纹与参考图相似度偏低：score=0.434。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_YANG_CHUN | P048 | 出图/第8话/panels/P048.png | CHAR_YANG_CHUN hair 指纹与参考图相似度偏低：score=0.201。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_ZHU_WU | P040 | 出图/第8话/panels/P040.png | CHAR_ZHU_WU face 指纹与参考图相似度偏低：score=0.486。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_ZHU_WU | P040 | 出图/第8话/panels/P040.png | CHAR_ZHU_WU hair 指纹与参考图相似度偏低：score=0.246。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_ZHU_WU | P042 | 出图/第8话/panels/P042.png | CHAR_ZHU_WU hair 指纹与参考图相似度偏低：score=0.290。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_ZHU_WU | P044 | 出图/第8话/panels/P044.png | CHAR_ZHU_WU face 指纹与参考图相似度偏低：score=0.396。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_ZHU_WU | P044 | 出图/第8话/panels/P044.png | CHAR_ZHU_WU hair 指纹与参考图相似度偏低：score=0.252。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_ZHU_WU | P048 | 出图/第8话/panels/P048.png | CHAR_ZHU_WU face 指纹与参考图相似度偏低：score=0.420。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_ZHU_WU | P048 | 出图/第8话/panels/P048.png | CHAR_ZHU_WU hair 指纹与参考图相似度偏低：score=0.129。这是色彩分布代理，需并排人审。 |
