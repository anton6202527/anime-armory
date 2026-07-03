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


KIND = "n2d_preventive_contracts"
VERSION = 1
OUT_JSON = "preventive_contracts_{stage}_{episode}.json"
OUT_MD = "preventive_contracts_{stage}_{episode}.md"
PILOT_COVERAGE = {"face", "scene", "action", "lipsync", "seam", "routing"}
PLACEHOLDER_RE = re.compile(r"(待补|待填写|TODO|TBD|__.+?__|<[^>]+>)", re.I)

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


def chars_from_clip(clip: Mapping[str, Any]) -> List[str]:
    out: List[str] = []
    for key in ("character_ids", "characters", "required_characters"):
        val = clip.get(key)
        if isinstance(val, list):
            out.extend(str(v) for v in val if str(v).strip())
        elif isinstance(val, str):
            out.extend(re.findall(r"\bCHAR[_A-Za-z0-9\u4e00-\u9fff-]+\b", val))
    out.extend(re.findall(r"\bCHAR[_A-Za-z0-9\u4e00-\u9fff-]+\b", flatten(clip)))
    return sorted(set(x.replace("-", "_") for x in out))


def asset_ids_from_clip(clip: Mapping[str, Any]) -> List[str]:
    out: List[str] = []
    loc = clip.get("location_id") or clip.get("loc_id")
    if loc:
        out.append(str(loc))
    for key in ("object_ids", "asset_ids", "prop_ids", "weapon_ids", "vfx_ids"):
        val = clip.get(key)
        if isinstance(val, list):
            out.extend(str(v) for v in val if str(v).strip())
        elif isinstance(val, str):
            out.extend(re.findall(r"\b(?:LOC|PROP|WEAPON|OUTFIT|VFX)[_A-Za-z0-9\u4e00-\u9fff-]+\b", val))
    out.extend(re.findall(r"\b(?:LOC|PROP|WEAPON|OUTFIT|VFX)[_A-Za-z0-9\u4e00-\u9fff-]+\b", flatten(clip)))
    return sorted(set(x.replace("-", "_") for x in out))


def by_id(rows: Iterable[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    out: Dict[str, Mapping[str, Any]] = {}
    for row in rows:
        key = str(row.get("id") or row.get("character_id") or row.get("asset_id") or row.get("scene_id") or row.get("clip_id") or row.get("clip") or "").strip()
        if key:
            out[key] = row
    return out


def add_finding(findings: List[Dict[str, Any]], gate: str, severity: str, loc: str, message: str, *, return_to_stage: str = "") -> None:
    row = {"gate": gate, "severity": severity, "loc": loc, "message": message}
    if return_to_stage:
        row["return_to_stage"] = return_to_stage
    findings.append(row)


def _blank_contract(root: Path, episode: str) -> Dict[str, Any]:
    clips = storyboard(root, episode)
    characters = sorted({cid for clip in clips for cid in chars_from_clip(clip)})
    assets = sorted({aid for clip in clips for aid in asset_ids_from_clip(clip)})
    high_risk = [clip_key(c, i) for i, c in enumerate(clips, 1) if clip_needs_physics(c)]
    dialogue = [clip_key(c, i) for i, c in enumerate(clips, 1) if clip_needs_audio_timing(c)]
    scenes = [a for a in assets if a.startswith("LOC")]
    non_scene_assets = [a for a in assets if not a.startswith("LOC")]
    return {
        "kind": KIND,
        "version": VERSION,
        "episode": episode,
        "status": "draft",
        "episode_promise": {
            "opening_hook": "",
            "promise": "",
            "obstacle": "",
            "payoff_or_progress": "",
            "cliffhanger": "",
        },
        "shots": [
            {
                "clip_id": clip_key(clip, idx),
                "dramatic_function": clip.get("dramatic_function") or "",
                "editing_intent": clip.get("editing_intent") or "",
                "emotional_turn": "",
                "visual_question": "",
            }
            for idx, clip in enumerate(clips, 1)
        ],
        "reference_slots": {
            "characters": [
                {"id": cid, "role": "core", "reference_slots": [], "identity_strategy": ""}
                for cid in characters
            ],
            "assets": [
                {"id": aid, "type": "asset", "reference_slots": [], "lock_strategy": ""}
                for aid in non_scene_assets
            ],
            "scenes": [
                {"id": sid, "type": "scene", "reference_slots": [], "lock_strategy": ""}
                for sid in scenes
            ],
        },
        "interaction_physics": [
            {
                "clip_id": cid,
                "risk_type": "auto_detected",
                "action_decomposition": [],
                "contact_points": [],
                "screen_positions": [],
                "vfx_layers": [],
                "degrade_plan": "",
            }
            for cid in high_risk
        ],
        "audio_timing": {
            "mode": production_mode(root),
            "post_dub": {"fit_strategy": "", "overflow_policy": ""},
            "native_av_policy": {"lipsync_policy": "", "subtitle_policy": "", "voice_identity_policy": ""},
            "dialogue_closeups": [
                {
                    "clip_id": cid,
                    "timing_source": "",
                    "mouth_policy": "",
                    "subtitle_policy": "",
                    "voice_or_native_policy": "",
                }
                for cid in dialogue
            ],
        },
    }


def scaffold(root: Path, episode: str) -> Dict[str, Any]:
    path = contract_path(root, episode)
    existing = load_json(path)
    base = _blank_contract(root, episode)
    if isinstance(existing, dict):
        merged = dict(base)
        for key, value in existing.items():
            if key in {"kind", "version", "episode"}:
                continue
            if key == "reference_slots" and isinstance(value, dict):
                ref = dict(base["reference_slots"])
                ref.update(value)
                merged[key] = ref
            elif key == "audio_timing" and isinstance(value, dict):
                audio = dict(base["audio_timing"])
                audio.update(value)
                merged[key] = audio
            else:
                merged[key] = value
        base = merged
    write_json_atomic(path, base)
    return base


def load_or_scaffold(root: Path, episode: str, write_missing: bool) -> Tuple[Optional[Dict[str, Any]], bool]:
    path = contract_path(root, episode)
    data = load_json(path)
    if isinstance(data, dict):
        return data, False
    if write_missing:
        return scaffold(root, episode), True
    return None, False


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
        source.update({k: v for k, v in dict(rows.get(cid, {})).items() if v not in (None, "", [], {})})
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
        ids = [str(char.get("id") or char.get("character_id") or char.get("name") or "")]
        for key in ids:
            if key:
                out[key] = char
        for form in char.get("forms") or []:
            if isinstance(form, Mapping):
                ids.extend(str(form.get(k) or "") for k in ("id", "asset_key", "form"))
                row = dict(char)
                row.update(form)
                for key in ids:
                    if key:
                        out[key] = row
    return out


def _asset_registry_rows(root: Path) -> Dict[str, Mapping[str, Any]]:
    data = load_json(root / "出图" / "共享" / "asset_registry.json")
    assets = data.get("assets") if isinstance(data, dict) else []
    return by_id(a for a in assets or [] if isinstance(a, Mapping))


def _row_reference_slots(row: Mapping[str, Any]) -> Any:
    return row.get("reference_slots") or row.get("reference_group") or row.get("reference_atlas")


def _row_strategy(row: Mapping[str, Any]) -> Any:
    return row.get("identity_strategy") or row.get("lock_strategy") or row.get("identity_adapters") or row.get("constraints") or row.get("drift_forbidden")


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
        row = contract_chars.get(cid) or identity_rows.get(cid)
        if not row or not filled(_row_reference_slots(row)):
            add_finding(findings, gate, "block", cid, f"核心/出场角色 {cid} 缺 reference_slots/reference_group。", return_to_stage="image_prompt")
            continue
        if not filled(_row_strategy(row)):
            add_finding(findings, gate, "block", cid, f"核心/出场角色 {cid} 缺 identity_strategy/identity_adapters。", return_to_stage="image_prompt")
    for aid in asset_ids:
        row = contract_assets.get(aid) or asset_rows.get(aid)
        if not row or not filled(_row_reference_slots(row)):
            add_finding(findings, gate, "block", aid, f"道具/场景 {aid} 缺 reference_slots/reference_group。", return_to_stage="image_prompt")
            continue
        if not filled(_row_strategy(row)):
            add_finding(findings, gate, "block", aid, f"道具/场景 {aid} 缺 lock_strategy/constraints。", return_to_stage="image_prompt")


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
    if status not in {"pass", "accepted", "green"} or len(clips) < 2 or missing_coverage or bad_checks:
        add_finding(
            findings,
            gate,
            "block",
            loc,
            f"pilot 未放行：status={status or 'unset'}, clips={len(clips)}, missing_coverage={missing_coverage}, checks_not_pass={bad_checks}。",
            return_to_stage="pilot",
        )


def build_report(root: Path, episode: str, *, stage: str, write_missing: bool = False) -> Dict[str, Any]:
    root = root.resolve()
    episode = normalize_episode(episode)
    gates = STAGE_GATES.get(stage, ())
    contract_needed = any(g != "pilot_release_gate" for g in gates)
    contract, scaffolded = load_or_scaffold(root, episode, write_missing) if contract_needed else (None, False)
    findings: List[Dict[str, Any]] = []
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
    ap.add_argument("--stage", required=True)
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
