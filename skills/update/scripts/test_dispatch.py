import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import dispatch as d


def test_has_episode_selector():
    assert d.has_episode_selector(["第2集"]) is True
    assert d.has_episode_selector(["--all"]) is True
    assert d.has_episode_selector(["--write-plan", "--json"]) is False
    assert d.has_episode_selector([]) is False


def test_split_target_episode_as_first_arg(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root, rest = d.split_target("第1集", ["--write-plan"])
    assert root == "."
    assert rest == ["第1集", "--write-plan"]
    root, rest = d.split_target("12", [])
    assert (root, rest) == (".", ["12"])


def test_split_target_keeps_real_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # 真实存在的目录即使长得像集号也按目录处理
    (tmp_path / "第1集").mkdir()
    root, rest = d.split_target("第1集", [])
    assert (root, rest) == ("第1集", [])
    root, rest = d.split_target("制漫剧/某剧", ["第1集"])
    assert (root, rest) == ("制漫剧/某剧", ["第1集"])


def test_media_dispatch_routes_project_to_media_planner(tmp_path, monkeypatch):
    project = tmp_path / "mv"
    project.mkdir()
    calls = []

    monkeypatch.setattr(d, "detect_line", lambda root, repo: "mv")
    monkeypatch.setattr(d, "MEDIA_REFRESH", __file__)

    class Result:
        returncode = 0

    def fake_run(cmd, check=False):
        calls.append(cmd)
        return Result()

    monkeypatch.setattr(d.subprocess, "run", fake_run)

    rc = d.main(["media", str(project), "--image", "Clip_001", "--write-plan"])

    assert rc == 0
    assert calls
    assert "--line" in calls[0]
    assert "mv" in calls[0]
    assert "--image" in calls[0]
