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
from typing import Any, Dict, List, Optional, Sequence


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
    return context_path(root, episode, stage_key).with_suffix(".md")


def pack_index() -> Dict[str, Dict[str, Any]]:
    packs = [load_pack(path) for path in pack_paths()]
    index: Dict[str, Dict[str, Any]] = {}
    for pack in packs:
        key = str(pack.get("genre_key") or "").strip().lower()
        if key:
            index[key] = pack
        for alias in pack.get("aliases") or []:
            text = str(alias or "").strip().lower()
            if text:
                index[text] = pack
    return index


def normalize_genre_key(value: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    index = pack_index()
    if text in index:
        return str(index[text].get("genre_key") or "")
    for alias, pack in index.items():
        if alias and alias in text:
            return str(pack.get("genre_key") or "")
    return ""


def load_pack_by_key(value: str) -> Optional[Dict[str, Any]]:
    key = normalize_genre_key(value)
    if not key:
        return None
    path = PACK_DIR / f"{key}.json"
    return load_pack(path) if path.is_file() else None


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
    for key in ("motion_contract", "action_contract", "video_contract", "continuity"):
        value = clip.get(key)
        if isinstance(value, dict):
            fields.update(value)
    return fields


def context_status(stage_key: str, issues: Sequence[Dict[str, Any]]) -> str:
    if not issues:
        return "pass"
    hard_stages = {"video_prompt", "video", "compose", "review"}
    has_block = any(item.get("severity") == "block" for item in issues)
    if has_block or stage_key in hard_stages:
        return "fail"
    return "warn"


def build_context(root: Path, episode: str, stage_key: str) -> Dict[str, Any]:
    root = root.resolve()
    genre_text = project_genre_text(root)
    pack = load_pack_by_key(genre_text)
    storyboard = load_storyboard(root, episode)
    clips = storyboard.get("clips") if isinstance(storyboard.get("clips"), list) else []
    active: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []
    if pack:
        for scene in pack.get("scene_archetypes") or []:
            matched = [clip for clip in clips if isinstance(clip, dict) and scene_matches_clip(scene, clip)]
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
                "matched_clips": [clip.get("id") or clip.get("clip_id") or "" for clip in matched],
                "required_contract_fields": scene.get("required_contract_fields") or [],
                "missing_by_clip": missing_by_clip,
                "style_binding": scene.get("style_binding"),
                "production_risks": scene.get("production_risks") or [],
            }
            active.append(row)
            for missing in missing_by_clip:
                issues.append({
                    "severity": "block" if stage_key in {"video_prompt", "video", "compose", "review"} else "warn",
                    "scene_id": scene.get("id"),
                    "clip": missing.get("clip"),
                    "message": "missing genre motion contract fields: " + ", ".join(missing.get("missing") or []),
                    "missing_fields": missing.get("missing") or [],
                })
    payload = {
        "kind": CONTEXT_KIND,
        "version": 1,
        "root": str(root),
        "episode": episode,
        "stage_key": stage_key,
        "generated_at": now_iso(),
        "genre": {
            "raw": genre_text,
            "genre_key": pack.get("genre_key") if pack else "",
            "label": pack.get("label") if pack else "",
            "matched": bool(pack),
        },
        "pack": {
            "motion_contract_fields": pack.get("motion_contract_fields") if pack else [],
            "qc_focus": pack.get("qc_focus") if pack else [],
            "degrade_plans": pack.get("degrade_plans") if pack else [],
            "style_binding_policy": pack.get("style_binding_policy") if pack else {},
        },
        "active_scene_archetypes": active,
        "issues": issues,
        "summary": {
            "active_scenes": len(active),
            "issues": len(issues),
            "matched_clips": len({clip for row in active for clip in row.get("matched_clips", []) if clip}),
        },
        "status": context_status(stage_key, issues),
    }
    return payload


def render_context_markdown(payload: Dict[str, Any]) -> str:
    genre = payload.get("genre") if isinstance(payload.get("genre"), dict) else {}
    pack = payload.get("pack") if isinstance(payload.get("pack"), dict) else {}
    lines = [
        "# n2d Genre Pack Context",
        "",
        f"- 集：{payload.get('episode')}",
        f"- 阶段：{payload.get('stage_key')}",
        f"- 题材：{genre.get('label') or genre.get('raw') or '未命中'}",
        f"- 状态：{payload.get('status')}",
        "",
        "## QC Focus",
        "",
    ]
    lines.extend([f"- {item}" for item in pack.get("qc_focus") or []] or ["- 无"])
    lines.extend(["", "## Active Scenes", "", "| scene | clips | missing |", "|---|---|---|"])
    for row in payload.get("active_scene_archetypes") or []:
        missing = "; ".join(
            f"{item.get('clip')}:{','.join(item.get('missing') or [])}"
            for item in row.get("missing_by_clip") or []
        ) or "-"
        lines.append(f"| {row.get('label')} | {','.join(row.get('matched_clips') or []) or '-'} | {missing} |")
    lines.append("")
    return "\n".join(lines)


def write_context(root: Path, episode: str, stage_key: str, payload: Dict[str, Any]) -> Path:
    path = context_path(root, episode, stage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    context_md_path(root, episode, stage_key).write_text(render_context_markdown(payload), encoding="utf-8")
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
