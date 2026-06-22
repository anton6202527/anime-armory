#!/usr/bin/env python3
"""Build a standard video evaluation manifest for n2d-review sidecars.

This script does not call a proprietary VLM/embedding/tracking backend. It
discovers clips, storyboard risks, and expected sidecar targets, then writes a
single manifest that an external heavy runner can consume reproducibly.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
from typing import Any, Dict, List, Mapping, Sequence

from video_consistency_common import clip_label, existing_media, load_json, read_text
from causal_event_consistency import infer_rules


QUESTION_TEMPLATES = {
    "subject": "该镜头中主体/角色是否保持参考身份、服装和关键特征一致？",
    "scene": "该镜头的场景、光线、背景结构是否与分镜/上一镜保持一致？",
    "action": "该镜头动作是否完成，运动是否平滑且没有冻结/抽搐？",
    "physics": "该镜头的物理因果是否成立，动作结果是否符合规则：{rules}？",
    "dialogue": "该镜头的说话人、台词归属、轮次和口型是否一致？",
    "camera": "该镜头相机运动方向、深度、越轴和抖动是否符合设计？",
}

SIDEcars = {
    "video_vlm": "生产数据/video_vlm_consistency_{ep}.json",
    "video_semantic": "生产数据/video_semantic_consistency_{ep}.json",
    "dialogue_av": "生产数据/dialogue_av_alignment_{ep}.json",
    "causal_event": "生产数据/causal_event_graph_{ep}.json",
    "camera": "生产数据/camera_trajectory_probe_{ep}.json",
    "motion": "生产数据/motion_quality_{ep}.json",
    "subject_video": "生产数据/subject_video_consistency_{ep}.json",
}

MOTION_HINTS = ("奔跑", "冲向", "转身", "打斗", "挥", "追逐", "掉落", "旋转", "run", "fight", "motion")
DIALOGUE_HINTS = ("：", ":", "对话", "speaker", "dialogue", "说", "喊")
CAMERA_HINTS = ("推镜", "拉镜", "摇镜", "跟拍", "环绕", "camera", "dolly", "pan", "tilt", "orbit")


def _storyboard(root: str, ep: str) -> List[dict]:
    data = load_json(os.path.join(root, "脚本", ep, "storyboard.json"))
    if not isinstance(data, Mapping):
        return []
    raw = data.get("clips") or data.get("shots") or []
    return [row for row in raw if isinstance(row, dict)]


def _clip_text(row: Mapping[str, Any]) -> str:
    try:
        return json.dumps(row, ensure_ascii=False)
    except Exception:
        return str(row)


def _contains(text: str, tokens: Sequence[str]) -> bool:
    lowered = text.lower()
    return any(token.lower() in lowered for token in tokens)


def _clip_media(root: str, ep: str, label: str) -> List[str]:
    paths: List[str] = []
    for pattern in (
        os.path.join(root, "出视频", ep, "视频", f"*{label}*.mp4"),
        os.path.join(root, "出视频", ep, "**", f"*{label}*.mp4"),
        os.path.join(root, "合成", ep, "**", f"*{label}*.mp4"),
    ):
        paths.extend(glob.glob(pattern, recursive=True))
    return sorted({os.path.relpath(path, root) for path in paths})


def build_manifest(root: str, ep: str) -> dict:
    clips = _storyboard(root, ep)
    overview = "\n".join([
        read_text(os.path.join(root, "出视频", ep, "prompt", "00_总览.md")),
        read_text(os.path.join(root, "出视频", ep, "prompt", "01_clips.md")),
    ])
    media = [os.path.relpath(path, root) for path in existing_media(root, ep)]
    tasks: List[dict] = []
    for idx, clip in enumerate(clips, 1):
        label = clip_label(clip.get("id") or clip.get("clip_id") or idx, fallback=f"Clip_{idx:02d}")
        text = _clip_text(clip) + "\n" + overview
        rules = infer_rules(text)
        kinds = ["subject", "scene"]
        if _contains(text, MOTION_HINTS):
            kinds.append("action")
        if rules:
            kinds.append("physics")
        if _contains(text, DIALOGUE_HINTS):
            kinds.append("dialogue")
        if _contains(text, CAMERA_HINTS):
            kinds.append("camera")
        questions = []
        for kind in kinds:
            questions.append({
                "kind": kind,
                "question": QUESTION_TEMPLATES[kind].format(rules=", ".join(rules) or "未登记"),
                "expected_from": [f"脚本/{ep}/storyboard.json", f"出视频/{ep}/prompt/00_总览.md"],
            })
        tasks.append({
            "clip": label,
            "media": _clip_media(root, ep, label),
            "frame_sampling": {
                "strategy": "start_mid_end_plus_action_peaks",
                "min_frames": 5,
                "max_frames": 16,
                "ffmpeg_hint": f"ffmpeg -i <clip.mp4> -vf fps=1 <frames_dir>/{label}_%04d.png",
            },
            "risk_kinds": kinds,
            "physical_rules": rules,
            "questions": questions,
        })
    return {
        "kind": "n2d_video_eval_manifest",
        "version": 1,
        "root": root,
        "episode": ep,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "media": media,
        "sidecar_targets": {key: value.format(ep=ep) for key, value in SIDEcars.items()},
        "judge_schema_required": [
            "judge_model", "rubric_version", "frame_sample_manifest",
            "question_chain", "self_consistency_votes",
        ],
        "tasks": tasks,
        "notes": [
            "Heavy VLM/embedding/tracking runners should consume this manifest and write the sidecars listed in sidecar_targets.",
            "Do not mark missing evidence as pass; use needs_review/warn until a runner or human review fills verdicts.",
        ],
    }


def write_manifest(root: str, ep: str) -> str:
    path = os.path.join(root, "生产数据", f"video_eval_manifest_{ep}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(build_manifest(root, ep), fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    if ns.write:
        path = write_manifest(ns.root.rstrip("/"), ns.episode)
        if not ns.json:
            print(path)
            return 0
    payload = build_manifest(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"video eval tasks: {len(payload.get('tasks', []))}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(os.sys.argv[1:]))
