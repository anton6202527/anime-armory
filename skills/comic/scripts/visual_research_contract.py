#!/usr/bin/env python3
"""Scaffold and validate research-only visual evidence for historical comics.

The contract is deliberately offline: it records URLs and derived findings,
but never opens a URL, downloads an image, or turns a film/TV still into a
generation attachment.  A complete contract is content evidence, not a human
style/model-pack approval receipt.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


SCHEMA_VERSION = 1
KIND = "comic_visual_research"
CONTRACT_RELATIVE_PATH = Path("设定库") / "visual_research.json"
STYLE_ANCHOR_RE = re.compile(r"^STYLE_[A-Za-z0-9][A-Za-z0-9_.-]*$")
SOURCE_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")
SOURCE_TYPES = {
    "film_tv_narrative",
    "museum_primary",
    "institution_primary",
    "archive_primary",
    "scholarly_secondary",
    "source_text",
}
PRIMARY_TYPES = {"museum_primary", "institution_primary", "archive_primary"}
DERIVED_DIMENSIONS = {
    "character",
    "costume_class",
    "environment",
    "props",
    "palette",
    "composition",
    "lighting",
    "material_finish",
    "narrative_coverage",
}
FORBIDDEN_ATTACHMENT_KEYS = {
    "local_path",
    "image_path",
    "attachment_path",
    "download_path",
    "reference_image",
}
REQUIRED_RIGHTS_RULES = (
    "research_only",
    "no_actor_likeness_direct_anchor",
    "no_film_still_as_generation_reference",
    "no_specific_composition_replication",
    "no_costume_combination_replication",
    "only_licensed_or_open_assets_in_generation",
)


def _setting_value(root: Path, key: str) -> str:
    path = root / "_设置.md"
    if not path.is_file():
        return ""
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.*?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return ""


def default_contract(root: Path, *, style_anchor_id: str = "") -> dict[str, Any]:
    anchor = style_anchor_id.strip() or _setting_value(root, "风格锚")
    if not STYLE_ANCHOR_RE.fullmatch(anchor):
        anchor = ""
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "status": "draft",
        "scope": "待填：时代、地域、章节与主要角色/场景",
        "project_style_anchor_id": anchor,
        "sources": [
            {
                "source_id": "FILM_001",
                "title": "待填：官方/版权方影视条目",
                "url": "",
                "provider": "",
                "accessed_at": date.today().isoformat(),
                "type": "film_tv_narrative",
                "usage_boundary": "research_only",
                "findings": [],
            },
            {
                "source_id": "PRIMARY_001",
                "title": "待填：博物馆/权威机构一手参考",
                "url": "",
                "provider": "",
                "accessed_at": date.today().isoformat(),
                "type": "museum_primary",
                "usage_boundary": "research_only",
                "findings": [],
            },
            {
                "source_id": "PRIMARY_002",
                "title": "待填：第二项博物馆/权威机构一手参考",
                "url": "",
                "provider": "",
                "accessed_at": date.today().isoformat(),
                "type": "institution_primary",
                "usage_boundary": "research_only",
                "findings": [],
            },
        ],
        "derived_style": {
            "summary": "",
            "decisions": [
                {
                    "dimension": "character",
                    "decision": "",
                    "evidence_source_ids": [],
                },
                {
                    "dimension": "environment",
                    "decision": "",
                    "evidence_source_ids": [],
                },
                {
                    "dimension": "palette",
                    "decision": "",
                    "evidence_source_ids": [],
                },
            ],
            "do_not_copy": [
                "影视演员脸、具体剧照构图与镜头",
                "单一影视版本的整套服饰组合",
            ],
        },
        "rights_rules": {
            "research_only": True,
            "no_actor_likeness_direct_anchor": True,
            "no_film_still_as_generation_reference": True,
            "no_specific_composition_replication": True,
            "no_costume_combination_replication": True,
            "only_licensed_or_open_assets_in_generation": True,
            "notes": [
                "本合同只保存 URL、研究发现与派生设计决策，不下载或挂载影视截图。",
            ],
        },
    }


def _issue(level: str, code: str, message: str, path: str = "") -> dict[str, str]:
    return {"level": level, "code": code, "path": path, "message": message}


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_https_url(value: Any) -> bool:
    if not _nonempty_text(value):
        return False
    parsed = urlparse(str(value).strip())
    return parsed.scheme.lower() == "https" and bool(parsed.netloc)


def _valid_iso_date(value: Any) -> bool:
    if not _nonempty_text(value):
        return False
    try:
        date.fromisoformat(str(value).strip())
    except ValueError:
        return False
    return True


def validate_contract(data: Any) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if not isinstance(data, Mapping):
        issues.append(_issue("error", "contract_not_object", "visual research contract 顶层必须是 object"))
        return _report(issues, {}, [])

    if data.get("schema_version") != SCHEMA_VERSION:
        issues.append(_issue("error", "schema_version_invalid", f"schema_version 必须为 {SCHEMA_VERSION}", "schema_version"))
    if data.get("kind") != KIND:
        issues.append(_issue("error", "kind_invalid", f"kind 必须为 {KIND}", "kind"))
    status = str(data.get("status") or "").strip()
    if status not in {"draft", "complete"}:
        issues.append(_issue("error", "status_invalid", "status 必须为 draft 或 complete", "status"))
    elif status != "complete":
        issues.append(_issue("warning", "research_status_draft", "研究内容仍为 draft；complete 只代表合同填写完整，不代表人工定妆批准", "status"))

    scope = data.get("scope")
    if not _nonempty_text(scope) or "待填" in str(scope):
        issues.append(_issue("error", "scope_missing", "scope 必须写明时代、地域或章节/角色边界", "scope"))
    anchor = str(data.get("project_style_anchor_id") or "").strip()
    if not STYLE_ANCHOR_RE.fullmatch(anchor):
        issues.append(_issue("error", "style_anchor_id_invalid", "project_style_anchor_id 必须是稳定 STYLE_... ID", "project_style_anchor_id"))

    raw_sources = data.get("sources")
    sources = raw_sources if isinstance(raw_sources, list) else []
    if not isinstance(raw_sources, list):
        issues.append(_issue("error", "sources_not_array", "sources 必须是 array", "sources"))
    known_ids: set[str] = set()
    urls: set[str] = set()
    film_urls: set[str] = set()
    primary_urls: set[str] = set()
    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        if not isinstance(source, Mapping):
            issues.append(_issue("error", "source_not_object", "source 必须是 object", prefix))
            continue
        source_id = str(source.get("source_id") or "").strip()
        if not SOURCE_ID_RE.fullmatch(source_id):
            issues.append(_issue("error", "source_id_invalid", "source_id 必须是稳定大写下划线 ID", f"{prefix}.source_id"))
        elif source_id in known_ids:
            issues.append(_issue("error", "source_id_duplicate", f"重复 source_id: {source_id}", f"{prefix}.source_id"))
        else:
            known_ids.add(source_id)
        for field in ("title", "provider"):
            if not _nonempty_text(source.get(field)):
                issues.append(_issue("error", f"source_{field}_missing", f"{field} 必填", f"{prefix}.{field}"))
        url = str(source.get("url") or "").strip()
        if not _valid_https_url(url):
            issues.append(_issue("error", "source_url_invalid", "url 必须是 https 权威来源页", f"{prefix}.url"))
        elif url in urls:
            issues.append(_issue("error", "source_url_duplicate", f"重复 url: {url}", f"{prefix}.url"))
        else:
            urls.add(url)
        if not _valid_iso_date(source.get("accessed_at")):
            issues.append(_issue("error", "source_accessed_at_invalid", "accessed_at 必须是 YYYY-MM-DD", f"{prefix}.accessed_at"))
        source_type = str(source.get("type") or "").strip()
        if source_type not in SOURCE_TYPES:
            issues.append(_issue("error", "source_type_invalid", f"type 必须是 {sorted(SOURCE_TYPES)} 之一", f"{prefix}.type"))
        elif _valid_https_url(url):
            if source_type == "film_tv_narrative":
                film_urls.add(url)
            if source_type in PRIMARY_TYPES:
                primary_urls.add(url)
        if source.get("usage_boundary") != "research_only":
            issues.append(_issue("error", "source_usage_boundary_invalid", "每项来源 usage_boundary 必须为 research_only", f"{prefix}.usage_boundary"))
        findings = source.get("findings")
        if not isinstance(findings, list) or not findings or not all(_nonempty_text(item) for item in findings):
            issues.append(_issue("error", "source_findings_missing", "findings 必须是非空文本数组", f"{prefix}.findings"))
        for key in FORBIDDEN_ATTACHMENT_KEYS.intersection(source.keys()):
            issues.append(_issue("error", "source_attachment_forbidden", f"研究合同不允许 {key}；不下载或挂载剧照/图像", f"{prefix}.{key}"))

    if len(film_urls) < 1:
        issues.append(_issue("error", "film_tv_reference_missing", "至少需要 1 项官方/版权方影视叙事参考", "sources"))
    if len(primary_urls) < 2:
        issues.append(_issue("error", "primary_references_insufficient", "至少需要 2 个不同 URL 的博物馆/权威机构一手参考", "sources"))

    derived = data.get("derived_style")
    referenced_ids: set[str] = set()
    if not isinstance(derived, Mapping):
        issues.append(_issue("error", "derived_style_not_object", "derived_style 必须是 object", "derived_style"))
    else:
        if not _nonempty_text(derived.get("summary")):
            issues.append(_issue("error", "derived_style_summary_missing", "derived_style.summary 必填", "derived_style.summary"))
        decisions = derived.get("decisions")
        if not isinstance(decisions, list) or len(decisions) < 3:
            issues.append(_issue("error", "derived_decisions_insufficient", "derived_style.decisions 至少需要 3 项可执行设计决策", "derived_style.decisions"))
            decisions = []
        dimensions: set[str] = set()
        for index, decision in enumerate(decisions):
            prefix = f"derived_style.decisions[{index}]"
            if not isinstance(decision, Mapping):
                issues.append(_issue("error", "derived_decision_not_object", "decision 必须是 object", prefix))
                continue
            dimension = str(decision.get("dimension") or "").strip()
            if dimension not in DERIVED_DIMENSIONS:
                issues.append(_issue("error", "derived_dimension_invalid", f"dimension 必须是 {sorted(DERIVED_DIMENSIONS)} 之一", f"{prefix}.dimension"))
            elif dimension in dimensions:
                issues.append(_issue("error", "derived_dimension_duplicate", f"重复 dimension: {dimension}", f"{prefix}.dimension"))
            else:
                dimensions.add(dimension)
            if not _nonempty_text(decision.get("decision")):
                issues.append(_issue("error", "derived_decision_missing", "decision 必须是可执行文本", f"{prefix}.decision"))
            evidence = decision.get("evidence_source_ids")
            if not isinstance(evidence, list) or not evidence:
                issues.append(_issue("error", "derived_evidence_missing", "evidence_source_ids 必须引用至少一项 source_id", f"{prefix}.evidence_source_ids"))
                continue
            for source_id in evidence:
                sid = str(source_id or "").strip()
                referenced_ids.add(sid)
                if sid not in known_ids:
                    issues.append(_issue("error", "derived_evidence_unknown", f"未知 source_id: {sid}", f"{prefix}.evidence_source_ids"))
        do_not_copy = derived.get("do_not_copy")
        if not isinstance(do_not_copy, list) or not do_not_copy or not all(_nonempty_text(item) for item in do_not_copy):
            issues.append(_issue("error", "derived_do_not_copy_missing", "derived_style.do_not_copy 必须明确不复制的元素", "derived_style.do_not_copy"))

    unused = sorted(known_ids - referenced_ids)
    if unused:
        issues.append(_issue("warning", "sources_not_traced_to_style", f"来源尚未追溯到 derived_style.decisions: {', '.join(unused)}", "derived_style.decisions"))

    rights = data.get("rights_rules")
    if not isinstance(rights, Mapping):
        issues.append(_issue("error", "rights_rules_not_object", "rights_rules 必须是 object", "rights_rules"))
    else:
        for field in REQUIRED_RIGHTS_RULES:
            if rights.get(field) is not True:
                issues.append(_issue("error", f"rights_{field}_required", f"rights_rules.{field} 必须显式为 true", f"rights_rules.{field}"))

    return _report(issues, {
        "sources": len(sources),
        "film_tv_narrative": len(film_urls),
        "institutional_primary": len(primary_urls),
        "derived_sources_referenced": len(referenced_ids & known_ids),
    }, sources)


def _report(issues: list[dict[str, str]], counts: Mapping[str, int], sources: Sequence[Any]) -> dict[str, Any]:
    errors = sum(item["level"] == "error" for item in issues)
    warnings = sum(item["level"] == "warning" for item in issues)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "comic_visual_research_validation",
        "valid": errors == 0,
        "strict_valid": errors == 0 and warnings == 0,
        "offline_only": True,
        "network_accessed": False,
        "counts": dict(counts),
        "summary": {"errors": errors, "warnings": warnings},
        "issues": issues,
    }


def _print_report(report: Mapping[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    print(
        "visual research contract: "
        f"valid={report.get('valid')} strict_valid={report.get('strict_valid')} "
        f"errors={summary.get('errors', 0)} warnings={summary.get('warnings', 0)} "
        f"path={report.get('path', '')}"
    )
    for issue in report.get("issues") or []:
        print(f"[{str(issue.get('level') or '').upper()}] {issue.get('code')}: {issue.get('message')}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="历史/公版名著漫画视觉研究合同（离线记录，不下载图像）")
    parser.add_argument("project_root")
    parser.add_argument("command", choices=("scaffold", "check"))
    parser.add_argument("--style-anchor-id", default="", help="稳定 STYLE_... ID；缺省尝试读 _设置.md 的风格锚")
    parser.add_argument("--write", action="store_true", help="scaffold 时写入缺失合同；永不覆盖已有文件")
    parser.add_argument("--strict", action="store_true", help="存在 warning 也返回非零")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.project_root).expanduser().resolve()
    path = root / CONTRACT_RELATIVE_PATH
    if args.command == "scaffold":
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                report = {
                    "kind": "comic_visual_research_validation",
                    "valid": False,
                    "strict_valid": False,
                    "path": str(path),
                    "error": f"已有合同无法解析，未覆盖: {exc}",
                }
                _print_report(report, as_json=args.json)
                return 2
            created = False
        else:
            data = default_contract(root, style_anchor_id=args.style_anchor_id)
            created = True
            if args.write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report = validate_contract(data)
        report.update({"path": str(path), "created": created, "written": bool(created and args.write)})
        _print_report(report, as_json=args.json)
        return 0

    if not path.is_file():
        report = {
            "kind": "comic_visual_research_validation",
            "valid": False,
            "strict_valid": False,
            "path": str(path),
            "summary": {"errors": 1, "warnings": 0},
            "issues": [_issue("error", "contract_missing", f"缺少 {CONTRACT_RELATIVE_PATH}；先运行 scaffold --write")],
        }
        _print_report(report, as_json=args.json)
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        report = {
            "kind": "comic_visual_research_validation",
            "valid": False,
            "strict_valid": False,
            "path": str(path),
            "summary": {"errors": 1, "warnings": 0},
            "issues": [_issue("error", "contract_json_invalid", str(exc))],
        }
        _print_report(report, as_json=args.json)
        return 2
    report = validate_contract(data)
    report["path"] = str(path)
    _print_report(report, as_json=args.json)
    ok = bool(report["strict_valid"] if args.strict else report["valid"])
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
