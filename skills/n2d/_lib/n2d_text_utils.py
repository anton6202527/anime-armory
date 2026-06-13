#!/usr/bin/env python3
"""Backward-compatible import path for shared text utilities."""
try:
    from text_utils import *  # noqa: F401,F403
except ImportError:  # pragma: no cover - package-style import fallback
    from .text_utils import *  # noqa: F401,F403
