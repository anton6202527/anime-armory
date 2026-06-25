#!/usr/bin/env python3
"""Video-side semantic embedding consistency reader.

External DINO/CLIP/DreamSim runners can write per-clip subject/background
similarities. This checker bands those sidecar metrics into review findings.
"""
from __future__ import annotations

import os
from typing import List, Optional

from video_consistency_common import existing_media, finding, load_first_json, rows_from, story_text, verdict_from


REPORT_RELS = (
    os.path.join("生产数据", "video_semantic_consistency_{ep}.json"),
    os.path.join("生产数据", "video_embedding_consistency_{ep}.json"),
    os.path.join("生产数据", "video_dreamsim_consistency_{ep}.json"),
    os.path.join("出视频", "{ep}", "video_semantic_consistency.json"),
    os.path.join("合成", "{ep}", "video_semantic_consistency.json"),
)


def _float(row: dict, *keys: str) -> Optional[float]:
    for key in keys:
        try:
            return float(row.get(key))
        except (TypeError, ValueError):
            continue
    return None


def _floor(data: object, key: str, default: float) -> float:
    if isinstance(data, dict):
        try:
            return float(data.get(key))
        except (TypeError, ValueError):
            pass
    return default


def analyze(root: str, ep: str) -> dict:
    data, rel = load_first_json(root, tuple(r.format(ep=ep) for r in REPORT_RELS))
    if data is None:
        if existing_media(root, ep) and story_text(root, ep).strip():
            return {
                "available": True,
                "findings": [finding(
                    "warn",
                    "本集已有视频产物和脚本/视频契约，但缺 video_semantic_consistency；无法核验视频侧主体/背景语义是否随视频生成漂移。",
                    stage="video",
                    artifacts=("生产数据/video_semantic_consistency_{ep}.json".format(ep=ep),),
                    evidence_missing=True,
                    required_evidence="video_semantic_consistency",
                )],
                "notes": [],
            }
        return {
            "available": False,
            "findings": [],
            "notes": ["未找到 video_semantic_consistency sidecar；视频侧 DINO/CLIP/DreamSim 语义一致性跳过。"],
        }

    subject_floor = _floor(data, "subject_similarity_floor", 0.55)
    subject_warn = _floor(data, "subject_similarity_warn", max(0.0, subject_floor + 0.08))
    bg_floor = _floor(data, "background_similarity_floor", 0.45)
    bg_warn = _floor(data, "background_similarity_warn", max(0.0, bg_floor + 0.08))

    findings: List[dict] = []
    for row in rows_from(data, ("findings", "segments", "checks", "items", "results")):
        explicit = verdict_from(row)
        shot = row.get("clip") or row.get("shot") or row.get("clip_id") or row.get("segment")
        if explicit in {"block", "warn"}:
            findings.append(finding(
                explicit,
                str(row.get("message") or row.get("reason") or "视频语义一致性报告未通过"),
                shot=shot,
                stage=str(row.get("return_to_stage") or "video"),
                artifacts=(rel,),
                subject_similarity=row.get("subject_similarity"),
                background_similarity=row.get("background_similarity"),
            ))
            continue
        subject = _float(row, "subject_similarity", "identity_similarity", "object_similarity")
        if subject is not None and subject < subject_warn:
            verdict = "block" if subject < subject_floor else "warn"
            findings.append(finding(
                verdict,
                f"视频侧主体语义相似度偏低：{subject:.3f}（warn<{subject_warn:.2f}, block<{subject_floor:.2f}）。",
                shot=shot,
                stage="video",
                artifacts=(rel,),
                subject_similarity=subject,
            ))
        bg = _float(row, "background_similarity", "scene_similarity", "location_similarity")
        if bg is not None and bg < bg_warn:
            verdict = "block" if bg < bg_floor else "warn"
            findings.append(finding(
                verdict,
                f"视频侧背景/场景语义相似度偏低：{bg:.3f}（warn<{bg_warn:.2f}, block<{bg_floor:.2f}）。",
                shot=shot,
                stage="video",
                artifacts=(rel,),
                background_similarity=bg,
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
