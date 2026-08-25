#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect or record the single final-completion verdict for a novel release."""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NOVEL_LIB = os.path.abspath(os.path.join(HERE, "..", "..", "_lib"))
if NOVEL_LIB not in sys.path:
    sys.path.insert(0, NOVEL_LIB)

from completion_contract import accept_release, build_completion_verdict, write_completion_verdict  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["status", "accept"])
    ap.add_argument("project_root")
    ap.add_argument("--accepted-by", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = os.path.abspath(ns.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    try:
        if ns.command == "accept":
            accept_release(root, accepted_by=ns.accepted_by, note=ns.note)
        if ns.write or ns.command == "accept":
            write_completion_verdict(root)
        verdict = build_completion_verdict(root)
    except ValueError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2
    if ns.json:
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
    else:
        print(f"status={verdict['status']} complete={verdict['complete']} release_digest={verdict['release_digest']}")
        for blocker in verdict.get("blockers") or []:
            print(f"- block: {blocker}")
        for issue in (verdict.get("acceptance") or {}).get("issues") or []:
            print(f"- acceptance: {issue}")
    return 0 if verdict.get("complete") else 1


if __name__ == "__main__":
    raise SystemExit(main())
