#!/usr/bin/env python3
"""Detect new/high-risk production conditions that require a mini-pilot."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set


SCRIPT_DIR = Path(__file__).resolve().parent
LIB = SCRIPT_DIR.parents[0] / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

try:
    from n2d_route import normalize_episode  # type: ignore
except Exception:  # pragma: no cover
    normalize_episode = lambda x: str(x or "").strip()  # type: ignore

import preventive_contracts  # noqa: E402


VERSION = 1
OUT_JSON = "mini_pilot_risk_{episode}.json"
OUT_MD = "mini_pilot_risk_{episode}.md"
ACCEPT_JSON = "mini_pilot_acceptance_{episode}.json"
RISK_TO_COVERAGE = {
    "new_character": "face",
    "multi_character_interaction": "action",
    "complex_action_or_contact": "action",
    "native_av_or_lipsync": "lipsync",
    "big_expression_closeup": "face",
    "new_backend_route": "routing",
    "seam_sensitive": "seam",
    "new_scene_or_vfx": "scene",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(str(k) + " " + flatten(v) for k, v in value.items())
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    return str(value or "")


def storyboard(root: Path, episode: str) -> List[Mapping[str, Any]]:
    data = load_json(root / "脚本" / episode / "storyboard.json")
    clips = data.get("clips") if isinstance(data, Mapping) else []
    return [c for c in clips or [] if isinstance(c, Mapping)]


def clip_id(row: Mapping[str, Any], idx: int) -> str:
    raw = str(row.get("clip_id") or row.get("clip") or row.get("id") or row.get("label") or "").strip()
    m = re.search(r"(?:Clip[_\s-]?|CLIP)(\d+)", raw, re.I)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    m = re.search(r"(\d+)", raw)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return raw or f"Clip_{idx:02d}"


def characters(clip: Mapping[str, Any]) -> Set[str]:
    out: Set[str] = set()
    for key in ("character_ids", "characters", "required_characters"):
        raw = clip.get(key)
        if isinstance(raw, list):
            out.update(str(x).strip() for x in raw if str(x).strip())
        elif isinstance(raw, str):
            out.update(re.findall(r"\bCHAR[_A-Za-z0-9\u4e00-\u9fff-]+\b", raw))
    out.update(re.findall(r"\bCHAR[_A-Za-z0-9\u4e00-\u9fff-]+\b", flatten(clip)))
    return out


def assets(clip: Mapping[str, Any]) -> Set[str]:
    return set(re.findall(r"\b(?:LOC|PROP|WEAPON|OUTFIT|VFX)[_A-Za-z0-9\u4e00-\u9fff-]+\b", flatten(clip)))


def previous_seen(root: Path, episode: str) -> Set[str]:
    """Best-effort seen registry from earlier mini-pilot reports."""
    seen: Set[str] = set()
    for path in production_dir(root).glob("mini_pilot_risk_*.json"):
        if episode in path.name:
            continue
        data = load_json(path)
        for row in (data.get("risk_clips") if isinstance(data, Mapping) else []) or []:
            seen.update(str(x) for x in row.get("characters") or [])
            seen.update(str(x) for x in row.get("assets") or [])
    return seen


def route_text(root: Path, episode: str) -> str:
    paths = [
        root / "出视频" / episode / "prompt" / "video_model_routes.json",
        root / "生产数据" / f"video_model_routes_{episode}.json",
    ]
    buf: List[str] = []
    for path in paths:
        if path.is_file():
            try:
                buf.append(path.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                pass
    return "\n".join(buf).lower()


def settings_text(root: Path) -> str:
    try:
        return (root / "_设置.md").read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def risk_clips(root: Path, episode: str) -> List[Dict[str, Any]]:
    route = route_text(root, episode)
    settings = settings_text(root)
    seen = previous_seen(root, episode)
    rows: List[Dict[str, Any]] = []
    for idx, clip in enumerate(storyboard(root, episode), 1):
        cid = clip_id(clip, idx)
        text = flatten(clip)
        low = text.lower()
        chars = sorted(characters(clip))
        asset_ids = sorted(assets(clip))
        risks: Set[str] = set()
        if any(ch not in seen for ch in chars):
            risks.add("new_character")
        if len(chars) >= 2:
            risks.add("multi_character_interaction")
        if preventive_contracts.clip_needs_physics(clip):
            risks.add("complex_action_or_contact")
        if "原生音画" in settings or "native_av" in route or "native_speech" in route or preventive_contracts.clip_needs_audio_timing(clip):
            risks.add("native_av_or_lipsync")
        if any(x in text for x in ("近景", "特写", "大表情", "哭", "笑", "怒", "惊恐")) or any(x in low for x in ("close-up", "closeup", "cu", "mcu", "expression")):
            risks.add("big_expression_closeup")
        if "backend" in route or "primary" in route or "fallback" in route:
            risks.add("new_backend_route")
        if any(x in low for x in ("need_end_frame", "endframe", "seam", "match cut")) or any(x in text for x in ("接缝", "首尾帧", "转场")):
            risks.add("seam_sensitive")
        if any(a.startswith(("LOC_", "VFX_")) for a in asset_ids):
            risks.add("new_scene_or_vfx")
        if risks:
            rows.append({
                "clip_id": cid,
                "risk_factors": sorted(risks),
                "coverage_required": sorted({RISK_TO_COVERAGE[r] for r in risks}),
                "characters": chars,
                "assets": asset_ids,
                "reason": text[:220],
            })
    rows.sort(key=lambda r: (-len(r["risk_factors"]), r["clip_id"]))
    return rows[:3]


def acceptance_path(root: Path, episode: str) -> Path:
    return production_dir(root) / ACCEPT_JSON.format(episode=episode)


def first_episode_pilot_path(root: Path, episode: str) -> Path:
    return production_dir(root) / f"pilot_acceptance_{episode}.json"


def acceptance_data(root: Path, episode: str) -> Optional[Mapping[str, Any]]:
    data = load_json(acceptance_path(root, episode))
    if isinstance(data, Mapping):
        return data
    if normalize_episode(episode) == "第1集":
        data = load_json(first_episode_pilot_path(root, episode))
        if isinstance(data, Mapping):
            return data
    return None


def check_acceptance(root: Path, episode: str, risks: Sequence[Mapping[str, Any]]) -> List[str]:
    if not risks:
        return []
    data = acceptance_data(root, episode)
    if not isinstance(data, Mapping):
        return [f"缺 {ACCEPT_JSON.format(episode=episode)}；本集存在新/高风险条件，需先打 2-3 个代表镜头。"]
    issues = preventive_contracts.pilot_acceptance_evidence_issues(root, data)
    status = str(data.get("status") or data.get("verdict") or "").strip().lower()
    if status not in {"accepted", "pass", "green"}:
        issues.append(f"mini-pilot status={status or 'unset'}")
    required = {cov for row in risks for cov in row.get("coverage_required", [])}
    coverage = {str(x).strip().lower() for x in (data.get("coverage") or [])}
    missing = sorted(required - coverage)
    if missing:
        issues.append("mini-pilot coverage 缺：" + "、".join(missing))
    clips = data.get("clips") if isinstance(data.get("clips"), list) else []
    if len(clips) < min(2, len(risks)):
        issues.append("mini-pilot clips 数量不足")
    return issues


def template(root: Path, episode: str) -> Dict[str, Any]:
    risks = risk_clips(root, episode)
    return {
        "kind": "n2d_mini_pilot_acceptance",
        "version": VERSION,
        "episode": episode,
        "status": "draft",
        "generated_at": now_iso(),
        "risk_selection": {"method": "first/new/high-risk deterministic sampler", "risk_clips": risks},
        "coverage": sorted({cov for row in risks for cov in row.get("coverage_required", [])}),
        "clips": [
            {"clip_id": row["clip_id"], "risk_factors": row["risk_factors"], "artifact_path": "", "artifact_sha256": "", "qc_report": ""}
            for row in risks
        ],
        "checks": {cov: "todo" for row in risks for cov in row.get("coverage_required", [])},
    }


def scaffold(root: Path, episode: str, *, force: bool = False) -> Path:
    path = acceptance_path(root, episode)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return path
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(template(root, episode), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def build_report(root: Path, episode: str, *, write_missing: bool = False) -> Dict[str, Any]:
    root = root.resolve()
    episode = normalize_episode(episode)
    risks = risk_clips(root, episode)
    if write_missing and risks and not acceptance_path(root, episode).exists():
        scaffold(root, episode)
    issues = check_acceptance(root, episode, risks)
    return {
        "kind": "n2d_mini_pilot_risk",
        "version": VERSION,
        "root": str(root),
        "episode": episode,
        "generated_at": now_iso(),
        "status": "blocked" if issues else "pass",
        "summary": {"risk_clips": len(risks), "issues": len(issues)},
        "acceptance_path": relpath(root, acceptance_path(root, episode)),
        "risk_clips": risks,
        "issues": issues,
    }


def render_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# n2d Mini Pilot Risk",
        "",
        f"- 集：{payload.get('episode')}",
        f"- 状态：{payload.get('status')}",
        f"- 汇总：{payload.get('summary')}",
        "",
        "| clip | risks | coverage |",
        "|---|---|---|",
    ]
    for row in payload.get("risk_clips") or []:
        lines.append(f"| {row.get('clip_id')} | {', '.join(row.get('risk_factors') or [])} | {', '.join(row.get('coverage_required') or [])} |")
    if payload.get("issues"):
        lines.extend(["", "## Issues", ""])
        lines.extend(f"- {issue}" for issue in payload.get("issues") or [])
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, episode: str, payload: Mapping[str, Any]) -> Dict[str, str]:
    out = production_dir(root)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / OUT_JSON.format(episode=episode)
    md_path = out / OUT_MD.format(episode=episode)
    tmp = json_path.with_name(f"{json_path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, json_path)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {"json": relpath(root, json_path), "markdown": relpath(root, md_path)}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="check/scaffold n2d mini-pilot risk sampler")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--write-missing", action="store_true")
    ap.add_argument("--scaffold", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    ep = normalize_episode(ns.episode)
    if ns.scaffold:
        path = scaffold(root, ep, force=ns.force)
        print(json.dumps({"path": str(path)}, ensure_ascii=False) if ns.json else str(path))
        return 0
    payload = build_report(root, ep, write_missing=ns.write_missing)
    if ns.write:
        payload["outputs"] = write_outputs(root, payload["episode"], payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
    return 2 if payload.get("status") == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
