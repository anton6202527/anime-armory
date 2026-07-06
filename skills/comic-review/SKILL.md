---
name: comic-review
description: 画漫画审查阶段。Use when reviewing comic scripts, layouts, panel art, lettering, long-scroll exports, readability, panel order, text overlap, character consistency, source adaptation faithfulness, platform deliverable readiness, or rework lists for projects under 创作区/画漫画. Triggers 漫画审查, 漫画质检, 阅读顺序, 遮挡, 角色一致性, 台词太多, 长图检查, 发布前检查, comic-review.
---

# comic-review — 漫画审查与返修

审查漫画是否读得顺、看得清、角色不漂、文字不挡、导出规格可用。它不生产新内容，只产问题清单、返修建议和发布前判断。

## 输入

- `_进度.md`、`_设置.md`。
- `脚本/第N话/panel_script.json`。
- `排版/第N话/layout.json`、`lettering.json`、`export_manifest.json`。
- `出图/第N话/panels/`。
- 可选源本、故事圣经和共享参考。

## 输出

- `生产数据/comic_review_第N话.json`。
- `生产数据/comic_review_第N话.md`。
- `_进度.md`：人工或机器审查通过后，把 `审查` 标 `✅`；有阻断问题时不回写完成。

## 审查维度

| 维度 | 检查点 |
|---|---|
| 阅读顺序 | 视线是否自然，页漫/条漫方向是否一致 |
| 叙事闭环 | 本话是否有钩子、冲突、推进、转折或收束 |
| 分格密度 | 单格信息是否过载，台词是否过长 |
| 画面可读性 | 主体、表情、动作、道具是否清楚 |
| 气泡遮挡 | 是否挡脸、手、关键动作、重要道具 |
| 角色一致性 | 脸、发型、服装、标志物是否跨格稳定 |
| 文字质量 | 错字、标点、语气、拟声词是否统一 |
| 导出规格 | 长图分段、尺寸、缺图、manifest 是否齐全 |
| 合规发布 | 字体、素材、源本、第三方资产状态是否可追溯 |

详细 checklist 见 `references/review_checklist.md`。

## 处理结论

- `pass`：可进入发布或归档。
- `revise`：有问题但可局部修。
- `block`：阅读顺序、缺图、严重遮挡、角色大漂、权利不明等问题阻断发布。

对每个问题写明：

- `severity`：block / warn / info。
- `artifact`：具体文件或 panel_id。
- `reason`：为什么影响阅读或发布。
- `return_to`：回 `comic-script` / `comic-layout` / `comic-image` / `comic-compose`。
- `suggested_fix`：最小返修动作。

## 不做什么

- 不直接重写脚本或重出图。
- 不用主观“好看/不好看”当硬阻断；阻断要落到可定位的阅读、画面、文字、导出或合规问题。
- 不把草稿字体授权当正式发布授权。
