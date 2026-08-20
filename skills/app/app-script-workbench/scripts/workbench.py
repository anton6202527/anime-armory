#!/usr/bin/env python3
"""Build and validate the top-level standalone canvas script workbench contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

SCHEMA = "app-script-workbench/v1"
SKILL = "app-script-workbench"
LEGACY_SCHEMAS = {"n2d-script-workbench/v1", "app-n2d-script-workbench/v1"}
LEGACY_SKILLS = {"n2d-script-workbench", "app-n2d-script-workbench"}
STEP_STATES = {"pending", "active", "done"}
ASSET_KINDS = {"character", "scene", "prop"}
ASSET_STATES = {"pending", "generating", "ready", "failed"}
ASSET_SOURCES = {"none", "ai", "canvas", "upload"}
SHOT_FIELDS = ("id", "duration", "visual", "scale", "lighting", "dialogue", "sound", "camera")
ASSET_FIELDS = ("id", "kind", "name", "description", "prompt", "status", "source")
ASSET_EVIDENCE_FIELDS = ("attachmentId", "nodeId", "imageUrl", "mimeType", "error")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON 顶层必须是 object")
    if payload.get("schema") in LEGACY_SCHEMAS:
        payload["schema"] = SCHEMA
    if payload.get("skill") in LEGACY_SKILLS:
        payload["skill"] = SKILL
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def stable_id(prefix: str, index: int, name: str) -> str:
    digest = hashlib.sha256(f"{prefix}:{index}:{name}".encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest}"


def normalize_shot(raw: dict[str, Any], index: int) -> dict[str, Any]:
    visual = str(raw.get("visual") or raw.get("description") or "").strip()
    try:
        duration = min(15, max(5, math.floor(float(raw.get("duration") or 5) + 0.5)))
    except (TypeError, ValueError, OverflowError):
        duration = 5
    return {
        "id": str(raw.get("id") or stable_id("shot", index, visual)),
        "duration": duration,
        "visual": visual,
        "scale": str(raw.get("scale") or "中景"),
        "lighting": str(raw.get("lighting") or "自然光，电影感"),
        "dialogue": str(raw.get("dialogue") or ""),
        "sound": str(raw.get("sound") or "环境底噪"),
        "camera": str(raw.get("camera") or "固定机位"),
        "final_prompt": str(raw.get("final_prompt") or ""),
        "color": str(raw.get("color") or ""),
    }


def normalize_asset(raw: dict[str, Any], index: int) -> dict[str, Any]:
    kind = str(raw.get("kind") or "character")
    name = str(raw.get("name") or "").strip()
    result = {
        "id": str(raw.get("id") or stable_id("asset", index, f"{kind}:{name}")),
        "kind": kind,
        "name": name,
        "description": str(raw.get("description") or "").strip(),
        "prompt": str(raw.get("prompt") or "").strip(),
        "status": str(raw.get("status") or "pending"),
        "source": str(raw.get("source") or "none"),
    }
    if result["source"] != "none":
        for field in ASSET_EVIDENCE_FIELDS:
            if field == "error":
                continue
            value = raw.get(field)
            if isinstance(value, str) and value.strip():
                result[field] = value.strip()
    error = raw.get("error")
    if isinstance(error, str) and error.strip():
        result["error"] = error.strip()
    if result["status"] == "ready" and not has_real_asset_source(result):
        result["status"] = "pending"
    return result


def has_real_asset_source(asset: dict[str, Any]) -> bool:
    if asset.get("source") == "none":
        return False
    if str(asset.get("attachmentId") or "").strip() or str(asset.get("nodeId") or "").strip():
        return True
    image_url = str(asset.get("imageUrl") or "").strip().lower()
    return image_url.startswith(("http://", "https://", "blob:", "data:image/", "/"))


def refresh_steps(payload: dict[str, Any]) -> None:
    shots = payload.get("shots", [])
    assets = payload.get("assets", [])
    shot_done = bool(shots) and all(
        all(str(shot.get(field, "")).strip() for field in ("id", "visual", "scale", "lighting", "sound", "camera"))
        and isinstance(shot.get("duration"), (int, float))
        and 5 <= float(shot["duration"]) <= 15
        for shot in shots
    )
    asset_done = bool(assets) and all(asset.get("status") == "ready" and has_real_asset_source(asset) for asset in assets)
    prompt_done = bool(shots) and all(str(shot.get("final_prompt", "")).strip() for shot in shots)
    payload["steps"] = {
        "shots": "done" if shot_done else "active",
        "assets": "done" if asset_done else ("active" if shot_done else "pending"),
        "prompts": "done" if prompt_done else ("active" if asset_done else "pending"),
    }


def build(raw: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": SCHEMA,
        "skill": SKILL,
        "title": str(raw.get("title") or "未命名故事脚本").strip(),
        "global_style": str(raw.get("global_style") or "电影级画面，主体一致，细节清晰").strip(),
        "style_locked": raw.get("style_locked") is True,
        "steps": {},
        "shots": [normalize_shot(item, index) for index, item in enumerate(raw.get("shots", []), 1) if isinstance(item, dict)],
        "assets": [normalize_asset(item, index) for index, item in enumerate(raw.get("assets", []), 1) if isinstance(item, dict)],
    }
    refresh_steps(payload)
    return payload


def compose_prompt(style: str, shot: dict[str, Any]) -> str:
    parts = [style, f"{shot['scale']}，{shot['visual']}", f"光影氛围：{shot['lighting']}。"]
    if str(shot.get("dialogue", "")).strip():
        parts.append(f"对白与旁白：{shot['dialogue']}。")
    parts.extend((f"音效：{shot['sound']}。", f"运镜：{shot['camera']}。", "主体一致，细节清晰，电影级构图。"))
    return " ".join(part.strip() for part in parts if part.strip())


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema 必须为 {SCHEMA}")
    if payload.get("skill") != SKILL:
        errors.append(f"skill 必须为 {SKILL}")
    if not str(payload.get("title", "")).strip():
        errors.append("title 不能为空")
    if not str(payload.get("global_style", "")).strip():
        errors.append("global_style 不能为空")
    if not isinstance(payload.get("style_locked"), bool):
        errors.append("style_locked 必须是 boolean")
    steps = payload.get("steps")
    if not isinstance(steps, dict):
        errors.append("steps 必须是 object")
    else:
        for key in ("shots", "assets", "prompts"):
            if steps.get(key) not in STEP_STATES:
                errors.append(f"steps.{key} 状态无效")
    shots = payload.get("shots")
    if not isinstance(shots, list) or not shots:
        errors.append("shots 至少需要一个镜头")
    else:
        seen: set[str] = set()
        for index, shot in enumerate(shots, 1):
            if not isinstance(shot, dict):
                errors.append(f"shots[{index}] 必须是 object")
                continue
            for field in SHOT_FIELDS:
                if field not in shot or (field in {"id", "visual", "scale", "lighting", "sound", "camera"} and not str(shot.get(field, "")).strip()):
                    errors.append(f"shots[{index}].{field} 缺失")
            if shot.get("id") in seen:
                errors.append(f"shots[{index}].id 重复")
            seen.add(str(shot.get("id")))
            try:
                duration = float(shot.get("duration", 0))
                if not math.isfinite(duration):
                    errors.append(f"shots[{index}].duration 必须是有限数字")
                elif duration < 5 or duration > 15:
                    errors.append(f"shots[{index}].duration 必须在 5–15 秒之间")
            except (TypeError, ValueError):
                errors.append(f"shots[{index}].duration 必须是数字")
    assets = payload.get("assets")
    if not isinstance(assets, list):
        errors.append("assets 必须是 array")
    else:
        seen_assets: set[str] = set()
        for index, asset in enumerate(assets, 1):
            if not isinstance(asset, dict):
                errors.append(f"assets[{index}] 必须是 object")
                continue
            for field in ASSET_FIELDS:
                if field not in asset or (field in {"id", "name"} and not str(asset.get(field, "")).strip()):
                    errors.append(f"assets[{index}].{field} 缺失")
            if asset.get("id") in seen_assets:
                errors.append(f"assets[{index}].id 重复")
            seen_assets.add(str(asset.get("id")))
            if asset.get("kind") not in ASSET_KINDS:
                errors.append(f"assets[{index}].kind 无效")
            if asset.get("status") not in ASSET_STATES:
                errors.append(f"assets[{index}].status 无效")
            if asset.get("source") not in ASSET_SOURCES:
                errors.append(f"assets[{index}].source 无效")
            if asset.get("status") == "ready" and not has_real_asset_source(asset):
                errors.append(f"assets[{index}] ready 时必须保留 attachmentId、nodeId 或 imageUrl 证据")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init", help="归一化输入并创建独立工作台 JSON")
    init_parser.add_argument("--input", type=Path, required=True)
    init_parser.add_argument("--output", type=Path, required=True)
    compose_parser = subparsers.add_parser("compose", help="合成所有镜头最终提示词")
    compose_parser.add_argument("path", type=Path)
    compose_parser.add_argument("--write", action="store_true")
    validate_parser = subparsers.add_parser("validate", help="验证工作台 JSON")
    validate_parser.add_argument("path", type=Path)
    args = parser.parse_args()

    if args.command == "init":
        payload = build(read_json(args.input))
        errors = validate(payload)
        if errors:
            print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
            return 1
        write_json(args.output, payload)
        print(json.dumps({"ok": True, "output": str(args.output), "shots": len(payload["shots"]), "assets": len(payload["assets"])}, ensure_ascii=False))
        return 0

    payload = read_json(args.path)
    if args.command == "compose":
        style = str(payload.get("global_style", "")).strip()
        for shot in payload.get("shots", []):
            shot["final_prompt"] = compose_prompt(style, shot)
        payload["style_locked"] = True
        refresh_steps(payload)
        errors = validate(payload)
        if errors:
            print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
            return 1
        if args.write:
            write_json(args.path, payload)
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    errors = validate(payload)
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
