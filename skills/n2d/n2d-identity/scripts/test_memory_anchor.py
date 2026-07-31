"""memory_anchor 纯函数单测。
cd skills/n2d/n2d-identity/scripts && python -m pytest test_memory_anchor.py
"""
import memory_anchor as ma
import json


_ANCHORS = {"CHAR_01": ["出图/共享/图片/定妆_沈念_front.png", "出图/共享/图片/定妆_沈念_side.png"]}


def _char(episodes, *, recurrence=None, total_block=0):
    return {"episodes": {e: {} for e in episodes},
            "recurrence": recurrence or {"max_gap": 0, "long_gap_reentries": [], "high_risk": False},
            "total_block": total_block}


def test_long_gap_reentry_triggers_reinject():
    chars = {"CHAR_01": _char(["第1集", "第4集"], recurrence={
        "max_gap": 2, "high_risk": True,
        "long_gap_reentries": [{"at": "第4集", "prev": "第1集", "gap": 2}]})}
    rows = ma.memory_anchor_rows(chars, _ANCHORS, "第4集")
    assert len(rows) == 1
    r = rows[0]
    assert r["reinject"] and "长间隔再登场" in r["reason"]
    assert r["memory_sink_episode"] == "第1集"
    assert r["memory_anchor_refs"][0].endswith("front.png")


def test_late_episode_triggers_reinject_even_without_gap():
    # 连续出场（无长间隔），但距首登场≥5集 → 晚集累积漂移防护
    eps = [f"第{i}集" for i in range(1, 8)]
    chars = {"CHAR_01": _char(eps)}
    rows = ma.memory_anchor_rows(chars, _ANCHORS, "第7集")
    assert rows and "晚集累积漂移" in rows[0]["reason"]


def test_measured_drift_triggers_reinject():
    chars = {"CHAR_01": _char(["第1集", "第2集"], total_block=3)}
    rows = ma.memory_anchor_rows(chars, _ANCHORS, "第2集")
    assert rows and "已测出跨集漂移" in rows[0]["reason"]


def test_early_stable_character_not_reinjected():
    # 第2集、无 gap、无漂移、非晚集 → 不重注入（不无脑刷）
    chars = {"CHAR_01": _char(["第1集", "第2集"])}
    rows = ma.memory_anchor_rows(chars, _ANCHORS, "第2集")
    assert rows == []


def test_char_not_in_target_episode_skipped():
    chars = {"CHAR_01": _char(["第1集", "第4集"], recurrence={
        "max_gap": 2, "high_risk": True,
        "long_gap_reentries": [{"at": "第4集", "prev": "第1集", "gap": 2}]})}
    # 目标第3集，角色本集不出场 → 跳过
    rows = ma.memory_anchor_rows(chars, _ANCHORS, "第3集")
    assert rows == []


def test_char_memory_anchors_extracts_front_first():
    registry = {"characters": [{"name": "沈念", "forms": [{
        "asset_key": "CHAR_SHEN/常态",
        "reference_group": {"front": "a_front.png", "side": "a_side.png",
                            "back": "a_back.png", "outfit": "a_outfit.png"}}]}]}
    anchors = ma.char_memory_anchors(registry)
    assert anchors["CHAR_SHEN/常态"][0] == "a_front.png"
    assert len(anchors["CHAR_SHEN/常态"]) == ma.MAX_MEMORY_REFS  # 截到上限


def test_char_memory_anchors_structured_planned_is_not_ready():
    registry = {"characters": [{"name": "沈念", "forms": [{
        "asset_key": "CHAR_SHEN/常态",
        "reference_group": {
            "front": {"path": "planned_front.png", "status": "planned"},
            "side": {"path": "ready_side.png", "status": "ready"},
        },
    }]}]}
    anchors = ma.char_memory_anchors(registry)
    assert anchors["CHAR_SHEN/常态"] == ["ready_side.png"]


def test_reinject_flagged_even_without_anchor_path():
    # 无定妆锚路径仍标 reinject（参考留空待人补），不静默漏掉长间隔角色
    chars = {"CHAR_09": _char(["第1集", "第5集"], recurrence={
        "max_gap": 3, "high_risk": True,
        "long_gap_reentries": [{"at": "第5集", "prev": "第1集", "gap": 3}]})}
    rows = ma.memory_anchor_rows(chars, {}, "第5集")
    assert rows and rows[0]["reinject"] and rows[0]["memory_anchor_refs"] == []


def test_build_plan_uses_storyboard_appearance_before_current_episode_png_exists(tmp_path):
    root = tmp_path / "剧"
    ref = root / "出图" / "共享" / "图片" / "shen_front.png"
    ref.parent.mkdir(parents=True)
    ref.write_bytes(b"reference")
    registry = {
        "characters": [{
            "id": "CHAR_01",
            "name": "沈念",
            "forms": [{
                "form": "常态",
                "asset_key": "沈念/常态",
                "reference_group": {"front": {"path": "出图/共享/图片/shen_front.png", "status": "ready"}},
            }],
        }],
    }
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    drift_path = root / "生产数据" / "identity_drift_report.json"
    drift_path.parent.mkdir(parents=True)
    drift_path.write_text(json.dumps({
        "available": True,
        "characters": {
            # Historical face tooling still keys by display name; planner must
            # resolve it to the stable registry key.
            "沈念": {"episodes": {"第1集": {}}, "total_block": 0},
        },
    }, ensure_ascii=False), encoding="utf-8")
    storyboard_path = root / "脚本" / "第7集" / "storyboard.json"
    storyboard_path.parent.mkdir(parents=True)
    storyboard_path.write_text(json.dumps({
        "clips": [{
            "clip_id": "Clip_01",
            "entity_schedule": {"characters": ["CHAR_01"]},
        }],
    }, ensure_ascii=False), encoding="utf-8")

    plan = ma.build_plan(str(root), "第7集")

    assert not (root / "出图" / "第7集").exists()  # genuinely pre-generation
    assert plan["available"] is True
    assert plan["target_appearances"] == ["CHAR_01/常态"]
    assert len(plan["rows"]) == 1
    assert plan["rows"][0]["char"] == "CHAR_01/常态"
    assert "长间隔再登场" in plan["rows"][0]["reason"]
    assert plan["rows"][0]["memory_anchor_refs"] == ["出图/共享/图片/shen_front.png"]


def test_explicit_empty_storyboard_appearances_do_not_fall_back_to_drift_current_episode():
    chars = {"CHAR_01/常态": _char(["第1集", "第7集"], total_block=2)}

    rows = ma.memory_anchor_rows(
        chars,
        {"CHAR_01/常态": ["front.png"]},
        "第7集",
        target_appearances=[],
    )

    assert rows == []


def test_storyboard_multi_form_character_requires_exact_form_binding():
    registry = {"characters": [{
        "id": "CHAR_01",
        "name": "沈念",
        "forms": [{"form": "常态"}, {"form": "战损态"}],
    }]}
    ambiguous = {"clips": [{
        "clip_id": "Clip_01",
        "entity_schedule": {"characters": ["CHAR_01"]},
    }]}
    exact = {"clips": [{
        "clip_id": "Clip_01",
        "entity_schedule": {"characters": [{"character_id": "CHAR_01", "form": "战损态"}]},
    }]}

    appearances, errors = ma.storyboard_target_appearance_resolution(ambiguous, registry)
    assert appearances == []
    assert errors and "ambiguous forms" in errors[0]
    assert ma.storyboard_target_appearance_resolution(exact, registry) == (["CHAR_01/战损态"], [])


def test_build_plan_rejects_legacy_name_drift_ambiguous_across_forms(tmp_path):
    root = tmp_path / "剧"
    registry = {"characters": [{
        "id": "CHAR_01",
        "name": "沈念",
        "forms": [{"form": "常态"}, {"form": "战损态"}],
    }]}
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    drift_path = root / "生产数据" / "identity_drift_report.json"
    drift_path.parent.mkdir(parents=True)
    drift_path.write_text(json.dumps({
        "available": True,
        "characters": {"沈念": {"episodes": {"第1集": {}}}},
    }, ensure_ascii=False), encoding="utf-8")
    storyboard_path = root / "脚本" / "第7集" / "storyboard.json"
    storyboard_path.parent.mkdir(parents=True)
    storyboard_path.write_text(json.dumps({"clips": [{
        "clip_id": "Clip_01",
        "entity_schedule": {"characters": [{"character_id": "CHAR_01", "form": "战损态"}]},
    }]}, ensure_ascii=False), encoding="utf-8")

    plan = ma.build_plan(str(root), "第7集")

    assert plan["available"] is False
    assert any(error.startswith("ambiguous_legacy_drift_key:沈念") for error in plan["errors"])


def test_first_visual_episode_accepts_unavailable_empty_drift_as_empty_history(tmp_path):
    root = tmp_path / "剧"
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(json.dumps({"characters": []}), encoding="utf-8")
    drift_path = root / "生产数据" / "identity_drift_report.json"
    drift_path.parent.mkdir(parents=True)
    drift_path.write_text(json.dumps({
        "available": False,
        "characters": {},
        "notes": ["face consistency run skipped by --skip-face"],
    }), encoding="utf-8")
    storyboard_path = root / "脚本" / "第1集" / "storyboard.json"
    storyboard_path.parent.mkdir(parents=True)
    storyboard_path.write_text(json.dumps({"clips": []}), encoding="utf-8")

    plan = ma.build_plan(str(root), "第1集")

    assert plan["available"] is True
    assert plan["rows"] == []
    assert any("空历史" in note for note in plan["notes"])


def test_unavailable_drift_remains_fail_closed_when_prior_episode_png_exists(tmp_path):
    root = tmp_path / "剧"
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(json.dumps({"characters": []}), encoding="utf-8")
    drift_path = root / "生产数据" / "identity_drift_report.json"
    drift_path.parent.mkdir(parents=True)
    drift_path.write_text(json.dumps({"available": False, "characters": {}}), encoding="utf-8")
    storyboard_path = root / "脚本" / "第2集" / "storyboard.json"
    storyboard_path.parent.mkdir(parents=True)
    storyboard_path.write_text(json.dumps({"clips": []}), encoding="utf-8")
    prior_png = root / "出图" / "第1集" / "图片" / "Clip_01.png"
    prior_png.parent.mkdir(parents=True)
    prior_png.write_bytes(b"historical-pixels")

    plan = ma.build_plan(str(root), "第2集")

    assert plan["available"] is False
    assert any("已有早期集 PNG" in note for note in plan["notes"])


def test_cli_overwrites_stale_ready_plan_with_explicit_unavailable_plan(tmp_path, capsys):
    root = tmp_path / "剧"
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(json.dumps({"characters": []}), encoding="utf-8")
    drift_path = root / "生产数据" / "identity_drift_report.json"
    drift_path.parent.mkdir(parents=True)
    drift_path.write_text(json.dumps({"available": False, "characters": {}}), encoding="utf-8")
    storyboard_path = root / "脚本" / "第2集" / "storyboard.json"
    storyboard_path.parent.mkdir(parents=True)
    storyboard_path.write_text(json.dumps({"clips": []}), encoding="utf-8")
    prior_png = root / "出图" / "第1集" / "图片" / "Clip_01.png"
    prior_png.parent.mkdir(parents=True)
    prior_png.write_bytes(b"historical-pixels")
    output = root / "生产数据" / "memory_anchor_plan_第2集.json"
    output.write_text(json.dumps({"available": True, "status": "ready"}), encoding="utf-8")

    assert ma.main([str(root), "第2集", "--json"]) == 0
    capsys.readouterr()
    current = json.loads(output.read_text(encoding="utf-8"))

    assert current["available"] is False
    assert current["status"] == "warn"
