#!/usr/bin/env python3
"""Create a hash-bound MV provenance manifest and optional C2PA sidecar input."""
import argparse
import glob
import os
import shutil
import subprocess
import sys
from datetime import date

import mv_utils


CORE_INPUTS = (
    "_meta.json", "_设置.md", "视觉蓝图.md", "词/lyrics.md", "节拍/beatgrid.json",
    "分镜/clip_plan.json", "分镜/timeline_manifest.json", "分镜/timeline.otio",
    "设定/identity_registry.json", "设定/asset_registry.json", "分镜/reference_plan.json",
    "生产数据/image_qc/image_qc.json", "生产数据/video_inherit_contract/inherit_contract.json",
    "生产数据/video_qc/video_qc.json", "字幕/alignment_report.json", "制片/picture_lock.json",
    "合规/rights_manifest.json", "合规/ai_usage.json",
)


def existing_assets(root, final, master):
    rows = [rel for rel in CORE_INPUTS if os.path.exists(os.path.join(root, rel))]
    song = mv_utils.find_song(root)
    if song: rows.append(mv_utils.relpath(root, song))
    rows.extend(mv_utils.relpath(root, p) for p in sorted(glob.glob(os.path.join(root, "出图", "**", "*.png"), recursive=True)))
    rows.extend(mv_utils.relpath(root, p) for p in sorted(glob.glob(os.path.join(root, "出视频", "视频", "*.mp4"))))
    for path in (final, master):
        if path and os.path.exists(path): rows.append(mv_utils.relpath(root, path))
    return list(dict.fromkeys(rows))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument("--final", required=True)
    parser.add_argument("--master")
    parser.add_argument("--embed-c2pa", action="store_true")
    args = parser.parse_args()
    root = os.path.abspath(args.project_root)
    assets = existing_assets(root, args.final, args.master)
    payload = {
        "schema_version": 1, "kind": "mv_provenance", "generated_at": date.today().isoformat(),
        "assets": [{"path": rel, "sha256": mv_utils.content_hash(os.path.join(root, rel))} for rel in assets],
        "relationships": {"final": mv_utils.relpath(root, args.final),
                          "master": mv_utils.relpath(root, args.master) if args.master else None,
                          "ingredients": [rel for rel in assets if rel not in {mv_utils.relpath(root, args.final), mv_utils.relpath(root, args.master) if args.master else ""}]},
        "ai_usage": mv_utils.load_json(os.path.join(root, "合规", "ai_usage.json"), {}) or {},
        "c2pa": {"requested": bool(args.embed_c2pa), "tool_available": bool(shutil.which("c2patool")), "embedded": False},
    }
    out = os.path.join(root, "合规", "provenance.json")
    mv_utils.write_json(out, payload)
    c2pa_manifest = {"claim_generator": "anime-armory-mv", "title": os.path.basename(args.final),
                     "assertions": [{"label": "c2pa.actions", "data": {"actions": [{"action": "c2pa.created"}, {"action": "c2pa.edited"}]}}]}
    c2pa_path = os.path.join(root, "合规", "c2pa_manifest.json")
    mv_utils.write_json(c2pa_path, c2pa_manifest)
    if args.embed_c2pa:
        if not shutil.which("c2patool"):
            print("[err] --embed-c2pa requested but c2patool is unavailable", file=sys.stderr)
            return 1
        proc = subprocess.run(["c2patool", args.final, "-m", c2pa_path, "-o", args.final + ".c2pa.mp4"])
        if proc.returncode:
            return proc.returncode
        payload["c2pa"]["embedded"] = True
        payload["c2pa"]["output"] = mv_utils.relpath(root, args.final + ".c2pa.mp4")
        mv_utils.write_json(out, payload)
    print(f"[ok] provenance → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
