#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest import mock

import pytest

import provenance


SCRIPT = Path(__file__).with_name("provenance.py")


def test_required_asset_rejects_symlink_escape(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"outside")
    (root / "linked.mp4").symlink_to(outside)
    with pytest.raises(ValueError, match="必须位于作品根内"):
        provenance._required_asset(str(root), "linked.mp4", "final")


def _json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_validation_separates_valid_trusted_and_timestamped():
    store = {
        "active_manifest": "urn:test",
        "manifests": {"urn:test": {"signature_info": {"issuer": "CA", "time": "2026-08-20T00:00:00Z"}}},
        "validation_state": "Trusted",
        "validation_results": {"activeManifest": {
            "success": [
                {"code": "claimSignature.validated"},
                {"code": "signingCredential.trusted"},
                {"code": "timeStamp.validated"},
            ],
            "informational": [], "failure": [],
        }},
    }
    result = provenance.evaluate_validation_store(store, trust_checked=True, test_certificate=False)
    assert result["structurally_valid"] is True
    assert result["signature_valid"] is True
    assert result["trusted"] is True
    assert result["timestamp_validated"] is True
    assert result["timestamp_trusted"] is True
    assert result["timestamped"] is True
    test_result = provenance.evaluate_validation_store(store, trust_checked=True, test_certificate=True)
    assert test_result["signature_valid"] is True and test_result["trusted"] is False


def test_untrusted_signature_is_not_trusted():
    store = {
        "active_manifest": "urn:test",
        "manifests": {"urn:test": {"signature_info": {"issuer": "test"}}},
        "validation_results": {"activeManifest": {
            "success": [{"code": "claimSignature.validated"}],
            "informational": [{"code": "signingCredential.untrusted"}],
            "failure": [],
        }},
    }
    result = provenance.evaluate_validation_store(store, trust_checked=True, test_certificate=False)
    assert result["structurally_valid"] is True
    assert result["signature_valid"] is True
    assert result["trusted"] is False


def test_signing_time_is_not_mistaken_for_tsa_and_missing_success_is_fail_closed():
    store = {
        "active_manifest": "urn:test",
        "manifests": {"urn:test": {"signature_info": {"time": "2026-08-20T00:00:00Z"}}},
        "validation_status": [],
    }
    result = provenance.evaluate_validation_store(store, trust_checked=True, test_certificate=False)
    assert result["structurally_valid"] is True
    assert result["signature_valid"] is False
    assert result["trusted"] is False
    assert result["signed_at"] == "2026-08-20T00:00:00Z"
    assert result["timestamp_validated"] is False
    assert result["timestamp_trusted"] is False
    assert result["timestamped"] is False


def test_validated_but_untrusted_timestamp_is_not_release_timestamp():
    store = {
        "active_manifest": "urn:test",
        "manifests": {"urn:test": {"signature_info": {"time": "2026-08-20T00:00:00Z"}}},
        "validation_state": "Trusted",
        "validation_results": {"activeManifest": {
            "success": [
                {"code": "claimSignature.validated"},
                {"code": "signingCredential.trusted"},
                {"code": "timeStamp.validated"},
            ],
            "informational": [{"code": "timeStamp.untrusted"}],
            "failure": [],
        }},
    }
    result = provenance.evaluate_validation_store(store, trust_checked=True, test_certificate=False)
    assert result["signature_valid"] is True
    assert result["trusted"] is True
    assert result["timestamp_validated"] is True
    assert result["timestamp_trusted"] is False
    assert result["timestamped"] is False


def test_manifest_has_ai_disclosure_ingredients_and_digital_source(tmp_path: Path):
    ingredient = tmp_path / "出图" / "shot.png"
    ingredient.parent.mkdir(parents=True)
    ingredient.write_bytes(b"pixels")
    payload = provenance.build_c2pa_manifest(
        root=str(tmp_path), final_rel="成片_MV.mp4", ingredients=["出图/shot.png"],
        ai_usage={
            "visual_mode": "AI-generated", "video_mode": "AI-generated",
            "image_model": "GPT Image 2", "image_channel": "API",
            "human_contribution": "导演选片并完成剪辑。",
        },
    )
    labels = {row["label"] for row in payload["assertions"]}
    assert labels == {"c2pa.actions.v2", "c2pa.ai-disclosure"}
    assert payload["ingredient_paths"] == ["出图/shot.png"]
    actions = next(row for row in payload["assertions"] if row["label"] == "c2pa.actions.v2")
    assert actions["data"]["actions"][0]["digitalSourceType"].endswith(
        "compositeWithTrainedAlgorithmicMedia"
    )
    disclosure = next(row for row in payload["assertions"] if row["label"] == "c2pa.ai-disclosure")
    assert disclosure["data"]["modelType"] == "c2pa.types.model"
    assert disclosure["data"]["contentProfile"]["humanOversightLevel"] == "human_validated"


def test_provenance_requires_disclosure_and_binds_current_assets(tmp_path: Path):
    final = tmp_path / "成片_MV.mp4"
    master = tmp_path / "成片_MV_master.mov"
    final.write_bytes(b"final")
    master.write_bytes(b"master")
    missing = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path), "--final", "成片_MV.mp4",
         "--master", "成片_MV_master.mov", "--no-progress"],
        capture_output=True, text=True,
    )
    assert missing.returncode == 1 and "ai_usage" in missing.stderr

    _json(tmp_path / "合规" / "ai_usage.json", {
        "schema_version": 2, "kind": "mv_ai_usage",
        "visual_mode": "AI-generated", "video_mode": "AI-generated",
        "human_contribution": "剪辑与审片",
    })
    done = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path), "--final", "成片_MV.mp4",
         "--master", "成片_MV_master.mov", "--no-progress"],
        capture_output=True, text=True,
    )
    assert done.returncode == 0, done.stderr
    payload = json.loads((tmp_path / "合规" / "provenance.json").read_text(encoding="utf-8"))
    assets = {row["path"]: row["sha256"] for row in payload["assets"]}
    assert set(("成片_MV.mp4", "成片_MV_master.mov", "合规/ai_usage.json")) <= set(assets)
    assert payload["ai_usage_sha256"] == assets["合规/ai_usage.json"]
    assert payload["c2pa"]["requested"] is False


def test_existing_assets_covers_all_image_formats_nested_video_and_provider_evidence(tmp_path: Path):
    final = tmp_path / "成片_MV.mp4"
    master = tmp_path / "成片_MV_master.mov"
    final.write_bytes(b"final")
    master.write_bytes(b"master")
    expected = (
        "出图/段落/a.jpg", "出图/段落/b.jpeg", "出图/段落/c.webp",
        "出视频/视频/scene/Clip_001.mp4",
        "生产数据/provider_evidence/Clip_001/raw.json",
        "出视频/provider_evidence/Clip_001/raw.json",
    )
    for rel in expected:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"evidence")
    assets = set(provenance.existing_assets(str(tmp_path), str(final), str(master)))
    assert set(expected) <= assets


def test_embed_resolves_portable_ingredients_from_project_root(tmp_path: Path):
    compliance = tmp_path / "合规"
    compliance.mkdir()
    manifest = compliance / "c2pa_manifest.json"
    final = tmp_path / "成片_MV.mp4"
    output = tmp_path / "成片_MV.c2pa.mp4"
    manifest.write_text("{}", encoding="utf-8")
    final.write_bytes(b"final")
    store = {
        "active_manifest": "urn:test",
        "manifests": {"urn:test": {"signature_info": {"time": "2026-08-20T00:00:00Z"}}},
        "validation_state": "Trusted",
        "validation_results": {"activeManifest": {
            "success": [
                {"code": "claimSignature.validated"},
                {"code": "signingCredential.trusted"},
                {"code": "timeStamp.validated"},
            ],
            "informational": [], "failure": [],
        }},
    }
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs.get("cwd")))
        if "--output" in command:
            output.write_bytes(b"signed")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout=json.dumps(store), stderr="")

    with mock.patch.object(provenance.shutil, "which", return_value="/usr/bin/c2patool"), \
            mock.patch.object(provenance.subprocess, "run", side_effect=fake_run):
        result = provenance._embed(
            final=str(final), manifest_path=str(manifest), output=str(output),
            signer_path="/usr/local/bin/signer", identity_signer_path="",
            trust_anchors="https://example.invalid/trust.json", allow_test_certificate=False,
            allow_no_timestamp=False,
        )
    assert result["trusted"] is True
    assert result["timestamp_trusted"] is True
    assert result["trust_source"] == {"kind": "url", "url": "https://example.invalid/trust.json"}
    assert result["external_signer_configured"] is True
    assert "signer_path" not in result
    assert "identity_signer_path" not in result
    assert calls and all(cwd == str(tmp_path) for _command, cwd in calls)
