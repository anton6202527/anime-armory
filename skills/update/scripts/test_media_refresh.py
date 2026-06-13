import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import media_refresh as m


def _project(tmp_path: Path, family_dir: str, name: str) -> Path:
    root = tmp_path / "repo" / family_dir / name
    root.mkdir(parents=True)
    (tmp_path / "repo" / "skills").mkdir(parents=True, exist_ok=True)
    return root


def test_n2d_media_plan_is_selective_and_reuse_first(tmp_path):
    root = _project(tmp_path, "制漫剧", "测试剧")
    (root / "_进度.md").write_text("# 进度\n", encoding="utf-8")

    plan = m.build_plan(
        str(root),
        line="n2d",
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
    agent_steps = "\n".join(plan["agent_steps"])
    assert '--rerun-from image --affected-shot "Clip_001" --affected-shot "Clip_002"' in agent_steps
    assert '--rerun-from video --affected-shot "Clip_004"' in agent_steps
    assert "显式人工输入" in agent_steps


def test_n2d_media_plan_requires_episode(tmp_path):
    root = _project(tmp_path, "制漫剧", "测试剧")
    (root / "_进度.md").write_text("# 进度\n", encoding="utf-8")

    try:
        m.build_plan(str(root), line="n2d", image_targets=["Clip_001"])
    except SystemExit as exc:
        assert "--episode" in str(exc)
    else:
        raise AssertionError("expected SystemExit")


def test_mv_media_plan_uses_mv_review_and_video_jobs(tmp_path):
    root = _project(tmp_path, "制MV", "测试MV")

    plan = m.build_plan(str(root), line="mv", image_targets=["Clip_001"], video_targets=["Clip_002"])

    assert plan["line"] == "mv"
    joined = "\n".join(plan["commands"])
    assert "mv-review/scripts/mv_check.py" in joined
    assert "mv-video/scripts/video_jobs.py" in joined
    assert "mv-image" in "\n".join(plan["agent_steps"])
    assert "mv-video" in "\n".join(plan["agent_steps"])
    assert "无证据" in "\n".join(plan["agent_steps"])


def test_ad_media_plan_uses_ad_gates_and_contract_inheritance(tmp_path):
    root = _project(tmp_path, "拍广告", "测试广告")

    plan = m.build_plan(str(root), line="ad", image_targets=["Shot_01"], video_targets=["Shot_02"])

    assert plan["line"] == "ad"
    joined = "\n".join(plan["commands"])
    assert "ad-craft/scripts/gate.py" in joined
    assert "ad-video/scripts/inherit_contract.py" in joined
    assert "ad-review/scripts/review.py" in joined
    assert "ad-image" in "\n".join(plan["agent_steps"])
    assert "ad-video" in "\n".join(plan["agent_steps"])
    assert "显式人工输入" in "\n".join(plan["agent_steps"])


def test_song_and_novel_media_are_explicit_noops(tmp_path):
    song = _project(tmp_path, "写歌", "测试歌")
    novel = _project(tmp_path, "写小说", "测试小说")

    song_plan = m.build_plan(str(song), line="song", image_targets=["cover"])
    novel_plan = m.build_plan(str(novel), line="novel", video_targets=["promo"])

    assert song_plan["needs_media_review"] is False
    assert "没有本线图片/视频重制阶段" in song_plan["unsupported_reason"]
    assert novel_plan["needs_media_review"] is False
    assert not novel_plan["commands"]


def test_write_plan_appends_update_run_log(tmp_path):
    root = _project(tmp_path, "制MV", "测试MV")
    plan = m.build_plan(str(root), line="mv", image_targets=["Clip_001"])

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
