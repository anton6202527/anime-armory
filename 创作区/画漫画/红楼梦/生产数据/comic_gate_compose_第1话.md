# 漫画 Gate — compose — 第1话

- 生成时间：2026-07-12T15:48:05
- 结论：warn
- block/warn/info：0 / 1 / 3

## 记录

- backend adapter: openai_gpt_image_project_memory; reference_image_limit=16; persistent_subject=False
- 参考图集合有扩充但提交 prompt 未变的格（不阻断，由 identity report 管理重抽）：P001、P002、P003、P004、P005、P006、P007、P008、P009、P010、P011、P012、P013、P014、P015、P016、P017、P018、P019、P020
- style consistency refreshed: 生产数据/comic_style_consistency_第1话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第1话.md
- scene/prop consistency refreshed: 生产数据/comic_scene_prop_consistency_第1话.md

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | panel_style_outlier | 出图/第1话/panels/P003.png | 风格指纹内聚度 0.7526 明显低于本话中位 0.8151，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P004.png | 风格指纹内聚度 0.7478 明显低于本话中位 0.8151，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | tone_value_outlier | 出图/第1话/panels/P002.png | 黑白灰量化偏离话内中位：black_ratio=0.1817（中位 0.000），线宽代理 edge_density=0.0862（中位 0.094）。疑似网点密度/黑场/线宽口径不统一。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| warn | platform_profile_unverified | 排版/export_manifest.json | 自定义(数字页漫+印刷母版) 平台规格未有当前可机检的一手尺寸证据。 | compose | 发布/商用前在平台后台或官方文档核验宽度、高度、格式、文件大小，并更新 platform profile。 |
