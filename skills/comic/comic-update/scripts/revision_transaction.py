#!/usr/bin/env python3
"""Recoverable Comic revision transaction with SHA preflight and rollback."""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Mapping

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]


HERE = Path(__file__).resolve().parent
COMIC_LIB = HERE.parents[1] / "_lib"
SPEC = importlib.util.spec_from_file_location("comic_revision_dependency", COMIC_LIB / "dependency_index.py")
assert SPEC and SPEC.loader
dependency = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dependency)

KIND = "comic_revision_transaction"
GATE = HERE.parents[1] / "comic-review" / "scripts" / "gate.py"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def safe_name(value: str) -> str:
    result = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(value or ""))
    if not result:
        raise ValueError("transaction id is required")
    return result


def tx_dir(root: Path, tx_id: str) -> Path:
    return root / "生产数据" / "revision_transactions" / safe_name(tx_id)


def tx_path(root: Path, tx_id: str) -> Path:
    return tx_dir(root, tx_id) / "transaction.json"


def load(root: Path, tx_id: str) -> dict[str, Any]:
    try:
        payload = json.loads(tx_path(root, tx_id).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"revision transaction not found: {tx_id}") from exc
    if not isinstance(payload, dict) or payload.get("kind") != KIND:
        raise ValueError(f"invalid revision transaction: {tx_id}")
    return payload


def _fsync_dir(path: Path) -> None:
    try:
        directory_fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError:  # pragma: no cover - unsupported on some filesystems/OSes
        pass


def atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)
    _fsync_dir(path.parent.parent)


def wal_path(root: Path, tx_id: str) -> Path:
    return tx_dir(root, tx_id) / "wal.jsonl"


def append_wal(root: Path, tx_id: str, payload: Mapping[str, Any]) -> None:
    path = wal_path(root, tx_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"at": now_iso(), **dict(payload)}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_dir(path.parent)
    _fsync_dir(path.parent.parent)


@contextlib.contextmanager
def revision_lock(root: Path, chapter: str):
    directory = root / "生产数据" / "revision_transactions"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f".{safe_name(chapter)}.lock"
    handle = path.open("a+")
    try:
        if fcntl is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValueError(f"another revision transaction is active for {chapter}") from exc
        yield
    finally:
        if fcntl is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


def _atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.revision.{os.getpid()}.tmp")
    shutil.copy2(source, tmp)
    with tmp.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(tmp, target)
    _fsync_dir(target.parent)
    _fsync_dir(target.parent.parent)


def project_file(root: Path, raw: str) -> tuple[Path, str]:
    path = (root / raw).resolve()
    try:
        rel = str(path.relative_to(root.resolve()))
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {raw}") from exc
    if not path.is_file():
        raise ValueError(f"revision source is missing: {rel}")
    return path, rel


def start(root: Path, tx_id: str, chapter: str, paths: list[str]) -> dict[str, Any]:
    root = root.resolve()
    with revision_lock(root, chapter):
        directory = tx_dir(root, tx_id)
        if tx_path(root, tx_id).exists():
            raise ValueError("transaction already exists")
        records = []
        for raw in paths:
            source, rel = project_file(root, raw)
            candidate = directory / "candidate" / rel
            backup = directory / "backup" / rel
            _atomic_copy(source, candidate)
            _atomic_copy(source, backup)
            records.append({"path": rel, "base_sha256": sha(source), "candidate_path": str(candidate.relative_to(root)), "backup_path": str(backup.relative_to(root))})
        if not records:
            raise ValueError("at least one --path is required")
        before = dependency.build_index(root)
        payload = {
            "schema_version": 2, "kind": KIND, "transaction_id": safe_name(tx_id),
            "chapter": chapter, "created_at": now_iso(), "status": "editing", "files": records,
            "dependency_index_before": before, "verification": {}, "promotion": {},
            "wal_path": str(wal_path(root, tx_id).relative_to(root)),
        }
        atomic(tx_path(root, tx_id), payload)
        append_wal(root, tx_id, {"event": "started", "status": "editing"})
        return payload


def verify(root: Path, tx_id: str, verified_by: str) -> dict[str, Any]:
    tx = load(root, tx_id)
    with revision_lock(root, str(tx.get("chapter") or "")):
        actor = str(verified_by or "").strip()
        issues, hashes, changed = [], [], []
        for row in tx["files"]:
            current = root / row["path"]
            candidate = root / row["candidate_path"]
            if sha(current) != row["base_sha256"]:
                issues.append(f"base changed during revision: {row['path']}")
            candidate_sha = sha(candidate)
            if not candidate_sha:
                issues.append(f"candidate missing/empty: {row['path']}")
            elif candidate_sha != row["base_sha256"]:
                changed.append(row["path"])
            hashes.append({"path": row["path"], "sha256": candidate_sha})
        if not changed:
            issues.append("candidate contains no changes")
        status = "blocked" if issues else "prepared" if actor else "needs_specialist_review"
        verification = {
            "verified_at": now_iso(), "verified_by": actor, "issues": issues,
            "changed_files": changed, "candidate_hashes": hashes,
        }
        verification["prepared_digest"] = hashlib.sha256(
            json.dumps(verification, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        tx.update({"status": status, "verification": verification})
        atomic(tx_path(root, tx_id), tx)
        append_wal(root, tx_id, {"event": "verified", "status": status, "prepared_digest": verification["prepared_digest"]})
        return tx


def _candidate_hashes(tx: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(row.get("path") or ""): str(row.get("sha256") or "")
        for row in (tx.get("verification") or {}).get("candidate_hashes") or []
        if isinstance(row, Mapping)
    }


def _record_restore_conflict(
    root: Path,
    tx: dict[str, Any],
    *,
    operation: str,
    conflicts: list[dict[str, Any]],
) -> None:
    plan_path = tx_dir(root, str(tx["transaction_id"])) / "three_way_recovery_plan.json"
    plan = {
        "schema_version": 1,
        "kind": "comic_revision_three_way_recovery_plan",
        "transaction_id": tx["transaction_id"],
        "chapter": tx.get("chapter"),
        "created_at": now_iso(),
        "operation": operation,
        "status": "manual_three_way_required",
        "conflicts": conflicts,
        "instruction": "Preserve current bytes; compare base backup, this transaction candidate, and newer current frontier, then start a new revision transaction.",
    }
    atomic(plan_path, plan)
    tx["status"] = "rollback_conflict"
    tx["rollback_conflict"] = {
        "detected_at": now_iso(),
        "operation": operation,
        "plan_path": str(plan_path.relative_to(root)),
        "conflict_count": len(conflicts),
    }
    atomic(tx_path(root, str(tx["transaction_id"])), tx)
    append_wal(root, str(tx["transaction_id"]), {
        "event": "rollback_conflict", "status": "rollback_conflict",
        "operation": operation, "conflict_count": len(conflicts),
    })


def _restore_with_cas(root: Path, tx: dict[str, Any], *, operation: str) -> None:
    """Restore only bytes still owned by this transaction.

    In ``promoting`` a target may still be at its base SHA or may already be at
    the prepared candidate SHA (including the crash window before `copied` was
    journaled).  In ``committed`` every target must still match the promoted
    candidate.  Any third SHA is a newer frontier and is never overwritten.
    """
    status = str(tx.get("status") or "")
    if status not in {"promoting", "committed"}:
        raise ValueError(f"{operation} is not allowed from transaction status {status!r}")
    candidates = _candidate_hashes(tx)
    conflicts: list[dict[str, Any]] = []
    restore_rows: list[Mapping[str, Any]] = []
    for row in tx.get("files") or []:
        path = str(row.get("path") or "")
        current_sha = sha(root / path)
        base_sha = str(row.get("base_sha256") or "")
        candidate_sha = str(candidates.get(path) or "")
        if status == "committed":
            owned = bool(candidate_sha) and current_sha == candidate_sha
            should_restore = owned
        else:
            owned = current_sha in {base_sha, candidate_sha} and bool(current_sha)
            should_restore = current_sha == candidate_sha and candidate_sha != base_sha
        if not owned:
            conflicts.append({
                "path": path,
                "base_sha256": base_sha,
                "transaction_candidate_sha256": candidate_sha,
                "current_sha256": current_sha,
                "backup_path": row.get("backup_path"),
                "candidate_path": row.get("candidate_path"),
            })
        elif should_restore:
            restore_rows.append(row)
    if conflicts:
        _record_restore_conflict(root, tx, operation=operation, conflicts=conflicts)
        raise ValueError("rollback CAS conflict; newer frontier preserved and three-way recovery plan written")
    for row in restore_rows:
        _atomic_copy(root / str(row["backup_path"]), root / str(row["path"]))
    if not all(sha(root / str(row["path"])) == str(row["base_sha256"]) for row in tx.get("files") or []):
        raise ValueError("rollback could not restore every base SHA")


def promote(root: Path, tx_id: str, gate_stage: str = "review") -> dict[str, Any]:
    tx = load(root, tx_id)
    with revision_lock(root, str(tx.get("chapter") or "")):
        tx = load(root, tx_id)
        if tx.get("status") != "prepared" or not tx.get("verification", {}).get("verified_by"):
            raise ValueError("transaction must be prepared before promote")
        verified = {
            str(row.get("path") or ""): str(row.get("sha256") or "")
            for row in tx.get("verification", {}).get("candidate_hashes") or []
        }
        for row in tx["files"]:
            if sha(root / row["path"]) != row["base_sha256"]:
                raise ValueError(f"base changed after prepare: {row['path']}")
            if sha(root / row["candidate_path"]) != verified.get(row["path"]):
                raise ValueError(f"candidate changed after prepare: {row['path']}")
        tx["status"] = "promoting"
        tx["promotion"] = {"started_at": now_iso(), "gate_stage": gate_stage, "copied": []}
        atomic(tx_path(root, tx_id), tx)
        append_wal(root, tx_id, {"event": "promotion_started", "status": "promoting", "gate_stage": gate_stage})
        try:
            for row in tx["files"]:
                _atomic_copy(root / row["candidate_path"], root / row["path"])
                tx["promotion"]["copied"].append({"path": row["path"], "sha256": sha(root / row["path"])})
                atomic(tx_path(root, tx_id), tx)
                append_wal(root, tx_id, {"event": "file_promoted", "status": "promoting", "path": row["path"]})
            proc = subprocess.run(
                [sys.executable, str(GATE), str(root), "--chapter", tx["chapter"], "--stage", gate_stage],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            if proc.returncode != 0:
                _restore_with_cas(root, tx, operation="gate_failure_rollback")
                tx["status"] = "rolled_back"
                tx["promotion"].update({
                    "finished_at": now_iso(), "returncode": proc.returncode,
                    "reason": "post-promote gate failed; automatic rollback complete",
                })
                atomic(tx_path(root, tx_id), tx)
                append_wal(root, tx_id, {"event": "rolled_back", "status": "rolled_back", "reason": "gate_failed"})
                return tx
            after = dependency.build_index(root)
            tx["status"] = "committed"
            tx["promotion"].update({
                "committed_at": now_iso(), "returncode": 0,
                "dependency_impacts": dependency.compare_indices(tx.get("dependency_index_before") or {}, after),
                "current_hashes": [{"path": row["path"], "sha256": sha(root / row["path"])} for row in tx["files"]],
            })
            atomic(tx_path(root, tx_id), tx)
            append_wal(root, tx_id, {"event": "committed", "status": "committed"})
            return tx
        except BaseException:
            # Normal Python failures are repaired immediately.  A process kill
            # leaves status=promoting; the explicit recover command performs
            # the same backup restore under the chapter lock.
            _restore_with_cas(root, tx, operation="promotion_exception_rollback")
            tx["status"] = "rolled_back"
            tx["promotion"].update({"finished_at": now_iso(), "reason": "promotion exception; automatic rollback complete"})
            atomic(tx_path(root, tx_id), tx)
            append_wal(root, tx_id, {"event": "rolled_back", "status": "rolled_back", "reason": "exception"})
            raise


def recover(root: Path, tx_id: str) -> dict[str, Any]:
    tx = load(root, tx_id)
    with revision_lock(root, str(tx.get("chapter") or "")):
        tx = load(root, tx_id)
        if tx.get("status") != "promoting":
            return tx
        _restore_with_cas(root, tx, operation="crash_recovery")
        restored = all(sha(root / row["path"]) == row["base_sha256"] for row in tx.get("files") or [])
        if not restored:
            raise ValueError("recovery could not restore every base SHA")
        tx["status"] = "rolled_back"
        tx["recovery"] = {
            "recovered_at": now_iso(), "from_status": "promoting",
            "result": "backup_restored", "operator_action": "rerun verify after editing candidate",
        }
        atomic(tx_path(root, tx_id), tx)
        append_wal(root, tx_id, {"event": "crash_recovered", "status": "rolled_back"})
        return tx


def rollback(root: Path, tx_id: str) -> dict[str, Any]:
    tx = load(root, tx_id)
    with revision_lock(root, str(tx.get("chapter") or "")):
        tx = load(root, tx_id)
        if tx.get("status") == "rolled_back":
            return tx
        if tx.get("status") not in {"promoting", "committed"}:
            raise ValueError(
                f"explicit rollback is allowed only from promoting/committed, not {tx.get('status')!r}"
            )
        _restore_with_cas(root, tx, operation="explicit_rollback")
        tx.update({"status": "rolled_back", "rollback": {"rolled_back_at": now_iso(), "reason": "explicit rollback"}})
        atomic(tx_path(root, tx_id), tx)
        append_wal(root, tx_id, {"event": "rolled_back", "status": "rolled_back", "reason": "explicit"})
        return tx


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("start", "status", "verify", "promote", "recover", "rollback"))
    parser.add_argument("project_root"); parser.add_argument("transaction_id")
    parser.add_argument("--chapter", default="第1话"); parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--verified-by", default=""); parser.add_argument("--gate-stage", choices=("script", "image_preflight", "image", "compose", "review"), default="review")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv); root = Path(args.project_root).expanduser().resolve()
    try:
        if args.command == "start": result = start(root, args.transaction_id, args.chapter, args.path)
        elif args.command == "verify": result = verify(root, args.transaction_id, args.verified_by)
        elif args.command == "promote": result = promote(root, args.transaction_id, args.gate_stage)
        elif args.command == "recover": result = recover(root, args.transaction_id)
        elif args.command == "rollback": result = rollback(root, args.transaction_id)
        else: result = load(root, args.transaction_id)
    except ValueError as exc:
        print(f"[err] {exc}", file=sys.stderr); return 2
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"{args.command}: {result['status']}")
    return 0 if result["status"] not in {"blocked", "rolled_back"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
