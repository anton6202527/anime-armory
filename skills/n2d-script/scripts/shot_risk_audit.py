#!/usr/bin/env python3
"""Pre-cost generation risk scoring for n2d storyboard clips.

This does not judge story quality. It flags clips that are expensive or fragile
for image/video generation before the project reaches paid stages.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from n2d_contract import (  # noqa: E402
    ACTION_CHOREOGRAPHY_SHOT_TYPES,
    default_degrade_plan,
    HIGH_MOTION_TEMPLATES,
    infer_spectacle_type,
    missing_fields,
    spectacle_recommendations,
    spectacle_required_fields,
)
# 多主体「已登记执行策略」放行集单一真值源（n2d_const）：与 gate/image_qc/face_drift 同源，
# 使 multi_subject_missing_slots_or_strategy 的 must ⊆ review 同框 block，不再靠人手同步词表。
from n2d_const import MULTI_SUBJECT_ACCEPTING_MARKERS  # noqa: E402
from seam_contract import needs_end_anchor  # noqa: E402

ACTION_KINDS = set(ACTION_CHOREOGRAPHY_SHOT_TYPES)
MOTION_RE = re.compile(r"(打斗|追逐|追车|疾驰|翻滚|俯冲|爆炸|法术|对轰|飞行|御兽|坐骑|骑兽|马车|车轮|载具|汽车|摩托|车流|变道|刹车|高架|飞舟|御物|尾随|跟踪|潜入|潜行|暗走廊|手电|渡劫|雷劫|突破|传送|穿越|召唤|元神|神魂|夺舍|快摇|甩镜|冲刺|撞击|受击|命中)")
MOUTH_RE = re.compile(r"(说话|开口|台词|对白|质问|喊|怒吼|mouth_visible|native_speech|dialogue)")
VFX_RE = re.compile(r"(系统面板|手机屏幕|电脑屏幕|监控画面|聊天记录|升级|法阵|阵法|阵图|结界|封印|传送门|时空裂缝|秘境入口|雷劫|天劫|突破光柱|炼丹|炼器|丹炉|测灵石|血脉觉醒|妖气|灵力|爆炸|光幕|特效|VFX_|WEAPON_|PROP_|EVIDENCE_)")
CLOSE_RE = re.compile(r"(CU|ECU|MCU|特写|近景|大特写|反打|正反打)")


def ep_label(value: str) -> str:
    return value if value.startswith("第") else f"第{value}集"


def storyboard_path(root: str, ep: str) -> Path:
    return Path(root) / "脚本" / ep / "storyboard.json"


def load_storyboard(root: str, ep: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    path = storyboard_path(root, ep)
    if not path.exists():
        return None, f"缺 {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"storyboard.json 不可解析：{type(exc).__name__}: {exc}"
    if not isinstance(data, dict):
        return None, "storyboard.json 顶层必须是对象"
    return data, None


def duration_of(clip: Dict[str, Any]) -> float:
    for key in ("duration", "duration_sec", "时长", "seconds"):
        value = clip.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            m = re.search(r"\d+(?:\.\d+)?", value)
            if m:
                return float(m.group(0))
    return 0.0


def clip_id(clip: Dict[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip{idx:02d}")


def clip_blob(clip: Dict[str, Any]) -> str:
    return json.dumps(clip, ensure_ascii=False, sort_keys=True)


def character_count(clip: Dict[str, Any], blob: str) -> int:
    schedule = clip.get("entity_schedule")
    if isinstance(schedule, dict) and isinstance(schedule.get("characters"), list):
        offscreen = {str(v).strip() for v in (schedule.get("offscreen_presence") or []) if str(v).strip()}
        forbidden = {str(v).strip() for v in (schedule.get("forbidden_presence") or []) if str(v).strip()}
        visible = {
            str(v).strip()
            for v in schedule.get("characters") or []
            if str(v).strip() and str(v).strip() not in offscreen and str(v).strip() not in forbidden
        }
        # entity_schedule is the Stage 2 visibility truth.  Do not fall back
        # to a whole-clip regex that turns offscreen voices into clear faces.
        return len(visible)
    for key in ("character_ids", "characters", "角色"):
        value = clip.get(key)
        if isinstance(value, list):
            ids = set()
            for item in value:
                if isinstance(item, dict):
                    raw = item.get("character_id") or item.get("id") or item.get("char_id") or item.get("name")
                else:
                    raw = item
                if str(raw or "").strip():
                    ids.add(str(raw).strip())
            return len(ids)
    ids = set(re.findall(r"\bCHAR_[A-Za-z0-9_]+", blob))
    return len(ids)


def has_multi_subject_slots(blob: str) -> bool:
    return any(token in blob for token in ("多人同框身份槽位", "character_slots", "subject_slots", "screen_positions", "face_priority")) \
        and bool(re.search(r"\bCHAR_[A-Za-z0-9_]+", blob)) and any(
        token in blob for token in ("LEFT_SLOT", "RIGHT_SLOT", "FOREGROUND_SLOT", "BACKGROUND_SLOT", "画左", "画右", "前景", "后景")
    )


def has_multi_subject_strategy(blob: str) -> bool:
    # 词表上提 n2d_const.MULTI_SUBJECT_ACCEPTING_MARKERS 单一真值源（含分层/原生/执行策略三类）。
    return any(token in blob for token in MULTI_SUBJECT_ACCEPTING_MARKERS)


def is_wide_crowd(blob: str, shot_size: str) -> bool:
    text = f"{shot_size}\n{blob}"
    return bool(re.search(r"(远景|大全景|群像|人海|crowd|wide shot|extreme long|ELS)", text, re.I))


def has_mid_anchor(cont: Dict[str, Any]) -> bool:
    return bool(cont.get("midframe") or cont.get("anchors") or cont.get("midframe_exempt_reason"))


def score_clip(clip: Dict[str, Any], idx: int) -> Dict[str, Any]:
    blob = clip_blob(clip)
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
    template = str(clip.get("template") or "")
    spectacle_type = infer_spectacle_type(clip)
    duration = duration_of(clip)
    chars = character_count(clip, blob)
    shot_size = str(cont.get("shot_size") or "")
    expression = str(cont.get("expression_span") or "")

    score = 0
    tags: List[str] = []
    recommendations: List[str] = []
    findings: List[Dict[str, Any]] = []

    def add_score(points: int, tag: str, rec: Optional[str] = None) -> None:
        nonlocal score
        score += points
        tags.append(tag)
        if rec and rec not in recommendations:
            recommendations.append(rec)

    if duration >= 12:
        add_score(4, "long_clip_12s", "长镜先拆节拍或确认后端多帧能力；至少补多锚帧。")
    elif duration >= 8:
        add_score(2, "long_clip_8s", "8s 以上镜头先补中段锚帧，必要时拆段接力。")
    if template in HIGH_MOTION_TEMPLATES or MOTION_RE.search(blob):
        add_score(3, "high_motion", "高运动镜头按专项模板拆起手/命中/收势，补 `_mid`/`_aK`。")
    if MOUTH_RE.search(blob):
        add_score(2, "mouth_visible", "说话近景优先原生音画或配音口型路线，避免后期双人声。")
    if CLOSE_RE.search(shot_size) or CLOSE_RE.search(blob):
        add_score(2, "closeup", "近景/特写镜头要强身份锁和表情锚。")
    if expression == "大":
        add_score(3, "large_expression_span", "大表情近景必须首尾双帧或降级为 MCU。")
    if chars >= 4:
        add_score(5, "many_named_characters", "高人数同框要写身份槽位+执行策略，优先拆组/反打/群像远景/分层合成。")
    elif chars >= 2:
        add_score(2, "multi_character", "多人同框要写身份槽位、执行策略、站位和区分锚点。")
    if VFX_RE.search(blob):
        add_score(2, "vfx_or_asset", "系统/法术/武器/道具要注册 LOC/PROP/WEAPON/VFX id，文字层后期 overlay。")
    if spectacle_type:
        tag = f"spectacle_{spectacle_type}"
        extra = 4 if spectacle_type in ACTION_KINDS else 3
        add_score(extra, tag, default_degrade_plan(spectacle_type))
        for rec in spectacle_recommendations(spectacle_type):
            if rec not in recommendations:
                recommendations.append(rec)
        contract = {}
        if spectacle_type == "large_establishing":
            for key in ("large_scene_contract", "spectacle_contract", "template_contract"):
                value = clip.get(key)
                if isinstance(value, dict):
                    contract = value
                    break
        elif isinstance(clip.get("template_contract"), dict):
            contract = clip["template_contract"]
        required = spectacle_required_fields(spectacle_type)
        missing = missing_fields(contract, required) if contract else list(required)
        if missing:
            findings.append({
                "severity": "warn",
                "code": "spectacle_contract_incomplete",
                "message": f"{spectacle_type} 缺专项契约字段：{', '.join(missing[:8])}；进入出图 prompt 前会被 spectacle_contract_audit 阻断。",
            })

    wide_crowd = is_wide_crowd(blob, shot_size)
    if chars >= 2 and not wide_crowd and not (has_multi_subject_slots(blob) and has_multi_subject_strategy(blob)):
        findings.append({"severity": "must", "code": "multi_subject_missing_slots_or_strategy",
                         "message": "清晰同框具名角色 ≥2 但缺 `多人同框身份槽位` 或 `多人同框执行策略`："
                                    "2-3 张清晰脸只是相对省钱/稳定的构图区，不是免登记区。剧情需要就照出，但必须登记 "
                                    "native_subject_slots / regional_construct_required / split_composite_required / shot_reverse_shot 等执行路径；"
                                    "远景群像请显式标 `远景/群像`。"})
    if chars >= 4 and not wide_crowd:
        findings.append({"severity": "warn", "code": "large_same_frame_strategy_recommended",
                         "message": "清晰同框具名角色 ≥4：人数高，优先拆组/反打/景别分层或分区构建；"
                                    "这是要求把同框做对，不是删戏/砍人数。"})
    if expression == "大" and (CLOSE_RE.search(shot_size) or CLOSE_RE.search(blob)) and not needs_end_anchor(clip):
        findings.append({"severity": "must", "code": "large_expression_without_endframe",
                         "message": "大表情近景缺 end_anchor_required=true，脸会被表情重画；该尾锚不等于跨镜 relay。"})
    if score >= 5 and not has_mid_anchor(cont):
        findings.append({"severity": "warn", "code": "high_risk_without_mid_anchor",
                         "message": "高风险 Clip 缺中段锚帧/多锚/豁免说明，建议先跑 anchor_planner --write。"})

    severity = "must" if any(f["severity"] == "must" for f in findings) else ("warn" if score >= 5 or findings else "info")
    return {
        "id": clip_id(clip, idx),
        "score": score,
        "severity": severity,
        "spectacle_type": spectacle_type,
        "duration": duration,
        "tags": tags,
        "recommendations": recommendations,
        "findings": findings,
    }


def audit(root: str, ep: str) -> Dict[str, Any]:
    ep = ep_label(ep)
    data, err = load_storyboard(root, ep)
    if err:
        return {"episode": ep, "ok": False, "clips": [], "findings": [
            {"severity": "must", "code": "missing_storyboard", "message": err}
        ], "pilot_candidates": []}
    clips = data.get("clips")
    if not isinstance(clips, list) or not clips:
        return {"episode": ep, "ok": False, "clips": [], "findings": [
            {"severity": "must", "code": "empty_clips", "message": "storyboard.json 缺非空 clips[]。"}
        ], "pilot_candidates": []}
    scored = [score_clip(c if isinstance(c, dict) else {}, i) for i, c in enumerate(clips, 1)]
    findings: List[Dict[str, Any]] = []
    for item in scored:
        for f in item["findings"]:
            findings.append({**f, "clip": item["id"], "score": item["score"]})
    top = sorted(scored, key=lambda x: (x["score"], x["severity"] == "must"), reverse=True)[:3]
    pilot = [c for c in top if c["score"] > 0] or scored[:1]
    return {
        "episode": ep,
        "ok": not any(f["severity"] == "must" for f in findings),
        "clips": scored,
        "findings": findings,
        "pilot_candidates": pilot,
        "summary": {
            "clips": len(scored),
            "max_score": max((c["score"] for c in scored), default=0),
            "warn_or_higher": sum(1 for c in scored if c["severity"] in {"warn", "must"}),
        },
    }


def print_human(result: Dict[str, Any]) -> None:
    summary = result.get("summary") or {}
    print(f"# 分镜生成风险评分 — {result.get('episode')}")
    print(f"clips={summary.get('clips', 0)} max_score={summary.get('max_score', 0)} high_risk={summary.get('warn_or_higher', 0)}")
    for clip in result.get("clips") or []:
        if clip["severity"] == "info":
            continue
        print(f"- {clip['severity'].upper()} {clip['id']} score={clip['score']} tags={','.join(clip['tags'])}")
        for rec in clip.get("recommendations") or []:
            print(f"  rec: {rec}")
    if not result.get("findings"):
        print("- PASS：未发现必须先处理的可生成性硬风险。")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d storyboard generation risk audit")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ns = ap.parse_args(argv)
    result = audit(ns.root.rstrip("/"), ep_label(ns.episode))
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result)
    has_must = any(f["severity"] == "must" for f in result.get("findings") or [])
    has_warn = any(f["severity"] == "warn" for f in result.get("findings") or [])
    if ns.strict and (has_must or has_warn):
        return 1
    return 1 if has_must else 0


if __name__ == "__main__":
    raise SystemExit(main())
