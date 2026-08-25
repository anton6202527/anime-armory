#!/usr/bin/env python3
"""Route Comic findings into deterministic repair, targeted review or hard boundary."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


DETERMINISTIC = {"missing_file", "sha_mismatch", "schema_invalid", "text_overflow", "filename_invalid"}
HARD = {"rights_unverified", "budget_expansion", "irreversible_publish", "final_acceptance"}


def classify(item: Mapping[str, Any]) -> str:
    code = str(item.get("code") or item.get("category") or "")
    if code in HARD: return "hard_boundary"
    if code in DETERMINISTIC or item.get("confidence") == "deterministic": return "deterministic_repair"
    if item.get("current_receipt_disposition") in {"accepted_intentional", "false_positive"}: return "receipt_bound_noop"
    return "targeted_review"


def triage(report: Mapping[str, Any]) -> dict[str, Any]:
    rows = []
    for finding in report.get("findings") or report.get("issues") or []:
        if isinstance(finding, Mapping): rows.append({**dict(finding), "route": classify(finding)})
    return {"schema_version": 1, "kind": "comic_finding_triage", "rows": rows, "counts": {route: sum(row["route"] == route for row in rows) for route in ("deterministic_repair", "targeted_review", "receipt_bound_noop", "hard_boundary")}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("report")
    args = parser.parse_args(argv); payload = json.loads(Path(args.report).read_text(encoding="utf-8")); print(json.dumps(triage(payload), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
