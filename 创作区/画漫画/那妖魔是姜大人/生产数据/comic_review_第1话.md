# 漫画审查报告 — 第1话

- 生成时间：2026-07-08T22:49:01
- 结论：pass
- panel 数：16
- block/warn/info：0 / 0 / 8

## 设置

- 定妆级别: 长线专门定妆
- 参考一致性策略: 共享参考图
- 年龄形态继承: 开启
- 角色一致性硬闸: 关闭
- 风格锚: 用户提供女主参考图；仅锁姜月初脸型、眼型、发质、气质和黑白仙侠审美，不继承拼图版式、水印、平台 UI、伞和头冠为固定剧情设定
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
| info | image | 出图/第1话/panels/P004.png | 疑似烘焙空白气泡已人审签收为误报：候选区域位于右侧天空和荒野雾面，是预留对白位置附近的自然亮部，不是模型烘焙的空白气泡或文字框。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P008.png | 疑似烘焙空白气泡已人审签收为误报：候选区域位于右上天空/雾光留白，用于后期对白，不含气泡边框、尾巴或文字容器。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P010.png | 疑似烘焙空白气泡已人审签收为误报：候选区域是虎妖复起大格的逆光天空/烟雾亮面，不是烘焙空白气泡；最终对白由 comic-compose 后期绘制。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | style | 出图/第1话/panels/P001.png | 风格指纹内聚度 0.7469 明显低于本话中位 0.8843，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P002.png | 风格指纹内聚度 0.7122 明显低于本话中位 0.8843，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P003.png | 风格指纹内聚度 0.8420 明显低于本话中位 0.8843，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P010.png | 风格指纹内聚度 0.8389 明显低于本话中位 0.8843，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P013.png | 风格指纹内聚度 0.8360 明显低于本话中位 0.8843，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |

## 疑似烘焙气泡

- P004: `出图/第1话/panels/P004.png` components=1，已签收为误报
- P008: `出图/第1话/panels/P008.png` components=1，已签收为误报
- P010: `出图/第1话/panels/P010.png` components=1，已签收为误报

## 风格一致性

- 结论：pass
- 摘要：{"panel_count": 16, "finding_count": 5, "block_count": 0, "warn_count": 0, "info_count": 5}

## 角色一致性

- 结论：pass
- 摘要：{"character_count": 2, "panel_binding_count": 22, "finding_count": 0, "block_count": 0, "warn_count": 0, "info_count": 0}
- 并排复核图：`生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg`
