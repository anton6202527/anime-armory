#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mv-review 视觉多样性 / 构图冗余 事前机检（report-only · 出图前跑，最便宜的点）。

MV 的命门是**卡点节奏**与**视觉不重复**。`mv-score`/`pacing.py` 已经把"卡点节奏"这条轴
（等长/downbeat 对齐/副歌密 verse 疏/总时长）做成确定性闸——但那套引擎**纯数值**，从不读任何
画面字段。于是"同一景别机位反复用""副歌镜头运镜静止""全曲挤在一个场景""大变化镜头没参考锚易漂"
这些**视觉单调**问题在出图/出视频花掉积分前无人拦。

本脚本把 n2d 的 `audit_shot_variety`（静态长镜/构图重复/景别单调）+ `redundancy_audit`
（构图计划重复）里**对 MV 适用的视觉信号**，前移到 `分镜/clip_plan.json` 的计划阶段（无需出图、
纯 stdlib）。MV 没有台词/旁白，故 n2d 的同义反复/旁白占比/事实复现三个文本信号**不适用、不移植**。

产物：`生产数据/shot_variety/shot_variety.{json,md}`。全部 advisory（最高 warn，永不 block）——
出图/出视频闸把它当 warning 抬进报告，绝不新增假阻断。

用法：
    python3 shot_variety_audit.py <制MV作品根> [--write] [--json]
退出码恒 0（report-only）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import date
from typing import Any

VERSION = 1
KIND = "mv_shot_variety_audit"
SEVERITIES = ("block", "warn", "info")

# —— 阈值（可按 env 覆盖，默认对齐 n2d/comic 的量级）——
def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default

def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default

# 同一 (场景,景别,机位,运镜) 计划在 ≥ 此 clip 数上出现 → 构图重复（n2d redundancy len≥2）。
DUP_MIN_CLIPS = _int_env("MV_DUP_MIN_CLIPS", 2)
# 一段连续同场景的 run 长度 ≥ 此值、且景别种类 < LENS_MIN_KINDS → 景别单调（n2d lens_variety RUN=5/KINDS=3）。
LENS_RUN_MIN = _int_env("MV_LENS_RUN_MIN", 5)
LENS_MIN_KINDS = _int_env("MV_LENS_MIN_KINDS", 3)
# 连续同场景 run ≥ 此值 → 场景滞留 warn。
LOCATION_RUN_WARN = _int_env("MV_LOCATION_RUN_WARN", 6)
# 单一场景覆盖 > 此比例的 clip → 场景单调 warn。
LOCATION_FRAC_WARN = _float_env("MV_LOCATION_FRAC_WARN", 0.6)
# 同一 视觉母题 / 转场母题 覆盖 > 此比例 → 母题过用 info。
MOTIF_FRAC_INFO = _float_env("MV_MOTIF_FRAC_INFO", 0.4)

# 判定用正则（值均为计划期人写/半自动文本，做宽松包含匹配）。
CHORUS_RE = re.compile(r"chorus|副歌|drop|hook|refrain|高潮|climax", re.IGNORECASE)
STATIC_RE = re.compile(r"固定|静止|锁定|定格|不动|无运镜|静帧|static|still|locked|hold|freeze", re.IGNORECASE)
HOLD_INTENT_RE = re.compile(r"留白|定格|空镜|静默|凝滞|hold|freeze", re.IGNORECASE)
CLOSEUP_RE = re.compile(r"大?特写|近景|closeup|close-?up|\bE?CU\b|face|脸部|面部", re.IGNORECASE)
EXTREME_ANGLE_RE = re.compile(r"极端|俯冲|仰冲|顶视|正俯|大俯|大仰|荷兰角|dutch|bird.?eye|worm.?eye|extreme", re.IGNORECASE)


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


def _sd(clip: dict[str, Any]) -> dict[str, Any]:
    sd = clip.get("shot_design")
    return sd if isinstance(sd, dict) else {}


def _norm(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _location_key(clip: dict[str, Any]) -> str:
    sd = _sd(clip)
    return _norm(sd.get("location_id") or sd.get("setup_group") or sd.get("location_name") or clip.get("section"))


def _is_chorusish(clip: dict[str, Any]) -> bool:
    if _norm(clip.get("beat_role")) == "key":
        return True
    return bool(CHORUS_RE.search(str(clip.get("section") or "")))


def _camera_text(clip: dict[str, Any]) -> str:
    sd = _sd(clip)
    return " ".join(str(sd.get(k) or "") for k in ("camera_movement", "lens_feel"))


def _reference_count(clip: dict[str, Any]) -> int:
    refs = clip.get("reference_inputs")
    return len(refs) if isinstance(refs, list) else 0


def audit_repeated_composition(clips: list[dict[str, Any]], findings: list[dict[str, Any]]) -> int:
    """同一 (场景,景别,机位,运镜) 反复计划 → 构图重复。副歌内 recurring hook 属有意 → 降 info。"""
    groups: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for clip in clips:
        sd = _sd(clip)
        sig = (
            _location_key(clip),
            _norm(sd.get("shot_size")),
            _norm(sd.get("angle")),
            _norm(sd.get("camera_movement")),
        )
        # 四要素全空的 clip 不参与（计划还没写实，不臆造重复）。
        if not any(sig):
            continue
        groups[sig].append(clip)
    hits = 0
    for sig, members in sorted(groups.items(), key=lambda kv: kv[0]):
        if len(members) < DUP_MIN_CLIPS:
            continue
        ids = [str(m.get("clip_id")) for m in members]
        sections = {str(m.get("section") or "") for m in members}
        all_chorus = all(_is_chorusish(m) for m in members)
        # 局限在副歌且是同一段的重复 = 很可能刻意的 hook 母题 → info；跨段/verse 内重复 = 单调 → warn。
        intentional = all_chorus and len(sections) <= 1
        sev = "info" if intentional else "warn"
        loc, size, angle, move = sig
        combo = "、".join(x for x in (size, angle, move, loc) if x) or "空构图"
        note = "（副歌 recurring hook，疑刻意；若非请换机位）" if intentional else "——出图前给其中几个换景别/机位/运镜，别一个构图撑全曲"
        findings.append(finding(sev, "repeated_composition_plan",
                                f"{'、'.join(ids)} 计划了相同构图 ({combo}){note}", ids))
        hits += 1
    return hits


def audit_lens_variety(clips: list[dict[str, Any]], findings: list[dict[str, Any]]) -> int:
    """连续同场景 run 内景别种类过少 → 景别单调（顺序遍历，遇换场 flush）。"""
    hits = 0

    def _flush(run: list[dict[str, Any]]) -> None:
        nonlocal hits
        if len(run) < LENS_RUN_MIN:
            return
        kinds = {_norm(_sd(c).get("shot_size")) for c in run if _norm(_sd(c).get("shot_size"))}
        if 0 < len(kinds) < LENS_MIN_KINDS:
            ids = [str(c.get("clip_id")) for c in run]
            findings.append(finding("warn", "lens_variety_low",
                                    f"{ids[0]}…{ids[-1]} 连续 {len(run)} 个 clip 同场景却只有 {len(kinds)} 种景别"
                                    f"（{'/'.join(sorted(kinds))}）——同一段落里推近/拉远/切中景，别一路平铺", ids))
            hits += 1

    run: list[dict[str, Any]] = []
    cur = None
    for clip in clips:
        loc = _location_key(clip)
        if cur is None or loc == cur:
            run.append(clip)
        else:
            _flush(run)
            run = [clip]
        cur = loc
    _flush(run)
    return hits


def audit_static_key_clip(clips: list[dict[str, Any]], findings: list[dict[str, Any]]) -> int:
    """副歌/爽点（key）镜头却计划静止运镜 → MV 命门（静态长镜的计划期等价物）。留白/空镜意图豁免。"""
    hits = 0
    for clip in clips:
        if not _is_chorusish(clip):
            continue
        cam = _camera_text(clip)
        motif = " ".join(str(clip.get(k) or "") for k in ("visual_motif", "transition_motif"))
        if STATIC_RE.search(cam) and not HOLD_INTENT_RE.search(cam + " " + motif):
            cid = str(clip.get("clip_id"))
            findings.append(finding("warn", "static_key_clip",
                                    f"{cid} 是副歌/爽点镜头却计划静止运镜（{_norm(_sd(clip).get('camera_movement')) or cam.strip()}）"
                                    "——高潮该动：给推/摇/甩/变焦/环绕，或回 mv-plan 把这一拍让给动镜", [cid]))
            hits += 1
    return hits


def audit_location_monotony(clips: list[dict[str, Any]], findings: list[dict[str, Any]]) -> int:
    """连续同场景 run 过长，或单一场景覆盖过高比例 → 场景滞留/单调。"""
    hits = 0
    # 单一场景占比
    counts = Counter(_location_key(c) for c in clips if _location_key(c))
    total = sum(counts.values())
    if total:
        loc, n = counts.most_common(1)[0]
        if n / total > LOCATION_FRAC_WARN and len(counts) > 1:
            findings.append(finding("warn", "location_monotony",
                                    f"场景『{loc}』覆盖 {n}/{total}（{n/total:.0%}）个 clip——全曲视觉易疲劳；"
                                    "插不同场景/空镜/回忆闪/抽象画面换气"))
            hits += 1
    # 最长连续同场景 run
    longest = 0
    longest_ids: list[str] = []
    run: list[dict[str, Any]] = []
    cur = None
    for clip in clips:
        loc = _location_key(clip)
        if cur is None or loc == cur:
            run.append(clip)
        else:
            if len(run) > longest:
                longest, longest_ids = len(run), [str(c.get("clip_id")) for c in run]
            run = [clip]
        cur = loc
    if len(run) > longest:
        longest, longest_ids = len(run), [str(c.get("clip_id")) for c in run]
    if longest >= LOCATION_RUN_WARN and longest_ids:
        findings.append(finding("warn", "location_run_long",
                                f"{longest_ids[0]}…{longest_ids[-1]} 连续 {longest} 个 clip 不换场景——"
                                "MV 常靠切场景推进，考虑中途插一个不同空间的镜头", longest_ids))
        hits += 1
    return hits


def audit_motif_overuse(clips: list[dict[str, Any]], findings: list[dict[str, Any]]) -> int:
    """视觉母题 / 转场母题 重复率过高 → info（母题重复可能刻意，仅提示自检）。"""
    hits = 0
    total = len(clips)
    if not total:
        return 0
    for field, label in (("visual_motif", "视觉母题"), ("transition_motif", "转场母题")):
        counts = Counter(_norm(c.get(field)) for c in clips if _norm(c.get(field)))
        if not counts:
            continue
        value, n = counts.most_common(1)[0]
        if n / total > MOTIF_FRAC_INFO and n >= 3:
            findings.append(finding("info", "motif_overuse",
                                    f"{label}『{value}』出现在 {n}/{total}（{n/total:.0%}）个 clip——"
                                    "若非刻意的贯穿母题，换几个避免视觉套路"))
            hits += 1
    return hits


def audit_reference_gap(clips: list[dict[str, Any]], findings: list[dict[str, Any]]) -> int:
    """大变化镜头（近景/换装/极端角度）却没规划参考输入 → 跨 clip 一致性易漂（事前处方 · 参照 comic reference_planner 的升档信号）。"""
    hits = 0
    prev_state = None
    gap_ids: list[str] = []
    for clip in clips:
        sd = _sd(clip)
        cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
        ident = clip.get("identity_contract") if isinstance(clip.get("identity_contract"), dict) else {}
        state = _norm(cont.get("identity_state") or cont.get("wardrobe_state"))
        wardrobe_change = bool(prev_state is not None and state and state != prev_state)
        prev_state = state or prev_state
        big_change = (
            bool(CLOSEUP_RE.search(str(sd.get("shot_size") or "")))
            or bool(EXTREME_ANGLE_RE.search(str(sd.get("angle") or "")))
            or wardrobe_change
            or bool(_norm(ident.get("forbidden_drift")))
        )
        if big_change and _reference_count(clip) == 0:
            gap_ids.append(str(clip.get("clip_id")))
    if gap_ids:
        head = "、".join(gap_ids[:8]) + ("…" if len(gap_ids) > 8 else "")
        findings.append(finding("warn", "reference_gap",
                                f"{len(gap_ids)} 个大变化镜头（近景/极端角度/换装/有禁漂约束）没规划参考输入：{head}"
                                "——这些最容易崩脸/漂移，出图前按 mv-image『MV一致性增强』补参考图/后端主体库/LoRA", gap_ids))
        hits += 1
    return hits


def summary_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    out = {key: 0 for key in SEVERITIES}
    for item in items:
        sev = item.get("severity")
        if sev in out:
            out[sev] += 1
    return out


def build_report(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    plan_rel = "分镜/clip_plan.json"
    plan_path = os.path.join(root, plan_rel)
    plan = load_json(plan_path)
    findings: list[dict[str, Any]] = []
    notes: list[str] = []
    if not isinstance(plan, dict):
        notes.append("缺 分镜/clip_plan.json——先跑 mv-plan 生成分镜后再做视觉多样性机检。")
        clips: list[dict[str, Any]] = []
    else:
        clips = [c for c in (plan.get("clips") or []) if isinstance(c, dict)]
        if not clips:
            notes.append("clip_plan 里没有 clips。")
        else:
            audit_repeated_composition(clips, findings)
            audit_lens_variety(clips, findings)
            audit_static_key_clip(clips, findings)
            audit_location_monotony(clips, findings)
            audit_motif_overuse(clips, findings)
            audit_reference_gap(clips, findings)
    counts = summary_counts(findings)
    return {
        "schema_version": VERSION,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "engine": "mv-review/scripts/shot_variety_audit.py",
        "inputs_sha256": {plan_rel: _sha256(plan_path)},
        "thresholds": {
            "dup_min_clips": DUP_MIN_CLIPS,
            "lens_run_min": LENS_RUN_MIN,
            "lens_min_kinds": LENS_MIN_KINDS,
            "location_run_warn": LOCATION_RUN_WARN,
            "location_frac_warn": LOCATION_FRAC_WARN,
            "motif_frac_info": MOTIF_FRAC_INFO,
        },
        "summary": {
            **counts,
            "block": counts["block"],   # 恒 0：本层永不制造 block
            "warn": counts["warn"],
            "info": counts["info"],
            "clips_checked": len(clips),
            "verdict": "review" if counts["warn"] else "ok",
        },
        "findings": findings,
        "notes": notes,
    }


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# MV 视觉多样性 / 构图冗余机检（事前 · advisory）",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- clips_checked: {s.get('clips_checked')}",
        f"- verdict: {s.get('verdict')}   warn: {s.get('warn')}   info: {s.get('info')}",
        "",
        "## Findings",
        "",
    ]
    if not report.get("findings"):
        lines.append("- （无视觉重复/单调项）")
    for item in report.get("findings") or []:
        clips = f"  · clips: {', '.join(item.get('clips') or [])}" if item.get("clips") else ""
        lines.append(f"- [{item.get('severity')}] {item.get('code')}: {item.get('message')}{clips}")
    for note in report.get("notes") or []:
        lines.append(f"- [note] {note}")
    return "\n".join(lines).rstrip() + "\n"


def write_report(root: str, report: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "生产数据", "shot_variety")
    json_path = os.path.join(out_dir, "shot_variety.json")
    md_path = os.path.join(out_dir, "shot_variety.md")
    write_json(json_path, report)
    write_text(md_path, render_markdown(report))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="MV 视觉多样性/构图冗余 事前机检（report-only）")
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true", help="落盘 生产数据/shot_variety/shot_variety.{json,md}")
    ap.add_argument("--json", action="store_true", help="打印机器可读 JSON")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.project_root):
        print(f"[err] 找不到作品根：{args.project_root}")
        return 2
    report = build_report(args.project_root)
    if args.write:
        json_path, md_path = write_report(report["project_root"], report)
        print(f"[ok] shot variety JSON → {json_path}")
        print(f"[ok] shot variety MD   → {md_path}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(report))
    return 0  # report-only：永不因 finding 退非零


if __name__ == "__main__":
    raise SystemExit(main())
