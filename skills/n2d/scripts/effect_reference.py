#!/usr/bin/env python3
"""Query the n2d signature-effect (特效镜头) prompt library.

特效镜头 are named composite "signature shots" (穿云而入 / 子弹时间 / 产品扫光 …):
each bundles a camera move + subject action + FX + timing into one ready-to-paste
core prompt. Unlike 运镜, these carry no visual reference media — the manifest is a
pure, offline prompt index. Video prompt authoring pulls the core prompt and the
identity-lock negatives from here instead of re-inventing them per clip.

Consumers:
- n2d_const.SIGNATURE_EFFECT_LEXICON (built from this manifest at import time)
- n2d_logic.normalize_signature_effect()
- n2d-video prompt_pack signature-effect injection
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

LINE_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = LINE_ROOT / "references" / "特效镜头"
MANIFEST_PATH = REFERENCE_DIR / "manifest.json"

REQUIRED_EFFECT_FIELDS = (
    "id",
    "name_zh",
    "name_en",
    "category",
    "camera_move",
    "core_prompt_zh",
    "core_prompt_en",
    "identity_risk",
)
IDENTITY_RISK_LEVELS = ("low", "medium", "high")


class EffectReferenceError(RuntimeError):
    pass


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - trivial IO wrapper
        raise EffectReferenceError(f"cannot read manifest {path}: {exc}") from exc
    if not isinstance(manifest.get("effects"), list):
        raise EffectReferenceError(f"manifest has no effects array: {path}")
    return manifest


def effect_terms(effect: dict[str, Any]) -> set[str]:
    values = [
        effect.get("id"),
        effect.get("name_zh"),
        effect.get("name_en"),
        *(effect.get("aliases_zh") or []),
        *(effect.get("aliases_en") or []),
    ]
    return {str(value).strip().casefold() for value in values if str(value or "").strip()}


def resolve_effect(manifest: dict[str, Any], query: str) -> dict[str, Any]:
    needle = str(query or "").strip().casefold()
    if not needle:
        raise EffectReferenceError("effect query is empty")
    effects = [e for e in manifest["effects"] if isinstance(e, dict)]
    exact = [e for e in effects if needle in effect_terms(e)]
    if len(exact) == 1:
        return exact[0]
    partial = [e for e in effects if any(needle in term for term in effect_terms(e))]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise EffectReferenceError(f"effect not found: {query}")
    names = ", ".join(str(e.get("id") or e.get("name_zh")) for e in partial[:8])
    raise EffectReferenceError(f"effect query is ambiguous: {query} -> {names}")


def self_check(manifest: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    effects = [e for e in manifest["effects"] if isinstance(e, dict)]
    for effect in effects:
        eid = str(effect.get("id") or "")
        for field in REQUIRED_EFFECT_FIELDS:
            if not str(effect.get(field) or "").strip():
                errors.append(f"{eid or '<no-id>'} missing required field: {field}")
        if eid in seen_ids:
            errors.append(f"duplicate effect id: {eid}")
        seen_ids.add(eid)
        risk = str(effect.get("identity_risk") or "")
        if risk and risk not in IDENTITY_RISK_LEVELS:
            errors.append(f"{eid} identity_risk not in {IDENTITY_RISK_LEVELS}: {risk}")
        neg = effect.get("negatives")
        if neg is not None and not isinstance(neg, list):
            errors.append(f"{eid} negatives must be a list")
    return {"ok": not errors, "effect_count": len(effects), "errors": errors}


def emit(value: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return
    if isinstance(value, list):
        for item in value:
            print(f"{item['id']}: {item['name_zh']} / {item['name_en']} [{item.get('category')}]")
        return
    if isinstance(value, dict) and "effect_count" in value:
        for key, item in value.items():
            print(f"{key}: {item}")
        return
    for key, item in value.items():
        print(f"{key}: {item}")


def effect_payload(effect: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": effect.get("id"),
        "name_zh": effect.get("name_zh"),
        "name_en": effect.get("name_en"),
        "category": effect.get("category"),
        "camera_move": effect.get("camera_move"),
        "identity_risk": effect.get("identity_risk"),
        "aliases_zh": effect.get("aliases_zh") or [],
        "use_when": effect.get("use_when"),
        "avoid_when": effect.get("avoid_when"),
        "core_prompt_zh": effect.get("core_prompt_zh"),
        "core_prompt_en": effect.get("core_prompt_en"),
        "negatives": effect.get("negatives") or [],
        "platform_refs": effect.get("platform_refs") or [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List signature effects (offline)")
    list_parser.add_argument("--json", action="store_true")
    list_parser.add_argument("--category", default=None, help="Filter by category")

    show_parser = subparsers.add_parser("show", help="Show one effect's core prompt and metadata")
    show_parser.add_argument("effect")
    show_parser.add_argument("--json", action="store_true")

    check_parser = subparsers.add_parser("self-check", help="Validate manifest structure")
    check_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    manifest = load_manifest()

    if args.command == "list":
        payload = [
            {
                "id": e.get("id"),
                "name_zh": e.get("name_zh"),
                "name_en": e.get("name_en"),
                "category": e.get("category"),
                "identity_risk": e.get("identity_risk"),
            }
            for e in manifest["effects"]
            if isinstance(e, dict) and (not args.category or e.get("category") == args.category)
        ]
        emit(payload, args.json)
        return 0

    if args.command == "self-check":
        payload = self_check(manifest)
        emit(payload, args.json)
        return 0 if payload["ok"] else 1

    if args.command == "show":
        emit(effect_payload(resolve_effect(manifest, args.effect)), args.json)
        return 0

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EffectReferenceError as exc:
        print(f"effect reference error: {exc}", file=sys.stderr)
        raise SystemExit(2)
