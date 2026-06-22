#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n2d video backend adapter layer.

This module records per-run evidence for the video backend that will execute a
paid batch. Static profiles live in `n2d_platform_profiles.py`; this file adds
the "checked today against official docs / CLI help / API capability" layer.

采集日期：2026-06-21
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

try:
    from n2d_platform_profiles import (
        CATALOG_VERIFIED as PROFILE_VERIFIED,
        VIDEO_BACKEND_PROFILES,
        anchor_consumption_plan,
        effective_frame_backend,
        normalize_video_backend,
        video_backend_frame_control,
        video_backend_max_seconds,
        video_backend_motion_control,
        video_backend_profile,
    )
except Exception:  # pragma: no cover
    from .n2d_platform_profiles import (  # type: ignore
        CATALOG_VERIFIED as PROFILE_VERIFIED,
        VIDEO_BACKEND_PROFILES,
        anchor_consumption_plan,
        effective_frame_backend,
        normalize_video_backend,
        video_backend_frame_control,
        video_backend_max_seconds,
        video_backend_motion_control,
        video_backend_profile,
    )


CATALOG_VERIFIED = {
    "date": "2026-06-21",
    "source": "n2d_platform_profiles static catalog + per-run official docs / CLI / API evidence",
    "profile_catalog": PROFILE_VERIFIED,
}

OFF_OR_MANUAL_VALUES = {
    "",
    "无",
    "关闭",
    "不使用",
    "off",
    "none",
    "no",
    "disable",
    "disabled",
    "manual",
    "人工",
    "手工",
}


def _slug(value: str) -> str:
    text = (value or "unknown").strip().lower()
    text = re.sub(r"[^0-9a-zA-Z._-]+", "_", text)
    return text.strip("_") or "unknown"


def canonical_backend(raw: Optional[str]) -> Tuple[str, str]:
    text = str(raw or "").strip()
    if text.lower() in OFF_OR_MANUAL_VALUES or text in OFF_OR_MANUAL_VALUES:
        return text.lower(), "manual_or_off"
    canonical = normalize_video_backend(text, default="")
    if canonical:
        return canonical, "known"
    return text.lower(), "unknown"


def backend_adapter(raw: Optional[str], channel: Optional[str] = None) -> Dict[str, Any]:
    canonical, status = canonical_backend(raw)
    channel_key, channel_status = canonical_backend(channel)
    execution = effective_frame_backend(canonical, channel_key)
    profile = video_backend_profile(canonical) or {}
    frame_control = video_backend_frame_control(canonical, channel_key)
    motion_control = video_backend_motion_control(canonical)
    return {
        "kind": "n2d_video_backend_adapter",
        "canonical": canonical,
        "classification": status,
        "label": profile.get("label") or raw or canonical or "unknown",
        "channel": channel_key,
        "channel_classification": channel_status,
        "execution_backend": execution,
        "profile_known": canonical in VIDEO_BACKEND_PROFILES,
        "max_clip_seconds": video_backend_max_seconds(canonical, default=8),
        "default_mode": profile.get("default_mode") or "",
        "native_av": bool(profile.get("native_av")),
        "lipsync_audio_ref": bool(profile.get("lipsync_audio_ref")),
        "identity_mechanism": profile.get("identity_mechanism") or "",
        "frame_control": frame_control,
        "motion_control": motion_control,
        "anchor_consumption_sample": anchor_consumption_plan(
            canonical,
            channel_key,
            anchor_count=1,
            need_end=True,
        ),
        "evidence": profile.get("frame_control", {}).get("verified", "unknown")
        if isinstance(profile.get("frame_control"), dict)
        else "unknown",
    }


def adapter_catalog() -> Dict[str, Any]:
    return {
        "kind": "n2d_video_backend_adapter_catalog",
        "verified": CATALOG_VERIFIED,
        "backends": {key: backend_adapter(key) for key in VIDEO_BACKEND_PROFILES},
    }


def requires_refresh(backend: Optional[str]) -> bool:
    canonical, status = canonical_backend(backend)
    if status == "manual_or_off":
        return False
    return bool(canonical)


def default_capability_assertions(raw: Optional[str], channel: Optional[str] = None) -> Dict[str, Any]:
    adapter = backend_adapter(raw, channel)
    frame = adapter.get("frame_control") if isinstance(adapter.get("frame_control"), dict) else {}
    motion = adapter.get("motion_control") if isinstance(adapter.get("motion_control"), dict) else {}
    return {
        "max_clip_seconds": adapter.get("max_clip_seconds"),
        "frame_control_mode": frame.get("mode"),
        "max_timeline_frames": frame.get("max_timeline_frames"),
        "max_reference_images": frame.get("max_reference_images"),
        "supports_first_frame": bool(frame.get("supports_first_frame")),
        "supports_last_frame": bool(frame.get("supports_last_frame")),
        "supports_native_mid_anchors": bool(frame.get("supports_native_mid_anchors")),
        "native_av": bool(adapter.get("native_av")),
        "lipsync_audio_ref": bool(adapter.get("lipsync_audio_ref")),
        "identity_mechanism": adapter.get("identity_mechanism") or "",
        "motion_control_level": motion.get("level") or "",
        "motion_control_capabilities": list(motion.get("capabilities") or []),
    }


def _capability_evidence_source(
    *,
    sources: Sequence[str],
    source_urls: Sequence[str],
    evidence_kind: str,
    note: str,
) -> Dict[str, str]:
    return {
        "source": str(sources[0]).strip() if sources else "",
        "source_url": str(source_urls[0]).strip() if source_urls else "",
        "evidence_kind": str(evidence_kind or "").strip(),
        "observed_text": str(note or "").strip(),
    }


def structured_capability_assertions(
    values: Mapping[str, Any],
    *,
    sources: Sequence[str],
    source_urls: Sequence[str] = (),
    evidence_kind: str = "",
    note: str = "",
) -> Dict[str, Dict[str, Any]]:
    """Wrap each capability assertion with auditable per-capability evidence."""
    evidence = _capability_evidence_source(
        sources=sources,
        source_urls=source_urls,
        evidence_kind=evidence_kind,
        note=note,
    )
    return {str(key): {"value": value, **evidence} for key, value in values.items()}


def capability_assertion_value(assertion: Any) -> Any:
    if isinstance(assertion, Mapping) and "value" in assertion:
        return assertion.get("value")
    return assertion


def _capability_assertion_evidence_gaps(assertions: Mapping[str, Any]) -> Dict[str, str]:
    gaps: Dict[str, str] = {}
    for key, item in assertions.items():
        if not isinstance(item, Mapping) or "value" not in item:
            gaps[str(key)] = "missing structured value"
            continue
        source = str(item.get("source") or "").strip()
        source_url = str(item.get("source_url") or "").strip()
        observed = str(item.get("observed_text") or item.get("note") or "").strip()
        kind = str(item.get("evidence_kind") or "").strip()
        if not source:
            gaps[str(key)] = "missing source"
        elif not (source_url or observed or kind):
            gaps[str(key)] = "missing source_url/observed_text/evidence_kind"
    return gaps


def _coerce_capability_value(value: str) -> Any:
    text = str(value).strip()
    lower = text.lower()
    if lower in {"true", "yes", "1", "是", "支持"}:
        return True
    if lower in {"false", "no", "0", "否", "不支持"}:
        return False
    try:
        if re.fullmatch(r"-?\d+", text):
            return int(text)
        if re.fullmatch(r"-?\d+\.\d+", text):
            return float(text)
    except Exception:
        pass
    if "," in text:
        return [part.strip() for part in text.split(",") if part.strip()]
    return text


def parse_capability_overrides(items: Sequence[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for item in items:
        if "=" not in str(item):
            raise ValueError(f"capability override must be key=value: {item}")
        key, value = str(item).split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"capability override has empty key: {item}")
        out[key] = _coerce_capability_value(value)
    return out


def refresh_evidence_path(root: str, backend: Optional[str], channel: Optional[str] = None) -> Path:
    canonical, _status = canonical_backend(backend)
    channel_key, channel_status = canonical_backend(channel)
    suffix = ""
    if channel_key and channel_status != "manual_or_off":
        suffix = f"__via_{_slug(channel_key)}"
    return Path(root) / "生产数据" / "video_backend_capabilities" / f"{_slug(canonical)}{suffix}.json"


def load_refresh_evidence(root: str, backend: Optional[str], channel: Optional[str] = None) -> Optional[Dict[str, Any]]:
    path = refresh_evidence_path(root, backend, channel)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def refresh_evidence_status(
    root: str,
    backend: Optional[str],
    channel: Optional[str] = None,
    *,
    today: Optional[dt.date] = None,
    max_age_days: int = 0,
) -> Dict[str, Any]:
    today = today or dt.date.today()
    path = refresh_evidence_path(root, backend, channel)
    if not requires_refresh(backend):
        return {"status": "skipped", "path": str(path), "message": "manual/off backend does not require API refresh evidence"}
    evidence = load_refresh_evidence(root, backend, channel)
    if not evidence:
        return {"status": "missing", "path": str(path), "message": "no per-run video backend refresh evidence"}
    raw_date = str(evidence.get("verified_at") or evidence.get("checked_at") or evidence.get("date") or "")
    try:
        verified = dt.date.fromisoformat(raw_date[:10])
    except ValueError:
        return {"status": "bad_date", "path": str(path), "message": f"invalid verified_at: {raw_date}"}
    age = max(0, (today - verified).days)
    fresh = age <= int(max_age_days)
    assertions = evidence.get("capability_assertions")
    if not isinstance(assertions, dict) or not assertions:
        return {
            "status": "missing_capability_assertions",
            "path": str(path),
            "verified_at": verified.isoformat(),
            "age_days": age,
            "max_age_days": int(max_age_days),
            "message": "freshness evidence lacks structured capability_assertions",
        }
    evidence_gaps = _capability_assertion_evidence_gaps(assertions)
    if evidence_gaps:
        sample = "; ".join(f"{key}: {reason}" for key, reason in list(evidence_gaps.items())[:8])
        return {
            "status": "missing_capability_evidence",
            "path": str(path),
            "verified_at": verified.isoformat(),
            "age_days": age,
            "max_age_days": int(max_age_days),
            "capability_assertions": assertions,
            "capability_evidence_gaps": evidence_gaps,
            "message": f"capability_assertions lack per-capability evidence ({sample})",
        }
    return {
        "status": "fresh" if fresh else "stale",
        "path": str(path),
        "verified_at": verified.isoformat(),
        "age_days": age,
        "max_age_days": int(max_age_days),
        "capability_assertions": assertions,
        "message": "fresh for this run" if fresh else f"refresh evidence is {age} day(s) old",
    }


def write_refresh_evidence(
    root: str,
    backend: Optional[str],
    *,
    channel: Optional[str] = None,
    sources: Sequence[str],
    source_urls: Sequence[str] = (),
    capability_overrides: Optional[Dict[str, Any]] = None,
    note: str = "",
    evidence_kind: str = "",
    today: Optional[str] = None,
) -> Path:
    path = refresh_evidence_path(root, backend, channel)
    path.parent.mkdir(parents=True, exist_ok=True)
    date_s = today or dt.date.today().isoformat()
    adapter = backend_adapter(backend, channel)
    values = default_capability_assertions(backend, channel)
    values.update(capability_overrides or {})
    assertions = structured_capability_assertions(
        values,
        sources=sources,
        source_urls=source_urls,
        evidence_kind=evidence_kind,
        note=note,
    )
    payload = {
        "kind": "n2d_video_backend_refresh_evidence",
        "backend": adapter.get("canonical"),
        "channel": adapter.get("channel"),
        "execution_backend": adapter.get("execution_backend"),
        "verified_at": date_s,
        "sources": list(sources),
        "source_urls": list(source_urls),
        "evidence_kind": evidence_kind,
        "capability_assertions": assertions,
        "note": note,
        "adapter": adapter,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d video backend adapter layer")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("catalog")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("inspect")
    p.add_argument("backend")
    p.add_argument("--channel", default="")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("status")
    p.add_argument("root")
    p.add_argument("--backend", required=True)
    p.add_argument("--channel", default="")
    p.add_argument("--today", default=None)
    p.add_argument("--max-age-days", type=int, default=0)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("record-refresh")
    p.add_argument("root")
    p.add_argument("--backend", required=True)
    p.add_argument("--channel", default="")
    p.add_argument("--source", action="append", required=True)
    p.add_argument("--source-url", action="append", default=[])
    p.add_argument("--capability", action="append", default=[],
                   help="Structured capability assertion override, key=value. Repeatable.")
    p.add_argument("--evidence-kind", default="")
    p.add_argument("--note", default="")
    p.add_argument("--date", default=None)

    ns = ap.parse_args(argv)
    if ns.cmd == "catalog":
        payload = adapter_catalog()
    elif ns.cmd == "inspect":
        payload = backend_adapter(ns.backend, ns.channel)
    elif ns.cmd == "status":
        today = dt.date.fromisoformat(ns.today) if ns.today else None
        payload = refresh_evidence_status(
            ns.root,
            ns.backend,
            ns.channel,
            today=today,
            max_age_days=ns.max_age_days,
        )
    elif ns.cmd == "record-refresh":
        path = write_refresh_evidence(
            ns.root,
            ns.backend,
            channel=ns.channel,
            sources=ns.source,
            source_urls=ns.source_url,
            capability_overrides=parse_capability_overrides(ns.capability),
            note=ns.note,
            evidence_kind=ns.evidence_kind,
            today=ns.date,
        )
        payload = {"path": str(path), "status": "written"}
    else:  # pragma: no cover
        raise AssertionError(ns.cmd)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
