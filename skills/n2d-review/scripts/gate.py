#!/usr/bin/env python3
"""Deterministic stage gates for n2d.

This script turns the high-risk SKILL.md rules into repeatable checks.  It does
not create assets; it only reports whether a stage may proceed.

Usage:
  # Production entry: records QA findings and returns this gate's exit code.
  python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image_preflight|video_preflight|image|video|compose|review

  # Engine/debug entry: deterministic findings only, no dashboard telemetry.
  python3 skills/n2d-review/scripts/gate.py <作品根> 第N集 --stage video --json

Exit codes:
  0 = no blockers
  1 = at least one blocker
  2 = bad invocation / missing project
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SCRIPT_DIR = os.path.dirname(__file__)
COMMON = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from n2d_contract import (  # noqa: E402
    APPROVED_IMAGE_BACKENDS,
    ASSET_REFERENCE_REGISTRY_KIND,
    CINEMATIC_CONTRACT_FIELDS,
    CONSISTENCY_DIMENSIONS,
    COMPLIANCE_ALLOWED_RIGHTS,
    COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS,
    COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS,
    COMPLIANCE_RIGHTS_EVIDENCE_REQUIRED,
    COMPLIANCE_APPROVED_CHARACTER,
    COMPLIANCE_BLOCKED_CHARACTER,
    COMPLIANCE_DONE_STATUSES,
    COMPLIANCE_DOMESTIC_REGIONS,
    COMPLIANCE_MANIFEST_KIND,
    COMPLIANCE_OVERSEAS_PLATFORMS,
    COMPLIANCE_PLACEHOLDER_MARKERS,
    COMPLIANCE_PLATFORM_REVIEW_STATUSES,
    COMPLIANCE_PRE_BROADCAST_STATUSES,
    COMPLIANCE_READY_STATUSES,
    COMPLIANCE_SAFE_VOICE,
    COMPLIANCE_STATUS_LIKE_VALUES,
    EXPRESSION_SPAN_BIG,
    EXPRESSION_SPAN_VALUES,
    GATE_STAGES,
    HIGH_MOTION_TEMPLATES,
    IDENTITY_ADAPTER_MATRIX_KIND,
    IDENTITY_HANDLE_FIELDS,
    IDENTITY_IMAGE_ADAPTERS,
    IDENTITY_REFERENCE_KEYS,
    IDENTITY_REGISTRY_KIND,
    IDENTITY_VIDEO_ADAPTERS,
    identity_allowed_modes,
    identity_registry_path,
    MOTION_CONTROL_MANIFEST_KIND,
    MOTION_CONTROL_REQUIRED_SHOT_TYPES,
    MOTION_CONTROL_RISK_FLAGS,
    STYLE_CONTRACT_FIELDS,
    VIDEO_MODEL_ROUTES_KIND,
    VISUAL_CONTRACT_FIELDS,
    VOICE_KEY_FIELD,
    VOICE_KEY_LEGACY_FIELD,
    annotate_finding,
    asset_registry_path,
    classify_image_backend,
    lora_gap_message,
    lora_registry_ready_blocks,
    motion_control_required,
    shared_asset_dir,
    shared_asset_path,
    special_template_keywords,
    stage_for_progress_column,
)
from n2d_contract_diff import diff_contracts  # noqa: E402  视觉契约继承 Diff 核心（common 层单一真值源）
from n2d_handoff import check_asset_handoff  # noqa: E402  逐镜资产交接 Diff（common 层单一真值源，与 inherit_contract 共用）
import image_backends  # noqa: E402  出图后端连通性探活 adapter（选择点→探针）
from n2d_platform_profiles import (  # noqa: E402
    backend_supports_three_plus_frames,
    video_backend_frame_control,
    video_backend_max_seconds,
)
from n2d_route import (  # noqa: E402
    is_done,
    is_progress_satisfied,
    manifest_path,
    parse_progress,
    voice_is_placeholder,
    voice_meta_path,
    voiceover_fingerprint,
)
from n2d_settings import get_setting, is_video_first  # noqa: E402
import semantic_continuity as semc  # noqa: E402
import state_continuity as statec  # noqa: E402
import multimodal_consistency as mmc  # noqa: E402
import subtitle_align as sa  # noqa: E402

BLOCK, WARN, INFO = "block", "warn", "info"
findings: List[Dict[str, object]] = []
FALLBACK_OFF_VALUES = {"", "无", "不使用", "关闭", "否", "off", "no", "none", "disable", "disabled"}


SPECIAL_SHOT_TEMPLATE_FIELDS: Dict[str, Tuple[str, ...]] = {
    "fight_exchange": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "attack_path", "impact_frame", "action_scope",
    ),
    "chase": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "screen_direction", "distance_curve", "obstacle_beats",
    ),
    "dialogue_shot_reverse": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "axis", "eyeline", "shot_pairing",
    ),
    "magic_burst": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "charge_frame", "release_frame", "effect_asset",
    ),
    "flight": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "pose_lock", "background_motion", "altitude_path",
    ),
    "intimate_interaction": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "contact_points", "distance_boundary", "body_overlap_limit",
    ),
    "hug_or_pull": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "contact_points", "force_direction", "body_overlap_limit", "release_frame",
    ),
    "multi_character_same_frame": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "character_slots", "face_priority", "overlap_rules",
    ),
    "ensemble_blocking": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "screen_positions", "focus_hierarchy", "crowd_simplification",
    ),
    "multi_person_blocking": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "screen_positions", "speaker_focus", "crowd_simplification",
    ),
}

# 专项镜头模板关键词从 common 派生（与 router.infer_shot_type 同一份 SHOT_TYPE_KEYWORDS，判型口径不再两边漂移）
SPECIAL_SHOT_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = special_template_keywords()

MOTION_CONTROL_KIND = MOTION_CONTROL_MANIFEST_KIND  # 从 n2d_contract 产物 kind 注册表取
# MOTION_CONTROL_REQUIRED_SHOT_TYPES / MOTION_CONTROL_RISK_FLAGS 从 n2d_contract 导入（与 router 同源）
MOTION_CONTROL_ROUTE_FIELDS = (
    "level",
    "required",
    "manifest_required",
    "manifest_path",
    "required_inputs",
    "backend_control_level",
    "failure_modes",
    "gate_policy",
    "degrade_allowed",
)
MOTION_CONTROL_READY_STATUSES = ("ready", "degrade_only")
MOTION_CONTROL_READY_INPUT_STATUSES = ("ready", "not_needed")
MOTION_CONTROL_CONTACT_FIELDS = ("contact_points", "occlusion_order", "body_part_ownership")

# IDENTITY_REGISTRY_KIND / IDENTITY_ADAPTER_MATRIX_KIND / IDENTITY_REFERENCE_FIELDS /
# IDENTITY_HANDLE_FIELDS 从 n2d_contract 导入（写方 lora/market/identity 同源）
IDENTITY_REFERENCE_FIELDS = IDENTITY_REFERENCE_KEYS
IDENTITY_FORM_FIELDS = (
    "form",
    "asset_key",
    "anchor_phrase",
    "reference_group",
    "identity_adapters",
    "angle_policy",
    "drift_forbidden",
)
IDENTITY_ANGLE_FIELDS = ("allowed", "risky", "requires_extra_reference")
IDENTITY_ADAPTER_SECTIONS = ("image", "video")
# 身份适配状态枚举从契约派生（与 n2d-identity 写入/校验、n2d-asset-market 重置同源，杜绝 gate 单边漂移）
from n2d_contract import (  # noqa: E402
    IDENTITY_ADAPTER_READY_STATUSES as IDENTITY_READY_STATUSES,
    IDENTITY_ADAPTER_KNOWN_STATUSES as IDENTITY_KNOWN_STATUSES,
)
# 后端→允许 mode 表从契约派生（与 n2d-identity 校验、n2d-asset-market 重置同源）
IDENTITY_ALLOWED_IMAGE_MODES = identity_allowed_modes(IDENTITY_IMAGE_ADAPTERS)
IDENTITY_ALLOWED_VIDEO_MODES = identity_allowed_modes(IDENTITY_VIDEO_ADAPTERS)

ASSET_REFERENCE_TYPE_PREFIX = {
    "scene": "LOC_",
    "location": "LOC_",
    "prop": "PROP_",
    "outfit": "OUTFIT_",
    "costume": "OUTFIT_",
    "vfx": "VFX_",
    "effect": "VFX_",
}
ASSET_REFERENCE_REQUIRED_FIELDS = ("id", "type", "name", "reference_group", "constraints", "drift_forbidden")
ASSET_PROP_REQUIRED_FIELDS = ("owner", "current_state", "lifecycle")
ASSET_SCENE_REQUIRED_FIELDS = ("spatial_layout",)

NATIVE_AUDIO_DISCARD = "discard"
NATIVE_AUDIO_AMBIENCE = "ambience"
NATIVE_AUDIO_KEEP = "keep"

COMPLIANCE_KIND = COMPLIANCE_MANIFEST_KIND
COMPLIANCE_READY = COMPLIANCE_READY_STATUSES
COMPLIANCE_DONE = COMPLIANCE_DONE_STATUSES
PLATFORM_REVIEW_STATUSES = COMPLIANCE_PLATFORM_REVIEW_STATUSES
PRE_BROADCAST_STATUSES = COMPLIANCE_PRE_BROADCAST_STATUSES
STATUS_LIKE_VALUES = COMPLIANCE_STATUS_LIKE_VALUES
OVERSEAS_PLATFORMS = COMPLIANCE_OVERSEAS_PLATFORMS
DOMESTIC_REGIONS = COMPLIANCE_DOMESTIC_REGIONS


def gate_family(stage: str) -> str:
    """Map explicit preflight stages to the production stage they validate."""
    return {
        "image_preflight": "image",
        "video_preflight": "video",
    }.get(stage, stage)


def add(sev: str, dim: str, loc: str, msg: str, **extra: object) -> None:
    item: Dict[str, object] = {"sev": sev, "dim": dim, "loc": loc, "msg": msg}
    item.update(extra)
    findings.append(item)


def exists(path: str) -> bool:
    return os.path.exists(path)


def load_json(path: str):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None


CHARACTER_ID_RE = re.compile(r"\bCHAR_\d{2,}\b")
ASSET_ID_RE = re.compile(r"\b(?:LOC|PROP|OUTFIT|VFX)_\d{2,}\b")


def _episode_reference_texts(root: str, ep: str) -> Iterable[str]:
    """Text surfaces that define the current episode's registry references."""
    roots = [
        os.path.join(root, "脚本", ep),
        os.path.join(root, "出图", ep, "prompt"),
        os.path.join(root, "出视频", ep, "prompt"),
    ]
    for base in roots:
        if not os.path.isdir(base):
            continue
        for pattern in ("*.md", "*.json", "*.txt"):
            for path in sorted(glob.glob(os.path.join(base, pattern))):
                try:
                    with open(path, encoding="utf-8") as fh:
                        yield fh.read()
                except Exception:
                    continue


def episode_registry_reference_ids(root: str, ep: str) -> Tuple[set, set]:
    """Return character and non-character registry ids used by one episode.

    The registries can contain planned future characters/assets. A stage gate for
    第N集 should validate registry schemas globally, but strict reference image
    existence only for ids this episode actually consumes.
    """
    text = "\n".join(_episode_reference_texts(root, ep))
    return set(CHARACTER_ID_RE.findall(text)), set(ASSET_ID_RE.findall(text))


MIDFRAME_SELF_CHECK_KEYS = ("self_check", "midframe_self_check", "prompt_self_check")
MIDFRAME_SELF_CHECK_PASS = {"pass", "passed", "ok", "true", "yes", "1", "✅", "通过"}
PROHIBITED_FACE_PATCH_LABEL = "本地贴脸修复产物禁用"
PROHIBITED_FACE_PATCH_STRONG_TOKENS = (
    "local_face_patch",
    "face_patch",
    "face-patch",
    "facepaste",
    "face_paste",
    "face paste",
    "faceswap",
    "face_swap",
    "face-swap",
    "facefix",
    "face_fix",
    "inswapper",
    "facefusion",
    "roop",
)
PROHIBITED_FACE_PATCH_OPERATION_TOKENS = (
    "crop_resize_color_match",
    "alpha_blend",
    "poisson_clone",
    "seamless_clone",
)


def _production_events_path(root: str) -> str:
    return os.path.join(root, "生产数据", "production_events.jsonl")


def _norm_rel_path(path: str) -> str:
    return os.path.normpath(str(path).strip()).replace(os.sep, "/")


def _asset_matches(root: str, asset: object, target_rel: str) -> bool:
    if not asset:
        return False
    asset_s = str(asset).strip()
    target_rel_norm = _norm_rel_path(target_rel)
    target_abs = os.path.abspath(target_rel if os.path.isabs(target_rel) else os.path.join(root, target_rel))
    if os.path.isabs(asset_s):
        return os.path.abspath(asset_s) == target_abs
    return _norm_rel_path(asset_s) == target_rel_norm or os.path.abspath(os.path.join(root, asset_s)) == target_abs


def _load_production_events(root: str) -> List[Dict[str, Any]]:
    path = _production_events_path(root)
    if not os.path.isfile(path):
        return []
    events: List[Dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                if isinstance(item, dict):
                    events.append(item)
    except Exception:
        return []
    return events


def _latest_asset_generation_event(root: str, ep: str, asset_rel: str) -> Optional[Dict[str, Any]]:
    latest: Optional[Dict[str, Any]] = None
    for event in _load_production_events(root):
        if str(event.get("episode") or "").strip() != ep:
            continue
        if str(event.get("stage") or "").strip() != "image":
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        generation = event.get("generation") if isinstance(event.get("generation"), dict) else {}
        if _asset_matches(root, generation.get("asset") or event.get("asset"), asset_rel):
            latest = event
    return latest


def _event_generation(event: Dict[str, Any]) -> Dict[str, Any]:
    return event.get("generation") if isinstance(event.get("generation"), dict) else {}


def _event_meta(event: Dict[str, Any]) -> Dict[str, Any]:
    return event.get("meta") if isinstance(event.get("meta"), dict) else {}


def _event_cost(event: Dict[str, Any]) -> Dict[str, Any]:
    return event.get("cost") if isinstance(event.get("cost"), dict) else {}


def _event_asset_rel(root: str, event: Dict[str, Any]) -> Optional[str]:
    generation = _event_generation(event)
    asset = generation.get("asset") or event.get("asset")
    if not asset:
        return None
    raw = str(asset).strip()
    if not raw:
        return None
    if os.path.isabs(raw):
        try:
            return os.path.relpath(os.path.abspath(raw), os.path.abspath(root)).replace(os.sep, "/")
        except Exception:
            return raw.replace(os.sep, "/")
    return _norm_rel_path(raw)


def _is_prohibited_face_patch_event(event: Dict[str, Any]) -> bool:
    generation = _event_generation(event)
    meta = _event_meta(event)
    cost = _event_cost(event)
    fields = [
        event.get("provider"),
        event.get("source"),
        event.get("method"),
        cost.get("provider"),
        cost.get("method"),
        generation.get("provider"),
        generation.get("method"),
        generation.get("redraw_category"),
        generation.get("redraw_reason"),
        meta.get("provider"),
        meta.get("method"),
    ]
    text = " ".join(str(v) for v in fields if v is not None).lower()
    if any(token in text for token in PROHIBITED_FACE_PATCH_STRONG_TOKENS):
        return True
    return ("face" in text or "脸" in text) and any(
        token in text for token in PROHIBITED_FACE_PATCH_OPERATION_TOKENS
    )


def _prohibited_face_patch_outputs(root: str, ep: str) -> List[Dict[str, Any]]:
    latest: Dict[str, tuple[int, Dict[str, Any]]] = {}
    for idx, event in enumerate(_load_production_events(root), start=1):
        if str(event.get("episode") or "").strip() != ep:
            continue
        if str(event.get("stage") or "").strip() != "image":
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        rel = _event_asset_rel(root, event)
        if rel and rel.endswith(".png"):
            latest[rel] = (idx, event)

    out: List[Dict[str, Any]] = []
    for rel, (line_no, event) in latest.items():
        if not _is_prohibited_face_patch_event(event):
            continue
        generation = _event_generation(event)
        meta = _event_meta(event)
        cost = _event_cost(event)
        out.append({
            "png": rel,
            "line": line_no,
            "provider": str(cost.get("provider") or generation.get("provider") or event.get("provider") or event.get("source") or ""),
            "method": str(meta.get("method") or generation.get("method") or cost.get("method") or event.get("method") or ""),
        })
    return sorted(out, key=lambda r: str(r.get("png") or ""))


def _midframe_self_check_value(event: Dict[str, Any]) -> str:
    meta = event.get("meta") if isinstance(event.get("meta"), dict) else {}
    for key in MIDFRAME_SELF_CHECK_KEYS:
        value = str(meta.get(key) or "").strip()
        if value:
            return value
    return ""


def _check_midframe_generation_self_check(root: str, ep: str, rel_png: str, loc: str, idx: int) -> None:
    """A declared midframe may exist on disk but still be a bad anchor.

    The visual judgment is human/agent-side, but the gate can make that judgment
    auditable: every landed `_mid` / anchor must have a latest image generation
    ledger event with status=pass and self_check=pass.
    """
    event = _latest_asset_generation_event(root, ep, rel_png)
    if event is None:
        add(BLOCK, "中段锚帧", loc,
            f"锚帧 {idx} PNG 已存在但缺中段动作自检 pass 记账：{rel_png}；"
            "落档后必须记录 image generation --status pass --meta self_check=pass，"
            "确认它不是只锁人锁景，而是姿态/动作确实落在首尾帧中间。")
        return
    generation = event.get("generation") if isinstance(event.get("generation"), dict) else {}
    status = str(generation.get("status") or event.get("status") or "").strip().lower()
    if status != "pass":
        add(BLOCK, "中段锚帧", loc,
            f"锚帧 {idx} 最近一次生成记录不是 pass（status={status or '缺失'}）：{rel_png}；"
            "先重抽或重新自检并记录 self_check=pass。")
        return
    self_check = _midframe_self_check_value(event)
    if self_check.lower() not in MIDFRAME_SELF_CHECK_PASS:
        add(BLOCK, "中段锚帧", loc,
            f"锚帧 {idx} 缺少通过值 self_check=pass（当前={self_check or '缺失'}）：{rel_png}；"
            "中段锚帧必须按本镜「中段锚帧生成方式/自检」确认动作推进成立，不能只凭 PNG 存在放行。")


def compliance_manifest_path(root: str) -> str:
    return os.path.join(root, "合规", "compliance_manifest.json")


def _listify(value) -> List:
    return value if isinstance(value, list) else []


def _status(value) -> str:
    return str(value or "").strip()


PLACEHOLDER_MARKERS = COMPLIANCE_PLACEHOLDER_MARKERS


def _filled(value) -> bool:
    text = _status(value)
    if not text:
        return False
    lower = text.lower()
    if lower in {"xxx", "xx", "x", "...", "n/a?"}:
        return False
    return not any(marker in lower for marker in PLACEHOLDER_MARKERS)


def _looks_like_status_value(value) -> bool:
    return _status(value).lower() in STATUS_LIKE_VALUES


def _valid_iso_date(value) -> bool:
    try:
        dt.date.fromisoformat(_status(value))
        return True
    except ValueError:
        return False


def _has_embedded_iso_date(value) -> bool:
    match = re.search(r"\d{4}-\d{2}-\d{2}", _status(value))
    if not match:
        return False
    try:
        dt.date.fromisoformat(match.group(0))
        return True
    except ValueError:
        return False


def _is_internal_distribution(data: dict) -> bool:
    """内部 demo（不投放）判定——与 n2d-compliance/scripts/compliance.py 同源：
    只认契约常量 COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS，不再各自维护口语别名。"""
    return _status(data.get("distribution_intent")).lower() in COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS


def _is_publish_intent(data: dict) -> bool:
    return not _is_internal_distribution(data)


# internal_only 免检范围 = 契约 COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS（platform_review / overseas_localization）：
# 这些字段域的 BLOCK 降为 INFO 并加注，角色/声音授权照常 BLOCK。
INTERNAL_SKIP_NOTE = "（内部 demo 免检，转投放前需补）"


def _compliance_block(loc: str, msg: str) -> None:
    add(BLOCK, "合规前置", loc, msg)


def _compliance_warn(loc: str, msg: str) -> None:
    add(WARN, "合规前置", loc, msg)


def _episode_in_scope(ep: str, value) -> bool:
    if value in (None, "", [], "all", "全剧"):
        return True
    if isinstance(value, list):
        return ep in value or "all" in value or "全剧" in value
    return str(value).strip() in (ep, "all", "全剧")


def _identity_character_ids(root: str) -> List[str]:
    data = load_json(identity_registry_path(root))
    if not isinstance(data, dict):
        return []
    ids = []
    for char in data.get("characters", []) or []:
        if isinstance(char, dict) and _status(char.get("id")):
            ids.append(_status(char.get("id")))
    return ids


def _check_compliance_rights(root: str, data: dict, loc: str) -> None:
    rights = data.get("rights")
    if not isinstance(rights, dict):
        _compliance_block(loc, "缺 rights；源小说/改编权/素材版权必须在出图前落合规包")
        return
    source = rights.get("source_text")
    if not isinstance(source, dict):
        _compliance_block(f"{loc} rights.source_text", "缺 source_text 权利来源；必须是 original/public_domain/licensed/user_declared 之一")
    else:
        status = _status(source.get("status"))
        if status not in COMPLIANCE_ALLOWED_RIGHTS or status in ("unknown", ""):
            _compliance_block(f"{loc} rights.source_text", f"源文本权利状态不可用：{status or 'missing'}")
        if status in COMPLIANCE_RIGHTS_EVIDENCE_REQUIRED and not _filled(source.get("evidence")):
            _compliance_block(f"{loc} rights.source_text", "licensed/stock_licensed/user_declared 必须填写 evidence/ref，不能只口头说已授权")

    for key in ("adaptation", "music_bgm", "sfx", "fonts"):
        item = rights.get(key)
        if not isinstance(item, dict):
            _compliance_block(f"{loc} rights.{key}", f"缺 {key} 权利状态；不用也要写 not_applicable，不能空着")
            continue
        status = _status(item.get("status"))
        if not status or status not in COMPLIANCE_ALLOWED_RIGHTS:
            _compliance_block(f"{loc} rights.{key}", f"{key} 权利状态未知：{status or 'missing'}")
        if status in COMPLIANCE_RIGHTS_EVIDENCE_REQUIRED and not _filled(item.get("evidence")):
            _compliance_block(f"{loc} rights.{key}", f"{key} 标为 {status} 但缺 evidence/ref")


def _check_compliance_characters(root: str, data: dict, loc: str) -> None:
    section = data.get("character_likeness")
    if not isinstance(section, dict):
        _compliance_block(loc, "缺 character_likeness；角色形象/真人肖像授权必须在出图前落合规包")
        return
    entries = _listify(section.get("characters"))
    by_id = {str(item.get("character_id")): item for item in entries if isinstance(item, dict) and item.get("character_id")}
    for char_id in _identity_character_ids(root):
        if char_id not in by_id:
            _compliance_block(f"{loc} character_likeness", f"identity_registry 中角色 {char_id} 缺肖像/角色授权记录")
    for idx, item in enumerate(entries, 1):
        if not isinstance(item, dict):
            _compliance_block(f"{loc} character_likeness.characters[{idx}]", "角色授权记录必须是对象")
            continue
        status = _status(item.get("status"))
        iloc = f"{loc} character_likeness.{item.get('character_id', idx)}"
        if status in COMPLIANCE_BLOCKED_CHARACTER or status not in COMPLIANCE_APPROVED_CHARACTER:
            _compliance_block(iloc, f"角色/肖像授权状态不可放行：{status or 'missing'}")
        if status in ("actor_authorized", "self_authorized", "licensed_likeness") and not _filled(item.get("evidence")):
            _compliance_block(iloc, "真人/演员/授权形象必须填写授权 evidence/ref")


def _check_compliance_voice(data: dict, loc: str) -> None:
    section = data.get("voice")
    if not isinstance(section, dict):
        _compliance_block(loc, "缺 voice；声音克隆/参考音授权必须在配音和出视频前落合规包")
        return
    status = _status(section.get("status"))
    if status not in COMPLIANCE_SAFE_VOICE:
        _compliance_block(f"{loc} voice", f"声音授权状态不可放行：{status or 'missing'}")
    if section.get("uses_voice_clone") is True or status == "authorized_clone":
        auth = _status(section.get("authorization_status"))
        if auth != "approved":
            _compliance_block(f"{loc} voice", "使用声音克隆/参考音时 authorization_status 必须是 approved")
        if not _filled(section.get("evidence")):
            _compliance_block(f"{loc} voice", "声音克隆/参考音授权缺 evidence/ref")


def _check_platform_targets(data: dict, loc: str, stage: str) -> None:
    if stage not in ("compose", "review"):
        return
    internal = _is_internal_distribution(data)

    def flag(floc: str, msg: str) -> None:
        # platform_review / overseas_localization ∈ COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS：
        # internal_only 时降 BLOCK → INFO；其余（角色/声音授权）不走本函数、照常 BLOCK。
        if internal:
            add(INFO, "合规前置", floc, f"{msg}{INTERNAL_SKIP_NOTE}")
        else:
            _compliance_block(floc, msg)

    if internal:
        _compliance_warn(
            loc,
            "distribution_intent=internal_only；"
            f"{' / '.join(COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS)} 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放",
        )
    targets = _listify((data.get("platform_review") or {}).get("targets"))
    if not targets:
        flag(f"{loc} platform_review", "发布候选缺 platform_review.targets；目标平台审核必须在合成前确定")
        return
    localization = data.get("localization") if isinstance(data.get("localization"), dict) else {}
    for idx, target in enumerate(targets, 1):
        if not isinstance(target, dict):
            flag(f"{loc} platform_review.targets[{idx}]", "平台审核项必须是对象")
            continue
        platform = _status(target.get("platform"))
        tloc = f"{loc} platform_review.{platform or idx}"
        for key in ("platform", "region", "policy_profile", "profile_checked_at", "copyright_review", "content_rating_review"):
            if not _filled(target.get(key)):
                flag(tloc, f"平台审核缺字段：{key}")
        for key in ("platform", "region"):
            if _filled(target.get(key)) and _looks_like_status_value(target.get(key)):
                flag(tloc, f"{key} 必须是具体平台/地区，不能写状态占位：{_status(target.get(key))}")
        if _filled(target.get("policy_profile")) and not _has_embedded_iso_date(target.get("policy_profile")):
            flag(tloc, "policy_profile 必须带 YYYY-MM-DD 检查日期，例如 douyin_policy_2026-06-08")
        if _filled(target.get("profile_checked_at")) and not _valid_iso_date(target.get("profile_checked_at")):
            flag(tloc, "profile_checked_at 必须是 YYYY-MM-DD")
        for key in ("copyright_review", "content_rating_review"):
            if _status(target.get(key)) not in PLATFORM_REVIEW_STATUSES:
                flag(tloc, f"{key} 必须 ready/done/not_applicable")
        region = _status(target.get("region")).lower()
        overseas = target.get("requires_localization") is True or platform.lower() in OVERSEAS_PLATFORMS or (region and region not in DOMESTIC_REGIONS)
        if overseas:
            if _status(localization.get("status")) not in ("ready", "done"):
                flag(f"{loc} localization", f"{platform or '海外平台'} 目标需要出海本地化；localization.status 必须 ready/done")
            languages = set(str(x).lower() for x in _listify(localization.get("subtitle_languages")))
            required = _status(target.get("language")).lower()
            if required and required not in languages:
                flag(f"{loc} localization", f"目标语言 {required} 不在 subtitle_languages 中")


def _check_regulatory_filing(data: dict, loc: str, stage: str) -> None:
    """广电总局 网络微短剧 备案/分级/播前审核（2026 新规：AIGC 全面纳入分级+播前审核）。
    与 platform_review 同列内部 demo 免检域：internal_only 时 BLOCK 降 INFO。"""
    if stage not in ("compose", "review"):
        return
    internal = _is_internal_distribution(data)

    def flag(floc: str, msg: str) -> None:
        if internal:
            add(INFO, "合规前置", floc, f"{msg}{INTERNAL_SKIP_NOTE}")
        else:
            _compliance_block(floc, msg)

    reg = data.get("regulatory_filing")
    if not isinstance(reg, dict):
        flag(f"{loc} regulatory_filing", "缺 regulatory_filing；境内投放须先过广电备案/分级/播前审核（2026 新规）")
        return
    if reg.get("applicable") is False:
        if not _filled(reg.get("notes")):
            flag(f"{loc} regulatory_filing", "applicable=false 须在 notes 写明理由（纯海外/内部预览等）")
        return
    pbr = _status(reg.get("pre_broadcast_review"))
    if pbr and pbr not in PRE_BROADCAST_STATUSES:
        flag(f"{loc} regulatory_filing", f"pre_broadcast_review 须为 {'/'.join(sorted(PRE_BROADCAST_STATUSES))}；got {pbr}")
    if pbr in ("", "pending"):
        flag(f"{loc} regulatory_filing", "pre_broadcast_review 不能停在 pending（境内投放须先过播前审核）")
    elif stage == "review" and pbr not in COMPLIANCE_DONE:
        flag(f"{loc} regulatory_filing", "pre_broadcast_review 须 done 才能过 review")
    paid = _status(data.get("distribution_intent")) == "paid_distribution"
    if (paid or stage == "review") and not _filled(reg.get("release_filing_no")):
        flag(f"{loc} regulatory_filing", "release_filing_no（上线备案号）付费投放/review 前必填，不能留 TODO 占位")
    if _filled(reg.get("filed_at")) and not _valid_iso_date(reg.get("filed_at")):
        flag(f"{loc} regulatory_filing", "filed_at 须为 YYYY-MM-DD")


def check_compliance_manifest(root: str, ep: str, stage: str) -> None:
    """Front-load rights, character/voice authorization, platform and localization gates.

    (AI 标识/水印/AI 披露 不再由本流水线强制——已于 2026-06 下线，合规义务移到工具之外处理。)
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


def row_for(root: str, ep: str) -> Tuple[List[str], Optional[Dict[str, str]]]:
    try:
        header, rows = parse_progress(root)
    except Exception as e:
        add(BLOCK, "进度", os.path.join(root, "_进度.md"), f"进度表不可解析：{e}")
        return [], None
    row = next((r for r in rows if r.get("_ep") == ep), None)
    if row is None:
        add(BLOCK, "进度", os.path.join(root, "_进度.md"), f"{ep} 不在进度表")
    return header, row


def require_progress(root: str, ep: str, cols: Iterable[str]) -> None:
    header, row = row_for(root, ep)
    if row is None:
        return
    for col in cols:
        if col not in header:
            add(BLOCK, "进度", os.path.join(root, "_进度.md"), f"缺进度列：{col}")
        elif not is_progress_satisfied(root, row, col):
            add(BLOCK, "进度", os.path.join(root, "_进度.md"), f"{ep}「{col}」未完成（当前 {row.get(col, '⬜')}）")


def _artifact_exists(root: str, ep: str, rel: str) -> bool:
    return os.path.exists(os.path.join(root, str(rel).format(ep=ep)))


def check_progress_artifact_signoff(root: str, ep: str, cols: Iterable[str]) -> None:
    """文本×产物双签：被判 ✅ 的列，用 STAGE_GRAPH 的 output_contract/outputs 验关键产物真在磁盘。

    `require_progress` 只信 `_进度.md` 单元格 ✅，手改进度把"配音 ✅"写上但实际没产 时长清单 也放行。
    本检查把"单一真相"从纯文本升级为"文本+产物双签"：✅ 但关键产物缺 → BLOCK，回退对应阶段。
    """
    header, row = row_for(root, ep)
    if row is None:
        return
    for col in cols:
        if col not in header or not is_done(row.get(col, "")):
            continue  # 未完成的列由 require_progress 负责，这里只验已判 ✅ 的
        spec = stage_for_progress_column(col)
        if not spec:
            continue
        loc = os.path.join(root, "_进度.md")
        oc = spec.get("output_contract")
        if isinstance(oc, dict) and oc.get("any_of"):
            variants = [v for v in oc["any_of"] if isinstance(v, dict)]
            if not any(all(_artifact_exists(root, ep, a) for a in v.get("all_of", ())) for v in variants):
                labels = " 或 ".join(str(v.get("label", "")) for v in variants)
                add(BLOCK, "产物签收", loc,
                    f"{ep}「{col}」标 ✅ 但关键产物缺失（需满足其一：{labels}）——文本与产物背离，补产物或修进度",
                    return_to_stage=spec.get("return_to_stage"))
        else:
            outs = spec.get("outputs") or ()
            if outs and not any(_artifact_exists(root, ep, a) for a in outs):
                add(BLOCK, "产物签收", loc,
                    f"{ep}「{col}」标 ✅ 但「{spec.get('label')}」产物一个都不在磁盘（如 {str(outs[0]).format(ep=ep)}）"
                    f"——幻影完成，补产物或修进度", return_to_stage=spec.get("return_to_stage"))


def progress_fraction_done(root: str, ep: str, col: str) -> bool:
    _, row = row_for(root, ep)
    if not row:
        return False
    return is_done(row.get(col, ""))


def check_placeholder_policy(root: str, ep: str, stage: str) -> None:
    if is_native_av_production(root):
        # 原生音画：说话镜由视频后端一次出同步音画，不靠配音时长；占位/缺配音不作硬闸。
        return
    ph = voice_is_placeholder(root, ep)
    if ph is None:
        if stage in {"image", "video", "compose"}:
            add(BLOCK, "配音", ep, "未找到可判定的时长清单；无法确认真实配音或 rough timing，先跑 n2d-voice 生成 `时长清单.json`")
        else:
            add(WARN, "配音", ep, "未找到可判定的占位字段；若尚未配音，下游应先补齐")
        return
    if not ph:
        return
    if stage == "image" and is_video_first(root):
        add(WARN, "配音", ep, "当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时")
    elif stage == "video" and is_video_first(root):
        add(WARN, "配音", ep, "先出视频后配音模式已放行占位时长进入出视频；后期补真音可能需要重出视频")
    else:
        add(BLOCK, "配音", ep, "配音仍为占位音色；`配音先行` 模式下该阶段不应继续，先 n2d-voice 换真实配音并重定时")


def check_voiceover_fingerprint(root: str, ep: str) -> None:
    """配音定稿后 voiceover.txt 又被改词/插句/删句 → 时长清单/字幕/镜头时长全部过期。

    `validate_timings` 在 n2d-script 阶段2收尾抓这条失配链，但 image/video preflight 此前不复查指纹——
    定稿后裸改台词，下游照常据过期时长出图出视频导致音画错位。这里把同一指纹比对前移到付费阶段闸门。
    原生音画模式镜头时长不依赖配音时长清单，跳过。
    """
    if is_native_av_production(root):
        return
    vo_p = os.path.join(root, "脚本", ep, "voiceover.txt")
    if not os.path.isfile(vo_p):
        return  # 无 voiceover：上游问题，require_progress/其它检查覆盖
    meta_p = voice_meta_path(root, ep)
    if not meta_p:
        # 占位轨/旧产物无指纹 sidecar：仅当配音非占位时温和提示（占位由 check_placeholder_policy 管）
        if voice_is_placeholder(root, ep) is False:
            add(WARN, "配音", vo_p, "无 时长清单.meta.json（旧配音产物）——无法核对配音后 voiceover 是否被改，建议重跑 n2d-voice 生成指纹")
        return
    recorded = (load_json(meta_p) or {}).get("voiceover_fingerprint")
    current = voiceover_fingerprint(vo_p)
    if recorded and current and recorded != current:
        add(
            BLOCK,
            "配音",
            vo_p,
            "voiceover.txt 在配音后被改动（台词指纹失配）→ 时长清单/字幕/镜头时长已过期；重跑 n2d-voice 再回跑 n2d-script 阶段2，过 gate 再出图/出视频",
            return_to_stage="voice",
            rerun_scope="重跑 n2d-voice 生成新时长清单 → 回跑 finalize_storyboard 重定镜头时长/字幕 → 再出图出视频。",
            affected_artifacts=[
                f"合成/{ep}/配音/时长清单.json",
                f"脚本/{ep}/storyboard.json",
                f"脚本/{ep}/字幕中.srt",
            ],
        )


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


def check_backend_reachable(root: str, ep: str) -> None:
    """付费出图前确认所选生图后端「能落 PNG」。

    SKILL.md 写了「确认能落 PNG 再开工」，但此前无确定性闸门兜底——后端不通（内网 502 /
    CLI 未登录 / 缺 API key）时照样进付费工位，要么白花钱碰壁，要么静默兜底换后端致漂移。
    探针口径走 adapter（image_backends），gate 不 hardcode 任何内网地址/CLI 细节：
      · down（探针确证不可达）→ BLOCK，且明确禁止静默兜底换后端；
      · unknown（无自动探针 / CLI 缺 / 已设 N2D_SKIP_BACKEND_PROBE）→ WARN，提示人工确认；
      · ok → 放行。
    """
    settings_loc = os.path.join(root, "_设置.md")
    setting = get_setting(root, "生图AI", "Codex").strip()
    status, detail = image_backends.probe_backend(setting)
    if status == "down":
        add(BLOCK, "生图后端连通性", settings_loc,
            f"生图后端「{setting}」探活不通：{detail}。出图是付费工位，不通就停——"
            "先修后端（验内网/重登 CLI/补 API key）再出图；禁止静默兜底换别的后端（会引入跨镜后端混用漂移）。",
            return_to_stage="image")
    elif status == "unknown":
        add(WARN, "生图后端连通性", settings_loc,
            f"生图后端「{setting}」无法自动探活：{detail}。出图前请人工确认它能落 PNG"
            "（如 curl 内网健康端点 / 确认即梦官方 CLI 已登录·会员有效 / 确认 API 额度），不通即停，勿静默兜底换后端。")


def drift_advisory_findings(report: Dict[str, Any]) -> List[Tuple[str, str, str, str]]:
    """drift-risk report → [(sev, dim, loc, msg)]（high→WARN·medium→INFO，只取 high/medium）。

    纯函数·可测：不读盘、不 add()，方便单测。face/asset 两种 report 同形（characters/assets +
    band/score/tier/suggestions），统一处理。advisory：绝不 BLOCK——出图前预案，落档闸是 image_qc。"""
    items = report.get("characters") or report.get("assets") or []
    is_face = report.get("kind") == "n2d_face_drift_risk"
    dim = "脸漂预案" if is_face else "物料漂移预案"
    label = "脸漂" if is_face else "物料漂移"
    out: List[Tuple[str, str, str, str]] = []
    for r in items:
        band = r.get("band")
        if band not in ("high", "medium"):
            continue
        sev = WARN if band == "high" else INFO
        rid = r.get("character_id") or r.get("id") or ""
        name = r.get("name") or rid
        tip = (r.get("suggestions") or [""])[0]
        tier = r.get("tier") or r.get("scope") or ""
        out.append((sev, dim, f"{name}（{rid}）",
                    f"本集{label}风险 {band}（分{r.get('score')}{'·'+str(tier) if tier else ''}）：{tip}"))
    return out


def _run_drift_risk_script(script_name: str, root: str, ep: str) -> Optional[Dict[str, Any]]:
    """跑 n2d-image 的 face/asset_drift_risk.py（--json），拿机器报告。跑不起来→None（交由调用方降级 INFO）。"""
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                          "n2d-image", "scripts", script_name)
    if not os.path.exists(script):
        return None
    try:
        out = subprocess.check_output([sys.executable, script, root, ep, "--json"],
                                      text=True, stderr=subprocess.DEVNULL, timeout=90)
        return json.loads(out)
    except Exception:
        return None


def check_drift_risk_advisories(root: str, ep: str) -> None:
    """image_preflight 专属：自动跑 face/asset drift_risk 预案，把 high/medium 内联进同一份预检报告。

    动机（E1·让 agent 跑得更顺）：脸漂/物料漂移预案此前是两个独立、要 agent **记得手动跑**的脚本，
    输出又各自落单独 JSON——agent 跑一次 gate 拿 block、还得另记两条 advisory。这里把它们折进
    image_preflight：一个入口 = 阻断 + 预案一次拿齐。advisory only（WARN/INFO），绝不阻断出图。"""
    for script_name, human in (("face_drift_risk.py", "脸漂"), ("asset_drift_risk.py", "物料漂移")):
        report = _run_drift_risk_script(script_name, root, ep)
        if report is None:
            add(INFO, "漂移预案", ep,
                f"{human}风险预案未能自动生成（缺 storyboard/registry 或脚本不可用）——"
                f"出图前可手动跑 skills/n2d-image/scripts/{script_name} 看预案。")
            continue
        rows = drift_advisory_findings(report)
        if not rows:
            add(INFO, "漂移预案", ep, f"{human}风险预案：本集无 high/医 medium 角色/物料（🟢 全低危）。")
            continue
        for sev, dim, loc, msg in rows:
            add(sev, dim, loc, msg, advisory=True)


def check_contract_inheritance(root: str, ep: str) -> None:
    """像素层视觉契约 出图→出视频 继承 Diff，逐字段机检（光位锚/轴线视线漂移=BLOCK）。

    这是唯一能抓「人工誊抄改写轴线/光位」的机检；此前只存在于 inherit_contract.py 的裸命令、
    游离在 gate 退出码之外，导致 `dashboard.py gate --stage video` 通过 ≠ 契约继承成立。
    接进 video_preflight/video gate 后，视频侧改写/丢失像素层五字段会被硬拦，并消费 contract_inheritance 维度的回退坐标。
    """
    img_p = os.path.join(root, "出图", ep, "prompt", "00_总览.md")
    vid_p = os.path.join(root, "出视频", ep, "prompt", "00_总览.md")
    if not os.path.isfile(img_p):
        return  # 出图总览缺：上游问题，image_preflight/image gate 负责，不在此重复 BLOCK
    if not os.path.isfile(vid_p):
        return  # 视频总览缺：check_video_prompt_overview 已 BLOCK，避免重复报
    dim = CONSISTENCY_DIMENSIONS["contract_inheritance"]
    for r in diff_contracts(open(img_p, encoding="utf-8").read(), open(vid_p, encoding="utf-8").read()):
        if r["severity"] == "block":
            add(
                BLOCK,
                "契约继承",
                vid_p,
                f"视觉契约继承漂移[{r['field']}]：{r['note']}（出图侧原文：{r['image_text'] or '缺'}）",
                return_to_stage=dim["return_to_stage"],
                rerun_scope=dim["scope"],
                affected_artifacts=[f"出视频/{ep}/prompt/00_总览.md"],
            )
        elif r["status"] == "warn_drift":
            add(WARN, "契约继承", vid_p, f"视觉契约继承提示[{r['field']}]：{r['note']}（出图侧：{r['image_text'] or '缺'}）")


def check_asset_handoff_inheritance(root: str, ep: str) -> None:
    """逐镜物料约束 出图→出视频 继承（LOC/PROP/OUTFIT/VFX）：出图绑定的资产在出视频对应镜
    丢失=block/warn。视觉契约五字段管 episode 级光位/轴线，本检查补**逐镜**资产锚。

    此前只在 inherit_contract.py 裸命令里跑，游离在 gate 退出码之外——`dashboard.py gate --stage video`
    通过 ≠ 资产逐镜交接成立。接进 video gate 后，出图逐镜 prompt 绑的道具/特效在视频侧被丢会被收口。
    （身份交接逐镜锁则由 check_route_identity_readiness / 近景身份锁负责，不在此重复报。）
    """
    res = check_asset_handoff(root, ep)
    if not res.get("available"):
        return  # 上游逐镜 prompt 未到位：image/video 各自 stage gate 负责，不在此重复 BLOCK
    dim = CONSISTENCY_DIMENSIONS["contract_inheritance"]
    vid_rel = res.get("video_clips_file", os.path.join("出视频", ep, "prompt", "01_clips.md"))
    vid_p = os.path.join(root, vid_rel)
    for f in res.get("findings", []):
        if f.get("severity") == "block":
            add(
                BLOCK,
                "契约继承",
                vid_p,
                f"资产逐镜交接[{f.get('code')}]：{f.get('note')}",
                return_to_stage=dim["return_to_stage"],
                rerun_scope=dim["scope"],
                affected_artifacts=[vid_rel],
            )
        else:
            add(WARN, "契约继承", vid_p, f"资产逐镜交接[{f.get('code')}]：{f.get('note')}")


def check_image_ai_policy(root: str, ep: str) -> None:
    """阶段2：`生图AI` 是选择点（默认 Codex），放行官方/已登录多参考后端，只拦混用 + 未授权出图。

    跨镜一致性真正的杀手是【同项目混用多个生图后端】，不是"用了非 Codex"。本检查：
      - 官方白名单后端（Codex/OpenAI/Dreamina/即梦官方 CLI/Seedream/可灵主体库/Nano Banana/Sora Cameo）：放行；
      - 未授权出图路径（同视频AI 含糊口径、第三方逆向 CLI/web 自动化）：BLOCK（安全 invariant）；
      - 未知后端：WARN（提示先确认是官方 API）；
      - 同项目/同集出现 ≥2 个不同官方后端：BLOCK（混用）。
    合规闸门（角色/声音克隆授权）由 check_compliance_manifest 负责，与本检查无关。
    """
    settings_loc = os.path.join(root, "_设置.md")
    used: set = set()  # 在用的官方后端 canonical 集合，用于混用检测

    setting = get_setting(root, "生图AI", "Codex").strip()
    canon, kind = classify_image_backend(setting)
    if kind == "forbidden":
        add(
            BLOCK,
            "生图AI一致性",
            settings_loc,
            f"生图AI「{setting}」是未授权/含糊出图路径（同视频AI、第三方逆向 CLI 或 web 自动化），违反安全闸门，永不放行。"
            "请显式改用官方后端：Codex/OpenAI、Dreamina/即梦官方 CLI、Seedream（官方 API）、可灵主体库、Nano Banana、Sora Cameo。",
        )
    elif kind == "unknown":
        add(
            WARN,
            "生图AI一致性",
            settings_loc,
            f"生图AI「{setting}」不在已知官方后端清单内。请先确认它是【官方 API】再用；"
            "已知官方后端：" + "、".join(cfg["label"] for cfg in APPROVED_IMAGE_BACKENDS.values()) + "。",
        )
    else:
        used.add(canon)

    prompt_paths = [
        os.path.join(root, "出图", ep, "prompt", "00_总览.md"),
        os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md"),
        shared_asset_path(root, "prompt", "角色定妆.md"),
        shared_asset_path(root, "prompt", "场景定妆.md"),
        shared_asset_path(root, "prompt", "道具定妆.md"),
        shared_asset_path(root, "prompt", "法宝定妆.md"),
        shared_asset_path(root, "prompt", "特效定妆.md"),
    ]
    backend_decl_re = re.compile(
        r"(?:生图AI|图像后端|图片后端|image backend|image model)\s*[:：]\s*([^\n\r`|]+)",
        re.I,
    )
    forbidden_call_re = re.compile(r"(同视频AI|非官方|第三方|逆向|web\s*自动化).{0,24}(?:生图|出图|image generation|text2image|image2image)", re.I)
    for path in prompt_paths:
        if not os.path.isfile(path):
            continue
        text = open(path, encoding="utf-8").read()
        if forbidden_call_re.search(text):
            add(
                BLOCK,
                "生图AI一致性",
                path,
                "prompt 出现同视频AI/非官方/第三方逆向/web 自动化出图口径；属未授权或含糊出图路径，必须移除。官方 Dreamina CLI 请显式写 “Dreamina/即梦”。",
            )
        for m in backend_decl_re.finditer(text):
            pc, pk = classify_image_backend(m.group(1))
            if pk == "forbidden":
                add(
                    BLOCK,
                    "生图AI一致性",
                    path,
                    f"prompt 标注未授权/含糊出图后端「{m.group(1).strip()}」；请改用官方后端（Codex/OpenAI/Dreamina/Seedream/可灵/Nano Banana/Sora）。",
                )
            elif pk == "approved":
                used.add(pc)

    if len(used) >= 2:
        add(
            BLOCK,
            "生图AI一致性",
            settings_loc,
            f"同项目/同集混用多个生图后端（{'、'.join(sorted(used))}）；混用会让同角色脸型/服装/画风跨镜漂移。"
            "请把 _设置.md 与所有 prompt 统一到同一个生图后端后再出图。",
        )


def storyboard_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "storyboard.json")


def load_storyboard(root: str, ep: str) -> Optional[dict]:
    p = storyboard_path(root, ep)
    data = load_json(p)
    if not isinstance(data, dict):
        add(BLOCK, "故事板", p, "缺少机器可读 storyboard.json；下游无法确定 continuity/need_endframe")
        return None
    clips = data.get("clips")
    if not isinstance(clips, list) or not clips:
        add(BLOCK, "故事板", p, "storyboard.json 缺 clips[]")
        return None
    return data


def check_storyboard_contract(root: str, ep: str, require_frame_assets: bool = True) -> Optional[dict]:
    data = load_storyboard(root, ep)
    if not data:
        return None
    clips = data["clips"]
    policy = data.get("policy")
    if not isinstance(policy, dict) or policy.get("tailframe_default") is not True:
        add(BLOCK, "故事板", storyboard_path(root, ep), "storyboard.json 缺 policy.tailframe_default=true；首尾双帧接力必须作为默认契约")
    prev_end = None
    for i, clip in enumerate(clips, 1):
        loc = f"{storyboard_path(root, ep)} clip#{i}"
        first_png = clip.get("firstframe_png")
        if not first_png:
            add(BLOCK, "首帧", loc, "缺 firstframe_png")
        elif require_frame_assets:
            first_full = first_png if os.path.isabs(first_png) else os.path.join(root, first_png)
            if not os.path.exists(first_full):
                add(BLOCK, "首帧", first_full, "firstframe_png 不存在")
        cont = clip.get("continuity")
        if not isinstance(cont, dict):
            add(BLOCK, "故事板", loc, "缺 continuity 块")
            continue
        for key in ("start_state", "end_state", "transition", "need_endframe"):
            if key not in cont:
                add(BLOCK, "故事板", loc, f"continuity 缺字段：{key}")
        if prev_end and cont.get("start_state") != prev_end:
            add(BLOCK, "故事板", loc, "start_state 未原样继承上一 Clip 的 end_state")
        prev_end = cont.get("end_state")
        if i < len(clips) and cont.get("need_endframe") is not True:
            if not cont.get("endframe_exempt_reason"):
                add(BLOCK, "尾帧", loc, "非最终 Clip 默认必须 need_endframe=true；若豁免需填写 endframe_exempt_reason")
        if cont.get("need_endframe") is True:
            end_png = cont.get("endframe_png")
            if not end_png:
                add(BLOCK, "尾帧", loc, "need_endframe=true 但未填写 endframe_png")
            elif require_frame_assets:
                full = end_png if os.path.isabs(end_png) else os.path.join(root, end_png)
                if not os.path.exists(full):
                    add(BLOCK, "尾帧", full, "need_endframe=true 但尾帧 PNG 不存在")
        # 中段锚帧：声明了 midframe/anchors 就必须是完整可执行契约。
        # 执行成本由后端能力决定（native multiframe / split relay / qc reference），但锚帧 PNG、
        # 时间点和理由缺一不放行，避免生成了 `_mid` 却在视频阶段被静默忽略。
        # midframe = 单锚帧手写糖（_mid）；anchors = 通用 N 锚帧链（_a1.._aN，anchor_planner 写）。
        mid = cont.get("midframe")
        anchors = cont.get("anchors")
        # 三帧契约铁律（默认强制·能力门控）：默认每镜 ≥3 帧（首+中+尾），不因 cost/风格豁免。
        # **唯一豁免**=路由视频后端不支持 ≥3 帧（first-frame-only，连首尾拆段都钉不住第3帧）——
        # 由 adapter 层 backend_supports_three_plus_frames 按后端能力自动判定，不是用户偏好。
        # backend 取 storyboard.policy.video_backend（缺/未知后端 → 按支持·向前看默认强制）。
        # policy 缺失/契约前定稿的旧集据此被拦，须补跑 anchor_planner --write 后才放行。
        sb_backend = policy.get("video_backend") if isinstance(policy, dict) else None
        midframe_enforced = backend_supports_three_plus_frames(sb_backend)
        if midframe_enforced \
                and mid is None and anchors is None and not cont.get("midframe_exempt_reason"):
            add(BLOCK, "中段锚帧", loc,
                "三帧契约铁律（首帧+中段锚帧+尾帧·默认强制）下，每镜必须声明 "
                "continuity.midframe/anchors，或写 midframe_exempt_reason（极短镜<3s豁免）；"
                "跑 anchor_planner.py --default-midframe --write 自动补齐。"
                "（唯一豁免=后端不支持≥3帧，由后端能力自动判定·不因 cost/风格放行）")
        if mid is not None and anchors is not None:
            add(BLOCK, "中段锚帧", loc, "continuity.midframe 与 continuity.anchors 不能同时声明（语义歧义）；单锚帧用 midframe 或一项 anchors，二选一")
            continue
        if mid is not None:
            if not isinstance(mid, dict):
                add(BLOCK, "中段锚帧", loc, "continuity.midframe 必须是 object（midframe_png/split_at_sec/reason）")
                continue
            anchors = [{**mid, "_fields": ("midframe_png", "split_at_sec", "reason")}]
        if anchors is not None:
            if not isinstance(anchors, list) or not anchors:
                add(BLOCK, "中段锚帧", loc, "continuity.anchors 必须是非空 list（每项 anchor_png/at_sec/reason）")
                continue
            duration = clip.get("duration")
            prev_at = 0.0
            for k, a in enumerate(anchors, 1):
                if not isinstance(a, dict):
                    add(BLOCK, "中段锚帧", loc, f"anchors[{k}] 必须是 object（anchor_png/at_sec/reason）")
                    continue
                png_key, at_key, reason_key = a.get("_fields", ("anchor_png", "at_sec", "reason"))
                for label, key in (("锚帧 PNG", png_key), ("锚点秒数", at_key), ("锚帧理由", reason_key)):
                    if a.get(key) in (None, ""):
                        add(BLOCK, "中段锚帧", loc, f"锚帧 {k} 缺字段：{key}（中段锚帧契约必须写明{label}；执行时会按后端能力走原生多帧、拆段接力或 QC/reference）")
                at = a.get(at_key)
                if at not in (None, ""):
                    if isinstance(at, bool) or not isinstance(at, (int, float)):
                        add(BLOCK, "中段锚帧", loc, f"锚帧 {k} 的 {at_key} 必须是数字：{at!r}")
                    else:
                        if isinstance(duration, (int, float)) and not (0 < at < duration):
                            add(BLOCK, "中段锚帧", loc, f"锚帧 {k} 的 {at_key}={at} 必须落在 (0, duration={duration}) 内，各段还须 ≥ 目标后端最短时长")
                        if at <= prev_at:
                            add(BLOCK, "中段锚帧", loc, f"锚帧 {k} 的 {at_key}={at} 必须严格递增（前一锚点 {prev_at}）")
                        prev_at = at if at > prev_at else prev_at
                png = a.get(png_key)
                if png and require_frame_assets:
                    full = png if os.path.isabs(png) else os.path.join(root, png)
                    if not os.path.exists(full):
                        add(BLOCK, "中段锚帧", full, f"声明了锚帧 {k} 但锚帧 PNG 不存在")
                    else:
                        _check_midframe_generation_self_check(root, ep, str(png), loc, k)
    return data


def check_storyboard_visual_contract(root: str, ep: str) -> None:
    """storyboard.json must seed the visual contract at the script stage.

    Axis/eyeline, scene light position, character-state progression and the
    shot-size ladder are director decisions made when the storyboard is cut.
    They must live in storyboard.json's `visual_contract` so n2d-image inherits
    them instead of re-inventing them — the single upstream source of truth for
    everything later baked into first-frame pixels.
    """
    p = storyboard_path(root, ep)
    data = load_json(p)
    if not isinstance(data, dict):
        return  # storyboard 缺失/损坏由 check_storyboard_contract 报，避免重复
    vc = data.get("visual_contract")
    if not isinstance(vc, dict):
        add(BLOCK, "视觉契约", p, "storyboard.json 缺 visual_contract 种子块；轴线/光位/状态/景别是分镜设计阶段的导演决策，须在此写死供出图继承（回 n2d-script 补 visual_contract）")
        return
    for key in VISUAL_CONTRACT_FIELDS:
        if key not in vc:
            add(BLOCK, "视觉契约", p, f"storyboard.json visual_contract 缺字段：{key}")


def check_storyboard_style_contract(root: str, ep: str) -> None:
    """storyboard.json must seed the chosen base visual style contract.

    The style choice belongs in user settings/global_style, not in skill code.
    The contract turns that choice into repeatable constraints so image/video
    prompts inherit one source instead of appending generic style adjectives.
    """
    p = storyboard_path(root, ep)
    data = load_json(p)
    if not isinstance(data, dict):
        return
    sc = data.get("style_contract")
    legacy = False
    fields = STYLE_CONTRACT_FIELDS
    if not isinstance(sc, dict):
        sc = data.get("cinematic_contract")
        legacy = isinstance(sc, dict)
        fields = CINEMATIC_CONTRACT_FIELDS
    if not isinstance(sc, dict):
        add(BLOCK, "基础视觉风格契约", p, "storyboard.json 缺 style_contract 种子块；基础视觉风格必须来自 `_设置.md`/global_style，并在分镜设计阶段写成结构化契约供出图/出视频继承")
        return
    key_name = "cinematic_contract" if legacy else "style_contract"
    for key in fields:
        if key not in sc:
            add(BLOCK, "基础视觉风格契约", p, f"storyboard.json {key_name} 缺字段：{key}")
    # ⑥ 软校验：风格名 应与选择点「基础视觉风格」同源（项目选二次元、契约却写写实=矛盾，gate 只查在场会漏）
    if not legacy:
        chosen = str(get_setting(root, "基础视觉风格", "")).strip()
        name = str(sc.get("风格名", "")).strip()
        if chosen and name and chosen not in name and name not in chosen:
            add(WARN, "风格一致性", p,
                f"style_contract.风格名「{name}」与 _设置.md 基础视觉风格「{chosen}」不一致——风格真值应同源；核对是否选错风格或契约写偏")


def check_storyboard_cinematic_contract(root: str, ep: str) -> None:
    """Backward-compatible wrapper for old tests/scripts."""
    check_storyboard_style_contract(root, ep)


_TONE_SPLIT_RE = re.compile(r"[；;。.，,\n]")


def _tone_base(value) -> str:
    """色调基线的基调首句（；。，前），去空白——逐集细化在首句后，基调首句应跨集恒定。"""
    s = str(value or "").strip()
    if not s:
        return ""
    return re.sub(r"\s+", "", _TONE_SPLIT_RE.split(s)[0])


def _earliest_storyboard_ep(root: str) -> Optional[str]:
    """打样集 = 最早一个有 storyboard.json 的集（按集号）。"""
    eps = []
    for p in glob.glob(os.path.join(root, "脚本", "*", "storyboard.json")):
        name = os.path.basename(os.path.dirname(p))
        digits = "".join(c for c in name if c.isdigit())
        if digits:
            eps.append((int(digits), name))
    return min(eps)[1] if eps else None


def check_cross_episode_style(root: str, ep: str) -> None:
    """跨集色调/风格基线：以打样集为基准比对本集 色调基线基调 + 风格名。

    集级 visual_contract/style_contract 各自自洽、inherit 各自 pass，整部却可能画风跳（第5集冷青灰、第6集暖橙）。
    色调基线允许逐集细化，但其【基调首句】应跨集恒定；风格名应完全一致。漂移→WARN（以打样集为准或确认有意改）。
    """
    base_ep = _earliest_storyboard_ep(root)
    if not base_ep or base_ep == ep:
        return
    # 直接读 JSON（只需契约块，不触发 load_storyboard 的 clips[] 硬校验与副作用 BLOCK）
    base, cur = load_json(storyboard_path(root, base_ep)), load_json(storyboard_path(root, ep))
    if not isinstance(base, dict) or not isinstance(cur, dict):
        return
    p = storyboard_path(root, ep)
    base_tone = _tone_base((base.get("visual_contract") or {}).get("色调基线"))
    cur_tone = _tone_base((cur.get("visual_contract") or {}).get("色调基线"))
    if base_tone and cur_tone and base_tone != cur_tone:
        add(WARN, "跨集色调", p,
            f"本集色调基线基调「{cur_tone}」与打样集 {base_ep}「{base_tone}」不一致——色调可逐集细化但基调应跨集恒定；"
            f"以打样集为准或确认有意改（防整部画风跳）", return_to_stage="script_stage2")
    base_name = str((base.get("style_contract") or {}).get("风格名", "")).strip()
    cur_name = str((cur.get("style_contract") or {}).get("风格名", "")).strip()
    if base_name and cur_name and base_name != cur_name:
        add(WARN, "跨集风格", p,
            f"本集风格名「{cur_name}」与打样集 {base_ep}「{base_name}」不一致——基础视觉风格应跨集统一；核对是否选错风格",
            return_to_stage="script_stage2")


def _clip_blob(clip: dict) -> str:
    try:
        return json.dumps(clip, ensure_ascii=False)
    except Exception:
        return str(clip)


def _first_template_keyword_hit(blob: str) -> Optional[str]:
    for template_id, words in SPECIAL_SHOT_KEYWORDS:
        if any(w in blob for w in words):
            return template_id
    return None


def _field_is_missing(contract: dict, key: str) -> bool:
    if key not in contract:
        return True
    value = contract.get(key)
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and not value:
        return True
    return False


def check_storyboard_special_templates(root: str, ep: str) -> None:
    """Complex shots must be declared through reusable storyboard templates.

    The expensive image/video stages should inherit a structured action/blocking
    contract instead of asking the model to invent fights, chases, reverse shots
    or crowd staging from prose every time.
    """
    p = storyboard_path(root, ep)
    data = load_json(p)
    if not isinstance(data, dict):
        return
    clips = data.get("clips")
    if not isinstance(clips, list):
        return
    for i, clip in enumerate(clips, 1):
        if not isinstance(clip, dict):
            continue
        loc = f"{p} clip#{i}"
        template_id = str(clip.get("template", "")).strip()
        contract = clip.get("template_contract")
        blob = _clip_blob(clip)
        keyword_template = _first_template_keyword_hit(blob)

        if not template_id:
            if keyword_template:
                add(
                    BLOCK,
                    "专项镜头模板",
                    loc,
                    f"复杂镜头疑似「{keyword_template}」，但缺 template/template_contract；回 n2d-script 按 references/专项镜头模板库.md 套模板，不要从零写 prompt",
                )
            elif isinstance(contract, dict):
                add(BLOCK, "专项镜头模板", loc, "有 template_contract 但缺 template；两者必须成对出现")
            continue

        if template_id not in SPECIAL_SHOT_TEMPLATE_FIELDS:
            add(
                BLOCK,
                "专项镜头模板",
                loc,
                f"未知 template「{template_id}」；只能使用 {', '.join(SPECIAL_SHOT_TEMPLATE_FIELDS.keys())}",
            )
            continue
        if not isinstance(contract, dict):
            add(BLOCK, "专项镜头模板", loc, f"template={template_id} 但缺 template_contract 结构块")
            continue
        if str(contract.get("template_id", "")).strip() != template_id:
            add(BLOCK, "专项镜头模板", loc, f"template_contract.template_id 必须等于 template「{template_id}」")
        for key in SPECIAL_SHOT_TEMPLATE_FIELDS[template_id]:
            if _field_is_missing(contract, key):
                add(BLOCK, "专项镜头模板", loc, f"template={template_id} 的 template_contract 缺字段：{key}")


def identity_adapter_matrix_path(root: str) -> str:
    return os.path.join(root, "生产数据", "identity_adapter_matrix.json")


def _has_identity_handle(cfg: dict) -> bool:
    return any(str(cfg.get(key, "")).strip() for key in IDENTITY_HANDLE_FIELDS)


def _validate_identity_adapter_map(section: object, loc: str, label: str) -> None:
    if not isinstance(section, dict) or not section:
        add(BLOCK, "资产身份注册层", loc, f"`identity_adapters.{label}` 缺失或为空")
        return
    for backend, cfg in section.items():
        bloc = f"{loc} identity_adapters.{label}.{backend}"
        if not isinstance(cfg, dict):
            add(BLOCK, "资产身份注册层", bloc, "adapter 必须是对象，含 mode/status")
            continue
        for key in ("mode", "status"):
            if _field_is_missing(cfg, key):
                add(BLOCK, "资产身份注册层", bloc, f"adapter 缺字段：{key}")
        status = str(cfg.get("status", "")).strip()
        mode = str(cfg.get("mode", "")).strip()
        if status and status not in IDENTITY_KNOWN_STATUSES:
            add(BLOCK, "资产身份注册层", bloc, f"未知 status「{status}」；必须使用结构化枚举，不能自由写")
        allowed_modes = (IDENTITY_ALLOWED_IMAGE_MODES if label == "image" else IDENTITY_ALLOWED_VIDEO_MODES).get(str(backend))
        if allowed_modes and mode and mode not in allowed_modes:
            add(BLOCK, "资产身份注册层", bloc, f"{label}.{backend} mode「{mode}」不匹配后端能力；允许：{', '.join(allowed_modes)}")
        if status in IDENTITY_READY_STATUSES and not _has_identity_handle(cfg):
            add(BLOCK, "资产身份注册层", bloc, "registered/ready 状态必须填写真实 id/handle/reference/model_path，不能空登记")


def _lora_gap_loc_suffix(code: str) -> str:
    """LoRA 缺口码 → finding loc 尾缀（保持与历史逐条检查相同的定位粒度）。"""
    if code == "ready_model_hash_mismatch":
        return ".model_hash"
    if code == "ready_model_path_missing":
        return ".model_path"
    if code.startswith("ready_validation_report") or code.startswith("ready_dataset_warnings"):
        return ".validation_report"
    return ""


def _validate_identity_lora(section: object, loc: str, root: str) -> None:
    """LoRA ready 校验收口到契约单一真值源 lora_registry_ready_blocks / lora_gap_message。

    与 n2d-lora cmd_register、n2d-identity 同源演进；磁盘层检查（model_path 是否存在）按契约约定
    留在调用方（契约层不碰文件系统），缺口码命名 ready_model_path_missing。
    """
    if not isinstance(section, dict):
        add(BLOCK, "资产身份注册层", f"{loc} identity_adapters.lora", "缺 LoRA 状态对象")
        return
    status = str(section.get("status", "")).strip()
    if not status:
        add(BLOCK, "资产身份注册层", f"{loc} identity_adapters.lora", "LoRA 缺 status")
    if status == "ready":
        report = None
        report_rel = str(section.get("validation_report", "")).strip()
        if report_rel:
            report_path = report_rel if os.path.isabs(report_rel) else os.path.join(root, report_rel)
            report = load_json(report_path)  # 读不出 → None，契约层报 ready_validation_report_missing
        codes = lora_registry_ready_blocks(section, report)
        model_rel = str(section.get("model_path", "")).strip()
        if model_rel and not _identity_reference_exists(root, model_rel):
            codes.append("ready_model_path_missing")  # 磁盘检查由调用方补充（契约约定）
        for code in codes:
            add(BLOCK, "资产身份注册层", f"{loc} identity_adapters.lora{_lora_gap_loc_suffix(code)}", lora_gap_message(code))


def _identity_reference_exists(root: str, rel: str) -> bool:
    full = rel if os.path.isabs(rel) else os.path.join(root, rel)
    return os.path.exists(full)


def _identity_reference_matches_asset_key(asset_key: str, rel: str) -> bool:
    """Registry references must advertise the exact character form they lock."""
    key = str(asset_key or "").strip()
    if not key:
        return True
    stem = os.path.splitext(os.path.basename(str(rel or "").strip()))[0]
    return key in stem


def check_identity_registry(
    root: str,
    require_reference_assets: bool = False,
    required_character_ids: Optional[set] = None,
) -> None:
    """Validate the role identity registry shared by image/video/review stages."""
    p = identity_registry_path(root)
    data = load_json(p)
    if not isinstance(data, dict):
        add(BLOCK, "资产身份注册层", p, "缺少或无法解析 identity_registry.json；共享定妆必须升级为角色身份注册层")
        return
    if data.get("kind") not in (None, IDENTITY_REGISTRY_KIND, "n2d_asset_identity_registry"):
        add(BLOCK, "资产身份注册层", p, f"kind 必须是 {IDENTITY_REGISTRY_KIND}")
    chars = data.get("characters")
    if not isinstance(chars, list) or not chars:
        add(BLOCK, "资产身份注册层", p, "characters[] 缺失或为空；明确角色/形态必须登记")
        return

    seen_ids = set()
    for ci, char in enumerate(chars, 1):
        loc = f"{p} character#{ci}"
        if not isinstance(char, dict):
            add(BLOCK, "资产身份注册层", loc, "character 必须是对象")
            continue
        for key in ("id", "name", "scope", "forms"):
            if _field_is_missing(char, key):
                add(BLOCK, "资产身份注册层", loc, f"character 缺字段：{key}")
        char_id = str(char.get("id", "")).strip()
        if char_id:
            if char_id in seen_ids:
                add(BLOCK, "资产身份注册层", loc, f"重复 character id：{char_id}")
            seen_ids.add(char_id)

        strict_references = required_character_ids is None or char_id in required_character_ids

        forms = char.get("forms")
        if not isinstance(forms, list) or not forms:
            add(BLOCK, "资产身份注册层", loc, "forms[] 缺失或为空；常态/变体必须分别登记")
            continue
        form_count = len(forms)
        for fi, form in enumerate(forms, 1):
            floc = f"{loc} form#{fi}"
            if not isinstance(form, dict):
                add(BLOCK, "资产身份注册层", floc, "form 必须是对象")
                continue
            for key in IDENTITY_FORM_FIELDS:
                if _field_is_missing(form, key):
                    add(BLOCK, "资产身份注册层", floc, f"form 缺字段：{key}")

            reference_group = form.get("reference_group")
            if not isinstance(reference_group, dict):
                add(BLOCK, "资产身份注册层", floc, "reference_group 必须是对象")
            else:
                asset_key = str(form.get("asset_key") or "").strip()
                form_name = str(form.get("form") or "").strip()
                # Legacy single-form baseline characters may use `定妆_<角色>.png`.
                # Multi-form or named variant forms must advertise the exact asset_key.
                enforce_asset_key_filename = form_count > 1 or form_name not in {"常态", "局部参考", "局部参考（暂不正脸）"}
                for key in IDENTITY_REFERENCE_FIELDS:
                    if _field_is_missing(reference_group, key):
                        if strict_references:
                            add(BLOCK, "资产身份注册层", floc, f"reference_group 缺核心路径：{key}")
                        continue
                    rel = str(reference_group.get(key, "")).strip()
                    if asset_key and enforce_asset_key_filename and not _identity_reference_matches_asset_key(asset_key, rel):
                        add(BLOCK, "资产身份注册层", floc,
                            f"reference_group.{key} 路径 `{rel}` 未包含 asset_key={asset_key}；"
                            "服饰/形态变体必须独立定妆，禁止复用其它服饰形态参考")
                    if require_reference_assets and strict_references and not _identity_reference_exists(root, rel):
                        add(BLOCK, "资产身份注册层", os.path.join(root, rel) if not os.path.isabs(rel) else rel, f"reference_group.{key} 路径不存在")
                expressions = reference_group.get("expressions", [])
                if expressions is not None and not isinstance(expressions, list):
                    add(BLOCK, "资产身份注册层", floc, "reference_group.expressions 必须是列表")
                for expr in expressions or []:
                    rel = str(expr or "").strip()
                    if not rel:
                        add(BLOCK, "资产身份注册层", floc, "reference_group.expressions 存在空路径")
                        continue
                    if require_reference_assets and strict_references and not _identity_reference_exists(root, rel):
                        add(BLOCK, "资产身份注册层", os.path.join(root, rel) if not os.path.isabs(rel) else rel, "reference_group.expressions 路径不存在")
                    if asset_key and asset_key not in os.path.basename(rel):
                        add(BLOCK, "资产身份注册层", floc, f"reference_group.expressions 跨角色/形态污染：{rel} 不属于 asset_key={asset_key}")

            adapters = form.get("identity_adapters")
            if not isinstance(adapters, dict):
                add(BLOCK, "资产身份注册层", floc, "identity_adapters 必须是对象")
            else:
                for section in IDENTITY_ADAPTER_SECTIONS:
                    _validate_identity_adapter_map(adapters.get(section), floc, section)
                _validate_identity_lora(adapters.get("lora"), floc, root)

            angle_policy = form.get("angle_policy")
            if not isinstance(angle_policy, dict):
                add(BLOCK, "资产身份注册层", floc, "angle_policy 必须是对象")
            else:
                for key in IDENTITY_ANGLE_FIELDS:
                    if _field_is_missing(angle_policy, key):
                        add(BLOCK, "资产身份注册层", floc, f"angle_policy 缺字段：{key}")

            drift_forbidden = form.get("drift_forbidden")
            if not isinstance(drift_forbidden, list) or not drift_forbidden:
                add(BLOCK, "资产身份注册层", floc, "drift_forbidden 必须是非空列表")


_COSTUME_VARIANT_RE = re.compile(r"_(侧|半身|全身|背|三视图|设定表|表情)$")
_COSTUME_NON_FACE = ("三视图", "设定表", "表情")  # 人审拼版，非脸度量基准


def _costume_stem(basename: str) -> str:
    s = basename[:-4] if basename.endswith(".png") else basename
    return _COSTUME_VARIANT_RE.sub("", s)


def check_costume_registry_reconcile(root: str) -> None:
    """定妆库 ↔ identity_registry 双向对账。

    face 机检按文件名 glob 发现定妆图、identity_registry 按登记的 reference_group 路径锁脸——两套各写各的，
    若 registry 登记 `定妆_X_人皮态.png` 但磁盘只有 `定妆_X.png`，崩脸机检可能测的根本不是 registry 锁的那张。
    本检查对账：① registry 登记但磁盘缺的参考；② 属于已登记角色、磁盘有却没进任何 reference_group 的定妆变体（orphan）。
    场景定妆（不属任何角色）天然不匹配角色 stem，不误报。
    """
    reg = load_json(identity_registry_path(root))
    if not isinstance(reg, dict):
        return  # 缺 registry：check_identity_registry 已把关
    registered_rel: set = set()
    for char in reg.get("characters") or []:
        for form in (char.get("forms") or []):
            rg = form.get("reference_group")
            if not isinstance(rg, dict):
                continue
            for val in rg.values():
                for v in (val if isinstance(val, list) else [val]):
                    if isinstance(v, str) and v.strip():
                        registered_rel.add(v.strip())
    if not registered_rel:
        return
    registered_base = {os.path.basename(p) for p in registered_rel}
    char_stems = {_costume_stem(b) for b in registered_base}
    # ① registry 登记但磁盘缺（三视图/设定表/表情 不强求落盘）
    for rel in sorted(registered_rel):
        bn = os.path.basename(rel)
        if any(t in bn for t in _COSTUME_NON_FACE):
            continue
        if not os.path.isfile(os.path.join(root, rel)):
            add(WARN, "定妆对账", rel,
                f"identity_registry 登记的定妆参考 {rel} 磁盘缺失；补出该图或修 registry 路径，否则锁脸参考落空")
    # ② 已登记角色的 orphan 变体：磁盘有、属同一角色 stem、却没进 reference_group
    for p in sorted(glob.glob(os.path.join(shared_asset_path(root, "图片"), "定妆_*.png"))):
        bn = os.path.basename(p)
        if any(t in bn for t in _COSTUME_NON_FACE):
            continue
        if bn in registered_base:
            continue
        # 属已登记角色 = 文件名等于某角色 stem，或是其变体（stem_ 前缀）——任意变体后缀都能抓到
        if any(bn == stem + ".png" or bn.startswith(stem + "_") for stem in char_stems):
            add(WARN, "定妆对账", p,
                f"定妆图 {bn} 属已登记角色但未进 identity_registry 任何 reference_group；"
                f"face 机检会按文件名把它当参考、与 registry 锁的不是同一套 → 登记进 registry 或删除")


def check_asset_reference_registry(
    root: str,
    require_reference_assets: bool = False,
    required_asset_ids: Optional[set] = None,
) -> None:
    """Validate reusable non-character scene/prop/outfit/vfx asset registry."""
    p = asset_registry_path(root)
    data = load_json(p)
    if not isinstance(data, dict):
        add(BLOCK, "资产引用注册层", p, "缺少或无法解析 asset_registry.json；关键场景/道具/服装/VFX 必须升级为 LOC_/PROP_/OUTFIT_/VFX_ 资产引用注册层")
        return
    if data.get("kind") != ASSET_REFERENCE_REGISTRY_KIND:
        add(BLOCK, "资产引用注册层", p, f"kind 必须是 {ASSET_REFERENCE_REGISTRY_KIND}")
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        add(BLOCK, "资产引用注册层", p, "assets[] 缺失或为空；关键场景/道具/服装/VFX 必须登记")
        return

    seen_ids = set()
    for idx, asset in enumerate(assets, 1):
        loc = f"{p} asset#{idx}"
        if not isinstance(asset, dict):
            add(BLOCK, "资产引用注册层", loc, "asset 必须是对象")
            continue
        for key in ASSET_REFERENCE_REQUIRED_FIELDS:
            if _field_is_missing(asset, key):
                add(BLOCK, "资产引用注册层", loc, f"asset 缺字段：{key}")

        asset_id = str(asset.get("id", "")).strip()
        asset_type = str(asset.get("type", "")).strip().lower()
        strict_references = required_asset_ids is None or asset_id in required_asset_ids
        if asset_id:
            if asset_id in seen_ids:
                add(BLOCK, "资产引用注册层", loc, f"重复 asset id：{asset_id}")
            seen_ids.add(asset_id)
        expected_prefix = ASSET_REFERENCE_TYPE_PREFIX.get(asset_type)
        if asset_type and not expected_prefix:
            add(BLOCK, "资产引用注册层", loc, f"未知 type「{asset_type}」；允许：{', '.join(sorted(ASSET_REFERENCE_TYPE_PREFIX))}")
        elif expected_prefix and asset_id and not asset_id.startswith(expected_prefix):
            add(BLOCK, "资产引用注册层", loc, f"type={asset_type} 的 id 必须以 {expected_prefix} 开头")

        # 深度一致性检查：道具生命周期与所有权
        if asset_type == "prop":
            for key in ASSET_PROP_REQUIRED_FIELDS:
                if _field_is_missing(asset, key):
                    add(BLOCK, "资产引用注册层", loc, f"关键道具资产缺生命周期字段：{key}")

        # 深度一致性检查：场景空间布局
        if asset_type in ("scene", "location"):
            for key in ASSET_SCENE_REQUIRED_FIELDS:
                if _field_is_missing(asset, key):
                    add(BLOCK, "资产引用注册层", loc, f"反复场景资产缺空间布局字段：{key}")

        reference_group = asset.get("reference_group")
        if not isinstance(reference_group, dict):
            add(BLOCK, "资产引用注册层", loc, "reference_group 必须是对象，至少含 primary")
        else:
            primary = str(reference_group.get("primary", "")).strip()
            if not primary:
                add(BLOCK, "资产引用注册层", loc, "reference_group.primary 缺失或为空")
            elif require_reference_assets and strict_references and not _identity_reference_exists(root, primary):
                add(BLOCK, "资产引用注册层", os.path.join(root, primary) if not os.path.isabs(primary) else primary, "reference_group.primary 路径不存在")
            alternates = reference_group.get("alternates", [])
            if alternates is not None and not isinstance(alternates, list):
                add(BLOCK, "资产引用注册层", loc, "reference_group.alternates 必须是列表")
            for rel in alternates or []:
                rel_s = str(rel or "").strip()
                if not rel_s:
                    add(BLOCK, "资产引用注册层", loc, "reference_group.alternates 存在空路径")
                elif require_reference_assets and strict_references and not _identity_reference_exists(root, rel_s):
                    add(BLOCK, "资产引用注册层", os.path.join(root, rel_s) if not os.path.isabs(rel_s) else rel_s, "reference_group.alternates 路径不存在")

        constraints = asset.get("constraints")
        if not isinstance(constraints, dict) or not constraints:
            add(BLOCK, "资产引用注册层", loc, "constraints 必须是非空对象；不能只登记名字 and 图片")
        else:
            if asset_type in {"scene", "location"}:
                if not any(k in constraints for k in ("layout", "axis", "light_anchor", "structure")):
                    add(BLOCK, "资产引用注册层", loc, "场景资产 constraints 必须锁 layout/axis/light_anchor/structure 至少一项")
                if "lighting_signature" not in constraints:
                    add(WARN, "资产引用注册层", loc, "建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变")

            if asset_type == "prop" and "structure" not in constraints:
                add(BLOCK, "资产引用注册层", loc, "道具资产 constraints 必须锁 structure，避免壶嘴/刀刃/镜面等部件幻觉")
            name_blob = f"{asset.get('name', '')}\n{json.dumps(constraints, ensure_ascii=False)}"
            if asset_type == "prop" and _has_any(name_blob, ("铜镜", "赐死", "托盘", "毒酒", "碎瓷", "匕首", "白绫")) and not _has_any(name_blob, (
                "单镜面", "唯一", "数量", "件数", "短颈圆口", "无侧嘴", "无斜嘴", "无双口", "一柄一刃", "同一只",
            )):
                add(BLOCK, "资产引用注册层", loc, "关键道具 constraints 未写结构唯一性；铜镜/托盘/毒酒/碎瓷必须锁数量与部件")

        drift_forbidden = asset.get("drift_forbidden")
        if not isinstance(drift_forbidden, list) or not drift_forbidden:
            add(BLOCK, "资产引用注册层", loc, "drift_forbidden 必须是非空列表")


# ── 景别阶梯机检（契约只校验「景别阶梯」字段存在；这里补对实际镜序列的机检）───────────────
# 长词优先（大远景 before 远景、中近景 before 中景、ECU/MCU before CU/MS），英文带词界防 CU 命中 MCU/ECU。
_SHOT_SCALE_MAP = sorted([
    ("大特写", "ECU"), ("极特写", "ECU"), ("ECU", "ECU"),
    ("特写", "CU"), ("CU", "CU"),
    ("中近景", "MCU"), ("中近", "MCU"), ("MCU", "MCU"),
    ("中景", "MS"), ("MS", "MS"),
    ("大远景", "ELS"), ("极远景", "ELS"), ("ELS", "ELS"),
    ("全景", "LS"), ("远景", "LS"), ("LS", "LS"),
], key=lambda kv: -len(kv[0]))
_OTS_RE = re.compile(r"反打|过肩|正反打|OTS|over[\s-]?shoulder", re.I)
SHOT_SCALE_MIN_RUN = 3  # 连续 >=N 镜同景别且非反打 → 景别阶梯单调告警


def shot_scale_class(text: str) -> Optional[str]:
    """从 lens/景别 串抽景别分级 ECU/CU/MCU/MS/LS/ELS。抽不到→None。纯函数·可测。"""
    raw = str(text or "")
    up = raw.upper()
    for tok, cls in _SHOT_SCALE_MAP:
        if tok.isascii():
            if re.search(rf"(?<![A-Z]){re.escape(tok.upper())}(?![A-Z])", up):
                return cls
        elif tok in raw:
            return cls
    return None


def monotonous_scale_runs(classes: Sequence[Optional[str]],
                          min_run: int = SHOT_SCALE_MIN_RUN) -> List[Tuple[int, int, str, int]]:
    """连续 >=min_run 个相同景别分级的区间 [(start_i, end_i, cls, length)]；None 打断连续。纯函数·可测。"""
    runs: List[Tuple[int, int, str, int]] = []
    i, n = 0, len(classes)
    while i < n:
        c = classes[i]
        if c is None:
            i += 1
            continue
        j = i
        while j + 1 < n and classes[j + 1] == c:
            j += 1
        if j - i + 1 >= min_run:
            runs.append((i, j, c, j - i + 1))
        i = j + 1
    return runs


def check_shot_scale_progression(root: str, ep: str) -> None:
    """景别阶梯机检：契约只校验「景别阶梯」字段存在（check_image_prompt_overview）；这里补对**实际镜序列**的机检——
    连续 >=3 镜同景别、且段内无反打/过肩（对白正反打是合法交替变化，豁免）= 景别阶梯单调、缺远近/机位变化 → warn。
    文本匹配较模糊（景别藏在 lens 串里），故 warn 不 block。"""
    sb = load_json(storyboard_path(root, ep))
    if not isinstance(sb, dict):
        return  # storyboard 缺失由 check_storyboard_contract 负责 BLOCK，这里不重复
    clips = sb.get("clips") or sb.get("shots") or []
    if not isinstance(clips, list) or len(clips) < SHOT_SCALE_MIN_RUN:
        return
    classes: List[Optional[str]] = []
    lens_texts: List[str] = []
    ids: List[str] = []
    for i, clip in enumerate(clips, 1):
        if not isinstance(clip, dict):
            classes.append(None); lens_texts.append(""); ids.append(f"Clip_{i:02d}"); continue
        lens = "；".join(str((s or {}).get("lens", "")) for s in (clip.get("shots") or []))
        scale_text = lens or str(clip.get("景别") or clip.get("shot_size") or "")
        classes.append(shot_scale_class(scale_text))
        lens_texts.append(lens or scale_text)
        ids.append(str(clip.get("id") or clip.get("clip") or clip.get("shot") or f"Clip_{i:02d}"))
    for start, end, cls, length in monotonous_scale_runs(classes):
        if any(_OTS_RE.search(lens_texts[k]) for k in range(start, end + 1)):
            continue  # 对白正反打/过肩交替 = 合法景别变化，豁免
        loc = f"{ids[start]}→{ids[end]}"
        add(WARN, "景别阶梯", loc,
            f"连续 {length} 镜同景别 {cls}（{loc}）——景别阶梯单调、缺远近或机位变化；"
            "按导演意图穿插不同景别/机位（或确认为设计内的同景别段）。",
            return_to_stage="image")
    # 抽取健壮性（G）：lens 写了但抽不出景别分级的镜（如「中景偏特写」「平视带点压」这类非标准写法），
    # 景别阶梯机检对它们静默失效——把这些镜醒目报出来，提示规范 lens 写法，避免「全绿=都查过了」的错觉。
    unparsed = [ids[i] for i in range(len(classes)) if classes[i] is None and lens_texts[i].strip()]
    if len(unparsed) >= 2:
        sample = "、".join(unparsed[:6]) + ("…" if len(unparsed) > 6 else "")
        add(WARN, "景别阶梯", sample,
            f"{len(unparsed)} 个镜写了 lens 但抽不出景别分级（{sample}）——景别阶梯单调性机检对它们失效；"
            "把 lens 写成标准景别词（ELS/LS/MS/MCU/CU/ECU 或 大远景/远景/中景/中近景/特写/大特写）再机检。",
            return_to_stage="image")


def check_cinematic_optical_continuity(root: str, ep: str) -> None:
    """Validate that focal lengths match shot sizes to prevent perspective distortion."""
    pd = os.path.join(root, "出图", ep, "prompt")
    f = os.path.join(pd, "01_分镜出图.md")
    if not os.path.exists(f):
        return
    
    content = open(f, encoding="utf-8").read()
    shots = re.split(r"## 镜头 \d+", content)
    
    # ECU/CU=85mm, MS=50mm, LS=35mm, ELS=24mm
    mapping = {
        "ECU": "85mm", "CU": "85mm",
        "MCU": "50mm", "MS": "50mm",
        "LS": "35mm", "ELS": "24mm"
    }
    
    for shot in shots:
        if not shot.strip(): continue
        
        shot_size_match = re.search(r"景别\((ELS|LS|MS|MCU|CU|ECU).*?\)", shot)
        if shot_size_match:
            size = shot_size_match.group(1)
            expected_focal = mapping.get(size)
            if expected_focal and expected_focal not in shot:
                add(WARN, "电影光学契约", f, f"镜头景别为 {size}，建议在 prompt 中显式锁定焦段为 {expected_focal} 以保透视一致")


def check_physical_scale_audit(root: str, ep: str) -> None:
    """Validate relative heights in multi-character shots."""
    pd = os.path.join(root, "出图", ep, "prompt")
    f = os.path.join(pd, "01_分镜出图.md")
    if not os.path.exists(f):
        return
        
    content = open(f, encoding="utf-8").read()
    shots = re.split(r"## 镜头 \d+", content)
    
    for shot in shots:
        if not shot.strip(): continue
        
        # Simple detection of multi-character shots (names often appear in '目标：')
        # This is a heuristic; real implementation would read identity_registry and storyboard.json
        char_mentions = re.findall(r"目标：.*?(沈念|柳娘子|王敦|小禾)", shot)
        if len(set(char_mentions)) >= 2:
            if not any(k in shot for k in ("仰视", "俯视", "高半个头", "身长", "比例")):
                add(WARN, "物理尺寸对账", f, f"检测到多人同框镜头，建议显式写明人物之间的【身高比例差】或【仰俯视关系】")


def check_identity_adapter_matrix(root: str) -> None:
    p = identity_adapter_matrix_path(root)
    data = load_json(p)
    if not isinstance(data, dict):
        add(BLOCK, "资产身份闭环", p, "缺少或无法解析 identity_adapter_matrix.json；先运行 `python3 skills/n2d-identity/scripts/identity.py <作品根> --write`")
        return
    if data.get("kind") != IDENTITY_ADAPTER_MATRIX_KIND:
        add(BLOCK, "资产身份闭环", p, f"kind 必须是 {IDENTITY_ADAPTER_MATRIX_KIND}")
    forms = data.get("forms")
    if not isinstance(forms, list) or not forms:
        add(BLOCK, "资产身份闭环", p, "forms[] 为空；identity_registry 没有展开成可执行后端 binding")
        return
    for idx, form in enumerate(forms, 1):
        loc = f"{p} form#{idx}"
        if not isinstance(form, dict):
            add(BLOCK, "资产身份闭环", loc, "form 必须是对象")
            continue
        for key in ("character_id", "form", "reference_group", "image_bindings", "video_bindings", "lora_binding"):
            if _field_is_missing(form, key):
                add(BLOCK, "资产身份闭环", loc, f"adapter matrix form 缺字段：{key}")


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
        for idx, sec in enumerate(sections, 1):
            check_image_shot_prompt_section(p, idx, sec)
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
        for sec in sections:
            check_video_clip_prompt_section(p, sec)
        return


def _has_any(text: str, needles: Iterable[str]) -> bool:
    return any(n in text for n in needles)


def _headline(section: str, fallback: str) -> str:
    first = next((ln.strip() for ln in section.splitlines() if ln.strip()), "")
    return first or fallback


def _has_field(section: str, label: str) -> bool:
    return bool(re.search(rf"(?:\*\*)?{re.escape(label)}(?:\*\*)?\s*[：:]", section))


def _has_line_field(section: str, label: str) -> bool:
    return bool(re.search(rf"(?m)^\s*(?:[-*]\s*)?(?:\*\*)?{re.escape(label)}(?:\*\*)?\s*[：:]", section))


def _section_requires_motion_control(section: str) -> bool:
    return _has_any(
        section,
        (
            "shot_type=fight_exchange",
            "shot_type=intimate_interaction",
            "shot_type=hug_or_pull",
            "contact_motion",
            "physical_interaction",
            "feature_melting_risk",
        ),
    )


def _missing_contract_fields(text: str, fields: Iterable[str]) -> List[str]:
    return [key for key in fields if key not in text]


def native_audio_policy(root: str) -> str:
    return get_setting(root, "视频原生音轨", "丢弃").strip() or "丢弃"


def native_audio_policy_mode(policy: str) -> str:
    normalized = policy.strip().lower().replace(" ", "")
    if normalized in ("丢弃", "discard", "none"):
        return NATIVE_AUDIO_DISCARD
    if "低音量" in policy or "环境声" in policy or normalized in ("ambience", "mix", "low"):
        return NATIVE_AUDIO_AMBIENCE
    if "保留" in policy or normalized in ("keep", "preserve"):
        return NATIVE_AUDIO_KEEP
    return NATIVE_AUDIO_DISCARD


def _section_native_audio_opt_in(section: str) -> bool:
    return _has_any(section, ("audio_intent=ambience", "audio_intent=native_sfx", "低音量混入环境声", "保留原片音轨", "compose_policy=低音量", "compose_policy=保留"))


def _native_audio_contract_ok(text: str) -> bool:
    return _has_any(text, ("无原生人声", "禁止原生人声", "no_native_speech", "no generated native voice"))


def is_native_av_production(root: str) -> bool:
    """`制作模式=原生音画`：视频后端有意一次生成同步音画（含台词）。"""
    mode = get_setting(root, "制作模式", "配音先行")
    return "原生音画" in (mode or "") or "native_av" in (mode or "").lower()


def _native_audio_policy_line(section: str) -> str:
    m = re.search(r"(?m)^\*\*原生音画策略\*\*.*$", section)
    if m:
        return m.group(0)
    m = re.search(r"(?m)^原生音画策略.*$", section)
    return m.group(0) if m else section


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


def check_markdown_style_contract(text: str, loc: str, layer: str) -> None:
    if "本集基础视觉风格契约" in text:
        missing = _missing_contract_fields(text, STYLE_CONTRACT_FIELDS)
        if missing:
            add(BLOCK, "基础视觉风格契约", loc, f"本集基础视觉风格契约缺字段：{missing[0]}")
        return
    if "本集真实电影感契约" in text:
        missing = _missing_contract_fields(text, CINEMATIC_CONTRACT_FIELDS)
        if missing:
            add(BLOCK, "基础视觉风格契约", loc, f"本集真实电影感契约缺字段：{missing[0]}")
        return
    add(BLOCK, "基础视觉风格契约", loc, f"缺「本集基础视觉风格契约」；{layer} 必须继承 storyboard.json style_contract，而不是只在 prompt 末尾加某一种风格词")


def check_markdown_cinematic_contract(text: str, loc: str, layer: str) -> None:
    """Backward-compatible wrapper for old tests/scripts."""
    check_markdown_style_contract(text, loc, layer)


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
            "缺「本集近景身份风险表」；CU/MCU/反打/说话镜必须在总览列明脸部特写/表情参考、当前后端身份锁能力、风险等级和降级方案",
        )
        return
    for key in ("脸部", "表情", "风险", "降级"):
        if key not in overview_text:
            add(BLOCK, "资产身份注册层", overview_path, f"本集近景身份风险表缺字段/关键词：{key}")
    if _has_any(overview_text, ("CHAR_02", "配角", "小禾", "柳娘子")) and not _has_any(overview_text, ("MCU", "OTS", "侧脸", "手部", "物件反应")):
        add(
            WARN,
            "资产身份注册层",
            overview_path,
            "本集近景身份风险表未写配角近景降级路径；建议明确 MCU/OTS/侧脸/手部/物件反应镜",
        )


def _route_clip_number(route: Dict[str, Any], fallback_index: int) -> int:
    raw = str(route.get("clip_id") or route.get("clip") or "").strip()
    match = re.search(r"(\d+)", raw)
    return int(match.group(1)) if match else fallback_index


def _storyboard_frame_requirements(root: str, ep: str) -> Dict[int, Dict[str, int | bool]]:
    """Clip -> ordered frame contract declared by storyboard continuity."""
    data = load_json(storyboard_path(root, ep))
    if not isinstance(data, dict) or not isinstance(data.get("clips"), list):
        return {}
    out: Dict[int, Dict[str, int | bool]] = {}
    for idx, clip in enumerate(data.get("clips") or [], 1):
        if not isinstance(clip, dict):
            continue
        cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
        if not isinstance(cont, dict):
            continue
        anchor_count = 0
        if isinstance(cont.get("midframe"), dict):
            anchor_count = 1
        elif isinstance(cont.get("anchors"), list):
            anchor_count = len([a for a in cont.get("anchors") or [] if isinstance(a, dict)])
        need_end = cont.get("need_endframe") is True
        out[idx] = {
            "need_end": need_end,
            "anchor_count": anchor_count,
            "total_timeline_frames": 1 + anchor_count + (1 if need_end else 0),
            # 高风险=高运动模板 或 跨情绪大表情近景：帧能力不匹配时安全网（双帧/多帧插值）静默失效，
            # check_route_frame_capability 据此把 WARN 升 BLOCK（其余镜保持 WARN，有合法降级路径）。
            "high_risk": (str(clip.get("template") or "") in HIGH_MOTION_TEMPLATES
                          or (cont.get("expression_span") == EXPRESSION_SPAN_BIG and _clip_is_closeup(clip))),
        }
    return out


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
    high_risk = bool(req.get("high_risk"))
    sev = BLOCK if high_risk else WARN
    risk_note = (
        "本镜为高运动模板/跨情绪大表情近景，帧间插值是唯一安全网，不许靠纯文本约束硬出（已升级为 BLOCK）。"
        if high_risk else ""
    )
    clip_id = str(route.get("clip_id") or f"Clip_{clip_num:02d}")
    mode = str(control.get("mode") or "unknown")
    verified = str(control.get("verified") or "unknown")
    fallback = str(control.get("fallback") or "Use split relay/manual generation.")
    channel_note = f"（执行渠道：{video_channel}）" if video_channel else ""
    if need_end and not bool(control.get("supports_last_frame")):
        add(
            sev,
            "首尾帧能力",
            route_path,
            f"{clip_id} storyboard 需要尾帧接力，但 primary 后端 {primary or 'unknown'}{channel_note} "
            f"的帧能力档案为 {mode}，未确认可原生消费尾帧。fallback：改走支持首尾帧的后端，"
            f"或退回单首帧 + 强 end_state 文字（接缝/大表情近景风险升高）。能力来源：{verified}{risk_note}",
            return_to_stage="video",
        )
    if anchors and not bool(control.get("supports_native_mid_anchors")):
        if bool(control.get("supports_last_frame")):
            consequence = "该后端通常只能吃首尾两帧，中段锚帧不会在一次请求里成为时间轴关键帧"
        else:
            consequence = "该后端通常只按首帧/参考图生成，中段锚帧和尾帧都可能只剩文字约束"
        add(
            sev,
            "多帧能力",
            route_path,
            f"{clip_id} storyboard 声明了 {anchors} 个中段锚帧（共 {total_frames} 张时间轴帧），"
            f"但 primary 后端 {primary or 'unknown'}{channel_note} 的帧能力档案为 {mode}，"
            f"最多 {max_frames} 张时间轴帧；{consequence}。fallback：{fallback}{risk_note}",
            return_to_stage="video",
        )


def check_video_model_routes(root: str, ep: str, overview_text: str, overview_path: str) -> None:
    if "本集模型路由表" not in overview_text:
        add(BLOCK, "模型路由", overview_path, "缺「本集模型路由表」；出视频必须先跑 n2d-model-router，不能固定一个视频模型或临场乱选后端")
    p = os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json")
    if not os.path.isfile(p):
        add(BLOCK, "模型路由", p, "缺 video_model_routes.json；先运行 `python3 skills/n2d-model-router/scripts/router.py <作品根> 第N集 --write`")
        return
    try:
        data = json.load(open(p, encoding="utf-8"))
    except Exception as exc:
        add(BLOCK, "模型路由", p, f"video_model_routes.json 解析失败：{exc}")
        return
    if data.get("kind") != VIDEO_MODEL_ROUTES_KIND:
        add(BLOCK, "模型路由", p, f"video_model_routes.json kind 必须是 {VIDEO_MODEL_ROUTES_KIND}")
    drift = data.get("baseline_drift")
    if isinstance(drift, list) and drift:
        sample = "、".join(f"{d.get('clip_id')}({d.get('shot_type')}):{d.get('was')}→{d.get('now')}" for d in drift[:5])
        add(WARN, "后端跨集锁", p,
            f"{len(drift)} 个 clip 的 shot_type 自然路由与 设定库/model_routes_baseline 不符，已按基线锚定（原后端降 fallback）；"
            f"确认基线后端仍合适，否则 --write-baseline 刷新基线。{sample}")
    routes = data.get("routes")
    if not isinstance(routes, list) or not routes:
        add(BLOCK, "模型路由", p, "video_model_routes.json routes 为空；逐 Clip 必须有 primary/fallback/mode")
        return
    fallback_setting = get_setting(root, "视频备用后端", "").strip()
    allow_empty_fallback = (
        data.get("routing_mode") == "fixed_default"
        and bool(fallback_setting)
        and (fallback_setting.lower() in FALLBACK_OFF_VALUES or fallback_setting in FALLBACK_OFF_VALUES)
    )
    required = ("clip_id", "shot_type", "primary_backend", "fallback_backends", "mode", "native_audio_policy", "identity_requirement", "motion_control", "degrade_plan")
    frame_requirements = _storyboard_frame_requirements(root, ep)
    video_channel = get_setting(root, "生视频渠道", "").strip()
    for idx, route in enumerate(routes, 1):
        if not isinstance(route, dict):
            add(BLOCK, "模型路由", p, f"routes[{idx}] 不是对象")
            continue
        for key in required:
            if key == "fallback_backends" and route.get(key) == [] and allow_empty_fallback:
                continue
            if key not in route or route.get(key) in (None, "", []):
                add(BLOCK, "模型路由", p, f"{route.get('clip_id', f'routes[{idx}]')} 缺字段：{key}")
        flags = route.get("risk_flags")
        if isinstance(flags, list) and "long_duration" in flags:
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
        check_motion_control_route(root, ep, route, p, idx)


# 非原生锁绑定 = 仅靠参考组兜底/不支持（换后端会丢真正的锁脸力）。
_NON_NATIVE_BINDINGS = {"reference_group", "fallback_reference_group", "not_needed", "unsupported", ""}
_CORE_SCOPES = {"全篇", "长线", "核心", "主角"}


def check_route_identity_readiness(root: str, ep: str) -> None:
    """换后端丢锁机检：出视频路由用到的 primary 后端 × identity_adapter_matrix 的角色锁脸能力对账。

    n2d-model-router 选后端时不读 matrix——一个在后端 A 原生注册了 character_id 的角色，若某 clip 被路由到
    后端 B（B 上只有 reference_group 兜底甚至无绑定），锁脸力骤降却无任何机检。本检查在出视频闸门前置对账：
    - 角色在 matrix 有「原生锁」(ready 且 binding 非 reference_group 族)，但路由用到的某 primary 后端在该角色上
      只有 reference_group 兜底 → 换后端丢原生锁（核心角色 BLOCK / 其余 WARN）；该后端连兜底都没有 → 必丢锁 BLOCK；
    - 全 reference_group 兜底（无任何原生锁，如当前 demo）= 后端间一致，不报（没有原生锁可丢，避免噪声）。
    """
    routes_data = load_json(os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json"))
    matrix_p = identity_adapter_matrix_path(root)
    matrix = load_json(matrix_p)
    if not isinstance(routes_data, dict) or not isinstance(matrix, dict):
        return  # 缺路由/矩阵：check_video_model_routes / check_identity_adapter_matrix 各自把关
    routes = routes_data.get("routes")
    forms = matrix.get("forms")
    if not isinstance(routes, list) or not isinstance(forms, list):
        return
    used = sorted({str(r.get("primary_backend") or "").strip()
                   for r in routes if isinstance(r, dict)} - {""})  # primary 后端集合（fallback 仅失败时触发，主查 primary）
    if not used:
        return
    for form in forms:
        if not isinstance(form, dict):
            continue
        vb = form.get("video_bindings") if isinstance(form.get("video_bindings"), dict) else {}
        native = sorted(b for b, v in vb.items()
                        if isinstance(v, dict) and v.get("ready")
                        and str(v.get("binding") or "") not in _NON_NATIVE_BINDINGS)
        if not native:
            continue  # 无原生锁 → 全兜底，后端间一致，无锁可丢
        name = form.get("character_name") or form.get("character_id") or "?"
        sev = BLOCK if str(form.get("scope") or "").strip() in _CORE_SCOPES else WARN
        for b in used:
            if b in native:
                continue
            v = vb.get(b)
            if not (isinstance(v, dict) and v.get("ready")):
                add(BLOCK, "换后端丢锁", matrix_p,
                    f"角色「{name}」已在 {native} 原生锁脸，但本集出视频路由用到后端 {b}，该后端无可用身份绑定（连 reference_group 兜底都没有）→ 必丢锁；改路由到 {native} 或先在 {b} 注册该角色身份",
                    return_to_stage="video_prompt",
                    rerun_scope=f"重跑 n2d-model-router 把涉及「{name}」的 clip 路由到 {native}，或在 {b} 注册 character_id/face_lock 后再出视频。",
                    affected_artifacts=[f"出视频/{ep}/prompt/video_model_routes.json", "生产数据/identity_adapter_matrix.json"])
            elif str(v.get("binding") or "") in _NON_NATIVE_BINDINGS:
                add(sev, "换后端丢锁", matrix_p,
                    f"角色「{name}」已在 {native} 原生锁脸，但本集有 clip 路由到后端 {b}（{b} 上仅 reference_group 兜底）= 换后端丢原生锁、锁脸力下降；核心角色应改路由或在 {b} 注册原生身份",
                    return_to_stage="video_prompt",
                    rerun_scope=f"重跑 n2d-model-router 让「{name}」的 clip 优先用 {native}，或在 {b} 注册原生身份。",
                    affected_artifacts=[f"出视频/{ep}/prompt/video_model_routes.json"])


def _motion_control_required_for_route(route: Dict[str, object]) -> bool:
    # 判定与 router 同源（n2d_contract.motion_control_required），避免两边对"需控制契约"的认定漂移
    flags = route.get("risk_flags")
    return motion_control_required(
        shot_type=route.get("shot_type"),
        risk_flags=flags if isinstance(flags, list) else None,
    )


def _resolve_under_root(root: str, path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(root, path)


def _uri_like(value: str) -> bool:
    return bool(re.match(r"^[a-z][a-z0-9+.-]*://", value.strip(), flags=re.I))


def _uri_scheme(value: str) -> str:
    m = re.match(r"^([a-z][a-z0-9+.-]*)://", value.strip(), flags=re.I)
    return m.group(1).lower() if m else ""


def _sequence_pattern_to_glob(value: str) -> str:
    text = re.sub(r"%0?\d*d", "*", value)
    return re.sub(r"#+", "*", text)


def _verified_remote_control_input(value: dict) -> bool:
    uri = str(value.get("uri") or "").strip()
    if _uri_scheme(uri) not in {"https", "s3", "gs"}:
        return False
    if not _valid_iso_date(value.get("verified_at")):
        return False
    return any(str(value.get(key) or "").strip() for key in ("sha256", "checksum", "etag"))


def _control_asset_exists(root: str, value: str, *, explicit_glob: bool = False) -> bool:
    text = value.strip()
    if not text:
        return False
    if _uri_like(text):
        return False
    pattern = _sequence_pattern_to_glob(text)
    has_glob = explicit_glob or pattern != text or any(ch in pattern for ch in "*?[]")
    full = _resolve_under_root(root, pattern)
    if has_glob:
        return bool(glob.glob(full))
    return os.path.exists(full)


def _input_ready(root: str, value: object) -> bool:
    if isinstance(value, str):
        return _control_asset_exists(root, value)
    if isinstance(value, dict):
        status = str(value.get("status") or "ready").strip()
        if status not in MOTION_CONTROL_READY_INPUT_STATUSES:
            return False
        if status == "not_needed":
            return True
        uri = str(value.get("uri") or "").strip()
        if uri:
            return _verified_remote_control_input(value)
        glob_value = str(value.get("glob") or "").strip()
        if glob_value:
            return _control_asset_exists(root, glob_value, explicit_glob=True)
        return _control_asset_exists(root, str(value.get("path") or ""))
    return False


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
        add(BLOCK, "Motion Control", loc, "高危物理接触镜头必须 motion_control.level=required 且 manifest_required=true")
    manifest_path = str(motion.get("manifest_path") or "").strip()
    if not manifest_path:
        add(BLOCK, "Motion Control", loc, "高危物理接触镜头缺 motion_control.manifest_path")
        return
    abs_manifest = _resolve_under_root(root, manifest_path)
    if not os.path.isfile(abs_manifest):
        add(BLOCK, "Motion Control", abs_manifest, "缺 motion_control_manifest.json；必须先准备 ready 控制资产，或写 status=degrade_only 的拆镜 manifest")
        return
    required_inputs = motion.get("required_inputs") if isinstance(motion.get("required_inputs"), list) else []
    check_motion_control_manifest(root, abs_manifest, route, [str(item) for item in required_inputs])


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
        add(BLOCK, "视觉契约", p, "缺「本集视觉一致性契约」；像素层导演决策（色调/光位/轴线/状态/景别）必须在出图总览先锁，不能下推到出视频")
        return
    for key in ("色调基线", "光位锚", "轴线", "状态演进", "景别阶梯"):
        if key not in text:
            add(BLOCK, "视觉契约", p, f"本集视觉一致性契约缺字段：{key}")
    check_markdown_style_contract(text, p, "出图总览")


def check_video_clip_prompt_section(path: str, section: str) -> None:
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

    if "视频 prompt（中文" not in section:
        add(BLOCK, "prompt", loc, "缺视频 prompt（中文）")
    if "视频 prompt（英文" not in section:
        add(BLOCK, "prompt", loc, "缺视频 prompt（英文）兜底")
    for key in ("运动精修约束", "环境交互约束", "人物运动", "镜头运动", "动态细节", "衔接约束", "声音约束"):
        if key not in section:
            add(BLOCK, "prompt", loc, f"中文视频 prompt 缺字段：{key}")
    if "角色身份注册层" not in section:
        add(BLOCK, "资产身份注册层", loc, "缺角色身份注册层字段；含角色镜必须继承 identity_registry.json，无人物镜写“无”")
    if not _has_line_field(section, "身份锁定约束"):
        add(BLOCK, "资产身份注册层", loc, "中文视频 prompt 缺身份锁定约束；必须写明 Character ID/Face Lock/reference controls 或 fallback reference_group")
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
                "近景/反打/说话镜缺细粒度身份锁定；必须写脸型、五官比例、发型发髻、标志配饰、服装配色和脸部特写/表情参考或降级方案",
            )
        if "近景身份锁定约束" not in section:
            add(BLOCK, "资产身份注册层", loc, "中文视频 prompt 缺近景身份锁定约束；配角近景需限制低幅度表情/转头，必要时降级 MCU/OTS/侧脸")
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
    if "模型路由约束" not in section:
        add(BLOCK, "模型路由", loc, "中文视频 prompt 缺模型路由约束；必须说明按 primary_backend 写平台参数，失败才切 fallback/degrade_plan")
    if _section_requires_motion_control(section):
        if not (_has_field(section, "Motion Control") or _has_field(section, "物理交互控制")):
            add(BLOCK, "Motion Control", loc, "高危物理接触镜头缺 Motion Control / 物理交互控制字段；必须继承 route.motion_control 和 manifest_path")
        else:
            for key in ("level", "manifest_path", "required_inputs", "failure_modes"):
                if key not in section:
                    add(BLOCK, "Motion Control", loc, f"物理交互控制字段缺：{key}")
        if "物理交互约束" not in section:
            add(BLOCK, "Motion Control", loc, "中文视频 prompt 缺物理交互约束；必须说明姿态/深度/实例遮挡或按 degrade_plan 拆镜")
        if not _has_any(section, ("FeatureMelting", "feature_melting", "特征融化")):
            add(BLOCK, "Motion Control", loc, "生成后自检必须包含 FeatureMelting/特征融化检查项")
    if "原生音画策略" not in section:
        add(BLOCK, "原生音画", loc, "缺原生音画策略字段；每 Clip 必须写 audio_intent/risk/mouth_visible/speech_policy/compose_policy，默认丢弃")
    else:
        for key in ("audio_intent", "risk", "mouth_visible", "speech_policy", "compose_policy"):
            if key not in section:
                add(BLOCK, "原生音画", loc, f"原生音画策略缺字段：{key}")
        if _section_native_audio_opt_in(section):
            native_policy = _native_audio_policy_line(section)
            if not _has_any(section, ("risk=low", "低风险")):
                add(BLOCK, "原生音画", loc, "原生环境声/音效 opt-in 仅允许低风险镜头；必须写 risk=low / 低风险理由")
            if not _has_any(native_policy, ("mouth_visible=no", "无口型", "嘴部不可见")):
                add(BLOCK, "原生音画", loc, "原生环境声/音效 opt-in 必须确认无口型或嘴部不可见")
            if not _native_audio_contract_ok(section):
                add(BLOCK, "原生音画", loc, "原生环境声/音效 opt-in 必须明确 no_native_speech / 禁止原生人声")
    if "原生音画约束" not in section:
        add(BLOCK, "原生音画", loc, "中文视频 prompt 缺原生音画约束；必须说明默认禁止原生人声，或仅允许低风险环境声/动作音效")

    # ④ 运镜越界 trip-wire：镜头运动含"廉价漂浮/旋转飞行/急速"类运镜 → 疑越 style_contract.运动边界
    m_cam = re.search(r"镜头运动[：:]([^\n；;]*)", section)
    cam = m_cam.group(1) if m_cam else ""
    SUSPECT_MOVES = ("旋转", "360", "环绕飞", "飞行", "急速", "极速", "快速拉近", "急推", "急拉", "乱甩", "甩镜", "螺旋", "翻滚")
    hit = [w for w in SUSPECT_MOVES if w in cam]
    if hit:
        add(WARN, "运动一致性", loc,
            f"镜头运动含「{'/'.join(hit)}」，疑越本集运动边界——核对 `本集基础视觉风格契约/导演一致性契约` 的运动边界禁忌；如确需该运镜须有明确剧情理由（爽点/高光），否则换克制运镜")

    if "检查清单（视频三件套自查" not in section:
        add(BLOCK, "prompt", loc, "缺提交前检查清单")
    if "自检（生成后逐条过" not in section:
        add(BLOCK, "prompt", loc, "缺生成后自检段")


def _reference_block(section: str) -> str:
    m = re.search(r"(?ms)(?:\*\*)?参考图(?:\*\*)?.*?(?=^###\s+|^\*\*导演视角八维\*\*|^##\s+|\Z)", section)
    return m.group(0) if m else ""


def _section_has_character_refs(section: str) -> bool:
    refs = _reference_block(section)
    if "清空人物参考" in refs or "无需人物参考" in refs or "无人物" in section or "空镜" in section:
        return False
    # 场景/道具/VFX 纯空镜可没有角色锚点；含角色语义或人物定妆引用才按角色镜头卡。
    if _has_any(section, ("角色", "人物", "脸", "脸型", "发型", "服装", "妆造", "锚点句", "同一少女", "同一少年")):
        return True
    asset_names = re.findall(r"定妆_([^`\s，。、,）)]+)", refs)
    non_character_words = (
        "场景", "道具", "寝殿", "宫", "殿", "庭", "院", "山", "洞", "门", "廊",
        "床", "榻", "托盘", "光幕", "符纹", "剑气", "法宝", "特效", "阵", "丹炉",
        "雷", "火", "云", "光效", "地标",
    )
    return any(not _has_any(name, non_character_words) for name in asset_names)


def _character_names_in_refs(refs: str) -> set:
    """参考图块里引用的**角色**定妆基名集合（去形态变体后缀、排除场景/道具/特效）。"""
    non_char = (
        "场景", "道具", "寝殿", "宫", "殿", "庭", "院", "山", "洞", "门", "廊", "道",
        "床", "榻", "托盘", "光幕", "符纹", "剑气", "法宝", "特效", "阵", "丹炉", "炉",
        "雷", "火", "云", "光效", "地标", "花田", "花", "米饼", "灯", "剪影",
    )
    names = set()
    for raw in re.findall(r"定妆_([^`\s，。、,）)]+)", refs):
        if raw.endswith(".png"):
            raw = raw[:-4]
        base = re.sub(
            r"_(侧|半身|全身|背|三视图|设定表|表情|脸部特写|头部特写|面部特写|局部|近景|特写)$",
            "",
            raw,
        )
        if base and not _has_any(base, non_char):
            names.add(base)
    return names


def _needs_closeup_identity_lock(section: str, name: str) -> bool:
    """Reaction/reverse-shot close-ups need finer identity locks than generic anchors.

    Plain reference-group generation often preserves a character *type* but
    redraws face shape, hair bun, or accessories in tight reaction shots.  Keep
    this check scoped to dialogue/reaction close-ups so ordinary medium shots
    are not over-gated.
    """
    focused_lines = "\n".join(
        line for line in section.splitlines()
        if _has_any(line, ("专项镜头模板", "镜头", "①", "template", "shot_type", "导演意图"))
    )
    blob = f"{name}\n{focused_lines}"
    return _has_any(blob, (
        "dialogue_shot_reverse",
        "正反打",
        "反打",
        "过肩",
        "反应镜",
        "表情镜",
        "逼问",
        "假面",
    ))


def _has_closeup_identity_lock(section: str) -> bool:
    has_lock_field = _has_any(section, (
        "近景/反打身份锁定",
        "近景身份锁定",
        "反打身份锁定",
        "细粒度身份锁定",
        "脸部特写",
        "_表情",
    ))
    has_face_detail = _has_any(section, ("脸型", "五官比例", "圆润脸", "窄长", "薄唇", "眼型"))
    has_hair_detail = _has_any(section, ("发型", "发髻", "高圆髻", "发簪", "发饰", "配饰", "头饰"))
    return has_lock_field and has_face_detail and has_hair_detail


def _has_i2i_tail_continuity_lock(section: str) -> bool:
    has_method = _has_any(section, (
        "image2image",
        "image-to-image",
        "图生图",
        "母图",
        "同镜首帧",
        "上一张成图",
        "上一帧成图",
        "前一张成图",
        "尾帧接力生成方式",
    ))
    forbids_text_only = _has_any(section, (
        "不得纯文生图",
        "禁止纯文生图",
        "不纯文生图",
        "不要纯文重抽",
        "不能纯文字重抽",
        "不得纯文字重抽",
    ))
    return has_method and forbids_text_only


def _has_character_id_binding(section: str) -> bool:
    """Character shots must bind concrete registry IDs, not just prose names."""
    return bool(re.search(r"`?CHAR_[A-Za-z0-9_]+/[^`\s；;，,]+`?", section))


def _multi_char_binding_ambiguity(section: str) -> Optional[List[str]]:
    """同框 ≥2 个注册角色但未星标 primary（`CHAR_xx*`）→ 返回角色 ID 列表；否则 None。

    多数后端单图主体锁只支持 1 个主体——不声明锁谁=后端随机挑，同框崩脸不可追责。
    规则出处：n2d-image/references/资产身份注册层.md「多角色同框绑定规则」。纯函数·可测。
    """
    ids = sorted({m.split("/")[0].rstrip("*") for m in re.findall(r"CHAR_[A-Za-z0-9_]+(?:/[^\s`；;，,]*)?", section)})
    if len(ids) < 2:
        return None
    if re.search(r"CHAR_[A-Za-z0-9_]+(?:/[^\s`；;，,]*?)?\*", section):
        return None
    return ids


def _has_asset_id_binding(section: str, prefix: str) -> bool:
    return bool(re.search(rf"`?{re.escape(prefix)}[A-Za-z0-9_]+`?", section))


def _needs_scene_asset_binding(refs: str) -> bool:
    return _has_any(refs, (
        "场景定妆",
        "场景锚",
        "定妆_冷宫寝殿",
        "定妆_场景",
    ))


def _needs_prop_asset_binding(refs: str) -> bool:
    return _has_any(refs, (
        "道具定妆",
        "定妆_斑驳铜镜",
        "定妆_赐死托盘",
        "定妆_毒酒碎瓷",
    ))


def _has_standard_character_turnaround(section: str) -> bool:
    """角色定妆必须具备标准正/侧/背三视图口径。"""
    has_front = _has_any(section, ("正面", "正脸", "主参考", "定妆_<角色>.png"))
    has_side = _has_any(section, ("_侧", "侧面", "侧脸"))
    has_back = _has_any(section, ("_背", "背面", "背身"))
    has_board = _has_any(section, ("_三视图", "标准三视图", "正/侧/背", "正面 / 侧面 / 背面"))
    return has_front and has_side and has_back and has_board


def _uses_halfbody_outfit_ref(section: str) -> bool:
    return _has_any(section, ("_半身", "半身服装", "半身参考", "半身.png", "半身图"))


def _has_halfbody_crop_rule(section: str) -> bool:
    """半身服装参考必须是正面主参考裁切放大，不能补底占位，且主体居中。

    作用域铁律：本规则（含「主体居中」）只针对**定妆照 / 共享定妆库的半身服装参考图**
    （仅 check_common_image_prompts 的 角色定妆.md 调用）。正式剧情**分镜图按导演构图与
    运镜处理、不强制居中**——绝不要把本检查接进 check_image_shot_prompt_section。"""
    has_source = _has_any(section, (
        "从已通过自检的正面主参考",
        "从已通过正面主参考",
        "从已通过的正面主参考",
        "从已通过正面图",
        "从正面主参考",
        "正面主参考裁切",
        "正面图裁切",
    ))
    has_crop = _has_any(section, ("裁切", "裁剪", "crop"))
    has_resize = _has_any(section, ("放大", "重采样", "回 9:16", "回9:16", "9:16"))
    forbids_padding = _has_any(section, (
        "不得用白底",
        "不要用白底",
        "禁止白底",
        "白底/浅灰底/空白",
        "空白补",
        "补满下半截",
        "补下半截",
        "补底",
        "纯色补底",
    ))
    has_centering = _has_any(section, (
        "人物主体居中",
        "人物居中",
        "主体居中",
        "居中裁切",
        "居中重裁",
        "头身中线",
        "画面中线",
        "左右留白",
        "留白基本均衡",
    ))
    return has_source and has_crop and has_resize and forbids_padding and has_centering


def _has_prop_structure_rule(section: str) -> bool:
    """关键道具必须锁结构唯一性，避免模型把描述词误画成新增部件。"""
    return _has_any(section, (
        "结构唯一性",
        "道具结构",
        "结构不幻觉",
        "件数锁定",
        "数量锁定",
        "三件套数量锁定",
        "唯一圆口",
        "唯一短颈",
        "一个圆口",
        "一个短颈圆口",
        "只有一个短颈圆口",
        "一个正常圆口",
        "无侧嘴",
        "无斜嘴",
        "无双口",
        "无多口",
        "无额外壶嘴",
        "无额外开口",
        "无重复瓶口",
        "无出酒嘴",
        "无管状嘴",
        "一柄一刃",
        "只有一柄一刃",
        "无多刃",
        "无双刃",
        "单镜面",
        "无多镜面",
        "不多镜面",
        "无重复镜框",
    ))


def _needs_prop_structure_gate(section: str, name: str, refs: str) -> bool:
    """只卡重道具镜头，避免普通场景里一句“托盘/铜镜”造成全剧误伤。"""
    heavy_title_or_refs = _has_any(
        f"{name}\n{refs}",
        (
            "赐死三件套",
            "毒酒碎裂",
            "定妆_赐死托盘",
            "定妆_毒酒碎瓷",
        ),
    )
    risky_wording = _has_any(section, (
        "毒酒壶",
        "白瓷毒酒壶",
        "毒酒瓷壶",
        "壶嘴",
        "白绫",
        "匕首",
        "短匕首",
        "赐死托盘",
        "赐死三件套",
    ))
    return heavy_title_or_refs or risky_wording


def check_image_shot_prompt_section(path: str, idx: int, section: str) -> None:
    name = _headline(section, f"镜头 {idx}")
    loc = f"{path} {name}"

    if "检查清单（八维自查" not in section:
        add(BLOCK, "prompt", loc, "缺提交前检查清单（八维自查·最易漏②机位/⑥光影/⑦张力）")
    if "**自检**" not in section and "逐镜自检" not in section and "自检（生成后逐张过" not in section:
        add(BLOCK, "prompt", loc, "缺生成后逐张自检段")
    if "重抽预算" not in section:
        add(BLOCK, "prompt", loc, "缺重抽预算字段；无法按主要人物/关键镜策略收口")
    if "正向 prompt（中文）" not in section:
        add(BLOCK, "prompt", loc, "缺正向 prompt（中文）")
    if "正向 prompt（英文）" not in section:
        add(BLOCK, "prompt", loc, "缺正向 prompt（英文）兜底")
    if "负向 prompt" not in section:
        add(BLOCK, "prompt", loc, "缺负向 prompt；人物/场景堵漏不可控")
    elif "风格禁忌" not in section:
        add(BLOCK, "风格一致性", loc, "负向 prompt 未继承 style_contract.风格禁忌；风格禁忌只在契约不进逐镜负向=shot 级防不住风格漂（突然照片感/插画/高饱和），须把本集风格禁忌拼进本镜负向")
    if "导演视角八维" not in section:
        add(BLOCK, "prompt", loc, "缺导演视角八维表；分镜图不能只写画师式描述")

    if not _has_field(section, "光位锚"):
        add(BLOCK, "光影一致性", loc, "缺光位锚字段；同场跨镜主光方向/色温/动机光源会飘，剪起来闪——须继承 00_总览 本场光位锚")
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
        if _needs_prop_asset_binding(refs) and not _has_asset_id_binding(section, "PROP_"):
            add(
                BLOCK,
                "资产引用注册层",
                loc,
                "参考图块含关键道具定妆但缺 PROP_xx 绑定；必须写 `资产引用注册层` 并引用 asset_registry.json，锁道具结构、件数和禁漂项。",
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
        if not re.search(r"(锚点句|anchor phrase)\s*[:：]", section, re.IGNORECASE):
            add(BLOCK, "角色一致性", loc, "含角色镜头缺锚点句；每镜必须拼角色卡锚点")
        if not _has_field(section, "视线方向"):
            add(BLOCK, "轴线一致性", loc, "含角色镜头缺视线方向；轴线/视线在出图阶段焊进像素、出视频改不动，正反打会穿帮——须对位 00_总览 本场轴线")
        if not _has_any(section, ("脸型与定妆一致", "角色脸/妆造未漂移", "脸/妆造未漂移", "妆造未漂移")):
            add(BLOCK, "角色一致性", loc, "含角色镜头自检未显式检查脸/妆造漂移")
        if not _has_any(section, ("服装配色一致", "服装", "配色")):
            add(BLOCK, "角色一致性", loc, "含角色镜头未显式锁服装/配色")
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
        if "_侧" not in refs and "_半身" not in refs and "_全身" not in refs and "主体库" not in section and "角色ID" not in section:
            add(WARN, "角色一致性", loc, "含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂")
        chars = _character_names_in_refs(refs)
        if len(chars) >= 2 and not _has_any(section, ("多参考", "主体库", "角色ID", "分别出图", "Seedream", "Nano Banana")):
            add(WARN, "角色一致性", loc,
                f"单镜多角色同框（{'/'.join(sorted(chars))}）：单图参考后端(如 Codex)难保多人各自一致——"
                "优先切官方多参考后端(Seedream 14图/Nano Banana Pro 5人/可灵主体库/Sora Cameo)或走「分别出图+合成」并登记降级")


def check_common_image_prompts(root: str) -> None:
    prompt_dir = shared_asset_path(root, "prompt")
    if not os.path.isdir(prompt_dir):
        add(BLOCK, "共享定妆", prompt_dir, "缺共享定妆 prompt 目录")
        return
    for filename in ("角色定妆.md", "场景定妆.md", "道具定妆.md", "法宝定妆.md", "特效定妆.md"):
        p = os.path.join(prompt_dir, filename)
        if not os.path.isfile(p):
            continue
        text = open(p, encoding="utf-8").read()
        sections = re.findall(r"(?ms)^##\s+.*?(?=^##\s+|\Z)", text)
        for i, sec in enumerate(sections, 1):
            name = _headline(sec, f"{filename} block#{i}")
            loc = f"{p} {name}"
            if "目标存档" not in sec:
                add(BLOCK, "共享定妆", loc, "缺目标存档；共享资产无法归档追踪")
            if "正向 prompt（中文）" not in sec:
                add(BLOCK, "共享定妆", loc, "缺正向 prompt（中文）")
            if "正向 prompt（英文）" not in sec:
                add(BLOCK, "共享定妆", loc, "缺正向 prompt（英文）")
            if "负向 prompt" not in sec:
                add(BLOCK, "共享定妆", loc, "缺负向 prompt")
            if "检查清单（定妆自查" not in sec:
                add(BLOCK, "共享定妆", loc, "缺定妆提交前检查清单")
            if "自检（生成后逐张过" not in sec and "**自检**" not in sec:
                add(BLOCK, "共享定妆", loc, "缺生成后落档自检段")
            if filename == "道具定妆.md" and not _has_prop_structure_rule(sec):
                add(BLOCK, "道具结构", loc, "道具定妆缺关键道具结构唯一性闸门；需锁唯一圆口/短颈、无侧嘴/斜嘴/双口/额外开口、多刃/多镜面/件数错等，避免道具结构幻觉")
            if filename == "角色定妆.md":
                if "身份注册" not in sec and "identity_registry" not in sec:
                    add(BLOCK, "资产身份注册层", loc, "角色定妆缺身份注册字段；必须指向 `出图/共享/identity_registry.json` 对应 characters[].forms[]")
                if "角色定妆组" not in sec:
                    add(BLOCK, "角色一致性", loc, "角色定妆缺定妆组说明；核心角色不能只靠单张正脸")
                if not _has_standard_character_turnaround(sec):
                    add(BLOCK, "角色三视图", loc, "人物定妆必须是标准三视图：正面主参考 + 侧面参考 + 背面参考 + `定妆_<角色>_三视图.png` 人审拼版；不得只出正脸/半身或把背面按需省略")
                if _uses_halfbody_outfit_ref(sec) and not _has_halfbody_crop_rule(sec):
                    add(BLOCK, "服装参考", loc, "半身服装参考必须写明：`定妆_<角色>_半身.png` 从已通过自检的正面主参考裁切并放大/重采样回 9:16；人物主体居中、头身中线接近画面中线、左右留白基本均衡；不得新抽半身导致脸漂，也不得用白底/浅灰底/空白补下半截")
                if "锚点" not in sec:
                    add(BLOCK, "角色一致性", loc, "角色定妆缺锚点字段；下游每镜无锚可拼")


def check_shared_image_index(root: str, ep: str) -> None:
    overview = os.path.join(root, "出图", ep, "prompt", "00_总览.md")
    index = shared_asset_path(root, "prompt", "00_索引.md")
    if not os.path.isfile(overview):
        add(BLOCK, "出图", overview, "缺本集出图总览")
        return
    if not os.path.isfile(index):
        add(BLOCK, "出图", index, "缺共享定妆索引")
        return
    common_dir = shared_asset_dir(root)
    index_text = open(index, encoding="utf-8").read()
    for ln in index_text.splitlines():
        if not ln.strip().startswith("|") or "✅" not in ln:
            continue
        paths = re.findall(r"`([^`]+\.png)`", ln)
        for rel in paths:
            if os.path.isabs(rel):
                full = rel
            else:
                # 路径可能是「作品根相对」(出图/共享/图片/定妆_X.png) 或「共享目录相对」(定妆_X.png)；两种都试
                cand_root = os.path.join(root, rel)
                cand_common = os.path.join(common_dir, rel)
                if os.path.exists(cand_root):
                    full = cand_root
                elif rel.startswith("_") and glob.glob(os.path.join(common_dir, f"*{rel}")):
                    continue
                else:
                    full = cand_common
            if not os.path.exists(full):
                add(BLOCK, "共享定妆", index, f"索引标 ✅ 但 PNG 不存在：{rel}")
    overview_text = open(overview, encoding="utf-8").read()
    missing = []
    in_table = False
    for ln in overview_text.splitlines():
        if ln.startswith("## 共享定妆就绪状态"):
            in_table = True
            continue
        if in_table and ln.startswith("## "):
            break
        if in_table and ln.strip().startswith("|") and "⬜" in ln:
            missing.append(ln.strip())
    if missing:
        add(BLOCK, "共享定妆", overview, f"本集引用的共享定妆仍有未完成项：{missing[0][:120]}")


_FINALIZE_CHAR_RE = re.compile(r"CHAR_[A-Za-z0-9_]+(?:/[^\s`，；、*]+)?")
_FINALIZE_ASSET_RE = re.compile(r"(?:LOC|PROP|OUTFIT|VFX)_[A-Za-z0-9_]+")


def _finalize_tracked_map(root: str) -> Dict[str, bool]:
    """registry 里**显式登记了** `self_check_passed` 的 form/asset → {引用键: passed}。

    机器可读的 finalize 真值（补 `00_索引.md` 的人读 ✅）：键缺失 = 未启用追踪（向后兼容/先出视频 demo
    天然豁免，不入表）。角色 form 同时登记 `CHAR_xx/形态` 与（单形态时）裸 `CHAR_xx` 两个键。"""
    tracked: Dict[str, bool] = {}
    try:
        reg = json.loads(open(os.path.join(root, "出图", "共享", "identity_registry.json"), encoding="utf-8").read())
        for c in (reg.get("characters") or []):
            cid = str(c.get("id") or "").strip()
            forms = c.get("forms") or []
            for fm in forms:
                if not isinstance(fm, dict) or "self_check_passed" not in fm:
                    continue
                passed = bool(fm.get("self_check_passed"))
                form_name = str(fm.get("form") or "").strip()
                if cid and form_name:
                    tracked[f"{cid}/{form_name}"] = passed
                if cid and len(forms) == 1:
                    tracked[cid] = passed
    except Exception:
        pass
    try:
        areg = json.loads(open(os.path.join(root, "出图", "共享", "asset_registry.json"), encoding="utf-8").read())
        for a in (areg.get("assets") or []):
            if not isinstance(a, dict) or "self_check_passed" not in a:
                continue
            aid = str(a.get("id") or "").strip()
            if aid:
                tracked[aid] = bool(a.get("self_check_passed"))
    except Exception:
        pass
    return tracked


def check_referenced_assets_finalized(root: str, ep: str) -> None:
    """付费出图前置·机器可读 finalize 闸门：本集逐镜引用的共享定妆/资产，若 registry 显式标
    `self_check_passed=false`（自检未过的"脏定妆"）→ BLOCK。补 `check_shared_image_index` 只拦 ⬜
    的缺口（⏳ 漏网）+ 总览表没列就静默放行的软肋——改查机器真值，不依赖手维护的人读表。

    **纯 opt-in**：registry 没登记 `self_check_passed` 字段 = 未启用追踪 → 跳过（向后兼容，现有作品/
    先出视频 demo 不会被突然阻断）。键=true 放行、=false 且被引用=block。"""
    tracked = _finalize_tracked_map(root)
    if not tracked:
        return  # 未启用机器 finalize 追踪：保持 00_索引 人读 ✅ 的既有流程，不强加
    shots_md = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
    try:
        text = open(shots_md, encoding="utf-8").read()
    except Exception:
        return  # 逐镜 prompt 未写：check_image_prompt_overview 等各自负责
    referenced = set(_FINALIZE_CHAR_RE.findall(text)) | set(_FINALIZE_ASSET_RE.findall(text))
    unfinalized = sorted(rid for rid in referenced
                         if rid in tracked and tracked[rid] is False)
    # 裸 CHAR_xx 引用对应多形态时，逐形态查（任一形态显式 false 且被引用基名）
    for rid in sorted(referenced):
        base = rid.split("/")[0]
        if rid == base and base not in tracked:
            bad = [k for k, v in tracked.items() if k.startswith(base + "/") and v is False]
            if bad and base not in unfinalized:
                unfinalized.extend(bad)
    for rid in sorted(set(unfinalized)):
        add(BLOCK, "共享定妆", shots_md,
            f"本集逐镜引用了未过落档自检的共享定妆/资产 `{rid}`（registry `self_check_passed=false`）——"
            "脏定妆是锚点，脸/结构漂了下游每镜继承；先过自检并把该项置 true（或人工复核后 `image_qc --mark-finalized`），再付费出图。")


def check_image_assets(root: str, ep: str) -> None:
    if not progress_fraction_done(root, ep, "出图"):
        add(BLOCK, "出图", os.path.join(root, "_进度.md"), "出图列未满，不能进入出视频")
    png_dir = os.path.join(root, "出图", ep, "图片")
    pngs = glob.glob(os.path.join(png_dir, "*.png"))
    if not pngs:
        add(BLOCK, "出图", png_dir, "本集没有分镜 PNG")


# 近景/特写景别标记（脸占画面主体、表情漂移=脸重画最致命的镜）。
_CLOSEUP_MARKERS = (
    "CU", "ECU", "MCU", "BCU", "特写", "近景", "脸部", "面部",
    "反打", "正反打", "过肩", "OTS", "dialogue_shot_reverse", "dialogue_closeup",
)


def _clip_is_closeup(clip: Dict[str, Any]) -> bool:
    """clip 是否为近景/特写/反打（脸占主体）：扫 template + label + shots[].lens/desc 的景别标记。

    用于「大表情近景必须首尾双帧」闸门——把 expression_span=大 收口到真正的脸戏，避免误伤
    远景/空镜被误标 大 的镜。纯函数·可测。"""
    blob = " ".join(str(clip.get(k) or "") for k in ("template", "label"))
    for shot in clip.get("shots") or []:
        if isinstance(shot, dict):
            blob += " " + " ".join(str(shot.get(k) or "") for k in ("lens", "desc"))
    return _has_any(blob, _CLOSEUP_MARKERS)


def check_expression_span_frame_contract(root: str, ep: str) -> None:
    """出视频前置（脸被表情带着重画的头号根因·机检闸门）：跨情绪近景必须走首尾双帧只插值工艺。

    `prompt_format.md`「近景大表情变化类 Clip」铁律：表情跨度=大（平静→爆哭/隐忍→暴怒）的 CU/MCU/反打镜
    若靠单首帧让模型自由生成中间表情，脸型/五官比例会随表情拉伸漂移、剪起来像换了个人。此前
    `表情跨度` 只活在总览风险表里、是人读自检——gate 看不见、拦不住。本检查把它结构化（storyboard
    `continuity.expression_span` ∈ {微,中,大}）后机检：

      · expression_span 值非法（非 微/中/大）→ BLOCK（typo 防呆）；
      · expression_span=大 且镜为近景/特写/反打 → 必须 need_endframe=true（有止表情尾帧可插值），
        否则 BLOCK——单首帧扛不住跨情绪表情；
      · expression_span=大 但镜非近景 → WARN（远景大表情风险低，或景别标错，提示复核）。

    纯 opt-in：`continuity.expression_span` 缺失=未启用追踪→跳过（现有 demo/未标镜不误伤），与
    `self_check_passed`、`midframe_default` 同款门控。路由后端能否真消费这条尾帧（frames2video/
    multiframe）由 `check_route_frame_capability` 对高风险镜升 BLOCK 兜，本检查不重复报。"""
    data = load_json(storyboard_path(root, ep))
    if not isinstance(data, dict) or not isinstance(data.get("clips"), list):
        return  # storyboard 缺失/损坏由 check_storyboard_contract 负责
    for i, clip in enumerate(data["clips"], 1):
        if not isinstance(clip, dict):
            continue
        cont = clip.get("continuity")
        if not isinstance(cont, dict):
            continue
        span = cont.get("expression_span")
        if span in (None, ""):
            continue  # opt-in：未声明=不追踪
        loc = f"{storyboard_path(root, ep)} clip#{i}"
        if span not in EXPRESSION_SPAN_VALUES:
            add(BLOCK, "表情一致性", loc,
                f"continuity.expression_span={span!r} 非法；必须是 {'/'.join(EXPRESSION_SPAN_VALUES)} 之一"
                "（大=跨情绪如 平静→爆哭/隐忍→暴怒）。")
            continue
        if span != EXPRESSION_SPAN_BIG:
            continue
        if not _clip_is_closeup(clip):
            add(WARN, "表情一致性", loc,
                "expression_span=大 但本镜景别未识别为近景/特写/反打——跨情绪大表情通常是脸戏；"
                "若确为远景/空镜风险较低，否则复核景别或下调跨度档。", return_to_stage="script_stage2")
            continue
        if cont.get("need_endframe") is not True:
            add(BLOCK, "表情一致性", loc,
                "expression_span=大 的近景/特写/反打镜必须 need_endframe=true 走「首尾双帧只插值」"
                "（首=起表情、尾=止表情同源定妆，mode=frames2video，让模型只插值表情肌肉、不自由重画脸）；"
                "缺尾帧=单首帧硬扛跨情绪表情=脸型/五官比例随表情漂移。补 endframe_png（止表情定妆，"
                "如 `镜头N_expr_end.png` 或 reference_group.expressions 对应情绪图）或降级 MCU/OTS/侧脸后下调跨度档。",
                return_to_stage="image")


_VID_CLIP_HEAD_RE = re.compile(r"^##\s*Clip[_\s]*(\d+)", re.M)
_VID_FIRST_FRAME_RE = re.compile(r"\*\*首帧\*\*[^`]*`([^`]+\.png)`")
_VID_END_FRAME_RE = re.compile(r"\*\*尾帧\*\*[^`]*`([^`]+\.png)`")
# 匹配 `**中段锚帧**`（单锚帧）和 `**锚帧K**`（N 锚帧链）两种 prompt 字段
_VID_MID_FRAME_RE = re.compile(r"\*\*(?:中段)?锚帧\s*\d*\*\*[^`]*`([^`]+\.png)`")


def check_video_prompt_frames(root: str, ep: str) -> None:
    """付费出视频前置：核验**视频 prompt（`01_clips.md`）实际引用的首帧/尾帧 PNG**——这是 runner
    （`parse_prompt_pack`）真正喂给后端的路径，与 `storyboard.firstframe_png` 分开誊抄、可能漂；
    `check_storyboard_contract` 查的是 storyboard 字段，这里查**真正提交的那条路径**，互补不重复。
      · 首帧 PNG 缺失 → BLOCK（image2video 必失败、白扣一次最贵的钱）；
      · 声明了尾帧但 PNG 缺失 → WARN（双帧接力降级为单首帧，大表情近景有脸重画风险）；
      · storyboard 标 `need_endframe=true` 但视频 prompt 该 Clip 漏写 `**尾帧**` → WARN（双帧意图誊抄时丢了）；
      · storyboard 声明 `continuity.midframe` 但视频 prompt 该 Clip 漏写 `**中段锚帧**`、或引用的
        锚帧 PNG 缺失 → WARN（拆段意图誊抄时丢失/锚帧漂，runner 会按单段出，中段漂移风险回归）；
      · 视频 prompt 引用的首帧路径 ≠ storyboard.firstframe_png（两侧都存在但不是同一张）→ BLOCK
        （誊抄成另一张存在的 PNG，两侧各查存在全绿、却动了错的首帧）；尾帧不一致 → WARN。"""
    p = os.path.join(root, "出视频", ep, "prompt", "01_clips.md")
    if not os.path.exists(p):
        return  # 视频 prompt 缺失由 check_video_prompt_overview 负责
    text = open(p, encoding="utf-8").read()
    need_end: Dict[int, bool] = {}
    need_mid: Dict[int, int] = {}  # Clip → 声明的锚帧数（midframe=1；anchors=len）
    sb_first: Dict[int, str] = {}  # Clip → storyboard.firstframe_png（路径相等校验基准）
    sb_end: Dict[int, str] = {}    # Clip → storyboard.continuity.endframe_png
    sb = load_json(storyboard_path(root, ep))  # 只读取 need_endframe/midframe/anchors/首尾帧，不重复报 storyboard 缺失
    if isinstance(sb, dict) and isinstance(sb.get("clips"), list):
        for i, clip in enumerate(sb["clips"], 1):
            if isinstance(clip, dict) and isinstance(clip.get("continuity"), dict):
                cont = clip["continuity"]
                need_end[i] = cont.get("need_endframe") is True
                if isinstance(cont.get("midframe"), dict):
                    need_mid[i] = 1
                elif isinstance(cont.get("anchors"), list):
                    need_mid[i] = len(cont["anchors"])
                if clip.get("firstframe_png"):
                    sb_first[i] = str(clip["firstframe_png"]).strip()
                if cont.get("endframe_png"):
                    sb_end[i] = str(cont["endframe_png"]).strip()

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
            add(WARN, "尾帧", loc,
                f"视频 prompt 声明了尾帧但 PNG 不存在：{em.group(1).strip()}——双帧接力会降级为单首帧"
                "（大表情近景有脸重画风险），先补尾帧或确认降级。", return_to_stage="image")
        elif em and num in sb_end and not _missing(em.group(1).strip()) \
                and not _same_path(em.group(1).strip(), sb_end[num]):
            add(WARN, "尾帧", loc,
                f"视频 prompt 尾帧引用 `{em.group(1).strip()}` ≠ storyboard.endframe_png `{sb_end[num]}`——"
                "誊抄漂成另一张尾帧=双帧插值的落点错，接缝/大表情近景插到错的止帧。确认是有意改写否则改回。",
                return_to_stage="video")
        elif em is None and need_end.get(num):
            add(WARN, "尾帧", loc,
                "storyboard 标 need_endframe=true 但视频 prompt 此 Clip 漏写 `**尾帧**` 引用——"
                "双帧接力意图在誊抄时丢失，runner 会按单首帧出，大表情近景有脸重画风险。",
                return_to_stage="image")
        mids = _VID_MID_FRAME_RE.findall(block)
        for rel in mids:
            if _missing(rel.strip()):
                add(WARN, "中段锚帧", loc,
                    f"视频 prompt 声明了锚帧但 PNG 不存在：{rel.strip()}——拆段接力会降级"
                    "（opt-in 的中段漂移风险回归），先补 `_mid`/`_aK` 锚帧或确认降级。", return_to_stage="image")
        declared = need_mid.get(num, 0)
        if len(mids) < declared:
            add(WARN, "中段锚帧", loc,
                f"storyboard 声明了 {declared} 个锚帧（continuity.midframe/anchors）但视频 prompt 此 Clip 只引用了 {len(mids)} 个"
                "`**中段锚帧**`/`**锚帧K**`——拆段意图在誊抄时丢失，runner 会按少段出，付了出图成本却没拿到中段锚定。",
                return_to_stage="video")


def check_input_frame_qc(root: str, ep: str) -> None:
    """出视频前置（省最贵那一步的钱）：图生视频是 n2d 最贵工位，image2video 会**忠实把首帧缺陷动起来**——
    崩脸的首帧 → 崩脸的片。所以付费出视频前先确认输入首帧已过出图落档机检 `image_qc`。
    读持久化结果（`生产数据/image_qc/<ep>/image_qc_<ep>.json`），**不重跑像素引擎**（每 Clip 提交都重跑太贵）：
      · `summary.hard_blocks>0`（崩脸 / 接缝断 / 降级精度近景 / 非法 CHAR）→ BLOCK，回 n2d-image 修复 + 重跑 QC；
      · 无 image_qc 结果 / 旧版 image_qc 无角色脸覆盖结果 → BLOCK；
      · `qc_environment.precision_level!=full` → BLOCK（降级精度不得进入 video）；
      · 角色脸定妆比对覆盖缺口 → BLOCK；
      · image_qc 结果早于最新 PNG（出图后改过帧没重验）→ BLOCK。"""
    png_dir = os.path.join(root, "出图", ep, "图片")
    pngs = glob.glob(os.path.join(png_dir, "*.png"))
    if not pngs:
        return  # check_image_assets 已 BLOCK「本集没有分镜 PNG」
    qc_path = os.path.join(root, "生产数据", "image_qc", ep, f"image_qc_{ep}.json")
    prohibited = _prohibited_face_patch_outputs(root, ep)
    if prohibited:
        sample = "、".join(p["png"] for p in prohibited[:5])
        more = f" 等 {len(prohibited)} 张" if len(prohibited) > 5 else ""
        add(BLOCK, "出图落档QC", _production_events_path(root),
            f"{PROHIBITED_FACE_PATCH_LABEL}：发现 {len(prohibited)} 张最新 image 落档事件来自本地贴脸/换脸/裁脸贴回画面"
            f"（{sample}{more}）。embedding 分数只是证据，不是目标；不能为了过脸部 embedding QC 把定妆脸盖到镜头上。"
            "这些图不能进 video，必须回 n2d-image 用真实重抽或官方 image2image 派生替换，并重跑 image_qc。",
            return_to_stage="image")
        return
    qc = load_json(qc_path)
    if not isinstance(qc, dict):
        add(BLOCK, "出图落档QC", qc_path,
            "出视频前未见 image_qc 落档机检结果——输入首帧的崩脸/降级精度近景未经核验。"
            "先跑 `dashboard gate --stage image`（或 `image_qc.py`）再出视频，别花图生视频的钱动画一张未验首帧。",
            return_to_stage="image")
        return
    hard = int((qc.get("summary") or {}).get("hard_blocks") or 0)
    if hard > 0:
        add(BLOCK, "出图落档QC", qc_path,
            f"输入首帧 image_qc 仍有 {hard} 项硬阻断（崩脸/接缝断/降级精度近景/非法 CHAR）——"
            "图生视频会忠实把这些缺陷动起来，是最贵工位上的纯浪费。先回 n2d-image 修复并重跑 image_qc 再出视频。",
            return_to_stage="image")
        return
    coverage = qc.get("face_reference_coverage")
    if not isinstance(coverage, dict):
        add(BLOCK, "出图落档QC", qc_path,
            "输入首帧 image_qc 是旧版结果，缺 `face_reference_coverage` 逐镜角色脸定妆比对覆盖证据。"
            "重跑 image_qc，确认每张已落档角色 PNG 都逐张对定妆/身份主参考过 full QC 后再出视频。",
            return_to_stage="image")
        return
    env = qc.get("qc_environment") or {}
    precision = str(env.get("precision_level") or "")
    if precision != "full":
        add(BLOCK, "出图落档QC", qc_path,
            f"输入首帧 image_qc 精度为 `{precision or 'unknown'}`，不是 full——"
            "含角色镜头图必须用 full 精度脸部参考比对后才能进 video；补 insightface/onnxruntime/buffalo_l 后重跑 image_qc。",
            return_to_stage="image")
        return
    missing = coverage.get("missing") or []
    if coverage.get("verdict") == "block" or missing:
        add(BLOCK, "出图落档QC", qc_path,
            f"角色脸定妆比对覆盖未过：{len(missing)} 张已落档角色图缺 full 比对/未通过比对。"
            "这是进入 video 的硬闸门；回 n2d-image 补检、重抽或修复后重跑 image_qc。",
            return_to_stage="image")
        return
    try:
        if max(os.path.getmtime(p) for p in pngs) > os.path.getmtime(qc_path) + 1:
            add(BLOCK, "出图落档QC", qc_path,
                "输入首帧晚于上次 image_qc（出图后改过帧未重验）——出视频前先重跑 image_qc，避免动画一张未验首帧。",
                return_to_stage="image")
    except OSError:
        pass


def ffprobe_json(path: str) -> Optional[dict]:
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
            text=True,
        )
        return json.loads(out)
    except Exception:
        return None


def duration(path: str) -> Optional[float]:
    data = ffprobe_json(path)
    if not data:
        return None
    try:
        return float(data.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        return None


def has_audio(path: str) -> Optional[bool]:
    data = ffprobe_json(path)
    if not data:
        return None
    return any(s.get("codec_type") == "audio" for s in data.get("streams", []))


def clip_files(root: str, ep: str) -> List[str]:
    return sorted(glob.glob(os.path.join(root, "出视频", ep, "视频", "*.mp4")))


def stripped_audio_artifacts(root: str, ep: str) -> List[str]:
    """Artifacts that show native clip audio was stripped during n2d-video.

    Source clips under 出视频/第N集/视频 must stay as AI platform originals.
    Compose may create no-audio working files under 合成/第N集/_clipcache, but
    those must not become the formal video-stage assets.
    """
    vid = os.path.join(root, "出视频", ep, "视频")
    if not os.path.isdir(vid):
        return []
    patterns = (
        "*.noaudio.mp4",
        "*_noaudio.mp4",
        "*-noaudio.mp4",
        "*no_audio*.mp4",
        "*silent*.mp4",
        "*无音轨*.mp4",
        "*静音*.mp4",
    )
    hits: List[str] = []
    for pattern in patterns:
        hits.extend(glob.glob(os.path.join(vid, pattern)))
    for dirname in ("_raw_with_audio", "raw_with_audio", "原片含音轨", "带音轨原片"):
        path = os.path.join(vid, dirname)
        if os.path.isdir(path):
            hits.append(path)
    return sorted(set(hits))


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


def voice_track_exists(root: str, ep: str) -> bool:
    voice_dir = os.path.join(root, "合成", ep, "配音")
    return any(os.path.isfile(os.path.join(voice_dir, name)) for name in ("voice_zh.wav", "voice_en.wav", "voice_zh_fitted.wav", "voice_en_fitted.wav"))


def voice_manifest_rows(root: str, ep: str) -> Optional[List[Dict[str, object]]]:
    path = manifest_path(root, ep)
    if not path:
        return None
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, list):
        return None
    return [row for row in data if isinstance(row, dict)]


def voiceover_role(role: str) -> bool:
    text = (role or "").strip()
    low = text.lower()
    return (
        "旁白" in text
        or "系统" in text
        or low in {"narrator", "voiceover", "system", "sys"}
    )


def voice_track_scope(root: str, ep: str) -> str:
    """Return none / voiceover_only / dialogue_or_unknown for compose double-voice policy."""
    if not voice_track_exists(root, ep):
        return "none"
    rows = voice_manifest_rows(root, ep)
    if not rows:
        return "dialogue_or_unknown"
    roles = [str(row.get("角色") or "").strip() for row in rows]
    if roles and all(role and voiceover_role(role) for role in roles):
        return "voiceover_only"
    return "dialogue_or_unknown"


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
                "原生音画：未显式设 视频原生音轨，compose 将自动「保留原片音轨」以免丢失原生台词（确需丢弃设 VIDEO_NATIVE_AUDIO_POLICY_EXPLICIT=1）")
        if overview_text:
            check_native_audio_opt_in_overview(root, ep, overview_text, overview)
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

    if mode == NATIVE_AUDIO_KEEP and voice_track_exists(root, ep):
        add(BLOCK, "原生音画", os.path.join(root, "合成", ep, "配音"), "`视频原生音轨=保留原片音轨` 且存在 n2d-voice 配音轨；正式合成会双人声，改为「低音量混入环境声」或「丢弃」")


def check_video_assets(root: str, ep: str) -> None:
    check_video_stage_raw_output_policy(root, ep)
    clips = clip_files(root, ep)
    if not clips:
        add(BLOCK, "视频", os.path.join(root, "出视频", ep, "视频"), "缺 clip MP4")
        return
    sb = load_storyboard(root, ep)
    if sb and len(clips) != len(sb.get("clips", [])):
        add(WARN, "视频", os.path.join(root, "出视频", ep, "视频"), f"clip 数 {len(clips)} 与 storyboard clips {len(sb.get('clips', []))} 不一致")
    audio_hits = [c for c in clips if has_audio(c)]
    check_native_audio_compose_policy(root, ep, audio_hits)
    shots = load_json(os.path.join(root, "脚本", ep, "镜头时长.json"))
    if isinstance(shots, dict):
        target = sum(float(v) for v in shots.values())
        actuals = [duration(c) for c in clips]
        if all(d is not None for d in actuals):
            total = sum(d for d in actuals if d is not None)
            if abs(total - target) > 1.0:
                add(WARN, "时长", ep, f"clip 总长 {total:.2f}s 与镜头时长累计 {target:.2f}s 差 {abs(total-target):.2f}s")


def check_compose_inputs(root: str, ep: str) -> None:
    check_video_assets(root, ep)
    check_placeholder_policy(root, ep, "compose")
    zh = os.path.join(root, "脚本", ep, "字幕_中文.srt")
    if not os.path.isfile(zh):
        # 原生音画：说话镜台词由视频后端原生生成、不跑逐句配音，finalize 也不产 SRT
        # （字幕走成片后 whisperx 词级对齐，见 n2d SKILL）——此处只提醒、不硬闸。
        if is_native_av_production(root):
            add(WARN, "字幕", zh, "原生音画：暂无中文字幕；成片后请用 whisperx 对原生台词做词级对齐再补字幕")
        else:
            add(BLOCK, "字幕", zh, "缺中文字幕")


def check_voice_conditioned_lipsync_policy(root: str, ep: str, storyboard: Dict[str, object]) -> None:
    """配音条件口型 (lipsync_condition_only) 校验：音轨必须丢弃原生，必须有 voice-first 轨。"""
    clips = storyboard.get("clips") or []
    lp_clips = [c for c in clips if isinstance(c, dict) and c.get("native_audio_policy") == "lipsync_condition_only"]
    if not lp_clips:
        return

    # lipsync_condition_only 模式下，模型音频只作口型参考，合成时必须丢弃
    policy = native_audio_policy(root)
    mode = native_audio_policy_mode(policy)
    if mode != NATIVE_AUDIO_DISCARD:
        add(BLOCK, "口型同步", os.path.join(root, "_设置.md"),
            f"检测到 {len(lp_clips)} 个 lipsync_condition_only 镜（后端音频参考口型），合成时必须「丢弃」模型原生音频，"
            f"否则会与主配音轨重叠。当前设置：视频原生音轨={policy}。")
    
    if not voice_track_exists(root, ep):
        add(BLOCK, "口型同步", os.path.join(root, "合成", ep, "配音"),
            f"检测到 {len(lp_clips)} 个配音条件口型镜，但未检测到主配音轨 (voice_zh.wav)；该模式依赖配音驱动口型，请先 n2d-voice。")


def _clip_label(value: Any) -> List[str]:
    labels: List[str] = []
    if isinstance(value, int):
        labels.append(f"Clip_{value:02d}")
    text = str(value or "")
    for m in re.finditer(r"(?i)(?:Clip|镜头|镜)\s*[_ -]?0*([0-9]+)", text):
        labels.append(f"Clip_{int(m.group(1)):02d}")
    out: List[str] = []
    for item in labels:
        if item not in out:
            out.append(item)
    return out


def _artifact_refs(text: str) -> List[str]:
    pattern = r"(?:出图|出视频|合成|脚本|设定库|合规)/[^\s，。；;|)）]+"
    out: List[str] = []
    for m in re.finditer(pattern, text or ""):
        item = m.group(0).rstrip("，。；;:：")
        if item not in out:
            out.append(item)
    return out


def _continuity_extra(row: Dict[str, Any], ep: str, default_stage: str,
                      default_scope: str, default_artifacts: Sequence[str]) -> Dict[str, object]:
    shots: List[str] = []
    for key in ("shot", "heading", "target", "png", "message", "loc"):
        shots.extend(_clip_label(row.get(key)))
    artifacts = list(default_artifacts)
    for key in ("source", "target", "png", "message", "loc"):
        artifacts.extend(_artifact_refs(str(row.get(key) or "")))
    png = str(row.get("png") or "")
    if png and "/" not in png:
        artifacts.append(f"出图/{ep}/图片/{png}")
    return {
        "return_to_stage": row.get("return_to_stage") or default_stage,
        "rerun_scope": row.get("rerun_scope") or default_scope,
        "affected_shots": sorted(set(shots)),
        "affected_artifacts": sorted(set(a for a in artifacts if a)),
    }


def _add_continuity_rows(dim: str, rows: Sequence[Dict[str, Any]], ep: str, *,
                         default_stage: str, default_scope: str,
                         default_artifacts: Sequence[str]) -> None:
    for row in rows:
        verdict = str(row.get("verdict") or "ok")
        if verdict not in {"block", "warn"}:
            continue
        sev = BLOCK if verdict == "block" else WARN
        loc = str(row.get("target") or row.get("source") or row.get("png") or row.get("heading") or dim)
        msg = str(row.get("message") or "一致性机检发现下游继承风险")
        missing = row.get("missing_terms")
        if missing:
            msg += "；缺：" + "、".join(str(x) for x in list(missing)[:8])
        add(sev, dim, loc, msg, **_continuity_extra(row, ep, default_stage, default_scope, default_artifacts))


def check_semantic_lineage(root: str, ep: str) -> None:
    res = semc.analyze(root, ep)
    _add_continuity_rows(
        "语义谱系(P0)",
        [r for r in res.get("findings", []) if isinstance(r, dict)],
        ep,
        default_stage="script_stage2",
        default_scope="修 storyboard→出图/出视频 prompt 的语义继承缺口；必要时重跑 n2d-script 阶段2。",
        default_artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt", f"出视频/{ep}/prompt"),
    )


def check_state_continuity(root: str, ep: str) -> None:
    res = statec.analyze(root, ep)
    _add_continuity_rows(
        "状态百科(P1)",
        [r for r in res.get("alerts", []) if isinstance(r, dict)],
        ep,
        default_stage="image",
        default_scope="修 visual_state_ledger / 出图分镜 prompt 的角色/道具状态锁；道具 lifecycle 未结构化的升级为 {states,transitions}；必要时回 storyboard / asset_registry 修状态演进。",
        default_artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt/01_分镜出图.md", "出图/共享/visual_state_ledger.json", "出图/共享/asset_registry.json"),
    )


def check_multimodal_continuity(root: str, ep: str) -> None:
    res = mmc.analyze(root, ep)
    _add_continuity_rows(
        "多模态(P2)",
        [r for r in res.get("shots", []) if isinstance(r, dict)],
        ep,
        default_stage="image",
        default_scope="按离群道具/场景/法宝参考组只重出受影响镜头；必要时补资产定妆 taxonomy。",
        default_artifacts=(f"出图/{ep}/prompt/01_分镜出图.md", f"出图/{ep}/图片"),
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


def run(root: str, ep: str, stage: str) -> None:
    if not os.path.isdir(root):
        add(BLOCK, "路径", root, "作品根不存在")
        return
    check_stage = gate_family(stage)
    av_native = is_native_av_production(root)  # 原生音画：说话镜不跑配音，不要求「配音」列就绪
    if check_stage == "image":
        check_compliance_manifest(root, ep, check_stage)
        # image 阶段只在「先出视频后配音」模式允许 rough timing 做 demo 出图；
        # 配音先行仍必须真实配音。不要把 rough 配音强写成 ✅。
        image_prereq = ("分镜设计",) if av_native else ("配音", "分镜设计")
        require_progress(root, ep, image_prereq)
        check_progress_artifact_signoff(root, ep, image_prereq)
        check_placeholder_policy(root, ep, check_stage)
        check_voiceover_fingerprint(root, ep)
        check_timing_manifest_complete(root, ep)
        check_image_ai_policy(root, ep)
        check_backend_reachable(root, ep)
        if stage == "image_preflight":
            check_drift_risk_advisories(root, ep)  # 出图前预案折进预检：一个入口拿齐阻断+预案
        check_identity_registry(root, require_reference_assets=False)
        check_costume_registry_reconcile(root)
        check_asset_reference_registry(root, require_reference_assets=False)
        check_storyboard_contract(root, ep, require_frame_assets=False)
        check_storyboard_visual_contract(root, ep)
        check_storyboard_style_contract(root, ep)
        check_cross_episode_style(root, ep)
        check_storyboard_special_templates(root, ep)
        check_image_prompt_overview(root, ep)
        check_prompt_checklists(root, ep, "image")
        check_semantic_lineage(root, ep)
        check_state_continuity(root, ep)
        check_shared_image_index(root, ep)
        check_referenced_assets_finalized(root, ep)
        check_common_image_prompts(root)
        check_cinematic_optical_continuity(root, ep)
        check_shot_scale_progression(root, ep)
        check_physical_scale_audit(root, ep)
    elif check_stage == "video":
        check_compliance_manifest(root, ep, check_stage)
        video_prereq = ("分镜设计", "出图prompt") if av_native else ("配音", "分镜设计", "出图prompt")
        require_progress(root, ep, video_prereq)
        check_progress_artifact_signoff(root, ep, video_prereq)
        check_placeholder_policy(root, ep, check_stage)
        check_voiceover_fingerprint(root, ep)
        referenced_characters, referenced_assets = episode_registry_reference_ids(root, ep)
        check_identity_registry(root, require_reference_assets=True, required_character_ids=referenced_characters)
        check_asset_reference_registry(root, require_reference_assets=True, required_asset_ids=referenced_assets)
        check_identity_adapter_matrix(root)
        check_route_identity_readiness(root, ep)
        check_storyboard_contract(root, ep, require_frame_assets=True)
        check_storyboard_style_contract(root, ep)
        check_storyboard_special_templates(root, ep)
        check_expression_span_frame_contract(root, ep)
        check_image_assets(root, ep)
        check_input_frame_qc(root, ep)
        check_video_prompt_frames(root, ep)
        check_multimodal_continuity(root, ep)
        check_prompt_checklists(root, ep, "video")
        check_video_stage_raw_output_policy(root, ep)
        check_contract_inheritance(root, ep)
        check_asset_handoff_inheritance(root, ep)
        check_semantic_lineage(root, ep)
        check_state_continuity(root, ep)
    elif check_stage == "compose":
        check_compliance_manifest(root, ep, check_stage)
        require_progress(root, ep, ("视频",))
        check_progress_artifact_signoff(root, ep, ("视频",))
        referenced_characters, referenced_assets = episode_registry_reference_ids(root, ep)
        check_identity_registry(root, require_reference_assets=True, required_character_ids=referenced_characters)
        check_asset_reference_registry(root, require_reference_assets=True, required_asset_ids=referenced_assets)
        check_identity_adapter_matrix(root)
        check_storyboard_contract(root, ep, require_frame_assets=True)
        check_storyboard_special_templates(root, ep)
        check_semantic_lineage(root, ep)
        check_state_continuity(root, ep)
        sb = load_json(os.path.join(root, "脚本", ep, "storyboard.json"))
        if sb:
            check_voice_conditioned_lipsync_policy(root, ep, sb)
        check_compose_inputs(root, ep)
    elif check_stage == "review":
        check_compliance_manifest(root, ep, check_stage)
        referenced_characters, referenced_assets = episode_registry_reference_ids(root, ep)
        check_identity_registry(root, require_reference_assets=True, required_character_ids=referenced_characters)
        check_asset_reference_registry(root, require_reference_assets=True, required_asset_ids=referenced_assets)
        check_identity_adapter_matrix(root)
        check_storyboard_contract(root, ep, require_frame_assets=True)
        check_storyboard_special_templates(root, ep)
        check_video_assets(root, ep)
        check_semantic_lineage(root, ep)
        check_state_continuity(root, ep)
        check_multimodal_continuity(root, ep)
        check_subtitle_alignment(root, ep)
    else:
        add(BLOCK, "参数", stage, "未知 stage")


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
        order = {BLOCK: 0, WARN: 1, INFO: 2}
        for f in sorted(structured, key=lambda x: order[x["sev"]]):
            icon = {"block": "⛔", "warn": "⚠️", "info": "ℹ️"}[f["sev"]]
            print(f"{icon} [{f['dim']}] {f['loc']}: {f['msg']}")
            if f.get("return_to_stage") and f["sev"] == BLOCK:
                print(f"   ↳ 回退: {f['return_to_stage']} · {f.get('rerun_scope', '')}")
    return 1 if any(f["sev"] == BLOCK for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
