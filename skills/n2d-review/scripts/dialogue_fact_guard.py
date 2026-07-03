#!/usr/bin/env python3
"""Dialogue/fact contract guard for native A/V video generation.

The expensive native-speech path needs two deterministic safeguards:

1. every physical video Clip owns a disjoint slice of the dialogue/narration
   track and any screen-text overlay track;
2. numeric facts such as age/height/spiritual-root are copied verbatim rather
   than paraphrased by the video backend.

This script builds a machine-readable contract from the episode storyboard and
checks the current text artifacts for overlap or fact drift. Screen text is a
post/compose overlay contract, not text the video model should paint into frames.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


KIND = "n2d_dialogue_fact_contract"
VERSION = 1

VOICEOVER_RE = re.compile(r"^\[镜头\s*(\d+)\s*·([^·\]]+)(?:·[^\]]*)*\]\s*(.+?)\s*$")
CLIP_NUM_RE = re.compile(r"Clip[_\s-]?(\d+)", re.IGNORECASE)
EP_NUM_RE = re.compile(r"(\d+)")
HOOK_MARKERS_RE = re.compile(r"[⚡💥🪝]\s*$")
NARRATION_ROLES = {"旁白", "narrator", "voiceover", "vo", "系统", "system", "sys"}
SCREEN_TEXT_KEYS = ("screen_text_lines", "onscreen_text_lines", "screen_text", "onscreen_text", "overlay_text")
DAILY_TRIP_HISTORICAL_CONTEXT_RE = re.compile(
    r"(昨日|昨天|昨儿|今日|今天|今儿|白日|已经|已|一共|极限|重量|挑水后|压到天黑|天黑|活全干完|没歇着|看见了)"
)
NEGATIVE_OR_FORBIDDEN_CONTEXT_RE = re.compile(
    r"(forbidden(?:_fact)?_values|禁止|不得|不要|不能|do\s+not|must\s+not|forbid)",
    re.IGNORECASE,
)
FORBIDDEN_VALUES_LINE_RE = re.compile(r"forbidden(?:_fact)?_values", re.IGNORECASE)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def normalize_episode(ep: str) -> str:
    text = str(ep or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = EP_NUM_RE.search(text)
    return f"第{int(m.group(1))}集" if m else text


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def contract_path(root: Path, episode: str) -> Path:
    return production_dir(root) / f"dialogue_fact_contract_{episode}.json"


def report_path(root: Path, episode: str) -> Path:
    return production_dir(root) / f"dialogue_fact_contract_{episode}.md"


def rel_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def normalize_clip(value: Any, fallback: Optional[int] = None) -> str:
    text = str(value or "")
    m = CLIP_NUM_RE.search(text)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    if fallback is not None:
        return f"Clip_{fallback:02d}"
    return text.strip()


def clean_dialogue(text: str) -> str:
    return HOOK_MARKERS_RE.sub("", str(text or "").strip()).strip()


def is_narration_role(role: Any) -> bool:
    text = str(role or "").strip()
    low = text.lower()
    return "旁白" in text or low in NARRATION_ROLES


def parse_voiceover(root: Path, episode: str) -> Dict[int, Dict[str, Any]]:
    path = root / "脚本" / episode / "voiceover.txt"
    entries: Dict[int, Dict[str, Any]] = {}
    for lineno, line in enumerate(read_text(path).splitlines(), start=1):
        m = VOICEOVER_RE.match(line.strip())
        if not m:
            continue
        idx = int(m.group(1))
        role = m.group(2).strip()
        raw_text = m.group(3).strip()
        entries[idx] = {
            "index": idx,
            "role": role,
            "text": clean_dialogue(raw_text),
            "raw_text": raw_text,
            "source": f"{rel_to_root(root, path)}:{lineno}",
        }
    return entries


def storyboard_path(root: Path, episode: str) -> Path:
    return root / "脚本" / episode / "storyboard.json"


def storyboard_clips(root: Path, episode: str) -> List[Dict[str, Any]]:
    data = read_json(storyboard_path(root, episode))
    clips = data.get("clips") if isinstance(data, dict) else None
    return [c for c in clips if isinstance(c, dict)] if isinstance(clips, list) else []


def _clip_voiceover_indices(clip: Mapping[str, Any]) -> List[int]:
    out: List[int] = []
    for raw in clip.get("voiceover_indices") or []:
        try:
            out.append(int(raw))
        except (TypeError, ValueError):
            continue
    return out


def _screen_text_entry(raw: Any, *, source_field: str, ordinal: int) -> Optional[Dict[str, Any]]:
    if isinstance(raw, Mapping):
        text = str(raw.get("text") or raw.get("value") or "").strip()
        if not text:
            return None
        return {
            "id": str(raw.get("id") or f"{source_field}_{ordinal}"),
            "text": text,
            "placement": str(raw.get("placement") or raw.get("position") or "auto"),
            "duration": str(raw.get("duration") or raw.get("window") or ""),
            "purpose": str(raw.get("purpose") or ""),
            "render_policy": str(raw.get("render_policy") or "compose_overlay_only"),
            "source_field": source_field,
        }
    text = str(raw or "").strip()
    if not text or text in {"无", "none", "None", "n/a"}:
        return None
    return {
        "id": f"{source_field}_{ordinal}",
        "text": text,
        "placement": "auto",
        "duration": "",
        "purpose": "",
        "render_policy": "compose_overlay_only",
        "source_field": source_field,
    }


def _clip_screen_text_entries(clip: Mapping[str, Any]) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    ordinal = 1
    for key in SCREEN_TEXT_KEYS:
        raw = clip.get(key)
        if raw is None:
            continue
        values = raw if isinstance(raw, list) else [raw]
        for item in values:
            entry = _screen_text_entry(item, source_field=key, ordinal=ordinal)
            ordinal += 1
            if entry:
                entries.append(entry)
    return entries


def _screen_text_key(text: Any) -> str:
    return re.sub(r"\s+", "", str(text or "").strip().lower())


def _field_line(text: str, field: str) -> str:
    pattern = re.compile(rf"^[\-*\s]*{re.escape(field)}(?:档)?\s*[:：]\s*(.+)$", re.MULTILINE)
    m = pattern.search(text or "")
    return m.group(1).strip() if m else ""


def _character_name(path: Path, text: str) -> str:
    m = re.search(r"^#\s*角色卡[:：]\s*(.+?)\s*$", text or "", re.MULTILINE)
    if m:
        return m.group(1).strip()
    return path.stem


def _forbidden_age_values(canonical: str) -> List[str]:
    if "十四" in canonical or re.search(r"\b14\s*岁", canonical):
        return ["十三岁", "十五岁", "十六岁", "13岁", "15岁", "16岁", "13 岁", "15 岁", "16 岁"]
    return []


def collect_character_facts(root: Path) -> List[Dict[str, Any]]:
    char_dir = root / "设定库" / "characters"
    facts: List[Dict[str, Any]] = []
    if not char_dir.is_dir():
        return facts
    for path in sorted(char_dir.glob("*.md")):
        if path.name.startswith("_"):
            continue
        text = read_text(path)
        name = _character_name(path, text)
        rel = rel_to_root(root, path)
        age = _field_line(text, "年龄")
        if age:
            canonical = age.rstrip("。；;")
            facts.append({
                "character": name,
                "key": "age",
                "canonical": canonical,
                "allowed_values": [canonical, canonical.replace("十四", "14")],
                "forbidden_values": _forbidden_age_values(canonical),
                "source": rel,
                "policy": "numeric_fact_no_paraphrase",
            })
        height = _field_line(text, "身高")
        if height:
            height_forbidden = []
            if name == "贺平生":
                height_forbidden = ["170cm", "175cm", "180cm", "一米七", "一米八"]
            facts.append({
                "character": name,
                "key": "height",
                "canonical": height.rstrip("。；;"),
                "allowed_values": ["少年偏矮", "155-160cm", "155 到 160cm", "155到160cm"],
                "forbidden_values": height_forbidden,
                "source": rel,
                "policy": "body_scale_no_drift",
            })
        if "五行灵根" in text and name.startswith("贺平生"):
            facts.append({
                "character": name,
                "key": "spiritual_root",
                "canonical": "五行灵根",
                "allowed_values": ["五行灵根", "金木水火土俱全"],
                "forbidden_values": ["天灵根", "单灵根", "火灵根", "变异灵根"],
                "source": rel,
                "policy": "setting_fact_no_paraphrase",
            })
    return facts


def collect_episode_quantity_facts(root: Path, episode: str) -> List[Dict[str, Any]]:
    text = "\n".join(entry.get("text", "") for entry in parse_voiceover(root, episode).values())
    facts: List[Dict[str, Any]] = []
    if "二十趟" in text or "20趟" in text:
        facts.append({
            "character": "剧情账本",
            "key": "daily_water_trips",
            "canonical": "一天至少二十趟",
            "allowed_values": ["一天至少二十趟", "二十趟", "20趟"],
            "forbidden_values": ["十五趟", "十六趟", "15趟", "16趟", "十几趟"],
            "source": rel_to_root(root, root / "脚本" / episode / "voiceover.txt"),
            "policy": "quantity_fact_no_paraphrase",
        })
    if "第五次" in text or "第五趟" in text:
        facts.append({
            "character": "剧情账本",
            "key": "night_water_trip",
            "canonical": "第五次来到水边",
            "allowed_values": ["第五次", "第五趟", "5次", "5趟"],
            "forbidden_values": ["第四次", "第六次", "四趟", "六趟", "4次", "6次", "4趟", "6趟"],
            "source": rel_to_root(root, root / "脚本" / episode / "voiceover.txt"),
            "policy": "quantity_fact_no_paraphrase",
        })
    return facts


def build_contract(root: Path, episode: str) -> Dict[str, Any]:
    episode = normalize_episode(episode)
    voiceover = parse_voiceover(root, episode)
    clips: List[Dict[str, Any]] = []
    for ordinal, clip in enumerate(storyboard_clips(root, episode), start=1):
        indices = _clip_voiceover_indices(clip)
        lines = []
        narration_lines = []
        character_lines = []
        for idx in indices:
            entry = voiceover.get(idx)
            line = {
                "index": idx,
                "role": entry.get("role") if entry else "missing",
                "text": entry.get("text") if entry else "",
                "source": entry.get("source") if entry else "",
            }
            lines.append(line)
            if is_narration_role(line.get("role")):
                narration_lines.append(line)
            else:
                character_lines.append(line)
        screen_text_lines = _clip_screen_text_entries(clip)
        clips.append({
            "clip": normalize_clip(clip.get("id"), ordinal),
            "storyboard_clip_id": str(clip.get("id") or ""),
            "label": str(clip.get("label") or ""),
            "source_clip_id": str(clip.get("source_clip_id") or ""),
            "split_segment": str(clip.get("split_segment") or ""),
            "allowed_voiceover_indices": indices,
            "allowed_narration_indices": [line["index"] for line in narration_lines],
            "allowed_character_dialogue_indices": [line["index"] for line in character_lines],
            "allowed_spoken_lines": lines,
            "allowed_dialogue": lines,
            "allowed_narration": narration_lines,
            "allowed_character_dialogue": character_lines,
            "screen_text_lines": screen_text_lines,
            "screen_text_policy": "compose_overlay_only; video_model_must_not_render_text; fact_locked",
            "dialogue_policy": (
                "three_track_contract; "
                "video_may_generate_only_listed_character_dialogue_no_extra_speech; "
                "narration_is_compose_stage_audio_only; "
                "screen_text_compose_overlay_only; "
                "do_not_repeat_previous_or_next_clip_dialogue_or_narration_or_screen_text; "
                "do_not_paraphrase_numeric_facts"
            ),
        })
    return {
        "kind": KIND,
        "version": VERSION,
        "episode": episode,
        "generated_at": now_iso(),
        "sources": {
            "voiceover": rel_to_root(root, root / "脚本" / episode / "voiceover.txt"),
            "storyboard": rel_to_root(root, storyboard_path(root, episode)),
            "character_cards": rel_to_root(root, root / "设定库" / "characters"),
        },
        "clips": clips,
        "facts": collect_character_facts(root) + collect_episode_quantity_facts(root, episode),
    }


def load_contract(root: Path, episode: str) -> Optional[Dict[str, Any]]:
    data = read_json(contract_path(root, episode))
    return data if isinstance(data, dict) else None


def native_speech_likely(root: Path, episode: str) -> bool:
    prompt_text = read_text(root / "出视频" / episode / "prompt" / "01_clips.md")
    route_text = read_text(root / "出视频" / episode / "prompt" / "video_model_routes.json")
    settings_text = read_text(root / "_设置.md")
    blob = "\n".join([prompt_text, route_text, settings_text])
    return any(token in blob for token in ("native_speech", "原生音画", "保留原片音轨"))


def _finding(severity: str, code: str, loc: Path | str, message: str) -> Dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "loc": str(loc),
        "message": message,
    }


def duplicate_storyboard_indices(root: Path, episode: str) -> List[Dict[str, Any]]:
    seen: Dict[int, List[str]] = {}
    for ordinal, clip in enumerate(storyboard_clips(root, episode), start=1):
        clip_key = normalize_clip(clip.get("id"), ordinal)
        for idx in _clip_voiceover_indices(clip):
            seen.setdefault(idx, []).append(clip_key)
    findings = []
    for idx, owners in sorted(seen.items()):
        if len(owners) > 1:
            findings.append(_finding(
                "block",
                "duplicate_voiceover_index",
                storyboard_path(root, episode),
                f"voiceover index {idx} is assigned to multiple physical clips: {', '.join(owners)}. "
                "Split relay may visually overlap, but dialogue ownership must be disjoint.",
            ))
    return findings


def duplicate_storyboard_screen_text(root: Path, episode: str) -> List[Dict[str, Any]]:
    seen: Dict[str, List[str]] = {}
    display: Dict[str, str] = {}
    for ordinal, clip in enumerate(storyboard_clips(root, episode), start=1):
        clip_key = normalize_clip(clip.get("id"), ordinal)
        for entry in _clip_screen_text_entries(clip):
            key = _screen_text_key(entry.get("text"))
            if not key:
                continue
            seen.setdefault(key, []).append(clip_key)
            display.setdefault(key, str(entry.get("text") or ""))
    findings = []
    for key, owners in sorted(seen.items()):
        if len(owners) > 1:
            findings.append(_finding(
                "block",
                "duplicate_screen_text_line",
                storyboard_path(root, episode),
                f"screen text {display.get(key)!r} is assigned to multiple physical clips: {', '.join(owners)}. "
                "Screen-text track must be disjoint; repeat only by creating an explicit new text card with a different purpose.",
            ))
    return findings


def _contract_clip_rows(contract: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    rows = contract.get("clips")
    return [r for r in rows if isinstance(r, Mapping)] if isinstance(rows, list) else []


def validate_contract_payload(root: Path, episode: str, contract: Mapping[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    path = contract_path(root, episode)
    if contract.get("kind") != KIND:
        findings.append(_finding("block", "contract_kind", path, f"dialogue fact contract kind must be {KIND}"))
    rows = _contract_clip_rows(contract)
    if not rows:
        findings.append(_finding("block", "contract_missing_clips", path, "dialogue fact contract has no clips[]"))
        return findings

    voiceover = parse_voiceover(root, episode)
    needed = {
        normalize_clip(clip.get("id"), ordinal)
        for ordinal, clip in enumerate(storyboard_clips(root, episode), start=1)
        if _clip_voiceover_indices(clip) or _clip_screen_text_entries(clip)
    }
    present = {normalize_clip(row.get("clip")) for row in rows}
    for missing in sorted(needed - present):
        findings.append(_finding("block", "contract_missing_clip", path, f"{missing} has storyboard voiceover_indices but no contract row"))

    seen: Dict[int, List[str]] = {}
    for row in rows:
        clip = normalize_clip(row.get("clip"))
        indices = row.get("allowed_voiceover_indices")
        screen_text = row.get("screen_text_lines") if isinstance(row.get("screen_text_lines"), list) else []
        if not isinstance(indices, list):
            findings.append(_finding("block", "contract_bad_dialogue_track", path, f"{clip} allowed_voiceover_indices must be a list"))
            indices = []
        if not indices and not screen_text:
            findings.append(_finding("warn", "contract_empty_tracks", path, f"{clip} has no dialogue/narration or screen_text track"))
        for raw in indices:
            try:
                idx = int(raw)
            except (TypeError, ValueError):
                findings.append(_finding("block", "contract_bad_index", path, f"{clip} has non-integer voiceover index: {raw!r}"))
                continue
            seen.setdefault(idx, []).append(clip)
            if idx not in voiceover:
                findings.append(_finding("block", "contract_unknown_index", path, f"{clip} references missing voiceover index {idx}"))
        policy = str(row.get("dialogue_policy") or "")
        if "do_not_repeat" not in policy or "numeric" not in policy or "screen_text" not in policy:
            findings.append(_finding("warn", "contract_policy_weak", path, f"{clip} dialogue_policy should forbid repeats and numeric paraphrase"))
        for entry in screen_text:
            if not isinstance(entry, Mapping):
                findings.append(_finding("block", "screen_text_bad_entry", path, f"{clip} has non-object screen_text entry"))
                continue
            text = str(entry.get("text") or "").strip()
            render_policy = str(entry.get("render_policy") or "").strip().lower()
            if text and not (("overlay" in render_policy) or ("compose" in render_policy)):
                findings.append(_finding(
                    "block",
                    "screen_text_not_overlay",
                    path,
                    f"{clip} screen text {text!r} must be compose/post overlay, not model-rendered frame text.",
                ))
    for idx, owners in sorted(seen.items()):
        if len(owners) > 1:
            findings.append(_finding(
                "block",
                "contract_duplicate_index",
                path,
                f"contract assigns voiceover index {idx} to multiple clips: {', '.join(owners)}",
            ))
    return findings


def _artifact_texts(root: Path, episode: str, contract: Optional[Mapping[str, Any]]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for path in [
        root / "脚本" / episode / "voiceover.txt",
        storyboard_path(root, episode),
        root / "出视频" / episode / "prompt" / "01_clips.md",
        root / "出视频" / episode / "prompt" / "00_总览.md",
    ]:
        text = read_text(path)
        if text:
            scan_text = "\n".join(
                line for line in text.splitlines()
                if not FORBIDDEN_VALUES_LINE_RE.search(line)
            )
            pairs.append((rel_to_root(root, path), scan_text))
    return pairs


def fact_drift_findings(root: Path, episode: str, contract: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    facts = collect_character_facts(root) + collect_episode_quantity_facts(root, episode)
    texts = _artifact_texts(root, episode, contract)
    for fact in facts:
        character = str(fact.get("character") or "")
        key = str(fact.get("key") or "")
        canonical = str(fact.get("canonical") or "")
        forbidden = [str(v) for v in fact.get("forbidden_values") or [] if str(v)]
        if not forbidden:
            continue
        if key == "age":
            bad_re = re.compile(r"(?:" + "|".join(re.escape(v).replace(r"\ ", r"\s*") for v in forbidden) + r")")
            for loc, text in texts:
                for m in bad_re.finditer(text):
                    context = text[max(0, m.start() - 48): min(len(text), m.end() + 48)]
                    if NEGATIVE_OR_FORBIDDEN_CONTEXT_RE.search(context):
                        continue
                    findings.append(_finding(
                        "block",
                        "age_fact_drift",
                        loc,
                        f"{character} canonical age is {canonical}; found forbidden age token {m.group(0)!r}. "
                        "Numeric age facts must be copied verbatim in native speech prompts.",
                    ))
        elif key == "height":
            # Only flag explicit height drift, not negative instructions like "不要画成年".
            bad_re = re.compile(r"(身高[^。；;\n]{0,30}(?:170|175|180)\s*cm|一米[七八])")
            for loc, text in texts:
                for m in bad_re.finditer(text):
                    context = text[max(0, m.start() - 80): min(len(text), m.end() + 80)]
                    if NEGATIVE_OR_FORBIDDEN_CONTEXT_RE.search(context):
                        continue
                    if character and character not in context:
                        continue
                    findings.append(_finding(
                        "block",
                        "height_fact_drift",
                        loc,
                        f"{character} canonical height/body scale is {canonical}; found explicit conflicting height token {m.group(0)!r}.",
                    ))
        elif key == "spiritual_root":
            bad_re = re.compile("|".join(re.escape(v) for v in forbidden))
            for loc, text in texts:
                for m in bad_re.finditer(text):
                    context = text[max(0, m.start() - 48): min(len(text), m.end() + 48)]
                    if NEGATIVE_OR_FORBIDDEN_CONTEXT_RE.search(context):
                        continue
                    findings.append(_finding(
                        "block",
                        "setting_fact_drift",
                        loc,
                        f"{character} canonical spiritual root is {canonical}; found conflicting token {m.group(0)!r}.",
                    ))
        elif key in {"daily_water_trips", "night_water_trip"}:
            bad_re = re.compile("|".join(re.escape(v) for v in forbidden))
            for loc, text in texts:
                for m in bad_re.finditer(text):
                    context = text[max(0, m.start() - 24): min(len(text), m.end() + 24)]
                    wide_context = text[max(0, m.start() - 48): min(len(text), m.end() + 48)]
                    if NEGATIVE_OR_FORBIDDEN_CONTEXT_RE.search(wide_context):
                        continue
                    if key == "daily_water_trips" and DAILY_TRIP_HISTORICAL_CONTEXT_RE.search(context):
                        continue
                    findings.append(_finding(
                        "block",
                        "quantity_fact_drift",
                        loc,
                        f"{character} canonical quantity fact is {canonical}; found conflicting token {m.group(0)!r}.",
                    ))
    return findings


def validate(root: Path, episode: str, *, require_contract: Optional[bool] = None) -> Dict[str, Any]:
    episode = normalize_episode(episode)
    findings: List[Dict[str, Any]] = []
    sb = storyboard_path(root, episode)
    if not sb.is_file():
        findings.append(_finding("block", "missing_storyboard", sb, "missing storyboard.json"))
    findings.extend(duplicate_storyboard_indices(root, episode))
    findings.extend(duplicate_storyboard_screen_text(root, episode))

    contract = load_contract(root, episode)
    required = native_speech_likely(root, episode) if require_contract is None else bool(require_contract)
    if required and contract is None:
        findings.append(_finding(
            "block",
            "missing_dialogue_fact_contract",
            contract_path(root, episode),
            "native_speech/native_av is active but dialogue_fact_contract is missing; run this script with --write before paid video submit.",
        ))
    if contract is not None:
        findings.extend(validate_contract_payload(root, episode, contract))
    findings.extend(fact_drift_findings(root, episode, contract))
    summary = {
        "block": sum(1 for f in findings if f.get("severity") == "block"),
        "warn": sum(1 for f in findings if f.get("severity") == "warn"),
        "info": sum(1 for f in findings if f.get("severity") == "info"),
    }
    return {
        "kind": "n2d_dialogue_fact_guard_report",
        "episode": episode,
        "required": required,
        "contract_path": rel_to_root(root, contract_path(root, episode)),
        "summary": summary,
        "findings": findings,
    }


def contract_prompt_suffix(root: Path, episode: str, clip: str) -> str:
    episode = normalize_episode(episode)
    contract = load_contract(root, episode)
    if not contract:
        return ""
    wanted = normalize_clip(clip)
    rows = _contract_clip_rows(contract)
    row = next((r for r in rows if normalize_clip(r.get("clip")) == wanted), None)
    if row is None:
        return ""
    character_lines = []
    for entry in row.get("allowed_character_dialogue") or []:
        if not isinstance(entry, Mapping):
            continue
        idx = entry.get("index")
        role = entry.get("role") or "角色"
        text = entry.get("text") or ""
        character_lines.append(f"{idx}. {role}: {text}")
    narration_lines = []
    for entry in row.get("allowed_narration") or []:
        if not isinstance(entry, Mapping):
            continue
        idx = entry.get("index")
        text = entry.get("text") or ""
        narration_lines.append(f"{idx}. 旁白: {text}")
    screen_text_lines = []
    for entry in row.get("screen_text_lines") or []:
        if not isinstance(entry, Mapping):
            continue
        text = entry.get("text") or ""
        render_policy = entry.get("render_policy") or "compose_overlay_only"
        purpose = entry.get("purpose") or ""
        screen_text_lines.append(f"{text}（{render_policy}; {purpose}）")
    facts = []
    for fact in contract.get("facts") or []:
        if not isinstance(fact, Mapping):
            continue
        character = fact.get("character") or ""
        key = fact.get("key") or ""
        canonical = fact.get("canonical") or ""
        if (
            character
            and canonical
            and key in {"age", "height", "spiritual_root", "daily_water_trips", "night_water_trip"}
            and (str(character) == "贺平生" or str(character) == "剧情账本")
        ):
            facts.append(f"{character}.{key}={canonical}")
    forbidden_values: List[str] = []
    for fact in contract.get("facts") or []:
        if isinstance(fact, Mapping):
            forbidden_values.extend(str(v) for v in fact.get("forbidden_values") or [] if str(v))
    return "\n".join([
        "对白事实锁 / Dialogue-Fact Contract:",
        f"- clip: {wanted}; allowed_voiceover_indices={row.get('allowed_voiceover_indices')}",
        f"- allowed_narration_indices={row.get('allowed_narration_indices')}; allowed_character_dialogue_indices={row.get('allowed_character_dialogue_indices')}",
        "- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。",
        "- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。",
        *[f"- dialogue: {line}" for line in character_lines],
        *[f"- narration_for_compose_only: {line}" for line in narration_lines],
        "- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.",
        "- screen_text_overlay: " + (" | ".join(screen_text_lines) if screen_text_lines else "none; 不要让视频模型生成文字"),
        "- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。",
        "- canonical_facts: " + ("; ".join(facts) if facts else "see character cards"),
        "- forbidden_fact_values: " + (", ".join(sorted(set(forbidden_values))) if forbidden_values else "none"),
        "- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。",
    ]).strip()


def render_markdown(report: Mapping[str, Any], contract: Optional[Mapping[str, Any]]) -> str:
    lines = [
        f"# {report.get('episode')} 对白事实锁检查",
        "",
        f"- contract: `{report.get('contract_path')}`",
        f"- required: {report.get('required')}",
        f"- summary: block={report.get('summary', {}).get('block', 0)} / warn={report.get('summary', {}).get('warn', 0)}",
        "",
        "## Findings",
    ]
    findings = report.get("findings") or []
    if not findings:
        lines.append("- ✅ no findings")
    else:
        for f in findings:
            lines.append(f"- {f.get('severity')} · {f.get('code')} · `{f.get('loc')}` · {f.get('message')}")
    if contract:
        lines.extend(["", "## Clip Three-Track Allocation"])
        for row in _contract_clip_rows(contract):
            label = row.get("label") or row.get("storyboard_clip_id") or row.get("clip")
            screen_text = [
                entry.get("text")
                for entry in row.get("screen_text_lines") or []
                if isinstance(entry, Mapping) and entry.get("text")
            ]
            lines.append(
                f"- `{row.get('clip')}` {label}: voice={row.get('allowed_voiceover_indices')} "
                f"narration={row.get('allowed_narration_indices')} "
                f"dialogue={row.get('allowed_character_dialogue_indices')} "
                f"screen_text={screen_text}"
            )
    lines.append("")
    return "\n".join(lines)


def write_report(root: Path, episode: str, report: Mapping[str, Any], contract: Optional[Mapping[str, Any]]) -> Path:
    path = report_path(root, episode)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(report, contract), encoding="utf-8")
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true", help="write/update dialogue_fact_contract and markdown report")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-require-contract", action="store_true", help="validate facts/duplicates without requiring sidecar")
    ns = ap.parse_args(argv)

    root = Path(ns.root).resolve()
    episode = normalize_episode(ns.episode)
    contract: Optional[Dict[str, Any]] = None
    if ns.write:
        contract = build_contract(root, episode)
        atomic_write_json(contract_path(root, episode), contract)
    else:
        contract = load_contract(root, episode)
    report = validate(root, episode, require_contract=False if ns.no_require_contract else None)
    if contract is None:
        contract = load_contract(root, episode)
    md = write_report(root, episode, report, contract)
    payload = dict(report)
    payload["report_path"] = rel_to_root(root, md)
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        s = report.get("summary", {})
        print(f"dialogue_fact_guard {episode}: block={s.get('block', 0)} warn={s.get('warn', 0)} report={rel_to_root(root, md)}")
        for f in report.get("findings") or []:
            print(f"- {f.get('severity')} {f.get('code')}: {f.get('message')}")
    return 1 if report.get("summary", {}).get("block", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
