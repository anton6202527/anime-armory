#!/usr/bin/env python3
"""Build the canonical derived episode lineage graph."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

# Load under an unambiguous module name: test runners may put this `scripts/`
# directory ahead of `_lib`, in which case plain `import episode_graph` would
# resolve this CLI shim recursively.
_SPEC = importlib.util.spec_from_file_location("n2d_episode_graph_impl", LIB / "episode_graph.py")
assert _SPEC is not None and _SPEC.loader is not None
episode_graph = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(episode_graph)
build = episode_graph.build
write = episode_graph.write
render_markdown = episode_graph.render_markdown
graph_path = episode_graph.graph_path
clip_id = episode_graph.clip_id


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    payload = episode_graph.build(Path(ns.root), ns.episode)
    if ns.write:
        payload["outputs"] = episode_graph.write(Path(ns.root), ns.episode, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else episode_graph.render_markdown(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
