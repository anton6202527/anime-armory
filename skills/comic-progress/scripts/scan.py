#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读扫描画漫画项目进度。"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROUTE = {
    "源本/企划": "comic-script",
    "漫画脚本": "comic-script",
    "缩略分镜": "comic-name",
    "页面排版": "comic-layout",
    "原稿收尾": "comic-finishing",
    "出图包": "comic-image",
    "出图": "comic-image",
    "嵌字合成": "comic-compose",
    "审查": "comic-review",
}

STAGE_ALIASES = {
    "原稿收尾": ("原稿收尾", "传统收尾"),
}

DONE = {"✅", "[x]", "完成", "done", "pass"}


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


def row_stage_done(row: dict[str, str], stage: str) -> bool:
    aliases = STAGE_ALIASES.get(stage, (stage,))
    present = [alias for alias in aliases if alias in row]
    if not present:
        return False
    return any(is_done(row.get(alias, "")) for alias in present)


def has_identity_blocker(root: Path, chapter: str) -> tuple[bool, str]:
    jobs_path = root / "出图" / chapter / "prompt" / "panel_jobs.json"
    if not jobs_path.is_file():
        return False, ""
    try:
        data = json.loads(jobs_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, ""
    missing_refs = set()
    stale_panels = []
    for job in data.get("jobs") or []:
        refs = [ref for ref in job.get("references") or [] if isinstance(ref, dict) and ref.get("id")]
        if not refs:
            continue
        valid_ref_count = 0
        for ref in refs:
            raw = str(ref.get("path") or "").strip()
            if not raw:
                missing_refs.add(str(ref.get("id")))
                continue
            path = Path(raw)
            if not path.is_absolute():
                path = root / path
            if path.is_file():
                valid_ref_count += 1
            else:
                missing_refs.add(str(ref.get("id")))
        generated_count = int(job.get("reference_input_count") or 0)
        if job.get("status") == "ready" and valid_ref_count and generated_count < valid_ref_count:
            stale_panels.append(str(job.get("panel_id") or ""))
    if missing_refs:
        return True, "共享参考缺失：" + "、".join(sorted(missing_refs))
    if stale_panels:
        return True, "已出图未使用当前真实参考：" + "、".join(pid for pid in stale_panels if pid)
    return False, ""


def has_longline_identity_blocker(root: Path, chapter: str) -> tuple[bool, str]:
    identity_level = read_setting(root, "定妆级别", "长线专门定妆")
    if "长线" not in identity_level and "专门定妆" not in identity_level:
        return False, ""
    report_path = root / "生产数据" / f"comic_identity_report_{chapter}.json"
    if not report_path.is_file():
        return True, "长线专门定妆：缺少 comic-identity 报告"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True, "长线专门定妆：comic-identity 报告不可解析"
    missing = report.get("missing_character_views")
    if not isinstance(missing, dict):
        return False, ""
    blockers = {
        str(character): [str(view) for view in views]
        for character, views in missing.items()
        if isinstance(views, list) and views
    }
    if not blockers:
        return False, ""
    pieces = [f"{character} 缺 {','.join(views)}" for character, views in sorted(blockers.items())]
    return True, "长线专门定妆未补齐：" + "；".join(pieces)


def has_style_blocker(root: Path, chapter: str) -> tuple[bool, str, str]:
    report_path = root / "生产数据" / f"comic_style_consistency_{chapter}.json"
    if not report_path.is_file():
        return True, "缺少风格一致性报告，请先跑 comic-review/style_consistency", "comic-review"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True, "风格一致性报告不可解析，请重跑 comic-review/style_consistency", "comic-review"
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    block_count = int(summary.get("block_count") or 0)
    if block_count > 0:
        examples = [
            str(item.get("panel_id") or item.get("artifact") or item.get("code"))
            for item in report.get("findings") or []
            if isinstance(item, dict) and item.get("severity") == "block"
        ]
        suffix = "：" + "、".join(item for item in examples[:8] if item) if examples else ""
        return True, f"风格一致性仍有 {block_count} 个阻断{suffix}", "comic-image"
    return False, "", ""


def has_source_semantics_blocker(root: Path, chapter: str) -> tuple[bool, str]:
    panel_path = root / "脚本" / chapter / "panel_script.json"
    if not panel_path.is_file():
        return False, ""
    try:
        panel_script = json.loads(panel_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, ""
    meta = panel_script.get("source_semantics") if isinstance(panel_script.get("source_semantics"), dict) else {}
    source_path = root / str(meta.get("path") or Path("脚本") / chapter / "source_semantics.json")
    requires = bool(meta.get("requires_normalization"))
    if not source_path.is_file() and not requires:
        return False, ""
    try:
        report = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True, "source_semantics 缺失或不可解析"
    if report.get("requires_normalization") and report.get("status") != "pass":
        return True, "源语义归一化 gate 未通过"
    if not (report.get("requires_normalization") or requires):
        return False, ""
    fields = ["source_excerpt", "meaning_zh", "text_target", "adaptation_note"]
    missing = []
    for panel in panel_script.get("panels") or []:
        if not isinstance(panel, dict):
            continue
        miss = [field for field in fields if not str(panel.get(field) or "").strip()]
        if miss:
            missing.append(f"{panel.get('panel_id') or 'unknown'}({','.join(miss)})")
    if missing:
        return True, "panel 缺语义追溯字段：" + "；".join(missing[:8])
    return False, ""


def summarize_project(root: Path) -> dict:
    progress = root / "_进度.md"
    parsed = parse_progress(progress)
    fronts = []
    for row in parsed["rows"]:
        chapter = row.get("话", "未命名")
        next_stage = None
        next_skill = None
        for stage in ROUTE:
            if not row_stage_done(row, stage):
                next_stage = stage
                next_skill = ROUTE[stage]
                break
        if next_stage not in (None, "源本/企划", "漫画脚本"):
            blocked, reason = has_source_semantics_blocker(root, chapter)
            if blocked:
                fronts.append(
                    {
                        "chapter": chapter,
                        "next_stage": "源语义归一化",
                        "next_skill": "comic-script",
                        "complete": False,
                        "reason": reason,
                    }
                )
                continue
        if next_stage in ("嵌字合成", "审查"):
            blocked, reason = has_identity_blocker(root, chapter)
            if blocked:
                fronts.append(
                    {
                        "chapter": chapter,
                        "next_stage": "一致性复核",
                        "next_skill": "comic-identity",
                        "complete": False,
                        "reason": reason,
                    }
                )
                continue
            blocked, reason = has_longline_identity_blocker(root, chapter)
            if blocked:
                fronts.append(
                    {
                        "chapter": chapter,
                        "next_stage": "专门定妆",
                        "next_skill": "comic-identity",
                        "complete": False,
                        "reason": reason,
                    }
                )
                continue
            blocked, reason, skill = has_style_blocker(root, chapter)
            if blocked:
                fronts.append(
                    {
                        "chapter": chapter,
                        "next_stage": "风格一致性复核" if skill == "comic-review" else "风格返修",
                        "next_skill": skill,
                        "complete": False,
                        "reason": reason,
                    }
                )
                continue
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
                suffix = f"（{front['reason']}）" if front.get("reason") else ""
                print(f"  {front['chapter']}: 下一步 {front['next_stage']} → {front['next_skill']}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
