# name_board.json schema v2

`name_board.json` 是 `panel_script.json` 与 `layout.json` 之间的可签收编辑合同。v2 把页流、翻页承接、气泡语义、画面保留区、上游指纹和人工/授权制作代理审批放进同一份可复算结构；默认产物是 `draft`，不是完成态。

最小结构：

```json
{
  "schema_version": 2,
  "kind": "comic_name_board",
  "workflow_status": "draft",
  "chapter": "第1话",
  "format": "页漫",
  "reading_direction": "从右到左",
  "manuscript": {
    "spec": "B5商漫",
    "trim_box": {"x": 0, "y": 0, "w": 1440, "h": 2036},
    "safe_area": {"x": 96, "y": 96, "w": 1248, "h": 1844},
    "bleed": 48,
    "inner_frame": {"x": 144, "y": 144, "w": 1152, "h": 1748}
  },
  "pages": [
    {
      "page_id": "PAGE_001",
      "page_side": "right",
      "spread_id": "SPREAD_001",
      "page_turn_hook": "P004 reveal",
      "page_turn": {
        "setup": {"panel_id": "P004", "story_function": "reveal"},
        "payoff": {"panel_id": "P005", "mode": "next_page_open"}
      },
      "eye_flow_path": ["P001", "P002", "P003", "P004"],
      "eye_flow": {
        "reading_direction": "从右到左",
        "entry_panel_id": "P001",
        "exit_panel_id": "P004",
        "path": ["P001", "P002", "P003", "P004"]
      },
      "panels": [
        {
          "panel_id": "P001",
          "thumbnail_rect": {"x": 96, "y": 96, "w": 610, "h": 520},
          "layout_weight": "heavy",
          "panel_shape": "wide",
          "border_style": "standard",
          "gutter_intent": "opening pause",
          "bubble_first": "right_top",
          "balloons": [
            {
              "balloon_id": "P001_D1",
              "type": "dialogue",
              "content_ref": "panel:P001.dialogue:1",
              "speaker": "CHAR_01",
              "order": 1,
              "tail": {"mode": "toward_speaker", "target": "CHAR_01"}
            }
          ],
          "subject_regions": [
            {
              "region_id": "SUBJECT_PRIMARY",
              "role": "acting_subject_and_key_action",
              "rect": {"x": 218, "y": 200, "w": 366, "h": 364},
              "source": "heuristic_thumbnail",
              "confidence": "heuristic"
            }
          ],
          "avoid_regions": [
            {
              "region_id": "TEXT_01",
              "role": "reserved_for_balloon_or_sfx",
              "content_ref": "panel:P001.dialogue:1",
              "rect": {"x": 431, "y": 122, "w": 244, "h": 173},
              "source": "heuristic_thumbnail",
              "confidence": "heuristic"
            }
          ],
          "eye_flow_entry": "right_top",
          "eye_flow_exit": "left_bottom",
          "effects_hint": "focus lines toward the artifact"
        }
      ]
    }
  ],
  "upstream_receipt": {
    "panel_script": "脚本/第1话/panel_script.json",
    "panel_script_sha256": "<sha256>",
    "settings": "_设置.md",
    "settings_sha256": "<sha256>"
  },
  "validation": {"status": "pass", "errors": []},
  "approval": {}
}
```

状态与审批：

- `workflow_status` 只允许 `draft → review → approved`。重建 board 会回到 `draft` 并清空旧审批。
- `approval.subject_sha256` 绑定除工作流状态、校验回显和审批对象外的完整创作合同；同时记录签收时的 panel script/settings SHA。
- 上游文件变化、board 内容变化或审批 SHA 不匹配时，`--check` 失败；不能沿用旧签收。
- `draft/review` 只能在 `_进度.md` 写 `🟡待签收`；仅 `approved + validation=pass + current upstream` 可写 `✅`。

结构规则：

- `page_hint` 要么每格都有，要么每格都没有；显式页号必须为正整数且按 panel 阅读顺序单调不减。
- `page_turn.setup` 必须是本页最后一格，`payoff` 是下一页首格；最后一页用 `mode=chapter_end`。
- `eye_flow_path`、`eye_flow.path` 与 `pages[].panels` 必须完全同序，并且全书覆盖每个 panel 一次。
- `thumbnail_rect` 必须为正尺寸且位于 `manuscript.safe_area` 内。它是正式 layout 的几何输入，不只是备注。
- `balloons` 为每段旁白、每句对白和每个 SFX 建一个稳定 `content_ref`，并记录 speaker、顺序和尾巴目标；缺 speaker 时显式写 `unresolved_speaker`，不偷偷猜人物。
- `subject_regions` / `avoid_regions` 是低保真构图辅助。自动生成项必须标 `confidence=heuristic`，不能单凭这些区域做审美硬阻断。
- `page_side`、`spread_id`、`gutter_intent`、`effects_hint` 都由 layout adapter 消费；不能只写入却在下游丢弃。
