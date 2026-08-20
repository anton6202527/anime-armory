#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漫画线流程推进脚本：推进已签收阶段，出图阶段带 gate 批跑。

- 缩略分镜/name board 与 layout 默认只产 draft，批跑必须停下等待人工或用户授权制作代理签收；
- 已签收后才继续原稿收尾/出图包/嵌字合成等确定性阶段；
- 出图阶段先跑 image_preflight gate，通过才调 runner，之后跑 image gate；
- 审查阶段只跑 review gate 产报告，不代替人工把 审查 标 ✅；
- 创作阶段（源本/企划、漫画脚本）不自动化，停下提示用对应 skill。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


COMIC_LIB = Path(__file__).resolve().parents[2] / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
from progress import update_stage as update_progress


STAGES = ["源本/企划", "漫画脚本", "缩略分镜", "页面排版", "原稿收尾", "出图包", "出图", "嵌字合成", "审查"]
# 缩略分镜/name board 现在是 layout 的强制编辑合同，不再随“传统原稿流程”关闭而跳过。
TRADITIONAL_STAGES = {"原稿收尾"}
TRADITIONAL_OFF_VALUES = {"关闭", "off", "disabled", "false", "False"}
CREATIVE_STAGES = {"源本/企划", "漫画脚本"}

# 免费确定性阶段 → 本线 stage 脚本（均只写文档/JSON，不花钱）。
DETERMINISTIC_STAGE_SCRIPTS = {
    "缩略分镜": "skills/comic/comic-name/scripts/build_name_board.py",
    "页面排版": "skills/comic/comic-layout/scripts/build_layout.py",
    "原稿收尾": "skills/comic/comic-finishing/scripts/build_finishing_plan.py",
    "出图包": "skills/comic/comic-image/scripts/build_panel_jobs.py",
}

# Copy-pasteable "run this next" hint per stage, so a batch stop is never a
# dead-end that only names a stage.  Descriptive only — points at a draft/check
# command, never an approval or paid generation.
STAGE_HINT_COMMAND = {
    "源本/企划": 'python3 skills/comic/comic-script/scripts/development_pack.py "{root}" scaffold --write   # 填完后 check --strict --json',
    "漫画脚本": 'python3 skills/comic/comic-script/scripts/source_semantics_gate.py "{root}" --chapter {ch}',
    "缩略分镜": 'python3 skills/comic/comic-name/scripts/build_name_board.py "{root}" --chapter {ch} --check',
    "页面排版": 'python3 skills/comic/comic-layout/scripts/build_layout.py "{root}" --chapter {ch} --check',
    "原稿收尾": 'python3 skills/comic/comic-finishing/scripts/build_finishing_plan.py "{root}" --chapter {ch} --check',
    "出图包": 'python3 skills/comic/comic-image/scripts/build_panel_jobs.py "{root}" --chapter {ch} --check',
    "出图": 'python3 skills/comic/comic-review/scripts/gate.py "{root}" --chapter {ch} --stage image_preflight',
    "嵌字合成": 'python3 skills/comic/comic-compose/scripts/export_longstrip.py "{root}" --chapter {ch} --render --qc-slots',
    "审查": 'python3 skills/comic/comic-review/scripts/review.py "{root}" --chapter {ch}',
}


def stage_hint_command(root: Path, chapter: str, stage: str) -> str:
    template = STAGE_HINT_COMMAND.get(stage, "")
    return template.format(root=root, ch=chapter) if template else ""


def repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "skills").is_dir() and (parent / "创作区").is_dir():
            return parent
    return cur.parents[4]


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
        [sys.executable, "skills/comic/comic-review/scripts/gate.py", str(root), "--chapter", chapter, "--stage", stage],
        repo,
    )


def pillow_available() -> bool:
    return importlib.util.find_spec("PIL") is not None


def chapter_images_ready(root: Path, chapter: str) -> bool:
    jobs_path = root / "出图" / chapter / "prompt" / "panel_jobs.json"
    if not jobs_path.is_file():
        return False
    try:
        jobs = json.loads(jobs_path.read_text(encoding="utf-8")).get("jobs") or []
    except (OSError, json.JSONDecodeError):
        return False
    if not jobs:
        return False
    for job in jobs:
        rel = str(job.get("result_path") or "").strip()
        if job.get("status") != "ready" or not rel or not (root / rel).is_file():
            return False
    return True


def image_runner_script(root: Path) -> str:
    channel = read_setting(root, "生图渠道", "").lower()
    model = read_setting(root, "生图模型", "").lower()
    if "dreamina" in channel or "即梦" in channel or "dreamina" in model or "即梦" in model:
        return "skills/comic/comic-image/scripts/dreamina_panel_runner.py"
    return "skills/comic/comic-image/scripts/codex_panel_runner.py"


def load_json_file(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def editorial_status(root: Path, chapter: str, stage: str) -> str:
    if stage == "缩略分镜":
        path = root / "排版" / chapter / "name_board.json"
    elif stage == "页面排版":
        path = root / "排版" / chapter / "layout.json"
    else:
        return ""
    return str(load_json_file(path).get("workflow_status") or "")


def print_editorial_wait(root: Path, chapter: str, stage: str, status: str) -> None:
    if stage == "缩略分镜":
        script = "skills/comic/comic-name/scripts/build_name_board.py"
        label = "name_board"
    else:
        script = "skills/comic/comic-layout/scripts/build_layout.py"
        label = "layout"
    print(
        f"[comic-batch] {label} status={status or 'missing'}；已停在人工签收点，不会自动越过。\n"
        f"  1) python3 {script} \"{root}\" --chapter {chapter} --submit-review\n"
        f"  2) python3 {script} \"{root}\" --chapter {chapter} --approve --reviewed-by <签收人>",
        flush=True,
    )


def update_progress_stage(root: Path, chapter: str, stage: str, value: str) -> None:
    update_progress(root, chapter, stage, value, actor="comic-batch")


def check_approved_editorial_stage(repo: Path, root: Path, chapter: str, stage: str) -> int:
    script = (
        "skills/comic/comic-name/scripts/build_name_board.py"
        if stage == "缩略分镜"
        else "skills/comic/comic-layout/scripts/build_layout.py"
    )
    return run_cmd([sys.executable, script, str(root), "--chapter", chapter, "--check", "--no-progress"], repo)


def check_editorial_prerequisites(repo: Path, root: Path, chapter: str) -> int:
    rc = run_cmd(
        [sys.executable, "skills/comic/comic-layout/scripts/build_layout.py", str(root), "--chapter", chapter, "--check", "--no-progress"],
        repo,
    )
    if rc != 0:
        print("[comic-batch] editorial layout 未签收、校验失败或上游已 stale；禁止进入出图", flush=True)
        return rc
    if read_setting(root, "传统原稿流程", "启用").strip() not in TRADITIONAL_OFF_VALUES:
        rc = run_cmd(
            [sys.executable, "skills/comic/comic-finishing/scripts/build_finishing_plan.py", str(root), "--chapter", chapter, "--check", "--no-progress"],
            repo,
        )
        if rc != 0:
            print("[comic-batch] finishing_plan 缺失、不完整或 stale；禁止进入出图", flush=True)
            return rc
    return 0


def run_image_stage(repo: Path, root: Path, args: argparse.Namespace) -> int:
    rc = check_editorial_prerequisites(repo, root, args.chapter)
    if rc != 0:
        return rc
    rc = run_gate(repo, root, args.chapter, "image_preflight")
    if rc != 0:
        print("[comic-batch] image_preflight gate blocked; fix findings before paid/batch image generation", flush=True)
        return rc
    cmd = [
        sys.executable,
        image_runner_script(root),
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
    if not chapter_images_ready(root, args.chapter):
        print(
            "[comic-batch] target/limited batch post-QC passed; chapter is still incomplete, "
            "so the full image gate is deferred until every panel is ready",
            flush=True,
        )
        return 0
    return run_gate(repo, root, args.chapter, "image")


def run_compose_stage(repo: Path, root: Path, chapter: str) -> int:
    rc = run_cmd(
        [sys.executable, "skills/comic/comic-compose/scripts/build_lettering.py", str(root), "--chapter", chapter],
        repo,
    )
    if rc != 0:
        return rc
    export_cmd = [
        sys.executable,
        "skills/comic/comic-compose/scripts/export_longstrip.py",
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


STAGE_STOP_NOTE = {
    "源本/企划": "创作阶段：改编策略/分话/分格由 comic-script 完成，不自动跑",
    "漫画脚本": "创作阶段：source trace/分格由 comic-script 完成，不自动跑",
    "缩略分镜": "⏸ 人工签收停点：draft → --submit-review → --approve --reviewed-by <签收人>",
    "页面排版": "⏸ 人工签收停点：draft → --submit-review → --approve --reviewed-by <签收人>",
    "原稿收尾": "确定性阶段：build_finishing_plan（免费，只写计划）",
    "出图包": "确定性阶段：build_panel_jobs（免费，编译出图包）",
    "出图": "⏸ 付费生成停点：需项目授权后才跑 panel runner（会花钱）",
    "嵌字合成": "确定性阶段：export_longstrip 渲染 + compose gate",
    "审查": "⏸ 人工验收停点：review gate pass 后仍需人工确认 审查 列",
}


def plan_chapter(root: Path, chapter: str) -> int:
    """Dry-run: print the ordered stage plan from the current frontier without
    executing anything — every stop point (human signoff / paid generation) is
    labelled so the user can see scope before committing."""
    headers: list[str] = []
    progress = root / "_进度.md"
    if progress.is_file():
        for line in progress.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("|") and "话" in stripped and "源本" in stripped:
                headers = [cell.strip() for cell in stripped.strip("|").split("|")]
                break
    stages = effective_stages(root, headers)
    frontier = read_stage(root, chapter)
    print(f"[comic-batch --dry-run] project={root.name} chapter={chapter} 当前前沿={frontier}", flush=True)
    if frontier == "完成":
        print("  本话主流程已完成（仍需人工发布前复核）。", flush=True)
        return 0
    try:
        start = stages.index(frontier)
    except ValueError:
        start = 0
    print("  从当前前沿起的阶段计划（只预览，不执行）：", flush=True)
    for idx, stage in enumerate(stages[start:], 1):
        note = STAGE_STOP_NOTE.get(stage, "")
        print(f"    {idx}. {stage} — {note}", flush=True)
        hint = stage_hint_command(root, chapter, stage)
        if hint:
            print(f"       运行: {hint}", flush=True)
    print("  说明：批跑会在每个 ⏸ 停点停下等人工/授权，不会自动越过签收或付费生成。", flush=True)
    return 0


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
    parser.add_argument("--dry-run", action="store_true", help="只打印从当前前沿起的阶段计划与停点，不执行任何阶段")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    repo = repo_root()

    if args.dry_run:
        return plan_chapter(root, args.chapter)

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
            hint = stage_hint_command(root, args.chapter, stage)
            if hint:
                print(f"  运行: {hint}", flush=True)
            return 2
        if stage in {"缩略分镜", "页面排版"}:
            status = editorial_status(root, args.chapter, stage)
            if status in {"draft", "review"}:
                print_editorial_wait(root, args.chapter, stage, status)
                return 0
            if status == "approved":
                rc = check_approved_editorial_stage(repo, root, args.chapter, stage)
                if rc != 0:
                    print(f"[comic-batch] {stage} 虽标 approved，但审批/上游已失效；停止，不能覆盖现有签收稿", flush=True)
                    return rc
                update_progress_stage(root, args.chapter, stage, "✅")
                continue
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
            hint = stage_hint_command(root, args.chapter, stage)
            if hint:
                print(f"  运行: {hint}", flush=True)
            return 2
        if rc != 0:
            return rc
        if stage in {"缩略分镜", "页面排版"}:
            status = editorial_status(root, args.chapter, stage)
            if status != "approved":
                print_editorial_wait(root, args.chapter, stage, status)
                return 0
        new_stage = read_stage(root, args.chapter)
        if new_stage == stage:
            print(
                f"[comic-batch] stage {stage} 已运行但前沿未推进"
                "（多为该阶段只产出 draft/需人工签收，或产物未过 --check，不是自动失败）。",
                flush=True,
            )
            hint = stage_hint_command(root, args.chapter, stage)
            if hint:
                print(f"  复核该阶段产物: {hint}", flush=True)
            return 2
    print("[comic-batch] 达到 --max-steps 上限，停止；再次运行可继续推进", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
