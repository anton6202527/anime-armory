#!/usr/bin/env python3
"""Write a per-episode n2d production manifest.

The manifest is a lightweight provenance snapshot: it records the contract
version, production mode, stage scope, artifact paths, existence, and file
hashes where available.  It does not generate media.
"""
from __future__ import annotations

import argparse
import os
import sys

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from n2d_contract import stage_for_key, stage_specs, write_episode_manifest  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="作品根，例如 制漫剧/剧名")
    ap.add_argument("episode", help="集号，例如 第1集")
    ap.add_argument("--stage", default=None, help="只记录某个阶段 key；默认记录全阶段")
    ns = ap.parse_args(argv)

    if ns.stage and not stage_for_key(ns.stage):
        known = ", ".join(str(s["key"]) for s in stage_specs())
        print(f"未知 stage: {ns.stage}\n可选: {known}", file=sys.stderr)
        return 2
    path = write_episode_manifest(ns.root.rstrip("/"), ns.episode, stage=ns.stage)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
