#!/usr/bin/env python3
"""Director camera-language audit for n2d storyboard clips.

Reads `脚本/第N集/storyboard.json` and emits a production sidecar:
`生产数据/director_camera_plan_第N集.json/.md`.

The sidecar is intentionally advisory: it turns story rhythm and shot grammar
into copyable image/video prompt injections without mutating the storyboard.
Use `--strict` only when a workflow wants missing/unstructured camera language
to fail fast before expensive image/video generation.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
N2D_LIB = REPO_ROOT / "skills" / "n2d" / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))

from n2d_const import CAMERA_MOVE_LEXICON, STATIC_CAMERA_WORDS  # noqa: E402
from n2d_logic import normalize_camera_move  # noqa: E402
from n2d_settings import get_setting  # noqa: E402
import video_backend_adapter  # noqa: E402


PEAK_WORDS = (
    "爽点", "爆点", "高潮", "高光", "反转", "逆转", "翻盘", "反杀", "逆袭", "打脸",
    "觉醒", "揭真相", "身份曝光", "威压", "climax", "reveal", "payoff",
)
SETUP_WORDS = ("铺垫", "潜伏", "试探", "压迫", "悬疑", "留白", "克制", "quiet", "suspense")
ACTION_WORDS = (
    "打斗", "追逐", "奔跑", "飞行", "御剑", "御兽", "马车", "飞舟", "载具", "爆发",
    "法术", "武技", "冲刺", "闪避", "战斗", "chase", "fight", "flight", "action",
)
DIALOGUE_WORDS = ("对话", "反打", "过肩", "dialogue", "shot_reverse", "talk", "审讯", "谈判")
RELEASE_WORDS = ("释放", "孤独", "失落", "退场", "结尾", "余韵", "aftermath", "release")
SCREEN_WORDS = ("系统面板", "screen_insert", "system_panel", "面板", "光幕", "字幕卡")
OVERACTIVE_WORDS = ("旋转", "360", "环绕飞", "飞行", "急速", "极速", "快速拉近", "急推", "急拉", "甩镜", "螺旋", "翻滚")
CLOSEUP_WORDS = ("ECU", "CU", "BCU", "MCU", "特写", "近景", "中近景", "close")
WIDE_WORDS = ("ELS", "LS", "远景", "全景", "大全景", "定场", "wide", "establishing")
DIRECT_GAZE_INTENT_WORDS = (
    "POV", "主观镜头", "第一人称", "破第四墙", "对镜讲话", "对镜表演",
    "direct_address", "look_into_camera", "camera_address",
)
DIRECT_GAZE_RISK_RE = re.compile(r"正面直视镜头|直视镜头|看向镜头|面对镜头|迎着镜头|look(?:s|ing)?\s+(?:into|at)\s+(?:the\s+)?camera", re.I)


def episode_label(value: str) -> str:
    value = str(value or "").strip()
    if value.startswith("第") and value.endswith("集"):
        return value
    return f"第{value}集"


def storyboard_path(root: str, episode: str) -> Path:
    return Path(root) / "脚本" / episode / "storyboard.json"


def load_storyboard(root: str, episode: str) -> Dict[str, Any]:
    path = storyboard_path(root, episode)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("clips"), list):
        raise ValueError(f"{path} 缺 clips[]")
    return data


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clip_id(clip: Dict[str, Any], index: int) -> str:
    for key in ("clip_id", "id", "shot_id", "name", "镜头"):
        value = clip.get(key)
        if value:
            return str(value)
    return f"Clip_{index:02d}"


def _clip_text(clip: Dict[str, Any]) -> str:
    return json.dumps(clip, ensure_ascii=False, sort_keys=True)


def _has_any(text: str, words: Iterable[str]) -> bool:
    low = text.lower()
    return any(str(w).lower() in low for w in words)


def _continuity(clip: Dict[str, Any]) -> Dict[str, Any]:
    return _dict(clip.get("continuity"))


def _template_contract(clip: Dict[str, Any]) -> Dict[str, Any]:
    return _dict(clip.get("template_contract"))


def clip_camera_motivation(clip: Dict[str, Any]) -> str:
    """Return an explicit reason for moving the camera, never a generic dramatic label."""
    cont = _continuity(clip)
    tpl = _template_contract(clip)
    values: List[str] = []
    for source in (clip, cont, tpl):
        for key in (
            "camera_motivation", "movement_motivation", "camera_move_motivation",
            "运镜动机", "镜头运动动机",
        ):
            value = str(source.get(key) or "").strip()
            if value and value not in values:
                values.append(value)
    for shot in clip.get("shots") or []:
        if not isinstance(shot, dict):
            continue
        for key in ("camera_motivation", "movement_motivation", "运镜动机"):
            value = str(shot.get(key) or "").strip()
            if value and value not in values:
                values.append(value)
    return "；".join(values)


def clip_allows_direct_gaze(clip: Dict[str, Any]) -> bool:
    """Direct-to-camera gaze is opt-in for POV/direct address/fourth-wall shots."""
    cont = _continuity(clip)
    tpl = _template_contract(clip)
    values: List[str] = []
    for source in (clip, cont, tpl):
        for key in (
            "template", "template_id", "shot_type", "camera_relation", "gaze_intent",
            "eyeline_intent", "pov", "direct_address", "视线意图", "镜头关系",
        ):
            value = str(source.get(key) or "").strip()
            if value:
                values.append(value)
    text = " ".join(values)
    return _has_any(text, DIRECT_GAZE_INTENT_WORDS)


def clip_shot_size(clip: Dict[str, Any]) -> str:
    cont = _continuity(clip)
    return str(cont.get("shot_size") or clip.get("shot_size") or clip.get("景别") or "")


def clip_rhythm(clip: Dict[str, Any]) -> str:
    return str(clip.get("rhythm") or clip.get("节奏") or "")


def clip_template(clip: Dict[str, Any]) -> str:
    return str(clip.get("template") or clip.get("template_id") or clip.get("shot_type") or "")


def clip_expression_span(clip: Dict[str, Any]) -> str:
    cont = _continuity(clip)
    return str(cont.get("expression_span") or clip.get("expression_span") or clip.get("表情幅度") or "")


def clip_has_screen_surface(clip: Dict[str, Any]) -> bool:
    """True only for actual screen/panel shots, not generic compose overlay subtitles."""
    template = clip_template(clip)
    if template in {"screen_insert", "system_panel"}:
        return True
    tpl = _template_contract(clip)
    targeted = " ".join(str(tpl.get(k) or "") for k in (
        "motif_id",
        "vfx_asset",
        "screen_content_ref",
        "device_lock",
        "panel_tier",
    ))
    object_ids = clip.get("object_ids") or clip.get("objects") or []
    if not isinstance(object_ids, list):
        object_ids = [object_ids]
    object_text = " ".join(str(x or "") for x in object_ids)
    narrative_text = " ".join(str(clip.get(k) or "") for k in ("description", "label", "scene", "rhythm"))
    return _has_any(f"{template} {targeted} {object_text} {narrative_text}", SCREEN_WORDS)


def extract_camera_text(clip: Dict[str, Any]) -> str:
    cont = _continuity(clip)
    tpl = _template_contract(clip)
    candidates = (
        clip.get("camera_motion"),
        clip.get("camera_move"),
        clip.get("镜头运动"),
        clip.get("camera"),
        clip.get("camera_rule"),
        cont.get("camera_motion"),
        cont.get("camera"),
        cont.get("camera_rule"),
        tpl.get("camera_rule"),
        tpl.get("camera_motion"),
    )
    seen: List[str] = []
    for value in candidates:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.append(text)
    return "；".join(seen)


def classify_clip(clip: Dict[str, Any]) -> Dict[str, bool]:
    text = _clip_text(clip)
    rhythm = clip_rhythm(clip)
    shot = clip_shot_size(clip)
    template = clip_template(clip)
    expression = clip_expression_span(clip)
    joined = f"{text} {rhythm} {shot} {template} {expression}"
    return {
        "peak": _has_any(f"{rhythm} {text}", PEAK_WORDS),
        "setup": _has_any(f"{rhythm} {text}", SETUP_WORDS),
        "action": _has_any(f"{template} {text}", ACTION_WORDS),
        "dialogue": _has_any(f"{template} {text}", DIALOGUE_WORDS),
        "release": _has_any(f"{rhythm} {text}", RELEASE_WORDS),
        "screen": clip_has_screen_surface(clip),
        "closeup": _has_any(shot, CLOSEUP_WORDS),
        "wide": _has_any(shot, WIDE_WORDS),
        "big_expression": "大" in expression or "large" in expression.lower(),
        "has_template": bool(template),
        "joined": bool(joined.strip()),
    }


def _recommendation(move: str, speed: str, direction: str, end_size: str, reason: str) -> Dict[str, str]:
    if move in CAMERA_MOVE_LEXICON:
        spec = CAMERA_MOVE_LEXICON[move]
        en = str(spec.get("en") or "")
    else:
        en = "locked / fixed camera" if move in STATIC_CAMERA_WORDS or "固定" in move else ""
    return {
        "camera_move_zh": move,
        "camera_move_en": en,
        "speed": speed,
        "direction": direction,
        "end_size": end_size,
        "reason": reason,
    }


def recommend_camera_move(clip: Dict[str, Any]) -> Dict[str, str]:
    flags = classify_clip(clip)
    shot = clip_shot_size(clip)
    motivation = clip_camera_motivation(clip)
    existing = extract_camera_text(clip)
    normalized = normalize_camera_move(existing) if existing else {
        "moves": [], "speeds": [], "is_static": False, "recognized": False,
    }

    if normalized.get("is_static"):
        return _recommendation(
            "固定机位", "静止", "锁定构图、轴线与景别；人物和环境只在画内运动", shot or "storyboard 景别",
            "storyboard 已选择静机位；保留这项主动导演决定，让表演、停顿与画内调度承载张力。",
        )

    if flags["screen"]:
        return _recommendation(
            "固定机位", "静止", "锁定屏幕/光幕平面和可读区域", shot or "insert",
            "屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。",
        )
    if flags["big_expression"] and flags["closeup"]:
        return _recommendation(
            "固定机位", "静止", "锁定人物与戏内视线目标的相对关系", "CU/MCU",
            "大表情近景让眉眼、呼吸和停顿自己产生张力；静机位同时降低迎镜头转脸与脸漂风险。",
        )
    if flags["action"] and flags["peak"] and not flags["closeup"]:
        return _recommendation(
            "跟拍", "快速", "顺动作方向跟随半拍，命中点前稳定", shot or "MS/LS",
            "动作高光用跟拍制造代入感，但在命中/反应剪点前收稳，给 match_on_action 或反应切留清楚相位。",
        )
    if flags["action"] and not flags["closeup"]:
        return _recommendation(
            "移镜头", "匀速", "横移跟随主体，保持轴线方向不反转", shot or "MS/LS",
            "动作过程需要空间方向清楚；匀速移镜比自由漂浮更容易守轴线和人物站位。",
        )
    if flags["peak"] and flags["closeup"]:
        if motivation:
            return _recommendation(
                "推镜头", "缓慢", "沿人物视线/证据物方向推近，落点后停稳", "CU",
                f"已声明运镜动机：{motivation}。只执行一次缓推，不叠加其他运动。",
            )
        return _recommendation(
            "固定机位", "静止", "锁定人物与证据物的构图关系", "CU",
            "峰值近景没有独立运镜动机时保持静止；反转靠表演、证据落点和剪辑显现。",
        )
    if flags["peak"]:
        if motivation:
            return _recommendation(
                "冲击变焦", "急速冲击", "仅在揭示瞬间收至关键物/表情，随即停稳", "MCU/CU",
                f"已声明运镜动机：{motivation}。峰值只用一次短促冲击。",
            )
        return _recommendation(
            "固定机位", "静止", "锁定揭示物、人物反应和画面重心", shot or "MS/MCU",
            "峰值不自动等于冲击运镜；没有明确动机时由动作落点、反应和硬切制造冲击。",
        )
    if flags["release"]:
        if motivation:
            return _recommendation(
                "拉镜头", "缓慢", "由人物退到场景关系，保留孤立感", "MS/LS",
                f"已声明运镜动机：{motivation}。缓拉只服务人物与环境关系的显露。",
            )
        return _recommendation(
            "固定机位", "静止", "让人物在固定构图中退场或停留", shot or "MS/LS",
            "余韵段没有独立动机时保持静止，让空白、距离和人物离画产生释放感。",
        )
    if flags["wide"]:
        if motivation:
            return _recommendation(
                "升降", "缓慢", "单向揭示此前被遮挡的空间层次，落点后停稳", "LS/ELS",
                f"已声明运镜动机：{motivation}。运动只负责一次空间揭示。",
            )
        return _recommendation(
            "固定机位", "静止", "用前中后景和人物入出画建立空间关系", "LS/ELS",
            "定场镜先用朴实固定构图交代地理与权力关系；空间没有新增信息时不移动摄影机。",
        )
    if flags["dialogue"]:
        return _recommendation(
            "固定机位", "静止", "过肩/反打保持轴线、景别和视线目标", shot or "MCU",
            "对白/反打优先听说关系、停顿与反应；摄影机静止能避免角色迎镜头表演。",
        )
    if flags["setup"]:
        if motivation:
            return _recommendation(
                "推镜头", "缓慢", "从场面关系慢推到新出现的人物/物证", "MS/MCU",
                f"已声明运镜动机：{motivation}。推近必须对应新增信息，而不是装饰性靠近。",
            )
        return _recommendation(
            "固定机位", "静止", "锁定场面关系，让人物/物证在画内显露", shot or "MS/MCU",
            "铺垫与压迫不默认慢推；静止构图、等待和画内调度往往更有张力。",
        )
    return _recommendation(
        "固定机位", "静止", "锁定构图、轴线与戏内视线目标", shot or "MS/MCU",
        "普通镜默认静机位；张力先由人物表演、画内调度、声音与剪辑产生，运镜需要另写叙事动机。",
    )


def camera_phrase(rec: Dict[str, str]) -> str:
    move = rec["camera_move_zh"]
    speed = rec["speed"]
    direction = rec["direction"]
    end_size = rec["end_size"]
    if "固定" in move:
        return f"固定机位，{direction}；摄影机保持完全静止，人物呼吸与环境微动留在画内"
    if end_size:
        return f"{speed}{move}，{direction}，落到{end_size}"
    return f"{speed}{move}，{direction}"


def backend_control_instruction(rec: Dict[str, str], backend_control: Dict[str, Any], clip_id: str) -> str:
    """Render the same camera plan into the target backend's control idiom."""
    idiom = str(backend_control.get("control_idiom") or "natural_language")
    move = rec["camera_move_zh"]
    speed = rec["speed"]
    direction = rec["direction"]
    end_size = rec["end_size"] or "storyboard end frame"
    phrase = camera_phrase(rec)
    if idiom == "motion_brush_on_firstframe":
        return (
            f"Kling motion brush：在首帧上沿「{direction}」画主体/背景运动路径；"
            f"per-shot: camera_move={move}; speed={speed}; end_size={end_size}; "
            "lock first-frame identity, axis, lighting, and contact points."
        )
    if idiom == "structured_multi_prompt":
        return (
            f"Shot {clip_id}: camera={move}; speed={speed}; direction={direction}; "
            f"end_frame={end_size}; keep first-frame identity/lighting/axis; "
            "no unplanned spin, drift, or scene rebuild."
        )
    return f"自然语言运镜：{phrase}；首帧锚定，不改变角色、光位、轴线和场景设定。"


def tension_word(clip: Dict[str, Any]) -> str:
    flags = classify_clip(clip)
    if flags["peak"] and flags["action"]:
        return "爆发"
    if flags["peak"]:
        return "紧张"
    if flags["release"]:
        return "释放"
    if flags["setup"]:
        return "克制"
    return "聚焦"


def build_prompt_injections(
    clip: Dict[str, Any],
    rec: Dict[str, str],
    backend_control: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    shot = clip_shot_size(clip) or "沿 storyboard 景别"
    phrase = camera_phrase(rec)
    tension = tension_word(clip)
    reason = rec["reason"]
    backend_control = backend_control or {"control_idiom": "natural_language", "source": "no_route"}
    is_static = "固定" in rec["camera_move_zh"]
    direct_gaze = clip_allows_direct_gaze(clip)
    image = {
        "镜头/机位": f"{shot}；{'锁定静止构图，以画内调度组织张力' if is_static else '按已声明运镜动机组织起幅与落幅'}，首帧不是摆拍肖像。",
        "起幅·运动余量": (
            "固定机位不预留摄影机漂移空间；只给人物动作方向、戏内视线与出入画保留 15%-25% 空间。"
            if is_static else f"为「{phrase}」预留前景/背景运动余量；主体不要顶边，动作方向留 15%-25% 空间。"
        ),
        "构图防呆": "光位、轴线、角色状态继承 storyboard visual_contract；摄影机是旁观者，角色头眼朝向戏内目标。" if not direct_gaze else "光位、轴线、角色状态继承 storyboard visual_contract；本镜已明确 POV/破第四墙，直视摄影机只发生在登记节拍。",
        "视线表演": "眼睛、鼻梁轴与头部朝向持续锁定戏内对手/道具/动作落点，以三分之四、侧向或过肩关系表演。" if not direct_gaze else "按 POV/破第四墙合同，在登记节拍内把视线落到摄影机；节拍外恢复戏内目标。",
        "导演意图": reason,
    }
    video = {
        "导演意图": reason,
        "起幅": "继承首帧构图、光位、轴线和角色状态，不重定视觉设定。",
        "落幅": f"落在{rec['end_size'] or shot}，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。",
        "镜头运动": phrase,
        "视线表演": image["视线表演"],
        "后端控制写法": backend_control_instruction(rec, backend_control, str(clip.get("clip_id") or clip.get("id") or "")),
        "运动精修": f"张力={tension}；无明确叙事动机时保持固定，张力先由表演、画内调度、停顿与剪辑产生；有动机也只执行一种单向运动。",
        "动态细节": "人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。",
    }
    return image, video


def analyze_clip(clip: Dict[str, Any], index: int, backend_control: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    clip_id = _clip_id(clip, index)
    camera_text = extract_camera_text(clip)
    norm = normalize_camera_move(camera_text) if camera_text else {
        "moves": [], "speeds": [], "is_static": False, "recognized": False,
    }
    rec = recommend_camera_move(clip)
    backend_control = backend_control or {"control_idiom": "natural_language", "source": "no_route"}
    image, video = build_prompt_injections(clip, rec, backend_control)
    findings: List[Dict[str, str]] = []

    if not camera_text:
        findings.append({
            "severity": "warn",
            "code": "camera_move_missing",
            "message": "storyboard 未声明镜头运动；出图/出视频容易退化成静态插画或随机漂浮。",
        })
    elif not norm["recognized"]:
        findings.append({
            "severity": "warn",
            "code": "camera_move_unstructured",
            "message": "镜头运动未命中 CAMERA_MOVE_LEXICON 或固定机位词；建议改为推/拉/摇/移/升降/跟拍/固定等结构化词。",
        })
    elif norm["moves"] and not norm["speeds"] and not norm["is_static"]:
        findings.append({
            "severity": "warn",
            "code": "camera_speed_missing",
            "message": "已声明运镜但缺速度档；补缓慢/匀速/快速/轻微/急速冲击，模型才知道节奏强度。",
        })

    flags = classify_clip(clip)
    motivation = clip_camera_motivation(clip)
    if camera_text and norm["moves"] and not norm["is_static"] and not motivation and not (flags["action"] and not flags["closeup"]):
        findings.append({
            "severity": "warn",
            "code": "unmotivated_camera_motion",
            "message": "已声明摄影机运动但没有 camera_motivation/运镜动机；普通镜应改固定，或补清楚运动揭示了什么新信息。",
        })
    gaze_text = " ".join(str(clip.get(key) or "") for key in ("description", "label", "camera_relation", "gaze_intent", "eyeline_intent"))
    gaze_text += " " + str(_continuity(clip).get("eyeline") or "")
    if DIRECT_GAZE_RISK_RE.search(gaze_text) and not clip_allows_direct_gaze(clip):
        findings.append({
            "severity": "warn",
            "code": "unmotivated_direct_camera_gaze",
            "message": "角色被写成正视/面对摄影机，但本镜没有 POV、破第四墙或对镜叙事合同；改为锁定戏内对象与三分之四/侧向头眼关系。",
        })
    if camera_text and flags["closeup"] and _has_any(camera_text, OVERACTIVE_WORDS):
        findings.append({
            "severity": "warn",
            "code": "overactive_closeup",
            "message": "近景/大表情镜出现旋转、飞行、急速等高风险运镜，容易造成脸漂、迎镜头和廉价感；优先改为固定机位。",
        })
    if flags["big_expression"] and flags["closeup"] and rec["camera_move_zh"] != "固定机位":
        findings.append({
            "severity": "warn",
            "code": "big_expression_needs_stable_camera",
            "message": "大表情近景应优先固定，复杂环绕、推近或快速跟拍会让表情和身份被重画，也更容易把脸吸向摄影机。",
        })

    return {
        "index": index,
        "clip_id": clip_id,
        "shot_size": clip_shot_size(clip),
        "rhythm": clip_rhythm(clip),
        "template": clip_template(clip),
        "existing_camera": camera_text,
        "normalized_camera": norm,
        "recommended": rec,
        "backend_control": backend_control,
        "image_prompt_injection": image,
        "video_prompt_injection": video,
        "findings": findings,
    }


def _route_map(root: str, episode: str) -> Dict[str, Dict[str, Any]]:
    if not root:
        return {}
    return {
        str(route.get("clip_id") or ""): route
        for route in video_backend_adapter.load_video_routes(root, episode)
        if isinstance(route, dict) and route.get("clip_id")
    }


def _clip_backend_control(root: str, episode: str, clip_id: str, routes_by_id: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    if not root:
        return {"control_idiom": "natural_language", "control_idiom_supported": False, "source": "no_project_root"}
    route = routes_by_id.get(clip_id)
    if not route:
        return {"control_idiom": "natural_language", "control_idiom_supported": False, "source": "no_video_route"}
    backend = str(route.get("primary_backend") or "").strip()
    channel = get_setting(root, "生视频渠道", "").strip()
    if not backend:
        return {"control_idiom": "natural_language", "control_idiom_supported": False, "source": "route_without_backend"}
    control = video_backend_adapter.resolve_control_idiom(root, backend, channel)
    control["route_backend"] = backend
    control["route_channel"] = channel
    return control


def build_plan(storyboard: Dict[str, Any], episode: str, root: str = "") -> Dict[str, Any]:
    clips = storyboard.get("clips") if isinstance(storyboard.get("clips"), list) else []
    routes_by_id = _route_map(root, episode)
    analyzed = []
    for i, clip in enumerate(clips):
        if not isinstance(clip, dict):
            continue
        clip_id = _clip_id(clip, i + 1)
        analyzed.append(analyze_clip(clip, i + 1, _clip_backend_control(root, episode, clip_id, routes_by_id)))
    warn_count = sum(1 for c in analyzed for f in c["findings"] if f.get("severity") == "warn")
    missing_count = sum(1 for c in analyzed for f in c["findings"] if f.get("code") == "camera_move_missing")
    unstructured_count = sum(1 for c in analyzed for f in c["findings"] if f.get("code") == "camera_move_unstructured")
    return {
        "kind": "n2d_director_camera_plan",
        "version": 3,
        "episode": episode,
        "summary": {
            "clips": len(analyzed),
            "warn_count": warn_count,
            "camera_move_missing": missing_count,
            "camera_move_unstructured": unstructured_count,
        },
        "clips": analyzed,
    }


def output_paths(root: str, episode: str) -> Tuple[Path, Path]:
    base = Path(root) / "生产数据"
    return base / f"director_camera_plan_{episode}.json", base / f"director_camera_plan_{episode}.md"


def format_markdown(plan: Dict[str, Any]) -> str:
    lines = [
        f"# 导演运镜审查与 Prompt 落地 - {plan['episode']}",
        "",
        f"- Clip 数：{plan['summary']['clips']}",
        f"- WARN：{plan['summary']['warn_count']}",
        f"- 缺运镜：{plan['summary']['camera_move_missing']}",
        f"- 自由散文运镜：{plan['summary']['camera_move_unstructured']}",
        "",
        "> 用法：把每个 Clip 的「出图注入」抄进 `01_分镜出图.md` 对应正向 prompt，把「视频注入」抄进 `01_clips.md` 的导演调度七字段/镜头运动段。若与 storyboard 既有剧情状态冲突，以 storyboard 为准并人工改写。",
        "",
    ]
    for clip in plan["clips"]:
        rec = clip["recommended"]
        lines.extend([
            f"## {clip['clip_id']}",
            f"- 景别：{clip.get('shot_size') or '未声明'}",
            f"- 节奏：{clip.get('rhythm') or '未声明'}",
            f"- 原运镜：{clip.get('existing_camera') or '未声明'}",
            f"- 建议运镜：{camera_phrase(rec)}",
            f"- 后端控制写法：{clip.get('backend_control', {}).get('control_idiom', 'natural_language')}（source={clip.get('backend_control', {}).get('source', 'unknown')}）",
            f"- 理由：{rec['reason']}",
        ])
        if clip["findings"]:
            lines.append("- Findings：")
            for finding in clip["findings"]:
                lines.append(f"  - [{finding['severity']}] {finding['code']}：{finding['message']}")
        lines.extend([
            "",
            "出图注入：",
            "```text",
            f"镜头/机位：{clip['image_prompt_injection']['镜头/机位']}",
            f"起幅·运动余量：{clip['image_prompt_injection']['起幅·运动余量']}",
            f"构图防呆：{clip['image_prompt_injection']['构图防呆']}",
            f"视线表演：{clip['image_prompt_injection']['视线表演']}",
            "```",
            "",
            "视频注入：",
            "```text",
            f"导演意图：{clip['video_prompt_injection']['导演意图']}",
            f"起幅：{clip['video_prompt_injection']['起幅']}",
            f"落幅：{clip['video_prompt_injection']['落幅']}",
            f"镜头运动：{clip['video_prompt_injection']['镜头运动']}",
            f"视线表演：{clip['video_prompt_injection']['视线表演']}",
            f"后端控制写法：{clip['video_prompt_injection']['后端控制写法']}",
            f"运动精修：{clip['video_prompt_injection']['运动精修']}",
            f"动态细节：{clip['video_prompt_injection']['动态细节']}",
            "```",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def write_plan(root: str, episode: str, plan: Dict[str, Any]) -> Tuple[Path, Path]:
    json_path, md_path = output_paths(root, episode)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
        f.write("\n")
    md_path.write_text(format_markdown(plan), encoding="utf-8")
    return json_path, md_path


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="n2d director camera-language audit")
    parser.add_argument("root", help="作品根")
    parser.add_argument("episode", help="第N集或 N")
    parser.add_argument("--write", action="store_true", help="写入 生产数据/director_camera_plan_第N集.json/.md")
    parser.add_argument("--json", action="store_true", help="stdout 输出 JSON")
    parser.add_argument("--strict", action="store_true", help="有 warn 时退出 1")
    args = parser.parse_args(argv)

    ep = episode_label(args.episode)
    try:
        storyboard = load_storyboard(args.root, ep)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"缺/坏 {storyboard_path(args.root, ep)}：{exc}", file=sys.stderr)
        return 2

    plan = build_plan(storyboard, ep, args.root)
    if args.write:
        json_path, md_path = write_plan(args.root, ep, plan)
        print(f"wrote {json_path}")
        print(f"wrote {md_path}")
    elif args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(format_markdown(plan), end="")

    if args.strict and plan["summary"]["warn_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
