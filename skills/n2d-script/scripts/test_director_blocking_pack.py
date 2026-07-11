#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import director_blocking_pack as dbp  # noqa: E402
from signoff_contract import new_manifest, profile_spec, record_approval, write_manifest  # noqa: E402


def _confirm_pack(root: Path, ep: str = "第1集") -> None:
    dbp.scaffold(root, ep)
    ep_dir = root / "脚本" / ep
    # P-2 is downstream of table read; unit fixture supplies that upstream receipt.
    (ep_dir / "table_read_signoff.json").write_text('{"status":"approved"}', encoding="utf-8")
    for name in dbp.REQUIRED_FILES:
        path = ep_dir / name
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = "confirmed"
        if name == "transition_map.json":
            for seam in data.get("seams") or []:
                seam["transition_type"] = "hard_cut"
                seam["seam_mode"] = "hard_cut"
                seam["seam_mode_source"] = "explicit"
                seam["seam_evidence"] = {"editorial_intent": "测试确认：以冲击性硬切推进下一拍"}
                seam["need_endframe"] = False
        blob = json.dumps(data, ensure_ascii=False).replace("待补", "已填写")
        path.write_text(json.dumps(json.loads(blob), ensure_ascii=False, indent=2), encoding="utf-8")
    spec = profile_spec(root, "p2", ep)
    payload = new_manifest(
        root, artifact_scope=spec["artifact_scope"], episode=ep, author_id="automation:n2d",
        input_paths=spec["input_paths"], evidence_paths=spec["evidence_paths"], required_role_groups=spec["required_role_groups"],
    )
    payload = record_approval(payload, root, reviewer_id="user:owner", reviewer_role="director", evidence_paths=spec["evidence_paths"])
    payload = record_approval(payload, root, reviewer_id="user:owner", reviewer_role="producer", evidence_paths=spec["evidence_paths"])
    write_manifest(root / spec["signoff_path"], payload)


def test_scaffold_creates_required_director_files(tmp_path: Path) -> None:
    ep_dir = tmp_path / "脚本" / "第1集"
    ep_dir.mkdir(parents=True)
    (ep_dir / "voiceover.txt").write_text("她推门而入。\n他抬头看见令牌。\n", encoding="utf-8")

    result = dbp.scaffold(tmp_path, "1")

    assert result["kind"] == dbp.KIND
    for name in dbp.REQUIRED_FILES:
        assert (tmp_path / "脚本" / "第1集" / name).exists()
    assert (tmp_path / "生产数据" / "director_blocking_pack_第1集.md").exists()


def test_scaffold_from_voiceover_keeps_all_beats(tmp_path: Path) -> None:
    ep_dir = tmp_path / "脚本" / "第1集"
    ep_dir.mkdir(parents=True)
    lines = [f"[镜头{i}·旁白·推进] 第{i}句。" for i in range(1, 13)]
    (ep_dir / "voiceover.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    dbp.scaffold(tmp_path, "第1集")

    beat_sheet = json.loads((ep_dir / "director_beat_sheet.json").read_text(encoding="utf-8"))
    transition_map = json.loads((ep_dir / "transition_map.json").read_text(encoding="utf-8"))
    assert len(beat_sheet["beats"]) == 12
    assert beat_sheet["beats"][-1]["beat_id"] == "Beat_12"
    assert len(transition_map["seams"]) == 11


def test_scaffold_axis_map_uses_storyboard_ids_not_placeholders(tmp_path: Path) -> None:
    ep_dir = tmp_path / "脚本" / "第1集"
    ep_dir.mkdir(parents=True)
    (ep_dir / "voiceover.txt").write_text("她拔刀。\n他后退。\n", encoding="utf-8")
    (ep_dir / "storyboard.json").write_text(json.dumps({
        "visual_contract": {"场景轴线视线": {"main_axis": "CHAR_01 画左，CHAR_02 画右"}},
        "clips": [{
            "id": "EP01_CLIP01",
            "character_ids": ["CHAR_01", "CHAR_02"],
            "location_id": "LOC_01",
            "character_slots": [
                {"character_id": "CHAR_01", "screen_position": "画左前景"},
                {"character_id": "CHAR_02", "screen_position": "画右中景"},
            ],
            "continuity": {"entry_exit": "CHAR_01 入画；CHAR_02 画内保持"},
            "template_contract": {"blocking": "CHAR_01 低位向画右推进，CHAR_02 高位压迫"},
        }],
    }, ensure_ascii=False), encoding="utf-8")

    dbp.scaffold(tmp_path, "第1集")
    data = json.loads((ep_dir / "axis_blocking_map.json").read_text(encoding="utf-8"))
    blob = json.dumps(data, ensure_ascii=False)

    assert "CHAR_xx" not in blob
    assert "LOC_xx" not in blob
    assert "CHAR_01" in blob
    assert "LOC_01" in blob
    assert data["status"] == "draft"


def test_scaffold_axis_map_adds_shot_reverse_pattern(tmp_path: Path) -> None:
    ep_dir = tmp_path / "脚本" / "第1集"
    ep_dir.mkdir(parents=True)
    (ep_dir / "voiceover.txt").write_text("你终于来了。\n我一直在等。\n", encoding="utf-8")
    (ep_dir / "storyboard.json").write_text(json.dumps({
        "visual_contract": {"场景轴线视线": {"main_axis": "CHAR_A 画左，CHAR_B 画右"}},
        "clips": [{
            "id": "EP01_CLIP02",
            "label": "对话正反打",
            "template": "dialogue_shot_reverse",
            "character_ids": ["CHAR_A", "CHAR_B"],
            "location_id": "LOC_HALL",
            "character_slots": [
                {"character_id": "CHAR_A", "screen_position": "画左"},
                {"character_id": "CHAR_B", "screen_position": "画右"},
            ],
            "continuity": {"eyeline": "CHAR_A 看画右，CHAR_B 看画左"},
            "template_contract": {
                "template_id": "dialogue_shot_reverse",
                "axis": "CHAR_A 与 CHAR_B 连线，摄影机守廊柱一侧",
                "eyeline": "CHAR_A 看画右，CHAR_B 看画左",
                "shot_pairing": "A: CHAR_A clean CU / B: CHAR_B OTS reverse CU",
                "blocking": "CHAR_A 画左，CHAR_B 画右",
            },
        }],
    }, ensure_ascii=False), encoding="utf-8")

    dbp.scaffold(tmp_path, "第1集")
    data = json.loads((ep_dir / "axis_blocking_map.json").read_text(encoding="utf-8"))
    pattern = data["shot_reverse_patterns"][0]

    assert pattern["applies_to"] == ["EP01_CLIP02"]
    assert pattern["screen_sides"]["left"] == "CHAR_A"
    assert "越轴" in pattern["crossing_axis_policy"]
    data["status"] = "confirmed"
    (ep_dir / "axis_blocking_map.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    report = dbp.check(tmp_path, "第1集")
    axis_row = next(row for row in report["files"] if row["rel"].endswith("axis_blocking_map.json"))
    assert axis_row["status"] == "pass"
    assert axis_row["issues"] == []


def test_check_blocks_confirmed_axis_map_missing_shot_reverse_pattern(tmp_path: Path) -> None:
    test_scaffold_axis_map_adds_shot_reverse_pattern(tmp_path)
    path = tmp_path / "脚本" / "第1集" / "axis_blocking_map.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["shot_reverse_patterns"] = []
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    report = dbp.check(tmp_path, "第1集")
    axis_row = next(row for row in report["files"] if row["rel"].endswith("axis_blocking_map.json"))

    assert report["status"] == "block"
    assert any("shot_reverse_patterns" in issue for issue in axis_row["issues"])


def test_scaffold_from_storyboard_prefills_but_does_not_self_approve(tmp_path: Path) -> None:
    ep_dir = tmp_path / "脚本" / "第1集"
    ep_dir.mkdir(parents=True)
    (ep_dir / "voiceover.txt").write_text("她拔刀。\n他后退。\n", encoding="utf-8")
    (ep_dir / "storyboard.json").write_text(json.dumps({
        "core_attraction": "赌刀斩妖的升级爽点",
        "first_3s_visual_hook": "插胸长刀与系统金光同时出现",
        "clips": [
            {
                "id": "EP01_CLIP01",
                "duration": 6.2,
                "rhythm": "冷开爆点",
                "dramatic_function": "兑现上一集悬念",
                "audience_effect": "观众确认系统到账",
                "character_ids": ["CHAR_01"],
                "location_id": "LOC_01",
                "subtitle_lines": ["百妖谱亮了。"],
                "character_slots": [{"character_id": "CHAR_01", "screen_position": "中部偏左"}],
                "continuity": {
                    "start_state": "长刀仍在尸身上",
                    "end_state": "金光映入眼底",
                    "shot_size": "CU→ECU",
                    "transition": "cut",
                    "eyeline": "视线锁画右系统面板",
                },
                "template_contract": {
                    "story_function": "交代到账规则",
                    "camera_rule": "先反应再切面板",
                    "post_cue_points": ["3.0s 金光音效"],
                },
            },
            {
                "id": "EP01_CLIP02",
                "duration": 7.1,
                "rhythm": "动作高潮",
                "dramatic_function": "把赌命选择拍清楚",
                "audience_effect": "观众等待刀落结果",
                "character_ids": ["CHAR_01", "CHAR_03"],
                "location_id": "LOC_01",
                "subtitle_lines": ["她把道行压进刀里。"],
                "continuity": {
                    "start_state": "金光映入眼底",
                    "end_state": "刀光逼近虎妖",
                    "shot_size": "MS→CU",
                    "transition": "cut",
                    "eyeline": "反打不越轴",
                },
                "template_contract": {
                    "blocking": "CHAR_01 画左向画右推进，CHAR_03 画右压下",
                    "camera_path": "低角度推近",
                },
            },
        ],
    }, ensure_ascii=False), encoding="utf-8")

    dbp.scaffold(tmp_path, "第1集")
    report = dbp.check(tmp_path, "第1集")
    merged = "".join((ep_dir / name).read_text(encoding="utf-8") for name in dbp.REQUIRED_FILES)

    assert report["status"] == "block"
    assert all(json.loads((ep_dir / name).read_text(encoding="utf-8"))["status"] == "draft" for name in dbp.REQUIRED_FILES)
    assert "EP01_CLIP01" in merged

    _confirm_pack(tmp_path)
    assert dbp.check(tmp_path, "第1集")["status"] == "pass"


def test_check_blocks_draft_pack(tmp_path: Path) -> None:
    dbp.scaffold(tmp_path, "第1集")

    report = dbp.check(tmp_path, "第1集")

    assert report["status"] == "block"
    assert report["summary"]["block"] == len(dbp.REQUIRED_FILES) + 1


def test_check_passes_confirmed_pack(tmp_path: Path) -> None:
    _confirm_pack(tmp_path)

    report = dbp.check(tmp_path, "第1集")

    assert report["status"] == "pass"
    assert report["summary"]["pass"] == len(dbp.REQUIRED_FILES) + 1
    assert Path(report["check_path"]).is_file()


def test_transition_map_rejects_noncanonical_or_mismatched_endframe_mode(tmp_path: Path) -> None:
    _confirm_pack(tmp_path)
    path = tmp_path / "脚本" / "第1集" / "transition_map.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["seams"][0]["seam_mode"] = "动作切一下"
    data["seams"][0]["need_endframe"] = True
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    report = dbp.check(tmp_path, "第1集")
    row = next(item for item in report["files"] if item["rel"].endswith("transition_map.json"))

    assert row["status"] == "block"
    assert any("seam_mode 必须显式选择" in issue for issue in row["issues"])
