#!/usr/bin/env python3
"""Build and validate a standalone first-frame image-to-video job."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "app-first-frame-video/v2"
SKILL = "app-first-frame-video"
LEGACY_SCHEMAS = {"app-first-frame-video/v1", "n2d-first-frame-video/v1", "app-n2d-first-frame-video/v1"}
LEGACY_SKILLS = {"n2d-first-frame-video", "app-n2d-first-frame-video"}
STATES = {"pending", "active", "done"}
REVIEWS = {"pending", "machine_complete", "accepted", "rejected", "stale"}
CONFIRMATION_KIND = "current_artifact_bytes"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON 顶层必须是 object")
    legacy = data.get("schema") in LEGACY_SCHEMAS or data.get("skill") in LEGACY_SKILLS
    if legacy:
        data["schema"] = SCHEMA
    if data.get("skill") in LEGACY_SKILLS:
        data["skill"] = SKILL
    if legacy:
        output = data.get("output")
        if isinstance(output, dict) and output.get("review") == "accepted":
            output["legacy_acceptance_receipt"] = output.get("acceptance_receipt", {"review": "accepted"})
            output["review"] = "machine_complete"
            output["acceptance_receipt"] = {}
        data["migration"] = {"source_schema": "v1", "human_reconfirmation_required": True, "legacy_evidence_preserved": True}
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


def resolve_path(value: Any, base_dir: Path | None) -> Path | None:
    if not str(value or "").strip():
        return None
    candidate = Path(str(value)).expanduser()
    if not candidate.is_absolute():
        if base_dir is None:
            return None
        candidate = base_dir / candidate
    return candidate.resolve()


def file_matches(value: Any, expected: Any, base_dir: Path | None) -> bool:
    candidate = resolve_path(value, base_dir)
    digest = str(expected or "").lower()
    if candidate is None or not candidate.is_file() or len(digest) != 64:
        return False
    try:
        return sha256(candidate) == digest
    except OSError:
        return False


def timezone_timestamp(value: Any) -> bool:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def named_human(value: Any) -> bool:
    name = str(value or "").strip()
    lowered = name.casefold()
    return len(name) >= 2 and not any(token in lowered for token in ("agent", "delegate", "auto", "robot", "system", "model", "助手", "代理"))


def human_receipt_passes(data: dict[str, Any]) -> bool:
    output = data.get("output", {})
    receipt = output.get("acceptance_receipt", {}) if isinstance(output, dict) else {}
    confirmation = receipt.get("confirmation", {}) if isinstance(receipt, dict) else {}
    output_hash = str(output.get("sha256", "")).lower() if isinstance(output, dict) else ""
    return (
        isinstance(receipt, dict)
        and receipt.get("reviewer_kind") == "human"
        and named_human(receipt.get("reviewer_name"))
        and receipt.get("verdict") == "accepted"
        and receipt.get("input_sha256") == data.get("job", {}).get("source_sha256")
        and receipt.get("output_sha256") == output_hash
        and isinstance(receipt.get("criteria"), list) and bool(receipt.get("criteria"))
        and receipt.get("blocks") == []
        and timezone_timestamp(receipt.get("reviewed_at"))
        and isinstance(confirmation, dict)
        and confirmation.get("kind") == CONFIRMATION_KIND
        and confirmation.get("artifact_sha256") == output_hash
        and confirmation.get("current_pixels_reviewed") is True
        and confirmation.get("decision") == "accept"
        and bool(str(confirmation.get("statement", "")).strip())
    )


def accept_output(data: dict[str, Any], base_dir: Path, reviewer: str, statement: str, confirmed: bool) -> None:
    output = data.get("output", {})
    if not confirmed:
        raise ValueError("必须由真人显式确认已查看当前视频")
    if not named_human(reviewer):
        raise ValueError("reviewer 必须是具名真人，不得使用 agent/自动代理身份")
    if not str(statement).strip():
        raise ValueError("statement 不能为空")
    if output.get("review") not in {"machine_complete", "accepted"}:
        raise ValueError("输出尚未 machine_complete")
    if not file_matches(output.get("path"), output.get("sha256"), base_dir):
        raise ValueError("输出当前文件字节与登记 SHA-256 不一致")
    digest = str(output.get("sha256", "")).lower()
    output["acceptance_receipt"] = {
        "reviewer_kind": "human",
        "reviewer_name": reviewer.strip(),
        "verdict": "accepted",
        "input_sha256": data.get("job", {}).get("source_sha256", ""),
        "output_sha256": digest,
        "criteria": ["首帧连续", "身份稳定", "动作与镜头运动合理"],
        "blocks": [],
        "reviewed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "confirmation": {
            "kind": CONFIRMATION_KIND,
            "artifact_sha256": digest,
            "current_pixels_reviewed": True,
            "decision": "accept",
            "statement": statement.strip(),
        },
    }
    output["review"] = "accepted"
    refresh(data, base_dir)


def refresh(data: dict[str, Any], base_dir: Path | None = None) -> None:
    frame = data.get("frame", {})
    motion = data.get("motion", {})
    output = data.get("output", {})
    frame_ready = file_matches(frame.get("path"), frame.get("sha256"), base_dir)
    motion_ready = all(str(motion.get(key, "")).strip() for key in ("subject", "camera", "environment", "pacing"))
    output_done = bool(
        output.get("review") == "accepted"
        and file_matches(output.get("path"), output.get("sha256"), base_dir)
        and human_receipt_passes(data)
    )
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
        "output": {"path": "", "sha256": "", "review": "pending", "acceptance_receipt": {}, "notes": ""},
    }
    refresh(data, resolved.parent)
    return data


def prepare(data: dict[str, Any], base_dir: Path | None = None) -> None:
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
    refresh(data, base_dir)


def validate(data: dict[str, Any], base_dir: Path | None = None) -> list[str]:
    errors: list[str] = []
    expected = {**data, "steps": {}}
    refresh(expected, base_dir)
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
        if steps != expected["steps"]:
            errors.append("steps 与当前文件字节和真人验收证据不一致")
    frame = data.get("frame", {})
    if not file_matches(frame.get("path"), frame.get("sha256"), base_dir):
        errors.append("frame 必须绑定当前真实文件与匹配的 SHA-256")
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
    if output.get("review") in {"machine_complete", "accepted"} and not file_matches(output.get("path"), output.get("sha256"), base_dir):
        errors.append("machine_complete 输出必须绑定当前真实文件与匹配的 SHA-256")
    if output.get("review") == "accepted" and not human_receipt_passes(data):
        errors.append("accepted 输出必须有具名真人、带时区、精确绑定当前视频字节的显式回执")
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
    accept = sub.add_parser("accept-output", help="真人核对当前视频字节并登记显式验收回执")
    accept.add_argument("path", type=Path)
    accept.add_argument("--reviewer", required=True)
    accept.add_argument("--statement", required=True)
    accept.add_argument("--confirm-current-artifact", action="store_true")
    accept.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.command == "init":
        data = build(args.source)
        write_json(args.output, data)
        print(json.dumps({"ok": True, "output": str(args.output)}, ensure_ascii=False))
        return 0
    data = read_json(args.path)
    if args.command == "accept-output":
        try:
            accept_output(data, args.path.parent, args.reviewer, args.statement, args.confirm_current_artifact)
        except ValueError as exc:
            print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
            return 1
        errors = validate(data, args.path.parent)
        if not errors and args.write:
            write_json(args.path, data)
        print(json.dumps({"ok": not errors, "errors": errors, "data": None if args.write else data}, ensure_ascii=False, indent=2))
        return 1 if errors else 0
    if args.command == "prepare":
        prepare(data, args.path.parent)
        errors = validate(data, args.path.parent)
        if not errors and args.write:
            write_json(args.path, data)
        print(json.dumps({"ok": not errors, "errors": errors, "data": None if args.write else data}, ensure_ascii=False, indent=2))
        return 1 if errors else 0
    refresh(data, args.path.parent)
    errors = validate(data, args.path.parent)
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
