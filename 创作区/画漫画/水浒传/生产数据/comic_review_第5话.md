# 漫画审查报告 — 第5话

- 生成时间：2026-07-19T16:56:31
- 结论：revise
- panel 数：48
- block/warn/info：0 / 50 / 3

## 设置

- 定妆级别: 长线专门定妆+高一致性
- 参考一致性策略: 共享参考图
- 年龄形态继承: 开启
- 角色一致性硬闸: 开启
- 风格锚: STYLE_SHUIHU_SONG_CINEMATIC
- 文字语言: 中文
- 合规用途: demo学习

## 记录

- 已刷新风格一致性报告：生产数据/comic_style_consistency_第5话.md
- 已刷新角色一致性报告：生产数据/comic_character_consistency_第5话.md
- demo学习 用途：字体权利=pending_before_publish，仅记录，不进入发布授权流程。
- demo学习 用途：素材权利=pending_before_publish，仅记录，不进入发布授权流程。
- demo学习 用途：system_font_draft 仅作草稿嵌字字体记录，不进入发布授权流程。
- 已刷新 QA 长图预览：生产数据/qa_previews/第5话_longstrip_preview.webp
- 已刷新 panel contact sheet：生产数据/panel_contact_sheet_第5话.jpg

## 问题清单

| severity | category | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | image | 出图/第5话/panels/P019.png | 疑似烘焙空白气泡已人审签收为误报：原图目检确认候选白区为山间云雾与天空留白，不是烘焙气泡、文字框或乱码。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第5话/panels/P032.png | 疑似烘焙空白气泡已人审签收为误报：原图目检确认候选白区为史太公白衣及院墙亮部，不是烘焙气泡、文字框或乱码。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第5话/panels/P037.png | 疑似烘焙空白气泡已人审签收为误报：原图目检确认候选白区为较场天空与石地高光，不是烘焙气泡、文字框或乱码。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| warn | style | 出图/第5话/panels/P004.png | 风格指纹内聚度 0.6576 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第5话/panels/P007.png | 风格指纹内聚度 0.6881 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第5话/panels/P012.png | 风格指纹内聚度 0.6000 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第5话/panels/P014.png | 风格指纹内聚度 0.7082 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第5话/panels/P022.png | 风格指纹内聚度 0.5620 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第5话/panels/P026.png | 风格指纹内聚度 0.6948 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第5话/panels/P027.png | 风格指纹内聚度 0.6739 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第5话/panels/P031.png | 风格指纹内聚度 0.7124 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第5话/panels/P034.png | 风格指纹内聚度 0.5653 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第5话/panels/P034.png | 同场景“LOC_SHI_TRAINING_YARD”内调色代理偏离组中位：warmth_dev=0.542, tint_dev=0.043。 | comic-image | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | style | 出图/第5话/panels/P012.png | 同场景“LOC_WANG_JIN_HOME”内调色代理偏离组中位：warmth_dev=0.429, tint_dev=0.044。 | comic-image | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | style | 出图/第5话/panels/P004.png | 与同场景锚 LOC_WANG_JIN_HOME 的前一格 P003 相比冷暖/亮度跳变：warmth_jump=0.158, val_jump=0.353；疑似光位翻转或昼夜漂移。 | comic-image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | style | 出图/第5话/panels/P005.png | 与同场景锚 LOC_WANG_JIN_HOME 的前一格 P004 相比冷暖/亮度跳变：warmth_jump=0.129, val_jump=0.352；疑似光位翻转或昼夜漂移。 | comic-image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | style | 出图/第5话/panels/P023.png | 与同场景锚 LOC_SHI_MANOR 的前一格 P022 相比冷暖/亮度跳变：warmth_jump=0.075, val_jump=0.419；疑似光位翻转或昼夜漂移。 | comic-image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | style | 出图/第5话/panels/P035.png | 与同场景锚 LOC_SHI_TRAINING_YARD 的前一格 P034 相比冷暖/亮度跳变：warmth_jump=0.626, val_jump=0.312；疑似光位翻转或昼夜漂移。 | comic-image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | style | 出图/第5话/panels/P002.png | 黑白灰量化偏离话内中位：black_ratio=0.3556（中位 0.029），线宽代理 edge_density=0.1029（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第5话/panels/P004.png | 黑白灰量化偏离话内中位：black_ratio=0.3496（中位 0.029），线宽代理 edge_density=0.0674（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第5话/panels/P012.png | 黑白灰量化偏离话内中位：black_ratio=0.3136（中位 0.029），线宽代理 edge_density=0.0547（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第5话/panels/P022.png | 黑白灰量化偏离话内中位：black_ratio=0.3304（中位 0.029），线宽代理 edge_density=0.0753（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第5话/panels/P034.png | 黑白灰量化偏离话内中位：black_ratio=0.2195（中位 0.029），线宽代理 edge_density=0.0647（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第5话/panels/P036.png | 黑白灰量化偏离话内中位：black_ratio=0.3457（中位 0.029），线宽代理 edge_density=0.1169（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第5话/panels/P044.png | 黑白灰量化偏离话内中位：black_ratio=0.2594（中位 0.029），线宽代理 edge_density=0.116（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第5话/panels/P046.png | 黑白灰量化偏离话内中位：black_ratio=0.3711（中位 0.029），线宽代理 edge_density=0.1142（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/共享/style_baseline.json | 本话整体指纹与风格锚图最高相似度仅 0.8779，风格锚可能已失去约束力。 | comic-image | 并排比对锚图与本话 contact sheet；必要时更新风格锚或统一重抽。 |
| warn | character | 出图/第5话/panels/P036.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.453。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P042.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.446。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P043.png | CHAR_SHI_JIN face 指纹与参考图相似度偏低：score=0.480。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P043.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.369。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P046.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.398。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P004.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.435。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P004.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.334。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P009.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.384。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P012.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.405。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P012.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.385。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P012.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.200。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P022.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.416。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P022.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.256。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P034.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.271。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P034.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.233。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P034.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.124。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P036.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.388。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P036.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.395。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P043.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.338。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P046.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.428。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P046.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.299。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P012.png | CHAR_WANG_MOTHER face 指纹与参考图相似度偏低：score=0.287。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P012.png | CHAR_WANG_MOTHER hair 指纹与参考图相似度偏低：score=0.242。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P012.png | CHAR_WANG_MOTHER outfit 指纹与参考图相似度偏低：score=0.363。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P022.png | CHAR_WANG_MOTHER face 指纹与参考图相似度偏低：score=0.391。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第5话/panels/P022.png | CHAR_WANG_MOTHER hair 指纹与参考图相似度偏低：score=0.194。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |

## 疑似烘焙气泡

- P019: `出图/第5话/panels/P019.png` components=1，已签收为误报
- P032: `出图/第5话/panels/P032.png` components=3，已签收为误报
- P037: `出图/第5话/panels/P037.png` components=3，已签收为误报

## 风格一致性

- 结论：warn
- 摘要：{"panel_count": 48, "finding_count": 24, "block_count": 0, "warn_count": 24, "info_count": 0}

## 角色一致性

- 结论：warn
- 摘要：{"character_count": 5, "panel_binding_count": 75, "finding_count": 26, "block_count": 0, "warn_count": 26, "info_count": 0}
- 并排复核图：`生产数据/qa_previews/第5话_character_consistency_contact_sheet.jpg`
