#!/usr/bin/env python3
"""Build n2d per-episode continuity chains.

The chain is the script-supervisor handoff between storyboard/P-3 and video
generation.  It makes every seam explicit: Clip N -> Clip N+1, plus the
previous-episode tail -> current-episode head when available.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

KIND = "n2d_continuity_chain"
VERSION = 1

PLACEHOLDER_RE = re.compile(r"(待补|待填写|TODO|TBD|__.+?__|<[^>]+>)", re.I)
CLIP_NUM_RE = re.compile(r"(?:Clip|CLIP|镜头|_CLIP)[_\s-]?(\d+)|(\d+)")

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
    match = CLIP_NUM_RE.search(text)
    if match:
        num = match.group(1) or match.group(2)
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
        "firstframe_png": str(clip.get("firstframe_png") or cont.get("firstframe_png") or ""),
        "endframe_png": str(clip.get("endframe_png") or cont.get("endframe_png") or cont.get("last_frame") or ""),
        "need_endframe": bool(cont.get("need_endframe") or cont.get("need_end") or cont.get("endframe")),
        "start_state": str(cont.get("start_state") or ""),
        "end_state": str(cont.get("end_state") or ""),
        "transition_to_next": str(cont.get("transition") or "").strip(),
        "episode_boundary": cont.get("episode_boundary") if isinstance(cont.get("episode_boundary"), Mapping) else {},
    }


def _transition_policy(transition: str, need_endframe: bool) -> str:
    text = str(transition or "").strip()
    if not text:
        return "missing"
    if STRICT_TRANSITION_RE.search(text) or need_endframe:
        return "relay"
    if DESIGN_CUT_RE.search(text):
        return "design_cut"
    return "design_cut"


def _boundary_override(to_clip: Mapping[str, Any]) -> Dict[str, Any]:
    boundary = to_clip.get("episode_boundary")
    if not isinstance(boundary, Mapping) or not boundary:
        return {"declared": False}
    reason = str(boundary.get("intentional_discontinuity_reason") or boundary.get("reason") or "").strip()
    continues = bool(boundary.get("continues_from_previous_episode") or boundary.get("continue_from_previous_episode"))
    transition = str(boundary.get("transition_from_previous") or boundary.get("transition") or "").strip()
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
        policy = _transition_policy(str(transition), bool(left.get("need_endframe")))
        issues: List[Dict[str, str]] = []
        if scope == "episode_boundary" and not boundary.get("declared"):
            issues.append(_issue(
                "block",
                "missing_episode_boundary_contract",
                "跨集首镜缺 continuity.episode_boundary：必须声明承接上一集，或写有意跳切理由。",
            ))
        if boundary.get("intentional_discontinuity_reason"):
            policy = "intentional_discontinuity"
        elif boundary.get("continues"):
            policy = "relay"
        if not filled(transition) and policy != "intentional_discontinuity":
            issues.append(_issue("block", "missing_transition", "seam 缺 transition/转场意图，不能默认硬切或默认接力。"))
        if not filled(left.get("end_state")):
            issues.append(_issue("block", "missing_from_end_state", "上一镜缺 end_state，无法定义接点。"))
        if not filled(right.get("start_state")):
            issues.append(_issue("block", "missing_to_start_state", "下一镜缺 start_state，无法承接上一镜。"))
        if policy == "relay":
            if not left.get("need_endframe"):
                issues.append(_issue("block", "relay_without_endframe_flag", "接力 seam 的上一镜必须 need_endframe=true。"))
            if not filled(left.get("endframe_png")):
                issues.append(_issue("block", "relay_missing_endframe_png", "接力 seam 的上一镜必须声明 endframe_png/last_frame。"))
            if not filled(right.get("firstframe_png")):
                issues.append(_issue("warn", "relay_missing_firstframe_path", "下一镜缺 firstframe_png 声明；出图 prompt 需补首帧路径。"))
        if policy == "design_cut" and not _common_entities(left, right) and left.get("location_id") == right.get("location_id"):
            issues.append(_issue("warn", "same_location_no_shared_entity", "同场景切镜但无共享在场实体；确认不是误删角色/道具。"))
        severity = "block" if any(i["severity"] == "block" for i in issues) else ("warn" if issues else "pass")
        seams.append({
            "scope": scope,
            "from_episode": left.get("episode"),
            "from_clip": left.get("clip_id"),
            "to_episode": right.get("episode"),
            "to_clip": right.get("clip_id"),
            "transition": transition,
            "policy": policy,
            "strictness": "strict" if policy == "relay" else "info",
            "from_end_state": left.get("end_state"),
            "to_start_state": right.get("start_state"),
            "required_boundary_frame": left.get("endframe_png") if policy == "relay" else "",
            "next_firstframe": right.get("firstframe_png"),
            "same_location": bool(left.get("location_id") and left.get("location_id") == right.get("location_id")),
            "common_entities": _common_entities(left, right),
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
