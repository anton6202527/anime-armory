#!/usr/bin/env python3
"""Plan optional open-source trajectory/camera controller usage for n2d clips."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


KIND = "n2d_trajectory_controller_plan"


def ep_label(value: str) -> str:
    return value if value.startswith("第") else f"第{value}集"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def controller_status() -> Dict[str, Any]:
    return {
        "motionctrl": {
            "enabled": bool(os.environ.get("MOTIONCTRL_HOME")),
            "home": os.environ.get("MOTIONCTRL_HOME", ""),
            "use_for": ["camera_path", "spatial_path", "object_motion"],
        },
        "cameractrl": {
            "enabled": bool(os.environ.get("CAMERACTRL_HOME")),
            "home": os.environ.get("CAMERACTRL_HOME", ""),
            "use_for": ["camera_path", "camera_pose_sequence"],
        },
        "dragnuwa": {
            "enabled": bool(os.environ.get("DRAGNUWA_HOME")),
            "home": os.environ.get("DRAGNUWA_HOME", ""),
            "use_for": ["spatial_path", "trajectory_points"],
        },
    }


def choose_controller(route: Mapping[str, Any]) -> Dict[str, Any]:
    controls = ((route.get("execution_recipe") or {}).get("control_inputs") or {}) if isinstance(route.get("execution_recipe"), Mapping) else {}
    required = controls.get("required_inputs") or []
    shot_type = str(route.get("shot_type") or "")
    if "camera_path" in required and ("spatial_path" in required or shot_type in {"chase", "flight"}):
        return {"primary": "motionctrl", "fallback": ["cameractrl", "dragnuwa"], "reason": "camera + object/path motion both matter"}
    if "camera_path" in required:
        return {"primary": "cameractrl", "fallback": ["motionctrl"], "reason": "camera trajectory is the main control"}
    if "spatial_path" in required:
        return {"primary": "dragnuwa", "fallback": ["motionctrl"], "reason": "object/spatial trajectory is the main control"}
    return {"primary": "", "fallback": [], "reason": "no trajectory controller needed"}


def build_plan(root: Path, ep: str) -> Dict[str, Any]:
    routes = load_json(root / "出视频" / ep / "prompt" / "video_model_routes.json")
    route_rows = routes.get("routes") if isinstance(routes, dict) else []
    status = controller_status()
    clips = []
    for route in route_rows or []:
        if not isinstance(route, dict):
            continue
        chosen = choose_controller(route)
        if not chosen["primary"]:
            continue
        primary_status = status.get(chosen["primary"], {})
        recipe = route.get("execution_recipe") if isinstance(route.get("execution_recipe"), Mapping) else {}
        controls = recipe.get("control_inputs") if isinstance(recipe.get("control_inputs"), Mapping) else {}
        clips.append({
            "clip_id": route.get("clip_id"),
            "shot_type": route.get("shot_type"),
            "controller": chosen["primary"],
            "fallback_controllers": chosen["fallback"],
            "enabled": bool(primary_status.get("enabled")),
            "controller_home": primary_status.get("home") or "",
            "reason": chosen["reason"],
            "required_inputs": controls.get("required_inputs") or [],
            "control_manifest": controls.get("manifest_path") or "",
            "execution_recipe_backend": recipe.get("execution_backend") or route.get("primary_backend"),
            "status": "ready_to_run" if primary_status.get("enabled") else "planned_env_missing",
        })
    return {
        "kind": KIND,
        "version": 1,
        "episode": ep,
        "controller_status": status,
        "clips": clips,
        "summary": {
            "controller_candidate_clips": len(clips),
            "ready_to_run": sum(1 for c in clips if c["status"] == "ready_to_run"),
            "planned_env_missing": sum(1 for c in clips if c["status"] == "planned_env_missing"),
        },
        "notes": [
            "This plan is optional. It does not download or run MotionCtrl/CameraCtrl/DragNUWA; set *_HOME env vars and run the controller-specific bridge only when local stacks are prepared.",
        ],
    }


def render_markdown(plan: Mapping[str, Any]) -> str:
    lines = [
        "# 开源轨迹/运镜控制器适配计划",
        "",
        f"- episode: {plan.get('episode')}",
        f"- candidate_clips: {(plan.get('summary') or {}).get('controller_candidate_clips', 0)}",
        "",
        "| Clip | Shot | Controller | Status | Required Inputs |",
        "|---|---|---|---|---|",
    ]
    for clip in plan.get("clips") or []:
        lines.append(
            f"| {clip.get('clip_id')} | {clip.get('shot_type')} | {clip.get('controller')} | "
            f"{clip.get('status')} | {', '.join(clip.get('required_inputs') or [])} |"
        )
    return "\n".join(lines)


def write_plan(plan: Mapping[str, Any], root: Path, ep: str) -> Dict[str, Path]:
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    out_json = prod / f"trajectory_controller_plan_{ep}.json"
    out_md = prod / f"trajectory_controller_plan_{ep}.md"
    out_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(render_markdown(plan) + "\n", encoding="utf-8")
    return {"json": out_json, "markdown": out_md}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="plan optional MotionCtrl/CameraCtrl/DragNUWA usage")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root.rstrip("/"))
    ep = ep_label(ns.episode)
    plan = build_plan(root, ep)
    if ns.write:
        paths = write_plan(plan, root, ep)
        plan["written"] = {k: str(v) for k, v in paths.items()}
    print(render_markdown(plan) if ns.markdown else json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
