#!/usr/bin/env python3
"""Verify that prompt text actually carries the script quality contract.

`script_contract_applied_*.json` is an audit receipt.  This verifier reads the
contract and prompt files directly, then checks that each Clip section contains
the Clip's dramatic function and audience effect, and that global retention /
audience-question entries are present in the prompt text.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

CONTRACT_KIND = "n2d_script_quality_contract"
VERIFY_KIND = "n2d_script_contract_verification"
VERSION = 1
SCOPES = ("出图", "出视频")

_HEADER_RE = re.compile(r"^##\s+.*(?:Clip|clip|镜头).*$", re.MULTILINE)
_DIGIT_RE = re.compile(r"(\d+)")
_DROP_RE = re.compile(r"[\s`*_#|:：;；,，.。!！?？()（）\[\]{}<>《》\"'“”‘’/\\\-]+")

RETENTION_KEYS = (
    "promise",
    "hook",
    "question",
    "payoff",
    "payoff_due",
    "status",
    "handling",
    "expected_next_handling",
    "承诺",
    "悬念",
    "问题",
    "兑现",
    "处理",
)
QUESTION_KEYS = (
    "question",
    "signal",
    "status",
    "expected_next_handling",
    "handling",
    "观众问题",
    "问题",
    "信号",
    "处理",
)
QUESTION_CLOSED_STATUSES = {"paid", "paid_or_progressed", "closed", "resolved", "done", "本集兑现", "本集兑现/推进"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def ep_label(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = _DIGIT_RE.search(text)
    return f"第{m.group(1)}集" if m else text


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def default_prompt(scope: str, ep: str) -> Path:
    if scope == "出图":
        return Path("出图") / ep / "prompt" / "01_分镜出图.md"
    return Path("出视频") / ep / "prompt" / "01_clips.md"


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        return " ".join(flatten(v) for v in value.values() if flatten(v))
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value if flatten(v))
    return str(value or "").strip()


def leaf_texts(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, Mapping):
        out: List[str] = []
        for v in value.values():
            out.extend(leaf_texts(v))
        return out
    if isinstance(value, list):
        out: List[str] = []
        for v in value:
            out.extend(leaf_texts(v))
        return out
    text = str(value or "").strip()
    return [text] if text else []


def keyed_texts(row: Mapping[str, Any], keys: Sequence[str]) -> List[str]:
    out: List[str] = []
    for key in keys:
        if key in row:
            out.extend(leaf_texts(row.get(key)))
    return unique_texts(out)


def unique_texts(values: Iterable[str], *, min_norm_len: int = 4) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        norm = normalize(text)
        if len(norm) < min_norm_len or norm in seen:
            continue
        seen.add(norm)
        out.append(text)
    return out


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text or "")).lower()
    return _DROP_RE.sub("", text)


def contains_text(haystack: str, needles: Sequence[str]) -> bool:
    normalized = normalize(haystack)
    return any(normalize(needle) in normalized for needle in needles if normalize(needle))


def clip_aliases(clip_id: str) -> List[str]:
    raw = str(clip_id or "").strip()
    aliases = {raw}
    m = (
        re.search(r"CLIP[_-]?(\d+)", raw, re.I)
        or re.search(r"镜头\s*(\d+)", raw, re.I)
        or _DIGIT_RE.search(raw)
    )
    if m:
        n = int(m.group(1))
        aliases.update({
            f"Clip_{n:02d}",
            f"Clip{n:02d}",
            f"Clip {n:02d}",
            f"Clip_{n}",
            f"Clip{n}",
            f"Clip {n}",
            f"镜头 {n}",
            f"镜头{n}",
        })
        if "EP" in raw.upper():
            ep_m = re.search(r"EP(\d+)", raw, re.I)
            if ep_m:
                aliases.add(f"EP{int(ep_m.group(1)):02d}_CLIP{n:02d}")
    return [a for a in aliases if a]


def prompt_sections(text: str) -> List[Dict[str, str]]:
    matches = list(_HEADER_RE.finditer(text))
    if not matches:
        return [{"header": "", "body": text, "text": text}]
    out: List[Dict[str, str]] = []
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        section = text[match.start():end]
        out.append({"header": match.group(0), "body": section, "text": section})
    return out


def section_for_clip(prompt_text: str, clip_id_value: str) -> str:
    aliases = clip_aliases(clip_id_value)
    for section in prompt_sections(prompt_text):
        if contains_text(section["text"], aliases):
            return section["text"]
    return prompt_text if contains_text(prompt_text, aliases) else ""


def finding(severity: str, scope: str, code: str, message: str, *, clip: str = "", field: str = "") -> Dict[str, Any]:
    row: Dict[str, Any] = {"severity": severity, "scope": scope, "code": code, "message": message}
    if clip:
        row["clip_id"] = clip
    if field:
        row["field"] = field
    return row


def _contract_path(root: Path, ep: str) -> Path:
    return root / "生产数据" / f"script_quality_contract_{ep}.json"


def load_contract(root: Path, ep: str) -> Mapping[str, Any]:
    path = _contract_path(root, ep)
    data = load_json(path)
    if not isinstance(data, Mapping) or data.get("kind") != CONTRACT_KIND:
        raise SystemExit(f"missing valid script quality contract: {path}")
    return data


def verify_scope(root: Path, ep: str, scope: str, *, prompt_rel: Optional[Path] = None,
                 contract: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    ep = ep_label(ep)
    if scope not in SCOPES:
        raise ValueError(f"unsupported scope: {scope}")
    contract = contract or load_contract(root, ep)
    contract_path = _contract_path(root, ep)
    prompt_rel = prompt_rel or default_prompt(scope, ep)
    prompt_path = prompt_rel if prompt_rel.is_absolute() else root / prompt_rel
    prompt_text = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    fields = contract.get("signable_fields") if isinstance(contract.get("signable_fields"), Mapping) else {}
    findings: List[Dict[str, Any]] = []

    if not prompt_path.is_file():
        findings.append(finding("block", scope, "prompt_missing", f"缺 prompt 文件：{prompt_path}"))
    else:
        for idx, row in enumerate(fields.get("clip_dramatic_functions") or [], start=1):
            if not isinstance(row, Mapping):
                continue
            cid = str(row.get("clip_id") or f"Clip_{idx:02d}")
            section = section_for_clip(prompt_text, cid)
            if not section:
                findings.append(finding("block", scope, "clip_section_missing", "prompt 中找不到该 Clip 的段落。", clip=cid))
                continue
            checks = (
                ("dramatic_function", row.get("dramatic_function")),
                ("audience_effect", row.get("audience_effect")),
            )
            for field_name, value in checks:
                candidates = unique_texts(leaf_texts(value))
                if candidates and not contains_text(section, candidates):
                    preview = flatten(value)[:120]
                    findings.append(
                        finding(
                            "block",
                            scope,
                            "clip_contract_field_missing",
                            f"{field_name} 未出现在该 Clip prompt 段：{preview}",
                            clip=cid,
                            field=field_name,
                        )
                    )

        ledger = fields.get("retention_promise_ledger")
        if isinstance(ledger, list):
            for idx, row in enumerate(ledger, start=1):
                if not isinstance(row, Mapping):
                    continue
                candidates = keyed_texts(row, RETENTION_KEYS)
                if candidates and not contains_text(prompt_text, candidates):
                    findings.append(
                        finding(
                            "block",
                            scope,
                            "retention_entry_missing",
                            f"留存承诺 R{idx:02d} 未出现在 prompt：{flatten(row)[:120]}",
                            field="retention_promise_ledger",
                        )
                    )

        qledger = fields.get("audience_question_ledger")
        questions = qledger.get("questions") if isinstance(qledger, Mapping) else []
        if isinstance(questions, list):
            for idx, row in enumerate(questions, start=1):
                if not isinstance(row, Mapping):
                    continue
                status = str(row.get("status") or "").strip()
                handling = str(row.get("expected_next_handling") or "").strip()
                if status in QUESTION_CLOSED_STATUSES or handling in QUESTION_CLOSED_STATUSES:
                    continue
                candidates = keyed_texts(row, QUESTION_KEYS)
                if candidates and not contains_text(prompt_text, candidates):
                    findings.append(
                        finding(
                            "block",
                            scope,
                            "audience_question_missing",
                            f"观众问题 Q{idx:02d} 未出现在 prompt：{flatten(row)[:120]}",
                            field="audience_question_ledger",
                        )
                    )

    blocks = sum(1 for f in findings if f.get("severity") == "block")
    warnings = sum(1 for f in findings if f.get("severity") == "warn")
    return {
        "kind": VERIFY_KIND,
        "version": VERSION,
        "episode": ep,
        "scope": scope,
        "verified_at": now_iso(),
        "status": "pass" if blocks == 0 else "block",
        "contract_path": str(contract_path.relative_to(root)),
        "contract_content_hash": str(contract.get("content_hash") or contract.get("contract_hash") or ""),
        "contract_file_sha256": sha256_file(contract_path) if contract_path.is_file() else "",
        "prompt_path": str(prompt_path.relative_to(root)) if prompt_path.is_relative_to(root) else str(prompt_path),
        "prompt_sha256": sha256_file(prompt_path) if prompt_path.is_file() else "",
        "summary": {
            "status": "pass" if blocks == 0 else "block",
            "blocks": blocks,
            "warnings": warnings,
            "checked_clips": len([r for r in fields.get("clip_dramatic_functions") or [] if isinstance(r, Mapping)]),
        },
        "findings": findings,
    }


def verify(root: Path, ep: str, scopes: Sequence[str]) -> Dict[str, Any]:
    ep = ep_label(ep)
    contract = load_contract(root, ep)
    scope_results = [verify_scope(root, ep, scope, contract=contract) for scope in scopes]
    findings = [f for result in scope_results for f in result.get("findings") or [] if isinstance(f, Mapping)]
    blocks = sum(1 for f in findings if f.get("severity") == "block")
    warnings = sum(1 for f in findings if f.get("severity") == "warn")
    return {
        "kind": VERIFY_KIND,
        "version": VERSION,
        "episode": ep,
        "verified_at": now_iso(),
        "status": "pass" if blocks == 0 else "block",
        "summary": {
            "status": "pass" if blocks == 0 else "block",
            "blocks": blocks,
            "warnings": warnings,
            "scopes": list(scopes),
        },
        "scopes": scope_results,
        "findings": findings,
    }


def render_md(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    lines = [
        "# script_contract_verify",
        "",
        f"- episode: {report.get('episode')}",
        f"- status: {summary.get('status')}",
        f"- blocks: {summary.get('blocks', 0)}",
        f"- warnings: {summary.get('warnings', 0)}",
        "",
        "| Severity | Scope | Clip | Field | Code | Message |",
        "|---|---|---|---|---|---|",
    ]
    for row in report.get("findings") or []:
        if not isinstance(row, Mapping):
            continue
        lines.append(
            f"| {row.get('severity')} | {row.get('scope')} | {row.get('clip_id', '-')} | "
            f"{row.get('field', '-')} | {row.get('code')} | {row.get('message')} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, ep: str, report: Mapping[str, Any]) -> List[Path]:
    ep = ep_label(ep)
    out = root / "生产数据"
    jp = out / f"script_contract_verification_{ep}.json"
    mp = out / f"script_contract_verification_{ep}.md"
    write_atomic(jp, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_atomic(mp, render_md(report))
    return [jp, mp]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Verify prompt consumption of script_quality_contract")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--scope", choices=[*SCOPES, "all"], default="all")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    ep = ep_label(ns.episode)
    scopes = list(SCOPES) if ns.scope == "all" else [ns.scope]
    report = verify(root, ep, scopes)
    if ns.write:
        write_outputs(root, ep, report)
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_md(report))
    return 1 if (report.get("summary") or {}).get("blocks", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
