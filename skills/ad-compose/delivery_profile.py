#!/usr/bin/env python3
"""Expose ad-craft delivery profile to shell without duplicating LUFS constants."""
import argparse
import os
import sys

CRAFT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ad-craft", "scripts"))
sys.path.insert(0, CRAFT)
import contract  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ns = ap.parse_args()
    spec = ns.spec if ns.spec in contract.DELIVERY_PROFILE else "平台默认"
    row = contract.delivery_profile(spec)
    print(f"{row['loudness_lufs']}\t{row['true_peak_db']}")


if __name__ == "__main__":
    main()
