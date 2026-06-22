#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backend-neutral image capability standards for n2d.

This module defines what n2d image generation must achieve. It deliberately
does not name vendors in the standards. Backend-specific differences are
handled by image_backend_adapter.py, which maps a selected backend to native
support or required mitigation steps.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional


STANDARD_VERSION = "2026-06-20"


IMAGE_CAPABILITY_STANDARDS: List[Dict[str, Any]] = [
    {
        "id": "official_auditable_backend",
        "title": "官方入口与审计证据",
        "requirement": "出图必须走官方/已登录/可审计入口，不能使用含糊或逆向路径。",
        "outputs": ("provider", "adapter_kind", "api_refresh_evidence", "production_event"),
    },
    {
        "id": "identity_continuity",
        "title": "角色身份连续性",
        "requirement": "同一 CHAR_ID/形态跨镜跨集必须保持同一角色 DNA；标准不因后端变弱而降低。",
        "outputs": ("identity_registry", "reference_group_or_subject_id", "face_qc"),
    },
    {
        "id": "multi_subject_separation",
        "title": "多主体身份隔离",
        "requirement": "多人同框时每个具名角色必须有独立身份槽位、位置、参考和互斥锚点。",
        "outputs": ("subject_slots", "distinct_anchors", "composition_or_subject_ids"),
    },
    {
        "id": "reference_ingestion",
        "title": "参考图真实入参",
        "requirement": "参考图必须作为实际后端入参或主体注册材料传入，不能只停留在 prompt 文本。",
        "outputs": ("reference_manifest", "reference_input_paths", "selected_and_dropped_refs"),
    },
    {
        "id": "edit_repair_path",
        "title": "合法修复路径",
        "requirement": "修脸/修物必须由官方编辑、整图重绘或重新生成完成；禁止本地贴脸/换脸伪修复。",
        "outputs": ("repair_mode", "source_asset", "qc_after_repair"),
    },
    {
        "id": "text_rendering_path",
        "title": "文字与图层清晰度",
        "requirement": "需要清晰文字时必须有可靠文字生成或后期 overlay；不把关键文字赌在弱后端里。",
        "outputs": ("text_strategy", "overlay_plan_or_native_text"),
    },
    {
        "id": "reference_budget",
        "title": "参考预算与选择理由",
        "requirement": "参考图数量必须按后端容量和镜头风险选择，超限时显式丢弃并说明理由。",
        "outputs": ("backend_limit", "selected_refs", "dropped_refs", "drop_reason"),
    },
    {
        "id": "qc_and_fallback",
        "title": "质检与回退闭环",
        "requirement": "任何能力降级都必须补足 QC、人审或重跑范围，不能把降级当通过。",
        "outputs": ("qc_precision", "manual_review_queue", "rerun_scope"),
    },
]


def catalog() -> Dict[str, Any]:
    return {
        "kind": "n2d_image_capability_standards",
        "version": STANDARD_VERSION,
        "principle": "standards are backend-neutral; backend adapters satisfy or mitigate them",
        "standards": IMAGE_CAPABILITY_STANDARDS,
    }


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "是", "需要", "有"}


def normalize_workload(raw: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    raw = dict(raw or {})
    characters = int(raw.get("characters") or raw.get("character_count") or 0)
    refs = int(raw.get("reference_images") or raw.get("reference_image_count") or 0)
    strong_identity = any(_as_bool(raw.get(k)) for k in (
        "core_character", "closeup", "strong_emotion", "extreme_angle", "needs_persistent_subject",
    ))
    has_characters = _as_bool(raw.get("has_characters")) or characters > 0 or strong_identity
    return {
        "has_characters": has_characters,
        "characters": characters,
        "reference_images": refs,
        "multi_character": _as_bool(raw.get("multi_character")) or characters >= 2,
        "core_character": _as_bool(raw.get("core_character")),
        "closeup": _as_bool(raw.get("closeup")),
        "strong_emotion": _as_bool(raw.get("strong_emotion")),
        "extreme_angle": _as_bool(raw.get("extreme_angle")),
        "needs_persistent_subject": _as_bool(raw.get("needs_persistent_subject")),
        "needs_edit": _as_bool(raw.get("needs_edit")),
        "needs_mask": _as_bool(raw.get("needs_mask") or raw.get("needs_inpaint")),
        "text_rendering": _as_bool(raw.get("text_rendering") or raw.get("critical_text")),
        "needs_seed": _as_bool(raw.get("needs_seed") or raw.get("reproducible")),
        "official_only": True if raw.get("official_only") is None else _as_bool(raw.get("official_only")),
    }


def _row(
    standard_id: str,
    status: str,
    *,
    native: Optional[List[str]] = None,
    mitigations: Optional[List[str]] = None,
    outputs: Optional[List[str]] = None,
    note: str = "",
) -> Dict[str, Any]:
    spec = next((s for s in IMAGE_CAPABILITY_STANDARDS if s["id"] == standard_id), {"id": standard_id})
    return {
        "standard": standard_id,
        "title": spec.get("title", standard_id),
        "status": status,
        "native_support": native or [],
        "mitigations": mitigations or [],
        "required_outputs": outputs or list(spec.get("outputs") or []),
        "note": note,
    }


def plan_for_backend(adapter: Mapping[str, Any], workload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Return a backend-neutral standard compliance plan for one backend adapter."""
    w = normalize_workload(workload)
    backend = str(adapter.get("canonical") or adapter.get("label") or "unknown")
    rows: List[Dict[str, Any]] = []

    if w["official_only"] and not adapter.get("official"):
        rows.append(_row(
            "official_auditable_backend",
            "blocked",
            mitigations=["改用官方/已登录/可审计后端，或先补官方入口适配与刷新证据"],
            note="unknown or unofficial backend cannot satisfy n2d production standard",
        ))
    else:
        rows.append(_row(
            "official_auditable_backend",
            "covered",
            native=["official_backend" if adapter.get("official") else "manual_official_proof"],
            mitigations=["每次付费出图前 record-refresh 记录当天官方 API/CLI 证据"],
        ))

    if not w["has_characters"]:
        rows.append(_row("identity_continuity", "not_applicable", note="no named character workload"))
    elif adapter.get("persistent_subject"):
        rows.append(_row(
            "identity_continuity",
            "native",
            native=["persistent_subject", "subject_registration"],
            mitigations=["主体 ID 仍需叠加 reference_group 单强锚和 full image_qc 双保险"],
        ))
    elif adapter.get("multi_reference") or adapter.get("supports_high_fidelity_reference"):
        extra = " + face_embedding" if (w["core_character"] or w["closeup"] or w["strong_emotion"]) else ""
        rows.append(_row(
            "identity_continuity",
            "mitigated",
            native=["multi_reference" if adapter.get("multi_reference") else "high_fidelity_reference"],
            mitigations=[
                f"加载 reference_group{extra}：正/45度/侧/半身/脸锚/表情库按镜头风险选入参",
                "近景/大表情/暗光镜强制同源脸锚或表情参考，并用 full image_qc 回验",
                "长线核心角反复漂移时升档到原生主体或 LoRA，不降低角色一致性标准",
            ],
        ))
    else:
        rows.append(_row(
            "identity_continuity",
            "mitigated",
            mitigations=[
                "降级为无人物/远景/背身/反应镜，或先补可用多参考/主体库适配",
                "所有含角色镜进入人工复核队列，不能自动视为通过",
            ],
            note="backend has no verified identity capability",
        ))

    if not w["multi_character"]:
        rows.append(_row("multi_subject_separation", "not_applicable", note="single subject or no subject"))
    elif adapter.get("persistent_subject"):
        rows.append(_row(
            "multi_subject_separation",
            "native",
            native=["native_subject_slots"],
            mitigations=["为每个 CHAR_ID/形态登记 subject slot + 位置 + 单强锚；失败时回 split_composite"],
        ))
    else:
        rows.append(_row(
            "multi_subject_separation",
            "mitigated",
            mitigations=[
                "自动加载 split_composite_required / 单人分层出图策略",
                "逐主体写画面槽位、reference_group、primary 星标、5-7 个互斥锚点",
                "站位复杂时叠 pose/depth 或改分镜为单人 CU + 反打",
            ],
        ))

    ref = adapter.get("reference_input") if isinstance(adapter.get("reference_input"), Mapping) else {}
    max_total = ref.get("max_total")
    ref_over = isinstance(max_total, int) and max_total > 0 and w["reference_images"] > max_total
    if w["reference_images"] <= 0 and not w["has_characters"]:
        rows.append(_row("reference_ingestion", "not_applicable", note="no reference workload"))
    elif adapter.get("multi_reference"):
        mitigations = ["生成 reference_manifest，记录实际传入路径、sha256、来源角色/资产"]
        if ref_over:
            mitigations.append(f"参考图超出后端预算 {max_total}：按风险优先级选择，dropped_refs 写明原因")
        rows.append(_row(
            "reference_ingestion",
            "mitigated" if ref_over else "native",
            native=[str(ref.get("mode") or "multi_reference")],
            mitigations=mitigations,
        ))
    else:
        rows.append(_row(
            "reference_ingestion",
            "mitigated",
            mitigations=[
                "一次只喂单强锚或注册主体材料；多参考需求拆成多 pass 或先注册主体",
                "不能把参考图只写在 prompt 文本里，必须落 actual input manifest",
            ],
        ))

    if not (w["needs_edit"] or w["needs_mask"]):
        rows.append(_row("edit_repair_path", "covered", mitigations=["命中本地贴脸/换脸产物仍按失败处理"]))
    elif w["needs_mask"] and adapter.get("supports_mask"):
        rows.append(_row(
            "edit_repair_path",
            "native",
            native=["mask_or_inpaint_edit"],
            mitigations=["编辑后必须重跑 image_qc；production_events 记录 source_asset 和 mask/edit 模式"],
        ))
    elif adapter.get("supports_edit"):
        rows.append(_row(
            "edit_repair_path",
            "mitigated",
            native=["image_edit_without_verified_mask"],
            mitigations=[
                "不做本地贴脸；改用官方整图 image2image/full-canvas edit",
                "局部修复不可控时重抽整张，保留原 reference_bundle 和 QC 证据",
            ],
        ))
    else:
        rows.append(_row(
            "edit_repair_path",
            "mitigated",
            mitigations=[
                "当前后端无已证实编辑路径：重抽整张或切到官方编辑后端后整镜重做",
                "不得用本地裁脸/换脸/贴图作为最终图",
            ],
        ))

    if not w["text_rendering"]:
        rows.append(_row("text_rendering_path", "not_applicable", note="no critical text"))
    elif adapter.get("supports_text_rendering") == "high":
        rows.append(_row(
            "text_rendering_path",
            "native",
            native=["high_text_rendering"],
            mitigations=["关键文字仍要有 OCR/人审；失败则转 compose overlay"],
        ))
    else:
        rows.append(_row(
            "text_rendering_path",
            "mitigated",
            mitigations=[
                "关键文字不烤进图；AI 只出无字底板",
                "用 n2d-compose/Pillow overlay 或后期字幕层生成清晰文字",
            ],
        ))

    rows.append(_row(
        "reference_budget",
        "mitigated" if ref_over else "covered",
        native=[f"limit={max_total}" if isinstance(max_total, int) and max_total > 0 else "local_policy_limit"],
        mitigations=(["按角色脸锚/表情 > 服装体态 > 场景道具 > 风格参考排序，超限 dropped_refs 落档"] if ref_over else []),
    ))

    qc_mitigations = ["full image_qc 是最终机器证据；degraded/none 时高风险镜进入人审或重跑"]
    if not adapter.get("persistent_subject") and w["has_characters"]:
        qc_mitigations.append("无持久主体后端必须加严脸部 drift/QC 与跨集漂移回扫")
    rows.append(_row("qc_and_fallback", "covered", mitigations=qc_mitigations))

    blocked = [r for r in rows if r["status"] == "blocked"]
    mitigated = [r for r in rows if r["status"] == "mitigated"]
    status = "blocked" if blocked else ("mitigations_required" if mitigated else "native_or_covered")
    required_mitigations = []
    for row in mitigated:
        required_mitigations.extend(row.get("mitigations") or [])
    return {
        "kind": "n2d_image_backend_standard_plan",
        "version": STANDARD_VERSION,
        "backend": backend,
        "status": status,
        "workload": w,
        "standards": rows,
        "required_mitigations": required_mitigations,
        "blocked_standards": [r["standard"] for r in blocked],
    }
