#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI capability probe — capture `<cli> <command> --help` as ground-truth snapshots.

Why: the video backends' CLI flags drift (即梦/dreamina ships fast). The pipeline
must build args from the *live* CLI contract, not a hand-copied guess. This probe
runs `--help` (free, local, no credits), snapshots it to
`references/cli_snapshots/<cli>/<command>.txt`, parses the flag list, and reports
drift vs the previous snapshot.

Two modes:
  probe   (default) — capture all known commands, write snapshots + index, report drift.
  verify  — run live --help for one command, assert required flags exist, exit
            nonzero if any is missing. Cheap enough for video_runner to call before
            every submit ("每次都跑一遍"); a scheduled `probe` covers "定期跑一下".

Usage:
  python3 probe_cli.py probe  [--cli dreamina] [--bin /path/to/dreamina]
  python3 probe_cli.py verify --command multiframe2video --requires images,transition-prompt,transition-duration

Tests: cd skills/n2d-video/scripts && python -m pytest test_probe_cli.py
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
SNAP_ROOT = HERE.parent / "references" / "cli_snapshots"

# Per-CLI command sets worth tracking. Video stages depend on these flag contracts.
KNOWN_COMMANDS: Dict[str, List[str]] = {
    "dreamina": [
        "multiframe2video",
        "frames2video",
        "image2video",
        "multimodal2video",
        "text2video",
    ],
}

_FLAG_RE = re.compile(r"^\s+(?:-\w,\s+)?--([a-zA-Z0-9][\w-]*)\b")


def parse_flags(help_text: str) -> List[str]:
    """Extract long-flag names from a cobra-style --help block (the Flags section)."""
    flags: List[str] = []
    in_flags = False
    for line in help_text.splitlines():
        stripped = line.strip()
        if stripped.endswith("Flags:"):  # "Flags:" and "Global Flags:"
            in_flags = True
            continue
        if not in_flags:
            continue
        if stripped and not line.startswith((" ", "\t")):
            in_flags = False
            continue
        m = _FLAG_RE.match(line)
        if m and m.group(1) not in flags:
            flags.append(m.group(1))
    return flags


def resolve_bin(cli: str, explicit: Optional[str]) -> Optional[str]:
    if explicit:
        return explicit if Path(explicit).exists() else None
    return shutil.which(cli)


def run_help(binary: str, command: Optional[str]) -> Tuple[int, str]:
    argv = [binary] + ([command] if command else []) + ["--help"]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, f"[probe error] {exc}"
    # cobra prints help to stdout; some tools use stderr — take whichever is non-empty.
    return proc.returncode, (proc.stdout or proc.stderr or "").strip()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def snapshot_dir(cli: str) -> Path:
    return SNAP_ROOT / cli


def snapshot_path(cli: str, command: str) -> Path:
    return snapshot_dir(cli) / f"{command}.txt"


def index_path(cli: str) -> Path:
    return snapshot_dir(cli) / "_index.json"


def load_prev_index(cli: str) -> Dict[str, dict]:
    path = index_path(cli)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {c["command"]: c for c in data.get("commands", []) if isinstance(c, dict)}


def probe(cli: str, binary: Optional[str], *, when: Optional[str] = None) -> Dict:
    """Capture all known commands for `cli`; write snapshots + index; return report."""
    commands = KNOWN_COMMANDS.get(cli)
    if not commands:
        raise SystemExit(f"[err] unknown cli {cli!r}; known: {', '.join(KNOWN_COMMANDS)}")
    captured_at = when or now_iso()
    prev = load_prev_index(cli)
    out_dir = snapshot_dir(cli)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not binary:
        return {
            "cli": cli, "captured_at": captured_at, "available": False,
            "reason": f"{cli} CLI not found on PATH (probe skipped; existing snapshots kept)",
            "commands": [],
        }

    entries, drift = [], []
    for command in commands:
        code, text = run_help(binary, command)
        ok = code == 0 and "Usage:" in text
        flags = parse_flags(text) if ok else []
        if ok:
            snapshot_path(cli, command).write_text(
                f"# captured_at: {captured_at}\n# cli: {binary}\n# command: {command}\n\n{text}\n",
                encoding="utf-8")
        prev_flags = prev.get(command, {}).get("flags")
        if prev_flags is not None and ok and set(prev_flags) != set(flags):
            drift.append({
                "command": command,
                "added": sorted(set(flags) - set(prev_flags)),
                "removed": sorted(set(prev_flags) - set(flags)),
            })
        entries.append({"command": command, "ok": ok, "flags": flags,
                        "captured_at": captured_at if ok else prev.get(command, {}).get("captured_at")})

    index = {
        "kind": "n2d_cli_snapshot_index",
        "cli": cli, "binary": binary, "captured_at": captured_at,
        "available": True, "commands": entries, "drift": drift,
    }
    index_path(cli).write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def verify(cli: str, binary: Optional[str], command: str, requires: List[str]) -> Tuple[bool, str]:
    """Run live --help for one command; assert required flags exist. Cheap, no credits."""
    if not binary:
        return False, f"{cli} CLI not found on PATH; cannot verify {command}"
    code, text = run_help(binary, command)
    if code != 0 or "Usage:" not in text:
        return False, f"`{cli} {command} --help` failed (exit {code}); command missing or CLI broken"
    flags = set(parse_flags(text))
    missing = [f for f in requires if f not in flags]
    if missing:
        return False, (f"`{cli} {command}` is missing required flags: {', '.join(missing)} "
                       f"(live flags: {', '.join(sorted(flags))}); CLI contract changed — re-probe")
    return True, f"{cli} {command} ok ({len(flags)} flags)"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="CLI capability probe for video backends")
    sub = ap.add_subparsers(dest="mode")

    p = sub.add_parser("probe", help="capture all known commands for a CLI")
    p.add_argument("--cli", default="dreamina")
    p.add_argument("--bin", dest="binary", default=None, help="explicit CLI path; default = which(<cli>)")

    v = sub.add_parser("verify", help="assert one command exposes required flags (cheap pre-submit check)")
    v.add_argument("--cli", default="dreamina")
    v.add_argument("--bin", dest="binary", default=None)
    v.add_argument("--command", required=True)
    v.add_argument("--requires", default="", help="comma-separated long-flag names")

    args = ap.parse_args(argv)
    mode = args.mode or "probe"

    if mode == "probe":
        binary = resolve_bin(args.cli, args.binary)
        report = probe(args.cli, binary)
        if not report.get("available"):
            print(f"[skip] {report['reason']}")
            return 0
        print(f"[ok] probed {args.cli} @ {report['binary']} ({report['captured_at']})")
        for c in report["commands"]:
            mark = "ok " if c["ok"] else "ERR"
            print(f"  [{mark}] {c['command']:18s} {len(c['flags'])} flags")
        if report["drift"]:
            print("  ⚠️ CLI drift vs previous snapshot:")
            for d in report["drift"]:
                if d["added"]:
                    print(f"     {d['command']}: + {', '.join(d['added'])}")
                if d["removed"]:
                    print(f"     {d['command']}: - {', '.join(d['removed'])}")
        else:
            print("  no drift vs previous snapshot")
        return 0

    if mode == "verify":
        binary = resolve_bin(args.cli, args.binary)
        requires = [f.strip().lstrip("-") for f in args.requires.split(",") if f.strip()]
        ok, msg = verify(args.cli, binary, args.command, requires)
        print(("[ok] " if ok else "[err] ") + msg)
        return 0 if ok else 1

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
