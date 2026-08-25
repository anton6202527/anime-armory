#!/usr/bin/env python3
"""Deterministic n2d color-management contract and master probe."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


KIND = "n2d_color_pipeline_contract"
REPORT_KIND = "n2d_color_pipeline_report"
VERSION = 1


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def contract_path(root: str | Path) -> Path:
    return Path(root) / "设定库" / "color_pipeline.json"


def report_path(root: str | Path, episode: str) -> Path:
    return Path(root) / "生产数据" / f"color_pipeline_{episode}.json"


def default_contract() -> Dict[str, Any]:
    return {
        "kind": KIND,
        "version": VERSION,
        "profile": "rec709_sdr",
        "management_mode": "ffmpeg_tagged_rec709",
        "source_policy": "probe_and_normalize_before_master",
        "working_space": "Rec.709 display-referred",
        "output": {
            "color_primaries": "bt709",
            "color_transfer": "bt709",
            "color_space": "bt709",
            "color_range": "tv",
            "pixel_format": "yuv420p",
        },
        "ocio": {"enabled": False, "config": "", "display": "", "view": ""},
        "status": "confirmed_default",
        "note": "Change only with an explicit delivery/mastering requirement; version the contract when changed.",
    }


def load_contract(root: str | Path) -> Dict[str, Any]:
    try:
        data = json.loads(contract_path(root).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_missing(root: str | Path) -> Path:
    path = contract_path(root)
    if path.is_file():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(default_contract(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def output_tags(contract: Mapping[str, Any]) -> Dict[str, str]:
    output = contract.get("output") if isinstance(contract.get("output"), Mapping) else {}
    return {
        "color_primaries": str(output.get("color_primaries") or "bt709"),
        "color_transfer": str(output.get("color_transfer") or "bt709"),
        "color_space": str(output.get("color_space") or "bt709"),
        "color_range": str(output.get("color_range") or "tv"),
        "pixel_format": str(output.get("pixel_format") or "yuv420p"),
    }


def ffmpeg_output_args(contract: Mapping[str, Any]) -> list[str]:
    tags = output_tags(contract)
    return [
        "-color_primaries", tags["color_primaries"],
        "-color_trc", tags["color_transfer"],
        "-colorspace", tags["color_space"],
        "-color_range", tags["color_range"],
        "-pix_fmt", tags["pixel_format"],
    ]


def find_master(root: str | Path, episode: str) -> Optional[Path]:
    base = Path(root) / "合成" / episode
    candidates = [
        path for path in base.glob("成片_*.mp4") if path.is_file()
        and not any(token in path.name for token in (".tmp", "_proxy", "_backup", "loudnorm"))
    ] if base.is_dir() else []
    return max(candidates, key=lambda path: path.stat().st_mtime_ns) if candidates else None


def probe_tags(path: Path, runner=subprocess.run) -> Dict[str, str]:
    try:
        proc = runner([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=pix_fmt,color_space,color_transfer,color_primaries,color_range",
            "-of", "json", str(path),
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        data = json.loads(proc.stdout or "{}") if proc.returncode == 0 else {}
    except (OSError, ValueError):
        return {}
    streams = data.get("streams") if isinstance(data, dict) else []
    row = streams[0] if isinstance(streams, list) and streams and isinstance(streams[0], dict) else {}
    return {key: str(row.get(key) or "") for key in (
        "pix_fmt", "color_space", "color_transfer", "color_primaries", "color_range"
    )}


def analyze(root: str | Path, episode: str, *, runner=subprocess.run) -> Dict[str, Any]:
    root_path = Path(root)
    contract = load_contract(root_path)
    issues: list[Dict[str, str]] = []
    if contract.get("kind") != KIND or int(contract.get("version") or 0) != VERSION:
        issues.append({"severity": "block", "code": "color_contract_missing_or_invalid", "message": "missing/invalid 设定库/color_pipeline.json"})
    expected = output_tags(contract or default_contract())
    master = find_master(root_path, episode)
    actual = probe_tags(master, runner=runner) if master else {}
    if master:
        field_map = {
            "pixel_format": "pix_fmt", "color_space": "color_space", "color_transfer": "color_transfer",
            "color_primaries": "color_primaries", "color_range": "color_range",
        }
        for expected_key, actual_key in field_map.items():
            wanted, got = expected[expected_key], actual.get(actual_key, "")
            if not got or got in {"unknown", "unspecified", "reserved"}:
                issues.append({"severity": "block", "code": f"{actual_key}_missing", "message": f"master lacks {actual_key}; expected {wanted}"})
            elif got != wanted:
                issues.append({"severity": "block", "code": f"{actual_key}_mismatch", "message": f"master {actual_key}={got}; expected {wanted}"})
    status = "block" if any(row["severity"] == "block" for row in issues) else "pass" if master else "pending_master"
    return {
        "kind": REPORT_KIND,
        "version": VERSION,
        "root": str(root_path),
        "episode": episode,
        "generated_at": now_iso(),
        "status": status,
        "contract": str(contract_path(root_path).relative_to(root_path)),
        "profile": str((contract or {}).get("profile") or ""),
        "master": str(master.relative_to(root_path)) if master else "",
        "expected": expected,
        "actual": actual,
        "issues": issues,
    }


def write_report(root: str | Path, episode: str, payload: Mapping[str, Any]) -> Path:
    path = report_path(root, episode)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write-missing", action="store_true")
    ap.add_argument("--print-tags", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    if ns.write_missing:
        write_missing(ns.root)
    contract = load_contract(ns.root) or default_contract()
    if ns.print_tags:
        tags = output_tags(contract)
        print(" ".join(tags[key] for key in ("color_primaries", "color_transfer", "color_space", "color_range", "pixel_format")))
        return 0
    payload = analyze(ns.root, ns.episode)
    payload["report"] = str(write_report(ns.root, ns.episode, payload))
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else f"{payload['status']} {payload['report']}")
    return 1 if payload["status"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
