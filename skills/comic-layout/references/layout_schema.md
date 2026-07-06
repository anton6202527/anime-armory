# layout.json schema

最小结构：

```json
{
  "schema_version": 1,
  "kind": "comic_layout",
  "chapter": "第1话",
  "format": "条漫",
  "reading_direction": "从上到下",
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
