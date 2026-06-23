#!/usr/bin/env python3
"""Build a small probe pack for fight/chase/flight/large-scene backend tests."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
LIB = os.path.abspath(os.path.join(HERE, "..", "..", "n2d", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import shot_risk_audit  # noqa: E402
from n2d_contract import (  # noqa: E402
    SPECTACLE_BACKEND_BENCHMARK_KIND,
    SPECTACLE_PROBE_PACK_KIND,
    default_degrade_plan,
    motion_control_inputs_for_spectacle,
    spectacle_recommendations,
)

TARGET_TYPES = ("fight_exchange", "chase", "flight", "large_establishing")
BACKEND_MATRIX: Dict[str, List[str]] = {
    "fight_exchange": ["kling", "seedance", "dreamina"],
    "chase": ["seedance", "kling", "dreamina"],
    "flight": ["seedance", "kling", "veo"],
    "large_establishing": ["veo", "seedance", "dreamina"],
}


def ep_label(value: str) -> str:
    return value if value.startswith("第") else f"第{value}集"


def output_json_path(root: Path, ep: str) -> Path:
    return root / "生产数据" / f"spectacle_probe_pack_{ep}.json"


def output_md_path(root: Path, ep: str) -> Path:
    return root / "生产数据" / f"spectacle_probe_pack_{ep}.md"


def benchmark_path(root: Path) -> Path:
    return root / "生产数据" / "spectacle_backend_benchmark.json"


def choose_candidates(risk: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    chosen: Dict[str, Dict[str, Any]] = {}
    for clip in risk.get("clips") or []:
        if not isinstance(clip, Mapping):
            continue
        kind = str(clip.get("spectacle_type") or "")
        if kind not in TARGET_TYPES:
            continue
        current = chosen.get(kind)
        if current is None or int(clip.get("score") or 0) > int(current.get("score") or 0):
            chosen[kind] = dict(clip)
    return chosen


def build_probe_pack(root: Path, ep: str) -> Dict[str, Any]:
    risk = shot_risk_audit.audit(str(root), ep)
    chosen = choose_candidates(risk)
    probes: List[Dict[str, Any]] = []
    for kind in TARGET_TYPES:
        clip = chosen.get(kind)
        if not clip:
            continue
        probes.append({
            "spectacle_type": kind,
            "clip_id": clip.get("id"),
            "risk_score": clip.get("score"),
            "risk_tags": clip.get("tags") or [],
            "candidate_backends": BACKEND_MATRIX[kind],
            "control_inputs_required": list(motion_control_inputs_for_spectacle(kind)),
            "success_criteria": [
                "identity/pose does not drift across start-mid-end",
                "camera/path direction matches storyboard contract",
                "no extra unplanned action beats or unreadable contact",
                "usable first/last frame for downstream seam checks",
            ],
            "degrade_plan": default_degrade_plan(kind),
            "recommendations": spectacle_recommendations(kind),
        })
    gaps = [kind for kind in TARGET_TYPES if kind not in chosen]
    return {
        "kind": SPECTACLE_PROBE_PACK_KIND,
        "version": 1,
        "episode": ep,
        "probe_clips": probes,
        "coverage_gaps": gaps,
        "benchmark_write_path": str(benchmark_path(root)),
        "benchmark_schema": {
            "kind": SPECTACLE_BACKEND_BENCHMARK_KIND,
            "version": 1,
            "recommendations": {
                kind: {"primary_backend": BACKEND_MATRIX[kind][0], "score": None, "evidence": "fill after probe"}
                for kind in TARGET_TYPES
            },
        },
        "source_risk_summary": risk.get("summary") or {},
    }


def render_markdown(pack: Mapping[str, Any]) -> str:
    lines = [
        "# 高动态/大场景 Probe Pack",
        "",
        f"- episode: {pack.get('episode')}",
        f"- benchmark_write_path: {pack.get('benchmark_write_path')}",
        "",
        "| 类型 | Clip | 候选后端 | 控制输入 |",
        "|---|---|---|---|",
    ]
    for probe in pack.get("probe_clips") or []:
        lines.append(
            "| {kind} | {clip} | {backends} | {inputs} |".format(
                kind=probe.get("spectacle_type", ""),
                clip=probe.get("clip_id", ""),
                backends=", ".join(probe.get("candidate_backends") or []),
                inputs=", ".join(probe.get("control_inputs_required") or []) or "-",
            )
        )
    gaps = pack.get("coverage_gaps") or []
    if gaps:
        lines.extend(["", "## 覆盖缺口", ""])
        for gap in gaps:
            lines.append(f"- {gap}: 本集没有代表 Clip，可在后续集补 probe。")
    return "\n".join(lines)


def write_pack(pack: Mapping[str, Any], root: Path, ep: str) -> Dict[str, Path]:
    jp = output_json_path(root, ep)
    mp = output_md_path(root, ep)
    jp.parent.mkdir(parents=True, exist_ok=True)
    jp.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mp.write_text(render_markdown(pack) + "\n", encoding="utf-8")
    return {"json": jp, "markdown": mp}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="build n2d spectacle backend probe pack")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root.rstrip("/"))
    ep = ep_label(ns.episode)
    pack = build_probe_pack(root, ep)
    if ns.write:
        paths = write_pack(pack, root, ep)
        pack["written"] = {k: str(v) for k, v in paths.items()}
    if ns.markdown:
        print(render_markdown(pack))
    else:
        print(json.dumps(pack, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
