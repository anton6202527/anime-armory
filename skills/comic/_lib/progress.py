#!/usr/bin/env python3
"""Atomic, line-owned mutations for comic ``_进度.md``.

All stage writers share this helper so table aliases, atomic replacement and
transition evidence cannot drift between individual stage scripts.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

try:  # macOS/Linux; the helper still works without advisory locking elsewhere.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


STAGE_ALIASES: dict[str, tuple[str, ...]] = {
    "原稿收尾": ("原稿收尾", "传统收尾"),
    "传统收尾": ("原稿收尾", "传统收尾"),
}


def _atomic_write(path: Path, text: str) -> None:
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(text, encoding="utf-8")
    os.replace(pending, path)


def _append_event(root: Path, event: Mapping[str, Any]) -> None:
    path = root / "生产数据" / "progress_transitions.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(json.dumps(dict(event), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def update_stage(
    root: Path,
    chapter: str,
    stage: str,
    value: str,
    *,
    aliases: Iterable[str] = (),
    evidence: str = "",
    actor: str = "stage_script",
) -> bool:
    root = root.expanduser().resolve()
    path = root / "_进度.md"
    if not path.is_file():
        return False
    candidates = tuple(dict.fromkeys((*STAGE_ALIASES.get(stage, (stage,)), *aliases)))
    lock_path = path.with_name(f".{path.name}.lock")
    lock_path.touch(exist_ok=True)
    old_value = ""
    updated = False
    with lock_path.open("r+") as lock:
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        lines = path.read_text(encoding="utf-8").splitlines()
        headers: list[str] = []
        out: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|"):
                cells = [cell.strip() for cell in stripped.strip("|").split("|")]
                if cells and cells[0] == "话":
                    headers = cells
                elif headers and len(cells) >= len(headers) and cells[0] == chapter:
                    column = next((item for item in candidates if item in headers), "")
                    if column:
                        index = headers.index(column)
                        old_value = cells[index]
                        if cells[index] != value:
                            cells[index] = value
                            line = "| " + " | ".join(cells) + " |"
                            updated = True
            out.append(line)
        if updated:
            _atomic_write(path, "\n".join(out) + "\n")
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    if updated:
        _append_event(root, {
            "kind": "comic_progress_transition",
            "schema_version": 1,
            "recorded_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "chapter": chapter,
            "stage": stage,
            "from": old_value,
            "to": value,
            "actor": actor,
            "evidence": evidence,
        })
    return updated


def update_checklist(root: Path, targets: Mapping[str, bool]) -> bool:
    root = root.expanduser().resolve()
    path = root / "_进度.md"
    if not path.is_file():
        return False
    lock_path = path.with_name(f".{path.name}.lock")
    lock_path.touch(exist_ok=True)
    changed = False
    with lock_path.open("r+") as lock:
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        out: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("- [") and "]" in stripped:
                label = stripped.split("]", 1)[1].strip()
                if label in targets:
                    desired = f"- [{'x' if targets[label] else ' '}] {label}"
                    indent = line[: len(line) - len(line.lstrip())]
                    replacement = indent + desired
                    changed = changed or replacement != line
                    line = replacement
            out.append(line)
        if changed:
            _atomic_write(path, "\n".join(out) + "\n")
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return changed
