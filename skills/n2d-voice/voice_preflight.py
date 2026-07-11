#!/usr/bin/env python3
"""CLI for voice casting plus no-WAV timing estimates."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "n2d" / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from voice_preproduction import (  # noqa: E402
    build_casting,
    casting_blockers,
    casting_path,
    load_voiceover,
    lock_role,
    normalize_episode,
    write_preproduction,
)


def _set_rough_progress(root: Path, ep: str) -> None:
    progress = Path(__file__).resolve().parents[1] / "n2d" / "progress.py"
    if progress.is_file() and (root / "_进度.md").is_file():
        subprocess.run([sys.executable, str(progress), "set", str(root), ep, "配音", "⏳rough"], check=False)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="n2d 声音选角 + 无 WAV 时间基准")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="生成/刷新选角表和 timing_estimate.json，不生成音频")
    prepare.add_argument("root")
    prepare.add_argument("episode")
    prepare.add_argument("--json", action="store_true")
    prepare.add_argument("--no-progress", action="store_true")

    check = sub.add_parser("check", help="检查该集角色是否已满足最终/导引音轨签收条件")
    check.add_argument("root")
    check.add_argument("episode")
    check.add_argument("--purpose", choices=("final", "guide"), default="final")
    check.add_argument("--json", action="store_true")

    lock = sub.add_parser("lock", help="将已试听通过的角色音色写入选角锁")
    lock.add_argument("root")
    lock.add_argument("role")
    lock.add_argument("--backend", required=True)
    lock.add_argument("--voice-id", required=True)
    lock.add_argument("--approved-by", required=True)
    lock.add_argument("--canonical-sample", required=True)
    lock.add_argument("--model", default="")
    lock.add_argument("--authorization", default="not_applicable_synthetic")
    lock.add_argument("--status", choices=("locked", "guide_approved"), default="locked")
    lock.add_argument("--json", action="store_true")

    ns = parser.parse_args(argv)
    root = Path(ns.root).resolve()
    if not root.is_dir():
        parser.error(f"作品根不存在：{root}")

    if ns.command == "prepare":
        ep = normalize_episode(ns.episode)
        result = write_preproduction(root, ep)
        if not ns.no_progress and result["timing"].get("status") == "provisional":
            _set_rough_progress(root, ep)
        payload = {
            "status": "ready" if result["timing"].get("status") == "provisional" else "missing_voiceover",
            "episode": ep,
            "audio_generated": False,
            "outputs": result["outputs"],
            "casting_summary": result["casting"].get("summary"),
            "timing_summary": result["timing"].get("summary"),
            "next": "先试听并锁定角色音色；未锁音色前不批量生成最终 WAV。",
        }
        if ns.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"声音前期完成：{ep}（未生成 WAV）")
            print(f"- 选角表：{payload['outputs']['casting']}")
            print(f"- 时间估算：{payload['outputs']['timing']}")
            print(f"- 待锁角色：{(payload['casting_summary'] or {}).get('pending_count', 0)}")
        return 0 if payload["status"] == "ready" else 1

    if ns.command == "check":
        ep = normalize_episode(ns.episode)
        _path, lines, _fingerprint = load_voiceover(root, ep)
        payload = json.loads(casting_path(root).read_text(encoding="utf-8")) if casting_path(root).is_file() else {}
        blockers = casting_blockers(payload, [row["角色"] for row in lines], purpose=ns.purpose)
        result = {"status": "pass" if not blockers else "block", "episode": ep, "purpose": ns.purpose, "blockers": blockers}
        if ns.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"选角检查：{result['status']}（purpose={ns.purpose}）")
            for item in blockers:
                print(f"- {item}")
        return 0 if not blockers else 1

    data = lock_role(
        root, ns.role, backend=ns.backend, voice_id=ns.voice_id,
        approved_by=ns.approved_by, canonical_sample=ns.canonical_sample,
        model=ns.model, authorization=ns.authorization, status=ns.status,
    )
    if ns.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"已锁定角色音色：{ns.role}（status={ns.status}，项目 casting={data.get('status')}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
