#!/usr/bin/env python3
"""Subject-to-video consistency checker.

This complements image-side face/outfit checks with video-side subject fidelity,
naturalness, text relevance, and subject/background disentanglement.
"""
from __future__ import annotations

import os
from typing import List, Optional

from video_consistency_common import existing_media, finding, load_first_json, load_json, rows_from, story_text, verdict_from


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
    findings: List[dict] = []
    for row in rows_from(data, ("findings", "subjects", "checks", "items", "results")):
        explicit = verdict_from(row)
        shot = row.get("clip") or row.get("shot") or row.get("clip_id")
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
            findings.append(finding(
                "block" if hard and value < floor * 0.75 else "warn",
                f"{message}：{value:.3f}（min={floor:.2f}）。",
                shot=shot,
                stage="video",
                artifacts=(rel,),
                subject=subject,
                category=row.get("category"),
                **{key: value},
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
