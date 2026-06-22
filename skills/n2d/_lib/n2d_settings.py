#!/usr/bin/env python3
"""Backward-compatible import path for n2d settings helpers.

New code should import `settings`; existing n2d scripts can keep importing
`n2d_settings`.
"""
try:
    from .settings import *  # noqa: F401,F403
except ImportError:  # pragma: no cover - script-style import fallback
    import importlib.util
    import os
    import sys

    _settings_path = os.path.join(os.path.dirname(__file__), "settings.py")
    _spec = importlib.util.spec_from_file_location("_n2d_local_settings", _settings_path)
    if _spec is None or _spec.loader is None:
        raise
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_spec.name] = _module
    _spec.loader.exec_module(_module)
    for _name in dir(_module):
        if not _name.startswith("_"):
            globals()[_name] = getattr(_module, _name)
