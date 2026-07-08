# lettering.json schema

最小结构：

```json
{
  "schema_version": 1,
  "kind": "comic_lettering",
  "chapter": "第1话",
  "language_mode": "中文",
  "items": [
    {
      "item_id": "L001",
      "panel_id": "P001",
      "type": "dialogue",
      "speaker": "主角",
      "text": "台词",
      "text_zh": "台词",
      "text_en": "Dialogue.",
      "text_source": "可选：原文或文言摘录",
      "lang": "zh-Hans",
      "dir": "ltr",
      "script": "Hans",
      "line_break": "cjk",
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

- `language_mode` 记录生成草案时的项目 `文字语言`，导出时仍以 `_设置.md` 的当前值为准。
- `text` 保持向后兼容，默认等于中文正文。
- `text_zh` 是中文正文；`text_en` 是英文译文或英文目标嵌字；`text_custom` 可用于 `自定义语言(...)`；`text_source` 可保留外语/文言原文。`文字语言=中文` 时只渲中文；`英文` 只渲英文；`中上英下` / `英上中下` 按指定顺序渲染双语。
- `lang` / `dir` / `script` / `line_break` 是每条最终嵌字文本的语言、方向和断行元数据。RTL 或 `line_break=dictionary_required` 的文字不得用当前 Pillow 草稿 renderer 静默渲染，必须换专业排版 renderer 或人工嵌字。
- 空字符串不应生成最终气泡；导出脚本会跳过无文字 item 和未使用的 `bubble_slots`。
- `dialogue` / `narration` 的最终容器由 `comic-compose` 绘制；不要在图像阶段烘焙空白气泡，也不要在不规则气泡内部再加矩形文字框。

正式发布前必须确认字体授权。MVP 可先用系统字体做草稿，但应在 manifest 或审查报告里标明 `font_status`。
