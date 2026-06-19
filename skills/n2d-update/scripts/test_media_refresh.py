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


def test_media_plan_warns_when_refreshing_a_locked_anchor(tmp_path):
    root = _project(tmp_path)
    reg = root / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "identity_registry.json").write_text(json.dumps({"characters": [
        {"id": "CHAR_10", "name": "阿离", "forms": [
            {"form": "常态", "anchor_sha": "deadbeef",
             "reference_group": {"front": "出图/共享/图片/定妆_阿离.png"}}]}
    ]}, ensure_ascii=False), encoding="utf-8")
    plan = m.build_plan(root=str(root), episode="第2集", image_targets=["定妆_阿离.png"])
    blob = json.dumps(plan, ensure_ascii=False)
    assert "定妆锚点预警" in blob and "CHAR_10/常态" in blob and "pin-anchor" in blob


def _write_image_qc(root: Path, ep: str, report: dict) -> None:
    d = root / "生产数据" / "image_qc" / ep
    d.mkdir(parents=True, exist_ok=True)
    (d / f"image_qc_{ep}.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")


def _write_contract(root: Path, ep: str, report: dict) -> None:
    d = root / "生产数据"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"contract_inheritance_{ep}.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")


def test_media_preclassifies_targets_from_existing_image_qc(tmp_path):
    root = _project(tmp_path)
    _write_image_qc(root, "第3集", {
        "checks": {"face": {"shots": [
            {"png": "Clip_001首帧.png", "verdict": "block"},
            {"png": "Clip_002首帧.png", "verdict": "ok"},
        ]}},
        "lint": {"findings": [{"shot": "Clip_002", "level": "warn", "code": "构图"}]},
    })
    plan = m.build_plan(str(root), episode="第3集", image_targets=["Clip_001", "Clip_002"])

    # Reports exist → media no longer demands the operator gather evidence from scratch.
    assert plan["needs_decision_evidence"] is False
    ev = plan["evidence"]
    assert ev["any_report_present"] is True
    assert ev["has_block_evidence"] is True
    verdicts = {t["target"]: t["evidence_verdict"] for t in ev["targets"]}
    assert verdicts["Clip_001"] == "block"   # matched by basename
    assert verdicts["Clip_002"] == "warn"    # matched by clip number / lint shot
    notes = "\n".join(plan["notes"])
    assert "命中 block" in notes and "Clip_001" in notes


def test_media_preclassifies_video_targets_from_contract_report(tmp_path):
    root = _project(tmp_path)
    _write_contract(root, "第5集", {
        "identity_handoff": {"findings": [
            {"clip_id": "Clip_004", "severity": "block", "code": "IDENTITY_UNLOCKED"}]},
        "asset_handoff": {"findings": []},
        "fields": [{"field": "光位锚", "status": "drift", "severity": "block"}],
    })
    plan = m.build_plan(str(root), episode="第5集", video_targets=["Clip_004", "Clip_009"])

    ev = plan["evidence"]
    verdicts = {t["target"]: t["evidence_verdict"] for t in ev["targets"]}
    assert verdicts["Clip_004"] == "block"
    assert verdicts["Clip_009"] == "no_evidence"
    assert ev["field_blocks"] == ["光位锚:drift"]
    assert "episode 级字段 block" in "\n".join(plan["notes"])


def test_media_without_reports_stays_review_only(tmp_path):
    root = _project(tmp_path)
    plan = m.build_plan(str(root), episode="第2集", image_targets=["Clip_001"])
    ev = plan["evidence"]
    assert ev["any_report_present"] is False
    assert plan["needs_decision_evidence"] is True
    assert any("media 无证据可预判" in n for n in plan["notes"])


def test_media_plan_no_anchor_warning_for_non_anchor_image(tmp_path):
    root = _project(tmp_path)
    reg = root / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "identity_registry.json").write_text(json.dumps({"characters": [
        {"id": "CHAR_10", "name": "阿离", "forms": [
            {"form": "常态", "reference_group": {"front": "出图/共享/图片/定妆_阿离.png"}}]}
    ]}, ensure_ascii=False), encoding="utf-8")
    plan = m.build_plan(root=str(root), episode="第2集", image_targets=["Clip_007_背景.png"])
    assert "定妆锚点预警" not in json.dumps(plan, ensure_ascii=False)
