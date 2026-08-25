#!/usr/bin/env python3
"""Decide exactly one current Comic action for the durable producer."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BATCH = _module("comic_supervisor_batch", REPO / "skills/comic/comic-batch/scripts/run.py")
RELEASE = _module("comic_supervisor_release", REPO / "skills/comic/scripts/release_verdict.py")


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _active_axes(root: Path, chapter: str) -> tuple[str, str, str]:
    contract = _load(root / "生产数据" / f"release_contract_{chapter}.json")
    medium = str(contract.get("medium") or "web_images")
    usage = str(contract.get("usage") or "internal")
    if usage == "commercial":
        profile = "commercial"
    elif medium == "print_pdf":
        profile = "print"
    elif usage == "public":
        profile = "digital"
    else:
        profile = "internal"
    return profile, medium, usage


def decide_next_action(project_root: str | Path, chapter: str = "第1话") -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    action = BATCH.next_action(root, chapter)
    if action.get("action") != "build_completion_verdict":
        return action
    profile, medium, usage = _active_axes(root, chapter)
    report = RELEASE.build(root, chapter, profile, medium=medium, usage=usage)
    completion = RELEASE.build_completion_verdict(root, report)
    stored = _load(root / "生产数据" / f"completion_verdict_{chapter}.json")
    if stored.get("release_digest") != completion.get("release_digest") or stored.get("status") != completion.get("status"):
        return {
            **action, "status": "runnable", "action": "refresh_active_release_verdict",
            "recommended_commands": [
                f'python3 skills/comic/scripts/release_verdict.py "{root}" {chapter} '
                f'--profile {profile} --medium {medium} --usage {usage} --write'
            ],
            "hard_boundary": False,
        }
    if completion["status"] == "accepted":
        return {**action, "status": "complete", "action": "complete", "completion": completion}
    if completion["status"] == "machine_ready":
        return {
            **action, "status": "needs_human", "action": "final_acceptance",
            "agent_role": "final_acceptor", "hard_boundary": True,
            "completion": completion,
            "reason": "only a named non-delegate final acceptance may promote machine_ready to accepted",
        }
    hard_domains = {"rights", "release"}
    hard = [row for row in report.get("issues") or [] if row.get("blocks_active_delivery") and row.get("domain") in hard_domains]
    if hard:
        return {
            **action, "status": "blocked", "action": "rights_or_release_boundary",
            "hard_boundary": True, "issues": hard, "completion": completion,
        }
    return {
        **action, "status": "specialist_required", "action": "repair_release_blockers",
        "agent_role": "quality_editor", "hard_boundary": False,
        "issues": [row for row in report.get("issues") or [] if row.get("blocks_active_delivery")],
        "completion": completion,
    }
