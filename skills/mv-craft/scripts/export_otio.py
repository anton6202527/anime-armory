#!/usr/bin/env python3
"""Export the MV timeline to a portable OpenTimelineIO JSON document."""
import argparse
import os
from datetime import date

import mv_utils


def rational(value, rate):
    return {"OTIO_SCHEMA": "RationalTime.1", "value": float(value) * rate, "rate": rate}


def time_range(duration, rate):
    return {"OTIO_SCHEMA": "TimeRange.1", "start_time": rational(0, rate), "duration": rational(duration, rate)}


def build(root, rate=24.0):
    timeline = mv_utils.load_json(os.path.join(root, "分镜", "timeline_manifest.json"), {}) or {}
    children = []
    for row in timeline.get("clips") or []:
        media = row.get("video_path") or ""
        children.append({
            "OTIO_SCHEMA": "Clip.2", "name": row.get("clip_id") or "clip",
            "source_range": time_range(float(row.get("duration") or 0), rate),
            "media_reference": {"OTIO_SCHEMA": "ExternalReference.1", "target_url": media,
                                "available_range": None, "metadata": {}},
            "metadata": {"mv": {"section": row.get("section"), "start": row.get("start"), "end": row.get("end"),
                                    "transition": row.get("transition")}},
        })
    return {
        "OTIO_SCHEMA": "Timeline.1", "name": timeline.get("title") or os.path.basename(root),
        "global_start_time": None, "metadata": {"mv": {"generated_at": date.today().isoformat()}},
        "tracks": {"OTIO_SCHEMA": "Stack.1", "name": "tracks", "source_range": None, "metadata": {},
                   "effects": [], "markers": [], "children": [
                       {"OTIO_SCHEMA": "Track.1", "name": "V1", "kind": "Video", "source_range": None,
                        "metadata": {}, "effects": [], "markers": [], "children": children}
                   ]},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument("--fps", type=float, default=24.0)
    args = parser.parse_args()
    root = os.path.abspath(args.project_root)
    out = os.path.join(root, "分镜", "timeline.otio")
    mv_utils.write_json(out, build(root, args.fps))
    print(f"[ok] OTIO → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
