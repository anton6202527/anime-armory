#!/usr/bin/env python3
"""Voice casting and no-audio timing contracts for the n2d pipeline.

This module deliberately separates three things that used to be conflated:

* casting: which approved voice/performance identity belongs to each role;
* timing: a text-derived editorial estimate that creates **no WAV files**;
* rendering: final or explicitly approved guide audio, handled by n2d-voice.

The timing estimate is suitable for an animatic, narration/off-screen pacing and
picture-first shots.  It is not evidence that a visible-mouth performance is
finished and must never masquerade as a final voice manifest.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


CASTING_KIND = "n2d_voice_casting"
TIMING_KIND = "n2d_timing_estimate"
VERSION = 1

VOICE_LINE_RE = re.compile(r"^\[(?P<shot>[^·\]]+)·(?P<role>[^·\]]+)·(?P<cue>[^\]]*)\]\s*(?P<text>.+)$")
NARRATION_ROLE_TOKENS = ("旁白", "画外", "内心", "心声", "系统音", "narrator", "voiceover", "v.o.")
CLONE_BACKEND_TOKENS = ("clone", "cosy", "fish", "gpt-sovits", "gptsovits", "index", "voxcpm", "zero-shot", "零样本", "克隆")
LOCKED_STATUSES = {"locked", "已锁定", "approved", "定妆通过"}
GUIDE_APPROVED_STATUSES = LOCKED_STATUSES | {"guide_approved", "导引通过"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def normalize_episode(value: str) -> str:
    raw = str(value or "").strip()
    if raw.startswith("第") and raw.endswith("集"):
        return raw
    match = re.search(r"\d+", raw)
    return f"第{int(match.group(0))}集" if match else raw


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _visible_text(text: str) -> str:
    out = re.sub(r"[⚡💥🪝🎬🔑]", "", str(text or ""))
    out = out.replace("||", "，")
    return re.sub(r"\s+", " ", out).strip()


def is_narration_role(role: str) -> bool:
    low = str(role or "").strip().lower()
    return any(token.lower() in low for token in NARRATION_ROLE_TOKENS)


def parse_voiceover_text(text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = VOICE_LINE_RE.match(line)
        if not match:
            continue
        cue = match.group("cue").strip()
        spoken = _visible_text(match.group("text"))
        if not spoken:
            continue
        role = match.group("role").strip()
        rows.append({
            "index": len(rows) + 1,
            "镜头": match.group("shot").strip(),
            "角色": role,
            "表演提示": cue,
            "文本": spoken,
            "line_type": "narration_or_offscreen" if is_narration_role(role) else "character_dialogue",
            "source_line": line,
        })
    return rows


def load_voiceover(root: Path, episode: str) -> Tuple[Path, List[Dict[str, Any]], str]:
    ep = normalize_episode(episode)
    path = root / "脚本" / ep / "voiceover.txt"
    text = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""
    rows = parse_voiceover_text(text)
    normalized = "\n".join(row["source_line"] for row in rows)
    fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else ""
    return path, rows, fingerprint


def _hook_gap(source_line: str, *, is_last: bool) -> float:
    if is_last:
        return 0.0
    raw = str(source_line or "")
    if "🪝" in raw or "集尾" in raw:
        return 1.0
    if "💥" in raw or "爽点" in raw:
        return 0.7
    if "⚡" in raw or "钩子" in raw:
        return 0.6
    return 0.4


def estimate_line_duration(text: str, cue: str = "", line_type: str = "character_dialogue") -> Dict[str, Any]:
    """Estimate editorial timing without synthesizing audio.

    The range is intentionally explicit: downstream may use the center for an
    animatic, but visible-mouth final performance must use an approved track.
    """
    spoken = str(text or "")
    cjk = len(re.findall(r"[\u3400-\u9fff]", spoken))
    words = len(re.findall(r"[A-Za-z0-9]+", spoken))
    punct = len(re.findall(r"[，。！？、；：,.!?;:]", spoken))
    ellipsis = spoken.count("……") + spoken.count("...")
    base = cjk / 5.2 + words / 2.6 + punct * 0.10 + ellipsis * 0.22
    cue_text = str(cue or "")
    if any(token in cue_text for token in ("慢", "迟疑", "哽咽", "喘", "停顿")):
        base *= 1.12
    elif "快" in cue_text:
        base *= 0.92
    if line_type == "narration_or_offscreen":
        base *= 1.03
    center = max(0.8, min(15.0, base or 0.8))
    low = max(0.6, center * 0.82)
    high = max(low + 0.15, center * 1.22)
    return {
        "estimated_duration_sec": round(center, 3),
        "range_sec": [round(low, 3), round(high, 3)],
        "confidence": "medium" if cjk + words >= 4 else "low",
        "method": "text_rate_v1",
    }


def build_timing_estimate(root: Path, episode: str) -> Dict[str, Any]:
    root = root.resolve()
    ep = normalize_episode(episode)
    source, rows, fingerprint = load_voiceover(root, ep)
    cursor = 0.0
    output_rows: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows):
        estimate = estimate_line_duration(row["文本"], row["表演提示"], row["line_type"])
        duration = float(estimate["estimated_duration_sec"])
        gap = _hook_gap(row.get("source_line", ""), is_last=idx == len(rows) - 1)
        start = cursor
        end = start + duration
        output_rows.append({
            "idx": idx,
            "line_index": idx + 1,
            "镜头": row["镜头"],
            "角色": row["角色"],
            "文本": row["文本"],
            "表演提示": row["表演提示"],
            "line_type": row["line_type"],
            "时长": round(duration, 3),
            "estimated_duration_sec": round(duration, 3),
            "duration_range_sec": estimate["range_sec"],
            "confidence": estimate["confidence"],
            "start": round(start, 3),
            "end": round(end, 3),
            "gap_after": round(gap, 3),
            "timing_basis": "text_estimate_no_audio",
            "audio_path": "",
        })
        cursor = end + gap
    return {
        "kind": TIMING_KIND,
        "version": VERSION,
        "episode": ep,
        "generated_at": now_iso(),
        "status": "provisional" if rows else "missing_voiceover",
        "source_path": str(source.relative_to(root)) if source.is_file() else f"脚本/{ep}/voiceover.txt",
        "source_fingerprint": fingerprint,
        "audio_generated": False,
        "timing_basis": "text_estimate_no_audio",
        "lines": output_rows,
        "summary": {
            "line_count": len(output_rows),
            "dialogue_lines": sum(1 for row in output_rows if row["line_type"] == "character_dialogue"),
            "narration_or_offscreen_lines": sum(1 for row in output_rows if row["line_type"] == "narration_or_offscreen"),
            "duration_sec": round(cursor, 3),
        },
        "suitable_for": ["animatic", "rough_editorial_timing", "narration_offscreen_pacing", "picture_first_shots"],
        "not_suitable_for": ["final_mix", "visible_mouth_final_performance", "final_lipsync", "voice_identity_approval"],
        "policy": "time_basis_first_without_disposable_wav",
    }


def casting_path(root: Path) -> Path:
    return root / "设定库" / "voice_casting.json"


def timing_path(root: Path, episode: str) -> Path:
    return root / "合成" / normalize_episode(episode) / "配音" / "timing_estimate.json"


def _roles_from_payload(payload: Any) -> Dict[str, Dict[str, Any]]:
    rows = payload.get("roles") if isinstance(payload, Mapping) else []
    if isinstance(rows, Mapping):
        return {str(role): dict(value) for role, value in rows.items() if isinstance(value, Mapping)}
    return {
        str(row.get("role") or ""): dict(row)
        for row in rows or [] if isinstance(row, Mapping) and str(row.get("role") or "").strip()
    }


def _role_lock_hash(row: Mapping[str, Any]) -> str:
    keys = ("role", "status", "backend", "model", "voice_id", "canonical_sample", "approved_by", "approved_at", "authorization")
    stable = {key: row.get(key) for key in keys}
    return hashlib.sha256(json.dumps(stable, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _entry_locked(row: Mapping[str, Any], *, allow_guide: bool = False) -> bool:
    allowed = GUIDE_APPROVED_STATUSES if allow_guide else LOCKED_STATUSES
    return str(row.get("status") or "").strip().lower() in {item.lower() for item in allowed}


def build_casting(root: Path, episodes: Sequence[str]) -> Dict[str, Any]:
    root = root.resolve()
    old = _load_json(casting_path(root))
    existing = _roles_from_payload(old)
    by_role: Dict[str, List[Dict[str, Any]]] = {}
    normalized_eps: List[str] = []
    for episode in episodes:
        ep = normalize_episode(episode)
        if ep not in normalized_eps:
            normalized_eps.append(ep)
        _path, lines, _fingerprint = load_voiceover(root, ep)
        for row in lines:
            by_role.setdefault(str(row["角色"]), []).append({**row, "episode": ep})

    # `voice_casting.json` is a project-level registry, not an episode snapshot.
    # Keep previously cast roles even when they do not speak in the episode that
    # is currently being prepared; otherwise preparing episode 2 could silently
    # delete a locked episode-1 voice identity.
    for role in existing:
        by_role.setdefault(role, [])

    roles: List[Dict[str, Any]] = []
    for role in sorted(by_role):
        source_lines = by_role[role]
        entry = dict(existing.get(role) or {})
        entry.setdefault("role", role)
        entry.setdefault("status", "unselected")
        entry.setdefault("required", True)
        entry.setdefault("backend", "")
        entry.setdefault("model", "")
        entry.setdefault("voice_id", "")
        entry.setdefault("canonical_sample", "")
        entry.setdefault("reference_audio", "")
        entry.setdefault("authorization", "not_applicable_synthetic_or_pending")
        entry.setdefault("approved_by", "")
        entry.setdefault("approved_at", "")
        entry.setdefault("voice_spec", {
            "age_impression": "",
            "texture": "",
            "pace": "",
            "accent": "",
            "performance_boundary": "",
        })
        previous_episodes = {
            str(value) for value in (entry.get("episodes") or []) if str(value).strip()
        }
        current_episodes = {str(row["episode"]) for row in source_lines}
        entry["line_count"] = (
            len(source_lines)
            if source_lines
            else int(entry.get("line_count") or 0)
        )
        entry["episodes"] = sorted(previous_episodes | current_episodes)
        # Audition coverage: first line plus up to two distinct performance cues.
        audition: List[Dict[str, Any]] = []
        seen_cues = set()
        for row in source_lines:
            cue = str(row.get("表演提示") or "").strip()
            if audition and cue in seen_cues:
                continue
            audition.append({
                "episode": row["episode"],
                "line_index": row["index"],
                "cue": cue,
                "text": row["文本"],
            })
            seen_cues.add(cue)
            if len(audition) >= 3:
                break
        if audition:
            entry["audition_lines"] = audition
        else:
            entry.setdefault("audition_lines", [])
        entry["lock_hash"] = _role_lock_hash(entry) if _entry_locked(entry, allow_guide=True) else ""
        roles.append(entry)

    required = [row for row in roles if row.get("required") is not False]
    locked = [row for row in required if _entry_locked(row)]
    return {
        "kind": CASTING_KIND,
        "version": VERSION,
        "generated_at": now_iso(),
        "status": "locked" if required and len(locked) == len(required) else "casting",
        "policy": "casting_first_final_render_later",
        "episodes_scanned": normalized_eps,
        "roles": roles,
        "summary": {
            "role_count": len(roles),
            "required_count": len(required),
            "locked_count": len(locked),
            "pending_count": max(0, len(required) - len(locked)),
        },
        "rules": [
            "No final episode render before every required role is locked.",
            "A text timing estimate is not a voice asset and creates no WAV files.",
            "Guide audio must be explicitly guide_approved or locked; never treat an arbitrary filler voice as performance truth.",
        ],
    }


def role_entry(casting: Mapping[str, Any], role: str) -> Dict[str, Any]:
    exact = _roles_from_payload(casting).get(str(role or ""))
    if exact:
        return exact
    needle = str(role or "").strip()
    for key, value in _roles_from_payload(casting).items():
        if key and (key in needle or needle in key):
            return value
    return {}


def _clone_authorized(entry: Mapping[str, Any]) -> bool:
    backend = str(entry.get("backend") or "").lower()
    if not any(token in backend for token in CLONE_BACKEND_TOKENS):
        return True
    return str(entry.get("authorization") or "").strip().lower() in {
        "authorized", "已授权", "self", "本人", "synthetic", "纯合成",
    }


def casting_blockers(casting: Mapping[str, Any], roles: Iterable[str], *, purpose: str = "final") -> List[str]:
    allow_guide = str(purpose or "final").lower() in {"guide", "performance_guide", "导引"}
    blockers: List[str] = []
    for role in sorted({str(item).strip() for item in roles if str(item).strip()}):
        entry = role_entry(casting, role)
        if not entry:
            blockers.append(f"角色「{role}」不在 voice_casting.json")
            continue
        if not _entry_locked(entry, allow_guide=allow_guide):
            target = "guide_approved/locked" if allow_guide else "locked"
            blockers.append(f"角色「{role}」status={entry.get('status') or 'missing'}，需要 {target}")
        if not str(entry.get("backend") or "").strip():
            blockers.append(f"角色「{role}」缺 backend")
        if not str(entry.get("voice_id") or "").strip():
            blockers.append(f"角色「{role}」缺 voice_id/performer_id")
        if not str(entry.get("approved_by") or "").strip():
            blockers.append(f"角色「{role}」缺 approved_by")
        sample = str(entry.get("canonical_sample") or entry.get("audition_sample") or "").strip()
        if not sample:
            blockers.append(f"角色「{role}」缺 canonical_sample/audition_sample")
        if not _clone_authorized(entry):
            blockers.append(f"角色「{role}」使用克隆/零样本后端但 authorization 未授权")
    return blockers


def casting_backend(entry: Mapping[str, Any]) -> str:
    raw = str(entry.get("backend") or "").strip().lower().replace("_", "-")
    aliases = {
        "火山": "volcengine", "volc": "volcengine", "volcengine": "volcengine",
        "minimax": "minimax", "mini-max": "minimax",
        "cosyvoice": "cosyvoice", "fishspeech": "fishspeech", "fish-speech": "fishspeech",
        "gptsovits": "gpt-sovits", "gpt-sovits": "gpt-sovits",
        "indextts": "indextts2", "indextts-2": "indextts2", "indextts2": "indextts2",
        "voxcpm": "voxcpm2", "voxcpm2": "voxcpm2",
        "human": "human-recording", "human-recording": "human-recording",
        "manual": "human-recording", "say": "say",
    }
    return aliases.get(raw, raw)


def write_preproduction(root: Path, episode: str, *, episodes_for_casting: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    root = root.resolve()
    ep = normalize_episode(episode)
    eps = list(episodes_for_casting or [ep])
    casting = build_casting(root, eps)
    timing = build_timing_estimate(root, ep)
    _atomic_json(casting_path(root), casting)
    _atomic_json(timing_path(root, ep), timing)
    return {
        "casting": casting,
        "timing": timing,
        "outputs": {
            "casting": str(casting_path(root).relative_to(root)),
            "timing": str(timing_path(root, ep).relative_to(root)),
        },
    }


def lock_role(
    root: Path,
    role: str,
    *,
    backend: str,
    voice_id: str,
    approved_by: str,
    canonical_sample: str,
    model: str = "",
    authorization: str = "not_applicable_synthetic",
    status: str = "locked",
) -> Dict[str, Any]:
    path = casting_path(root)
    payload = _load_json(path)
    if not isinstance(payload, Mapping):
        raise ValueError("voice_casting.json 不存在；先运行 voice_preflight.py prepare")
    data = dict(payload)
    roles = [dict(row) for row in data.get("roles") or [] if isinstance(row, Mapping)]
    target = next((row for row in roles if str(row.get("role") or "") == role), None)
    if target is None:
        raise ValueError(f"角色「{role}」不在 voice_casting.json；先 prepare 刷新角色表")
    target.update({
        "status": status,
        "backend": backend,
        "model": model,
        "voice_id": voice_id,
        "canonical_sample": canonical_sample,
        "authorization": authorization,
        "approved_by": approved_by,
        "approved_at": now_iso(),
    })
    target["lock_hash"] = _role_lock_hash(target)
    required = [row for row in roles if row.get("required") is not False]
    locked = [row for row in required if _entry_locked(row)]
    data["roles"] = roles
    data["generated_at"] = now_iso()
    data["status"] = "locked" if required and len(locked) == len(required) else "casting"
    data["summary"] = {
        "role_count": len(roles), "required_count": len(required),
        "locked_count": len(locked), "pending_count": max(0, len(required) - len(locked)),
    }
    _atomic_json(path, data)
    return data
