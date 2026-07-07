# panel_script.json schema

最小结构：

```json
{
  "schema_version": 1,
  "kind": "comic_panel_script",
  "title": "作品名",
  "chapter": "第1话",
  "status": "draft",
  "panels": [
    {
      "panel_id": "P001",
      "story_function": "opening_hook",
      "description": "首格画面描述",
      "characters": ["主角"],
      "location": "场景名",
      "dialogue": [
        {"speaker": "主角", "text": "台词", "tone": "紧张"}
      ],
      "narration": "旁白",
      "sfx": ["轰"],
      "art_notes": "景别、构图、表情、动作、禁漂移项",
      "references": ["CHAR_MAIN", "LOC_001"]
    }
  ]
}
```

字段规则：

- `panel_id`：同一话唯一，推荐 `P001`。
- `story_function`：该格的戏剧功能，如 `opening_hook`、`reaction`、`reveal`、`action_peak`、`turning_point`、`cliffhanger`。
- `description`：画面事实，不写空泛风格词。
- `dialogue`：只存文字，不要求画进图里。
- `art_notes`：给排版和出图用，包含景别、构图、表情、动作、需要参考的资产。
- `references`：角色、场景、道具、服装、特效等引用 ID；MVP 可先留自然语言，正式出图前再规范。
- `layout_weight` / `visual_weight` / `importance`（可选）：`heavy` / `medium` / `compact` 或 1-3，用于让 `comic-layout` 以数据驱动方式决定大格/中格/小格，避免把具体项目 story_function 写进通用脚本。
- `style_bucket` / `scene_family` / `visual_context`（可选）：同一场景/光色族群标识，供 `comic-review` 的风格一致性按计划内场景分组，避免把夜景、梦境、蒙太奇、系统光效等合理差异误判成画风漂移。
