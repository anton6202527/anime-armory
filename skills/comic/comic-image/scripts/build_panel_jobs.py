#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 panel_script.json 与 layout.json 生成逐格出图任务包。"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import reference_planner  # noqa: E402
import codex_panel_runner as panel_gate  # noqa: E402

COMIC_LIB = Path(__file__).resolve().parents[2] / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
try:
    from image_backend_adapter import ImageBackendCapabilities, intersect_with_execution, resolve_capabilities
    from image_execution_adapter import resolve_execution_adapter
except Exception:  # pragma: no cover - keep job building usable in partially-copied skill folders
    ImageBackendCapabilities = Any  # type: ignore
    resolve_capabilities = None  # type: ignore
    intersect_with_execution = None  # type: ignore
    resolve_execution_adapter = None  # type: ignore
from comic_image_prompt_compiler import compile_prompt
from progress import update_stage


PRESERVE_GENERATION_KEYS = {
    "status",
    "result_path",
    "source",
    "model",
    "generated_at",
    "backend_version",
    "artifact_sha256",
    "attempt",
    "reference_input_mode",
    "reference_input_count",
    "reference_manifest",
    "generated_from_contract_sha256",
    "generated_from_submit_prompt_sha256",
    "post_qc",
    "accepted_at",
    "last_error",
    "generated_from_execution_input_sha256",
    "resolution_provenance",
    "master_path",
}
LEGACY_MAX_REFERENCE_IMAGES_PER_JOB = 6
LEGACY_SINGLE_CHARACTER_REFERENCE_LIMIT = 4
LEGACY_MULTI_CHARACTER_REFERENCE_LIMIT = 2
REFERENCE_VIEW_PRIORITY = {
    "anchor_path": 0,
    "anchor": 0,
    "primary_path": 0,
    "face": 1,
    "front": 2,
    "three_quarter": 3,
    "side": 4,
    "back": 5,
}
REFERENCE_ID_PREFIXES = ("CHAR_", "MON_", "BEAST_", "ANIMAL_", "LOC_", "PROP_", "WEAPON_", "OUTFIT_", "SYS_", "FX_", "VFX_", "STYLE_")


class ReferencePlanBlocked(ValueError):
    """Raised when deterministic reference/binding contracts are incomplete."""
PRODUCTION_NEGATIVE_CONTRACT = (
    "文字，水印，logo，乱码字，字幕，播放按钮，搜索框，播放器控件，平台 UI，竖排标题，"
    "对白气泡，空白气泡，旁白框，文字框，额外手指，畸形手，手脚混淆，把脚画成手，"
    "脸部漂移，发际线漂移，眼型漂移，眼距漂移，发型漂移，年龄形态换脸，服装漂移，"
    "标志灵纹丢失，场景布局漂移，光位漂移，常驻道具丢失，looking at viewer，"
    "eye contact with camera，front-facing portrait，selfie，低清晰度，低成本彩漫感，"
    "Q版化，过度血腥细节"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def read_setting(root: Path, key: str, default: str) -> str:
    path = root / "_设置.md"
    if not path.is_file():
        return default
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


def load_reference_registry(root: Path) -> dict:
    path = root / "出图" / "共享" / "identity_registry.json"
    if not path.is_file():
        return {}
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def load_finishing_plan(root: Path, chapter: str) -> dict[str, Any]:
    path = root / "出图" / chapter / "finishing" / "finishing_plan.json"
    if not path.is_file():
        return {}
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def finishing_by_panel(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for panel in plan.get("panels") or []:
        if isinstance(panel, dict) and panel.get("panel_id"):
            out[str(panel.get("panel_id"))] = panel
    return out


def path_relative_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def resolve_reference_paths(root: Path, ref_id: str, registry: dict) -> list[dict[str, str]]:
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    asset = assets.get(ref_id) if isinstance(assets, dict) else None
    candidates: list[tuple[str, Path]] = []
    if isinstance(asset, dict):
        for key in ("anchor_path", "primary_path", "path"):
            raw = asset.get(key)
            if isinstance(raw, str) and raw.strip():
                path = Path(raw)
                candidates.append((key, path if path.is_absolute() else root / path))
        views = asset.get("views") if isinstance(asset.get("views"), dict) else {}
        for key in ("front", "three_quarter", "face", "side", "back"):
            raw = views.get(key) if isinstance(views, dict) else ""
            if isinstance(raw, str) and raw.strip():
                path = Path(raw)
                candidates.append((key, path if path.is_absolute() else root / path))
        for item in asset.get("reference_images") or []:
            raw = item.get("path") if isinstance(item, dict) else item
            if isinstance(raw, str) and raw.strip():
                path = Path(raw)
                role = str(item.get("view") or item.get("role") or "reference_image") if isinstance(item, dict) else "reference_image"
                candidates.append((role, path if path.is_absolute() else root / path))
    shared = root / "出图" / "共享" / "图片"
    for suffix in ("__anchor.png", ".png", ".jpg", ".jpeg", ".webp"):
        candidates.append(("anchor", shared / f"{ref_id}{suffix}"))
    out: list[dict[str, str]] = []
    seen: set[Path] = set()
    for role, path in candidates:
        if path.is_file():
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append({"id": ref_id, "path": path_relative_to_root(root, path), "view": role})
    return out


def compact_metadata(value: Any, *, max_len: int = 460) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, list):
        text = "；".join(compact_metadata(item, max_len=max_len) for item in value)
    elif isinstance(value, dict):
        items = []
        for key, item in value.items():
            item_text = compact_metadata(item, max_len=max_len)
            if item_text:
                items.append(f"{key}:{item_text}")
        text = "；".join(items)
    else:
        text = str(value).strip()
    text = re.sub(r"\s+", " ", text).strip("； ")
    if len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text


def asset_contract(ref_id: str, asset: dict[str, Any]) -> str:
    label = str(asset.get("display_name") or asset.get("name") or ref_id)
    parts = [f"{ref_id}={label}"]
    for key, title in (
        ("character_dna", "角色DNA"),
        ("dna_contract", "定妆契约"),
        ("prop_contract", "道具契约"),
        ("variant_policy", "年龄/形态继承"),
        ("forbidden_inheritance", "禁继承"),
        ("style_contract", "风格契约"),
        ("notes", "备注"),
    ):
        limit = 300 if key in {"character_dna", "prop_contract"} else 180
        text = compact_metadata(asset.get(key), max_len=limit)
        if text:
            parts.append(f"{title}:{text}")
    age_variants = asset.get("age_variants")
    if isinstance(age_variants, dict) and age_variants:
        parts.append("已定义年龄形态:" + ",".join(map(str, age_variants.keys())))
    if str(asset.get("type") or "").lower() == "character" or ref_id.startswith("CHAR_"):
        parts.append("同一角色换年龄、受伤、闭关、觉醒或换装时，只允许改变年龄比例/状态/服饰层，不得换脸、换发际线、换眼型或丢失标志物")
    return "；".join(parts)


def registry_style_contract(registry: dict) -> str:
    parts: list[str] = []
    for key, limit in (("style_contract", 360), ("consistency_policy", 260), ("forbidden_inheritance", 160)):
        text = compact_metadata(registry.get(key), max_len=limit)
        if text:
            parts.append(f"{key}:{text}")
    return "；".join(parts)


def panel_reference_ids(panel: dict) -> list[str]:
    ids: list[str] = []
    for binding in panel.get("character_bindings") or []:
        if isinstance(binding, dict):
            ref_id = str(binding.get("character_id") or binding.get("id") or "").strip()
            if ref_id.startswith(("CHAR_", "MON_", "BEAST_", "ANIMAL_")) and ref_id not in ids:
                ids.append(ref_id)
    for key in ("references", "characters"):
        for raw in panel.get(key) or []:
            ref_id = str(raw).strip()
            if ref_id and ref_id.startswith(REFERENCE_ID_PREFIXES) and ref_id not in ids:
                ids.append(ref_id)
    return ids


def panel_scene_anchor_id(panel: dict) -> str:
    for key in ("scene_anchor_id", "scene_id", "location_id"):
        value = str(panel.get(key) or "").strip()
        if value:
            return value
    for ref_id in panel_reference_ids(panel):
        if ref_id.startswith("LOC_"):
            return ref_id
    return ""


def scene_anchor_contract(panel_script: dict, scene_id: str) -> dict[str, Any]:
    visual_contract = panel_script.get("visual_contract") if isinstance(panel_script.get("visual_contract"), dict) else {}
    anchors = visual_contract.get("scene_anchors") if isinstance(visual_contract.get("scene_anchors"), dict) else {}
    contract = anchors.get(scene_id) if scene_id and isinstance(anchors, dict) else {}
    return contract if isinstance(contract, dict) else {}


def first_contract_value(*values: Any) -> str:
    for value in values:
        text = compact_metadata(value)
        if text:
            return text
    return ""


def panel_continuity_contract(panel: dict, panel_script: dict) -> dict[str, str]:
    scene_id = panel_scene_anchor_id(panel)
    scene_contract = scene_anchor_contract(panel_script, scene_id)
    visual_contract = panel_script.get("visual_contract") if isinstance(panel_script.get("visual_contract"), dict) else {}
    return {
        key: value
        for key, value in {
            "scene_anchor_id": scene_id,
            "spatial_layout": first_contract_value(panel.get("spatial_layout"), panel.get("scene_layout"), scene_contract.get("spatial_layout"), scene_contract.get("layout")),
            "lighting_anchor": first_contract_value(panel.get("lighting_anchor"), panel.get("light_anchor"), scene_contract.get("lighting_anchor"), scene_contract.get("light_anchor")),
            "axis_eyeline": first_contract_value(panel.get("axis_eyeline"), panel.get("axis"), scene_contract.get("axis_eyeline"), scene_contract.get("eyeline_axis")),
            "resident_assets": first_contract_value(panel.get("resident_assets"), scene_contract.get("resident_assets")),
            "gaze_target": first_contract_value(panel.get("gaze_target"), panel.get("eyeline_target")),
            "eyeline_direction": first_contract_value(panel.get("eyeline_direction"), panel.get("gaze_direction")),
            "camera_role": first_contract_value(panel.get("camera_role"), panel.get("pov")),
            "continuity_from": first_contract_value(panel.get("continuity_from"), panel.get("previous_panel")),
            "character_integrity": first_contract_value(panel.get("character_integrity"), panel.get("completeness_notes"), visual_contract.get("character_integrity_policy")),
            "spatial_relationships": first_contract_value(panel.get("spatial_relationships"), panel.get("blocking"), panel.get("staging")),
        }.items()
        if value
    }


def panel_outfit(panel: dict, registry: dict) -> tuple[str, str, dict[str, Any]]:
    """返回 (角色 ref_id, outfit_id, outfit 记录)。

    outfit 子注册表：registry.assets[CHAR_x].outfits[OUTFIT_y] =
    {name, description, reference_images: [path], forbidden}。
    业界已验证的失效模式是"锁了脸锁不住领型/纽扣/花纹"，
    所以换装格必须显式声明 outfit_id 并绑定专属参考图与"绝不"负向清单。
    """
    binding_outfits = [
        str(item.get("outfit_id") or "").strip()
        for item in panel.get("character_bindings") or []
        if isinstance(item, dict) and item.get("outfit_id")
    ]
    outfit_id = str(panel.get("outfit_id") or panel.get("outfit") or (binding_outfits[0] if len(binding_outfits) == 1 else "")).strip()
    if not outfit_id:
        return "", "", {}
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    for ref_id in panel_reference_ids(panel):
        asset = assets.get(ref_id) if isinstance(assets, dict) else None
        outfits = asset.get("outfits") if isinstance(asset, dict) and isinstance(asset.get("outfits"), dict) else {}
        record = outfits.get(outfit_id)
        if isinstance(record, dict):
            return ref_id, outfit_id, record
    return "", outfit_id, {}


def outfit_reference_paths(root: Path, ref_id: str, outfit_id: str, record: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in record.get("reference_images") or []:
        raw = item.get("path") if isinstance(item, dict) else item
        if not isinstance(raw, str) or not raw.strip():
            continue
        path = Path(raw)
        resolved = path if path.is_absolute() else root / path
        if resolved.is_file():
            out.append({"id": ref_id, "path": path_relative_to_root(root, resolved), "view": f"outfit:{outfit_id}"})
    return out


def outfit_contract_text(outfit_id: str, record: dict[str, Any]) -> str:
    parts = [f"本格服装={record.get('name') or outfit_id}"]
    description = compact_metadata(record.get("description"), max_len=200)
    if description:
        parts.append(description)
    forbidden = compact_metadata(record.get("forbidden"), max_len=140)
    if forbidden:
        parts.append("绝不出现：" + forbidden)
    parts.append("领型、纽扣数、布料花纹、配饰按服装参考保持，不得代际漂移")
    return "；".join(parts)


def reference_priority(item: dict[str, str]) -> tuple[int, str]:
    view = str(item.get("view") or "")
    return (REFERENCE_VIEW_PRIORITY.get(view, 99), str(item.get("path") or ""))


def ref_kind(ref_id: str) -> str:
    if ref_id.startswith(("CHAR_", "MON_", "BEAST_", "ANIMAL_")):
        return "character"
    if ref_id.startswith("STYLE_"):
        return "style"
    return "asset"


def _cap_value(caps: Any, name: str, default: int) -> int:
    try:
        value = int(getattr(caps, name))
    except Exception:
        return default
    return max(0, value)


def load_memory_anchor_pins(root: Path, chapter: str) -> dict[str, list[dict[str, str]]]:
    """跨话记忆锚计划（comic-identity/memory_anchor.py 产·文件契约消费，不跨 skill import）。

    长间隔再登场角色把最早定妆钉为最高优先参考——对抗复现间隔越长漂移越大（Gap-Decay）。
    计划缺失/无效 → 空 dict，零行为变化。"""
    path = root / "生产数据" / f"comic_memory_anchor_{chapter}.json"
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, list[dict[str, str]]] = {}
    for row in plan.get("characters") or []:
        if not isinstance(row, dict) or row.get("status") != "ready":
            continue
        cid = str(row.get("character_id") or "")
        refs = [{"id": cid, "path": str(r.get("path") or ""), "role": "memory_anchor"}
                for r in (row.get("pinned_refs") or []) if isinstance(r, dict) and r.get("path")]
        if cid and refs:
            out[cid] = refs
    return out


def reference_plan_for_build(root: Path, chapter: str, supplied: dict[str, Any] | None = None) -> dict[str, Any]:
    fresh = reference_planner.build_plan(root, chapter)
    plan = supplied or fresh
    if plan.get("kind") != reference_planner.KIND or plan.get("chapter") != chapter:
        raise ReferencePlanBlocked("reference plan kind/chapter mismatch")
    if str(plan.get("inputs_fingerprint") or "") != str(fresh.get("inputs_fingerprint") or ""):
        raise ReferencePlanBlocked("reference plan is stale: inputs_fingerprint differs from current project inputs")
    if str(plan.get("plan_sha256") or "") != str(fresh.get("plan_sha256") or ""):
        raise ReferencePlanBlocked("reference plan is stale or was edited without rebuilding: plan_sha256 differs")
    blocks = [finding for finding in plan.get("findings") or [] if isinstance(finding, dict) and finding.get("severity") == "block"]
    if blocks:
        compact = "; ".join(f"{item.get('panel')}:{item.get('code')}" for item in blocks)
        raise ReferencePlanBlocked(f"reference plan blocked: {compact}")
    return plan


def references_from_panel_plan(root: Path, panel_plan: dict[str, Any]) -> list[dict[str, str]]:
    attachments = panel_plan.get("attachment_plan") if isinstance(panel_plan.get("attachment_plan"), dict) else {}
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in attachments.get("selected") or []:
        if not isinstance(raw, dict):
            continue
        path = str(raw.get("path") or "").strip()
        if not path or path in seen:
            continue
        resolved = Path(path) if Path(path).is_absolute() else root / path
        if not resolved.is_file():
            raise ReferencePlanBlocked(f"reference plan attachment disappeared: {path}")
        actual_sha = reference_planner.file_sha256(resolved)
        expected_sha = str(raw.get("sha256") or "")
        if expected_sha and expected_sha != actual_sha:
            raise ReferencePlanBlocked(f"reference plan attachment changed after planning: {path}")
        seen.add(path)
        out.append({
            "id": str(raw.get("id") or raw.get("character_id") or ""),
            "path": path_relative_to_root(root, resolved),
            "view": str(raw.get("role") or "reference"),
            "role": str(raw.get("role") or "reference"),
            "sha256": actual_sha,
            "contract_id": str(raw.get("contract_id") or ""),
            "required": bool(raw.get("required")),
        })
    required_count = int(attachments.get("required_count") or 0)
    if required_count > len(out):
        raise ReferencePlanBlocked(
            f"reference plan selected {len(out)} existing attachments but requires {required_count}; rebuild/split the panel"
        )
    return out


def binding_records(panel_plan: dict[str, Any], registry: dict[str, Any]) -> list[dict[str, Any]]:
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    records: list[dict[str, Any]] = []
    for binding in panel_plan.get("character_bindings") or []:
        if not isinstance(binding, dict):
            continue
        cid = str(binding.get("character_id") or "")
        asset = assets.get(cid) if isinstance(assets.get(cid), dict) else {}
        record: dict[str, Any] = {key: str(binding.get(key) or "") for key in ("character_id", "form_id", "outfit_id", "expression_id", "state_id")}
        record["display_name"] = str(asset.get("display_name") or asset.get("name") or "角色")
        record["character_dna"] = asset.get("character_dna") or asset.get("dna_contract") or {}
        record["variant_policy"] = asset.get("variant_policy") or asset.get("age_variants") or {}
        record["forbidden_inheritance"] = asset.get("forbidden_inheritance") or []
        resolved: dict[str, Any] = {}
        for key, collection_name in (("form_id", "forms"), ("outfit_id", "outfits"), ("expression_id", "expressions"), ("state_id", "states")):
            collection = asset.get(collection_name) if isinstance(asset.get(collection_name), dict) else {}
            item = collection.get(record[key]) if isinstance(collection.get(record[key]), dict) else {}
            resolved[collection_name[:-1] if collection_name.endswith("s") else collection_name] = {
                "id": record[key],
                "name": str(item.get("name") or record[key]),
                "description": compact_metadata(item.get("description") or item.get("continuity_contract") or item.get("inheritance_contract"), max_len=180),
                "forbidden": compact_metadata(item.get("forbidden"), max_len=120),
            }
        record["resolved_contracts"] = resolved
        records.append(record)
    return records


def binding_execution_contracts(
    root: Path,
    panel: dict[str, Any],
    records: list[dict[str, Any]],
    registry: dict[str, Any],
    references: list[dict[str, str]],
    *,
    execution_adapter: dict[str, Any],
    persistent_subject: bool,
) -> list[dict[str, Any]]:
    """Freeze the exact identity/state contract consumed by one paid call.

    The registry-wide SHA remains useful provenance, but it is too coarse for
    explaining *which* DNA/form/outfit/expression/state and exact pixels drove
    one panel.  These per-subject records are canonical-hashed and become part
    of ``execution_input_sha256``.
    """
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    raw_bindings = {
        str(item.get("character_id") or item.get("id") or ""): item
        for item in panel.get("character_bindings") or []
        if isinstance(item, dict)
    }
    adapter_id = str(execution_adapter.get("adapter_id") or "")
    out: list[dict[str, Any]] = []
    for record in records:
        cid = str(record.get("character_id") or "")
        asset = assets.get(cid) if isinstance(assets.get(cid), dict) else {}
        raw_binding = raw_bindings.get(cid) if isinstance(raw_bindings.get(cid), dict) else {}
        locator = {
            key: raw_binding.get(key)
            for key in ("bbox", "mask_path", "occlusion", "visibility", "position", "review_region")
            if raw_binding.get(key) not in (None, "", [], {})
        }
        if locator.get("mask_path"):
            mask_path = Path(str(locator["mask_path"]))
            mask_path = mask_path if mask_path.is_absolute() else root / mask_path
            locator["mask_path"] = path_relative_to_root(root, mask_path)
            locator["mask_sha256"] = reference_planner.file_sha256(mask_path) if mask_path.is_file() else ""
        binding_ref_ids = {
            str(record.get(key) or "")
            for key in ("character_id", "form_id", "outfit_id", "expression_id", "state_id")
            if str(record.get(key) or "")
        }
        exact_refs = [
            {
                "path": str(ref.get("path") or ""),
                "sha256": str(ref.get("sha256") or ""),
                "role": str(ref.get("role") or ref.get("view") or "reference"),
                "contract_id": str(ref.get("contract_id") or ""),
            }
            for ref in references
            if (
                str(ref.get("id") or "") in binding_ref_ids
                or str(ref.get("contract_id") or "").startswith(f"{cid}:")
            )
        ]
        subject_binding: dict[str, Any] = {}
        subject_bindings = asset.get("subject_bindings") if isinstance(asset.get("subject_bindings"), dict) else {}
        candidate = subject_bindings.get(adapter_id) if isinstance(subject_bindings.get(adapter_id), dict) else {}
        if persistent_subject and candidate:
            subject_binding = {
                "adapter_id": adapter_id,
                "subject_id": str(candidate.get("subject_id") or ""),
                "verified_at": str(candidate.get("verified_at") or ""),
                "evidence": str(candidate.get("evidence") or candidate.get("source") or ""),
            }
        contract = {
            "character_id": cid,
            "form_id": str(record.get("form_id") or ""),
            "outfit_id": str(record.get("outfit_id") or ""),
            "expression_id": str(record.get("expression_id") or ""),
            "state_id": str(record.get("state_id") or ""),
            "character_dna": record.get("character_dna") or {},
            "variant_policy": record.get("variant_policy") or {},
            "forbidden_inheritance": record.get("forbidden_inheritance") or [],
            "resolved_contracts": record.get("resolved_contracts") or {},
            "subject_locator": locator,
            "exact_references": exact_refs,
            "subject_binding": subject_binding,
        }
        contract["contract_sha256"] = canonical_sha256(contract)
        out.append(contract)
    return out


def binding_contract_text(records: list[dict[str, Any]], *, include_ids: bool = True) -> str:
    parts: list[str] = []
    for record in records:
        visible: list[str] = []
        for kind, item in (record.get("resolved_contracts") or {}).items():
            if not isinstance(item, dict):
                continue
            chunk = f"{kind}={item.get('name') or item.get('id')}"
            if item.get("description"):
                chunk += f"({item['description']})"
            if item.get("forbidden"):
                chunk += f"；不得:{item['forbidden']}"
            visible.append(chunk)
        label = str(record.get("character_id") if include_ids else record.get("display_name") or "角色")
        parts.append(f"{label}：" + "；".join(visible))
    return " || ".join(parts)


def panel_references(root: Path, panel: dict, registry: dict, caps: Any,
                     memory_pins: dict[str, list[dict[str, str]]] | None = None) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for ref_id in panel_reference_ids(panel):
        resolved = resolve_reference_paths(root, str(ref_id), registry) or [{"id": str(ref_id), "path": ""}]
        grouped[ref_id] = sorted(resolved, key=reference_priority)
        pins = (memory_pins or {}).get(str(ref_id)) or []
        if pins:
            pinned_paths = {ref["path"] for ref in pins}
            grouped[ref_id] = pins + [ref for ref in grouped[ref_id] if ref.get("path") not in pinned_paths]

    outfit_ref_id, outfit_id, outfit_record = panel_outfit(panel, registry)
    if outfit_ref_id and outfit_record:
        outfit_refs = outfit_reference_paths(root, outfit_ref_id, outfit_id, outfit_record)
        if outfit_refs:
            seen_paths = {ref["path"] for ref in outfit_refs}
            grouped[outfit_ref_id] = outfit_refs + [
                ref for ref in grouped.get(outfit_ref_id, []) if ref.get("path") not in seen_paths
            ]

    character_ids = [ref_id for ref_id in grouped if ref_id.startswith("CHAR_")]
    char_limit = (
        _cap_value(caps, "single_character_reference_limit", LEGACY_SINGLE_CHARACTER_REFERENCE_LIMIT)
        if len(character_ids) <= 1
        else _cap_value(caps, "multi_character_reference_limit", LEGACY_MULTI_CHARACTER_REFERENCE_LIMIT)
    )
    non_character_limit = _cap_value(caps, "non_character_reference_limit", 1)
    style_limit = _cap_value(caps, "style_reference_limit", 1)
    max_refs = _cap_value(caps, "reference_image_limit", LEGACY_MAX_REFERENCE_IMAGES_PER_JOB)
    selected: list[dict[str, str]] = []
    deferred_groups: list[list[dict[str, str]]] = []
    for ref_id, refs in grouped.items():
        kind = ref_kind(ref_id)
        if kind == "character":
            limit = char_limit
        elif kind == "style":
            limit = style_limit
        else:
            limit = non_character_limit
        selected.extend(refs[:limit])
        if refs[limit:]:
            deferred_groups.append(list(refs[limit:]))

    while len(selected) < max_refs and any(deferred_groups):
        progressed = False
        for refs in deferred_groups:
            if len(selected) >= max_refs:
                break
            if refs:
                selected.append(refs.pop(0))
                progressed = True
        if not progressed:
            break
    if len(selected) > max_refs:
        non_char = [item for item in selected if ref_kind(str(item.get("id") or "")) != "character"]
        char = [item for item in selected if ref_kind(str(item.get("id") or "")) == "character"]
        selected = (non_char + char)[:max_refs]
    return selected


def panel_rects(layout: dict) -> dict[str, dict]:
    rects = {}
    for segment in layout.get("segments", []):
        for panel in segment.get("panels", []):
            pid = panel.get("panel_id")
            if pid:
                rects[pid] = panel
    return rects


def build_prompt(panel: dict, style: str, registry: dict, panel_script: dict, finish: dict[str, Any], render_stage: str) -> str:
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    ref_ids = panel_reference_ids(panel)
    continuity = panel_continuity_contract(panel, panel_script)
    parts = [
        f"无字漫画分格画面，{style}",
        f"画面事实：{panel.get('description', '')}",
    ]
    style_contract = registry_style_contract(registry)
    if style_contract:
        parts.append("项目风格锚与一致性契约：" + style_contract)
    if panel.get("characters"):
        parts.append("角色：" + "、".join(map(str, panel.get("characters", []))))
    if panel.get("location"):
        parts.append("场景：" + str(panel.get("location")))
    if continuity:
        scene_parts = []
        for key, label in (
            ("scene_anchor_id", "场景锚"),
            ("spatial_layout", "空间布局"),
            ("lighting_anchor", "光位/光色"),
            ("axis_eyeline", "轴线/视线"),
            ("resident_assets", "常驻物件"),
            ("continuity_from", "承接上一格"),
            ("spatial_relationships", "人物站位/前后景"),
        ):
            if continuity.get(key):
                scene_parts.append(f"{label}:{continuity[key]}")
        if scene_parts:
            parts.append("场景一致性契约：" + "；".join(scene_parts))
        if continuity.get("gaze_target") or continuity.get("eyeline_direction") or continuity.get("camera_role"):
            parts.append(
                "视线/眼神契约："
                + "；".join(
                    item
                    for item in (
                        f"目标={continuity.get('gaze_target')}" if continuity.get("gaze_target") else "",
                        f"方向={continuity.get('eyeline_direction')}" if continuity.get("eyeline_direction") else "",
                        f"镜头角色={continuity.get('camera_role')}" if continuity.get("camera_role") else "",
                    )
                    if item
                )
            )
        if continuity.get("character_integrity"):
            parts.append("人物完整性契约：" + continuity["character_integrity"])
    outfit_ref_id, outfit_id, outfit_record = panel_outfit(panel, registry)
    if outfit_id:
        if outfit_record:
            parts.append("服装契约：" + outfit_contract_text(outfit_id, outfit_record))
        else:
            parts.append(f"服装契约：本格声明 outfit_id={outfit_id} 但 registry 未登记该服装，出图前先补 outfits 子注册表")
    if panel.get("art_notes"):
        parts.append("构图与表演：" + str(panel.get("art_notes")))
    finish_parts = []
    for key, label in (
        ("art_stage_sequence", "传统稿层顺序"),
        ("ink_plan", "墨线计划"),
        ("black_fill_plan", "黑场计划"),
        ("tone_plan", "网点/灰阶计划"),
        ("value_plan", "黑白灰可读性"),
        ("effects_plan", "效果线/漫符计划"),
        ("lettering_sfx_plan", "拟声词画法"),
        ("no_bake_text_contract", "无字原图契约"),
    ):
        text = compact_metadata(finish.get(key), max_len=360)
        if text:
            finish_parts.append(f"{label}:{text}")
    if finish_parts:
        parts.append(f"传统漫画原稿收尾契约（目标稿层={render_stage or '完成稿'}）：" + "；".join(finish_parts))
    if ref_ids:
        contracts = []
        for ref_id in ref_ids:
            asset = assets.get(ref_id) if isinstance(assets, dict) else None
            if isinstance(asset, dict):
                contracts.append(asset_contract(ref_id, asset))
            else:
                contracts.append(ref_id)
        parts.append("共享参考ID与不可漂移约束：" + " || ".join(contracts))
    if panel.get("dialogue") or panel.get("narration"):
        parts.append("在不挡脸、不挡手脚、不挡关键道具的位置预留低细节留白区域；不要画对白气泡、旁白框、空白文字框或任何可读文字")
    parts.append("定型参考图是最高优先级；截图里的播放按钮、搜索框、字幕、水印、平台 UI、竖排标题和可读文字都不是设定，必须排除")
    if panel.get("characters") or any(ref_id.startswith(("CHAR_", "MON_", "BEAST_", "ANIMAL_")) for ref_id in ref_ids):
        parts.append("角色必须保持同一张脸、同一眼型/眼距、发际线、发型轮廓、服装主色和标志配饰；头发、脸、手臂、手、腿、脚和关键道具必须完整可读，不能裁掉叙事需要的身体部位")
        parts.append("除非本格明确写 POV/破第四墙，角色不要直视读者镜头；眼神应锁定戏内对象、对手、道具、对白对象或下一动作目标")
    parts.append("线条清晰，主体明确，角色脸部、发型、服装、灵力纹路、标志道具和整体画风稳定，适合后期嵌字")
    return "；".join(part for part in parts if part)


def compile_panel_prompt(
    panel: dict[str, Any],
    *,
    model: str,
    channel: str,
    style: str,
    render_stage: str,
    continuity: dict[str, str],
    finish: dict[str, Any],
    references: list[dict[str, str]],
    size: dict[str, int],
    outfit_contract: str = "",
    binding_contract: str = "",
) -> dict[str, Any]:
    continuity = dict(continuity)
    if continuity.get("continuity_from", "").strip().lower() in {"none", "无", "n/a", "-"}:
        continuity.pop("continuity_from")
    scene = "；".join(
        f"{label}:{continuity[key]}"
        for key, label in (
            ("spatial_layout", "空间布局"),
            ("lighting_anchor", "光位/光色"),
            ("axis_eyeline", "轴线/视线"),
            ("resident_assets", "常驻物件"),
            ("continuity_from", "承接上一格"),
            ("spatial_relationships", "人物站位/前后景"),
            ("gaze_target", "视线目标"),
            ("eyeline_direction", "视线方向"),
            ("camera_role", "镜头角色"),
        )
        if continuity.get(key)
    )
    finishing = "；".join(
        f"{label}:{compact_metadata(finish.get(key), max_len=180)}"
        for key, label in (
            ("ink_plan", "墨线"),
            ("black_fill_plan", "黑场"),
            ("tone_plan", "网点/灰阶"),
            ("value_plan", "黑白灰层级"),
            ("effects_plan", "效果线/漫符"),
        )
        if compact_metadata(finish.get(key), max_len=180)
    )
    has_identity_refs = any(str(ref.get("id") or "").startswith(("CHAR_", "MON_", "BEAST_", "ANIMAL_")) for ref in references)
    identity_hold = (
        "按已附角色/妖物参考保持同一张脸、眼型、发际线、发型轮廓、服装主色、体型和标志物；不同角色不得串脸串衣"
        if has_identity_refs else
        "按已附场景、道具或风格参考保持相同结构、材质与视觉语言"
    )
    if outfit_contract:
        identity_hold += "；" + outfit_contract
    if binding_contract:
        identity_hold += "；逐角色本格状态：" + binding_contract
    has_text = bool(panel.get("dialogue") or panel.get("narration"))
    compiled = compile_prompt({
        "panel_id": panel.get("panel_id"),
        "backend": f"{model} {channel}",
        "visible_facts": panel.get("description"),
        "style": f"{style}；目标稿层={render_stage or '完成稿'}",
        "composition": panel.get("art_notes") or "主体明确、叙事焦点清楚、前中后景关系可读",
        "scene_continuity": scene,
        "identity_hold": identity_hold,
        "finishing": finishing or "线条清晰，黑白灰层级稳定，效果服务叙事焦点",
        "text_strategy": (
            "不生成对白、旁白、可读文字、气泡或文字框；仅在不挡脸、手脚和关键道具处保留低细节后期嵌字区"
            if has_text else
            "不生成可读文字、气泡、文字框、字幕、Logo 或水印"
        ),
        "anatomy": "叙事需要的头发、脸、手臂、手、腿、脚和关键道具完整可读；肢体与道具接触关系自然",
        "negative_elements": [
            "文字、气泡、UI、Logo 或水印",
            "额外或畸形手指、手脚混淆",
            "脸、发际线、眼型、发型或服装漂移",
            "场景布局、光位或常驻道具漂移",
            "角色无故直视读者镜头",
            "内部多面板、截图边或拼贴边框",
            "低清晰度、Q版化或过度血腥特写",
        ],
        "reference_inputs": references,
        "canvas": size,
    })
    if compiled["lint"]["errors"]:
        raise ValueError(f"{panel.get('panel_id')} prompt compiler blocked: {compiled['lint']['errors']}")
    return compiled


def build_jobs(root: Path, chapter: str, reference_plan: dict[str, Any] | None = None) -> dict:
    panel_script_path = root / "脚本" / chapter / "panel_script.json"
    layout_path = root / "排版" / chapter / "layout.json"
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    panel_script = load_json(panel_script_path)
    layout = load_json(layout_path)
    rects = panel_rects(layout)
    model = read_setting(root, "生图模型", "自定义")
    channel = read_setting(root, "生图渠道", "manual")
    planned_caps = resolve_capabilities(model, channel) if resolve_capabilities else None
    repo_root = Path(__file__).resolve().parents[4]
    execution_adapter = (
        resolve_execution_adapter(root, model, channel, repo_root=repo_root)
        if resolve_execution_adapter
        else {"adapter_id": "unavailable", "status": "planning_only", "features": {}}
    )
    caps = (
        intersect_with_execution(planned_caps, execution_adapter)
        if planned_caps is not None and intersect_with_execution
        else planned_caps
    )
    style = read_setting(root, "基础视觉风格", "彩色国漫条漫")
    text_language = read_setting(root, "文字语言", "中文")
    render_stage = read_setting(root, "出图稿层", "完成稿")
    resolution_policy = read_setting(root, "生图分辨率策略", "后端最高可达")
    try:
        key_panel_candidate_count = max(1, int(read_setting(root, "关键格候选数", "2")))
    except ValueError:
        key_panel_candidate_count = 2
    registry = load_reference_registry(root)
    plan = reference_plan_for_build(root, chapter, reference_plan)
    plan_by_panel = {
        str(item.get("panel_id")): item
        for item in plan.get("panel_plans") or []
        if isinstance(item, dict) and item.get("panel_id")
    }
    finishing_plan = load_finishing_plan(root, chapter)
    finishing_map = finishing_by_panel(finishing_plan)
    jobs = []
    for panel in panel_script.get("panels", []):
        pid = panel.get("panel_id")
        panel_plan = plan_by_panel.get(str(pid), {})
        rect = rects.get(pid, {})
        finish = finishing_map.get(str(pid), {})
        size = {"width": int(rect.get("w", 1440)), "height": int(rect.get("h", 900))}
        continuity = panel_continuity_contract(panel, panel_script)
        references = references_from_panel_plan(root, panel_plan) if panel_plan else []
        bindings = binding_records(panel_plan, registry) if panel_plan else []
        identity_contracts = binding_execution_contracts(
            root,
            panel,
            bindings,
            registry,
            references,
            execution_adapter=execution_adapter,
            persistent_subject=bool(caps and caps.persistent_subject),
        )
        identity_contracts_sha = canonical_sha256(identity_contracts)
        binding_full = binding_contract_text(bindings, include_ids=True)
        binding_visible = binding_contract_text(bindings, include_ids=False)
        production_prompt = build_prompt(panel, style, registry, panel_script, finish, render_stage)
        if binding_full:
            production_prompt += "；逐角色结构化状态合同：" + binding_full
        outfit_ref_id, outfit_id, outfit_record = panel_outfit(panel, registry)
        outfit_contract = outfit_contract_text(outfit_id, outfit_record) if outfit_ref_id and outfit_record else ""
        compiled = compile_panel_prompt(
            panel,
            model=model,
            channel=channel,
            style=style,
            render_stage=render_stage,
            continuity=continuity,
            finish=finish,
            references=references,
            size=size,
            outfit_contract=outfit_contract,
            binding_contract=binding_visible,
        )
        submit_prompt = str(compiled["prompt"])
        registry_sha = reference_planner.file_sha256(registry_path) if registry_path.is_file() else ""
        consumed_contracts = {
            "reference_plan": {
                "path": str(Path("生产数据") / f"comic_reference_plan_{chapter}.json"),
                "plan_sha256": str(plan.get("plan_sha256") or ""),
                "inputs_fingerprint": str(plan.get("inputs_fingerprint") or ""),
                "panel_plan_sha256": str(panel_plan.get("panel_plan_sha256") or ""),
            },
            "identity_registry": {
                "path": "出图/共享/identity_registry.json",
                "sha256": registry_sha,
                "schema_version": registry.get("schema_version"),
            },
            "identity_bindings": {
                "sha256": identity_contracts_sha,
                "contracts": [
                    {"character_id": item.get("character_id"), "contract_sha256": item.get("contract_sha256")}
                    for item in identity_contracts
                ],
            },
            "panel_script": {"path": str(panel_script_path.relative_to(root)), "sha256": reference_planner.file_sha256(panel_script_path)},
            "layout": {"path": str(layout_path.relative_to(root)), "sha256": reference_planner.file_sha256(layout_path)},
        }
        execution_input = {
            "submit_prompt_sha256": hashlib.sha256(submit_prompt.encode("utf-8")).hexdigest(),
            "size": size,
            "resolution_policy": resolution_policy,
            "references": [{"id": ref.get("id"), "path": ref.get("path"), "sha256": ref.get("sha256")} for ref in references],
            "character_bindings": [{key: row.get(key) for key in ("character_id", "form_id", "outfit_id", "expression_id", "state_id")} for row in bindings],
            "identity_contracts_sha256": identity_contracts_sha,
            "identity_contracts": identity_contracts,
            "execution_adapter": {
                "adapter_id": execution_adapter.get("adapter_id"),
                "status": execution_adapter.get("status"),
                "features": execution_adapter.get("features") or {},
                "feature_evidence": execution_adapter.get("feature_evidence") or {},
            },
            "panel_plan_sha256": str(panel_plan.get("panel_plan_sha256") or ""),
        }
        execution_input_sha = hashlib.sha256(
            json.dumps(execution_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        story_function = str(panel.get("story_function") or "").lower()
        key_panel = bool(panel.get("key_panel")) or any(
            token in story_function
            for token in ("hook", "cliff", "reveal", "turning_point", "climax", "payoff", "高潮", "揭示", "转折")
        ) or str(finish.get("layout_weight") or "") == "heavy"
        jobs.append(
            {
                "panel_id": pid,
                "status": "planned",
                "size": size,
                "resolution_policy": resolution_policy,
                "production_contract_prompt": production_prompt,
                "production_negative_contract": PRODUCTION_NEGATIVE_CONTRACT,
                "prompt_source_kind": "compiled_submit_prompt",
                "prompt_compiler": {
                    key: compiled[key]
                    for key in ("kind", "version", "profile_version", "profile", "backend", "language")
                },
                "submit_prompt": submit_prompt,
                "prompt": submit_prompt,
                "negative_prompt": compiled["negative_prompt"],
                "source_contract_sha256": compiled["source_contract_sha256"],
                "submit_prompt_sha256": hashlib.sha256(submit_prompt.encode("utf-8")).hexdigest(),
                "submit_prompt_chars": len(submit_prompt),
                "execution_input": execution_input,
                "execution_input_sha256": execution_input_sha,
                "consumed_contracts": consumed_contracts,
                "continuity_contract": continuity,
                "traditional_finish_contract": finish,
                "outfit_binding": (
                    {"ref_id": outfit_ref_id, "outfit_id": outfit_id, "registered": bool(outfit_record)}
                    if outfit_id
                    else {}
                ),
                "character_bindings": bindings,
                "identity_execution_contracts": identity_contracts,
                "identity_execution_contracts_sha256": identity_contracts_sha,
                "execution_adapter": {
                    "adapter_id": execution_adapter.get("adapter_id"),
                    "status": execution_adapter.get("status"),
                    "source": execution_adapter.get("source"),
                    "features": execution_adapter.get("features") or {},
                    "feature_evidence": execution_adapter.get("feature_evidence") or {},
                },
                "candidate_policy": {
                    "enabled": bool(key_panel and key_panel_candidate_count > 1),
                    "target_count": key_panel_candidate_count if key_panel else 1,
                    "generation_order": "sequential_same_stage_budget_envelope",
                    "selection": "fewest_structured_axis_warnings_then_earliest",
                    "each_candidate_requires_b14": True,
                },
                "references": references,
                "reference_budget": caps.to_dict() if caps else {},
                "result_path": "",
                "source": channel,
            }
        )
    return {
        "schema_version": 2,
        "kind": "comic_panel_jobs",
        "chapter": chapter,
        "model": model,
        "channel": channel,
        "backend_capabilities": caps.to_dict() if caps else {},
        "planned_backend_capabilities": planned_caps.to_dict() if planned_caps else {},
        "execution_adapter": {
            "adapter_id": execution_adapter.get("adapter_id"),
            "status": execution_adapter.get("status"),
            "source": execution_adapter.get("source"),
            "features": execution_adapter.get("features") or {},
            "feature_evidence": execution_adapter.get("feature_evidence") or {},
        },
        "text_language": text_language,
        "render_stage": render_stage,
        "resolution_policy": resolution_policy,
        "reference_plan": {
            "path": str(Path("生产数据") / f"comic_reference_plan_{chapter}.json"),
            "plan_sha256": str(plan.get("plan_sha256") or ""),
            "inputs_fingerprint": str(plan.get("inputs_fingerprint") or ""),
        },
        "finishing_plan": str(Path("出图") / chapter / "finishing" / "finishing_plan.json") if finishing_plan else "",
        "jobs": jobs,
    }


def job_is_stale(old: dict, new: dict) -> bool:
    """已生成图对应的提交契约是否已过期。

    只比较真正影响成图内容的部分：submit_prompt 哈希和画布尺寸。
    参考图集合的扩充（补视图）不算过期——参考图内容变化由
    comic-identity report 的 sha 比对负责触发重抽。
    """
    if str(old.get("submit_prompt_sha256") or "") != str(new.get("submit_prompt_sha256") or ""):
        return True
    if str(old.get("execution_input_sha256") or "") != str(new.get("execution_input_sha256") or ""):
        return True
    return (
        (old.get("size") or {}) != (new.get("size") or {})
        or str(old.get("resolution_policy") or "按最终画布")
        != str(new.get("resolution_policy") or "后端最高可达")
    )


def preserve_ready_jobs(root: Path, chapter: str, jobs: dict) -> tuple[int, list[str]]:
    path = root / "出图" / chapter / "prompt" / "panel_jobs.json"
    if not path.is_file():
        return 0, []
    try:
        existing = load_json(path)
    except (OSError, json.JSONDecodeError):
        return 0, []
    old_by_id = {
        str(job.get("panel_id")): job
        for job in existing.get("jobs", [])
        if isinstance(job, dict) and job.get("panel_id")
    }
    preserved = 0
    stale: list[str] = []
    for job in jobs.get("jobs", []):
        if not isinstance(job, dict):
            continue
        old = old_by_id.get(str(job.get("panel_id")))
        if not old or old.get("status") != "ready":
            continue
        result_path = str(old.get("result_path") or "")
        if not result_path:
            continue
        result = Path(result_path)
        if not result.is_absolute():
            result = root / result
        if not result.is_file():
            continue
        acceptance = panel_gate.panel_acceptance_status(root, old)
        if not acceptance.get("accepted"):
            stale.append(str(job.get("panel_id")))
            continue
        if job_is_stale(old, job):
            stale.append(str(job.get("panel_id")))
            continue
        for key in PRESERVE_GENERATION_KEYS:
            if key in old:
                job[key] = old[key]
        preserved += 1
    return preserved, stale


def check_stale_jobs(root: Path, chapter: str, fresh: dict) -> dict:
    """对比当前契约与已落盘 panel_jobs.json，不写任何文件。"""
    path = root / "出图" / chapter / "prompt" / "panel_jobs.json"
    result: dict[str, Any] = {
        "kind": "comic_panel_jobs_check",
        "chapter": chapter,
        "jobs_file": str(Path("出图") / chapter / "prompt" / "panel_jobs.json"),
        "stale_panels": [],
        "missing_panels": [],
        "orphan_panels": [],
        "reference_shifted_panels": [],
        "checked": 0,
    }
    if not path.is_file():
        result["error"] = "panel_jobs_missing"
        return result
    try:
        existing = load_json(path)
    except (OSError, json.JSONDecodeError):
        result["error"] = "panel_jobs_unreadable"
        return result
    old_by_id = {
        str(job.get("panel_id")): job
        for job in existing.get("jobs", [])
        if isinstance(job, dict) and job.get("panel_id")
    }
    fresh_ids: set[str] = set()
    for job in fresh.get("jobs", []):
        if not isinstance(job, dict):
            continue
        pid = str(job.get("panel_id"))
        fresh_ids.add(pid)
        old = old_by_id.get(pid)
        if not old:
            result["missing_panels"].append(pid)
            continue
        result["checked"] += 1
        if job_is_stale(old, job):
            result["stale_panels"].append(pid)
        elif str(old.get("source_contract_sha256") or "") != str(job.get("source_contract_sha256") or ""):
            result["reference_shifted_panels"].append(pid)
    result["orphan_panels"] = sorted(set(old_by_id) - fresh_ids)
    return result


def write_reference_index(root: Path, chapter: str, jobs: dict) -> None:
    refs: dict[str, dict[str, object]] = {}
    for job in jobs.get("jobs", []):
        for ref in job.get("references", []):
            rid = ref.get("id")
            if rid:
                item = refs.setdefault(rid, {"count": 0, "path": ""})
                item["count"] = int(item.get("count") or 0) + 1
                if ref.get("path"):
                    item["path"] = ref.get("path")
    lines = [
        f"# 共享参考任务索引 — {chapter}",
        "",
        "正式逐格出图前，先补齐这些角色、场景、道具或特效参考。",
        "",
        "| ref_id | 出现次数 | 状态 | 建议 |",
        "|---|---:|---|---|",
    ]
    for rid, item in sorted(refs.items()):
        count = int(item.get("count") or 0)
        path = str(item.get("path") or "")
        if path:
            lines.append(f"| {rid} | {count} | ✅ | `{path}` |")
        else:
            lines.append(f"| {rid} | {count} | ⬜ | 生成或放入 `出图/共享/图片/` 后回填 panel_jobs.json |")
    if not refs:
        lines.append("| （无） | 0 | - | 当前脚本未声明 references |")
    path = root / "出图" / "共享" / "prompt" / "00_索引.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成漫画逐格出图任务包")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument(
        "--check",
        action="store_true",
        help="只对比当前契约与已落盘 panel_jobs.json 并输出 JSON 结果，不写任何文件；有陈旧/缺失格时退出码 1",
    )
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    plan = reference_planner.build_plan(root, args.chapter)
    if args.check:
        try:
            jobs = build_jobs(root, args.chapter, plan)
        except Exception as exc:  # noqa: BLE001 - check 模式必须给出结构化结果
            print(json.dumps(
                {"kind": "comic_panel_jobs_check", "chapter": args.chapter, "error": f"rebuild_failed: {exc}"},
                ensure_ascii=False,
            ))
            return 1
        result = check_stale_jobs(root, args.chapter, jobs)
        print(json.dumps(result, ensure_ascii=False))
        dirty = bool(result.get("error") or result["stale_panels"] or result["missing_panels"])
        return 1 if dirty else 0
    plan_dir = root / "生产数据"
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / f"comic_reference_plan_{args.chapter}.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (plan_dir / f"comic_reference_plan_{args.chapter}.md").write_text(
        reference_planner.render_markdown(plan), encoding="utf-8"
    )
    try:
        jobs = build_jobs(root, args.chapter, plan)
    except ReferencePlanBlocked as exc:
        print(f"[block] {exc}; see 生产数据/comic_reference_plan_{args.chapter}.json", file=sys.stderr)
        return 2
    preserved, stale = preserve_ready_jobs(root, args.chapter, jobs)
    out_path = root / "出图" / args.chapter / "prompt" / "panel_jobs.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_reference_index(root, args.chapter, jobs)
    if not args.no_progress:
        update_stage(
            root,
            args.chapter,
            "出图包",
            "✅",
            evidence=str(out_path.relative_to(root)),
            actor="comic-image.build_panel_jobs",
        )
    suffix = f" preserved_ready={preserved}" if preserved else ""
    if stale:
        suffix += f" stale_reset_to_planned={','.join(stale)}"
    print(f"[ok] {out_path}{suffix}")
    if stale:
        print(f"[stale] 这些格的提交契约已变化，旧图不再有效，已回到 planned 待重抽：{','.join(stale)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
