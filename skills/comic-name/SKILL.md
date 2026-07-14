---
name: comic-name
description: 漫画缩略分镜/ネーム阶段。Use when turning panel_script.json into traditional manga name boards, page-turn rhythm, thumbnail panel plans, rough eye-flow, gutter intent, manuscript-safe roughs, or a storyboard SVG before final layout. Triggers 缩略分镜, ネーム, name, name board, manga thumbnails, 漫画草稿分镜, 页流, 翻页钩子, comic-name.
---

# comic-name — 缩略分镜 / ネーム

把 `panel_script.json` 转成传统漫画生产里的 `ネーム`：先用小图解决阅读顺序、页流、大小格节奏、翻页钩子、气泡优先级和原稿安全区，再进入 `comic-layout` 精排。它不生成最终图，也不替代角色定妆。

## 输入

- `_设置.md`：漫画形态、阅读方向、页面尺寸、原稿规格、版式模板策略。
- `脚本/第N话/panel_script.json`。
- 可选：`设定库/story_bible.md` 的角色/场景重要性说明。

## 输出

- `排版/第N话/name_board.json`：schema 见 `references/name_board_schema.md`。
- `排版/第N话/name/name_board.svg`：低保真缩略分镜板，便于人工快速看节奏。
- `_进度.md`：默认草案只写 `🟡待签收`；只有当前上游 SHA、结构校验和人工审批收据同时有效才把 `缩略分镜` 标为 `✅`。

## 怎么跑

```bash
python3 skills/comic-name/scripts/build_name_board.py "创作区/画漫画/作品名" --chapter 第1话
```

脚本只用标准库。它会按 `story_function`、`layout_weight`、台词量和拟声词粗分大格/中格/小格；页漫会额外记录 `page_side`、`spread_id`、`page_turn_hook`，条漫会记录每个滚动段的停顿和呼吸。`panel_script.json` 若逐格提供数字 `page_hint`，会优先按明确页意图分组；只有没有完整 page_hint 时才回退到通用每页格数，避免自动平均切页破坏翻页钩子。

首次运行永远生成 `workflow_status=draft`，不会免费越过编辑签收。审阅后按两步变更状态：

```bash
python3 skills/comic-name/scripts/build_name_board.py "创作区/画漫画/作品名" --chapter 第1话 --submit-review
python3 skills/comic-name/scripts/build_name_board.py "创作区/画漫画/作品名" --chapter 第1话 --approve --reviewed-by "签收人"
```

正式进入排版前可只读复核审批及上游是否仍新鲜：

```bash
python3 skills/comic-name/scripts/build_name_board.py "创作区/画漫画/作品名" --chapter 第1话 --check
```

`page_hint` 必须全部提供或全部省略，且按 panel 阅读顺序单调不减；部分填写、非整数或回退页号会直接失败，不会静默重排。

## 工作流

1. 读分格脚本，确认每格 `story_function`、画面事实、对白/旁白/拟声词。
2. 先做缩略图，不追求美术细节，只决定格子轻重、阅读入口、视线流和页末钩子。
3. 给每格写 `thumbnail_rect`、`panel_shape`、`border_style`、`gutter_intent`、`bubble_first`、`effects_hint`，并为气泡记录 `content_ref/speaker/order/tail`。
4. 给每格记录 subject/avoid regions、视线入口/出口；这些自动区域是低保真启发式，只服务后续排版，不作为审美硬闸。
5. 记录原稿口径：`trim_box`、`safe_area`、`bleed`、`inner_frame`。
6. 每个翻页记录最后一格 setup 与下一页首格 payoff，不能把页中间的重格误记成翻页钩子。
7. 输出 draft JSON/SVG；若页流或文字密度不顺，回 `comic-script` 改分格。
8. 人工提交 review 并签收；签收收据绑定 board 内容、`panel_script` 与 `_设置.md` SHA，之后再跑 `comic-layout`。

## 原则

- ネーム先解决“读得顺不顺”，不是精修画面。
- 页漫关注翻页钩子、左右页、跨页节奏；条漫关注滚动停顿、屏间呼吸和大格冲击。
- 大格必须服务钩子、揭示、动作峰值或情绪停顿；不能只是平均堆格。
- 气泡优先级在ネーム阶段先定，避免成图后发现文字挡脸、手、道具或动作接触点。

## 不做什么

- 不生成最终 layout 的像素级坐标；那是 `comic-layout`。
- 不生成面板图；那是 `comic-image`。
- 不做最终嵌字；那是 `comic-compose`。
