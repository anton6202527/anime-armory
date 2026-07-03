#!/usr/bin/env python3
"""Validate n2d machine artifacts against the lightweight schema registry."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from n2d_schema_registry import render_markdown, scan_artifacts, write_validation  # noqa: E402


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="validate n2d artifacts by schema registry")
    ap.add_argument("root")
    ap.add_argument("--strict-unknown", action="store_true", help="treat unknown artifact kind as block")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    payload = scan_artifacts(ns.root.rstrip("/"), strict_unknown=ns.strict_unknown)
    if ns.write:
        payload["outputs"] = write_validation(ns.root.rstrip("/"), payload)
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(payload))
    return 1 if payload.get("status") == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
