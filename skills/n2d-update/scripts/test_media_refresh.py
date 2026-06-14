"""Run from this dir: python3 -m pytest test_media_refresh.py."""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import media_refresh as m
import update_plan as u


def _project(tmp_path: Path, name: str = "测试剧") -> Path:
    root = tmp_path / "repo" / "制漫剧" / name
    root.mkdir(parents=True)
    (tmp_path / "repo" / "skills").mkdir(parents=True, exist_ok=True)
    (root / "_进度.md").write_text("# 进度\n", encoding="utf-8")
    return root


def test_n2d_media_plan_is_selective_and_reuse_first(tmp_path):
    root = _project(tmp_path)

    plan = m.build_plan(
        str(root),
        episode="第3集",
        image_targets=["Clip_001,Clip_002"],
        video_targets=["Clip_004"],
    )

    assert plan["line"] == "n2d"
    assert plan["targets"]["images"] == ["Clip_001", "Clip_002"]
    assert plan["targets"]["videos"] == ["Clip_004"]
    assert "只生成计划" in plan["policy"]["principle"]
    assert plan["needs_decision_evidence"] is True
    assert "不得把 --image/--video/--target 传入值直接解释为坏目标" in plan["decision_boundary"]["must_not"]
    joined = "\n".join(plan["commands"])
    assert "image_qc.py" in joined
    assert "--regen-mode 严审刷新" in joined
    assert "--rerun-from image" not in joined
    assert "--rerun-from video" not in joined
    assert joined.count("--stage video") == 1
    assert "预检" in joined
    agent_steps = "\n".join(plan["agent_steps"])
    assert '--rerun-from image --affected-shot "Clip_001" --affected-shot "Clip_002"' in agent_steps
    assert '--rerun-from video --affected-shot "Clip_004"' in agent_steps
    assert "显式人工输入" in agent_steps
    assert "实际完成视频重出" in agent_steps
    assert "不能把这一步当成已验收" in agent_steps


def test_n2d_media_plan_requires_episode(tmp_path):
    root = _project(tmp_path)

    try:
        m.build_plan(str(root), image_targets=["Clip_001"])
    except SystemExit as exc:
        assert "--episode" in str(exc)
    else:
        raise AssertionError("expected SystemExit")


def test_write_plan_appends_update_run_log(tmp_path):
    root = _project(tmp_path)
    plan = m.build_plan(str(root), episode="第1集", image_targets=["Clip_001"])

    written = m.write_plan(str(root), plan)

    assert Path(written["plan_json"]).exists()
    assert Path(written["plan_md"]).exists()
    log = Path(written["run_log"])
    rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert rows[-1]["mode"] == "media_refresh"
    assert rows[-1]["targets"]["images"] == ["Clip_001"]
    markdown = Path(written["plan_md"]).read_text(encoding="utf-8")
    assert "## 职责边界" in markdown
    assert "无证据规则" in markdown


def test_media_subcommand_wires_into_update_plan(tmp_path, capsys):
    root = _project(tmp_path)

    rc = u.main(["media", str(root), "第2集", "--image", "Clip_001", "--write-plan"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "n2d:" in out
    assert (root / "生产数据" / "media_refresh_plan_第2集.json").exists()
