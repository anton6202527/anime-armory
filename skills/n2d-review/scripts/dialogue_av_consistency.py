#!/usr/bin/env python3
"""Native multi-speaker dialogue audio/video consistency reader."""
from __future__ import annotations

import os
from typing import List

from video_consistency_common import (
    boolish_false,
    existing_media,
    finding,
    has_native_av_route,
    load_first_json,
    rows_from,
    story_text,
    verdict_from,
)


REPORT_RELS = (
    os.path.join("生产数据", "dialogue_av_alignment_{ep}.json"),
    os.path.join("生产数据", "native_dialogue_alignment_{ep}.json"),
    os.path.join("生产数据", "native_av_dialogue_{ep}.json"),
    os.path.join("出视频", "{ep}", "dialogue_av_alignment.json"),
    os.path.join("合成", "{ep}", "dialogue_av_alignment.json"),
)

MULTI_DIALOGUE_TOKENS = ("：", ":", "对话", "轮流", "插话", "打断", "speaker", "dialogue", "multi-speaker")


def _looks_like_multi_dialogue(root: str, ep: str) -> bool:
    text = story_text(root, ep)
    if not text:
        return False
    speaker_lines = 0
    for line in text.splitlines():
        if "：" in line or ":" in line:
            speaker_lines += 1
    return speaker_lines >= 2 or any(token.lower() in text.lower() for token in MULTI_DIALOGUE_TOKENS[2:])


def analyze(root: str, ep: str) -> dict:
    data, rel = load_first_json(root, tuple(r.format(ep=ep) for r in REPORT_RELS))
    if data is None:
        if has_native_av_route(root, ep) and _looks_like_multi_dialogue(root, ep) and existing_media(root, ep):
            return {
                "available": True,
                "findings": [finding(
                    "warn",
                    "检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。",
                    stage="compose",
                    artifacts=("生产数据/dialogue_av_alignment_{ep}.json".format(ep=ep),),
                )],
                "notes": [],
            }
        return {
            "available": False,
            "findings": [],
            "notes": ["未找到 dialogue_av_alignment sidecar；多人对话原生音画结构检查跳过。"],
        }

    findings: List[dict] = []
    for row in rows_from(data, ("findings", "turns", "checks", "items", "results")):
        explicit = verdict_from(row)
        shot = row.get("clip") or row.get("shot") or row.get("clip_id") or row.get("turn_id")
        if explicit in {"block", "warn"}:
            findings.append(finding(
                explicit,
                str(row.get("message") or row.get("reason") or "多人对话音画结构报告未通过"),
                shot=shot,
                stage=str(row.get("return_to_stage") or "compose"),
                artifacts=(rel,),
                speaker=row.get("speaker") or row.get("expected_speaker"),
            ))
            continue
        checks = (
            ("speaker_match", "说话人身份与声道/字幕/画面对人不一致"),
            ("utterance_match", "台词内容与音频识别/字幕不一致"),
            ("turn_order_ok", "多人对话轮次顺序不一致"),
            ("turn_taking_ok", "多人对话 turn-taking 逻辑不一致，出现跳轮次/截断/顺序错乱"),
            ("overlap_ok", "多人对话出现非设计性的重叠说话或互相抢声"),
            ("camera_on_speaker", "镜头没有对准当前说话人"),
            ("active_speaker_visible", "当前活跃说话人不可见或不可定位"),
            ("voice_identity_match", "声纹/音色与当前可见角色不匹配"),
            ("emotion_match", "台词情绪与表演/配音情绪不一致"),
            ("lip_sync_ok", "当前说话人口型与音频不同步"),
            ("narration_stability_ok", "旁白/角色对白归属发生漂移"),
        )
        for key, message in checks:
            if key in row and boolish_false(row.get(key)):
                findings.append(finding(
                    "block" if key in {
                        "speaker_match", "utterance_match", "turn_order_ok", "turn_taking_ok",
                        "voice_identity_match",
                    } else "warn",
                    message,
                    shot=shot,
                    stage="compose",
                    artifacts=(rel,),
                    speaker=row.get("speaker") or row.get("expected_speaker"),
                    utterance=row.get("utterance") or row.get("expected_text"),
                ))
        if row.get("hallucinated_speaker"):
            findings.append(finding(
                "block",
                f"多人对话出现幻觉说话人：{row.get('hallucinated_speaker')}。",
                shot=shot,
                stage="compose",
                artifacts=(rel,),
                speaker=row.get("hallucinated_speaker"),
            ))
        if row.get("missing_turn") or row.get("extra_utterance"):
            findings.append(finding(
                "block",
                "多人对话轮次缺失或多出未登记台词。",
                shot=shot,
                stage="compose",
                artifacts=(rel,),
                missing_turn=row.get("missing_turn"),
                extra_utterance=row.get("extra_utterance"),
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
