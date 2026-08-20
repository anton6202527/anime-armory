#!/usr/bin/env python3
"""Deterministic stage gates for n2d.

This script turns the high-risk SKILL.md rules into repeatable checks.  It does
not create assets; it only reports whether a stage may proceed.

Usage:
  # Production entry: records QA findings and returns this gate's exit code.
  python3 skills/n2d/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image_prompt_preflight|image_preflight|video_prompt_preflight|video_preflight|image|video|compose|review

  # Engine/debug entry: deterministic findings only, no dashboard telemetry.
  python3 skills/n2d/n2d-review/scripts/gate.py <作品根> 第N集 --stage video --json

Exit codes:
  0 = no blockers
  1 = at least one blocker
  2 = bad invocation / missing project
"""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

# 共享基座（增量2·按证据族拆分）：常量/findings/add/无状态助手全部住 gate_core，
# gate.py 只留 check_*/run/main。gates/<family>.py 后续也从 gate_core 取，避免循环导入。
from gate_core import *  # noqa: F401,F403
# B7 contract sentinel：三视图人审拼版不能替代正/45°/侧/背等拆分参考；
# tier-aware executable checks remain in gate_core and are invoked through this gate entry.
from seam_contract import (  # noqa: E402
    missing_evidence as seam_missing_evidence,
    needs_end_anchor,
    normalize_seam_mode,
    requires_boundary_frame,
)
import prompt_consumption_contract  # noqa: E402
from gates.evidence import *  # noqa: F401,F403  证据族 check_（增量3）
from gates.consistency import *  # noqa: F401,F403  证据族 check_（增量3）
from gates.backend import *  # noqa: F401,F403  证据族 check_（增量3）
from gates.asset import *  # noqa: F401,F403  证据族 check_（增量3）
from gates.voice import *  # noqa: F401,F403  证据族 check_（增量3）
from gates.scene import *  # noqa: F401,F403  证据族 check_（增量3）
from gates.contract import *  # noqa: F401,F403  证据族 check_（增量3·face 先行）
from gates.face import *  # noqa: F401,F403  证据族 check_（增量3·face 先行）
_BGM_CORE_PATH = Path(__file__).resolve().parents[2] / "_lib" / "bgm_contract.py"
_BGM_CORE_SPEC = importlib.util.spec_from_file_location("n2d_bgm_contract_core_for_gate", _BGM_CORE_PATH)
assert _BGM_CORE_SPEC is not None and _BGM_CORE_SPEC.loader is not None
bgm_contract_core = importlib.util.module_from_spec(_BGM_CORE_SPEC)
sys.modules[_BGM_CORE_SPEC.name] = bgm_contract_core
_BGM_CORE_SPEC.loader.exec_module(bgm_contract_core)
_SERIES_CORE_PATH = Path(__file__).resolve().parents[2] / "_lib" / "series_consistency.py"
_SERIES_CORE_SPEC = importlib.util.spec_from_file_location(
    "n2d_series_consistency_core_for_gate", _SERIES_CORE_PATH,
)
assert _SERIES_CORE_SPEC is not None and _SERIES_CORE_SPEC.loader is not None
series_consistency_core = importlib.util.module_from_spec(_SERIES_CORE_SPEC)
sys.modules[_SERIES_CORE_SPEC.name] = series_consistency_core
_SERIES_CORE_SPEC.loader.exec_module(series_consistency_core)
from gate_core import (  # 显式带上 import* 默认会漏的下划线私有助手
    _IDENTITY_SCRIPTS,
    _cross_episode_diff,
    _ce_overview_rel,
    _ce_prior_episode,
    _ce_episode_number,
    _ce_scene_names,
    _ce_core_scene_names,
    _loads_json_from_noisy_stdout,
    _RISK_DEFAULTS,
    _default_risk_score,
    _warn_tier,
    _warn_icon,
    _default_evidence_family,
    _DOF_INTENT_TOKENS,
    _HEURISTIC_BLOCK_DEMOTIONS,
    _CHARTER_LOCKED_DIMS_CACHE,
    _charter_locked_dims,
    _DEGRADED_QC_WAIVERS,
    _production_mode_contract_issues,
    _profile_values,
    _contains_profile_marker,
    _production_profile_inferred,
    _settings_values,
    _project_has_english_subtitles,
    _project_has_overseas_release_target,
    _episode_reference_texts,
    _episode_has_per_shot_frames,
    _registered_registry_ids,
    _production_events_path,
    _norm_rel_path,
    _asset_matches,
    _load_production_events,
    _latest_asset_generation_event,
    _event_generation,
    _event_meta,
    _event_cost,
    _event_asset_rel,
    _is_prohibited_face_patch_event,
    _prohibited_face_patch_outputs,
    _seed_record_value,
    _event_value_any,
    _event_status_pass,
    _final_media_exists,
    _final_media_rels,
    _recipe_return_stage_for_asset,
    _recipe_event_missing_fields,
    select_video_frame_strategy,
    _midframe_self_check_value,
    _check_midframe_generation_self_check,
    _listify,
    _status,
    _filled,
    _looks_like_status_value,
    _valid_iso_date,
    _has_embedded_iso_date,
    _is_internal_distribution,
    _is_publish_intent,
    _compliance_block,
    _compliance_warn,
    _episode_in_scope,
    _identity_character_ids,
    _check_compliance_rights,
    _check_compliance_characters,
    _check_compliance_voice,
    _check_platform_targets,
    _check_regulatory_filing,
    _ai_labeling_required,
    _check_ai_labeling,
    _artifact_exists,
    _episode_planned_minutes,
    _image_backend_gate_workload,
    _truthy_setting,
    _route_video_backends,
    _video_route_backend_roles,
    _cap_bool,
    _cap_number,
    _cap_value,
    _route_capability_assertion_gaps,
    _run_drift_risk_script,
    _CORE_SCOPE_RE,
    _image_backend_supports_native_subject,
    _image_event_provider,
    _lora_exception_scope_path,
    _validate_lora_exception_scope,
    _lora_scope_clips,
    _event_clip_id,
    _is_lora_sidechain_event,
    _reference_plan_requirement,
    _reference_plan_application_path,
    _reference_plan_prompt_path,
    _safe_sha256,
    _reference_plan_application_status,
    _route_allows_no_firstframe,
    _styleid_release_signoff_path,
    _styleid_structured_signoff_ok,
    _storyboard_closeup_character_ratio,
    _styleid_release_gate_required,
    _TONE_SPLIT_RE,
    _tone_base,
    _earliest_storyboard_ep,
    _possession_ledger_path_candidates,
    _possession_ledger_exists,
    _possession_mentions_core_asset,
    _long_running_subjectless_severity,
    _normalize_lora_backend,
    _lora_usable_on_image_backend,
    _image_form_has_identity_lock,
    _clip_blob,
    _first_template_keyword_hit,
    _field_is_missing,
    _is_restricted_partial_form,
    _gate_make_clip_id,
    _has_identity_handle,
    _validate_identity_adapter_map,
    _lora_gap_loc_suffix,
    _validate_identity_lora,
    _validate_generation_control,
    _validate_character_dna,
    _performance_signature_present,
    _signature_equipment_refs,
    _core_action_character_needs_equipment,
    _validate_signature_equipment,
    _profile_has_any,
    _validate_wardrobe_profile,
    _validate_character_asset_bundle,
    _identity_reference_item_path,
    _identity_reference_item_ready,
    _identity_reference_item_derivation,
    _file_sha256,
    _validate_same_source_makeup_derivation,
    _identity_expression_path,
    _identity_reference_list_paths,
    _identity_ready_reference_list_paths,
    _validate_reference_atlas,
    _identity_reference_exists,
    _identity_reference_matches_asset_key,
    _COSTUME_VARIANT_RE,
    _COSTUME_NON_FACE,
    _costume_stem,
    _validate_scene_dna,
    _flatten_asset_terms,
    _asset_must_not_have_terms,
    _validate_scene_atlas,
    _is_core_location_asset,
    _asset_has_any,
    _weapon_profile,
    _is_weapon_like_asset,
    _asset_owner_present,
    _validate_weapon_profile,
    _SHOT_SCALE_MAP,
    _OTS_RE,
    _SHOT_BLOCK_SPLIT_RE,
    _PHYSICAL_SCALE_TOKENS,
    _registry_character_names,
    _has_any,
    _headline,
    _clip_number_from_section,
    _has_field,
    _has_line_field,
    _section_requires_motion_control,
    _route_requires_contact_fields,
    _section_shot_type,
    _action_choreography_required_fields,
    _missing_contract_fields,
    _section_native_audio_opt_in,
    _native_audio_contract_ok,
    _native_audio_policy_line,
    _distribution_intent,
    _truthy,
    _mapping,
    _clip_audio_intent,
    _clip_compose_policy,
    _sidecar_clip_id,
    _native_av_physics_clip_errors,
    _route_clip_number,
    _video_route_policy_map,
    _storyboard_frame_requirements,
    _route_is_speech_like,
    _route_needs_mouth_visible_audit,
    _route_needs_model_baseline,
    _identity_route_requires_character_refs,
    _route_clip_character_refs,
    _baseline_override_accepted,
    _as_string_list,
    _baseline_override_payload,
    _override_expiry_ok,
    _baseline_override_errors,
    _route_is_high_action,
    _NON_NATIVE_BINDINGS,
    _CORE_SCOPES,
    _motion_control_required_for_route,
    _resolve_under_root,
    _uri_like,
    _uri_scheme,
    _sequence_pattern_to_glob,
    _verified_remote_control_input,
    _control_asset_exists,
    _input_ready,
    _reference_block,
    _section_has_character_refs,
    _character_names_in_refs,
    _needs_closeup_identity_lock,
    _has_closeup_identity_lock,
    _has_i2i_tail_continuity_lock,
    _has_i2i_derivation,
    _codex_needs_face_reference,
    _codex_has_face_reference,
    _codex_dark_vfx_face_risk,
    _codex_has_face_visibility_guard,
    _has_codex_split_composite_strategy,
    _has_generic_reference_index_lock,
    _has_native_multi_subject_strategy,
    _has_multi_subject_identity_slots,
    _has_character_id_binding,
    _has_character_aesthetic_baseline,
    _multi_char_binding_ambiguity,
    _has_asset_id_binding,
    _needs_scene_asset_binding,
    _needs_prop_asset_binding,
    _has_standard_character_turnaround,
    _is_restricted_partial_prompt_section,
    _has_positive_prompt_heading,
    _uses_halfbody_outfit_ref,
    _has_halfbody_crop_rule,
    _has_prop_structure_rule,
    _needs_prop_structure_gate,
    _evolution_derived_forms,
    _section_is_derived_form,
    _declares_evolution_derivation,
    _FINALIZE_CHAR_RE,
    _FINALIZE_ASSET_RE,
    _finalize_evidence,
    _sha256_file,
    _form_anchor_relpath,
    _CLOSEUP_MARKERS,
    _clip_is_closeup,
    _episode_big_expression_closeup_clips,
    _clip_character_ids,
    _VID_CLIP_HEAD_RE,
    _VID_FIRST_FRAME_RE,
    _VID_END_FRAME_RE,
    _VID_MID_FRAME_RE,
    _native_av_subtitle_status_ok,
    _native_av_subtitle_word_level,
    _native_av_subtitle_errors,
    _native_voice_segments_errors,
    _clip_label,
    _artifact_refs,
    _continuity_extra,
    _add_continuity_rows,
    _translation_glossary_terms,
    _translation_term_has_pair,
    _translation_category_covered,
    _consistency_signoff_path,
    _row_is_key_scene,
    _row_is_dialogue_closeup,
    _consistency_finding_hash,
    _signoff_expiry_ok,
    _advisory_row_signed_off,
    _strict_advisory_should_block,
    _intentional_discontinuity_module,
    _sanitized_intentional_manifest,
    _native_block_intentional_signoff,
    _canonical_fingerprint_fresh,
    _check_fidelity_gate_active,
    _autorun_scene_verifier,
    _SEV_RANK,
    _series_ep_int,
    _finding_sort_key,
)

from video_prompt_compiler import (  # noqa: E402  完整合同 → 后端提交 prompt 的单一编译边界
    KIND as COMPILED_VIDEO_PROMPT_KIND,
    lint_compiled_prompt,
    normalize_backend as normalize_video_prompt_backend,
    parse_compiled_markdown,
)
from image_prompt_compiler import (  # noqa: E402  完整图片合同 → 后端提交 prompt 的单一编译边界
    KIND as COMPILED_IMAGE_PROMPT_KIND,
    lint_compiled_section as lint_compiled_image_section,
)

def check_gate_policy_matrix(stage: str) -> None:
    for err in validate_gate_policy_matrix():
        add(BLOCK, "Gate Policy Matrix", stage, f"gate_policy_matrix.json 无效：{err}", return_to_stage="review")
def _consistency_rule_registry_issues() -> List[str]:
    issues: List[str] = []
    test_path = os.path.join(SCRIPT_DIR, "test_gate.py")
    try:
        test_source = open(test_path, encoding="utf-8").read()
    except OSError:
        test_source = ""
    for key, row in CONSISTENCY_RULE_REGISTRY.items():
        fn_name = str(row.get("gate_function") or "").strip()
        if not fn_name:
            issues.append(f"{key}: missing gate_function")
            continue
        fn = globals().get(fn_name)
        if not callable(fn):
            issues.append(f"{key}: gate_function {fn_name} is not callable")
        if not row.get("stages"):
            issues.append(f"{key}: missing stages")
        if not row.get("tests"):
            issues.append(f"{key}: missing tests")
        elif test_source:
            for test_name in row.get("tests") or ():
                if f"def {test_name}" not in test_source:
                    issues.append(f"{key}: missing registered test {test_name}")
    return issues
def _consistency_charter_issues() -> List[str]:
    """charter 登记的 enforcement 不变量闸函数必须仍存在且可调用（防改名/删除静默失效）。
    源码级"locked 闸是否被 profile 门控"的深检在 test_consistency_charter.py，不在运行时跑。"""
    if SCRIPT_DIR and SCRIPT_DIR not in sys.path:
        sys.path.insert(0, SCRIPT_DIR)
    try:
        from consistency_charter import CHARTER  # 同目录·纯 stdlib
    except Exception as exc:  # 导入失败不崩整个 gate
        return [f"consistency_charter 加载失败：{exc}"]
    issues: List[str] = []
    for name in CHARTER:
        if not callable(globals().get(name)):
            issues.append(f"charter 闸 {name} 在 gate.py 不可调用（被改名/删除？强制力不变量失联）")
    return issues
def check_consistency_rule_registry(root: str, ep: str, stage: str) -> None:
    """Meta-gate: documented consistency rules must point to callable gates/tests."""
    issues = _consistency_rule_registry_issues() + _consistency_charter_issues()
    if not issues:
        return
    add(
        BLOCK,
        "一致性规则注册表",
        os.path.join(os.path.dirname(SCRIPT_DIR), "scripts", "gate.py"),
        "一致性规则注册表失效：" + "；".join(issues) +
        "。每条规则必须映射到 gate function、stage 和测试，避免文档规则变成孤儿。",
        return_to_stage="review",
    )
def check_referenced_markers_resolve(root: str, ep: str) -> None:
    """出图/出视频前：本集分镜/prompt 引用到的每个资产标记必须在注册层真实存在。

    堵的洞（image_qc.py 自注释承认、此前无人在花钱前拦）：闸只查「写了 CHAR_xx」，
    不验该 id 在 identity_registry/asset_registry 真存在——写错 `CHAR_99`/`PROP_88` 能一路
    过出图前 preflight、付费生成，要到出图后逐镜核对（require reference ids 仅在帧已存在时
    才传）才暴露，此时钱已烧。这里把 `referenced_ids ⊆ registered_ids` 前移成**花钱前**硬约束。

    只读盘·纯结构核对（不需要像素），是最便宜的一致性闸。registry 文件本身缺失/为空由
    check_identity_registry / check_asset_reference_registry 负责 BLOCK；这里仅当对应 registry
    已可解析且有条目时，对「引用到却没登记」的 id 报 BLOCK，避免共享库自举那一次误伤。"""
    ref_chars, ref_assets = episode_registry_reference_ids(root, ep)
    if not ref_chars and not ref_assets:
        return
    reg_chars, reg_assets = _registered_registry_ids(root)
    for ref, reg, is_char, reg_file in (
        (ref_chars, reg_chars, True, "identity_registry.json"),
        (ref_assets, reg_assets, False, "asset_registry.json"),
    ):
        if not reg:
            # registry 为空/缺失 → 交由专门的 registry 校验报 BLOCK，避免重复噪音。
            continue
        label = "资产身份注册层" if is_char else "资产引用注册层"
        noun = "角色" if is_char else "资产"
        for rid in sorted(ref - reg):
            add(
                BLOCK,
                label,
                f"{ep} {rid}",
                f"本集分镜/出图 prompt 引用了未登记的{noun}标记 `{rid}`，但它不在 {reg_file} 已登记 id 中——"
                f"要么写错/笔误（回分镜改正），要么该{noun}尚未定妆登记（先补登记+定妆再引用）。"
                f"未知标记禁止进入付费出图/出视频（防写错 id 空烧）。",
                return_to_stage="image",
            )
def check_compliance_manifest(root: str, ep: str, stage: str) -> None:
    """Front-load rights, character/voice authorization, platform, localization and regulatory gates.

    AI 标识仅做 INFO 待办；不得把未落标升级为 compose/review blocker。
    """
    p = compliance_manifest_path(root)
    data = load_json(p)
    if not isinstance(data, dict):
        add(BLOCK, "合规前置", p, "缺少或无法解析合规/compliance_manifest.json；角色授权、声音克隆、平台审核、出海本地化必须进入 gate")
        return
    if data.get("kind") != COMPLIANCE_KIND:
        _compliance_block(p, f"kind 必须是 {COMPLIANCE_KIND}")
    _check_compliance_rights(root, data, p)
    _check_compliance_characters(root, data, p)
    _check_compliance_voice(data, p)
    _check_platform_targets(data, p, stage)
    _check_regulatory_filing(data, p, stage)
    _check_ai_labeling(data, p, stage)
def check_placeholder_policy(root: str, ep: str, stage: str) -> None:
    if is_native_av_production(root):
        # 原生音画：说话镜由视频后端一次出同步音画，不靠配音时长；占位/缺配音不作硬闸。
        return
    family = policy_family_for_stage(stage, fallback=gate_family(stage))
    profile = consistency_release_profile(root, stage, ep)
    ph = voice_is_placeholder(root, ep)
    if is_hybrid_routing(root):
        estimate, estimate_error = _hybrid_timing_estimate(root, ep)
        if ph is False:
            return
        if family in {"compose", "review"} and _hybrid_final_voice_required(root, ep):
            add(
                BLOCK, "配音", ep,
                "混合自动路由仍有 final_voice_required 镜头，但最终真实配音尚未完成。"
                "timing_estimate.json 只是无 WAV 时间基准，不能进入正式合成/验收；先完成声音选角锁与最终配音。",
                return_to_stage="voice",
            )
        elif family in {"image", "video"} and estimate:
            add(
                WARN, "时间基准", ep,
                "当前使用 timing_estimate.json（无 WAV）推进画面；这是设计态时间基准。"
                "可见口型镜只可按 production_mode_route 生成表演驱动画面或 base_video_only 基础片，不能冒充最终说话镜。",
                return_to_stage="voice",
            )
        elif family in {"image", "video", "compose", "review"} and not estimate:
            add(BLOCK, "时间基准", ep, f"混合自动路由缺有效 timing_estimate.json：{estimate_error}", return_to_stage="voice")
        return
    if ph is None:
        if family in {"image", "video", "compose", "review"}:
            add(BLOCK, "配音", ep, "未找到可判定的时长清单；无法确认真实配音或 rough timing，先跑 n2d-voice 生成 `时长清单.json`")
        else:
            add(WARN, "配音", ep, "未找到可判定的占位字段；若尚未配音，下游应先补齐")
        return
    if not ph:
        return
    if is_video_first(root) and profile == "production" and family in {"compose", "review"}:
        add(
            BLOCK,
            "配音",
            ep,
            "production 项目仍在「先出视频后配音」占位时长链路上；占位只允许 rough demo，"
            "正式成片/验收前必须补真实配音并重定时，或切到原生音画并补声纹/字幕对齐证据后再继续。",
            return_to_stage="voice",
        )
    elif family == "image" and is_video_first(root):
        add(WARN, "配音", ep, "当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时")
    elif family == "video" and is_video_first(root):
        add(WARN, "配音", ep, "先出视频后配音模式已放行占位时长进入出视频；后期补真音可能需要重出视频")
    else:
        add(BLOCK, "配音", ep, "配音仍为占位音色；`配音先行` 模式下该阶段不应继续，先 n2d-voice 换真实配音并重定时")


def _hybrid_timing_estimate(root: str, ep: str) -> Tuple[Optional[Dict[str, Any]], str]:
    path = os.path.join(root, "合成", ep, "配音", "timing_estimate.json")
    data = load_json(path)
    if not isinstance(data, dict):
        return None, f"缺或无法解析 {path}"
    if data.get("kind") != "n2d_timing_estimate":
        return None, "kind 不是 n2d_timing_estimate"
    if data.get("audio_generated") is not False:
        return None, "audio_generated 必须为 false（估时合同不可冒充音频）"
    rows = data.get("lines")
    if not isinstance(rows, list) or not rows:
        return None, "lines 为空"
    return data, ""


def _hybrid_final_voice_required(root: str, ep: str) -> bool:
    path = os.path.join(root, "生产数据", f"production_mode_route_{ep}.json")
    data = load_json(path)
    routes = data.get("clip_routes") if isinstance(data, dict) else []
    if isinstance(routes, list) and routes:
        return any(isinstance(row, dict) and row.get("final_voice_required") is True for row in routes)
    voiceover = os.path.join(root, "脚本", ep, "voiceover.txt")
    try:
        return any(line.strip() and not line.lstrip().startswith("#") for line in open(voiceover, encoding="utf-8"))
    except OSError:
        return False
def check_timing_manifest_complete(root: str, ep: str) -> None:
    """时长清单逐句完整性：非占位但残缺也要拦。

    `check_placeholder_policy` 只判「是否占位」、`check_voiceover_fingerprint` 只判「定稿后是否被改」——
    一份非占位但残缺的清单（漏句 / 某句 voice_key 空 / 实测时长<=0）能溜过这两关，下游镜头时长据残缺
    数据切，导致音画错位、塌帧、跨集音色对账缺数据源。这里在付费出图前做逐句对账。
    原生音画模式镜头时长不依赖配音时长清单，跳过。
    """
    if is_native_av_production(root):
        return
    man_p = manifest_path(root, ep)
    if is_hybrid_routing(root) and not man_p:
        estimate, error = _hybrid_timing_estimate(root, ep)
        if not estimate:
            add(BLOCK, "时间基准", os.path.join(root, "合成", ep, "配音", "timing_estimate.json"), error, return_to_stage="voice")
            return
        rows = estimate.get("lines") or []
        bad = []
        for idx, row in enumerate(rows):
            try:
                duration = float(row.get("时长") or row.get("estimated_duration_sec") or 0)
            except (TypeError, ValueError, AttributeError):
                duration = 0.0
            if not isinstance(row, dict) or duration <= 0 or str(row.get("timing_basis") or "") != "text_estimate_no_audio":
                bad.append(idx)
        if bad:
            add(BLOCK, "时间基准", os.path.join(root, "合成", ep, "配音", "timing_estimate.json"),
                f"timing_estimate 有 {len(bad)} 行缺正时长或 timing_basis（如 {bad[:8]}）", return_to_stage="voice")
        vo_p = os.path.join(root, "脚本", ep, "voiceover.txt")
        parsed_lines = []
        if os.path.isfile(vo_p):
            parsed_lines = [
                line.strip() for line in open(vo_p, encoding="utf-8")
                if re.match(r"\[(镜头[^·]*)·([^·]+)·([^\]]*)\]\s*(.+)", line.strip())
            ]
        current = hashlib.sha256("\n".join(parsed_lines).encode("utf-8")).hexdigest() if parsed_lines else ""
        recorded = str(estimate.get("source_fingerprint") or "")
        if recorded and current and recorded != current:
            add(BLOCK, "时间基准", vo_p, "voiceover.txt 在估时后被改动；重跑 voice_preflight.py prepare 与 finalize_storyboard", return_to_stage="voice")
        if parsed_lines and len(parsed_lines) != len(rows):
            add(BLOCK, "时间基准", vo_p, f"voiceover {len(parsed_lines)} 句 ≠ timing_estimate {len(rows)} 行", return_to_stage="voice")
        return
    rows = load_json(man_p)
    if not isinstance(rows, list) or not rows:
        return  # 缺/空清单由 check_progress_artifact_signoff 覆盖，避免重复上报
    dict_rows = [r for r in rows if isinstance(r, dict)]
    # 行数对账：仅当 voiceover.txt 可解析台词行时（render_voice 逐行正则一行一条，1:1）
    vo_p = os.path.join(root, "脚本", ep, "voiceover.txt")
    vo_lines = 0
    if os.path.isfile(vo_p):
        with open(vo_p, encoding="utf-8") as fh:
            for ln in fh:
                if re.match(r"\[(镜头[^·]*)·([^·]+)·([^\]]*)\]\s*(.+)", ln.strip()):
                    vo_lines += 1
    if vo_lines and len(rows) != vo_lines:
        add(BLOCK, "配音", man_p,
            f"时长清单句数({len(rows)})与 voiceover.txt 台词行数({vo_lines})不符——漏句/多句会让镜头时长整体错位；"
            "重跑 n2d-voice 对齐后再出图。",
            return_to_stage="voice")
        return

    def _dur(r: dict) -> float:
        try:
            return float(r.get("时长") or 0)
        except (TypeError, ValueError):
            return 0.0

    bad_key = [i for i, r in enumerate(dict_rows)
               if not str(r.get(VOICE_KEY_FIELD) or r.get(VOICE_KEY_LEGACY_FIELD) or "").strip()]
    bad_dur = [i for i, r in enumerate(dict_rows) if _dur(r) <= 0]
    if bad_key:
        add(BLOCK, "配音", man_p,
            f"{len(bad_key)} 句缺 voice_key（音色键）——一角一色跨集对账缺数据源，下游 n2d-identity 无法对账；"
            f"重跑 n2d-voice 补齐。受影响句序 {bad_key[:8]}",
            return_to_stage="voice")
    if bad_dur:
        add(BLOCK, "配音", man_p,
            f"{len(bad_dur)} 句实测时长<=0——镜头时长据此为 0 会塌帧/音画错位；重跑 n2d-voice 重测时长。"
            f"受影响句序 {bad_dur[:8]}",
            return_to_stage="voice")
def check_budget_cap(root: str, ep: str) -> None:
    """付费生成前的预算硬挂钩（堵「只在事后 rebuild 才告警」的执行时松动洞）。

    此前 budget_cap 只在 dashboard build 后由 evaluate_alerts **事后**告警（cmd_record append 成本事件之后），
    用户能一路花超才被发现。这里把同一上限挪到**付费前** gate：累计已花 ≥ 上限、或本集历史单价×计划时长
    预测会冲破上限 → BLOCK；接近上限 → WARN。上限来源同 dashboard（alert_thresholds.json budget_cap /
    设置「告警预算上限」/ env N2D_ALERT_BUDGET_CAP）。未配 budget_cap → 不挡（graceful，不强加预算）。
    累计成本读已落盘的 生产数据/dashboard.json totals（aggregate 的产物，不在 gate 里重算）；
    逃生口：调高 budget_cap、换免费/降档后端、或拆少本集产出后重跑。"""
    thresholds = load_thresholds(root)
    cap = thresholds.get("budget_cap")
    if cap in (None, "", 0):
        return
    warn_ratio = thresholds.get("budget_warn_ratio") or 0.8
    dash = load_json(os.path.join(root, "生产数据", "dashboard.json"))
    totals = (dash.get("totals") if isinstance(dash, dict) else None) or {}
    cost_totals = totals.get("cost_totals") if isinstance(totals.get("cost_totals"), dict) else {}
    cost_per_min = totals.get("cost_per_finished_min") if isinstance(totals.get("cost_per_finished_min"), dict) else {}
    planned_min = _episode_planned_minutes(root, ep)
    loc = os.path.join(root, "生产数据", "dashboard.json")
    for sev, _cur, _spent, _forecast, reason in evaluate_budget_gate(
            cost_totals, cost_per_min, cap, planned_min, warn_ratio=float(warn_ratio)):
        if sev == "block":
            add(BLOCK, "预算", loc,
                f"付费生成前预算闸门：{reason}。停止付费生成——调高预算上限"
                "（生产数据/alert_thresholds.json budget_cap / 设置「告警预算上限」/ env N2D_ALERT_BUDGET_CAP）、"
                "换免费/降档后端，或拆少本集产出后再跑；别一路花超才在事后 dashboard 才发现。")
        else:
            add(WARN, "预算", loc,
                f"付费生成前预算预警：{reason}。已接近上限，留意后续几集别冲破；必要时降档/换后端或调预算。")
def check_backend_smoke_evidence(root: str, backend_kind: str, backend: str, *, channel: str = "", loc: str = "") -> None:
    if not backend_smoke_gate_enabled(root):
        return
    status = backend_smoke.smoke_status(
        root,
        backend_kind,
        backend,
        channel=channel,
        max_age_days=backend_smoke_max_age_days(),
        require_proof=True,  # 硬闸要求 live_probe 或可核验真实产物，堵手录 pass 证声明不证活性
    )
    if status.get("status") != "fresh":
        label = "生图后端Smoke" if backend_kind == "image" else "生视频后端Smoke"
        add(
            BLOCK,
            label,
            loc or str(status.get("path") or ""),
            f"{backend_kind} 后端「{backend}」缺少最近通过的 smoke 证据：{status.get('message')}。"
            "放量/多 worker/付费批量前必须用 `python3 skills/n2d/_lib/backend_smoke.py probe`（真探活）"
            "或 `record --status pass --output-asset <真实产物路径>`（手录须附可核验产物）写入最近可运行证明；"
            "仅刷新官方文档、或没有产物的手录 pass 都不等于当前账号/渠道可跑。",
            affected_artifacts=[str(status.get("path") or "")],
        )
def check_image_backend_api_refresh(root: str, ep: str) -> None:
    """正式付费出图前要求本次后端 API/CLI 能力刷新证据。

    后端能力和 API 名称变化快，不能把旧模型矩阵或菜单文案当事实。这里不在 gate 里联网，
    而是要求操作者/agent 当次查官方文档或 CLI/API help 后，把来源和能力结论写入
    `生产数据/image_backend_capabilities/<backend>.json`；gate 只检查这份证据是否是今天的。
    """
    settings_loc = os.path.join(root, "_设置.md")
    setting = get_setting(root, "生图AI", "Codex").strip()
    status = image_backend_adapter.refresh_evidence_status(root, setting)
    if status.get("status") != "fresh":
        add(
            BLOCK,
            "生图后端适配",
            settings_loc,
            f"生图后端「{setting}」缺少本次官方 API/CLI 刷新证据：{status.get('message')}。"
            "正式付费出图前必须实时查官方文档/本机 CLI 或 API help，确认生成、编辑、多参考、主体库、掩码、输出 schema、价格/额度等当前能力，"
            "再记录刷新证据：`python3 skills/n2d/_lib/image_backend_adapter.py record-refresh <作品根> --backend "
            f"\"{setting}\" --source \"<官方文档或CLI/API证据>\" --source-url \"<链接或留空>\" "
            "--evidence-kind official_docs --note \"<本次能力结论>\"`。"
            f"证据文件：{status.get('path')}。未刷新不得开跑，避免旧 API 或能力误判造成整集返工。",
            return_to_stage="image",
            affected_artifacts=[str(status.get("path") or "")],
        )
    check_backend_smoke_evidence(root, "image", setting, loc=settings_loc)

    rec = image_backend_adapter.recommend_backend(setting, _image_backend_gate_workload(root, ep))
    standard_plan = image_backend_adapter.standard_plan(setting, _image_backend_gate_workload(root, ep))
    if standard_plan.get("status") == "blocked":
        add(
            BLOCK,
            "生图后端适配",
            settings_loc,
            f"所选生图后端「{setting}」无法满足统一出图能力标准："
            f"{', '.join(standard_plan.get('blocked_standards') or [])}。"
            "标准层不随后端短板下调；请换官方可审计后端，或先补适配层能力与弥补措施。",
            return_to_stage="image",
        )
    elif standard_plan.get("status") == "mitigations_required":
        items = [str(x) for x in (standard_plan.get("required_mitigations") or [])[:4]]
        add(
            WARN,
            "生图后端适配",
            settings_loc,
            f"统一标准已按「{setting}」自动加载弥补措施：{'；'.join(items)}"
            + ("；..." if len(standard_plan.get("required_mitigations") or []) > 4 else "")
            + "。这些是后端差异的执行补偿，不降低 n2d 的出图标准。",
            return_to_stage="image",
        )
    if rec.get("upgrade_recommended"):
        cur = rec.get("current") or {}
        best = rec.get("recommended") or {}
        adapter = rec.get("adapter") or {}
        add(
            WARN,
            "生图后端适配",
            settings_loc,
            f"适配层评分建议升档：当前「{setting}」score={cur.get('score')}，"
            f"推荐「{best.get('label') or best.get('backend')}」score={best.get('score')}。"
            f"理由：推荐后端能力={','.join(best.get('strengths') or []) or adapter.get('adapter_kind')}；"
            "若确认切换，先统一 `_设置.md` 与全部 prompt 的生图模型/渠道，并按新模型/渠道重做/刷新本集定妆、参考包和身份注册，禁止半集混用。",
            return_to_stage="image",
        )
def check_video_backend_api_refresh(
    root: str,
    ep: str,
    routes: Sequence[Dict[str, Any]],
    video_channel: str,
    route_path: str,
    allow_empty_fallback: bool = False,
) -> None:
    """正式付费出视频前要求本次视频后端 API/CLI 能力刷新证据。"""
    for backend in _route_video_backends(routes, allow_empty_fallback):
        status = video_backend_adapter.refresh_evidence_status(root, backend, video_channel)
        if status.get("status") == "fresh":
            assertions = status.get("capability_assertions") if isinstance(status.get("capability_assertions"), dict) else {}
            adapter = video_backend_adapter.backend_adapter(backend, video_channel)
            if not bool(adapter.get("paid_routing_allowed")) and not _cap_bool(assertions, "paid_routing_allowed"):
                channel_note = f"（渠道 {video_channel}，执行后端 {adapter.get('execution_backend')}）" if video_channel else ""
                add(
                    BLOCK,
                    "生视频后端适配",
                    route_path,
                    f"生视频后端「{backend}」{channel_note}当前适配层仍标记为不可自动付费路由"
                    f"（confidence={adapter.get('capability_confidence', {}).get('confidence') if isinstance(adapter.get('capability_confidence'), dict) else 'unknown'}）。"
                    "不能只靠过期/保守静态档或泛化文档进入实际出视频队列；"
                    "请改 route 到本项目已验证可执行后端，或用 `record-refresh --capability paid_routing_allowed=true` "
                    "记录本次官方 API/CLI + 账号/额度/输出 schema 证据后再付费生成。",
                    return_to_stage="video",
                    affected_artifacts=[str(status.get("path") or "")],
                )
            check_backend_smoke_evidence(root, "video", backend, channel=video_channel, loc=route_path)
            continue
        adapter = video_backend_adapter.backend_adapter(backend, video_channel)
        channel_note = f"（渠道 {video_channel}，执行后端 {adapter.get('execution_backend')}）" if video_channel else ""
        add(
            BLOCK,
            "生视频后端适配",
            route_path,
            f"生视频后端「{backend}」{channel_note}缺少本次官方 API/CLI 刷新证据：{status.get('message')}。"
            "正式付费出视频前必须实时查官方文档/本机 CLI 或 API help，确认单 Clip 上限、首尾/多帧能力、"
            "原生音画/口型、身份绑定、分辨率/价格/额度和输出 schema，再记录刷新证据："
            "`python3 skills/n2d/_lib/video_backend_adapter.py record-refresh <作品根> --backend "
            f"\"{backend}\" --channel \"{video_channel}\" --source \"<官方文档或CLI/API证据>\" "
            "--note \"<本次能力结论>\"`。"
            f"证据文件：{status.get('path')}。未刷新不得开跑，避免旧 API 或能力误判造成整集返工。",
            return_to_stage="video",
            affected_artifacts=[str(status.get("path") or "")],
        )
    capability_gap_records: List[str] = []
    for route in routes:
        if not isinstance(route, dict):
            continue
        for role, backend in _video_route_backend_roles(route, allow_empty_fallback):
            if not backend or not video_backend_adapter.requires_refresh(backend):
                continue
            status = video_backend_adapter.refresh_evidence_status(root, backend, video_channel)
            if status.get("status") != "fresh":
                continue
            assertions = status.get("capability_assertions") if isinstance(status.get("capability_assertions"), dict) else {}
            capability_gap_records.extend(_route_capability_assertion_gaps(route, assertions, role))
    if capability_gap_records:
        add(
            BLOCK,
            "生视频后端适配",
            route_path,
            "本次视频后端刷新证据缺少或不满足 route 需要的结构化能力断言："
            + "；".join(capability_gap_records[:8])
            + ("；..." if len(capability_gap_records) > 8 else "")
            + "。请重跑 record-refresh 并补 `--capability key=value`，确认首/尾/多帧、native_av、口型音频参考、身份机制和 Motion Control 后再付费出视频。",
            return_to_stage="video",
        )
def check_prompt_checklists(root: str, ep: str, kind: str) -> None:
    if kind == "image":
        p = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
        if not os.path.isfile(p):
            add(BLOCK, "prompt", p, "缺本集分镜出图 prompt")
            return
        text = open(p, encoding="utf-8").read()
        if "生成后自检流程" not in text and "自检（生成后逐张过" not in text:
            add(WARN, "prompt", p, "缺全局生成后自检流程")
        sections = re.findall(r"(?ms)^##\s+(?:镜头\s+\d+|Clip\s+\d+[A-Z]?).*?(?=^##\s+(?:镜头\s+\d+|Clip\s+\d+[A-Z]?)|\Z)", text)
        if not sections:
            add(BLOCK, "prompt", p, "未识别到逐镜 prompt 块")
            return
        # 单图参考后端(无原生主体锁，如 Codex)下，双人同框是实锤脸漂真凶 → 该镜的多角色检查升 BLOCK；
        # 有原生主体能力的后端(Seedream/可灵/Sora)仍按 WARN。能力判定走契约 persistent_subject，不 hardcode。
        _img_canon, _ = classify_image_backend(get_setting(root, "生图AI", "Codex").strip())
        single_ref_backend = not image_backend_supports_persistent_subject(_img_canon)
        for idx, sec in enumerate(sections, 1):
            check_image_shot_prompt_section(
                p,
                idx,
                sec,
                single_ref_backend=single_ref_backend,
                root=root,
            )
        return
    else:
        check_video_prompt_overview(root, ep)
        p = os.path.join(root, "出视频", ep, "prompt", "01_clips.md")
        if not os.path.isfile(p):
            add(BLOCK, "prompt", p, "缺本集视频 Clip prompt")
            return
        text = open(p, encoding="utf-8").read()
        native_av = is_native_av_production(root)
        if _section_native_audio_opt_in(text) or (native_av and "native_speech" in text):
            overview = os.path.join(root, "出视频", ep, "prompt", "00_总览.md")
            overview_text = open(overview, encoding="utf-8").read() if os.path.isfile(overview) else ""
            if "原生音画 opt-in 清单" not in overview_text:
                add(BLOCK, "原生音画", overview, "逐 Clip prompt 启用了原生音画，但出视频总览缺「原生音画 opt-in 清单」")
            elif native_av:
                # 制作模式=原生音画：台词由后端原生生成是有意为之，不再强制 no_native_speech。
                if not _has_any(overview_text, ("native_speech", "原生人声")):
                    add(WARN, "原生音画", overview, "原生音画模式：总览应说明 native_speech 为有意生成")
            elif not _native_audio_contract_ok(overview_text):
                add(BLOCK, "原生音画", overview, "原生音画 opt-in 清单必须明确 no_native_speech / 无原生人声")
        sections = re.findall(r"(?ms)^##\s+Clip\s+\d+[A-Z]?（.*?(?=^##\s+Clip\s+\d+[A-Z]?（|\Z)", text)
        if not sections:
            add(BLOCK, "prompt", p, "未识别到 Clip prompt 块")
            return
        route_map = _video_route_policy_map(root, ep)
        for idx, sec in enumerate(sections, 1):
            clip_num = _clip_number_from_section(sec, idx)
            check_video_clip_prompt_section(p, sec, route=route_map.get(clip_num))
        return
def check_native_audio_opt_in_overview(root: str, ep: str, overview_text: str, loc: str) -> None:
    if is_native_av_production(root):
        # 制作模式=原生音画：native_speech 是有意路由（说话镜一次出同步音画），不强制 no_native_speech。
        # 仍要求总览声明原生音画意图。
        if not _has_any(overview_text, ("native_speech", "原生音画", "原生人声")):
            add(WARN, "原生音画", loc, "原生音画模式：出视频总览应声明 native_speech 路由（台词+口型由后端原生生成）")
        return
    policy = native_audio_policy(root)
    mode = native_audio_policy_mode(policy)
    if mode == NATIVE_AUDIO_DISCARD:
        return
    if "原生音画 opt-in 清单" not in overview_text:
        add(BLOCK, "原生音画", loc, f"`视频原生音轨={policy}` 不是默认丢弃；出视频总览必须写「原生音画 opt-in 清单」，逐 Clip 说明低风险、无口型、无原生人声")
    if not _native_audio_contract_ok(overview_text):
        add(BLOCK, "原生音画", loc, "原生音画 opt-in 清单必须明确 no_native_speech / 无原生人声；否则 compose 不得混入或保留原生音轨")
def check_native_av_physical_contract(root: str, ep: str, overview_text: str, loc: str) -> None:
    if not native_av_physics_required(root, ep, overview_text):
        return
    title = "原生音画物理一致性契约"
    if title not in overview_text:
        add(BLOCK, "原生音画物理一致性", loc,
            f"本集会保留/混入原生音轨或使用原生音画，但缺「{title}」；"
            "必须锁声源归属、口型策略、材质/动作声、空间声学、字幕/后期策略后才能进视频生成/合成")
        return
    for key in NATIVE_AV_PHYSICAL_FIELDS:
        if key not in overview_text:
            add(BLOCK, "原生音画物理一致性", loc, f"{title} 缺字段：{key}")
def check_native_av_physics_sidecar(root: str, ep: str, required: Optional[bool] = None) -> None:
    if required is None:
        required = native_av_physics_required(root, ep)
    if not required:
        return
    path = native_av_physics_sidecar_path(root, ep)
    data = load_json(path)
    if not isinstance(data, dict):
        add(
            BLOCK,
            "原生音画物理一致性",
            path,
            "缺机器可读 sidecar：生产数据/native_av_physics_第N集.json；必须逐 Clip 写谁发声、动作声可见证据、空间混响/距离和后期保留策略，不能只靠总览人判。",
            return_to_stage="video",
        )
        return
    if data.get("kind") != NATIVE_AV_PHYSICS_KIND:
        add(BLOCK, "原生音画物理一致性", path, f"native_av_physics sidecar kind 应为 {NATIVE_AV_PHYSICS_KIND}")
    clips = data.get("clips")
    if not isinstance(clips, list) or not clips:
        add(BLOCK, "原生音画物理一致性", path, "native_av_physics sidecar 缺 clips[]；无法逐镜校验声源/动作声/空间声学。")
        return
    for idx, row in enumerate(clips, start=1):
        if not isinstance(row, Mapping):
            add(BLOCK, "原生音画物理一致性", path, f"clips[{idx}] 不是对象")
            continue
        for err in _native_av_physics_clip_errors(row, idx):
            add(BLOCK, "原生音画物理一致性", path, err, return_to_stage="video")


def check_dialogue_fact_contract(root: str, ep: str, stage: str) -> None:
    """Native-speech clips must own disjoint dialogue and locked numeric facts."""
    if stage == "video_prompt_preflight" and not os.path.isfile(os.path.join(root, "脚本", ep, "storyboard.json")):
        return
    try:
        if SCRIPT_DIR and SCRIPT_DIR not in sys.path:
            sys.path.insert(0, SCRIPT_DIR)
        import dialogue_fact_guard  # type: ignore
    except Exception as exc:
        add(
            BLOCK,
            "对白事实锁",
            "dialogue_fact_guard",
            f"无法加载 dialogue_fact_guard：{exc}；原生音画说话镜缺对白/事实锁，不能进入付费视频链路。",
            return_to_stage="review",
        )
        return
    try:
        report = dialogue_fact_guard.validate(Path(root), ep)
    except Exception as exc:
        add(
            BLOCK,
            "对白事实锁",
            "dialogue_fact_guard",
            f"dialogue_fact_guard 运行失败：{exc}；先修合同或分镜再出视频。",
            return_to_stage="script",
        )
        return
    for row in report.get("findings") or []:
        if not isinstance(row, Mapping):
            continue
        sev_raw = str(row.get("severity") or "").lower()
        sev = BLOCK if sev_raw == "block" else WARN if sev_raw == "warn" else INFO
        code = str(row.get("code") or "dialogue_fact_contract")
        loc = str(row.get("loc") or "dialogue_fact_guard")
        message = str(row.get("message") or "")
        return_stage = "script" if code in {
            "duplicate_voiceover_index",
            "contract_duplicate_index",
            "contract_missing_clip",
            "contract_unknown_index",
            "duplicate_screen_text_line",
            "screen_text_not_overlay",
            "age_fact_drift",
            "height_fact_drift",
            "setting_fact_drift",
            "quantity_fact_drift",
        } else "video_prompt"
        add(sev, "对白事实锁", loc, f"{code}: {message}", return_to_stage=return_stage)


def check_markdown_style_contract(text: str, loc: str, layer: str) -> None:
    if "本集基础视觉风格契约" in text:
        missing = _missing_contract_fields(text, STYLE_CONTRACT_FIELDS)
        if missing:
            add(BLOCK, "基础视觉风格契约", loc, f"本集基础视觉风格契约缺字段：{missing[0]}")
        if not _has_any(text, ("style_anchor", "风格锚")):
            add(BLOCK, "基础视觉风格契约", loc,
                f"本集基础视觉风格契约缺 style_anchor/风格锚；{layer} 必须继承 storyboard.json style_contract.style_anchor，"
                "否则 image_qc 无法做风格归属机检。")
        return
    if "本集真实电影感契约" in text:
        missing = _missing_contract_fields(text, CINEMATIC_CONTRACT_FIELDS)
        if missing:
            add(BLOCK, "基础视觉风格契约", loc, f"本集真实电影感契约缺字段：{missing[0]}")
        return
    add(BLOCK, "基础视觉风格契约", loc, f"缺「本集基础视觉风格契约」；{layer} 必须继承 storyboard.json style_contract，而不是只在 prompt 末尾加某一种风格词")
def check_video_prompt_overview(root: str, ep: str) -> None:
    """Video prompt overview must carry the episode-level director contract.

    Per-clip prompts can be locally valid and still cut together badly.  The
    overview locks the episode's visual grammar before any paid video call.
    """
    p = os.path.join(root, "出视频", ep, "prompt", "00_总览.md")
    if not os.path.isfile(p):
        add(BLOCK, "prompt", p, "缺出视频总览；无法锁本集导演一致性契约")
        return
    text = open(p, encoding="utf-8").read()
    if "本集导演一致性契约" not in text:
        add(BLOCK, "导演一致性", p, "缺「本集导演一致性契约」；不能只按单 Clip 随机写视频 prompt")
        return
    for key in ("主色调", "镜头语法", "轴线", "剧情状态锁", "场景状态"):
        if key not in text:
            add(BLOCK, "导演一致性", p, f"本集导演一致性契约缺字段：{key}")
    check_markdown_style_contract(text, p, "出视频总览")
    check_video_model_routes(root, ep, text, p)
    check_video_closeup_identity_overview(text, p)
    check_native_audio_opt_in_overview(root, ep, text, p)
    check_native_av_physical_contract(root, ep, text, p)
    check_native_av_physics_sidecar(root, ep, native_av_physics_required(root, ep, text))
def check_video_closeup_identity_overview(overview_text: str, overview_path: str) -> None:
    has_identity_overview = _has_any(
        overview_text,
        (
            "本集资产身份速查",
            "本集身份 Adapter Matrix 摘要",
            "identity_adapter_matrix",
            "reference_group",
            "角色身份",
        ),
    )
    if not has_identity_overview:
        return
    if "本集近景身份风险表" not in overview_text:
        add(
            BLOCK,
            "资产身份注册层",
            overview_path,
            "缺「本集近景身份风险表」；CU/MCU/反打/说话镜必须在总览列明脸部特写/表情参考、当前后端身份锁能力、风险等级和回退/保真实现方案",
        )
        return
    for key in ("脸部", "表情", "风险"):
        if key not in overview_text:
            add(BLOCK, "资产身份注册层", overview_path, f"本集近景身份风险表缺字段/关键词：{key}")
    if not _has_any(overview_text, ("回退", "保真实现", "MCU", "OTS", "侧脸")):
        add(BLOCK, "资产身份注册层", overview_path, "本集近景身份风险表缺回退/保真实现路径")
    if _has_any(overview_text, ("CHAR_02", "配角", "小禾", "柳娘子")) and not _has_any(overview_text, ("MCU", "OTS", "侧脸", "手部", "物件反应")):
        add(
            WARN,
            "资产身份注册层",
            overview_path,
            "本集近景身份风险表未写配角近景回退/保真实现路径；建议明确 MCU/OTS/侧脸/手部/物件反应镜",
        )
def check_route_frame_capability(
    root: str,
    ep: str,
    route: Dict[str, Any],
    route_path: str,
    idx: int,
    frame_requirements: Dict[int, Dict[str, int | bool]],
    video_channel: str,
) -> None:
    """Warn when the storyboard asks for more timeline frames than the route can consume.

    For ordinary clips the warning is intentional rather than blocking: n2d has
    valid fallback paths (split relay, first+last only, or first frame +
    end_state text). What must not happen is silent degradation where `_mid`
    frames are generated but ignored by the selected backend.

    **高风险镜例外（req.high_risk）**：高运动模板（打斗/追逐/法术/飞行/拥抱拉扯/亲密接触）
    与跨情绪大表情近景，靠帧间插值（双帧/多帧）才稳——后端吃不下首尾/中段帧 = 双帧安全网
    静默失效 = 必崩接触/必脸漂。这类镜帧能力不匹配从 WARN 升 **BLOCK**，强制换后端或显式降级，
    不许靠纯文本约束硬出。
    """
    clip_num = _route_clip_number(route, idx)
    req = frame_requirements.get(clip_num)
    if not req:
        return
    primary = str(route.get("primary_backend") or "").strip()
    control = video_backend_frame_control(primary, video_channel)
    max_frames = int(control.get("max_timeline_frames") or 1)
    total_frames = int(req.get("total_timeline_frames") or 1)
    anchors = int(req.get("anchor_count") or 0)
    need_end = bool(req.get("need_end"))
    consumption = anchor_consumption_plan(primary, video_channel, anchor_count=anchors, need_end=need_end)
    consumption_mode = str(consumption.get("consumption_mode") or "unknown")
    high_risk = bool(req.get("high_risk"))
    production = consistency_release_profile(root, "video_preflight", ep) == "production"
    sev = BLOCK if (high_risk or production) else WARN
    risk_note = (
        "本镜为高运动模板/跨情绪大表情近景，帧间插值是唯一安全网，不许靠纯文本约束硬出（已升级为 BLOCK）。"
        if high_risk else
        "production 项目优先使用支持首尾帧/多锚帧的后端；帧消费能力不匹配不再作为普通 WARN 放行。"
        if production else ""
    )
    clip_id = str(route.get("clip_id") or f"Clip_{clip_num:02d}")
    mode = str(control.get("mode") or "unknown")
    verified = str(control.get("verified") or "unknown")
    fallback = str(control.get("fallback") or "Use split relay/manual generation.")
    channel_note = f"（执行渠道：{video_channel}）" if video_channel else ""
    if need_end and not bool(consumption.get("consumes_endframe")):
        add(
            sev,
            "首尾帧能力",
            route_path,
            f"{clip_id} storyboard 需要镜内尾锚/连续 take 边界帧，但 primary 后端 {primary or 'unknown'}{channel_note} "
            f"的帧能力档案为 {mode}，消费计划为 {consumption_mode}，未确认可消费尾帧。fallback：改走支持首尾帧的后端，"
            f"或退回单首帧 + 强 end_state 文字（接缝/大表情近景风险升高）。能力来源：{verified}{risk_note}",
            return_to_stage="video",
        )
    if anchors and not bool(consumption.get("consumes_mid_anchors_natively")):
        if consumption.get("requires_split_relay"):
            consequence = "该后端通常只能吃首尾两帧，中段锚帧不会在一次请求里成为时间轴关键帧，执行侧必须拆段接力"
        else:
            consequence = "该后端通常只按首帧/参考图生成，中段锚帧和尾帧都可能只剩文字约束"
        add(
            sev,
            "多帧能力",
            route_path,
            f"{clip_id} storyboard 声明了 {anchors} 个中段锚帧（共 {total_frames} 张时间轴帧），"
            f"但 primary 后端 {primary or 'unknown'}{channel_note} 的帧能力档案为 {mode}，"
            f"最多 {max_frames} 张时间轴帧，消费计划为 {consumption_mode}；{consequence}。fallback：{fallback}{risk_note}",
            return_to_stage="video",
        )


ACTION_ANCHOR_DURATION_SEC = 8.0
_ACTION_ANCHOR_HEAVY_RE = re.compile(
    r"打斗|攻防|拳脚|挥拳|刀剑|挥剑|抬剑|举剑|拔剑|掌法|出掌|追逐|追赶|冲刺|法术|武技|斗法|撞点|命中|碰撞|接触|抓腕|拉扯|拥抱|多主体接触|多人接触|"
    r"fight|chase|magic|impact|collision|contact",
    re.I,
)
_ACTION_ANCHOR_PREP_RE = re.compile(r"起手|蓄力|预备|发力|逼近|冲刺|冲向|追近|跃起|抬剑|举剑|拔剑|挥拳|出招|charge|windup|approach", re.I)
_ACTION_ANCHOR_IMPACT_RE = re.compile(r"命中|击中|撞点|撞击|碰撞|格挡|接触|抓住|拉住|爆发|落地|受击|hit|impact|collision|contact", re.I)
_ACTION_ANCHOR_RESPONSE_RE = re.compile(r"反应|受击|后撤|倒退|跌落|摔倒|余波|收势|回收|定住|僵住|退开|reaction|recovery|aftershock", re.I)
ACTION_ANCHOR_RISK_FLAGS = frozenset({
    "physical_contact",
    "multi_character_overlap",
    "high_speed_motion",
    "extreme_camera",
    "high_action",
    "spectacle",
    "contact_motion",
    "fast_motion",
    "physics",
})


def _action_anchor_text(clip: Mapping[str, Any], route: Optional[Mapping[str, Any]] = None) -> str:
    parts: List[str] = []
    for source in (clip, route or {}):
        for key in (
            "id",
            "clip_id",
            "label",
            "scene",
            "description",
            "visual",
            "action",
            "template",
            "shot_type",
            "risk_flags",
            "template_contract",
            "action_choreography",
            "motion_control",
            "shots",
            "continuity",
        ):
            value = source.get(key)
            if value is None:
                continue
            parts.append(json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value))
    return "\n".join(parts)


def _action_anchor_chain(text: str) -> Dict[str, bool]:
    prep = bool(_ACTION_ANCHOR_PREP_RE.search(text))
    impact = bool(_ACTION_ANCHOR_IMPACT_RE.search(text))
    response = bool(_ACTION_ANCHOR_RESPONSE_RE.search(text))
    return {
        "prep": prep,
        "impact": impact,
        "response": response,
        "partial": impact and (prep or response),
        "full": prep and impact and response,
    }


def _action_anchor_duration(clip: Mapping[str, Any]) -> Optional[float]:
    for key in ("duration", "duration_sec", "时长", "seconds"):
        value = clip.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            match = re.search(r"\d+(?:\.\d+)?", value)
            if match:
                return float(match.group(0))
    return None


def _action_anchor_has_list(clip: Mapping[str, Any]) -> bool:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    anchors = cont.get("anchors") if isinstance(cont, Mapping) else None
    return isinstance(anchors, list) and any(isinstance(item, Mapping) for item in anchors)


def _action_anchor_requirement(
    clip: Mapping[str, Any],
    route: Optional[Mapping[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    contract = clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}
    template = str(clip.get("template") or "").strip()
    shot_type = str((route or {}).get("shot_type") or clip.get("shot_type") or contract.get("template_id") or template).strip()
    route_flags = set(str(x).strip() for x in _listify((route or {}).get("risk_flags")) if str(x).strip())
    clip_flags = set(str(x).strip() for x in _listify(clip.get("risk_flags")) if str(x).strip())
    text = _action_anchor_text(clip, route)
    high_action = (
        template in HIGH_MOTION_TEMPLATES
        or shot_type in HIGH_MOTION_TEMPLATES
        or shot_type in ACTION_CHOREOGRAPHY_SHOT_TYPES
        or bool((route_flags | clip_flags) & ACTION_ANCHOR_RISK_FLAGS)
        or bool(_ACTION_ANCHOR_HEAVY_RE.search(text))
    )
    if not high_action:
        return None
    duration = _action_anchor_duration(clip)
    chain = _action_anchor_chain(text)
    long_clip = duration is not None and duration >= ACTION_ANCHOR_DURATION_SEC
    if not long_clip and not chain["partial"]:
        return None
    sev = BLOCK if (long_clip or chain["full"] or shot_type in ACTION_CHOREOGRAPHY_SHOT_TYPES) else WARN
    reasons: List[str] = []
    if long_clip:
        reasons.append(f"单镜时长 {duration:g}s >= {ACTION_ANCHOR_DURATION_SEC:g}s")
    if chain["full"]:
        reasons.append("含起手-命中-反应/收势完整动作链")
    elif chain["partial"]:
        reasons.append("含命中/接触及起手或反应动作链")
    return {"severity": sev, "reason": "；".join(reasons) or "重动作镜", "duration": duration, "chain": chain}


def check_action_anchor_contract(root: str, ep: str, stage: str = "video_preflight") -> None:
    data = load_json(storyboard_path(root, ep))
    if not isinstance(data, dict) or not isinstance(data.get("clips"), list):
        return
    route_map = _video_route_policy_map(root, ep)
    for idx, clip in enumerate(data.get("clips") or [], 1):
        if not isinstance(clip, Mapping):
            continue
        route = route_map.get(idx)
        req = _action_anchor_requirement(clip, route)
        if not req or _action_anchor_has_list(clip):
            continue
        cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
        has_mid = isinstance(cont.get("midframe"), Mapping) if isinstance(cont, Mapping) else False
        clip_id = _gate_make_clip_id(clip, idx)
        loc = f"{storyboard_path(root, ep)} {clip_id}"
        suffix = "当前只有 continuity.midframe；重动作/长动作链不能只靠单个 _mid。" if has_mid else "当前缺 continuity.anchors[]。"
        add(
            str(req["severity"]),
            "重动作多中帧",
            loc,
            f"{req['reason']}，必须写 continuity.anchors[] 多中帧链；{suffix}"
            "先回 n2d-script 跑 anchor_planner.py --write，出图补 anchor PNG，再重跑 n2d-model-router/video_preflight；"
            "这样 video_runner 才能自动走 native_multiframe 或 split_relay。",
            return_to_stage="script_stage2",
        )
def check_native_av_voice_fallback_route(root: str, ep: str, route: Mapping[str, object], routes_path: str, idx: int) -> None:
    """Native AV speech shots must either be native_speech or explicitly reopen voice-first."""
    if not is_native_av_production(root):
        return
    if not _route_is_speech_like(route):
        return
    clip_id = str(route.get("clip_id") or f"routes[{idx}]")
    native_policy = str(route.get("native_audio_policy") or "").strip()
    mode = str(route.get("mode") or "").strip()
    if native_policy == "native_speech" or mode == "native_av":
        return
    if route.get("requires_voice_fallback") is not True:
        add(
            BLOCK,
            "原生音画降级",
            routes_path,
            f"{clip_id} 位于制作模式=原生音画，但说话/口型镜既不是 native_speech，也未声明 requires_voice_fallback=true。"
            "这会制造无声对白镜；请重跑 n2d-model-router，或关闭固定模型/改配音先行。",
            return_to_stage="video_prompt",
        )
        return
    if str(route.get("fallback_production_mode") or "").strip() != "voice_first":
        add(
            BLOCK,
            "原生音画降级",
            routes_path,
            f"{clip_id} requires_voice_fallback=true 但 fallback_production_mode 不是 voice_first；"
            "无法确认本镜由 n2d-voice 接管台词。",
            return_to_stage="video_prompt",
        )
    ph = voice_is_placeholder(root, ep)
    if ph is None:
        add(
            BLOCK,
            "原生音画降级",
            os.path.join(root, "合成", ep, "配音"),
            f"{clip_id} 已回退 voice-first，但缺可判定的 `时长清单.json`；先跑 n2d-voice 生成真实配音/时长清单。",
            return_to_stage="voice",
        )
    elif ph:
        add(
            BLOCK,
            "原生音画降级",
            os.path.join(root, "合成", ep, "配音"),
            f"{clip_id} 已回退 voice-first，但配音仍为占位；先换真实配音并重定时后再出视频。",
            return_to_stage="voice",
        )
def check_mouth_visible_audit(root: str, ep: str, routes: Sequence[Mapping[str, object]], routes_path: str) -> None:
    needed = [r for r in routes if isinstance(r, Mapping) and _route_needs_mouth_visible_audit(r)]
    if not needed:
        return
    path = os.path.join(root, "生产数据", f"mouth_visible_audit_{ep}.json")
    if not os.path.isfile(path):
        add(
            BLOCK,
            "mouth_visible证据",
            path,
            "说话/口型镜或原生音频策略镜必须先跑 `python3 skills/n2d/n2d-model-router/scripts/mouth_detect.py <作品根> "
            f"{ep} --write`，把 mouth_visible 图像/文本/prompt 复核落成 sidecar，再进入付费出视频。",
            return_to_stage="video_prompt",
        )
        return
    data = load_json(path)
    if not isinstance(data, dict) or data.get("kind") != "n2d_mouth_visible_audit":
        add(BLOCK, "mouth_visible证据", path, "mouth_visible_audit kind 不正确；请重跑 mouth_detect.py --write", return_to_stage="video_prompt")
        return
    rows = data.get("rows")
    if not isinstance(rows, list):
        add(BLOCK, "mouth_visible证据", path, "mouth_visible_audit 缺 rows[]；请重跑 mouth_detect.py --write", return_to_stage="video_prompt")
        return
    row_ids = {str(r.get("clip_id") or "") for r in rows if isinstance(r, Mapping)}
    missing = [
        str(r.get("clip_id") or f"routes[{idx}]")
        for idx, r in enumerate(needed, 1)
        if str(r.get("clip_id") or f"routes[{idx}]") not in row_ids
    ]
    if missing:
        add(
            BLOCK,
            "mouth_visible证据",
            path,
            "mouth_visible_audit 未覆盖需要证据的 clip："
            + "、".join(missing[:8])
            + "。请用当前 storyboard/prompt 重跑 mouth_detect.py --write。",
            return_to_stage="video_prompt",
        )
    warned = [r for r in rows if isinstance(r, Mapping) and r.get("verdict") == "warn"]
    if warned:
        allow = os.environ.get("N2D_ALLOW_MOUTH_VISIBLE_WARN") == "1"
        sev = WARN if allow else BLOCK
        sample = "；".join(
            f"{r.get('clip_id')}: {r.get('message') or 'mouth_visible 冲突'}"
            for r in warned[:3]
        )
        add(
            sev,
            "mouth_visible证据",
            path,
            f"{len(warned)} 个 clip 的 mouth_visible 图像/文本/prompt 复核冲突：{sample}"
            + ("（已显式 N2D_ALLOW_MOUTH_VISIBLE_WARN 放行）" if allow else "。按 sidecar 建议修 prompt 后重跑。"),
            return_to_stage="video_prompt",
        )
def check_model_route_baseline_policy(root: str, ep: str, data: Mapping[str, object], routes: Sequence[Dict[str, Any]], path: str) -> None:
    """Episode 2+ high-risk/core routes must be anchored to a cross-episode backend baseline."""
    try:
        ep_num = _ce_episode_number(ep) or 0
    except Exception:
        ep_num = 0
    risky = [r for r in routes if isinstance(r, dict) and _route_needs_model_baseline(r)]
    if ep_num < 2 or not risky:
        return
    baseline_path = os.path.join(root, "设定库", "model_routes_baseline.json")
    if all(_baseline_override_accepted(data, r) for r in risky):
        add(
            WARN,
            "后端跨集锁",
            path,
            "本集高风险/含角色路由使用了结构化 baseline_override；请确认这是有意换后端，而不是漏跑第1集模型路由基线。",
            return_to_stage="video_prompt",
        )
        return
    samples = "、".join(str(r.get("clip_id") or r.get("shot_type") or "?") for r in risky[:6])
    if not os.path.isfile(baseline_path):
        add(
            BLOCK,
            "后端跨集锁",
            baseline_path,
            f"{ep} 含高风险/含角色路由（{samples}）但缺 `设定库/model_routes_baseline.json`。"
            "第2集起必须先用打样集 `n2d-model-router --write-baseline` 建立 shot_type→primary 后端基线，"
            "否则跨集自然路由可能换后端导致脸质感、运动质感和画风漂移。",
            return_to_stage="video_prompt",
            affected_artifacts=[baseline_path, path],
        )
    elif data.get("baseline_anchored") is not True:
        add(
            BLOCK,
            "后端跨集锁",
            path,
            f"{ep} 已存在 model_routes_baseline.json，但本集 video_model_routes.json 未标记 baseline_anchored=true。"
            "请重跑 n2d-model-router 让路由按跨集基线锚定，或写结构化 baseline_override（accepted/reviewer/reason/expires_at/affected_routes）。",
            return_to_stage="video_prompt",
            affected_artifacts=[baseline_path, path],
        )
def check_backend_consistency_scope(data: Mapping[str, object], routes: Sequence[Mapping[str, Any]], path: str) -> None:
    """Make image-vs-video backend consistency scopes explicit.

    n2d intentionally keeps image generation on one project model/channel while
    allowing video to route per clip.  Without an explicit scope declaration,
    future maintainers can accidentally apply the image rule to video or loosen
    image consistency because video is per-clip.
    """
    scope = data.get("backend_consistency_scope")
    primary_backends = {
        str(route.get("primary_backend") or "").strip()
        for route in routes
        if isinstance(route, Mapping) and str(route.get("primary_backend") or "").strip()
    }
    mixed_video = len(primary_backends) >= 2
    if not isinstance(scope, Mapping):
        add(
            WARN if not mixed_video else BLOCK,
            "后端一致性作用域(BSCOPE)",
            path,
            "video_model_routes.json 缺 backend_consistency_scope；需显式声明 image_generation=single_model_channel_per_project、"
            "video_generation=per_clip_allowed_with_baseline，并列出 baseline/identity_handoff/execution_recipe/post_video_qc 护栏。"
            + ("当前本集混用多个 video primary 后端，未声明作用域时容易把逐镜路由误当作随意换后端。" if mixed_video else ""),
            return_to_stage="video_prompt",
            risk_score=0.75 if mixed_video else 0.55,
            affected_artifacts=[path],
            evidence_family="text_contract",
        )
        return
    image_policy = str(scope.get("image_generation") or scope.get("image_policy") or "").strip()
    video_policy = str(scope.get("video_generation") or scope.get("video_policy") or "").strip()
    required_guards = {
        "model_routes_baseline",
        "identity_handoff",
        "execution_recipe",
        "post_video_qc",
    }
    guards = {str(x).strip() for x in _listify(scope.get("required_guards") or scope.get("guards")) if str(x).strip()}
    missing = sorted(required_guards - guards)
    if image_policy != "single_model_channel_per_project":
        add(WARN, "后端一致性作用域(BSCOPE)", path,
            "backend_consistency_scope.image_generation 应为 single_model_channel_per_project；出图侧不要因视频逐镜路由而放松统一后端口径。",
            return_to_stage="video_prompt", affected_artifacts=[path], evidence_family="text_contract")
    if video_policy != "per_clip_allowed_with_baseline":
        sev = BLOCK if mixed_video else WARN
        add(sev, "后端一致性作用域(BSCOPE)", path,
            "backend_consistency_scope.video_generation 应为 per_clip_allowed_with_baseline；逐镜路由必须通过 baseline/身份交接/配方/回验约束。",
            return_to_stage="video_prompt", risk_score=0.75 if sev == BLOCK else 0.55,
            affected_artifacts=[path], evidence_family="text_contract")
    if missing:
        add(WARN, "后端一致性作用域(BSCOPE)", path,
            f"backend_consistency_scope.required_guards 缺 {', '.join(missing)}；逐镜换视频后端的护栏不完整。",
            return_to_stage="video_prompt", affected_artifacts=[path], evidence_family="text_contract")
def check_route_execution_recipe(route: Mapping[str, Any], routes_path: str, idx: int) -> None:
    clip_id = str(route.get("clip_id") or f"routes[{idx}]")
    recipe = route.get("execution_recipe")
    if not isinstance(recipe, Mapping):
        add(
            BLOCK,
            "执行配方",
            routes_path,
            f"{clip_id} 缺 execution_recipe；请重跑 n2d-model-router，让逐 Clip 路由输出可执行输入配方。",
            return_to_stage="video_prompt",
        )
        return
    required_sections = ("frame_inputs", "reference_inputs", "control_inputs", "audio_inputs", "fallback", "capability_match", "post_video_qc")
    for section in required_sections:
        if not isinstance(recipe.get(section), Mapping):
            add(BLOCK, "执行配方", routes_path, f"{clip_id} execution_recipe 缺结构块：{section}", return_to_stage="video_prompt")
    frame = recipe.get("frame_inputs") if isinstance(recipe.get("frame_inputs"), Mapping) else {}
    refs = recipe.get("reference_inputs") if isinstance(recipe.get("reference_inputs"), Mapping) else {}
    controls = recipe.get("control_inputs") if isinstance(recipe.get("control_inputs"), Mapping) else {}
    audio = recipe.get("audio_inputs") if isinstance(recipe.get("audio_inputs"), Mapping) else {}
    fallback = recipe.get("fallback") if isinstance(recipe.get("fallback"), Mapping) else {}
    capability = recipe.get("capability_match") if isinstance(recipe.get("capability_match"), Mapping) else {}
    post_qc = recipe.get("post_video_qc") if isinstance(recipe.get("post_video_qc"), Mapping) else {}
    for key in ("first_frame", "consumption_mode", "native_timeline_frames"):
        if key not in frame or frame.get(key) in (None, ""):
            add(BLOCK, "执行配方", routes_path, f"{clip_id} execution_recipe.frame_inputs 缺字段：{key}", return_to_stage="video_prompt")
    for key in ("characters", "assets", "max_reference_images", "motion_reference"):
        if key not in refs:
            add(BLOCK, "执行配方", routes_path, f"{clip_id} execution_recipe.reference_inputs 缺字段：{key}", return_to_stage="video_prompt")
    for key in ("video_generation_audio_policy", "native_audio_policy", "speech_policy", "requires_voice_track"):
        if key not in audio:
            add(BLOCK, "执行配方", routes_path, f"{clip_id} execution_recipe.audio_inputs 缺字段：{key}", return_to_stage="video_prompt")
    for key in ("fallback_backends", "degrade_plan"):
        if key not in fallback:
            add(BLOCK, "执行配方", routes_path, f"{clip_id} execution_recipe.fallback 缺字段：{key}", return_to_stage="video_prompt")
    for key in ("frame_contract_supported", "motion_reference_supported", "motion_control_level"):
        if key not in capability:
            add(BLOCK, "执行配方", routes_path, f"{clip_id} execution_recipe.capability_match 缺字段：{key}", return_to_stage="video_prompt")
    for key in ("identity_qc_required", "dense_face_watch_required", "required_reports", "acceptance_policy"):
        if key not in post_qc:
            add(BLOCK, "执行配方", routes_path, f"{clip_id} execution_recipe.post_video_qc 缺字段：{key}", return_to_stage="video_prompt")
    mode = str(route.get("mode") or recipe.get("mode") or "").strip().lower()
    if mode and mode not in {"text2video", "t2v"} and frame.get("first_frame") is not True:
        add(
            BLOCK,
            "执行配方",
            routes_path,
            f"{clip_id} mode={route.get('mode')} 但 execution_recipe.frame_inputs.first_frame 不为 true；"
            "图生/帧生视频必须把首帧作为真实入参，不能退化为裸文本。",
            return_to_stage="video_prompt",
        )
    if _identity_route_requires_character_refs(route) and not refs.get("characters"):
        add(
            BLOCK,
            "执行配方",
            routes_path,
            f"{clip_id} identity_requirement={route.get('identity_requirement')} 但 execution_recipe.reference_inputs.characters 为空；"
            "角色镜必须把 reference_group / Character ID / Face Lock 等身份引用写进真实配方。",
            return_to_stage="video_prompt",
        )
    if _identity_route_requires_character_refs(route) and post_qc.get("identity_qc_required") is not True:
        add(
            BLOCK,
            "执行配方",
            routes_path,
            f"{clip_id} 含身份路由但 execution_recipe.post_video_qc.identity_qc_required 不为 true；"
            "成片验收必须知道本镜需要身份回验，不能只在 prompt 阶段声明身份锁。",
            return_to_stage="video_prompt",
        )
    reports = {str(x).strip() for x in (post_qc.get("required_reports") or []) if str(x).strip()} if isinstance(post_qc.get("required_reports"), list) else set()
    if post_qc.get("identity_qc_required") is True and "temporal_consistency" not in reports:
        add(
            BLOCK,
            "执行配方",
            routes_path,
            f"{clip_id} post_video_qc.identity_qc_required=true 但 required_reports 缺 temporal_consistency；"
            "身份镜验收至少要有片内一致性机检/降级人审入口。",
            return_to_stage="video_prompt",
        )
    if post_qc.get("dense_face_watch_required") is True and "video_face_drift_watch" not in reports:
        add(
            BLOCK,
            "执行配方",
            routes_path,
            f"{clip_id} post_video_qc.dense_face_watch_required=true 但 required_reports 缺 video_face_drift_watch；"
            "近景/反打/说话/多人身份高风险镜必须把密集抽帧人审包接入验收链。",
            return_to_stage="video_prompt",
        )
    if route.get("native_audio_policy") == "native_speech" and audio.get("speech_policy") != "native_speech":
        add(BLOCK, "执行配方", routes_path, f"{clip_id} native_speech 路由与 execution_recipe.audio_inputs.speech_policy 不一致", return_to_stage="video_prompt")
    if controls.get("required") is True and not controls.get("manifest_path"):
        add(BLOCK, "执行配方", routes_path, f"{clip_id} 需要 Motion Control 但 execution_recipe.control_inputs 缺 manifest_path", return_to_stage="video_prompt")


def _norm_clip_id(value: object) -> str:
    text = str(value or "").strip()
    m = re.search(r"Clip[_-]?(\d+)", text, re.I)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return text


def _dense_post_qc_routes(root: str, ep: str) -> List[Tuple[str, Mapping[str, Any], Mapping[str, Any]]]:
    path = os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json")
    data = load_json(path)
    routes = data.get("routes") if isinstance(data, Mapping) else None
    out: List[Tuple[str, Mapping[str, Any], Mapping[str, Any]]] = []
    if not isinstance(routes, list):
        return out
    for route in routes:
        if not isinstance(route, Mapping):
            continue
        recipe = route.get("execution_recipe") if isinstance(route.get("execution_recipe"), Mapping) else {}
        policy = recipe.get("post_video_qc") if isinstance(recipe.get("post_video_qc"), Mapping) else route.get("post_video_qc")
        if not isinstance(policy, Mapping) or policy.get("dense_face_watch_required") is not True:
            continue
        clip_id = _norm_clip_id(route.get("clip_id") or route.get("clip") or route.get("id"))
        if clip_id:
            out.append((clip_id, route, policy))
    return out


def _latest_video_batch_item(root: str, ep: str, clip_id: str) -> Tuple[str, Optional[Mapping[str, Any]]]:
    patterns = [
        os.path.join(root, "生产数据", f"video_batch_{ep}_*.json"),
        os.path.join(root, "生产数据", "video_batches", ep, "*", "*.json"),
    ]
    candidates: List[Tuple[float, str, Mapping[str, Any]]] = []
    for pattern in patterns:
        for path in glob.glob(pattern):
            data = load_json(path)
            items = data.get("items") if isinstance(data, Mapping) else None
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, Mapping) and _norm_clip_id(item.get("clip")) == clip_id:
                    try:
                        mtime = os.path.getmtime(path)
                    except OSError:
                        mtime = 0.0
                    candidates.append((mtime, path, item))
    if not candidates:
        return "", None
    candidates.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return candidates[0][1], candidates[0][2]


def _packet_mentions_clip(packet: Mapping[str, Any], clip_id: str) -> bool:
    fields = [
        packet.get("packet_id"),
        packet.get("master"),
        packet.get("source_clip"),
        packet.get("clip"),
    ]
    if any(_norm_clip_id(value) == clip_id for value in fields):
        return True
    for key in ("frames", "segments"):
        rows = packet.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, Mapping) and _norm_clip_id(row.get("clip")) == clip_id:
                return True
    return False


def _dense_watch_packets_for_clip(root: str, ep: str, clip_id: str) -> List[Tuple[str, Mapping[str, Any]]]:
    pattern = os.path.join(root, "生产数据", f"video_face_drift_watch_{ep}_*.json")
    out: List[Tuple[str, Mapping[str, Any]]] = []
    for path in glob.glob(pattern):
        data = load_json(path)
        if not isinstance(data, Mapping):
            continue
        if data.get("kind") != "n2d_video_face_drift_watch":
            continue
        if _packet_mentions_clip(data, clip_id):
            out.append((path, data))
    return sorted(out)


def _video_artifacts_for_clip(root: str, ep: str, clip_id: str) -> List[str]:
    video_dir = os.path.join(root, "出视频", ep, "视频")
    if not os.path.isdir(video_dir):
        return []
    out: List[str] = []
    for path in glob.glob(os.path.join(video_dir, "*.mp4")):
        if os.path.basename(os.path.dirname(path)) == "_downloads":
            continue
        if _norm_clip_id(os.path.basename(path)) == clip_id:
            out.append(path)
    return sorted(out)


def _dense_watch_human_pass(packet: Mapping[str, Any]) -> bool:
    review = packet.get("human_review") or packet.get("review")
    if not isinstance(review, Mapping):
        return False
    for key in ("identity_verdict", "face_identity", "verdict", "status"):
        value = str(review.get(key) or "").strip().lower()
        if value in {"pass", "passed", "same_character", "same_identity", "一致", "同一角色", "人工通过"}:
            return True
    return False


def check_video_post_qc_artifacts(root: str, ep: str, stage: str) -> None:
    """Post-video identity QC must become stage evidence, not a side note in routes."""
    if stage not in {"video", "compose", "review"}:
        return
    routes_path = os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json")
    for clip_id, _route, _policy in _dense_post_qc_routes(root, ep):
        manifest_path, item = _latest_video_batch_item(root, ep, clip_id)
        if item is None:
            existing_videos = _video_artifacts_for_clip(root, ep, clip_id)
            if stage == "video" and not existing_videos:
                # Video stage can be partially complete. Do not require post-video
                # acceptance evidence for clips that have not been generated yet.
                continue
            add(
                BLOCK,
                "成片身份回验",
                routes_path,
                f"{clip_id} 路由要求 dense_face_watch，但找不到对应 video_batch manifest item；"
                "必须通过 video_runner accept 写入 qc_machine/post_video_qc/video_face_drift_watch 证据后再进入合成/验收。",
                return_to_stage="video",
                affected_artifacts=existing_videos or [routes_path],
                evidence_family="face_embedding",
            )
            continue
        status = str(item.get("status") or "").strip()
        machine = item.get("qc_machine") if isinstance(item.get("qc_machine"), Mapping) else {}
        if status == "qc_blocked":
            add(
                BLOCK,
                "成片身份回验",
                manifest_path,
                f"{clip_id} 已被 video_runner 标记 qc_blocked：{item.get('fail_reason') or '缺 fail_reason'}",
                return_to_stage="video",
                affected_artifacts=[manifest_path, str(item.get("qc_json") or ""), str(item.get("qc_markdown") or "")],
                evidence_family="face_embedding",
            )
            continue
        packets = _dense_watch_packets_for_clip(root, ep, clip_id)
        ready_packets = [
            (path, packet) for path, packet in packets
            if packet.get("status") == "ready_for_human_frame_identity_review"
            and isinstance(packet.get("frames"), list)
            and len(packet.get("frames") or []) > 0
        ]
        human_pass = any(_dense_watch_human_pass(packet) for _path, packet in ready_packets)
        if int(machine.get("intra_warns") or 0) > 0 or item.get("qc_overridden") is True:
            if human_pass:
                add(
                    WARN,
                    "成片身份回验",
                    ready_packets[-1][0],
                    f"{clip_id} dense_face_watch 存在片内身份 warn/强制放行记录，但已有 "
                    "human_review.identity_verdict=pass；按人工密集抽帧复核签收降级为 WARN，"
                    "公开发布前仍建议重出或补重型身份一致性证据。",
                    return_to_stage="video",
                    affected_artifacts=[ready_packets[-1][0], str(ready_packets[-1][1].get("contact_sheet") or "")],
                    evidence_family="human_signoff",
                )
            else:
                add(
                    BLOCK,
                    "成片身份回验",
                    manifest_path,
                    f"{clip_id} dense_face_watch 镜存在片内身份 warn/强制放行记录；"
                    "不能用 --allow-qc-block 静默通过，必须确认误报并重出可审计 watch 包，真脸漂则回 video/image 重出。",
                    return_to_stage="video",
                    affected_artifacts=[manifest_path, str(item.get("qc_json") or ""), str(item.get("qc_markdown") or "")],
                    evidence_family="face_embedding",
                )
                continue
        if int(machine.get("intra_checked") or 0) <= 0:
            add(
                BLOCK,
                "成片身份回验",
                manifest_path,
                f"{clip_id} dense_face_watch 镜缺片内近脸身份采样 qc_machine.intra_checked；"
                "必须重跑 video_runner accept/video_qc，不能只凭首帧和接缝验收。",
                return_to_stage="video",
                evidence_family="face_embedding",
            )
        if not ready_packets:
            add(
                BLOCK,
                "成片身份回验",
                manifest_path,
                f"{clip_id} dense_face_watch 镜缺 video_face_drift_watch 密集抽帧包；"
                f"请跑 `python3 skills/n2d/n2d-review/scripts/video_face_drift_watch.py <作品根> {ep} --video <本clip.mp4> --clip {clip_id} --write`。",
                return_to_stage="video",
                affected_artifacts=[manifest_path],
                evidence_family="face_embedding",
            )
            continue
        if stage in {"compose", "review"} and not human_pass:
            add(
                WARN if stage == "compose" else BLOCK,
                "成片身份回验",
                ready_packets[-1][0],
                f"{clip_id} 已有密集抽帧包，但缺 human_review.identity_verdict=pass；"
                "交付验收前必须人工看 contact sheet，确认清晰近脸仍是同一角色。真脸漂不能签收。",
                return_to_stage="video",
                affected_artifacts=[ready_packets[-1][0], str(ready_packets[-1][1].get("contact_sheet") or "")],
                evidence_family="human_signoff",
            )
def check_motion_identity_priority(route: Mapping[str, Any], routes_path: str, idx: int) -> None:
    """High-action clips must state how motion freedom and identity lock are reconciled."""
    if not _route_is_high_action(route):
        return
    identity = str(route.get("identity_requirement") or "").strip().lower()
    if identity in {"", "none", "not_needed"}:
        return
    clip_id = str(route.get("clip_id") or f"routes[{idx}]")
    plan = route.get("identity_preservation_plan") or route.get("motion_identity_priority")
    recipe = route.get("execution_recipe") if isinstance(route.get("execution_recipe"), Mapping) else {}
    refs = recipe.get("reference_inputs") if isinstance(recipe.get("reference_inputs"), Mapping) else {}
    recipe_plan = refs.get("identity_preservation_plan") if isinstance(refs, Mapping) else None
    if isinstance(plan, Mapping) and plan:
        return
    if isinstance(recipe_plan, Mapping) and recipe_plan:
        return
    motion = route.get("motion_control") if isinstance(route.get("motion_control"), Mapping) else {}
    sev = BLOCK if motion.get("required") is True else WARN
    add(
        sev,
        "动作身份优先级",
        routes_path,
        f"{clip_id} 是高动作/接触/奇观镜且 identity_requirement={route.get('identity_requirement')}，但缺 identity_preservation_plan；"
        "请声明何时允许减少静态锚点以保物理/动作、如何保留角色身份、以及失败时拆近景身份镜/动作远景的方案。",
        return_to_stage="video_prompt",
        risk_score=0.75 if sev == BLOCK else 0.6,
        affected_shots=[clip_id],
        affected_artifacts=[routes_path],
        evidence_family="text_contract",
    )
def check_video_model_routes(root: str, ep: str, overview_text: str, overview_path: str) -> None:
    if "本集模型路由表" not in overview_text:
        add(BLOCK, "模型路由", overview_path, "缺「本集模型路由表」；出视频必须先跑 n2d-model-router，不能固定一个视频模型或临场乱选后端")
    p = os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json")
    if not os.path.isfile(p):
        add(BLOCK, "模型路由", p, "缺 video_model_routes.json；先运行 `python3 skills/n2d/n2d-model-router/scripts/router.py <作品根> 第N集 --write`")
        return
    try:
        data = json.load(open(p, encoding="utf-8"))
    except Exception as exc:
        add(BLOCK, "模型路由", p, f"video_model_routes.json 解析失败：{exc}")
        return
    if data.get("kind") != VIDEO_MODEL_ROUTES_KIND:
        add(BLOCK, "模型路由", p, f"video_model_routes.json kind 必须是 {VIDEO_MODEL_ROUTES_KIND}")
    routes = data.get("routes")
    if not isinstance(routes, list) or not routes:
        add(BLOCK, "模型路由", p, "video_model_routes.json routes 为空；逐 Clip 必须有 primary/fallback/mode")
        return
    check_backend_consistency_scope(data, [r for r in routes if isinstance(r, Mapping)], p)
    check_model_route_baseline_policy(root, ep, data, routes, p)
    drift = data.get("baseline_drift")
    if isinstance(drift, list) and drift:
        route_by_id = {str(r.get("clip_id") or ""): r for r in routes if isinstance(r, dict)}
        strict: List[object] = []
        for d in drift:
            route = route_by_id.get(str((d or {}).get("clip_id") or "")) if isinstance(d, dict) else None
            if route is None and isinstance(d, dict):
                route = {"shot_type": d.get("shot_type")}
            if isinstance(route, dict) and _route_needs_model_baseline(route) and not _baseline_override_accepted(data, route):
                strict.append(d)
        sample = "、".join(
            f"{d.get('clip_id')}({d.get('shot_type')}):{d.get('was')}→{d.get('now')}"
            for d in drift[:5] if isinstance(d, dict)
        )
        sev = BLOCK if strict else WARN
        add(
            sev,
            "后端跨集锁",
            p,
            f"{len(drift)} 个 clip 的 shot_type 自然路由与 设定库/model_routes_baseline 不符，已按基线锚定（原后端降 fallback）；"
            + ("高风险/含角色镜头的路由漂移必须写结构化 baseline_override（accepted/reviewer/reason/expires_at/affected_routes）或刷新基线后重跑。"
               if sev == BLOCK else "确认基线后端仍合适，否则 --write-baseline 刷新基线。")
            + sample,
            return_to_stage="video_prompt",
        )
    fallback_setting = get_setting(root, "视频备用后端", "").strip()
    allow_empty_fallback = (
        data.get("routing_mode") == "fixed_default"
        and bool(fallback_setting)
        and (fallback_setting.lower() in FALLBACK_OFF_VALUES or fallback_setting in FALLBACK_OFF_VALUES)
    )
    required = ("clip_id", "shot_type", "primary_backend", "fallback_backends", "mode", "native_audio_policy", "identity_requirement", "motion_control", "degrade_plan")
    frame_requirements = _storyboard_frame_requirements(root, ep)
    video_channel = get_setting(root, "生视频渠道", "").strip()
    check_video_backend_api_refresh(root, ep, routes, video_channel, p, allow_empty_fallback)
    check_mouth_visible_audit(root, ep, [r for r in routes if isinstance(r, Mapping)], p)
    for idx, route in enumerate(routes, 1):
        if not isinstance(route, dict):
            add(BLOCK, "模型路由", p, f"routes[{idx}] 不是对象")
            continue
        for key in required:
            if key == "fallback_backends" and route.get(key) == [] and allow_empty_fallback:
                continue
            if key not in route or route.get(key) in (None, "", []):
                add(BLOCK, "模型路由", p, f"{route.get('clip_id', f'routes[{idx}]')} 缺字段：{key}")
        mode = str(route.get("mode") or "").strip().lower()
        identity = str(route.get("identity_requirement") or "").strip().lower()
        check_native_av_voice_fallback_route(root, ep, route, p, idx)
        if mode in {"text2video", "t2v"} and identity not in {"", "none", "not_needed"}:
            clip_id = str(route.get("clip_id") or f"routes[{idx}]")
            if route.get("experimental_t2v") is not True:
                add(
                    BLOCK,
                    "T2V动作通道",
                    p,
                    f"{clip_id} 含身份要求(identity_requirement={route.get('identity_requirement')})却 mode=text2video，"
                    "必须由 n2d-model-router 明确标 experimental_t2v=true；否则回退 image2video/frames2video，"
                    "不可让文生视频绕过首帧、身份参考和风格链。",
                    return_to_stage="video_prompt",
                )
            plan = route.get("t2v_identity_reference_plan")
            if route.get("experimental_t2v") is True and (not isinstance(plan, Mapping) or not plan):
                add(
                    BLOCK,
                    "T2V动作通道",
                    p,
                    f"{clip_id} experimental_t2v=true 但缺 t2v_identity_reference_plan；"
                    "请在 storyboard/template_contract 写 reference_inputs、identity anchors、degrade_plan 后重跑路由，"
                    "或回退 image2video/frames2video。",
                    return_to_stage="script_stage2",
                )
        if _identity_route_requires_character_refs(route) and not _route_clip_character_refs(route):
            clip_id = str(route.get("clip_id") or f"routes[{idx}]")
            add(
                BLOCK,
                "模型路由",
                p,
                f"{clip_id} identity_requirement={route.get('identity_requirement')} 但缺结构化 clip_characters[]；"
                "请重跑 n2d-model-router 生成逐镜角色绑定，避免 gate 无法判断本 clip 的真实身份锁范围。",
                return_to_stage="video_prompt",
            )
        flags = route.get("risk_flags")
        if isinstance(flags, list) and "long_duration" in flags and not _route_has_supported_duration_segment_relay(route):
            clip_id = str(route.get("clip_id") or f"routes[{idx}]")
            primary = str(route.get("primary_backend") or "")
            max_sec = route.get("max_clip_seconds") or video_backend_max_seconds(primary)
            add(
                BLOCK,
                "单Clip时长",
                p,
                f"{clip_id} 超出 primary 后端 {primary or 'unknown'} 单 Clip 上限 {max_sec}s；回 n2d-script 阶段2 拆 Clip，或重跑 n2d-model-router 选择支持更长单镜的后端后再出视频",
                return_to_stage="script_stage2",
                rerun_scope="按后端单 Clip 上限重切 storyboard.json clips[].duration / 接力契约，重跑 n2d-model-router 与 video_preflight；未过 gate 不出视频。",
                affected_artifacts=[
                    f"脚本/{ep}/storyboard.json",
                    f"出视频/{ep}/prompt/video_model_routes.json",
                    f"出视频/{ep}/prompt",
                ],
            )
        check_route_frame_capability(root, ep, route, p, idx, frame_requirements, video_channel)
        check_route_execution_recipe(route, p, idx)
        check_motion_identity_priority(route, p, idx)
        check_motion_control_route(root, ep, route, p, idx)
        check_action_choreography_route(route, p, idx)
        # ③ 一角一后端亲和：router 已尽力把核心角色硬钉到原生主体后端；剩余冲突多为同镜多个锁脸后端
        # 无法同时满足，需要拆镜/分区，核心冲突 BLOCK，非核心冲突 WARN。
        conflicts = route.get("character_backend_conflicts")
        if isinstance(conflicts, list) and conflicts:
            clip_id = str(route.get("clip_id") or f"routes[{idx}]")
            bits = "；".join(f"{c.get('character')} 原生主体在 {c.get('prefers_backend')}，本镜路由 {c.get('routed_backend')}"
                             for c in conflicts if isinstance(c, dict))
            sev = BLOCK if any(isinstance(c, dict) and (c.get("enforce") or c.get("core")) for c in conflicts) else WARN
            action = "必须拆正反打/分区让各核心角色走自己的原生后端，或重注册到同一后端" if sev == BLOCK else "拆正反打让该角色单独走其原生后端，或本镜改走该后端，或人工确认可接受"
            add(sev, "一角一后端", p,
                f"{clip_id} 跨集后端亲和冲突：{bits}。同角色跨集换后端→脸质感漂移；处理：{action}。",
                return_to_stage="video")


def check_storyboard_video_feasibility_before_images(root: str, ep: str) -> None:
    """Catch video duration/boundary-frame debt before paid episode images.

    The final video compiler is authoritative, but waiting for it used to let
    multi-shot clips consume image budget before discovering that an editorial
    boundary frame was missing.  This lightweight planning pass consumes the
    same frame-strategy selector and the router output when available.
    """
    storyboard_path = os.path.join(root, "脚本", ep, "storyboard.json")
    storyboard = load_json(storyboard_path)
    if not isinstance(storyboard, Mapping):
        return
    routes_path = os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json")
    route_data = load_json(routes_path)
    routes = route_data.get("routes") if isinstance(route_data, Mapping) else []
    route_map = {
        str(row.get("clip_id") or ""): row
        for row in routes or [] if isinstance(row, Mapping)
    }
    channel = get_setting(root, "生视频渠道", "").strip()
    default_backend = get_setting(root, "生视频模型", "").strip() or "seedance"
    clips = storyboard.get("clips") if isinstance(storyboard.get("clips"), list) else []
    for idx, clip in enumerate(clips, 1):
        if not isinstance(clip, Mapping):
            continue
        clip_id = str(clip.get("clip_id") or clip.get("id") or f"Clip_{idx:02d}")
        route = route_map.get(clip_id, {})
        backend = str(route.get("primary_backend") or default_backend)
        shots = [row for row in clip.get("shots") or [] if isinstance(row, Mapping)]
        editorial = [row for row in shots if any(row.get(k) for k in ("lens", "camera", "shot_size"))]
        if len(editorial) <= 1:
            continue
        continuity = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
        anchors = [row for row in continuity.get("anchors") or [] if isinstance(row, Mapping)]
        executable_anchors = [
            row for row in anchors
            if str(row.get("use") or "split").strip().lower() not in {"qc", "reference", "reference_qc", "review"}
        ]
        take_policy = str(clip.get("take_policy") or continuity.get("take_policy") or "").strip().lower()
        strategy = select_video_frame_strategy(
            backend,
            channel,
            shot_count=len(editorial),
            anchor_count=len(executable_anchors),
            need_end=bool(clip.get("endframe_png")) or needs_end_anchor(continuity),
            requires_mid_anchors=bool(route.get("risk_flags") and "split_relay_required" in route.get("risk_flags", [])),
            explicit=str((continuity.get("frame_strategy") or {}).get("strategy") if isinstance(continuity.get("frame_strategy"), Mapping) else continuity.get("frame_strategy") or ""),
            take_policy=take_policy,
            duration_sec=clip.get("duration") if isinstance(clip.get("duration"), (int, float)) else None,
        )
        if str(strategy.get("strategy") or "") == "edit_cut_pending_assets":
            add(
                BLOCK, "视频可执行性前置", storyboard_path,
                f"{clip_id} 在出图前已可判定为多镜位 edit_cut，但缺镜位边界帧/尾帧；"
                "先把边界图加入 anchor plan 和出图任务，再开始整集付费生图。",
                return_to_stage="script_stage2",
                affected_shots=[clip_id],
                affected_artifacts=[storyboard_path, f"出图/{ep}/prompt"],
            )
def check_motion_control_manifest(root: str, path: str, route: Dict[str, object], required_inputs: List[str]) -> None:
    data = load_json(path)
    loc = path
    if not isinstance(data, dict):
        add(BLOCK, "Motion Control", loc, "motion_control_manifest.json 不是 JSON 对象")
        return
    if data.get("kind") != MOTION_CONTROL_KIND:
        add(BLOCK, "Motion Control", loc, f"motion_control_manifest.json kind 必须是 {MOTION_CONTROL_KIND}")
    status = str(data.get("status") or "").strip()
    if status not in MOTION_CONTROL_READY_STATUSES:
        add(BLOCK, "Motion Control", loc, "status 必须是 ready 或 degrade_only；planned/pending 不能进入付费出视频")
        return
    route_clip_id = str(route.get("clip_id") or "").strip()
    manifest_clip_id = str(data.get("clip_id") or "").strip()
    if manifest_clip_id and route_clip_id and manifest_clip_id != route_clip_id:
        add(BLOCK, "Motion Control", loc, f"clip_id={manifest_clip_id} 与路由 {route_clip_id} 不一致")
    if status == "degrade_only":
        if _field_is_missing(data, "degrade_plan"):
            add(BLOCK, "Motion Control", loc, "status=degrade_only 时必须写 degrade_plan，明确拆手部/反打/释放帧等降级执行")
        return

    inputs = data.get("control_inputs")
    if not isinstance(inputs, dict):
        add(BLOCK, "Motion Control", loc, "status=ready 时必须有 control_inputs 对象")
        return
    for key in required_inputs:
        if key not in inputs or not _input_ready(root, inputs.get(key)):
            add(BLOCK, "Motion Control", loc, f"ready manifest 缺可用控制输入或本地资产：control_inputs.{key}")
    if _route_requires_contact_fields(route):
        for key in MOTION_CONTROL_CONTACT_FIELDS:
            if _field_is_missing(data, key):
                add(BLOCK, "Motion Control", loc, f"高危物理接触 manifest 缺字段：{key}")
    if _field_is_missing(data, "failure_modes"):
        add(WARN, "Motion Control", loc, "建议写 failure_modes：feature_melting / limb_fusion / body_interpenetration 等，方便审片回流")
def check_motion_control_route(root: str, ep: str, route: Dict[str, object], routes_path: str, idx: int) -> None:
    loc = f"{routes_path} {route.get('clip_id', f'routes[{idx}]')}"
    motion = route.get("motion_control")
    if not isinstance(motion, dict):
        add(BLOCK, "Motion Control", loc, "缺 motion_control 对象；重新跑 n2d-model-router 生成可审计控制契约")
        return
    for key in MOTION_CONTROL_ROUTE_FIELDS:
        if key not in motion:
            add(BLOCK, "Motion Control", loc, f"motion_control 缺字段：{key}")

    requires_control = _motion_control_required_for_route(route)
    if not requires_control:
        return
    if motion.get("level") != "required" or motion.get("required") is not True or motion.get("manifest_required") is not True:
        add(BLOCK, "Motion Control", loc, "高危动作/物理镜头必须 motion_control.level=required 且 manifest_required=true")
    manifest_path = str(motion.get("manifest_path") or "").strip()
    if not manifest_path:
        add(BLOCK, "Motion Control", loc, "高危动作/物理镜头缺 motion_control.manifest_path")
        return
    abs_manifest = _resolve_under_root(root, manifest_path)
    if not os.path.isfile(abs_manifest):
        add(BLOCK, "Motion Control", abs_manifest, "缺 motion_control_manifest.json；必须先准备 ready 控制资产，或写 status=degrade_only 的拆镜 manifest")
        return
    required_inputs = motion.get("required_inputs") if isinstance(motion.get("required_inputs"), list) else []
    check_motion_control_manifest(root, abs_manifest, route, [str(item) for item in required_inputs])
def check_action_choreography_route(route: Dict[str, object], routes_path: str, idx: int) -> None:
    shot_type = str(route.get("shot_type") or "").strip()
    if shot_type not in ACTION_CHOREOGRAPHY_SHOT_TYPES:
        return
    loc = f"{routes_path} {route.get('clip_id', f'routes[{idx}]')}"
    choreography = route.get("action_choreography")
    if not isinstance(choreography, dict):
        add(BLOCK, "动作编排", loc, "高动作镜头缺 action_choreography 对象；重跑 n2d-model-router 生成动作编排契约")
        return
    if choreography.get("required") is not True:
        add(BLOCK, "动作编排", loc, "高动作镜头 action_choreography.required 必须为 true")
    for key in ("required_fields", "failure_modes", "gate_policy", "degrade_plan"):
        if key == "degrade_plan":
            if _field_is_missing(route, "degrade_plan") and _field_is_missing(choreography, "degrade_plan"):
                add(BLOCK, "动作编排", loc, "动作编排缺 degrade_plan；失败后必须有拆镜/降级路径")
            continue
        if _field_is_missing(choreography, key):
            add(BLOCK, "动作编排", loc, f"action_choreography 缺字段：{key}")
    declared = set(str(x) for x in choreography.get("required_fields", []) if str(x).strip()) if isinstance(choreography.get("required_fields"), list) else set()
    missing = [field for field in _action_choreography_required_fields(shot_type) if field not in declared]
    if missing:
        add(BLOCK, "动作编排", loc, "action_choreography.required_fields 缺字段：" + ", ".join(missing))


def _route_has_supported_duration_segment_relay(route: Mapping[str, object]) -> bool:
    plan = route.get("duration_segment_relay")
    if not isinstance(plan, Mapping) or plan.get("supported") is not True:
        return False
    segments = plan.get("segments")
    if not isinstance(segments, list) or not segments:
        return False
    try:
        cap = float(plan.get("max_clip_seconds") or route.get("max_clip_seconds") or video_backend_max_seconds(str(route.get("primary_backend") or "")))
    except (TypeError, ValueError):
        cap = 0.0
    if cap <= 0:
        return False
    for segment in segments:
        if not isinstance(segment, Mapping):
            return False
        try:
            sec = float(segment.get("duration_sec") or 0.0)
        except (TypeError, ValueError):
            return False
        if sec <= 0 or sec > cap:
            return False
        if not segment.get("from_frame") or not segment.get("to_frame"):
            return False
    recipe = route.get("execution_recipe")
    if isinstance(recipe, Mapping):
        video_segments = recipe.get("video_segments")
        if not isinstance(video_segments, Mapping) or video_segments.get("required") is not True:
            return False
    return True


def _policy_line_requests_native_speech(policy_line: str) -> bool:
    text = str(policy_line or "").strip().lower()
    if "allow_native_speech" in text:
        return True
    return bool(re.search(r"(?<!no_)native_speech", text))


def check_image_prompt_overview(root: str, ep: str) -> None:
    """Image overview must carry the episode-level visual contract.

    The image stage is where visual variables get baked into pixels (color,
    light position, axis/eyeline, character state, shot-size ladder).  Anything
    the video stage cannot change must be decided here, in the overview, before
    any paid image call — mirroring the video stage's director contract so the
    two contracts share one source instead of being re-invented downstream.
    """
    p = os.path.join(root, "出图", ep, "prompt", "00_总览.md")
    if not os.path.isfile(p):
        # 总览缺失由 check_shared_image_index 单独阻断，这里只管契约内容，避免重复报错
        return
    text = open(p, encoding="utf-8").read()
    if "本集视觉一致性契约" not in text:
        add(BLOCK, "契约继承", p, "缺「本集视觉一致性契约」；像素层导演决策（色调/光位/轴线/状态/景别）必须在出图总览先锁，不能下推到出视频")
        return
    for key in ("色调基线", "光位锚", "轴线", "状态演进", "景别阶梯"):
        if key not in text:
            add(BLOCK, "契约继承", p, f"本集视觉一致性契约缺字段：{key}")
    check_markdown_style_contract(text, p, "出图总览")
def _compiled_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def check_video_clip_prompt_section(path: str, section: str, route: Optional[Dict[str, Any]] = None) -> None:
    name = _headline(section, "Clip")
    loc = f"{path} {name}"

    required_fields = (
        ("导演意图", "缺导演意图；每条视频 prompt 必须先说明本镜剧情功能和为什么这样拍"),
        ("起幅", "缺起幅；必须写清从首帧/上一 Clip 接什么姿态、视线、道具和场景状态开始"),
        ("落幅", "缺落幅；必须写清结尾停到哪里，服务下一镜怎么切"),
        ("场面调度", "缺场面调度；必须锁人物左右站位、轴线、前后景或无人物的画面重心"),
        ("表演节拍", "缺表演节拍；必须按时间段写人物/光效/环境的节拍，不能只有静态动作"),
        ("运动精修", "缺运动精修；必须写幅度/能量/身体守卫，避免视频模型把近景脸、手部和肢体拉变形"),
        ("环境交互", "缺环境交互；必须写动作对光影/粒子/道具/背景的反馈，避免视频只做静态缩放"),
    )
    for label, msg in required_fields:
        if not _has_field(section, label):
            add(BLOCK, "导演调度", loc, msg)

    if "衔接设计" not in section:
        add(BLOCK, "导演调度", loc, "缺衔接设计；视频 prompt 必须继承故事板接力契约")
    if "continuity" not in section:
        add(BLOCK, "导演调度", loc, "缺 continuity 块；start/action/end/constraints/negative 无法被校验")
    for key in ("start_state", "action", "end_state", "constraints", "negative"):
        if key not in section:
            add(BLOCK, "导演调度", loc, f"continuity 缺字段：{key}")

    compiled_prompt = parse_compiled_markdown(section)
    if compiled_prompt is None:
        add(
            BLOCK,
            "prompt compiler",
            loc,
            "缺「后端编译提交 prompt」；完整生产合同不能直接当模型 prompt。重新运行 n2d-video prompt_pack.py，按 primary_backend 编译唯一提交指令。",
        )
    else:
        for key in (
            "kind", "version", "profile_version", "profile", "backend", "mode",
            "language", "native_audio_policy", "source_contract_sha256",
        ):
            if not str(compiled_prompt.get(key) or "").strip():
                add(BLOCK, "prompt compiler", loc, f"编译元数据缺字段：{key}")
        if compiled_prompt.get("kind") != COMPILED_VIDEO_PROMPT_KIND:
            add(BLOCK, "prompt compiler", loc, f"编译产物 kind 错误：{compiled_prompt.get('kind')}")
        compiler_version = compiled_prompt.get("version")
        if compiler_version not in {1, 2}:
            add(BLOCK, "prompt compiler", loc, f"不支持的编译产物 version={compiler_version}")
        elif compiler_version == 1:
            add(
                WARN,
                "prompt compiler",
                loc,
                "仍在使用 v1 编译产物：缺少帧策略与后端时长量化合同；请重新运行 n2d-video prompt_pack.py 升级到 v2。",
            )
        else:
            for key in ("frame_strategy",):
                if not str(compiled_prompt.get(key) or "").strip():
                    add(BLOCK, "prompt compiler", loc, f"v2 编译元数据缺字段：{key}")
            duration_plan = compiled_prompt.get("duration_plan")
            if not isinstance(duration_plan, dict):
                add(BLOCK, "prompt compiler", loc, "v2 编译元数据缺 duration_plan；无法区分剪辑目标与后端请求时长")
            else:
                for key in (
                    "story_span_sec", "edit_target_sec", "backend_request_sec",
                    "action_start_sec", "action_end_sec", "hold_end_sec", "trim_mode",
                ):
                    if duration_plan.get(key) in (None, ""):
                        add(BLOCK, "prompt compiler", loc, f"v2 duration_plan 缺字段：{key}")
                edit_target = _compiled_float(duration_plan.get("edit_target_sec"))
                backend_request = _compiled_float(duration_plan.get("backend_request_sec"))
                if edit_target is not None and backend_request is not None:
                    if backend_request + 0.05 < edit_target and not duration_plan.get("requires_split"):
                        add(BLOCK, "prompt compiler", loc, "后端请求时长短于剪辑目标但未声明 requires_split")
            strategy = str(compiled_prompt.get("frame_strategy") or "").strip().lower()
            if strategy == "edit_cut_pending_assets":
                add(BLOCK, "帧策略", loc, "多镜位 Clip 选择了 edit_cut，但缺少分镜边界图或尾帧；先补图再付费生成")
            elif strategy == "reroute_required":
                add(BLOCK, "帧策略", loc, "高风险连续镜需要中段控制，但当前后端无法消费；必须改路由或显式拆段")
        if not re.fullmatch(r"[0-9a-f]{64}", str(compiled_prompt.get("source_contract_sha256") or "")):
            add(BLOCK, "prompt compiler", loc, "编译元数据 source_contract_sha256 非 64 位 SHA-256；无法追溯来源合同")
        expected_backend = normalize_video_prompt_backend((route or {}).get("primary_backend")) if route else ""
        actual_backend = normalize_video_prompt_backend(compiled_prompt.get("backend"))
        if expected_backend and actual_backend != expected_backend:
            add(
                BLOCK,
                "prompt compiler",
                loc,
                f"编译 backend={actual_backend} 与 route.primary_backend={expected_backend} 不一致；不得拿别的后端口径提交。",
            )
        expected_mode = str((route or {}).get("mode") or "").strip().lower()
        actual_mode = str(compiled_prompt.get("mode") or "").strip().lower()
        if expected_mode and actual_mode != expected_mode:
            add(BLOCK, "prompt compiler", loc, f"编译 mode={actual_mode} 与 route.mode={expected_mode} 不一致")
        route_policy = str((route or {}).get("native_audio_policy") or "none").strip().lower()
        if expected_mode == "native_av" or route_policy == "native_speech":
            route_policy = "native_speech"
        actual_policy = str(compiled_prompt.get("native_audio_policy") or "").strip().lower()
        if route and actual_policy != route_policy:
            add(
                BLOCK,
                "prompt compiler",
                loc,
                f"编译 native_audio_policy={actual_policy} 与 route 真值 {route_policy} 不一致",
            )
        lint = lint_compiled_prompt(compiled_prompt)
        for code in lint.get("errors", []):
            add(BLOCK, "prompt compiler", loc, f"提交 prompt 结构错误：{code}")
        for code in lint.get("warnings", []):
            add(WARN, "prompt compiler", loc, f"提交 prompt 可进一步精简：{code}")

    # 在场链属于严格生产合同与真实输入层，不要求重复塞进模型文本。
    for key in ("required_presence", "offscreen_presence", "forbidden_presence"):
        if key not in section:
            add(
                BLOCK,
                "人物在场链",
                loc,
                f"完整合同缺 {key}；必须把 storyboard.entity_schedule 的必在/画外/禁入真值传到执行配方与 QC。",
            )
    if not (_has_field(section, "接缝执行包") or _has_field(section, "Handoff Package")):
        add(
            BLOCK,
            "接缝执行包",
            loc,
            "缺接缝执行包；每条视频 prompt 必须把 seam_mode/first_frame/end_frame/midframes/need_end_anchor/anchor_consumption/fallback 写成执行真值。",
        )
    else:
        for key in ("seam_mode", "first_frame", "end_frame", "midframes", "need_end_anchor", "anchor_consumption", "fallback"):
            if key not in section:
                add(BLOCK, "接缝执行包", loc, f"接缝执行包缺字段：{key}")
    if not (_has_field(section, "执行配方") or _has_field(section, "Execution Recipe")):
        add(
            BLOCK,
            "执行配方",
            loc,
            "缺执行配方 / Execution Recipe；视频 prompt 必须说明 frame_inputs/reference_inputs/control_inputs/audio_inputs/fallback/anchor_consumption，不能只交裸文本 prompt 给后端。",
        )
    else:
        for key in ("frame_inputs", "reference_inputs", "control_inputs", "audio_inputs", "fallback", "anchor_consumption"):
            if key not in section:
                add(BLOCK, "执行配方", loc, f"执行配方缺字段：{key}")
    if "角色身份注册层" not in section:
        add(BLOCK, "资产身份注册层", loc, "缺角色身份注册层字段；含角色镜必须继承 identity_registry.json，无人物镜写“无”")
    closeup_identity_risk = (
        "角色身份注册层" in section
        and not _has_any(section, ("角色身份注册层**：无", "角色身份注册层**： 无", "无人物", "空镜"))
        and _has_any(section, ("mouth_visible", "dialogue_closeup", "dialogue_shot_reverse", "CU", "MCU", "近景", "特写", "反打", "表情", "脸"))
    )
    if closeup_identity_risk:
        if not _has_any(section, ("近景/反打身份锁定", "近景身份锁定", "细粒度身份锁定")):
            add(
                BLOCK,
                "资产身份注册层",
                loc,
                "近景/反打/说话镜缺细粒度身份锁定；必须写脸型、五官比例、发型发髻、标志配饰、服装配色和脸部特写/表情参考或回退/保真实现方案",
            )
        if not _has_any(section, ("脸型", "五官", "发型", "发髻")):
            add(BLOCK, "资产身份注册层", loc, "近景身份锁定未写脸型/五官/发型发髻等不可漂项")
        if not _has_any(section, ("脸部特写", "表情参考", "expressions", "正脸", "front", "reference_group")):
            add(WARN, "资产身份注册层", loc, "近景身份锁定未明确脸部特写/表情参考或 reference_group 来源；配角近景容易漂移")
    if not _has_field(section, "模型路由"):
        add(BLOCK, "模型路由", loc, "缺模型路由字段；每 Clip 必须继承 video_model_routes.json 的 shot_type/primary/fallback/mode/degrade_plan")
    else:
        for key in ("shot_type", "primary_backend", "fallback", "mode", "degrade_plan"):
            if key not in section:
                add(BLOCK, "模型路由", loc, f"模型路由缺字段：{key}")
        has_character_identity_layer = (
            "角色身份注册层" in section
            and not _has_any(section, ("角色身份注册层**：无", "角色身份注册层**： 无", "无人物", "空镜"))
            and bool(re.search(r"\bCHAR_[A-Za-z0-9_]+(?:/[^`\s，；、*]+)?\*?\b", section))
        )
        if has_character_identity_layer and re.search(r"identity_requirement\s*=\s*none\b", section):
            add(
                BLOCK,
                "模型路由",
                loc,
                "模型路由 identity_requirement=none 但本 Clip 写了角色身份注册层/CHAR_xx；必须改为 reference_group 或后端原生身份绑定，避免执行端少传身份参考。",
            )
        mode_value = str((route or {}).get("mode") or "").strip().lower()
        identity_req_value = str((route or {}).get("identity_requirement") or "").strip().lower()
        if mode_value and mode_value not in {"text2video", "t2v"} and re.search(r"frame_inputs\s*=\s*(无|none|null|n/a|na)(?:[；;,，\s]|$)", section, re.I):
            add(
                BLOCK,
                "执行配方",
                loc,
                f"路由 mode={mode_value} 需要首帧/尾帧/锚帧等图像入参，但执行配方 frame_inputs 为空；先回 n2d-video prompt/router 修真实入参。",
            )
        if (
            identity_req_value
            and identity_req_value not in {"none", "no", "无", "not_required"}
            and has_character_identity_layer
            and re.search(r"reference_inputs\s*=\s*(无|none|null|n/a|na)(?:[；;,，\s]|$)", section, re.I)
        ):
            add(
                BLOCK,
                "执行配方",
                loc,
                f"路由 identity_requirement={identity_req_value} 且本 Clip 含角色身份层，但执行配方 reference_inputs 为空；这会让后端只按首帧猜脸，必须传 reference_group/Character ID/Face Lock 或明确降级保真拍法。",
            )
    shot_type = _section_shot_type(section, route)
    if shot_type in ACTION_CHOREOGRAPHY_SHOT_TYPES:
        if not (_has_field(section, "动作编排契约") or _has_field(section, "Action Choreography")):
            add(
                BLOCK,
                "动作编排",
                loc,
                "打斗/追逐/飞行/御兽/马车/飞舟/现代车辆/尾随潜入等高动作镜头缺「动作编排契约」；必须写 beats、speed_curve、spatial_path、camera_path、readability_beats 及该镜专属字段，不能只写“精彩打斗/高速飞行/骑兽狂奔/马车疾驰/车流疾驰/暗处尾随”。",
            )
        else:
            missing = _missing_contract_fields(section, _action_choreography_required_fields(shot_type))
            if missing:
                add(BLOCK, "动作编排", loc, "动作编排契约缺字段：" + ", ".join(missing))
        if not _has_any(section, ("动作编排", "Action Choreography", "readability_beats")):
            add(BLOCK, "动作编排", loc, "生成后自检必须包含动作编排/可读性检查项，确认动作方向、速度曲线、空间路径和命中/距离/高度落点。")
    if _section_requires_motion_control(section):
        if not (_has_field(section, "Motion Control") or _has_field(section, "物理交互控制")):
            add(BLOCK, "Motion Control", loc, "高危动作/物理镜头缺 Motion Control / 物理交互控制字段；必须继承 route.motion_control 和 manifest_path")
        else:
            for key in ("level", "manifest_path", "required_inputs", "failure_modes"):
                if key not in section:
                    add(BLOCK, "Motion Control", loc, f"物理交互控制字段缺：{key}")
        if not _has_any(section, ("FeatureMelting", "feature_melting", "特征融化")):
            add(BLOCK, "Motion Control", loc, "生成后自检必须包含 FeatureMelting/特征融化检查项")
    if "原生音画策略" not in section:
        add(BLOCK, "原生音画", loc, "缺原生音画策略字段；每 Clip 必须写 audio_intent/risk/mouth_visible/speech_policy/compose_policy，默认丢弃")
    else:
        for key in ("audio_intent", "risk", "mouth_visible", "speech_policy", "compose_policy"):
            if key not in section:
                add(BLOCK, "原生音画", loc, f"原生音画策略缺字段：{key}")
        route_native_policy = str((route or {}).get("native_audio_policy") or "").strip()
        route_mode = str((route or {}).get("mode") or "").strip()
        if route_native_policy == "native_speech" or route_mode == "native_av":
            policy_line = _native_audio_policy_line(section)
            if "native_speech" not in policy_line:
                add(BLOCK, "原生音画", loc, "路由表 native_audio_policy=native_speech，但本 Clip 原生音画策略未写 speech_policy=native_speech")
            if _has_any(policy_line, ("no_native_speech", "禁止原生人声", "无原生人声")):
                add(BLOCK, "原生音画", loc, "路由表要求 native_speech，说话镜不能同时写 no_native_speech / 禁止原生人声；应改为台词+口型由原生音画后端生成并由 compose 保留原片音轨")
            if not _has_any(policy_line, ("audio_intent=native_speech", "台词", "原生人声")):
                add(WARN, "原生音画", loc, "native_speech 镜建议写 audio_intent=native_speech，并说明台词文本/声源/口型策略")
            if not _has_any(policy_line, ("compose_policy=保留原片音轨", "保留原片音轨")):
                add(BLOCK, "原生音画", loc, "native_speech 镜 compose_policy 必须保留原片音轨；否则合成会丢原生台词")
        elif route_native_policy and route_native_policy != "native_speech":
            policy_line = _native_audio_policy_line(section)
            if _policy_line_requests_native_speech(policy_line):
                add(BLOCK, "原生音画", loc, f"路由表 native_audio_policy={route_native_policy}，本 Clip 不得写 native_speech/allow_native_speech")
        if _section_native_audio_opt_in(section) and route_native_policy != "native_speech" and route_mode != "native_av":
            native_policy = _native_audio_policy_line(section)
            if not _has_any(section, ("risk=low", "低风险")):
                add(BLOCK, "原生音画", loc, "原生环境声/音效 opt-in 仅允许低风险镜头；必须写 risk=low / 低风险理由")
            if not _has_any(native_policy, ("mouth_visible=no", "无口型", "嘴部不可见")):
                add(BLOCK, "原生音画", loc, "原生环境声/音效 opt-in 必须确认无口型或嘴部不可见")
            if not _native_audio_contract_ok(section):
                add(BLOCK, "原生音画", loc, "原生环境声/音效 opt-in 必须明确 no_native_speech / 禁止原生人声")
    # ④ 运镜越界 trip-wire：镜头运动含"廉价漂浮/旋转飞行/急速"类运镜 → 疑越 style_contract.运动边界
    m_cam = re.search(r"(?:镜头运动|镜头)[：:]([^\n；;。]*)", section)
    cam = m_cam.group(1) if m_cam else ""
    SUSPECT_MOVES = ("旋转", "360", "环绕飞", "飞行", "急速", "极速", "快速拉近", "急推", "急拉", "乱甩", "甩镜", "螺旋", "翻滚")
    hit = [w for w in SUSPECT_MOVES if w in cam]
    if hit:
        add(WARN, "运动一致性", loc,
            f"镜头运动含「{'/'.join(hit)}」，疑越本集运动边界——核对 `本集基础视觉风格契约/导演一致性契约` 的运动边界禁忌；如确需该运镜须有明确剧情理由（爽点/高光），否则换克制运镜")

    # ⑤ 运镜结构化（消费 CAMERA_MOVE_LEXICON·治"运镜全是自由散文、丢速度/方向"）：
    #    运镜是 2026 一等控制项（Seedance 参考视频运动 / Kling motion-control 端点）。WARN-only，不硬挡。
    if m_cam and cam.strip():
        cm = normalize_camera_move(cam)
        if not cm["recognized"]:
            add(WARN, "运动一致性", loc,
                "镜头运动未用结构化运镜词（推/拉/摇/移/升降/变焦/环绕/跟拍/甩镜/弧线/手持/固定…）：运镜是传达情绪与节奏"
                "最强的工具，自由散文下游模型常乱给。请从 CAMERA_MOVE_LEXICON 取词，运镜服务情绪（逼近=推近/释放=拉远/"
                "高光=环绕/压迫=固定），并填速度+方向 slot。")
        elif cm["moves"] and not cm["speeds"] and not cm["is_static"]:
            add(WARN, "运动一致性", loc,
                f"镜头运动「{'/'.join(m['zh'] for m in cm['moves'])}」缺速度档（缓慢/匀速/快速/轻微/急速冲击）："
                "运镜速度直接决定情绪与节奏感，请补速度词（CAMERA_SPEED_WORDS）。")

    if "检查清单（视频三件套自查" not in section:
        add(BLOCK, "prompt", loc, "缺提交前检查清单")
    if "自检（生成后逐条过" not in section:
        add(BLOCK, "prompt", loc, "缺生成后自检段")
def check_image_shot_prompt_section(path: str, idx: int, section: str,
                                    single_ref_backend: bool = False,
                                    root: str = "") -> None:
    name = _headline(section, f"镜头 {idx}")
    loc = f"{path} {name}"

    if root:
        selection = image_backend_adapter.current_image_backend_selection(root)
        compiled_audit = lint_compiled_image_section(
            section,
            expected_backend=selection.get("backend") or selection.get("access"),
            allowed_tasks=("shot_keyframe", "relay_edit", "multi_subject"),
        )
        for code in compiled_audit.get("errors") or []:
            add(
                BLOCK,
                "image prompt compiler",
                loc,
                f"编译图片请求结构错误：{code}。完整生产合同不得直接提交；请重新运行 n2d-image image_prompt_pack.py。",
                return_to_stage="image_prompt",
            )
        for code in compiled_audit.get("warnings") or []:
            add(WARN, "image prompt compiler", loc, f"编译图片请求可进一步精简：{code}")

    if "检查清单（八维自查" not in section:
        add(BLOCK, "prompt", loc, "缺提交前检查清单（八维自查·最易漏②机位/⑥光影/⑦张力）")
    if "**自检**" not in section and "逐镜自检" not in section and "自检（生成后逐张过" not in section:
        add(BLOCK, "prompt", loc, "缺生成后逐张自检段")
    if "重抽预算" not in section:
        add(BLOCK, "prompt", loc, "缺重抽预算字段；无法按主要人物/关键镜策略收口")
    if not _has_positive_prompt_heading(section, "中文"):
        add(BLOCK, "prompt", loc, "缺正向 prompt（中文）")
    if not _has_positive_prompt_heading(section, "英文"):
        add(BLOCK, "prompt", loc, "缺正向 prompt（英文）兜底")
    if "负向 prompt" not in section:
        add(BLOCK, "prompt", loc, "缺负向 prompt；人物/场景堵漏不可控")
    else:
        neg_match = re.search(r"(?ms)^###\s*负向 prompt[^\n]*\n(?P<body>.*?)(?=^###\s+|^##\s+|\Z)", section)
        neg_block = neg_match.group("body") if neg_match else ""
        if "风格禁忌" not in neg_block:
            add(BLOCK, "风格一致性", loc, "负向 prompt 未继承 style_contract.风格禁忌；风格禁忌只在契约不进逐镜负向=shot 级防不住风格漂（突然照片感/插画/高饱和），须把本集风格禁忌拼进本镜负向")
    if "导演视角八维" not in section:
        add(BLOCK, "prompt", loc, "缺导演视角八维表；分镜图不能只写画师式描述")
    image_prompt_fields = (
        "身份保持",
        "镜头构图",
        "动作瞬间",
        "场景光影",
        "情绪张力",
        "画风规格",
        "禁止",
    )
    for key in image_prompt_fields:
        if not _has_line_field(section, key):
            add(BLOCK, "prompt", loc, f"中文图片 prompt 缺字段：{key}")

    if not _has_field(section, "光位锚"):
        add(BLOCK, "光影一致性", loc, "缺光位锚字段；同场跨镜主光方向/色温/动机光源会飘，剪起来闪——须继承 00_总览 本场光位锚")
    else:
        # 色温数值化体检（消费 n2d_logic.color_temperature_findings·治"Kelvin 是自由文本从不校验"）：
        m_light = re.search(r"光位锚[^\n]*?[：:]([^\n]*)", section)
        for f in color_temperature_findings(m_light.group(1) if m_light else ""):
            add(WARN, "光影一致性", loc, f["msg"])
    if not _has_field(section, "运动余量"):
        add(BLOCK, "首帧起幅", loc, "缺起幅·运动余量字段；clip 首帧须是起幅而非动作顶点，并按计划运镜预留构图余量")

    refs = _reference_block(section)
    if not refs:
        add(BLOCK, "prompt", loc, "缺参考图块；分镜图必须多图参考派生，禁止纯文生图")
    else:
        if "定妆_" not in refs:
            add(BLOCK, "prompt", loc, "参考图块未引用共享定妆资产；会导致跨镜人物/场景漂移")
        if "强度" not in refs and "strength" not in refs.lower():
            add(WARN, "prompt", loc, "参考图块未标参考强度；多图参考派生稳定性不可复现")
        if _needs_scene_asset_binding(refs) and not _has_asset_id_binding(section, "LOC_"):
            add(
                BLOCK,
                "资产引用注册层",
                loc,
                "参考图块含关键场景定妆但缺 LOC_xx 绑定；必须写 `资产引用注册层` 并引用 asset_registry.json，让执行端自动取场景 reference_group / constraints / drift_forbidden。",
            )
        if _needs_prop_asset_binding(refs) and not _has_asset_id_binding(section, ("PROP_", "WEAPON_", "MOUNT_GROUP_", "OUTFIT_", "VFX_")):
            add(
                BLOCK,
                "资产引用注册层",
                loc,
                "参考图块含关键道具定妆但缺 PROP_/WEAPON_/MOUNT_GROUP_xx 绑定；必须写 `资产引用注册层` 并引用 asset_registry.json，锁道具结构、件数和禁漂项。",
            )

    if _needs_prop_structure_gate(section, name, refs) and not _has_prop_structure_rule(section):
        add(BLOCK, "道具结构", loc, "关键道具镜头缺结构唯一性闸门；毒酒壶/瓷壶须锁唯一短颈圆口、无侧嘴/斜嘴/双口/额外开口，匕首须一柄一刃，三件套件数须锁定，避免道具幻觉")

    for key in ("①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧"):
        if key not in section:
            add(BLOCK, "prompt", loc, f"导演八维缺 {key} 维标记")

    # 机位即态度，是最易漏的导演决策——②机位 标记在场不等于真填了机位。空/默认正面平视无理由 → WARN。
    cam = re.search(r"\|\s*②[^|]*\|\s*([^|\n]*?)\s*\|", section)
    if cam:
        value = cam.group(1).strip().strip("*` ")
        if (not value) or value in ("正面平视", "平视", "默认", "正面", "默认正面平视", "—", "-", "/"):
            add(WARN, "构图景别", loc,
                "②机位 为空或默认正面平视——机位即态度（八维最易漏）；给本镜一个有叙事理由的机位（俯/仰/过肩/侧/主观），默认平视须注明理由")

    if _section_has_character_refs(section):
        if not _has_character_aesthetic_baseline(section):
            add(
                WARN,
                "人物审美基线",
                loc,
                "含角色镜头缺 `人物审美基线` 或等价说明。除非角色圣经/剧情特别要求丑、怪、病、老、恐怖、粗粝或非主流，"
                "人物默认应按主流可播审美和镜头友好来写：五官比例协调、妆造服装精致耐看、光影让脸好看，同时不覆盖角色 DNA。",
            )
        if not re.search(r"(锚点句|anchor phrase)\s*[:：]", section, re.IGNORECASE):
            add(BLOCK, "角色一致性", loc, "含角色镜头缺锚点句；每镜必须拼角色卡锚点")
        if not _has_field(section, "视线方向"):
            add(BLOCK, "轴线一致性", loc, "含角色镜头缺视线方向；轴线/视线在出图阶段焊进像素、出视频改不动，正反打会穿帮——须对位 00_总览 本场轴线")
        if not _has_any(section, ("脸型与定妆一致", "角色脸/妆造未漂移", "脸/妆造未漂移", "妆造未漂移")):
            add(BLOCK, "角色一致性", loc, "含角色镜头自检未显式检查脸/妆造漂移")
        if not _has_any(section, ("服装配色一致", "服装", "配色")):
            add(BLOCK, "角色一致性", loc, "含角色镜头未显式锁服装/配色")
        if single_ref_backend and not _has_i2i_derivation(section):
            add(
                BLOCK,
                "角色一致性",
                loc,
                "无持久角色 ID 后端(如 Codex/OpenAI/Dreamina/Nano)逐镜重画脸：本镜(含首帧)未声明从共享定妆 "
                "image2image/多图参考派生——纯文生图会把角色重抽成新演员，跨集必漂。"
                "请写明生成方式=以 `定妆_<角色>` 为母图做 image2image/多图参考派生，禁纯文生图。"
                "（原生主体锁后端可豁免；本后端下**每个**角色镜都须 i2i 派生，不止尾帧。）",
            )
        if not _has_any(section, ("资产身份注册层", "身份注册", "identity_registry", "reference_group", "drift_forbidden")):
            add(BLOCK, "资产身份注册层", loc, "含角色镜头缺资产身份注册层约束；必须从 identity_registry.json 继承 reference_group / angle_policy / drift_forbidden")
        if not _has_character_id_binding(section):
            add(
                BLOCK,
                "资产身份注册层",
                loc,
                "含角色镜头缺明确角色 ID 绑定；必须写 `CHAR_xx/形态`，让执行端从 identity_registry.json 自动反查 reference_group，禁止只靠中文角色名或纯文描述生图。",
            )
        ambiguous = _multi_char_binding_ambiguity(section)
        if ambiguous:
            add(
                WARN,
                "资产身份注册层",
                loc,
                f"同框引用多个角色（{'、'.join(ambiguous)}）但未星标 primary（写法 `CHAR_xx*`）；"
                "多数后端单图只锁得住一个主体，不声明锁谁=后端随机挑、崩脸不可追责——"
                "按 资产身份注册层.md「多角色同框绑定规则」给最高优先角色加星，其余降级参考图组。",
            )
        if _needs_closeup_identity_lock(section, name) and not _has_closeup_identity_lock(section):
            add(
                BLOCK,
                "角色一致性",
                loc,
                "正反打/反应/表情近景缺近景身份锁定；fallback reference_group 容易只保留角色大类但重画脸型/发髻/配饰。"
                "请补 `近景/反打身份锁定` 字段，引用脸部特写或表情参考，并明确锁脸型/五官比例/发型发髻/标志配饰。",
            )
        if _needs_closeup_identity_lock(section, name) and not _has_i2i_tail_continuity_lock(section):
            add(
                BLOCK,
                "角色一致性",
                loc,
                "正反打/反应/表情尾帧缺图生图接力约束；只写身份锚点仍可能纯文重抽成新演员。"
                "请补 `尾帧接力生成方式` 字段：尾帧必须以上一张成图或同镜首帧 image2image/图生图为母图，"
                "只改表情/眼神/嘴角，不得纯文生图。",
            )
        if single_ref_backend and _codex_needs_face_reference(section, name) and not _codex_has_face_reference(section):
            add(
                BLOCK,
                "Codex锁脸",
                loc,
                "Codex/OpenAI/Dreamina/Nano/Gemini 这类无持久角色 ID 后端会逐镜重新解脸；"
                "近景/反打/大表情镜不能只靠普通多参考或锚点句。请在本镜显式引用同源脸部特写/表情库 "
                "（expressions / `定妆_<角色>_脸部特写.png` / `定妆_<角色>_表情*.png`），并让尾帧用 image2image 接力，只改表情不重画五官。",
            )
        if single_ref_backend and _codex_dark_vfx_face_risk(section, name) and not _codex_has_face_visibility_guard(section):
            add(
                BLOCK,
                "Codex锁脸",
                loc,
                "暗光/烟雾/VFX 叠脸会诱导无持久角色 ID 后端重画五官；本镜缺脸部可见性约束。"
                "请补约束：眼鼻嘴三角区清晰、特效/黑烟只在脸外侧或后景、不得遮住五官、不得重画脸。",
            )
        if "_侧" not in refs and "_半身" not in refs and "_全身" not in refs and "主体库" not in section and "角色ID" not in section:
            add(WARN, "角色一致性", loc, "含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂")
        chars = _character_names_in_refs(refs)
        # 多人同框（C6 剧情优先：≥4 张清晰脸该出就出，必须登记分区合成把它做对，不删戏/不砍人数）+ 锚点去重（④）。
        _wide_crowd = _has_any(section, ("远景", "大全景", "群像", "人海", "crowd", "wide shot", "extreme long", "ELS"))
        _multi_closeup = _has_any(section, ("ECU", "BCU", "CU", "MCU", "近景", "特写", "面部", "脸部", "反应镜", "表情镜")) \
            and not _has_any(section, ("远景", "全景", "中景"))
        # 把 ≥4 同框「做对」的执行策略（分区合成 / 原生主体策略）——登记了就放行该镜，由下面 ≥2 层继续校验槽位等细节。
        _has_multi_exec_strategy = (
            _has_codex_split_composite_strategy(section) or _has_native_multi_subject_strategy(section)
        )
        if len(chars) >= 4 and not _wide_crowd and not _has_multi_exec_strategy:
            add(
                BLOCK,
                "构图景别",
                loc,
                f"单镜清晰同框 ≥4 具名角色（{'/'.join(sorted(chars))}）未登记分区合成执行策略：单帧 co-gen 4+ 张清晰脸"
                "所有后端都难压（实测 ≤3 更稳）——但这是「要分区合成做对」，不是「删到 ≤3 / 砍同框戏」（设计宪法 C6 剧情优先）。"
                "剧情需要这场 ≥4 人同框就照出：登记 split_composite/分别出图+合成（每主体身份槽位）把每张脸分别做好再合成，"
                "或拆 establish+反打把整场戏拍全；确属远景群像（脸不解析）请在本镜显式标 `远景/群像`。",
                return_to_stage="image",
            )
        if len(chars) >= 2:
            # 升 BLOCK 后，逃生口收紧为「显式 split/分层 执行 token」——不再认裸的「反打/正反打」字样：
            # 那些常作为视线对位/身份锁定的样板话出现在每个对话镜里（一次生成多张脸的同框近景也会写），
            # 认它就等于永不触发。真·反打是拆成单人镜（每帧 1 张脸），本就不该是「多人同框」，故同框近景的
            # 放行只认 分别出图/分层合成/单人分层/景别分层 这类落地执行策略。
            _CLOSEUP_SPLIT_TOKENS = ("shot_reverse_shot", "split_composite", "regional_construct",
                                     "分区构建", "区域构建", "分别出图", "分角色出图",
                                     "拆成单人镜", "拆单人镜", "单人分层", "分层合成", "景别分层")
            if _multi_closeup and not _has_any(section, _CLOSEUP_SPLIT_TOKENS):
                # 多人近景同框是 cross-attention 串脸最高发档（2026 SOTA：单帧多主体身份必相互渗透，
                # 即便最强后端 ~85% 一致、近景更糟；公认最佳实践是「分开生成再合成」而非单帧绑定）。
                # 槽位绑定仍是「一次生成多张脸」，治不了近景串脸——必须拆开生成。
                # 2026-06 由 WARN 升 BLOCK（与「空间绑定对所有后端 block」同向，对最危险的近景档收口）。
                add(
                    BLOCK,
                    "构图景别",
                    loc,
                    f"多人近景同框（{'/'.join(sorted(chars))}）未声明反打/分层/分别出图：近景是多主体 cross-attention "
                    "串脸最高发档，槽位绑定（一次生成多张脸）治不住——必须拆「单人CU + 反打」或「单人分层出图 + 合成」"
                    "分开生成各自的脸；确需同框请降到中景/全景做景别分层（清晰主角1人，余者推后景/虚焦），"
                    "并登记 split_composite/分层合成执行策略。",
                    return_to_stage="image",
                )
            if single_ref_backend and not _has_any(section, ("区分锚点", "互斥锚点", "可区分性", "distinct anchor", "去重锚点", "撞色")):
                add(
                    WARN,
                    "角色一致性",
                    loc,
                    f"多人同框（{'/'.join(sorted(chars))}）缺 `区分锚点` 字段：同框角色发色/发型/服装主色越接近，越易被模型平均成同一张脸。"
                    "逐主体写 5–7 个互斥锚点（各自唯一发色/发型/服装主色HEX/标志配饰）并确保两两不撞色；"
                    "可读 reference_planner 的 `distinct_anchors` 处方。",
                )
            if single_ref_backend and _has_generic_reference_index_lock(section):
                add(
                    BLOCK,
                    "Codex锁脸",
                    loc,
                    "多角色同框镜使用了“参考图①/reference image 1”这类泛化身份锁。"
                    "无持久角色 ID 后端会把第 1 张参考误当成所有人的身份锚，造成配角串脸或重解脸。"
                    "请改成逐主体锁脸句：每个 `CHAR_xx/形态` 分别对应自己的定妆/脸部特写/表情库；"
                    "并在同框镜登记分别出图+合成或切统一的原生主体后端。",
                    return_to_stage="image",
                )
            if single_ref_backend:
                if not _has_codex_split_composite_strategy(section):
                    add(BLOCK, "角色一致性", loc,
                        f"单镜多角色同框（{'/'.join(sorted(chars))}）× 无持久角色 ID 后端(如 Codex)：普通多参考不是持久主体锁，"
                        "每个主体都会被重新解脸，且多人同框无硬位置/主体 ID 绑定时极易串脸。"
                        "本后端下只有「分别出图+合成/单人分层出图」这类硬降级能放行；"
                        "或把项目生图AI统一切到支持原生主体/角色ID的官方后端后再跑 gate。")
                elif not _has_multi_subject_identity_slots(section):
                    add(
                        BLOCK,
                        "角色一致性",
                        loc,
                        f"单镜多角色同框（{'/'.join(sorted(chars))}）虽登记了分层/合成，但缺 `多人同框身份槽位`。"
                        "无持久角色 ID 后端必须逐主体写 LEFT/RIGHT/FOREGROUND/BACKGROUND 槽位，"
                        "每个槽位绑定 `CHAR_xx/形态`、画面位置、视线、自己的脸部参考/表情库和 primary 星标；"
                        "否则分层合成阶段仍会串脸或无法追责。",
                        return_to_stage="image",
                    )
            elif not _has_native_multi_subject_strategy(section):
                add(BLOCK, "角色一致性", loc,
                    f"单镜多角色同框（{'/'.join(sorted(chars))}）× 原生主体后端：缺 `多人同框执行策略`"
                    "（native_subject_slots / 区域绑定 / 分别出图+合成）。多主体后端虽有主体绑定能力，但无显式"
                    "空间/主体策略时仍会把参考身份混到错位或把两张脸平均成同一张——逐主体写原生主体名额或区域绑定策略，"
                    "否则不放行（空间绑定是同框一致性硬约束，2026-06 起对所有后端 block，不再降级为建议）。",
                    return_to_stage="image")
            elif not _has_multi_subject_identity_slots(section):
                add(BLOCK, "角色一致性", loc,
                    f"单镜多角色同框（{'/'.join(sorted(chars))}）缺 `多人同框身份槽位`：逐主体绑定 CHAR_xx/形态、"
                    "画面槽位（LEFT/RIGHT/FOREGROUND/BACKGROUND）、视线与各自参考图组，避免多主体后端把参考身份混到错误位置——"
                    "空间槽位绑定是同框一致性硬约束，2026-06 起对所有后端 block，不再降级为建议。",
                    return_to_stage="image")
def check_video_prompt_frames(root: str, ep: str, stage: str = "video") -> None:
    """付费出视频前置：核验**视频 prompt（`01_clips.md`）实际引用的首帧/尾帧 PNG**——这是 runner
    （`parse_prompt_pack`）真正喂给后端的路径，与 `storyboard.firstframe_png` 分开誊抄、可能漂；
    `check_storyboard_contract` 查的是 storyboard 字段，这里查**真正提交的那条路径**，互补不重复。
      · 首帧 PNG 缺失 → BLOCK（image2video 必失败、白扣一次最贵的钱）；
      · 声明了尾帧但 PNG 缺失 → WARN（镜内双锚/relay 降级为单首帧）；
      · storyboard 需要尾锚但视频 prompt 漏写 `**尾帧**` → WARN（执行意图誊抄时丢失）；
      · storyboard 声明 `continuity.midframe` 但视频 prompt 该 Clip 漏写 `**中段锚帧**`、或引用的
        锚帧 PNG 缺失 → WARN（拆段意图誊抄时丢失/锚帧漂，runner 会按单段出，中段漂移风险回归）；
      · 视频 prompt 引用的首帧路径 ≠ storyboard.firstframe_png（两侧都存在但不是同一张）→ BLOCK
        （誊抄成另一张存在的 PNG，两侧各查存在全绿、却动了错的首帧）；尾帧不一致 → WARN。"""
    p = os.path.join(root, "出视频", ep, "prompt", "01_clips.md")
    if not os.path.exists(p):
        return  # 视频 prompt 缺失由 check_video_prompt_overview 负责
    text = open(p, encoding="utf-8").read()
    production = consistency_release_profile(root, stage, ep) == "production"
    frame_warn = BLOCK if production else WARN
    need_end: Dict[int, bool] = {}
    need_mid: Dict[int, int] = {}  # Clip → 声明的锚帧数（midframe=1；anchors=len）
    sb_first: Dict[int, str] = {}  # Clip → storyboard.firstframe_png（路径相等校验基准）
    sb_end: Dict[int, str] = {}    # Clip → storyboard continuity/top-level endframe_png
    sb = load_json(storyboard_path(root, ep))  # 只读取尾锚/中锚/首尾帧，不重复报 storyboard 缺失
    if isinstance(sb, dict) and isinstance(sb.get("clips"), list):
        for i, clip in enumerate(sb["clips"], 1):
            if isinstance(clip, dict) and isinstance(clip.get("continuity"), dict):
                cont = clip["continuity"]
                need_end[i] = needs_end_anchor(clip)
                if isinstance(cont.get("midframe"), dict):
                    need_mid[i] = 1
                elif isinstance(cont.get("anchors"), list):
                    need_mid[i] = len(cont["anchors"])
                if clip.get("firstframe_png"):
                    sb_first[i] = str(clip["firstframe_png"]).strip()
                endframe = (
                    cont.get("endframe_png")
                    or clip.get("endframe_png")
                    or clip.get("last_frame")
                    or clip.get("end_frame_png")
                )
                if endframe:
                    sb_end[i] = str(endframe).strip()

    def _missing(rel: str) -> bool:
        full = rel if os.path.isabs(rel) else os.path.join(root, rel)
        return not os.path.exists(full)

    def _same_path(a: str, b: str) -> bool:
        """两条 PNG 引用是否指向同一文件：归一化（去 ./、统一分隔符、相对根解析）后比对。"""
        def _norm(rel: str) -> str:
            full = rel if os.path.isabs(rel) else os.path.join(root, rel)
            return os.path.normpath(full)
        return _norm(a) == _norm(b)

    heads = list(_VID_CLIP_HEAD_RE.finditer(text))
    for idx, m in enumerate(heads):
        num = int(m.group(1))
        block = text[m.end(): heads[idx + 1].start() if idx + 1 < len(heads) else len(text)]
        loc = f"出视频/{ep}/prompt/01_clips.md Clip_{num:02d}"
        fm = _VID_FIRST_FRAME_RE.search(block)
        if fm and _missing(fm.group(1).strip()):
            add(BLOCK, "首帧", loc,
                f"视频 prompt 引用的首帧 PNG 不存在：{fm.group(1).strip()}——image2video 调用会失败、"
                "白扣一次最贵工位的钱，先补帧/改路径再出视频。", return_to_stage="image")
        elif fm and num in sb_first and not _missing(fm.group(1).strip()) \
                and not _same_path(fm.group(1).strip(), sb_first[num]):
            add(BLOCK, "首帧", loc,
                f"视频 prompt 首帧引用 `{fm.group(1).strip()}` ≠ storyboard.firstframe_png `{sb_first[num]}`——"
                "两侧各查存在都绿，但誊抄漂成另一张图=image2video 会动错的首帧（最贵工位上动错人/错构图）。"
                "改回与 storyboard 一致的那张，或回 n2d-script 同步 firstframe_png。", return_to_stage="video")
        em = _VID_END_FRAME_RE.search(block)
        if em and _missing(em.group(1).strip()):
            add(frame_warn, "尾帧", loc,
                f"视频 prompt 声明了尾帧但 PNG 不存在：{em.group(1).strip()}——镜内双锚/relay 会降级为单首帧"
                "（大表情近景有脸重画风险），先补尾帧或确认降级。", return_to_stage="image")
        elif em and num in sb_end and not _missing(em.group(1).strip()) \
                and not _same_path(em.group(1).strip(), sb_end[num]):
            add(frame_warn, "尾帧", loc,
                f"视频 prompt 尾帧引用 `{em.group(1).strip()}` ≠ storyboard.endframe_png `{sb_end[num]}`——"
                "誊抄漂成另一张尾帧=双帧插值的落点错，接缝/大表情近景插到错的止帧。确认是有意改写否则改回。",
                return_to_stage="video")
        elif em is None and need_end.get(num):
            add(frame_warn, "尾帧", loc,
                "storyboard 要求 end_anchor/relay boundary，但视频 prompt 此 Clip 漏写 `**尾帧**` 引用——"
                "尾锚意图在誊抄时丢失，runner 会按单首帧出，大表情近景或连续 take 会失去安全网。",
                return_to_stage="image")
        mids = _VID_MID_FRAME_RE.findall(block)
        for rel in mids:
            if _missing(rel.strip()):
                add(frame_warn, "中段锚帧", loc,
                    f"视频 prompt 声明了锚帧但 PNG 不存在：{rel.strip()}——拆段接力会降级"
                    "（opt-in 的中段漂移风险回归），先补 `_mid`/`_aK` 锚帧或确认降级。", return_to_stage="image")
        declared = need_mid.get(num, 0)
        if len(mids) < declared:
            add(frame_warn, "中段锚帧", loc,
                f"storyboard 声明了 {declared} 个锚帧（continuity.midframe/anchors）但视频 prompt 此 Clip 只引用了 {len(mids)} 个"
                "`**中段锚帧**`/`**锚帧K**`——拆段意图在誊抄时丢失，runner 会按少段出，付了出图成本却没拿到中段锚定。",
                return_to_stage="video")
def check_video_stage_raw_output_policy(root: str, ep: str) -> None:
    hits = stripped_audio_artifacts(root, ep)
    if hits:
        add(
            BLOCK,
            "原生音轨",
            hits[0],
            "出视频阶段必须保留 AI 平台原片；不得在 `出视频/第N集/视频/` 放 `.noaudio`/静音派生或把原片挪到 `_raw_with_audio/`。"
            "原生音轨统一交 n2d-compose 按 `视频原生音轨` 策略丢弃/混入/保留。",
        )
def check_native_audio_compose_policy(root: str, ep: str, audio_hits: List[str]) -> None:
    policy = native_audio_policy(root)
    mode = native_audio_policy_mode(policy)
    overview = os.path.join(root, "出视频", ep, "prompt", "00_总览.md")
    overview_text = open(overview, encoding="utf-8").read() if os.path.isfile(overview) else ""

    if is_native_av_production(root):
        # 原生音画：台词就在 clip 原生音轨里；compose.sh 默认自动「保留原片音轨」（除非显式丢弃），
        # 所以不能照搬「丢弃会剥离台词」的误报——按有效策略=保留校验。
        if not audio_hits:
            add(WARN, "原生音画", os.path.join(root, "出视频", ep, "视频"),
                "原生音画模式但未在 clip 检测到原生音频流；说话镜台词应由视频后端原生生成，确认出视频后端是否输出了同步音轨")
            return
        if mode == NATIVE_AUDIO_DISCARD:
            add(WARN, "原生音画", os.path.join(root, "_设置.md"),
                f"原生音画：当前 视频原生音轨={policy}，但 native_speech 台词在 clip 原片音轨里；"
                "compose 将按有效策略自动「保留原片音轨」以免丢失原生台词（确需强制丢弃须设 VIDEO_NATIVE_AUDIO_POLICY_EXPLICIT=1）")
        if overview_text:
            check_native_audio_opt_in_overview(root, ep, overview_text, overview)
            check_native_av_physical_contract(root, ep, overview_text, overview)
            check_native_av_physics_sidecar(root, ep, native_av_physics_required(root, ep, overview_text))
        else:
            add(WARN, "原生音画", overview, "缺出视频总览；建议声明 native_speech 路由（台词+口型由后端原生生成）")
        scope = voice_track_scope(root, ep)
        if scope == "voiceover_only":
            add(WARN, "原生音画", os.path.join(root, "合成", ep, "配音"),
                "原生音画 clip 含原生台词，同时检测到旁白/系统 n2d-voice 轨；允许作为后期旁白层，但合成前需确认不与原生台词重叠")
        elif scope == "dialogue_or_unknown":
            add(BLOCK, "原生音画", os.path.join(root, "合成", ep, "配音"),
                "原生音画 clip 已含原生台词，又存在无法确认仅为旁白/系统的 n2d-voice 配音轨；正式合成会双人声，请移除角色配音或把配音清单限定为旁白/系统层")
        return

    if not audio_hits:
        if mode != NATIVE_AUDIO_DISCARD:
            add(WARN, "原生音画", os.path.join(root, "_设置.md"), f"`视频原生音轨={policy}`，但当前 clip 未检测到原生音频流；该设置本集不会生效")
        return

    if mode == NATIVE_AUDIO_DISCARD:
        add(WARN, "原生音轨", audio_hits[0], "clip 含原生音轨；当前策略=丢弃，compose 会剥离以避免原生台词与配音双人声")
        return

    if not overview_text:
        add(BLOCK, "原生音画", overview, f"`视频原生音轨={policy}` 且 clip 含音频流，但缺出视频总览；无法核验 opt-in 清单")
    else:
        check_native_audio_opt_in_overview(root, ep, overview_text, overview)
        check_native_av_physical_contract(root, ep, overview_text, overview)
        check_native_av_physics_sidecar(root, ep, native_av_physics_required(root, ep, overview_text))

    if mode == NATIVE_AUDIO_KEEP and voice_track_exists(root, ep):
        add(BLOCK, "原生音画", os.path.join(root, "合成", ep, "配音"), "`视频原生音轨=保留原片音轨` 且存在 n2d-voice 配音轨；正式合成会双人声，改为「低音量混入环境声」或「丢弃」")
def check_compose_foley_native_audio_policy(root: str, ep: str) -> None:
    """Advisory guard: native-AV clip audio should not get a second compose foley layer."""
    effective_audio_preserved = (
        is_native_av_production(root)
        or native_audio_policy_mode(native_audio_policy(root)) != NATIVE_AUDIO_DISCARD
    )
    if not effective_audio_preserved:
        return
    profile = video_backend_adapter.route_native_audio_profile(
        root,
        ep,
        channel=get_setting(root, "生视频渠道", "").strip(),
    )
    if not profile.get("native_audio"):
        return
    work = os.path.join(root, "合成", ep, "_work")
    policy_path = os.path.join(work, "foley_render_policy.json")
    foley_wav = os.path.join(work, "foley_mix.wav")
    data = load_json(policy_path)
    if isinstance(data, dict):
        forced = bool(data.get("force_compose_foley")) or str(data.get("strategy") or "").strip() == "强制叠加"
        if data.get("mode") == "full" and not forced:
            sample = "、".join(str(h.get("clip_id") or h.get("backend") or "") for h in (profile.get("hits") or [])[:4])
            add(
                WARN,
                "后期拟音",
                policy_path,
                "本集路由/制作模式会保留原生音画后端音轨，但 compose 侧 foley_render_policy=full 且未显式 force；"
                f"疑似双层拟音/重复打击声（clips: {sample or 'unknown'}）。"
                "默认应由 foley_agent 抑制 compose foley；确需补拟音请设 `_设置.md` 后期拟音策略=强制叠加 或 FORCE_COMPOSE_FOLEY=1。",
                return_to_stage="compose",
                confidence="heuristic",
            )
            return
    if os.path.isfile(foley_wav):
        add(
            WARN,
            "后期拟音",
            foley_wav,
            "本集路由/制作模式会保留原生音画后端音轨，但合成工作区缺 foley_render_policy.json，无法确认 compose foley 是否已抑制。"
            "请用新版 n2d-compose 重跑；确需强制叠加时显式 FORCE_COMPOSE_FOLEY=1 或 后期拟音策略=强制叠加。",
            return_to_stage="compose",
            confidence="heuristic",
        )


def _final_timeline_probe_passes(root: str, ep: str) -> bool:
    data = load_json(os.path.join(root, "生产数据", f"final_timeline_probe_{ep}.json"))
    if not isinstance(data, dict) or data.get("kind") != "n2d_final_timeline_probe":
        return False
    if data.get("findings"):
        return False
    actual = data.get("actual_duration_sec")
    expected = data.get("expected_duration_sec")
    tolerance = data.get("duration_tolerance_sec")
    try:
        return abs(float(actual) - float(expected)) <= float(tolerance)
    except Exception:
        return False


def check_video_delivery_consistency(root: str, ep: str) -> None:
    """批内帧率/分辨率一致性（video_qc.delivery_consistency 消费端·2026-07 落地）。

    video_qc 只产报告不阻断（main 恒 0）；混帧率/混分辨率 clip 进 compose 会被规格化静默掩盖
    （重复帧/缩放糊边）。这里读最新批次 QC 报告，把 delivery mismatch 升为 gate WARN——
    warn 而非 block：混批可能是有意的（如后端能力差异），但必须在验收面可见。缺报告不拦。"""
    import glob as _glob
    reports = sorted(_glob.glob(os.path.join(root, "生产数据", "video_qc", ep, "*", f"video_qc_{ep}_*.json")))
    seen_clips: set = set()
    for path in reversed(reports):  # 新批次优先，避免旧报告覆盖新结论
        try:
            payload = json.loads(open(path, encoding="utf-8").read())
        except Exception:
            continue
        dc = payload.get("delivery_consistency") or {}
        for f in dc.get("findings") or []:
            key = (str(f.get("clip") or ""), str(f.get("kind") or ""))
            if key in seen_clips:
                continue
            seen_clips.add(key)
            add(WARN, "视频", path,
                f"{f.get('clip')} 交付一致性偏离：{f.get('kind')}={f.get('value')}（批内众数 {f.get('expected')}）"
                "——混帧率/混分辨率进 compose 会被静默规格化掩盖，确认该 clip 是否该重出。")


def check_video_assets(root: str, ep: str) -> None:
    check_video_stage_raw_output_policy(root, ep)
    check_video_delivery_consistency(root, ep)
    clips = clip_files(root, ep)
    if not clips:
        add(BLOCK, "视频", os.path.join(root, "出视频", ep, "视频"), "缺 clip MP4")
        return
    sb = load_storyboard(root, ep)
    final_timeline_ok = _final_timeline_probe_passes(root, ep)
    if sb and len(clips) != len(sb.get("clips", [])):
        sev = INFO if final_timeline_ok else WARN
        tail = "；final_timeline_probe 已验证成片时间线，raw split 数量差异仅作原料说明" if final_timeline_ok else ""
        add(sev, "视频", os.path.join(root, "出视频", ep, "视频"),
            f"clip 数 {len(clips)} 与 storyboard clips {len(sb.get('clips', []))} 不一致{tail}")
    audio_probe = [(c, has_audio(c)) for c in clips]
    audio_hits = [c for c, a in audio_probe if a]
    unprobeable = [c for c, a in audio_probe if a is None]
    # 双人声硬闸门（原生台词 + n2d-voice 配音）依赖 ffprobe 探测 clip 原生音轨。ffprobe 缺失时
    # has_audio 返回 None → audio_hits 收缩为空 → 双人声 BLOCK 静默到不了。review 是交付边界：
    # 探不了原生音轨又存在配音轨 = 双人声硬闸门其实没校验过，默认 BLOCK（与降级精度一致性审计同一套
    # 「缺核心检测工具→交付边界拦截」策略，逃生口同为 N2D_ALLOW_DEGRADED_QC=1·留痕自负其责）。
    if unprobeable and voice_track_exists(root, ep):
        allow_degraded = degraded_qc_active(root)
        if allow_degraded:
            note_degraded_qc_waiver("原生音画", ep, os.path.join(root, "出视频", ep, "视频"),
                                    "ffprobe 不可用·原生音轨硬闸降级放行")
        sev = WARN if allow_degraded else BLOCK
        tail = (f"（已通过{degraded_qc_waiver_label(root)}放行）" if allow_degraded
                else "装 ffprobe 后重跑，或显式 N2D_ALLOW_DEGRADED_QC=1 / 项目 internal_only demo 放行并自负其责。")
        add(sev, "原生音画", os.path.join(root, "出视频", ep, "视频"),
            f"ffprobe 不可用，{len(unprobeable)} 个 clip 无法探测原生音轨——"
            f"「原生台词 + n2d-voice 配音 = 双人声」硬闸门无法校验，交付边界不放行。{tail}")
    check_native_audio_compose_policy(root, ep, audio_hits)
    check_compose_foley_native_audio_policy(root, ep)
    shots = load_json(os.path.join(root, "脚本", ep, "镜头时长.json"))
    if isinstance(shots, dict):
        target = sum(float(v) for v in shots.values())
        actuals = [duration(c) for c in clips]
        if all(d is not None for d in actuals):
            total = sum(d for d in actuals if d is not None)
            if abs(total - target) > 1.0:
                sev = INFO if final_timeline_ok else WARN
                tail = "；final_timeline_probe 已验证最终成片时长，raw split 总长差异仅作原料说明" if final_timeline_ok else ""
                add(sev, "时长", ep, f"clip 总长 {total:.2f}s 与镜头时长累计 {target:.2f}s 差 {abs(total-target):.2f}s{tail}")
def check_compose_inputs(root: str, ep: str) -> None:
    check_video_assets(root, ep)
    check_placeholder_policy(root, ep, "compose")
    zh = os.path.join(root, "脚本", ep, "字幕_中文.srt")
    if not os.path.isfile(zh):
        # 原生音画：说话镜台词由视频后端原生生成、不跑逐句配音，finalize 也不产 SRT
        # （字幕走成片后 whisperx 词级对齐，见 n2d SKILL）——compose 草稿只提醒，review/release 由
        # native_av_subtitle_alignment sidecar 硬闸兜住。
        if is_native_av_production(root):
            add(WARN, "字幕", zh,
                "原生音画：暂无中文字幕；compose 可先出 draft，但 review/付费投放前必须用 whisperx 或等效词级对齐"
                "生成字幕，并写 `生产数据/native_av_subtitle_alignment_第N集.json`")
        else:
            add(BLOCK, "字幕", zh, "缺中文字幕")
def check_native_av_subtitle_alignment(root: str, ep: str, stage: str) -> None:
    if not is_native_av_production(root):
        return
    required = native_av_subtitle_alignment_required(root, stage)
    path = native_av_subtitle_alignment_path(root, ep)
    data = load_json(path)
    if not isinstance(data, dict):
        sev = BLOCK if required else WARN
        add(
            sev,
            "原生音画字幕对齐",
            path,
            "缺 native AV 字幕对齐 sidecar：原生音画说话镜不走前期配音 SRT，成片后必须用 whisperx 或等效词级对齐"
            "生成中文字幕并写 `kind=n2d_native_av_subtitle_alignment`、status、word_level、subtitle_path。"
            + (" review/付费投放前不放行。" if required else " compose 可先出 draft，但 review 会阻断。"),
            return_to_stage="compose" if required else "review",
        )
        return
    errors = _native_av_subtitle_errors(root, ep, data)
    if errors:
        sev = BLOCK if required else WARN
        add(
            sev,
            "原生音画字幕对齐",
            path,
            "native AV 字幕对齐 sidecar 不完整：" + "；".join(errors),
            return_to_stage="compose" if required else "review",
        )
def check_subtitle_alignment(root: str, ep: str) -> None:
    """字幕对齐(L1)：双语短语边界/阅读速度/译文完整性（补 mechanical_check 条数对账盲区）。"""
    res = sa.analyze(root, ep)
    _add_continuity_rows(
        "字幕对齐(L1)",
        [r for r in res.get("rows", []) if isinstance(r, dict)],
        ep,
        default_stage="script_stage2",
        default_scope="回 n2d-script 阶段2重跑 finalize_storyboard / 修翻译层，对齐中↔英断句与阅读速度。",
        default_artifacts=(f"脚本/{ep}/字幕_中文.srt", f"脚本/{ep}/字幕_英文.srt"),
    )
def check_translation_glossary_release_gate(root: str, ep: str, stage: str) -> None:
    if stage not in {"compose", "review"}:
        return
    required = _project_has_english_subtitles(root, ep) or _project_has_overseas_release_target(root)
    if not required:
        return
    path = translation_glossary_path(root)
    data = load_json(path)
    if not isinstance(data, dict):
        add(
            BLOCK,
            "译名发布闸门",
            path,
            "海外/英文字幕发布前缺 translation_glossary.json；必须锁人名、称谓、境界、招式、口头禅、系统提示语的 canonical 译名，"
            "并让字幕生成与 OCR/字幕检查同用这份 glossary。",
            return_to_stage="script_stage2",
        )
        return
    terms = _translation_glossary_terms(data)
    if not terms or not all(_translation_term_has_pair(term) for term in terms):
        add(
            BLOCK,
            "译名发布闸门",
            path,
            "translation_glossary.json 必须包含非空 terms[]，且每条至少有 cn/source 与 en/canonical；不能只写空壳或说明文字。",
            return_to_stage="script_stage2",
        )
        return
    missing_categories = [cat for cat in TRANSLATION_GLOSSARY_CATEGORIES if not _translation_category_covered(data, terms, cat)]
    if missing_categories:
        add(
            BLOCK,
            "译名发布闸门",
            path,
            "translation_glossary.json 缺覆盖类目：" + "、".join(missing_categories) +
            "；无该类内容也要在 coverage 标 not_applicable，避免海外字幕/称谓/招式名临场多译。",
            return_to_stage="script_stage2",
        )
def check_pilot_arc_contract_gate(root: str, ep: str, stage: str) -> None:
    """第1-2集也要有 onboarding 小弧，不等到 ≥3 集才看系列留存。"""
    ep_n = _series_ep_int(ep)
    if ep_n is None or ep_n > 2:
        return
    loc = os.path.join(root, PILOT_ARC_CONTRACT_REL)
    production = consistency_release_profile(root, stage, ep) == "production"
    sev = BLOCK if production else WARN
    data = load_json(loc)
    if not isinstance(data, dict) or not data:
        add(
            sev,
            SERIES_RETENTION_DIM,
            loc,
            "第1-2集缺 pilot_arc_contract：必须先锁系列承诺、主角欲望、可重复爽感、长问题、首个兑现/阻碍/反转，再进入交付边界。",
            risk_score=0.82,
            code="pilot_arc_contract_missing",
        )
        return
    missing = [field for field in PILOT_ARC_REQUIRED_FIELDS if not str(data.get(field) or "").strip()]
    if missing:
        add(
            sev,
            SERIES_RETENTION_DIM,
            loc,
            "pilot_arc_contract 字段未填全：%s；前两集不能只按单集爽点推进，必须能证明追更小弧成立。" % "、".join(missing),
            risk_score=0.82,
            code="pilot_arc_contract_incomplete",
            missing=missing,
        )
def check_series_retention_gate(root: str, ep: str, stage: str) -> None:
    """交付边界(compose/review)的**系列级**留存闸。

    背景：`beat_audit --series`（跨集套路同质化 + 跨集冷开场链 + 看点高潮位）和 series_balance
    的全剧钩子/反转曲线此前**只进 score KPI、从不 gate**——run.py 只逐集跑 beat_audit。结果
    "全剧钩子曲线塌、套路复印、集内虎头蛇尾"在交付时不可见。系列信号要全集齐了才算，不适合逐集
    硬闸，但适合在 compose/review 交付边界做一道闸（同 production advisory 升级逻辑）。

    per-episode 语义（gate 是按单集调用的）：只对**牵涉当前集**的系列 finding 给 WARN，
    production + 交付边界(compose/review) 升 BLOCK（可经 consistency_advisory_signoff 签收）；
    不牵涉当前集的 → INFO（可见但不拦本集，避免用 ep2↔ep3 的雷同去拦 ep5 的 compose）。
    需 ≥3 集才有"系列"可言，否则静默。beat_audit 跑不起来只 WARN，不硬拦产线（系列检是软基建）。
    """
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                          "n2d-script", "scripts", "beat_audit.py")
    sdir = os.path.join(root, "脚本")
    if not os.path.exists(script):
        return
    try:
        eps = [d for d in os.listdir(sdir)
               if re.match(r"第\d+集$", d) and os.path.isfile(os.path.join(sdir, d, "voiceover.txt"))]
    except Exception:
        eps = []
    if len(eps) < 3:
        check_pilot_arc_contract_gate(root, ep, stage)
        return
    try:
        proc = subprocess.run([sys.executable, script, root, "--series", "--json"],
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=False, timeout=300)
        res = json.loads(proc.stdout or "{}")
    except Exception as exc:
        add(WARN, SERIES_RETENTION_DIM, sdir,
            f"beat_audit --series 跑不起来（{type(exc).__name__}），系列留存未审；"
            "可手动跑 beat_audit.py <作品根> --series", risk_score=0.4)
        return
    if not isinstance(res, dict):
        return

    profile = consistency_release_profile(root, stage, ep)
    deliverable = stage in {"compose", "review"}
    cur = _series_ep_int(ep)
    cur_label = f"第{cur}集" if cur is not None else (ep or "")

    def emit(loc: str, msg: str, implicated: bool, return_to: str, scope: str) -> None:
        if not implicated:
            add(INFO, SERIES_RETENTION_DIM, loc, msg, risk_score=0.3)
            return
        row = {"dimension": SERIES_RETENTION_DIM, "message": msg, "affected_artifacts": [loc]}
        if profile == "production" and deliverable and not _advisory_row_signed_off(root, ep, row):
            add(BLOCK, SERIES_RETENTION_DIM, loc,
                msg + "（production 交付边界升 BLOCK；确属有意则写 consistency_advisory_signoff_第N集.json 签收）",
                risk_score=0.7, return_to_stage=return_to, rerun_scope=scope, affected_artifacts=[loc])
        else:
            add(WARN, SERIES_RETENTION_DIM, loc, msg, risk_score=0.55,
                return_to_stage=return_to, rerun_scope=scope)

    # ① 跨集套路同质化（Gap4·桥段指纹 Jaccard≥0.8）
    for pair in res.get("duplicates") or []:
        if not (isinstance(pair, (list, tuple)) and len(pair) >= 3):
            continue
        ea, eb, j = str(pair[0]), str(pair[1]), pair[2]
        emit(sdir, f"{ea}↔{eb} 桥段指纹重合 {j}（套路雷同→观众疲劳）：换爽点类型/信息角度/情绪曲线",
             cur_label in (ea, eb), "script_stage1",
             "回 n2d-script 阶段1 给雷同集换爽点/反转类型，反同质化")
    # ② 跨集冷开场链（P2·上集硬断→下集 0-3s 冷开场接住同一根线）
    # P1（2026-06-26 接线）：image_preflight 也是付费前闸——首屏 3s 钩失效=30%+ 留存塌，必须在烧钱出图前拦。
    # 此前这条 image_preflight 分支是 dead code（check_series_retention_gate 只在 compose/review dispatch 被调），
    # 现已在 image dispatch 的 image_preflight 子条件接上。profile-aware（与全仓一致）：production 升 BLOCK（可签收），demo WARN。
    scope2 = "回 n2d-script 阶段1/2 调切点：上集集尾硬断、下集 0-3s 冷开场接住同一根线"
    for f in res.get("cold_open_chain_findings") or []:
        msg = str(f.get("msg") or "")
        if not (bool(cur_label) and cur_label in msg):
            add(INFO, SERIES_RETENTION_DIM, sdir, f"[冷开场链] {msg}", risk_score=0.3)
            continue
        cold_msg = f"[冷开场链] {msg}"
        if stage == "image_preflight":
            row = {"dimension": SERIES_RETENTION_DIM, "message": cold_msg, "affected_artifacts": [sdir]}
            if profile == "production" and not _advisory_row_signed_off(root, ep, row):
                add(BLOCK, SERIES_RETENTION_DIM, sdir,
                    cold_msg + "（预算前：0-3s 冷开场未接住上集硬断 → 3s 留存塌，别烧钱渲染；"
                    "确属有意写 consistency_advisory_signoff_第N集.json 签收）",
                    risk_score=0.8, return_to_stage="script_stage1", rerun_scope=scope2)
            else:
                add(WARN, SERIES_RETENTION_DIM, sdir, cold_msg + "（预算前留存地板·首屏冷开场）",
                    risk_score=0.55, return_to_stage="script_stage1", rerun_scope=scope2)
        else:
            emit(sdir, cold_msg, True, "script_stage1", scope2)
    # ③ 看点高潮位（北极星看点④·虎头蛇尾/平庸无看点集·需真实镜头时长）
    for f in res.get("highlight_climax_findings") or []:
        msg = str(f.get("msg") or "")
        emit(sdir, f"[看点位] {msg}", bool(cur_label) and cur_label in msg, "script_stage2",
             "回 n2d-script 阶段2 后移看点到 60-85% 高潮位 / 补核心看点")
    # ④ 冷开场质量深度（G2·4 层钩子信号：冲突/悬念/反转/信息揭示）
    for f in res.get("cold_open_quality_findings") or []:
        msg = str(f.get("msg") or "")
        sev = str(f.get("severity") or "")
        emit(sdir, f"[冷开场质量] {msg}", bool(cur_label) and cur_label in msg, "script_stage1",
             "回 n2d-script 阶段1 补冷开场冲突/悬念/反转层（至少 2 层钩子信号）")
def check_episode_narrative_floor(root: str, ep: str, stage: str) -> None:
    """逐集**预算前**留存地板（首屏 3s 视觉钩 / 留存承诺账本）——批量 gate 路径的叙事地板。

    背景（2026-06-26·P1）：`run.py next` 在付费前用 `beat_audit --strict` 逐集硬挡「无首屏视觉钩 /
    无留存承诺账本」的平庸集；但**批量生产**时 runner 经 `dashboard.py gate ... --stage image_preflight`
    直接跑 gate（不走 run.py），这道地板就漏了——平庸集照样烧钱出图（红果 2026-05 下架约 2.1 万剧、其中
    ~95% 是漫剧、广电备案过审<30%，平庸=白烧+被下架）。这里把同一道 beat_audit 逐集 `must` 地板接进
    image_preflight：production 升 BLOCK（可经 consistency_advisory_signoff 签收），demo 只 WARN。
    单一真值源=`n2d-script/beat_audit.py`（gate 只消费其 must findings，不重写判据）。仅 image_preflight 跑。"""
    if stage != "image_preflight":
        return
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                          "n2d-script", "scripts", "beat_audit.py")
    sdir = os.path.join(root, "脚本", ep)
    if not os.path.exists(script) or not os.path.isdir(sdir):
        return
    try:
        proc = subprocess.run([sys.executable, script, root, ep, "--json"],
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=False, timeout=120)
        res = json.loads(proc.stdout or "{}")
    except Exception as exc:
        add(WARN, SERIES_RETENTION_DIM, sdir,
            f"beat_audit 逐集留存地板跑不起来（{type(exc).__name__}），首屏钩/留存承诺未审；"
            "可手动跑 beat_audit.py <作品根> 第N集", risk_score=0.4)
        return
    if not isinstance(res, dict):
        return
    production = consistency_release_profile(root, stage, ep) == "production"
    scope = "回 n2d-script 阶段1/2 补首屏视觉钩(visual_hook/内容承诺/静音可读证明/目标指标)与留存承诺账本，再付费出图"
    for f in res.get("findings") or []:
        if not isinstance(f, dict) or str(f.get("severity")) != "must":
            continue
        code, msg = str(f.get("code") or ""), str(f.get("msg") or "")
        row = {"dimension": SERIES_RETENTION_DIM, "message": msg, "affected_artifacts": [sdir], "code": code}
        if production and not _advisory_row_signed_off(root, ep, row):
            add(BLOCK, SERIES_RETENTION_DIM, sdir,
                f"[预算前留存地板] {msg}（production 升 BLOCK：别烧钱渲染无钩/无承诺的平庸集；"
                "确属有意写 consistency_advisory_signoff_第N集.json 签收）",
                risk_score=0.8, return_to_stage="script_stage2", code=code, rerun_scope=scope)
        else:
            add(WARN, SERIES_RETENTION_DIM, sdir, f"[预算前留存地板] {msg}", risk_score=0.55,
                return_to_stage="script_stage2", code=code, rerun_scope=scope)
def check_progress_receipt_reconcile(root: str, ep: str, current_stage: str = "") -> None:
    """H3：交付/验收前**从凭据重新推导真相**——该集每个受闸列(出图/视频/成片)的 ✅ 必须有
    fresh+green 闸门凭据，否则 BLOCK。这把进度 ✅ 从「可写真值」降级成「待背书声明」，
    抓住绕过 `progress.do_set` 的手写/带外 ✅（凭据耦合只活在 do_set，sed/编辑器/别的写路径
    都是构造性旁路）。凭据模块不可加载=不能证明任何 ✅ 真实=fail-closed BLOCK。

    确定性证据闸（charter-locked·不随 profile 降级）：与 do_set 写时校验互为第二/三防线。"""
    try:
        import gate_receipt as _gr
    except Exception as e:  # 凭据模块缺失，无法证明 ✅ 背书 → fail-closed，绝不放行交付
        add(BLOCK, "进度凭据对账", str(ep),
            f"无法加载 gate_receipt（{e}）：无法证明进度 ✅ 有凭据背书，fail-closed 拒绝交付。")
        return
    for v in _gr.reconcile_progress(root, ep):
        if current_stage and str(v.get("gate_stage") or "") == current_stage:
            continue
        add(BLOCK, "进度凭据对账", f"{ep}/{v['column']}",
            f"进度「{v['column']}」标 ✅ 却无新鲜通过的闸门凭据（{v['code']}）：{v['message']}（"
            f"凡绕过 progress set 直接写 ✅ 都会在此被抓——重跑该阶段闸门盖新鲜凭据后再交付）")


def check_preventive_contracts(root: str, ep: str, stage: str) -> None:
    """Preventive contracts must be signed before downstream gate families run."""
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "preventive_contracts.py"))
    if not os.path.exists(script):
        add(BLOCK, "预防式合同", stage, "缺 skills/n2d/scripts/preventive_contracts.py；无法核验预防式合同，fail-closed。")
        return
    try:
        r = subprocess.run(
            [sys.executable, script, root, ep, "--stage", stage, "--write", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception as exc:
        add(BLOCK, "预防式合同", stage, f"preventive_contracts.py 运行失败：{type(exc).__name__}: {str(exc)[:160]}")
        return
    payload = _loads_json_from_noisy_stdout(r.stdout) or {}
    if not isinstance(payload, Mapping):
        detail = (r.stderr or r.stdout or "").strip()[:180]
        add(BLOCK, "预防式合同", stage, f"preventive_contracts.py 未输出可解析 JSON：{detail}")
        return
    for row in payload.get("findings") or []:
        if not isinstance(row, Mapping):
            continue
        sev_raw = str(row.get("severity") or "info").strip().lower()
        sev = BLOCK if sev_raw == "block" else WARN if sev_raw == "warn" else INFO
        gate_name = str(row.get("gate") or "preventive_contract")
        loc = str(row.get("loc") or payload.get("contract_path") or stage)
        msg = str(row.get("message") or "")
        add(sev, "预防式合同", loc, f"{gate_name}: {msg}", return_to_stage=str(row.get("return_to_stage") or ""))
    if r.returncode != 0 and not any(
        isinstance(row, Mapping) and str(row.get("severity") or "").lower() == "block"
        for row in payload.get("findings") or []
    ):
        add(BLOCK, "预防式合同", stage, f"preventive_contracts.py 退出码 {r.returncode}，但未返回 block finding。")


def _skills_dir() -> str:
    return os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))


def _repair_preflight_command(root: str, ep: str, stage: str) -> str:
    return (
        f'python3 skills/n2d/scripts/repair_preflight.py "{root}" {ep} '
        f"--stage {stage} --write-missing"
    )


def _run_json_tool(cmd: List[str]) -> Tuple[int, Dict[str, Any], str]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    payload = _loads_json_from_noisy_stdout(r.stdout)
    detail = (r.stderr or r.stdout or "").strip()
    if not isinstance(payload, dict):
        payload = {}
    return r.returncode, payload, detail


def check_production_handoff_pack(root: str, ep: str, stage: str) -> None:
    """P-3 production handoff must be complete before image/video work.

    `run.py` already runs production_breakdown.py as prework, but batch/r2a/dashboard
    callers can enter gate directly.  This check makes the P-3 package a true
    gate invariant instead of a dispatcher-only convention.
    """
    script = os.path.join(_skills_dir(), "n2d-script", "scripts", "production_breakdown.py")
    if not os.path.exists(script):
        add(
            BLOCK,
            "P-3制片交接包",
            script,
            "缺 production_breakdown.py，无法核验 continuity_chain/continuity_bible/拍摄计划/通告单；"
            "fail-closed，先恢复脚本再继续。",
            return_to_stage="script_stage2",
        )
        return
    code, report, detail = _run_json_tool([sys.executable, script, root, ep, "check", "--json"])
    if code == 0 and str(report.get("status") or "").strip() == "pass":
        return
    files = [row for row in report.get("files") or [] if isinstance(row, Mapping) and row.get("status") != "pass"]
    examples = []
    for row in files[:6]:
        issues = "；".join(str(x) for x in (row.get("issues") or [])) or str(row.get("status") or "")
        examples.append(f"{row.get('rel')}: {issues}")
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    loc = report.get("check_path") or os.path.join(root, "生产数据", f"production_breakdown_check_{ep}.json")
    add(
        BLOCK,
        "P-3制片交接包",
        str(loc),
        "P-3 制片交接包未通过："
        f"{summary.get('pass', 0)}/{summary.get('required', '?')} confirmed。"
        "进入出图/视频前必须补齐并确认 continuity_chain.json、continuity_bible.json、"
        "ai_shooting_schedule.json、ai_call_sheet.md 等交接文件；"
        + ("问题示例：" + "；".join(examples) + "。" if examples else f"详情：{detail[:240]}。")
        + f"统一修复入口：`{_repair_preflight_command(root, ep, stage)}`。",
        return_to_stage="script_stage2",
        affected_artifacts=[str(row.get("rel") or "") for row in files[:20]],
        recovery_command=_repair_preflight_command(root, ep, stage),
        evidence_family="production_handoff",
    )


def check_story_economy_audit(root: str, ep: str, stage: str) -> None:
    """Story economy must pass before expensive image/video generation."""
    script = os.path.join(_skills_dir(), "n2d-script", "scripts", "story_economy_audit.py")
    if not os.path.exists(script):
        add(
            BLOCK,
            "剧情经济性",
            script,
            "缺 story_economy_audit.py，无法证明剧情已压缩到该详拍的段落；fail-closed，先恢复脚本。",
            return_to_stage="script_stage2",
        )
        return
    code, report, detail = _run_json_tool([sys.executable, script, root, ep, "--strict", "--json"])
    findings = [f for f in report.get("findings") or [] if isinstance(f, Mapping)]
    blocks = [f for f in findings if str(f.get("severity") or "").lower() == "block"]
    warnings = [f for f in findings if str(f.get("severity") or "").lower() == "warn"]
    if code == 0 and report.get("ok", False):
        if warnings and stage in {"image_preflight", "video_preflight"}:
            add(
                WARN,
                "剧情经济性",
                os.path.join(root, "脚本", ep, "storyboard.json"),
                f"story_economy_audit 仍有 {len(warnings)} 条压缩建议；本次不硬拦，但建议在付费生成前处理，"
                "避免解释/行进/普通反应占用视频预算。",
                return_to_stage="script_stage2",
                evidence_family="story_economy",
            )
        return
    examples = []
    for row in blocks[:5]:
        clip = str(row.get("clip") or "").strip()
        examples.append(f"{clip} {row.get('code')}: {row.get('message')}")
    add(
        BLOCK,
        "剧情经济性",
        os.path.join(root, "脚本", ep, "storyboard.json"),
        "story_economy_audit 未通过；昂贵出图/出视频前必须先压缩非战斗、非强情绪、解释/行进/普通反应长段。"
        + ("问题示例：" + "；".join(examples) + "。" if examples else f"详情：{detail[:240]}。")
        + f"统一修复入口：`{_repair_preflight_command(root, ep, stage)}`。",
        return_to_stage="script_stage2",
        affected_artifacts=[os.path.join(root, "脚本", ep, "storyboard.json")],
        recovery_command=_repair_preflight_command(root, ep, stage),
        evidence_family="story_economy",
    )


def check_production_locks_preflight(root: str, ep: str, stage: str) -> None:
    """Stage lock ledger must exist and be fresh at paid/irreversible boundaries."""
    script = os.path.join(_skills_dir(), "scripts", "production_locks.py")
    if not os.path.exists(script):
        add(
            BLOCK,
            "生产锁版账",
            script,
            "缺 production_locks.py，无法核验锁版账；fail-closed，先恢复脚本。",
            return_to_stage="script_stage2",
        )
        return
    code, report, detail = _run_json_tool([sys.executable, script, root, ep, "check", "--stage", stage, "--json"])
    if code == 0 and str(report.get("status") or "").strip() == "pass":
        return
    findings_rows = [f for f in report.get("findings") or [] if isinstance(f, Mapping)]
    examples = [str(f.get("message") or f.get("code") or "") for f in findings_rows[:5]]
    loc = report.get("check_path") or os.path.join(root, "生产数据", f"production_locks_check_{stage}_{ep}.json")
    add(
        BLOCK,
        "生产锁版账",
        str(loc),
        f"{stage} 前置锁版账未通过："
        + ("；".join(examples) if examples else detail[:240] or "缺失或未确认")
        + f"。先用统一修复入口补缺失 lock 草稿、确认锁版或记录解锁/最小返工范围："
        f"`{_repair_preflight_command(root, ep, stage)}`。",
        return_to_stage="script_stage2",
        affected_artifacts=[str(f.get("artifacts") or f.get("lock_id") or "") for f in findings_rows[:20]],
        recovery_command=_repair_preflight_command(root, ep, stage),
        evidence_family="production_locks",
    )


def _episode_storyboard(root: str, ep: str) -> Mapping[str, Any]:
    data = load_json(os.path.join(root, "脚本", ep, "storyboard.json"))
    return data if isinstance(data, Mapping) else {}


def _storyboard_clips(data: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    clips = data.get("clips") if isinstance(data.get("clips"), list) else data.get("shots")
    return [c for c in clips or [] if isinstance(c, Mapping)]


def _field_value(data: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and _filled(data.get(key)):
            return data.get(key)
    handoff = data.get("series_handoff") if isinstance(data.get("series_handoff"), Mapping) else {}
    for key in keys:
        if key in handoff and _filled(handoff.get(key)):
            return handoff.get(key)
    return None


PROMPT_CONSUMED_CONTRACTS_KIND = "n2d_prompt_consumed_contracts"
PROMPT_CONSUMED_REQUIRED = [
    "storyboard",
    "continuity_chain",
    "script_quality_contract",
    "director_camera_plan",
    "reference_plan",
]
PROMPT_CONSUMED_EXPECTED = {
    "storyboard": lambda ep: os.path.join("脚本", ep, "storyboard.json"),
    "continuity_chain": lambda ep: os.path.join("脚本", ep, "continuity_chain.json"),
    "script_quality_contract": lambda ep: os.path.join("生产数据", f"script_quality_contract_{ep}.json"),
    "director_camera_plan": lambda ep: os.path.join("生产数据", f"director_camera_plan_{ep}.json"),
    "reference_plan": lambda ep: os.path.join("生产数据", f"reference_plan_{ep}.json"),
}
PROMPT_CONSUMED_PROMPTS = {
    "image_prompt": [
        lambda ep: os.path.join("出图", ep, "prompt", "00_总览.md"),
        lambda ep: os.path.join("出图", ep, "prompt", "01_分镜出图.md"),
    ],
    "video_prompt": [
        lambda ep: os.path.join("出视频", ep, "prompt", "00_总览.md"),
        lambda ep: os.path.join("出视频", ep, "prompt", "01_clips.md"),
    ],
}


def _norm_receipt_rel(value: Any) -> str:
    return os.path.normpath(str(value or "").strip()).replace("\\", "/")


def _receipt_scope_for_stage(stage: str) -> Optional[str]:
    if stage in {"image_preflight", "image"}:
        return "image_prompt"
    if stage in {"video_preflight", "video"}:
        return "video_prompt"
    return None


def check_prompt_consumed_contracts(root: str, ep: str, stage: str) -> None:
    """Paid stages must consume the current upstream contracts, not stale prompt files."""
    scope = _receipt_scope_for_stage(stage)
    if not scope:
        return
    path = os.path.join(root, "生产数据", f"consumed_contracts_{scope}_{ep}.json")
    data = load_json(path)
    if not isinstance(data, Mapping):
        add(
            BLOCK,
            "Prompt消费收据",
            path,
            f"进入 {stage} 前缺 {scope} prompt 消费收据；请重跑对应 prompt pack，让下游写入 storyboard、continuity_chain、script_quality_contract、director_camera_plan、reference_plan 的 sha256。",
            return_to_stage="image_prompt" if scope == "image_prompt" else "video_prompt",
            evidence_family="contract",
        )
        return

    issues: List[str] = []
    if data.get("kind") != PROMPT_CONSUMED_CONTRACTS_KIND:
        issues.append("kind 不是 n2d_prompt_consumed_contracts")
    if data.get("scope") != scope:
        issues.append(f"scope={data.get('scope')!r}，应为 {scope!r}")
    if data.get("accepted") is not True:
        issues.append("accepted 不是 true")
    fingerprint_problems = prompt_consumption_contract.fingerprint_issues(
        root, ep, scope, data.get("input_fingerprint")
    )
    if fingerprint_problems:
        issues.append("统一 input_fingerprint 无效：" + ",".join(fingerprint_problems))

    contracts = data.get("contracts") if isinstance(data.get("contracts"), list) else []
    by_name = {str(row.get("name") or ""): row for row in contracts if isinstance(row, Mapping)}
    for name in PROMPT_CONSUMED_REQUIRED:
        row = by_name.get(name)
        rel = _norm_receipt_rel(row.get("path") if row else PROMPT_CONSUMED_EXPECTED[name](ep))
        expected_rel = _norm_receipt_rel(PROMPT_CONSUMED_EXPECTED[name](ep))
        if row is None:
            issues.append(f"缺 contract 记录：{name}")
            continue
        if rel != expected_rel:
            issues.append(f"{name} path={rel}，应为 {expected_rel}")
        current = os.path.join(root, rel)
        recorded_sha = str(row.get("sha256") or "").strip()
        if not row.get("exists") or not recorded_sha:
            issues.append(f"{name} 未记录存在且带 sha256")
        elif not os.path.isfile(current):
            issues.append(f"{name} 当前文件缺失：{rel}")
        else:
            current_sha = _sha256_file(current)
            if current_sha and current_sha != recorded_sha:
                issues.append(f"{name} 已变更但 prompt 未重签：{rel}")

    prompt_rows = data.get("prompt_files") if isinstance(data.get("prompt_files"), list) else []
    by_path = {_norm_receipt_rel(row.get("path")): row for row in prompt_rows if isinstance(row, Mapping)}
    for rel_fn in PROMPT_CONSUMED_PROMPTS[scope]:
        rel = _norm_receipt_rel(rel_fn(ep))
        row = by_path.get(rel)
        current = os.path.join(root, rel)
        if row is None:
            issues.append(f"缺 prompt 文件记录：{rel}")
            continue
        recorded_sha = str(row.get("sha256") or "").strip()
        if not row.get("exists") or not recorded_sha:
            issues.append(f"prompt 未记录存在且带 sha256：{rel}")
        elif not os.path.isfile(current):
            issues.append(f"prompt 当前文件缺失：{rel}")
        else:
            current_sha = _sha256_file(current)
            if current_sha and current_sha != recorded_sha:
                issues.append(f"prompt 已被改动但消费收据未更新：{rel}")

    if not issues:
        return
    add(
        BLOCK,
        "Prompt消费收据",
        path,
        "prompt pack 消费合同不新鲜或不完整，禁止进入昂贵生成："
        + "；".join(issues[:8])
        + ("；…" if len(issues) > 8 else ""),
        return_to_stage="image_prompt" if scope == "image_prompt" else "video_prompt",
        evidence_family="contract",
    )


_PLACEHOLDER_TEXT_RE = re.compile(
    r"^\s*(?:todo|tbd|待补|待定|占位|placeholder|xxx|无|none|null|n/?a|略|同上|见上|待确认)\s*$",
    re.I,
)


def _contract_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(value or "").strip()


def _meaningful_contract_value(value: Any, min_chars: int = 8) -> bool:
    if not _filled(value):
        return False
    text = re.sub(r"\s+", "", _contract_text(value))
    if len(text) < min_chars:
        return False
    return not _PLACEHOLDER_TEXT_RE.match(text)


def _value_any(seam: Mapping[str, Any], names: Tuple[str, ...]) -> Any:
    for name in names:
        value = seam.get(name)
        if _filled(value):
            return value
    return None


def _path_and_hash_from_seam(seam: Mapping[str, Any]) -> Tuple[str, str]:
    path_names = (
        "required_boundary_frame",
        "boundary_frame",
        "from_end_frame",
        "from_endframe",
        "end_frame",
        "endframe",
        "endframe_png",
        "from_endframe_png",
    )
    hash_names = (
        "required_boundary_frame_sha256",
        "boundary_frame_sha256",
        "from_end_frame_sha256",
        "from_endframe_sha256",
        "end_frame_sha256",
        "endframe_sha256",
        "endframe_png_sha256",
        "sha256",
    )
    path = ""
    digest = ""
    for name in path_names:
        value = seam.get(name)
        if isinstance(value, Mapping):
            path = str(value.get("path") or value.get("rel") or value.get("file") or "").strip()
            digest = str(value.get("sha256") or value.get("hash") or "").strip()
        elif _filled(value):
            path = str(value).strip()
        if path:
            break
    if not digest:
        for name in hash_names:
            value = seam.get(name)
            if _filled(value) and not isinstance(value, Mapping):
                digest = str(value).strip()
                break
    return path, digest


def _continuity_chain_seams(data: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    raw = data.get("seams")
    if isinstance(raw, list) and raw:
        return [s for s in raw if isinstance(s, Mapping)]
    clips = [c for c in data.get("clips") or [] if isinstance(c, Mapping)]
    seams: List[Mapping[str, Any]] = []
    for idx in range(max(0, len(clips) - 1)):
        current = clips[idx]
        nxt = clips[idx + 1]
        seams.append({
            "from_clip": current.get("clip_id") or current.get("id") or f"Clip_{idx + 1:02d}",
            "to_clip": nxt.get("clip_id") or nxt.get("id") or f"Clip_{idx + 2:02d}",
            "from_end_state": current.get("end_state"),
            "to_start_state": nxt.get("start_state"),
            "transition": current.get("transition_to_next") or current.get("transition"),
            "seam_mode": current.get("seam_mode"),
            "seam_evidence": current.get("seam_evidence") or {},
            "need_endframe": current.get("need_endframe") is True,
            "required_boundary_frame": current.get("endframe_png") or current.get("end_frame"),
            "common_entities": sorted(set(_listify(current.get("required_presence"))) & set(_listify(nxt.get("required_presence")))),
        })
    return seams


def check_seam_hard_contract(root: str, ep: str, stage: str) -> None:
    """Clip seams need executable visual/audio continuity before video spending."""
    if stage not in {"video_prompt_preflight", "video_preflight", "video"}:
        return
    path = os.path.join(root, "脚本", ep, "continuity_chain.json")
    data = load_json(path)
    if not isinstance(data, Mapping):
        return
    issues: List[str] = []
    clips = [c for c in data.get("clips") or [] if isinstance(c, Mapping)]
    clip_ids = [str(c.get("clip_id") or c.get("id") or "").strip() for c in clips if _filled(c.get("clip_id") or c.get("id"))]
    duplicate_ids = sorted({cid for cid in clip_ids if clip_ids.count(cid) > 1})
    if duplicate_ids:
        issues.append(f"continuity_chain clips[] clip_id 重复：{', '.join(duplicate_ids[:5])}")

    seams = _continuity_chain_seams(data)
    if not seams and len(clips) > 1:
        issues.append("缺 seams[]，且无法从 clips[] 推导接缝")
    for idx, seam in enumerate(seams, start=1):
        label = f"seam#{idx}"
        from_clip = str(seam.get("from_clip") or "").strip()
        to_clip = str(seam.get("to_clip") or "").strip()
        if not from_clip or not to_clip:
            issues.append(f"{label} 缺 from_clip/to_clip")
        elif from_clip == to_clip and seam.get("scope") != "episode_boundary":
            issues.append(f"{label} from_clip 与 to_clip 相同：{from_clip}")
        transition_value = _value_any(seam, ("transition", "transition_to_next", "cut_type"))
        if not _meaningful_contract_value(transition_value, min_chars=3):
            issues.append(f"{label} 缺可执行 transition")
        mode_info = normalize_seam_mode(
            seam.get("seam_mode"), transition_value,
            need_endframe=bool(seam.get("need_endframe")),
        )
        seam_mode = str(mode_info.get("mode") or "")
        if mode_info.get("source") != "explicit":
            issues.append(f"{label} 缺显式 seam_mode；旧 transition/need_endframe 推断不能替代剪辑决策")
        evidence = seam.get("seam_evidence") if isinstance(seam.get("seam_evidence"), Mapping) else {}
        discontinuity_reason = _value_any(seam, ("intentional_discontinuity_reason", "jump_cut_reason", "time_jump_reason"))
        if seam_mode == "intentional_discontinuity" and not discontinuity_reason:
            discontinuity_reason = evidence.get("reason")
        intentional = seam_mode == "intentional_discontinuity" and _meaningful_contract_value(discontinuity_reason, min_chars=10)
        mode_missing = list(seam_missing_evidence(seam_mode, evidence))
        if seam_mode == "continuous_take_relay":
            mode_missing = [field for field in mode_missing if field not in {"boundary_frame", "end_state", "start_state"}]
        if mode_missing:
            issues.append(f"{label} {seam_mode or '未分类'} 缺模式证据：{', '.join(mode_missing)}")
        if not intentional:
            if not _meaningful_contract_value(_value_any(seam, ("from_end_state", "previous_out_point", "out_point", "end_state")), min_chars=10):
                issues.append(f"{label} 缺 from_end_state/out_point")
            if not _meaningful_contract_value(_value_any(seam, ("to_start_state", "next_in_point", "in_point", "start_state")), min_chars=10):
                issues.append(f"{label} 缺 to_start_state/in_point")
            entity_value = _value_any(seam, (
                "entry_exit",
                "entity_entry_exit",
                "continuity_entities",
                "common_entities",
                "required_presence_delta",
                "presence_delta",
            ))
            if not _meaningful_contract_value(entity_value, min_chars=5):
                issues.append(f"{label} 缺人物/资产出入场链 entry_exit/common_entities")
            if requires_boundary_frame(seam_mode):
                frame_rel, frame_sha = _path_and_hash_from_seam(seam)
                if not frame_rel:
                    issues.append(f"{label} continuous_take_relay 缺 required_boundary_frame/from_end_frame")
                elif not frame_sha:
                    issues.append(f"{label} 缺边界帧 sha256：{frame_rel}")
                else:
                    frame_path = os.path.join(root, frame_rel)
                    if not os.path.isfile(frame_path):
                        issues.append(f"{label} 边界帧文件缺失：{frame_rel}")
                    else:
                        current_sha = _sha256_file(frame_path)
                        if current_sha and current_sha != frame_sha:
                            issues.append(f"{label} 边界帧 sha256 已过期：{frame_rel}")
                next_rel = str(seam.get("next_firstframe") or seam.get("to_firstframe") or "").strip()
                next_sha = str(seam.get("next_firstframe_sha256") or seam.get("to_firstframe_sha256") or "").strip()
                if not next_rel:
                    issues.append(f"{label} continuous_take_relay 缺 next_firstframe")
                elif not next_sha:
                    issues.append(f"{label} 缺下一首帧 sha256：{next_rel}")
                else:
                    next_path = os.path.join(root, next_rel)
                    if not os.path.isfile(next_path):
                        issues.append(f"{label} 下一首帧文件缺失：{next_rel}")
                    else:
                        current_next_sha = _sha256_file(next_path)
                        if current_next_sha and current_next_sha != next_sha:
                            issues.append(f"{label} 下一首帧 sha256 已过期：{next_rel}")
                if frame_sha and next_sha and frame_sha != next_sha:
                    issues.append(f"{label} relay 边界帧与下一首帧 SHA 不同，不能视为同一接点")
        if len(issues) >= 16:
            break

    if not issues:
        return
    add(
        BLOCK,
        "Clip接缝硬合同",
        path,
        "continuity_chain 的 clip/seam 还不足以进入视频生成："
        + "；".join(issues[:12])
        + ("；…" if len(issues) > 12 else "")
        + "。请在 n2d-script/repair_preflight 回补 seam_mode、模式证据、start/end state、出入场与声画衔接；仅 continuous_take_relay 补边界帧 sha256。",
        return_to_stage="script_stage2",
        evidence_family="continuity",
    )


_PICKUP_TOKENS_RE = re.compile(r"上一集|上集|前集|前情|承接|兑现|延迟|悬念|钩子|上一问题|未解|previous|prior|payoff|hook|delay|bridge", re.I)
_THROW_TOKENS_RE = re.compile(r"下一集|下集|继续|悬念|问题|目标|承诺|未兑现|待兑现|钩子|危机|追问|next|hook|promise|question|payoff", re.I)


def _handoff_quality_issue(value: Any, label: str, token_re: re.Pattern[str]) -> Optional[str]:
    if not _meaningful_contract_value(value, min_chars=12):
        return f"{label} 内容过薄或是占位"
    text = _contract_text(value)
    if not token_re.search(text):
        return f"{label} 没有明确写承接/兑现/延迟/可接收问题"
    return None


def check_series_handoff_contract(root: str, ep: str, stage: str) -> None:
    """Early episodes must explicitly pick up and throw cross-episode hooks."""
    if stage not in {"image_prompt_preflight", "image_preflight", "image"}:
        return
    data = _episode_storyboard(root, ep)
    if not data:
        return  # storyboard_contract owns missing/invalid storyboard.
    n = _ce_episode_number(ep)
    if not n or n > 5:
        return
    issues: List[str] = []
    hook_bridge = data.get("hook_bridge") if isinstance(data.get("hook_bridge"), Mapping) else {}
    previous_pickup = _field_value(data, "previous_episode_pickup", "opening_bridge")
    if not previous_pickup and _filled(hook_bridge.get("answers_prev_hook") or hook_bridge.get("bridge_text") or hook_bridge.get("delayed_payoff_ep")):
        previous_pickup = hook_bridge
    if n > 1 and not previous_pickup:
        issues.append("缺 previous_episode_pickup/opening_bridge：本集开头没有明示接住上一集问题、延迟兑现或切线理由")
    elif n > 1:
        issue = _handoff_quality_issue(previous_pickup, "previous_episode_pickup/opening_bridge", _PICKUP_TOKENS_RE)
        if issue:
            issues.append(issue)
    final_flag = bool(data.get("final_episode") or (isinstance(data.get("series_handoff"), Mapping) and data["series_handoff"].get("final_episode")))
    next_throw = _field_value(data, "ending_throw", "next_episode_receivable_hook")
    ledger = data.get("retention_promise_ledger") if isinstance(data.get("retention_promise_ledger"), list) else []
    if not next_throw and any(isinstance(row, Mapping) and _filled(row.get("payoff_due") or row.get("delayed_payoff_ep")) for row in ledger):
        next_throw = ledger
    if not final_flag and not next_throw:
        issues.append("缺 ending_throw/next_episode_receivable_hook：本集没有给下一集可承接的问题、目标或未兑现承诺")
    elif not final_flag:
        issue = _handoff_quality_issue(next_throw, "ending_throw/next_episode_receivable_hook", _THROW_TOKENS_RE)
        if issue:
            issues.append(issue)
    if not issues:
        return
    add(
        BLOCK,
        "跨集承接合同",
        os.path.join(root, "脚本", ep, "storyboard.json"),
        "早期集必须显式写跨集承接合同，避免集与集之间像拼接短片："
        + "；".join(issues)
        + "。建议字段：series_handoff.previous_episode_pickup / opening_bridge / ending_throw / next_episode_receivable_hook。",
        return_to_stage="script_stage2",
        evidence_family="retention",
    )


def _clip_is_dialogue_heavy(clip: Mapping[str, Any]) -> bool:
    template = str(clip.get("template") or clip.get("rhythm") or "").lower()
    if "dialogue" in template or "shot_reverse" in template or "反打" in template or "对话" in template:
        return True
    if _filled(clip.get("native_speech")):
        return True
    if isinstance(clip.get("dialogue_indices"), list) and clip.get("dialogue_indices"):
        return True
    if isinstance(clip.get("dialogue_lines"), list) and clip.get("dialogue_lines"):
        return True
    text = json.dumps(clip, ensure_ascii=False)
    return any(token in text for token in ("说话", "对白", "台词", "质问", "回答", "dialogue"))


def check_dialogue_timing_mode(root: str, ep: str, stage: str) -> None:
    """Dialogue-heavy episodes cannot enter video on rough video-first timing."""
    if stage not in {"video_prompt_preflight", "video_preflight"}:
        return
    if is_native_av_production(root) or not is_video_first(root):
        return
    if voice_is_placeholder(root, ep) is not True:
        return
    data = _episode_storyboard(root, ep)
    clips = _storyboard_clips(data)
    if not clips:
        return
    dialogue = [c for c in clips if _clip_is_dialogue_heavy(c)]
    ratio = len(dialogue) / max(1, len(clips))
    if len(dialogue) < 3 and ratio < 0.35:
        return
    add(
        BLOCK,
        "配音时长模式",
        os.path.join(root, "脚本", ep, "storyboard.json"),
        f"本集对白/反打/说话镜占比高（{len(dialogue)}/{len(clips)}），但仍是「先出视频后配音」+ 占位/估算时长。"
        "这类集若先出视频，clip 节奏、停顿、口型和 J/L cut 会被粗时长锁死。"
        "先切到配音先行或至少生成真实配音/可信时长清单，再重跑分镜定时和 video preflight。",
        return_to_stage="voice",
        evidence_family="audio_sync",
    )


def check_hybrid_performance_routes(root: str, ep: str, stage: str) -> None:
    """Enforce the execution half of mixed per-shot sound routing.

    Preflight may pass a neutral base plate with no audio.  Post-generation
    video/compose/review may not treat that plate as a finished talking shot.
    """
    if not is_hybrid_routing(root):
        return
    routes_path = os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json")
    data = load_json(routes_path)
    routes = data.get("routes") if isinstance(data, dict) else None
    if not isinstance(routes, list) or not routes:
        add(BLOCK, "逐镜声音路由", routes_path, "混合自动路由缺 video_model_routes.json routes；先重跑 n2d-model-router", return_to_stage="video_prompt")
        return
    preflight = stage in {"video_prompt_preflight", "video_preflight"}
    final_video_boundary = stage in {"video", "compose", "review"}
    for idx, route in enumerate(routes):
        if not isinstance(route, Mapping):
            continue
        cid = str(route.get("clip_id") or f"routes[{idx}]")
        strategy = str(route.get("audio_strategy") or "")
        if not strategy:
            add(BLOCK, "逐镜声音路由", routes_path, f"{cid} 缺 audio_strategy/timing_basis；混合模式不能退回项目级一刀切", return_to_stage="video_prompt")
            continue
        if strategy == "performance_audio_first":
            paths = []
            for raw in route.get("performance_audio_paths") or []:
                path = str(raw or "")
                path = path if os.path.isabs(path) else os.path.join(root, path)
                if os.path.isfile(path):
                    paths.append(path)
            if str(route.get("performance_track_status") or "") not in {"guide_ready", "final_ready"} or not paths:
                add(BLOCK, "表演音轨", routes_path, f"{cid} 路由为 performance_audio_first，但没有可验证的已签收音轨路径", return_to_stage="voice")
        if strategy == "base_video_then_post_lipsync":
            if route.get("base_video_only") is not True or route.get("post_lipsync_required") is not True:
                add(BLOCK, "后期表演通道", routes_path, f"{cid} 基础视频路线缺 base_video_only=true / post_lipsync_required=true", return_to_stage="video_prompt")
            if str(route.get("base_video_mouth_policy") or "") != "neutral_rest_no_visible_articulation":
                add(BLOCK, "后期表演通道", routes_path, f"{cid} 基础片未锁 neutral_rest_no_visible_articulation，可能提前生成假口型", return_to_stage="video_prompt")
            if preflight:
                add(WARN, "后期表演通道", routes_path, f"{cid} 只获准生成中性嘴型基础片；完成 lipsync_pass 前不是最终说话镜", return_to_stage="video")
            if final_video_boundary:
                declared = str(route.get("post_lipsync_output") or "").strip()
                candidates = [
                    declared,
                    os.path.join("出视频", ep, "视频_lipsync", f"{cid}_lipsync.mp4"),
                ]
                exists = False
                for raw in candidates:
                    if not raw:
                        continue
                    path = raw if os.path.isabs(raw) else os.path.join(root, raw)
                    if os.path.isfile(path):
                        exists = True
                        break
                if not exists:
                    add(
                        BLOCK, "后期表演通道", os.path.join(root, "出视频", ep, "视频_lipsync"),
                        f"{cid} 仍只有 base_video_only 基础片，缺最终后期口型/表演输出。"
                        f"先运行 python3 skills/n2d/n2d-video/scripts/lipsync_pass.py {root} {ep} --apply（或按 jobs 手工执行）。",
                        return_to_stage="video",
                    )
                else:
                    # 口型同步最小量化消费（2026-07 落地）：lipsync 回执现记录输出/音频时长差
                    # av_duration_delta_ms；>500ms 说明对口型工具吞/拉了轨（"偏差大则重跑"从散文
                    # 变成可查数字）。仍是 warn——真口型同步度量（嘴部-音频包络）另议，时长差只是下限信号。
                    jobs_payload = load_json(os.path.join(root, "出视频", ep, "control", "lipsync_jobs.json"))
                    for job in (jobs_payload.get("jobs") or []) if isinstance(jobs_payload, Mapping) else []:
                        if not isinstance(job, Mapping) or str(job.get("clip_id") or "") != cid:
                            continue
                        delta = job.get("av_duration_delta_ms")
                        if isinstance(delta, (int, float)) and delta > 500:
                            add(WARN, "后期表演通道",
                                os.path.join(root, "出视频", ep, "control", "lipsync_jobs.json"),
                                f"{cid} lipsync 输出与音频时长差 {delta:.0f}ms（>500ms）：对口型工具可能吞/拉了轨，"
                                "复核该镜口型后决定是否重跑 lipsync_pass。",
                                return_to_stage="video")
    if stage in {"compose", "review"} and any(isinstance(row, Mapping) and row.get("final_voice_required") is True for row in routes):
        casting = load_json(os.path.join(root, "设定库", "voice_casting.json"))
        if not isinstance(casting, dict) or casting.get("status") != "locked":
            add(BLOCK, "声音选角", os.path.join(root, "设定库", "voice_casting.json"),
                "最终声音已进入合成边界，但 voice_casting.status 不是 locked；先完成角色声音定妆签收。", return_to_stage="voice")
        fit_strategies = {"rough_timing_final_dub_later", "post_dub", "base_video_then_post_lipsync"}
        fit_routes = [
            str(row.get("clip_id") or row.get("id") or "")
            for row in routes if isinstance(row, Mapping) and str(row.get("audio_strategy") or "") in fit_strategies
        ]
        if fit_routes:
            report_path = os.path.join(root, "合成", ep, "配音", "voice_fit_zh.json")
            fitted_path = os.path.join(root, "合成", ep, "配音", "voice_zh_fitted.wav")
            report = load_json(report_path)
            report_scope = {str(x) for x in (report.get("fit_scope") or [])} if isinstance(report, Mapping) else set()
            missing_scope = sorted(set(fit_routes) - report_scope)
            input_hashes = report.get("input_sha256") if isinstance(report, Mapping) and isinstance(report.get("input_sha256"), Mapping) else {}
            expected_inputs = {
                "shot_durations": os.path.join(root, "脚本", ep, "镜头时长.json"),
                "voice_manifest": os.path.join(root, "合成", ep, "配音", "时长清单.json"),
                "production_mode_route": os.path.join(root, "生产数据", f"production_mode_route_{ep}.json"),
            }
            stale_inputs = sorted(
                key for key, path in expected_inputs.items()
                if not input_hashes.get(key) or input_hashes.get(key) != _safe_sha256(path)
            )
            fitted_hash_stale = bool(
                isinstance(report, Mapping)
                and (not report.get("output_sha256") or report.get("output_sha256") != _safe_sha256(fitted_path))
            )
            if (
                not isinstance(report, Mapping)
                or report.get("kind") != "n2d_voice_fit_report"
                or report.get("status") != "pass"
                or report.get("applied") is not True
                or not os.path.isfile(fitted_path)
                or missing_scope
                or stale_inputs
                or fitted_hash_stale
            ):
                add(
                    BLOCK,
                    "后配音时长拟合",
                    report_path,
                    f"混合模式有 {len(fit_routes)} 个按粗时长锁画面的后配镜，但缺新鲜 pass 拟合报告/轨，"
                    f"或报告未覆盖 {missing_scope or '全部 route'}、输入已变更 {stale_inputs or '无'}、拟合轨哈希过期={fitted_hash_stale}。"
                    f"先运行 `python3 skills/n2d/n2d-compose/fit_voice_to_clips.py {root} {ep} zh --apply`；"
                    "overflow 必须局部重定时/重出，不得直接拿整轨合成。",
                    return_to_stage="compose",
                    affected_artifacts=[report_path, fitted_path],
                    evidence_family="audio_sync",
                )


def check_bgm_machine_contract(root: str, ep: str, *, allow_placeholder: bool = True) -> None:
    """BGM must be an explicit machine contract, not a silent sine-wave fallback."""
    path = str(bgm_contract_core.contract_path(root, ep))
    for issue in bgm_contract_core.validate(root, ep, allow_placeholder=allow_placeholder):
        add(
            BLOCK,
            "BGM合同",
            path,
            f"[{issue.get('code')}] {issue.get('message')}",
            return_to_stage="compose",
            affected_artifacts=[path, os.path.join(root, "脚本", ep, "bgm.txt")],
            evidence_family="audio_sync",
        )


def check_series_consistency_baseline(root: str, ep: str, stage: str) -> None:
    if not series_consistency_core.required(root):
        return
    phase = "full" if gate_family(stage) in {"compose", "review"} else "script"
    contract_path = str(series_consistency_core.path(root))
    for issue in series_consistency_core.validate(root, ep, phase=phase):
        add(
            BLOCK,
            "剧级一致性合同",
            contract_path,
            f"[{issue.get('code')}] {issue.get('message')} 运行 `python3 skills/n2d/scripts/series_consistency.py {root} {ep} --phase {phase} --write-missing --json` 补齐后签收。",
            return_to_stage="script_stage1" if phase == "script" else "compose",
            affected_artifacts=[contract_path],
            evidence_family="contract",
        )


def check_scene_lock_execution(root: str, ep: str) -> None:
    """A planned scene lock only counts after its plate/subject/LoRA is executable."""
    _, referenced_assets = episode_registry_reference_ids(root, ep)
    referenced_locations = {str(value) for value in referenced_assets if str(value).upper().startswith("LOC_")}
    if not referenced_locations:
        return
    plan_path = os.path.join(root, "生产数据", f"scene_reference_plan_{ep}.json")
    plan = load_json(plan_path)
    if not isinstance(plan, Mapping) or plan.get("kind") != "n2d_scene_reference_plan":
        add(
            BLOCK, "场景锁执行", plan_path,
            f"缺场景生成侧执行计划；先运行 `python3 skills/n2d/n2d-image/scripts/scene_reference_planner.py {root} {ep} --write --json`。",
            return_to_stage="image_prompt", evidence_family="contract",
        )
        return
    for row in plan.get("locations") or []:
        if not isinstance(row, Mapping):
            continue
        loc_id = str(row.get("loc_id") or "LOC_unknown")
        if loc_id not in referenced_locations:
            continue
        if row.get("master_anchor") and not str(row.get("master_anchor_ref") or "").strip():
            add(BLOCK, "场景锁执行", plan_path,
                f"{loc_id} 同集达到 master plate 阈值，但只有计划 ID、没有真实 master_anchor_ref；先补场景主全景 plate。",
                return_to_stage="image_prompt", affected_shots=[loc_id], evidence_family="contract")
        if row.get("subject_registration_required") is True and row.get("is_core") and int(row.get("cross_eps") or 0) >= 3:
            add(BLOCK, "场景锁执行", plan_path,
                f"核心长线场景 {loc_id} 的后端支持 subject，但 registry 尚未 registered/ready；能力声明不能冒充已注册执行。",
                return_to_stage="image_prompt", affected_shots=[loc_id], evidence_family="contract")
        if row.get("suggest_scene_lora") is True:
            add(BLOCK, "场景锁执行", plan_path,
                f"核心长线场景 {loc_id} 无可用后端 subject 且已触发 scene LoRA 升档；先执行 scene_lock job/register，或显式改用已注册场景主体后端。",
                return_to_stage="image_prompt", affected_shots=[loc_id], evidence_family="contract")
        refs = [ref for ref in row.get("refs") or [] if isinstance(ref, Mapping)]
        if not any(ref.get("slot") in {"primary", "master_plate"} and str(ref.get("ref") or "").strip() and not ref.get("planned") for ref in refs):
            add(BLOCK, "场景锁执行", plan_path,
                f"{loc_id} 缺可执行 primary/master scene plate；场景锁仍是空计划。",
                return_to_stage="image_prompt", affected_shots=[loc_id], evidence_family="contract")


def run(root: str, ep: str, stage: str) -> None:
    _DEGRADED_QC_WAIVERS.clear()  # 每次 gate 运行重置降级 waiver 账本（进程内复用/测试安全）
    _HEURISTIC_BLOCK_DEMOTIONS.clear()  # 同上：重置启发式降级账本
    if not os.path.isdir(root):
        add(BLOCK, "路径", root, "作品根不存在")
        return
    check_gate_policy_matrix(stage)
    check_consistency_rule_registry(root, ep, stage)
    check_production_mode_contract_sync(root, ep, stage)
    check_series_consistency_baseline(root, ep, stage)
    check_stage = policy_family_for_stage(stage, fallback=gate_family(stage))
    if check_stage in {"video_prompt_preflight", "video", "compose", "review"}:
        check_hybrid_performance_routes(root, ep, stage)
    if check_stage not in {"image_prompt_preflight", "video_prompt_preflight"}:
        check_preventive_contracts(root, ep, stage)
    av_native = is_native_av_production(root)  # 原生音画：说话镜不跑配音，不要求「配音」列就绪
    if check_stage == "image_prompt_preflight":
        check_compliance_manifest(root, ep, "image")
        # Prompt 生成前只查上游确定性契约；不得要求本阶段即将生成的出图 prompt/registry 已存在。
        image_prereq = ("分镜设计",) if av_native else ("配音", "分镜设计")
        require_progress(root, ep, image_prereq)
        check_progress_artifact_signoff(root, ep, image_prereq)
        check_placeholder_policy(root, ep, "image")
        check_voiceover_fingerprint(root, ep)
        check_timing_manifest_complete(root, ep)
        check_voice_cross_episode(root, ep)
        check_image_ai_policy(root, ep)
        check_lora_exception_scope(root, ep)
        check_backend_reachable(root, ep)
        check_drift_risk_advisories(root, ep)
        check_drift_report_freshness(root, ep)  # measured-drift BLOCK 环的报告新鲜度闸（堵静默退化）
        check_cross_episode_character_definition(root, ep)
        check_cross_episode_action_handoff(root, ep)
        check_storyboard_contract(root, ep, require_frame_assets=False)
        check_storyboard_possession_gate(root, ep)
        check_storyboard_visual_contract(root, ep)
        check_storyboard_style_contract(root, ep)
        check_stylized_face_encoder_policy(root, ep, stage)
        check_storyboard_special_templates(root, ep)
        check_script_quality_contract(root, ep)
        check_series_handoff_contract(root, ep, stage)
        check_story_economy_audit(root, ep, stage)
        check_production_handoff_pack(root, ep, stage)
        check_skill_freshness(root, ep, stage)  # 重生成出图 prompt 前先看 skill 是否漂移
    elif check_stage == "image":
        check_compliance_manifest(root, ep, check_stage)
        # image 阶段只在「先出视频后配音」模式允许 rough timing 做 demo 出图；
        # 配音先行仍必须真实配音。不要把 rough 配音强写成 ✅。
        image_prereq = ("分镜设计",) if av_native else ("配音", "分镜设计")
        require_progress(root, ep, image_prereq)
        check_progress_artifact_signoff(root, ep, image_prereq)
        check_placeholder_policy(root, ep, check_stage)
        check_voiceover_fingerprint(root, ep)
        check_timing_manifest_complete(root, ep)
        check_voice_cross_episode(root, ep)
        check_image_ai_policy(root, ep)
        check_image_backend_baseline(root, ep, stage)
        check_keyshot_candidate_plan(root, ep, stage)
        check_lora_exception_scope(root, ep)
        check_backend_reachable(root, ep)
        check_budget_cap(root, ep)
        if stage == "image_preflight":
            check_storyboard_video_feasibility_before_images(root, ep)
            check_production_locks_preflight(root, ep, stage)
            check_image_backend_api_refresh(root, ep)
        # 已测得的跨集脸/资产漂移 BLOCK 不分预检/出图后——整个 image family 都跑，避免直接 `--stage image`
        # 跳过预检时上一集已漂移的角色蒙混过出图后 gate。
        check_drift_risk_advisories(root, ep)
        check_drift_report_freshness(root, ep)  # measured-drift BLOCK 环的报告新鲜度闸（堵静默退化）
        check_cross_episode_character_definition(root, ep)  # 跨集角色文字定义漂移（重派生）信号
        if stage == "image_preflight":
            check_reference_plan_applied(root, ep)  # 逐镜参考规划落实对账（advisory·治跨集脸漂）
            check_director_camera_plan_consumption(root, ep)  # 导演运镜计划→出图 prompt 消费收据（治「规划好没落片」·高潮镜未消费 BLOCK）
            check_long_running_weak_backend(root, ep)  # 长线剧×无持久主体 ID 后端→核心/常驻角色必须升身份锁
            check_stylized_face_encoder_policy(root, ep, stage)
            # P1（2026-06-26）：付费出图前的**叙事/留存地板**——批量 runner 经 dashboard 直接跑 image_preflight
            # gate（不走 run.py --strict），这道地板此前只在 run.py 生效、批量路径漏掉，平庸集照样烧钱出图。
            check_series_retention_gate(root, ep, stage)    # 系列冷开场链 / pilot 弧（激活原 dead-code 的 image_preflight 分支）
            check_episode_narrative_floor(root, ep, stage)  # 逐集首屏 3s 钩 / 留存承诺账本（must→production BLOCK·可签收）
            check_skill_freshness(root, ep, stage)          # 花钱出图前：skill 漂移 → 物料可能过期（BLOCK·路由 n2d-update/repair_preflight）
        # 两层出图不变量（2026-06-27 修 charter 审计发现的"声明漏洞"）：出图闸此前对共享资产只验
        # identity_registry/asset_registry 里写没写 status:ready 字符串，不验多角度定妆/武器/服饰的
        # 共享 PNG 是否真在磁盘——真存在性核对被推迟到出视频阶段，于是逐镜帧/clip 可能在共享图仅
        # "声明 ready"未真生成时就被产出。这里前移：本集**已有逐镜帧**(出图后)时，对本集**引用到的**
        # 共享角色/资产升到文件级核对（require_reference_assets=True）；共享库自举那一次(还没逐镜帧)
        # 保持原行为不卡死。回归测试 test_gate.py::test_image_stage_requires_real_shared_pngs_once_frames_exist 守护。
        _require_real_refs = (stage == "image") and _episode_has_per_shot_frames(root, ep)
        _ref_identity_refs = episode_registry_identity_refs(root, ep)
        if _require_real_refs:
            _ref_chars, _ref_assets = episode_registry_reference_ids(root, ep)
            check_identity_registry(root, require_reference_assets=True, required_character_ids=_ref_chars, required_identity_refs=_ref_identity_refs)
            check_production_core_identity_lock(root, ep, stage)
            check_costume_registry_reconcile(root)
            check_asset_reference_registry(root, require_reference_assets=True, required_asset_ids=_ref_assets)
        else:
            _ref_chars, _ = episode_registry_reference_ids(root, ep)
            check_identity_registry(root, require_reference_assets=False, required_character_ids=_ref_chars, required_identity_refs=_ref_identity_refs)
            check_production_core_identity_lock(root, ep, stage)
            check_costume_registry_reconcile(root)
            check_asset_reference_registry(root, require_reference_assets=False)
        # B7 核心人物五角+表情逐视图收据：不信任 ready 字符串，只读当前 PNG hash 绑定的人审证据。
        check_identity_eval_pack(root, ep)
        # 标记解析（花钱前）：本集引用到的 CHAR_/LOC_/PROP_/WEAPON_/OUTFIT_/VFX_ id 必须在注册层真实存在。
        # registry schema 已由上面两道校验保证；这里加 referenced⊆registered，堵「写错 id 空烧」（image_preflight 即拦）。
        check_referenced_markers_resolve(root, ep)
        check_scene_lock_execution(root, ep)
        check_storyboard_contract(root, ep, require_frame_assets=False)
        check_storyboard_possession_gate(root, ep)
        check_storyboard_visual_contract(root, ep)
        # script→image 接缝内容 diff（补在场校验之外的漂移拦截）：storyboard 光位/轴线种子被出图
        # 00_总览 誊抄改写=下游全部忠实继承错误权威源。与 出图→出视频 契约继承对称，光位/轴线漂移=BLOCK。
        check_storyboard_image_contract_inheritance(root, ep)
        check_storyboard_style_contract(root, ep)
        check_cross_episode_style(root, ep)
        check_cross_episode_contract(root, ep)
        check_cross_episode_action_handoff(root, ep)
        check_storyboard_special_templates(root, ep)
        check_script_quality_contract(root, ep)
        check_series_handoff_contract(root, ep, stage)
        check_story_economy_audit(root, ep, stage)
        check_production_handoff_pack(root, ep, stage)
        check_prompt_consumed_contracts(root, ep, stage)
        check_image_prompt_overview(root, ep)
        check_prompt_checklists(root, ep, "image")
        check_script_contract_consumption(root, ep, ("出图",))
        check_semantic_lineage(root, ep)
        check_state_continuity(root, ep)
        check_shared_image_index(root, ep)
        check_referenced_assets_finalized(root, ep)
        check_anchor_fingerprints(root, ep)
        check_core_anchor_pinning(root, ep)
        check_expression_anchors(root, ep)
        check_character_backend_pin(root, ep)
        check_seed_event_records(root, ep)
        check_generation_recipe_evidence(root, ep, stage)
        check_common_image_prompts(root)
        check_cinematic_optical_continuity(root, ep)
        check_shot_scale_progression(root, ep)
        check_noncharacter_insert_coverage(root, ep)
        check_physical_scale_audit(root, ep)
        if stage == "image":
            # 生成后落档机检：崩脸/人体解剖N5/接缝断/降级精度近景/角色脸覆盖缺口的**像素**硬挡，此前只挂在
            # video / video_prompt_preflight 阶段（gate.py:5770/5794），出图阶段（runner 生成后跑的
            # 就是 `--stage image`）一直不接 → 崩脸要拖到最贵的「出视频」工位才被拦。现接进 image 阶段，
            # 让崩脸在最近的出图闸门即 BLOCK。pre-gen 的 image_preflight 不跑（此时还没 PNG/QC 报告，
            # 见 check_input_frame_qc 对无 PNG 的优雅降级）。
            check_input_frame_qc(root, ep)
            # 一致性总审同样前移到出图后闸门：手部多指/天气硬跳/极端身高/禁用称谓/动作硬断等**确定性
            # 🔴 维度**此前只在 compose/review（已花完出视频钱）才拦。出图后 PNG 已在、clip 未出——
            # 此处跑全套 consistency_audit，确定性 block 维度即 BLOCK，把它们挡在最贵的「出视频」之前。
            # stage="image"：降级精度（缺 insightface）按既有逻辑只降级为 WARN（不硬拦无依赖产线，
            # 交付边界 compose/review 才对降级精度 BLOCK，逃生口仍是 N2D_ALLOW_DEGRADED_QC）。
            check_consistency_audit_gate(root, ep, stage="image")
    elif check_stage == "video_prompt_preflight":
        check_compliance_manifest(root, ep, "video")
        # 视频 prompt 生成前必须证明首帧/尾帧和身份矩阵已可继承，但不得要求视频 prompt 文件已存在。
        video_prereq = ("分镜设计", "出图prompt", "出图") if av_native else ("配音", "分镜设计", "出图prompt", "出图")
        require_progress(root, ep, video_prereq)
        check_progress_artifact_signoff(root, ep, video_prereq)
        check_placeholder_policy(root, ep, "video")
        check_voiceover_fingerprint(root, ep)
        check_timing_manifest_complete(root, ep)
        check_voice_cross_episode(root, ep)
        referenced_characters, referenced_assets = episode_registry_reference_ids(root, ep)
        referenced_identity_refs = episode_registry_identity_refs(root, ep)
        check_identity_registry(root, require_reference_assets=True, required_character_ids=referenced_characters, required_identity_refs=referenced_identity_refs)
        check_production_core_identity_lock(root, ep, stage)
        check_asset_reference_registry(root, require_reference_assets=True, required_asset_ids=referenced_assets)
        check_referenced_markers_resolve(root, ep)  # 引用到的标记必须在注册层真实存在（防写错 id）
        check_identity_adapter_matrix(root)
        check_route_identity_readiness(root, ep)
        check_storyboard_contract(root, ep, require_frame_assets=True)
        check_action_anchor_contract(root, ep, check_stage)
        check_dialogue_fact_contract(root, ep, stage)
        check_storyboard_style_contract(root, ep)
        check_storyboard_special_templates(root, ep)
        check_director_camera_plan_consumption(root, ep)  # 导演运镜计划→出视频 prompt 消费收据（治「规划好没落片」）
        check_script_quality_contract(root, ep)
        check_dialogue_timing_mode(root, ep, stage)
        check_story_economy_audit(root, ep, stage)
        check_production_handoff_pack(root, ep, stage)
        check_production_locks_preflight(root, ep, stage)
        check_seam_hard_contract(root, ep, stage)
        check_script_contract_consumption(root, ep, ("出图",))
        check_spectacle_sequence_plan(root, ep)
        check_action_beat_budget(root, ep, check_stage)
        check_expression_span_frame_contract(root, ep)
        check_core_expression_anchor_coverage(root, ep)
        check_image_assets(root, ep)
        check_input_frame_qc(root, ep)
        # Router feasibility and image-generation receipts are both knowable
        # before video prompt generation; do not defer them to paid-video preflight.
        check_video_model_routes(root, ep, "本集模型路由表", os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json"))
        check_generation_recipe_evidence(root, ep, stage)
        check_multimodal_continuity(root, ep)
        check_semantic_lineage(root, ep)
        check_state_continuity(root, ep)
        check_video_backend_reachable(root, ep)
        check_skill_freshness(root, ep, stage)  # 重生成视频 prompt 前先看 skill 是否漂移
    elif check_stage == "video":
        check_compliance_manifest(root, ep, check_stage)
        video_prereq = ("分镜设计", "出图prompt") if av_native else ("配音", "分镜设计", "出图prompt")
        require_progress(root, ep, video_prereq)
        check_progress_artifact_signoff(root, ep, video_prereq)
        check_placeholder_policy(root, ep, check_stage)
        if stage == "video_preflight":
            check_skill_freshness(root, ep, stage)  # 花钱出视频前：skill 漂移 → 物料可能过期（BLOCK·路由 n2d-update/repair_preflight）
        check_voiceover_fingerprint(root, ep)
        # 一角一色跨集契约：video 阶段也再校一次（出图→出视频之间若改了 voicemap/补配音）。
        check_timing_manifest_complete(root, ep)
        check_voice_cross_episode(root, ep)
        referenced_characters, referenced_assets = episode_registry_reference_ids(root, ep)
        referenced_identity_refs = episode_registry_identity_refs(root, ep)
        check_identity_registry(root, require_reference_assets=True, required_character_ids=referenced_characters, required_identity_refs=referenced_identity_refs)
        check_production_core_identity_lock(root, ep, stage)
        check_asset_reference_registry(root, require_reference_assets=True, required_asset_ids=referenced_assets)
        check_referenced_markers_resolve(root, ep)  # 引用到的标记必须在注册层真实存在（防写错 id）
        check_identity_adapter_matrix(root)
        check_route_identity_readiness(root, ep)
        check_storyboard_contract(root, ep, require_frame_assets=True)
        check_action_anchor_contract(root, ep, check_stage)
        check_dialogue_fact_contract(root, ep, stage)
        check_storyboard_style_contract(root, ep)
        check_storyboard_special_templates(root, ep)
        check_director_camera_plan_consumption(root, ep)  # 导演运镜计划→出视频 prompt 消费收据（治「规划好没落片」）
        check_script_quality_contract(root, ep)
        check_dialogue_timing_mode(root, ep, stage)
        check_spectacle_sequence_plan(root, ep)
        check_action_beat_budget(root, ep, check_stage)
        check_expression_span_frame_contract(root, ep)
        check_core_expression_anchor_coverage(root, ep)
        check_image_assets(root, ep)
        check_input_frame_qc(root, ep)
        check_video_prompt_frames(root, ep, stage)
        check_video_backend_reachable(root, ep)
        check_budget_cap(root, ep)
        if stage == "video_preflight":
            check_production_locks_preflight(root, ep, stage)
        check_seam_hard_contract(root, ep, stage)
        check_prompt_consumed_contracts(root, ep, stage)
        check_multimodal_continuity(root, ep)
        check_prompt_checklists(root, ep, "video")
        check_script_contract_consumption(root, ep, ("出图", "出视频"))
        check_video_stage_raw_output_policy(root, ep)
        check_generation_recipe_evidence(root, ep, stage)
        check_video_post_qc_artifacts(root, ep, stage)
        check_contract_inheritance(root, ep)
        check_cross_episode_contract(root, ep)
        check_identity_handoff_inheritance(root, ep)
        check_asset_handoff_inheritance(root, ep)
        check_story_economy_audit(root, ep, stage)
        check_production_handoff_pack(root, ep, stage)
        check_semantic_lineage(root, ep)
        check_state_continuity(root, ep)
        if stage == "video":
            # 视频落档后立即跑总审：重型 sidecar 缺证据、主体串换、相机/动作问题不要拖到 compose 才回流。
            check_consistency_audit_gate(root, ep, stage="video")
    elif check_stage == "compose":
        check_bgm_machine_contract(root, ep)
        check_compliance_manifest(root, ep, check_stage)
        require_progress(root, ep, ("视频",))
        check_progress_artifact_signoff(root, ep, ("视频",))
        # 一角一色跨集契约在出图后若被改 voicemap/补配音会失效——compose 终装前再校一次，
        # 不让出图后编辑悄悄绕过跨集换声 BLOCK。（原仅在 image 阶段校验，是上次审计的遗留 gap）
        check_timing_manifest_complete(root, ep)
        check_voice_cross_episode(root, ep)
        referenced_characters, referenced_assets = episode_registry_reference_ids(root, ep)
        referenced_identity_refs = episode_registry_identity_refs(root, ep)
        check_identity_registry(root, require_reference_assets=True, required_character_ids=referenced_characters, required_identity_refs=referenced_identity_refs)
        check_asset_reference_registry(root, require_reference_assets=True, required_asset_ids=referenced_assets)
        check_referenced_markers_resolve(root, ep)  # 引用到的标记必须在注册层真实存在（防写错 id）
        check_identity_adapter_matrix(root)
        check_storyboard_contract(root, ep, require_frame_assets=True)
        check_storyboard_special_templates(root, ep)
        check_semantic_lineage(root, ep)
        check_state_continuity(root, ep)
        # 跨集视觉契约（光位/轴线翻）+ 跨集角色文字定义漂移：出图后到合成前若改了 00_总览.md，
        # 越轴/光跳/换脸会一路绿灯到成片。compose 终装前再校一次——和 check_voice_cross_episode 进
        # compose 同理（不让出图后编辑悄悄绕过跨集一致性），补此前只在 image/video 校验的不对称遗留。
        check_cross_episode_contract(root, ep)
        check_cross_episode_character_definition(root, ep)
        sb = load_json(os.path.join(root, "脚本", ep, "storyboard.json"))
        if sb:
            check_voice_conditioned_lipsync_policy(root, ep, sb)
        check_compose_inputs(root, ep)
        check_native_av_subtitle_alignment(root, ep, stage)
        check_native_voice_identity(root, ep, stage)
        check_stylized_face_encoder_policy(root, ep, stage)
        check_translation_glossary_release_gate(root, ep, stage)
        check_generation_recipe_evidence(root, ep, stage)
        check_video_post_qc_artifacts(root, ep, stage)
        check_series_retention_gate(root, ep, stage)
        check_consistency_audit_gate(root, ep, stage="compose")
        check_progress_receipt_reconcile(root, ep, current_stage="compose")  # H3：成片前对账已标 ✅ 的上游受闸列都有新鲜凭据
    elif check_stage == "review":
        check_bgm_machine_contract(root, ep, allow_placeholder=False)
        check_compliance_manifest(root, ep, check_stage)
        referenced_characters, referenced_assets = episode_registry_reference_ids(root, ep)
        referenced_identity_refs = episode_registry_identity_refs(root, ep)
        check_identity_registry(root, require_reference_assets=True, required_character_ids=referenced_characters, required_identity_refs=referenced_identity_refs)
        check_asset_reference_registry(root, require_reference_assets=True, required_asset_ids=referenced_assets)
        check_referenced_markers_resolve(root, ep)  # 引用到的标记必须在注册层真实存在（防写错 id）
        check_identity_adapter_matrix(root)
        check_storyboard_contract(root, ep, require_frame_assets=True)
        check_storyboard_special_templates(root, ep)
        check_video_assets(root, ep)
        check_semantic_lineage(root, ep)
        check_state_continuity(root, ep)
        check_multimodal_continuity(root, ep)
        check_subtitle_alignment(root, ep)
        check_native_av_subtitle_alignment(root, ep, stage)
        check_native_voice_identity(root, ep, stage)
        check_stylized_face_encoder_policy(root, ep, stage)
        check_translation_glossary_release_gate(root, ep, stage)
        check_generation_recipe_evidence(root, ep, stage)
        check_video_post_qc_artifacts(root, ep, stage)
        check_cross_episode_contract(root, ep)
        check_cross_episode_character_definition(root, ep)
        check_identity_handoff_inheritance(root, ep)
        check_asset_handoff_inheritance(root, ep)
        check_series_retention_gate(root, ep, stage)
        check_consistency_audit_gate(root, ep, stage="review")
        check_consistency_ledger_gate(root, ep)
        check_series_ledger_gate(root, ep)  # 2026-07-26：季级总账铁律此前从未被流水线调用，落地为 review 闸
        check_progress_receipt_reconcile(root, ep, current_stage="review")  # H3：验收前对账每个上游受闸列 ✅ 都有新鲜凭据（抓带外 ✅）
    else:
        add(BLOCK, "参数", stage, "未知 stage")

    # #4 单一 waiver 收口：把本次 gate 累积的降级 QC waiver 汇成一条可查 rollup（满档=无此 finding）。
    rollup = consistency_waiver_rollup(_DEGRADED_QC_WAIVERS, stage)
    if rollup is not None:
        sev, loc, msg = rollup
        add(sev, loc, ep, msg)

    # #3 启发式降级收口：把本次 gate 静默降级的 would-be-BLOCK 汇成一条可查 rollup（无降级=无此 finding）。
    demotion_rollup = heuristic_demotion_rollup(_HEURISTIC_BLOCK_DEMOTIONS, stage)
    if demotion_rollup is not None:
        sev, loc, msg = demotion_rollup
        add(sev, "gate", ep, msg)
def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--stage", required=True, choices=GATE_STAGES)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    run(ns.root.rstrip("/"), ns.episode, ns.stage)
    structured = [annotate_finding(f, ns.stage, ep=ns.episode) for f in findings]
    if ns.json:
        print(json.dumps(structured, ensure_ascii=False, indent=2))
    else:
        blocks = sum(1 for f in structured if f["sev"] == BLOCK)
        warns = sum(1 for f in structured if f["sev"] == WARN)
        infos = sum(1 for f in structured if f["sev"] == INFO)
        print(f"=== n2d gate: {ns.root} {ns.episode} stage={ns.stage} ===")
        print(f"block {blocks} · warn {warns} · info {infos}\n")
        for f in sorted(structured, key=_finding_sort_key):
            icon = {"block": "⛔", "warn": _warn_icon(_warn_tier(f.get("risk_score"))), "info": "ℹ️"}[f["sev"]]
            icon = {"block": "⛔", "warn": _warn_icon(_warn_tier(f.get("risk_score"))), "info": "ℹ️"}[f["sev"]]
            print(f"{icon} [{f['dim']}] {f['loc']}: {f['msg']}")
            if f.get("return_to_stage") and f["sev"] == BLOCK:
                print(f"   ↳ 回退: {f['return_to_stage']} · {f.get('rerun_scope', '')}")
    return 1 if any(f["sev"] == BLOCK for f in findings) else 0
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
