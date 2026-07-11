#!/usr/bin/env python3
"""Build/refresh the canonical n2d OpenTimelineIO editorial timeline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

N2D_LIB = Path(__file__).resolve().parents[2] / "n2d" / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))
from editorial_timeline import build_editorial_timeline, write_editorial_timeline  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="write n2d OpenTimelineIO timeline")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    payload = build_editorial_timeline(root, ns.episode)
    if ns.write:
        payload["outputs"] = write_editorial_timeline(root, payload)
    if ns.json:
        print(json.dumps({k: v for k, v in payload.items() if k != "otio"}, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{payload['episode']} OTIO: {payload['status']} · phase={payload['phase']} · {payload.get('duration_sec')}s")
    return 0 if payload.get("status") == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
