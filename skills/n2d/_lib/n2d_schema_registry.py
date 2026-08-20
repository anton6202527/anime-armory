#!/usr/bin/env python3
"""Lightweight schema registry for n2d machine artifacts.

This is intentionally smaller than full JSON Schema.  It validates the contract
fields that make artifacts routable and auditable: kind, version, ownership
fields, trace fields and high-level arrays.  Stage-specific business checks stay
in gate/review scripts.
"""

from __future__ import annotations

import json
import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from n2d_const import (
        ARTIFACT_LINEAGE_MANIFEST_KIND,
        BATCH_QUEUE_KIND,
        COMPLIANCE_MANIFEST_KIND,
        CONSISTENCY_FINDINGS_KIND,
        CONTRACT_INHERITANCE_KIND,
        EMOTION_FLOW_KIND,
        GATE_POLICY_COVERAGE_KIND,
        GENERATION_RECIPE_MANIFEST_KIND,
        GENRE_PACK_CONTEXT_KIND,
        GENRE_PACK_KIND,
        IDENTITY_REGISTRY_KIND,
        IDENTITY_VOICE_PRINT_REPORT_KIND,
        MANIFEST_KIND,
        PRODUCTION_ALERTS_KIND,
        PRODUCTION_DASHBOARD_KIND,
        PRODUCTION_READINESS_KIND,
        PRODUCTION_EVENT_KIND,
        REVIEW_UI_KIND,
        VIDEO_MODEL_ROUTES_KIND,
    )
    from n2d_registry import production_dir
    from n2d_schema import BOUNDARY_PRODUCT_KINDS
    from n2d_action_registry import STOP_REASONS
except ImportError:  # pragma: no cover - package import fallback
    from .n2d_const import (
        ARTIFACT_LINEAGE_MANIFEST_KIND,
        BATCH_QUEUE_KIND,
        COMPLIANCE_MANIFEST_KIND,
        CONSISTENCY_FINDINGS_KIND,
        CONTRACT_INHERITANCE_KIND,
        EMOTION_FLOW_KIND,
        GATE_POLICY_COVERAGE_KIND,
        GENERATION_RECIPE_MANIFEST_KIND,
        GENRE_PACK_CONTEXT_KIND,
        GENRE_PACK_KIND,
        IDENTITY_REGISTRY_KIND,
        IDENTITY_VOICE_PRINT_REPORT_KIND,
        MANIFEST_KIND,
        PRODUCTION_ALERTS_KIND,
        PRODUCTION_DASHBOARD_KIND,
        PRODUCTION_READINESS_KIND,
        PRODUCTION_EVENT_KIND,
        REVIEW_UI_KIND,
        VIDEO_MODEL_ROUTES_KIND,
    )
    from .n2d_registry import production_dir
    from .n2d_schema import BOUNDARY_PRODUCT_KINDS
    from .n2d_action_registry import STOP_REASONS


SCHEMA_REGISTRY_KIND = "n2d_schema_registry"
ARTIFACT_VALIDATION_KIND = "n2d_artifact_validation"
CONTEXT_PACK_KIND = "n2d_context_pack"
CREATIVE_LOOP_KIND = "n2d_creative_loop_packet"
EPISODE_GRAPH_KIND = "n2d_episode_graph"
BLOCKING_BUNDLE_KIND = "n2d_blocking_bundle"
FLOW_TELEMETRY_KIND = "n2d_flow_telemetry"
FLOW_EVENT_KIND = "n2d_flow_event"
VIDEO_EXECUTION_ADAPTER_REGISTRY_KIND = "n2d_video_execution_adapter_registry"
VIDEO_EXECUTION_REQUEST_KIND = "n2d_video_execution_request"
MULTISHOT_BATCH_KIND = "n2d_multishot_batch"
POST_VIDEO_PROXY_KIND = "n2d_post_video_proxy"
POST_VIDEO_PROXY_TIMELINE_KIND = "n2d_post_video_proxy_timeline"
SUPERVISOR_PLAN_KIND = "n2d_supervisor_plan"
GATE_POLICY_MATRIX_KIND = "n2d_gate_policy_matrix"
JOB_RECONCILE_KIND = "n2d_job_reconcile"
CONTRACT_MIGRATION_REPORT_KIND = "n2d_contract_migration_report"
SOURCE_FINGERPRINT_KIND = "n2d_source_fingerprint"
LEITMOTIF_REGISTRY_KIND = "n2d_leitmotif_registry"
ANCHOR_PLAN_KIND = "n2d_anchor_plan"
MOTIF_PLAN_KIND = "n2d_motif_plan"
MOTIF_REGISTRY_KIND = "n2d_motif_registry"
STORY_INTEGRITY_LEDGER_KIND = "n2d_story_integrity_ledger"
THREAD_SCHEDULER_KIND = "n2d_thread_scheduler"
PILOT_ARC_CONTRACT_KIND = "n2d_pilot_arc_contract"
STORYBOARD_KIND = "n2d_storyboard"
ARTIFACT_SIGNOFF_KIND = "n2d_artifact_signoff"
AUTONOMY_AUTHORIZATION_KIND = "n2d_autonomy_authorization"
PRODUCTION_MODE_ROUTE_KIND = "n2d_production_mode_route"
EDITORIAL_TIMELINE_KIND = "n2d_editorial_timeline"
VOICE_CASTING_KIND = "n2d_voice_casting"
TIMING_ESTIMATE_KIND = "n2d_timing_estimate"
SHOT_TIMING_BASIS_KIND = "n2d_shot_timing_basis"
BGM_CONTRACT_KIND = "n2d_bgm_contract"
BGM_GENERATION_JOB_KIND = "n2d_bgm_generation_job"
BGM_GENERATION_RECEIPT_KIND = "n2d_bgm_generation_receipt"
SERIES_CONSISTENCY_KIND = "n2d_series_consistency"
VOICE_FIT_REPORT_KIND = "n2d_voice_fit_report"
ACCEPTANCE_RECEIPT_KIND = "n2d_acceptance_receipt"
RELEASE_MANIFEST_KIND = "n2d_release_manifest"
VIDEO_EVAL_MANIFEST_KIND = "n2d_video_eval_manifest"
PROJECT_CHARACTER_ASSET_BUNDLE_KIND = "n2d_project_character_asset_bundle"
VISUAL_REFERENCE_MANIFEST_KIND = "n2d_visual_reference_manifest"
SCHEMA_VERSION = 1

# A path in the boundary registry is an explicit machine-contract claim.  A
# manifest filename is also an explicit claim, while a non-empty ``kind`` is a
# payload-level claim.  Other JSON files are allowed to be caches, views or
# authoring helpers and must not be promoted merely because their suffix is
# ``.json``.
SCAN_SCOPE_ALL = "all"
SCAN_SCOPE_RELEASE = "release"
SCAN_SCOPES = (SCAN_SCOPE_ALL, SCAN_SCOPE_RELEASE)
VERSION_FIELDS = ("version", "schema_version", "contract_version")
EVENT_STREAM_KINDS = {
    "production_events.jsonl": PRODUCTION_EVENT_KIND,
    "flow_events.jsonl": FLOW_EVENT_KIND,
}
BOUNDARY_KIND_ALIASES = {
    kind: tuple(str(value) for value in (meta.get("accepted_kinds") or []) if str(value))
    for kind, meta in BOUNDARY_PRODUCT_KINDS.items()
    if meta.get("accepted_kinds")
}
_BOUNDARY_ALIAS_TO_CANONICAL = {
    alias: canonical
    for canonical, aliases in BOUNDARY_KIND_ALIASES.items()
    for alias in aliases
}

TYPE_NAMES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
}


def obj(required: Iterable[str], properties: Dict[str, Any], *, allow_extra: bool = True) -> Dict[str, Any]:
    return {"type": "object", "required": list(required), "properties": properties, "allow_extra": allow_extra}


def arr(items: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"type": "array", "items": items or {}}


def issue(severity: str, source: str, message: str, *, pointer: str = "$", kind: str = "") -> Dict[str, Any]:
    return {"severity": severity, "source": source, "pointer": pointer, "kind": kind, "message": message}


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    typ = TYPE_NAMES.get(expected)
    return isinstance(value, typ) if typ else True


def _validate(value: Any, schema: Dict[str, Any], *, source: str, pointer: str = "$", kind: str = "") -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    expected_type = schema.get("type")
    nullable = bool(schema.get("nullable"))
    if value is None and nullable:
        return issues
    if expected_type and not _type_ok(value, str(expected_type)):
        issues.append(issue("block", source, f"expected {expected_type}, got {type(value).__name__}", pointer=pointer, kind=kind))
        return issues
    enum = schema.get("enum")
    if enum is not None and value not in enum:
        issues.append(issue("block", source, f"value must be one of {enum!r}", pointer=pointer, kind=kind))
    if expected_type == "object":
        required = schema.get("required") or []
        props = schema.get("properties") or {}
        for key in required:
            if key not in value or value.get(key) in (None, ""):
                issues.append(issue("block", source, f"missing required field `{key}`", pointer=f"{pointer}.{key}", kind=kind))
        for key, child_schema in props.items():
            if key in value:
                issues.extend(_validate(value[key], child_schema, source=source, pointer=f"{pointer}.{key}", kind=kind))
        if not schema.get("allow_extra", True):
            extra = sorted(set(value) - set(props))
            for key in extra:
                issues.append(issue("warn", source, f"unknown field `{key}`", pointer=f"{pointer}.{key}", kind=kind))
    elif expected_type == "array":
        item_schema = schema.get("items") or {}
        if item_schema:
            for idx, item in enumerate(value):
                issues.extend(_validate(item, item_schema, source=source, pointer=f"{pointer}[{idx}]", kind=kind))
    return issues


# Exact-path legacy contracts.  These are not a general exemption from the
# kind/version envelope: each rule names one registered boundary kind, checks
# its historical shape, and emits a visible v0 -> v1 migration warning.
LEGACY_BOUNDARY_SCHEMAS: Dict[str, Dict[str, Any]] = {
    EMOTION_FLOW_KIND: arr({"type": "object"}),
    CONTRACT_INHERITANCE_KIND: obj(
        (
            "kind", "episode", "image_overview", "video_overview", "fields", "summary",
            "identity_handoff", "asset_handoff", "pixel_contract", "verdict", "generated_at",
            "inputs_fingerprint",
        ),
        {
            "kind": {"type": "string", "enum": [CONTRACT_INHERITANCE_KIND]},
            "episode": {"type": "string"},
            "image_overview": {"type": "string"},
            "video_overview": {"type": "string"},
            "fields": arr({"type": "object"}),
            "summary": {"type": "object"},
            "identity_handoff": {"type": "object"},
            "asset_handoff": {"type": "object"},
            "pixel_contract": {"type": "object"},
            "verdict": {"type": "string"},
            "generated_at": {"type": "string"},
            "inputs_fingerprint": {"type": "object"},
        },
    ),
    IDENTITY_VOICE_PRINT_REPORT_KIND: obj(
        ("kind", "episode", "available", "mode", "precision", "groups", "total_drift"),
        {
            "kind": {
                "type": "string",
                "enum": [IDENTITY_VOICE_PRINT_REPORT_KIND, "n2d_identity_voice_print"],
            },
            "episode": {"type": "string"},
            "available": {"type": "boolean"},
            "mode": {"type": "string"},
            "precision": {"type": "string"},
            "groups": {"type": "object"},
            "total_drift": {"type": "integer"},
            "precision_level": {"type": "string"},
        },
    ),
}


def _validate_explicit_legacy_boundary(
    payload: Any,
    *,
    expected_kind: str,
    source: str,
) -> Optional[Tuple[List[Dict[str, Any]], Dict[str, Any]]]:
    schema = LEGACY_BOUNDARY_SCHEMAS.get(expected_kind)
    if not schema:
        return None
    if expected_kind == EMOTION_FLOW_KIND:
        if not isinstance(payload, list):
            return None
    else:
        if not isinstance(payload, dict) or any(field in payload for field in VERSION_FIELDS):
            return None
        actual_kind = str(payload.get("kind") or "")
        accepted = {expected_kind, *BOUNDARY_KIND_ALIASES.get(expected_kind, ())}
        if actual_kind not in accepted:
            return None
    issues = _validate(payload, schema, source=source, kind=expected_kind)
    issues.append(
        issue(
            "warn",
            source,
            f"accepted explicit legacy v0 contract for `{expected_kind}`; migrate writer to versioned v1 envelope",
            kind=expected_kind,
        )
    )
    return issues, {
        "rule": f"legacy_v0_{expected_kind}",
        "from_version": 0,
        "to_version": 1,
        "status": "accepted_with_migration_warning",
    }


SCHEMAS: Dict[str, Dict[str, Any]] = {
    PRODUCTION_EVENT_KIND: obj(
        ("kind", "version", "ts", "episode", "stage", "event", "source"),
        {
            "kind": {"type": "string", "enum": [PRODUCTION_EVENT_KIND]},
            "version": {"type": "integer"},
            "ts": {"type": "string"},
            "episode": {"type": "string"},
            "stage": {"type": "string"},
            "event": {"type": "string"},
            "source": {"type": "string"},
            "trace": obj((), {"trace_id": {"type": "string"}, "span_id": {"type": "string"}, "idempotency_key": {"type": "string"}}),
            "meta": {"type": "object"},
        },
    ),
    PRODUCTION_DASHBOARD_KIND: obj(
        ("kind", "version", "root", "episodes", "totals"),
        {
            "kind": {"type": "string", "enum": [PRODUCTION_DASHBOARD_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "episodes": arr(obj(("episode",), {
                "episode": {"type": "string"},
                "event_count": {"type": "integer"},
                "progress_next_stage": {"type": "string"},
                "progress_next_skill": {"type": "string"},
                "stages": {"type": "object"},
            })),
            "totals": {"type": "object"},
            "alerts": arr({"type": "object"}),
            "alert_counts": {"type": "object"},
            "release_metrics_file": {"type": "string"},
            "retention_trend": {"type": "object"},
            "benchmarks": {"type": "object"},
        },
    ),
    PRODUCTION_ALERTS_KIND: obj(
        ("kind", "version", "root", "generated_at", "thresholds", "counts", "alerts"),
        {
            "kind": {"type": "string", "enum": [PRODUCTION_ALERTS_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "generated_at": {"type": "string"},
            "thresholds": {"type": "object"},
            "counts": {"type": "object"},
            "alerts": arr({"type": "object"}),
        },
    ),
    BATCH_QUEUE_KIND: obj(
        ("kind", "version", "root", "tasks"),
        {
            "kind": {"type": "string", "enum": [BATCH_QUEUE_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "tasks": arr(obj(("id", "episode", "stage_key", "status"), {
                "id": {"type": "string"},
                "episode": {"type": "string"},
                "stage_key": {"type": "string"},
                "status": {"type": "string"},
                "idempotency_key": {"type": "string"},
            })),
            "coordination": {"type": "object"},
        },
    ),
    COMPLIANCE_MANIFEST_KIND: obj(
        ("kind", "version"),
        {"kind": {"type": "string", "enum": [COMPLIANCE_MANIFEST_KIND]}, "version": {"type": "integer"}},
    ),
    IDENTITY_REGISTRY_KIND: obj(
        ("kind", "version"),
        {
            "kind": {"type": "string", "enum": [IDENTITY_REGISTRY_KIND]},
            "version": {"type": "integer"},
            "characters": arr({"type": "object"}),
        },
    ),
    VIDEO_MODEL_ROUTES_KIND: obj(
        ("kind", "version"),
        {
            "kind": {"type": "string", "enum": [VIDEO_MODEL_ROUTES_KIND]},
            "version": {"type": "integer"},
            "routes": arr({"type": "object"}),
        },
    ),
    CONSISTENCY_FINDINGS_KIND: obj(
        ("kind", "version", "episode", "findings"),
        {
            "kind": {"type": "string", "enum": [CONSISTENCY_FINDINGS_KIND]},
            "version": {"type": "integer"},
            "episode": {"type": "string"},
            "gate_stage": {"type": "string"},
            "summary": {"type": "object"},
            "findings": arr({"type": "object"}),
            "auto_return_tasks": arr({"type": "object"}),
        },
    ),
    REVIEW_UI_KIND: obj(
        ("kind", "version"),
        {"kind": {"type": "string", "enum": [REVIEW_UI_KIND]}, "version": {"type": "integer"}},
    ),
    MANIFEST_KIND: obj(
        ("kind", "schema_version", "episode", "stage", "artifacts"),
        {
            "kind": {"type": "string", "enum": [MANIFEST_KIND]},
            "schema_version": {"type": "integer"},
            "episode": {"type": "string"},
            "stage": {"type": "string"},
            "production_mode": {"type": "string"},
            "artifacts": arr(obj(("stage", "path", "exists", "kind"), {
                "stage": {"type": "string"},
                "path": {"type": "string"},
                "exists": {"type": "boolean"},
                "kind": {"type": "string"},
                "sha256": {"type": "string"},
            })),
        },
    ),
    ACCEPTANCE_RECEIPT_KIND: obj(
        ("kind", "version", "episode", "decision", "reviewer", "accepted_at", "bindings", "evidence_digest", "receipt_id"),
        {
            "kind": {"type": "string", "enum": [ACCEPTANCE_RECEIPT_KIND]},
            "version": {"type": "integer"},
            "episode": {"type": "string"},
            "decision": {"type": "string", "enum": ["approved", "accepted"]},
            "reviewer": {"type": "string"},
            "accepted_at": {"type": "string"},
            "bindings": {"type": "object"},
            "evidence_digest": {"type": "string"},
            "receipt_id": {"type": "string"},
            "source": {"type": "object"},
        },
    ),
    RELEASE_MANIFEST_KIND: obj(
        ("kind", "version", "episode", "root", "stage", "asset", "compliance", "review", "provenance", "readiness"),
        {
            "kind": {"type": "string", "enum": [RELEASE_MANIFEST_KIND]},
            "version": {"type": "integer"},
            "episode": {"type": "string"},
            "root": {"type": "string"},
            "stage": {"type": "string"},
            "asset": {"type": "object"},
            "compliance": {"type": "object"},
            "review": {"type": "object"},
            "provenance": {"type": "object"},
            "readiness": {"type": "object"},
            "transparency": {"type": "object"},
            "platform_release_checklist": {"type": "object"},
            "manifest_id": {"type": "string"},
        },
    ),
    VIDEO_EVAL_MANIFEST_KIND: obj(
        ("kind", "version", "root", "episode", "generated_at", "media", "sidecar_targets", "judge_schema_required", "tasks"),
        {
            "kind": {"type": "string", "enum": [VIDEO_EVAL_MANIFEST_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "episode": {"type": "string"},
            "generated_at": {"type": "string"},
            "media": arr({"type": "string"}),
            "sidecar_targets": {"type": "object"},
            "judge_schema_required": arr({"type": "string"}),
            "tasks": arr(obj(
                ("clip", "media", "frame_sampling", "risk_kinds", "questions"),
                {
                    "clip": {"type": "string"},
                    "media": arr({"type": "string"}),
                    "frame_sampling": {"type": "object"},
                    "risk_kinds": arr({"type": "string"}),
                    "physical_rules": arr({"type": "string"}),
                    "questions": arr({"type": "object"}),
                },
            )),
            "notes": arr({"type": "string"}),
        },
    ),
    PROJECT_CHARACTER_ASSET_BUNDLE_KIND: obj(
        ("kind", "version", "character_id", "name", "library_tier", "directories", "truth_sources", "updated_at"),
        {
            "kind": {"type": "string", "enum": [PROJECT_CHARACTER_ASSET_BUNDLE_KIND]},
            "version": {"type": "integer"},
            "character_id": {"type": "string"},
            "name": {"type": "string"},
            "scope": {"type": "string"},
            "library_tier": {"type": "string"},
            "planned_episode_count": {"type": "integer"},
            "directories": {"type": "object"},
            "truth_sources": {"type": "object"},
            "created_by": {"type": "string"},
            "updated_at": {"type": "string"},
        },
    ),
    VISUAL_REFERENCE_MANIFEST_KIND: obj(
        ("kind", "version", "status", "updated_at", "references", "rules"),
        {
            "kind": {"type": "string", "enum": [VISUAL_REFERENCE_MANIFEST_KIND]},
            "version": {"type": "integer"},
            "status": {"type": "string"},
            "updated_at": {"type": "string"},
            "references": arr(obj(
                (
                    "reference_id", "name", "path", "sha256", "source", "use_policy",
                    "rights_status", "eligible_for_generation", "backend_upload_allowed",
                ),
                {
                    "reference_id": {"type": "string"},
                    "name": {"type": "string"},
                    "path": {"type": "string"},
                    "sha256": {"type": "string"},
                    "source": {"type": "string"},
                    "use_policy": {"type": "string"},
                    "rights_status": {"type": "string"},
                    "eligible_for_generation": {"type": "boolean"},
                    "backend_upload_allowed": {"type": "boolean"},
                },
            )),
            "rules": {"type": "object"},
        },
    ),
    CONTEXT_PACK_KIND: obj(
        ("kind", "version", "root", "episode", "stage_key", "action_contract", "files"),
        {
            "kind": {"type": "string", "enum": [CONTEXT_PACK_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "episode": {"type": "string"},
            "stage_key": {"type": "string"},
            "action_contract": {"type": "object"},
            "files": arr(obj(("relpath", "exists"), {"relpath": {"type": "string"}, "exists": {"type": "boolean"}})),
        },
    ),
    EPISODE_GRAPH_KIND: obj(
        ("kind", "version", "root", "episode", "nodes", "edges", "source_files", "graph_hash", "summary", "status"),
        {
            "kind": {"type": "string", "enum": [EPISODE_GRAPH_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "episode": {"type": "string"},
            "nodes": arr(obj(("id", "type"), {"id": {"type": "string"}, "type": {"type": "string"}})),
            "edges": arr(obj(("source", "relation", "target"), {
                "source": {"type": "string"}, "relation": {"type": "string"}, "target": {"type": "string"},
            })),
            "source_files": arr({"type": "object"}),
            "graph_hash": {"type": "string"},
            "summary": {"type": "object"},
            "status": {"type": "string"},
            "lineage_gaps": arr({"type": "object"}),
        },
    ),
    BLOCKING_BUNDLE_KIND: obj(
        ("kind", "version", "episode", "stage_key", "stop_reason", "category", "blocked", "blockers"),
        {
            "kind": {"type": "string", "enum": [BLOCKING_BUNDLE_KIND]},
            "version": {"type": "integer"},
            "episode": {"type": "string"},
            "stage_key": {"type": "string"},
            "stop_reason": {"type": "string", "enum": list(STOP_REASONS)},
            "category": {"type": "string"},
            "blocked": {"type": "boolean"},
            "blockers": arr({"type": "object"}),
            "repair_commands": arr({"type": "string"}),
            "gate": {"type": "object"},
            "episode_graph": {"type": "object"},
        },
    ),
    BGM_CONTRACT_KIND: obj(
        ("kind", "version", "episode", "status", "strategy", "source", "cues"),
        {
            "kind": {"type": "string", "enum": [BGM_CONTRACT_KIND]},
            "version": {"type": "integer"},
            "episode": {"type": "string"},
            "status": {"type": "string"},
            "strategy": {"type": "string", "enum": ["none", "licensed_file", "generated", "placeholder"]},
            "source": {"type": "object"},
            "cues": arr({"type": "object"}),
            "mix": {"type": "object"},
            "placeholder_approval": {"type": "object"},
        },
    ),
    BGM_GENERATION_JOB_KIND: obj(
        ("kind", "version", "episode", "duration_sec", "model", "channel", "output", "cues"),
        {"kind": {"type": "string", "enum": [BGM_GENERATION_JOB_KIND]}, "version": {"type": "integer"},
         "episode": {"type": "string"}, "duration_sec": {"type": "number"}, "model": {"type": "string"},
         "channel": {"type": "string"}, "output": {"type": "string"}, "cues": arr({"type": "object"}),
         "mix": {"type": "object"}},
    ),
    BGM_GENERATION_RECEIPT_KIND: obj(
        ("kind", "version", "status", "episode", "model", "channel", "output", "output_sha256", "contract_sha256", "mode"),
        {"kind": {"type": "string", "enum": [BGM_GENERATION_RECEIPT_KIND]}, "version": {"type": "integer"},
         "status": {"type": "string", "enum": ["pass"]}, "episode": {"type": "string"},
         "model": {"type": "string"}, "channel": {"type": "string"}, "output": {"type": "string"},
         "output_sha256": {"type": "string"}, "contract_sha256": {"type": "string"}, "mode": {"type": "string"},
         "registered_at": {"type": "string"}},
    ),
    SERIES_CONSISTENCY_KIND: obj(
        ("kind", "version", "status", "subtitle_style", "canonical_names", "dialogue_registers", "audio_baseline"),
        {
            "kind": {"type": "string", "enum": [SERIES_CONSISTENCY_KIND]},
            "version": {"type": "integer"},
            "status": {"type": "string"},
            "subtitle_style": {"type": "object"},
            "canonical_names": {"type": "object"},
            "dialogue_registers": {"type": "object"},
            "audio_baseline": {"type": "object"},
        },
    ),
    VOICE_FIT_REPORT_KIND: obj(
        ("kind", "version", "episode", "language", "status", "applied", "fit_scope", "rows", "input_sha256"),
        {
            "kind": {"type": "string", "enum": [VOICE_FIT_REPORT_KIND]},
            "version": {"type": "integer"},
            "episode": {"type": "string"},
            "language": {"type": "string"},
            "status": {"type": "string", "enum": ["planned", "pass", "block"]},
            "applied": {"type": "boolean"},
            "fit_scope": arr({"type": "string"}),
            "rows": arr({"type": "object"}),
            "summary": {"type": "object"},
            "output": {"type": "string"},
            "output_sha256": {"type": "string"},
            "input_sha256": {"type": "object"},
        },
    ),
    FLOW_TELEMETRY_KIND: obj(
        ("kind", "version", "event_count", "stop_reasons", "stages", "prework", "orchestrator_latency_ms"),
        {
            "kind": {"type": "string", "enum": [FLOW_TELEMETRY_KIND]},
            "version": {"type": "integer"},
            "event_count": {"type": "integer"},
            "stop_reasons": {"type": "object"},
            "stages": {"type": "object"},
            "prework": {"type": "object"},
            "orchestrator_latency_ms": {"type": "object"},
        },
    ),
    FLOW_EVENT_KIND: obj(
        ("kind", "version", "at", "event_type"),
        {
            "kind": {"type": "string", "enum": [FLOW_EVENT_KIND]},
            "version": {"type": "integer"},
            "at": {"type": "string"},
            "event_type": {"type": "string"},
            "episode": {"type": "string"},
            "stage": {"type": "string"},
        },
    ),
    VIDEO_EXECUTION_ADAPTER_REGISTRY_KIND: obj(
        ("kind", "version", "adapters"),
        {
            "kind": {"type": "string", "enum": [VIDEO_EXECUTION_ADAPTER_REGISTRY_KIND]},
            "version": {"type": "integer"},
            "adapters": {"type": "object"},
        },
    ),
    VIDEO_EXECUTION_REQUEST_KIND: obj(
        ("kind", "version", "operation", "adapter_id", "root", "episode", "clip", "inputs", "output", "idempotency_key", "request_sha256"),
        {
            "kind": {"type": "string", "enum": [VIDEO_EXECUTION_REQUEST_KIND]},
            "version": {"type": "integer"},
            "operation": {"type": "string"},
            "adapter_id": {"type": "string"},
            "root": {"type": "string"},
            "episode": {"type": "string"},
            "clip": {"type": "string"},
            "inputs": {"type": "object"},
            "output": {"type": "object"},
            "idempotency_key": {"type": "string"},
            "request_sha256": {"type": "string"},
        },
    ),
    MULTISHOT_BATCH_KIND: obj(
        ("kind", "version", "episode", "group_id", "backend", "members", "status", "shots"),
        {
            "kind": {"type": "string", "enum": [MULTISHOT_BATCH_KIND]},
            "version": {"type": "integer"},
            "episode": {"type": "string"},
            "group_id": {"type": "string"},
            "backend": {"type": "string"},
            "members": arr({"type": "string"}),
            "status": {"type": "string"},
            "shots": arr({"type": "object"}),
        },
    ),
    POST_VIDEO_PROXY_KIND: obj(
        ("kind", "version", "episode", "status", "timeline", "output"),
        {
            "kind": {"type": "string", "enum": [POST_VIDEO_PROXY_KIND]},
            "version": {"type": "integer"},
            "episode": {"type": "string"},
            "status": {"type": "string"},
            "timeline": arr({"type": "object"}),
            "output": {"type": "string"},
        },
    ),
    POST_VIDEO_PROXY_TIMELINE_KIND: obj(
        ("kind", "version", "episode", "status", "timeline"),
        {
            "kind": {"type": "string", "enum": [POST_VIDEO_PROXY_TIMELINE_KIND]},
            "version": {"type": "integer"},
            "episode": {"type": "string"},
            "status": {"type": "string"},
            "timeline": arr({"type": "object"}),
        },
    ),
    ARTIFACT_SIGNOFF_KIND: obj(
        ("kind", "version", "artifact_scope", "authored_by", "input_fingerprint", "evidence_fingerprint", "required_approval_groups", "approvals", "status"),
        {
            "kind": {"type": "string", "enum": [ARTIFACT_SIGNOFF_KIND]},
            "version": {"type": "integer"},
            "artifact_scope": {"type": "string"},
            "episode": {"type": "string"},
            "authored_by": {"type": "string"},
            "input_fingerprint": {"type": "object"},
            "evidence_fingerprint": {"type": "object"},
            "required_approval_groups": arr({"type": "object"}),
            "approvals": arr({"type": "object"}),
            "status": {"type": "string"},
        },
    ),
    AUTONOMY_AUTHORIZATION_KIND: obj(
        (
            "kind", "version", "status", "policy", "project_root", "authorization_id",
            "authorized_by", "authorized_at", "source_quote", "delegated_reviewer_id",
            "allowed_signoff_profiles", "allowed_boundary_decisions", "human_confirmation_required",
        ),
        {
            "kind": {"type": "string", "enum": [AUTONOMY_AUTHORIZATION_KIND]},
            "version": {"type": "integer"},
            "status": {"type": "string"},
            "policy": {"type": "string"},
            "project_root": {"type": "string"},
            "project_name": {"type": "string"},
            "authorization_id": {"type": "string"},
            "authorized_by": {"type": "string"},
            "authorized_at": {"type": "string"},
            "source_quote": {"type": "string"},
            "delegated_reviewer_id": {"type": "string"},
            "allowed_signoff_profiles": arr({"type": "string"}),
            "allowed_boundary_decisions": arr({"type": "string"}),
            "allowed_internal_actions": arr({"type": "string"}),
            "human_confirmation_required": arr({"type": "string"}),
            "independent_review": {"type": "string"},
        },
    ),
    PRODUCTION_MODE_ROUTE_KIND: obj(
        ("kind", "version", "episode", "status", "decision", "signals", "inputs_fingerprint"),
        {
            "kind": {"type": "string", "enum": [PRODUCTION_MODE_ROUTE_KIND]},
            "version": {"type": "integer"},
            "episode": {"type": "string"},
            "status": {"type": "string"},
            "decision": {"type": "object"},
            "signals": {"type": "object"},
            "clip_routes": arr({"type": "object"}),
            "summary": {"type": "object"},
            "inputs_fingerprint": {"type": "object"},
        },
    ),
    VOICE_CASTING_KIND: obj(
        ("kind", "version", "status", "policy", "roles", "summary"),
        {
            "kind": {"type": "string", "enum": [VOICE_CASTING_KIND]},
            "version": {"type": "integer"},
            "status": {"type": "string"},
            "policy": {"type": "string"},
            "roles": arr(obj(("role", "status"), {
                "role": {"type": "string"},
                "status": {"type": "string"},
                "backend": {"type": "string"},
                "voice_id": {"type": "string"},
                "canonical_sample": {"type": "string"},
            })),
            "summary": {"type": "object"},
        },
    ),
    TIMING_ESTIMATE_KIND: obj(
        ("kind", "version", "episode", "status", "audio_generated", "timing_basis", "lines", "summary"),
        {
            "kind": {"type": "string", "enum": [TIMING_ESTIMATE_KIND]},
            "version": {"type": "integer"},
            "episode": {"type": "string"},
            "status": {"type": "string"},
            "source_fingerprint": {"type": "string"},
            "audio_generated": {"type": "boolean", "enum": [False]},
            "timing_basis": {"type": "string", "enum": ["text_estimate_no_audio"]},
            "lines": arr(obj(("line_index", "镜头", "角色", "文本", "时长", "start", "end", "gap_after", "timing_basis"), {
                "line_index": {"type": "integer"},
                "镜头": {"type": "string"},
                "角色": {"type": "string"},
                "文本": {"type": "string"},
                "时长": {"type": "number"},
                "start": {"type": "number"},
                "end": {"type": "number"},
                "gap_after": {"type": "number"},
                "timing_basis": {"type": "string"},
            })),
            "summary": {"type": "object"},
        },
    ),
    SHOT_TIMING_BASIS_KIND: obj(
        ("kind", "version", "episode", "timing_basis", "provisional", "source", "final_voice_required_before_compose"),
        {
            "kind": {"type": "string", "enum": [SHOT_TIMING_BASIS_KIND]},
            "version": {"type": "integer"},
            "episode": {"type": "string"},
            "timing_basis": {"type": "string"},
            "provisional": {"type": "boolean"},
            "source": {"type": "string"},
            "final_voice_required_before_compose": {"type": "boolean"},
        },
    ),
    EDITORIAL_TIMELINE_KIND: obj(
        ("kind", "version", "episode", "phase", "status", "duration_sec", "track_names", "media", "seams", "otio_path", "otio_sha256"),
        {
            "kind": {"type": "string", "enum": [EDITORIAL_TIMELINE_KIND]},
            "version": {"type": "integer"},
            "episode": {"type": "string"},
            "phase": {"type": "string"},
            "status": {"type": "string"},
            "duration_sec": {"type": "number"},
            "track_names": arr({"type": "string"}),
            "media": arr({"type": "object"}),
            "seams": arr({"type": "object"}),
            "otio_path": {"type": "string"},
            "otio_sha256": {"type": "string"},
        },
    ),
    CREATIVE_LOOP_KIND: obj(
        ("kind", "version", "root", "episode", "stage_key", "action_contract", "loop"),
        {
            "kind": {"type": "string", "enum": [CREATIVE_LOOP_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "episode": {"type": "string"},
            "stage_key": {"type": "string"},
            "action_contract": {"type": "object"},
            "loop": arr(obj(("step", "owner"), {"step": {"type": "string"}, "owner": {"type": "string"}})),
        },
    ),
    SUPERVISOR_PLAN_KIND: obj(
        ("kind", "version", "root", "next_action", "dispatch", "summary"),
        {
            "kind": {"type": "string", "enum": [SUPERVISOR_PLAN_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "episode": {"type": "string"},
            "next_action": {"type": "object"},
            "dispatch": {"type": "object"},
            "summary": {"type": "object"},
        },
    ),
    GATE_POLICY_MATRIX_KIND: obj(
        ("kind", "version", "stages"),
        {
            "kind": {"type": "string", "enum": [GATE_POLICY_MATRIX_KIND]},
            "version": {"type": "integer"},
            "stages": {"type": "object"},
        },
    ),
    JOB_RECONCILE_KIND: obj(
        ("kind", "version", "root", "summary", "matches"),
        {
            "kind": {"type": "string", "enum": [JOB_RECONCILE_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "summary": {"type": "object"},
            "matches": arr({"type": "object"}),
        },
    ),
    CONTRACT_MIGRATION_REPORT_KIND: obj(
        ("kind", "contract_version", "root", "applied", "before", "after"),
        {
            "kind": {"type": "string", "enum": [CONTRACT_MIGRATION_REPORT_KIND]},
            "contract_version": {"type": "integer"},
            "root": {"type": "string"},
            "applied": {"type": "boolean"},
            "before": {"type": "object"},
            "after": {"type": "object"},
            "steps": arr({"type": "object"}),
        },
    ),
    SOURCE_FINGERPRINT_KIND: obj(
        ("kind", "version", "source_label", "source_kind", "source_hash"),
        {
            "kind": {"type": "string", "enum": [SOURCE_FINGERPRINT_KIND]},
            "version": {"type": "integer"},
            "source_label": {"type": "string"},
            "source_kind": {"type": "string"},
            "source_hash": {"type": "string"},
            "source_chars": {"type": "integer"},
            "episodes": {"type": "integer"},
            "upstream": {"type": "object"},
            "rule": {"type": "string"},
        },
    ),
    LEITMOTIF_REGISTRY_KIND: obj(
        ("kind", "motifs"),
        {
            "kind": {"type": "string", "enum": [LEITMOTIF_REGISTRY_KIND]},
            "version": {"type": "integer"},
            "motifs": arr(obj(("id", "subject", "desc"), {
                "id": {"type": "string"},
                "subject": arr({"type": "string"}),
                "desc": {"type": "string"},
                "file": {"type": "string"},
                "audio_sha256": {"type": "string"},
                "cue": {"type": "string"},
            })),
        },
    ),
    ANCHOR_PLAN_KIND: obj(
        ("kind", "schema_version", "episode", "planned"),
        {
            "kind": {"type": "string", "enum": [ANCHOR_PLAN_KIND]},
            "schema_version": {"type": "integer"},
            "episode": {"type": "string"},
            "params": {"type": "object"},
            "planned": arr(obj(("clip_id", "duration", "anchors"), {
                "clip_index": {"type": "integer"},
                "clip_id": {"type": "string"},
                "duration": {"type": "number"},
                "rule": {"type": "string"},
                "anchors": arr(obj(("anchor_png", "at_sec", "use", "reason"), {
                    "anchor_png": {"type": "string"},
                    "at_sec": {"type": "number"},
                    "use": {"type": "string"},
                    "reason": {"type": "string"},
                })),
                "added_cost": {"type": "object"},
            })),
            "summary": {"type": "object"},
        },
    ),
    MOTIF_PLAN_KIND: obj(
        ("kind", "schema_version", "episode", "motif_clips", "summary"),
        {
            "kind": {"type": "string", "enum": [MOTIF_PLAN_KIND]},
            "schema_version": {"type": "integer"},
            "episode": {"type": "string"},
            "genre": {"type": "object"},
            "motif_clips": arr(obj(("clip_id", "motif_type", "motif_id", "template"), {
                "clip_index": {"type": "integer"},
                "clip_id": {"type": "string"},
                "motif_type": {"type": "string"},
                "motif_id": {"type": "string"},
                "template": {"type": "string"},
                "hits": {"type": "integer"},
                "matched": arr({"type": "string"}),
                "rule": {"type": "string"},
                "growth_suggestion": {"type": "object"},
            })),
            "summary": {"type": "object"},
        },
    ),
    MOTIF_REGISTRY_KIND: obj(
        ("kind", "version", "motifs"),
        {
            "kind": {"type": "string", "enum": [MOTIF_REGISTRY_KIND]},
            "version": {"type": "integer"},
            "motifs": arr(obj(("motif_id", "motif_type", "growth_state_machine"), {
                "motif_id": {"type": "string"},
                "motif_type": {"type": "string"},
                "scope": {"type": "string"},
                "growth_state_machine": obj(("progression",), {
                    "bound_vfx": {"type": "string"},
                    "monotonic_fields": arr({"type": "string"}),
                    "progression": arr(obj(("at_clip", "level", "panel_tier", "title"), {
                        "at_clip": {"type": "string"},
                        "level": {"type": "integer"},
                        "panel_tier": {"type": "string"},
                        "title": {"type": "string"},
                        "attrs": {"type": "object"},
                        "overlay_lines": arr({"type": "string"}),
                    })),
                }),
                "shot_template_id": {"type": "string"},
                "dialogue_patterns": {"type": "object"},
                "overlay_spec": {"type": "object"},
            })),
        },
    ),
    STORY_INTEGRITY_LEDGER_KIND: obj(
        ("kind", "version", "episodes"),
        {
            "kind": {"type": "string", "enum": [STORY_INTEGRITY_LEDGER_KIND]},
            "version": {"type": "integer"},
            "generated_at": {"type": "string"},
            "episodes": arr(obj(("episode",), {
                "episode": {"type": "string"},
                "choices": arr({"type": "object"}),
                "consequences": arr({"type": "object"}),
                "motivations": arr({"type": "object"}),
                "dialogue_functions": arr({"type": "object"}),
            })),
        },
    ),
    THREAD_SCHEDULER_KIND: obj(
        ("kind", "version", "threads"),
        {
            "kind": {"type": "string", "enum": [THREAD_SCHEDULER_KIND]},
            "version": {"type": "integer"},
            "generated_at": {"type": "string"},
            "threads": arr(obj(("thread_id", "status", "opened_ep", "next_due_ep", "open_question"), {
                "id": {"type": "string"},
                "thread_id": {"type": "string"},
                "status": {"type": "string"},
                "opened_ep": {"type": "string"},
                "last_touched_ep": {"type": "string"},
                "next_due_ep": {"type": "string"},
                "payoff_ep": {"type": "string"},
                "open_question": {"type": "string"},
                "touch_keywords": arr({"type": "string"}),
            })),
        },
    ),
    PILOT_ARC_CONTRACT_KIND: obj(
        (
            "kind",
            "version",
            "episode_window",
            "series_promise",
            "protagonist_desire",
            "repeatable_pleasure_loop",
            "long_question",
        ),
        {
            "kind": {"type": "string", "enum": [PILOT_ARC_CONTRACT_KIND]},
            "version": {"type": "integer"},
            "episode_window": arr({"type": "string"}),
            "series_promise": {"type": "string"},
            "protagonist_desire": {"type": "string"},
            "repeatable_pleasure_loop": {"type": "string"},
            "long_question": {"type": "string"},
            "first_payoff_ep": {"type": "string"},
            "first_complication_ep": {"type": "string"},
            "first_reversal_ep": {"type": "string"},
            "notes": {"type": "string"},
        },
    ),
    STORYBOARD_KIND: obj(
        ("kind", "version", "episode", "clips", "visual_contract", "style_contract"),
        {
            "kind": {"type": "string", "enum": [STORYBOARD_KIND]},
            "version": {"type": "integer"},
            "episode": {"type": "string"},
            "title": {"type": "string"},
            "source": {"type": "string"},
            "total_duration": {"type": "number"},
            "policy": {"type": "object"},
            "first_3s_visual_hook": {"type": "object"},
            "retention_promise_ledger": arr({"type": "object"}),
            "visual_contract": {"type": "object"},
            "style_contract": {"type": "object"},
            "creative_variants_used": {"type": "object"},
            "clips": arr(obj(("id", "duration", "continuity"), {
                "id": {"type": "string"},
                "label": {"type": "string"},
                "duration": {"type": "number"},
                "scene": {"type": "string"},
                "rhythm": {"type": "string"},
                "template": {"type": "string"},
                "template_contract": {"type": "object"},
                "entity_schedule": {"type": "object"},
                "continuity": {"type": "object"},
                "shots": arr({"type": "object"}),
            })),
        },
    ),
    ARTIFACT_LINEAGE_MANIFEST_KIND: obj(
        ("kind", "version", "root", "episode", "files", "summary", "status"),
        {
            "kind": {"type": "string", "enum": [ARTIFACT_LINEAGE_MANIFEST_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "episode": {"type": "string"},
            "files": arr(obj(("role", "path", "exists", "sha256"), {
                "role": {"type": "string"},
                "path": {"type": "string"},
                "exists": {"type": "boolean"},
                "sha256": {"type": "string"},
                "required": {"type": "boolean"},
            })),
            "summary": {"type": "object"},
            "trace": {"type": "object"},
            "status": {"type": "string"},
        },
    ),
    PRODUCTION_READINESS_KIND: obj(
        ("kind", "version", "root", "episode", "checks", "summary", "status"),
        {
            "kind": {"type": "string", "enum": [PRODUCTION_READINESS_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "episode": {"type": "string"},
            "profile": {"type": "string"},
            "checks": arr(obj(("name", "status"), {
                "name": {"type": "string"},
                "status": {"type": "string"},
                "message": {"type": "string"},
            })),
            "summary": {"type": "object"},
            "status": {"type": "string"},
        },
    ),
    GATE_POLICY_COVERAGE_KIND: obj(
        ("kind", "version", "root", "episode", "matrix", "groups", "summary", "status"),
        {
            "kind": {"type": "string", "enum": [GATE_POLICY_COVERAGE_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "episode": {"type": "string"},
            "matrix": {"type": "object"},
            "groups": arr({"type": "object"}),
            "summary": {"type": "object"},
            "status": {"type": "string"},
        },
    ),
    GENERATION_RECIPE_MANIFEST_KIND: obj(
        ("kind", "version", "root", "episode", "records", "summary", "status"),
        {
            "kind": {"type": "string", "enum": [GENERATION_RECIPE_MANIFEST_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "episode": {"type": "string"},
            "records": arr({"type": "object"}),
            "summary": {"type": "object"},
            "status": {"type": "string"},
        },
    ),
    GENRE_PACK_KIND: obj(
        ("kind", "version", "genre_key", "label", "scene_archetypes", "qc_focus"),
        {
            "kind": {"type": "string", "enum": [GENRE_PACK_KIND]},
            "version": {"type": "integer"},
            "genre_key": {"type": "string"},
            "label": {"type": "string"},
            "aliases": arr({"type": "string"}),
            "scene_archetypes": arr({"type": "object"}),
            "motion_contract_fields": arr({"type": "string"}),
            "qc_focus": arr({"type": "string"}),
            "style_binding_policy": {"type": "object"},
        },
    ),
    GENRE_PACK_CONTEXT_KIND: obj(
        ("kind", "version", "root", "episode", "stage_key", "genre", "pack", "summary", "status"),
        {
            "kind": {"type": "string", "enum": [GENRE_PACK_CONTEXT_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "episode": {"type": "string"},
            "stage_key": {"type": "string"},
            "genre": {"type": "object"},
            "pack": {"type": "object"},
            "activation": {"type": "object"},
            "active_scene_archetypes": arr({"type": "object"}),
            "issues": arr({"type": "object"}),
            "summary": {"type": "object"},
            "status": {"type": "string"},
        },
    ),
    ARTIFACT_VALIDATION_KIND: obj(
        (
            "kind", "version", "root", "scope", "strict_unknown", "completion_inputs_only", "schema_registry",
            "source", "discovered_count", "scanned_count", "skipped_count",
            "scanned", "skipped", "summary", "status", "checked", "issues",
            "content_sha256",
        ),
        {
            "kind": {"type": "string", "enum": [ARTIFACT_VALIDATION_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "scope": {"type": "string", "enum": list(SCAN_SCOPES)},
            "strict_unknown": {"type": "boolean"},
            "completion_inputs_only": {"type": "boolean"},
            "schema_registry": {"type": "object"},
            "source": {"type": "object"},
            "discovered_count": {"type": "integer"},
            "scanned_count": {"type": "integer"},
            "skipped_count": {"type": "integer"},
            "scanned": arr({"type": "object"}),
            "skipped": arr({"type": "object"}),
            "summary": {"type": "object"},
            "status": {"type": "string"},
            "checked": arr({"type": "object"}),
            "issues": arr({"type": "object"}),
            "content_sha256": {"type": "string"},
        },
    ),
}


def schema_registry_payload() -> Dict[str, Any]:
    return {
        "kind": SCHEMA_REGISTRY_KIND,
        "version": SCHEMA_VERSION,
        "schemas": sorted(SCHEMAS),
        "boundary_product_kinds": sorted(BOUNDARY_PRODUCT_KINDS),
        "rule": "validate routable/auditable machine-contract fields; stage business rules stay in gates",
    }


def validate_payload(payload: Any, *, expected_kind: str = "", source: str = "") -> List[Dict[str, Any]]:
    source = source or "<memory>"
    if not isinstance(payload, dict):
        return [issue("block", source, "artifact must be a JSON object", kind=expected_kind)]
    kind = str(expected_kind or payload.get("kind") or "")
    if not kind:
        return [issue("block", source, "missing `kind`; cannot route artifact to schema")]
    if expected_kind and payload.get("kind") != expected_kind:
        return [issue("block", source, f"kind mismatch: expected {expected_kind}, got {payload.get('kind')!r}", kind=expected_kind)]
    schema = SCHEMAS.get(kind)
    if not schema:
        identity_issues = _validate_routable_identity(payload, source=source, kind=kind)
        # Boundary kinds are registered machine contracts even when they only
        # have the common routing envelope here.  Unknown self-declared kinds
        # remain informational by default and become blocking in strict scans.
        if kind in BOUNDARY_PRODUCT_KINDS or kind in _BOUNDARY_ALIAS_TO_CANONICAL:
            return identity_issues
        identity_issues.append(issue("info", source, f"no schema registered for kind `{kind}`", kind=kind))
        return identity_issues
    return _validate(payload, schema, source=source, kind=kind)


def _validate_routable_identity(payload: Dict[str, Any], *, source: str, kind: str) -> List[Dict[str, Any]]:
    """Validate the common envelope for a registered boundary-only kind."""

    issues: List[Dict[str, Any]] = []
    if not isinstance(payload.get("kind"), str) or not str(payload.get("kind") or "").strip():
        issues.append(issue("block", source, "`kind` must be a non-empty string", pointer="$.kind", kind=kind))
    present = [field for field in VERSION_FIELDS if field in payload]
    if not present:
        issues.append(
            issue(
                "block",
                source,
                "missing artifact version; expected one of `version`, `schema_version`, `contract_version`",
                pointer="$.version",
                kind=kind,
            )
        )
    else:
        for field in present:
            if not _type_ok(payload.get(field), "integer"):
                issues.append(issue("block", source, "expected integer version", pointer=f"$.{field}", kind=kind))
    return issues


def validate_json_file(path: Path, *, expected_kind: str = "") -> List[Dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [issue("block", str(path), f"invalid JSON: {exc}", kind=expected_kind)]
    return validate_payload(payload, expected_kind=expected_kind, source=str(path))


def validate_jsonl_file(path: Path, *, expected_kind: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        return [issue("block", str(path), f"cannot read JSONL: {exc}", kind=expected_kind)]
    for idx, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except Exception as exc:
            out.append(issue("block", str(path), f"line {idx}: invalid JSON: {exc}", pointer=f"$[{idx}]", kind=expected_kind))
            continue
        out.extend(validate_payload(payload, expected_kind=expected_kind, source=f"{path}:{idx}"))
    return out


def _template_pattern(template: str) -> re.Pattern[str]:
    parts = re.split(r"(\{[^{}]+\})", template.strip("/"))
    pattern_parts: List[str] = []
    for part in parts:
        if part.startswith("{") and part.endswith("}"):
            placeholder = part[1:-1]
            # n2d normalizes episode directories/file suffixes to 第N集.  A
            # generic ``[^/]+`` here would falsely classify names such as
            # review_ui_findings_第1集.json as review_ui_{ep}.json.
            pattern_parts.append(r"第[^/]+集" if placeholder == "ep" else r"[^/]+")
        else:
            pattern_parts.append(re.escape(part))
    pattern = "".join(pattern_parts)
    return re.compile(rf"^{pattern}$")


_BOUNDARY_PATH_PATTERNS = tuple(
    (kind, _template_pattern(str(meta.get("path") or "")))
    for kind, meta in BOUNDARY_PRODUCT_KINDS.items()
    if str(meta.get("path") or "").endswith(".json")
)


def _relative_posix(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def _boundary_kind(relative_path: str) -> str:
    for kind, pattern in _BOUNDARY_PATH_PATTERNS:
        if pattern.fullmatch(relative_path):
            return str(kind)
    return ""


def classify_artifact(root: Path, path: Path, payload: Any = None, *, parse_error: str = "") -> Dict[str, Any]:
    """Classify one JSON candidate without inferring a contract from its suffix.

    The returned reason is stable machine output, so callers can distinguish a
    true contract from cache/config/view/support data without parsing prose.
    """

    relative_path = _relative_posix(root, path)
    expected_kind = _boundary_kind(relative_path)
    if expected_kind:
        return {
            "routable": True,
            "reason": "boundary_registry_path",
            "expected_kind": expected_kind,
            "accepted_kind_aliases": list(BOUNDARY_KIND_ALIASES.get(expected_kind, ())),
            "relative_path": relative_path,
        }
    if "manifest" in path.stem.casefold():
        return {
            "routable": True,
            "reason": "manifest_file",
            "expected_kind": "",
            "relative_path": relative_path,
        }
    if isinstance(payload, dict) and str(payload.get("kind") or "").strip():
        return {
            "routable": True,
            "reason": "declared_kind",
            "expected_kind": "",
            "relative_path": relative_path,
        }

    name = path.name.casefold()
    stem = path.stem.casefold()
    parts = {part.casefold() for part in path.parts}
    if ".tmp." in name or name.endswith(".tmp"):
        reason = "temporary_json"
    elif name.startswith(".prework_cache_") or name.startswith("prework_cache_"):
        reason = "prework_cache"
    elif path.name == "_源指纹.json" or stem in {"source_fingerprint", "_source_fingerprint"}:
        reason = "source_fingerprint"
    elif "embedding" in stem or stem.endswith("_ep_means"):
        reason = "embedding_support"
    elif "views" in parts or "view" in parts:
        reason = "view_json"
    elif stem in {"config", "settings", "配置", "设置"} or stem.endswith("_config") or stem.endswith("_settings"):
        reason = "config_json"
    elif isinstance(payload, list):
        reason = "list_support"
    elif parse_error:
        reason = "unroutable_invalid_json"
    elif isinstance(payload, dict):
        reason = "support_json"
    else:
        reason = "scalar_support"
    return {
        "routable": False,
        "reason": reason,
        "expected_kind": "",
        "relative_path": relative_path,
    }


def _scan_row(path: Path, *, fmt: str, kind: str, issue_count: int, classification: Dict[str, Any]) -> Dict[str, Any]:
    h = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        digest = h.hexdigest()
        size = path.stat().st_size
    except OSError:
        digest = ""
        size = 0
    return {
        "path": str(path),
        "relative_path": classification.get("relative_path") or "",
        "kind": kind,
        "format": fmt,
        "sha256": digest,
        "bytes": size,
        "issues": issue_count,
        "classification": classification,
        "classifier_reason": classification.get("reason") or "",
    }


def _skip_row(path: Path, *, fmt: str, classification: Dict[str, Any], code: str = "", detail: str = "") -> Dict[str, Any]:
    skip_code = code or str(classification.get("reason") or "support_json")
    return {
        "path": str(path),
        "relative_path": classification.get("relative_path") or "",
        "format": fmt,
        "classification": classification,
        "classifier_reason": classification.get("reason") or "",
        "skip_reason": {"code": skip_code, "detail": detail},
    }


def _strict_unknown_issues(items: List[Dict[str, Any]], *, strict_unknown: bool) -> None:
    if not strict_unknown:
        return
    for item in items:
        if item.get("severity") == "info" and "no schema registered" in str(item.get("message")):
            item["severity"] = "block"


def scan_artifacts(
    root: str,
    *,
    strict_unknown: bool = False,
    scope: str = SCAN_SCOPE_ALL,
    completion_inputs_only: bool = False,
) -> Dict[str, Any]:
    if scope not in SCAN_SCOPES:
        raise ValueError(f"unsupported artifact scan scope: {scope!r}; expected one of {SCAN_SCOPES!r}")
    root_path = Path(root).resolve()
    issues: List[Dict[str, Any]] = []
    scanned: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    if not root_path.exists():
        issues.append(issue("block", root, "作品根不存在"))
        return _scan_payload(
            root, scanned, skipped, issues, scope=scope, strict_unknown=strict_unknown,
            completion_inputs_only=completion_inputs_only,
        )

    for filename, expected_kind in EVENT_STREAM_KINDS.items():
        path = root_path / production_dir("") / filename
        if not path.is_file():
            continue
        classification = {
            "routable": True,
            "reason": "boundary_event_stream",
            "expected_kind": expected_kind,
            "relative_path": _relative_posix(root_path, path),
        }
        file_issues = validate_jsonl_file(path, expected_kind=expected_kind)
        _strict_unknown_issues(file_issues, strict_unknown=strict_unknown)
        issues.extend(file_issues)
        scanned.append(_scan_row(path, fmt="jsonl", kind=expected_kind, issue_count=len(file_issues), classification=classification))

    for path in sorted(root_path.rglob("*.json")):
        # The report must be reproducible after it is written.  Scanning its own
        # previous bytes or completion outputs written after this preflight
        # would create an unavoidable cycle.  Those downstream products have
        # their own canonical validators and cannot be inputs to this report.
        relative_path = _relative_posix(root_path, path)
        completion_output = (
            relative_path == f"{production_dir('')}/artifact_validation.json"
            or re.fullmatch(rf"{re.escape(production_dir(''))}/(?:release_verdict|acceptance_receipt|artifact_lineage)_.+\.json", relative_path)
            or re.fullmatch(rf"{re.escape(production_dir(''))}/production_readiness(?:_.+)?\.json", relative_path)
            or re.fullmatch(r"合规/release_manifest_.+\.json", relative_path)
        )
        if completion_inputs_only and completion_output:
            continue
        payload: Any = None
        parse_error = ""
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            parse_error = f"{type(exc).__name__}: {exc}"
        classification = classify_artifact(root_path, path, payload, parse_error=parse_error)
        release_selected = classification.get("reason") in {"boundary_registry_path", "manifest_file"}
        if not classification.get("routable"):
            skipped.append(_skip_row(path, fmt="json", classification=classification, detail=parse_error))
            continue
        if scope == SCAN_SCOPE_RELEASE and not release_selected:
            skipped.append(
                _skip_row(
                    path,
                    fmt="json",
                    classification=classification,
                    code="outside_release_boundary",
                    detail="self-declared artifact is routable but is not a canonical boundary path or manifest file",
                )
            )
            continue
        expected_kind = str(classification.get("expected_kind") or "")
        if parse_error:
            file_issues = [issue("block", str(path), f"invalid JSON: {parse_error}", kind=expected_kind)]
        else:
            legacy = _validate_explicit_legacy_boundary(
                payload,
                expected_kind=expected_kind,
                source=str(path),
            ) if expected_kind else None
            if legacy is not None:
                file_issues, migration = legacy
                classification["legacy_migration"] = migration
            else:
                actual_kind = str(payload.get("kind") or "") if isinstance(payload, dict) else ""
                accepted_aliases = set(classification.get("accepted_kind_aliases") or [])
                if expected_kind and actual_kind in accepted_aliases:
                    file_issues = validate_payload(payload, source=str(path))
                else:
                    file_issues = validate_payload(payload, expected_kind=expected_kind, source=str(path))
        _strict_unknown_issues(file_issues, strict_unknown=strict_unknown)
        issues.extend(file_issues)
        kind = str(payload.get("kind") or "") if isinstance(payload, dict) else ""
        scanned.append(_scan_row(path, fmt="json", kind=kind, issue_count=len(file_issues), classification=classification))
    return _scan_payload(
        root, scanned, skipped, issues, scope=scope, strict_unknown=strict_unknown,
        completion_inputs_only=completion_inputs_only,
    )


def _scan_payload(
    root: str,
    scanned: List[Dict[str, Any]],
    skipped: List[Dict[str, Any]],
    issues: List[Dict[str, Any]],
    *,
    scope: str,
    strict_unknown: bool,
    completion_inputs_only: bool,
) -> Dict[str, Any]:
    counts: Dict[str, int] = {"block": 0, "warn": 0, "info": 0}
    for item in issues:
        sev = str(item.get("severity") or "warn")
        counts[sev] = counts.get(sev, 0) + 1
    resolved_root = str(Path(root).resolve())
    evidence_rows = [
        {
            "relative_path": str(row.get("relative_path") or ""),
            "format": str(row.get("format") or ""),
            "kind": str(row.get("kind") or ""),
            "sha256": str(row.get("sha256") or ""),
            "bytes": int(row.get("bytes") or 0),
        }
        for row in scanned
    ]
    source = {
        "kind": "n2d_artifact_validation_source",
        "version": 1,
        "scope": scope,
        "strict_unknown": strict_unknown,
        "completion_inputs_only": completion_inputs_only,
        "evidence_sha256": hashlib.sha256(
            json.dumps(evidence_rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }
    payload = {
        "kind": ARTIFACT_VALIDATION_KIND,
        "version": 1,
        "root": resolved_root,
        "scope": scope,
        "strict_unknown": strict_unknown,
        "completion_inputs_only": completion_inputs_only,
        "source": source,
        "schema_registry": schema_registry_payload(),
        "discovered_count": len(scanned) + len(skipped),
        "scanned_count": len(scanned),
        "skipped_count": len(skipped),
        "scanned": scanned,
        "skipped": skipped,
        # Backward-compatible aliases for existing report consumers.
        "checked_count": len(scanned),
        "checked": scanned,
        "issues": issues,
        "summary": counts,
        "status": "fail" if counts.get("block") else ("warn" if counts.get("warn") else "pass"),
    }
    payload["content_sha256"] = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def render_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# n2d Artifact Validation",
        "",
        f"- 状态：{payload.get('status')}",
        f"- 扫描范围：{payload.get('scope', SCAN_SCOPE_ALL)}",
        f"- 已发现：{payload.get('discovered_count', payload.get('checked_count', 0))}",
        f"- 已严格扫描：{payload.get('scanned_count', payload.get('checked_count', 0))}",
        f"- 已跳过：{payload.get('skipped_count', 0)}",
        f"- block：{(payload.get('summary') or {}).get('block', 0)}",
        f"- warn：{(payload.get('summary') or {}).get('warn', 0)}",
        "",
        "## Issues",
        "",
    ]
    issues = payload.get("issues") or []
    if not issues:
        lines.append("- 无")
    else:
        for item in issues[:80]:
            lines.append(
                f"- {item.get('severity')} `{item.get('kind') or '-'}` {item.get('source')} {item.get('pointer')}: {item.get('message')}"
            )
    skipped = payload.get("skipped") or []
    lines.extend(["", "## Skipped", ""])
    if not skipped:
        lines.append("- 无")
    else:
        reason_counts: Dict[str, int] = {}
        for item in skipped:
            code = str((item.get("skip_reason") or {}).get("code") or "unknown")
            reason_counts[code] = reason_counts.get(code, 0) + 1
        for code, count in sorted(reason_counts.items()):
            lines.append(f"- `{code}`: {count}")
    lines.append("")
    return "\n".join(lines)


def write_validation(root: str, payload: Dict[str, Any]) -> Dict[str, str]:
    out_dir = Path(root) / production_dir("")
    out_dir.mkdir(parents=True, exist_ok=True)
    path_json = out_dir / "artifact_validation.json"
    path_md = out_dir / "artifact_validation.md"
    path_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path_md.write_text(render_markdown(payload), encoding="utf-8")
    return {"json": str(path_json), "markdown": str(path_md)}
