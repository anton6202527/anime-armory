#!/usr/bin/env python3
"""Validate n2d industry benchmark provenance schema."""
from __future__ import annotations

import argparse
import json
import os
import sys

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from n2d_thresholds import BENCHMARK_REFERENCE_FILE, validate_retention_benchmark_schema  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="validate n2d retention benchmark provenance schema")
    ap.add_argument("path", nargs="?", default=BENCHMARK_REFERENCE_FILE)
    ns = ap.parse_args(argv)
    with open(ns.path, encoding="utf-8") as fh:
        data = json.load(fh)
    errors = validate_retention_benchmark_schema(data)
    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        return 1
    print(f"OK {ns.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
