# 漫画审查报告 — 第1话

- 生成时间：2026-07-18T17:08:04
- 结论：pass
- panel 数：44
- block/warn/info：0 / 0 / 36

## 设置

- 定妆级别: 长线专门定妆+高一致性
- 参考一致性策略: 共享参考图
- 年龄形态继承: 开启
- 角色一致性硬闸: 开启
- 风格锚: STYLE_JPM_MING_GENRE_CINEMATIC
- 文字语言: 中文
- 合规用途: demo学习

## 记录

- 已刷新风格一致性报告：生产数据/comic_style_consistency_第1话.md
- 已刷新角色一致性报告：生产数据/comic_character_consistency_第1话.md
- demo学习 用途：字体权利=pending_before_publish，仅记录，不进入发布授权流程。
- demo学习 用途：素材权利=pending_before_publish，仅记录，不进入发布授权流程。
- demo学习 用途：system_font_draft 仅作草稿嵌字字体记录，不进入发布授权流程。

## 问题清单

| severity | category | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | image | 出图/第1话/panels/P001.png | 疑似烘焙空白气泡已人审签收为误报：放大复核为空间中的白色剑光与雨线，不是气泡或文字框。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P011.png | 疑似烘焙空白气泡已人审签收为误报：放大复核为天空、街面和轿中自然亮部，不是气泡或文字框。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P015.png | 疑似烘焙空白气泡已人审签收为误报：空白候选来自衣袖、窗沿与纸张底色，不是气泡；纸面伪字纹理由后续嵌字前清理单独处理。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P017.png | 疑似烘焙空白气泡已人审签收为误报：放大复核为窗外日光、墙面和蒸汽留白，不是气泡或文字框。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P021.png | 疑似烘焙空白气泡已人审签收为误报：放大复核为逆光天空与街面高光，不是气泡或文字框。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P023.png | 疑似烘焙空白气泡已人审签收为误报：放大复核为袖口、墙面和雪景亮部，不是气泡或文字框。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P025.png | 疑似烘焙空白气泡已人审签收为误报：放大复核为瓷器、雪地与蒸汽亮部，不是气泡或文字框。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P031.png | 疑似烘焙空白气泡已人审签收为误报：放大复核为雪街、衣袖与远景雾光，不是气泡或文字框。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P034.png | 疑似烘焙空白气泡已人审签收为误报：放大复核为瓷器、袖口、蒸汽与雪地亮部，不是气泡或文字框。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P039.png | 疑似烘焙空白气泡已人审签收为误报：放大复核为白袖、蒸饼布和火光，不是气泡或文字框。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P041.png | 疑似烘焙空白气泡已人审签收为误报：放大复核为室内墙面与下层雪路；中间黑横线是脚本要求的双层时间蒙太奇分隔，不是气泡。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P043.png | 疑似烘焙空白气泡已人审签收为误报：放大复核为雪地、鞋面和衣袖亮部，不是气泡或文字框。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | style | 出图/第1话/panels/P028.png | 检测到疑似内部分栏/拼贴 gutter，单个漫画 panel 被模型画成多面板。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P001.png | 风格指纹内聚度 0.4869 明显低于本话中位 0.8436，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P002.png | 风格指纹内聚度 0.7471 明显低于本话中位 0.8436，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P003.png | 风格指纹内聚度 0.7848 明显低于本话中位 0.8436，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P005.png | 风格指纹内聚度 0.7772 明显低于本话中位 0.8436，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P012.png | 风格指纹内聚度 0.7902 明显低于本话中位 0.8436，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P013.png | 风格指纹内聚度 0.7923 明显低于本话中位 0.8436，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P031.png | 风格指纹内聚度 0.8012 明显低于本话中位 0.8436，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P028.png | 与同场景锚 LOC_WU_HOME 的前一格 P027 相比冷暖/亮度跳变：warmth_jump=0.438, val_jump=0.033；疑似光位翻转或昼夜漂移。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P001.png | 黑白灰量化偏离话内中位：black_ratio=0.4259（中位 0.045），线宽代理 edge_density=0.0947（中位 0.131）。疑似网点密度/黑场/线宽口径不统一。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | character | 出图/第1话/panels/P014.png | CHAR_PAN_JINLIAN hair 指纹与参考图相似度偏低：score=0.444。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P029.png | CHAR_PAN_JINLIAN hair 指纹与参考图相似度偏低：score=0.368。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P036.png | CHAR_PAN_JINLIAN hair 指纹与参考图相似度偏低：score=0.445。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P039.png | CHAR_PAN_JINLIAN hair 指纹与参考图相似度偏低：score=0.346。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P039.png | CHAR_WU_DA face 指纹与参考图相似度偏低：score=0.486。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P039.png | CHAR_WU_DA hair 指纹与参考图相似度偏低：score=0.335。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P040.png | CHAR_WU_DA face 指纹与参考图相似度偏低：score=0.367。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P040.png | CHAR_WU_DA hair 指纹与参考图相似度偏低：score=0.318。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P003.png | CHAR_WU_SONG hair 指纹与参考图相似度偏低：score=0.414。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P005.png | CHAR_WU_SONG hair 指纹与参考图相似度偏低：score=0.441。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P029.png | CHAR_WU_SONG hair 指纹与参考图相似度偏低：score=0.448。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P006.png | MON_JINGYANG_TIGER hair 指纹与参考图相似度偏低：score=0.386。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P008.png | MON_JINGYANG_TIGER hair 指纹与参考图相似度偏低：score=0.410。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P009.png | MON_JINGYANG_TIGER hair 指纹与参考图相似度偏低：score=0.385。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |

## 疑似烘焙气泡

- P001: `出图/第1话/panels/P001.png` components=1，已签收为误报
- P011: `出图/第1话/panels/P011.png` components=3，已签收为误报
- P015: `出图/第1话/panels/P015.png` components=1，已签收为误报
- P017: `出图/第1话/panels/P017.png` components=1，已签收为误报
- P021: `出图/第1话/panels/P021.png` components=1，已签收为误报
- P023: `出图/第1话/panels/P023.png` components=2，已签收为误报
- P025: `出图/第1话/panels/P025.png` components=2，已签收为误报
- P031: `出图/第1话/panels/P031.png` components=3，已签收为误报
- P034: `出图/第1话/panels/P034.png` components=1，已签收为误报
- P039: `出图/第1话/panels/P039.png` components=2，已签收为误报
- P041: `出图/第1话/panels/P041.png` components=3，已签收为误报
- P043: `出图/第1话/panels/P043.png` components=1，已签收为误报

## 风格一致性

- 结论：pass
- 摘要：{"panel_count": 44, "finding_count": 10, "block_count": 0, "warn_count": 0, "info_count": 10}

## 角色一致性

- 结论：pass
- 摘要：{"character_count": 5, "panel_binding_count": 74, "finding_count": 14, "block_count": 0, "warn_count": 0, "info_count": 14}
- 并排复核图：`生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg`
