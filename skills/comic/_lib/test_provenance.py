from pathlib import Path

import importlib.util
import json
import subprocess
import sys

import pytest


MODULE = Path(__file__).with_name("provenance.py")
SPEC = importlib.util.spec_from_file_location("comic_provenance_tested", MODULE)
assert SPEC and SPEC.loader
provenance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(provenance)
append_event = provenance.append_event
binding = provenance.binding
load_events = provenance.load_events
sign_c2pa = provenance.sign_c2pa
validate_chain = provenance.validate_chain
verify_c2pa_receipt = provenance.verify_c2pa_receipt
write_c2pa_sidecar = provenance.write_c2pa_sidecar


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


def test_real_signing_adapter_must_bind_validator_to_signed_bytes(tmp_path: Path):
    asset = tmp_path / "page.png"; asset.write_bytes(b"source")
    append_event(tmp_path, asset, action="generated", human_contribution="layout", rights_basis="self_owned")
    runner = tmp_path / "c2pa_runner.py"
    runner.write_text(
        "#!/usr/bin/env python3\nimport argparse,hashlib,json\n"
        "p=argparse.ArgumentParser();p.add_argument('--request');p.add_argument('--output');p.add_argument('--receipt');a=p.parse_args()\n"
        "r=json.load(open(a.request));src=open(r['source'],'rb').read();out=src+b'-signed-c2pa';open(a.output,'wb').write(out)\n"
        "json.dump({'status':'pass','validator':'fixture-c2pa','signature_valid':True,'manifest_embedded':True,'source_sha256':hashlib.sha256(src).hexdigest(),'asset_sha256':hashlib.sha256(out).hexdigest()},open(a.receipt,'w'))\n",
        encoding="utf-8",
    ); runner.chmod(0o755)
    registry = tmp_path / "生产数据" / "c2pa_signing_adapters.json"; registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps({"adapters": [{"id": "fixture", "protocol": "comic_c2pa_sign_v1", "command": [str(runner)]}]}), encoding="utf-8")
    receipt = sign_c2pa(tmp_path, asset, adapter_id="fixture")
    signed = tmp_path / receipt["signed_asset"]["path"]
    assert signed.is_file() and receipt["external_validator"]["signature_valid"] is True
    receipt_path = tmp_path / "生产数据" / "c2pa_receipts" / f"{receipt['signed_asset']['sha256']}.json"
    assert verify_c2pa_receipt(tmp_path, receipt_path)["status"] == "pass"
    report = binding(tmp_path, [{"path": receipt["signed_asset"]["path"], "sha256": receipt["signed_asset"]["sha256"]}])
    assert report["c2pa_status"] == "signed"


def test_parallel_appenders_form_one_linear_chain(tmp_path: Path):
    asset = tmp_path / "page.png"
    asset.write_bytes(b"shared-current-pixels")
    processes = []
    for index in range(16):
        script = (
            "import importlib.util,pathlib\n"
            f"module=pathlib.Path({str(MODULE)!r})\n"
            "spec=importlib.util.spec_from_file_location('comic_provenance_worker',module)\n"
            "loaded=importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded)\n"
            f"root=pathlib.Path({str(tmp_path)!r});asset=root/'page.png'\n"
            f"loaded.append_event(root,asset,action='worker-{index}')\n"
        )
        processes.append(subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
    failures = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=15)
        if process.returncode != 0:
            failures.append((process.returncode, stdout, stderr))
    assert failures == []

    events = load_events(tmp_path)
    assert len(events) == 16
    assert validate_chain(events) == []
    hashes = [str(row["event_sha256"]) for row in events]
    assert len(set(hashes)) == 16
    assert [str(row["previous_event_sha256"]) for row in events] == ["", *hashes[:-1]]


def test_torn_tail_is_fail_closed_and_never_restarts_chain(tmp_path: Path):
    asset = tmp_path / "page.png"
    asset.write_bytes(b"page")
    append_event(tmp_path, asset, action="valid-first-event")
    ledger = tmp_path / "生产数据" / "asset_provenance.jsonl"
    with ledger.open("ab") as handle:
        handle.write(b'{"kind":"comic_asset_provenance_event"')
        handle.flush()

    before = ledger.read_bytes()
    with pytest.raises(ValueError, match="torn or invalid at row 2"):
        load_events(tmp_path)
    with pytest.raises(ValueError, match="torn or invalid at row 2"):
        append_event(tmp_path, asset, action="must-not-append")
    assert ledger.read_bytes() == before
