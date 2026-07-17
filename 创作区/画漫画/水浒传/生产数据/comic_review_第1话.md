# 漫画审查报告 — 第1话

- 生成时间：2026-07-17T10:52:10
- 结论：pass
- panel 数：48
- block/warn/info：0 / 0 / 18

## 设置

- 定妆级别: 长线专门定妆+高一致性
- 参考一致性策略: 共享参考图
- 年龄形态继承: 开启
- 角色一致性硬闸: 开启
- 风格锚: STYLE_SHUIHU_SONG_CINEMATIC
- 文字语言: 中文
- 合规用途: demo学习

## 记录

- 已刷新风格一致性报告：生产数据/comic_style_consistency_第1话.md
- 已刷新角色一致性报告：生产数据/comic_character_consistency_第1话.md
- demo学习 用途：字体权利=pending_before_publish，仅记录，不进入发布授权流程。
- demo学习 用途：素材权利=pending_before_publish，仅记录，不进入发布授权流程。
- demo学习 用途：system_font_draft 仅作草稿嵌字字体记录，不进入发布授权流程。
- 已刷新 QA 长图预览：生产数据/qa_previews/第1话_longstrip_preview.webp
- 已刷新 panel contact sheet：生产数据/panel_contact_sheet_第1话.jpg

## 问题清单

| severity | category | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | image | 出图/第1话/panels/P002.png | 疑似烘焙空白气泡已人审签收为误报：接触表复核为紫宸殿地面受光与建筑留白，不是烘焙气泡或文字框。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P015.png | 疑似烘焙空白气泡已人审签收为误报：接触表复核为庭院天空、铺地与钟磬周边的自然负空间，不是烘焙气泡或文字框。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | style | 出图/第1话/panels/P003.png | 风格指纹内聚度 0.7337 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P007.png | 风格指纹内聚度 0.7942 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P009.png | 风格指纹内聚度 0.6932 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P011.png | 风格指纹内聚度 0.7872 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P014.png | 风格指纹内聚度 0.7606 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P018.png | 风格指纹内聚度 0.6841 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P021.png | 风格指纹内聚度 0.7690 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P034.png | 风格指纹内聚度 0.7472 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P046.png | 风格指纹内聚度 0.7125 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P047.png | 风格指纹内聚度 0.7204 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P018.png | 同场景“上清宫方丈”内调色代理偏离组中位：warmth_dev=0.244, tint_dev=0.031。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P046.png | 黑白灰量化偏离话内中位：black_ratio=0.2547（中位 0.009），线宽代理 edge_density=0.0792（中位 0.122）。疑似网点密度/黑场/线宽口径不统一。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | character | 出图/第1话/panels/P004.png | CHAR_WEN_YANBO face 指纹与参考图相似度偏低：score=0.451。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P004.png | CHAR_WEN_YANBO hair 指纹与参考图相似度偏低：score=0.168。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P004.png | CHAR_WEN_YANBO outfit 指纹与参考图相似度偏低：score=0.329。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P005.png | CHAR_WEN_YANBO hair 指纹与参考图相似度偏低：score=0.296。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |

## 疑似烘焙气泡

- P002: `出图/第1话/panels/P002.png` components=3，已签收为误报
- P015: `出图/第1话/panels/P015.png` components=2，已签收为误报

## 风格一致性

- 结论：pass
- 摘要：{"panel_count": 48, "finding_count": 12, "block_count": 0, "warn_count": 0, "info_count": 12}

## 角色一致性

- 结论：pass
- 摘要：{"character_count": 9, "panel_binding_count": 76, "finding_count": 4, "block_count": 0, "warn_count": 0, "info_count": 4}
- 并排复核图：`生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg`
