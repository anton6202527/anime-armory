# lettering.json schema

最小结构：

```json
{
  "schema_version": 1,
  "kind": "comic_lettering",
  "chapter": "第1话",
  "items": [
    {
      "item_id": "L001",
      "panel_id": "P001",
      "type": "dialogue",
      "speaker": "主角",
      "text": "台词",
      "slot_id": "B001",
      "style": {
        "font": "project_default",
        "size": 44,
        "direction": "horizontal",
        "bubble": "round"
      }
    }
  ]
}
```

类型建议：

- `dialogue`：对白气泡。
- `narration`：旁白框。
- `sfx`：拟声词。
- `system`：系统面板或界面文字。

正式发布前必须确认字体授权。MVP 可先用系统字体做草稿，但应在 manifest 或审查报告里标明 `font_status`。
