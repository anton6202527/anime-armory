from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import continuity_chain as cc


def test_normalize_clip_id_prefers_clip_suffix_over_episode_number() -> None:
    assert cc.normalize_clip_id("EP05_CLIP01") == "Clip_01"
    assert cc.normalize_clip_id("EP12-CLIP09") == "Clip_09"


def test_build_chain_keeps_ep_clip_order_distinct() -> None:
    payload = cc.build_chain(
        "第5集",
        [
            {"id": "EP05_CLIP01", "continuity": {"transition": "硬切", "start_state": "A", "end_state": "B"}},
            {"id": "EP05_CLIP02", "continuity": {"transition": "硬切", "start_state": "B", "end_state": "C"}},
        ],
        status="confirmed",
    )

    assert [clip["clip_id"] for clip in payload["clips"]] == ["Clip_01", "Clip_02"]
    assert payload["clips"][0]["source_id"] == "EP05_CLIP01"
    assert payload["seams"][0]["from_clip"] == "Clip_01"
    assert payload["seams"][0]["to_clip"] == "Clip_02"


def test_cross_episode_handoff_alias_satisfies_episode_boundary() -> None:
    payload = cc.build_chain(
        "第5集",
        [
            {
                "id": "EP05_CLIP01",
                "continuity": {
                    "start_state": "接第4集尾帧",
                    "end_state": "拔刀接招",
                    "transition": "match_action_cut",
                    "need_endframe": True,
                    "endframe_png": "出图/第5集/图片/Clip01_end.png",
                    "cross_episode_handoff": {
                        "from_episode": "第4集",
                        "from_clip": "EP04_CLIP11",
                        "prev_tail_frame": "出图/第4集/图片/Clip11_end.png",
                        "handoff_type": "continuous_action_match_cut",
                        "source_frame_required": True,
                    },
                },
                "firstframe_png": "出图/第5集/图片/Clip01_first.png",
            }
        ],
        previous_episode="第4集",
        previous_clips=[
            {
                "id": "EP04_CLIP11",
                "continuity": {
                    "end_state": "青面郎君喊杀了她",
                    "transition": "hard_cut",
                    "need_endframe": True,
                    "seam_mode": "continuous_take_relay",
                    "seam_evidence": {},
                    "endframe_png": "出图/第4集/图片/Clip11_end.png",
                },
            }
        ],
        status="confirmed",
    )

    seam = payload["seams"][0]
    assert seam["scope"] == "episode_boundary"
    assert seam["policy"] == "relay"
    assert seam["severity"] == "pass"


def test_match_on_action_is_mode_specific_not_frame_relay() -> None:
    payload = cc.build_chain(
        "第1集",
        [
            {
                "id": "Clip_01",
                "continuity": {
                    "start_state": "人物举刀",
                    "end_state": "刀锋向画右下劈至中段",
                    "transition": "动作切",
                    "seam_mode": "match_on_action",
                    "seam_evidence": {
                        "action_phase_out": "刀锋下劈中段",
                        "action_phase_in": "下一角度接刀锋下劈后段",
                        "screen_direction": "画左上至画右下",
                    },
                    "need_endframe": False,
                },
            },
            {"id": "Clip_02", "continuity": {"start_state": "另一角度接下劈后段", "end_state": "刀锋命中"}},
        ],
        status="confirmed",
    )
    seam = payload["seams"][0]
    assert seam["seam_mode"] == "match_on_action"
    assert seam["required_boundary_frame"] == ""
    assert seam["severity"] == "pass"
