#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build novel semantic dependency graph and scoped invalidation plan."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
NOVEL_LIB = HERE.parents[1] / "_lib"
if str(NOVEL_LIB) not in sys.path:
    sys.path.insert(0, str(NOVEL_LIB))
from content_dependency import build_graph, invalidation_plan  # noqa: E402
from store import atomic_write_json  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project_root")
    ap.add_argument("--changed", action="append", default=[])
    ap.add_argument("--change-kind", choices=["prose_only", "state", "semantic", "structure"], default="semantic")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = str(Path(ns.project_root).resolve())
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    graph = build_graph(root)
    result: dict = {"graph": graph}
    if ns.changed:
        result["invalidation_plan"] = invalidation_plan(graph, ns.changed, change_kind=ns.change_kind)
    if ns.write:
        out = Path(root) / "生产数据"
        atomic_write_json(out / "content_dependency_graph.json", graph)
        if result.get("invalidation_plan"):
            atomic_write_json(out / "content_invalidation_plan.json", result["invalidation_plan"])
    print(json.dumps(result, ensure_ascii=False, indent=2) if ns.json else (
        f"nodes={len(graph['nodes'])} edges={len(graph['edges'])} affected={len((result.get('invalidation_plan') or {}).get('affected') or [])}"
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
