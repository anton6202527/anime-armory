#!/usr/bin/env python3
"""Bind a human picture-lock decision to the exact plan, animatic, song and frames."""
import argparse
import os
import sys
from datetime import date

import mv_utils


def build_lock(root, reviewer, notes):
    required = ("分镜/clip_plan.json", "节拍/beatgrid.json", "分镜/animatic.mp4", "生产数据/image_qc/image_qc.json")
    missing = [rel for rel in required if not os.path.exists(os.path.join(root, rel))]
    if missing:
        raise RuntimeError(f"picture lock 缺前置：{', '.join(missing)}")
    plan = mv_utils.load_json(os.path.join(root, "分镜", "clip_plan.json"), {}) or {}
    paths = list(required)
    song = mv_utils.find_song(root)
    if not song:
        raise RuntimeError("缺 歌/song.*")
    paths.append(mv_utils.relpath(root, song))
    paths.extend(c.get("image_path") for c in plan.get("clips", []) if c.get("image_path"))
    return {
        "schema_version": 1, "kind": "mv_picture_lock", "accepted": True,
        "reviewer": reviewer, "date": date.today().isoformat(), "notes": notes,
        "review_dimensions": ["narrative", "coverage", "cut_rhythm", "screen_direction", "identity", "color_script", "subtitle_safe_area"],
        "inputs_sha256": {rel: mv_utils.content_hash(os.path.join(root, rel)) for rel in paths},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    root = os.path.abspath(args.project_root)
    try:
        payload = build_lock(root, args.reviewer, args.notes)
    except RuntimeError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 1
    path = os.path.join(root, "制片", "picture_lock.json")
    mv_utils.write_json(path, payload)
    print(f"[ok] picture lock → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
