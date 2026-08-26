#!/usr/bin/env python3
"""Run every self-contained production line in an isolated Python process.

The six lines deliberately vendor helpers with repeated flat import names.
Isolation here is part of the distribution contract: a test run must exercise
the same module boundary as a separately installed line, while still emitting
one aggregate machine result for repository-wide verification.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from time import monotonic


LINES = ("novel", "n2d", "comic", "song", "mv", "ad")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("lines", nargs="*", choices=LINES, default=list(LINES))
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--quiet", action="store_true", help="pass -q to pytest")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    selected = list(dict.fromkeys(args.lines or LINES))
    results = []
    started = monotonic()
    for line in selected:
        command = [sys.executable, "-m", "pytest"]
        if args.quiet:
            command.append("-q")
        command.append(f"skills/{line}")
        line_started = monotonic()
        completed = subprocess.run(command, cwd=root, check=False)
        results.append({
            "line": line,
            "returncode": completed.returncode,
            "passed": completed.returncode == 0,
            "elapsed_seconds": round(monotonic() - line_started, 3),
            "command": command,
        })
    payload = {
        "schema_version": 1,
        "kind": "isolated_skill_line_test_report",
        "complete": all(row["passed"] for row in results),
        "elapsed_seconds": round(monotonic() - started, 3),
        "results": results,
    }
    if args.json_out:
        target = args.json_out if args.json_out.is_absolute() else root / args.json_out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
