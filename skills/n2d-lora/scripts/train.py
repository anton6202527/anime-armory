#!/usr/bin/env python3
"""Compatibility wrapper for `lora.py train-job`."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


if __name__ == "__main__":
    sys.argv = [sys.argv[0], "train-job", *sys.argv[1:]]
    runpy.run_path(str(Path(__file__).with_name("lora.py")), run_name="__main__")
