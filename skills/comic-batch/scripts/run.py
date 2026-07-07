#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漫画线流程推进脚本：读当前前沿并调用本线 stage runner。"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


STAGES = ["源本/企划", "漫画脚本", "页面排版", "出图包", "出图", "嵌字合成", "审查"]


def repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "skills").is_dir() and (parent / "创作区").is_dir():
            return parent
    return cur.parents[3]


def read_stage(root: Path, chapter: str) -> str:
    progress = root / "_进度.md"
    if not progress.is_file():
        return "源本/企划"
    headers: list[str] = []
    for line in progress.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and cells[0] == "话":
            headers = cells
            continue
        if not headers or not cells or cells[0] != chapter:
            continue
        row = {headers[i]: cells[i] for i in range(min(len(headers), len(cells)))}
        for stage in STAGES:
            if row.get(stage) != "✅":
                return stage
        return "完成"
    return "源本/企划"


def run_cmd(cmd: list[str], cwd: Path) -> int:
    print("[comic-batch] " + " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(cwd))


def main() -> int:
    parser = argparse.ArgumentParser(description="漫画线流程推进与批跑")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--stage", choices=["auto", "image"], default="auto")
    parser.add_argument("--targets", default="", help="逗号分隔 panel_id")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--force", action="store_true", help="重抽已 ready 的目标格")
    parser.add_argument("--image-max-attempts", type=int, default=1)
    parser.add_argument("--timeout-sec", type=int, default=240)
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    repo = repo_root()
    stage = read_stage(root, args.chapter) if args.stage == "auto" else "出图"
    print(f"[comic-batch] project={root.name} chapter={args.chapter} next_stage={stage}", flush=True)

    if stage == "完成":
        print("[comic-batch] chapter already complete", flush=True)
        return 0
    if stage != "出图":
        print(f"[comic-batch] next stage is {stage}; use the matching comic-* skill first", flush=True)
        return 2

    preflight = [
        sys.executable,
        "skills/comic-review/scripts/gate.py",
        str(root),
        "--chapter",
        args.chapter,
        "--stage",
        "image_preflight",
    ]
    rc = run_cmd(preflight, repo)
    if rc != 0:
        print("[comic-batch] image_preflight gate blocked; fix findings before paid/batch image generation", flush=True)
        return rc

    cmd = [
        sys.executable,
        "skills/comic-image/scripts/codex_panel_runner.py",
        str(root),
        "--chapter",
        args.chapter,
        "--max-attempts",
        str(max(1, args.image_max_attempts)),
        "--timeout-sec",
        str(args.timeout_sec),
    ]
    if args.targets:
        cmd.extend(["--targets", args.targets])
    if args.limit:
        cmd.extend(["--limit", str(args.limit)])
    if args.force:
        cmd.append("--force")
    rc = run_cmd(cmd, repo)
    if rc != 0:
        return rc
    image_gate = [
        sys.executable,
        "skills/comic-review/scripts/gate.py",
        str(root),
        "--chapter",
        args.chapter,
        "--stage",
        "image",
    ]
    return run_cmd(image_gate, repo)


if __name__ == "__main__":
    raise SystemExit(main())
