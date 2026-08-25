#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bind one revision task to a Story-VCS branch, verification and rollback.

This turns revision advice into a recoverable transaction: start snapshots the
exact chapter/state files, a specialist edits branch copies, verify binds a
named reviewer to candidate hashes, and promote merges only after hash-safe
preflight.  New red mechanical findings trigger automatic rollback.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
NOVEL_LIB = HERE.parents[1] / "_lib"
for path in (HERE, NOVEL_LIB):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
import story_vcs  # noqa: E402
from content_dependency import build_graph, invalidation_plan  # noqa: E402
from store import atomic_write_json  # noqa: E402


KIND = "novel_revision_transaction"
REVIEW_SCRIPT = HERE.parents[1] / "novel-review" / "scripts" / "mechanical_check.py"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def tx_path(root: str | Path, task_id: str) -> Path:
    return Path(root) / "生产数据" / "revision_transactions" / f"{story_vcs.safe_name(task_id)}.json"


def load_transaction(root: str | Path, task_id: str) -> dict[str, Any]:
    payload = _load(tx_path(root, task_id))
    if payload.get("kind") != KIND:
        raise ValueError(f"revision transaction not found: {task_id}")
    return payload


def _task(root: Path, task_id: str) -> dict[str, Any]:
    plan = _load(root / "修订" / "revision_plan.json")
    for task in plan.get("tasks") or []:
        if isinstance(task, dict) and str(task.get("id") or "") == task_id:
            return task
    raise ValueError(f"revision task not found: {task_id}")


def _selected_files(root: Path, task: dict[str, Any]) -> list[str]:
    files = list(story_vcs.CORE_FILES)
    chapter = task.get("chapter")
    if chapter:
        candidates = sorted((root / "章节").glob(f"第{int(chapter):02d}章*.md"))
        if not candidates:
            candidates = sorted((root / "章节").glob(f"第{int(chapter)}章*.md"))
        if candidates:
            files.append(os.path.relpath(candidates[0], root).replace(os.sep, "/"))
    if task.get("tier") == "structure":
        files.extend(["设定/章纲.md", "设定/scene_cards.json", "设定/创作蓝图.md"])
    return [path for path in dict.fromkeys(files) if (root / path).is_file()]


def start(root: str | Path, task_id: str) -> dict[str, Any]:
    root_path = Path(root).resolve()
    task = _task(root_path, task_id)
    if task.get("status") == "superseded":
        raise ValueError("superseded revision task cannot start")
    if task.get("conflict"):
        raise ValueError("unresolved revision conflict requires arbitration before transaction start")
    branch = f"revision_{task_id}"
    files = _selected_files(root_path, task)
    if not files:
        raise ValueError("revision task has no existing files to branch")
    manifest = story_vcs.handle_branch(str(root_path), branch, selected_files=files)
    payload = {
        "schema_version": 1,
        "kind": KIND,
        "task_id": task_id,
        "task": task,
        "branch": manifest["branch"],
        "branch_manifest": os.path.relpath(story_vcs.branch_manifest_path(str(root_path), branch), root_path).replace(os.sep, "/"),
        "created_at": now_iso(),
        "status": "editing",
        "verified_by": "",
        "verification": {},
        "merge_id": "",
    }
    atomic_write_json(tx_path(root_path, task_id), payload)
    return payload


def verify(root: str | Path, task_id: str, *, verified_by: str = "") -> dict[str, Any]:
    root_path = Path(root).resolve()
    tx = load_transaction(root_path, task_id)
    preflight = story_vcs.merge_preflight(str(root_path), tx["branch"])
    changed, content_issues, hashes = [], [], []
    for row in preflight.get("files") or []:
        if row.get("branch_sha256") != row.get("base_sha256"):
            changed.append(row["main_path"])
        branch_path = root_path / row["branch_path"]
        if not branch_path.is_file() or not branch_path.read_text(encoding="utf-8").strip():
            content_issues.append(f"empty candidate: {row['branch_path']}")
        hashes.append({"path": row["branch_path"], "sha256": row.get("branch_sha256")})
    issues = [str(item.get("message") or item) for item in preflight.get("blockers") or []]
    issues.extend(content_issues)
    if not changed:
        issues.append("candidate branch contains no changes")
    actor = str(verified_by or "").strip()
    if not issues and not actor:
        status = "needs_specialist_review"
    elif issues:
        status = "blocked"
    else:
        status = "verified"
    tx["status"] = status
    tx["verified_by"] = actor
    tx["verification"] = {
        "verified_at": now_iso(), "verdict": status, "issues": issues,
        "changed_files": changed, "candidate_hashes": hashes,
        "definition": "verified requires a named specialist and hash-safe, non-empty changed branch files",
    }
    atomic_write_json(tx_path(root_path, task_id), tx)
    return tx


def _mechanical_check(root: Path, chapter: int | None, task_id: str) -> dict[str, Any]:
    out = root / "审稿" / f"mechanical_revision_{story_vcs.safe_name(task_id)}.json"
    argv = [sys.executable, str(REVIEW_SCRIPT), str(root), "--json-out", str(out)]
    if chapter:
        argv.extend(["--range", str(chapter)])
    proc = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    payload = _load(out)
    findings = payload.get("findings") if isinstance(payload.get("findings"), list) else []
    red = [item for item in findings if isinstance(item, dict) and str(item.get("severity") or "") in {"🔴", "blocking", "block"}]
    return {
        "returncode": proc.returncode, "report": os.path.relpath(out, root).replace(os.sep, "/"),
        "red_findings": red, "stdout": (proc.stdout or "")[-2000:], "stderr": (proc.stderr or "")[-2000:],
    }


def _close_plan_task(root: Path, task_id: str, merge_id: str) -> None:
    path = root / "修订" / "revision_plan.json"
    plan = _load(path)
    changed = False
    for task in plan.get("tasks") or []:
        if isinstance(task, dict) and str(task.get("id") or "") == task_id:
            task.update({"status": "completed", "completed_at": now_iso(), "revision_merge_id": merge_id})
            changed = True
    if changed:
        atomic_write_json(path, plan)


def promote(root: str | Path, task_id: str) -> dict[str, Any]:
    root_path = Path(root).resolve()
    tx = load_transaction(root_path, task_id)
    if tx.get("status") != "verified" or not tx.get("verified_by"):
        raise ValueError("transaction must be verified by a named specialist before promote")
    merged = story_vcs.handle_merge(str(root_path), tx["branch"])
    if merged.get("status") != "committed":
        tx["status"] = "blocked"
        tx["merge_preflight"] = merged
        atomic_write_json(tx_path(root_path, task_id), tx)
        return tx
    tx["merge_id"] = merged["merge_id"]
    mechanical = _mechanical_check(root_path, tx.get("task", {}).get("chapter"), task_id)
    tx["mechanical_check"] = mechanical
    if mechanical["returncode"] != 0 or mechanical["red_findings"]:
        tx["rollback"] = story_vcs.handle_rollback(str(root_path), merged["merge_id"])
        tx["status"] = "rolled_back"
        tx["reason"] = "post-merge mechanical gate failed"
    else:
        tx["status"] = "promoted"
        tx["promoted_at"] = now_iso()
        changed_paths = [
            row["main_path"] for row in merged.get("files") or []
            if row.get("branch_sha256") != row.get("base_sha256")
        ]
        graph = build_graph(root_path)
        impact = invalidation_plan(
            graph, changed_paths,
            change_kind="structure" if tx.get("task", {}).get("tier") == "structure" else "semantic",
        )
        atomic_write_json(root_path / "生产数据" / "content_dependency_graph.json", graph)
        atomic_write_json(root_path / "生产数据" / "content_invalidation_plan.json", impact)
        tx["content_invalidation_plan"] = impact
        _close_plan_task(root_path, task_id, merged["merge_id"])
    atomic_write_json(tx_path(root_path, task_id), tx)
    return tx


def rollback(root: str | Path, task_id: str) -> dict[str, Any]:
    root_path = Path(root).resolve()
    tx = load_transaction(root_path, task_id)
    merge_id = str(tx.get("merge_id") or "")
    if not merge_id:
        raise ValueError("transaction has no merge to roll back")
    tx["rollback"] = story_vcs.handle_rollback(str(root_path), merge_id)
    tx["status"] = "rolled_back"
    atomic_write_json(tx_path(root_path, task_id), tx)
    return tx


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["start", "status", "verify", "promote", "rollback"])
    ap.add_argument("project_root")
    ap.add_argument("task_id")
    ap.add_argument("--verified-by", default="")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    try:
        if ns.command == "start":
            result = start(ns.project_root, ns.task_id)
        elif ns.command == "verify":
            result = verify(ns.project_root, ns.task_id, verified_by=ns.verified_by)
        elif ns.command == "promote":
            result = promote(ns.project_root, ns.task_id)
        elif ns.command == "rollback":
            result = rollback(ns.project_root, ns.task_id)
        else:
            result = load_transaction(ns.project_root, ns.task_id)
    except (ValueError, FileNotFoundError) as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2) if ns.json else f"{ns.command}: {result.get('status')}")
    return 0 if result.get("status") not in {"blocked", "rolled_back"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
