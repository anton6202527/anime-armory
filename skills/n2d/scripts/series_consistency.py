#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

_LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import series_consistency as core  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="n2d 剧级字幕/人名/语域/响度一致性合同")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--phase", choices=("script", "full"), default="full")
    ap.add_argument("--write-missing", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    if ns.write_missing:
        core.write_missing(ns.root)
    issues = core.validate(ns.root, ns.episode, phase=ns.phase)
    result = {"kind": "n2d_series_consistency_check", "required": core.required(ns.root),
              "status": "block" if issues else "pass", "path": str(core.path(ns.root)), "issues": issues}
    print(json.dumps(result, ensure_ascii=False, indent=2) if ns.json else f"{result['status']}: {result['path']}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
