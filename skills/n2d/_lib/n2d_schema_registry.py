#!/usr/bin/env python3
"""Lightweight schema registry for n2d machine artifacts.

This is intentionally smaller than full JSON Schema.  It validates the contract
fields that make artifacts routable and auditable: kind, version, ownership
fields, trace fields and high-level arrays.  Stage-specific business checks stay
in gate/review scripts.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from n2d_const import (
        ARTIFACT_LINEAGE_MANIFEST_KIND,
        BATCH_QUEUE_KIND,
        COMPLIANCE_MANIFEST_KIND,
        CONSISTENCY_FINDINGS_KIND,
        GATE_POLICY_COVERAGE_KIND,
        GENERATION_RECIPE_MANIFEST_KIND,
        GENRE_PACK_CONTEXT_KIND,
        GENRE_PACK_KIND,
        IDENTITY_REGISTRY_KIND,
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
except ImportError:  # pragma: no cover - package import fallback
    from .n2d_const import (
        ARTIFACT_LINEAGE_MANIFEST_KIND,
        BATCH_QUEUE_KIND,
        COMPLIANCE_MANIFEST_KIND,
        CONSISTENCY_FINDINGS_KIND,
        GATE_POLICY_COVERAGE_KIND,
        GENERATION_RECIPE_MANIFEST_KIND,
        GENRE_PACK_CONTEXT_KIND,
        GENRE_PACK_KIND,
        IDENTITY_REGISTRY_KIND,
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
PRODUCTION_MODE_ROUTE_KIND = "n2d_production_mode_route"
EDITORIAL_TIMELINE_KIND = "n2d_editorial_timeline"
VOICE_CASTING_KIND = "n2d_voice_casting"
TIMING_ESTIMATE_KIND = "n2d_timing_estimate"
SHOT_TIMING_BASIS_KIND = "n2d_shot_timing_basis"
SCHEMA_VERSION = 1
NON_ROUTABLE_JSON_FILENAMES = {"镜头时长.json"}

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
            "stop_reason": {"type": "string"},
            "category": {"type": "string"},
            "blocked": {"type": "boolean"},
            "blockers": arr({"type": "object"}),
            "repair_commands": arr({"type": "string"}),
            "gate": {"type": "object"},
            "episode_graph": {"type": "object"},
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
            "active_scene_archetypes": arr({"type": "object"}),
            "issues": arr({"type": "object"}),
            "summary": {"type": "object"},
            "status": {"type": "string"},
        },
    ),
    ARTIFACT_VALIDATION_KIND: obj(
        ("kind", "version", "root", "summary", "checked", "issues"),
        {
            "kind": {"type": "string", "enum": [ARTIFACT_VALIDATION_KIND]},
            "version": {"type": "integer"},
            "root": {"type": "string"},
            "summary": {"type": "object"},
            "checked": arr({"type": "object"}),
            "issues": arr({"type": "object"}),
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
        return [issue("info", source, f"no schema registered for kind `{kind}`", kind=kind)]
    return _validate(payload, schema, source=source, kind=kind)


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


def scan_artifacts(root: str, *, strict_unknown: bool = False) -> Dict[str, Any]:
    root_path = Path(root)
    issues: List[Dict[str, Any]] = []
    checked: List[Dict[str, Any]] = []
    if not root_path.exists():
        issues.append(issue("block", root, "作品根不存在"))
        return _scan_payload(root, checked, issues)

    events = root_path / production_dir("") / "production_events.jsonl"
    if events.is_file():
        ev_issues = validate_jsonl_file(events, expected_kind=PRODUCTION_EVENT_KIND)
        issues.extend(ev_issues)
        checked.append({"path": str(events), "kind": PRODUCTION_EVENT_KIND, "format": "jsonl", "issues": len(ev_issues)})

    flow_events = root_path / production_dir("") / "flow_events.jsonl"
    if flow_events.is_file():
        flow_issues = validate_jsonl_file(flow_events, expected_kind=FLOW_EVENT_KIND)
        issues.extend(flow_issues)
        checked.append({"path": str(flow_events), "kind": FLOW_EVENT_KIND, "format": "jsonl", "issues": len(flow_issues)})

    for path in sorted(root_path.rglob("*.json")):
        if ".tmp." in path.name or path.name.endswith(".tmp"):
            continue
        if path.name == "production_events.jsonl":
            continue
        if path.name in NON_ROUTABLE_JSON_FILENAMES:
            checked.append({"path": str(path), "kind": "non_routable_json", "format": "json", "issues": 0})
            continue
        file_issues = validate_json_file(path)
        if strict_unknown:
            for item in file_issues:
                if item.get("severity") == "info" and "no schema registered" in str(item.get("message")):
                    item["severity"] = "block"
        issues.extend(file_issues)
        kind = ""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                kind = str(data.get("kind") or "")
        except Exception:
            pass
        checked.append({"path": str(path), "kind": kind, "format": "json", "issues": len(file_issues)})
    return _scan_payload(root, checked, issues)


def _scan_payload(root: str, checked: List[Dict[str, Any]], issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {"block": 0, "warn": 0, "info": 0}
    for item in issues:
        sev = str(item.get("severity") or "warn")
        counts[sev] = counts.get(sev, 0) + 1
    return {
        "kind": ARTIFACT_VALIDATION_KIND,
        "version": 1,
        "root": root,
        "schema_registry": schema_registry_payload(),
        "checked_count": len(checked),
        "checked": checked,
        "issues": issues,
        "summary": counts,
        "status": "fail" if counts.get("block") else ("warn" if counts.get("warn") else "pass"),
    }


def render_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# n2d Artifact Validation",
        "",
        f"- 状态：{payload.get('status')}",
        f"- 检查文件：{payload.get('checked_count')}",
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
