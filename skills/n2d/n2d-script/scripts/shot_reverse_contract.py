#!/usr/bin/env python3
"""Build and audit shot/reverse-shot contracts for n2d episodes.

The contract is a deterministic bridge between the director blocking layer and
image/video prompts.  It turns `dialogue_shot_reverse` / confrontation clips
into explicit A/B screen positions, eyelines, coverage, axis policy and 9:16
vertical staging rules, then emits hard audit findings for continuity defects.
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

KIND = "n2d_shot_reverse_contract"
CHECK_KIND = "n2d_shot_reverse_contract_check"
VERSION = 1

SHOT_REVERSE_RE = re.compile(
    r"dialogue_shot_reverse|shot_reverse|正反打|反打|过肩|\bOTS\b|over[- ]the[- ]shoulder",
    re.I,
)
CONFRONTATION_TEMPLATES = {"public_confrontation", "reveal_reaction_chain", "relationship_turn", "fight_exchange"}
AXIAL_PRESSURE_RE = re.compile(r"对峙|对压|沿主轴|轴线|高位|低位|前景|后景|深处|逼近|跪|仰视|俯视", re.I)
CAMERA_GAZE_RE = re.compile(r"看镜头|直视镜头|looking at (?:the )?(?:viewer|camera)|direct eye contact", re.I)
CAMERA_GAZE_NEG_RE = re.compile(
    r"不看镜头|不得看镜头|不要看镜头|禁止看镜头|"
    r"(?:不得|不要|禁止)(?:让?[^，。；]{0,12})?(?:看|直视)镜头|"
    r"非\s*POV\s*镜不看镜头|no direct camera gaze|do not (?:look at|face) (?:the )?(?:viewer|camera)",
    re.I,
)
POV_ALLOW_RE = re.compile(r"\bPOV\b|主观镜头|破第四墙|看镜头是剧情|fourth wall", re.I)
OTS_RE = re.compile(r"\bOTS\b|过肩|over[- ]the[- ]shoulder", re.I)
FOREGROUND_SHOULDER_RE = re.compile(r"前景.*(?:肩|背头|侧背)|(?:肩|背头|侧背).*前景|foreground.*shoulder|shoulder.*foreground", re.I)
CROSS_AXIS_RE = re.compile(r"越轴|反轴|cross(?:ing)? axis|180", re.I)
CROSS_AXIS_ALLOWED_RE = re.compile(r"允许越轴|可越轴|cross(?:ing)? axis allowed", re.I)
CROSS_AXIS_FORBID_RE = re.compile(r"禁止越轴|不得越轴|不越轴|no crossing|do not cross", re.I)
BUFFER_RE = re.compile(r"缓冲|建立镜|重建空间|重新定向|空镜|插入|cutaway|insert|reestablish|re-establish|中线|运动弧线", re.I)
CLOSEUP_RE = re.compile(r"\b(?:CU|ECU|MCU)\b|近景|特写|close[- ]?up|反打|过肩", re.I)
GROUP_RE = re.compile(r"^GROUP_")
ID_RE = re.compile(r"\b(?:CHAR|GROUP)_[^/\s,，;；)）]+")

CONTRACT_REQUIRED_FIELDS = (
    "axis_id",
    "axis_line",
    "participants",
    "screen_sides",
    "eyeline_match",
    "shot_pairing",
    "coverage_order",
    "camera_coverage",
    "lens_height_distance_match",
    "crossing_axis_policy",
    "buffer_or_reestablishing",
    "vertical_9x16",
    "prompt_requirements",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def episode_label(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    match = re.search(r"\d+", text)
    return f"第{match.group(0)}集" if match else text


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    write_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def one_line(value: Any, default: str = "") -> str:
    if isinstance(value, Mapping):
        parts = [f"{k}={one_line(v)}" for k, v in value.items() if one_line(v)]
        text = "；".join(parts)
    elif isinstance(value, list):
        text = "；".join(one_line(v) for v in value if one_line(v))
    else:
        text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text or default


def compact_id(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_\u4e00-\u9fff]+", "_", str(value or "").strip())
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "scene"


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or f"Clip_{idx:02d}").strip()


def episode_dir(root: Path, ep: str) -> Path:
    return root / "脚本" / ep


def storyboard(root: Path, ep: str) -> Mapping[str, Any]:
    data = load_json(episode_dir(root, ep) / "storyboard.json")
    return data if isinstance(data, Mapping) else {}


def clips_from_storyboard(sb: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    return [c for c in sb.get("clips") or [] if isinstance(c, Mapping)]


def clip_blob(clip: Mapping[str, Any]) -> str:
    return json.dumps(clip, ensure_ascii=False, sort_keys=True)


def is_candidate(clip: Mapping[str, Any]) -> bool:
    template = str(clip.get("template") or "").strip()
    contract = clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}
    template_id = str(contract.get("template_id") or "").strip()
    if template == "dialogue_shot_reverse" or template_id == "dialogue_shot_reverse":
        return True
    blob = " ".join([template, template_id, clip_blob(clip)])
    if template in CONFRONTATION_TEMPLATES and (SHOT_REVERSE_RE.search(blob) or AXIAL_PRESSURE_RE.search(blob)):
        return True
    if template == "ensemble_blocking" and re.search(r"跪求|求援|众人齐跪|群体压力|对峙|对压", blob):
        return True
    return False


def source_paths(root: Path, ep: str) -> List[Tuple[str, Path]]:
    skill_root = Path(__file__).resolve().parent.parent
    return [
        ("storyboard", episode_dir(root, ep) / "storyboard.json"),
        ("axis_blocking_map", episode_dir(root, ep) / "axis_blocking_map.json"),
        ("continuity_bible", episode_dir(root, ep) / "continuity_bible.json"),
        ("cinematic_coverage_grammar", skill_root / "references" / "cinematic_coverage_grammar.json"),
    ]


def axis_patterns(root: Path, ep: str) -> Dict[str, Mapping[str, Any]]:
    data = load_json(episode_dir(root, ep) / "axis_blocking_map.json")
    if not isinstance(data, Mapping):
        return {}
    out: Dict[str, Mapping[str, Any]] = {}
    for row in data.get("shot_reverse_patterns") or []:
        if not isinstance(row, Mapping):
            continue
        for cid in row.get("applies_to") or []:
            out[str(cid)] = row
    return out


def continuity_shot_reverse(root: Path, ep: str) -> Dict[str, Mapping[str, Any]]:
    data = load_json(episode_dir(root, ep) / "continuity_bible.json")
    if not isinstance(data, Mapping):
        return {}
    out: Dict[str, Mapping[str, Any]] = {}
    for row in data.get("clips") or []:
        if not isinstance(row, Mapping):
            continue
        cid = str(row.get("clip_id") or row.get("id") or "").strip()
        cont = row.get("shot_reverse_continuity")
        if cid and isinstance(cont, Mapping):
            out[cid] = cont
    return out


def ids_from_value(value: Any) -> List[str]:
    return [m.group(0) for m in ID_RE.finditer(one_line(value))]


def named_ids(clip: Mapping[str, Any]) -> List[str]:
    ids = [str(x) for x in clip.get("character_ids") or [] if str(x).strip()]
    primary = [x for x in ids if not GROUP_RE.match(x)]
    return primary or ids


def slot_rows(clip: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    rows = clip.get("character_slots")
    if isinstance(rows, list):
        return [r for r in rows if isinstance(r, Mapping)]
    contract = clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}
    rows = contract.get("character_slots")
    if isinstance(rows, list):
        return [r for r in rows if isinstance(r, Mapping)]
    return []


def slot_character(row: Mapping[str, Any]) -> str:
    return str(row.get("character_id") or row.get("entity") or "").strip()


def slot_position(row: Mapping[str, Any]) -> str:
    return str(row.get("screen_position") or row.get("position") or row.get("slot") or "").strip()


def position_kind(text: str) -> str:
    t = str(text or "")
    if "左" in t or re.search(r"\bleft\b", t, re.I):
        return "left"
    if "右" in t or re.search(r"\bright\b", t, re.I):
        return "right"
    if any(x in t for x in ("上", "高位", "前景", "upper", "foreground", "high")):
        return "upper_foreground"
    if any(x in t for x in ("下", "低位", "后景", "background", "low", "lower")):
        return "lower_background"
    return ""


def side_map_from_screen_sides(screen_sides: Any) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not isinstance(screen_sides, Mapping):
        return out
    for key, value in screen_sides.items():
        if key == "locked_rule":
            out["locked_rule"] = one_line(value)
            continue
        ids = ids_from_value(value)
        char = ids[0] if ids else one_line(value)
        kind = position_kind(f"{key} {value}")
        if kind == "left" and "left" not in out:
            out["left"] = char
            out["left_position"] = one_line(value)
        elif kind == "right" and "right" not in out:
            out["right"] = char
            out["right_position"] = one_line(value)
        elif kind == "upper_foreground" and "upper_foreground" not in out:
            out["upper_foreground"] = char
            out["upper_foreground_position"] = one_line(value)
        elif kind == "lower_background" and "lower_background" not in out:
            out["lower_background"] = char
            out["lower_background_position"] = one_line(value)
    return out


def side_map_from_slots(rows: Sequence[Mapping[str, Any]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for row in rows:
        cid = slot_character(row)
        if not cid:
            continue
        pos = slot_position(row)
        kind = position_kind(f"{row.get('slot') or ''} {pos}")
        if kind and kind not in out:
            out[kind] = cid
            out[f"{kind}_position"] = pos
    return out


def resolve_ab(clip: Mapping[str, Any], source: Mapping[str, Any]) -> Tuple[str, str, Dict[str, str], str]:
    screen_sides = source.get("screen_sides") or (clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}).get("screen_sides")
    sides = side_map_from_screen_sides(screen_sides)
    if not sides:
        sides = side_map_from_slots(slot_rows(clip))
    ids = named_ids(clip)
    left = sides.get("left")
    right = sides.get("right")
    if left and right and left != right:
        return left, right, sides, "left_right"
    upper = sides.get("upper_foreground")
    lower = sides.get("lower_background")
    if upper and lower and upper != lower:
        return upper, lower, sides, "vertical_depth_9x16"
    blob = clip_blob(clip)
    a = ids[0] if ids else ""
    if "CHAR_05" in ids and re.search(r"青面郎君|狼妖|血食|镇魔司|杀了她|狼爪", blob):
        b = "CHAR_05"
    else:
        b = ids[1] if len(ids) > 1 else ""
    if a and b and AXIAL_PRESSURE_RE.search(blob):
        sides = {
            "upper_foreground": a,
            "lower_background": b,
            "upper_foreground_position": "画面前景/高位/主动压场，按 storyboard 纵深站位锁定",
            "lower_background_position": "画面后景/低位/受压或压出，按 storyboard 纵深站位锁定",
            "locked_rule": "9:16 纵深对压；A/B 高低位、前后景和视线方向不得在反打中互换。",
        }
        return a, b, sides, "vertical_depth_9x16"
    return a, b, sides, "inferred"


def eyeline_for_position(position: str, counterpart_position: str) -> str:
    kind = position_kind(position)
    counterpart_kind = position_kind(counterpart_position)
    if kind == "left" or counterpart_kind == "right":
        return "看画右的戏内对象，不看镜头"
    if kind == "right" or counterpart_kind == "left":
        return "看画左的戏内对象，不看镜头"
    if kind == "upper_foreground":
        return "看向画面下方/后景的戏内对象，不看镜头"
    if kind == "lower_background":
        return "看向画面上方/前景的戏内对象，不看镜头"
    return "看向对手/目标，不看镜头"


def merged_source(clip: Mapping[str, Any], axis_row: Mapping[str, Any], bible_row: Mapping[str, Any]) -> Dict[str, Any]:
    contract = clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}
    out: Dict[str, Any] = {}
    for src in (contract, bible_row, axis_row):
        for key, value in src.items():
            if value not in (None, "", [], {}):
                out[key] = value
    return out


def buffer_from_source(source: Mapping[str, Any], mode: str) -> str:
    text = one_line(source.get("buffer_or_reestablishing") or source.get("coverage_order") or source.get("camera_coverage"))
    if text:
        return text
    if mode == "vertical_depth_9x16":
        return "建立镜/前景肩部/道具插入/反应近景负责重新定向；竖屏优先用纵深和上下高低位，不直接跳反轴。"
    return "双人建立镜、道具插入、反应近景或空镜负责重新定向；不得直接跳反轴近景。"


def build_pattern(
    ep: str,
    idx: int,
    clip: Mapping[str, Any],
    axis_row: Mapping[str, Any],
    bible_row: Mapping[str, Any],
) -> Dict[str, Any]:
    cid = clip_id(clip, idx)
    source = merged_source(clip, axis_row, bible_row)
    a, b, sides, spatial_mode = resolve_ab(clip, source)
    loc = str(clip.get("location_id") or clip.get("scene") or "SCENE").strip()
    axis_id = str(source.get("axis_id") or f"AXIS_{compact_id(loc)}_{compact_id(a)}_VS_{compact_id(b)}").strip()
    axis_line = one_line(source.get("axis_line") or source.get("axis"), "按本场 180° 行动轴线；摄影机守同一侧。")
    a_pos = sides.get("left_position") if sides.get("left") == a else sides.get("upper_foreground_position") if sides.get("upper_foreground") == a else ""
    b_pos = sides.get("right_position") if sides.get("right") == b else sides.get("lower_background_position") if sides.get("lower_background") == b else ""
    if not a_pos:
        a_pos = "画左/前景/高位，按 storyboard 站位锁定" if spatial_mode != "vertical_depth_9x16" else "画面上方/前景/高位，按 storyboard 纵深站位锁定"
    if not b_pos:
        b_pos = "画右/后景/低位，按 storyboard 站位锁定" if spatial_mode != "vertical_depth_9x16" else "画面下方/后景/低位，按 storyboard 纵深站位锁定"
    a_eye = eyeline_for_position(a_pos, b_pos)
    b_eye = eyeline_for_position(b_pos, a_pos)
    eyeline_match = one_line(source.get("eyeline_match") or source.get("eyeline"), f"{a}: {a_eye}；{b}: {b_eye}。")
    coverage_order = source.get("coverage_order") or [
        "建立镜确认 A/B 空间关系和行动轴线",
        f"A 面 clean single/OTS：焦点 {a}，{b} 的前景肩部或侧背只作遮挡层",
        f"B 面 clean single/OTS：焦点 {b}，{a} 的前景肩部或侧背只作遮挡层",
        "道具/手部/反应插入作为节奏和越轴缓冲",
        "回到反应近景或重建空间镜落幅",
    ]
    camera_coverage = one_line(
        source.get("camera_coverage"),
        "establishing master + paired clean singles + true OTS with foreground shoulder + insert/cutaway + reaction shot",
    )
    lens_match = one_line(
        source.get("lens_height_distance_match"),
        "A/B 反打保持相近焦段、镜头距离、镜头高度、光位和背景深度；权力高低只用轻微机位差表达。",
    )
    crossing_policy = one_line(
        source.get("crossing_axis_policy"),
        "默认禁止越轴；如剧情必须越轴，先用建立镜/中线移动/道具插入/空镜缓冲重新定向。",
    )
    buffer = buffer_from_source(source, spatial_mode)
    screen_sides = {
        "spatial_mode": spatial_mode,
        "A": {"character_id": a, "screen_position": a_pos},
        "B": {"character_id": b, "screen_position": b_pos},
        "left": sides.get("left") or ("vertical-depth mode; left/right not primary" if spatial_mode == "vertical_depth_9x16" else a),
        "right": sides.get("right") or ("vertical-depth mode; left/right not primary" if spatial_mode == "vertical_depth_9x16" else b),
        "upper_foreground": sides.get("upper_foreground", ""),
        "lower_background": sides.get("lower_background", ""),
        "locked_rule": sides.get("locked_rule") or "A/B 屏幕关系、纵深和高低位不得在反打中互换。",
    }
    participants = {
        "A": {"character_id": a, "screen_position": a_pos, "eyeline_direction": a_eye, "focus_role": "A 面焦点"},
        "B": {"character_id": b, "screen_position": b_pos, "eyeline_direction": b_eye, "focus_role": "B 面焦点"},
    }
    shot_pairing = source.get("shot_pairing") or [
        f"A 面：{a} clean single / OTS，焦点在 {a}；{b} 的肩或侧背在前景虚化边缘。",
        f"B 面：{b} reverse clean single / OTS，焦点在 {b}；{a} 的肩或侧背在前景虚化边缘。",
        "插入镜：手部、道具、火把/门框/地面尘土或眼神反应负责缓冲和节奏。",
    ]
    coverage = {
        "establishing_master": f"先确认 axis_id={axis_id}、A/B 站位和 9:16 纵深层级。",
        "a_clean_single": f"焦点 {a}；{a_pos}；{a_eye}；非 POV 不看镜头。",
        "b_clean_single": f"焦点 {b}；{b_pos}；{b_eye}；非 POV 不看镜头。",
        "a_ots": f"焦点 {a}；{b} 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。",
        "b_ots": f"焦点 {b}；{a} 的前景肩部/侧背/背头必须在画面边缘虚化遮挡，不能变成第三张清晰脸。",
        "insert_cutaway": "手部/道具/火把/门框/地面尘土/眼神反应，用于节奏、遮挡和越轴缓冲。",
        "reaction_shot": "反应镜只拍正在承受信息的一方，主焦点明确，不挤多张清晰近脸。",
    }
    vertical_rules = {
        "aspect": "9:16",
        "avoid": "不要频繁横向多人并排，尤其不要把 2+ 清晰脸挤进近景横排。",
        "prefer": "前景肩部 + 背景脸、纵深站位、上下高低位、道具插入、反应近景和重建空间镜。",
        "face_readability": "关键表情用 clean single/OTS/MCU/CU；群体只做剪影或建立镜层级。",
    }
    prompt_requirements = [
        f"必须写 axis_id={axis_id}，并说明 {a} 与 {b} 的屏幕位置。",
        f"必须写 {a} 看向哪里、{b} 看向哪里；非 POV 镜禁止看镜头。",
        "若写 OTS/过肩，必须说明谁的肩/侧背在前景、谁是焦点。",
        "必须写镜头距离、焦段/景别、镜头高度、光位和背景深度如何匹配。",
        "必须写本镜情绪功能：压迫、求援、试探、拒绝、承诺、揭示或反应。",
        "如允许越轴，必须写建立镜/插入镜/中线移动/空镜缓冲；否则默认禁止越轴。",
        "竖屏 9:16 优先纵深和过肩，不把多人横向排队挤成小脸。",
    ]
    return {
        "clip_id": cid,
        "pattern_id": str(source.get("pattern_id") or f"SR_{compact_id(cid)}"),
        "source_template": str(clip.get("template") or source.get("template_id") or ""),
        "axis_id": axis_id,
        "axis_line": axis_line,
        "participants": participants,
        "screen_sides": screen_sides,
        "eyeline_match": eyeline_match,
        "shot_pairing": shot_pairing,
        "coverage_order": coverage_order,
        "camera_coverage": camera_coverage,
        "coverage": coverage,
        "lens_height_distance_match": lens_match,
        "crossing_axis_policy": crossing_policy,
        "allow_cross_axis": bool(CROSS_AXIS_ALLOWED_RE.search(crossing_policy)) and not bool(CROSS_AXIS_FORBID_RE.search(crossing_policy)),
        "buffer_or_reestablishing": buffer,
        "continuity_must": source.get("continuity_must") or [
            "A/B 左右或纵深关系不得互换",
            "互补视线看戏内对象，不看镜头",
            "OTS 必须有前景肩部/侧背",
            "近景必须使用同源脸锚/表情锚或保真实现",
        ],
        "vertical_9x16": vertical_rules,
        "prompt_requirements": prompt_requirements,
    }


def has_positive_camera_gaze(text: str) -> bool:
    if not CAMERA_GAZE_RE.search(text):
        return False
    stripped = CAMERA_GAZE_NEG_RE.sub("", text)
    return bool(CAMERA_GAZE_RE.search(stripped)) and not bool(POV_ALLOW_RE.search(text))


def audit_pattern(pattern: Mapping[str, Any], clip: Mapping[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    def add(severity: str, code: str, message: str, suggestion: str = "") -> None:
        issues.append({
            "severity": severity,
            "code": code,
            "message": message,
            "suggestion": suggestion,
        })

    participants = pattern.get("participants") if isinstance(pattern.get("participants"), Mapping) else {}
    a = participants.get("A", {}).get("character_id") if isinstance(participants.get("A"), Mapping) else ""
    b = participants.get("B", {}).get("character_id") if isinstance(participants.get("B"), Mapping) else ""
    if not a or not b or a == b:
        add("block", "missing_ab_participants", "正反打合同缺 A/B 两个不同戏内对象。", "补 character_ids、character_slots 或 screen_sides。")

    sides = pattern.get("screen_sides") if isinstance(pattern.get("screen_sides"), Mapping) else {}
    mode = str(sides.get("spatial_mode") or "")
    if mode == "left_right":
        if not sides.get("left") or not sides.get("right") or sides.get("left") == sides.get("right"):
            add("block", "non_complementary_screen_sides", "A/B 镜没有形成左右互补站位。", "补 screen_left / screen_right，并锁定反打不互换。")
    elif mode == "vertical_depth_9x16":
        if not sides.get("upper_foreground") or not sides.get("lower_background"):
            add("block", "missing_vertical_depth_pair", "竖屏纵深对压模式缺上/前景与下/后景对位。", "补 upper_foreground / lower_background 站位。")
    else:
        add("block", "missing_screen_position_mode", "正反打合同缺明确左右或纵深站位模式。", "补左右站位；9:16 对压可签 vertical_depth_9x16。")

    eyeline = one_line(pattern.get("eyeline_match"))
    if not eyeline:
        add("block", "missing_eyeline_match", "正反打合同缺互补视线。", "写 A 看画右/B 看画左，或竖屏高低位互看。")
    if has_positive_camera_gaze(" ".join([eyeline, clip_blob(clip)])):
        add("block", "camera_gaze_not_allowed", "非 POV 正反打中出现看镜头/直视观众。", "改为看戏内对手、道具或画外目标；若是 POV 必须显式写 POV 叙事理由。")

    coverage_blob = one_line(pattern.get("coverage")) + " " + one_line(pattern.get("camera_coverage")) + " " + one_line(pattern.get("shot_pairing"))
    if OTS_RE.search(coverage_blob) and not FOREGROUND_SHOULDER_RE.search(coverage_blob):
        add("block", "ots_missing_foreground_shoulder", "OTS/过肩没有明确前景肩部/侧背遮挡层。", "写清谁的肩在前景、谁是焦点、前景肩部虚化。")

    cross_text = one_line(pattern.get("crossing_axis_policy")) + " " + one_line(pattern.get("buffer_or_reestablishing"))
    if CROSS_AXIS_ALLOWED_RE.search(cross_text) and not BUFFER_RE.search(cross_text):
        add("block", "cross_axis_without_buffer", "合同允许越轴但没有缓冲/重建空间镜。", "补建立镜、插入镜、中线移动、空镜或明确转场。")
    if CROSS_AXIS_RE.search(clip_blob(clip)) and not CROSS_AXIS_FORBID_RE.search(cross_text) and not BUFFER_RE.search(cross_text):
        add("block", "cross_axis_policy_ambiguous", "素材提到越轴/反轴但合同未说明禁止或缓冲。", "补 crossing_axis_policy 与 buffer_or_reestablishing。")

    closeup_blob = one_line(pattern.get("camera_coverage")) + " " + one_line(clip.get("continuity")) + " " + one_line(clip.get("shots"))
    if CLOSEUP_RE.search(closeup_blob) and not (
        str(clip.get("firstframe_png") or "").strip()
        or "face_anchor" in clip_blob(clip)
        or "脸锚" in clip_blob(clip)
        or "reference_group" in clip_blob(clip)
    ):
        add("warn", "closeup_anchor_pending", "近景/反打镜未看到已落档的近景锚定图或脸锚引用。", "出图前必须从 identity_registry.face_anchor_refs / 表情库 / 同源首帧补锚。")

    char_ids = [str(x) for x in clip.get("character_ids") or []]
    if len(char_ids) >= 3 and mode == "left_right":
        add("warn", "vertical_crowd_risk", "9:16 正反打含 3+ 主体，横向并排会导致脸小和关系乱。", "用建立镜 + 过肩/纵深 + 插入/反应近景，不做多人横排近景。")

    for key in CONTRACT_REQUIRED_FIELDS:
        if pattern.get(key) in (None, "", [], {}):
            add("block", "missing_contract_field", f"正反打合同缺字段 {key}。", "回 n2d-script 补 shot_reverse_contract。")
    return issues


def infer_cinematic_techniques(clip: Mapping[str, Any]) -> List[str]:
    blob = clip_blob(clip)
    template = str(clip.get("template") or "")
    techniques: List[str] = []
    if is_candidate(clip):
        techniques += ["establishing_master", "ots_pair", "clean_single", "reaction_shot", "insert_cutaway", "eyeline_cut"]
    if template in {"fight_exchange", "task_order"} or re.search(r"拔|推|落下|下马|抓|砍|挥|弹出|接下|match", blob, re.I):
        techniques += ["match_on_action", "insert_cutaway", "reaction_shot"]
    if template in {"compressed_flashback", "montage"} or "快闪" in blob:
        techniques += ["montage_ellipsis", "insert_cutaway", "j_cut_l_cut"]
    if template in {"public_confrontation", "relationship_turn", "reveal_reaction_chain"}:
        techniques += ["reestablishing_buffer", "axial_pressure", "reveal_closeup", "eyeline_cut"]
    out: List[str] = []
    for item in techniques:
        if item not in out:
            out.append(item)
    return out


def build_contract(root: Path, ep: str) -> Dict[str, Any]:
    root = root.resolve()
    ep = episode_label(ep)
    sb = storyboard(root, ep)
    clips = clips_from_storyboard(sb)
    axis_by_clip = axis_patterns(root, ep)
    bible_by_clip = continuity_shot_reverse(root, ep)
    patterns: List[Dict[str, Any]] = []
    all_issues: List[Dict[str, Any]] = []
    technique_rows: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, start=1):
        cid = clip_id(clip, idx)
        techniques = infer_cinematic_techniques(clip)
        if techniques:
            technique_rows.append({"clip_id": cid, "techniques": techniques})
        if not is_candidate(clip):
            continue
        pattern = build_pattern(ep, idx, clip, axis_by_clip.get(cid, {}), bible_by_clip.get(cid, {}))
        issues = audit_pattern(pattern, clip)
        pattern["audit"] = {"status": "block" if any(i["severity"] == "block" for i in issues) else "pass", "issues": issues}
        patterns.append(pattern)
        for issue in issues:
            all_issues.append({"clip_id": cid, **issue})
    summary = {
        "patterns": len(patterns),
        "block": sum(1 for i in all_issues if i["severity"] == "block"),
        "warn": sum(1 for i in all_issues if i["severity"] == "warn"),
        "info": sum(1 for i in all_issues if i["severity"] == "info"),
    }
    data = {
        "kind": KIND,
        "version": VERSION,
        "episode": ep,
        "status": "block" if summary["block"] else "pass",
        "generated_at": now_iso(),
        "generated_by": "skills/n2d/n2d-script/scripts/shot_reverse_contract.py",
        "sources": [
            {"name": name, "path": str(path), "exists": (root / path).is_file() if not path.is_absolute() else path.is_file(), "sha256": sha256_file((root / path) if not path.is_absolute() else path)}
            for name, path in source_paths(root, ep)
        ],
        "summary": summary,
        "patterns": patterns,
        "audit_issues": all_issues,
        "cinematic_technique_usage": technique_rows,
        "cinematic_grammar_library": "skills/n2d/n2d-script/references/cinematic_coverage_grammar.json",
        "vertical_9x16_global_rules": {
            "avoid": "不要频繁横向多人并排；清晰近景不要同时塞多张脸。",
            "prefer": "前景肩部 + 背景脸、纵深站位、道具插入、反应近景、建立/重建空间镜。",
            "reason": "竖屏脸部可读面积有限，横向多人并排会让脸小、关系乱、视线难对。",
        },
    }
    return data


def render_markdown(contract: Mapping[str, Any]) -> str:
    lines = [
        f"# {contract.get('episode')} 正反打合同与镜头语法审计",
        "",
        f"- status: {contract.get('status')}",
        f"- patterns: {contract.get('summary', {}).get('patterns', 0)}",
        f"- block: {contract.get('summary', {}).get('block', 0)}",
        f"- warn: {contract.get('summary', {}).get('warn', 0)}",
        "",
        "## 正反打合同",
        "",
        "| Clip | A | B | 站位模式 | 轴线 | 覆盖 | 审计 |",
        "|---|---|---|---|---|---|---|",
    ]
    for pattern in contract.get("patterns") or []:
        if not isinstance(pattern, Mapping):
            continue
        participants = pattern.get("participants") if isinstance(pattern.get("participants"), Mapping) else {}
        a = participants.get("A", {}).get("character_id") if isinstance(participants.get("A"), Mapping) else ""
        b = participants.get("B", {}).get("character_id") if isinstance(participants.get("B"), Mapping) else ""
        sides = pattern.get("screen_sides") if isinstance(pattern.get("screen_sides"), Mapping) else {}
        lines.append(
            f"| {pattern.get('clip_id')} | {a} | {b} | {sides.get('spatial_mode')} | "
            f"{one_line(pattern.get('axis_line'))[:80]} | {one_line(pattern.get('camera_coverage'))[:80]} | "
            f"{pattern.get('audit', {}).get('status')} |"
        )
    lines += ["", "## 审计问题", "", "| Clip | Severity | Code | Message |", "|---|---|---|---|"]
    for issue in contract.get("audit_issues") or []:
        if isinstance(issue, Mapping):
            lines.append(f"| {issue.get('clip_id')} | {issue.get('severity')} | {issue.get('code')} | {one_line(issue.get('message'))} |")
    if not contract.get("audit_issues"):
        lines.append("| - | pass | - | 未发现确定性硬伤 |")
    lines += ["", "## 传统影视镜头语法使用建议", "", "| Clip | Techniques |", "|---|---|"]
    for row in contract.get("cinematic_technique_usage") or []:
        if isinstance(row, Mapping):
            lines.append(f"| {row.get('clip_id')} | {', '.join(str(x) for x in row.get('techniques') or [])} |")
    lines += [
        "",
        "## 9:16 规则",
        "",
        "- 不频繁横向多人并排，近景优先单人 clean single / OTS。",
        "- 使用前景肩部、背景脸、上下高低位和纵深站位维持关系。",
        "- 插入道具、手部、火把、门框、尘土、眼神反应用于节奏和越轴缓冲。",
        "",
    ]
    return "\n".join(lines)


def axis_pattern_from_contract(pattern: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "pattern_id": pattern.get("pattern_id"),
        "source": "shot_reverse_contract",
        "applies_to": [pattern.get("clip_id")],
        "axis_line": pattern.get("axis_line"),
        "screen_sides": pattern.get("screen_sides"),
        "eyeline_match": pattern.get("eyeline_match"),
        "shot_pairing": pattern.get("shot_pairing"),
        "coverage_order": pattern.get("coverage_order"),
        "camera_coverage": pattern.get("camera_coverage"),
        "lens_height_distance_match": pattern.get("lens_height_distance_match"),
        "crossing_axis_policy": pattern.get("crossing_axis_policy"),
        "buffer_or_reestablishing": pattern.get("buffer_or_reestablishing"),
        "continuity_must": pattern.get("continuity_must"),
    }


def sync_axis_map(root: Path, ep: str, contract: Mapping[str, Any]) -> Optional[Path]:
    path = episode_dir(root, ep) / "axis_blocking_map.json"
    data = load_json(path)
    if not isinstance(data, dict):
        return None
    pattern_clip_ids = {str(p.get("clip_id")) for p in contract.get("patterns") or [] if isinstance(p, Mapping)}
    existing = []
    for row in data.get("shot_reverse_patterns") or []:
        applies = {str(x) for x in row.get("applies_to") or []} if isinstance(row, Mapping) else set()
        pattern_id = str(row.get("pattern_id") or "") if isinstance(row, Mapping) else ""
        generated_source = str(row.get("source") or "") == "shot_reverse_contract" if isinstance(row, Mapping) else False
        if applies.isdisjoint(pattern_clip_ids) and not generated_source and not pattern_id.startswith("SR_"):
            existing.append(row)
    existing.extend(axis_pattern_from_contract(p) for p in contract.get("patterns") or [] if isinstance(p, Mapping))
    data["shot_reverse_patterns"] = existing
    data["shot_reverse_contract_path"] = str(Path("脚本") / ep / "shot_reverse_contract.json")
    data["updated_at"] = now_iso()
    write_json_atomic(path, data)
    return path


def write_contract(root: Path, ep: str, *, sync_axis: bool = False) -> Dict[str, Any]:
    root = root.resolve()
    ep = episode_label(ep)
    contract = build_contract(root, ep)
    contract_path = episode_dir(root, ep) / "shot_reverse_contract.json"
    report_path = root / "生产数据" / f"shot_reverse_contract_{ep}.md"
    check_path = root / "生产数据" / f"shot_reverse_contract_check_{ep}.json"
    write_json_atomic(contract_path, contract)
    write_atomic(report_path, render_markdown(contract))
    check_payload = {
        "kind": CHECK_KIND,
        "version": VERSION,
        "episode": ep,
        "status": contract.get("status"),
        "generated_at": now_iso(),
        "contract_path": str(contract_path.relative_to(root)),
        "report_path": str(report_path.relative_to(root)),
        "summary": contract.get("summary"),
        "issues": contract.get("audit_issues"),
    }
    if sync_axis:
        synced = sync_axis_map(root, ep, contract)
        if synced:
            check_payload["synced_axis_blocking_map"] = str(synced.relative_to(root))
    write_json_atomic(check_path, check_payload)
    contract["contract_path"] = str(contract_path)
    contract["report_path"] = str(report_path)
    contract["check_path"] = str(check_path)
    return contract


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("episode")
    parser.add_argument("--write", action="store_true", help="write shot_reverse_contract.json and reports")
    parser.add_argument("--sync-axis-map", action="store_true", help="backfill axis_blocking_map.json#shot_reverse_patterns")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = args.root
    ep = episode_label(args.episode)
    result = write_contract(root, ep, sync_axis=args.sync_axis_map) if args.write else build_contract(root, ep)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{ep} shot_reverse_contract status={result.get('status')} patterns={result.get('summary', {}).get('patterns', 0)} block={result.get('summary', {}).get('block', 0)} warn={result.get('summary', {}).get('warn', 0)}")
    return 1 if result.get("status") == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
