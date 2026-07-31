#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aggregate ad consistency evidence into one review-facing findings file.

This provides a single consistency findings surface for the ad line.  It only
reads existing ad artifacts and stays self-contained.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable


KIND = "ad_consistency_findings"
SEVERITIES = ("block", "warn", "info")

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import asset_consistency  # noqa: E402
import asset_drift_report  # noqa: E402
import final_media_consistency  # noqa: E402
import voice_consistency  # noqa: E402


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


def rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


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


def report_counts(report: Any) -> tuple[int | None, int | None]:
    if not isinstance(report, dict):
        return None, None
    summary = report.get("summary")
    if not isinstance(summary, dict):
        return None, None
    try:
        return int(summary.get("block") or 0), int(summary.get("warn") or 0)
    except (TypeError, ValueError):
        return None, None


def has_media(folder: str, suffixes: tuple[str, ...]) -> bool:
    if not os.path.isdir(folder):
        return False
    return any(name.lower().endswith(suffixes) for name in os.listdir(folder))


def add_report_summary(findings: list[dict[str, Any]], root: str, relpath: str,
                       dimension: str, label: str, missing_severity: str) -> Any:
    path = os.path.join(root, relpath)
    report = load_json(path)
    if report is None:
        findings.append(finding(
            missing_severity,
            dimension,
            f"{label}_missing",
            f"缺 {relpath}，一致性证据链不闭合。",
            relpath,
        ))
        return None
    blocks, warns = report_counts(report)
    if blocks is None:
        findings.append(finding("block", dimension, f"{label}_malformed", f"{relpath} 缺 summary.block/warn。", relpath))
        return report
    if blocks:
        findings.append(finding("block", dimension, f"{label}_block", f"{relpath} 仍有 block={blocks}。", relpath, label))
    if warns:
        findings.append(finding("warn", dimension, f"{label}_warn", f"{relpath} 有 warn={warns}，需人工确认。", relpath, label))
    if not blocks and not warns:
        findings.append(finding("info", dimension, f"{label}_clean", f"{relpath} 一致性摘要为 0 block / 0 warn。", relpath, label))
    return report


def product_qc_checks(root: str, findings: list[dict[str, Any]]) -> None:
    image_dir = os.path.join(root, "出图", "分镜", "图片")
    missing_sev = "block" if has_media(image_dir, (".png", ".jpg", ".jpeg", ".webp")) else "warn"
    report = add_report_summary(findings, root, "出图/分镜/product_qc.json",
                                "product_identity", "product_qc", missing_sev)
    if not isinstance(report, dict):
        return
    env = report.get("qc_environment") if isinstance(report.get("qc_environment"), dict) else {}
    precision = str(env.get("precision_level") or "").strip()
    manual_ok = bool(report.get("manual_review_accepted") or env.get("manual_review_accepted"))
    if precision and precision != "full" and not manual_ok:
        findings.append(finding(
            "block",
            "product_identity",
            "product_qc_precision",
            f"product_qc 精度为 {precision}，缺完整像素证据；正式投放前需补依赖重跑或人工留痕。",
            "出图/分镜/product_qc.json",
        ))
    for item in (report.get("findings") or [])[:20]:
        sev = item.get("severity")
        if sev in {"block", "warn"}:
            findings.append(finding(
                sev,
                "product_identity",
                str(item.get("check") or "product_qc_finding"),
                str(item.get("reason") or item.get("msg") or "product_qc finding"),
                "出图/分镜/product_qc.json",
                "product_qc",
                {"shot": item.get("shot"), "detail": item.get("detail") or {}},
            ))


def video_checks(root: str, findings: list[dict[str, Any]]) -> None:
    add_report_summary(findings, root, "出视频/分镜/contract_inheritance.json",
                       "video_handoff", "contract_inheritance", "warn")
    add_report_summary(findings, root, "出视频/分镜/video_qc.json",
                       "video_handoff", "video_qc", "block")


def compliance_checks(root: str, findings: list[dict[str, Any]]) -> None:
    ad_law = add_report_summary(findings, root, "脚本/广告法机检报告.json",
                                "claims_rights", "ad_law", "block")
    if isinstance(ad_law, dict) and ad_law.get("disabled"):
        findings.append(finding("warn", "claims_rights", "ad_law_disabled",
                                "广告法机检关闭，只能在明确非中国大陆投放时人工放行。",
                                "脚本/广告法机检报告.json"))
    ai_usage_path = os.path.join(root, "合规", "ai_usage.json")
    usage = load_json(ai_usage_path)
    if not isinstance(usage, dict):
        findings.append(finding("block", "claims_rights", "ai_usage_missing",
                                "缺 AI 使用/授权披露，投放前证据链不完整。", "合规/ai_usage.json"))
    else:
        findings.append(finding("info", "claims_rights", "ai_usage_present",
                                "AI 使用/授权披露已留痕。", "合规/ai_usage.json"))


def build_report(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    findings: list[dict[str, Any]] = []
    for module, relpath, dimension in (
        (asset_consistency, "生产数据/asset_consistency.json", "asset_identity"),
        (voice_consistency, "生产数据/voice_consistency.json", "voice_identity"),
        # 跨镜聚合层：回答"哪个资产从第几镜开始崩"。它自身恒不产 block（见其 finding()
        # 构造层降档），故此处直通 severity 不会把启发式聚合变成硬阻断。
        (asset_drift_report, "生产数据/asset_drift_report.json", "asset_drift"),
    ):
        payload = module.build(Path(root))
        write_json(os.path.join(root, relpath), payload)
        for item in payload.get("findings") or []:
            findings.append(finding(str(item.get("severity") or "info"), dimension,
                                    str(item.get("code") or "finding"), str(item.get("msg") or ""),
                                    relpath, payload.get("kind", ""), dict(item)))
    final_media = final_media_consistency.build(Path(root), write_frames=True)
    write_json(os.path.join(root, "生产数据/final_media_consistency.json"), final_media)
    for item in final_media.get("findings") or []:
        findings.append(finding(str(item.get("severity") or "info"), "final_media_identity",
                                str(item.get("code") or "finding"), str(item.get("msg") or ""),
                                "生产数据/final_media_consistency.json", final_media.get("kind", ""), dict(item)))
    product_qc_checks(root, findings)
    video_checks(root, findings)
    compliance_checks(root, findings)
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
            "出图/分镜/product_qc.json",
            "出视频/分镜/contract_inheritance.json",
            "出视频/分镜/video_qc.json",
            "脚本/广告法机检报告.json",
            "合规/ai_usage.json",
            "生产数据/asset_consistency.json",
            "生产数据/voice_consistency.json",
            "生产数据/asset_drift_report.json",
            "生产数据/final_media_consistency.json",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Ad Consistency Findings",
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
    ap = argparse.ArgumentParser(description="汇总广告产品/品牌/视频/合规一致性 findings")
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
