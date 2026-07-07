# 漫画审查报告 — 第2话

- 生成时间：2026-07-07T20:01:19
- 结论：pass
- panel 数：14
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

- 已刷新风格一致性报告：生产数据/comic_style_consistency_第2话.md
- demo学习 用途：字体权利=pending_before_publish，仅记录，不进入发布授权流程。
- demo学习 用途：素材权利=pending_before_publish，仅记录，不进入发布授权流程。
- demo学习 用途：system_font_draft 仅作草稿嵌字字体记录，不进入发布授权流程。
- 已刷新 QA 长图预览：生产数据/qa_previews/第2话_longstrip_preview.webp
- 已刷新 panel contact sheet：生产数据/panel_contact_sheet_第2话.jpg

## 问题清单

| severity | category | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | image | 出图/第2话/panels/P013.png | 疑似烘焙空白气泡已人审签收为误报：成品审查命中的白色连通区域是右侧高亮天空、雾光和旗影，不是对白气泡、旁白框或烘焙文字容器；画面无文字、水印、logo。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第2话/panels/P014.png | 疑似烘焙空白气泡已人审签收为误报：成品审查命中的右上角亮区是天空和雾光留白，不是对白气泡、旁白框或烘焙文字容器；画面无文字、水印、logo。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | style | 出图/第2话/panels/P004.png | 风格指纹内聚度 0.8703 明显低于本话中位 0.9152，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第2话/panels/P006.png | 风格指纹内聚度 0.8251 明显低于本话中位 0.9152，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第2话/panels/P008.png | 风格指纹内聚度 0.8643 明显低于本话中位 0.9152，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第2话/panels/P010.png | 风格指纹内聚度 0.7788 明显低于本话中位 0.9152，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第2话/panels/P011.png | 风格指纹内聚度 0.8467 明显低于本话中位 0.9152，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第2话/panels/P010.png | 同场景“LOC_WASTELAND”内调色代理偏离组中位：warmth_dev=0.254, tint_dev=0.020。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |

## 疑似烘焙气泡

- P013: `出图/第2话/panels/P013.png` components=1，已签收为误报
- P014: `出图/第2话/panels/P014.png` components=1，已签收为误报

## 风格一致性

- 结论：pass
- 摘要：{"panel_count": 14, "finding_count": 6, "block_count": 0, "warn_count": 0, "info_count": 6}
