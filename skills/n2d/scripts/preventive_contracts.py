#!/usr/bin/env python3
"""Preventive contracts for n2d.

These gates check intent/production contracts before expensive generation:

  episode_promise_gate      -> before script_stage2
  shot_intent_gate          -> before image_prompt
  reference_slot_gate       -> before image
  interaction_physics_gate  -> before video_prompt/video
  audio_timing_gate         -> before video_prompt/video/compose
  pilot_release_gate        -> before review/release

The script is deterministic.  It may scaffold missing contract sections when
--write-missing is passed, but a scaffold is draft evidence and still blocks
until the contract is confirmed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
N2D_DIR = SCRIPT_DIR.parents[0]
LIB = N2D_DIR / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

try:
    from n2d_route import normalize_episode  # type: ignore
except Exception:  # pragma: no cover
    normalize_episode = lambda x: str(x or "").strip()  # type: ignore
from n2d_const import PRODUCTION_MODE_DEFAULT
try:
    from production_mode_router import build_route as build_production_mode_route
except Exception:  # pragma: no cover - legacy/minimal distribution fallback
    build_production_mode_route = None  # type: ignore


KIND = "n2d_preventive_contracts"
VERSION = 1
OUT_JSON = "preventive_contracts_{stage}_{episode}.json"
OUT_MD = "preventive_contracts_{stage}_{episode}.md"
PILOT_COVERAGE = {"face", "scene", "action", "lipsync", "seam", "routing"}
PLACEHOLDER_RE = re.compile(r"(待补|待填写|TODO|TBD|__(?:TODO|TBD|PLACEHOLDER|待补|待填写)[^_]*__|<[^>]+>)", re.I)
REFERENCE_SLOT_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".json", ".md", ".mp4", ".mov", ".wav", ".mp3"}
GENERIC_ASSET_TOKENS = {"VFX", "VFX_only", "VFX_layer", "VFX_layers"}
ASSET_ID_RE = re.compile(r"\b(?:MOUNT_GROUP|LOC|PROP|WEAPON|OUTFIT|VFX)[_A-Za-z0-9\u4e00-\u9fff-]+\b")

ROOT_CAUSE_BY_GATE: Dict[str, Tuple[str, str, str]] = {
    "episode_promise_gate": ("script", "编剧/故事编辑", "回 n2d-script 阶段1 修每集承诺/兑现/阻碍/集尾钩"),
    "shot_intent_gate": ("script", "编剧/故事编辑", "回 n2d-script 阶段2 补逐镜戏剧功能和剪辑意图"),
    "reference_slot_gate": ("production_breakdown", "制片主任/场记", "回 production_breakdown/identity/asset registry 补引用槽位与锁定策略"),
    "interaction_physics_gate": ("director_blocking", "导演/分镜", "回导演排戏包或 storyboard 拆动作、接触点、多人站位和降级方案"),
    "audio_timing_gate": ("backend", "模型路由/后端适配", "回音频/口型/字幕/时长策略和模型路由补证据"),
    "pilot_release_gate": ("qc", "QC/验收", "回首集 pilot acceptance 补风险选择、证据路径/hash/QC/签收"),
    "contract_schema_gate": ("production_breakdown", "制片主任/场记", "补 preventive_contracts schema 和跨产物引用证据后复跑"),
}

STAGE_GATES: Dict[str, Tuple[str, ...]] = {
    "script_stage2": ("episode_promise_gate",),
    "image_prompt": ("shot_intent_gate",),
    "image_prompt_preflight": ("shot_intent_gate",),
    "image": ("reference_slot_gate",),
    "image_preflight": ("reference_slot_gate",),
    "video_prompt": ("interaction_physics_gate", "audio_timing_gate"),
    "video_prompt_preflight": ("interaction_physics_gate", "audio_timing_gate"),
    "video": ("interaction_physics_gate", "audio_timing_gate"),
    "video_preflight": ("interaction_physics_gate", "audio_timing_gate"),
    "compose": ("audio_timing_gate",),
    "review": ("pilot_release_gate",),
    "release": (
        "episode_promise_gate",
        "shot_intent_gate",
        "reference_slot_gate",
        "interaction_physics_gate",
        "audio_timing_gate",
        "pilot_release_gate",
    ),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def contract_path(root: Path, episode: str) -> Path:
    return root / "脚本" / episode / "preventive_contracts.json"


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def normalize_clip_id(value: Any, idx: int = 0) -> str:
    text = str(value or "").strip()
    m = re.search(r"(?:Clip[_\s-]?|CLIP)(\d+)", text, re.I)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    m = re.search(r"(\d+)", text)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return f"Clip_{idx:02d}" if idx else text


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    if isinstance(value, dict):
        return " ".join(str(k) + " " + flatten(v) for k, v in value.items())
    return str(value or "")


def flatten_for_positive_id_scan(value: Any) -> str:
    """Flatten clip data for real presence scans, excluding explicit negatives."""
    skip_keys = {"forbidden_presence", "negative", "negative_prompt", "must_not_have", "forbidden"}
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(flatten_for_positive_id_scan(v) for v in value)
    if isinstance(value, dict):
        return " ".join(
            str(k) + " " + flatten_for_positive_id_scan(v)
            for k, v in value.items()
            if str(k) not in skip_keys
        )
    return str(value or "")


def filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        text = value.strip()
        return bool(text) and not PLACEHOLDER_RE.search(text)
    if isinstance(value, list):
        return any(filled(v) for v in value)
    if isinstance(value, dict):
        return any(filled(v) for v in value.values())
    return bool(value)


def status_confirmed(data: Mapping[str, Any]) -> bool:
    return str(data.get("status") or "").strip().lower() in {"confirmed", "pass", "accepted", "ready", "已确认"}


def contains_placeholder(value: Any) -> bool:
    """Check placeholders per string so filename tokens with "__" cannot pair across JSON fields."""
    if isinstance(value, str):
        return bool(PLACEHOLDER_RE.search(value))
    if isinstance(value, list):
        return any(contains_placeholder(v) for v in value)
    if isinstance(value, dict):
        return any(contains_placeholder(v) for v in value.values())
    return False


def storyboard(root: Path, episode: str) -> List[Dict[str, Any]]:
    data = load_json(root / "脚本" / episode / "storyboard.json")
    clips = data.get("clips") if isinstance(data, dict) else []
    return [c for c in clips or [] if isinstance(c, dict)]


def clip_key(clip: Mapping[str, Any], idx: int) -> str:
    return normalize_clip_id(clip.get("clip_id") or clip.get("id") or clip.get("label"), idx)


def settings_text(root: Path) -> str:
    try:
        return (root / "_设置.md").read_text(encoding="utf-8")
    except Exception:
        return ""


def production_mode(root: Path) -> str:
    text = settings_text(root)
    for line in text.splitlines():
        if "制作模式" in line:
            return line.split(":", 1)[-1].split("：", 1)[-1].strip()
    return ""


def setting_value(root: Path, key: str) -> str:
    text = settings_text(root)
    for line in text.splitlines():
        if key not in line:
            continue
        if ":" in line:
            return line.split(":", 1)[-1].strip()
        if "：" in line:
            return line.split("：", 1)[-1].strip()
    return ""


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def compact_values(values: Iterable[Any], *, limit: int = 8) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, Mapping):
            text = "；".join(f"{k}={flatten(v)}" for k, v in value.items() if filled(v))
        else:
            text = flatten(value)
        text = re.sub(r"\s+", " ", str(text or "").strip())
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def chars_from_clip(clip: Mapping[str, Any]) -> List[str]:
    out: List[str] = []
    for key in ("character_ids", "characters", "required_characters"):
        val = clip.get(key)
        if isinstance(val, list):
            out.extend(str(v) for v in val if str(v).strip())
        elif isinstance(val, str):
            out.extend(re.findall(r"\bCHAR[_A-Za-z0-9\u4e00-\u9fff-]+\b", val))
    schedule = clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else {}
    for val in as_list(schedule.get("characters")) + as_list(schedule.get("required_presence")):
        text = str(val).strip()
        if text.startswith("CHAR_"):
            out.append(text)
    return sorted(set(x.replace("-", "_") for x in out))


def asset_ids_from_clip(clip: Mapping[str, Any]) -> List[str]:
    """Collect asset IDs only from storyboard entity fields.

    Chinese asset IDs make prose regex scanning unsafe: ``LOC_01光位`` in a
    continuity note is greedily read as a new asset instead of ``LOC_01`` plus
    the word “光位”. Stage-2 storyboards already expose structured entity
    fields, which are the authoritative source for production gates.
    """
    out: List[str] = []
    loc = clip.get("location_id") or clip.get("loc_id")
    if loc:
        loc_text = str(loc)
        out.extend(ASSET_ID_RE.findall(loc_text) or [loc_text])
    for key in ("object_ids", "asset_ids", "prop_ids", "weapon_ids", "vfx_ids"):
        val = clip.get(key)
        if isinstance(val, list):
            for item in val:
                item_text = str(item).strip()
                if not item_text:
                    continue
                out.extend(ASSET_ID_RE.findall(item_text) or [item_text])
        elif isinstance(val, str):
            out.extend(ASSET_ID_RE.findall(val))
    schedule = clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else {}
    for key in ("objects", "locations", "required_presence", "offscreen_presence"):
        for value in as_list(schedule.get(key)):
            text = str(value or "").strip()
            if text.startswith(("MOUNT_GROUP_", "LOC_", "PROP_", "WEAPON_", "OUTFIT_", "VFX_")):
                out.extend(ASSET_ID_RE.findall(text) or [text])
    normalized = {x.replace("-", "_") for x in out}
    return sorted(x for x in normalized if x not in GENERIC_ASSET_TOKENS)


def _clip_template(clip: Mapping[str, Any]) -> Mapping[str, Any]:
    value = clip.get("template_contract")
    return value if isinstance(value, Mapping) else {}


def _clip_continuity(clip: Mapping[str, Any]) -> Mapping[str, Any]:
    value = clip.get("continuity")
    return value if isinstance(value, Mapping) else {}


def _template_values(template: Mapping[str, Any], keys: Sequence[str]) -> List[Any]:
    values: List[Any] = []
    for key in keys:
        values.extend(as_list(template.get(key)))
    return values


def _character_position_values(clip: Mapping[str, Any], template: Mapping[str, Any]) -> List[Any]:
    values: List[Any] = []
    for slot in as_list(clip.get("character_slots")):
        if isinstance(slot, Mapping):
            char = slot.get("character_id") or slot.get("id") or slot.get("character") or "角色"
            pos = slot.get("screen_position") or slot.get("position") or slot.get("slot") or ""
            lock = slot.get("identity_lock") or slot.get("face_priority") or ""
            values.append(f"{char}：{pos}；{lock}".strip("；"))
        else:
            values.append(slot)
    screen_positions = clip.get("screen_positions")
    if isinstance(screen_positions, Mapping):
        values.extend(f"{k}={v}" for k, v in screen_positions.items())
    else:
        values.extend(as_list(screen_positions))
    values.extend(_template_values(template, ("blocking", "screen_direction", "spatial_path", "camera_path", "occlusion_layers")))
    return values


def _derive_action_decomposition(clip: Mapping[str, Any]) -> List[str]:
    template = _clip_template(clip)
    continuity = _clip_continuity(clip)
    values: List[Any] = []
    values.extend(_template_values(template, ("beats", "readability_beats", "keyframe_plan")))
    for key in ("start_state", "action", "end_state", "entry_exit"):
        if filled(continuity.get(key)):
            values.append(f"{key}: {flatten(continuity.get(key))}")
    values.extend(as_list(clip.get("performance_beats") or clip.get("表演节拍")))
    values.extend(as_list(clip.get("description") or clip.get("label")))
    result = compact_values(values, limit=8)
    if not result:
        result = ["按 storyboard 起幅-主动作-落幅执行单一主动作链，保持首尾状态连续。"]
    return result


def _derive_contact_points(clip: Mapping[str, Any]) -> List[str]:
    template = _clip_template(clip)
    continuity = _clip_continuity(clip)
    values: List[Any] = []
    values.extend(_template_values(template, ("contact_points", "contact_map", "physics_guard", "mount_contact")))
    values.extend(as_list(clip.get("contact_points") or clip.get("contact_map")))
    blob = flatten(clip)
    chars = chars_from_clip(clip)
    assets = asset_ids_from_clip(clip)
    if not values:
        if any(x in blob for x in ("握", "持", "拿")) and assets:
            values.append(f"手部与 {assets[0]} 的接触点由首帧/参考帧保持，避免道具漂移或穿模。")
        elif any(x in blob for x in ("接触", "拥抱", "拉扯", "打斗", "contact", "touch")):
            values.append("按 storyboard 保持角色/道具接触点、遮挡层级和肢体归属；不新增额外身体接触。")
        elif len(chars) >= 2 or filled(continuity.get("entry_exit")):
            values.append("无直接身体接触；按 screen_positions/entry_exit 保持画面分层、距离和画外保留关系。")
    return compact_values(values, limit=6)


def _derive_vfx_layers(clip: Mapping[str, Any]) -> Tuple[List[str], str]:
    template = _clip_template(clip)
    values: List[Any] = []
    values.extend(_template_values(template, (
        "vfx_layers",
        "vfx_asset",
        "motif_id",
        "light_shadow_lock",
        "occlusion_layers",
        "parallax_layers",
        "physics_guard",
    )))
    values.extend(as_list(clip.get("vfx_layers") or clip.get("effect_cause") or clip.get("vfx_asset")))
    asset_ids = [aid for aid in asset_ids_from_clip(clip) if aid.startswith("VFX")]
    values.extend(asset_ids)
    layers = compact_values(values, limit=8)
    effect_cause = flatten(template.get("effect_cause") or template.get("physics_guard") or template.get("story_function") or "")
    blob = flatten(clip).lower()
    if not layers and any(x in blob for x in ("vfx", "magic", "法术", "特效", "剑气")):
        layers = ["按 storyboard 光影/粒子/烟尘因果生成 VFX，不新增未登记法术或系统文字。"]
    if not effect_cause and layers:
        effect_cause = "VFX 只响应本镜动作、系统面板或环境事件；文字交 compose overlay，不在视频内烤字。"
    return layers, effect_cause


def _derive_degrade_plan(clip: Mapping[str, Any]) -> str:
    template = _clip_template(clip)
    for key in ("degrade_plan", "fallback", "implementation_decomposition"):
        if filled(template.get(key)):
            return flatten(template.get(key)).strip()
    label = str(clip.get("label") or clip.get("description") or "").strip()
    if "system_panel" in flatten(template) or "面板" in flatten(clip):
        return "面板文字全部交 compose overlay；视频只保留人物反应和干净负空间，必要时拆为人物反应 + 面板空镜。"
    if len(chars_from_clip(clip)) >= 2:
        return "复杂多人/接触不稳时拆为建立镜、手部/物件特写、反打反应镜，保留剧情 beat 和动作目标。"
    return f"{label or '本镜'} 动作不稳时拆为建立镜 + 关键动作 + 反应/结果镜，保留剧情 beat。"


def derive_interaction_row(clip: Mapping[str, Any], cid: str) -> Dict[str, Any]:
    template = _clip_template(clip)
    vfx_layers, effect_cause = _derive_vfx_layers(clip)
    row: Dict[str, Any] = {
        "clip_id": cid,
        "risk_type": str(template.get("template_id") or clip.get("template_id") or "auto_detected"),
        "action_decomposition": _derive_action_decomposition(clip),
        "contact_points": _derive_contact_points(clip),
        "screen_positions": compact_values(_character_position_values(clip, template), limit=8),
        "vfx_layers": vfx_layers,
        "degrade_plan": _derive_degrade_plan(clip),
    }
    if effect_cause:
        row["effect_cause"] = effect_cause
    return row


def derive_audio_timing(root: Path, episode: str, clips: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    mode = production_mode(root) or PRODUCTION_MODE_DEFAULT
    audio_strategy = setting_value(root, "视频生成音频策略") or "无声视频流"
    lipsync = setting_value(root, "对口型") or "关闭"
    native_track = setting_value(root, "视频原生音轨") or "丢弃"
    sound_plan: Dict[str, Any] = {}
    sound_by_clip: Dict[str, Dict[str, Any]] = {}
    if build_production_mode_route is not None and (
        "混合自动路由" in mode or "hybrid" in mode.lower() or "mixed" in mode.lower()
    ):
        try:
            sound_plan = build_production_mode_route(root, episode)
            sound_by_clip = {
                str(row.get("clip_id") or ""): dict(row)
                for row in (sound_plan.get("clip_routes") or [])
                if isinstance(row, Mapping) and str(row.get("clip_id") or "").strip()
            }
        except Exception:
            sound_plan = {}
            sound_by_clip = {}
    dialogue_rows: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, 1):
        if not clip_needs_audio_timing(clip):
            continue
        cid = clip_key(clip, idx)
        sound = sound_by_clip.get(cid, {})
        strategy = str(sound.get("audio_strategy") or "").strip()
        timing_basis = str(sound.get("timing_basis") or "").strip()
        if not strategy:
            if "原生音画" in mode:
                strategy = "native_av"
            elif "先出视频后配音" in mode:
                strategy = "post_dub"
            else:
                strategy = "performance_audio_first"
        if not timing_basis:
            timing_basis = (
                "native_av_script_timing" if strategy == "native_av"
                else "text_estimate_no_audio" if strategy in {"post_dub", "rough_timing_final_dub_later"}
                else "approved_performance_or_final_audio"
            )
        duration = clip.get("duration") or clip.get("duration_sec") or clip.get("时长")
        dialogue_indices = clip.get("dialogue_indices") or []
        voiceover_indices = clip.get("voiceover_indices") or []
        timing_parts = [f"timing_basis={timing_basis}", f"storyboard.duration={duration}s" if duration else "storyboard clip duration"]
        if dialogue_indices:
            timing_parts.append(f"dialogue_indices={dialogue_indices}")
        if voiceover_indices:
            timing_parts.append(f"voiceover_indices={voiceover_indices}")
        if strategy == "performance_audio_first":
            mouth_policy = (
                f"voice_conditioned_lipsync；performance_track_status={sound.get('performance_track_status') or 'required'}；"
                "模型音轨只作表演条件，成片使用 final voice。"
            )
            voice_policy = "声音选角锁定后可先用获批表演/guide 驱动；final voice 可后置替换，替换后重验口型。"
        elif strategy == "base_video_then_post_lipsync":
            mouth_policy = (
                "neutral_resting_mouth_base_plate；no_native_speech；"
                f"post_lipsync_required=true；output={sound.get('post_lipsync_output') or '出视频/<集>/视频_lipsync/<clip>_lipsync.mp4'}。"
            )
            voice_policy = "先出中性口型基础视频；获批表演/final 音轨到位后走独立 lipsync pass，不让视频后端猜台词。"
        elif strategy == "native_av":
            mouth_policy = "native_speech；逐镜核验台词事实、声源、口型与后端同步音画能力。"
            voice_policy = f"native_av；原生音轨策略={native_track}；仿真人音色仍需授权。"
        else:
            mouth_policy = f"no_visible_lipsync；{audio_strategy}；no_native_speech；画内不生成角色口型人声。"
            voice_policy = "最终旁白/口外音后置；前期仅用 text_estimate_no_audio 或画面节奏，不生成占位 WAV。"
        dialogue_rows.append({
            "clip_id": cid,
            "audio_strategy": strategy,
            "timing_basis": timing_basis,
            "performance_track_status": sound.get("performance_track_status") or "not_applicable",
            "final_voice_stage": sound.get("final_voice_stage") or "after_voice_casting_lock",
            "base_video_only": bool(sound.get("base_video_only")),
            "post_lipsync_required": bool(sound.get("post_lipsync_required")),
            "timing_source": "；".join(timing_parts),
            "mouth_policy": mouth_policy,
            "subtitle_policy": "compose_overlay_only；视频模型禁止生成字幕/屏幕文字/logo/水印。",
            "voice_or_native_policy": voice_policy,
        })
    return {
        "mode": mode,
        "policy": "time_basis_first_per_shot_sound_routing",
        "production_route_status": sound_plan.get("status") or "legacy_project_mode",
        "post_dub": {
            "fit_strategy": "先锁无 WAV 时间槽或画面节奏；音色定妆后生成 final voice，按偏差刷新 OTIO、拟合或局部重切。",
            "overflow_policy": "final voice 超出估时范围时回 n2d-script/video 调整节奏；不得用重度压速或静音占位伪装通过。",
        },
        "native_av_policy": {
            "lipsync_policy": f"逐镜 route 决定；项目级对口型={lipsync}。",
            "subtitle_policy": "compose_overlay_only；视频后端禁止烤字。",
            "voice_identity_policy": "native_av 仍须声音授权；其它 route 的 final voice 由 voice_casting 锁定。",
        },
        "dialogue_closeups": dialogue_rows,
    }


def _merge_missing(existing: Any, derived: Any) -> Any:
    if isinstance(existing, Mapping) and isinstance(derived, Mapping):
        out: Dict[str, Any] = dict(derived)
        for key, value in existing.items():
            out[key] = _merge_missing(value, out.get(key)) if key in out else value
        return out
    if filled(existing):
        return existing
    return derived


def _merge_clip_rows(derived_rows: Sequence[Mapping[str, Any]], existing_rows: Any) -> List[Dict[str, Any]]:
    existing_by_key = by_id(r for r in (existing_rows or []) if isinstance(r, Mapping)) if isinstance(existing_rows, list) else {}
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for row in derived_rows:
        key = str(row.get("clip_id") or row.get("clip") or row.get("id") or "").strip()
        merged = _merge_missing(existing_by_key.get(key, {}), row)
        out.append(dict(merged))
        if key:
            seen.add(key)
    for key, row in existing_by_key.items():
        if key not in seen:
            out.append(dict(row))
    return out


def _merge_audio_timing(derived: Mapping[str, Any], existing: Any) -> Dict[str, Any]:
    if not isinstance(existing, Mapping):
        return dict(derived)
    out = dict(derived)
    for key, value in existing.items():
        if key == "dialogue_closeups":
            out[key] = _merge_clip_rows(derived.get("dialogue_closeups") or [], value)
        elif isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[key] = _merge_missing(value, out.get(key))
        elif filled(value):
            out[key] = value
    return out


def by_id(rows: Iterable[Any]) -> Dict[str, Mapping[str, Any]]:
    out: Dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        key = str(row.get("id") or row.get("character_id") or row.get("asset_id") or row.get("scene_id") or row.get("clip_id") or row.get("clip") or "").strip()
        if key:
            out[key] = row
            normalized = normalize_clip_id(key)
            if normalized and normalized != key:
                out.setdefault(normalized, row)
    return out


def add_finding(findings: List[Dict[str, Any]], gate: str, severity: str, loc: str, message: str, *, return_to_stage: str = "") -> None:
    row = {"gate": gate, "severity": severity, "loc": loc, "message": message}
    if return_to_stage:
        row["return_to_stage"] = return_to_stage
    layer, owner, scope = ROOT_CAUSE_BY_GATE.get(gate, ROOT_CAUSE_BY_GATE["contract_schema_gate"])
    row.setdefault("root_cause_layer", layer)
    row.setdefault("owner", owner)
    row.setdefault("minimal_rerun_scope", scope)
    findings.append(row)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _artifact_path_from(value: Mapping[str, Any]) -> str:
    for key in ("path", "file", "image_path", "video_path", "artifact_path", "qc_report", "qc_path"):
        val = value.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def looks_like_artifact_path(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return False
    suffix = Path(value).suffix.lower()
    if suffix in REFERENCE_SLOT_SUFFIXES:
        return True
    return value.startswith(("出图/", "脚本/", "生产数据/", "合规/", "成片/", "视频/", "音频/"))


def _reference_slots(row: Mapping[str, Any]) -> List[Any]:
    slots = row.get("reference_slots") or row.get("reference_group") or row.get("reference_atlas") or []
    return slots if isinstance(slots, list) else [slots]


def _slot_artifact_issues(root: Path, row: Mapping[str, Any]) -> List[str]:
    issues: List[str] = []
    resolved = 0
    slots: List[Any] = []
    for slot in _reference_slots(row):
        if isinstance(slot, Mapping) and not _artifact_path_from(slot):
            slots.extend(_slot_entries_from_node(root, slot))
        else:
            slots.append(slot)
    for slot in slots:
        if isinstance(slot, Mapping):
            rel = _artifact_path_from(slot)
            expected = str(slot.get("sha256") or slot.get("hash") or "").strip().lower()
        elif isinstance(slot, str):
            text = slot.strip()
            rel = text if any(sep in text for sep in ("/", "\\")) or "." in Path(text).name else ""
            expected = ""
        else:
            continue
        if not rel:
            continue
        path = (root / rel).resolve() if not os.path.isabs(rel) else Path(rel)
        if not path.is_file():
            issues.append(f"{rel} 不存在")
            continue
        resolved += 1
        if expected:
            actual = sha256_file(path)
            if actual.lower() != expected:
                issues.append(f"{rel} sha256 不匹配")
        else:
            # 与 pilot_release_gate 同口径（2026-07 标准审计）：只给路径不给 hash，
            # "存在但内容错/陈旧的图"可蒙混过闸；缺 sha256 一并报出，别让两个 gate
            # 对"真实产物绑定"一严一松。
            issues.append(f"{rel} 缺 sha256（引用槽位须绑定内容哈希，防陈旧/错图冒充）")
    if not resolved:
        issues.append("reference_slots 缺可解析的真实文件 path/hash")
    return issues


def _slot_entries_from_node(root: Path, node: Any, *, slot_name: str = "") -> List[Dict[str, Any]]:
    """Convert registry reference_group/reference_atlas nodes into signed slots.

    The gate checks `preventive_contracts.json`, but the durable visual evidence
    usually lives first in identity/asset registries.  Scaffolding empty slots
    hides that evidence and creates a false preflight blocker, so derived
    contract rows carry the actual file path and current content hash.
    """
    entries: List[Dict[str, Any]] = []

    def walk(value: Any, label: str) -> None:
        if isinstance(value, Mapping):
            rel = _artifact_path_from(value)
            if rel:
                row: Dict[str, Any] = {"slot": label or str(value.get("slot") or "primary"), "path": rel}
                path = (root / rel).resolve() if not os.path.isabs(rel) else Path(rel)
                if path.is_file():
                    row["sha256"] = sha256_file(path)
                status = str(value.get("status") or "").strip()
                if status:
                    row["status"] = status
                entries.append(row)
            for key, child in value.items():
                if key in {"derivation", "human_review"}:
                    continue
                walk(child, str(key or label or "primary"))
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, label or f"slot_{idx + 1}")
        elif isinstance(value, str):
            text = value.strip()
            if looks_like_artifact_path(text):
                path = (root / text).resolve() if not os.path.isabs(text) else Path(text)
                row = {"slot": slot_name or "primary", "path": text}
                if path.is_file():
                    row["sha256"] = sha256_file(path)
                entries.append(row)

    walk(node, slot_name)
    out: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str]] = set()
    for row in entries:
        key = (str(row.get("slot") or ""), str(row.get("path") or ""))
        if row.get("path") and key not in seen:
            seen.add(key)
            out.append(row)
    return out


def _registry_reference_slots(root: Path, row: Mapping[str, Any]) -> List[Dict[str, Any]]:
    slots: List[Dict[str, Any]] = []
    for key in ("reference_slots", "reference_group", "reference_atlas"):
        slots.extend(_slot_entries_from_node(root, row.get(key), slot_name=key))
    return slots


def _strategy_value(row: Mapping[str, Any], keys: Sequence[str], fallback: str) -> Any:
    for key in keys:
        value = row.get(key)
        if filled(value):
            return value
    return fallback


def _identity_scaffold_rows(root: Path) -> Dict[str, Mapping[str, Any]]:
    data = load_json(root / "出图" / "共享" / "identity_registry.json")
    chars = data.get("characters") if isinstance(data, dict) else []
    out: Dict[str, Mapping[str, Any]] = {}
    for char in chars or []:
        if not isinstance(char, Mapping):
            continue
        forms = [f for f in (char.get("forms") or []) if isinstance(f, Mapping)]
        ordered_forms = sorted(forms, key=lambda f: 0 if str(f.get("form") or "") == "常态" else 1)
        rows = ordered_forms or [{}]
        for form in rows:
            row = dict(char)
            row.update(form)
            ids = [
                str(char.get("id") or char.get("character_id") or ""),
                str(form.get("id") or ""),
                str(form.get("asset_key") or ""),
            ]
            for key in ids:
                if key and key not in out:
                    out[key] = row
    return out


def _asset_scaffold_rows(root: Path) -> Dict[str, Mapping[str, Any]]:
    data = load_json(root / "出图" / "共享" / "asset_registry.json")
    return by_id(a for a in (data.get("assets") if isinstance(data, dict) else []) or [] if isinstance(a, Mapping))


def _blank_contract(root: Path, episode: str) -> Dict[str, Any]:
    clips = storyboard(root, episode)
    characters = sorted({cid for clip in clips for cid in chars_from_clip(clip)})
    assets = sorted({aid for clip in clips for aid in asset_ids_from_clip(clip)})
    high_risk = [(clip_key(c, i), c) for i, c in enumerate(clips, 1) if clip_needs_physics(c)]
    scenes = [a for a in assets if a.startswith("LOC")]
    non_scene_assets = [a for a in assets if not a.startswith("LOC")]
    identity_rows = _identity_scaffold_rows(root)
    asset_rows = _asset_scaffold_rows(root)

    def char_row(cid: str) -> Dict[str, Any]:
        source = identity_rows.get(cid) or {}
        return {
            "id": cid,
            "role": "core",
            "reference_slots": _registry_reference_slots(root, source),
            "identity_strategy": _strategy_value(
                source,
                ("identity_strategy", "identity_adapters", "generation_control", "angle_policy", "drift_forbidden"),
                "same-source registry reference_group identity lock",
            ),
        }

    def asset_row(aid: str, *, typ: str) -> Dict[str, Any]:
        source = asset_rows.get(aid) or {}
        return {
            "id": aid,
            "type": typ,
            "reference_slots": _registry_reference_slots(root, source),
            "lock_strategy": _strategy_value(
                source,
                ("lock_strategy", "constraints", "drift_forbidden", "scene_dna", "weapon_profile"),
                "registry reference_group shape/scene lock",
            ),
        }

    return {
        "kind": KIND,
        "version": VERSION,
        "episode": episode,
        "status": "draft",
        "episode_promise": {
            "source_trace_ids": [],
            "opening_hook": "",
            "promise": "",
            "obstacle": "",
            "payoff_or_progress": "",
            "cliffhanger": "",
        },
        "shots": [
            {
                "clip_id": clip_key(clip, idx),
                "source_trace_ids": [],
                "dramatic_function": clip.get("dramatic_function") or "",
                "editing_intent": clip.get("editing_intent") or "",
                "emotional_turn": "",
                "visual_question": "",
            }
            for idx, clip in enumerate(clips, 1)
        ],
        "reference_slots": {
            "characters": [char_row(cid) for cid in characters],
            "assets": [asset_row(aid, typ="asset") for aid in non_scene_assets],
            "scenes": [asset_row(sid, typ="scene") for sid in scenes],
        },
        "interaction_physics": [
            derive_interaction_row(clip, cid)
            for cid, clip in high_risk
        ],
        "audio_timing": derive_audio_timing(root, episode, clips),
    }


def scaffold(root: Path, episode: str) -> Dict[str, Any]:
    path = contract_path(root, episode)
    existing = load_json(path)
    base = _blank_contract(root, episode)
    if isinstance(existing, dict):
        merged = _merge_missing(existing, base)
        merged["kind"] = base["kind"]
        merged["version"] = base["version"]
        merged["episode"] = base["episode"]
        merged["interaction_physics"] = _merge_clip_rows(base.get("interaction_physics") or [], existing.get("interaction_physics"))
        merged["audio_timing"] = _merge_audio_timing(base.get("audio_timing") or {}, existing.get("audio_timing"))
        base = merged
    write_json_atomic(path, base)
    return base


def load_or_scaffold(root: Path, episode: str, write_missing: bool) -> Tuple[Optional[Dict[str, Any]], bool]:
    path = contract_path(root, episode)
    data = load_json(path)
    if isinstance(data, dict):
        if write_missing:
            return scaffold(root, episode), False
        return data, False
    if write_missing:
        return scaffold(root, episode), True
    return None, False


def _required_sections_for_gates(gates: Sequence[str]) -> Dict[str, type]:
    required: Dict[str, type] = {}
    if "episode_promise_gate" in gates:
        required["episode_promise"] = dict
    if "shot_intent_gate" in gates:
        required["shots"] = list
    if "reference_slot_gate" in gates:
        required["reference_slots"] = dict
    if "interaction_physics_gate" in gates:
        required["interaction_physics"] = list
    if "audio_timing_gate" in gates:
        required["audio_timing"] = dict
    return required


def _relevant_payload(contract: Mapping[str, Any], gates: Sequence[str]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "kind": contract.get("kind"),
        "version": contract.get("version"),
        "episode": contract.get("episode"),
        "status": contract.get("status"),
    }
    for section in _required_sections_for_gates(gates):
        payload[section] = contract.get(section)
    return payload


def check_contract_schema(root: Path, episode: str, contract: Optional[Mapping[str, Any]], gates: Sequence[str], findings: List[Dict[str, Any]]) -> None:
    if not isinstance(contract, Mapping):
        return
    gate = "contract_schema_gate"
    loc = relpath(root, contract_path(root, episode))
    if contract.get("kind") != KIND:
        add_finding(findings, gate, "block", loc, f"preventive_contracts.kind 必须是 {KIND}。", return_to_stage="script_stage2")
    if int(contract.get("version") or 0) < 1:
        add_finding(findings, gate, "block", loc, "preventive_contracts.version 缺失或非法。", return_to_stage="script_stage2")
    if str(contract.get("episode") or episode).strip() != episode:
        add_finding(findings, gate, "block", loc, f"episode 不匹配：contract={contract.get('episode')!r}, expected={episode}。", return_to_stage="script_stage2")
    for section, typ in _required_sections_for_gates(gates).items():
        if not isinstance(contract.get(section), typ):
            add_finding(findings, gate, "block", loc, f"{section} 必须是 {typ.__name__}。", return_to_stage="script_stage2")
    if status_confirmed(contract) and contains_placeholder(_relevant_payload(contract, gates)):
        add_finding(findings, gate, "block", loc, "已 confirmed 的相关合同段仍含待补/TODO/占位符。", return_to_stage="script_stage2")


def check_contract_cross_refs(root: Path, episode: str, contract: Optional[Mapping[str, Any]], gates: Sequence[str], findings: List[Dict[str, Any]]) -> None:
    if not isinstance(contract, Mapping):
        return
    gate = "contract_schema_gate"
    clips = storyboard(root, episode)
    if not clips:
        return
    clip_ids = {clip_key(clip, idx) for idx, clip in enumerate(clips, 1)}
    loc = relpath(root, contract_path(root, episode))
    if "shot_intent_gate" in gates and isinstance(contract.get("shots"), list):
        unknown = sorted(
            normalize_clip_id(row.get("clip_id") or row.get("clip") or row.get("id"))
            for row in contract.get("shots") or []
            if isinstance(row, Mapping) and normalize_clip_id(row.get("clip_id") or row.get("clip") or row.get("id")) not in clip_ids
        )
        if unknown:
            add_finding(findings, gate, "block", loc, "shots 引用了 storyboard 不存在的 Clip：" + "、".join(unknown[:12]), return_to_stage="script_stage2")
    if "interaction_physics_gate" in gates and isinstance(contract.get("interaction_physics"), list):
        unknown = sorted(
            normalize_clip_id(row.get("clip_id") or row.get("clip") or row.get("id"))
            for row in contract.get("interaction_physics") or []
            if isinstance(row, Mapping) and normalize_clip_id(row.get("clip_id") or row.get("clip") or row.get("id")) not in clip_ids
        )
        if unknown:
            add_finding(findings, gate, "block", loc, "interaction_physics 引用了 storyboard 不存在的 Clip：" + "、".join(unknown[:12]), return_to_stage="script_stage2")
    if "audio_timing_gate" in gates:
        audio = contract.get("audio_timing") if isinstance(contract.get("audio_timing"), Mapping) else {}
        unknown = sorted(
            normalize_clip_id(row.get("clip_id") or row.get("clip") or row.get("id"))
            for row in audio.get("dialogue_closeups") or []
            if isinstance(row, Mapping) and normalize_clip_id(row.get("clip_id") or row.get("clip") or row.get("id")) not in clip_ids
        )
        if unknown:
            add_finding(findings, gate, "block", loc, "audio_timing 引用了 storyboard 不存在的 Clip：" + "、".join(unknown[:12]), return_to_stage="script_stage2")


def check_episode_promise(root: Path, episode: str, contract: Optional[Mapping[str, Any]], findings: List[Dict[str, Any]]) -> None:
    gate = "episode_promise_gate"
    loc = relpath(root, contract_path(root, episode))
    if not isinstance(contract, Mapping):
        add_finding(findings, gate, "block", loc, "缺 preventive_contracts.json；先补每集承诺/阻碍/兑现/集尾钩合同。", return_to_stage="script_stage1")
        return
    section = contract.get("episode_promise") if isinstance(contract.get("episode_promise"), Mapping) else {}
    required = ("opening_hook", "promise", "obstacle", "payoff_or_progress", "cliffhanger")
    missing = [key for key in required if not filled(section.get(key))]
    if not status_confirmed(contract):
        add_finding(findings, gate, "block", loc, "preventive_contracts.status 不是 confirmed；承诺合同未签收。", return_to_stage="script_stage1")
    if missing:
        add_finding(findings, gate, "block", loc, "每集承诺合同缺字段：" + "、".join(missing), return_to_stage="script_stage1")


def _shot_rows(root: Path, episode: str, contract: Optional[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    rows: List[Mapping[str, Any]] = []
    if isinstance(contract, Mapping) and isinstance(contract.get("shots"), list):
        rows.extend(r for r in contract.get("shots") or [] if isinstance(r, Mapping))
    shot_intent = load_json(root / "脚本" / episode / "shot_intent.json")
    if isinstance(shot_intent, dict) and isinstance(shot_intent.get("shots"), list):
        rows.extend(r for r in shot_intent.get("shots") or [] if isinstance(r, Mapping))
    return by_id(rows)


def _storyboard_intent(clip: Mapping[str, Any]) -> Mapping[str, Any]:
    intent = clip.get("intent") if isinstance(clip.get("intent"), Mapping) else {}
    return {
        "dramatic_function": clip.get("dramatic_function") or clip.get("戏剧功能") or intent.get("dramatic_function") or intent.get("戏剧功能"),
        "editing_intent": clip.get("editing_intent") or clip.get("剪辑意图") or intent.get("editing_intent") or intent.get("剪辑意图"),
    }


def check_shot_intent(root: Path, episode: str, contract: Optional[Mapping[str, Any]], findings: List[Dict[str, Any]]) -> None:
    gate = "shot_intent_gate"
    clips = storyboard(root, episode)
    loc = relpath(root, root / "脚本" / episode / "storyboard.json")
    if not clips:
        add_finding(findings, gate, "block", loc, "缺 storyboard.json clips；无法证明逐镜戏剧功能/剪辑意图。", return_to_stage="script_stage2")
        return
    if not isinstance(contract, Mapping):
        add_finding(findings, gate, "block", relpath(root, contract_path(root, episode)), "缺 preventive_contracts.json；逐镜意图必须进入可签收合同。", return_to_stage="script_stage2")
        return
    rows = _shot_rows(root, episode, contract)
    missing: List[str] = []
    for idx, clip in enumerate(clips, 1):
        cid = clip_key(clip, idx)
        source = dict(_storyboard_intent(clip))
        row = dict(rows.get(cid, {}))
        if not filled(row.get("editing_intent")) and filled(row.get("edit_intent")):
            row["editing_intent"] = row.get("edit_intent")
        source.update({k: v for k, v in row.items() if v not in (None, "", [], {})})
        absent = [key for key in ("dramatic_function", "editing_intent") if not filled(source.get(key))]
        if absent:
            missing.append(f"{cid}({','.join(absent)})")
    if not status_confirmed(contract):
        add_finding(findings, gate, "block", relpath(root, contract_path(root, episode)), "preventive_contracts.status 不是 confirmed；逐镜意图合同未签收。", return_to_stage="script_stage2")
    if missing:
        add_finding(findings, gate, "block", loc, "逐镜缺戏剧功能/剪辑意图：" + "、".join(missing[:12]), return_to_stage="script_stage2")


def _identity_registry_rows(root: Path) -> Dict[str, Mapping[str, Any]]:
    data = load_json(root / "出图" / "共享" / "identity_registry.json")
    out: Dict[str, Mapping[str, Any]] = {}
    chars = data.get("characters") if isinstance(data, dict) else []
    for char in chars or []:
        if not isinstance(char, Mapping):
            continue
        base_ids = [
            str(char.get("id") or char.get("character_id") or "").strip(),
            str(char.get("name") or "").strip(),
        ]
        forms = [form for form in (char.get("forms") or []) if isinstance(form, Mapping)]
        if not forms:
            for key in base_ids:
                if key:
                    out.setdefault(key, char)
            continue
        for index, form in enumerate(forms):
            row = dict(char)
            row.update(form)
            form_ids = [
                str(form.get("id") or "").strip(),
                str(form.get("asset_key") or "").strip(),
                str(form.get("form") or "").strip(),
            ]
            keys = [key for key in form_ids if key]
            if index == 0:
                keys.extend(key for key in base_ids if key)
            for base in base_ids:
                if not base:
                    continue
                for suffix in form_ids:
                    if suffix:
                        keys.append(f"{base}/{suffix}")
            for key in keys:
                if key:
                    out.setdefault(key, row)
    return out


def _asset_registry_rows(root: Path) -> Dict[str, Mapping[str, Any]]:
    data = load_json(root / "出图" / "共享" / "asset_registry.json")
    assets = data.get("assets") if isinstance(data, dict) else []
    return by_id(a for a in assets or [] if isinstance(a, Mapping))


def _row_reference_slots(row: Mapping[str, Any]) -> Any:
    return row.get("reference_slots") or row.get("reference_group") or row.get("reference_atlas")


def _row_strategy(row: Mapping[str, Any]) -> Any:
    return row.get("identity_strategy") or row.get("lock_strategy") or row.get("identity_adapters") or row.get("constraints") or row.get("drift_forbidden")


def _registry_row_with_current_slots(root: Path, registry_row: Mapping[str, Any]) -> Dict[str, Any]:
    row = dict(registry_row)
    current_slots = _registry_reference_slots(root, registry_row)
    if current_slots:
        row["reference_slots"] = current_slots
    return row


def _reference_gate_row(root: Path, contract_row: Optional[Mapping[str, Any]], registry_row: Optional[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    if isinstance(contract_row, Mapping) and isinstance(registry_row, Mapping):
        registry = _registry_row_with_current_slots(root, registry_row)
        row = dict(_merge_missing(contract_row, registry))
        if registry.get("reference_slots"):
            # Signed contracts can lag behind regenerated makeup/reference cards.
            # The registry is the durable visual evidence source, so keep the
            # contract strategy but validate against current file hashes.
            row["reference_slots"] = registry["reference_slots"]
        return row
    if isinstance(contract_row, Mapping):
        return contract_row
    if isinstance(registry_row, Mapping):
        return _registry_row_with_current_slots(root, registry_row)
    return None


def _lookup_registry_row(rows: Mapping[str, Mapping[str, Any]], entity_id: str) -> Optional[Mapping[str, Any]]:
    row = rows.get(entity_id)
    if row:
        return row
    if "/" in entity_id:
        base_id = entity_id.split("/", 1)[0].strip()
        if base_id:
            return rows.get(base_id)
    return None


def check_reference_slots(root: Path, episode: str, contract: Optional[Mapping[str, Any]], findings: List[Dict[str, Any]]) -> None:
    gate = "reference_slot_gate"
    clips = storyboard(root, episode)
    if not isinstance(contract, Mapping):
        add_finding(findings, gate, "block", relpath(root, contract_path(root, episode)), "缺 preventive_contracts.json；引用槽位/身份锁策略必须进入可签收合同。", return_to_stage="image_prompt")
        return
    ref = contract.get("reference_slots") if isinstance(contract, Mapping) and isinstance(contract.get("reference_slots"), Mapping) else {}
    contract_chars = by_id(ref.get("characters") or [] if isinstance(ref, Mapping) else [])
    contract_assets = by_id(list(ref.get("assets") or []) + list(ref.get("scenes") or []) if isinstance(ref, Mapping) else [])
    identity_rows = _identity_registry_rows(root)
    asset_rows = _asset_registry_rows(root)
    char_ids = sorted({cid for clip in clips for cid in chars_from_clip(clip)})
    asset_ids = sorted({aid for clip in clips for aid in asset_ids_from_clip(clip)})
    if not char_ids and not asset_ids:
        return
    if not status_confirmed(contract):
        add_finding(findings, gate, "block", relpath(root, contract_path(root, episode)), "preventive_contracts.status 不是 confirmed；引用槽位合同未签收。", return_to_stage="image_prompt")
    for cid in char_ids:
        row = _reference_gate_row(root, contract_chars.get(cid), _lookup_registry_row(identity_rows, cid))
        if not row or not filled(_row_reference_slots(row)):
            add_finding(findings, gate, "block", cid, f"核心/出场角色 {cid} 缺 reference_slots/reference_group。", return_to_stage="image_prompt")
            continue
        if not filled(_row_strategy(row)):
            add_finding(findings, gate, "block", cid, f"核心/出场角色 {cid} 缺 identity_strategy/identity_adapters。", return_to_stage="image_prompt")
        slot_issues = _slot_artifact_issues(root, row)
        if slot_issues:
            add_finding(findings, gate, "block", cid, f"核心/出场角色 {cid} 引用槽位未绑定真实产物：" + "；".join(slot_issues[:3]), return_to_stage="image_prompt")
    for aid in asset_ids:
        row = _reference_gate_row(root, contract_assets.get(aid), asset_rows.get(aid))
        if not row or not filled(_row_reference_slots(row)):
            add_finding(findings, gate, "block", aid, f"道具/场景 {aid} 缺 reference_slots/reference_group。", return_to_stage="image_prompt")
            continue
        if not filled(_row_strategy(row)):
            add_finding(findings, gate, "block", aid, f"道具/场景 {aid} 缺 lock_strategy/constraints。", return_to_stage="image_prompt")
        slot_issues = _slot_artifact_issues(root, row)
        if slot_issues:
            add_finding(findings, gate, "block", aid, f"道具/场景 {aid} 引用槽位未绑定真实产物：" + "；".join(slot_issues[:3]), return_to_stage="image_prompt")


def clip_needs_physics(clip: Mapping[str, Any]) -> bool:
    text = flatten(clip).lower()
    markers = (
        "持", "拿", "握", "接触", "碰", "打斗", "战斗", "追逐", "冲刺", "拥抱", "拉扯", "亲密",
        "法术", "特效", "剑气", "爆炸", "飞行", "御剑", "vfx", "magic", "fight", "combat",
        "contact", "touch", "multi_character_same_frame", "physical_interaction",
    )
    return len(chars_from_clip(clip)) >= 2 or any(m in text for m in markers)


def check_interaction_physics(root: Path, episode: str, contract: Optional[Mapping[str, Any]], findings: List[Dict[str, Any]]) -> None:
    gate = "interaction_physics_gate"
    clips = storyboard(root, episode)
    if not isinstance(contract, Mapping):
        add_finding(findings, gate, "block", relpath(root, contract_path(root, episode)), "缺 preventive_contracts.json；交互物理/动作分解必须进入可签收合同。", return_to_stage="script_stage2")
        return
    if not status_confirmed(contract):
        add_finding(findings, gate, "block", relpath(root, contract_path(root, episode)), "preventive_contracts.status 不是 confirmed；交互物理合同未签收。", return_to_stage="script_stage2")
    rows = by_id(contract.get("interaction_physics") or [] if isinstance(contract, Mapping) else [])
    for idx, clip in enumerate(clips, 1):
        if not clip_needs_physics(clip):
            continue
        cid = clip_key(clip, idx)
        row = rows.get(cid)
        if not row:
            add_finding(findings, gate, "block", cid, "高风险交互/动作/多人/特效镜缺 interaction_physics 行。", return_to_stage="script_stage2")
            continue
        missing = []
        if not filled(row.get("action_decomposition") or row.get("beats")):
            missing.append("action_decomposition")
        if not filled(row.get("degrade_plan")):
            missing.append("degrade_plan")
        if len(chars_from_clip(clip)) >= 2 and not filled(row.get("screen_positions") or row.get("character_slots")):
            missing.append("screen_positions/character_slots")
        blob = flatten(clip)
        if any(x in blob for x in ("接触", "拥抱", "拉扯", "打斗", "握", "持", "contact", "touch")) and not filled(row.get("contact_points")):
            missing.append("contact_points")
        if any(x in blob.lower() for x in ("vfx", "magic", "法术", "特效", "剑气")) and not filled(row.get("vfx_layers") or row.get("effect_cause")):
            missing.append("vfx_layers/effect_cause")
        if missing:
            add_finding(findings, gate, "block", cid, "交互物理合同缺字段：" + "、".join(missing), return_to_stage="script_stage2")


def clip_needs_audio_timing(clip: Mapping[str, Any]) -> bool:
    text = flatten(clip).lower()
    return bool(clip.get("dialogue_indices") or clip.get("voiceover_indices") or any(x in text for x in ("台词", "对白", "说话", "口型", "mouth", "lipsync", "native_speech")))


def check_audio_timing(root: Path, episode: str, contract: Optional[Mapping[str, Any]], findings: List[Dict[str, Any]]) -> None:
    gate = "audio_timing_gate"
    if not isinstance(contract, Mapping):
        add_finding(findings, gate, "block", relpath(root, contract_path(root, episode)), "缺 preventive_contracts.json；口型/字幕/声纹/时长策略必须进入可签收合同。", return_to_stage="script_stage2")
        return
    if not status_confirmed(contract):
        add_finding(findings, gate, "block", relpath(root, contract_path(root, episode)), "preventive_contracts.status 不是 confirmed；音频时长合同未签收。", return_to_stage="script_stage2")
    audio = contract.get("audio_timing") if isinstance(contract, Mapping) and isinstance(contract.get("audio_timing"), Mapping) else {}
    mode = production_mode(root)
    clips = storyboard(root, episode)
    rows = by_id(audio.get("dialogue_closeups") or [] if isinstance(audio, Mapping) else [])
    for idx, clip in enumerate(clips, 1):
        if not clip_needs_audio_timing(clip):
            continue
        cid = clip_key(clip, idx)
        row = rows.get(cid)
        if not row:
            add_finding(findings, gate, "block", cid, "对白/口型镜缺 audio_timing.dialogue_closeups 行。", return_to_stage="script_stage2")
            continue
        missing = [key for key in ("timing_source", "mouth_policy", "subtitle_policy", "voice_or_native_policy") if not filled(row.get(key))]
        if missing:
            add_finding(findings, gate, "block", cid, "对白/口型时长合同缺字段：" + "、".join(missing), return_to_stage="script_stage2")
        if "混合自动路由" in mode or "hybrid" in mode.lower() or "mixed" in mode.lower():
            route_missing = [key for key in ("audio_strategy", "timing_basis", "final_voice_stage") if not filled(row.get(key))]
            if route_missing:
                add_finding(findings, gate, "block", cid, "混合逐镜声音合同缺字段：" + "、".join(route_missing), return_to_stage="script_stage2")
            strategy = str(row.get("audio_strategy") or "")
            if strategy == "base_video_then_post_lipsync":
                if row.get("base_video_only") is not True or row.get("post_lipsync_required") is not True or "neutral" not in str(row.get("mouth_policy") or "").lower():
                    add_finding(findings, gate, "block", cid, "基础视频后置口型合同必须声明 base_video_only、post_lipsync_required 与 neutral mouth。", return_to_stage="script_stage2")
    if "先出视频后配音" in mode:
        post = audio.get("post_dub") if isinstance(audio.get("post_dub"), Mapping) else {}
        missing = [key for key in ("fit_strategy", "overflow_policy") if not filled(post.get(key))]
        if missing:
            add_finding(findings, gate, "block", relpath(root, contract_path(root, episode)), "后配音模式缺 post_dub 策略：" + "、".join(missing), return_to_stage="script_stage2")
    if "原生音画" in mode:
        native = audio.get("native_av_policy") if isinstance(audio.get("native_av_policy"), Mapping) else {}
        missing = [key for key in ("lipsync_policy", "subtitle_policy", "voice_identity_policy") if not filled(native.get(key))]
        if missing:
            add_finding(findings, gate, "block", relpath(root, contract_path(root, episode)), "原生音画模式缺 native_av_policy：" + "、".join(missing), return_to_stage="script_stage2")


def check_pilot_release(root: Path, episode: str, findings: List[Dict[str, Any]]) -> None:
    gate = "pilot_release_gate"
    if normalize_episode(episode) != "第1集":
        return
    path = production_dir(root) / f"pilot_acceptance_{episode}.json"
    data = load_json(path)
    loc = relpath(root, path)
    if not isinstance(data, Mapping):
        add_finding(findings, gate, "block", loc, "第1集缺 pilot_acceptance；先用 2-3 个代表镜头验证脸/场景/动作/口型/接缝/路由。", return_to_stage="pilot")
        return
    status = str(data.get("status") or data.get("verdict") or "").strip().lower()
    clips = data.get("clips") if isinstance(data.get("clips"), list) else []
    coverage = {str(x).strip().lower() for x in (data.get("coverage") or [])}
    checks = data.get("checks") if isinstance(data.get("checks"), Mapping) else {}
    missing_coverage = sorted(PILOT_COVERAGE - coverage)
    bad_checks = [key for key in sorted(PILOT_COVERAGE) if str(checks.get(key) or "").strip().lower() not in {"pass", "ok", "accepted"}]
    evidence_issues = pilot_acceptance_evidence_issues(root, data)
    if status not in {"pass", "accepted", "green"} or len(clips) < 2 or missing_coverage or bad_checks or evidence_issues:
        add_finding(
            findings,
            gate,
            "block",
            loc,
            f"pilot 未放行：status={status or 'unset'}, clips={len(clips)}, missing_coverage={missing_coverage}, checks_not_pass={bad_checks}。",
            return_to_stage="pilot",
        )
        for issue in evidence_issues[:8]:
            add_finding(findings, gate, "block", loc, issue, return_to_stage="pilot")


def _clip_evidence_path(row: Mapping[str, Any]) -> str:
    evidence = row.get("evidence") if isinstance(row.get("evidence"), Mapping) else {}
    for source in (row, evidence):
        rel = _artifact_path_from(source)
        if rel and not rel.endswith(".json"):
            return rel
    return ""


def _clip_qc_path(row: Mapping[str, Any]) -> str:
    evidence = row.get("evidence") if isinstance(row.get("evidence"), Mapping) else {}
    for source in (row, evidence):
        rel = str(source.get("qc_report") or source.get("qc_path") or "").strip()
        if rel:
            return rel
    return ""


def pilot_acceptance_evidence_issues(root: Path, data: Mapping[str, Any]) -> List[str]:
    issues: List[str] = []
    signoff = data.get("signoff") if isinstance(data.get("signoff"), Mapping) else {}
    reviewer = data.get("reviewer") or data.get("reviewed_by") or signoff.get("reviewer")
    if not filled(reviewer):
        issues.append("pilot_acceptance 缺 reviewer/reviewed_by 签收人。")
    if not filled(data.get("risk_selection")):
        issues.append("pilot_acceptance 缺 risk_selection（为什么选这 2-3 个代表镜头）。")
    clips = data.get("clips") if isinstance(data.get("clips"), list) else []
    for idx, row in enumerate(clips, 1):
        if not isinstance(row, Mapping):
            issues.append(f"pilot clips[{idx}] 必须是 object。")
            continue
        clip_id = row.get("clip_id") or row.get("clip") or row.get("id")
        if not filled(clip_id):
            issues.append(f"pilot clips[{idx}] 缺 clip_id。")
        rel = _clip_evidence_path(row)
        evidence = row.get("evidence") if isinstance(row.get("evidence"), Mapping) else {}
        expected = str(row.get("artifact_sha256") or row.get("sha256") or evidence.get("sha256") or "").strip().lower()
        if not rel:
            issues.append(f"pilot {clip_id or idx} 缺 artifact_path/video_path/image_path。")
        else:
            path = (root / rel).resolve() if not os.path.isabs(rel) else Path(rel)
            if not path.is_file():
                issues.append(f"pilot {clip_id or idx} artifact_path 不存在：{rel}")
            elif not expected:
                issues.append(f"pilot {clip_id or idx} 缺 artifact_sha256。")
            elif sha256_file(path).lower() != expected:
                issues.append(f"pilot {clip_id or idx} artifact_sha256 不匹配：{rel}")
        qc_rel = _clip_qc_path(row)
        if not qc_rel:
            issues.append(f"pilot {clip_id or idx} 缺 qc_report/qc_path。")
        else:
            qc_path = (root / qc_rel).resolve() if not os.path.isabs(qc_rel) else Path(qc_rel)
            if not qc_path.is_file():
                issues.append(f"pilot {clip_id or idx} qc_report 不存在：{qc_rel}")
    return issues


def build_report(root: Path, episode: str, *, stage: str, write_missing: bool = False) -> Dict[str, Any]:
    root = root.resolve()
    episode = normalize_episode(episode)
    gates = STAGE_GATES.get(stage, ())
    contract_needed = any(g != "pilot_release_gate" for g in gates)
    contract, scaffolded = load_or_scaffold(root, episode, write_missing) if contract_needed else (None, False)
    findings: List[Dict[str, Any]] = []
    check_contract_schema(root, episode, contract, gates, findings)
    check_contract_cross_refs(root, episode, contract, gates, findings)
    for gate in gates:
        if gate == "episode_promise_gate":
            check_episode_promise(root, episode, contract, findings)
        elif gate == "shot_intent_gate":
            check_shot_intent(root, episode, contract, findings)
        elif gate == "reference_slot_gate":
            check_reference_slots(root, episode, contract, findings)
        elif gate == "interaction_physics_gate":
            check_interaction_physics(root, episode, contract, findings)
        elif gate == "audio_timing_gate":
            check_audio_timing(root, episode, contract, findings)
        elif gate == "pilot_release_gate":
            check_pilot_release(root, episode, findings)
    block_n = sum(1 for f in findings if f.get("severity") == "block")
    payload = {
        "kind": "n2d_preventive_contract_report",
        "version": VERSION,
        "root": str(root),
        "episode": episode,
        "stage": stage,
        "gates": list(gates),
        "generated_at": now_iso(),
        "status": "blocked" if block_n else "pass",
        "summary": {
            "block": block_n,
            "warn": sum(1 for f in findings if f.get("severity") == "warn"),
            "info": sum(1 for f in findings if f.get("severity") == "info"),
        },
        "contract_path": relpath(root, contract_path(root, episode)) if contract_needed else "",
        "scaffolded": scaffolded,
        "findings": findings,
    }
    return payload


def render_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# n2d Preventive Contracts",
        "",
        f"- 集：{payload.get('episode')}",
        f"- stage：{payload.get('stage')}",
        f"- 状态：{payload.get('status')}",
        f"- gates：{', '.join(payload.get('gates') or [])}",
        f"- contract：{payload.get('contract_path') or '-'}",
        "",
        "| gate | severity | loc | message |",
        "|---|---|---|---|",
    ]
    for f in payload.get("findings") or []:
        msg = str(f.get("message") or "").replace("\n", " ")[:260]
        lines.append(f"| {f.get('gate')} | {f.get('severity')} | {f.get('loc')} | {msg} |")
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, episode: str, stage: str, payload: Mapping[str, Any]) -> Dict[str, str]:
    out = production_dir(root)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / OUT_JSON.format(stage=stage, episode=episode)
    md_path = out / OUT_MD.format(stage=stage, episode=episode)
    write_json_atomic(json_path, payload)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {"json": relpath(root, json_path), "markdown": relpath(root, md_path)}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="check n2d preventive contracts")
    ap.add_argument("root")
    ap.add_argument("episode")
    # 未知/拼错 stage 旧行为是 gates 空集 → 零 findings → pass/exit 0（vacuous fail-open）；
    # 用 choices fail-closed（2026-07 标准审计）。
    ap.add_argument("--stage", required=True, choices=sorted(STAGE_GATES))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--write-missing", action="store_true")
    ap.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    ep = normalize_episode(ns.episode)
    payload = build_report(root, ep, stage=ns.stage, write_missing=ns.write_missing)
    if ns.write:
        payload["outputs"] = write_outputs(root, payload["episode"], ns.stage, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
    return 2 if payload.get("status") == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
