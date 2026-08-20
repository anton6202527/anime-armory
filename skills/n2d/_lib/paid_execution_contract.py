"""Producer-owned final interlock for batch-authorized paid requests.

The batch runner may approve a request minutes before a provider subprocess is reached.  This
small contract carries only exact per-target digests into that subprocess and makes the producer
compare them again at the last local boundary before spending credits.  Absence means a manual
non-batch invocation; presence is strict and cannot be ignored or partially matched.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional


EXPECTATION_ENV = "N2D_EXPECTED_PAID_REQUESTS_JSON"
EXPECTATION_DIGEST_ENV = "N2D_EXPECTED_PAID_REQUESTS_DIGEST"
AUTHORIZATION_DIGEST_ENV = "N2D_EXPECTED_AUTHORIZATION_DIGEST"
KIND = "n2d_paid_execution_expectation"
VERSION = 1
RECEIPT_KIND = "n2d_paid_boundary_receipt"


class PaidExecutionContractError(RuntimeError):
    pass


def canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(
        dict(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def expectation_digest(payload: Mapping[str, Any]) -> str:
    return canonical_digest({key: value for key, value in payload.items() if key != "digest"})


def build_expectation(
    *,
    stage: str,
    task_id: str,
    episode: str,
    attempt: int,
    authorization_digest: str,
    records: Iterable[Mapping[str, Any]],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "stage": str(stage),
        "task_id": str(task_id),
        "episode": str(episode),
        "attempt": int(attempt),
        "authorization_digest": str(authorization_digest),
        "records": sorted(
            [dict(row) for row in records],
            key=lambda row: (
                str(row.get("target") or ""),
                str(row.get("clip") or row.get("shot") or ""),
            ),
        ),
    }
    payload["digest"] = expectation_digest(payload)
    return payload


def environment_for_expectation(payload: Mapping[str, Any]) -> Dict[str, str]:
    return {
        EXPECTATION_ENV: json.dumps(
            dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ),
        EXPECTATION_DIGEST_ENV: str(payload.get("digest") or ""),
        AUTHORIZATION_DIGEST_ENV: str(payload.get("authorization_digest") or ""),
    }


def expectation_from_environment() -> Optional[Dict[str, Any]]:
    raw = os.environ.get(EXPECTATION_ENV)
    if raw is None:
        if any(
            str(os.environ.get(name) or "").strip()
            for name in ("N2D_TASK_ID", "N2D_IDEMPOTENCY_KEY", "N2D_STAGE")
        ):
            raise PaidExecutionContractError(
                "batch/task execution markers are present but paid expectation is missing"
            )
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PaidExecutionContractError("paid execution expectation JSON is invalid") from exc
    if not isinstance(payload, dict):
        raise PaidExecutionContractError("paid execution expectation must be an object")
    if payload.get("kind") != KIND or payload.get("version") != VERSION:
        raise PaidExecutionContractError("paid execution expectation kind/version invalid")
    calculated = expectation_digest(payload)
    if str(payload.get("digest") or "") != calculated:
        raise PaidExecutionContractError("paid execution expectation digest mismatch")
    if os.environ.get(EXPECTATION_DIGEST_ENV) != calculated:
        raise PaidExecutionContractError("paid execution expectation environment digest mismatch")
    authorization = str(payload.get("authorization_digest") or "")
    if not authorization or os.environ.get(AUTHORIZATION_DIGEST_ENV) != authorization:
        raise PaidExecutionContractError("paid execution authorization digest mismatch")
    task_id = str(os.environ.get("N2D_TASK_ID") or "")
    if task_id and str(payload.get("task_id") or "") != task_id:
        raise PaidExecutionContractError("paid execution expectation task_id mismatch")
    return payload


def _receipt_path(root: Path, payload: Mapping[str, Any], row: Mapping[str, Any]) -> Path:
    identity = str(row.get("clip") or row.get("shot") or "target")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", identity).strip("._") or "target"
    token = hashlib.sha256(
        f"{row.get('target')}|{identity}".encode("utf-8")
    ).hexdigest()[:12]
    return (
        root
        / "生产数据"
        / "paid_execution_receipts"
        / str(payload.get("task_id") or "missing-task")
        / f"{safe}_{token}.json"
    )


def _write_boundary_receipt(payload: Mapping[str, Any], row: Mapping[str, Any]) -> Dict[str, Any]:
    root_text = str(os.environ.get("N2D_ROOT") or "").strip()
    if not root_text:
        raise PaidExecutionContractError("N2D_ROOT missing at paid execution boundary")
    root = Path(root_text).expanduser().resolve()
    receipt: Dict[str, Any] = {
        "kind": RECEIPT_KIND,
        "version": 1,
        "task_id": str(payload.get("task_id") or ""),
        "episode": str(payload.get("episode") or ""),
        "stage": str(payload.get("stage") or ""),
        "attempt": int(payload.get("attempt") or 0),
        "expectation_digest": str(payload.get("digest") or ""),
        "authorization_digest": str(payload.get("authorization_digest") or ""),
        "record": dict(row),
        "crossed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    receipt["digest"] = canonical_digest(
        {key: value for key, value in receipt.items() if key != "digest"}
    )
    path = _receipt_path(root, payload, row)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=path.name + ".tmp.",
        delete=False,
    ) as fh:
        fh.write(text)
        temp = Path(fh.name)
    os.replace(temp, path)
    return {**receipt, "path": path.relative_to(root).as_posix()}


def verify_expected_receipts(root: Path, payload: Mapping[str, Any]) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    issues = []
    verified = []
    rows = payload.get("records") if isinstance(payload.get("records"), list) else []
    for expected in rows:
        if not isinstance(expected, Mapping):
            issues.append("expectation record invalid")
            continue
        path = _receipt_path(root, payload, expected)
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            issues.append(f"paid boundary receipt missing or invalid: {path.relative_to(root)}")
            continue
        if not isinstance(receipt, Mapping):
            issues.append(f"paid boundary receipt is not an object: {path.relative_to(root)}")
            continue
        calculated = canonical_digest(
            {key: value for key, value in receipt.items() if key != "digest"}
        )
        if receipt.get("kind") != RECEIPT_KIND or receipt.get("version") != 1:
            issues.append(f"paid boundary receipt kind/version invalid: {path.relative_to(root)}")
        if str(receipt.get("digest") or "") != calculated:
            issues.append(f"paid boundary receipt digest mismatch: {path.relative_to(root)}")
        for key, value in (
            ("task_id", payload.get("task_id")),
            ("episode", payload.get("episode")),
            ("stage", payload.get("stage")),
            ("attempt", int(payload.get("attempt") or 0)),
            ("expectation_digest", payload.get("digest")),
            ("authorization_digest", payload.get("authorization_digest")),
        ):
            if receipt.get(key) != value:
                issues.append(f"paid boundary receipt {key} mismatch: {path.relative_to(root)}")
        if dict(receipt.get("record") or {}) != dict(expected):
            issues.append(f"paid boundary receipt request mismatch: {path.relative_to(root)}")
        verified.append({
            "path": path.relative_to(root).as_posix(),
            "digest": str(receipt.get("digest") or ""),
            "expectation_digest": str(receipt.get("expectation_digest") or ""),
            "authorization_digest": str(receipt.get("authorization_digest") or ""),
            "record": dict(receipt.get("record") or {}),
        })
    return {
        "status": "pass" if rows and not issues and len(verified) == len(rows) else "fail",
        "records": verified,
        "issues": list(dict.fromkeys(issues)),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_content_issue(path: Path) -> Optional[str]:
    """Return why a paid producer output cannot be proved usable.

    This validator is deliberately shared by the producer runner and the queue's lock-held
    completion commit.  A header-shaped file is not sufficient evidence: images must decode,
    and audio/video must expose a positive-duration stream through ffprobe.  Missing tooling is
    fail-closed because completion means "proved usable", not "probably usable".
    """
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        try:
            from PIL import Image

            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                if image.width <= 0 or image.height <= 0:
                    return "image has no decodable pixels"
        except Exception as exc:
            return f"invalid or undecodable {suffix[1:]} media ({exc})"
        return None
    if suffix not in {".mp4", ".mov", ".m4v", ".wav", ".mp3", ".m4a", ".aac", ".flac"}:
        return f"unsupported paid output type: {suffix or '<none>'}"
    stream = "v:0" if suffix in {".mp4", ".mov", ".m4v"} else "a:0"
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", stream,
                "-show_entries", "stream=codec_type:format=duration", "-of", "json", str(path),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"ffprobe unavailable or failed ({exc})"
    if probe.returncode != 0:
        detail = (probe.stderr or "").strip().splitlines()
        return "media is not ffprobe-decodable" + (f" ({detail[-1]})" if detail else "")
    try:
        data = json.loads(probe.stdout or "{}")
        streams = data.get("streams") if isinstance(data, Mapping) else None
        duration = float((data.get("format") or {}).get("duration") or 0)
    except (TypeError, ValueError, json.JSONDecodeError):
        return "ffprobe returned invalid stream/duration evidence"
    if not isinstance(streams, list) or not streams or duration <= 0:
        return "media has no required stream or positive duration"
    return None


def _expected_output_path(root: Path, payload: Mapping[str, Any], row: Mapping[str, Any]) -> Path:
    target = str(row.get("target") or "").strip()
    if str(payload.get("stage") or "") == "video" and target and not target.startswith("出视频/"):
        target = f"出视频/{payload.get('episode')}/视频/{target}"
    path = Path(target).expanduser()
    return (path if path.is_absolute() else root / path).resolve(strict=False)


def verify_current_output_bindings(
    root: Path,
    payload: Mapping[str, Any],
    verified_bindings: Any,
) -> Dict[str, Any]:
    """Re-attest exact pixels/bytes immediately before the queue commits ``done``."""
    root = root.expanduser().resolve()
    rows = payload.get("records") if isinstance(payload.get("records"), list) else []
    declared_rows = verified_bindings if isinstance(verified_bindings, list) else []
    declared = {
        str(item.get("path") or ""): item
        for item in declared_rows
        if isinstance(item, Mapping) and str(item.get("path") or "")
    }
    issues = []
    current = []
    if not rows:
        issues.append("paid expectation has no physical outputs")
    for row in rows:
        if not isinstance(row, Mapping):
            issues.append("paid expectation output row invalid")
            continue
        path = _expected_output_path(root, payload, row)
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            issues.append(f"paid output escapes project root: {path}")
            continue
        prior = declared.get(rel)
        if not isinstance(prior, Mapping):
            issues.append(f"runner did not verify paid output: {rel}")
            continue
        if not path.is_file():
            issues.append(f"paid output missing at completion commit: {rel}")
            continue
        issue = artifact_content_issue(path)
        sha256 = _sha256_file(path)
        size = path.stat().st_size
        if issue:
            issues.append(f"paid output unusable at completion commit: {rel} ({issue})")
        if str(prior.get("sha256") or "") != sha256:
            issues.append(f"paid output changed after runner verification: {rel}")
        if prior.get("exists") is not True or str(prior.get("issue") or ""):
            issues.append(f"runner output binding was not a clean pass: {rel}")
        current.append({"path": rel, "exists": True, "sha256": sha256, "bytes": size, "issue": issue or ""})
    extras = sorted(set(declared) - {str(item.get("path") or "") for item in current})
    if extras:
        issues.append("runner output bindings contain unexpected paths: " + ", ".join(extras))
    payload_out: Dict[str, Any] = {
        "kind": "n2d_paid_output_commit_attestation",
        "version": 1,
        "status": "pass" if current and not issues and len(current) == len(rows) else "fail",
        "expectation_digest": str(payload.get("digest") or ""),
        "records": current,
        "issues": list(dict.fromkeys(issues)),
    }
    payload_out["digest"] = canonical_digest(
        {key: value for key, value in payload_out.items() if key != "digest"}
    )
    return payload_out


def enforce_expected_paid_request(
    *,
    stage: str,
    identity: str,
    target: str,
    input_fingerprint: str,
    submit_request_sha256: str,
) -> Dict[str, Any]:
    payload = expectation_from_environment()
    if payload is None:
        return {"enforced": False, "reason": "manual_non_batch_invocation"}
    if str(payload.get("stage") or "") != str(stage):
        raise PaidExecutionContractError(
            f"paid execution stage mismatch: {payload.get('stage')} != {stage}"
        )
    rows = payload.get("records")
    if not isinstance(rows, list) or not rows:
        raise PaidExecutionContractError("paid execution expectation has no records")
    matches = [
        row
        for row in rows
        if isinstance(row, Mapping)
        and str(row.get("target") or "") == str(target)
        and str(row.get("clip") or row.get("shot") or "") == str(identity)
    ]
    if len(matches) != 1:
        raise PaidExecutionContractError(
            f"paid execution target is not uniquely authorized: {identity} / {target}"
        )
    expected = matches[0]
    mismatches = []
    if str(expected.get("input_fingerprint") or "") != str(input_fingerprint or ""):
        mismatches.append("input_fingerprint")
    if str(expected.get("submit_request_sha256") or "") != str(submit_request_sha256 or ""):
        mismatches.append("submit_request_sha256")
    if mismatches:
        raise PaidExecutionContractError(
            "paid request changed after authorization: " + ", ".join(mismatches)
        )
    boundary_receipt = _write_boundary_receipt(payload, expected)
    return {
        "enforced": True,
        "expectation_digest": str(payload.get("digest") or ""),
        "authorization_digest": str(payload.get("authorization_digest") or ""),
        "identity": str(identity),
        "target": str(target),
        "boundary_receipt": boundary_receipt,
    }
