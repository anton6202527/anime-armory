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
