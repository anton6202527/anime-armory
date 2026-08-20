"""Sync guard for n2d-update's file→stage hint tables.

Run from this directory:
    cd skills/n2d/n2d-update/scripts && python -m pytest test_hint_coverage.py

The classification tables in update_plan.py enumerate concrete filenames. When a
new `n2d/_lib/*.py` appears, or a hinted reference file is renamed, the table
silently drifts: an unclassified `_lib` file falls back to `script_stage1`
(over-rebuilds the whole chain from 拆集), and an orphaned 分镜 reference token
falls back to `owned[0]` (also script_stage1). Both burn paid generation while
looking "safe". These tests fail the moment a real file stops being explicitly
classified, forcing the table to stay complete.
"""
import glob
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import update_plan as up  # noqa: E402

REPO_ROOT = Path(up.REPO_ROOT)
N2D_LIB_DIR = REPO_ROOT / "skills" / "n2d" / "_lib"


def _real_lib_modules():
    """Runtime `n2d/_lib/*.py` (tests excluded — they never affect produced artifacts)."""
    out = []
    for p in sorted(N2D_LIB_DIR.glob("*.py")):
        if up.is_test_path(p.name):
            continue
        out.append("skills/n2d/_lib/" + p.name)
    return out


def _lib_classified_stage(rel):
    """The stage a `_lib` file is EXPLICITLY classified under, or None if unclassified.

    Mirrors the lookup order in update_plan but never returns the unknown→stage1
    fallback, so it can distinguish "classified as stage1" from "fell through".
    """
    if any(tok in rel for tok in up.N2D_LIB_OBSERVE_ONLY_TOKENS):
        return "observe_only"
    for stage_key, tokens in up.N2D_LIB_FILE_STAGE_HINTS:
        if any(tok in rel for tok in tokens):
            return stage_key
    for stage_key, tokens in up.GATE_ONLY_FILE_STAGE_HINTS.get("n2d", ()):
        if any(tok in rel for tok in tokens):
            return "gate_only:" + stage_key
    return None


def test_every_lib_module_is_explicitly_classified():
    """No `_lib` module may rely on the unknown→script_stage1 over-rebuild fallback."""
    unclassified = [rel for rel in _real_lib_modules() if _lib_classified_stage(rel) is None]
    assert not unclassified, (
        "新增/未分类的 n2d/_lib 模块会静默回退到 script_stage1（全链从拆集重制·烧钱）。"
        "请在 update_plan.py 的 N2D_LIB_FILE_STAGE_HINTS（影响产物的阶段）或 "
        "N2D_LIB_OBSERVE_ONLY_TOKENS（仅审计/不产物料）里登记：" + ", ".join(unclassified)
    )


def test_paid_execution_contract_replays_from_first_paid_stage():
    rel = "skills/n2d/_lib/paid_execution_contract.py"

    assert _lib_classified_stage(rel) == "image"


def test_lib_hint_tokens_point_at_real_files():
    """Every enumerated `_lib` token must resolve to an existing file (rename guard)."""
    tokens = list(up.N2D_LIB_OBSERVE_ONLY_TOKENS)
    for _stage, toks in up.N2D_LIB_FILE_STAGE_HINTS:
        tokens.extend(toks)
    missing = []
    for tok in tokens:
        # tokens are `_lib/<file>.py`; resolve against the n2d skill root.
        if (REPO_ROOT / "skills" / "n2d" / tok).is_file():
            continue
        missing.append(tok)
    assert not missing, (
        "这些 _lib 映射 token 指向的文件已不存在（重命名/删除后映射表没跟着改，"
        "对应改动会落到兜底阶段）：" + ", ".join(missing)
    )


def test_shared_lock_rule_files_exist():
    """Known n2d-image shared-lock rule files must exist (rename downgrade guard).

    A renamed-but-still-listed rule file would silently drop to the generic
    `unknown_reference_rule` path and lose its specific shared-lock semantics.
    """
    missing = [rel for rel in up.N2D_IMAGE_SHARED_LOCK_RULE_FILES if not (REPO_ROOT / rel).is_file()]
    assert not missing, (
        "N2D_IMAGE_SHARED_LOCK_RULE_FILES 列的定妆库规则文件不存在了（重命名后未同步）："
        + ", ".join(missing)
    )


def test_skill_file_stage_hint_tokens_match_real_files():
    """Each multi-stage owner's hint tokens must still match ≥1 real file.

    Catches a renamed 分镜 reference (e.g. 打斗分镜.md → …) that would orphan its
    token and silently over-rebuild from script_stage1 instead of script_stage2.
    """
    orphaned = []
    for skill, rules in up.SKILL_FILE_STAGE_HINTS.items():
        line = skill.split("-", 1)[0]
        skill_dir = REPO_ROOT / "skills" / line / skill
        all_paths = [
            os.path.relpath(p, REPO_ROOT).replace(os.sep, "/")
            for p in glob.glob(str(skill_dir / "**" / "*"), recursive=True)
            if os.path.isfile(p)
        ]
        for _stage, tokens in rules:
            for tok in tokens:
                if not any(tok in rel for rel in all_paths):
                    orphaned.append(f"{skill}:{tok}")
    assert not orphaned, (
        "这些 SKILL_FILE_STAGE_HINTS token 匹配不到任何真实文件（很可能被重命名了，"
        "对应改动会回退到该 skill 最早阶段·过度重制）：" + ", ".join(orphaned)
    )
