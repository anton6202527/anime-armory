#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分镜定稿闸门（配音后回跑）：用 配音/时长清单.json 的实测 VO 时长对账 storyboard.json，
算每镜/总时长，校验是否贴合主片目标时长（如 30s），并标接缝缺尾帧。自包含纯标准库 + 单测。

广告与 n2d 同构：VO 实测时长驱动镜头时长；但广告**总时长是硬约束**（30s 就得 30s，超了投
不出去），所以这里多一条「总时长 vs 主片目标」对账，超/欠都报。

用法：
    python3 finalize_storyboard.py <作品根> --master 30s --json 脚本/镜头时长.json
"""
import argparse
import json
import os
import sys


def parse_seconds(label):
    """'30s'/'15'/'1:30' → float 秒。"""
    s = str(label).strip().lower().replace("s", "")
    if ":" in s:
        m, sec = s.split(":", 1)
        return int(m) * 60 + float(sec)
    return float(s)


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def vo_total(duration_list):
    """时长清单.json（[{时长:..}, ..] 或 {lines:[..]}）→ 总 VO 秒数 + 是否有占位。"""
    items = duration_list.get("lines", duration_list) if isinstance(duration_list, dict) else duration_list
    total, placeholder = 0.0, False
    for it in items or []:
        total += float(it.get("时长", it.get("duration", 0)) or 0)
        total += float(it.get("gap_after", 0) or 0)
        if it.get("占位") or it.get("placeholder"):
            placeholder = True
    return round(total, 3), placeholder


def shot_durations(storyboard):
    """storyboard.json → [(shot_id, duration)]。容忍 shots/clips 两种键。"""
    shots = storyboard.get("shots") or storyboard.get("clips") or []
    out = []
    for i, sh in enumerate(shots, 1):
        sid = sh.get("shot_id") or sh.get("clip_id") or f"镜头{i}"
        dur = float(sh.get("duration", sh.get("时长", 0)) or 0)
        out.append((sid, dur))
    return out


def fit_check(master_seconds, sb_total, vo_seconds, tol=0.5):
    """对账总时长。返回 findings 列表（block/warn）。"""
    findings = []
    if master_seconds and abs(sb_total - master_seconds) > tol:
        sev = "block" if abs(sb_total - master_seconds) > max(1.0, master_seconds * 0.1) else "warn"
        findings.append({
            "severity": sev, "kind": "master_duration_mismatch",
            "msg": f"分镜总时长 {sb_total:.2f}s ≠ 主片目标 {master_seconds:.0f}s（差 {sb_total - master_seconds:+.2f}s）",
        })
    if vo_seconds and sb_total + tol < vo_seconds:
        findings.append({
            "severity": "block", "kind": "vo_overflow",
            "msg": f"VO 实测 {vo_seconds:.2f}s 超过分镜总时长 {sb_total:.2f}s，旁白会被截断",
        })
    return findings


def seam_check(storyboard):
    """逐接缝查：标了 need_end_frame 但无尾帧约定 → warn。"""
    findings = []
    shots = storyboard.get("shots") or storyboard.get("clips") or []
    for i, sh in enumerate(shots, 1):
        cont = sh.get("continuity") or {}
        if cont.get("need_end_frame") and not cont.get("transition"):
            findings.append({"severity": "warn", "kind": "seam_missing_transition",
                             "msg": f"镜头{i} 标了需要尾帧但缺 transition 类型"})
    return findings


def main():
    ap = argparse.ArgumentParser(description="拍广告分镜定稿闸门（VO 时长 × 主片目标对账）")
    ap.add_argument("project_root")
    ap.add_argument("--master", default=None, help="主片目标时长，如 30s")
    ap.add_argument("--json", default=None, help="把镜头时长汇总写到该路径")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)

    sb = load_json(os.path.join(root, "脚本", "storyboard.json"), {})
    dl = load_json(os.path.join(root, "配音", "时长清单.json"), [])
    vo_sec, placeholder = vo_total(dl)
    shots = shot_durations(sb)
    sb_total = round(sum(d for _, d in shots), 3)
    master_sec = parse_seconds(args.master) if args.master else None

    findings = fit_check(master_sec, sb_total, vo_sec) + seam_check(sb)
    payload = {
        "schema_version": 1, "kind": "ad_storyboard_finalize",
        "master_seconds": master_sec, "storyboard_total": sb_total,
        "vo_seconds": vo_sec, "vo_placeholder": placeholder,
        "shots": [{"shot_id": s, "duration": d} for s, d in shots],
        "findings": findings,
    }
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"# 分镜定稿对账  分镜总时长={sb_total:.2f}s  VO={vo_sec:.2f}s"
          + (f"  主片目标={master_sec:.0f}s" if master_sec else "")
          + ("  ⏳占位VO" if placeholder else ""))
    for f in findings:
        print(("🔴" if f["severity"] == "block" else "🟡") + f" {f['msg']}")
    if not findings:
        print("✅ 时长对账通过")
    if placeholder:
        print("⚠️ VO 仍是占位（say 应急），正式定稿前需用真 VO 复跑（音画才准）")
    sys.exit(1 if any(f["severity"] == "block" for f in findings) else 0)


if __name__ == "__main__":
    main()
