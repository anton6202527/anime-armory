#!/usr/bin/env python3
"""Skill 设计宪法机检 runner —— 把 docs/skill-design-principles.md 里标 ✅ 的条文变成可执行检查。

唯一真值源是 docs/skill-design-principles.md；本脚本只机检其中能机检的几条：
  - E1  交付端 VCS-free：skill 不得用 git 做本仓状态/基线/变更检测（内容快照除外）。
  - B2  推荐 skill 写裸名：skill 的 SKILL.md/.sh/.py 不得把 skill 当斜杠命令写成 /skillname
         （含脚本里打印给用户看的 echo —— agent 可能把 /name 当内置斜杠命令）。
  - F1  改了 skill 集合必须同步 skills/README.md 索引：每个 skills/<name>/ 都要在 README 出现。
  - F3  入口文档同步：AGENTS/GEMINI/CLAUDE 不得保留过期命令或旧路径，关键入口保持一致。

零依赖、纯标准库，从仓库根跑：
    python3 tools/validate_skills.py            # 全检，违规 exit 1
    python3 tools/validate_skills.py --only E1  # 只跑某条
配套：跨线独立性(A1/F2) 由 tools/independence-audit/scripts/check_independence.py 机检，不在这里重复。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"
README = SKILLS / "README.md"
ENTRY_DOCS = ("AGENTS.md", "GEMINI.md", "CLAUDE.md")

# 四条创作线的 skill 名前缀（用于 B2 斜杠命令检测）
LINE_PREFIXES = ("n2d", "song", "mv", "ad")

# E1 grandfathered 例外清单 —— 现已清空。
# n2d-update 历史上用 git 基线比对，2026-06 已重构为纯内容 SHA256 快照
# （build_baseline_snapshot），并主动拒绝 legacy git 基线，账已销。
# 机制保留作未来扩展点：新增本仓 VCS 自省/变更检测调用一律 fail。
KNOWN_GIT_EXCEPTIONS: set[str] = set()

# E1: `git <subcommand>` —— 只查 VCS「自省」子命令（对本仓状态/基线/变更检测），
# 不含 clone/fetch/pull/push 等远端操作（references 安装第三方模型常 `git clone`，允许）。
GIT_RE = re.compile(
    r"\bgit\s+(?:status|diff|log|rev-parse|show|add|commit|checkout|switch|"
    r"stash|init|branch|tag|ls-files|describe|reset|restore)\b"
)

# B2: 斜杠命令式引用 /n2d-image —— slash 前不接 word/./- 以排除路径(skills/n2d-image)。
SLASH_RE = re.compile(
    r"(?<![\w./-])/(?:" + "|".join(LINE_PREFIXES) + r")(?:-[a-z]+)*\b"
)

ENTRY_REQUIRED_ALL = (
    "docs/skill-design-principles.md",
    "python3 tools/validate_skills.py",
    "tools/independence-audit/scripts/check_independence.py",
)

ROUTING_DOCS = ("AGENTS.md", "GEMINI.md")
ROUTING_SNIPPETS = (
    "`n2d`",
    "`song`",
    "`mv`",
    "`ad`",
    "`n2d-progress`",
    "`n2d-settings`",
    "`n2d-update`",
    "`tools/shared-cleanup`",
    "`tools/independence-audit`",
    "skills/<line>/_lib/refresh.py",
)

ENTRY_FORBIDDEN = {
    "tools/check_independence.py": "旧 independence audit 命令，应用 tools/independence-audit/scripts/check_independence.py",
    "/progress": "旧斜杠进度入口，入口文档应写裸 skill 名或直接读 _进度.md",
    ".claude/创作偏好-默认.md": "Claude 私有旧路径不应作为唯一全局默认；应写工具中立私有默认并注明 .claude legacy",
}


def _rel(p: Path) -> str:
    return str(p.relative_to(SKILLS))


def check_no_git_calls() -> list[str]:
    """E1: skills/ 下任何 .py/.sh/.md 不得出现本仓 VCS 自省/变更检测调用。"""
    bad: list[str] = []
    for p in SKILLS.rglob("*"):
        if p.suffix not in (".py", ".sh", ".md") or not p.is_file():
            continue
        if _rel(p) in KNOWN_GIT_EXCEPTIONS:
            continue
        for i, line in enumerate(p.read_text("utf-8", "ignore").splitlines(), 1):
            if GIT_RE.search(line):
                bad.append(f"{_rel(p)}:{i}: git 调用/描述 —— {line.strip()[:80]}")
    return bad


def check_bare_skill_refs() -> list[str]:
    """B2: skill 的 SKILL.md/.sh/.py 里不得把 skill 写成斜杠命令 /skillname。

    含脚本里打印给用户的 echo/print —— 这类引用从前只扫 SKILL.md 时会漏检
    （根级入口文档反例不在 skills/ 下，天然不扫）。
    """
    bad: list[str] = []
    seen: set[str] = set()
    for pattern in ("SKILL.md", "*.sh", "*.py"):
        for p in SKILLS.rglob(pattern):
            rel = _rel(p)
            if rel in seen or not p.is_file():
                continue
            seen.add(rel)
            for i, line in enumerate(p.read_text("utf-8", "ignore").splitlines(), 1):
                m = SLASH_RE.search(line)
                if m:
                    bad.append(f"{rel}:{i}: 斜杠命令式 skill 引用 '{m.group(0)}' —— 应写裸名")
    return bad


def check_readme_index() -> list[str]:
    """F1: 每个 skills/<name>/SKILL.md 的 name 必须在 README 以 `name` 形式出现。"""
    text = README.read_text("utf-8", "ignore")
    bad: list[str] = []
    for d in sorted(SKILLS.iterdir()):
        if not (d / "SKILL.md").is_file():
            continue
        name = d.name
        if f"`{name}`" not in text and f"`{name}/" not in text:
            bad.append(f"skills/{name}/ 未在 skills/README.md 索引中登记（F1）")
    return bad


def check_entry_docs_sync() -> list[str]:
    """F3: 入口文档关键命令、路由入口和过期写法同步检查。"""
    bad: list[str] = []
    texts: dict[str, str] = {}
    for name in ENTRY_DOCS:
        p = REPO / name
        if not p.is_file():
            bad.append(f"{name}: 入口文档不存在（F3）")
            continue
        text = p.read_text("utf-8", "ignore")
        texts[name] = text
        for needle in ENTRY_REQUIRED_ALL:
            if needle not in text:
                bad.append(f"{name}: 缺少关键入口约定/命令 '{needle}'（F3）")
        for needle, reason in ENTRY_FORBIDDEN.items():
            if needle in text:
                bad.append(f"{name}: 发现过期入口写法 '{needle}' —— {reason}（F3）")

    for name in ROUTING_DOCS:
        text = texts.get(name, "")
        for needle in ROUTING_SNIPPETS:
            if needle not in text:
                bad.append(f"{name}: 路由表缺少 '{needle}'（F3）")

    claude = texts.get("CLAUDE.md", "")
    if "AGENTS.md" not in claude or "routing table" not in claude.lower():
        bad.append("CLAUDE.md: 应明确指向 AGENTS.md 作为路由表真值源（F3）")
    return bad


CHECKS = {
    "E1": ("交付端 VCS-free（无 git 调用）", check_no_git_calls),
    "B2": ("推荐 skill 写裸名（无 /skillname）", check_bare_skill_refs),
    "F1": ("skills/README.md 索引同步", check_readme_index),
    "F3": ("入口文档同步", check_entry_docs_sync),
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Skill 设计宪法机检")
    ap.add_argument("--only", choices=list(CHECKS), help="只跑某条检查")
    args = ap.parse_args()

    selected = {args.only: CHECKS[args.only]} if args.only else CHECKS
    total = 0
    for code, (label, fn) in selected.items():
        violations = fn()
        total += len(violations)
        mark = "✅" if not violations else "❌"
        print(f"{mark} {code} {label}: {len(violations)} 处")
        for v in violations:
            print(f"    - {v}")
    if total:
        print(f"\n违规合计 {total} 处（条文见 docs/skill-design-principles.md）")
        return 1
    print("\n全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
