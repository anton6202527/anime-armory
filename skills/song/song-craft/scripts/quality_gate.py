#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage gates for the song production line.

The gate distinguishes missing evidence from failed evidence and binds selection
to the reviewed audio. A waiver is explicit, reasoned, and written to the gate
receipt; it never changes the underlying findings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date
from typing import Any


KIND = "song_quality_gate"
REVIEW_DIMENSIONS = ("hook", "melody", "vocal", "arrangement", "mix", "brief_fit")


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _finding(items: list[dict[str, str]], issue_id: str, message: str, path: str) -> None:
    items.append({"id": issue_id, "severity": "blocking", "message": message, "path": path})


def _passed_report(root: str, relpath: str, items: list[dict[str, str]]) -> dict[str, Any]:
    payload = load_json(os.path.join(root, relpath), {}) or {}
    if not payload:
        _finding(items, "GATE-MISSING-EVIDENCE", f"缺少阶段证据 {relpath}。", relpath)
    elif payload.get("passed") is not True:
        _finding(items, "GATE-FAILED-EVIDENCE", f"阶段证据未通过：{relpath}。", relpath)
    return payload


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fresh_report(root: str, report_rel: str, source_rel: str, items: list[dict[str, str]], *, text: bool = False) -> None:
    report = _passed_report(root, report_rel, items)
    source_path = os.path.join(root, source_rel)
    if not report or not os.path.isfile(source_path):
        if not os.path.isfile(source_path):
            _finding(items, "GATE-MISSING-SOURCE", f"缺少阶段源文件 {source_rel}。", source_rel)
        return
    if text:
        expected = sha256_file(source_path)
    else:
        payload = load_json(source_path, None)
        expected = _canonical_sha256(payload) if payload is not None else ""
    if not expected or report.get("source_sha256") != expected:
        _finding(items, "GATE-STALE-EVIDENCE", f"{report_rel} 与当前 {source_rel} 不一致，需重跑检查。", report_rel)


def compose_findings(root: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    _fresh_report(root, "创作/song_brief_check.json", "创作/song_brief.json", findings)
    _fresh_report(root, "素材/reference_pack_check.json", "素材/reference_pack.json", findings)
    _fresh_report(root, "词/lyric_prosody.json", "词/lyrics.md", findings, text=True)
    _fresh_report(root, "歌/song_form_check.json", "歌/song_form.json", findings)
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    rights = str(meta.get("rights_status") or "").strip().lower()
    vocal = str(meta.get("vocal_source") or "").strip().lower()
    if rights in {"", "unknown", "未定", "未知"}:
        _finding(findings, "GATE-RIGHTS-UNKNOWN", "词曲权利状态未知。", "_meta.json:rights_status")
    authorized = any(token in vocal for token in ("synthetic", "合成", "authorized", "授权", "own", "自有", "self"))
    if not vocal or not authorized:
        _finding(findings, "GATE-VOCAL-AUTH", "演唱音色必须明确为自有、已授权或合成。", "_meta.json:vocal_source")
    return findings


def selection_findings(root: str, take_id: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    manifest = load_json(os.path.join(root, "歌", "takes_manifest.json"), {}) or {}
    take = next((row for row in manifest.get("takes", []) if row.get("take_id") == take_id), None)
    if not take:
        _finding(findings, "GATE-TAKE-MISSING", f"manifest 中没有 {take_id}。", "歌/takes_manifest.json")
        return findings
    audio_rel = str(take.get("audio_path") or "")
    audio_path = os.path.join(root, audio_rel)
    if not audio_rel or not os.path.isfile(audio_path):
        _finding(findings, "GATE-TAKE-AUDIO", f"{take_id} 没有可读取音频。", audio_rel or "歌/takes_manifest.json")
    score = take.get("score") if isinstance(take.get("score"), dict) else {}
    missing = [key for key in REVIEW_DIMENSIONS if not isinstance(score.get(key), (int, float))]
    if missing:
        _finding(findings, "GATE-SCORE-INCOMPLETE", "manifest 六维评分不完整：" + ", ".join(missing), "歌/takes_manifest.json")
    elif min(float(score[key]) for key in REVIEW_DIMENSIONS) < 2:
        _finding(findings, "GATE-SCORE-FLOOR", "存在低于 2/5 的硬伤维度；修复或明确 waiver 后再定稿。", "歌/takes_manifest.json")
    review = load_json(os.path.join(root, "歌", "take_review.json"), {}) or {}
    row = next((item for item in review.get("reviews", []) if item.get("take_id") == take_id), None)
    if not row:
        _finding(findings, "GATE-REVIEW-MISSING", f"{take_id} 缺结构化盲听记录。", "歌/take_review.json")
    else:
        scores = row.get("scores") if isinstance(row.get("scores"), dict) else {}
        if any(not isinstance(scores.get(key), (int, float)) or scores.get(key) <= 0 for key in REVIEW_DIMENSIONS):
            _finding(findings, "GATE-REVIEW-INCOMPLETE", f"{take_id} 的六维盲听评分不完整。", "歌/take_review.json")
        if audio_rel and os.path.isfile(audio_path):
            expected = row.get("audio_sha256")
            actual = sha256_file(audio_path)
            if not expected:
                _finding(findings, "GATE-REVIEW-HASH-MISSING", "盲听记录未绑定音频 sha256。", "歌/take_review.json")
            elif expected != actual:
                _finding(findings, "GATE-REVIEW-STALE", "盲听记录绑定的音频已变化。", "歌/take_review.json")
        if scores and all(isinstance(scores.get(key), (int, float)) for key in REVIEW_DIMENSIONS):
            if any(float(scores[key]) != float(score[key]) for key in REVIEW_DIMENSIONS if key in score):
                _finding(findings, "GATE-SCORE-DRIFT", "manifest 与盲听报告的六维评分不一致。", "歌/take_review.json")
        unresolved = [
            note for note in row.get("timecode_notes") or []
            if str(note.get("severity") or "").lower() in {"block", "blocking", "critical", "严重"}
            and str(note.get("status") or "open").lower() not in {"resolved", "accepted", "fixed", "已解决", "接受"}
        ]
        if unresolved:
            _finding(findings, "GATE-UNRESOLVED-NOTES", f"仍有 {len(unresolved)} 条阻断级试听问题未关闭。", "歌/take_review.json")
        recommended = str(review.get("recommended_take") or "")
        rationale = str(review.get("selection_rationale") or "").strip().lower()
        if recommended and recommended != take_id and (not rationale or rationale.startswith("highest total")):
            _finding(findings, "GATE-SELECTION-RATIONALE", "选择非推荐 take 时必须记录明确理由。", "歌/take_review.json")
    return findings


def evaluate(root: str, stage: str, *, take_id: str = "", waiver_reason: str = "") -> dict[str, Any]:
    root = os.path.abspath(root)
    if stage == "compose":
        findings = compose_findings(root)
    elif stage == "select":
        findings = selection_findings(root, take_id)
    else:
        raise ValueError(f"unsupported stage: {stage}")
    waiver = waiver_reason.strip()
    waiver_valid = len(waiver) >= 10
    return {
        "schema_version": 1,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "stage": stage,
        "take_id": take_id or None,
        "passed": not findings or waiver_valid,
        "passed_without_waiver": not findings,
        "waiver": {"used": bool(waiver), "valid": waiver_valid, "reason": waiver},
        "blocking": len(findings),
        "findings": findings,
    }


def write_report(root: str, report: dict[str, Any]) -> str:
    path = os.path.join(root, "评审", f"quality_gate_{report['stage']}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="检查 song 阶段质量闸门")
    ap.add_argument("project_root")
    ap.add_argument("--stage", required=True, choices=("compose", "select"))
    ap.add_argument("--take", default="")
    ap.add_argument("--waiver-reason", default="")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    report = evaluate(args.project_root, args.stage, take_id=args.take, waiver_reason=args.waiver_reason)
    if args.write:
        print(f"[ok] quality gate -> {write_report(args.project_root, report)}")
    if args.json or not args.write:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
