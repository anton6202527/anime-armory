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
      "text_zh": "台词",
      "text_en": "Dialogue.",
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

字段约定：

- `text` 保持向后兼容，默认等于中文正文。
- `text_zh` 是中文正文；`text_en` 是英文译文。中英双版导出时两者都应存在，英文由导出脚本自动使用较小字号并按词换行。
- 空字符串不应生成最终气泡；导出脚本会跳过无文字 item 和未使用的 `bubble_slots`。
- `dialogue` / `narration` 的最终容器由 `comic-compose` 绘制；不要在图像阶段烘焙空白气泡，也不要在不规则气泡内部再加矩形文字框。

正式发布前必须确认字体授权。MVP 可先用系统字体做草稿，但应在 manifest 或审查报告里标明 `font_status`。
