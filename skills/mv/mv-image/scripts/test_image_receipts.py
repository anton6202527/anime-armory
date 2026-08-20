"""Regression tests for the MV B14 per-image double gate."""
from __future__ import annotations

import base64
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from PIL import Image


SCRIPT = Path(__file__).with_name("image_receipts.py")
spec = importlib.util.spec_from_file_location("mv_image_receipts", SCRIPT)
receipts = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(receipts)

RECORD_SCRIPT = Path(__file__).with_name("record_generation.py")
record_spec = importlib.util.spec_from_file_location("mv_record_generation", RECORD_SCRIPT)
record_generation = importlib.util.module_from_spec(record_spec)
assert record_spec.loader is not None
record_spec.loader.exec_module(record_generation)


def _png(path: Path, seed: int = 0, size: int = 640) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (size, size))
    pixels = image.load()
    for y in range(size):
        for x in range(size):
            pixels[x, y] = ((x * 7 + seed) % 256, (y * 11 + seed) % 256,
                            ((x + y) * 5 + seed) % 256)
    image.save(path)


def _project(tmp_path: Path) -> tuple[Path, str, str, str]:
    root = tmp_path
    prompt_rel = "出图/段落/prompt/Clip_001.md"
    ref_rel = "设定/reference_images/lead.png"
    asset_rel = "出图/段落/图片/Clip_001.png"
    prompt = root / prompt_rel
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("身份锚点 + 禁止漂移", encoding="utf-8")
    _png(root / ref_rel, seed=17)
    (root / "分镜").mkdir(parents=True, exist_ok=True)
    (root / "分镜/clip_plan.json").write_text(json.dumps({
        "kind": "mv_clip_plan",
        "clips": [{"clip_id": "Clip_001", "image_path": asset_rel,
                   "image_prompt_path": prompt_rel}],
    }, ensure_ascii=False), encoding="utf-8")
    return root, asset_rel, prompt_rel, ref_rel


def _preflight(root: Path, asset_rel: str, prompt_rel: str, ref_rel: str,
               **overrides):
    values = {
        "asset": asset_rel,
        "asset_kind": "auto",
        "owner": "lead:主唱",
        "use": "clip_start",
        "identity_scope": "contains_identity",
        "model": "GPT Image 2",
        "channel": "Codex",
        "prompt": prompt_rel,
        "reference_specs": [f"{ref_rel}::lead:主唱::identity_anchor"],
    }
    values.update(overrides)
    return receipts.create_preflight(root, **values)


def _provider_evidence(root: Path, asset_rel: str, *, model: str = "GPT Image 2",
                       channel: str = "Codex", job_id: str = "",
                       source: str = "api_response_json") -> tuple[str, str, dict]:
    current = receipts.load_ledger(root)["assets"][asset_rel]["current"]
    asset_sha = receipts.sha256_path(root / asset_rel)
    job_id = job_id or f"img-{current['attempt_id']}-{asset_sha[:12]}"
    response_payload = {
        "id": f"resp-{current['attempt_id']}-{asset_sha[:12]}",
        "created_at": int(datetime.now(timezone.utc).timestamp()),
        "model": model,
        "status": "completed",
        "output": [{
            "type": "image_generation_call",
            "id": job_id,
            "status": "completed",
            "result": base64.b64encode((root / asset_rel).read_bytes()).decode("ascii"),
        }],
    }
    raw_dir = root / "生产数据/provider_evidence/raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    if source == "api_response_json":
        raw_rel = f"生产数据/provider_evidence/raw/{job_id}.response.json"
        (root / raw_rel).write_text(
            json.dumps(response_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        adapter_id = "openai_responses_image_v1"
    else:
        raw_rel = f"生产数据/provider_evidence/raw/{job_id}.har"
        har = {"log": {"entries": [{
            "request": {"method": "POST", "url": "https://api.openai.com/v1/responses"},
            "response": {"status": 200, "content": {
                "mimeType": "application/json",
                "text": json.dumps(response_payload, ensure_ascii=False),
            }},
        }]}}
        (root / raw_rel).write_text(
            json.dumps(har, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        adapter_id = "openai_responses_image_har_v1"
    payload = {
        "kind": receipts.PROVIDER_EVIDENCE_KIND,
        "schema_version": receipts.PROVIDER_EVIDENCE_SCHEMA_VERSION,
        "source": source,
        "adapter_id": adapter_id,
        "attempt_id": current["attempt_id"],
        "preflight_sha256": current["preflight"]["receipt_sha256"],
        "raw_capture": {"path": raw_rel, "sha256": receipts.sha256_path(root / raw_rel)},
        "output_selector": 0,
    }
    if source == "ui_export":
        payload["entry_selector"] = 0
    evidence_rel = f"生产数据/provider_evidence/{job_id}.json"
    evidence = root / evidence_rel
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence_rel, job_id, payload


def _submission(root: Path, asset_rel: str, prompt_rel: str, ref_rel: str,
                *, provider_evidence: str = "", provider_job_id: str = ""):
    if not provider_evidence:
        provider_evidence, provider_job_id, _payload = _provider_evidence(root, asset_rel)
    return receipts.record_submission(
        root, asset=asset_rel, model="GPT Image 2", channel="Codex",
        prompt=prompt_rel, references=[ref_rel], provider_job_id=provider_job_id,
        provider_evidence=provider_evidence)


def _qc(root: Path, asset_rel: str, *, face_verdict: str = "ok",
        precision: str = "full") -> Path:
    path = root / receipts.QC_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    current = receipts.load_ledger(root)["assets"][asset_rel]["current"]
    payload = {
        "kind": "mv_image_qc",
        "version": 3,
        "assets_sha256": {asset_rel: receipts.sha256_path(root / asset_rel)},
        "qc_environment": {"precision_level": precision},
        "asset_integrity": {"rows": [{"asset": asset_rel, "png": asset_rel, "verdict": "ok"}]},
        "checks": {
            "face": {"shots": [{"png": asset_rel, "verdict": face_verdict}]},
            "palette": {"shots": [{"png": asset_rel, "verdict": "ok"}]},
        },
        "generation_provenance": {"uniform": True, "rows": [{
            "asset": asset_rel, "verdict": "ok",
            "b14_attempt_id": current["attempt_id"],
            "b14_preflight_sha256": current["preflight"]["receipt_sha256"],
            "b14_submission_sha256": current["submission"]["receipt_sha256"],
        }]},
        "prohibited_local_patch_outputs": {"outputs": []},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _accept(root: Path, asset_rel: str):
    return receipts.record_postflight(
        root, asset=asset_rel, qc_report=receipts.QC_REL.as_posix(),
        reviewer="审图人", visual_verdict="pass", notes="逐图与全部参考及上一验收图并排核对")


def test_discovery_covers_frames_shared_candidates_and_cover(tmp_path: Path) -> None:
    root, asset_rel, _prompt, _ref = _project(tmp_path)
    _png(root / "出图/段落/图片/Clip_001_end.png")
    _png(root / "出图/共享/图片/定妆_主唱.png")
    _png(root / "出图/候选/图片/chorus_alt.png")
    _png(root / "出图/封面/图片/cover.png")
    _png(root / "出图/废料/bad.png")
    found = receipts.discover_image_assets(root)
    assert found[asset_rel] == "clip_start"                       # plan path, even before render
    assert found["出图/段落/图片/Clip_001_end.png"] == "clip_end"
    assert found["出图/共享/图片/定妆_主唱.png"] == "shared_costume"
    assert found["出图/候选/图片/chorus_alt.png"] == "candidate"
    assert found["出图/封面/图片/cover.png"] == "cover"
    assert "出图/废料/bad.png" not in found


def test_preflight_blocks_zero_and_placeholder_references(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    with pytest.raises(receipts.ReceiptError, match="至少有一个"):
        _preflight(root, asset_rel, prompt_rel, ref_rel, reference_specs=[])
    placeholder = root / "设定/reference_images/placeholder.png"
    placeholder.write_bytes(b"not pixels")
    with pytest.raises(receipts.ReceiptError, match="不可解码"):
        _preflight(root, asset_rel, prompt_rel, ref_rel,
                   reference_specs=["设定/reference_images/placeholder.png::lead::identity"])


def test_preflight_consumes_current_clip_and_reference_contract(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    required = "设定/reference_images/costume.png"
    _png(root / required, seed=21)
    plan_path = root / "分镜/clip_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["clips"][0]["identity_ids"] = ["CHAR_LEAD"]
    plan["clips"][0]["reference_inputs"] = [{"path": required, "use": "costume_identity"}]
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(receipts.ReceiptError, match="漏掉上游"):
        _preflight(root, asset_rel, prompt_rel, ref_rel)
    with pytest.raises(receipts.ReceiptError, match="承载主体身份"):
        _preflight(
            root, asset_rel, prompt_rel, ref_rel, identity_scope="no_identity",
            reference_specs=[f"{ref_rel}::lead::identity", f"{required}::lead::costume"])
    other_prompt = "出图/段落/prompt/wrong.md"
    (root / other_prompt).write_text("wrong", encoding="utf-8")
    with pytest.raises(receipts.ReceiptError, match="clip_plan 不一致"):
        _preflight(
            root, asset_rel, other_prompt, ref_rel,
            reference_specs=[f"{ref_rel}::lead::identity", f"{required}::lead::costume"])


def test_actual_submission_must_equal_frozen_reference_set(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    with pytest.raises(receipts.ReceiptError, match="未实际提交"):
        receipts.record_submission(
            root, asset=asset_rel, model="GPT Image 2", channel="Codex",
            prompt=prompt_rel, references=[])
    other = "设定/reference_images/other.png"
    _png(root / other, seed=4)
    with pytest.raises(receipts.ReceiptError, match="计划外参考"):
        receipts.record_submission(
            root, asset=asset_rel, model="GPT Image 2", channel="Codex",
            prompt=prompt_rel, references=[ref_rel, other])
    result = _submission(root, asset_rel, prompt_rel, ref_rel)
    actual = result["submission"]["actual_references"][0]
    assert actual["path"] == ref_rel and actual["owner"] == "lead:主唱"
    assert actual["use"] == "identity_anchor" and actual["decodable"] is True


def test_provider_submission_rejects_missing_empty_and_arbitrary_evidence(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    with pytest.raises(receipts.ReceiptError, match="provider.*job|provider-job-id"):
        receipts.record_submission(
            root, asset=asset_rel, model="GPT Image 2", channel="Codex",
            prompt=prompt_rel, references=[ref_rel])

    empty_rel = "生产数据/provider_evidence/empty.json"
    (root / empty_rel).parent.mkdir(parents=True, exist_ok=True)
    (root / empty_rel).write_text("{}\n", encoding="utf-8")
    with pytest.raises(receipts.ReceiptError, match="非空|占位"):
        receipts.record_submission(
            root, asset=asset_rel, model="GPT Image 2", channel="Codex",
            prompt=prompt_rel, references=[ref_rel], provider_job_id="job-empty-0001",
            provider_evidence=empty_rel)

    legacy_rel = "生产数据/provider_evidence/legacy-v1.json"
    (root / legacy_rel).write_text(json.dumps({
        "kind": receipts.PROVIDER_EVIDENCE_KIND, "schema_version": 1,
        "source": "api_response_json", "provider": "openai",
        "provider_job_id": "job-legacy-0001", "asset_sha256": "0" * 64,
    }), encoding="utf-8")
    with pytest.raises(receipts.ReceiptError, match="schema v2"):
        receipts.record_submission(
            root, asset=asset_rel, model="GPT Image 2", channel="Codex",
            prompt=prompt_rel, references=[ref_rel], provider_job_id="job-legacy-0001",
            provider_evidence=legacy_rel)

    placeholder_rel, placeholder_job, _placeholder = _provider_evidence(
        root, asset_rel, job_id="test-job-0001")
    with pytest.raises(receipts.ReceiptError, match="非占位"):
        receipts.record_submission(
            root, asset=asset_rel, model="GPT Image 2", channel="Codex",
            prompt=prompt_rel, references=[ref_rel], provider_job_id=placeholder_job,
            provider_evidence=placeholder_rel)

    evidence_rel, job_id, payload = _provider_evidence(root, asset_rel)
    raw_path = root / payload["raw_capture"]["path"]
    raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
    raw_payload["created_at"] = 946684800
    raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False), encoding="utf-8")
    payload["raw_capture"]["sha256"] = receipts.sha256_path(raw_path)
    (root / evidence_rel).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(receipts.ReceiptError, match="provider time"):
        receipts.record_submission(
            root, asset=asset_rel, model="GPT Image 2", channel="Codex",
            prompt=prompt_rel, references=[ref_rel], provider_job_id=job_id,
            provider_evidence=evidence_rel)

    raw_payload["created_at"] = int(datetime.now(timezone.utc).timestamp())
    raw_payload["output"][0].pop("result")
    raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False), encoding="utf-8")
    payload["raw_capture"]["sha256"] = receipts.sha256_path(raw_path)
    (root / evidence_rel).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(receipts.ReceiptError, match="result.*base64"):
        receipts.record_submission(
            root, asset=asset_rel, model="GPT Image 2", channel="Codex",
            prompt=prompt_rel, references=[ref_rel], provider_job_id=job_id,
            provider_evidence=evidence_rel)

    raw_payload["output"][0]["result"] = base64.b64encode((root / asset_rel).read_bytes()).decode("ascii")
    raw_payload["output"][0]["id"] = "unrelated-job-9999"
    raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False), encoding="utf-8")
    payload["raw_capture"]["sha256"] = receipts.sha256_path(raw_path)
    (root / evidence_rel).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(receipts.ReceiptError, match="provider-job-id"):
        receipts.record_submission(
            root, asset=asset_rel, model="GPT Image 2", channel="Codex",
            prompt=prompt_rel, references=[ref_rel], provider_job_id=job_id,
            provider_evidence=evidence_rel)


def test_provider_evidence_ui_export_must_be_hash_bound_and_machine_readable(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    preflight = _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    evidence_rel, job_id, payload = _provider_evidence(root, asset_rel, source="ui_export")
    normalized = receipts.validate_provider_evidence(
        root, evidence_rel, expected_job_id=job_id, model="GPT Image 2", channel="Codex",
        asset_sha256=receipts.sha256_path(root / asset_rel),
        expected_attempt_id=preflight["attempt_id"],
        expected_preflight_sha256=preflight["preflight"]["receipt_sha256"],
        not_before=preflight["preflight"]["created_at"])
    assert normalized["raw_capture"]["sha256"] == payload["raw_capture"]["sha256"]
    assert normalized["provider_output_sha256"] == receipts.sha256_path(root / asset_rel)

    export = root / payload["raw_capture"]["path"]
    har = json.loads(export.read_text(encoding="utf-8"))
    har["log"]["entries"][0]["request"]["url"] = "https://attacker.example/v1/responses"
    export.write_text(json.dumps(har, ensure_ascii=False), encoding="utf-8")
    payload["raw_capture"]["sha256"] = receipts.sha256_path(export)
    (root / evidence_rel).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(receipts.ReceiptError, match="受信.*origin"):
        receipts.validate_provider_evidence(
            root, evidence_rel, expected_job_id=job_id, model="GPT Image 2", channel="Codex",
            asset_sha256=receipts.sha256_path(root / asset_rel),
            expected_attempt_id=preflight["attempt_id"],
            expected_preflight_sha256=preflight["preflight"]["receipt_sha256"],
            not_before=preflight["preflight"]["created_at"])

    fake_rel = f"生产数据/provider_evidence/raw/{job_id}.html"
    (root / fake_rel).write_text(
        f"openai {job_id} GPT Image 2 Codex completed 2026-08-20T00:00:00+00:00",
        encoding="utf-8")
    payload["raw_capture"] = {
        "path": fake_rel, "sha256": receipts.sha256_path(root / fake_rel),
    }
    (root / evidence_rel).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(receipts.ReceiptError, match="后缀.*har"):
        receipts.validate_provider_evidence(
            root, evidence_rel, expected_job_id=job_id, model="GPT Image 2", channel="Codex",
            asset_sha256=receipts.sha256_path(root / asset_rel),
            expected_attempt_id=preflight["attempt_id"],
            expected_preflight_sha256=preflight["preflight"]["receipt_sha256"],
            not_before=preflight["preflight"]["created_at"])


def test_provider_capture_uses_exact_fields_not_nested_spoof(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    evidence_rel, job_id, manifest = _provider_evidence(root, asset_rel)
    raw_path = root / manifest["raw_capture"]["path"]
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    raw["status"] = "failed"
    raw["spoof"] = {
        "status": "completed", "model": "GPT Image 2", "id": job_id,
        "output": raw["output"],
    }
    raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    manifest["raw_capture"]["sha256"] = receipts.sha256_path(raw_path)
    (root / evidence_rel).write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(receipts.ReceiptError, match="/status.*completed"):
        receipts.record_submission(
            root, asset=asset_rel, model="GPT Image 2", channel="Codex",
            prompt=prompt_rel, references=[ref_rel], provider_job_id=job_id,
            provider_evidence=evidence_rel)


def test_provider_output_bytes_must_equal_current_asset(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    evidence_rel, job_id, manifest = _provider_evidence(root, asset_rel)
    raw_path = root / manifest["raw_capture"]["path"]
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    raw["output"][0]["result"] = base64.b64encode(b"some other output").decode("ascii")
    raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    manifest["raw_capture"]["sha256"] = receipts.sha256_path(raw_path)
    (root / evidence_rel).write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(receipts.ReceiptError, match="output.*SHA-256.*资产"):
        receipts.record_submission(
            root, asset=asset_rel, model="GPT Image 2", channel="Codex",
            prompt=prompt_rel, references=[ref_rel], provider_job_id=job_id,
            provider_evidence=evidence_rel)


def test_provider_capture_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    evidence_rel, job_id, manifest = _provider_evidence(root, asset_rel)
    raw_path = root / manifest["raw_capture"]["path"]
    raw_text = raw_path.read_text(encoding="utf-8").replace(
        '"status": "completed",', '"status": "failed",\n  "status": "completed",', 1)
    raw_path.write_text(raw_text, encoding="utf-8")
    manifest["raw_capture"]["sha256"] = receipts.sha256_path(raw_path)
    (root / evidence_rel).write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(receipts.ReceiptError, match="重复键.*status"):
        receipts.record_submission(
            root, asset=asset_rel, model="GPT Image 2", channel="Codex",
            prompt=prompt_rel, references=[ref_rel], provider_job_id=job_id,
            provider_evidence=evidence_rel)


def test_submission_is_idempotent_but_provider_output_cannot_cross_attempt(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    evidence_rel, job_id, first_manifest = _provider_evidence(root, asset_rel)
    first = _submission(
        root, asset_rel, prompt_rel, ref_rel,
        provider_evidence=evidence_rel, provider_job_id=job_id)
    replay = _submission(
        root, asset_rel, prompt_rel, ref_rel,
        provider_evidence=evidence_rel, provider_job_id=job_id)
    assert replay["idempotent"] is True
    assert replay["submission"] == first["submission"]

    _qc(root, asset_rel)
    assert _accept(root, asset_rel)["accepted"] is True
    second_asset = "出图/段落/图片/Clip_002.png"
    second_prompt = "出图/段落/prompt/Clip_002.md"
    (root / second_prompt).write_text("prompt 2", encoding="utf-8")
    (root / second_asset).parent.mkdir(parents=True, exist_ok=True)
    (root / second_asset).write_bytes((root / asset_rel).read_bytes())
    second_preflight = _preflight(root, second_asset, second_prompt, ref_rel)
    second_manifest = json.loads(json.dumps(first_manifest))
    second_manifest["attempt_id"] = second_preflight["attempt_id"]
    second_manifest["preflight_sha256"] = second_preflight["preflight"]["receipt_sha256"]
    second_evidence_rel = "生产数据/provider_evidence/reused-output-second-attempt.json"
    (root / second_evidence_rel).write_text(
        json.dumps(second_manifest, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(receipts.ReceiptError, match="output.*已绑定其他 attempt"):
        receipts.record_submission(
            root, asset=second_asset, model="GPT Image 2", channel="Codex",
            prompt=second_prompt, references=[ref_rel], provider_job_id=job_id,
            provider_evidence=second_evidence_rel)


def test_only_explicit_local_route_does_not_claim_provider_evidence(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel, channel="local", model="local:fixture-model")
    _png(root / asset_rel, seed=2)
    result = receipts.record_submission(
        root, asset=asset_rel, model="local:fixture-model", channel="local",
        prompt=prompt_rel, references=[ref_rel])
    assert result["submission"]["provider_evidence_required"] is False
    assert result["submission"]["provider_job_id"] == ""
    assert result["submission"]["provider_evidence"] == {}


def test_cloud_model_cannot_self_exempt_with_local_channel(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel, channel="local")
    _png(root / asset_rel, seed=2)
    with pytest.raises(receipts.ReceiptError, match="provider-job-id"):
        receipts.record_submission(
            root, asset=asset_rel, model="GPT Image 2", channel="local",
            prompt=prompt_rel, references=[ref_rel])


def test_actual_submission_blocks_reference_sha_mismatch(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    _png(root / ref_rel, seed=99)  # reference pixels changed after preflight
    with pytest.raises(receipts.ReceiptError, match="SHA-256"):
        _submission(root, asset_rel, prompt_rel, ref_rel)


def test_previous_asset_interlock_and_current_pixel_acceptance(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    _submission(root, asset_rel, prompt_rel, ref_rel)

    prompt2 = "出图/段落/prompt/Clip_002.md"
    (root / prompt2).write_text("prompt 2", encoding="utf-8")
    asset2 = "出图/段落/图片/Clip_002.png"
    with pytest.raises(receipts.ReceiptError, match="尚无当前像素 accepted"):
        _preflight(root, asset2, prompt2, ref_rel)

    _qc(root, asset_rel)
    accepted = _accept(root, asset_rel)
    assert accepted["accepted"] is True
    with pytest.raises(receipts.ReceiptError, match="不得静默混用"):
        _preflight(root, asset2, prompt2, ref_rel, model="Seedream 5.0 Lite")
    second = _preflight(root, asset2, prompt2, ref_rel, previous_asset=asset_rel)
    previous = second["preflight"]["previous_acceptance"]
    assert previous["asset"] == asset_rel and previous["acceptance_sha256"]


def test_postflight_rejects_noface_and_degraded_qc(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    _submission(root, asset_rel, prompt_rel, ref_rel)
    _qc(root, asset_rel, face_verdict="noface")
    rejected = _accept(root, asset_rel)
    assert rejected["accepted"] is False
    assert "identity_face_check_not_ok" in rejected["postflight"]["machine_qc"]["findings"]

    # New attempt can retry the same asset, but degraded precision still cannot accept.
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    attempts = receipts.load_ledger(root)["assets"][asset_rel]["attempts"]
    assert len(attempts) == 2 and attempts[0]["postflight"]["status"] == "rejected"
    _png(root / asset_rel, seed=3)
    _submission(root, asset_rel, prompt_rel, ref_rel)
    _qc(root, asset_rel, precision="degraded")
    rejected2 = _accept(root, asset_rel)
    assert rejected2["accepted"] is False
    assert any("qc_precision_not_full" in value
               for value in rejected2["postflight"]["machine_qc"]["findings"])


def test_postflight_rejects_qc_from_previous_attempt_even_if_pixels_match(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    _submission(root, asset_rel, prompt_rel, ref_rel)
    _qc(root, asset_rel)  # report is bound to attempt-0001
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _submission(root, asset_rel, prompt_rel, ref_rel)  # same pixels, new attempt-0002
    rejected = _accept(root, asset_rel)
    assert rejected["accepted"] is False
    assert "qc_generation_event_not_bound_to_current_attempt" in (
        rejected["postflight"]["machine_qc"]["findings"])


def test_acceptance_invalidates_when_pixels_or_references_change(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    _submission(root, asset_rel, prompt_rel, ref_rel)
    _qc(root, asset_rel)
    assert _accept(root, asset_rel)["accepted"] is True
    assert receipts.audit_ledger(root)["summary"]["all_current_accepted"] is True

    _png(root / asset_rel, seed=9)
    audit = receipts.audit_ledger(root)
    assert audit["summary"]["all_current_accepted"] is False
    assert "asset_changed_after_acceptance" in audit["rows"][0]["findings"]

    # Restore/re-accept, then mutate a planned reference: the acceptance also stales.
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _submission(root, asset_rel, prompt_rel, ref_rel)
    _qc(root, asset_rel)
    assert _accept(root, asset_rel)["accepted"] is True
    _png(root / ref_rel, seed=31)
    findings = receipts.audit_ledger(root)["rows"][0]["findings"]
    assert any(value.startswith("reference_pixels_stale:") for value in findings)


def test_acceptance_invalidates_when_provider_evidence_file_changes(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    submitted = _submission(root, asset_rel, prompt_rel, ref_rel)
    _qc(root, asset_rel)
    assert _accept(root, asset_rel)["accepted"] is True
    evidence_rel = submitted["submission"]["provider_evidence"]["path"]
    evidence_path = root / evidence_rel
    evidence_path.write_text(evidence_path.read_text(encoding="utf-8") + " \n", encoding="utf-8")
    findings = receipts.audit_ledger(root)["rows"][0]["findings"]
    assert "provider_evidence_receipt_mismatch" in findings


def test_acceptance_invalidates_when_upstream_clip_contract_changes(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    _submission(root, asset_rel, prompt_rel, ref_rel)
    _qc(root, asset_rel)
    assert _accept(root, asset_rel)["accepted"] is True
    plan_path = root / "分镜/clip_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["clips"][0]["shot_design"] = {"costume_state": "雨战破损"}
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    findings = receipts.audit_ledger(root)["rows"][0]["findings"]
    assert "upstream_clip_or_reference_contract_stale" in findings


def test_visual_reject_is_persisted_and_never_accepted(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    _submission(root, asset_rel, prompt_rel, ref_rel)
    _qc(root, asset_rel)
    result = receipts.record_postflight(
        root, asset=asset_rel, qc_report=receipts.QC_REL.as_posix(),
        reviewer="审图人", visual_verdict="reject", notes="服装轮廓漂移")
    assert result["accepted"] is False
    saved = receipts.load_ledger(root)["assets"][asset_rel]["current"]["postflight"]
    assert saved["status"] == "rejected" and saved["visual_review"]["reviewer"] == "审图人"
    with pytest.raises(receipts.ReceiptError, match="不得覆盖"):
        receipts.record_postflight(
            root, asset=asset_rel, qc_report=receipts.QC_REL.as_posix(),
            reviewer="另一人", visual_verdict="pass", notes="试图覆盖旧结论")
    with pytest.raises(receipts.ReceiptError, match="不得用新 submission 覆盖"):
        _submission(root, asset_rel, prompt_rel, ref_rel)


def test_status_cli_nonzero_until_every_current_pixel_is_accepted(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    assert receipts.main(["status", str(root), "--json"]) == 1
    _preflight(root, asset_rel, prompt_rel, ref_rel)
    _png(root / asset_rel, seed=2)
    _submission(root, asset_rel, prompt_rel, ref_rel)
    _qc(root, asset_rel)
    _accept(root, asset_rel)
    assert receipts.main(["status", str(root)]) == 0


def test_record_generation_requires_preflight_and_writes_b14_binding(tmp_path: Path) -> None:
    root, asset_rel, prompt_rel, ref_rel = _project(tmp_path)
    _png(root / asset_rel, seed=2)
    argv = [str(root), "--asset", asset_rel, "--model", "GPT Image 2",
            "--channel", "Codex", "--prompt", prompt_rel, "--reference", ref_rel]
    assert record_generation.main(argv) == 1
    assert not (root / "生产数据/production_events.jsonl").exists()

    _preflight(root, asset_rel, prompt_rel, ref_rel)
    assert record_generation.main(argv) == 1  # 正式 provider 不能只靠自报 job id/空 evidence
    evidence_rel, job_id, _payload = _provider_evidence(root, asset_rel)
    argv.extend(["--provider-job-id", job_id, "--provider-evidence", evidence_rel])
    assert record_generation.main(argv) == 0
    event = json.loads((root / "生产数据/production_events.jsonl").read_text(encoding="utf-8"))
    generation = event["generation"]
    assert event["schema_version"] == 2
    assert generation["b14_attempt_id"] == "attempt-0001"
    assert generation["b14_preflight_sha256"]
    assert generation["b14_submission_sha256"]
    assert generation["reference_inputs"][0]["owner"] == "lead:主唱"
    assert generation["provider_job_id"] == job_id
    assert generation["provider_evidence"]["path"] == evidence_rel
    assert generation["provider_evidence"]["sha256"] == receipts.sha256_path(root / evidence_rel)
