#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import production_breakdown as pb  # noqa: E402
from signoff_contract import new_manifest, profile_spec, record_approval, write_manifest  # noqa: E402


def _sign_p3(root: Path, ep: str = "第1集") -> None:
    ep_dir = root / "脚本" / ep
    ep_dir.mkdir(parents=True, exist_ok=True)
    for name in ("director_blocking_signoff.json", "animatic_signoff.json"):
        path = ep_dir / name
        if not path.exists():
            path.write_text('{"status":"approved"}', encoding="utf-8")
    spec = profile_spec(root, "p3", ep)
    payload = new_manifest(
        root, artifact_scope=spec["artifact_scope"], episode=ep, author_id="automation:n2d",
        input_paths=spec["input_paths"], evidence_paths=spec["evidence_paths"], required_role_groups=spec["required_role_groups"],
    )
    payload = record_approval(
        payload, root, reviewer_id="user:owner", reviewer_role="producer", evidence_paths=spec["evidence_paths"],
    )
    write_manifest(root / spec["signoff_path"], payload)


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
    for name in [n for n in pb.REQUIRED_FILES if n.endswith(".json")]:
        path = ep_dir / name
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = "confirmed"
        blob = json.dumps(data, ensure_ascii=False).replace("待补", "已填写").replace("TODO", "已填写")
        path.write_text(json.dumps(json.loads(blob), ensure_ascii=False, indent=2), encoding="utf-8")
    call_sheet = (ep_dir / "ai_call_sheet.md").read_text(encoding="utf-8")
    call_sheet = call_sheet.replace("status: draft", "status: confirmed").replace("待补", "已填写")
    (ep_dir / "ai_call_sheet.md").write_text(call_sheet, encoding="utf-8")
    manifest = json.loads((ep_dir / "production_handoff_pack.json").read_text(encoding="utf-8"))
    manifest["status"] = "confirmed"
    (ep_dir / "production_handoff_pack.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _sign_p3(root, ep)


def test_scaffold_creates_production_handoff_files(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)

    result = pb.scaffold(tmp_path, "1")

    assert result["kind"] == pb.KIND
    for name in pb.REQUIRED_FILES:
        assert (tmp_path / "脚本" / "第1集" / name).exists()
    assert (tmp_path / "生产数据" / "ai_shooting_schedule_batch_seed_第1集.json").exists()
    assert (tmp_path / "生产数据" / "production_handoff_pack_第1集.md").exists()
    schedule = json.loads((tmp_path / "脚本" / "第1集" / "ai_shooting_schedule.json").read_text(encoding="utf-8"))
    bible = json.loads((tmp_path / "脚本" / "第1集" / "continuity_bible.json").read_text(encoding="utf-8"))
    assert schedule["tasks"][0]["resource_plan"]["video_backend_slot"]
    assert bible["clips"][0]["state"]["start_state"] == "A 持令牌入画"


def test_scaffold_carries_shot_reverse_continuity_to_bible(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    sb_path = tmp_path / "脚本" / "第1集" / "storyboard.json"
    data = json.loads(sb_path.read_text(encoding="utf-8"))
    data["clips"][0]["template"] = "dialogue_shot_reverse"
    data["clips"][0]["template_contract"] = {
        "template_id": "dialogue_shot_reverse",
        "axis": "A 与 B 连线，摄影机守门口一侧",
        "screen_sides": {"left": "CHAR_A", "right": "CHAR_B"},
        "eyeline": "CHAR_A 看画右，CHAR_B 看画左",
        "shot_pairing": "A clean CU / B OTS reverse CU",
        "coverage_order": "双人建立 → A 面 → B 面反打 → 令牌特写",
        "camera_coverage": "clean single + OTS + insert",
        "lens_height_distance_match": "两侧反打保持相近高度、距离和景别",
        "crossing_axis_policy": "禁止越轴；需要换侧时用令牌特写缓冲",
        "buffer_or_reestablishing": "令牌特写或双人建立镜负责重新定向",
    }
    sb_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    pb.scaffold(tmp_path, "第1集", confirmed=True)
    bible = json.loads((tmp_path / "脚本" / "第1集" / "continuity_bible.json").read_text(encoding="utf-8"))
    contract = bible["clips"][0]["shot_reverse_continuity"]

    assert contract["screen_sides"]["left"] == "CHAR_A"
    assert "禁止越轴" in contract["crossing_axis_policy"]


def test_check_blocks_draft_pack(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    pb.scaffold(tmp_path, "第1集")

    report = pb.check(tmp_path, "第1集")

    assert report["status"] == "block"
    assert report["summary"]["block"] == len(pb.REQUIRED_FILES) + 2


def test_check_passes_confirmed_pack(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    _confirm_pack(tmp_path)

    report = pb.check(tmp_path, "第1集")

    assert report["status"] == "pass"
    assert report["summary"]["pass"] == len(pb.REQUIRED_FILES) + 3
    assert Path(report["check_path"]).is_file()


def test_scaffold_confirm_still_requires_independent_signoff(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)

    pb.scaffold(tmp_path, "第1集", confirmed=True)
    report = pb.check(tmp_path, "第1集")

    assert report["status"] == "block"
    _sign_p3(tmp_path)
    report = pb.check(tmp_path, "第1集")
    assert report["status"] == "pass"
    assert report["summary"]["pass"] == len(pb.REQUIRED_FILES) + 3


def test_scaffold_drops_stale_endframe_when_continuity_exempts_it(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    sb_path = tmp_path / "脚本" / "第1集" / "storyboard.json"
    data = json.loads(sb_path.read_text(encoding="utf-8"))
    data["clips"][0]["endframe_png"] = "出图/第1集/图片/Clip01_end.png"
    data["clips"][0]["continuity"]["need_endframe"] = False
    data["clips"][0]["continuity"]["endframe_exempt_reason"] = "最终镜硬断"
    sb_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    pb.scaffold(tmp_path, "第1集", confirmed=True)
    prod = json.loads((tmp_path / "脚本" / "第1集" / "production_breakdown.json").read_text(encoding="utf-8"))

    req = prod["scene_breakdowns"][0]["image_video_requirements"]
    assert req["endframe"] == ""


def test_scaffold_confirm_does_not_leave_placeholder_for_missing_eyeline(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    sb_path = tmp_path / "脚本" / "第1集" / "storyboard.json"
    data = json.loads(sb_path.read_text(encoding="utf-8"))
    data["clips"][0]["continuity"].pop("eyeline")
    sb_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    pb.scaffold(tmp_path, "第1集", confirmed=True)
    _sign_p3(tmp_path)
    report = pb.check(tmp_path, "第1集")

    assert report["status"] == "pass"
    cont = json.loads((tmp_path / "脚本" / "第1集" / "continuity_breakdown.json").read_text(encoding="utf-8"))
    assert cont["rows"][0]["eyeline"] == "按本场轴线/主体目标方向接力"


def test_scaffold_confirm_fills_missing_knowledge_state(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    sb_path = tmp_path / "脚本" / "第1集" / "storyboard.json"
    data = json.loads(sb_path.read_text(encoding="utf-8"))
    data["clips"][0]["entity_schedule"].pop("knowledge_state")
    sb_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    pb.scaffold(tmp_path, "第1集", confirmed=True)
    _sign_p3(tmp_path)
    report = pb.check(tmp_path, "第1集")

    assert report["status"] == "pass"
    cont = json.loads((tmp_path / "脚本" / "第1集" / "continuity_breakdown.json").read_text(encoding="utf-8"))
    assert "待补" not in json.dumps(cont, ensure_ascii=False)
    assert "不提前知道后续转折" in cont["rows"][0]["knowledge_state"]


def test_check_blocks_stale_handoff_after_storyboard_change(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    pb.scaffold(tmp_path, "第1集", confirmed=True)

    sb_path = tmp_path / "脚本" / "第1集" / "storyboard.json"
    data = json.loads(sb_path.read_text(encoding="utf-8"))
    data["clips"][0]["label"] = "改过的冷开"
    sb_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    report = pb.check(tmp_path, "第1集")

    assert report["status"] == "block"
    manifest = next(row for row in report["files"] if row["rel"].endswith("production_handoff_pack.json"))
    assert any("inputs_fingerprint" in issue for issue in manifest["issues"])


def test_continuity_chain_blocks_relay_without_endframe(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    sb_path = tmp_path / "脚本" / "第1集" / "storyboard.json"
    data = json.loads(sb_path.read_text(encoding="utf-8"))
    data["clips"].append({
        "id": "EP01_CLIP02",
        "label": "接动作反打",
        "duration": 4,
        "scene": "正堂/夜/内",
        "location_id": "LOC_HALL",
        "character_ids": ["CHAR_A", "CHAR_B"],
        "firstframe_png": "出图/第1集/图片/Clip_02.png",
        "continuity": {
            "start_state": "B 后退半步",
            "end_state": "A 举令牌逼问",
            "eyeline": "B 看向 A",
            "transition": "硬切",
        },
        "entity_schedule": {"required_presence": ["CHAR_A", "CHAR_B"]},
    })
    data["clips"][0]["continuity"]["transition"] = "接力"
    data["clips"][0]["continuity"]["need_endframe"] = False
    data["clips"][0]["continuity"].pop("endframe_png", None)
    data["clips"][0].pop("endframe_png", None)
    sb_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    pb.scaffold(tmp_path, "第1集", confirmed=True)
    report = pb.check(tmp_path, "第1集")

    assert report["status"] == "block"
    row = next(r for r in report["files"] if r["rel"].endswith("continuity_chain.json"))
    assert any("relay_without_endframe_flag" in issue for issue in row["issues"])


def test_production_chain_hashes_both_sides_of_relay_boundary(tmp_path: Path) -> None:
    _write_storyboard(tmp_path)
    sb_path = tmp_path / "脚本" / "第1集" / "storyboard.json"
    data = json.loads(sb_path.read_text(encoding="utf-8"))
    boundary_rel = "出图/第1集/图片/relay_boundary.png"
    boundary = tmp_path / boundary_rel
    boundary.parent.mkdir(parents=True)
    boundary.write_bytes(b"same-boundary")
    data["clips"][0]["endframe_png"] = boundary_rel
    data["clips"][0]["continuity"].update({
        "transition": "连续接力", "seam_mode": "continuous_take_relay",
        "seam_evidence": {
            "boundary_frame": boundary_rel,
            "end_state": "B 后退半步",
            "start_state": "B 后退半步",
        },
        "need_endframe": True,
    })
    data["clips"].append({
        "id": "EP01_CLIP02", "label": "接力下半段", "location_id": "LOC_HALL",
        "character_ids": ["CHAR_A", "CHAR_B"], "firstframe_png": boundary_rel,
        "continuity": {"start_state": "B 后退半步", "end_state": "B 站稳", "transition": "hard_cut"},
        "entity_schedule": {"required_presence": ["CHAR_A", "CHAR_B"]},
    })
    sb_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    pb.scaffold(tmp_path, "第1集", confirmed=False)
    chain = json.loads((tmp_path / "脚本" / "第1集" / "continuity_chain.json").read_text(encoding="utf-8"))
    seam = chain["seams"][0]

    assert seam["required_boundary_frame_sha256"] == seam["next_firstframe_sha256"]
    assert seam["required_boundary_frame_sha256"]


def test_cross_episode_boundary_requires_explicit_contract(tmp_path: Path) -> None:
    _write_storyboard(tmp_path, "第1集")
    _write_storyboard(tmp_path, "第2集")

    pb.scaffold(tmp_path, "第2集", confirmed=True)
    _sign_p3(tmp_path, "第2集")
    report = pb.check(tmp_path, "第2集")

    assert report["status"] == "block"
    row = next(r for r in report["files"] if r["rel"].endswith("continuity_chain.json"))
    assert any("missing_episode_boundary_contract" in issue for issue in row["issues"])


def test_cross_episode_intentional_discontinuity_passes(tmp_path: Path) -> None:
    _write_storyboard(tmp_path, "第1集")
    _write_storyboard(tmp_path, "第2集")
    sb_path = tmp_path / "脚本" / "第2集" / "storyboard.json"
    data = json.loads(sb_path.read_text(encoding="utf-8"))
    data["clips"][0]["continuity"]["episode_boundary"] = {
        "intentional_discontinuity_reason": "第2集冷开先切到三日后官道，后续对白补上一集尾钩。",
        "transition_from_previous": "硬切",
    }
    sb_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    pb.scaffold(tmp_path, "第2集", confirmed=True)
    _sign_p3(tmp_path, "第2集")
    report = pb.check(tmp_path, "第2集")

    assert report["status"] == "pass"
    chain = json.loads((tmp_path / "脚本" / "第2集" / "continuity_chain.json").read_text(encoding="utf-8"))
    assert chain["seams"][0]["policy"] == "intentional_discontinuity"
