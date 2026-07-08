# layout.json schema

最小结构：

```json
{
  "schema_version": 1,
  "kind": "comic_layout",
  "chapter": "第1话",
  "format": "条漫",
  "reading_direction": "从上到下",
  "manuscript": {
    "spec": "数字条漫",
    "trim_box": {"x": 0, "y": 0, "w": 1440, "h": "auto"},
    "safe_area": {"x": 72, "y": 72, "w": 1296, "h": 1656},
    "bleed": 0,
    "inner_frame": {"x": 72, "y": 72, "w": 1296, "h": 1656}
  },
  "name_board": "排版/第1话/name_board.json",
  "canvas": {"width": 1440, "height": "auto"},
  "segments": [
    {
      "segment_id": "S001",
      "width": 1440,
      "height": 2400,
      "panels": [
        {
          "panel_id": "P001",
          "x": 0,
          "y": 0,
          "w": 1440,
          "h": 900,
          "layout_weight": "heavy",
          "panel_shape": "wide",
          "border_style": "standard",
          "gutter_intent": "opening pause",
          "bubble_first": "right_top",
          "effects_hint": "focus lines toward artifact",
          "name_page_id": "PAGE_001",
          "page_side": "right",
          "spread_id": "SPREAD_001",
          "page_turn_hook": "P004 reveal",
          "bubble_slots": [
            {"slot_id": "B001", "type": "dialogue", "x": 920, "y": 80, "w": 360, "h": 180}
          ]
        }
      ]
    }
  ]
}
```

规则：

- `panel_id` 必须能在 `panel_script.json` 找到。
- 坐标单位为像素，原点在 segment 左上角。
- `bubble_slots` 是占位，不是最终文字；最终文字进入 `lettering.json`。
- 条漫默认可用单个 `segment` 表示整话长图；目标平台需要限高时，可用多个 `segments` 对应长图分段。
- 页漫可把 `segment_id` 当页号，如 `PAGE_001`。
- `manuscript` 记录传统原稿规格、裁切框、安全区、出血和内框；来自 `comic-name` 时应原样继承。页漫/投稿规格缺 `safe_area` 会在 gate/review 中提示。
- `name_board` 记录当前 layout 消费的缩略分镜路径；没有则为空字符串。
- `layout_weight` / `panel_shape` / `border_style` / `gutter_intent` / `bubble_first` / `effects_hint` 是从 `name_board.json` 或 `panel_script.json` 继承的传统排版提示。
- `page_side` / `spread_id` / `page_turn_hook` 帮助页漫审查翻页节奏；条漫可写 `scroll` 或留空。
