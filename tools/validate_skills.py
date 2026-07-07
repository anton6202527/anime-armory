#!/usr/bin/env python3
"""Skill 设计宪法机检 runner —— 把 docs/skill-design-principles.md 里标 ✅ 的条文变成可执行检查。

唯一真值源是 docs/skill-design-principles.md；本脚本只机检其中能机检的几条：
  - E1  交付端 VCS-free：skill 不得用 git 做本仓状态/基线/变更检测（内容快照除外）。
  - B2  推荐 skill 写裸名：skill 的 SKILL.md/.sh/.py 不得把 skill 当斜杠命令写成 /skillname
         （含脚本里打印给用户看的 echo —— agent 可能把 /name 当内置斜杠命令）。
  - B7  n2d 人物定妆基础包与 Clip 前共享资产基础包不可缺失：
         宪法、n2d-image 铁律、prompt 模板、gate 常量和回归测试必须同时存在。
  - B9  n2d 无持久主体 ID 与项目记忆分层：Codex/OpenAI 无公开 subject_id 不得等同不能锁角色。
  - N1  novel runtime 不得裸 import contract：避免 shim 被 sys.path 顺序误解析。
  - N2  novel 易变市场断言必须绑定 market baseline / research sources。
  - T1  测试文件不得硬编码引用真实 `创作区/**` 作品路径；需要样例应使用 tmp_path 或 tests/fixtures。
  - F1  改了 skill 集合必须同步 skills/README.md 索引：每个 skills/<name>/ 都要在 README 出现。
  - F3  入口文档同步：AGENTS/GEMINI/CLAUDE 不得保留过期命令或旧路径，关键入口保持一致。
  - F7  系列规模统计同步：skills/README.md 与六个总领 skill 第一行统计不得过期。

零依赖、纯标准库，从仓库根跑：
    python3 tools/validate_skills.py            # 全检，违规 exit 1
    python3 tools/validate_skills.py --only E1  # 只跑某条
配套：跨线独立性(A1/F2) 由 tools/independence-audit/scripts/check_independence.py 机检，不在这里重复。
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

import update_skill_stats

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"
README = SKILLS / "README.md"
ENTRY_DOCS = ("AGENTS.md", "GEMINI.md", "CLAUDE.md")

# 创作线的 skill 名前缀（用于 B2 斜杠命令检测）
LINE_PREFIXES = ("n2d", "comic", "song", "mv", "ad")

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
    "`comic`",
    "`song`",
    "`mv`",
    "`ad`",
    "`n2d-progress`",
    "`comic-progress`",
    "`novel-settings`",
    "`n2d-settings`",
    "`comic-settings`",
    "`song-settings`",
    "`mv-settings`",
    "`ad-settings`",
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

NOVEL_MARKET_ALLOWED_FILES = {
    "novel-score/references/market-claims.md",
    "novel-score/scripts/collect_market_baseline.py",
}
NOVEL_MARKET_ALLOWED_PATH_PARTS = (
    "/test_",
    "/tests/",
    "/fixtures/",
)
NOVEL_MARKET_ANCHORS = (
    "market_baseline",
    "评分/market_baseline",
    "评分/题材热榜",
    "research_sources",
    "资料/research_sources",
    "market-claims.md",
    "实时基准",
    "当前基准",
    "资料包",
    "证据",
    "核验",
    "未单独验证",
    "待验证",
    "以实时基准为准",
)
NOVEL_MARKET_EXEMPT_RE = re.compile(r"(AI\s*检测|AI检测|perplexity|burstiness|burst|合规|版权|侵权|GB\s*\d|AI Act)")
NOVEL_MARKET_CLAIM_RE = re.compile(
    r"(?=.*(?:市场|平台|榜单|热榜|番茄|七猫|晋江|红果|抖音|短剧|改编|赛道|题材热度|读者口味|爆款|头部(?:作品|内容|平台|榜单)|支柱))"
    r"(?:"
    r".*\b20(?:2[5-9]|3\d)\b|"
    r".*\d+(?:\.\d+)?\s*%|"
    r".*\d+\s*(?:万|亿|千)\+?|"
    r".*(?:成功率|市场规模|半壁市场|第一变现|"
    r"平台(?:确认|投入|榜单|热榜)|"
    r"支柱|趋势|上升|降温|热门|退潮|疲软|头部(?:作品|内容|平台|榜单)|"
    r"改编(?:机会|概率|成功率|池|赛道))"
    r")"
)

TEST_SOURCE_ROOTS = (REPO / "tools", REPO / "skills", REPO / "tests")

B7_REQUIRED_SNIPPETS = {
    "docs/skill-design-principles.md": (
        "B7 人物定妆基础包不可缺失铁律",
        "Clip 图前完整资产基础包铁律",
        "七类基础定妆包",
        "三视图不能替代拆分 PNG",
        "同源母本派生",
        "derivation.method/source_path/source_sha256/crop_box",
        "planned",
        "共享资产必须先完成可传给模型的基础包",
        "不得生成 Clip 分镜图",
        "共享库先行顺序不可被",
        "enforce_shared_first_interlock",
    ),
    "skills/n2d-image/SKILL.md": (
        "角色定妆基础包铁律",
        "Clip 图前完整资产基础包铁律",
        "基础包至少七类",
        "不能替代正/45°/侧/背/半身/脸锚任一拆图",
        "同源母本派生铁律",
        "derive_makeup_pack.py",
        "derivation.method/source_path/source_sha256/crop_box",
        "未过人审不得标 ready",
        "配饰/标志物",
        "weapon_profile",
        "不得生成 Clip 分镜图",
        "--skip-preflight",
        "共享库先行顺序不可被",
        "enforce_shared_first_interlock",
    ),
    "skills/n2d-image/references/prompt_format.md": (
        "Clip 图前完整资产基础包铁律",
        "不得进入 `出图/第N集/图片/` 分镜生成",
        "`asset_registry` ID",
        "`weapon_profile`",
    ),
    "skills/n2d-image/references/角色一致性checklist.md": (
        "Clip 图前完整资产基础包",
        "不许先生成 `Clip_*` / `镜头*` 分镜 PNG",
    ),
    "skills/n2d-image/QUICKSTART.md": (
        "Shared reference assets must be complete before episode shot PNGs",
        "shared-first order is non-waivable",
        "post-generation self-check",
        "preflight block",
    ),
    "skills/n2d-image/scripts/derive_makeup_pack.py": (
        "turnaround_split",
        "front_crop",
        "source_sha256",
    ),
    "skills/n2d-image/scripts/codex_image_runner.py": (
        "requires_human_review_before_ready",
        "review_pending",
        "N2D_HUMAN_REVIEWED_SHARED",
        "shared_first_interlock_issues",
        "enforce_shared_first_interlock",
        "cannot bypass shared-first",
    ),
    "skills/n2d-image/scripts/dreamina_image_runner.py": (
        "enforce_shared_first_interlock",
        "--skip-preflight",
    ),
    "skills/n2d-image/scripts/test_codex_image_runner.py": (
        "test_shared_first_interlock_blocks_incomplete_character_pack",
        "test_main_skip_preflight_cannot_bypass_shared_first_interlock",
    ),
    "skills/n2d-image/scripts/test_derive_makeup_pack.py": (
        "test_derive_project_splits_turnaround_and_front_crops",
        "turnaround_split",
        "front_crop",
    ),
    "skills/n2d-review/scripts/gate.py": (
        "REQUIRED_CHARACTER_MAKEUP_REFERENCE_GROUP_FIELDS",
        "REQUIRED_CHARACTER_MAKEUP_ATLAS_VIEWS",
        "CHARACTER_MAKEUP_BODY_REFERENCE_FIELDS",
        "DERIVED_CHARACTER_MAKEUP_REFERENCE_FIELDS",
        "derivation.method/source_path/source_sha256/crop_box",
        "三视图人审拼版不能替代正/45°/侧/背等拆分参考",
    ),
    "skills/n2d-review/scripts/test_gate.py": (
        "test_identity_registry_missing_three_quarter_is_blocked",
        "test_identity_registry_planned_makeup_reference_is_blocked",
        "test_identity_registry_ready_split_reference_requires_same_source_derivation",
        "test_identity_registry_turnaround_cannot_replace_split_makeup_refs",
        "test_image_shot_prompt_missing_post_generation_self_check_blocks",
        "缺生成后逐张自检段",
    ),
}

B9_REQUIRED_SNIPPETS = {
    "docs/skill-design-principles.md": (
        "B9 无持久主体 ID 与项目记忆分层铁律",
        "公开服务端持久主体 ID / character subject handle",
        "项目记忆式主体连续性",
        "不得写成不能做角色一致性",
        "不得因为 `persistent_subject=False` 自动阻断核心/长线角色出图",
        "identity_registry",
        "codex_reference_bundles",
        "每镜真实图片入参",
        "actual image inputs=0",
        "missing_ready_refs",
        "split_composite",
        "full `image_qc`",
    ),
    "skills/n2d/_lib/n2d_schema.py": (
        "无公开服务端持久角色 ID",
        "项目记忆 reference_group",
        "真实图片入参",
        "高保真参考",
        "无 n2d 持久主体 ID",
    ),
    "skills/n2d/_lib/image_backend_adapter.py": (
        "codex exec --image",
        "supports_high_fidelity_reference",
        "no_persistent_subject_id",
        "multi_image_flags",
    ),
    "skills/n2d-image/scripts/codex_image_runner.py": (
        "n2d_codex_reference_bundle",
        "true_image_reference_support",
        "reference_input_mode",
        "codex_exec_image_flags",
        "persistent_subject_support",
        "cli_image_input_count",
        "missing_ready_refs",
    ),
    "skills/n2d-image/scripts/face_drift_risk.py": (
        "PROJECT_MEMORY_BACKENDS",
        "backend_can_use_project_memory",
        "project_memory_mitigation",
        "project_memory_reference_bundle",
        "codex_reference_bundles",
        "actual image inputs",
        "missing_ready_refs",
        "当前后端仍无持久主体 ID，但不再因这一点自动阻断",
    ),
    "skills/n2d-image/scripts/test_face_drift_risk.py": (
        "test_analyze_core_high_risk_project_memory_mitigates_predicted_block",
        "project_memory_reference_bundle",
        "split_composite_required",
    ),
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


def check_skill_stats_sync() -> list[str]:
    """F7: README scale table and top-level dispatcher stat lines must be fresh."""
    return update_skill_stats.validate_stats(update_skill_stats.get_stats())


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


def _gate_layer_text(p) -> str:
    """读 n2d-review gate 闸源码全集：若是 gate.py，则并上同目录 gate_core.py + gates/*.py。

    增量2 按证据族拆分后，B7/B9 守护片段分散到共享基座 gate_core.py / 证据族子包 gates/*.py，
    单读 gate.py 会漏报。与 consistency_charter.gate_source_text 同一多文件纪律。"""
    text = p.read_text("utf-8", "ignore")
    if p.name == "gate.py" and p.parent.name == "scripts" and p.parent.parent.name == "n2d-review":
        for e in [p.parent / "gate_core.py", *sorted(p.parent.glob("gates/*.py"))]:
            if e.is_file():
                text += "\n" + e.read_text("utf-8", "ignore")
    return text


def check_n2d_character_makeup_constitution() -> list[str]:
    """B7: n2d 定妆/Clip 前基础包铁律不能只剩口号，必须有文档、gate 和测试锚点。"""
    bad: list[str] = []
    for rel, snippets in B7_REQUIRED_SNIPPETS.items():
        p = REPO / rel
        if not p.is_file():
            bad.append(f"{rel}: 文件不存在，B7 定妆/Clip 前基础包铁律失去覆盖")
            continue
        text = _gate_layer_text(p)
        for needle in snippets:
            if needle not in text:
                bad.append(f"{rel}: 缺少 B7 守护片段 '{needle}'")
    return bad


def check_n2d_project_memory_constitution() -> list[str]:
    """B9: 无持久主体 ID 不得被误写成不能锁角色；项目记忆路线必须保留机检锚点。"""
    bad: list[str] = []
    for rel, snippets in B9_REQUIRED_SNIPPETS.items():
        p = REPO / rel
        if not p.is_file():
            bad.append(f"{rel}: 文件不存在，B9 项目记忆铁律失去覆盖")
            continue
        text = _gate_layer_text(p)
        for needle in snippets:
            if needle not in text:
                bad.append(f"{rel}: 缺少 B9 守护片段 '{needle}'")
    return bad


def check_novel_import_shadowing() -> list[str]:
    """N1: novel runtime code must import novel_contract explicitly."""
    script = REPO / "tools" / "independence-audit" / "scripts" / "check_novel_import_shadowing.py"
    if not script.is_file():
        return [f"{script.relative_to(REPO)}: 文件不存在，novel import-shadowing 机检失去覆盖"]
    spec = importlib.util.spec_from_file_location("_novel_import_shadowing_check", script)
    if spec is None or spec.loader is None:
        return [f"{script.relative_to(REPO)}: 无法加载 novel import-shadowing 机检"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.check_novel_import_shadowing())


def _line_has_market_anchor(lines: list[str], idx: int) -> bool:
    """Return whether the claim line is tied to an explicit evidence mechanism."""
    window = "\n".join(lines[max(0, idx - 2): min(len(lines), idx + 3)])
    doc_scope = "\n".join(lines[:12])
    return any(anchor in window or anchor in doc_scope for anchor in NOVEL_MARKET_ANCHORS)


def check_novel_market_claims() -> list[str]:
    """N2: novel docs/scripts must not freeze volatile market claims in prose.

    Platform rankings, trend years, percentages, market-size numbers, and
    adaptation-probability claims must point to project evidence
    (market_baseline/research_sources) or live verification wording. The
    dedicated collector and policy doc are allowed to describe the rule itself.
    """
    bad: list[str] = []
    for root in sorted(SKILLS.glob("novel*")):
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if p.suffix not in (".md", ".py") or not p.is_file():
                continue
            rel = _rel(p)
            rel_with_slash = "/" + rel
            if rel in NOVEL_MARKET_ALLOWED_FILES:
                continue
            if any(part in rel_with_slash for part in NOVEL_MARKET_ALLOWED_PATH_PARTS):
                continue
            lines = p.read_text("utf-8", "ignore").splitlines()
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith(("import ", "from ")):
                    continue
                if NOVEL_MARKET_EXEMPT_RE.search(stripped):
                    continue
                if not NOVEL_MARKET_CLAIM_RE.search(stripped):
                    continue
                if _line_has_market_anchor(lines, i - 1):
                    continue
                bad.append(
                    f"{rel}:{i}: 易变市场/平台断言缺少 market_baseline 或 research_sources 证据锚点 —— "
                    f"{stripped[:100]}"
                )
    return bad


def _is_test_source_file(p: Path) -> bool:
    """Return whether a Python file is a test source file."""
    if p.suffix != ".py" or not p.is_file():
        return False
    try:
        parts = p.relative_to(REPO).parts
    except ValueError:
        parts = p.parts
    return p.name.startswith("test_") or p.name.endswith("_test.py") or "tests" in parts


def _workspace_work_names() -> set[str]:
    """Collect concrete work names currently under 创作区/<line>/<work>."""
    names: set[str] = set()
    root = REPO / "创作区"
    if not root.is_dir():
        return names
    for line_dir in root.iterdir():
        if not line_dir.is_dir():
            continue
        for work_dir in line_dir.iterdir():
            if work_dir.is_dir():
                names.add(work_dir.name)
    return names


def _line_mentions_real_work_path(line: str, work_names: set[str]) -> bool:
    """Detect hard-coded real workspace project paths in tests.

    Tests may construct fake projects under tmp_path/tempfile with generic names.
    What is forbidden is using a concrete project from the repo's 创作区 as the
    fixture source, because those production directories are allowed to be moved
    or cleaned independently from regression fixtures.
    """
    if "创作区" not in line:
        return False
    return any(name and name in line for name in work_names)


def check_tests_do_not_reference_real_workspace_projects() -> list[str]:
    """T1: tests must not depend on concrete production works under 创作区/**."""
    work_names = _workspace_work_names()
    if not work_names:
        return []
    bad: list[str] = []
    for root in TEST_SOURCE_ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if not _is_test_source_file(p):
                continue
            rel = p.relative_to(REPO)
            lines = p.read_text("utf-8", "ignore").splitlines()
            for i, line in enumerate(lines, 1):
                if _line_mentions_real_work_path(line, work_names):
                    bad.append(
                        f"{rel}:{i}: 测试文件硬编码引用真实创作区作品路径；"
                        "请改用 tmp_path 构造泛化项目或移入 tests/fixtures —— "
                        f"{line.strip()[:120]}"
                    )
    return bad


CHECKS = {
    "E1": ("交付端 VCS-free（无 git 调用）", check_no_git_calls),
    "B2": ("推荐 skill 写裸名（无 /skillname）", check_bare_skill_refs),
    "B7": ("n2d 人物定妆与 Clip 前共享资产基础包不可缺失", check_n2d_character_makeup_constitution),
    "B9": ("n2d 无持久主体 ID 与项目记忆分层", check_n2d_project_memory_constitution),
    "N1": ("novel runtime 无 contract 裸导入", check_novel_import_shadowing),
    "N2": ("novel 市场断言必须绑定证据", check_novel_market_claims),
    "T1": ("测试不得引用真实创作区作品路径", check_tests_do_not_reference_real_workspace_projects),
    "F1": ("skills/README.md 索引同步", check_readme_index),
    "F3": ("入口文档同步", check_entry_docs_sync),
    "F7": ("系列规模统计同步", check_skill_stats_sync),
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
