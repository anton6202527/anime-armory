# 漫画 Gate — review — 第1话

- 生成时间：2026-07-09T11:05:30
- 结论：pass
- block/warn/info：0 / 0 / 10

## 记录

- backend adapter: openai_gpt_image_project_memory; reference_image_limit=16; persistent_subject=False
- style consistency refreshed: 生产数据/comic_style_consistency_第1话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第1话.md
- comic-review report refreshed in review gate

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | panel_style_outlier | 出图/第1话/panels/P001.png | 风格指纹内聚度 0.7478 明显低于本话中位 0.8876，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P002.png | 风格指纹内聚度 0.7114 明显低于本话中位 0.8876，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P010.png | 风格指纹内聚度 0.8389 明显低于本话中位 0.8876，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P013.png | 风格指纹内聚度 0.8346 明显低于本话中位 0.8876，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | image | 出图/第1话/panels/P008.png | 疑似烘焙空白气泡已人审签收为误报：候选区域位于右上天空/雾光留白，用于后期对白，不含气泡边框、尾巴或文字容器。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P010.png | 疑似烘焙空白气泡已人审签收为误报：候选区域是虎妖复起大格的逆光天空/烟雾亮面，不是烘焙空白气泡；最终对白由 comic-compose 后期绘制。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | style | 出图/第1话/panels/P001.png | 风格指纹内聚度 0.7478 明显低于本话中位 0.8876，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P002.png | 风格指纹内聚度 0.7114 明显低于本话中位 0.8876，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P010.png | 风格指纹内聚度 0.8389 明显低于本话中位 0.8876，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P013.png | 风格指纹内聚度 0.8346 明显低于本话中位 0.8876，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
