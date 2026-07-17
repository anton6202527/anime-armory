#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aggregate MV visual/timing consistency evidence into one findings file."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date
from typing import Any, Iterable


KIND = "mv_consistency_findings"
SEVERITIES = ("block", "warn", "info")


def load_file_hash(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def manual_review_ok(report: dict[str, Any]) -> bool:
    """image_qc 降级人工放行是否有效：具名 + 绑定报告 hash（与 mv-image/mv-craft gate 同算法）。"""
    manual = report.get("manual_review") or {}
    if not (manual.get("accepted") and str(manual.get("reviewer") or "").strip()):
        return False
    stripped = {k: v for k, v in report.items()
                if k not in ("manual_review", "json_path", "markdown_path")}
    encoded = json.dumps(stripped, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return manual.get("bound_report_sha256") == hashlib.sha256(encoded).hexdigest()


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
    manual_ok = manual_review_ok(report)
    if precision and precision != "full" and not manual_ok:
        legacy = " 旧式布尔留痕已不被接受，需 --accept-degraded 具名绑定放行。" if (
            report.get("manual_review_accepted") or env.get("manual_review_accepted")
            or report.get("manual_review")) else ""
        findings.append(finding("block", "visual_identity", "image_qc_precision",
                                f"image_qc 精度为 {precision}，不能当作完整脸/主色一致性证据。{legacy}", rel))
    elif precision and precision != "full":
        findings.append(finding("warn", "visual_identity", "image_qc_precision_manual",
                                f"image_qc 精度为 {precision}，已有具名人工放行（绑定当前报告）。", rel))
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
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    if not meta.get("is_demo") and not (report.get("semantic_review") or {}).get("accepted"):
        findings.append(finding("block", "video_handoff", "semantic_review_missing",
                                "正式项目视频语义复核尚未绑定当前选中视频签收。", rel, "video_qc"))
    semantic = report.get("semantic_review") or {}
    if semantic.get("accepted") and semantic.get("bound_video_sha256") != (report.get("selected_video_sha256") or {}):
        findings.append(finding("block", "video_handoff", "semantic_video_hash_stale",
                                "视频语义签收与当前 selected video hashes 不一致。", rel, "video_qc"))
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
        stale = [
            rel for rel, recorded in (report.get("inputs_sha256") or {}).items()
            if load_file_hash(os.path.join(root, rel)) != recorded
        ]
        if stale:
            findings.append(finding("block", "lyric_timeline", "alignment_stale",
                                    f"歌词对齐报告输入已变化：{stale[0]}。", "字幕/alignment_report.json"))
        warnings = report.get("warnings") or []
        if warnings:
            findings.append(finding("warn", "lyric_timeline", "alignment_warn",
                                    f"字幕对齐报告有 {len(warnings)} 条 warning。", "字幕/alignment_report.json",
                                    "alignment_report", {"warnings": warnings[:10]}))
        else:
            findings.append(finding("info", "lyric_timeline", "alignment_clean", "字幕对齐报告无 warning。", "字幕/alignment_report.json"))


def shot_variety(findings: list[dict[str, Any]], root: str) -> None:
    """视觉多样性/构图冗余事前机检（advisory）——有 clip_plan 时应先跑，出图/出视频前拦同构图反复。"""
    if not has_clip_plan(root):
        return
    rel = "生产数据/shot_variety/shot_variety.json"
    report = load_json(os.path.join(root, rel))
    if not isinstance(report, dict):
        findings.append(finding("info", "shot_variety", "shot_variety_missing",
                                "未跑视觉多样性事前机检（shot_variety_audit）；出图前建议补跑。", rel))
        return
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    warn = int(summary.get("warn") or 0)
    if warn:
        codes = sorted({str(f.get("code")) for f in (report.get("findings") or [])
                        if f.get("severity") == "warn"})
        findings.append(finding("warn", "shot_variety", "shot_variety_warn",
                                f"视觉多样性 advisory={warn}（{'/'.join(codes) or 'n/a'}），回 mv-plan 换景别/机位/场景。", rel, "shot_variety_audit"))
    else:
        findings.append(finding("info", "shot_variety", "shot_variety_clean", "视觉多样性事前机检无重复/单调项。", rel))


REDRAW_RATE_WARN = 0.35        # 单曲工位默认重画率预警线
TAKES_PER_CLIP_WARN = 3.0      # 平均每 clip 抽 take 数超过此值 → 出视频侧烧钱失控预警


def production_stats(findings: list[dict[str, Any]], root: str) -> None:
    """止损轻量件（stop_loss lite）：从生产事件账本与挑版台账算重画率 / 每镜 take 数。

    MV 单曲工位小，只保留必要止损信号；「同一张图反复重抽 / 一个 clip 抽了
    一堆 take 还挑不出」正是积分烧穿的前兆，advisory 提示回看 prompt/参考锚。"""
    events_rel = "生产数据/production_events.jsonl"
    events_path = os.path.join(root, events_rel)
    if os.path.exists(events_path):
        per_asset: dict[str, int] = {}
        try:
            with open(events_path, encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(event, dict) or event.get("event") != "generation":
                        continue
                    if event.get("stage") != "image":
                        continue
                    asset = str((event.get("generation") or {}).get("asset") or "").strip()
                    if asset:
                        per_asset[asset] = per_asset.get(asset, 0) + 1
        except OSError:
            per_asset = {}
        if per_asset:
            redrawn = sum(1 for count in per_asset.values() if count >= 2)
            rate = redrawn / len(per_asset)
            detail = {"assets": len(per_asset), "redrawn_assets": redrawn,
                      "redraw_rate": round(rate, 3), "threshold": REDRAW_RATE_WARN}
            if rate > REDRAW_RATE_WARN:
                worst = max(per_asset.items(), key=lambda kv: kv[1])
                findings.append(finding("warn", "production_economy", "image_redraw_rate_high",
                                        f"出图重画率 {rate:.0%}（{redrawn}/{len(per_asset)} 资产重抽过，"
                                        f"最多 {worst[0]} 抽了 {worst[1]} 次）——积分烧穿前兆；"
                                        "回看该批 prompt 锚点/参考图是否缺失，别硬抽。",
                                        events_rel, "production_events", detail))
            else:
                findings.append(finding("info", "production_economy", "image_redraw_rate",
                                        f"出图重画率 {rate:.0%}（{redrawn}/{len(per_asset)}）。",
                                        events_rel, "production_events", detail))
    jobs_rel = "出视频/jobs_manifest.json"
    jobs = (load_json(os.path.join(root, jobs_rel), {}) or {}).get("jobs") or []
    takes_counts = [len(job.get("takes") or []) for job in jobs if isinstance(job, dict)]
    counted = [n for n in takes_counts if n]
    if counted:
        avg = sum(counted) / len(counted)
        detail = {"jobs_with_takes": len(counted), "avg_takes_per_clip": round(avg, 2),
                  "max_takes": max(counted), "threshold": TAKES_PER_CLIP_WARN}
        if avg > TAKES_PER_CLIP_WARN:
            findings.append(finding("warn", "production_economy", "takes_per_clip_high",
                                    f"平均每 clip 抽 {avg:.1f} 个 take（最多 {max(counted)}）——"
                                    "出视频侧烧钱失控预警；先回 mv-image/mv-plan 修首帧与动作锚再抽。",
                                    jobs_rel, "jobs_manifest", detail))
        else:
            findings.append(finding("info", "production_economy", "takes_per_clip",
                                    f"平均每 clip 抽 {avg:.1f} 个 take。", jobs_rel, "jobs_manifest", detail))


def build_report(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    findings: list[dict[str, Any]] = []
    registry_checks(findings, root)
    shot_variety(findings, root)
    image_qc(findings, root)
    report_summary(findings, root, "生产数据/video_inherit_contract/inherit_contract.json",
                   "video_handoff", "inherit_contract")
    video_qc_details(findings, root)
    timing_checks(findings, root)
    production_stats(findings, root)
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    if has_clip_plan(root) and not meta.get("is_demo"):
        lock = load_json(os.path.join(root, "制片", "picture_lock.json"))
        if not isinstance(lock, dict) or not lock.get("accepted"):
            findings.append(finding("block", "picture_lock", "picture_lock_missing",
                                    "正式项目缺绑定 animatic/plan/图片的 picture lock。", "制片/picture_lock.json"))
    if os.path.exists(os.path.join(root, "成片_MV.mp4")):
        report_summary(findings, root, "生产数据/delivery_qc/delivery_qc.json", "delivery", "delivery_qc", "block")
        if not isinstance(load_json(os.path.join(root, "合规", "provenance.json")), dict):
            findings.append(finding("block", "provenance", "provenance_missing", "成片缺全链路 provenance。", "合规/provenance.json"))
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
            "生产数据/shot_variety/shot_variety.json",
            "生产数据/image_qc/image_qc.json",
            "生产数据/video_inherit_contract/inherit_contract.json",
            "生产数据/video_qc/video_qc.json",
            "字幕/alignment_report.json",
            "生产数据/production_events.jsonl",
            "出视频/jobs_manifest.json",
            "制片/picture_lock.json",
            "生产数据/delivery_qc/delivery_qc.json",
            "合规/provenance.json",
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
