#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aggregate song consistency evidence into one review-facing findings file."""
from __future__ import annotations

import argparse
import json
import os
from datetime import date
from typing import Any, Iterable


KIND = "song_consistency_findings"
SEVERITIES = ("block", "warn", "info")


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def finding(severity: str, dimension: str, code: str, message: str,
            path: str = "", source: str = "", detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "severity": severity if severity in SEVERITIES else "info",
        "dimension": dimension,
        "code": code,
        "message": message,
        "path": path,
        "source": source,
        "detail": detail or {},
    }


def summary_counts(items: Iterable[dict[str, Any]]) -> dict[str, int]:
    out = {key: 0 for key in SEVERITIES}
    for item in items:
        sev = item.get("severity")
        if sev in out:
            out[sev] += 1
    return out


def check_prosody(findings: list[dict[str, Any]], root: str) -> None:
    rel = "词/lyric_prosody.json"
    report = load_json(os.path.join(root, rel))
    if not isinstance(report, dict):
        sev = "warn" if os.path.exists(os.path.join(root, "词", "lyrics.md")) else "info"
        findings.append(finding(sev, "lyric_prosody", "prosody_missing",
                                "缺歌词可唱性/Hook 检查报告；有歌词时建议先跑 lyric_prosody_check.py。", rel))
        return
    blocking = int(report.get("blocking") or 0)
    warnings = int(report.get("warnings") or 0)
    if blocking:
        findings.append(finding("block", "lyric_prosody", "prosody_block", f"lyric_prosody blocking={blocking}。", rel))
    if warnings:
        findings.append(finding("warn", "lyric_prosody", "prosody_warn", f"lyric_prosody warnings={warnings}。", rel))
    if not blocking and not warnings:
        findings.append(finding("info", "lyric_prosody", "prosody_clean", "歌词 prosody 检查通过。", rel))


def check_form(findings: list[dict[str, Any]], root: str) -> None:
    rel = "歌/song_form.json"
    packet = load_json(os.path.join(root, rel))
    if not isinstance(packet, dict):
        if os.path.exists(os.path.join(root, "词", "lyrics.md")):
            findings.append(finding("warn", "form_structure", "song_form_missing",
                                    "缺曲式/和声/topline 草图，歌词到作曲的结构传递不完整。", rel))
        return
    sections = packet.get("sections") if isinstance(packet.get("sections"), list) else []
    if not sections:
        findings.append(finding("warn", "form_structure", "song_form_empty", "song_form 没有 sections。", rel))
    else:
        findings.append(finding("info", "form_structure", "song_form_present", f"song_form sections={len(sections)}。", rel))


def check_takes(findings: list[dict[str, Any]], root: str) -> None:
    manifest_rel = "歌/takes_manifest.json"
    manifest = load_json(os.path.join(root, manifest_rel))
    song_exists = os.path.exists(os.path.join(root, "歌", "song.wav"))
    if not isinstance(manifest, dict):
        if song_exists:
            findings.append(finding("warn", "take_selection", "takes_manifest_missing",
                                    "已有 song.wav 但缺 takes_manifest，成品来源和一致性选择不可追溯。", manifest_rel))
        return
    takes = manifest.get("takes") if isinstance(manifest.get("takes"), list) else []
    selected = manifest.get("selected_take")
    if song_exists and not selected:
        findings.append(finding("warn", "take_selection", "selected_take_missing",
                                "已有 song.wav 但 selected_take 为空。", manifest_rel))
    elif selected:
        findings.append(finding("info", "take_selection", "selected_take_present", f"selected_take={selected}。", manifest_rel))
    review_rel = "歌/take_review.json"
    review = load_json(os.path.join(root, review_rel))
    if len(takes) >= 2 and not isinstance(review, dict):
        findings.append(finding("warn", "take_selection", "take_review_missing",
                                "多版 take 已存在但缺结构化试听评审，挑版理由不足。", review_rel))
    elif isinstance(review, dict):
        recommended = review.get("recommended_take")
        review_count = int(review.get("review_count") or 0)
        if selected and recommended and selected != recommended:
            findings.append(finding("warn", "take_selection", "selected_differs_from_review",
                                    f"selected_take={selected} 与 take_review 推荐 {recommended} 不一致，需留选择理由。",
                                    review_rel))
        if review_count == 0 and len(takes) >= 2:
            findings.append(finding("warn", "take_selection", "take_review_empty", "take_review 没有实际 reviews。", review_rel))
        else:
            findings.append(finding("info", "take_selection", "take_review_present",
                                    f"take_review review_count={review_count} recommended={recommended or '未定'}。", review_rel))


def check_master(findings: list[dict[str, Any]], root: str) -> None:
    rel = "混音/master_check.json"
    report = load_json(os.path.join(root, rel))
    if not isinstance(report, dict):
        if os.path.exists(os.path.join(root, "歌", "song.wav")):
            findings.append(finding("warn", "master_delivery", "master_check_missing",
                                    "已有 song.wav 但缺母带/交付基础检查。", rel))
        return
    blocking = int(report.get("blocking") or 0)
    warnings = int(report.get("warnings") or 0)
    if report.get("passed") is False or blocking:
        findings.append(finding("block", "master_delivery", "master_check_block",
                                f"master_check 未通过，blocking={blocking}。", rel))
    if warnings:
        findings.append(finding("warn", "master_delivery", "master_check_warn",
                                f"master_check warnings={warnings}。", rel))
    if report.get("passed") is True and not warnings:
        findings.append(finding("info", "master_delivery", "master_check_clean", "master_check 通过。", rel))


def check_rights(findings: list[dict[str, Any]], root: str) -> None:
    ai_rel = "合规/ai_usage.json"
    rights_rel = "合规/rights_metadata.json"
    ai_usage = load_json(os.path.join(root, ai_rel))
    rights = load_json(os.path.join(root, rights_rel))
    song_exists = os.path.exists(os.path.join(root, "歌", "song.wav"))
    if song_exists and not isinstance(ai_usage, dict):
        findings.append(finding("warn", "rights_ai", "ai_usage_missing", "已有成品歌但缺 AI 使用披露。", ai_rel))
    elif isinstance(ai_usage, dict):
        findings.append(finding("info", "rights_ai", "ai_usage_present", "AI 使用披露已留痕。", ai_rel))
    if song_exists and not isinstance(rights, dict):
        findings.append(finding("warn", "rights_ai", "rights_metadata_missing", "已有成品歌但缺权益元数据。", rights_rel))
    elif isinstance(rights, dict):
        status = rights.get("rights_status") or "unknown"
        sev = "block" if status in {"", "unknown", None} else "info"
        findings.append(finding(sev, "rights_ai", "rights_status", f"rights_status={status}。", rights_rel))
    release = load_json(os.path.join(root, "导出", "release_pack.json"))
    if isinstance(release, dict) and release.get("release_ready") is False:
        blockers = ((release.get("readiness") or {}).get("blockers") or [])
        findings.append(finding("block", "rights_ai", "release_pack_not_ready",
                                f"release_pack 未 ready，blockers={len(blockers)}。", "导出/release_pack.json"))


def build_report(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    findings: list[dict[str, Any]] = []
    check_prosody(findings, root)
    check_form(findings, root)
    check_takes(findings, root)
    check_master(findings, root)
    check_rights(findings, root)
    counts = summary_counts(findings)
    return {
        "schema_version": 1,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "summary": {
            **counts,
            "verdict": "block" if counts["block"] else ("review" if counts["warn"] else "ok"),
        },
        "findings": findings,
        "read_scope": [
            "词/lyric_prosody.json",
            "歌/song_form.json",
            "歌/takes_manifest.json",
            "歌/take_review.json",
            "混音/master_check.json",
            "合规/ai_usage.json",
            "合规/rights_metadata.json",
            "导出/release_pack.json",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Song Consistency Findings",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- verdict: {s.get('verdict')}",
        f"- block: {s.get('block')}  warn: {s.get('warn')}  info: {s.get('info')}",
        "",
        "## Findings",
        "",
    ]
    for item in report.get("findings") or []:
        path = f" ({item.get('path')})" if item.get("path") else ""
        lines.append(f"- [{item.get('severity')}] {item.get('dimension')} / {item.get('code')}: {item.get('message')}{path}")
    return "\n".join(lines).rstrip() + "\n"


def write_report(root: str, report: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "评审")
    json_path = os.path.join(out_dir, "consistency_findings.json")
    md_path = os.path.join(out_dir, "consistency_findings.md")
    write_json(json_path, report)
    write_text(md_path, render_markdown(report))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="汇总歌曲歌词/曲式/take/母带/权益一致性 findings")
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.project_root):
        print(f"[err] 找不到作品根：{args.project_root}")
        return 2
    report = build_report(args.project_root)
    if args.write:
        json_path, md_path = write_report(report["project_root"], report)
        print(f"[ok] consistency findings JSON → {json_path}")
        print(f"[ok] consistency findings MD   → {md_path}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(report))
    return 1 if report["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
