#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Measured voice evidence for n2d.

Energy is only one signal. A line is never marked green merely because ffmpeg
was invoked: every measurement records return codes, exact WAV hashes and
explicit unmeasured dimensions. Optional ASR/speaker/prosody adapters are
configured with ``N2D_VOICE_{ASR,SPEAKER,PROSODY}_CMD``; each command receives
``{audio}``, ``{text}`` and ``{role}`` placeholders and prints one JSON object.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


EVIDENCE_KIND = "n2d_voice_quality_evidence"
LISTENING_KIND = "n2d_voice_listening_receipt"
LISTENING_VERSION = 1
PLAN_KIND = "n2d_voice_key_line_best_of_n_plan"
PLAN_VERSION = 1
LISTENING_REVIEWER_KINDS = {"human", "executor_audio"}


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _timezone_iso(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = dt.datetime.fromisoformat(value.strip())
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _manifest_contract_sha(manifest: Sequence[Mapping[str, Any]]) -> str:
    payload = json.dumps(list(manifest), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _manifest_binding(
    manifest: Sequence[Mapping[str, Any]], manifest_path: str | Path | None = None,
) -> Dict[str, Any]:
    binding: Dict[str, Any] = {"contract_sha256": _manifest_contract_sha(manifest)}
    if manifest_path is not None:
        path = Path(manifest_path).resolve()
        if not path.is_file():
            raise ValueError(f"manifest 文件不存在：{path}")
        try:
            on_disk = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"manifest 文件无法解析：{path}") from exc
        if on_disk != list(manifest):
            raise ValueError("传入 manifest 与磁盘当前 manifest 不一致")
        binding.update({"path": str(path), "sha256": _sha256(path)})
    return binding


def _line_index(entry: Mapping[str, Any], position: int) -> int:
    try:
        return int(_entry_value(entry, "index", "idx", default=position))
    except Exception as exc:
        raise ValueError(f"manifest line {position} 的 index/idx 无效") from exc


def _nonempty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(x, str) and x.strip() for x in value)


def _entry_value(entry: Mapping[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        if entry.get(key) not in (None, ""):
            return entry[key]
    return default


def resolve_line_wav(wav_dir: str | Path, entry: Mapping[str, Any]) -> Path | None:
    raw = str(_entry_value(entry, "line_wav", "wav", default="")).strip()
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_absolute() else Path(wav_dir) / path


def extract_energy(wav_path: str | Path) -> Dict[str, Any]:
    """Return measured volume or an explicit error; never synthesize 0 dB."""
    path = Path(wav_path)
    if not path.is_file():
        return {"status": "error", "error": "audio_missing", "mean_db": None, "max_db": None, "energy_score": None}
    try:
        result = subprocess.run(
            ["ffmpeg", "-nostdin", "-i", str(path), "-filter:a", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, check=False,
        )
    except Exception as exc:
        return {"status": "error", "error": f"ffmpeg_unavailable:{exc}", "mean_db": None, "max_db": None, "energy_score": None}
    output = result.stderr or ""
    mean = re.search(r"mean_volume:\s*([-+]?\d+(?:\.\d+)?) dB", output)
    maximum = re.search(r"max_volume:\s*([-+]?\d+(?:\.\d+)?) dB", output)
    if result.returncode != 0 or not mean or not maximum:
        return {
            "status": "error",
            "error": "ffmpeg_failed" if result.returncode else "volumedetect_unparsed",
            "returncode": result.returncode,
            "mean_db": None, "max_db": None, "energy_score": None,
        }
    mean_db = float(mean.group(1))
    max_db = float(maximum.group(1))
    return {
        "status": "measured", "returncode": result.returncode,
        "mean_db": mean_db, "max_db": max_db,
        "energy_score": round(max(0.0, min(1.0, (100.0 + mean_db) / 100.0)), 4),
    }


def probe_duration(wav_path: str | Path) -> Dict[str, Any]:
    path = Path(wav_path)
    if not path.is_file():
        return {"status": "error", "duration_sec": None, "error": "audio_missing"}
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, check=False,
        )
        duration = float((result.stdout or "").strip()) if result.returncode == 0 else 0.0
    except Exception as exc:
        return {"status": "error", "duration_sec": None, "error": f"ffprobe_unavailable:{exc}"}
    if duration <= 0:
        return {"status": "error", "duration_sec": None, "returncode": result.returncode, "error": "duration_unavailable"}
    return {"status": "measured", "duration_sec": round(duration, 4), "returncode": result.returncode}


def _normalized_chars(text: str) -> List[str]:
    return list(re.sub(r"[^0-9A-Za-z\u3400-\u9fff]+", "", str(text or "")).lower())


def character_error_rate(reference: str, hypothesis: str) -> float:
    ref = _normalized_chars(reference)
    hyp = _normalized_chars(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    previous = list(range(len(hyp) + 1))
    for i, left in enumerate(ref, start=1):
        current = [i]
        for j, right in enumerate(hyp, start=1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
        previous = current
    return round(previous[-1] / len(ref), 4)


def _run_plugin(env_key: str, *, audio: Path, text: str, role: str) -> Dict[str, Any]:
    template = str(os.environ.get(env_key) or "").strip()
    if not template:
        return {"status": "unmeasured", "adapter": env_key, "reason": "adapter_not_configured"}
    try:
        argv = [token.format(audio=str(audio), text=text, role=role) for token in shlex.split(template)]
        result = subprocess.run(argv, capture_output=True, text=True, check=False)
    except Exception as exc:
        return {"status": "error", "adapter": env_key, "error": str(exc)}
    if result.returncode != 0:
        return {"status": "error", "adapter": env_key, "returncode": result.returncode, "error": (result.stderr or "")[-500:]}
    try:
        payload = json.loads(result.stdout)
    except Exception:
        return {"status": "error", "adapter": env_key, "returncode": result.returncode, "error": "plugin_stdout_not_json"}
    if not isinstance(payload, Mapping):
        return {"status": "error", "adapter": env_key, "returncode": result.returncode, "error": "plugin_json_not_object"}
    return {"status": "measured", "adapter": env_key, "returncode": result.returncode, "result": dict(payload)}


def analyze_emotion_flow(
    wav_dir: str | Path,
    manifest: Sequence[Mapping[str, Any]],
    output_path: str | Path,
    evidence_output_path: str | Path | None = None,
) -> List[Dict[str, Any]]:
    """Analyze every manifest row and emit compatibility flow + evidence contract."""
    flow: List[Dict[str, Any]] = []
    evidence_lines: List[Dict[str, Any]] = []
    for position, entry in enumerate(manifest):
        idx = _entry_value(entry, "index", "idx", default=position)
        role = str(_entry_value(entry, "role", "角色", default=""))
        text = str(_entry_value(entry, "text", "文本", default=""))
        expected_duration = float(_entry_value(entry, "duration", "时长", default=0) or 0)
        wav_path = resolve_line_wav(wav_dir, entry)
        energy = extract_energy(wav_path) if wav_path else {
            "status": "error", "error": "line_wav_missing", "mean_db": None, "max_db": None, "energy_score": None
        }
        duration = probe_duration(wav_path) if wav_path else {"status": "error", "duration_sec": None, "error": "line_wav_missing"}
        timing_status = "unmeasured"
        delta = None
        if duration.get("status") == "measured" and expected_duration > 0:
            delta = round(float(duration["duration_sec"]) - expected_duration, 4)
            timing_status = "pass" if abs(delta) <= max(0.25, expected_duration * 0.15) else "fail"
        elif duration.get("status") == "measured":
            timing_status = "measured_no_manifest_target"
        if wav_path and wav_path.is_file():
            asr = _run_plugin("N2D_VOICE_ASR_CMD", audio=wav_path, text=text, role=role)
            speaker = _run_plugin("N2D_VOICE_SPEAKER_CMD", audio=wav_path, text=text, role=role)
            prosody = _run_plugin("N2D_VOICE_PROSODY_CMD", audio=wav_path, text=text, role=role)
        else:
            asr = speaker = prosody = {"status": "error", "error": "audio_missing"}
        if asr.get("status") == "measured":
            transcript = str((asr.get("result") or {}).get("transcript") or "")
            asr["reference_text"] = text
            asr["transcript"] = transcript
            asr["cer"] = character_error_rate(text, transcript)
            asr["threshold"] = float(os.environ.get("N2D_VOICE_CER_MAX") or 0.12)
            asr["verdict"] = "pass" if asr["cer"] <= asr["threshold"] else "fail"
        statuses = [energy.get("status"), duration.get("status"), timing_status]
        plugin_failed = any(
            item.get("status") == "error"
            or str((item.get("result") or {}).get("verdict") or (item.get("result") or {}).get("status") or "").lower()
            in {"fail", "block", "rejected", "error"}
            for item in (asr, speaker, prosody)
        )
        if any(value in {"error", "fail"} for value in statuses) or asr.get("verdict") == "fail" or plugin_failed:
            line_status = "block"
        elif any(item.get("status") == "unmeasured" for item in (asr, speaker, prosody)):
            line_status = "unmeasured"
        else:
            line_status = "pass"
        flow.append({
            "index": idx, "shot": _entry_value(entry, "shot", "镜头"), "role": role,
            "line_wav": str(wav_path) if wav_path else "", "analysis_status": line_status,
            "energy": energy, "emotion_applied": _entry_value(entry, "emotion_applied", "情绪_已应用"),
            "duration": expected_duration,
        })
        evidence_lines.append({
            "index": idx, "role": role, "text": text,
            "line_wav": str(wav_path) if wav_path else "",
            "line_wav_sha256": _sha256(wav_path) if wav_path and wav_path.is_file() else None,
            "status": line_status, "energy": energy,
            "timing": {"status": timing_status, "manifest_duration_sec": expected_duration, "probe": duration, "delta_sec": delta},
            "asr_cer": asr, "speaker": speaker, "prosody": prosody,
        })

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(flow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    overall = "block" if not evidence_lines or any(x["status"] == "block" for x in evidence_lines) else (
        "unmeasured" if any(x["status"] == "unmeasured" for x in evidence_lines) else "pass"
    )
    evidence = {
        "kind": EVIDENCE_KIND, "version": 1, "generated_at": _now_iso(), "status": overall,
        "summary": {
            "manifest_lines": len(manifest), "analyzed_lines": len(evidence_lines),
            "pass": sum(1 for x in evidence_lines if x["status"] == "pass"),
            "unmeasured": sum(1 for x in evidence_lines if x["status"] == "unmeasured"),
            "block": sum(1 for x in evidence_lines if x["status"] == "block"),
        },
        "dimensions": ["energy", "timing", "asr_cer", "speaker", "prosody"],
        "lines": evidence_lines, "final_user_acceptance": False,
    }
    evidence_path = Path(evidence_output_path) if evidence_output_path else output.with_name("voice_quality_evidence.json")
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return flow


def key_line(entry: Mapping[str, Any]) -> bool:
    hook = str(_entry_value(entry, "hook", "钩子", default="")).strip()
    emotion = str(_entry_value(entry, "emotion", "情绪", default="neutral")).strip().lower()
    text = str(_entry_value(entry, "text", "文本", default=""))
    return bool(hook and hook not in {"0", "false", "none"}) or emotion not in {"", "neutral", "中性"} or bool(re.search(r"[！？!?…]", text))


def _manifest_rows(manifest: Sequence[Mapping[str, Any]]) -> Dict[int, Mapping[str, Any]]:
    if not isinstance(manifest, (list, tuple)):
        raise ValueError("manifest 必须是逐句数组")
    rows: Dict[int, Mapping[str, Any]] = {}
    for position, entry in enumerate(manifest):
        if not isinstance(entry, Mapping):
            raise ValueError(f"manifest line {position} 不是对象")
        idx = _line_index(entry, position)
        if idx in rows:
            raise ValueError(f"manifest 有重复 line index：{idx}")
        rows[idx] = entry
    return rows


def _required_key_line_indices(manifest: Sequence[Mapping[str, Any]]) -> set[int]:
    return {
        idx for idx, entry in _manifest_rows(manifest).items()
        if key_line(entry)
    }


def build_key_line_best_of_n_plan(
    manifest: Sequence[Mapping[str, Any]],
    n: int = 3,
    *,
    manifest_path: str | Path | None = None,
) -> Dict[str, Any]:
    if n < 2:
        raise ValueError("关键句 best-of-N 的 N 必须至少为 2")
    lines: List[Dict[str, Any]] = []
    for position, entry in enumerate(manifest):
        if not key_line(entry):
            continue
        idx = _line_index(entry, position)
        lines.append({
            "index": idx, "role": _entry_value(entry, "role", "角色"),
            "text": _entry_value(entry, "text", "文本"), "candidate_count": n,
            "candidate_files": [f"candidates/line_{idx:02d}_take_{take:02d}.wav" for take in range(1, n + 1)],
            "selection_requires_actual_listening": True,
        })
    return {
        "kind": PLAN_KIND, "version": PLAN_VERSION, "generated_at": _now_iso(),
        "status": "ready" if lines else "not_applicable", "n": n, "key_lines": lines,
        "manifest": _manifest_binding(manifest, manifest_path),
    }


def _validate_plan(
    manifest: Sequence[Mapping[str, Any]],
    *,
    manifest_path: str | Path | None,
    plan_path: str | Path | None,
) -> tuple[set[int], List[str]]:
    """Recompute key lines and reject stale/self-authored plan state."""
    required = _required_key_line_indices(manifest)
    issues: List[str] = []
    path = Path(plan_path) if plan_path is not None else None
    if path is None or not path.is_file():
        if required:
            issues.append("缺当前 key_line_best_of_n_plan.json")
        return required, issues
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return required, ["key-line plan 无法解析"]
    if not isinstance(plan, Mapping):
        return required, ["key-line plan 必须是对象"]
    if plan.get("kind") != PLAN_KIND or type(plan.get("version")) is not int or plan.get("version") != PLAN_VERSION:
        issues.append("key-line plan kind/version 无效")
    if not _timezone_iso(plan.get("generated_at")):
        issues.append("key-line plan generated_at 缺有效时区")
    current_binding = _manifest_binding(manifest, manifest_path)
    recorded_binding = plan.get("manifest") if isinstance(plan.get("manifest"), Mapping) else {}
    for field in ("contract_sha256", "path", "sha256"):
        if field in current_binding and recorded_binding.get(field) != current_binding[field]:
            issues.append(f"key-line plan manifest.{field} 已过期")
    plan_lines = plan.get("key_lines")
    if not isinstance(plan_lines, list):
        issues.append("key-line plan.key_lines 必须是数组")
        plan_lines = []
    planned: set[int] = set()
    for row in plan_lines:
        if not isinstance(row, Mapping):
            issues.append("key-line plan 每行必须是对象")
            continue
        try:
            if type(row.get("index")) is not int or type(row.get("candidate_count")) is not int:
                raise ValueError
            idx = row["index"]
            candidate_count = row["candidate_count"]
        except Exception:
            issues.append("key-line plan index/candidate_count 无效")
            continue
        if idx in planned:
            issues.append(f"key-line plan 重复 index：{idx}")
        planned.add(idx)
        if candidate_count < 2 or row.get("selection_requires_actual_listening") is not True:
            issues.append(f"key-line plan line {idx} 未声明有效 best-of-N/实际听辨")
    if planned != required:
        issues.append(
            "key-line plan 与当前 manifest 推导不一致："
            f"planned={sorted(planned)} required={sorted(required)}"
        )
    expected_status = "ready" if required else "not_applicable"
    if plan.get("status") != expected_status:
        issues.append(f"key-line plan status 应为 {expected_status}")
    return required, issues


def record_listening_receipt(
    wav_dir: str | Path,
    manifest: Sequence[Mapping[str, Any]],
    output_path: str | Path,
    *,
    reviewer_kind: str,
    listened_indices: Sequence[int],
    review_notes: Sequence[str],
    manifest_path: str | Path | None = None,
    plan_path: str | Path | None = None,
) -> Dict[str, Any]:
    """Bind an actual-listening declaration to selected line WAV bytes."""
    if reviewer_kind not in LISTENING_REVIEWER_KINDS:
        raise ValueError("reviewer_kind 必须是 human 或 executor_audio")
    if not _nonempty_string_list(list(review_notes) if isinstance(review_notes, tuple) else review_notes):
        raise ValueError("实际听辨必须留下 review_notes")
    rows_by_idx = _manifest_rows(manifest)
    wanted = {int(x) for x in listened_indices}
    if plan_path is not None:
        required, plan_issues = _validate_plan(
            manifest, manifest_path=manifest_path, plan_path=plan_path,
        )
        if plan_issues:
            raise ValueError("key-line plan 无效：" + "；".join(plan_issues))
    else:
        required = _required_key_line_indices(manifest)
    if not required.issubset(wanted):
        raise ValueError("关键句尚未全部实际听辨：" + ", ".join(str(x) for x in sorted(required - wanted)))
    rows: List[Dict[str, Any]] = []
    unknown = wanted - set(rows_by_idx)
    if unknown:
        raise ValueError("listened_indices 不在当前 manifest：" + ", ".join(str(x) for x in sorted(unknown)))
    for idx in sorted(wanted):
        entry = rows_by_idx[idx]
        wav_path = resolve_line_wav(wav_dir, entry)
        if not wav_path or not wav_path.is_file():
            raise ValueError(f"line {idx} 的 line_wav 缺失")
        rows.append({"index": idx, "line_wav": str(wav_path.resolve()), "sha256": _sha256(wav_path)})
    payload = {
        "kind": LISTENING_KIND, "version": LISTENING_VERSION, "status": "reviewed", "reviewed_at": _now_iso(),
        "reviewer_kind": reviewer_kind, "listened_lines": rows, "key_line_coverage": 1.0,
        "review_notes": [str(x).strip() for x in review_notes if str(x).strip()],
        "manifest": _manifest_binding(manifest, manifest_path),
        "final_user_acceptance": False,
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def validate_listening_receipt(
    wav_dir: str | Path,
    manifest: Sequence[Mapping[str, Any]],
    receipt_path: str | Path,
    *,
    manifest_path: str | Path | None = None,
    plan_path: str | Path | None = None,
) -> Dict[str, Any]:
    """Strictly revalidate actual-listening evidence against current bytes.

    The receipt is a hash-bound executor/human declaration, not proof that a
    person listened and never final user acceptance.  Callers must not infer
    completion from its self-reported ``status``.
    """
    issues: List[str] = []
    try:
        rows_by_idx = _manifest_rows(manifest)
        current_binding = _manifest_binding(manifest, manifest_path)
        required, plan_issues = _validate_plan(
            manifest, manifest_path=manifest_path, plan_path=plan_path,
        )
        issues.extend(plan_issues)
    except Exception as exc:
        return {
            "kind": "n2d_voice_listening_check", "version": 1, "status": "block",
            "issues": [str(exc)], "required_key_line_indices": [], "key_line_coverage": 0.0,
            "receipt": str(receipt_path), "final_user_acceptance": False,
        }

    path = Path(receipt_path)
    # No current key line and no suspicious/stale plan: explicitly non-blocking.
    if not required and not issues:
        return {
            "kind": "n2d_voice_listening_check", "version": 1, "status": "not_applicable",
            "issues": [], "required_key_line_indices": [], "key_line_coverage": 1.0,
            "receipt": str(path), "manifest": current_binding, "final_user_acceptance": False,
        }
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        receipt = None
        if required:
            issues.append("缺或无法解析 voice_listening_receipt.json")
    listened: Dict[int, Mapping[str, Any]] = {}
    if isinstance(receipt, Mapping):
        if receipt.get("kind") != LISTENING_KIND:
            issues.append("listening receipt kind 无效")
        if type(receipt.get("version")) is not int or receipt.get("version") != LISTENING_VERSION:
            issues.append("listening receipt version 无效")
        if receipt.get("status") != "reviewed":
            issues.append("listening receipt status 无效")
        if receipt.get("reviewer_kind") not in LISTENING_REVIEWER_KINDS:
            issues.append("listening receipt reviewer_kind 无效")
        if not _timezone_iso(receipt.get("reviewed_at")):
            issues.append("listening receipt reviewed_at 缺有效时区")
        if not _nonempty_string_list(receipt.get("review_notes")):
            issues.append("listening receipt 缺有效 review_notes")
        if receipt.get("final_user_acceptance") is not False:
            issues.append("listening receipt 不得冒充最终用户验收")
        recorded_binding = receipt.get("manifest") if isinstance(receipt.get("manifest"), Mapping) else {}
        for field in ("contract_sha256", "path", "sha256"):
            if field in current_binding and recorded_binding.get(field) != current_binding[field]:
                issues.append(f"listening receipt manifest.{field} 已过期")
        receipt_lines = receipt.get("listened_lines")
        if not isinstance(receipt_lines, list):
            issues.append("listened_lines 必须是数组")
            receipt_lines = []
        for row in receipt_lines:
            if not isinstance(row, Mapping):
                issues.append("listened_lines 每行必须是对象")
                continue
            try:
                if type(row.get("index")) is not int:
                    raise ValueError
                idx = row["index"]
            except Exception:
                issues.append("listened_lines.index 无效")
                continue
            if idx in listened:
                issues.append(f"listened_lines 重复 index：{idx}")
                continue
            listened[idx] = row
        unknown = set(listened) - set(rows_by_idx)
        if unknown:
            issues.append("listened_lines 含非当前 manifest 行：" + ", ".join(str(x) for x in sorted(unknown)))
        for idx, row in listened.items():
            entry = rows_by_idx.get(idx)
            if entry is None:
                continue
            wav_path = resolve_line_wav(wav_dir, entry)
            if not wav_path or not wav_path.is_file():
                issues.append(f"line {idx} 当前 line_wav 缺失")
                continue
            if str(row.get("line_wav") or "") != str(wav_path.resolve()):
                issues.append(f"line {idx} line_wav path 已变化")
            if str(row.get("sha256") or "") != _sha256(wav_path):
                issues.append(f"line {idx} line_wav SHA 已变化")
        missing = required - set(listened)
        if missing:
            issues.append("关键句尚未全部实际听辨：" + ", ".join(str(x) for x in sorted(missing)))
        coverage = len(required & set(listened)) / len(required) if required else 1.0
        try:
            raw_coverage = receipt.get("key_line_coverage")
            if isinstance(raw_coverage, bool) or not isinstance(raw_coverage, (int, float)) or not math.isfinite(float(raw_coverage)):
                raise ValueError
            reported_coverage = float(raw_coverage)
        except Exception:
            reported_coverage = -1.0
        if abs(reported_coverage - coverage) > 1e-9 or coverage < 1.0:
            issues.append(f"key_line_coverage 无效：reported={reported_coverage} derived={coverage:.4f}")
    elif required and receipt is not None:
        issues.append("listening receipt 必须是对象")
    coverage = len(required & set(listened)) / len(required) if required else 1.0
    return {
        "kind": "n2d_voice_listening_check", "version": 1,
        "status": "pass" if not issues else "block", "issues": issues,
        "required_key_line_indices": sorted(required), "key_line_coverage": round(coverage, 4),
        "receipt": str(path), "manifest": current_binding, "final_user_acceptance": False,
    }
