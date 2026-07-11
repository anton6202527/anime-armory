#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漫画线流程推进脚本：从当前前沿起自动推进免费确定性阶段，出图阶段带 gate 批跑。

- 免费确定性阶段（缩略分镜/页面排版/原稿收尾/出图包/嵌字合成）自动 chain；
- 出图阶段先跑 image_preflight gate，通过才调 runner，之后跑 image gate；
- 审查阶段只跑 review gate 产报告，不代替人工把 审查 标 ✅；
- 创作阶段（源本/企划、漫画脚本）不自动化，停下提示用对应 skill。
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path


STAGES = ["源本/企划", "漫画脚本", "缩略分镜", "页面排版", "原稿收尾", "出图包", "出图", "嵌字合成", "审查"]
TRADITIONAL_STAGES = {"缩略分镜", "原稿收尾"}
TRADITIONAL_OFF_VALUES = {"关闭", "off", "disabled", "false", "False"}
CREATIVE_STAGES = {"源本/企划", "漫画脚本"}

# 免费确定性阶段 → 本线 stage 脚本（均只写文档/JSON，不花钱）。
DETERMINISTIC_STAGE_SCRIPTS = {
    "缩略分镜": "skills/comic-name/scripts/build_name_board.py",
    "页面排版": "skills/comic-layout/scripts/build_layout.py",
    "原稿收尾": "skills/comic-finishing/scripts/build_finishing_plan.py",
    "出图包": "skills/comic-image/scripts/build_panel_jobs.py",
}


def repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "skills").is_dir() and (parent / "创作区").is_dir():
            return parent
    return cur.parents[3]


def read_setting(root: Path, key: str, default: str = "") -> str:
    path = root / "_设置.md"
    if not path.is_file():
        return default
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


def effective_stages(root: Path, headers: list[str]) -> list[str]:
    traditional_off = read_setting(root, "传统原稿流程", "启用").strip() in TRADITIONAL_OFF_VALUES
    stages = []
    for stage in STAGES:
        if traditional_off and stage in TRADITIONAL_STAGES:
            continue
        if headers and stage not in headers:
            # 旧进度表整列缺失 → 该阶段对此表不适用，不能卡死前沿。
            continue
        stages.append(stage)
    return stages


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
        for stage in effective_stages(root, headers):
            if not str(row.get(stage, "")).startswith("✅"):
                return stage
        return "完成"
    return "源本/企划"


def run_cmd(cmd: list[str], cwd: Path) -> int:
    print("[comic-batch] " + " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(cwd))


def run_gate(repo: Path, root: Path, chapter: str, stage: str) -> int:
    return run_cmd(
        [sys.executable, "skills/comic-review/scripts/gate.py", str(root), "--chapter", chapter, "--stage", stage],
        repo,
    )


def pillow_available() -> bool:
    return importlib.util.find_spec("PIL") is not None


def run_image_stage(repo: Path, root: Path, args: argparse.Namespace) -> int:
    rc = run_gate(repo, root, args.chapter, "image_preflight")
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
        # preflight 刚在编排层跑过且通过，runner 内置 gate 不必重复付一次检查成本。
        "--skip-gate",
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
    return run_gate(repo, root, args.chapter, "image")


def run_compose_stage(repo: Path, root: Path, chapter: str) -> int:
    rc = run_cmd(
        [sys.executable, "skills/comic-compose/scripts/build_lettering.py", str(root), "--chapter", chapter],
        repo,
    )
    if rc != 0:
        return rc
    export_cmd = [
        sys.executable,
        "skills/comic-compose/scripts/export_longstrip.py",
        str(root),
        "--chapter",
        chapter,
        "--write-progress",
    ]
    if pillow_available():
        export_cmd.append("--render")
    else:
        print("[comic-batch] 未安装 Pillow：只写导出 manifest，不渲染长图；compose gate 会提示待渲染", flush=True)
    rc = run_cmd(export_cmd, repo)
    if rc != 0:
        return rc
    return run_gate(repo, root, chapter, "compose")


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
    parser.add_argument("--max-steps", type=int, default=12, help="单次调用最多推进多少个阶段（防循环）")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    repo = repo_root()

    if args.stage == "image":
        print(f"[comic-batch] project={root.name} chapter={args.chapter} stage=出图(手动指定)", flush=True)
        return run_image_stage(repo, root, args)

    for _step in range(max(1, args.max_steps)):
        stage = read_stage(root, args.chapter)
        print(f"[comic-batch] project={root.name} chapter={args.chapter} next_stage={stage}", flush=True)

        if stage == "完成":
            print("[comic-batch] chapter already complete", flush=True)
            return 0
        if stage in CREATIVE_STAGES:
            print(f"[comic-batch] next stage is {stage}; creative stage — use comic-script first", flush=True)
            return 2
        if stage in DETERMINISTIC_STAGE_SCRIPTS:
            rc = run_cmd(
                [sys.executable, DETERMINISTIC_STAGE_SCRIPTS[stage], str(root), "--chapter", args.chapter],
                repo,
            )
        elif stage == "出图":
            rc = run_image_stage(repo, root, args)
        elif stage == "嵌字合成":
            rc = run_compose_stage(repo, root, args.chapter)
        elif stage == "审查":
            rc = run_gate(repo, root, args.chapter, "review")
            if rc == 0:
                print("[comic-batch] review gate pass；审查 列请人工确认后标 ✅（批跑不代替人工验收）", flush=True)
            return rc
        else:
            print(f"[comic-batch] next stage is {stage}; use the matching comic-* skill first", flush=True)
            return 2
        if rc != 0:
            return rc
        new_stage = read_stage(root, args.chapter)
        if new_stage == stage:
            print(f"[comic-batch] stage {stage} ran but 前沿未推进；检查该阶段脚本输出后再续跑", flush=True)
            return 2
    print("[comic-batch] 达到 --max-steps 上限，停止；再次运行可继续推进", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
