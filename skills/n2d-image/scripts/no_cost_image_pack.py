#!/usr/bin/env python3
"""no_cost_image_pack.py — 不考虑图片成本时的出图生产包。

把已有的 reference_pack / keyshot_candidates / reference_plan 进一步收束成
可执行的生产队列：补参考资产、多候选关键镜、多人同框分区构建、golden calibration、
逐镜 shot package。仍然不直接调用生图后端；它只生成可审、可排队、可复现的侧车。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

KIND = "n2d_no_cost_image_production_pack"
ASSET_PREFIXES = ("LOC_", "PROP_", "WEAPON_", "OUTFIT_", "VFX_")


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    if isinstance(value, dict):
        return " ".join(str(k) + " " + flatten(v) for k, v in value.items())
    return str(value or "")


def recipe_hash(payload: Mapping[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


def ep_label(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = re.search(r"\d+", text)
    return f"第{m.group(0)}集" if m else text


def storyboard(root: Path, ep: str) -> List[dict]:
    data = load_json(root / "脚本" / ep / "storyboard.json")
    clips = data.get("clips") if isinstance(data, dict) else []
    return [c for c in clips or [] if isinstance(c, dict)]


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}")


def entity_base_id(value: Any) -> str:
    """Return the persistent entity ID while preserving form text elsewhere."""
    return re.split(r"[/／]", str(value or "").strip(), maxsplit=1)[0]


def structured_entities(clip: Mapping[str, Any]) -> Tuple[List[str], List[str]]:
    """Read entity IDs from schema fields without extending IDs into prose."""
    chars: List[str] = []
    assets: List[str] = []

    def add(value: Any) -> None:
        text = str(value or "").strip()
        if not text or any(ch.isspace() for ch in text):
            return
        target = chars if text.startswith(("CHAR_", "BEAST_")) else assets if text.startswith(ASSET_PREFIXES) else None
        if target is chars:
            # entity_schedule commonly carries `CHAR_01/form` while
            # required_presence carries `CHAR_01`. They are one subject, not
            # two regional-composite slots. Keep the first (usually the
            # form-specific value) and deduplicate on the persistent base ID.
            base = entity_base_id(text)
            if base and all(entity_base_id(existing) != base for existing in chars):
                chars.append(text)
        elif target is assets and text not in assets:
            assets.append(text)

    schedule = clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else {}
    offscreen = {str(value).strip() for value in (schedule.get("offscreen_presence") or []) if str(value).strip()}
    forbidden = {str(value).strip() for value in (schedule.get("forbidden_presence") or []) if str(value).strip()}
    nonvisible = offscreen | forbidden
    nonvisible_character_bases = {
        entity_base_id(value)
        for value in nonvisible
        if str(value).startswith(("CHAR_", "BEAST_"))
    }

    def visible(value: Any) -> bool:
        text = str(value).strip()
        if text in nonvisible:
            return False
        if text.startswith(("CHAR_", "BEAST_")) and entity_base_id(text) in nonvisible_character_bases:
            return False
        return True

    char_values = schedule.get("characters") if isinstance(schedule.get("characters"), list) else clip.get("character_ids") or []
    object_values = schedule.get("objects") if isinstance(schedule.get("objects"), list) else clip.get("object_ids") or []
    location_values = schedule.get("locations") if isinstance(schedule.get("locations"), list) else [clip.get("location_id")]
    for value in char_values:
        if visible(value):
            add(value)
    for value in object_values:
        if visible(value):
            add(value)
    for value in location_values:
        if visible(value):
            add(value)
    for key in ("characters", "objects", "locations", "required_presence", "offscreen_presence", "forbidden_presence"):
        if key in {"required_presence"}:
            for value in schedule.get(key) or []:
                if visible(value):
                    add(value)
    return chars, assets


def load_pack(root: Path, ep: str) -> Dict[str, Any]:
    data = load_json(root / "生产数据" / f"no_cost_reference_pack_{ep}.json")
    return data if isinstance(data, dict) else {"targets": [], "summary": {}}


def load_keyshots(root: Path, ep: str) -> Dict[str, Any]:
    data = load_json(root / "生产数据" / f"keyshot_candidate_plan_{ep}.json")
    return data if isinstance(data, dict) else {"keyshots": [], "summary": {}}


def load_reference_plan(root: Path, ep: str) -> Dict[str, Any]:
    data = load_json(root / "生产数据" / f"reference_plan_{ep}.json")
    return data if isinstance(data, dict) else {"clips": [], "summary": {}}


def priority_for_target(target: Mapping[str, Any]) -> str:
    scope = str(target.get("scope") or "")
    slot = str(target.get("slot") or "")
    reason = str(target.get("reason") or "")
    if scope == "multi_subject" or slot in {"regional_construct_plate", "region_masks"}:
        return "P0"
    if slot in {"turnaround", "face_anchor_refs", "expression_bank", "performance_signature", "action_pose_pack"}:
        return "P0"
    if "核心" in reason or "必用" in reason:
        return "P0"
    if scope == "asset":
        return "P1"
    return "P2"


def reference_generation_queue(root: Path, ep: str, pack: Mapping[str, Any]) -> List[Dict[str, Any]]:
    tasks: List[Dict[str, Any]] = []
    by_output_path: Dict[str, Dict[str, Any]] = {}
    for idx, target in enumerate(pack.get("targets") or [], 1):
        if not isinstance(target, Mapping) or target.get("status") == "ready":
            continue
        output_path = str(target.get("path") or "").strip()
        requirement = {
            "scope": target.get("scope"),
            "owner": target.get("owner"),
            "slot": target.get("slot"),
            "reason": target.get("reason"),
        }
        if output_path and output_path in by_output_path:
            task = by_output_path[output_path]
            if requirement not in task["satisfies"]:
                task["satisfies"].append(requirement)
            if priority_for_target(target) < str(task.get("priority") or "P9"):
                task["priority"] = priority_for_target(target)
            task["prompt_recipe"]["satisfies"] = task["satisfies"]
            task["recipe_hash"] = recipe_hash(task["prompt_recipe"])
            continue
        prompt = {
            "owner": target.get("owner"),
            "slot": target.get("slot"),
            "reason": target.get("reason"),
            "style": "继承本剧 style_contract / identity_registry / asset_registry；无文字无水印。",
            "satisfies": [requirement],
        }
        task = {
            "task_id": f"REF_{idx:03d}",
            "priority": priority_for_target(target),
            "scope": target.get("scope"),
            "owner": target.get("owner"),
            "slot": target.get("slot"),
            "output_path": output_path,
            "prompt_recipe": prompt,
            "recipe_hash": recipe_hash(prompt),
            "qc_required": ["reference_ready", "no_logo_text", "identity_or_asset_match"],
            "satisfies": [requirement],
        }
        tasks.append(task)
        if output_path:
            by_output_path[output_path] = task
    return sorted(tasks, key=lambda t: (t["priority"], str(t["task_id"])))


def keyshot_candidate_queue(root: Path, ep: str, plan: Mapping[str, Any]) -> List[Dict[str, Any]]:
    tasks: List[Dict[str, Any]] = []
    for row in plan.get("keyshots") or []:
        if not isinstance(row, Mapping):
            continue
        existing = row.get("existing_scores") or []
        best = existing[0] if existing else {}
        recipe = {
            "clip": row.get("clip"),
            "tags": row.get("tags") or [],
            "criteria": row.get("selection_criteria") or [],
            "candidate_count": row.get("candidate_count"),
        }
        tasks.append({
            "clip": row.get("clip"),
            "tags": row.get("tags") or [],
            "candidate_count": row.get("candidate_count"),
            "candidate_dir": row.get("candidate_dir"),
            "expected_candidates": row.get("expected_candidates") or [],
            "selection_manifest": row.get("selection_manifest"),
            "selection_status": "selected" if best else "needs_generation",
            "current_best": best or None,
            "recipe_hash": recipe_hash(recipe),
        })
    return tasks


def _strategy_by_clip(reference_plan: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    out: Dict[str, Mapping[str, Any]] = {}
    for clip in reference_plan.get("clips") or []:
        if not isinstance(clip, Mapping):
            continue
        strategy = clip.get("multi_subject_strategy")
        if isinstance(strategy, Mapping):
            out[str(clip.get("clip_id") or "")] = strategy
    return out


def regional_construct_manifests(root: Path, ep: str, clips: Sequence[Mapping[str, Any]],
                                 reference_plan: Mapping[str, Any]) -> List[Dict[str, Any]]:
    strategies = _strategy_by_clip(reference_plan)
    manifests: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip, idx)
        cids, _ = structured_entities(clip)
        if len(cids) < 2 and cid not in strategies:
            continue
        strategy = strategies.get(cid, {})
        slots = strategy.get("slots") if isinstance(strategy, Mapping) else []
        if not slots:
            slots = [{"slot": f"SLOT_{i + 1}", "char_id": char_id, "form": "常态"} for i, char_id in enumerate(cids)]
        base = f"出图/{ep}/区域构建/{cid}"
        recipe = {
            "clip": cid,
            "mode": (strategy or {}).get("mode") or "regional_construct_required",
            "slots": slots,
            "empty_plate": f"{base}/empty_plate.png",
            "masks": f"{base}/masks.json",
        }
        manifests.append({
            "clip": cid,
            "mode": recipe["mode"],
            "manifest_path": f"{base}/regional_construct_manifest.json",
            "empty_plate": recipe["empty_plate"],
            "region_masks": recipe["masks"],
            "slots": slots,
            "steps": [
                "generate_empty_plate_without_characters",
                "create_region_masks_per_slot",
                "inpaint_each_slot_with_own_reference_group",
                "relighting_color_match",
                "final_qc_identity_slots",
            ],
            "recipe_hash": recipe_hash(recipe),
        })
    return manifests


def golden_calibration_plan(ep: str, keyshots: Sequence[Mapping[str, Any]],
                            reference_tasks: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    golden_candidates = []
    for row in keyshots:
        if row.get("selection_status") == "selected" and row.get("current_best"):
            golden_candidates.append({"kind": "selected_keyshot", "clip": row.get("clip"), "candidate": row.get("current_best")})
        elif row.get("tags") and any(t in row.get("tags") for t in ("opening", "cover", "multi_subject", "action")):
            golden_candidates.append({"kind": "planned_keyshot", "clip": row.get("clip"), "expected": (row.get("expected_candidates") or [])[:2]})
    for task in reference_tasks[:8]:
        if task.get("priority") == "P0":
            golden_candidates.append({"kind": "reference_anchor", "owner": task.get("owner"), "slot": task.get("slot"), "path": task.get("output_path")})
    return {
        "kind": "n2d_golden_calibration_plan",
        "episode": ep,
        "target_path": f"生产数据/golden_calibration_{ep}.json",
        "candidates": golden_candidates,
        "calibrate_dimensions": [
            "face_identity", "hair_outfit", "style_attribution", "scene_light", "multi_subject_slots", "keyshot_hook_strength",
        ],
        "policy": "先用本集 P0 关键镜/参考锚做人审 golden，再把阈值和选优偏好回写到后续集。",
    }


def shot_packages(root: Path, ep: str, clips: Sequence[Mapping[str, Any]],
                  reference_tasks: Sequence[Mapping[str, Any]],
                  keyshots: Sequence[Mapping[str, Any]],
                  regional: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    ref_by_owner: Dict[str, List[Mapping[str, Any]]] = {}
    for task in reference_tasks:
        owners = {str(task.get("owner") or "")}
        for requirement in task.get("satisfies") or []:
            if isinstance(requirement, Mapping):
                owners.add(str(requirement.get("owner") or ""))
        for owner in owners:
            if owner:
                ref_by_owner.setdefault(owner, []).append(task)
    key_by_clip = {str(k.get("clip")): k for k in keyshots}
    reg_by_clip = {str(r.get("clip")): r for r in regional}
    packages: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip, idx)
        chars, assets = structured_entities(clip)
        related_refs = []
        for owner, tasks in ref_by_owner.items():
            if any(char in owner for char in chars) or any(asset in owner for asset in assets):
                related_refs.extend(tasks[:3])
        recipe = {"clip": cid, "chars": chars, "assets": assets, "keyshot": bool(key_by_clip.get(cid)), "regional": bool(reg_by_clip.get(cid))}
        packages.append({
            "clip": cid,
            "characters": chars,
            "assets": assets,
            "intent": str(clip.get("description") or clip.get("summary") or clip.get("label") or "")[:180],
            "reference_tasks": related_refs,
            "keyshot_candidate_task": key_by_clip.get(cid),
            "regional_construct": reg_by_clip.get(cid),
            "required_sidecars": [
                f"生产数据/reference_plan_{ep}.json",
                f"生产数据/no_cost_reference_pack_{ep}.json",
                f"生产数据/keyshot_candidate_plan_{ep}.json",
            ],
            "recipe_hash": recipe_hash(recipe),
        })
    return packages


def build_pack(root: Path, ep: str) -> Dict[str, Any]:
    ep = ep_label(ep)
    clips = storyboard(root, ep)
    ref_pack = load_pack(root, ep)
    keyshot_plan = load_keyshots(root, ep)
    reference_plan = load_reference_plan(root, ep)
    reference_tasks = reference_generation_queue(root, ep, ref_pack)
    keyshot_tasks = keyshot_candidate_queue(root, ep, keyshot_plan)
    regional = regional_construct_manifests(root, ep, clips, reference_plan)
    golden = golden_calibration_plan(ep, keyshot_tasks, reference_tasks)
    packages = shot_packages(root, ep, clips, reference_tasks, keyshot_tasks, regional)
    return {
        "kind": KIND,
        "version": 1,
        "episode": ep,
        "summary": {
            "clips": len(clips),
            "reference_generation_tasks": len(reference_tasks),
            "keyshot_candidate_tasks": len(keyshot_tasks),
            "regional_construct_manifests": len(regional),
            "shot_packages": len(packages),
        },
        "reference_generation_queue": reference_tasks,
        "keyshot_candidate_queue": keyshot_tasks,
        "regional_construct_manifests": regional,
        "golden_calibration": golden,
        "shot_packages": packages,
        "notes": ["不直接生图；这是无成本图片增强档的排队/选优/回写真值源。"],
    }


def render_md(pack: Mapping[str, Any]) -> str:
    s = pack.get("summary") or {}
    lines = [
        "# 无成本图片生产包",
        "",
        f"- episode: {pack.get('episode')}",
        f"- reference_generation_tasks: {s.get('reference_generation_tasks')}",
        f"- keyshot_candidate_tasks: {s.get('keyshot_candidate_tasks')}",
        f"- regional_construct_manifests: {s.get('regional_construct_manifests')}",
        f"- shot_packages: {s.get('shot_packages')}",
        "",
        "## P0 参考资产补图",
        "",
        "| Task | Priority | Owner | Slot | Output |",
        "|---|---|---|---|---|",
    ]
    for task in pack.get("reference_generation_queue") or []:
        lines.append(f"| {task.get('task_id')} | {task.get('priority')} | {task.get('owner')} | {task.get('slot')} | {task.get('output_path')} |")
    lines += ["", "## 关键镜候选", "", "| Clip | Tags | N | Status | Best |", "|---|---|---:|---|---|"]
    for task in pack.get("keyshot_candidate_queue") or []:
        best = task.get("current_best") or {}
        lines.append(f"| {task.get('clip')} | {'、'.join(task.get('tags') or [])} | {task.get('candidate_count')} | {task.get('selection_status')} | {best.get('candidate') or '-'} |")
    lines += ["", "## 多人同框分区构建", "", "| Clip | Mode | Manifest | Steps |", "|---|---|---|---|"]
    for item in pack.get("regional_construct_manifests") or []:
        lines.append(f"| {item.get('clip')} | {item.get('mode')} | {item.get('manifest_path')} | {' → '.join(item.get('steps') or [])} |")
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, ep: str, pack: Mapping[str, Any]) -> Tuple[Path, Path]:
    out = root / "生产数据"
    jp = out / f"no_cost_image_production_pack_{ep}.json"
    mp = out / f"no_cost_image_production_pack_{ep}.md"
    write_atomic(jp, json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_atomic(mp, render_md(pack))
    return jp, mp


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 无成本图片生产包")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    ep = ep_label(ns.episode)
    pack = build_pack(root, ep)
    if ns.write:
        jp, mp = write_outputs(root, ep, pack)
        pack["outputs"] = {"json": str(jp), "md": str(mp)}
    if ns.json:
        print(json.dumps(pack, ensure_ascii=False, indent=2))
    else:
        print(render_md(pack))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
