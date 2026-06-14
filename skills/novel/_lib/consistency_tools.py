#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stable loader for novel-line deterministic consistency tools."""

import importlib
import os
import sys
from contextlib import contextmanager


_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))


@contextmanager
def _prepend_path(path):
    added = path not in sys.path
    if added:
        sys.path.insert(0, path)
    try:
        yield
    finally:
        if added:
            try:
                sys.path.remove(path)
            except ValueError:
                pass


def _load_from_skill(skill_name, module_name):
    scripts = os.path.join(_SKILLS, skill_name, "scripts")
    with _prepend_path(scripts):
        return importlib.import_module(module_name)


def load_wiki_tools():
    """Return (wiki_builder, logic_sentry), or (None, None) when unavailable."""
    try:
        return (
            _load_from_skill("novel-wiki", "wiki_builder"),
            _load_from_skill("novel-wiki", "logic_sentry"),
        )
    except Exception:  # pragma: no cover
        return None, None


def load_style_tool():
    """Return extract_style module, or None when unavailable."""
    try:
        return _load_from_skill("novel-style", "extract_style")
    except Exception:  # pragma: no cover
        return None
