#!/usr/bin/env python3
"""Hash-bound creative watchdown for an n2d episode master.

This is an executor/human preflight receipt.  It can prove which bytes were
watched, for how long and what timecoded findings were recorded; it explicitly
cannot represent final user acceptance or the release completion verdict.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


KIND = "n2d_creative_watchdown"
VERSION = 1
DIMENSIONS = ("story_performance", "visual_continuity", "audio_dialogue", "pacing")
REVIEWER_KINDS = {"human", "executor_visual_audio"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def episode_label(value: str) -> str:
    value = str(value or "").strip()
    return value if value.startswith("第") and value.endswith("集") else f"第{value}集"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"ffprobe 失败 returncode={result.returncode}: {(result.stderr or '')[-300:]}")
    try:
        duration = float((result.stdout or "").strip())
    except Exception as exc:
        raise ValueError("ffprobe 未返回有效 duration") from exc
    if duration <= 0:
        raise ValueError("master duration 必须大于 0")
    return duration


def resolve_master(root: Path, ep: str, master: str | Path | None = None) -> Path:
    ep = episode_label(ep)
    if master:
        path = Path(master)
        path = path if path.is_absolute() else root / path
        if not path.is_file():
            raise FileNotFoundError(f"master 不存在：{path}")
        return path
    exact = root / "合成" / ep / f"成片_{ep}_zh.mp4"
    if exact.is_file():
        return exact
    candidates = sorted((root / "合成" / ep).glob("*.mp4")) if (root / "合成" / ep).is_dir() else []
    candidates = [p for p in candidates if "preview" not in p.name.lower() and "animatic" not in p.name.lower()]
    if len(candidates) != 1:
        raise FileNotFoundError(f"无法唯一解析 {ep} master；请显式传 --master")
    return candidates[0]


def receipt_path(root: Path, ep: str) -> Path:
    return root / "生产数据" / f"creative_watchdown_{episode_label(ep)}.json"


def _normalize_findings(findings: Sequence[Mapping[str, Any]], duration: float) -> List[Dict[str, Any]]:
    if not isinstance(findings, (list, tuple)):
        raise ValueError("timecode_findings 必须是数组")
    rows: List[Dict[str, Any]] = []
    for item in findings:
        if not isinstance(item, Mapping):
            raise ValueError("每条 finding 必须是对象")
        raw_timecode = item.get("timecode_sec")
        if isinstance(raw_timecode, bool) or not isinstance(raw_timecode, (int, float)) or not math.isfinite(float(raw_timecode)):
            raise ValueError("每条 finding 必须有数字 timecode_sec")
        timecode = float(raw_timecode)
        if timecode < 0 or timecode > duration + 0.05:
            raise ValueError(f"finding timecode 超出 master：{timecode:.3f}s")
        if not isinstance(item.get("severity"), str):
            raise ValueError("finding severity 必须是 note/warn/block")
        severity = item["severity"].strip().lower()
        if severity not in {"note", "warn", "block"}:
            raise ValueError("finding severity 必须是 note/warn/block")
        if not isinstance(item.get("dimension"), str):
            raise ValueError("finding dimension 不在创作听看合同中")
        dimension = item["dimension"].strip()
        if dimension not in DIMENSIONS:
            raise ValueError("finding dimension 不在创作听看合同中")
        if not isinstance(item.get("message"), str):
            raise ValueError("finding message 不能为空")
        message = item["message"].strip()
        if not message:
            raise ValueError("finding message 不能为空")
        rows.append({"timecode_sec": round(timecode, 3), "severity": severity, "dimension": dimension, "message": message})
    return rows


def _timezone_iso(value: Any) -> bool:
    """Only accept a real ISO timestamp carrying an explicit UTC offset."""
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = dt.datetime.fromisoformat(value.strip())
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _nonempty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(x, str) and x.strip() for x in value)


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"watchdown {field} 必须是有限数字")
    return float(value)


def record_watchdown(
    root: Path,
    ep: str,
    *,
    master: str | Path | None = None,
    reviewer_kind: str,
    watched_duration_sec: float,
    coverage: float,
    dimensions_reviewed: Sequence[str],
    findings: Sequence[Mapping[str, Any]] = (),
    review_notes: Sequence[str] = (),
) -> Dict[str, Any]:
    ep = episode_label(ep)
    path = resolve_master(root, ep, master)
    duration = probe_duration(path)
    if reviewer_kind not in REVIEWER_KINDS:
        raise ValueError("reviewer_kind 必须是 human 或 executor_visual_audio")
    try:
        coverage = float(coverage)
        watched_duration_sec = float(watched_duration_sec)
    except Exception as exc:
        raise ValueError("coverage/watched_duration_sec 必须是数字") from exc
    if not (0.98 <= coverage <= 1.0):
        raise ValueError("整片听看 coverage 必须至少 0.98")
    if watched_duration_sec + 0.05 < duration * coverage:
        raise ValueError(f"实际听看时长不足：{watched_duration_sec:.3f}/{duration:.3f}s")
    dimensions = sorted({str(x) for x in dimensions_reviewed})
    missing = [x for x in DIMENSIONS if x not in dimensions]
    if missing:
        raise ValueError("未覆盖创作维度：" + ", ".join(missing))
    notes = [str(x).strip() for x in review_notes if str(x).strip()]
    if not notes:
        raise ValueError("整片听看必须留下 review_notes")
    rows = _normalize_findings(findings, duration)
    status = "needs_revision" if any(x["severity"] == "block" for x in rows) else "pass"
    payload = {
        "kind": KIND,
        "version": VERSION,
        "episode": ep,
        "status": status,
        "reviewed_at": now_iso(),
        "reviewer_kind": reviewer_kind,
        "master": {"path": relpath(root, path), "sha256": file_sha256(path), "duration_sec": round(duration, 3)},
        "watched_duration_sec": round(watched_duration_sec, 3),
        "coverage": round(coverage, 4),
        "dimensions_reviewed": dimensions,
        "timecode_findings": rows,
        "review_notes": notes,
        "scope": "creative_preflight_only",
        "final_user_acceptance": False,
        "release_completion_verdict": False,
    }
    out = receipt_path(root, ep)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f"{out.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, out)
    return payload


def validate_watchdown(root: Path, ep: str, master: str | Path | None = None) -> Dict[str, Any]:
    ep = episode_label(ep)
    out = receipt_path(root, ep)
    issues: List[str] = []
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
    except Exception:
        data = None
        issues.append("缺 creative watchdown receipt")
    derived_status = "block"
    normalized_findings: List[Dict[str, Any]] = []
    if not isinstance(data, Mapping):
        issues.append("creative watchdown receipt 必须是对象")
    else:
        if data.get("kind") != KIND:
            issues.append("watchdown kind 无效")
        if type(data.get("version")) is not int or data.get("version") != VERSION:
            issues.append("watchdown version 无效")
        if data.get("episode") != ep:
            issues.append("watchdown episode 与当前集不一致")
        if data.get("reviewer_kind") not in REVIEWER_KINDS:
            issues.append("watchdown reviewer_kind 无效")
        if not _timezone_iso(data.get("reviewed_at")):
            issues.append("watchdown reviewed_at 缺有效时区")
        if data.get("final_user_acceptance") is not False or data.get("release_completion_verdict") is not False:
            issues.append("creative watchdown 不得冒充最终验收/完成 verdict")
        if data.get("scope") != "creative_preflight_only":
            issues.append("creative watchdown scope 无效")
        try:
            recorded = data.get("master") if isinstance(data.get("master"), Mapping) else {}
            recorded_path = str(recorded.get("path") or "").strip()
            recorded_sha = str(recorded.get("sha256") or "").strip().lower()
            recorded_duration = _finite_number(recorded.get("duration_sec"), "master.duration_sec")
            if not recorded_path:
                raise ValueError("watchdown master.path 缺失")
            if not re.fullmatch(r"[0-9a-f]{64}", recorded_sha):
                raise ValueError("watchdown master.sha256 无效")
            if recorded_duration <= 0:
                raise ValueError("watchdown master.duration_sec 无效")
            current = resolve_master(root, ep, master or recorded_path)
            if recorded_sha != file_sha256(current):
                issues.append("master SHA 已变化，必须重新整片听看")
            duration = probe_duration(current)
            if abs(recorded_duration - duration) > 0.1:
                issues.append("master duration 已变化")
            coverage = _finite_number(data.get("coverage"), "coverage")
            watched_duration = _finite_number(data.get("watched_duration_sec"), "watched_duration_sec")
            if not (0.98 <= coverage <= 1.0):
                issues.append("watchdown coverage 必须在 0.98..1.0")
            if watched_duration < 0 or watched_duration + 0.05 < duration * coverage:
                issues.append("watched duration/coverage 不足")
            normalized_findings = _normalize_findings(data.get("timecode_findings") or [], duration)
            derived_status = "needs_revision" if any(row["severity"] == "block" for row in normalized_findings) else "pass"
        except Exception as exc:
            issues.append(str(exc))
        dimensions = data.get("dimensions_reviewed")
        if (
            not isinstance(dimensions, list)
            or any(not isinstance(x, str) for x in dimensions)
            or len(dimensions) != len(DIMENSIONS)
            or sorted(dimensions) != sorted(DIMENSIONS)
        ):
            issues.append("创作维度覆盖不完整")
        if not _nonempty_string_list(data.get("review_notes")):
            issues.append("缺 review_notes")
        if data.get("status") != derived_status:
            issues.append(f"watchdown 自报 status 与 findings 推导不一致：reported={data.get('status')} derived={derived_status}")
        if derived_status == "needs_revision":
            issues.append("仍有 block 级 timecode finding")
    return {
        "kind": "n2d_creative_watchdown_check",
        "episode": ep,
        "status": "pass" if not issues else "block",
        "issues": issues,
        "derived_status": derived_status,
        "normalized_findings": normalized_findings,
        "receipt": str(out),
        "final_user_acceptance": False,
    }


def _finding_arg(raw: str) -> Dict[str, Any]:
    parts = raw.split(":", 3)
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("finding 格式：timecode:severity:dimension:message")
    try:
        timecode = float(parts[0])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("finding timecode 必须是数字") from exc
    return {"timecode_sec": timecode, "severity": parts[1], "dimension": parts[2], "message": parts[3]}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="hash-bound n2d creative master watchdown")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("command", choices=("record", "check"))
    ap.add_argument("--master")
    ap.add_argument("--reviewer-kind", choices=("human", "executor_visual_audio"), default="executor_visual_audio")
    ap.add_argument("--watched-duration-sec", type=float, default=0.0)
    ap.add_argument("--coverage", type=float, default=1.0)
    ap.add_argument("--dimension", action="append", choices=DIMENSIONS, default=[])
    ap.add_argument("--finding", action="append", type=_finding_arg, default=[])
    ap.add_argument("--review-note", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    if ns.command == "record":
        payload = record_watchdown(
            root, ns.episode, master=ns.master, reviewer_kind=ns.reviewer_kind,
            watched_duration_sec=ns.watched_duration_sec, coverage=ns.coverage,
            dimensions_reviewed=ns.dimension, findings=ns.finding, review_notes=ns.review_note,
        )
        code = 0 if payload["status"] == "pass" else 2
    else:
        payload = validate_watchdown(root, ns.episode, ns.master)
        code = 0 if payload["status"] == "pass" else 2
    print(json.dumps(payload, ensure_ascii=False, indent=2) if ns.json else f"creative watchdown: {payload['status']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
