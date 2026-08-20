#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a release manifest for exported novel artifacts."""
from __future__ import annotations

import argparse
import glob
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
NOVEL_LIB = os.path.abspath(os.path.join(HERE, "..", "..", "_lib"))
if NOVEL_LIB not in sys.path:
    sys.path.insert(0, NOVEL_LIB)

from qa_gate import collect_gate_status  # noqa: E402
from authenticity_contract import evaluate_authenticity_read  # noqa: E402
from report_snapshot import snapshot_chapters, validate_snapshot  # noqa: E402
from waivers import has_waiver, load_waivers  # noqa: E402
try:
    from provenance import append_event  # noqa: E402
except Exception:  # pragma: no cover - provenance is additive
    append_event = None


def _load_compliance_lib():
    path = os.path.join(NOVEL_LIB, "compliance_profile.py")
    spec = importlib.util.spec_from_file_location("novel_compliance_profile_for_release", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MANIFEST_KIND = "novel_release_manifest"
DEFAULT_RELEASE_PROFILE = "platform_publish"
RELEASE_PROFILES: dict[str, dict[str, Any]] = {
    "internal_draft": {
        "label": "Internal draft",
        "require_exports": False,
        "mandatory_evidence": (),
        "snapshot_block": (),
        "snapshot_warn": ("review_report", "score_report"),
        "ai_usage_block": False,
        "compliance_fingerprint_block": False,
        "qa_gate": None,
        "research_missing": "ignore",
        "reader_plan_required": False,
        "reader_telemetry_missing": "ignore",
    },
    "beta_read": {
        "label": "Beta reader package",
        "require_exports": True,
        "mandatory_evidence": ("review_report", "ai_usage", "reader_test_plan"),
        "snapshot_block": ("review_report",),
        "snapshot_warn": ("score_report",),
        "ai_usage_block": True,
        "compliance_fingerprint_block": False,
        "qa_gate": {"require_review_report": True, "require_score_report": False, "require_state_closure": False},
        "research_missing": "warn",
        "reader_plan_required": True,
        "reader_telemetry_missing": "warn",
    },
    "platform_publish": {
        "label": "Platform publish",
        "require_exports": True,
        "mandatory_evidence": ("review_report", "ai_usage", "compliance_profile", "metadata_pack"),
        "snapshot_block": ("review_report", "score_report"),
        "snapshot_warn": (),
        "ai_usage_block": True,
        "compliance_fingerprint_block": True,
        "qa_gate": {"require_review_report": True, "require_score_report": True, "require_state_closure": True},
        "research_missing": "warn",
        "reader_plan_required": False,
        "reader_telemetry_missing": "warn",
    },
    "kdp_publish": {
        "label": "Amazon KDP publish",
        "require_exports": True,
        "mandatory_evidence": ("review_report", "ai_usage", "compliance_profile", "metadata_pack"),
        "snapshot_block": ("review_report",),
        "snapshot_warn": ("score_report",),
        "ai_usage_block": True,
        "compliance_fingerprint_block": True,
        "qa_gate": {"require_review_report": True, "require_score_report": False, "require_state_closure": True},
        "research_missing": "warn",
        "reader_plan_required": False,
        "reader_telemetry_missing": "warn",
        "kdp": True,
    },
    "data_validated_launch": {
        "label": "Data-validated platform launch",
        "require_exports": True,
        "mandatory_evidence": ("review_report", "ai_usage", "compliance_profile", "reader_test_plan", "metadata_pack"),
        "snapshot_block": ("review_report", "score_report"),
        "snapshot_warn": (),
        "ai_usage_block": True,
        "compliance_fingerprint_block": True,
        "qa_gate": {"require_review_report": True, "require_score_report": True, "require_state_closure": True},
        "research_missing": "warn",
        "reader_plan_required": True,
        "reader_telemetry_missing": "block",
    },
    "archive": {
        "label": "Archive snapshot",
        "require_exports": False,
        "mandatory_evidence": (),
        "snapshot_block": (),
        "snapshot_warn": ("review_report", "score_report"),
        "ai_usage_block": False,
        "compliance_fingerprint_block": False,
        "qa_gate": None,
        "research_missing": "ignore",
        "reader_plan_required": False,
        "reader_telemetry_missing": "ignore",
    },
}


def release_profile_config(profile: str) -> dict[str, Any]:
    if profile not in RELEASE_PROFILES:
        raise ValueError(f"unsupported release profile: {profile}")
    return RELEASE_PROFILES[profile]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def file_record(root: str, path: str) -> dict[str, Any]:
    return {
        "path": rel(root, path),
        "sha256": sha256_file(path),
        "size_bytes": os.path.getsize(path),
        "mtime": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds"),
    }


def optional_record(root: str, relpath: str) -> dict[str, Any]:
    path = os.path.join(root, relpath)
    if not os.path.exists(path):
        return {"path": relpath, "exists": False}
    return {"exists": True, **file_record(root, path)}


def evidence_index_record(root: str, path: str, *, source: str, purpose: str) -> dict[str, Any]:
    return {
        **file_record(root, path),
        "source": source,
        "purpose": purpose,
    }


def build_evidence_index(
    root: str,
    *,
    chapters: list[dict[str, Any]],
    exports: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_path(relpath: str, source: str, purpose: str) -> None:
        if not relpath or relpath in seen:
            return
        path = os.path.join(root, relpath)
        if not os.path.isfile(path):
            return
        seen.add(relpath)
        records.append(evidence_index_record(root, path, source=source, purpose=purpose))

    for chapter in chapters:
        add_path(str(chapter.get("path") or ""), "chapters", "canonical chapter source included in release")
    for export in exports:
        add_path(str(export.get("path") or ""), "exports", "release export artifact")
    evidence_purposes = {
        "review_report": "review gate evidence and blocker summary",
        "score_report": "market/quality score and production decision",
        "ai_usage": "AI usage disclosure and human contribution evidence",
        "compliance_profile": "release jurisdiction/platform compliance profile",
        "research_sources": "research source ledger for specialist factual claims",
        "revision_plan": "editorial revision task ledger",
        "authenticity_read": "author-controlled authenticity/cultural read and decision ledger",
        "waiver_log": "explicit waiver audit trail",
        "reader_test_plan": "reader validation plan for beta or publish decisions",
        "reader_telemetry_summary": "real reader telemetry summary and drop-off evidence",
        "metadata_pack": "publishing metadata: blurb, categories, keywords, age/content notes",
    }
    for key, record in evidence.items():
        if isinstance(record, dict) and record.get("exists"):
            add_path(str(record.get("path") or ""), key, evidence_purposes.get(key, "release evidence"))
    extra_patterns = [
        ("评分/market_baseline_*.json", "market_baseline", "current market baseline JSON used by score"),
        ("评分/题材热榜_*.md", "market_baseline", "human-readable market baseline/rank evidence"),
        ("评分/market_evidence_jobs.json", "market_evidence_jobs", "pending market evidence search jobs"),
        ("评分/读者测试计划.md", "reader_test_plan", "human-readable reader validation plan"),
        ("评分/真实读者反馈_*.md", "reader_telemetry_summary", "human-readable reader feedback report"),
        ("导出/metadata_pack.md", "metadata_pack", "human-readable publishing metadata"),
        ("资料/专业资料包_*.md", "research_pack", "specialist research packet"),
        ("资料/research_sources.json", "research_sources", "research source ledger for specialist factual claims"),
        ("审稿/review_board.json", "review_board", "editorial arbitration board"),
        ("修订/authenticity_read.md", "authenticity_read", "human-readable authenticity/cultural read"),
        ("修订/authenticity_read_check.json", "authenticity_read", "authenticity read workflow check"),
        ("合规/platform_ai_evidence.json", "platform_ai_evidence", "platform AI policy evidence for text mode exception"),
    ]
    for pattern, source, purpose in extra_patterns:
        for path in sorted(glob.glob(os.path.join(root, pattern))):
            add_path(rel(root, path), source, purpose)
    return records


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def aggregate_hash(records: list[dict[str, Any]]) -> str:
    h = hashlib.sha256()
    for record in sorted(records, key=lambda item: item.get("path", "")):
        h.update(str(record.get("path") or "").encode("utf-8"))
        h.update(str(record.get("sha256") or "").encode("utf-8"))
    return h.hexdigest()


def export_formats(exports: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for record in exports:
        ext = os.path.splitext(str(record.get("path") or ""))[1].lstrip(".").lower()
        if ext and ext not in out:
            out.append(ext)
    return out


def check_snapshot(root: str, evidence_key: str, relpath: str) -> dict[str, Any]:
    path = os.path.join(root, relpath)
    payload = load_json(path, {}) or {}
    ok, message = validate_snapshot(root, payload.get("source_snapshot"))
    return {
        "id": f"{evidence_key}_source_snapshot",
        "evidence": evidence_key,
        "path": relpath,
        "passed": ok,
        "message": message,
        "aggregate_hash": (payload.get("source_snapshot") or {}).get("aggregate_hash") if isinstance(payload, dict) else "",
    }


def ai_usage_check(root: str) -> dict[str, Any]:
    relpath = "合规/ai_usage.json"
    payload = load_json(os.path.join(root, relpath), {}) or {}
    issues = []
    text_mode = payload.get("text_mode") if isinstance(payload, dict) else ""
    if text_mode in {"AI-generated", "AI-assisted"}:
        if not str(payload.get("human_contribution") or "").strip():
            issues.append("AI-generated/AI-assisted text requires human_contribution")
        detail = payload.get("disclosure_detail") if isinstance(payload.get("disclosure_detail"), dict) else {}
        if not detail.get("review_steps"):
            issues.append("AI usage disclosure should record review_steps before release")
        chapter_usage = payload.get("chapter_usage") if isinstance(payload.get("chapter_usage"), list) else []
        if not chapter_usage:
            issues.append("AI usage disclosure should record chapter_usage for each released chapter")
        else:
            for row in chapter_usage:
                if not isinstance(row, dict):
                    issues.append("AI usage chapter_usage contains invalid row")
                    continue
                if not row.get("chapter") or not row.get("usage_mode"):
                    issues.append("AI usage chapter_usage rows require chapter and usage_mode")
                    break
    return {
        "id": "ai_usage_release_disclosure",
        "evidence": "ai_usage",
        "path": relpath,
        "passed": not issues,
        "message": "; ".join(issues) if issues else "AI usage disclosure has release-facing detail",
    }


def compliance_fingerprint_check(root: str) -> dict[str, Any]:
    relpath = "合规/compliance_profile.json"
    stored = load_json(os.path.join(root, relpath), {}) or {}
    if not isinstance(stored, dict) or not stored:
        return {
            "id": "compliance_profile_input_fingerprint",
            "evidence": "compliance_profile",
            "path": relpath,
            "passed": False,
            "message": "compliance_profile.json is missing or invalid",
            "stored_input_fingerprint": "",
            "current_input_fingerprint": "",
        }
    stored_fingerprint = str(stored.get("input_fingerprint") or "")
    if not stored_fingerprint:
        return {
            "id": "compliance_profile_input_fingerprint",
            "evidence": "compliance_profile",
            "path": relpath,
            "passed": False,
            "message": "compliance_profile lacks input_fingerprint; rerun compliance_profile.py --write",
            "stored_input_fingerprint": "",
            "current_input_fingerprint": "",
        }
    lib = _load_compliance_lib()
    if lib is None:
        return {
            "id": "compliance_profile_input_fingerprint",
            "evidence": "compliance_profile",
            "path": relpath,
            "passed": False,
            "message": "cannot load compliance profile library to verify fingerprint",
            "stored_input_fingerprint": stored_fingerprint,
            "current_input_fingerprint": "",
        }
    current = lib.build_profile(root)
    current_fingerprint = str(current.get("input_fingerprint") or "")
    passed = stored_fingerprint == current_fingerprint
    return {
        "id": "compliance_profile_input_fingerprint",
        "evidence": "compliance_profile",
        "path": relpath,
        "passed": passed,
        "message": "compliance_profile fingerprint fresh" if passed else "compliance_profile fingerprint is stale; rerun compliance_profile.py --write",
        "stored_input_fingerprint": stored_fingerprint,
        "current_input_fingerprint": current_fingerprint,
        "stored_components": stored.get("input_fingerprint_components") if isinstance(stored.get("input_fingerprint_components"), dict) else {},
        "current_components": current.get("input_fingerprint_components") if isinstance(current.get("input_fingerprint_components"), dict) else {},
    }


def reader_plan_check(root: str) -> dict[str, Any]:
    relpath = "评分/reader_test_plan.json"
    payload = load_json(os.path.join(root, relpath), {}) or {}
    issues = []
    if not isinstance(payload, dict) or not payload:
        issues.append("reader_test_plan.json is missing or invalid")
    else:
        if payload.get("kind") != "novel_reader_test_plan":
            issues.append("reader_test_plan kind should be novel_reader_test_plan")
        if not payload.get("scope"):
            issues.append("reader test plan lacks scope")
        if not payload.get("target_reader"):
            issues.append("reader test plan lacks target_reader")
        if not payload.get("variants"):
            issues.append("reader test plan lacks variants/takes")
        if not payload.get("cohorts"):
            issues.append("reader test plan lacks cohorts/sample definition")
        if not payload.get("experiment_design"):
            issues.append("reader test plan lacks experiment_design")
        if not payload.get("data_collection_fields"):
            issues.append("reader test plan lacks data_collection_fields")
        if not payload.get("privacy_note"):
            issues.append("reader test plan lacks privacy_note")
        required_attribution = set(payload.get("attribution_required_fields") or [])
        if not {"ab_test_id", "variant_id", "take_id"} <= required_attribution:
            issues.append("reader test plan lacks required attribution fields ab_test_id/variant_id/take_id")
        if not payload.get("metrics"):
            issues.append("reader test plan lacks metrics")
        min_sample = payload.get("min_sample")
        try:
            if int(min_sample) < 10:
                issues.append("reader test min_sample is below 10; publish decisions need a meaningful sample")
        except (TypeError, ValueError):
            issues.append("reader test plan lacks numeric min_sample")
    return {
        "id": "reader_test_plan_quality",
        "evidence": "reader_test_plan",
        "path": relpath,
        "passed": not issues,
        "message": "; ".join(issues) if issues else "reader test plan is usable",
    }


def reader_telemetry_check(root: str) -> dict[str, Any]:
    relpath = "评分/reader_telemetry_summary.json"
    payload = load_json(os.path.join(root, relpath), {}) or {}
    issues = []
    if not isinstance(payload, dict) or not payload:
        issues.append("reader_telemetry_summary.json is missing")
    else:
        if payload.get("kind") != "novel_reader_telemetry_summary":
            issues.append("reader telemetry summary kind should be novel_reader_telemetry_summary")
        aggregate = payload.get("aggregate") if isinstance(payload.get("aggregate"), dict) else {}
        if not aggregate.get("total_starts"):
            issues.append("reader telemetry has no starts/views; use as qualitative evidence only")
        if (payload.get("reader_test_plan") or {}).get("present") is False:
            issues.append("reader telemetry was ingested without a matching reader_test_plan")
        experiments = payload.get("experiments") if isinstance(payload.get("experiments"), dict) else {}
        has_group_attribution = bool(experiments.get("groups") or experiments.get("best_by_ab_test"))
        has_take_hint = bool(payload.get("take_id") or payload.get("variant_id") or payload.get("ab_test_id"))
        if not has_group_attribution and not has_take_hint:
            issues.append("reader telemetry lacks take_id/variant_id/ab_test_id attribution; use for drop-off observation, not version-level causality")
    return {
        "id": "reader_telemetry_summary_quality",
        "evidence": "reader_telemetry_summary",
        "path": relpath,
        "passed": not issues,
        "message": "; ".join(issues) if issues else "reader telemetry summary is usable",
    }


def metadata_pack_check(root: str) -> dict[str, Any]:
    relpath = "导出/metadata_pack.json"
    payload = load_json(os.path.join(root, relpath), {}) or {}
    issues = []
    if not isinstance(payload, dict) or payload.get("kind") != "novel_metadata_pack":
        issues.append("metadata_pack.json is missing or kind should be novel_metadata_pack")
    else:
        if not str(payload.get("title") or "").strip():
            issues.append("metadata pack lacks title")
        if not str(payload.get("short_blurb") or "").strip():
            issues.append("metadata pack lacks short_blurb")
        if not payload.get("categories"):
            issues.append("metadata pack lacks categories")
        if len(payload.get("keywords") or []) < 3:
            issues.append("metadata pack should contain at least 3 keywords")
        rights = payload.get("rights_summary") if isinstance(payload.get("rights_summary"), dict) else {}
        if rights.get("rights_status") in {"unknown", "", None}:
            issues.append("metadata pack rights_status is unknown")
    return {
        "id": "metadata_pack_quality",
        "evidence": "metadata_pack",
        "path": relpath,
        "passed": not issues,
        "message": "; ".join(issues) if issues else "metadata pack is publish-ready",
    }


def has_reader_telemetry_waiver(root: str, release_profile: str) -> bool:
    waivers = load_waivers(root)
    scope = {"release_profile": release_profile}
    return (
        has_waiver(waivers, "reader_telemetry_missing", scope)
        or has_waiver(waivers, "reader_data_missing", scope)
    )


def authenticity_read_check(root: str) -> dict[str, Any]:
    """Validate only the opted-in workflow, never the author's portrayal."""
    relpath = "修订/authenticity_read.json"
    report = evaluate_authenticity_read(root)
    issues = [str(item.get("message") or "") for item in report.get("findings") or []]
    return {
        "id": "authenticity_read",
        "evidence": "authenticity_read",
        "path": relpath,
        "required_for_release": bool(report.get("required_for_release")),
        "passed": not issues,
        "gate_passed": bool(report.get("passed")),
        "blocking": report.get("blocking", 0),
        "warnings": report.get("warnings", 0),
        "message": "; ".join(issues) if issues else "authenticity read workflow is complete and current",
        "scope_note": "checks scope/version/decision closure only; it does not judge creative acceptability",
    }


def _is_kdp_declared(root: str, ai_usage: dict[str, Any], compliance: dict[str, Any]) -> bool:
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    axes = compliance.get("target_axes") if isinstance(compliance, dict) else {}
    axes = axes if isinstance(axes, dict) else {}
    text = " ".join([
        str(meta.get("target_platform") or ""),
        str(meta.get("target") or ""),
        str(meta.get("purpose") or ""),
        str(ai_usage.get("publish_target") or "") if isinstance(ai_usage, dict) else "",
        str(axes.get("raw_target_text") or ""),
    ]).lower()
    return any(key in text for key in ("kdp", "kindle", "amazon")) or bool(axes.get("kdp"))


def _compliance_blocking_requirements(compliance: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for req in compliance.get("requirements") or []:
        if not isinstance(req, dict):
            continue
        if req.get("severity") == "blocking" and req.get("status") in {"missing", "action_required"}:
            out.append(req)
    return out


def release_readiness(
    root: str,
    evidence: dict[str, Any],
    chapters: list[dict[str, Any]],
    exports: list[dict[str, Any]],
    *,
    release_profile: str = DEFAULT_RELEASE_PROFILE,
) -> dict[str, Any]:
    config = release_profile_config(release_profile)
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    def block(check_id: str, message: str, *, path: str = "") -> None:
        blockers.append({"id": check_id, "message": message, "path": path})

    def warn(check_id: str, message: str, *, path: str = "") -> None:
        warnings.append({"id": check_id, "message": message, "path": path})

    if not chapters:
        block("RELEASE-CHAPTERS-MISSING", "release manifest requires at least one chapter")
    if not exports and config.get("require_exports"):
        block("RELEASE-EXPORTS-MISSING", "release manifest requires at least one exported artifact")
    elif not exports:
        warn("RELEASE-EXPORTS-NOT-DECLARED", "no exported artifact recorded for this archive-style manifest")

    for key in config.get("mandatory_evidence") or ():
        record = evidence.get(key) or {}
        if not record.get("exists"):
            block(f"RELEASE-{key.upper()}-MISSING", f"missing required release evidence: {key}", path=record.get("path") or "")

    for key, relpath in (("review_report", "审稿/review_report.json"), ("score_report", "评分/score_report.json")):
        if (evidence.get(key) or {}).get("exists"):
            check = check_snapshot(root, key, relpath)
            checks.append(check)
            if not check["passed"] and key in config.get("snapshot_block", ()):
                block(f"RELEASE-{key.upper()}-STALE", check["message"], path=relpath)
            elif not check["passed"] and key in config.get("snapshot_warn", ()):
                warn(f"RELEASE-{key.upper()}-STALE", check["message"], path=relpath)

    if (evidence.get("ai_usage") or {}).get("exists"):
        check = ai_usage_check(root)
        checks.append(check)
        if not check["passed"] and config.get("ai_usage_block"):
            block("RELEASE-AI-USAGE-DETAIL", check["message"], path=check["path"])
        elif not check["passed"]:
            warn("RELEASE-AI-USAGE-DETAIL", check["message"], path=check["path"])

    if (evidence.get("compliance_profile") or {}).get("exists"):
        check = compliance_fingerprint_check(root)
        checks.append(check)
        if not check["passed"] and config.get("compliance_fingerprint_block"):
            block("RELEASE-COMPLIANCE-FINGERPRINT-STALE", check["message"], path=check["path"])
        elif not check["passed"]:
            warn("RELEASE-COMPLIANCE-FINGERPRINT-STALE", check["message"], path=check["path"])

    if (evidence.get("reader_test_plan") or {}).get("exists"):
        check = reader_plan_check(root)
        checks.append(check)
        if not check["passed"] and config.get("reader_plan_required"):
            block("RELEASE-READER-TEST-PLAN-QUALITY", check["message"], path=check["path"])
        elif not check["passed"]:
            warn("RELEASE-READER-TEST-PLAN-QUALITY", check["message"], path=check["path"])
    if (evidence.get("reader_telemetry_summary") or {}).get("exists"):
        check = reader_telemetry_check(root)
        checks.append(check)
        if not check["passed"]:
            if config.get("reader_telemetry_missing") == "block":
                block("RELEASE-READER-TELEMETRY-QUALITY", check["message"], path=check["path"])
            else:
                warn("RELEASE-READER-TELEMETRY-QUALITY", check["message"], path=check["path"])
    else:
        telemetry_policy = config.get("reader_telemetry_missing")
        if telemetry_policy in {"warn", "block"}:
            if has_reader_telemetry_waiver(root, release_profile):
                warn(
                    "RELEASE-READER-TELEMETRY-WAIVED",
                    "reader telemetry is missing, but a scoped reader-data waiver is recorded for this release profile",
                    path="审稿/waiver_log.jsonl",
                )
            elif telemetry_policy == "block":
                block(
                    "RELEASE-READER-TELEMETRY-NOT-DECLARED",
                    "data_validated_launch requires real reader telemetry or a scoped reader-data waiver",
                    path="评分/reader_telemetry_summary.json",
                )
            else:
                warn(
                    "RELEASE-READER-TELEMETRY-NOT-DECLARED",
                    "no reader_telemetry_summary.json found; this is market-validation evidence, not a publication-compliance prerequisite",
                    path="评分/reader_telemetry_summary.json",
                )

    if (evidence.get("metadata_pack") or {}).get("exists"):
        check = metadata_pack_check(root)
        checks.append(check)
        if not check["passed"] and release_profile in {"platform_publish", "kdp_publish", "data_validated_launch"}:
            block("RELEASE-METADATA-PACK-QUALITY", check["message"], path=check["path"])
        elif not check["passed"]:
            warn("RELEASE-METADATA-PACK-QUALITY", check["message"], path=check["path"])

    if (evidence.get("authenticity_read") or {}).get("exists"):
        check = authenticity_read_check(root)
        checks.append(check)
        if not check["passed"] and check.get("required_for_release"):
            block("RELEASE-AUTHENTICITY-READ", check["message"], path=check["path"])
        elif not check["passed"]:
            warn(
                "RELEASE-AUTHENTICITY-READ",
                check["message"] + "; optional consultancy does not block release",
                path=check["path"],
            )

    gate_payload: dict[str, Any] = {"blocking": False, "blocker_count": 0, "warning_count": 0, "profile_skipped": True}
    if config.get("qa_gate"):
        formats = export_formats(exports) or ["txt"]
        gate_args = dict(config["qa_gate"])
        gate = collect_gate_status(root, export_formats=formats, **gate_args)
        gate_payload = {
            "blocking": gate.get("blocking"),
            "blocker_count": len(gate.get("blockers") or []),
            "warning_count": len(gate.get("warnings") or []),
            "profile_skipped": False,
        }
        for item in gate.get("blockers") or []:
            block(f"QA-{item.get('id') or 'BLOCK'}", item.get("reason") or "QA gate blocker", path=item.get("path") or "")
        for item in gate.get("warnings") or []:
            warn(f"QA-{item.get('id') or 'WARN'}", item.get("reason") or "QA gate warning", path=item.get("path") or "")

    ai_usage = load_json(os.path.join(root, "合规", "ai_usage.json"), {}) or {}
    compliance = load_json(os.path.join(root, "合规", "compliance_profile.json"), {}) or {}
    if config.get("kdp"):
        if not _is_kdp_declared(root, ai_usage, compliance):
            block("RELEASE-KDP-TARGET-MISSING", "kdp_publish profile requires KDP/Kindle/Amazon target intent in meta, AI usage, or compliance profile")
        for req in _compliance_blocking_requirements(compliance):
            block(f"RELEASE-KDP-{str(req.get('id') or 'COMPLIANCE').upper()}", req.get("reason") or "KDP compliance requirement is unresolved", path="合规/compliance_profile.json")

    if not (evidence.get("research_sources") or {}).get("exists"):
        if config.get("research_missing") == "block":
            block("RELEASE-RESEARCH-NOT-DECLARED", "no research_sources.json found for this release profile")
        elif config.get("research_missing") == "warn":
            warn("RELEASE-RESEARCH-NOT-DECLARED", "no research_sources.json found; acceptable only if this project has no specialist factual domains")

    return {
        "release_profile": release_profile,
        "profile_label": config.get("label"),
        "passed": not blockers,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "blockers": blockers,
        "warnings": warnings,
        "checks": checks,
        "qa_gate": gate_payload,
    }


def build_manifest(root: str, *, release_name: str = "", release_profile: str = DEFAULT_RELEASE_PROFILE) -> dict[str, Any]:
    root = os.path.abspath(root)
    config = release_profile_config(release_profile)
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    chapters = [file_record(root, path) for path in sorted(glob.glob(os.path.join(root, "章节", "第*.md")))]
    exports = [
        file_record(root, path)
        for path in sorted(glob.glob(os.path.join(root, "导出", "*")))
        if os.path.isfile(path) and not path.endswith(("release_manifest.json", "release_manifest.md"))
    ]
    evidence = {
        "review_report": optional_record(root, "审稿/review_report.json"),
        "score_report": optional_record(root, "评分/score_report.json"),
        "ai_usage": optional_record(root, "合规/ai_usage.json"),
        "compliance_profile": optional_record(root, "合规/compliance_profile.json"),
        "research_sources": optional_record(root, "资料/research_sources.json"),
        "revision_plan": optional_record(root, "修订/revision_plan.json"),
        "authenticity_read": optional_record(root, "修订/authenticity_read.json"),
        "waiver_log": optional_record(root, "审稿/waiver_log.jsonl"),
        "reader_test_plan": optional_record(root, "评分/reader_test_plan.json"),
        "reader_telemetry_summary": optional_record(root, "评分/reader_telemetry_summary.json"),
        "metadata_pack": optional_record(root, "导出/metadata_pack.json"),
    }
    missing_evidence = [key for key, record in evidence.items() if not record.get("exists")]
    chapter_snapshot = snapshot_chapters(root, mode="release:chapters")
    readiness = release_readiness(root, evidence, chapters, exports, release_profile=release_profile)
    evidence_index = build_evidence_index(root, chapters=chapters, exports=exports, evidence=evidence)
    return {
        "schema_version": 1,
        "kind": MANIFEST_KIND,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": root,
        "release_name": release_name or meta.get("title") or os.path.basename(root),
        "release_profile": release_profile,
        "release_profile_label": config.get("label"),
        "title": meta.get("title") or meta.get("source_title") or os.path.basename(root),
        "meta": optional_record(root, "_meta.json"),
        "settings": optional_record(root, "_设置.md"),
        "chapters": chapters,
        "exports": exports,
        "evidence": evidence,
        "evidence_index": evidence_index,
        "missing_evidence": missing_evidence,
        "release_ready": readiness["passed"],
        "release_readiness": readiness,
        "chapter_source_snapshot": chapter_snapshot,
        "chapter_aggregate_hash": chapter_snapshot.get("aggregate_hash") or aggregate_hash(chapters),
        "export_aggregate_hash": aggregate_hash(exports),
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Release Manifest",
        "",
        f"- release：{manifest.get('release_name')}",
        f"- profile：{manifest.get('release_profile')} ({manifest.get('release_profile_label')})",
        f"- title：{manifest.get('title')}",
        f"- generated_at：{manifest.get('generated_at')}",
        f"- chapters：{len(manifest.get('chapters') or [])}",
        f"- exports：{len(manifest.get('exports') or [])}",
        f"- release_ready：{manifest.get('release_ready')}",
        f"- chapter_aggregate_hash：`{manifest.get('chapter_aggregate_hash')}`",
        f"- export_aggregate_hash：`{manifest.get('export_aggregate_hash')}`",
        "",
        "## Evidence",
        "",
        "| item | exists | path | sha256 |",
        "|---|---|---|---|",
    ]
    for key, record in (manifest.get("evidence") or {}).items():
        lines.append(f"| {key} | {record.get('exists')} | {record.get('path')} | {record.get('sha256') or ''} |")
    if manifest.get("missing_evidence"):
        lines.extend(["", "## Missing Evidence", ""])
        for key in manifest["missing_evidence"]:
            lines.append(f"- {key}")
    lines.extend(["", "## Evidence Index", "", "| source | purpose | path | sha256 |", "|---|---|---|---|"])
    for record in manifest.get("evidence_index") or []:
        lines.append(
            f"| {record.get('source')} | {record.get('purpose')} | `{record.get('path')}` | `{record.get('sha256')}` |"
        )
    readiness = manifest.get("release_readiness") or {}
    if readiness.get("blockers"):
        lines.extend(["", "## Release Blockers", ""])
        for item in readiness["blockers"]:
            lines.append(f"- {item.get('id')}: {item.get('message')} {item.get('path') or ''}".rstrip())
    if readiness.get("warnings"):
        lines.extend(["", "## Release Warnings", ""])
        for item in readiness["warnings"]:
            lines.append(f"- {item.get('id')}: {item.get('message')} {item.get('path') or ''}".rstrip())
    lines.extend(["", "## Exports", ""])
    if manifest.get("exports"):
        for record in manifest["exports"]:
            lines.append(f"- `{record['path']}` `{record['sha256']}`")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def write_manifest(root: str, manifest: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "导出")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "release_manifest.json")
    md_path = os.path.join(out_dir, "release_manifest.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(manifest))
    if append_event:
        append_event(
            root,
            event_type="release_manifest_written",
            tool="novel-craft/scripts/release_manifest.py",
            inputs=[
                *sorted({
                    *(record["path"] for record in manifest.get("chapters") or []),
                    *(record["path"] for record in manifest.get("exports") or []),
                    *(
                        record.get("path")
                        for record in (manifest.get("evidence") or {}).values()
                        if isinstance(record, dict) and record.get("exists")
                    ),
                    *(record.get("path") for record in manifest.get("evidence_index") or []),
                }),
            ],
            outputs=[json_path, md_path],
            metadata={
                "release_name": manifest.get("release_name"),
                "release_profile": manifest.get("release_profile"),
                "release_ready": manifest.get("release_ready"),
                "blocker_count": (manifest.get("release_readiness") or {}).get("blocker_count"),
            },
        )
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="build novel release manifest")
    parser.add_argument("project_root")
    parser.add_argument("--release-name", default="")
    parser.add_argument("--release-profile", default=DEFAULT_RELEASE_PROFILE, choices=sorted(RELEASE_PROFILES))
    parser.add_argument("--allow-not-ready", action="store_true", help="write manifest even when release readiness blocks, and return 0")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    manifest = build_manifest(root, release_name=args.release_name, release_profile=args.release_profile)
    json_path, md_path = write_manifest(root, manifest)
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"[ok] release manifest JSON → {json_path}")
        print(f"[ok] release manifest MD   → {md_path}")
        if manifest.get("missing_evidence"):
            print(f"[warn] missing evidence: {', '.join(manifest['missing_evidence'])}")
        if not manifest.get("release_ready"):
            count = (manifest.get("release_readiness") or {}).get("blocker_count", 0)
            print(f"[block] release not ready: {count} blocker(s)", file=sys.stderr)
    return 0 if manifest.get("release_ready") or args.allow_not_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
