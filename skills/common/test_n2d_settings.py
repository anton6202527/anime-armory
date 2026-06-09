from pathlib import Path

import n2d_settings


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "skills").mkdir(parents=True)
    return repo


def test_project_setting_wins_over_global_default(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    work = repo / "制漫剧" / "测试剧"
    work.mkdir(parents=True)
    (repo / "创作偏好-默认.md").write_text("- 生图AI: Seedream\n", encoding="utf-8")
    (work / "_设置.md").write_text("- 生图AI: Codex\n", encoding="utf-8")

    assert n2d_settings.get_setting(str(work), "生图AI") == "Codex"


def test_tool_neutral_global_default_beats_legacy_claude_default(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    work = repo / "制漫剧" / "测试剧"
    work.mkdir(parents=True)
    (repo / ".agents").mkdir()
    (repo / ".claude").mkdir()
    (repo / ".agents" / "创作偏好-默认.md").write_text("- 生图AI: Seedream\n", encoding="utf-8")
    (repo / ".claude" / "创作偏好-默认.md").write_text("- 生图AI: Codex\n", encoding="utf-8")

    assert n2d_settings.global_settings_path(str(repo)) == str(repo / ".agents" / "创作偏好-默认.md")
    assert n2d_settings.get_setting(str(work), "生图AI") == "Seedream"


def test_legacy_claude_default_remains_backward_compatible(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    work = repo / "制漫剧" / "测试剧"
    work.mkdir(parents=True)
    (repo / ".claude").mkdir()
    (repo / ".claude" / "创作偏好-默认.md").write_text("- 生图AI: Codex\n", encoding="utf-8")

    assert n2d_settings.get_setting(str(work), "生图AI") == "Codex"


def test_is_native_av_handles_list_and_bare_forms(tmp_path: Path) -> None:
    for body in ("- 制作模式: 原生音画\n", "制作模式：原生音画\n", "- 制作模式: native_av\n"):
        work = tmp_path / body[:4].strip("- :")  # unique-ish dir per form
        work.mkdir(exist_ok=True)
        (work / "_设置.md").write_text(body, encoding="utf-8")
        assert n2d_settings.is_native_av(str(work)) is True
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "_设置.md").write_text("制作模式: 配音先行\n", encoding="utf-8")
    assert n2d_settings.is_native_av(str(plain)) is False


def test_load_settings_parses_all_forms(tmp_path: Path) -> None:
    work = tmp_path / "w"
    work.mkdir()
    (work / "_设置.md").write_text(
        "- 制作模式: 原生音画  # 带注释\n生图AI：Codex\n水印: 不打\n", encoding="utf-8")
    s = n2d_settings.load_settings(str(work))
    assert s["制作模式"] == "原生音画"   # 列表形 + 注释剥除
    assert s["生图AI"] == "Codex"        # 裸形 + 全角冒号
    assert s["水印"] == "不打"
    assert n2d_settings.load_settings(str(tmp_path / "missing")) == {}
