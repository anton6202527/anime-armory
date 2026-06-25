#!/usr/bin/env python3
"""video_production_pack.py — 视频生成前的生产增强包。

P0/P1：把首/中/尾锚帧链、motion sample 小样、route empirical scorecard
收束成一份可执行侧车。它不调用视频后端，只给 n2d-video / router / review 一个统一入口。
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

KIND = "n2d_video_production_pack"
CHAR_RE = re.compile(r"\bCHAR_[A-Za-z0-9_\-\u4e00-\u9fff]+\b")


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


def ep_label(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = re.search(r"\d+", text)
    return f"第{m.group(0)}集" if m else text


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    if isinstance(value, dict):
        return " ".join(str(k) + " " + flatten(v) for k, v in value.items())
    return str(value or "")


def storyboard(root: Path, ep: str) -> List[dict]:
    data = load_json(root / "脚本" / ep / "storyboard.json")
    clips = data.get("clips") if isinstance(data, dict) else []
    return [c for c in clips or [] if isinstance(c, dict)]


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    """归一化 Clip 标识为 `Clip_NN`，与 n2d-model-router.make_clip_id 及 image runner 落盘命名同口径。

    storyboard 的 clip `id` 常是作者自定写法（`镜头3` / `clip#5` / `Clip 3`）；而 router 出的
    video_model_routes.json 的 `clip_id` 与 image runner 落盘的 `Clip_NN.png` 都已归一化成 `Clip_NN`。
    若此处返回原始 id，route_by_clip 的键(`Clip_03`)与本侧查键(`镜头3`)对不上 → 高动镜静默丢后端
    路由/运动参考、anchor_chain 首帧路径也指错。跨 skill 无共享层，各处各自维护副本——改这里需同步
    router.make_clip_id 与 image runner 的落盘命名规则。"""
    raw = clip.get("clip_id") or clip.get("id") or clip.get("label") or ""
    text = str(raw).strip()
    m = re.search(r"(?:Clip[_\s-]?|CLIP)(\d+)", text, re.I)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    m = re.search(r"(\d+)", text)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return f"Clip_{idx:02d}"


def routes(root: Path, ep: str) -> List[dict]:
    data = load_json(root / "出视频" / ep / "prompt" / "video_model_routes.json")
    rows = data.get("routes") if isinstance(data, dict) else []
    return [r for r in rows or [] if isinstance(r, dict)]


def anchor_chain_for_clip(ep: str, clip: Mapping[str, Any], idx: int) -> Dict[str, Any]:
    cid = clip_id(clip, idx)
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    anchors = []
    mid = cont.get("midframe")
    if isinstance(mid, Mapping):
        anchors.append({
            "kind": "midframe",
            "at_sec": mid.get("at_sec") or mid.get("split_at_sec"),
            "image": mid.get("midframe_png") or mid.get("anchor_png") or f"出图/{ep}/图片/{cid}_mid.png",
            "reason": mid.get("reason") or "default_midframe",
        })
    for i, item in enumerate(cont.get("anchors") or [], 1):
        if isinstance(item, Mapping):
            anchors.append({
                "kind": "anchor",
                "at_sec": item.get("at_sec"),
                "image": item.get("anchor_png") or f"出图/{ep}/图片/{cid}_a{i}.png",
                "reason": item.get("reason") or "planned_anchor",
            })
    need_end = bool(cont.get("need_endframe") or cont.get("need_end") or cont.get("endframe"))
    chain = {
        "clip": cid,
        "first_frame": cont.get("first_frame") or f"出图/{ep}/图片/{cid}.png",
        "anchors": anchors,
        "last_frame": cont.get("endframe_png") or cont.get("last_frame") or (f"出图/{ep}/图片/{cid}_end.png" if need_end else ""),
        "status": "ready" if anchors or need_end else "minimal",
        "policy": "first + anchors + last；长镜/动作镜优先用多帧，后端不支持再拆段。",
    }
    return chain


def anchor_chains(root: Path, ep: str, clips: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [anchor_chain_for_clip(ep, clip, idx) for idx, clip in enumerate(clips, 1)]


def route_by_clip(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    return {str(r.get("clip_id") or r.get("clip") or ""): r for r in rows}


def motion_sample_plan(root: Path, ep: str, clips: Sequence[Mapping[str, Any]], route_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    lib = load_json(root / "生产数据" / "motion_reference_library.json")
    references = lib.get("references") if isinstance(lib, dict) else []
    refs_by_type: Dict[str, List[Mapping[str, Any]]] = {}
    for ref in references or []:
        if isinstance(ref, Mapping):
            refs_by_type.setdefault(str(ref.get("spectacle_type") or ""), []).append(ref)
    routes_map = route_by_clip(route_rows)
    plan: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip, idx)
        blob = flatten(clip)
        route = routes_map.get(cid, {})
        shot_type = str(route.get("shot_type") or "")
        risk = set(route.get("risk_flags") or [])
        high_motion = any(x in blob for x in ("打斗", "追逐", "飞行", "法术", "冲刺", "拥抱", "拉扯")) or bool(risk & {"high_speed_motion", "contact_motion", "physical_interaction"})
        if not high_motion:
            continue
        matched = refs_by_type.get(shot_type) or refs_by_type.get(str(route.get("spectacle_type") or "")) or []
        plan.append({
            "clip": cid,
            "shot_type": shot_type or "high_motion",
            "route_backend": route.get("primary_backend"),
            "existing_motion_references": [r.get("reference_id") for r in matched[:3]],
            "sample_required": not bool(matched),
            "sample_output": f"出视频/{ep}/motion_samples/{cid}_sample.mp4",
            "acceptance": ["动作方向可读", "主体不串换", "接触点不融化", "首尾帧能接回正片"],
        })
    return plan


def _score_key(route: Mapping[str, Any]) -> str:
    return f"{route.get('primary_backend') or 'unknown'}::{route.get('shot_type') or 'unknown'}"


def route_empirical_scorecard(root: Path, ep: str, route_rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    qc = load_json(root / "生产数据" / f"spectacle_video_qc_{ep}.json")
    checks = {str(r.get("clip")): r for r in (qc.get("checks") if isinstance(qc, dict) else []) or [] if isinstance(r, Mapping)}
    rows: Dict[str, Dict[str, Any]] = {}
    for route in route_rows:
        key = _score_key(route)
        row = rows.setdefault(key, {
            "backend": route.get("primary_backend"),
            "shot_type": route.get("shot_type"),
            "attempts": 0,
            "passed": 0,
            "clips": [],
            "confidence": "pending",
        })
        row["attempts"] += 1
        cid = str(route.get("clip_id") or route.get("clip") or "")
        check = checks.get(cid, {})
        evidence = str(check.get("evidence_status") or "")
        if evidence in {"measured", "external_report", "vlm_verified", "tracked"}:
            row["passed"] += 1
        row["clips"].append(cid)
    for row in rows.values():
        attempts = int(row.get("attempts") or 0)
        passed = int(row.get("passed") or 0)
        row["pass_rate"] = round(passed / attempts, 3) if attempts else None
        row["confidence"] = "measured" if passed else "pending"
    return {
        "kind": "n2d_route_empirical_scorecard",
        "episode": ep,
        "rows": sorted(rows.values(), key=lambda r: (str(r.get("backend")), str(r.get("shot_type")))),
        "policy": "后续 router 可优先 measured/pass_rate 高的 backend+shot_type；无证据只作 pending，不臆造通过率。",
    }


def build_pack(root: Path, ep: str) -> Dict[str, Any]:
    ep = ep_label(ep)
    clips = storyboard(root, ep)
    route_rows = routes(root, ep)
    anchors = anchor_chains(root, ep, clips)
    motion = motion_sample_plan(root, ep, clips, route_rows)
    scorecard = route_empirical_scorecard(root, ep, route_rows)
    return {
        "kind": KIND,
        "version": 1,
        "episode": ep,
        "summary": {
            "clips": len(clips),
            "route_rows": len(route_rows),
            "anchor_chains": len(anchors),
            "motion_samples_required": sum(1 for m in motion if m.get("sample_required")),
            "route_score_rows": len(scorecard.get("rows") or []),
        },
        "anchor_chains": anchors,
        "motion_sample_plan": motion,
        "route_empirical_scorecard": scorecard,
        "notes": ["不触发视频生成；这是出视频前的锚帧/动作小样/路由实测生产侧车。"],
    }


def render_md(pack: Mapping[str, Any]) -> str:
    s = pack.get("summary") or {}
    lines = [
        "# 视频生产包",
        "",
        f"- episode: {pack.get('episode')}",
        f"- anchor_chains: {s.get('anchor_chains')}",
        f"- motion_samples_required: {s.get('motion_samples_required')}",
        f"- route_score_rows: {s.get('route_score_rows')}",
        "",
        "## 锚帧链",
        "",
        "| Clip | First | Anchors | Last |",
        "|---|---|---|---|",
    ]
    for row in pack.get("anchor_chains") or []:
        anchors = "、".join(a.get("image") for a in row.get("anchors") or [] if a.get("image")) or "-"
        lines.append(f"| {row.get('clip')} | {row.get('first_frame')} | {anchors} | {row.get('last_frame') or '-'} |")
    lines += ["", "## 动作小样", "", "| Clip | Type | Required | Existing refs |", "|---|---|---|---|"]
    for row in pack.get("motion_sample_plan") or []:
        lines.append(f"| {row.get('clip')} | {row.get('shot_type')} | {row.get('sample_required')} | {'、'.join(row.get('existing_motion_references') or []) or '-'} |")
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, ep: str, pack: Mapping[str, Any]) -> Tuple[Path, Path]:
    out = root / "生产数据"
    jp = out / f"video_production_pack_{ep}.json"
    mp = out / f"video_production_pack_{ep}.md"
    write_atomic(jp, json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_atomic(mp, render_md(pack))
    return jp, mp


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 视频生产增强包")
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
