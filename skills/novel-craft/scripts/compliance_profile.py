#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build/update platform and jurisdiction compliance profile for a novel project."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import date


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LIB_PATH = os.path.join(REPO, "skills", "novel", "_lib", "compliance_profile.py")


def _load_lib():
    spec = importlib.util.spec_from_file_location("novel_compliance_profile_lib", LIB_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


cp = _load_lib()


def _confirm(root: str, req_id: str, *, note: str = "", by: str = "user-confirmed") -> None:
    existing = cp.load_existing_profile(root)
    confirmations = existing.get("confirmations")
    if not isinstance(confirmations, dict):
        confirmations = {}
    confirmations[req_id] = {
        "confirmed_at": date.today().isoformat(),
        "by": by,
        "note": note,
    }
    existing["confirmations"] = confirmations
    cp.write_json(cp.profile_path(root), existing)


def main() -> int:
    ap = argparse.ArgumentParser(description="生成/更新小说项目合规 profile")
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true", help="写入 合规/compliance_profile.json 和 .md")
    ap.add_argument("--json", action="store_true", help="打印完整 JSON")
    ap.add_argument("--confirm", action="append", default=[], help="确认某个 requirement id 已在平台/交付侧处理，可重复")
    ap.add_argument("--note", default="", help="配合 --confirm 写入确认备注")
    ap.add_argument("--by", default="user-confirmed", help="配合 --confirm 写入确认来源")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    for req_id in args.confirm:
        _confirm(root, req_id, note=args.note, by=args.by)
    profile = cp.build_profile(root)
    if args.write or args.confirm:
        json_path, md_path = cp.write_profile(root, profile)
        print(f"[ok] compliance profile JSON → {json_path}")
        print(f"[ok] compliance profile MD   → {md_path}")
    if args.json:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
    else:
        blockers, warnings = cp.gate_items(profile)
        print(f"[summary] blockers={len(blockers)} warnings={len(warnings)} requirements={len(profile.get('requirements') or [])}")
        for item in blockers:
            print(f"[block] {item['id']}: {item['reason']}")
        for item in warnings:
            print(f"[warn] {item['id']}: {item['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
