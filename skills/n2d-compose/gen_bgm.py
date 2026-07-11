#!/usr/bin/env python3
"""Generate or register a generated BGM through a provider-neutral command adapter."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "n2d" / "_lib"
spec = importlib.util.spec_from_file_location("n2d_bgm_contract_core_for_generator", LIB / "bgm_contract.py")
assert spec is not None and spec.loader is not None
core = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = core
spec.loader.exec_module(core)


def target_duration(root: Path, episode: str) -> float:
    try:
        payload = json.loads((root / "脚本" / episode / "镜头时长.json").read_text(encoding="utf-8"))
        return round(sum(float(value) for value in payload.values()), 3)
    except Exception:
        return 0.0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("episode")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--register-existing", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    contract_file = core.contract_path(root, args.episode)
    contract = core.load(root, args.episode)
    source = contract.get("source") if isinstance(contract.get("source"), dict) else {}
    raw = str(source.get("file") or "")
    output = Path(raw) if Path(raw).is_absolute() else root / raw
    blockers = []
    if contract.get("kind") != core.KIND or contract.get("strategy") != "generated":
        blockers.append("bgm_contract 必须是 strategy=generated")
    if str(contract.get("status") or "").lower() not in {"confirmed", "approved", "ready"}:
        blockers.append("bgm_contract.status 必须 confirmed")
    if not raw or not source.get("model") or not source.get("channel"):
        blockers.append("source.file/model/channel 必填")
    duration = target_duration(root, args.episode)
    job = {
        "kind": "n2d_bgm_generation_job", "version": 1, "episode": args.episode,
        "duration_sec": duration, "model": source.get("model"), "channel": source.get("channel"),
        "output": str(output), "cues": contract.get("cues") or [], "mix": contract.get("mix") or {},
    }
    job_path = contract_file.with_name("bgm_generation_job.json")
    if not blockers:
        job_path.parent.mkdir(parents=True, exist_ok=True)
        job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.run and not blockers:
        template = os.environ.get("N2D_BGM_CMD", "").strip()
        if not template:
            blockers.append("缺 N2D_BGM_CMD；命令模板需使用 {job} 与 {out}")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            command = template.format(job=str(job_path), out=str(output), duration=duration)
            result = subprocess.run(shlex.split(command), check=False)
            if result.returncode != 0:
                blockers.append(f"BGM adapter 退出码 {result.returncode}")
    if (args.run or args.register_existing) and not output.is_file():
        blockers.append(f"输出文件不存在：{output}")
    receipt = None
    if (args.run or args.register_existing) and not blockers:
        receipt = {
            "kind": "n2d_bgm_generation_receipt", "version": 1, "status": "pass",
            "episode": args.episode, "registered_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "model": source.get("model"), "channel": source.get("channel"), "output": str(output),
            "output_sha256": core.sha256_file(output), "contract_sha256": core.sha256_file(contract_file),
            "mode": "generated" if args.run else "register_existing",
        }
        contract_file.with_name("bgm_generation_receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {"kind": "n2d_bgm_generation_result", "status": "block" if blockers else ("pass" if receipt else "planned"),
              "job": str(job_path) if job_path.is_file() else "", "receipt": receipt, "blockers": blockers}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"BGM {result['status']}: {job_path}")
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
