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


def _write_minimal_contract(root: Path) -> None:
    (root / "skills" / "common").mkdir(parents=True, exist_ok=True)
    (root / "skills" / "common" / "n2d_contract.py").write_text(
        "APPROVED_IMAGE_BACKENDS = {\n"
        "  'codex': {'label': 'Codex'},\n"
        "  'openai': {'label': '官方 OpenAI gpt-image / DALL·E'},\n"
        "  'dreamina': {'label': 'Dreamina/即梦官方 CLI'},\n"
        "}\n",
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


def test_self_audit_flags_image_backend_doc_drift(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    _write_minimal_contract(tmp_path)
    (tmp_path / "skills" / "n2d-image" / "SKILL.md").write_text(
        "生图AI 可选 Codex 和 Dreamina/即梦官方 CLI。\n",
        encoding="utf-8",
    )
    report = self_audit.audit(tmp_path)
    matches = [f for f in report["findings"] if f["dim"] == "生图后端白名单"]
    assert matches and matches[0]["sev"] == "warn"
    assert "OpenAI" in matches[0]["loc"]


def test_self_audit_accepts_image_backend_docs_aligned(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    _write_minimal_contract(tmp_path)
    (tmp_path / "skills" / "n2d-image" / "SKILL.md").write_text(
        "生图AI 可选 Codex、OpenAI/gpt-image、Dreamina/即梦官方 CLI；同视频AI 是禁用旧值。\n",
        encoding="utf-8",
    )
    report = self_audit.audit(tmp_path)
    matches = [f for f in report["findings"] if f["dim"] == "生图后端白名单"]
    assert matches and matches[0]["sev"] == "info"
