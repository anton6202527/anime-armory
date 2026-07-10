#!/usr/bin/env python3
"""Action registry for n2d supervisor/runtime integration.

This module is deliberately data-first.  Stage skills remain the source of
domain work; the registry only describes how a supervisor should wrap each
stage: prework class, stop policy, context pack, creative loop, trace needs and
specialist handoff.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, List


ACTION_SCHEMA_VERSION = 2

AGENT_CREATIVE_STAGES = {"script_stage1", "script_stage2", "image_prompt", "video_prompt"}
PAID_STAGES = {"image", "video", "compose"}

SPECIALISTS: Dict[str, Dict[str, Any]] = {
    "n2d-script-agent": {
        "scope": "剧本改编、分镜设计、题材母题、爽点/钩子/叙事连续性",
        "allowed_stage_keys": ["script_stage1", "script_stage2"],
        "may_execute_paid_work": False,
        "may_write_progress": False,
        "must_use": ["source_comprehension_contract", "context_pack", "creative_loop", "n2d-script references"],
    },
    "n2d-visual-agent": {
        "scope": "出图 prompt、视频 prompt、模型路由、身份/资产/运动契约继承",
        "allowed_stage_keys": ["image_prompt", "image", "video_prompt", "video"],
        "may_execute_paid_work": False,
        "may_write_progress": False,
        "must_use": ["context_pack", "creative_loop for prompt stages", "model_router"],
    },
    "n2d-qc-agent": {
        "scope": "gate、score、review-ui、consistency ledger、返工队列",
        "allowed_stage_keys": ["compose", "review"],
        "may_execute_paid_work": False,
        "may_write_progress": False,
        "must_use": ["post_qc_bundle", "progress_dag", "failure_taxonomy", "release_verdict"],
    },
    "n2d-producer-agent": {
        "scope": "制作模式、合规/花钱放行、batch、dashboard、ROI 和停线判断",
        "allowed_stage_keys": ["voice", "image", "video", "compose"],
        "may_execute_paid_work": False,
        "may_write_progress": False,
        "must_use": ["run.py next", "dashboard", "batch_queue"],
    },
}


def _base(stage_key: str, owner: str, *, specialist: str, stop: str, prework: List[str]) -> Dict[str, Any]:
    paid = stage_key in PAID_STAGES
    creative = stage_key in AGENT_CREATIVE_STAGES
    return {
        "schema_version": ACTION_SCHEMA_VERSION,
        "stage_key": stage_key,
        "owner": owner,
        "specialist": specialist,
        "prework_steps": ["episode_graph", *[step for step in prework if step != "episode_graph"]],
        "requires_context_pack": True,
        "requires_creative_loop": creative,
        "requires_trace": True,
        "requires_human_approval": paid,
        "paid_or_irreversible": paid,
        "stop_policy": stop,
        "supervisor_contract": {
            "may_auto_run_deterministic_prework": True,
            "may_call_specialist": True,
            "may_execute_paid_work": False,
            "may_change_backend_without_adapter": False,
            "may_write_progress_without_stage_verification": False,
        },
    }


STAGE_ACTIONS: Dict[str, Dict[str, Any]] = {
    "script_stage1": _base(
        "script_stage1",
        "n2d-script",
        specialist="n2d-script-agent",
        stop="needs_choice_or_agent_gen",
        prework=[
            "source_check",
            "source_comprehension_gate",
            "update_plan",
            "doctor",
            "development_pack",
            "midstart_context",
            "boundary_audit",
        ],
    ),
    "voice": _base(
        "voice",
        "n2d-voice",
        specialist="n2d-producer-agent",
        stop="needs_payment_confirm",
        prework=["source_check", "update_plan", "doctor", "gate", "compliance"],
    ),
    "script_stage2": _base(
        "script_stage2",
        "n2d-script",
        specialist="n2d-script-agent",
        stop="needs_agent_gen",
        prework=["source_check", "update_plan", "doctor", "episode_promise_gate", "director_blocking_pack"],
    ),
    "image_prompt": _base(
        "image_prompt",
        "n2d-image",
        specialist="n2d-visual-agent",
        stop="needs_agent_gen",
        prework=[
            "source_adaptation_audit",
            "beat_audit",
            "story_economy_audit",
            "spectacle_contract_audit",
            "setup_payoff_gate",
            "series_retention_gate",
            "shot_risk_audit",
            "shot_split_decision",
            "shot_intent_gate",
            "production_breakdown",
            "spectacle_plan",
            "gate",
        ],
    ),
    "image": _base(
        "image",
        "n2d-image",
        specialist="n2d-visual-agent",
        stop="needs_payment_confirm",
        prework=["doctor", "production_breakdown", "reference_slot_gate", "identity", "reference_plan", "image_preflight_gate", "compliance"],
    ),
    "video_prompt": _base(
        "video_prompt",
        "n2d-video",
        specialist="n2d-visual-agent",
        stop="needs_agent_gen",
        prework=[
            "model_router",
            "mouth_visible_audit",
            "spectacle_motion_plan",
            "trajectory_controller_plan",
            "image_qc",
            "interaction_physics_gate",
            "audio_timing_gate",
            "gate",
        ],
    ),
    "video": _base(
        "video",
        "n2d-video",
        specialist="n2d-visual-agent",
        stop="needs_payment_confirm",
        prework=["model_router", "interaction_physics_gate", "audio_timing_gate", "shared_video_materialize", "identity", "image_qc", "video_preflight_gate", "compliance"],
    ),
    "compose": _base(
        "compose",
        "n2d-compose",
        specialist="n2d-qc-agent",
        stop="needs_payment_confirm",
        prework=["audio_timing_gate", "mouth_visible_audit", "shared_video_materialize", "action_edit_cues", "identity", "image_qc", "compose_gate", "compliance"],
    ),
    "review": _base(
        "review",
        "n2d-review",
        specialist="n2d-qc-agent",
        stop="needs_acceptance_signoff",
        prework=[
            "spectacle_video_qc",
            "motion_reference_library",
            "gate",
            "progress_dag",
            "production_breakdown",
            "score",
            "consistency_ledger",
            "review_ui",
            "failure_taxonomy",
            "pilot_release_gate",
            "release_verdict",
        ],
    ),
}


def safe_episode_slug(episode: str) -> str:
    text = str(episode or "全集").strip() or "全集"
    text = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", text)
    return text.strip("_") or "全集"


def stage_action_spec(stage_key: str) -> Dict[str, Any]:
    spec = STAGE_ACTIONS.get(stage_key)
    if spec:
        return deepcopy(spec)
    return {
        "schema_version": ACTION_SCHEMA_VERSION,
        "stage_key": stage_key,
        "owner": "",
        "specialist": "n2d-producer-agent",
        "prework_steps": [],
        "requires_context_pack": True,
        "requires_creative_loop": False,
        "requires_trace": True,
        "requires_human_approval": False,
        "paid_or_irreversible": False,
        "stop_policy": "unknown_stage",
        "supervisor_contract": {
            "may_auto_run_deterministic_prework": True,
            "may_call_specialist": True,
            "may_execute_paid_work": False,
            "may_change_backend_without_adapter": False,
            "may_write_progress_without_stage_verification": False,
        },
    }


def specialist_for_stage(stage_key: str) -> Dict[str, Any]:
    spec = stage_action_spec(stage_key)
    name = spec.get("specialist") or "n2d-producer-agent"
    out = deepcopy(SPECIALISTS.get(name, SPECIALISTS["n2d-producer-agent"]))
    out["name"] = name
    return out


def context_pack_relpath(episode: str, stage_key: str) -> str:
    return f"生产数据/context_packs/context_pack_{safe_episode_slug(episode)}_{stage_key}.json"


def creative_loop_relpath(episode: str, stage_key: str) -> str:
    return f"生产数据/creative_loops/creative_loop_{safe_episode_slug(episode)}_{stage_key}.json"


def all_action_specs() -> List[Dict[str, Any]]:
    return [stage_action_spec(key) for key in STAGE_ACTIONS]


def validate_action_registry() -> List[str]:
    errors: List[str] = []
    for key, spec in STAGE_ACTIONS.items():
        if spec.get("stage_key") != key:
            errors.append(f"{key}: stage_key mismatch")
        specialist = spec.get("specialist")
        if specialist not in SPECIALISTS:
            errors.append(f"{key}: unknown specialist {specialist}")
        contract = spec.get("supervisor_contract") or {}
        if contract.get("may_execute_paid_work"):
            errors.append(f"{key}: supervisor may not execute paid work")
        if key in PAID_STAGES and not spec.get("requires_human_approval"):
            errors.append(f"{key}: paid stage must require human approval")
    return errors
