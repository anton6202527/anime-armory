#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读扫描画漫画项目进度。"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping


COMIC_LIB = Path(__file__).resolve().parents[2] / "comic" / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
from contracts import stage_inputs_fingerprint  # noqa: E402


ROUTE = {
    "源本/企划": "comic-script",
    "漫画脚本": "comic-script",
    "缩略分镜": "comic-name",
    "页面排版": "comic-layout",
    "原稿收尾": "comic-finishing",
    "出图包": "comic-image",
    "出图": "comic-image",
    "嵌字合成": "comic-compose",
    "审查": "comic-review",
}

STAGE_ALIASES = {
    "原稿收尾": ("原稿收尾", "传统收尾"),
}

DONE = {"✅", "[x]", "完成", "done", "pass"}

STAGE_KEYS = {
    "源本/企划": "source",
    "漫画脚本": "script",
    "缩略分镜": "name",
    "页面排版": "layout",
    "原稿收尾": "finishing",
    "出图包": "image_jobs",
    "出图": "image",
    "嵌字合成": "compose",
    "审查": "review",
}
STAGE_ORDER = tuple(STAGE_KEYS.values())
STAGE_LABELS = {value: key for key, value in STAGE_KEYS.items()}
SKILL_FOR_STAGE = {
    "source": "comic-script",
    "script": "comic-script",
    "name": "comic-name",
    "layout": "comic-layout",
    "finishing": "comic-finishing",
    "identity": "comic-identity",
    "image_jobs": "comic-image",
    "image": "comic-image",
    "compose": "comic-compose",
    "review": "comic-review",
}
PLACEHOLDER_RE = re.compile(r"待补|待填|TODO|TBD|<[^>]*>|__待", re.IGNORECASE)

# Copy-pasteable "run this next" command per stage.  Purely descriptive — it
# names the next stage's own script (which itself only produces a draft / runs a
# --check), never an approval or a paid generation, so surfacing it bypasses no
# gate.  Kept local to this skill (not imported from comic-update) to preserve
# cross-line independence.
STAGE_NEXT_COMMAND = {
    "source": 'python3 skills/comic-script/scripts/development_pack.py "{root}" check --strict --json',
    "script": 'python3 skills/comic-script/scripts/source_semantics_gate.py "{root}" --chapter {ch}',
    "name": 'python3 skills/comic-name/scripts/build_name_board.py "{root}" --chapter {ch}',
    "layout": 'python3 skills/comic-layout/scripts/build_layout.py "{root}" --chapter {ch}',
    "finishing": 'python3 skills/comic-finishing/scripts/build_finishing_plan.py "{root}" --chapter {ch}',
    "image_jobs": 'python3 skills/comic-image/scripts/build_panel_jobs.py "{root}" --chapter {ch}',
    "image": 'python3 skills/comic-review/scripts/gate.py "{root}" --chapter {ch} --stage image_preflight',
    "compose": 'python3 skills/comic-compose/scripts/export_longstrip.py "{root}" --chapter {ch} --render --qc-slots',
    "review": 'python3 skills/comic-review/scripts/review.py "{root}" --chapter {ch}',
}
# Fallback for blocker/special fronts whose stage label is not in STAGE_KEYS.
SKILL_NEXT_COMMAND = {
    "comic-script": 'python3 skills/comic-script/scripts/development_pack.py "{root}" check --strict --json',
    "comic-identity": 'python3 skills/comic-identity/scripts/model_pack.py "{root}" check --write --json',
    "comic-name": 'python3 skills/comic-name/scripts/build_name_board.py "{root}" --chapter {ch} --check',
    "comic-layout": 'python3 skills/comic-layout/scripts/build_layout.py "{root}" --chapter {ch} --check',
    "comic-finishing": 'python3 skills/comic-finishing/scripts/build_finishing_plan.py "{root}" --chapter {ch}',
    "comic-image": 'python3 skills/comic-image/scripts/build_panel_jobs.py "{root}" --chapter {ch} --check',
    "comic-compose": 'python3 skills/comic-compose/scripts/export_longstrip.py "{root}" --chapter {ch} --render --qc-slots',
    "comic-review": 'python3 skills/comic-review/scripts/review.py "{root}" --chapter {ch}',
}


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _gap(
    root: Path,
    chapter: str,
    stage: str,
    code: str,
    path: Path,
    reason: str,
    skill: str | None = None,
) -> dict[str, Any]:
    return {
        "chapter": chapter,
        "stage": stage,
        "stage_label": STAGE_LABELS.get(stage, "一致性合同" if stage == "identity" else stage),
        "severity": "block",
        "code": code,
        "artifact": rel(root, path),
        "reason": reason,
        "next_skill": skill or SKILL_FOR_STAGE.get(stage, "comic-review"),
    }


_CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNITS = {"十": 10, "百": 100, "千": 1000, "万": 10000}


def _cn_number(raw: str) -> int | None:
    if raw.isdigit():
        return int(raw)
    if not raw or any(ch not in _CN_DIGITS and ch not in _CN_UNITS for ch in raw):
        return None
    total = section = number = 0
    for ch in raw:
        if ch in _CN_DIGITS:
            number = _CN_DIGITS[ch]
        elif _CN_UNITS[ch] == 10000:
            total += (section + number) * 10000
            section = number = 0
        else:
            section += (number or 1) * _CN_UNITS[ch]
            number = 0
    return total + section + number


def _numbered_label(value: Any) -> tuple[int, str] | None:
    match = re.search(r"第\s*([0-9]+|[零〇一二两三四五六七八九十百千万]+)\s*(话|話|章|回|节)", str(value or ""))
    if not match:
        return None
    number = _cn_number(match.group(1))
    return (number, "话" if match.group(2) == "話" else match.group(2)) if number is not None else None


def normalize_chapter(value: Any) -> str:
    parsed = _numbered_label(value)
    if parsed:
        return f"第{parsed[0]}话"
    return str(value or "").strip()


def _source_coverage_gaps(blueprint: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    previous: dict[tuple[str, str], tuple[int, int, str]] = {}
    whole_files: dict[str, str] = {}
    for entry in blueprint.get("chapters") or []:
        if not isinstance(entry, Mapping) or entry.get("source_mode", "adapted") != "adapted":
            continue
        chapter = str(entry.get("chapter") or "?")
        for span in entry.get("source_spans") or []:
            if not isinstance(span, Mapping):
                continue
            source_path = str(span.get("source_path") or "")
            exception = str(span.get("coverage_exception") or "").strip()
            if span.get("whole_file") is True:
                if source_path in whole_files and not exception:
                    issues.append(f"{source_path} 在 {whole_files[source_path]}/{chapter} 重复整文件消费")
                whole_files[source_path] = chapter
                continue
            start = _numbered_label(span.get("start"))
            end = _numbered_label(span.get("end") or span.get("start"))
            if not start or not end or start[1] != end[1]:
                continue
            key = (source_path, start[1])
            prior = previous.get(key)
            if prior and not exception:
                if start[0] <= prior[1]:
                    issues.append(f"{source_path} {prior[2]}/{chapter} 范围重叠")
                elif start[0] > prior[1] + 1:
                    issues.append(f"{source_path} 第{prior[1] + 1}{start[1]}-第{start[0] - 1}{start[1]} 未覆盖")
            previous[key] = (start[0], max(end[0], prior[1] if prior else end[0]), chapter)
    return issues


def read_setting(root: Path, key: str, default: str = "") -> str:
    path = root / "_设置.md"
    if not path.is_file():
        return default
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


def _approval_subject_sha(payload: Mapping[str, Any]) -> str:
    subject = copy.deepcopy(dict(payload))
    subject.pop("approval", None)
    subject.pop("validation", None)
    subject.pop("workflow_status", None)
    return canonical_sha256(subject)


def _editorial_artifact_gaps(root: Path, chapter: str, stage: str) -> list[dict[str, Any]]:
    path = (
        root / "排版" / chapter / "name_board.json"
        if stage == "name"
        else root / "排版" / chapter / "layout.json"
    )
    payload = load_json(path)
    if payload is None:
        return [_gap(root, chapter, stage, f"{stage}_missing_or_invalid", path, f"{path.name} 缺失或不可解析。")]
    expected_kind = "comic_name_board" if stage == "name" else "comic_layout"
    if payload.get("schema_version") != 2 or payload.get("kind") != expected_kind:
        return [_gap(root, chapter, stage, f"{stage}_schema_legacy", path, f"{path.name} 尚未迁移到 schema v2。")]
    approval = payload.get("approval") if isinstance(payload.get("approval"), Mapping) else {}
    if payload.get("workflow_status") != "approved" or approval.get("status") != "approved":
        status = str(payload.get("workflow_status") or "missing")
        return [_gap(root, chapter, stage, f"{stage}_not_approved", path, f"{path.name} 尚未 approved（当前 {status}）；draft 必须先 submit-review 再人工签收。")]
    if not str(approval.get("reviewed_by") or "").strip() or not str(approval.get("reviewed_at") or "").strip():
        return [_gap(root, chapter, stage, f"{stage}_approval_identity_missing", path, f"{path.name} approval 缺 reviewed_by/reviewed_at。")]
    if str(approval.get("subject_sha256") or "") != _approval_subject_sha(payload):
        return [_gap(root, chapter, stage, f"{stage}_approval_stale", path, f"{path.name} 已在签收后改动，approval subject SHA 失效。")]
    receipt = payload.get("upstream_receipt") if isinstance(payload.get("upstream_receipt"), Mapping) else {}
    current = {
        "panel_script_sha256": sha256_file(root / "脚本" / chapter / "panel_script.json"),
        "settings_sha256": sha256_file(root / "_设置.md"),
    }
    if stage == "layout":
        current["name_board_sha256"] = sha256_file(root / "排版" / chapter / "name_board.json")
    stale = [key for key, value in current.items() if str(receipt.get(key) or "") != value]
    if stale:
        return [_gap(root, chapter, stage, f"{stage}_upstream_stale", path, f"{path.name} 未消费当前上游 SHA：{','.join(stale)}。")]
    validation = payload.get("validation") if isinstance(payload.get("validation"), Mapping) else {}
    if validation.get("status") not in {"pass", None}:
        return [_gap(root, chapter, stage, f"{stage}_validation_failed", path, f"{path.name} validation 未通过。")]
    return []


def _finishing_gaps(root: Path, chapter: str) -> list[dict[str, Any]]:
    path = root / "出图" / chapter / "finishing" / "finishing_plan.json"
    payload = load_json(path)
    if payload is None:
        return [_gap(root, chapter, "finishing", "finishing_plan_missing_or_invalid", path, "finishing_plan.json 缺失或不可解析。")]
    if payload.get("schema_version") != 2 or payload.get("kind") != "comic_finishing_plan":
        return [_gap(root, chapter, "finishing", "finishing_plan_schema_legacy", path, "finishing_plan 尚未迁移到 schema v2。")]
    if payload.get("workflow_status") != "validated" or (payload.get("validation") or {}).get("status") != "pass":
        return [_gap(root, chapter, "finishing", "finishing_plan_not_validated", path, "finishing_plan 尚未 validated/pass。")]
    receipt = payload.get("upstream_receipt") if isinstance(payload.get("upstream_receipt"), Mapping) else {}
    current = {
        "panel_script_sha256": sha256_file(root / "脚本" / chapter / "panel_script.json"),
        "name_board_sha256": sha256_file(root / "排版" / chapter / "name_board.json"),
        "layout_sha256": sha256_file(root / "排版" / chapter / "layout.json"),
        "settings_sha256": sha256_file(root / "_设置.md"),
    }
    stale = [key for key, value in current.items() if str(receipt.get(key) or "") != value]
    if stale:
        return [_gap(root, chapter, "finishing", "finishing_plan_stale", path, "finishing_plan 上游 SHA 失效：" + ",".join(stale))]
    return []


def _chapter_contract_gaps(root: Path, chapter: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    gaps: list[dict[str, Any]] = []
    blueprint_path = root / "脚本" / "split_blueprint.json"
    blueprint = load_json(blueprint_path)
    if blueprint is None:
        return [_gap(root, chapter, "script", "split_blueprint_missing_or_invalid", blueprint_path, "缺少可解析的 split_blueprint.json v2 章节合同。")], None
    if int(blueprint.get("version") or 1) < 2:
        gaps.append(_gap(root, chapter, "script", "split_blueprint_migration_required", blueprint_path, "split_blueprint 是 v1/旧结构，strict 流程要求 v2。"))
    if blueprint.get("status") != "confirmed":
        gaps.append(_gap(root, chapter, "script", "split_blueprint_not_confirmed", blueprint_path, f"split_blueprint status={blueprint.get('status') or 'missing'}，未确认。"))
    coverage = _source_coverage_gaps(blueprint)
    if coverage:
        gaps.append(_gap(root, chapter, "script", "source_coverage_gap", blueprint_path, "source_spans 覆盖存在未说明的缺口/重叠：" + "；".join(coverage[:6])))
    contract = next(
        (
            item
            for item in blueprint.get("chapters") or []
            if isinstance(item, dict) and normalize_chapter(item.get("chapter")) == normalize_chapter(chapter)
        ),
        None,
    )
    if contract is None:
        gaps.append(_gap(root, chapter, "script", "chapter_contract_missing", blueprint_path, f"split_blueprint 缺 {chapter} chapter contract。"))
        return gaps, None
    required = ("reader_promise", "core_conflict", "turning_point", "payoff", "ending_mode", "budget")
    missing = [key for key in required if contract.get(key) in (None, "", [], {})]
    if contract.get("source_mode", "adapted") == "adapted" and not contract.get("source_spans"):
        missing.append("source_spans")
    elif contract.get("source_mode", "adapted") == "adapted":
        span_errors: list[str] = []
        for index, span in enumerate(contract.get("source_spans") or []):
            if not isinstance(span, Mapping) or not str(span.get("source_path") or "").strip():
                span_errors.append(f"source_spans[{index}]缺 source_path")
                continue
            source_path = root / str(span.get("source_path"))
            if not source_path.is_file():
                span_errors.append(f"{span.get('source_path')}不存在")
            if span.get("whole_file") is not True:
                start = _numbered_label(span.get("start"))
                end = _numbered_label(span.get("end") or span.get("start"))
                if not start or not end or start[1] != end[1] or start[0] > end[0]:
                    span_errors.append(f"source_spans[{index}]区间无效")
        if span_errors:
            gaps.append(_gap(root, chapter, "script", "chapter_contract_source_spans_invalid", blueprint_path, f"{chapter} source_spans 无法确定性消费：" + "；".join(span_errors[:8])))
    if contract.get("chapter_type") in {"serial", "bridge", "epilogue"}:
        missing += [key for key in ("entry_state", "exit_state") if not isinstance(contract.get(key), Mapping) or not contract.get(key)]
        if not isinstance(contract.get("continuity_delta"), list) or not contract.get("continuity_delta"):
            missing.append("continuity_delta")
        else:
            transition_errors = []
            required_transition = ("entity_id", "field", "from", "to", "panel_id", "reason")
            for index, transition in enumerate(contract.get("continuity_delta") or []):
                if not isinstance(transition, Mapping):
                    transition_errors.append(f"continuity_delta[{index}] 不是 object")
                    continue
                absent = [key for key in required_transition if transition.get(key) in (None, "")]
                if absent:
                    transition_errors.append(f"continuity_delta[{index}]缺 {','.join(absent)}")
            if transition_errors:
                gaps.append(_gap(root, chapter, "script", "chapter_contract_continuity_delta_invalid", blueprint_path, f"{chapter} continuity_delta 不是可追溯 transition：" + "；".join(transition_errors[:8])))
    if missing:
        gaps.append(_gap(root, chapter, "script", "chapter_contract_incomplete", blueprint_path, f"{chapter} chapter contract 缺必填字段：{','.join(dict.fromkeys(missing))}。"))
    if contract.get("status") not in {"confirmed", "locked"}:
        gaps.append(_gap(root, chapter, "script", "chapter_contract_not_confirmed", blueprint_path, f"{chapter} contract status={contract.get('status') or 'missing'}。"))
    return gaps, contract


def _development_pack_gaps(root: Path, chapter: str, blueprint: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    files = {
        "adaptation_strategy": root / "开发包" / "adaptation_strategy.json",
        "season_arc": root / "开发包" / "season_arc.json",
        "split_blueprint": root / "脚本" / "split_blueprint.json",
    }
    hashes: dict[str, str] = {}
    for key, path in files.items():
        payload = blueprint if key == "split_blueprint" and blueprint is not None else load_json(path)
        if payload is None:
            gaps.append(_gap(root, chapter, "script", f"development_pack_{key}_missing", path, f"开发包 strict 缺 {rel(root, path)}。"))
            continue
        hashes[key] = sha256_file(path)
        if int(payload.get("version") or 1) < 2:
            gaps.append(_gap(root, chapter, "script", f"development_pack_{key}_legacy", path, f"{path.name} 需迁移到 v2。"))
        if payload.get("status") != "confirmed":
            gaps.append(_gap(root, chapter, "script", f"development_pack_{key}_not_confirmed", path, f"{path.name} status 必须是 confirmed。"))
        if payload.get("status") == "confirmed" and PLACEHOLDER_RE.search(json.dumps(payload, ensure_ascii=False)):
            gaps.append(_gap(root, chapter, "script", f"development_pack_{key}_placeholder", path, f"{path.name} 已声明 confirmed 但仍有占位符。"))
    signoff_path = root / "开发包" / "signoff.json"
    signoff = load_json(signoff_path)
    if signoff is None:
        gaps.append(_gap(root, chapter, "script", "development_pack_signoff_missing", signoff_path, "开发包缺 reviewer/role/time + 三件套 SHA 签收。"))
        return gaps
    if not all(str(signoff.get(key) or "").strip() for key in ("reviewer", "role", "time")):
        gaps.append(_gap(root, chapter, "script", "development_pack_signoff_identity_missing", signoff_path, "开发包 signoff 缺 reviewer/role/time。"))
    bound = signoff.get("file_sha256") if isinstance(signoff.get("file_sha256"), Mapping) else {}
    stale = [key for key, digest in hashes.items() if str(bound.get(key) or "") != digest]
    if stale:
        gaps.append(_gap(root, chapter, "script", "development_pack_signoff_stale", signoff_path, "开发包签收未绑定当前 SHA：" + ",".join(stale)))
    return gaps


def _script_and_source_gaps(root: Path, chapter: str, contract: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    panel_path = root / "脚本" / chapter / "panel_script.json"
    panel = load_json(panel_path)
    if panel is None:
        return [_gap(root, chapter, "script", "panel_script_missing_or_invalid", panel_path, "panel_script.json 缺失或不可解析。")]
    if not isinstance(panel.get("visual_contract"), Mapping) or not panel.get("visual_contract"):
        gaps.append(_gap(root, chapter, "script", "visual_contract_missing", panel_path, "panel_script 缺 visual_contract。"))
    if contract is None:
        return gaps
    contract_sha = canonical_sha256(contract)
    binding = panel.get("chapter_contract") if isinstance(panel.get("chapter_contract"), Mapping) else {}
    if str(binding.get("chapter_contract_sha256") or binding.get("sha256") or "") != contract_sha:
        gaps.append(_gap(root, chapter, "script", "panel_script_chapter_contract_stale", panel_path, "panel_script 没有绑定当前 chapter contract SHA。"))
    if contract.get("source_mode", "adapted") != "adapted":
        return gaps
    semantics_path = root / "脚本" / chapter / "source_semantics.json"
    semantics = load_json(semantics_path)
    if semantics is None:
        gaps.append(_gap(root, chapter, "script", "source_semantics_missing_or_invalid", semantics_path, "改编话次缺 source_semantics.json v2。"))
        return gaps
    if semantics.get("schema_version") != 2 or semantics.get("kind") != "comic_source_semantics":
        gaps.append(_gap(root, chapter, "script", "source_semantics_schema_legacy", semantics_path, "source_semantics 不是 schema v2。"))
    contract_receipt = semantics.get("chapter_contract") if isinstance(semantics.get("chapter_contract"), Mapping) else {}
    if contract_receipt.get("enforced") is not True or str(contract_receipt.get("sha256") or "") != contract_sha:
        gaps.append(_gap(root, chapter, "script", "source_semantics_contract_stale", semantics_path, "source_semantics 未消费当前 chapter contract SHA。"))
    stale_files: list[str] = []
    for record in semantics.get("source_files") or []:
        if not isinstance(record, Mapping) or record.get("status") != "read":
            continue
        raw = str(record.get("path") or "")
        source_path = Path(raw) if Path(raw).is_absolute() else root / raw
        if not source_path.is_file() or str(record.get("sha256") or "") != sha256_file(source_path):
            stale_files.append(raw or "unknown")
    if stale_files or semantics.get("stale_reasons"):
        gaps.append(_gap(root, chapter, "script", "source_semantics_source_stale", semantics_path, "源文件/报告已变更：" + "、".join(stale_files + [str(item) for item in semantics.get("stale_reasons") or []])[:800]))
    coverage = semantics.get("panel_coverage") if isinstance(semantics.get("panel_coverage"), Mapping) else {}
    if semantics.get("status") != "pass" or coverage.get("status") != "pass":
        missing = coverage.get("missing_segment_ids") if isinstance(coverage.get("missing_segment_ids"), list) else []
        gaps.append(_gap(root, chapter, "script", "source_semantics_coverage_not_passed", semantics_path, "源语义/分格覆盖未 pass" + ("：" + ",".join(map(str, missing)) if missing else "") + "。"))
    return gaps


def _identity_gaps(root: Path, chapter: str) -> list[dict[str, Any]]:
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry = load_json(registry_path)
    if registry is None:
        return [_gap(root, chapter, "identity", "identity_registry_missing_or_invalid", registry_path, "identity_registry.json 缺失或不可解析。")]
    if registry.get("schema_version") != 2 or registry.get("kind") != "comic_identity_registry":
        return [_gap(root, chapter, "identity", "identity_registry_v2_required", registry_path, "identity registry 必须先迁移并校验为 schema v2。")]
    assets = registry.get("assets") if isinstance(registry.get("assets"), Mapping) else {}
    if not isinstance(registry.get("assets"), Mapping):
        return [_gap(root, chapter, "identity", "identity_registry_assets_invalid", registry_path, "identity registry assets 必须是 object。")]
    identity_assets = {
        str(asset_id): asset
        for asset_id, asset in assets.items()
        if isinstance(asset, Mapping)
        and asset.get("type") in {"character", "monster"}
    }
    binding_collections = {
        "form_id": "forms",
        "outfit_id": "outfits",
        "expression_id": "expressions",
        "state_id": "states",
    }
    for cid, asset in identity_assets.items():
        default = asset.get("default_binding") if isinstance(asset.get("default_binding"), Mapping) else {}
        invalid: list[str] = []
        for id_key, collection_key in binding_collections.items():
            collection = asset.get(collection_key) if isinstance(asset.get(collection_key), Mapping) else {}
            selected = str(default.get(id_key) or "")
            if not collection:
                invalid.append(collection_key)
            elif not selected or selected not in collection:
                invalid.append(f"default_binding.{id_key}")
        if invalid:
            return [_gap(root, chapter, "identity", "identity_registry_character_contract_invalid", registry_path, f"{cid} 缺失/引用不明的 v2 身份子合同：{','.join(invalid)}。")]
    # Align exactly with model_pack.py（2026-07-17 起）：角色全部纳管；monster 按
    # 档位默认纳管（core_full/recurring_standard），model_pack_required 显式
    # true/false 可覆盖。此前 opt-in 口径导致虎妖漏管（P015 四足虎无人拦）。
    def _monster_managed(asset: Mapping) -> bool:
        flag = asset.get("model_pack_required")
        if flag is True or flag is False:
            return flag
        tier = str(asset.get("library_tier") or asset.get("tier") or "").strip()
        return tier in ("core_full", "recurring_standard")

    model_pack_assets = {
        cid: asset
        for cid, asset in identity_assets.items()
        if asset.get("type") == "character"
        or (asset.get("type") == "monster" and _monster_managed(asset))
    }
    if not model_pack_assets:
        return []
    report_path = root / "生产数据" / "comic_model_pack_report.json"
    report = load_json(report_path)
    if report is None:
        return [_gap(root, chapter, "identity", "model_pack_report_missing_or_invalid", report_path, "缺少可解析的 comic_model_pack_report.json。")]
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    if int(summary.get("needs_fix") or 0) or int(summary.get("needs_approval") or 0):
        return [_gap(root, chapter, "identity", "model_pack_not_ready", report_path, f"model pack 仍有 needs_fix={summary.get('needs_fix') or 0} / needs_approval={summary.get('needs_approval') or 0}。")]
    rows = {
        str(item.get("character_id")): item
        for item in report.get("characters") or []
        if isinstance(item, Mapping) and item.get("character_id")
    }
    missing = sorted(set(model_pack_assets) - set(rows))
    if missing:
        return [_gap(root, chapter, "identity", "model_pack_report_incomplete", report_path, "model pack report 未覆盖角色：" + "、".join(missing))]
    for cid, asset in model_pack_assets.items():
        row = rows[cid]
        if row.get("readiness") != "ready":
            return [_gap(root, chapter, "identity", "model_pack_character_not_ready", report_path, f"{cid} readiness={row.get('readiness') or 'missing'}。")]
        stale_views: list[str] = []
        for evidence in row.get("view_evidence") or []:
            if not isinstance(evidence, Mapping) or not evidence.get("path"):
                continue
            view_path = Path(str(evidence.get("path")))
            if not view_path.is_absolute():
                view_path = root / view_path
            if str(evidence.get("sha256") or "") != sha256_file(view_path):
                stale_views.append(str(evidence.get("view") or evidence.get("path")))
        if stale_views:
            return [_gap(root, chapter, "identity", "model_pack_report_stale", report_path, f"{cid} 定妆视图在检查后已改动：{','.join(stale_views)}。")]
        tier = str(asset.get("library_tier") or asset.get("tier") or "core_full")
        # Every tier with required views needs a current SHA-bound human
        # receipt.  Tier controls production depth, not whether visual
        # identity approval may be skipped.
        if tier != "restricted_partial":
            signoff_path = root / "生产数据" / "comic_model_pack_signoffs" / f"{cid}.json"
            signoff = load_json(signoff_path)
            if signoff is None:
                return [_gap(root, chapter, "identity", "model_pack_signoff_missing", signoff_path, f"{cid} 缺业界多视图并排人审签收。")]
            if (
                signoff.get("decision") != "approved"
                or str(signoff.get("character_id") or "") != cid
                or str(signoff.get("model_pack_fingerprint") or "") != str(row.get("model_pack_fingerprint") or "")
                or str((row.get("signoff") or {}).get("status") or "") != "current"
            ):
                return [_gap(root, chapter, "identity", "model_pack_signoff_stale", signoff_path, f"{cid} model-pack 签收未绑定当前视图指纹。")]
            if (
                not str(signoff.get("reviewer") or "").strip()
                or not str(signoff.get("approved_at") or "").strip()
                or not str(signoff.get("reason") or "").strip()
            ):
                return [_gap(root, chapter, "identity", "model_pack_signoff_identity_missing", signoff_path, f"{cid} 签收缺 reviewer/approved_at/reason。")]
            confirmations = signoff.get("confirmations") if isinstance(signoff.get("confirmations"), Mapping) else {}
            required_confirmations = (
                "same_character", "correct_view_labels", "proportions_aligned", "baseline_aligned",
                "outfit_and_markers_consistent", "neutral_pose_usable",
            )
            if not all(confirmations.get(key) is True for key in required_confirmations):
                return [_gap(root, chapter, "identity", "model_pack_signoff_confirmations_missing", signoff_path, f"{cid} 签收未确认全部多视图人审项。")]
    return []


def _reference_and_jobs_gaps(root: Path, chapter: str) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    plan_path = root / "生产数据" / f"comic_reference_plan_{chapter}.json"
    plan = load_json(plan_path)
    if plan is None:
        return [_gap(root, chapter, "image_jobs", "reference_plan_missing_or_invalid", plan_path, "缺少可解析的逐格参考事前处方。")]
    if plan.get("kind") != "comic_reference_plan" or plan.get("chapter") != chapter:
        gaps.append(_gap(root, chapter, "image_jobs", "reference_plan_contract_invalid", plan_path, "reference plan kind/chapter 与当前话不匹配。"))
    summary = plan.get("summary") if isinstance(plan.get("summary"), Mapping) else {}
    if int(summary.get("block") or 0) or int(summary.get("panels_blocked") or 0):
        gaps.append(_gap(root, chapter, "image_jobs", "reference_plan_blocked", plan_path, "reference plan 仍含 block，不能构建正式出图包。", "comic-identity"))
    stale_inputs: list[str] = []
    inputs = plan.get("inputs") if isinstance(plan.get("inputs"), Mapping) else {}
    for item in inputs.get("files") or []:
        if not isinstance(item, Mapping) or not item.get("path"):
            continue
        path = Path(str(item.get("path")))
        if not path.is_absolute():
            path = root / path
        exists = path.is_file()
        if bool(item.get("exists")) != exists or (exists and str(item.get("sha256") or "") != sha256_file(path)):
            stale_inputs.append(str(item.get("path")))
    if stale_inputs:
        gaps.append(_gap(root, chapter, "image_jobs", "reference_plan_stale", plan_path, "reference plan 输入已变更：" + "、".join(stale_inputs)))
    plan_subject = {key: value for key, value in plan.items() if key not in {"generated_at", "plan_sha256"}}
    if str(plan.get("plan_sha256") or "") != canonical_sha256(plan_subject):
        gaps.append(_gap(root, chapter, "image_jobs", "reference_plan_sha_invalid", plan_path, "reference plan plan_sha256 与当前内容不匹配。"))

    jobs_path = root / "出图" / chapter / "prompt" / "panel_jobs.json"
    jobs = load_json(jobs_path)
    if jobs is None:
        gaps.append(_gap(root, chapter, "image_jobs", "panel_jobs_missing_or_invalid", jobs_path, "panel_jobs.json 缺失或不可解析。"))
        return gaps
    if jobs.get("schema_version") != 2 or jobs.get("kind") != "comic_panel_jobs":
        gaps.append(_gap(root, chapter, "image_jobs", "panel_jobs_schema_legacy", jobs_path, "panel_jobs 必须为 schema v2 正式出图合同。"))
    plan_ref = jobs.get("reference_plan") if isinstance(jobs.get("reference_plan"), Mapping) else {}
    if str(plan_ref.get("plan_sha256") or "") != str(plan.get("plan_sha256") or "") or str(plan_ref.get("inputs_fingerprint") or "") != str(plan.get("inputs_fingerprint") or ""):
        gaps.append(_gap(root, chapter, "image_jobs", "panel_jobs_reference_plan_stale", jobs_path, "panel_jobs 未消费当前 reference plan 指纹。"))
    panel_script = load_json(root / "脚本" / chapter / "panel_script.json") or {}
    expected = [str(item.get("panel_id")) for item in panel_script.get("panels") or [] if isinstance(item, Mapping) and item.get("panel_id")]
    actual = [str(item.get("panel_id")) for item in jobs.get("jobs") or [] if isinstance(item, Mapping) and item.get("panel_id")]
    if actual != expected or len(actual) != len(set(actual)):
        gaps.append(_gap(root, chapter, "image_jobs", "panel_jobs_coverage_mismatch", jobs_path, "panel_jobs 未唯一且按顺序覆盖 panel_script 全部格。"))
    plan_rows = {
        str(item.get("panel_id")): item
        for item in plan.get("panel_plans") or []
        if isinstance(item, Mapping) and item.get("panel_id")
    }
    stale_jobs: list[str] = []
    current_shas = {
        "identity_registry": sha256_file(root / "出图" / "共享" / "identity_registry.json"),
        "panel_script": sha256_file(root / "脚本" / chapter / "panel_script.json"),
        "layout": sha256_file(root / "排版" / chapter / "layout.json"),
    }
    for job in jobs.get("jobs") or []:
        if not isinstance(job, Mapping):
            continue
        pid = str(job.get("panel_id") or "?")
        consumed = job.get("consumed_contracts") if isinstance(job.get("consumed_contracts"), Mapping) else {}
        consumed_plan = consumed.get("reference_plan") if isinstance(consumed.get("reference_plan"), Mapping) else {}
        expected_panel_sha = str((plan_rows.get(pid) or {}).get("panel_plan_sha256") or "")
        if (
            str(consumed_plan.get("plan_sha256") or "") != str(plan.get("plan_sha256") or "")
            or str(consumed_plan.get("inputs_fingerprint") or "") != str(plan.get("inputs_fingerprint") or "")
            or str(consumed_plan.get("panel_plan_sha256") or "") != expected_panel_sha
            or not str(job.get("execution_input_sha256") or "")
        ):
            stale_jobs.append(pid)
            continue
        for key, digest in current_shas.items():
            record = consumed.get(key) if isinstance(consumed.get(key), Mapping) else {}
            if str(record.get("sha256") or "") != digest:
                stale_jobs.append(pid)
                break
        for reference in job.get("references") or []:
            if not isinstance(reference, Mapping) or not reference.get("path"):
                continue
            ref_path = Path(str(reference.get("path")))
            if not ref_path.is_absolute():
                ref_path = root / ref_path
            if str(reference.get("sha256") or "") != sha256_file(ref_path):
                stale_jobs.append(pid)
                break
    if stale_jobs:
        gaps.append(_gap(root, chapter, "image_jobs", "panel_jobs_stale", jobs_path, "出图合同或真实参考已过期：" + "、".join(dict.fromkeys(stale_jobs))))
    return gaps


def _gate_gap(root: Path, chapter: str, stage: str) -> dict[str, Any] | None:
    receipt_path = root / "生产数据" / "gate_receipts" / f"{stage}_{chapter}.json"
    receipt = load_json(receipt_path)
    stage_key = "image_jobs" if stage == "image_preflight" else stage
    if receipt is None:
        return _gap(root, chapter, stage_key, f"{stage}_gate_receipt_missing", receipt_path, f"缺当前 {stage} gate receipt；_进度.md 的勾选不能代替验收证据。", "comic-review")
    if receipt.get("kind") != "comic_gate_receipt" or receipt.get("stage") != stage or receipt.get("chapter") != chapter:
        return _gap(root, chapter, stage_key, f"{stage}_gate_receipt_invalid", receipt_path, f"{stage} gate receipt kind/stage/chapter 无效。", "comic-review")
    current_inputs = stage_inputs_fingerprint(root, chapter, stage)
    if str(receipt.get("inputs_fingerprint_sha256") or "") != str(current_inputs.get("sha256") or ""):
        return _gap(root, chapter, stage_key, f"{stage}_gate_receipt_stale", receipt_path, f"{stage} gate 后输入已变更，receipt 过期。", "comic-review")
    report_path = root / str(receipt.get("report_path") or Path("生产数据") / f"comic_gate_{stage}_{chapter}.json")
    if not report_path.is_file() or str(receipt.get("report_sha256") or "") != sha256_file(report_path):
        return _gap(root, chapter, stage_key, f"{stage}_gate_report_stale", report_path, f"{stage} gate report 缺失或与 receipt SHA 不匹配。", "comic-review")
    report = load_json(report_path)
    report_inputs = report.get("inputs_fingerprint") if isinstance(report, Mapping) and isinstance(report.get("inputs_fingerprint"), Mapping) else {}
    if (
        report is None
        or report.get("kind") != "comic_gate"
        or report.get("stage") != stage
        or report.get("chapter") != chapter
        or report.get("verdict") != receipt.get("verdict")
        or str(report_inputs.get("sha256") or "") != str(current_inputs.get("sha256") or "")
        or str(report_inputs.get("sha256") or "") != str(receipt.get("inputs_fingerprint_sha256") or "")
    ):
        return _gap(root, chapter, stage_key, f"{stage}_gate_report_stale", report_path, f"{stage} gate report 的合同、verdict 或输入指纹与 receipt 不一致。", "comic-review")
    if receipt.get("verdict") == "block":
        first = next((item for item in report.get("findings") or [] if isinstance(item, Mapping) and item.get("severity") == "block"), {})
        return_to = str(first.get("return_to_stage") or stage_key)
        skill = SKILL_FOR_STAGE.get(return_to, "comic-review")
        reason = str(first.get("reason") or f"{stage} gate 仍有 block。")
        return _gap(root, chapter, return_to, f"{stage}_gate_block", report_path, reason, skill)
    if receipt.get("execution_authorized") is not True:
        return _gap(root, chapter, stage_key, f"{stage}_gate_execution_not_authorized", receipt_path, f"{stage} gate receipt 未明确授权继续执行。", "comic-review")
    return None


def repo_root(start: Path) -> Path:
    cur = start.resolve()
    for parent in (cur, *cur.parents):
        if (parent / "skills").is_dir() and (parent / "创作区").is_dir():
            return parent
    return start.resolve()


def parse_progress(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = []
    headers = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells:
            continue
        if cells[0] == "话":
            headers = cells
            in_table = True
            continue
        if in_table and set(cells[0]) <= {"-"}:
            continue
        if in_table and headers and len(cells) >= len(headers):
            rows.append(dict(zip(headers, cells)))
    return {"path": str(path), "rows": rows}


def is_done(value: str) -> bool:
    return value.strip() in DONE or value.strip().startswith("✅")


# 缩略分镜/name 是编辑阅读合同，不是可由“传统原稿流程=关闭”
# 绕过的装饰层。该设置只跳过 finishing（网点/黑场/效果线计划）。
TRADITIONAL_STAGES = ("原稿收尾",)
TRADITIONAL_OFF_VALUES = {"关闭", "off", "disabled", "false", "False"}


def row_stage_state(row: dict[str, str], stage: str) -> str:
    """'done' / 'pending' / 'absent'。

    旧进度表可能整列缺失（如早期 7 列表没有 缩略分镜/原稿收尾）；
    缺列表示"该阶段对此表不适用"，不能当作未完成卡死前沿。
    """
    aliases = STAGE_ALIASES.get(stage, (stage,))
    present = [alias for alias in aliases if alias in row]
    if not present:
        return "absent"
    return "done" if any(is_done(row.get(alias, "")) for alias in present) else "pending"


def stage_index(stage: str) -> int:
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return len(STAGE_ORDER)


def contract_gaps(
    root: Path,
    chapter: str,
    next_stage_label: str | None,
    *,
    traditional_off: bool = False,
) -> list[dict[str, Any]]:
    """Return deterministic structural blockers before the table's claimed frontier.

    ``_progress.md`` is only a claimed state.  Each completed stage must also
    have a current artifact/approval/gate receipt before a later stage is
    considered reachable.
    """
    next_key = STAGE_KEYS.get(next_stage_label or "")
    threshold = stage_index(next_key) if next_key else len(STAGE_ORDER)
    gaps: list[dict[str, Any]] = []
    if threshold <= stage_index("script"):
        return gaps

    chapter_gaps, contract = _chapter_contract_gaps(root, chapter)
    gaps.extend(chapter_gaps)
    blueprint = load_json(root / "脚本" / "split_blueprint.json")
    gaps.extend(_development_pack_gaps(root, chapter, blueprint))
    gaps.extend(_script_and_source_gaps(root, chapter, contract))

    if threshold > stage_index("name"):
        gaps.extend(_editorial_artifact_gaps(root, chapter, "name"))

    if threshold > stage_index("layout"):
        gaps.extend(_editorial_artifact_gaps(root, chapter, "layout"))

    if not traditional_off and threshold > stage_index("finishing"):
        gaps.extend(_finishing_gaps(root, chapter))

    # Identity/model-pack readiness is a prerequisite to compiling formal
    # image jobs, so it is checked when image_jobs is the next open stage too.
    if threshold >= stage_index("image_jobs"):
        gaps.extend(_identity_gaps(root, chapter))
    if threshold > stage_index("image_jobs"):
        gaps.extend(_reference_and_jobs_gaps(root, chapter))
    # A current downstream receipt is a transitive proof that its gate reran
    # all upstream checks.  Earlier receipts may legitimately stale because a
    # later runner updates jobs/reports/timestamps; requiring every historic
    # receipt to remain current would make a completed project impossible.
    latest_gate: str | None
    if threshold == stage_index("name"):
        latest_gate = "script"
    elif threshold == stage_index("layout"):
        latest_gate = "name"
    elif threshold == stage_index("finishing"):
        latest_gate = "layout"
    elif threshold == stage_index("image_jobs"):
        latest_gate = "layout" if traditional_off else "finishing"
    elif threshold == stage_index("image"):
        latest_gate = "image_preflight"
    elif threshold == stage_index("compose"):
        latest_gate = "image"
    elif threshold == stage_index("review"):
        latest_gate = "compose"
    elif threshold > stage_index("review"):
        latest_gate = "review"
    else:
        latest_gate = None
    if latest_gate:
        gate = _gate_gap(root, chapter, latest_gate)
        if gate:
            gaps.append(gate)
    return gaps


def has_identity_blocker(root: Path, chapter: str) -> tuple[bool, str]:
    jobs_path = root / "出图" / chapter / "prompt" / "panel_jobs.json"
    if not jobs_path.is_file():
        return False, ""
    try:
        data = json.loads(jobs_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, ""
    missing_refs = set()
    stale_panels = []
    for job in data.get("jobs") or []:
        refs = [ref for ref in job.get("references") or [] if isinstance(ref, dict) and ref.get("id")]
        if not refs:
            continue
        valid_ref_count = 0
        for ref in refs:
            raw = str(ref.get("path") or "").strip()
            if not raw:
                missing_refs.add(str(ref.get("id")))
                continue
            path = Path(raw)
            if not path.is_absolute():
                path = root / path
            if path.is_file():
                valid_ref_count += 1
            else:
                missing_refs.add(str(ref.get("id")))
        generated_count = int(job.get("reference_input_count") or 0)
        if job.get("status") == "ready" and valid_ref_count and generated_count < valid_ref_count:
            stale_panels.append(str(job.get("panel_id") or ""))
    if missing_refs:
        return True, "共享参考缺失：" + "、".join(sorted(missing_refs))
    if stale_panels:
        return True, "已出图未使用当前真实参考：" + "、".join(pid for pid in stale_panels if pid)
    return False, ""


def has_longline_identity_blocker(root: Path, chapter: str) -> tuple[bool, str]:
    identity_level = read_setting(root, "定妆级别", "长线专门定妆")
    if "长线" not in identity_level and "专门定妆" not in identity_level:
        return False, ""
    report_path = root / "生产数据" / f"comic_identity_report_{chapter}.json"
    if not report_path.is_file():
        return True, "长线专门定妆：缺少 comic-identity 报告"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True, "长线专门定妆：comic-identity 报告不可解析"
    missing = report.get("missing_character_views")
    if not isinstance(missing, dict):
        return False, ""
    blockers = {
        str(character): [str(view) for view in views]
        for character, views in missing.items()
        if isinstance(views, list) and views
    }
    if not blockers:
        return False, ""
    pieces = [f"{character} 缺 {','.join(views)}" for character, views in sorted(blockers.items())]
    return True, "长线专门定妆未补齐：" + "；".join(pieces)


def has_style_blocker(root: Path, chapter: str) -> tuple[bool, str, str]:
    report_path = root / "生产数据" / f"comic_style_consistency_{chapter}.json"
    if not report_path.is_file():
        return True, "缺少风格一致性报告，请先跑 comic-review/style_consistency", "comic-review"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True, "风格一致性报告不可解析，请重跑 comic-review/style_consistency", "comic-review"
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    block_count = int(summary.get("block_count") or 0)
    if block_count > 0:
        examples = [
            str(item.get("panel_id") or item.get("artifact") or item.get("code"))
            for item in report.get("findings") or []
            if isinstance(item, dict) and item.get("severity") == "block"
        ]
        suffix = "：" + "、".join(item for item in examples[:8] if item) if examples else ""
        return True, f"风格一致性仍有 {block_count} 个阻断{suffix}", "comic-image"
    return False, "", ""


def has_source_semantics_blocker(root: Path, chapter: str) -> tuple[bool, str]:
    panel_path = root / "脚本" / chapter / "panel_script.json"
    if not panel_path.is_file():
        return False, ""
    try:
        panel_script = json.loads(panel_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, ""
    meta = panel_script.get("source_semantics") if isinstance(panel_script.get("source_semantics"), dict) else {}
    source_path = root / str(meta.get("path") or Path("脚本") / chapter / "source_semantics.json")
    requires = bool(meta.get("requires_normalization"))
    if not source_path.is_file() and not requires:
        return False, ""
    try:
        report = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True, "source_semantics 缺失或不可解析"
    if report.get("requires_normalization") and report.get("status") != "pass":
        return True, "源语义归一化 gate 未通过"
    if not (report.get("requires_normalization") or requires):
        return False, ""
    fields = ["source_excerpt", "meaning_zh", "text_target", "adaptation_note"]
    missing = []
    for panel in panel_script.get("panels") or []:
        if not isinstance(panel, dict):
            continue
        miss = [field for field in fields if not str(panel.get(field) or "").strip()]
        if miss:
            missing.append(f"{panel.get('panel_id') or 'unknown'}({','.join(miss)})")
    if missing:
        return True, "panel 缺语义追溯字段：" + "；".join(missing[:8])
    return False, ""


def next_command_for(root: Path, chapter: str, front: Mapping[str, Any]) -> str:
    stage_key = STAGE_KEYS.get(str(front.get("next_stage") or ""), "")
    template = STAGE_NEXT_COMMAND.get(stage_key) or SKILL_NEXT_COMMAND.get(str(front.get("next_skill") or ""), "")
    if not template:
        return ""
    return template.format(root=root, ch=chapter)


# Primary artifact whose presence proves a stage produced real output.  Used to
# detect a table that *under-claims* (frontier left early while later artifacts
# already exist) — the mirror of the over-claim re-verification already done.
def downstream_artifacts_present(root: Path, chapter: str, after_stage_key: str) -> list[tuple[str, Path]]:
    threshold = stage_index(after_stage_key)
    candidates = [
        ("script", root / "脚本" / chapter / "panel_script.json"),
        ("name", root / "排版" / chapter / "name_board.json"),
        ("layout", root / "排版" / chapter / "layout.json"),
        ("finishing", root / "出图" / chapter / "finishing" / "finishing_plan.json"),
        ("image_jobs", root / "出图" / chapter / "prompt" / "panel_jobs.json"),
        ("compose", root / "排版" / chapter / "export_manifest.json"),
    ]
    present = [(key, path) for key, path in candidates if stage_index(key) > threshold and path.is_file()]
    panels = root / "出图" / chapter / "panels"
    if stage_index("image") > threshold and panels.is_dir() and any(panels.glob("*.png")):
        present.append(("image", panels))
    return present


def under_claim_disclosure(root: Path, chapter: str, claimed_stage: str | None) -> dict[str, Any] | None:
    """Surface (never auto-fix) a table whose frontier reads earlier than the
    artifacts on disk, so the user isn't silently sent back to square one."""
    claimed_key = STAGE_KEYS.get(claimed_stage or "", "")
    if claimed_key not in ("source", "script"):
        return None
    present = downstream_artifacts_present(root, chapter, claimed_key)
    if not present:
        return None
    labels = "、".join(f"{STAGE_LABELS.get(key, key)}({rel(root, path)})" for key, path in present)
    return {
        "chapter": chapter,
        "claimed_stage": claimed_stage,
        "present": [{"stage": key, "artifact": rel(root, path)} for key, path in present],
        "hint": (
            f"{chapter}: 表声明前沿仍在「{claimed_stage}」，但已存在下游产物：{labels}。"
            "请核对后把 _进度.md 推进到真实前沿（用对应 comic-* 阶段 --check 复核），否则这些产物可能是未登记的孤儿。"
        ),
    }


def summarize_project(root: Path) -> dict:
    progress = root / "_进度.md"
    parsed = parse_progress(progress)
    traditional_off = read_setting(root, "传统原稿流程", "启用").strip() in TRADITIONAL_OFF_VALUES
    fronts = []
    under_claim: list[dict[str, Any]] = []
    for row in parsed["rows"]:
        chapter = row.get("话", "未命名")
        next_stage = None
        next_skill = None
        for stage in ROUTE:
            if traditional_off and stage in TRADITIONAL_STAGES:
                continue
            state = row_stage_state(row, stage)
            if state == "absent":
                continue
            if state != "done":
                next_stage = stage
                next_skill = ROUTE[stage]
                break
        disclosure = under_claim_disclosure(root, chapter, next_stage)
        if disclosure:
            under_claim.append(disclosure)
        blockers = contract_gaps(
            root,
            chapter,
            next_stage,
            traditional_off=traditional_off,
        )
        if blockers:
            first = blockers[0]
            fronts.append(
                {
                    "chapter": chapter,
                    "next_stage": first.get("stage_label") or "合同验收",
                    "next_skill": first.get("next_skill") or "comic-review",
                    "complete": False,
                    "reason": first.get("reason") or first.get("code"),
                    "blocker_code": first.get("code"),
                    "artifact": first.get("artifact"),
                    "blockers": blockers,
                    "progress_claim": {
                        "next_stage": next_stage or "完成",
                        "next_skill": next_skill or "comic-review",
                    },
                }
            )
            continue
        if next_stage not in (None, "源本/企划", "漫画脚本"):
            blocked, reason = has_source_semantics_blocker(root, chapter)
            if blocked:
                fronts.append(
                    {
                        "chapter": chapter,
                        "next_stage": "源语义归一化",
                        "next_skill": "comic-script",
                        "complete": False,
                        "reason": reason,
                    }
                )
                continue
        if next_stage in ("嵌字合成", "审查"):
            blocked, reason = has_identity_blocker(root, chapter)
            if blocked:
                fronts.append(
                    {
                        "chapter": chapter,
                        "next_stage": "一致性复核",
                        "next_skill": "comic-identity",
                        "complete": False,
                        "reason": reason,
                    }
                )
                continue
            blocked, reason = has_longline_identity_blocker(root, chapter)
            if blocked:
                fronts.append(
                    {
                        "chapter": chapter,
                        "next_stage": "专门定妆",
                        "next_skill": "comic-identity",
                        "complete": False,
                        "reason": reason,
                    }
                )
                continue
            blocked, reason, skill = has_style_blocker(root, chapter)
            if blocked:
                fronts.append(
                    {
                        "chapter": chapter,
                        "next_stage": "风格一致性复核" if skill == "comic-review" else "风格返修",
                        "next_skill": skill,
                        "complete": False,
                        "reason": reason,
                    }
                )
                continue
        fronts.append(
            {
                "chapter": chapter,
                "next_stage": next_stage or "完成",
                "next_skill": next_skill or "comic-review",
                "complete": next_stage is None,
                "blockers": [],
            }
        )
    for front in fronts:
        if not front.get("complete"):
            front["next_command"] = next_command_for(root, front.get("chapter", ""), front)
    return {
        "project": root.name,
        "root": str(root),
        "fronts": fronts,
        "under_claim_disclosures": under_claim,
        "review_verdict_disclosures": review_verdict_disclosures(root, parsed["rows"]),
    }


def review_verdict_disclosures(root: Path, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """叙事对账：`_进度.md` 勾了 ✅审查 的话，其 review receipt 的机检真相是什么。

    历史教训：review gate 实为 warn（0 block/133 warn）而进度叙事写「pass/
    内部验收通过」，完成度表述比机检结论乐观。本函数只披露、不改判定——
    ✅ 属于人审签收权限，但披露必须与叙事同屏。
    """
    out: list[dict[str, Any]] = []
    for row in rows:
        chapter = row.get("话", "")
        if not chapter or row_stage_state(row, "审查") != "done":
            continue
        receipt = load_json(root / "生产数据" / "gate_receipts" / f"review_{chapter}.json") or {}
        report = load_json(root / "生产数据" / f"comic_gate_review_{chapter}.json") or {}
        report_summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
        verdict = str(receipt.get("verdict") or "missing")
        if verdict in {"pass", ""}:
            continue
        block_count = report_summary.get("block_count")
        warn_count = report_summary.get("warn_count")
        out.append(
            {
                "chapter": chapter,
                "receipt_verdict": verdict,
                "block_count": block_count,
                "warn_count": warn_count,
                "hint": (
                    f"{chapter} 审查已勾 ✅ 但机检结论为 {verdict}"
                    + (f"（block {block_count} / warn {warn_count}）" if isinstance(warn_count, int) else "")
                    + "；进度叙事必须引用机检计数与签收依据，不得只写 pass。"
                ),
            }
        )
    return out


def find_projects(root: Path, args: argparse.Namespace) -> list[Path]:
    if args.projects:
        projects = []
        for item in args.projects:
            p = Path(item).expanduser().resolve()
            if p.is_file() and p.name == "_进度.md":
                p = p.parent
            if (p / "_进度.md").is_file():
                projects.append(p)
        return projects
    base = root / "创作区" / "画漫画"
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if (p / "_进度.md").is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描画漫画项目进度")
    parser.add_argument("projects", nargs="*", help="项目根或 _进度.md；不填则扫 创作区/画漫画")
    parser.add_argument("--root", default=None, help="仓库根")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else repo_root(Path.cwd())
    projects = find_projects(root, args)
    summaries = [summarize_project(p) for p in projects]

    if args.json:
        print(json.dumps({"projects": summaries}, ensure_ascii=False, indent=2))
        return 0

    if not summaries:
        print("未找到画漫画项目。可先运行：python3 skills/comic/scripts/init_project.py \"创作区/画漫画/作品名\" --title 作品名")
        return 0

    for summary in summaries:
        print(f"{summary['project']} — {summary['root']}")
        for front in summary["fronts"]:
            if front["complete"]:
                print(f"  {front['chapter']}: 主流程完成，建议 comic-review 做发布前复核")
            else:
                suffix = f"（{front['reason']}）" if front.get("reason") else ""
                print(f"  {front['chapter']}: 下一步 {front['next_stage']} → {front['next_skill']}{suffix}")
                if front.get("next_command"):
                    print(f"      运行: {front['next_command']}")
        for item in summary.get("under_claim_disclosures") or []:
            print(f"  [进度对账] {item['hint']}")
        for item in summary.get("review_verdict_disclosures") or []:
            print(f"  [叙事对账] {item['hint']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
