#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Novel-side platform compliance preflight for microdrama/manhua-drama source books."""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import date


MICRODRAMA_KEYS = ("微短剧", "短剧", "漫剧", "红果", "抖音")

REGULATORY_SOURCES = [
    {
        "title": "国家广播电视总局办公厅关于进一步加强网络微短剧管理实施创作提升计划有关工作的通知",
        "date": "2022-11-14",
        "url": "https://zh.wikisource.org/wiki/国家广播电视总局办公厅关于进一步加强网络微短剧管理实施创作提升计划有关工作的通知",
        "notes": ["先审后播", "许可证/备案", "内容审核", "片名关/内容关/审美关"],
    },
    {
        "title": "国家广播电视总局办公厅关于进一步统筹发展和安全促进网络微短剧行业健康繁荣发展的通知",
        "date": "2025-02-05",
        "url": "https://zh.wikisource.org/wiki/国家广播电视总局办公厅关于进一步统筹发展和安全促进网络微短剧行业健康繁荣发展的通知",
        "notes": ["分类分层审核", "白名单", "总编辑内容负责制", "备案号/许可证号"],
    },
    {
        "title": "广电总局：微短剧不得使用恶俗恶趣味片名",
        "date": "2024-12-21",
        "url": "https://www.news.cn/politics/20241221/0d5bf6a634124b03ae74e3ec849111de/c.html",
        "notes": ["片名提升思想/文化/审美内涵", "不渲染极端对立、复仇、暴戾、焦虑"],
    },
    {
        "title": "广电总局 AI 漫剧/微短剧备案新规：先备案后上线·投资额三级分层审核",
        "date": "2026-04-01",
        "url": "https://www.21jingji.com/article/20260410/herald/055ad9a327c3eed4dc4a0aa93f0863f2.html",
        "notes": ["先备案后上线，未备案存量下架", "投资额三级审核（≥300万/100-300万/<100万）",
                  "严禁颠覆性魔改经典作品与英雄/历史人物", "未授权真人肖像禁用",
                  "AI生成内容片头/显著位置标识"],
    },
]

TITLE_RISK_PATTERNS = [
    ("title_vulgar", r"贱|婊|绿茶|渣女|狗男人|废物|下贱|骚", "片名疑似恶俗/恶趣味或违背公序良俗。"),
    ("title_extreme_revenge", r"复仇|虐渣|血债|生不如死|灭门|杀疯|暴君", "片名渲染极端对立、复仇、暴戾或焦虑。"),
    ("title_overlong_colloquial", r".{24,}", "片名过长，微短剧片名预检建议更规整、关联剧情。"),
]

CONTENT_RISK_PATTERNS = [
    ("sexual_low", r"床戏|肉欲|露骨|下药|强奸|迷奸|裸露|色情|卖身", "色情低俗/性侵高风险表达。", "block"),
    ("bloody_violence", r"虐杀|碎尸|血肉模糊|剁碎|活埋|凌迟|酷刑", "血腥暴力高风险表达。", "block"),
    ("extreme_revenge", r"让.{0,12}生不如死|灭.{0,6}满门|血债血偿|杀光|复仇到底", "极端复仇/暴戾表达。", "warn"),
    ("money_worship", r"炫富|黑卡|千亿|百亿彩礼|拜金|物价贬值.*亿", "炫富拜金/浮躁悬浮风险。", "warn"),
    ("harmful_aesthetics", r"畸形审美|整容上瘾|以瘦为美|颜值即正义", "畸形审美或价值导向风险。", "warn"),
    ("minor_sensitive", r"未成年.{0,12}(恋爱|怀孕|性|包养)|学生.{0,8}包养", "未成年人敏感情节风险。", "block"),
    ("political_security", r"历史虚无|分裂国家|颠覆|恐怖主义|邪教", "政治安全/社会稳定/邪教风险。", "block"),
]


def load_json(path):
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_settings_text(root):
    path = os.path.join(root, "_设置.md")
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def project_text(root, max_chars=160000):
    parts = []
    for path in sorted(glob.glob(os.path.join(root, "章节", "第*.md"))):
        with open(path, encoding="utf-8") as f:
            parts.append(f.read())
    for rel in ("设定/章纲.md", "设定/创作蓝图.md"):
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                parts.append(f.read())
    return "\n".join(parts)[:max_chars]


def is_microdrama_project(meta, settings_text):
    haystack = " ".join(str(meta.get(k) or "") for k in (
        "purpose", "target_platform", "target", "draft_mode", "kind"
    ))
    haystack += "\n" + settings_text
    return any(key in haystack for key in MICRODRAMA_KEYS)


def _snippet(text, start, end, radius=28):
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return text[left:right].replace("\n", " ")


def finding(code, severity, field, message, snippet="", route="novel-review"):
    return {
        "code": code,
        "severity": severity,
        "field": field,
        "message": message,
        "snippet": snippet,
        "recommended_skill": route,
    }


def scan_title(title):
    findings = []
    for code, pattern, message in TITLE_RISK_PATTERNS:
        if re.search(pattern, title or ""):
            findings.append(finding(code, "warn", "title", message, title, route="novel-title"))
    return findings


def scan_content(text):
    findings = []
    for code, pattern, message, severity in CONTENT_RISK_PATTERNS:
        for match in re.finditer(pattern, text or ""):
            findings.append(finding(code, severity, "content", message, _snippet(text, match.start(), match.end())))
            break
    return findings


def metadata_findings(meta, settings_text, microdrama):
    findings = []
    if not microdrama:
        return findings
    if not str(meta.get("rights_status") or "").strip():
        findings.append(finding(
            "rights_status_missing",
            "warn",
            "metadata",
            "微短剧/漫剧源书上线前需权利链清晰；当前 _meta.json 缺 rights_status。",
        ))
    permit = " ".join(str(meta.get(k) or "") for k in ("microdrama_permit", "permit_no", "备案号", "license_no")).strip()
    if not permit and "备案号" not in settings_text and "许可证" not in settings_text:
        findings.append(finding(
            "microdrama_license_todo",
            "warn",
            "metadata",
            "微短剧上线/投流前须完成相应许可证或备案号流程；小说侧先记录为发布前待办。",
        ))
    return findings


def classic_ip_findings(meta, microdrama):
    """广电2026-04新规：严禁'颠覆性魔改经典作品与英雄/历史人物'+真人肖像须授权。

    只读 _meta 的**结构化字段**（不扫正文，符合 B10）：rights_status=='public-domain'（作者声明
    公版来源，强信号=老作品/经典/历史题材）或显式 _meta.classic_ip_adaptation 标记 → 该源书一旦
    改编成漫剧/微短剧，须按新规复核经典/历史/英雄人物形象与真人肖像授权。
    judgment call → 仅 warn（review·不硬阻断）；微短剧/漫剧目标才触发（纯小说不受此规）。"""
    findings = []
    if not microdrama:
        return findings
    rights = str(meta.get("rights_status") or "").strip().lower()
    flagged = bool(meta.get("classic_ip_adaptation")) or rights in ("public-domain", "public_domain")
    if flagged:
        findings.append(finding(
            "classic_ip_alteration_review",
            "warn",
            "metadata",
            "源书为公版/经典 IP 改编：改编成漫剧/微短剧前须按广电2026-04新规复核——不得颠覆性魔改"
            "经典作品或英雄/历史人物形象；涉真人肖像须取得授权；按投资额三级备案审核；AI生成内容"
            "片头/显著位置标识。小说侧先记录为发布前待办，并随交付契约把 classic_ip 标记传给改编环节。",
        ))
    return findings


def check(root):
    meta = load_json(os.path.join(root, "_meta.json"))
    settings_text = load_settings_text(root)
    title = str(meta.get("title") or meta.get("source_title") or os.path.basename(root))
    microdrama = is_microdrama_project(meta, settings_text)
    text = project_text(root)
    findings = []
    findings.extend(scan_title(title))
    findings.extend(scan_content(text))
    findings.extend(metadata_findings(meta, settings_text, microdrama))
    findings.extend(classic_ip_findings(meta, microdrama))
    blockers = [item for item in findings if item["severity"] == "block"]
    warnings = [item for item in findings if item["severity"] == "warn"]
    verdict = "pass"
    if blockers:
        verdict = "block"
    elif warnings:
        verdict = "review"
    return {
        "schema_version": 1,
        "kind": "novel_platform_compliance_preflight",
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "target_detected": "microdrama" if microdrama else "general_novel",
        "title": title,
        "verdict": verdict,
        "blocking_count": len(blockers),
        "warning_count": len(warnings),
        "findings": findings,
        "regulatory_sources": REGULATORY_SOURCES,
        "note": "确定性关键词预检只定位风险，不替代平台审核、法律意见或成片报审。",
    }


def write_artifacts(root, report):
    out_dir = os.path.join(root, "审稿")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "platform_compliance.json")
    md_path = os.path.join(out_dir, f"platform_compliance_{date.today().isoformat()}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 微短剧/平台合规预检 — {date.today().isoformat()}\n\n")
        f.write(f"- target_detected: {report['target_detected']}\n")
        f.write(f"- verdict: **{report['verdict']}**\n")
        f.write(f"- blockers/warnings: {report['blocking_count']} / {report['warning_count']}\n\n")
        f.write("## Findings\n\n")
        if not report["findings"]:
            f.write("- 未命中确定性风险词；仍需按目标平台最新规则复核。\n")
        for item in report["findings"]:
            f.write(f"- [{item['severity']}] {item['code']} ({item['field']}): {item['message']}\n")
            if item.get("snippet"):
                f.write(f"  - snippet: {item['snippet']}\n")
        f.write("\n## Sources\n\n")
        for src in report["regulatory_sources"]:
            f.write(f"- {src['date']} {src['title']}：{src['url']}\n")
    return json_path, md_path


def main():
    ap = argparse.ArgumentParser(description="微短剧/漫剧源书平台合规预检")
    ap.add_argument("project_root")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    report = check(root)
    json_path, md_path = write_artifacts(root, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[ok] platform compliance JSON → {json_path}")
        print(f"[ok] platform compliance MD   → {md_path}")
        print(f"     verdict: {report['verdict']} | block={report['blocking_count']} warn={report['warning_count']}")
    return 0 if report["verdict"] != "block" else 1


if __name__ == "__main__":
    raise SystemExit(main())
