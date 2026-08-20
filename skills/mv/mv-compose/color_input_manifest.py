#!/usr/bin/env python3
"""Build and enforce the per-input colour interpretation ledger for MV compose."""
import argparse
import json
import os
import subprocess
import sys
from datetime import date


HERE = os.path.dirname(os.path.abspath(__file__))
CRAFT = os.path.abspath(os.path.join(HERE, "..", "mv-craft", "scripts"))
if CRAFT not in sys.path:
    sys.path.insert(0, CRAFT)
import mv_utils


HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}
WIDE_PRIMARIES = {"bt2020", "smpte431", "smpte432"}


def probe_colour(path):
    proc = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=color_primaries,color_transfer,color_space,color_range,pix_fmt,width,height",
        "-of", "json", path,
    ], capture_output=True, text=True)
    if proc.returncode:
        return {}
    try:
        return ((json.loads(proc.stdout).get("streams") or [{}])[0])
    except (json.JSONDecodeError, IndexError):
        return {}


def classify(probe):
    primaries = str(probe.get("color_primaries") or "").lower()
    transfer = str(probe.get("color_transfer") or "").lower()
    matrix = str(probe.get("color_space") or "").lower()
    color_range = str(probe.get("color_range") or "").lower()
    if transfer in HDR_TRANSFERS or primaries in WIDE_PRIMARIES:
        return "unsupported_hdr_or_wide_gamut"
    if primaries == transfer == matrix == "bt709":
        if color_range in {"tv", "mpeg"}:
            return "declared_bt709_limited"
        if color_range in {"pc", "jpeg"}:
            return "declared_bt709_full"
        return "untagged"
    if (not primaries or not transfer or not matrix or not color_range
            or "unknown" in {primaries, transfer, matrix, color_range}):
        return "untagged"
    return "unsupported_non_bt709"


def transform_for(classification):
    """Return the exact ffmpeg input transform consumed by mv_compose.sh."""
    if classification == "declared_bt709_full":
        return (
            "scale=in_range=full:out_range=limited,"
            "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv"
        )
    if classification in {"declared_bt709_limited", "untagged"}:
        return "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv"
    return None


def timeline_inputs(root):
    timeline = mv_utils.load_json(os.path.join(root, "分镜", "timeline_manifest.json"), {}) or {}
    rows = []
    for clip in timeline.get("clips") or []:
        rel = str(clip.get("video_path") or "")
        if rel and rel not in rows:
            rows.append(rel)
    return rows


def build(root):
    rows = []
    for rel in timeline_inputs(root):
        full = os.path.join(root, rel)
        probed = probe_colour(full) if os.path.isfile(full) else {}
        classification = "missing" if not os.path.isfile(full) else classify(probed)
        rows.append({
            "path": rel,
            "sha256": mv_utils.content_hash(full),
            "probed": probed,
            "classification": classification,
            "interpretation": "bt709_limited" if classification == "declared_bt709_limited" else (
                "bt709_full" if classification == "declared_bt709_full" else None
            ),
            "ffmpeg_input_filter": transform_for(classification),
        })
    return rows


def valid_acceptance(existing, rows):
    acceptance = (existing or {}).get("untagged_acceptance") or {}
    if not (acceptance.get("accepted") and str(acceptance.get("reviewer") or "").strip()
            and str(acceptance.get("notes") or "").strip()):
        return False
    bound = acceptance.get("bound_inputs_sha256") or {}
    current = {row["path"]: row["sha256"] for row in rows if row["classification"] == "untagged"}
    return bool(current) and bound == current


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root")
    parser.add_argument("--accept-untagged-as-bt709", action="store_true")
    parser.add_argument("--reviewer")
    parser.add_argument("--notes")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    out = os.path.join(root, "生产数据", "color", "color_input_manifest.json")
    existing = mv_utils.load_json(out, {}) or {}
    rows = build(root)
    if args.accept_untagged_as_bt709:
        if not str(args.reviewer or "").strip() or not str(args.notes or "").strip():
            parser.error("接受无标签素材必须具名 reviewer 和 notes")
        unknown = {row["path"]: row["sha256"] for row in rows if row["classification"] == "untagged"}
        if not unknown:
            parser.error("当前没有无标签输入需要签收")
        acceptance = {
            "accepted": True, "interpret_as": "bt709", "reviewer": args.reviewer.strip(),
            "notes": args.notes.strip(), "date": date.today().isoformat(),
            "bound_inputs_sha256": unknown,
        }
    else:
        acceptance = existing.get("untagged_acceptance") if valid_acceptance(existing, rows) else None
    if acceptance:
        for row in rows:
            if row["classification"] == "untagged":
                row["interpretation"] = "bt709_limited_by_named_source_interpretation"
                row["ffmpeg_input_filter"] = transform_for("untagged")
    blocks = []
    if not rows:
        blocks.append("timeline_has_no_selected_video_inputs")
    for row in rows:
        if row["classification"] in {"missing", "unsupported_hdr_or_wide_gamut", "unsupported_non_bt709"}:
            blocks.append(f"{row['path']}:{row['classification']}")
        elif row["classification"] == "untagged" and not acceptance:
            blocks.append(f"{row['path']}:untagged_requires_named_interpretation")
    timeline_path = os.path.join(root, "分镜", "timeline_manifest.json")
    payload = {
        "schema_version": 2, "kind": "mv_color_input_manifest", "generated_at": date.today().isoformat(),
        "root_rel": ".",
        "output_space": "bt709_sdr_limited", "inputs": rows,
        "timeline_sha256": mv_utils.content_hash(timeline_path),
        "inputs_sha256": {row["path"]: row["sha256"] for row in rows},
        "untagged_acceptance": acceptance,
        "summary": {"hard_blocks": len(blocks), "blocks": blocks, "verdict": "block" if blocks else "ok"},
    }
    mv_utils.write_json(out, payload)
    print(f"[ok] colour input manifest → {out} ({payload['summary']['verdict']})")
    if blocks:
        print("[err] " + blocks[0], file=sys.stderr)
        if any("untagged" in block for block in blocks):
            print("[next] 人工确认来源确为 Rec.709 后用 --accept-untagged-as-bt709 --reviewer <name> --notes <依据>", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
