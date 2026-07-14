#!/usr/bin/env python3
"""Cross-episode subtitle/name/audio/register truth contract."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping

KIND = "n2d_series_consistency"
VERSION = 1


def path(root: str | Path) -> Path:
    return Path(root) / "设定库" / "series_consistency.json"


def _load_json(file: Path) -> Dict[str, Any]:
    try:
        value = json.loads(file.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def load(root: str | Path) -> Dict[str, Any]:
    return _load_json(path(root))


def _settings_text(root: Path) -> str:
    try:
        return (root / "_设置.md").read_text(encoding="utf-8")
    except OSError:
        return ""


def required(root: str | Path) -> bool:
    """Require the baseline for multi-episode/long-running/publish projects."""
    root_path = Path(root)
    progress = ""
    try:
        progress = (root_path / "_进度.md").read_text(encoding="utf-8")
    except OSError:
        pass
    episode_count = len(set(re.findall(r"第\s*\d+\s*集", progress)))
    settings = _settings_text(root_path).lower()
    long_or_publish = any(token in settings for token in (
        "多集长线", "长篇量产", "publish_candidate", "paid_distribution", "公开发布", "付费投放",
    ))
    return episode_count >= 2 or long_or_publish


def _identity_rows(root: Path) -> List[Dict[str, Any]]:
    data = _load_json(root / "出图" / "共享" / "identity_registry.json")
    return [dict(row) for row in data.get("characters") or [] if isinstance(row, Mapping)]


def scaffold(root: str | Path) -> Dict[str, Any]:
    root_path = Path(root)
    canonical: Dict[str, Any] = {}
    registers: Dict[str, Any] = {}
    for idx, row in enumerate(_identity_rows(root_path), 1):
        cid = str(row.get("id") or row.get("character_id") or f"CHAR_{idx:02d}")
        name = str(row.get("name") or row.get("canonical_name") or "")
        canonical[cid] = {"canonical_name": name, "forbidden_variants": []}
        if cid.startswith("BEAST_"):
            formality = "具名妖魔按角色卡保持非人身份语气；措辞服务剧情性格，不使用现代网络梗或无来源卖萌口吻。"
        else:
            formality = "按角色卡身份、年龄与关系保持稳定语域；不使用无来源现代网络梗。"
        registers[cid] = {"formality": formality, "anchors": [], "forbidden_terms": [], "sentence_len_max": None}
    return {
        "kind": KIND,
        "version": VERSION,
        "status": "draft",
        "subtitle_style": {
            "zh_font_paths": ["/System/Library/Fonts/STHeiti Medium.ttc"],
            "en_font_paths": ["/System/Library/Fonts/Supplemental/Arial.ttf"],
            "zh_size_px": 38,
            "en_size_px": 28,
            "zh_fill": "#FFFFFF",
            "en_fill": "#EBEBEB",
            "outline_fill": "#0A0A0A",
            "zh_outline_px": 4,
            "en_outline_px": 3,
            "bottom_margin_px": 130,
            "safe_width_margin_px": 60,
        },
        "canonical_names": canonical,
        "dialogue_registers": registers,
        "audio_baseline": {"target_lufs": -16.0, "tolerance_lu": 1.0, "true_peak_dbtp": -1.0},
        "note": "填完后设 status=confirmed；多集长线/发布项目的字幕、人名、语域和响度以此为剧级真值。",
    }


def write_missing(root: str | Path) -> Path:
    target = path(root)
    generated = scaffold(root)
    existing = load(root) if target.is_file() else {}
    if existing:
        merged = dict(existing)
        for section in ("canonical_names", "dialogue_registers"):
            current = dict(existing.get(section) or {}) if isinstance(existing.get(section), Mapping) else {}
            for key, value in (generated.get(section) or {}).items():
                current.setdefault(key, value)
            merged[section] = current
        for key in ("subtitle_style", "audio_baseline", "note"):
            if key not in merged:
                merged[key] = generated[key]
        generated = merged
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(generated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    return target


def _episode_text(root: Path, episode: str) -> str:
    files = [
        root / "脚本" / episode / "voiceover.txt",
        root / "脚本" / episode / "字幕_中文.srt",
        root / "脚本" / episode / "字幕中.srt",
    ]
    out = []
    for file in files:
        try:
            out.append(file.read_text(encoding="utf-8"))
        except OSError:
            pass
    return "\n".join(out)


def _character_dialogue_lines(text: str, character_id: str, canonical_name: str) -> List[str]:
    """Return only lines explicitly attributed to a character; avoid global register false positives."""
    markers = [token for token in (character_id, canonical_name) if token]
    rows: List[str] = []
    for line in text.splitlines():
        # Free-form comments, summaries and subtitle prose may mention a character
        # without being that character's spoken line.  Only bracket-attributed
        # voiceover rows are eligible for dialogue-register enforcement.
        if "]" not in line and "】" not in line:
            continue
        header = line.split("]", 1)[0] if "]" in line else line.split("】", 1)[0]
        if any(token in header for token in markers):
            rows.append(line.split("]", 1)[-1].split("】", 1)[-1].strip())
    return rows


def _spoken_segments(line: str) -> List[str]:
    """Split one attributed voiceover row into actual spoken sentences.

    ``sentence_len_max`` is a per-sentence performance constraint, not a
    per-row limit.  Rows may deliberately contain several sentences or the
    ``||`` breath/cut marker, and may end in non-spoken retention labels.
    """
    spoken = re.sub(r"\s+[⚡💥🪝][^。！？!?；;]*$", "", str(line or "")).strip()
    return [
        segment.strip()
        for segment in re.split(r"\|\||[。！？!?；;]+", spoken)
        if segment.strip()
    ]


def validate(root: str | Path, episode: str, *, phase: str = "full") -> List[Dict[str, str]]:
    root_path = Path(root)
    data = load(root_path)
    issues: List[Dict[str, str]] = []

    def issue(code: str, message: str) -> None:
        issues.append({"code": code, "severity": "block", "message": message})

    if data.get("kind") != KIND or int(data.get("version") or 0) < VERSION:
        issue("series_consistency_missing", "缺有效 series_consistency.json。")
        return issues
    if str(data.get("status") or "").lower() not in {"confirmed", "approved", "ready"}:
        issue("series_consistency_unconfirmed", "剧级一致性合同尚未 confirmed。")
    canonical = data.get("canonical_names") if isinstance(data.get("canonical_names"), Mapping) else {}
    registers = data.get("dialogue_registers") if isinstance(data.get("dialogue_registers"), Mapping) else {}
    for idx, row in enumerate(_identity_rows(root_path), 1):
        cid = str(row.get("id") or row.get("character_id") or f"CHAR_{idx:02d}")
        name_row = canonical.get(cid) if isinstance(canonical.get(cid), Mapping) else {}
        if not str(name_row.get("canonical_name") or "").strip():
            issue("canonical_name_missing", f"{cid} 缺 canonical_name。")
        register = registers.get(cid) if isinstance(registers.get(cid), Mapping) else {}
        if not str(register.get("formality") or "").strip() or not isinstance(register.get("anchors"), list) or not isinstance(register.get("forbidden_terms"), list):
            issue("dialogue_register_missing", f"{cid} 缺 formality/anchors/forbidden_terms 语域合同。")
    text = _episode_text(root_path, episode)
    for cid, row in canonical.items():
        if not isinstance(row, Mapping):
            continue
        for variant in row.get("forbidden_variants") or []:
            token = str(variant or "").strip()
            if token and token in text:
                issue("forbidden_name_variant", f"{episode} 出现 {cid} 的禁用异体/错字「{token}」。")
    for cid, row in registers.items():
        if not isinstance(row, Mapping):
            continue
        name_row = canonical.get(cid) if isinstance(canonical.get(cid), Mapping) else {}
        dialogue_lines = _character_dialogue_lines(text, str(cid), str(name_row.get("canonical_name") or ""))
        if dialogue_lines and not [str(x).strip() for x in (row.get("anchors") or []) if str(x).strip()]:
            issue("dialogue_register_anchors_missing", f"{episode} 的 {cid} 有台词但语域 anchors 为空。")
        for token_raw in row.get("forbidden_terms") or []:
            token = str(token_raw or "").strip()
            if token and any(token in line for line in dialogue_lines):
                issue("dialogue_register_forbidden_term", f"{episode} 出现 {cid} 的语域禁用词「{token}」。")
        limit = row.get("sentence_len_max")
        if limit not in (None, ""):
            try:
                segments = [segment for line in dialogue_lines for segment in _spoken_segments(line)]
                too_long = [segment for segment in segments if len(re.sub(r"\s+", "", segment)) > int(limit)]
            except (TypeError, ValueError):
                issue("dialogue_register_sentence_limit_invalid", f"{cid}.sentence_len_max 必须是正整数或 null。")
            else:
                if int(limit) <= 0:
                    issue("dialogue_register_sentence_limit_invalid", f"{cid}.sentence_len_max 必须是正整数或 null。")
                elif too_long:
                    issue("dialogue_register_sentence_too_long", f"{episode} 的 {cid} 有 {len(too_long)} 句超过 sentence_len_max={limit}。")
    if phase == "full":
        style = data.get("subtitle_style") if isinstance(data.get("subtitle_style"), Mapping) else {}
        for key in ("zh_font_paths", "zh_size_px", "zh_fill", "outline_fill", "zh_outline_px", "bottom_margin_px", "safe_width_margin_px"):
            if key not in style or style.get(key) in (None, "", []):
                issue("subtitle_style_incomplete", f"subtitle_style 缺 {key}。")
        audio = data.get("audio_baseline") if isinstance(data.get("audio_baseline"), Mapping) else {}
        for key in ("target_lufs", "tolerance_lu", "true_peak_dbtp"):
            try:
                float(audio.get(key))
            except (TypeError, ValueError):
                issue("audio_baseline_incomplete", f"audio_baseline.{key} 缺失或不是数值。")
    return issues


__all__ = ["KIND", "VERSION", "load", "path", "required", "scaffold", "validate", "write_missing"]
