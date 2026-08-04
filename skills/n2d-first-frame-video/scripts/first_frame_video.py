#!/usr/bin/env python3
"""Build and validate a standalone first-frame image-to-video job."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "n2d-first-frame-video/v1"
SKILL = "n2d-first-frame-video"
STATES = {"pending", "active", "done"}
REVIEWS = {"pending", "accepted", "rejected"}


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON 顶层必须是 object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def refresh(data: dict[str, Any]) -> None:
    frame = data.get("frame", {})
    motion = data.get("motion", {})
    output = data.get("output", {})
    frame_ready = bool(frame.get("path") and frame.get("sha256"))
    motion_ready = all(str(motion.get(key, "")).strip() for key in ("subject", "camera", "environment", "pacing"))
    output_done = bool(output.get("path") and output.get("sha256") and output.get("review") == "accepted")
    data["steps"] = {
        "frame": "done" if frame_ready else "active",
        "motion": "done" if motion_ready else ("active" if frame_ready else "pending"),
        "generation": "done" if output_done else ("active" if motion_ready else "pending"),
    }


def build(source: Path) -> dict[str, Any]:
    resolved = source.expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"首帧不存在: {resolved}")
    data: dict[str, Any] = {
        "schema": SCHEMA,
        "skill": SKILL,
        "title": resolved.stem,
        "steps": {},
        "frame": {"kind": "upload", "path": str(resolved), "sha256": sha256(resolved), "description": "待补充首帧可见事实"},
        "motion": {
            "subject": "主体做自然、连续的小幅动作",
            "camera": "镜头缓慢向前推进",
            "environment": "环境光影与背景元素自然变化",
            "pacing": "前缓后稳，无突然跳变",
            "forbidden": ["身份改变", "服装改变", "肢体变形", "背景重绘", "首帧跳切"],
        },
        "generation": {"model": "manual", "channel": "manual", "duration": 5, "aspect_ratio": "16:9", "resolution": "720P", "count": 1},
        "job": {"source_sha256": "", "prompt": "", "negative": "", "status": "draft"},
        "output": {"path": "", "sha256": "", "review": "pending", "notes": ""},
    }
    refresh(data)
    return data


def prepare(data: dict[str, Any]) -> None:
    frame = data.get("frame", {})
    motion = data.get("motion", {})
    generation = data.get("generation", {})
    forbidden = "、".join(str(item) for item in motion.get("forbidden", []))
    data["job"] = {
        "source_sha256": frame.get("sha256", ""),
        "prompt": (
            f"以输入首帧为第0帧并保持构图连续。主体运动：{motion.get('subject')}。"
            f"镜头运动：{motion.get('camera')}。环境变化：{motion.get('environment')}。"
            f"节奏：{motion.get('pacing')}。时长 {generation.get('duration')} 秒。"
        ),
        "negative": f"禁止：{forbidden}",
        "status": "ready",
    }
    refresh(data)


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != SCHEMA:
        errors.append(f"schema 必须为 {SCHEMA}")
    if data.get("skill") != SKILL:
        errors.append(f"skill 必须为 {SKILL}")
    steps = data.get("steps")
    if not isinstance(steps, dict):
        errors.append("steps 必须是 object")
    else:
        for key in ("frame", "motion", "generation"):
            if steps.get(key) not in STATES:
                errors.append(f"steps.{key} 状态无效")
    frame = data.get("frame", {})
    if not frame.get("path") or not frame.get("sha256"):
        errors.append("frame 必须绑定真实路径与 SHA-256")
    motion = data.get("motion", {})
    for key in ("subject", "camera", "environment", "pacing"):
        if not str(motion.get(key, "")).strip():
            errors.append(f"motion.{key} 不能为空")
    generation = data.get("generation", {})
    if not str(generation.get("model", "")).strip() or not str(generation.get("channel", "")).strip():
        errors.append("generation.model 与 generation.channel 必须分列填写")
    if int(generation.get("duration", 0)) <= 0:
        errors.append("generation.duration 必须大于 0")
    output = data.get("output", {})
    if output.get("review") not in REVIEWS:
        errors.append("output.review 无效")
    if output.get("review") == "accepted" and not (output.get("path") and output.get("sha256")):
        errors.append("accepted 输出必须绑定真实路径与 SHA-256")
    job = data.get("job", {})
    if job.get("status") == "ready" and job.get("source_sha256") != frame.get("sha256"):
        errors.append("job 已过期：source_sha256 与当前首帧不一致")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--source", type=Path, required=True)
    init.add_argument("--output", type=Path, required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("path", type=Path)
    prep.add_argument("--write", action="store_true")
    check = sub.add_parser("validate")
    check.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.command == "init":
        data = build(args.source)
        write_json(args.output, data)
        print(json.dumps({"ok": True, "output": str(args.output)}, ensure_ascii=False))
        return 0
    data = read_json(args.path)
    if args.command == "prepare":
        prepare(data)
        errors = validate(data)
        if not errors and args.write:
            write_json(args.path, data)
        print(json.dumps({"ok": not errors, "errors": errors, "data": None if args.write else data}, ensure_ascii=False, indent=2))
        return 1 if errors else 0
    errors = validate(data)
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
