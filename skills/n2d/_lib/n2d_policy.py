#!/usr/bin/env python3
"""Consistency policy lattice for n2d route and audit decisions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Dict, List

try:
    from n2d_const import CONSISTENCY_POLICY_LATTICE_KIND
except ImportError:  # pragma: no cover - package import fallback
    from .n2d_const import CONSISTENCY_POLICY_LATTICE_KIND


POLICY_PRIORITY_ORDER = (
    "fixed_mode",
    "compliance_capability_evidence",
    "native_voice_fallback",
    "identity_affinity",
    "identity_failure_escalation",
    "motion_control_required",
    "frame_anchor_required",
    "cross_episode_baseline",
    "spectacle_benchmark",
    "spectacle_prior",
    "cost_quality_tier",
    "motion_reference_advisory",
    "multishot_advisory",
)

POLICY_PRIORITY = {name: idx for idx, name in enumerate(POLICY_PRIORITY_ORDER)}

POLICY_DESCRIPTIONS = {
    "fixed_mode": "用户显式固定模型时，项目设置优先于自动路由、先验和 benchmark。",
    "compliance_capability_evidence": "合规、授权和后端硬能力证据优先，缺能力不得用低优先级策略绕过。",
    "native_voice_fallback": "原生音画的说话镜若无法保证声纹一致，先回退 voice-first 或要求补声纹证据。",
    "identity_affinity": "一角一后端亲和/已注册主体优先于跨集 shot_type 基线。",
    "identity_failure_escalation": "身份漂移反复失败时升级锁定强度，优先于成本和快慢档。",
    "motion_control_required": "高风险动作镜的运动控制/拆招契约优先于普通质量档。",
    "frame_anchor_required": "首尾/中帧锚是物理和表情保真的执行契约，不得被 ROI 直接取消。",
    "cross_episode_baseline": "跨集后端基线稳定画风；低于身份亲和，高于 benchmark/先验。",
    "spectacle_benchmark": "小样 probe 的奇观后端推荐可覆盖自动兜底，但不得覆盖更高优先级锁定。",
    "spectacle_prior": "冷启动动作先验只修正通用兜底，不能覆盖已定稿策略。",
    "cost_quality_tier": "成本/速度/质量档只在不破坏一致性契约时生效。",
    "motion_reference_advisory": "运动参考库是增强项，缺失时降级为风险提醒。",
    "multishot_advisory": "多镜单次生成是建议项，跨项目统一切换前不自动改主路由。",
}


def policy_lattice_document() -> Dict[str, Any]:
    """Return the machine-readable single source of truth for n2d policy priority."""
    return {
        "kind": CONSISTENCY_POLICY_LATTICE_KIND,
        "version": 1,
        "priority_order": list(POLICY_PRIORITY_ORDER),
        "policies": [
            {"policy": name, "priority": POLICY_PRIORITY[name], "description": POLICY_DESCRIPTIONS[name]}
            for name in POLICY_PRIORITY_ORDER
        ],
        "rule": "lower priority number wins when policies compete for the same routing or consistency surface",
        "conflict_surfaces": {
            "backend_choice": [
                "fixed_mode",
                "identity_affinity",
                "cross_episode_baseline",
                "spectacle_benchmark",
                "spectacle_prior",
                "cost_quality_tier",
            ],
            "voice_identity": ["compliance_capability_evidence", "native_voice_fallback", "cost_quality_tier"],
            "frame_contract": ["identity_failure_escalation", "motion_control_required", "frame_anchor_required", "cost_quality_tier"],
            "style_grade": ["cross_episode_baseline", "cost_quality_tier"],
        },
    }


def _flag(route: Mapping[str, Any], name: str) -> bool:
    flags = route.get("risk_flags") or []
    return isinstance(flags, Sequence) and not isinstance(flags, (str, bytes)) and name in flags


def _policy_active(route: Mapping[str, Any], context: Mapping[str, Any], policy: str) -> bool:
    if policy == "fixed_mode":
        return str(context.get("routing_mode") or route.get("routing_mode") or "") == "fixed_default"
    if policy == "compliance_capability_evidence":
        return bool(route.get("capability_blocked") or route.get("compliance_blocked") or _flag(route, "capability_mismatch"))
    if policy == "native_voice_fallback":
        return bool(route.get("requires_voice_fallback") or route.get("native_audio_policy") == "native_speech")
    if policy == "identity_affinity":
        return bool(route.get("locked_backend") or route.get("backend_affinity") or route.get("character_backend_conflicts"))
    if policy == "identity_failure_escalation":
        # router 升锁写的 risk_flag 是 `identity_escalated`（router.py escalate_identity_for_failures）；
        # 旧判定只查 `identity_escalation` 键与 `identity_failure_escalation` flag——全仓无人设这两个值，
        # 导致 frame_contract 面最高优先级策略对真实升锁 route 永远 inactive（policy_resolution 审计失明）。
        return bool(
            route.get("identity_escalation")
            or _flag(route, "identity_escalated")
            or _flag(route, "identity_failure_escalation")
        )
    if policy == "motion_control_required":
        motion = route.get("motion_control")
        return isinstance(motion, Mapping) and (motion.get("required") is True or motion.get("level") == "required")
    if policy == "frame_anchor_required":
        anchor = route.get("anchor_consumption")
        motion = route.get("motion_control")
        return (
            isinstance(anchor, Mapping)
            and int(anchor.get("anchor_count") or 0) >= 2
        ) or (isinstance(motion, Mapping) and bool(motion.get("manifest_required")))
    if policy == "cross_episode_baseline":
        return bool(route.get("baseline_anchored") or _flag(route, "baseline_deferred_by_locked_backend"))
    if policy == "spectacle_benchmark":
        return bool(
            route.get("spectacle_benchmark")
            or _flag(route, "spectacle_benchmark_deferred_by_baseline")
            or _flag(route, "spectacle_benchmark_deferred_by_identity")
        )
    if policy == "spectacle_prior":
        return bool(route.get("spectacle_prior") or _flag(route, "spectacle_prior_routed"))
    if policy == "cost_quality_tier":
        return bool(route.get("quality_tier") or route.get("urgency_tier"))
    if policy == "motion_reference_advisory":
        ref = route.get("motion_reference")
        return isinstance(ref, Mapping) and bool(ref.get("applicable"))
    if policy == "multishot_advisory":
        return bool(route.get("multishot_group") or route.get("multishot_reroute_suggestion"))
    return False


def _decision_effect(route: Mapping[str, Any], policy: str) -> str:
    if policy == "fixed_mode":
        return f"primary={route.get('primary_backend')} from explicit fixed routing"
    if policy == "identity_affinity":
        return f"locked_backend={route.get('locked_backend') or route.get('primary_backend')}"
    if policy == "cross_episode_baseline":
        return f"baseline primary={route.get('primary_backend')}"
    if policy == "spectacle_benchmark":
        bench = route.get("spectacle_benchmark") if isinstance(route.get("spectacle_benchmark"), Mapping) else {}
        return f"benchmark recommended={bench.get('recommended_backend') or route.get('primary_backend')}"
    if policy == "spectacle_prior":
        prior = route.get("spectacle_prior") if isinstance(route.get("spectacle_prior"), Mapping) else {}
        return f"prior backend={prior.get('prior_backend') or route.get('primary_backend')}"
    if policy == "native_voice_fallback":
        return f"native_audio_policy={route.get('native_audio_policy')}; fallback={route.get('requires_voice_fallback')}"
    if policy == "motion_control_required":
        motion = route.get("motion_control") if isinstance(route.get("motion_control"), Mapping) else {}
        return f"motion_control={motion.get('level') or motion.get('gate_policy')}"
    if policy == "frame_anchor_required":
        anchor = route.get("anchor_consumption") if isinstance(route.get("anchor_consumption"), Mapping) else {}
        return f"anchors={anchor.get('anchor_count')} consumption={anchor.get('consumption_mode')}"
    if policy == "cost_quality_tier":
        return f"quality={route.get('quality_tier')} urgency={route.get('urgency_tier')}"
    return POLICY_DESCRIPTIONS.get(policy, "")


def route_policy_resolution(route: Mapping[str, Any], context: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Explain which consistency policy won for a final route.

    The router mutates routes in several passes.  This function is deliberately
    side-effect free: it records the final priority picture so gate/review can
    audit whether a lower-priority pass accidentally overrode a stronger one.
    """
    ctx = context or {}
    decisions: List[Dict[str, Any]] = []
    active: List[str] = []
    for policy in POLICY_PRIORITY_ORDER:
        is_active = _policy_active(route, ctx, policy)
        if is_active:
            active.append(policy)
        decisions.append({
            "policy": policy,
            "priority": POLICY_PRIORITY[policy],
            "active": is_active,
            "effect": _decision_effect(route, policy) if is_active else "",
        })
    winner = active[0] if active else "none"
    conflicts: List[Dict[str, Any]] = []
    backend_policies = [p for p in active if p in {"fixed_mode", "identity_affinity", "cross_episode_baseline", "spectacle_benchmark", "spectacle_prior", "cost_quality_tier"}]
    if len(backend_policies) > 1:
        conflicts.append({
            "surface": "backend_choice",
            "policies": backend_policies,
            "winner": backend_policies[0],
            "resolution": "priority_lattice",
        })
    voice_policies = [p for p in active if p in {"compliance_capability_evidence", "native_voice_fallback", "cost_quality_tier"}]
    if len(voice_policies) > 1:
        conflicts.append({
            "surface": "voice_identity",
            "policies": voice_policies,
            "winner": voice_policies[0],
            "resolution": "priority_lattice",
        })
    return {
        "kind": "n2d_route_policy_resolution",
        "version": 1,
        "clip_id": route.get("clip_id"),
        "winner": winner,
        "priority_order": list(POLICY_PRIORITY_ORDER),
        "decisions": decisions,
        "conflicts": conflicts,
        "signoff_required": any(
            f in set(route.get("risk_flags") or [])
            for f in ("baseline_deferred_by_locked_backend", "spectacle_benchmark_deferred_by_baseline", "native_voice_identity_unproven")
        ),
    }
