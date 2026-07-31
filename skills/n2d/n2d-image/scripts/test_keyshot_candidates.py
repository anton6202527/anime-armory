#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import keyshot_candidates as kc  # noqa: E402


def _write_storyboard(root: Path) -> None:
    ep = root / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "storyboard.json").write_text(json.dumps({
        "clips": [
            {"id": "Clip_01", "description": "封面冷开场，女主发现真相。"},
            {"id": "Clip_02", "description": "CHAR_01 与 CHAR_02 多人同框打斗特写。", "character_ids": ["CHAR_01", "CHAR_02"]},
        ]
    }, ensure_ascii=False), encoding="utf-8")


def test_keyshot_candidates_plans_multiple_options(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    sidecar_dir = tmp_path / "出图" / "第1集" / "候选" / "Clip_01"
    sidecar_dir.mkdir(parents=True)
    (sidecar_dir / "candidate_01.json").write_text(json.dumps({
        "candidate": "candidate_01",
        "face_consistency": 0.9,
        "composition": 0.8,
        "hook_strength": 0.9,
    }), encoding="utf-8")

    plan = kc.build_plan(tmp_path, "第1集")

    assert plan["kind"] == kc.KIND
    by_clip = {k["clip"]: k for k in plan["keyshots"]}
    assert by_clip["Clip_01"]["candidate_count"] == 6
    assert by_clip["Clip_02"]["candidate_count"] == 5
    assert by_clip["Clip_01"]["existing_scores"][0]["candidate"] == "candidate_01"


def test_signature_scene_is_top_tier(tmp_path: Path) -> None:
    # 原著名场面/爽点兑现镜 → signature_scene 标签 + 封面级 6 候选 + 跨后端多版兜底建议。
    ep = tmp_path / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "storyboard.json").write_text(json.dumps({
        "clips": [
            {"id": "Clip_01", "description": "当众打脸宿敌，全场震惊，主角逆袭翻盘。"},
            {"id": "Clip_02", "description": "主角走在街上，平淡的过场镜。"},
        ]
    }, ensure_ascii=False), encoding="utf-8")

    plan = kc.build_plan(tmp_path, "第1集")
    by_clip = {k["clip"]: k for k in plan["keyshots"]}

    assert "signature_scene" in by_clip["Clip_01"]["tags"]
    assert by_clip["Clip_01"]["candidate_count"] == 6
    assert any("名场面" in c for c in by_clip["Clip_01"]["selection_criteria"])
    # 平淡过场不应被误升为 signature
    assert "Clip_02" not in by_clip or "signature_scene" not in by_clip["Clip_02"]["tags"]


def test_keyshot_candidates_writes_outputs(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    plan = kc.build_plan(tmp_path, "第1集")
    jp, mp = kc.write_outputs(tmp_path, "第1集", plan)

    assert jp.exists()
    assert mp.exists()
    assert json.loads(jp.read_text(encoding="utf-8"))["kind"] == kc.KIND


def test_classify_ignores_offscreen_character_and_schema_field_names() -> None:
    clip = {
        "id": "Clip_03",
        "description": "主角平静地听画外人说话。",
        "character_ids": ["CHAR_01", "CHAR_02"],
        "entity_schedule": {
            "characters": ["CHAR_01"],
            "offscreen_presence": ["CHAR_02"],
            "forbidden_presence": [],
        },
        "continuity": {"shot_size": "CU", "expression_span": "中"},
        "template_contract": {"character_slots": [], "face_priority": "primary"},
    }

    tags = kc.classify(clip, 3)

    assert "multi_subject" not in tags
    assert "strong_emotion" not in tags
