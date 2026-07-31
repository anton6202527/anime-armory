from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("shot_reverse_contract.py")
spec = importlib.util.spec_from_file_location("shot_reverse_contract", SCRIPT)
shot_reverse_contract = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(shot_reverse_contract)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_write_contract_backfills_axis_map_and_audits_pass(tmp_path: Path) -> None:
    root = tmp_path
    ep = "第1集"
    _write_json(root / "脚本" / ep / "storyboard.json", {
        "clips": [{
            "id": "EP01_CLIP02",
            "template": "dialogue_shot_reverse",
            "character_ids": ["CHAR_A", "CHAR_B"],
            "location_id": "LOC_HALL",
            "character_slots": [
                {"character_id": "CHAR_A", "screen_position": "画左前景"},
                {"character_id": "CHAR_B", "screen_position": "画右中景"},
            ],
            "continuity": {"eyeline": "CHAR_A 看画右，CHAR_B 看画左；非 POV 镜不看镜头"},
            "template_contract": {
                "template_id": "dialogue_shot_reverse",
                "axis": "CHAR_A 与 CHAR_B 连线，摄影机守殿柱一侧",
                "screen_sides": {"screen_left": "CHAR_A", "screen_right": "CHAR_B"},
                "eyeline": "CHAR_A 看画右，CHAR_B 看画左；非 POV 镜不看镜头",
                "camera_coverage": "clean single + true OTS foreground shoulder + insert",
                "crossing_axis_policy": "禁止越轴；必须先用建立镜或插入镜缓冲。",
                "buffer_or_reestablishing": "殿柱插入、手部 cutaway 或双人建立镜。",
            },
        }],
    })
    _write_json(root / "脚本" / ep / "axis_blocking_map.json", {
        "kind": "n2d_axis_blocking_map",
        "status": "confirmed",
        "shot_reverse_patterns": [],
    })

    contract = shot_reverse_contract.write_contract(root, ep, sync_axis=True)

    assert contract["status"] == "pass"
    assert (root / "脚本" / ep / "shot_reverse_contract.json").exists()
    assert (root / "生产数据" / f"shot_reverse_contract_{ep}.md").exists()
    pattern = contract["patterns"][0]
    assert pattern["participants"]["A"]["character_id"] == "CHAR_A"
    assert "前景肩部" in json.dumps(pattern["coverage"], ensure_ascii=False)

    axis = json.loads((root / "脚本" / ep / "axis_blocking_map.json").read_text(encoding="utf-8"))
    assert axis["shot_reverse_patterns"][0]["applies_to"] == ["EP01_CLIP02"]
    assert axis["shot_reverse_contract_path"] == "脚本/第1集/shot_reverse_contract.json"


def test_camera_gaze_in_non_pov_shot_reverse_blocks(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(tmp_path / "脚本" / ep / "storyboard.json", {
        "clips": [{
            "id": "EP01_CLIP03",
            "template": "dialogue_shot_reverse",
            "character_ids": ["CHAR_A", "CHAR_B"],
            "character_slots": [
                {"character_id": "CHAR_A", "screen_position": "画左"},
                {"character_id": "CHAR_B", "screen_position": "画右"},
            ],
            "description": "CHAR_A 直视镜头说话，CHAR_B 等待反应。",
            "template_contract": {
                "template_id": "dialogue_shot_reverse",
                "screen_sides": {"screen_left": "CHAR_A", "screen_right": "CHAR_B"},
                "eyeline": "CHAR_A 直视镜头，CHAR_B 看画左",
                "camera_coverage": "clean single + OTS foreground shoulder",
                "crossing_axis_policy": "禁止越轴；用插入镜缓冲。",
                "buffer_or_reestablishing": "道具插入。",
            },
        }],
    })

    contract = shot_reverse_contract.build_contract(tmp_path, ep)

    assert contract["status"] == "block"
    assert any(issue["code"] == "camera_gaze_not_allowed" for issue in contract["audit_issues"])


def test_negative_prompt_forbidding_camera_gaze_does_not_block(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(tmp_path / "脚本" / ep / "storyboard.json", {
        "clips": [{
            "id": "EP01_CLIP07",
            "template": "dialogue_shot_reverse",
            "character_ids": ["CHAR_A", "CHAR_B"],
            "character_slots": [
                {"character_id": "CHAR_A", "screen_position": "画左"},
                {"character_id": "CHAR_B", "screen_position": "画右"},
            ],
            "template_contract": {
                "template_id": "dialogue_shot_reverse",
                "screen_sides": {"screen_left": "CHAR_A", "screen_right": "CHAR_B"},
                "eyeline": "CHAR_A 看画右，CHAR_B 看画左",
                "camera_coverage": "clean single + OTS foreground shoulder",
                "crossing_axis_policy": "禁止越轴；用插入镜缓冲。",
                "buffer_or_reestablishing": "道具插入。",
                "negative": ["不要让两人直视镜头", "不要交换左右站位"],
            },
        }],
    })

    contract = shot_reverse_contract.build_contract(tmp_path, ep)

    assert not any(issue["code"] == "camera_gaze_not_allowed" for issue in contract["audit_issues"])


def test_negative_prompt_without_rang_forbidding_camera_gaze_does_not_block(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(tmp_path / "脚本" / ep / "storyboard.json", {
        "clips": [{
            "id": "EP01_CLIP08",
            "template": "reveal_reaction_chain",
            "character_ids": ["CHAR_A", "CHAR_B"],
            "character_slots": [
                {"character_id": "CHAR_A", "screen_position": "画左"},
                {"character_id": "CHAR_B", "screen_position": "画右"},
            ],
            "template_contract": {
                "template_id": "reveal_reaction_chain",
                "screen_sides": {"screen_left": "CHAR_A", "screen_right": "CHAR_B"},
                "eyeline": "CHAR_A 看画右，CHAR_B 看画左",
                "camera_coverage": "clean single + OTS foreground shoulder",
                "crossing_axis_policy": "禁止越轴；用插入镜缓冲。",
                "buffer_or_reestablishing": "道具插入。",
                "negative": ["不要两人直视镜头"],
            },
        }],
    })

    contract = shot_reverse_contract.build_contract(tmp_path, ep)

    assert not any(issue["code"] == "camera_gaze_not_allowed" for issue in contract["audit_issues"])
