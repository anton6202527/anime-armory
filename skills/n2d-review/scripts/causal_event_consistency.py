#!/usr/bin/env python3
"""Physical/causal chain consistency checker for video-stage events."""
from __future__ import annotations

import os
from typing import List

from video_consistency_common import contains_any, existing_media, finding, load_first_json, rows_from, story_text, verdict_from


REPORT_RELS = (
    os.path.join("生产数据", "causal_event_graph_{ep}.json"),
    os.path.join("生产数据", "physical_causality_{ep}.json"),
    os.path.join("脚本", "{ep}", "causal_event_graph.json"),
    os.path.join("出视频", "{ep}", "causal_event_graph.json"),
)

CAUSAL_WORDS = (
    "击中", "命中", "刺中", "砍中", "推倒", "撞碎", "摔碎", "破裂", "断裂", "燃起", "熄灭",
    "落地", "掉落", "飞出", "爆炸", "流血", "伤口", "打开", "关闭", "因而", "导致", "随后",
    "hit", "break", "shatter", "fall", "drop", "burn", "explode", "cause", "therefore",
)


def _has_risk(root: str, ep: str) -> bool:
    text = story_text(root, ep)
    return contains_any(text, CAUSAL_WORDS)


def _event_id(row: dict, idx: int) -> str:
    return str(row.get("id") or row.get("event_id") or row.get("name") or f"event_{idx + 1}")


def analyze(root: str, ep: str) -> dict:
    data, rel = load_first_json(root, tuple(r.format(ep=ep) for r in REPORT_RELS))
    if data is None:
        if _has_risk(root, ep) and existing_media(root, ep):
            return {
                "available": True,
                "findings": [finding(
                    "warn",
                    "视频/脚本包含明显物理因果动作，但缺 causal_event_graph；状态转场之外的因果链无法复核。",
                    stage="script_stage2",
                    artifacts=(f"脚本/{ep}/storyboard.json", "生产数据/causal_event_graph_{ep}.json".format(ep=ep)),
                )],
                "notes": [],
            }
        return {
            "available": False,
            "findings": [],
            "notes": ["未找到 causal_event_graph sidecar；物理/因果链一致性跳过。"],
        }

    findings: List[dict] = []
    for idx, row in enumerate(rows_from(data, ("findings", "events", "causal_events", "checks", "items"))):
        explicit = verdict_from(row)
        shot = row.get("clip") or row.get("shot") or row.get("clip_id")
        event_id = _event_id(row, idx)
        if explicit in {"block", "warn"}:
            findings.append(finding(
                explicit,
                str(row.get("message") or row.get("reason") or f"因果事件 {event_id} 未通过"),
                shot=shot,
                stage=str(row.get("return_to_stage") or "video"),
                artifacts=(rel,),
                event_id=event_id,
            ))
            continue
        missing = []
        if not (row.get("cause") or row.get("precondition") or row.get("before_state")):
            missing.append("cause/precondition")
        if not (row.get("effect") or row.get("after_state") or row.get("state_after")):
            missing.append("effect/after_state")
        if not (row.get("evidence_frames") or row.get("evidence_clips") or row.get("vlm_question") or row.get("evidence")):
            missing.append("video_evidence")
        if missing:
            findings.append(finding(
                "warn",
                f"因果事件 {event_id} 缺字段：{', '.join(missing)}；无法确认动作、结果和视频证据是否闭环。",
                shot=shot,
                stage="script_stage2",
                artifacts=(rel,),
                event_id=event_id,
            ))
        if row.get("cause_clip") and row.get("effect_clip") and str(row.get("order_ok")).lower() in {"false", "0", "no"}:
            findings.append(finding(
                "block",
                f"因果事件 {event_id} 的结果早于原因或跨镜顺序异常。",
                shot=shot or row.get("effect_clip"),
                stage="video",
                artifacts=(rel,),
                event_id=event_id,
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
