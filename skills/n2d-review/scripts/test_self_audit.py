from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("self_audit.py")
spec = importlib.util.spec_from_file_location("self_audit", SCRIPT)
self_audit = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(self_audit)


def _minimal_repo(root: Path) -> None:
    (root / "skills" / "novel2drama").mkdir(parents=True)
    (root / "skills" / "n2d-progress").mkdir(parents=True)
    (root / "skills" / "n2d-dashboard" / "references").mkdir(parents=True)
    (root / "skills" / "n2d-image").mkdir(parents=True)
    (root / "skills" / "novel2drama" / "progress.py").write_text(
        "def progress_lock(): pass\n"
        "def atomic_write_text():\n"
        "    os.replace('a', 'b')\n",
        encoding="utf-8",
    )
    (root / "skills" / "n2d-progress" / "scan.py").write_text(
        "def coverage_status(): pass\n"
        "def episode_coverage(): pass\n"
        "score_ = 'score_*.json'\n"
        "review_ui_ = 'review_ui_*.html'\n",
        encoding="utf-8",
    )
    (root / "skills" / "n2d-dashboard" / "references" / "industry_benchmark.json").write_text(
        '{"collected":"2026-06","sources":[],"one_pass_rate":0.9,"redraw_rate":0.1}\n',
        encoding="utf-8",
    )
    (root / "skills" / "n2d-image" / "SKILL.md").write_text(
        "python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image\n",
        encoding="utf-8",
    )


def test_self_audit_passes_minimal_aligned_repo(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    report = self_audit.audit(tmp_path)
    assert report["counts"]["block"] == 0
    assert not [f for f in report["findings"] if f["dim"] == "gate 单入口" and f["sev"] == "warn"]


def test_self_audit_flags_bare_production_gate(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    (tmp_path / "skills" / "n2d-image" / "SKILL.md").write_text(
        "python3 skills/n2d-review/scripts/gate.py <作品根> 第N集 --stage image\n",
        encoding="utf-8",
    )
    report = self_audit.audit(tmp_path)
    matches = [f for f in report["findings"] if f["dim"] == "gate 单入口"]
    assert matches and matches[0]["sev"] == "warn"
