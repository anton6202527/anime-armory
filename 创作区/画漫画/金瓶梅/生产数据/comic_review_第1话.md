# 漫画审查报告 — 第1话

- 生成时间：2026-07-09T18:29:30
- 结论：pass
- panel 数：18
- block/warn/info：0 / 0 / 7

## 设置

- 定妆级别: 长线专门定妆
- 参考一致性策略: 高一致性长线
- 年龄形态继承: 开启
- 角色一致性硬闸: 开启
- 风格锚: 古典世情水墨写实；宋代市井、酒肆、县衙、宅院、街巷；欲望与权势以物件和光影暗示，不画露骨性行为
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
| info | image | 出图/第1话/panels/P001.png | 疑似烘焙空白气泡已人审签收为误报：P001 是计划内象征序幕，检测到的空白亮部为刀光/烟雾留白，不是烘焙空白气泡或文字容器；全话嵌字仍由后期完成。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | style | 出图/第1话/panels/P001.png | 风格指纹内聚度 0.7679 明显低于本话中位 0.8880，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P002.png | 风格指纹内聚度 0.7925 明显低于本话中位 0.8880，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P006.png | 风格指纹内聚度 0.7866 明显低于本话中位 0.8880，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P012.png | 风格指纹内聚度 0.6008 明显低于本话中位 0.8880，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P013.png | 风格指纹内聚度 0.8326 明显低于本话中位 0.8880，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P014.png | 风格指纹内聚度 0.8179 明显低于本话中位 0.8880，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |

## 疑似烘焙气泡

- P001: `出图/第1话/panels/P001.png` components=1，已签收为误报

## 风格一致性

- 结论：pass
- 摘要：{"panel_count": 18, "finding_count": 6, "block_count": 0, "warn_count": 0, "info_count": 6}

## 角色一致性

- 结论：pass
- 摘要：{"character_count": 5, "panel_binding_count": 29, "finding_count": 0, "block_count": 0, "warn_count": 0, "info_count": 0}
- 并排复核图：`生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg`
