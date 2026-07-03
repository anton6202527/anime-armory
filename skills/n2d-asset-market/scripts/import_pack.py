#!/usr/bin/env python3
"""Compatibility wrapper for importing character asset packs.

Preferred explicit form:
  python3 skills/n2d-asset-market/scripts/market.py import-character <作品根> <资产包> --as-id CHAR_YYY --as-name 新角色
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


if __name__ == "__main__":
    sys.argv = [sys.argv[0], "import-character", *sys.argv[1:]]
    runpy.run_path(str(Path(__file__).with_name("market.py")), run_name="__main__")
