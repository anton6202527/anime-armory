#!/usr/bin/env python3
"""Check or scaffold first-episode pilot acceptance evidence for n2d."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


VERSION = 1
REQUIRED_COVERAGE = {"face", "scene", "action", "lipsync", "seam", "routing"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def out_path(root: Path, episode: str) -> Path:
    return root / "生产数据" / f"pilot_acceptance_{episode}.json"


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def template(root: Path, episode: str) -> Dict[str, Any]:
    return {
        "kind": "n2d_pilot_acceptance",
        "version": VERSION,
        "episode": episode,
        "status": "draft",
        "generated_at": now_iso(),
        "clips": [
            {"clip": "EP01_CLIP01", "why": "主角脸与主场景", "result": "todo"},
            {"clip": "EP01_CLIP02", "why": "动作/口型/接缝", "result": "todo"},
        ],
        "coverage": ["face", "scene", "action", "lipsync", "seam", "routing"],
        "checks": {
            "face": "todo",
            "scene": "todo",
            "action": "todo",
            "lipsync": "todo",
            "seam": "todo",
            "routing": "todo",
        },
        "notes": "首集放量前先打 2-3 个代表镜头；全部 result/checks 改为 pass 后，status 改为 accepted。",
    }


def write_template(root: Path, episode: str, *, force: bool = False) -> Path:
    path = out_path(root, episode)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return path
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(template(root, episode), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def check(root: Path, episode: str) -> Dict[str, Any]:
    path = out_path(root, episode)
    data = load_json(path)
    if not isinstance(data, dict):
        return {"kind": "n2d_pilot_check", "version": VERSION, "episode": episode, "status": "blocked", "path": str(path), "issues": ["missing pilot acceptance"]}
    issues = []
    status = str(data.get("status") or "").strip().lower()
    if status not in {"accepted", "pass", "green"}:
        issues.append(f"status={status or 'unset'}")
    clips = data.get("clips") if isinstance(data.get("clips"), list) else []
    if len(clips) < 2:
        issues.append("clips<2")
    coverage = set(str(x).strip().lower() for x in (data.get("coverage") or []))
    missing = sorted(REQUIRED_COVERAGE - coverage)
    if missing:
        issues.append(f"missing coverage: {', '.join(missing)}")
    checks = data.get("checks") if isinstance(data.get("checks"), Mapping) else {}
    bad_checks = [k for k in sorted(REQUIRED_COVERAGE) if str(checks.get(k) or "").strip().lower() not in {"pass", "ok", "accepted"}]
    if bad_checks:
        issues.append(f"checks not pass: {', '.join(bad_checks)}")
    return {
        "kind": "n2d_pilot_check",
        "version": VERSION,
        "episode": episode,
        "status": "blocked" if issues else "pass",
        "path": str(path),
        "issues": issues,
    }


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="check/scaffold n2d pilot acceptance")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scaffold")
    p.add_argument("root")
    p.add_argument("episode")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("check")
    p.add_argument("root")
    p.add_argument("episode")
    p.add_argument("--write-missing", action="store_true")
    p.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    if ns.cmd == "scaffold":
        path = write_template(root, ns.episode, force=ns.force)
        print(str(path))
        return 0
    if ns.write_missing and not out_path(root, ns.episode).exists():
        write_template(root, ns.episode)
    payload = check(root, ns.episode)
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("pilot ok" if payload["status"] == "pass" else "\n".join(payload.get("issues") or ["pilot blocked"]))
    return 2 if payload["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
