#!/usr/bin/env python3
"""Canonical editorial seam taxonomy shared by script, video, compose and QA.

A cut is not automatically a continuous-take relay.  Only
``continuous_take_relay`` requires an identical boundary frame.  Other seam
types carry their own executable evidence (action phase, eyeline, audio bridge,
etc.) and intentionally permit different adjacent images.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Sequence, Tuple


VERSION = 1
SEAM_MODES: Tuple[str, ...] = (
    "continuous_take_relay",
    "match_on_action",
    "graphic_match",
    "eyeline_cut",
    "reaction_cut",
    "insert_cutaway",
    "j_cut",
    "l_cut",
    "dissolve",
    "hard_cut",
    "intentional_discontinuity",
)

ALIASES = {
    "relay": "continuous_take_relay",
    "continuous": "continuous_take_relay",
    "continuous_relay": "continuous_take_relay",
    "split_relay": "continuous_take_relay",
    "seamless": "continuous_take_relay",
    "match_action": "match_on_action",
    "action_cut": "match_on_action",
    "match_action_cut": "match_on_action",
    "match_cut": "graphic_match",
    "graphic_cut": "graphic_match",
    "eyeline": "eyeline_cut",
    "reaction": "reaction_cut",
    "insert": "insert_cutaway",
    "cutaway": "insert_cutaway",
    "empty_buffer": "insert_cutaway",
    "fade": "dissolve",
    "crossfade": "dissolve",
    "cut": "hard_cut",
    "jump_cut": "intentional_discontinuity",
}

MODE_PATTERNS: Sequence[Tuple[str, re.Pattern[str]]] = (
    ("intentional_discontinuity", re.compile(r"有意不连续|有意跳切|时间大跳|jump[_ -]?cut|intentional[_ -]?discontinuity", re.I)),
    ("dissolve", re.compile(r"溶解|叠化|淡入|淡出|dissolve|cross[_ -]?fade|fade", re.I)),
    ("j_cut", re.compile(r"\bj[_ -]?cut\b|声音先行|下场声先入", re.I)),
    ("l_cut", re.compile(r"\bl[_ -]?cut\b|声音延续|上场声延续", re.I)),
    ("eyeline_cut", re.compile(r"视线接|eyeline", re.I)),
    ("match_on_action", re.compile(r"动作接|动作切|match[_ -]?(?:on[_ -]?)?action|action[_ -]?cut", re.I)),
    ("graphic_match", re.compile(r"构图匹配|形状匹配|图形匹配|graphic[_ -]?match|match[_ -]?cut", re.I)),
    ("reaction_cut", re.compile(r"反应镜|reaction[_ -]?cut", re.I)),
    ("insert_cutaway", re.compile(r"插入镜|空镜缓冲|物件特写|cutaway|insert|empty[_ -]?buffer", re.I)),
    ("continuous_take_relay", re.compile(r"连续拍|连续动作接力|首尾帧接力|拆段接力|接力|\brelay\b|seamless[_ -]?relay|continuous[_ -]?take|split[_ -]?relay", re.I)),
    ("hard_cut", re.compile(r"硬切|直切|hard[_ -]?cut|\bcut\b", re.I)),
)

MODE_REQUIREMENTS: Dict[str, Tuple[str, ...]] = {
    "continuous_take_relay": ("boundary_frame", "end_state", "start_state"),
    "match_on_action": ("action_phase_out", "action_phase_in", "screen_direction"),
    "graphic_match": ("match_element_out", "match_element_in", "composition_relation"),
    "eyeline_cut": ("eyeline_source", "eyeline_target", "axis"),
    "reaction_cut": ("stimulus", "reaction_subject", "reaction_beat"),
    "insert_cutaway": ("insert_subject", "return_anchor"),
    "j_cut": ("audio_source", "audio_lead_sec"),
    "l_cut": ("audio_source", "audio_tail_sec"),
    "dissolve": ("duration_sec", "editorial_reason"),
    "hard_cut": ("editorial_intent",),
    "intentional_discontinuity": ("reason",),
}


def _canonical(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text in SEAM_MODES:
        return text
    return ALIASES.get(text, "")


def infer_seam_mode(transition: Any, *, need_endframe: bool = False) -> str:
    text = str(transition or "").strip()
    for mode, pattern in MODE_PATTERNS:
        if pattern.search(text):
            return mode
    # Legacy projects marked every seam need_endframe=true.  Preserving relay is
    # safer than silently weakening their existing hard contract.
    if need_endframe:
        return "continuous_take_relay"
    return ""


def normalize_seam_mode(value: Any, transition: Any = "", *, need_endframe: bool = False) -> Dict[str, Any]:
    explicit = _canonical(value)
    inferred = infer_seam_mode(transition, need_endframe=need_endframe)
    mode = explicit or inferred
    return {
        "mode": mode,
        "source": "explicit" if explicit else ("legacy_inferred" if inferred else "missing"),
        "recognized": mode in SEAM_MODES,
    }


def requires_boundary_frame(mode: Any) -> bool:
    return _canonical(mode) == "continuous_take_relay"


def needs_end_anchor(value: Mapping[str, Any]) -> bool:
    """Return whether a clip needs an executable last-frame input.

    This is deliberately separate from :func:`requires_boundary_frame`:
    non-relay clips may still use an end anchor for within-shot performance or
    composition control, but that image is never evidence of an identical
    cross-clip boundary.  An explicit ``seam_mode`` wins over legacy
    ``need_endframe`` flags; old projects without taxonomy keep their previous
    behaviour until migrated.
    """
    clip = value if isinstance(value, Mapping) else {}
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else clip
    explicit_mode = clip.get("seam_mode") or cont.get("seam_mode")
    transition = clip.get("transition") or cont.get("transition")
    legacy_need = any(
        clip.get(key) is True or cont.get(key) is True
        for key in ("need_endframe", "need_end_frame", "need_end")
    )
    explicit_anchor = clip.get("end_anchor_required") is True or cont.get("end_anchor_required") is True
    explicit_exemption = bool(clip.get("endframe_exempt_reason") or cont.get("endframe_exempt_reason"))
    explicit_path = any(
        bool(clip.get(key) or cont.get(key))
        for key in ("endframe_png", "end_frame_png", "last_frame", "endframe")
    )
    mode = normalize_seam_mode(
        explicit_mode,
        transition,
        need_endframe=False if str(explicit_mode or "").strip() else legacy_need,
    ).get("mode")
    if str(explicit_mode or "").strip():
        return requires_boundary_frame(mode) or explicit_anchor or (explicit_path and not explicit_exemption)
    return requires_boundary_frame(mode) or legacy_need or explicit_anchor or (explicit_path and not explicit_exemption)


def requirements_for(mode: Any) -> Tuple[str, ...]:
    return MODE_REQUIREMENTS.get(_canonical(mode), ())


def seam_evidence(continuity: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("seam_evidence", "seam_contract", "transition_evidence"):
        value = continuity.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def missing_evidence(mode: Any, evidence: Mapping[str, Any]) -> Tuple[str, ...]:
    missing = []
    for field in requirements_for(mode):
        value = evidence.get(field)
        text = str(value or "").strip().lower()
        if (
            value is None or value == "" or value == [] or value == {}
            or any(marker in text for marker in ("待补", "待定", "todo", "tbd", "pending", "unknown"))
        ):
            missing.append(field)
    return tuple(missing)


def compose_decision(mode: Any) -> str:
    """Map editorial seam type to the current video concat primitive."""
    canonical = _canonical(mode)
    if canonical == "dissolve":
        return "dissolve"
    if canonical in SEAM_MODES:
        return "cut"
    return "warn"
