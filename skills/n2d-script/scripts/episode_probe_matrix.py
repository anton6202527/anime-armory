#!/usr/bin/env python3
"""episode_probe_matrix.py — 每集高光/风险探针矩阵。

在全量出图/出视频之前，用 storyboard + shot_risk_audit 信号挑 2-5 个代表镜头做打样：
开场钩、封面/爽点、多人同框、动作/VFX、强情绪近景。产物是纯计划，不花钱。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import shot_risk_audit as sra  # noqa: E402

KIND = "n2d_episode_probe_matrix"
KEY_RE = re.compile(r"(🔑|🪝|⚡|💥|封面|爽点|反转|真相|系统|升级|觉醒|打斗|追逐|法术|多人|同框|CU|ECU|特写)")


def load_storyboard(root: Path, ep: str) -> List[dict]:
    try:
        data = json.loads((root / "脚本" / ep / "storyboard.json").read_text(encoding="utf-8"))
    except Exception:
        return []
    clips = data.get("clips") if isinstance(data, dict) else []
    return [c for c in clips or [] if isinstance(c, dict)]


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    if isinstance(value, dict):
        return " ".join(flatten(v) for v in value.values())
    return str(value or "")


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}")


def classify_probe(clip: Mapping[str, Any], risk: Mapping[str, Any], idx: int) -> Dict[str, Any]:
    blob = flatten(clip)
    tags = list(risk.get("tags") or [])
    reasons: List[str] = []
    if idx == 1:
        reasons.append("opening_probe")
    if KEY_RE.search(blob):
        reasons.append("highlight_probe")
    if "multi_character" in tags or "many_named_characters" in tags:
        reasons.append("multi_subject_probe")
    if any(t in tags for t in ("high_motion", "vfx_or_asset")):
        reasons.append("motion_or_vfx_probe")
    if any(t in tags for t in ("closeup", "large_expression_span", "mouth_visible")):
        reasons.append("performance_probe")
    if not reasons and int(risk.get("score") or 0) >= 5:
        reasons.append("risk_probe")
    return {
        "clip": clip_id(clip, idx),
        "score": risk.get("score", 0),
        "reasons": reasons,
        "image_probe": "先出首帧 + 必要尾帧/中锚，跑 image_qc/ref plan 后再全量。",
        "video_probe": "用该镜 primary/fallback route 各出 1 条短样，核身份/动作/接缝/音画。",
        "acceptance": ["角色/资产不漂", "动作节拍可读", "首尾帧能被后端消费", "不触发 gate block"],
    }


def build_matrix(root: Path, ep: str, limit: int = 5) -> Dict[str, Any]:
    ep = sra.ep_label(ep)
    clips = load_storyboard(root, ep)
    risk = sra.audit(str(root), ep)
    by_id = {str(row.get("id")): row for row in risk.get("clips") or []}
    risk_rows = risk.get("clips") or []
    probes: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip, idx)
        row = by_id.get(cid)
        if row is None and idx - 1 < len(risk_rows):
            row = risk_rows[idx - 1]
        if not isinstance(row, Mapping):
            row = {}
        probe = classify_probe(clip, row if isinstance(row, Mapping) else {}, idx)
        if probe["reasons"]:
            probes.append(probe)
    probes = sorted(probes, key=lambda x: (x["score"], "opening_probe" in x["reasons"]), reverse=True)
    # 保证开场镜不被排序挤掉。
    opening = [p for p in probes if "opening_probe" in p["reasons"]]
    selected: List[Dict[str, Any]] = []
    for p in opening + probes:
        if p["clip"] not in {x["clip"] for x in selected}:
            selected.append(p)
        if len(selected) >= limit:
            break
    return {
        "kind": KIND,
        "episode": ep,
        "clip_count": len(clips),
        "probes": selected,
        "risk_summary": risk.get("summary") or {},
        "notes": ["report-only；探针矩阵不改变时长逻辑，不自动生成图片/视频。"],
    }


def render_md(matrix: Mapping[str, Any]) -> str:
    lines = [
        "# 每集高光/风险探针矩阵",
        "",
        f"- episode: {matrix.get('episode')}",
        f"- clip_count: {matrix.get('clip_count')}",
        "",
        "| Clip | Score | Reasons | Image Probe | Video Probe |",
        "|---|---:|---|---|---|",
    ]
    for p in matrix.get("probes") or []:
        lines.append(
            f"| {p.get('clip')} | {p.get('score')} | {'、'.join(p.get('reasons') or [])} | "
            f"{p.get('image_probe')} | {p.get('video_probe')} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, ep: str, matrix: Mapping[str, Any]) -> Tuple[Path, Path]:
    out = root / "生产数据"
    out.mkdir(parents=True, exist_ok=True)
    jp = out / f"episode_probe_matrix_{ep}.json"
    mp = out / f"episode_probe_matrix_{ep}.md"
    tmp = jp.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(matrix, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, jp)
    tmp_md = mp.with_suffix(".md.tmp")
    tmp_md.write_text(render_md(matrix), encoding="utf-8")
    os.replace(tmp_md, mp)
    return jp, mp


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 每集高光/风险探针矩阵")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    ep = sra.ep_label(ns.episode)
    matrix = build_matrix(root, ep, limit=ns.limit)
    if ns.write:
        jp, mp = write_outputs(root, ep, matrix)
        matrix["outputs"] = {"json": str(jp), "md": str(mp)}
    if ns.json:
        print(json.dumps(matrix, ensure_ascii=False, indent=2))
    else:
        print(render_md(matrix))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
