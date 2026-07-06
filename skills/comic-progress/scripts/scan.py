#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读扫描画漫画项目进度。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROUTE = {
    "源本/企划": "comic-script",
    "漫画脚本": "comic-script",
    "页面排版": "comic-layout",
    "出图包": "comic-image",
    "出图": "comic-image",
    "嵌字合成": "comic-compose",
    "审查": "comic-review",
}

DONE = {"✅", "[x]", "完成", "done", "pass"}


def repo_root(start: Path) -> Path:
    cur = start.resolve()
    for parent in (cur, *cur.parents):
        if (parent / "skills").is_dir() and (parent / "创作区").is_dir():
            return parent
    return start.resolve()


def parse_progress(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = []
    headers = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells:
            continue
        if cells[0] == "话":
            headers = cells
            in_table = True
            continue
        if in_table and set(cells[0]) <= {"-"}:
            continue
        if in_table and headers and len(cells) >= len(headers):
            rows.append(dict(zip(headers, cells)))
    return {"path": str(path), "rows": rows}


def is_done(value: str) -> bool:
    return value.strip() in DONE or value.strip().startswith("✅")


def summarize_project(root: Path) -> dict:
    progress = root / "_进度.md"
    parsed = parse_progress(progress)
    fronts = []
    for row in parsed["rows"]:
        chapter = row.get("话", "未命名")
        next_stage = None
        next_skill = None
        for stage in ROUTE:
            if not is_done(row.get(stage, "")):
                next_stage = stage
                next_skill = ROUTE[stage]
                break
        fronts.append(
            {
                "chapter": chapter,
                "next_stage": next_stage or "完成",
                "next_skill": next_skill or "comic-review",
                "complete": next_stage is None,
            }
        )
    return {"project": root.name, "root": str(root), "fronts": fronts}


def find_projects(root: Path, args: argparse.Namespace) -> list[Path]:
    if args.projects:
        projects = []
        for item in args.projects:
            p = Path(item).expanduser().resolve()
            if p.is_file() and p.name == "_进度.md":
                p = p.parent
            if (p / "_进度.md").is_file():
                projects.append(p)
        return projects
    base = root / "创作区" / "画漫画"
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if (p / "_进度.md").is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描画漫画项目进度")
    parser.add_argument("projects", nargs="*", help="项目根或 _进度.md；不填则扫 创作区/画漫画")
    parser.add_argument("--root", default=None, help="仓库根")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else repo_root(Path.cwd())
    projects = find_projects(root, args)
    summaries = [summarize_project(p) for p in projects]

    if args.json:
        print(json.dumps({"projects": summaries}, ensure_ascii=False, indent=2))
        return 0

    if not summaries:
        print("未找到画漫画项目。可先运行：python3 skills/comic/scripts/init_project.py \"创作区/画漫画/作品名\" --title 作品名")
        return 0

    for summary in summaries:
        print(f"{summary['project']} — {summary['root']}")
        for front in summary["fronts"]:
            if front["complete"]:
                print(f"  {front['chapter']}: 主流程完成，建议 comic-review 做发布前复核")
            else:
                print(f"  {front['chapter']}: 下一步 {front['next_stage']} → {front['next_skill']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
