# panel_jobs.json schema

最小结构：

```json
{
  "schema_version": 1,
  "kind": "comic_panel_jobs",
  "chapter": "第1话",
  "model": "自定义",
  "channel": "manual",
  "jobs": [
    {
      "panel_id": "P001",
      "status": "planned",
      "size": {"width": 1440, "height": 900},
      "prompt": "无字漫画画面描述",
      "negative_prompt": "不要文字、不要水印、不要多余手指",
      "references": [
        {"id": "CHAR_MAIN", "path": "出图/共享/图片/CHAR_MAIN_front.png"}
      ],
      "result_path": "",
      "source": "manual"
    }
  ]
}
```

状态建议：

- `planned`：任务已写，未执行。
- `submitted`：已交给某个后端或人工流程。
- `ready`：图片已落到 `result_path`。
- `rework`：需要重出。

正文台词不要写进 prompt。台词只作为气泡预留和表演语气参考。
