#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-image preflight, QC and visual-signoff receipts for the ad line.

The receipt is intentionally bound to bytes, not filenames.  A job may only
become ``accepted`` when its prompt, every submitted reference, the output
pixel file, the machine-QC report and the explicit visual-review record still
match their recorded SHA-256 values.  The next manifest job is blocked until
the previous non-cancelled job has such a current receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


REQUIRED_VISUAL_CHECKS = (
    "subject_identity",
    "product_brand_text",
    "state_scene_props",
    "style_light_color",
    "composition_safe_area",
    "continuity",
)
RECEIPT_DIR = Path("生产数据") / "image_job_receipts"
MANIFEST_REL = Path("出图") / "分镜" / "image_jobs_manifest.json"


class ReceiptBlocked(RuntimeError):
    """Raised after a fail-closed receipt has been written."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def sha256_file(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _inside(root: Path, raw: Any) -> Tuple[Path, str]:
    rel = Path(str(raw or "").strip())
    if not str(rel):
        raise ValueError("empty project path")
    path = rel if rel.is_absolute() else root / rel
    resolved = path.resolve()
    try:
        canonical = resolved.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {raw}") from exc
    return resolved, canonical


def _decode_image(path: Path) -> Dict[str, Any]:
    try:
        from PIL import Image  # type: ignore
    except Exception as exc:
        raise RuntimeError("Pillow unavailable; install Pillow before formal image generation") from exc
    try:
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            im.load()
            return {"format": str(im.format or ""), "width": int(im.width), "height": int(im.height)}
    except Exception as exc:
        raise RuntimeError(f"image is not decodable: {path}") from exc


def _safe_job_id(job_id: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", job_id).strip("_.-") or "job"
    digest = hashlib.sha256(job_id.encode("utf-8")).hexdigest()[:10]
    return f"{slug[:64]}-{digest}.json"


def receipt_rel(job: Mapping[str, Any]) -> Path:
    return RECEIPT_DIR / _safe_job_id(str(job.get("job_id") or "job"))


def receipt_path(root: Path, job: Mapping[str, Any]) -> Path:
    return root / receipt_rel(job)


def find_job(manifest: Mapping[str, Any], job_id: str) -> Tuple[Dict[str, Any], int]:
    for index, raw in enumerate(manifest.get("jobs") or []):
        if isinstance(raw, dict) and str(raw.get("job_id") or "") == job_id:
            return raw, index
    raise KeyError(f"unknown image job_id: {job_id}")


def _reference_descriptors(job: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    raw = job.get("reference_descriptors") or []
    return [row for row in raw if isinstance(row, Mapping)]


def _descriptor_by_path(job: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    return {str(row.get("path") or ""): row for row in _reference_descriptors(job) if row.get("path")}


def _record_failure(root: Path, job: Mapping[str, Any], phase: str, findings: Iterable[str],
                    base: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    payload = dict(base or {})
    payload.update({
        "schema_version": 1,
        "kind": "ad_image_job_receipt",
        "job_id": str(job.get("job_id") or ""),
        "status": f"{phase}_blocked",
        "phase": phase,
        "findings": list(findings),
        "updated_at": now_iso(),
    })
    write_json(receipt_path(root, job), payload)
    return payload


def _current_reference_rows(root: Path, rows: Sequence[Mapping[str, Any]]) -> bool:
    for row in rows:
        try:
            path, rel = _inside(root, row.get("path"))
        except ValueError:
            return False
        if rel != row.get("path") or sha256_file(path) != row.get("sha256"):
            return False
    return True


def current_accepted(root: Path, job: Mapping[str, Any]) -> Tuple[bool, str]:
    receipt = load_json(receipt_path(root, job), {}) or {}
    if receipt.get("status") != "accepted":
        return False, f"receipt status={receipt.get('status') or 'missing'}"
    try:
        prompt, _ = _inside(root, job.get("prompt"))
        output, _ = _inside(root, job.get("expected_output") or job.get("output"))
    except ValueError as exc:
        return False, str(exc)
    if sha256_file(prompt) != receipt.get("prompt_sha256"):
        return False, "prompt SHA changed"
    if sha256_file(output) != receipt.get("output_sha256"):
        return False, "output pixel SHA changed"
    refs = receipt.get("reference_inputs") or []
    if not isinstance(refs, list) or not refs or not _current_reference_rows(root, refs):
        return False, "reference input missing or SHA changed"
    review = receipt.get("visual_review") or {}
    try:
        review_file, _ = _inside(root, review.get("review_file"))
    except ValueError:
        return False, "visual review file invalid"
    if sha256_file(review_file) != review.get("review_file_sha256"):
        return False, "visual review evidence changed"
    return True, "accepted and current"


def preflight(root: Path, manifest: Mapping[str, Any], job: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Validate and record the exact prompt/reference package before spend."""
    root = root.resolve()
    findings: List[str] = []
    prompt_sha = None
    refs: List[Dict[str, Any]] = []
    try:
        prompt_path, prompt_rel = _inside(root, job.get("prompt"))
        prompt_sha = sha256_file(prompt_path)
        if not prompt_sha:
            findings.append(f"prompt missing: {prompt_rel}")
        planned = str(job.get("prompt_sha256") or "")
        if not planned or prompt_sha != planned:
            findings.append("prompt SHA does not match manifest prompt_sha256")
    except ValueError as exc:
        findings.append(str(exc))

    planned_refs = [str(value) for value in (job.get("reference_inputs") or []) if str(value).strip()]
    descriptors = _descriptor_by_path(job)
    if not planned_refs:
        findings.append("reference_inputs is empty; formal generation requires real pixel references")
    if list(descriptors) != planned_refs:
        findings.append("reference_descriptors paths/order do not exactly match reference_inputs")
    for raw in planned_refs:
        desc = descriptors.get(raw) or {}
        purpose = str(desc.get("purpose") or "").strip()
        owner = str(desc.get("owner") or desc.get("owner_asset_id") or "").strip()
        if not purpose or not owner:
            findings.append(f"reference lacks purpose/owner: {raw}")
        try:
            path, rel = _inside(root, raw)
            digest = sha256_file(path)
            if not digest:
                findings.append(f"reference missing: {rel}")
                continue
            try:
                image = _decode_image(path)
            except RuntimeError as exc:
                findings.append(str(exc))
                continue
            refs.append({"path": rel, "sha256": digest, "purpose": purpose, "owner": owner, **image})
        except ValueError as exc:
            findings.append(str(exc))

    jobs = manifest.get("jobs") or []
    previous = None
    for raw in reversed(jobs[:index]):
        if isinstance(raw, dict) and raw.get("status") != "cancelled":
            previous = raw
            break
    previous_binding = None
    if previous is not None:
        ok, reason = current_accepted(root, previous)
        if not ok:
            findings.append(f"previous job {previous.get('job_id')} not currently accepted: {reason}")
        prev_rel = str(previous.get("expected_output") or previous.get("output") or "")
        if prev_rel not in planned_refs:
            findings.append(f"adjacent accepted frame is not an actual planned reference: {prev_rel}")
        previous_binding = {
            "job_id": previous.get("job_id"),
            "output": prev_rel,
            "output_sha256": sha256_file(root / prev_rel) if prev_rel else None,
        }

    payload = {
        "schema_version": 1,
        "kind": "ad_image_job_receipt",
        "job_id": str(job.get("job_id") or ""),
        "phase": "preflight",
        "status": "preflight_passed" if not findings else "preflight_blocked",
        "prompt": str(job.get("prompt") or ""),
        "prompt_sha256": prompt_sha,
        "reference_inputs": refs,
        "previous_job": previous_binding,
        "findings": findings,
        "preflight_at": now_iso(),
        "updated_at": now_iso(),
    }
    write_json(receipt_path(root, job), payload)
    job["qc_receipt"] = receipt_rel(job).as_posix()
    if findings:
        raise ReceiptBlocked("; ".join(findings))
    return payload


def _same_shot(left: Any, right: Any) -> bool:
    def norm(value: Any) -> str:
        raw = str(value or "").lower().replace(" ", "")
        match = re.search(r"(?:镜头|shot)0*(\d+)", raw)
        return f"shot{int(match.group(1))}" if match else raw
    return norm(left) == norm(right)


def _qc_findings_for_job(qc: Mapping[str, Any], job: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    shot = job.get("shot") or job.get("job_id")
    out = []
    for raw in qc.get("findings") or []:
        if not isinstance(raw, Mapping):
            continue
        target = raw.get("shot")
        if target in (None, "", "-") or _same_shot(target, shot):
            out.append(raw)
    return out


def postflight(root: Path, job: Dict[str, Any], qc_path: Optional[Path] = None) -> Dict[str, Any]:
    """Bind current output and full machine-QC evidence, then await visual review."""
    root = root.resolve()
    path = receipt_path(root, job)
    receipt = load_json(path, {}) or {}
    findings: List[str] = []
    if receipt.get("status") != "preflight_passed":
        findings.append("a current passed preflight receipt is required")
    try:
        output, output_rel = _inside(root, job.get("expected_output") or job.get("output"))
        output_sha = sha256_file(output)
        if not output_sha:
            findings.append(f"output missing: {output_rel}")
            image_meta: Dict[str, Any] = {}
        else:
            try:
                image_meta = _decode_image(output)
            except RuntimeError as exc:
                findings.append(str(exc))
                image_meta = {}
    except ValueError as exc:
        findings.append(str(exc))
        output_rel, output_sha, image_meta = "", None, {}

    actual = [str(v) for v in (job.get("actual_reference_inputs") or [])]
    planned = [str(row.get("path")) for row in (receipt.get("reference_inputs") or [])]
    if actual != planned:
        findings.append("runner actual_reference_inputs do not exactly match passed preflight references")

    qc_path = qc_path or (root / "出图" / "分镜" / "product_qc.json")
    qc = load_json(qc_path, {}) or {}
    qc_sha = sha256_file(qc_path)
    precision = str(((qc.get("qc_environment") or {}).get("precision_level") or ""))
    if not qc_sha:
        findings.append("machine QC report missing")
    if precision != "full":
        findings.append(f"machine QC precision is {precision or 'unknown'}, not full")
    scoped = _qc_findings_for_job(qc, job)
    for raw in scoped:
        severity = str(raw.get("severity") or "").lower()
        detail = raw.get("detail") if isinstance(raw.get("detail"), Mapping) else {}
        if severity in {"block", "warn", "error", "unverifiable"} or detail.get("degraded"):
            findings.append(
                f"machine QC {severity or 'unverifiable'} [{raw.get('check') or raw.get('code') or '?'}]: "
                f"{raw.get('reason') or raw.get('msg') or ''}"
            )

    receipt.update({
        "phase": "postflight",
        "status": "postflight_blocked" if findings else "awaiting_human_signoff",
        "output": output_rel,
        "output_sha256": output_sha,
        "output_image": image_meta,
        "machine_qc": {
            "path": qc_path.relative_to(root).as_posix() if qc_path.is_relative_to(root) else str(qc_path),
            "sha256": qc_sha,
            "precision_level": precision,
            "scoped_findings": [dict(row) for row in scoped],
        },
        "findings": findings,
        "postflight_at": now_iso(),
        "updated_at": now_iso(),
    })
    write_json(path, receipt)
    job["qc_receipt"] = receipt_rel(job).as_posix()
    if findings:
        raise ReceiptBlocked("; ".join(findings))
    return receipt


def signoff(root: Path, manifest: Dict[str, Any], job: Dict[str, Any], review_file: Path) -> Dict[str, Any]:
    """Apply an explicit human review bound to the current output pixel SHA."""
    root = root.resolve()
    receipt = load_json(receipt_path(root, job), {}) or {}
    if receipt.get("status") != "awaiting_human_signoff":
        raise ReceiptBlocked(f"job is not awaiting signoff: {receipt.get('status') or 'missing'}")
    review_path, review_rel = _inside(root, review_file)
    review = load_json(review_path, {}) or {}
    errors: List[str] = []
    reviewer = str(review.get("reviewer") or "").strip()
    decision = str(review.get("decision") or "").strip().lower()
    notes = str(review.get("notes") or "").strip()
    if not reviewer:
        errors.append("reviewer is required")
    if decision not in {"accepted", "rejected"}:
        errors.append("decision must be accepted or rejected")
    if not notes:
        errors.append("review notes are required")
    if review.get("output_sha256") != receipt.get("output_sha256"):
        errors.append("review output_sha256 does not bind the current generated pixels")
    checks = review.get("checks") if isinstance(review.get("checks"), Mapping) else {}
    if decision == "accepted":
        missing = [key for key in REQUIRED_VISUAL_CHECKS if str(checks.get(key) or "").lower() != "pass"]
        if missing:
            errors.append("accepted review requires pass for: " + ", ".join(missing))
    review_sha = sha256_file(review_path)
    if not review_sha:
        errors.append("review evidence file is missing")
    if errors:
        raise ReceiptBlocked("; ".join(errors))
    receipt.update({
        "phase": "visual_signoff",
        "status": decision,
        "visual_review": {
            "reviewer": reviewer,
            "decision": decision,
            "notes": notes,
            "checks": dict(checks),
            "review_file": review_rel,
            "review_file_sha256": review_sha,
            "reviewed_at": str(review.get("reviewed_at") or now_iso()),
        },
        "findings": [] if decision == "accepted" else ["human visual review rejected current pixels"],
        "updated_at": now_iso(),
    })
    write_json(receipt_path(root, job), receipt)
    job["qc_receipt"] = receipt_rel(job).as_posix()
    job["status"] = "done" if decision == "accepted" else "rejected"
    job["accepted_output_sha256"] = receipt.get("output_sha256") if decision == "accepted" else None
    write_json(root / MANIFEST_REL, manifest)
    return receipt


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="audit or sign a per-image ad generation receipt")
    ap.add_argument("project_root")
    sub = ap.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("--job", required=True)
    sign = sub.add_parser("signoff")
    sign.add_argument("--job", required=True)
    sign.add_argument("--review-file", required=True,
                      help="project-local JSON binding output_sha256 and all required visual checks")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    manifest = load_json(root / MANIFEST_REL, {}) or {}
    try:
        job, _ = find_job(manifest, ns.job)
        if ns.command == "audit":
            ok, reason = current_accepted(root, job)
            print(json.dumps({"job_id": ns.job, "accepted": ok, "reason": reason}, ensure_ascii=False))
            return 0 if ok else 1
        receipt = signoff(root, manifest, job, Path(ns.review_file))
        print(json.dumps({"job_id": ns.job, "status": receipt["status"]}, ensure_ascii=False))
        return 0 if receipt["status"] == "accepted" else 1
    except (KeyError, ReceiptBlocked, ValueError) as exc:
        print(f"[block] {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
