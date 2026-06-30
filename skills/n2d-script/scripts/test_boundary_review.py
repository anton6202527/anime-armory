#!/usr/bin/env python3
"""Tests for boundary_review.py structured signoff."""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import boundary_review as BR  # noqa: E402


def _mk_work(raw_text):
    d = tempfile.mkdtemp()
    ep = Path(d) / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "raw.txt").write_text(raw_text, encoding="utf-8")
    return d


RISKY = "她走进屋里。\n然后坐下。\n"


def test_check_blocks_missing_review_for_risky_boundary():
    root = _mk_work(RISKY)
    result = BR.validate(root)
    assert not result["ok"]
    assert any(f["code"] == "missing_boundary_review" for f in result["findings"])


def test_draft_then_signed_review_passes():
    root = _mk_work(RISKY)
    BR.draft(root, write=True)
    path = BR.review_path(root)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["reviews"][0]["decision"] = "accept_risk"
    data["reviews"][0]["notes"] = "短集保留，后续 voiceover 补冲突和集尾钩。"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    result = BR.validate(root)

    assert result["ok"]
    assert not result["findings"]


def test_raw_change_invalidates_signed_review():
    root = _mk_work(RISKY)
    BR.draft(root, write=True)
    path = BR.review_path(root)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["reviews"][0]["decision"] = "accept_risk"
    data["reviews"][0]["notes"] = "先接受。"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (Path(root) / "脚本" / "第1集" / "raw.txt").write_text("她走进屋里。\n然后坐下。\n门外忽然传来哭声，", encoding="utf-8")

    result = BR.validate(root)

    assert not result["ok"]
    assert any(f["code"] == "stale_episode_review" for f in result["findings"])


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
