#!/usr/bin/env python3
"""Story economy audit for n2d storyboard clips.

The goal is to stop weak information from becoming expensive long videos.
It classifies each story_clip by production value, assigns a target story
runtime, and tells script/video stages whether to compress, merge, narrate, or
keep detailed coverage before paid video generation.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

KIND = "n2d_story_economy_audit"
VERSION = 1

COMBAT_RE = re.compile(
    r"(fight_exchange|combat|打斗|斗法|交锋|命中|击中|挥刀|拔刀|格挡|扑杀|弹爪|狼爪|"
    r"法术|武技|追逐|冲撞|杀了她)"
)
NEGATED_GENERIC_COMBAT_RE = re.compile(r"(不|未|无需|不要|别).{0,16}(打斗|斗法|交锋)")
EMOTION_RE = re.compile(
    r"(relationship_turn|emotional_exchange|情感|感情|男女主|表白|亲密|拥抱|接吻|"
    r"心动|诀别|和解|信任|背叛|强情绪|情绪峰)"
)
SELECTIVE_RE = re.compile(
    r"(reveal_reaction_chain|public_confrontation|dialogue_shot_reverse|揭示|真相|身份|"
    r"宣判|问名|登场|正主|压场|危机|钩|集尾|冷开|反转|爽点|误认|求援)"
)
EXPOSITION_RE = re.compile(
    r"(解释|交代|情报|背景|路引|户籍|前情|危机说清|报出|代价压实|旁白|"
    r"信息|规则|身份死局|上盘村|狼妖危机|公务在身)"
)
TRAVEL_RE = re.compile(r"(返村路|官道|马队|骑|马蹄|赶路|路上|行进|远景|落幅|蒙太奇)")
ORDINARY_RE = re.compile(r"(普通反应|沉默|站在原地|一句话也没说|反应|气氛|氛围|过渡|桥接)")
NARRATION_RE = re.compile(r"(旁白[:：]|narration|voiceover)", re.I)

TARGETS = {
    "premium_detail": (8.0, 15.0),
    "selective_detail": (5.0, 8.0),
    "compact_story": (3.0, 6.0),
    "montage_bridge": (3.0, 6.0),
    "micro_reaction": (2.0, 4.0),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def ep_label(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = re.search(r"\d+", text)
    return f"第{m.group(0)}集" if m else text


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


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(str(k) + " " + flatten(v) for k, v in value.items())
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    return str(value or "")


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}")


def duration_of(clip: Mapping[str, Any]) -> Optional[float]:
    for key in ("duration", "duration_sec", "story_duration", "seconds", "时长"):
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


def storyboard(root: Path, ep: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    path = root / "脚本" / ep / "storyboard.json"
    data = load_json(path)
    if not isinstance(data, Mapping):
        return [], f"缺 storyboard.json 或 JSON 不可解析：{path}"
    clips = data.get("clips")
    if not isinstance(clips, list) or not clips:
        return [], "storyboard.json 缺非空 clips[]"
    return [c for c in clips if isinstance(c, dict)], None


def story_blob(clip: Mapping[str, Any]) -> str:
    keys = (
        "id",
        "label",
        "rhythm",
        "template",
        "dramatic_function",
        "audience_effect",
        "spectacle_story_function",
        "pacing_role",
        "runtime_priority",
        "description",
        "visual",
        "native_speech",
        "voiceover_lines",
        "subtitle_lines",
        "narration_lines",
        "dialogue_lines",
    )
    parts = [flatten(clip.get(k)) for k in keys if k in clip]
    cont = clip.get("continuity")
    if isinstance(cont, Mapping):
        parts.append(flatten({k: cont.get(k) for k in ("start_state", "end_state", "shot_size") if k in cont}))
    for shot in clip.get("shots") or []:
        if isinstance(shot, Mapping):
            parts.append(flatten({k: shot.get(k) for k in ("desc", "description", "action", "line") if k in shot}))
    return "\n".join(p for p in parts if p)


def _count_list(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def narration_weight(clip: Mapping[str, Any], blob: str) -> float:
    narration_count = _count_list(clip.get("narration_indices")) + _count_list(clip.get("narration_lines"))
    dialogue_count = _count_list(clip.get("dialogue_indices")) + _count_list(clip.get("dialogue_lines"))
    narration_hits = len(NARRATION_RE.findall(blob))
    total = narration_count + dialogue_count + narration_hits
    if total <= 0:
        return 0.0
    return (narration_count + narration_hits) / total


def manual_target_range(value: Any) -> Optional[Tuple[float, float]]:
    if isinstance(value, Mapping):
        lo = value.get("min")
        hi = value.get("max")
        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and lo > 0 and hi >= lo:
            return float(lo), float(hi)
    if isinstance(value, str):
        nums = [float(m.group(0)) for m in re.finditer(r"\d+(?:\.\d+)?", value)]
        if len(nums) >= 2 and nums[0] > 0 and nums[1] >= nums[0]:
            return nums[0], nums[1]
    return None


def classify_clip(clip: Mapping[str, Any], idx: int, total: int) -> Dict[str, Any]:
    blob = story_blob(clip)
    template = str(clip.get("template") or "")
    duration = duration_of(clip)
    signals: List[str] = []
    manual_intent = str(clip.get("economy_intent") or clip.get("story_economy_intent") or "").strip()

    combat_hits = [m.group(0) for m in COMBAT_RE.finditer(blob)]
    is_combat = bool(combat_hits)
    if is_combat and NEGATED_GENERIC_COMBAT_RE.search(blob):
        specific_hits = [h for h in combat_hits if h not in {"打斗", "斗法", "交锋"}]
        if not specific_hits:
            is_combat = False
    is_emotion = bool(EMOTION_RE.search(blob))
    is_selective = bool(SELECTIVE_RE.search(blob)) or idx in (1, total)
    is_exposition = bool(EXPOSITION_RE.search(blob))
    is_travel = bool(TRAVEL_RE.search(blob))
    is_ordinary = bool(ORDINARY_RE.search(blob))
    narr_ratio = narration_weight(clip, blob)

    for flag, name in (
        (is_combat, "combat_or_action"),
        (is_emotion, "emotional_turn"),
        (is_selective, "selective_reveal_or_hook"),
        (is_exposition, "exposition"),
        (is_travel, "travel_or_establishing"),
        (is_ordinary, "ordinary_reaction_or_bridge"),
    ):
        if flag:
            signals.append(name)
    if narr_ratio >= 0.55:
        signals.append("narration_heavy")

    if is_combat or is_emotion:
        economy_class = "premium_detail"
        detail_allowed = True
        reason = "战斗/动作或强情绪交流可详拍，但仍拆为 4-8s video_shot。"
    elif is_selective:
        economy_class = "selective_detail"
        detail_allowed = False
        reason = "揭示/对质/冷开/集尾可保留辨识度，但不应铺成 20s+ 长段。"
    elif is_travel:
        economy_class = "montage_bridge"
        detail_allowed = False
        reason = "行进/换场/建立关系适合蒙太奇或少量关键画面，不宜长拍。"
    elif is_exposition or narr_ratio >= 0.55:
        economy_class = "compact_story"
        detail_allowed = False
        reason = "解释/情报/旁白信息应压成短镜、道具细节或一句旁白。"
    elif is_ordinary:
        economy_class = "micro_reaction"
        detail_allowed = False
        reason = "普通反应只保留能改变观众判断的一瞬。"
    else:
        economy_class = "compact_story"
        detail_allowed = False
        reason = "未证明需要详拍，默认按紧凑信息镜处理。"

    if manual_intent in TARGETS:
        economy_class = manual_intent
        detail_allowed = manual_intent == "premium_detail"
        reason = f"storyboard 明确 economy_intent={manual_intent}；仍按对应时长预算审查。"
        signals.append("manual_economy_intent")

    t_min, t_max = TARGETS[economy_class]
    manual_target = manual_target_range(clip.get("target_story_clip_sec") or clip.get("economy_target_sec"))
    if manual_target:
        t_min, t_max = manual_target
        signals.append("manual_target_story_clip_sec")
    over_budget = None if duration is None else max(0.0, duration - t_max)
    hard_max = 35.0 if detail_allowed else (15.0 if economy_class == "selective_detail" else 12.0)
    severity = "pass"
    code = ""
    if duration is not None and duration > hard_max:
        severity = "block"
        code = "non_premium_story_clip_too_long" if not detail_allowed else "premium_story_clip_extreme_long"
    elif duration is not None and duration > t_max:
        severity = "warn"
        code = "story_clip_over_economy_target"

    if detail_allowed:
        action = "keep_detail_but_split_video_shots" if duration and duration > 12 else "keep_detail"
        demo = "保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。"
    elif economy_class == "montage_bridge":
        action = "merge_or_montage_before_video"
        demo = "改成 3-6s 蒙太奇：建立镜一闪 + 关键道具/动作特写 + 目的地落幅。"
    elif economy_class == "micro_reaction":
        action = "compress_to_reaction_insert"
        demo = "改成 2-4s 反应插入：一个眼神/手部/沉默落点即可，不单独讲完整段落。"
    elif economy_class == "selective_detail":
        action = "trim_to_selective_detail"
        demo = "改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。"
    else:
        action = "compress_or_narrate_before_video"
        demo = "改成 3-6s：一句旁白承载信息，画面只拍能改变局势的物件/表情/动作。"

    return {
        "economy_class": economy_class,
        "detail_allowed": detail_allowed,
        "detail_reason": reason,
        "signals": signals,
        "narration_weight": round(narr_ratio, 3),
        "target_story_clip_sec": {"min": t_min, "max": t_max},
        "recommended_video_shot_sec": {"min": 4.0, "max": 8.0},
        "hard_max_story_clip_sec": hard_max,
        "over_budget_sec": round(over_budget, 3) if over_budget is not None else None,
        "recommended_action": action,
        "rewrite_demo": demo,
        "finding": {"severity": severity, "code": code} if code else {"severity": severity},
        "template": template,
    }


def build_report(root: Path, ep: str) -> Dict[str, Any]:
    ep = ep_label(ep)
    clips, err = storyboard(root, ep)
    if err:
        return {
            "kind": KIND,
            "version": VERSION,
            "episode": ep,
            "generated_at": now_iso(),
            "ok": False,
            "summary": {"clips": 0, "blocks": 1, "warnings": 0},
            "clips": [],
            "findings": [{"severity": "block", "code": "missing_storyboard", "message": err}],
        }

    rows: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    total_duration = 0.0
    target_min_total = 0.0
    target_max_total = 0.0
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip, idx)
        duration = duration_of(clip)
        audit = classify_clip(clip, idx, len(clips))
        target = audit["target_story_clip_sec"]
        if duration is not None:
            total_duration += duration
        target_min_total += float(target["min"])
        target_max_total += float(target["max"])
        row = {
            "clip": cid,
            "label": clip.get("label", ""),
            "duration_sec": duration,
            **audit,
        }
        rows.append(row)
        f = audit.get("finding") or {}
        sev = f.get("severity")
        code = f.get("code")
        if sev in {"warn", "block"} and code:
            target_text = f"{target['min']:g}-{target['max']:g}s"
            findings.append({
                "severity": sev,
                "code": code,
                "clip": cid,
                "message": (
                    f"{cid} 当前 {duration:g}s，分类={audit['economy_class']}，建议 {target_text}；"
                    f"{audit['recommended_action']}。{audit['rewrite_demo']}"
                ),
            })

    blocks = sum(1 for f in findings if f.get("severity") == "block")
    warnings = sum(1 for f in findings if f.get("severity") == "warn")
    potential_savings = sum(
        max(0.0, float(row.get("duration_sec") or 0.0) - float((row.get("target_story_clip_sec") or {}).get("max") or 0.0))
        for row in rows
    )
    summary = {
        "clips": len(rows),
        "total_duration_sec": round(total_duration, 3),
        "target_total_min_sec": round(target_min_total, 3),
        "target_total_max_sec": round(target_max_total, 3),
        "potential_savings_sec": round(potential_savings, 3),
        "rewrite_required": sum(1 for row in rows if float(row.get("over_budget_sec") or 0.0) > 0.0),
        "premium_detail": sum(1 for row in rows if row.get("economy_class") == "premium_detail"),
        "compact_or_montage": sum(1 for row in rows if row.get("economy_class") in {"compact_story", "montage_bridge", "micro_reaction"}),
        "blocks": blocks,
        "warnings": warnings,
    }
    return {
        "kind": KIND,
        "version": VERSION,
        "episode": ep,
        "generated_at": now_iso(),
        "ok": blocks == 0,
        "summary": summary,
        "clips": rows,
        "findings": findings,
        "rules": [
            "默认把秒数还给战斗/动作、男女主或核心人物强情绪交流、真正反转/集尾钩。",
            "解释、行进、普通反应、情报交代优先压成 2-6s，或并入相邻强戏。",
            "长 story_clip 若不值得详拍，不应先拆成多个视频段烧额度；应先回 n2d-script 压缩剧情表达。",
        ],
    }


def render_md(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = [
        "# 剧情经济性审查",
        "",
        f"- episode: {report.get('episode')}",
        f"- ok: {report.get('ok')}",
        f"- total_duration_sec: {s.get('total_duration_sec')}",
        f"- target_total_max_sec: {s.get('target_total_max_sec')}",
        f"- potential_savings_sec: {s.get('potential_savings_sec')}",
        "",
        "| Clip | Dur | Class | Target | Action | Demo |",
        "|---|---:|---|---:|---|---|",
    ]
    for row in report.get("clips") or []:
        dur = row.get("duration_sec")
        dur_text = f"{float(dur):.3f}s" if isinstance(dur, (int, float)) else ""
        target = row.get("target_story_clip_sec") or {}
        target_text = f"{target.get('min', '')}-{target.get('max', '')}s"
        lines.append(
            f"| {row.get('clip')} | {dur_text} | {row.get('economy_class')} | "
            f"{target_text} | {row.get('recommended_action')} | {row.get('rewrite_demo')} |"
        )
    findings = report.get("findings") or []
    if findings:
        lines.extend(["", "## Findings", ""])
        for f in findings:
            lines.append(f"- {str(f.get('severity')).upper()} {f.get('clip') or ''} {f.get('code')}: {f.get('message')}")
    lines.extend(["", "## Rules", ""])
    for rule in report.get("rules") or []:
        lines.append(f"- {rule}")
    return "\n".join(lines)


def write_outputs(root: Path, ep: str, report: Mapping[str, Any]) -> Tuple[Path, Path]:
    out = root / "生产数据"
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"story_economy_audit_{ep}.json"
    md_path = out / f"story_economy_audit_{ep}.md"
    write_atomic(json_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_atomic(md_path, render_md(report) + "\n")
    return json_path, md_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d story economy audit")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 when non-premium story clips are materially over budget")
    ns = ap.parse_args(argv)
    root = Path(ns.root.rstrip("/"))
    ep = ep_label(ns.episode)
    report = build_report(root, ep)
    if ns.write:
        jp, mp = write_outputs(root, ep, report)
        report = {**report, "outputs": {"json": str(jp), "markdown": str(mp)}}
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_md(report))
    if ns.strict and not report.get("ok", False):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
