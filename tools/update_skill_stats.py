#!/usr/bin/env python3
"""Update and validate series and top-level standalone skill size statistics.

This keeps two surfaces in sync:
  1. skills/README.md scale table.
  2. The first body line of each top-level dispatcher skill
     (skills/n2d/SKILL.md, skills/novel/SKILL.md, ...).
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"
README = SKILLS / "README.md"
SERIES = ("n2d", "novel", "comic", "song", "mv", "ad")
STANDALONE = "standalone"
GROUPS = (*SERIES, STANDALONE)
TEXT_SUFFIXES = {".md", ".py", ".sh", ".json", ".html"}

STAT_RE = re.compile(
    r"^> 规模统计：Skill 数 \d+ \| SKILL\.md 总行数 \d+ \| 目录文本总行数 \d+$"
)
README_DATE_RE = re.compile(r"> 统计时间：\d{4}-\d{2}-\d{2}。")
README_ROW_RE = {
    line: re.compile(
        rf"\| {line} \| `(?:{line}` \+ `{line}-\*|skills/{line}/\*\*/SKILL\.md)` "
        rf"\| \d+ \| \d+ \| \d+ \|"
    )
    for line in SERIES
}
README_ROW_RE[STANDALONE] = re.compile(
    r"\| 独立 skill \| `skills/<skill-name>/SKILL\.md` \| \d+ \| \d+ \| \d+ \|"
)
README_TOTAL_RE = re.compile(
    r"\| \*\*合计\*\* \| `skills/(?:\*\*/SKILL|\*/SKILL|<line>/\*\*/SKILL)\.md` "
    r"\| \*\*\d+\*\* \| \d+ \| \d+ \|"
)


@dataclass(frozen=True)
class SkillStats:
    skills: int
    skill_md_lines: int
    total_lines: int


def count_lines(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def dispatcher_skill_path(line: str) -> Path:
    return SKILLS / line / "SKILL.md"


def is_dispatcher_skill(path: Path) -> bool:
    return any(path == dispatcher_skill_path(line) for line in SERIES)


def stat_line_count(path: Path) -> int:
    try:
        lines = path.read_text("utf-8", "ignore").splitlines()
    except OSError:
        return 0
    return sum(1 for line in lines if STAT_RE.match(line))


def normalized_line_count(path: Path) -> int:
    """Count lines after normalizing dispatcher stats to exactly one line."""
    lines = count_lines(path)
    if not is_dispatcher_skill(path):
        return lines
    stats = stat_line_count(path)
    if stats == 0:
        return lines + 1
    if stats > 1:
        return lines - (stats - 1)
    return lines


def skill_dirs_for(line: str) -> list[Path]:
    if line == STANDALONE:
        return sorted(
            d
            for d in SKILLS.iterdir()
            if d.is_dir()
            and d.name not in SERIES
            and (d / "SKILL.md").is_file()
        )
    line_dir = SKILLS / line
    if not (line_dir / "SKILL.md").is_file():
        return []
    children = sorted(
        d
        for d in line_dir.iterdir()
        if d.is_dir()
        and d.name.startswith(f"{line}-")
        and (d / "SKILL.md").is_file()
    )
    return [line_dir, *children]


def iter_owned_text_files(skill_dir: Path, child_skill_dirs: set[Path]):
    """Yield files owned by one skill without double-counting nested children."""
    for path in skill_dir.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if "__pycache__" in path.parts:
            continue
        if any(child in path.parents for child in child_skill_dirs):
            continue
        yield path


def get_stats() -> dict[str, SkillStats]:
    stats: dict[str, SkillStats] = {}
    for line in GROUPS:
        skill_dirs = skill_dirs_for(line)
        skill_count = len(skill_dirs)
        skill_md_lines = 0
        total_lines = 0
        child_skill_dirs = set(skill_dirs[1:]) if line in SERIES else set()
        for skill_dir in skill_dirs:
            skill_md = skill_dir / "SKILL.md"
            if skill_md.is_file():
                skill_md_lines += normalized_line_count(skill_md)
            nested_children = child_skill_dirs if line in SERIES and skill_dir == SKILLS / line else set()
            for path in iter_owned_text_files(skill_dir, nested_children):
                total_lines += normalized_line_count(path)
        stats[line] = SkillStats(skill_count, skill_md_lines, total_lines)
    return stats


def total_stats(stats: dict[str, SkillStats]) -> SkillStats:
    return SkillStats(
        skills=sum(item.skills for item in stats.values()),
        skill_md_lines=sum(item.skill_md_lines for item in stats.values()),
        total_lines=sum(item.total_lines for item in stats.values()),
    )


def stat_line(line: str, stats: dict[str, SkillStats]) -> str:
    item = stats[line]
    return (
        f"> 规模统计：Skill 数 {item.skills} | "
        f"SKILL.md 总行数 {item.skill_md_lines} | "
        f"目录文本总行数 {item.total_lines}"
    )


def frontmatter_end_index(lines: list[str]) -> int:
    if not lines or lines[0].strip() != "---":
        return 0
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return idx + 1
    return 0


def render_dispatcher_skill(path: Path, line: str, stats: dict[str, SkillStats]) -> str:
    original = path.read_text("utf-8")
    had_final_newline = original.endswith("\n")
    lines = original.splitlines()
    lines = [item for item in lines if not STAT_RE.match(item)]
    idx = frontmatter_end_index(lines)
    lines.insert(idx, stat_line(line, stats))
    text = "\n".join(lines)
    if had_final_newline:
        text += "\n"
    return text


def render_readme(stats: dict[str, SkillStats]) -> str:
    content = README.read_text("utf-8")
    today = date.today().isoformat()
    content = README_DATE_RE.sub(f"> 统计时间：{today}。", content)

    for line in SERIES:
        item = stats[line]
        replacement = (
            f"| {line} | `skills/{line}/**/SKILL.md` | "
            f"{item.skills} | {item.skill_md_lines} | {item.total_lines} |"
        )
        content = README_ROW_RE[line].sub(replacement, content)

    standalone = stats[STANDALONE]
    content = README_ROW_RE[STANDALONE].sub(
        f"| 独立 skill | `skills/<skill-name>/SKILL.md` | "
        f"{standalone.skills} | {standalone.skill_md_lines} | {standalone.total_lines} |",
        content,
    )

    total = total_stats(stats)
    total_replacement = (
        f"| **合计** | `skills/**/SKILL.md` | **{total.skills}** | "
        f"{total.skill_md_lines} | {total.total_lines} |"
    )
    content = README_TOTAL_RE.sub(total_replacement, content)
    return content


def expected_updates(stats: dict[str, SkillStats]) -> dict[Path, str]:
    updates = {README: render_readme(stats)}
    for line in SERIES:
        path = dispatcher_skill_path(line)
        if path.is_file():
            updates[path] = render_dispatcher_skill(path, line, stats)
    return updates


def update_files(stats: dict[str, SkillStats]) -> list[Path]:
    changed: list[Path] = []
    for path, expected in expected_updates(stats).items():
        current = path.read_text("utf-8")
        if current == expected:
            continue
        path.write_text(expected, encoding="utf-8")
        changed.append(path)
    return changed


def validate_stats(stats: dict[str, SkillStats]) -> list[str]:
    bad: list[str] = []
    readme = README.read_text("utf-8", "ignore")
    for line in SERIES:
        item = stats[line]
        expected_row = (
            f"| {line} | `skills/{line}/**/SKILL.md` | "
            f"{item.skills} | {item.skill_md_lines} | {item.total_lines} |"
        )
        if expected_row not in readme:
            bad.append(f"skills/README.md: {line} 规模统计过期，应为：{expected_row}")

        path = dispatcher_skill_path(line)
        if not path.is_file():
            bad.append(f"{path.relative_to(REPO)}: 总领 skill 不存在，无法写入规模统计")
            continue
        lines = path.read_text("utf-8", "ignore").splitlines()
        idx = frontmatter_end_index(lines)
        expected_stat = stat_line(line, stats)
        actual = lines[idx] if idx < len(lines) else ""
        if actual != expected_stat:
            bad.append(
                f"{path.relative_to(REPO)}:{idx + 1}: 总领 skill 第一行规模统计过期，"
                f"应为：{expected_stat}"
            )
        extra_stats = [i + 1 for i, value in enumerate(lines) if STAT_RE.match(value)]
        if extra_stats != [idx + 1]:
            bad.append(
                f"{path.relative_to(REPO)}: 规模统计行必须且只能出现在 frontmatter 后第一行；"
                f"当前行号：{extra_stats}"
            )

    standalone = stats[STANDALONE]
    expected_standalone = (
        f"| 独立 skill | `skills/<skill-name>/SKILL.md` | "
        f"{standalone.skills} | {standalone.skill_md_lines} | {standalone.total_lines} |"
    )
    if expected_standalone not in readme:
        bad.append(f"skills/README.md: 独立 skill 规模统计过期，应为：{expected_standalone}")

    total = total_stats(stats)
    expected_total = (
        f"| **合计** | `skills/**/SKILL.md` | **{total.skills}** | "
        f"{total.skill_md_lines} | {total.total_lines} |"
    )
    if expected_total not in readme:
        bad.append(f"skills/README.md: 合计规模统计过期，应为：{expected_total}")
    return bad


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update per-line skill size statistics")
    parser.add_argument("--check", action="store_true", help="only validate stats, do not write files")
    args = parser.parse_args(argv)

    stats = get_stats()
    if args.check:
        bad = validate_stats(stats)
        if bad:
            for item in bad:
                print(item)
            print("\nRun: python3 tools/update_skill_stats.py", file=sys.stderr)
            return 1
        print("Skill stats are up to date.")
        return 0

    changed = update_files(stats)
    for line in GROUPS:
        item = stats[line]
        print(
            f"{line}: skills={item.skills}, "
            f"skill_md_lines={item.skill_md_lines}, total_lines={item.total_lines}"
        )
    if changed:
        print("Updated:")
        for path in changed:
            print(f"  - {path.relative_to(REPO)}")
    else:
        print("No files changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
