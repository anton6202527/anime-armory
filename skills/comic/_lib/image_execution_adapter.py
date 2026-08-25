#!/usr/bin/env python3
"""Resolve Comic image settings to a truthful executable adapter.

Capability planning and local execution are deliberately separate.  A model
may accept references without this checkout having a runner for it.  Unknown
routes are therefore ``planning_only`` rather than silently falling back to
Codex.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import shlex
from typing import Any, Mapping


REGISTRY_REL = Path("生产数据") / "image_execution_adapters.json"
KIND = "comic_image_execution_adapter_registry"
FORBIDDEN = {"|", ";", "&&", "||", ">", "<"}


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def _tokens(value: Any) -> list[str]:
    if isinstance(value, list):
        tokens = [str(item) for item in value]
    else:
        try:
            tokens = shlex.split(str(value or ""))
        except ValueError:
            return []
    if not tokens or any(token in FORBIDDEN for token in tokens):
        return []
    return tokens


def _registry(root: Path, model: str, channel: str) -> dict[str, Any] | None:
    path = root / REGISTRY_REL
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(registry, Mapping) or registry.get("kind") not in {None, "", KIND}:
        return None
    for row in registry.get("adapters") or []:
        if not isinstance(row, Mapping):
            continue
        if _norm(str(row.get("model") or "")) not in {"", "*", _norm(model)}:
            continue
        if _norm(str(row.get("channel") or "")) not in {"", "*", _norm(channel)}:
            continue
        command = _tokens(row.get("command"))
        if command:
            return {
                "adapter_id": str(row.get("adapter_id") or "project_adapter"),
                "status": "executable", "command": command,
                "source": REGISTRY_REL.as_posix(),
            }
    return None


def resolve_execution_adapter(root: Path, model: str, channel: str, *, repo_root: Path) -> dict[str, Any]:
    registered = _registry(root, model, channel)
    if registered:
        return registered
    combined = _norm(f"{model} {channel}")
    if any(token in combined for token in ("dreamina", "即梦")):
        return {
            "adapter_id": "dreamina_cli", "status": "executable",
            "command": ["{python}", str(repo_root / "skills/comic/comic-image/scripts/dreamina_panel_runner.py")],
            "source": "builtin",
        }
    if any(token in combined for token in ("gpt image", "gpt-image", "codex cli", "openai")):
        return {
            "adapter_id": "codex_cli", "status": "executable",
            "command": ["{python}", str(repo_root / "skills/comic/comic-image/scripts/codex_panel_runner.py")],
            "source": "builtin",
        }
    if "manual" in combined or "手动" in combined:
        return {
            "adapter_id": "manual", "status": "manual", "command": [],
            "reason": "manual route has no continuous executable adapter",
        }
    return {
        "adapter_id": "unavailable", "status": "planning_only", "command": [],
        "reason": f"{model or 'unknown model'} via {channel or 'unknown channel'} has capability planning only; register a project adapter",
    }
