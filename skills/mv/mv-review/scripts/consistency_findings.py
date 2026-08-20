#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aggregate MV visual/timing consistency evidence into one findings file."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Iterable


KIND = "mv_consistency_findings"
SEVERITIES = ("block", "warn", "info")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
ALIGNMENT_PATH = os.path.join(REPO, "skills", "mv", "mv-lyric-sync", "scripts", "align.py")
IMAGE_RECEIPTS_PATH = os.path.join(REPO, "skills", "mv", "mv-image", "scripts", "image_receipts.py")
_ALIGNMENT_MODULE = None
_IMAGE_RECEIPTS_MODULE = None


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_alignment_module():
    global _ALIGNMENT_MODULE
    if _ALIGNMENT_MODULE is None:
        _ALIGNMENT_MODULE = _load_module("mv_findings_alignment_schema", ALIGNMENT_PATH)
    return _ALIGNMENT_MODULE


def _load_image_receipts():
    global _IMAGE_RECEIPTS_MODULE
    if _IMAGE_RECEIPTS_MODULE is None:
        _IMAGE_RECEIPTS_MODULE = _load_module("mv_findings_image_receipts", IMAGE_RECEIPTS_PATH)
    return _IMAGE_RECEIPTS_MODULE


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


def image_qc(findings: list[dict[str, Any]], root: str) -> None:
    rel = "生产数据/image_qc/image_qc.json"
    ledger_rel = "生产数据/image_acceptance/image_acceptance.json"
    report = load_json(os.path.join(root, rel))
    if not isinstance(report, dict):
        sev = "block" if has_clip_plan(root) else "info"
        findings.append(finding(sev, "visual_identity", "image_qc_missing",
                                "缺当前 mv_image_qc 聚合报告；B14 不接受降级人工替代。", rel))
        return
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    hard = int(summary.get("hard_blocks") or 0)
    advisory = int(summary.get("advisory") or summary.get("warnings") or 0)
    if hard:
        findings.append(finding("block", "visual_identity", "image_qc_block", f"image_qc hard_blocks={hard}。", rel, "image_qc"))
    if advisory:
        findings.append(finding("warn", "visual_identity", "image_qc_warn", f"image_qc advisory={advisory}，需并排复核。", rel, "image_qc"))
    version = report.get("version", report.get("schema_version"))
    try:
        current_version = not isinstance(version, bool) and int(version) >= 3
    except (TypeError, ValueError):
        current_version = False
    if report.get("kind") != "mv_image_qc" or not current_version:
        findings.append(finding("block", "visual_identity", "image_qc_schema",
                                "image_qc 必须是当前 mv_image_qc v3+ 聚合报告。", rel, "image_qc"))
    env = report.get("qc_environment") if isinstance(report.get("qc_environment"), dict) else {}
    precision = str(env.get("precision_level") or "").strip()
    if precision != "full":
        findings.append(finding("block", "visual_identity", "image_qc_precision",
                                f"image_qc 精度为 {precision or 'missing'}；degraded/manual_review/--accept-degraded 均不能放行 B14。", rel))
    if hard != 0 or summary.get("verdict") != "ok":
        findings.append(finding("block", "visual_identity", "image_qc_not_ok",
                                f"image_qc 必须 hard_blocks=0 且 verdict=ok，当前 verdict={summary.get('verdict')!r}。", rel))
    assets_sha = report.get("assets_sha256") or {}
    if not isinstance(assets_sha, dict) or not assets_sha:
        findings.append(finding("block", "visual_identity", "image_qc_assets_missing",
                                "image_qc 缺 assets_sha256，不能证明检查的是当前像素。", rel))
        assets_sha = {}
    stale_assets = [asset for asset, digest in assets_sha.items()
                    if load_file_hash(os.path.join(root, str(asset))) != digest]
    if stale_assets:
        findings.append(finding("block", "visual_identity", "image_qc_assets_stale",
                                f"image_qc 当前像素绑定已过期：{stale_assets[0]}。", rel))
    provenance = report.get("generation_provenance") or {}
    if provenance.get("complete") is not True or (provenance.get("summary") or {}).get("block") != 0:
        findings.append(finding("block", "visual_identity", "image_generation_receipts_incomplete",
                                "image_qc generation_provenance 必须 complete 且 block=0。", rel))

    ledger = load_json(os.path.join(root, ledger_rel))
    if not isinstance(ledger, dict) or ledger.get("kind") != "mv_image_acceptance_ledger":
        findings.append(finding("block", "visual_identity", "image_acceptance_missing",
                                "缺权威 image_acceptance ledger；旧 image_qc/manual_review 不能证明逐图验收。", ledger_rel))
        return
    try:
        audit = _load_image_receipts().audit_ledger(Path(root), ledger=ledger)
    except Exception as exc:
        findings.append(finding("block", "visual_identity", "image_acceptance_invalid",
                                f"image_acceptance ledger 无法按当前像素复算：{exc}。", ledger_rel))
        return
    audit_summary = audit.get("summary") or {}
    rows = audit.get("rows") or []
    if audit_summary.get("all_current_accepted") is not True:
        findings.append(finding("block", "visual_identity", "image_acceptance_incomplete",
                                f"B14 未完成：accepted={audit_summary.get('accepted', 0)}/{audit_summary.get('expected', 0)}，"
                                f"stale={audit_summary.get('stale', 0)}。", ledger_rel, "image_acceptance"))
    invalid_rows = [row for row in rows if row.get("status") != "accepted"]
    if invalid_rows:
        row = invalid_rows[0]
        findings.append(finding("block", "visual_identity", "image_acceptance_stale",
                                f"逐图验收失效：{row.get('asset')}（{','.join(str(x) for x in row.get('findings') or []) or 'unknown'}）。",
                                ledger_rel, "image_acceptance"))
    audited_assets = {str(row.get("asset")) for row in rows if row.get("asset")}
    if set(map(str, assets_sha)) != audited_assets:
        findings.append(finding("block", "visual_identity", "image_acceptance_scope_mismatch",
                                "image_qc 资产全集与 image_acceptance 动态审计全集不一致。", ledger_rel))
    if (not hard and not advisory and precision == "full" and summary.get("verdict") == "ok"
            and audit_summary.get("all_current_accepted") is True
            and set(map(str, assets_sha)) == audited_assets and not stale_assets):
        findings.append(finding("info", "visual_identity", "image_qc_clean",
                                f"B14 当前像素逐图验收有效：{audit_summary.get('accepted', 0)}/{audit_summary.get('expected', 0)}。",
                                ledger_rel, "image_acceptance"))


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
    if not isinstance(report, dict):
        meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
        formal = not meta.get("is_demo")
        required = False
        if formal:
            try:
                runtime = _load_alignment_module().mv_gate._runtime_state(root)
                required = bool(
                    runtime.get("subtitle_language") != "无字幕"
                    or runtime.get("lip_sync_mode") != "关闭"
                )
            except Exception:
                # A formal project with subtitle outputs is still fail-closed
                # even if the shared runtime adapter itself cannot be loaded.
                required = bool(
                    os.path.exists(os.path.join(root, "字幕", "lyrics.lrc"))
                    or os.path.exists(os.path.join(root, "字幕", "karaoke.ass"))
                )
        if required:
            findings.append(finding(
                "block", "lyric_timeline", "alignment_missing",
                "正式字幕/演唱口型缺当前 schema v5 alignment_report，不能进入正式验收。",
                "字幕/alignment_report.json", "alignment_report",
            ))
        return
    if isinstance(report, dict):
        errors = []
        if report.get("kind") != "mv_lyric_alignment_report" or report.get("schema_version") != 5:
            errors.append("alignment_report 必须是当前 schema v5 mv_lyric_alignment_report")
        if "alignment_confidence" in report:
            errors.append("schema v5 禁止 alignment_confidence；character_coverage_ratio 只表示文本覆盖")
        if report.get("coverage_metric") != "text_character_mapping_ratio_not_acoustic_confidence":
            errors.append("schema v5 必须明确字符覆盖率不是声学置信度")
        acceptance = report.get("acceptance") or {}
        if acceptance.get("status") != "accepted" or acceptance.get("accepted") is not True:
            errors.append("alignment_report 尚未正式接受；pending/旧报告不能进入正式验收")
        try:
            alignment = _load_alignment_module()
            errors.extend(alignment.acceptance_errors(root, report))
            gate = alignment.mv_gate
            if report.get("alignment_unit") != "character":
                errors.append("alignment_report 不是字符级强制对齐")
            errors.extend(gate._alignment_stem_timing_errors(root, report))
            expected_binding = gate._alignment_acceptance_binding(root, report)
            if acceptance.get("binding") != expected_binding:
                errors.append("alignment_report 尚未以当前 master/stem/lyrics/ASS/LRC/report binding 正式接受")
            route = acceptance.get("route")
            if route == "singing_acoustic_evidence":
                lyric_lines = report.get("lyric_lines")
                if isinstance(lyric_lines, bool) or not isinstance(lyric_lines, int):
                    lyric_lines = 0
                if not gate._alignment_acoustic_valid(report, expected_binding, lyric_lines):
                    errors.append("singing acoustic evidence 未校准、非 singing-specific、不可正式验收、"
                                  "未逐行覆盖或未绑定当前 inputs/outputs")
            elif route == "named_listening_review":
                manual = report.get("manual_review") or {}
                manual_current = bool(
                    manual.get("accepted") is True
                    and manual.get("kind") == "named_full_listening_review"
                    and manual.get("verdict") == "pass"
                    and gate._valid_named_reviewer(manual.get("reviewer"))
                    and str(manual.get("notes") or "").strip()
                    and manual.get("bound_inputs_sha256") == report.get("inputs_sha256")
                    and manual.get("bound_outputs_sha256") == report.get("outputs_sha256")
                    and manual.get("binding") == expected_binding
                    and manual.get("bound_report_preaccept_sha256")
                    == expected_binding.get("report_preaccept_content_sha256")
                )
                if not manual_current:
                    errors.append("具名逐行 listening review 未绑定当前 inputs/outputs/report 前置内容")
        except Exception as exc:
            errors.append(f"schema v5 验收复算失败：{exc}")
        for index, message in enumerate(dict.fromkeys(str(item) for item in errors if str(item).strip())):
            code = "alignment_invalid" if index else "alignment_not_accepted"
            findings.append(finding("block", "lyric_timeline", code,
                                    message, "字幕/alignment_report.json", "alignment_report"))
        warnings = report.get("warnings") or []
        if warnings:
            findings.append(finding("warn", "lyric_timeline", "alignment_warn",
                                    f"字幕对齐报告有 {len(warnings)} 条 warning。", "字幕/alignment_report.json",
                                    "alignment_report", {"warnings": warnings[:10]}))
        if not warnings and not errors:
            coverage = report.get("character_coverage_ratio")
            findings.append(finding("info", "lyric_timeline", "alignment_clean",
                                    f"schema v5 正式验收有效；character_coverage_ratio={coverage} 仅表示文本字符映射覆盖率。",
                                    "字幕/alignment_report.json"))


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


def craft_audit(findings: list[dict[str, Any]], root: str) -> None:
    """传统 MV 手法机检（advisory）——副歌升级/动静对比/hook 上脸/冷开场/关键镜候选/bridge 换气。"""
    if not has_clip_plan(root):
        return
    rel = "生产数据/craft_audit/craft_audit.json"
    report = load_json(os.path.join(root, rel))
    if not isinstance(report, dict):
        findings.append(finding("info", "craft", "craft_audit_missing",
                                "未跑传统手法机检（craft_audit）；出图前建议补跑。", rel))
        return
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    warn = int(summary.get("warn") or 0)
    if warn:
        codes = sorted({str(f.get("code")) for f in (report.get("findings") or [])
                        if f.get("severity") == "warn"})
        findings.append(finding("warn", "craft", "craft_audit_warn",
                                f"传统手法 advisory={warn}（{'/'.join(codes) or 'n/a'}），回 mv-plan 调结构。",
                                rel, "craft_audit"))
    else:
        findings.append(finding("info", "craft", "craft_audit_clean", "传统手法机检无结构律违反项。", rel))


def drift_risk(findings: list[dict[str, Any]], root: str) -> None:
    """出图前漂移风险预测（advisory）——high 风险 clip 出图前应挂参考锚并优先打样。"""
    if not has_clip_plan(root):
        return
    rel = "生产数据/drift_risk/drift_risk.json"
    report = load_json(os.path.join(root, rel))
    if not isinstance(report, dict):
        findings.append(finding("info", "drift_risk", "drift_risk_missing",
                                "未跑出图前漂移风险预测（drift_risk）；出图前建议补跑。", rel))
        return
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    high = int(summary.get("high") or 0)
    measured = int(summary.get("measured_backfilled") or 0)
    if high:
        findings.append(finding("warn", "drift_risk", "drift_risk_high",
                                f"漂移风险 high={high}（实测回灌 {measured}），出图前给这些 clip 挂定妆/表情/场景参考。",
                                rel, "drift_risk"))
    else:
        findings.append(finding("info", "drift_risk", "drift_risk_clean", "漂移风险预测无 high 风险 clip。", rel))


# ── fail-closed 覆盖账本：现实验证器 适用 × 真跑过 ─────────────────────────────
# 治「跑了数据却没真执行一致性」：脸检(insightface)/构图 dHash(Pillow)/视频脸检 都是
# 后端缺失时优雅降级成 advisory 的现实验证器——真实出片机器上依赖常常没装，最强的
# 检测器全程休眠，报告却看着「跑过 QC」。此账本显式声明每个验证器是否适用（项目登记了
# 要查的数据）+ 是否真跑过（后端真出活），适用但休眠 → warn 现形（正式项目的 image 脸检
# 休眠已由 gate 的 precision!=full 硬拦，本层不重复造 block）。

def _verifier_rows(root: str) -> list[dict[str, Any]]:
    """逐验证器状态（纯函数化 I/O 汇总）：{key,label,applicable,ran_fresh,dormant,evidence}。"""
    image_qc_report = load_json(os.path.join(root, "生产数据/image_qc/image_qc.json"), {}) or {}
    video_qc_report = load_json(os.path.join(root, "生产数据/video_qc/video_qc.json"), {}) or {}
    registry = load_json(os.path.join(root, "设定/identity_registry.json"))
    has_plan = has_clip_plan(root)
    has_identity = isinstance(registry, dict) and bool(registry.get("lead_id"))
    has_image_qc = bool(image_qc_report)
    has_video_qc = bool(video_qc_report)

    face = ((image_qc_report.get("checks") or {}).get("face") or {})
    palette = ((image_qc_report.get("checks") or {}).get("palette") or {})
    variety = image_qc_report.get("shot_variety") or {}
    v_summary = video_qc_report.get("summary") or {}

    rows = [
        {"key": "image_face", "label": "出图主角脸检(insightface)",
         "applicable": has_plan and has_identity and has_image_qc,
         "ran_fresh": face.get("mode") == "insightface" and bool(face.get("available")),
         "evidence": f"mode={face.get('mode') or 'none'}",
         "producer": "mv-image/scripts/image_qc.py"},
        {"key": "image_palette", "label": "主色锚 palette(Pillow)",
         "applicable": has_image_qc and bool(palette),
         "ran_fresh": bool(palette.get("available")),
         "evidence": f"available={palette.get('available')}",
         "producer": "mv-image/scripts/image_qc.py"},
        {"key": "image_composition_dhash", "label": "出图构图重复 dHash(Pillow)",
         "applicable": has_image_qc and bool(variety),
         "ran_fresh": bool(variety.get("available")),
         "evidence": f"available={variety.get('available')}",
         "producer": "mv-image/scripts/image_qc.py"},
        {"key": "video_face", "label": "视频脸身份漂移(insightface)",
         "applicable": has_video_qc and has_identity,
         "ran_fresh": v_summary.get("face_identity_mode") == "insightface",
         "evidence": f"face_identity_mode={v_summary.get('face_identity_mode') or 'none'}",
         "producer": "mv-video/scripts/video_qc.py"},
        {"key": "video_frame_perception", "label": "视频首中尾抽帧感知(ffmpeg+Pillow)",
         "applicable": has_video_qc,
         "ran_fresh": int(v_summary.get("frame_samples") or 0) > 0,
         "evidence": f"frame_samples={v_summary.get('frame_samples') or 0}",
         "producer": "mv-video/scripts/video_qc.py"},
    ]
    for row in rows:
        row["dormant"] = bool(row["applicable"] and not row["ran_fresh"])
    return rows


def verifier_coverage(findings: list[dict[str, Any]], root: str) -> None:
    """现实验证器覆盖：适用但休眠（后端缺失/静默降级）→ warn，全部在岗 → info。"""
    rows = _verifier_rows(root)
    applicable = [r for r in rows if r["applicable"]]
    if not applicable:
        return
    dormant = [r for r in applicable if r["dormant"]]
    detail = {"rows": rows}
    if dormant:
        labels = "、".join(f"{r['label']}（{r['evidence']}）" for r in dormant)
        findings.append(finding("warn", "verifier_coverage", "reality_verifier_dormant",
                                f"{len(dormant)}/{len(applicable)} 个现实验证器适用但休眠：{labels}——"
                                "报告看着「跑过 QC」但最强检测器没真出活；补依赖重跑；若只能降级检测，"
                                "须具名记录局限，且不得据此签收正式阶段。",
                                "", "verifier_coverage", detail))
    else:
        findings.append(finding("info", "verifier_coverage", "reality_verifiers_active",
                                f"{len(applicable)} 个适用的现实验证器全部真跑过。", "", "verifier_coverage", detail))


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
    craft_audit(findings, root)
    drift_risk(findings, root)
    image_qc(findings, root)
    verifier_coverage(findings, root)
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
        "root_rel": ".",
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
            "生产数据/craft_audit/craft_audit.json",
            "生产数据/drift_risk/drift_risk.json",
            "生产数据/image_qc/image_qc.json",
            "生产数据/image_acceptance/image_acceptance.json",
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
        json_path, md_path = write_report(os.path.abspath(args.project_root), report)
        print(f"[ok] consistency findings JSON → {json_path}")
        print(f"[ok] consistency findings MD   → {md_path}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(report))
    return 1 if report["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
