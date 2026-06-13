#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M0 review for ad delivery: deterministic manifest checks before publishing."""
import argparse
import json
import os
import sys

_COMPOSE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ad-compose"))
if _COMPOSE not in sys.path:
    sys.path.insert(0, _COMPOSE)
import deliver  # noqa: E402


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


def review(root):
    root = os.path.abspath(root)
    findings = []

    master = os.path.join(root, "合成", "成片_主片.mp4")
    if not os.path.isfile(master):
        findings.append(finding("block", "master_missing", "缺主片 合成/成片_主片.mp4", master))

    ad_law = os.path.join(root, "脚本", "广告法机检报告.json")
    report = load_json(ad_law)
    if report is None:
        findings.append(finding("block", "ad_law_missing", "缺广告法机检报告", ad_law))
    else:
        blocks = int(((report.get("summary") or {}).get("block")) or 0)
        warns = int(((report.get("summary") or {}).get("warn")) or 0)
        if blocks:
            findings.append(finding("block", "ad_law_block", f"广告法机检仍有 block={blocks}", ad_law))
        if warns:
            findings.append(finding("warn", "ad_law_warn", f"广告法机检 warn={warns}，需人工确认依据", ad_law))

    voice = os.path.join(root, "配音", "时长清单.json")
    voice_manifest = load_json(voice)
    if voice_manifest is None:
        findings.append(finding("block", "voice_missing", "缺配音时长清单", voice))
    elif voice_manifest.get("has_placeholder"):
        findings.append(finding("block", "voice_placeholder", "VO 仍是占位，不能作为正式投放成片", voice))

    ai_usage = os.path.join(root, "合规", "ai_usage.json")
    usage = load_json(ai_usage)
    if usage is None:
        findings.append(finding("block", "ai_usage_missing", "缺 AI 使用/授权披露", ai_usage))
    else:
        wm = str(usage.get("watermark_status") or "").strip()
        if not wm or wm in ("未记录", "待补", "tbd", "TBD"):
            findings.append(finding("block", "watermark_unrecorded", "水印 / AI 标识状态未记录", ai_usage))

    progress = os.path.join(root, "_进度.md")
    if not os.path.isfile(progress):
        findings.append(finding("block", "progress_missing", "缺 _进度.md", progress))
    else:
        with open(progress, encoding="utf-8") as f:
            rows = deliver.parse_deliverables(f.read())
        master_rows = [r for r in rows if r["kind"] == "master"]
        if not master_rows:
            findings.append(finding("warn", "master_matrix_missing", "交付矩阵缺主片行", progress))
        else:
            row = master_rows[0]
            if "✅" not in row["status"] or not row["path"]:
                findings.append(finding("warn", "master_matrix_not_done",
                                        "主片文件存在后应回写交付矩阵状态/路径", progress))

    findings.extend([
        finding("info", "human_product_check", "人工复核：产品包装/logo/品牌色是否跨镜漂移"),
        finding("info", "human_subtitle_av_check", "人工复核：字幕、VO、音乐床、画面节奏是否同步"),
        finding("info", "human_safe_area_check", "人工复核：竖版/方版安全框内 logo/CTA/产品未被裁切"),
    ])
    summary = {
        "block": sum(1 for f in findings if f["severity"] == "block"),
        "warn": sum(1 for f in findings if f["severity"] == "warn"),
        "info": sum(1 for f in findings if f["severity"] == "info"),
    }
    return {"schema_version": 1, "kind": "ad_review_m0", "project_root": root,
            "summary": summary, "findings": findings}


def write_markdown(path, payload):
    lines = [
        "# ad-review M0",
        "",
        f"- block: {payload['summary']['block']}",
        f"- warn: {payload['summary']['warn']}",
        f"- info: {payload['summary']['info']}",
        "",
        "## Findings",
    ]
    for item in payload["findings"]:
        lines.append(f"- {item['severity'].upper()} [{item['code']}] {item['msg']}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description="拍广告 M0 质检/自审")
    ap.add_argument("project_root")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    payload = review(args.project_root)
    root = payload["project_root"]
    json_path = args.json or os.path.join(root, "合规", "ad_review_m0.json")
    md_path = os.path.splitext(json_path)[0] + ".md"
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    write_markdown(md_path, payload)
    print(f"# ad-review M0  block={payload['summary']['block']}  warn={payload['summary']['warn']}")
    for item in payload["findings"]:
        icon = "🔴" if item["severity"] == "block" else ("🟡" if item["severity"] == "warn" else "ℹ️")
        print(f"{icon} [{item['code']}] {item['msg']}")
    print(f"[ok] {json_path}")
    sys.exit(1 if payload["summary"]["block"] else 0)


if __name__ == "__main__":
    main()
