#!/usr/bin/env python3
"""Motion smoothness / dynamic degree consistency checker."""
from __future__ import annotations

import os
from typing import List, Optional

from video_consistency_common import contains_any, existing_media, finding, load_first_json, rows_from, story_text, verdict_from


REPORT_RELS = (
    os.path.join("生产数据", "motion_quality_{ep}.json"),
    os.path.join("生产数据", "motion_smoothness_{ep}.json"),
    os.path.join("出视频", "{ep}", "motion_quality.json"),
    os.path.join("合成", "{ep}", "motion_quality.json"),
)

MOTION_WORDS = (
    "奔跑", "冲向", "转身", "挥剑", "挥刀", "打斗", "追逐", "飞出", "掉落", "旋转", "跳起",
    "镜头推进", "跟拍", "动作", "motion", "run", "fight", "chase", "jump", "turn", "swing",
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
        if contains_any(story_text(root, ep), MOTION_WORDS) and existing_media(root, ep):
            return {
                "available": True,
                "findings": [finding(
                    "warn",
                    "视频含明确动作/运动镜，但缺 motion_quality 报告；无法核验冻结、抽搐、速度突变和动作完成度。",
                    stage="video",
                    artifacts=("生产数据/motion_quality_{ep}.json".format(ep=ep),),
                )],
                "notes": [],
            }
        return {
            "available": False,
            "findings": [],
            "notes": ["未找到 motion_quality sidecar；运动平滑/动态度检查跳过。"],
        }

    min_smoothness = _floor(data, "motion_smoothness_min", 0.55)
    min_dynamic = _floor(data, "dynamic_degree_min", 0.18)
    max_freeze = _floor(data, "freeze_ratio_max", 0.28)
    max_jerk = _floor(data, "jerk_score_max", 0.42)
    min_completion = _floor(data, "action_completion_min", 0.55)
    findings: List[dict] = []
    for row in rows_from(data, ("findings", "shots", "segments", "checks", "items", "results")):
        explicit = verdict_from(row)
        shot = row.get("clip") or row.get("shot") or row.get("clip_id") or row.get("segment")
        if explicit in {"block", "warn"}:
            findings.append(finding(
                explicit,
                str(row.get("message") or row.get("reason") or "运动质量报告未通过"),
                shot=shot,
                stage=str(row.get("return_to_stage") or "video"),
                artifacts=(rel,),
            ))
            continue
        smoothness = _float(row, "motion_smoothness")
        if smoothness is not None and smoothness < min_smoothness:
            findings.append(finding(
                "block" if smoothness < min_smoothness * 0.75 else "warn",
                f"运动平滑度偏低：{smoothness:.3f}（min={min_smoothness:.2f}）。",
                shot=shot,
                stage="video",
                artifacts=(rel,),
                motion_smoothness=smoothness,
            ))
        dynamic = _float(row, "dynamic_degree")
        if dynamic is not None and dynamic < min_dynamic and str(row.get("expected_motion") or row.get("intended_motion") or "").strip():
            findings.append(finding(
                "warn",
                f"设计为动作镜但动态度偏低：{dynamic:.3f}（min={min_dynamic:.2f}），可能像静帧/PPT。",
                shot=shot,
                stage="video",
                artifacts=(rel,),
                dynamic_degree=dynamic,
            ))
        freeze = _float(row, "freeze_ratio")
        if freeze is not None and freeze > max_freeze:
            findings.append(finding(
                "block" if freeze > max_freeze * 1.5 else "warn",
                f"冻结帧比例偏高：{freeze:.3f}（max={max_freeze:.2f}）。",
                shot=shot,
                stage="video",
                artifacts=(rel,),
                freeze_ratio=freeze,
            ))
        jerk = _float(row, "jerk_score")
        if jerk is not None and jerk > max_jerk:
            findings.append(finding(
                "warn",
                f"运动 jerk/速度突变偏高：{jerk:.3f}（max={max_jerk:.2f}）。",
                shot=shot,
                stage="video",
                artifacts=(rel,),
                jerk_score=jerk,
            ))
        completion = _float(row, "action_completion")
        if completion is not None and completion < min_completion:
            findings.append(finding(
                "warn",
                f"动作完成度偏低：{completion:.3f}（min={min_completion:.2f}）。",
                shot=shot,
                stage="video",
                artifacts=(rel,),
                action_completion=completion,
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
