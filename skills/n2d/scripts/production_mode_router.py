#!/usr/bin/env python3
"""CLI for the n2d evidence-led production-mode recommendation."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Sequence

N2D_LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))
# This CLI intentionally shares its filename with the reusable `_lib` module.
# Load the core under a private module name so test/CLI sys.path ordering can
# never turn `import production_mode_router` into a circular self-import.
_SPEC = importlib.util.spec_from_file_location(
    "n2d_production_mode_router_core", N2D_LIB / "production_mode_router.py",
)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise ImportError("cannot load n2d production mode router core")
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)
for _NAME in dir(_CORE):
    if not _NAME.startswith("_"):
        globals().setdefault(_NAME, getattr(_CORE, _NAME))


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="recommend n2d production mode from episode evidence")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    payload = build_route(root, ns.episode)
    if ns.write:
        payload["outputs"] = write_route(root, payload)
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        decision = payload["decision"]
        print(f"{payload['episode']} 制作模式：{decision['selected_mode']} → 推荐 {decision['recommended_mode']} ({payload['status']})")
    # Advisory only: a mismatch must never become an opaque heuristic blocker.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
