#!/usr/bin/env python3
"""Normalize a NextAction stop into one repair-oriented blocking bundle."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


KIND = "n2d_blocking_bundle"
VERSION = 1


def classify(stop_reason: str, gate: Optional[Mapping[str, Any]] = None) -> str:
    reason = str(stop_reason or "")
    if reason == "done":
        return "complete"
    if reason == "needs_choice":
        return "user_choice"
    if reason == "needs_payment_confirm":
        return "paid_confirmation"
    if reason == "needs_compliance" or "compliance" in reason:
        return "compliance"
    if reason in {"env_missing", "capability_evidence_required"}:
        return "environment_or_adapter"
    if reason in {"needs_acceptance_signoff", "blocked_by_image_qc", "blocked_by_review_acceptance"}:
        return "qc_or_review"
    if (gate or {}).get("blocked") or "gate" in reason or reason.startswith("blocked_by_"):
        return "contract_or_gate"
    if reason in {"prework_failed", "needs_agent_gen", "needs_stage_execution"}:
        return "creative_or_execution"
    return "other"


def safe_slug(value: Any) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", str(value or "全集")).strip("_") or "全集"


def build(payload: Mapping[str, Any], *, graph: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    frontier = payload.get("frontier") if isinstance(payload.get("frontier"), Mapping) else {}
    card = payload.get("action_card") if isinstance(payload.get("action_card"), Mapping) else {}
    gate = payload.get("gate") if isinstance(payload.get("gate"), Mapping) else {}
    stop = str(payload.get("stop_reason") or "unknown")
    commands = [str(x) for x in card.get("commands") or [] if str(x).strip()]
    if card.get("exact_command"):
        commands.insert(0, str(card.get("exact_command")))
    blockers = []
    for row in card.get("blocking_items") or card.get("prework_blocks") or []:
        if isinstance(row, Mapping):
            blockers.append({"step": str(row.get("step") or ""), "message": str(row.get("message") or row.get("detail") or "")})
    if not blockers and stop != "done":
        blockers.append({"step": stop, "message": str(card.get("to_user") or card.get("headline") or stop)})
    return {
        "kind": KIND,
        "version": VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "episode": str(frontier.get("ep") or ""),
        "stage_key": str(frontier.get("stage_key") or ""),
        "owner": str(frontier.get("owner") or ""),
        "stop_reason": stop,
        "category": classify(stop, gate),
        "blocked": stop not in {"done", "needs_agent_gen", "needs_stage_execution"},
        "headline": str(card.get("headline") or ""),
        "blockers": blockers,
        "repair_commands": list(dict.fromkeys(commands)),
        "gate": {
            "stage": str(gate.get("stage") or ""),
            "return_to_stage": gate.get("return_to_stage"),
            "affected_artifacts": list(gate.get("affected_artifacts") or []),
            "findings_path": gate.get("findings_path"),
        },
        "episode_graph": {
            "graph_hash": str((graph or {}).get("graph_hash") or ""),
            "status": str((graph or {}).get("status") or ""),
            "lineage_gaps": int(((graph or {}).get("summary") or {}).get("lineage_gaps") or 0),
        },
        "authority": "repair view only; it does not create a new gate or override existing verdicts",
    }


def write(root: str | Path, bundle: Mapping[str, Any]) -> Dict[str, str]:
    root_path = Path(root)
    episode = safe_slug(bundle.get("episode"))
    stage = safe_slug(bundle.get("stage_key") or "done")
    path = root_path / "生产数据" / "blocking_bundles" / f"blocking_{episode}_{stage}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    latest = path.parent / f"latest_{episode}.json"
    latest_tmp = latest.with_name(f".{latest.name}.tmp.{os.getpid()}")
    latest_tmp.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(latest_tmp, latest)
    return {"json": str(path), "latest": str(latest)}


__all__ = ["KIND", "VERSION", "build", "classify", "safe_slug", "write"]

