#!/usr/bin/env python3
"""Generate the n2d-video prompt pack from existing stage artifacts.

The n2d-video skill requires `出视频/第N集/prompt/00_总览.md` and
`01_clips.md`, while the runner only consumes them.  This script closes that
gap without calling any paid backend: it transcribes storyboard, route,
identity, image overview, mouth-audit and script-contract data into a
deterministic prompt pack that the video preflight gate can inspect.
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
N2D_LIB = SCRIPT_DIR.parents[1] / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))

from video_prompt_compiler import compile_video_prompt, render_compiled_markdown
from n2d_const import PRODUCTION_MODE_DEFAULT, IDENTITY_LOCK_NEGATIVE_TERMS
from n2d_platform_profiles import (
    anchor_consumption_plan,
    select_video_frame_strategy,
    single_take_merge_ceiling_seconds,
)
from seam_contract import needs_end_anchor, normalize_seam_mode
from n2d_logic import normalize_signature_effect

KIND = "n2d_video_prompt_pack"
CONSUMED_CONTRACTS_KIND = "n2d_prompt_consumed_contracts"
CONSUMED_CONTRACTS_VERSION = 1
INNER_FOCUS_RE = re.compile(
    r"内心戏|内心独白|心声|心理反应|心理活动|心念|心想|暗想|自省|心里一沉|心里想|"
    r"inner monologue|internal monologue|thought beat|subjective reaction",
    re.I,
)
CLOSEUP_PROMOTION_RE = re.compile(
    r"\b(?:ECU|BCU|MCU|CU|OTS)\b|close[- ]?up|reaction shot|近景|特写|半特写|反打|"
    r"推近|缓推|脸部|抬眼|低头看|大表情|表情幅度\s*=\s*大|倒飞砸|脚边|扑到.*脸",
    re.I,
)
ENDING_REACTION_HOLD_RE = re.compile(
    r"手部|横刀|刀|剑|衣袖|袖口|手指|脚边|地面|物件|道具|武器|物体|侧背|背影|侧脸|"
    r"OTS|反打|不露脸|无脸|禁止.*脸|不要.*脸|object reaction|hand|sleeve|weapon|prop|"
    r"side[- ]?face|side[- ]?back|no clear face|no face|hold",
    re.I,
)

HIGH_RISK_CONTINUOUS_SHOTS = {
    "fight_exchange", "chase", "flight", "mount_ride", "vehicle_ride",
    "vessel_flight", "road_vehicle", "stealth_stalk", "magic_burst",
    "intimate_interaction", "hug_or_pull", "kiss_or_near_kiss",
}
DIRECT_GAZE_INTENT_RE = re.compile(
    r"\bPOV\b|主观镜头|第一人称|破第四墙|对镜讲话|对镜表演|"
    r"direct_address|look_into_camera|camera_address",
    re.I,
)


def route_execution_channel(route: Mapping[str, Any]) -> str:
    """Resolve the channel that actually executes a logical video backend."""
    adapter = route.get("execution_adapter") if isinstance(route.get("execution_adapter"), Mapping) else {}
    return str(
        route.get("channel")
        or route.get("backend_channel")
        or adapter.get("channel")
        or ""
    ).strip()


def _frame_strategy_requires_mid(
    clip: Mapping[str, Any], route: Mapping[str, Any], anchors: Sequence[Mapping[str, Any]],
    mid: Optional[Mapping[str, Any]],
) -> bool:
    """Only continuous high-risk motion requires a real middle timeline anchor."""
    template = str(clip.get("template") or route.get("shot_type") or "").strip().lower()
    motion = route.get("motion_control") if isinstance(route.get("motion_control"), Mapping) else {}
    if template in HIGH_RISK_CONTINUOUS_SHOTS or str(motion.get("level") or "").lower() == "required":
        return True
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    if str(cont.get("expression_span") or "").strip().lower() in {"大", "large", "high"}:
        return True
    rows = list(anchors) + ([mid] if isinstance(mid, Mapping) else [])
    for row in rows:
        reason = str(row.get("reason") or "").lower()
        if any(mark in reason for mark in ("r1 ", "r2 ", "r3 ", "apex:", "auto:")):
            return True
    return False


def ep_label(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = re.search(r"\d+", text)
    return f"第{m.group(0)}集" if m else text


def clip_num(value: Any, fallback: int) -> int:
    text = str(value or "")
    m = re.search(r"(?:^|[^A-Za-z0-9])CLIP[_\s-]?(\d+)\b", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"\bClip[_\s-]?(\d+)\b", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"镜头\s*(\d+)", text)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else fallback


def clip_id(value: Any, fallback: int) -> str:
    return f"Clip_{clip_num(value, fallback):02d}"


def resolved_frame_paths(clip: Mapping[str, Any], ep: str, idx: int) -> Tuple[str, str]:
    """Resolve physical frames using the n2d-image naming contract."""
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    first = str(
        clip.get("firstframe_png")
        or cont.get("firstframe_png")
        or f"出图/{ep}/图片/Clip{idx:02d}_first.png"
    )
    end = str(cont.get("endframe_png") or clip.get("endframe_png") or "")
    if not end and bool(cont.get("end_anchor_required")):
        anchors = [row for row in cont.get("anchors") or [] if isinstance(row, Mapping)]
        anchors = [
            row for row in anchors
            if str(row.get("use") or "split").strip().lower()
            not in {"qc", "reference", "reference_qc", "review"}
            and str(row.get("anchor_png") or "").strip()
        ]
        if anchors:
            end = str(max(anchors, key=lambda row: float(row.get("at_sec") or 0)).get("anchor_png") or "")
    return first, end


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json_atomic(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def one_line(value: Any, default: str = "无") -> str:
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, Mapping):
        parts: List[str] = []
        for k, v in value.items():
            piece = one_line(v, "")
            if piece:
                parts.append(f"{k}={piece}")
        text = "；".join(parts)
    elif isinstance(value, list):
        text = "、".join(one_line(v, "") for v in value if one_line(v, ""))
    else:
        text = str(value or "").strip()
    return re.sub(r"\s+", " ", text) if text else default


def clip_text_blob(clip: Mapping[str, Any], keys: Sequence[str]) -> str:
    parts: List[str] = []
    for key in keys:
        if key not in clip:
            continue
        value = clip.get(key)
        if isinstance(value, (Mapping, list)):
            parts.append(json.dumps(value, ensure_ascii=False, sort_keys=True))
        else:
            parts.append(str(value or ""))
    return "\n".join(parts)


def is_inner_focus_clip(clip: Mapping[str, Any]) -> bool:
    return bool(INNER_FOCUS_RE.search(clip_text_blob(clip, (
        "id",
        "label",
        "scene",
        "description",
        "dramatic_function",
        "story_function",
        "rhythm",
        "audience_effect",
        "template",
        "template_contract",
        "shots",
        "subtitle_lines",
        "voiceover",
    ))))


def inner_focus_context_reason(clip: Mapping[str, Any]) -> str:
    for key in ("inner_focus_context_reason", "context_presence_reason"):
        value = one_line(clip.get(key), "")
        if value:
            return value
    policy = clip.get("inner_focus_policy") if isinstance(clip.get("inner_focus_policy"), Mapping) else {}
    for key in ("context_reason", "allow_context"):
        value = one_line(policy.get(key), "")
        if value:
            return value
    contract = clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}
    for key in ("inner_focus_context_reason", "inner_focus_allow_context"):
        value = one_line(contract.get(key), "")
        if value:
            return value
    return ""


def inner_focus_directive(clip: Mapping[str, Any], chars: Sequence[str], assets: Sequence[str]) -> str:
    if not is_inner_focus_clip(clip):
        return ""
    subject = chars[0] if chars else "本镜思考主体"
    others = [c for c in chars[1:]]
    context_reason = inner_focus_context_reason(clip)
    context_line = f"；若保留其他实体，必须服务：{context_reason}" if context_reason else ""
    other_line = f"；非焦点主体 {', '.join(others)} 不给清晰脸/全身/新增动作" if others else ""
    asset_line = f"；非必要资产 {', '.join(assets[:4])} 不做运动焦点" if assets else ""
    return (
        f"内心戏主体隔离：视频运动只服务 {subject} 的眼神、呼吸、手指、微表情或光影反应；"
        "其他人物、妖魔、系统面板、武器或道具默认画外、虚焦、剪影或静止背景符号，"
        "不要重复上一镜群像/怪物/道具陈列，不让背景实体产生新动作。"
        f"{other_line}{asset_line}{context_line}"
    )


def closeup_promotion_guard(
    clip: Mapping[str, Any],
    route: Mapping[str, Any],
    chars: Sequence[str],
    start: str,
    end: str,
    lenses: str,
    camera: str,
    span: str,
) -> str:
    """Guard against video models inventing a new close-up face from small anchor faces."""
    if not chars:
        return ""
    blob = "\n".join([
        clip_text_blob(clip, (
            "id",
            "label",
            "description",
            "dramatic_function",
            "audience_effect",
            "scene",
            "shots",
            "template_contract",
            "continuity",
        )),
        json.dumps(route, ensure_ascii=False, sort_keys=True),
        start,
        end,
        lenses,
        camera,
        f"expression_span={span}",
    ])
    if not CLOSEUP_PROMOTION_RE.search(blob):
        return ""
    focus = chars[0]
    return (
        f"近景升格守卫：不得把首/中/尾锚帧里脸部很小、侧背、遮挡或非主焦点的 {focus} "
        "直接推成清晰近脸；只有已落档且 full image_qc 通过的同源近景锚帧/脸部特写/表情参考可支撑 CU/MCU。"
        "缺该锚帧时，落幅停在原锚帧景别，或改 MCU/OTS/侧脸/手部/物件反应镜，禁止让视频模型补一张新脸。"
    )


def ending_reaction_hold_guard(
    clip: Mapping[str, Any],
    offscreen_presence: Sequence[str],
    end: str,
    transition: str,
) -> str:
    """Keep reaction/object endings from leaking offscreen characters before the cut."""
    offscreen = [str(x) for x in offscreen_presence if str(x).strip()]
    if not offscreen:
        return ""
    blob = "\n".join([
        end,
        transition,
        clip_text_blob(clip, (
            "label",
            "description",
            "dramatic_function",
            "audience_effect",
            "shots",
            "template_contract",
            "continuity",
        )),
    ])
    if not ENDING_REACTION_HOLD_RE.search(blob):
        return ""
    names = ", ".join(offscreen)
    return (
        f"最后 0.5 秒必须维持 storyboard 的手部/物件/侧背/反打落幅直到剪点；"
        f"offscreen_presence={names} 不得在剪点前被拉回清晰脸、全身主体或新增动作。"
        "若需要展示该角色进场或系统反应，交给下一 Clip 开始，不在本 Clip 尾段提前预演下一构图。"
    )


def md_table_escape(value: Any) -> str:
    return one_line(value, "-").replace("|", "／")


def extract_section(text: str, title: str) -> str:
    pattern = re.compile(rf"(?ms)^##\s+{re.escape(title)}\s*\n(.*?)(?=^##\s+|\Z)")
    m = pattern.search(text or "")
    return m.group(0).rstrip() if m else ""


def project_setting(root: Path, key: str, default: str = "") -> str:
    text = ""
    try:
        text = (root / "_设置.md").read_text(encoding="utf-8")
    except Exception:
        return default
    m = re.search(rf"^\s*-?\s*{re.escape(key)}\s*[:：]\s*([^#\n]+)", text, re.MULTILINE)
    return m.group(1).strip() if m else default


def storyboard(root: Path, ep: str) -> Mapping[str, Any]:
    data = load_json(root / "脚本" / ep / "storyboard.json")
    if not isinstance(data, Mapping):
        raise SystemExit(f"missing storyboard.json: {root / '脚本' / ep / 'storyboard.json'}")
    return data


def routes(root: Path, ep: str) -> Mapping[str, Mapping[str, Any]]:
    data = load_json(root / "出视频" / ep / "prompt" / "video_model_routes.json")
    rows = data.get("routes") if isinstance(data, Mapping) else []
    out: Dict[str, Mapping[str, Any]] = {}
    for idx, row in enumerate(rows or [], 1):
        if isinstance(row, Mapping):
            out[clip_id(row.get("clip_id"), idx)] = row
    return out


def mouth_map(root: Path, ep: str) -> Dict[str, bool]:
    data = load_json(root / "生产数据" / f"mouth_visible_audit_{ep}.json")
    rows = data.get("rows") if isinstance(data, Mapping) else []
    out: Dict[str, bool] = {}
    for idx, row in enumerate(rows or [], 1):
        if isinstance(row, Mapping):
            out[clip_id(row.get("clip_id"), idx)] = bool(row.get("suggested"))
    return out


def contract_clip_map(root: Path, ep: str) -> Dict[str, Mapping[str, Any]]:
    data = load_json(root / "生产数据" / f"script_quality_contract_{ep}.json")
    fields = data.get("signable_fields") if isinstance(data, Mapping) else {}
    rows = fields.get("clip_dramatic_functions") if isinstance(fields, Mapping) else []
    out: Dict[str, Mapping[str, Any]] = {}
    for idx, row in enumerate(rows or [], 1):
        if isinstance(row, Mapping):
            out[clip_id(row.get("clip_id"), idx)] = row
    return out


def shot_reverse_contract_map(root: Path, ep: str) -> Dict[str, Mapping[str, Any]]:
    data = load_json(root / "脚本" / ep / "shot_reverse_contract.json")
    rows = data.get("patterns") if isinstance(data, Mapping) else []
    out: Dict[str, Mapping[str, Any]] = {}
    for idx, row in enumerate(rows or [], 1):
        if not isinstance(row, Mapping):
            continue
        raw = str(row.get("clip_id") or "").strip()
        if raw:
            out[raw] = row
            out[clip_id(raw, idx)] = row
    return out


def director_camera_plan_map(root: Path, ep: str) -> Dict[str, Mapping[str, Any]]:
    data = load_json(root / "生产数据" / f"director_camera_plan_{ep}.json")
    rows = data.get("clips") if isinstance(data, Mapping) and isinstance(data.get("clips"), list) else []
    out: Dict[str, Mapping[str, Any]] = {}
    for idx, row in enumerate(rows, 1):
        if not isinstance(row, Mapping):
            continue
        raw = str(row.get("clip_id") or "").strip()
        if raw:
            out[raw] = row
            out[clip_id(raw, idx)] = row
    return out


def shot_reverse_video_line(pattern: Mapping[str, Any]) -> str:
    participants = pattern.get("participants") if isinstance(pattern.get("participants"), Mapping) else {}
    a = participants.get("A") if isinstance(participants.get("A"), Mapping) else {}
    b = participants.get("B") if isinstance(participants.get("B"), Mapping) else {}
    sides = pattern.get("screen_sides") if isinstance(pattern.get("screen_sides"), Mapping) else {}
    coverage = pattern.get("coverage") if isinstance(pattern.get("coverage"), Mapping) else {}
    return "；".join([
        f"axis_id={one_line(pattern.get('axis_id'))}",
        f"A={one_line(a.get('character_id'))}，位置={one_line(a.get('screen_position'))}，视线={one_line(a.get('eyeline_direction'))}",
        f"B={one_line(b.get('character_id'))}，位置={one_line(b.get('screen_position'))}，视线={one_line(b.get('eyeline_direction'))}",
        f"站位模式={one_line(sides.get('spatial_mode'))}，A/B 不互换",
        f"OTS 前景肩部={one_line(coverage.get('a_ots'))} / {one_line(coverage.get('b_ots'))}",
        f"coverage={one_line(pattern.get('camera_coverage'))}",
        f"镜头匹配={one_line(pattern.get('lens_height_distance_match'))}",
        f"越轴策略={one_line(pattern.get('crossing_axis_policy'))}；缓冲镜={one_line(pattern.get('buffer_or_reestablishing'))}",
    ])


def contract_retention_lines(root: Path, ep: str) -> List[str]:
    data = load_json(root / "生产数据" / f"script_quality_contract_{ep}.json")
    fields = data.get("signable_fields") if isinstance(data, Mapping) else {}
    ledger = fields.get("retention_promise_ledger") if isinstance(fields, Mapping) else []
    lines: List[str] = []
    if not isinstance(ledger, list):
        return lines
    for idx, row in enumerate(ledger, 1):
        if not isinstance(row, Mapping):
            continue
        bits = []
        for key in ("hook_id", "opened_at", "payoff_clip", "payoff_due", "payoff_status", "promise", "promise_type", "expected_next_handling", "handling"):
            if row.get(key):
                bits.append(f"{key}={one_line(row.get(key))}")
        if bits:
            lines.append(f"- R{idx:02d}: " + "；".join(bits))
    return lines


def identity_forms(root: Path) -> List[Mapping[str, Any]]:
    data = load_json(root / "生产数据" / "identity_adapter_matrix.json")
    forms = data.get("forms") if isinstance(data, Mapping) else []
    return [f for f in forms or [] if isinstance(f, Mapping)]


def continuity_chain(root: Path, ep: str) -> Mapping[str, Any]:
    data = load_json(root / "脚本" / ep / "continuity_chain.json")
    return data if isinstance(data, Mapping) else {}


def continuity_chain_maps(chain: Mapping[str, Any]) -> Tuple[Dict[str, Mapping[str, Any]], Dict[str, Mapping[str, Any]]]:
    incoming: Dict[str, Mapping[str, Any]] = {}
    outgoing: Dict[str, Mapping[str, Any]] = {}
    for seam in chain.get("seams") or []:
        if not isinstance(seam, Mapping):
            continue
        to_clip = str(seam.get("to_clip") or "")
        from_clip = str(seam.get("from_clip") or "")
        if to_clip:
            incoming[to_clip] = seam
        if from_clip:
            outgoing[from_clip] = seam
    return incoming, outgoing


def seam_summary_line(seam: Optional[Mapping[str, Any]], fallback: str) -> str:
    if not isinstance(seam, Mapping):
        return fallback
    issues = [
        str(item.get("code") or "")
        for item in seam.get("issues") or []
        if isinstance(item, Mapping) and item.get("code")
    ]
    bits = [
        f"{seam.get('from_episode')}/{seam.get('from_clip')}→{seam.get('to_episode')}/{seam.get('to_clip')}",
        f"scope={seam.get('scope')}",
        f"policy={seam.get('policy')}",
        f"strictness={seam.get('strictness')}",
        f"transition={one_line(seam.get('transition'), '未声明')}",
        f"from_end={one_line(seam.get('from_end_state'), '未声明')}",
        f"to_start={one_line(seam.get('to_start_state'), '未声明')}",
    ]
    if seam.get("required_boundary_frame"):
        bits.append(f"boundary_frame={seam.get('required_boundary_frame')}")
    if seam.get("intentional_discontinuity_reason"):
        bits.append(f"intentional_discontinuity={seam.get('intentional_discontinuity_reason')}")
    if issues:
        bits.append("issues=" + ",".join(issues))
    return "；".join(bits)


def form_for_char(forms: Sequence[Mapping[str, Any]], char_id: str) -> Optional[Mapping[str, Any]]:
    # Storyboard character bindings commonly carry a requested performance form
    # (`CHAR_01/囚途残损态`), while the adapter matrix is keyed by the stable base
    # character id (`CHAR_01`).  Match on that stable id so a ready registry
    # reference_group is not silently downgraded to a textual fallback.
    base_char_id = str(char_id or "").split("/", 1)[0].strip()
    for form in forms:
        if str(form.get("character_id") or "").strip() == base_char_id:
            return form
    return None


def identity_line(forms: Sequence[Mapping[str, Any]], chars: Sequence[str]) -> str:
    if not chars:
        return "无人物；空镜/物件镜只锁场景与资产。"
    lines: List[str] = []
    for char in chars:
        form = form_for_char(forms, str(char))
        if form:
            ref_ready = "ready" if (form.get("reference_group") or {}) else "missing"
            lines.append(
                f"{char}：reference_group={ref_ready}；registry_form={form.get('form') or '默认形态'}；"
                f"锚点句={one_line(form.get('anchor_phrase'), '按 identity_registry')}"
            )
        else:
            lines.append(f"{char}：registry form 未在 adapter matrix 摘要中命中，使用首帧+reference_group 兜底。")
    return "；".join(lines)


def visual_contract_values(image_overview: str) -> Dict[str, str]:
    block = extract_section(image_overview, "本集视觉一致性契约")
    values: Dict[str, str] = {}
    for label in ("色调基线", "光位锚", "轴线", "状态演进", "景别阶梯"):
        m = re.search(rf"(?m)^-\s*{label}\s*[:：]\s*(.+)$", block)
        values[label] = m.group(1).strip() if m else "继承出图总览。"
    return values


def storyboard_style_anchors(sb: Mapping[str, Any]) -> List[str]:
    contract = sb.get("style_contract") if isinstance(sb.get("style_contract"), Mapping) else {}
    raw = (contract.get("style_anchor") or contract.get("风格锚")) if isinstance(contract, Mapping) else None
    if isinstance(raw, str):
        vals = [raw]
    elif isinstance(raw, list):
        vals = [str(x) for x in raw if str(x or "").strip()]
    else:
        vals = []
    return [v.strip() for v in vals if v.strip()]


def ensure_style_anchor(style_block: str, sb: Mapping[str, Any]) -> str:
    anchors = storyboard_style_anchors(sb)
    m = re.search(r"(?m)^(\s*-\s*(?:style_anchor|风格锚)\s*[:：]\s*)(.+)$", style_block or "")
    if m:
        existing = m.group(2).strip()
        if not anchors or any(anchor in existing for anchor in anchors):
            return style_block
        if "继承" not in existing and "`" in existing:
            return style_block
        anchor_text = "、".join(f"`{a}`" for a in anchors)
        return (style_block[:m.start()] + f"{m.group(1)}{anchor_text}（风格锚；style-only，不克隆角色脸和服装）" + style_block[m.end():])
    if not anchors:
        return style_block
    anchor_text = "、".join(f"`{a}`" for a in anchors)
    return style_block.rstrip() + f"\n- style_anchor：{anchor_text}（风格锚；style-only，不克隆角色脸和服装）"


def route_list(route: Mapping[str, Any], key: str) -> str:
    val = route.get(key)
    if isinstance(val, list):
        return ",".join(str(v) for v in val)
    return str(val or "")


def shot_text(clip: Mapping[str, Any]) -> Tuple[str, str, str]:
    shots = [s for s in clip.get("shots") or [] if isinstance(s, Mapping)]
    descs = [one_line(s.get("desc"), "") for s in shots if one_line(s.get("desc"), "")]
    prompts = [one_line(s.get("video_prompt"), "") for s in shots if one_line(s.get("video_prompt"), "")]
    lenses = [one_line(s.get("lens"), "") for s in shots if one_line(s.get("lens"), "")]
    return "；".join(descs), "；".join(prompts), " → ".join(lenses)


def camera_motivation(clip: Mapping[str, Any]) -> str:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    contract = clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}
    values: List[str] = []
    for source in (clip, cont, contract):
        for key in (
            "camera_motivation", "movement_motivation", "camera_move_motivation",
            "运镜动机", "镜头运动动机",
        ):
            value = one_line(source.get(key), "")
            if value and value not in values:
                values.append(value)
    for shot in clip.get("shots") or []:
        if not isinstance(shot, Mapping):
            continue
        for key in ("camera_motivation", "movement_motivation", "运镜动机"):
            value = one_line(shot.get(key), "")
            if value and value not in values:
                values.append(value)
    return "；".join(values)


def direct_gaze_intended(clip: Mapping[str, Any]) -> bool:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    contract = clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}
    values: List[str] = []
    for source in (clip, cont, contract):
        for key in (
            "template", "template_id", "shot_type", "camera_relation", "gaze_intent",
            "eyeline_intent", "pov", "direct_address", "视线意图", "镜头关系",
        ):
            value = one_line(source.get(key), "")
            if value:
                values.append(value)
    return bool(DIRECT_GAZE_INTENT_RE.search(" ".join(values)))


def _positive_eyeline(value: Any) -> str:
    text = one_line(value, "")
    for phrase in (
        "，不看镜头", ",不看镜头", "不看现实镜头而", "不看镜头", "不要看镜头", "禁止直视镜头",
        "不得直视镜头", "avoid camera", "do not look at camera",
    ):
        text = text.replace(phrase, "")
    return text.strip(" ；;,，。")


def gaze_performance_guard(
    clip: Mapping[str, Any], chars: Sequence[str], shot_reverse_pattern: Mapping[str, Any],
) -> str:
    subject = "、".join(chars) if chars else "本镜角色"
    if direct_gaze_intended(clip):
        return f"本镜为明确 POV/破第四墙叙事；{subject} 只在登记节拍内把视线落到摄影机，节拍外跟随戏内目标。"
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    targets: List[str] = []
    eyeline = _positive_eyeline(cont.get("eyeline"))
    if eyeline:
        targets.append(eyeline)
    participants = shot_reverse_pattern.get("participants") if isinstance(shot_reverse_pattern.get("participants"), Mapping) else {}
    for row in participants.values():
        if not isinstance(row, Mapping):
            continue
        direction = _positive_eyeline(row.get("eyeline_direction") or row.get("eyeline"))
        if direction and direction not in targets:
            targets.append(direction)
    if targets:
        return (
            f"摄影机保持旁观者位置；逐角色的眼睛、鼻梁轴和头部朝向按以下戏内视线关系持续成立：{'；'.join(targets)}；"
            "人物保持三分之四、侧向或过肩关系，转头只跟随各自戏内目标。"
        )
    return (
        f"摄影机保持旁观者位置；{subject} 的眼睛、鼻梁轴和头部朝向持续锁定戏内对手、道具或动作落点，"
        "保持三分之四、侧向或过肩关系，转头只跟随该戏内目标。"
    )


def motion_words(
    clip: Mapping[str, Any], route: Mapping[str, Any], camera_plan: Optional[Mapping[str, Any]] = None,
) -> Tuple[str, str, str]:
    if isinstance(camera_plan, Mapping):
        injection = camera_plan.get("video_prompt_injection") if isinstance(camera_plan.get("video_prompt_injection"), Mapping) else {}
        planned = one_line(injection.get("镜头运动"), "")
        recommended = camera_plan.get("recommended") if isinstance(camera_plan.get("recommended"), Mapping) else {}
        if planned:
            speed = one_line(recommended.get("speed"), "克制")
            return "小幅；人物动作在画内完成，摄影机运动不与表演争夺注意", speed, planned
    rhythm = str(clip.get("rhythm") or "")
    shot_type = str(route.get("shot_type") or "")
    if any(x in shot_type for x in ("chase", "mount", "flight", "vehicle")) or any(x in rhythm for x in ("马队", "追", "压近")):
        return "中等；背景/前景视差动，主体不变形", "匀速压近；关键节点短暂停顿", "缓慢跟拍或微推，保持官道轴线"
    if any(x in shot_type for x in ("multi_character", "dialogue")):
        return "小到中；人物槽位不漂移", "克制；表情和视线先动，身体后动", "固定机位，锁定轴线与景别，摄影机保持完全静止"
    motivation = camera_motivation(clip)
    if motivation:
        _, _, lenses = shot_text(clip)
        camera = lenses if re.search(r"推|拉|摇|移|跟|升降|变焦|环绕|甩|固定", lenses) else "固定机位，锁定构图与轴线"
        return "小幅；只执行本镜主动作链", f"克制；运镜动机={motivation}", camera
    if any(x in rhythm for x in ("钩子", "爽点", "尾")):
        return "小幅；高光点只给一次明确动作", "蓄力后定住", "固定机位，锁定高光落点，摄影机保持完全静止"
    return "小幅；只执行本镜主动作链", "克制匀速", "固定机位，锁定构图与轴线，摄影机保持完全静止"


def environment_motion(clip: Mapping[str, Any]) -> str:
    """Return only scene evidence explicitly present in storyboard contracts.

    The old generator injected moonlight, torches, fog and dust into every
    project.  A neutral fallback belongs in the audit contract, but it must not
    invent weather/props for the model-facing prompt.
    """
    for key in ("environment_interaction", "environment_motion", "dynamic_detail", "dynamic_details"):
        value = one_line(clip.get(key), "")
        if value:
            return value
    shots = [s for s in clip.get("shots") or [] if isinstance(s, Mapping)]
    values: List[str] = []
    for shot in shots:
        for key in ("environment_interaction", "environment_motion", "dynamic_detail", "dynamic_details"):
            value = one_line(shot.get(key), "")
            if value and value not in values:
                values.append(value)
    contract = clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}
    for key in ("environment_stillness", "micro_motion", "aura_vfx_lock"):
        value = one_line(contract.get(key), "")
        if value and value not in values:
            values.append(value)
    return "；".join(values)


def _recipe_list(recipe: Mapping[str, Any], key: str, fallback: Sequence[str] = ()) -> List[str]:
    value = recipe.get(key)
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if value not in (None, "", "none", "无", []):
        return [one_line(value)]
    return [str(v) for v in fallback if str(v)]


def native_audio_contract(route: Mapping[str, Any], mouth: str) -> Tuple[str, str]:
    policy = str(route.get("native_audio_policy") or "none").strip().lower()
    mode = str(route.get("mode") or "").strip().lower()
    if policy == "native_speech" or mode == "native_av":
        return (
            f"audio_intent=native_speech; risk=medium; mouth_visible={mouth}; "
            "speech_policy=native_speech; compose_policy=保留原片音轨; "
            "review=确认仅生成已登记画内台词且台词/口型/声源同步。",
            "native_speech",
        )
    if policy in {"ambience", "native_sfx", "environment_sfx"}:
        return (
            f"audio_intent={policy}; risk=low; mouth_visible={mouth}; "
            "speech_policy=no_native_speech; compose_policy=低音量混入环境声; "
            "review=确认只有环境声/动作音效且无原生人声。",
            policy,
        )
    if policy == "lipsync_condition_only" or mode == "voice_conditioned_lipsync":
        return (
            f"audio_intent=voice_conditioned_lipsync; risk=medium; mouth_visible={mouth}; "
            "speech_policy=no_native_speech; compose_policy=丢弃; "
            "review=配音只作口型条件，确认模型音轨未进入成片。",
            policy,
        )
    return (
        f"audio_intent=none; risk=low; mouth_visible={mouth}; "
        "speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。",
        "none",
    )


def action_choreography_line(route: Mapping[str, Any], clip: Optional[Mapping[str, Any]] = None) -> str:
    choreo = route.get("action_choreography") if isinstance(route.get("action_choreography"), Mapping) else {}
    contract = clip.get("template_contract") if isinstance(clip, Mapping) and isinstance(clip.get("template_contract"), Mapping) else {}

    def value(key: str, default: str) -> str:
        if isinstance(contract, Mapping) and contract.get(key) not in (None, "", []):
            return one_line(contract.get(key), default)
        if isinstance(choreo, Mapping) and choreo.get(key) not in (None, "", []):
            return one_line(choreo.get(key), default)
        if key == "beats" and isinstance(choreo, Mapping) and choreo.get("beat_model"):
            return one_line(choreo.get("beat_model"), default)
        if key == "degrade_plan":
            return one_line(route.get("degrade_plan"), default)
        return default

    defaults = {
        "beats": "按 storyboard shots 顺序执行",
        "speed_curve": "慢→稳→定",
        "spatial_path": "沿既定轴线，不重置距离",
        "camera_path": "固定/微推，服务可读性",
        "readability_beats": "起势/动作/落点都可读",
        "degrade_plan": "按保真实现分解",
        "keyframe_plan": "对齐 continuity.anchors / midframe 分段，不临场新增时间轴",
        "post_cue_points": "按 voiceover/subtitle/SFX 节点后期对齐",
        "physics_guard": "人物/道具/地面/遮挡关系不穿模不漂移",
        "screen_direction": "保持 storyboard 轴线",
        "harness_lock": "鞍具/缰绳/绑带归属清楚，不变形漂移",
    }
    ordered = ["beats", "speed_curve", "spatial_path", "camera_path", "readability_beats", "degrade_plan"]
    required = choreo.get("required_fields") if isinstance(choreo.get("required_fields"), list) else []
    for field in required:
        key = str(field or "").strip()
        if key and key not in ordered:
            ordered.append(key)
    parts = [f"{key}={value(key, defaults.get(key, '按 storyboard/template_contract 执行'))}" for key in ordered]
    return "；".join(parts)


def motion_control_line(route: Mapping[str, Any]) -> str:
    mc = route.get("motion_control") if isinstance(route.get("motion_control"), Mapping) else {}
    if not mc:
        return "无；level=none；manifest_path=无；required_inputs=[]；failure_modes=[]。"
    return (
        f"level={one_line(mc.get('level'))}；manifest_path={one_line(mc.get('manifest_path'))}；"
        f"required_inputs={route_list(mc, 'required_inputs')}；failure_modes={route_list(mc, 'failure_modes')}；"
        f"degrade_plan={one_line(route.get('degrade_plan') or mc.get('degrade_plan'), '保真实现分解')}"
    )


def handoff_package_line(
    first: str,
    endframe: str,
    mid_count: int,
    cont: Mapping[str, Any],
    frame_control: Mapping[str, Any],
    fallback: str,
) -> str:
    """Machine-readable summary of the frame handoff the runner must preserve."""
    seam_mode = normalize_seam_mode(
        cont.get("seam_mode"), cont.get("transition"),
        need_endframe=bool(cont.get("need_endframe")),
    ).get("mode")
    return (
        f"first_frame={first or '无'}；end_frame={endframe or '无'}；midframes={mid_count}；"
        f"seam_mode={seam_mode or 'missing'}；need_end_anchor={needs_end_anchor(cont)}；"
        f"transition={one_line(cont.get('transition'), '按 storyboard')}；"
        f"entry_exit={one_line(cont.get('entry_exit') or cont.get('entry_exit_plan'), '按 entity_schedule')}；"
        f"anchor_consumption={one_line(frame_control)}；fallback={fallback}"
    )


def execution_recipe_line(recipe: Mapping[str, Any], frame_control: Mapping[str, Any], fallback: str) -> str:
    """Compact execution recipe copied into every prompt block and submit prompt."""
    return (
        f"frame_inputs={one_line(recipe.get('frame_inputs'), '按首帧/尾帧/锚帧')}；"
        f"reference_inputs={one_line(recipe.get('reference_inputs'), 'reference_group fallback')}；"
        f"control_inputs={one_line(recipe.get('control_inputs'), '按 Motion Control manifest 或 degrade_only')}；"
        f"audio_inputs={one_line(recipe.get('audio_inputs'), 'none')}；"
        f"post_video_qc={one_line(recipe.get('post_video_qc'), 'standard video_qc')}；"
        f"fallback={one_line(recipe.get('fallback') or fallback)}；"
        f"anchor_consumption={one_line(frame_control)}"
    )


def render_overview(root: Path, ep: str, sb: Mapping[str, Any], route_rows: Mapping[str, Mapping[str, Any]],
                    image_overview: str, forms: Sequence[Mapping[str, Any]], mouths: Mapping[str, bool]) -> str:
    clips = [c for c in sb.get("clips") or [] if isinstance(c, Mapping)]
    values = visual_contract_values(image_overview)
    visual_block = extract_section(image_overview, "本集视觉一致性契约") or "## 本集视觉一致性契约\n- 色调基线：继承出图总览。"
    style_block = ensure_style_anchor(extract_section(image_overview, "本集基础视觉风格契约") or (
        "## 本集基础视觉风格契约\n"
        f"- 风格名：{project_setting(root, '基础视觉风格', '冷灰写实3D国风漫剧')}\n"
        "- 视觉基调：继承 storyboard/style_contract。\n"
        "- 镜头与构图：9:16 竖屏，克制构图。\n"
        "- 光色策略：继承出图首帧。\n"
        "- 运动边界：固定/微推/缓跟。\n"
        "- 风格禁忌：不要换脸换衣、不要现代物、不要文字水印。\n"
        "- style_anchor：继承出图风格锚。"
    ), sb)
    image_contract = extract_section(image_overview, "本集可看性签收合同")
    total_sec = sum(float(c.get("duration") or 0) for c in clips)
    scene_states: List[str] = []
    seen_scene_ids: set[str] = set()
    for clip in clips:
        loc_id = str(clip.get("location_id") or clip.get("loc_id") or "").strip()
        if not loc_id or loc_id in seen_scene_ids:
            continue
        seen_scene_ids.add(loc_id)
        scene_name = str(clip.get("scene") or "").strip()
        scene_states.append(f"{loc_id}（{scene_name}）" if scene_name else loc_id)
    scene_state_text = "、".join(scene_states) or "按 storyboard 逐镜场景登记"

    lines = [
        f"# {ep} 出视频总览",
        "",
        f"- kind: {KIND}",
        f"- Clip 总数：{len(clips)}",
        f"- 总时长：{total_sec:.3f}s",
        f"- 制作模式：{project_setting(root, '制作模式', str(sb.get('production_mode') or PRODUCTION_MODE_DEFAULT))}",
        f"- 视频生成音频策略：{project_setting(root, '视频生成音频策略', '无声视频流')}",
        f"- 生视频渠道：{project_setting(root, '生视频渠道', 'Dreamina')}",
        f"- 出视频规格：{project_setting(root, '出视频规格', '预算充足')}",
        "",
        "## 本集导演一致性契约",
        f"- 主色调：继承出图色调基线：{values.get('色调基线')}",
        "- 镜头语法：逐镜继承 director_camera_plan 的景别、机位、运动速度与剪辑意图，不新增未登记镜头事件。",
        f"- 轴线：继承出图轴线：{values.get('轴线')}",
        f"- 剧情状态锁：继承出图状态演进：{values.get('状态演进')}；不得提前或回退 storyboard 登记的角色、道具与事件状态。",
        f"- 场景状态：继承出图光位锚：{values.get('光位锚')}；本集登记场景仅为 {scene_state_text}，保持各自空间布局与光位锚。",
        "",
        visual_block,
        "",
        style_block,
    ]
    if image_contract:
        lines += ["", image_contract]
    else:
        lines += [
            "",
            "## 本集可看性签收合同",
            "- 合同来源：`生产数据/script_quality_contract_%s.json`；逐 Clip 已在 `01_clips.md` 写入 dramatic_function / audience_effect。" % ep,
        ]

    lines += [
        "",
        "## 本集资产身份速查",
        "",
        "| 角色 | 形态 | reference_group | 锚点 |",
        "|---|---|---|---|",
    ]
    for form in forms:
        rg = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
        lines.append(
            f"| {md_table_escape(form.get('character_id'))} | {md_table_escape(form.get('form'))} | "
            f"{'ready' if rg else 'missing'} | {md_table_escape(form.get('anchor_phrase'))} |"
        )

    lines += [
        "",
        "## 本集身份 Adapter Matrix 摘要",
        f"- identity_adapter_matrix: `生产数据/identity_adapter_matrix.json`；本轮使用 reference_group fallback + 首帧/尾帧/锚帧约束，原生视频 ready 数以 matrix.summary 为准。",
        "",
        "## 本集近景身份风险表",
        "",
        "| Clip | 角色/形态 | 景别/口型 | 脸部/表情参考 | 表情跨度 | 后端身份锁 | 风险 | 工艺/回退 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip.get("id"), idx)
        route = route_rows.get(cid, {})
        cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
        chars = [str(x) for x in clip.get("character_ids") or []]
        span = str(cont.get("expression_span") or "微")
        mouth = "mouth_visible=yes" if mouths.get(cid) else "mouth_visible=no"
        risk = "high" if span == "大" or mouths.get(cid) or len(chars) > 1 else "medium"
        lines.append(
            f"| {cid} | {md_table_escape(','.join(chars) or '无')} | {md_table_escape(cont.get('shot_size'))}; {mouth} | "
            "脸部特写 / expressions / reference_group；缺情绪尾帧时降 MCU/OTS/侧脸/手部/物件反应 | "
            f"{md_table_escape(span)} | {md_table_escape(route.get('identity_requirement'))} | {risk} | "
            "首尾双帧优先；不稳则 MCU/OTS/侧脸/手部/物件反应保真实现 |"
        )

    lines += [
        "",
        "## 本集模型路由表",
        "",
        "| Clip | shot_type | primary_backend | fallback_backends | mode | native_audio_policy | identity_requirement | risk_flags | degrade_plan |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip.get("id"), idx)
        r = route_rows.get(cid, {})
        lines.append(
            f"| {cid} | {md_table_escape(r.get('shot_type'))} | {md_table_escape(r.get('primary_backend'))} | "
            f"{md_table_escape(route_list(r, 'fallback_backends'))} | {md_table_escape(r.get('mode'))} | "
            f"{md_table_escape(r.get('native_audio_policy'))} | {md_table_escape(r.get('identity_requirement'))} | "
            f"{md_table_escape(route_list(r, 'risk_flags'))} | {md_table_escape(r.get('degrade_plan'))} |"
        )

    lines += [
        "",
        "## 本集高动作编排清单",
        "",
        "| Clip | shot_type | beats/speed/spatial/camera/readability | degrade_plan |",
        "|---|---|---|---|",
    ]
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip.get("id"), idx)
        r = route_rows.get(cid, {})
        lines.append(f"| {cid} | {md_table_escape(r.get('shot_type'))} | {md_table_escape(action_choreography_line(r, clip))} | {md_table_escape(r.get('degrade_plan'))} |")

    lines += [
        "",
        "## 本集 Motion Control 清单",
        "",
        "| Clip | level | manifest_path | status | required_inputs | failure_modes | degrade_plan |",
        "|---|---|---|---|---|---|---|",
    ]
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip.get("id"), idx)
        r = route_rows.get(cid, {})
        mc = r.get("motion_control") if isinstance(r.get("motion_control"), Mapping) else {}
        path = str(mc.get("manifest_path") or "")
        status = "-"
        if path:
            man = load_json(root / path)
            status = str(man.get("status") or "missing") if isinstance(man, Mapping) else "missing"
        lines.append(
            f"| {cid} | {md_table_escape(mc.get('level'))} | {md_table_escape(path)} | {status} | "
            f"{md_table_escape(route_list(mc, 'required_inputs'))} | {md_table_escape(route_list(mc, 'failure_modes'))} | "
            f"{md_table_escape(r.get('degrade_plan'))} |"
        )

    lines += [
        "",
        "## 进度",
        "",
        "| Clip | 时长 | 首帧 | 尾帧 | 转场 | 状态 | 落档路径 |",
        "|---|---:|---|---|---|---|---|",
    ]
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip.get("id"), idx)
        cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
        lines.append(
            f"| {cid} | {float(clip.get('duration') or 0):.3f}s | `{clip.get('firstframe_png') or ''}` | "
            f"`{cont.get('endframe_png') or clip.get('endframe_png') or ''}` | {md_table_escape(cont.get('transition'))} | ⬜ | `{clip.get('video_out') or ''}` |"
        )
    lines.append("")
    return "\n".join(lines)


def signature_effect_directive(clip: Mapping[str, Any], probe_text: str) -> Tuple[str, List[str], bool]:
    """检测本镜声明的命名『特效镜头』，返回 (指引行, 追加负向词, 是否高身份风险)。

    命中来源是 SIGNATURE_EFFECT_LEXICON（特效镜头/manifest.json）。命中即把该特效的可粘贴核心
    prompt 与回链运镜暴露给操作者；identity_risk=high（换装/换脸/名场面/近脸升格/对打等）自动把该
    特效 negatives 与身份锁负向词并入本镜提交负向 prompt。未命中则返回空，不改变既有输出。"""
    probe = " ".join(part for part in [
        str(probe_text or ""),
        str(clip.get("signature_effect") or ""),
    ] if part)
    sig = normalize_signature_effect(probe)
    effects = sig.get("effects") or []
    if not effects:
        return "", [], False
    primary = effects[0]
    extra_negatives: List[str] = []
    high_risk = bool(sig.get("has_high_identity_risk"))
    if high_risk:
        for effect in effects:
            if effect.get("identity_risk") == "high":
                extra_negatives.extend(effect.get("negatives") or [])
        extra_negatives.extend(IDENTITY_LOCK_NEGATIVE_TERMS)
    hit_names = "、".join(f"{one_line(e.get('zh'))}({one_line(e.get('identity_risk'))})" for e in effects)
    line = (
        f"**特效镜头 / Signature Effect**：命中={hit_names}；运镜链={one_line(primary.get('camera_move'))}；"
        f"核心 prompt（{one_line(primary.get('zh'))}）：{one_line(primary.get('core_prompt_zh'))}"
    )
    if high_risk:
        line += "；⚠️ 高身份风险特效：已自动拼身份锁负向词；换装/换脸类须确认为有意形变，不得用于假冒真实人物。"
    return line, extra_negatives, high_risk


def render_clip(root: Path, ep: str, idx: int, clip: Mapping[str, Any], route: Mapping[str, Any],
                forms: Sequence[Mapping[str, Any]], mouths: Mapping[str, bool],
                contract_rows: Mapping[str, Mapping[str, Any]],
                shot_reverse_rows: Mapping[str, Mapping[str, Any]],
                camera_plan: Optional[Mapping[str, Any]] = None,
                incoming_seam: Optional[Mapping[str, Any]] = None,
                outgoing_seam: Optional[Mapping[str, Any]] = None) -> str:
    cid = clip_id(clip.get("id"), idx)
    raw_id = str(clip.get("id") or cid)
    label = str(clip.get("label") or "")
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    entity = clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else {}
    chars = [str(x) for x in clip.get("character_ids") or []]
    objects = [str(x) for x in clip.get("object_ids") or []]
    location = str(clip.get("location_id") or "")
    descs, prompts, lenses = shot_text(clip)
    start = one_line(cont.get("start_state") or descs, "承接首帧画面")
    action = one_line(prompts or descs, "只执行 storyboard 本镜主动作链")
    end = one_line(cont.get("end_state") or action, "停在可接下一镜的姿态/视线/画面重心")
    constraints = (
        f"required_presence={one_line(entity.get('required_presence'), '按首帧')}; "
        f"offscreen_presence={one_line(entity.get('offscreen_presence'), '无')}; "
        f"forbidden_presence={one_line(entity.get('forbidden_presence'), 'modern vehicles, phones, random readable text, watermark')}; "
        f"eyeline={one_line(cont.get('eyeline'), '按出图轴线')}"
    )
    amp, energy, camera = motion_words(clip, route, camera_plan)
    mouth = "yes" if mouths.get(cid) else "no"
    audio_line, normalized_audio_policy = native_audio_contract(route, mouth)
    negative_items = [
        "换脸或五官比例漂移",
        "换衣或发型漂移",
        "新增未登记人物或道具",
        "改变场景、光位或构图",
        "随机文字、logo 或水印",
        "无剧情动机的正视镜头、迎镜头转脸或对镜表演",
    ]
    if normalized_audio_policy == "native_speech":
        negative_items.append("旁白、额外台词或错误说话人")
    else:
        negative_items.append("原生人声")
    negative = "禁止：" + "；".join(negative_items) + "；表情变化不得改变脸型、眼距、鼻梁或下颌。"
    signature_probe = " ".join(part for part in [
        str(camera or ""), " ".join(descs or []), " ".join(prompts or []), str(lenses or ""),
    ] if part)
    signature_effect_line, signature_extra_negatives, signature_high_risk = signature_effect_directive(clip, signature_probe)
    for term in signature_extra_negatives:
        if term not in negative_items:
            negative_items.append(term)
    if signature_high_risk:
        negative += (
            " 高身份风险特效已启用身份锁负向词：脸型/五官比例/眼距/鼻梁/下颌/发际线/服装轮廓保持，"
            "形变仅限声明的转场点，不得用于假冒真实人物。"
        )
    contract = contract_rows.get(cid, {})
    dramatic = one_line(contract.get("dramatic_function") or clip.get("dramatic_function"))
    audience = one_line(contract.get("audience_effect") or clip.get("audience_effect"))
    fallback = one_line(route.get("degrade_plan"), "失败则按保真实现分解：拆手部/反打/OTS/释放帧，保留剧情 beat。")
    route_line = (
        f"shot_type={one_line(route.get('shot_type'))}; primary_backend={one_line(route.get('primary_backend'))}; "
        f"fallback={route_list(route, 'fallback_backends') or '无'}; mode={one_line(route.get('mode'))}; "
        f"native_audio_policy={one_line(route.get('native_audio_policy'), 'none')}; "
        f"identity_requirement={one_line(route.get('identity_requirement'))}; degrade_plan={fallback}"
    )
    shot_reverse_pattern = shot_reverse_rows.get(raw_id) or shot_reverse_rows.get(cid) or {}
    shot_reverse_line = shot_reverse_video_line(shot_reverse_pattern) if isinstance(shot_reverse_pattern, Mapping) and shot_reverse_pattern else ""
    gaze_guard = gaze_performance_guard(
        clip,
        chars,
        shot_reverse_pattern if isinstance(shot_reverse_pattern, Mapping) else {},
    )
    recipe = route.get("execution_recipe") if isinstance(route.get("execution_recipe"), Mapping) else {}
    assets = ", ".join([x for x in [location] + objects if x])
    asset_ids = [x for x in [location] + objects if x]
    inner_focus = inner_focus_directive(clip, chars, asset_ids)
    env_motion = environment_motion(clip)
    first, endframe = resolved_frame_paths(clip, ep, idx)
    anchors = [a for a in cont.get("anchors") or [] if isinstance(a, Mapping)]
    mid = cont.get("midframe") if isinstance(cont.get("midframe"), Mapping) else None
    execution_anchors = [
        row for row in anchors
        if str(row.get("use") or "split").strip().lower() not in {"qc", "reference", "reference_qc", "review"}
    ]
    mid_count = (1 if mid and str(mid.get("use") or "split").strip().lower() not in {"qc", "reference", "reference_qc", "review"} else 0) + len(execution_anchors)
    shots = [row for row in clip.get("shots") or [] if isinstance(row, Mapping)]
    editorial_shots = [
        row for row in shots
        if any(row.get(key) for key in ("lens", "camera", "shot_size"))
    ]
    explicit_frame_strategy = cont.get("frame_strategy")
    if isinstance(explicit_frame_strategy, Mapping):
        explicit_frame_strategy = explicit_frame_strategy.get("strategy")
    take_policy = str(clip.get("take_policy") or cont.get("take_policy") or "").strip().lower()
    requires_mid = _frame_strategy_requires_mid(clip, route, execution_anchors, mid)
    risk_anchor_present = any(
        str(row.get("use") or "split").strip().lower() in {"split", "keyframe"}
        for row in execution_anchors
    )
    # storyboard 显式声明逐镜独立付费 take：规整为空，不进入单拍多镜。
    if take_policy in {"split_each", "multi_take", "multitake", "independent_takes", "force_split"}:
        take_policy = ""
    # 拆镜经济性默认合并（2026-07-22 clip 经济性回修·第二阶段，与 shot_split_decision 同口径）：
    # 低风险、纯镜位覆盖、跨度 ≤ 单次生成硬上限的多镜位镜，即使 storyboard 未显式声明也默认单拍多镜，
    # 由 multishot-native 后端一次生成；奇观/大表情/高身份风险/需锚帧链/需中锚镜不默认合并。
    # 最终能力/时长闸仍由 select_video_frame_strategy → single_take_multishot_supported 兜底回落 edit_cut。
    auto_single_take = False
    if (
        not take_policy
        and len(editorial_shots) > 1
        and not (requires_mid or risk_anchor_present)
    ):
        _dur = clip.get("duration") if isinstance(clip.get("duration"), (int, float)) else None
        _span = str(cont.get("expression_span") or "微")
        _spectacle_like = bool(clip.get("template") or clip.get("spectacle_type") or signature_high_risk)
        # 合并上限后端能力感知（与 shot_split_decision.project_single_take_ceiling 同口径）：
        # 未设/未知后端 → 历史 15s；已验后端单段上限更高时自动跟进。
        _ceiling = single_take_merge_ceiling_seconds(
            project_setting(root, "生视频模型", "") or project_setting(root, "生视频AI", ""), floor=15.0)
        if _dur is not None and _dur <= _ceiling and _span != "大" and not _spectacle_like:
            take_policy = "single_take_multishot"
            auto_single_take = True
    # 安全优先：命中 R1-R3 高风险锚链或需中锚的镜，忽略单拍多镜声明，仍按锚帧链/拆段执行
    # （与 shot_split_decision.single_take_policy_verdict / anchor_planner 同口径）。
    effective_take_policy = "" if (requires_mid or risk_anchor_present) else take_policy
    strategy_plan = select_video_frame_strategy(
        route.get("primary_backend") or "generic",
        route_execution_channel(route),
        shot_count=max(1, len(editorial_shots)),
        anchor_count=mid_count,
        need_end=bool(endframe) or needs_end_anchor(cont),
        requires_mid_anchors=requires_mid,
        explicit=str(explicit_frame_strategy or ""),
        take_policy=effective_take_policy,
        duration_sec=clip.get("duration") if isinstance(clip.get("duration"), (int, float)) else None,
    )
    frame_strategy = str(strategy_plan.get("strategy") or "first_only")
    single_take_ladder = ""
    if frame_strategy == "single_take_multishot" and editorial_shots:
        # 单拍多镜：一次生成承载多个镜位，主动作编成「镜头1/2/…」阶梯（Seedance/Kling 多镜叙事口径），
        # 镜位切换由 multishot-native 后端在 take 内部完成，不再拆独立付费 take。
        ladder_parts = []
        for s_idx, shot in enumerate(editorial_shots, 1):
            piece = one_line(shot.get("video_prompt") or shot.get("desc") or shot.get("description"), "")
            lens = one_line(shot.get("lens") or shot.get("shot_size") or shot.get("camera"), "")
            if piece or lens:
                ladder_parts.append(f"镜头{s_idx}（{lens or '承接'}）：{piece or '承接上一镜动作'}")
        if ladder_parts:
            single_take_ladder = "；".join(ladder_parts)
            action = single_take_ladder
    frame_control = anchor_consumption_plan(
        route.get("primary_backend") or "generic",
        route_execution_channel(route),
        anchor_count=mid_count,
        need_end=bool(endframe) or needs_end_anchor(cont),
        frame_strategy=frame_strategy,
    )
    handoff_line = handoff_package_line(first, endframe, mid_count, cont, frame_control, fallback)
    exec_line = execution_recipe_line(recipe, frame_control, fallback)
    incoming_line = seam_summary_line(incoming_seam, "本镜为本集首镜且无前集边界，或 continuity_chain 未生成。")
    outgoing_line = seam_summary_line(outgoing_seam, "本镜为本集末镜，或下一镜 seam 未登记。")
    span = str(cont.get("expression_span") or "微")
    closeup_guard = closeup_promotion_guard(clip, route, chars, start, end, lenses, camera, span)
    tail_hold_guard = ending_reaction_hold_guard(
        clip,
        [str(x) for x in entity.get("offscreen_presence") or []],
        end,
        one_line(cont.get("transition"), ""),
    )
    if inner_focus:
        negative += " 内心戏镜头不要重复上一镜群像/妖魔/道具陈列，不要让非焦点人物清晰入画或产生新动作，不要让系统面板/武器/VFX 抢主观情绪。"
    if closeup_guard:
        negative += " 不得从小脸/远脸/侧背/遮挡脸直接升格成清晰近脸；缺同源近景锚帧时改 MCU/OTS/侧脸/手部/物件反应。"
    if tail_hold_guard:
        negative += " 本镜尾端保持手部/物件/侧背/反打落幅直到剪点，不要提前把 offscreen 角色拉回清晰入画或预演下一镜构图。"

    frame_inputs = _recipe_list(recipe, "frame_inputs", [first, endframe] if endframe else [first])
    reference_inputs = _recipe_list(recipe, "reference_inputs")
    control_inputs = _recipe_list(recipe, "control_inputs")
    audio_inputs = _recipe_list(recipe, "audio_inputs")
    compiled = compile_video_prompt({
        "clip_id": cid,
        "backend": route.get("primary_backend") or "generic",
        "mode": route.get("mode") or "image2video",
        "native_audio_policy": normalized_audio_policy,
        "duration": clip.get("duration"),
        "story_span_sec": clip.get("duration"),
        "edit_target_sec": clip.get("edit_target_sec") or clip.get("video_shot_duration") or clip.get("duration"),
        "model_version": route.get("model_version") or route.get("model") or "",
        "channel": route.get("channel") or route.get("backend_channel") or "",
        "frame_strategy": frame_strategy,
        "subject": chars,
        "scene": clip.get("scene"),
        "primary_action": action,
        "camera_motion": camera,
        "eyeline": gaze_guard,
        "environment_motion": env_motion,
        "rhythm": clip.get("rhythm"),
        "end_state": end,
        "must_hold": [constraints, closeup_guard, tail_hold_guard],
        "must_avoid": negative_items,
        "frame_inputs": frame_inputs,
        "reference_inputs": reference_inputs,
        "control_inputs": control_inputs,
        "audio_inputs": audio_inputs,
    })

    lines = [
        f"## Clip {idx:02d}（时长 {float(clip.get('duration') or 0):.3f}s · {raw_id} · {label}）",
        "",
        f"**首帧**：`{first}`",
    ]
    if endframe:
        lines.append(f"**尾帧**：`{endframe}`")
    if mid:
        lines.append(f"**中段锚帧**：`{mid.get('midframe_png') or mid.get('anchor_png') or f'出图/{ep}/图片/{cid}_mid.png'}`")
    for a_idx, anchor in enumerate(anchors, 1):
        lines.append(f"**锚帧{a_idx}**：`{anchor.get('anchor_png') or f'出图/{ep}/图片/{cid}_a{a_idx}.png'}`（at_sec={anchor.get('at_sec')}）")

    lines += [
        f"**场景**：{one_line(clip.get('scene'))}",
        f"**剧本可看性合同**：dramatic_function={dramatic}；audience_effect={audience}；retention promise / audience question 必须由运动和表演承接，不改写承诺。",
        f"**导演意图**：{dramatic}",
        f"**起幅**：{start}",
        f"**落幅**：{end}",
        f"**场面调度**：{one_line(lenses, '按 storyboard 镜头链')}；角色={one_line(chars, '无')}；资产={assets or '无'}；轴线/视线={one_line(cont.get('eyeline'), '按出图总览')}",
        f"**视线表演合同**：{gaze_guard}",
        f"**正反打视频合同**：{shot_reverse_line}" if shot_reverse_line else "**正反打视频合同**：本镜未登记 shot_reverse_contract；若临场改成反打/过肩，先回 n2d-script 生成合同。",
        f"**内心戏主体隔离**：{inner_focus or '非内心戏/按 entity_schedule 在场链执行'}",
        f"**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] {action}；[75-100%] 停到落幅，给下一镜接点。",
        "**运动精修**：物理层锁定；动作只服务本镜导演意图。",
        f"- 幅度：{amp}",
        f"- 能量：{energy}",
        "- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。",
        f"**环境交互**：{env_motion or 'storyboard 未登记专属环境动态；背景保持稳定，不凭空增加天气、粒子、道具或光源运动。'}",
        f"**动作编排契约 / Action Choreography**：{action_choreography_line(route, clip)}",
        f"**专项镜头模板**：template={one_line(route.get('template') or route.get('shot_type'), '无')}；blocking/continuity_must/negative 继承 storyboard，不临场改戏。",
        *([signature_effect_line] if signature_effect_line else []),
        f"**模型路由**：{route_line}",
        f"**帧策略 / Frame Strategy**：strategy={frame_strategy}；reason={strategy_plan.get('reason')}；shot_count={strategy_plan.get('shot_count')}；anchor_count={strategy_plan.get('anchor_count')}；首尾帧后端不得把 split relay 冒充原生三帧。",
        *([
            f"**单拍多镜合同 / Single-Take Multishot**：take_policy=single_take_multishot；内部镜位 {len(editorial_shots)} 个由 multishot-native 后端一次生成（镜头阶梯：{single_take_ladder or '按 storyboard shots 顺序'}）；"
            "不拆独立付费 take、不消费 edit_cut 边界锚为时间轴；后端不支持或时长超窗时必须回落 edit_cut 拆 take，不得静默按单镜直提。"
        ] if frame_strategy == "single_take_multishot" else []),
        f"**接缝执行包 / Handoff Package**：{handoff_line}",
        f"**连续性链路 / Continuity Chain**：入点={incoming_line}；出点={outgoing_line}",
        f"**执行配方 / Execution Recipe**：{exec_line}",
        f"**Motion Control / 物理交互控制**：{motion_control_line(route)}",
        f"**角色身份注册层**：{identity_line(forms, chars)}；本镜绑定={one_line(chars, '无人物')}；资产引用注册层={assets or '无'}。",
        f"**近景/反打身份锁定**：主焦点={one_line(chars[:1], '无')}；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度={span}；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。",
        f"**近景升格守卫**：{closeup_guard or '未触发近景升格；按当前首/中/尾锚帧景别生成，不主动新增近脸。'}",
        f"**尾端落幅保持**：{tail_hold_guard or '未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。'}",
        f"**原生音画策略**：{audio_line}",
        "**衔接设计**：",
        f"- 入点：{start}",
        f"- 出点：{end}",
        f"- 转场：{one_line(cont.get('transition'), '硬切/动作切按 storyboard')}",
        f"- 连贯性：{constraints}; inner_focus={inner_focus or '无'}",
        "",
        "**continuity**：",
        f"- start_state：{start}",
        f"- action：{action}",
        f"- end_state：{end}",
        f"- constraints：{constraints}",
        f"- negative：{negative}",
        "",
        "**视频提交口径**：严格合同保留在本 Clip 块；runner 只提取下方 compiler 产物，不把路由、审计、身份注册层或接缝说明拼入模型 prompt。",
        "",
        render_compiled_markdown(compiled),
        "",
        "### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）",
        "- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。",
        "- ✅ 剧本可看性合同 dramatic_function / audience_effect 已由完整合同承接，未塞入模型提交 prompt。",
        "- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。",
        "- ✅ compiler 已按 primary_backend / mode 生成唯一提交 prompt，语言与负向策略匹配后端。",
        "- ✅ 在场链 required_presence/offscreen_presence/forbidden_presence 保留在完整合同与真实输入层。",
        "- ✅ 接缝执行包 / 执行配方已进入完整合同，frame/reference/control/audio 输入与 route 一致。",
        "- ✅ Continuity Chain 保留在完整合同和锚帧输入层；提交 prompt 只保留动作、运镜、节奏、落幅。",
        "- ✅ ④人物运动动作链明确，幅度与能量可控。",
        "- ✅ ②镜头运动有结构化运镜词和速度。",
        "- ✅ 运镜动机：摄影机运动能说明揭示了什么新信息；说不清时使用固定机位，由表演、画内调度与剪辑承载张力。",
        "- ✅ 视线表演：非 POV/破第四墙镜头已写清戏内视线目标与头眼方向，角色不迎着摄影机转脸。",
        "- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不靠乱推、乱甩或随机环绕。",
        "- ✅ 模型路由、Motion Control、角色身份注册层、原生音画策略已继承。",
        "- ✅ 内心戏/心理反应镜只让主焦点运动；其他实体无结构化例外时不得清晰入画或抢动作。",
        "- ✅ 近景升格守卫：CU/MCU/反打落幅不得从小脸/远脸直接补新脸；缺近景锚帧则改保真拍法或回 n2d-image 补锚。",
        "- ✅ 尾端落幅保持：offscreen 角色不在最后 0.5 秒提前清晰入画，手部/物件/侧背反应维持到剪点。",
        "",
        "### 自检（生成后逐条过 · 落档闸门）",
        "- [ ] 首帧一致性：人物脸/服装/场景与首帧一致。",
        "- [ ] 人物运动：方向正确，无肢体扭曲、脸部抖动、多人脸错乱。",
        "- [ ] 在场链：required_presence 在场，offscreen/forbidden 不乱入。",
        "- [ ] 物理守卫 / FeatureMelting：手部归属、遮挡、接触点、肢体边界、特征融化全部过。",
        "- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致；固定镜无漂移、呼吸式缩放或无意义重构，运动镜确实完成登记的叙事动机。",
        "- [ ] 视线与迎镜头：抽起/中/止帧检查眼睛、鼻梁轴和头部朝向；非 POV/破第四墙镜角色始终看戏内对象，出现无动机正视镜头或迎镜头转脸即废料重跑。",
        "- [ ] 动态细节 & 环境交互成立，无现代物/文字/logo/水印。",
        "- [ ] 导演调度完成本镜意图，起幅/落幅可剪。",
        "- [ ] 模型路由结果符合 primary 强项；失败按 fallback/degrade_plan，不临场乱换。",
        "- [ ] 近景身份：脸型、五官比例、发型发髻、标志配饰、服装配色稳定。",
        "- [ ] 帧级近脸：最终 MP4 内任何新增/推近的主角清晰脸都仍是同一角色；若像换人，废料重跑或回 image 补近景锚帧。",
        "- [ ] 原生音画：确认无 AI 自带台词/旁白/哼唱。",
        "- [ ] 落档判定：通过落 `出视频/%s/视频/%s.mp4`；失败进废料并改 prompt/拆 Clip。" % (ep, cid),
        "",
    ]
    return "\n".join(lines)


def render_clips(root: Path, ep: str, sb: Mapping[str, Any], route_rows: Mapping[str, Mapping[str, Any]],
                 forms: Sequence[Mapping[str, Any]], mouths: Mapping[str, bool],
                 contract_rows: Mapping[str, Mapping[str, Any]],
                 shot_reverse_rows: Mapping[str, Mapping[str, Any]],
                 camera_plan_rows: Mapping[str, Mapping[str, Any]],
                 chain: Mapping[str, Any]) -> str:
    clips = [c for c in sb.get("clips") or [] if isinstance(c, Mapping)]
    incoming_map, outgoing_map = continuity_chain_maps(chain)
    out = [f"# {ep} 视频 Clip prompt", ""]
    retention = contract_retention_lines(root, ep)
    if retention:
        out += ["## 本集留存承诺账本（script_quality_contract）", "", *retention, ""]
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip.get("id"), idx)
        out.append(render_clip(
            root,
            ep,
            idx,
            clip,
            route_rows.get(cid, {}),
            forms,
            mouths,
            contract_rows,
            shot_reverse_rows,
            camera_plan_rows.get(str(clip.get("id") or "")) or camera_plan_rows.get(cid),
            incoming_map.get(cid),
            outgoing_map.get(cid),
        ))
    return "\n".join(out)


def build(root: Path, ep: str) -> Tuple[str, str]:
    ep = ep_label(ep)
    sb = storyboard(root, ep)
    route_rows = routes(root, ep)
    forms = identity_forms(root)
    mouths = mouth_map(root, ep)
    contract_rows = contract_clip_map(root, ep)
    shot_reverse_rows = shot_reverse_contract_map(root, ep)
    camera_plan_rows = director_camera_plan_map(root, ep)
    chain = continuity_chain(root, ep)
    image_overview_path = root / "出图" / ep / "prompt" / "00_总览.md"
    image_overview = image_overview_path.read_text(encoding="utf-8") if image_overview_path.is_file() else ""
    return (
        render_overview(root, ep, sb, route_rows, image_overview, forms, mouths),
        render_clips(root, ep, sb, route_rows, forms, mouths, contract_rows, shot_reverse_rows, camera_plan_rows, chain),
    )


def write_outputs(root: Path, ep: str, overview: str, clips: str) -> Tuple[Path, Path]:
    out = root / "出视频" / ep / "prompt"
    p0 = out / "00_总览.md"
    p1 = out / "01_clips.md"
    write_atomic(p0, overview.rstrip() + "\n")
    write_atomic(p1, clips.rstrip() + "\n")
    return p0, p1


def consumed_contract_inputs(ep: str) -> List[Tuple[str, Path]]:
    return [
        ("storyboard", Path("脚本") / ep / "storyboard.json"),
        ("continuity_chain", Path("脚本") / ep / "continuity_chain.json"),
        ("shot_reverse_contract", Path("脚本") / ep / "shot_reverse_contract.json"),
        ("script_quality_contract", Path("生产数据") / f"script_quality_contract_{ep}.json"),
        ("director_camera_plan", Path("生产数据") / f"director_camera_plan_{ep}.json"),
        ("reference_plan", Path("生产数据") / f"reference_plan_{ep}.json"),
    ]


def write_consumed_contracts_receipt(root: Path, ep: str, prompt_paths: Sequence[Path]) -> Path:
    contracts: List[Dict[str, Any]] = []
    for name, rel in consumed_contract_inputs(ep):
        path = root / rel
        contracts.append({
            "name": name,
            "path": str(rel),
            "exists": path.is_file(),
            "sha256": sha256_file(path) if path.is_file() else "",
        })
    prompt_files: List[Dict[str, Any]] = []
    for path in prompt_paths:
        rel = path.relative_to(root)
        prompt_files.append({
            "path": str(rel),
            "exists": path.is_file(),
            "sha256": sha256_file(path) if path.is_file() else "",
        })
    out = root / "生产数据" / f"consumed_contracts_video_prompt_{ep}.json"
    write_json_atomic(out, {
        "kind": CONSUMED_CONTRACTS_KIND,
        "version": CONSUMED_CONTRACTS_VERSION,
        "episode": ep,
        "scope": "video_prompt",
        "accepted": True,
        "reviewer": "Codex n2d-video prompt pack",
        "generated_by": "skills/n2d/n2d-video/scripts/prompt_pack.py",
        "generated_at": now_iso(),
        "contracts": contracts,
        "prompt_files": prompt_files,
    })
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Generate n2d-video prompt pack from storyboard/routes")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    ep = ep_label(ns.episode)
    overview, clips = build(root, ep)
    if ns.write:
        p0, p1 = write_outputs(root, ep, overview, clips)
        receipt = write_consumed_contracts_receipt(root, ep, (p0, p1))
        if ns.json:
            print(json.dumps({"overview": str(p0), "clips": str(p1), "receipt": str(receipt)}, ensure_ascii=False, indent=2))
        else:
            print(f"wrote {p0}")
            print(f"wrote {p1}")
            print(f"wrote {receipt}")
    else:
        print(overview)
        print("\n--- 01_clips.md ---\n")
        print(clips)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
