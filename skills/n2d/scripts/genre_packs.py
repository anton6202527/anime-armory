#!/usr/bin/env python3
"""Validate and inspect n2d genre packs."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from n2d_const import GENRE_PACK_CONTEXT_KIND, GENRE_PACK_KIND  # noqa: E402


PACK_DIR = Path(__file__).resolve().parents[1] / "references" / "genre_packs"
CONTEXT_KIND = GENRE_PACK_CONTEXT_KIND
REQUIRED_TOP = ("kind", "version", "genre_key", "label", "scene_archetypes", "motion_contract_fields", "qc_focus")
REQUIRED_SCENE = ("id", "label", "production_risks", "required_contract_fields", "style_binding")


def pack_paths() -> List[Path]:
    return sorted(path for path in PACK_DIR.glob("*.json") if path.is_file())


def load_pack(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a JSON object")
    return data


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def context_path(root: Path, episode: str, stage_key: str) -> Path:
    slug = "".join(ch if (ch.isalnum() or ch in "-_.") else "_" for ch in str(stage_key or "stage"))
    return production_dir(root) / f"genre_pack_context_{episode}_{slug}.json"


def context_md_path(root: Path, episode: str, stage_key: str) -> Path:
    return production_dir(root) / "views" / "genre_packs" / context_path(root, episode, stage_key).with_suffix(".md").name


def pack_index() -> Dict[str, Dict[str, Any]]:
    packs = [load_pack(path) for path in pack_paths()]
    index: Dict[str, Dict[str, Any]] = {}
    for pack in packs:
        key = str(pack.get("genre_key") or "").strip().lower()
        if key:
            index.setdefault(key, pack)
        aliases = [pack.get("label"), *(pack.get("aliases") or [])]
        for alias in aliases:
            text = str(alias or "").strip().lower()
            if text:
                # Keep the first sorted pack so legacy callers remain
                # deterministic even if local extensions reuse an alias.
                index.setdefault(text, pack)
    return index


def _unique_strings(values: Iterable[Any]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _pack_match_terms(pack: Dict[str, Any]) -> List[str]:
    return _unique_strings([
        pack.get("genre_key"),
        pack.get("label"),
        *(pack.get("aliases") or []),
    ])


def _term_start(text: str, term: str) -> int:
    """Return the first explicit term match; never infer a nearby genre."""
    term = str(term or "").strip().lower()
    if not term:
        return -1
    if re.fullmatch(r"[a-z0-9_./-]+", term):
        match = re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text)
        return match.start() if match else -1
    return text.find(term)


def match_genre_packs(value: str) -> List[Dict[str, Any]]:
    """Match every explicitly named pack in deterministic user-declared order.

    Compatibility: the first row is the same primary genre exposed by the old
    single-pack API.  Composite values add rows ordered by first textual
    occurrence, then the longest matching term, then sorted pack path/key.
    Only keys, labels and declared aliases match; no semantic nearest-neighbour
    mapping is attempted (for example, ``志怪`` alone remains unmatched).
    """
    text = str(value or "").strip().lower()
    if not text:
        return []
    matches: List[Dict[str, Any]] = []
    for pack_order, path in enumerate(pack_paths()):
        pack = load_pack(path)
        candidates: List[tuple[int, int, int, str]] = []
        for term_order, term in enumerate(_pack_match_terms(pack)):
            normalized = term.strip().lower()
            start = _term_start(text, normalized)
            if start >= 0:
                candidates.append((start, -len(normalized), term_order, term))
        if not candidates:
            continue
        start, negative_length, term_order, matched_term = min(candidates)
        matches.append({
            "genre_key": str(pack.get("genre_key") or "").strip().lower(),
            "label": str(pack.get("label") or "").strip(),
            "matched_term": matched_term,
            "match_start": start,
            "match_length": -negative_length,
            "pack_order": pack_order,
            "term_order": term_order,
            "path": str(path),
            "pack": pack,
        })
    matches.sort(key=lambda row: (
        int(row["match_start"]),
        -int(row["match_length"]),
        int(row["pack_order"]),
        str(row["genre_key"]),
    ))
    return matches


def normalize_genre_key(value: str) -> str:
    """Return the primary key for legacy single-genre callers."""
    matches = match_genre_packs(value)
    return str(matches[0].get("genre_key") or "") if matches else ""


def load_pack_by_key(value: str) -> Optional[Dict[str, Any]]:
    """Load the primary pack (legacy API); use load_packs_by_value for composites."""
    key = normalize_genre_key(value)
    if not key:
        return None
    path = PACK_DIR / f"{key}.json"
    return load_pack(path) if path.is_file() else None


def load_packs_by_value(value: str) -> List[Dict[str, Any]]:
    return [row["pack"] for row in match_genre_packs(value)]


def project_genre_text(root: Path) -> str:
    try:
        if str(LIB) not in sys.path:
            sys.path.insert(0, str(LIB))
        from settings import get_setting  # type: ignore

        return get_setting(str(root), "题材", "") or ""
    except Exception:
        path = root / "_设置.md"
        if not path.is_file():
            return ""
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip().lstrip("-").strip()
            if line.startswith("题材") and ":" in line:
                return line.split(":", 1)[1].strip()
        return ""


def load_storyboard(root: Path, episode: str) -> Dict[str, Any]:
    path = root / "脚本" / episode / "storyboard.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def storyboard_probe(root: Path, episode: str) -> Dict[str, Any]:
    path = root / "脚本" / episode / "storyboard.json"
    if not path.is_file():
        return {"state": "missing", "path": str(path), "data": {}, "clips": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"state": "invalid", "path": str(path), "data": {}, "clips": [], "error": str(exc)}
    if not isinstance(data, dict):
        return {"state": "invalid", "path": str(path), "data": {}, "clips": [], "error": "root is not an object"}
    raw_clips = data.get("clips")
    if raw_clips is not None and not isinstance(raw_clips, list):
        return {"state": "invalid", "path": str(path), "data": data, "clips": [], "error": "clips is not an array"}
    clips = [item for item in (raw_clips or []) if isinstance(item, dict)]
    return {
        "state": "ready" if clips else "empty",
        "path": str(path),
        "data": data,
        "clips": clips,
    }


def clip_text(clip: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in ("id", "clip_id", "title", "shot_type", "template", "description", "visual", "action", "dialogue", "notes"):
        value = clip.get(key)
        if isinstance(value, (str, int, float)):
            parts.append(str(value))
    for key in ("continuity", "motion_contract", "action_contract", "visual_contract"):
        value = clip.get(key)
        if isinstance(value, dict):
            parts.append(json.dumps(value, ensure_ascii=False))
    return " ".join(parts).lower()


def scene_tokens(scene: Dict[str, Any]) -> List[str]:
    tokens = [str(scene.get("id") or ""), str(scene.get("label") or "")]
    tokens.extend(str(item or "") for item in scene.get("production_risks") or [])
    expanded: List[str] = []
    for token in tokens:
        expanded.append(token)
        expanded.extend(part for part in re.split(r"[/／、_\-\s]+", token) if part)
    return [item.strip().lower() for item in expanded if item and len(item.strip()) >= 2]


def token_matches_text(token: str, text: str) -> bool:
    token = str(token or "").strip().lower()
    if not token:
        return False
    if re.fullmatch(r"[a-z0-9_./-]+", token):
        pattern = rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])"
        return re.search(pattern, text) is not None
    return token in text


def scene_matches_clip(scene: Dict[str, Any], clip: Dict[str, Any]) -> bool:
    text = clip_text(clip)
    return any(token_matches_text(token, text) for token in scene_tokens(scene))


def clip_contract_fields(clip: Dict[str, Any]) -> Dict[str, Any]:
    fields: Dict[str, Any] = {}
    for key in ("motion_contract", "action_contract", "video_contract", "template_contract", "continuity"):
        value = clip.get(key)
        if isinstance(value, dict):
            fields.update(value)
    if fields.get("screen_direction") in (None, "", [], {}):
        for key in ("blocking", "camera_rule", "spatial_path", "entry_exit", "eyeline"):
            if fields.get(key) not in (None, "", [], {}):
                fields["screen_direction"] = fields[key]
                break
    if fields.get("degrade_plan") in (None, "", [], {}):
        for key in ("fallback", "implementation_decomposition", "degrade"):
            if fields.get(key) not in (None, "", [], {}):
                fields["degrade_plan"] = fields[key]
                break
    if fields.get("degrade_plan") in (None, "", [], {}) and _is_system_panel_overlay_contract(clip, fields):
        fields["degrade_plan"] = "system panel text is compose_overlay_only; keep clean negative space and split to character reaction + panel insert if the model bakes text or UI drifts."
    return fields


def _is_system_panel_overlay_contract(clip: Dict[str, Any], fields: Dict[str, Any]) -> bool:
    template = str(clip.get("template") or fields.get("template_id") or "").lower()
    blob = json.dumps({"clip": clip, "fields": fields}, ensure_ascii=False).lower()
    if "system_panel" not in template and "系统面板" not in blob and "百妖谱" not in blob:
        return False
    overlay_locked = "compose_overlay_only" in blob or "后期叠加" in blob or "文字全部由 compose overlay" in blob
    text_guard = any(token in blob for token in ("不要烤字", "不要随机生成乱码", "no_baked", "video_model_must_not_render_text"))
    return overlay_locked and text_guard


def context_status(stage_key: str, issues: Sequence[Dict[str, Any]]) -> str:
    if not issues:
        return "pass"
    hard_stages = {"video_prompt", "video", "compose", "review"}
    has_block = any(item.get("severity") == "block" for item in issues)
    if has_block or stage_key in hard_stages:
        return "fail"
    return "warn"


def _public_matches(matches: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{
        "priority": idx + 1,
        "genre_key": row.get("genre_key"),
        "label": row.get("label"),
        "matched_term": row.get("matched_term"),
        "match_start": row.get("match_start"),
    } for idx, row in enumerate(matches)]


def compose_pack(matches: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge selected packs in priority order without duplicate list values."""
    keys = _unique_strings(row.get("genre_key") for row in matches)
    labels = _unique_strings(row.get("label") for row in matches)
    fields = _unique_strings(
        item
        for row in matches
        for item in (row.get("pack") or {}).get("motion_contract_fields") or []
    )
    qc_focus = _unique_strings(
        item
        for row in matches
        for item in (row.get("pack") or {}).get("qc_focus") or []
    )
    degrade_plans = _unique_strings(
        item
        for row in matches
        for item in (row.get("pack") or {}).get("degrade_plans") or []
    )
    policy_rows: List[Dict[str, Any]] = []
    policy_notes: List[str] = []
    bind_to_visual_style = False
    for row in matches:
        policy = (row.get("pack") or {}).get("style_binding_policy")
        if not isinstance(policy, dict):
            continue
        bind_to_visual_style = bind_to_visual_style or bool(policy.get("bind_to_visual_style"))
        if policy.get("notes"):
            policy_notes.append(str(policy["notes"]))
        policy_rows.append({"genre_key": row.get("genre_key"), **policy})
    style_policy: Dict[str, Any] = {}
    if policy_rows:
        # Keep legacy top-level keys while exposing every contributing policy.
        style_policy = dict(policy_rows[0])
        style_policy.pop("genre_key", None)
        style_policy["bind_to_visual_style"] = bind_to_visual_style
        style_policy["notes"] = " | ".join(_unique_strings(policy_notes))
        style_policy["by_genre"] = policy_rows
    return {
        "genre_keys": keys,
        "labels": labels,
        "matched_packs": _public_matches(matches),
        "motion_contract_fields": fields,
        "qc_focus": qc_focus,
        "degrade_plans": degrade_plans,
        "style_binding_policy": style_policy,
    }


def compose_scene_archetypes(matches: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge duplicate scene ids while retaining pack provenance."""
    rows: Dict[str, Dict[str, Any]] = {}
    for match in matches:
        genre_key = str(match.get("genre_key") or "")
        for scene in (match.get("pack") or {}).get("scene_archetypes") or []:
            if not isinstance(scene, dict):
                continue
            scene_id = str(scene.get("id") or "").strip()
            dedupe_key = scene_id.lower() or f"label:{str(scene.get('label') or '').strip().lower()}"
            if dedupe_key not in rows:
                rows[dedupe_key] = {
                    "id": scene_id,
                    "label": scene.get("label"),
                    "labels": [],
                    "genre_keys": [],
                    "production_risks": [],
                    "required_contract_fields": [],
                    "style_binding": scene.get("style_binding"),
                    "style_bindings": [],
                    # 非人物特写覆盖期望（首个声明该 scene 的 pack 胜出，advisory 元数据）。
                    "insert_coverage": scene.get("insert_coverage"),
                }
            row = rows[dedupe_key]
            if row.get("insert_coverage") is None and scene.get("insert_coverage") is not None:
                row["insert_coverage"] = scene.get("insert_coverage")
            row["labels"] = _unique_strings([*row["labels"], scene.get("label")])
            row["genre_keys"] = _unique_strings([*row["genre_keys"], genre_key])
            row["production_risks"] = _unique_strings([
                *row["production_risks"],
                *(scene.get("production_risks") or []),
            ])
            row["required_contract_fields"] = _unique_strings([
                *row["required_contract_fields"],
                *(scene.get("required_contract_fields") or []),
            ])
            row["style_bindings"] = _unique_strings([
                *row["style_bindings"],
                scene.get("style_binding"),
            ])
    return list(rows.values())


def activation_contract(
    genre_text: str,
    matches: Sequence[Dict[str, Any]],
    storyboard: Dict[str, Any],
    active: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    board_state = str(storyboard.get("state") or "missing")
    if not str(genre_text or "").strip():
        state = "genre_unset"
        reason = "项目未设置题材；没有题材包可触发。"
    elif not matches:
        state = "genre_unmatched"
        reason = "题材未显式命中任何 genre key、label 或 alias；未做近义词猜测。"
    elif board_state == "missing":
        state = "storyboard_missing"
        reason = "题材包已匹配；storyboard 尚不存在，因此场景规则尚未触发。"
    elif board_state == "invalid":
        state = "storyboard_invalid"
        reason = "题材包已匹配；storyboard 不可解析，因此场景规则尚未触发。"
    elif board_state == "empty":
        state = "storyboard_empty"
        reason = "题材包已匹配；storyboard 还没有结构化 clips，因此场景规则尚未触发。"
    elif active:
        state = "scene_archetypes_triggered"
        reason = "storyboard 中已有镜头命中题材高风险场景。"
    else:
        state = "no_scene_archetype_triggered"
        reason = "题材包已匹配且 storyboard 可读，但当前 clips 未命中题材高风险场景。"
    return {
        "state": state,
        "triggered": bool(active),
        "reason": reason,
        "storyboard_state": board_state,
        "storyboard_path": storyboard.get("path"),
        "storyboard_clip_count": len(storyboard.get("clips") or []),
    }


def build_context(root: Path, episode: str, stage_key: str) -> Dict[str, Any]:
    root = root.resolve()
    genre_text = project_genre_text(root)
    matches = match_genre_packs(genre_text)
    pack = compose_pack(matches)
    storyboard = storyboard_probe(root, episode)
    clips = storyboard.get("clips") or []
    active: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []
    if matches:
        for scene in compose_scene_archetypes(matches):
            matched = [clip for clip in clips if scene_matches_clip(scene, clip)]
            if not matched:
                continue
            missing_by_clip: List[Dict[str, Any]] = []
            for clip in matched:
                fields = clip_contract_fields(clip)
                missing = [field for field in scene.get("required_contract_fields") or [] if fields.get(field) in (None, "", [], {})]
                if missing:
                    missing_by_clip.append({"clip": clip.get("id") or clip.get("clip_id") or "", "missing": missing})
            row = {
                "scene_id": scene.get("id"),
                "label": scene.get("label"),
                "genre_keys": scene.get("genre_keys") or [],
                "matched_clips": _unique_strings(clip.get("id") or clip.get("clip_id") or "" for clip in matched),
                "required_contract_fields": scene.get("required_contract_fields") or [],
                "insert_coverage": scene.get("insert_coverage"),
                "missing_by_clip": missing_by_clip,
                "style_binding": scene.get("style_binding"),
                "style_bindings": scene.get("style_bindings") or [],
                "production_risks": scene.get("production_risks") or [],
            }
            active.append(row)
            for missing in missing_by_clip:
                issues.append({
                    "severity": "block" if stage_key in {"video_prompt", "video", "compose", "review"} else "warn",
                    "scene_id": scene.get("id"),
                    "genre_keys": scene.get("genre_keys") or [],
                    "clip": missing.get("clip"),
                    "message": "missing genre motion contract fields: " + ", ".join(missing.get("missing") or []),
                    "missing_fields": missing.get("missing") or [],
                })
    activation = activation_contract(genre_text, matches, storyboard, active)
    primary = matches[0] if matches else {}
    payload = {
        "kind": CONTEXT_KIND,
        "version": 1,
        "root": str(root),
        "episode": episode,
        "stage_key": stage_key,
        "generated_at": now_iso(),
        "genre": {
            "raw": genre_text,
            # Singular fields stay for old consumers and point to priority #1.
            "genre_key": primary.get("genre_key") or "",
            "label": primary.get("label") or "",
            "matched": bool(matches),
            "matched_genre_keys": pack.get("genre_keys") or [],
            "matched_labels": pack.get("labels") or [],
            "matches": _public_matches(matches),
        },
        "pack": pack,
        "activation": activation,
        "active_scene_archetypes": active,
        "issues": issues,
        "summary": {
            "active_scenes": len(active),
            "issues": len(issues),
            "matched_clips": len({clip for row in active for clip in row.get("matched_clips", []) if clip}),
            "matched_packs": len(matches),
            "matched_genre_keys": pack.get("genre_keys") or [],
            "activation_state": activation.get("state"),
            "storyboard_state": activation.get("storyboard_state"),
            "storyboard_clip_count": activation.get("storyboard_clip_count"),
        },
        "status": context_status(stage_key, issues),
    }
    return payload


def render_context_markdown(payload: Dict[str, Any]) -> str:
    genre = payload.get("genre") if isinstance(payload.get("genre"), dict) else {}
    pack = payload.get("pack") if isinstance(payload.get("pack"), dict) else {}
    activation = payload.get("activation") if isinstance(payload.get("activation"), dict) else {}
    genre_keys = genre.get("matched_genre_keys") or ([genre.get("genre_key")] if genre.get("genre_key") else [])
    lines = [
        "# n2d Genre Pack Context",
        "",
        f"- 集：{payload.get('episode')}",
        f"- 阶段：{payload.get('stage_key')}",
        f"- 题材原值：{genre.get('raw') or '未设置'}",
        f"- 命中 pack：{', '.join(genre_keys) or '未命中'}",
        f"- 场景触发：{activation.get('state') or 'unknown'} — {activation.get('reason') or '无说明'}",
        f"- 状态：{payload.get('status')}",
        "",
        "## QC Focus",
        "",
    ]
    lines.extend([f"- {item}" for item in pack.get("qc_focus") or []] or ["- 无"])
    lines.extend(["", "## Active Scenes", "", "| packs | scene | clips | missing |", "|---|---|---|---|"])
    active = payload.get("active_scene_archetypes") or []
    for row in active:
        missing = "; ".join(
            f"{item.get('clip')}:{','.join(item.get('missing') or [])}"
            for item in row.get("missing_by_clip") or []
        ) or "-"
        lines.append(
            f"| {','.join(row.get('genre_keys') or []) or '-'} | {row.get('label')} | "
            f"{','.join(row.get('matched_clips') or []) or '-'} | {missing} |"
        )
    if not active:
        lines.append(f"| - | 未触发（{activation.get('state') or 'unknown'}） | - | - |")
    lines.append("")
    return "\n".join(lines)


def write_context(root: Path, episode: str, stage_key: str, payload: Dict[str, Any]) -> Path:
    path = context_path(root, episode, stage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    stable_payload = dict(payload)
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = None
        if isinstance(existing, dict):
            existing_semantic = {key: value for key, value in existing.items() if key != "generated_at"}
            current_semantic = {key: value for key, value in stable_payload.items() if key != "generated_at"}
            if existing_semantic == current_semantic:
                # A regenerated diagnostic with identical semantics must not revoke an already
                # accepted release merely because the wall clock advanced.
                stable_payload["generated_at"] = existing.get("generated_at")
    text = json.dumps(stable_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return path
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    md_path = context_md_path(root, episode, stage_key)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_context_markdown(stable_payload), encoding="utf-8")
    return path


def validate_pack(path: Path) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    try:
        data = load_pack(path)
    except Exception as exc:
        return {"path": str(path), "status": "fail", "issues": [{"severity": "block", "message": str(exc)}]}
    for key in REQUIRED_TOP:
        if key not in data or data.get(key) in (None, "", []):
            issues.append({"severity": "block", "message": f"missing `{key}`"})
    if data.get("kind") != GENRE_PACK_KIND:
        issues.append({"severity": "block", "message": f"kind must be {GENRE_PACK_KIND}"})
    if data.get("version") != 1:
        issues.append({"severity": "block", "message": "version must be 1"})
    fields = data.get("motion_contract_fields")
    if not isinstance(fields, list) or not all(isinstance(item, str) and item for item in fields):
        issues.append({"severity": "block", "message": "motion_contract_fields must be non-empty string array"})
    scenes = data.get("scene_archetypes")
    if not isinstance(scenes, list) or not scenes:
        issues.append({"severity": "block", "message": "scene_archetypes must be non-empty array"})
    else:
        seen = set()
        for idx, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                issues.append({"severity": "block", "message": f"scene_archetypes[{idx}] must be object"})
                continue
            sid = str(scene.get("id") or "")
            if sid in seen:
                issues.append({"severity": "block", "message": f"duplicate scene id `{sid}`"})
            seen.add(sid)
            for key in REQUIRED_SCENE:
                if key not in scene or scene.get(key) in (None, "", []):
                    issues.append({"severity": "block", "message": f"scene `{sid or idx}` missing `{key}`"})
            unknown = [item for item in scene.get("required_contract_fields") or [] if item not in (fields or [])]
            if unknown:
                issues.append({"severity": "warn", "message": f"scene `{sid}` requires fields not declared top-level: {unknown}"})
    status = "fail" if any(item["severity"] == "block" for item in issues) else ("warn" if issues else "pass")
    return {
        "path": str(path),
        "genre_key": data.get("genre_key"),
        "label": data.get("label"),
        "status": status,
        "issues": issues,
    }


def validate_all() -> Dict[str, Any]:
    packs = [validate_pack(path) for path in pack_paths()]
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for item in packs:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {
        "kind": "n2d_genre_pack_validation",
        "version": 1,
        "pack_dir": str(PACK_DIR),
        "packs": packs,
        "summary": counts,
        "status": "fail" if counts.get("fail") else ("warn" if counts.get("warn") else "pass"),
    }


def render_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# n2d Genre Pack Validation",
        "",
        f"- 状态：{payload.get('status')}",
        f"- pack 数：{len(payload.get('packs') or [])}",
        "",
        "| genre | status | issues |",
        "|---|---|---:|",
    ]
    for item in payload.get("packs") or []:
        lines.append(f"| {item.get('genre_key') or item.get('path')} | {item.get('status')} | {len(item.get('issues') or [])} |")
    lines.append("")
    return "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="validate/list n2d genre packs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("validate")
    p.add_argument("pack", nargs="?")
    p.add_argument("--all", action="store_true")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("list")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("context")
    p.add_argument("root")
    p.add_argument("episode")
    p.add_argument("stage_key")
    p.add_argument("--write", action="store_true")
    p.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    if ns.cmd == "list":
        packs = [load_pack(path) for path in pack_paths()]
        payload = {
            "kind": "n2d_genre_pack_index",
            "version": 1,
            "packs": [
                {"genre_key": item.get("genre_key"), "label": item.get("label"), "aliases": item.get("aliases") or []}
                for item in packs
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else "\n".join(f"- {p['genre_key']}: {p['label']}" for p in payload["packs"]))
        return 0
    if ns.cmd == "context":
        payload = build_context(Path(ns.root), ns.episode, ns.stage_key)
        if ns.write:
            path = write_context(Path(ns.root), ns.episode, ns.stage_key, payload)
            payload["path"] = str(path)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_context_markdown(payload))
        return 1 if payload.get("status") == "fail" else 0
    if ns.all or not ns.pack:
        payload = validate_all()
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
        return 1 if payload.get("status") == "fail" else 0
    path = Path(ns.pack)
    if not path.is_absolute():
        path = PACK_DIR / path
    payload = validate_pack(path)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown({"status": payload["status"], "packs": [payload]}))
    return 1 if payload.get("status") == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
