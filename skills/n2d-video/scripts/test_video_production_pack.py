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
