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


_PENDING_TOKENS = {"", "未记录", "待补", "待填写", "tbd", "未填", "未定"}


def _pending(value):
    return str(value or "").strip().lower() in _PENDING_TOKENS


def _filled(value):
    """brief 字段是否「填了真实内容」（非空且非占位）。"""
    if isinstance(value, str):
        return not _pending(value)
    if isinstance(value, (list, tuple)):
        return any(_filled(v) for v in value)
    if isinstance(value, dict):
        return any(_filled(v) for v in value.values())
    return value is not None


def _summary_block(report):
    """读报告 summary.block 整数；格式异常返回 None。"""
    summary = report.get("summary")
    if not isinstance(summary, dict):
        return None, None
    try:
        return int(summary.get("block") or 0), int(summary.get("warn") or 0)
    except (TypeError, ValueError):
        return None, None


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
    elif report.get("disabled"):
        findings.append(finding("warn", "ad_law_disabled",
                                f"广告法机检已关闭（region={report.get('region', '?')}）；仅限非中国大陆投放，需人工确认", ad_law))
    else:
        blocks, warns = _summary_block(report)
        if blocks is None:
            findings.append(finding("block", "ad_law_malformed", "广告法机检报告缺 summary.block 整数字段（格式异常）", ad_law))
        else:
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

    # AI 使用/授权披露：不仅查文件存在，还要查内容与 brief 授权信息不矛盾（空壳披露应拦）。
    ai_usage = os.path.join(root, "合规", "ai_usage.json")
    usage = load_json(ai_usage)
    if usage is None:
        findings.append(finding("block", "ai_usage_missing", "缺 AI 使用/授权披露", ai_usage))
    else:
        brief = load_json(os.path.join(root, "需求", "brief.json"), {}) or {}
        rights = brief.get("rights") if isinstance(brief.get("rights"), dict) else {}
        # 用了真人/代言人但披露里 talent_status 仍占位或写「未使用真人」= 矛盾，block。
        if _filled(rights.get("talent")):
            ts = usage.get("talent_status")
            if _pending(ts) or "未使用" in str(ts):
                findings.append(finding("block", "ai_usage_talent_unrecorded",
                                        f"brief 标注使用真人/代言人，但 AI 披露 talent_status={ts!r} 未留授权痕迹", ai_usage))
        if _filled(rights.get("music")):
            if _pending(usage.get("music_status")):
                findings.append(finding("block", "ai_usage_music_unrecorded",
                                        "brief 标注音乐授权，但 AI 披露 music_status 未记录", ai_usage))
        for fld, key in (("fonts", "asset_status"), ("assets", "asset_status")):
            if _filled(rights.get(fld)) and _pending(usage.get(key)):
                findings.append(finding("warn", "ai_usage_asset_unrecorded",
                                        f"brief 标注 {fld} 授权，但 AI 披露 {key} 未记录", ai_usage))
                break
        # 全空披露兜底：各项均占位且 brief 无任何授权信息 → 提示确认确无真人/授权素材。
        if not any(_filled(rights.get(k)) for k in ("talent", "music", "fonts", "assets")) and all(
            _pending(usage.get(k)) for k in ("talent_status", "music_status", "voice_status", "asset_status")
        ):
            findings.append(finding("warn", "ai_usage_all_unrecorded",
                                    "AI 披露各授权项均未记录，请确认确无真人/授权音乐/字体/素材", ai_usage))

    progress = os.path.join(root, "_进度.md")
    if not os.path.isfile(progress):
        findings.append(finding("block", "progress_missing", "缺 _进度.md", progress))
    else:
        with open(progress, encoding="utf-8") as f:
            rows = deliver.parse_deliverables(f.read())
        master_rows = [r for r in rows if r["kind"] == "master"]
        if not master_rows:
            findings.append(finding("warn", "master_matrix_missing", "交付矩阵缺主片行", progress))
        # 逐行核验交付矩阵：①标 ✅ 但文件缺失/路径空 = 假完成 block；②未产出的交付件 = warn。
        for row in rows:
            done = "✅" in row["status"]
            rel = (row.get("path") or "").strip()
            abspath = rel if os.path.isabs(rel) else os.path.join(root, rel)
            label = row.get("label") or row.get("deliverable_id") or row.get("kind")
            if done:
                if not rel or not os.path.isfile(abspath):
                    findings.append(finding("block", "deliverable_claimed_missing",
                                            f"交付件「{label}」标记完成但文件缺失/路径为空：{rel or '(空)'}", progress))
            else:
                findings.append(finding("warn", "deliverable_unrendered",
                                        f"交付件「{label}」尚未产出/回写（投放前需补齐或显式取消）", progress))

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
