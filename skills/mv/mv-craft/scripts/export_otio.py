#!/usr/bin/env python3
"""Export an editable, hash-bound OpenTimelineIO MV timeline.

OTIO is an editorial interchange document, not a rendered movie.  The export
therefore carries the locked song on A1, selected/missing picture references on
V1, musical-section and seam markers, and a sidecar that proves which manifest
and media the document describes.  No OTIO Python package is required.
"""
import argparse
import os
from datetime import date

import mv_utils


def rational(seconds, rate):
    return {
        "OTIO_SCHEMA": "RationalTime.1",
        "value": round(float(seconds) * float(rate), 6),
        "rate": float(rate),
    }


def time_range(start, duration, rate):
    return {
        "OTIO_SCHEMA": "TimeRange.1",
        "start_time": rational(start, rate),
        "duration": rational(duration, rate),
    }


def media_reference(root, otio_dir, rel, duration, rate):
    full = os.path.join(root, rel) if rel else ""
    metadata = {"mv": {"project_relative_path": rel or "", "sha256": mv_utils.content_hash(full)}}
    if full and os.path.isfile(full):
        target = os.path.relpath(full, otio_dir).replace(os.sep, "/")
        available = mv_utils.audio_duration(full)
        if available is None:
            probed = mv_utils.ffprobe_json(full, "-show_entries", "format=duration")
            try:
                available = float((probed.get("format") or {}).get("duration"))
            except (TypeError, ValueError):
                available = None
        return {
            "OTIO_SCHEMA": "ExternalReference.1",
            "name": os.path.basename(full),
            "metadata": metadata,
            "target_url": target,
            "available_range": time_range(0, max(float(duration), float(available or 0)), rate),
            "available_image_bounds": None,
        }
    metadata["mv"]["missing"] = True
    return {
        "OTIO_SCHEMA": "MissingReference.1",
        "name": os.path.basename(rel) if rel else "missing_media",
        "metadata": metadata,
        "available_range": None,
        "available_image_bounds": None,
    }


def clip_item(root, otio_dir, name, rel, duration, rate, metadata):
    ref = media_reference(root, otio_dir, rel, duration, rate)
    return {
        "OTIO_SCHEMA": "Clip.2",
        "name": name,
        "metadata": {"mv": metadata},
        "source_range": time_range(0, duration, rate),
        "effects": [],
        "markers": [],
        "enabled": True,
        "media_references": {"DEFAULT_MEDIA": ref},
        "active_media_reference_key": "DEFAULT_MEDIA",
    }


def marker(name, start, duration, rate, color, metadata):
    return {
        "OTIO_SCHEMA": "Marker.2",
        "name": str(name),
        "metadata": {"mv": metadata},
        "marked_range": time_range(start, max(duration, 1.0 / rate), rate),
        "color": color,
    }


def transition_item(name, duration, rate, seam):
    half = max(1.0 / rate, float(duration) / 2.0)
    return {
        "OTIO_SCHEMA": "Transition.1",
        "name": name,
        "metadata": {"mv": {"seam_contract": seam}},
        "transition_type": "SMPTE_Dissolve",
        "in_offset": rational(half, rate),
        "out_offset": rational(half, rate),
    }


def track(name, kind, children, markers=None):
    return {
        "OTIO_SCHEMA": "Track.1",
        "name": name,
        "metadata": {"mv": {"track_role": name}},
        "source_range": None,
        "effects": [],
        "markers": list(markers or []),
        "enabled": True,
        "children": children,
        "kind": kind,
    }


def build_bundle(root, rate=None):
    timeline_path = os.path.join(root, "分镜", "timeline_manifest.json")
    timeline = mv_utils.load_json(timeline_path, {}) or {}
    beatgrid_path = os.path.join(root, "节拍", "beatgrid.json")
    beatgrid = mv_utils.load_json(beatgrid_path, {}) or {}
    rate = float(rate or timeline.get("rate") or 24.0)
    otio_dir = os.path.join(root, "分镜")
    video_children = []
    seam_markers = []
    media_paths = []
    missing_media = []
    rows = timeline.get("clips") or []
    for index, row in enumerate(rows):
        duration = float(row.get("duration") or 0)
        rel = str(row.get("video_path") or "")
        seam = row.get("seam_contract") or {}
        item = clip_item(
            root, otio_dir, row.get("clip_id") or f"Clip_{index + 1:03d}", rel,
            duration, rate,
            {
                "section": row.get("section"),
                "timeline_start": row.get("start"),
                "timeline_end": row.get("end"),
                "transition": row.get("transition"),
                "speed_mode": row.get("speed_mode"),
                "seam_contract": seam,
            },
        )
        video_children.append(item)
        if rel:
            media_paths.append(rel)
            if not os.path.isfile(os.path.join(root, rel)):
                missing_media.append(rel)
        if seam.get("transition_type") == "dissolve":
            seconds = float(seam.get("duration_sec") or 8.0 / rate)
            video_children.append(transition_item(f"{row.get('clip_id')}_dissolve", seconds, rate, seam))
        if index < len(rows) - 1:
            seam_markers.append(marker(
                f"SEAM {row.get('clip_id')} → {rows[index + 1].get('clip_id')}",
                float(row.get("end") or 0), 1.0 / rate, rate, "YELLOW",
                {"kind": "seam", "contract": seam},
            ))

    section_markers = [
        marker(
            f"SECTION {row.get('section') or row.get('name') or 'section'}",
            float(row.get("start") or 0),
            max(1.0 / rate, float(row.get("end") or 0) - float(row.get("start") or 0)),
            rate, "BLUE", {"kind": "musical_section", "source": row.get("source")},
        )
        for row in (beatgrid.get("sections") or []) if isinstance(row, dict)
    ]

    total_duration = sum(float(row.get("duration") or 0) for row in rows)
    song_rel = str(timeline.get("song_path") or "")
    song_duration = mv_utils.audio_duration(os.path.join(root, song_rel)) if song_rel else None
    audio_item = clip_item(
        root, otio_dir, "MASTER_SONG", song_rel, float(song_duration or total_duration), rate,
        {"track_role": "A1 Master Song", "policy": timeline.get("audio_policy")},
    )
    if song_rel:
        media_paths.append(song_rel)
        if not os.path.isfile(os.path.join(root, song_rel)):
            missing_media.append(song_rel)

    payload = {
        "OTIO_SCHEMA": "Timeline.1",
        "name": timeline.get("title") or os.path.basename(root),
        "global_start_time": None,
        "metadata": {
            "mv": {
                "generated_at": date.today().isoformat(),
                "timeline_edit_sha256": mv_utils.timeline_edit_hash(timeline),
                "source_clip_plan_sha256": timeline.get("source_clip_plan_sha256"),
            }
        },
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "name": "tracks",
            "source_range": None,
            "metadata": {},
            "effects": [],
            "markers": section_markers,
            "children": [
                track("V1 Picture", "Video", video_children, seam_markers),
                track("A1 Master Song", "Audio", [audio_item]),
            ],
        },
    }
    sidecar = {
        "schema_version": 2,
        "kind": "mv_otio_export_receipt",
        "generated_at": date.today().isoformat(),
        "rate": rate,
        "timeline_edit_sha256": mv_utils.timeline_edit_hash(timeline),
        "inputs_sha256": {
            "分镜/timeline_manifest.json": mv_utils.content_hash(timeline_path),
            "节拍/beatgrid.json": mv_utils.content_hash(beatgrid_path),
        },
        "media_sha256": {
            rel: mv_utils.content_hash(os.path.join(root, rel))
            for rel in dict.fromkeys(media_paths) if os.path.isfile(os.path.join(root, rel))
        },
        "missing_media": list(dict.fromkeys(missing_media)),
        "tracks": {"video": 1, "audio": 1},
        "markers": {"sections": len(section_markers), "seams": len(seam_markers)},
    }
    return payload, sidecar


def build(root, rate=24.0):
    """Compatibility wrapper used by production_pack and tests."""
    return build_bundle(root, rate)[0]


def write_export(root, rate=None):
    payload, sidecar = build_bundle(root, rate)
    out = os.path.join(root, "分镜", "timeline.otio")
    receipt = os.path.join(root, "生产数据", "otio", "otio_receipt.json")
    mv_utils.write_json(out, payload)
    sidecar["otio_sha256"] = mv_utils.content_hash(out)
    mv_utils.write_json(receipt, sidecar)
    return out, receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument("--fps", type=float)
    args = parser.parse_args()
    root = os.path.abspath(args.project_root)
    out, receipt = write_export(root, args.fps)
    print(f"[ok] OTIO → {out}")
    print(f"[ok] OTIO receipt → {receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
