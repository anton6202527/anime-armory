#!/usr/bin/env python3
"""Deterministic cross-chapter continuity audit for comic chapter contracts.

The audit does not guess visual quality.  It checks declared state only:
previous exit must match the next entry, and every declared state mutation must
be represented by a structured transition with evidence in a panel.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


VERSION = 1


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def chapter_number(value: str) -> int:
    match = re.search(r"\d+", value)
    return int(match.group()) if match else 10**9


def flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {prefix or "$": value}
    out: dict[str, Any] = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(item, Mapping):
            out.update(flatten(item, path))
        else:
            out[path] = item
    return out


def state_entities(state: Any) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        return {}
    entities = state.get("entities")
    return copy.deepcopy(dict(entities)) if isinstance(entities, Mapping) else copy.deepcopy(dict(state))


def get_field(entities: Mapping[str, Any], entity_id: str, field: str) -> tuple[bool, Any]:
    current: Any = entities.get(entity_id)
    if current is None:
        return False, None
    for token in str(field).split("."):
        if not isinstance(current, Mapping) or token not in current:
            return False, None
        current = current[token]
    return True, current


def set_field(entities: dict[str, Any], entity_id: str, field: str, value: Any) -> None:
    current = entities.setdefault(entity_id, {})
    if not isinstance(current, dict):
        entities[entity_id] = {}
        current = entities[entity_id]
    tokens = [token for token in str(field).split(".") if token]
    for token in tokens[:-1]:
        child = current.setdefault(token, {})
        if not isinstance(child, dict):
            current[token] = {}
        current = current[token]
    if tokens:
        current[tokens[-1]] = value


def finding(severity: str, code: str, chapter: str, reason: str, *, panel_id: str = "") -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "chapter": chapter,
        "panel_id": panel_id,
        "artifact": f"脚本/{chapter}/panel_script.json",
        "reason": reason,
        "return_to_stage": "comic-script",
        "suggested_fix": "修正 chapter_contract 的 entry_state/continuity_delta/exit_state，并重签下游合同。",
        "evidence_family": "deterministic_state_contract",
    }


def binding_finding(severity: str, code: str, chapter: str, reason: str, *, panel_id: str = "") -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "chapter": chapter,
        "panel_id": panel_id,
        "artifact": f"脚本/{chapter}/panel_script.json",
        "reason": reason,
        "return_to_stage": "comic-script",
        "suggested_fix": "对齐 continuity_delta 与逐格 character_bindings（换装/形态/状态转移后，转移格之后的绑定要用新 ID），并重签下游合同。",
        "evidence_family": "deterministic_state_contract",
    }


# continuity_delta.field vocabulary → the panel binding dimension it constrains.
# Only these fields carry a *visual* binding that a rendered panel must honour;
# pure-narrative facts (hp/location/knows_secret/…) are audited for internal
# consistency elsewhere and never map to a binding.
BINDING_FIELD_TO_DIMENSION = {
    "outfit": "outfit_id",
    "outfit_id": "outfit_id",
    "costume": "outfit_id",
    "clothes": "outfit_id",
    "form": "form_id",
    "form_id": "form_id",
    "state": "state_id",
    "state_id": "state_id",
    "expression": "expression_id",
    "expression_id": "expression_id",
}


def _norm(value: Any) -> str:
    return str(value).strip()


def binding_dimension(field: str) -> str:
    return BINDING_FIELD_TO_DIMENSION.get(_norm(field).lower(), "")


def audit_delta_bindings(
    chapter: str,
    contract: Mapping[str, Any],
    ordered_panels: list[dict[str, Any]],
    declared_entity_ids: set[str],
) -> list[dict[str, Any]]:
    """Cross-check the declared state contract against per-panel bindings.

    This is the bridge between the two trust domains: continuity_audit proves
    entry+delta==exit *within* the state facts, and reference_planner proves each
    binding resolves *within* the registry — but nothing linked them, so a
    declared outfit transition at P010 could leave P011+ still bound to the old
    outfit while every check passed.

    Deterministic only.  A BLOCK means a drawn panel's binding uses a
    contract-known value that contradicts the piecewise state computed from
    entry_state + continuity_delta at that panel's position.  A value the state
    contract never names is a WARN (the contract vocabulary may not match the
    registry IDs), never a silent pass.
    """
    findings: list[dict[str, Any]] = []
    transitions = contract.get("continuity_delta")
    if not isinstance(transitions, list) or not ordered_panels:
        return findings
    entry_entities = state_entities(contract.get("entry_state"))
    index_of = {panel["panel_id"]: i for i, panel in enumerate(ordered_panels)}

    # --- entity_id / field validation (the free-text sub-hole) -------------
    seen_entity_issue: set[str] = set()
    for transition in transitions:
        if not isinstance(transition, Mapping):
            continue
        entity_id = _norm(transition.get("entity_id"))
        field = _norm(transition.get("field"))
        if not entity_id or entity_id in seen_entity_issue:
            continue
        dim = binding_dimension(field)
        if entity_id not in declared_entity_ids:
            seen_entity_issue.add(entity_id)
            findings.append(
                binding_finding(
                    "warn",
                    "continuity_transition_entity_unknown",
                    chapter,
                    f"continuity_delta 的 entity_id={entity_id!r} 既不是已登记资产，也不在 entry/exit_state 里（疑似写成显示名或拼写错误，将永远绑不到真实资产）。",
                )
            )
        elif dim and not entity_id.startswith(("CHAR_", "MON_", "BEAST_", "ANIMAL_")):
            seen_entity_issue.add(entity_id)
            findings.append(
                binding_finding(
                    "warn",
                    "continuity_transition_entity_not_bindable",
                    chapter,
                    f"continuity_delta 用绑定维度字段 {field!r} 声明 {entity_id!r} 的变化，但只有 CHAR_/MON_ 有逐格绑定，该转移无法在画面绑定上落实。",
                )
            )

    # --- group binding-mappable transitions by (entity_id, field) ----------
    groups: dict[tuple[str, str, str], list[tuple[int | None, Any, Any]]] = {}
    for transition in transitions:
        if not isinstance(transition, Mapping):
            continue
        entity_id = _norm(transition.get("entity_id"))
        field = _norm(transition.get("field"))
        dim = binding_dimension(field)
        if not entity_id or not dim:
            continue
        t_index = index_of.get(_norm(transition.get("panel_id")))
        groups.setdefault((entity_id, field, dim), []).append(
            (t_index, transition.get("from"), transition.get("to"))
        )

    for (entity_id, field, dim), items in groups.items():
        items = sorted([item for item in items if item[0] is not None], key=lambda item: item[0])
        if not items:
            continue
        entry_exists, entry_val = get_field(entry_entities, entity_id, field)
        known: set[str] = set()
        if entry_exists and entry_val is not None:
            known.add(_norm(entry_val))
        for _, from_val, to_val in items:
            if from_val is not None:
                known.add(_norm(from_val))
            if to_val is not None:
                known.add(_norm(to_val))
        start = _norm(entry_val) if entry_exists and entry_val is not None else _norm(items[0][1])

        drawn: set[str] = set()
        for panel in ordered_panels:
            binding = panel["bindings"].get(entity_id)
            if binding and binding.get(dim):
                drawn.add(_norm(binding.get(dim)))
        for t_index, _from_val, to_val in items:
            if to_val is not None and _norm(to_val) not in drawn:
                findings.append(
                    binding_finding(
                        "warn",
                        "continuity_transition_never_drawn",
                        chapter,
                        f"{entity_id}.{field} 声明变为 {to_val!r}，但本话没有任何格的 {dim} 绑定用到它（声明了却没画）。",
                        panel_id=ordered_panels[t_index]["panel_id"] if 0 <= t_index < len(ordered_panels) else "",
                    )
                )

        for i, panel in enumerate(ordered_panels):
            binding = panel["bindings"].get(entity_id)
            if not binding:
                continue
            val = _norm(binding.get(dim))
            if not val:
                continue
            exp_after = start
            exp_before = start
            for t_index, _from_val, to_val in items:
                if i >= t_index:
                    exp_after = _norm(to_val)
                if i > t_index:
                    exp_before = _norm(to_val)
            if val in {exp_after, exp_before}:
                continue
            if val in known:
                findings.append(
                    binding_finding(
                        "block",
                        "panel_binding_contradicts_state",
                        chapter,
                        f"{panel['panel_id']} 的 {entity_id} 绑定 {dim}={val!r} 与该格应处状态 {exp_after!r} 矛盾"
                        f"（由 entry_state + continuity_delta 推得；换装/转移后的格没有换用新 ID）。",
                        panel_id=panel["panel_id"],
                    )
                )
            else:
                findings.append(
                    binding_finding(
                        "warn",
                        "panel_binding_outside_state",
                        chapter,
                        f"{panel['panel_id']} 的 {entity_id} 绑定 {dim}={val!r} 不在本话状态合同声明的取值集内"
                        f"（continuity_delta 用词可能与 registry ID 不一致，无法机检其正确性）。",
                        panel_id=panel["panel_id"],
                    )
                )
    return findings


def compare_previous_exit(previous: Mapping[str, Any], current: Mapping[str, Any], chapter: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    prev_flat = flatten(state_entities(previous))
    current_flat = flatten(state_entities(current))
    for path in sorted(prev_flat):
        if path not in current_flat:
            findings.append(
                finding(
                    "block",
                    "chapter_entry_state_missing_previous_fact",
                    chapter,
                    f"本话 entry_state 静默丢失上一话 exit_state 的 {path}={prev_flat[path]!r}。",
                )
            )
        elif prev_flat[path] != current_flat[path]:
            findings.append(
                finding(
                    "block",
                    "chapter_entry_state_mismatch",
                    chapter,
                    f"上一话 exit_state 与本话 entry_state 在 {path} 不一致：{prev_flat[path]!r} != {current_flat[path]!r}。",
                )
            )
    return findings


def audit_chapter_contract(
    chapter: str,
    contract: Mapping[str, Any],
    panel_ids: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    entry = state_entities(contract.get("entry_state"))
    exit_state = state_entities(contract.get("exit_state"))
    transitions = contract.get("continuity_delta")
    if not isinstance(transitions, list):
        transitions = []

    computed = copy.deepcopy(entry)
    for index, transition in enumerate(transitions, 1):
        if not isinstance(transition, Mapping):
            findings.append(finding("block", "continuity_transition_invalid", chapter, f"continuity_delta[{index}] 不是对象。"))
            continue
        entity_id = str(transition.get("entity_id") or "").strip()
        field = str(transition.get("field") or "").strip()
        panel_id = str(transition.get("panel_id") or "").strip()
        reason = str(transition.get("reason") or "").strip()
        if not entity_id or not field or "from" not in transition or "to" not in transition or not panel_id or not reason:
            findings.append(
                finding(
                    "block",
                    "continuity_transition_fields_missing",
                    chapter,
                    f"continuity_delta[{index}] 必须有 entity_id/field/from/to/panel_id/reason。",
                    panel_id=panel_id,
                )
            )
            continue
        if panel_id not in panel_ids:
            findings.append(
                finding(
                    "block",
                    "continuity_transition_panel_missing",
                    chapter,
                    f"{entity_id}.{field} 的转移证据格 {panel_id} 不存在。",
                    panel_id=panel_id,
                )
            )
        exists, before = get_field(computed, entity_id, field)
        if exists and before != transition.get("from"):
            findings.append(
                finding(
                    "block",
                    "continuity_transition_from_mismatch",
                    chapter,
                    f"{entity_id}.{field} 声明 from={transition.get('from')!r}，但当前状态为 {before!r}。",
                    panel_id=panel_id,
                )
            )
        set_field(computed, entity_id, field, transition.get("to"))

    computed_flat = flatten(computed)
    exit_flat = flatten(exit_state)
    for path in sorted(computed_flat.keys() | exit_flat.keys()):
        if computed_flat.get(path) != exit_flat.get(path):
            findings.append(
                finding(
                    "block",
                    "chapter_exit_state_unexplained",
                    chapter,
                    f"continuity_delta 应得 {path}={computed_flat.get(path)!r}，exit_state 为 {exit_flat.get(path)!r}。",
                )
            )
    return findings, {"entry": entry, "computed_exit": computed, "declared_exit": exit_state}


def load_ordered_panels(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    ordered: list[dict[str, Any]] = []
    for panel in payload.get("panels") or []:
        if not isinstance(panel, Mapping):
            continue
        pid = _norm(panel.get("panel_id"))
        if not pid:
            continue
        bindings: dict[str, dict[str, str]] = {}
        for row in panel.get("character_bindings") or []:
            if not isinstance(row, Mapping):
                continue
            entity_id = _norm(row.get("character_id"))
            if not entity_id:
                continue
            bindings[entity_id] = {
                key: _norm(row.get(key))
                for key in ("form_id", "outfit_id", "expression_id", "state_id")
            }
        ordered.append({"panel_id": pid, "bindings": bindings})
    return ordered


def registry_entity_ids(root: Path) -> set[str]:
    registry = load_json(root / "出图" / "共享" / "identity_registry.json", {})
    assets = registry.get("assets") if isinstance(registry, Mapping) else None
    return set(assets.keys()) if isinstance(assets, Mapping) else set()


def audit(root: Path, *, through_chapter: str = "") -> dict[str, Any]:
    blueprint = load_json(root / "脚本" / "split_blueprint.json", {})
    blueprint_contracts = {
        str(item.get("chapter")): item
        for item in (blueprint.get("chapters") or [])
        if isinstance(item, Mapping) and item.get("chapter")
    } if isinstance(blueprint, Mapping) else {}
    registry_ids = registry_entity_ids(root)
    script_files = sorted(
        (root / "脚本").glob("第*话/panel_script.json"),
        key=lambda path: chapter_number(path.parent.name),
    )
    if through_chapter:
        ceiling = chapter_number(through_chapter)
        script_files = [path for path in script_files if chapter_number(path.parent.name) <= ceiling]
    findings: list[dict[str, Any]] = []
    chapters: list[dict[str, Any]] = []
    previous_exit: Mapping[str, Any] | None = None
    for path in script_files:
        chapter = path.parent.name
        payload = load_json(path, {})
        receipt = payload.get("chapter_contract") if isinstance(payload, Mapping) else None
        contract = blueprint_contracts.get(chapter)
        if contract is not None:
            if not isinstance(receipt, Mapping):
                findings.append(finding("block", "chapter_contract_receipt_missing", chapter, "panel_script 未绑定 split_blueprint 中的本话合同 SHA。"))
            else:
                expected_sha = canonical_sha256(contract)
                recorded_sha = str(receipt.get("chapter_contract_sha256") or "")
                if recorded_sha != expected_sha:
                    findings.append(
                        finding(
                            "block",
                            "chapter_contract_receipt_stale",
                            chapter,
                            f"panel_script 合同 SHA 不是当前本话 contract：{recorded_sha or '缺失'} != {expected_sha}。",
                        )
                    )
        elif isinstance(receipt, Mapping) and any(key in receipt for key in ("entry_state", "continuity_delta", "exit_state")):
            # Migration compatibility for pre-blueprint projects/tests that
            # embedded the whole state contract in panel_script.
            contract = receipt
        if not isinstance(contract, Mapping):
            findings.append(finding("warn", "chapter_contract_missing", chapter, "旧项目缺 chapter_contract，无法审计跨话状态。"))
            previous_exit = None
            continue
        if previous_exit is not None:
            findings.extend(compare_previous_exit(previous_exit, contract.get("entry_state") or {}, chapter))
        ordered_panels = load_ordered_panels(payload)
        panel_ids = {panel["panel_id"] for panel in ordered_panels}
        local_findings, state = audit_chapter_contract(chapter, contract, panel_ids)
        findings.extend(local_findings)
        declared_entity_ids = (
            registry_ids
            | set(state_entities(contract.get("entry_state")).keys())
            | set(state_entities(contract.get("exit_state")).keys())
        )
        findings.extend(
            audit_delta_bindings(chapter, contract, ordered_panels, declared_entity_ids)
        )
        chapters.append(
            {
                "chapter": chapter,
                "panel_script_path": str(path.relative_to(root)),
                "panel_script_sha256": sha256_file(path),
                "state": state,
            }
        )
        previous_exit = contract.get("exit_state") if isinstance(contract.get("exit_state"), Mapping) else None
    summary = {
        "chapters": len(chapters),
        "block": sum(item["severity"] == "block" for item in findings),
        "warn": sum(item["severity"] == "warn" for item in findings),
        "info": sum(item["severity"] == "info" for item in findings),
    }
    return {
        "schema_version": VERSION,
        "kind": "comic_continuity_audit",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "project_root": ".",
        "through_chapter": through_chapter,
        "summary": summary,
        "chapters": chapters,
        "findings": findings,
        "verdict": "block" if summary["block"] else "warn" if summary["warn"] else "pass",
    }


def write_report(root: Path, report: Mapping[str, Any]) -> tuple[Path, Path]:
    json_path = root / "生产数据" / "comic_continuity_audit.json"
    md_path = root / "生产数据" / "comic_continuity_audit.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# 漫画跨话连续性审计",
        "",
        f"- verdict: {report.get('verdict')}",
        f"- chapters: {(report.get('summary') or {}).get('chapters', 0)}",
        f"- block/warn: {(report.get('summary') or {}).get('block', 0)} / {(report.get('summary') or {}).get('warn', 0)}",
        "",
        "## Findings",
        "",
    ]
    for item in report.get("findings") or []:
        lines.append(f"- [{str(item.get('severity')).upper()}] {item.get('chapter')} {item.get('code')}: {item.get('reason')}")
    if not report.get("findings"):
        lines.append("- 无。")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="漫画跨话人物/道具/场景状态连续性审计")
    parser.add_argument("project_root")
    parser.add_argument("--through-chapter", default="")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.project_root).expanduser().resolve()
    report = audit(root, through_chapter=args.through_chapter)
    if args.write:
        write_report(root, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"verdict={report['verdict']} block={report['summary']['block']} "
            f"warn={report['summary']['warn']} chapters={report['summary']['chapters']}"
        )
    return 1 if args.strict and report["verdict"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
