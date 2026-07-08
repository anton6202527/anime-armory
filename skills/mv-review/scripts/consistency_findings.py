#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aggregate MV visual/timing consistency evidence into one findings file."""
from __future__ import annotations

import argparse
import json
import os
from datetime import date
from typing import Any, Iterable


KIND = "mv_consistency_findings"
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


def has_clip_plan(root: str) -> bool:
    return os.path.exists(os.path.join(root, "分镜", "clip_plan.json"))


def image_qc(findings: list[dict[str, Any]], root: str) -> None:
    rel = "生产数据/image_qc/image_qc.json"
    report = load_json(os.path.join(root, rel))
    if not isinstance(report, dict):
        sev = "warn" if has_clip_plan(root) else "info"
        findings.append(finding(sev, "visual_identity", "image_qc_missing",
                                "缺 mv-image 出图落档机检；有 clip_plan 时应先跑 image_qc 再出视频。", rel))
        return
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    hard = int(summary.get("hard_blocks") or 0)
    advisory = int(summary.get("advisory") or summary.get("warnings") or 0)
    if hard:
        findings.append(finding("block", "visual_identity", "image_qc_block", f"image_qc hard_blocks={hard}。", rel, "image_qc"))
    if advisory:
        findings.append(finding("warn", "visual_identity", "image_qc_warn", f"image_qc advisory={advisory}，需并排复核。", rel, "image_qc"))
    env = report.get("qc_environment") if isinstance(report.get("qc_environment"), dict) else {}
    precision = str(env.get("precision_level") or "").strip()
    manual_ok = bool(report.get("manual_review_accepted") or env.get("manual_review_accepted"))
    if precision and precision != "full" and not manual_ok:
        findings.append(finding("block", "visual_identity", "image_qc_precision",
                                f"image_qc 精度为 {precision}，不能当作完整脸/主色一致性证据。", rel))
    elif precision and precision != "full":
        findings.append(finding("warn", "visual_identity", "image_qc_precision_manual",
                                f"image_qc 精度为 {precision}，已有人工放行留痕。", rel))
    if not hard and not advisory and (not precision or precision == "full"):
        findings.append(finding("info", "visual_identity", "image_qc_clean", "出图一致性机检没有阻断项。", rel))


def registry_checks(findings: list[dict[str, Any]], root: str) -> None:
    if not has_clip_plan(root):
        return
    for rel, dim, label in (
        ("设定/identity_registry.json", "reference_coverage", "identity_registry"),
        ("设定/asset_registry.json", "reference_coverage", "asset_registry"),
        ("分镜/reference_plan.json", "reference_coverage", "reference_plan"),
        ("设定/reference_requirements.json", "reference_coverage", "reference_requirements"),
    ):
        payload = load_json(os.path.join(root, rel))
        if not isinstance(payload, dict):
            findings.append(finding("warn", dim, f"{label}_missing", f"缺 {rel}，身份/资产参考链不闭合。", rel))
            continue
        rows = payload.get("reference_groups") or payload.get("clips") or payload.get("requirements") or []
        if isinstance(rows, list) and rows:
            ready = sum(1 for row in rows if isinstance(row, dict) and row.get("status") == "ready")
            if ready < len(rows):
                findings.append(finding("warn", dim, f"{label}_partial",
                                        f"{label} ready={ready}/{len(rows)}，未 ready 项需人判或补参考。", rel))
            else:
                findings.append(finding("info", dim, f"{label}_ready", f"{label} ready={ready}/{len(rows)}。", rel))


def report_summary(findings: list[dict[str, Any]], root: str, rel: str,
                   dimension: str, label: str, missing_severity: str = "warn") -> None:
    report = load_json(os.path.join(root, rel))
    if not isinstance(report, dict):
        findings.append(finding(missing_severity, dimension, f"{label}_missing", f"缺 {rel}。", rel))
        return
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    hard = int(summary.get("hard_blocks") or summary.get("block") or 0)
    warn = int(summary.get("warnings") or summary.get("warn") or 0)
    if hard:
        findings.append(finding("block", dimension, f"{label}_block", f"{label} hard/block={hard}。", rel, label))
    if warn:
        findings.append(finding("warn", dimension, f"{label}_warn", f"{label} warnings={warn}。", rel, label))
    if not hard and not warn:
        findings.append(finding("info", dimension, f"{label}_clean", f"{label} 没有阻断项。", rel, label))


def video_qc_details(findings: list[dict[str, Any]], root: str) -> None:
    rel = "生产数据/video_qc/video_qc.json"
    report_summary(findings, root, rel, "video_handoff", "video_qc")
    report = load_json(os.path.join(root, rel), {}) or {}
    for seam in report.get("seams") or []:
        risks = seam.get("risk") or []
        if risks:
            findings.append(finding("warn", "video_handoff", "seam_review",
                                    f"{seam.get('from')} -> {seam.get('to')} 接缝需复核：{', '.join(risks)}。",
                                    rel, "video_qc", {"seam": seam}))


def timing_checks(findings: list[dict[str, Any]], root: str) -> None:
    path = os.path.join(root, "字幕", "alignment_report.json")
    report = load_json(path)
    if isinstance(report, dict):
        warnings = report.get("warnings") or []
        if warnings:
            findings.append(finding("warn", "lyric_timeline", "alignment_warn",
                                    f"字幕对齐报告有 {len(warnings)} 条 warning。", "字幕/alignment_report.json",
                                    "alignment_report", {"warnings": warnings[:10]}))
        else:
            findings.append(finding("info", "lyric_timeline", "alignment_clean", "字幕对齐报告无 warning。", "字幕/alignment_report.json"))


def build_report(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    findings: list[dict[str, Any]] = []
    registry_checks(findings, root)
    image_qc(findings, root)
    report_summary(findings, root, "生产数据/video_inherit_contract/inherit_contract.json",
                   "video_handoff", "inherit_contract")
    video_qc_details(findings, root)
    timing_checks(findings, root)
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
            "设定/identity_registry.json",
            "设定/asset_registry.json",
            "分镜/reference_plan.json",
            "设定/reference_requirements.json",
            "生产数据/image_qc/image_qc.json",
            "生产数据/video_inherit_contract/inherit_contract.json",
            "生产数据/video_qc/video_qc.json",
            "字幕/alignment_report.json",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# MV Consistency Findings",
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
    out_dir = os.path.join(root, "生产数据")
    json_path = os.path.join(out_dir, "consistency_findings.json")
    md_path = os.path.join(out_dir, "consistency_findings.md")
    write_json(json_path, report)
    write_text(md_path, render_markdown(report))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="汇总 MV 身份/参考/出图/视频/字幕一致性 findings")
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
