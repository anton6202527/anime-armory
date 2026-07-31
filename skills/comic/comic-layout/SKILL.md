---
name: comic-layout
description: 画漫画排版阶段。Use when turning panel_script.json and optional name_board.json into page or long-scroll layouts, manuscript safe areas, reading order, panel rectangles, gutters, bubble placeholders, and layout.json for comic projects under 创作区/画漫画. Triggers 漫画排版, 页面排版, 条漫排版, 分格排版, 原稿安全区, 气泡占位, 阅读顺序, layout.json, comic-layout.
---

# comic-layout — 页面/条漫排版

把 `panel_script.json` 转成可出图、可嵌字、可审查的 `layout.json`。本阶段决定阅读顺序、格子尺寸、留白、节奏和气泡占位，不负责生成最终图像。

deterministic adapter 现支持三个最低可靠几何 profile：条漫 `longstrip_single_column`、页漫 `paged_grid_ltr|paged_grid_rtl`、四格 `yonkoma_four_rows`。它严格消费已签收缩略分镜/name board 的 page grouping、`thumbnail_rect`、格子轻重、gutter、气泡语义和 subject/avoid regions；复杂跨页、破格、斜格或特殊装帧仍需人工或用户授权的制作代理调整并重新签收。

## 输入

- `_设置.md`：漫画形态、阅读方向、页面尺寸、单话分段高度、原稿规格。
- `脚本/第N话/panel_script.json`。
- 必需 `排版/第N话/name_board.json` schema v2：必须为 `approved`，审批 SHA 与当前 `panel_script` / `_设置.md` 同时有效。
- `设定库/story_bible.md`：角色重要性和视觉重心。

## 输出

- `排版/第N话/layout.json`：schema 见 `references/layout_schema.md`，会继承 `name_board.json` 的 manuscript、page_side、spread_id、page_turn_hook、bubble_first、effects_hint 等元数据。
- 可选 `排版/第N话/layout_notes.md`：说明大格、留白、气泡风险、出图注意。
- `_进度.md`：默认 layout 草案只写 `🟡待签收`；validator 与人工或已授权制作代理的审批均有效后才把 `页面排版` 标为 `✅`。

## 怎么跑

已有已签收 name board 后生成排版草案：

```bash
python3 skills/comic/comic-layout/scripts/build_layout.py "创作区/画漫画/作品名" --chapter 第1话
```

首次运行只写 `workflow_status=draft`。人工检查页面节奏、气泡和关键动作可读性后按两步签收：

```bash
python3 skills/comic/comic-layout/scripts/build_layout.py "创作区/画漫画/作品名" --chapter 第1话 --submit-review
python3 skills/comic/comic-layout/scripts/build_layout.py "创作区/画漫画/作品名" --chapter 第1话 --approve --reviewed-by "签收人"
```

进入出图前只读检查当前 layout、name 审批和所有上游 SHA：

```bash
python3 skills/comic/comic-layout/scripts/build_layout.py "创作区/画漫画/作品名" --chapter 第1话 --check
```

旧 schema v1 只能用显式 `--allow-legacy-name` 生成迁移草案，receipt 会记录 waiver；正常批跑与收尾不会用该参数越过正式签收。

需要快速审节奏和气泡占位时，可渲染 SVG 分格草图：

```bash
python3 skills/comic/comic-layout/scripts/render_storyboard_svg.py "创作区/画漫画/作品名" --chapter 第1话
```

条漫应同时按1440px母版、手机可视窗口和目标平台导出规格审阅；平台规格与制作代理的证据化检查见 [条漫排版与代理审阅](references/条漫排版与代理审阅.md)。

## 工作流

1. 读 `panel_script.json` 与已签收 `name_board.json`；任何一个缺失、SHA 过期或覆盖顺序不同都停止。
2. 按 `_设置.md` 判断 `条漫` / `页漫` / `四格`。
3. 建立阅读顺序：同一屏或同一页不要让视线倒流。
4. 给每格写矩形 `x/y/w/h`，并预留 gutter 和安全边距。
5. 给台词、旁白、拟声词预留 `bubble_slots`，避免遮挡脸、手、关键道具和动作接触点。
6. 运行确定性 validator：panel ID 唯一且同序覆盖，矩形不重叠/不越界，阅读顺序一致，每段正文/SFX 都有界内 bubble slot。
7. 输出 draft `layout.json`。如果文字过多，回 `comic-script`；如果页流不顺，回 `comic-name`，不要靠缩小字号硬塞。
8. 人工或项目内已授权制作代理签收后写 SHA-bound approval receipt，才回写 `_进度.md` 的 `页面排版=✅`；代理不得越过确定性阻断或授权边界。

## 排版原则

- 条漫：用高低错落制造停顿，大格之间留足呼吸；每 3-6 格设置一次视觉节奏变化。
- 页漫：每页要有页内入口和页末推动；双页或跨页必须明确阅读方向。
- 四格 adapter：每页严格四个纵向行格；最后一格的叙事质量由编辑审阅，脚本不靠关键词启发式硬阻断。
- 气泡先占位，文字后合成；不要用最终文字改动格子尺寸造成返工。
- `layout.json` 坐标稳定后，出图和嵌字都以它为准。

## 不做什么

- 不生成图片；那是 `comic-image`。
- 不嵌最终文字；那是 `comic-compose`。
- 不靠一张无限高草图替代结构化 layout。
