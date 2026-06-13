#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Machine gate for paid/high-risk ad stages: image, video, compose.

This is the deterministic counterpart to the SKILL.md reminders. It blocks
missing brief compliance, upstream blockers, and final-compose hazards before
money or irreversible production work starts.
"""
import argparse
import json
import os
import sys

import contract


STAGES = ("image", "video", "compose")


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def finding(severity, code, msg, path=None):
    out = {"severity": severity, "code": code, "msg": msg}
    if path:
        out["path"] = path
    return out


def has_files(folder, suffixes):
    if not os.path.isdir(folder):
        return False
    for name in os.listdir(folder):
        if name.lower().endswith(suffixes):
            return True
    return False


def brief_findings(root):
    path = os.path.join(root, "需求", "brief.json")
    brief = load_json(path)
    if brief is None:
        return [finding("block", "brief_missing", "缺 需求/brief.json", path)]
    check = contract.brief_check(brief)
    out = []
    if check["missing_required"]:
        out.append(finding("block", "brief_required_missing",
                           "brief 必填最小集缺项：" + "、".join(check["missing_required"]), path))
    if check["missing_deferred"]:
        out.append(finding("block", "brief_deferred_missing",
                           "花钱 gate 前合规项缺项：" + "、".join(check["missing_deferred"]), path))
    return out


def ad_law_findings(root):
    path = os.path.join(root, "脚本", "广告法机检报告.json")
    report = load_json(path)
    if report is None:
        return [finding("block", "ad_law_report_missing", "缺广告法机检报告，请先跑 ad-script/ad_law_check.py", path)]
    blocks = int(((report.get("summary") or {}).get("block")) or 0)
    warns = int(((report.get("summary") or {}).get("warn")) or 0)
    out = []
    if blocks:
        out.append(finding("block", "ad_law_block", f"广告法机检仍有 block={blocks}", path))
    if warns:
        out.append(finding("warn", "ad_law_warn", f"广告法机检仍有 warn={warns}，需人工确认依据", path))
    return out


def storyboard_findings(root):
    out = []
    for rel in ("脚本/storyboard.json", "脚本/镜头时长.json"):
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            out.append(finding("block", "storyboard_missing", f"缺 {rel}", path))
    timing = load_json(os.path.join(root, "脚本", "镜头时长.json"), {}) or {}
    for item in timing.get("findings", []):
        if item.get("severity") == "block":
            out.append(finding("block", "storyboard_finalize_block", item.get("msg", "分镜定稿存在 block"),
                               os.path.join(root, "脚本", "镜头时长.json")))
    return out


def voice_findings(root, stage, allow_placeholder=False):
    path = os.path.join(root, "配音", "时长清单.json")
    manifest = load_json(path)
    if manifest is None:
        return [finding("block", "voice_manifest_missing", "缺 配音/时长清单.json", path)]
    if manifest.get("has_placeholder"):
        sev = "warn" if (allow_placeholder or stage in ("image", "video")) else "block"
        return [finding(sev, "voice_placeholder", "VO 仍是占位；正式成片前必须真 VO 复跑", path)]
    return []


def image_findings(root):
    folder = os.path.join(root, "出图", "分镜")
    if has_files(folder, (".png", ".jpg", ".jpeg", ".webp")):
        return []
    return [finding("block", "image_frames_missing", "缺逐镜首帧/尾帧图片", folder)]


def video_contract_findings(root):
    path = os.path.join(root, "出视频", "分镜", "contract_inheritance.json")
    report = load_json(path)
    if report is None:
        return [finding("block", "video_contract_missing", "缺契约继承机检报告，请先跑 inherit_contract.py", path)]
    blocks = int(((report.get("summary") or {}).get("block")) or 0)
    warns = int(((report.get("summary") or {}).get("warn")) or 0)
    out = []
    if blocks:
        out.append(finding("block", "video_contract_block", f"视频契约继承仍有 block={blocks}", path))
    if warns:
        out.append(finding("warn", "video_contract_warn", f"视频契约继承 warn={warns}，需人工确认", path))
    return out


def video_clip_findings(root):
    folder = os.path.join(root, "出视频", "分镜", "视频")
    if has_files(folder, (".mp4", ".mov", ".m4v")):
        return []
    return [finding("block", "video_clips_missing", "缺出视频 Clip 文件", folder)]


def compose_output_findings(root):
    path = os.path.join(root, "合成", "成片_主片.mp4")
    if os.path.isfile(path):
        return []
    return [finding("warn", "master_missing_before_compose", "尚未生成主片；compose gate 通过后执行合成", path)]


def run_gate(root, stage, allow_placeholder=False):
    root = os.path.abspath(root)
    if stage not in STAGES:
        raise ValueError(f"unknown gate stage: {stage}")
    findings = []
    findings.extend(brief_findings(root))
    findings.extend(ad_law_findings(root))
    findings.extend(storyboard_findings(root))
    findings.extend(voice_findings(root, stage, allow_placeholder))
    if stage in ("video", "compose"):
        findings.extend(image_findings(root))
    if stage == "video":
        findings.extend(video_contract_findings(root))
    if stage == "compose":
        findings.extend(video_contract_findings(root))
        findings.extend(video_clip_findings(root))
        findings.extend(compose_output_findings(root))
    summary = {
        "block": sum(1 for f in findings if f["severity"] == "block"),
        "warn": sum(1 for f in findings if f["severity"] == "warn"),
        "info": sum(1 for f in findings if f["severity"] == "info"),
    }
    return {"schema_version": 1, "kind": "ad_gate", "stage": stage, "project_root": root,
            "summary": summary, "findings": findings}


def main():
    ap = argparse.ArgumentParser(description="拍广告花钱/不可逆阶段 gate")
    ap.add_argument("project_root")
    ap.add_argument("--stage", required=True, choices=STAGES)
    ap.add_argument("--json", default=None)
    ap.add_argument("--allow-placeholder", action="store_true",
                    help="允许占位 VO 继续 demo；compose 默认不建议使用")
    args = ap.parse_args()
    payload = run_gate(args.project_root, args.stage, args.allow_placeholder)
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    b, w = payload["summary"]["block"], payload["summary"]["warn"]
    print(f"# ad gate stage={args.stage}  block={b}  warn={w}")
    for item in payload["findings"]:
        icon = "🔴" if item["severity"] == "block" else ("🟡" if item["severity"] == "warn" else "ℹ️")
        print(f"{icon} [{item['code']}] {item['msg']}")
    if b == 0:
        print("✅ gate 通过")
    sys.exit(1 if b else 0)


if __name__ == "__main__":
    main()
