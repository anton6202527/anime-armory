# 漫画 Gate — compose — 第1话

- 生成时间：2026-07-09T10:58:48
- 结论：pass
- block/warn/info：0 / 0 / 4

## 记录

- backend adapter: openai_gpt_image_project_memory; reference_image_limit=16; persistent_subject=False
- style consistency refreshed: 生产数据/comic_style_consistency_第1话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第1话.md

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | panel_style_outlier | 出图/第1话/panels/P001.png | 风格指纹内聚度 0.7478 明显低于本话中位 0.8876，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P002.png | 风格指纹内聚度 0.7114 明显低于本话中位 0.8876，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P010.png | 风格指纹内聚度 0.8389 明显低于本话中位 0.8876，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P013.png | 风格指纹内聚度 0.8346 明显低于本话中位 0.8876，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
