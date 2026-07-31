#!/usr/bin/env python3
"""Validate locale-specific ad copy, media and approvals.

The locale matrix is a project-authored contract.  This module never invents
translations or legal copy: it can create a pending template, then validates
that every deliverable is mapped to a locale whose CTA, legal lines, voice,
subtitles, typography and translation review are explicit and queryable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Mapping


KIND = "ad_locale_matrix"
VALIDATION_KIND = "ad_locale_matrix_validation"
SCHEMA_VERSION = 1
PENDING = {"", "待补", "未定", "未记录", "tbd", "pending"}


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def sha(path: Path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pending(value: Any) -> bool:
    return str(value or "").strip().lower() in PENDING


def normalize_copy(value: Any):
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff%]+", "", text)


def evidence_exists(root: Path, value: Any) -> bool:
    ref = str(value or "").strip()
    if not ref:
        return False
    if ref.startswith(("https://", "http://", "record:")):
        return True
    path = Path(ref)
    if not path.is_absolute():
        path = root / path
    return path.is_file()


def evidence_digest(root: Path, row: Mapping[str, Any]):
    ref = str(row.get("evidence") or "").strip()
    if ref.startswith(("https://", "http://", "record:")):
        claimed = str(row.get("evidence_sha256") or "").strip().lower()
        return claimed if re.fullmatch(r"[0-9a-f]{64}", claimed) else None
    path = Path(ref)
    if ref and not path.is_absolute():
        path = root / path
    return sha(path) if ref else None


def _settings(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        raw = (root / "_设置.md").read_text(encoding="utf-8")
    except OSError:
        return out
    for line in raw.splitlines():
        stripped = line.strip().lstrip("-* ")
        for sep in (":", "："):
            if sep in stripped:
                key, value = stripped.split(sep, 1)
                out[key.strip()] = value.split("#", 1)[0].strip()
                break
    return out


def _default_locale(root: Path, brief: Mapping[str, Any]) -> str:
    explicit = str(brief.get("default_locale") or "").strip()
    if explicit:
        return explicit
    settings = _settings(root)
    language = settings.get("字幕语言") or "中文"
    region = str(brief.get("release_region") or settings.get("发行地区") or "中国大陆")
    if language == "仅英文" or region in {"北美", "全球"}:
        return "en-US"
    return "zh-CN"


def template(root: Path, deliverable_ids=None) -> dict[str, Any]:
    root = root.resolve()
    brief = load(root / "需求" / "brief.json", {}) or {}
    default = _default_locale(root, brief)
    mandatories = brief.get("mandatories") if isinstance(brief.get("mandatories"), Mapping) else {}
    legal = mandatories.get("legal_lines") or []
    if isinstance(legal, str):
        legal = [legal]
    cta = str(mandatories.get("endcard_cta") or mandatories.get("cta") or "待补")
    subtitle = "脚本/字幕_en.srt" if default.startswith("en") else "脚本/字幕_zh.srt"
    voice = "脚本/voiceover.txt"
    region = brief.get("release_regions") or brief.get("release_region") or _settings(root).get("发行地区") or "待补"
    jurisdictions = region if isinstance(region, list) else [region]
    ids = [str(v) for v in (deliverable_ids or ["master"]) if str(v)]
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "default_locale": default,
        "locales": {
            default: {
                "language": default,
                "jurisdictions": jurisdictions,
                "currency": "CNY" if default == "zh-CN" else "待补",
                "unit_system": "metric" if default == "zh-CN" else "待补",
                "cta": cta,
                "legal_lines": list(legal),
                "voiceover_path": voice,
                "subtitle_path": subtitle,
                "translation_review": {
                    "status": "source_language" if default == "zh-CN" else "pending",
                    "approved_by": "", "evidence": "",
                },
                "typography_review": {"status": "pending", "approved_by": "", "evidence": ""},
            }
        },
        "deliverable_locales": {did: [default] for did in ids},
    }


def _review_findings(root: Path, locale: str, name: str, row: Any, *, allow_source=False):
    findings = []
    row = row if isinstance(row, Mapping) else {}
    status = str(row.get("status") or "").strip().lower()
    allowed = {"approved"}
    if allow_source:
        allowed.add("source_language")
    if status not in allowed:
        findings.append({"severity": "block", "code": f"{name}_review_pending",
                         "msg": f"{locale} {name} review status={status or 'missing'}"})
        return findings
    if status == "approved":
        if pending(row.get("approved_by")):
            findings.append({"severity": "block", "code": f"{name}_reviewer_missing",
                             "msg": f"{locale} {name} review 缺 approved_by"})
        if not evidence_exists(root, row.get("evidence")) or evidence_digest(root, row) is None:
            findings.append({"severity": "block", "code": f"{name}_evidence_missing",
                             "msg": f"{locale} {name} review 证据不存在/不可查询；远程证据另需 evidence_sha256"})
    return findings


def validate(root: Path, matrix: Mapping[str, Any] | None = None,
             delivery_plan: Mapping[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve()
    path = root / "合规" / "locale_matrix.json"
    matrix = matrix if isinstance(matrix, Mapping) else load(path, {}) or {}
    delivery_plan = delivery_plan if isinstance(delivery_plan, Mapping) else load(root / "合成" / "delivery_plan.json", {}) or {}
    findings: list[dict[str, Any]] = []
    if not matrix:
        findings.append({"severity": "block", "code": "locale_matrix_missing", "msg": "缺 合规/locale_matrix.json"})
    if int(matrix.get("schema_version") or 0) != SCHEMA_VERSION:
        findings.append({"severity": "block", "code": "locale_matrix_schema", "msg": "locale matrix schema_version 不受支持"})
    locales = matrix.get("locales") if isinstance(matrix.get("locales"), Mapping) else {}
    mapping = matrix.get("deliverable_locales") if isinstance(matrix.get("deliverable_locales"), Mapping) else {}
    default = str(matrix.get("default_locale") or "").strip()
    if not default or default not in locales:
        findings.append({"severity": "block", "code": "default_locale_missing", "msg": "default_locale 未指向 locales 中的有效项"})
    normalized: dict[str, Any] = {}
    for locale, raw in locales.items():
        locale = str(locale)
        row = raw if isinstance(raw, Mapping) else {}
        missing = [key for key in ("language", "jurisdictions", "currency", "unit_system", "cta", "legal_lines",
                                   "voiceover_path", "subtitle_path") if pending(row.get(key)) or row.get(key) == []]
        if missing:
            findings.append({"severity": "block", "code": "locale_fields_missing",
                             "msg": f"{locale} 缺/占位：{', '.join(missing)}"})
        files = {}
        for key in ("voiceover_path", "subtitle_path"):
            ref = str(row.get(key) or "")
            target = root / ref if ref else Path()
            files[key] = {"path": ref, "sha256": sha(target) if ref else None}
            if ref and not target.is_file():
                findings.append({"severity": "block", "code": "locale_media_missing",
                                 "msg": f"{locale} {key} 文件不存在：{ref}"})
        translation = row.get("translation_review") if isinstance(row.get("translation_review"), Mapping) else {}
        typography = row.get("typography_review") if isinstance(row.get("typography_review"), Mapping) else {}
        findings.extend(_review_findings(root, locale, "translation", translation,
                                         allow_source=(locale == default)))
        findings.extend(_review_findings(root, locale, "typography", typography))
        normalized[locale] = {
            **dict(row), "language": str(row.get("language") or ""),
            "jurisdictions": list(row.get("jurisdictions") or []), "files": files,
            "translation_review": {**dict(translation), "evidence_sha256_actual": evidence_digest(root, translation)},
            "typography_review": {**dict(typography), "evidence_sha256_actual": evidence_digest(root, typography)},
        }
    brief = load(root / "需求" / "brief.json", {}) or {}
    mandatories = brief.get("mandatories") if isinstance(brief.get("mandatories"), Mapping) else {}
    source_cta = mandatories.get("endcard_cta") or mandatories.get("cta")
    source_legal = mandatories.get("legal_lines") or []
    if isinstance(source_legal, str):
        source_legal = [source_legal]
    default_row = locales.get(default) if isinstance(locales.get(default), Mapping) else {}
    if source_cta and normalize_copy(default_row.get("cta")) != normalize_copy(source_cta):
        findings.append({"severity": "block", "code": "source_locale_cta_mismatch",
                         "msg": f"default locale CTA 与 brief mandatories 不一致：{default_row.get('cta')} != {source_cta}"})
    if source_legal:
        localized_legal = default_row.get("legal_lines") or []
        if isinstance(localized_legal, str):
            localized_legal = [localized_legal]
        if [normalize_copy(value) for value in localized_legal] != [normalize_copy(value) for value in source_legal]:
            findings.append({"severity": "block", "code": "source_locale_legal_mismatch",
                             "msg": "default locale 法律声明与 brief mandatories.legal_lines 不一致"})
    active = []
    for item in delivery_plan.get("deliverables") or []:
        if item.get("status") == "cancelled":
            continue
        did = str(item.get("deliverable_id") or "")
        if did:
            active.append(did)
    normalized_map: dict[str, list[str]] = {}
    for did in active:
        values = mapping.get(did) or []
        if isinstance(values, str):
            values = [values]
        values = [str(v) for v in values if str(v)]
        normalized_map[did] = values
        if not values:
            findings.append({"severity": "block", "code": "deliverable_locale_missing",
                             "msg": f"交付件 {did} 未映射 locale"})
        unknown = sorted(set(values) - set(locales))
        if unknown:
            findings.append({"severity": "block", "code": "deliverable_locale_unknown",
                             "msg": f"交付件 {did} 指向未知 locale：{', '.join(unknown)}"})
    extra = sorted(set(mapping) - set(active)) if active else []
    if extra:
        findings.append({"severity": "warn", "code": "locale_mapping_orphan",
                         "msg": "locale mapping 含当前 delivery plan 不存在的交付件：" + ", ".join(extra)})
    return {
        "schema_version": SCHEMA_VERSION, "kind": VALIDATION_KIND,
        "matrix_path": "合规/locale_matrix.json", "matrix_sha256": sha(path),
        "default_locale": default, "locales": normalized,
        "deliverable_locales": normalized_map,
        "findings": findings,
        "summary": {"block": sum(f["severity"] == "block" for f in findings),
                    "warn": sum(f["severity"] == "warn" for f in findings)},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="validate ad locale matrix")
    ap.add_argument("project_root")
    ap.add_argument("--init", action="store_true", help="缺失时写 pending template；不覆盖现有文件")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    path = root / "合规" / "locale_matrix.json"
    if ns.init and not path.exists():
        plan = load(root / "合成" / "delivery_plan.json", {}) or {}
        ids = [row.get("deliverable_id") for row in plan.get("deliverables") or [] if row.get("deliverable_id")]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(template(root, ids), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[ok] {path}")
    payload = validate(root)
    out = root / "合规" / "locale_matrix_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# locale matrix block={payload['summary']['block']} warn={payload['summary']['warn']}")
    print(f"[ok] {out}")
    return 1 if payload["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
