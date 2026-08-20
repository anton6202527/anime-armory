#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import sys
from unittest import mock

import contract
import mv_utils
import provenance
import release_decision


SCRIPT = Path(__file__).with_name("release_decision.py")


def test_bound_evidence_rejects_symlink_escape(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    (root / "linked.json").symlink_to(outside)
    _path, errors = release_decision._bound_evidence_errors(
        str(root), {"path": "linked.json", "sha256": release_decision.mv_utils.content_hash(outside)},
        "evidence",
    )
    assert errors


def _json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _project(root: Path) -> None:
    settings = dict(contract.DEFAULT_SETTINGS)
    settings["发行目标平台"] = "抖音"
    (root / "_设置.md").write_text(contract.settings_markdown("测试", settings), encoding="utf-8")
    runtime = contract.runtime_state_from_settings(settings)
    final = root / "成片_MV.mp4"
    master = root / "成片_MV_master.mov"
    delivery_qc = root / "生产数据" / "delivery_qc" / "delivery_qc.json"
    final.write_bytes(b"final")
    master.write_bytes(b"master")
    _json(delivery_qc, {"kind": "mv_delivery_qc_fixture", "status": "pass"})
    ai_path = _json(root / "合规" / "ai_usage.json", {
        "schema_version": 2,
        "kind": "mv_ai_usage",
        "complete": True,
        "project_root": ".",
        "reviewer": "披露人",
        "human_contribution": "人工导演、挑版和终审。",
        "visual_mode": runtime["ai_visual_usage"],
        "video_mode": runtime["ai_visual_usage"],
        "publish_target": runtime["publish_target"],
        "territories": ["CN"],
        "realism": "stylized",
        "real_person_status": "none",
        "music_mode": "human",
        "gen_ai_classification": "partly_gen_ai",
        "image_model": runtime["image_model"],
        "image_channel": runtime["image_channel"],
        "video_model": runtime["video_model"],
        "video_channel": runtime["video_channel"],
        "inputs_sha256": {"_设置.md": mv_utils.content_hash(root / "_设置.md")},
    })
    assert provenance.main([
        str(root), "--final", str(final), "--master", str(master), "--no-progress",
    ]) == 0
    provenance_path = root / "合规" / "provenance.json"
    current_c2pa = json.loads(provenance_path.read_text(encoding="utf-8")).get("c2pa") or {}
    reviewed_at = "2026-08-20T15:30:00+08:00"
    _json(root / "生产数据" / "review" / "review_receipt.json", {
        "schema_version": 1,
        "kind": "mv_review_receipt",
        "accepted": True,
        "reviewed_at": reviewed_at,
        "machine_review": {
            "hard_blocks": 0,
            "warnings": 0,
            "infos": 0,
            "findings": [],
            "findings_sha256": mv_utils.json_hash([]),
            "c2pa": {
                "requested": current_c2pa.get("requested") is True,
                "embedded": current_c2pa.get("embedded") is True,
                "structurally_valid": current_c2pa.get("structurally_valid") is True,
                "signature_valid": current_c2pa.get("signature_valid") is True,
                "trust_checked": current_c2pa.get("trust_checked") is True,
                "trusted": current_c2pa.get("trusted") is True,
                "test_certificate": str(current_c2pa.get("certificate_profile") or "").lower().startswith("test"),
                "certificate_profile": current_c2pa.get("certificate_profile") or None,
                "timestamp_validated": current_c2pa.get("timestamp_validated") is True,
                "timestamp_trusted": current_c2pa.get("timestamp_trusted") is True,
                "timestamped": current_c2pa.get("timestamped") is True,
                "timestamp_exception_allowed": current_c2pa.get("timestamp_exception_allowed") is True,
                "output": current_c2pa.get("output"),
                "output_sha256": current_c2pa.get("output_sha256"),
            },
        },
        "human_signoff": {
            "accepted": True,
            "reviewer": "总审人",
            "notes": "已逐项观看当前成片并确认交付",
            "reviewed_at": reviewed_at,
            "confirmation": {
                "kind": "explicit_current_delivery_acceptance",
                "accepted_current_delivery": True,
            },
        },
        "inputs_sha256": {
            "成片_MV.mp4": mv_utils.content_hash(final),
            "成片_MV_master.mov": mv_utils.content_hash(master),
            "生产数据/delivery_qc/delivery_qc.json": mv_utils.content_hash(delivery_qc),
            "合规/provenance.json": mv_utils.content_hash(provenance_path),
            "合规/ai_usage.json": mv_utils.content_hash(ai_path),
        },
    })


def test_rule_routing_separates_platform_and_machine_actions():
    disclosure = {
        "gen_ai_classification": "partly_gen_ai",
        "realism": "stylized",
        "real_person_status": "none",
        "music_mode": "human",
    }
    cn = release_decision.applicable_requirements(disclosure, ["抖音"], ["CN"])
    assert {row["id"] for row in cn} == {
        "machine_readable_disclosure", "platform_ai_declaration", "visible_platform_label",
    }
    youtube = release_decision.applicable_requirements(disclosure, ["YouTube"], ["US"])
    assert {row["id"] for row in youtube} == {"machine_readable_disclosure"}
    disclosure["realism"] = "photorealistic"
    youtube_real = release_decision.applicable_requirements(disclosure, ["YouTube"], ["US"])
    assert "platform_ai_declaration" in {row["id"] for row in youtube_real}


def test_comma_separated_cli_values_are_normalized():
    assert release_decision._split_values(["CN, EU", "CN"]) == ["CN", "EU"]


def test_api_upload_receipt_reextracts_remote_fields_from_raw_response(tmp_path: Path):
    final = tmp_path / "成片_MV.mp4"
    final.write_bytes(b"final")
    url = "https://www.douyin.com/video/7391234567899"
    raw = _json(tmp_path / "合规" / "upload-response.json", {
        "data": {"work_id": "7391234567899", "share_url": url,
                 "created_at": "2026-08-20T16:00:00+08:00"},
    })
    receipt = _json(tmp_path / "合规" / "上传回执.json", {
        "schema_version": 3, "kind": "mv_platform_upload_receipt",
        "source": "platform_api_response", "platform": "抖音",
        "remote_asset_id": "7391234567899", "operator": "发行人",
        "uploaded_at": "2026-08-20T16:00:00+08:00", "published_url": url,
        "uploaded_asset": {"path": "成片_MV.mp4", "sha256": mv_utils.content_hash(final)},
        "provider_evidence": {"path": "合规/upload-response.json", "sha256": mv_utils.content_hash(raw)},
        "provider_bindings": {
            "remote_asset_id": {"json_pointer": "/data/work_id"},
            "published_url": {"json_pointer": "/data/share_url"},
            "uploaded_at": {"json_pointer": "/data/created_at", "format": "iso8601"},
        },
    })
    _payload, errors = release_decision.validate_upload_receipt(
        str(tmp_path), str(receipt), platforms=["抖音"], operator="发行人",
        published_url=url,
    )
    assert errors == []
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["schema_version"] = 2
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    _payload, errors = release_decision.validate_upload_receipt(
        str(tmp_path), str(receipt), platforms=["抖音"], operator="发行人",
        published_url=url,
    )
    assert any("schema v3" in message for message in errors)
    payload["schema_version"] = 3
    payload["remote_asset_id"] = "7391234567000"
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    _payload, errors = release_decision.validate_upload_receipt(
        str(tmp_path), str(receipt), platforms=["抖音"], operator="发行人",
        published_url=url,
    )
    assert any("remote_asset_id" in message for message in errors)


def test_release_blocks_pending_actions_and_missing_upload(tmp_path: Path):
    _project(tmp_path)
    result = subprocess.run(
        [
            sys.executable, str(SCRIPT), str(tmp_path),
            "--operator", "发行人", "--notes", "发布前核验",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    payload = json.loads((tmp_path / "合规" / "release_decision.json").read_text(encoding="utf-8"))
    assert payload["decision"] == "blocked"
    assert any("上传回执" in message for message in payload["errors"])


def test_ready_decision_requires_review_and_binds_platform_machine_and_upload_evidence(tmp_path: Path):
    _project(tmp_path)
    evidence = tmp_path / "合规" / "平台AI声明截图.png"
    machine = tmp_path / "合规" / "平台元数据导出.json"
    provider = tmp_path / "合规" / "平台上传成功截图.png"
    upload = tmp_path / "合规" / "上传回执.json"
    evidence.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
    machine.write_text('{"aigc_label":true}', encoding="utf-8")
    provider.write_bytes(b"\x89PNG\r\n\x1a\nprovider-fixture")
    published_url = "https://www.douyin.com/video/7391234567890"
    _json(upload, {
        "schema_version": 3,
        "kind": "mv_platform_upload_receipt",
        "source": "platform_ui_export",
        "platform": "抖音",
        "remote_asset_id": "7391234567890",
        "operator": "发行人",
        "uploaded_at": "2026-08-20T16:00:00+08:00",
        "published_url": published_url,
        "uploaded_asset": {
            "path": "成片_MV.mp4",
            "sha256": mv_utils.content_hash(tmp_path / "成片_MV.mp4"),
        },
        "provider_evidence": {
            "path": "合规/平台上传成功截图.png",
            "sha256": mv_utils.content_hash(provider),
        },
        "ui_observation": {
            "reviewer": "发行人", "notes": "逐项查看平台上传成功页与作品链接",
            "observed_at": "2026-08-20T16:01:00+08:00",
            "remote_asset_id": "7391234567890", "published_url": published_url,
        },
    })
    command = [
        sys.executable, str(SCRIPT), str(tmp_path),
        "--operator", "发行人", "--notes", "已逐项复核平台上传页",
        "--platform-declaration-status", "completed",
        "--visible-label-status", "completed",
        "--machine-label-method", "platform_metadata",
        "--platform-evidence", str(evidence),
        "--machine-evidence", str(machine),
        "--submission-status", "uploaded",
        "--upload-receipt", str(upload),
        "--published-url", published_url,
    ]
    review = tmp_path / "生产数据" / "review" / "review_receipt.json"
    review_bytes = review.read_bytes()
    review.unlink()
    blocked = subprocess.run(command, capture_output=True, text=True)
    assert blocked.returncode == 1
    blocked_payload = json.loads((tmp_path / "合规" / "release_decision.json").read_text(encoding="utf-8"))
    assert any(message.startswith("compose:") for message in blocked_payload["errors"])
    assert any(message.startswith("review:") for message in blocked_payload["errors"])
    review.write_bytes(review_bytes)
    healthy = {"ok": True, "errors": [], "warnings": [], "evidence": {}}
    with mock.patch.object(release_decision.completion, "stage_health", return_value=healthy) as stage_health:
        assert release_decision.main(command[2:]) == 0
    assert [call.args[1] for call in stage_health.call_args_list] == [
        "compose", "disclosure", "provenance", "review",
    ]
    payload = json.loads((tmp_path / "合规" / "release_decision.json").read_text(encoding="utf-8"))
    assert payload["decision"] == "ready_for_handoff"
    assert payload["ruleset_version"] == release_decision.RULESET_VERSION
    assert payload["submission"]["receipt"]["sha256"] == mv_utils.content_hash(upload)
    assert payload["submission"]["receipt_claim"]["remote_asset_id"] == "7391234567890"
    assert payload["submission"]["receipt_claim"]["uploaded_asset"] == {
        "path": "成片_MV.mp4",
        "sha256": mv_utils.content_hash(tmp_path / "成片_MV.mp4"),
    }
    assert "final_sha256" not in payload["submission"]["receipt_claim"]
    assert payload["inputs_sha256"]["生产数据/review/review_receipt.json"] == mv_utils.content_hash(review)
    assert payload["inputs_sha256"]["合规/provenance.json"] == mv_utils.content_hash(
        tmp_path / "合规" / "provenance.json"
    )


def test_release_rejects_reserved_url_and_arbitrary_receipt_bytes(tmp_path: Path):
    _project(tmp_path)
    evidence = tmp_path / "合规" / "平台AI声明截图.png"
    machine = tmp_path / "合规" / "平台元数据导出.json"
    upload = tmp_path / "合规" / "上传回执.json"
    evidence.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
    machine.write_text('{"aigc_label":true}', encoding="utf-8")
    upload.write_bytes(b"receipt-placeholder")
    result = subprocess.run(
        [
            sys.executable, str(SCRIPT), str(tmp_path),
            "--operator", "发行人", "--notes", "逐项核验",
            "--platform-declaration-status", "completed",
            "--visible-label-status", "completed",
            "--machine-label-method", "platform_metadata",
            "--platform-evidence", str(evidence),
            "--machine-evidence", str(machine),
            "--submission-status", "uploaded",
            "--upload-receipt", str(upload),
            "--published-url", "https://example.invalid/video/123",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    payload = json.loads((tmp_path / "合规" / "release_decision.json").read_text(encoding="utf-8"))
    assert any("保留/测试域名" in message for message in payload["errors"])
    assert any("结构化 JSON" in message for message in payload["errors"])


def test_release_rejects_arbitrary_platform_and_machine_evidence_bytes(tmp_path: Path):
    _project(tmp_path)
    platform = tmp_path / "合规" / "平台证据.png"
    machine = tmp_path / "合规" / "机器证据.json"
    provider = tmp_path / "合规" / "上传成功.png"
    upload = tmp_path / "合规" / "上传回执.json"
    platform.write_bytes(b"not-an-image")
    machine.write_bytes(b"not-json")
    provider.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
    url = "https://www.douyin.com/video/7391234567891"
    _json(upload, {
        "schema_version": 3, "kind": "mv_platform_upload_receipt",
        "source": "platform_ui_export", "platform": "抖音",
        "remote_asset_id": "7391234567891", "operator": "发行人",
        "uploaded_at": "2026-08-20T16:00:00+08:00", "published_url": url,
        "uploaded_asset": {
            "path": "成片_MV.mp4",
            "sha256": mv_utils.content_hash(tmp_path / "成片_MV.mp4"),
        },
        "provider_evidence": {"path": "合规/上传成功.png", "sha256": mv_utils.content_hash(provider)},
        "ui_observation": {
            "reviewer": "发行人", "notes": "逐项查看平台上传成功页",
            "observed_at": "2026-08-20T16:01:00+08:00",
            "remote_asset_id": "7391234567891", "published_url": url,
        },
    })
    result = subprocess.run([
        sys.executable, str(SCRIPT), str(tmp_path), "--operator", "发行人",
        "--notes", "逐项核验", "--platform-declaration-status", "completed",
        "--visible-label-status", "completed", "--machine-label-method", "platform_metadata",
        "--platform-evidence", str(platform), "--machine-evidence", str(machine),
        "--submission-status", "uploaded", "--upload-receipt", str(upload),
        "--published-url", url,
    ], capture_output=True, text=True)
    assert result.returncode == 1
    payload = json.loads((tmp_path / "合规" / "release_decision.json").read_text(encoding="utf-8"))
    assert any("PNG/JPEG/PDF" in message for message in payload["errors"])
    assert any("可解析 JSON" in message for message in payload["errors"])


def test_c2pa_upload_receipt_must_bind_the_current_signed_output(tmp_path: Path):
    final = tmp_path / "成片_MV.mp4"
    signed = tmp_path / "合规" / "成片_MV.c2pa.mp4"
    provider = tmp_path / "合规" / "平台上传成功截图.png"
    final.write_bytes(b"unsigned-final")
    signed.parent.mkdir(parents=True, exist_ok=True)
    signed.write_bytes(b"signed-final")
    provider.write_bytes(b"\x89PNG\r\n\x1a\nprovider-fixture")
    url = "https://www.douyin.com/video/7391234567892"
    provenance_payload = {
        "c2pa": {
            "output": "合规/成片_MV.c2pa.mp4",
            "output_sha256": mv_utils.content_hash(signed),
        }
    }
    receipt = _json(tmp_path / "合规" / "上传回执.json", {
        "schema_version": 3,
        "kind": "mv_platform_upload_receipt",
        "source": "platform_ui_export",
        "platform": "抖音",
        "remote_asset_id": "7391234567892",
        "operator": "发行人",
        "uploaded_at": "2026-08-20T16:00:00+08:00",
        "published_url": url,
        "uploaded_asset": {
            "path": "成片_MV.mp4",
            "sha256": mv_utils.content_hash(final),
        },
        "provider_evidence": {
            "path": "合规/平台上传成功截图.png",
            "sha256": mv_utils.content_hash(provider),
        },
        "ui_observation": {
            "reviewer": "发行人",
            "notes": "已在平台上传完成页核对作品 ID 和 URL",
            "observed_at": "2026-08-20T16:01:00+08:00",
            "remote_asset_id": "7391234567892",
            "published_url": url,
        },
    })
    _payload, errors = release_decision.validate_upload_receipt(
        str(tmp_path), str(receipt), platforms=["抖音"], operator="发行人",
        published_url=url, machine_label_method="c2pa", provenance=provenance_payload,
    )
    assert any("provenance.c2pa.output" in message for message in errors)

    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["uploaded_asset"] = {
        "path": "合规/成片_MV.c2pa.mp4",
        "sha256": mv_utils.content_hash(signed),
    }
    receipt.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _payload, errors = release_decision.validate_upload_receipt(
        str(tmp_path), str(receipt), platforms=["抖音"], operator="发行人",
        published_url=url, machine_label_method="c2pa", provenance=provenance_payload,
    )
    assert errors == []
