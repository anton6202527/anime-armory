import json

from layout_candidates import has_protected_complex_layout, preview_evidence, score, write


def test_score_penalizes_bubble_overload_and_repetition():
    good = {"segments": [{"panels": [{"panel_shape": "wide", "eye_flow_entry": "top", "bubble_slots": []}, {"panel_shape": "close", "page_turn_hook": "reveal", "bubble_slots": []}]}]}
    bad = {"segments": [{"panels": [{"panel_shape": "same", "bubble_slots": [{}, {}, {}, {}, {}]}, {"panel_shape": "same", "bubble_slots": []}]}]}
    assert score(good)["total"] > score(bad)["total"]


def test_ordinary_paired_pages_are_not_mistaken_for_cross_page_art():
    ordinary = {"pages": [{"spread_id": "SPREAD_001", "spread_mode": "paired_pages", "cross_page_art": False}]}
    crossing = {"pages": [{"spread_id": "SPREAD_001", "spread_mode": "cross_page_art", "cross_page_art": True}]}

    assert has_protected_complex_layout(ordinary) is False
    assert has_protected_complex_layout(crossing) is True


def test_longstrip_preview_is_continuous_phone_screen_evidence():
    layout = {
        "geometry_profile": "longstrip_single_column",
        "canvas": {"width": 900},
        "segments": [{
            "height": 2200,
            "panels": [
                {"panel_id": "P001", "x": 50, "y": 60, "w": 800, "h": 700},
                {"panel_id": "P002", "x": 50, "y": 1000, "w": 800, "h": 800},
            ],
        }],
    }

    evidence = preview_evidence(layout)

    assert evidence["kind"] == "continuous_phone_screen_beats"
    assert evidence["viewport"]["aspect_ratio"] == "9:16"
    assert evidence["frames"]
    assert evidence["metrics"]["frame_count"] == len(evidence["frames"])


def test_write_emits_preview_and_binds_it_into_selection(tmp_path):
    layout = {
        "geometry_profile": "longstrip_single_column",
        "canvas": {"width": 900},
        "segments": [{"height": 1200, "panels": [{"panel_id": "P001", "x": 50, "y": 50, "w": 800, "h": 900}]}],
    }
    evidence = preview_evidence(layout)
    payload = {
        "schema_version": 2,
        "kind": "comic_layout_candidates",
        "chapter": "第1话",
        "input_bindings": {"panel_script_sha256": "a", "name_board_sha256": "b", "settings_sha256": "c"},
        "protected_complex_layout": False,
        "recommended_candidate_id": "balanced",
        "candidates": [{
            "candidate_id": "balanced", "max_segment_height": 16000, "gutter": 140,
            "layout_sha256": "d", "layout": layout, "preview_evidence": evidence, "score": score(layout, evidence),
        }],
    }

    report_path, selection_path = write(tmp_path, "第1话", payload, apply_best=True)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    preview = tmp_path / report["candidates"][0]["preview_evidence"]["path"]

    assert preview.is_file()
    assert "<svg" in preview.read_text(encoding="utf-8")
    assert selection["preview_evidence"]["svg_sha256"] == report["candidates"][0]["preview_evidence"]["svg_sha256"]
