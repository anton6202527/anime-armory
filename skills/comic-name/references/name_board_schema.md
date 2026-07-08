# name_board.json schema

`name_board.json` 是传统漫画ネーム层。它介于 `panel_script.json` 和 `layout.json` 之间，用低保真结构锁页流、格子轻重、翻页钩子和原稿安全区。

最小结构：

```json
{
  "schema_version": 1,
  "kind": "comic_name_board",
  "chapter": "第1话",
  "format": "页漫",
  "reading_direction": "从右到左",
  "manuscript": {
    "spec": "B5商漫",
    "trim_box": {"x": 0, "y": 0, "w": 1440, "h": 2036},
    "safe_area": {"x": 96, "y": 96, "w": 1248, "h": 1844},
    "bleed": 48,
    "inner_frame": {"x": 144, "y": 144, "w": 1152, "h": 1748}
  },
  "pages": [
    {
      "page_id": "PAGE_001",
      "page_side": "right",
      "spread_id": "SPREAD_001",
      "page_turn_hook": "P004 reveal",
      "eye_flow_path": ["P001", "P002", "P003", "P004"],
      "gutter_intent": "opening pause, then fast reaction cut",
      "panels": [
        {
          "panel_id": "P001",
          "thumbnail_rect": {"x": 96, "y": 96, "w": 1248, "h": 520},
          "layout_weight": "heavy",
          "panel_shape": "wide",
          "border_style": "standard",
          "camera_hint": "low angle opening hook",
          "bubble_first": "right_top",
          "effects_hint": "focus lines toward the artifact"
        }
      ]
    }
  ],
  "finishing_preview": {
    "render_stage": "完成稿",
    "ink_plan": "clear contour, solid blacks only for focal hierarchy",
    "tone_plan": "style-driven screentone or grayscale hierarchy",
    "effects_plan": "use action/focus/speed lines only where motion needs clarity"
  }
}
```

字段规则：

- `page_id`：页漫推荐 `PAGE_001`；条漫可用 `SCROLL_001`。
- `page_side`：页漫记录 `left` / `right`；条漫可写 `scroll`。
- `spread_id`：双页或翻页节奏用；条漫可每段一组。
- `page_turn_hook`：页末或滚动段末的钩子格，来自揭示、动作峰值、反转、悬念或强情绪停顿。
- `eye_flow_path`：本页/本段阅读顺序，必须覆盖页面内所有 panel。
- `thumbnail_rect`：缩略分镜坐标，不等于最终 layout 坐标，但应保留相对轻重、入口和停顿。
- `bubble_first`：优先放气泡的方向或区域，供 `comic-layout` 生成 `bubble_slots` 时继承。
- `effects_hint`：速度线、集中线、冲击线、漫符、背景省略等传统漫画效果的粗计划；最终细节进 `effects_plan`。

ネーム只做可执行草图，不做美术最终判断；审美和像素质量仍在后续出图、收尾和审查阶段确认。
