#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""entity_schedule_audit 单测。"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import entity_schedule_audit as E  # noqa: E402


def _root(storyboard):
    d = Path(tempfile.mkdtemp())
    epd = d / "脚本" / "第1集"
    epd.mkdir(parents=True)
    (epd / "storyboard.json").write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")
    return str(d)


def codes(res):
    return {f["code"] for f in res["findings"]}


def test_complete_clip_entity_schedule_passes():
    root = _root({
        "clips": [{
            "id": "C01",
            "character_ids": ["CHAR_01"],
            "object_ids": ["PROP_玉佩"],
            "location_id": "LOC_冷宫",
            "entity_schedule": {
                "characters": ["CHAR_01"],
                "objects": ["PROP_玉佩"],
                "locations": ["LOC_冷宫"],
                "knowledge_state": {"CHAR_01": ["知道玉佩是假"]},
                "required_presence": ["CHAR_01", "PROP_玉佩"],
            },
        }]
    })
    res = E.audit_episode(root, "第1集")
    assert res["ok"]
    assert res["stats"]["coverage"] == 1.0
    assert not res["findings"]


def test_missing_schedule_warns_when_clip_has_entities():
    root = _root({"clips": [{"id": "C01", "character_ids": ["CHAR_01"], "description": "沈念入殿"}]})
    res = E.audit_episode(root, "第1集")
    assert not res["ok"]
    assert "missing_entity_schedule" in codes(res)


def test_schedule_missing_expected_character_warns():
    root = _root({
        "clips": [{
            "id": "C01",
            "character_ids": ["CHAR_01", "CHAR_02"],
            "entity_schedule": {"characters": ["CHAR_01"], "locations": ["LOC_01"]},
        }]
    })
    res = E.audit_episode(root, "第1集")
    assert "entity_schedule_missing_expected" in codes(res)
    finding = next(f for f in res["findings"] if f["code"] == "entity_schedule_missing_expected")
    assert finding["missing"]["characters"] == ["CHAR_02"]


def test_shot_schedule_overrides_clip_schedule():
    root = _root({
        "clips": [{
            "id": "C01",
            "entity_schedule": {"characters": ["CHAR_01"], "locations": ["LOC_01"]},
            "shots": [{
                "id": "S01",
                "character_ids": ["CHAR_02"],
                "entity_schedule": {"characters": ["CHAR_02"], "locations": ["LOC_01"]},
            }],
        }]
    })
    res = E.audit_episode(root, "第1集")
    assert res["ok"]
    assert res["stats"]["units"] == 1


def test_required_presence_must_be_declared_entity():
    root = _root({
        "clips": [{
            "id": "C01",
            "entity_schedule": {"characters": ["CHAR_01"], "required_presence": ["PROP_玉佩"]},
        }]
    })
    res = E.audit_episode(root, "第1集")
    assert "required_presence_unbound" in codes(res)


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))
