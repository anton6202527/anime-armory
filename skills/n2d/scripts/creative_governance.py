#!/usr/bin/env python3
"""Creative decision log and crew RACI for n2d."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping


KIND = "n2d_creative_governance"
CHECK_KIND = "n2d_creative_governance_check"
VERSION = 1
DECISIONS = "creative_decisions.jsonl"
RACI = "crew_raci.json"


DEFAULT_RACI = {
    "kind": "n2d_crew_raci",
    "version": VERSION,
    "status": "confirmed",
    "roles": {
        "writer": {
            "responsible": ["source_comprehension", "voiceover", "adaptation_delta", "script_quality_contract"],
            "approves": ["script_lock"],
            "consulted": ["storyboard_lock", "continuity_bible"],
        },
        "director": {
            "responsible": ["director_blocking_pack", "storyboard", "animatic_packet", "shot_progression_plan"],
            "approves": ["storyboard_lock", "rough_cut_lock", "picture_lock"],
            "consulted": ["script_lock", "delivery_lock"],
        },
        "producer": {
            "responsible": ["development_pack", "ai_shooting_schedule", "budget", "batch_governance"],
            "approves": ["source_lock", "script_lock", "storyboard_lock", "delivery_lock"],
            "consulted": ["all_unlocks"],
        },
        "assistant_director": {
            "responsible": ["ai_call_sheet", "ai_shooting_schedule", "batch_queue"],
            "approves": ["shooting_schedule"],
            "consulted": ["picture_lock"],
        },
        "script_supervisor": {
            "responsible": ["continuity_breakdown", "continuity_bible", "entity_schedule", "state_transition_manifest"],
            "approves": ["continuity_bible", "storyboard_lock"],
            "consulted": ["picture_lock", "delivery_lock"],
        },
        "post_supervisor": {
            "responsible": ["rough_cut", "rough_cut_lock", "picture_lock", "sound_mix", "subtitles", "delivery_matrix"],
            "approves": ["rough_cut_lock", "picture_lock", "delivery_lock"],
            "consulted": ["storyboard_lock"],
        },
        "compliance": {
            "responsible": ["rights", "voice_authorization", "platform_review", "localization", "ai_labeling"],
            "approves": ["paid_distribution", "delivery_lock"],
            "consulted": ["source_lock"],
        },
    },
    "unlock_policy": {
        "requires_decision_log": True,
        "requires_affected_artifacts": True,
        "requires_minimal_rerun_scope": True,
        "decision_log": "生产数据/creative_decisions.jsonl",
    },
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    write_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def decisions_path(root: Path) -> Path:
    return production_dir(root) / DECISIONS


def raci_path(root: Path) -> Path:
    return production_dir(root) / RACI


def scaffold(root: Path, *, force: bool = False) -> Dict[str, Any]:
    created: List[str] = []
    dp = decisions_path(root)
    if force or not dp.exists():
        sample = {
            "kind": "n2d_creative_decision",
            "version": VERSION,
            "created_at": now_iso(),
            "decision_type": "template",
            "status": "example",
            "owner": "producer",
            "scope": "replace this sample with real decisions",
            "alternatives_considered": [],
            "accepted_choice": "",
            "reason": "",
            "affected_artifacts": [],
            "affected_stages": [],
            "unlock_of": "",
            "follow_up_batch_scope": "",
        }
        write_atomic(dp, json.dumps(sample, ensure_ascii=False, sort_keys=True) + "\n")
        created.append(str(dp))
    rp = raci_path(root)
    if force or not rp.exists():
        payload = dict(DEFAULT_RACI)
        payload["generated_at"] = now_iso()
        write_json(rp, payload)
        created.append(str(rp))
    return {"kind": KIND, "status": "scaffolded", "created": created}


def _valid_decision(row: Mapping[str, Any]) -> bool:
    if row.get("status") == "example":
        return False
    required = ("decision_type", "owner", "scope", "accepted_choice", "reason")
    return all(str(row.get(k) or "").strip() for k in required)


def _production_ready_decision(row: Mapping[str, Any]) -> bool:
    if not _valid_decision(row):
        return False
    if not isinstance(row.get("affected_artifacts"), list) or not row.get("affected_artifacts"):
        return False
    if not isinstance(row.get("affected_stages"), list) or not row.get("affected_stages"):
        return False
    rerun_scope = (
        row.get("follow_up_batch_scope")
        or row.get("minimal_rerun_scope")
        or row.get("rerun_scope")
    )
    return bool(str(rerun_scope or "").strip())


def _load_decisions(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            rows.append({"_invalid": raw[:120]})
            continue
        rows.append(obj if isinstance(obj, dict) else {"_invalid": raw[:120]})
    return rows


def _jsonl_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def major_change_reasons(root: Path) -> List[str]:
    reasons: List[str] = []
    prod = production_dir(root)
    lock_codes = {"lock_artifact_stale", "lock_artifact_missing", "lock_required_artifact_missing"}
    for path in sorted(prod.glob("production_locks_check_*.json")):
        data = load_json(path)
        for finding in (data.get("findings") if isinstance(data, dict) else []) or []:
            if not isinstance(finding, dict):
                continue
            if finding.get("code") in lock_codes:
                reasons.append(f"production lock change: {finding.get('lock_id') or ''} {finding.get('code')}")
    for row in _jsonl_rows(prod / "production_events.jsonl"):
        if row.get("event") == "waiver":
            meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
            reasons.append(f"dashboard waiver: {row.get('stage') or ''} {meta.get('waiver') or ''}")
    for row in _jsonl_rows(prod / "progress_unverified_waivers.jsonl"):
        reasons.append(f"unverified progress waiver: {row.get('episode') or ''} {row.get('stage') or row.get('col') or ''}")
    for path in sorted(prod.glob("gate_findings_*.json")):
        data = load_json(path)
        findings = data.get("findings") if isinstance(data, dict) else []
        for finding in findings or []:
            if not isinstance(finding, dict):
                continue
            blob = json.dumps(finding, ensure_ascii=False).lower()
            if "waiver" in blob or "降级 qc" in blob or "降级qc" in blob:
                reasons.append(f"gate waiver finding: {path.name}")
                break
    out: List[str] = []
    seen = set()
    for reason in reasons:
        if reason and reason not in seen:
            seen.add(reason)
            out.append(reason)
    return out


def check(root: Path, *, write_missing: bool = False, require_decision: bool = False, reason: str = "") -> Dict[str, Any]:
    if write_missing:
        scaffold(root)
    findings: List[Dict[str, Any]] = []
    dp = decisions_path(root)
    rp = raci_path(root)
    decisions = _load_decisions(dp)
    auto_reasons = major_change_reasons(root)
    effective_require_decision = bool(require_decision or auto_reasons)
    if not dp.exists():
        findings.append({"severity": "block", "code": "missing_decision_log", "message": f"缺 {dp}"})
    valid = [row for row in decisions if _valid_decision(row)]
    production_ready = [row for row in decisions if _production_ready_decision(row)]
    invalid = [row for row in decisions if not _valid_decision(row)]
    if invalid and len(invalid) == len(decisions):
        findings.append({
            "severity": "block" if effective_require_decision else "warn",
            "code": "no_real_decisions" if not effective_require_decision else "decision_required",
            "message": "creative_decisions.jsonl 目前只有模板或无有效决策；生产、解锁、放量或重大改编时必须补真实行。",
        })
    elif effective_require_decision and not production_ready:
        findings.append({
            "severity": "block",
            "code": "decision_scope_incomplete",
            "message": "生产治理要求至少一条真实决策同时写明 affected_artifacts、affected_stages 和 minimal/follow_up rerun scope。",
        })
    if auto_reasons and not production_ready:
        findings.append({
            "severity": "block",
            "code": "major_change_decision_required",
            "message": "检测到重大变更/逃生口，必须先补 creative_decisions.jsonl 决策账。",
            "reasons": auto_reasons[:20],
        })
    raci = load_json(rp)
    if not isinstance(raci, Mapping):
        findings.append({"severity": "block", "code": "missing_raci", "message": f"缺 crew_raci.json 或 JSON 无效：{rp}"})
    elif str(raci.get("status") or "").lower() != "confirmed":
        findings.append({"severity": "block", "code": "raci_not_confirmed", "message": "crew_raci.json status 不是 confirmed"})
    else:
        roles = raci.get("roles") if isinstance(raci.get("roles"), Mapping) else {}
        for role in ("writer", "director", "producer", "assistant_director", "script_supervisor", "post_supervisor", "compliance"):
            if role not in roles:
                findings.append({"severity": "block", "code": "raci_missing_role", "message": f"crew_raci 缺角色 {role}"})
    block = sum(1 for f in findings if f["severity"] == "block")
    payload = {
        "kind": CHECK_KIND,
        "version": VERSION,
        "generated_at": now_iso(),
        "require_decision": effective_require_decision,
        "requested_require_decision": require_decision,
        "required_due_to": reason,
        "auto_required_reasons": auto_reasons,
        "status": "block" if block else ("warn" if findings else "pass"),
        "summary": {
            "block": block,
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
            "decisions": len(valid),
            "production_ready_decisions": len(production_ready),
        },
        "findings": findings,
        "paths": {"decisions": str(dp), "raci": str(rp)},
    }
    out = production_dir(root) / "creative_governance_check.json"
    write_json(out, payload)
    payload["check_path"] = str(out)
    return payload


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    sub = ap.add_subparsers(dest="command", required=True)
    p_scaffold = sub.add_parser("scaffold")
    p_scaffold.add_argument("--force", action="store_true")
    p_check = sub.add_parser("check")
    p_check.add_argument("--write-missing", action="store_true")
    p_check.add_argument("--require-decision", action="store_true", help="block when no production-ready real decision row exists")
    p_check.add_argument("--reason", default="", help="why this check requires a real decision row")
    p_check.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)

    root = Path(ns.root)
    if ns.command == "scaffold":
        payload = scaffold(root, force=ns.force)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    payload = check(root, write_missing=ns.write_missing, require_decision=ns.require_decision, reason=ns.reason)
    print(json.dumps(payload, ensure_ascii=False, indent=2) if ns.json else f"creative governance: {payload['status']}")
    return 0 if payload["status"] != "block" else 1


if __name__ == "__main__":
    raise SystemExit(main())
