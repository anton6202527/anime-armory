#!/usr/bin/env python3
"""Generate and check post-generation script supervisor take logs for n2d."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


KIND = "n2d_script_supervisor_log"
CHECK_KIND = "n2d_script_supervisor_log_check"
VERSION = 1


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def episode_label(value: str) -> str:
    value = str(value or "").strip()
    if value.startswith("第") and value.endswith("集"):
        return value
    return f"第{value}集"


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    write_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def log_path(root: Path, episode: str) -> Path:
    return production_dir(root) / f"script_supervisor_log_{episode}.jsonl"


def summary_path(root: Path, episode: str) -> Path:
    return production_dir(root) / f"script_supervisor_log_{episode}.json"


def check_path(root: Path, episode: str) -> Path:
    return production_dir(root) / f"script_supervisor_log_check_{episode}.json"


def clip_id(value: Any, idx: int) -> str:
    raw = str(value or "").strip()
    m = re.search(r"(?:Clip|clip)[_\s-]?(\d+)", raw)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    m = re.search(r"(\d+)", raw)
    if m and not raw.startswith("CHAR"):
        return f"Clip_{int(m.group(1)):02d}"
    return raw or f"Clip_{idx:02d}"


def storyboard_clips(root: Path, episode: str) -> List[Mapping[str, Any]]:
    data = load_json(root / "脚本" / episode / "storyboard.json")
    clips = data.get("clips") if isinstance(data, Mapping) else []
    return [c for c in clips or [] if isinstance(c, Mapping)]


def video_files(root: Path, episode: str) -> List[Path]:
    base = root / "出视频" / episode / "视频"
    if not base.is_dir():
        return []
    return [p for p in sorted(base.rglob("*.mp4")) if p.is_file()]


def group_videos(paths: Iterable[Path]) -> Dict[str, List[Path]]:
    grouped: Dict[str, List[Path]] = {}
    for idx, path in enumerate(paths, 1):
        cid = clip_id(path.stem, idx)
        grouped.setdefault(cid, []).append(path)
    return grouped


def ffprobe_duration(path: Path) -> Optional[float]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    try:
        return round(float(proc.stdout.strip()), 3)
    except Exception:
        return None


def _continuity_summary(clip: Mapping[str, Any]) -> Dict[str, str]:
    continuity = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    return {
        "start_state": str(continuity.get("start_state") or ""),
        "end_state": str(continuity.get("end_state") or ""),
        "transition": str(continuity.get("transition") or ""),
        "eyeline": str(continuity.get("eyeline") or continuity.get("screen_direction") or ""),
    }


def build_rows(root: Path, episode: str) -> List[Dict[str, Any]]:
    root = root.resolve()
    episode = episode_label(episode)
    clips = storyboard_clips(root, episode)
    videos = group_videos(video_files(root, episode))
    rows: List[Dict[str, Any]] = []
    if not clips:
        for idx, path in enumerate(video_files(root, episode), 1):
            cid = clip_id(path.stem, idx)
            rows.append({
                "kind": KIND,
                "version": VERSION,
                "episode": episode,
                "clip_id": cid,
                "take_id": path.stem,
                "asset": relpath(root, path),
                "duration_sec": ffprobe_duration(path),
                "screen_direction": "",
                "continuity_expected": {},
                "deviation_from_storyboard": "storyboard_missing",
                "director_note": "自动从视频目录补行；需补 storyboard 对照。",
                "accepted_take": True,
                "logged_at": now_iso(),
            })
        return rows
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip.get("clip_id") or clip.get("id") or clip.get("label"), idx)
        takes = videos.get(cid, [])
        continuity = _continuity_summary(clip)
        if not takes:
            rows.append({
                "kind": KIND,
                "version": VERSION,
                "episode": episode,
                "clip_id": cid,
                "take_id": "",
                "asset": "",
                "duration_sec": None,
                "screen_direction": continuity.get("eyeline") or "",
                "continuity_expected": continuity,
                "deviation_from_storyboard": "missing_video_take",
                "director_note": "未找到本 Clip MP4；回 n2d-video 或 batch 重跑。",
                "accepted_take": False,
                "logged_at": now_iso(),
            })
            continue
        for take_idx, path in enumerate(takes, 1):
            accepted = take_idx == len(takes)
            rows.append({
                "kind": KIND,
                "version": VERSION,
                "episode": episode,
                "clip_id": cid,
                "take_id": path.stem,
                "asset": relpath(root, path),
                "duration_sec": ffprobe_duration(path),
                "screen_direction": continuity.get("eyeline") or "",
                "continuity_expected": continuity,
                "deviation_from_storyboard": "" if accepted else "superseded_take",
                "director_note": "自动接受最新 take；如人审改判，直接改本 JSONL 行并保留原因。",
                "accepted_take": accepted,
                "logged_at": now_iso(),
            })
    return rows


def write_log(root: Path, episode: str, rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    episode = episode_label(episode)
    path = log_path(root, episode)
    text = "".join(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    write_atomic(path, text)
    summary = {
        "kind": KIND,
        "version": VERSION,
        "episode": episode,
        "generated_at": now_iso(),
        "log_path": relpath(root, path),
        "summary": {
            "rows": len(rows),
            "clips": len({row.get("clip_id") for row in rows}),
            "accepted_takes": sum(1 for row in rows if row.get("accepted_take") is True),
            "missing_takes": sum(1 for row in rows if row.get("deviation_from_storyboard") == "missing_video_take"),
        },
    }
    write_json(summary_path(root, episode), summary)
    return summary


def load_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            rows.append({"_invalid": raw[:160]})
            continue
        rows.append(obj if isinstance(obj, dict) else {"_invalid": raw[:160]})
    return rows


def check_log(root: Path, episode: str, *, write_missing: bool = False) -> Dict[str, Any]:
    episode = episode_label(episode)
    if write_missing and not log_path(root, episode).exists():
        rows = build_rows(root, episode)
        write_log(root, episode, rows)
    rows = load_rows(log_path(root, episode))
    clips = storyboard_clips(root, episode)
    expected = {clip_id(c.get("clip_id") or c.get("id") or c.get("label"), i) for i, c in enumerate(clips, 1)}
    accepted = {str(row.get("clip_id")) for row in rows if row.get("accepted_take") is True}
    findings: List[Dict[str, Any]] = []
    if not rows:
        findings.append({"severity": "block", "code": "missing_script_supervisor_log", "message": "缺场记 JSONL。"})
    for row in rows:
        if row.get("_invalid"):
            findings.append({"severity": "block", "code": "invalid_jsonl_row", "message": str(row.get("_invalid"))})
            continue
        if row.get("accepted_take") is True:
            asset = str(row.get("asset") or "")
            asset_path = root / asset if asset and not Path(asset).is_absolute() else Path(asset)
            if not asset or not asset_path.is_file():
                findings.append({"severity": "block", "code": "accepted_take_asset_missing", "clip_id": row.get("clip_id"), "message": "accepted_take 缺有效 MP4 asset。"})
                continue
            duration = ffprobe_duration(asset_path)
            if duration is None or duration <= 0:
                findings.append({
                    "severity": "block",
                    "code": "accepted_take_media_invalid",
                    "clip_id": row.get("clip_id"),
                    "message": "accepted_take MP4 无法被 ffprobe 读取有效时长。",
                    "asset": asset,
                })
    missing = sorted(expected - accepted)
    for cid in missing:
        findings.append({"severity": "block", "code": "clip_without_accepted_take", "clip_id": cid, "message": f"{cid} 缺 accepted_take。"})
    payload = {
        "kind": CHECK_KIND,
        "version": VERSION,
        "episode": episode,
        "generated_at": now_iso(),
        "status": "block" if findings else "pass",
        "log_path": relpath(root, log_path(root, episode)),
        "summary": {
            "rows": len(rows),
            "expected_clips": len(expected),
            "accepted_clips": len(accepted),
            "block": len(findings),
        },
        "findings": findings,
    }
    write_json(check_path(root, episode), payload)
    payload["check_path"] = relpath(root, check_path(root, episode))
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d script supervisor take log")
    ap.add_argument("root")
    ap.add_argument("episode")
    sub = ap.add_subparsers(dest="command", required=True)
    p_build = sub.add_parser("build")
    p_build.add_argument("--write", action="store_true")
    p_build.add_argument("--json", action="store_true")
    p_check = sub.add_parser("check")
    p_check.add_argument("--write-missing", action="store_true")
    p_check.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    episode = episode_label(ns.episode)
    if ns.command == "build":
        rows = build_rows(root, episode)
        payload = write_log(root, episode, rows) if ns.write else {
            "kind": KIND,
            "episode": episode,
            "summary": {"rows": len(rows), "accepted_takes": sum(1 for r in rows if r.get("accepted_take") is True)},
            "rows": rows,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else f"{episode} script supervisor log rows={len(rows)}")
        return 0
    payload = check_log(root, episode, write_missing=ns.write_missing)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else f"{episode} script supervisor log: {payload['status']}")
    return 0 if payload.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
