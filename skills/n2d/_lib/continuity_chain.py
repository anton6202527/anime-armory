#!/usr/bin/env python3
"""Build n2d per-episode continuity chains.

The chain is the script-supervisor handoff between storyboard/P-3 and video
generation.  It makes every seam explicit: Clip N -> Clip N+1, plus the
previous-episode tail -> current-episode head when available.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

try:
    from seam_contract import missing_evidence, needs_end_anchor, normalize_seam_mode, requires_boundary_frame, seam_evidence
except ImportError:  # pragma: no cover - package import fallback
    from .seam_contract import missing_evidence, needs_end_anchor, normalize_seam_mode, requires_boundary_frame, seam_evidence

KIND = "n2d_continuity_chain"
VERSION = 2

PLACEHOLDER_RE = re.compile(r"(待补|待填写|TODO|TBD|__.+?__|<[^>]+>)", re.I)
EXPLICIT_CLIP_NUM_RE = re.compile(r"(?:clip|镜头)[_\s-]?(\d+)", re.I)
GENERIC_NUM_RE = re.compile(r"(\d+)")

STRICT_TRANSITION_RE = re.compile(
    r"接力|连续|延续|承接|seamless|relay|continuous|continuation|match[_\s-]?cut|"
    r"动作接|动作切|action[_\s-]?cut|视线接|eyeline",
    re.I,
)
DESIGN_CUT_RE = re.compile(
    r"硬切|cut|hard[_\s-]?cut|jump[_\s-]?cut|黑场|fade|dissolve|蒙太奇|montage|"
    r"转场|scene[_\s-]?change|空镜",
    re.I,
)


def normalize_clip_id(value: Any, fallback: int = 0) -> str:
    text = str(value or "").strip()
    match = EXPLICIT_CLIP_NUM_RE.search(text)
    if match:
        num = match.group(1)
        return f"Clip_{int(num):02d}"
    match = GENERIC_NUM_RE.search(text)
    if match:
        num = match.group(1)
        return f"Clip_{int(num):02d}"
    return f"Clip_{fallback:02d}" if fallback else text


def filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        text = value.strip()
        return bool(text) and not PLACEHOLDER_RE.search(text)
    if isinstance(value, Mapping):
        return any(filled(v) for v in value.values())
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(filled(v) for v in value)
    return bool(value)


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    return [str(value)] if str(value).strip() else []


def _cont(clip: Mapping[str, Any]) -> Mapping[str, Any]:
    return clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}


def _entity(clip: Mapping[str, Any]) -> Mapping[str, Any]:
    return clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else {}


def _clip_summary(clip: Mapping[str, Any], idx: int, episode: str) -> Dict[str, Any]:
    cont = _cont(clip)
    entity = _entity(clip)
    cid = normalize_clip_id(clip.get("clip_id") or clip.get("id") or clip.get("label"), idx)
    episode_boundary = cont.get("episode_boundary")
    if not isinstance(episode_boundary, Mapping):
        episode_boundary = cont.get("cross_episode_handoff")
    return {
        "episode": episode,
        "clip_id": cid,
        "source_id": str(clip.get("id") or clip.get("clip_id") or cid),
        "label": str(clip.get("label") or clip.get("scene") or ""),
        "scene": str(clip.get("scene") or ""),
        "location_id": str(clip.get("location_id") or ""),
        "characters": _as_list(clip.get("character_ids")),
        "objects": _as_list(clip.get("object_ids")),
        "required_presence": _as_list(entity.get("required_presence")),
        "offscreen_presence": _as_list(entity.get("offscreen_presence")),
        "forbidden_presence": _as_list(entity.get("forbidden_presence")),
        "entry_exit": str(cont.get("entry_exit") or entity.get("entry_exit") or ""),
        "firstframe_png": str(clip.get("firstframe_png") or cont.get("firstframe_png") or ""),
        "endframe_png": str(clip.get("endframe_png") or cont.get("endframe_png") or cont.get("last_frame") or ""),
        "need_endframe": bool(cont.get("need_endframe") or cont.get("need_end")),
        "end_anchor_required": needs_end_anchor(clip),
        "seam_mode": str(cont.get("seam_mode") or cont.get("cut_mode") or "").strip(),
        "seam_evidence": dict(seam_evidence(cont)),
        "start_state": str(cont.get("start_state") or ""),
        "end_state": str(cont.get("end_state") or ""),
        "transition_to_next": str(cont.get("transition") or "").strip(),
        "episode_boundary": episode_boundary if isinstance(episode_boundary, Mapping) else {},
    }


def _transition_policy(transition: str, need_endframe: bool, seam_mode: str = "") -> str:
    text = str(transition or "").strip()
    mode = normalize_seam_mode(seam_mode, text, need_endframe=need_endframe).get("mode")
    if not text and not mode:
        return "missing"
    if mode == "continuous_take_relay":
        return "relay"
    if mode == "intentional_discontinuity":
        return "intentional_discontinuity"
    if mode:
        return "design_cut"
    if STRICT_TRANSITION_RE.search(text) or need_endframe:
        return "relay"
    return "design_cut" if DESIGN_CUT_RE.search(text) else "missing"


def _boundary_override(to_clip: Mapping[str, Any]) -> Dict[str, Any]:
    boundary = to_clip.get("episode_boundary")
    if not isinstance(boundary, Mapping) or not boundary:
        return {"declared": False}
    reason = str(boundary.get("intentional_discontinuity_reason") or boundary.get("reason") or "").strip()
    handoff_type = str(boundary.get("handoff_type") or "").strip()
    continues = bool(
        boundary.get("continues_from_previous_episode")
        or boundary.get("continue_from_previous_episode")
        or boundary.get("source_frame_required")
        or STRICT_TRANSITION_RE.search(handoff_type)
    )
    transition = str(boundary.get("transition_from_previous") or boundary.get("transition") or handoff_type).strip()
    return {
        "declared": True,
        "continues": continues,
        "intentional_discontinuity_reason": reason,
        "transition": transition,
    }


def _common_entities(left: Mapping[str, Any], right: Mapping[str, Any]) -> List[str]:
    left_set = set(left.get("characters") or []) | set(left.get("objects") or []) | set(left.get("required_presence") or [])
    right_set = set(right.get("characters") or []) | set(right.get("objects") or []) | set(right.get("required_presence") or [])
    return sorted(left_set & right_set)


def _issue(severity: str, code: str, message: str) -> Dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def build_chain(
    episode: str,
    clips: Sequence[Mapping[str, Any]],
    *,
    previous_episode: str = "",
    previous_clips: Optional[Sequence[Mapping[str, Any]]] = None,
    status: str = "draft",
) -> Dict[str, Any]:
    current = [_clip_summary(clip, idx, episode) for idx, clip in enumerate(clips, 1)]
    previous = [
        _clip_summary(clip, idx, previous_episode)
        for idx, clip in enumerate(previous_clips or [], 1)
    ] if previous_episode else []
    seams: List[Dict[str, Any]] = []

    def add_seam(left: Dict[str, Any], right: Dict[str, Any], *, scope: str) -> None:
        boundary = _boundary_override(right) if scope == "episode_boundary" else {"declared": True}
        transition = boundary.get("transition") or left.get("transition_to_next") or ""
        mode_info = normalize_seam_mode(
            left.get("seam_mode"),
            transition,
            need_endframe=bool(left.get("need_endframe")),
        )
        seam_mode = str(mode_info.get("mode") or "")
        evidence = dict(left.get("seam_evidence") or {})
        policy = _transition_policy(str(transition), bool(left.get("need_endframe")), seam_mode)
        issues: List[Dict[str, str]] = []
        if scope == "episode_boundary" and not boundary.get("declared"):
            issues.append(_issue(
                "block",
                "missing_episode_boundary_contract",
                "跨集首镜缺 continuity.episode_boundary：必须声明承接上一集，或写有意跳切理由。",
            ))
        if boundary.get("intentional_discontinuity_reason"):
            policy = "intentional_discontinuity"
            seam_mode = "intentional_discontinuity"
            evidence.setdefault("reason", boundary.get("intentional_discontinuity_reason"))
        elif boundary.get("continues"):
            policy = "relay"
            seam_mode = "continuous_take_relay"
        if mode_info.get("source") != "explicit" and not boundary.get("intentional_discontinuity_reason"):
            issues.append(_issue(
                "block",
                "seam_mode_not_explicit",
                "seam 必须显式分类 seam_mode；旧 transition/need_endframe 推断只用于迁移提示，不能替代导演剪辑决策。",
            ))
        if not filled(transition) and policy != "intentional_discontinuity":
            issues.append(_issue("block", "missing_transition", "seam 缺 transition/转场意图，不能默认硬切或默认接力。"))
        if not filled(left.get("end_state")):
            issues.append(_issue("block", "missing_from_end_state", "上一镜缺 end_state，无法定义接点。"))
        if not filled(right.get("start_state")):
            issues.append(_issue("block", "missing_to_start_state", "下一镜缺 start_state，无法承接上一镜。"))
        if requires_boundary_frame(seam_mode):
            if not left.get("need_endframe"):
                issues.append(_issue("block", "relay_without_endframe_flag", "continuous_take_relay 的上一镜必须 need_endframe=true。"))
            if not filled(left.get("endframe_png")):
                issues.append(_issue("block", "relay_missing_endframe_png", "continuous_take_relay 必须声明 endframe_png/last_frame。"))
            if not filled(right.get("firstframe_png")):
                issues.append(_issue("warn", "relay_missing_firstframe_path", "下一镜缺 firstframe_png 声明；出图 prompt 需补首帧路径。"))
        elif left.get("need_endframe"):
            issues.append(_issue(
                "warn",
                "nonrelay_endframe_optional",
                f"{seam_mode or '未分类'} 不要求相邻帧相同；镜内尾锚应改记 end_anchor_required，不得用 need_endframe 冒充连续 take。",
            ))
        mode_missing = missing_evidence(seam_mode, evidence)
        # Relay frame/start/end evidence is checked by the dedicated strict
        # branch above; report only additional taxonomy-specific fields here.
        if seam_mode == "continuous_take_relay":
            mode_missing = tuple(field for field in mode_missing if field not in {"boundary_frame", "end_state", "start_state"})
        if mode_missing:
            issues.append(_issue(
                "block",
                "missing_seam_mode_evidence",
                f"{seam_mode or 'seam'} 缺模式证据：{', '.join(mode_missing)}。",
            ))
        if (
            policy == "design_cut"
            and left.get("location_id")
            and left.get("location_id") == right.get("location_id")
            and not _common_entities(left, right)
        ):
            issues.append(_issue("warn", "same_location_no_shared_entity", "同场景切镜但无共享在场实体；确认不是误删角色/道具。"))
        entry_exit_parts = [str(left.get("entry_exit") or "").strip(), str(right.get("entry_exit") or "").strip()]
        if left.get("location_id") and right.get("location_id") and left.get("location_id") != right.get("location_id"):
            entry_exit_parts.append(f"换场 {left.get('location_id')} -> {right.get('location_id')}")
        entity_entry_exit = "；".join(part for part in entry_exit_parts if part)
        severity = "block" if any(i["severity"] == "block" for i in issues) else ("warn" if issues else "pass")
        seams.append({
            "scope": scope,
            "from_episode": left.get("episode"),
            "from_clip": left.get("clip_id"),
            "to_episode": right.get("episode"),
            "to_clip": right.get("clip_id"),
            "transition": transition,
            "seam_mode": seam_mode,
            "seam_mode_source": mode_info.get("source"),
            "seam_evidence": evidence,
            "policy": policy,
            "strictness": "strict" if requires_boundary_frame(seam_mode) else "mode_specific",
            "from_end_state": left.get("end_state"),
            "to_start_state": right.get("start_state"),
            "required_boundary_frame": left.get("endframe_png") if requires_boundary_frame(seam_mode) else "",
            "next_firstframe": right.get("firstframe_png"),
            "same_location": bool(left.get("location_id") and left.get("location_id") == right.get("location_id")),
            "common_entities": _common_entities(left, right),
            "entity_entry_exit": entity_entry_exit,
            "intentional_discontinuity_reason": boundary.get("intentional_discontinuity_reason") or "",
            "issues": issues,
            "severity": severity,
        })

    if previous and current:
        add_seam(previous[-1], current[0], scope="episode_boundary")
    for left, right in zip(current, current[1:]):
        add_seam(left, right, scope="intra_episode")

    summary = {
        "clips": len(current),
        "seams": len(seams),
        "episode_boundaries": sum(1 for s in seams if s.get("scope") == "episode_boundary"),
        "relays": sum(1 for s in seams if s.get("policy") == "relay"),
        "seam_modes": {
            mode: sum(1 for s in seams if str(s.get("seam_mode") or "missing") == mode)
            for mode in sorted({str(s.get("seam_mode") or "missing") for s in seams})
        },
        "design_cuts": sum(1 for s in seams if s.get("policy") == "design_cut"),
        "intentional_discontinuities": sum(1 for s in seams if s.get("policy") == "intentional_discontinuity"),
        "block": sum(1 for s in seams if s.get("severity") == "block"),
        "warn": sum(1 for s in seams if s.get("severity") == "warn"),
    }
    return {
        "kind": KIND,
        "version": VERSION,
        "episode": episode,
        "status": status,
        "previous_episode": previous_episode,
        "clips": current,
        "seams": seams,
        "summary": summary,
    }
