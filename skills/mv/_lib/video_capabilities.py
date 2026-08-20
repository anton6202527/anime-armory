#!/usr/bin/env python3
"""Versioned MV video provider capability and route boundary.

The graph is deliberately model-version × access-channel specific.  A model
being known and a channel being known is not enough to make the pair
executable.  Unknown/custom/manual routes need a named adapter record and are
otherwise rejected before a provider request can be prepared.

Collected: 2026-08-20.  Official sources are stored on every current entry;
legacy entries are compatibility profiles and are never promoted to a newer
model version implicitly.
"""
from __future__ import annotations

import copy
from datetime import date, datetime
import hashlib
import json
import re
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence


CAPABILITY_GRAPH_VERSION = "2026-08-20.3"
CAPABILITY_GRAPH_COLLECTED_AT = "2026-08-20"
CAPABILITY_GRAPH_STALE_AFTER_DAYS = 90
ADAPTER_KIND = "mv_video_provider_adapter"
ADAPTER_SCHEMA_VERSION = 1

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _inputs(
    *,
    start: int = 1,
    end: int = 0,
    reference_image: int = 0,
    reference_video: int = 0,
    reference_audio: int = 0,
    keyframe: int = 0,
) -> Dict[str, Dict[str, Any]]:
    return {
        "start_frame": {"max_count": start, "required_for_image2video": bool(start)},
        "end_frame": {"max_count": end},
        "reference_image": {"max_count": reference_image},
        "reference_video": {"max_count": reference_video},
        "reference_audio": {"max_count": reference_audio},
        "keyframe": {"max_count": keyframe},
    }


def _model(
    *,
    inputs: Mapping[str, Any],
    combinations: Sequence[Sequence[str]],
    duration: Mapping[str, Any],
    fps: Sequence[int],
    resolutions: Sequence[str],
    native_audio: Mapping[str, Any],
    multi_shot: bool = False,
    max_sequence_seconds: Optional[float] = None,
    legacy: bool = False,
    source: str = "",
    source_date: str = "2026-08-20",
) -> Dict[str, Any]:
    value: Dict[str, Any] = {
        "input_roles": dict(inputs),
        "allowed_input_combinations": [list(row) for row in combinations],
        "duration_seconds": dict(duration),
        "fps": list(fps),
        "resolutions": [str(v).lower() for v in resolutions],
        "native_audio": dict(native_audio),
        "multi_shot": bool(multi_shot),
        "legacy_compatibility": bool(legacy),
        "provenance": {"source": source, "source_date_or_collected": source_date},
    }
    if max_sequence_seconds is not None:
        value["max_sequence_seconds"] = float(max_sequence_seconds)
    return value


# Current entries use primary vendor documentation.  Conservative legacy
# profiles preserve existing projects; their access is explicit and they never
# alias to Seedance 2.5 / Ray3.2 or any other current version.
MODEL_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "Seedance 2.0": _model(
        inputs=_inputs(start=1, reference_image=9, reference_video=3, reference_audio=3),
        combinations=(("start_frame",), ("reference_image",), ("start_frame", "reference_image"),
                      ("reference_image", "reference_video"),
                      ("start_frame", "reference_image", "reference_video"),
                      ("reference_image", "reference_video", "reference_audio"),
                      ("start_frame", "reference_image", "reference_video", "reference_audio")),
        duration={"min": 2.0, "max": 15.0}, fps=(24,), resolutions=("720p", "1080p"),
        native_audio={"produces": True, "disableable": None, "disableability_status": "not_confirmed"}, multi_shot=True,
        max_sequence_seconds=15,
        source="https://seed.bytedance.com/en/blog/official-launch-of-seedance-2.0",
        source_date="2026-02-12",
    ),
    "Seedance 2.5": _model(
        inputs=_inputs(start=1, reference_image=30, reference_video=10, reference_audio=10),
        combinations=(("start_frame",), ("reference_image",), ("start_frame", "reference_image"),
                      ("reference_image", "reference_video"),
                      ("start_frame", "reference_image", "reference_video"),
                      ("reference_image", "reference_video", "reference_audio"),
                      ("start_frame", "reference_image", "reference_video", "reference_audio")),
        duration={"min": 2.0, "max": 30.0}, fps=(24,), resolutions=("720p", "1080p"),
        native_audio={"produces": True, "disableable": None, "disableability_status": "not_confirmed"}, multi_shot=True,
        max_sequence_seconds=30,
        source="https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5",
        source_date="2026-07-31",
    ),
    "Veo 3.1": _model(
        inputs=_inputs(start=1, end=1, reference_image=3),
        combinations=(("start_frame",), ("start_frame", "end_frame"), ("reference_image",)),
        duration={"allowed": [4.0, 6.0, 8.0], "constraints": [
            {"when_any": ["end_frame", "reference_image"], "allowed": [8.0]},
            {"when_resolution": ["1080p", "4k"], "allowed": [8.0]},
        ]},
        fps=(24,), resolutions=("720p", "1080p", "4k"),
        native_audio={"produces": True, "disableable": False, "disableability_status": "confirmed_always_on"},
        source="https://ai.google.dev/gemini-api/docs/veo",
        source_date="2026-07-30",
    ),
    "Kling 3.0": _model(
        inputs=_inputs(start=1, end=1, reference_image=4, reference_video=1, reference_audio=1),
        combinations=(("start_frame",), ("start_frame", "end_frame"), ("reference_image",),
                      ("start_frame", "reference_image"), ("reference_image", "reference_video"),
                      ("start_frame", "reference_image", "reference_video"),
                      ("reference_image", "reference_audio"), ("start_frame", "reference_image", "reference_audio")),
        duration={"min": 2.0, "max": 15.0}, fps=(24, 30), resolutions=("720p", "1080p"),
        native_audio={"produces": True, "disableable": None, "disableability_status": "not_confirmed"}, multi_shot=True,
        max_sequence_seconds=15, source="https://app.klingai.com/global/dev/document-api/quickStart/productIntroduction/overview",
        source_date="collected 2026-08-20",
    ),
    "Runway Gen-4.5": _model(
        inputs=_inputs(start=1), combinations=(("start_frame",),),
        duration={"min": 2.0, "max": 10.0}, fps=(24, 25), resolutions=("720p",),
        native_audio={"produces": False, "disableable": True},
        source="https://help.runwayml.com/hc/en-us/articles/46974685288467-Creating-with-Gen-4-5",
        source_date="collected 2026-08-20",
    ),
    "Luma Ray3.2": _model(
        inputs=_inputs(start=1, end=1, reference_image=4, reference_video=1, keyframe=16),
        combinations=(("start_frame",), ("start_frame", "end_frame"), ("reference_image",),
                      ("reference_video",), ("reference_video", "end_frame"), ("keyframe",)),
        duration={"min": 1.0, "max": 20.0}, fps=(24,), resolutions=("720p", "1080p"),
        native_audio={"produces": False, "disableable": True}, multi_shot=True,
        max_sequence_seconds=20,
        source="https://lumalabs.ai/news/introducing-ray-3-2", source_date="2026-06-09",
    ),
}


# Preview candidates are deliberately separate from MODEL_CAPABILITIES.  Their
# official docs establish that the model/route exists, but do not yet provide a
# stable execution matrix that this pipeline can safely compile against.  They
# become executable only when a named adapter supplies the exact capability
# contract verified for the caller's account/SDK version.
MODEL_CANDIDATES: Dict[str, Dict[str, Any]] = {
    "Gemini Omni Flash Preview": {
        "provider_model_id": "gemini-omni-flash-preview",
        "release_stage": "preview",
        "route_status": "adapter_required",
        "officially_documented": {
            "api": "Gemini Interactions API v1beta",
            "tasks": ["text_to_video", "image_to_video", "reference_to_video", "edit"],
            "image_input": True,
            "multiple_reference_images": True,
            "aspect_ratios": ["16:9", "9:16"],
            "generated_audio_default": True,
            "synthid_watermark": True,
            "unsupported_or_limited": [
                "audio_reference_upload",
                "last_frame_interpolation",
                "video_extension",
                "multi_video_reasoning",
                "negative_prompt_parameter",
            ],
        },
        "adapter_must_supply": [
            "input_roles",
            "allowed_input_combinations",
            "duration_seconds",
            "fps",
            "resolutions",
            "native_audio",
        ],
        "provenance": {
            "sources": [
                "https://ai.google.dev/gemini-api/docs/omni",
                "https://ai.google.dev/gemini-api/docs/video",
            ],
            "official_pages_last_updated": ["2026-07-30", "2026-06-30"],
            "collected_at": "2026-08-20",
            "note": "No stable duration/fps/resolution execution matrix was published; do not borrow Veo limits.",
        },
    },
}


def _legacy_model(
    name: str,
    *,
    start: int = 1,
    end: int = 0,
    reference_image: int = 0,
    native_audio: bool = False,
    multi_shot: bool = False,
    max_seconds: float = 15,
) -> None:
    combos = [("start_frame",)] if start else [()]
    if start and end:
        combos.append(("start_frame", "end_frame"))
    if reference_image:
        combos.append(("reference_image",))
    MODEL_CAPABILITIES[name] = _model(
        inputs=_inputs(start=start, end=end, reference_image=reference_image),
        combinations=combos, duration={"min": 1.0, "max": max_seconds},
        fps=(24, 30), resolutions=("720p", "1080p"),
        native_audio={"produces": native_audio, "disableable": True},
        multi_shot=multi_shot, max_sequence_seconds=max_seconds if multi_shot else None,
        legacy=True, source="legacy project compatibility profile; reverify before a new paid run",
        source_date="collected 2026-08-20",
    )


_legacy_model("Hailuo 02", end=1, reference_image=1)
_legacy_model("Hailuo 2.3", end=1, reference_image=1)
_legacy_model("Runway Gen-4", end=1, reference_image=1, max_seconds=10)
_legacy_model("Luma Ray3 / Ray3.14", end=1, reference_image=4, max_seconds=20)
_legacy_model("Pika 2.5", end=1, reference_image=1, max_seconds=10)
_legacy_model("HunyuanVideo 1.5", start=0, max_seconds=10)
_legacy_model("Wan 2.2", end=1, reference_image=1, max_seconds=10)
_legacy_model("LTX-2.3", start=0, max_seconds=10)
_legacy_model("Sora", end=1, reference_image=1, max_seconds=20)
_legacy_model("Sora 2", reference_image=1, native_audio=True, multi_shot=True, max_seconds=20)


CHANNELS: Dict[str, Dict[str, Any]] = {
    "即梦/Dreamina": {"provider_id": "bytedance.dreamina", "kind": "web", "models": {
        "Seedance 2.0": "available", "Seedance 2.5": "available"}},
    "即梦": {"provider_id": "bytedance.jimeng", "kind": "web", "models": {
        "Seedance 2.0": "available", "Seedance 2.5": "available"}},
    "Dreamina": {"provider_id": "bytedance.dreamina", "kind": "web", "models": {
        "Seedance 2.0": "available", "Seedance 2.5": "available"}},
    "豆包": {"provider_id": "bytedance.doubao", "kind": "web", "models": {
        "Seedance 2.0": "available", "Seedance 2.5": "available"}},
    "火山方舟/Volcengine API": {"provider_id": "bytedance.volcengine_api", "kind": "api", "models": {
        "Seedance 2.0": "available", "Seedance 2.5": "api_pending"}},
    "Google Gemini API": {
        "provider_id": "google.gemini_api",
        "kind": "api",
        "models": {
            "Veo 3.1": "available",
            "Gemini Omni Flash Preview": "adapter_required",
        },
        "model_release_stages": {"Gemini Omni Flash Preview": "preview"},
    },
    "可灵/Kling": {"provider_id": "kuaishou.kling", "kind": "api_or_web", "models": {"Kling 3.0": "available"}},
    "可灵": {"provider_id": "kuaishou.kling", "kind": "api_or_web", "models": {"Kling 3.0": "available"}},
    "Kling": {"provider_id": "kuaishou.kling", "kind": "api_or_web", "models": {"Kling 3.0": "available"}},
    "海螺AI": {"provider_id": "minimax.hailuo", "kind": "web", "models": {"Hailuo 02": "legacy", "Hailuo 2.3": "legacy"}},
    "Hailuo": {"provider_id": "minimax.hailuo", "kind": "web", "models": {"Hailuo 02": "legacy", "Hailuo 2.3": "legacy"}},
    "Runway API": {"provider_id": "runway.api", "kind": "api", "models": {"Runway Gen-4.5": "available", "Runway Gen-4": "legacy"}},
    "Runway": {"provider_id": "runway", "kind": "api_or_web", "models": {"Runway Gen-4.5": "available", "Runway Gen-4": "legacy"}},
    "Luma Dream Machine": {"provider_id": "luma.dream_machine", "kind": "api_or_web", "models": {
        "Luma Ray3.2": "available", "Luma Ray3 / Ray3.14": "legacy"}},
    "Luma": {"provider_id": "luma", "kind": "api_or_web", "models": {
        "Luma Ray3.2": "available", "Luma Ray3 / Ray3.14": "legacy"}},
    "Pika": {"provider_id": "pika", "kind": "api_or_web", "models": {"Pika 2.5": "legacy"}},
    "本地/开源": {"provider_id": "local.open_source", "kind": "local", "models": {
        "HunyuanVideo 1.5": "legacy", "Wan 2.2": "legacy", "LTX-2.3": "legacy"}},
    "manual": {"provider_id": "manual.unbound", "kind": "manual", "models": {}},
}


def graph_snapshot() -> Dict[str, Any]:
    return {
        "kind": "mv_video_capability_graph",
        "version": CAPABILITY_GRAPH_VERSION,
        "collected_at": CAPABILITY_GRAPH_COLLECTED_AT,
        "stale_after_days": CAPABILITY_GRAPH_STALE_AFTER_DAYS,
        "models": copy.deepcopy(MODEL_CAPABILITIES),
        "candidates": copy.deepcopy(MODEL_CANDIDATES),
        "channels": copy.deepcopy(CHANNELS),
    }


def graph_sha256() -> str:
    return stable_hash(graph_snapshot())


def capability_graph_freshness_errors(today: Optional[date] = None) -> Sequence[str]:
    """Make volatile execution limits expire instead of aging into folklore."""
    today = today or date.today()
    try:
        collected = datetime.strptime(CAPABILITY_GRAPH_COLLECTED_AT, "%Y-%m-%d").date()
    except ValueError:
        return ["capability_graph_collected_at_invalid"]
    age = (today - collected).days
    if age < 0:
        return ["capability_graph_collected_at_in_future"]
    if age > CAPABILITY_GRAPH_STALE_AFTER_DAYS:
        return [
            f"capability_graph_stale:age_days={age},"
            f"max={CAPABILITY_GRAPH_STALE_AFTER_DAYS},collected_at={CAPABILITY_GRAPH_COLLECTED_AT}"
        ]
    return []


def _execution_capability_errors(capability: Any) -> Sequence[str]:
    """Validate the minimum graph shape needed for deterministic compilation."""
    if not isinstance(capability, Mapping):
        return ["adapter_capability_missing"]
    errors = []
    roles = capability.get("input_roles")
    if not isinstance(roles, Mapping):
        errors.append("adapter_capability_input_roles_missing")
    combinations = capability.get("allowed_input_combinations")
    if not isinstance(combinations, Sequence) or isinstance(combinations, (str, bytes)) or not combinations:
        errors.append("adapter_capability_combinations_missing")
    duration = capability.get("duration_seconds")
    if not isinstance(duration, Mapping) or not any(
        key in duration for key in ("allowed", "min", "max")
    ):
        errors.append("adapter_capability_duration_missing")
    fps = capability.get("fps")
    if not isinstance(fps, Sequence) or isinstance(fps, (str, bytes)) or not fps:
        errors.append("adapter_capability_fps_missing")
    resolutions = capability.get("resolutions")
    if not isinstance(resolutions, Sequence) or isinstance(resolutions, (str, bytes)) or not resolutions:
        errors.append("adapter_capability_resolutions_missing")
    audio = capability.get("native_audio")
    if not isinstance(audio, Mapping) or "produces" not in audio or "disableable" not in audio:
        errors.append("adapter_capability_native_audio_missing")
    return errors


def _adapter_errors(adapter: Any, model: str, channel: str) -> Sequence[str]:
    if not isinstance(adapter, Mapping):
        return ["missing_explicit_adapter_record"]
    errors = []
    if adapter.get("kind") != ADAPTER_KIND or adapter.get("schema_version") != ADAPTER_SCHEMA_VERSION:
        errors.append("invalid_adapter_schema")
    if str(adapter.get("model") or "").strip() != model:
        errors.append("adapter_model_mismatch")
    if str(adapter.get("channel") or "").strip() != channel:
        errors.append("adapter_channel_mismatch")
    if not str(adapter.get("provider_id") or "").strip():
        errors.append("adapter_provider_id_missing")
    if str(adapter.get("access_status") or "") not in {"available", "legacy"}:
        errors.append("adapter_access_status_not_executable")
    if not str(adapter.get("adapter_kind") or "").strip():
        errors.append("adapter_kind_missing")
    reviewer = str(adapter.get("reviewer") or "").strip()
    if not reviewer:
        errors.append("adapter_reviewer_missing")
    if not str(adapter.get("notes") or "").strip():
        errors.append("adapter_notes_missing")
    cap = adapter.get("capability")
    if model not in MODEL_CAPABILITIES:
        errors.extend(_execution_capability_errors(cap))
    return errors


def resolve_route(model: str, channel: str, adapter: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Resolve one executable model × channel pair, or fail closed."""
    model = str(model or "").strip()
    channel = str(channel or "").strip()
    channel_row = CHANNELS.get(channel)
    candidate = MODEL_CANDIDATES.get(model)
    if model in MODEL_CAPABILITIES:
        freshness_errors = capability_graph_freshness_errors()
        if freshness_errors:
            raise ValueError("capability_graph_reverification_required:" + ",".join(freshness_errors))
    status = (channel_row.get("models") or {}).get(model) if channel_row else None
    needs_adapter = (
        model in {"manual", "自定义"}
        or channel in {"manual", "自定义"}
        or model not in MODEL_CAPABILITIES
        or channel_row is None
        or status == "adapter_required"
    )
    if not needs_adapter and status not in {"available", "legacy"}:
        known_model = model in MODEL_CAPABILITIES or model in MODEL_CANDIDATES
        known_channel = channel in CHANNELS
        raise ValueError(
            f"non_executable_model_channel_pair:model={model!r},channel={channel!r},"
            f"known_model={known_model},known_channel={known_channel}"
        )
    if needs_adapter:
        errors = _adapter_errors(adapter, model, channel)
        if errors:
            raise ValueError("adapter_record_rejected:" + ",".join(errors))
        capability = copy.deepcopy(adapter.get("capability") or MODEL_CAPABILITIES.get(model))
        route = {
            "model": model,
            "channel": channel,
            "provider_id": str(adapter["provider_id"]).strip(),
            "channel_kind": str(adapter["adapter_kind"]).strip(),
            "access_status": str(adapter["access_status"]),
            "adapter_record": copy.deepcopy(dict(adapter)),
            "adapter_record_sha256": stable_hash(adapter),
            "capability": capability,
            "release_stage": (candidate or {}).get("release_stage") or "stable",
            "declared_route_status": status or "custom_adapter_required",
            "adapter_required": bool(candidate or status == "adapter_required"),
        }
    else:
        route = {
            "model": model,
            "channel": channel,
            "provider_id": channel_row["provider_id"],
            "channel_kind": channel_row["kind"],
            "access_status": status,
            "adapter_record": None,
            "adapter_record_sha256": "",
            "capability": copy.deepcopy(MODEL_CAPABILITIES[model]),
            "release_stage": "legacy" if status == "legacy" else "stable",
            "declared_route_status": status,
            "adapter_required": False,
        }
    route["capability_graph_version"] = CAPABILITY_GRAPH_VERSION
    route["capability_graph_sha256"] = graph_sha256()
    route["route_sha256"] = stable_hash({k: v for k, v in route.items() if k != "route_sha256"})
    return route


def _present_roles(rows: Iterable[Mapping[str, Any]]) -> Sequence[str]:
    return sorted({str(row.get("role") or "") for row in rows if row.get("role")})


def _combination_allowed(present: Sequence[str], combinations: Sequence[Sequence[str]]) -> bool:
    current = set(present)
    return any(current.issubset(set(combo)) for combo in combinations)


def compile_request_controls(route: Mapping[str, Any], planned: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate and compile exact provider controls without changing edit timing."""
    capability = route.get("capability") or {}
    if not isinstance(capability, Mapping):
        raise ValueError("route_capability_missing")
    planned_inputs = [dict(row) for row in planned.get("input_roles") or [] if isinstance(row, Mapping)]
    by_role: Dict[str, list] = {}
    for row in planned_inputs:
        role = str(row.get("role") or "").strip()
        if role:
            by_role.setdefault(role, []).append(row)
    role_caps = capability.get("input_roles") or {}
    compiled_inputs = []
    adaptations = []
    for role, rows in by_role.items():
        max_count = int((role_caps.get(role) or {}).get("max_count") or 0)
        if role == "end_frame" and max_count == 0:
            adaptations.append({"kind": "unsupported_end_frame_not_submitted", "role": role})
            continue
        if max_count <= 0:
            raise ValueError(f"unsupported_input_role:{role}")
        if len(rows) > max_count:
            raise ValueError(f"input_role_count_exceeded:{role}:{len(rows)}>{max_count}")
        compiled_inputs.extend(rows)
    present = _present_roles(compiled_inputs)
    combinations = capability.get("allowed_input_combinations") or []
    if present and not _combination_allowed(present, combinations):
        raise ValueError("unsupported_input_combination:" + "+".join(present))

    planned_duration = float(planned.get("duration_seconds") or 0)
    compiled_duration = planned_duration
    duration_cap = capability.get("duration_seconds") or {}
    allowed_durations = sorted(float(v) for v in duration_cap.get("allowed") or [])
    if allowed_durations:
        eligible = [value for value in allowed_durations if value + 1e-9 >= planned_duration]
        if not eligible:
            raise ValueError(f"duration_above_max:{planned_duration}")
        compiled_duration = eligible[0]
    if duration_cap.get("min") is not None and planned_duration < float(duration_cap["min"]) - 1e-9:
        compiled_duration = float(duration_cap["min"])
    if duration_cap.get("max") is not None and planned_duration > float(duration_cap["max"]) + 1e-9:
        raise ValueError(f"duration_above_max:{planned_duration}")
    resolution = str(planned.get("resolution") or "").lower()
    if resolution not in set(capability.get("resolutions") or []):
        raise ValueError(f"unsupported_resolution:{resolution}")
    for constraint in duration_cap.get("constraints") or []:
        when_roles = set(constraint.get("when_any") or [])
        when_res = set(constraint.get("when_resolution") or [])
        applies = bool(when_roles.intersection(present) or resolution in when_res)
        if applies:
            constraint_allowed = sorted(float(v) for v in constraint.get("allowed") or [])
            eligible = [value for value in constraint_allowed if value + 1e-9 >= planned_duration]
            if not eligible:
                raise ValueError(f"duration_constraint_failed:{planned_duration}")
            compiled_duration = eligible[0]
    if abs(compiled_duration - planned_duration) > 1e-9:
        adaptations.append({
            "kind": "provider_duration_then_trim_to_picture_lock",
            "planned": planned_duration,
            "compiled": compiled_duration,
        })

    requested_fps = int(planned.get("fps") or 0)
    supported_fps = [int(v) for v in capability.get("fps") or []]
    if requested_fps in supported_fps:
        compiled_fps = requested_fps
    elif supported_fps:
        compiled_fps = min(supported_fps, key=lambda value: (abs(value - requested_fps), value))
        adaptations.append({"kind": "provider_native_fps", "planned": requested_fps, "compiled": compiled_fps})
    else:
        raise ValueError(f"unsupported_fps:{requested_fps}")

    audio = capability.get("native_audio") or {}
    disableable = audio.get("disableable")
    produces = bool(audio.get("produces"))
    audio_control = {
        "mv_policy": "external_song_track",
        "provider_can_disable": disableable,
        "provider_disableability_status": audio.get("disableability_status") or (
            "confirmed_disableable" if disableable is True else "confirmed_not_disableable"
        ),
        "provider_parameter_generate_audio": False if disableable is True else None,
        "discard_provider_audio_after_download": bool(produces and disableable is not True),
    }
    compiled = {
        "duration_seconds": compiled_duration,
        "fps": compiled_fps,
        "resolution": resolution,
        "mode": str(planned.get("mode") or "image2video"),
        "quality_tier": str(planned.get("quality_tier") or ""),
        "input_roles": compiled_inputs,
        "audio": audio_control,
        "adaptations": adaptations,
    }
    return compiled


def legacy_projection(capability: Mapping[str, Any]) -> Dict[str, Any]:
    """Small compatibility view for existing Markdown and motion-axis callers."""
    roles = capability.get("input_roles") or {}
    return {
        "reference_images": int((roles.get("reference_image") or {}).get("max_count") or 0) > 0,
        "start_end_frames": int((roles.get("end_frame") or {}).get("max_count") or 0) > 0,
        "reference_video_motion": int((roles.get("reference_video") or {}).get("max_count") or 0) > 0,
        "native_audio": bool((capability.get("native_audio") or {}).get("produces")),
        "multi_shot": bool(capability.get("multi_shot")),
        "max_sequence_seconds": capability.get("max_sequence_seconds"),
        "legacy": bool(capability.get("legacy_compatibility")),
    }
