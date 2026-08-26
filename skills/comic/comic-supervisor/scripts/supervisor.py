#!/usr/bin/env python3
"""Decide exactly one current Comic action for the durable producer."""
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BATCH = _module("comic_supervisor_batch", REPO / "skills/comic/comic-batch/scripts/run.py")
RELEASE = _module("comic_supervisor_release", REPO / "skills/comic/scripts/release_verdict.py")
SETTINGS = _module("comic_supervisor_settings", REPO / "skills/comic/_lib/settings.py")


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _profile_for(medium: str, usage: str) -> str:
    if usage == "commercial":
        return "commercial"
    elif medium == "print_pdf":
        return "print"
    elif usage == "public":
        return "digital"
    return "internal"


def ensure_active_release_contract(root: Path, chapter: str) -> dict[str, Any]:
    """Bootstrap/refresh the active delivery only from explicit project settings."""
    settings_path = root / "_设置.md"
    if not settings_path.is_file():
        raise ValueError("_设置.md is missing; refusing to assume internal delivery")
    current = SETTINGS.load_settings(str(root))
    missing = [key for key in ("交付介质", "交付用途", "目标平台") if not str(current.get(key) or "").strip()]
    if missing:
        raise ValueError(f"explicit delivery settings are missing: {', '.join(missing)}")
    medium = SETTINGS.normalize_setting_value("交付介质", str(current["交付介质"]))
    usage = SETTINGS.normalize_setting_value("交付用途", str(current["交付用途"]))
    target_platform = str(current["目标平台"]).strip()
    if medium not in RELEASE.MEDIUMS:
        raise ValueError(f"invalid 交付介质: {medium}")
    if usage not in RELEASE.USAGES:
        raise ValueError(f"invalid 交付用途: {usage}")
    settings_binding = {
        "path": "_设置.md", "sha256": RELEASE.sha256_file(settings_path),
        "delivery": {"medium": medium, "usage": usage, "target_platform": target_platform},
    }
    path = root / "生产数据" / f"release_contract_{chapter}.json"
    existing = _load(path)
    if existing and existing.get("kind") != "comic_active_release_contract":
        raise ValueError("existing release_contract kind is invalid")
    if existing:
        old_medium = str(existing.get("medium") or "")
        old_usage = str(existing.get("usage") or "")
        if old_medium and old_medium not in RELEASE.MEDIUMS:
            raise ValueError(f"active release contract has invalid medium: {old_medium}")
        if old_usage and old_usage not in RELEASE.USAGES:
            raise ValueError(f"active release contract has invalid usage: {old_usage}")
    axes_changed = bool(existing) and (
        str(existing.get("medium") or "") != medium
        or str(existing.get("usage") or "") != usage
        or str(existing.get("target_platform") or "") != target_platform
    )
    if not existing or axes_changed:
        contract = {
            "schema_version": 2, "kind": "comic_active_release_contract", "chapter": chapter,
            "medium": medium, "usage": usage, "target_platform": target_platform,
            "settings_binding": settings_binding, "release_digest": "", "bundle_path": "",
            "bundle_sha256": "", "bootstrap_status": "awaiting_release_verdict",
            "bootstrapped_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "previous_release_digest": str(existing.get("release_digest") or "") if existing else "",
            "definition": "single active delivery bootstrapped from explicit _设置.md; no completion claim until an immutable digest bundle is activated",
        }
        RELEASE.atomic_json(path, contract)
        return contract
    if existing.get("settings_binding") != settings_binding:
        existing["schema_version"] = 2
        existing["settings_binding"] = settings_binding
        existing["settings_observed_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        RELEASE.atomic_json(path, existing)
    return existing


def _active_axes(root: Path, chapter: str) -> tuple[str, str, str]:
    contract = ensure_active_release_contract(root, chapter)
    medium = str(contract.get("medium") or "")
    usage = str(contract.get("usage") or "")
    return _profile_for(medium, usage), medium, usage


def decide_next_action(project_root: str | Path, chapter: str = "第1话") -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    try:
        profile, medium, usage = _active_axes(root, chapter)
    except ValueError as exc:
        return {
            "status": "blocked", "action": "invalid_active_delivery_settings",
            "next_stage": "发布合同", "agent_role": "workflow_orchestrator",
            "hard_boundary": True, "reason": str(exc),
            "issues": [{"code": "invalid_active_delivery_settings", "reason": str(exc), "blocks_active_delivery": True}],
        }
    action = BATCH.next_action(root, chapter)
    if action.get("action") != "build_completion_verdict":
        return action
    report = RELEASE.build(root, chapter, profile, medium=medium, usage=usage)
    completion = RELEASE.build_completion_verdict(root, report)
    verification = RELEASE.verify_stored_completion(root, chapter)
    stored = verification.get("completion") if isinstance(verification.get("completion"), Mapping) else {}
    if (
        verification.get("current") is not True
        or str(verification.get("release_digest") or "") != str(completion.get("release_digest") or "")
        or stored.get("status") != completion.get("status")
    ):
        return {
            **action, "status": "runnable", "action": "refresh_active_release_verdict",
            "recommended_commands": [
                f'python3 skills/comic/scripts/release_verdict.py "{root}" {chapter} '
                f'--profile {profile} --medium {medium} --usage {usage} --write'
            ],
            "hard_boundary": False,
            "completion_current": False,
            "completion_issues": verification.get("issues") or [],
        }
    current_completion = dict(stored)
    if current_completion["status"] == "accepted":
        return {
            **action, "status": "complete", "action": "complete",
            "completion": current_completion, "completion_current": True,
        }
    if current_completion["status"] == "machine_ready":
        return {
            **action, "status": "needs_human", "action": "final_acceptance",
            "agent_role": "final_acceptor", "hard_boundary": True,
            "completion": current_completion,
            "reason": "only a named non-delegate final acceptance may promote machine_ready to accepted",
        }
    hard_domains = {"rights", "release"}
    hard = [row for row in report.get("issues") or [] if row.get("blocks_active_delivery") and row.get("domain") in hard_domains]
    if hard:
        return {
            **action, "status": "blocked", "action": "rights_or_release_boundary",
            "hard_boundary": True, "issues": hard, "completion": current_completion,
        }
    return {
        **action, "status": "specialist_required", "action": "repair_release_blockers",
        "agent_role": "quality_editor", "hard_boundary": False,
        "issues": [row for row in report.get("issues") or [] if row.get("blocks_active_delivery")],
        "completion": current_completion,
    }
