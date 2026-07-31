"""零耦合闸门单测——重点锁 cross-line co-load 运行期命名空间 guard。

从本目录跑：
  cd tools/independence-audit/scripts && python3 -m pytest test_check_novel_n2d_zero_coupling.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("check_novel_n2d_zero_coupling.py")
spec = importlib.util.spec_from_file_location("zero_coupling", SCRIPT)
zc = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(zc)


def _mk(repo: Path, rel: str, body: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def test_neutral_file_coloading_both_lines_is_flagged(tmp_path: Path) -> None:
    # tools/ 中立文件同时把两线放上 sys.path = 共享进程 sys.modules 串模块风险
    _mk(tmp_path, "tools/orchestrate.py",
        "import sys\n"
        "sys.path.insert(0, 'skills/n2d/_lib')\n"
        "sys.path.insert(0, 'skills/novel/_lib')\n"
        "import settings\n")
    failures = zc.check_no_cross_line_coload(tmp_path)
    assert any("co-load" in f for f in failures)


def test_single_line_syspath_is_clean(tmp_path: Path) -> None:
    # 只加一条线 = 正常自包含，不报
    _mk(tmp_path, "skills/n2d/n2d-update/scripts/u.py",
        "import sys\nsys.path.insert(0, 'skills/n2d/_lib')\nimport settings\n")
    _mk(tmp_path, "skills/novel/novel-create/scripts/c.py",
        "import sys\nsys.path.insert(0, 'skills/novel/_lib')\nimport settings\n")
    assert zc.check_no_cross_line_coload(tmp_path) == []


def test_mentioning_both_lines_without_syspath_is_not_flagged(tmp_path: Path) -> None:
    # 纯文本扫描器（如 validate_skills）按 Path 遍历两线，但不 sys.path 加载 → 不算 co-load
    _mk(tmp_path, "tools/validate_like.py",
        "from pathlib import Path\n"
        "for d in (Path('skills/n2d'), Path('skills/novel')):\n"
        "    list(d.rglob('*.py'))\n")
    assert zc.check_no_cross_line_coload(tmp_path) == []


def test_repo_itself_passes_coload_guard() -> None:
    # 真仓库今天 0 命中——guard 锁住现状
    assert zc.check_no_cross_line_coload(zc.REPO) == []
