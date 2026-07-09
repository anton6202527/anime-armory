# 漫画审查报告 — 第3话

- 生成时间：2026-07-09T14:31:48
- 结论：pass
- panel 数：16
- block/warn/info：0 / 0 / 4

## 设置

- 定妆级别: 长线专门定妆
- 参考一致性策略: 共享参考图
- 年龄形态继承: 开启
- 角色一致性硬闸: 关闭
- 风格锚: 用户提供女主参考图；仅锁姜月初脸型、眼型、发质、气质和黑白仙侠审美，不继承拼图版式、水印、平台 UI、伞和头冠为固定剧情设定
- 文字语言: 中文
- 合规用途: demo学习

## 记录

- 已刷新风格一致性报告：生产数据/comic_style_consistency_第3话.md
- 已刷新角色一致性报告：生产数据/comic_character_consistency_第3话.md
- demo学习 用途：字体权利=pending_before_publish，仅记录，不进入发布授权流程。
- demo学习 用途：素材权利=pending_before_publish，仅记录，不进入发布授权流程。
- demo学习 用途：system_font_draft 仅作草稿嵌字字体记录，不进入发布授权流程。
- 已刷新 QA 长图预览：生产数据/qa_previews/第3话_longstrip_preview.webp
- 已刷新 panel contact sheet：生产数据/panel_contact_sheet_第3话.jpg

## 问题清单

| severity | category | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | image | 出图/第3话/panels/P001.png | 疑似烘焙空白气泡已人审签收为误报：机检命中的左上亮区是满月高光和薄云留白，不是对白气泡、旁白框或烘焙文字容器；画面无文字、水印、logo。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | style | 出图/第3话/panels/P006.png | 风格指纹内聚度 0.7810 明显低于本话中位 0.8771，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第3话/panels/P011.png | 风格指纹内聚度 0.7720 明显低于本话中位 0.8771，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | character | 出图/第3话/panels/P010.png | CHAR_JYC face 指纹与参考图相似度偏低：score=0.491。这是启发式提示，需并排人审。 | comic-review | 若 P010 后续重抽或改构图，重新运行 character_consistency.py 并重新签收。 |

## 疑似烘焙气泡

- P001: `出图/第3话/panels/P001.png` components=1，已签收为误报

## 风格一致性

- 结论：pass
- 摘要：{"panel_count": 16, "finding_count": 2, "block_count": 0, "warn_count": 0, "info_count": 2}

## 角色一致性

- 结论：pass
- 摘要：{"character_count": 2, "panel_binding_count": 15, "finding_count": 1, "block_count": 0, "warn_count": 0, "info_count": 1}
- 并排复核图：`生产数据/qa_previews/第3话_character_consistency_contact_sheet.jpg`
