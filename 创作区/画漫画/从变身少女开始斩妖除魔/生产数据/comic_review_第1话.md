# 漫画审查报告 — 第1话

- 生成时间：2026-07-16T01:29:35
- 结论：pass
- panel 数：28
- block/warn/info：0 / 0 / 15

## 设置

- 定妆级别: 长线专门定妆
- 参考一致性策略: 共享参考图
- 年龄形态继承: 开启
- 角色一致性硬闸: 开启
- 风格锚: STYLE_USER_JIANG_YUECHU_REF
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
| info | image | 出图/第1话/panels/P028.png | 疑似烘焙空白气泡已人审签收为误报：误报：几何连通区是黑墨冲击、暗红布带与白色速度线，画面无空白气泡或文字容器。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | style | 出图/第1话/panels/P010.png | 风格指纹内聚度 0.8091 明显低于本话中位 0.8502，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P019.png | 风格指纹内聚度 0.8080 明显低于本话中位 0.8502，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P024.png | 风格指纹内聚度 0.7024 明显低于本话中位 0.8502，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P025.png | 风格指纹内聚度 0.8079 明显低于本话中位 0.8502，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P028.png | 风格指纹内聚度 0.7415 明显低于本话中位 0.8502，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P015.png | 同场景“尸骸荒野”内调色代理偏离组中位：warmth_dev=0.227, tint_dev=0.058。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P018.png | 同场景“尸骸荒野”内调色代理偏离组中位：warmth_dev=0.210, tint_dev=0.052。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P019.png | 同场景“尸骸荒野”内调色代理偏离组中位：warmth_dev=0.232, tint_dev=0.089。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P024.png | 同场景“尸骸荒野”内调色代理偏离组中位：warmth_dev=0.482, tint_dev=0.215。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P028.png | 同场景“尸骸荒野”内调色代理偏离组中位：warmth_dev=0.236, tint_dev=0.040。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P025.png | 与同场景锚 LOC_DESOLATE_WILDERNESS 的前一格 P024 相比冷暖/亮度跳变：warmth_jump=0.502, val_jump=0.075；疑似光位翻转或昼夜漂移。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P009.png | 黑白灰量化偏离话内中位：black_ratio=0.045（中位 0.226），线宽代理 edge_density=0.0842（中位 0.083）。疑似网点密度/黑场/线宽口径不统一。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P021.png | 黑白灰量化偏离话内中位：black_ratio=0.4285（中位 0.226），线宽代理 edge_density=0.0813（中位 0.083）。疑似网点密度/黑场/线宽口径不统一。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P028.png | 黑白灰量化偏离话内中位：black_ratio=0.3853（中位 0.226），线宽代理 edge_density=0.1412（中位 0.083）。疑似网点密度/黑场/线宽口径不统一。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |

## 疑似烘焙气泡

- P028: `出图/第1话/panels/P028.png` components=1，已签收为误报

## 风格一致性

- 结论：pass
- 摘要：{"panel_count": 28, "finding_count": 14, "block_count": 0, "warn_count": 0, "info_count": 14}

## 角色一致性

- 结论：pass
- 摘要：{"character_count": 3, "panel_binding_count": 55, "finding_count": 0, "block_count": 0, "warn_count": 0, "info_count": 0}
- 并排复核图：`生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg`
