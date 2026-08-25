#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-bound dynamic outline deltas for long-form novel production.

The workflow periodically proposes changes only for unwritten chapters.  Safe,
future-only deltas can be applied automatically; changes to author intent,
ending contracts, already-written chapters, or tied evidence remain a human
boundary.  Every application verifies base hashes and emits a receipt.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
NOVEL_LIB = HERE.parents[1] / "_lib"
if str(NOVEL_LIB) not in sys.path:
    sys.path.insert(0, str(NOVEL_LIB))
from store import atomic_write_json, atomic_write_text  # noqa: E402


KIND = "novel_dynamic_outline_delta"
ALLOWED_FILES = {"设定/章纲.md", "设定/scene_cards.json"}
DEFAULT_INTERVAL = 5


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def completed_chapters(root: str | Path) -> list[int]:
    out = []
    for path in glob.glob(str(Path(root) / "章节" / "第*.md")):
        match = re.search(r"第0*(\d+)章", Path(path).name)
        if match:
            out.append(int(match.group(1)))
    return sorted(set(out))


def delta_dir(root: str | Path) -> Path:
    return Path(root) / "设定" / "outline_deltas"


def delta_path(root: str | Path, delta_id: str) -> Path:
    return delta_dir(root) / f"{delta_id}.json"


def _latest_delta(root: str | Path) -> tuple[Path | None, dict[str, Any]]:
    paths = sorted(delta_dir(root).glob("*.json")) if delta_dir(root).is_dir() else []
    if not paths:
        return None, {}
    return paths[-1], _load(paths[-1])


def scaffold(root: str | Path, *, checkpoint: int | None = None, delta_id: str = "") -> dict[str, Any]:
    root_path = Path(root).resolve()
    chapters = completed_chapters(root_path)
    completed = max(chapters, default=0)
    checkpoint = checkpoint or (completed // DEFAULT_INTERVAL) * DEFAULT_INTERVAL
    if checkpoint <= 0:
        raise ValueError("dynamic outline requires at least one completed checkpoint")
    delta_id = delta_id or f"checkpoint_{checkpoint:04d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    bases = []
    for relpath in sorted(ALLOWED_FILES):
        path = root_path / relpath
        bases.append({"path": relpath, "exists": path.is_file(), "sha256": sha256_file(path) if path.is_file() else ""})
    payload = {
        "schema_version": 1,
        "kind": KIND,
        "delta_id": delta_id,
        "created_at": now_iso(),
        "status": "draft",
        "checkpoint_completed_chapters": checkpoint,
        "completed_chapters_at_creation": completed,
        "future_from_chapter": completed + 1,
        "base_files": bases,
        "evidence": [],
        "reason": "",
        "affected_chapters": [],
        "proposed_files": [],
        "touches_author_intent": False,
        "touches_core_ending": False,
        "touches_reader_contract": False,
        "conflicts": [],
    }
    atomic_write_json(delta_path(root_path, delta_id), payload)
    return payload


def evaluate(root: str | Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    root_path = Path(root).resolve()
    issues, human_reasons = [], []
    if payload.get("kind") != KIND:
        issues.append("invalid delta kind")
    proposed = payload.get("proposed_files") if isinstance(payload.get("proposed_files"), list) else []
    if not proposed:
        issues.append("proposed_files is empty")
    seen = set()
    for row in proposed:
        if not isinstance(row, Mapping):
            issues.append("proposed_files contains invalid row")
            continue
        relpath = str(row.get("path") or "")
        if relpath not in ALLOWED_FILES:
            issues.append(f"unsupported proposed file: {relpath}")
        if relpath in seen:
            issues.append(f"duplicate proposed file: {relpath}")
        seen.add(relpath)
        if not isinstance(row.get("content"), str) or not str(row.get("content") or "").strip():
            issues.append(f"proposed content is empty: {relpath}")
        if relpath.endswith(".json"):
            try:
                json.loads(str(row.get("content") or ""))
            except ValueError:
                issues.append(f"proposed JSON is invalid: {relpath}")
    affected = payload.get("affected_chapters") if isinstance(payload.get("affected_chapters"), list) else []
    future_from = int(payload.get("future_from_chapter") or 1)
    if not affected:
        issues.append("affected_chapters is empty")
    elif any(int(chapter) < future_from for chapter in affected):
        human_reasons.append("delta affects an already-written chapter")
    for key, label in (
        ("touches_author_intent", "author intent"),
        ("touches_core_ending", "core ending"),
        ("touches_reader_contract", "reader contract"),
    ):
        if payload.get(key):
            human_reasons.append(f"delta changes {label}")
    conflicts = payload.get("conflicts") if isinstance(payload.get("conflicts"), list) else []
    unresolved = []
    for conflict in conflicts:
        if not isinstance(conflict, Mapping):
            unresolved.append("invalid conflict")
        elif not conflict.get("resolved") or not str(conflict.get("evidence_advantage") or "").strip():
            unresolved.append(str(conflict.get("id") or conflict.get("topic") or "unresolved conflict"))
    if unresolved:
        human_reasons.append("unresolved/tied evidence conflicts: " + ", ".join(unresolved))
    stale = []
    for row in payload.get("base_files") or []:
        if not isinstance(row, Mapping):
            continue
        path = root_path / str(row.get("path") or "")
        actual = sha256_file(path) if path.is_file() else ""
        if actual != str(row.get("sha256") or ""):
            stale.append(str(row.get("path") or ""))
    if stale:
        issues.append("base hash changed: " + ", ".join(stale))
    if issues:
        verdict = "invalid"
    elif human_reasons:
        verdict = "needs_human"
    else:
        verdict = "auto_apply"
    return {
        "verdict": verdict,
        "auto_apply": verdict == "auto_apply",
        "issues": issues,
        "human_reasons": human_reasons,
        "evaluated_at": now_iso(),
    }


def apply_delta(root: str | Path, path: str | Path, *, human_approved_by: str = "") -> dict[str, Any]:
    root_path = Path(root).resolve()
    delta_file = Path(path)
    if not delta_file.is_absolute():
        delta_file = root_path / delta_file
    payload = _load(delta_file)
    evaluation = evaluate(root_path, payload)
    if evaluation["verdict"] == "invalid":
        raise ValueError("; ".join(evaluation["issues"]))
    actor = str(human_approved_by or "").strip()
    if evaluation["verdict"] == "needs_human" and not actor:
        raise ValueError("human approval required: " + "; ".join(evaluation["human_reasons"]))
    delta_id = str(payload.get("delta_id") or delta_file.stem)
    backup_dir = root_path / "生产数据" / "dynamic_outline" / "backups" / delta_id
    outputs = []
    originals: dict[Path, str | None] = {}
    try:
        for row in payload.get("proposed_files") or []:
            relpath = str(row["path"])
            target = root_path / relpath
            originals[target] = target.read_text(encoding="utf-8") if target.is_file() else None
            if target.is_file():
                backup = backup_dir / relpath
                backup.parent.mkdir(parents=True, exist_ok=True)
                atomic_write_text(backup, originals[target] or "")
            atomic_write_text(target, str(row["content"]))
            outputs.append({"path": relpath, "sha256": sha256_file(target)})
    except Exception:
        for target, original in originals.items():
            if original is None:
                if target.exists():
                    os.remove(target)
            else:
                atomic_write_text(target, original)
        raise
    payload["status"] = "applied"
    payload["evaluation"] = evaluation
    payload["applied_at"] = now_iso()
    payload["applied_by"] = actor or "novel-producer:auto"
    payload["applied_outputs"] = outputs
    atomic_write_json(delta_file, payload)
    receipt = {
        "schema_version": 1,
        "kind": "novel_dynamic_outline_application",
        "delta_id": delta_id,
        "applied_at": payload["applied_at"],
        "applied_by": payload["applied_by"],
        "checkpoint_completed_chapters": payload.get("checkpoint_completed_chapters"),
        "delta_path": os.path.relpath(delta_file, root_path).replace(os.sep, "/"),
        "outputs": outputs,
        "backup_dir": os.path.relpath(backup_dir, root_path).replace(os.sep, "/"),
    }
    atomic_write_json(root_path / "生产数据" / "dynamic_outline" / f"apply_{delta_id}.json", receipt)
    return receipt


def workflow_status(root: str | Path, *, interval: int = DEFAULT_INTERVAL) -> dict[str, Any]:
    root_path = Path(root).resolve()
    completed = max(completed_chapters(root_path), default=0)
    checkpoint = (completed // max(1, interval)) * max(1, interval)
    path, payload = _latest_delta(root_path)
    latest_checkpoint = int(payload.get("checkpoint_completed_chapters") or 0) if payload else 0
    if checkpoint <= 0 or checkpoint <= latest_checkpoint and payload.get("status") == "applied":
        phase = "current"
        evaluation = {}
    elif not payload:
        phase = "create_delta"
        evaluation = {}
    elif payload.get("status") != "applied":
        evaluation = evaluate(root_path, payload)
        phase = {
            "invalid": "needs_specialist",
            "auto_apply": "apply_auto",
            "needs_human": "needs_human",
        }[evaluation["verdict"]]
    elif latest_checkpoint < checkpoint:
        phase = "create_delta"
        evaluation = {}
    else:
        evaluation = evaluate(root_path, payload)
        phase = {
            "invalid": "needs_specialist",
            "auto_apply": "apply_auto",
            "needs_human": "needs_human",
        }[evaluation["verdict"]]
    return {
        "phase": phase,
        "completed_chapters": completed,
        "checkpoint": checkpoint,
        "interval": interval,
        "delta_path": os.path.relpath(path, root_path).replace(os.sep, "/") if path else "",
        "delta": payload,
        "evaluation": evaluation,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["scaffold", "evaluate", "apply", "status"])
    ap.add_argument("project_root")
    ap.add_argument("--delta", default="")
    ap.add_argument("--delta-id", default="")
    ap.add_argument("--checkpoint", type=int)
    ap.add_argument("--interval", type=int, default=DEFAULT_INTERVAL)
    ap.add_argument("--human-approved-by", default="")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = str(Path(ns.project_root).resolve())
    try:
        if ns.command == "scaffold":
            result = scaffold(root, checkpoint=ns.checkpoint, delta_id=ns.delta_id)
        elif ns.command == "status":
            result = workflow_status(root, interval=ns.interval)
        else:
            delta = ns.delta
            if not delta:
                latest, _ = _latest_delta(root)
                if latest is None:
                    raise ValueError("no outline delta found")
                delta = str(latest)
            payload = _load(Path(delta) if Path(delta).is_absolute() else Path(root) / delta)
            result = evaluate(root, payload) if ns.command == "evaluate" else apply_delta(
                root, delta, human_approved_by=ns.human_approved_by
            )
    except ValueError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2) if ns.json else f"{ns.command}: {result.get('verdict') or result.get('phase') or result.get('delta_id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
