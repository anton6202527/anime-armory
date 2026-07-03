#!/usr/bin/env python3
"""Storyboard contract gate for n2d-script stage 2.

This is the cheap, script-stage version of the image/video gates: it checks the
director contracts that must exist before any paid image work starts.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "n2d", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from n2d_contract import (  # noqa: E402
    ACTION_CHOREOGRAPHY_SHOT_TYPES,
    TEMPLATE_BASE_FIELDS,
    spectacle_required_fields,
)
from n2d_const import HIGH_MOTION_TEMPLATES, STYLE_CONTRACT_FIELDS, VISUAL_CONTRACT_FIELDS  # noqa: E402
from n2d_logic import special_template_keywords  # noqa: E402
from n2d_platform_profiles import backend_supports_three_plus_frames  # noqa: E402


ACTION_ANCHOR_DURATION_SEC = 8.0
_ACTION_ANCHOR_HEAVY_RE = re.compile(
    r"打斗|攻防|拳脚|挥拳|刀剑|挥剑|抬剑|举剑|拔剑|掌法|出掌|追逐|追赶|冲刺|法术|武技|斗法|撞点|命中|碰撞|接触|抓腕|拉扯|拥抱|多主体接触|多人接触|"
    r"fight|chase|magic|impact|collision|contact",
    re.I,
)
_ACTION_ANCHOR_PREP_RE = re.compile(r"起手|蓄力|预备|发力|逼近|冲刺|冲向|追近|跃起|抬剑|举剑|拔剑|挥拳|出招|charge|windup|approach", re.I)
_ACTION_ANCHOR_IMPACT_RE = re.compile(r"命中|击中|撞点|撞击|碰撞|格挡|接触|抓住|拉住|爆发|落地|受击|hit|impact|collision|contact", re.I)
_ACTION_ANCHOR_RESPONSE_RE = re.compile(r"反应|受击|后撤|倒退|跌落|摔倒|余波|收势|回收|定住|僵住|退开|reaction|recovery|aftershock", re.I)
ACTION_ANCHOR_RISK_FLAGS = frozenset({
    "physical_contact",
    "multi_character_overlap",
    "high_speed_motion",
    "extreme_camera",
    "high_action",
    "spectacle",
    "contact_motion",
    "fast_motion",
    "physics",
})

_REALM_PORTAL_WEAK_TERMS = frozenset({
    "穿越", "魂穿", "身穿", "穿到", "醒来在", "异界", "transmigration", "isekai",
})
_REALM_PORTAL_VISUAL_RE = re.compile(
    r"时空裂缝|传送门|传送阵|秘境入口|遗迹入口|跨界门|裂缝|旋涡|漩涡|卷入|吸入|吞入|穿过|踏入|"
    r"portal|secret realm entrance|rift|vortex|gate",
    re.I,
)


def storyboard_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "storyboard.json")


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def missing(value: Any) -> bool:
    if value in (None, ""):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and not value:
        return True
    return False


def clip_id(clip: Dict[str, Any], index: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or clip.get("镜头") or f"clip#{index}")


def clip_blob(clip: Dict[str, Any]) -> str:
    """复杂镜头关键词检测只扫**散文描述**（label/scene/shots desc/video_prompt/template…），
    不扫结构化 `continuity` 块——它的 schema 字段名/枚举值（如 `eyeline` 字段、`transition:"eyeline"`）
    与 dialogue_shot_reverse 关键词 `eyeline` 撞名，会让**每个**合规 clip（formats §4 要求每 clip 填
    continuity.eyeline）误判成对话反打。三轨元数据同理：`dialogue_indices` 是对白分配账本，
    不代表该镜头是对话反打复杂镜。散文里真有 过肩/反打/对视/台词 仍会被正确命中。"""
    ignored = {
        "continuity",
        "dialogue_indices",
        "narration_indices",
        "screen_text_lines",
        "screen_text_policy",
    }
    scanned = {k: v for k, v in clip.items() if k not in ignored}
    return json.dumps(scanned, ensure_ascii=False, sort_keys=True)


def first_template_keyword_hit(text: str) -> Optional[str]:
    low = text.lower()
    for template, words in special_template_keywords():
        for word in words:
            token = str(word).lower().strip()
            if not token:
                continue
            # Short ASCII triggers such as "ots" must not fire inside schema
            # keys like "shots"; CJK triggers still use substring matching.
            if token.isascii() and re.fullmatch(r"[a-z0-9_+-]+", token):
                if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", low):
                    if template == "realm_portal" and token in _REALM_PORTAL_WEAK_TERMS and not _REALM_PORTAL_VISUAL_RE.search(text):
                        continue
                    return str(template)
            elif token in low:
                if template == "realm_portal" and token in _REALM_PORTAL_WEAK_TERMS and not _REALM_PORTAL_VISUAL_RE.search(text):
                    continue
                return str(template)
    return None


def duration_of(clip: Dict[str, Any]) -> Optional[float]:
    for key in ("duration", "duration_sec", "时长", "seconds"):
        value = clip.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            m = re.search(r"\d+(?:\.\d+)?", value)
            if m:
                return float(m.group(0))
    return None


def action_anchor_text(clip: Dict[str, Any]) -> str:
    """Text surface for deciding whether a clip is a long/heavy action chain."""
    parts: List[str] = []
    for key in (
        "id",
        "clip_id",
        "label",
        "scene",
        "description",
        "visual",
        "action",
        "template",
        "template_contract",
        "shots",
        "continuity",
    ):
        value = clip.get(key)
        if value is None:
            continue
        parts.append(json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value))
    return "\n".join(parts)


def action_anchor_chain(text: str) -> Dict[str, bool]:
    prep = bool(_ACTION_ANCHOR_PREP_RE.search(text))
    impact = bool(_ACTION_ANCHOR_IMPACT_RE.search(text))
    response = bool(_ACTION_ANCHOR_RESPONSE_RE.search(text))
    return {
        "prep": prep,
        "impact": impact,
        "response": response,
        "partial": impact and (prep or response),
        "full": prep and impact and response,
    }


def _listish(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        return [x.strip() for x in re.split(r"[,，、\s]+", value) if x.strip()]
    return []


def action_anchor_requirement(clip: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    template = str(clip.get("template") or "").strip()
    contract = clip.get("template_contract") if isinstance(clip.get("template_contract"), dict) else {}
    shot_type = str(clip.get("shot_type") or contract.get("template_id") or template).strip()
    risk_flags = set(_listish(clip.get("risk_flags"))) | set(_listish(contract.get("risk_flags")))
    text = action_anchor_text(clip)
    high_action = (
        template in HIGH_MOTION_TEMPLATES
        or shot_type in HIGH_MOTION_TEMPLATES
        or shot_type in ACTION_CHOREOGRAPHY_SHOT_TYPES
        or bool(risk_flags & ACTION_ANCHOR_RISK_FLAGS)
        or bool(_ACTION_ANCHOR_HEAVY_RE.search(text))
    )
    if not high_action:
        return None
    duration = duration_of(clip)
    chain = action_anchor_chain(text)
    long_clip = duration is not None and duration >= ACTION_ANCHOR_DURATION_SEC
    if not long_clip and not chain["partial"]:
        return None
    severity = "block" if (long_clip or chain["full"] or shot_type in ACTION_CHOREOGRAPHY_SHOT_TYPES) else "warn"
    reasons = []
    if long_clip:
        reasons.append(f"单镜时长 {duration:g}s >= {ACTION_ANCHOR_DURATION_SEC:g}s")
    if chain["full"]:
        reasons.append("含起手-命中-反应/收势完整动作链")
    elif chain["partial"]:
        reasons.append("含命中/接触及起手或反应动作链")
    return {"severity": severity, "reason": "；".join(reasons) or "重动作镜", "duration": duration, "chain": chain}


def add(rows: List[Dict[str, Any]], sev: str, dim: str, loc: str, msg: str) -> None:
    rows.append({"severity": sev, "dimension": dim, "loc": loc, "message": msg})


def check_contract_fields(rows: List[Dict[str, Any]], data: Dict[str, Any], path: str) -> None:
    vc = data.get("visual_contract")
    if not isinstance(vc, dict):
        add(rows, "block", "视觉契约", path, "storyboard.json 缺 visual_contract；分镜阶段必须先定色调、光位、轴线、状态和景别阶梯。")
    else:
        for field in VISUAL_CONTRACT_FIELDS:
            if missing(vc.get(field)):
                add(rows, "block", "视觉契约", path, f"visual_contract 缺字段或为空：{field}")

    sc = data.get("style_contract")
    if not isinstance(sc, dict):
        if isinstance(data.get("cinematic_contract"), dict):
            add(rows, "block", "基础视觉风格契约", path, "仍在使用旧 cinematic_contract；新分镜必须写 style_contract。")
        else:
            add(rows, "block", "基础视觉风格契约", path, "storyboard.json 缺 style_contract；基础视觉风格必须在分镜阶段结构化。")
    else:
        for field in STYLE_CONTRACT_FIELDS:
            if missing(sc.get(field)):
                add(rows, "block", "基础视觉风格契约", path, f"style_contract 缺字段或为空：{field}")


def check_template_contract(rows: List[Dict[str, Any]], clip: Dict[str, Any], loc: str) -> None:
    template = str(clip.get("template") or "").strip()
    contract = clip.get("template_contract")
    keyword_template = first_template_keyword_hit(clip_blob(clip))
    if not template:
        if isinstance(contract, dict):
            add(rows, "block", "专项镜头模板", loc, "有 template_contract 但缺 template；两者必须成对出现。")
        elif keyword_template:
            add(rows, "block", "专项镜头模板", loc, f"复杂镜头疑似 {keyword_template}，但缺 template/template_contract。")
        return
    if not isinstance(contract, dict):
        add(rows, "block", "专项镜头模板", loc, f"template={template} 但缺 template_contract。")
        return
    if str(contract.get("template_id") or "").strip() != template:
        add(rows, "block", "专项镜头模板", loc, f"template_contract.template_id 必须等于 template={template}。")
    required_fields = tuple(spectacle_required_fields(template)) or TEMPLATE_BASE_FIELDS
    for field in required_fields:
        if missing(contract.get(field)):
            add(rows, "block", "专项镜头模板", loc, f"template_contract 缺字段或为空：{field}")


def check_anchor_contract(rows: List[Dict[str, Any]], clip: Dict[str, Any], loc: str, enforce_midframe: bool) -> None:
    cont = clip.get("continuity")
    if not isinstance(cont, dict):
        add(rows, "block", "衔接契约", loc, "缺 continuity 块。")
        return
    for field in ("start_state", "end_state", "transition", "need_endframe"):
        if field not in cont:
            add(rows, "block", "衔接契约", loc, f"continuity 缺字段：{field}")
    mid = cont.get("midframe")
    anchors = cont.get("anchors")
    if enforce_midframe and mid is None and anchors is None and not cont.get("midframe_exempt_reason"):
        add(rows, "block", "中段锚帧", loc, "三帧契约默认强制：每镜必须有 continuity.midframe/anchors 或 midframe_exempt_reason；请跑 anchor_planner.py --write。")
    if mid is not None and anchors is not None:
        add(rows, "block", "中段锚帧", loc, "continuity.midframe 与 continuity.anchors 不能同时声明。")
        return
    req = action_anchor_requirement(clip)
    has_anchor_list = isinstance(anchors, list) and any(isinstance(a, dict) for a in anchors)
    if req and not has_anchor_list:
        if mid is not None:
            suffix = "当前只有 continuity.midframe；重动作/长动作链不能只靠单个 _mid。"
        else:
            suffix = "当前缺 continuity.anchors[]。"
        add(
            rows,
            str(req["severity"]),
            "重动作多中帧",
            loc,
            f"{req['reason']}，必须写 continuity.anchors[] 多中帧链；{suffix}请跑 skills/n2d-script/scripts/anchor_planner.py <作品根> <集> --write 后重跑 n2d-image。",
        )
    duration = duration_of(clip)
    anchor_rows: List[Tuple[int, Dict[str, Any], str, str, str]] = []
    if mid is not None:
        if not isinstance(mid, dict):
            add(rows, "block", "中段锚帧", loc, "continuity.midframe 必须是对象。")
        else:
            anchor_rows.append((1, mid, "midframe_png", "split_at_sec", "reason"))
    if anchors is not None:
        if not isinstance(anchors, list) or not anchors:
            add(rows, "block", "中段锚帧", loc, "continuity.anchors 必须是非空数组。")
        else:
            for idx, anchor in enumerate(anchors, 1):
                if isinstance(anchor, dict):
                    anchor_rows.append((idx, anchor, "anchor_png", "at_sec", "reason"))
                else:
                    add(rows, "block", "中段锚帧", loc, f"anchors[{idx}] 必须是对象。")
    prev = 0.0
    for idx, anchor, png_key, at_key, reason_key in anchor_rows:
        for field in (png_key, at_key, reason_key):
            if missing(anchor.get(field)):
                add(rows, "block", "中段锚帧", loc, f"锚帧 {idx} 缺字段或为空：{field}")
        at = anchor.get(at_key)
        if isinstance(at, bool) or not isinstance(at, (int, float)):
            if at not in (None, ""):
                add(rows, "block", "中段锚帧", loc, f"锚帧 {idx} 的 {at_key} 必须是数字。")
            continue
        if duration is not None and not (0 < float(at) < duration):
            add(rows, "block", "中段锚帧", loc, f"锚帧 {idx} 的 {at_key}={at} 必须落在 (0, duration={duration}) 内。")
        if float(at) <= prev:
            add(rows, "block", "中段锚帧", loc, f"锚帧 {idx} 的 {at_key}={at} 必须严格递增。")
        prev = max(prev, float(at))


def validate(root: str, ep: str) -> Dict[str, Any]:
    path = storyboard_path(root, ep)
    rows: List[Dict[str, Any]] = []
    if not os.path.isfile(path):
        add(rows, "block", "故事板", path, "缺 storyboard.json。")
        return {"ok": False, "findings": rows}
    try:
        data = load_json(path)
    except Exception as exc:
        add(rows, "block", "故事板", path, f"storyboard.json 不可解析：{type(exc).__name__}: {exc}")
        return {"ok": False, "findings": rows}
    if not isinstance(data, dict):
        add(rows, "block", "故事板", path, "storyboard.json 顶层必须是对象。")
        return {"ok": False, "findings": rows}
    check_contract_fields(rows, data, path)
    clips = data.get("clips")
    if not isinstance(clips, list) or not clips:
        add(rows, "block", "故事板", path, "storyboard.json 缺非空 clips[]。")
        return {"ok": False, "findings": rows}
    policy = data.get("policy") if isinstance(data.get("policy"), dict) else {}
    enforce_midframe = backend_supports_three_plus_frames(policy.get("video_backend"))
    for index, clip in enumerate(clips, 1):
        if not isinstance(clip, dict):
            add(rows, "block", "故事板", f"{path} clip#{index}", "clip 必须是对象。")
            continue
        loc = f"{path} {clip_id(clip, index)}"
        # 镜头时长是 storyboard-driven（原生音画）下 finalize/出视频的唯一时间预算来源；
        # 缺 duration 的 clip 会在 finalize 里被静默丢成 0 长 → 无时间预算出视频。这里硬拦。
        if duration_of(clip) is None:
            add(rows, "block", "镜头时长", loc, "clip 缺可解析的 duration（duration/duration_sec/时长/seconds 之一）；原生音画下镜头时长靠它定时间预算，分镜设计时必须填 Clip duration。")
        check_template_contract(rows, clip, loc)
        check_anchor_contract(rows, clip, loc, enforce_midframe)
    return {"ok": not any(r["severity"] == "block" for r in rows), "findings": rows}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Validate storyboard visual/style/template/midframe contracts")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = validate(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"=== storyboard 契约校验 {ns.episode} ===")
        if not res["findings"]:
            print("  ✅ visual_contract / style_contract / template_contract / 中段锚帧契约通过")
        for row in res["findings"]:
            marker = "⛔" if row["severity"] == "block" else "⚠️"
            print(f"  {marker} [{row['dimension']}] {row['loc']}: {row['message']}")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
