# panel_jobs.json schema

最小结构：

```json
{
  "schema_version": 1,
  "kind": "comic_panel_jobs",
  "chapter": "第1话",
  "model": "自定义",
  "channel": "manual",
  "backend_capabilities": {
    "adapter_id": "manual_or_unknown",
    "reference_image_limit": 6,
    "supports_image_inputs": true,
    "persistent_subject": false
  },
  "text_language": "中文",
  "jobs": [
    {
      "panel_id": "P001",
      "status": "planned",
      "size": {"width": 1440, "height": 900},
      "prompt": "无字漫画画面描述",
      "negative_prompt": "不要文字、不要水印、不要多余手指",
      "reference_budget": {
        "adapter_id": "manual_or_unknown",
        "reference_image_limit": 6
      },
      "references": [
        {"id": "CHAR_MAIN", "path": "出图/共享/图片/CHAR_MAIN_front.png"}
      ],
      "result_path": "",
      "source": "manual",
      "reference_input_mode": "codex_exec_image_flags",
      "reference_input_count": 1,
      "reference_manifest": "生产数据/codex_reference_bundles/第1话/P001.json"
    }
  ]
}
```

状态建议：

- `planned`：任务已写，未执行。
- `submitted`：已交给某个后端或人工流程。
- `ready`：图片已落到 `result_path`。
- `qc_block`：图片已落盘但 `post_qc.verdict=block`，不算 ready，不能进入合成。
- `rework`：需要重出。

正文台词不要写进 prompt。`text_language` 只记录后期嵌字/导出的文字语言；台词只作为气泡预留和表演语气参考。

注意：`references[].path` 表示 job 已绑定共享参考图；`reference_input_count` 和 `reference_manifest` 表示生成时已经把这些参考图真实传给后端。已有面板如果只有 path、没有 manifest 或 `reference_input_count=0`，应由 `comic-identity` 标入重抽计划。

`backend_capabilities` / `reference_budget` 来自 comic 自己的 `image_backend_adapter`，用于记录当前模型+渠道的参考图预算、是否支持真实图片输入、是否具备持久主体能力。它是 job 生成时的执行约束，不代表本机一定已安装对应 runner。
