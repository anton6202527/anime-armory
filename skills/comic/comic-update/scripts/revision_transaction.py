#!/usr/bin/env python3
"""Recoverable Comic revision transaction with SHA preflight and rollback."""
from __future__ import annotations

import argparse
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


def atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


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
    directory = tx_dir(root, tx_id)
    if tx_path(root, tx_id).exists():
        raise ValueError("transaction already exists")
    records = []
    for raw in paths:
        source, rel = project_file(root, raw)
        candidate = directory / "candidate" / rel
        backup = directory / "backup" / rel
        candidate.parent.mkdir(parents=True, exist_ok=True)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, candidate); shutil.copy2(source, backup)
        records.append({"path": rel, "base_sha256": sha(source), "candidate_path": str(candidate.relative_to(root)), "backup_path": str(backup.relative_to(root))})
    if not records:
        raise ValueError("at least one --path is required")
    before = dependency.build_index(root)
    payload = {
        "schema_version": 1, "kind": KIND, "transaction_id": safe_name(tx_id),
        "chapter": chapter, "created_at": now_iso(), "status": "editing", "files": records,
        "dependency_index_before": before, "verification": {}, "promotion": {},
    }
    atomic(tx_path(root, tx_id), payload)
    return payload


def verify(root: Path, tx_id: str, verified_by: str) -> dict[str, Any]:
    tx = load(root, tx_id)
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
    status = "blocked" if issues else "verified" if actor else "needs_specialist_review"
    tx.update({
        "status": status, "verification": {
            "verified_at": now_iso(), "verified_by": actor, "issues": issues,
            "changed_files": changed, "candidate_hashes": hashes,
        },
    })
    atomic(tx_path(root, tx_id), tx)
    return tx


def _restore(root: Path, tx: Mapping[str, Any]) -> None:
    for row in tx.get("files") or []:
        shutil.copy2(root / row["backup_path"], root / row["path"])


def promote(root: Path, tx_id: str, gate_stage: str = "review") -> dict[str, Any]:
    tx = load(root, tx_id)
    if tx.get("status") != "verified" or not tx.get("verification", {}).get("verified_by"):
        raise ValueError("transaction must be verified before promote")
    for row in tx["files"]:
        if sha(root / row["path"]) != row["base_sha256"]:
            raise ValueError(f"base changed after verify: {row['path']}")
        shutil.copy2(root / row["candidate_path"], root / row["path"])
    proc = subprocess.run(
        [sys.executable, str(GATE), str(root), "--chapter", tx["chapter"], "--stage", gate_stage],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        _restore(root, tx)
        tx["status"] = "rolled_back"
        tx["promotion"] = {"promoted_at": now_iso(), "gate_stage": gate_stage, "returncode": proc.returncode, "reason": "post-promote gate failed; automatic rollback complete"}
    else:
        after = dependency.build_index(root)
        tx["status"] = "promoted"
        tx["promotion"] = {
            "promoted_at": now_iso(), "gate_stage": gate_stage, "returncode": 0,
            "dependency_impacts": dependency.compare_indices(tx.get("dependency_index_before") or {}, after),
            "current_hashes": [{"path": row["path"], "sha256": sha(root / row["path"])} for row in tx["files"]],
        }
    atomic(tx_path(root, tx_id), tx)
    return tx


def rollback(root: Path, tx_id: str) -> dict[str, Any]:
    tx = load(root, tx_id)
    _restore(root, tx)
    tx.update({"status": "rolled_back", "rollback": {"rolled_back_at": now_iso(), "reason": "explicit rollback"}})
    atomic(tx_path(root, tx_id), tx)
    return tx


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("start", "status", "verify", "promote", "rollback"))
    parser.add_argument("project_root"); parser.add_argument("transaction_id")
    parser.add_argument("--chapter", default="第1话"); parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--verified-by", default=""); parser.add_argument("--gate-stage", choices=("script", "image_preflight", "image", "compose", "review"), default="review")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv); root = Path(args.project_root).expanduser().resolve()
    try:
        if args.command == "start": result = start(root, args.transaction_id, args.chapter, args.path)
        elif args.command == "verify": result = verify(root, args.transaction_id, args.verified_by)
        elif args.command == "promote": result = promote(root, args.transaction_id, args.gate_stage)
        elif args.command == "rollback": result = rollback(root, args.transaction_id)
        else: result = load(root, args.transaction_id)
    except ValueError as exc:
        print(f"[err] {exc}", file=sys.stderr); return 2
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"{args.command}: {result['status']}")
    return 0 if result["status"] not in {"blocked", "rolled_back"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
