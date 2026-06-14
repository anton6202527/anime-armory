#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI wrapper for n2d project settings helpers.

This script is intentionally thin: the single source of truth for parsing,
validation, normalization, and record keeping remains `skills/n2d/_lib/settings.py`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Iterable, Optional


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REPO_SKILLS = os.path.abspath(os.path.join(SKILL_DIR, ".."))
COMMON = os.path.join(REPO_SKILLS, "n2d", "_lib")
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from settings import (  # noqa: E402
    audit_settings,
    reset_project_setting,
    set_project_setting,
    sync_global_settings,
    syncable_project_settings,
)


def setting_file(root: str) -> str:
    return os.path.join(os.path.abspath(root), "_设置.md")


def dump(data: Dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def parse_assignments(items: Iterable[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for raw in items:
        if "=" not in raw:
            raise SystemExit(f"sync-global 参数需为 选择点=值：{raw}")
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise SystemExit(f"sync-global 参数缺选择点名：{raw}")
        out[key] = value
    return out


def cmd_audit(args: argparse.Namespace) -> int:
    data = audit_settings(args.root)
    data["root"] = os.path.abspath(args.root)
    data["setting_file"] = setting_file(args.root)
    if args.json:
        dump(data, as_json=True)
    else:
        print(f"family={data['family']} settings={len(data['settings'])} errors={data['errors']} warnings={data['warnings']}")
        for row in data["rows"]:
            mark = row["level"]
            key = row.get("canonical_key") or row.get("key")
            msg = row.get("message", "")
            print(f"- {mark}: {key} = {row.get('value', '')} ({msg})")
    if data["errors"]:
        return 1
    if args.fail_on_warn and data["warnings"]:
        return 1
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    try:
        old, new = set_project_setting(
            args.root,
            args.key,
            args.value,
            record=not args.no_record,
            message=args.message,
            validate=not args.force,
        )
    except ValueError as exc:
        print(f"设置无效：{exc}", file=sys.stderr)
        return 2
    data = {
        "root": os.path.abspath(args.root),
        "setting_file": setting_file(args.root),
        "key": args.key,
        "old": old,
        "new": new,
        "recorded": not args.no_record,
        "forced": args.force,
    }
    if args.json:
        dump(data, as_json=True)
    else:
        print(f"已设置 {args.key}: {old or '（无）'} -> {new}")
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    old = reset_project_setting(args.root, args.key, record=not args.no_record)
    data = {
        "root": os.path.abspath(args.root),
        "setting_file": setting_file(args.root),
        "key": args.key,
        "old": old,
        "removed": old is not None,
        "recorded": bool(old is not None and not args.no_record),
    }
    if args.json:
        dump(data, as_json=True)
    else:
        if old is None:
            print(f"未找到设置 {args.key}")
        else:
            print(f"已重置 {args.key}: {old}")
    return 0 if old is not None else 1


def cmd_sync_global(args: argparse.Namespace) -> int:
    fields: Dict[str, str] = {}
    project_fields = syncable_project_settings(args.root)
    if args.all:
        fields.update(project_fields)
    for key in args.key or []:
        if key not in project_fields:
            raise SystemExit(f"项目中没有可同步设置：{key}")
        fields[key] = project_fields[key]
    fields.update(parse_assignments(args.assignments or []))
    if not fields:
        raise SystemExit("sync-global 需要 --all、--key，或 选择点=值")
    path = sync_global_settings(args.root, fields)
    data = {
        "root": os.path.abspath(args.root),
        "global_settings": path,
        "synced": fields,
    }
    if args.json:
        dump(data, as_json=True)
    else:
        print(f"已同步 {len(fields)} 项到 {path}")
        for key, value in fields.items():
            print(f"- {key}: {value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="n2d project settings manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    audit = sub.add_parser("audit", help="audit <作品根>/_设置.md")
    audit.add_argument("root")
    audit.add_argument("--json", action="store_true")
    audit.add_argument("--fail-on-warn", action="store_true")
    audit.set_defaults(func=cmd_audit)

    set_cmd = sub.add_parser("set", help="set one project setting")
    set_cmd.add_argument("root")
    set_cmd.add_argument("key")
    set_cmd.add_argument("value")
    set_cmd.add_argument("--force", action="store_true", help="allow unknown/experimental values")
    set_cmd.add_argument("--message", default=None, help="custom record message")
    set_cmd.add_argument("--no-record", action="store_true")
    set_cmd.add_argument("--json", action="store_true")
    set_cmd.set_defaults(func=cmd_set)

    reset = sub.add_parser("reset", help="remove one project setting")
    reset.add_argument("root")
    reset.add_argument("key")
    reset.add_argument("--no-record", action="store_true")
    reset.add_argument("--json", action="store_true")
    reset.set_defaults(func=cmd_reset)

    sync = sub.add_parser("sync-global", help="sync settings to 创作偏好-默认.md")
    sync.add_argument("root")
    sync.add_argument("assignments", nargs="*", help="optional 选择点=值 overrides")
    sync.add_argument("--all", action="store_true", help="sync all syncable project settings")
    sync.add_argument("--key", action="append", default=[], help="sync one existing project setting key")
    sync.add_argument("--json", action="store_true")
    sync.set_defaults(func=cmd_sync_global)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
