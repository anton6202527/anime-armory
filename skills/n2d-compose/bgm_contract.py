#!/usr/bin/env python3
"""Build/check the structured n2d BGM contract."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

_LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "n2d", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

_CORE_SPEC = importlib.util.spec_from_file_location("n2d_bgm_contract_core", os.path.join(_LIB, "bgm_contract.py"))
assert _CORE_SPEC is not None and _CORE_SPEC.loader is not None
_CORE = importlib.util.module_from_spec(_CORE_SPEC)
sys.modules[_CORE_SPEC.name] = _CORE
_CORE_SPEC.loader.exec_module(_CORE)
contract_path = _CORE.contract_path
load = _CORE.load
scaffold = _CORE.scaffold
validate = _CORE.validate
write_missing = _CORE.write_missing


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write-missing", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    if ns.write_missing:
        write_missing(ns.root, ns.episode)
    payload = load(ns.root, ns.episode) or scaffold(ns.root, ns.episode)
    issues = validate(ns.root, ns.episode, payload)
    result = {
        "kind": "n2d_bgm_contract_check",
        "episode": ns.episode,
        "status": "block" if issues else "pass",
        "contract_path": str(contract_path(ns.root, ns.episode)),
        "issues": issues,
        "contract": payload,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2) if ns.json else (
        f"{'⛔' if issues else '✓'} BGM contract {result['status']}: {result['contract_path']}"
    ))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
