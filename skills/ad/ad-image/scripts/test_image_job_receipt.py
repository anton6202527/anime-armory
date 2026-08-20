#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import image_job_receipt as receipts  # noqa: E402


def _image(path: Path, color=(20, 40, 80)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 48), color).save(path)


def _sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _job(root: Path, job_id="镜头01_first", shot="镜头01", *, ref="设定库/ref.png", output="出图/分镜/图片/镜头01.png"):
    prompt = root / "出图" / "分镜" / "prompt" / f"{job_id}.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("real prompt", encoding="utf-8")
    return {
        "job_id": job_id,
        "shot": shot,
        "prompt": prompt.relative_to(root).as_posix(),
        "prompt_sha256": _sha(prompt),
        "expected_output": output,
        "reference_inputs": [ref] if ref else [],
        "reference_descriptors": ([{"path": ref, "owner": "PROD_A", "purpose": "product_identity"}]
                                  if ref else []),
        "status": "planned",
    }


def _qc(root: Path, findings=None):
    path = root / "出图" / "分镜" / "product_qc.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": {"block": 0, "warn": 0, "info": 0},
        "findings": findings or [],
        "qc_environment": {"precision_level": "full"},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_preflight_blocks_empty_reference_inputs(tmp_path):
    root = tmp_path / "project"
    job = _job(root, ref="")
    manifest = {"jobs": [job]}

    with pytest.raises(receipts.ReceiptBlocked, match="reference_inputs is empty"):
        receipts.preflight(root, manifest, job, 0)

    saved = json.loads(receipts.receipt_path(root, job).read_text(encoding="utf-8"))
    assert saved["status"] == "preflight_blocked"


def test_preflight_blocks_reference_sha_or_decode_mismatch(tmp_path):
    root = tmp_path / "project"
    ref = root / "设定库" / "ref.png"
    ref.parent.mkdir(parents=True)
    ref.write_bytes(b"not pixels")
    job = _job(root)

    with pytest.raises(receipts.ReceiptBlocked, match="not decodable"):
        receipts.preflight(root, {"jobs": [job]}, job, 0)


def test_next_job_blocks_until_previous_current_pixels_are_accepted(tmp_path):
    root = tmp_path / "project"
    _image(root / "设定库" / "ref.png")
    first = _job(root)
    _image(root / first["expected_output"])
    second = _job(
        root, "镜头02_first", "镜头02", ref=first["expected_output"],
        output="出图/分镜/图片/镜头02.png",
    )
    second["reference_descriptors"] = [{
        "path": first["expected_output"], "owner": first["job_id"], "purpose": "adjacent_accepted_frame",
    }]

    with pytest.raises(receipts.ReceiptBlocked, match="previous job.*not currently accepted"):
        receipts.preflight(root, {"jobs": [first, second]}, second, 1)


def test_postflight_blocks_warn_or_unverifiable_machine_qc(tmp_path):
    root = tmp_path / "project"
    _image(root / "设定库" / "ref.png")
    job = _job(root)
    manifest = {"jobs": [job]}
    receipts.preflight(root, manifest, job, 0)
    job["actual_reference_inputs"] = list(job["reference_inputs"])
    _image(root / job["expected_output"])
    qc_path = _qc(root, [{
        "severity": "warn", "shot": "镜头1", "check": "vlm_judge", "reason": "unverifiable",
    }])

    with pytest.raises(receipts.ReceiptBlocked, match="machine QC warn"):
        receipts.postflight(root, job, qc_path)

    saved = json.loads(receipts.receipt_path(root, job).read_text(encoding="utf-8"))
    assert saved["status"] == "postflight_blocked"


def test_visual_acceptance_is_invalidated_when_current_pixels_change(tmp_path):
    root = tmp_path / "project"
    _image(root / "设定库" / "ref.png")
    job = _job(root)
    manifest = {"jobs": [job]}
    receipts.preflight(root, manifest, job, 0)
    job["actual_reference_inputs"] = list(job["reference_inputs"])
    output = root / job["expected_output"]
    _image(output)
    receipts.postflight(root, job, _qc(root))

    review = root / "生产数据" / "image_job_reviews" / "镜头01.json"
    review.parent.mkdir(parents=True)
    review.write_text(json.dumps({
        "reviewer": "user",
        "decision": "accepted",
        "output_sha256": _sha(output),
        "notes": "并排核对参考图、当前图与相邻帧，所有项目通过。",
        "checks": {key: "pass" for key in receipts.REQUIRED_VISUAL_CHECKS},
    }, ensure_ascii=False), encoding="utf-8")
    receipts.signoff(root, manifest, job, review)

    assert receipts.current_accepted(root, job)[0] is True
    _image(output, color=(200, 20, 20))
    ok, reason = receipts.current_accepted(root, job)
    assert ok is False
    assert "output pixel SHA changed" in reason
