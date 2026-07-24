#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n2d_insert_coverage 策略真值源单测。cd skills/n2d/_lib && python -m pytest test_insert_coverage.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import n2d_insert_coverage as ic


def _c(**kw):
    return dict(kw)


# ── resolve_mode / 老项目宽限 ────────────────────────────────────────────────

def test_mode_missing_defaults_to_warn_only():
    assert ic.resolve_mode(None) == ic.INSERT_COVERAGE_MODE_WARN
    assert ic.resolve_mode("") == ic.INSERT_COVERAGE_MODE_WARN


def test_mode_aliases():
    assert ic.resolve_mode("启用") == ic.INSERT_COVERAGE_MODE_ENFORCE
    assert ic.resolve_mode("开启") == ic.INSERT_COVERAGE_MODE_ENFORCE
    assert ic.resolve_mode("仅提示") == ic.INSERT_COVERAGE_MODE_WARN
    assert ic.resolve_mode("关闭") == ic.INSERT_COVERAGE_MODE_OFF
    assert ic.resolve_mode("garbage") == ic.INSERT_COVERAGE_MODE_WARN  # 不认得回退宽限档


# ── clip_insert_subject ──────────────────────────────────────────────────────

def test_subject_by_template():
    assert ic.clip_insert_subject(_c(template="system_panel")) == ic.SUBJECT_SYSTEM
    assert ic.clip_insert_subject(_c(template="screen_insert")) == ic.SUBJECT_SYSTEM
    assert ic.clip_insert_subject(_c(template="object_discovery")) == ic.SUBJECT_PROP
    assert ic.clip_insert_subject(_c(template="evidence_search")) == ic.SUBJECT_PROP


def test_subject_by_template_contract():
    clip = _c(template_contract={"template_id": "system_panel"})
    assert ic.clip_insert_subject(clip) == ic.SUBJECT_SYSTEM


def test_subject_by_close_and_tokens():
    assert ic.clip_insert_subject(_c(shot_size="CU 特写", desc="系统面板底框浮现")) == ic.SUBJECT_SYSTEM
    assert ic.clip_insert_subject(_c(shot_size="ECU 特写", desc="令牌的物件细节特写")) == ic.SUBJECT_PROP


def test_character_shot_is_none():
    # 人物中景反应镜 → 不是非人物 insert
    assert ic.clip_insert_subject(_c(shot_size="MS 中景", desc="主角惊讶地看着前方")) is None
    # 提到系统但是人物反应中景、无近景无 insert 线索 → 不当作已覆盖
    assert ic.clip_insert_subject(_c(shot_size="MS 中景", desc="他盯着面板念叨")) is None


# ── evaluate_episode 策略 ────────────────────────────────────────────────────

def _character_clips(n):
    return [_c(shot_size="MS 中景", desc=f"人物对话{i}") for i in range(n)]


def test_system_expected_uncovered_blocks_when_enforced():
    clips = _character_clips(4) + [_c(shot_size="MCU", desc="他盯着属性面板发呆")]
    res = ic.evaluate_episode(clips, mode="启用", genre_keys=["chuanyue"])
    assert res["expect"]["system_panel"] is True
    assert res["covered"]["system_panel"] is False
    codes = {(f["code"], f["severity"]) for f in res["findings"]}
    assert ("insert_coverage_system_panel", "block") in codes


def test_system_expected_uncovered_warns_when_advisory():
    clips = _character_clips(4) + [_c(shot_size="MCU", desc="他盯着属性面板发呆")]
    res = ic.evaluate_episode(clips, mode="仅提示")
    sev = {f["code"]: f["severity"] for f in res["findings"]}
    assert sev.get("insert_coverage_system_panel") == "warn"
    assert not ic.has_blocking(res)


def test_system_covered_no_finding():
    clips = _character_clips(4) + [_c(template="system_panel", shot_size="CU", desc="系统面板底框")]
    res = ic.evaluate_episode(clips, mode="启用")
    codes = {f["code"] for f in res["findings"]}
    assert "insert_coverage_system_panel" not in codes


def test_prop_is_warn_never_block():
    clips = _character_clips(4) + [_c(shot_size="MS", desc="她握着那枚令牌走了")]
    res = ic.evaluate_episode(clips, mode="启用")
    sev = {f["code"]: f["severity"] for f in res["findings"]}
    assert sev.get("insert_coverage_prop") == "warn"
    assert not ic.has_blocking(res)  # 道具永不 block


def test_prop_covered_no_finding():
    clips = _character_clips(4) + [_c(template="object_discovery", desc="令牌 insert 特写")]
    res = ic.evaluate_episode(clips, mode="启用")
    codes = {f["code"] for f in res["findings"]}
    assert "insert_coverage_prop" not in codes


def test_off_mode_silent():
    clips = _character_clips(4) + [_c(desc="属性面板 系统面板")]
    res = ic.evaluate_episode(clips, mode="关闭")
    assert res["findings"] == []


def test_pure_dialogue_episode_not_forced():
    # 无系统/道具证据的纯对话集：不强塞 insert（题材+证据双门控的证据主门）
    clips = _character_clips(4)  # 短集 < RHYTHM_MIN_CLIPS
    res = ic.evaluate_episode(clips, mode="启用")
    assert res["findings"] == []


def test_rhythm_nudge_long_all_character():
    clips = _character_clips(8)  # 长集全人物、无证据
    res = ic.evaluate_episode(clips, mode="仅提示")
    codes = {f["code"] for f in res["findings"]}
    assert "insert_coverage_all_character" in codes
    assert not ic.has_blocking(res)


def test_rhythm_nudge_suppressed_when_specific_evidence():
    clips = _character_clips(8) + [_c(desc="他看着系统面板")]
    res = ic.evaluate_episode(clips, mode="仅提示")
    codes = {f["code"] for f in res["findings"]}
    # 有 system 证据时走专项 finding，不再叠泛化节奏提醒
    assert "insert_coverage_all_character" not in codes
    assert "insert_coverage_system_panel" in codes


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
