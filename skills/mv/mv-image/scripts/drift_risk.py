#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mv-image 出图前·主角/物料漂移风险预测（report-only · 不读像素、不花钱）。

现状链路里，脸漂只有**出图之后**才被处理（image_qc 脸检 G1 → 崩了重抽）。本脚本把判断
前移到出图前：纯读 `分镜/clip_plan.json` + `设定/identity_registry.json`，用高危信号预测
哪些 clip 最容易漂——MV 是"单主角跨 16-64 个 clip"的脸一致性重灾区，参考锚该挂在哪、
哪几个镜先打样，应该在花积分前就知道（参照兄弟线 face_drift_risk 的"事后升档→事前预测"）。

逐 clip 风险信号（业界口径：近景放大漂移最刺眼；大表情让模型重画整张脸；逆光/暗部
遮脸导致自由发挥；换装/长间隔复现是重锚点；多主体同框易串脸；缺参考锚放大一切）：
  closeup / strong_emotion / extreme_angle / lighting_risk / multi_subject /
  state_change / state_reentry / new_location_no_reference / no_reference(放大器)
项目级基础分：主角定妆组 ready(≥3 张) → 0；partial → +14；缺 registry → +24。

**实测回灌**：若 生产数据/image_qc/image_qc.json 已有脸检结果，其中 warn/block 的 clip
直接升 high（既成事实，非预测）；本脚本自身仍恒退 0——硬拦截由 image_qc/gate 负责。

产物：`生产数据/drift_risk/drift_risk.{json,md}`。全部 advisory（最高 warn，永不 block）。
用法：python3 drift_risk.py <制MV作品根> [--write] [--json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from typing import Any
from datetime import date

VERSION = 1
KIND = "mv_drift_risk"
SEVERITIES = ("block", "warn", "info")


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


# 风险分层阈值（可 env 覆盖）。
HIGH_SCORE = _int_env("MV_DRIFT_HIGH_SCORE", 60)
MEDIUM_SCORE = _int_env("MV_DRIFT_MEDIUM_SCORE", 35)
# 同一 identity_state 缺席 ≥ 此 clip 数后再登场 = 长间隔复现（一致性随复现间隔衰退，重锚点）。
REENTRY_GAP = _int_env("MV_DRIFT_REENTRY_GAP", 6)

WEIGHTS = {
    "closeup": 28, "strong_emotion": 14, "extreme_angle": 12, "lighting_risk": 10,
    "multi_subject": 16, "state_change": 18, "state_reentry": 12,
    "new_location_no_reference": 10, "no_reference": 12,
    "base_ready": 0, "base_partial": 14, "base_missing": 24,
}

# 与 shot_variety_audit 同口径的宽松包含匹配（计划期人写/半自动文本）。mv 惯例：本线自留词表，不跨线 import。
CLOSEUP_RE = re.compile(r"大?特写|近景|closeup|close-?up|\bE?CU\b|\bMCU\b|\bBCU\b|face|脸部|面部|过肩|OTS|反打", re.IGNORECASE)
EXTREME_ANGLE_RE = re.compile(r"极端|俯冲|仰冲|顶视|正俯|大俯|大仰|荷兰角|dutch|bird.?eye|worm.?eye|extreme", re.IGNORECASE)
EMOTION_RE = re.compile(r"哭|泪|嘶吼|怒|吼|崩溃|狂喜|大笑|尖叫|颤抖|绝望|痛苦|挣扎|爆发|scream|cry|sob|rage|ecsta|anguish", re.IGNORECASE)
LIGHTING_RISK_RE = re.compile(r"逆光|剪影|暗部|黑暗|夜色|夜晚|背光|烛光|昏暗|silhouette|backlit|low.?key|dim", re.IGNORECASE)
MULTI_SUBJECT_RE = re.compile(r"同框|双人|二人|两人|群像|合唱|对视|对唱|伴舞|人群|路人|duet|crowd|group", re.IGNORECASE)


def _sha256(path: str) -> str:
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


def finding(severity: str, code: str, message: str, clips: list[str] | None = None) -> dict[str, Any]:
    return {
        "severity": severity if severity in SEVERITIES else "info",
        "code": code,
        "message": message,
        "clips": clips or [],
    }


def _norm(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _sd(clip: dict[str, Any]) -> dict[str, Any]:
    sd = clip.get("shot_design")
    return sd if isinstance(sd, dict) else {}


def _location_key(clip: dict[str, Any]) -> str:
    sd = _sd(clip)
    return _norm(sd.get("location_id") or sd.get("setup_group") or sd.get("location_name") or clip.get("section"))


def clip_blob(clip: dict[str, Any]) -> str:
    """clip 的可读文本拼接（desc/动作/表演/光影/歌词等），供正则宽松匹配。"""
    parts: list[str] = []
    for key in ("desc", "description", "action", "action_peak", "performance", "emotion",
                "visual_motif", "vocal_lyrics", "prompt_summary"):
        parts.append(str(clip.get(key) or ""))
    sd = _sd(clip)
    for key in ("shot_size", "angle", "camera_movement", "lens_feel", "lighting"):
        parts.append(str(sd.get(key) or ""))
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
    for value in cont.values():
        if isinstance(value, str):
            parts.append(value)
    return " ".join(p for p in parts if p)


def _reference_count(clip: dict[str, Any]) -> int:
    refs = clip.get("reference_inputs")
    return len(refs) if isinstance(refs, list) else 0


def _identity_state(clip: dict[str, Any]) -> str:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
    return _norm(cont.get("identity_state") or cont.get("wardrobe_state"))


def lead_base(registry: Any) -> tuple[int, str]:
    """项目级基础分：主角定妆组越弱，全体 clip 起点风险越高（与 gate _identity_readiness 同口径）。"""
    if not isinstance(registry, dict):
        return WEIGHTS["base_missing"], "identity_registry_missing"
    lead_id = registry.get("lead_id")
    lead = next((row for row in registry.get("identities") or []
                 if isinstance(row, dict) and row.get("id") == lead_id), None)
    if not isinstance(lead, dict):
        return WEIGHTS["base_missing"], "lead_identity_missing"
    groups = {g.get("id"): g for g in registry.get("reference_groups") or [] if isinstance(g, dict)}
    group = groups.get(lead.get("reference_group")) or {}
    paths = [p for p in group.get("paths") or [] if p]
    if group.get("status") == "ready" and len(paths) >= 3:
        return WEIGHTS["base_ready"], "lead_reference_ready"
    if paths:
        return WEIGHTS["base_partial"], "lead_reference_partial"
    return WEIGHTS["base_missing"], "lead_reference_planned"


def other_identity_names(registry: Any) -> list[str]:
    """非主角命名身份（配角/伴舞等）——同框即多主体串脸风险。"""
    if not isinstance(registry, dict):
        return []
    lead_id = registry.get("lead_id")
    names = []
    for row in registry.get("identities") or []:
        if isinstance(row, dict) and row.get("id") != lead_id:
            name = str(row.get("display_name") or "").strip()
            if name:
                names.append(name)
    return names


def score_clip(clip: dict[str, Any], prev_state: str, state_last_seen: dict[str, int],
               seen_locations: set[str], index: int, base: int,
               other_names: list[str]) -> dict[str, Any]:
    """单 clip 风险打分（纯函数）。返回 {clip_id, score, tier, signals}。"""
    blob = clip_blob(clip)
    sd = _sd(clip)
    signals: list[str] = []
    score = base

    if CLOSEUP_RE.search(str(sd.get("shot_size") or "") + " " + str(sd.get("lens_feel") or "")):
        signals.append("closeup")
    if EMOTION_RE.search(blob):
        signals.append("strong_emotion")
    if EXTREME_ANGLE_RE.search(str(sd.get("angle") or "") + " " + blob):
        signals.append("extreme_angle")
    if LIGHTING_RISK_RE.search(blob):
        signals.append("lighting_risk")
    if MULTI_SUBJECT_RE.search(blob) or any(name and name in blob for name in other_names):
        signals.append("multi_subject")

    state = _identity_state(clip)
    if state and prev_state and state != prev_state:
        signals.append("state_change")
    if state and state in state_last_seen and index - state_last_seen[state] >= REENTRY_GAP:
        signals.append("state_reentry")

    loc = _location_key(clip)
    if loc and loc not in seen_locations and index > 0 and _reference_count(clip) == 0:
        signals.append("new_location_no_reference")

    if signals and _reference_count(clip) == 0:
        signals.append("no_reference")

    score += sum(WEIGHTS.get(sig, 0) for sig in signals)
    tier = "high" if score >= HIGH_SCORE else ("medium" if score >= MEDIUM_SCORE else "low")
    return {"clip_id": str(clip.get("clip_id")), "score": score, "tier": tier, "signals": signals}


def measured_face_backfill(root: str) -> tuple[list[str], list[str], str]:
    """image_qc 实测回灌：已出图 clip 的脸检 warn/block → 升 high（既成事实，非预测）。

    返回 (warn_or_block_clip_ids, notes, face_mode)。无报告/降级模式不臆造。"""
    report = load_json(os.path.join(root, "生产数据", "image_qc", "image_qc.json"))
    if not isinstance(report, dict):
        return [], [], ""
    face = (report.get("checks") or {}).get("face") or {}
    mode = str(face.get("mode") or "")
    if mode != "insightface":
        note = ("image_qc 脸检非 insightface 模式（降级/跳过）——实测回灌不可用，"
                "本报告纯预测档；补依赖重跑 image_qc 后重跑本审计。") if face else ""
        return [], [note] if note else [], mode
    hits = sorted({str(row.get("clip")) for row in face.get("shots") or []
                   if isinstance(row, dict) and row.get("verdict") in ("warn", "block")})
    return hits, [], mode


def build_report(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    plan_rel = "分镜/clip_plan.json"
    registry_rel = "设定/identity_registry.json"
    plan_path = os.path.join(root, plan_rel)
    plan = load_json(plan_path)
    registry = load_json(os.path.join(root, registry_rel))
    findings: list[dict[str, Any]] = []
    notes: list[str] = []
    rows: list[dict[str, Any]] = []

    base, base_reason = lead_base(registry)
    other_names = other_identity_names(registry)

    if not isinstance(plan, dict):
        notes.append("缺 分镜/clip_plan.json——先跑 mv-plan 生成分镜后再做漂移风险预测。")
        clips: list[dict[str, Any]] = []
    else:
        clips = [c for c in (plan.get("clips") or []) if isinstance(c, dict)]
        if not clips:
            notes.append("clip_plan 里没有 clips。")

    prev_state = ""
    state_last_seen: dict[str, int] = {}
    seen_locations: set[str] = set()
    for index, clip in enumerate(clips):
        row = score_clip(clip, prev_state, state_last_seen, seen_locations, index, base, other_names)
        rows.append(row)
        state = _identity_state(clip)
        if state:
            state_last_seen[state] = index
            prev_state = state
        loc = _location_key(clip)
        if loc:
            seen_locations.add(loc)

    measured_hits, measured_notes, face_mode = measured_face_backfill(root)
    notes.extend(measured_notes)
    by_id = {row["clip_id"]: row for row in rows}
    backfilled = []
    for cid in measured_hits:
        row = by_id.get(cid)
        if row is not None and row["tier"] != "high":
            row["tier"] = "high"
            row["signals"] = list(row["signals"]) + ["measured_face_warn"]
            backfilled.append(cid)
        elif row is not None:
            row["signals"] = list(row["signals"]) + ["measured_face_warn"]
            backfilled.append(cid)

    high = [r for r in rows if r["tier"] == "high"]
    medium = [r for r in rows if r["tier"] == "medium"]

    if base >= WEIGHTS["base_partial"]:
        findings.append(finding("warn", "lead_reference_base_weak",
                                f"主角定妆参考基础薄弱（{base_reason}）——全体 clip 漂移起点风险抬高；"
                                "先补共享定妆（正面/侧脸/全身 ≥3 张）再批量出图，gate 在 video_jobs 期会硬拦"))
    if high:
        ids = [r["clip_id"] for r in high]
        top_signals = sorted({sig for r in high for sig in r["signals"]})
        head = "、".join(ids[:8]) + ("…" if len(ids) > 8 else "")
        findings.append(finding("warn", "high_drift_risk_clips",
                                f"{len(ids)} 个 clip 漂移风险 high（{head}；信号：{'/'.join(top_signals)}）——"
                                "出图前给这些 clip 挂定妆/表情/场景参考，后端有主体库先注册主体；"
                                "建议先跑 mv-plan pilot_matrix 打样这几类再全量出图", ids))
    if measured_hits:
        findings.append(finding("warn", "measured_face_drift_backfill",
                                f"image_qc 已实测出 {len(measured_hits)} 个 clip 脸检 warn/block（既成事实，非预测）："
                                f"{'、'.join(measured_hits[:8])}{'…' if len(measured_hits) > 8 else ''}——"
                                "重抽前先看这些镜的共性信号，别只换 seed 硬抽", measured_hits))
    if medium:
        findings.append(finding("info", "medium_drift_risk_clips",
                                f"{len(medium)} 个 clip 漂移风险 medium——批量出图时优先安排在定妆参考确认后",
                                [r["clip_id"] for r in medium]))
    if clips and not findings:
        findings.append(finding("info", "drift_risk_low",
                                "全部 clip 漂移风险 low——保持现有参考锚安排即可"))

    counts = {key: 0 for key in SEVERITIES}
    for item in findings:
        counts[item["severity"]] += 1
    return {
        "schema_version": VERSION,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "root_rel": ".",
        "engine": "mv-image/scripts/drift_risk.py",
        "inputs_sha256": {
            plan_rel: _sha256(plan_path),
            registry_rel: _sha256(os.path.join(root, registry_rel)),
        },
        "thresholds": {"high_score": HIGH_SCORE, "medium_score": MEDIUM_SCORE,
                       "reentry_gap": REENTRY_GAP, "weights": WEIGHTS},
        "lead_base": {"score": base, "reason": base_reason},
        "measured_face_mode": face_mode,
        "clips": rows,
        "summary": {
            **counts,
            "block": 0,  # 恒 0：本层永不制造 block；硬拦截由 image_qc/gate 负责
            "clips_checked": len(rows),
            "high": len(high),
            "medium": len(medium),
            "low": len(rows) - len(high) - len(medium),
            "measured_backfilled": len(backfilled),
            "verdict": "review" if counts["warn"] else "ok",
        },
        "findings": findings,
        "notes": notes,
    }


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# MV 漂移风险预测（出图前 · advisory）",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- clips_checked: {s.get('clips_checked')}   high: {s.get('high')}   medium: {s.get('medium')}   low: {s.get('low')}",
        f"- lead_base: {report.get('lead_base', {}).get('reason')}   verdict: {s.get('verdict')}",
        "",
        "## Findings",
        "",
    ]
    if not report.get("findings"):
        lines.append("- （无漂移风险项）")
    for item in report.get("findings") or []:
        clips = f"  · clips: {', '.join(item.get('clips') or [])}" if item.get("clips") else ""
        lines.append(f"- [{item.get('severity')}] {item.get('code')}: {item.get('message')}{clips}")
    high_rows = [r for r in report.get("clips") or [] if r.get("tier") == "high"]
    if high_rows:
        lines += ["", "## High 风险 clip 明细", ""]
        for row in high_rows:
            lines.append(f"- {row['clip_id']} · score={row['score']} · {'/'.join(row['signals']) or 'base'}")
    for note in report.get("notes") or []:
        lines.append(f"- [note] {note}")
    return "\n".join(lines).rstrip() + "\n"


def write_report(root: str, report: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "生产数据", "drift_risk")
    json_path = os.path.join(out_dir, "drift_risk.json")
    md_path = os.path.join(out_dir, "drift_risk.md")
    write_json(json_path, report)
    write_text(md_path, render_markdown(report))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="MV 出图前漂移风险预测（report-only）")
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true", help="落盘 生产数据/drift_risk/drift_risk.{json,md}")
    ap.add_argument("--json", action="store_true", help="打印机器可读 JSON")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{args.project_root}")
        return 2
    report = build_report(root)
    if args.write:
        json_path, md_path = write_report(root, report)
        print(f"[ok] drift risk JSON → {json_path}")
        print(f"[ok] drift risk MD   → {md_path}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(report))
    return 0  # report-only：永不因 finding 退非零


if __name__ == "__main__":
    raise SystemExit(main())
