#!/usr/bin/env python3
"""Evidence-led production-mode routing for n2d episodes.

The router recommends; it never rewrites ``_设置.md`` and never turns a fuzzy
score into a blocking gate.  A user's explicit project choice remains the
decision, while the report makes timing/rework consequences visible before
storyboard or paid video work.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

try:
    from n2d_const import PRODUCTION_MODE_DEFAULT
    from n2d_logic import normalize_production_mode
    from settings import get_setting, project_setting_source
    from signoff_contract import artifact_fingerprint
    from voice_preproduction import (
        casting_path,
        is_narration_role,
        load_voiceover,
        role_entry,
        timing_path,
    )
except ImportError:  # pragma: no cover
    from .n2d_const import PRODUCTION_MODE_DEFAULT
    from .n2d_logic import normalize_production_mode
    from .settings import get_setting, project_setting_source
    from .signoff_contract import artifact_fingerprint
    from .voice_preproduction import (
        casting_path,
        is_narration_role,
        load_voiceover,
        role_entry,
        timing_path,
    )


KIND = "n2d_production_mode_route"
VERSION = 2
NARRATOR_TOKENS = ("旁白", "画外", "内心", "心声", "系统音", "narrator", "voiceover", "v.o.")
ACTION_TOKENS = ("fight", "combat", "action", "追逐", "打斗", "飞行", "montage", "空镜", "动作")
CLOSEUP_TOKENS = ("cu", "mcu", "close-up", "closeup", "近景", "特写", "正反打", "shot_reverse")
SOUND_STRATEGIES = {
    "performance_audio_first",
    "base_video_then_post_lipsync",
    "rough_timing_final_dub_later",
    "post_dub",
    "picture_first",
    "native_av",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _yes(value: Any) -> bool:
    if value is True:
        return True
    return str(value or "").strip().lower() in {"yes", "true", "1", "是", "有", "visible"}


def _clip_id(row: Mapping[str, Any], index: int) -> str:
    raw = str(row.get("clip_id") or row.get("clip") or row.get("id") or "").strip()
    match = re.search(r"(?:clip|镜头)[_\s-]?(\d+)", raw, re.I)
    return f"Clip_{int(match.group(1)):02d}" if match else (raw or f"Clip_{index:02d}")


def _indices(value: Any) -> List[int]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    out: List[int] = []
    for item in value:
        try:
            number = int(item)
        except (TypeError, ValueError):
            continue
        if number > 0 and number not in out:
            out.append(number)
    return out


def _clip_line_indices(row: Mapping[str, Any]) -> List[int]:
    out: List[int] = []
    for key in (
        "voiceover_indices", "line_indices", "dialogue_indices",
        "allowed_character_dialogue_indices", "allowed_narration_indices",
    ):
        for item in _indices(row.get(key)):
            if item not in out:
                out.append(item)
    return out


def _relative_existing(root: Path, value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    path = Path(raw)
    path = path if path.is_absolute() else root / path
    if not path.is_file():
        return ""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def _guide_audio_paths(root: Path, row: Mapping[str, Any], episode: str = "", line_indices: Sequence[int] = ()) -> List[str]:
    continuity = row.get("continuity") if isinstance(row.get("continuity"), Mapping) else {}
    values: List[Any] = []
    for target in (row, continuity):
        for key in ("performance_audio", "guide_audio", "audio_input", "performance_track", "dialogue_audio"):
            value = target.get(key)
            values.extend(value if isinstance(value, list) else [value])
    out = [path for path in (_relative_existing(root, value) for value in values) if path]
    if episode:
        for line_index in line_indices:
            path = root / "合成" / episode / "配音_导引" / f"line_{int(line_index) - 1:02d}.wav"
            if path.is_file():
                rel = path.relative_to(root).as_posix()
                if rel not in out:
                    out.append(rel)
    return out


def _base_video_exists(root: Path, episode: str, cid: str) -> bool:
    folder = root / "出视频" / episode / "视频"
    if not folder.is_dir():
        return False
    compact = re.sub(r"[^a-z0-9]", "", cid.lower())
    for path in folder.glob("*.mp4"):
        name = re.sub(r"[^a-z0-9]", "", path.stem.lower())
        if compact and compact in name and not any(token in path.name.lower() for token in ("noaudio", "_raw")):
            return True
    return False


def _previous_sound_routes(root: Path, episode: str) -> Dict[str, Dict[str, Any]]:
    candidates = (
        (root / "出视频" / episode / "prompt" / "video_model_routes.json", "routes"),
        (root / "生产数据" / f"production_mode_route_{episode}.json", "clip_routes"),
    )
    for path, key in candidates:
        payload = _load_json(path)
        rows = payload.get(key) if isinstance(payload, Mapping) else []
        if isinstance(rows, list) and rows:
            return {
                _clip_id(row, idx): dict(row)
                for idx, row in enumerate(rows, 1)
                if isinstance(row, Mapping)
            }
    return {}


def _manifest_placeholder(manifest: Any) -> bool:
    if not isinstance(manifest, list) or not manifest:
        return False
    blob = json.dumps(manifest, ensure_ascii=False).lower()
    return any(
        isinstance(row, Mapping) and (
            row.get("占位") is True
            or row.get("placeholder") is True
            or str(row.get("voice_key") or "").startswith("say:")
        )
        for row in manifest
    ) or "placeholder" in blob


def _casting_locked(entry: Mapping[str, Any]) -> bool:
    return str(entry.get("status") or "").strip().lower() in {"locked", "已锁定", "approved", "定妆通过"}


def build_clip_sound_routes(
    root: Path,
    episode: str,
    clips: Sequence[Mapping[str, Any]],
    voice_lines: Sequence[Mapping[str, Any]],
    *,
    casting: Mapping[str, Any],
    timing_estimate: Mapping[str, Any],
    final_manifest: Any,
    previous_routes: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Route sound per Clip; never synthesize audio or mutate the storyboard."""
    ep = str(episode)
    line_by_index = {int(row.get("index") or 0): row for row in voice_lines if int(row.get("index") or 0) > 0}
    final_ready = isinstance(final_manifest, list) and bool(final_manifest) and not _manifest_placeholder(final_manifest)
    estimate_ready = (
        isinstance(timing_estimate, Mapping)
        and timing_estimate.get("kind") == "n2d_timing_estimate"
        and bool(timing_estimate.get("lines"))
    )
    routes: List[Dict[str, Any]] = []
    for index, row in enumerate(clips, 1):
        cid = _clip_id(row, index)
        blob = json.dumps(row, ensure_ascii=False).lower()
        indices = _clip_line_indices(row)
        line_rows = [line_by_index[item] for item in indices if item in line_by_index]
        roles = sorted({str(item.get("角色") or "").strip() for item in line_rows if str(item.get("角色") or "").strip()})
        declared_dialogue_indices = _indices(row.get("dialogue_indices")) or _indices(row.get("allowed_character_dialogue_indices"))
        declared_narration_indices = _indices(row.get("narration_indices")) or _indices(row.get("allowed_narration_indices"))
        tracks_declared = any(
            key in row
            for key in (
                "dialogue_indices", "narration_indices",
                "allowed_character_dialogue_indices", "allowed_narration_indices",
            )
        )
        if tracks_declared:
            character_lines = [item for item in line_rows if int(item.get("index") or 0) in declared_dialogue_indices]
            narration_lines = [item for item in line_rows if int(item.get("index") or 0) in declared_narration_indices]
        else:
            character_lines = [item for item in line_rows if not is_narration_role(str(item.get("角色") or ""))]
            narration_lines = [item for item in line_rows if is_narration_role(str(item.get("角色") or ""))]
        explicit_dialogue = bool(
            _indices(row.get("dialogue_indices"))
            or _indices(row.get("allowed_character_dialogue_indices"))
            or str(row.get("dialogue") or "").strip()
            or str(row.get("speech") or "").strip()
        )
        has_character_dialogue = bool(character_lines or explicit_dialogue)
        narration_only = bool(narration_lines or _indices(row.get("allowed_narration_indices"))) and not has_character_dialogue
        continuity = row.get("continuity") if isinstance(row.get("continuity"), Mapping) else {}
        mouth_declared = "mouth_visible" in row or "mouth_visible" in continuity
        mouth_visible = _yes(row.get("mouth_visible")) or _yes(continuity.get("mouth_visible"))
        if not mouth_declared and has_character_dialogue and any(token in blob for token in CLOSEUP_TOKENS):
            mouth_visible = True
        native_policy = str(row.get("native_audio_policy") or row.get("speech_policy") or "").strip().lower()
        native_explicit = native_policy == "native_speech" or str(row.get("audio_strategy") or "").strip() == "native_av"
        action_or_montage = any(token in blob for token in ACTION_TOKENS)

        guide_paths = _guide_audio_paths(root, row, ep, indices)
        final_paths: List[str] = []
        if final_ready:
            for line_index in indices:
                path = root / "合成" / ep / "配音" / f"line_{line_index - 1:02d}.wav"
                if path.is_file():
                    final_paths.append(path.relative_to(root).as_posix())
        performance_paths = final_paths or guide_paths
        performance_status = "final_ready" if final_paths else ("guide_ready" if guide_paths else "missing")

        override = str(row.get("audio_strategy") or row.get("sound_strategy") or "").strip()
        if override and override not in SOUND_STRATEGIES:
            override = ""
        previous = dict((previous_routes or {}).get(cid) or {})
        base_route_committed = bool(
            not override
            and str(previous.get("audio_strategy") or "") == "base_video_then_post_lipsync"
            and previous.get("base_video_only") is True
            and _base_video_exists(root, ep, cid)
        )
        if base_route_committed:
            # Once paid/generated base pixels exist, final audio arriving later
            # should drive the promised post-performance pass, not trigger a
            # second full video generation route.
            strategy = "base_video_then_post_lipsync"
        elif override:
            strategy = override
        elif native_explicit:
            strategy = "native_av"
        elif has_character_dialogue and mouth_visible:
            strategy = "performance_audio_first" if performance_paths else "base_video_then_post_lipsync"
        elif narration_only:
            strategy = "rough_timing_final_dub_later"
        elif has_character_dialogue:
            strategy = "post_dub"
        elif action_or_montage:
            strategy = "picture_first"
        else:
            strategy = "picture_first"

        if final_paths:
            timing_basis = "final_voice"
        elif guide_paths:
            timing_basis = "performance_guide"
        elif estimate_ready and indices:
            timing_basis = "text_estimate_no_audio"
        else:
            timing_basis = "storyboard_duration"

        role_states = [role_entry(casting, role) for role in roles]
        lock_status = (
            "locked" if role_states and all(_casting_locked(entry) for entry in role_states)
            else ("not_applicable" if not roles else "pending")
        )
        final_voice_required = bool((has_character_dialogue or narration_only) and strategy != "native_av")
        post_lipsync_required = strategy == "base_video_then_post_lipsync"
        route: Dict[str, Any] = {
            "clip_id": cid,
            "line_indices": indices,
            "roles": roles,
            "content_class": (
                "native_av" if strategy == "native_av"
                else "visible_mouth_dialogue" if has_character_dialogue and mouth_visible
                else "narration_or_offscreen" if narration_only
                else "offscreen_or_nonvisible_dialogue" if has_character_dialogue
                else "action_montage_or_picture"
            ),
            "audio_strategy": strategy,
            "timing_basis": timing_basis,
            "performance_track_status": performance_status,
            "performance_audio_paths": performance_paths,
            "voice_lock_status": lock_status,
            "mouth_visible": mouth_visible,
            "final_voice_required": final_voice_required,
            "requires_voice_lock_before_final_render": final_voice_required,
            "requires_performance_audio_before_final": bool(has_character_dialogue and mouth_visible and strategy != "native_av"),
            "post_lipsync_required": post_lipsync_required,
            "post_lipsync_output": (
                f"出视频/{ep}/视频_lipsync/{cid}_lipsync.mp4"
                if post_lipsync_required else ""
            ),
            "base_video_only": post_lipsync_required,
            "base_video_mouth_policy": "neutral_rest_no_visible_articulation" if post_lipsync_required else "route_default",
            "can_generate_base_video": True,
            "can_generate_final_performance": bool(
                strategy == "native_av" or performance_paths or not (has_character_dialogue and mouth_visible)
            ),
            "route_commitment": "base_plate_already_generated" if base_route_committed else "uncommitted",
            "final_voice_stage": (
                "native_generation" if strategy == "native_av"
                else "post_lipsync_before_compose" if post_lipsync_required
                else "post_video_before_compose" if final_voice_required
                else "optional_post"
            ),
            "timing_estimate_path": (
                str(timing_path(root, ep).relative_to(root)) if estimate_ready else ""
            ),
        }
        if post_lipsync_required:
            route["warning"] = (
                "当前只允许生成不含可见发音动作的基础视频；音色/表演轨就绪后必须走独立后期表演驱动，"
                "该基础视频不能直接冒充最终说话镜。"
            )
        routes.append(route)
    return routes


def _voice_signals(text: str) -> Dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    narration = []
    dialogue = []
    for line in lines:
        head = line.split("]", 1)[0].lower()
        (narration if any(token.lower() in head for token in NARRATOR_TOKENS) else dialogue).append(line)
    return {
        "spoken_line_count": len(lines),
        "character_dialogue_count": len(dialogue),
        "narration_count": len(narration),
        "sample": lines[:5],
    }


def collect_signals(root: Path, episode: str) -> Dict[str, Any]:
    ep = episode if episode.startswith("第") and episode.endswith("集") else f"第{episode}集"
    voice_path = root / "脚本" / ep / "voiceover.txt"
    voice = _voice_signals(_read(voice_path))
    storyboard = _load_json(root / "脚本" / ep / "storyboard.json")
    clips = [row for row in storyboard.get("clips") or [] if isinstance(row, Mapping)]
    speaking_clips = 0
    mouth_visible = 0
    closeup_speaking = 0
    native_speech = 0
    action_clips = 0
    for row in clips:
        blob = json.dumps(row, ensure_ascii=False).lower()
        tracks_declared = any(
            key in row
            for key in (
                "dialogue_indices", "narration_indices",
                "allowed_character_dialogue_indices", "allowed_narration_indices",
            )
        )
        has_dialogue = bool(
            row.get("dialogue_indices")
            or row.get("allowed_character_dialogue_indices")
            or (not tracks_declared and row.get("voiceover_indices"))
            or row.get("dialogue")
            or row.get("speech")
        )
        policy = row.get("native_audio_policy") or row.get("speech_policy")
        if "native_speech" in str(policy or "").lower():
            native_speech += 1
            has_dialogue = True
        if has_dialogue:
            speaking_clips += 1
        continuity = row.get("continuity") if isinstance(row.get("continuity"), Mapping) else {}
        is_mouth = _yes(row.get("mouth_visible")) or _yes(continuity.get("mouth_visible"))
        if is_mouth:
            mouth_visible += 1
        if has_dialogue and is_mouth and any(token in blob for token in CLOSEUP_TOKENS):
            closeup_speaking += 1
        if any(token in blob for token in ACTION_TOKENS):
            action_clips += 1
    manifest_path = root / "合成" / ep / "配音" / "时长清单.json"
    try:
        timing_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else []
    except Exception:
        timing_manifest = []
    placeholder_timing = _manifest_placeholder(timing_manifest)
    estimate = _load_json(timing_path(root, ep))
    casting = _load_json(casting_path(root))
    return {
        "episode": ep,
        "voiceover_present": voice_path.is_file(),
        **voice,
        "storyboard_clip_count": len(clips),
        "speaking_clip_count": speaking_clips,
        "mouth_visible_clip_count": mouth_visible,
        "closeup_speaking_clip_count": closeup_speaking,
        "native_speech_clip_count": native_speech,
        "action_or_montage_clip_count": action_clips,
        "timing_manifest_present": bool(timing_manifest),
        "final_voice_manifest_present": bool(timing_manifest) and not placeholder_timing,
        "timing_estimate_present": estimate.get("kind") == "n2d_timing_estimate" and bool(estimate.get("lines")),
        "voice_casting_status": str(casting.get("status") or "missing"),
        "placeholder_timing": placeholder_timing,
    }


def recommend_mode(signals: Mapping[str, Any], selected_mode: str) -> Dict[str, Any]:
    selected = normalize_production_mode(selected_mode)
    spoken = int(signals.get("spoken_line_count") or 0)
    speaking_clips = int(signals.get("speaking_clip_count") or 0)
    native = int(signals.get("native_speech_clip_count") or 0)
    closeup = int(signals.get("closeup_speaking_clip_count") or 0)
    clip_count = int(signals.get("storyboard_clip_count") or 0)
    action = int(signals.get("action_or_montage_clip_count") or 0)
    voiceover_present = bool(signals.get("voiceover_present"))
    placeholder = bool(signals.get("placeholder_timing"))
    reasons: List[str] = []
    risks: List[Dict[str, str]] = []
    strategy_counts = signals.get("audio_strategy_counts") if isinstance(signals.get("audio_strategy_counts"), Mapping) else {}
    active_strategies = {str(key) for key, value in strategy_counts.items() if int(value or 0) > 0}

    if selected == "原生音画":
        recommended = "原生音画"
        reasons.append(f"项目已显式 opt-in 原生音画；保持该制作决定，不由启发式路由擅自降回配音链。")
        if native > 0:
            reasons.append(f"分镜已声明 {native} 个 native_speech Clip。")
    elif not voiceover_present and clip_count == 0:
        recommended = PRODUCTION_MODE_DEFAULT
        reasons.append("尚无 voiceover/storyboard 证据；采用新项目默认的混合自动路由，待分镜出现后刷新逐镜声音路线。")
        risks.append({"code": "insufficient_evidence", "level": "low", "message": "待阶段1脚本或分镜生成后刷新逐镜路线。"})
    elif len(active_strategies) > 1 or selected == "混合自动路由":
        recommended = "混合自动路由"
        reasons.append(
            "本集同时包含不同声音需求，按镜头路由：可见口型对白走表演音轨/后期表演驱动，"
            "旁白与口外音只锁估算节奏，动作/空镜画面先行，native_speech 镜单独处理。"
        )
        if closeup:
            reasons.append(f"其中 {closeup} 个近景/正反打说话 Clip 需要表演音轨或明确的后期口型通道，不要求整集最终配音前置。")
    elif active_strategies == {"performance_audio_first"}:
        recommended = "配音先行"
        reasons.append("全部镜头都由可见口型对白主导且已有表演音轨，固定配音先行可减少路由复杂度。")
    elif active_strategies and active_strategies <= {"picture_first"}:
        recommended = "先出视频后配音"
        reasons.append(
            f"现有脚本/分镜未检测到口播或对白（动作/空镜/蒙太奇候选 {action}/{clip_count}）；"
            "可先锁画面，再在后期加声音层。"
        )
    else:
        recommended = "混合自动路由" if (spoken > 0 or speaking_clips > 0) else "先出视频后配音"
        reasons.append("证据不足以把全项目锁成单一声音顺序；优先保持逐镜混合路线。")

    if selected == "先出视频后配音" and (spoken > 0 or speaking_clips > 0):
        risks.append({"code": "uniform_video_first_rework", "level": "medium", "message": "统一画面先行会把说话镜也按粗时长生成；建议只让动作/空镜画面先行。"})
        if placeholder:
            risks.append({"code": "placeholder_audio_waste", "level": "medium", "message": "不要为估时生成整集占位 WAV；改用 timing_estimate.json。"})

    if selected == "原生音画" and native == 0:
        risks.append({"code": "native_contract_missing", "level": "medium", "message": "项目选择原生音画，但 storyboard 尚无 native_speech Clip 合同；先补声源/口型/后期策略。"})
    if selected not in {"原生音画", "混合自动路由"} and native > 0:
        risks.append({"code": "native_mode_conflict", "level": "high", "message": "storyboard 含 native_speech，但项目未 opt-in 原生音画；应删除该合同或由用户显式改制作模式。"})
    return {
        "selected_mode": selected,
        "recommended_mode": recommended,
        "aligned": selected == recommended,
        "reasons": reasons,
        "risks": risks,
        "advisory_only": True,
    }


def build_route(root: Path, episode: str) -> Dict[str, Any]:
    root = root.resolve()
    signals = collect_signals(root, episode)
    selected = str(get_setting(str(root), "制作模式", PRODUCTION_MODE_DEFAULT) or PRODUCTION_MODE_DEFAULT)
    source = str(project_setting_source(str(root), "制作模式") or "default")
    ep = str(signals["episode"])
    _source, voice_lines, _fingerprint = load_voiceover(root, ep)
    storyboard = _load_json(root / "脚本" / ep / "storyboard.json")
    clips = [row for row in storyboard.get("clips") or [] if isinstance(row, Mapping)]
    casting = _load_json(casting_path(root))
    estimate = _load_json(timing_path(root, ep))
    try:
        final_manifest = json.loads((root / "合成" / ep / "配音" / "时长清单.json").read_text(encoding="utf-8"))
    except Exception:
        final_manifest = []
    clip_routes = build_clip_sound_routes(
        root, ep, clips, voice_lines, casting=casting,
        timing_estimate=estimate, final_manifest=final_manifest,
        previous_routes=_previous_sound_routes(root, ep),
    )
    strategy_counts: Dict[str, int] = {}
    for route in clip_routes:
        strategy = str(route.get("audio_strategy") or "unknown")
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
    signals["audio_strategy_counts"] = strategy_counts
    signals["final_voice_required_clip_count"] = sum(1 for row in clip_routes if row.get("final_voice_required"))
    signals["post_lipsync_clip_count"] = sum(1 for row in clip_routes if row.get("post_lipsync_required"))
    decision = recommend_mode(signals, selected)
    inputs = [
        "_设置.md",
        f"脚本/{ep}/voiceover.txt",
        f"脚本/{ep}/storyboard.json",
        f"合成/{ep}/配音/时长清单.json",
        f"合成/{ep}/配音/timing_estimate.json",
        "设定库/voice_casting.json",
    ]
    return {
        "kind": KIND,
        "version": VERSION,
        "episode": ep,
        "generated_at": now_iso(),
        "status": "aligned" if decision["aligned"] else "review_recommended",
        "mode_source": source,
        "decision": decision,
        "signals": signals,
        "clip_routes": clip_routes,
        "summary": {
            "clip_count": len(clip_routes),
            "audio_strategy_counts": strategy_counts,
            "final_voice_required": any(row.get("final_voice_required") for row in clip_routes),
            "post_lipsync_required": any(row.get("post_lipsync_required") for row in clip_routes),
            "base_video_only_count": sum(1 for row in clip_routes if row.get("base_video_only")),
        },
        "inputs_fingerprint": artifact_fingerprint(root, inputs),
        "next": (
            "执行逐镜声音路线；最终配音只在音色锁定后批量渲染。" if decision["aligned"]
            else "这是建议而非硬门：若接受推荐，用 n2d-settings 修改制作模式；旧模式仍可显式固定，风险会逐镜留痕。"
        ),
    }


def write_route(root: Path, payload: Mapping[str, Any]) -> Dict[str, str]:
    ep = str(payload.get("episode") or "")
    out = root / "生产数据"
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"production_mode_route_{ep}.json"
    md_path = out / f"production_mode_route_{ep}.md"
    tmp = json_path.with_name(f"{json_path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, json_path)
    decision = payload.get("decision") if isinstance(payload.get("decision"), Mapping) else {}
    signals = payload.get("signals") if isinstance(payload.get("signals"), Mapping) else {}
    lines = [
        f"# {ep} 制作模式路由",
        "",
        f"- 状态：{payload.get('status')}",
        f"- 当前模式：{decision.get('selected_mode')}（source={payload.get('mode_source')}）",
        f"- 推荐模式：{decision.get('recommended_mode')}",
        "- 性质：项目模式建议 + 逐镜执行合同；不自动改 `_设置.md`，分类启发式本身不作硬门。",
        "",
        "## 证据",
        "",
        f"- 口播文本：{signals.get('spoken_line_count', 0)}",
        f"- 说话 Clip：{signals.get('speaking_clip_count', 0)}",
        f"- 近景/正反打说话 Clip：{signals.get('closeup_speaking_clip_count', 0)}",
        f"- native_speech Clip：{signals.get('native_speech_clip_count', 0)}",
        f"- 占位时长：{signals.get('placeholder_timing')}",
        f"- 无 WAV 时间估算：{signals.get('timing_estimate_present')}",
        f"- 声音选角状态：{signals.get('voice_casting_status')}",
        "",
        "## 理由",
        "",
        *[f"- {item}" for item in decision.get("reasons") or []],
    ]
    if decision.get("risks"):
        lines += ["", "## 风险", "", *[f"- [{row.get('level')}] {row.get('message')}" for row in decision["risks"]]]
    clip_routes = payload.get("clip_routes") if isinstance(payload.get("clip_routes"), list) else []
    if clip_routes:
        lines += [
            "", "## 逐镜声音路线", "",
            "| Clip | 内容 | 时间基准 | 声音策略 | 表演轨 | 音色锁 | 最终声音阶段 |",
            "|---|---|---|---|---|---|---|",
        ]
        for row in clip_routes:
            lines.append(
                "| {clip} | {content} | {timing} | {strategy} | {track} | {lock} | {stage} |".format(
                    clip=row.get("clip_id", ""), content=row.get("content_class", ""),
                    timing=row.get("timing_basis", ""), strategy=row.get("audio_strategy", ""),
                    track=row.get("performance_track_status", ""), lock=row.get("voice_lock_status", ""),
                    stage=row.get("final_voice_stage", ""),
                )
            )
    tmp_md = md_path.with_name(f"{md_path.name}.tmp.{os.getpid()}")
    tmp_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    os.replace(tmp_md, md_path)
    return {"json": str(json_path), "markdown": str(md_path)}
