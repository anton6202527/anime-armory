#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings Manager - CLI for managing project _设置.md.

Implements reset, audit, sync, and get/set functionality for project preferences.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, Optional, Sequence

# Add common dir to path
SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = SCRIPT_DIR.parents[1]
COMMON_DIR = Path(__file__).resolve().parent  # 本线 _lib（settings.py 同目录兄弟）
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

try:
    import settings as common_settings
except ImportError:
    print("Error: cannot import 本线 _lib/settings.py", file=sys.stderr)
    raise


def cmd_reset(root: Path, key: Optional[str] = None, reset_all: bool = False) -> int:
    if not reset_all and not key:
        print("Error: Specify --key or --all to reset.", file=sys.stderr)
        return 1
    
    settings = common_settings.load_settings(str(root))
    if reset_all:
        old_keys = common_settings.reset_all_project_settings(str(root))
        print(f"Project settings at {root} have been fully reset. Removed: {', '.join(old_keys) or 'none'}")
    else:
        old_val = common_settings.reset_project_setting(str(root), key)
        if old_val is not None:
            print(f"Setting '{key}' has been removed from {root}/_设置.md.")
        else:
            print(f"Setting '{key}' not found in {root}/_设置.md.")
    
    return 0


def cmd_audit(root: Path) -> int:
    result = common_settings.audit_settings(str(root))
    print(f"--- Auditing settings for {root} (family={result['family']}) ---")
    for row in result["rows"]:
        level = row["level"]
        label = {"ok": "OK", "info": "INFO", "warn": "WARN", "error": "ERR"}.get(level, level.upper())
        suffix = f" ({row['message']})" if row.get("message") and row["message"] != "ok" else ""
        if row.get("expected"):
            suffix += " Expected one of: " + ", ".join(row["expected"])
        print(f"[{label}] {row['key']}: {row['value']}{suffix}")
    print(f"\nAudit complete: {result['errors']} errors, {result['warnings']} warnings, {result['infos']} metadata/info.")
    return 1 if result["errors"] > 0 else 0


def cmd_sync(root: Path, key: Optional[str] = None, sync_all: bool = False) -> int:
    settings = common_settings.load_settings(str(root))
    family = common_settings.detect_family(str(root))
    if key and sync_all:
        print("Error: use either --key or --all, not both.", file=sys.stderr)
        return 1
    if not key and not sync_all:
        print("Error: sync requires --key <KEY> or --all. Full sync is whitelist-only.", file=sys.stderr)
        return 1
    if key:
        spec = common_settings.get_setting_spec(key, family)
        canonical = common_settings.canonical_setting_key(key, family)
        if not spec or spec.metadata or not spec.syncable:
            print(f"Error: setting '{key}' is not syncable to global defaults.", file=sys.stderr)
            return 1
        if key not in settings and canonical not in settings:
            print(f"Error: setting '{key}' not found in project settings.", file=sys.stderr)
            return 1
        to_sync: Dict[str, str] = {canonical: settings.get(key, settings.get(canonical, ""))}
    else:
        to_sync = common_settings.syncable_project_settings(str(root))
    if not to_sync:
        print("No settings to sync.")
        return 0
    global_path = common_settings.sync_global_settings(str(root), to_sync)
    print(f"Synced {len(to_sync)} settings to {global_path}")
    common_settings.append_record(str(root), f"同步设置到全局默认: {', '.join(to_sync.keys())}")
    return 0


def cmd_get(root: Path, key: Optional[str] = None) -> int:
    settings = common_settings.load_settings(str(root))
    if key:
        if key in settings:
            print(f"{key}: {settings[key]}")
        else:
            print(f"'{key}' not set in project. Checking defaults...")
            val = common_settings.get_setting(str(root), key)
            print(f"{key}: {val} (inherited)")
    else:
        for k, v in sorted(settings.items()):
            print(f"- {k}: {v}")
    return 0


def cmd_set(root: Path, key: str, value: str, *, force: bool = False) -> int:
    if not force:
        result = common_settings.validate_project_setting(str(root), key, value)
        if result["level"] in ("warn", "error"):
            print(f"Error: {result['key']}: {result['message']}", file=sys.stderr)
            if result.get("expected"):
                print("Expected one of: " + ", ".join(result["expected"]), file=sys.stderr)
            print("Use --force only when this is an intentional custom setting.", file=sys.stderr)
            return 1
    old_val, _ = common_settings.set_project_setting(str(root), key, value, validate=not force)
    canonical = common_settings.canonical_setting_key(key, common_settings.detect_family(str(root)))
    print(f"Updated {canonical}: {old_val} -> {value}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Manage project _设置.md")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("reset")
    p.add_argument("root", type=Path)
    p.add_argument("--key", help="Key to reset")
    p.add_argument("--all", action="store_true", help="Reset all settings")

    p = sub.add_parser("audit")
    p.add_argument("root", type=Path)

    p = sub.add_parser("sync")
    p.add_argument("root", type=Path)
    p.add_argument("--key", help="Specific key to sync")
    p.add_argument("--all", action="store_true", help="Sync all whitelisted preference keys")

    p = sub.add_parser("get")
    p.add_argument("root", type=Path)
    p.add_argument("key", nargs="?", help="Specific key to get")

    p = sub.add_parser("set")
    p.add_argument("root", type=Path)
    p.add_argument("key")
    p.add_argument("value")
    p.add_argument("--force", action="store_true", help="write an unknown/custom setting without schema validation")

    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()
    
    if args.cmd == "reset":
        return cmd_reset(root, key=args.key, reset_all=args.all)
    elif args.cmd == "audit":
        return cmd_audit(root)
    elif args.cmd == "sync":
        return cmd_sync(root, key=args.key, sync_all=args.all)
    elif args.cmd == "get":
        return cmd_get(root, key=args.key)
    elif args.cmd == "set":
        return cmd_set(root, args.key, args.value, force=args.force)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
