---
name: comic-layout
description: 画漫画排版阶段。Use when turning panel_script.json and optional name_board.json into page or long-scroll layouts, manuscript safe areas, reading order, panel rectangles, gutters, bubble placeholders, and layout.json for comic projects under 创作区/画漫画. Triggers 漫画排版, 页面排版, 条漫排版, 分格排版, 原稿安全区, 气泡占位, 阅读顺序, layout.json, comic-layout.
---

# comic-layout — 页面/条漫排版

把 `panel_script.json` 转成可出图、可嵌字、可审查的 `layout.json`。本阶段决定阅读顺序、格子尺寸、留白、节奏和气泡占位，不负责生成最终图像。

**形态支持边界**：deterministic 脚本 `build_layout.py` 只会产出单列条漫几何（layout 会带 `geometry_profile=longstrip_single_column` 与 `format_supported_by_script` 标记）。`漫画形态=页漫/四格` 时，页内多格网格、RTL 阅读方向和分页装订必须由人工或 agent 重排 layout.json；不重排直接出图会被 `comic-review gate` 的 `format_geometry_mismatch` 阻断。

## 输入

- `_设置.md`：漫画形态、阅读方向、页面尺寸、单话分段高度、原稿规格。
- `脚本/第N话/panel_script.json`。
- 可选 `排版/第N话/name_board.json`：缩略分镜、页流、格子轻重、气泡优先级和原稿安全框。
- `设定库/story_bible.md`：角色重要性和视觉重心。

## 输出

- `排版/第N话/layout.json`：schema 见 `references/layout_schema.md`，会继承 `name_board.json` 的 manuscript、page_side、spread_id、page_turn_hook、bubble_first、effects_hint 等元数据。
- 可选 `排版/第N话/layout_notes.md`：说明大格、留白、气泡风险、出图注意。
- `_进度.md`：完成后把 `页面排版` 标为 `✅`。

## 怎么跑

已有 `panel_script.json` 后，可先生成 MVP 条漫排版：

```bash
python3 skills/comic-layout/scripts/build_layout.py "创作区/画漫画/作品名" --chapter 第1话
```

脚本只用标准库，会读取 `_设置.md` 的页面宽度、漫画形态和阅读方向，写 `layout.json` / `layout_notes.md`，并把本话 `页面排版` 标为 `✅`。正式发布前仍需人工检查气泡是否遮挡脸、手、刀、妖物或关键动作。

需要快速审节奏和气泡占位时，可渲染 SVG 分格草图：

```bash
python3 skills/comic-layout/scripts/render_storyboard_svg.py "创作区/画漫画/作品名" --chapter 第1话
```

## 工作流

1. 读 `panel_script.json`；若存在 `name_board.json`，优先继承ネーム层的格子轻重、页流和原稿安全框。
2. 按 `_设置.md` 判断 `条漫` / `页漫` / `四格`。
3. 建立阅读顺序：同一屏或同一页不要让视线倒流。
4. 给每格写矩形 `x/y/w/h`，并预留 gutter 和安全边距。
5. 给台词、旁白、拟声词预留 `bubble_slots`，避免遮挡脸、手、关键道具和动作接触点。
6. 输出 `layout.json`。如果文本过多，回 `comic-script` 压缩台词；如果页流或翻页钩子不顺，回 `comic-name` 改 name board；不要靠缩小字号硬塞。
7. 回写 `_进度.md` 的 `页面排版`。

## 排版原则

- 条漫：用高低错落制造停顿，大格之间留足呼吸；每 3-6 格设置一次视觉节奏变化。
- 页漫：每页要有页内入口和页末推动；双页或跨页必须明确阅读方向。
- 四格：每格承担固定节奏，最后一格必须有反差、包袱或信息翻转。
- 气泡先占位，文字后合成；不要用最终文字改动格子尺寸造成返工。
- `layout.json` 坐标稳定后，出图和嵌字都以它为准。

## 不做什么

- 不生成图片；那是 `comic-image`。
- 不嵌最终文字；那是 `comic-compose`。
- 不靠一张无限高草图替代结构化 layout。
