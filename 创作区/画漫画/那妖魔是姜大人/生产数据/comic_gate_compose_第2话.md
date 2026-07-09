# 漫画 Gate — compose — 第2话

- 生成时间：2026-07-09T10:58:47
- 结论：warn
- block/warn/info：0 / 3 / 6

## 记录

- backend adapter: openai_gpt_image_project_memory; reference_image_limit=16; persistent_subject=False
- style consistency refreshed: 生产数据/comic_style_consistency_第2话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第2话.md

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| warn | panel_post_qc_warn | 出图/第2话/panels/P014.png | P014 的落盘 post_qc=warn，需要人审签收或重抽。 | image | 放大查看 panel_qc 与原图；确认误报时在审查报告保留签收证据。 |
| info | panel_style_outlier | 出图/第2话/panels/P004.png | 风格指纹内聚度 0.8703 明显低于本话中位 0.9152，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第2话/panels/P006.png | 风格指纹内聚度 0.8251 明显低于本话中位 0.9152，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第2话/panels/P008.png | 风格指纹内聚度 0.8643 明显低于本话中位 0.9152，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第2话/panels/P010.png | 风格指纹内聚度 0.7788 明显低于本话中位 0.9152，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第2话/panels/P011.png | 风格指纹内聚度 0.8467 明显低于本话中位 0.9152，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | location_color_grade_shift | 出图/第2话/panels/P010.png | 同场景“LOC_WASTELAND”内调色代理偏离组中位：warmth_dev=0.254, tint_dev=0.020。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| warn | face_fingerprint_low | 出图/第2话/panels/P010.png | CHAR_JYC face 指纹与参考图相似度偏低：score=0.408。这是启发式提示，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第2话/panels/P010.png | CHAR_JYC outfit 指纹与参考图相似度偏低：score=0.298。这是启发式提示，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
