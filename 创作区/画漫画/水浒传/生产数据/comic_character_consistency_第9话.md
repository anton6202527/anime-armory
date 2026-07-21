# 漫画角色一致性报告 — 第9话

- 生成时间：2026-07-20T18:56:20
- 结论：warn
- 角色数：8
- 出场绑定：95
- block/warn/info：0 / 23 / 0
- 并排复核图：`生产数据/qa_previews/第9话_character_consistency_contact_sheet.jpg`

## 记录

- VLM 并排判定任务包已刷新：生产数据/comic_vlm_judge_tasks_第9话.json（裁决 0/137）；由多模态 agent 看图执行并写回 verdict 文件。
- 已生成角色一致性并排复核图：生产数据/qa_previews/第9话_character_consistency_contact_sheet.jpg

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_CHEN_DA | 3 | 13 |
| CHAR_COUNTY_LIEUTENANT | 2 | 2 |
| CHAR_LI_JI | 3 | 4 |
| CHAR_LU_DA | 3 | 4 |
| CHAR_SHI_JIN | 3 | 42 |
| CHAR_WANG_SI | 2 | 2 |
| CHAR_YANG_CHUN | 3 | 13 |
| CHAR_ZHU_WU | 3 | 15 |

## Findings

| severity | code | character | panel | artifact | reason |
|---|---|---|---|---|---|
| warn | ccip_identity_low | CHAR_CHEN_DA | P002 | 出图/第9话/panels/P002.png | CHAR_CHEN_DA CCIP 身份距离 0.1909 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | CHAR_CHEN_DA | P009 | 出图/第9话/panels/P009.png | CHAR_CHEN_DA CCIP 身份距离 0.2346 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | CHAR_CHEN_DA | P012 | 出图/第9话/panels/P012.png | CHAR_CHEN_DA CCIP 身份距离 0.1871 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | CHAR_CHEN_DA | P019 | 出图/第9话/panels/P019.png | CHAR_CHEN_DA CCIP 身份距离 0.195 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | CHAR_CHEN_DA | P023 | 出图/第9话/panels/P023.png | CHAR_CHEN_DA CCIP 身份距离 0.1825 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | CHAR_CHEN_DA | P025 | 出图/第9话/panels/P025.png | CHAR_CHEN_DA CCIP 身份距离 0.1799 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | CHAR_CHEN_DA | P028 | 出图/第9话/panels/P028.png | CHAR_CHEN_DA CCIP 身份距离 0.1803 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | CHAR_CHEN_DA | P030 | 出图/第9话/panels/P030.png | CHAR_CHEN_DA CCIP 身份距离 0.1828 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | CHAR_CHEN_DA | P035 | 出图/第9话/panels/P035.png | CHAR_CHEN_DA CCIP 身份距离 0.1975 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | ccip_identity_low | CHAR_CHEN_DA | P036 | 出图/第9话/panels/P036.png | CHAR_CHEN_DA CCIP 身份距离 0.2099 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） |
| warn | hair_fingerprint_low | CHAR_COUNTY_LIEUTENANT | P024 | 出图/第9话/panels/P024.png | CHAR_COUNTY_LIEUTENANT hair 指纹与参考图相似度偏低：score=0.359。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_LI_JI | P021 | 出图/第9话/panels/P021.png | CHAR_LI_JI face 指纹与参考图相似度偏低：score=0.423。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_LI_JI | P021 | 出图/第9话/panels/P021.png | CHAR_LI_JI hair 指纹与参考图相似度偏低：score=0.194。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_LI_JI | P022 | 出图/第9话/panels/P022.png | CHAR_LI_JI hair 指纹与参考图相似度偏低：score=0.457。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_SHI_JIN | P008 | 出图/第9话/panels/P008.png | CHAR_SHI_JIN face 指纹与参考图相似度偏低：score=0.450。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P008 | 出图/第9话/panels/P008.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.207。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P021 | 出图/第9话/panels/P021.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.424。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_SHI_JIN | P038 | 出图/第9话/panels/P038.png | CHAR_SHI_JIN face 指纹与参考图相似度偏低：score=0.375。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_SHI_JIN | P038 | 出图/第9话/panels/P038.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.391。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG_SI | P008 | 出图/第9话/panels/P008.png | CHAR_WANG_SI face 指纹与参考图相似度偏低：score=0.411。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_WANG_SI | P008 | 出图/第9话/panels/P008.png | CHAR_WANG_SI hair 指纹与参考图相似度偏低：score=0.194。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_YANG_CHUN | P020 | 出图/第9话/panels/P020.png | CHAR_YANG_CHUN hair 指纹与参考图相似度偏低：score=0.456。这是色彩分布代理，需并排人审。 |
| warn | hair_fingerprint_low | CHAR_ZHU_WU | P012 | 出图/第9话/panels/P012.png | CHAR_ZHU_WU hair 指纹与参考图相似度偏低：score=0.429。这是色彩分布代理，需并排人审。 |
