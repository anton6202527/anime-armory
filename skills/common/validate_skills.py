#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate local skill metadata and README coverage.

The checks are intentionally lightweight and stdlib-first:
- every `skills/*/SKILL.md` has frontmatter with `name` and `description`
- YAML frontmatter parses when PyYAML is installed; fallback catches common
  plain-scalar colon mistakes in `description: ...`
- `name` matches the directory name and is unique
- `skills/README.md` mentions every existing skill in backticks
"""

from __future__ import annotations

import argparse
import dataclasses
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:  # Optional. macOS/dev envs often have PyYAML, but the script still works without it.
    import yaml  # type: ignore
except Exception:  # pragma: no cover - exercised only on hosts without PyYAML
    yaml = None


FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


@dataclasses.dataclass(frozen=True)
class Finding:
    severity: str
    path: str
    message: str


def extract_frontmatter(text: str) -> Optional[str]:
    match = FRONTMATTER_RE.match(text)
    return match.group(1) if match else None


def fallback_parse(frontmatter: str) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for raw in frontmatter.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in {"name", "description"}:
            data[key] = value.strip("'\"")
    return data


def has_unquoted_colon_space(frontmatter: str) -> bool:
    for raw in frontmatter.splitlines():
        if not raw.startswith("description: "):
            continue
        value = raw.split(":", 1)[1].strip()
        if not value or value[0] in {"'", '"', "|", ">"}:
            return False
        return ": " in value
    return False


def parse_frontmatter(path: Path) -> Tuple[Optional[Dict[str, object]], Optional[str]]:
    text = path.read_text(encoding="utf-8")
    frontmatter = extract_frontmatter(text)
    if frontmatter is None:
        return None, "missing frontmatter block"
    if yaml is not None:
        try:
            data = yaml.safe_load(frontmatter) or {}
        except Exception as exc:
            return None, f"invalid YAML frontmatter: {exc}"
        if not isinstance(data, dict):
            return None, "frontmatter must be a mapping"
        return data, None
    if has_unquoted_colon_space(frontmatter):
        return None, "likely invalid YAML: quote description when it contains ': '"
    return fallback_parse(frontmatter), None


def iter_skill_files(skills_dir: Path) -> Iterable[Path]:
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        skill = child / "SKILL.md"
        if skill.is_file():
            yield skill


def validate_tree(skills_dir: Path) -> List[Finding]:
    findings: List[Finding] = []
    seen: Dict[str, Path] = {}
    skill_names: List[str] = []

    for skill_file in iter_skill_files(skills_dir):
        rel = skill_file.relative_to(skills_dir.parent).as_posix()
        data, error = parse_frontmatter(skill_file)
        if error:
            findings.append(Finding("error", rel, error))
            continue
        assert data is not None
        name = str(data.get("name", "")).strip()
        description = str(data.get("description", "")).strip()
        if not name:
            findings.append(Finding("error", rel, "missing frontmatter `name`"))
            continue
        if not description:
            findings.append(Finding("error", rel, "missing frontmatter `description`"))
        expected = skill_file.parent.name
        if name != expected:
            findings.append(Finding("error", rel, f"frontmatter name `{name}` must match directory `{expected}`"))
        if name in seen:
            first = seen[name].relative_to(skills_dir.parent).as_posix()
            findings.append(Finding("error", rel, f"duplicate skill name `{name}` also used by {first}"))
        else:
            seen[name] = skill_file
        if len(description) > 900:
            findings.append(Finding("warn", rel, "description is very long; consider moving detail into body/references"))
        skill_names.append(name)

    readme = skills_dir / "README.md"
    if not readme.is_file():
        findings.append(Finding("error", "skills/README.md", "missing skills index"))
        return findings
    readme_text = readme.read_text(encoding="utf-8")
    for name in sorted(set(skill_names)):
        if f"`{name}`" not in readme_text:
            findings.append(Finding("error", "skills/README.md", f"missing index entry for `{name}`"))
    return findings


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Validate skills metadata and README coverage.")
    ap.add_argument("skills_dir", nargs="?", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args(argv)

    skills_dir = Path(args.skills_dir).resolve()
    findings = validate_tree(skills_dir)
    for finding in findings:
        print(f"[{finding.severity}] {finding.path}: {finding.message}")
    errors = [f for f in findings if f.severity == "error"]
    if errors:
        print(f"\nfailed: {len(errors)} error(s), {len(findings) - len(errors)} warning(s)")
        return 1
    print(f"ok: validated {len(list(iter_skill_files(skills_dir)))} skills")
    warnings = [f for f in findings if f.severity == "warn"]
    if warnings:
        print(f"warnings: {len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
