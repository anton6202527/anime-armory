# 漫画审查报告 — 第1话

- 生成时间：2026-07-21T22:11:04
- 结论：revise
- panel 数：16
- block/warn/info：0 / 36 / 1

## 设置

- 定妆级别: 长线专门定妆+高一致性
- 参考一致性策略: 共享参考图
- 年龄形态继承: 开启
- 角色一致性硬闸: 开启
- 风格锚: STYLE_LIAOZHAI_QING_GONGXI
- 文字语言: 中文
- 合规用途: 自用草稿

## 记录

- 已刷新风格一致性报告：生产数据/comic_style_consistency_第1话.md
- 已刷新角色一致性报告：生产数据/comic_character_consistency_第1话.md
- 自用草稿 用途：字体权利=pending_before_publish，仅记录，不进入发布授权流程。
- 自用草稿 用途：素材权利=pending_before_publish，仅记录，不进入发布授权流程。
- 自用草稿 用途：system_font_draft 仅作草稿嵌字字体记录，不进入发布授权流程。
- 已刷新 QA 长图预览：生产数据/qa_previews/第1话_longstrip_preview.webp
- 已刷新 panel contact sheet：生产数据/panel_contact_sheet_第1话.jpg

## 问题清单

| severity | category | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| warn | visual_contract | 脚本/第1话/panel_script.json#P001 | P001 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P006 | P006 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P008 | P008 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P009 | P009 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P011 | P011 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P012 | P012 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P013 | P013 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P014 | P014 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P015 | P015 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P016 | P016 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| info | lettering | 排版/第1话/export_manifest.json | manifest 未记录嵌字槽位 QC 接触表，长条图过高时不便逐字复核 | comic-compose | 用 export_longstrip.py --render --qc-slots 重新导出 |
| warn | export | 排版/export_manifest.json | 自定义(红果式移动端节奏内审，不作为发布平台规格) 平台规格未有当前可机检的一手尺寸证据。 | comic-compose | 发布/商用前在平台后台或官方文档核验宽度、高度、格式、文件大小，并更新 platform profile。 |
| warn | style | 出图/第1话/panels/P005.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P006.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P007.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P008.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P009.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P010.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P011.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P012.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P001.png | 风格指纹内聚度 0.6497 明显低于本话中位 0.7778，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第1话/panels/P001.png | 黑白灰量化偏离话内中位：black_ratio=0.5191（中位 0.123），线宽代理 edge_density=0.0763（中位 0.099）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第1话/panels/P005.png | 黑白灰量化偏离话内中位：black_ratio=0.3501（中位 0.123），线宽代理 edge_density=0.0864（中位 0.099）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第1话/panels/P012.png | 黑白灰量化偏离话内中位：black_ratio=0.5788（中位 0.123），线宽代理 edge_density=0.0694（中位 0.099）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第1话/panels/P013.png | 黑白灰量化偏离话内中位：black_ratio=0.3048（中位 0.123），线宽代理 edge_density=0.1209（中位 0.099）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第1话/panels/P016.png | 黑白灰量化偏离话内中位：black_ratio=0.0437（中位 0.123），线宽代理 edge_density=0.1732（中位 0.099）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | character | 出图/第1话/panels/P011.png | CHAR_CHEN hair 指纹与参考图相似度偏低：score=0.437。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P012.png | CHAR_CHEN hair 指纹与参考图相似度偏低：score=0.410。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P006.png | CHAR_DAOIST hair 指纹与参考图相似度偏低：score=0.319。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P002.png | CHAR_WANG face 指纹与参考图相似度偏低：score=0.452。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P004.png | CHAR_WANG hair 指纹与参考图相似度偏低：score=0.430。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P005.png | CHAR_WANG outfit 指纹与参考图相似度偏低：score=0.382。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P006.png | CHAR_WANG face 指纹与参考图相似度偏低：score=0.450。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P006.png | CHAR_WANG hair 指纹与参考图相似度偏低：score=0.275。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P007.png | CHAR_WANG face 指纹与参考图相似度偏低：score=0.427。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P007.png | CHAR_WANG hair 指纹与参考图相似度偏低：score=0.424。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P001.png | MON_PAINTED_SKIN hair 指纹与参考图相似度偏低：score=0.429。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |

## 风格一致性

- 结论：warn
- 摘要：{"panel_count": 16, "finding_count": 14, "block_count": 0, "warn_count": 14, "info_count": 0}

## 角色一致性

- 结论：warn
- 摘要：{"character_count": 5, "panel_binding_count": 32, "finding_count": 11, "block_count": 0, "warn_count": 11, "info_count": 0}
- 并排复核图：`生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg`
