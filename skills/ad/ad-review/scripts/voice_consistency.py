#!/usr/bin/env python3
"""Deterministic role→voice_key and line-audio consistency audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def build(root: Path):
    root = root.resolve()
    manifest = load(root / "配音" / "时长清单.json", {}) or {}
    findings = []
    by_role = {}
    for line in manifest.get("lines") or manifest.get("items") or []:
        if not isinstance(line, dict):
            continue
        role = str(line.get("role") or "旁白")
        key = str(line.get("voice_key") or line.get("音色键") or "")
        by_role.setdefault(role, set()).add(key)
        rel = line.get("line_wav")
        if rel and not (root / str(rel)).is_file() and not (root / "配音" / str(rel)).is_file():
            findings.append({"severity": "block", "code": "line_audio_missing", "role": role,
                             "msg": f"登记逐句音频不存在：{rel}"})
    for role, keys in by_role.items():
        clean = {k for k in keys if k}
        if len(clean) > 1:
            findings.append({"severity": "block", "code": "voice_key_drift", "role": role,
                             "msg": f"同一角色/旁白跨句出现多个 voice_key：{sorted(clean)}"})
        if not clean:
            findings.append({"severity": "warn", "code": "voice_key_missing", "role": role,
                             "msg": "缺 voice_key，无法证明音色一致"})
    return {"schema_version": 1, "kind": "ad_voice_consistency",
            "roles": {k: sorted(v) for k, v in by_role.items()},
            "summary": {"block": sum(1 for f in findings if f["severity"] == "block"),
                        "warn": sum(1 for f in findings if f["severity"] == "warn")},
            "findings": findings}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project_root")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root)
    payload = build(root)
    out = root / "生产数据" / "voice_consistency.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# voice consistency block={payload['summary']['block']} warn={payload['summary']['warn']}")
    return 1 if payload["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
