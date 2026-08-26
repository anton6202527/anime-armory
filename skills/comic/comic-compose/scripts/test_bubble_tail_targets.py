from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image
import pytest


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import export_longstrip


def test_dialogue_tail_consumes_speaker_anchor_and_records_tip() -> None:
    image = Image.new("RGB", (400, 300), "#777777")
    panel = {
        "panel_id": "P001", "x": 0, "y": 0, "w": 400, "h": 300,
        "speaker_anchors": {"CHAR_A": {"bbox": {"x": 300, "y": 150, "w": 60, "h": 100}}},
        "bubble_slots": [{
            "slot_id": "D1", "type": "dialogue", "speaker": "CHAR_A",
            "tail": {"mode": "toward_speaker", "target": "CHAR_A"},
            "x": 20, "y": 20, "w": 150, "h": 100,
        }],
    }
    items = [{"item_id": "D1", "slot_id": "D1", "type": "dialogue", "speaker": "CHAR_A", "text_zh": "走。"}]

    _rendered, stats = export_longstrip.apply_lettering(
        image, "P001", export_longstrip.panel_slot_info(panel), items, "", "中文"
    )

    receipt = stats["tail_receipts"][0]
    assert receipt["target_resolved"] is True
    assert receipt["target_resolution"] == "panel.speaker_anchors"
    assert receipt["target"] == "CHAR_A"
    assert receipt["target_point"] == [330, 200]
    assert receipt["tail_tip"] == receipt["target_point"]


def test_legacy_dialogue_without_anchor_keeps_visible_fallback_but_does_not_claim_resolution() -> None:
    image = Image.new("RGB", (400, 300), "#777777")
    panel = {
        "panel_id": "P001", "x": 0, "y": 0, "w": 400, "h": 300,
        "bubble_slots": [{
            "slot_id": "D1", "type": "dialogue", "speaker": "CHAR_A",
            "tail": {"mode": "toward_speaker", "target": "CHAR_A"},
            "x": 20, "y": 20, "w": 150, "h": 100,
        }],
    }
    items = [{"item_id": "D1", "slot_id": "D1", "type": "dialogue", "speaker": "CHAR_A", "text_zh": "走。"}]

    _rendered, stats = export_longstrip.apply_lettering(
        image, "P001", export_longstrip.panel_slot_info(panel), items, "", "中文"
    )

    receipt = stats["tail_receipts"][0]
    assert receipt["rendered"] is True
    assert receipt["target_resolved"] is False
    assert receipt["target_resolution"] == "deterministic_legacy_fallback"
    assert receipt["target_point"] == []
    assert len(receipt["tail_tip"]) == 2


def test_publication_lettering_consumes_real_adapter_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = Image.new("RGB", (400, 300), "#777777")
    panel = {
        "panel_id": "P001", "x": 0, "y": 0, "w": 400, "h": 300,
        "bubble_slots": [{"slot_id": "D1", "type": "dialogue", "x": 20, "y": 20, "w": 180, "h": 110}],
    }
    items = [{"item_id": "D1", "slot_id": "D1", "type": "dialogue", "text_zh": "出版文字"}]
    monkeypatch.setattr(export_longstrip.text_renderer_adapter, "select_renderer", lambda **_kwargs: {
        "adapter_id": "test-professional", "publication_claim_allowed": True, "selection_sha256": "s",
    })
    monkeypatch.setattr(export_longstrip.text_renderer_adapter, "validate_glyph_coverage", lambda *_args, **_kwargs: {
        "kind": "comic_glyph_coverage_receipt", "status": "pass", "text_sha256": "t",
    })

    def render(_request, output_path: Path, **_kwargs):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", (90, 30), (0, 0, 0, 255)).save(output_path)
        return {
            "kind": "comic_text_render_receipt", "status": "rendered",
            "publication_claim_allowed": True, "output_path": str(output_path), "output_sha256": "x",
        }

    monkeypatch.setattr(export_longstrip.text_renderer_adapter, "render_text_rgba", render)

    _rendered, stats = export_longstrip.apply_lettering(
        image,
        "P001",
        export_longstrip.panel_slot_info(panel),
        items,
        "",
        "中文",
        {"root": tmp_path, "overlay_dir": tmp_path / "pages" / "text_overlays", "text_language": "中文", "publication_required": True},
    )

    receipt = stats["text_renderer_receipts"][0]
    assert receipt["status"] == "rendered"
    assert receipt["publication_claim_allowed"] is True
    assert receipt["output_path"].startswith("pages/text_overlays/")
