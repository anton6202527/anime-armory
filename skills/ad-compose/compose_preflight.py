#!/usr/bin/env python3
"""Small deterministic compose decisions shared by compose.sh and tests."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ENDCARD_TOKENS = ("end card", "endcard", "片尾", "品牌包装", "cta")


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def storyboard_has_endcard(root: Path) -> bool:
    sb = load(root / "脚本" / "storyboard.json", {}) or {}
    for shot in sb.get("shots") or sb.get("clips") or []:
        if not isinstance(shot, dict):
            continue
        text = " ".join(str(shot.get(k) or "") for k in ("section", "scene", "shot", "frame", "description")).lower()
        if any(token in text for token in ENDCARD_TOKENS):
            return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project_root")
    ap.add_argument("--should-append-endcard", action="store_true")
    ns = ap.parse_args(argv)
    if ns.should_append_endcard:
        return 1 if storyboard_has_endcard(Path(ns.project_root)) else 0
    print(json.dumps({"storyboard_has_endcard": storyboard_has_endcard(Path(ns.project_root))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
