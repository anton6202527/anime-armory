#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path
import json

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_layout
from editorial_authorization import AUTHORIZATION_RELATIVE_PATH, authorization_payload_sha256


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_approved_name(
    root: Path,
    chapter: str,
    panels: list[dict],
    *,
    comic_format: str = "页漫",
    reading_direction: str = "从右到左",
    page_groups: list[list[str]] | None = None,
) -> dict:
    panel_ids = [str(panel["panel_id"]) for panel in panels]
    page_groups = page_groups or [panel_ids]
    width, height = 1440, 2036
    safe = {"x": 96, "y": 96, "w": 1248, "h": 1844}
    pages = []
    panel_lookup = {str(panel["panel_id"]): panel for panel in panels}
    for page_index, ids in enumerate(page_groups, 1):
        page_panels = []
        for panel_index, pid in enumerate(ids):
            panel = panel_lookup[pid]
            if "页漫" in comic_format and len(ids) > 1:
                columns = 2
                rows = (len(ids) + columns - 1) // columns
                cell_w = (safe["w"] - 28) // columns
                row_h = (safe["h"] - 28 * max(0, rows - 1)) // rows
                row, reading_col = divmod(panel_index, columns)
                visual_col = columns - 1 - reading_col if reading_direction == "从右到左" else reading_col
                thumbnail = {
                    "x": safe["x"] + visual_col * (cell_w + 28),
                    "y": safe["y"] + row * (row_h + 28),
                    "w": cell_w,
                    "h": row_h,
                }
            else:
                row_h = (safe["h"] - 28 * max(0, len(ids) - 1)) // max(1, len(ids))
                thumbnail = {"x": safe["x"], "y": safe["y"] + panel_index * (row_h + 28), "w": safe["w"], "h": row_h}
            balloons = []
            for dialogue_index, dialogue in enumerate(panel.get("dialogue") or [], 1):
                balloons.append(
                    {
                        "type": "dialogue",
                        "content_ref": f"panel:{pid}.dialogue:{dialogue_index}",
                        "speaker": dialogue.get("speaker", ""),
                        "order": dialogue_index,
                        "tail": {"mode": "toward_speaker", "target": dialogue.get("speaker", "")},
                    }
                )
            page_panels.append(
                {
                    "panel_id": pid,
                    "thumbnail_rect": thumbnail,
                    "layout_weight": "heavy" if panel_index == 0 else "medium",
                    "panel_shape": "wide",
                    "border_style": "standard",
                    "bubble_first": "right_top" if reading_direction == "从右到左" else "left_top",
                    "balloons": balloons,
                    "subject_regions": [],
                    "avoid_regions": [],
                }
            )
        pages.append(
            {
                "page_id": f"PAGE_{page_index:03d}" if "条漫" not in comic_format else f"SCROLL_{page_index:03d}",
                "page_side": "right" if reading_direction == "从右到左" else "left",
                "spread_id": f"SPREAD_{(page_index + 1) // 2:03d}",
                "page_turn_hook": f"{ids[-1]} beat",
                "eye_flow_path": ids,
                "eye_flow": {"path": ids},
                "panels": page_panels,
            }
        )
    board = {
        "schema_version": 2,
        "kind": "comic_name_board",
        "workflow_status": "approved",
        "chapter": chapter,
        "format": comic_format,
        "reading_direction": reading_direction,
        "manuscript": {
            "spec": "B5商漫",
            "trim_box": {"x": 0, "y": 0, "w": width, "h": height},
            "safe_area": safe,
            "bleed": 48,
            "inner_frame": {"x": 144, "y": 144, "w": 1152, "h": 1748},
        },
        "pages": pages,
        "upstream_receipt": {
            "panel_script_sha256": build_layout.sha256_file(root / "脚本" / chapter / "panel_script.json"),
            "settings_sha256": build_layout.sha256_file(root / "_设置.md"),
        },
        "approval": {},
    }
    board["approval"] = {
        "status": "approved",
        "reviewed_by": "name-editor",
        "reviewed_at": "2026-07-14T00:00:00+00:00",
        "subject_sha256": build_layout.approval_subject_sha256(board),
    }
    write_json(root / "排版" / chapter / "name_board.json", board)
    return board


def test_dialogue_slot_height_uses_text_target_length() -> None:
    short_panel = {
        "panel_id": "P001",
        "story_function": "reaction",
        "dialogue": [{"text": "短句"}],
    }
    long_panel = {
        "panel_id": "P002",
        "story_function": "reaction",
        "dialogue": [
            {
                "text": "短句",
                "text_target": "This translated line is deliberately much longer than the source and should need more than two bubble lines.",
            }
        ],
    }

    short_slot = build_layout.bubble_slots(short_panel, {"x": 0, "y": 0, "w": 1440, "h": 700}, 1)[0]
    long_slot = build_layout.bubble_slots(long_panel, {"x": 0, "y": 0, "w": 1440, "h": 900}, 2)[0]

    assert long_slot["h"] > short_slot["h"]
    assert build_layout.panel_height(long_panel) > build_layout.panel_height(short_panel)


def test_panel_metadata_maps_normalized_speaker_anchor_to_final_geometry() -> None:
    item = build_layout.panel_metadata(
        {"panel_id": "P001", "dialogue": [{"speaker": "CHAR_A", "text": "走。"}]},
        {"page_id": "PAGE_001", "spread_id": "SPREAD_001", "spread_mode": "paired_pages", "cross_page_art": False},
        {
            "panel_id": "P001",
            "thumbnail_rect": {"x": 100, "y": 100, "w": 600, "h": 800},
            "balloons": [{
                "type": "dialogue", "content_ref": "panel:P001.dialogue:1", "speaker": "CHAR_A", "order": 1,
                "tail": {"mode": "toward_speaker", "target": "CHAR_A"},
            }],
            "speaker_anchors": {"CHAR_A": {"bbox": {"x": 0.6, "y": 0.4, "w": 0.2, "h": 0.4}}},
        },
        {"x": 20, "y": 40, "w": 300, "h": 400},
        1,
    )

    assert item["speaker_anchors"]["CHAR_A"]["bbox"] == {"x": 200, "y": 200, "w": 60, "h": 160}
    assert item["spread_mode"] == "paired_pages"
    assert item["cross_page_art"] is False


def test_build_layout_inherits_name_board_manuscript_and_panel_metadata(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text("- 漫画形态：页漫\n- 阅读方向：从右到左\n- 页面尺寸：1440xauto\n- 原稿规格：B5商漫\n", encoding="utf-8")
    write_json(
        root / "脚本" / chapter / "panel_script.json",
        {
            "panels": [
                {
                    "panel_id": "P001",
                    "story_function": "opening_hook",
                    "description": "主角推门。",
                    "dialogue": [{"text": "来了。"}],
                }
            ]
        },
    )
    write_approved_name(
        root,
        chapter,
        [
            {
                "panel_id": "P001",
                "story_function": "opening_hook",
                "description": "主角推门。",
                "dialogue": [{"text": "来了。"}],
            }
        ],
    )

    layout = build_layout.build_layout(root, chapter, 0, 28)
    panel = layout["segments"][0]["panels"][0]

    assert layout["manuscript"]["spec"] == "B5商漫"
    assert layout["schema_version"] == 2
    assert layout["workflow_status"] == "draft"
    assert layout["validation"]["status"] == "pass"
    assert layout["geometry_profile"] == "paged_grid_rtl"
    assert layout["format_supported_by_script"] is True
    assert layout["name_board"] == "排版/第1话/name_board.json"
    assert panel["layout_weight"] == "heavy"
    assert panel["page_side"] == "right"
    assert panel["bubble_first"] == "right_top"
    assert panel["bubble_slots"][0]["x"] > 700
    assert panel["bubble_slots"][0]["content_ref"] == "panel:P001.dialogue:1"


def test_unapproved_name_is_blocked_without_explicit_legacy_flag(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text("- 漫画形态：条漫\n- 阅读方向：从上到下\n", encoding="utf-8")
    write_json(root / "脚本" / chapter / "panel_script.json", {"panels": [{"panel_id": "P001"}]})
    write_json(
        root / "排版" / chapter / "name_board.json",
        {
            "schema_version": 1,
            "manuscript": {"trim_box": {"w": 1440, "h": 1800}, "safe_area": {"x": 72, "y": 72, "w": 1296, "h": 1656}},
            "pages": [{"page_id": "SCROLL_001", "panels": [{"panel_id": "P001", "thumbnail_rect": {"x": 72, "y": 72, "w": 1296, "h": 1656}}]}],
        },
    )

    try:
        build_layout.build_layout(root, chapter, 0, 28)
        assert False, "unapproved legacy name should block"
    except build_layout.LayoutError:
        pass

    migrated = build_layout.build_layout(root, chapter, 0, 28, allow_legacy_name=True)
    assert migrated["upstream_receipt"]["legacy_name_waiver"] is True


def test_page_grid_rtl_has_unique_non_overlapping_bounded_panels(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text("- 漫画形态：页漫\n- 阅读方向：从右到左\n- 页面尺寸：1440xauto\n", encoding="utf-8")
    panels = [
        {"panel_id": f"P{index:03d}", "story_function": "beat", "dialogue": [{"speaker": "甲", "text": f"台词{index}"}]}
        for index in range(1, 5)
    ]
    write_json(root / "脚本" / chapter / "panel_script.json", {"panels": panels})
    write_approved_name(root, chapter, panels)

    layout = build_layout.build_layout(root, chapter, 0, 28)

    assert layout["geometry_profile"] == "paged_grid_rtl"
    assert build_layout.validate_layout(layout, {"panels": panels}, json.loads((root / "排版" / chapter / "name_board.json").read_text(encoding="utf-8"))) == []


def test_yonkoma_adapter_requires_and_builds_four_rows(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text("- 漫画形态：四格\n- 阅读方向：从上到下\n- 页面尺寸：1440xauto\n", encoding="utf-8")
    panels = [{"panel_id": f"P{index:03d}", "story_function": "beat"} for index in range(1, 5)]
    write_json(root / "脚本" / chapter / "panel_script.json", {"panels": panels})
    write_approved_name(root, chapter, panels, comic_format="四格", reading_direction="从上到下")

    layout = build_layout.build_layout(root, chapter, 0, 28)

    assert layout["geometry_profile"] == "yonkoma_four_rows"
    ys = [panel["y"] for panel in layout["segments"][0]["panels"]]
    assert ys == sorted(ys)
    assert len(set(ys)) == 4


def test_layout_approval_is_bound_to_current_upstream(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    settings = root / "_设置.md"
    settings.write_text("- 漫画形态：条漫\n- 阅读方向：从上到下\n", encoding="utf-8")
    panels = [{"panel_id": "P001", "dialogue": [{"speaker": "甲", "text": "走。"}]}]
    write_json(root / "脚本" / chapter / "panel_script.json", {"panels": panels})
    write_approved_name(root, chapter, panels, comic_format="条漫", reading_direction="从上到下")
    path = root / "排版" / chapter / "layout.json"
    write_json(path, build_layout.build_layout(root, chapter, 0, 28))

    build_layout.transition_existing(root, chapter, "review")
    approved = build_layout.transition_existing(root, chapter, "approved", reviewed_by="layout-editor")
    assert build_layout.verify_layout_approval(approved) == []

    settings.write_text("- 漫画形态：条漫\n- 阅读方向：从上到下\n- 页面尺寸：1280xauto\n", encoding="utf-8")
    name = json.loads((root / "排版" / chapter / "name_board.json").read_text(encoding="utf-8"))
    assert build_layout.verify_layout_upstream(root, chapter, approved, name)


def test_name_and_layout_approvals_require_reviewer_and_time(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text("- 漫画形态：条漫\n- 阅读方向：从上到下\n", encoding="utf-8")
    panels = [{"panel_id": "P001"}]
    write_json(root / "脚本" / chapter / "panel_script.json", {"panels": panels})
    name = write_approved_name(root, chapter, panels, comic_format="条漫", reading_direction="从上到下")

    missing_name_reviewer = json.loads(json.dumps(name, ensure_ascii=False))
    missing_name_reviewer["approval"].pop("reviewed_by")
    assert any(
        "reviewed_by" in error
        for error in build_layout.verify_name_board(root, chapter, missing_name_reviewer)
    )

    layout_path = root / "排版" / chapter / "layout.json"
    write_json(layout_path, build_layout.build_layout(root, chapter, 0, 28))
    build_layout.transition_existing(root, chapter, "review")
    approved = build_layout.transition_existing(root, chapter, "approved", reviewed_by="layout-editor")
    subject_sha = build_layout.approval_subject_sha256(approved)
    for field in ("reviewed_by", "reviewed_at"):
        malformed = json.loads(json.dumps(approved, ensure_ascii=False))
        malformed["approval"].pop(field)
        assert build_layout.approval_subject_sha256(malformed) == subject_sha
        assert any(field in error for error in build_layout.verify_layout_approval(malformed))


def test_delegated_layout_approval_requires_explicit_current_authorization(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    settings = root / "_设置.md"
    base_settings = "- 漫画形态：条漫\n- 阅读方向：从上到下\n"
    settings.write_text(base_settings, encoding="utf-8")
    panels = [{"panel_id": "P001"}]
    write_json(root / "脚本" / chapter / "panel_script.json", {"panels": panels})
    write_approved_name(root, chapter, panels, comic_format="条漫", reading_direction="从上到下")
    write_json(root / "排版" / chapter / "layout.json", build_layout.build_layout(root, chapter, 0, 28))
    build_layout.transition_existing(root, chapter, "review")

    with pytest.raises(build_layout.LayoutError, match="未显式设置"):
        build_layout.transition_existing(
            root,
            chapter,
            "approved",
            reviewed_by="delegate:comic-production-agent",
        )

    envelope_path = root / AUTHORIZATION_RELATIVE_PATH
    envelope_path.parent.mkdir(parents=True)
    envelope = {
        "schema": "comic-editorial-authorization/v1",
        "status": "authorized",
        "authorized_by": "project-owner@example.test",
        "source_quote": "允许制作代理审阅当前 layout",
        "scope": ["layout"],
        "delegate": "comic-production-agent",
        "issued_at": "2026-08-21T00:00:00+00:00",
        "expires_at": "2099-01-01T00:00:00+00:00",
    }
    envelope["authorization_sha256"] = authorization_payload_sha256(envelope)
    envelope_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    approved = build_layout.transition_existing(
        root,
        chapter,
        "approved",
        reviewed_by="delegate:comic-production-agent",
    )
    assert approved["approval"]["authorization"]["source"] == "authorization_envelope"
    assert approved["approval"]["review_kind"] == "delegated_policy_auto_review"
    assert build_layout.verify_layout_approval(approved, root) == []

    envelope["scope"] = ["name_board"]
    envelope_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert any(
        "授权" in item or "authorization" in item
        for item in build_layout.verify_layout_approval(approved, root)
    )


def test_layout_cli_only_marks_complete_after_validation_and_approval(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text("- 漫画形态：条漫\n- 阅读方向：从上到下\n", encoding="utf-8")
    (root / "_进度.md").write_text("| 话 | 页面排版 |\n|---|---|\n| 第1话 | ⬜ |\n", encoding="utf-8")
    panels = [{"panel_id": "P001", "dialogue": [{"speaker": "甲", "text": "走。"}]}]
    write_json(root / "脚本" / chapter / "panel_script.json", {"panels": panels})
    write_approved_name(root, chapter, panels, comic_format="条漫", reading_direction="从上到下")

    monkeypatch.setattr(sys, "argv", ["comic-layout", str(root), "--chapter", chapter])
    assert build_layout.main() == 0
    assert "🟡待签收" in (root / "_进度.md").read_text(encoding="utf-8")
    assert "✅" not in (root / "_进度.md").read_text(encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["comic-layout", str(root), "--chapter", chapter, "--submit-review"])
    assert build_layout.main() == 0
    monkeypatch.setattr(
        sys,
        "argv",
        ["comic-layout", str(root), "--chapter", chapter, "--approve", "--reviewed-by", "layout-editor"],
    )
    assert build_layout.main() == 0
    assert "✅" in (root / "_进度.md").read_text(encoding="utf-8")


def test_layout_geometry_hash_ignores_generation_settings(tmp_path: Path) -> None:
    root = tmp_path
    (root / "_设置.md").write_text(
        "- 漫画形态：条漫\n- 阅读方向：从上到下\n- 页面尺寸：1440xauto\n- 原稿规格：数字条漫\n"
        "- 单话分段高度：0\n- 生图模型：A\n", encoding="utf-8")
    before = build_layout.settings_geometry_sha256(root)
    # generation-only edit → geometry hash unchanged
    (root / "_设置.md").write_text(
        "- 漫画形态：条漫\n- 阅读方向：从上到下\n- 页面尺寸：1440xauto\n- 原稿规格：数字条漫\n"
        "- 单话分段高度：0\n- 生图模型：B\n", encoding="utf-8")
    assert build_layout.settings_geometry_sha256(root) == before
    # geometry edit → hash changes
    (root / "_设置.md").write_text(
        "- 漫画形态：页漫\n- 阅读方向：从上到下\n- 页面尺寸：1440xauto\n- 原稿规格：数字条漫\n"
        "- 单话分段高度：0\n- 生图模型：B\n", encoding="utf-8")
    assert build_layout.settings_geometry_sha256(root) != before


def test_layout_name_geometry_keys_mirror_name_skill() -> None:
    # If comic-name changes its geometry key set, this must be updated in lock-step
    # (layout recomputes the name board's own hash for independence).
    assert build_layout.NAME_GEOMETRY_SETTING_KEYS == ("漫画形态", "阅读方向", "页面尺寸", "原稿规格")
