#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import video_production_pack as vpp  # noqa: E402


def _write_project(root: Path) -> None:
    ep = root / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "Clip_01",
            "description": "CHAR_01 打斗冲刺",
            "character_ids": ["CHAR_01"],
            "continuity": {
                "first_frame": "出图/第1集/图片/Clip_01.png",
                "midframe": {"at_sec": 2.0, "midframe_png": "出图/第1集/图片/Clip_01_mid.png"},
                "need_endframe": True,
                "endframe_png": "出图/第1集/图片/Clip_01_end.png",
            },
        }]
    }, ensure_ascii=False), encoding="utf-8")
    route_dir = root / "出视频" / "第1集" / "prompt"
    route_dir.mkdir(parents=True)
    (route_dir / "video_model_routes.json").write_text(json.dumps({
        "kind": "n2d_video_model_routes",
        "routes": [{
            "clip_id": "Clip_01",
            "primary_backend": "dreamina",
            "shot_type": "fight_exchange",
            "risk_flags": ["contact_motion"],
        }],
    }, ensure_ascii=False), encoding="utf-8")
    prod = root / "生产数据"
    prod.mkdir()
    (prod / "spectacle_video_qc_第1集.json").write_text(json.dumps({
        "checks": [{"clip": "Clip_01", "evidence_status": "measured"}]
    }, ensure_ascii=False), encoding="utf-8")


def test_clip_id_normalizes_author_ids_to_clip_nn():
    # 作者自定 id 全部归一化成 Clip_NN（与 router.make_clip_id / image runner 落盘命名同口径）
    assert vpp.clip_id({"id": "镜头3"}, 0) == "Clip_03"
    assert vpp.clip_id({"id": "clip#5"}, 0) == "Clip_05"
    assert vpp.clip_id({"id": "Clip 7"}, 0) == "Clip_07"
    assert vpp.clip_id({"clip_id": "Clip_02"}, 0) == "Clip_02"
    assert vpp.clip_id({"label": "无数字"}, 4) == "Clip_04"  # 无数字 → 退回序号


def test_motion_plan_joins_route_when_storyboard_id_is_raw(tmp_path: Path) -> None:
    # 真凶回归：storyboard 用原始 id「镜头1」，router 路由键已归一化「Clip_01」——
    # 归一化后 join 命中，高动镜拿到 backend/shot_type（修复前 route={} 静默丢路由）。
    ep = tmp_path / "脚本" / "第1集"; ep.mkdir(parents=True)
    (ep / "storyboard.json").write_text(json.dumps({
        "clips": [{"id": "镜头1", "description": "CHAR_01 打斗冲刺", "character_ids": ["CHAR_01"]}]
    }, ensure_ascii=False), encoding="utf-8")
    rd = tmp_path / "出视频" / "第1集" / "prompt"; rd.mkdir(parents=True)
    (rd / "video_model_routes.json").write_text(json.dumps({
        "routes": [{"clip_id": "Clip_01", "primary_backend": "kling",
                    "shot_type": "fight_exchange", "risk_flags": ["contact_motion"]}]
    }, ensure_ascii=False), encoding="utf-8")
    clips = vpp.storyboard(tmp_path, "第1集")
    rows = vpp.routes(tmp_path, "第1集")
    plan = vpp.motion_sample_plan(tmp_path, "第1集", clips, rows)
    assert plan and plan[0]["clip"] == "Clip_01"
    assert plan[0]["route_backend"] == "kling" and plan[0]["shot_type"] == "fight_exchange"


def test_anchor_chain_prefers_storyboard_top_level_frame_paths() -> None:
    chain = vpp.anchor_chain_for_clip("第1集", {
        "id": "EP01_CLIP02",
        "firstframe_png": "出图/第1集/图片/Clip02_first.png",
        "endframe_png": "出图/第1集/图片/Clip02_end.png",
        "continuity": {"need_endframe": True},
    }, 2)

    assert chain["clip"] == "Clip_02"
    assert chain["first_frame"] == "出图/第1集/图片/Clip02_first.png"
    assert chain["last_frame"] == "出图/第1集/图片/Clip02_end.png"


def test_anchor_chain_does_not_treat_explicit_hard_cut_as_relay_tail() -> None:
    chain = vpp.anchor_chain_for_clip("第1集", {
        "id": "Clip_03",
        "continuity": {"seam_mode": "hard_cut", "need_endframe": True},
    }, 3)

    assert chain["seam_mode"] == "hard_cut"
    assert chain["end_anchor_required"] is False
    assert chain["last_frame"] == ""


def test_video_production_pack_builds_anchor_motion_and_route_scores(tmp_path: Path) -> None:
    _write_project(tmp_path)

    pack = vpp.build_pack(tmp_path, "第1集")

    assert pack["kind"] == vpp.KIND
    assert pack["anchor_chains"][0]["anchors"][0]["image"].endswith("_mid.png")
    assert pack["motion_sample_plan"][0]["sample_required"] is True
    row = pack["route_empirical_scorecard"]["rows"][0]
    assert row["backend"] == "dreamina"
    assert row["pass_rate"] == 1.0


def test_video_production_pack_writes_outputs(tmp_path: Path) -> None:
    _write_project(tmp_path)
    pack = vpp.build_pack(tmp_path, "第1集")
    jp, mp = vpp.write_outputs(tmp_path, "第1集", pack)

    assert jp.exists()
    assert mp.exists()
    assert json.loads(jp.read_text(encoding="utf-8"))["kind"] == vpp.KIND
