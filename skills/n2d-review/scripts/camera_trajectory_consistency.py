#!/usr/bin/env python3
"""Camera/spatial trajectory consistency checker for video clips."""
from __future__ import annotations

import os
from typing import List, Optional

from video_consistency_common import contains_any, existing_media, finding, load_first_json, rows_from, story_text, verdict_from


REPORT_RELS = (
    os.path.join("生产数据", "camera_trajectory_probe_{ep}.json"),
    os.path.join("生产数据", "camera_spatial_trajectory_{ep}.json"),
    os.path.join("出视频", "{ep}", "camera_trajectory_probe.json"),
    os.path.join("合成", "{ep}", "camera_trajectory_probe.json"),
)

CAMERA_WORDS = (
    "推镜", "拉镜", "摇镜", "移镜", "跟拍", "环绕", "绕行", "上摇", "下摇", "升降", "穿过",
    "向左", "向右", "画左", "画右", "越轴", "镜头运动", "camera", "dolly", "pan", "tilt",
    "tracking", "orbit", "crane", "push in", "pull out",
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


def analyze(root: str, ep: str) -> dict:
    data, rel = load_first_json(root, tuple(r.format(ep=ep) for r in REPORT_RELS))
    if data is None:
        if contains_any(story_text(root, ep), CAMERA_WORDS) and existing_media(root, ep):
            return {
                "available": True,
                "findings": [finding(
                    "warn",
                    "视频含明确镜头运动/空间轨迹，但缺 camera_trajectory_probe；无法核验运动方向、深度、越轴和抖动连续性。",
                    stage="video",
                    artifacts=("生产数据/camera_trajectory_probe_{ep}.json".format(ep=ep),),
                    evidence_missing=True,
                    required_evidence="camera_trajectory_probe",
                )],
                "notes": [],
            }
        return {
            "available": False,
            "findings": [],
            "notes": ["未找到 camera_trajectory_probe sidecar；相机/空间轨迹一致性跳过。"],
        }

    max_error = _floor(data, "trajectory_error_max", 0.32)
    warn_error = _floor(data, "trajectory_error_warn", max_error * 0.75)
    max_jitter = _floor(data, "jitter_score_max", 0.40)
    warn_jitter = _floor(data, "jitter_score_warn", max_jitter * 0.75)

    findings: List[dict] = []
    for row in rows_from(data, ("findings", "segments", "shots", "checks", "items", "results")):
        explicit = verdict_from(row)
        shot = row.get("clip") or row.get("shot") or row.get("clip_id") or row.get("segment")
        if explicit in {"block", "warn"}:
            findings.append(finding(
                explicit,
                str(row.get("message") or row.get("reason") or "相机/空间轨迹报告未通过"),
                shot=shot,
                stage=str(row.get("return_to_stage") or "video"),
                artifacts=(rel,),
            ))
            continue
        if str(row.get("axis_flip") or row.get("crossed_axis") or "").lower() in {"true", "1", "yes"}:
            findings.append(finding("block", "相机运动出现越轴/屏幕方向翻转。", shot=shot, stage="video", artifacts=(rel,)))
        if str(row.get("depth_flip") or "").lower() in {"true", "1", "yes"}:
            findings.append(finding("warn", "相机深度运动方向与设计不一致。", shot=shot, stage="video", artifacts=(rel,)))
        err = _float(row, "trajectory_error")
        if err is not None and err > warn_error:
            findings.append(finding(
                "block" if err > max_error else "warn",
                f"相机轨迹偏差过高：{err:.3f}（warn>{warn_error:.2f}, block>{max_error:.2f}）。",
                shot=shot,
                stage="video",
                artifacts=(rel,),
                trajectory_error=err,
            ))
        jitter = _float(row, "jitter_score")
        if jitter is not None and jitter > warn_jitter:
            findings.append(finding(
                "block" if jitter > max_jitter else "warn",
                f"相机运动抖动/漂移过高：{jitter:.3f}（warn>{warn_jitter:.2f}, block>{max_jitter:.2f}）。",
                shot=shot,
                stage="video",
                artifacts=(rel,),
                jitter_score=jitter,
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
