# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import fetch_novel as fn


def test_missing_deps_returns_pip_hint():
    missing = fn.missing_deps(have={"requests", "bs4"})  # trafilatura & docx absent
    assert "trafilatura" in missing
    assert "python-docx" in missing  # reported by install name, not import name


def test_no_missing_deps_when_all_present():
    have = {"requests", "bs4", "trafilatura", "docx"}
    assert fn.missing_deps(have=have) == []
