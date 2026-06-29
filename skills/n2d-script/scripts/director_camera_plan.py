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
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
N2D_LIB = REPO_ROOT / "skills" / "n2d" / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))

from n2d_const import CAMERA_MOVE_LEXICON, STATIC_CAMERA_WORDS  # noqa: E402
from n2d_logic import normalize_camera_move  # noqa: E402


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
SCREEN_WORDS = ("系统面板", "screen_insert", "面板", "光幕", "字幕卡", "overlay")
OVERACTIVE_WORDS = ("旋转", "360", "环绕飞", "飞行", "急速", "极速", "快速拉近", "急推", "急拉", "甩镜", "螺旋", "翻滚")
CLOSEUP_WORDS = ("ECU", "CU", "BCU", "MCU", "特写", "近景", "中近景", "close")
WIDE_WORDS = ("ELS", "LS", "远景", "全景", "大全景", "定场", "wide", "establishing")


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
        "screen": _has_any(f"{template} {text}", SCREEN_WORDS),
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
    rhythm = clip_rhythm(clip)

    if flags["screen"]:
        return _recommendation(
            "固定机位", "轻微", "锁定屏幕/光幕平面，不漂移", shot or "insert",
            "屏幕/面板镜以可读性为第一目标，固定机位避免文字和 UI 漂移。",
        )
    if flags["big_expression"] and flags["closeup"]:
        return _recommendation(
            "推镜头", "轻微", "沿视线轴轻推，最后稳定停住", "CU/MCU",
            "大表情近景最怕脸被运动重画；轻微推近比环绕/甩镜更稳，也能把情绪怼近。",
        )
    if flags["action"] and flags["peak"] and not flags["closeup"]:
        return _recommendation(
            "跟拍", "快速", "顺动作方向跟随半拍，命中点前稳定", shot or "MS/LS",
            "动作高光用跟拍制造代入感，但在命中/反应拍前收稳，方便首尾帧接力。",
        )
    if flags["action"] and not flags["closeup"]:
        return _recommendation(
            "移镜头", "匀速", "横移跟随主体，保持轴线方向不反转", shot or "MS/LS",
            "动作过程需要空间方向清楚；匀速移镜比自由漂浮更容易守轴线和人物站位。",
        )
    if flags["peak"] and flags["closeup"]:
        return _recommendation(
            "推镜头", "缓慢", "沿人物视线/证据物方向推近", "CU",
            "反转/打脸/觉醒在近景里用推近强化压迫，不用大幅旋转破坏表演。",
        )
    if flags["peak"]:
        return _recommendation(
            "冲击变焦", "急速冲击", "在揭示瞬间收至关键物/表情", "MCU/CU",
            "峰值拍需要短促冲击，但只在揭示瞬间使用，避免整镜廉价乱动。",
        )
    if flags["release"]:
        return _recommendation(
            "拉镜头", "缓慢", "由人物退到场景关系，保留孤立感", "MS/LS",
            "余韵/孤独/退场用拉远释放情绪，并给下一镜留转场空间。",
        )
    if flags["wide"]:
        return _recommendation(
            "升降", "缓慢", "轻微上升/下降揭示空间层次", "LS/ELS",
            "定场镜用升降建立地理和权力关系，不抢人物表演。",
        )
    if flags["dialogue"]:
        return _recommendation(
            "固定机位", "轻微", "过肩/反打保持轴线，只允许呼吸式微推", shot or "MCU",
            "对白/反打优先表演和脸稳；固定机位或微推比无目的漂移更有戏。",
        )
    if flags["setup"]:
        return _recommendation(
            "推镜头", "缓慢", "从场面关系慢推到人物/物证", "MS/MCU",
            "铺垫和压迫段用慢推聚焦信息，让观众逐步靠近秘密。",
        )
    return _recommendation(
        "推镜头", "轻微", "沿主体动作/视线方向轻推", shot or "MS/MCU",
        "默认给镜头一点目的性：轻微推近能增加叙事关注，同时风险低。",
    )


def camera_phrase(rec: Dict[str, str]) -> str:
    move = rec["camera_move_zh"]
    speed = rec["speed"]
    direction = rec["direction"]
    end_size = rec["end_size"]
    if "固定" in move:
        return f"固定机位，{direction}，只允许{speed}呼吸式微动"
    if end_size:
        return f"{speed}{move}，{direction}，落到{end_size}"
    return f"{speed}{move}，{direction}"


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


def build_prompt_injections(clip: Dict[str, Any], rec: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    shot = clip_shot_size(clip) or "沿 storyboard 景别"
    phrase = camera_phrase(rec)
    tension = tension_word(clip)
    reason = rec["reason"]
    image = {
        "镜头/机位": f"{shot}；按导演运镜预留起幅，首帧不是摆拍肖像。",
        "起幅·运动余量": f"为「{phrase}」预留前景/背景运动余量；主体不要顶边，动作方向留 15%-25% 空间。",
        "构图防呆": "角色视线锁戏内目标；非 POV 镜不看镜头；光位、轴线、角色状态继承 storyboard visual_contract。",
        "导演意图": reason,
    }
    video = {
        "导演意图": reason,
        "起幅": "继承首帧构图、光位、轴线和角色状态，不重定视觉设定。",
        "落幅": f"落在{rec['end_size'] or shot}，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。",
        "镜头运动": phrase,
        "运动精修": f"张力={tension}；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。",
        "动态细节": "人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构。",
    }
    return image, video


def analyze_clip(clip: Dict[str, Any], index: int) -> Dict[str, Any]:
    clip_id = _clip_id(clip, index)
    camera_text = extract_camera_text(clip)
    norm = normalize_camera_move(camera_text) if camera_text else {
        "moves": [], "speeds": [], "is_static": False, "recognized": False,
    }
    rec = recommend_camera_move(clip)
    image, video = build_prompt_injections(clip, rec)
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
    if camera_text and flags["closeup"] and _has_any(camera_text, OVERACTIVE_WORDS):
        findings.append({
            "severity": "warn",
            "code": "overactive_closeup",
            "message": "近景/大表情镜出现旋转、飞行、急速等高风险运镜，容易造成脸漂和廉价感；改为固定或轻微推近。",
        })
    if flags["big_expression"] and flags["closeup"] and rec["camera_move_zh"] not in ("固定机位", "推镜头"):
        findings.append({
            "severity": "warn",
            "code": "big_expression_needs_stable_camera",
            "message": "大表情近景应优先固定/轻推，复杂环绕或快速跟拍会让表情和身份被重画。",
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
        "image_prompt_injection": image,
        "video_prompt_injection": video,
        "findings": findings,
    }


def build_plan(storyboard: Dict[str, Any], episode: str) -> Dict[str, Any]:
    clips = storyboard.get("clips") if isinstance(storyboard.get("clips"), list) else []
    analyzed = [analyze_clip(c, i + 1) for i, c in enumerate(clips) if isinstance(c, dict)]
    warn_count = sum(1 for c in analyzed for f in c["findings"] if f.get("severity") == "warn")
    missing_count = sum(1 for c in analyzed for f in c["findings"] if f.get("code") == "camera_move_missing")
    unstructured_count = sum(1 for c in analyzed for f in c["findings"] if f.get("code") == "camera_move_unstructured")
    return {
        "kind": "n2d_director_camera_plan",
        "version": 1,
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
            "```",
            "",
            "视频注入：",
            "```text",
            f"导演意图：{clip['video_prompt_injection']['导演意图']}",
            f"起幅：{clip['video_prompt_injection']['起幅']}",
            f"落幅：{clip['video_prompt_injection']['落幅']}",
            f"镜头运动：{clip['video_prompt_injection']['镜头运动']}",
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

    plan = build_plan(storyboard, ep)
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
