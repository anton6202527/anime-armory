#!/usr/bin/env python3
"""Build and validate a standalone beat-synced audio-to-video job."""

from __future__ import annotations

import argparse
import hashlib
import json
import wave
from pathlib import Path
from typing import Any

SCHEMA = "n2d-audio-video/v1"
SKILL = "n2d-audio-video"
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


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wav_duration(path: Path) -> float | None:
    if path.suffix.lower() != ".wav":
        return None
    try:
        with wave.open(str(path), "rb") as stream:
            rate = stream.getframerate()
            return stream.getnframes() / rate if rate else None
    except (wave.Error, EOFError):
        return None


def timeline_for(duration: float) -> list[dict[str, Any]]:
    count = max(1, min(8, round(duration / 8)))
    width = duration / count
    energies = ("low", "medium", "high", "medium")
    return [
        {
            "id": f"segment-{index + 1}",
            "start": round(index * width, 3),
            "end": round(duration if index == count - 1 else (index + 1) * width, 3),
            "energy": energies[index % len(energies)],
            "visual": "建立画面" if index == 0 else "按段落能量推进主体动作与场景变化",
            "cut": "soft" if index == 0 else "beat",
        }
        for index in range(count)
    ]


def refresh(data: dict[str, Any]) -> None:
    audio = data.get("audio", {})
    visual = data.get("visual", {})
    timeline = data.get("timeline", [])
    output = data.get("output", {})
    audio_ready = bool(audio.get("path") and audio.get("sha256") and float(audio.get("duration") or 0) > 0)
    plan_ready = bool(timeline) and all(str(visual.get(key, "")).strip() for key in ("style", "subject", "camera"))
    generation_done = bool(output.get("path") and output.get("sha256") and output.get("review") == "accepted")
    data["steps"] = {
        "audio": "done" if audio_ready else "active",
        "plan": "done" if plan_ready else ("active" if audio_ready else "pending"),
        "generation": "done" if generation_done else ("active" if plan_ready else "pending"),
    }


def build(audio_path: Path) -> dict[str, Any]:
    resolved = audio_path.expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"音频不存在: {resolved}")
    duration = wav_duration(resolved)
    data: dict[str, Any] = {
        "schema": SCHEMA,
        "skill": SKILL,
        "title": resolved.stem,
        "steps": {},
        "audio": {
            "path": str(resolved),
            "sha256": file_sha(resolved),
            "format": resolved.suffix.lower().lstrip("."),
            "duration": round(duration, 3) if duration else None,
            "analysis_mode": "wave-header" if duration else "unavailable",
        },
        "timeline": timeline_for(duration) if duration else [],
        "visual": {
            "style": "电影感写实画面，统一色彩与主体",
            "subject": "保持同一主体贯穿主要段落",
            "camera": "低能量段缓慢推进，高能量段在强拍切换景别",
            "reference_path": "",
            "reference_sha256": "",
            "forbidden": ["主体随机变化", "无节奏跳切", "画面闪烁", "音轨截断"],
        },
        "generation": {"model": "manual", "channel": "manual", "aspect_ratio": "16:9", "resolution": "720P", "count": 1},
        "job": {"audio_sha256": "", "timeline_sha256": "", "prompt": "", "status": "draft"},
        "output": {"path": "", "sha256": "", "review": "pending", "beat_sync_notes": ""},
    }
    refresh(data)
    return data


def prepare(data: dict[str, Any]) -> None:
    audio = data.get("audio", {})
    timeline = data.get("timeline", [])
    if not audio.get("duration"):
        raise ValueError("缺少真实音频时长，无法准备时间线任务")
    timeline_blob = json.dumps(timeline, ensure_ascii=False, sort_keys=True).encode("utf-8")
    visual = data.get("visual", {})
    forbidden = "、".join(str(item) for item in visual.get("forbidden", []))
    data["job"] = {
        "audio_sha256": audio.get("sha256", ""),
        "timeline_sha256": digest_bytes(timeline_blob),
        "prompt": (
            f"视觉风格：{visual.get('style')}。主体连续：{visual.get('subject')}。"
            f"运镜与剪辑：{visual.get('camera')}。按 timeline 的 start/end/energy/cut 执行卡点。"
            f"禁止：{forbidden}。保留完整原音频作为时间基准。"
        ),
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
        for key in ("audio", "plan", "generation"):
            if steps.get(key) not in STATES:
                errors.append(f"steps.{key} 状态无效")
    audio = data.get("audio", {})
    if not audio.get("path") or not audio.get("sha256"):
        errors.append("audio 必须绑定真实路径与 SHA-256")
    if float(audio.get("duration") or 0) <= 0:
        errors.append("audio.duration 必须是真实正数")
    timeline = data.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        errors.append("timeline 至少需要一个段落")
    else:
        last_end = 0.0
        for index, segment in enumerate(timeline, 1):
            start = float(segment.get("start", -1))
            end = float(segment.get("end", -1))
            if start < last_end or end <= start:
                errors.append(f"timeline[{index}] 时间区间无效或重叠")
            last_end = end
    generation = data.get("generation", {})
    if not generation.get("model") or not generation.get("channel"):
        errors.append("generation.model 与 generation.channel 必须分列填写")
    output = data.get("output", {})
    if output.get("review") not in REVIEWS:
        errors.append("output.review 无效")
    if output.get("review") == "accepted" and not (output.get("path") and output.get("sha256")):
        errors.append("accepted 输出必须绑定真实路径与 SHA-256")
    job = data.get("job", {})
    if job.get("status") == "ready":
        timeline_sha = digest_bytes(json.dumps(timeline, ensure_ascii=False, sort_keys=True).encode("utf-8")) if isinstance(timeline, list) else ""
        if job.get("audio_sha256") != audio.get("sha256") or job.get("timeline_sha256") != timeline_sha:
            errors.append("job 已过期：音频或时间线 SHA 不一致")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--audio", type=Path, required=True)
    init.add_argument("--output", type=Path, required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("path", type=Path)
    prep.add_argument("--write", action="store_true")
    check = sub.add_parser("validate")
    check.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.command == "init":
        data = build(args.audio)
        write_json(args.output, data)
        print(json.dumps({"ok": True, "output": str(args.output), "analysis_mode": data["audio"]["analysis_mode"]}, ensure_ascii=False))
        return 0
    data = read_json(args.path)
    if args.command == "prepare":
        try:
            prepare(data)
        except ValueError as exc:
            print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
            return 1
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
