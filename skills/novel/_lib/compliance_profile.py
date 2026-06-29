#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Platform/jurisdiction compliance profile for novel projects.

This module is intentionally deterministic. It does not decide legal questions;
it turns project intent, AI usage metadata, rights metadata, and current source
provenance into a checklist that export/localization gates can consume.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date
from typing import Any

from novel_contract import parse_regions
from project_io import load_project_settings


SCHEMA_VERSION = 1
KIND = "novel_compliance_profile"
PROFILE_REL = os.path.join("合规", "compliance_profile.json")
PROFILE_MD_REL = os.path.join("合规", "compliance_profile.md")

SOURCE_PROVENANCE = [
    {
        "id": "SRC-KDP-AI-20260623",
        "title": "Amazon KDP Content Guidelines - AI content",
        "url": "https://kdp.amazon.com/help/topic/G200672390",
        "accessed_at": "2026-06-23",
        "reliability": "official",
        "notes": "KDP requires disclosure of AI-generated text, images, or translations; AI-assisted content is not required to be disclosed.",
    },
    {
        "id": "SRC-KDP-IP-20260623",
        "title": "Amazon KDP Intellectual Property Rights FAQ",
        "url": "https://kdp.amazon.com/help/topic/G200672400",
        "accessed_at": "2026-06-23",
        "reliability": "official",
        "notes": "KDP requires the publisher to hold publishing rights for uploaded content.",
    },
    {
        "id": "SRC-CN-AI-LABEL-20260623",
        "title": "人工智能生成合成内容标识办法",
        "url": "https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm",
        "accessed_at": "2026-06-23",
        "reliability": "official",
        "notes": "AI-generated/synthetic content labeling rules implemented in 2025.",
    },
    {
        "id": "SRC-GB45438-20260623",
        "title": "GB 45438-2025 网络安全技术 人工智能生成合成内容标识方法",
        "url": "https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F32EA2A561F1886CD8D606513512D547",
        "accessed_at": "2026-06-23",
        "reliability": "official",
        "notes": "Mandatory national standard, published 2025-02-28 and implemented 2025-09-01.",
    },
    {
        "id": "SRC-EU-AI-ACT-20260623",
        "title": "EU Code of Practice on Transparency of AI-Generated Content",
        "url": "https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content",
        "accessed_at": "2026-06-23",
        "reliability": "official",
        "notes": "Supports AI Act Article 50 transparency obligations, applicable from 2026-08-02.",
    },
    {
        "id": "SRC-NRTA-MICRODRAMA-20260623",
        "title": "国家广播电视总局办公厅关于进一步统筹发展和安全促进网络微短剧行业健康繁荣发展的通知",
        "url": "https://www.nrta.gov.cn/art/2025/2/5/art_113_70148.html",
        "accessed_at": "2026-06-23",
        "reliability": "official",
        "notes": "Microdrama classified review, permit/record and platform responsibility requirements.",
    },
]

CN_TARGET_KEYS = ("中国", "大陆", "CN", "红果", "番茄", "抖音", "微短剧", "短剧", "漫剧")
KDP_TARGET_KEYS = ("KDP", "Kindle", "Amazon")
EU_TARGET_KEYS = ("EU", "欧盟", "Europe", "欧洲", "Germany", "France", "Spain", "Italy", "Netherlands", "德国", "法国", "西班牙", "意大利")
OUTBOUND_KEYS = ("出海", "海外", "本地化", "翻译", "YouTube", "TikTok", "KDP", "Kindle", "Amazon")
MICRODRAMA_KEYS = ("微短剧", "短剧", "漫剧", "红果", "抖音")


def today() -> str:
    return date.today().isoformat()


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_record(root: str, rel_path: str) -> dict[str, Any]:
    path = os.path.join(root, rel_path)
    record: dict[str, Any] = {"path": rel_path.replace(os.sep, "/"), "exists": os.path.exists(path)}
    if os.path.isfile(path):
        record.update({
            "sha256": _sha256_file(path),
            "size_bytes": os.path.getsize(path),
        })
    return record


def _records_hash(records: list[dict[str, Any]]) -> str:
    h = hashlib.sha256()
    for record in sorted(records, key=lambda item: item.get("path", "")):
        h.update(str(record.get("path") or "").encode("utf-8"))
        h.update(str(record.get("sha256") or "").encode("utf-8"))
    return h.hexdigest()


def _chapter_records(root: str) -> list[dict[str, Any]]:
    chdir = os.path.join(root, "章节")
    if not os.path.isdir(chdir):
        return []
    return [
        _file_record(root, os.path.join("章节", name))
        for name in sorted(os.listdir(chdir))
        if name.endswith(".md") and re.search(r"第0*\d+章", name)
    ]


def _export_records(root: str) -> list[dict[str, Any]]:
    out_dir = os.path.join(root, "导出")
    if not os.path.isdir(out_dir):
        return []
    return [
        _file_record(root, os.path.join("导出", name))
        for name in sorted(os.listdir(out_dir))
        if os.path.isfile(os.path.join(out_dir, name))
        and name not in {"release_manifest.json", "release_manifest.md"}
    ]


def profile_path(root: str) -> str:
    return os.path.join(root, PROFILE_REL)


def profile_md_path(root: str) -> str:
    return os.path.join(root, PROFILE_MD_REL)


def load_existing_profile(root: str) -> dict[str, Any]:
    payload = load_json(profile_path(root), {}) or {}
    return payload if isinstance(payload, dict) else {}


def load_confirmations(root: str) -> dict[str, Any]:
    payload = load_existing_profile(root)
    confirmations = payload.get("confirmations")
    return confirmations if isinstance(confirmations, dict) else {}


def _confirmation_text(confirmations: dict[str, Any], req_id: str) -> str:
    entry = confirmations.get(req_id)
    if not entry:
        return ""
    if isinstance(entry, dict):
        parts = []
        if entry.get("confirmed_at"):
            parts.append(f"confirmed_at={entry['confirmed_at']}")
        if entry.get("by"):
            parts.append(f"by={entry['by']}")
        if entry.get("note"):
            parts.append(f"note={entry['note']}")
        return "；".join(parts) or "confirmed"
    return "confirmed"


def _text_blob(meta: dict[str, Any], settings: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "draft_mode", "purpose", "target_platform", "target", "outputs",
        "target_distribution_regions", "distribution_regions", "target_language",
        "target_languages", "localization_targets",
    ):
        value = meta.get(key)
        if isinstance(value, list):
            parts.append(",".join(str(v) for v in value))
        else:
            parts.append(str(value or ""))
    for key in ("小说用途", "目标平台", "目标用途", "输出格式", "发行地区", "目标语言", "出海目标平台"):
        parts.append(str(settings.get(key) or ""))
    return " ".join(parts)


def _has_any(text: str, keys: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(key.lower() in lower for key in keys)


def _regions(meta: dict[str, Any], settings: dict[str, Any]) -> list[str]:
    values = [
        meta.get("target_distribution_regions"),
        meta.get("distribution_regions"),
        settings.get("发行地区"),
    ]
    out: list[str] = []
    for value in values:
        out.extend(r for r in parse_regions(value) if r != "UNSPECIFIED")
    return sorted(set(out))


def target_axes(meta: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    text = _text_blob(meta, settings)
    regions = _regions(meta, settings)
    region_text = " ".join(regions)
    return {
        "raw_target_text": text.strip(),
        "regions": regions,
        "kdp": _has_any(text, KDP_TARGET_KEYS),
        "china_public": _has_any(text + " " + region_text, CN_TARGET_KEYS) or any(r in {"CN", "CHN"} for r in regions),
        "eu": _has_any(text + " " + region_text, EU_TARGET_KEYS) or any(r in {"EU", "EEA", "DE", "FR", "ES", "IT", "NL"} for r in regions),
        "microdrama_cn": _has_any(text, MICRODRAMA_KEYS),
        "outbound": _has_any(text, OUTBOUND_KEYS) or bool(settings.get("目标语言") or settings.get("出海目标平台")),
    }


def ai_summary(root: str) -> dict[str, Any]:
    payload = load_json(os.path.join(root, "合规", "ai_usage.json"), {}) or {}
    if not isinstance(payload, dict):
        payload = {}
    return {
        "exists": bool(payload),
        "text_mode": payload.get("text_mode") or "unknown",
        "image_mode": payload.get("image_mode") or "unknown",
        "publish_target": payload.get("publish_target") or "",
        "human_contribution_present": bool(str(payload.get("human_contribution") or "").strip()),
        "disclosure_detail": payload.get("disclosure_detail") if isinstance(payload.get("disclosure_detail"), dict) else {},
    }


def input_fingerprint_components(root: str, meta: dict[str, Any], settings: dict[str, Any], ai: dict[str, Any]) -> dict[str, Any]:
    chapter_records = _chapter_records(root)
    export_records = _export_records(root)
    return {
        "meta": _file_record(root, "_meta.json"),
        "settings": _file_record(root, "_设置.md"),
        "ai_usage": _file_record(root, os.path.join("合规", "ai_usage.json")),
        "chapter_count": len(chapter_records),
        "chapter_aggregate_hash": _records_hash(chapter_records),
        "export_count": len(export_records),
        "export_aggregate_hash": _records_hash(export_records),
        "target_axes": target_axes(meta, settings),
        "ai_summary": ai,
    }


def _input_fingerprint(root: str, meta: dict[str, Any], settings: dict[str, Any], ai: dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update(json.dumps({
        "meta": meta,
        "settings": settings,
        "ai": ai,
        "components": input_fingerprint_components(root, meta, settings, ai),
        "sources": SOURCE_PROVENANCE,
    }, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    return h.hexdigest()


def _req(req_id: str, title: str, severity: str, status: str, reason: str, sources: list[str],
         confirmations: dict[str, Any] | None = None) -> dict[str, Any]:
    confirm_note = _confirmation_text(confirmations or {}, req_id)
    if confirm_note and status in {"missing", "action_required", "upcoming"}:
        status = "ok"
        reason = f"{reason}；本地确认：{confirm_note}"
    return {
        "id": req_id,
        "title": title,
        "severity": severity,
        "status": status,
        "reason": reason,
        "evidence_source_ids": sources,
    }


def build_profile(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    if not isinstance(meta, dict):
        meta = {}
    settings = load_project_settings(root)
    axes = target_axes(meta, settings)
    ai = ai_summary(root)
    confirmations = load_confirmations(root)
    rights_status = meta.get("rights_status") or "unknown"
    requirements: list[dict[str, Any]] = []

    if axes["kdp"]:
        if rights_status in {"unknown", "", None}:
            requirements.append(_req(
                "kdp_publishing_rights",
                "KDP publishing rights",
                "blocking",
                "missing",
                "KDP 上传前必须确认拥有发布权；当前 rights_status 未明确。",
                ["SRC-KDP-IP-20260623"],
                confirmations,
            ))
        else:
            requirements.append(_req(
                "kdp_publishing_rights",
                "KDP publishing rights",
                "blocking",
                "ok",
                f"rights_status={rights_status}",
                ["SRC-KDP-IP-20260623"],
                confirmations,
            ))
        if ai["text_mode"] == "AI-generated":
            requirements.append(_req(
                "kdp_ai_generated_disclosure",
                "KDP AI-generated disclosure",
                "blocking",
                "action_required",
                "KDP 发布/重发时须在 KDP UI 披露 AI-generated 文本/图片/翻译；本地 profile 只能提示，不能替你完成平台勾选。",
                ["SRC-KDP-AI-20260623"],
                confirmations,
            ))
        elif ai["text_mode"] == "AI-assisted":
            requirements.append(_req(
                "kdp_ai_assisted_note",
                "KDP AI-assisted note",
                "info",
                "ok",
                "KDP 当前不要求披露 AI-assisted 内容，但仍需确保权利和内容合规。",
                ["SRC-KDP-AI-20260623"],
                confirmations,
            ))

    if axes["china_public"]:
        if ai["text_mode"] in {"AI-generated", "AI-assisted"} or ai["image_mode"] in {"AI-generated", "AI-assisted"}:
            requirements.append(_req(
                "cn_ai_labeling_plan",
                "China AI content labeling plan",
                "blocking",
                "action_required",
                "面向中国公开发布的 AI 生成/辅助内容需准备显式标识、隐式元数据标识和留痕方案。",
                ["SRC-CN-AI-LABEL-20260623", "SRC-GB45438-20260623"],
                confirmations,
            ))
        else:
            requirements.append(_req(
                "cn_ai_labeling_plan",
                "China AI content labeling plan",
                "info",
                "not_applicable",
                "未检测到 AI-generated/AI-assisted 使用声明。",
                ["SRC-CN-AI-LABEL-20260623", "SRC-GB45438-20260623"],
                confirmations,
            ))

    if axes["eu"]:
        status = "upcoming" if today() < "2026-08-02" else "action_required"
        requirements.append(_req(
            "eu_ai_act_article_50",
            "EU AI Act Article 50 transparency",
            "warning" if status == "upcoming" else "blocking",
            status,
            "EU AI Act Article 50 透明度义务在 2026-08-02 起适用；面向欧盟受众的 AI 生成/操纵文本需按场景准备标识。",
            ["SRC-EU-AI-ACT-20260623"],
            confirmations,
        ))

    if axes["microdrama_cn"]:
        requirements.append(_req(
            "cn_microdrama_permit_or_record",
            "China microdrama permit/record reminder",
            "warning",
            "action_required",
            "小说侧只能预检；成片上线/引流前需按网络微短剧分层分类审核取得许可证或完成上线备案/登记并标注编号。",
            ["SRC-NRTA-MICRODRAMA-20260623"],
            confirmations,
        ))

    if axes["outbound"]:
        manifest_path = os.path.join(root, "出海", "manifest.json")
        manifest = load_json(manifest_path, {}) or {}
        if not isinstance(manifest, dict) or not manifest:
            requirements.append(_req(
                "outbound_manifest",
                "Localization/export manifest",
                "warning",
                "missing",
                "出海/本地化项目应写 出海/manifest.json，记录语言、平台、目标辖区、权利、AI 标识和署名元数据。",
                ["SRC-KDP-IP-20260623", "SRC-KDP-AI-20260623"],
                confirmations,
            ))
        else:
            requirements.append(_req(
                "outbound_manifest",
                "Localization/export manifest",
                "warning",
                "ok",
                "已检测到 出海/manifest.json。",
                ["SRC-KDP-IP-20260623", "SRC-KDP-AI-20260623"],
                confirmations,
            ))

    blockers = [r for r in requirements if r["severity"] == "blocking" and r["status"] in {"missing", "action_required"}]
    warnings = [r for r in requirements if r["severity"] == "warning" and r["status"] in {"missing", "action_required", "upcoming"}]
    fingerprint_components = input_fingerprint_components(root, meta, settings, ai)
    profile = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "generated_at": today(),
        "project_root": root,
        "input_fingerprint": _input_fingerprint(root, meta, settings, ai),
        "input_fingerprint_components": fingerprint_components,
        "target_axes": axes,
        "rights_status": rights_status,
        "ai_usage": ai,
        "confirmations": confirmations,
        "requirements": requirements,
        "blocking": len(blockers),
        "warning": len(warnings),
        "source_provenance": SOURCE_PROVENANCE,
    }
    return profile


def render_markdown(profile: dict[str, Any]) -> str:
    lines = [
        "# 合规 Profile",
        "",
        f"- 生成日期：{profile.get('generated_at')}",
        f"- 项目：{profile.get('project_root')}",
        f"- 阻断：{profile.get('blocking', 0)}",
        f"- 提醒：{profile.get('warning', 0)}",
        f"- input_fingerprint：`{profile.get('input_fingerprint') or ''}`",
        "",
        "## Target Axes",
        "",
    ]
    axes = profile.get("target_axes") or {}
    for key in ("kdp", "china_public", "eu", "microdrama_cn", "outbound"):
        lines.append(f"- {key}: {axes.get(key)}")
    if axes.get("regions"):
        lines.append("- regions: " + ", ".join(axes["regions"]))
    components = profile.get("input_fingerprint_components") or {}
    lines.extend([
        "",
        "## Input Fingerprint",
        "",
        f"- chapters: {components.get('chapter_count', 0)} `{components.get('chapter_aggregate_hash') or ''}`",
        f"- exports: {components.get('export_count', 0)} `{components.get('export_aggregate_hash') or ''}`",
        f"- ai_usage: `{(components.get('ai_usage') or {}).get('sha256') or ''}`",
    ])
    lines.extend([
        "",
        "## Requirements",
        "",
        "| id | severity | status | reason | sources |",
        "|---|---|---|---|---|",
    ])
    for req in profile.get("requirements") or []:
        reason = str(req.get("reason") or "").replace("|", "\\|")
        lines.append(
            f"| {req.get('id')} | {req.get('severity')} | {req.get('status')} | "
            f"{reason} | {', '.join(req.get('evidence_source_ids') or [])} |"
        )
    if not profile.get("requirements"):
        lines.append("| none | info | ok | 未命中平台/辖区专项合规要求 |  |")
    lines.extend([
        "",
        "## Source Provenance",
        "",
    ])
    for source in profile.get("source_provenance") or []:
        lines.append(f"- {source['id']}: {source['title']} ({source['url']})")
    return "\n".join(lines) + "\n"


def write_profile(root: str, profile: dict[str, Any] | None = None) -> tuple[str, str]:
    profile = profile or build_profile(root)
    json_path = profile_path(root)
    md_path = profile_md_path(root)
    write_json(json_path, profile)
    write_text(md_path, render_markdown(profile))
    return json_path, md_path


def gate_items(profile: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for req in profile.get("requirements") or []:
        status = req.get("status")
        if req.get("severity") == "blocking" and status in {"missing", "action_required"}:
            blockers.append(req)
        elif req.get("severity") == "warning" and status in {"missing", "action_required", "upcoming"}:
            warnings.append(req)
    return blockers, warnings
