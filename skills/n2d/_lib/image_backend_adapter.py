#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n2d image backend adapter layer.

This module normalizes image-generation backends into one capability model so
stage scripts can ask for capabilities instead of branching on vendor names.

采集日期：2026-06-22
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:
    from n2d_contract import classify_image_backend, image_identity_profile
except Exception:  # pragma: no cover
    from .n2d_contract import classify_image_backend, image_identity_profile  # type: ignore

try:
    import image_backends
except Exception:  # pragma: no cover
    image_backends = None  # type: ignore

try:
    import image_backend_standards
except Exception:  # pragma: no cover
    try:
        from . import image_backend_standards  # type: ignore
    except Exception:
        image_backend_standards = None  # type: ignore


CATALOG_VERIFIED = {
    "date": "2026-06-22",
    "sources": [
        {
            "name": "OpenAI image generation guide + GPT Image 2 docs",
            "url": "https://developers.openai.com/api/docs/guides/image-generation",
            "facts": [
                "official image generation is exposed through the Images API and Responses image-generation tool",
                "GPT Image models include gpt-image-2; the model surface supports text+image inputs and image outputs",
                "official image editing supports one or more source images and high-fidelity image inputs where the selected model allows it",
                "current model names, sizes, quality parameters, and pricing must come from per-run official refresh evidence",
            ],
        },
        {
            "name": "Google Gemini image generation guide",
            "url": "https://ai.google.dev/gemini-api/docs/image-generation",
            "facts": [
                "Gemini native image generation uses generateContent-style multimodal parts",
                "Nano Banana/Gemini image model names and reference budgets are model-specific",
                "current model names, reference budgets, and safety/usage limits must come from per-run official refresh evidence",
            ],
        },
        {
            "name": "Google Vertex AI image overview",
            "url": "https://cloud.google.com/vertex-ai/generative-ai/docs/image/overview",
            "facts": ["Vertex AI exposes Gemini and Imagen image generation/editing models"],
        },
    ],
}


BACKEND_API_ADAPTERS: Dict[str, Dict[str, Any]] = {
    "codex": {
        "label": "Codex CLI image_generation",
        "adapter_kind": "codex_cli",
        "official": True,
        "auto_runnable": True,
        "env_keys": (),
        "probe_backend": "codex",
        "api_surface": "codex exec --image ...",
        "transport": "cli_image_flags",
        "output": "png_file",
        "generation_modes": ("text2image", "image_reference"),
        "reference_input": {
            "mode": "multi_image_flags",
            "max_total": int(os.environ.get("N2D_CODEX_MAX_REFERENCE_IMAGES", "24")),
            "character_refs": None,
            "object_refs": None,
            "style_refs": None,
        },
        "native_subject": False,
        "subject_registration": False,
        "supports_edit": False,
        "supports_mask": False,
        "supports_high_fidelity_reference": True,
        "supports_text_rendering": "medium",
        "cost_tier": "project_default",
        "best_for": ("default_n2d", "multi_reference", "agentic_prompt_repair"),
        "limitations": ("no_persistent_subject_id", "reference_budget_local_policy"),
        "evidence": {"verified_at": "2026-06-22", "source": "local codex CLI capability: codex exec --image"},
    },
    "openai": {
        "label": "OpenAI Images API / Responses image tool",
        "adapter_kind": "openai_images",
        "official": True,
        "auto_runnable": True,
        "env_keys": ("OPENAI_API_KEY",),
        "probe_backend": "openai",
        "api_surface": "/v1/images/generations + /v1/images/edits + Responses image_generation tool",
        "model_hint": "use current official image model from per-run refresh evidence",
        "transport": "multipart_or_sdk",
        "output": "b64_json",
        "generation_modes": ("text2image", "image_edit", "multi_turn_edit"),
        "reference_input": {
            "mode": "image_edits_multipart",
            "max_total": None,
            "character_refs": None,
            "object_refs": None,
            "style_refs": None,
        },
        "native_subject": False,
        "subject_registration": False,
        "supports_edit": True,
        "supports_mask": True,
        "supports_high_fidelity_reference": True,
        "supports_text_rendering": "high",
        "cost_tier": "usage_tokens",
        "best_for": ("high_fidelity_edit", "text_rendering", "prompt_iterate"),
        "limitations": ("no_persistent_subject_id", "transparent_background_not_for_gpt_image_2"),
        "evidence": {"verified_at": "2026-06-20", "source": CATALOG_VERIFIED["sources"][0]["url"]},
    },
    "dreamina": {
        "label": "Dreamina/即梦官方 CLI",
        "adapter_kind": "dreamina_official_cli",
        "official": True,
        "auto_runnable": True,
        "env_keys": (),
        "probe_backend": "dreamina",
        "api_surface": "official logged-in CLI",
        "transport": "official_cli_assets",
        "output": "png_file",
        "generation_modes": ("text2image", "image_reference"),
        "reference_input": {"mode": "official_cli_references", "max_total": None},
        "native_subject": False,
        "subject_registration": False,
        "supports_edit": True,
        "supports_mask": False,
        "supports_high_fidelity_reference": True,
        "supports_text_rendering": "medium",
        "cost_tier": "credits",
        "best_for": ("same_ecosystem_with_seedance", "fast_iteration"),
        "limitations": ("no_persistent_subject_id", "official_cli_must_be_logged_in"),
        "evidence": {"verified_at": "manual_required", "source": "refresh before paid use"},
    },
    "seedream": {
        "label": "Seedream Universal Reference",
        "adapter_kind": "seedream_api",
        "official": True,
        "auto_runnable": False,
        "env_keys": ("SEEDREAM_API_KEY", "ARK_API_KEY"),
        "probe_backend": "seedream",
        "api_surface": "official API",
        "transport": "api_reference_assets",
        "output": "png_file_or_url",
        "generation_modes": ("text2image", "image_reference", "universal_reference"),
        "reference_input": {"mode": "universal_reference", "max_total": 14},
        "native_subject": True,
        "subject_registration": True,
        "supports_edit": True,
        "supports_mask": False,
        "supports_high_fidelity_reference": True,
        "supports_text_rendering": "medium",
        "cost_tier": "provider_pricing",
        "best_for": ("core_character_consistency", "high_risk_identity", "multi_reference"),
        "limitations": ("adapter_needs_official_endpoint_refresh",),
        "evidence": {"verified_at": "manual_required", "source": "refresh before paid use"},
    },
    "kling": {
        "label": "Kling subject library",
        "adapter_kind": "kling_subject_library",
        "official": True,
        "auto_runnable": False,
        "env_keys": ("KLING_ACCESS_KEY", "KLING_SECRET_KEY"),
        "probe_backend": "kling",
        "api_surface": "official API / subject library",
        "transport": "subject_id_plus_references",
        "output": "png_file_or_url",
        "generation_modes": ("image_reference", "subject_library", "custom_model"),
        "reference_input": {"mode": "subject_library", "max_total": None},
        "native_subject": True,
        "subject_registration": True,
        "supports_edit": True,
        "supports_mask": False,
        "supports_high_fidelity_reference": True,
        "supports_text_rendering": "medium",
        "cost_tier": "provider_pricing",
        "best_for": ("multi_character", "core_character_consistency", "subject_library"),
        "limitations": ("adapter_needs_official_endpoint_refresh",),
        "evidence": {"verified_at": "manual_required", "source": "refresh before paid use"},
    },
    "nano_banana": {
        "label": "Gemini / Nano Banana image generation",
        "adapter_kind": "gemini_generate_content",
        "official": True,
        "auto_runnable": True,
        "env_keys": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "probe_backend": "gemini",
        "api_surface": "models.generateContent",
        "model_hint": "use current Gemini/Nano Banana image model from per-run refresh evidence",
        "transport": "generate_content_parts",
        "output": "inline_image_part",
        "generation_modes": ("text2image", "image_reference", "multimodal_reference"),
        "reference_input": {
            "mode": "gemini_parts",
            "max_total": 14,
            "character_refs": 5,
            "object_refs": 10,
            "style_refs": 3,
        },
        "native_subject": False,
        "subject_registration": False,
        "supports_edit": True,
        "supports_mask": False,
        "supports_high_fidelity_reference": True,
        "supports_text_rendering": "high",
        "cost_tier": "provider_pricing",
        "best_for": ("text_rendering", "object_fidelity", "multimodal_reference"),
        "limitations": ("no_persistent_subject_id", "reference_budget_model_specific"),
        "evidence": {"verified_at": "2026-06-20", "source": CATALOG_VERIFIED["sources"][1]["url"]},
    },
    "sora": {
        "label": "Sora Character Cameo",
        "adapter_kind": "sora_cameo_manual",
        "official": True,
        "auto_runnable": False,
        "env_keys": (),
        "probe_backend": "sora",
        "api_surface": "manual/official product flow",
        "transport": "cameo_reference",
        "output": "manual_asset",
        "generation_modes": ("character_cameo",),
        "reference_input": {"mode": "cameo", "max_total": None},
        "native_subject": True,
        "subject_registration": True,
        "supports_edit": False,
        "supports_mask": False,
        "supports_high_fidelity_reference": True,
        "supports_text_rendering": "medium",
        "cost_tier": "manual",
        "best_for": ("legacy_manual_character",),
        "limitations": ("manual_only", "refresh_before_use"),
        "evidence": {"verified_at": "manual_required", "source": "refresh before paid use"},
    },
}


def canonical_backend(raw: Optional[str]) -> Tuple[str, str]:
    canonical, status = classify_image_backend(raw or "")
    return canonical, status


def backend_adapter(raw: Optional[str]) -> Dict[str, Any]:
    canonical, status = canonical_backend(raw)
    key = canonical if status == "approved" else str(raw or "").strip().lower()
    identity = image_identity_profile(canonical or key)
    adapter = dict(BACKEND_API_ADAPTERS.get(canonical) or {})
    if not adapter:
        adapter = {
            "label": key or "unknown",
            "adapter_kind": "unknown",
            "official": False,
            "auto_runnable": False,
            "env_keys": (),
            "probe_backend": key,
            "api_surface": "unknown",
            "transport": "manual",
            "output": "unknown",
            "generation_modes": (),
            "reference_input": {"mode": "unknown", "max_total": 0},
            "native_subject": False,
            "subject_registration": False,
            "limitations": ("unknown_backend",),
            "evidence": {"verified_at": "missing", "source": "unknown"},
        }
    adapter["canonical"] = canonical or key
    adapter["classification"] = status
    adapter["identity_profile"] = identity
    adapter["persistent_subject"] = bool(identity.get("persistent_subject") or adapter.get("native_subject"))
    adapter["multi_reference"] = bool(identity.get("multi_reference") or adapter.get("reference_input", {}).get("max_total"))
    return adapter


def adapter_catalog() -> Dict[str, Any]:
    return {
        "kind": "n2d_image_backend_adapter_catalog",
        "verified": CATALOG_VERIFIED,
        "backends": {k: backend_adapter(k) for k in BACKEND_API_ADAPTERS},
    }


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "是", "需要"}


def normalize_workload(raw: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    raw = dict(raw or {})
    characters = int(raw.get("characters") or raw.get("character_count") or 0)
    references = int(raw.get("reference_images") or raw.get("reference_image_count") or 0)
    return {
        "characters": characters,
        "reference_images": references,
        "has_characters": _as_bool(raw.get("has_characters")) or characters > 0 or _as_bool(raw.get("core_character")),
        "core_character": _as_bool(raw.get("core_character")),
        "multi_character": _as_bool(raw.get("multi_character")) or characters >= 2,
        "closeup": _as_bool(raw.get("closeup")),
        "strong_emotion": _as_bool(raw.get("strong_emotion")),
        "extreme_angle": _as_bool(raw.get("extreme_angle")),
        "needs_edit": _as_bool(raw.get("needs_edit")),
        "needs_mask": _as_bool(raw.get("needs_mask") or raw.get("needs_inpaint")),
        "text_rendering": _as_bool(raw.get("text_rendering") or raw.get("critical_text")),
        "needs_persistent_subject": _as_bool(raw.get("needs_persistent_subject")),
        "needs_seed": _as_bool(raw.get("needs_seed") or raw.get("reproducible")),
        "official_only": True if raw.get("official_only") is None else _as_bool(raw.get("official_only")),
    }


def score_backend(adapter: Mapping[str, Any], workload: Mapping[str, Any]) -> Dict[str, Any]:
    w = normalize_workload(workload)
    score = 0
    blockers: List[str] = []
    warnings: List[str] = []
    strengths: List[str] = []
    ref = adapter.get("reference_input") if isinstance(adapter.get("reference_input"), Mapping) else {}

    if w["official_only"] and not adapter.get("official"):
        blockers.append("backend is not marked official")
    if w["needs_edit"] and not adapter.get("supports_edit"):
        blockers.append("workload needs image editing but backend adapter has no edit path")
    if w["needs_mask"] and not adapter.get("supports_mask"):
        blockers.append("workload needs mask/inpaint but backend adapter has no mask path")
    max_total = ref.get("max_total")
    if isinstance(max_total, int) and max_total > 0 and w["reference_images"] > max_total:
        blockers.append(f"reference image count {w['reference_images']} exceeds backend budget {max_total}")

    if adapter.get("persistent_subject"):
        score += 30
        strengths.append("persistent_subject")
    elif w["needs_persistent_subject"]:
        warnings.append("no persistent subject id; use reference_group/face_embedding/LoRA fallback")
        score -= 15
    if adapter.get("multi_reference"):
        score += 15
        strengths.append("multi_reference")
    if adapter.get("supports_high_fidelity_reference"):
        score += 10
        strengths.append("high_fidelity_reference")
    if w["multi_character"] and adapter.get("persistent_subject"):
        score += 15
    if w["core_character"] and (w["closeup"] or w["strong_emotion"] or w["extreme_angle"]):
        score += 20 if adapter.get("persistent_subject") else -10
    if w["text_rendering"] and adapter.get("supports_text_rendering") == "high":
        score += 18
        strengths.append("text_rendering")
    if w["needs_edit"] and adapter.get("supports_edit"):
        score += 12
    if adapter.get("classification") == "approved":
        score += 5
    if adapter.get("evidence", {}).get("verified_at") in {"manual_required", "missing"}:
        warnings.append("official API details must be refreshed before paid use")
        score -= 3

    verdict = "blocked" if blockers else ("review" if warnings else "ok")
    return {
        "backend": adapter.get("canonical"),
        "label": adapter.get("label"),
        "score": score,
        "verdict": verdict,
        "blockers": blockers,
        "warnings": warnings,
        "strengths": strengths,
    }


def recommend_backend(
    current: Optional[str],
    workload: Optional[Mapping[str, Any]] = None,
    candidates: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    w = normalize_workload(workload)
    cand = list(candidates or BACKEND_API_ADAPTERS.keys())
    scored = [score_backend(backend_adapter(name), w) for name in cand]
    scored.sort(key=lambda row: (row["verdict"] == "blocked", -int(row["score"])))
    cur = score_backend(backend_adapter(current), w)
    best = scored[0] if scored else cur
    upgrade = cur["verdict"] == "blocked" or int(best["score"]) >= int(cur["score"]) + 20
    if cur["backend"] == best["backend"]:
        upgrade = False
    return {
        "kind": "n2d_image_backend_recommendation",
        "verified": CATALOG_VERIFIED,
        "current": cur,
        "recommended": best,
        "upgrade_recommended": upgrade,
        "workload": w,
        "candidates": scored,
        "adapter": backend_adapter(best.get("backend")),
    }


def probe(raw: Optional[str]) -> Dict[str, Any]:
    adapter = backend_adapter(raw)
    if image_backends is None:
        status, detail = "unknown", "image_backends probe module unavailable"
    else:
        status, detail = image_backends.probe_backend(adapter.get("canonical") or raw)
    return {"backend": adapter.get("canonical"), "status": status, "detail": detail, "adapter": adapter}


def scan() -> Dict[str, Any]:
    if image_backends is None:
        return {
            "kind": "n2d_image_backend_scan",
            "results": [],
            "usable_backends": [],
            "needs_confirmation_backends": [],
            "down_backends": [],
            "summary": {"usable_count": 0, "needs_confirmation_count": 0, "down_count": 0},
            "error": "image_backends probe module unavailable",
        }
    payload = image_backends.scan_backends()
    for item in payload.get("results", []):
        backend = item.get("backend")
        item["adapter"] = backend_adapter(str(backend or "")).get("label")
    return payload


def standards_catalog() -> Dict[str, Any]:
    if image_backend_standards is None:
        return {"kind": "n2d_image_capability_standards", "status": "unavailable", "standards": []}
    return image_backend_standards.catalog()


def standard_plan(current: Optional[str], workload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    adapter = backend_adapter(current)
    if image_backend_standards is None:
        return {
            "kind": "n2d_image_backend_standard_plan",
            "backend": adapter.get("canonical"),
            "status": "unavailable",
            "standards": [],
            "required_mitigations": [],
        }
    return image_backend_standards.plan_for_backend(adapter, normalize_workload(workload))


def refresh_evidence_path(root: str, backend: Optional[str]) -> Path:
    canonical, _status = canonical_backend(backend)
    key = canonical or str(backend or "unknown").strip().lower() or "unknown"
    return Path(root) / "生产数据" / "image_backend_capabilities" / f"{key}.json"


def load_refresh_evidence(root: str, backend: Optional[str]) -> Optional[Dict[str, Any]]:
    path = refresh_evidence_path(root, backend)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def refresh_evidence_status(root: str, backend: Optional[str], today: Optional[dt.date] = None) -> Dict[str, Any]:
    today = today or dt.date.today()
    evidence = load_refresh_evidence(root, backend)
    path = refresh_evidence_path(root, backend)
    if not evidence:
        return {"status": "missing", "path": str(path), "message": "no per-run official API refresh evidence"}
    raw_date = str(evidence.get("verified_at") or evidence.get("date") or "")
    try:
        verified = dt.date.fromisoformat(raw_date[:10])
    except ValueError:
        return {"status": "bad_date", "path": str(path), "message": f"invalid verified_at: {raw_date}"}
    age = max(0, (today - verified).days)
    return {
        "status": "fresh" if age == 0 else "stale",
        "path": str(path),
        "verified_at": verified.isoformat(),
        "age_days": age,
        "message": "fresh for this run" if age == 0 else f"refresh evidence is {age} day(s) old",
    }


def write_refresh_evidence(
    root: str,
    backend: Optional[str],
    *,
    sources: Sequence[str],
    note: str = "",
    today: Optional[str] = None,
) -> Path:
    path = refresh_evidence_path(root, backend)
    path.parent.mkdir(parents=True, exist_ok=True)
    date_s = today or dt.date.today().isoformat()
    payload = {
        "kind": "n2d_image_backend_refresh_evidence",
        "backend": backend_adapter(backend).get("canonical"),
        "verified_at": date_s,
        "sources": list(sources),
        "note": note,
        "adapter": backend_adapter(backend),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _parse_kv_pairs(items: Iterable[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--workload expects key=value, got: {item}")
        key, value = item.split("=", 1)
        if value.isdigit():
            out[key] = int(value)
        else:
            out[key] = value
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d image backend adapter layer")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("catalog")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("inspect")
    p.add_argument("backend")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("recommend")
    p.add_argument("--backend", default="Codex")
    p.add_argument("--workload", action="append", default=[], help="key=value, e.g. core_character=true")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("probe")
    p.add_argument("backend")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("scan")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("standards")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("plan-standards")
    p.add_argument("--backend", default="Codex")
    p.add_argument("--workload", action="append", default=[], help="key=value, e.g. multi_character=true")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("refresh-status")
    p.add_argument("root")
    p.add_argument("--backend", default="Codex")
    p.add_argument("--today", default=None)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("record-refresh")
    p.add_argument("root")
    p.add_argument("--backend", default="Codex")
    p.add_argument("--source", action="append", required=True)
    p.add_argument("--note", default="")
    p.add_argument("--date", default=None)

    ns = ap.parse_args(argv)
    if ns.cmd == "catalog":
        payload = adapter_catalog()
    elif ns.cmd == "inspect":
        payload = backend_adapter(ns.backend)
    elif ns.cmd == "recommend":
        payload = recommend_backend(ns.backend, _parse_kv_pairs(ns.workload))
    elif ns.cmd == "probe":
        payload = probe(ns.backend)
    elif ns.cmd == "scan":
        payload = scan()
    elif ns.cmd == "standards":
        payload = standards_catalog()
    elif ns.cmd == "plan-standards":
        payload = standard_plan(ns.backend, _parse_kv_pairs(ns.workload))
    elif ns.cmd == "refresh-status":
        today = dt.date.fromisoformat(ns.today) if ns.today else None
        payload = refresh_evidence_status(ns.root, ns.backend, today)
    elif ns.cmd == "record-refresh":
        path = write_refresh_evidence(ns.root, ns.backend, sources=ns.source, note=ns.note, today=ns.date)
        payload = {"path": str(path), "status": "written"}
    else:  # pragma: no cover
        raise AssertionError(ns.cmd)
    if getattr(ns, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
