#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import production_breakdown as pb  # noqa: E402


def _write_storyboard(root: Path, ep: str = "第1集") -> None:
    ep_dir = root / "脚本" / ep
    ep_dir.mkdir(parents=True)
    (ep_dir / "storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "EP01_CLIP01",
            "label": "冷开对峙",
            "duration": 5,
            "scene": "正堂/夜/内",
            "location_id": "LOC_HALL",
            "character_ids": ["CHAR_A", "CHAR_B"],
            "object_ids": ["PROP_TOKEN"],
            "dialogue_indices": [1],
            "screen_text_lines": [{"text": "令牌是真的", "render_policy": "compose_overlay_only"}],
            "continuity": {
                "start_state": "A 持令牌入画",
                "end_state": "B 后退半步",
                "eyeline": "A 看向 B",
                "transition": "eyeline",
                "need_endframe": True,
            },
            "entity_schedule": {
                "required_presence": ["CHAR_A", "CHAR_B", "PROP_TOKEN"],
                "knowledge_state": {"CHAR_B": ["知道令牌是真的"]},
            },
        }]
    }, ensure_ascii=False), encoding="utf-8")


def _confirm_pack(root: Path, ep: str = "第1集") -> None:
    pb.scaffold(root, ep)
    ep_dir = root / "脚本" / ep
    for name in ("production_breakdown.json", "continuity_breakdown.json"):
        path = ep_dir / name
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = "confirmed"
        blob = json.dumps(data, ensure_ascii=False).replace("待补", "已填写").replace("TODO", "已填写")
        path.write_text(json.dumps(json.loads(blob), ensure_ascii=False, indent=2), encoding="utf-8")
    call_sheet = (ep_dir / "ai_call_sheet.md").read_text(encoding="utf-8")
    call_sheet = call_sheet.replace("status: draft", "status: confirmed").replace("待补", "已填写")
    (ep_dir / "ai_call_sheet.md").write_text(call_sheet, encoding="utf-8")


def test_scaffold_creates_production_handoff_files(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)

    result = pb.scaffold(tmp_path, "1")

    assert result["kind"] == pb.KIND
    for name in pb.REQUIRED_FILES:
        assert (tmp_path / "脚本" / "第1集" / name).exists()
    assert (tmp_path / "生产数据" / "production_handoff_pack_第1集.md").exists()


def test_check_blocks_draft_pack(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    pb.scaffold(tmp_path, "第1集")

    report = pb.check(tmp_path, "第1集")

    assert report["status"] == "block"
    assert report["summary"]["block"] == len(pb.REQUIRED_FILES)


def test_check_passes_confirmed_pack(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    _confirm_pack(tmp_path)

    report = pb.check(tmp_path, "第1集")

    assert report["status"] == "pass"
    assert report["summary"]["pass"] == len(pb.REQUIRED_FILES)
    assert Path(report["check_path"]).is_file()


def test_scaffold_confirm_can_pass_when_storyboard_is_complete(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)

    pb.scaffold(tmp_path, "第1集", confirmed=True)
    report = pb.check(tmp_path, "第1集")

    assert report["status"] == "pass"
    assert report["summary"]["pass"] == len(pb.REQUIRED_FILES)


def test_scaffold_confirm_does_not_leave_placeholder_for_missing_eyeline(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    sb_path = tmp_path / "脚本" / "第1集" / "storyboard.json"
    data = json.loads(sb_path.read_text(encoding="utf-8"))
    data["clips"][0]["continuity"].pop("eyeline")
    sb_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    pb.scaffold(tmp_path, "第1集", confirmed=True)
    report = pb.check(tmp_path, "第1集")

    assert report["status"] == "pass"
    cont = json.loads((tmp_path / "脚本" / "第1集" / "continuity_breakdown.json").read_text(encoding="utf-8"))
    assert cont["rows"][0]["eyeline"] == "按本场轴线/主体目标方向接力"
