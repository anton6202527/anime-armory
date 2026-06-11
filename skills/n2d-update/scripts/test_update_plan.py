import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import update_plan as up


def make_project(tmp_path: Path) -> Path:
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("- 制作模式：配音先行\n", encoding="utf-8")
    (root / "_进度.md").write_text(
        "\n".join(
            [
                "# 测试剧 — 生产进度",
                "",
                "| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | 1000 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | 57/68 | ⬜ | ⬜ | ⬜ |",
                "| 第2集 | 900 | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return root


def test_current_stage_for_partial_image(tmp_path):
    root = make_project(tmp_path)
    header, rows = up.rows_by_episode(str(root))
    assert up.current_stage_key(str(root), "第1集", header, rows["第1集"]) == "image"


def test_plan_detects_snapshot_change_and_bounds_to_current_stage(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    monkeypatch.setattr(up, "git_changed_files", lambda: [])
    old = up.snapshot_for_skills(up.relevant_skills_for_stage("image"))
    old["files"]["skills/n2d-image/SKILL.md"] = "outdated"
    up.write_json(up.snapshot_path(str(root)), old)

    plan = up.build_plan(str(root), "第1集", include_git=False)
    assert plan["rebuild_needed"] is True
    assert plan["rerun_from"] in {"image_prompt", "image"}
    assert plan["rerun_until"] == "image"
    assert "n2d-image" in plan["changed_skills"]


def test_record_writes_snapshot(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    monkeypatch.setattr(up, "git_changed_files", lambda: [])
    snap = up.record(str(root), ["第1集"])
    assert snap["kind"] == up.KIND_SNAPSHOT
    path = Path(up.snapshot_path(str(root)))
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "n2d-image" in data["skills"]


def test_git_dirty_is_only_bootstrap_hint_after_record(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    up.record(str(root), ["第1集"])
    monkeypatch.setattr(up, "git_changed_files", lambda: ["skills/n2d-image/SKILL.md"])

    plan = up.build_plan(str(root), "第1集", include_git=True)
    assert plan["rebuild_needed"] is False
    assert plan["changed_files"] == []
