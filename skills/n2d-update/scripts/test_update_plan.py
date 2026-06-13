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


def test_current_stage_uses_furthest_started_when_earlier_gap_exists(tmp_path):
    root = make_project(tmp_path)
    progress = root / "_进度.md"
    text = progress.read_text(encoding="utf-8")
    progress.write_text(
        text.replace(
            "| 第1集 | 1000 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | 57/68 | ⬜ | ⬜ | ⬜ |",
            "| 第1集 | 1000 | ✅ | ✅ | ✅ | ✅ | ⏳rough | ✅ | ✅ | ✅ | ⬜ | ✅ | 25/35 | ⬜ | ⬜ | ⬜ |",
        ),
        encoding="utf-8",
    )
    header, rows = up.rows_by_episode(str(root))
    assert up.current_stage_key(str(root), "第1集", header, rows["第1集"]) == "image"


def test_plan_reports_current_todo_even_when_video_started(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    progress = root / "_进度.md"
    text = progress.read_text(encoding="utf-8")
    progress.write_text(
        text.replace(
            "| 第1集 | 1000 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | 57/68 | ⬜ | ⬜ | ⬜ |",
            "| 第1集 | 1000 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | 69/85 | ✅ | 5/20 | ⬜ |",
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(up, "git_changed_files", lambda *_: [])
    up.record(str(root), ["第1集"])

    plan = up.build_plan(str(root), "第1集", include_git=False)

    assert plan["current_stage"] == "video"
    assert plan["rebuild_needed"] is False
    assert plan["current_todo"]["stage_key"] == "image"
    assert plan["current_todo"]["skill"] == "n2d-image"
    assert plan["current_todo"]["status"] == "69/85"

    md = up.render_markdown(plan)
    assert "当前生产缺口" in md
    assert "出图 = `69/85`" in md
    assert "最远已开始产物 `video`" in md


def test_plan_detects_snapshot_change_and_bounds_to_current_stage(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    monkeypatch.setattr(up, "git_changed_files", lambda *_: [])
    old = up.snapshot_for_skills(up.REPO_ROOT, up.REPO_SKILLS, up.relevant_skills_for_stage("image"))
    old["files"]["skills/n2d-image/SKILL.md"] = "outdated"
    up.write_json(up.snapshot_path(str(root)), old)

    plan = up.build_plan(str(root), "第1集", include_git=False)
    assert plan["rebuild_needed"] is True
    assert plan["rerun_from"] in {"image_prompt", "image"}
    assert plan["rerun_until"] == "image"
    assert "n2d-image" in plan["changed_skills"]


def test_build_plan_strict_refresh_uses_latest_prompt_standard(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    monkeypatch.setattr(up, "git_changed_files", lambda *_: [])
    old = up.snapshot_for_skills(up.REPO_ROOT, up.REPO_SKILLS, up.relevant_skills_for_stage("image"))
    old["files"]["skills/n2d-image/SKILL.md"] = "outdated"
    up.write_json(up.snapshot_path(str(root)), old)

    plan = up.build_plan(str(root), "第1集", include_git=False, regen_mode="严审刷新")

    assert plan["strict_image_refresh"] is True
    assert "keep_images" not in plan
    joined = "\n".join(plan["commands"])
    assert "--regen-list --strict" in joined
    assert "不符合最新prompt/QC标准" in joined


def test_image_qc_change_refreshes_gate_without_rebuild(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    monkeypatch.setattr(up, "git_changed_files", lambda *_: [])
    old = up.snapshot_for_skills(up.REPO_ROOT, up.REPO_SKILLS, up.relevant_skills_for_stage("image"))
    old["files"]["skills/n2d-image/scripts/image_qc.py"] = "outdated"
    up.write_json(up.snapshot_path(str(root)), old)

    plan = up.build_plan(str(root), "第1集", include_git=False)

    assert plan["rebuild_needed"] is False
    assert plan["gate_refresh_needed"] is True
    assert plan["gate_refresh_stages"] == ["image"]
    assert plan["rerun_from"] is None
    assert any("--stage image" in c for c in plan["commands"])
    assert not any(c.startswith("n2d-image ") for c in plan["commands"])

    md = up.render_markdown(plan)
    assert "建议动作：`刷新 gate/QC`" in md
    assert "需要重制：否" in md


def test_record_writes_snapshot(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    monkeypatch.setattr(up, "git_changed_files", lambda *_: [])
    snap = up.record(str(root), ["第1集"])
    assert snap["kind"] == up.KIND_SNAPSHOT
    path = Path(up.snapshot_path(str(root)))
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "n2d-image" in data["skills"]


def test_record_preserves_existing_snapshot_scope(tmp_path):
    root = make_project(tmp_path)
    old = up.snapshot_for_skills(up.REPO_ROOT, up.REPO_SKILLS, ["n2d-video"])
    old["kind"] = up.KIND_SNAPSHOT
    up.write_json(up.snapshot_path(str(root)), old)

    snap = up.record(str(root), ["第2集"])
    assert "n2d-video" in snap["skills"]


def test_record_all_then_check_earlier_episode_has_no_phantom_changes(tmp_path):
    # 基线按 --all 并集记录（第1集到 image，第2集还在 script_stage1）；
    # check 早期集时，超出该集范围的 skill 不能被当成“变更”。
    root = make_project(tmp_path)
    up.record(str(root), ["第1集", "第2集"])

    plan = up.build_plan(str(root), "第2集", include_git=False)
    assert plan["rebuild_needed"] is False
    assert plan["changed_files"] == []
    assert plan["changed_skills"] == []


def test_stage_advance_is_newly_relevant_not_changed(tmp_path):
    # record 时第1集在配音阶段；推进到出图后 check，
    # n2d-image 应记为“新纳入范围”而不是“变更→建议重制”。
    root = make_project(tmp_path)
    progress = root / "_进度.md"
    header = progress.read_text(encoding="utf-8").split("| 第1集")[0]
    progress.write_text(
        header
        + "| 第1集 | 1000 | ✅ | ✅ | ✅ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |\n",
        encoding="utf-8",
    )
    up.record(str(root), ["第1集"])
    progress.write_text(
        header
        + "| 第1集 | 1000 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | 10/68 | ⬜ | ⬜ | ⬜ |\n",
        encoding="utf-8",
    )

    plan = up.build_plan(str(root), "第1集", include_git=False)
    assert plan["rebuild_needed"] is False
    assert plan["changed_files"] == []
    assert "n2d-image" in plan["newly_relevant_skills"]
    assert any("首次纳入" in note for note in plan["notes"])


def test_test_file_changes_do_not_trigger_rebuild(tmp_path):
    root = make_project(tmp_path)
    up.record(str(root), ["第1集"])
    path = Path(up.snapshot_path(str(root)))
    snap = json.loads(path.read_text(encoding="utf-8"))
    # 新基线不收测试文件；旧基线遗留的测试文件条目也不算变更
    assert not any(up.is_test_path(p) for p in snap["files"])
    snap["files"]["skills/n2d-image/scripts/test_legacy.py"] = "stale"
    up.write_json(str(path), snap)

    plan = up.build_plan(str(root), "第1集", include_git=False)
    assert plan["rebuild_needed"] is False
    assert plan["changed_files"] == []


def test_storyboard_only_change_reruns_from_stage2(tmp_path):
    root = make_project(tmp_path)
    up.record(str(root), ["第1集"])
    path = Path(up.snapshot_path(str(root)))
    snap = json.loads(path.read_text(encoding="utf-8"))
    snap["files"]["skills/n2d-script/finalize_storyboard.py"] = "outdated"
    up.write_json(str(path), snap)

    plan = up.build_plan(str(root), "第1集", include_git=False)
    assert plan["rebuild_needed"] is True
    assert plan["rerun_from"] == "script_stage2"


def test_split_change_still_reruns_from_stage1(tmp_path):
    root = make_project(tmp_path)
    up.record(str(root), ["第1集"])
    path = Path(up.snapshot_path(str(root)))
    snap = json.loads(path.read_text(encoding="utf-8"))
    snap["files"]["skills/n2d-script/scripts/split_novel.py"] = "outdated"
    up.write_json(str(path), snap)

    plan = up.build_plan(str(root), "第1集", include_git=False)
    assert plan["rebuild_needed"] is True
    assert plan["rerun_from"] == "script_stage1"


def test_git_dirty_is_only_bootstrap_hint_after_record(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    up.record(str(root), ["第1集"])
    monkeypatch.setattr(up, "git_changed_files", lambda *_: ["skills/n2d-image/SKILL.md"])

    plan = up.build_plan(str(root), "第1集", include_git=True)
    assert plan["rebuild_needed"] is False
    assert plan["changed_files"] == []


def test_git_dirty_newly_relevant_skill_is_counted(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    progress = root / "_进度.md"
    text = progress.read_text(encoding="utf-8")
    progress.write_text(
        text.replace(
            "| 第1集 | 1000 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | 57/68 | ⬜ | ⬜ | ⬜ |",
            "| 第1集 | 1000 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | 68/68 | ✅ | 5/20 | ⬜ |",
        ),
        encoding="utf-8",
    )
    old = up.snapshot_for_skills(up.REPO_ROOT, up.REPO_SKILLS, ["n2d-image"])
    old["kind"] = up.KIND_SNAPSHOT
    up.write_json(up.snapshot_path(str(root)), old)
    monkeypatch.setattr(up, "git_changed_files", lambda *_: ["skills/n2d-video/scripts/video_runner.py"])

    plan = up.build_plan(str(root), "第1集", include_git=True)
    assert plan["rebuild_needed"] is True
    assert "skills/n2d-video/scripts/video_runner.py" in plan["changed_files"]
    assert plan["rerun_from"] == "video_prompt"


def test_rerun_covers_image_range() -> None:
    assert up.rerun_covers_image("image_prompt", "compose") is True
    assert up.rerun_covers_image("script_stage1", "image") is True
    assert up.rerun_covers_image(None, "image") is True       # 无 start = 从头
    assert up.rerun_covers_image("video", "compose") is False  # image 已过，不会重出
    assert up.rerun_covers_image("image", "image") is True


def test_command_for_rerun_appends_image_qc_when_image_covered() -> None:
    cmds = up.command_for_rerun("R", "第1集", "image_prompt", "image")
    assert any("image_qc" in c for c in cmds)
    assert any("--stage image" in c for c in cmds)


def test_command_for_rerun_no_image_qc_when_image_not_covered() -> None:
    cmds = up.command_for_rerun("R", "第1集", "video", "compose")
    assert not any("image_qc" in c for c in cmds)


def test_plan_includes_image_qc_environment_when_report_exists(tmp_path, monkeypatch) -> None:
    root = make_project(tmp_path)
    monkeypatch.setattr(up, "git_changed_files", lambda *_: [])
    old = up.snapshot_for_skills(up.REPO_ROOT, up.REPO_SKILLS, up.relevant_skills_for_stage("image"))
    old["files"]["skills/n2d-image/SKILL.md"] = "outdated"
    up.write_json(up.snapshot_path(str(root)), old)

    qc_dir = root / "生产数据" / "image_qc" / "第1集"
    qc_dir.mkdir(parents=True)
    (qc_dir / "image_qc_第1集.json").write_text(json.dumps({
        "qc_environment": {
            "precision_level": "full",
            "python": "/env/bin/python",
            "recommended_install": "",
            "jump_to_stage": "image",
            "jump_reason": "image_qc 有硬阻断",
        },
        "summary": {
            "verdict": "block",
            "hard_blocks": 8,
            "advisory": 16,
            "degraded": False,
        },
    }, ensure_ascii=False), encoding="utf-8")

    plan = up.build_plan(str(root), "第1集", include_git=False)
    qc = plan["image_qc_environment"]
    assert qc["precision_level"] == "full"
    assert qc["jump_to_stage"] == "image"
    assert qc["hard_blocks"] == 8

    md = up.render_markdown(plan)
    assert "图片质检环境与阶段跳转" in md
    assert "非阻断初筛 `16`" in md
    assert "初筛人判" not in md
    assert "当前应停在/回退：`image`" in md
    assert "建议安装：无需补装" in md


def test_read_setting_and_resolve_regen_mode(tmp_path) -> None:
    root = tmp_path / "剧"
    root.mkdir()
    (root / "_设置.md").write_text("- 制作模式：配音先行\n- 更新重制策略：保图刷新\n", encoding="utf-8")
    assert up.read_setting(str(root), "更新重制策略") == "保图刷新"
    assert up.read_setting(str(root), "缺这个键") is None
    # CLI 显式 > 设置 > 默认；旧名「保图刷新」归一到「严审刷新」
    assert up.resolve_regen_mode(str(root), "最小") == "最小"
    assert up.resolve_regen_mode(str(root), None) == "严审刷新"
    assert up.resolve_regen_mode(str(root), "保图刷新") == "严审刷新"
    assert up.resolve_regen_mode(str(tmp_path / "无设置"), None) == "最小"


def test_commands_for_strict_image_refresh_shape() -> None:
    cmds = up.commands_for_strict_image_refresh("R", "第1集", "image_prompt", "image")
    joined = "\n".join(cmds)
    assert "--regen-list --strict" in joined   # 按最新标准严审旧图
    assert "--affected-shots --strict" in joined
    assert "--affected-shots" in joined        # 只重生成这些镜
    assert "严审刷新" in joined
    assert "--stage image" in joined           # 末尾验像素
    # 不应出现"整集 --rerun-from image"无 affected 限定的裸重出（避免全部重出）
    assert "--rerun-from image $shots" in joined


def test_strict_image_refresh_only_when_image_covered() -> None:
    # video→compose 不覆盖 image：即便严审刷新模式也走普通命令（无图可审）
    cmds = up.commands_for_strict_image_refresh("R", "第1集", "video", "compose")
    # text_start 退回 image_prompt（封顶），但此函数本身只在覆盖 image 时被 build_plan 调用
    assert any("image_qc" in c for c in cmds)
