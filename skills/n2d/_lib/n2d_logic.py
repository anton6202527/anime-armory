#!/usr/bin/env python3
"""Normalization and classification logic for the n2d pipeline."""

from __future__ import annotations
import hashlib
import re
from typing import Dict, List, Any, Optional, Tuple

try:
    from n2d_const import *
    from n2d_schema import *
except ImportError:
    from .n2d_const import *
    from .n2d_schema import *

def classify_redraw_reason(text: str) -> str:
    """Classify a raw redraw reason into standard dimensions."""
    t = str(text or "").lower().strip()
    if not t:
        return "other"
    for dim, keywords in REDRAW_REASON_KEYWORDS:
        if any(kw in t for kw in keywords):
            return dim
    return "other"

def normalize_precision(result: Any) -> str:
    """Normalize detector precision signals into (full, degraded, none)."""
    if isinstance(result, dict):
        if result.get("available") is False:
            return PRECISION_NONE
        return PRECISION_ALIASES.get(str(result.get("precision") or "").strip().lower(), PRECISION_FULL)
    return PRECISION_ALIASES.get(str(result or "").strip().lower(), PRECISION_NONE)

def is_native_av_mode(mode: Any) -> bool:
    """Check if the production mode is Native A/V."""
    m = str(mode or "").strip().lower()
    return "原生音画" in m or "native_av" in m

def production_mode_keys() -> Tuple[str, ...]:
    """Return valid production mode keys in order."""
    return ("配音先行", "先出视频后配音", "原生音画")

def normalize_production_mode(value: Any) -> str:
    """Normalize a production mode value."""
    v = str(value or "").strip()
    keys = production_mode_keys()
    for k in keys:
        if v == k:
            return k
    if "原生" in v or "native" in v.lower():
        return "原生音画"
    if "视频" in v and "配音" in v:
        return "先出视频后配音"
    return PRODUCTION_MODE_DEFAULT

def classify_image_backend(text: str) -> Tuple[str, str]:
    """Classify image backend into canonical name and status (approved/unknown)."""
    t = str(text or "").lower().strip()
    if not t:
        return ("", "unknown")
    compact = re.sub(r"\s+", "", t)
    if any(str(kw).lower().replace(" ", "") in compact for kw in FORBIDDEN_IMAGE_BACKEND_KEYWORDS):
        return ("", "forbidden")
    for alias, canonical_key in IMAGE_BACKEND_ALIASES.items():
        if alias in t:
            return (APPROVED_IMAGE_BACKENDS[canonical_key]["canonical"], "approved")
    return ("", "unknown")

def image_identity_profile(backend: str) -> Dict[str, Any]:
    """Return image identity capability profile for a backend canonical/raw value."""
    canonical, kind = classify_image_backend(backend)
    key = canonical if kind == "approved" else str(backend or "").strip().lower()
    profile = IMAGE_IDENTITY_PROFILES.get(key)
    if isinstance(profile, dict):
        out = dict(profile)
        out["canonical"] = key
        return out
    return {
        "canonical": key or "",
        "label": key or "unknown",
        "persistent_subject": False,
        "multi_reference": False,
        "strategy": "reference_group",
        "max_reference_images": None,
        "native_modes": (),
        "notes": "未知图后端；按 reference_group 兜底并要求人工确认。",
    }

def image_backend_supports_persistent_subject(backend: str) -> bool:
    """Whether the image backend has a reusable native subject/character ID layer."""
    return bool(image_identity_profile(backend).get("persistent_subject"))

def image_lock_tier(
    backend: str,
    image_adapters: Optional[Dict[str, Any]] = None,
    lora: Optional[Dict[str, Any]] = None,
) -> str:
    """Classify the effective image identity lock tier for one character form.

    Return values, weakest to strongest:
      reference_group      unknown/single-reference fallback only
      multi_reference      multiple references or image-to-image, no persistent subject ID
      native_unregistered  backend has persistent subject ability, but this form is not registered
      native_subject       backend subject/character binding is registered or ready
      lora                 LoRA ready/training, strongest identity lock
    """
    if str((lora or {}).get("status") or "").strip() in {"ready", "training"}:
        return "lora"
    profile = image_identity_profile(backend)
    canonical = str(profile.get("canonical") or "")
    adapters = image_adapters or {}
    entry = adapters.get(canonical)
    status = str(entry.get("status") if isinstance(entry, dict) else entry or "").strip()
    if bool(profile.get("persistent_subject")):
        return "native_subject" if status in {"registered", "ready"} else "native_unregistered"
    if bool(profile.get("multi_reference")):
        return "multi_reference"
    return "reference_group"

def motion_control_required(shot_type: Optional[str] = None, risk_flags: Optional[List[str]] = None) -> bool:
    """Determine if a shot requires motion control based on type or risk flags."""
    from n2d_schema import MOTION_CONTROL_REQUIRED_SHOT_TYPES, MOTION_CONTROL_RISK_FLAGS
    if str(shot_type or "").strip() in MOTION_CONTROL_REQUIRED_SHOT_TYPES:
        return True
    if risk_flags:
        return any(f in MOTION_CONTROL_RISK_FLAGS for f in risk_flags)
    return False

def lora_verdict_ok(verdict: Any) -> bool:
    """Check if a LoRA validation verdict is acceptable for ready status."""
    return str(verdict or "").strip() in ("pass",)

def lora_dataset_warning_blocks(report: Dict[str, Any]) -> List[str]:
    """Identify dataset warnings that require manual override."""
    warnings = report.get("warnings") if isinstance(report.get("warnings"), list) else []
    if "dataset_has_warnings" not in warnings:
        return []
    manual_review = report.get("manual_review", {})
    if not isinstance(manual_review, dict):
        manual_review = {}
    if not manual_review.get("allow_dataset_warnings"):
        return ["dataset_warnings_without_override"]
    if not str(manual_review.get("notes") or "").strip():
        return ["dataset_warnings_override_notes_missing"]
    return []

def lora_report_ready_blocks(report: Dict[str, Any]) -> List[str]:
    """Check if a validation report supports ready status."""
    blocks: List[str] = []
    if not lora_verdict_ok(report.get("verdict")):
        blocks.append(f"validation_verdict_not_pass:{str(report.get('verdict') or '').strip() or 'missing'}")
    
    # Required fields for report
    required = ("base_model", "model_path", "trigger", "model_sha256")
    for key in required:
        if not str(report.get(key, "") or "").strip():
            blocks.append(f"missing_report_field:{key}")
    blocks.extend(lora_dataset_warning_blocks(report))
    return blocks

def lora_registry_ready_blocks(cfg: Dict[str, Any], report: Optional[Dict[str, Any]]) -> List[str]:
    """Check if a registry entry supports ready status."""
    blocks: List[str] = []
    # Required fields for registry
    required = ("base_model", "model_path", "trigger", "validation_report", "model_hash")
    for key in required:
        if not str(cfg.get(key, "") or "").strip():
            blocks.append(f"ready_missing_{key}")
    
    if not str(cfg.get("validation_report", "") or "").strip():
        return blocks
    
    if not isinstance(report, dict):
        blocks.append("ready_validation_report_missing")
        return blocks
    
    if report.get("kind") != LORA_VALIDATION_REPORT_KIND:
        blocks.append("ready_validation_report_kind_invalid")
    if not lora_verdict_ok(report.get("verdict")):
        blocks.append("ready_validation_report_not_pass")
        
    report_hash = str(report.get("model_sha256", "") or "").strip()
    registry_hash = str(cfg.get("model_hash", "") or "").strip()
    if report_hash and registry_hash and report_hash != registry_hash:
        blocks.append("ready_model_hash_mismatch")
        
    blocks.extend(f"ready_{b}" for b in lora_dataset_warning_blocks(report))
    return blocks

def lora_gap_message(code: str) -> str:
    """Map LoRA gap codes to human-readable Chinese messages."""
    messages = {
        "ready_validation_report_missing": "LoRA validation_report 缺失或无法解析",
        "ready_validation_report_kind_invalid": "LoRA validation_report kind 不正确",
        "ready_validation_report_not_pass": "LoRA ready 必须对应 verdict=pass 的验证报告",
        "ready_model_hash_mismatch": "registry model_hash 与 validation_report.model_sha256 不一致",
        "ready_model_path_missing": "LoRA ready 的 model_path 不存在",
        "ready_dataset_warnings_without_override": "LoRA 数据集有 warning，但验证报告缺 allow_dataset_warnings 显式放行",
        "ready_dataset_warnings_override_notes_missing": "LoRA 数据集 warning 被人工放行时，manual_review.notes 必须写明原因",
    }
    if code.startswith("ready_missing_"):
        return f"LoRA ready 但缺字段：{code[len('ready_missing_'):]}"
    return messages.get(code, f"LoRA ready 缺口：{code}")

def _fingerprint_episode(episode: Any) -> str:
    s = str(episode or "").strip()
    digits = "".join(ch for ch in s if ch.isdigit())
    return str(int(digits)) if digits else s.lower()

_SHOT_TOKEN_RE = re.compile(r"(?:clip|shot|镜头)[\s_\-#]*0*(\d+)", re.IGNORECASE)

def canonical_scope_key(scope: Any) -> str:
    s = str(scope or "").strip()
    if not s:
        return ""
    m = _SHOT_TOKEN_RE.search(s)
    if m:
        return f"clip_{int(m.group(1))}"
    return s.lower()

def finding_fingerprint(episode: Any, stage: Any, dim: Any, scope: Any = "") -> str:
    key_parts = [
        _fingerprint_episode(episode),
        str(stage or "").strip().lower(),
        str(dim or "").strip().lower(),
    ]
    scope_s = canonical_scope_key(scope)
    if scope_s:
        key_parts.append(scope_s)
    key = "|".join(key_parts)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

_DIM_KEY_BY_LABEL = {spec["label"]: key for key, spec in CONSISTENCY_DIMENSIONS.items()}

def resolve_dim_key(dim: Any) -> str:
    d = str(dim or "").strip()
    if not d:
        return ""
    if d in CONSISTENCY_DIMENSIONS:
        return d
    if d in _DIM_KEY_BY_LABEL:
        return _DIM_KEY_BY_LABEL[d]
    for key, spec in CONSISTENCY_DIMENSIONS.items():
        if any(kw and kw in d for kw in spec.get("keywords", ())):
            return key
    return ""

def normalize_finding(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    severity = str(raw.get("severity") or raw.get("sev") or raw.get("verdict") or "").strip().lower()
    dim = raw.get("dimension") or raw.get("dim") or ""
    if not dim:
        dims = raw.get("dimensions")
        if isinstance(dims, list) and dims:
            dim = dims[0]
    dim_key = str(raw.get("dim_key") or "").strip() or resolve_dim_key(dim)
    stage = str(raw.get("return_to_stage") or raw.get("rerun_from") or "").strip()
    if not stage and dim_key in CONSISTENCY_DIMENSIONS:
        stage = str(CONSISTENCY_DIMENSIONS[dim_key].get("return_to_stage") or "")
    return {
        "severity": severity,
        "dimension": str(dim or "").strip(),
        "dim_key": dim_key,
        "message": str(raw.get("message") or raw.get("msg") or "").strip(),
        "return_to_stage": stage,
        "rerun_scope": str(raw.get("rerun_scope") or raw.get("scope") or "").strip(),
        "loc": str(raw.get("loc") or "").strip(),
        "shot": str(raw.get("shot") or "").strip(),
        "affected_shots": [str(s) for s in (raw.get("affected_shots") or []) if str(s).strip()],
        "affected_artifacts": [str(a) for a in (raw.get("affected_artifacts") or []) if str(a).strip()],
    }

def identity_allowed_modes(adapters: Dict[str, Dict[str, object]]) -> Dict[str, tuple]:
    """Extract allowed modes for each backend in identity_adapters."""
    out = {}
    for backend, cfg in adapters.items():
        allowed = cfg.get("allowed_modes")
        if isinstance(allowed, (list, tuple)):
            out[backend] = tuple(allowed)
    return out

def identity_reset_template(adapters: Dict[str, Dict[str, object]]) -> Dict[str, Dict[str, str]]:
    """Generate a fresh registry template for identity_adapters."""
    out = {}
    for backend, cfg in adapters.items():
        out[backend] = {
            "status": str(cfg.get("default_status") or "unregistered"),
            "mode": str(cfg.get("default_mode") or ""),
            "handle": "",
        }
    return out

def product_kind(kind: str) -> Optional[Dict[str, str]]:
    """Return metadata for a product kind."""
    return BOUNDARY_PRODUCT_KINDS.get(kind)

def consistency_dimensions() -> Dict[str, Dict[str, Any]]:
    """Return consistency dimension metadata."""
    return {key: dict(spec) for key, spec in CONSISTENCY_DIMENSIONS.items()}

def consistency_dim_key(value: Any) -> Optional[str]:
    """Resolve a dimension key from a value."""
    return resolve_dim_key(value)

def consistency_dim_spec(value: Any) -> Optional[Dict[str, Any]]:
    """Resolve a dimension spec from a value."""
    key = resolve_dim_key(value)
    return CONSISTENCY_DIMENSIONS.get(key) if key else None

def stage_specs() -> List[Dict[str, Any]]:
    """Return all stage definitions."""
    return [dict(spec) for spec in STAGE_GRAPH]

def cross_cutting() -> List[Dict[str, Any]]:
    """Return readiness-tracked cross-cutting tools."""
    return [dict(item) for item in READINESS_TRACKED_SKILLS]

def cross_cutting_tools() -> List[Dict[str, Any]]:
    """Return optional/observability cross-cutting tools."""
    return [dict(item) for item in CROSS_CUTTING_TOOLS]

def special_template_keywords() -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    """Return shot-type keyword tuples for special-template detection."""
    return tuple((key, tuple(words)) for key, words in SHOT_TYPE_KEYWORDS if key in SPECIAL_TEMPLATE_SHOT_TYPES)

def routing_stages() -> List[Tuple[List[str], str, str, str]]:
    """Return legacy n2d_route.STAGES shape."""
    return [
        (list(spec["progress_columns"]), str(spec["label"]), str(spec["owner"]), str(spec["command"]))
        for spec in STAGE_GRAPH
        if spec.get("routes")
    ]

def stage_for_key(key: str) -> Optional[Dict[str, Any]]:
    """Find a stage by its key."""
    return next((dict(spec) for spec in STAGE_GRAPH if spec["key"] == key), None)

def stage_requires_for_mode(spec: Dict[str, Any], mode: str = "") -> Tuple[str, ...]:
    """Adjust requirements based on production mode."""
    requires = tuple(spec.get("requires", ()))
    if is_native_av_mode(mode):
        return tuple(r for r in requires if r != "配音")
    return requires

def stage_for_progress_column(column: str) -> Optional[Dict[str, Any]]:
    """Find a stage that owns a given progress column."""
    for spec in STAGE_GRAPH:
        if column in spec.get("progress_columns", ()):
            return dict(spec)
    return None

def annotate_finding(finding: Dict[str, Any], gate_stage: str, ep: Optional[str] = None) -> Dict[str, Any]:
    """Add recovery info to a finding."""
    out = dict(finding)
    recovery = GATE_RECOVERY.get(gate_stage, {})
    if not recovery:
        return out
    out.setdefault("return_to_stage", recovery.get("return_to_stage"))
    out.setdefault("rerun_scope", recovery.get("rerun_scope"))
    artifacts = recovery.get("affected_artifacts", ())
    if ep:
        artifacts = [str(p).format(ep=ep) for p in artifacts]
    out.setdefault("affected_artifacts", artifacts)
    return out

def finding_dim_key(raw: Dict[str, Any]) -> str:
    """Extract stable dimension key from finding."""
    norm = normalize_finding(raw)
    return norm.get("dim_key") or norm.get("dimension") or "一致性"

def finding_scope_keys(raw: Dict[str, Any]) -> List[str]:
    """Extract scope keys from finding."""
    norm = normalize_finding(raw)
    scopes = norm.get("affected_shots") or norm.get("affected_artifacts") or []
    if not scopes and norm.get("loc"):
        scopes = [str(norm["loc"])]
    cleaned: List[str] = []
    seen = set()
    for scope in scopes:
        text = str(scope or "").strip()
        if text and text not in seen:
            seen.add(text)
            cleaned.append(text)
    return cleaned or [""]

def finding_fingerprints(episode: Any, stage: Any, dim: Any, raw: Optional[Dict[str, Any]] = None) -> List[str]:
    """Generate fingerprints for all scopes in a finding."""
    scopes = finding_scope_keys(raw or {})
    return [finding_fingerprint(episode, stage, dim, scope) for scope in scopes]
