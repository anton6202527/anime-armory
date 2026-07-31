#!/usr/bin/env python3
"""Expose ad-craft delivery profile to shell without duplicating LUFS constants."""
import argparse
import json
import os
import sys

CRAFT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ad-craft", "scripts"))
sys.path.insert(0, CRAFT)
import contract  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--project-root", default=None)
    ns = ap.parse_args()
    spec = ns.spec if ns.spec in contract.DELIVERY_PROFILE else "平台默认"
    custom = None
    if spec == "自定义" and ns.project_root:
        try:
            brief = json.loads(open(os.path.join(ns.project_root, "需求", "brief.json"), encoding="utf-8").read())
            custom = (brief.get("delivery_profiles") or {}).get("自定义")
        except Exception:
            custom = None
    try:
        row = contract.resolve_delivery_profile(spec, custom)
    except ValueError as exc:
        ap.error(str(exc))
    print(f"{row['loudness_lufs']}\t{row['true_peak_db']}")


if __name__ == "__main__":
    main()
