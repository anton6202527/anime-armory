#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cd skills/n2d/_lib && python3 -m pytest test_skill_freshness.py"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skill_freshness as sf  # noqa: E402


def test_until_key_maps_gate_stages():
    assert sf.until_key_for_gate_stage("image_preflight") == "image"
    assert sf.until_key_for_gate_stage("video_preflight") == "video"
    assert sf.until_key_for_gate_stage("image_prompt_preflight") == "image_prompt"
    assert sf.until_key_for_gate_stage("video_prompt_preflight") == "video_prompt"
    assert sf.until_key_for_gate_stage("compose") == "compose"
    assert sf.until_key_for_gate_stage("nonsense") is None


def test_owner_scope_excludes_downstream_and_observe_only():
    owners = sf.production_owner_skills_until("image")
    assert "n2d-image" in owners and "n2d-script" in owners and "n2d-voice" in owners
    # 下游线（出视频）不应纳入"出图阶段"的物料过期范围
    assert "n2d-video" not in owners
    scope = sf.relevant_skills_for_diff("image")
    assert "n2d" in scope  # _lib 运行期契约层
    assert "n2d-lora" in scope  # LoRA 生命周期是横切身份锁生产规则
    assert not (scope & sf.OBSERVE_ONLY_SKILLS)  # 观测层从不参与比对


def test_material_classification():
    assert sf.is_material_affecting("skills/n2d-image/SKILL.md") is True
    assert sf.is_material_affecting("skills/n2d-lora/SKILL.md") is True
    assert sf.is_material_affecting("skills/n2d/_lib/n2d_const.py") is True
    # 观测层 / gate-only / 加速基建：改了不让物料过期
    assert sf.is_material_affecting("skills/n2d-review/scripts/gate.py") is False
    assert sf.is_material_affecting("skills/n2d-image/scripts/image_qc.py") is False
    assert sf.is_material_affecting("skills/n2d/_lib/n2d_friction.py") is False
    assert sf.is_material_affecting("skills/n2d/_lib/skill_freshness.py") is False


def _baseline(root, mutate=None):
    relevant = sf.relevant_skills_for_diff("image")
    snap = sf.snapshot_for_skills(sf.REPO_ROOT, sf.REPO_SKILLS, relevant)
    if mutate:
        snap["files"][mutate] = "0" * 64
    path = sf.snapshot_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, ensure_ascii=False)


def test_assess_statuses():
    with tempfile.TemporaryDirectory() as td:
        assert sf.assess(td, "image")["status"] == "no_baseline"

    with tempfile.TemporaryDirectory() as td:
        _baseline(td)
        assert sf.assess(td, "image")["status"] == "fresh"

    with tempfile.TemporaryDirectory() as td:
        _baseline(td, mutate="skills/n2d-image/SKILL.md")
        res = sf.assess(td, "image")
        assert res["status"] == "drift"
        assert "n2d-image" in res["material_skills"]

    with tempfile.TemporaryDirectory() as td:
        _baseline(td, mutate="skills/n2d-image/scripts/image_qc.py")
        res = sf.assess(td, "image")
        assert res["status"] == "drift"
        assert res["material_skills"] == []  # gate-only：有改动但不影响物料


def test_legacy_baseline_flagged():
    with tempfile.TemporaryDirectory() as td:
        path = sf.snapshot_path(td)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"git_commit": "abc123"}, fh)  # 旧版无 files 内容快照
        assert sf.assess(td, "image")["status"] == "no_baseline_legacy"
