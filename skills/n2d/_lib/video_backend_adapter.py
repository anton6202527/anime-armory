#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n2d video backend adapter layer.

This module records per-run evidence for the video backend that will execute a
paid batch. Static profiles live in `n2d_platform_profiles.py`; this file adds
the "checked today against official docs / CLI help / API capability" layer.

采集日期：2026-07-01
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

try:
    from n2d_platform_profiles import (
        CATALOG_VERIFIED as PROFILE_VERIFIED,
        VIDEO_BACKEND_PROFILES,
        anchor_consumption_plan,
        effective_frame_backend,
        normalize_video_backend,
        video_backend_capability_confidence,
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
        video_backend_capability_confidence,
        video_backend_frame_control,
        video_backend_max_seconds,
        video_backend_motion_control,
        video_backend_profile,
    )


CATALOG_VERIFIED = {
    "date": "2026-07-01",
    "source": "n2d_platform_profiles static catalog + Gemini Omni Flash / Veo / Seedance refresh + per-run official docs / CLI / API evidence",
    "profile_catalog": PROFILE_VERIFIED,
}
SKILLS_DIR = Path(__file__).resolve().parents[1]
CLI_SNAPSHOT_ROOT = SKILLS_DIR.parent / "n2d-video" / "references" / "cli_snapshots"

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

CONTROL_IDIOM_NATURAL_LANGUAGE = "natural_language"
CONTROL_IDIOM_STRUCTURED_MULTI_PROMPT = "structured_multi_prompt"
CONTROL_IDIOM_MOTION_BRUSH = "motion_brush_on_firstframe"
CONTROL_IDIOM_VALUES = {
    CONTROL_IDIOM_NATURAL_LANGUAGE,
    CONTROL_IDIOM_STRUCTURED_MULTI_PROMPT,
    CONTROL_IDIOM_MOTION_BRUSH,
}

# Static hint only. Paid execution still needs per-run capability evidence; callers
# that need a guaranteed current capability should use resolve_control_idiom().
STATIC_CONTROL_IDIOMS: Dict[str, str] = {
    "dreamina": CONTROL_IDIOM_STRUCTURED_MULTI_PROMPT,
    "seedance": CONTROL_IDIOM_STRUCTURED_MULTI_PROMPT,
    "kling": CONTROL_IDIOM_MOTION_BRUSH,
    "veo": CONTROL_IDIOM_NATURAL_LANGUAGE,
    "gemini_omni": CONTROL_IDIOM_NATURAL_LANGUAGE,
    "luma": CONTROL_IDIOM_NATURAL_LANGUAGE,
    "runway": CONTROL_IDIOM_NATURAL_LANGUAGE,
    "pika": CONTROL_IDIOM_NATURAL_LANGUAGE,
    "wan": CONTROL_IDIOM_NATURAL_LANGUAGE,
    "sora": CONTROL_IDIOM_NATURAL_LANGUAGE,
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


# ── 付费出视频前的后端连通性探针（与 image_backends.probe_backend 同状态语义）────────────────
# status: ok=可达；down=确证不可达（gate 可据此 BLOCK）；unknown=无法自动探活（gate 只 WARN）。
# 保守原则（同图侧 dreamina/kling 都标 none）：不臆造各官方后端的 argv/凭据变量名——错的会假 BLOCK；
# 默认走「人工确认」(unknown→WARN)，但若导出该后端的健康端点 base url（内网/自定义供应商场景，
# 见 codex 内网 192.168.x 502 先例）→ 真 HTTP 探活，502/超时=down→BLOCK。逃生舱 N2D_SKIP_BACKEND_PROBE。
ProbeStatus = str  # "ok" | "down" | "unknown"

# 每后端可选的 HTTP 健康端点环境变量（导出即启用真探活）；都没有则回退通用 N2D_VIDEO_BACKEND_BASE_URL。
VIDEO_BACKEND_HEALTH_URL_ENVS: Dict[str, Tuple[str, ...]] = {
    "dreamina": ("N2D_VIDEO_DREAMINA_BASE_URL", "DREAMINA_VIDEO_BASE_URL"),
    "kling":    ("N2D_VIDEO_KLING_BASE_URL",),
    "veo":      ("N2D_VIDEO_VEO_BASE_URL",),
    "seedance": ("N2D_VIDEO_SEEDANCE_BASE_URL",),
    "sora":     ("N2D_VIDEO_SORA_BASE_URL",),
    "luma":     ("N2D_VIDEO_LUMA_BASE_URL",),
    "runway":   ("N2D_VIDEO_RUNWAY_BASE_URL",),
    "pika":     ("N2D_VIDEO_PIKA_BASE_URL",),
    "wan":      ("N2D_VIDEO_WAN_BASE_URL",),
}
_GENERIC_VIDEO_HEALTH_URL_ENV = "N2D_VIDEO_BACKEND_BASE_URL"


def _resolve_video_health_url(canonical: str, env: Mapping[str, str]) -> str:
    """本后端的健康端点 url：优先各自 *_BASE_URL，回退通用 N2D_VIDEO_BACKEND_BASE_URL；都没有→空。"""
    for var in VIDEO_BACKEND_HEALTH_URL_ENVS.get(canonical, ()):
        v = str(env.get(var) or "").strip()
        if v:
            return v
    return str(env.get(_GENERIC_VIDEO_HEALTH_URL_ENV) or "").strip()


def _video_http_runner(url: str, timeout: int) -> Tuple[ProbeStatus, str]:
    """GET 健康端点：2xx/3xx=ok；5xx（含内网 502）/4xx/超时/连接失败=down。纯标准库。"""
    import urllib.error
    import urllib.request
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=timeout) as resp:
            code = getattr(resp, "status", 200) or 200
            return ("ok", "") if 200 <= code < 400 else ("down", f"HTTP {code}")
    except urllib.error.HTTPError as exc:
        return ("down", f"HTTP {exc.code}")
    except Exception as exc:
        return ("down", f"{type(exc).__name__}: {str(exc)[:120]}")


def probe_video_backend(
    raw: Optional[str],
    *,
    env: Optional[Mapping[str, str]] = None,
    http_runner: Optional[Callable[..., Tuple[ProbeStatus, str]]] = None,
    timeout: int = 8,
) -> Tuple[ProbeStatus, str]:
    """探所选生视频后端是否可达（付费出视频前）。返回 (status, detail)，语义同 image_backends.probe_backend。

    走 adapter（canonical_backend + 健康端点 env），gate 不 hardcode 内网地址/CLI 细节。runner 可注入（测试）。
    `N2D_SKIP_BACKEND_PROBE=1` → unknown（逃生舱）。导出后端健康 base url → 真 HTTP 探活；否则 unknown
    （不臆造各官方 CLI argv/凭据名，避免假 BLOCK），由 gate 降级为 WARN 提示人工确认。"""
    env = dict(os.environ) if env is None else env
    if str(env.get("N2D_SKIP_BACKEND_PROBE") or "") in ("1", "true", "True"):
        return ("unknown", "N2D_SKIP_BACKEND_PROBE 已设——跳过 live 探活")
    canonical, kind = canonical_backend(raw)
    if kind == "manual_or_off":
        return ("unknown", "渠道=人工/关闭——无自动出视频后端可探，按人工出视频流程（accept 登记）")
    if kind == "unknown" or canonical not in VIDEO_BACKEND_PROFILES:
        return ("unknown", f"未识别的生视频渠道 `{raw}`——无探针，需人工确认后端可用")
    url = _resolve_video_health_url(canonical, env)
    if url:
        runner = http_runner or _video_http_runner
        return runner(url.rstrip("/") + "/", timeout)
    return ("unknown",
            f"`{canonical}` 无自动探针（未导出健康端点 base url）——付费出视频前请人工确认："
            "官方 CLI 已登录 / 会员态有效 / API key·额度可用（或一次 dry-run）。内网/自定义供应商可导出 "
            f"{_GENERIC_VIDEO_HEALTH_URL_ENV} 或对应 *_BASE_URL 启用自动探活。")


def backend_adapter(raw: Optional[str], channel: Optional[str] = None, *, root: Optional[str] = None) -> Dict[str, Any]:
    canonical, status = canonical_backend(raw)
    channel_key, channel_status = canonical_backend(channel)
    execution = effective_frame_backend(canonical, channel_key)
    profile = video_backend_profile(canonical) or {}
    frame_control = video_backend_frame_control(canonical, channel_key)
    motion_control = video_backend_motion_control(canonical)
    confidence = video_backend_capability_confidence(canonical, channel_key)
    control_idiom = static_control_idiom(canonical, channel_key)
    native_av = bool(profile.get("native_av"))
    payload = {
        "kind": "n2d_video_backend_adapter",
        "version": 2,
        "canonical": canonical,
        "classification": status,
        "label": profile.get("label") or raw or canonical or "unknown",
        "channel": channel_key,
        "channel_classification": channel_status,
        "execution_backend": execution,
        "profile_known": canonical in VIDEO_BACKEND_PROFILES,
        "max_clip_seconds": video_backend_max_seconds(canonical, default=8),
        "default_mode": profile.get("default_mode") or "",
        "native_av": native_av,
        "native_audio": native_av,
        "lipsync_audio_ref": bool(profile.get("lipsync_audio_ref")),
        "identity_mechanism": profile.get("identity_mechanism") or "",
        "frame_control": frame_control,
        "motion_control": motion_control,
        "control_idiom": control_idiom,
        "control_idiom_supported": control_idiom != CONTROL_IDIOM_NATURAL_LANGUAGE,
        "control_idiom_source": "static_catalog",
        "capability_confidence": confidence,
        "paid_routing_allowed": bool(confidence.get("paid_routing_allowed")),
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
    if root is not None:
        try:
            from video_execution_adapter import execution_status
        except ImportError:  # pragma: no cover
            from .video_execution_adapter import execution_status  # type: ignore
        payload["execution"] = execution_status(root, canonical, channel_key)
    return payload


def static_control_idiom(raw: Optional[str], channel: Optional[str] = None) -> str:
    """Best-effort static motion-control prompt idiom for a backend/channel.

    This is a catalog hint, not paid-run proof. Use resolve_control_idiom() when
    a project root is available and current per-run evidence is required.
    """
    execution = effective_frame_backend(raw, channel)
    return STATIC_CONTROL_IDIOMS.get(execution, CONTROL_IDIOM_NATURAL_LANGUAGE)


def _assertion_value(assertions: Mapping[str, Any], key: str, default: Any = None) -> Any:
    if key not in assertions:
        return default
    return capability_assertion_value(assertions.get(key))


def resolve_control_idiom(
    root: str,
    backend: Optional[str],
    channel: Optional[str] = None,
    *,
    today: Optional[dt.date] = None,
    max_age_days: int = 0,
) -> Dict[str, Any]:
    """Return the currently usable motion-control idiom.

    Structured idioms are only returned when fresh per-run evidence contains a
    supported `control_idiom` assertion. Missing/stale evidence degrades to
    natural language, which every video prompt backend can consume.
    """
    status = refresh_evidence_status(
        root,
        backend,
        channel,
        today=today,
        max_age_days=max_age_days,
    )
    assertions = status.get("capability_assertions")
    if status.get("status") == "fresh" and isinstance(assertions, Mapping):
        raw_idiom = str(_assertion_value(assertions, "control_idiom", "") or "").strip()
        supported = _assertion_value(assertions, "control_idiom_supported", None)
        if raw_idiom in CONTROL_IDIOM_VALUES and (raw_idiom == CONTROL_IDIOM_NATURAL_LANGUAGE or supported is not False):
            return {
                "control_idiom": raw_idiom,
                "control_idiom_supported": raw_idiom != CONTROL_IDIOM_NATURAL_LANGUAGE,
                "source": "per_run_evidence",
                "status": status.get("status"),
                "backend": backend or "",
                "channel": channel or "",
            }
    return {
        "control_idiom": CONTROL_IDIOM_NATURAL_LANGUAGE,
        "control_idiom_supported": False,
        "source": "fallback_no_fresh_evidence",
        "status": status.get("status"),
        "backend": backend or "",
        "channel": channel or "",
    }


def video_routes_path(root: str, episode: str) -> Path:
    return Path(root) / "出视频" / episode / "prompt" / "video_model_routes.json"


def load_video_routes(root: str, episode: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(video_routes_path(root, episode).read_text(encoding="utf-8"))
    except Exception:
        return []
    routes = data.get("routes") if isinstance(data, Mapping) else []
    return [r for r in routes if isinstance(r, dict)]


def route_native_audio_profile(
    root: str,
    episode: str,
    *,
    channel: Optional[str] = None,
    routes: Optional[Sequence[Mapping[str, Any]]] = None,
    include_fallback: bool = False,
) -> Dict[str, Any]:
    """Summarize whether this episode routes through native-audio-capable video.

    This is intentionally route-aware: `_设置.md` may hold a generic default,
    while `video_model_routes.json` is the actual per-Clip execution contract.
    """
    selected = list(routes) if routes is not None else load_video_routes(root, episode)
    hits: List[Dict[str, Any]] = []
    for idx, route in enumerate(selected, 1):
        backends: List[Tuple[str, str]] = []
        primary = str(route.get("primary_backend") or "").strip()
        if primary:
            backends.append(("primary", primary))
        if include_fallback:
            fallbacks = route.get("fallback_backends")
            if isinstance(fallbacks, list):
                backends.extend(("fallback", str(item or "").strip()) for item in fallbacks if str(item or "").strip())
        for role, backend in backends:
            adapter = backend_adapter(backend, channel)
            route_native = (
                str(route.get("mode") or "").strip() == "native_av"
                or str(route.get("native_audio_policy") or "").strip() == "native_speech"
            )
            backend_native = bool(adapter.get("native_audio") or adapter.get("native_av"))
            if route_native or backend_native:
                hits.append({
                    "clip_id": route.get("clip_id") or f"routes[{idx}]",
                    "role": role,
                    "backend": backend,
                    "canonical": adapter.get("canonical"),
                    "execution_backend": adapter.get("execution_backend"),
                    "route_native_audio": route_native,
                    "backend_native_audio": backend_native,
                    "native_audio_policy": route.get("native_audio_policy") or "",
                    "mode": route.get("mode") or "",
                })
    return {
        "kind": "n2d_route_native_audio_profile",
        "episode": episode,
        "native_audio": bool(hits),
        "hits": hits,
        "routes_path": str(video_routes_path(root, episode)),
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
        "native_audio": bool(adapter.get("native_audio")),
        "lipsync_audio_ref": bool(adapter.get("lipsync_audio_ref")),
        "identity_mechanism": adapter.get("identity_mechanism") or "",
        "motion_control_level": motion.get("level") or "",
        "motion_control_capabilities": list(motion.get("capabilities") or []),
        "control_idiom": adapter.get("control_idiom") or CONTROL_IDIOM_NATURAL_LANGUAGE,
        "control_idiom_supported": bool(adapter.get("control_idiom_supported")),
        "paid_routing_allowed": bool(adapter.get("paid_routing_allowed")),
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


def load_cli_snapshot_evidence(cli: str) -> Optional[Dict[str, Any]]:
    path = CLI_SNAPSHOT_ROOT / _slug(cli) / "_index.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("kind") != "n2d_cli_snapshot_index":
        return None
    commands = [
        {"command": c.get("command"), "captured_at": c.get("captured_at"), "flag_count": len(c.get("flags") or [])}
        for c in data.get("commands") or []
        if isinstance(c, dict) and c.get("ok")
    ]
    return {
        "kind": "n2d_cli_snapshot_evidence",
        "cli": data.get("cli") or cli,
        "captured_at": data.get("captured_at") or "",
        "path": str(path),
        "commands": commands,
    }


def cli_evidence_for_route(backend: Optional[str], channel: Optional[str] = None) -> List[Dict[str, Any]]:
    execution = effective_frame_backend(backend, channel)
    channel_key = normalize_video_backend(channel or "", default="")
    if execution != "dreamina" and channel_key != "dreamina":
        return []
    evidence = load_cli_snapshot_evidence("dreamina")
    return [evidence] if evidence else []


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
    cli_evidence = cli_evidence_for_route(backend, channel)
    merged_sources = list(sources)
    for item in cli_evidence:
        label = f"cli_snapshot:{item.get('cli')}@{item.get('captured_at') or 'unknown'}"
        if label not in merged_sources:
            merged_sources.append(label)
    assertions = structured_capability_assertions(
        values,
        sources=merged_sources,
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
        "sources": merged_sources,
        "source_urls": list(source_urls),
        "evidence_kind": evidence_kind,
        "cli_snapshot_evidence": cli_evidence,
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
