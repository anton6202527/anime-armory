#!/usr/bin/env python3
"""Record production-rights assertions for an MV project (not legal advice)."""
import argparse
import os
from datetime import date

import mv_utils


ALLOWED = ("owned", "public_domain", "licensed", "authorized", "cleared", "not_applicable")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument("--song", required=True, choices=ALLOWED)
    parser.add_argument("--visual-reference", required=True, choices=ALLOWED)
    parser.add_argument("--likeness", required=True, choices=ALLOWED)
    parser.add_argument("--brand", required=True, choices=ALLOWED)
    parser.add_argument("--location", required=True, choices=ALLOWED)
    parser.add_argument("--choreography", required=True, choices=ALLOWED)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    payload = {"schema_version": 1, "kind": "mv_rights_manifest", "date": date.today().isoformat(),
               "reviewer": args.reviewer, "notes": args.notes,
               "assertions": {"song": args.song, "visual_reference": args.visual_reference,
                              "likeness": args.likeness, "brand": args.brand,
                              "location": args.location, "choreography": args.choreography},
               "notice": "Production record only; platform and jurisdiction-specific review remains the publisher's responsibility."}
    root = os.path.abspath(args.project_root)
    out = os.path.join(root, "合规", "rights_manifest.json")
    mv_utils.write_json(out, payload)
    print(f"[ok] rights manifest → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
