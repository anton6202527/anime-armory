#!/usr/bin/env python3
"""Build and validate a standalone character-turnaround job."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "app-character-turnaround/v2"
SKILL = "app-character-turnaround"
LEGACY_SCHEMAS = {"app-character-turnaround/v1", "n2d-character-turnaround/v1", "app-n2d-character-turnaround/v1"}
LEGACY_SKILLS = {"n2d-character-turnaround", "app-n2d-character-turnaround"}
STEP_STATES = {"pending", "active", "done"}
VIEW_STATES = {"pending", "ready", "machine_complete", "accepted", "rejected", "stale"}
CONFIRMATION_KIND = "current_artifact_bytes"
VIEW_LABELS = {
    "front": "正面全身视图，角色正对镜头，站姿中性",
    "left_profile": "左侧面全身视图，严格九十度侧身，站姿中性",
    "back": "背面全身视图，完整展示后脑、服装背部与鞋履",
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON 顶层必须是 object")
    legacy = value.get("schema") in LEGACY_SCHEMAS or value.get("skill") in LEGACY_SKILLS
    if legacy:
        value["schema"] = SCHEMA
    if value.get("skill") in LEGACY_SKILLS:
        value["skill"] = SKILL
    if legacy:
        for view in value.get("views", []):
            if isinstance(view, dict) and (view.get("status") == "accepted" or view.get("review") == "accepted"):
                view["legacy_acceptance_receipt"] = view.get("acceptance_receipt", {"review": "accepted"})
                view["status"] = "machine_complete"
                view["review"] = "machine_complete"
                view["acceptance_receipt"] = {}
        value["migration"] = {"source_schema": "v1", "human_reconfirmation_required": True, "legacy_evidence_preserved": True}
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
        return file_sha(candidate) == digest
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


def view_receipt_passes(view: dict[str, Any], source_sha256: str) -> bool:
    receipt = view.get("acceptance_receipt", {})
    confirmation = receipt.get("confirmation", {}) if isinstance(receipt, dict) else {}
    output_hash = str(view.get("output_sha256", "")).lower()
    return (
        isinstance(receipt, dict)
        and receipt.get("reviewer_kind") == "human"
        and named_human(receipt.get("reviewer_name"))
        and receipt.get("verdict") == "accepted"
        and receipt.get("view_id") == view.get("id")
        and receipt.get("source_sha256") == source_sha256
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


def accept_views(data: dict[str, Any], base_dir: Path, reviewer: str, statement: str, confirmed: bool) -> None:
    if not confirmed:
        raise ValueError("必须由真人显式确认已逐张查看三张当前图片")
    if not named_human(reviewer):
        raise ValueError("reviewer 必须是具名真人，不得使用 agent/自动代理身份")
    if not str(statement).strip():
        raise ValueError("statement 不能为空")
    views = data.get("views", [])
    if len(views) != 3:
        raise ValueError("必须有 front / left_profile / back 三张视图")
    for view in views:
        if view.get("status") not in {"machine_complete", "accepted"}:
            raise ValueError(f"视图 {view.get('id')} 尚未 machine_complete")
        if not file_matches(view.get("output_path"), view.get("output_sha256"), base_dir):
            raise ValueError(f"视图 {view.get('id')} 当前文件字节与登记 SHA-256 不一致")
    reviewed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    source_sha = str(data.get("source", {}).get("sha256", ""))
    for view in views:
        digest = str(view.get("output_sha256", "")).lower()
        view["acceptance_receipt"] = {
            "reviewer_kind": "human",
            "reviewer_name": reviewer.strip(),
            "verdict": "accepted",
            "view_id": view.get("id"),
            "source_sha256": source_sha,
            "output_sha256": digest,
            "criteria": ["脸与五官一致", "发型服装一致", "体型配饰与比例一致"],
            "blocks": [],
            "reviewed_at": reviewed_at,
            "confirmation": {
                "kind": CONFIRMATION_KIND,
                "artifact_sha256": digest,
                "current_pixels_reviewed": True,
                "decision": "accept",
                "statement": statement.strip(),
            },
        }
        view["status"] = "accepted"
        view["review"] = "accepted"
    refresh_steps(data, base_dir)


def source_payload(source: str | None) -> dict[str, str]:
    if not source:
        return {"status": "pending", "kind": "description", "path": "", "sha256": ""}
    path = Path(source).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"参考图不存在: {path}")
    return {"status": "ready", "kind": "upload", "path": str(path), "sha256": file_sha(path)}


def refresh_steps(data: dict[str, Any], base_dir: Path | None = None) -> None:
    source = data.get("source", {})
    character = data.get("character", {})
    views = data.get("views", [])
    identity_ready = all(str(character.get(key, "")).strip() for key in ("name", "face", "hair", "body", "outfit"))
    source_ready = file_matches(source.get("path"), source.get("sha256"), base_dir) or (source.get("kind") == "description" and identity_ready)
    generation_done = len(views) == 3 and all(
        view.get("status") == "accepted"
        and file_matches(view.get("output_path"), view.get("output_sha256"), base_dir)
        and view_receipt_passes(view, str(source.get("sha256", "")))
        for view in views
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
            {"id": key, "label": label, "prompt": "", "status": "pending", "output_path": "", "output_sha256": "", "review": "pending", "acceptance_receipt": {}}
            for key, label in VIEW_LABELS.items()
        ],
    }
    refresh_steps(data, Path(source).expanduser().resolve().parent if source else None)
    return data


def prepare(data: dict[str, Any], base_dir: Path | None = None) -> None:
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
    refresh_steps(data, base_dir)


def validate(data: dict[str, Any], base_dir: Path | None = None) -> list[str]:
    errors: list[str] = []
    expected = {**data, "steps": {}}
    refresh_steps(expected, base_dir)
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
        if steps != expected["steps"]:
            errors.append("steps 与当前文件字节和真人验收证据不一致")
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
            if view.get("status") in {"machine_complete", "accepted"} and not file_matches(view.get("output_path"), view.get("output_sha256"), base_dir):
                errors.append(f"views.{view.get('id')} machine_complete 必须绑定当前真实文件与匹配 SHA-256")
            if view.get("status") == "accepted" and not view_receipt_passes(view, str(data.get("source", {}).get("sha256", ""))):
                errors.append(f"views.{view.get('id')} accepted 必须有具名真人、带时区、精确绑定当前图片字节的回执")
    source = data.get("source", {})
    if source.get("kind") != "description" and not file_matches(source.get("path"), source.get("sha256"), base_dir):
        errors.append("source 必须绑定当前真实参考图与匹配 SHA-256")
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
    accept = sub.add_parser("accept", help="一次真人动作逐张核对三视图并分别登记当前像素回执")
    accept.add_argument("path", type=Path)
    accept.add_argument("--reviewer", required=True)
    accept.add_argument("--statement", required=True)
    accept.add_argument("--confirm-current-pixels", action="store_true")
    accept.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if args.command == "init":
        data = initial_payload(args.name, args.source)
        write_json(args.output, data)
        print(json.dumps({"ok": True, "output": str(args.output)}, ensure_ascii=False))
        return 0
    data = read_json(args.path)
    if args.command == "accept":
        try:
            accept_views(data, args.path.parent, args.reviewer, args.statement, args.confirm_current_pixels)
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
        print(json.dumps({"ok": not errors, "errors": errors, "data": data if not args.write else None}, ensure_ascii=False, indent=2))
        return 1 if errors else 0
    refresh_steps(data, args.path.parent)
    errors = validate(data, args.path.parent)
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
