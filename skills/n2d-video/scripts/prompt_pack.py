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
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

KIND = "n2d_video_prompt_pack"
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


def form_for_char(forms: Sequence[Mapping[str, Any]], char_id: str) -> Optional[Mapping[str, Any]]:
    for form in forms:
        if str(form.get("character_id") or "") == char_id:
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
                f"{char}/{form.get('form') or '默认形态'}：reference_group={ref_ready}；"
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


def motion_words(clip: Mapping[str, Any], route: Mapping[str, Any]) -> Tuple[str, str, str]:
    rhythm = str(clip.get("rhythm") or "")
    shot_type = str(route.get("shot_type") or "")
    if any(x in shot_type for x in ("chase", "mount", "flight", "vehicle")) or any(x in rhythm for x in ("马队", "追", "压近")):
        return "中等；背景/前景视差动，主体不变形", "匀速压近；关键节点短暂停顿", "缓慢跟拍或微推，保持官道轴线"
    if any(x in shot_type for x in ("multi_character", "dialogue")):
        return "小到中；人物槽位不漂移", "克制；表情和视线先动，身体后动", "固定或缓慢推近"
    if any(x in rhythm for x in ("钩子", "爽点", "尾")):
        return "小幅；高光点只给一次明确动作", "蓄力后定住", "缓慢推近，尾端定格"
    return "小幅；只执行本镜主动作链", "克制匀速", "固定或极缓推近"


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
    return (
        f"first_frame={first or '无'}；end_frame={endframe or '无'}；midframes={mid_count}；"
        f"need_endframe={cont.get('need_endframe')}；transition={one_line(cont.get('transition'), '按 storyboard')}；"
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

    lines = [
        f"# {ep} 出视频总览",
        "",
        f"- kind: {KIND}",
        f"- Clip 总数：{len(clips)}",
        f"- 总时长：{total_sec:.3f}s",
        f"- 制作模式：{project_setting(root, '制作模式', str(sb.get('production_mode') or '先出视频后配音'))}",
        f"- 视频生成音频策略：{project_setting(root, '视频生成音频策略', '无声视频流')}",
        f"- 生视频渠道：{project_setting(root, '生视频渠道', 'Dreamina')}",
        f"- 出视频规格：{project_setting(root, '出视频规格', '预算充足')}",
        "",
        "## 本集导演一致性契约",
        f"- 主色调：继承出图色调基线：{values.get('色调基线')}",
        "- 镜头语法：冷开/欠命账用固定和极缓推；换装/身份爽点用克制推近；马队/跪求用前后景压迫与反打；尾钩用定格和近景压住选择困局。",
        f"- 轴线：继承出图轴线：{values.get('轴线')}",
        f"- 剧情状态锁：继承出图状态演进：{values.get('状态演进')}；不提前画狼妖完整形态，不提前把救村选择拍成已答应。",
        f"- 场景状态：继承出图光位锚：{values.get('光位锚')}；LOC_01 浅坑/尸场/低雾保持，LOC_02 官道深处、火把侧光、马队画右中景保持。",
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


def render_clip(root: Path, ep: str, idx: int, clip: Mapping[str, Any], route: Mapping[str, Any],
                forms: Sequence[Mapping[str, Any]], mouths: Mapping[str, bool],
                contract_rows: Mapping[str, Mapping[str, Any]]) -> str:
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
    negative = "不要换脸、不要换衣、不要新增人物、不要改变场景/光位/发型、不要生成文字/logo/水印、不要生成原生人声、不要随表情改变脸型/五官比例/眼距/鼻梁/下颌。"
    amp, energy, camera = motion_words(clip, route)
    mouth = "yes" if mouths.get(cid) else "no"
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
    recipe = route.get("execution_recipe") if isinstance(route.get("execution_recipe"), Mapping) else {}
    assets = ", ".join([x for x in [location] + objects if x])
    asset_ids = [x for x in [location] + objects if x]
    inner_focus = inner_focus_directive(clip, chars, asset_ids)
    frame_control = route.get("anchor_consumption") if isinstance(route.get("anchor_consumption"), Mapping) else {}
    first = str(clip.get("firstframe_png") or f"出图/{ep}/图片/{cid}.png")
    endframe = str(cont.get("endframe_png") or clip.get("endframe_png") or "")
    anchors = [a for a in cont.get("anchors") or [] if isinstance(a, Mapping)]
    mid = cont.get("midframe") if isinstance(cont.get("midframe"), Mapping) else None
    mid_count = (1 if mid else 0) + len(anchors)
    handoff_line = handoff_package_line(first, endframe, mid_count, cont, frame_control, fallback)
    exec_line = execution_recipe_line(recipe, frame_control, fallback)
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
        f"**内心戏主体隔离**：{inner_focus or '非内心戏/按 entity_schedule 在场链执行'}",
        f"**表演节拍**：[0-30%] 承接首帧并建立状态；[30-75%] {action}；[75-100%] 停到落幅，给下一镜接点。",
        "**运动精修**：物理层锁定；动作只服务本镜导演意图。",
        f"- 幅度：{amp}",
        f"- 能量：{energy}",
        "- 身体守卫：脸型/五官比例/发型发髻/服装轮廓保持；手部归属和遮挡层级清楚；多人槽位不互换。",
        "**环境交互**：冷月/火把光影按动作产生轻微阴影变化；土粒、低雾、衣袂、火把烟与马队尘土只做物理反馈，不新增现代物或随机文字。",
        f"**动作编排契约 / Action Choreography**：{action_choreography_line(route, clip)}",
        f"**专项镜头模板**：template={one_line(route.get('template') or route.get('shot_type'), '无')}；blocking/continuity_must/negative 继承 storyboard，不临场改戏。",
        f"**模型路由**：{route_line}",
        f"**接缝执行包 / Handoff Package**：{handoff_line}",
        f"**执行配方 / Execution Recipe**：{exec_line}",
        f"**Motion Control / 物理交互控制**：{motion_control_line(route)}",
        f"**角色身份注册层**：{identity_line(forms, chars)}；本镜绑定={one_line(chars, '无人物')}；资产引用注册层={assets or '无'}。",
        f"**近景/反打身份锁定**：主焦点={one_line(chars[:1], '无')}；脸部特写/表情参考/expressions 优先；表情锚=起幅情绪→落幅情绪；表情幅度={span}；锁脸不锁情：只动眉眼嘴角，脸型/五官比例/眼距/鼻梁/下颌/发际线/痣疤保持；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。",
        f"**近景升格守卫**：{closeup_guard or '未触发近景升格；按当前首/中/尾锚帧景别生成，不主动新增近脸。'}",
        f"**尾端落幅保持**：{tail_hold_guard or '未触发；按 continuity.end_state 自然停住，不提前预演下一 Clip。'}",
        f"**原生音画策略**：audio_intent=none; risk=low; mouth_visible={mouth}; speech_policy=no_native_speech; compose_policy=丢弃; review=生成后确认无原生人声。",
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
        "**视频提交口径**：`首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止`。",
        "",
        "### 视频 prompt（中文，目标=即梦/可灵/Seedance）",
        "```",
        "continuity:",
        f"  start_state: {start}",
        f"  action: {action}",
        f"  end_state: {end}",
        f"  constraints: {constraints}",
        f"  negative: {negative}",
        f"剧本可看性合同：dramatic_function={dramatic}; audience_effect={audience}; 本镜承接留存承诺和观众问题处理，运动与表演只强化不改写；",
        f"导演意图：{dramatic};",
        f"起幅：{start};",
        f"落幅：{end};",
        f"场面调度：{one_line(lenses, '按 storyboard 镜头链')}；角色槽位={one_line(chars, '无')}；资产ID={assets or '无'}；",
        f"内心戏主体隔离：{inner_focus or '非内心戏/按在场链执行'}；",
        f"表演节拍：[0-30%] 承接首帧；[30-75%] {action}；[75-100%] {end};",
        f"运动精修约束：幅度={amp}；能量={energy}；身体守卫=脸型五官比例发型发髻服装轮廓保持，手部归属清楚，遮挡不穿模；",
        "环境交互约束：冷月与火把光影轻微随动，低雾/尘土/衣袂/火把烟提供动态反馈，不改变首帧设定；",
        f"动作编排约束：{action_choreography_line(route, clip)}；",
        f"专项模板约束：template={one_line(route.get('template') or route.get('shot_type'), '无')}；按 storyboard template_contract 执行；",
        f"模型路由约束：读取 video_model_routes.json；本镜 primary_backend={one_line(route.get('primary_backend'))}，fallback={route_list(route, 'fallback_backends') or '无'}，mode={one_line(route.get('mode'))}，native_audio_policy={one_line(route.get('native_audio_policy'), 'none')}，identity_requirement={one_line(route.get('identity_requirement'))}；失败按 degrade_plan={fallback}；",
        f"接缝执行包：{handoff_line}；",
        f"执行配方约束：{exec_line}；真正提交给后端时必须把 frame_inputs/reference_inputs/control_inputs/audio_inputs 按该配方组织，不得只提交裸文本 prompt；",
        f"物理交互约束：读取 motion_control_manifest.json；{motion_control_line(route)}；degrade_only 时不直接生成全身复杂接触或长连续高速动作，按保真实现分解执行，避免 FeatureMelting/特征融化；",
        f"身份锁定约束：{identity_line(forms, chars)}；锁脸型/五官比例/发型发髻/标志配饰/服装配色，reference_group 和首帧为身份真值；",
        f"近景身份锁定约束：表情锚起→止，表情幅度={span}；锁脸不锁情；无原生锁时限制低幅表情和小角度转头，必要时 MCU/OTS/侧脸/手部/物件反应保真实现；",
        f"在场链约束：{constraints}；只允许 required_presence/entity_schedule/首帧已登记的人物、物件、场景和特效进入清晰画面；offscreen_presence 只能作为画外声音、影子、侧背/手部/物件反应承接，不得清晰入画抢动作；forbidden_presence 完全不出现；",
        f"近景升格守卫：{closeup_guard or '不主动把小脸/远脸升格成近脸；按锚帧景别保持。'}；",
        f"尾端落幅保持：{tail_hold_guard or '按 continuity.end_state 停住，不提前预演下一 Clip。'}；",
        "原生音画约束：默认禁止原生人声；audio_intent=none；speech_policy=no_native_speech；compose_policy=丢弃；",
        "首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心；不重定视觉设定；",
        f"人物运动：{action}；表情只动面部肌肉，脸型五官比例不变；",
        f"镜头运动：{camera}；",
        f"情绪节奏：[0-30%] 克制承接；[30-75%] 张力推进；[75-100%] 定住，服务{one_line(clip.get('rhythm'), '本镜节奏')}；",
        "动态细节：低雾缓流、衣袂微动、火把烟或土粒细动，与人物动作产生轻微物理反馈；",
        f"衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints 和在场链约束，避开 continuity.negative，按{one_line(cont.get('transition'), '转场')}服务下一镜；",
        "禁止：不要换脸、不要换衣、不要新增人物/道具、不要改变场景/光位/发型、不要生成文字/logo/水印，非 native_speech 镜不要生成原生人声；内心戏镜头不得重复上一镜群像/妖魔/道具陈列；",
        "声音约束：无对白、无旁白、不要生成原生人声；声音只作为后期 n2d-compose 的剪辑意图。",
        "```",
        "",
        "### 视频 prompt（英文，目标=安全兜底/Veo/海外）",
        "```",
        f"continuity: start from {start}; perform only {action}; end on {end}; preserve {constraints}; follow required_presence/offscreen_presence/forbidden_presence exactly; avoid face drift, costume changes, unregistered characters or props, text, logos, watermarks, and generated native voice.",
        f"inner-focus isolation: {inner_focus or 'not an inner-focus shot; follow entity schedule.'}",
        f"director intent: {dramatic}; audience effect: {audience}.",
        f"character motion: {action}; camera motion: {camera}; dynamic detail: cold moonlight, torch smoke, dust, fog, and fabric move subtly with the action.",
        "close-up identity lock: preserve face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, signature accessories, and costume palette; lock face not emotion; downgrade unstable close-ups to MCU, OTS, side-face, hand or object reaction shots.",
        "close-up promotion guard: do not turn a small, distant, side/back, occluded, or non-primary anchor face into a clear close-up face unless a same-source close-up anchor/expression reference has passed full image QC.",
        f"ending reaction hold: {tail_hold_guard or 'hold the continuity.end_state until the cut and do not preview the next clip early.'}",
        "native audio policy: audio_intent=none; speech_policy=no_native_speech; compose_policy=discard.",
        "```",
        "",
        "### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）",
        "- ✅ 首帧 PNG 已落档并与 Clip 编号匹配。",
        "- ✅ 剧本可看性合同 dramatic_function / audience_effect 已进入 prompt。",
        "- ✅ 导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全。",
        "- ✅ 中文 prompt 已写首帧保持 / 人物运动 / 镜头运动 / 情绪节奏 / 禁止。",
        "- ✅ 在场链约束 required_presence/offscreen_presence/forbidden_presence 已进入中文 prompt。",
        "- ✅ 接缝执行包 / 执行配方约束已进入中文 prompt，frame_inputs/reference_inputs/control_inputs/audio_inputs 与 route 一致。",
        "- ✅ ④人物运动动作链明确，幅度与能量可控。",
        "- ✅ ②镜头运动有结构化运镜词和速度。",
        "- ✅ ⑦张力与节奏匹配，留白/爽点/压迫不乱甩。",
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
        "- [ ] 镜头运动：推/拉/跟/固定等与 prompt 一致。",
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
                 contract_rows: Mapping[str, Mapping[str, Any]]) -> str:
    clips = [c for c in sb.get("clips") or [] if isinstance(c, Mapping)]
    out = [f"# {ep} 视频 Clip prompt", ""]
    retention = contract_retention_lines(root, ep)
    if retention:
        out += ["## 本集留存承诺账本（script_quality_contract）", "", *retention, ""]
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip.get("id"), idx)
        out.append(render_clip(root, ep, idx, clip, route_rows.get(cid, {}), forms, mouths, contract_rows))
    return "\n".join(out)


def build(root: Path, ep: str) -> Tuple[str, str]:
    ep = ep_label(ep)
    sb = storyboard(root, ep)
    route_rows = routes(root, ep)
    forms = identity_forms(root)
    mouths = mouth_map(root, ep)
    contract_rows = contract_clip_map(root, ep)
    image_overview_path = root / "出图" / ep / "prompt" / "00_总览.md"
    image_overview = image_overview_path.read_text(encoding="utf-8") if image_overview_path.is_file() else ""
    return (
        render_overview(root, ep, sb, route_rows, image_overview, forms, mouths),
        render_clips(root, ep, sb, route_rows, forms, mouths, contract_rows),
    )


def write_outputs(root: Path, ep: str, overview: str, clips: str) -> Tuple[Path, Path]:
    out = root / "出视频" / ep / "prompt"
    p0 = out / "00_总览.md"
    p1 = out / "01_clips.md"
    write_atomic(p0, overview.rstrip() + "\n")
    write_atomic(p1, clips.rstrip() + "\n")
    return p0, p1


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
        if ns.json:
            print(json.dumps({"overview": str(p0), "clips": str(p1)}, ensure_ascii=False, indent=2))
        else:
            print(f"wrote {p0}")
            print(f"wrote {p1}")
    else:
        print(overview)
        print("\n--- 01_clips.md ---\n")
        print(clips)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
