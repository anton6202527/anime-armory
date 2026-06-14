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
    # record 直接捕获当前 repo 内容快照；check 立即比对，无中间改动 → 无变更。
    up.record(str(root), ["第1集"])

    plan = up.build_plan(str(root), "第1集")

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
    old = up.snapshot_for_skills(up.REPO_ROOT, up.REPO_SKILLS, up.relevant_skills_for_stage("image"))
    old["files"]["skills/n2d-image/SKILL.md"] = "outdated"
    up.write_json(up.snapshot_path(str(root)), old)

    plan = up.build_plan(str(root), "第1集")
    assert plan["rebuild_needed"] is True
    assert plan["rerun_from"] in {"image_prompt", "image"}
    assert plan["rerun_until"] == "image"
    assert "n2d-image" in plan["changed_skills"]


def test_build_plan_strict_refresh_uses_latest_prompt_standard(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    old = up.snapshot_for_skills(up.REPO_ROOT, up.REPO_SKILLS, up.relevant_skills_for_stage("image"))
    old["files"]["skills/n2d-image/SKILL.md"] = "outdated"
    up.write_json(up.snapshot_path(str(root)), old)

    plan = up.build_plan(str(root), "第1集", regen_mode="严审刷新")

    assert plan["strict_image_refresh"] is True
    assert "keep_images" not in plan
    joined = "\n".join(plan["commands"])
    assert "--regen-list --strict" in joined
    assert "不符合最新prompt/QC标准" in joined


def test_image_qc_change_refreshes_gate_without_rebuild(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    old = up.snapshot_for_skills(up.REPO_ROOT, up.REPO_SKILLS, up.relevant_skills_for_stage("image"))
    old["files"]["skills/n2d-image/scripts/image_qc.py"] = "outdated"
    up.write_json(up.snapshot_path(str(root)), old)

    plan = up.build_plan(str(root), "第1集")

    assert plan["rebuild_needed"] is False
    assert plan["gate_refresh_needed"] is True
    assert plan["gate_refresh_stages"] == ["image"]
    assert plan["rerun_from"] is None
    assert any("--stage image" in c for c in plan["commands"])
    assert not any(c.startswith("n2d-image ") for c in plan["commands"])

    md = up.render_markdown(plan)
    assert "建议动作：`刷新 gate/QC`" in md
    assert "需要重制：否" in md


def test_observe_only_change_refreshes_review_outputs(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    old = up.snapshot_for_skills(up.REPO_ROOT, up.REPO_SKILLS, up.relevant_skills_for_stage("image"))
    old["files"]["skills/n2d-review/SKILL.md"] = "outdated"
    up.write_json(up.snapshot_path(str(root)), old)

    plan = up.build_plan(str(root), "第1集")

    assert plan["rebuild_needed"] is False
    assert plan["gate_refresh_needed"] is False
    joined = "\n".join(plan["commands"])
    assert "dashboard.py gate" in joined
    assert "--stage image" in joined
    assert "consistency_audit.py" in joined
    assert any("刷新当前 gate/审查 findings" in note for note in plan["notes"])


def test_rebuild_needed_implies_actionable_rerun_from(tmp_path, monkeypatch):
    # 不变量：artifact 文件变了但映射不到本集已达阶段（rerun_from=None）时，
    # 绝不报 rebuild_needed=True（否则下游拿到无起点的重制指令），转 gate/审查刷新。
    root = make_project(tmp_path)
    _write_content_baseline(
        root, up.relevant_skills_for_stage("image"),
        outdated=["skills/n2d-image/SKILL.md"],  # 本是 artifact 变更
    )
    monkeypatch.setattr(up, "earliest_rerun_stage", lambda *_a, **_k: None)

    plan = up.build_plan(str(root), "第1集")
    assert plan["rerun_from"] is None
    assert plan["rebuild_needed"] is False  # 关键：不再自相矛盾
    assert plan["changed_files"]  # 变更仍如实上报
    # 应路由到 gate/审查刷新，而不是发一条没有起点的重制命令
    assert not any(c.startswith("n2d-image ") for c in plan["commands"])
    assert any("先重跑 gate/审查/计划" in n for n in plan["notes"])


def test_record_writes_snapshot(tmp_path, monkeypatch):
    root = make_project(tmp_path)
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

    plan = up.build_plan(str(root), "第2集")
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

    plan = up.build_plan(str(root), "第1集")
    assert plan["rebuild_needed"] is False
    assert plan["changed_files"] == []
    assert "n2d-image" in plan["newly_relevant_skills"]
    assert any("首次纳入" in note for note in plan["notes"])


def _write_content_baseline(root: Path, skills, *, outdated=()) -> dict:
    """Write a git-free content-hash baseline; `outdated` paths get a stale hash
    so the current repo content differs from baseline (simulates 'changed since')."""
    snap = up.snapshot_for_skills(up.REPO_ROOT, up.REPO_SKILLS, skills)
    snap["kind"] = up.KIND_SNAPSHOT
    for path in outdated:
        snap["files"][path] = "outdated"
    up.write_json(up.snapshot_path(str(root)), snap)
    return snap


def test_record_writes_content_baseline(tmp_path):
    root = make_project(tmp_path)
    snap = up.record(str(root), ["第1集"])
    # 交付铁律：基线是文件内容 SHA256 表，不含任何 git 字段。
    assert isinstance(snap.get("files"), dict) and snap["files"]
    assert "git_commit" not in snap
    assert "dirty_files" not in snap
    assert not any(up.is_test_path(p) for p in snap["files"])


def test_content_baseline_unchanged_reports_nothing(tmp_path):
    root = make_project(tmp_path)
    # record captures current repo content → nothing differs at check time.
    up.record(str(root), ["第1集"])
    plan = up.build_plan(str(root), "第1集")
    assert plan["rebuild_needed"] is False
    assert plan["changed_files"] == []


def test_content_change_is_detected(tmp_path):
    # A file whose content moved off the recorded hash counts as a change.
    root = make_project(tmp_path)
    sb = "skills/n2d-image/SKILL.md"
    _write_content_baseline(root, up.relevant_skills_for_stage("image"), outdated=[sb])
    plan = up.build_plan(str(root), "第1集")
    assert plan["rebuild_needed"] is True
    assert sb in plan["changed_files"]


def test_stale_git_baseline_prompts_rerecord(tmp_path):
    # 旧版 git 派生基线（git_commit、无内容 files 表）在无 git 的交付环境无法 diff，
    # 必须提示重新 record，而不是误判成“无变更”或“git 不可用”。
    root = make_project(tmp_path)
    up.write_json(up.snapshot_path(str(root)), {
        "kind": up.KIND_SNAPSHOT,
        "skills": sorted(up.relevant_skills_for_stage("image")),
        "git_commit": "BASE",
        "dirty_files": {},
    })
    plan = up.build_plan(str(root), "第1集")
    assert plan["rebuild_needed"] is False
    assert any("重新 record" in n for n in plan["notes"])
    assert not any("git" in n.lower() for n in plan["notes"])


def test_test_file_changes_do_not_trigger_rebuild(tmp_path):
    root = make_project(tmp_path)
    # 即便基线里混入了测试文件条目，is_test_path 过滤后也绝不触发重制。
    _write_content_baseline(
        root, up.relevant_skills_for_stage("image"),
        outdated=["skills/n2d-image/scripts/test_legacy.py"],
    )
    plan = up.build_plan(str(root), "第1集")
    assert plan["rebuild_needed"] is False
    assert plan["changed_files"] == []


def test_storyboard_only_change_reruns_from_stage2(tmp_path):
    root = make_project(tmp_path)
    _write_content_baseline(
        root, up.relevant_skills_for_stage("image"),
        outdated=["skills/n2d-script/finalize_storyboard.py"],
    )
    plan = up.build_plan(str(root), "第1集")
    assert plan["rebuild_needed"] is True
    assert plan["rerun_from"] == "script_stage2"


def test_split_change_still_reruns_from_stage1(tmp_path):
    root = make_project(tmp_path)
    _write_content_baseline(
        root, up.relevant_skills_for_stage("image"),
        outdated=["skills/n2d-script/scripts/split_novel.py"],
    )
    plan = up.build_plan(str(root), "第1集")
    assert plan["rebuild_needed"] is True
    assert plan["rerun_from"] == "script_stage1"


def test_no_baseline_reports_needs_record(tmp_path):
    # 无基线（交付环境无 git 可兜底）→ 不报变更，提示先 record。
    root = make_project(tmp_path)
    plan = up.build_plan(str(root), "第1集")
    assert plan["rebuild_needed"] is False
    assert plan["changed_files"] == []
    assert any("record" in n for n in plan["notes"])


def test_newly_relevant_skill_not_counted_as_change(tmp_path):
    # 阶段推进首次纳入的 skill 没有旧基线可比，不算变更（不靠 git 工作区兜底）。
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
    # baseline only covered n2d-image; n2d-video becomes newly relevant at video stage.
    _write_content_baseline(root, ["n2d-image"])
    plan = up.build_plan(str(root), "第1集")
    assert plan["rebuild_needed"] is False
    assert "n2d-video" in plan["newly_relevant_skills"]
    assert any("首次纳入" in n for n in plan["notes"])


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

    plan = up.build_plan(str(root), "第1集")
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
    assert up.read_setting(str(root), "更新重制策略") == "严审刷新"
    assert up.read_setting(str(root), "缺这个键") is None
    # CLI 显式 > 设置 > 默认；旧名「保图刷新」归一到「严审刷新」
    assert up.resolve_regen_mode(str(root), "最小") == "最小"
    assert up.resolve_regen_mode(str(root), None) == "严审刷新"
    assert up.resolve_regen_mode(str(root), "保图刷新") == "严审刷新"
    assert up.resolve_regen_mode(str(tmp_path / "无设置"), None) == "最小"


def test_resolve_regen_mode_reads_global_default(tmp_path) -> None:
    repo = tmp_path / "repo"
    root = repo / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (repo / "skills").mkdir()
    (root / "_设置.md").write_text("- 制作模式：配音先行\n", encoding="utf-8")
    (repo / "创作偏好-默认.md").write_text("- 更新重制策略：严审刷新\n", encoding="utf-8")

    assert up.read_setting(str(root), "更新重制策略") == "严审刷新"
    assert up.resolve_regen_mode(str(root), None) == "严审刷新"


def test_commands_for_strict_image_refresh_shape() -> None:
    cmds = up.commands_for_strict_image_refresh("R", "第1集", "image_prompt", "image")
    joined = "\n".join(cmds)
    assert "--regen-list --strict" in joined   # 按最新标准严审旧图
    assert "--affected-shots --strict" in joined
    assert "--affected-shots" in joined        # 只重生成这些镜
    assert "严审刷新" in joined
    assert "--stage image" in joined           # 末尾验像素
    assert "&&" not in joined                  # 不能用 A && B || echo 掩盖 queue 失败
    assert "if ! shots=$(" in joined
    # 不应出现"整集 --rerun-from image"无 affected 限定的裸重出（避免全部重出）
    assert "--rerun-from image $shots" in joined


def test_strict_image_refresh_only_when_image_covered() -> None:
    # video→compose 不覆盖 image：即便严审刷新模式也走普通命令（无图可审）
    cmds = up.commands_for_strict_image_refresh("R", "第1集", "video", "compose")
    # text_start 退回 image_prompt（封顶），但此函数本身只在覆盖 image 时被 build_plan 调用
    assert any("image_qc" in c for c in cmds)


def test_shared_lock_reuse_when_image_change_misses_production_rules(tmp_path, monkeypatch):
    # n2d-image 分析工具变更未命中定妆库生产规则 → 共享定妆库默认沿用，只重出本集分镜帧。
    root = make_project(tmp_path)
    old = up.snapshot_for_skills(up.REPO_ROOT, up.REPO_SKILLS, up.relevant_skills_for_stage("image"))
    old["files"]["skills/n2d-image/scripts/asset_impact.py"] = "outdated"
    up.write_json(up.snapshot_path(str(root)), old)

    plan = up.build_plan(str(root), "第1集")

    assert plan["rebuild_needed"] is True
    assert plan["shared_lock_reuse"] is True
    assert plan["shared_lock_changed_files"] == []
    assert any("共享定妆库默认沿用" in n for n in plan["notes"])
    assert any("复用共享定妆库" in c for c in plan["commands"])

    md = up.render_markdown(plan)
    assert "共享定妆库：默认沿用" in md


def test_shared_lock_review_when_unknown_image_rules_change(tmp_path, monkeypatch):
    # n2d-image/SKILL.md 可能改定妆生产规则；未知规则变更默认复核共享定妆库，不能静默沿用。
    root = make_project(tmp_path)
    old = up.snapshot_for_skills(up.REPO_ROOT, up.REPO_SKILLS, up.relevant_skills_for_stage("image"))
    old["files"]["skills/n2d-image/SKILL.md"] = "outdated"
    up.write_json(up.snapshot_path(str(root)), old)

    plan = up.build_plan(str(root), "第1集")

    assert plan["rebuild_needed"] is True
    assert plan["shared_lock_reuse"] is False
    assert "skills/n2d-image/SKILL.md" in plan["shared_lock_changed_files"]
    assert any("共享定妆库需复核" in n for n in plan["notes"])


def test_shared_lock_review_when_production_rules_change(tmp_path, monkeypatch):
    # 命中定妆库生产规则（prompt_format 标准三视图铁律）→ 定妆库需复核，非默认沿用。
    root = make_project(tmp_path)
    old = up.snapshot_for_skills(up.REPO_ROOT, up.REPO_SKILLS, up.relevant_skills_for_stage("image"))
    old["files"]["skills/n2d-image/references/prompt_format.md"] = "outdated"
    up.write_json(up.snapshot_path(str(root)), old)

    plan = up.build_plan(str(root), "第1集")

    assert plan["rebuild_needed"] is True
    assert plan["shared_lock_reuse"] is False
    assert "skills/n2d-image/references/prompt_format.md" in plan["shared_lock_changed_files"]
    assert any("共享定妆库需复核" in n for n in plan["notes"])
    assert any("asset_impact.py" in n for n in plan["notes"])

    md = up.render_markdown(plan)
    assert "共享定妆库：需复核" in md


def test_shared_lock_reuse_false_when_image_not_in_rebuild_scope(tmp_path, monkeypatch):
    # 只改 image_qc（gate-only，不重制 PNG）→ image 不进重制范围，无沿用判定。
    root = make_project(tmp_path)
    old = up.snapshot_for_skills(up.REPO_ROOT, up.REPO_SKILLS, up.relevant_skills_for_stage("image"))
    old["files"]["skills/n2d-image/scripts/image_qc.py"] = "outdated"
    up.write_json(up.snapshot_path(str(root)), old)

    plan = up.build_plan(str(root), "第1集")

    assert plan["rebuild_needed"] is False
    assert plan["shared_lock_reuse"] is False


def test_shared_lock_production_touched_only_matches_n2d_image():
    files = [
        "skills/n2d-image/references/prompt_format.md",
        "skills/n2d-image/references/资产身份注册层.md",
        "skills/n2d-image/SKILL.md",
        "skills/n2d-script/references/prompt_format.md",  # 别的 skill 同名片段不算
        "skills/n2d-image/scripts/asset_impact.py",       # 分析工具，非定妆库生产规则
    ]
    hits = up.shared_lock_production_touched(files)
    assert hits == [
        "skills/n2d-image/SKILL.md",
        "skills/n2d-image/references/prompt_format.md",
        "skills/n2d-image/references/资产身份注册层.md",
    ]


def test_n2d_lib_contract_change_triggers_stage_rebuild(tmp_path):
    root = make_project(tmp_path)
    _write_content_baseline(
        root, up.relevant_skills_for_stage("image"),
        outdated=["skills/n2d/_lib/n2d_route.py"],
    )

    plan = up.build_plan(str(root), "第1集")

    assert plan["rebuild_needed"] is True
    assert plan["rerun_from"] == "script_stage1"
    assert "skills/n2d/_lib/n2d_route.py" in plan["changed_files"]


def test_n2d_lib_snapshot_change_is_observe_only(tmp_path):
    root = make_project(tmp_path)
    _write_content_baseline(
        root, up.relevant_skills_for_stage("image"),
        outdated=["skills/n2d/_lib/skill_snapshot.py"],
    )

    plan = up.build_plan(str(root), "第1集")

    assert plan["rebuild_needed"] is False
    assert "skills/n2d/_lib/skill_snapshot.py" in plan["changed_files"]
    assert any("横切层" in n or "刷新当前 gate" in n for n in plan["notes"])


# ── Part 2: update 健康检测（源漂移 / 三帧契约 / 图片一致性）──

def _write_storyboard(root: Path, ep: str, clips, *, video_backend=None):
    import json as _json
    d = root / "脚本" / ep
    d.mkdir(parents=True, exist_ok=True)
    policy = {"tailframe_default": True}
    if video_backend is not None:
        policy["video_backend"] = video_backend
    (d / "storyboard.json").write_text(
        _json.dumps({"episode": 1, "policy": policy, "clips": clips}, ensure_ascii=False),
        encoding="utf-8")


def _clip(cid, *, mid=False, anchors=False, exempt=False):
    cont = {"start_state": "s", "end_state": "e"}
    if mid:
        cont["midframe"] = {"midframe_png": "x.png", "split_at_sec": 2, "reason": "r"}
    if anchors:
        cont["anchors"] = [{"anchor_png": "x.png", "at_sec": 2, "reason": "r"}]
    if exempt:
        cont["midframe_exempt_reason"] = "极短镜 <3s"
    return {"id": cid, "duration": 4.0, "continuity": cont}


def test_three_frame_violation_on_capable_backend(tmp_path):
    root = make_project(tmp_path)
    _write_storyboard(Path(root), "第1集",
                      [_clip("C1"), _clip("C2", mid=True), _clip("C3")], video_backend="即梦")
    r = up.check_three_frame_compliance(root, "第1集")
    assert r["enforced"] is True and r["compliant"] is False
    assert r["violating_clips"] == ["C1", "C3"]


def test_three_frame_empty_anchor_structures_are_not_compliant(tmp_path):
    root = make_project(tmp_path)
    clips = [
        {"id": "C1", "continuity": {"midframe": {}}},
        {"id": "C2", "continuity": {"anchors": []}},
        {"id": "C3", "continuity": {"anchors": [{"reason": "missing path"}]}},
        {"id": "C4", "continuity": {"anchors": [{"anchor_png": "mid.png"}]}},
    ]
    _write_storyboard(Path(root), "第1集", clips, video_backend="即梦")

    r = up.check_three_frame_compliance(root, "第1集")

    assert r["enforced"] is True
    assert r["compliant"] is False
    assert r["violating_clips"] == ["C1", "C2", "C3"]


def test_three_frame_exempt_when_backend_cannot_3plus(tmp_path):
    root = make_project(tmp_path)
    _write_storyboard(Path(root), "第1集", [_clip("C1"), _clip("C2")], video_backend="runway")
    r = up.check_three_frame_compliance(root, "第1集")
    assert r["enforced"] is False and r["compliant"] is True


def test_three_frame_compliant_with_anchors_and_exempt(tmp_path):
    root = make_project(tmp_path)
    _write_storyboard(Path(root), "第1集",
                      [_clip("C1", anchors=True), _clip("C2", exempt=True)], video_backend="dreamina")
    r = up.check_three_frame_compliance(root, "第1集")
    assert r["compliant"] is True and r["violating_clips"] == [] and r["exempt_clips"] == 1


def test_three_frame_none_when_no_storyboard(tmp_path):
    root = make_project(tmp_path)
    assert up.check_three_frame_compliance(root, "第1集") is None


def test_source_drift_none_without_fingerprint(tmp_path):
    root = make_project(tmp_path)
    assert up.detect_source_drift(root) is None  # 无 小说/_源指纹.json → 跳过(不跑 subprocess)


def test_summarize_image_consistency_flags_hard_blocks():
    assert up.summarize_image_consistency(None) is None
    ok = up.summarize_image_consistency({"verdict": "ok", "hard_blocks": 0})
    assert ok["consistent"] is True
    bad = up.summarize_image_consistency({"verdict": "block", "hard_blocks": 3})
    assert bad["consistent"] is False


def test_build_plan_surfaces_three_frame_violation(tmp_path):
    root = make_project(tmp_path)
    _write_storyboard(Path(root), "第1集", [_clip("C1"), _clip("C2")], video_backend="即梦")
    plan = up.build_plan(root, "第1集")
    tf = plan["three_frame_compliance"]
    assert tf and tf["compliant"] is False
    assert any("三帧契约未达标" in n for n in plan["notes"])


def test_invalid_image_qc_report_is_visible_not_clean(tmp_path):
    root = make_project(tmp_path)
    qc_dir = root / "生产数据" / "image_qc" / "第1集"
    qc_dir.mkdir(parents=True)
    (qc_dir / "image_qc_第1集.json").write_text("{bad json", encoding="utf-8")

    plan = up.build_plan(str(root), "第1集")

    assert plan["image_qc_environment"]["status"] == "error"
    assert plan["image_consistency"]["status"] == "error"
    assert plan["image_consistency"]["consistent"] is False
    assert any("图片一致性检测不可用" in n for n in plan["notes"])


def test_json_output_not_polluted_by_smart_suggestions(tmp_path, capsys):
    root = make_project(tmp_path)
    events = root / "生产数据" / "production_events.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        json.dumps({"qa": {"status": "block"}, "meta": {"character_id": "CHAR_01", "backend": "kling"}},
                   ensure_ascii=False)
        for _ in range(3)
    ]
    events.write_text("\n".join(rows) + "\n", encoding="utf-8")
    reg = root / "出图" / "共享" / "identity_registry.json"
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(json.dumps({
        "characters": {
            "CHAR_01": {"name": "小妖", "identity_adapters": {"kling": {"mode": None}}},
        }
    }, ensure_ascii=False), encoding="utf-8")

    rc = up.main(["check", str(root), "第1集", "--json"])

    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["smart_suggestions"][0]["type"] == "upgrade_identity"
