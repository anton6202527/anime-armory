#!/usr/bin/env python3
"""Safely migrate a legacy ad project to the current contracts.

Default mode is dry-run.  --write stores originals under
生产数据/migrations/<timestamp>/ before changing settings, brief, locale matrix
or the generated stage table.  Unknown facts remain pending; migration never
fabricates legal approval, evidence, placements or human sign-off.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import contract
import dependency_graph
import locale_matrix
import stage_acceptance


KIND = "ad_project_migration"
SCHEMA_VERSION = 1


LEGACY_IMAGE = {
    "codex": ("GPT Image 2", "Codex CLI"),
    "openai": ("GPT Image 2", "OpenAI Images API"),
    "seedream": ("Seedream 4.5", "BytePlus ModelArk API"),
    "nano banana": ("Nano Banana Pro (Gemini 3 Pro Image)", "Google Gemini API"),
    "gemini": ("Nano Banana Pro (Gemini 3 Pro Image)", "Google Gemini API"),
    "可灵": ("Kling Image 3.0", "Kling API"),
    "kling": ("Kling Image 3.0", "Kling API"),
    "sora": ("Sora 2", "OpenAI Sora"),
}


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def sha_bytes(raw: bytes):
    return hashlib.sha256(raw).hexdigest()


def sha(path: Path):
    return sha_bytes(path.read_bytes()) if path.is_file() else None


def parse_settings(raw: str):
    out = {}
    for line in raw.splitlines():
        m = re.match(r"\s*[-*]?\s*([^:：#]+)[:：]\s*([^#]+)", line)
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def _legacy_route(value: str):
    text = value.strip().lower()
    for marker, route in LEGACY_IMAGE.items():
        if marker in text:
            return route
    return ("manual", "manual")


def migrate_settings_text(raw: str):
    settings = parse_settings(raw)
    if "生图AI" not in settings:
        return raw, []
    model, channel = _legacy_route(settings["生图AI"])
    lines = raw.splitlines()
    out = []
    changes = []
    for line in lines:
        if re.match(r"\s*[-*]?\s*生图AI\s*[:：]", line):
            indent = line[:len(line) - len(line.lstrip())]
            prefix = "- " if line.lstrip().startswith("-") else ""
            out.append(f"{indent}{prefix}生图模型: {model}")
            out.append(f"{indent}{prefix}生图渠道: {channel}")
            changes.append(f"生图AI={settings['生图AI']} → 生图模型={model} + 生图渠道={channel}")
        else:
            out.append(line)
    note = f"- {datetime.now().date().isoformat()} 合同迁移：" + changes[0]
    try:
        index = out.index("## 记录") + 1
        out.insert(index, note)
    except ValueError:
        out.extend(["", "## 记录", note])
    return "\n".join(out).rstrip() + "\n", changes


def _as_list(value):
    if isinstance(value, list):
        return value
    return [] if value in (None, "") else [value]


def _settings_campaign(settings: Mapping[str, str]):
    return settings.get("广告目标") or "待补"


def migrate_brief(brief: Mapping[str, Any], settings: Mapping[str, str]):
    out = json.loads(json.dumps(dict(brief), ensure_ascii=False))
    changes = []
    if int(out.get("schema_version") or 0) < 2:
        out["schema_version"] = 2; changes.append("brief schema_version → 2")
    if not out.get("campaign_objective"):
        out["campaign_objective"] = _settings_campaign(settings); changes.append("补 campaign_objective（来自项目设置；仍需确认）")
    measurement = out.get("measurement") if isinstance(out.get("measurement"), dict) else {}
    for key in ("primary_kpi", "conversion_event"):
        if not measurement.get(key):
            measurement[key] = "待补"; changes.append(f"补 measurement.{key}=待补")
    out["measurement"] = measurement
    raw_claims = out.get("claims") or []
    if isinstance(raw_claims, Mapping):
        raw_claims = [raw_claims]
    claims = []
    for pos, raw in enumerate(raw_claims, 1):
        if not isinstance(raw, Mapping):
            raw = {"claim": str(raw)}
        row = dict(raw)
        row.setdefault("id", f"claim_{pos:02d}")
        row.setdefault("evidence_type", "brand_fact")
        row.setdefault("evidence", row.get("reasonable_basis") or "待补")
        row.setdefault("evidence_file", "待补")
        row.setdefault("method", "待补")
        row.setdefault("evidence_date", "待补")
        row.setdefault("territory", settings.get("发行地区") or "待补")
        row.setdefault("approved_by", "待补")
        claims.append(row)
    out["claims"] = claims
    rights = out.get("rights") if isinstance(out.get("rights"), Mapping) else {}
    migrated_rights = {}
    platforms = _as_list(out.get("platforms")) or [settings.get("目标平台") or "待补"]
    for key in ("talent", "music", "fonts", "assets"):
        raw = rights.get(key)
        if isinstance(raw, Mapping) or isinstance(raw, list):
            migrated_rights[key] = raw
            continue
        migrated_rights[key] = {
            "status": "pending", "territory": [settings.get("发行地区") or "待补"],
            "media_scope": platforms, "approved_by": "待补", "evidence_file": "待补",
            "validity": "待补", "legacy_note": str(raw or ""),
        }
        changes.append(f"rights.{key} 裸字符串 → pending 结构化记录")
    out["rights"] = migrated_rights
    out.setdefault("default_locale", "zh-CN" if settings.get("字幕语言") != "仅英文" else "en-US")
    history = out.get("migration_history") if isinstance(out.get("migration_history"), list) else []
    already_current = any(isinstance(row, Mapping) and row.get("tool") == "ad-craft/migrate_project.py" and
                          row.get("contract_version") == contract.CONTRACT_VERSION for row in history)
    if changes or not already_current:
        history.append({"tool": "ad-craft/migrate_project.py", "at": datetime.now(timezone.utc).isoformat(),
                        "contract_version": contract.CONTRACT_VERSION,
                        "note": "未知事实保留 pending；未伪造授权、法务、placement 或审批"})
    out["migration_history"] = history
    return out, changes


def _split_row(line: str):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _existing_stage_rows(raw: str):
    rows = {}
    in_stage = False
    aliases = {"AI披露/交付": "handoff", "AI披露/发布合规": "handoff", "质检自审": "review"}
    labels = {row["label"]: row["key"] for row in contract.stage_table()}
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_stage = "阶段进度" in stripped
            continue
        if not in_stage or not stripped.startswith("|"):
            continue
        cells = _split_row(stripped)
        if len(cells) < 4 or cells[0] in {"阶段", ""} or set(cells[0]) <= {"-", ":"}:
            continue
        key = labels.get(cells[0]) or aliases.get(cells[0])
        if key:
            rows[key] = cells[:4]
    return rows


def _stage_has_artifact(root: Path, stage: str):
    candidates = {
        "brief": ["需求/brief.json"], "concept": ["创意/concept.md"], "script": ["脚本/广告脚本.md"],
        "voice": ["配音/时长清单.json"], "storyboard": ["脚本/storyboard.json"],
        "image": ["出图/分镜/image_jobs_manifest.json"], "video": ["出视频/分镜/video_jobs_manifest.json"],
        "compose": ["合成/delivery_plan.json", "合成/成片_主片.mp4"],
        "handoff": ["合规/compliance_manifest.json"], "review": ["合规/ad_review_m0.json"],
        "feedback": ["投放反馈/experiment_plan.json"],
    }
    return any((root / rel).exists() for rel in candidates.get(stage, []))


def _progress_deliverable_ids(raw: str):
    ids = []
    in_matrix = False
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_matrix = "交付版本矩阵" in stripped
            continue
        if not in_matrix or not stripped.startswith("|"):
            continue
        cells = _split_row(stripped)
        if len(cells) < 4 or cells[0] in {"交付件", ""} or set(cells[0]) <= {"-", ":"}:
            continue
        duration, aspect, kind = cells[1], cells[2], cells[3]
        if kind == "master":
            ids.append("master")
        elif kind == "cutdown":
            ids.append(f"cut_{duration.lower()}")
        elif kind == "reframe":
            ids.append(f"reframe_{aspect.replace(':', 'x').lower()}")
    return ids


def _ensure_locale_deliverables(payload, ids):
    out = json.loads(json.dumps(payload, ensure_ascii=False))
    default = str(out.get("default_locale") or "").strip()
    mapping = out.setdefault("deliverable_locales", {})
    added = []
    for did in ids:
        if did and not mapping.get(did):
            mapping[did] = [default] if default else []
            added.append(did)
    return out, added


def migrate_progress_text(root: Path, raw: str):
    existing = _existing_stage_rows(raw)
    reports = {stage: stage_acceptance.evaluate(root, stage, "formal") for stage in stage_acceptance.ACCEPTORS}
    dependency = dependency_graph.analyze(root)
    table = ["## 阶段进度", "", "| 阶段 | 状态 | 产物 | 备注 |", "|---|---|---|---|"]
    for row in contract.stage_table():
        key, label = row["key"], row["label"]
        previous = existing.get(key, [label, "⬜", "", ""])
        report = reports[key]
        dep = (dependency.get("stages") or {}).get(key) or {}
        dep_total = sum(int(dep.get(name) or 0) for name in ("current", "stale", "unaccepted", "missing"))
        dependency_current = dep_total > 0 and int(dep.get("current") or 0) == dep_total
        if report["summary"]["accepted"] and dependency_current:
            status = "✅"
        elif _stage_has_artifact(root, key):
            status = "🔴block"
        else:
            status = "⬜"
        codes = [item["code"] for item in report["findings"] if item["severity"] == "block"]
        remark = previous[3]
        if codes:
            remark = "新验收阻断：" + ", ".join(codes[:4]) + ("…" if len(codes) > 4 else "")
        table.append(f"| {label} | {status} | {previous[2]} | {remark} |")
    lines = raw.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "## 阶段进度"), None)
    if start is None:
        lines.extend(["", *table])
    else:
        end = next((i for i in range(start + 1, len(lines)) if lines[i].strip().startswith("## ")), len(lines))
        lines[start:end] = table + [""]
    note = f"- {datetime.now().date().isoformat()} 合同迁移：按当前 stage_acceptance 重算状态；旧 ✅ 不自动继承。"
    marker = next((i for i, line in enumerate(lines) if line.strip() == "## 维护记录"), None)
    if marker is None:
        lines.extend(["", "## 维护记录", note])
    else:
        lines.insert(marker + 1, note)
    return "\n".join(lines).rstrip() + "\n", reports


def _backup(root: Path, paths):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = root / "生产数据" / "migrations" / stamp / "original"
    for path in paths:
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    return base.parent


def run(root: Path, write=False):
    root = root.resolve()
    settings_path = root / "_设置.md"; brief_path = root / "需求" / "brief.json"; progress_path = root / "_进度.md"
    settings_raw = settings_path.read_text(encoding="utf-8")
    new_settings, setting_changes = migrate_settings_text(settings_raw)
    settings_values = parse_settings(new_settings)
    old_brief = load(brief_path, {}) or {}
    new_brief, brief_changes = migrate_brief(old_brief, settings_values)
    plan = load(root / "合成" / "delivery_plan.json", {}) or {}
    progress_before = progress_path.read_text(encoding="utf-8")
    ids = [row.get("deliverable_id") for row in plan.get("deliverables") or [] if row.get("deliverable_id")]
    ids.extend(_progress_deliverable_ids(progress_before))
    cutdown = settings_values.get("cutdown版本", "主片+15s+6s")
    if cutdown in {"15s+6s", "15s"}:
        cutdown = "主片+" + cutdown
    ids.extend(row.get("deliverable_id") for row in contract.default_deliverables(
        settings_values.get("主片时长", "30s"), settings_values.get("交付比例", "16:9"), cutdown)
               if row.get("deliverable_id"))
    ids = list(dict.fromkeys(str(value) for value in ids if value))
    locale_path = root / "合规" / "locale_matrix.json"
    locale_missing_before = not locale_path.is_file()
    locale_payload = load(locale_path) if locale_path.is_file() else locale_matrix.template(root, ids)
    locale_payload, locale_added = _ensure_locale_deliverables(locale_payload, ids)
    locale_changed = locale_missing_before or bool(locale_added)
    before = {str(path.relative_to(root)): sha(path) for path in (settings_path, brief_path, progress_path, locale_path)}
    backup = None
    reports = {}
    if write:
        backup = _backup(root, (settings_path, brief_path, progress_path, locale_path,
                                root / "生产数据" / "migration_report.json"))
        settings_path.write_text(new_settings, encoding="utf-8")
        brief_path.write_text(json.dumps(new_brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        locale_path.parent.mkdir(parents=True, exist_ok=True)
        if locale_changed:
            locale_path.write_text(json.dumps(locale_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        progress_raw = progress_path.read_text(encoding="utf-8")
        new_progress, reports = migrate_progress_text(root, progress_raw)
        progress_path.write_text(new_progress, encoding="utf-8")
        dependency_graph.write_graph(root)
    else:
        reports = {stage: stage_acceptance.evaluate(root, stage, "formal") for stage in stage_acceptance.ACCEPTORS}
    after = {str(path.relative_to(root)): sha(path) for path in (settings_path, brief_path, progress_path, locale_path)}
    payload = {
        "schema_version": SCHEMA_VERSION, "kind": KIND, "mode": "write" if write else "dry_run",
        "generated_at": datetime.now(timezone.utc).isoformat(), "project_root": str(root),
        "contract_version": contract.CONTRACT_VERSION, "backup": str(backup.relative_to(root)) if backup else "",
        "changes": setting_changes + brief_changes + (["初始化 locale_matrix pending template"] if locale_missing_before else []) +
                   (["locale matrix 补交付件映射：" + ", ".join(locale_added)] if locale_added and not locale_missing_before else []),
        "before_sha256": before, "after_sha256": after,
        "acceptance": {stage: report["summary"] for stage, report in reports.items()},
        "note": "迁移只修 schema/状态；pending 事实必须由客户、品牌、法务或发布方补齐。",
    }
    if write:
        out = root / "生产数据" / "migration_report.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv=None):
    ap = argparse.ArgumentParser(description="migrate legacy ad project contracts")
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true", help="备份后写入；默认只预览")
    ns = ap.parse_args(argv)
    payload = run(Path(ns.project_root), ns.write)
    print(f"# ad migration mode={payload['mode']} changes={len(payload['changes'])}")
    for change in payload["changes"]:
        print(f"- {change}")
    for stage, summary in payload["acceptance"].items():
        print(f"  {stage}: accepted={summary['accepted']} block={summary['block']} warn={summary['warn']}")
    if ns.write:
        print(f"[ok] {Path(ns.project_root).resolve() / '生产数据' / 'migration_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
