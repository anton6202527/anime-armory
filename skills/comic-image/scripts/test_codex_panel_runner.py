from pathlib import Path
import importlib.util


MODULE_PATH = Path(__file__).with_name("codex_panel_runner.py")
SPEC = importlib.util.spec_from_file_location("comic_codex_panel_runner", MODULE_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_reference_attachment_budget_prioritizes_identity_scene_and_prop() -> None:
    records = [
        {"id": "STYLE_A", "path": "style.png"},
        {"id": "LOC_A", "path": "loc.png"},
        {"id": "CHAR_A", "path": "a.png"},
        {"id": "CHAR_B", "path": "b.png"},
        {"id": "PROP_A", "path": "prop.png"},
        {"id": "FX_A", "path": "fx.png"},
    ]

    selected, omitted = runner.select_reference_attachments(records)

    assert [record["id"] for record in selected] == ["STYLE_A", "LOC_A", "CHAR_A", "CHAR_B", "PROP_A"]
    assert [record["id"] for record in omitted] == ["FX_A"]


def test_reference_manifest_discloses_omitted_text_only_contract(tmp_path: Path) -> None:
    used = [{"id": "CHAR_A", "path": "a.png", "abs_path": "/tmp/a.png", "sha256": "a"}]
    omitted = [{"id": "FX_A", "path": "fx.png", "abs_path": "/tmp/fx.png", "sha256": "f"}]

    path = runner.write_reference_manifest(tmp_path, "第1话", "P001", used, omitted)
    payload = runner.load_json(path)

    assert payload["reference_attachment_limit"] == 5
    assert payload["omitted_attachment_count"] == 1
    assert payload["omitted_attachments"][0]["id"] == "FX_A"
    assert "textual_contract_retained" in payload["omitted_attachments"][0]["reason"]


def test_post_qc_accepts_disclosed_tool_limit_omission(tmp_path: Path, monkeypatch) -> None:
    panel = tmp_path / "P015.png"
    panel.write_bytes(b"png")
    monkeypatch.setattr(runner, "png_valid", lambda _path: True)
    monkeypatch.setattr(runner, "image_size", lambda _path: (100, 100))
    monkeypatch.setattr(runner, "likely_blank_bubble_regions", lambda _path: [])
    job = {
        "panel_id": "P015",
        "size": {"width": 100, "height": 100},
        "references": [{"id": f"REF_{index}"} for index in range(6)],
    }
    used = [{"id": f"REF_{index}"} for index in range(5)]
    omitted = [{"id": "REF_5"}]

    payload = runner.post_qc_panel(tmp_path, "第1话", job, panel, used, omitted)

    assert payload["verdict"] == "pass"
    assert payload["omitted_attachment_count"] == 1
    assert payload["manual_review_required"] is False
