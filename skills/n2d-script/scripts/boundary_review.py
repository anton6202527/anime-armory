#!/usr/bin/env python3
"""Structured boundary review signoff for n2d-script stage 1.

`boundary_audit.py --strict` finds risky raw episode boundaries. This script
turns those risks into a machine-checkable signoff:

  python3 boundary_review.py draft <作品根> [start-end] --write
  python3 boundary_review.py check <作品根> [start-end] --json
  python3 boundary_review.py sign <作品根> <blocker_id> --decision keep \
      --notes "..." --reviewer "..." --semantic-evidence "..."

The review binds each blocker code to a two-sided boundary contract. Machine
drafts and human decisions are separate; mutating decisions require an applied
receipt with old/new hashes and source mapping.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import boundary_audit as BA  # noqa: E402
from n2d_settings import get_setting  # noqa: E402

KIND = "n2d_boundary_review"
VERSION = 2
REVIEW_REL = os.path.join("脚本", "boundary_review.json")
REVIEW_DRAFT_REL = os.path.join("脚本", "boundary_review_draft.json")
VALID_DECISIONS = {
    "keep",
    "merge_prev",
    "merge_next",
    "move_boundary",
    "split",
    "rewrite",
    "accept_risk",
}
MUTATING_DECISIONS = {"merge_prev", "merge_next", "move_boundary", "split", "rewrite"}
AUTOMATED_REVIEWER_RE = re.compile(
    r"^(?:auto(?:mated|mation)?|machine|system|agent|bot|ai|codex|claude|gpt|gemini|copilot)"
    r"(?:$|[-_:#/\s].*)",
    re.IGNORECASE,
)
AUTOMATED_REVIEWER_CN_RE = re.compile(r"^(?:自动|机器|系统|机器人|智能体)(?:$|[-_：:#/\s].*)")


def review_path(root: str) -> Path:
    return Path(root) / REVIEW_REL


def review_draft_path(root: str) -> Path:
    return Path(root) / REVIEW_DRAFT_REL


def normalize_ep(value: Any) -> Optional[int]:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group(0)) if m else None


def range_filter(rows: List[Dict[str, Any]], range_arg: Optional[str]) -> List[Dict[str, Any]]:
    if not range_arg:
        return rows
    m = re.match(r"(\d+)-(\d+)$", range_arg)
    if not m:
        raise ValueError("范围格式应为 start-end，例如 2-10")
    a, b = map(int, m.groups())
    return [r for r in rows if a <= int(r["ep"]) <= b]


def current_audit(root: str, range_arg: Optional[str] = None) -> Dict[str, Any]:
    genre = get_setting(root, "题材", "")
    monet = get_setting(root, "变现模式", "免费") or "免费"
    strong_re, conflict_re, payoff_re = BA.build_res(genre)
    all_rows = BA.load_rows(root, strong_re, conflict_re, payoff_re)
    rows = range_filter(all_rows, range_arg)
    per_ep, has_risk = BA.enrich_episode_rows(rows)
    policy = BA.load_paywall_policy(root, monet)
    arc = BA.series_arc(all_rows, monet, policy)
    blockers = BA.build_blockers(all_rows, per_ep, arc, scope_eps=[r["ep"] for r in rows])
    return {
        "genre": genre,
        "monetization": monet,
        "series_arc": arc,
        "all_rows": all_rows,
        "episodes": per_ep,
        "risk_episodes": [r for r in per_ep if r.get("risk")],
        "blockers": blockers,
        "has_risk": bool(blockers),
        "episode_heuristic_risk": has_risk,
        "series_arc_scope": "global",
    }


def load_review(root: str) -> Dict[str, Any]:
    path = review_path(root)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else {}


def _load_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else {}


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    """Replace one JSON document atomically without touching the machine draft."""
    path.parent.mkdir(parents=True, exist_ok=True)
    previous_mode = path.stat().st_mode & 0o777 if path.exists() else None
    tmp_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            tmp_name = fh.name
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        if previous_mode is not None:
            os.chmod(tmp_name, previous_mode)
        os.replace(tmp_name, path)
    except Exception:
        if tmp_name:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
        raise


def review_entries(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries = data.get("reviews")
    if isinstance(entries, list):
        return [e for e in entries if isinstance(e, dict)]
    # Compatibility for manually authored files.
    entries = data.get("episodes")
    if isinstance(entries, list):
        return [e for e in entries if isinstance(e, dict)]
    return []


def _entry_key(entry: Dict[str, Any]) -> Tuple[str, str]:
    blocker_id = str(entry.get("blocker_id") or "").strip()
    if blocker_id:
        return ("blocker_id", blocker_id)
    contract = entry.get("boundary_contract") if isinstance(entry.get("boundary_contract"), dict) else {}
    boundary_id = str(entry.get("boundary_id") or contract.get("boundary_id") or "").strip()
    code = str(entry.get("blocker_code") or entry.get("code") or "").strip()
    return (boundary_id, code)


def _reviewer_error(reviewer: Any) -> str:
    value = str(reviewer or "").strip()
    if not value:
        return "reviewer 不能为空"
    if AUTOMATED_REVIEWER_RE.match(value) or AUTOMATED_REVIEWER_CN_RE.match(value):
        return "reviewer 必须是可追责的人类审阅者，不能使用自动/agent/bot/system 身份"
    return ""


def _nonempty_evidence(value: Any) -> bool:
    if isinstance(value, (list, dict)):
        return bool(value)
    return bool(str(value or "").strip())


def _nonempty_mapping(value: Any) -> bool:
    return isinstance(value, (list, dict)) and bool(value)


def _contract_digest(contract: Dict[str, Any]) -> str:
    boundary_id = str(contract.get("boundary_id") or "")
    left_sha = str(contract.get("left_raw_sha256") or "")
    right_sha = str(contract.get("right_raw_sha256") or "")
    return hashlib.sha256(f"{boundary_id}\0{left_sha}\0{right_sha}".encode("utf-8")).hexdigest()


def _contract_errors(contract: Any, blocker_id: str) -> List[str]:
    if not isinstance(contract, dict) or not contract:
        return ["缺 boundary_contract"]
    errors: List[str] = []
    boundary_id = str(contract.get("boundary_id") or "").strip()
    expected_boundary = blocker_id.rsplit(":", 1)[0] if ":" in blocker_id else ""
    if not boundary_id or boundary_id != expected_boundary:
        errors.append("boundary_contract.boundary_id 与 blocker_id 不一致")
    if normalize_ep(contract.get("from_episode")) is None:
        errors.append("boundary_contract.from_episode 无效")
    if str(contract.get("contract_sha256") or "") != _contract_digest(contract):
        errors.append("boundary_contract.contract_sha256 与左右 raw SHA 不一致")
    return errors


def _exact_entry(data: Dict[str, Any], blocker_id: str, source: str) -> Optional[Dict[str, Any]]:
    matches = [e for e in review_entries(data) if str(e.get("blocker_id") or "").strip() == blocker_id]
    if len(matches) > 1:
        raise ValueError(f"{source} 中 blocker_id={blocker_id} 有重复记录，拒绝模糊签收")
    return matches[0] if matches else None


def _contract_for_boundary(audit: Dict[str, Any], old_contract: Dict[str, Any]) -> Dict[str, Any]:
    from_ep = normalize_ep(old_contract.get("from_episode"))
    if from_ep is None:
        raise ValueError("旧 boundary_contract 缺有效 from_episode")
    to_ep = normalize_ep(old_contract.get("to_episode"))
    return BA._boundary_contract(audit.get("all_rows") or [], from_ep, to_ep)


def _replace_exact_entry(data: Dict[str, Any], blocker_id: str, entry: Dict[str, Any]) -> None:
    entries = data.get("reviews")
    if not isinstance(entries, list):
        legacy = data.get("episodes")
        entries = list(legacy) if isinstance(legacy, list) else []
        data.pop("episodes", None)
        data["reviews"] = entries
    found = None
    for index, row in enumerate(entries):
        if isinstance(row, dict) and str(row.get("blocker_id") or "").strip() == blocker_id:
            if found is not None:
                raise ValueError(f"boundary_review.json 中 blocker_id={blocker_id} 有重复记录")
            found = index
    if found is None:
        entries.append(entry)
    else:
        entries[found] = entry


def record(
    root: str,
    blocker_id: str,
    *,
    decision: str,
    notes: str,
    reviewer: str,
    semantic_evidence: Any = None,
    source_mapping: Any = None,
    range_arg: Optional[str] = None,
) -> Dict[str, Any]:
    """Record one exact v2 blocker decision and atomically update the human file.

    Non-mutating decisions bind the current two-sided contract. Mutating
    decisions instead retain the prior contract and create an applied receipt
    from the raw files that already changed; this function never edits raw.txt.
    """
    root = root.rstrip("/")
    blocker_id = str(blocker_id or "").strip()
    decision = str(decision or "").strip()
    notes = str(notes or "").strip()
    reviewer = str(reviewer or "").strip()
    if not blocker_id:
        raise ValueError("blocker_id 不能为空，必须精确选择一条 blocker")
    if decision not in VALID_DECISIONS:
        raise ValueError(f"decision={decision!r} 无效；可选 {sorted(VALID_DECISIONS)}")
    if not notes:
        raise ValueError("notes 不能为空")
    reviewer_error = _reviewer_error(reviewer)
    if reviewer_error:
        raise ValueError(reviewer_error)
    if decision == "keep" and not _nonempty_evidence(semantic_evidence):
        raise ValueError("decision=keep 必须显式提供非空 semantic_evidence")
    if decision == "accept_risk":
        raise ValueError("boundary_review 的 blocker 均为 strict；accept_risk 不能签收 strict blocker")
    if decision in MUTATING_DECISIONS and not _nonempty_mapping(source_mapping):
        raise ValueError(f"decision={decision} 必须显式提供非空 source_mapping")

    human_data = load_review(root)
    machine_data = _load_json_file(review_draft_path(root))
    human_entry = _exact_entry(human_data, blocker_id, REVIEW_REL) if human_data else None
    machine_entry = _exact_entry(machine_data, blocker_id, REVIEW_DRAFT_REL) if machine_data else None
    audit = current_audit(root, range_arg)
    current_matches = [b for b in audit.get("blockers") or [] if str(b.get("blocker_id") or "") == blocker_id]
    if len(current_matches) > 1:
        raise ValueError(f"当前审计中 blocker_id={blocker_id} 重复，拒绝模糊签收")
    current_blocker = current_matches[0] if current_matches else None
    if human_entry is None and machine_entry is None and current_blocker is None:
        raise ValueError(f"未知 blocker_id={blocker_id}；先运行 draft --write 刷新候选")

    old_sources: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []
    for label, candidate in (("human", human_entry), ("machine", machine_entry)):
        if candidate is None:
            continue
        contract = candidate.get("boundary_contract")
        errors = _contract_errors(contract, blocker_id)
        if errors:
            raise ValueError(f"{label} 旧合同无效：{'；'.join(errors)}")
        old_sources.append((label, candidate, contract))

    if decision in MUTATING_DECISIONS:
        # The previous contract must come from an already materialized machine
        # or human review. A live blocker alone cannot prove the pre-edit SHA.
        if not old_sources:
            raise ValueError("改边界签收缺旧 machine/human boundary_contract；先在改 raw 前运行 draft --write")
        selected: Optional[Tuple[str, Dict[str, Any], Dict[str, Any], Dict[str, Any]]] = None
        for label, candidate, contract in old_sources:  # human is intentionally preferred
            current_contract = _contract_for_boundary(audit, contract)
            changed = (
                str(contract.get("left_raw_sha256") or "") != str(current_contract.get("left_raw_sha256") or "")
                or str(contract.get("right_raw_sha256") or "") != str(current_contract.get("right_raw_sha256") or "")
            )
            if changed:
                selected = (label, candidate, contract, current_contract)
                break
        if selected is None:
            raise ValueError("左右 raw SHA 均未变化；必须先真实修改 raw，再记录 mutation 决策")
        _, base_entry, signed_contract, current_contract = selected
    else:
        if current_blocker is None:
            raise ValueError(f"blocker_id={blocker_id} 已不在当前 strict blockers 中，不能记录 {decision}")
        current_contract = current_blocker.get("boundary_contract") or {}
        errors = _contract_errors(current_contract, blocker_id)
        if errors:
            raise ValueError(f"当前边界合同无效：{'；'.join(errors)}")
        matching = [item for item in old_sources if item[2].get("contract_sha256") == current_contract.get("contract_sha256")]
        if not matching:
            raise ValueError("machine/human boundary_contract 已陈旧；先运行 draft --write 刷新机器合同后再签")
        _, base_entry, signed_contract = matching[0]

    # Re-read the raw-derived contract immediately before writing, so a raw
    # edit racing with signoff cannot be silently paired with the wrong SHA.
    fresh_audit = current_audit(root, range_arg)
    fresh_contract = _contract_for_boundary(fresh_audit, signed_contract)
    if fresh_contract.get("contract_sha256") != current_contract.get("contract_sha256"):
        raise ValueError("签收过程中 raw 再次变化；本次未写入，请重新检查后签收")

    now = datetime.now(timezone.utc).isoformat()
    entry = dict(base_entry)
    entry.update({
        "blocker_id": blocker_id,
        "blocker_code": blocker_id.rsplit(":", 1)[-1],
        "boundary_contract": dict(signed_contract),
        "boundary_contract_sha256": str(signed_contract.get("contract_sha256") or ""),
        "decision": decision,
        "notes": notes,
        "reviewed_by": reviewer,
        "reviewed_at": now,
        "status": "signed",
    })
    if decision == "keep":
        entry["semantic_evidence"] = semantic_evidence
        entry["applied_receipt"] = {}
    elif decision in MUTATING_DECISIONS:
        entry["semantic_evidence"] = semantic_evidence if _nonempty_evidence(semantic_evidence) else {}
        entry["applied_receipt"] = {
            "status": "applied",
            "previous_boundary_contract_sha256": str(signed_contract.get("contract_sha256") or ""),
            "new_left_raw_sha256": str(current_contract.get("left_raw_sha256") or ""),
            "new_right_raw_sha256": str(current_contract.get("right_raw_sha256") or ""),
            "source_mapping": source_mapping,
            "recorded_by": reviewer,
            "recorded_at": now,
        }

    if human_data:
        output = dict(human_data)
    elif machine_data:
        output = dict(machine_data)
    else:
        output = {"reviews": []}
    output.update({
        "kind": KIND,
        "version": VERSION,
        "updated_at": now,
    })
    _replace_exact_entry(output, blocker_id, entry)
    _atomic_write_json(review_path(root), output)
    return {
        "ok": True,
        "review_path": str(review_path(root)),
        "blocker_id": blocker_id,
        "decision": decision,
        "entry": entry,
    }


def sign(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Public alias retained for callers that name the action `sign`."""
    return record(*args, **kwargs)


def _receipt_errors(entry: Dict[str, Any], current_contract: Dict[str, Any]) -> List[str]:
    receipt = entry.get("applied_receipt")
    if not isinstance(receipt, dict):
        return ["缺 applied_receipt"]
    errors = []
    if str(receipt.get("status") or "").lower() != "applied":
        errors.append("applied_receipt.status 必须为 applied")
    if str(receipt.get("new_left_raw_sha256") or "") != str(current_contract.get("left_raw_sha256") or ""):
        errors.append("new_left_raw_sha256 与当前左侧 raw 不一致")
    if current_contract.get("to_episode") is not None and (
        str(receipt.get("new_right_raw_sha256") or "") != str(current_contract.get("right_raw_sha256") or "")
    ):
        errors.append("new_right_raw_sha256 与当前右侧 raw 不一致")
    mapping = receipt.get("source_mapping")
    if not isinstance(mapping, (list, dict)) or not mapping:
        errors.append("缺非空 source_mapping（原 source span → 新集/新 span）")
    signed_contract = entry.get("boundary_contract") if isinstance(entry.get("boundary_contract"), dict) else {}
    if signed_contract:
        previous_sha = str(receipt.get("previous_boundary_contract_sha256") or "")
        if previous_sha != str(signed_contract.get("contract_sha256") or ""):
            errors.append("previous_boundary_contract_sha256 未绑定改动前边界合同")
        unchanged = (
            str(signed_contract.get("left_raw_sha256") or "") == str(current_contract.get("left_raw_sha256") or "")
            and str(signed_contract.get("right_raw_sha256") or "") == str(current_contract.get("right_raw_sha256") or "")
        )
        if unchanged:
            errors.append("左右 raw SHA 均未变化，不能把 rewrite/move/merge/split 记为已实施")
    return errors


def entry_is_signed(entry: Dict[str, Any], blocker: Optional[Dict[str, Any]] = None) -> bool:
    decision = str(entry.get("decision") or "").strip()
    status = str(entry.get("status") or "").strip().lower()
    notes = str(entry.get("notes") or entry.get("boundary_decision") or "").strip()
    if decision not in VALID_DECISIONS:
        return False
    if status in {"pending", "todo", "draft"}:
        return False
    # A decision without a human/agent note is not auditable enough to unlock
    # downstream generation. Keep the note short, but make the cut explicit.
    if not notes:
        return False
    if _reviewer_error(entry.get("reviewed_by") or entry.get("reviewer")):
        return False
    # `accept_risk` may acknowledge advisories, but must never unlock a strict
    # blocker. Blocker false positives should use `keep` with semantic notes.
    if decision == "accept_risk" and blocker is not None and blocker.get("severity") == "block":
        return False
    if decision == "keep" and blocker is not None:
        evidence = entry.get("semantic_evidence")
        if not ((isinstance(evidence, (list, dict)) and bool(evidence)) or str(evidence or "").strip()):
            return False
    if decision in MUTATING_DECISIONS and blocker is not None:
        return not _receipt_errors(entry, blocker.get("boundary_contract") or {})
    return True


def validate(root: str, range_arg: Optional[str] = None) -> Dict[str, Any]:
    audit = current_audit(root, range_arg)
    blockers = audit["blockers"]
    findings: List[Dict[str, Any]] = []
    path = review_path(root)
    data = load_review(root)
    entries = review_entries(data)
    by_key = {_entry_key(e): e for e in entries}

    # A successful edit can remove the original blocker. The mutation still
    # needs an applied receipt; otherwise simply changing raw would make the
    # blocker disappear and bypass the audit trail.
    current_blocker_ids = {str(b.get("blocker_id") or "") for b in blockers}
    scope_eps = {int(r["ep"]) for r in audit.get("episodes") or []}
    for entry in entries:
        decision = str(entry.get("decision") or "").strip()
        if decision not in MUTATING_DECISIONS or str(entry.get("blocker_id") or "") in current_blocker_ids:
            continue
        reviewer_error = _reviewer_error(entry.get("reviewed_by") or entry.get("reviewer"))
        if reviewer_error or not str(entry.get("notes") or "").strip():
            findings.append({
                "severity": "block",
                "code": "resolved_blocker_invalid_signer",
                "blocker_id": entry.get("blocker_id"),
                "message": (
                    f"原 blocker 已消失，但 mutation 签收不可追责："
                    f"{reviewer_error or 'notes 不能为空'}。"
                ),
            })
            continue
        old_contract = entry.get("boundary_contract") if isinstance(entry.get("boundary_contract"), dict) else {}
        from_ep = normalize_ep(old_contract.get("from_episode"))
        to_ep = normalize_ep(old_contract.get("to_episode"))
        if from_ep is None:
            findings.append({
                "severity": "block",
                "code": "mutation_receipt_missing_boundary_contract",
                "message": "改边界决策缺 from_episode/to_episode 双侧合同，无法验证是否实施。",
            })
            continue
        if range_arg and from_ep not in scope_eps and (to_ep is None or to_ep not in scope_eps):
            continue
        current_contract = BA._boundary_contract(audit.get("all_rows") or [], from_ep, to_ep)
        errors = _receipt_errors(entry, current_contract)
        if errors:
            findings.append({
                "severity": "block",
                "code": "resolved_blocker_missing_applied_receipt",
                "blocker_id": entry.get("blocker_id"),
                "message": f"原 blocker 已消失，但 decision={decision} 的实施收据无效：{'；'.join(errors)}。",
            })

    if not blockers:
        return {
            "ok": not findings,
            "review_path": str(path),
            "required": [],
            "findings": findings,
            "message": "boundary_audit 当前无高风险边界，历史改边界收据通过。" if not findings else "边界风险已消失，但实施收据未通过。",
        }
    if not data:
        findings.append({
            "severity": "block",
            "code": "missing_boundary_review",
            "message": f"缺 {REVIEW_REL}；先运行 boundary_review.py draft <作品根> --write 并填写 decision/notes。",
        })
    elif data.get("kind") not in {KIND, None}:
        findings.append({
            "severity": "block",
            "code": "bad_kind",
            "message": f"{REVIEW_REL} kind={data.get('kind')}，期望 {KIND}。",
        })

    required = []
    for blocker in blockers:
        contract = blocker.get("boundary_contract") or {}
        ep_num = int(contract.get("from_episode") or 0)
        ep_label = str(blocker.get("episode") or f"第{ep_num}集")
        required.append({
            "episode": ep_label,
            "blocker_id": blocker["blocker_id"],
            "blocker_code": blocker["code"],
            "boundary_contract": contract,
            "message": blocker["message"],
        })
        entry = by_key.get(("blocker_id", blocker["blocker_id"])) or by_key.get((contract.get("boundary_id", ""), blocker["code"]))
        if not entry:
            findings.append({
                "severity": "block",
                "code": "missing_blocker_review",
                "episode": ep_label,
                "blocker_id": blocker["blocker_id"],
                "message": f"{blocker['blocker_id']} 未在 {REVIEW_REL} 按 blocker code + 双侧边界合同签收。",
            })
            continue
        reviewer_error = _reviewer_error(entry.get("reviewed_by") or entry.get("reviewer"))
        if reviewer_error:
            findings.append({
                "severity": "block",
                "code": "invalid_boundary_reviewer",
                "episode": ep_label,
                "blocker_id": blocker["blocker_id"],
                "message": f"{blocker['blocker_id']} {reviewer_error}。",
            })
            continue
        decision = str(entry.get("decision") or "").strip()
        if decision == "accept_risk":
            findings.append({
                "severity": "block",
                "code": "accept_risk_advisory_only",
                "episode": ep_label,
                "blocker_id": blocker["blocker_id"],
                "message": f"{blocker['blocker_id']} 是 strict blocker；accept_risk 只能确认 advisory，不能放行。",
            })
            continue
        if decision in MUTATING_DECISIONS:
            receipt_errors = _receipt_errors(entry, contract)
            if receipt_errors:
                findings.append({
                    "severity": "block",
                    "code": "missing_applied_receipt",
                    "episode": ep_label,
                    "blocker_id": blocker["blocker_id"],
                    "message": f"{blocker['blocker_id']} 决策={decision} 但实施收据无效：{'；'.join(receipt_errors)}。",
                })
                continue
        else:
            signed_contract = entry.get("boundary_contract") if isinstance(entry.get("boundary_contract"), dict) else {}
            signed_sha = str(entry.get("boundary_contract_sha256") or signed_contract.get("contract_sha256") or "")
            if signed_sha != str(contract.get("contract_sha256") or ""):
                findings.append({
                    "severity": "block",
                    "code": "stale_boundary_review",
                    "episode": ep_label,
                    "blocker_id": blocker["blocker_id"],
                    "message": f"{blocker['blocker_id']} 左/右 raw 合同已变化，旧签收失效。",
                })
                continue
            if decision == "keep":
                evidence = entry.get("semantic_evidence")
                if not ((isinstance(evidence, (list, dict)) and bool(evidence)) or str(evidence or "").strip()):
                    findings.append({
                        "severity": "block",
                        "code": "missing_semantic_evidence",
                        "episode": ep_label,
                        "blocker_id": blocker["blocker_id"],
                        "message": f"{blocker['blocker_id']} decision=keep 需填写 semantic_evidence，不能只写泛化 notes。",
                    })
                    continue
        if not entry_is_signed(entry, blocker):
            findings.append({
                "severity": "block",
                "code": "unsigned_blocker_review",
                "episode": ep_label,
                "blocker_id": blocker["blocker_id"],
                "message": (
                    f"{blocker['blocker_id']} 签收未完成；decision 必须是 {sorted(VALID_DECISIONS)} 之一，"
                    "notes 需写明语义判定；改边界类决策还必须附 applied_receipt/new SHA/source_mapping。"
                ),
            })

    return {
        "ok": not any(f["severity"] == "block" for f in findings),
        "review_path": str(path),
        "required": required,
        "findings": findings,
        "message": "boundary_review 通过。" if not findings else "boundary_review 未通过。",
    }


def draft(root: str, range_arg: Optional[str] = None, write: bool = False) -> Dict[str, Any]:
    audit = current_audit(root, range_arg)
    path = review_path(root)
    old = load_review(root)
    old_by_key = {_entry_key(e): e for e in review_entries(old)}
    reviews: List[Dict[str, Any]] = []
    for blocker in audit["blockers"]:
        contract = blocker.get("boundary_contract") or {}
        ep_num = int(contract.get("from_episode") or 0)
        ep_label = str(blocker.get("episode") or f"第{ep_num}集")
        old_entry = old_by_key.get(("blocker_id", blocker["blocker_id"])) or old_by_key.get((contract.get("boundary_id", ""), blocker["code"]))
        # Machine draft mirrors current facts. Human decisions stay exclusively
        # in boundary_review.json and are never overwritten by continuation runs.
        reviews.append({
            "episode": ep_label,
            "blocker_id": blocker["blocker_id"],
            "blocker_code": blocker["code"],
            "blocker_message": blocker["message"],
            "boundary_contract": contract,
            "decision": str((old_entry or {}).get("decision") or "pending"),
            "notes": str((old_entry or {}).get("notes") or ""),
            "reviewed_by": str((old_entry or {}).get("reviewed_by") or ""),
            "reviewed_at": str((old_entry or {}).get("reviewed_at") or ""),
            "semantic_evidence": (old_entry or {}).get("semantic_evidence") or {},
            "applied_receipt": (old_entry or {}).get("applied_receipt") or {},
        })
    data = {
        "kind": KIND,
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": range_arg or "all",
        "source": "boundary_audit.py",
        "reviews": reviews,
    }
    if write:
        machine_path = review_draft_path(root)
        machine_path.parent.mkdir(parents=True, exist_ok=True)
        with machine_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        # First run bootstraps the human file. Later drafts never overwrite it.
        if not path.exists():
            with path.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
        data["machine_draft_path"] = str(machine_path)
        data["human_review_path"] = str(path)
    return data


def print_human(result: Dict[str, Any]) -> None:
    print(f"boundary_review: {'PASS' if result.get('ok') else 'BLOCK'}")
    print(result.get("message") or "")
    if result.get("review_path"):
        print(f"review_path: {result['review_path']}")
    for f in result.get("findings") or []:
        print(f"- {f.get('severity', 'info')}: {f.get('message')}")


def _json_cli_value(inline: Optional[str], file_arg: Optional[str], label: str) -> Any:
    if inline is not None and file_arg:
        raise ValueError(f"{label} 的 JSON 参数与文件参数不能同时使用")
    if file_arg:
        path = Path(file_arg)
        if not path.exists() or not path.is_file():
            raise ValueError(f"{label} 文件不存在：{path}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label} 文件不是有效 JSON：{exc}") from exc
    if inline is not None:
        try:
            return json.loads(inline)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label} 参数不是有效 JSON：{exc}") from exc
    return None


def _add_record_parser(sub: argparse._SubParsersAction, name: str) -> None:
    sp = sub.add_parser(name, help="原子记录一个精确 blocker_id 的人工决策")
    sp.add_argument("root")
    sp.add_argument("blocker_id")
    sp.add_argument("--decision", required=True, choices=sorted(VALID_DECISIONS))
    sp.add_argument("--notes", required=True)
    sp.add_argument("--reviewer", required=True)
    sp.add_argument("--semantic-evidence", help="keep 的非空语义证据（纯文本）")
    sp.add_argument("--semantic-evidence-json", help="keep 的 JSON 语义证据")
    sp.add_argument("--semantic-evidence-file", help="keep 的 JSON 语义证据文件")
    sp.add_argument(
        "--source-mapping-json",
        "--source-mapping",
        dest="source_mapping_json",
        help="mutation 的非空 JSON source mapping",
    )
    sp.add_argument("--source-mapping-file", help="mutation 的 JSON source mapping 文件")
    sp.add_argument("--range", dest="range_arg", help="可选审计范围 start-end")
    sp.add_argument("--json", action="store_true")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d boundary review structured signoff")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("draft", "check"):
        sp = sub.add_parser(name)
        sp.add_argument("root")
        sp.add_argument("range", nargs="?")
        sp.add_argument("--json", action="store_true")
        if name == "draft":
            sp.add_argument("--write", action="store_true")
    _add_record_parser(sub, "sign")
    _add_record_parser(sub, "record")
    ns = ap.parse_args(argv)
    try:
        if ns.cmd == "draft":
            data = draft(ns.root.rstrip("/"), ns.range, write=ns.write)
            if ns.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                print(f"drafted {len(data['reviews'])} risk episode review(s)")
                if ns.write:
                    print(f"wrote machine draft {review_draft_path(ns.root)}; human review preserved at {review_path(ns.root)}")
            return 0
        if ns.cmd in {"sign", "record"}:
            evidence_json = _json_cli_value(
                ns.semantic_evidence_json,
                ns.semantic_evidence_file,
                "semantic_evidence",
            )
            if ns.semantic_evidence is not None and evidence_json is not None:
                raise ValueError("semantic_evidence 文本、JSON 参数、JSON 文件只能选一种")
            evidence = evidence_json if evidence_json is not None else ns.semantic_evidence
            mapping = _json_cli_value(
                ns.source_mapping_json,
                ns.source_mapping_file,
                "source_mapping",
            )
            result = record(
                ns.root,
                ns.blocker_id,
                decision=ns.decision,
                notes=ns.notes,
                reviewer=ns.reviewer,
                semantic_evidence=evidence,
                source_mapping=mapping,
                range_arg=ns.range_arg,
            )
            if ns.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"recorded {result['blocker_id']} decision={result['decision']}")
                print(f"human review: {result['review_path']}")
            return 0
        result = validate(ns.root.rstrip("/"), ns.range)
        if ns.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_human(result)
        return 0 if result["ok"] else 1
    except Exception as exc:
        payload = {"ok": False, "findings": [{"severity": "block", "code": "exception", "message": str(exc)}]}
        if getattr(ns, "json", False):
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"boundary_review error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
