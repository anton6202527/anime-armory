#!/usr/bin/env python3
"""Machine-readable contract for the n2d pipeline (Facade).

Refactored 2026-06 to separate constants, schema, logic, and registry/filesystem logic.
This file remains for backward compatibility as the main entry point for the contract.
"""

from __future__ import annotations
import sys
import os

# Import everything from sub-modules to keep n2d_contract as a facade.
try:
    from n2d_const import *
    from n2d_schema import *
    from n2d_logic import *
    from n2d_registry import *
    from n2d_maintenance import *
except ImportError:
    from .n2d_const import *
    from .n2d_schema import *
    from .n2d_logic import *
    from .n2d_registry import *
    from .n2d_maintenance import *

if __name__ == "__main__":
    import argparse
    import json

    _parser = argparse.ArgumentParser(description="n2d contract maintenance")
    _sub = _parser.add_subparsers(dest="command", required=True)
    
    _mig_shared = _sub.add_parser("migrate-shared", help="把旧 出图/common/ 迁到 出图/共享/，消除双路径裂脑")
    _mig_shared.add_argument("root")
    _mig_shared.add_argument("--dry-run", action="store_true")
    
    _check_ver = _sub.add_parser("check-version", help="检查每集 manifest schema_version 是否落后于当前契约")
    _check_ver.add_argument("root")
    
    _mig_ver = _sub.add_parser("migrate-version", help="运行契约版本迁移脚手架并刷新每集 manifest")
    _mig_ver.add_argument("root")
    _mig_ver.add_argument("--dry-run", action="store_true")
    
    _args = _parser.parse_args()
    
    if _args.command == "migrate-shared":
        _result = migrate_legacy_shared_assets(_args.root, apply=not _args.dry_run)
        print(json.dumps(_result, ensure_ascii=False, indent=2))
        if _result.get("conflicts"):
            print("[warn] 存在同名冲突文件，已留在旧目录，请人工裁决后重跑。", file=sys.stderr)
            sys.exit(1)
            
    elif _args.command == "check-version":
        _result = contract_version_report(_args.root)
        print(json.dumps(_result, ensure_ascii=False, indent=2))
        if _result.get("status") != "current":
            sys.exit(1)
            
    elif _args.command == "migrate-version":
        _result = migrate_contract(_args.root, apply=not _args.dry_run)
        print(json.dumps(_result, ensure_ascii=False, indent=2))
