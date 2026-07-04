#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import validate_skills


def test_novel_market_claim_regex_flags_unanchored_volatile_claim():
    line = "2026 红果短剧赛道持续热门，改编成功率超过 40%。"
    assert validate_skills.NOVEL_MARKET_CLAIM_RE.search(line)
    assert not validate_skills._line_has_market_anchor([line], 0)


def test_novel_market_claim_anchor_window_allows_evidence_reference():
    lines = [
        "以下平台趋势以 market_baseline 与 research_sources 为准。",
        "2026 红果短剧赛道持续热门，改编成功率超过 40%。",
    ]
    assert validate_skills.NOVEL_MARKET_CLAIM_RE.search(lines[1])
    assert validate_skills._line_has_market_anchor(lines, 1)


def test_real_workspace_path_lint_flags_concrete_work_path():
    line = 'asset = "/repo/" + "创作区/制漫剧/LintFixtureRealWork/出视频/第1集/Clip_01.mp4"'
    assert validate_skills._line_mentions_real_work_path(line, {"LintFixtureRealWork"})


def test_real_workspace_path_lint_allows_generic_tmp_project_path():
    line = 'root = tmp_path / "创作区" / "制漫剧" / "测试剧"'
    assert not validate_skills._line_mentions_real_work_path(line, {"LintFixtureRealWork"})
