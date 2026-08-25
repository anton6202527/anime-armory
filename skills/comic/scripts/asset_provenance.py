#!/usr/bin/env python3
"""Record/verify Comic asset provenance without claiming a C2PA signature."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


COMIC_LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(COMIC_LIB) not in sys.path: sys.path.insert(0, str(COMIC_LIB))
from provenance import append_event, binding, load_events, validate_chain, write_c2pa_sidecar  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("command", choices=("append", "verify", "sidecar")); parser.add_argument("project_root"); parser.add_argument("asset", nargs="?", default="")
    parser.add_argument("--action", default=""); parser.add_argument("--model", default=""); parser.add_argument("--model-version", default=""); parser.add_argument("--channel", default=""); parser.add_argument("--human-contribution", default=""); parser.add_argument("--rights-basis", default="")
    args = parser.parse_args(argv); root = Path(args.project_root).expanduser().resolve(); asset = (root / args.asset).resolve() if args.asset else root
    try:
        if args.command == "append": result = append_event(root, asset, action=args.action, model=args.model, model_version=args.model_version, channel=args.channel, human_contribution=args.human_contribution, rights_basis=args.rights_basis)
        elif args.command == "sidecar": result = {"path": str(write_c2pa_sidecar(root, asset)), "c2pa_status": "not_signed"}
        else:
            events = load_events(root); errors = validate_chain(events); result = {"events": len(events), "errors": errors, "binding": binding(root, [])}
    except ValueError as exc: print(f"[err] {exc}", file=sys.stderr); return 2
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 1 if result.get("errors") else 0


if __name__ == "__main__": raise SystemExit(main())
