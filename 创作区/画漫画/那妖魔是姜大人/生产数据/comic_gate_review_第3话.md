# 漫画 Gate — review — 第3话

- 生成时间：2026-07-09T14:30:37
- 结论：pass
- block/warn/info：0 / 0 / 8

## 记录

- backend adapter: openai_gpt_image_project_memory; reference_image_limit=16; persistent_subject=False
- style consistency refreshed: 生产数据/comic_style_consistency_第3话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第3话.md
- comic-review report refreshed in review gate

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | panel_post_qc_warn | 出图/第3话/panels/P001.png | P001 的落盘 post_qc=warn 已人审签收为误报：机检命中的左上亮区是满月高光和薄云留白，不是对白气泡、旁白框或烘焙文字容器；画面无文字、水印、logo。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_style_outlier | 出图/第3话/panels/P006.png | 风格指纹内聚度 0.7810 明显低于本话中位 0.8771，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第3话/panels/P011.png | 风格指纹内聚度 0.7720 明显低于本话中位 0.8771，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | face_fingerprint_low | 出图/第3话/panels/P010.png | CHAR_JYC face 指纹与参考图相似度偏低：score=0.491。这是启发式提示，需并排人审。 | review | 若 P010 后续重抽或改构图，重新运行 character_consistency.py 并重新签收。 |
| info | image | 出图/第3话/panels/P001.png | 疑似烘焙空白气泡已人审签收为误报：机检命中的左上亮区是满月高光和薄云留白，不是对白气泡、旁白框或烘焙文字容器；画面无文字、水印、logo。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | style | 出图/第3话/panels/P006.png | 风格指纹内聚度 0.7810 明显低于本话中位 0.8771，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第3话/panels/P011.png | 风格指纹内聚度 0.7720 明显低于本话中位 0.8771，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | character | 出图/第3话/panels/P010.png | CHAR_JYC face 指纹与参考图相似度偏低：score=0.491。这是启发式提示，需并排人审。 | comic-review | 若 P010 后续重抽或改构图，重新运行 character_consistency.py 并重新签收。 |
