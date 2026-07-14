#!/usr/bin/env python3
"""comic doctor: disclose local QA/production capability without mutating art.

The result separates deterministic contract support from optional visual
inspection dependencies.  A missing optional dependency is never reported as
"pass"; it is an explicit degraded/none capability with an installation hint.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = 1


def module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def capability(
    name: str,
    status: str,
    reason: str,
    *,
    install_hint: str = "",
    affects: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "reason": reason,
        "install_hint": install_hint,
        "affects": affects or [],
    }


def project_checks(root: Path | None) -> list[dict[str, Any]]:
    if root is None:
        return []
    checks: list[dict[str, Any]] = []
    for name, path in (
        ("settings", root / "_设置.md"),
        ("progress", root / "_进度.md"),
        ("identity_registry", root / "出图" / "共享" / "identity_registry.json"),
        ("model_pack_report", root / "生产数据" / "comic_model_pack_report.json"),
        ("split_blueprint", root / "脚本" / "split_blueprint.json"),
        ("development_signoff", root / "开发包" / "signoff.json"),
    ):
        checks.append(
            {
                "name": name,
                "status": "present" if path.is_file() else "missing",
                "path": str(path.relative_to(root)),
            }
        )
    for name, path in (
        ("model_pack_signoffs", root / "生产数据" / "comic_model_pack_signoffs"),
        ("gate_receipts", root / "生产数据" / "gate_receipts"),
    ):
        checks.append(
            {
                "name": name,
                "status": "present" if path.is_dir() else "missing",
                "path": str(path.relative_to(root)),
            }
        )
    return checks


def diagnose(root: Path | None = None) -> dict[str, Any]:
    pillow = module_available("PIL")
    imgutils = module_available("imgutils")
    repo_root = Path(__file__).resolve().parents[2]
    validators = [
        repo_root / "skills" / "comic-script" / "scripts" / "development_pack.py",
        repo_root / "skills" / "comic-name" / "scripts" / "build_name_board.py",
        repo_root / "skills" / "comic-layout" / "scripts" / "build_layout.py",
        repo_root / "skills" / "comic-finishing" / "scripts" / "build_finishing_plan.py",
        repo_root / "skills" / "comic-identity" / "scripts" / "model_pack.py",
        repo_root / "skills" / "comic-review" / "scripts" / "gate.py",
    ]
    contract_ready = all(path.is_file() for path in validators)
    capabilities = [
        capability(
            "contract_and_sha_validation",
            "full" if contract_ready else "none",
            "All stage contract validators and SHA receipt tools are available."
            if contract_ready
            else "One or more stage contract validators are missing.",
            affects=["script", "name", "layout", "finishing", "gate"],
        ),
        capability(
            "raster_metadata_and_contact_sheets",
            "full" if pillow else "degraded",
            "Pillow is available." if pillow else "Pillow is absent; only file/signature checks can run.",
            install_hint="Install Pillow in the active Python environment." if not pillow else "",
            affects=["panel_qc", "style_consistency", "contact_sheets"],
        ),
        capability(
            "anime_identity_embedding",
            "full" if imgutils else "degraded",
            "dghs-imgutils/CCIP is available." if imgutils else "CCIP identity embedding is unavailable; SHA-bound human review remains required.",
            install_hint="Install dghs-imgutils in an isolated environment for CCIP triage." if not imgutils else "",
            affects=["character_consistency"],
        ),
        capability(
            "multimodal_visual_judgement",
            "degraded",
            "The repository creates SHA-bound VLM task packets, but no proprietary model is assumed by the skill.",
            install_hint="Use a current multimodal agent to fill verdict packets, or complete the human review receipt.",
            affects=["character", "scene", "prop"],
        ),
        capability(
            "codex_cli_access",
            "full" if shutil.which("codex") else "none",
            "Codex CLI executable is visible; exact image model/capability still requires per-run adapter verification."
            if shutil.which("codex")
            else "Codex CLI executable is not visible; job packs remain usable with another configured channel.",
            affects=["optional_image_execution"],
        ),
    ]
    statuses = [item["status"] for item in capabilities]
    overall = "full" if all(status == "full" for status in statuses) else "degraded"
    return {
        "schema_version": VERSION,
        "kind": "comic_doctor",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        # Persisted reports must stay portable across machines/checkouts.  The
        # report already lives under the project root, so an absolute host path
        # adds no evidence and leaks workstation-specific state.
        "project_root": "." if root else "",
        "overall": overall,
        "capabilities": capabilities,
        "project_checks": project_checks(root),
        "policy": {
            "deterministic_missing_or_stale": "may_block",
            "uncalibrated_visual_metric": "warn_only",
            "degraded_visual_capability": "requires_current_sha_human_receipt_for_release",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="漫画生产能力/精度自检")
    parser.add_argument("project_root", nargs="?")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.project_root).expanduser().resolve() if args.project_root else None
    report = diagnose(root)
    if args.write:
        if root is None:
            parser.error("--write requires project_root")
        out = root / "生产数据" / "comic_doctor.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"comic doctor: overall={report['overall']}")
        for item in report["capabilities"]:
            print(f"- {item['status']:8s} {item['name']}: {item['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
