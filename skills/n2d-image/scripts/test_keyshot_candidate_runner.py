#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import keyshot_candidate_runner as kcr  # noqa: E402


def _write_inputs(root: Path) -> None:
    prompt_dir = root / "出图" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "01_分镜出图.md").write_text(
        "\n".join([
            "## 镜头 1 `EP01_CLIP01`",
            "**目标**：`出图/第1集/图片/Clip01_first.png`",
            "正向 prompt：女主蹲在废土里，手心有微光。",
            "",
        ]),
        encoding="utf-8",
    )
    prod = root / "生产数据"
    prod.mkdir()
    (prod / "keyshot_candidate_plan_第1集.json").write_text(
        json.dumps({
            "kind": "n2d_keyshot_candidate_plan",
            "keyshots": [{
                "clip": "EP01_CLIP01",
                "candidate_count": 6,
                "tags": ["opening", "hero"],
                "selection_criteria": ["蹲姿接触面清楚", "手心微光不糊"],
            }],
        }, ensure_ascii=False),
        encoding="utf-8",
    )


def test_build_candidate_tasks_maps_plan_clip_to_prompt_shot(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    plan = kcr.load_plan(tmp_path, "第1集")

    tasks = kcr.build_candidate_tasks(tmp_path, "第1集", plan, max_candidates_per_clip=2)

    assert len(tasks) == 2
    assert tasks[0]["clip"] == "EP01_CLIP01"
    assert tasks[0]["source_target"].shot == "Clip_01"
    assert tasks[0]["source_target"].rel_path == "出图/第1集/图片/Clip01_first.png"
    assert tasks[0]["target"].shot == "Clip_01_candidate_01"
    assert tasks[0]["target"].rel_path == "出图/第1集/候选/EP01_CLIP01/candidate_01.png"
    assert tasks[1]["target"].rel_path == "出图/第1集/候选/EP01_CLIP01/candidate_02.png"


def test_run_generation_writes_candidates_without_touching_final(tmp_path: Path, monkeypatch) -> None:
    _write_inputs(tmp_path)
    final = tmp_path / "出图" / "第1集" / "图片" / "Clip01_first.png"
    final.parent.mkdir(parents=True)
    final.write_bytes(b"final-frame")

    def fake_process_target(root, episode, target, *, task_id, timeout_sec, dry_run, force):
        path = root / target.rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"candidate-frame")
        return True

    monkeypatch.setattr(kcr.cir, "process_target", fake_process_target)

    summary = kcr.run_generation(
        tmp_path,
        "第1集",
        clips=[],
        max_candidates_per_clip=2,
        limit_clips=None,
        timeout_sec=None,
        dry_run=False,
        force=False,
        stop_on_fail=False,
        skip_preflight=True,
        select_after=False,
        apply_selection=False,
        no_ledger=True,
    )

    assert summary["generated"] == 2
    assert final.read_bytes() == b"final-frame"
    for idx in (1, 2):
        png = tmp_path / "出图" / "第1集" / "候选" / "EP01_CLIP01" / f"candidate_{idx:02d}.png"
        sidecar = png.with_suffix(".json")
        assert png.read_bytes() == b"candidate-frame"
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        assert data["source_target"] == "出图/第1集/图片/Clip01_first.png"
        assert data["status"] == "pass"
