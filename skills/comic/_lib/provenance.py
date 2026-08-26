#!/usr/bin/env python3
"""Append-only Comic asset provenance ledger with an auditable hash chain."""
from __future__ import annotations

from datetime import datetime, timezone
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, IO, Iterator, Mapping

try:
    import fcntl
except ImportError:  # pragma: no cover - Comic production currently targets macOS/POSIX
    fcntl = None  # type: ignore[assignment]


LEDGER_REL = Path("生产数据") / "asset_provenance.jsonl"
KIND = "comic_asset_provenance_event"
C2PA_REGISTRY_REL = Path("生产数据") / "c2pa_signing_adapters.json"
C2PA_PROTOCOL = "comic_c2pa_sign_v1"


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _fsync_dir(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError:  # pragma: no cover - filesystem may not support directory fsync
        pass


def _read_events(handle: IO[str], *, path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    handle.seek(0)
    for line_number, line in enumerate(handle, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"provenance ledger is torn or invalid at row {line_number}: {path}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"provenance ledger row {line_number} is not an object: {path}")
        rows.append(value)
    return rows


@contextlib.contextmanager
def _locked_ledger(path: Path, *, exclusive: bool, create: bool = False) -> Iterator[IO[str]]:
    if fcntl is None:  # pragma: no cover
        raise RuntimeError("Comic provenance requires POSIX flock support")
    mode = "a+" if create else "r"
    handle = path.open(mode, encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield handle
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def load_events(root: Path) -> list[dict[str, Any]]:
    path = root / LEDGER_REL
    if not path.is_file():
        return []
    try:
        with _locked_ledger(path, exclusive=False) as handle:
            return _read_events(handle, path=path)
    except OSError as exc:
        raise ValueError(f"provenance ledger is unreadable: {path}") from exc


def validate_chain(events: list[Mapping[str, Any]]) -> list[str]:
    errors, previous = [], ""
    for index, row in enumerate(events, 1):
        body = {key: value for key, value in row.items() if key != "event_sha256"}
        if str(row.get("previous_event_sha256") or "") != previous:
            errors.append(f"row {index}: previous_event_sha256 mismatch")
        expected = canonical_sha256(body)
        if str(row.get("event_sha256") or "") != expected:
            errors.append(f"row {index}: event_sha256 mismatch")
        previous = str(row.get("event_sha256") or "")
    return errors


def append_event(
    root: Path,
    asset: Path,
    *,
    action: str,
    model: str = "",
    model_version: str = "",
    channel: str = "",
    references: list[Mapping[str, Any]] | None = None,
    human_contribution: str = "",
    rights_basis: str = "",
    c2pa_status: str = "not_signed",
    c2pa_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root, asset = root.resolve(), asset.resolve()
    try:
        rel = str(asset.relative_to(root))
    except ValueError as exc:
        raise ValueError("asset must be inside project root") from exc
    if not asset.is_file():
        raise ValueError("asset does not exist")
    if c2pa_status not in {"not_signed", "signed"}:
        raise ValueError("c2pa_status must be not_signed or signed")
    normalized_action = str(action or "").strip()
    if not normalized_action:
        raise ValueError("action is required")
    ledger = root / LEDGER_REL
    parent_existed = ledger.parent.is_dir()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    if not parent_existed:
        _fsync_dir(root)
    try:
        # The exclusive lock covers the whole read -> validate -> append -> fsync
        # transaction.  Parallel panel workers therefore cannot fork the chain.
        with _locked_ledger(ledger, exclusive=True, create=True) as handle:
            existing = _read_events(handle, path=ledger)
            chain_errors = validate_chain(existing)
            if chain_errors:
                raise ValueError("provenance ledger chain is invalid: " + "; ".join(chain_errors))
            body = {
                "schema_version": 1,
                "kind": KIND,
                "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "asset_path": rel.replace(os.sep, "/"),
                "asset_sha256": file_sha256(asset),
                "action": normalized_action,
                "model": str(model or "").strip(),
                "model_version": str(model_version or "").strip(),
                "channel": str(channel or "").strip(),
                "references": list(references or []),
                "human_contribution": str(human_contribution or "").strip(),
                "rights_basis": str(rights_basis or "").strip(),
                "previous_event_sha256": str(existing[-1].get("event_sha256") or "") if existing else "",
                "c2pa_status": c2pa_status,
                "c2pa_receipt": dict(c2pa_receipt or {}),
            }
            event = {**body, "event_sha256": canonical_sha256(body)}
            handle.seek(0, os.SEEK_END)
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            _fsync_dir(ledger.parent)
    except OSError as exc:
        raise ValueError(f"provenance ledger append failed: {ledger}") from exc
    return event


def binding(root: Path, artifacts: list[Mapping[str, Any]]) -> dict[str, Any]:
    events = load_events(root)
    errors = validate_chain(events)
    latest = {}
    for event in events:
        latest[(str(event.get("asset_path") or ""), str(event.get("asset_sha256") or ""))] = event
    missing, artifact_credentials = [], []
    for artifact in artifacts:
        key = (str(artifact.get("path") or ""), str(artifact.get("sha256") or ""))
        event = latest.get(key)
        if event is None: missing.append(key[0])
        artifact_credentials.append({
            "path": key[0], "sha256": key[1], "event_present": event is not None,
            "c2pa_status": str((event or {}).get("c2pa_status") or "not_signed"),
            "c2pa_receipt": dict((event or {}).get("c2pa_receipt") or {}),
        })
    ledger = root / LEDGER_REL
    return {
        "ledger_path": LEDGER_REL.as_posix(),
        "ledger_sha256": file_sha256(ledger),
        "event_count": len(events),
        "chain_valid": not errors,
        "chain_errors": errors,
        "artifacts_without_current_event": missing,
        "human_authorship_summary_present": any(str(row.get("human_contribution") or "").strip() for row in events),
        "artifact_credentials": artifact_credentials,
        "c2pa_status": "signed" if artifact_credentials and all(row["c2pa_status"] == "signed" for row in artifact_credentials) else "not_signed",
    }


def write_c2pa_sidecar(root: Path, artifact: Path) -> Path:
    """Write a disclosure sidecar; never claim a cryptographic C2PA signature."""
    events = [
        row for row in load_events(root)
        if row.get("asset_path") == str(artifact.resolve().relative_to(root.resolve())).replace(os.sep, "/")
        and row.get("asset_sha256") == file_sha256(artifact)
    ]
    sidecar = artifact.with_suffix(artifact.suffix + ".provenance.json")
    payload = {
        "kind": "comic_c2pa_compatible_disclosure_sidecar",
        "asset": str(artifact.resolve().relative_to(root.resolve())).replace(os.sep, "/"),
        "asset_sha256": file_sha256(artifact),
        "c2pa_status": "not_signed",
        "notice": "This sidecar is a disclosure record, not a signed C2PA Content Credential.",
        "events": events,
    }
    sidecar.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sidecar


def _c2pa_adapters(root: Path) -> list[dict[str, Any]]:
    try: registry = json.loads((root / C2PA_REGISTRY_REL).read_text(encoding="utf-8"))
    except (OSError, ValueError): registry = {}
    result = []
    for row in registry.get("adapters") or [] if isinstance(registry, Mapping) else []:
        if not isinstance(row, Mapping) or str(row.get("protocol") or "") != C2PA_PROTOCOL: continue
        command = row.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(token, str) and token for token in command): continue
        binary = command[0] if Path(command[0]).is_absolute() else shutil.which(command[0])
        if not binary or not Path(binary).is_file(): continue
        result.append({**dict(row), "command": [str(binary), *command[1:]]})
    return result


def _adapter_command(adapter: Mapping[str, Any], request: Path, output: Path, receipt: Path) -> list[str]:
    original = list(adapter.get("command") or [])
    command = [token.replace("{request}", str(request)).replace("{output}", str(output)).replace("{receipt}", str(receipt)) for token in original]
    if not any("{request}" in token for token in original): command += ["--request", str(request)]
    if not any("{output}" in token for token in original): command += ["--output", str(output)]
    if not any("{receipt}" in token for token in original): command += ["--receipt", str(receipt)]
    return command


def sign_c2pa(
    root: Path,
    artifact: Path,
    *,
    output: Path | None = None,
    adapter_id: str = "",
) -> dict[str, Any]:
    """Create and independently verify a real signed derivative via adapter.

    Merely writing a JSON sidecar is never accepted.  The configured adapter
    must both embed a manifest and return a validator receipt for the exact
    signed bytes before the derivative is promoted.
    """
    root, artifact = root.resolve(), artifact.resolve()
    try: source_rel = artifact.relative_to(root)
    except ValueError as exc: raise ValueError("asset must be inside project root") from exc
    if not artifact.is_file(): raise ValueError("asset does not exist")
    source_sha = file_sha256(artifact)
    matching = [row for row in load_events(root) if row.get("asset_path") == source_rel.as_posix() and row.get("asset_sha256") == source_sha]
    if not matching: raise ValueError("current asset SHA has no provenance event; append disclosure first")
    adapters = _c2pa_adapters(root)
    adapter = next((row for row in adapters if not adapter_id or str(row.get("id") or "") == adapter_id), None)
    if adapter is None: raise ValueError("no executable comic_c2pa_sign_v1 signing/verification adapter")
    output = (output or artifact.with_name(f"{artifact.stem}.signed{artifact.suffix}")).resolve()
    try: output_rel = output.relative_to(root)
    except ValueError as exc: raise ValueError("signed output must be inside project root") from exc
    if output == artifact: raise ValueError("signed output must be a derivative; source is immutable")
    output.parent.mkdir(parents=True, exist_ok=True)
    ledger = root / LEDGER_REL
    disclosure = {
        "kind": "comic_c2pa_manifest_input", "c2pa_specification": "2.4",
        "source": {"path": source_rel.as_posix(), "sha256": source_sha},
        "provenance_ledger": {"path": LEDGER_REL.as_posix(), "sha256": file_sha256(ledger)},
        "events": matching,
    }
    with tempfile.TemporaryDirectory(prefix="comic-c2pa-", dir=str(output.parent)) as folder:
        stage = Path(folder); pending = stage / output.name; external_path = stage / "validator_receipt.json"
        request = stage / "request.json"; request.write_text(json.dumps({
            "protocol": C2PA_PROTOCOL, "source": str(artifact), "output": str(pending),
            "manifest": disclosure, "validator_receipt": str(external_path),
        }, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        proc = subprocess.run(_adapter_command(adapter, request, pending, external_path), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if proc.returncode != 0: raise ValueError(f"C2PA adapter failed: {(proc.stderr or proc.stdout or '')[-1500:]}")
        if not pending.is_file() or not pending.stat().st_size: raise ValueError("C2PA adapter produced no signed asset")
        signed_sha = file_sha256(pending)
        try: external = json.loads(external_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc: raise ValueError("C2PA adapter produced no valid validator receipt") from exc
        if not isinstance(external, Mapping) or external.get("status") != "pass" or not external.get("validator") or external.get("signature_valid") is not True or external.get("manifest_embedded") is not True or str(external.get("source_sha256") or "") != source_sha or str(external.get("asset_sha256") or "") != signed_sha:
            raise ValueError("C2PA validator receipt is incomplete or not bound to current bytes")
        os.replace(pending, output)
    receipt_path = root / "生产数据" / "c2pa_receipts" / f"{signed_sha}.json"
    receipt = {
        "schema_version": 1, "kind": "comic_c2pa_signature_receipt", "status": "pass",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "specification": "C2PA 2.4", "adapter": {"id": str(adapter.get("id") or ""), "protocol": C2PA_PROTOCOL},
        "source": {"path": source_rel.as_posix(), "sha256": source_sha},
        "signed_asset": {"path": output_rel.as_posix(), "sha256": signed_sha},
        "manifest_input_sha256": canonical_sha256(disclosure), "external_validator": dict(external),
        "external_validator_sha256": canonical_sha256(external),
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    pending_receipt = receipt_path.with_name(f".{receipt_path.name}.pending.{os.getpid()}")
    pending_receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(pending_receipt, receipt_path)
    append_event(
        root, output, action="c2pa_signed_derivative", channel=str(adapter.get("id") or ""),
        references=[{"path": source_rel.as_posix(), "sha256": source_sha}],
        human_contribution=str(matching[-1].get("human_contribution") or ""),
        rights_basis=str(matching[-1].get("rights_basis") or ""), c2pa_status="signed",
        c2pa_receipt={"path": receipt_path.relative_to(root).as_posix(), "sha256": file_sha256(receipt_path)},
    )
    return receipt


def verify_c2pa_receipt(root: Path, receipt_path: Path) -> dict[str, Any]:
    try: receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError): return {"status": "fail", "errors": ["invalid_receipt_json"]}
    errors = []
    signed = root.resolve() / str((receipt.get("signed_asset") or {}).get("path") or "")
    if file_sha256(signed) != str((receipt.get("signed_asset") or {}).get("sha256") or ""): errors.append("signed_asset_sha_mismatch")
    external = receipt.get("external_validator") or {}
    if canonical_sha256(external) != str(receipt.get("external_validator_sha256") or ""): errors.append("validator_receipt_sha_mismatch")
    if not isinstance(external, Mapping) or external.get("signature_valid") is not True or external.get("manifest_embedded") is not True: errors.append("signature_not_verified")
    return {"status": "pass" if not errors else "fail", "errors": errors, "receipt": str(receipt_path)}
