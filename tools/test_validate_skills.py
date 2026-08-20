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


def test_skill_stats_sync_is_registered():
    assert "F7" in validate_skills.CHECKS


def test_bare_skill_ref_regex_covers_web_app_skill_prefix():
    match = validate_skills.SLASH_RE.search("下一步调用 /app-script-workbench")
    assert match
    assert match.group(0) == "/app-script-workbench"


def test_app_namespace_skills_are_counted_as_standalone():
    names = {path.name for path in validate_skills.update_skill_stats.skill_dirs_for("standalone")}
    assert {"app-script-workbench", "app-character-turnaround", "app-first-frame-video", "app-audio-video"} <= names


def test_app_namespace_rejects_skill_without_app_prefix(tmp_path, monkeypatch):
    skills = tmp_path / "skills"
    skill = skills / "app" / "canvas-tool"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: canvas-tool\ndescription: test\n---\n",
        encoding="utf-8",
    )
    readme = skills / "README.md"
    readme.write_text("| `canvas-tool` | test |\n", encoding="utf-8")
    monkeypatch.setattr(validate_skills, "SKILLS", skills)
    monkeypatch.setattr(validate_skills, "README", readme)

    issues = validate_skills.check_readme_index()
    assert any("skills/app/ 下的 skill 名必须以 app- 开头" in issue for issue in issues)
