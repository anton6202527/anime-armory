import json
from pathlib import Path

import calibrate_thresholds
import production_consistency as pc
import probe_route_recommend


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


def test_entity_memory_bank_warns_missing_recurrent_entity(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    _write_json(
        root / "脚本" / ep / "storyboard.json",
        {"clips": [
            {"id": "Clip_01", "entity_schedule": {"characters": ["CHAR_SHEN"]}, "action": "CHAR_SHEN 入画"},
            {"id": "Clip_02", "entity_schedule": {"characters": ["CHAR_SHEN"]}, "action": "CHAR_SHEN 回头"},
        ]},
    )
    res = pc.check_entity_memory_bank(str(root), ep)
    assert any("entity_memory_bank" in row["message"] for row in res["findings"])


def test_entity_memory_bank_blocks_rejected_memory_and_requires_core_expression_pack(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    _write_json(
        root / "脚本" / ep / "storyboard.json",
        {"clips": [{"id": "Clip_01", "entity_schedule": {"characters": ["CHAR_SHEN"]}}]},
    )
    _write_json(
        root / "出图" / "共享" / "identity_registry.json",
        {"characters": [{"id": "CHAR_SHEN", "core": True, "forms": [{"form": "常态", "expression_anchors": [{"emotion": "neutral"}]}]}]},
    )
    _write_json(
        root / "生产数据" / "entity_memory_bank.json",
        {"entries": [{"entity_id": "CHAR_SHEN", "source_shot": "Clip_01", "crop_path": "出图/第1集/图片/Clip_01.png", "accepted": False}]},
    )
    res = pc.check_entity_memory_bank(str(root), ep)
    messages = "\n".join(row["message"] for row in res["findings"])
    assert any(row["verdict"] == "block" and "未通过" in row["message"] for row in res["findings"])
    assert "表情锚点少于 3" in messages
    assert "performance_signature" in messages


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


def test_physical_event_graph_requires_attributable_failure(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    _write_json(
        root / "生产数据" / f"physical_event_graph_{ep}.json",
        {"events": [{
            "event_id": "p1",
            "clip": "Clip_01",
            "law": "impenetrability",
            "object_ids": ["PROP_铜镜", "WEAPON_剑"],
            "frame_range": ["00:00:01.000", "00:00:01.400"],
            "expected_state_delta": "剑被铜镜挡住",
            "verdict": "fail",
            "violation_type": "object_interpenetration",
        }]},
    )
    res = pc.check_physical_event_graph(str(root), ep)
    assert any(row["verdict"] == "block" and "object_interpenetration" in row["message"] for row in res["findings"])


def test_video_evidence_completeness_warns_missing_required_sidecars(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    video = root / "出视频" / ep / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"")
    _write_json(
        root / "生产数据" / f"video_eval_manifest_{ep}.json",
        {
            "tasks": [{"clip": "Clip_01", "risk_kinds": ["subject", "physics", "camera"]}],
            "sidecar_targets": {
                "video_vlm": f"生产数据/video_vlm_consistency_{ep}.json",
                "causal_event": f"生产数据/causal_event_graph_{ep}.json",
                "camera": f"生产数据/camera_trajectory_probe_{ep}.json",
            },
        },
    )
    res = pc.check_video_evidence_completeness(str(root), ep)
    assert any("尚未写回" in row["message"] for row in res["findings"])


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


def test_recipe_schema_requires_backend_or_model_version(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    prod = root / "生产数据"
    prod.mkdir()
    event = {
        "kind": "n2d_production_event",
        "episode": ep,
        "stage": "video",
        "event": "generation",
        "source": "n2d-video",
        "generation": {"asset": "出视频/第1集/视频/Clip_01.mp4", "status": "pass"},
        "cost": {"provider": "BackendX"},
        "meta": {
            "mode": "image2video",
            "recipe_hash": "abc",
            "prompt_sha256": "p",
            "reference_bundle_sha256": "r",
            "route_hash": "route",
            "adapter_version": "adapter",
            "qc_version": "qc",
            "seed_support": "unsupported",
        },
    }
    (prod / "production_events.jsonl").write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")
    res = pc.check_recipe_schema(str(root), ep)
    assert any("backend_version/model_version" in row["message"] for row in res["findings"])


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


def test_calibrate_thresholds_writes_recommendations(tmp_path: Path) -> None:
    root = tmp_path
    prod = root / "生产数据"
    prod.mkdir()
    rows = [
        {"label": "false_positive", "dimension": "脸(G1)", "reviewer": "qa", "reason": "遮挡", "finding_hash": "a"},
        {"label": "false_positive", "dimension": "脸(G1)", "reviewer": "qa", "reason": "侧脸", "finding_hash": "b"},
    ]
    (prod / "consistency_calibration.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    path = calibrate_thresholds.write_recommendations(str(root))
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert data["recommendations"][0]["dimension"] == "脸(G1)"
    assert data["recommendations"][0]["direction"] == "loosen_threshold_or_add_exemption"


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


def test_probe_route_recommend_writes_best_backend(tmp_path: Path) -> None:
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
    path = probe_route_recommend.write_recommendations(str(root), ep)
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert data["route_recommendations"][0]["recommended_backend"] == "FastGen"


def test_dialogue_register_fallback_catches_mixed_self_address(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    voice = root / "脚本" / ep / "voiceover.txt"
    voice.parent.mkdir(parents=True)
    voice.write_text("沈念：本宫不会退。\n沈念：俺偏要试试。\n", encoding="utf-8")
    res = pc.check_dialogue_register(str(root), ep)
    assert any("混用" in row["message"] for row in res["findings"])


def test_dialogue_register_flags_wenbai_mix(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    voice = root / "脚本" / ep / "voiceover.txt"
    voice.parent.mkdir(parents=True)
    # 同角色同集既用文言（在下/告辞）又用市井口语（咋整/玩意）——文白横跳。
    voice.write_text("书生：在下这就告辞了。\n书生：这玩意儿咋整啊。\n", encoding="utf-8")
    res = pc.check_dialogue_register(str(root), ep)
    assert any("文白" in row["message"] for row in res["findings"])


def test_dialogue_register_formality_conflict_and_overlong(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    voice = root / "脚本" / ep / "voiceover.txt"
    voice.parent.mkdir(parents=True)
    voice.write_text("先生：这事儿咋办呗。\n先生：" + "之乎者也" * 8 + "。\n", encoding="utf-8")
    reg = root / "设定库" / "dialogue_register.json"
    reg.parent.mkdir(parents=True)
    reg.write_text(json.dumps({"先生": {"formality": "formal", "sentence_len_max": 12}},
                              ensure_ascii=False), encoding="utf-8")
    res = pc.check_dialogue_register(str(root), ep)
    msgs = " ".join(row["message"] for row in res["findings"])
    assert "正式度漂移" in msgs   # 声明 formal 却出现「咋」「呗」市井口语
    assert "句长上限" in msgs     # 第二句远超 12 字


def test_register_pure_helpers() -> None:
    formal, colloq = pc.register_marker_hits(["在下告辞", "这玩意咋整"])
    assert formal and colloq
    assert pc.register_mix_flagged(formal, colloq)
    assert not pc.register_mix_flagged([], colloq)
    assert pc.overlong_lines(["短", "这是一句很长很长很长的台词"], 5) == ["这是一句很长很长很长的台词"]
    assert pc.overlong_lines(["任意"], 0) == []


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


def test_floorplan_requires_spatial_memory_fields_for_reused_location(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    _write_json(
        root / "脚本" / ep / "storyboard.json",
        {"clips": [
            {"id": "Clip_01", "scene": "冷宫寝殿/夜", "action": "沈念在门边"},
            {"id": "Clip_02", "scene": "冷宫寝殿/夜", "action": "反打"},
        ]},
    )
    _write_json(root / "设定库" / "scene_floorplan.json", {"scenes": {"冷宫寝殿": {"zones": ["门边", "床榻"]}}})
    res = pc.check_floorplan(str(root), ep)
    assert any("空间记忆缺字段" in row["message"] for row in res["findings"])


def test_series_packaging_requires_platform_and_brand_fields(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    _write_json(root / "设定库" / "series_packaging.json", {"title_treatment": "金色标题", "cover": "封面模板"})
    res = pc.check_series_packaging(str(root), ep)
    messages = "\n".join(row["message"] for row in res["findings"])
    assert "platform_specs" in messages
    assert "brand_visual" in messages
