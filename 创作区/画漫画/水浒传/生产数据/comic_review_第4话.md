# 漫画审查报告 — 第4话

- 生成时间：2026-07-18T19:02:00
- 结论：block
- panel 数：46
- block/warn/info：4 / 19 / 0

## 设置

- 定妆级别: 长线专门定妆+高一致性
- 参考一致性策略: 共享参考图
- 年龄形态继承: 开启
- 角色一致性硬闸: 开启
- 风格锚: STYLE_SHUIHU_SONG_CINEMATIC
- 文字语言: 中文
- 合规用途: demo学习

## 记录

- 已刷新风格一致性报告：生产数据/comic_style_consistency_第4话.md
- 已刷新角色一致性报告：生产数据/comic_character_consistency_第4话.md
- demo学习 用途：字体权利=pending_before_publish，仅记录，不进入发布授权流程。
- demo学习 用途：素材权利=pending_before_publish，仅记录，不进入发布授权流程。
- 已刷新 panel contact sheet：生产数据/panel_contact_sheet_第4话.jpg

## 问题清单

| severity | category | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| block | missing_artifact | 排版/第4话/lettering.json | 审查必需文件缺失 | comic-compose | 补齐文件后重新运行 comic-review |
| block | missing_artifact | 排版/第4话/export_manifest.json | 审查必需文件缺失 | comic-compose | 补齐文件后重新运行 comic-review |
| block | export | 排版/第4话/export_manifest.json | manifest 缺少 layout 中的 panel：P001, P002, P003, P004, P005, P006, P007, P008, P009, P010, P011, P012, P013, P014, P015, P016, P017, P018, P019, P020, P021, P022, P023, P024, P025, P026, P027, P028, P029, P030, P031, P032, P033, P034, P035, P036, P037, P038, P039, P040, P041, P042, P043, P044, P045, P046 | comic-compose | 重新导出 manifest/长图 |
| block | export | 排版/第4话/export_manifest.json | 未登记实际渲染导出物 | comic-compose | 运行 export_longstrip.py --render |
| warn | image | 出图/第4话/panels | 原始面板图疑似烘焙了空白气泡/文字容器：P002, P008, P009, P012, P015, P016, P021 | comic-image | 后续重抽这些格时要求无字画面、无空白气泡，只保留低细节留白；系统绘卷等叙事道具可人工豁免 |
| warn | style | 出图/第4话/panels/P005.png | 风格指纹内聚度 0.7680 明显低于本话中位 0.8422，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第4话/panels/P007.png | 风格指纹内聚度 0.7062 明显低于本话中位 0.8422，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第4话/panels/P013.png | 风格指纹内聚度 0.7811 明显低于本话中位 0.8422，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第4话/panels/P014.png | 风格指纹内聚度 0.7801 明显低于本话中位 0.8422，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第4话/panels/P016.png | 风格指纹内聚度 0.7923 明显低于本话中位 0.8422，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第4话/panels/P023.png | 风格指纹内聚度 0.7474 明显低于本话中位 0.8422，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第4话/panels/P027.png | 风格指纹内聚度 0.7897 明显低于本话中位 0.8422，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第4话/panels/P028.png | 风格指纹内聚度 0.7623 明显低于本话中位 0.8422，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第4话/panels/P030.png | 风格指纹内聚度 0.7506 明显低于本话中位 0.8422，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第4话/panels/P032.png | 风格指纹内聚度 0.7805 明显低于本话中位 0.8422，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第4话/panels/P043.png | 风格指纹内聚度 0.7085 明显低于本话中位 0.8422，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第4话/panels/P044.png | 风格指纹内聚度 0.7933 明显低于本话中位 0.8422，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第4话/panels/P045.png | 风格指纹内聚度 0.7301 明显低于本话中位 0.8422，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第4话/panels/P046.png | 风格指纹内聚度 0.8016 明显低于本话中位 0.8422，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/共享/style_baseline.json | 本话整体指纹与风格锚图最高相似度仅 0.8777，风格锚可能已失去约束力。 | comic-image | 并排比对锚图与本话 contact sheet；必要时更新风格锚或统一重抽。 |
| warn | character | 出图/第4话/panels/P027.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.394。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第4话/panels/P039.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.495。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第4话/panels/P042.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.404。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |

## 疑似烘焙气泡

- P002: `出图/第4话/panels/P002.png` components=1，待处理
- P008: `出图/第4话/panels/P008.png` components=1，待处理
- P009: `出图/第4话/panels/P009.png` components=3，待处理
- P012: `出图/第4话/panels/P012.png` components=2，待处理
- P015: `出图/第4话/panels/P015.png` components=1，待处理
- P016: `出图/第4话/panels/P016.png` components=2，待处理
- P021: `出图/第4话/panels/P021.png` components=1，待处理

## 风格一致性

- 结论：warn
- 摘要：{"panel_count": 46, "finding_count": 15, "block_count": 0, "warn_count": 15, "info_count": 0}

## 角色一致性

- 结论：warn
- 摘要：{"character_count": 4, "panel_binding_count": 70, "finding_count": 3, "block_count": 0, "warn_count": 3, "info_count": 0}
- 并排复核图：`生产数据/qa_previews/第4话_character_consistency_contact_sheet.jpg`
