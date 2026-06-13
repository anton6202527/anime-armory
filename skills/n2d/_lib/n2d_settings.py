#!/usr/bin/env python3
"""Backward-compatible import path for n2d settings helpers.

New code should import `settings`; existing n2d scripts can keep importing
`n2d_settings`.
"""
try:
    from settings import *  # noqa: F401,F403
except ImportError:  # pragma: no cover - package-style import fallback
    from .settings import *  # noqa: F401,F403
