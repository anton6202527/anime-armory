#!/usr/bin/env python3
"""Unified repair/preflight for n2d production boundaries.

This script intentionally stays deterministic: it scaffolds missing management
sidecars when requested, checks whether they are confirmed/fresh, and reports the
next repair command for expensive generation boundaries.

Usage:
  python3 skills/n2d/scripts/repair_preflight.py <作品根> 第N集 --stage image_preflight --write-missing --json
  python3 skills/n2d/scripts/repair_preflight.py <作品根> 第N集 --stage video_preflight --write-missing --repair-qc --json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
N2D_DIR = SCRIPT_DIR.parent
SKILLS_DIR = N2D_DIR.parent
LIB = N2D_DIR / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

try:
    from n2d_route import normalize_episode  # type: ignore
except Exception:  # pragma: no cover
    normalize_episode = lambda x: str(x or "").strip()  # type: ignore

try:
    from skill_snapshot import fingerprint_is_fresh  # type: ignore
except Exception:  # pragma: no cover
    fingerprint_is_fresh = None  # type: ignore

import preventive_contracts as preventive_contracts_module  # noqa: E402


KIND = "n2d_repair_preflight"
VERSION = 1
IMAGE_QC_STAGES = {"video_prompt", "video_prompt_preflight", "video", "video_preflight", "compose", "review"}
P3_STAGES = {"image_prompt", "image_prompt_preflight", "image", "image_preflight", "video_prompt", "video_prompt_preflight", "video", "video_preflight"}
LOCK_STAGES = {"image", "image_preflight", "video_prompt", "video_prompt_preflight", "video", "video_preflight", "compose", "review"}
PREVENTIVE_CONTRACT_STAGES = frozenset(preventive_contracts_module.STAGE_GATES)
# These are valid n2d frontiers, but their preventive-contract gate lives at a
# later boundary.  Keep the skip explicit; arbitrary/typo stages still block.
NO_PREVENTIVE_CONTRACT_STAGES = frozenset({"script_stage1", "voice"})


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def parse_json(stdout: str) -> Dict[str, Any]:
    text = str(stdout or "").strip()
    if not text:
        return {}
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch not in "[{":
            continue
        try:
            obj, end = decoder.raw_decode(text[idx:])
        except Exception:
            continue
        if text[idx + end :].strip():
            continue
        return obj if isinstance(obj, dict) else {"items": obj}
    for idx in range(len(text) - 1, -1, -1):
        if text[idx] not in "{[":
            continue
        try:
            obj = json.loads(text[idx:])
            return obj if isinstance(obj, dict) else {"items": obj}
        except Exception:
            continue
    return {}


def run_cmd(name: str, cmd: Sequence[str], *, block_on_nonzero: bool = True) -> Dict[str, Any]:
    try:
        r = subprocess.run(list(cmd), capture_output=True, text=True)
    except Exception as exc:
        return {
            "step": name,
            "status": "block",
            "returncode": 127,
            "detail": f"{type(exc).__name__}: {exc}",
            "command": " ".join(str(x) for x in cmd),
        }
    payload = parse_json(r.stdout)
    detail = (r.stderr or r.stdout or "").strip()
    status = str(payload.get("status") or "").lower()
    if not status:
        status = "pass" if r.returncode == 0 else "block"
    if block_on_nonzero and r.returncode != 0:
        status = "block"
    if status in {"ok", "ready", "confirmed"}:
        status = "pass"
    return {
        "step": name,
        "status": "pass" if status == "pass" else "block" if status in {"block", "blocked"} else status,
        "returncode": r.returncode,
        "detail": detail[:800],
        "command": " ".join(str(x) for x in cmd),
        "payload": payload,
    }


def update_plan_check(root: Path, ep: str) -> Dict[str, Any]:
    script = SKILLS_DIR / "n2d-update" / "scripts" / "update_plan.py"
    if not script.is_file():
        return {"step": "update_plan", "status": "skip", "detail": "n2d-update/update_plan.py missing"}
    row = run_cmd("update_plan", [sys.executable, str(script), "check", str(root), ep, "--write-plan", "--json"], block_on_nonzero=False)
    payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
    if payload.get("rebuild_needed") or (isinstance(payload.get("source_drift"), Mapping) and payload["source_drift"].get("status") == "drift"):
        row["status"] = "block"
        row["detail"] = str(payload.get("plan_md") or row.get("detail") or "skill/source drift requires rebuild")
    elif row.get("returncode") == 0:
        row["status"] = "pass"
    return row


def production_breakdown_check(root: Path, ep: str, *, write_missing: bool) -> Dict[str, Any]:
    script = SKILLS_DIR / "n2d-script" / "scripts" / "production_breakdown.py"
    cmd = [sys.executable, str(script), str(root), ep, "check", "--json"]
    if write_missing:
        cmd.append("--write-missing")
    return run_cmd("production_breakdown", cmd)


def production_locks_check(root: Path, ep: str, stage: str, *, write_missing: bool) -> Dict[str, Any]:
    script = N2D_DIR / "scripts" / "production_locks.py"
    cmd = [sys.executable, str(script), str(root), ep, "check", "--stage", stage, "--json"]
    if write_missing:
        cmd.insert(5, "--write-missing")
        cmd.insert(6, "--write-check")
    return run_cmd("production_locks", cmd)


def preventive_contracts_check(root: Path, ep: str, stage: str, *, write_missing: bool) -> Dict[str, Any]:
    if stage in NO_PREVENTIVE_CONTRACT_STAGES:
        return {
            "step": "preventive_contracts",
            "status": "skip",
            "stage": stage,
            "detail": f"stage={stage} 无 preventive contract gate；首个适用边界为 script_stage2",
        }
    if stage not in PREVENTIVE_CONTRACT_STAGES:
        return {
            "step": "preventive_contracts",
            "status": "block",
            "stage": stage,
            "detail": f"未知 preventive contract stage={stage!r}；拒绝按空 gate 放行",
        }
    script = N2D_DIR / "scripts" / "preventive_contracts.py"
    cmd = [sys.executable, str(script), str(root), ep, "--stage", stage, "--json"]
    if write_missing:
        cmd.extend(["--write", "--write-missing"])
    row = run_cmd("preventive_contracts", cmd)
    payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
    if payload.get("status") == "blocked":
        row["status"] = "block"
    return row


def image_qc_status(root: Path, ep: str, *, repair_qc: bool) -> Dict[str, Any]:
    script = SKILLS_DIR / "n2d-image" / "scripts" / "image_qc.py"
    if repair_qc:
        row = run_cmd("image_qc_repair", [sys.executable, str(script), str(root), ep, "--json"], block_on_nonzero=False)
        row["repair_attempted"] = True
        if row.get("returncode") != 0:
            row["status"] = "block"
            return row
    path = root / "生产数据" / "image_qc" / ep / f"image_qc_{ep}.json"
    data = load_json(path)
    if not isinstance(data, Mapping):
        return {
            "step": "image_qc",
            "status": "block",
            "detail": f"缺 image_qc 报告：{path}",
            "command": f"python3 skills/n2d/n2d-image/scripts/image_qc.py \"{root}\" {ep} --json",
        }
    fresh: Optional[bool] = None
    if fingerprint_is_fresh is not None:
        try:
            fresh = fingerprint_is_fresh(data.get("inputs_fingerprint"), str(root))
        except Exception:
            fresh = None
    if fresh is not True:
        state = "stale" if fresh is False else "unknown"
        return {
            "step": "image_qc",
            "status": "block",
            "detail": f"image_qc 新鲜度={state}：旧报告不能证明当前图片一致",
            "path": str(path),
            "command": f"python3 skills/n2d/n2d-image/scripts/image_qc.py \"{root}\" {ep} --json",
        }
    env = data.get("qc_environment") if isinstance(data.get("qc_environment"), Mapping) else {}
    summary = data.get("summary") if isinstance(data.get("summary"), Mapping) else {}
    precision = str(env.get("precision_level") or "").lower()
    hard_blocks = int(summary.get("hard_blocks") or 0)
    verdict = str(summary.get("verdict") or "").lower()
    if precision != "full" or hard_blocks > 0 or verdict == "block":
        return {
            "step": "image_qc",
            "status": "block",
            "detail": f"image_qc 未放行：precision={precision or 'unknown'} hard_blocks={hard_blocks} verdict={verdict or 'unknown'}",
            "path": str(path),
        }
    return {"step": "image_qc", "status": "pass", "path": str(path)}


def build_report(root: Path, ep: str, stage: str, *, write_missing: bool, repair_qc: bool) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = [update_plan_check(root, ep)]
    if stage in P3_STAGES:
        rows.append(production_breakdown_check(root, ep, write_missing=write_missing))
    if stage in LOCK_STAGES:
        rows.append(production_locks_check(root, ep, stage, write_missing=write_missing))
    rows.append(preventive_contracts_check(root, ep, stage, write_missing=write_missing))
    if stage in IMAGE_QC_STAGES:
        rows.append(image_qc_status(root, ep, repair_qc=repair_qc))
    blocks = [r for r in rows if r.get("status") == "block"]
    warns = [r for r in rows if r.get("status") == "warn"]
    return {
        "kind": KIND,
        "version": VERSION,
        "generated_at": now_iso(),
        "root": str(root),
        "episode": ep,
        "stage": stage,
        "status": "block" if blocks else "warn" if warns else "pass",
        "summary": {
            "steps": len(rows),
            "block": len(blocks),
            "warn": len(warns),
            "pass": sum(1 for r in rows if r.get("status") == "pass"),
            "skip": sum(1 for r in rows if r.get("status") == "skip"),
        },
        "steps": rows,
        "next_when_blocked": [
            str(r.get("command") or r.get("detail") or r.get("step"))
            for r in blocks[:8]
        ],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--stage", required=True)
    ap.add_argument("--write-missing", action="store_true", help="补缺失的 P-3/lock/contract 草稿；草稿仍会 block，直到 confirmed")
    ap.add_argument("--repair-qc", action="store_true", help="视频链路发现 image_qc 缺失/过期时，先尝试重跑 image_qc")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).expanduser().resolve()
    ep = normalize_episode(ns.episode)
    report = build_report(root, ep, ns.stage, write_missing=ns.write_missing, repair_qc=ns.repair_qc)
    out = root / "生产数据" / f"repair_preflight_{ns.stage}_{ep}.json"
    write_atomic(out, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    report["path"] = str(out)
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"repair_preflight {ns.stage} {ep}: {report['status']} {report['summary']}")
        for row in report.get("steps") or []:
            print(f"- {row.get('step')}: {row.get('status')} {row.get('detail') or row.get('path') or ''}")
    return 1 if report["status"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
