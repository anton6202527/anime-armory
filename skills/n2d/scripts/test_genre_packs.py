from __future__ import annotations

import importlib.util
from pathlib import Path
import json


SCRIPT = Path(__file__).with_name("genre_packs.py")
spec = importlib.util.spec_from_file_location("genre_packs", SCRIPT)
genre_packs = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(genre_packs)


def test_all_genre_packs_validate() -> None:
    payload = genre_packs.validate_all()
    keys = {item["genre_key"] for item in payload["packs"]}

    assert payload["status"] == "pass"
    assert {"xianxia", "xuanhuan", "chuanyue", "urban", "suspense"} <= keys


def test_genre_pack_scene_fields_are_declared() -> None:
    for path in genre_packs.pack_paths():
        result = genre_packs.validate_pack(path)
        assert result["status"] == "pass", result


def test_genre_pack_context_blocks_missing_contract_fields_at_review(tmp_path: Path) -> None:
    episode = "第1集"
    (tmp_path / "_设置.md").write_text("- 题材: 仙侠\n", encoding="utf-8")
    script = tmp_path / "脚本" / episode
    script.mkdir(parents=True)
    (script / "storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "Clip_01",
            "shot_type": "mount_ride",
            "description": "御兽坐骑在山道疾驰",
            "motion_contract": {"screen_direction": "left_to_right"},
        }]
    }, ensure_ascii=False), encoding="utf-8")

    payload = genre_packs.build_context(tmp_path, episode, "review")

    assert payload["genre"]["genre_key"] == "xianxia"
    assert payload["status"] == "fail"
    assert any("mount_contact" in item["missing_fields"] for item in payload["issues"])


def test_genre_pack_context_passes_complete_motion_contract(tmp_path: Path) -> None:
    episode = "第1集"
    (tmp_path / "_设置.md").write_text("- 题材: 仙侠\n", encoding="utf-8")
    script = tmp_path / "脚本" / episode
    script.mkdir(parents=True)
    (script / "storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "Clip_01",
            "shot_type": "mount_ride",
            "description": "御兽坐骑在山道疾驰",
            "motion_contract": {
                "mount_contact": "rider hips locked to saddle",
                "gait_cycle": "four-beat gallop",
                "harness_lock": "reins taut",
                "screen_direction": "left_to_right",
            },
        }]
    }, ensure_ascii=False), encoding="utf-8")

    payload = genre_packs.build_context(tmp_path, episode, "review")
    genre_packs.write_context(tmp_path, episode, "review", payload)

    assert payload["status"] == "pass"
    assert (tmp_path / "生产数据" / f"genre_pack_context_{episode}_review.json").is_file()


def test_write_context_is_semantically_idempotent_across_clock_changes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    episode = "第1集"
    (tmp_path / "_设置.md").write_text("- 题材: 仙侠\n", encoding="utf-8")
    monkeypatch.setattr(genre_packs, "now_iso", lambda: "2026-08-20T00:00:00+00:00")
    first = genre_packs.build_context(tmp_path, episode, "review")
    path = genre_packs.write_context(tmp_path, episode, "review", first)
    first_bytes = path.read_bytes()

    monkeypatch.setattr(genre_packs, "now_iso", lambda: "2026-08-21T00:00:00+00:00")
    second = genre_packs.build_context(tmp_path, episode, "review")
    genre_packs.write_context(tmp_path, episode, "review", second)

    assert path.read_bytes() == first_bytes
    assert json.loads(path.read_text(encoding="utf-8"))["generated_at"] == "2026-08-20T00:00:00+00:00"


def test_system_panel_overlay_template_satisfies_chuanyue_motion_contract(tmp_path: Path) -> None:
    episode = "第1集"
    (tmp_path / "_设置.md").write_text("- 题材: 穿越\n", encoding="utf-8")
    script = tmp_path / "脚本" / episode
    script.mkdir(parents=True)
    (script / "storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "Clip_01",
            "template": "system_panel",
            "description": "百妖谱系统面板在角色视线旁弹出。",
            "continuity": {"entry_exit": "VFX_系统面板入画；角色视线锁面板。"},
            "template_contract": {
                "template_id": "system_panel",
                "blocking": "系统面板悬在角色视线附近，人物与面板分层。",
                "camera_rule": "先角色反应再切面板，面板留干净负空间。",
                "text_layer": "compose_overlay_only",
                "negative": ["不要烤字进视频画面", "不要随机生成乱码汉字"],
            },
        }]
    }, ensure_ascii=False), encoding="utf-8")

    payload = genre_packs.build_context(tmp_path, episode, "video_prompt")

    assert payload["status"] == "pass"
    assert payload["summary"]["active_scenes"] == 1


def test_genre_pack_context_does_not_match_flight_inside_preflight(tmp_path: Path) -> None:
    episode = "第1集"
    (tmp_path / "_设置.md").write_text("- 题材: 仙侠\n", encoding="utf-8")
    script = tmp_path / "脚本" / episode
    script.mkdir(parents=True)
    (script / "storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "Clip_01",
            "description": "video_preflight split relay; no aerial prop appears",
            "continuity": {"midframe_exempt_reason": "video_preflight split relay"},
        }]
    }, ensure_ascii=False), encoding="utf-8")

    payload = genre_packs.build_context(tmp_path, episode, "video")

    assert payload["status"] == "pass"
    assert payload["summary"]["active_scenes"] == 0


def test_composite_genre_matches_every_explicit_pack_in_text_order_without_storyboard(tmp_path: Path) -> None:
    episode = "第1集"
    (tmp_path / "_设置.md").write_text(
        "- 题材: 自定义（系统流+修仙+志怪悬疑）\n",
        encoding="utf-8",
    )

    payload = genre_packs.build_context(tmp_path, episode, "script_stage1")

    # Singular fields remain the priority-1 compatibility view.
    assert payload["genre"]["genre_key"] == "chuanyue"
    assert payload["genre"]["matched_genre_keys"] == ["chuanyue", "xianxia", "suspense"]
    assert payload["summary"]["matched_packs"] == 3
    assert len(payload["pack"]["motion_contract_fields"]) == len(set(payload["pack"]["motion_contract_fields"]))
    assert len(payload["pack"]["qc_focus"]) == len(set(payload["pack"]["qc_focus"]))
    assert payload["summary"]["active_scenes"] == 0
    assert payload["activation"]["state"] == "storyboard_missing"
    assert "已匹配" in payload["activation"]["reason"]

    markdown = genre_packs.render_context_markdown(payload)
    assert "chuanyue, xianxia, suspense" in markdown
    assert "storyboard_missing" in markdown
    assert "未触发" in markdown


def test_composite_genre_activates_scenes_from_all_matched_packs(tmp_path: Path) -> None:
    episode = "第1集"
    (tmp_path / "_设置.md").write_text("- 题材: 系统流+修仙+悬疑\n", encoding="utf-8")
    script = tmp_path / "脚本" / episode
    script.mkdir(parents=True)
    (script / "storyboard.json").write_text(json.dumps({
        "clips": [
            {
                "id": "Clip_01",
                "template": "system_panel",
                "description": "系统面板弹出",
                "template_contract": {
                    "blocking": "角色先反应再看系统面板",
                    "text_layer": "compose_overlay_only",
                    "negative": "不要烤字进视频画面",
                },
            },
            {
                "id": "Clip_02",
                "shot_type": "beast_mount",
                "description": "御兽坐骑疾驰",
                "motion_contract": {
                    "mount_contact": "hips locked to saddle",
                    "gait_cycle": "four-beat gallop",
                    "harness_lock": "reins taut",
                    "screen_direction": "left_to_right",
                },
            },
            {
                "id": "Clip_03",
                "shot_type": "clue_closeup",
                "description": "证物线索特写",
                "action_contract": {"degrade_plan": "lock evidence as a still insert"},
            },
        ],
    }, ensure_ascii=False), encoding="utf-8")

    payload = genre_packs.build_context(tmp_path, episode, "review")

    assert payload["status"] == "pass"
    assert payload["activation"]["state"] == "scene_archetypes_triggered"
    assert payload["summary"]["active_scenes"] == 3
    active_keys = {key for row in payload["active_scene_archetypes"] for key in row["genre_keys"]}
    assert active_keys == {"chuanyue", "xianxia", "suspense"}


def test_duplicate_scene_ids_are_merged_with_stable_field_and_pack_order() -> None:
    matches = [
        {
            "genre_key": "first",
            "pack": {"scene_archetypes": [{
                "id": "shared_scene",
                "label": "共享场景",
                "production_risks": ["risk_a"],
                "required_contract_fields": ["screen_direction", "degrade_plan"],
                "style_binding": "first binding",
            }]},
        },
        {
            "genre_key": "second",
            "pack": {"scene_archetypes": [{
                "id": "shared_scene",
                "label": "共享场景",
                "production_risks": ["risk_a", "risk_b"],
                "required_contract_fields": ["degrade_plan", "parallax_layers"],
                "style_binding": "second binding",
            }]},
        },
    ]

    scenes = genre_packs.compose_scene_archetypes(matches)

    assert len(scenes) == 1
    assert scenes[0]["genre_keys"] == ["first", "second"]
    assert scenes[0]["production_risks"] == ["risk_a", "risk_b"]
    assert scenes[0]["required_contract_fields"] == ["screen_direction", "degrade_plan", "parallax_layers"]
    assert scenes[0]["style_bindings"] == ["first binding", "second binding"]


def test_zhiguai_alone_is_not_guessed_as_an_existing_pack(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 题材: 志怪\n", encoding="utf-8")

    payload = genre_packs.build_context(tmp_path, "第1集", "script_stage1")

    assert genre_packs.normalize_genre_key("志怪") == ""
    assert payload["genre"]["matched"] is False
    assert payload["activation"]["state"] == "genre_unmatched"
