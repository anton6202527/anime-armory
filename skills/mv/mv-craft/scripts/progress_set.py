#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mark one MV progress stage done.

Usage:
    python3 progress_set.py <制MV作品根> <stage_key> [--status "[x]"]
"""
import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import mv_utils
import completion
import progress


def main():
    ap = argparse.ArgumentParser(description="回写制MV项目 _进度.md 的某个阶段状态")
    ap.add_argument("project_root")
    ap.add_argument("stage_key")
    ap.add_argument("--status", default="[x]")
    ap.add_argument("--reviewer", default="", help="handoff 等具名完成态使用")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    try:
        requested_state = progress.state_of(args.status)
        if requested_state == "done" and args.stage_key in completion.OUTPUT_HEALTH_STAGES:
            completion.mark_stage_complete(
                root, args.stage_key, reviewer=args.reviewer, notes=args.notes,
            )
            changed = True
            effective_status = "[x]"
        else:
            # Persist one canonical done marker so alternate UI tokens cannot create
            # a second completion path with subtly different semantics.
            effective_status = "[x]" if requested_state == "done" else args.status
            changed = mv_utils.update_progress_stage(root, args.stage_key, effective_status)
            mv_utils.update_meta_flags(root)
    except KeyError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2
    if changed:
        print(f"[ok] _进度.md: {args.stage_key} -> {effective_status}")
    else:
        print(f"[warn] _进度.md 未找到 stage={args.stage_key} 对应行", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
