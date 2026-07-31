#!/usr/bin/env python3
"""Subject-to-video consistency checker.

This complements image-side face/outfit checks with video-side subject fidelity,
naturalness, text relevance, and subject/background disentanglement.
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import List, Optional, Set

from video_consistency_common import existing_media, finding, load_first_json, load_json, rows_from, story_text, verdict_from

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
try:
    import n2d_spectacle as _spec  # 动作 beat 识别单一真值源（与 script/gate 共用 ACTION_BEAT_LEXICON）
except Exception:  # pragma: no cover - _lib 不可用时优雅退化（仅失去 storyboard 派生信号）
    _spec = None  # type: ignore[assignment]


REPORT_RELS = (
    os.path.join("生产数据", "subject_video_consistency_{ep}.json"),
    os.path.join("生产数据", "s2v_consistency_{ep}.json"),
    os.path.join("出视频", "{ep}", "subject_video_consistency.json"),
    os.path.join("合成", "{ep}", "subject_video_consistency.json"),
)


def _float(row: dict, key: str) -> Optional[float]:
    try:
        return float(row.get(key))
    except (TypeError, ValueError):
        return None


def _floor(data: object, key: str, default: float) -> float:
    if isinstance(data, dict):
        try:
            return float(data.get(key))
        except (TypeError, ValueError):
            pass
    return default


def _clip_num(value: object) -> Optional[int]:
    s = str(value or "")
    m = re.search(r"(?:Clip|片段|镜头?|shot)\s*[_\- ]?\s*0*([0-9]+)", s, re.I) or re.search(r"0*([0-9]+)", s)
    return int(m.group(1)) if m else None


_ACTION_ROW_KEYS = ("action_beat", "high_motion", "high_action")
_ACTION_TRUTHY = {"true", "1", "yes", "高", "大", "high", "strong", "激烈"}


def _is_action_row(row: dict) -> bool:
    """sidecar 行自带的动作/高动态信号（runner 最知情）。"""
    for k in _ACTION_ROW_KEYS:
        v = row.get(k)
        if v is True or str(v).strip().lower() in _ACTION_TRUTHY:
            return True
    mi = row.get("motion_intensity")
    try:
        if mi is not None and float(mi) >= 0.6:
            return True
    except (TypeError, ValueError):
        pass
    return False


def relax_action_fidelity(verdict: str, is_action: bool) -> str:
    """动作/高动态镜：主体形变属预期，subject_fidelity 硬 block 降 warn（仍 surface·不强制重出）。
    根治「一致性度量偏好静止→闸门压向静帧/PPT 感」（Survey 2504.16081）。纯函数·可测。"""
    return "warn" if verdict == "block" and is_action else verdict


def _high_motion_clips(root: str, ep: str) -> Set[int]:
    """storyboard 派生的高动态/动作 beat clip 号集合（行级无 flag 时的兜底信号）。
    用 n2d_spectacle.action_beat_categories 命中 attack/block/counter/impact，或 meta 动态=高。"""
    out: Set[int] = set()
    sb_path = os.path.join(root, "脚本", ep, "storyboard.json")
    try:
        sb = json.load(open(sb_path, encoding="utf-8"))
    except Exception:
        return out
    for idx, clip in enumerate(sb.get("clips") or [], start=1):
        if not isinstance(clip, dict):
            continue
        meta = clip.get("meta") if isinstance(clip.get("meta"), dict) else {}
        text = " ".join(str(clip.get(k) or "") for k in ("shot_description", "description", "action", "动作", "镜头描述"))
        is_action = bool(_spec.action_beat_categories(text)) if _spec is not None else False
        mv = str(meta.get("motion") or meta.get("motion_intensity") or meta.get("动态") or "").strip().lower()
        if mv in _ACTION_TRUTHY or meta.get("high_action") is True or meta.get("action_beat"):
            is_action = True
        if is_action:
            num = _clip_num(clip.get("clip_id") or clip.get("id")) or idx
            out.add(num)
    return out


def _has_subject_contract(root: str, ep: str) -> bool:
    registry = load_json(os.path.join(root, "出图", "共享", "identity_registry.json"))
    if registry:
        return True
    text = story_text(root, ep)
    return "CHAR_" in text or "character_id" in text or "角色" in text


def analyze(root: str, ep: str) -> dict:
    data, rel = load_first_json(root, tuple(r.format(ep=ep) for r in REPORT_RELS))
    if data is None:
        if _has_subject_contract(root, ep) and existing_media(root, ep):
            return {
                "available": True,
                "findings": [finding(
                    "warn",
                    "本集已有主体/角色契约和视频产物，但缺 subject_video_consistency；无法核验视频侧主体保真、多主体串脸、自然度和背景解耦。",
                    stage="video",
                    artifacts=("生产数据/subject_video_consistency_{ep}.json".format(ep=ep),),
                    evidence_missing=True,
                    required_evidence="subject_video_consistency",
                )],
                "notes": [],
            }
        return {
            "available": False,
            "findings": [],
            "notes": ["未找到 subject_video_consistency sidecar；S2V 主体一致性检查跳过。"],
        }

    fidelity_min = _floor(data, "subject_fidelity_min", 0.60)
    natural_min = _floor(data, "naturalness_min", 0.50)
    text_min = _floor(data, "text_relevance_min", 0.55)
    bg_min = _floor(data, "background_disentanglement_min", 0.50)
    high_motion = _high_motion_clips(root, ep)  # 动作 beat 镜：主体形变属预期，松 subject_fidelity 硬 block
    findings: List[dict] = []
    for row in rows_from(data, ("findings", "subjects", "checks", "items", "results")):
        explicit = verdict_from(row)
        shot = row.get("clip") or row.get("shot") or row.get("clip_id")
        is_action = _is_action_row(row) or (_clip_num(shot) in high_motion)
        subject = row.get("subject") or row.get("subject_id") or row.get("character_id") or row.get("asset_id")
        if explicit in {"block", "warn"}:
            findings.append(finding(
                explicit,
                str(row.get("message") or row.get("reason") or "S2V 主体一致性报告未通过"),
                shot=shot,
                stage=str(row.get("return_to_stage") or "video"),
                artifacts=(rel,),
                subject=subject,
                category=row.get("category"),
            ))
            continue
        metrics = (
            ("subject_fidelity", fidelity_min, "主体参考保真度偏低", True),
            ("naturalness", natural_min, "主体自然度偏低", False),
            ("text_relevance", text_min, "主体与文本/动作相关性偏低", False),
            ("background_disentanglement", bg_min, "主体与背景解耦不足，可能被背景吞并或串色", False),
        )
        for key, floor, message, hard in metrics:
            value = _float(row, key)
            if value is None or value >= floor:
                continue
            verdict = "block" if hard and value < floor * 0.75 else "warn"
            kw = {key: value}
            suffix = ""
            if key == "subject_fidelity" and is_action:
                relaxed = relax_action_fidelity(verdict, True)
                if relaxed != verdict:
                    verdict = relaxed
                    kw["action_beat_relaxed"] = True
                    suffix = "（动作/高动态镜，主体形变属预期 → block 降 warn 人核对，不强制重出）"
            findings.append(finding(
                verdict,
                f"{message}：{value:.3f}（min={floor:.2f}）。{suffix}",
                shot=shot,
                stage="video",
                artifacts=(rel,),
                subject=subject,
                category=row.get("category"),
                **kw,
            ))
        if row.get("multi_subject_swap") is True or str(row.get("multi_subject_swap")).lower() in {"true", "1", "yes"}:
            findings.append(finding(
                "block",
                "多主体视频出现身份/主体槽位串换。",
                shot=shot,
                stage="video",
                artifacts=(rel,),
                subject=subject,
                category=row.get("category") or "multi_subject",
            ))
    return {"available": True, "findings": findings, "notes": []}


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ns = ap.parse_args()
    print(json.dumps(analyze(ns.root, ns.episode), ensure_ascii=False, indent=2))
