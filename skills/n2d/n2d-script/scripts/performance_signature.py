#!/usr/bin/env python3
"""performance_signature.py — 角色表演签名脚手架/缺口报告。

脸、发、服锁住之后，核心角色还会因为“演法”漂移：站姿、眼神、惯用手势、微表情和说话节奏变成另一个人。
本脚本只读 `identity_registry.json`，生成缺口报告与可填模板，不直接改 registry。
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

KIND = "n2d_performance_signature_audit"
FIELDS = ("micro_expression", "gaze", "stance", "habitual_gesture", "speech_rhythm", "action_style")
CORE_RE = re.compile(r"全篇|全程|长线|核心|主角|女主|男主|主反派|常驻")


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def flatten(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(value or "")


def signature_missing(sig: Any) -> List[str]:
    if isinstance(sig, Mapping):
        return [field for field in FIELDS if not str(sig.get(field) or "").strip()]
    if isinstance(sig, str) and sig.strip():
        return []
    if isinstance(sig, list) and any(str(x or "").strip() for x in sig):
        return []
    return list(FIELDS)


def analyze(root: Path) -> Dict[str, Any]:
    path = root / "出图" / "共享" / "identity_registry.json"
    data = load_json(path)
    findings: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {
            "kind": KIND,
            "available": False,
            "findings": [{"severity": "warn", "code": "missing_identity_registry", "message": f"缺 {path}"}],
            "rows": [],
        }
    for char in data.get("characters") or []:
        if not isinstance(char, dict):
            continue
        cid = str(char.get("id") or "").strip()
        core = bool(CORE_RE.search(flatten({k: char.get(k) for k in ("name", "scope", "tier", "role")})))
        char_sig = char.get("performance_signature")
        for form in char.get("forms") or []:
            if not isinstance(form, dict):
                continue
            sig = form.get("performance_signature") or char_sig
            missing = signature_missing(sig)
            row = {
                "character_id": cid,
                "name": char.get("name"),
                "form": form.get("form") or "常态",
                "core": core,
                "ready": not missing,
                "missing_fields": missing,
            }
            rows.append(row)
            if core and missing:
                findings.append({
                    "severity": "warn",
                    "code": "core_form_missing_performance_signature",
                    "message": f"核心/长线角色 {cid}/{row['form']} 缺表演签名字段：" + "、".join(missing),
                    "character_id": cid,
                    "form": row["form"],
                })
    return {"kind": KIND, "available": True, "rows": rows, "findings": findings}


def render_md(report: Mapping[str, Any]) -> str:
    lines = [
        "# Performance Signature Audit",
        "",
        "| 角色 | 形态 | 核心 | 状态 | 缺字段 |",
        "|---|---|---|---|---|",
    ]
    for row in report.get("rows") or []:
        lines.append(
            f"| {row.get('character_id')} {row.get('name') or ''} | {row.get('form')} | "
            f"{'yes' if row.get('core') else 'no'} | {'ready' if row.get('ready') else 'missing'} | "
            f"{'、'.join(row.get('missing_fields') or []) or '-'} |"
        )
    lines += ["", "## 填写模板", ""]
    for row in report.get("rows") or []:
        if row.get("ready"):
            continue
        lines.append(f"### {row.get('character_id')}/{row.get('form')}")
        for field in FIELDS:
            lines.append(f"- {field}: ")
        lines.append("")
    findings = report.get("findings") or []
    if findings:
        lines += ["## Findings"]
        for f in findings:
            lines.append(f"- {str(f.get('severity') or 'info').upper()} [{f.get('code')}] {f.get('message')}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, report: Mapping[str, Any]) -> Tuple[Path, Path]:
    out = root / "生产数据"
    out.mkdir(parents=True, exist_ok=True)
    jp = out / "performance_signature_audit.json"
    mp = out / "performance_signature_scaffold.md"
    tmp = jp.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, jp)
    tmp_md = mp.with_suffix(".md.tmp")
    tmp_md.write_text(render_md(report), encoding="utf-8")
    os.replace(tmp_md, mp)
    return jp, mp


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 角色表演签名脚手架/缺口报告")
    ap.add_argument("root")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ns = ap.parse_args(argv)
    report = analyze(Path(ns.root).resolve())
    if ns.write:
        jp, mp = write_outputs(Path(ns.root).resolve(), report)
        report["outputs"] = {"json": str(jp), "md": str(mp)}
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_md(report))
    warn = any(f.get("severity") == "warn" for f in report.get("findings") or [])
    return 1 if (ns.strict and warn) else 0


if __name__ == "__main__":
    raise SystemExit(main())
