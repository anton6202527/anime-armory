# finishing_plan.json schema v2

`finishing_plan.json` 是已签收 layout 的可执行原稿收尾合同。它供出图阶段消费传统稿层，也供嵌字和审查核对 SFX、价值与文本分层。缺输入、覆盖不全或上游过期时不得生成空计划。

```json
{
  "schema_version": 2,
  "kind": "comic_finishing_plan",
  "workflow_status": "validated",
  "chapter": "第1话",
  "render_stage": "网点完成稿",
  "style": "黑白日漫页漫",
  "delivery_mode": "monochrome_print",
  "layer_contract": {
    "delivery_mode": "monochrome_print",
    "ordered_layers": [
      {"layer_id": "LINEART", "role": "lineart", "required": true, "blend": "normal"},
      {"layer_id": "INK_BLACKS", "role": "ink_blacks", "required": true, "blend": "normal"},
      {"layer_id": "TONE", "role": "tone", "required": true, "blend": "normal"},
      {"layer_id": "EFFECTS", "role": "effects", "required": true, "blend": "normal"}
    ],
    "text_separation": "dialogue/narration stay in post-lettering layers; only contracted drawn SFX may enter art layers",
    "flatten_policy": "keep logical layer manifest even when a backend returns one flattened raster"
  },
  "page_value_plans": [
    {
      "page_or_segment_id": "PAGE_001",
      "panel_ids": ["P001", "P002"],
      "focal_panel_ids": ["P001"],
      "value_rhythm": "alternate focal contrast and recovery beats; preserve a readable three-value hierarchy",
      "check": "thumbnail test at page/segment scale before export"
    }
  ],
  "panels": [
    {
      "panel_id": "P001",
      "layout_weight": "heavy",
      "art_stage_sequence": ["rough", "pencil", "lineart", "ink_blacks", "tone", "effects"],
      "layer_items": [
        {
          "item_id": "P001_LINEART",
          "layer": "lineart",
          "role": "art",
          "mask_scope": "panel",
          "no_bake_dialogue_or_narration": true
        }
      ],
      "ink_plan": "clean contour and expressive line weight",
      "black_fill_plan": "solid blacks frame the reveal without hiding identity",
      "tone_plan": "separate skin, cloth and background depth",
      "tone_items": [
        {
          "item_id": "P001_TONE_01",
          "role": "material_and_depth",
          "strategy": "explicit screentone plan",
          "scope": "subject/background separation"
        }
      ],
      "value_plan": "three-value read",
      "effects_plan": "focus lines toward the reveal object",
      "lettering_sfx_plan": {
        "mode": "drawn_sfx",
        "integration": "follow action path without covering identity or text slots",
        "shape": "jagged impact"
      },
      "sfx_items": [
        {
          "item_id": "P001_SFX_01",
          "content_ref": "panel:P001.sfx:1",
          "text_hint": "砰",
          "delivery": "drawn_sfx",
          "layer": "lettering_sfx"
        }
      ],
      "no_bake_text_contract": "dialogue and narration stay out of raw images"
    }
  ],
  "upstream_receipt": {
    "panel_script_sha256": "<sha256>",
    "name_board_sha256": "<sha256>",
    "layout_sha256": "<sha256>",
    "settings_sha256": "<sha256>",
    "name_approval_subject_sha256": "<sha256>",
    "layout_approval_subject_sha256": "<sha256>"
  },
  "validation": {"status": "pass", "errors": []}
}
```

规则：

- `delivery_mode` 优先读项目显式设置；否则按风格和稿层归一为 `monochrome_print`、`grayscale_digital` 或 `color_digital`。
- `layer_contract` 是项目级有序图层合同；即使后端只返回扁平图，也必须保留逻辑图层清单和文字分离约束。
- `page_value_plans` 必须逐一覆盖 layout 的所有 page/segment，记录焦点格与整页缩略价值检查。
- `panels` 必须唯一并按原顺序完整覆盖 panel script、name 和 layout。
- 每格必须同时具备稿层、墨线、黑场、tone、value、effects、SFX 和禁止烘焙正文合同；没有 SFX 时 `sfx_items=[]` 是合法显式值。
- 每个 SFX item 绑定稳定 `content_ref`；对白和旁白不得进入 art layer。
- `upstream_receipt` 绑定全部三份上游合同和设置；任一 SHA 变化后 `--check` 返回失败，必须重建计划。
- `workflow_status=validated` 只表示确定性结构与新鲜度通过，不替代对墨线、网点、效果和整页价值的人工审美判断。
