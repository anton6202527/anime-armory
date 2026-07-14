# layout.json schema v2

`layout.json` 是已签收ネーム的像素几何实现。默认状态为 `draft`；只有结构 validator 通过、上游 SHA 当前且人工签收后才成为页面排版完成态。

```json
{
  "schema_version": 2,
  "kind": "comic_layout",
  "workflow_status": "draft",
  "chapter": "第1话",
  "format": "页漫",
  "reading_direction": "从右到左",
  "geometry_profile": "paged_grid_rtl",
  "format_supported_by_script": true,
  "manuscript": {
    "spec": "B5商漫",
    "trim_box": {"x": 0, "y": 0, "w": 1440, "h": 2036},
    "safe_area": {"x": 96, "y": 96, "w": 1248, "h": 1844},
    "bleed": 48,
    "inner_frame": {"x": 144, "y": 144, "w": 1152, "h": 1748}
  },
  "name_board": "排版/第1话/name_board.json",
  "canvas": {"width": 1440, "height": 2036},
  "segments": [
    {
      "segment_id": "PAGE_001",
      "page_side": "right",
      "spread_id": "SPREAD_001",
      "width": 1440,
      "height": 2036,
      "reading_order": ["P001", "P002"],
      "panels": [
        {
          "panel_id": "P001",
          "x": 734,
          "y": 96,
          "w": 610,
          "h": 900,
          "layout_weight": "heavy",
          "gutter_intent": "opening pause",
          "name_page_id": "PAGE_001",
          "page_turn": {
            "setup": {"panel_id": "P002"},
            "payoff": {"panel_id": "P003", "mode": "next_page_open"}
          },
          "subject_regions": [],
          "avoid_regions": [],
          "bubble_slots": [
            {
              "slot_id": "B001D1",
              "type": "dialogue",
              "content_ref": "panel:P001.dialogue:1",
              "speaker": "CHAR_01",
              "order": 1,
              "tail": {"mode": "toward_speaker", "target": "CHAR_01"},
              "x": 900,
              "y": 140,
              "w": 360,
              "h": 136
            }
          ]
        }
      ]
    }
  ],
  "upstream_receipt": {
    "panel_script_sha256": "<sha256>",
    "name_board_sha256": "<sha256>",
    "name_approval_subject_sha256": "<sha256>",
    "settings_sha256": "<sha256>",
    "legacy_name_waiver": false
  },
  "validation": {"status": "pass", "errors": []},
  "approval": {}
}
```

支持的 adapter：

- `longstrip_single_column`：按 name page/scroll grouping 排列；`thumbnail_rect` 的相对宽度和水平位置会映射到长条画布，`gutter_intent` 会转成实际 `gutter_after`。若设置最大分段高度，只在 panel 边界拆分。
- `paged_grid_ltr` / `paged_grid_rtl`：一个 segment 对应一页，直接把缩略分镜矩形映射进原稿安全框；panel 数组保持阅读顺序，不能用坐标排序代替 RTL 顺序。
- `yonkoma_four_rows`：一个 segment 对应一页，每页必须恰好四格，按四个纵向行格输出。

确定性 validator：

- `panel_id` 在脚本、name 和 layout 中必须唯一、完全覆盖且同序。
- `segments[].reading_order` 必须与对应 `panels` 数组一致。
- panel 矩形必须为正、位于 segment 内，同一 segment 不得相互重叠。
- 每段 narration、每句 dialogue 和每个 SFX 必须恰好得到同类型 bubble slot；slot 必须位于所属 panel 内并继承 `content_ref/speaker/order/tail`。
- `geometry_profile` 必须与项目漫画形态匹配。
- validator 只验证可复算结构事实；构图好坏、视觉重心和气泡是否美观仍由人工签收。

审批与失效：

- `workflow_status` 按 `draft → review → approved` 推进。
- `approval.subject_sha256` 绑定布局内容，receipt 同时记录 panel script、name board、settings SHA。
- 修改脚本、已签收 name、设置或 layout 内容后，旧 approval 立即失效；`--check` 必须失败并要求从相应阶段重建。
- `--allow-legacy-name` 只为旧项目迁移，并在 upstream receipt 留痕；正式生产入口不默认传入。
