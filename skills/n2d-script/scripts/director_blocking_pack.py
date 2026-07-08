#!/usr/bin/env python3
"""P-2 director blocking pack gate for n2d.

This is the director previsualization layer between stage 1 voiceover and
stage 2 storyboard. It scaffolds and checks the per-episode documents that
lock dramatic beats, blocking, axis/eyeline, shot progression, transitions,
vertical composition, and edit rhythm before expensive downstream work.

Usage:
  python3 director_blocking_pack.py <作品根> 第N集 scaffold --write
  python3 director_blocking_pack.py <作品根> 第N集 check --json --write-missing
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

KIND = "n2d_director_blocking_pack"
CHECK_KIND = "n2d_director_blocking_pack_check"
VERSION = 1
PLACEHOLDER_RE = re.compile(r"(待补|待填写|TODO|TBD|__.+?__|<[^>]+>)", re.I)

REQUIRED_FILES = (
    "director_beat_sheet.json",
    "axis_blocking_map.json",
    "shot_progression_plan.json",
    "transition_map.json",
    "vertical_composition_plan.json",
    "edit_rhythm_map.json",
)
SHOT_REVERSE_PATTERN_FIELDS = (
    "pattern_id",
    "applies_to",
    "axis_line",
    "screen_sides",
    "eyeline_match",
    "shot_pairing",
    "coverage_order",
    "camera_coverage",
    "lens_height_distance_match",
    "crossing_axis_policy",
    "buffer_or_reestablishing",
    "continuity_must",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def episode_label(value: str) -> str:
    value = str(value or "").strip()
    if value.startswith("第") and value.endswith("集"):
        return value
    return f"第{value}集"


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    write_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_json_if_absent(path: Path, payload: Mapping[str, Any], *, force: bool = False) -> bool:
    if path.exists() and not force:
        return False
    write_json_atomic(path, payload)
    return True


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _episode_dir(root: Path, ep: str) -> Path:
    return root / "脚本" / ep


def _voiceover_lines(root: Path, ep: str, *, limit: int | None = None) -> List[str]:
    path = _episode_dir(root, ep) / "voiceover.txt"
    if not path.is_file():
        return []
    lines: List[str] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        text = raw.strip()
        if not text or text.startswith("#") or text.startswith("---"):
            continue
        text = re.sub(r"^\s*(?:[-*]|\d+[.)、])\s*", "", text)
        if text:
            lines.append(text[:80])
        if limit is not None and len(lines) >= limit:
            break
    return lines


def _beat_ids(lines: List[str]) -> List[str]:
    count = max(3, len(lines) or 3)
    return [f"Beat_{idx:02d}" for idx in range(1, count + 1)]


def _storyboard(root: Path, ep: str) -> Dict[str, Any]:
    data = load_json(_episode_dir(root, ep) / "storyboard.json")
    return data if isinstance(data, dict) else {}


def _storyboard_clips(root: Path, ep: str) -> List[Dict[str, Any]]:
    clips = _storyboard(root, ep).get("clips") or []
    return [c for c in clips if isinstance(c, dict)]


def _storyboard_ids(clips: List[Mapping[str, Any]]) -> List[str]:
    ids: List[str] = []
    for idx, clip in enumerate(clips, start=1):
        cid = str(clip.get("id") or "").strip() or f"Clip_{idx:02d}"
        ids.append(cid)
    return ids


def _clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or f"Clip_{idx:02d}").strip()


def _planning_ids(root: Path, ep: str, lines: List[str]) -> List[str]:
    clips = _storyboard_clips(root, ep)
    return _storyboard_ids(clips) if clips else _beat_ids(lines)


def _visual_contract(root: Path, ep: str) -> Mapping[str, Any]:
    vc = _storyboard(root, ep).get("visual_contract")
    return vc if isinstance(vc, Mapping) else {}


def _clean_text(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    if not text or PLACEHOLDER_RE.search(text):
        return fallback
    return text


def _clip_contract(clip: Mapping[str, Any]) -> Mapping[str, Any]:
    data = clip.get("template_contract")
    return data if isinstance(data, Mapping) else {}


def _clip_continuity(clip: Mapping[str, Any]) -> Mapping[str, Any]:
    data = clip.get("continuity")
    return data if isinstance(data, Mapping) else {}


def _clip_line(clip: Mapping[str, Any]) -> str:
    for key in ("subtitle_lines", "screen_text_lines"):
        values = clip.get(key)
        if isinstance(values, list):
            for item in values:
                text = str(item or "").strip()
                if text:
                    return text[:100]
    return _clean_text(clip.get("rhythm"), "按 storyboard 镜头节奏执行")


def _clip_story_function(clip: Mapping[str, Any]) -> str:
    contract = _clip_contract(clip)
    return _clean_text(
        clip.get("dramatic_function") or contract.get("story_function"),
        f"{_clean_text(clip.get('rhythm'), '剧情推进')}：把本镜信息用动作、反应和空间关系拍清楚",
    )


def _clip_audience_effect(clip: Mapping[str, Any]) -> str:
    return _clean_text(
        clip.get("audience_effect"),
        "观众能在静音竖屏下看懂局势变化和下一步悬念",
    )


def _clip_shot_size(clip: Mapping[str, Any]) -> str:
    cont = _clip_continuity(clip)
    return _clean_text(cont.get("shot_size"), "按 storyboard 已锁景别推进")


def _clip_camera_rule(clip: Mapping[str, Any]) -> str:
    contract = _clip_contract(clip)
    return _clean_text(
        contract.get("camera_path") or contract.get("camera_rule"),
        "镜头服务角色反应和信息交接，保持轴线稳定",
    )


def _clip_post_cues(clip: Mapping[str, Any]) -> str:
    cues = _clip_contract(clip).get("post_cue_points")
    if isinstance(cues, list):
        text = "；".join(str(x).strip() for x in cues if str(x).strip())
        if text:
            return text
    return "环境声先稳住空间，剪点处用短促音效托住信息落点"


def _clip_subject_zone(clip: Mapping[str, Any]) -> str:
    slots = clip.get("character_slots") if isinstance(clip.get("character_slots"), list) else []
    rows: List[str] = []
    for slot in slots:
        if isinstance(slot, Mapping):
            cid = str(slot.get("character_id") or "").strip()
            pos = str(slot.get("screen_position") or slot.get("zone") or "").strip()
            if cid or pos:
                rows.append(f"{cid}: {pos}".strip(": "))
    positions = clip.get("screen_positions") if isinstance(clip.get("screen_positions"), Mapping) else {}
    for cid, pos in positions.items():
        row = f"{cid}: {pos}"
        if row not in rows:
            rows.append(row)
    return "；".join(rows) or "主体锁中上安全区，反应脸保留竖屏可读尺度"


def _clip_chars(clip: Mapping[str, Any]) -> str:
    chars = [str(x).strip() for x in clip.get("character_ids") or [] if str(x).strip()]
    return "、".join(chars) if chars else "无具名角色"


def _clip_location(clip: Mapping[str, Any]) -> str:
    return str(clip.get("location_id") or clip.get("scene_id") or clip.get("scene") or "LOC_01").strip()


def _screen_sides_from_clip(clip: Mapping[str, Any]) -> Dict[str, str]:
    sides: Dict[str, str] = {}
    slots = clip.get("character_slots") if isinstance(clip.get("character_slots"), list) else []
    for slot in slots:
        if not isinstance(slot, Mapping):
            continue
        cid = str(slot.get("character_id") or slot.get("id") or "").strip()
        pos = str(slot.get("screen_position") or slot.get("zone") or slot.get("slot") or "").strip()
        if not cid:
            continue
        if "左" in pos or "left" in pos.lower():
            sides["left"] = cid
        elif "右" in pos or "right" in pos.lower():
            sides["right"] = cid
    if not sides:
        chars = [str(x).strip() for x in clip.get("character_ids") or [] if str(x).strip()]
        if len(chars) >= 2:
            sides = {"left": chars[0], "right": chars[1]}
    return sides


def _is_shot_reverse_clip(clip: Mapping[str, Any]) -> bool:
    contract = _clip_contract(clip)
    hay = " ".join(
        str(value)
        for value in (
            clip.get("template"),
            clip.get("label"),
            clip.get("scene"),
            clip.get("rhythm"),
            contract.get("template_id"),
            contract.get("camera_rule"),
            contract.get("shot_pairing"),
        )
        if value
    ).lower()
    return any(token in hay for token in (
        "dialogue_shot_reverse",
        "shot_reverse",
        "正反打",
        "反打",
        "过肩",
        "ots",
        "over-the-shoulder",
        "over the shoulder",
    ))


def _shot_reverse_pattern(clip: Mapping[str, Any], idx: int, axis_text: str) -> Dict[str, Any]:
    contract = _clip_contract(clip)
    continuity = _clip_continuity(clip)
    cid = _clip_id(clip, idx)
    sides = contract.get("screen_sides") if _pattern_value_filled(contract.get("screen_sides")) else _screen_sides_from_clip(clip)
    return {
        "pattern_id": f"SR_{cid}",
        "applies_to": [cid],
        "mode": "dialogue_shot_reverse",
        "axis_line": _clean_text(contract.get("axis"), axis_text),
        "screen_sides": sides or "A 方固定画左，B 方固定画右；正式分镜需用 CHAR_id 填实。",
        "eyeline_match": _clean_text(contract.get("eyeline") or continuity.get("eyeline"), "画左角色看画右；画右角色看画左；除 POV/破第四墙外不看镜头"),
        "shot_pairing": _clean_text(contract.get("shot_pairing"), "A 面 clean single/OTS → B 面 reverse clean single/OTS → 必要插入物/反应镜"),
        "coverage_order": _clean_text(contract.get("coverage_order"), "先双人建立/空间锚 → A 面说话/动作 → B 面反应反打 → 插入物或手部缓冲 → 落在眼神/反应"),
        "camera_coverage": _clean_text(contract.get("camera_coverage"), "clean single + over-the-shoulder + insert/reaction；近景优先单人锁脸，避免多人近景同框串脸"),
        "lens_height_distance_match": _clean_text(contract.get("lens_height_distance_match"), "A/B 反打使用相近景别、镜头高度、距离和焦段；只因权力关系有计划地改变高度/距离"),
        "crossing_axis_policy": _clean_text(contract.get("crossing_axis_policy"), "默认禁止越轴；如必须越轴，先用双人建立/中线镜/运动弧线/空镜缓冲重新定向"),
        "buffer_or_reestablishing": _clean_text(contract.get("buffer_or_reestablishing"), "越轴、换侧或强情绪转折前插入双人建立、道具特写、手部动作或空镜缓冲"),
        "continuity_must": contract.get("continuity_must") or ["屏幕左右关系不交换", "视线互补", "主光方向和背景深度不跳", "脸型/发型/服装身份不漂"],
        "negative": contract.get("negative") or ["不要跳轴", "不要交换左右站位", "不要无理由看镜头", "不要多人近景同框串脸"],
    }


def _default_shot_reverse_pattern(axis_text: str) -> Dict[str, Any]:
    return {
        "pattern_id": "SR_DEFAULT",
        "applies_to": ["all_dialogue_or_confrontation_beats"],
        "mode": "none_until_storyboard_uses_dialogue_shot_reverse",
        "axis_line": axis_text,
        "screen_sides": "正式正反打出现时，先把 A/B 角色固定为画左/画右并写 CHAR_id。",
        "eyeline_match": "画左角色看画右；画右角色看画左；除 POV/破第四墙外不看镜头。",
        "shot_pairing": "双人建立或空间锚 → A 面 clean single/OTS → B 面 reverse clean single/OTS → 插入物/反应缓冲。",
        "coverage_order": "先建立空间，再交替说话/反应；不在未重建空间时交换左右关系。",
        "camera_coverage": "clean singles / OTS / insert / reaction；多人近景优先拆正反打或分层合成。",
        "lens_height_distance_match": "A/B 反打保持相近镜头高度、距离、景别和焦段；变化必须服务权力关系。",
        "crossing_axis_policy": "默认禁止越轴；越轴必须有双人建立、中线镜、运动弧线或空镜缓冲。",
        "buffer_or_reestablishing": "用双人建立、道具特写、手部动作、眼神 cutaway 或空镜重新定向。",
        "continuity_must": ["屏幕左右关系不交换", "视线互补", "主光方向不跳", "背景深度关系不跳"],
        "negative": ["不要跳轴", "不要交换左右站位", "不要无理由看镜头", "不要把反打拍成随机角度"],
    }


def _clip_depth(clip: Mapping[str, Any]) -> str:
    slots = clip.get("character_slots") if isinstance(clip.get("character_slots"), list) else []
    rows = []
    for slot in slots:
        if isinstance(slot, Mapping):
            cid = str(slot.get("character_id") or "").strip()
            pos = str(slot.get("screen_position") or slot.get("slot") or "").strip()
            if cid or pos:
                rows.append(f"{cid}: {pos}".strip(": "))
    return "；".join(rows) or str((clip.get("template_contract") or {}).get("blocking") if isinstance(clip.get("template_contract"), Mapping) else "") or "按 storyboard blocking 保持前中后景关系"


def _clip_entry_exit(clip: Mapping[str, Any]) -> str:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    if cont.get("entry_exit"):
        return str(cont["entry_exit"])
    schedule = clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else {}
    required = "、".join(str(x) for x in schedule.get("required_presence") or [])
    offscreen = "、".join(str(x) for x in schedule.get("offscreen_presence") or [])
    return f"画内保持：{required or _clip_chars(clip)}；画外保留：{offscreen or '按 storyboard'}"


def _beat_sheet(root: Path, ep: str, lines: List[str]) -> Dict[str, Any]:
    clips = _storyboard_clips(root, ep)
    if clips:
        beats = []
        for clip in clips:
            cont = _clip_continuity(clip)
            start_state = _clean_text(cont.get("start_state"), "上一镜状态延续")
            end_state = _clean_text(cont.get("end_state"), "本镜信息落定")
            beats.append({
                "beat_id": str(clip.get("id") or f"Clip_{len(beats) + 1:02d}"),
                "source_voiceover_hint": _clip_line(clip),
                "dramatic_function": _clip_story_function(clip),
                "audience_question": _clip_audience_effect(clip),
                "emotional_value_shift": {"from": start_state, "to": end_state},
                "director_intent": f"把“{_clip_story_function(clip)}”落实为可见调度，先让观众看懂再加节奏。",
                "must_keep_reaction": f"保留{_clip_chars(clip)}的关键反应；{_clip_audience_effect(clip)}。",
            })
        return {
            "kind": "n2d_director_beat_sheet",
            "version": VERSION,
            "episode": ep,
            "status": "confirmed",
            "generated_at": now_iso(),
            "inputs": {
                "voiceover": f"脚本/{ep}/voiceover.txt",
                "storyboard": f"脚本/{ep}/storyboard.json",
            },
            "beats": beats,
        }
    beats = []
    for idx, beat_id in enumerate(_beat_ids(lines), start=1):
        beats.append({
            "beat_id": beat_id,
            "source_voiceover_hint": lines[idx - 1] if idx - 1 < len(lines) else "",
            "dramatic_function": "待补：铺垫 / 冲突 / 反转 / 兑现 / 悬念",
            "audience_question": "待补：观众此刻想知道什么",
            "emotional_value_shift": {"from": "待补", "to": "待补"},
            "director_intent": "待补：这一拍为什么必须被看见，而不是旁白带过",
            "must_keep_reaction": "待补：必须补谁的反应镜/沉默半拍",
        })
    return {
        "kind": "n2d_director_beat_sheet",
        "version": VERSION,
        "episode": ep,
        "status": "draft",
        "generated_at": now_iso(),
        "inputs": {
            "voiceover": f"脚本/{ep}/voiceover.txt",
            "development_pack": "开发包/",
        },
        "beats": beats,
    }


def _axis_blocking_map(root: Path, ep: str, beat_ids: Iterable[str]) -> Dict[str, Any]:
    clips = _storyboard_clips(root, ep)
    vc = _visual_contract(root, ep)
    axis = vc.get("场景轴线视线") if isinstance(vc.get("场景轴线视线"), Mapping) else {}
    axis_text = "；".join(f"{k}: {v}" for k, v in axis.items()) if axis else "按 storyboard 场景轴线和视线关系执行，反打不越轴"
    locations = []
    for clip in clips:
        loc = _clip_location(clip)
        if loc and loc not in locations:
            locations.append(loc)
    primary_location = "、".join(locations[:4]) or "LOC_01"
    beat_ids = list(beat_ids)
    clip_by_beat = clips[: len(beat_ids)]
    shot_reverse_patterns = [
        _shot_reverse_pattern(clip, idx, axis_text)
        for idx, clip in enumerate(clips, start=1)
        if _is_shot_reverse_clip(clip)
    ] or [_default_shot_reverse_pattern(axis_text)]
    return {
        "kind": "n2d_axis_blocking_map",
        "version": VERSION,
        "episode": ep,
        "status": "confirmed" if clips else "draft",
        "generated_at": now_iso(),
        "scene_axis_rules": [
            {
                "scene_id": "Scene_01",
                "location": primary_location,
                "main_axis": axis_text,
                "screen_direction": axis_text,
                "default_eyelines": axis_text,
                "blocking_floorplan": str(vc.get("空间锚点") or vc.get("场景空间") or "按 storyboard 连续性锚点：主角、对手、道具、出口方向保持稳定。"),
            }
        ],
        "beat_blocking": [
            {
                "beat_id": beat_id,
                "characters": _clip_chars(clip_by_beat[idx]) if idx < len(clip_by_beat) else "按本 beat voiceover 对应角色",
                "z_depth": _clip_depth(clip_by_beat[idx]) if idx < len(clip_by_beat) else "按前后景纵深表达权力关系",
                "entry_exit": _clip_entry_exit(clip_by_beat[idx]) if idx < len(clip_by_beat) else "按上一 beat 连续性接续",
                "power_relation": str((clip_by_beat[idx].get("template_contract") or {}).get("blocking") if idx < len(clip_by_beat) and isinstance(clip_by_beat[idx].get("template_contract"), Mapping) else "") or "按主角/对手压迫关系调度",
                "axis_exception": "",
            }
            for idx, beat_id in enumerate(beat_ids)
        ],
        "shot_reverse_patterns": shot_reverse_patterns,
    }


def _shot_progression_plan(root: Path, ep: str, beat_ids: Iterable[str]) -> Dict[str, Any]:
    clips = _storyboard_clips(root, ep)
    if clips:
        progressions = []
        for clip in clips:
            shot_size = _clip_shot_size(clip)
            progressions.append({
                "beat_id": str(clip.get("id") or f"Clip_{len(progressions) + 1:02d}"),
                "start_shot_size": shot_size.split("→")[0].strip() if "→" in shot_size else shot_size,
                "peak_shot_size": shot_size,
                "release_shot_size": _clean_text(_clip_continuity(clip).get("transition"), "cut"),
                "camera_move": _clip_camera_rule(clip),
                "camera_motivation": _clip_story_function(clip),
                "must_have_insert_or_reaction": f"{_clip_audience_effect(clip)}；保留{_clip_chars(clip)}反应或道具/VFX落点。",
            })
        return {
            "kind": "n2d_shot_progression_plan",
            "version": VERSION,
            "episode": ep,
            "status": "confirmed",
            "generated_at": now_iso(),
            "rules": {
                "establishing": "每个场面先交代角色、压迫源和关键道具/VFX，竖屏里脸部仍可辨。",
                "scale_ladder": "按 storyboard 的 shot_size 从信息交代推进到反应/动作峰值，避免连续同景别失去节奏。",
                "peak_closeup": "系统到账、赌刀、斩妖、官道来人等爆点必须有近景或明确反应镜签收。",
                "movement_motivation": "所有推拉跟移都绑定求生压力、系统信息或动作力线，不做无动机炫技。",
            },
            "progressions": progressions,
        }
    return {
        "kind": "n2d_shot_progression_plan",
        "version": VERSION,
        "episode": ep,
        "status": "draft",
        "generated_at": now_iso(),
        "rules": {
            "establishing": "待补：每场至少一个定场/关系镜，竖屏里脸仍可读",
            "scale_ladder": "待补：远/中/近有进有出，避免连续三个同景别",
            "peak_closeup": "待补：爽点/反转/觉醒落 CU/ECU 或有明确反应镜",
            "movement_motivation": "待补：每个推/拉/跟/摇/升降必须有情绪或信息动机",
        },
        "progressions": [
            {
                "beat_id": beat_id,
                "start_shot_size": "待补：ELS/LS/MS/MCU/CU/ECU",
                "peak_shot_size": "待补：本 beat 情绪峰值景别",
                "release_shot_size": "待补：余韵/转场景别",
                "camera_move": "待补：固定/推/拉/移/跟/摇/升降/短促冲击",
                "camera_motivation": "待补：为什么动；不动也要说明压迫/表演优先",
                "must_have_insert_or_reaction": "待补：道具特写/反应镜/空镜",
            }
            for beat_id in beat_ids
        ],
    }


def _transition_map(root: Path, ep: str, beat_ids: List[str]) -> Dict[str, Any]:
    clips = _storyboard_clips(root, ep)
    if len(clips) >= 2:
        seams = []
        for idx, (prev, nxt) in enumerate(zip(clips, clips[1:]), start=1):
            prev_cont = _clip_continuity(prev)
            next_cont = _clip_continuity(nxt)
            seams.append({
                "seam_id": f"Seam_{idx:02d}",
                "from_beat": str(prev.get("id") or f"Clip_{idx:02d}"),
                "to_beat": str(nxt.get("id") or f"Clip_{idx + 1:02d}"),
                "out_point": _clean_text(prev_cont.get("end_state"), "上一镜动作/信息完成落点"),
                "in_point": _clean_text(next_cont.get("start_state"), "下一镜接住上一镜状态"),
                "transition_type": _clean_text(next_cont.get("transition") or prev_cont.get("transition"), "cut"),
                "need_endframe": bool(prev_cont.get("need_endframe", True)),
                "sound_bridge": _clip_post_cues(prev),
                "continuity_guard": _clean_text(
                    next_cont.get("eyeline") or prev_cont.get("eyeline"),
                    "轴线、视线、道具、服装和战损状态保持连续",
                ),
            })
        return {
            "kind": "n2d_transition_map",
            "version": VERSION,
            "episode": ep,
            "status": "confirmed",
            "generated_at": now_iso(),
            "seams": seams,
        }
    seams = []
    for idx, beat_id in enumerate(beat_ids[:-1], start=1):
        seams.append({
            "seam_id": f"Seam_{idx:02d}",
            "from_beat": beat_id,
            "to_beat": beat_ids[idx],
            "out_point": "待补：上一拍最后一帧/动作/声音",
            "in_point": "待补：下一拍第一帧；应与 out_point 形成接力",
            "transition_type": "待补：match_cut / eyeline / action_cut / j_cut / l_cut / empty_buffer / hard_cut",
            "need_endframe": True,
            "sound_bridge": "待补：下句先入/上句延续/环境声桥/BGM hit",
            "continuity_guard": "待补：轴线、视线、道具/服装/状态不能断",
        })
    return {
        "kind": "n2d_transition_map",
        "version": VERSION,
        "episode": ep,
        "status": "draft",
        "generated_at": now_iso(),
        "seams": seams or [{
            "seam_id": "Seam_01",
            "from_beat": "Beat_01",
            "to_beat": "Beat_02",
            "out_point": "待补",
            "in_point": "待补",
            "transition_type": "待补",
            "need_endframe": True,
            "sound_bridge": "待补",
            "continuity_guard": "待补",
        }],
    }


def _vertical_composition_plan(root: Path, ep: str, beat_ids: Iterable[str]) -> Dict[str, Any]:
    clips = _storyboard_clips(root, ep)
    if clips:
        return {
            "kind": "n2d_vertical_composition_plan",
            "version": VERSION,
            "episode": ep,
            "status": "confirmed",
            "generated_at": now_iso(),
            "composition_rules": {
                "safe_zone": "字幕、百妖谱面板和道行计数统一走后期 overlay，主体脸部避开底部字幕区。",
                "face_readability": "核心角色在竖屏中至少保留可辨侧脸/三分之二侧脸尺度，动作全景后必须补反应或状态落点。",
                "z_axis_depth": "优先用前景尸骸/刀、主角中景、虎妖或官道火把后景建立纵深，避免横向并排挤脸。",
                "overlay_policy": "系统面板、数值、屏幕文字全部 compose overlay；视频模型画面只留干净负空间。",
            },
            "beat_composition": [
                {
                    "beat_id": str(clip.get("id") or f"Clip_{idx:02d}"),
                    "primary_subject_zone": _clip_subject_zone(clip),
                    "foreground_midground_background": _clip_depth(clip),
                    "subtitle_clearance": "底部字幕区保持低细节；系统/数值 overlay 放在主体视线附近的负空间。",
                    "vertical_motion": f"{_clip_shot_size(clip)}；{_clip_camera_rule(clip)}",
                }
                for idx, clip in enumerate(clips, start=1)
            ],
        }
    return {
        "kind": "n2d_vertical_composition_plan",
        "version": VERSION,
        "episode": ep,
        "status": "draft",
        "generated_at": now_iso(),
        "composition_rules": {
            "safe_zone": "待补：字幕/系统面板/花字/进度条安全区",
            "face_readability": "待补：竖屏中核心脸部最低可读尺度",
            "z_axis_depth": "待补：优先用前后景纵深而非横向并排挤脸",
            "overlay_policy": "待补：系统面板/屏幕文字走 compose overlay，不让视频模型烤字",
        },
        "beat_composition": [
            {
                "beat_id": beat_id,
                "primary_subject_zone": "待补：上中/中部/下中/偏左/偏右",
                "foreground_midground_background": "待补：三层关系与遮挡",
                "subtitle_clearance": "待补：字幕区是否空出",
                "vertical_motion": "待补：抬头/俯身/升降/落下等竖屏运动",
            }
            for beat_id in beat_ids
        ],
    }


def _edit_rhythm_map(root: Path, ep: str, beat_ids: Iterable[str]) -> Dict[str, Any]:
    story = _storyboard(root, ep)
    clips = _storyboard_clips(root, ep)
    if clips:
        return {
            "kind": "n2d_edit_rhythm_map",
            "version": VERSION,
            "episode": ep,
            "status": "confirmed",
            "generated_at": now_iso(),
            "timeline": {
                "first_3s_hook": _clean_text(story.get("first_3s_visual_hook"), "首镜用尸场、插胸长刀和百妖谱金光建立冷开爆点。"),
                "first_6s_proposition": _clean_text(story.get("core_attraction"), "杀裴后的系统奖励、赌命斩妖和官道新危机串成升级爽点。"),
                "hook_cadence": "每 10-20 秒交出一次信息增量：到账、嘲讽、赌刀、斩妖、收录、官道火把。",
                "cliffhanger": _clean_text(story.get("retention_promise_ledger") or story.get("audience_question_ledger"), "结尾让官道来人接住下一集冷开场。"),
            },
            "beats": [
                {
                    "beat_id": str(clip.get("id") or f"Clip_{idx:02d}"),
                    "tempo": _clean_text(clip.get("rhythm"), "按 storyboard 节奏推进"),
                    "estimated_seconds": f"{float(clip.get('duration') or 0):.2f}s",
                    "reaction_cut": _clip_audience_effect(clip),
                    "sound_or_bgm_cue": _clip_post_cues(clip),
                }
                for idx, clip in enumerate(clips, start=1)
            ],
        }
    return {
        "kind": "n2d_edit_rhythm_map",
        "version": VERSION,
        "episode": ep,
        "status": "draft",
        "generated_at": now_iso(),
        "timeline": {
            "first_3s_hook": "待补：0-3 秒静音可读的视觉钩",
            "first_6s_proposition": "待补：前 6 秒观众知道这集看什么",
            "hook_cadence": "待补：中段每 10-20 秒的信息增量/反转/危机",
            "cliffhanger": "待补：集尾硬断与下一集冷开场接力",
        },
        "beats": [
            {
                "beat_id": beat_id,
                "tempo": "待补：铺垫长镜 / 加速碎切 / 爽点硬切 / 留白定格",
                "estimated_seconds": "待补：本 beat 预估秒数",
                "reaction_cut": "待补：谁的反应镜负责让信息落地",
                "sound_or_bgm_cue": "待补：J/L cut、重音、静音、环境声桥",
            }
            for beat_id in beat_ids
        ],
    }


def _write_overview(root: Path, ep: str, report: Mapping[str, Any] | None = None) -> str:
    out = root / "生产数据" / f"director_blocking_pack_{ep}.md"
    files = [f"脚本/{ep}/{name}" for name in REQUIRED_FILES]
    lines = [
        f"# P-2 导演排戏包 — {ep}",
        "",
        "本包位于 Stage 1 台词之后、Stage 2 分镜之前，用来先锁导演排戏、镜头衔接和竖屏调度。",
        "",
        "## Required Files",
        "",
    ]
    lines.extend(f"- `{rel}`" for rel in files)
    if report:
        lines.extend([
            "",
            "## Check",
            "",
            f"- 状态：{report.get('status')}",
            f"- 通过：{(report.get('summary') or {}).get('pass')}/{(report.get('summary') or {}).get('required')}",
            "",
            "| 文件 | 状态 | 问题 |",
            "|---|---|---|",
        ])
        for row in report.get("files") or []:
            issues = "；".join(row.get("issues") or []) or "-"
            lines.append(f"| `{row.get('rel')}` | {row.get('status')} | {issues} |")
    write_atomic(out, "\n".join(lines).rstrip() + "\n")
    return str(out)


def scaffold(root: Path, ep: str, *, force: bool = False) -> Dict[str, Any]:
    ep = episode_label(ep)
    ep_dir = _episode_dir(root, ep)
    lines = _voiceover_lines(root, ep)
    storyboard_clips = _storyboard_clips(root, ep)
    beat_ids = _planning_ids(root, ep, lines)
    status = "confirmed" if storyboard_clips else "draft"
    created: List[str] = []
    templates: Tuple[Tuple[str, Dict[str, Any]], ...] = (
        ("director_beat_sheet.json", _beat_sheet(root, ep, lines)),
        ("axis_blocking_map.json", _axis_blocking_map(root, ep, beat_ids)),
        ("shot_progression_plan.json", _shot_progression_plan(root, ep, beat_ids)),
        ("transition_map.json", _transition_map(root, ep, beat_ids)),
        ("vertical_composition_plan.json", _vertical_composition_plan(root, ep, beat_ids)),
        ("edit_rhythm_map.json", _edit_rhythm_map(root, ep, beat_ids)),
    )
    for name, payload in templates:
        if write_json_if_absent(ep_dir / name, payload, force=force):
            created.append(f"脚本/{ep}/{name}")
    manifest = {
        "kind": KIND,
        "version": VERSION,
        "episode": ep,
        "status": status,
        "generated_at": now_iso(),
        "root": str(root),
        "required_files": [f"脚本/{ep}/{name}" for name in REQUIRED_FILES],
        "gate": "run.py script_stage2 prework requires all P-2 director files to be confirmed.",
    }
    write_json_atomic(ep_dir / "director_blocking_pack.json", manifest)
    overview = _write_overview(root, ep)
    return {
        "kind": KIND,
        "root": str(root),
        "episode": ep,
        "episode_dir": str(ep_dir),
        "created": created,
        "manifest": f"脚本/{ep}/director_blocking_pack.json",
        "overview_path": overview,
    }


def _json_status(path: Path) -> Tuple[str, List[str]]:
    data = load_json(path)
    issues: List[str] = []
    if not isinstance(data, dict):
        return "block", ["JSON 无法解析或不是 object"]
    if str(data.get("status") or "").strip().lower() != "confirmed":
        issues.append("status 不是 confirmed")
    blob = json.dumps(data, ensure_ascii=False)
    if PLACEHOLDER_RE.search(blob):
        issues.append("仍含待补/TODO 占位")
    return ("pass" if not issues else "block"), issues


def _storyboard_shot_reverse_clip_ids(root: Path, ep: str) -> List[str]:
    ids: List[str] = []
    for idx, clip in enumerate(_storyboard_clips(root, ep), start=1):
        if _is_shot_reverse_clip(clip):
            ids.append(_clip_id(clip, idx))
    return ids


def _pattern_value_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and not PLACEHOLDER_RE.search(value)
    if isinstance(value, list):
        return any(_pattern_value_filled(item) for item in value)
    if isinstance(value, Mapping):
        return any(_pattern_value_filled(item) for item in value.values())
    return True


def _axis_blocking_contract_issues(data: Mapping[str, Any], required_clip_ids: Iterable[str]) -> List[str]:
    issues: List[str] = []
    patterns = data.get("shot_reverse_patterns")
    if not isinstance(patterns, list) or not patterns:
        return ["缺 shot_reverse_patterns：正反打必须在 P-2 锁轴线、左右侧、互补视线和越轴策略"]
    applied: set[str] = set()
    for idx, pattern in enumerate(patterns, start=1):
        if not isinstance(pattern, Mapping):
            issues.append(f"shot_reverse_patterns[{idx}] 不是 object")
            continue
        mode = str(pattern.get("mode") or "").strip()
        applies = [str(item).strip() for item in _as_iter(pattern.get("applies_to")) if str(item).strip()]
        applied.update(applies)
        if mode == "none_until_storyboard_uses_dialogue_shot_reverse":
            continue
        for key in SHOT_REVERSE_PATTERN_FIELDS:
            if not _pattern_value_filled(pattern.get(key)):
                issues.append(f"{pattern.get('pattern_id') or f'shot_reverse_patterns[{idx}]'} 缺正反打字段：{key}")
    for clip_id in required_clip_ids:
        if clip_id not in applied:
            issues.append(f"{clip_id} 是 dialogue_shot_reverse/反打镜，但 axis_blocking_map 未登记对应 shot_reverse_patterns")
    return issues


def _as_iter(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def check(root: Path, ep: str, *, write_missing: bool = False) -> Dict[str, Any]:
    ep = episode_label(ep)
    if write_missing:
        scaffold(root, ep)
    ep_dir = _episode_dir(root, ep)
    rows: List[Dict[str, Any]] = []
    for name in REQUIRED_FILES:
        path = ep_dir / name
        rel = f"脚本/{ep}/{name}"
        if not path.exists():
            rows.append({"rel": rel, "status": "missing", "issues": ["文件缺失"]})
            continue
        status, issues = _json_status(path)
        if name == "axis_blocking_map.json" and status == "pass":
            data = load_json(path)
            if isinstance(data, Mapping):
                issues.extend(_axis_blocking_contract_issues(data, _storyboard_shot_reverse_clip_ids(root, ep)))
                status = "pass" if not issues else "block"
        rows.append({"rel": rel, "status": status, "issues": issues})
    blockers = [row for row in rows if row["status"] != "pass"]
    payload = {
        "kind": CHECK_KIND,
        "version": VERSION,
        "generated_at": now_iso(),
        "root": str(root),
        "episode": ep,
        "status": "pass" if not blockers else "block",
        "summary": {
            "required": len(REQUIRED_FILES),
            "pass": len(rows) - len(blockers),
            "block": len(blockers),
        },
        "files": rows,
        "scaffold_command": f"python3 skills/n2d-script/scripts/director_blocking_pack.py {root} {ep} scaffold --write",
        "next_when_blocked": (
            "补齐 P-2 导演排戏包六件套，删除待补/TODO 占位，并把每个文件 status 改为 confirmed；"
            "之后重跑 check，再进入阶段2分镜设计。"
        ),
    }
    out = root / "生产数据" / f"director_blocking_pack_check_{ep}.json"
    write_json_atomic(out, payload)
    payload["check_path"] = str(out)
    payload["overview_path"] = _write_overview(root, ep, payload)
    return payload


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        f"# P-2 导演排戏包检查 — {report.get('episode')}",
        "",
        f"- 状态：{report.get('status')}",
        f"- 通过：{(report.get('summary') or {}).get('pass')}/{(report.get('summary') or {}).get('required')}",
        "",
        "| 文件 | 状态 | 问题 |",
        "|---|---|---|",
    ]
    for row in report.get("files") or []:
        issues = "；".join(row.get("issues") or []) or "-"
        lines.append(f"| `{row.get('rel')}` | {row.get('status')} | {issues} |")
    lines += ["", str(report.get("next_when_blocked") or "")]
    return "\n".join(lines).rstrip() + "\n"


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    sub = ap.add_subparsers(dest="command", required=True)
    p_scaffold = sub.add_parser("scaffold")
    p_scaffold.add_argument("--write", action="store_true", help="兼容显式写入语义；scaffold 默认即写入")
    p_scaffold.add_argument("--force", action="store_true", help="覆盖已有模板（谨慎）")
    p_check = sub.add_parser("check")
    p_check.add_argument("--json", action="store_true")
    p_check.add_argument("--markdown", action="store_true")
    p_check.add_argument("--write-missing", action="store_true", help="缺文件时先补 scaffold，再返回 block")
    ns = ap.parse_args(argv)

    root = Path(ns.root)
    ep = episode_label(ns.episode)
    if ns.command == "scaffold":
        payload = scaffold(root, ep, force=ns.force)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    report = check(root, ep, write_missing=ns.write_missing)
    if ns.markdown:
        md = render_markdown(report)
        path = root / "生产数据" / f"director_blocking_pack_check_{ep}.md"
        write_atomic(path, md)
        print(md)
    elif ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"P-2 导演排戏包检查：{report['status']} ({report['summary']['pass']}/{report['summary']['required']})")
        if report["status"] != "pass":
            print(report["next_when_blocked"])
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
