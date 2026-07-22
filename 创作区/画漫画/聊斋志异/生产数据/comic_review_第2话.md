# 漫画审查报告 — 第2话

- 生成时间：2026-07-22T15:24:28
- 结论：revise
- panel 数：16
- block/warn/info：0 / 26 / 0

## 设置

- 定妆级别: 长线专门定妆+高一致性
- 参考一致性策略: 共享参考图
- 年龄形态继承: 开启
- 角色一致性硬闸: 开启
- 风格锚: STYLE_LIAOZHAI_QING_GONGXI
- 文字语言: 中文
- 合规用途: 自用草稿

## 记录

- 已刷新风格一致性报告：生产数据/comic_style_consistency_第2话.md
- 已刷新角色一致性报告：生产数据/comic_character_consistency_第2话.md
- 自用草稿 用途：字体权利=pending_before_publish，仅记录，不进入发布授权流程。
- 自用草稿 用途：素材权利=pending_before_publish，仅记录，不进入发布授权流程。
- 自用草稿 用途：system_font_draft 仅作草稿嵌字字体记录，不进入发布授权流程。

## 问题清单

| severity | category | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| warn | export | 排版/export_manifest.json | 自定义(红果式移动端节奏内审，不作为发布平台规格) 平台规格未有当前可机检的一手尺寸证据。 | comic-compose | 发布/商用前在平台后台或官方文档核验宽度、高度、格式、文件大小，并更新 platform profile。 |
| warn | style | 出图/第2话/panels/P002.png | 黑白灰量化偏离话内中位：black_ratio=0.3751（中位 0.059），线宽代理 edge_density=0.0524（中位 0.086）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第2话/panels/P003.png | 黑白灰量化偏离话内中位：black_ratio=0.3565（中位 0.059），线宽代理 edge_density=0.055（中位 0.086）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第2话/panels/P004.png | 黑白灰量化偏离话内中位：black_ratio=0.2626（中位 0.059），线宽代理 edge_density=0.0593（中位 0.086）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第2话/panels/P006.png | 黑白灰量化偏离话内中位：black_ratio=0.2614（中位 0.059），线宽代理 edge_density=0.0424（中位 0.086）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第2话/panels/P007.png | 黑白灰量化偏离话内中位：black_ratio=0.2497（中位 0.059），线宽代理 edge_density=0.058（中位 0.086）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第2话/panels/P015.png | 黑白灰量化偏离话内中位：black_ratio=0.4109（中位 0.059），线宽代理 edge_density=0.0797（中位 0.086）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/共享/style_baseline.json | 本话整体指纹与风格锚图最高相似度仅 0.7094，风格锚可能已失去约束力。 | comic-image | 并排比对锚图与本话 contact sheet；必要时更新风格锚或统一重抽。 |
| warn | character | 出图/第2话/panels/P007.png | CHAR_JIA_CHILD CCIP 身份距离 0.2126 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） | comic-image | 并排对比 contact sheet 与定妆图；确认脸漂则回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P007.png | CHAR_JIA_CHILD hair 指纹与参考图相似度偏低：score=0.341。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P015.png | CHAR_JIA_CHILD hair 指纹与参考图相似度偏低：score=0.294。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P006.png | CHAR_JIA_FATHER hair 指纹与参考图相似度偏低：score=0.450。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P002.png | CHAR_JIA_MOTHER hair 指纹与参考图相似度偏低：score=0.431。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P004.png | MON_FOX_BROTHERS face 指纹与参考图相似度偏低：score=0.491。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P007.png | MON_FOX_BROTHERS CCIP 身份距离 0.2107 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） | comic-image | 并排对比 contact sheet 与定妆图；确认脸漂则回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P007.png | MON_FOX_BROTHERS face 指纹与参考图相似度偏低：score=0.392。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P007.png | MON_FOX_BROTHERS hair 指纹与参考图相似度偏低：score=0.274。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P015.png | MON_FOX_BROTHERS face 指纹与参考图相似度偏低：score=0.450。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P015.png | MON_FOX_BROTHERS hair 指纹与参考图相似度偏低：score=0.260。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P007.png | MON_FOX_SERVANT CCIP 身份距离 0.2219 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） | comic-image | 并排对比 contact sheet 与定妆图；确认脸漂则回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P007.png | MON_FOX_SERVANT face 指纹与参考图相似度偏低：score=0.438。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P007.png | MON_FOX_SERVANT hair 指纹与参考图相似度偏低：score=0.325。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P008.png | MON_FOX_SERVANT hair 指纹与参考图相似度偏低：score=0.438。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P015.png | MON_FOX_SERVANT CCIP 身份距离 0.196 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） | comic-image | 并排对比 contact sheet 与定妆图；确认脸漂则回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P015.png | MON_FOX_SERVANT face 指纹与参考图相似度偏低：score=0.462。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第2话/panels/P015.png | MON_FOX_SERVANT hair 指纹与参考图相似度偏低：score=0.281。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |

## 风格一致性

- 结论：warn
- 摘要：{"panel_count": 16, "finding_count": 7, "block_count": 0, "warn_count": 7, "info_count": 0}

## 角色一致性

- 结论：warn
- 摘要：{"character_count": 5, "panel_binding_count": 32, "finding_count": 18, "block_count": 0, "warn_count": 18, "info_count": 0}
- 并排复核图：`生产数据/qa_previews/第2话_character_consistency_contact_sheet.jpg`
