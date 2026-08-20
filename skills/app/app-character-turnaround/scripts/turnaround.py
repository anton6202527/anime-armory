#!/usr/bin/env python3
"""Build and validate a standalone character-turnaround job."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "app-character-turnaround/v1"
SKILL = "app-character-turnaround"
LEGACY_SCHEMAS = {"n2d-character-turnaround/v1", "app-n2d-character-turnaround/v1"}
LEGACY_SKILLS = {"n2d-character-turnaround", "app-n2d-character-turnaround"}
STEP_STATES = {"pending", "active", "done"}
VIEW_STATES = {"pending", "ready", "accepted", "rejected"}
VIEW_LABELS = {
    "front": "正面全身视图，角色正对镜头，站姿中性",
    "left_profile": "左侧面全身视图，严格九十度侧身，站姿中性",
    "back": "背面全身视图，完整展示后脑、服装背部与鞋履",
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON 顶层必须是 object")
    if value.get("schema") in LEGACY_SCHEMAS:
        value["schema"] = SCHEMA
    if value.get("skill") in LEGACY_SKILLS:
        value["skill"] = SKILL
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_payload(source: str | None) -> dict[str, str]:
    if not source:
        return {"status": "pending", "kind": "description", "path": "", "sha256": ""}
    path = Path(source).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"参考图不存在: {path}")
    return {"status": "ready", "kind": "upload", "path": str(path), "sha256": file_sha(path)}


def refresh_steps(data: dict[str, Any]) -> None:
    source = data.get("source", {})
    character = data.get("character", {})
    views = data.get("views", [])
    identity_ready = all(str(character.get(key, "")).strip() for key in ("name", "face", "hair", "body", "outfit"))
    source_ready = bool(source.get("path") and source.get("sha256")) or (source.get("kind") == "description" and identity_ready)
    generation_done = len(views) == 3 and all(
        view.get("status") == "accepted" and view.get("output_path") and view.get("output_sha256") for view in views
    )
    data["steps"] = {
        "source": "done" if source_ready else "active",
        "identity": "done" if identity_ready else ("active" if source_ready else "pending"),
        "generation": "done" if generation_done else ("active" if identity_ready else "pending"),
    }


def initial_payload(name: str, source: str | None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema": SCHEMA,
        "skill": SKILL,
        "title": f"{name} · 角色三视图",
        "steps": {},
        "source": source_payload(source),
        "character": {
            "name": name.strip(),
            "face": "待确认脸型、五官比例与肤色",
            "hair": "待确认发型、发色与发际线",
            "body": "待确认身高、体型与身体比例",
            "outfit": "待确认服装版型、材质与配色",
            "accessories": "",
            "drift_forbidden": ["脸型", "五官比例", "发型", "服装结构", "身体比例"],
        },
        "generation": {
            "model": "manual",
            "channel": "manual",
            "aspect_ratio": "16:9",
            "resolution": "2K",
            "background": "纯中性浅灰背景，无文字无水印",
            "negative": "禁止透视夸张、姿势变化、服装变化、发型变化、裁切肢体",
            "job_status": "draft",
        },
        "views": [
            {"id": key, "label": label, "prompt": "", "status": "pending", "output_path": "", "output_sha256": "", "review": "pending"}
            for key, label in VIEW_LABELS.items()
        ],
    }
    refresh_steps(data)
    return data


def prepare(data: dict[str, Any]) -> None:
    character = data.get("character", {})
    generation = data.get("generation", {})
    identity = "，".join(str(character.get(key, "")).strip() for key in ("face", "hair", "body", "outfit", "accessories") if str(character.get(key, "")).strip())
    locked = "、".join(str(item) for item in character.get("drift_forbidden", []))
    for view in data.get("views", []):
        view["prompt"] = (
            f"{character.get('name', '角色')}，{view.get('label')}。身份事实：{identity}。"
            f"三视图统一比例与站姿，严格锁定{locked}。{generation.get('background')}。"
            f"负向约束：{generation.get('negative')}。"
        )
    generation["job_status"] = "ready"
    refresh_steps(data)


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
        for key in ("source", "identity", "generation"):
            if steps.get(key) not in STEP_STATES:
                errors.append(f"steps.{key} 状态无效")
    character = data.get("character")
    if not isinstance(character, dict):
        errors.append("character 必须是 object")
    else:
        for key in ("name", "face", "hair", "body", "outfit"):
            if not str(character.get(key, "")).strip():
                errors.append(f"character.{key} 不能为空")
    views = data.get("views")
    if not isinstance(views, list) or {view.get("id") for view in views if isinstance(view, dict)} != set(VIEW_LABELS):
        errors.append("views 必须包含 front / left_profile / back")
    else:
        for view in views:
            if view.get("status") not in VIEW_STATES:
                errors.append(f"views.{view.get('id')}.status 无效")
            if view.get("status") == "accepted" and not (view.get("output_path") and view.get("output_sha256")):
                errors.append(f"views.{view.get('id')} accepted 时必须绑定真实输出路径与 SHA-256")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="创建独立三视图工作台 JSON")
    init.add_argument("--name", required=True)
    init.add_argument("--source")
    init.add_argument("--output", type=Path, required=True)
    prep = sub.add_parser("prepare", help="生成三个视角 prompt 与 job 包")
    prep.add_argument("path", type=Path)
    prep.add_argument("--write", action="store_true")
    check = sub.add_parser("validate", help="验证工作台 JSON")
    check.add_argument("path", type=Path)
    args = parser.parse_args()

    if args.command == "init":
        data = initial_payload(args.name, args.source)
        write_json(args.output, data)
        print(json.dumps({"ok": True, "output": str(args.output)}, ensure_ascii=False))
        return 0
    data = read_json(args.path)
    if args.command == "prepare":
        prepare(data)
        errors = validate(data)
        if not errors and args.write:
            write_json(args.path, data)
        print(json.dumps({"ok": not errors, "errors": errors, "data": data if not args.write else None}, ensure_ascii=False, indent=2))
        return 1 if errors else 0
    errors = validate(data)
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
