#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_name_board


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_name_board_records_page_flow_and_finishing_preview(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text(
        "- 漫画形态：页漫\n- 阅读方向：从右到左\n- 页面尺寸：1440xauto\n- 原稿规格：B5商漫\n- 出图稿层：网点完成稿\n- 网点策略：显式tone_plan\n- 效果线策略：剧情驱动\n- 基础视觉风格：黑白日漫页漫\n",
        encoding="utf-8",
    )
    write_json(
        root / "脚本" / chapter / "panel_script.json",
        {
            "panels": [
                {
                    "panel_id": "P001",
                    "story_function": "opening_hook",
                    "description": "主角推门。",
                    "art_notes": "不要画成现代玻璃门。",
                    "dialogue": [{"text": "来了。"}],
                    "layout_weight": "heavy",
                },
                {"panel_id": "P002", "story_function": "reaction", "description": "对手回头。"},
            ]
        },
    )

    board = build_name_board.build_name_board(root, chapter)

    assert board["kind"] == "comic_name_board"
    assert board["schema_version"] == 2
    assert board["workflow_status"] == "draft"
    assert board["validation"]["status"] == "pass"
    assert len(board["upstream_receipt"]["panel_script_sha256"]) == 64
    assert board["manuscript"]["bleed"] > 0
    assert board["pages"][0]["page_side"] == "right"
    assert board["pages"][0]["spread_id"] == "SPREAD_001"
    assert board["pages"][0]["spread_mode"] == "paired_pages"
    assert board["pages"][0]["cross_page_art"] is False
    assert board["pages"][0]["eye_flow_path"] == ["P001", "P002"]
    assert board["pages"][0]["panels"][0]["layout_weight"] == "heavy"
    assert board["pages"][0]["panels"][0]["camera_hint"] == "主角推门。"
    assert board["pages"][0]["panels"][0]["bubble_first"] == "right_top"
    assert board["pages"][0]["panels"][0]["balloons"][0]["content_ref"] == "panel:P001.dialogue:1"
    assert board["pages"][0]["panels"][0]["balloons"][0]["tail"]["mode"] == "toward_speaker"
    assert board["pages"][0]["panels"][0]["subject_regions"]
    assert board["pages"][0]["panels"][0]["avoid_regions"]
    assert board["pages"][0]["page_turn"]["setup"]["panel_id"] == "P002"
    assert "screentone" in board["finishing_preview"]["tone_plan"]


def test_spread_grouping_is_not_cross_page_art_without_explicit_source_intent(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text("- 漫画形态：页漫\n- 阅读方向：从左到右\n", encoding="utf-8")
    write_json(root / "脚本" / chapter / "panel_script.json", {
        "panels": [
            {"panel_id": "P001", "page_hint": 1},
            {"panel_id": "P002", "page_hint": 2, "cross_page_art": True},
        ]
    })

    board = build_name_board.build_name_board(root, chapter)

    assert board["pages"][0]["spread_id"] == board["pages"][1]["spread_id"] == "SPREAD_001"
    assert board["pages"][0]["spread_mode"] == "paired_pages"
    assert board["pages"][0]["cross_page_art"] is False
    assert board["pages"][1]["spread_mode"] == "cross_page_art"
    assert board["pages"][1]["cross_page_art"] is True


def test_scroll_name_board_has_no_physical_spread(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text("- 漫画形态：条漫\n- 阅读方向：从上到下\n", encoding="utf-8")
    write_json(root / "脚本" / chapter / "panel_script.json", {"panels": [{"panel_id": "P001"}]})

    page = build_name_board.build_name_board(root, chapter)["pages"][0]

    assert page["spread_id"] == ""
    assert page["spread_mode"] == "scroll_sequence"
    assert page["cross_page_art"] is False


def test_explicit_page_hints_override_fixed_page_capacity(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text(
        "- 漫画形态：页漫\n- 阅读方向：从左到右\n- 页面尺寸：1440xauto\n- 原稿规格：B5商漫\n",
        encoding="utf-8",
    )
    panels = [
        {"panel_id": f"P{index:03d}", "story_function": "beat", "page_hint": 1 if index <= 3 else 2}
        for index in range(1, 7)
    ]
    write_json(root / "脚本" / chapter / "panel_script.json", {"panels": panels})

    board = build_name_board.build_name_board(root, chapter)

    assert len(board["pages"]) == 2
    assert board["pages"][0]["eye_flow_path"] == ["P001", "P002", "P003"]
    assert board["pages"][1]["eye_flow_path"] == ["P004", "P005", "P006"]


@pytest.mark.parametrize(
    "hints",
    [
        [1, None, 2],
        [1, 2, 1],
    ],
)
def test_partial_or_nonmonotonic_page_hints_fail_instead_of_reordering(tmp_path: Path, hints: list[int | None]) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text("- 漫画形态：页漫\n- 阅读方向：从左到右\n", encoding="utf-8")
    write_json(
        root / "脚本" / chapter / "panel_script.json",
        {
            "panels": [
                {"panel_id": f"P{index:03d}", "story_function": "beat", "page_hint": hint}
                for index, hint in enumerate(hints, 1)
            ]
        },
    )

    with pytest.raises(build_name_board.NameBoardError):
        build_name_board.build_name_board(root, chapter)


def test_name_approval_is_sha_bound_and_becomes_stale(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    settings = root / "_设置.md"
    settings.write_text("- 漫画形态：条漫\n- 阅读方向：从上到下\n", encoding="utf-8")
    write_json(
        root / "脚本" / chapter / "panel_script.json",
        {"panels": [{"panel_id": "P001", "story_function": "opening_hook", "dialogue": [{"speaker": "甲", "text": "走。"}]}]},
    )
    path = root / "排版" / chapter / "name_board.json"
    write_json(path, build_name_board.build_name_board(root, chapter))

    review = build_name_board.transition_existing(root, chapter, "review")
    assert review["workflow_status"] == "review"
    approved = build_name_board.transition_existing(root, chapter, "approved", reviewed_by="editor")
    assert approved["workflow_status"] == "approved"
    assert approved["approval"]["subject_sha256"] == build_name_board.approval_subject_sha256(approved)
    assert build_name_board.verify_approval(root, chapter, approved) == []

    settings.write_text("- 漫画形态：条漫\n- 阅读方向：从上到下\n- 页面尺寸：1280xauto\n", encoding="utf-8")
    assert any("stale" in item for item in build_name_board.verify_approval(root, chapter, approved))


def test_name_approval_requires_named_reviewer_and_review_time(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text("- 漫画形态：条漫\n- 阅读方向：从上到下\n", encoding="utf-8")
    write_json(root / "脚本" / chapter / "panel_script.json", {"panels": [{"panel_id": "P001"}]})
    write_json(root / "排版" / chapter / "name_board.json", build_name_board.build_name_board(root, chapter))
    build_name_board.transition_existing(root, chapter, "review")
    approved = build_name_board.transition_existing(root, chapter, "approved", reviewed_by="editor")
    subject_sha = build_name_board.approval_subject_sha256(approved)

    for field in ("reviewed_by", "reviewed_at"):
        malformed = json.loads(json.dumps(approved, ensure_ascii=False))
        malformed["approval"].pop(field)
        assert build_name_board.approval_subject_sha256(malformed) == subject_sha
        assert any(field in error for error in build_name_board.verify_approval(root, chapter, malformed))


def test_delegated_name_approval_requires_explicit_current_project_authorization(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    settings = root / "_设置.md"
    base_settings = "- 漫画形态：条漫\n- 阅读方向：从上到下\n"
    settings.write_text(base_settings, encoding="utf-8")
    write_json(root / "脚本" / chapter / "panel_script.json", {"panels": [{"panel_id": "P001"}]})
    write_json(root / "排版" / chapter / "name_board.json", build_name_board.build_name_board(root, chapter))
    build_name_board.transition_existing(root, chapter, "review")

    with pytest.raises(build_name_board.NameBoardError, match="未显式设置"):
        build_name_board.transition_existing(
            root,
            chapter,
            "approved",
            reviewed_by="delegate:comic-production-agent",
        )

    settings.write_text(base_settings + "- 审阅策略：用户授权制作代理\n", encoding="utf-8")
    approved = build_name_board.transition_existing(
        root,
        chapter,
        "approved",
        reviewed_by="delegate:comic-production-agent",
    )
    assert approved["approval"]["authorization"]["source"] == "project_setting"
    assert approved["approval"]["review_kind"] == "delegated_policy_auto_review"
    assert build_name_board.verify_approval(root, chapter, approved) == []

    settings.write_text(base_settings + "- 审阅策略：逐阶段用户确认\n", encoding="utf-8")
    assert any("授权" in item or "authorization" in item for item in build_name_board.verify_approval(root, chapter, approved))


def test_default_cli_writes_waiting_not_complete_until_explicit_approval(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    root.mkdir()
    (root / "_设置.md").write_text("- 漫画形态：条漫\n- 阅读方向：从上到下\n", encoding="utf-8")
    (root / "_进度.md").write_text(
        "| 话 | 缩略分镜 |\n|---|---|\n| 第1话 | ⬜ |\n",
        encoding="utf-8",
    )
    write_json(root / "脚本" / chapter / "panel_script.json", {"panels": [{"panel_id": "P001"}]})

    monkeypatch.setattr(sys, "argv", ["comic-name", str(root), "--chapter", chapter])
    assert build_name_board.main() == 0
    assert "🟡待签收" in (root / "_进度.md").read_text(encoding="utf-8")
    assert "✅" not in (root / "_进度.md").read_text(encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["comic-name", str(root), "--chapter", chapter, "--submit-review"])
    assert build_name_board.main() == 0
    monkeypatch.setattr(
        sys,
        "argv",
        ["comic-name", str(root), "--chapter", chapter, "--approve", "--reviewed-by", "editor"],
    )
    assert build_name_board.main() == 0
    assert "✅" in (root / "_进度.md").read_text(encoding="utf-8")


def _minimal_project(root: Path, chapter: str = "第1话") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "_设置.md").write_text(
        "- 漫画形态：条漫\n- 阅读方向：从上到下\n- 页面尺寸：1440xauto\n- 原稿规格：数字条漫\n"
        "- 生图模型：模型A\n- 网点策略：风格驱动\n",
        encoding="utf-8",
    )
    write_json(
        root / "脚本" / chapter / "panel_script.json",
        {"panels": [{"panel_id": "P001", "story_function": "opening_hook", "description": "开场。"}]},
    )


def test_generation_only_setting_change_does_not_stale_name_board(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    _minimal_project(root, chapter)
    board = build_name_board.build_name_board(root, chapter)
    assert build_name_board.verify_upstream(root, chapter, board) == []
    # edit a generation-only setting → must NOT stale a geometry approval
    (root / "_设置.md").write_text(
        "- 漫画形态：条漫\n- 阅读方向：从上到下\n- 页面尺寸：1440xauto\n- 原稿规格：数字条漫\n"
        "- 生图模型：模型B\n- 网点策略：显式tone_plan\n",
        encoding="utf-8",
    )
    assert build_name_board.verify_upstream(root, chapter, board) == []


def test_geometry_setting_change_stales_name_board(tmp_path: Path) -> None:
    root = tmp_path / "comic"
    chapter = "第1话"
    _minimal_project(root, chapter)
    board = build_name_board.build_name_board(root, chapter)
    # edit a geometry setting → MUST stale
    (root / "_设置.md").write_text(
        "- 漫画形态：页漫\n- 阅读方向：从上到下\n- 页面尺寸：1440xauto\n- 原稿规格：数字条漫\n"
        "- 生图模型：模型A\n- 网点策略：风格驱动\n",
        encoding="utf-8",
    )
    errors = build_name_board.verify_upstream(root, chapter, board)
    assert any("几何" in e for e in errors)
