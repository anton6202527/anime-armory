#!/usr/bin/env python3
"""Craft-profile policy for novel scene planning.

This module is deliberately platform-agnostic.  A project's target platform
may affect market advice, but it must never silently select the craft contract
used by scene cards or the manuscript map.
"""
from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from typing import Any


CRAFT_PROFILE_KEY = "创作工艺档"
DEFAULT_CRAFT_PROFILE = "genre_novel"
CRAFT_PROFILE_VALUES = (
    "commercial_serial",
    "genre_novel",
    "literary",
    "experimental",
)

_ALIASES = {
    "commercial_serial": "commercial_serial",
    "commercial": "commercial_serial",
    "商业": "commercial_serial",
    "商业连载": "commercial_serial",
    "商业连载型": "commercial_serial",
    "genre_novel": "genre_novel",
    "genre": "genre_novel",
    "类型": "genre_novel",
    "类型小说": "genre_novel",
    "类型文学": "genre_novel",
    "literary": "literary",
    "文学": "literary",
    "文学小说": "literary",
    "纯文学": "literary",
    "experimental": "experimental",
    "实验": "experimental",
    "实验小说": "experimental",
    "实验性": "experimental",
}

# Traditional profiles retain the complete classical scene contract.  A
# literary scene only needs an attributable narrative position (`pov` or the
# broader `viewpoint`); experimental work has no subjective field-presence
# blocker.  In both flexible profiles narrative effectiveness remains human
# judgement and therefore advisory under B10.
CORE_SCENE_FIELDS = ("pov", "desire", "obstacle", "conflict")
TRADITIONAL_SCENE_FIELDS = ("turn", "value_shift")
LITERARY_ATTRIBUTION_FIELDS = ("pov", "viewpoint")
LITERARY_ADVISORY_FIELDS = ("desire", "obstacle", "conflict")
TRADITIONAL_PROFILES = frozenset({"commercial_serial", "genre_novel"})
FLEXIBLE_PROFILES = frozenset({"literary", "experimental"})
CRAFT_CONTRACT_SNAPSHOT_KIND = "novel_craft_contract_snapshot"

# `reveal_or_payoff` is the historical field and remains a valid revelation
# mechanism.  The other fields make non-plot-centric movement explicit instead
# of forcing it into `turn` merely to satisfy a checker.
NARRATIVE_FUNCTION_FIELDS = (
    "turn",
    "value_shift",
    "revelation",
    "reveal_or_payoff",
    "relation_drift",
    "perceptual_shift",
    "motif_return",
    "deliberate_stasis",
)

NARRATIVE_FUNCTION_LABELS = {
    "turn": "局面转折",
    "value_shift": "价值变化",
    "revelation": "揭示",
    "reveal_or_payoff": "揭示/兑现",
    "relation_drift": "关系微移",
    "perceptual_shift": "感知变化",
    "motif_return": "意象复现",
    "deliberate_stasis": "有意停滞",
}


def normalize_craft_profile(value: Any) -> str:
    """Canonicalize aliases; only a missing value receives the legacy default.

    Unknown values remain visible so `settings set --force` keeps the user's
    explicit custom input.  Runtime consumers must report the unsupported
    adapter instead of silently replacing that choice.
    """
    text = str(value or "").strip()
    if not text:
        return DEFAULT_CRAFT_PROFILE
    return _ALIASES.get(text, _ALIASES.get(text.lower(), text))


def resolve_craft_profile(settings_or_value: Mapping[str, Any] | Any) -> str:
    """Resolve profile from a settings mapping or a raw value.

    No target-platform or genre inference is intentionally present here.
    """
    if isinstance(settings_or_value, Mapping):
        value = settings_or_value.get(CRAFT_PROFILE_KEY)
        if value in (None, ""):
            value = settings_or_value.get("craft_profile")
        return normalize_craft_profile(value)
    return normalize_craft_profile(settings_or_value)


def requires_traditional_turn(profile: Any) -> bool:
    # Unknown custom profiles take the conservative contract until an adapter
    # is added, while callers also emit an explicit unsupported-profile block.
    return normalize_craft_profile(profile) not in FLEXIBLE_PROFILES


def is_supported_craft_profile(profile: Any) -> bool:
    return normalize_craft_profile(profile) in CRAFT_PROFILE_VALUES


def required_scene_fields(profile: Any) -> tuple[str, ...]:
    normalized = normalize_craft_profile(profile)
    if normalized in TRADITIONAL_PROFILES or normalized not in CRAFT_PROFILE_VALUES:
        return CORE_SCENE_FIELDS + TRADITIONAL_SCENE_FIELDS
    return ()


def _has_value(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "false", "no", "none", "否", "无"}
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def narrative_functions(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return the explicitly registered narrative functions on one scene/chapter row."""
    return {
        field: record.get(field)
        for field in NARRATIVE_FUNCTION_FIELDS
        if _has_value(record.get(field))
    }


def missing_required_scene_fields(scene: Mapping[str, Any], profile: Any) -> list[str]:
    normalized = normalize_craft_profile(profile)
    missing = [field for field in required_scene_fields(normalized) if not _has_value(scene.get(field))]
    if normalized == "literary" and not any(_has_value(scene.get(field)) for field in LITERARY_ATTRIBUTION_FIELDS):
        missing.append("pov|viewpoint")
    return missing


def missing_literary_dynamics(scene: Mapping[str, Any], profile: Any) -> list[str]:
    """Conventional dynamics absent from a literary scene (advisory only)."""
    if normalize_craft_profile(profile) != "literary":
        return []
    return [field for field in LITERARY_ADVISORY_FIELDS if not _has_value(scene.get(field))]


def _file_snapshot(project_root: str, relpath: str) -> dict[str, Any]:
    path = os.path.join(project_root, *relpath.split("/"))
    if not os.path.isfile(path):
        return {"path": relpath, "exists": False, "sha256": None}
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": relpath, "exists": True, "sha256": digest.hexdigest()}


def build_craft_contract_snapshot(project_root: str, profile: Any) -> dict[str, Any]:
    """Fingerprint the exact inputs that determine manuscript-map craft checks.

    The snapshot binds the canonical selected profile and scene-card content,
    while retaining `_设置.md` path/existence only as provenance.  Unrelated
    setting edits therefore stay fresh, but a profile or scene-card edit cannot
    let downstream workflow reuse an old pass.
    """
    normalized = normalize_craft_profile(profile)
    settings_path = os.path.join(project_root, "_设置.md")
    inputs = {
        # Keep provenance for the choice-point file without hashing unrelated
        # settings (platform, disclosure mode, etc.) into the craft contract.
        "settings": {
            "path": "_设置.md",
            "exists": os.path.isfile(settings_path),
            "craft_profile": normalized,
        },
        "scene_cards": _file_snapshot(project_root, "设定/scene_cards.json"),
    }
    canonical = json.dumps(
        {"craft_profile": normalized, "scene_cards": inputs["scene_cards"]},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "schema_version": 1,
        "kind": CRAFT_CONTRACT_SNAPSHOT_KIND,
        "craft_profile": normalized,
        "inputs": inputs,
        "aggregate_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def validate_craft_contract_snapshot(
    project_root: str,
    snapshot: Mapping[str, Any] | None,
    profile: Any,
) -> dict[str, Any]:
    """Compare a stored craft snapshot with the project's current inputs."""
    current = build_craft_contract_snapshot(project_root, profile)
    issues: list[str] = []
    stored = snapshot if isinstance(snapshot, Mapping) else {}
    if stored.get("kind") != CRAFT_CONTRACT_SNAPSHOT_KIND:
        issues.append("missing_or_legacy_snapshot")
    else:
        stored_profile = normalize_craft_profile(stored.get("craft_profile"))
        if stored_profile != current["craft_profile"]:
            issues.append("craft_profile_changed")
        stored_inputs = stored.get("inputs") if isinstance(stored.get("inputs"), Mapping) else {}
        before = stored_inputs.get("scene_cards") if isinstance(stored_inputs.get("scene_cards"), Mapping) else {}
        after = current["inputs"]["scene_cards"]
        if before.get("exists") != after.get("exists") or before.get("sha256") != after.get("sha256"):
            issues.append("scene_cards_changed")
        if stored.get("aggregate_sha256") != current["aggregate_sha256"] and not issues:
            issues.append("aggregate_changed")
    return {
        "fresh": not issues,
        "issues": issues,
        "current": current,
    }
