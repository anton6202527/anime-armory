#!/usr/bin/env python3
"""Truthful Comic text-renderer selection, glyph proof and execution.

The adapter deliberately separates *being able to discover a binary* from
*having rendered the current text*. Publication code may only claim support
after a renderer receipt and, when a font is supplied, a glyph receipt are
bound to the exact request.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Mapping


REGISTRY_REL = Path("生产数据") / "text_renderer_adapters.json"
PROTOCOL = "comic_text_rgba_v1"


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_registry(root: Path | None) -> list[dict[str, Any]]:
    if root is None:
        return []
    try:
        payload = json.loads((root.resolve() / REGISTRY_REL).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = payload.get("adapters") if isinstance(payload, Mapping) else []
    return [dict(row) for row in rows or [] if isinstance(row, Mapping)]


def _valid_command(value: Any) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        return []
    executable = value[0]
    resolved = executable if Path(executable).is_absolute() else shutil.which(executable)
    if not resolved or not Path(resolved).is_file():
        return []
    return [str(resolved), *value[1:]]


def _registered_adapters(root: Path | None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in _load_registry(root):
        command = _valid_command(row.get("command"))
        supports = sorted({str(item) for item in row.get("supports") or [] if str(item).strip()})
        if str(row.get("protocol") or "") != PROTOCOL or not command or not supports:
            continue
        result.append({
            "adapter_id": str(row.get("id") or row.get("adapter_id") or command[0]),
            "status": "executable",
            "supports": supports,
            "command": command,
            "protocol": PROTOCOL,
            "source": str(REGISTRY_REL),
        })
    return result


def probe(root: Path | None = None) -> dict[str, Any]:
    """Return the strongest executable adapter, never an aspirational one."""
    registered = _registered_adapters(root)
    if registered:
        return registered[0]
    pango = shutil.which("pango-view")
    harfbuzz = shutil.which("hb-shape")
    if pango and harfbuzz:
        return {
            "adapter_id": "pango_harfbuzz",
            "status": "executable",
            "supports": ["complex_shaping", "rtl", "cjk_horizontal", "latin_horizontal", "font_fallback"],
            "commands": {"pango_view": pango, "hb_shape": harfbuzz},
            "protocol": "builtin_pango_harfbuzz_v1",
        }
    return {
        "adapter_id": "pillow_draft",
        "status": "draft_only",
        "supports": ["cjk_horizontal", "latin_horizontal"],
        "missing": [name for name, value in (("pango-view", pango), ("hb-shape", harfbuzz)) if not value],
        "reason": "professional complex shaping adapter is unavailable; Pillow remains a draft renderer",
    }


def required_capabilities(*, language_mode: str, direction: str, writing_mode: str = "horizontal-tb") -> list[str]:
    language = str(language_mode or "").lower()
    direction_key = str(direction or "").lower()
    writing_key = str(writing_mode or "horizontal-tb").lower()
    required: list[str] = []
    if writing_key.startswith("vertical"):
        required.append("vertical_cjk")
    elif any(token in language for token in ("cjk", "chinese", "japanese", "korean", "zh", "ja", "ko", "中文", "日文", "韩")):
        required.append("cjk_horizontal")
    else:
        required.append("latin_horizontal")
    if direction_key in {"rtl", "right-to-left", "从右到左"}:
        required.extend(["rtl", "complex_shaping"])
    elif any(token in language for token in ("arab", "hebrew", "thai", "devanagari", "阿拉伯", "希伯来", "泰", "天城")):
        required.append("complex_shaping")
    return list(dict.fromkeys(required))


def suitability(
    *, language_mode: str, direction: str, writing_mode: str = "horizontal-tb",
    available: dict[str, Any] | None = None,
) -> dict[str, Any]:
    adapter = dict(available or probe())
    required = required_capabilities(language_mode=language_mode, direction=direction, writing_mode=writing_mode)
    supported = set(adapter.get("supports") or [])
    suitable = all(item in supported for item in required)
    return {
        **adapter,
        "required_capability": required[0],
        "required_capabilities": required,
        "suitable": suitable,
        "publication_claim_allowed": adapter.get("status") == "executable" and suitable,
    }


def select_renderer(
    *, language_mode: str, direction: str, writing_mode: str = "horizontal-tb",
    root: Path | None = None, available: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select an adapter and bind the decision to its capabilities."""
    candidates = [dict(available)] if available is not None else [*_registered_adapters(root), probe(None)]
    evaluated = [suitability(
        language_mode=language_mode, direction=direction, writing_mode=writing_mode, available=candidate,
    ) for candidate in candidates]
    chosen = next((item for item in evaluated if item["publication_claim_allowed"]), None)
    if chosen is None:
        chosen = next((item for item in evaluated if item["suitable"]), evaluated[-1])
    decision = {
        **chosen,
        "schema_version": 2,
        "kind": "comic_text_renderer_selection",
        "language_mode": language_mode,
        "direction": direction,
        "writing_mode": writing_mode,
    }
    decision["selection_sha256"] = _canonical_sha(decision)
    return decision


def _resolve_font(font_path: str | Path, family: str = "") -> Path | None:
    path = Path(font_path).expanduser() if str(font_path or "").strip() else None
    if path and path.is_file():
        return path.resolve()
    fc_match = shutil.which("fc-match")
    if not fc_match or not family.strip():
        return None
    proc = subprocess.run(
        [fc_match, "-f", "%{file}\n", family], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    first = (proc.stdout or "").splitlines()
    candidate = Path(first[0]).expanduser() if proc.returncode == 0 and first else None
    return candidate.resolve() if candidate and candidate.is_file() else None


def validate_glyph_coverage(
    text: str, *, font_path: str | Path = "", font_family: str = "", hb_shape: str = "",
) -> dict[str, Any]:
    """Use HarfBuzz's actual shaping result; gid=0 is missing-glyph evidence."""
    font = _resolve_font(font_path, font_family)
    binary = hb_shape or shutil.which("hb-shape") or ""
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "kind": "comic_glyph_coverage_receipt",
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "font_path": str(font or ""),
        "font_sha256": hashlib.sha256(font.read_bytes()).hexdigest() if font else "",
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    if not text:
        return {**receipt, "status": "pass", "missing_glyphs": [], "reason": "empty_text"}
    if not font or not binary:
        return {**receipt, "status": "unavailable", "missing_glyphs": [], "reason": "font_or_hb_shape_unavailable"}
    proc = subprocess.run(
        [binary, str(font), text, "--output-format=json"], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    missing: list[int] = []
    try:
        rows = json.loads(proc.stdout or "[]")
        for index, row in enumerate(rows if isinstance(rows, list) else []):
            glyph_id = row.get("g") if isinstance(row, Mapping) else None
            if glyph_id in {0, "0", ".notdef", "gid0"}:
                missing.append(index)
    except ValueError:
        rows = []
    return {
        **receipt,
        "status": "pass" if proc.returncode == 0 and rows and not missing else "fail",
        "missing_glyphs": missing,
        "shape_returncode": proc.returncode,
        "stderr": (proc.stderr or "")[-1000:],
    }


def _registered_command(adapter: Mapping[str, Any], request_path: Path, output_path: Path) -> list[str]:
    command = list(adapter.get("command") or [])
    rendered = [token.replace("{request}", str(request_path)).replace("{output}", str(output_path)) for token in command]
    if not any("{request}" in token for token in command):
        rendered.extend(["--request", str(request_path)])
    if not any("{output}" in token for token in command):
        rendered.extend(["--output", str(output_path)])
    return rendered


def render_text_rgba(
    request: Mapping[str, Any], output_path: Path, *, root: Path | None = None,
    adapter: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a professional adapter and validate its real PNG output."""
    text = str(request.get("text") or "")
    selection = dict(adapter or select_renderer(
        language_mode=str(request.get("language_mode") or "cjk"),
        direction=str(request.get("direction") or "ltr"),
        writing_mode=str(request.get("writing_mode") or "horizontal-tb"), root=root,
    ))
    request_body = {"protocol": PROTOCOL, **dict(request), "selection_sha256": selection.get("selection_sha256", "")}
    request_sha = _canonical_sha(request_body)
    if not selection.get("publication_claim_allowed"):
        return {
            "schema_version": 1, "kind": "comic_text_render_receipt",
            "status": "fallback_allowed" if selection.get("suitable") else "blocked",
            "renderer": selection.get("adapter_id"), "request_sha256": request_sha,
            "output_path": "", "output_sha256": "", "publication_claim_allowed": False,
            "reason": selection.get("reason") or "required professional capability unavailable",
        }
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pending = output_path.with_name(f".{output_path.name}.pending.{os.getpid()}.png")
    if pending.exists():
        pending.unlink()
    if selection.get("protocol") == PROTOCOL:
        with tempfile.TemporaryDirectory(prefix="comic-text-") as folder:
            request_path = Path(folder) / "request.json"
            request_path.write_text(json.dumps(request_body, ensure_ascii=False, sort_keys=True), encoding="utf-8")
            proc = subprocess.run(
                _registered_command(selection, request_path, pending), text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
    else:
        pango = str((selection.get("commands") or {}).get("pango_view") or "")
        font = str(request.get("font_family") or "Sans")
        font_size = max(1, int(request.get("font_size") or 32))
        width = max(1, int(request.get("width") or 1024))
        markup = f"<span>{escape(text)}</span>"
        proc = subprocess.run(
            [pango, "--no-display", "--markup", "--text", markup, "--font", f"{font} {font_size}", "--width", str(width), "--output", str(pending)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
    valid, size = False, [0, 0]
    if proc.returncode == 0 and pending.is_file():
        try:
            from PIL import Image
            with Image.open(pending) as image:
                image.verify()
            with Image.open(pending) as image:
                size = [int(image.width), int(image.height)]
                valid = image.format == "PNG" and image.mode in {"RGBA", "LA", "P", "RGB"}
        except (ImportError, OSError):
            valid = False
    if not valid:
        if pending.exists():
            pending.unlink()
        return {
            "schema_version": 1, "kind": "comic_text_render_receipt", "status": "failed",
            "renderer": selection.get("adapter_id"), "request_sha256": request_sha,
            "output_path": "", "output_sha256": "", "publication_claim_allowed": False,
            "returncode": proc.returncode, "stderr": (proc.stderr or "")[-2000:],
        }
    os.replace(pending, output_path)
    return {
        "schema_version": 1, "kind": "comic_text_render_receipt", "status": "rendered",
        "renderer": selection.get("adapter_id"), "request_sha256": request_sha,
        "output_path": str(output_path), "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "size": size, "publication_claim_allowed": True,
    }
