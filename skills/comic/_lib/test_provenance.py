from pathlib import Path

from provenance import append_event, binding, load_events, validate_chain, write_c2pa_sidecar


def test_append_chain_and_binding(tmp_path: Path):
    asset = tmp_path / "page.png"
    asset.write_bytes(b"page")
    append_event(tmp_path, asset, action="generated", model="fixture", human_contribution="layout and lettering")
    append_event(tmp_path, asset, action="approved", rights_basis="self_owned")
    events = load_events(tmp_path)
    assert len(events) == 2
    assert validate_chain(events) == []
    report = binding(tmp_path, [{"path": "page.png", "sha256": events[-1]["asset_sha256"]}])
    assert report["chain_valid"]
    assert report["artifacts_without_current_event"] == []


def test_sidecar_is_explicitly_not_signed(tmp_path: Path):
    asset = tmp_path / "page.png"
    asset.write_bytes(b"page")
    append_event(tmp_path, asset, action="generated")
    sidecar = write_c2pa_sidecar(tmp_path, asset)
    assert '"c2pa_status": "not_signed"' in sidecar.read_text(encoding="utf-8")
