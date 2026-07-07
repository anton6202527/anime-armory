# 漫画审查报告 — 第2话

- 生成时间：2026-07-07T17:26:24
- 结论：revise
- panel 数：18
- block/warn/info：0 / 4 / 0

## 设置

- 定妆级别: 长线专门定妆+n2d级一致性
- 参考一致性策略: n2d级共享参考图+多视图+形态继承
- 年龄形态继承: 开启
- 角色一致性硬闸: 开启
- 风格锚: STYLE_XIANJIE_CINEMATIC_REALISTIC_GUOMAN
- 文字语言: 中文
- 合规用途: 内部打样

## 记录

- 已刷新风格一致性报告：生产数据/comic_style_consistency_第2话.md
- 内部打样 用途：字体权利=pending_before_publish，仅记录，不进入发布授权流程。
- 内部打样 用途：素材权利=pending_before_publish，仅记录，不进入发布授权流程。
- 内部打样 用途：system_font_draft 仅作草稿嵌字字体记录，不进入发布授权流程。
- 已刷新 QA 长图预览：生产数据/qa_previews/第2话_longstrip_preview.webp
- 已刷新 panel contact sheet：生产数据/panel_contact_sheet_第2话.jpg

## 问题清单

| severity | category | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| warn | style | 出图/第2话/panels/P001.png | 风格指纹内聚度 0.8525 明显低于本话中位 0.9128，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第2话/panels/P007.png | 风格指纹内聚度 0.8666 明显低于本话中位 0.9128，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第2话/panels/P009.png | 风格指纹内聚度 0.8536 明显低于本话中位 0.9128，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第2话/panels/P015.png | 风格指纹内聚度 0.8562 明显低于本话中位 0.9128，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |

## 风格一致性

- 结论：warn
- 摘要：{"panel_count": 18, "finding_count": 4, "block_count": 0, "warn_count": 4, "info_count": 0}
