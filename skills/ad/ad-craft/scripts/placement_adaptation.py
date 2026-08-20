#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plan native creative adaptation per deliverable and placement.

An aspect-ratio row is not permission to center-crop a master.  This module
forces an explicit choice among native recrop/re-edit/variant and the narrowly
approved mechanical reframe path, then binds that choice to project-local
focus/shot plans and current placement safe-zone evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

import platform_pack
import render_profile


ALLOWED_MODES = {
    "native_master", "native_recrop", "native_reedit", "native_variant", "mechanical_reframe",
}
REPORT_REL = Path("生产数据") / "placement_adaptation.json"
RECEIPT_DIR = Path("生产数据") / "placement_adaptation_receipts"


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def sha256_file(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def item_sha(item: Mapping[str, Any]) -> str:
    return canonical_sha({key: value for key, value in item.items() if not str(key).startswith("_")})


def plan_sha(report: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in report.items()
               if key not in {"generated_at", "plan_sha256"} and not str(key).startswith("_")}
    return canonical_sha(payload)


def _project_file(root: Path, raw: Any) -> tuple[Optional[Path], str]:
    value = str(raw or "").strip()
    if not value:
        return None, ""
    path = Path(value)
    path = path if path.is_absolute() else root / path
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None, value
    return path.resolve(), rel


def _parse_progress_deliverables(text: str) -> list[Dict[str, str]]:
    rows: list[Dict[str, str]] = []
    active = False
    fields = ("label", "duration", "aspect", "kind", "spec", "status", "path")
    for line in text.splitlines():
        value = line.strip()
        if value.startswith("## "):
            active = "交付版本矩阵" in value
            continue
        if not active or not value.startswith("|"):
            continue
        cells = [cell.strip() for cell in value.strip("|").split("|")]
        if len(cells) < 7 or cells[0] in {"", "交付件"} or all(set(c) <= set("-: ") for c in cells):
            continue
        row = dict(zip(fields, cells[:7]))
        if row["kind"] == "master":
            did = "master"
        elif row["kind"] == "cutdown":
            did = "cut_" + row["duration"].lower()
        elif row["kind"] == "reframe":
            did = "reframe_" + row["aspect"].replace(":", "x")
        else:
            did = re.sub(r"[^0-9A-Za-z_.-]+", "_", row["label"]).strip("_") or "variant"
        rows.append({"deliverable_id": did, **row})
    return rows


def _deliverables(root: Path, pack: Mapping[str, Any]) -> list[Dict[str, Any]]:
    try:
        text = (root / "_进度.md").read_text(encoding="utf-8")
    except OSError:
        text = ""
    rows = _parse_progress_deliverables(text)
    if rows:
        return rows
    meta = load_json(root / "_meta.json", {}) or {}
    raw = meta.get("deliverables") or pack.get("deliverables") or []
    return [dict(row) for row in raw if isinstance(row, Mapping)]


def _config_for(brief: Mapping[str, Any], deliverable_id: str) -> Dict[str, Any]:
    table = brief.get("placement_adaptation_modes")
    if not isinstance(table, Mapping):
        return {}
    raw = table.get(deliverable_id)
    if isinstance(raw, str):
        return {"mode": raw}
    return dict(raw) if isinstance(raw, Mapping) else {}


def _storyboard_risk(root: Path) -> Dict[str, Any]:
    board = load_json(root / "脚本" / "storyboard.json", {}) or {}
    shots = board.get("shots") or board.get("clips") or []
    risky: list[str] = []
    missing_safe: list[str] = []
    for pos, shot in enumerate(shots, 1):
        if not isinstance(shot, Mapping):
            continue
        sid = str(shot.get("shot_id") or shot.get("clip_id") or f"S{pos}")
        text_bearing = any(shot.get(key) for key in (
            "subtitle", "text", "cta", "legal_lines", "disclosures", "claim_ids", "product_lock",
        ))
        if text_bearing:
            risky.append(sid)
        if text_bearing and not isinstance(shot.get("safe_area"), Mapping):
            missing_safe.append(sid)
    return {
        "shot_count": len([row for row in shots if isinstance(row, Mapping)]),
        "structural_risk_shots": risky,
        "missing_safe_area_shots": missing_safe,
        "requires_native_reedit": bool(missing_safe),
    }


def _evidence(root: Path, raw: Any, *, code: str, findings: list[Dict[str, Any]]) -> Dict[str, Any]:
    path, rel = _project_file(root, raw)
    digest = sha256_file(path) if path else None
    if not path or not digest:
        findings.append({"severity": "block", "code": code, "msg": f"缺项目内当前证据文件：{raw or '未填写'}"})
    return {"path": rel or str(raw or ""), "sha256": digest}


def _focus_plan_valid(payload: Any) -> bool:
    rows = payload.get("shots") if isinstance(payload, Mapping) else payload
    if not isinstance(rows, list) or not rows:
        return False
    for row in rows:
        if not isinstance(row, Mapping):
            return False
        try:
            start, end, x, y = (float(row[key]) for key in ("start", "end", "x", "y"))
        except (KeyError, TypeError, ValueError):
            return False
        if start < 0 or end <= start or not (0 <= x <= 1 and 0 <= y <= 1):
            return False
    return True


def _shot_plan_valid(payload: Any) -> bool:
    rows = payload.get("shots") if isinstance(payload, Mapping) else payload
    return bool(isinstance(rows, list) and rows and all(
        isinstance(row, Mapping) and row.get("shot_id") and
        (row.get("composition") or row.get("change") or row.get("instruction")) and
        (row.get("source_path") or row.get("input_path") or row.get("clip_path") or row.get("source_paths"))
        for row in rows
    ))


def _shot_plan_sources(payload: Any) -> list[str]:
    rows = payload.get("shots") if isinstance(payload, Mapping) else payload
    out: list[str] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, Mapping):
            continue
        raw = row.get("source_paths") or row.get("source_path") or row.get("input_path") or row.get("clip_path")
        values = raw if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) else [raw]
        for value in values:
            rel = str(value or "").strip()
            if rel and rel not in out:
                out.append(rel)
    return out


def evaluate(root: Path, deliverables: Optional[Sequence[Mapping[str, Any]]] = None) -> Dict[str, Any]:
    root = root.resolve()
    brief = load_json(root / "需求" / "brief.json", {}) or {}
    pack = platform_pack.build_pack(root)
    deliverables = ([dict(row) for row in deliverables] if deliverables is not None
                    else _deliverables(root, pack))
    master = next((row for row in deliverables if row.get("kind") == "master"), None)
    master_aspect = str((master or {}).get("aspect") or "")
    risk = _storyboard_risk(root)
    mapping = pack.get("deliverable_placements") or {}
    placement_specs = pack.get("placement_specs") or {}
    items: list[Dict[str, Any]] = []
    findings: list[Dict[str, Any]] = []

    if not deliverables:
        findings.append({"severity": "block", "code": "adaptation_deliverables_missing",
                         "msg": "缺交付矩阵，无法制定版位原生适配计划"})
    for row in deliverables:
        did = str(row.get("deliverable_id") or "")
        aspect = str(row.get("aspect") or "")
        kind = str(row.get("kind") or "")
        targets = mapping.get(did) or row.get("target_placements") or []
        if isinstance(targets, str):
            targets = [targets]
        targets = [str(v) for v in targets]
        if kind == "master" and aspect == master_aspect:
            recommended = "native_master"
        elif kind == "cutdown" and aspect == master_aspect:
            recommended = "native_reedit"
        elif risk["requires_native_reedit"]:
            recommended = "native_reedit"
        else:
            recommended = "native_recrop"
        config = _config_for(brief, did)
        automatic = "native_master" if recommended == "native_master" else (
            "native_reedit" if kind == "cutdown" and aspect == master_aspect else ""
        )
        needs_explicit_plan = not automatic
        selected = str(config.get("mode") or automatic).strip()
        row_findings: list[Dict[str, Any]] = []
        evidence: Dict[str, Any] = {}
        if selected not in ALLOWED_MODES:
            row_findings.append({"severity": "block", "code": "adaptation_mode_missing",
                                 "msg": f"{did} 须显式选择 native_recrop/native_reedit/native_variant/mechanical_reframe"})
        if selected == "native_master" and (kind != "master" or aspect != master_aspect):
            row_findings.append({"severity": "block", "code": "native_master_scope_invalid",
                                 "msg": f"{did} 不是原生母版，不能声明 native_master"})
        if needs_explicit_plan and selected in {"native_recrop", "mechanical_reframe", "native_reedit", "native_variant"}:
            if not str(config.get("approved_by") or "").strip():
                row_findings.append({"severity": "block", "code": "adaptation_approval_missing",
                                     "msg": f"{did} 缺具名 approved_by"})
            evidence["approval"] = _evidence(
                root, config.get("evidence_file"), code="adaptation_approval_evidence_missing",
                findings=row_findings,
            )
            if not targets:
                row_findings.append({"severity": "block", "code": "adaptation_placement_mapping_missing",
                                     "msg": f"{did} 未映射具体 placement，无法做原生安全区适配"})
            for placement in targets:
                spec = placement_specs.get(placement) or {}
                safe = str(spec.get("safe_zone_evidence") or "")
                safe_evidence = _evidence(root, safe, code="adaptation_safe_zone_evidence_missing",
                                          findings=row_findings)
                evidence.setdefault("safe_zones", {})[placement] = safe_evidence
        if needs_explicit_plan and selected in {"native_recrop", "mechanical_reframe"}:
            focus = _evidence(root, config.get("focus_plan_file"), code="adaptation_focus_plan_missing",
                              findings=row_findings)
            evidence["focus_plan"] = focus
            focus_path, _ = _project_file(root, focus.get("path"))
            if focus_path and focus_path.is_file() and not _focus_plan_valid(load_json(focus_path)):
                row_findings.append({"severity": "block", "code": "adaptation_focus_plan_malformed",
                                     "msg": f"{did} focus plan 须逐镜含 start/end/x/y 且焦点在 0..1"})
        if needs_explicit_plan and selected in {"native_reedit", "native_variant"}:
            shot = _evidence(root, config.get("shot_plan_file"), code="adaptation_shot_plan_missing",
                             findings=row_findings)
            evidence["shot_plan"] = shot
            shot_path, _ = _project_file(root, shot.get("path"))
            shot_payload = load_json(shot_path) if shot_path and shot_path.is_file() else None
            if shot_path and shot_path.is_file() and not _shot_plan_valid(shot_payload):
                row_findings.append({"severity": "block", "code": "adaptation_shot_plan_malformed",
                                     "msg": f"{did} native plan 须逐镜含 shot_id、制作指令与 source_path(s)"})
            native_sources = []
            for source_rel in _shot_plan_sources(shot_payload):
                native_sources.append(_evidence(
                    root, source_rel, code="adaptation_native_source_missing", findings=row_findings,
                ))
            evidence["native_sources"] = native_sources
            if not native_sources:
                row_findings.append({"severity": "block", "code": "adaptation_native_sources_missing",
                                     "msg": f"{did} 原生重剪/变体计划必须逐镜绑定真实源素材路径与 SHA"})
        if selected == "mechanical_reframe" and recommended == "native_reedit" and not str(config.get("risk_acceptance") or "").strip():
            row_findings.append({"severity": "block", "code": "mechanical_reframe_risk_unaccepted",
                                 "msg": f"{did} 含文字/产品/安全区结构风险；机械裁切须写 risk_acceptance，优先 native_reedit"})
        status = "approved" if not any(f["severity"] == "block" for f in row_findings) else "blocked"
        item = {
            "deliverable_id": did,
            "kind": kind,
            "source_aspect": master_aspect,
            "target_aspect": aspect,
            "target_placements": targets,
            "recommended_mode": recommended,
            "selected_mode": selected or None,
            "status": status,
            "approved_by": str(config.get("approved_by") or (
                "auto:original_master" if selected == "native_master" else
                "auto:deterministic_cutdown_pipeline" if automatic == "native_reedit" else ""
            )),
            "risk_acceptance": str(config.get("risk_acceptance") or ""),
            "evidence": evidence,
            "findings": row_findings,
        }
        items.append(item)
        for finding in row_findings:
            findings.append({**finding, "deliverable_id": did})

    pack_payload = {key: value for key, value in pack.items() if not str(key).startswith("_")}
    payload = {
        "schema_version": 1,
        "kind": "ad_placement_adaptation_plan",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root),
        "storyboard_risk": risk,
        "platform_pack_summary": pack.get("summary") or {},
        "input_sha256": {
            "需求/brief.json": sha256_file(root / "需求" / "brief.json"),
            "脚本/storyboard.json": sha256_file(root / "脚本" / "storyboard.json"),
            "生产数据/platform_pack.json": canonical_sha(pack_payload),
        },
        "items": items,
        "summary": {
            "block": sum(f["severity"] == "block" for f in findings),
            "warn": sum(f["severity"] == "warn" for f in findings),
            "approved": bool(items) and not any(f["severity"] == "block" for f in findings),
        },
        "findings": findings,
    }
    payload["plan_sha256"] = plan_sha(payload)
    return payload


def record_execution(root: Path, deliverable_id: str, actual_mode: str,
                     inputs: Sequence[str], output: str, executed_by: str,
                     note: str = "") -> Dict[str, Any]:
    root = root.resolve()
    report = write_report(root)
    item = next((row for row in report.get("items") or []
                 if str(row.get("deliverable_id")) == str(deliverable_id)), None)
    if not isinstance(item, Mapping):
        raise ValueError(f"未知 deliverable_id: {deliverable_id}")
    if item.get("status") != "approved":
        raise ValueError(f"{deliverable_id} placement adaptation 未批准")
    if actual_mode != item.get("selected_mode"):
        raise ValueError(f"actual_mode={actual_mode} 与 selected_mode={item.get('selected_mode')} 不一致")
    if not str(executed_by or "").strip():
        raise ValueError("execution receipt 必须有具名 executed_by")
    output_path, output_rel = _project_file(root, output)
    output_digest = sha256_file(output_path) if output_path else None
    if not output_path or not output_digest:
        raise ValueError(f"输出不存在或不在作品根内: {output}")
    input_rows = []
    for raw in inputs:
        path, rel = _project_file(root, raw)
        digest = sha256_file(path) if path else None
        if not path or not digest:
            raise ValueError(f"输入不存在或不在作品根内: {raw}")
        input_rows.append({"path": rel, "sha256": digest})
    if not input_rows:
        raise ValueError("execution receipt 至少绑定一个真实输入")
    if actual_mode in {"native_reedit", "native_variant"}:
        evidence = item.get("evidence") if isinstance(item.get("evidence"), Mapping) else {}
        native_sources = evidence.get("native_sources") if isinstance(evidence.get("native_sources"), list) else []
        expected_sources = {
            str(row.get("path") or ""): str(row.get("sha256") or "")
            for row in native_sources if isinstance(row, Mapping) and row.get("path")
        }
        actual_sources = {row["path"]: row["sha256"] for row in input_rows}
        if not expected_sources:
            raise ValueError("native_reedit/native_variant 缺 shot plan 绑定的真实源素材")
        missing = [path for path, digest in expected_sources.items() if actual_sources.get(path) != digest]
        if missing:
            raise ValueError(f"execution inputs 未消费 shot plan 当前源素材: {', '.join(missing)}")
    profile = render_profile.compile_profile(root)
    if int((profile.get("summary") or {}).get("block") or 0):
        raise ValueError("render_profile 仍有 block，拒绝签发 adaptation execution receipt")
    receipt = {
        "schema_version": 1,
        "kind": "ad_placement_adaptation_execution_receipt",
        "deliverable_id": str(deliverable_id),
        "actual_mode": actual_mode,
        "selected_mode": item.get("selected_mode"),
        "executed_by": str(executed_by).strip(),
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "inputs": input_rows,
        "output": {"path": output_rel, "sha256": output_digest},
        "adaptation_plan_sha256": report.get("plan_sha256"),
        "adaptation_item_sha256": item_sha(item),
        "render_profile_sha256": profile.get("profile_sha256"),
        "note": str(note or ""),
    }
    receipt["receipt_sha256"] = canonical_sha(receipt)
    path = root / RECEIPT_DIR / f"{deliverable_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt["_json_path"] = str(path)
    return receipt


def markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Placement adaptation plan", "",
        f"- approved: {str(bool((report.get('summary') or {}).get('approved'))).lower()}",
        f"- block: {(report.get('summary') or {}).get('block', 0)}", "",
        "| deliverable | source → target | recommended | selected | status |",
        "|---|---|---|---|---|",
    ]
    for row in report.get("items") or []:
        lines.append(
            f"| {row.get('deliverable_id')} | {row.get('source_aspect')} → {row.get('target_aspect')} | "
            f"{row.get('recommended_mode')} | {row.get('selected_mode') or '待选择'} | {row.get('status')} |"
        )
    if report.get("findings"):
        lines.extend(["", "## Findings", ""])
        lines.extend(f"- [{row.get('severity')}] {row.get('deliverable_id') or ''} {row.get('msg')}"
                     for row in report.get("findings") or [])
    return "\n".join(lines) + "\n"


def write_report(root: Path, out: Optional[Path] = None,
                 deliverables: Optional[Sequence[Mapping[str, Any]]] = None) -> Dict[str, Any]:
    report = evaluate(root, deliverables=deliverables)
    out = out or (root.resolve() / REPORT_REL)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    report["_json_path"] = str(out)
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="plan placement-native ad creative adaptation")
    ap.add_argument("project_root")
    ap.add_argument("--json", default=None)
    ap.add_argument("--record-execution", metavar="DELIVERABLE_ID")
    ap.add_argument("--actual-mode", choices=sorted(ALLOWED_MODES))
    ap.add_argument("--input", action="append", default=[])
    ap.add_argument("--output")
    ap.add_argument("--executed-by")
    ap.add_argument("--execution-note", default="")
    ns = ap.parse_args(argv)
    if ns.record_execution:
        if not ns.actual_mode or not ns.output or not ns.executed_by:
            ap.error("--record-execution 需同时提供 --actual-mode/--input/--output/--executed-by")
        try:
            receipt = record_execution(
                Path(ns.project_root), ns.record_execution, ns.actual_mode,
                ns.input, ns.output, ns.executed_by, ns.execution_note,
            )
        except ValueError as exc:
            print(f"[block] {exc}")
            return 1
        print(f"[ok] {receipt['_json_path']}")
        return 0
    report = write_report(Path(ns.project_root), Path(ns.json) if ns.json else None)
    print(f"# placement adaptation approved={report['summary']['approved']} block={report['summary']['block']}")
    return 1 if report["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
