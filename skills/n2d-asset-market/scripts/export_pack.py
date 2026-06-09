#!/usr/bin/env python3
"""Compatibility wrapper for exporting character asset packs.

Preferred explicit form:
  python3 skills/n2d-asset-market/scripts/market.py export-character <作品根> --character-id CHAR_XXX

Short form kept for memory:
  python3 skills/n2d-asset-market/scripts/export_pack.py <作品根> CHAR_XXX
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


if __name__ == "__main__":
    if len(sys.argv) >= 3 and not sys.argv[2].startswith("-"):
        sys.argv = [sys.argv[0], "export-character", sys.argv[1], "--character-id", sys.argv[2], *sys.argv[3:]]
    else:
        sys.argv = [sys.argv[0], "export-character", *sys.argv[1:]]
    runpy.run_path(str(Path(__file__).with_name("market.py")), run_name="__main__")
