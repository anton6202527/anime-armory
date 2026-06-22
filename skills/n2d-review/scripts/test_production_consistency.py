import json
from pathlib import Path

import production_consistency as pc


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_object_permanence_blocks_registered_persistent_prop_drop(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    _write_json(
        root / "脚本" / ep / "storyboard.json",
        {
            "clips": [
                {"id": "Clip_01", "scene": "冷宫寝殿/夜", "action": "沈念手持 PROP_玉簪"},
                {"id": "Clip_02", "scene": "冷宫寝殿/夜", "action": "沈念抬头看向门口"},
            ]
        },
    )
    _write_json(
        root / "出图" / "共享" / "asset_registry.json",
        {"assets": [{"id": "PROP_玉簪", "name": "玉簪", "location": "冷宫寝殿", "persistent": True}]},
    )
    res = pc.check_object_permanence(str(root), ep)
    assert any(row["verdict"] == "block" and row["asset"] == "PROP_玉簪" for row in res["findings"])


def test_interaction_graph_warns_missing_contact_graph_and_blocks_holder_jump(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    _write_json(
        root / "脚本" / ep / "storyboard.json",
        {
            "clips": [
                {"id": "Clip_01", "scene": "冷宫", "action": "沈念手持 PROP_玉簪"},
                {"id": "Clip_02", "scene": "冷宫", "action": "柳娘子手持 PROP_玉簪逼近"},
            ]
        },
    )
    res = pc.check_interaction_graph(str(root), ep)
    messages = "\n".join(row["message"] for row in res["findings"])
    assert "缺 interaction_graph" in messages
    assert any(row["verdict"] == "block" and row.get("asset") == "PROP_玉簪" for row in res["findings"])


def test_state_transition_requires_video_evidence_manifest(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    _write_json(
        root / "脚本" / ep / "storyboard.json",
        {"clips": [{"id": "Clip_01", "scene": "冷宫", "action": "烛火熄灭，沈念脸上的血迹逐渐消失"}]},
    )
    res = pc.check_state_transition_verification(str(root), ep)
    assert any("state_transition_manifest" in row["message"] for row in res["findings"])


def test_possession_ledger_blocks_cross_scene_holder_jump_without_transfer(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    _write_json(
        root / "脚本" / ep / "storyboard.json",
        {
            "clips": [
                {"id": "Clip_01", "scene": "冷宫", "action": "沈念手持 PROP_玉簪退到帘后"},
                {"id": "Clip_02", "scene": "御花园", "action": "柳娘子手持 PROP_玉簪逼近"},
            ]
        },
    )
    res = pc.check_possession_ledger(str(root), ep)
    assert any(row["verdict"] == "block" and row.get("asset") == "PROP_玉簪" for row in res["findings"])


def test_interaction_schema_blocks_high_risk_missing_structured_graph(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    _write_json(
        root / "脚本" / ep / "storyboard.json",
        {"clips": [{"id": "Clip_01", "scene": "冷宫", "action": "沈念刺中柳娘子，柳娘子格挡后推开她"}]},
    )
    res = pc.check_interaction_schema(str(root), ep)
    assert any(row["verdict"] == "block" and "结构化 interaction_graph" in row["message"] for row in res["findings"])


def test_recipe_ledger_derives_hash_and_reports_missing_declared_hash(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    prod = root / "生产数据"
    prod.mkdir()
    event = {
        "kind": "n2d_production_event",
        "episode": ep,
        "stage": "image",
        "event": "generation",
        "source": "n2d-image",
        "generation": {"asset": "出图/第1集/图片/Clip_01.png", "status": "pass"},
        "cost": {"provider": "Codex", "unit": "credits"},
        "meta": {"mode": "codex_exec_image_generation_shot", "logical_seed": "abc", "reference_input_count": "2"},
    }
    (prod / "production_events.jsonl").write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")

    ledger = pc.build_recipe_ledger(str(root), ep)
    assert ledger["rows"][0]["recipe_hash"]
    assert ledger["rows"][0]["declared_recipe_hash"] is False

    res = pc.check_generation_recipe(str(root), ep)
    assert any("declared_recipe_hash" in row["message"] for row in res["findings"])

    strict = pc.check_recipe_schema(str(root), ep)
    assert any("强配方 schema 缺字段" in row["message"] for row in strict["findings"])

    path = pc.write_recipe_ledger(str(root), ep)
    assert Path(path).exists()


def test_final_timeline_probe_required_after_final_cut(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    cut = root / "合成" / ep / "成片_第1集.mp4"
    cut.parent.mkdir(parents=True)
    cut.write_bytes(b"")
    res = pc.check_final_timeline_probe(str(root), ep)
    assert any("final_timeline_probe" in row["message"] for row in res["findings"])


def test_review_calibration_required_when_signoff_exists(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    _write_json(root / "生产数据" / f"human_review_signoff_{ep}.json", {"episode": ep, "reviewer": "qa"})
    res = pc.check_review_calibration(str(root), ep)
    assert any("consistency_calibration.jsonl" in row["message"] for row in res["findings"])


def test_review_calibration_requires_threshold_learning_for_repeated_fp(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    prod = root / "生产数据"
    prod.mkdir()
    _write_json(prod / f"human_review_signoff_{ep}.json", {"episode": ep, "reviewer": "qa"})
    rows = [
        {"label": "false_positive", "dimension": "脸(G1)", "reviewer": "qa", "reason": "遮挡误报", "finding_hash": "a"},
        {"label": "false_positive", "dimension": "脸(G1)", "reviewer": "qa", "reason": "侧脸误报", "finding_hash": "b"},
        {"label": "missed_by_machine", "dimension": "服装配色(N1)", "reviewer": "qa", "reason": "腰带漏检", "finding_hash": "c"},
    ]
    (prod / "consistency_calibration.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    res = pc.check_review_calibration(str(root), ep)
    assert any("阈值/规则没有形成可复跑学习闭环" in row["message"] for row in res["findings"])


def test_probe_pack_requires_required_scenarios_and_baseline(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "脚本" / "第2集").mkdir(parents=True)
    _write_json(
        root / "生产数据" / "consistency_probe_pack.json",
        {"scenarios": [{"scenario": "character_turnaround", "verdict": "pass"}]},
    )
    res = pc.check_probe_pack(str(root), ep)
    messages = "\n".join(row["message"] for row in res["findings"])
    assert "缺哨兵场景" in messages
    assert "baseline/input 指纹" in messages


def test_probe_pack_compares_backend_scores_to_current_route(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    _write_json(
        root / "生产数据" / "video_model_routes.json",
        {"routes": [{"clip_id": "Clip_01", "primary_backend": "SlowGen"}]},
    )
    scenarios = [{"scenario": name, "baseline_hash": f"base-{name}", "verdict": "pass"} for name in pc.PROBE_SCENARIOS]
    _write_json(
        root / "生产数据" / "consistency_probe_pack.json",
        {
            "latest_result": "run-001",
            "scenarios": scenarios,
            "backend_scores": [
                {"scenario": "character_turnaround", "backend": "FastGen", "consistency_score": 0.93},
                {"scenario": "character_turnaround", "backend": "SlowGen", "consistency_score": 0.70},
            ],
        },
    )
    res = pc.check_probe_pack(str(root), ep)
    assert any("高于当前路由" in row["message"] for row in res["findings"])


def test_dialogue_register_fallback_catches_mixed_self_address(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    voice = root / "脚本" / ep / "voiceover.txt"
    voice.parent.mkdir(parents=True)
    voice.write_text("沈念：本宫不会退。\n沈念：俺偏要试试。\n", encoding="utf-8")
    res = pc.check_dialogue_register(str(root), ep)
    assert any("混用" in row["message"] for row in res["findings"])


def test_floorplan_warns_repeated_scene_without_plan(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    _write_json(
        root / "脚本" / ep / "storyboard.json",
        {"clips": [
            {"id": "Clip_01", "scene": "冷宫寝殿/夜"},
            {"id": "Clip_02", "scene": "冷宫寝殿/夜"},
            {"id": "Clip_03", "scene": "冷宫寝殿/夜"},
        ]},
    )
    res = pc.check_floorplan(str(root), ep)
    assert any("缺 scene_floorplan" in row["message"] for row in res["findings"])
